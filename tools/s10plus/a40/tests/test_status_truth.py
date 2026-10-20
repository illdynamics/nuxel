#!/usr/bin/env python3
"""Contract checks: status bars must never invent cellular service."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
SOURCE = (ROOT / 'pwa/nuxel-home/js/status-bar.js').read_text()
BRIDGE = (ROOT / 'services/nuxel-bridge/src/bridge.py').read_text()
QS = (ROOT / 'pwa/nuxel-home/js/qs.js').read_text()
BRIDGE_UNIT = (ROOT / 'services/nuxel-bridge/systemd/nuxel-bridge.service').read_text()

def require(condition, description):
    if not condition:
        raise AssertionError(description)
    print('PASS', description)

require("signalLevel: 0" in SOURCE and "cellularState: 'unknown'" in SOURCE,
        'status bar begins with unknown cellular state, not fabricated bars')
require("const visible = state === 'registered';" in SOURCE and
        'this.elements.signal.hidden = !visible;' in SOURCE,
        'cellular icon is shown only for an explicit registered modem')
require("modem && modem.connected && !simAbsent" in SOURCE,
        'registered signal requires a positive modem report')
require("this.state.cellularState = 'no-sim';" in SOURCE and
        "this.state.cellularState = 'unavailable';" in SOURCE,
        'no-SIM and unavailable adapter states stay distinct')
require("status.network.signal" not in SOURCE and "Fallback to network signal" not in SOURCE,
        'generic network status cannot masquerade as cellular signal')
require('Math.max(1, Math.round' not in SOURCE,
        'zero reported signal does not become one fabricated bar')
require("manager.GetDevices()" in BRIDGE and "'wifi_state': wifi_state" in BRIDGE,
        'bridge derives Wi-Fi state from actual NetworkManager Wi-Fi devices')
require('def _refresh_proxy(self):' in BRIDGE and
        'self._refresh_proxy()' in BRIDGE,
        'bridge rebinds NetworkManager after a D-Bus service restart')
require("network.wifi_state" in SOURCE and "status.network.type === 'ethernet'" not in SOURCE,
        'Wi-Fi icon cannot inherit an ethernet or NetworkManager-service connection')
require("NetworkWifiSetEnabled" in BRIDGE and "WirelessEnabled" in BRIDGE,
        'bridge writes and verifies NetworkManager WirelessEnabled for Wi-Fi controls')
require("_setWifiEnabled" in QS and "network', 'wifi-enabled" in QS and
        "control is unavailable on this build" in QS,
        'Quick Settings Wi-Fi is backend-confirmed and other unintegrated tiles stay honest')
require("SupplementaryGroups=nuxel" in BRIDGE_UNIT,
        'bridge receives only group access to the shared portal permission store')
