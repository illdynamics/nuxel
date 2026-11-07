#!/usr/bin/env python3
"""Nuxel durable alarm, timer and calendar-reminder scheduler.

The Clock PWA is only a client.  This daemon owns every schedule and
occurrence across Clock closure, WebView reload, service restart and reboot.

State:
  /var/lib/nuxel/clock/state.json   authoritative schedule + occurrence ledger
  /run/nuxel/clockd.sock            private root-only JSON control socket
  /run/nuxel/clockd.state           read-only compatibility/status projection

Design rules:
  * alarm sources and fired occurrences are separate objects;
  * snooze creates a new occurrence and never mutates a recurring alarm;
  * a one-shot alarm is disabled only after its occurrence was durably fired;
  * timers use an absolute wall deadline plus a unique run id;
  * sound is delegated to nuxel-soundd, never opened from this daemon;
  * no RTC write is attempted unless the owner explicitly opts in; capability
    is reported honestly in status.
"""
from __future__ import annotations

import json
import logging
import os
import signal
import socket
import subprocess
import sys
import threading
import time
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

STATE_FILE = Path(os.environ.get("NUXEL_CLOCK_STATE_FILE", "/var/lib/nuxel/clock/state.json"))
RUNTIME_STATE = Path(os.environ.get("NUXEL_CLOCK_STATE", "/run/nuxel/clockd.state"))
SOCKET = Path(os.environ.get("NUXEL_CLOCK_SOCKET", "/run/nuxel/clockd.sock"))
SOUNDD_SOCKET = Path(os.environ.get("NUXEL_SOUNDD_SOCKET", "/run/nuxel/soundd.sock"))
LEGACY_SCHEDULE = Path(os.environ.get("NUXEL_CLOCK_SCHEDULE", "/var/lib/nuxel/clock/schedule.json"))
RTC_WAKEALARM = Path(os.environ.get("NUXEL_CLOCK_WAKEALARM", "/sys/class/rtc/rtc0/wakealarm"))
SOUNDCTL = os.environ.get("NUXEL_SOUNDCTL", "/usr/libexec/nuxel/nuxel-soundctl")
HAPTICS = os.environ.get("NUXEL_HAPTICS_FIFO", "/run/nuxel-haptics/haptics.cmd")
SESSION_RUNTIME = os.environ.get("NUXEL_SESSION_RUNTIME", "/run/nuxel-wayland")
NOTIFY = os.environ.get("NUXEL_NOTIFY", "/usr/bin/notify-send")
SCHEMA = 2
MAX_OCCURRENCES = 256
# Durable cue delivery is retried with bounded backoff while the occurrence is
# ringing.  Waiting is event-driven (soundd socket/health), never an alarm sleep.
CUE_BACKOFF_MS = (250, 500, 1000, 2000, 5000, 10000)
CUE_RECONCILE_MS = 5000

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("nuxel-clockd")


class ClockError(Exception):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


def _now_ms() -> int:
    return int(time.time() * 1000)


def _iso(ts: float | None = None) -> str:
    return datetime.fromtimestamp(ts if ts is not None else time.time(),
                                  timezone.utc).isoformat(timespec="seconds")


def _atomic_json(path: Path, doc: dict, mode: int = 0o600) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp.%d" % os.getpid())
    try:
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(doc, fh, indent=2, sort_keys=True)
            fh.write("\n")
            fh.flush()
            os.fsync(fh.fileno())
        os.chmod(tmp, mode)
        os.replace(tmp, path)
        try:
            dfd = os.open(str(path.parent), os.O_DIRECTORY)
            try:
                os.fsync(dfd)
            finally:
                os.close(dfd)
        except OSError:
            pass
    finally:
        try:
            if tmp.exists():
                tmp.unlink()
        except OSError:
            pass


def _valid_time(value) -> str:
    raw = str(value or "").strip()
    digits = "".join(ch for ch in raw if ch.isdigit())
    if len(digits) == 3:
        digits = "0" + digits
    if len(digits) != 4:
        raise ClockError("INVALID_TIME", "time must be HH:MM (24-hour)")
    hh, mm = int(digits[:2]), int(digits[2:])
    if hh > 23 or mm > 59:
        raise ClockError("INVALID_TIME", "time must be a real 24-hour clock value")
    return "%02d:%02d" % (hh, mm)


def _valid_id(value, prefix: str) -> str:
    raw = str(value or "").strip()
    if not raw:
        return "%s-%s" % (prefix, uuid.uuid4().hex[:12])
    if len(raw) > 100 or any(ch not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789._:-" for ch in raw):
        raise ClockError("INVALID_ID", "invalid object id")
    return raw


def default_state() -> dict:
    now = _iso()
    return {
        "schema_version": SCHEMA,
        "revision": 1,
        "created_at": now,
        "updated_at": now,
        "settings": {
            "snooze_minutes": 9,
            "snooze_enabled": True,
            "vibrate": True,
            "alarm_sound": None,
            "timer_sound": None,
        },
        "alarms": [],
        "timer": {
            "run_id": None, "label": "Timer", "duration_ms": 300000,
            "remaining_ms": 300000, "deadline_ms": None,
            "state": "idle", "started_at": None, "updated_at": now,
        },
        "occurrences": [],
        "calendar_reminders": [],
        "migration": {},
    }


class ClockDaemon:
    def __init__(self) -> None:
        self._lock = threading.RLock()
        self.stop_requested = False
        self._cue_wake = threading.Event()
        self._last_health_check = 0
        self.state = self._load_state()
        self._migrate_legacy()
        self._normalise()
        self._rearm_ringing_cues()
        self._save()

    # ---- persistence ----------------------------------------------------
    def _load_state(self) -> dict:
        try:
            doc = json.loads(STATE_FILE.read_text(encoding="utf-8"))
            if not isinstance(doc, dict):
                raise ValueError("state is not an object")
            base = default_state()
            base.update(doc)
            return base
        except FileNotFoundError:
            return default_state()
        except (OSError, ValueError) as exc:
            log.error("state unreadable, preserving it and starting a fresh in-memory state: %s", exc)
            try:
                if STATE_FILE.exists():
                    os.replace(STATE_FILE, STATE_FILE.with_suffix(".corrupt-%d.json" % int(time.time())))
            except OSError:
                pass
            return default_state()

    def _normalise(self) -> None:
        with self._lock:
            st = self.state
            st["schema_version"] = SCHEMA
            settings = st.setdefault("settings", {})
            try:
                snooze = int(settings.get("snooze_minutes", 9))
            except (TypeError, ValueError):
                snooze = 9
            settings["snooze_minutes"] = max(1, min(60, snooze))
            settings["snooze_enabled"] = bool(settings.get("snooze_enabled", True))
            settings["vibrate"] = bool(settings.get("vibrate", True))
            for key in ("alarm_sound", "timer_sound"):
                value = settings.get(key)
                settings[key] = str(value) if value else None
            seen = set()
            alarms = []
            for alarm in st.get("alarms") or []:
                if not isinstance(alarm, dict):
                    continue
                try:
                    at = _valid_time(alarm.get("time"))
                except ClockError:
                    continue
                aid = _valid_id(alarm.get("id"), "alarm")
                if aid in seen:
                    continue
                seen.add(aid)
                alarms.append({
                    "id": aid,
                    "time": at,
                    "label": str(alarm.get("label") or "Alarm")[:160],
                    "repeat": bool(alarm.get("repeat", False)),
                    "enabled": bool(alarm.get("enabled", True)),
                    "vibrate": bool(alarm.get("vibrate", settings["vibrate"])),
                    "snooze_minutes": max(1, min(60, int(alarm.get("snooze_minutes") or settings["snooze_minutes"]))),
                    "timezone": str(alarm.get("timezone") or (datetime.now().astimezone().tzinfo or timezone.utc)),
                    "created_at": alarm.get("created_at") or _iso(),
                    "updated_at": alarm.get("updated_at") or _iso(),
                    "source_note_id": alarm.get("sourceNoteId") or alarm.get("source_note_id"),
                })
            st["alarms"] = sorted(alarms, key=lambda a: (a["time"], a["label"].lower()))
            timer = st.get("timer") if isinstance(st.get("timer"), dict) else {}
            st["timer"] = self._normalise_timer(timer)
            occurrences = []
            for occ in st.get("occurrences") or []:
                if not isinstance(occ, dict):
                    continue
                if occ.get("state") not in ("snoozed", "ringing", "dismissed"):
                    continue
                occurrences.append(occ)
            occurrences.sort(key=lambda o: float(o.get("due_ms") or 0))
            st["occurrences"] = occurrences[-MAX_OCCURRENCES:]
            reminders = st.get("calendar_reminders")
            st["calendar_reminders"] = reminders if isinstance(reminders, list) else []
            st["revision"] = int(st.get("revision") or 1)

    def _normalise_timer(self, timer: dict) -> dict:
        def _int_or(value, default):
            if value is None:
                return default
            try:
                return max(0, int(value))
            except (TypeError, ValueError):
                return default
        # Zero is a legitimate timer value (expired/acknowledged).  Using
        # `or 300000` here was the source of the "set 0:30 but the daemon shows
        # 5:00" bug: a completed timer's remaining_ms=0 was coerced back to the
        # five-minute default on every reload.
        duration = _int_or(timer.get("duration_ms"), 300000)
        remaining_raw = timer.get("remaining_ms")
        if remaining_raw is None:
            remaining_raw = timer.get("remaining")
        out = {
            "run_id": timer.get("run_id"),
            "label": str(timer.get("label") or "Timer")[:160],
            "duration_ms": duration,
            "remaining_ms": _int_or(remaining_raw, duration),
            "deadline_ms": int(timer["deadline_ms"]) if timer.get("deadline_ms") else None,
            "state": str(timer.get("state") or ("running" if timer.get("running") else "idle")),
            "started_at": timer.get("started_at"),
            "updated_at": timer.get("updated_at") or _iso(),
        }
        if out["state"] not in ("idle", "running", "paused", "completed", "acknowledged"):
            out["state"] = "idle"
        return out

    def _migrate_legacy(self) -> None:
        """Import the old bridge schedule exactly once, without deleting it."""
        with self._lock:
            if self.state.get("migration", {}).get("legacy_schedule_imported"):
                return
            imported = False
            try:
                doc = json.loads(LEGACY_SCHEDULE.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                doc = None
            if isinstance(doc, dict):
                known = {a.get("id") for a in self.state.get("alarms") or []}
                for alarm in doc.get("alarms") or []:
                    if not isinstance(alarm, dict):
                        continue
                    try:
                        at = _valid_time(alarm.get("time"))
                    except ClockError:
                        continue
                    aid = _valid_id(alarm.get("id"), "alarm")
                    if aid in known:
                        continue
                    self.state.setdefault("alarms", []).append({
                        "id": aid, "time": at,
                        "label": str(alarm.get("label") or "Alarm")[:160],
                        "repeat": bool(alarm.get("repeat", False)),
                        "enabled": bool(alarm.get("enabled", True)),
                        "vibrate": bool(alarm.get("vibrate", True)),
                        "snooze_minutes": int(self.state["settings"]["snooze_minutes"]),
                        "timezone": str(datetime.now().astimezone().tzinfo or timezone.utc),
                        "created_at": _iso(), "updated_at": _iso(),
                    })
                    known.add(aid)
                    imported = True
                legacy_timer = doc.get("timer")
                if isinstance(legacy_timer, dict) and legacy_timer.get("endsAt"):
                    try:
                        ends = int(legacy_timer["endsAt"])
                    except (TypeError, ValueError):
                        ends = 0
                    if ends:
                        rem = max(0, ends - _now_ms())
                        self.state["timer"] = {
                            "run_id": "timer-legacy-%d" % ends,
                            "label": "Timer",
                            "duration_ms": max(rem, int(legacy_timer.get("remaining") or rem)),
                            "remaining_ms": rem,
                            "deadline_ms": ends,
                            "state": "running" if legacy_timer.get("running") else "paused",
                            "started_at": _iso(), "updated_at": _iso(),
                        }
                        imported = True
            self.state.setdefault("migration", {})["legacy_schedule_imported"] = True
            if imported:
                self.state["revision"] = int(self.state.get("revision") or 1) + 1
                log.info("migrated legacy clock schedule")

    def _save(self) -> None:
        with self._lock:
            self.state["updated_at"] = _iso()
            _atomic_json(STATE_FILE, self.state)
            self._publish()

    def _rearm_ringing_cues(self) -> None:
        """Resume durable cue delivery after a clockd restart.

        soundd deduplicates by occurrence token, so re-sending an already playing
        alarm is an acknowledgement rather than a second playback.  If soundd
        also restarted, its persisted queue and this re-send restore the cue.
        """
        with self._lock:
            for occ in self.state.get("occurrences") or []:
                if occ.get("state") != "ringing":
                    continue
                occ["cue_state"] = "pending"
                occ["cue_attempts"] = 0
                occ["cue_next_attempt_ms"] = 0
                occ["cue_last_error"] = "daemon restart: re-arming durable cue"
                occ.pop("soundd_instance", None)

    def _publish(self) -> None:
        active = [o for o in self.state.get("occurrences", []) if o.get("state") == "ringing"]
        snoozed = [o for o in self.state.get("occurrences", []) if o.get("state") == "snoozed"]
        timer = self.state.get("timer") or {}
        _atomic_json(RUNTIME_STATE, {
            "schema_version": SCHEMA,
            "revision": self.state.get("revision"),
            "updated": time.time(),
            "updated_iso": _iso(),
            "alarms": list(self.state.get("alarms") or []),
            "timer": timer,
            "active_occurrences": active,
            "snoozed_occurrences": snoozed,
            "next": self._next_pending(),
            "capabilities": self._capabilities(),
        }, mode=0o644)

    # ---- sound / notification ------------------------------------------
    def _soundctl(self, *args: str, timeout: float = 6.0) -> dict:
        try:
            proc = subprocess.run([SOUNDCTL, "--json", *args], capture_output=True,
                                  text=True, timeout=timeout, stdin=subprocess.DEVNULL,
                                  env=dict(os.environ, XDG_RUNTIME_DIR=SESSION_RUNTIME))
            return json.loads(proc.stdout or "{}")
        except (OSError, ValueError, subprocess.SubprocessError) as exc:
            return {"success": False, "error": str(exc)}

    def _soundd_health(self, timeout: float = 2.0) -> dict:
        """Read soundd's control/backend state without starting any player."""
        try:
            sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            sock.connect(str(SOUNDD_SOCKET))
            sock.sendall(b'{"cmd":"health"}\n')
            buf = b""
            while b"\n" not in buf:
                chunk = sock.recv(65536)
                if not chunk:
                    break
                buf += chunk
            sock.close()
            doc = json.loads(buf.split(b"\n", 1)[0].decode("utf-8") or "{}")
            return doc if isinstance(doc, dict) else {"success": False}
        except (OSError, ValueError) as exc:
            return {"success": False, "error": str(exc)}

    def _cue_backoff_ms(self, attempts: int) -> int:
        return CUE_BACKOFF_MS[min(max(attempts - 1, 0), len(CUE_BACKOFF_MS) - 1)]

    def _cue_send(self, ident: str) -> None:
        with self._lock:
            occ = next((o for o in self.state.get("occurrences", [])
                        if o.get("id") == ident), None)
            if occ is None or occ.get("state") != "ringing" or occ.get("cue_state") == "accepted":
                return
            token = str(occ.get("token") or occ.get("id"))
            kind = "timer" if occ.get("kind") == "timer" else "alarm"
            setting_key = "timer_sound" if kind == "timer" else "alarm_sound"
            sound = self.state["settings"].get(setting_key)
            args = ["play", kind, "--loop", "--token", token]
            if sound:
                args += ["--path", sound]
            occ["cue_state"] = "sending"
            occ["cue_attempts"] = int(occ.get("cue_attempts") or 0) + 1
            occ["cue_last_attempt_ms"] = _now_ms()
            attempt = occ["cue_attempts"]
        result = self._soundctl(*args)
        now = _now_ms()
        with self._lock:
            occ = next((o for o in self.state.get("occurrences", [])
                        if o.get("id") == ident), None)
            if occ is None or occ.get("state") != "ringing":
                return
            if result.get("success"):
                player = result.get("player") if isinstance(result.get("player"), dict) else {}
                occ["cue_state"] = "accepted"
                occ["cue_ack_ms"] = now
                occ["cue_last_error"] = None
                occ["soundd_instance"] = player.get("instance_id") or result.get("instance_id")
                log.info("cue accepted token=%s attempt=%d duplicate=%s",
                         token, attempt, bool(result.get("duplicate")))
            else:
                occ["cue_state"] = "pending"
                occ["cue_last_error"] = str(result.get("error") or result)[:240]
                occ["cue_next_attempt_ms"] = now + self._cue_backoff_ms(attempt)
                log.warning("cue deferred token=%s attempt=%d retry_in=%dms: %s",
                            token, attempt, self._cue_backoff_ms(attempt),
                            occ["cue_last_error"])
            self._save()

    def _cue_loop(self) -> None:
        while not self.stop_requested:
            now = _now_ms()
            due: list[str] = []
            accepted: list[dict] = []
            with self._lock:
                for occ in self.state.get("occurrences") or []:
                    if occ.get("state") != "ringing":
                        continue
                    if occ.get("cue_state") == "accepted":
                        accepted.append(dict(occ))
                    elif occ.get("cue_state") != "sending" and \
                            int(occ.get("cue_next_attempt_ms") or 0) <= now:
                        due.append(str(occ.get("id")))
            for ident in due:
                self._cue_send(ident)

            # Reconcile accepted cues if soundd restarted or lost the stream.
            # One health request per interval; no library scan and no player.
            if accepted and now - self._last_health_check >= CUE_RECONCILE_MS:
                self._last_health_check = now
                health = self._soundd_health()
                with self._lock:
                    player = health.get("player") if isinstance(health.get("player"), dict) else {}
                    active_token = player.get("active_token")
                    pending_token = player.get("pending_token")
                    instance = health.get("instance_id") or player.get("instance_id")
                    for snapshot in accepted:
                        occ = next((o for o in self.state.get("occurrences", [])
                                    if o.get("id") == snapshot.get("id")), None)
                        if occ is None or occ.get("state") != "ringing" or occ.get("cue_state") != "accepted":
                            continue
                        token = str(occ.get("token") or occ.get("id"))
                        changed_instance = bool(instance and occ.get("soundd_instance") and
                                                instance != occ.get("soundd_instance"))
                        missing = health.get("success") and token not in (active_token, pending_token)
                        unavailable = not health.get("success")
                        if changed_instance or missing or unavailable:
                            occ["cue_state"] = "pending"
                            occ["cue_next_attempt_ms"] = now + 250
                            occ["cue_last_error"] = ("soundd restarted" if changed_instance else
                                                     "soundd unavailable" if unavailable else
                                                     "cue is no longer active")
                            if instance:
                                occ["soundd_instance"] = instance
                            log.warning("cue re-armed token=%s reason=%s", token, occ["cue_last_error"])
                            self._save()
                            self._cue_wake.set()
            self._cue_wake.wait(0.5)
            self._cue_wake.clear()

    def _ring(self, occ: dict) -> None:
        # Audio is delivered by the durable cue worker.  Keep vibration and the
        # critical notification immediate; neither blocks scheduler readiness.
        if self.state["settings"].get("vibrate", True) and occ.get("vibrate", True):
            try:
                fd = os.open(str(HAPTICS), os.O_WRONLY | os.O_NONBLOCK)
                try:
                    os.write(fd, b"alarm\n")
                finally:
                    os.close(fd)
            except OSError:
                pass
        self._notify(occ)
        self._cue_wake.set()

    def _stop_sound(self, occ: dict) -> None:
        token = str(occ.get("token") or occ.get("id"))
        self._soundctl("stop", "--token", token)

    def _notify(self, occ: dict) -> None:
        if not os.path.exists(NOTIFY):
            return
        title = "Timer finished" if occ.get("kind") == "timer" else "Alarm"
        body = str(occ.get("label") or title)
        try:
            subprocess.Popen([
                "/usr/sbin/runuser", "-u", "nuxel", "--", "env",
                "HOME=/home/nuxel", "XDG_RUNTIME_DIR=/run/user/1000",
                "DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/1000/bus",
                NOTIFY, "-a", "Nuxel Clock", "-u", "critical",
                "-h", "string:x-canonical-private-synchronous:nuxel-clock-%s" % occ.get("id"),
                title, body,
            ], stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
               stderr=subprocess.DEVNULL, start_new_session=True)
        except OSError:
            pass

    # ---- capabilities / schedule ---------------------------------------
    def _capabilities(self) -> dict:
        wake = {"path": str(RTC_WAKEALARM), "present": RTC_WAKEALARM.exists()}
        if RTC_WAKEALARM.exists():
            try:
                wake["value"] = RTC_WAKEALARM.read_text(encoding="utf-8").strip()[:80]
                wake["writable"] = os.access(RTC_WAKEALARM, os.W_OK)
            except OSError as exc:
                wake["read_error"] = str(exc)
        return {
            "screen_off_awake_alarm": True,
            "audio_owner": "nuxel-soundd",
            "rtc_wakealarm": wake,
            "rtc_wake_from_suspend_verified": False,
            "rtc_policy": ("owner-enabled optional programming" if os.environ.get("NUXEL_CLOCK_RTC_WAKE") == "1"
                           else "capability reported; no RTC write performed"),
        }

    def _next_pending(self) -> dict | None:
        candidates = []
        now = time.time()
        dt = datetime.fromtimestamp(now)
        for alarm in self.state.get("alarms") or []:
            if not alarm.get("enabled"):
                continue
            hh, mm = (int(x) for x in alarm["time"].split(":"))
            candidate = dt.replace(hour=hh, minute=mm, second=0, microsecond=0)
            if candidate.timestamp() <= now:
                candidate += timedelta(days=1)
            candidates.append({"kind": "alarm", "id": alarm["id"], "at": int(candidate.timestamp() * 1000),
                               "label": alarm.get("label") or "Alarm"})
        timer = self.state.get("timer") or {}
        if timer.get("state") == "running" and timer.get("deadline_ms"):
            candidates.append({"kind": "timer", "id": timer.get("run_id"),
                               "at": int(timer["deadline_ms"]), "label": timer.get("label") or "Timer"})
        for occ in self.state.get("occurrences") or []:
            if occ.get("state") == "snoozed" and occ.get("due_ms"):
                candidates.append({"kind": occ.get("kind") or "alarm", "id": occ.get("id"),
                                   "at": int(occ["due_ms"]), "label": occ.get("label") or "Alarm",
                                   "snoozed": True})
        return min(candidates, key=lambda c: c["at"]) if candidates else None

    # ---- occurrences ----------------------------------------------------
    def _occurrence(self, **kwargs) -> dict:
        return {
            "id": kwargs.get("id") or ("occ-" + uuid.uuid4().hex[:16]),
            "kind": kwargs.get("kind") or "alarm",
            "alarm_id": kwargs.get("alarm_id"),
            "key": kwargs.get("key"),
            "label": str(kwargs.get("label") or ("Timer" if kwargs.get("kind") == "timer" else "Alarm"))[:160],
            "due_ms": int(kwargs.get("due_ms") or _now_ms()),
            "fired_ms": int(kwargs["fired_ms"]) if kwargs.get("fired_ms") else None,
            "state": kwargs.get("state") or "snoozed",
            "vibrate": bool(kwargs.get("vibrate", True)),
            "token": "clock-%s-%s" % (kwargs.get("kind") or "alarm", uuid.uuid4().hex[:12]),
            "snoozed_from": kwargs.get("snoozed_from"),
            "snooze_audit": kwargs.get("snooze_audit") or [],
            "timezone": str(kwargs.get("timezone") or (datetime.now().astimezone().tzinfo or timezone.utc)),
        }

    def _find_occ(self, ident: str) -> dict:
        for occ in self.state.get("occurrences") or []:
            if occ.get("id") == ident:
                return occ
        raise ClockError("NOT_FOUND", "occurrence not found")

    def _fire(self, occ: dict) -> None:
        if occ.get("state") == "ringing":
            return
        occ["state"] = "ringing"
        occ["fired_ms"] = _now_ms()
        occ["cue_state"] = "pending"
        occ["cue_attempts"] = 0
        occ["cue_next_attempt_ms"] = 0
        occ["cue_last_error"] = None
        occ.pop("soundd_instance", None)
        # Persist the occurrence and its pending cue before audio so a crash
        # cannot duplicate the same occurrence or silently lose the cue.
        self._save()
        self._ring(occ)
        log.info("RING kind=%s id=%s label=%s", occ.get("kind"), occ.get("id"), occ.get("label"))

    def _dismiss(self, ident: str) -> dict:
        occ = self._find_occ(ident)
        self._stop_sound(occ)
        occ["state"] = "dismissed"
        occ["cue_state"] = "dismissed"
        occ["cue_next_attempt_ms"] = None
        occ["dismissed_ms"] = _now_ms()
        self.state["revision"] = int(self.state.get("revision") or 1) + 1
        self._save()
        return occ

    def _snooze(self, ident: str, minutes=None) -> dict:
        settings = self.state["settings"]
        if not settings.get("snooze_enabled", True):
            raise ClockError("SNOOZE_DISABLED", "snooze is disabled in Clock settings")
        occ = self._find_occ(ident)
        if occ.get("state") != "ringing":
            raise ClockError("NOT_RINGING", "only a ringing alarm can be snoozed")
        try:
            mins = int(minutes if minutes is not None else settings.get("snooze_minutes", 9))
        except (TypeError, ValueError):
            mins = 9
        mins = max(1, min(60, mins))
        self._stop_sound(occ)
        occ["state"] = "dismissed"
        occ["cue_state"] = "dismissed"
        occ["cue_next_attempt_ms"] = None
        occ["snoozed_ms"] = _now_ms()
        link = self._occurrence(kind="alarm", alarm_id=occ.get("alarm_id"),
                                key="%s@snooze@%d" % (occ.get("key"), _now_ms()),
                                label=occ.get("label"), due_ms=_now_ms() + mins * 60000,
                                state="snoozed", vibrate=occ.get("vibrate", True),
                                snoozed_from=occ.get("id"),
                                snooze_audit=[{"at": _iso(), "minutes": mins}])
        self.state.setdefault("occurrences", []).append(link)
        self.state["revision"] = int(self.state.get("revision") or 1) + 1
        self._save()
        return link

    def _check(self) -> None:
        with self._lock:
            now_ms = _now_ms()
            changed = False
            # Calendar reminders are ordinary derived occurrences.
            for rem in list(self.state.get("calendar_reminders") or []):
                if not isinstance(rem, dict) or not rem.get("enabled", True):
                    continue
                try:
                    due = int(rem.get("due_ms") or 0)
                except (TypeError, ValueError):
                    continue
                key = "calendar@%s@%s" % (rem.get("id"), rem.get("occurrence_key") or due)
                if due and due <= now_ms and not any(o.get("key") == key for o in self.state.get("occurrences", [])):
                    occ = self._occurrence(kind="alarm", key=key, label=rem.get("title") or "Calendar reminder",
                                           due_ms=due, state="snoozed", vibrate=True)
                    self.state.setdefault("occurrences", []).append(occ)
                    changed = True
            # Promote reached snoozes before checking new wall-clock matches.
            for occ in self.state.get("occurrences", []):
                if occ.get("state") == "snoozed" and int(occ.get("due_ms") or 0) <= now_ms:
                    self._fire(occ)
                    changed = True
            timer = self.state.get("timer") or {}
            if timer.get("state") == "running" and timer.get("deadline_ms") and int(timer["deadline_ms"]) <= now_ms:
                run_id = timer.get("run_id") or "timer"
                key = "timer@%s" % run_id
                if not any(o.get("key") == key for o in self.state.get("occurrences", [])):
                    timer["state"] = "completed"
                    timer["remaining_ms"] = 0
                    timer["updated_at"] = _iso()
                    occ = self._occurrence(kind="timer", key=key, label=timer.get("label") or "Timer",
                                           due_ms=now_ms, state="snoozed", vibrate=True)
                    self.state.setdefault("occurrences", []).append(occ)
                    changed = True
                    self._save()
            # Wall-clock alarms.  The occurrence key uses the local calendar day
            # and offset, so a recurring 07:00 follows DST instead of a frozen UTC.
            dt = datetime.now().astimezone()
            hhmm = dt.strftime("%H:%M")
            day = dt.strftime("%Y-%m-%d %z")
            for alarm in self.state.get("alarms") or []:
                if not alarm.get("enabled") or alarm.get("time") != hhmm:
                    continue
                key = "%s@%s@%s" % (alarm.get("id"), day, hhmm)
                if any(o.get("key") == key for o in self.state.get("occurrences", [])):
                    continue
                occ = self._occurrence(kind="alarm", alarm_id=alarm.get("id"), key=key,
                                       label=alarm.get("label") or "Alarm",
                                       due_ms=now_ms, state="snoozed",
                                       vibrate=alarm.get("vibrate", True))
                self.state.setdefault("occurrences", []).append(occ)
                if not alarm.get("repeat"):
                    alarm["enabled"] = False
                    alarm["completed_at"] = _iso()
                alarm["last_fired_at"] = _iso()
                changed = True
                self._save()
            if changed:
                self.state["revision"] = int(self.state.get("revision") or 1) + 1
                self._normalise()
                self._save()

    # ---- API ------------------------------------------------------------
    def status(self) -> dict:
        timer = self.state.get("timer") or {}
        return {
            "success": True,
            "schema_version": SCHEMA,
            "revision": self.state.get("revision"),
            "ready": True,
            "alarms": self.state.get("alarms") or [],
            "timer": timer,
            "occurrences": self.state.get("occurrences") or [],
            "active_occurrences": [o for o in self.state.get("occurrences", []) if o.get("state") == "ringing"],
            "snoozed_occurrences": [o for o in self.state.get("occurrences", []) if o.get("state") == "snoozed"],
            "next": self._next_pending(),
            "settings": self.state.get("settings") or {},
            "capabilities": self._capabilities(),
        }

    def create_alarm(self, params: dict) -> dict:
        alarm = {
            "id": _valid_id(params.get("id"), "alarm"),
            "time": _valid_time(params.get("time")),
            "label": str(params.get("label") or "Alarm")[:160],
            "repeat": bool(params.get("repeat", False)),
            "enabled": bool(params.get("enabled", True)),
            "vibrate": bool(params.get("vibrate", True)),
            "snooze_minutes": max(1, min(60, int(params.get("snooze_minutes") or self.state["settings"]["snooze_minutes"]))),
            "timezone": str(params.get("timezone") or (datetime.now().astimezone().tzinfo or timezone.utc)),
            "created_at": _iso(), "updated_at": _iso(),
            "source_note_id": params.get("source_note_id"),
        }
        with self._lock:
            self.state.setdefault("alarms", []).append(alarm)
            self._normalise()
            self.state["revision"] = int(self.state.get("revision") or 1) + 1
            self._save()
        return {"success": True, "alarm": alarm, "state": self.status()}

    def update_alarm(self, params: dict) -> dict:
        ident = str(params.get("id") or "")
        with self._lock:
            alarm = next((a for a in self.state.get("alarms", []) if a.get("id") == ident), None)
            if not alarm:
                raise ClockError("NOT_FOUND", "alarm not found")
            if "time" in params:
                alarm["time"] = _valid_time(params.get("time"))
            if "label" in params:
                alarm["label"] = str(params.get("label") or "Alarm")[:160]
            if "repeat" in params:
                alarm["repeat"] = bool(params.get("repeat"))
                if alarm["repeat"]:
                    alarm.pop("completed_at", None)
            if "enabled" in params:
                alarm["enabled"] = bool(params.get("enabled"))
            if "vibrate" in params:
                alarm["vibrate"] = bool(params.get("vibrate"))
            if "snooze_minutes" in params:
                alarm["snooze_minutes"] = max(1, min(60, int(params.get("snooze_minutes") or 9)))
            alarm["updated_at"] = _iso()
            self._normalise()
            self.state["revision"] = int(self.state.get("revision") or 1) + 1
            self._save()
        return {"success": True, "alarm": alarm, "state": self.status()}

    def delete_alarm(self, ident: str) -> dict:
        with self._lock:
            before = len(self.state.get("alarms") or [])
            self.state["alarms"] = [a for a in self.state.get("alarms", []) if a.get("id") != ident]
            if len(self.state["alarms"]) == before:
                raise ClockError("NOT_FOUND", "alarm not found")
            self.state["revision"] = int(self.state.get("revision") or 1) + 1
            self._save()
        return {"success": True, "deleted": ident, "state": self.status()}

    def enable_alarm(self, ident: str, enabled: bool) -> dict:
        return self.update_alarm({"id": ident, "enabled": bool(enabled)})

    def settings_get(self) -> dict:
        return {"success": True, "settings": self.state.get("settings") or {}}

    def settings_set(self, params: dict) -> dict:
        with self._lock:
            settings = self.state.setdefault("settings", {})
            if "snooze_minutes" in params:
                try:
                    settings["snooze_minutes"] = max(1, min(60, int(params.get("snooze_minutes"))))
                except (TypeError, ValueError):
                    raise ClockError("INVALID_SETTING", "snooze_minutes must be 1..60")
            if "snooze_enabled" in params:
                settings["snooze_enabled"] = bool(params.get("snooze_enabled"))
            if "vibrate" in params:
                settings["vibrate"] = bool(params.get("vibrate"))
            for key in ("alarm_sound", "timer_sound"):
                if key in params:
                    value = params.get(key)
                    settings[key] = str(value) if value else None
            self.state["revision"] = int(self.state.get("revision") or 1) + 1
            self._save()
        return {"success": True, "settings": settings, "state": self.status()}

    def timer_cmd(self, verb: str, params: dict) -> dict:
        with self._lock:
            timer = self.state.setdefault("timer", self._normalise_timer({}))
            now = _now_ms()
            if verb == "set":
                duration = max(1000, int(params.get("duration_ms") or 300000))
                timer.update({
                    "run_id": None, "label": str(params.get("label") or "Timer")[:160],
                    "duration_ms": duration, "remaining_ms": duration,
                    "deadline_ms": None, "state": "idle",
                    "started_at": None, "updated_at": _iso(),
                })
            elif verb == "start":
                duration = max(1000, int(params.get("duration_ms") or 300000))
                run_id = "timer-%s" % uuid.uuid4().hex[:12]
                timer.update({
                    "run_id": run_id, "label": str(params.get("label") or "Timer")[:160],
                    "duration_ms": duration, "remaining_ms": duration,
                    "deadline_ms": now + duration, "state": "running",
                    "started_at": _iso(), "updated_at": _iso(),
                })
            elif verb == "pause":
                if timer.get("state") != "running":
                    raise ClockError("NOT_RUNNING", "timer is not running")
                timer["remaining_ms"] = max(0, int(timer.get("deadline_ms") or now) - now)
                timer["deadline_ms"] = None
                timer["state"] = "paused"
                timer["updated_at"] = _iso()
            elif verb == "resume":
                if timer.get("state") != "paused":
                    raise ClockError("NOT_PAUSED", "timer is not paused")
                timer["deadline_ms"] = now + max(0, int(timer.get("remaining_ms") or 0))
                timer["state"] = "running"
                timer["updated_at"] = _iso()
            elif verb == "reset":
                timer.update({"run_id": None, "remaining_ms": timer.get("duration_ms") or 300000,
                              "deadline_ms": None, "state": "idle", "updated_at": _iso()})
            elif verb == "stop":
                for occ in self.state.get("occurrences", []):
                    if occ.get("kind") == "timer" and occ.get("state") == "ringing":
                        self._stop_sound(occ)
                        occ["state"] = "dismissed"
                        occ["cue_state"] = "dismissed"
                        occ["cue_next_attempt_ms"] = None
                        occ["dismissed_ms"] = now
                timer.update({"remaining_ms": 0, "deadline_ms": None,
                              "state": "acknowledged" if timer.get("state") == "completed" else "idle",
                              "updated_at": _iso()})
            else:
                raise ClockError("UNKNOWN_VERB", "unknown timer command")
            self.state["revision"] = int(self.state.get("revision") or 1) + 1
            self._save()
        return {"success": True, "timer": timer, "state": self.status()}

    def sync_legacy(self, params: dict) -> dict:
        """Compatibility sync for existing Clock/Notes callers."""
        alarms = params.get("alarms")
        if isinstance(alarms, list):
            for alarm in alarms:
                if not isinstance(alarm, dict):
                    continue
                try:
                    at = _valid_time(alarm.get("time"))
                except ClockError:
                    continue
                existing = next((a for a in self.state.get("alarms", []) if a.get("id") == alarm.get("id")), None)
                if existing:
                    existing.update({"time": at, "label": alarm.get("label") or "Alarm",
                                     "repeat": bool(alarm.get("repeat")), "enabled": bool(alarm.get("enabled", True)),
                                     "updated_at": _iso()})
                else:
                    self.state.setdefault("alarms", []).append({
                        "id": _valid_id(alarm.get("id"), "alarm"), "time": at,
                        "label": str(alarm.get("label") or "Alarm")[:160],
                        "repeat": bool(alarm.get("repeat")), "enabled": bool(alarm.get("enabled", True)),
                        "vibrate": bool(alarm.get("vibrate", True)),
                        "snooze_minutes": self.state["settings"]["snooze_minutes"],
                        "timezone": str(datetime.now().astimezone().tzinfo or timezone.utc),
                        "created_at": _iso(), "updated_at": _iso(),
                    })
            self._normalise()
            self.state["revision"] = int(self.state.get("revision") or 1) + 1
            self._save()
        timer = params.get("timer")
        if isinstance(timer, dict):
            try:
                ends = int(timer.get("endsAt") or 0)
            except (TypeError, ValueError):
                ends = 0
            if ends:
                self.state["timer"] = {
                    "run_id": "timer-legacy-%d" % ends, "label": str(timer.get("label") or "Timer")[:160],
                    "duration_ms": max(0, int(timer.get("remaining") or 0)),
                    "remaining_ms": max(0, ends - _now_ms()), "deadline_ms": ends,
                    "state": "running" if timer.get("running") else "paused",
                    "started_at": _iso(), "updated_at": _iso(),
                }
                self.state["revision"] = int(self.state.get("revision") or 1) + 1
                self._save()
        return {"success": True, "state": self.status()}

    def _dispatch(self, request: dict) -> dict:
        cmd = str(request.get("cmd") or request.get("verb") or "")
        params = request.get("params") if isinstance(request.get("params"), dict) else request
        if cmd in ("status", "get-state"):
            return self.status()
        if cmd in ("list-alarms",):
            return {"success": True, "alarms": self.state.get("alarms") or [], "state": self.status()}
        if cmd in ("create-alarm", "add-alarm"):
            return self.create_alarm(params)
        if cmd in ("update-alarm",):
            return self.update_alarm(params)
        if cmd in ("delete-alarm", "remove-alarm"):
            return self.delete_alarm(str(params.get("id") or ""))
        if cmd in ("enable-alarm",):
            return self.enable_alarm(str(params.get("id") or ""), bool(params.get("enabled", True)))
        if cmd in ("get-settings",):
            return self.settings_get()
        if cmd in ("set-settings", "set-sound"):
            return self.settings_set(params)
        if cmd in ("start-timer", "pause-timer", "resume-timer", "reset-timer", "stop-timer", "set-timer"):
            return self.timer_cmd(cmd.split("-")[0], params)
        if cmd in ("dismiss-occurrence", "stop-occurrence"):
            occ = self._dismiss(str(params.get("id") or ""))
            return {"success": True, "occurrence": occ, "state": self.status()}
        if cmd == "snooze-occurrence":
            occ = self._snooze(str(params.get("id") or ""), params.get("minutes"))
            return {"success": True, "occurrence": occ, "state": self.status()}
        if cmd in ("sync", "set"):
            return self.sync_legacy(params)
        if cmd == "stop":
            # Legacy global stop remains supported, but dismisses every ringing
            # occurrence explicitly and never deletes schedules.
            for occ in self.state.get("occurrences", []):
                if occ.get("state") == "ringing":
                    self._dismiss(occ["id"])
            return {"success": True, "state": self.status()}
        if cmd in ("preview-sound", "preview"):
            kind = "timer" if params.get("kind") == "timer" else "alarm"
            token = "preview-%s-%s" % (kind, uuid.uuid4().hex[:10])
            args = ["play", kind, "--token", token]
            path = params.get("path") or self.state["settings"].get(kind + "_sound")
            if path:
                args += ["--path", path]
            return {"success": True, "preview_token": token,
                    "result": self._soundctl(*args)}
        if cmd == "stop-preview":
            return {"success": True, "result": self._soundctl(
                "stop", "--token", str(params.get("token") or ""))}
        if cmd == "capabilities":
            return {"success": True, "capabilities": self._capabilities(),
                    "next": self._next_pending()}
        if cmd == "calendar-reminders":
            return {"success": True, "reminders": self.state.get("calendar_reminders") or []}
        if cmd == "set-calendar-reminders":
            reminders = params.get("reminders")
            if not isinstance(reminders, list):
                raise ClockError("INVALID_REMINDERS", "reminders must be a list")
            self.state["calendar_reminders"] = reminders[:512]
            self.state["revision"] = int(self.state.get("revision") or 1) + 1
            self._save()
            return {"success": True, "state": self.status()}
        raise ClockError("UNKNOWN_VERB", "unknown clock command: %s" % cmd)

    def dispatch(self, request: dict) -> dict:
        """Structured API boundary used by both the socket and unit tests."""
        try:
            return self._dispatch(request)
        except ClockError as exc:
            return {"success": False, "error": exc.message, "error_code": exc.code}
        except Exception as exc:  # noqa: BLE001
            log.exception("clock request failed")
            return {"success": False, "error": "internal error: %s" % exc,
                    "error_code": "INTERNAL"}

    # ---- socket loop ----------------------------------------------------
    def _serve_client(self, conn: socket.socket) -> None:
        try:
            conn.settimeout(5)
            data = b""
            while len(data) < 131072:
                chunk = conn.recv(65536)
                if not chunk:
                    break
                data += chunk
                if b"\n" in chunk:
                    break
            req = json.loads(data.decode("utf-8") or "{}")
            if not isinstance(req, dict):
                raise ClockError("INVALID_REQUEST", "request must be an object")
            try:
                result = self.dispatch(req)
                result.setdefault("success", True)
                result.setdefault("state_revision", self.state.get("revision"))
            except ClockError as exc:
                result = {"success": False, "error": exc.message, "error_code": exc.code}
            except Exception as exc:  # noqa: BLE001
                log.exception("clock request failed")
                result = {"success": False, "error": "internal error: %s" % exc, "error_code": "INTERNAL"}
            conn.sendall((json.dumps(result, sort_keys=True) + "\n").encode("utf-8"))
        except (OSError, ValueError, ClockError) as exc:
            try:
                conn.sendall((json.dumps({"success": False, "error": str(exc),
                                          "error_code": "BAD_REQUEST"}) + "\n").encode("utf-8"))
            except OSError:
                pass
        finally:
            try:
                conn.close()
            except OSError:
                pass

    def _socket_loop(self) -> None:
        try:
            SOCKET.unlink()
        except FileNotFoundError:
            pass
        SOCKET.parent.mkdir(parents=True, exist_ok=True)
        srv = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        srv.bind(str(SOCKET))
        os.chmod(SOCKET, 0o600)
        srv.listen(16)
        srv.settimeout(0.5)
        while not self.stop_requested:
            try:
                conn, _ = srv.accept()
            except socket.timeout:
                continue
            except OSError:
                break
            threading.Thread(target=self._serve_client, args=(conn,), daemon=True).start()
        try:
            srv.close()
        finally:
            try:
                SOCKET.unlink()
            except OSError:
                pass

    def run(self) -> int:
        def _term(_sig, _frame):
            self.stop_requested = True
        signal.signal(signal.SIGTERM, _term)
        signal.signal(signal.SIGINT, _term)
        threading.Thread(target=self._socket_loop, daemon=True, name="nuxel-clockd-api").start()
        threading.Thread(target=self._cue_loop, daemon=True, name="nuxel-clockd-cues").start()
        self._publish()
        log.info("scheduler ready alarms=%d timer=%s", len(self.state.get("alarms") or []),
                 (self.state.get("timer") or {}).get("state"))
        while not self.stop_requested:
            try:
                self._check()
            except Exception:  # noqa: BLE001
                log.exception("scheduler tick failed")
            time.sleep(0.25)
        for occ in list(self.state.get("occurrences") or []):
            if occ.get("state") == "ringing":
                self._stop_sound(occ)
        self._save()
        return 0


def main() -> int:
    return ClockDaemon().run()


if __name__ == "__main__":
    raise SystemExit(main())
