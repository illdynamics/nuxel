"""Sharing must remain cellular-only and protect owner configuration."""
import importlib.util
import json
from pathlib import Path
import sys
from types import SimpleNamespace
import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'services/nuxel-bridge/src'))
import sharing_link
import network_manager
import usb_tether


@pytest.mark.parametrize('service,ready,expected', [
    ('active', False, 'starting'), ('deactivating', True, 'stopping'),
    ('inactive', False, 'off'), ('active', True, 'error'),
])
def test_hotspot_incomplete_process_state(tmp_path, monkeypatch, service, ready, expected):
    spec = importlib.util.spec_from_file_location('hotspot_state_test',
        ROOT / 'services/nuxel-network/nuxel-hotspot.py')
    hotspot = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(hotspot)
    state = tmp_path / 'state.json'
    state.write_text(json.dumps({'enabled': ready}))
    monkeypatch.setattr(hotspot, 'STATE', str(state))
    monkeypatch.setattr(hotspot, 'RUN', str(tmp_path))
    monkeypatch.setattr(hotspot, '_read_pid', lambda _: 0)
    monkeypatch.setattr(hotspot, 'upstream_status', lambda: {'available': True})
    monkeypatch.setattr(hotspot, 'run', lambda args, **_: SimpleNamespace(
        stdout=service if args[0] == 'systemctl' else '1', returncode=0))
    result = hotspot.status()
    assert result['state'] == expected
    assert result['enabled'] is False


def test_upstream_loss_removes_only_live_route_and_retains_terminal_route(tmp_path, monkeypatch):
    (tmp_path / 'owner.json').write_text(json.dumps({'upstream': 'nuxclat', 'dns': ['2001:db8::53']}))
    monkeypatch.setattr(sharing_link, 'root', lambda _: tmp_path)
    commands = []
    monkeypatch.setattr(sharing_link, 'run', lambda *a, **k: commands.append(a))
    sharing_link.refresh('usb', {'available': False})
    assert commands == [('ip', '-4', 'route', 'del', 'default', 'metric', '100', 'table', '108')]
    assert (tmp_path / 'owner.json').exists()


def test_routing_collision_is_not_flushed(tmp_path, monkeypatch):
    monkeypatch.setattr(sharing_link, 'root', lambda _: tmp_path)
    monkeypatch.setattr(sharing_link.pwd, 'getpwnam', lambda _: SimpleNamespace(pw_uid=0, pw_gid=0))
    monkeypatch.setattr(sharing_link.os, 'chown', lambda *_: None)
    calls=[]
    def run(*a, **_):
        calls.append(a)
        return SimpleNamespace(returncode=0, stdout='[{"dst":"default"}]' if 'route' in a else '[]')
    monkeypatch.setattr(sharing_link, 'run', run)
    with pytest.raises(RuntimeError, match='already owned'):
        sharing_link.start('usb', {'available': True, 'dns': ['2001:db8::53'], 'interface': 'nuxclat'})
    assert all('flush' not in c and 'del' not in c for c in calls)
    assert not (tmp_path / 'owner.json').exists()


def test_hotspot_credentials_persist_private_and_reject_newlines(tmp_path, monkeypatch):
    config = tmp_path / 'hotspot' / 'config.json'
    monkeypatch.setattr(network_manager, 'HOTSPOT_CONFIG', config)
    first = network_manager._hotspot_config()
    assert len(first['password']) >= 20
    assert config.stat().st_mode & 0o777 == 0o600
    assert network_manager._hotspot_config()['password'] == first['password']
    with pytest.raises(network_manager.NetworkManagerError):
        network_manager._hotspot_config(password='testpass\nwpa=0')
    assert json.loads(config.read_text()) == first


def test_usb_rules_restrict_management_and_downstream_forwarding():
    rules = usb_tether._render({'interface':'usb0'}, {'interface':'nuxclat'})
    assert 'ip saddr 10.100.10.2 tcp dport 2022 accept' in rules
    assert 'input iifname "usb0" drop' in rules
    assert 'forward iifname "usb0" counter drop' in rules
    assert 'oifname "nuxclat" ip saddr 10.100.10.0/24' in rules
    assert 'flush ruleset' not in rules
    assert 'policy drop' not in rules  # Other owners retain their forwarding policy.


@pytest.mark.parametrize('baseline', ['0', '1'])
def test_last_sharing_owner_restores_original_forwarding(tmp_path, monkeypatch, baseline):
    monkeypatch.setattr(sharing_link, 'COMMON', tmp_path)
    values = {'net.ipv4.ip_forward': baseline, 'net.ipv4.conf.usb0.rp_filter': '1',
              'net.ipv4.conf.wlan1.rp_filter': '2', 'net.ipv4.conf.nuxclat.rp_filter': '1'}
    original = values.copy()
    def sysctl(*args, **kwargs):
        if args[1] == '-n': return SimpleNamespace(stdout=values[args[2]])
        key, value = args[2].split('=')
        values[key] = value
    monkeypatch.setattr(sharing_link, 'run', sysctl)
    sharing_link.forwarding('usb', 'nuxclat')
    sharing_link.forwarding('hotspot', 'nuxclat')
    sharing_link.forwarding('usb')
    assert values['net.ipv4.ip_forward'] == '1'
    assert values['net.ipv4.conf.nuxclat.rp_filter'] == '2'
    assert values['net.ipv4.conf.usb0.rp_filter'] == '1'
    sharing_link.forwarding('hotspot')
    assert values == original
