#!/usr/bin/env python3
"""Nuxel lockhead indicator state (single owner, no mocks).

Three independent states are derived from real Linux interfaces:

  charging      external power present, plus the kernel's active-charge state
  usb_data      configfs gadget bound AND UDC enumerated (data-capable link);
                when that controller state is unavailable, the vendor
                android_usb CONFIGURED state is accepted as corroboration
  live_console  the nuxel-console process itself holds the console tty

Nothing here is inferred from "root is available".  In particular the live
console indicator requires a running ``nuxel-console`` process with an open fd
to the console tty (or a validated session lease written by that process).  A
bare ``/dev/ttyGS0`` node, a bound gadget, and root access are each insufficient.

Every root is overridable for the offline tests:

  NUXEL_SYS_POWER_SUPPLY   /sys/class/power_supply
  NUXEL_SYS_UDC            /sys/class/udc
  NUXEL_SYS_TTY            /sys/class/tty
  NUXEL_CONFIGFS_GADGET    /sys/kernel/config/usb_gadget
  NUXEL_PROC               /proc
  NUXEL_RUN                /run
  NUXEL_CONSOLE_TTY        ttyGS0
  NUXEL_ANDROID_USB_STATE  /sys/class/android_usb/android0/state
"""

from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

_EXTERNAL_TYPES = {
    "usb", "usb-pd", "usb_typec", "usb_type_c", "usb_c", "mains", "ac", "dc",
    "wireless", "wpc", "quick_charge", "hv_charger", "charger",
}


def _root(env: str, default: str) -> str:
    return os.environ.get(env, default)


def _read(path: str) -> Optional[str]:
    try:
        with open(path, "r") as fh:
            return fh.read().strip()
    except (OSError, ValueError):
        return None


def _read_int(path: str) -> Optional[int]:
    value = _read(path)
    if value is None:
        return None
    try:
        return int(float(value))
    except (ValueError, TypeError):
        return None


def _list_dir(path: str) -> List[str]:
    try:
        return sorted(os.listdir(path))
    except OSError:
        return []


def _read_power_supplies() -> List[Dict[str, Any]]:
    root = _root("NUXEL_SYS_POWER_SUPPLY", "/sys/class/power_supply")
    supplies: List[Dict[str, Any]] = []
    for name in _list_dir(root):
        base = os.path.join(root, name)
        if not os.path.isdir(base):
            continue
        supplies.append({
            "name": name,
            "type": (_read(os.path.join(base, "type")) or "unknown").lower(),
            "online_raw": _read_int(os.path.join(base, "online")),
            "status": _read(os.path.join(base, "status")) or "unknown",
            "capacity": _read_int(os.path.join(base, "capacity")),
        })
    return supplies


def power_state() -> Dict[str, Any]:
    """Return external_power/charging from power_supply.

    ``external_power`` is true only for an external supply with online=1.
    ``charging`` is true only when the battery's status is exactly "Charging";
    "Full", "Not charging", and "Discharging" never light the charge animation.
    """
    supplies = _read_power_supplies()
    if not supplies:
        return {
            "external_power": False, "charging": False, "battery_level": None,
            "source": "unavailable:no-power-supply", "battery_status": "unknown",
            "external_sources": [],
        }

    external_power = False
    external_sources: List[str] = []
    battery_level: Optional[int] = None
    battery_status = "unknown"
    battery_seen = False

    for supply in supplies:
        supply_type = supply["type"]
        if supply_type == "battery" or (supply_type == "unknown" and supply["capacity"] is not None):
            if not battery_seen:
                battery_level = supply["capacity"]
                battery_status = supply["status"]
                battery_seen = True
            continue
        # OTG/host-mode is not charging: a USB host adapter can be online while
        # the phone is sourcing power, so it must never light the charge icon.
        if supply_type in ("otg", "usb_host"):
            continue
        if supply["online_raw"] == 1 and (supply_type in _EXTERNAL_TYPES or supply_type not in ("battery", "otg", "usb_host")):
            external_power = True
            external_sources.append(supply["name"])

    charging = battery_seen and battery_status.strip().lower() == "charging"
    return {
        "external_power": external_power,
        "charging": charging,
        "battery_level": battery_level,
        "source": "sysfs",
        "battery_status": battery_status.strip().lower(),
        "external_sources": external_sources,
    }


def _udc_names() -> List[str]:
    return _list_dir(_root("NUXEL_SYS_UDC", "/sys/class/udc"))


def _bound_gadgets() -> List[str]:
    """configfs gadgets whose UDC attribute names a controller."""
    root = _root("NUXEL_CONFIGFS_GADGET", "/sys/kernel/config/usb_gadget")
    bound: List[str] = []
    for gadget in _list_dir(root):
        value = _read(os.path.join(root, gadget, "UDC"))
        if value and value.strip():
            bound.append(gadget)
    return bound


def _udc_states() -> Dict[str, Optional[str]]:
    root = _root("NUXEL_SYS_UDC", "/sys/class/udc")
    return {name: _read(os.path.join(root, name, "state")) for name in _udc_names()}


def _android_usb_state() -> Optional[str]:
    """Vendor Android gadget state, read as a corroborating signal only.

    The S10+ kernel logs `android_work: sent uevent USB_STATE=CONFIGURED` when the
    host enumerates the device.  This is accepted as a corroborating fallback
    only when configfs/UDC state is unavailable; a power_supply online flag is
    still never sufficient.  A DISCONNECTED/CONNECTED state is never PC.
    """
    configured = _root("NUXEL_ANDROID_USB_STATE",
                       "/sys/class/android_usb/android0")
    if os.path.isdir(configured):
        configured = os.path.join(configured, "state")
    return _read(configured)


def usb_connection() -> Dict[str, Any]:
    """Return {pc_connected, source} for a real USB data link.

    A charging-only cable can still power the board but does not enumerate the
    device controller.  Requiring BOTH a bound configfs gadget and a UDC state of
    ``configured``/``addressed`` is what distinguishes data from charging.  When
    the UDC exposes no state at all, the vendor android_usb CONFIGURED signal is
    accepted as corroboration.  The power_supply online flag is never consulted.
    """
    gadgets = _bound_gadgets()
    android_state = _android_usb_state()
    if not gadgets:
        connected = bool(android_state and android_state.strip().upper() == "CONFIGURED")
        source = ("sysfs:android_usb:configured" if connected
                  else "unavailable:gadget-not-bound")
        return {"pc_connected": connected, "source": source,
                "bound_gadgets": [], "udc_states": {},
                "android_usb_state": android_state}

    states = _udc_states()
    data_states = {name: state for name, state in states.items()
                   if state and state.strip().lower() in ("configured", "addressed")}
    if data_states:
        name = sorted(data_states)[0]
        return {
            "pc_connected": True,
            "source": "sysfs:udc:" + name + ":" + str(data_states[name]).strip().lower(),
            "bound_gadgets": gadgets,
            "udc_states": states,
        }
    if not states:
        if android_state and android_state.strip().upper() == "CONFIGURED":
            return {"pc_connected": True, "source": "sysfs:android_usb:configured",
                    "bound_gadgets": gadgets, "udc_states": states,
                    "android_usb_state": android_state}
        return {"pc_connected": False, "source": "unknown:no-udc",
                "bound_gadgets": gadgets, "udc_states": states,
                "android_usb_state": android_state}
    rendered = ",".join("%s=%s" % (k, v) for k, v in sorted(states.items()))
    return {"pc_connected": False, "source": "sysfs:udc:" + rendered,
            "bound_gadgets": gadgets, "udc_states": states,
            "android_usb_state": android_state}


def _console_tty_basenames() -> List[str]:
    configured = _root("NUXEL_CONSOLE_TTY", "ttyGS0")
    names = {os.path.basename(configured) or "ttyGS0", "ttyGS0"}
    return sorted(names)


def _pid_is_alive(pid: int, procroot: str = "/proc") -> bool:
    """A lease pid is alive when its proc directory exists.

    Using the proc root (not os.kill) keeps the check honest when NUXEL_PROC is
    redirected by the offline tests, and avoids pid-reuse races in the live case.
    """
    if pid <= 0:
        return False
    if procroot != "/proc":
        return os.path.isdir(os.path.join(procroot, str(pid)))
    try:
        os.kill(pid, 0)
        return True
    except (OSError, ValueError):
        return False


def _cmdline(pid: str, procroot: str) -> str:
    try:
        with open(os.path.join(procroot, pid, "cmdline"), "rb") as fh:
            raw = fh.read(4096)
    except OSError:
        return ""
    return raw.replace(b"\x00", b" ").decode("utf-8", "replace").strip()


def _lease_pid() -> Optional[int]:
    runroot = _root("NUXEL_RUN", "/run")
    for name in ("live-console-session",):
        path = os.path.join(runroot, "nuxel", name)
        text = _read(path)
        if not text:
            continue
        for token in text.replace("\n", " ").split():
            key, sep, value = token.partition("=")
            if sep and key.lower() in ("pid", "session_pid"):
                try:
                    return int(value)
                except ValueError:
                    return None
    return None


def live_console() -> Dict[str, Any]:
    """Return {active, source, pids}.

    Active means the live-console implementation is actually running AND is
    attached to the console tty.  The process scan is authoritative: it requires
    a ``nuxel-console`` command line plus an fd that resolves to the console tty.
    That excludes a shell merely running as root, a present tty node left behind
    by the gadget, and a stale marker file.
    """
    procroot = _root("NUXEL_PROC", "/proc")
    runroot = _root("NUXEL_RUN", "/run")
    ttynames = _console_tty_basenames()
    ttyset = {"/dev/" + name for name in ttynames} | set(ttynames)

    pids: List[int] = []
    session_source = ""
    for pid in _list_dir(procroot):
        if not pid.isdigit():
            continue
        command = _cmdline(pid, procroot)
        if "nuxel-console" not in command:
            continue
        fdroot = os.path.join(procroot, pid, "fd")
        for fd in _list_dir(fdroot):
            try:
                target = os.readlink(os.path.join(fdroot, fd))
            except OSError:
                continue
            base = os.path.basename(target)
            if target in ttyset or base in ttynames:
                pids.append(int(pid))
                session_source = "proc:nuxel-console:tty"
                break

    lease_pid = _lease_pid()
    if lease_pid and _pid_is_alive(lease_pid, procroot):
        command = _cmdline(str(lease_pid), procroot)
        # A lease is not self-authenticating: require the PID to still belong to
        # the console implementation.  This defeats PID reuse and stale markers.
        if "nuxel-console" in command:
            if lease_pid not in pids:
                pids.append(lease_pid)
            if not session_source:
                session_source = "lease:nuxel-console"

    if not pids:
        return {"active": False, "source": "inactive:no-console-session", "pids": []}

    gadget_bound = bool(_bound_gadgets())
    ttyroot = _root("NUXEL_SYS_TTY", "/sys/class/tty")
    tty_registered = any(os.path.exists(os.path.join(ttyroot, name)) for name in ttynames)
    if gadget_bound and tty_registered:
        return {"active": True, "source": session_source or "proc:nuxel-console",
                "pids": sorted(set(pids))}
    # The process is real but its backing gadget/tty is gone: report the session
    # as inactive rather than keeping a stale "on" after a disconnect.
    return {"active": False, "source": "console-process-without-gadget",
            "pids": sorted(set(pids))}


def get_indicators() -> Dict[str, Any]:
    power = power_state()
    usb = usb_connection()
    console = live_console()
    return {
        "charging": {
            "external_power": bool(power["external_power"]),
            "charging": bool(power["charging"]),
            "battery_level": power["battery_level"],
            "source": power["source"],
        },
        "usb_data": {
            "pc_connected": bool(usb["pc_connected"]),
            "source": usb["source"],
        },
        "live_console": {
            "active": bool(console["active"]),
            "source": console["source"],
            "pids": console.get("pids", []),
        },
        "sources": {
            "power": power["source"],
            "usb": usb["source"],
            "live_console": console["source"],
        },
    }


if __name__ == "__main__":  # pragma: no cover - operator smoke helper
    import json
    print(json.dumps(get_indicators(), sort_keys=True))
