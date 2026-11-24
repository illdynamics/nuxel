import importlib
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'tools/s10plus/s5000ap-05/scripts'))
link = importlib.import_module('cellular_link')


def test_resolver_uses_returned_object_path_and_property_array(monkeypatch):
    calls = []
    def query(args):
        calls.append(args)
        if 'GetLink' in args:
            return {'type': 'o', 'data': ['/org/freedesktop/resolve1/link/_34']}
        assert '/org/freedesktop/resolve1/link/_34' in args
        return {'type': 'a(iay)', 'data': [[2, [192, 0, 2, 53]]]}
    monkeypatch.setattr(link, 'resolved_available', lambda: True)
    monkeypatch.setattr(link, 'query', query)
    assert link.Link.resolver_dns(4) == ['192.0.2.53']
    assert calls[0][-2:] == ['i', '4']


def test_resolver_empty_property_is_not_a_nested_array(monkeypatch):
    monkeypatch.setattr(link, 'resolved_available', lambda: True)
    monkeypatch.setattr(link, 'query', lambda args: {'data': ['/org/freedesktop/resolve1/link/_34']} if 'GetLink' in args else {'data': []})
    assert link.Link.resolver_dns(4) == []
