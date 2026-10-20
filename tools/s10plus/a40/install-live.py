#!/usr/bin/env python3
"""Atomic, reversible userspace-only A40 monitor installer (runs on phone)."""
import hashlib, json, os, shutil, subprocess, sys, time
from pathlib import Path
from urllib.error import URLError
from urllib.request import urlopen

ROOT = Path(sys.argv[1]).resolve()
ALLOWED = ('/usr/share/nuxel/pwa/nuxel-home/', '/usr/lib/nuxel/nuxel-metricsd', '/usr/bin/nuxel-bridge', '/usr/libexec/nuxel/nuxel-sound-cue',
           '/etc/systemd/system/nuxel-metrics.', '/etc/systemd/system/nuxel-boot-sound.service')
receipt = {'started_at': time.time(), 'status': 'PREPARING', 'files': []}
backup = Path('/var/lib/nuxel/a40-monitor') / time.strftime('%Y%m%dT%H%M%SZ', time.gmtime())

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()
def save():
    tmp = backup / 'receipt.json.tmp'; backup.mkdir(parents=True, exist_ok=True)
    tmp.write_text(json.dumps(receipt, indent=2)+'\n'); tmp.replace(backup/'receipt.json')
def safe(path):
    value = str(path)
    return ('..' not in path.parts and (value == '/usr/lib/nuxel/nuxel-metricsd' or value == '/usr/bin/nuxel-bridge' or value == '/usr/libexec/nuxel/nuxel-sound-cue' or
            value == '/etc/systemd/system/nuxel-boot-sound.service' or
            value.startswith('/usr/share/nuxel/pwa/nuxel-home/') or
            value.startswith('/usr/share/nuxel/assets/nuxel-applications-icon-pack/') or
            value.startswith('/usr/share/nuxel/assets/nuxel-quicksettings-icon-pack/') or
            value in ('/usr/share/nuxel/assets/button-left.png', '/usr/share/nuxel/assets/button-middle.png', '/usr/share/nuxel/assets/button-right.png') or
            value.startswith('/etc/systemd/system/nuxel-metrics.')))
def http_bytes(url):
    """Read an active launcher endpoint, allowing its host to come back up.

    Restarting nuxel-wayland deliberately terminates the child PWA host.  The
    host normally binds 127.0.0.1:8000 a moment later, so a one-shot request
    immediately after the restart turned a good atomic install into an
    unnecessary rollback.  Retry only connection-level startup failures; a
    non-200 response remains a failed verification.
    """
    deadline = time.monotonic() + 20
    while True:
        try:
            with urlopen(url, timeout=8) as response:
                if response.status != 200:
                    raise RuntimeError('unexpected HTTP status for '+url+': '+str(response.status))
                return response.read(), response.headers
        except URLError:
            if time.monotonic() >= deadline:
                raise
            time.sleep(0.5)
def verify_running_payload(rows):
    # Filesystem hashes prove atomic installation; these requests prove the
    # active nuxel-web document root serves the same bytes to WebKitGTK.
    served = []
    for row in rows:
        target = Path(row['path'])
        try:
            relative = target.relative_to('/usr/share/nuxel')
        except ValueError:
            continue
        body, _ = http_bytes('http://127.0.0.1:8000/' + str(relative))
        if hashlib.sha256(body).hexdigest() != row['sha256']:
            raise RuntimeError('served hash mismatch '+str(target))
        served.append(str(target))
    body, headers = http_bytes('http://127.0.0.1:8624/metrics')
    metrics = json.loads(body.decode('utf-8'))
    required = {'cpu_percent', 'cpu_status', 'cpu_frequency_mhz',
                'memory_percent', 'memory_status', 'memory_used_kib',
                'memory_total_kib', 'gpu_percent', 'gpu_status',
                'gpu_frequency_mhz', 'gpu_memory_kib', 'gpu_memory_total_kib',
                'gpu_memory_status'}
    if not required.issubset(metrics):
        raise RuntimeError('metrics response missing required fields')
    if headers.get('Access-Control-Allow-Origin') != 'http://127.0.0.1:8000':
        raise RuntimeError('metrics CORS origin does not match the active launcher')
    receipt['served_paths'] = served
    receipt['metrics_snapshot'] = metrics

try:
    manifest = json.loads((ROOT/'manifest.json').read_text())
    for row in manifest:
        target = Path(row['path'])
        src = ROOT/'files'/str(target).lstrip('/')
        if not safe(target) or not src.is_file() or digest(src) != row['sha256']:
            raise RuntimeError('invalid payload member '+str(target))
        if target.is_symlink(): raise RuntimeError('refusing symlink target '+str(target))
        old = digest(target) if target.exists() else None
        b = backup/'backup'/str(target).lstrip('/')
        if target.exists(): b.parent.mkdir(parents=True, exist_ok=True); shutil.copy2(target, b)
        row.update({'old_sha256': old, 'backup': str(b), 'existed': target.exists()})
        receipt['files'].append(row)
    save()
    changed=[]
    for row in receipt['files']:
        target=Path(row['path']); src=ROOT/'files'/str(target).lstrip('/')
        target.parent.mkdir(parents=True, exist_ok=True)
        staged=target.with_name(target.name+'.a40-stage')
        shutil.copyfile(src, staged); staged.chmod(row['mode']); os.replace(staged, target)
        if digest(target) != row['sha256']: raise RuntimeError('install hash mismatch '+str(target))
        changed.append(row)
    subprocess.run(['systemctl', 'daemon-reload'], check=True, timeout=15)
    subprocess.run(['systemctl', 'enable', '--now', 'nuxel-metrics.socket'], check=True, timeout=20)
    subprocess.run(['systemctl', 'try-restart', 'nuxel-bridge.service'], check=True, timeout=20)
    # A socket-activated instance can still be resident from the previous Home
    # poll while its executable has just been atomically replaced.  Restart only
    # that service so the very next snapshot is generated by the new binary.
    subprocess.run(['systemctl', 'try-restart', 'nuxel-metrics.service'], check=True, timeout=15)
    # Migrate the enablement link as well as the unit contents. Otherwise an
    # older multi-user.target.wants symlink keeps the nonessential sound probe
    # on the boot critical path even though the new unit declares a later owner.
    subprocess.run(['systemctl', 'disable', 'nuxel-boot-sound.service'], check=True, timeout=15)
    subprocess.run(['systemctl', 'enable', 'nuxel-boot-sound.service'], check=True, timeout=15)
    # The old unverified boot cue is known to have failed.  Clear only that
    # stale result after the verified-gate unit is installed; never mask audio
    # diagnostics or any unrelated failed unit.
    subprocess.run(['systemctl', 'reset-failed', 'nuxel-boot-sound.service'], check=True, timeout=15)
    # This reloads the only resident WebKit surface so the new SW version and
    # code are actually active. nuxel-wayland's existing restart policy keeps
    # the USB recovery console independent and intact.
    subprocess.run(['systemctl', 'restart', 'nuxel-wayland'], check=True, timeout=40)
    subprocess.run(['systemctl', 'is-active', '--quiet', 'nuxel-wayland', 'nuxel-wl-fb', 'nuxel-metrics.socket', 'nuxel-bridge', 'nuxel-http-bridge'], check=True, timeout=10)
    verify_running_payload(receipt['files'])
    receipt['status']='DEPLOYED_UNVERIFIED'; save()
except Exception as error:
    receipt['error']=str(error)
    for row in reversed(receipt['files']):
        target=Path(row['path']); b=Path(row['backup'])
        try:
            if row['existed'] and b.is_file():
                staged=target.with_name(target.name+'.a40-restore'); shutil.copy2(b, staged); os.replace(staged,target)
            elif not row['existed']: target.unlink(missing_ok=True)
        except Exception as restore_error: receipt.setdefault('restore_errors',[]).append(str(restore_error))
    try: subprocess.run(['systemctl','daemon-reload'], check=False, timeout=15); subprocess.run(['systemctl','restart','nuxel-wayland'],check=False,timeout=40)
    except Exception as restart_error: receipt['rollback_restart_error']=str(restart_error)
    receipt['status']='ROLLED_BACK'; save()
finally:
    receipt['finished_at']=time.time(); save()
print(json.dumps(receipt, indent=2))
sys.exit(0 if receipt['status']=='DEPLOYED_UNVERIFIED' else 5)
