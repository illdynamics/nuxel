#!/usr/bin/python3
"""NetworkManager is the sole L3/DNS owner for a CP-established CID1 bearer.

Radio1 owns modem commands and reconnect policy. Profiles are temporary and
never autoconnect: only a fresh CP IP report may activate them. The existing
write-ahead journal also rolls back pre-NM helper configuration on upgrade.
"""
import ipaddress
import time
from pathlib import Path
from cellular_link import Link, LinkError, IP, query, run

NMCLI = '/usr/bin/nmcli'
UUID = '8ba40bd5-cc4c-4a12-96c5-757170a1d106'


def profile_args(config):
    args = [NMCLI, 'connection', 'add', 'save', 'no', 'type', 'generic',
            'ifname', 'rmnet0', 'con-name', 'Nuxel native LTE',
            'connection.uuid', UUID, 'connection.autoconnect', 'no',
            'connection.metered', 'yes', 'generic.device-handler', 'nuxel-cellular']
    for family in ('4', '6'):
        prefix = 'ipv' + family
        addresses = [a for a in config['addresses'] if str(ipaddress.ip_interface(a).version) == family]
        dns = [a for a in config['dns'] if str(ipaddress.ip_address(a).version) == family]
        if family not in config['sources']:
            args += [prefix + '.method', 'disabled']
            continue
        source = config['sources'][family]
        default = '0.0.0.0/0' if family == '4' else '::/0'
        route = default + ' 2100 src=' + source
        args += [prefix + '.method', 'manual', prefix + '.addresses', ','.join(addresses),
                 prefix + '.dns', ','.join(dns), prefix + '.dns-priority', '2100',
                 prefix + '.route-metric', '2100', prefix + '.may-fail', 'no',
                 prefix + '.ignore-auto-dns', 'yes', prefix + '.ignore-auto-routes', 'yes',
                 prefix + '.routes', route + ', ' + route + ' table=106',
                 prefix + '.routing-rules', 'priority 30600 from ' + source +
                 ' table 106, priority 30601 oif rmnet0 table 106']
    return args


class NetworkManagerLink(Link):
    def down(self):
        if self.journal is None:
            self.read()
        if self.journal and self.journal.get('engine') != 'NetworkManager':
            return super().down()
        # A crash after profile creation but before journal completion is safe:
        # the reserved UUID is always reconciled, even without a journal.
        profiles = run([NMCLI, '-g', 'UUID', 'connection', 'show']).stdout.splitlines()
        if UUID in profiles:
            run([NMCLI, '--wait', '10', 'connection', 'delete', 'uuid', UUID])
        if self.journal:
            # Delete completion may precede kernel deconfiguration. Retain the
            # journal and report failure if NM leaves our configuration behind.
            deadline = time.monotonic() + 5
            while True:
                addresses = query([IP, '-j', 'address', 'show', 'dev', 'rmnet0'])
                owned = set(self.journal['config']['sources'].values())
                remaining = any(a.get('local') in owned for item in addresses for a in item['addr_info'])
                for family in ('4', '6'):
                    routes = query([IP, '-j', '-' + family, 'route', 'show', 'dev', 'rmnet0'])
                    remaining = remaining or any(r.get('metric') == 2100 for r in routes)
                if not remaining:
                    break
                if time.monotonic() >= deadline:
                    raise LinkError('NetworkManager cellular cleanup incomplete')
                time.sleep(0.2)
            old_mtu = self.journal.get('old_mtu', 1500)
            run([IP, 'link', 'set', 'dev', 'rmnet0', 'mtu', str(old_mtu), 'down'])
            self.path.unlink()
            self.sync_dir()
            self.journal = None

    def verify(self, config):
        active = run([NMCLI, '-g', 'UUID,DEVICE', 'connection', 'show', '--active']).stdout
        if UUID + ':rmnet0' not in active.splitlines():
            raise LinkError('native cellular NetworkManager connection is not active on rmnet0')
        # Same kernel address/source-routing checks as the established helper;
        # DNS is checked against NM, which owns the host resolver here.
        links = query([IP, '-j', 'address', 'show', 'dev', 'rmnet0'])
        if not links or 'UP' not in links[0]['flags']:
            raise LinkError('cellular link is not up')
        for address in config['addresses']:
            value, bits = address.split('/')
            if not any(a['local'] == value and a['prefixlen'] == int(bits) and
                       not a.get('tentative') and not a.get('dadfailed') for a in links[0]['addr_info']):
                raise LinkError('cellular address verification failed')
        for family, source in config['sources'].items():
            for table in ('main', '106'):
                routes = query([IP, '-j', '-' + family, 'route', 'show', 'table', table])
                if not any(r.get('dst') == 'default' and r.get('dev') == 'rmnet0' and
                           r.get('metric') == 2100 and r.get('prefsrc') == source for r in routes):
                    raise LinkError('cellular source/default route missing')
            rules = query([IP, '-j', '-' + family, 'rule', 'show'])
            if not all(any(r.get('priority') == priority and str(r.get('table')) == '106'
                           for r in rules) for priority in (30600, 30601)):
                raise LinkError('cellular policy rule missing')
        dns = run([NMCLI, '-g', 'IP4.DNS,IP6.DNS', 'connection', 'show', 'uuid', UUID]).stdout
        actual = {str(ipaddress.ip_address(a.replace('\\:', ':'))) for a in dns.splitlines() if a}
        if actual != set(config['dns']):
            raise LinkError('NetworkManager carrier DNS mismatch')

    def apply(self, config):
        previous = self.read()
        if previous and previous.get('engine') == 'NetworkManager' and previous['config'] == config and previous['configured']:
            self.verify(config)
            return
        self.down()
        links = query([IP, '-j', 'link', 'show', 'dev', 'rmnet0'])
        if len(links) != 1:
            raise LinkError('CID1 rmnet0 interface missing')
        addresses = query([IP, '-j', 'address', 'show', 'dev', 'rmnet0'])
        if any(a.get('scope') == 'global' for link in addresses for a in link['addr_info']):
            raise LinkError('unowned cellular addresses exist')
        for family in ('4', '6'):
            result = run([IP, '-j', '-' + family, 'route', 'show', 'table', '106'], check=False)
            if result.returncode and 'FIB table does not exist' not in result.stderr:
                raise LinkError('cannot inspect reserved cellular route table')
            import json
            if not result.returncode and json.loads(result.stdout):
                raise LinkError('reserved cellular route table already in use')
            rules = query([IP, '-j', '-' + family, 'rule', 'show'])
            if any(r.get('priority') in (30600, 30601) for r in rules):
                raise LinkError('reserved cellular rule already in use')
        self.journal = {'version': 1, 'engine': 'NetworkManager', 'config': config,
                        'configured': False, 'old_mtu': links[0]['mtu'], 'undo': []}
        self.save()
        try:
            run([IP, 'link', 'set', 'dev', 'rmnet0', 'mtu', str(config['mtu'])])
            run(profile_args(config))
            run([NMCLI, '--wait', '10', 'connection', 'up', 'uuid', UUID])
            self.verify(config)
            self.journal['configured'] = True
            self.save()
        except BaseException:
            self.down()
            raise
