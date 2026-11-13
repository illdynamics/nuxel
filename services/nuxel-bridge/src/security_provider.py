#!/usr/bin/env python3
"""Nuxel device-lock credential owner (PWNAGE-45000 / A80).

The verifier lives here, in the root bridge process, never in browser
JavaScript/localStorage.  Credentials are stored as salted scrypt verifiers with
constant-time comparison, restrictive permissions and persistent failure
accounting.  The attempt policy is owner-configurable:

  * "limited"  — historical behaviour: after MAX_FAILURES a growing lockout.
  * "unlimited"— no lockout/blocking at all.  This is the owner's explicit
    temporary choice for the role-out phase so a mis-typo can never wedge the
    phone; the configured credential is still required to unlock.

Modes
-----
  swipe       no credential (drag the penguin up)
  pin         numeric PIN (stored in salt/verifier)
  pattern     Android-style dot pattern "0-4-8-5-2" (salt/verifier)
  fingerprint secure biometric provider unlock + mandatory PIN fallback
              (fallback_pin_salt/fallback_pin_verifier)

The credential-mode-aware verification is important: fingerprint mode never has
a `verifier`, so `unlock()` must consult the fallback verifier instead of the
normal one.  A pattern credential is accepted ONLY as a pattern and a PIN only
as a PIN (no cross-mode replay of the same digits).
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
DEFAULT_POLICY = "/var/lib/nuxel/security/lock-policy.json"
SCRYPT_N, SCRYPT_R, SCRYPT_P = 2 ** 14, 8, 1
MAX_FAILURES = 5
LOCKOUT_BASE_S = 30
MIN_PIN = 4
VALID_MODES = ("swipe", "pattern", "pin", "fingerprint")
PATTERN_DOTS = 9
PATTERN_MIN_DOTS = 4
ATTEMPT_POLICIES = ("unlimited", "limited")
DEFAULT_ATTEMPT_POLICY = "unlimited"


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


def normalize_pin(pin: Any) -> str:
    """Digits only, whitespace stripped.  A PIN is never a pattern string."""
    return "".join(ch for ch in str(pin or "") if ch.isdigit())


def normalize_pattern(pattern: Any) -> str:
    """Canonical '0-1-2-5-8' form from dots 0..8.

    Accepts '0-1-2-5-8', '0,1,2,5,8', '01258' or a JSON list.  Rejects any
    dot outside 0..8, repeated immediate dots and separators that make no sense.
    """
    if isinstance(pattern, (list, tuple)):
        parts = [str(p).strip() for p in pattern]
    else:
        text = str(pattern or "").strip()
        if not text:
            return ""
        if text.startswith("["):
            try:
                return normalize_pattern(json.loads(text))
            except (ValueError, TypeError):
                return ""
        for sep in (",", " ", ":", "."):
            text = text.replace(sep, "-")
        parts = [p for p in text.split("-") if p != ""]
        if len(parts) == 1 and len(parts[0]) > 1 and parts[0].isdigit():
            parts = list(parts[0])
    out = []
    for p in parts:
        if not p.isdigit():
            return ""
        n = int(p)
        if n < 0 or n >= PATTERN_DOTS:
            return ""
        if out and out[-1] == str(n):
            return ""
        out.append(str(n))
    return "-".join(out)


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
    """Reject patterns that are trivial to guess OR easy to enter by accident.

    Weak: fewer than PATTERN_MIN_DOTS dots, too few distinct dots, a straight
    three-dot line (0-1-2 / 0-3-6), or an "L" swipe where three/four dots are
    one row/column plus the next dot of that line (0-1-3-5).  A normal
    Android-style zig-zag such as 0-4-8-5-2 is accepted.
    """
    seq = [p for p in pattern.strip().split("-") if p]
    if len(seq) < PATTERN_MIN_DOTS:
        return True
    if len(set(seq)) < PATTERN_MIN_DOTS:
        return True
    rows = [["0", "1", "2"], ["3", "4", "5"], ["6", "7", "8"]]
    cols = [["0", "3", "6"], ["1", "4", "7"], ["2", "5", "8"]]
    for line in rows + cols:
        for i in range(len(seq) - 2):
            if seq[i:i + 3] == line:
                return True
    for line in rows + cols:
        on = [p for p in seq if p in line]
        if len(on) == 3 and len(set(on)) == 3 and seq[-1] in line:
            return True
    return False


class SecurityProvider:
    def __init__(self) -> None:
        self.cred_path = os.environ.get("NUXEL_LOCK_CREDENTIAL", DEFAULT_CRED)
        self.state_path = os.environ.get("NUXEL_LOCK_STATE", DEFAULT_STATE)
        self.biometric_path = os.environ.get("NUXEL_BIOMETRIC_STATE", DEFAULT_BIOMETRIC)
        self.policy_path = os.environ.get("NUXEL_LOCK_POLICY", DEFAULT_POLICY)
        self._lock = threading.RLock()

    # ------------------------------------------------------------ state files
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

    def _policy(self) -> Dict[str, Any]:
        doc = _read_json(self.policy_path)
        attempts = doc.get("attempt_policy")
        if attempts not in ATTEMPT_POLICIES:
            attempts = DEFAULT_ATTEMPT_POLICY
        return {"schema_version": 1, "attempt_policy": attempts,
                "updated_at": float(doc.get("updated_at", 0) or 0),
                "source": doc.get("source", "default")}

    def set_attempt_policy(self, policy: Any) -> Dict[str, Any]:
        with self._lock:
            p = str(policy or "").strip().lower()
            if p not in ATTEMPT_POLICIES:
                return {"success": False, "error": "invalid_attempt_policy",
                        "valid": list(ATTEMPT_POLICIES)}
            _atomic_json(self.policy_path, {
                "schema_version": 1, "attempt_policy": p,
                "updated_at": time.time(), "source": "user",
            }, 0o644)
            # Switching back to a limited policy starts from a clean slate.
            cred = _read_json(self.cred_path)
            if cred:
                cred["failures"] = 0
                cred["locked_until"] = 0
                _atomic_json(self.cred_path, cred)
            return {"success": True, **self._policy()}

    def _biometric_doc(self) -> Dict[str, Any]:
        doc = _read_json(self.biometric_path)
        return {"schema_version": 1, "enabled": bool(doc.get("enabled", False)),
                "enrolled": bool(doc.get("enrolled", False)),
                "updated_at": float(doc.get("updated_at", 0) or 0),
                "source": doc.get("source", "default")}

    def biometric_status(self, fp_ready: bool) -> Dict[str, Any]:
        doc = self._biometric_doc()
        return {
            "supported": bool(fp_ready),
            "enabled": bool(doc.get("enabled")) if fp_ready else False,
            "available": bool(fp_ready),
            "enrolled": bool(doc.get("enrolled")) if fp_ready else False,
            "reason": None if fp_ready else "no verified secure fingerprint provider",
            "pin_fallback_required": True,
            "updated_at": doc.get("updated_at", 0),
            "source": "security_provider",
        }

    def set_biometric_unlock(self, enabled: bool) -> Dict[str, Any]:
        return self.set_biometric(enabled=enabled)

    def set_biometric(self, enabled: Optional[bool] = None,
                      enrolled: Optional[bool] = None) -> Dict[str, Any]:
        with self._lock:
            st = self.status()
            fp = st.get("fingerprint") or {}
            if not fp.get("provider_ready"):
                return {"success": False, "error": "fingerprint_provider_unavailable",
                        "detail": "no verified secure fingerprint provider exists for this sensor",
                        "biometric_unlock": self.biometric_status(False)}
            doc = self._biometric_doc()
            if enrolled is not None:
                doc["enrolled"] = bool(enrolled)
                if not enrolled:
                    doc["enabled"] = False
            if enabled is not None:
                if enabled and not st.get("pin_fallback_set"):
                    return {"success": False, "error": "pin_fallback_required",
                            "detail": "set a PIN fallback before enabling fingerprint unlock",
                            "biometric_unlock": self.biometric_status(True)}
                if enabled and not doc.get("enrolled"):
                    return {"success": False, "error": "fingerprint_not_enrolled",
                            "detail": "enroll a fingerprint before enabling biometric unlock",
                            "biometric_unlock": self.biometric_status(True)}
                doc["enabled"] = bool(enabled)
            doc.update({"schema_version": 1, "updated_at": time.time(), "source": "user"})
            _atomic_json(self.biometric_path, doc, 0o600)
            return {"success": True, **self.biometric_status(True)}

    # ----------------------------------------------------------------- status
    def status(self) -> Dict[str, Any]:
        with self._lock:
            cred = _read_json(self.cred_path)
            state = self._state()
            policy = self._policy()
            mode = cred.get("mode", "swipe")
            if mode not in VALID_MODES:
                mode = "swipe"
            failures = int(cred.get("failures", 0) or 0)
            locked_until = float(cred.get("locked_until", 0) or 0)
            fp_ready = False
            try:
                import fingerprint_provider
                fp_ready = bool(fingerprint_provider.handle("status", {}).get("ready"))
            except Exception:
                fp_ready = False
            bio = self.biometric_status(fp_ready)
            enabled = policy["attempt_policy"] == "limited"
            locked_out = bool(enabled and locked_until > time.time())
            return {
                "success": True,
                "schema": "nuxel.security-status/1",
                "mode": mode,
                "biometric_unlock": bio,
                "fingerprint_unlock": bio,
                "credential_set": bool(cred.get("verifier")) or mode == "swipe",
                "pin_fallback_set": bool(cred.get("fallback_pin_verifier")),
                "fallback_pin_set": bool(cred.get("fallback_pin_verifier")),
                "pattern_dots": PATTERN_DOTS,
                "locked": bool(state.get("locked", True)),
                "reason": state.get("reason", "unknown"),
                "fingerprint": {"provider_ready": fp_ready,
                                "selectable": bool(fp_ready and cred.get("fallback_pin_verifier")),
                                "enrolled": bool(bio.get("enrolled")),
                                "enabled": bool(bio.get("enabled"))},
                "attempt_policy": policy["attempt_policy"],
                "attempt_policy_source": policy.get("source"),
                "unlimited_attempts": not enabled,
                "rate_limit": {
                    "enabled": enabled,
                    "failures": failures,
                    "locked_until": locked_until,
                    "locked_out": locked_out,
                    "remaining_s": max(0, int(locked_until - time.time())),
                },
                "kdf": "scrypt(n=2^14,r=8,p=1,dklen=32)",
                "source": "security_provider",
            }

    # ------------------------------------------------------------- credential
    def _set_secret(self, mode: str, secret: str, fallback_pin: Optional[str] = None,
                    current_secret: Optional[str] = None, confirm_downgrade: bool = False,
                    allow_swipe: bool = False, secret_confirm: Optional[str] = None,
                    fallback_pin_confirm: Optional[str] = None) -> Dict[str, Any]:
        with self._lock:
            old = _read_json(self.cred_path)
            st = self.status()
            if st["rate_limit"]["locked_out"]:
                return {"success": False, "error": "rate_limited",
                        "remaining_s": st["rate_limit"]["remaining_s"]}
            if old.get("verifier"):
                if current_secret is None or not self._verify_locked(old, current_secret):
                    return {"success": False, "error": "current_credential_required",
                            "detail": "the current unlock credential is required to change the lock"}
            if mode not in VALID_MODES:
                return {"success": False, "error": "invalid_mode", "valid": list(VALID_MODES)}
            if mode == "swipe" and not (confirm_downgrade or allow_swipe):
                return {"success": False, "error": "explicit_downgrade_confirmation_required"}
            # Switching into PIN mode with no new secret reuses the stored PIN
            # verifier (the current credential above already proved ownership).
            reuse_pin = (mode == "pin" and not normalize_pin(secret)
                         and old.get("verifier") and old.get("secret_kind") in ("pin", "pattern"))
            if reuse_pin:
                # Reusing an existing PIN verifier only.  A pattern verifier is
                # never relabelled as a PIN (that would let a pattern unlock a
                # PIN-mode device and vice versa).
                if old.get("secret_kind") != "pin":
                    return {"success": False, "error": "pin_required",
                            "detail": "set the PIN first (enter it twice) to use PIN mode"}
                doc = {"schema_version": 1, "mode": "pin",
                       "failures": 0, "locked_until": 0, "updated_at": time.time(),
                       "salt": old.get("salt"), "verifier": old.get("verifier"),
                       "secret_kind": "pin"}
                if old.get("fallback_pin_verifier"):
                    doc["fallback_pin_verifier"] = old["fallback_pin_verifier"]
                    doc["fallback_pin_salt"] = old.get("fallback_pin_salt")
                _atomic_json(self.cred_path, doc)
                self._write_state(True, "credential-set")
                return self.status()
            doc: Dict[str, Any] = {"schema_version": 1, "mode": mode,
                                   "failures": 0, "locked_until": 0,
                                   "updated_at": time.time()}
            pattern = ""
            if mode == "pin":
                pin = normalize_pin(secret)
                if secret_confirm is not None and normalize_pin(secret_confirm) != pin:
                    return {"success": False, "error": "confirmation_mismatch"}
                if _trivial_pin(pin):
                    return {"success": False, "error": "pin_too_weak",
                            "detail": "use at least 4 digits and avoid repeats/sequences"}
                doc["salt"] = secrets.token_hex(16)
                doc["verifier"] = _derive(pin, doc["salt"])
                doc["secret_kind"] = "pin"
                # The PIN is also the fingerprint fallback, so keep a separate
                # fallback verifier for it while the mode is PIN.
                doc["fallback_pin_salt"] = secrets.token_hex(16)
                doc["fallback_pin_verifier"] = _derive(pin, doc["fallback_pin_salt"])
            elif mode == "pattern":
                pattern = normalize_pattern(secret)
                if not pattern:
                    return {"success": False, "error": "invalid_pattern",
                            "detail": "the pattern must use dots 0..8, joined with '-'"}
                # Every pattern path needs both entries, including legacy
                # callers that reach _set_secret directly.
                if secret_confirm is None or normalize_pattern(secret_confirm) != pattern:
                    return {"success": False, "error":
                            "pattern_confirmation_required" if secret_confirm is None
                            else "pattern_confirmation_mismatch"}
                # Deliberately no "too weak" gate: the setup flow confirms the
                # pattern twice, and the owner must not be able to dead-lock the
                # phone by choosing a shape the heuristic dislikes.
                doc["salt"] = secrets.token_hex(16)
                doc["verifier"] = _derive(pattern, doc["salt"])
                doc["secret_kind"] = "pattern"
                doc["pattern_dots"] = PATTERN_DOTS
                # Setting a pattern must not silently drop the PIN fallback
                # (needed to switch to fingerprint or PIN mode without a
                # credential blank).  Preserve the previous PIN if one exists.
                old_pin = old.get("fallback_pin_verifier"), old.get("fallback_pin_salt")
                if old_pin[0] and old_pin[1]:
                    doc["fallback_pin_verifier"] = old_pin[0]
                    doc["fallback_pin_salt"] = old_pin[1]
            elif mode == "fingerprint":
                pin = normalize_pin(fallback_pin)
                if secret_confirm is not None and normalize_pin(secret_confirm) != pin:
                    return {"success": False, "error": "confirmation_mismatch"}
                if not pin or _trivial_pin(pin):
                    return {"success": False, "error": "fingerprint_requires_pin_fallback",
                            "detail": "set a PIN (>=4 digits) as the fingerprint fallback"}
                fp = __import__("fingerprint_provider").handle("status", {})
                if not fp.get("ready"):
                    return {"success": False, "error": "fingerprint_provider_unavailable",
                            "detail": fp.get("blocker")}
                doc["fallback_pin_salt"] = secrets.token_hex(16)
                doc["fallback_pin_verifier"] = _derive(pin, doc["fallback_pin_salt"])
                doc["provider"] = fp.get("provider_id") or "secure-fingerprint"
            _atomic_json(self.cred_path, doc)
            if mode == "fingerprint":
                # Keep the biometric document in sync with the mode change.
                bdoc = self._biometric_doc()
                bdoc["schema_version"] = 1
                bdoc["updated_at"] = time.time()
                _atomic_json(self.biometric_path, bdoc, 0o600)
            self._write_state(True, "credential-set")
            result = self.status()
            if pattern:
                result["pattern_normalized"] = pattern
            return result

    def set_mode(self, mode: str, secret: str = "", **kw) -> Dict[str, Any]:
        # The two-entry guard is a property of the mode, not of the verb: any
        # path that sets a pattern or PIN must confirm it first so a mistyped
        # credential can never be stored (and the phone never dead-locks).
        confirm = kw.pop("secret_confirm", None)
        if mode == "pattern":
            return self.set_pattern(secret, confirm, current_secret=kw.pop("current_secret", None))
        if mode == "pin":
            cur = kw.pop("current_secret", None)
            if not str(secret or "").strip():
                return self._set_secret("pin", "", current_secret=cur, allow_swipe=True)
            return self.set_pin(secret, confirm, current_secret=cur)
        return self._set_secret(mode, secret, **kw)

    def set_pattern(self, pattern: str, pattern_confirm: Optional[str] = None,
                    current_secret: Optional[str] = None) -> Dict[str, Any]:
        # Confirmation is checked BEFORE the current credential so a
        # mis-entered pattern can never be enabled (dead-lock guard).
        if str(pattern_confirm or "") == "":
            return {"success": False, "error": "pattern_confirmation_required",
                    "detail": "enter the pattern twice; the confirmation prevents a dead-lock"}
        first, second = normalize_pattern(pattern), normalize_pattern(pattern_confirm)
        if not first or not second:
            return {"success": False, "error": "invalid_pattern",
                    "detail": "the pattern must use dots 0..8"}
        if first != second:
            return {"success": False, "error": "pattern_confirmation_mismatch",
                    "detail": "the two patterns do not match; nothing was changed"}
        # Check the confirmed pattern itself, not only the legacy entry path.
        res = self._set_secret("pattern", first, current_secret=current_secret,
                               secret_confirm=first, allow_swipe=True)
        if res.get("success"):
            res["pattern_confirmations"] = 2
        return res

    def set_pin(self, pin: str, pin_confirm: Optional[str] = None,
                current_secret: Optional[str] = None) -> Dict[str, Any]:
        if str(pin_confirm or "") == "":
            return {"success": False, "error": "pin_confirmation_required",
                    "detail": "enter the PIN twice"}
        res = self._set_secret("pin", pin, current_secret=current_secret,
                               secret_confirm=pin_confirm, allow_swipe=True)
        if res.get("success"):
            res["pin_confirmations"] = 2
        return res

    # ------------------------------------------------------------- verifying
    def _verify_doc(self, cred: Dict[str, Any], secret: str, kind: str) -> bool:
        """Constant-time verification of one named verifier pair."""
        salt = cred.get((kind + "_salt") if kind else "salt")
        verifier = cred.get((kind + "_verifier") if kind else "verifier")
        if not salt or not verifier or not secret:
            return False
        try:
            got = _derive(secret, salt)
            return hmac.compare_digest(got, verifier)
        except Exception:
            return False

    def _verify_locked(self, cred: Dict[str, Any], secret: str) -> bool:
        """Mode-aware credential check (never accepts a pattern as a PIN)."""
        mode = cred.get("mode", "swipe")
        if mode == "fingerprint":
            return self._verify_doc(cred, normalize_pin(secret), "fallback_pin")
        if mode == "pattern":
            return self._verify_doc(cred, normalize_pattern(secret), "")
        if mode == "pin":
            return self._verify_doc(cred, normalize_pin(secret), "")
        return False

    def _record_failure(self) -> Dict[str, Any]:
        cred = _read_json(self.cred_path)
        failures = int(cred.get("failures", 0) or 0) + 1
        until = 0.0
        if self._policy()["attempt_policy"] == "limited" and failures >= MAX_FAILURES:
            until = time.time() + LOCKOUT_BASE_S * (2 ** min(failures - MAX_FAILURES, 10))
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
            if mode == "fingerprint":
                # A plain PIN submitted here is the fallback; a genuine
                # biometric result goes through unlock_biometric().
                ok = self._verify_locked(cred, secret or "")
                via = "pin-fallback"
            else:
                ok = self._verify_locked(cred, secret or "")
                via = mode
            if not ok:
                r = self._record_failure()
                return {"success": False, "error": "invalid_credential",
                        "failures": r["failures"],
                        "locked_until": r["locked_until"], "locked": True,
                        "attempt_policy": state["attempt_policy"],
                        "unlimited_attempts": state["unlimited_attempts"]}
            cred["failures"] = 0
            cred["locked_until"] = 0
            _atomic_json(self.cred_path, cred)
            self._write_state(False, "credential-verified")
            return {"success": True, "unlocked": True, "locked": False, "via": via}

    def unlock_biometric(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """Consume a token minted by the trusted biometric broker."""
        with self._lock:
            cred = _read_json(self.cred_path)
            state = self.status()
            if cred.get("mode") != "fingerprint":
                return {"success": False, "error": "biometric_mode_not_active", "locked": True}
            if state["rate_limit"]["locked_out"]:
                return {"success": False, "error": "rate_limited", "locked": True,
                        "remaining_s": state["rate_limit"]["remaining_s"]}
            ok = isinstance(result, dict) and result.get("success") is True \
                and result.get("authenticated") is True
            if not ok:
                r = self._record_failure()
                return {"success": False, "error": "biometric_rejected",
                        "failures": r["failures"], "locked": True}
            cred["failures"] = 0
            cred["locked_until"] = 0
            _atomic_json(self.cred_path, cred)
            self._write_state(False, "biometric-verified")
            return {"success": True, "unlocked": True, "locked": False, "via": "fingerprint"}

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
    if verb == "unlock-biometric":
        return p.unlock_biometric(params.get("biometric_result"))
    if verb == "set-attempt-policy":
        return p.set_attempt_policy(params.get("policy"))
    if verb in ("biometric-status", "biometric-get"):
        return p.biometric_status(p.status().get("fingerprint", {}).get("provider_ready", False))
    if verb in ("set-biometric-unlock", "biometric-set"):
        return p.set_biometric(enabled=bool(params.get("enabled", False)),
                               enrolled=params.get("enrolled"))
    if verb == "set-pattern":
        return p.set_pattern(str(params.get("pattern", params.get("secret", ""))),
                             params.get("pattern_confirm", params.get("secret_confirm")),
                             current_secret=params.get("current_secret"))
    if verb == "set-pin":
        return p.set_pin(str(params.get("pin", params.get("secret", ""))),
                         params.get("pin_confirm", params.get("secret_confirm")),
                         current_secret=params.get("current_secret"))
    if verb in ("set-mode", "set-credential"):
        mode = params.get("mode")
        return p.set_mode(str(mode), str(params.get("secret", "")),
                          fallback_pin=params.get("fallback_pin"),
                          current_secret=params.get("current_secret"),
                          confirm_downgrade=bool(params.get("confirm_downgrade")),
                          secret_confirm=params.get("secret_confirm"))
    return {"success": False, "error": "unknown security verb", "verb": verb}
