#!/usr/bin/env python3
"""Nuxel device-lock credential owner (PWNAGE-45000).

The verifier lives here, in the root bridge process, never in browser
JavaScript/localStorage.  Credentials are stored as salted scrypt verifiers with
constant-time comparison, restrictive permissions and persistent rate limiting.
Fingerprint is only selectable when a secure provider is ready AND a PIN
fallback has been configured; otherwise it is refused.

The authoritative locked flag is /run/nuxel/security/lock-state.json.  Home
uses it for its lock overlay and the bridge refuses native launches while
locked.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import secrets
import tempfile
import threading
import time
from typing import Any, Dict, Optional

DEFAULT_CRED = "/var/lib/nuxel/security/lock.json"
DEFAULT_STATE = "/run/nuxel/security/lock-state.json"
DEFAULT_BIOMETRIC = "/etc/nuxel/security/biometric-unlock.json"
SCRYPT_N, SCRYPT_R, SCRYPT_P = 2 ** 14, 8, 1
MAX_FAILURES = 5
LOCKOUT_BASE_S = 30
MIN_PIN = 6
VALID_MODES = ("swipe", "pattern", "pin", "fingerprint")


def _atomic_json(path: str, doc: Dict[str, Any], mode: int = 0o600) -> None:
    d = os.path.dirname(path)
    os.makedirs(d, exist_ok=True)
    os.chmod(d, 0o700)
    fd, tmp = tempfile.mkstemp(prefix=".lock-", dir=d)
    try:
        os.fchmod(fd, mode)
        with os.fdopen(fd, "w") as fh:
            json.dump(doc, fh, sort_keys=True, indent=2)
            fh.write("\n")
        os.replace(tmp, path)
        os.chmod(path, mode)
    finally:
        try:
            os.unlink(tmp)
        except OSError:
            pass


def _read_json(path: str) -> Dict[str, Any]:
    try:
        with open(path) as fh:
            doc = json.load(fh)
        return doc if isinstance(doc, dict) else {}
    except (OSError, ValueError):
        return {}


def _derive(secret: str, salt_hex: str) -> str:
    salt = bytes.fromhex(salt_hex)
    return hashlib.scrypt(secret.encode("utf-8"), salt=salt, n=SCRYPT_N,
                          r=SCRYPT_R, p=SCRYPT_P, dklen=32).hex()


def _trivial_pin(pin: str) -> bool:
    if len(pin) < MIN_PIN or not pin.isdigit():
        return True
    if pin == pin[0] * len(pin):
        return True
    asc = "0123456789"
    if pin in asc or pin in asc[::-1]:
        return True
    # Monotonic stepping sequences, e.g. 123456 / 987654.
    deltas = [int(pin[i + 1]) - int(pin[i]) for i in range(len(pin) - 1)]
    if len(set(deltas)) == 1 and deltas[0] in (-1, 1):
        return True
    return False


def _trivial_pattern(pattern: str) -> bool:
    seq = [p for p in pattern.strip().split("-") if p]
    if len(seq) < 4:
        return True
    return len(set(seq)) < 4


class SecurityProvider:
    def __init__(self) -> None:
        self.cred_path = os.environ.get("NUXEL_LOCK_CREDENTIAL", DEFAULT_CRED)
        self.state_path = os.environ.get("NUXEL_LOCK_STATE", DEFAULT_STATE)
        self.biometric_path = os.environ.get("NUXEL_BIOMETRIC_STATE", DEFAULT_BIOMETRIC)
        self._lock = threading.RLock()

    def _state(self) -> Dict[str, Any]:
        st = _read_json(self.state_path)
        if not st:
            st = {"locked": True, "reason": "no-state: fail locked"}
        return st

    def _write_state(self, locked: bool, reason: str) -> None:
        _atomic_json(self.state_path, {
            "schema_version": 1,
            "locked": bool(locked),
            "reason": reason,
            "updated_at": time.time(),
            "owner": "security_provider",
        })

    def _biometric_doc(self) -> Dict[str, Any]:
        doc = _read_json(self.biometric_path)
        return {"schema_version": 1, "enabled": bool(doc.get("enabled", False)),
                "updated_at": float(doc.get("updated_at", 0) or 0),
                "source": doc.get("source", "default")}

    def biometric_status(self, fp_ready: bool) -> Dict[str, Any]:
        doc = self._biometric_doc()
        return {
            "supported": bool(fp_ready),
            "enabled": bool(doc.get("enabled")) if fp_ready else False,
            "available": bool(fp_ready),
            "reason": None if fp_ready else "no verified secure fingerprint provider",
            "pin_fallback_required": True,
            "updated_at": doc.get("updated_at", 0),
            "source": "security_provider",
        }

    def set_biometric_unlock(self, enabled: bool) -> Dict[str, Any]:
        with self._lock:
            st = self.status()
            fp = st.get("fingerprint") or {}
            if not fp.get("provider_ready"):
                return {"success": False, "error": "fingerprint_provider_unavailable",
                        "detail": "no verified secure fingerprint provider exists for this sensor",
                        "biometric_unlock": self.biometric_status(False)}
            if enabled and not fp.get("selectable"):
                return {"success": False, "error": "pin_fallback_required",
                        "detail": "set the PIN fallback before enabling fingerprint unlock",
                        "biometric_unlock": self.biometric_status(True)}
            _atomic_json(self.biometric_path, {
                "schema_version": 1, "enabled": bool(enabled),
                "updated_at": time.time(), "source": "user",
            }, 0o600)
            return {"success": True, **self.biometric_status(True)}

    def status(self) -> Dict[str, Any]:
        with self._lock:
            cred = _read_json(self.cred_path)
            state = self._state()
            mode = cred.get("mode", "swipe")
            failures = int(cred.get("failures", 0) or 0)
            locked_until = float(cred.get("locked_until", 0) or 0)
            fp_ready = False
            try:
                import fingerprint_provider
                fp_ready = bool(fingerprint_provider.handle("status", {}).get("ready"))
            except Exception:
                fp_ready = False
            bio = self.biometric_status(fp_ready)
            return {
                "success": True,
                "schema": "nuxel.security-status/1",
                "mode": mode,
                "biometric_unlock": bio,
                "fingerprint_unlock": bio,
                "credential_set": bool(cred.get("verifier")) or mode == "swipe",
                "pin_fallback_set": mode in ("pin", "pattern", "fingerprint") and bool(cred.get("fallback_pin_verifier")),
                "locked": bool(state.get("locked", True)),
                "reason": state.get("reason", "unknown"),
                "fingerprint": {"provider_ready": fp_ready,
                                "selectable": bool(fp_ready and cred.get("fallback_pin_verifier"))},
                "rate_limit": {
                    "failures": failures,
                    "locked_until": locked_until,
                    "locked_out": locked_until > time.time(),
                    "remaining_s": max(0, int(locked_until - time.time())),
                },
                "kdf": "scrypt(n=2^14,r=8,p=1,dklen=32)",
                "source": "security_provider",
            }

    def _set_secret(self, mode: str, secret: str, fallback_pin: Optional[str] = None,
                    current_secret: Optional[str] = None, confirm_downgrade: bool = False,
                    allow_swipe: bool = False) -> Dict[str, Any]:
        with self._lock:
            old = _read_json(self.cred_path)
            st = self.status()
            if st["rate_limit"]["locked_out"]:
                return {"success": False, "error": "rate_limited",
                        "remaining_s": st["rate_limit"]["remaining_s"]}
            if old.get("verifier"):
                if current_secret is None or not self._verify_locked(old, current_secret):
                    return {"success": False, "error": "current_credential_required"}
            if mode not in VALID_MODES:
                return {"success": False, "error": "invalid_mode"}
            if mode == "swipe" and not confirm_downgrade:
                return {"success": False, "error": "explicit_downgrade_confirmation_required"}
            doc: Dict[str, Any] = {"schema_version": 1, "mode": mode,
                                   "failures": 0, "locked_until": 0,
                                   "updated_at": time.time()}
            if mode != "swipe":
                if mode == "pin":
                    if _trivial_pin(secret or ""):
                        return {"success": False, "error": "pin_too_weak",
                                "detail": "use at least 6 digits and avoid repeats/sequences"}
                elif mode == "pattern":
                    if _trivial_pattern(secret or ""):
                        return {"success": False, "error": "pattern_too_weak"}
                elif mode == "fingerprint":
                    if not fallback_pin or _trivial_pin(fallback_pin):
                        return {"success": False, "error": "fingerprint_requires_pin_fallback"}
                    fp = __import__("fingerprint_provider").handle("status", {})
                    if not fp.get("ready"):
                        return {"success": False, "error": "fingerprint_provider_unavailable",
                                "detail": fp.get("blocker")}
                    doc["fallback_pin_salt"] = secrets.token_hex(16)
                    doc["fallback_pin_verifier"] = _derive(fallback_pin, doc["fallback_pin_salt"])
                if mode in ("pin", "pattern"):
                    doc["salt"] = secrets.token_hex(16)
                    doc["verifier"] = _derive(secret, doc["salt"])
                elif mode == "fingerprint":
                    # No PIN verifier for unlock; the PIN is the mandatory
                    # fallback (stored above).  The secure provider owns the
                    # biometric template and is currently unavailable.
                    doc["provider"] = "secure-fingerprint"
            _atomic_json(self.cred_path, doc)
            self._write_state(True, "credential-set")
            return self.status()

    def set_mode(self, mode: str, secret: str = "", **kw) -> Dict[str, Any]:
        return self._set_secret(mode, secret, **kw)

    def _verify_locked(self, cred: Dict[str, Any], secret: str) -> bool:
        if not cred.get("verifier") or not cred.get("salt"):
            return False
        try:
            got = _derive(secret, cred["salt"])
            return hmac.compare_digest(got, cred["verifier"])
        except Exception:
            return False

    def _record_failure(self) -> Dict[str, Any]:
        cred = _read_json(self.cred_path)
        failures = int(cred.get("failures", 0) or 0) + 1
        until = 0.0
        if failures >= MAX_FAILURES:
            until = time.time() + LOCKOUT_BASE_S * (2 ** (failures - MAX_FAILURES))
        cred["failures"] = failures
        cred["locked_until"] = until
        _atomic_json(self.cred_path, cred)
        return {"failures": failures, "locked_until": until}

    def unlock(self, secret: str) -> Dict[str, Any]:
        with self._lock:
            cred = _read_json(self.cred_path)
            state = self.status()
            if state["rate_limit"]["locked_out"]:
                return {"success": False, "error": "rate_limited",
                        "remaining_s": state["rate_limit"]["remaining_s"],
                        "locked": True}
            mode = cred.get("mode", "swipe")
            if mode == "swipe":
                self._write_state(False, "swipe")
                return {"success": True, "unlocked": True, "locked": False}
            if not self._verify_locked(cred, secret or ""):
                r = self._record_failure()
                return {"success": False, "error": "invalid_credential",
                        "failures": r["failures"],
                        "locked_until": r["locked_until"], "locked": True}
            cred["failures"] = 0
            cred["locked_until"] = 0
            _atomic_json(self.cred_path, cred)
            self._write_state(False, "credential-verified")
            return {"success": True, "unlocked": True, "locked": False}

    def lock(self, reason: str = "manual") -> Dict[str, Any]:
        with self._lock:
            self._write_state(True, reason)
            return self.status()


_PROVIDER: Optional[SecurityProvider] = None


def get_provider() -> SecurityProvider:
    global _PROVIDER
    if _PROVIDER is None:
        _PROVIDER = SecurityProvider()
    return _PROVIDER


def handle(verb: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    params = params or {}
    p = get_provider()
    if verb in ("status", "get"):
        return p.status()
    if verb == "lock":
        return p.lock(str(params.get("reason", "manual")))
    if verb == "unlock":
        return p.unlock(str(params.get("secret", "")))
    if verb in ("biometric-status", "biometric-get"):
        return p.biometric_status(p.status().get("fingerprint", {}).get("provider_ready", False))
    if verb in ("set-biometric-unlock", "biometric-set"):
        return p.set_biometric_unlock(bool(params.get("enabled", False)))
    if verb in ("set-mode", "set-credential", "set-pin", "set-pattern"):
        mode = params.get("mode") or {"set-pin": "pin", "set-pattern": "pattern"}.get(verb)
        return p.set_mode(str(mode), str(params.get("secret", "")),
                          fallback_pin=params.get("fallback_pin"),
                          current_secret=params.get("current_secret"),
                          confirm_downgrade=bool(params.get("confirm_downgrade")))
    return {"success": False, "error": "unknown security verb", "verb": verb}
