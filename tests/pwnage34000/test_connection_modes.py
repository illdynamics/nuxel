"""PWNAGE-34000 offline tests: connection-mode state + transport model."""
import importlib.util
import json
import os
import stat
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
SRC = REPO / "services" / "nuxel-bridge" / "src"


def load(name):
    spec = importlib.util.spec_from_file_location(name, SRC / (name + ".py"))
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def test_connection_mode_state_defaults_to_charging(tmp_path):
    si = load("system_indicators")
    run = tmp_path / "run"
    (run / "nuxel").mkdir(parents=True)
    state = si.connection_mode_state(run_root=str(run))
    assert state["selected"] == "charging"
    assert state["active"] is False
    assert state["transition_in_progress"] is False


def test_connection_mode_state_reads_selection_and_activation(tmp_path):
    si = load("system_indicators")
    run = tmp_path / "run"
    (run / "nuxel").mkdir(parents=True)
    (run / "nuxel" / "connection-mode.json").write_text(
        json.dumps({"mode": "file_transfer", "transition_in_progress": False}))
    (run / "nuxel" / "usb-mode.state").write_text(
        json.dumps({"mode": "file_transfer", "active": True,
                    "endpoint_state": "active", "source": "helper"}))
    state = si.connection_mode_state(run_root=str(run))
    assert state["selected"] == "file_transfer"
    assert state["active"] is True
    assert state["endpoint_state"] == "active"


def test_usb_mode_refuses_unknown(tmp_path):
    um = load("usb_mode")
    sel = tmp_path / "selection.json"
    act = tmp_path / "activation.json"
    helper = tmp_path / "helper.sh"
    helper.write_text("#!/bin/sh\nexit 0\n")
    helper.chmod(helper.stat().st_mode | stat.S_IXUSR)
    os.environ["NUXEL_CONNECTION_MODE"] = str(sel)
    os.environ["NUXEL_USB_MODE_STATE"] = str(act)
    os.environ["NUXEL_USB_MODE_HELPER"] = str(helper)
    try:
        res = um.set_mode("bogus")
        assert res["success"] is False
        assert res["error"] == "unknown-mode"
    finally:
        for k in ("NUXEL_CONNECTION_MODE", "NUXEL_USB_MODE_STATE", "NUXEL_USB_MODE_HELPER"):
            os.environ.pop(k, None)


def test_usb_mode_charging_records_success_without_faking_transfer(tmp_path):
    um = load("usb_mode")
    sel = tmp_path / "selection.json"
    act = tmp_path / "activation.json"
    helper = tmp_path / "helper.sh"
    helper.write_text("#!/bin/sh\nprintf '{\"mode\":\"charging\",\"active\":false,\"endpoint_state\":\"inactive\",\"source\":\"charging-mode\",\"error\":null}\\n' > \"$NUXEL_USB_MODE_STATE\"\n")
    helper.chmod(helper.stat().st_mode | stat.S_IXUSR)
    os.environ["NUXEL_CONNECTION_MODE"] = str(sel)
    os.environ["NUXEL_USB_MODE_STATE"] = str(act)
    os.environ["NUXEL_USB_MODE_HELPER"] = str(helper)
    try:
        res = um.set_mode("charging")
        assert res["success"] is True
        assert res["selected"] == "charging"
        assert res["active"] is False
    finally:
        for k in ("NUXEL_CONNECTION_MODE", "NUXEL_USB_MODE_STATE", "NUXEL_USB_MODE_HELPER"):
            os.environ.pop(k, None)
