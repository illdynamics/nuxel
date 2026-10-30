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
import math
import uuid
import os
try:
    import dbus
    import dbus.service
    import dbus.mainloop.glib
    import dbus.exceptions
    from gi.repository import GLib
    HAVE_DBUS = True
except ImportError:
    dbus = None
    HAVE_DBUS = False
import threading
import time
import subprocess
import media_store

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
        status_val = 'unknown'
        try:
            with open(os.path.join(base, 'status')) as f:
                status_val = f.read().strip()
        except OSError:
            pass
        # 'Full' is a valid readable state, NOT a charging indicator: the S10+
        # reports "Full" once the charger holds the battery at 100%.  Showing the
        # charging glyph then is the exact "battery looks wrong after boot" bug.
        charging = (status_val == 'Charging')
        status_word = {'Charging': 'charging', 'Full': 'full',
                       'Discharging': 'discharging', 'Not charging': 'not-charging'}.get(
                           status_val, 'unknown')
        result = {'level': level, 'charging': bool(charging), 'available': True,
                  'status': status_word, 'source': 'sysfs:' + name}
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
BRIDGE_HOST_VERSION = os.environ.get('NUXEL_BRIDGE_VERSION', '0.2.1')
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

# File-backed camera/photo/video store (A52). Files, never browser localStorage.
MEDIA_DIR = os.environ.get('NUXEL_MEDIA_DIR', '/var/lib/nuxel/media')


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
    'bluetooth:manage': 'Enable or disable the Bluetooth radio',
    'location:manage': 'Enable or disable the system location policy',
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
    'bluetooth:manage': 'medium', 'location:manage': 'medium',
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
    'bluetooth:manage': 'bluetooth', 'location:manage': 'location',
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
    """NetworkManager connector with correct, stale-safe Wi-Fi AP activation.

    A51 fix: the previous revision hard-coded ``/new`` as the
    ``AddAndActivateConnection`` specific_object even though the scan already
    returned real AP D-Bus object paths.  ``/new`` is not an access point, so
    NetworkManager answered ``Device.SpecificObjectNotFound`` on every connect.
    This revision selects a *verified* AP object path from the current scan
    list on the *same* Wi-Fi device, re-uses existing saved profiles, and never
    fabricates an AP identity.
    """

    NM_BUS = 'org.freedesktop.NetworkManager'
    # A scan is advisory: NetworkManager may take substantially longer while a
    # vendor radio/firmware is recovering.  Never hold the shared bridge's
    # D-Bus handler at the default (effectively UI-visible) timeout; cached APs
    # are still useful and an unavailable radio must return an honest result.
    SCAN_REQUEST_TIMEOUT_SECONDS = 5
    NM_IFACE = 'org.freedesktop.NetworkManager'
    DEV_IFACE = 'org.freedesktop.NetworkManager.Device'
    WIRELESS_IFACE = 'org.freedesktop.NetworkManager.Device.Wireless'
    AP_IFACE = 'org.freedesktop.NetworkManager.AccessPoint'
    PROPS = 'org.freedesktop.DBus.Properties'
    SETTINGS_PATH = '/org/freedesktop/NetworkManager/Settings'
    SETTINGS_IFACE = 'org.freedesktop.NetworkManager.Settings'
    CONN_IFACE = 'org.freedesktop.NetworkManager.Settings.Connection'

    # NM_802_11_AP_FLAGS / security AKM bits (from libnm).
    AP_FLAG_PRIVACY = 0x1
    AP_SEC_KEY_MGMT_PSK = 0x8
    AP_SEC_KEY_MGMT_SAE = 0x400

    RETRY_SECONDS = float(os.environ.get('NUXEL_NM_RETRY', '5.0'))

    def __init__(self):
        self.bus = None
        self.nm_proxy = None
        self.connected = False
        self.last_error = None
        self.last_attempt = 0.0

    # ------------------------------------------------------------------ infra

    def _refresh_proxy(self):
        """Re-acquire the NM well-known name after a daemon restart."""
        if self.bus is None:
            self.bus = dbus.SystemBus()
        self.nm_proxy = self.bus.get_object(self.NM_BUS,
                                            '/org/freedesktop/NetworkManager')
        self.connected = True

    def connect(self, force=False):
        now = time.time()
        if self.connected:
            return True
        if not force and self.last_error and (now - self.last_attempt) < self.RETRY_SECONDS:
            return False
        self.last_attempt = now
        try:
            self._refresh_proxy()
            self.last_error = None
            logger.info("NetworkManager connected")
            return True
        except Exception as e:
            self.connected = False
            self.last_error = str(e)
            logger.error("NetworkManager connect failed: %s", e)
            return False

    @staticmethod
    def _security(rsn, wpa, flags):
        """Map RSN/WPA/flags to the UI's security vocabulary.

        The UI contract only knows wpa3/wpa2/wep/open.  SAE (WPA3) wins over
        legacy PSK; a WEP-only AP is reported as ``wep`` and refused on connect
        (never downgraded to a fake password).  Enterprise/EAP is not guessed.
        """
        if rsn & NetworkManagerConnector.AP_SEC_KEY_MGMT_SAE:
            return 'wpa3'
        if rsn or wpa:
            return 'wpa2'
        if flags & NetworkManagerConnector.AP_FLAG_PRIVACY:
            return 'wep'
        return 'open'

    @staticmethod
    def _display_ssid(raw):
        """Lossy-but-safe display form; never used as an identity key."""
        return bytes(raw).decode('utf-8', 'replace') if raw else ''

    @staticmethod
    def _ssid_bytes(ssid, ssid_hex):
        """Authoritative SSID bytes.  ``ssid_hex`` (from the scan) wins because
        it survives SSIDs that are not valid UTF-8; otherwise encode the
        display string.  Returns b'' on garbage."""
        if ssid_hex:
            try:
                raw = bytes.fromhex(str(ssid_hex))
                if 1 <= len(raw) <= 32:
                    return raw
            except (ValueError, TypeError):
                pass
        try:
            return ssid.encode('utf-8') if isinstance(ssid, str) else b''
        except Exception:
            return b''

    @staticmethod
    def _norm_mac(value):
        import re as _re
        return _re.sub(r'[^0-9a-fA-F]', '', value or '').lower()

    @staticmethod
    def _redact(text, secret):
        if secret and isinstance(text, str) and isinstance(secret, str):
            return text.replace(secret, '[REDACTED]')
        return text

    @staticmethod
    def _friendly_error(exc):
        name = ''
        msg = str(exc)
        try:
            name = exc.get_dbus_name()
        except Exception:
            pass
        if name:
            if 'SpecificObjectNotFound' in name:
                return 'The selected access point is no longer in the scan list; rescan and retry.'
            if 'NoSecrets' in name or 'Agent' in name or 'Secrets' in name:
                return 'Authentication failed or the stored secret is unavailable.'
            if 'PermissionDenied' in name or 'NotAuthorized' in name:
                return 'Permission denied for this NetworkManager operation.'
            if 'InvalidConnection' in name or 'InvalidProperty' in name:
                return 'The Wi-Fi profile was rejected by NetworkManager.'
        if '802-1x' in msg or '8021x' in msg or 'EAP' in msg:
            return 'Enterprise/EAP networks are not supported by the Settings connector.'
        if 'invalid' in msg.lower() and 'password' in msg.lower():
            return 'Authentication failed: the passphrase was rejected.'
        return msg

    # -------------------------------------------------------------- devices

    def _device(self, path):
        obj = self.bus.get_object(self.NM_BUS, path)
        return obj, dbus.Interface(obj, self.PROPS)

    def _device_type(self, path):
        _, props = self._device(path)
        try:
            return int(props.Get(self.DEV_IFACE, 'DeviceType'))
        except Exception:
            return None

    def _wifi_devices(self):
        """All type-2 (Wi-Fi) device object paths owned by NM, in NM order."""
        self._refresh_proxy()
        mgr = dbus.Interface(self.nm_proxy, self.NM_IFACE)
        out = []
        for path in mgr.GetDevices():
            if self._device_type(path) == 2:
                out.append(path)
        return out

    def _wifi_device(self):
        """Select an actual NM Wi-Fi device, never a guessed wlan0."""
        devices = self._wifi_devices()
        if not devices:
            raise RuntimeError('No NetworkManager Wi-Fi device: inspect kernel driver, firmware, rfkill and NM ownership')
        path = devices[0]
        obj, props = self._device(path)
        return path, obj, props

    def _select_device(self, device_hint):
        """Verify a caller-supplied Wi-Fi device path, else pick the first."""
        devices = self._wifi_devices()
        if not devices:
            raise RuntimeError('No NetworkManager Wi-Fi device available')
        if device_hint and device_hint in devices:
            return device_hint
        return devices[0]

    # ---------------------------------------------------------- access points

    def _access_points(self, device_path):
        """Read every AP currently listed on ``device_path`` as typed values.

        SSID is read as raw bytes; HwAddress/Frequency/Flags/WpaFlags/RsnFlags
        are read as scalars.  Each record carries its D-Bus object path so an
        activation can point at the real AP, never a placeholder.
        """
        obj, _ = self._device(device_path)
        wireless = dbus.Interface(obj, self.WIRELESS_IFACE)
        try:
            paths = wireless.GetAccessPoints()
        except dbus.DBusException as exc:
            logger.info('GetAccessPoints failed (%s): %s', exc.get_dbus_name(), exc)
            paths = []
        aps = []
        for ap_path in paths:
            try:
                ap = self.bus.get_object(self.NM_BUS, ap_path)
                props = dbus.Interface(ap, self.PROPS)
                get = lambda k: props.Get(self.AP_IFACE, k)
                raw_ssid = bytes(get('Ssid'))
                bssid = str(get('HwAddress'))
                frequency = int(get('Frequency'))
                strength = int(get('Strength'))
                rsn = int(get('RsnFlags'))
                wpa = int(get('WpaFlags'))
                flags = int(get('Flags'))
            except Exception as exc:
                logger.info('Skipping unreadable AP %s: %s', ap_path, exc)
                continue
            aps.append({
                'path': str(ap_path),
                'ssid_bytes': raw_ssid,
                'bssid': bssid,
                'frequency': frequency,
                'strength': strength,
                'rsn': rsn,
                'wpa': wpa,
                'flags': flags,
            })
        return aps

    def _resolve_ap(self, device_path, ssid_bytes, ap_path=None, bssid=None):
        """Find the target AP on ``device_path`` without trusting the frontend.

        Priority: (1) a caller-supplied AP object path, but only while it is
        still listed on the same device and its SSID still matches; (2) a
        BSSID + SSID match; (3) a unique SSID match; (4) the strongest of
        duplicate SSIDs.  Returns ``(ap_record_or_None, all_records)``.
        """
        aps = self._access_points(device_path)
        want_bssid = self._norm_mac(bssid)
        if ap_path:
            for ap in aps:
                if ap['path'] == ap_path and ap['ssid_bytes'] == ssid_bytes:
                    return ap, aps
        if want_bssid:
            for ap in aps:
                if self._norm_mac(ap['bssid']) == want_bssid and ap['ssid_bytes'] == ssid_bytes:
                    return ap, aps
        matches = [ap for ap in aps if ap['ssid_bytes'] == ssid_bytes]
        if len(matches) == 1:
            return matches[0], aps
        if len(matches) > 1:
            matches.sort(key=lambda a: a['strength'], reverse=True)
            return matches[0], aps
        return None, aps

    def _bounded_rescan(self, device_path, ssid_bytes, ap_path=None, bssid=None,
                        attempts=2, wait_s=2.5):
        """Refresh the scan and re-resolve, at most ``attempts`` times."""
        obj, _ = self._device(device_path)
        wireless = dbus.Interface(obj, self.WIRELESS_IFACE)
        for _ in range(attempts):
            try:
                wireless.RequestScan(dbus.Dictionary({}, signature='sv'))
            except dbus.DBusException as exc:
                logger.info('RequestScan deferred: %s', exc.get_dbus_name())
            time.sleep(wait_s)
            ap, _ = self._resolve_ap(device_path, ssid_bytes, ap_path, bssid)
            if ap is not None:
                return ap
        return None

    # ------------------------------------------------------------- profiles

    def _find_saved_connection(self, ssid_bytes):
        """Return the object path of an existing saved Wi-Fi profile whose SSID
        bytes match, so a re-connect reuses it instead of creating ``Nuxel <SSID> 2``."""
        try:
            settings = dbus.Interface(
                self.bus.get_object(self.NM_BUS, self.SETTINGS_PATH),
                self.SETTINGS_IFACE)
            for conn_path in settings.ListConnections():
                try:
                    conn = self.bus.get_object(self.NM_BUS, conn_path)
                    conn_iface = dbus.Interface(conn, self.CONN_IFACE)
                    cfg = conn_iface.GetSettings()
                except dbus.DBusException:
                    continue
                wifi = cfg.get('802-11-wireless') or {}
                saved = wifi.get('ssid')
                try:
                    if bytes(saved) == ssid_bytes:
                        return str(conn_path)
                except Exception:
                    continue
        except dbus.DBusException as exc:
            logger.info('ListConnections failed (%s): %s', exc.get_dbus_name(), exc)
        return None

    def _update_saved_profile(self, conn_path, ssid_bytes, password, security):
        """Refresh a reused profile's secret + autoconnect before activation.

        A previous failed attempt may have left a saved profile with
        ``autoconnect=false`` and a stale/wrong PSK.  Reusing it verbatim would
        then fail authentication or fail to auto-reconnect after reboot, so the
        freshly-entered passphrase and the autoconnect preference are written
        back to the existing settings-connection instead of creating a duplicate.
        The PSK travels only inside the D-Bus settings payload, never argv/logs.
        """
        conn = self.bus.get_object(self.NM_BUS, conn_path)
        conn_iface = dbus.Interface(conn, self.CONN_IFACE)
        cfg = conn_iface.GetSettings()
        conn_s = cfg.get('connection')
        if conn_s is None:
            conn_s = dbus.Dictionary({}, signature='sv')
            cfg['connection'] = conn_s
        conn_s['id'] = dbus.String('Nuxel ' + self._display_ssid(ssid_bytes))
        conn_s['autoconnect'] = dbus.Boolean(True)
        wifi_s = cfg.get('802-11-wireless')
        if wifi_s is None:
            wifi_s = dbus.Dictionary({}, signature='sv')
            cfg['802-11-wireless'] = wifi_s
        wifi_s['ssid'] = dbus.ByteArray(ssid_bytes)
        wifi_s['mode'] = dbus.String('infrastructure')
        if security != 'open':
            wifi_s['security'] = dbus.String('802-11-wireless-security')
            sec = cfg.get('802-11-wireless-security')
            if sec is None:
                sec = dbus.Dictionary({}, signature='sv')
                cfg['802-11-wireless-security'] = sec
            sec['key-mgmt'] = dbus.String('sae' if security == 'wpa3' else 'wpa-psk')
            sec['psk'] = dbus.String(password)
        else:
            cfg.pop('802-11-wireless-security', None)
        conn_iface.Update(dbus.Dictionary(cfg, signature='sa{sv}'))

    def _build_profile(self, ssid_bytes, password, security):
        """Typed ``a{sa{sv}}`` connection profile with autoconnect enabled."""
        wifi_cfg = dbus.Dictionary({
            'ssid': dbus.ByteArray(ssid_bytes),
            'mode': dbus.String('infrastructure'),
        }, signature='sv')
        profile = {
            'connection': dbus.Dictionary({
                'id': dbus.String('Nuxel ' + self._display_ssid(ssid_bytes)),
                'type': dbus.String('802-11-wireless'),
                'autoconnect': dbus.Boolean(True),
                'autoconnect-priority': dbus.Int32(0),
            }, signature='sv'),
            '802-11-wireless': wifi_cfg,
            'ipv4': dbus.Dictionary({'method': dbus.String('auto')}, signature='sv'),
            'ipv6': dbus.Dictionary({'method': dbus.String('auto')}, signature='sv'),
        }
        if security != 'open':
            wifi_cfg['security'] = dbus.String('802-11-wireless-security')
            profile['802-11-wireless-security'] = dbus.Dictionary({
                'key-mgmt': dbus.String('sae' if security == 'wpa3' else 'wpa-psk'),
                'psk': dbus.String(password),
            }, signature='sv')
        return profile

    # ------------------------------------------------------------- public API

    def get_status(self):
        if not self.connected and not self.connect():
            return {'available': False, 'connected': False,
                    'wifi_available': False, 'wifi_connected': False,
                    'wifi_state': 'unavailable', 'wifi_stage': 'unavailable',
                    'error': self.last_error or 'NetworkManager unavailable'}
        try:
            self._refresh_proxy()
            props = dbus.Interface(self.nm_proxy, self.PROPS)
            connectivity = props.Get(self.NM_IFACE, 'Connectivity')
            wifi_enabled = props.Get(self.NM_IFACE, 'WirelessEnabled')
            wifi_devices = []
            for device_path in self._wifi_devices():
                _, device_props = self._device(device_path)
                interface = str(device_props.Get(self.DEV_IFACE, 'Interface'))
                state = int(device_props.Get(self.DEV_IFACE, 'State'))
                wifi_devices.append({'interface': interface, 'state': state,
                                     'path': device_path})
            active = [row for row in wifi_devices if row['state'] == 100]
            highest_state = max((row['state'] for row in wifi_devices), default=None)
            # Device state -> honest lifecycle stage (NM DeviceState values).
            # 30 disconnected, 40 prepare, 50 config, 60 need-auth,
            # 70 ip-config, 80 ip-check, 90 secondaries, 100 activated.
            if not wifi_enabled:
                wifi_state = 'disabled'
                wifi_stage = 'disabled'
            elif not wifi_devices:
                wifi_state = 'unavailable'
                wifi_stage = 'unavailable'
            elif active:
                wifi_state = 'internet' if int(connectivity) == 4 else 'connected'
                wifi_stage = 'online' if int(connectivity) == 4 else 'connected'
            elif highest_state == 10:
                wifi_state = 'unmanaged'
                wifi_stage = 'unmanaged'
            elif highest_state in (40, 50, 60):
                wifi_state = 'connecting'
                wifi_stage = 'associating'
            elif highest_state in (70, 80, 90):
                wifi_state = 'connecting'
                wifi_stage = 'ip'
            else:
                wifi_state = 'enabled_disconnected'
                wifi_stage = 'enabled_disconnected'
            return {
                'available': True,
                'connected': bool(active),
                'state': highest_state if highest_state is not None else 30,
                'connectivity': int(connectivity),
                'wifi_enabled': bool(wifi_enabled),
                'wifi_available': bool(wifi_devices),
                'wifi_connected': bool(active),
                'wifi_state': wifi_state,
                'wifi_stage': wifi_stage,
                'wifi_devices': wifi_devices,
            }
        except Exception as e:
            return {'available': False, 'connected': False,
                    'wifi_available': False, 'wifi_connected': False,
                    'wifi_state': 'unavailable', 'wifi_stage': 'unavailable',
                    'error': str(e)}

    def set_wifi_enabled(self, enabled):
        """Set NM's real WirelessEnabled property and confirm its readback."""
        if not self.connected and not self.connect():
            return {'success': False, 'error': self.last_error or 'NetworkManager unavailable'}
        try:
            self._refresh_proxy()
            props = dbus.Interface(self.nm_proxy, self.PROPS)
            props.Set(self.NM_IFACE, 'WirelessEnabled', dbus.Boolean(bool(enabled)))
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

    def scan_wifi(self):
        """Return real AP observations with verified identity metadata."""
        try:
            path, device, props = self._wifi_device()
            wireless = dbus.Interface(device, self.WIRELESS_IFACE)
            try:
                wireless.RequestScan(dbus.Dictionary({}, signature='sv'),
                                     timeout=self.SCAN_REQUEST_TIMEOUT_SECONDS)
            except dbus.DBusException as exc:
                logger.info('Wi-Fi scan request deferred after bounded wait: %s',
                            exc.get_dbus_name())
            results = []
            for ap in self._access_points(path):
                raw = ap['ssid_bytes']
                results.append({
                    'ssid': self._display_ssid(raw),
                    'ssid_hex': raw.hex(),
                    'strength': ap['strength'],
                    'security': self._security(ap['rsn'], ap['wpa'], ap['flags']),
                    'ap_path': ap['path'],
                    'bssid': ap['bssid'],
                    'frequency': ap['frequency'],
                    'device': path,
                })
            results.sort(key=lambda a: a['strength'], reverse=True)
            return {'success': True, 'networks': results, 'device': str(path)}
        except Exception as exc:
            return {'success': False, 'networks': [], 'error': str(exc)}

    def connect_wifi(self, ssid, password, security, ap_path=None, bssid=None,
                     device=None, ssid_hex=None):
        """Connect through NetworkManager D-Bus using a *verified* AP path.

        ``ap_path``/``bssid``/``device``/``ssid_hex`` are caller hints and are
        never trusted blindly: the target AP must still be listed on the same
        Wi-Fi device and its SSID bytes must match.  A stale AP triggers a
        bounded re-scan; if it is genuinely gone the caller gets a human
        readable ``stale_scan`` error.  PSKs never reach argv or logs.
        """
        try:
            if not isinstance(ssid, str) or '\x00' in ssid:
                return {'success': False, 'error': 'SSID must not contain NUL'}
            ssid_bytes = self._ssid_bytes(ssid, ssid_hex)
            if not 1 <= len(ssid_bytes) <= 32:
                return {'success': False, 'error': 'SSID must contain 1-32 bytes'}
            if security not in ('wpa2', 'wpa3', 'open'):
                return {'success': False, 'error': 'Unsupported security type; WEP and enterprise/EAP are not supported'}
            if security != 'open' and (not isinstance(password, str) or not 8 <= len(password) <= 63):
                return {'success': False, 'error': 'Passphrase must contain 8-63 characters'}

            device_path = self._select_device(device)
            ap, _ = self._resolve_ap(device_path, ssid_bytes, ap_path, bssid)
            if ap is None:
                ap = self._bounded_rescan(device_path, ssid_bytes, ap_path, bssid)
            if ap is None:
                return {'success': False, 'error': 'stale_scan',
                        'detail': 'The selected access point is no longer in the scan list; rescan and retry.'}

            nm_iface = dbus.Interface(self.nm_proxy, self.NM_IFACE)

            existing = self._find_saved_connection(ssid_bytes)
            if existing:
                # Reuse the saved profile (no duplicate), but refresh its secret
                # and autoconnect first so a corrected password persists and the
                # network auto-reconnects after reboot.  ActivateConnection's
                # specific_object may be the AP path or, when unresolvable, '/'.
                self._update_saved_profile(existing, ssid_bytes, password, security)
                try:
                    nm_iface.ActivateConnection(dbus.ObjectPath(existing),
                                                dbus.ObjectPath(device_path),
                                                dbus.ObjectPath(ap['path']))
                except dbus.DBusException:
                    nm_iface.ActivateConnection(dbus.ObjectPath(existing),
                                                dbus.ObjectPath(device_path),
                                                dbus.ObjectPath('/'))
                return {'success': True, 'state': 'connecting', 'stage': 'associating',
                        'ssid': ssid, 'reused': True, 'connection': existing,
                        'ap_path': ap['path'], 'device': device_path}

            profile = self._build_profile(ssid_bytes, password, security)
            settings_path, active_path = nm_iface.AddAndActivateConnection(
                dbus.Dictionary(profile, signature='sa{sv}'),
                dbus.ObjectPath(device_path),
                dbus.ObjectPath(ap['path']))
            # Activation is asynchronous; the caller polls get_status for the
            # honest lifecycle (associating -> ip -> online).
            return {'success': True, 'state': 'connecting', 'stage': 'associating',
                    'ssid': ssid, 'connection': str(settings_path),
                    'active': str(active_path), 'ap_path': ap['path'],
                    'device': device_path}
        except dbus.DBusException as exc:
            logger.warning('Wi-Fi activation failed (%s)', exc.get_dbus_name())
            return {'success': False, 'error': self._friendly_error(exc),
                    'error_code': exc.get_dbus_name(),
                    'stage': 'failed'}
        except Exception as exc:
            logger.warning('Wi-Fi activation failed (%s)', type(exc).__name__)
            return {'success': False, 'error': self._redact(str(exc), password),
                    'stage': 'failed'}

    def disconnect_wifi(self):
        try:
            path, device, props = self._wifi_device()
            dbus.Interface(device, self.DEV_IFACE).Disconnect()
            return {'success': True, 'state': 'disconnected'}
        except Exception as exc:
            return {'success': False, 'error': str(exc)}

    def forget_wifi(self, ssid=None, ssid_hex=None, connection_path=None):
        """Delete a saved profile (explicit Forget), never the active radio."""
        try:
            target = None
            if connection_path:
                target = connection_path
            else:
                ssid_bytes = self._ssid_bytes(ssid, ssid_hex)
                if ssid_bytes:
                    target = self._find_saved_connection(ssid_bytes)
            if not target:
                return {'success': False, 'error': 'No matching saved network'}
            conn = self.bus.get_object(self.NM_BUS, target)
            dbus.Interface(conn, self.CONN_IFACE).Delete()
            return {'success': True, 'connection': target}
        except dbus.DBusException as exc:
            return {'success': False, 'error': self._friendly_error(exc),
                    'error_code': exc.get_dbus_name()}
        except Exception as exc:
            return {'success': False, 'error': str(exc)}

    def saved_wifi(self):
        """List saved Wi-Fi profiles (SSID, autoconnect, active state)."""
        try:
            self._refresh_proxy()
            mgr = dbus.Interface(self.nm_proxy, self.NM_IFACE)
            # Resolve which settings-connection path is currently active on a
            # Wi-Fi device, so the "connected" marker is real NM state.
            active_conn_paths = set()
            for dev_path in mgr.GetDevices():
                if self._device_type(dev_path) != 2:
                    continue
                _, dp = self._device(dev_path)
                try:
                    ac = str(dp.Get(self.DEV_IFACE, 'ActiveConnection'))
                except Exception:
                    ac = '/'
                if not ac or ac == '/':
                    continue
                try:
                    acobj = self.bus.get_object(self.NM_BUS, ac)
                    acprops = dbus.Interface(acobj, self.PROPS)
                    active_conn_paths.add(str(acprops.Get(
                        'org.freedesktop.NetworkManager.Connection.Active', 'Connection')))
                except Exception:
                    continue
            settings = dbus.Interface(
                self.bus.get_object(self.NM_BUS, self.SETTINGS_PATH),
                self.SETTINGS_IFACE)
            out = []
            for conn_path in settings.ListConnections():
                try:
                    conn = self.bus.get_object(self.NM_BUS, conn_path)
                    conn_iface = dbus.Interface(conn, self.CONN_IFACE)
                    cfg = conn_iface.GetSettings()
                    conn_type = str((cfg.get('connection') or {}).get('type', ''))
                    if conn_type != '802-11-wireless':
                        continue
                    wifi = cfg.get('802-11-wireless') or {}
                    raw = bytes(wifi.get('ssid', b''))
                    conn_id = str((cfg.get('connection') or {}).get('id', ''))
                    autoconnect = bool((cfg.get('connection') or {}).get('autoconnect', False))
                    security = 'open'
                    sec = cfg.get('802-11-wireless-security') or {}
                    if sec.get('key-mgmt') == 'sae':
                        security = 'wpa3'
                    elif sec.get('key-mgmt'):
                        security = 'wpa2'
                    out.append({'ssid': self._display_ssid(raw), 'ssid_hex': raw.hex(),
                                'id': conn_id, 'connection': str(conn_path),
                                'autoconnect': autoconnect, 'security': security,
                                'connected': str(conn_path) in active_conn_paths})
                except dbus.DBusException:
                    continue
            return {'success': True, 'networks': out}
        except dbus.DBusException as exc:
            return {'success': False, 'error': self._friendly_error(exc),
                    'error_code': exc.get_dbus_name()}
        except Exception as exc:
            return {'success': False, 'error': str(exc)}

class GeoClueConnector:
    """Bounded GeoClue2 client.

    GeoClue is the canonical location provider on a normal Linux userspace, but
    it is not always present or responsive on the S10+ port.  Every D-Bus call
    here is bounded: a missing GPS backend must produce an honest provider
    status, not a 25-second D-Bus timeout that also stalls Quick Settings.
    """

    DBUS_TIMEOUT = float(os.environ.get('NUXEL_GEOCLUE_TIMEOUT', '2.0'))
    RETRY_SECONDS = float(os.environ.get('NUXEL_GEOCLUE_RETRY', '20.0'))
    SERVICE_FILE = '/usr/share/dbus-1/system-services/org.freedesktop.GeoClue2.service'

    def __init__(self):
        self.bus = None
        self.client = None
        self.client_iface = None
        self.connected = False
        self.present = False
        self.last_error = None
        self.last_attempt = 0.0
        self.acquiring = False
        self.acquire_started_at = None

    @classmethod
    def service_installed(cls):
        return os.path.exists(cls.SERVICE_FILE)

    def _call(self, iface, method, *args):
        return getattr(iface, method)(*args, timeout=self.DBUS_TIMEOUT)

    def connect(self, force=False):
        now = time.time()
        if self.connected:
            return True
        if not force and self.last_error and (now - self.last_attempt) < self.RETRY_SECONDS:
            return False
        self.last_attempt = now
        try:
            self.bus = dbus.SystemBus()
            geo_obj = self.bus.get_object('org.freedesktop.GeoClue2',
                                          '/org/freedesktop/GeoClue2/Manager')
            manager = dbus.Interface(geo_obj, 'org.freedesktop.GeoClue2.Manager')
            client_path = self._call(manager, 'GetClient')
            self.client = self.bus.get_object('org.freedesktop.GeoClue2', client_path)
            self.client_iface = dbus.Interface(self.client, 'org.freedesktop.GeoClue2.Client')
            self._call(self.client_iface, 'SetDesktopId', 'org.nuxel.Bridge')
            self._call(self.client_iface, 'SetRequestedAccuracyLevel', 1)
            self.connected = True
            self.present = True
            self.last_error = None
            logger.info('GeoClue connected')
            return True
        except Exception as exc:
            self.connected = False
            self.client_iface = None
            self.last_error = str(exc)
            logger.warning('GeoClue connect failed: %s', exc)
            return False

    def start_acquisition(self):
        """Ask GeoClue to start locating.  Returns (ok, error), never a fix."""
        if not self.connected and not self.connect():
            return False, self.last_error or 'GeoClue not connected'
        try:
            self._call(self.client_iface, 'Start')
            self.acquiring = True
            self.acquire_started_at = time.time()
            return True, None
        except Exception as exc:
            self.acquiring = False
            self.last_error = str(exc)
            return False, str(exc)

    def get_location(self):
        """Read the provider's current location, bounded by DBUS_TIMEOUT.

        ``timestamp`` is GeoClue's own Location.Timestamp when available.  The
        caller must not substitute the poll time for a missing provider time.
        """
        if not self.connected and not self.connect():
            return {'success': False, 'error': self.last_error or 'GeoClue not connected',
                    'error_code': 'PROVIDER_UNAVAILABLE'}
        try:
            location_path = self._call(self.client_iface, 'GetLocation')
            if not location_path or location_path == '/':
                return {'success': False, 'error': 'No location available',
                        'error_code': 'NO_FIX'}
            loc_obj = self.bus.get_object('org.freedesktop.GeoClue2', location_path)
            loc_props = dbus.Interface(loc_obj, 'org.freedesktop.DBus.Properties')
            props = self._call(loc_props, 'GetAll', 'org.freedesktop.GeoClue2.Location')
            lat = props.get('Latitude')
            lon = props.get('Longitude')
            if lat is None or lon is None:
                return {'success': False, 'error': 'Provider returned no coordinates',
                        'error_code': 'NO_FIX'}
            timestamp = props.get('Timestamp')
            try:
                timestamp = float(timestamp) if timestamp is not None else None
            except (TypeError, ValueError):
                timestamp = None
            self.last_error = None
            return {
                'success': True,
                'latitude': float(lat),
                'longitude': float(lon),
                'accuracy': float(props.get('Accuracy')) if props.get('Accuracy') is not None else None,
                'altitude': float(props.get('Altitude')) if props.get('Altitude') is not None else None,
                'timestamp': timestamp,
                'observed_at': time.time(),
                'source': 'geoclue2',
            }
        except Exception as exc:
            self.last_error = str(exc)
            return {'success': False, 'error': str(exc), 'error_code': 'PROVIDER_ERROR'}


class BluetoothConnector:
    """Authoritative Bluetooth status/toggle over rfkill + BlueZ + kernel.

    The bridge runs as the nuxel-bridge user, so SET operations that need root
    (rfkill unblock, BlueZ Adapter1.Powered writes) are attempted and the
    ACTUAL result is read back; nothing is faked.  On the S10+ there is no hci0
    (CONFIG_BT_BCM43XX=y but the controller never registers), so the tile must
    report that concrete blocker, never a generic 'unavailable in this build'.
    """

    BLUEZ_BUS = 'org.bluez'
    ADAPTER_IFACE = 'org.bluez.Adapter1'

    def __init__(self):
        self.bus = None

    def _connect(self):
        if self.bus is not None:
            return self.bus
        try:
            self.bus = dbus.SystemBus()
        except Exception:
            self.bus = None
        return self.bus

    # ---- kernel/rfkill evidence (read-only, world-readable) ---------------
    def _rfkill(self):
        out = {'present': False, 'soft_blocked': None, 'hard_blocked': None,
               'names': []}
        try:
            names = sorted(os.listdir('/sys/class/rfkill'))
        except OSError:
            return out
        for name in names:
            base = '/sys/class/rfkill/' + name
            try:
                with open(base + '/type') as f:
                    typ = f.read().strip().lower()
            except OSError:
                continue
            if typ != 'bluetooth':
                continue
            out['present'] = True
            try:
                with open(base + '/name') as f:
                    out['names'].append(f.read().strip())
            except OSError:
                pass
            for key, attr in (('soft_blocked', 'soft'), ('hard_blocked', 'hard')):
                try:
                    with open(base + '/' + attr) as f:
                        out[key] = int(f.read().strip()) == 1
                except (OSError, ValueError):
                    pass
        return out

    def _hci_devices(self):
        try:
            names = [n for n in os.listdir('/sys/class/bluetooth')
                     if n.startswith('hci')]
        except OSError:
            return []
        return sorted(names)

    def _kernel_config(self):
        """Return the running kernel config text, or '' when it is unavailable."""
        try:
            import gzip
            with gzip.open('/proc/config.gz', 'rb') as f:
                return f.read().decode('utf-8', 'replace')
        except Exception:
            return ''

    def _kernel_bt_driver(self):
        """Best-effort: which BT driver does the running kernel carry?"""
        cfg = self._kernel_config()
        if not cfg:
            return 'unknown'
        for k in ('CONFIG_BT_HCIUART', 'CONFIG_BT_HCIBTUSB',
                  'CONFIG_BT_HCIBTSDIO', 'CONFIG_BT_BCM43XX'):
            if k + '=y' in cfg:
                return k.split('_', 2)[-1].lower()
        return 'none'

    def _kernel_hci_transport(self):
        """True/False when the config is readable, None when it is not.

        ``CONFIG_BT_BCM43XX`` is only the Samsung power/rfkill driver; it does
        not create an HCI transport.  Without ``CONFIG_BT_HCIUART`` (or a USB
        transport) the controller can be powered but can never register hci0.
        The verified S10+ image builds HCIUART/H4 and starts ``btattach``, so
        ``hci0`` registers; a false value here still names the exact blocker.
        """
        cfg = self._kernel_config()
        if not cfg:
            return None
        return any(k + '=y' in cfg for k in
                   ('CONFIG_BT_HCIUART', 'CONFIG_BT_HCIBTUSB',
                    'CONFIG_BT_HCIBTSDIO'))

    def _firmware_status(self):
        """Check the BCM43xx HCD firmware candidates (read-only).

        The S10+ uses ``CONFIG_BT_BCM43XX=y`` (platform driver bcm43xx_bluetooth)
        and its HCD blob is the Samsung vendor file.  A missing blob is the
        concrete reason the controller powers on but never registers hci0.
        """
        candidates = ('bcm4375B1_semco.hcd', 'BCM4375B1.hcd', 'bcm4375b1.hcd',
                      'BCM4375.hcd', 'bcm4375.hcd')
        dirs = ('/lib/firmware/brcm', '/lib/firmware', '/usr/lib/firmware/brcm',
                '/usr/lib/firmware', '/vendor/firmware')
        found = []
        checked = []
        for d in dirs:
            for c in candidates:
                path = os.path.join(d, c)
                checked.append(path)
                if os.path.isfile(path):
                    found.append(path)
        return {'present': bool(found), 'found': found, 'checked': checked,
                'hcd_candidates': candidates}

    # ---- BlueZ D-Bus evidence --------------------------------------------
    def _bluez_adapters(self):
        bus = self._connect()
        if bus is None:
            return []
        try:
            mgr = dbus.Interface(
                bus.get_object(self.BLUEZ_BUS, '/'),
                'org.freedesktop.DBus.ObjectManager')
            managed = mgr.GetManagedObjects()
        except Exception:
            return []
        adapters = []
        for obj_path, ifaces in managed.items():
            if self.ADAPTER_IFACE not in ifaces:
                continue
            props = ifaces[self.ADAPTER_IFACE]
            adapters.append({
                'path': str(obj_path),
                'address': str(props.get('Address', '')),
                'name': str(props.get('Name', '')),
                'powered': bool(props.get('Powered', False)),
                'discovering': bool(props.get('Discovering', False)),
            })
        return adapters

    def get_status(self):
        rfkill = self._rfkill()
        hci = self._hci_devices()
        adapters = self._bluez_adapters()
        driver = self._kernel_bt_driver()
        hci_transport = self._kernel_hci_transport()

        adapter_present = bool(hci) or bool(adapters)
        powered = None
        discovering = None
        if adapters:
            powered = any(a['powered'] for a in adapters)
            discovering = any(a['discovering'] for a in adapters)

        if rfkill['hard_blocked']:
            state = 'hardware_blocked'
        elif not adapter_present:
            state = 'service_unavailable'
        elif powered is True:
            state = 'on'
        elif powered is False:
            state = 'off'
        else:
            state = 'unsupported'

        firmware = self._firmware_status()

        detail = []
        if not adapter_present:
            detail.append('no hci0 registered (no BlueZ adapter)')
        if driver in ('none', 'unknown'):
            detail.append('kernel BT controller driver: ' + driver)
        elif adapter_present is False:
            detail.append('kernel BT controller driver: ' + driver)
        if hci_transport is False:
            detail.append('kernel HCI transport missing: CONFIG_BT_HCIUART is not set '
                          '(bcm43xx_bluetooth is power/rfkill only)')
        if rfkill['present'] and rfkill['soft_blocked']:
            detail.append('rfkill soft-blocked')
        if not adapter_present and not firmware['present']:
            detail.append('BCM43xx HCD firmware missing (%s)' %
                          ', '.join(firmware['hcd_candidates'][:2]) +
                          ('…' if len(firmware['hcd_candidates']) > 2 else ''))

        # A distinct, machine-readable blocker string for the UI.  Kernel
        # transport is checked before firmware: a blob cannot create hci0 when
        # no HCI UART/USB transport driver is built in.
        blocker = None
        if rfkill['hard_blocked']:
            blocker = 'RFKILL_HARD_BLOCKED'
        elif not adapter_present and hci_transport is False:
            blocker = 'BLOCKED_KERNEL'
        elif not adapter_present and not firmware['present']:
            blocker = 'BLOCKED_FIRMWARE'
        elif not adapter_present:
            blocker = 'BLOCKED_TRANSPORT'
        elif not powered:
            blocker = 'ADAPTER_OFF'
        else:
            blocker = None

        return {
            'success': True,
            'state': state,
            'adapter_present': adapter_present,
            'powered': powered,
            'discovering': discovering,
            'rfkill_present': rfkill['present'],
            'rfkill_soft_blocked': rfkill['soft_blocked'],
            'rfkill_hard_blocked': rfkill['hard_blocked'],
            'rfkill_names': rfkill['names'],
            'hci_devices': hci,
            'kernel_bt_driver': driver,
            'kernel_hci_transport': hci_transport,
            'adapters': adapters,
            'adapter_address': adapters[0]['address'] if adapters else None,
            'adapter_name': adapters[0]['name'] if adapters else None,
            'firmware_present': firmware['present'],
            'firmware_found': firmware['found'],
            'blocker': blocker,
            'detail': '; '.join(detail) if detail else None,
            'timestamp': time.time(),
        }

    def set_powered(self, enabled):
        enabled = bool(enabled)
        st = self.get_status()

        # Best-effort rfkill unblock/reblock even when no adapter is present.
        # The bridge unit runs as nuxel-bridge with /sys read-only, so this
        # usually cannot write; the root HTTP bridge owns the real rfkill write.
        # It is still attempted here so a direct D-Bus caller is not lied to.
        if enabled:
            try:
                with open('/sys/class/rfkill/rfkill0/soft', 'w') as f:
                    f.write('0')
            except (OSError, PermissionError):
                pass
        else:
            try:
                with open('/sys/class/rfkill/rfkill0/soft', 'w') as f:
                    f.write('1')
            except (OSError, PermissionError):
                pass

        if not st['adapter_present']:
            st = self.get_status()
            st['success'] = False
            st['requested'] = enabled
            st['error'] = 'NO_ADAPTER'
            st['error_detail'] = (st.get('detail') or
                                  'no hci0 registered (no BlueZ adapter)')
            st['blocker'] = st.get('blocker') or 'BLOCKED_TRANSPORT'
            st['powered'] = None
            return st
        # Attempt BlueZ Adapter1.Powered write on every available adapter and
        # READ BACK the actual value (the D-Bus policy only authorises root to
        # write Properties, so a non-root denial is reported, not masked).
        bus = self._connect()
        applied = False
        err = None
        for adapter in st.get('adapters', []):
            try:
                obj = bus.get_object(self.BLUEZ_BUS, adapter['path'])
                props = dbus.Interface(obj, 'org.freedesktop.DBus.Properties')
                props.Set(self.ADAPTER_IFACE, 'Powered', dbus.Boolean(enabled))
                applied = True
            except Exception as exc:
                err = str(exc)
        # Unblock rfkill soft-block when enabling (best effort; needs root).
        if enabled and st.get('rfkill_soft_blocked'):
            try:
                with open('/sys/class/rfkill/rfkill0/soft', 'w') as f:
                    f.write('0')
            except (OSError, PermissionError):
                pass
        readback = self.get_status()
        readback['requested'] = enabled
        readback['success'] = (readback['powered'] == enabled)
        if not readback['success']:
            readback['error'] = err or ('adapter did not confirm Powered=%s' % enabled)
        return readback


class LocationConnector:
    """Canonical location policy and provider state with honest fix reporting.

    The state machine is deliberately explicit:

        unavailable  no provider/hardware path can answer (or the provider is
                     installed but not responsive)
        disabled     the persistent global privacy/provider switch is off
        searching    acquisition was requested from a ready provider and no
                     fix has arrived yet
        no_fix       provider is ready but has no valid current or recent fix
        stale        a real previous fix exists but is older than the documented
                     freshness window
        fixed        a real provider fix within the freshness window
        error        the provider failed and reported a meaningful error

    A coordinate is only exposed when it came from the provider.  Geocoding,
    manual map coordinates and saved pins never enter this object.
    """

    POLICY_PATH = os.environ.get('NUXEL_LOCATION_POLICY',
                                 '/var/lib/nuxel/permissions/location-policy.json')
    FRESH_SECONDS = float(os.environ.get('NUXEL_LOCATION_FRESH_SECONDS', '60'))
    STALE_SECONDS = float(os.environ.get('NUXEL_LOCATION_STALE_SECONDS', '600'))
    SEARCH_WINDOW_SECONDS = float(os.environ.get('NUXEL_LOCATION_SEARCH_WINDOW', '600'))

    def __init__(self):
        self.geoclue = None  # set by NuxelBridgeService after connect()
        self._last_fix = None
        self._last_error = None
        self._acquisition_started_at = None

    def _read_policy(self):
        try:
            with open(self.POLICY_PATH) as f:
                doc = json.load(f)
            return bool(doc.get('enabled', False))
        except (OSError, ValueError):
            return False

    def _write_policy(self, enabled):
        os.makedirs(os.path.dirname(self.POLICY_PATH), exist_ok=True)
        tmp = self.POLICY_PATH + '.tmp'
        doc = {'enabled': bool(enabled), 'updated': time.time()}
        with open(tmp, 'w') as f:
            json.dump(doc, f)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, self.POLICY_PATH)
        return bool(enabled)

    def _provider_ready(self):
        if self.geoclue is None:
            return False
        return bool(getattr(self.geoclue, 'connected', False))

    def _provider_installed(self):
        if self.geoclue is not None and hasattr(self.geoclue, 'service_installed'):
            try:
                if self.geoclue.service_installed():
                    return True
            except Exception:
                pass
        return os.path.exists('/usr/share/dbus-1/system-services/org.freedesktop.GeoClue2.service')

    def _ensure_provider(self):
        """One bounded connection attempt; never waits on a wedged provider."""
        if self._provider_ready() or self.geoclue is None:
            return self._provider_ready()
        try:
            ok = bool(self.geoclue.connect())
            if not ok:
                err = getattr(self.geoclue, 'last_error', None)
                self._last_error = (str(err)[:300] if err else
                                    self._last_error or 'provider did not connect')
            return ok
        except Exception as exc:
            self._last_error = str(exc)[:300]
            return False

    def _gnss_hardware(self):
        """Read-only GNSS path inventory; never a fix claim."""
        nodes = [n for n in ('/dev/ttyBCM', '/dev/ssp_sensorhub',
                             '/dev/ssp_data_injection', '/dev/bbd_sensor')
                 if os.path.exists(n)]
        spi_dir = '/sys/bus/spi/drivers/brcm gps spi'
        bound = []
        try:
            for name in sorted(os.listdir(spi_dir)):
                if name.startswith('spi'):
                    bound.append(os.path.join(spi_dir, name))
        except OSError:
            pass
        firmware = []
        for d in ('/lib/firmware/gnss', '/lib/firmware'):
            try:
                for name in sorted(os.listdir(d)):
                    low = name.lower()
                    if ('bcm477' in low or low.startswith('gps') or low.startswith('gnss')):
                        firmware.append(os.path.join(d, name))
            except OSError:
                continue
        blocker = None
        if not nodes and not bound:
            blocker = 'no GNSS device node or BCM GPS SPI driver binding'
        elif not bound:
            blocker = 'no BCM GPS SPI driver binding'
        if blocker is None and not firmware:
            blocker = 'no GNSS/sensor-hub firmware in /lib/firmware'
        if blocker is None and not nodes:
            blocker = ('GNSS driver is bound but /dev is private to the bridge; '
                       'no GNSS userspace provider is wired')
        if blocker is None:
            blocker = 'no GNSS userspace reader (NMEA/gpsd) is wired'
        return {
            # The bridge unit has PrivateDevices=true, so a node may exist in
            # the real /dev while being hidden here.  A bound SPI device is
            # still positive evidence that the GNSS hardware path is present.
            'present': bool(nodes or bound),
            'nodes': nodes,
            'node_visible_to_bridge': bool(nodes),
            'private_devices': True,
            'driver': 'brcm gps spi',
            'driver_bound': bool(bound),
            'spi_bindings': bound,
            'firmware_present': bool(firmware),
            'firmware': firmware,
            'fix_supported': False,
            'blocker': blocker,
        }

    def _remember_fix(self, loc):
        ts = loc.get('timestamp')
        if ts is None:
            # Do not pretend GeoClue supplied a time.  Use the observation time
            # only when the coordinate is new; a repeated UI poll of the same
            # coordinate must not refresh its age.
            same = (self._last_fix is not None and
                    self._last_fix.get('latitude') == loc.get('latitude') and
                    self._last_fix.get('longitude') == loc.get('longitude') and
                    self._last_fix.get('timestamp_source') == 'observed')
            ts = self._last_fix['timestamp'] if same else (loc.get('observed_at') or time.time())
            ts_source = 'observed'
        else:
            ts_source = 'provider'
        self._last_fix = {
            'latitude': loc['latitude'],
            'longitude': loc['longitude'],
            'accuracy': loc.get('accuracy'),
            'timestamp': float(ts),
            'timestamp_source': ts_source,
            'source': loc.get('source') or 'geoclue2',
            'kind': 'provider',
        }
        self._last_error = None
        return self._last_fix

    def _fix_view(self, now):
        fix = self._last_fix
        if not fix:
            return None
        age = max(0.0, now - fix['timestamp'])
        if age <= self.FRESH_SECONDS:
            freshness = 'fresh'
        elif age <= self.STALE_SECONDS:
            freshness = 'stale'
        else:
            return None
        return dict(fix, age_seconds=age, freshness=freshness)

    def _current_fix(self):
        """Return the provider's real fix, if any.  No coordinate is invented."""
        if not self._ensure_provider():
            return None
        try:
            loc = self.geoclue.get_location()
        except Exception as exc:
            self._last_error = str(exc)
            return None
        if not loc or not loc.get('success'):
            code = (loc or {}).get('error_code')
            if code == 'PROVIDER_ERROR':
                self._last_error = (loc or {}).get('error') or 'provider error'
            elif code == 'NO_FIX':
                # The provider answered; "no fix" is not a provider failure.
                self._last_error = None
            return None
        try:
            lat = float(loc['latitude'])
            lon = float(loc['longitude'])
            if not (math.isfinite(lat) and math.isfinite(lon)) or not (-90 <= lat <= 90) or not (-180 <= lon <= 180):
                raise ValueError('coordinates out of range')
            loc = dict(loc, latitude=lat, longitude=lon)
            return self._remember_fix(loc)
        except (KeyError, TypeError, ValueError) as exc:
            self._last_error = 'invalid provider fix: %s' % exc
            return None

    def start_acquisition(self):
        if not self._ensure_provider():
            return False, self._last_error or 'location provider unavailable'
        try:
            ok, err = self.geoclue.start_acquisition()
        except Exception as exc:
            ok, err = False, str(exc)
        if ok:
            self._acquisition_started_at = time.time()
            self._last_error = None
        else:
            self._last_error = err or 'provider did not start acquisition'
        return ok, self._last_error

    def _state(self, enabled, provider_ready, provider_installed, fix, now):
        if not enabled:
            return 'disabled'
        if not provider_ready:
            return 'unavailable'
        if self._last_error and not fix:
            return 'error'
        if fix:
            return 'fixed' if fix['freshness'] == 'fresh' else 'stale'
        started = self._acquisition_started_at
        if started is not None and (now - started) <= self.SEARCH_WINDOW_SECONDS:
            return 'searching'
        return 'no_fix'

    def get_status(self, include_coordinates=True):
        now = time.time()
        enabled = self._read_policy()
        provider_ready = self._provider_ready()
        provider_installed = self._provider_installed()
        if enabled:
            provider_ready = self._ensure_provider()
            self._current_fix()
        fix = self._fix_view(now)
        state = self._state(enabled, provider_ready, provider_installed, fix, now)
        gnss = self._gnss_hardware()
        detail = None
        if state == 'unavailable':
            if provider_installed:
                if self._last_error:
                    detail = 'GeoClue2 is installed but unavailable: ' + self._last_error
                else:
                    detail = 'GeoClue2 is installed but did not answer within %.1fs' % getattr(
                        self.geoclue, 'DBUS_TIMEOUT', 2.0)
            else:
                detail = 'GeoClue2 is not installed'
        elif state == 'error':
            detail = self._last_error or 'location provider error'
        elif state == 'searching':
            detail = 'acquisition requested; waiting for the provider to produce a fix'
        elif state in ('no_fix', 'stale'):
            detail = gnss.get('blocker')
        # Only a fixed/stale state may expose a coordinate.  In particular a
        # provider that has just disappeared must not leave a "current" fix on
        # screen merely because its last timestamp is still recent.
        expose = fix if state in ('fixed', 'stale') else None
        return {
            'success': True,
            'state': state,
            'enabled': enabled,
            'permission_enabled': enabled,
            'provider': 'geoclue2',
            'provider_available': bool(provider_installed),
            'provider_ready': bool(provider_ready),
            'provider_detail': detail,
            'detail': detail,
            'location_fix_available': state == 'fixed',
            'fix_valid': state == 'fixed',
            'stale': state == 'stale',
            'fix_source': expose['source'] if expose else None,
            'fix_kind': expose.get('kind', 'provider') if expose else None,
            'gnss_fix': False,
            'fix_timestamp': expose['timestamp'] if expose else None,
            'last_fix_timestamp': expose['timestamp'] if expose else None,
            'last_fix_age_s': expose['age_seconds'] if expose else None,
            'accuracy': expose['accuracy'] if (expose and include_coordinates) else None,
            'latitude': expose['latitude'] if (expose and include_coordinates) else None,
            'longitude': expose['longitude'] if (expose and include_coordinates) else None,
            'freshness_seconds': self.FRESH_SECONDS,
            'stale_after_seconds': self.STALE_SECONDS,
            'acquiring': state == 'searching',
            'acquisition_started_at': self._acquisition_started_at,
            'last_error': self._last_error,
            'gnss': gnss,
            'timestamp': now,
        }

    def set_enabled(self, enabled):
        enabled = bool(enabled)
        self._write_policy(enabled)
        if enabled:
            self.start_acquisition()
        else:
            if self.geoclue is not None and getattr(self.geoclue, 'connected', False):
                try:
                    self.geoclue.client_iface.Stop(timeout=getattr(self.geoclue, 'DBUS_TIMEOUT', 2.0))
                except Exception:
                    pass
            self._acquisition_started_at = None
        # The policy toggle itself is not a position read; never echo a
        # coordinate from this administrative response.
        st = self.get_status(include_coordinates=False)
        st['requested'] = enabled
        st['success'] = (st['enabled'] == enabled)
        return st


class OrientationConnector:
    """Proxy to the ONE orientation policy implementation (nuxel-orientationd).

    The bridge must not re-implement the seven-mode table or the hysteresis
    policy; it delegates to the daemon (subprocess) exactly as nuxelctl
    delegates to the diag scripts, so there is a single source of truth. A
    missing daemon / failed call is reported honestly (``success: False``),
    never replaced with a mock mode.
    """

    BIN = os.environ.get("NUXEL_ORIENTATIOND", "/usr/libexec/nuxel/nuxel-orientationd")

    def _run(self, *args):
        try:
            proc = subprocess.run(
                [self.BIN, *args, "--json"], capture_output=True,
                text=True, timeout=6)
        except (OSError, subprocess.SubprocessError) as exc:
            return {"success": False, "error": "orientation daemon unavailable: %s" % exc}
        if not proc.stdout.strip():
            return {"success": False, "error": "orientation daemon returned no output",
                    "stderr": proc.stderr.strip()}
        try:
            return json.loads(proc.stdout)
        except ValueError:
            return {"success": False, "error": "orientation daemon returned non-JSON",
                    "stderr": proc.stderr.strip()[:200]}

    def get_status(self):
        return self._run("status")

    def modes(self):
        return self._run("modes")

    def set_mode(self, mode):
        if not isinstance(mode, str) or not mode.strip():
            return {"success": False, "error": "invalid mode value"}
        return self._run("set", mode.strip())

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
        self.orientation = OrientationConnector()
        self.bluetooth = BluetoothConnector()
        self.location = LocationConnector()
        self.location.geoclue = self.geoclue
        self.media = media_store.MediaStore(MEDIA_DIR)
        
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
        """Load valid capability grants without treating policy state as grants.

        ``PERMISSIONS_DIR`` is intentionally shared with the location privacy
        policy.  Grant files contain ``capability -> {duration, ...}``, whereas
        the policy is ``{enabled: bool, updated: number}``.  A previous loader
        assumed every value had ``.get``; one location toggle could therefore
        crash the bridge before it exported its D-Bus object and take Wi-Fi,
        Bluetooth, and Location down together.

        Accept the historical boolean grant representation for compatibility,
        but ignore false/unknown entries and the policy document itself.  Bad
        persisted state must be observable in the journal, never prevent the
        provider from starting.
        """
        grants = {}
        permissions_dir = PERMISSIONS_DIR
        policy_name = os.path.basename(os.environ.get(
            'NUXEL_LOCATION_POLICY',
            '/var/lib/nuxel/permissions/location-policy.json'))
        if os.path.isdir(permissions_dir):
            for fname in os.listdir(permissions_dir):
                if not fname.endswith('.json') or fname == policy_name:
                    continue
                app_id = fname[:-5].replace('_', '/')
                try:
                    with open(os.path.join(permissions_dir, fname)) as f:
                        data = json.load(f)
                except (json.JSONDecodeError, OSError) as exc:
                    logger.warning('Ignoring unreadable capability grant file %s: %s', fname, exc)
                    continue
                if not isinstance(data, dict):
                    logger.warning('Ignoring non-object capability grant file %s', fname)
                    continue

                app_grants = {}
                for cap, info in data.items():
                    if isinstance(info, dict):
                        app_grants[str(cap)] = info.get('duration', 'always')
                    elif info is True:
                        # Older grant stores used capability -> true.  Retain a
                        # positive user grant rather than making a bridge repair
                        # revoke it, while migrating new writes to the object form.
                        app_grants[str(cap)] = 'always'
                    elif info is not False:
                        logger.warning('Ignoring malformed capability grant %s in %s', cap, fname)
                if app_grants:
                    grants[app_id] = app_grants
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

    @dbus.service.method(INTERFACE_NAME, in_signature='ssssssss', out_signature='s')
    def NetworkWifiConnect(self, app_id, ssid, password, security, ap_path, bssid, device, ssid_hex):
        if not self._check_capability(app_id, 'network:manage'):
            return json.dumps({'success': False, 'error': 'Network permission denied'})
        return json.dumps(self.network.connect_wifi(
            str(ssid), str(password), str(security),
            ap_path=(str(ap_path) if ap_path else None),
            bssid=(str(bssid) if bssid else None),
            device=(str(device) if device else None),
            ssid_hex=(str(ssid_hex) if ssid_hex else None)))

    @dbus.service.method(INTERFACE_NAME, in_signature='s', out_signature='s')
    def NetworkWifiDisconnect(self, app_id):
        if not self._check_capability(app_id, 'network:manage'):
            return json.dumps({'success': False, 'error': 'Network permission denied'})
        return json.dumps(self.network.disconnect_wifi())

    @dbus.service.method(INTERFACE_NAME, in_signature='s', out_signature='s')
    def NetworkWifiSaved(self, app_id):
        if not self._check_capability(app_id, 'network:manage'):
            return json.dumps({'success': False, 'error': 'Network permission denied'})
        return json.dumps(self.network.saved_wifi())

    @dbus.service.method(INTERFACE_NAME, in_signature='ss', out_signature='s')
    def NetworkWifiForget(self, app_id, connection_path):
        if not self._check_capability(app_id, 'network:manage'):
            return json.dumps({'success': False, 'error': 'Network permission denied'})
        return json.dumps(self.network.forget_wifi(connection_path=(str(connection_path) if connection_path else None)))

    # ---------- D-Bus: Bluetooth (A73) ----------

    @dbus.service.method(INTERFACE_NAME, in_signature='s', out_signature='s')
    def BluetoothGetStatus(self, app_id):
        return json.dumps(self.bluetooth.get_status())

    @dbus.service.method(INTERFACE_NAME, in_signature='sb', out_signature='s')
    def BluetoothSetPowered(self, app_id, enabled):
        if not self._check_capability(app_id, 'bluetooth:manage'):
            return json.dumps({'success': False,
                               'error': 'Capability not granted: bluetooth:manage',
                               'error_code': 'CAPABILITY_DENIED'})
        return json.dumps(self.bluetooth.set_powered(bool(enabled)))

    # ---------- D-Bus: Location (A73) ----------

    @dbus.service.method(INTERFACE_NAME, in_signature='s', out_signature='s')
    def LocationGetStatus(self, app_id):
        # Status is a diagnostic surface.  State, age and the GNSS blocker are
        # useful to any local caller; coordinates/accuracy require location:read.
        granted = 'location:read' in self.capability_grants.get(app_id, {})
        return json.dumps(self.location.get_status(include_coordinates=granted))

    @dbus.service.method(INTERFACE_NAME, in_signature='sb', out_signature='s')
    def LocationSetEnabled(self, app_id, enabled):
        if not self._check_capability(app_id, 'location:manage'):
            return json.dumps({'success': False,
                               'error': 'Capability not granted: location:manage',
                               'error_code': 'CAPABILITY_DENIED'})
        return json.dumps(self.location.set_enabled(bool(enabled)))

    @dbus.service.method(INTERFACE_NAME, in_signature='s', out_signature='s')
    def LocationAcquire(self, app_id):
        """Request acquisition without ever manufacturing a fix."""
        if not self._check_capability(app_id, 'location:read'):
            return json.dumps({'success': False,
                               'error': 'Capability not granted: location:read',
                               'error_code': 'CAPABILITY_DENIED'})
        if not self.location.get_status().get('enabled'):
            return json.dumps({'success': False,
                               'error': 'Location is disabled (global policy)',
                               'error_code': 'LOCATION_DISABLED',
                               'enabled': False, 'state': 'disabled'})
        ok, err = self.location.start_acquisition()
        st = self.location.get_status()
        st['acquire_requested'] = bool(ok)
        if not ok:
            st['last_error'] = err or st.get('last_error')
        return json.dumps(st)

    # ---------- D-Bus: Location ----------
    
    @dbus.service.method(INTERFACE_NAME, in_signature='s', out_signature='s')
    def GetLocation(self, app_id):
        st = self.location.get_status()
        if not st.get('enabled'):
            return json.dumps({'success': False,
                               'error': 'Location is disabled (global policy)',
                               'error_code': 'LOCATION_DISABLED',
                               'state': st.get('state')})
        if not self._check_capability(app_id, 'location:read'):
            return json.dumps({'success': False, 'error': 'Capability not granted: location:read',
                               'error_code': 'CAPABILITY_DENIED'})
        if st.get('state') != 'fixed':
            return json.dumps({'success': False,
                               'error': st.get('detail') or ('Location state: %s' % st.get('state')),
                               'error_code': 'STALE_FIX' if st.get('state') == 'stale' else 'NO_FIX',
                               'state': st.get('state'),
                               'provider_ready': st.get('provider_ready'),
                               'last_fix_timestamp': st.get('last_fix_timestamp'),
                               'last_fix_age_s': st.get('last_fix_age_s')})
        return json.dumps({
            'success': True,
            'latitude': st.get('latitude'),
            'longitude': st.get('longitude'),
            'accuracy': st.get('accuracy'),
            'timestamp': st.get('last_fix_timestamp'),
            'source': st.get('fix_source'),
            'state': st.get('state'),
        })
    
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
    

    # ---------- D-Bus: Orientation ----------

    @dbus.service.method(INTERFACE_NAME, in_signature='s', out_signature='s')
    def OrientationGet(self, app_id):
        """Current orientation state: mode, effective, allowed, sensor, compositor."""
        return json.dumps(self.orientation.get_status())

    @dbus.service.method(INTERFACE_NAME, in_signature='s', out_signature='s')
    def OrientationModes(self, app_id):
        """The seven named modes with allowed sets and auto flags."""
        return json.dumps(self.orientation.modes())

    @dbus.service.method(INTERFACE_NAME, in_signature='ss', out_signature='s')
    def OrientationSet(self, app_id, mode):
        """Validate and persist a mode; reject malformed values."""
        return json.dumps(self.orientation.set_mode(mode))


    # ---------- D-Bus: Camera / media (A52 file-backed store) ----------

    def _camera_status_payload(self):
        """Honest camera hardware status. A /dev/video* node existing is NOT a
        claim that a frame can be captured (the S10+ FIMC-IS vendor interface is
        blocked). The bridge reports the enumerated state truthfully.

        The bridge runs with DevicePolicy=closed, so it cannot enumerate the
        host /dev.  An authoritative system snapshot is therefore read from
        /var/lib/nuxel/camera-topology.json (generated by root at deploy time);
        /dev enumeration is only the fallback when that snapshot is absent.
        """
        nodes = []
        source = "snapshot"
        try:
            with open("/var/lib/nuxel/camera-topology.json") as f:
                doc = json.load(f)
            listed = doc.get("video_nodes") or doc.get("nodes") or []
            nodes = [str(n) for n in listed if str(n)]
        except (OSError, ValueError, TypeError):
            source = "dev-enumeration"
            try:
                nodes = sorted(n for n in os.listdir("/dev") if n.startswith("video"))
            except OSError:
                nodes = []
        # capture_verified is NEVER claimed without a real decoded frame.
        return {
            "success": True,
            "camera_present": len(nodes) > 0,
            "capture_verified": False,
            "error": None if nodes else "NO_CAMERA",
            "source": source,
            "video_node_count": len(nodes),
            "detail": ("V4L2 nodes enumerated (%d); the Exynos FIMC-IS vendor "
                       "interface does not expose standard capture (see "
                       "docs/a52-camera/MEDIA-PIPELINE-ANALYSIS.md)" % len(nodes))
                       if nodes else "no /dev/video* node visible to the bridge",
        }

    @dbus.service.method(INTERFACE_NAME, in_signature='s', out_signature='s')
    def CameraStatus(self, app_id):
        return json.dumps(self._camera_status_payload())

    @dbus.service.method(INTERFACE_NAME, in_signature='ss', out_signature='s')
    def CameraListCaptures(self, app_id, kind):
        if not self._check_capability(app_id, 'camera:preview'):
            return json.dumps({'success': False, 'error': 'Capability not granted: camera:preview',
                               'error_code': 'PERMISSION_DENIED'})
        kind = (kind or '').strip() or None
        try:
            records = self.media.list(kind)
        except Exception as exc:
            return json.dumps({'success': False, 'error': 'media list failed: %s' % exc})
        # Do NOT return base64 pixel data: metadata + canonical path only.
        rows = [{
            'id': r['id'], 'kind': r['kind'], 'name': r['name'], 'path': r['path'],
            'size': r.get('size'), 'taken': r.get('taken'), 'mtime': r.get('mtime'),
            'width': r.get('width'), 'height': r.get('height'),
            'orientation': r.get('orientation'), 'camera': r.get('camera'),
            'duration': r.get('duration'), 'mime': r.get('mime'),
        } for r in records]
        return json.dumps({'success': True, 'captures': rows, 'count': len(rows)})

    @dbus.service.method(INTERFACE_NAME, in_signature='ssss', out_signature='s')
    def CameraCapture(self, app_id, kind, mime, data_b64):
        if not self._check_capability(app_id, 'camera:capture'):
            return json.dumps({'success': False, 'error': 'Capability not granted: camera:capture',
                               'error_code': 'PERMISSION_DENIED'})
        try:
            import base64
            data = base64.b64decode(data_b64)
        except Exception as exc:
            return json.dumps({'success': False, 'error': 'invalid payload encoding: %s' % exc})
        cap = media_store.MAX_PHOTO_BYTES if kind == 'photo' else media_store.MAX_VIDEO_BYTES
        if len(data) > cap:
            return json.dumps({'success': False, 'error': 'payload exceeds size cap (%d > %d)'
                               % (len(data), cap), 'error_code': 'PAYLOAD_TOO_LARGE'})
        try:
            rec = self.media.save(kind, data, mime=mime or None)
        except media_store.MediaStoreError as exc:
            return json.dumps({'success': False, 'error': str(exc), 'error_code': 'SAVE_FAILED'})
        return json.dumps({'success': True, 'capture': {
            'id': rec['id'], 'kind': rec['kind'], 'name': rec['name'], 'path': rec['path'],
            'size': rec['size'], 'taken': rec['taken'], 'mime': rec['mime'],
        }})

    @dbus.service.method(INTERFACE_NAME, in_signature='ss', out_signature='s')
    def CameraOpen(self, app_id, capture_id):
        if not self._check_capability(app_id, 'camera:preview'):
            return json.dumps({'success': False, 'error': 'Capability not granted: camera:preview',
                               'error_code': 'PERMISSION_DENIED'})
        got = self.media.get(capture_id)
        if got is None:
            return json.dumps({'success': False, 'error': 'capture not found',
                               'error_code': 'NOT_FOUND'})
        rec, data = got
        if len(data) > media_store.MAX_PHOTO_BYTES * 2:
            return json.dumps({'success': False, 'error': 'capture too large to inline',
                               'error_code': 'PAYLOAD_TOO_LARGE'})
        import base64
        return json.dumps({'success': True, 'capture': {
            'id': rec['id'], 'kind': rec['kind'], 'name': rec['name'], 'mime': rec['mime'],
            'width': rec.get('width'), 'height': rec.get('height'),
            'data_b64': base64.b64encode(data).decode('ascii'),
        }})

    @dbus.service.method(INTERFACE_NAME, in_signature='ss', out_signature='s')
    def CameraDelete(self, app_id, capture_id):
        if not self._check_capability(app_id, 'camera:capture'):
            return json.dumps({'success': False, 'error': 'Capability not granted: camera:capture',
                               'error_code': 'PERMISSION_DENIED'})
        ok = self.media.delete(capture_id)
        return json.dumps({'success': ok, 'deleted': ok,
                           'error': None if ok else 'capture not found or not deletable'})

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
    logger.info("Starting Nuxel Bridge v0.2.1...")
    
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
