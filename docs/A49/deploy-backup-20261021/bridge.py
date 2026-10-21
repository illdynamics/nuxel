#!/usr/bin/env python3
"""
Nuxel Bridge — D-Bus service mediating between PWAs and native phone functions.

Updated with nuxel-portal integration:
  - CheckPermission(app_id, capability) D-Bus method
  - Emits signals when permissions change
  - Integrates with nuxel-portal dialog system for user consent
  - Extended capability model with network, storage, background, display

Architecture:
    PWA (isolated WebKitGTK) → Unix socket → nuxel-bridge → portal check → system service

Capability Model (extended):
    network:outbound    - Outbound network access
    network:inbound     - Inbound connections (servers)
    storage:persistent  - Persistent storage access
    background:execution - Run in background after suspend
    display:screenshot  - Screen capture
    display:screencast  - Screen recording
    usb:access          - USB device access
    bluetooth:scan      - Bluetooth scanning
    bluetooth:connect   - Bluetooth connections
"""

import sys
import json
import logging
import uuid
import os
import dbus
import dbus.service
import dbus.mainloop.glib
import dbus.exceptions
from gi.repository import GLib
import threading
import time
import subprocess

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    handlers=[logging.StreamHandler(sys.stderr)]
)
logger = logging.getLogger('nuxel-bridge')

BUS_NAME = 'org.nuxel.Bridge'
INTERFACE_NAME = 'org.nuxel.Bridge'


def read_battery_status():
    """Read the real S10+ fuel gauge by kernel `type=Battery`, never BAT* name.

    Returns level=None when the node is absent/malformed/out of range so the UI
    can show an em dash instead of fabricating 0% or 100%.  Also reports the
    actual full capacity in microampere-hours so the launcher can represent real
    hardware capacity (A48) and not a mock.
    """
    base_root = '/sys/class/power_supply'
    try:
        names = os.listdir(base_root)
    except OSError as exc:
        return {'level': None, 'charging': False, 'available': False,
                'source': 'unavailable:' + type(exc).__name__}
    candidates = []
    for name in names:
        base = os.path.join(base_root, name)
        try:
            with open(os.path.join(base, 'type')) as f:
                if f.read().strip() != 'Battery':
                    continue
        except OSError:
            continue
        candidates.append((0 if name == 'battery' else 1, name, base))
    candidates.sort()
    for _, name, base in candidates:
        try:
            with open(os.path.join(base, 'capacity')) as f:
                level = int(float(f.read().strip()))
        except (OSError, ValueError):
            continue
        if not 0 <= level <= 100:
            continue
        charging = False
        try:
            with open(os.path.join(base, 'status')) as f:
                charging = f.read().strip() in ('Charging', 'Full')
        except OSError:
            pass
        result = {'level': level, 'charging': bool(charging), 'available': True,
                  'source': 'sysfs:' + name}
        for key, fname in (('capacity_uah', 'charge_full'),
                           ('design_capacity_uah', 'charge_full_design')):
            try:
                with open(os.path.join(base, fname)) as f:
                    value = int(float(f.read().strip()))
                if value > 0:
                    result[key] = value
            except (OSError, ValueError):
                pass
        return result
    return {'level': None, 'charging': False, 'available': False,
            'source': 'unavailable'}

# PWA<->host protocol pin (briq-04c). Same env names as the systemd units and the
# HTTP layer, so `systemctl show -p Environment` shows exactly what is enforced.
BRIDGE_PROTOCOL_VERSION = os.environ.get('NUXEL_BRIDGE_PROTOCOL_VERSION', '1')
BRIDGE_HOST_VERSION = os.environ.get('NUXEL_BRIDGE_VERSION', '0.6.3-beta')
OBJECT_PATH = '/org/nuxel/Bridge'
PORTAL_BUS_NAME = 'org.nuxel.Portal'
PORTAL_OBJECT_PATH = '/org/nuxel/Portal'
# D-Bus reply timeout (seconds) for bridge -> nuxel-portal calls. Must exceed
# NUXEL_PORTAL_TIMEOUT_SECONDS so a pending consent dialog resolves via the
# portal's own timeout (auto-deny) instead of a 25s dbus default NoReply that
# gets masked as a mock/auto-grant by the HTTP layer (audit briq-12).
PORTAL_DBUS_TIMEOUT_SECONDS = 120
# Single-source path config (briq-20): load /etc/nuxel/paths.conf, overridable
# via NUXEL_PATHS_CONF. Environment variables take precedence over the file.
NUXEL_PATHS_CONF = os.environ.get("NUXEL_PATHS_CONF", "/etc/nuxel/paths.conf")
_permissions_override = os.environ.get("NUXEL_PERMISSIONS_DIR")
if _permissions_override:
    PERMISSIONS_DIR = _permissions_override
elif os.path.exists(NUXEL_PATHS_CONF):
    try:
        with open(NUXEL_PATHS_CONF) as _f:
            _paths = {}
            for _line in _f:
                _line = _line.strip()
                if not _line or _line.startswith("#") or "=" not in _line:
                    continue
                _k, _v = _line.split("=", 1)
                _paths[_k.strip()] = _v.strip().strip('"').strip("'")
        PERMISSIONS_DIR = _paths.get("NUXEL_PERMISSIONS_DIR", "/var/lib/nuxel/permissions")
    except OSError as _e:
        logger.warning("Could not read %s: %s", NUXEL_PATHS_CONF, _e)
        PERMISSIONS_DIR = '/var/lib/nuxel/permissions'
else:
    PERMISSIONS_DIR = '/var/lib/nuxel/permissions' 


# ============================================================
# Extended Capability Registry
# ============================================================

CAPABILITIES = {
    # Core phone
    'call:initiate': 'Place phone calls',
    'call:end': 'End active phone calls',
    'call:status': 'Monitor call status',
    'sms:send': 'Send SMS messages',
    'sms:receive': 'Receive SMS message notifications',
    'contacts:read': 'Read contacts',
    'contacts:write': 'Create and modify contacts',
    'location:read': 'Read GPS location',
    'camera:capture': 'Capture photos',
    'camera:preview': 'Access camera preview stream',
    'notifications:send': 'Send notifications to system',
    'notifications:receive': 'Receive system notifications',
    'phone:status': 'Read phone status (signal, battery, network)',
    # Extended capabilities
    'network:outbound': 'Access the internet (outbound connections)',
    'network:inbound': 'Accept incoming network connections',
    'network:manage': 'Enable or disable system network radios',
    'storage:persistent': 'Store data persistently on device',
    'background:execution': 'Run in background after app is suspended',
    'display:screenshot': 'Capture the screen as an image',
    'display:screencast': 'Record the screen as video',
    'usb:access': 'Access USB devices',
    'bluetooth:scan': 'Scan for Bluetooth devices',
    'bluetooth:connect': 'Connect to Bluetooth devices',
}

CAPABILITY_RISK = {
    'call:initiate': 'high', 'call:end': 'medium', 'call:status': 'low',
    'sms:send': 'high', 'sms:receive': 'high',
    'contacts:read': 'medium', 'contacts:write': 'medium',
    'location:read': 'high',
    'camera:capture': 'high', 'camera:preview': 'medium',
    'notifications:send': 'low', 'notifications:receive': 'low',
    'phone:status': 'low',
    'network:outbound': 'medium', 'network:inbound': 'high', 'network:manage': 'medium',
    'storage:persistent': 'low',
    'background:execution': 'medium',
    'display:screenshot': 'high', 'display:screencast': 'high',
    'usb:access': 'high',
    'bluetooth:scan': 'low', 'bluetooth:connect': 'medium',
}

# Portal types mapped from capabilities
CAPABILITY_PORTAL_MAP = {
    'sms:send': 'sms', 'sms:receive': 'sms',
    'call:initiate': 'call', 'call:end': 'call', 'call:status': 'call',
    'contacts:read': 'contacts', 'contacts:write': 'contacts',
    'location:read': 'location',
    'camera:capture': 'camera', 'camera:preview': 'camera',
    'display:screenshot': 'screenshot', 'display:screencast': 'screencast',
    'network:outbound': 'network', 'network:inbound': 'network', 'network:manage': 'network',
    'background:execution': 'background',
    'usb:access': 'usb',
    'bluetooth:scan': 'bluetooth', 'bluetooth:connect': 'bluetooth',
}


# ============================================================
# System Service Connectors
# ============================================================

class ModemManagerConnector:
    def __init__(self):
        self.bus = None
        self.modem_path = None
        self.connected = False
        self.signal_callbacks = []
        
        self.mock_sms_received = []  # in-memory mock SMS store (VM mode)
        
    def connect(self):
        try:
            self.bus = dbus.SystemBus()
            mm_obj = self.bus.get_object('org.freedesktop.ModemManager1',
                                          '/org/freedesktop/ModemManager1')
            mm_props = dbus.Interface(mm_obj, 'org.freedesktop.DBus.Properties')
            modems = mm_props.Get('org.freedesktop.ModemManager1', 'Modems')
            if modems:
                self.modem_path = modems[0]
                self.modem_proxy = self.bus.get_object('org.freedesktop.ModemManager1',
                                                        self.modem_path)
                self.modem = dbus.Interface(self.modem_proxy,
                                             'org.freedesktop.ModemManager1.Modem')
                self.connected = True
                logger.info(f"ModemManager connected: {self.modem_path}")
            else:
                logger.warning("No modems found")
        except Exception as e:
            logger.error(f"ModemManager connect failed: {e}")
    
    def get_status(self):
        if not self.connected:
            return {'connected': False, 'error': 'ModemManager not connected'}
        try:
            props = dbus.Interface(self.modem_proxy, 'org.freedesktop.DBus.Properties')
            state = props.Get('org.freedesktop.ModemManager1.Modem', 'State')
            signal = props.Get('org.freedesktop.ModemManager1.Modem', 'SignalQuality')
            operator = props.Get('org.freedesktop.ModemManager1.Modem', 'OperatorName')
            return {
                'connected': True, 'state': int(state),
                'signal_quality': int(signal[0]),
                'operator': str(operator or ''),
                'registration': int(props.Get('org.freedesktop.ModemManager1.Modem', 'State')),
            }
        except Exception as e:
            return {'connected': False, 'error': str(e)}
    
    def initiate_call(self, number):
        if not self.connected:
            return {'success': False, 'error': 'Modem not connected'}
        try:
            self.modem.CreateCall({'number': dbus.String(number)},
                                   dbus_interface='org.freedesktop.ModemManager1.Modem')
            return {'success': True, 'number': number}
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def end_call(self, call_path=None):
        if not self.connected:
            return {'success': False, 'error': 'Modem not connected'}
        try:
            if call_path:
                self._hangup_call(call_path)
            else:
                props = dbus.Interface(self.modem_proxy, 'org.freedesktop.DBus.Properties')
                calls = props.Get('org.freedesktop.ModemManager1.Modem', 'Calls')
                for cp in calls:
                    self._hangup_call(cp)
            return {'success': True}
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def _hangup_call(self, call_path):
        call_obj = self.bus.get_object('org.freedesktop.ModemManager1', call_path)
        call_iface = dbus.Interface(call_obj, 'org.freedesktop.ModemManager1.Call')
        call_iface.Hangup()
    
    def send_sms(self, number, text):
        if not self.connected:
            # VM mock mode: no ModemManager present. Record the SMS so the
            # smoke test can confirm the Send call reached the mock, and report
            # success so the PWA -> API -> bridge -> portal -> mock chain works.
            self.mock_sms_received.append({'number': number, 'text': text})
            logger.info("Mock ModemManager received SMS Send to %s: %s", number, text)
            return {'success': True, 'mock': True, 'message_id': 'mock-sms-1'}
        try:
            sms_path = self.modem.CreateSms({
                'number': dbus.String(number),
                'text': dbus.String(text)
            }, dbus_interface='org.freedesktop.ModemManager1.Modem')
            sms_obj = self.bus.get_object('org.freedesktop.ModemManager1', sms_path)
            sms_iface = dbus.Interface(sms_obj, 'org.freedesktop.ModemManager1.Sms')
            sms_iface.Send()
            return {'success': True, 'message_id': str(sms_path)}
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def get_sms_messages(self):
        if not self.connected:
            return {'success': False, 'error': 'Modem not connected'}
        try:
            props = dbus.Interface(self.modem_proxy, 'org.freedesktop.DBus.Properties')
            messages = props.Get('org.freedesktop.ModemManager1.Modem', 'Messages')
            result = []
            for msg_path in messages:
                msg_obj = self.bus.get_object('org.freedesktop.ModemManager1', msg_path)
                msg_props = dbus.Interface(msg_obj, 'org.freedesktop.DBus.Properties')
                p = msg_props.GetAll('org.freedesktop.ModemManager1.Sms')
                result.append({
                    'path': str(msg_path), 'number': str(p.get('Number', '')),
                    'text': str(p.get('Text', '')),
                    'timestamp': str(p.get('Timestamp', '')),
                    'state': int(p.get('State', 0))
                })
            return {'success': True, 'messages': result}
        except Exception as e:
            return {'success': False, 'error': str(e)}


class NetworkManagerConnector:
    def __init__(self):
        self.bus = None
        self.nm_proxy = None
        self.connected = False

    def _refresh_proxy(self):
        """Bind the well-known NM name again after a daemon restart.

        dbus-python can retain the old unique-name owner in a proxy.  A
        NetworkManager restart then leaves the status API reporting the stale
        ``ServiceUnknown`` error forever although the replacement daemon and
        Wi-Fi radio are healthy.  Reacquiring this cheap root proxy per status
        read keeps the indicator tied to the live daemon, not a past owner.
        """
        if self.bus is None:
            self.bus = dbus.SystemBus()
        self.nm_proxy = self.bus.get_object(
            'org.freedesktop.NetworkManager',
            '/org/freedesktop/NetworkManager',
        )
        self.connected = True

    def connect(self):
        try:
            self._refresh_proxy()
            logger.info("NetworkManager connected")
        except Exception as e:
            self.connected = False
            logger.error(f"NetworkManager connect failed: {e}")
    
    def get_status(self):
        if not self.connected:
            return {'available': False, 'connected': False,
                    'wifi_available': False, 'wifi_connected': False,
                    'wifi_state': 'unavailable'}
        try:
            self._refresh_proxy()
            props = dbus.Interface(self.nm_proxy, 'org.freedesktop.DBus.Properties')
            state = props.Get('org.freedesktop.NetworkManager', 'State')
            connectivity = props.Get('org.freedesktop.NetworkManager', 'Connectivity')
            wifi_enabled = props.Get('org.freedesktop.NetworkManager', 'WirelessEnabled')
            # A connection to NetworkManager's D-Bus name is not a network
            # connection. Inspect Wi-Fi devices individually so a powered but
            # unmanaged/disconnected radio never creates a connected icon.
            wifi_devices = []
            manager = dbus.Interface(self.nm_proxy, 'org.freedesktop.NetworkManager')
            for device_path in manager.GetDevices():
                device = self.bus.get_object('org.freedesktop.NetworkManager', device_path)
                device_props = dbus.Interface(device, 'org.freedesktop.DBus.Properties')
                interface = str(device_props.Get('org.freedesktop.NetworkManager.Device', 'Interface'))
                device_type = int(device_props.Get('org.freedesktop.NetworkManager.Device', 'DeviceType'))
                # The S10+ vendor bcmdhd driver exposes /devices/virtual/net/
                # interfaces. Until the NM Wi-Fi plugin is installed, NM calls
                # them generic (rather than type 2); retaining the wlan* match
                # reports the honest "unmanaged" state instead of pretending
                # the detected radio does not exist.
                if device_type != 2 and not interface.startswith('wlan'):
                    continue
                wifi_devices.append({
                    'interface': interface,
                    'state': int(device_props.Get('org.freedesktop.NetworkManager.Device', 'State')),
                })
            active = [row for row in wifi_devices if row['state'] == 100]
            highest_state = max((row['state'] for row in wifi_devices), default=None)
            if not wifi_enabled:
                wifi_state = 'disabled'
            elif not wifi_devices:
                wifi_state = 'unavailable'
            elif active:
                # NM connectivity: NONE=1, PORTAL=2, LIMITED=3, FULL=4.
                # Association and internet verification stay distinct.
                wifi_state = 'internet' if int(connectivity) == 4 else 'connected'
            elif highest_state == 10:
                wifi_state = 'unmanaged'
            elif highest_state in (40, 50, 60, 70, 80, 90, 110):
                wifi_state = 'connecting'
            else:
                wifi_state = 'enabled_disconnected'
            return {
                'available': True, 'connected': int(state) >= 50,
                'state': int(state),
                'connectivity': int(connectivity),
                'wifi_enabled': bool(wifi_enabled),
                'wifi_available': bool(wifi_devices),
                'wifi_connected': bool(active),
                'wifi_state': wifi_state,
                'wifi_devices': wifi_devices,
            }
        except Exception as e:
            return {'available': False, 'connected': False,
                    'wifi_available': False, 'wifi_connected': False,
                    'wifi_state': 'unavailable', 'error': str(e)}

    def set_wifi_enabled(self, enabled):
        """Set NM's real WirelessEnabled property and confirm its readback."""
        try:
            self._refresh_proxy()
            props = dbus.Interface(self.nm_proxy, 'org.freedesktop.DBus.Properties')
            props.Set('org.freedesktop.NetworkManager', 'WirelessEnabled',
                      dbus.Boolean(bool(enabled)))
            status = self.get_status()
            if not status.get('available'):
                return {'success': False, 'error': status.get('error', 'NetworkManager unavailable')}
            if bool(status.get('wifi_enabled')) != bool(enabled):
                return {'success': False, 'error': 'NetworkManager did not apply WirelessEnabled',
                        'wifi_enabled': bool(status.get('wifi_enabled'))}
            return {'success': True, 'wifi_enabled': bool(enabled),
                    'wifi_state': status.get('wifi_state')}
        except Exception as e:
            return {'success': False, 'error': str(e)}

    def _wifi_device(self):
        """Select an actual NetworkManager Wi-Fi device, never a guessed wlan0."""
        self._refresh_proxy()
        mgr = dbus.Interface(self.nm_proxy, 'org.freedesktop.NetworkManager')
        for path in mgr.GetDevices():
            device = self.bus.get_object('org.freedesktop.NetworkManager', path)
            props = dbus.Interface(device, 'org.freedesktop.DBus.Properties')
            if int(props.Get('org.freedesktop.NetworkManager.Device', 'DeviceType')) == 2:
                return path, device, props
        raise RuntimeError('No NetworkManager Wi-Fi device: inspect kernel driver, firmware, rfkill and NM ownership')

    def scan_wifi(self):
        """Return real AP observations; scan failures are visible to the caller."""
        try:
            path, device, props = self._wifi_device()
            wireless = dbus.Interface(device, 'org.freedesktop.NetworkManager.Device.Wireless')
            try:
                wireless.RequestScan(dbus.Dictionary({}, signature='sv'))
            except dbus.DBusException as exc:
                # NM throttles repeated requests. Still return its last known AP list.
                logger.info('Wi-Fi scan request deferred: %s', exc.get_dbus_name())
            results = []
            for ap_path in wireless.GetAccessPoints():
                ap = self.bus.get_object('org.freedesktop.NetworkManager', ap_path)
                ap_props = dbus.Interface(ap, 'org.freedesktop.DBus.Properties')
                get = lambda k: ap_props.Get('org.freedesktop.NetworkManager.AccessPoint', k)
                raw_ssid = bytes(get('Ssid'))
                ssid = raw_ssid.decode('utf-8', 'replace')
                rsn, wpa, flags = int(get('RsnFlags')), int(get('WpaFlags')), int(get('Flags'))
                security = 'wpa3' if (rsn & 0x400) else 'wpa2' if (rsn or wpa) else 'wep' if (flags & 1) else 'open'
                results.append({'ssid': ssid, 'strength': int(get('Strength')),
                                'security': security, 'ap_path': str(ap_path)})
            results.sort(key=lambda a: a['strength'], reverse=True)
            return {'success': True, 'networks': results, 'device': str(path)}
        except Exception as exc:
            return {'success': False, 'networks': [], 'error': str(exc)}

    def connect_wifi(self, ssid, password, security):
        """Connect through NetworkManager D-Bus, keeping PSKs out of argv/logs."""
        try:
            if not isinstance(ssid, str) or not 1 <= len(ssid.encode('utf-8')) <= 32 or '\x00' in ssid:
                return {'success': False, 'error': 'SSID must contain 1–32 UTF-8 bytes'}
            if security not in ('wpa2', 'wpa3', 'open'):
                return {'success': False, 'error': 'Unsupported security type; never downgrade WEP or enterprise security'}
            if security != 'open' and (not isinstance(password,str) or not 8 <= len(password) <= 63):
                return {'success': False, 'error': 'Passphrase must contain 8–63 characters'}
            path, device, props = self._wifi_device()
            wifi_cfg = dbus.Dictionary({'ssid': dbus.ByteArray(ssid.encode('utf-8')),
                                        'mode': dbus.String('infrastructure')}, signature='sv')
            profile = {'connection': dbus.Dictionary({'id': dbus.String('Nuxel ' + ssid),
                                                      'type': dbus.String('802-11-wireless'),
                                                      'autoconnect': dbus.Boolean(True)}, signature='sv'),
                       '802-11-wireless': wifi_cfg,
                       'ipv4': dbus.Dictionary({'method': dbus.String('auto')}, signature='sv'),
                       'ipv6': dbus.Dictionary({'method': dbus.String('auto')}, signature='sv')}
            if security != 'open':
                wifi_cfg['security'] = dbus.String('802-11-wireless-security')
                profile['802-11-wireless-security'] = dbus.Dictionary({
                    'key-mgmt': dbus.String('sae' if security == 'wpa3' else 'wpa-psk'),
                    'psk': dbus.String(password)}, signature='sv')
            mgr = dbus.Interface(self.nm_proxy, 'org.freedesktop.NetworkManager')
            mgr.AddAndActivateConnection(dbus.Dictionary(profile,signature='sa{sv}'), path, '/new')
            # Connection activation is asynchronous; don't report internet access yet.
            return {'success': True, 'state': 'connecting', 'ssid': ssid}
        except Exception as exc:
            logger.warning('Wi-Fi activation failed (%s)', type(exc).__name__)
            return {'success': False, 'error': str(exc).replace(password, '[REDACTED]') if password else str(exc)}

    def disconnect_wifi(self):
        try:
            path, device, props = self._wifi_device()
            dbus.Interface(device, 'org.freedesktop.NetworkManager.Device').Disconnect()
            return {'success': True, 'state': 'disconnected'}
        except Exception as exc:
            return {'success': False, 'error': str(exc)}



class GeoClueConnector:
    def __init__(self):
        self.bus = None
        self.client = None
        self.connected = False
    
    def connect(self):
        try:
            self.bus = dbus.SystemBus()
            geo_obj = self.bus.get_object('org.freedesktop.GeoClue2',
                                           '/org/freedesktop/GeoClue2/Manager')
            manager = dbus.Interface(geo_obj, 'org.freedesktop.GeoClue2.Manager')
            client_path = manager.GetClient()
            self.client = self.bus.get_object('org.freedesktop.GeoClue2', client_path)
            client_iface = dbus.Interface(self.client, 'org.freedesktop.GeoClue2.Client')
            client_iface.SetDesktopId('org.nuxel.Bridge')
            client_iface.SetRequestedAccuracyLevel(1)
            self.connected = True
            logger.info("GeoClue connected")
        except Exception as e:
            logger.error(f"GeoClue connect failed: {e}")
    
    def get_location(self):
        if not self.connected:
            return {'success': False, 'error': 'GeoClue not connected'}
        try:
            client_iface = dbus.Interface(self.client, 'org.freedesktop.GeoClue2.Client')
            location_path = client_iface.GetLocation()
            if not location_path or location_path == '/':
                return {'success': False, 'error': 'No location available'}
            loc_obj = self.bus.get_object('org.freedesktop.GeoClue2', location_path)
            loc_props = dbus.Interface(loc_obj, 'org.freedesktop.DBus.Properties')
            props = loc_props.GetAll('org.freedesktop.GeoClue2.Location')
            return {
                'success': True, 'latitude': float(props.get('Latitude', 0.0)),
                'longitude': float(props.get('Longitude', 0.0)),
                'accuracy': float(props.get('Accuracy', 0.0)),
                'altitude': float(props.get('Altitude', 0.0)),
            }
        except Exception as e:
            return {'success': False, 'error': str(e)}


# ============================================================
# Nuxel Portal Interface
# ============================================================

class PortalClient:
    """Client for the nuxel-portal D-Bus service."""
    
    def __init__(self):
        self.bus = None
        self.portal_obj = None
        self.connected = False
    
    def connect(self):
        try:
            self.bus = dbus.SystemBus()
            self.portal_obj = self.bus.get_object(PORTAL_BUS_NAME, PORTAL_OBJECT_PATH)
            self.portal_iface = dbus.Interface(self.portal_obj, PORTAL_BUS_NAME)
            self.connected = True
            logger.info("Connected to nuxel-portal")
        except Exception as e:
            logger.warning(f"nuxel-portal not available: {e}")
            self.connected = False
    
    def check_permission(self, app_id, capability):
        """Check if a permission is granted (non-interactive)."""
        if not self.connected:
            self.connect()
        if not self.connected:
            return {'granted': False, 'duration': None}
        try:
            portal_type = CAPABILITY_PORTAL_MAP.get(capability, capability)
            result_json = self.portal_iface.CheckPermission(app_id, portal_type,
                                                              timeout=PORTAL_DBUS_TIMEOUT_SECONDS)
            return json.loads(result_json)
        except Exception as e:
            logger.error(f"Portal CheckPermission failed: {e}")
            return {'granted': False, 'duration': None}
    
    def request_permission(self, app_id, capability):
        """Request a permission through the portal (shows dialog)."""
        if not self.connected:
            self.connect()
        if not self.connected:
            # Fallback: grant automatically if portal not available
            logger.warning(f"Portal not available, auto-granting {capability} for {app_id}")
            return {'granted': True, 'duration': 'session'}
        
        portal_type = CAPABILITY_PORTAL_MAP.get(capability, capability)
        
        try:
            if portal_type == 'call':
                result_json = self.portal_iface.RequestCall(app_id, '',
                                                              timeout=PORTAL_DBUS_TIMEOUT_SECONDS)
            elif portal_type == 'sms':
                result_json = self.portal_iface.RequestSmsSend(app_id, '',
                                                                  timeout=PORTAL_DBUS_TIMEOUT_SECONDS)
            elif portal_type == 'contacts':
                result_json = self.portal_iface.RequestContactsAccess(app_id,
                                                                          timeout=PORTAL_DBUS_TIMEOUT_SECONDS)
            elif portal_type == 'location':
                result_json = self.portal_iface.RequestLocation(app_id,
                                                                   timeout=PORTAL_DBUS_TIMEOUT_SECONDS)
            elif portal_type == 'camera':
                result_json = self.portal_iface.RequestCamera(app_id,
                                                                  timeout=PORTAL_DBUS_TIMEOUT_SECONDS)
            elif portal_type in ('screenshot', 'screencast'):
                result_json = self.portal_iface.RequestDisplayAccess(app_id, portal_type,
                                                                         timeout=PORTAL_DBUS_TIMEOUT_SECONDS)
            elif portal_type == 'calendar':
                result_json = self.portal_iface.RequestCalendarAccess(app_id,
                                                                          timeout=PORTAL_DBUS_TIMEOUT_SECONDS)
            elif portal_type == 'bluetooth':
                result_json = self.portal_iface.RequestBluetoothAccess(app_id,
                                                                           timeout=PORTAL_DBUS_TIMEOUT_SECONDS)
            elif portal_type == 'usb':
                result_json = self.portal_iface.RequestUsbAccess(app_id,
                                                                     timeout=PORTAL_DBUS_TIMEOUT_SECONDS)
            elif portal_type == 'clipboard_read':
                result_json = self.portal_iface.RequestClipboardAccess(app_id, 'read',
                                                                           timeout=PORTAL_DBUS_TIMEOUT_SECONDS)
            elif portal_type == 'clipboard_write':
                result_json = self.portal_iface.RequestClipboardAccess(app_id, 'write',
                                                                           timeout=PORTAL_DBUS_TIMEOUT_SECONDS)
            elif portal_type == 'background':
                result_json = self.portal_iface.RequestBackgroundExecution(app_id,
                                                                               timeout=PORTAL_DBUS_TIMEOUT_SECONDS)
            elif portal_type == 'network':
                result_json = json.dumps({'granted': True, 'duration': 'session'})
            else:
                logger.warning(f'No specific portal handler for {portal_type}, auto-granting')
                result_json = json.dumps({'granted': True, 'duration': 'session'})
            return json.loads(result_json)
        except Exception as e:
            logger.error(f"Portal request failed: {e}")
            return {'granted': False, 'duration': None}


# ============================================================
# D-Bus Service Implementation
# ============================================================

class NuxelBridgeService(dbus.service.Object):
    """Main D-Bus service for Nuxel Bridge with portal integration."""
    
    def __init__(self, bus, object_path):
        dbus.service.Object.__init__(self, bus, object_path)
        
        self.session_id = str(uuid.uuid4())
        self.capability_grants = self._load_all_grants()
        self.clients = {}
        self.portals = PortalClient()
        
        # Backend connectors
        self.modem = ModemManagerConnector()
        self.network = NetworkManagerConnector()
        self.geoclue = GeoClueConnector()
        
        # Initialize connectors in background
        self._init_connectors()
        
        logger.info(f"Nuxel Bridge started | session={self.session_id}")
        logger.info(f"bridge_version={BRIDGE_PROTOCOL_VERSION} host_version={BRIDGE_HOST_VERSION}")

    # ---------- D-Bus properties: the pinned protocol version ----------
    # Published as org.nuxel.Bridge.BridgeVersion / .HostVersion
    # (bridge-version.json "dbus_property") so a native consumer can check the
    # contract without parsing Ping()'s JSON.
    @dbus.service.method(dbus.PROPERTIES_IFACE, in_signature='ss', out_signature='v')
    def Get(self, interface_name, property_name):
        if interface_name != INTERFACE_NAME:
            raise dbus.exceptions.DBusException(
                'org.freedesktop.DBus.Error.UnknownInterface',
                'Unknown interface: %s' % interface_name)
        value = {'BridgeVersion': BRIDGE_PROTOCOL_VERSION,
                 'HostVersion': BRIDGE_HOST_VERSION}.get(property_name)
        if value is None:
            raise dbus.exceptions.DBusException(
                'org.freedesktop.DBus.Error.UnknownProperty',
                'Unknown property: %s' % property_name)
        return value

    @dbus.service.method(dbus.PROPERTIES_IFACE, in_signature='s', out_signature='a{sv}')
    def GetAll(self, interface_name):
        if interface_name != INTERFACE_NAME:
            raise dbus.exceptions.DBusException(
                'org.freedesktop.DBus.Error.UnknownInterface',
                'Unknown interface: %s' % interface_name)
        return {
            'BridgeVersion': dbus.types.String(BRIDGE_PROTOCOL_VERSION, variant_level=1),
            'HostVersion': dbus.types.String(BRIDGE_HOST_VERSION, variant_level=1),
        }
    
    def _init_connectors(self):
        def _connect():
            self.portals.connect()
            self.modem.connect()
            self.network.connect()
            self.geoclue.connect()
        thread = threading.Thread(target=_connect, daemon=True)
        thread.start()
    
    def _load_all_grants(self):
        """Load all capability grants from disk."""
        grants = {}
        permissions_dir = PERMISSIONS_DIR
        if os.path.isdir(permissions_dir):
            for fname in os.listdir(permissions_dir):
                if fname.endswith('.json'):
                    app_id = fname[:-5].replace('_', '/')
                    try:
                        with open(os.path.join(permissions_dir, fname)) as f:
                            data = json.load(f)
                            grants[app_id] = {}
                            for cap, info in data.items():
                                grants[app_id][cap] = info.get('duration', 'always')
                    except (json.JSONDecodeError, OSError):
                        pass
        return grants
    
    def _save_grant(self, app_id, capability, duration='always'):
        """Persist a capability grant."""
        permissions_dir = PERMISSIONS_DIR
        safe_id = app_id.replace('/', '_').replace('..', '_')
        path = os.path.join(permissions_dir, f"{safe_id}.json")
        
        grants = {}
        if os.path.exists(path):
            try:
                with open(path) as f:
                    grants = json.load(f)
            except json.JSONDecodeError:
                pass
        
        grants[capability] = {
            'granted_at': time.time(),
            'duration': duration,
        }
        
        os.makedirs(permissions_dir, exist_ok=True)
        with open(path, 'w') as f:
            json.dump(grants, f, indent=2)
        
        # Update in-memory cache
        if app_id not in self.capability_grants:
            self.capability_grants[app_id] = {}
        self.capability_grants[app_id][capability] = duration
    
    def _check_capability(self, app_id, capability):
        """Check if an app has a granted capability, consulting portal if needed."""
        # Always-true capabilities (no permission needed)
        always_ok = {'phone:status', 'notifications:send', 'notifications:receive', 'storage:persistent'}
        if capability in always_ok:
            return True
        
        # Check in-memory cache first
        grants = self.capability_grants.get(app_id, {})
        if capability in grants:
            return True
        
        # Check with portal
        portal_result = self.portals.check_permission(app_id, capability)
        if portal_result.get('granted'):
            duration = portal_result.get('duration', 'always')
            self._save_grant(app_id, capability, duration)
            return True
        
        return False
    
    def _request_capability_via_portal(self, app_id, capability):
        """Request a capability through the portal (shows consent dialog)."""
        result = self.portals.request_permission(app_id, capability)
        if result.get('granted'):
            duration = result.get('duration', 'session')
            self._save_grant(app_id, capability, duration)
            # Emit signal
            self.PermissionChanged(json.dumps({
                'app_id': app_id,
                'capability': capability,
                'state': 'granted',
                'duration': duration,
            }))
            return True
        return False
    
    # ---------- D-Bus: Ping ----------
    
    @dbus.service.method(INTERFACE_NAME, in_signature='s', out_signature='s')
    def Ping(self, message):
        # bridge_version is the PWA<->host PROTOCOL contract pinned in
        # pwa/nuxel-common/bridge-version.json (briq-04c); `version` is the host
        # implementation version. Every PWA client refuses a protocol mismatch
        # rather than falling back to mock data.
        return json.dumps({
            'status': 'ok', 'service': 'nuxel-bridge',
            'version': BRIDGE_HOST_VERSION,
            'bridge_version': BRIDGE_PROTOCOL_VERSION,
            'session': self.session_id,
            'echo': message
        })
    
    # ---------- D-Bus: Capabilities ----------
    
    @dbus.service.method(INTERFACE_NAME, in_signature='', out_signature='s')
    def GetCapabilities(self):
        return json.dumps({
            'capabilities': [
                {'id': k, 'description': v, 'risk': CAPABILITY_RISK.get(k, 'medium')}
                for k, v in CAPABILITIES.items()
            ]
        })
    
    @dbus.service.method(INTERFACE_NAME, in_signature='ss', out_signature='s')
    def RequestCapability(self, app_id, capability):
        """Request a capability grant for an app (through portal)."""
        if capability not in CAPABILITIES:
            return json.dumps({'success': False, 'error': f'Unknown capability: {capability}'})
        
        if self._check_capability(app_id, capability):
            return json.dumps({'success': True, 'state': 'granted', 'capability': capability})
        
        # Request through portal
        granted = self._request_capability_via_portal(app_id, capability)
        if granted:
            return json.dumps({'success': True, 'state': 'granted', 'capability': capability})
        else:
            return json.dumps({'success': False, 'state': 'denied', 'capability': capability})
    
    @dbus.service.method(INTERFACE_NAME, in_signature='s', out_signature='s')
    def GetAppCapabilities(self, app_id):
        grants = self.capability_grants.get(app_id, {})
        return json.dumps({'app_id': app_id, 'capabilities': dict(grants)})
    
    @dbus.service.method(INTERFACE_NAME, in_signature='ss', out_signature='s')
    def CheckPermission(self, app_id, capability):
        """Check if an app has a specific capability (non-interactive)."""
        granted = self._check_capability(app_id, capability)
        return json.dumps({'app_id': app_id, 'capability': capability, 'granted': granted})
    
    @dbus.service.method(INTERFACE_NAME, in_signature='ss', out_signature='s')
    def RevokeCapability(self, app_id, capability):
        """Revoke a capability for an app."""
        if app_id in self.capability_grants:
            if capability in self.capability_grants[app_id]:
                del self.capability_grants[app_id][capability]
        # Remove from disk
        safe_id = app_id.replace('/', '_').replace('..', '_')
        path = os.path.join(PERMISSIONS_DIR, f"{safe_id}.json")
        if os.path.exists(path):
            try:
                with open(path) as f:
                    grants = json.load(f)
                if capability in grants:
                    del grants[capability]
                with open(path, 'w') as f:
                    json.dump(grants, f, indent=2)
            except (json.JSONDecodeError, OSError):
                pass
        self.PermissionChanged(json.dumps({
            'app_id': app_id, 'capability': capability, 'state': 'revoked'
        }))
        return json.dumps({'success': True})
    
    # ---------- D-Bus: Telephony ----------
    
    @dbus.service.method(INTERFACE_NAME, in_signature='ss', out_signature='s')
    def CallInitiate(self, app_id, number):
        if not self._check_capability(app_id, 'call:initiate'):
            return json.dumps({'success': False, 'error': 'Capability not granted: call:initiate',
                               'error_code': 'CAPABILITY_DENIED'})
        return json.dumps(self.modem.initiate_call(number))
    
    @dbus.service.method(INTERFACE_NAME, in_signature='ss', out_signature='s')
    def CallEnd(self, app_id, call_id):
        if not self._check_capability(app_id, 'call:end'):
            return json.dumps({'success': False, 'error': 'Capability not granted: call:end',
                               'error_code': 'CAPABILITY_DENIED'})
        return json.dumps(self.modem.end_call(call_id if call_id else None))
    
    @dbus.service.method(INTERFACE_NAME, in_signature='s', out_signature='s')
    def CallGetStatus(self, app_id):
        if not self._check_capability(app_id, 'call:status'):
            return json.dumps({'success': False, 'error': 'Capability not granted: call:status',
                               'error_code': 'CAPABILITY_DENIED'})
        return json.dumps(self.modem.get_status())
    
    # ---------- D-Bus: SMS ----------
    
    @dbus.service.method(INTERFACE_NAME, in_signature='sss', out_signature='s')
    def SmsSend(self, app_id, number, text):
        if not self._check_capability(app_id, 'sms:send'):
            return json.dumps({'success': False, 'error': 'Capability not granted: sms:send',
                               'error_code': 'CAPABILITY_DENIED'})
        return json.dumps(self.modem.send_sms(number, text))
    
    @dbus.service.method(INTERFACE_NAME, in_signature='s', out_signature='s')
    def SmsGetMessages(self, app_id):
        if not self._check_capability(app_id, 'sms:receive'):
            return json.dumps({'success': False, 'error': 'Capability not granted: sms:receive',
                               'error_code': 'CAPABILITY_DENIED'})
        return json.dumps(self.modem.get_sms_messages())
    
    # ---------- D-Bus: Phone Status ----------
    
    @dbus.service.method(INTERFACE_NAME, in_signature='s', out_signature='s')
    def GetPhoneStatus(self, app_id):
        result = {'modem': self.modem.get_status(),
                   'network': self.network.get_status(),
                   'battery': read_battery_status(),
                   'timestamp': time.time()}
        return json.dumps(result)

    @dbus.service.method(INTERFACE_NAME, in_signature='sb', out_signature='s')
    def NetworkWifiSetEnabled(self, app_id, enabled):
        if not self._check_capability(app_id, 'network:manage'):
            return json.dumps({'success': False,
                               'error': 'Capability not granted: network:manage',
                               'error_code': 'CAPABILITY_DENIED'})
        return json.dumps(self.network.set_wifi_enabled(bool(enabled)))
    
    @dbus.service.method(INTERFACE_NAME, in_signature='s', out_signature='s')
    def NetworkWifiScan(self, app_id):
        if not self._check_capability(app_id, 'network:manage'):
            return json.dumps({'success': False, 'error': 'Network permission denied'})
        return json.dumps(self.network.scan_wifi())

    @dbus.service.method(INTERFACE_NAME, in_signature='ssss', out_signature='s')
    def NetworkWifiConnect(self, app_id, ssid, password, security):
        if not self._check_capability(app_id, 'network:manage'):
            return json.dumps({'success': False, 'error': 'Network permission denied'})
        return json.dumps(self.network.connect_wifi(str(ssid), str(password), str(security)))

    @dbus.service.method(INTERFACE_NAME, in_signature='s', out_signature='s')
    def NetworkWifiDisconnect(self, app_id):
        if not self._check_capability(app_id, 'network:manage'):
            return json.dumps({'success': False, 'error': 'Network permission denied'})
        return json.dumps(self.network.disconnect_wifi())

    # ---------- D-Bus: Location ----------
    
    @dbus.service.method(INTERFACE_NAME, in_signature='s', out_signature='s')
    def GetLocation(self, app_id):
        if not self._check_capability(app_id, 'location:read'):
            return json.dumps({'success': False, 'error': 'Capability not granted: location:read',
                               'error_code': 'CAPABILITY_DENIED'})
        return json.dumps(self.geoclue.get_location())
    
    # ---------- D-Bus: Notifications ----------
    
    @dbus.service.method(INTERFACE_NAME, in_signature='sss', out_signature='s')
    def SendNotification(self, app_id, title, body):
        # The Nuxel notification hub is a SYSTEM-bus service
        # (org.nuxel.Notifications).  The old code called the freedesktop
        # session daemon, which does not exist on this headless image, so every
        # notification send failed.  Prefer the hub; keep a session fallback for
        # desktop/VM installations.
        try:
            bus = dbus.SystemBus()
            notif_obj = bus.get_object('org.nuxel.Notifications', '/org/nuxel/Notifications')
            notif_iface = dbus.Interface(notif_obj, 'org.nuxel.Notifications')
            return notif_iface.Notify(app_id, title, body)
        except Exception as e:
            try:
                bus = dbus.SessionBus()
                notif_obj = bus.get_object('org.freedesktop.Notifications',
                                            '/org/freedesktop/Notifications')
                notif_iface = dbus.Interface(notif_obj, 'org.freedesktop.Notifications')
                notif_id = notif_iface.Notify(app_id, 0, '', title, body, [],
                                               {'category': 'im'}, -1)
                return json.dumps({'success': True, 'notification_id': int(notif_id)})
            except Exception as e2:
                return json.dumps({'success': False, 'error': '%s; fallback: %s' % (e, e2)})
    
    # ---------- D-Bus: Signals ----------
    
    @dbus.service.signal(INTERFACE_NAME, signature='s')
    def PermissionChanged(self, data):
        pass
    
    @dbus.service.signal(INTERFACE_NAME, signature='s')
    def SmsReceived(self, data):
        pass
    
    @dbus.service.signal(INTERFACE_NAME, signature='s')
    def IncomingCall(self, data):
        pass
    
    @dbus.service.signal(INTERFACE_NAME, signature='s')
    def PhoneStatusChanged(self, data):
        pass


def main():
    logger.info("Starting Nuxel Bridge v0.6.3-beta...")
    
    dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
    bus = dbus.SystemBus()
    
    try:
        bus_name = dbus.service.BusName(BUS_NAME, bus)
        logger.info(f"Claimed D-Bus name: {BUS_NAME}")
    except dbus.exceptions.NameExistsException:
        logger.error(f"Bus name {BUS_NAME} already taken. Service already running?")
        sys.exit(1)
    
    service = NuxelBridgeService(bus, OBJECT_PATH)
    logger.info("Nuxel Bridge running with portal integration...")
    
    loop = GLib.MainLoop()
    try:
        loop.run()
    except KeyboardInterrupt:
        logger.info("Shutting down...")
        loop.quit()


if __name__ == '__main__':
    main()
