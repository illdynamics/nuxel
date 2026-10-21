"""Offline tests for nuxel-orientationd against a fake root (NUXEL_ROOT)."""

import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
DAEMON = os.path.join(HERE, "..", "nuxel-orientationd")


def run(root, *args, env=None):
    e = {"NUXEL_ROOT": root, "PATH": os.environ.get("PATH", "")}
    if env:
        e.update(env)
    return subprocess.run(
        [sys.executable, DAEMON, *args], capture_output=True, text=True, env=e)


def test_status_json(tmp_path):
    r = run(str(tmp_path), "status", "--json")
    assert r.returncode == 0, r.stderr
    doc = json.loads(r.stdout)
    assert doc["mode"] == "portrait"
    assert doc["auto"] is False
    assert doc["allowed"] == [0]
    assert doc["effective_orientation"] == 0
    # calibration must be honestly unverified
    assert doc["calibration"]["mount_matrix"] == "unverified"
    assert doc["compositor"]["transform_available"] is False


def test_modes_lists_seven(tmp_path):
    r = run(str(tmp_path), "modes", "--json")
    doc = json.loads(r.stdout)
    assert len(doc) == 7
    names = {m["mode"] for m in doc}
    assert names == {"portrait", "reverse_portrait", "landscape",
                     "reverse_landscape", "auto", "auto_portrait", "auto_landscape"}
    assert all(isinstance(m["allowed"], list) for m in doc)
    assert all(isinstance(m["auto"], bool) for m in doc)


def test_set_persists_and_get_returns(tmp_path):
    r = run(str(tmp_path), "set", "landscape", "--json")
    assert r.returncode == 0, r.stderr
    doc = json.loads(r.stdout)
    assert doc["success"] is True
    assert doc["mode"] == "landscape"
    assert doc["effective_orientation"] == 90
    # persisted state file exists under the fake root
    state = os.path.join(str(tmp_path), "var", "lib", "nuxel", "orientation", "state.json")
    assert os.path.exists(state)
    with open(state) as f:
        assert json.load(f)["mode"] == "landscape"
    r2 = run(str(tmp_path), "get", "--json")
    assert json.loads(r2.stdout) == "landscape"


def test_set_rejects_garbage(tmp_path):
    r = run(str(tmp_path), "set", "six", "--json")
    doc = json.loads(r.stdout)
    assert doc["success"] is False
    assert "unknown orientation mode" in doc["error"]


def test_set_auto_portrait_from_landscape_picks_legal(tmp_path):
    # Start in landscape, then switch to auto_portrait: 90 is disallowed -> 0 or 180
    run(str(tmp_path), "set", "landscape", "--json")
    r = run(str(tmp_path), "set", "auto_portrait", "--json")
    doc = json.loads(r.stdout)
    assert doc["success"] is True
    assert doc["effective_orientation"] in (0, 180)
    assert doc["auto"] is True


def test_selftest_passes(tmp_path):
    r = run(str(tmp_path), "selftest")
    assert "PASS" in r.stdout


def test_status_reports_sensor_unavailable_without_hardware(tmp_path):
    r = run(str(tmp_path), "status", "--json")
    doc = json.loads(r.stdout)
    # no real IIO/DBus sensor on this host -> iio-accel and proxy unavailable
    assert doc["sensor"]["available"] is False
