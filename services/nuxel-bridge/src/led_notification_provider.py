#!/usr/bin/env python3
"""Single owner for notification lights (PWNAGE-45000).

Truth first: the S10+ kernel in this image exposes only the rear torch classes
(`leds-sec1`, `torch-sec1`) and no front notification LED / RGB class.  This
provider therefore reports NOT_SUPPORTED_ON_DEVICE for a hardware notification
LED, and NEVER borrows the camera torch.  If a real front/RGB class appears on a
future kernel it drives the requested colour channels; otherwise it publishes a
bounded, clearly-labelled display-edge-lighting request for nuxel-wl-fb (the
single framebuffer owner).

Per-channel mapping is taken from configs/nuxel/leds/leds.json.  All channels
are explicitly zeroed on clear, timeout, service start and exit.
"""
from __future__ import annotations

import atexit
import glob
import json
import os
import threading
import time
from typing import Any, Dict, Optional, Tuple

DEFAULT_POLICY = "/etc/nuxel/leds/leds.json"
DEFAULT_LEDS_ROOT = "/sys/class/leds"
DEFAULT_STATE = "/var/lib/nuxel/leds/notification-state.json"
DEFAULT_EDGE_CMD = "/run/nuxel-wl-fb.cmd"

COLORS: Dict[str, Tuple[int, int, int]] = {
    "red": (255, 0, 0),
    "green": (0, 255, 0),
    "blue": (0, 0, 255),
    "yellow": (255, 180, 0),
    "amber": (255, 140, 0),
    "cyan": (0, 255, 255),
    "magenta": (255, 0, 255),
    "white": (255, 255, 255),
}
MAX_MS = 60000


def _read_int(path: str) -> Optional[int]:
    try:
        with open(path) as fh:
            return int(fh.read().strip())
    except (OSError, ValueError):
        return None


def _atomic_json(path: str, doc: Dict[str, Any]) -> None:
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        tmp = path + ".tmp.%d" % os.getpid()
        with open(tmp, "w") as fh:
            json.dump(doc, fh, sort_keys=True, indent=2)
            fh.write("\n")
        os.replace(tmp, path)
    except OSError:
        pass


class LedNotificationProvider:
    def __init__(self) -> None:
        self.policy_path = os.environ.get("NUXEL_LED_POLICY", DEFAULT_POLICY)
        self.leds_root = os.environ.get("NUXEL_LEDS_ROOT", DEFAULT_LEDS_ROOT)
        self.state_path = os.environ.get("NUXEL_LED_NOTIFY_STATE", DEFAULT_STATE)
        self.edge_cmd = os.environ.get("NUXEL_EDGE_LIGHT_CMD", DEFAULT_EDGE_CMD)
        self._lock = threading.RLock()
        self._timer: Optional[threading.Timer] = None
        self._color = "off"
        self._state = "OFF"
        self._reason = "not requested"
        self._channels: Dict[str, str] = {}
        self._display_overlay = False
        self._load_policy()
        self.clear("service-start")
        atexit.register(lambda: self.clear("service-exit"))

    def _load_policy(self) -> None:
        doc: Dict[str, Any] = {}
        try:
            with open(self.policy_path) as fh:
                doc = json.load(fh)
        except (OSError, ValueError):
            pass
        classes = (doc.get("classes") or {})
        notif = classes.get("notification") or {}
        colors = notif.get("colors") or {"red": "led:red", "green": "led:green", "blue": "led:blue"}
        for name in ("red", "green", "blue"):
            node = str(colors.get(name, "led:" + name))
            if node.startswith("/"):
                path = node
            else:
                path = os.path.join(self.leds_root, node)
            if not os.path.isdir(path):
                path = os.path.join(self.leds_root, node.replace("led:", ""))
            if os.path.isdir(path) and os.path.exists(os.path.join(path, "brightness")):
                self._channels[name] = path
        # A single-colour/notification class can only render its own colour.
        if not self._channels:
            for cand in notif.get("candidates") or []:
                p = str(cand)
                if p.startswith("/sys/class/leds/"):
                    p = os.path.join(self.leds_root, p[len("/sys/class/leds/"):])
                if os.path.isdir(p) and os.path.exists(os.path.join(p, "brightness")):
                    self._channels["white"] = p
                    break

    def _write_channel(self, name: str, value: int) -> bool:
        path = self._channels.get(name)
        if not path:
            return False
        mx = _read_int(os.path.join(path, "max_brightness")) or 255
        try:
            with open(os.path.join(path, "brightness"), "w") as fh:
                fh.write(str(max(0, min(mx, int(value)))))
            return True
        except OSError:
            return False

    def _all_off(self) -> None:
        for name in list(self._channels):
            self._write_channel(name, 0)

    def _send_edge(self, line: str) -> bool:
        # The display bridge owns /dev/fb0; this provider writes only its
        # narrow control FIFO and only when that owner is actually present.
        if not os.path.exists(self.edge_cmd):
            return False
        try:
            with open(self.edge_cmd, "w") as fh:
                fh.write(line + "\n")
            return True
        except OSError:
            return False

    def status(self) -> Dict[str, Any]:
        with self._lock:
            hardware = bool(self._channels)
            colors = sorted(set(COLORS) & set(self._channels.keys())) if hardware else []
            if hardware and set(self._channels) >= {"red", "green", "blue"}:
                colors = ["red", "green", "blue", "yellow", "amber", "cyan", "magenta", "white"]
            return {
                "success": True,
                "state": self._state,
                "color": self._color,
                "supported": hardware,
                "hardware_led": hardware,
                "kind": "hardware_led" if hardware else "none",
                "channels": sorted(self._channels),
                "supported_colors": colors,
                "display_fallback": {
                    "available": os.path.exists(self.edge_cmd),
                    "kind": "display_edge_lighting",
                    "hardware_led": False,
                    "label": "software edge-lighting (display effect)",
                    "owner": "nuxel-wl-fb",
                },
                "max_on_ms": MAX_MS,
                "reason": self._reason,
                "source": "led_notification_provider",
            }

    def _apply(self, color: str) -> bool:
        rgb = COLORS.get(color)
        if not rgb:
            return False
        if not self._channels:
            return False
        if not self._all_off():
            return False
        ok = True
        if set(self._channels) >= {"red", "green", "blue"}:
            for name, value in zip(("red", "green", "blue"), rgb):
                ok = self._write_channel(name, (value * 255 + 127) // 255) and ok
        elif "white" in self._channels:
            # A single notification LED has no colour channel; only white is
            # physically provable.  Requested colour is reported as such.
            ok = self._write_channel("white", 255) and ok
        return ok

    def _remember(self) -> None:
        _atomic_json(self.state_path, {
            "schema_version": 1,
            "state": self._state,
            "color": self._color,
            "hardware_led": bool(self._channels),
            "channels": sorted(self._channels),
            "reason": self._reason,
            "updated_at": int(time.time()),
            "owner": "led_notification_provider",
        })

    def clear(self, reason: str = "explicit-off") -> Dict[str, Any]:
        with self._lock:
            if self._timer is not None:
                try:
                    self._timer.cancel()
                except Exception:
                    pass
                self._timer = None
            self._all_off()
            self._display_overlay = False
            self._send_edge("edge-light-off")
            self._state = "OFF"
            self._color = "off"
            self._reason = reason
            self._remember()
            return self.status()

    def set_color(self, color: str, duration_ms: int = 2500,
                  priority: str = "normal") -> Dict[str, Any]:
        duration_ms = max(100, min(MAX_MS, int(duration_ms or 2500)))
        color = (color or "red").lower()
        # DND is checked by the caller (notification daemon / bridge), but a
        # direct test request is explicitly allowed to exercise the channel.
        with self._lock:
            self._color = color
            if self._channels:
                if not self._apply(color):
                    self._state = "ERROR"
                    self._reason = "channel write failed; all channels forced off"
                    self._all_off()
                    self._remember()
                    return self.status()
                self._state = "ON"
                self._reason = "hardware notification LED channels active"
            else:
                rgb = COLORS.get(color, (255, 255, 255))
                # Truthful fallback: the display bridge paints a bounded edge
                # glow.  This is NOT reported as a hardware LED.
                if self._send_edge("edge-light %02x %02x %02x %d" % (rgb + (duration_ms,))):
                    self._display_overlay = True
                    self._state = "DISPLAY_FALLBACK"
                    self._reason = "no notification LED class; bounded display edge-lighting fallback"
                else:
                    self._display_overlay = False
                    self._state = "NOT_SUPPORTED_ON_DEVICE"
                    self._reason = "no notification LED class and display bridge unavailable"
            if self._timer is not None:
                try:
                    self._timer.cancel()
                except Exception:
                    pass
            self._timer = threading.Timer(duration_ms / 1000.0, self.clear, kwargs={"reason": "timeout"})
            self._timer.daemon = True
            self._timer.start()
            self._remember()
            return self.status()


_PROVIDER: Optional[LedNotificationProvider] = None


def get_provider() -> LedNotificationProvider:
    global _PROVIDER
    if _PROVIDER is None:
        _PROVIDER = LedNotificationProvider()
    return _PROVIDER


def handle(verb: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    params = params or {}
    p = get_provider()
    if verb in ("status", "get"):
        return p.status()
    if verb in ("off", "clear"):
        return p.clear("explicit-off")
    if verb in ("test", "set-color", "notify"):
        return p.set_color(str(params.get("color", "red")),
                           int(params.get("duration_ms", 2500)),
                           str(params.get("priority", "normal")))
    return {"success": False, "error": "unknown led-notification verb", "verb": verb}
