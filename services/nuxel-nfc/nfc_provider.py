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
         timeout_s: float = 5.0,
         app_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
    s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    s.settimeout(timeout_s)
    try:
        s.connect(SOCKET_PATH)
        request = {"verb": verb, "params": params or {}}
        if app_id:
            # nuxel-nfcd authorizes every tag operation against this app's
            # capability grant; an unidentified request is refused.
            request["app_id"] = str(app_id)
        s.sendall((json.dumps(request) + "\n").encode())
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
    kernel_nci = bool(inv.get("kernel_nfc_core") or
                      os.path.exists("/dev/nfc0"))
    transport = bool(inv.get("vendor_transport_present"))
    fw_ok = bool(inv.get("firmware_file_verified"))
    if kernel_nci:
        state, blocker = "SERVICE_STOPPED", "nuxel-nfcd is not running; NFC remains OFF"
    elif not transport:
        state, blocker = "BLOCKED_KERNEL", "kernel NCI (/dev/nfc0) and sec-nfc transport are absent"
    elif not fw_ok:
        state, blocker = "BLOCKED_FIRMWARE", "verified sec_s3nrn82_firmware.bin is missing or has the wrong hash"
    else:
        state, blocker = "SERVICE_STOPPED", "nuxel-nfcd is not running; NFC remains OFF"
    return {
        "success": True,
        "schema": SCHEMA,
        "supported": bool(kernel_nci or transport),
        "ready": False,
        "enabled": False,
        "state": state,
        "verdict": state,
        "mode": "off",
        "controller": {
            "expected": "Samsung S3NRN82 / S3FWRN5-compatible NCI (I2C 0x27)",
            "kernel_nci": kernel_nci,
            "kernel_nfc": bool(inv.get("kernel_nfc_core")),
            "i2c_0x27": bool(inv.get("controller_present")),
            "interfaces": (["/dev/nfc0"] if kernel_nci else []) +
                          ([inv.get("transport", {}).get("path")] if transport else []),
            "bound": bool(kernel_nci or transport),
        },
        "firmware": {"present": bool(inv.get("firmware", {}).get("present")),
                     "verified": fw_ok,
                     "runtime_verified": False,
                     "sha256": inv.get("firmware", {}).get("sha256"),
                     "note": "kernel NCI uses the on-controller NCI firmware; "
                             "a matching vendor image is an artifact, not a runtime claim"},
        "transport": inv.get("transport", {}),
        "protocol": inv.get("protocol", ""),
        "protocol_verified": False,
        "userspace": {"daemon": False, "socket": False},
        "blocker": blocker,
        "detail": blocker,
        "tag_test_supported": bool(kernel_nci or transport),
        "tag_writes_supported": True,
        "write_requires_confirmation": True,
        "last_tag": None,
        "payment": {"supported": False,
                    "note": "card emulation/payment and secure-element access are not implemented"},
        "source": "nfc_provider",
    }


class NfcProvider:
    # The bridge sets this to the authenticated caller id for the duration of
    # one request so /run/nuxel/nfc/nfc.sock sees who is asking.
    _caller_app_id: Optional[str] = None

    def _as(self, app_id: Optional[str]):
        return _CallerScope(self, app_id)

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

    def set_enabled(self, enabled: bool, persist: bool = True) -> Dict[str, Any]:
        out = _rpc("enable" if enabled else "disable", {"enabled": bool(enabled)},
                   timeout_s=8.0 if enabled else 4.0)
        if out is None:
            st = _service_off_status()
            st["success"] = False
            st["error"] = "nfc_service_unavailable"
            st["error_code"] = "SERVICE_UNAVAILABLE"
            return st
        # Persist only a state the controller actually accepted.  A failed
        # enable must not silently become the next boot's desired state.
        if persist and out.get("success") is not False:
            try:
                import interface_state
                interface_state.set_desired(
                    "nfc", bool(enabled),
                    source="nfc_provider.NfcProvider")
                out["persisted"] = True
            except Exception as exc:  # noqa: BLE001
                out["persisted"] = False
                out["persist_error"] = str(exc)
        return out

    def test_tag(self, timeout_s: float = 10.0, read_ndef: bool = True) -> Dict[str, Any]:
        out = _rpc("scan", {"timeout_s": float(timeout_s), "read_ndef": bool(read_ndef)},
                   timeout_s=float(timeout_s) + 8.0, app_id=self._caller_app_id)
        if out is None:
            st = _service_off_status()
            st["success"] = False
            st["error"] = "nfc_service_unavailable"
            st["error_code"] = "SERVICE_UNAVAILABLE"
            st["tag_test_supported"] = False
            return st
        return out

    def read_last(self) -> Dict[str, Any]:
        out = _rpc("read", {}, timeout_s=2.0, app_id=self._caller_app_id)
        if out is None:
            return {"success": False, "error": "nfc_service_unavailable",
                    "error_code": "SERVICE_UNAVAILABLE"}
        return out

    def write_tag(self, kind: str, value: str, confirm: bool,
                  language: str = "en") -> Dict[str, Any]:
        """Write one NDEF record; caller must already have explicit consent."""
        if confirm is not True:
            return {"success": False,
                    "error": "write requires explicit confirmation",
                    "error_code": "CONFIRMATION_REQUIRED"}
        out = _rpc("write", {"confirm": True, "kind": str(kind),
                             "value": str(value),
                             "language": str(language or "en")},
                   timeout_s=8.0, app_id=self._caller_app_id)
        if out is None:
            st = _service_off_status()
            st["success"] = False
            st["error"] = "nfc_service_unavailable"
            st["error_code"] = "SERVICE_UNAVAILABLE"
            return st
        return out

    def clear(self) -> Dict[str, Any]:
        out = _rpc("clear", {}, timeout_s=2.0, app_id=self._caller_app_id)
        if out is None:
            return {"success": False, "error": "nfc_service_unavailable",
                    "error_code": "SERVICE_UNAVAILABLE"}
        return out


class _CallerScope:
    """Context manager that binds NfcProvider._caller_app_id to one caller."""

    def __init__(self, provider, app_id):
        self.provider = provider
        self.app_id = app_id
        self.previous = None

    def __enter__(self):
        self.previous = NfcProvider._caller_app_id
        NfcProvider._caller_app_id = self.app_id
        return self.provider

    def __exit__(self, *exc):
        NfcProvider._caller_app_id = self.previous
        return False


_PROVIDER: Optional[NfcProvider] = None


def get_provider() -> NfcProvider:
    global _PROVIDER
    if _PROVIDER is None:
        _PROVIDER = NfcProvider()
    return _PROVIDER


def handle(verb: str, params: Optional[Dict[str, Any]] = None,
           app_id: Optional[str] = None) -> Dict[str, Any]:
    params = params or {}
    p = get_provider()
    with p._as(app_id):
        return _handle_inner(p, verb, params, app_id)


def _handle_inner(p, verb, params, app_id):
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
    if verb in ("write", "write-tag"):
        return p.write_tag(str(params.get("kind") or "text"),
                           str(params.get("value") or ""),
                           params.get("confirm") is True,
                           str(params.get("language") or "en"))
    if verb == "clear":
        return p.clear()
    return {"success": False, "error": "unknown nfc verb", "verb": verb}
