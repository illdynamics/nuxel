#!/usr/bin/env python3
"""BlueZ OBEX Object Push sender for the Files app.

This is the only file-transfer implementation.  It talks to the system BlueZ
OBEX daemon over D-Bus (org.bluez.obex) and never invents a transfer result:

  * source paths are resolved and must stay inside the Files root;
  * the receiving device must be a real BlueZ peer (paired preferred);
  * a transfer is only reported successful after the OBEX transfer object
    reaches Status=complete; a created object path alone is not success;
  * sessions are closed on every path and each call is bounded.

On a host without the obex service the provider returns OBEX_UNAVAILABLE, which
the UI shows honestly.  It never falls back to a raw socket protocol.
"""
from __future__ import annotations

import os
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    import dbus  # type: ignore
except Exception:  # pragma: no cover - absent on some hosts
    dbus = None

OBEX_BUS = "org.bluez.obex"
OBEX_CLIENT = "org.bluez.obex.Client1"
OBEX_OPP = "org.bluez.obex.ObjectPush1"
OBEX_TRANSFER = "org.bluez.obex.Transfer1"
MAX_FILES = 20
MAX_BYTES = 512 * 1024 * 1024
TRANSFER_TIMEOUT_S = 180


class ObexError(Exception):
    pass


def _validate_path(root: Path, raw: str) -> Path:
    if not raw or not isinstance(raw, str):
        raise ObexError("invalid path")
    candidate = Path(raw)
    # Bridge paths are home-relative with a leading slash ("/hello.txt").
    if not candidate.is_absolute() or not candidate.exists():
        candidate = root / raw.lstrip("/")
    try:
        resolved = candidate.resolve(strict=True)
        root_resolved = root.resolve()
        if os.path.commonpath([str(root_resolved), str(resolved)]) != str(root_resolved):
            raise ObexError("path escapes the Files root")
        if not resolved.is_file():
            raise ObexError("not a regular file: %s" % raw)
        return resolved
    except FileNotFoundError:
        raise ObexError("file not found: %s" % raw)
    except OSError as exc:
        raise ObexError("path check failed: %s" % exc)


def _props(obj) -> Dict[str, Any]:
    try:
        iface = dbus.Interface(obj, "org.freedesktop.DBus.Properties")
        return {str(k): _plain(v) for k, v in dict(iface.GetAll(OBEX_TRANSFER)).items()}
    except Exception:
        return {}


def _plain(value):
    try:
        if isinstance(value, dbus.Boolean):
            return bool(value)
        if isinstance(value, dbus.UInt64):
            return int(value)
        if isinstance(value, (dbus.Int32, dbus.UInt32, dbus.Int64, dbus.Byte, dbus.UInt16)):
            return int(value)
        if isinstance(value, dbus.String):
            return str(value)
        if isinstance(value, (dbus.Array, list, tuple)):
            return [_plain(v) for v in value]
        if isinstance(value, dbus.Dictionary):
            return {str(k): _plain(v) for k, v in value.items()}
    except Exception:
        pass
    return value


def _adapter_address(bus) -> Optional[str]:
    try:
        manager = dbus.Interface(bus.get_object("org.bluez", "/"),
                                 "org.freedesktop.DBus.ObjectManager")
        objects = manager.GetManagedObjects()
        for path, ifaces in objects.items():
            if "org.bluez.Adapter1" in ifaces:
                return str(ifaces["org.bluez.Adapter1"].get("Address", "")) or None
    except Exception:
        return None
    return None


def list_targets() -> Dict[str, Any]:
    """Return real BlueZ peers, paired first.  No fabricated devices."""
    if dbus is None:
        return {"success": False, "devices": [], "error": "D-Bus bindings unavailable",
                "error_code": "DBUS_UNAVAILABLE"}
    try:
        bus = dbus.SystemBus()
        adapter_addr = _adapter_address(bus)
        manager = dbus.Interface(bus.get_object("org.bluez", "/"),
                                 "org.freedesktop.DBus.ObjectManager")
        objects = manager.GetManagedObjects()
    except Exception as exc:
        return {"success": False, "devices": [], "error": str(exc),
                "error_code": "BLUEZ_UNAVAILABLE"}
    devices = []
    for path, ifaces in objects.items():
        dev = ifaces.get("org.bluez.Device1")
        if not dev:
            continue
        address = str(dev.get("Address", "")).upper()
        if not address or address == (adapter_addr or "").upper():
            continue
        paired = bool(dev.get("Paired", False))
        connected = bool(dev.get("Connected", False))
        name = str(dev.get("Alias") or dev.get("Name") or address)
        devices.append({
            "address": address,
            "name": name,
            "paired": paired,
            "connected": connected,
            "trusted": bool(dev.get("Trusted", False)),
            "icon": str(dev.get("Icon", "")),
        })
    devices.sort(key=lambda d: (not d["paired"], not d["connected"], d["name"].lower()))
    return {"success": True, "devices": devices,
            "adapter_address": adapter_addr,
            "paired_count": sum(1 for d in devices if d["paired"])}


def _wait_transfer(bus, transfer_path: str, timeout: float = TRANSFER_TIMEOUT_S) -> Dict[str, Any]:
    deadline = time.monotonic() + timeout
    last: Dict[str, Any] = {}
    while time.monotonic() < deadline:
        try:
            obj = bus.get_object(OBEX_BUS, transfer_path)
            props = _props(obj)
            if props:
                last = props
            status = str(props.get("Status", "")).lower()
            if status in ("complete", "error"):
                return {"status": status, "properties": props}
            if status:
                last = props
        except Exception:
            pass
        time.sleep(0.25)
    return {"status": "timeout", "properties": last}


def send_files(root: Path, paths: List[str], address: str,
               timeout: float = TRANSFER_TIMEOUT_S) -> Dict[str, Any]:
    if not isinstance(paths, list) or not paths:
        return {"success": False, "error": "no files selected", "files": []}
    if len(paths) > MAX_FILES:
        return {"success": False, "error": "too many files (max %d)" % MAX_FILES, "files": []}
    address = str(address or "").strip().upper()
    if len(address) != 17 or address.count(":") != 5:
        return {"success": False, "error": "invalid Bluetooth address", "files": []}
    resolved = []
    try:
        for raw in paths:
            p = _validate_path(root, raw)
            st = p.stat()
            if st.st_size > MAX_BYTES:
                raise ObexError("file exceeds %d MB: %s" % (MAX_BYTES // (1024 * 1024), p.name))
            resolved.append(p)
    except (ObexError, OSError) as exc:
        return {"success": False, "error": str(exc), "error_code": "INVALID_SOURCE", "files": []}
    if dbus is None:
        return {"success": False, "error": "D-Bus bindings unavailable",
                "error_code": "DBUS_UNAVAILABLE", "files": []}

    try:
        # BlueZ's OBEX daemon is a SESSION-bus service on Fedora
        # (/usr/share/dbus-1/services/org.bluez.obex.service), while the BlueZ
        # adapter/device objects live on the system bus.  The bridge unit pins
        # DBUS_SESSION_BUS_ADDRESS to the Nuxel session bus; fall back to the
        # system bus for hosts that ship a system-wide obex service.
        try:
            bus = dbus.SessionBus()
        except Exception:
            bus = dbus.SystemBus()
        # Activate org.bluez.obex through the bus; a missing daemon is an
        # explicit error, not an invitation to implement OBEX ourselves.
        client = dbus.Interface(bus.get_object(OBEX_BUS, "/org/bluez/obex"), OBEX_CLIENT)
        session_path = client.CreateSession(address, {"Target": dbus.String("opp")})
        session_path = str(session_path)
    except Exception as exc:
        return {"success": False, "error": "Bluetooth OBEX unavailable: %s" % exc,
                "error_code": "OBEX_UNAVAILABLE", "files": []}

    results = []
    try:
        opp = dbus.Interface(bus.get_object(OBEX_BUS, session_path), OBEX_OPP)
        for p in resolved:
            entry = {"path": str(p), "name": p.name, "size": p.stat().st_size,
                     "status": "queued", "transferred": 0, "success": False}
            try:
                transfer_path, props = opp.SendFile(str(p))
                transfer_path = str(transfer_path)
                initial = {str(k): _plain(v) for k, v in dict(props).items()} if props else {}
                final = _wait_transfer(bus, transfer_path, timeout)
                st = final.get("status", "error")
                props = dict(initial)
                props.update(final.get("properties") or {})
                entry.update({
                    "transfer_path": transfer_path,
                    "status": st,
                    "transferred": int(props.get("Transferred", 0) or 0),
                    "size": int(props.get("Size", entry["size"]) or entry["size"]),
                    "mime": str(props.get("Filename", "")),
                    "success": st == "complete",
                })
                if st != "complete":
                    entry["error"] = "transfer %s" % st
            except Exception as exc:
                entry.update({"status": "error", "error": str(exc)})
            results.append(entry)
    finally:
        try:
            client.RemoveSession(dbus.ObjectPath(session_path))
        except Exception:
            pass
    ok = all(r.get("success") for r in results) and bool(results)
    return {
        "success": ok,
        "address": address,
        "files": results,
        "sent": sum(1 for r in results if r.get("success")),
        "failed": sum(1 for r in results if not r.get("success")),
        "error": None if ok else "one or more transfers failed",
    }
