#!/usr/bin/env python3
"""Persistent system-wide Do Not Disturb policy for Nuxel.

One owner: this module.  The notification daemon, Quick Settings, Settings and
the notification LED/edge-light provider all read the same state document.  DND
suppresses interruption effects (popup/sound/haptic/LED) but never deletes the
notification record: history is preserved and marked suppressed.

Files (overridable for offline tests):
  NUXEL_DND_CONFIG  /etc/nuxel/notifications/dnd.json       (defaults/policy)
  NUXEL_DND_STATE   /var/lib/nuxel/notifications/dnd.json   (current state)
"""
from __future__ import annotations

import datetime as _dt
import json
import os
import tempfile
import threading
import time
from typing import Any, Dict, Optional

DEFAULT_CONFIG = "/etc/nuxel/notifications/dnd.json"
DEFAULT_STATE = "/var/lib/nuxel/notifications/dnd.json"

DEFAULT_POLICY: Dict[str, Any] = {
    "schema_version": 1,
    "default_enabled": False,
    "suppress": {"popups": True, "sound": True, "haptics": True, "led": True},
    "exceptions": {"critical": True, "alarms": True, "calls": False},
    "schedule": {"enabled": False, "start": "22:00", "end": "07:00", "days": [0, 1, 2, 3, 4, 5, 6]},
}


def _read_json(path: str) -> Dict[str, Any]:
    try:
        with open(path, "r") as fh:
            doc = json.load(fh)
        return doc if isinstance(doc, dict) else {}
    except (OSError, ValueError):
        return {}


def _atomic_json(path: str, doc: Dict[str, Any]) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=".dnd-", dir=os.path.dirname(path))
    try:
        os.fchmod(fd, 0o644)
        with os.fdopen(fd, "w") as fh:
            json.dump(doc, fh, sort_keys=True, indent=2)
            fh.write("\n")
        os.replace(tmp, path)
        try:
            os.chmod(path, 0o644)
        except OSError:
            pass
    finally:
        try:
            os.unlink(tmp)
        except OSError:
            pass


def _minutes(hhmm: str) -> Optional[int]:
    try:
        h, m = str(hhmm).split(":", 1)
        h, m = int(h), int(m)
        if 0 <= h < 24 and 0 <= m < 60:
            return h * 60 + m
    except (TypeError, ValueError):
        pass
    return None


def schedule_active(policy: Dict[str, Any], now: Optional[_dt.datetime] = None) -> bool:
    sched = policy.get("schedule") or {}
    if not sched.get("enabled"):
        return False
    now = now or _dt.datetime.now()
    days = sched.get("days")
    if isinstance(days, list) and days and now.weekday() not in days:
        return False
    start, end = _minutes(sched.get("start", "22:00")), _minutes(sched.get("end", "07:00"))
    if start is None or end is None or start == end:
        return False
    cur = now.hour * 60 + now.minute
    if start < end:
        return start <= cur < end
    return cur >= start or cur < end


class DndProvider:
    def __init__(self) -> None:
        self.config_path = os.environ.get("NUXEL_DND_CONFIG", DEFAULT_CONFIG)
        self.state_path = os.environ.get("NUXEL_DND_STATE", DEFAULT_STATE)
        self._lock = threading.RLock()

    def policy(self) -> Dict[str, Any]:
        doc = dict(DEFAULT_POLICY)
        user = _read_json(self.config_path)
        for key in ("default_enabled", "suppress", "exceptions", "schedule"):
            if key in user:
                if isinstance(doc.get(key), dict) and isinstance(user[key], dict):
                    merged = dict(doc[key])
                    merged.update(user[key])
                    doc[key] = merged
                else:
                    doc[key] = user[key]
        return doc

    def _state(self) -> Dict[str, Any]:
        policy = self.policy()
        state = _read_json(self.state_path)
        enabled = bool(state.get("enabled", policy.get("default_enabled", False)))
        reason = state.get("reason") or ("manual" if enabled else "off")
        scheduled = schedule_active(policy)
        active = enabled or scheduled
        if scheduled and not enabled:
            reason = "schedule"
        elif enabled:
            reason = "manual"
        return {
            "schema_version": 1,
            "enabled": bool(enabled),
            "active": active,
            "reason": reason,
            "scheduled": scheduled,
            "updated_at": state.get("updated_at"),
            "policy": policy,
        }

    def status(self) -> Dict[str, Any]:
        with self._lock:
            doc = self._state()
            doc.update({"success": True, "source": "dnd_provider"})
            return doc

    def set_enabled(self, enabled: bool) -> Dict[str, Any]:
        with self._lock:
            _atomic_json(self.state_path, {
                "schema_version": 1,
                "enabled": bool(enabled),
                "reason": "manual" if enabled else "off",
                "updated_at": time.time(),
                "owner": "dnd_provider",
            })
            return self.status()

    def set_schedule(self, enabled: bool, start: Optional[str] = None,
                     end: Optional[str] = None, days: Optional[list] = None) -> Dict[str, Any]:
        with self._lock:
            policy = self.policy()
            sched = dict(policy.get("schedule") or {})
            sched["enabled"] = bool(enabled)
            if start:
                sched["start"] = start
            if end:
                sched["end"] = end
            if isinstance(days, list):
                sched["days"] = [int(d) for d in days if 0 <= int(d) <= 6]
            _atomic_json(self.config_path, {"schema_version": 1, "schedule": sched,
                                            "suppress": policy.get("suppress"),
                                            "exceptions": policy.get("exceptions")})
            return self.status()

    def suppresses(self, urgency: str = "normal", category: str = "") -> bool:
        status = self.status()
        if not status["active"]:
            return False
        policy = status["policy"]
        exc = policy.get("exceptions") or {}
        urg = (urgency or "normal").lower()
        cat = (category or "").lower()
        if urg == "critical" and exc.get("critical", True):
            return False
        if ("alarm" in cat or "emergency" in cat) and exc.get("alarms", True):
            return False
        if ("call" in cat) and exc.get("calls", False):
            return False
        return True


_PROVIDER: Optional[DndProvider] = None


def get_provider() -> DndProvider:
    global _PROVIDER
    if _PROVIDER is None:
        _PROVIDER = DndProvider()
    return _PROVIDER


def handle(verb: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    params = params or {}
    p = get_provider()
    if verb in ("status", "get", "get-status"):
        return p.status()
    if verb in ("set-enabled", "set", "toggle"):
        if verb == "toggle":
            want = not p.status()["enabled"]
        else:
            want = bool(params.get("enabled"))
        return p.set_enabled(want)
    if verb in ("set-schedule", "schedule"):
        return p.set_schedule(bool(params.get("enabled")),
                              params.get("start"), params.get("end"), params.get("days"))
    if verb == "is-suppressed":
        return {"success": True, "suppressed": p.suppresses(
            str(params.get("urgency", "normal")), str(params.get("category", "")))}
    return {"success": False, "error": "unknown dnd verb", "verb": verb}
