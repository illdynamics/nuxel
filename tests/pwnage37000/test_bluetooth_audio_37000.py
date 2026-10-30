"""PWNAGE-37000 Bluetooth manager + audio route offline regressions.

These tests pin the contract that the Settings Bluetooth page can actually
enumerate/scan/pair/connect devices through the root bridge, and that the ABOX
audio route script targets the real beyond-madera control names (the previous
script probed non-existent controls and therefore aborted before routing).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "services" / "nuxel-bridge" / "src"))

from hw_providers import BluetoothManagerProvider  # noqa: E402


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


# ── Bluetooth manager provider parsing ─────────────────────────────────────
def test_bt_devices_parsing_from_bluetoothctl_output():
    out = """Device C8:C8:3F:85:82:02 C8-C8-3F-85-82-02
\tPaired: no
\tTrusted: no
\tConnected: yes
\tIcon: audio-headset
Device 1F:6F:46:62:20:78 1F-6F-46-62-20-78
"""
    devices = BluetoothManagerProvider()._devices_from_stdout(out)
    assert len(devices) == 2
    by_mac = {d["mac"]: d for d in devices}
    assert by_mac["C8:C8:3F:85:82:02"]["connected"] is True
    assert by_mac["C8:C8:3F:85:82:02"]["paired"] is False
    assert by_mac["C8:C8:3F:85:82:02"]["alias"] == "C8-C8-3F-85-82-02"


@pytest.mark.parametrize("mac", [
    "C8:C8:3F:85:82:02", "aa:bb:cc:dd:ee:ff", "AA:BB:CC:DD:EE:FF",
])
def test_bt_mac_validation_accepts_valid(mac):
    assert BluetoothManagerProvider._validate_mac(mac) == mac.upper()


@pytest.mark.parametrize("mac", ["", "nope", "C8:C8:3F:85:82", "GG:00:11:22:33:44"])
def test_bt_mac_validation_rejects_invalid(mac):
    assert BluetoothManagerProvider._validate_mac(mac) is None


# ── Bridge wiring and capability seed ──────────────────────────────────────
def test_settings_app_declares_bluetooth_connect():
    app = json.loads(_read(ROOT / "pwa" / "nuxel-apps" / "settings" / "app.json"))
    assert "bluetooth:connect" in app["capabilities"]
    assert "bluetooth:scan" in app["capabilities"]


def test_settings_permission_seed_includes_bluetooth_connect():
    seed = json.loads(_read(ROOT / "configs" / "nuxel" / "permissions" / "nuxel-settings.json"))
    assert "bluetooth:connect" in seed
    assert seed["bluetooth:connect"]["duration"] == "always"


def test_api_handles_bluetooth_manager_verbs_in_root_bridge():
    api = _read(ROOT / "services" / "nuxel-bridge" / "src" / "api.py")
    for verb in ("list-devices", "scan", "pair", "connect", "disconnect",
                 "trust", "remove", "info"):
        assert f"'bluetooth' and verb in" in api
        assert f"'{verb}'" in api
    assert "BluetoothManagerProvider" in _read(
        ROOT / "services" / "nuxel-bridge" / "src" / "hw_providers.py")


def test_bridge_js_never_mocks_bluetooth_manager():
    js = _read(ROOT / "pwa" / "nuxel-common" / "bridge.js")
    for key in ("bluetooth.list-devices", "bluetooth.scan", "bluetooth.pair",
                "bluetooth.connect"):
        assert key in js


# ── Audio route script targets real controls ───────────────────────────────
def test_audio_route_uses_real_control_names():
    script = _read(ROOT / "services" / "nuxel-s10" / "bin" / "nuxel-audio-route.sh")
    for good in ("Left AMP Enable Switch", "Right AMP Enable Switch",
                 "ABOX SPUS IN1", "ABOX SPUS OUT1", "ABOX SIFS1",
                 "ABOX UAIF1 SPK", "ABOX SIFS1 OUT Switch", "ABOX UAIF1 Switch"):
        assert good in script
    # PWNAGE-40000: ABOX RDMA1_EN DOES exist (numid=1031, enum Off/On) on the
    # live beyond-madera card.  With it Off, hw_ptr advances but ABOX clocks no
    # samples into SPUS.  Pin the mandatory gate by name; never by numid.
    assert "ABOX RDMA1_EN" in script
    assert "RDMA1 gate on" in script
    assert "cset name='ABOX RDMA0_EN'" not in script
    assert "Left AMP Enable Switch' on" in script
    assert "'ABOX UAIF1 SPK' 2" in script
    assert "'ABOX RDMA1_EN' 1" in script


def test_audio_route_service_keeps_bounded_timeout():
    unit = _read(ROOT / "services" / "nuxel-s10" / "systemd" / "nuxel-audio-route.service")
    # Bounded, but long enough for the verified ABOX cold-boot PM cycle.
    assert "TimeoutStartSec=45" in unit
    assert "Restart=no" in unit
    assert "After=sound.target\n" in unit


# ── GNSS power-rail probe wiring ───────────────────────────────────────────
def test_api_handles_gnss_probe_in_root_bridge():
    api = _read(ROOT / "services" / "nuxel-bridge" / "src" / "api.py")
    assert "'location' and verb in ('gnss-probe', 'gnss-power')" in api
    assert "GnssProvider" in api
    hw = _read(ROOT / "services" / "nuxel-bridge" / "src" / "hw_providers.py")
    assert "class GnssProvider" in hw
    assert "sample_nmea" in hw and "power_rail" in hw


def test_bridge_js_never_mocks_gnss_probe():
    js = _read(ROOT / "pwa" / "nuxel-common" / "bridge.js")
    assert "location.gnss-probe" in js
    assert "location.gnss-power" in js
