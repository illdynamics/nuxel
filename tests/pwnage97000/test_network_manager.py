"""Focused tests for the Nuxel Network Manager wrapper provider."""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = ROOT / "services/nuxel-bridge/src/network_manager.py"
spec = importlib.util.spec_from_file_location("nuxel_network_manager", MODULE_PATH)
nm = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = nm
assert spec.loader is not None
spec.loader.exec_module(nm)


def test_terse_parser_handles_escaped_colons():
    assert nm.split_nmcli_terse(r"uuid:name:802-11-wireless:wlan0") == [
        "uuid", "name", "802-11-wireless", "wlan0"]
    assert nm.split_nmcli_terse(r"uuid:my\:wifi:wireguard:--") == [
        "uuid", "my:wifi", "wireguard", "--"]


def test_zerotier_ids_are_strict():
    assert nm.valid_zerotier_id("0cccb752f72ecf52")
    assert nm.valid_zerotier_id("0CCCB752F72ECF52")
    for bad in ("", "0cccb752f72ecf5", "0cccb752f72ecf522",
                "zzccb752f72ecf52", "../0cccb752f72ecf52"):
        assert not nm.valid_zerotier_id(bad)


def test_dns_provider_and_custom_validation():
    key, v4, v6 = nm.dns_servers_for("cloudflare")
    assert key == "cloudflare" and "1.1.1.1" in v4 and v6
    key, v4, v6 = nm.dns_servers_for("custom", "9.9.9.9, 2620:fe::fe")
    assert key == "custom" and v4 == ["9.9.9.9"] and v6 == ["2620:fe::fe"]
    with pytest.raises(nm.NetworkManagerError):
        nm.dns_servers_for("custom", ["not-an-ip"])
    with pytest.raises(nm.NetworkManagerError):
        nm.dns_servers_for("custom", [])
    with pytest.raises(nm.NetworkManagerError):
        nm.dns_servers_for("hostile")


def test_vpn_config_validation_is_truthful():
    wg = "[Interface]\nPrivateKey = x\nAddress = 10.0.0.2/24\n"
    assert nm.validate_vpn_config("wireguard", wg) == wg
    ovpn = "client\ndev tun\nremote vpn.example 1194\n"
    assert nm.validate_vpn_config("openvpn", ovpn) == ovpn
    with pytest.raises(nm.NetworkManagerError):
        nm.validate_vpn_config("wireguard", "PrivateKey = x")
    with pytest.raises(nm.NetworkManagerError):
        nm.validate_vpn_config("openvpn", "client\n")
    with pytest.raises(nm.NetworkManagerError):
        nm.validate_vpn_config("ipsec", ovpn)
    with pytest.raises(nm.NetworkManagerError):
        nm.validate_vpn_config("wireguard", wg + "\x00")


def test_unknown_verb_is_rejected_without_running_anything():
    with pytest.raises(nm.NetworkManagerError) as exc:
        nm.handle("shell", {"command": "id"})
    assert exc.value.code == "UNKNOWN_VERB"


def test_no_shell_true_or_host_filesystem_flags_in_provider():
    src = MODULE_PATH.read_text()
    assert "shell=True" not in src
    assert "os.system" not in src
    for forbidden in ("--filesystem=host", "--device=all", "--no-sandbox"):
        assert forbidden not in src
