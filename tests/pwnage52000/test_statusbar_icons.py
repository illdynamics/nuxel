import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_shared_icon_registry_and_config_agree():
    js = (ROOT / 'pwa/nuxel-common/statusbar-icons.js').read_text()
    doc = json.loads((ROOT / 'configs/nuxel/display/statusbar-icons.json').read_text())
    for icon in ('time', 'signal', 'wifi', 'location', 'bluetooth', 'nfc',
                 'sound', 'usb', 'remote', 'battery', 'battery_pct'):
        assert f"id: '{icon}'" in js, icon
        assert icon in doc['icons'], icon


def test_preferences_are_ui_only_and_separate_from_safezones():
    js = (ROOT / 'pwa/nuxel-common/statusbar-icons.js').read_text()
    assert 'statusbar-icons' in js
    assert "CFG_NAME = 'statusbar-icons'" in js
    assert "CFG_NAME = 'statusbar-safezones'" not in js
    assert 'configSet' in js


def test_host_exposes_user_writable_icon_document():
    host = (ROOT / 'tools/s10plus/a45/nuxel-pwa-host.c').read_text()
    assert '{ "statusbar-icons",     "/etc/nuxel/display/statusbar-icons.json",     1 }' in host


def test_wifi_hides_when_radio_is_off_and_bluetooth_requires_power():
    js = (ROOT / 'pwa/nuxel-home/js/status-bar.js').read_text()
    assert 'wifiRadioOn' in js
    assert "knownOff = radioOn === false" in js
    assert "const visible = radioOn === true && !knownOff" in js
    assert "const visible = this.state.bluetoothOn === true" in js
    assert "_setProviderVisible(this.elements.wifi, visible)" in js
    assert "_setProviderVisible(this.elements.bluetooth, visible)" in js


def test_every_icon_is_individually_configurable_in_settings():
    html = (ROOT / 'pwa/nuxel-apps/settings/index.html').read_text()
    js = (ROOT / 'pwa/nuxel-apps/settings/settings.js').read_text()
    assert 'statusbar-icon-list' in html
    assert 'statusbar-icons-save' in html
    assert 'statusbar-icons-defaults' in html
    assert 'api.DEFS.forEach' in js
