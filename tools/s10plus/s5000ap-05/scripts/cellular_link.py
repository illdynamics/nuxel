#!/usr/bin/python3
"""Configure one raw-IP bearer using Linux iproute2 and systemd-resolved.

The radio daemon supplies CP-decoded addresses. No APN, NV, modem command,
global DNS file or other network interface is modified here. An undo journal
precedes every mutation and survives a helper/daemon crash. Route table 106,
rule priorities 30600/30601 and metric 2100 are reserved for this bearer.
"""
import fcntl
import ipaddress
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
import tempfile
import time

STATE_DIR = Path('/run/nuxel-radio')
IP = '/usr/sbin/ip'
RESOLVECTL = '/usr/bin/resolvectl'
BUSCTL = '/usr/bin/busctl'


class LinkError(RuntimeError):
    pass


def run(argv, check=True):
    result = subprocess.run(argv, capture_output=True, text=True, timeout=15,
                            env={'PATH': '/usr/sbin:/usr/bin', 'LC_ALL': 'C'})
    if check and result.returncode:
        raise LinkError(f'{Path(argv[0]).name} failed ({result.returncode}): {result.stderr.strip()}')
    return result


def query(argv):
    return json.loads(run(argv).stdout)


def resolved_available():
    """systemd-resolved is optional: Nuxel normally runs NetworkManager for
    DNS and /etc/resolv.conf is a plain file. When resolve1 is absent the
    helper configures addresses/routes only and never touches the resolver.
    This keeps cellular bring-up working instead of failing on a missing
    org.freedesktop.resolve1 name."""
    result = run([BUSCTL, '--address=unix:path=/run/systemd/resolve/io.systemd.Resolve',
                  'list', '--no-legend', '--no-pager'], check=False)
    if result.returncode:
        result = run([BUSCTL, 'list', '--no-legend', '--no-pager'], check=False)
        if result.returncode:
            return False
        return 'org.freedesktop.resolve1' in result.stdout
    return True


def configuration(args):
    if len(args) != 10 or args[0] != 'rmnet0' or args[1] != '1':
        raise LinkError('unsupported interface/CID mapping; beyond2lte CID1 is rmnet0')
    iface, cid, v4, prefix, v6, d41, d42, d61, d62, mtu = args
    prefix, mtu = int(prefix), int(mtu)
    if not 0 <= prefix <= 32 or not 1280 <= mtu <= 1500:
        raise LinkError('invalid prefix or MTU')
    addresses, sources, dns = [], {}, []
    for family, value, bits in ((4, v4, prefix), (6, v6, 64)):
        if value == '-':
            continue
        address = ipaddress.ip_address(value)
        if address.version != family or address.is_unspecified or address.is_multicast or address.is_loopback or address.is_link_local:
            raise LinkError('unusable cellular address')
        addresses.append(f'{address}/{bits}')
        sources[str(family)] = str(address)
        if family == 6:
            # Interface::BringUp @0x2dcf30 preserves the CP interface ID.
            ll = ipaddress.IPv6Address(int(ipaddress.IPv6Address('fe80::')) | (int(address) & ((1 << 64) - 1)))
            addresses.append(f'{ll}/64')
    for family, value in ((4, d41), (4, d42), (6, d61), (6, d62)):
        if value == '-':
            continue
        address = ipaddress.ip_address(value)
        if address.is_unspecified:
            continue
        if address.version != family or address.is_loopback or address.is_multicast or address.is_link_local:
            raise LinkError('unusable cellular DNS address')
        if str(family) in sources and str(address) not in dns:
            dns.append(str(address))
    if not sources or not dns:
        raise LinkError('CP did not supply a usable address and DNS server')
    return {'iface': iface, 'cid': int(cid), 'mtu': mtu, 'addresses': addresses,
            'sources': sources, 'dns': dns}


class Link:
    def __init__(self, state_dir=STATE_DIR):
        self.path = state_dir / 'cellular-link.json'
        self.journal = None

    def read(self):
        try:
            fd = os.open(self.path, os.O_RDONLY | os.O_NOFOLLOW)
        except FileNotFoundError:
            return None
        with os.fdopen(fd) as f:
            mode = os.fstat(f.fileno())
            if not stat.S_ISREG(mode.st_mode) or mode.st_mode & 0o077 or mode.st_uid != os.geteuid():
                raise LinkError('unsafe link journal')
            data = json.load(f)
        if data.get('version') != 1 or data.get('config', {}).get('iface') != 'rmnet0':
            raise LinkError('unknown link journal')
        self.journal = data
        return data

    def save(self):
        fd, name = tempfile.mkstemp(prefix='.link-', dir=self.path.parent)
        try:
            with os.fdopen(fd, 'w') as f:
                json.dump(self.journal, f, sort_keys=True)
                f.flush()
                os.fsync(f.fileno())
            os.replace(name, self.path)
            self.sync_dir()
        finally:
            if os.path.exists(name):
                os.unlink(name)

    def sync_dir(self):
        fd = os.open(self.path.parent, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(fd)
        finally:
            os.close(fd)

    def change(self, forward, undo, absent_ok=False):
        self.journal['undo'].append({'argv': undo, 'absent_ok': absent_ok})
        self.save()  # intent must reach the journal before the kernel mutation
        run(forward)

    def down(self):
        if self.journal is None and not self.read():
            return
        self.journal['configured'] = False
        self.save()
        # Stop on an undo failure: retain the entire unprocessed journal for
        # a later recovery, rather than falsely reporting a successful stop.
        while self.journal['undo']:
            entry = self.journal['undo'][-1]
            result = run(entry['argv'], check=False)
            absent = any(s in result.stderr for s in ('Cannot assign requested address', 'No such process', 'No such file or directory', 'Cannot find device', 'does not exist'))
            if result.returncode and not (entry['absent_ok'] and absent):
                raise LinkError(f'link rollback failed: {result.stderr.strip()}')
            self.journal['undo'].pop()
            self.save()
        self.path.unlink()
        self.sync_dir()
        self.journal = None

    @staticmethod
    def resolver_dns(index):
        if not resolved_available():
            return []
        # Object paths use D-Bus escaping (e.g. index 4 is _34), not _4.
        obj = query([BUSCTL, '--json=short', 'call', 'org.freedesktop.resolve1',
                     '/org/freedesktop/resolve1', 'org.freedesktop.resolve1.Manager',
                     'GetLink', 'i', str(index)])['data'][0]
        value = query([BUSCTL, '--json=short', 'get-property', 'org.freedesktop.resolve1',
                       obj, 'org.freedesktop.resolve1.Link', 'DNS'])
        return [str(ipaddress.ip_address(bytes(record[1]))) for record in value['data']]

    def verify(self, config):
        iface = config['iface']
        links = query([IP, '-j', 'address', 'show', 'dev', iface])
        if len(links) != 1 or 'UP' not in links[0]['flags'] or links[0]['mtu'] != config['mtu']:
            raise LinkError('cellular link state or MTU mismatch')
        entries = links[0]['addr_info']
        for address in config['addresses']:
            value, bits = address.split('/')
            matches = [a for a in entries if a['local'] == value and a['prefixlen'] == int(bits)]
            if len(matches) != 1 or any(matches[0].get(k) for k in ('tentative', 'dadfailed')):
                raise LinkError('cellular address verification failed')
        for family, source in config['sources'].items():
            routes = query([IP, '-j', f'-{family}', 'route', 'show', 'table', '106'])
            if not any(r.get('dst') == 'default' and r.get('dev') == iface and r.get('prefsrc') == source and r.get('metric') == 2100 for r in routes):
                raise LinkError('cellular policy route missing')
            rules = query([IP, '-j', f'-{family}', 'rule', 'show'])
            source_ok = any(r.get('priority') == 30600 and str(r.get('table')) == '106' and r.get('src', '').split('/')[0] == source for r in rules)
            iface_ok = any(r.get('priority') == 30601 and str(r.get('table')) == '106' and r.get('oif') == iface for r in rules)
            if not source_ok or not iface_ok:
                raise LinkError('cellular policy rules missing')
            main = query([IP, '-j', f'-{family}', 'route', 'show', 'table', 'main'])
            if not any(r.get('dst') == 'default' and r.get('dev') == iface and r.get('metric') == 2100 for r in main):
                raise LinkError('cellular default route missing')
        if resolved_available() and self.resolver_dns(links[0]['ifindex']) != config['dns']:
            raise LinkError('cellular DNS verification failed')

    def apply(self, config):
        prior = self.read()
        if prior and prior['config'] == config and prior['configured']:
            try:
                self.verify(config)
                return
            except LinkError:
                pass
        if prior:
            self.down()
        iface = config['iface']
        # Interface existence must be independent of its administrative/UP
        # state. A raw-IP bearer is reported by the CP while the kernel link is
        # still DOWN; `ip -j address show` omits address-less interfaces, so the
        # existence/ifindex check uses `ip link`, not `ip address`.
        links = query([IP, '-j', 'link', 'show', 'dev', iface])
        if len(links) != 1:
            raise LinkError('cellular interface absent')
        link = links[0]
        addrs = query([IP, '-j', 'address', 'show', 'dev', iface])
        addr_info = addrs[0]['addr_info'] if addrs else []
        if any(a.get('scope') == 'global' for a in addr_info):
            raise LinkError('unowned cellular address exists')
        if self.resolver_dns(link['ifindex']):
            raise LinkError('unowned cellular DNS exists')
        for family in ('4', '6'):
            # "table ... does not exist" is an ordinary empty IPv4/IPv6 FIB.
            result = run([IP, '-j', f'-{family}', 'route', 'show', 'table', '106'], check=False)
            if result.returncode and 'FIB table does not exist' not in result.stderr:
                raise LinkError('cannot inspect reserved route table')
            if result.returncode == 0 and json.loads(result.stdout):
                raise LinkError('reserved route table already in use')
            rules = query([IP, '-j', f'-{family}', 'rule', 'show'])
            if any(r.get('priority') in (30600, 30601) for r in rules):
                raise LinkError('reserved rule priority already in use')
        self.journal = {'version': 1, 'config': config, 'configured': False,
                        'started_monotonic': time.monotonic(), 'undo': []}
        self.save()
        try:
            self.change([IP, 'link', 'set', 'dev', iface, 'mtu', str(config['mtu']), 'up'],
                        [IP, 'link', 'set', 'dev', iface, 'mtu', str(link['mtu']), 'up' if 'UP' in link['flags'] else 'down'])
            existing = {f"{a['local']}/{a['prefixlen']}" for a in addr_info}
            for address in config['addresses']:
                if address in existing:
                    continue  # an existing link-local address is not ours
                family = str(ipaddress.ip_interface(address).version)
                args = [IP, f'-{family}', 'address', 'add', address, 'dev', iface]
                if family == '6':
                    args.append('nodad')
                self.change(args, [IP, f'-{family}', 'address', 'del', address, 'dev', iface], True)
            for family, source in config['sources'].items():
                for table in ('106', 'main'):
                    spec = ['table', table, 'default', 'dev', iface, 'metric', '2100', 'src', source, 'proto', '186']
                    self.change([IP, f'-{family}', 'route', 'add'] + spec, [IP, f'-{family}', 'route', 'del'] + spec, True)
                for spec in (['priority', '30600', 'from', source + ('/128' if family == '6' else '/32'), 'lookup', '106'],
                             ['priority', '30601', 'oif', iface, 'lookup', '106']):
                    self.change([IP, f'-{family}', 'rule', 'add'] + spec, [IP, f'-{family}', 'rule', 'del'] + spec, True)
            if resolved_available():
                self.change([RESOLVECTL, 'dns', iface] + config['dns'], [RESOLVECTL, 'revert', iface], True)
                run([RESOLVECTL, 'default-route', iface, 'yes'])
            self.verify(config)
            self.journal['configured'] = True
            self.save()
        except BaseException:
            self.down()
            raise


def main():
    if os.geteuid() != 0:
        raise LinkError('requires root')
    STATE_DIR.mkdir(mode=0o700, parents=True, exist_ok=True)
    info = STATE_DIR.lstat()
    if not stat.S_ISDIR(info.st_mode) or info.st_uid != 0 or info.st_mode & 0o022:
        raise LinkError('unsafe runtime directory')
    fd = os.open(STATE_DIR / 'cellular-link.lock', os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, 'w') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        # S5000AP exposes raw IP as ARPHRD_PPP. NM 1.54's PPP device only
        # accepts PPPoE and cannot activate a generic profile on this link.
        # Keep one L3 owner: the existing journalled native helper for this
        # hardware, with resolved shared by NM's Wi-Fi and cellular DNS.
        if Path('/sys/class/net/rmnet0/type').read_text().strip() == '512':
            if sys.argv[1:2] == ['apply'] and not resolved_available():
                raise LinkError('native raw-IP requires systemd-resolved for carrier DNS')
            link = Link()
        else:
            from cellular_nm import NetworkManagerLink
            link = NetworkManagerLink()
        if len(sys.argv) > 1 and sys.argv[1] == 'apply':
            link.apply(configuration(sys.argv[2:]))
        elif sys.argv[1:] == ['down']:
            link.down()
        elif sys.argv[1:] == ['check']:
            data = link.read()
            if not data or not data['configured']:
                raise LinkError('no configured cellular link')
            link.verify(data['config'])
        else:
            raise LinkError('expected apply, down or check')


if __name__ == '__main__':
    try:
        main()
    except (OSError, ValueError, KeyError, LinkError, subprocess.SubprocessError) as error:
        print(f'nuxel-cellular-link: {error}', file=sys.stderr)
        sys.exit(1)
