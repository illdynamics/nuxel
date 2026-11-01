#!/usr/bin/env python3
"""S10+ ultrasonic fingerprint capability broker (PWNAGE-45000).

The kernel binds a Samsung qbt2000 FPS driver, but this repository has no
verified secure userspace/TEE enrollment provider (and fprintd/libfprint do not
support this sensor here).  The provider therefore reports the sensor as
detected but NOT usable for enrollment.  It never exposes or imports templates
and never fabricates a scan result.
"""
from __future__ import annotations

import glob
import os
import shutil
from typing import Any, Dict, Optional


def _exists_any(patterns) -> list:
    out = []
    for pat in patterns:
        out.extend(glob.glob(pat))
    return sorted(set(out))


class FingerprintProvider:
    def status(self) -> Dict[str, Any]:
        devs = _exists_any(["/dev/fingerprint*", "/dev/fp*", "/dev/qbt*"])
        spi = _exists_any(["/sys/bus/spi/drivers/*qbt*", "/sys/bus/spi/devices/*qbt*"])
        driver = bool(spi) or bool(_exists_any(["/sys/module/qbt*", "/sys/class/fingerprint*"]))
        fprintd = bool(shutil.which("fprintd") or shutil.which("fprintd-enroll"))
        libfprint = bool(_exists_any(["/usr/lib*/libfprint*.so*", "/usr/lib/*/libfprint*.so*"]))
        # A secure provider requires an actual device node AND a provider that
        # explicitly supports this exact sensor.  None is demonstrated here.
        secure = bool(devs) and False
        if not (devs or driver):
            state = "NOT_SUPPORTED_ON_DEVICE"
            blocker = "no qbt2000 fingerprint device/driver node is exposed"
        elif not secure:
            state = "BLOCKED_SECURE_PROVIDER"
            blocker = ("sensor/driver is present but no verified TEE-backed enrollment "
                       "provider exists for this qbt2000 sensor")
        else:
            state = "READY"
            blocker = None
        return {
            "success": True,
            "schema": "nuxel.fingerprint-status/1",
            "supported": secure,
            "ready": secure,
            "state": state,
            "sensor": {"detected": bool(driver or devs), "devices": devs, "driver": driver},
            "provider": {"fprintd": fprintd, "libfprint": libfprint, "secure_tee": secure},
            "enrolled": 0,
            "slots": [],
            "enrollment_supported": secure,
            "deletion_supported": secure,
            "test_supported": secure,
            "pin_fallback_required": True,
            "template_policy": "templates remain inside the secure provider/TEE; no import/export",
            "blocker": blocker,
            "detail": blocker,
            "source": "fingerprint_provider",
        }

    def _refuse(self) -> Dict[str, Any]:
        st = self.status()
        st["success"] = False
        st["error"] = st["blocker"] or "secure fingerprint provider unavailable"
        return st

    def enroll(self, label: str = "Fingerprint") -> Dict[str, Any]:
        return self._refuse()

    def delete(self, slot_id: str = "") -> Dict[str, Any]:
        return self._refuse()

    def test(self) -> Dict[str, Any]:
        return self._refuse()


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
    if verb == "enroll":
        return p.enroll(str(params.get("label", "Fingerprint")))
    if verb in ("delete", "remove"):
        return p.delete(str(params.get("slot_id", "")))
    if verb in ("test", "verify"):
        return p.test()
    return {"success": False, "error": "unknown fingerprint verb", "verb": verb}
