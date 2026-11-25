"""Owned DHCP/DNS and cellular policy routing for the two sharing links.

USB addressing/gadget ownership remains with the existing management service.
DNS forwarding is explicitly bound to rmnet0. No host default route is changed.
"""
import json
import os
import pwd
import grp
from pathlib import Path
import signal
import subprocess
import time
import fcntl

KINDS = {'usb': ('usb0', '10.100.10.1', '10.100.10', 108, 30508),
         'hotspot': ('wlan1', '10.42.0.1', '10.42.0', 107, 30507)}
COMMON = Path('/run/nuxel-sharing-common')


def run(*args, check=True):
    p=subprocess.run(args,capture_output=True,text=True,timeout=8)
    if check and p.returncode: raise RuntimeError(p.stderr.strip() or 'sharing command failed')
    return p


def root(kind): return Path('/run/nuxel-sharing-'+kind)


def forwarding(kind, upstream=None):
    """Restore the original sysctls after the last sharing owner leaves."""
    base = COMMON
    base.mkdir(mode=0o700, exist_ok=True)
    with (base / 'lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        path = base / 'forwarding.json'
        saved = json.loads(path.read_text()) if path.exists() else {'owners': {}, 'original': {}}
        if upstream:
            keys = ['net.ipv4.ip_forward'] + ['net.ipv4.conf.' + iface + '.rp_filter'
                    for iface in (KINDS[kind][0], upstream)]
            for key in keys:
                if key not in saved['original']:
                    saved['original'][key] = run('sysctl', '-n', key).stdout.strip()
            saved['owners'][kind] = keys
            path.write_text(json.dumps(saved))
            for key in keys:
                run('sysctl', '-qw', key + ('=1' if key.endswith('ip_forward') else '=2'))
        else:
            saved['owners'].pop(kind, None)
            needed = {key for keys in saved['owners'].values() for key in keys}
            for key in list(saved['original']):
                if key not in needed:
                    # A bearer transition may have removed its temporary netdev.
                    run('sysctl', '-qw', key + '=' + saved['original'].pop(key), check=False)
            if saved['owners']: path.write_text(json.dumps(saved))
            else: path.unlink(missing_ok=True)


def stop_dns(kind):
    base=root(kind)
    try:
        pid=int((base/'dnsmasq.pid').read_text())
        cmd=Path('/proc/'+str(pid)+'/cmdline').read_bytes()
        if ('--conf-file='+str(base/'dnsmasq.conf')).encode() not in cmd:
            raise RuntimeError('DNS process identity mismatch')
        os.kill(pid,signal.SIGTERM)
        for _ in range(20):
            if not Path('/proc/'+str(pid)).exists(): break
            time.sleep(.05)
    except (FileNotFoundError, ProcessLookupError): pass
    (base/'dnsmasq.pid').unlink(missing_ok=True)


def firewall(kind, upstream=None):
    tag = 'nuxel-sharing-' + kind
    for chain in ('input', 'forward'):
        result = run('nft', '-j', 'list', 'chain', 'inet', 'nuxel_app_firewall', chain, check=False)
        if result.returncode: raise RuntimeError('System firewall is unavailable')
        for item in json.loads(result.stdout)['nftables']:
            r = item.get('rule', {})
            if r.get('comment') == tag:
                run('nft','delete','rule','inet','nuxel_app_firewall',chain,'handle',str(r['handle']))
    if upstream is None: return
    iface, address, subnet, _, _ = KINDS[kind]
    up = upstream['interface']
    rules = [('input', f'iifname "{iface}" udp dport {{ 53, 67 }} accept'),
             ('input', f'iifname "{iface}" tcp dport 53 accept'),
             ('forward', f'iifname "{iface}" oifname "{up}" ip saddr {subnet}.0/24 accept'),
             ('forward', f'iifname "{up}" oifname "{iface}" ip daddr {subnet}.0/24 ct state established,related accept')]
    for chain, rule in rules:
        subprocess.run(['nft','-f','-'], input=f'insert rule inet nuxel_app_firewall {chain} {rule} comment "{tag}"\n', text=True, capture_output=True, check=True, timeout=8)


def stop(kind):
    iface, address, subnet, table, priority = KINDS[kind]
    base=root(kind)
    if not (base/'owner.json').exists(): return
    stop_dns(kind)
    firewall(kind)
    run('ip','-4','rule','del','priority',str(priority),'iif',iface,'table',str(table),check=False)
    run('ip','-4','route','flush','table',str(table),check=False)
    (base/'owner.json').unlink(missing_ok=True)
    forwarding(kind)


def start(kind, upstream):
    iface, address, subnet, table, priority = KINDS[kind]
    base=root(kind);base.mkdir(mode=0o755,exist_ok=True)
    # dnsmasq drops privileges. Only its lease directory is writable by that
    # user; route ownership and configuration remain root-controlled.
    base.chmod(0o755)
    lease_dir = base / 'leases.d'
    lease_dir.mkdir(mode=0o750, exist_ok=True)
    daemon = pwd.getpwnam('dnsmasq')
    os.chown(lease_dir, daemon.pw_uid, daemon.pw_gid)
    if (base/'owner.json').exists(): stop(kind)
    routes=run('ip','-j','-4','route','show','table',str(table),check=False)
    rules=json.loads(run('ip','-j','-4','rule','show').stdout)
    if (routes.returncode == 0 and json.loads(routes.stdout)) or any(r.get('priority')==priority for r in rules):
        raise RuntimeError('sharing routing table/priority already owned')
    if not upstream['available'] or not upstream['dns']: raise RuntimeError('no cellular upstream')
    (base/'owner.json').write_text(json.dumps({'upstream':upstream['interface'],'dns':upstream['dns']}))
    try:
        forwarding(kind, upstream['interface'])
        # The terminal unreachable route prevents accidental Wi-Fi/VPN fallback.
        run('ip','-4','route','add','unreachable','default','metric','32760','table',str(table))
        run('ip','-4','route','add','default','dev',upstream['interface'],'metric','100','mtu',str(upstream.get('mtu', 1480)),'table',str(table))
        run('ip','-4','rule','add','priority',str(priority),'iif',iface,'table',str(table))
        conf = '\n'.join(['interface='+iface, 'bind-interfaces', 'listen-address='+address,
            'except-interface=lo', 'no-resolv', 'no-hosts', 'domain-needed', 'stop-dns-rebind',
            'dhcp-range='+subnet+'.20,'+subnet+'.60,255.255.255.0,1h',
            'dhcp-option=option:router,'+address, 'dhcp-option=option:dns-server,'+address,
            'user=dnsmasq', 'group='+grp.getgrgid(daemon.pw_gid).gr_name,
            'dhcp-leasefile='+str(lease_dir/'leases'), 'pid-file='+str(base/'dnsmasq.pid'),
            'log-facility='+str(base/'dnsmasq.log')]+['server='+dns+'@rmnet0' for dns in upstream['dns']])+'\n'
        (base/'dnsmasq.conf').write_text(conf)
        firewall(kind, upstream)
        run('dnsmasq','--test','--conf-file='+str(base/'dnsmasq.conf'))
        run('dnsmasq','--conf-file='+str(base/'dnsmasq.conf'))
    except BaseException:
        stop(kind);raise


def refresh(kind, upstream):
    """Restore the route when a new bearer recreates nuxclat; never use Wi-Fi."""
    iface, address, subnet, table, priority=KINDS[kind]
    base=root(kind)
    if not (base/'owner.json').exists(): return
    old=json.loads((base/'owner.json').read_text())
    if not upstream['available']:
        run('ip','-4','route','del','default','metric','100','table',str(table),check=False)
        return
    if old['upstream'] != upstream['interface'] or old['dns'] != upstream['dns']:
        start(kind,upstream)
    else:
        run('ip','-4','route','replace','default','dev',upstream['interface'],'metric','100','mtu',str(upstream.get('mtu', 1480)),'table',str(table))
