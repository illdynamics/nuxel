#!/usr/bin/env python3
"""Typed, read-only Nuxel diagnostics for the Squad SYSTEM route.

Only a fixed allowlist of read operations exists.  There is no shell string,
no arbitrary path and no write.  Values are read from /proc, /sys and systemd
in read-only form; missing evidence is reported as unavailable, never invented.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
from typing import Any, Dict, Optional

ALLOWED = {
    "battery": ("/sys/class/power_supply", "capacity"),
    "wifi": ("/sys/class/net", "operstate"),
    "bluetooth": ("/sys/class/bluetooth", None),
    "temperature": ("/sys/class/thermal", "temp"),
    "uptime": ("/proc/uptime", None),
    "kernel": ("/proc/version", None),
    "memory": ("/proc/meminfo", None),
    "device model": ("/proc/device-tree/model", None),
    "storage": ("/", None),
    "volume": (None, None),
}
ALIASES = {
    "wi-fi": "wifi", "disk space": "storage", "free memory": "memory",
    "memory usage": "memory", "kernel version": "kernel", "charging": "battery",
    "thermal": "temperature", "device model": "device model",
    "ip address": "network status", "service status": "services",
    "network status": "network status",
}


def _battery() -> Dict[str, Any]:
    root = "/sys/class/power_supply"
    try:
        names = os.listdir(root)
    except OSError:
        return {"available": False, "why": "no power_supply node"}
    for name in names:
        try:
            typ = open(os.path.join(root, name, "type")).read().strip()
        except OSError:
            continue
        if typ == "Battery":
            def rd(f):
                try:
                    return open(os.path.join(root, name, f)).read().strip()
                except OSError:
                    return None
            return {"available": True, "capacity_percent": rd("capacity"),
                    "status": rd("status"), "node": name}
    return {"available": False, "why": "no Battery-type node"}


def _net() -> Dict[str, Any]:
    out = {}
    try:
        for dev in os.listdir("/sys/class/net"):
            if dev == "lo":
                continue
            try:
                out[dev] = open("/sys/class/net/%s/operstate" % dev).read().strip()
            except OSError:
                out[dev] = "unknown"
    except OSError:
        return {"available": False}
    return {"available": True, "interfaces": out}


def _memory() -> Dict[str, Any]:
    try:
        lines = dict(l.split(":", 1) for l in open("/proc/meminfo") if ":" in l)
        return {"available": True,
                "mem_total_kib": int(lines["MemTotal"].split()[0]),
                "mem_available_kib": int(lines["MemAvailable"].split()[0])}
    except Exception:  # noqa: BLE001
        return {"available": False}


def _temperature() -> Dict[str, Any]:
    out = {}
    try:
        for zone in os.listdir("/sys/class/thermal"):
            if not zone.startswith("thermal_zone"):
                continue
            try:
                kind = open("/sys/class/thermal/%s/type" % zone).read().strip()
                raw = int(open("/sys/class/thermal/%s/temp" % zone).read().strip())
                out[kind] = round(raw / 1000.0, 1)
            except (OSError, ValueError):
                continue
    except OSError:
        return {"available": False}
    return {"available": bool(out), "celsius": out}


def _read(path: str, limit: int = 4096) -> Optional[str]:
    try:
        with open(path) as fh:
            return fh.read(limit).strip()
    except OSError:
        return None


def resolve(text: str, ident: Dict[str, str]) -> Dict[str, Any]:
    """Answer only an explicit, allowlisted read."""
    lowered = text.lower()
    target = None
    for alias, canon in sorted(ALIASES.items(), key=lambda kv: -len(kv[0])):
        if re.search(r"\b%s\b" % re.escape(alias), lowered):
            target = canon
            break
    for canon in ALLOWED:
        if re.search(r"\b%s\b" % re.escape(canon), lowered):
            target = target or canon
    if target not in ALLOWED and target not in ("network status", "services"):
        return {"ok": False, "error": "unsupported_system_read",
                "detail": "no typed read matches this request"}
    if target == "battery":
        data = _battery()
    elif target == "wifi":
        data = _net()
    elif target == "network status":
        data = _net()
    elif target == "memory":
        data = _memory()
    elif target == "temperature":
        data = _temperature()
    elif target == "kernel":
        v = _read("/proc/version")
        data = {"available": bool(v), "version": v}
    elif target == "uptime":
        v = _read("/proc/uptime")
        data = {"available": bool(v), "seconds": v.split()[0] if v else None}
    elif target == "device model":
        v = _read("/proc/device-tree/model")
        data = {"available": bool(v), "model": v}
    elif target == "storage":
        try:
            st = os.statvfs("/")
            data = {"available": True,
                    "free_bytes": st.f_bavail * st.f_frsize,
                    "total_bytes": st.f_blocks * st.f_frsize}
        except OSError:
            data = {"available": False}
    elif target == "bluetooth":
        data = {"available": os.path.isdir("/sys/class/bluetooth"),
                "adapters": sorted(os.listdir("/sys/class/bluetooth"))
                if os.path.isdir("/sys/class/bluetooth") else []}
    elif target == "services":
        try:
            out = subprocess.run(["systemctl", "is-system-running"],
                                 capture_output=True, text=True, timeout=5,
                                 stdin=subprocess.DEVNULL)
            data = {"available": True, "system_state": out.stdout.strip() or out.stderr.strip()}
        except (OSError, subprocess.SubprocessError):
            data = {"available": False}
    else:
        return {"ok": False, "error": "unsupported_system_read"}
    return {"ok": True, "action": "system_read", "target": target,
            "capability": "system_inspect", "data": data,
            "read_only": True, "identity": ident.get("app_id")}
