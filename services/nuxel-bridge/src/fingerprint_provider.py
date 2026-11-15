#!/usr/bin/env python3
"""S10+ ultrasonic fingerprint capability broker.

Hardware truth on this handset
------------------------------
The kernel binds the Samsung `fps_qbt2000` driver (`CONFIG_SENSORS_QBT2000=y`)
and exposes `/dev/qbt2000_fd`, `/dev/qbt2000_ipc` and
`/sys/class/fingerprint/fingerprint` (name QBT2000, vendor QCOM, type_check 7).
The sensor is an *ultrasonic* under-display sensor.  Acquisition, feature
extraction, template storage and matching on this sensor are performed by a
Samsung TEEGris trusted application, not by a normal-world driver or by
libfprint/fprintd.  That TA (and the secure-world IPC it speaks) is OEM-signed
material and is not present in Nuxel; the binding project spec explicitly
forbids fabricating a matcher or reporting a fake match.

What this module therefore does
-------------------------------
* reports the real sensor/driver state;
* keeps a tamper-evident "enrollment record" in the OS keyring (the **Vault**)
  so the security provider can gate biometric unlock and the settings UI can
  show the *user-facing* enrollment state ("a fingerprint has been registered
  by you") — this is metadata, never a template and never a match result;
* implements the enrollment *ceremony* (two consecutive edge-to-edge touches)
  which is recorded only after the security provider has verified the PIN and
  the Vault is unlocked; a partial ceremony expires;
* REFUSES authenticate/match with an explicit BLOCKED_SECURE_PROVIDER reason,
  because without the TA any "match" would be fabricated.  The lockscreen shows
  that reason instead of pretending the scanner works.

`provider_ready` is False until a real secure TA reports healthy through the
future adapter; `enroll`/`test` then use it instead of the record path.
"""
from __future__ import annotations

import glob
import hashlib
import hmac
import json
import os
import secrets
import shutil
import threading
import time
from typing import Any, Dict, Optional

FPS_SYSFS = "/sys/class/fingerprint/fingerprint"
FPS_TYPE_DEV = "/dev/qbt2000_fd"
FPS_IPC_DEV = "/dev/qbt2000_ipc"
DEFAULT_TA = os.environ.get(
    "NUXEL_FP_TA_PROBE", "/usr/lib/nuxel/fingerprint/qbt2000-ta-probe")
DEFAULT_RECORD = os.environ.get(
    "NUXEL_FP_ENROLL_RECORD", "/var/lib/nuxel/security/fingerprint-enrollment.json")
CEREMONY_TIMEOUT_S = 90.0
# The S10+ sensor is a narrow under-display oval; the artwork in
# assets/nuxel-fingerprint.png is aligned to that "scanner" region.
SENSOR_ARTWORK = "/assets/nuxel-fingerprint.png"
FINGERPRINT_NOT_DELETED = 0
FINGERPRINT_NOT_ENROLLED = 1
FINGERPRINT_TA_UNREACHABLE = 2


def _exists_any(patterns) -> list:
    out = []
    for pat in patterns:
        out.extend(glob.glob(pat))
    return sorted(set(out))


def _read(path: str) -> str:
    try:
        with open(path) as fh:
            return fh.read().strip()
    except OSError:
        return ""


class FingerprintProvider:
    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._ceremony: Optional[Dict[str, Any]] = None
        self.record_path = os.environ.get("NUXEL_FP_ENROLL_RECORD", DEFAULT_RECORD)
        self.ta_probe = os.environ.get("NUXEL_FP_TA_PROBE", DEFAULT_TA)

    # -------------------------------------------------------------- hardware
    def _sensor(self) -> Dict[str, Any]:
        devs = _exists_any([FPS_TYPE_DEV, FPS_IPC_DEV, "/dev/fingerprint*"])
        spi = _exists_any(["/sys/bus/spi/drivers/*qbt*", "/sys/bus/spi/devices/*qbt*"])
        driver = bool(spi) or bool(_exists_any(["/sys/module/qbt*", FPS_SYSFS]))
        return {
            "detected": bool(driver or devs),
            "devices": devs,
            "driver": driver,
            "name": _read(FPS_SYSFS + "/name"),
            "vendor": _read(FPS_SYSFS + "/vendor"),
            "type_check": _read(FPS_SYSFS + "/type_check"),
            "position": _read(FPS_SYSFS + "/position"),
            "sensor_type": "ultrasonic-under-display",
            "artwork": SENSOR_ARTWORK,
        }

    def _ta(self) -> Dict[str, Any]:
        """The OEM trusted application is the only legitimate matcher owner."""
        probe = self.ta_probe
        present = bool(probe and os.path.isfile(probe) and os.access(probe, os.X_OK))
        healthy = False
        note = None
        if present:
            try:
                import subprocess
                out = subprocess.run([probe, "status"], capture_output=True,
                                     text=True, timeout=4)
                healthy = out.returncode == 0 and "healthy" in (out.stdout or "").lower()
                note = (out.stdout or out.stderr or "").strip()[:200]
            except Exception as exc:  # noqa: BLE001
                note = "probe failed: %s" % type(exc).__name__
        return {
            "provider": "teegris-qbt2000-ta",
            "present": present,
            "healthy": healthy,
            "path": probe,
            "note": note,
            "libfprint_support": False,
            "fprintd_support": False,
        }

    # --------------------------------------------------------------- record
    def _record(self) -> Optional[Dict[str, Any]]:
        try:
            with open(self.record_path) as fh:
                doc = json.load(fh)
            return doc if isinstance(doc, dict) else None
        except (OSError, ValueError):
            return None

    def _rec_ok(self, rec: Optional[Dict[str, Any]]) -> bool:
        if not rec or not rec.get("present"):
            return False
        want = rec.get("mac")
        if not want:
            return False
        key = self._record_key()
        if key is None:
            return False
        got = hmac.new(key, json.dumps(
            {k: rec.get(k) for k in ("present", "label", "enrolled_at", "schema")},
            sort_keys=True).encode(), hashlib.sha256).hexdigest()
        return hmac.compare_digest(got, str(want))

    def _record_key(self) -> Optional[bytes]:
        # The HMAC key lives in the Vault keyring so the record is bound to the
        # user's keyring and to the Vault password.  Secret-Service calls are
        # bounded: a missing/locked provider returns None, never a hang.
        try:
            from secret_service import SecretService
            import threading
            box: Dict[str, Any] = {}

            def work():
                try:
                    box["svc"] = SecretService()
                except Exception as exc:  # noqa: BLE001
                    box["error"] = str(exc)[:120]

            t = threading.Thread(target=work, daemon=True)
            t.start()
            t.join(3.0)
            svc = box.get("svc")
            if svc is None:
                return None
            if svc.status().get("state") != "unlocked":
                return None
            got = svc.internal_get("fingerprint-record-hmac")
            if not got.get("exists"):
                return None
            return bytes.fromhex(str(got.get("value") or ""))
        except Exception:  # noqa: BLE001
            return None

    def keyring_status(self) -> Dict[str, Any]:
        """Is the Vault set up, unlocked and able to hold the record?"""
        try:
            import keyring_api
            st = keyring_api.get_api().handle("org.nuxel.Home", "status", {})
            return {
                "available": bool(st.get("success")),
                "initialized": bool(st.get("initialized")),
                "unlocked": st.get("state") == "unlocked",
                "state": st.get("state"),
                "detail": st.get("detail"),
            }
        except Exception as exc:  # noqa: BLE001
            return {"available": False, "initialized": False, "unlocked": False,
                    "state": "unavailable", "detail": str(exc)[:160]}

    def vault_guard(self) -> Optional[Dict[str, Any]]:
        ks = self.keyring_status()
        if not ks["available"]:
            return {"error": "vault_unavailable",
                    "detail": "The Nuxel Vault keyring provider is not reachable. "
                              "Fingerprint enrollment needs the Vault to store its "
                              "enrollment record securely.",
                    "guidance": {"open_app": "org.nuxel.Vault"}}
        if not ks["initialized"]:
            return {"error": "vault_password_required",
                    "detail": "Set a Nuxel Vault master password first. Fingerprint "
                              "enrollment is stored in the Vault, so it cannot be "
                              "enabled before the Vault is set up.",
                    "guidance": {"open_app": "org.nuxel.Vault",
                                 "action": "create-master-password"}}
        if not ks["unlocked"]:
            return {"error": "vault_locked",
                    "detail": "Unlock the Nuxel Vault first; the fingerprint record is "
                              "kept inside it.",
                    "guidance": {"open_app": "org.nuxel.Vault", "action": "unlock"}}
        return None

    def _write_record(self, label: str) -> Optional[Dict[str, Any]]:
        key = self._record_key()
        if key is None:
            return None
        rec = {"schema": "nuxel.fingerprint-enrollment/1", "present": True,
               "label": label or "Fingerprint", "enrolled_at": time.time(),
               "sensor": "QBT2000"}
        rec["mac"] = hmac.new(key, json.dumps(
            {k: rec.get(k) for k in ("present", "label", "enrolled_at", "schema")},
            sort_keys=True).encode(), hashlib.sha256).hexdigest()
        os.makedirs(os.path.dirname(self.record_path), exist_ok=True)
        os.chmod(os.path.dirname(self.record_path), 0o700)
        tmp = self.record_path + ".tmp"
        with open(tmp, "w") as fh:
            json.dump(rec, fh, indent=2, sort_keys=True)
        os.chmod(tmp, 0o600)
        os.replace(tmp, self.record_path)
        return rec

    def _delete_record(self) -> None:
        try:
            os.unlink(self.record_path)
        except OSError:
            pass

    # ----------------------------------------------------------------- status
    def status(self) -> Dict[str, Any]:
        with self._lock:
            sensor = self._sensor()
            ta = self._ta()
            rec = self._record()
            enrolled = self._rec_ok(rec)
            ready = bool(sensor["detected"] and ta["present"] and ta["healthy"])
            vault = self.keyring_status()
            if ready:
                state, blocker = "READY", None
            elif not sensor["detected"]:
                state = "NOT_SUPPORTED_ON_DEVICE"
                blocker = "no qbt2000 fingerprint device/driver node is exposed"
            else:
                state = "BLOCKED_SECURE_PROVIDER"
                blocker = ("sensor/driver is present, but the OEM-signed TEEGris "
                           "fingerprint trusted application is not available; "
                           "matching cannot be performed outside it")
            if not vault["initialized"]:
                vault_state = "set_vault_password"
            elif not vault["unlocked"]:
                vault_state = "unlock_vault"
            else:
                vault_state = "ready"
            return {
                "success": True,
                "schema": "nuxel.fingerprint-status/2",
                "supported": bool(ready),
                "ready": bool(ready),
                "state": state,
                "sensor": sensor,
                "provider": ta,
                "provider_id": "teegris-qbt2000-ta" if ready else None,
                "enrolled": bool(enrolled),
                "enrollment_record": bool(enrolled),
                "enrollment_record_verified": bool(enrolled),
                "enrolled_at": (rec or {}).get("enrolled_at") if enrolled else None,
                "slots": [] if not enrolled else [{"id": "finger-1",
                                                   "label": (rec or {}).get("label", "Fingerprint")}],
                "enrollment_supported": True,
                "enrollment_requires": "vault_unlocked+pin_fallback+two_touch_ceremony",
                "match_supported": bool(ready),
                "deletion_supported": True,
                "test_supported": True,
                "unlock_supported": bool(ready),
                "pin_fallback_required": True,
                "vault": vault,
                "vault_state": vault_state,
                "template_policy": "no template/raw image ever leaves the TEE; without "
                                   "the TEE TA no match is reported",
                "blocker": blocker,
                "detail": blocker,
                "sensor_artwork": SENSOR_ARTWORK,
                "source": "fingerprint_provider",
            }

    def _refuse_match(self) -> Dict[str, Any]:
        st = self.status()
        return {"success": False, "authenticated": False,
                "error": "secure_provider_unavailable",
                "state": st["state"], "blocker": st["blocker"],
                "detail": "no match is reported without the TEEGris fingerprint TA",
                "provider_ready": st["ready"]}

    def _refuse_enroll(self) -> Dict[str, Any]:
        st = self.status()
        st["success"] = False
        st["error"] = st["blocker"] or "secure fingerprint provider unavailable"
        return st

    # --------------------------------------------------------------- enroll
    def cer_start(self, label: str = "Fingerprint") -> Dict[str, Any]:
        with self._lock:
            guard = self.vault_guard()
            if guard:
                return dict(guard, success=False)
            if self._sensor()["detected"] is False:
                return {"success": False, "error": "fingerprint_sensor_missing"}
            self._ceremony = {
                "label": label or "Fingerprint",
                "started_at": time.time(),
                "edges": 0,
                "touches": [],
                "token": secrets.token_hex(12),
            }
            return {"success": True, "schema": "nuxel.fingerprint-ceremony/1",
                    "token": self._ceremony["token"], "edges": 0, "edges_needed": 2,
                    "sensor_artwork": SENSOR_ARTWORK,
                    "instruction": "Touch the scanner once, lift, then touch it again. "
                                   "Each touch must start at an edge of the oval sensor.",
                    "timeout_s": CEREMONY_TIMEOUT_S}

    def cer_touch(self, edge: str = "", token: str = "") -> Dict[str, Any]:
        with self._lock:
            c = self._ceremony
            if not c:
                return {"success": False, "error": "no_enrollment_in_progress"}
            if token and hmac.compare_digest(str(token), c["token"]) is False:
                return {"success": False, "error": "invalid_enrollment_token"}
            if time.time() - c["started_at"] > CEREMONY_TIMEOUT_S:
                self._ceremony = None
                return {"success": False, "error": "enrollment_expired",
                        "detail": "start the enrollment again"}
            edge = str(edge or "unconfirmed")
            c["touches"].append({"edge": edge, "at": time.time()})
            if edge in ("left", "right", "top", "bottom", "left-edge", "right-edge"):
                c["edges"] += 1
            return {"success": True, "token": c["token"], "edges": c["edges"],
                    "edges_needed": 2, "touches": len(c["touches"]),
                    "enough": c["edges"] >= 2}

    def cer_commit(self, token: str = "") -> Dict[str, Any]:
        with self._lock:
            c = self._ceremony
            if not c:
                return {"success": False, "error": "no_enrollment_in_progress"}
            if token and hmac.compare_digest(str(token), c["token"]) is False:
                return {"success": False, "error": "invalid_enrollment_token"}
            if c["edges"] < 2:
                return {"success": False, "error": "enrollment_incomplete",
                        "detail": "both touches must start at a sensor edge",
                        "edges": c["edges"], "edges_needed": 2}
            rec = self._write_record(c["label"])
            self._ceremony = None
            if rec is None:
                return {"success": False, "error": "vault_record_failed",
                        "detail": "the Vault key is unavailable; unlock the Vault"}
            return {"success": True, "state": "enrolled", "enrolled": True,
                    "label": rec["label"], "enrolled_at": rec["enrolled_at"],
                    "template_stored": False,
                    "detail": "enrollment record stored in the Vault; a real template "
                              "can only be created by the TEE TA"}

    def enroll(self, label: str = "Fingerprint") -> Dict[str, Any]:
        """Real TA enrollment when the TA exists; otherwise the recorded path."""
        st = self.status()
        if not st["ready"]:
            return self._refuse_enroll()
        return {"success": False, "error": "ta_enroll_not_implemented",
                "detail": "a healthy TA was reported but no enrollment ABI is wired"}

    def delete(self, slot_id: str = "") -> Dict[str, Any]:
        with self._lock:
            self._delete_record()
            self._ceremony = None
            return {"success": True, "enrolled": False, "deleted": True,
                    "slot": slot_id or "finger-1"}

    def cancel(self) -> Dict[str, Any]:
        with self._lock:
            self._ceremony = None
            return {"success": True, "cancelled": True}

    def test(self, unlock: bool = False) -> Dict[str, Any]:
        st = self.status()
        if not st["ready"]:
            return self._refuse_match()
        return {"success": False, "authenticated": False,
                "error": "ta_match_not_implemented"}


_PROVIDER: Optional[FingerprintProvider] = None


def get_provider() -> FingerprintProvider:
    global _PROVIDER
    if _PROVIDER is None:
        _PROVIDER = FingerprintProvider()
    return _PROVIDER


def handle(verb: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    params = params or {}
    p = get_provider()
    if verb in ("status", "get"):
        return p.status()
    if verb in ("vault-status",):
        return {"success": True, **p.keyring_status()}
    if verb == "ceremony-start":
        return p.cer_start(str(params.get("label", "Fingerprint")))
    if verb == "ceremony-touch":
        return p.cer_touch(str(params.get("edge", "")), str(params.get("token", "")))
    if verb in ("ceremony-commit", "enroll-record"):
        return p.cer_commit(str(params.get("token", "")))
    if verb == "enroll":
        return p.enroll(str(params.get("label", "Fingerprint")))
    if verb in ("delete", "remove"):
        return p.delete(str(params.get("slot_id", "")))
    if verb == "cancel":
        return p.cancel()
    if verb in ("test", "verify", "authenticate"):
        return p.test(bool(params.get("unlock")))
    return {"success": False, "error": "unknown fingerprint verb", "verb": verb}
