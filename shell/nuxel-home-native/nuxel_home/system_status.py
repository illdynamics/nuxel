"""Nuxel Home — System Status Reader

Reads real system status from:
  - /sys/class/net/*           → network interfaces (WiFi, Ethernet)
  - /sys/class/power_supply/*  → battery status
  - /proc/net/route            → default gateway detection

Falls back to the HTTP bridge (127.0.0.1:8080) when sysfs paths
aren't available (e.g., in a container or VM without host sysfs).

Polling is done via GLib.timeout_add_seconds rather than raw
threading to stay on the main loop and avoid GObject thread-safety
issues.
"""

import json
import logging
import os
import time
from typing import Any, Dict, Optional

from gi.repository import GLib

logger = logging.getLogger(__name__)

HTTP_BRIDGE_URL = "http://127.0.0.1:8080/api/v1/phone/status"

# ── Network ──────────────────────────────────────────────────────


def list_network_interfaces() -> Dict[str, str]:
    """Return dict mapping iface name → 'wifi', 'ethernet', 'loopback', 'unknown'."""
    SYS_NET = "/sys/class/net"
    ifaces = {}
    if not os.path.isdir(SYS_NET):
        return ifaces

    for name in os.listdir(SYS_NET):
        if name == "lo":
            ifaces[name] = "loopback"
            continue
        uevent_path = os.path.join(SYS_NET, name, "uevent")
        if os.path.isfile(uevent_path):
            try:
                with open(uevent_path, "r") as fh:
                    data = fh.read()
                if "DEVTYPE=wlan" in data or "INTERFACE=wlan" in data or "wl" in name:
                    ifaces[name] = "wifi"
                elif "eth" in name or "en" in name:
                    ifaces[name] = "ethernet"
                elif "usb" in name:
                    ifaces[name] = "usb"
                else:
                    ifaces[name] = "unknown"
            except OSError:
                ifaces[name] = "unknown"
        else:
            ifaces[name] = "unknown"
    return ifaces


def is_iface_up(iface: str) -> bool:
    """Check if a network interface is up (operstate = 'up')."""
    op_path = f"/sys/class/net/{iface}/operstate"
    if os.path.isfile(op_path):
        try:
            with open(op_path, "r") as fh:
                return fh.read().strip().lower() == "up"
        except OSError:
            pass
    return False


def has_default_gateway() -> bool:
    """Check /proc/net/route for a non-zero default gateway."""
    try:
        with open("/proc/net/route", "r") as fh:
            for line in fh.readlines()[1:]:  # skip header
                parts = line.strip().split()
                if len(parts) >= 3 and parts[1] == "00000000" and parts[2] != "00000000":
                    return True
    except OSError:
        pass
    return False


def get_network_status() -> Dict[str, Any]:
    """Return network connectivity summary."""
    ifaces = list_network_interfaces()
    wifi_up = any(
        is_iface_up(name)
        for name, kind in ifaces.items() if kind == "wifi"
    )
    eth_up = any(
        is_iface_up(name)
        for name, kind in ifaces.items() if kind == "ethernet"
    )
    has_gw = has_default_gateway()
    connected = (wifi_up or eth_up) and has_gw

    return {
        "connected": connected,
        "wifi": wifi_up,
        "ethernet": eth_up,
        "has_gateway": has_gw,
        "interfaces": ifaces,
    }


# ── Battery ──────────────────────────────────────────────────────


def get_battery_status() -> Dict[str, Any]:
    """Return battery level (0–100) and charging status from sysfs."""
    SUPPLY = "/sys/class/power_supply"
    if not os.path.isdir(SUPPLY):
        return {"level": 100, "charging": True, "source": "fallback"}

    for name in os.listdir(SUPPLY):
        supply_path = os.path.join(SUPPLY, name)
        type_path = os.path.join(supply_path, "type")
        if not os.path.isfile(type_path):
            continue
        try:
            with open(type_path, "r") as fh:
                supply_type = fh.read().strip()
        except OSError:
            continue

        if supply_type == "Battery":
            level = 100
            charging = False
            try:
                with open(os.path.join(supply_path, "capacity"), "r") as fh:
                    level = int(fh.read().strip())
            except (OSError, ValueError):
                pass
            try:
                with open(os.path.join(supply_path, "status"), "r") as fh:
                    status = fh.read().strip()
                charging = status in ("Charging", "Full")
            except OSError:
                pass
            return {
                "level": max(0, min(100, level)),
                "charging": charging,
                "source": "sysfs",
            }

    # No battery found — likely desktop/VM
    return {"level": 100, "charging": True, "source": "no_battery"}


# ── Time ─────────────────────────────────────────────────────────


def get_current_time() -> str:
    """Return current local time as HH:MM string."""
    return time.strftime("%H:%M")


# ── HTTP Bridge fallback (blocking, called from GLib timeout) ────


def _fetch_status_from_bridge_impl() -> Optional[Dict[str, Any]]:
    """Synchronous fetch of status from the HTTP bridge.

    Called from within a GLib timeout (which can tolerate blocking
    I/O as long as it returns quickly). We use urllib here to avoid
    pulling in aiohttp dependencies and to keep everything on one
    thread.
    """
    try:
        import urllib.request
        req = urllib.request.Request(HTTP_BRIDGE_URL, headers={"Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=3) as resp:
            return json.loads(resp.read().decode())
    except Exception as exc:
        logger.debug("HTTP bridge fallback failed: %s", exc)
        return None


# ── Combined status ──────────────────────────────────────────────


def get_full_status() -> Dict[str, Any]:
    """Combine network, battery, and time into a single status dict."""
    net = get_network_status()
    bat = get_battery_status()
    return {
        "time": get_current_time(),
        "network": net,
        "battery": bat,
        "notification_count": 0,  # populated by caller
    }


def get_full_status_with_fallback() -> Dict[str, Any]:
    """Try HTTP bridge first, fall back to sysfs.

    This is suitable for use from a GLib timeout callback.
    """
    bridge = _fetch_status_from_bridge_impl()
    if bridge is not None:
        return bridge
    return get_full_status()


# ── StatusPoller: GLib-based periodic status updates ─────────────


class StatusPoller:
    """Periodically polls system status via GLib.timeout_add_seconds.

    Calls the provided callback with a status dict every N seconds.
    This replaces any raw threading.Timer approach to stay on the
    main GTK thread.
    """

    def __init__(self, interval_s: int, callback):
        """
        Args:
            interval_s: Polling interval in seconds.
            callback: Callable receiving a single status dict argument.
        """
        self._interval = interval_s
        self._callback = callback
        self._timer_id: Optional[int] = None
        self._running = False

    def start(self) -> None:
        """Begin periodic polling."""
        if self._running:
            return
        self._running = True
        # Fire immediately, then repeat
        self._tick()
        self._timer_id = GLib.timeout_add_seconds(self._interval, self._tick)
        logger.info("StatusPoller started (interval=%ds)", self._interval)

    def stop(self) -> None:
        """Remove the GLib timeout."""
        if not self._running:
            return
        self._running = False
        if self._timer_id is not None:
            GLib.source_remove(self._timer_id)
            self._timer_id = None
        logger.info("StatusPoller stopped")

    def _tick(self) -> bool:
        """Fetch status and invoke callback.

        Returns True to keep the GLib timeout alive.
        """
        if not self._running:
            return False
        try:
            status = get_full_status()
            self._callback(status)
        except Exception as exc:
            logger.warning("StatusPoller tick error: %s", exc)
        return True
