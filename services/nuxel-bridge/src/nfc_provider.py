#!/usr/bin/env python3
"""Nuxel bridge client for the native ``nuxel-nfc`` controller service.

The bridge never opens ``/dev/sec-nfc`` and never speaks I2C/NCI itself.  It
talks to the root-owned Unix socket served by ``nuxel-nfcd``.  When the service
is absent, status is still a truthful read-only inventory: hardware present is
not the same as NFC enabled, and a matching firmware file is not proof that the
controller firmware is running.
"""
from __future__ import annotations

import json
import os
import socket
from typing import Any, Dict, Optional

SCHEMA = "nuxel.nfc-status/2"
SOCKET_PATH = os.environ.get("NUXEL_NFC_SOCKET", "/run/nuxel/nfc/nfc.sock")


def _inventory():
    try:
        from nuxel_nfc import inventory  # type: ignore
    except Exception:
        # Bridge installations stage the package under /usr/lib/nuxel/nuxel-nfc.
        import sys
        extra = "/usr/lib/nuxel/nuxel-nfc"
        if os.path.isdir(extra) and extra not in sys.path:
            sys.path.insert(0, extra)
        try:
            from nuxel_nfc import inventory  # type: ignore
        except Exception:
            return None
    return inventory


def _rpc(verb: str, params: Optional[Dict[str, Any]] = None,
         timeout_s: float = 5.0) -> Optional[Dict[str, Any]]:
    s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    s.settimeout(timeout_s)
    try:
        s.connect(SOCKET_PATH)
        s.sendall((json.dumps({"verb": verb, "params": params or {}}) + "\n").encode())
        buf = b""
        while not buf.endswith(b"\n"):
            chunk = s.recv(65536)
            if not chunk:
                break
            buf += chunk
        if not buf:
            return None
        out = json.loads(buf.decode("utf-8"))
        return out if isinstance(out, dict) else None
    except (OSError, ValueError):
        return None
    finally:
        s.close()


def _service_off_status() -> Dict[str, Any]:
    inv_mod = _inventory()
    inv = inv_mod.inventory() if inv_mod is not None else {}
    transport = bool(inv.get("vendor_transport_present"))
    fw_ok = bool(inv.get("firmware_file_verified"))
    if not transport:
        state, blocker = "BLOCKED_KERNEL", "sec-nfc transport /dev/sec-nfc is not present"
    elif not fw_ok:
        state, blocker = "BLOCKED_FIRMWARE", "verified sec_s3nrn82_firmware.bin is missing or has the wrong hash"
    else:
        state, blocker = "SERVICE_STOPPED", "nuxel-nfcd is not running; NFC remains OFF"
    return {
        "success": True,
        "schema": SCHEMA,
        "supported": transport,
        "ready": False,
        "enabled": False,
        "state": state,
        "verdict": state,
        "mode": "off",
        "controller": {
            "expected": "Samsung sec-nfc / S3NRN82 (I2C 0x27)",
            "kernel_nfc": bool(inv.get("kernel_nfc_core")),
            "i2c_0x27": bool(inv.get("controller_present")),
            "interfaces": [inv.get("transport", {}).get("path")] if transport else [],
            "bound": transport,
        },
        "firmware": {"present": bool(inv.get("firmware", {}).get("present")),
                     "verified": fw_ok,
                     "runtime_verified": False,
                     "sha256": inv.get("firmware", {}).get("sha256")},
        "transport": inv.get("transport", {}),
        "protocol": inv.get("protocol", ""),
        "protocol_verified": False,
        "userspace": {"daemon": False, "socket": False},
        "blocker": blocker,
        "detail": blocker,
        "tag_test_supported": False,
        "tag_writes_supported": False,
        "last_tag": None,
        "payment": {"supported": False,
                    "note": "card emulation/payment and secure-element access are not implemented"},
        "source": "nfc_provider",
    }


class NfcProvider:
    def status(self) -> Dict[str, Any]:
        out = _rpc("status", {}, timeout_s=2.0)
        if out is not None:
            out.setdefault("success", True)
            out.setdefault("schema", SCHEMA)
            out["source"] = "nfc_provider->nuxel-nfcd"
            out.setdefault("userspace", {})
            out["userspace"].update({"daemon": True, "socket": True})
            return out
        return _service_off_status()

    def set_enabled(self, enabled: bool) -> Dict[str, Any]:
        out = _rpc("enable" if enabled else "disable", {"enabled": bool(enabled)},
                   timeout_s=8.0 if enabled else 4.0)
        if out is None:
            st = _service_off_status()
            st["success"] = False
            st["error"] = "nfc_service_unavailable"
            st["error_code"] = "SERVICE_UNAVAILABLE"
            return st
        return out

    def test_tag(self, timeout_s: float = 10.0, read_ndef: bool = True) -> Dict[str, Any]:
        out = _rpc("scan", {"timeout_s": float(timeout_s), "read_ndef": bool(read_ndef)},
                   timeout_s=float(timeout_s) + 8.0)
        if out is None:
            st = _service_off_status()
            st["success"] = False
            st["error"] = "nfc_service_unavailable"
            st["error_code"] = "SERVICE_UNAVAILABLE"
            st["tag_test_supported"] = False
            return st
        return out

    def read_last(self) -> Dict[str, Any]:
        out = _rpc("read", {}, timeout_s=2.0)
        if out is None:
            return {"success": False, "error": "nfc_service_unavailable",
                    "error_code": "SERVICE_UNAVAILABLE"}
        return out

    def clear(self) -> Dict[str, Any]:
        out = _rpc("clear", {}, timeout_s=2.0)
        if out is None:
            return {"success": False, "error": "nfc_service_unavailable",
                    "error_code": "SERVICE_UNAVAILABLE"}
        return out


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
        enabled = (not p.status().get("enabled", False)) if verb == "toggle" else bool(params.get("enabled"))
        return p.set_enabled(enabled)
    if verb in ("test-tag", "scan", "read-tag"):
        timeout = params.get("timeout_s", 10.0)
        try:
            timeout = max(1.0, min(float(timeout), 30.0))
        except (TypeError, ValueError):
            timeout = 10.0
        return p.test_tag(timeout, bool(params.get("read_ndef", True)))
    if verb in ("read", "last-tag"):
        return p.read_last()
    if verb == "clear":
        return p.clear()
    return {"success": False, "error": "unknown nfc verb", "verb": verb}
