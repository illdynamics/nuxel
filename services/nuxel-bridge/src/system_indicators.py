#!/usr/bin/env python3
"""Nuxel lockhead indicator state (single owner, no mocks).

Three independent states are derived from real Linux interfaces:

  charging      external power present, plus the kernel's active-charge state
  usb_data      a real enumerated USB data link to a host, NOT merely a bound
                gadget or a stale vendor/UDC "configured" string
  live_console  an actually usable host-connected Live Console transport/session

Nothing here is inferred from "root is available".  In particular the live
console indicator requires a running ``nuxel-console`` process with an open fd
to the console tty (or a validated session lease written by that process) AND a
viable USB data link.  A bare ``/dev/ttyGS0`` node, a bound gadget, a lease that
outlives the cable, and root access are each insufficient.

USB data-link truth (A73) is a two-part contract:

  * POSITIVE proof — a configfs gadget is bound to a UDC whose state is exactly
    ``configured`` (completed host enumeration).  ``addressed`` is a pre-
    configuration handshake and is never sufficient; a charging-only cable never
    enumerates the controller.

  * PHYSICAL detach vetoes (A77) — Samsung 4.14 gadget drivers can leave a UDC
    state ``configured`` (and a bound gadget) intact after a physical cable
    pull.  The owner's SM-G975F detach log proves ``typec/port0/data_role``
    ALSO stays ``host [device]``, so the A73 Type-C role check alone can never
    clear the icons.  The independent signals that do change on this board are:

      - ``/sys/class/udc/<udc>/current_speed`` becomes ``UNKNOWN`` on detach
        while the stale UDC still reports ``configured``.
      - the wired power supplies (``ac``/``usb``) report ``online=0`` once VBUS
        is gone.  A bus-powered USB gadget cannot carry a data link without
        VBUS; wireless charging is excluded because it never carries data.
      - the Type-C resolved role is still honoured when it *does* report no
        ``[device]`` role.

    Absent signals are neutral (desktops/VMs and kernels without these
    attributes keep working); any explicit down signal fails closed.

    A74: the DWC3 debugfs ``link_state`` node is deliberately NOT read.  On the
    S10+ downstream 4.14 kernel, reading that debugfs attribute dereferences the
    DWC3 controller registers through debugfs while the controller can be
    runtime-suspended (FSYS0 / pd-fsys0a powered off) right after a physical
    detach.  That register access produces a bus ``SLVERR`` which this kernel
    escalates to a hard lockup on the reading CPU
    (``Watchdog detected hard LOCKUP on cpu 0``) and a watchdog reset — the
    reboot the owner observed.  The Type-C data_role read is a safe PMIC class
    attribute and is sufficient on its own.

Every root is overridable for the offline tests:

  NUXEL_SYS_POWER_SUPPLY   /sys/class/power_supply
  NUXEL_SYS_UDC            /sys/class/udc
  NUXEL_SYS_TTY            /sys/class/tty
  NUXEL_CONFIGFS_GADGET    /sys/kernel/config/usb_gadget
  NUXEL_PROC               /proc
  NUXEL_RUN                /run
  NUXEL_CONSOLE_TTY        ttyGS0
  NUXEL_ANDROID_USB_STATE  /sys/class/android_usb/android0/state
  NUXEL_SYS_TYPEC          /sys/class/typec
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


def _bound_udc_names() -> List[str]:
    """Controller names selected by bound configfs gadgets."""
    root = _root("NUXEL_CONFIGFS_GADGET", "/sys/kernel/config/usb_gadget")
    names = []
    for gadget in _list_dir(root):
        value = _read(os.path.join(root, gadget, "UDC"))
        if value and value.strip():
            names.append(value.strip())
    return sorted(set(names))


def _udc_states() -> Dict[str, Optional[str]]:
    root = _root("NUXEL_SYS_UDC", "/sys/class/udc")
    return {name: _read(os.path.join(root, name, "state")) for name in _udc_names()}


# Speeds a connected gadget controller can report.  ``UNKNOWN`` (or an empty
# file) is what the S10+ DWC3 controller leaves behind after a physical detach,
# even while the gadget framework still says ``configured``.
_UDC_CONNECTED_SPEEDS = {
    "low-speed", "full-speed", "high-speed", "super-speed", "super-speed-plus",
}


def _udc_speeds() -> Dict[str, Optional[str]]:
    root = _root("NUXEL_SYS_UDC", "/sys/class/udc")
    return {name: _read(os.path.join(root, name, "current_speed"))
            for name in _udc_names()}


def _udc_speed_is_connected(speed: Optional[str]) -> Optional[bool]:
    """True/False when a speed is readable; None when the attribute is absent.

    A readable but non-connected value (``UNKNOWN``, ``not attached``) is a
    positive detach signal.
    """
    if speed is None:
        return None
    return speed.strip().lower() in _UDC_CONNECTED_SPEEDS


# Wired charging supplies prove VBUS.  Wireless is excluded: it powers the
# battery but can never carry the USB data link.
_WIRED_VBUS_TYPES = {
    "usb", "usb-pd", "usb_typec", "usb_type_c", "usb_c", "mains", "ac", "dc",
    "charger", "quick_charge", "hv_charger",
}


def _wired_vbus_state() -> Optional[bool]:
    """True/False when wired supplies are readable; None when there are none.

    True  at least one wired supply reports online=1 (VBUS present)
    False every readable wired supply reports online=0 (no cable power)
    None  no readable wired supply attribute (desktop/VM/other kernel)
    """
    supplies = _read_power_supplies()
    seen = False
    for supply in supplies:
        if supply["type"] not in _WIRED_VBUS_TYPES:
            continue
        online = supply.get("online_raw")
        if online is None:
            continue
        seen = True
        if online == 1:
            return True
    return False if seen else None


def _android_usb_state() -> Optional[str]:
    """Vendor Android gadget state, retained for diagnostics only.

    This value can remain CONFIGURED after detach on vendor kernels, so it is
    never allowed to create a positive PC assertion.  Exact UDC `configured`
    state is the live target's enumeration proof.
    """
    configured = _root("NUXEL_ANDROID_USB_STATE",
                       "/sys/class/android_usb/android0")
    if os.path.isdir(configured):
        configured = os.path.join(configured, "state")
    return _read(configured)


# --------------------------------------------------------------------------- #
# Physical detach veto (A73): independent signals that must override a stale
# UDC "configured" / bound gadget after a real cable pull.
# --------------------------------------------------------------------------- #

def _typec_data_role_device() -> Optional[bool]:
    """True when a Type-C port reports the ``[device]`` data role.

    The bracket marks the *resolved* role: ``host [device]`` means the phone is
    a peripheral attached to a host partner.  After a physical detach the
    bracket disappears (``[none]``) — there is no partner.  Returns:

      True   at least one port is currently ``[device]``
      False  Type-C ports exist but none is ``[device]``
      None   the Type-C class is absent on this kernel
    """
    root = _root("NUXEL_SYS_TYPEC", "/sys/class/typec")
    ports: List[str] = []
    for name in _list_dir(root):
        # port0-partner / port0-cable are symlinked sub-objects, not ports.
        if name.endswith("-partner") or name.endswith("-cable"):
            continue
        if os.path.isdir(os.path.join(root, name)):
            ports.append(name)
    if not ports:
        return None
    for name in ports:
        role = _read(os.path.join(root, name, "data_role")) or ""
        if "[device]" in role.lower():
            return True
    return False


def _physical_data_link_veto() -> tuple:
    """Return (veto, evidence) where veto=True means an independent physical
    signal proves the data link is DOWN right now.

    Only the Type-C data_role is read (the DWC3 debugfs link_state was removed
    for A74 — reading it after detach can hard-lockup the downstream 4.14
    kernel, see the module docstring).  A signal that is absent/unreadable is
    neutral.
    """
    evidence: List[str] = []
    typec = _typec_data_role_device()
    if typec is False:
        evidence.append("typec:no-device-role")
    elif typec is True:
        evidence.append("typec:device-role")
    # A74: the DWC3 debugfs link_state read was removed (see module docstring).
    # The Type-C data_role is now the sole independent physical detach veto.
    veto = typec is False
    return veto, evidence


def usb_connection() -> Dict[str, Any]:
    """Return {pc_connected, source} for a real USB data link.

    A charging-only cable can still power the board but does not enumerate the
    device controller.  Requiring a configfs gadget bound to the SAME UDC whose
    state is exactly ``configured`` distinguishes completed host enumeration
    from VBUS, gadget preparation and the pre-configuration ``addressed`` state.

    A stale ``configured`` is then vetoed by independent physical signals (UDC
    speed, wired VBUS and Type-C data role), so a physical unplug clears the PC
    and Live Console icons promptly instead of leaving a ghost.  The vendor
    CONFIGURED value is diagnostic only.
    """
    gadgets = _bound_gadgets()
    bound_udcs = _bound_udc_names()
    android_state = _android_usb_state()
    veto, physical_evidence = _physical_data_link_veto()
    if not gadgets or not bound_udcs:
        return {"pc_connected": False, "source": "unavailable:gadget-not-bound",
                "bound_gadgets": [], "udc_states": {}, "udc_speeds": {},
                "vbus_present": None,
                "android_usb_state": android_state,
                "physical": physical_evidence}

    states = _udc_states()
    speeds = _udc_speeds()
    vbus = _wired_vbus_state()
    data_states = {name: state for name, state in states.items()
                   if name in bound_udcs and state and
                   state.strip().lower() == "configured"}
    base = {
        "bound_gadgets": gadgets,
        "udc_states": states,
        "udc_speeds": speeds,
        "vbus_present": vbus,
        "android_usb_state": android_state,
        "physical": physical_evidence,
    }
    if data_states:
        name = sorted(data_states)[0]
        speed = speeds.get(name)
        if veto:
            return dict(base, **{
                "pc_connected": False,
                "source": "sysfs:udc:" + name + ":configured-vetoed-by-physical-detach",
            })
        if _udc_speed_is_connected(speed) is False:
            evidence = list(physical_evidence) + [
                "udc:speed-" + (speed or "unknown").strip().lower()]
            return dict(base, **{
                "physical": evidence,
                "pc_connected": False,
                "source": "sysfs:udc:" + name + ":configured-vetoed-by-udc-speed",
            })
        if vbus is False:
            evidence = list(physical_evidence) + ["power:wired-vbus-off"]
            return dict(base, **{
                "physical": evidence,
                "pc_connected": False,
                "source": "sysfs:udc:" + name + ":configured-vetoed-by-no-vbus",
            })
        return dict(base, **{
            "pc_connected": True,
            "source": "sysfs:udc:" + name + ":" + str(data_states[name]).strip().lower(),
        })
    if not states:
        return dict(base, **{"pc_connected": False,
                             "source": "unavailable:no-udc-state"})
    rendered = ",".join("%s=%s" % (k, v) for k, v in sorted(states.items()))
    return dict(base, **{"pc_connected": False, "source": "sysfs:udc:" + rendered})


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


def _lease_fields() -> Dict[str, str]:
    runroot = _root("NUXEL_RUN", "/run")
    for name in ("live-console-session",):
        path = os.path.join(runroot, "nuxel", name)
        text = _read(path)
        if not text:
            continue
        fields: Dict[str, str] = {}
        for token in text.replace("\n", " ").split():
            key, sep, value = token.partition("=")
            if sep:
                fields[key.lower()] = value
        return fields
    return {}


def _proc_start_ticks(pid: int, procroot: str) -> Optional[int]:
    """Return Linux /proc/<pid>/stat field 22 without trusting comm spacing."""
    text = _read(os.path.join(procroot, str(pid), "stat"))
    if not text:
        return None
    end = text.rfind(")")
    if end < 0:
        return None
    fields = text[end + 1:].strip().split()
    # fields[0] is stat field 3 (state); field 22 is therefore index 19.
    if len(fields) <= 19:
        return None
    try:
        return int(fields[19])
    except (TypeError, ValueError):
        return None


def live_console(pc_connected: Optional[bool] = None) -> Dict[str, Any]:
    """Return the Live Console model with three distinct layers (A73-02):

      service_armed        the nuxel-console daemon is running (process exists)
      transport_connected  the console tty is registered AND the USB data link
                           is up (gadget bound + UDC configured, not vetoed)
      session_active       the daemon holds the console tty fd, or a validated
                           session lease names a live nuxel-console PID

    The display predicate (``active``) requires ALL THREE: a prestarted console
    service, an open gadget TTY, a stale pid/lease or an enabled service without
    an attached host is NOT sufficient.  After a physical detach it turns OFF
    promptly even while the daemon remains enabled.

    The console daemon itself is never terminated just to extinguish its icon.
    """
    procroot = _root("NUXEL_PROC", "/proc")
    ttynames = _console_tty_basenames()
    ttyset = {"/dev/" + name for name in ttynames} | set(ttynames)

    pids: List[int] = []
    tty_pids: List[int] = []
    service_pids: List[int] = []
    for pid in _list_dir(procroot):
        if not pid.isdigit():
            continue
        command = _cmdline(pid, procroot)
        if "nuxel-console" not in command:
            continue
        service_pids.append(int(pid))
        fdroot = os.path.join(procroot, pid, "fd")
        for fd in _list_dir(fdroot):
            try:
                target = os.readlink(os.path.join(fdroot, fd))
            except OSError:
                continue
            base = os.path.basename(target)
            if target in ttyset or base in ttynames:
                pids.append(int(pid))
                tty_pids.append(int(pid))
                break

    service_armed = bool(service_pids)

    if pc_connected is None:
        pc_connected = bool(usb_connection()["pc_connected"])
    transport_connected = bool(pc_connected)

    # Validate the session lease independently of the tty-fd scan (defeats PID
    # reuse and stale markers); a serving/active lease plus a live owner counts.
    fields = _lease_fields()
    try:
        lease_pid = int(fields.get("pid", fields.get("session_pid", "0")))
        lease_start = int(fields.get("start_ticks", "0"))
    except (TypeError, ValueError):
        lease_pid, lease_start = 0, 0
    lease_valid = False
    if fields.get("state", "").lower() in ("", "serving", "active"):
        if lease_pid and _pid_is_alive(lease_pid, procroot):
            if "nuxel-console" in _cmdline(str(lease_pid), procroot):
                if not lease_start or _proc_start_ticks(lease_pid, procroot) == lease_start:
                    lease_valid = True

    session_active = bool(tty_pids) or lease_valid
    if lease_valid and lease_pid not in pids:
        pids.append(lease_pid)

    if not pc_connected:
        # Fail closed on detach even if the daemon and its lease are still alive.
        return {
            "active": False,
            "service_armed": service_armed,
            "transport_connected": False,
            "session_active": session_active,
            "source": "inactive:no-usb-data-link",
            "pids": sorted(set(pids)),
        }

    ttyroot = _root("NUXEL_SYS_TTY", "/sys/class/tty")
    tty_registered = any(os.path.exists(os.path.join(ttyroot, name)) for name in ttynames)
    if not tty_registered:
        return {
            "active": False,
            "service_armed": service_armed,
            "transport_connected": False,
            "session_active": session_active,
            "source": "inactive:console-tty-missing",
            "pids": sorted(set(pids)),
        }

    if not session_active:
        return {
            "active": False,
            "service_armed": service_armed,
            "transport_connected": True,
            "session_active": False,
            "source": "inactive:no-console-session",
            "pids": sorted(set(pids)),
        }

    if tty_pids:
        return {
            "active": True,
            "service_armed": service_armed,
            "transport_connected": True,
            "session_active": True,
            "source": "proc:nuxel-console:tty",
            "pids": sorted(set(pids)),
        }

    return {
        "active": True,
        "service_armed": service_armed,
        "transport_connected": True,
        "session_active": True,
        "source": "lease:nuxel-console:serving",
        "pids": sorted(set(pids)),
    }



def _proc_net_sockets(proc_root: str = "/proc") -> List[Dict[str, Any]]:
    """Return TCP socket lines from /proc/net/tcp and /proc/net/tcp6."""
    out: List[Dict[str, Any]] = []
    for name in ("tcp", "tcp6"):
        text = _read(os.path.join(proc_root, "net", name))
        if not text:
            continue
        for line in text.splitlines():
            if "local_address" in line:
                continue
            fields = line.split()
            if len(fields) < 4:
                continue
            host_hex, _, port_hex = fields[1].partition(":")
            try:
                port = int(port_hex, 16)
            except ValueError:
                continue
            out.append({
                "proto": name,
                "local_hex": host_hex,
                "port": port,
                "state": fields[3].upper(),
            })
    return out


def _established_ssh_sessions(proc_root: str = "/proc", port: int = 22) -> List[Dict[str, Any]]:
    """Return ESTABLISHED TCP connections on the SSH port (state 01)."""
    return [s for s in _proc_net_sockets(proc_root)
            if s["port"] == int(port) and s["state"] == "01"]


_TRANSPORT_CACHE: Dict[str, Any] = {"at": 0.0}
_TRANSPORT_CACHE_TTL_S = 5.0

def bluetooth_indicator() -> Dict[str, Any]:
    """Return proof-only Bluetooth state for the lockscreen indicator.

    This module is imported by both the native host and the loopback HTTP
    bridge, so it must not open BlueZ directly: that would duplicate the
    authoritative ``BluetoothConnector`` logic.  The bridge/server injects the
    provider result through ``NUXEL_BLUETOOTH_STATE``; without a fresh value the
    indicator is explicitly UNKNOWN and stays hidden.

    Expected JSON: ``{"powered": true|false|null, "state": "...",
    "discovering": bool, "source": "..."}``.  A malformed or absent document is
    never interpreted as OFF.
    """
    path = os.environ.get("NUXEL_BLUETOOTH_STATE", "/run/nuxel/bluetooth-indicator.json")
    raw = _read(path)
    if not raw:
        return {"powered": None, "state": "unknown", "discovering": False,
                "source": "unavailable:no-provider-state"}
    try:
        import json as _json
        doc = _json.loads(raw)
    except Exception as exc:  # noqa: BLE001
        return {"powered": None, "state": "unknown", "discovering": False,
                "source": "unavailable:invalid-provider-state:%s" % exc}
    if not isinstance(doc, dict):
        return {"powered": None, "state": "unknown", "discovering": False,
                "source": "unavailable:invalid-provider-state"}
    powered = doc.get("powered")
    if powered not in (True, False, None):
        powered = None
    return {
        "powered": powered,
        "state": str(doc.get("state") or ("on" if powered else "off" if powered is False else "unknown")),
        "discovering": bool(doc.get("discovering")),
        "source": str(doc.get("source") or "provider-state"),
    }


def _cached_tri_link_facts() -> Dict[str, Any]:
    global _TRANSPORT_CACHE
    import time as _time
    now = _time.monotonic()
    cached = _TRANSPORT_CACHE
    if cached.get("at") and now - cached.get("at", 0.0) < _TRANSPORT_CACHE_TTL_S:
        return cached
    facts: Dict[str, Any] = {"wifi_status": "unknown", "usb_status": "unknown"}
    try:
        import importlib
        tl = importlib.import_module("tri_link_status")
        wl = tl.wifi_status()
        us = tl.usb_status()
        facts["wifi_status"] = wl.get("status", "unknown")
        facts["usb_status"] = us.get("status", "unknown")
    except Exception as exc:  # noqa: BLE001
        facts["wifi_status"] = "tri-link-status-unavailable"
        facts["usb_status"] = "tri-link-status-unavailable"
        facts["error"] = str(exc)
    facts["at"] = now
    _TRANSPORT_CACHE = facts
    return facts


def console_transports(serial_live: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Return independent transport states for the lockscreen console icons.

    Semantics (documented deliberately):

      serial_active   the USB CDC-ACM live console has an actual session: the
                      nuxel-console process holds the console tty fd (or a
                      validated serving lease) AND the USB data link is up.
                      This is exactly the existing live-console display predicate.

      wlan_active     the project defines a live WLAN console as a reachable,
                      key-only sshd listener on a non-loopback Wi-Fi interface.
                      It is true when that listener is present; the number of
                      currently ESTABLISHED SSH sessions is reported separately
                      so a listening-but-idle console is not conflated with an
                      active remote session.

      usb_active      an SSH listener over a USB network interface.  On the
                      current 4.14.253 kernel the USB-network gadget is blocked
                      (NCM teardown panic), so this is reported as blocked and
                      never presented as active.
    """
    if serial_live is None:
        serial_live = live_console()
    serial_active = bool(serial_live.get("active"))
    serial_source = serial_live.get("source", "unknown")

    # WLAN/USB reachability uses the tri-link module's definition, cached for a
    # few seconds so status polling never re-reads /proc/config.gz on every tick.
    facts = _cached_tri_link_facts()
    wifi_detail = facts.get("wifi_status", "unknown")
    wifi_ready = wifi_detail == "AVAILABLE"
    usb_detail = facts.get("usb_status", "blocked-kernel")
    usb_ready = usb_detail == "AVAILABLE"

    established = _established_ssh_sessions()

    return {
        "serial": {
            "active": serial_active,
            "source": serial_source,
            "pids": serial_live.get("pids", []),
        },
        "usb": {
            "active": usb_ready,
            "source": usb_detail,
            "sessions": 0,
        },
        "wlan": {
            "active": wifi_ready,
            "source": wifi_detail,
            "sessions": len(established),
        },
    }


def _read_state_file(path: str) -> Dict[str, Any]:
    raw = _read(path)
    if not raw:
        return {}
    try:
        import json as _json
        data = _json.loads(raw)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def connection_mode_state(run_root: str = "/run") -> Dict[str, Any]:
    """Read the persisted connection-mode selection and activation result.

    Selection is persisted at /run/nuxel/connection-mode.json; activation truth
    is written by the USB-mode helper at /run/nuxel/usb-mode.state.  A selected
    File Transfer mode is NOT "active" until the helper records success.
    """
    base = os.path.join(run_root, "nuxel")
    selection = _read_state_file(os.path.join(base, "connection-mode.json"))
    activation = _read_state_file(os.path.join(base, "usb-mode.state"))
    selected = str(selection.get("mode", "charging"))
    if selected not in ("charging", "file_transfer"):
        selected = "charging"
    return {
        "selected": selected,
        "transition_in_progress": bool(selection.get("transition_in_progress")),
        "host_connected": bool(usb_connection()["pc_connected"]),
        "endpoint_state": activation.get("endpoint_state", "inactive"),
        "active": bool(activation.get("active")),
        "source": activation.get("source", "unavailable:not-activated"),
        "last_error": activation.get("error"),
    }

def sound_mode_state() -> Dict[str, Any]:
    """Read the hardware chord's persisted sound mode truthfully.

    The button manager writes normal|vibrate|silent to
    /var/lib/nuxel/audio/sound-mode.  A missing/unreadable file is UNKNOWN,
    never a guessed 'normal'.  'vibrate' is a SELECTED mode; it is not proof
    that a physical vibrator actuated.
    """
    root = _root("NUXEL_AUDIO_DIR", "/var/lib/nuxel/audio")
    path = os.path.join(root, "sound-mode")
    raw = _read(path)
    if raw is None:
        return {"mode": "unknown", "selected": None, "source": "unavailable:%s" % path,
                "haptics_verified": False}
    mode = raw.strip().lower()
    if mode not in ("normal", "vibrate", "silent"):
        return {"mode": "unknown", "selected": None, "source": "invalid:%s" % path,
                "haptics_verified": False}
    return {"mode": mode, "selected": mode, "source": path,
            "haptics_verified": False,
            "note": "selected sound mode; physical vibration is not claimed"}


def get_indicators() -> Dict[str, Any]:
    power = power_state()
    usb = usb_connection()
    console = live_console(bool(usb["pc_connected"]))
    transports = console_transports(console)
    mode = connection_mode_state()
    bluetooth = bluetooth_indicator()
    sound = sound_mode_state()
    return {
        "sound_mode": sound,
        "bluetooth": {
            "powered": bluetooth["powered"],
            "state": bluetooth["state"],
            "discovering": bluetooth["discovering"],
            "source": bluetooth["source"],
        },
        "charging": {
            "external_power": bool(power["external_power"]),
            "charging": bool(power["charging"]),
            "battery_level": power["battery_level"],
            "source": power["source"],
        },
        "usb_data": {
            "pc_connected": bool(usb["pc_connected"]),
            "source": usb["source"],
            "physical": usb.get("physical", []),
            "vbus_present": usb.get("vbus_present"),
            "udc_speeds": usb.get("udc_speeds", {}),
        },
        "live_console": {
            "active": bool(console["active"]),
            "service_armed": bool(console["service_armed"]),
            "transport_connected": bool(console["transport_connected"]),
            "session_active": bool(console["session_active"]),
            "source": console["source"],
            "pids": console.get("pids", []),
        },
        "console_transports": {
            "serial": {
                "active": bool(transports["serial"]["active"]),
                "source": transports["serial"]["source"],
                "pids": transports["serial"].get("pids", []),
            },
            "usb": {
                "active": bool(transports["usb"]["active"]),
                "source": transports["usb"]["source"],
                "sessions": transports["usb"].get("sessions", 0),
            },
            "wlan": {
                "active": bool(transports["wlan"]["active"]),
                "source": transports["wlan"]["source"],
                "sessions": transports["wlan"].get("sessions", 0),
            },
        },
        "file_transfer": {
            "active": bool(mode["active"]),
            "selected": mode["selected"],
            "endpoint_state": mode["endpoint_state"],
            "source": mode["source"],
            "error": mode["last_error"],
        },
        "connection_mode": {
            "selected": mode["selected"],
            "transition_in_progress": mode["transition_in_progress"],
            "host_connected": mode["host_connected"],
            "endpoint_state": mode["endpoint_state"],
            "last_error": mode["last_error"],
        },
        "sources": {
            "power": power["source"],
            "usb": usb["source"],
            "live_console": console["source"],
            "console_serial": transports["serial"]["source"],
            "console_usb": transports["usb"]["source"],
            "console_wlan": transports["wlan"]["source"],
            "file_transfer": mode["source"],
            "bluetooth": bluetooth["source"],
        },
    }


if __name__ == "__main__":  # pragma: no cover - operator smoke helper
    import json
    print(json.dumps(get_indicators(), sort_keys=True))
