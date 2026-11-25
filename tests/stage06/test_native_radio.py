import importlib.util
from pathlib import Path

spec = importlib.util.spec_from_file_location('native_radio', Path(__file__).resolve().parents[2] / 'services/nuxel-bridge/src/native_radio.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def backend(data, calls):
    def invoke(method, *args):
        calls.append((method, args))
        if method == 'GetDataSessionState':
            return data
        if method == 'GetSimState':
            return 'ready'
        return True
    return module.NativeRadio(invoke)


def test_registration_is_not_internet_or_signal():
    radio = backend({'registration': 'REGISTERED_HOME', 'rat': 'LTE',
                     'mobile_data_enabled': 'true', 'ip_configured': 'false'}, [])
    status = radio.status()
    assert status['registered'] and not status['connected']
    assert status['signal_quality'] is None and not status['signal_valid']
    assert status['operator'] is None


def test_off_does_not_turn_off_radio():
    calls = []
    radio = backend({'mobile_data_enabled': 'false', 'ip_configured': 'true'}, calls)
    assert radio.set_enabled(False)['success']
    assert calls[0] == ('StopDataSession', ())
    assert all(method != 'SetRadioEnabled' for method, args in calls)
    assert not radio.status()['connected']


def test_on_reuses_native_apn_and_single_transaction():
    calls = []
    radio = backend({'apn': 'fixture.apn'}, calls)
    assert radio.set_enabled(True)['success']
    assert [call for call in calls if call[0] == 'StartDataSession'] == [('StartDataSession', ('fixture.apn', 1))]


def test_missing_preference_stays_unknown():
    assert backend({}, []).status()['mobile_data_enabled'] is None


def test_outage_does_not_invent_mock_modem():
    def failed(*args):
        raise RuntimeError('private details')
    radio = module.NativeRadio(failed)
    assert radio.status()['state'] == 'unavailable'
    assert radio.set_enabled(False)['success'] is False
    assert 'private details' not in str(radio.set_enabled(True))


def test_invalid_toggle_does_not_issue_command():
    calls = []
    assert not backend({}, calls).set_enabled('false')['success']
    assert calls == []


def test_dbus_profile_is_unsigned(monkeypatch):
    import sys
    from types import SimpleNamespace
    calls = []
    class UInt32(int):
        pass
    class Bus:
        def set_exit_on_disconnect(self, enabled):
            assert enabled is False
        def get_object(self, *args, **kwargs):
            return object()
        def close(self):
            calls.append('closed')
    class Interface:
        def StartDataSession(self, apn, profile, timeout):
            assert type(profile) is UInt32
            calls.append((apn, profile))
            return True
    monkeypatch.setitem(sys.modules, 'dbus', SimpleNamespace(
        UInt32=UInt32, SystemBus=lambda **kwargs: Bus(),
        Interface=lambda *args: Interface()))
    monkeypatch.setitem(sys.modules, 'dbus.mainloop', SimpleNamespace(NULL_MAIN_LOOP=object()))
    assert module.NativeRadio._invoke('StartDataSession', 'internet', 1)
    assert calls == [('internet', 1), 'closed']


def test_ip_is_visible_only_for_configured_bearer():
    data = {'registration': 'REGISTERED_HOME', 'mobile_data_enabled': 'true',
            'ip_configured': 'true', 'ipv6': '2001:db8::2'}
    radio = backend(data, [])
    assert radio.status()['ipv6'] == '2001:db8::2'
    assert radio.status()['connected']
    data['ip_configured'] = 'false'
    assert radio.status()['ipv6'] is None
    assert not radio.status()['connected']
