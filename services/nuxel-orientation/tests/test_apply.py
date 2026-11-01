"""Offline tests for the compositor transform backend (honest results only)."""

import json
import subprocess

import nuxel_orientation.apply as apply_mod


def test_transform_for_mapping():
    # PWNAGE-54000: canonical clockwise pose -> the compositor transform that
    # the historical physical test used.  90/270 are deliberately reversed.
    assert apply_mod.transform_for(0) == "normal"
    assert apply_mod.transform_for(90) == "270"
    assert apply_mod.transform_for(180) == "180"
    assert apply_mod.transform_for(270) == "90"


def test_wlr_randr_available_uses_executable_lookup(monkeypatch):
    monkeypatch.setattr(apply_mod.shutil, "which", lambda name: "/usr/bin/wlr-randr")
    assert apply_mod.wlr_randr_available() is True
    monkeypatch.setattr(apply_mod.shutil, "which", lambda name: None)
    assert apply_mod.wlr_randr_available() is False


def test_apply_transform_dry_run_never_claims_applied(monkeypatch):
    monkeypatch.setattr(apply_mod, "output_status", lambda *a, **k: {
        "output": "HEADLESS-1", "transform": "normal", "applied": True})
    res = apply_mod.apply_transform(90, dry_run=True)
    assert res["applied"] is False
    assert res["dry_run"] is True
    assert res["transform"] == "270"


def test_apply_transform_missing_binary_is_honest(monkeypatch):
    monkeypatch.setattr(apply_mod, "wlr_randr_available", lambda: False)
    res = apply_mod.apply_transform(90)
    assert res["applied"] is False
    assert "not present" in res["error"]


def test_apply_transform_success_requires_live_readback(monkeypatch):
    monkeypatch.setattr(apply_mod, "wlr_randr_available", lambda: True)
    calls = []

    def fake_output_status(config=None, output=None):
        calls.append(output)
        transform = "270" if len(calls) > 1 else "normal"
        return {"backend": "wlr-randr", "output": "HEADLESS-1",
                "transform": transform, "physical_width": 720,
                "physical_height": 1520,
                "scale": 1.0 if transform in ("90", "270") else 2.0,
                "logical_width": 1520 if transform in ("90", "270") else 360,
                "logical_height": 720 if transform in ("90", "270") else 760,
                "applied": True, "error": ""}

    def fake_run(*a, **k):
        return type("R", (), {"returncode": 0, "stderr": "", "stdout": ""})()

    monkeypatch.setattr(apply_mod, "output_status", fake_output_status)
    monkeypatch.setattr(apply_mod.subprocess, "run", fake_run)
    res = apply_mod.apply_transform(90)
    assert res["applied"] is True
    assert res["transform"] == "270"
    assert res["output"] == "HEADLESS-1"
    assert (res["logical_width"], res["logical_height"]) == (1520, 720)


def test_apply_transform_failure_is_not_success(monkeypatch):
    monkeypatch.setattr(apply_mod, "wlr_randr_available", lambda: True)
    monkeypatch.setattr(apply_mod, "output_status", lambda *a, **k: {
        "backend": "wlr-randr", "output": "HEADLESS-1",
        "transform": "normal", "applied": True, "error": ""})
    monkeypatch.setattr(apply_mod.subprocess, "run",
                        lambda *a, **k: type("R", (), {"returncode": 1, "stderr": "transform failed", "stdout": ""})())
    res = apply_mod.apply_transform(90)
    assert res["applied"] is False
    assert "transform failed" in res["error"] or "did not report" in res["error"]


def test_output_status_selects_live_output_and_swaps_logical_dimensions(monkeypatch):
    payload = [{
        "name": "HEADLESS-1", "enabled": True, "transform": "90", "scale": 2.0,
        "modes": [{"width": 720, "height": 1520, "current": True}],
    }]
    monkeypatch.setattr(apply_mod, "wlr_randr_available", lambda: True)
    monkeypatch.setattr(apply_mod.subprocess, "run",
                        lambda *a, **k: type("R", (), {
                            "returncode": 0, "stderr": "", "stdout": json.dumps(payload)})())
    st = apply_mod.output_status({"compositor": {"output": "auto"}})
    assert st["output"] == "HEADLESS-1"
    assert st["transform"] == "90"
    assert (st["logical_width"], st["logical_height"]) == (760, 360)


def test_output_status_reports_missing_configured_output(monkeypatch):
    payload = [{"name": "HEADLESS-1", "enabled": True, "transform": "normal",
                "modes": [{"width": 720, "height": 1520, "current": True}]}]
    monkeypatch.setattr(apply_mod, "wlr_randr_available", lambda: True)
    monkeypatch.setattr(apply_mod.subprocess, "run",
                        lambda *a, **k: type("R", (), {
                            "returncode": 0, "stderr": "", "stdout": json.dumps(payload)})())
    st = apply_mod.output_status({"compositor": {"output": "DSI-1"}})
    assert st["output"] == "DSI-1"
    assert "no enabled output" in st["error"]


def test_output_status_command_timeout(monkeypatch):
    monkeypatch.setattr(apply_mod, "wlr_randr_available", lambda: True)

    def boom(*a, **k):
        raise subprocess.TimeoutExpired("wlr-randr", 5)
    monkeypatch.setattr(apply_mod.subprocess, "run", boom)
    st = apply_mod.output_status({})
    assert st["backend"] == "wlr-randr"
    assert st["error"]


def test_landscape_scale_is_one_for_real_logical_geometry():
    cfg = {"compositor": {"portrait_scale": 2, "landscape_scale": 1}}
    assert apply_mod.scale_for(0, cfg) == 2
    assert apply_mod.scale_for(180, cfg) == 2
    assert apply_mod.scale_for(90, cfg) == 1
    assert apply_mod.scale_for(270, cfg) == 1


def test_input_matrices_match_each_compositor_transform_once():
    import json
    from pathlib import Path
    cfg = json.loads(Path(__file__).resolve().parents[3].joinpath(
        "configs/nuxel/orientation/orientation.json").read_text())
    maps = cfg["compositor"]["input_matrix_map"]

    def apply(m, x, y):
        return (m[0] * x + m[1] * y + m[2], m[3] * x + m[4] * y + m[5])

    # The libinput matrix consumes raw portrait touch coordinates and maps them
    # ONCE into the logical desktop.  These are the geometric corner mappings
    # for the compositor transform that was actually read back.
    assert apply(maps["normal"], 0, 0) == (0, 0)
    assert apply(maps["90"], 0, 0) == (1, 0)       # (1-y, x)
    assert apply(maps["180"], 0, 0) == (1, 1)      # (1-x, 1-y)
    assert apply(maps["270"], 0, 0) == (0, 1)      # (y, 1-x)
    # Inverse corner sanity: every mapped point stays inside 0..1.
    for m in maps.values():
        for x in (0, 1):
            for y in (0, 1):
                nx, ny = apply(m, x, y)
                assert 0 <= nx <= 1 and 0 <= ny <= 1
