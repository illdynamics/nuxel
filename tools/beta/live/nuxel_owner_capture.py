#!/usr/bin/env python3
"""Passive, bounded phone-side owner capture. No grabs, injection or framebuffer opens.

Run under a transient systemd service with RuntimeMaxSec=170. Wait for ready.json,
print the owner's instructions, then create OUT/start. The *capture* lasts the full
90 seconds after that signal; setup time is never subtracted. No existing asset or
state file is modified. Logs contain input metadata, never typed text or app data.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import select
import signal
import struct
import subprocess
import time

EVENT = struct.Struct('llHHi')  # target Linux input_event; native userspace ABI
MAX_EVENT_BYTES = 8 * 1024 * 1024
MAX_LOG_BYTES = 2 * 1024 * 1024
LOG_PATHS = ('/run/nuxel-home.state', '/run/nuxel-button-manager.state')
STATE_PATHS = ('/run/nuxel-wl-fb.state', '/run/nuxel-libinput-path.state')


def read(path, limit=65536):
    try:
        with open(path, 'r', errors='replace') as f:
            return f.read(limit)
    except OSError:
        return ''


def write_json(path, obj):
    tmp = path.with_suffix(path.suffix + '.tmp')
    tmp.write_text(json.dumps(obj, indent=2) + '\n')
    tmp.replace(path)


def bit(bitmap, index):
    words = bitmap.split()
    value = int(''.join(w.zfill(struct.calcsize('l') * 2) for w in words), 16) if words else 0
    return bool(value & (1 << index))


def inventory():
    nodes = []
    for p in sorted(Path('/sys/class/input').glob('event*')):
        d = p / 'device'
        name, props, absbits = (read(d / q).strip() for q in ('name', 'properties', 'capabilities/abs'))
        touch = name == 'sec_touchscreen' and bit(props, 1) and all(bit(absbits, b) for b in (53, 54, 57))
        nodes.append({'path': '/dev/input/' + p.name, 'name': name, 'properties': props,
                      'abs': absbits, 'touchscreen': touch, 'buttons': name == 'gpio_keys'})
    return nodes


def safe_log(line):
    # Observe only known event metadata, not console messages, URLs, terminal
    # output, input values, notifications or arbitrary bridge requests.
    match = re.search(r'NUXEL_INPUT EVT (touchstart|touchmove|touchend|pointerdown|pointerup|pointercancel|click|app:launch|app:lifecycle|focusin|input)\b', line)
    if not match:
        return None
    fields = re.findall(r'\b(x|y|tag|id|w|h|dpr|splash|app|state|hit|path|trusted|ts)=([A-Za-z0-9_.:-]+)', line[match.end():])
    prefix = re.match(r'^\d+(?:\.\d+)?', line)
    return {'event': match.group(1), 'fields': dict(fields),
            'source_time': prefix.group(0) if prefix else None}


class Cursor:
    """Start at EOF so a prior boot or trial cannot satisfy this trial."""
    def __init__(self, path):
        self.path, self.pos, self.inode, self.tail = Path(path), 0, None, b''
        try:
            st = self.path.stat()
            self.pos, self.inode = st.st_size, st.st_ino
        except OSError:
            pass

    def lines(self):
        try:
            st = self.path.stat()
            if st.st_ino != self.inode or st.st_size < self.pos:
                self.pos, self.tail = 0, b''
            self.inode = st.st_ino
            with self.path.open('rb') as f:
                f.seek(self.pos)
                data = f.read(65536)
                self.pos = f.tell()
            chunks = (self.tail + data).split(b'\n')
            self.tail = chunks.pop()
            return [x.decode('utf-8', 'replace') for x in chunks]
        except OSError:
            return []


def snapshot():
    services = subprocess.run(['systemctl', 'show', 'nuxel-wayland', 'nuxel-wl-fb',
                               'nuxel-touch-arm', 'nuxel-button-manager',
                               '-p', 'Id', '-p', 'MainPID', '-p', 'ActiveState', '-p', 'SubState'],
                              capture_output=True, text=True, timeout=5)
    clients = []
    for p in Path('/proc').glob('[0-9]*'):
        name = read(p / 'comm').strip()
        if name not in ('phoc', 'nuxel-pwa-host', 'nuxel-wl-fb', 'nuxel-touch-arm'):
            continue
        fds = []
        try:
            for fd in (p / 'fd').iterdir():
                try:
                    dest = os.readlink(fd)
                    if dest.startswith('/dev/input/'):
                        fds.append(dest)
                except OSError:
                    pass
        except OSError:
            pass
        clients.append({'pid': int(p.name), 'name': name, 'input_fds': fds})
    return {'wall_time': time.time(), 'monotonic': time.monotonic(),
            'boot_id': read('/proc/sys/kernel/random/boot_id').strip(),
            'kernel': os.uname().release, 'machine': os.uname().machine,
            'mode': [v for v in read('/proc/cmdline').split() if v.startswith(('androidboot.mode=', 'lpcharge=', 'charging_mode='))],
            'inputs': inventory(), 'irq': [l for l in read('/proc/interrupts').splitlines() if 'sec_ts' in l],
            'services': services.stdout, 'clients': clients,
            'states': {p: read(p) for p in STATE_PATHS}}


def capture(out, seconds=90, arm_wait=60):
    if not 1 <= seconds <= 90 or not 1 <= arm_wait <= 60:
        raise ValueError('bounded to 90 capture seconds and 60 setup seconds')
    out.mkdir(parents=True, exist_ok=False)
    initial = snapshot()
    write_json(out / 'before.json', initial)
    nodes = [n for n in initial['inputs'] if n['touchscreen'] or n['buttons']]
    if 'androidboot.mode=charger' in initial['mode'] or not any(n['touchscreen'] for n in nodes):
        write_json(out / 'receipt.json', {'verdict': 'CAPTURE_BLOCKED', 'reason': 'touchscreen absent or charger boot', 'capture_seconds': 0})
        return 3
    fds = {}
    try:
        for n in nodes:
            fds[os.open(n['path'], os.O_RDONLY | os.O_NONBLOCK | os.O_CLOEXEC)] = n
        cursors = {p: Cursor(p) for p in LOG_PATHS}
        write_json(out / 'ready.json', {'armed_at': time.time(), 'nodes': nodes, 'event_size': EVENT.size,
                                       'wait_for_start_seconds': arm_wait, 'capture_seconds': seconds})
        ready_deadline = time.monotonic() + arm_wait
        while not (out / 'start').exists():
            if time.monotonic() >= ready_deadline:
                write_json(out / 'receipt.json', {'verdict': 'INVALID_CAPTURE', 'reason': 'start signal absent'})
                return 4
            # Drain pre-window input without treating it as owner evidence.
            for fd in select.select(list(fds), [], [], .05)[0]:
                os.read(fd, EVENT.size * 128)
        cursors = {p: Cursor(p) for p in LOG_PATHS}
        start_mono, start_wall = time.monotonic(), time.time()
        deadline = start_mono + seconds
        write_json(out / 'started.json', {'started_wall': start_wall, 'started_monotonic': start_mono,
                                         'deadline_wall': start_wall + seconds, 'seconds': seconds})
        totals = {'events': 0, 'touch_events': 0, 'tracking_down': 0, 'tracking_up': 0,
                  'syn_report': 0, 'syn_dropped': 0, 'dom_events': 0, 'dom_touch_events': 0, 'dom_clicks': 0,
                  'app_launches': 0, 'event_bytes': 0, 'log_bytes': 0}
        errors, buffers, states = [], {fd: b'' for fd in fds}, {}
        next_state = 0
        with (out / 'events.jsonl').open('w') as events, (out / 'timeline.jsonl').open('w') as timeline:
            def emit(stream, obj, key, cap):
                line = json.dumps(obj, separators=(',', ':')) + '\n'
                if totals[key] + len(line) <= cap:
                    stream.write(line)
                    totals[key] += len(line)
                elif 'capture-size-cap' not in errors:
                    errors.append('capture-size-cap')
            while time.monotonic() < deadline:
                now = time.monotonic()
                for fd in select.select(list(fds), [], [], min(.05, max(0, deadline - now)))[0]:
                    data = os.read(fd, EVENT.size * 256)
                    if not data:
                        raise OSError('input device returned EOF')
                    data = buffers[fd] + data
                    end = len(data) - len(data) % EVENT.size
                    buffers[fd] = data[end:]
                    for offset in range(0, end, EVENT.size):
                        sec, usec, typ, code, value = EVENT.unpack_from(data, offset)
                        node = fds[fd]
                        totals['events'] += 1
                        if node['touchscreen']:
                            totals['touch_events'] += 1
                            if typ == 3 and code == 57:
                                totals['tracking_down' if value >= 0 else 'tracking_up'] += 1
                            if typ == 0 and code in (0, 3):
                                totals['syn_report' if code == 0 else 'syn_dropped'] += 1
                        emit(events, {'kernel_time': sec + usec / 1e6, 'received_monotonic': time.monotonic(),
                                      'source': node['name'], 'type': typ, 'code': code, 'value': value},
                             'event_bytes', MAX_EVENT_BYTES)
                for path, cursor in cursors.items():
                    for line in cursor.lines():
                        obj = safe_log(line)
                        if obj:
                            totals['dom_events'] += 1
                            totals['dom_touch_events'] += obj['event'] in ('touchstart', 'touchmove', 'touchend', 'pointerdown', 'pointerup')
                            totals['dom_clicks'] += obj['event'] == 'click'
                            totals['app_launches'] += obj['event'] == 'app:launch'
                            emit(timeline, dict(obj, path=path, observed_monotonic=time.monotonic(), wall_time=time.time()),
                                 'log_bytes', MAX_LOG_BYTES)
                if now >= next_state:
                    for path in STATE_PATHS:
                        value = read(path)
                        if value != states.get(path):
                            emit(timeline, {'path': path, 'state': value, 'observed_monotonic': time.monotonic(), 'wall_time': time.time()},
                                 'log_bytes', MAX_LOG_BYTES)
                            states[path] = value
                    next_state = now + .25
        end_mono, end_wall = time.monotonic(), time.time()
        if any(buffers.values()) or totals['syn_dropped']:
            errors.append('incomplete-or-dropped-input')
        verdict = ('INVALID_CAPTURE' if errors else
                   'NO_PHYSICAL_EVENT_RECORDED' if not totals['tracking_down'] else
                   'EVENTS_RECORDED_BUT_NOT_FORWARDED' if not totals['dom_touch_events'] else
                   'PHYSICAL_EVENTS_RECORDED_OWNER_TEST_REQUIRED')
        receipt = {'verdict': verdict, 'started_wall': start_wall, 'ended_wall': end_wall,
                   'capture_seconds': end_mono - start_mono, 'requested_seconds': seconds,
                   'totals': totals, 'errors': errors, 'owner_verified': False}
        write_json(out / 'receipt.json', receipt)
        write_json(out / 'after.json', snapshot())
        return 4 if errors else 0
    finally:
        for fd in fds:
            os.close(fd)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--out', type=Path, required=True)
    ap.add_argument('--seconds', type=float, default=90)
    args = ap.parse_args()
    def expired(signum, frame):
        raise TimeoutError('capture exceeded hard deadline or was stopped')
    signal.signal(signal.SIGALRM, expired)
    signal.signal(signal.SIGTERM, expired)
    signal.alarm(165)
    lock = Path('/run/nuxel-owner-test.lock')
    lock_fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    os.write(lock_fd, ('%d\n' % os.getpid()).encode())
    try:
        return capture(args.out, args.seconds)
    except Exception as e:
        if args.out.exists():
            write_json(args.out / 'error.json', {'verdict': 'INVALID_CAPTURE', 'error': str(e)})
        raise
    finally:
        os.close(lock_fd)
        lock.unlink()


if __name__ == '__main__':
    raise SystemExit(main())
