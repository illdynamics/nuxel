"""Offline tests for the USB networking adapter (PWNAGE-107000 -> status 114000).

The adapter no longer owns configfs: services/nuxel-s10/bin/nuxel-usb-mode.sh
does, with flock()-serialised journaled transitions.  These tests keep the
original intent - default OFF, CDC-NCM as the only enabled data plane, and a
tether *composition* that never implies Internet - while matching the adapter's
real read-back contract.
"""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
MODULE = ROOT / "services/nuxel-bridge/src/usb_tethering.py"


def load_module():
    spec = importlib.util.spec_from_file_location("usb_tethering_under_test", MODULE)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


def write(path: Path, obj) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj))
    return path


@pytest.fixture()
def env(monkeypatch, tmp_path):
    monkeypatch.setenv("NUXEL_USB_MODE_STATE", str(tmp_path / "act.json"))
    monkeypatch.setenv("NUXEL_USB_MODE_SELECTION", str(tmp_path / "sel.json"))
    return tmp_path


def test_current_state_default_off(env):
    mod = load_module()
    st = mod.current_state()
    assert st["active"] is False
    assert st["mode"] == "charging"
    assert st["interface"] == ""
    assert st["device_ip"] == ""
    assert st["subnet"] == ""


def test_unknown_mode_and_function(monkeypatch, env):
    mod = load_module()
    monkeypatch.setenv("NUXEL_USB_MODE_HELPER", "/definitely/not/present")
    assert mod.set_mode("bogus")["success"] is False
    r = mod.set_mode("usb_network", "rndis")
    assert r["success"] is False and r["error_code"] == "UNSUPPORTED_FUNCTION"


def test_helper_missing_is_error(monkeypatch, env):
    mod = load_module()
    monkeypatch.setenv("NUXEL_USB_MODE_HELPER", "/definitely/not/present")
    r = mod.set_mode("usb_network", "ncm")
    assert r["success"] is False
    assert r["error_code"] == "PROVIDER_UNAVAILABLE"


def test_network_inactive_selection(env):
    mod = load_module()
    write(env / "sel.json", {"mode": "usb_network"})
    write(env / "act.json", {"mode": "usb_network", "active": False})
    st = mod.current_state()
    assert st["selected"] == "usb_network"
    assert st["active"] is False
    assert st["mode"] == "charging"
    assert st["device_ip"] == ""


def test_tether_composition_is_not_internet(env):
    mod = load_module()
    write(env / "sel.json", {"mode": "usb_tethering"})
    write(env / "act.json", {"mode": "usb_tethering", "active": True,
                             "interface": "usb0", "tether_composition": True,
                             "phone_address": "10.15.19.1/24",
                             "host_address": "10.15.19.2/24",
                             "source": "gadget:acm+ncm"})
    st = mod.current_state()
    assert st["active"] is True
    assert st["mode"] == "usb_tethering"
    # Same local USB link; forwarding/NAT lives in usb_tether.py and is not
    # implied by the composition.
    assert st["device_ip"] == "10.15.19.1/24"
    assert st["subnet"] == "10.15.19.0/24"
    assert st["tether_composition"] is True
    # There is no "internet" field here on purpose: the adapter must not imply it.
    assert "internet_verified" not in st


def test_default_function_is_ncm(monkeypatch, env):
    mod = load_module()
    seen = {}

    class P:
        returncode = 0
        stdout = ""
        stderr = ""

    def fake_run(argv, **kwargs):
        seen["argv"] = list(argv)
        write(env / "act.json", {"mode": "usb_network", "active": True,
                                 "interface": "usb0", "source": "gadget:acm+ncm"})
        return P()

    monkeypatch.setenv("NUXEL_USB_MODE_HELPER", __file__)  # any existing path
    monkeypatch.setattr(mod.subprocess, "run", fake_run)
    r = mod.set_mode("usb_network")       # default function
    assert seen["argv"][-1] == "usb_network"
    assert r["success"] is True
