"""PWNAGE-41000 Wi-Fi boot-radio regression tests.

PWNAGE-37000 made the boot unit preserve a disabled radio.  PWNAGE-41000
supersedes that policy: every normal boot must enable the Wi-Fi radio through
NetworkManager and verify the readback.  Manual OFF remains respected for the
current session, and NetworkManager remains the single radio/connection owner.
"""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HELPER = ROOT / "services" / "nuxel-s10" / "bin" / "nuxel-wifi-up.sh"
APPLY = ROOT / "services" / "nuxel-s10" / "bin" / "nuxel-apply-pwnage36000.sh"
UNIT = ROOT / "services" / "nuxel-s10" / "systemd" / "nuxel-wifi.service"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _active_lines(script: str) -> list[str]:
    return [line.strip() for line in script.splitlines()
            if line.strip() and not line.lstrip().startswith("#")]


def test_wifi_up_enables_radio_at_boot():
    script = _read(HELPER)
    active = _active_lines(script)
    assert any(line.startswith("nmcli radio wifi on") for line in active)
    assert "nmcli -t -f WIFI radio" in script
    # The boot default must be verified by reading NetworkManager back, never
    # assumed from the set command's exit status.
    assert "Wi-Fi radio verification failed" in script


def test_wifi_up_handles_networkmanager_not_yet_ready():
    script = _read(HELPER)
    assert "while [ \"$i\" -lt 30 ]" in script
    assert "nmcli unavailable; leaving Wi-Fi unchanged" in script


def test_wifi_up_never_blocks_rfkill_or_starts_a_second_manager():
    active = _active_lines(_read(HELPER))
    assert any(line.startswith("rfkill unblock wifi") for line in active)
    assert not any(line.startswith("rfkill block") for line in active)
    assert "hard blocked" not in "\n".join(active)
    assert not any("wpa_supplicant" in line for line in active)
    assert not any(line.startswith("systemctl restart NetworkManager") for line in active)


def test_wifi_up_does_not_select_or_reconnect_a_profile():
    active = _active_lines(_read(HELPER))
    assert not any(line.startswith("nmcli connection up") for line in active)
    assert "nmcli connection modify" not in "\n".join(active)
    assert "connection.autoconnect yes" not in "\n".join(active)


def test_wifi_up_discovers_actual_wifi_device_instead_of_assuming_wlan0():
    script = _read(HELPER)
    assert "$2==\"wifi\"" in script
    assert "further assumption" not in script
    assert "[ \"$wifi_dev\" = \"wlan0\" ]" not in script
    assert "awk -F: -v d=\"$wifi_dev\"" in script


def test_apply_script_policy_is_default_on_without_profile_rewrites():
    script = _read(APPLY)
    assert "PWNAGE-41000" in script
    assert "Wi-Fi is ON by default" in script
    assert "connection.autoconnect yes" not in script
    # The installer may enable services, but never rewrites the radio state or
    # saved profiles itself.
    assert "nmcli radio wifi on" not in script


def test_wifi_unit_describes_boot_default_on():
    unit = _read(UNIT)
    assert "radio ON by default" in unit
    assert "WantedBy=multi-user.target" in unit
    assert "ExecStart=/usr/lib/nuxel/nuxel-wifi-up.sh" in unit

def test_quick_settings_never_maps_missing_radio_to_false():
    qs = _read(ROOT / "pwa" / "nuxel-home" / "js" / "qs.js")
    assert "wifi: null" in qs
    assert "static wifiRadioState(network)" in qs
    assert "CHECKING/UNKNOWN" in qs
    assert "Boolean(net.wifi_enabled)" not in qs
    # Radio and link are separate UI facts: an enabled radio with no link is
    # still ON.
    assert "wifiLinkState" in qs
    assert "data-radio-enabled" not in qs


def test_quick_settings_bridge_fallback_keeps_network_unknown():
    bridge = _read(ROOT / "pwa" / "nuxel-home" / "js" / "bridge.js")
    assert "network: {}," in bridge
    assert "network: { connected: false }" not in bridge

def test_software_rfkill_is_cleared_before_radio_enable():
    script = _read(HELPER)
    unblock = script.index("rfkill unblock wifi")
    enable = script.index("nmcli radio wifi on")
    assert unblock < enable
    assert script.count("Soft blocked: yes") >= 2
