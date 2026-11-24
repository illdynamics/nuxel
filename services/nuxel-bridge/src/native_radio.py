"""Native Radio1 adapter. No raw modem access or route/DNS ownership here."""
import os


class NativeRadio:
    def __init__(self, invoke=None):
        self.invoke = invoke or self._invoke

    @staticmethod
    def _invoke(method, *args):
        import dbus
        if method == 'StartDataSession':
            args = (str(args[0]), dbus.UInt32(args[1]))
        bus = dbus.SystemBus(private=True)
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
            return {
                'available': True, 'source': 'native:Radio1',
                'registered': registered,
                'connected': data.get('ip_configured') == 'true' and desired == 'true',
                'sim_state': sim, 'sim_present': False if sim == 'absent' else True if sim == 'ready' else None,
                'registration': data.get('registration', 'UNKNOWN'),
                'registration_raw': data.get('registration_raw', 'unknown'),
                'error': ('Timed out at ' + data.get('failure_phase', 'unknown'))
                         if data.get('phase') == 'FAILED' else
                         'Carrier rejected the data session' if data.get('phase') == 'REJECTED' else None,
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
