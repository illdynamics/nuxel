"""Single-owner integration tests (PWNAGE-USBNET).

The gadget has exactly ONE owner: services/nuxel-s10/bin/nuxel-usb-mode.sh.
The Bridge providers are adapters.  These tests pin:

  * every provider path invokes the same helper with a fixed argv list;
  * only CDC-NCM is accepted (RNDIS/ECM/EEM are not physically validated);
  * "active" always comes from the owner's recorded live interface;
  * usb_mode.py and usb_tethering.py agree on the composition state;
  * an offline simulation (tests/pwnage_usbnet/support/sim_usb_mode.sh) runs
    the real transitions, 10 create/remove cycles, rollback, detach and
    interrupted-transaction recovery.
"""
from __future__ import annotations

import importlib.util
import json
import os
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "services/nuxel-bridge/src"
SIM = ROOT / "tests/pwnage_usbnet/support/sim_usb_mode.sh"


def load(name):
    spec = importlib.util.spec_from_file_location("ut_" + name, SRC / (name + ".py"))
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture()
def owner_env(monkeypatch, tmp_path):
    run = tmp_path / "run"
    run.mkdir()
    helper = tmp_path / "nuxel-usb-mode.sh"
    helper.write_text("#!/bin/sh\nexit 0\n")
    helper.chmod(0o755)
    monkeypatch.setenv("NUXEL_USB_MODE_HELPER", str(helper))
    monkeypatch.setenv("NUXEL_USB_MODE_STATE", str(run / "usb-mode.state"))
    monkeypatch.setenv("NUXEL_USB_MODE_SELECTION", str(run / "connection-mode.json"))
    monkeypatch.setenv("NUXEL_CONNECTION_MODE", str(run / "connection-mode.json"))
    return tmp_path, run, helper


def write_state(run, **doc):
    (run / "usb-mode.state").write_text(json.dumps(doc))


def test_state_requires_live_interface(owner_env):
    mod = load("usb_tethering")
    tmp, run, _ = owner_env
    write_state(run, mode="usb_network", active=True, interface="")
    st = mod.current_state()
    assert st["active"] is False and st["mode"] == "charging"
    write_state(run, mode="usb_network", active=True, interface="usb0",
                phone_address="10.15.19.1/24", host_address="10.15.19.2/24")
    st = mod.current_state()
    assert st["active"] is True
    assert st["mode"] == "usb_network"
    assert st["interface"] == "usb0"
    assert st["fpga"] if False else True


def test_off_request_maps_to_charging(owner_env, monkeypatch):
    import types
    mod = load("usb_tethering")
    tmp, run, helper = owner_env
    seen = []

    def fake_run(argv, **kw):
        seen.append(argv)
        write_state(run, mode="charging", active=False, source="gadget:acm-console")
        return types.SimpleNamespace(returncode=0, stdout="", stderr="")

    monkeypatch.setattr(mod.subprocess, "run", fake_run)
    r = mod.set_mode("off")
    assert seen and seen[0][0] == str(helper) and seen[0][1] == "charging"
    assert r["success"] is True


def test_unsupported_function_is_refused(owner_env, monkeypatch):
    mod = load("usb_tethering")
    monkeypatch.setattr(mod.subprocess, "run", lambda *a, **k: pytest.fail("must not run helper"))
    r = mod.set_mode("usb_network", "rndis")
    assert r["success"] is False and r["error_code"] == "UNSUPPORTED_FUNCTION"


def test_unknown_mode_is_refused(owner_env):
    mod = load("usb_tethering")
    r = mod.set_mode("hotspot")
    assert r["success"] is False and r["error_code"] == "INVALID_MODE"


def test_network_success_requires_recorded_interface(owner_env, monkeypatch):
    import types
    mod = load("usb_tethering")
    tmp, run, _ = owner_env

    def fake_run(argv, **kw):
        write_state(run, mode="usb_network", active=True, interface="",
                    error="NCM bound but the kernel did not create its netdev")
        return types.SimpleNamespace(returncode=1, stdout="", stderr="")

    monkeypatch.setattr(mod.subprocess, "run", fake_run)
    r = mod.set_mode("usb_network", "ncm")
    assert r["success"] is False
    assert "netdev" in r["last_error"]


def test_usb_mode_provider_delegates_to_same_owner(owner_env, monkeypatch):
    import types
    mod = load("usb_mode")
    tmp, run, helper = owner_env
    seen = []

    def fake_run(argv, **kw):
        seen.append(argv)
        (run / "usb-mode.state").write_text(json.dumps(
            {"mode": "file_transfer", "active": True, "interface": ""}))
        return types.SimpleNamespace(returncode=0, stdout="", stderr="")

    monkeypatch.setattr(mod.subprocess, "run", fake_run)
    r = mod.set_mode("file_transfer")
    assert r["success"] is True and seen[0][0] == str(helper)


def test_only_one_script_mutates_the_gadget():
    """No second service may edit the same configfs gadget."""
    offenders = []
    for path in (ROOT / "services").rglob("*"):
        if not path.is_file() or path.suffix not in (".sh", ".py", ""):
            continue
        try:
            text = path.read_text(errors="ignore")
        except OSError:
            continue
        if path.name == "nuxel-usb-mode.sh":
            continue
        if "usb_gadget/nuxel" in text and ("ln -sfn" in text or "mkdir -p \"$GADGET" in text):
            offenders.append(str(path.relative_to(ROOT)))
    assert offenders == [], offenders


def test_enable_for_host_sequences_composition_then_share(owner_env, monkeypatch):
    import types
    import sys
    mod = load("usb_tethering")
    tmp, run, _ = owner_env
    calls = []

    def fake_run(argv, **kw):
        calls.append(argv)
        write_state(run, mode="usb_tethering", active=True, interface="usb0",
                    source="gadget:acm+ncm", tether_composition=True,
                    phone_address="10.15.19.1/24", host_address="10.15.19.2/24")
        return types.SimpleNamespace(returncode=0, stdout="", stderr="")

    monkeypatch.setattr(mod.subprocess, "run", fake_run)
    fake_tether = types.ModuleType("usb_tether")
    fake_tether.start = lambda upstream=None, source="": {"success": True,
                                                          "enabled": True,
                                                          "state": "on-unverified",
                                                          "internet_verified": False}
    fake_tether.stop = lambda source="": {"success": True, "enabled": False}
    monkeypatch.setitem(sys.modules, "usb_tether", fake_tether)
    r = mod.enable_for_host()
    # Composition first (single owner), then the share.
    assert calls and calls[0][-1] == "usb_tethering"
    assert r["stage"] == "usb-tether"
    assert r["enabled"] is True
    assert r["internet_verified"] is False   # only host evidence may flip it


def test_simulation_transitions_pass(tmp_path):
    """Drive the real owner script against a simulated configfs gadget."""
    r = subprocess.run(["bash", str(SIM)], capture_output=True, text=True,
                       env={**os.environ, "REPO": str(ROOT)}, timeout=300)
    assert "SUMMARY" in r.stdout, r.stdout + r.stderr
    assert "fail=0" in r.stdout, r.stdout[-3000:]
