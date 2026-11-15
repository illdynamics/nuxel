"""USB Internet tethering provider tests (PWNAGE-USBNET).

The provider must be narrow and honest: one owned table, exact source address,
no global flush, no console-guard mutation, no IPv4-forwarding left behind, an
explicit refusal instead of silently bypassing an armed VPN kill switch, and
`internet_verified` only from *current* attached-host evidence - a configured
forwarding path is not proof of Internet.
"""
from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
MODULE = ROOT / "services/nuxel-bridge/src/usb_tether.py"


@pytest.fixture()
def monkeypatch_env(monkeypatch, tmp_path):
    """Point the provider's runtime state/evidence at a private directory."""
    monkeypatch.setenv("NUXEL_USB_TETHER_STATE", str(tmp_path / "usb-tether.json"))
    monkeypatch.setenv("NUXEL_USB_HOST_EVIDENCE", str(tmp_path / "usb-tether-host.json"))
    monkeypatch.setenv("NUXEL_USB_MODE_STATE", str(tmp_path / "usb-mode.state"))
    return tmp_path


def load():
    spec = importlib.util.spec_from_file_location("usb_tether_under_test", MODULE)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


class FakeProc:
    def __init__(self, rc=0, out="", err=""):
        self.returncode = rc
        self.stdout = out
        self.stderr = err


class Recorder:
    def __init__(self, table_present=True, nft_rc=0, routes="", addrs="", ruleset=""):
        self.calls = []
        self.table_present = table_present
        self.nft_rc = nft_rc
        self.routes = routes
        self.addrs = addrs
        self.ruleset = ruleset

    def __call__(self, argv, timeout=15, **kwargs):
        self.calls.append(list(argv))
        a = list(argv)
        if a[:4] == ["nft", "list", "table", "inet"]:
            return FakeProc(0 if self.table_present else 1, "table inet %s {}\n" % a[4])
        if a[:2] == ["nft", "list"]:
            return FakeProc(0, self.ruleset)
        if a[:3] == ["ip", "-4", "route"]:
            return FakeProc(0, self.routes)
        if a[:3] == ["ip", "-4", "-o"]:
            if "dev" in a:
                dev = a[a.index("dev") + 1]
                for line in self.addrs.splitlines():
                    if (" dev %s " % dev) in line + " ":
                        return FakeProc(0, line + "\n")
                return FakeProc(0, "")
            return FakeProc(0, self.addrs)
        if a[:2] == ["nft", "delete"]:
            self.table_present = False
            return FakeProc(0)
        return FakeProc(self.nft_rc if a[:3] == ["nft", "-f", "-"] else 0)

    def flat(self):
        return [" ".join(c) for c in self.calls]


def link_ready(monkeypatch, mod, iface="usb0"):
    monkeypatch.setattr(mod, "usb_link", lambda: {
        "active": True, "interface": iface, "mode": "usb_network",
        "phone_address": "10.15.19.1/24", "host_address": "10.15.19.2/24",
        "netdev_present": True})


def upstream_ok(monkeypatch, mod, name="wlan0", kind="wifi", tunnel=False):
    monkeypatch.setattr(mod, "choose_upstream", lambda req: {
        "interface": name, "kind": kind, "link": "up", "has_ipv4": True,
        "default_route": True, "vpn_tunnel": tunnel, "usable": True,
        "gateway": "192.168.178.1"})


def test_invalid_ifname_rejected():
    mod = load()
    for bad in ("", "../../etc", "wlan0;id", "a" * 20, "wlan 0"):
        assert mod.valid_ifname(bad) is False


def test_start_refuses_without_live_link(monkeypatch):
    mod = load()
    monkeypatch.setattr(mod, "usb_link", lambda: {"active": False, "interface": ""})
    r = mod.start("wlan0")
    assert r["success"] is False and r["error_code"] == "USB_NOT_ACTIVE"


def test_upstream_must_be_usable(monkeypatch):
    mod = load()
    link_ready(monkeypatch, mod)
    monkeypatch.setattr(mod, "upstream_candidates", lambda: [
        {"interface": "wlan0", "usable": False, "kind": "wifi", "link": "down",
         "has_ipv4": False, "default_route": False, "vpn_tunnel": False}])
    r = mod.start("wlan0")
    assert r["success"] is False and r["error_code"] == "UPSTREAM_UNAVAILABLE"


def test_vpn_killswitch_refuses_physical_upstream(monkeypatch):
    mod = load()
    link_ready(monkeypatch, mod)
    upstream_ok(monkeypatch, mod)
    monkeypatch.setattr(mod, "_vpn_armed", lambda: True)
    r = mod.start("wlan0")
    assert r["success"] is False and r["error_code"] == "VPN_CONFLICT"


def test_vpn_killswitch_allows_tunnel_upstream(monkeypatch):
    mod = load()
    link_ready(monkeypatch, mod)
    upstream_ok(monkeypatch, mod, name="tun0", kind="tunnel", tunnel=True)
    monkeypatch.setattr(mod, "_vpn_armed", lambda: True)
    assert mod.vpn_conflict({"interface": "tun0", "vpn_tunnel": True}) is None


def test_rules_are_scoped_to_exact_address_and_owned_table(monkeypatch, monkeypatch_env):
    mod = load()
    link_ready(monkeypatch, mod)
    upstream_ok(monkeypatch, mod)
    monkeypatch.setattr(mod, "_vpn_armed", lambda: False)
    rec = Recorder(table_present=False)
    monkeypatch.setattr(mod, "_run", rec)
    captured = {}

    def fake_script(script):
        captured["script"] = script
        rec.table_present = True
        return FakeProc(0)

    monkeypatch.setattr(mod, "_run_nft_script", fake_script)
    monkeypatch.setattr(mod, "_ip_forward", lambda: "1")
    r = mod.start("wlan0")
    assert r["success"] is True, r
    script = captured["script"]
    assert "inet nuxel_usb_tether" in script
    # Exact source address, not a CIDR broadcast that would NAT the whole subnet.
    assert 'ip saddr 10.15.19.1' in script
    assert 'iifname "usb0" oifname "wlan0"' in script
    assert 'oifname "wlan0" ip saddr 10.15.19.1 masquerade' in script
    assert "flush" not in script
    assert "nuxel_console_guard" not in script
    assert "nuxel_app_firewall" not in script
    assert 'iifname "usb0" accept' not in script
    assert "priority -50" in script
    # A configured share is not verified Internet.
    assert r["internet_verified"] is False
    assert r["state"] == "on-unverified"


def test_stop_restores_forwarding_and_removes_only_own_table(monkeypatch, monkeypatch_env):
    mod = load()
    monkeypatch.setenv("NUXEL_USB_TETHER_STATE", str(monkeypatch_env / "t.json"))
    (monkeypatch_env / "t.json").write_text(
        '{"enabled": true, "upstream": "wlan0", "prev_ip_forward": "0"}')
    rec = Recorder()
    monkeypatch.setattr(mod, "_run", rec)
    monkeypatch.setattr(mod, "usb_link", lambda: {"active": False, "interface": ""})
    # v0.8.5: forwarding is now shared with the Wi-Fi hotspot, so stopping the
    # tether must NOT write back the stale "previous" value captured at start.
    # Only a stop with nothing else needing routing may disable ip_forward.
    monkeypatch.setattr(mod, "_ip_forward", lambda: "1")
    monkeypatch.setattr(mod, "_ip_forward_needed_elsewhere", lambda: True)
    mod.stop()
    flat = rec.flat()
    assert "nft delete table inet nuxel_usb_tether" in flat
    assert not any(c.startswith("sysctl -qw net.ipv4.ip_forward=") for c in flat)
    assert not any("flush" in c for c in flat)
    assert not any("console_guard" in c for c in flat)
    # With nothing else needing it, forwarding is turned off again.
    rec2 = Recorder()
    monkeypatch.setattr(mod, "_run", rec2)
    monkeypatch.setattr(mod, "_ip_forward_needed_elsewhere", lambda: False)
    mod.stop()
    flat2 = rec2.flat()
    assert any(c.startswith("sysctl -qw net.ipv4.ip_forward=0") for c in flat2)


def test_status_off_is_honest(monkeypatch, monkeypatch_env):
    mod = load()
    rec = Recorder()
    monkeypatch.setattr(mod, "_run", rec)
    monkeypatch.setattr(mod, "usb_link", lambda: {"active": True, "interface": "usb0"})
    st = mod.status()
    assert st["enabled"] is False and st["state"] == "off"
    assert st["internet_verified"] is False


def test_host_report_requires_phone_address_and_sets_verified(monkeypatch, monkeypatch_env):
    mod = load()
    link_ready(monkeypatch, mod)
    rec = Recorder(table_present=True)
    monkeypatch.setattr(mod, "_run", rec)
    monkeypatch.setenv("NUXEL_USB_TETHER_STATE", str(monkeypatch_env / "s.json"))
    (monkeypatch_env / "s.json").write_text(
        '{"enabled": true, "upstream": "wlan0", "source_address": "10.15.19.1"}')
    bad = mod.host_report({"host_address": "10.15.19.2", "checked_phone": "10.15.19.9",
                           "internet_ok": True})
    assert bad["success"] is False and bad["error_code"] == "EVIDENCE_TARGET_MISMATCH"
    good = mod.host_report({"host_address": "10.15.19.2", "checked_phone": "10.15.19.1",
                            "internet_ok": True, "ping_ok": True})
    assert good["success"] is True
    assert good["state"] == "on"
    assert good["internet_verified"] is True


def test_stale_host_evidence_is_not_verified(monkeypatch, monkeypatch_env):
    mod = load()
    link_ready(monkeypatch, mod)
    rec = Recorder(table_present=True)
    monkeypatch.setattr(mod, "_run", rec)
    monkeypatch.setenv("NUXEL_USB_TETHER_STATE", str(monkeypatch_env / "s.json"))
    (monkeypatch_env / "s.json").write_text(
        '{"enabled": true, "upstream": "wlan0", "source_address": "10.15.19.1"}')
    monkeypatch.setenv("NUXEL_USB_HOST_EVIDENCE", str(monkeypatch_env / "e.json"))
    (monkeypatch_env / "e.json").write_text(
        '{"verified": true, "age_seconds": 999, "checked_phone": "10.15.19.1"}')
    st = mod.status()
    assert st["internet_verified"] is False
    assert st["state"] == "on-unverified"
