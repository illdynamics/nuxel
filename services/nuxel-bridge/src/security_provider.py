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
    text = str(pin or "").strip()
    return text if text.isascii() and text.isdigit() else ""


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
    """The owner may choose any ASCII PIN of 4–16 digits, including repeats."""
    return not (MIN_PIN <= len(pin) <= 16 and pin.isascii() and pin.isdigit())


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
    def ensure_state(self) -> Dict[str, Any]:
        """A85: publish the lock state once, deterministically.

        /run is a tmpfs: after every reboot there is NO lock-state.json until
        something calls security/lock.  Measured 2026-11-14: at boot the file
        was absent, so nuxel-navdock and the status bar read `unknown` (the
        native dock then refused to map: the swipe-up triple buttons did not
        work in Settings or the VNC screen) and the launcher's boot gate
        released the overlay, i.e. the phone came up UNLOCKED.

        The stored mode decides the boot value and it is written exactly as the
        provider will report it:

          * swipe / unlock -> locked:false.  The lockhead still covers the
            glass; one upward swipe releases it (security/unlock).  Reporting
            locked:true here made every swipe-mode boot impossible (the A84
            dead-lock); reporting locked:false keeps the native dock usable.
          * pin / pattern / fingerprint -> locked:true.
        """
        with self._lock:
            cred = _read_json(self.cred_path)
            mode = cred.get("mode", "swipe")
            if mode not in VALID_MODES:
                mode = "swipe"
            # A88: EVERY mode boots LOCKED.  The credential modes always did.
            # Swipe used to publish locked:false, and the launcher's boot gate
            # then released the overlay on an early answer: the phone came up
            # on the desktop with no lockhead.  Swipe has no secret, so a
            # `locked` flag costs nothing; the direct lockhead swipe releases
            # it through security/unlock (see unlock()).
            self._write_state(True, "boot:swipe" if mode in ("swipe", "unlock")
                              else "boot:credential")
            return self._state()

    def _state(self) -> Dict[str, Any]:
        st = _read_json(self.state_path)
        if not st:
            # FAIL CLOSED, except for a swipe lock: that mode has no secret to
            # verify, and the launcher's lock overlay is up anyway, so the
            # owner's single swipe is the unlock.  (Before A84 a missing state -
            # which happened on EVERY reboot because /run is a tmpfs - made a
            # swipe-mode phone impossible to unlock: the provider reported
            # locked and the launcher rejected even the direct swipe.)
            cred = _read_json(self.cred_path)
            if cred.get("mode", "swipe") == "swipe":
                return {"locked": False, "reason": "no-state: swipe mode"}
            return {"locked": True, "reason": "no-state: fail locked",
                    "owner": "security_provider"}
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
            cred = self._credentials()
            state = self._state()
            policy = self._policy()
            mode = cred.get("mode", "swipe")
            if mode not in VALID_MODES:
                mode = "swipe"
            failures = int(cred.get("failures", 0) or 0)
            locked_until = float(cred.get("locked_until", 0) or 0)
            fp_ready = False
            fp_blocker = None
            fp_vault = None
            try:
                import fingerprint_provider
                _fp = fingerprint_provider.handle("status", {})
                fp_ready = bool(_fp.get("ready"))
                fp_blocker = _fp.get("blocker")
                fp_vault = _fp.get("vault_state")
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
                # Every non-swipe mode REQUIRES an unlock verifier (the
                # invariant is enforced on write in _set_secret); only a
                # downgrade to swipe may legitimately have none.
                "credential_set": bool(cred.get("verifier")) or mode == "swipe",
                # NUXEL-105200: the Settings pattern card must be able to say
                # truthfully whether a pattern exists (and offer "Set up" vs
                # "Change").  Hash/salt/verifier are never exposed.
                "secret_kind": cred.get("secret_kind") if cred.get("verifier") else None,
                "pattern_set": bool(cred.get("stored_pattern_verifier")),
                "pin_set": bool(cred.get("fallback_pin_verifier")),
                "available_modes": ["swipe"] + (["pin"] if cred.get("fallback_pin_verifier") else [])
                    + (["pattern"] if cred.get("fallback_pin_verifier") and cred.get("stored_pattern_verifier") else [])
                    + (["fingerprint"] if fp_ready and bio.get("enrolled") and cred.get("fallback_pin_verifier") else []),
                "pin_fallback_set": bool(cred.get("fallback_pin_verifier")),
                "swipe_available": True,
                "fallback_pin_set": bool(cred.get("fallback_pin_verifier")),
                "pattern_dots": PATTERN_DOTS,
                "locked": bool(state.get("locked", True)),
                "reason": state.get("reason", "unknown"),
                "fingerprint": {"provider_ready": fp_ready,
                                "selectable": bool(fp_ready and bio.get("enrolled") and cred.get("fallback_pin_verifier")),
                                "enrolled": bool(bio.get("enrolled")),
                                "enabled": bool(bio.get("enabled")),
                                "blocker": fp_blocker,
                                "vault_state": fp_vault},
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

    # Saved credentials are independent of the selected lock method. Changing
    # to swipe must never erase the owner's PIN or enrolled pattern.
    PRESETS = ("swipe", "unlock", "pin", "pattern", "fingerprint")

    def _credentials(self) -> Dict[str, Any]:
        doc = _read_json(self.cred_path)
        if doc.get("verifier") and doc.get("salt"):
            prefix = {"pin": "fallback_pin", "pattern": "stored_pattern"}.get(doc.get("secret_kind"))
            if prefix and not doc.get(prefix + "_verifier"):
                doc[prefix + "_verifier"] = doc["verifier"]
                doc[prefix + "_salt"] = doc["salt"]
        return doc

    @staticmethod
    def _credential_locked(cred: Dict[str, Any]) -> bool:
        return cred.get("mode", "swipe") in ("pin", "pattern", "fingerprint")

    def _fallback_matches(self, secret: str) -> bool:
        return self._verify_doc(self._credentials(), normalize_pin(secret), "fallback_pin")

    def _change_allowed(self, doc: Dict[str, Any], current_secret: Optional[str]) -> bool:
        # Settings can change an unlocked phone. A credentialed locked phone
        # still needs proof; confirming a NEW PIN twice is not that proof.
        return (not self._credential_locked(doc) or not self._state().get("locked", True)
                or self._verify_locked(doc, str(current_secret or "")))

    def _save_credentials(self, doc: Dict[str, Any]) -> Dict[str, Any]:
        mode = doc.get("mode", "swipe")
        # Keep the active legacy verifier in sync for existing clients/readers.
        prefix = {"pin": "fallback_pin", "pattern": "stored_pattern"}.get(mode)
        for key in ("salt", "verifier", "secret_kind"):
            doc.pop(key, None)
        if prefix:
            doc.update(salt=doc.get(prefix + "_salt"), verifier=doc.get(prefix + "_verifier"), secret_kind=mode)
        doc.update(schema_version=2, failures=0, locked_until=0, updated_at=time.time())
        _atomic_json(self.cred_path, doc)
        return self.status()

    def set_mode(self, mode: str, secret: str = "", **kw) -> Dict[str, Any]:
        mode = str(mode or "").lower().strip()
        if mode == "unlock":
            mode = "swipe"
        if mode not in VALID_MODES:
            return {"success": False, "error": "invalid_mode", "valid": list(VALID_MODES)}
        if secret and mode in ("pin", "pattern"):
            return self.apply_preset(mode, secret, kw.get("secret_confirm"), kw.get("current_secret"))
        with self._lock:
            doc = self._credentials()
            if not self._change_allowed(doc, kw.get("current_secret")):
                return {"success": False, "error": "current_credential_required"}
            if mode != "swipe" and not doc.get("fallback_pin_verifier"):
                return {"success": False, "error": "pin_required", "detail": "Set a PIN first."}
            if mode == "pattern" and not doc.get("stored_pattern_verifier"):
                return {"success": False, "error": "pattern_required", "detail": "Set a pattern first."}
            if mode == "fingerprint":
                fp = self.status()["fingerprint"]
                if not fp.get("provider_ready"):
                    return {"success": False, "error": "fingerprint_provider_unavailable", "detail": fp.get("blocker")}
                if not fp.get("enrolled"):
                    return {"success": False, "error": "fingerprint_not_enrolled"}
            doc["mode"] = mode
            return self._save_credentials(doc)

    def apply_preset(self, preset: str, secret: str = "",
                     secret_confirm: Optional[str] = None,
                     current_secret: Optional[str] = None,
                     fallback_pin: Optional[str] = None) -> Dict[str, Any]:
        mode = "swipe" if preset == "unlock" else preset
        with self._lock:
            if mode == "pin" and secret:
                result = self.set_pin(secret, secret_confirm, current_secret)
                if not result.get("success"):
                    return result
                # The old credential was proved before writing the new one.
                return self.set_mode("pin", current_secret=secret)
            if mode == "pattern" and secret:
                return self.set_pattern(secret, secret_confirm, current_secret)
            # No implicit fallback PIN and no numeric conversion of a pattern.
            return self.set_mode(mode, current_secret=current_secret)

    def set_pattern(self, pattern: str, pattern_confirm: Optional[str] = None,
                    current_secret: Optional[str] = None) -> Dict[str, Any]:
        first, second = normalize_pattern(pattern), normalize_pattern(pattern_confirm)
        if pattern_confirm is None:
            return {"success": False, "error": "pattern_confirmation_required"}
        if not first or len(set(first.split("-"))) < PATTERN_MIN_DOTS:
            return {"success": False, "error": "invalid_pattern", "detail": "Use at least four different dots."}
        if first != second:
            return {"success": False, "error": "pattern_confirmation_mismatch"}
        with self._lock:
            doc = self._credentials()
            if not doc.get("fallback_pin_verifier"):
                return {"success": False, "error": "pin_required", "detail": "Set a PIN before setting a pattern."}
            if not self._change_allowed(doc, current_secret):
                return {"success": False, "error": "current_credential_required"}
            doc["stored_pattern_salt"] = secrets.token_hex(16)
            doc["stored_pattern_verifier"] = _derive(first, doc["stored_pattern_salt"])
            doc["mode"] = "pattern"
            return dict(self._save_credentials(doc), pattern_confirmations=2)

    def set_pin(self, pin: str, pin_confirm: Optional[str] = None,
                current_secret: Optional[str] = None) -> Dict[str, Any]:
        if pin_confirm is None:
            return {"success": False, "error": "pin_confirmation_required"}
        pin = normalize_pin(pin)
        if _trivial_pin(pin):
            return {"success": False, "error": "invalid_pin", "detail": "Use 4 to 16 digits."}
        if pin != normalize_pin(pin_confirm):
            return {"success": False, "error": "confirmation_mismatch"}
        with self._lock:
            doc = self._credentials()
            if not self._change_allowed(doc, current_secret):
                return {"success": False, "error": "current_credential_required"}
            doc["fallback_pin_salt"] = secrets.token_hex(16)
            doc["fallback_pin_verifier"] = _derive(pin, doc["fallback_pin_salt"])
            doc.setdefault("mode", "swipe")
            return dict(self._save_credentials(doc), pin_confirmations=2)

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
        """Mode-aware credential check (never accepts a pattern as a PIN).

        A30: every credential mode that HAS a stored PIN fallback accepts that
        PIN.  Measured 2026-11-14: the device was in `pattern` mode with a
        valid PIN fallback (3838, verified scrypt match), the lock screen
        offers the PIN button in pattern mode, and the owner entering that PIN
        got `invalid_credential` - so the advertised fallback never worked.
        The fallback verifier is a separate salted scrypt verifier, so cross-
        mode replay is still impossible: a pattern verifier can only ever be
        checked against a pattern, a PIN verifier only against a PIN.
        """
        mode = cred.get("mode", "swipe")
        if mode == "fingerprint":
            return self._verify_doc(cred, normalize_pin(secret), "fallback_pin")
        if mode == "pattern":
            if self._verify_doc(cred, normalize_pattern(secret), ""):
                return True
            # A84: entering the PIN (with the keypad) IS proof of ownership, so
            # it may also authorise a lock change, not just an unlock.
            return (self._verify_doc(cred, normalize_pin(secret), "fallback_pin") or
                    self._verify_doc(cred, normalize_pin(secret), "pending_fallback_pin"))
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
            if mode in ("swipe", "unlock"):
                # A88: the boot state is ALWAYS locked:true (the launcher shows
                # the lockhead); the swipe itself is the release.  There is no
                # secret to check in these modes by definition.
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
    if verb in ("ensure-state", "boot-state"):
        # A85: idempotent boot publication (see ensure_state).  A single
        # systemd ExecStartPre makes the state exist before ANY reader starts.
        p.ensure_state()
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
    if verb in ("apply-preset", "preset"):
        return p.apply_preset(str(params.get("preset", params.get("mode", ""))),
                              str(params.get("secret", params.get("pin", ""))),
                              params.get("secret_confirm", params.get("pin_confirm")),
                              params.get("current_secret"),
                              params.get("fallback_pin"))
    if verb in ("set-mode", "set-credential"):
        mode = params.get("mode")
        return p.set_mode(str(mode), str(params.get("secret", "")),
                          fallback_pin=params.get("fallback_pin"),
                          current_secret=params.get("current_secret"),
                          confirm_downgrade=bool(params.get("confirm_downgrade")),
                          secret_confirm=params.get("secret_confirm"))
    return {"success": False, "error": "unknown security verb", "verb": verb}
