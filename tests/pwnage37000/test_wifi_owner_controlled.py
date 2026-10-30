"""PWNAGE-37000 Wi-Fi boot policy regression tests.

The S10+ boot unit used to run `rfkill unblock wifi` and `nmcli radio wifi on`
unconditionally, which re-enabled a radio the owner had deliberately turned off.
The new policy leaves NetworkManager as the single owner of the radio: the
boot script only brings up a saved autoconnect profile when the radio is
already enabled and wlan0 is genuinely disconnected.
"""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_wifi_up_never_forces_radio_on():
    script = _read(ROOT / "services" / "nuxel-s10" / "bin" / "nuxel-wifi-up.sh")
    lines = [line.strip() for line in script.splitlines()]
    assert "rfkill unblock wifi" not in lines
    assert "nmcli radio wifi on" not in lines
    assert "nmcli -t -f WIFI radio" in script


def test_wifi_up_respects_disabled_radio():
    script = _read(ROOT / "services" / "nuxel-s10" / "bin" / "nuxel-wifi-up.sh")
    assert "disabled by owner" in script
    assert "leaving it off" in script


def test_wifi_up_does_not_rewrite_profile_autoconnect():
    script = _read(ROOT / "services" / "nuxel-s10" / "bin" / "nuxel-wifi-up.sh")
    assert "connection.autoconnect yes" not in script
    assert "nmcli connection modify" not in script
    lines = [line.strip() for line in script.splitlines()]
    assert "timeout 30 nmcli connection up" not in lines
    assert not any(line.startswith("nmcli connection up") for line in lines)


def test_wifi_up_does_not_try_to_pick_profile_manually():
    script = _read(ROOT / "services" / "nuxel-s10" / "bin" / "nuxel-wifi-up.sh")
    assert "nmcli connection show" not in script


def test_apply_script_never_forces_wifi():
    script = _read(ROOT / "services" / "nuxel-s10" / "bin" / "nuxel-apply-pwnage36000.sh")
    assert "rfkill unblock wifi" not in script
    assert "nmcli radio wifi on" not in script
    assert "connection.autoconnect yes" not in script


def test_wifi_unit_description_is_owner_controlled():
    unit = _read(ROOT / "services" / "nuxel-s10" / "systemd" / "nuxel-wifi.service")
    assert "owner-controlled" in unit
    assert "WantedBy=multi-user.target" in unit
