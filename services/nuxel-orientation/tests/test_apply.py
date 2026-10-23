"""Offline tests for the compositor apply/revert path (honest results only)."""

import nuxel_orientation.apply as apply_mod


def test_transform_for_mapping():
    assert apply_mod.transform_for(0) == "normal"
    assert apply_mod.transform_for(90) == "270"
    assert apply_mod.transform_for(180) == "180"
    assert apply_mod.transform_for(270) == "90"


def test_apply_transform_dry_run_never_claims_applied():
    res = apply_mod.apply_transform(90, dry_run=True)
    assert res["applied"] is False
    assert res["dry_run"] is True
    assert res["transform"] == "270"


def test_apply_transform_missing_binary_is_honest(monkeypatch):
    monkeypatch.setattr(apply_mod, "wlr_randr_available", lambda: False)
    res = apply_mod.apply_transform(90)
    assert res["applied"] is False
    assert "not present" in res["error"]


def test_apply_transform_success_when_binary_returns_zero(monkeypatch):
    monkeypatch.setattr(apply_mod, "wlr_randr_available", lambda: True)
    monkeypatch.setattr(apply_mod.subprocess, "run",
                        lambda *a, **k: type("R", (), {"returncode": 0, "stderr": ""})())
    res = apply_mod.apply_transform(0)
    assert res["applied"] is True
    assert res["transform"] == "normal"


def test_apply_transform_failure_reported(monkeypatch):
    monkeypatch.setattr(apply_mod, "wlr_randr_available", lambda: True)
    monkeypatch.setattr(apply_mod.subprocess, "run",
                        lambda *a, **k: type("R", (), {"returncode": 1, "stderr": "transform failed"})())
    res = apply_mod.apply_transform(90)
    assert res["applied"] is False
    assert "transform failed" in res["error"]
