"""Tri-Link USB truth: the RUNNING build decides, not the version string.

tri_link_status.usb_status() previously hardcoded "4.14.253 => blocked", which
would keep the USB transport UNAVAILABLE even after the NCM lifecycle patch is
running.  These tests pin the marker-based verdict and the activation read-back.
"""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
MODULE = ROOT / "services/nuxel-bridge/src/tri_link_status.py"

CFG = "\n".join([
    "CONFIG_USB_CONFIGFS=y", "CONFIG_USB_F_NCM=y", "CONFIG_USB_CONFIGFS_NCM=y",
    "CONFIG_USB_DWC3=y", "CONFIG_USB_DWC3_DUAL_ROLE=y", "",
])


def load():
    spec = importlib.util.spec_from_file_location("tri_under_test", MODULE)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture()
def roots(monkeypatch, tmp_path):
    gadget = tmp_path / "gadget"
    (gadget / "nuxel" / "functions" / "acm.usb0").mkdir(parents=True)
    net = tmp_path / "net"
    net.mkdir()
    misc = tmp_path / "misc" / "usb_ncm"
    misc.mkdir(parents=True)
    state = tmp_path / "usb-mode.state"
    proc = tmp_path / "proc"
    (proc / "net").mkdir(parents=True)
    return gadget, net, misc, state, proc


def test_baseline_without_marker_is_blocked(monkeypatch, roots):
    mod = load()
    gadget, net, misc, state, proc = roots
    r = mod.usb_status(release="4.14.253", gadget_root=gadget, net_root=net,
                       proc_root=proc, kernel_config=CFG,
                       fix_path=str(misc / "nuxel_fix"),
                       activation_path=str(state))
    assert r["status"] in ("NEEDS_VALIDATION", "SUPPORTED_NOT_ENABLED")
    checks = {c["name"]: c["status"] for c in r["checks"]}
    assert checks["ncm-safety"] == "BLOCKED"


def test_marker_makes_build_eligible_and_reports_activation(monkeypatch, roots):
    mod = load()
    gadget, net, misc, state, proc = roots
    (misc / "nuxel_fix").write_text(mod.NCM_FIX_MARKER + "\n")
    (net / "usb0").mkdir()
    state.write_text(json.dumps({"mode": "usb_network", "active": True,
                                 "interface": "usb0"}))
    r = mod.usb_status(release="4.14.253", gadget_root=gadget, net_root=net,
                       proc_root=proc, kernel_config=CFG,
                       fix_path=str(misc / "nuxel_fix"),
                       activation_path=str(state))
    checks = {c["name"]: c["status"] for c in r["checks"]}
    assert checks["ncm-safety"] == "FIX_MARKER_PRESENT"
    assert checks["usb-mode-owner"] == "OK"
    assert r["modes"]["ncm"]["status"] == "NEEDS_PHYSICAL_SOAK"
    # Still not READY: there is no authenticated host probe recorded.
    assert r["status"] != "READY"


def test_never_claims_ready_from_configfs_alone(monkeypatch, roots):
    mod = load()
    gadget, net, misc, state, proc = roots
    (gadget / "nuxel" / "functions" / "ncm.usb0").mkdir()
    (misc / "nuxel_fix").write_text(mod.NCM_FIX_MARKER + "\n")
    r = mod.usb_status(release="4.14.253", gadget_root=gadget, net_root=net,
                       proc_root=proc, kernel_config=CFG,
                       fix_path=str(misc / "nuxel_fix"),
                       activation_path=str(state))
    assert r["status"] in ("SUPPORTED_NOT_ENABLED", "UNAVAILABLE",
                           "NEEDS_VALIDATION")
    assert r["status"] != "READY"
