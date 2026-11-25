"""Native Radio1 adapter. No raw modem access or route/DNS ownership here."""
import os
import json
from pathlib import Path
import threading
import time

_sample_lock = threading.Lock()
_sample = None


def cellular_statistics(connected):
    """Counters are lifetime netdev counters; duration belongs to this bearer."""
    global _sample
    result = dict(rx_bytes=None, tx_bytes=None, rx_bytes_per_second=None,
                  tx_bytes_per_second=None, duration_seconds=None, dns=[])
    try:
        rx, tx = (int(Path('/sys/class/net/rmnet0/statistics/' + key).read_text())
                  for key in ('rx_bytes', 'tx_bytes'))
        now = time.monotonic()
        result.update(rx_bytes=rx, tx_bytes=tx)
        with _sample_lock:
            if _sample and now - _sample[0] >= 0.5 and rx >= _sample[1] and tx >= _sample[2]:
                result['rx_bytes_per_second'] = (rx - _sample[1]) / (now - _sample[0])
                result['tx_bytes_per_second'] = (tx - _sample[2]) / (now - _sample[0])
            if not _sample or now - _sample[0] >= 0.5:
                _sample = (now, rx, tx)
        if connected:
            link = json.loads(Path('/run/nuxel-radio/cellular-link.json').read_text())
            if link.get('configured') and link['config']['iface'] == 'rmnet0':
                result['dns'] = link['config']['dns']
                if 'started_monotonic' in link:
                    result['duration_seconds'] = max(0, int(now - link['started_monotonic']))
    except (OSError, ValueError, KeyError, TypeError):
        pass
    return result


class NativeRadio:
    def __init__(self, invoke=None):
        self.invoke = invoke or self._invoke

    @staticmethod
    def _invoke(method, *args):
        import dbus
        from dbus.mainloop import NULL_MAIN_LOOP
        if method == 'StartDataSession':
            args = (str(args[0]), dbus.UInt32(args[1]))
        bus = dbus.SystemBus(private=True, mainloop=NULL_MAIN_LOOP)
        # The HTTP bridge also dispatches a shared GLib system bus. Closing
        # this short-lived connection must not let libdbus exit the process.
        bus.set_exit_on_disconnect(False)
        try:
            obj = bus.get_object('nl.nuxel.Radio1', '/nl/nuxel/Radio1', introspect=False)
            return getattr(dbus.Interface(obj, 'nl.nuxel.Radio1'), method)(*args, timeout=3)
        finally:
            bus.close()

    def status(self):
        try:
            data = dict(self.invoke('GetDataSessionState'))
            sim = str(self.invoke('GetSimState'))
            registered = data.get('registration') in ('REGISTERED_HOME', 'REGISTERED_ROAMING')
            desired = data.get('mobile_data_enabled')
            connected = data.get('ip_configured') == 'true' and desired == 'true'
            return {
                'available': True, 'source': 'native:Radio1',
                'registered': registered,
                'connected': connected,
                'sim_state': sim, 'sim_present': False if sim == 'absent' else True if sim == 'ready' else None,
                'registration': data.get('registration', 'UNKNOWN'),
                'registration_raw': data.get('registration_raw', 'unknown'),
                'error': ('Timed out at ' + data.get('failure_phase', 'unknown'))
                         if data.get('phase') == 'FAILED' else
                         ('Native network configuration failed' if data.get('link_result') not in (None, '0')
                          else 'Carrier rejected the data session') if data.get('phase') == 'REJECTED' else None,
                'state': 'no-sim' if sim == 'absent' else 'registered' if registered else 'searching',
                'technology': data.get('rat', 'unknown'),
                # Home PLMN is not the actual serving operator, especially when roaming.
                'operator': None, 'signal_quality': None, 'signal_valid': False,
                'mobile_data_enabled': desired == 'true' if desired in ('true', 'false') else None,
                'connection_state': data.get('connection_state', 'unknown'),
                'apn': data.get('apn', ''), 'phase': data.get('phase', 'unknown'),
                'failure_phase': data.get('failure_phase', 'unknown'),
                'failure_result': data.get('failure_result', 'unavailable'),
                'disconnect_result': data.get('disconnect_result', 'unknown'),
                'interface': 'rmnet0', 'cid': 1,
                'ipv4': data.get('ipv4') if data.get('ip_configured') == 'true' else None,
                'ipv6': data.get('ipv6') if data.get('ip_configured') == 'true' else None,
                'link_result': data.get('link_result', 'unknown'),
                'home_operator': data.get('home_plmn') or None,
                'roaming': data.get('registration') == 'REGISTERED_ROAMING' if registered else None,
                'statistics': cellular_statistics(connected),
            }
        except Exception:
            return {'available': False, 'connected': False, 'registered': False,
                    'source': 'native:Radio1', 'state': 'unavailable',
                    'mobile_data_enabled': None, 'connection_state': 'unavailable',
                    'signal_quality': None, 'signal_valid': False, 'operator': None}

    def set_enabled(self, enabled):
        if not isinstance(enabled, (bool, int)) or enabled not in (True, False):
            return {'success': False, 'error': 'enabled must be a boolean'}
        try:
            if enabled:
                state = dict(self.invoke('GetDataSessionState'))
                apn = str(state.get('apn') or 'internet')
                accepted = bool(self.invoke('StartDataSession', apn, 1))
            else:
                accepted = bool(self.invoke('StopDataSession'))
            return {'success': accepted, 'modem': self.status()}
        except Exception:
            # Do not copy exception strings that might contain private D-Bus arguments.
            return {'success': False, 'error': 'Native data operation refused or unavailable; check radio status',
                    'modem': self.status()}
