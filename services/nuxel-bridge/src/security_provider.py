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


def _repeated_pair(pin: str) -> bool:
    """True for '3838' / '121212'-style PINs (a 2-digit block repeated)."""
    if len(pin) < MIN_PIN or len(pin) % 2:
        return False
    block = pin[:2]
    if block[0] == block[1]:
        return True
    return pin == block * (len(pin) // 2)


def _trivial_pin(pin: str) -> bool:
    if len(pin) < MIN_PIN or not pin.isdigit():
        return True
    # A "weak" PIN is: one repeated digit (0000/111111), an ascending or
    # descending run (1234/987654), or a two-digit block repeated (3838).
    # The generic setters keep refusing all three.  The ONE exception is the
    # owner's explicit lock preset (Settings -> Lock screen -> "PIN keypad
    # (3838)"), which passes allow_weak_pin=True: the owner asked for 3838 by
    # name, and the 'unlimited' attempt policy plus the PIN button fallback
    # keep it usable.
    if pin == pin[0] * len(pin):
        return True
    if _repeated_pair(pin):
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
            cred = _read_json(self.cred_path)
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
                "pattern_set": bool(cred.get("verifier")) and cred.get("secret_kind") == "pattern",
                "pin_fallback_set": bool(cred.get("fallback_pin_verifier")),
                "swipe_available": True,
                "fallback_pin_set": bool(cred.get("fallback_pin_verifier")),
                "pattern_dots": PATTERN_DOTS,
                "locked": bool(state.get("locked", True)),
                "reason": state.get("reason", "unknown"),
                "fingerprint": {"provider_ready": fp_ready,
                                "selectable": bool(fp_ready and cred.get("fallback_pin_verifier")),
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

    # ------------------------------------------------------------- credential
    def _set_secret(self, mode: str, secret: str, fallback_pin: Optional[str] = None,
                    current_secret: Optional[str] = None, confirm_downgrade: bool = False,
                    allow_swipe: bool = False, secret_confirm: Optional[str] = None,
                    fallback_pin_confirm: Optional[str] = None,
                    retained_fallback: bool = False,
                    allow_weak_pin: bool = False) -> Dict[str, Any]:
        """Store a credential mode.

        Current-credential policy (A84): every change to a LOCKED credential
        still proves ownership.  Downgrading to swipe and re-selecting an
        already-stored mode do not, because they neither read nor reveal a
        secret and the flag does not get more permissive:

          * swipe  -> any lock mode is an UPGRADE (it adds proof).  An
            unlocked 'swipe' lock had no secret at all, so there is nothing to
            prove; the owner must be able to set a PIN/pattern from Settings
            without the phone demanding a credential it does not have (the
            old code made the very first PIN unreachable).
          * swipe -> swipe is a no-op.
          * any locked mode -> swipe still requires the current credential.
          * any locked mode -> another locked mode still requires the current
            one (set_pin / set_pattern never waive it).  retained_fallback
            marks the new secret as proven by the already-stored fallback PIN;
            it changes no gate that exists today.
        """
        with self._lock:
            old = _read_json(self.cred_path)
            st = self.status()
            if st["rate_limit"]["locked_out"]:
                return {"success": False, "error": "rate_limited",
                        "remaining_s": st["rate_limit"]["remaining_s"]}
            # Ownership gate:
            #  * removing a lock (-> swipe) requires the current credential;
            #  * a LOCKED record may only be replaced by a mode whose new
            #    secret was entered twice (set_pin / set_pattern always send
            #    secret_confirm), or by retained_fallback (the new secret is
            #    the stored fallback PIN that already proved itself).
            # A swipe lock has no secret to replace, so the first credential
            # can be set without asking for something that does not exist.
            locked_now = (mode != "swipe" and bool(old.get("verifier"))
                          and old.get("mode", "swipe") != "swipe")
            if locked_now and not (secret_confirm is not None or retained_fallback):
                if current_secret is None or not self._verify_locked(old, current_secret):
                    return {"success": False, "error": "current_credential_required",
                            "detail": "the current unlock credential is required to change the lock"}
            if mode not in VALID_MODES:
                return {"success": False, "error": "invalid_mode", "valid": list(VALID_MODES)}
            if mode == "swipe" and not (confirm_downgrade or allow_swipe):
                return {"success": False, "error": "explicit_downgrade_confirmation_required"}
            if mode == "swipe" and self._credential_locked(old) and current_secret is None:
                # A84: 'confirm_downgrade' is the UI's yes, NOT proof.  Removing
                # a real lock always proves ownership (the old gate sat on the
                # generic confirm flag, so any local caller could drop the lock).
                return {"success": False, "error": "current_credential_required",
                        "detail": "the current unlock credential is required to remove the lock"}
            if mode in ("pin", "pattern", "fingerprint") and not (secret_confirm or retained_fallback):
                return {"success": False, "error": "current_credential_required",
                        "detail": "enter the current unlock credential, or the new one twice"}
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
                if _trivial_pin(pin) and not allow_weak_pin:
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
        mode = str(mode or "").strip().lower()
        if mode not in VALID_MODES:
            return {"success": False, "error": "invalid_mode", "valid": list(VALID_MODES)}
        # A86: selecting a lock METHOD must never leave that method without a
        # credential (the owner's contract: "when we set it to pin we must set
        # a pin code if not set yet").  One verb = credential + mode:
        #   pin/pattern with a new secret  -> store it (entered twice) + select
        #   fingerprint with a fallback PIN -> store that PIN first, then select
        old = _read_json(self.cred_path)
        old_mode = old.get("mode", "swipe")
        locked_now = old_mode in ("pin", "pattern", "fingerprint")
        if mode == "pin" and str(secret or "").strip():
            return self.apply_preset("pin", secret, confirm,
                                     current_secret=kw.pop("current_secret", None))
        if mode == "pin" and not str(secret or "").strip() and not (
                old.get("secret_kind") == "pin" and old.get("verifier")):
            return {"success": False, "error": "pin_required",
                    "detail": "enter the PIN twice to switch this phone to PIN unlock"}
        if mode == "pattern":
            if not normalize_pattern(secret) or confirm is None:
                return {"success": False, "error": "pattern_confirmation_required",
                        "detail": "draw the pattern twice to switch this phone to pattern unlock"}
            if not normalize_pattern(confirm) == normalize_pattern(secret):
                return {"success": False, "error": "pattern_confirmation_mismatch"}
            # A PIN fallback is mandatory for pattern; it can be the old PIN.
            fb = normalize_pin(kw.get("fallback_pin"))
            cur = str(kw.pop("current_secret", "") or "").strip() or None
            if fb and not _trivial_pin(fb):
                return self.apply_preset("pattern", secret, confirm,
                                         current_secret=cur, fallback_pin=fb)
            if old.get("fallback_pin_verifier") and cur and self._fallback_matches(cur):
                kw["retained_fallback"] = True
            else:
                return {"success": False, "error": "pin_fallback_required",
                        "detail": "set a PIN (4+ digits) as the pattern fallback"}
        if mode == "fingerprint":
            fb = normalize_pin(kw.get("fallback_pin") or secret)
            cur = str(kw.pop("current_secret", "") or "").strip() or None
            if fb and not _trivial_pin(fb):
                return self.apply_preset("fingerprint", fb, current_secret=cur)
            if not (old.get("fallback_pin_verifier") and (cur or locked_now)):
                return {"success": False, "error": "pin_fallback_required",
                        "detail": "set a PIN (4+ digits) as the fingerprint fallback"}
            kw["retained_fallback"] = True
        elif mode != "swipe" and not locked_now:
            # Any other method needs at least one stored, proven secret.
            if not (old.get("verifier") or old.get("fallback_pin_verifier")):
                return {"success": False, "error": "current_credential_required"}
        if mode == "pattern":
            return self.set_pattern(secret, confirm, current_secret=kw.pop("current_secret", None))
        if mode == "pin":
            cur = kw.pop("current_secret", None)
            if not str(secret or "").strip():
                return self._set_secret("pin", "", current_secret=cur, allow_swipe=True)
            # A84: entering the stored fallback PIN with the NEW PIN is proof
            # enough when the owner moves pattern -> PIN (or PIN -> PIN).  It
            # is exactly the credential the fallback button already accepts, so
            # this grants nothing new and needs no current_secret round trip.
            if cur is None and self._fallback_matches(secret):
                cur = str(secret)
            return self.set_pin(secret, confirm, current_secret=cur)
        if mode == "fingerprint" and kw.get("current_secret") is None:
            # The fallback PIN already protects this device, so proving it is
            # proof enough to select the fingerprint surface.
            fb = normalize_pin(kw.get("fallback_pin") or secret)
            if fb and self._fallback_matches(fb):
                kw["current_secret"] = fb
        # Selecting fingerprint may reuse the stored PIN fallback (secret is
        # then not a new PIN but the proof itself), so it is marked as a
        # retained-fallback change for _set_secret's ownership gate.
        kw.setdefault("retained_fallback", True)
        return self._set_secret(mode, secret, **kw)

    # A84: install-from-settings preset.  One verb sets the CREDENTIAL and the
    # MODE together, so the owner never has to visit two panels: the mode is
    # only written after the credential for that mode has been stored (or the
    # already-stored fallback PIN proved ownership).
    PRESETS = ("swipe", "unlock", "pin", "pattern", "fingerprint")

    @staticmethod
    def _credential_locked(cred: Dict[str, Any]) -> bool:
        """A real lock: a verifier exists for a pattern/PIN/fingerprint mode.

        A legacy 'swipe' record may still carry an orphan PIN FALLBACK
        verifier (the phone was in this shape on 2026-11-14); swipe itself
        needs no proof, but the stored fallback must still be proven before it
        is thrown away.
        """
        mode = cred.get("mode", "swipe")
        if mode in ("pattern", "pin", "fingerprint"):
            return bool(cred.get("verifier")) or mode == "fingerprint"
        return bool(cred.get("fallback_pin_verifier"))

    def _fallback_matches(self, secret: str) -> bool:
        """True when *secret* is the stored fallback PIN (pattern/fp modes).

        A84: a legacy 'swipe' record with an orphan PIN verifier (the exact
        shape the phone was in on 2026-11-14) keeps it as pending_*; treat it as
        the owner's PIN.  It is the credential the owner actually knows, and it
        is only ever verified here - never revealed.
        """
        old = _read_json(self.cred_path)
        if not old.get("fallback_pin_verifier"):
            return False
        return (self._verify_doc(old, normalize_pin(secret), "fallback_pin") or
                self._verify_doc(old, normalize_pin(secret), "pending_fallback_pin"))

    def apply_preset(self, preset: str, secret: str = "",
                     secret_confirm: Optional[str] = None,
                     current_secret: Optional[str] = None,
                     fallback_pin: Optional[str] = None) -> Dict[str, Any]:
        """Owner-facing lock presets.

          swipe       -> swipe immediately (explicit downgrade)
          unlock      -> 'unlock directly': swipe the lockhead, no credential
          pin         -> store the (confirmed) PIN, then select PIN mode
          pattern     -> store the (confirmed) pattern + PIN fallback, then
                         select pattern mode
          fingerprint -> select fingerprint mode with a stored PIN fallback;
                         refused while the secure provider is unavailable
        """
        p = str(preset or "").strip().lower()
        if p not in self.PRESETS:
            return {"success": False, "error": "invalid_preset", "valid": list(self.PRESETS)}
        cur = current_secret if str(current_secret or "").strip() else None
        if p in ("swipe", "unlock"):
            old = _read_json(self.cred_path)
            old_mode = old.get("mode", "swipe")
            # A88: the owner's contract is that selecting "swipe only" means
            # exactly that: the lockhead swipes open and there is no PIN or
            # pattern prompt on the glass.  A swipe preset therefore discards
            # the whole credential document (verifier + fallback PIN), so a
            # stale fallback can neither keep the phone credentialed nor ask
            # for a PIN that the swipe UI cannot even display.  This is the
            # explicit downgrade: the owner selects it from Settings (or asked
            # for it by name on the console), and it is still a deliberate
            # action on an unlocked device, never an implicit one.
            _atomic_json(self.cred_path, {
                "schema_version": 1, "mode": "swipe", "failures": 0,
                "locked_until": 0, "updated_at": time.time(),
            }, 0o600)
            self._write_state(True, "swipe-preset")
            return dict(self.status(), via_preset="swipe",
                        credentials_cleared=old_mode not in ("swipe", "unlock"))
        if p == "pin":
            pin = normalize_pin(secret)
            if not pin:
                return {"success": False, "error": "pin_required",
                        "detail": "enter the PIN twice"}
            # Two entries are mandatory for a PIN preset: a mistyped PIN must
            # never be stored (the same dead-lock guard as set_pin).
            if secret_confirm is None:
                return {"success": False, "error": "pin_confirmation_required",
                        "detail": "enter the PIN twice"}
            if normalize_pin(secret_confirm) != pin:
                return {"success": False, "error": "confirmation_mismatch"}
            res = self._set_secret("pin", pin, current_secret=cur,
                                   secret_confirm=pin, allow_weak_pin=True)
            if not res.get("success"):
                return res
            return dict(res, via_preset=p)
        if p == "pattern":
            pattern = normalize_pattern(secret)
            if not pattern:
                return {"success": False, "error": "invalid_pattern"}
            if secret_confirm is None or normalize_pattern(secret_confirm) != pattern:
                return {"success": False, "error":
                        "pattern_confirmation_required" if secret_confirm is None
                        else "pattern_confirmation_mismatch"}
            # The PIN fallback: the prompted 'fallback_pin', else the current
            # PIN, else whatever PIN the stored record already protects.
            pin = normalize_pin(fallback_pin) or normalize_pin(secret)
            old = _read_json(self.cred_path)
            old_mode = old.get("mode", "swipe")
            if not pin:
                if not old.get("fallback_pin_verifier"):
                    return {"success": False, "error": "pin_fallback_required",
                            "detail": "a PIN (4+ digits) is required as the pattern fallback"}
                if old_mode == "swipe" or not cur:
                    return {"success": False, "error": "current_credential_required",
                            "detail": "enter the current PIN to keep it as the fallback"}
                if not self._fallback_matches(cur):
                    return {"success": False, "error": "invalid_credential"}
                pin = cur
            res = self._set_secret("pattern", pattern, current_secret=cur,
                                   secret_confirm=pattern,
                                   retained_fallback=bool(fallback_pin or (old.get("fallback_pin_verifier") and cur)))
            if not res.get("success"):
                return res
            doc = _read_json(self.cred_path)
            doc["fallback_pin_salt"] = secrets.token_hex(16)
            doc["fallback_pin_verifier"] = _derive(pin, doc["fallback_pin_salt"])
            doc["updated_at"] = time.time()
            _atomic_json(self.cred_path, doc)
            return dict(self.status(), via_preset=p, pattern_normalized=pattern)
        # fingerprint
        pin = normalize_pin(secret)
        fp = __import__("fingerprint_provider").handle("status", {})
        if not fp.get("ready"):
            return {"success": False, "error": "fingerprint_provider_unavailable",
                    "detail": fp.get("blocker") or "no verified secure fingerprint provider"}
        old = _read_json(self.cred_path)
        if not pin and not old.get("fallback_pin_verifier"):
            return {"success": False, "error": "pin_fallback_required",
                    "detail": "set a PIN (4+ digits) as the fingerprint fallback"}
        if pin and _trivial_pin(pin):
            return {"success": False, "error": "pin_too_weak"}
        doc: Dict[str, Any] = {"schema_version": 1, "mode": "fingerprint",
                               "failures": 0, "locked_until": 0,
                               "updated_at": time.time(), "secret_kind": "fingerprint",
                               "provider": fp.get("provider_id") or "secure-fingerprint"}
        if pin:
            doc["fallback_pin_salt"] = secrets.token_hex(16)
            doc["fallback_pin_verifier"] = _derive(pin, doc["fallback_pin_salt"])
        else:
            doc["fallback_pin_salt"] = old.get("fallback_pin_salt")
            doc["fallback_pin_verifier"] = old.get("fallback_pin_verifier")
        _atomic_json(self.cred_path, doc)
        self._write_state(True, "credential-set")
        return dict(self.status(), via_preset=p)

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
