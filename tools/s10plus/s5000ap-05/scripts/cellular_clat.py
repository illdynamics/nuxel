#!/usr/bin/python3
"""Native IPv4 compatibility for a genuinely IPv6-only cellular bearer.

Discover the carrier's /96 NAT64 prefix through its DNS (RFC 7050). TAYGA
translates a local RFC7335 address; scoped SNAT uses the actual carrier IPv6.
This is translated IPv4, never a claim that the CP assigned native IPv4.
All mutations have a private undo journal; no kernel/firmware changes.
"""
import ipaddress
import json
import os
from pathlib import Path
import secrets
import socket
import struct
import subprocess
from cellular_link import LinkError, run, query

ROOT = Path('/run/nuxel-radio')
STATE = ROOT / 'clat.json'
IFACE = 'nuxclat'
LOCAL4 = '192.0.0.2'
LOCAL6 = 'fd4e:5558:454c::2'
TAG = 'nuxel-cellular-clat'
UNIT = 'nuxel-cellular-clat.service'


def discover(dns):
    ident = secrets.randbelow(65536)
    question = b'\x08ipv4only\x04arpa\x00' + struct.pack('!HH', 28, 1)
    packet = struct.pack('!6H', ident, 0x100, 1, 0, 0, 0) + question
    with socket.socket(socket.AF_INET6, socket.SOCK_DGRAM) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BINDTODEVICE, b'rmnet0\0')
        sock.settimeout(3)
        sock.connect((dns, 53)); sock.send(packet); data = sock.recv(4096)
    if len(data) < 12:
        raise LinkError('truncated DNS64 reply')
    rid, flags, nq, na, _, _ = struct.unpack_from('!6H', data)
    if rid != ident or flags & 0x820f != 0x8000 or nq != 1:
        raise LinkError('invalid DNS64 reply')
    def name_end(offset):
        for _ in range(128):
            if offset >= len(data): break
            n = data[offset]; offset += 1
            if n == 0: return offset
            if n & 0xc0 == 0xc0 and offset < len(data): return offset + 1
            if n > 63: break
            offset += n
        raise LinkError('invalid DNS64 name')
    off = name_end(12) + 4
    found = {}
    for _ in range(na):
        off = name_end(off)
        if off + 10 > len(data): raise LinkError('truncated DNS64 record')
        kind, cls, _, size = struct.unpack_from('!HHIH', data, off); off += 10
        if off + size > len(data): raise LinkError('truncated DNS64 address')
        if kind == 28 and cls == 1 and size == 16:
            address = ipaddress.IPv6Address(data[off:off+size])
            low = int(address) & 0xffffffff
            if low in (0xc00000aa, 0xc00000ab):
                prefix = str(ipaddress.IPv6Network((int(address) & ~0xffffffff, 96)))
                found.setdefault(prefix, set()).add(low)
        off += size
    for prefix, values in found.items():
        if len(values) == 2: return prefix
    raise LinkError('carrier DNS did not demonstrate a supported /96 NAT64 prefix')


def save(doc):
    tmp = STATE.with_suffix('.new')
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, 'w') as f:
        json.dump(doc, f); f.flush(); os.fsync(f.fileno())
    os.replace(tmp, STATE)


def clear_firewall():
    result = run(['nft', '-j', 'list', 'chain', 'inet', 'nuxel_app_firewall', 'forward'], check=False)
    if result.returncode: return
    for item in json.loads(result.stdout)['nftables']:
        r = item.get('rule', {})
        if r.get('comment') == TAG:
            run(['nft', 'delete', 'rule', 'inet', 'nuxel_app_firewall', 'forward', 'handle', str(r['handle'])])


def down():
    if not STATE.exists(): return
    doc = json.loads(STATE.read_text())
    doc['active'] = False; save(doc)
    run(['systemctl', 'stop', UNIT], check=False)
    clear_firewall()
    while doc.get('undo'):
        args = doc['undo'][-1]
        result = run(args, check=False)
        absent = any(x in result.stderr for x in ('No such', 'Cannot find device', 'does not exist', 'Bad rule'))
        if result.returncode and not absent:
            raise LinkError('CLAT cleanup failed: ' + result.stderr.strip())
        doc['undo'].pop(); save(doc)
    STATE.unlink()
    (ROOT / 'clat.conf').unlink(missing_ok=True)


def verify():
    try:
        doc = json.loads(STATE.read_text())
        if not doc.get('active'): return False
        return (run(['systemctl', 'is-active', '--quiet', UNIT], check=False).returncode == 0
                and Path('/sys/class/net/' + IFACE).exists())
    except (OSError, ValueError): return False


def apply(config):
    if '4' in config['sources'] or '6' not in config['sources']: return
    if verify(): return
    down()
    prefix = None
    for dns in config['dns']:
        if ipaddress.ip_address(dns).version != 6: continue
        try: prefix = discover(dns); break
        except (OSError, LinkError): pass
    if not prefix: raise LinkError('no supported carrier DNS64 prefix')
    # Reserved local translation range must not overlap owner configuration.
    addresses = query(['ip', '-j', 'address', 'show'])
    for iface in addresses:
        for addr in iface.get('addr_info', []):
            if addr.get('local') in (LOCAL4, LOCAL6): raise LinkError('CLAT local address already in use')
    doc = {'active': False, 'prefix': prefix, 'interface': IFACE,
           'ipv4': LOCAL4, 'carrier_interface': 'rmnet0', 'undo': [], 'error': None}
    save(doc)
    def change(args, undo):
        doc['undo'].append(undo); save(doc); run(args)
    try:
        (ROOT/'clat.conf').write_text('tun-device '+IFACE+'\nipv4-addr 192.0.0.1\n'
            'ipv6-addr fd4e:5558:454c::1\nprefix '+prefix+'\nmap '+LOCAL4+' '+LOCAL6+'\n')
        run(['systemctl', 'start', UNIT])
        import time
        for _ in range(30):
            if Path('/sys/class/net/'+IFACE).exists(): break
            time.sleep(.1)
        # The same TUN carries IPv4 and IPv6. Its link MTU must accommodate
        # the larger IPv6 return packet; limiting only the IPv4 route reserves
        # the 20-byte translation overhead without black-holing TLS replies.
        run(['ip', 'link', 'set', IFACE, 'mtu', str(config['mtu']), 'up'])
        run(['ip', 'addr', 'add', LOCAL4+'/32', 'dev', IFACE])
        run(['sysctl', '-qw', 'net.ipv6.conf.'+IFACE+'.forwarding=1'])
        for scope in ('all', 'rmnet0'):
            path = '/proc/sys/net/ipv6/conf/'+scope+'/forwarding'
            old = Path(path).read_text().strip()
            change(['sysctl','-qw','net.ipv6.conf.'+scope+'.forwarding=1'],
                   ['sysctl','-qw','net.ipv6.conf.'+scope+'.forwarding='+old])
        run(['ip','-6','route','add',LOCAL6+'/128','dev',IFACE])
        rule = ['priority','30602','from',LOCAL6+'/128','table','106']
        change(['ip','-6','rule','add',*rule],['ip','-6','rule','del',*rule])
        # Default metric keeps Wi-Fi preferred; sharing installs its own iif rule.
        change(['ip','-4','route','add','default','dev',IFACE,'metric','2100',
                'mtu',str(config['mtu'] - 20)],
               ['ip','-4','route','del','default','dev',IFACE,'metric','2100'])
        rule = ['-s',LOCAL6+'/128','-o','rmnet0','-j','SNAT','--to-source',config['sources']['6']]
        change(['ip6tables','-w','-t','nat','-A','POSTROUTING',*rule],
               ['ip6tables','-w','-t','nat','-D','POSTROUTING',*rule])
        for rule in [f'iifname "{IFACE}" oifname "rmnet0" ip6 saddr {LOCAL6} ip6 daddr {prefix} accept',
                     f'iifname "rmnet0" oifname "{IFACE}" ip6 daddr {LOCAL6} ct state established,related accept']:
            subprocess.run(['nft','-f','-'], input='insert rule inet nuxel_app_firewall forward '+rule+' comment "'+TAG+'"\n',text=True,capture_output=True,check=True,timeout=5)
        doc['active']=True;save(doc)
    except BaseException:
        down();raise

if __name__ == '__main__':
    import sys
    if os.geteuid() != 0: raise SystemExit('requires root')
    if sys.argv[1:] == ['down']:
        down()
    elif sys.argv[1:] == ['apply']:
        data = json.loads((ROOT/'cellular-link.json').read_text())
        if not data.get('configured') or data['config']['iface'] != 'rmnet0':
            raise SystemExit('cellular bearer is not configured')
        apply(data['config'])
    else: raise SystemExit('expected apply or down')
