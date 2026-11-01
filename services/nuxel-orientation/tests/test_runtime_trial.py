"""Runtime trial/rollback tests.  No hardware, no real fb, no compositor."""

import importlib.machinery
import importlib.util
import json
import os
import time

import pytest

import nuxel_orientation.apply as apply_mod

HERE = os.path.dirname(os.path.abspath(__file__))
DAEMON = os.path.join(HERE, "..", "nuxel-orientationd")


def load_daemon(tmp_path, monkeypatch):
    monkeypatch.setenv("NUXEL_ROOT", str(tmp_path))
    loader = importlib.machinery.SourceFileLoader("pwnage46000_daemon", DAEMON)
    spec = importlib.util.spec_from_loader(loader.name, loader)
    mod = importlib.util.module_from_spec(spec)
    loader.exec_module(mod)
    mod.ROOT = str(tmp_path)
    return mod


def fake_apply(monkeypatch, calls):
    def _apply(degrees, config=None, dry_run=False, output=None):
        calls.append(degrees)
        transform = apply_mod.transform_for(degrees, config)
        swapped = transform in ("90", "270")
        return {"applied": True, "display_verified": True, "geometry_verified": True,
                "backend": "wlr-randr", "output": "HEADLESS-1",
                "transform": transform,
                "logical_width": 1520 if swapped else 360,
                "logical_height": 720 if swapped else 760,
                "physical_width": 720, "physical_height": 1520,
                "scale": 1.0 if swapped else 2.0,
                "error": ""}
    monkeypatch.setattr(apply_mod, "apply_transform", _apply)
    return _apply


def fake_status(monkeypatch, transform="normal"):
    def _status(config=None, output=None):
        return {"applied": True, "backend": "wlr-randr", "output": "HEADLESS-1",
                "transform": transform, "physical_width": 720, "physical_height": 1520,
                "scale": 1.0 if transform in ("90", "270") else 2.0,
                "logical_width": 1520 if transform in ("90", "270") else 360,
                "logical_height": 720 if transform in ("90", "270") else 760,
                "error": ""}
    monkeypatch.setattr(apply_mod, "output_status", _status)


def test_default_mode_change_commits_without_invisible_trial(tmp_path, monkeypatch):
    mod = load_daemon(tmp_path, monkeypatch)
    calls = []
    fake_apply(monkeypatch, calls)
    fake_status(monkeypatch, "270")
    rt = mod.Runtime(mod.load_config())
    st = rt.set_mode("landscape", apply_now=True, request_id="COMMIT")
    assert st["mode"] == "landscape"
    assert st["effective_orientation"] == 90
    assert st["applied"] is True
    assert st["display_verified"] is True
    assert st["transition_state"] == "verified"
    assert st["trial"]["pending_confirmation"] is False
    assert calls[-1] == 90


def test_explicit_trial_arms_bounded_window(tmp_path, monkeypatch):
    mod = load_daemon(tmp_path, monkeypatch)
    calls = []
    fake_apply(monkeypatch, calls)
    fake_status(monkeypatch, "90")
    rt = mod.Runtime(mod.load_config())
    st = rt.set_mode("landscape", apply_now=True, arm_trial=True,
                     trial_seconds=75, request_id="T1")
    assert st["mode"] == "landscape"
    assert st["effective_orientation"] == 90
    assert st["applied"] is True
    assert st["trial"]["pending_confirmation"] is True
    assert 60 <= st["trial"]["deadline_epoch"] - st["trial"]["started_epoch"] <= 90
    assert calls[-1] == 90


def test_yes_commits_as_last_good(tmp_path, monkeypatch):
    mod = load_daemon(tmp_path, monkeypatch)
    fake_apply(monkeypatch, [])
    fake_status(monkeypatch, "normal")
    rt = mod.Runtime(mod.load_config())
    rt.set_mode("portrait", arm_trial=True, trial_seconds=75, request_id="T2")
    rt.set_mode("landscape", arm_trial=True, trial_seconds=75, request_id="T3")
    st = rt.confirm("T3", "yes")
    assert st["trial"]["pending_confirmation"] is False
    good = mod.load_last_good(rt.config)
    assert good["mode"] == "landscape"
    assert good["effective_orientation"] == 90


def test_no_rolls_back_to_previous_good(tmp_path, monkeypatch):
    mod = load_daemon(tmp_path, monkeypatch)
    fake_apply(monkeypatch, [])
    fake_status(monkeypatch, "normal")
    rt = mod.Runtime(mod.load_config())
    rt.set_mode("portrait", arm_trial=True, trial_seconds=75, request_id="T4")
    rt.set_mode("reverse-portrait", arm_trial=True, trial_seconds=75, request_id="T5")
    st = rt.confirm("T5", "no")
    assert st["mode"] == "portrait"
    assert st["effective_orientation"] == 0
    assert "rollback" in st["last_error"]


def test_blank_saved_answer_rolls_back(tmp_path, monkeypatch):
    mod = load_daemon(tmp_path, monkeypatch)
    fake_apply(monkeypatch, [])
    fake_status(monkeypatch, "normal")
    rt = mod.Runtime(mod.load_config())
    rt.set_mode("landscape", arm_trial=True, trial_seconds=75, request_id="T6")
    st = rt.confirm("T6", "")
    assert st["effective_orientation"] == 0
    assert st["mode"] == "portrait"


def test_watchdog_timeout_rolls_back(tmp_path, monkeypatch):
    mod = load_daemon(tmp_path, monkeypatch)
    fake_apply(monkeypatch, [])
    fake_status(monkeypatch, "normal")
    rt = mod.Runtime(mod.load_config())
    rt.set_mode("reverse-landscape", arm_trial=True, trial_seconds=60, request_id="T7")
    rt.trial["deadline_epoch"] = time.time() - 1
    rt._trial_watchdog()
    assert rt.trial is None
    assert rt.effective == 0
    assert "timeout" in rt.last_error


def test_stale_trial_id_cannot_commit_new_trial(tmp_path, monkeypatch):
    mod = load_daemon(tmp_path, monkeypatch)
    fake_apply(monkeypatch, [])
    fake_status(monkeypatch, "normal")
    rt = mod.Runtime(mod.load_config())
    rt.set_mode("landscape", arm_trial=True, trial_seconds=75, request_id="NEW")
    st = rt.confirm("OLD", "yes")
    assert st["trial"]["pending_confirmation"] is True
    assert st["trial"]["request_id"] == "NEW"


def test_presenter_state_never_double_applies_the_compositor_transform(tmp_path, monkeypatch):
    mod = load_daemon(tmp_path, monkeypatch)
    cfg = mod.load_config()
    cfg["compositor"]["screencopy_already_transformed"] = True
    cfg["compositor"]["presenter_state"] = "/presenter"
    display = {"transform": "90", "output": "HEADLESS-1",
               "logical_width": 1520, "logical_height": 720,
               "backend": "wlr-randr", "applied": True}
    mod._emit_presenter_state(cfg, display, 90)
    body = (tmp_path / "presenter").read_text()
    assert "transform=90\n" in body
    assert "presenter_rotation=0\n" in body

    cfg["compositor"]["screencopy_already_transformed"] = False
    mod._emit_presenter_state(cfg, display, 90)
    body = (tmp_path / "presenter").read_text()
    assert "presenter_rotation=90\n" in body


def test_blocked_auto_mode_holds_legal_pose_without_arming_trial(tmp_path, monkeypatch):
    """No live gravity source => auto is selectable but never claims rotation.

    A trial here would time out and fight the owner's choice; worse, the UI
    would imply the screen followed a sensor that does not exist.
    """
    mod = load_daemon(tmp_path, monkeypatch)
    calls = []
    fake_apply(monkeypatch, calls)
    fake_status(monkeypatch, "90")
    monkeypatch.setattr(mod, "sensor_probe", lambda config, start=False: {
        "sources": [], "available": False, "preferred": None, "unverified": True})
    rt = mod.Runtime(mod.load_config())
    rt.set_mode("landscape", arm_trial=False, request_id="L")
    st = rt.set_mode("auto-portrait", apply_now=True, arm_trial=True,
                     trial_seconds=75, request_id="A")
    assert st["mode"] == "auto-portrait"
    assert st["effective_orientation"] in (0, 180)
    assert st["trial"]["pending_confirmation"] is False
    assert st["auto_state"] == "blocked_sensor_unavailable"
    assert "blocked" in st["last_error"]
    # The chosen legal portrait pose was actually applied.
    assert calls[-1] in (0, 180)


def test_auto_sensor_tick_applies_real_change_and_commits(tmp_path, monkeypatch):
    """A genuine gravity sample drives a real transform transaction."""
    import nuxel_orientation.sensors as sensors

    mod = load_daemon(tmp_path, monkeypatch)
    calls = []
    fake_apply(monkeypatch, calls)
    fake_status(monkeypatch, "normal")
    monkeypatch.setattr(mod, "sensor_probe", lambda config, start=False: {
        "sources": [{"source": "iio-sysfs-accel", "available": True,
                     "auto_capable": True}],
        "available": True, "preferred": "iio-sysfs-accel",
        "unverified": True, "hub": {"raw_live": True}})
    monkeypatch.setattr(mod, "sensor_reading", lambda config, source: (
        sensors.SensorReading(9.8, 0.0, 0.0, source=source)))
    rt = mod.Runtime(mod.load_config())
    rt.set_mode("auto", apply_now=True, request_id="AUTO")
    # Feed enough real samples to cross the 450 ms hysteresis window.
    for _ in range(8):
        time.sleep(0.11)
        rt._sensor_tick()
    assert rt.effective == 90
    assert rt.display_verified if hasattr(rt, "display_verified") else True
    assert calls[-1] == 90
    assert rt.transition_state == "verified"
    assert rt.last_sensor_read["source"] == "iio-sysfs-accel"


def test_auto_mode_selection_requests_sensor_hub_start(tmp_path, monkeypatch):
    mod = load_daemon(tmp_path, monkeypatch)
    fake_apply(monkeypatch, [])
    fake_status(monkeypatch, "normal")
    seen = []
    def probe(config, start=False):
        seen.append(start)
        return {"sources": [], "available": False, "preferred": None,
                "unverified": True, "hub": {"raw_live": False,
                "reason": "vendor Android lhd daemon is not installed"}}
    monkeypatch.setattr(mod, "sensor_probe", probe)
    rt = mod.Runtime(mod.load_config())
    seen.clear()
    rt.set_mode("auto-landscape", apply_now=True, request_id="AUTO-START")
    assert True in seen
