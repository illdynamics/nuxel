import importlib
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'tools/s10plus/s5000ap-05/scripts'))
nm = importlib.import_module('cellular_nm')
link = importlib.import_module('cellular_link')


def test_ipv6_only_uses_carrier_dns_and_no_ipv4_or_autoconnect():
    config = link.configuration(['rmnet0', '1', '-', '0', '2001:db8::1234',
                                 '-', '-', '2001:db8::53', '-', '1500'])
    args = nm.profile_args(config)
    values = dict(zip(args[3::2], args[4::2]))
    assert values['connection.autoconnect'] == 'no'
    assert values['ipv4.method'] == 'disabled'
    assert values['ipv6.method'] == 'manual'
    assert values['ipv6.dns'] == '2001:db8::53'
    assert 'table=106' in values['ipv6.routes']
    assert 'priority 30601 oif rmnet0 table 106' in values['ipv6.routing-rules']
    assert 'fe80::1234/64' in values['ipv6.addresses']


def test_nm_activation_failure_removes_profile_and_journal(tmp_path, monkeypatch):
    from types import SimpleNamespace
    config = link.configuration(['rmnet0', '1', '192.0.2.2', '32', '-',
                                 '192.0.2.53', '-', '-', '-', '1500'])
    calls = []
    def run(args, **kwargs):
        calls.append(args)
        if 'up' in args:
            raise link.LinkError('activation failed')
        return SimpleNamespace(stdout='[]' if 'route' in args else nm.UUID + '\n', returncode=0, stderr='')
    monkeypatch.setattr(nm, 'run', run)
    monkeypatch.setattr(nm, 'query', lambda a: [{'mtu': 1500}] if 'link' in a else [])
    obj = nm.NetworkManagerLink(tmp_path)
    import pytest
    with pytest.raises(link.LinkError, match='activation failed'):
        obj.apply(config)
    assert not obj.path.exists()
    assert calls[-2] == [nm.NMCLI, '--wait', '10', 'connection', 'delete', 'uuid', nm.UUID]
    assert calls[-1][-1] == 'down'
