"""Carrier DNS64 validation: never invent a translation prefix."""
import importlib
import ipaddress
from pathlib import Path
import struct
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'tools/s10plus/s5000ap-05/scripts'))
clat = importlib.import_module('cellular_clat')


def response(addresses, ident=42):
    question = b'\x08ipv4only\x04arpa\x00' + struct.pack('!HH', 28, 1)
    records = b''.join(b'\xc0\x0c' + struct.pack('!HHIH', 28, 1, 60, 16)
                       + ipaddress.IPv6Address(a).packed for a in addresses)
    return struct.pack('!6H', ident, 0x8180, 1, len(addresses), 0, 0) + question + records


def install_socket(monkeypatch, reply):
    class Socket:
        def __enter__(self): return self
        def __exit__(self, *_): pass
        def setsockopt(self, *args): assert args[-1] == b'rmnet0\0'
        def settimeout(self, *_): pass
        def connect(self, *_): pass
        def send(self, *_): pass
        def recv(self, *_): return reply
    monkeypatch.setattr(clat.socket, 'SO_BINDTODEVICE', 25, raising=False)
    monkeypatch.setattr(clat.socket, 'socket', lambda *_: Socket())
    monkeypatch.setattr(clat.secrets, 'randbelow', lambda _: 42)


def test_discover_requires_both_rfc7050_answers(monkeypatch):
    install_socket(monkeypatch, response(['64:ff9b::c000:aa', '64:ff9b::c000:ab']))
    assert clat.discover('2001:db8::53') == '64:ff9b::/96'


def test_rejects_unproven_or_mismatched_prefix(monkeypatch):
    import pytest
    for reply in [response(['64:ff9b::c000:aa']),
                  response(['64:ff9b::c000:aa', '2001:db8::c000:ab']),
                  response(['64:ff9b::c000:aa', '64:ff9b::c000:ab'], ident=43),
                  b'\x00']:
        install_socket(monkeypatch, reply)
        with pytest.raises(clat.LinkError): clat.discover('2001:db8::53')
