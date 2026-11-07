#!/usr/bin/env python3
"""PWNAGE-84000 scheduler contract tests (offline, no audio device)."""
from __future__ import annotations

import importlib.util
import json
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = ROOT / "services/nuxel-clock/nuxel-clockd.py"


def load(tmp_path, monkeypatch):
    monkeypatch.setenv("NUXEL_CLOCK_STATE_FILE", str(tmp_path / "state.json"))
    monkeypatch.setenv("NUXEL_CLOCK_STATE", str(tmp_path / "clockd.state"))
    monkeypatch.setenv("NUXEL_CLOCK_SOCKET", str(tmp_path / "clockd.sock"))
    monkeypatch.setenv("NUXEL_CLOCK_SCHEDULE", str(tmp_path / "legacy.json"))
    monkeypatch.setenv("NUXEL_CLOCK_WAKEALARM", str(tmp_path / "no-wakealarm"))
    monkeypatch.setenv("NUXEL_HAPTICS_FIFO", str(tmp_path / "no-haptics"))
    monkeypatch.setenv("NUXEL_NOTIFY", str(tmp_path / "no-notify"))
    spec = importlib.util.spec_from_file_location("nuxel_clockd_test_%d" % time.time_ns(), MODULE_PATH)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    mod.SOUNDCTL = "/bin/true"
    return mod


def test_alarm_crud_and_settings(tmp_path, monkeypatch):
    mod = load(tmp_path, monkeypatch)
    daemon = mod.ClockDaemon()
    created = daemon.dispatch({"cmd": "create-alarm", "params": {
        "id": "alarm-test", "time": "7:05", "label": "Wake", "repeat": True}})
    assert created["success"] is True
    assert created["alarm"]["time"] == "07:05"
    assert created["state"]["alarms"][0]["id"] == "alarm-test"
    out = daemon.dispatch({"cmd": "set-settings", "params": {
        "snooze_minutes": 9, "snooze_enabled": True}})
    assert out["settings"]["snooze_minutes"] == 9
    out = daemon.dispatch({"cmd": "update-alarm", "params": {
        "id": "alarm-test", "enabled": False}})
    assert out["state"]["alarms"][0]["enabled"] is False
    out = daemon.dispatch({"cmd": "delete-alarm", "params": {"id": "alarm-test"}})
    assert out["state"]["alarms"] == []
    # The state must be durable, not an in-memory lie.
    disk = json.loads((tmp_path / "state.json").read_text())
    assert disk["schema_version"] == 2
    assert disk["settings"]["snooze_minutes"] == 9


def test_alarm_occurrence_dismiss_does_not_delete_source(tmp_path, monkeypatch):
    mod = load(tmp_path, monkeypatch)
    daemon = mod.ClockDaemon()
    daemon.dispatch({"cmd": "create-alarm", "params": {
        "id": "alarm-repeat", "time": "06:30", "repeat": True}})
    now_ms = mod._now_ms()
    occ = daemon._occurrence(kind="alarm", alarm_id="alarm-repeat", key="test-key",
                             label="Wake", due_ms=now_ms, state="snoozed")
    daemon.state["occurrences"].append(occ)
    daemon._fire(occ)
    assert daemon.status()["active_occurrences"][0]["state"] == "ringing"
    out = daemon.dispatch({"cmd": "dismiss-occurrence", "params": {"id": occ["id"]}})
    assert out["success"] is True
    assert out["state"]["alarms"][0]["enabled"] is True
    assert out["state"]["alarms"][0]["id"] == "alarm-repeat"
    assert not out["state"]["active_occurrences"]


def test_snooze_creates_independent_future_occurrence(tmp_path, monkeypatch):
    mod = load(tmp_path, monkeypatch)
    daemon = mod.ClockDaemon()
    daemon.dispatch({"cmd": "create-alarm", "params": {
        "id": "alarm-snooze", "time": "06:30", "repeat": True}})
    occ = daemon._occurrence(kind="alarm", alarm_id="alarm-snooze", key="k",
                             label="Wake", due_ms=mod._now_ms(), state="snoozed")
    daemon.state["occurrences"].append(occ)
    daemon._fire(occ)
    out = daemon.dispatch({"cmd": "snooze-occurrence", "params": {"id": occ["id"]}})
    assert out["success"] is True
    snoozed = out["occurrence"]
    assert snoozed["id"] != occ["id"]
    assert snoozed["state"] == "snoozed"
    assert snoozed["due_ms"] > mod._now_ms() + 8 * 60 * 1000
    assert out["state"]["snoozed_occurrences"][0]["snoozed_from"] == occ["id"]
    assert out["state"]["alarms"][0]["enabled"] is True


def test_snooze_can_be_disabled(tmp_path, monkeypatch):
    mod = load(tmp_path, monkeypatch)
    daemon = mod.ClockDaemon()
    daemon.dispatch({"cmd": "set-settings", "params": {"snooze_enabled": False}})
    occ = daemon._occurrence(kind="alarm", alarm_id="a", key="k",
                             label="Wake", due_ms=mod._now_ms(), state="snoozed")
    daemon.state["occurrences"].append(occ)
    daemon._fire(occ)
    out = daemon.dispatch({"cmd": "snooze-occurrence", "params": {"id": occ["id"]}})
    assert out["success"] is False
    assert out["error_code"] == "SNOOZE_DISABLED"


def test_timer_fires_once_per_run(tmp_path, monkeypatch):
    mod = load(tmp_path, monkeypatch)
    daemon = mod.ClockDaemon()
    out = daemon.dispatch({"cmd": "start-timer", "params": {"duration_ms": 1200, "label": "Tea"}})
    assert out["timer"]["state"] == "running"
    run_id = out["timer"]["run_id"]
    daemon.state["timer"]["deadline_ms"] = mod._now_ms() - 1
    daemon._check()
    st = daemon.status()
    assert st["timer"]["state"] == "completed"
    assert len([o for o in st["occurrences"] if o["kind"] == "timer"]) == 1
    daemon._check()
    assert len([o for o in st["occurrences"] if o["kind"] == "timer"]) == 1
    out = daemon.dispatch({"cmd": "stop-timer", "params": {}})
    assert out["timer"]["state"] == "acknowledged"
    assert out["timer"]["run_id"] == run_id
    assert not out["state"]["active_occurrences"]


def test_legacy_schedule_migration_preserves_alarm(tmp_path, monkeypatch):
    (tmp_path / "legacy.json").write_text(json.dumps({
        "schema_version": 1,
        "alarms": [{"id": "legacy-a", "time": "08:15", "label": "Legacy", "repeat": True}],
        "timer": None,
    }))
    mod = load(tmp_path, monkeypatch)
    daemon = mod.ClockDaemon()
    st = daemon.status()
    assert st["alarms"][0]["id"] == "legacy-a"
    assert st["alarms"][0]["time"] == "08:15"
    assert (tmp_path / "legacy.json").exists()  # source retained for rollback


def test_status_reports_rtc_honestly_without_write(tmp_path, monkeypatch):
    mod = load(tmp_path, monkeypatch)
    daemon = mod.ClockDaemon()
    caps = daemon.status()["capabilities"]
    assert caps["screen_off_awake_alarm"] is True
    assert caps["rtc_wake_from_suspend_verified"] is False
    assert caps["rtc_wakealarm"]["present"] is False

def test_set_timer_is_authoritative_and_persists_sub_minute(tmp_path, monkeypatch):
    mod = load(tmp_path, monkeypatch)
    daemon = mod.ClockDaemon()
    out = daemon.dispatch({"cmd": "set-timer", "params": {"duration_ms": 30000, "label": "Tea"}})
    assert out["success"] is True
    assert out["timer"]["duration_ms"] == 30000
    assert out["timer"]["remaining_ms"] == 30000
    assert out["timer"]["state"] == "idle"
    # Reload from disk: the chosen 30 s must survive, never the 5-minute default.
    daemon2 = mod.ClockDaemon()
    t = daemon2.status()["timer"]
    assert t["duration_ms"] == 30000
    assert t["remaining_ms"] == 30000


def test_normalise_timer_preserves_zero_remaining(tmp_path, monkeypatch):
    mod = load(tmp_path, monkeypatch)
    daemon = mod.ClockDaemon()
    daemon.dispatch({"cmd": "start-timer", "params": {"duration_ms": 5000}})
    # Simulate an expired, stopped timer whose remaining_ms is exactly 0.
    daemon.state["timer"].update({"state": "acknowledged", "remaining_ms": 0,
                                  "deadline_ms": None, "duration_ms": 5000})
    daemon._normalise()
    daemon._save()
    disk = json.loads((tmp_path / "state.json").read_text())
    assert disk["timer"]["remaining_ms"] == 0
    assert disk["timer"]["duration_ms"] == 5000


def test_disabled_alarm_never_has_a_future_projection(tmp_path, monkeypatch):
    mod = load(tmp_path, monkeypatch)
    daemon = mod.ClockDaemon()
    daemon.dispatch({"cmd": "create-alarm", "params": {
        "id": "alarm-disabled", "time": "06:30", "repeat": True, "enabled": False}})
    st = daemon.status()
    assert st["alarms"][0]["enabled"] is False
    # A disabled alarm must not be returned as a next/pending candidate.
    assert not any(a.get("id") == "alarm-disabled" for a in [st.get("next")] if a)

