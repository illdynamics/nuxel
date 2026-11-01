#!/usr/bin/env python3
"""Truthful NFC provider for the S10+ (S3FWRN5 / sec-nfc family).

The current image's kernel reports CONFIG_NFC unset, so no controller can bind
and no userspace reader stack can exist.  This provider enumerates the real
kernel/device/firmware/stack state on every status call and only enables a
toggle or a tag test when a coherent path is actually present.

It never writes I2C/sysfs directly and never claims payment/emulation support.
"""
from __future__ import annotations

import glob
import json
import os
from typing import Any, Dict, Optional

DEFAULT_CONFIG = "/etc/nuxel/nfc/nfc.json"


def _read(path: str) -> Optional[str]:
    try:
        with open(path) as fh:
            return fh.read().strip()
    except OSError:
        return None


def _exists_any(patterns) -> list:
    out = []
    for pat in patterns:
        out.extend(glob.glob(pat))
    return sorted(set(out))


class NfcProvider:
    def __init__(self) -> None:
        self.config_path = os.environ.get("NUXEL_NFC_CONFIG", DEFAULT_CONFIG)

    def _config(self) -> Dict[str, Any]:
        try:
            with open(self.config_path) as fh:
                doc = json.load(fh)
            return doc if isinstance(doc, dict) else {}
        except (OSError, ValueError):
            return {}

    def _kernel_nfc(self) -> bool:
        # /proc/config.gz or /boot/config-* are authoritative; /proc/devices
        # and /sys/class/nfc prove a live subsystem.
        for path in ("/proc/config.gz", "/boot/config-%s" % os.uname().release):
            try:
                if path.endswith(".gz"):
                    import gzip
                    with gzip.open(path, "rt") as fh:
                        text = fh.read()
                else:
                    with open(path) as fh:
                        text = fh.read()
                for line in text.splitlines():
                    if line.startswith("CONFIG_NFC="):
                        return line.split("=", 1)[1].strip() in ("y", "m")
                    if line.strip() == "# CONFIG_NFC is not set":
                        return False
            except OSError:
                continue
        if os.path.isdir("/sys/class/nfc") and os.listdir("/sys/class/nfc"):
            return True
        return bool(_exists_any(["/dev/nfc*"]))

    def _i2c_present(self) -> bool:
        return bool(_exists_any(["/sys/bus/i2c/devices/*-0027"]))

    def _stack(self) -> Dict[str, Any]:
        return {
            "neard": os.path.exists("/usr/sbin/neard") or os.path.exists("/usr/bin/neard"),
            "libnfc": bool(_exists_any(["/usr/lib*/libnfc.so*", "/usr/lib/*/libnfc.so*"])),
            "nfctool": bool(_exists_any(["/usr/bin/nfctool", "/usr/sbin/nfctool"])),
            "nci_devices": _exists_any(["/dev/nci*"]),
        }

    def status(self) -> Dict[str, Any]:
        cfg = self._config()
        kernel = self._kernel_nfc()
        i2c = self._i2c_present()
        iface = _exists_any(["/sys/class/nfc/*", "/dev/nfc*"])
        stack = self._stack()
        controller = bool(iface) or (i2c and kernel)
        firmware = bool(_exists_any([
            "/lib/firmware/*s3fwrn5*", "/lib/firmware/*sec-nfc*",
            "/lib/firmware/nfc/*s3nrn82*", "/lib/firmware/*s3nrn82*",
            "/vendor/firmware/*s3fwrn5*", "/vendor/firmware/nfc/*s3nrn82*",
        ]))
        if not kernel:
            verdict, blocker = "BLOCKED_KERNEL", "CONFIG_NFC is not set in the running 4.14.253 kernel"
        elif not i2c:
            verdict, blocker = "NOT_SUPPORTED_ON_DEVICE", "expected sec-nfc/S3FWRN5 controller at I2C 0x27 was not enumerated"
        elif not firmware:
            verdict, blocker = "BLOCKED_FIRMWARE", "controller present but no S3FWRN5/sec-nfc firmware file was found"
        elif not controller:
            verdict, blocker = "BLOCKED_KERNEL", "NFC subsystem is enabled but no controller/device node is bound"
        elif not (stack["neard"] or stack["nci_devices"]):
            verdict, blocker = "BLOCKED_EXTERNAL_RESOURCE", "no NFC userspace reader stack (neard/nci device) is installed"
        else:
            verdict, blocker = "READY_FOR_TAG", "controller, kernel NFC subsystem and userspace reader are present; physical tag test still required"
        supported = verdict == "READY_FOR_TAG"
        return {
            "success": True,
            "schema": "nuxel.nfc-status/1",
            "supported": supported,
            "enabled": None if not supported else _read("/sys/class/nfc/nfc0/enabled") == "1",
            "state": verdict,
            "verdict": verdict,
            "controller": {
                "expected": "Samsung sec-nfc / S3FWRN5 family (I2C 0x27)",
                "kernel_nfc": kernel,
                "i2c_0x27": i2c,
                "interfaces": iface,
                "bound": controller,
            },
            "firmware": {"present": firmware},
            "userspace": stack,
            "mode": "off" if not supported else "reader",
            "blocker": blocker,
            "detail": blocker,
            "tag_test_supported": supported,
            "last_tag": None,
            "payment": {"supported": False, "note": "card emulation/payment is not implemented and must not be inferred from a tag read"},
            "source": "nfc_provider",
            "config_present": bool(cfg),
        }

    def set_enabled(self, enabled: bool) -> Dict[str, Any]:
        st = self.status()
        if not st["supported"]:
            # No fake toggling: return the same truthful blocker.
            st["success"] = False
            st["error"] = "NFC is not supported by this kernel/build"
            return st
        # A future backend must implement a real vendor enable path.  Until it
        # exists, refuse instead of pretending the radio changed.
        st["success"] = False
        st["error"] = "NFC provider has no verified enable path in this build"
        return st

    def test_tag(self) -> Dict[str, Any]:
        st = self.status()
        if not st["supported"]:
            return {"success": False, "state": st["state"], "error": st["blocker"],
                    "tag_test_supported": False, "uid": None}
        return {"success": False, "state": "BLOCKED_EXTERNAL_RESOURCE",
                "error": "a reader backend is present but no bounded tag-read API is configured",
                "tag_test_supported": False, "uid": None}


_PROVIDER: Optional[NfcProvider] = None


def get_provider() -> NfcProvider:
    global _PROVIDER
    if _PROVIDER is None:
        _PROVIDER = NfcProvider()
    return _PROVIDER


def handle(verb: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    params = params or {}
    p = get_provider()
    if verb in ("status", "get", "diagnostics"):
        return p.status()
    if verb in ("set-enabled", "toggle"):
        want = (not p.status()["enabled"]) if verb == "toggle" else bool(params.get("enabled"))
        return p.set_enabled(want)
    if verb in ("test-tag", "read-tag"):
        return p.test_tag()
    return {"success": False, "error": "unknown nfc verb", "verb": verb}
