#!/usr/bin/env python3
"""Durable desired state for Nuxel's switchable hardware interfaces.

The UI owns intent, the providers own hardware, and this module owns the one
small document that lets intent survive a reboot:

    /var/lib/nuxel/interfaces.json

Only interfaces Nuxel itself switches are stored here.  Wi-Fi radio state is
already durable in NetworkManager (/var/lib/NetworkManager/NetworkManager.state)
and the location/GPS privacy policy is durable in
/var/lib/nuxel/permissions/location-policy.json; those two remain owned by their
existing services.  Bluetooth, NFC and the GNSS power rail are restored by
nuxel-interface-state.service at boot from this document.

The document is deliberately boring: one boolean per interface.  A missing
entry is the documented default rather than an error, so a fresh image boots
with Bluetooth and NFC OFF.  Writes are atomic and serialized with flock so a
Bluetooth toggle and an NFC toggle cannot lose one another.
"""
from __future__ import annotations

import json
import os
import time
from typing import Any, Dict, Optional

SCHEMA_VERSION = 1
DEFAULT_STATE_PATH = "/var/lib/nuxel/interfaces.json"

# First-boot defaults.  Bluetooth is OFF by owner request; NFC is default-off
# by design; the GNSS rail is battery-safe OFF until a consumer asks for it.
DEFAULTS: Dict[str, bool] = {
    "bluetooth": False,
    "nfc": False,
    "gps": False,
}

INTERFACES = tuple(DEFAULTS.keys())


def state_path(path: Optional[str] = None) -> str:
    return path or os.environ.get("NUXEL_INTERFACE_STATE", DEFAULT_STATE_PATH)


def _empty_doc() -> Dict[str, Any]:
    now = time.time()
    return {
        "schema_version": SCHEMA_VERSION,
        "updated_at": now,
        "interfaces": {
            name: {"enabled": bool(value), "updated_at": 0, "source": "default"}
            for name, value in DEFAULTS.items()
        },
    }


def _normalise(doc: Any) -> Dict[str, Any]:
    out = _empty_doc()
    if not isinstance(doc, dict):
        return out
    if isinstance(doc.get("interfaces"), dict):
        for name in INTERFACES:
            entry = doc["interfaces"].get(name)
            if isinstance(entry, dict) and isinstance(entry.get("enabled"), bool):
                out["interfaces"][name] = {
                    "enabled": entry["enabled"],
                    "updated_at": entry.get("updated_at", 0),
                    "source": str(entry.get("source") or "unknown"),
                }
    try:
        out["updated_at"] = float(doc.get("updated_at") or 0)
    except (TypeError, ValueError):
        out["updated_at"] = 0
    return out


def _read_unlocked(path: str) -> Dict[str, Any]:
    try:
        with open(path, "r", encoding="utf-8") as fh:
            return _normalise(json.load(fh))
    except (OSError, ValueError, TypeError):
        return _empty_doc()


def read(path: Optional[str] = None) -> Dict[str, Any]:
    """Return the normalised document, filling documented defaults."""
    return _read_unlocked(state_path(path))


def get(name: str, default: Optional[bool] = None, path: Optional[str] = None) -> Optional[bool]:
    """Return the persisted desired value for one interface."""
    if name not in DEFAULTS:
        raise ValueError("unknown interface: %s" % name)
    entry = read(path)["interfaces"].get(name) or {}
    value = entry.get("enabled")
    if isinstance(value, bool):
        return value
    return DEFAULTS[name] if default is None else default


def set_desired(name: str, enabled: bool, source: str = "api",
                path: Optional[str] = None) -> Dict[str, Any]:
    """Atomically persist one interface's desired state.

    The caller applies the hardware change; this function only records intent.
    It raises OSError when the durable document cannot be written so callers can
    report a real persistence failure instead of silently pretending success.
    """
    if name not in DEFAULTS:
        raise ValueError("unknown interface: %s" % name)
    target = state_path(path)
    directory = os.path.dirname(target) or "."
    os.makedirs(directory, exist_ok=True)

    # POSIX advisory lock.  The lock file is separate so replacing the state
    # file never invalidates a holder's lock.
    lock_path = target + ".lock"
    lock_fd = os.open(lock_path, os.O_WRONLY | os.O_CREAT, 0o644)
    try:
        try:
            import fcntl
            fcntl.flock(lock_fd, fcntl.LOCK_EX)
        except (ImportError, OSError):
            pass
        doc = _read_unlocked(target)
        entry = {
            "enabled": bool(enabled),
            "updated_at": time.time(),
            "source": str(source or "api")[:120],
        }
        doc["interfaces"][name] = entry
        doc["schema_version"] = SCHEMA_VERSION
        doc["updated_at"] = entry["updated_at"]
        tmp = target + ".tmp.%d" % os.getpid()
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(doc, fh, indent=2, sort_keys=True)
            fh.write("\n")
            fh.flush()
            os.fsync(fh.fileno())
        os.chmod(tmp, 0o644)
        os.replace(tmp, target)
        return dict(entry)
    finally:
        try:
            import fcntl
            fcntl.flock(lock_fd, fcntl.LOCK_UN)
        except (ImportError, OSError):
            pass
        os.close(lock_fd)


def snapshot(path: Optional[str] = None) -> Dict[str, Any]:
    return read(path)
