#!/usr/bin/env python3
"""Single safe owner for the S10+ torch/flashlight.

Only this module writes an LED brightness node.  Neither JavaScript nor the
button manager touches /sys/class/leds directly.  The state machine enforces:

  * the LED class must really exist and be writable -> otherwise
    NOT_SUPPORTED_ON_DEVICE; no fake ON state;
  * camera arbitration (a camera-active marker blocks the shared flash LED);
  * a thermal guard read from the kernel thermal zones;
  * the policy's bounded max_on_ms and an unconditional explicit OFF on timeout,
    process exit, or an explicit off call;
  * no auto-on at boot.

Every path is overridable for offline tests:

  NUXEL_LED_POLICY       policy JSON (default /etc/nuxel/leds/leds.json)
  NUXEL_LEDS_ROOT        /sys/class/leds
  NUXEL_FLASHLIGHT_STATE state JSON (default /var/lib/nuxel/leds/state.json)
  NUXEL_CAMERA_ACTIVE    marker path(s), colon separated (default /run/nuxel/camera-active)
  NUXEL_THERMAL_ROOT     /sys/class/thermal
"""
from __future__ import annotations

import atexit
import glob
import json
import os
import re
import threading
import time
from typing import Any, Dict, Optional

DEFAULT_POLICY = "/etc/nuxel/leds/leds.json"
DEFAULT_LEDS_ROOT = "/sys/class/leds"
DEFAULT_STATE = "/var/lib/nuxel/leds/state.json"
DEFAULT_CAMERA_ACTIVE = "/run/nuxel/camera-active"
DEFAULT_THERMAL_ROOT = "/sys/class/thermal"
THERMAL_BLOCK_C = 70.0


def _read_int(path: str) -> Optional[int]:
    try:
        with open(path, "r") as fh:
            return int(fh.read().strip())
    except (OSError, ValueError):
        return None


def _read_text(path: str) -> Optional[str]:
    try:
        with open(path, "r") as fh:
            return fh.read().strip()
    except OSError:
        return None


def _atomic_json(path: str, doc: Dict[str, Any]) -> None:
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        tmp = path + ".tmp.%d" % os.getpid()
        with open(tmp, "w") as fh:
            json.dump(doc, fh, sort_keys=True)
        os.replace(tmp, path)
    except OSError:
        pass


class FlashlightProvider:
    def __init__(self) -> None:
        self.policy_path = os.environ.get("NUXEL_LED_POLICY", DEFAULT_POLICY)
        self.leds_root = os.environ.get("NUXEL_LEDS_ROOT", DEFAULT_LEDS_ROOT)
        self.state_path = os.environ.get("NUXEL_FLASHLIGHT_STATE", DEFAULT_STATE)
        self.camera_markers = [p for p in os.environ.get(
            "NUXEL_CAMERA_ACTIVE", DEFAULT_CAMERA_ACTIVE).split(":") if p]
        self.thermal_root = os.environ.get("NUXEL_THERMAL_ROOT", DEFAULT_THERMAL_ROOT)
        self._lock = threading.RLock()
        self._timer: Optional[threading.Timer] = None
        self._state = "OFF"
        self._reason = "not requested"
        self._brightness_path: Optional[str] = None
        self._max_brightness = 255
        self._policy = self._load_policy()
        atexit.register(self.force_off)
        self._refresh_path()

    # ---- policy / discovery ------------------------------------------------
    def _load_policy(self) -> Dict[str, Any]:
        try:
            with open(self.policy_path, "r") as fh:
                doc = json.load(fh)
            return doc if isinstance(doc, dict) else {}
        except (OSError, ValueError):
            return {}

    def _policy_torch(self) -> Dict[str, Any]:
        classes = self._policy.get("classes") or {}
        torch = classes.get("flashlight") or {}
        return torch if isinstance(torch, dict) else {}

    def _candidates(self):
        torch = self._policy_torch()
        for p in torch.get("candidates") or []:
            yield str(p)
        for pattern in torch.get("globs") or []:
            # Restrict glob expansion to the configured LED root.  A policy may
            # use absolute /sys paths; map them onto the testable root.
            pat = str(pattern)
            if pat.startswith("/sys/class/leds/"):
                pat = os.path.join(self.leds_root, pat[len("/sys/class/leds/"):])
            for hit in sorted(glob.glob(pat)):
                yield hit

    def _refresh_path(self) -> Optional[str]:
        """Pick the first usable torch class.  Never invent a path."""
        with self._lock:
            for cand in self._candidates():
                # Map policy absolute paths onto the actual (possibly test) root.
                if cand.startswith("/sys/class/leds/"):
                    cand = os.path.join(self.leds_root, cand[len("/sys/class/leds/"):])
                if not os.path.isdir(cand):
                    continue
                brightness = os.path.join(cand, "brightness")
                if not os.path.exists(brightness):
                    continue
                if not os.access(brightness, os.W_OK):
                    continue
                self._brightness_path = brightness
                self._max_brightness = _read_int(os.path.join(cand, "max_brightness")) or 255
                return brightness
            self._brightness_path = None
            return None

    def _camera_active(self) -> bool:
        for marker in self.camera_markers:
            if os.path.exists(marker):
                return True
        return False

    def _thermal_blocked(self) -> bool:
        policy = self._policy.get("safety") or {}
        limit = float(policy.get("thermal_block_c", THERMAL_BLOCK_C))
        hottest = None
        try:
            zones = sorted(os.listdir(self.thermal_root))
        except OSError:
            return False
        for zone in zones:
            t = _read_int(os.path.join(self.thermal_root, zone, "temp"))
            if t is None:
                continue
            c = t / 1000.0 if t > 1000 else float(t)
            if hottest is None or c > hottest:
                hottest = c
        return hottest is not None and hottest >= limit

    def _max_on_seconds(self) -> float:
        safety = self._policy.get("safety") or {}
        try:
            ms = int(safety.get("max_on_ms", 60000))
        except (TypeError, ValueError):
            ms = 60000
        return max(1.0, min(300.0, ms / 1000.0))

    # ---- state / control ---------------------------------------------------
    def status(self) -> Dict[str, Any]:
        with self._lock:
            self._refresh_path()
            supported = self._brightness_path is not None
            state = self._state if supported else "NOT_SUPPORTED_ON_DEVICE"
            if not supported:
                reason = "no writable torch LED class under %s" % self.leds_root
            else:
                reason = self._reason
            return {
                "success": True,
                "supported": supported,
                "state": state,
                "on": state == "ON",
                "led_path": self._brightness_path,
                "led_name": os.path.basename(os.path.dirname(self._brightness_path)) if self._brightness_path else None,
                "max_on_seconds": self._max_on_seconds(),
                "camera_active": self._camera_active(),
                "thermal_blocked": self._thermal_blocked(),
                "reason": reason,
                "source": "flashlight_provider",
            }

    def _write_brightness(self, value: int) -> bool:
        if not self._brightness_path:
            return False
        try:
            with open(self._brightness_path, "w") as fh:
                fh.write(str(max(0, min(self._max_brightness, int(value)))))
            return True
        except OSError:
            return False

    def _cancel_timer(self) -> None:
        if self._timer is not None:
            try:
                self._timer.cancel()
            except Exception:
                pass
            self._timer = None

    def _remember(self) -> None:
        _atomic_json(self.state_path, {
            "schema_version": 1,
            "state": self._state,
            "on": self._state == "ON",
            "reason": self._reason,
            "led_path": self._brightness_path,
            "updated_at": int(time.time()),
            "owner": "flashlight_provider",
        })

    def force_off(self, reason: str = "explicit-off") -> Dict[str, Any]:
        with self._lock:
            self._cancel_timer()
            if self._brightness_path:
                self._write_brightness(0)
                self._state = "OFF"
                self._reason = reason
                self._remember()
            else:
                self._state = "NOT_SUPPORTED_ON_DEVICE"
                self._reason = "no writable torch LED class"
            return self.status()

    def set_enabled(self, enabled: bool, requested_by: str = "pwa") -> Dict[str, Any]:
        with self._lock:
            self._refresh_path()
            if not self._brightness_path:
                self._state = "NOT_SUPPORTED_ON_DEVICE"
                self._reason = "no writable torch LED class under %s" % self.leds_root
                self._remember()
                return self.status()
            if not enabled:
                return self.force_off("explicit-off")
            # Re-check every activation, not just at service start.
            if self._camera_active():
                self._state = "BLOCKED_CAMERA"
                self._reason = "camera owns the shared flash LED"
                self._remember()
                return self.status()
            if self._thermal_blocked():
                self._state = "THERMAL_LIMIT"
                self._reason = "thermal guard blocks the torch"
                self._remember()
                return self.status()
            if not self._write_brightness(self._max_brightness):
                self._state = "ERROR"
                self._reason = "brightness write failed"
                self._remember()
                # A failed write must not leave the LED in an unknown state.
                self._write_brightness(0)
                return self.status()
            self._state = "ON"
            self._reason = "torch on via privileged owner; request=%s" % requested_by
            self._remember()
            self._cancel_timer()
            self._timer = threading.Timer(self._max_on_seconds(), self._timeout_off)
            self._timer.daemon = True
            self._timer.start()
            return self.status()

    def _timeout_off(self) -> None:
        with self._lock:
            self._timer = None
            if self._brightness_path:
                self._write_brightness(0)
            self._state = "OFF"
            self._reason = "policy max_on_seconds elapsed; forced off"
            self._remember()

    def toggle(self, requested_by: str = "pwa") -> Dict[str, Any]:
        with self._lock:
            current = self.status()
            if current["state"] == "ON":
                return self.force_off("toggle-off")
            return self.set_enabled(True, requested_by)


_PROVIDER: Optional[FlashlightProvider] = None


def get_provider() -> FlashlightProvider:
    global _PROVIDER
    if _PROVIDER is None:
        _PROVIDER = FlashlightProvider()
    return _PROVIDER


def handle(verb: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    params = params or {}
    p = get_provider()
    if verb in ("status", "get", "state"):
        return p.status()
    if verb == "off":
        return p.force_off("explicit-off")
    if verb == "on":
        return p.set_enabled(True, str(params.get("requested_by", "pwa")))
    if verb in ("toggle", "set"):
        if verb == "set":
            return p.set_enabled(bool(params.get("enabled")), str(params.get("requested_by", "pwa")))
        return p.toggle(str(params.get("requested_by", "pwa")))
    return {"success": False, "error": "unknown flashlight verb", "verb": verb}
