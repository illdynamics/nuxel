#!/usr/bin/env python3
"""Nuxel's bounded Samsung timed_output haptics owner.

Only this service writes the vibrator.  It accepts a small FIFO protocol from
the launcher host, clamps every pulse, writes amplitude only when the actual
Samsung ``intensity`` attribute is present, and always turns the motor off on
exit.  No register access, input-event emulation, or kernel assumptions.
"""
from __future__ import annotations
import json, os, select, signal, sys, time
from pathlib import Path

CFG = Path('/etc/nuxel/haptics/settings.json')
STATE = Path('/run/nuxel-haptics/state')
FIFO = Path('/run/nuxel-haptics/haptics.cmd')
VIB = Path('/sys/class/timed_output/vibrator')
STOP = False
DEFAULT = dict(schema_version=1, enabled=True, touch_feedback=True,
               scroll_feedback=True, navigation_feedback=True,
               long_press_feedback=True, intensity_percent=30,
               tap_ms=12, scroll_ms=6, long_press_ms=25)
MAX_MS = 100
COOLDOWN_MS = dict(tap=45, scroll=110, navigation=70, switch=80, long=350, error=350, test=0)

def read_cfg():
    try:
        data = json.loads(CFG.read_text())
        if not isinstance(data, dict): data = {}
    except Exception: data = {}
    out = DEFAULT.copy(); out.update(data)
    for key, lo, hi in [('intensity_percent',0,100), ('tap_ms',5,40), ('scroll_ms',3,20), ('long_press_ms',10,80)]:
        try: out[key] = max(lo, min(hi, int(out[key])))
        except Exception: out[key] = DEFAULT[key]
    return out

def write(path: Path, value: int):
    with path.open('w') as f: f.write(str(value))

class Haptics:
    def __init__(self): self.last = {}; self.amplitude = (VIB/'intensity').exists()
    def state(self, note='ready'):
        STATE.write_text('backend=timed_output\nnode=%s\namplitude_supported=%d\nmax_duration_ms=%d\n%s\n' % (VIB, self.amplitude, MAX_MS, note))
    def off(self):
        try: write(VIB/'enable', 0)
        except OSError: pass
    def pulse(self, kind):
        cfg = read_cfg()
        if not VIB.exists(): self.state('refused=no_vibrator_node'); return
        if not cfg['enabled']: self.state('refused=master_disabled'); return
        enable_key = {'tap':'touch_feedback','scroll':'scroll_feedback','navigation':'navigation_feedback','switch':'navigation_feedback','long':'long_press_feedback'}.get(kind)
        if enable_key and not cfg[enable_key]: self.state('refused=%s_disabled' % enable_key); return
        now = time.monotonic() * 1000
        if now - self.last.get(kind, -10**9) < COOLDOWN_MS.get(kind, 100): self.state('coalesced=' + kind); return
        self.last[kind] = now
        if kind == 'scroll': ms, pct = cfg['scroll_ms'], min(100, max(0, cfg['intensity_percent']//2))
        elif kind == 'long': ms, pct = cfg['long_press_ms'], min(100, max(0, cfg['intensity_percent'] + 15))
        elif kind == 'switch': ms, pct = 14, min(100, max(0, cfg['intensity_percent'] + 5))
        elif kind == 'error': ms, pct = 20, min(100, max(0, cfg['intensity_percent'] + 10))
        elif kind == 'test': ms, pct = cfg['tap_ms'], cfg['intensity_percent']
        else: ms, pct = cfg['tap_ms'], cfg['intensity_percent']
        try:
            if self.amplitude: write(VIB/'intensity', pct * 100)
            write(VIB/'enable', min(MAX_MS, ms))
            if kind == 'error':
                time.sleep((ms + 35) / 1000.0)
                if self.amplitude: write(VIB/'intensity', pct * 100)
                write(VIB/'enable', min(MAX_MS, ms))
            self.state('pulse=%s duration_ms=%d intensity_percent=%d' % (kind, ms, pct))
        except OSError as e: self.off(); self.state('write_failed=%s' % e.errno)

def main():
    global STOP
    h = Haptics(); h.off(); h.state('started_no_pulse')
    FIFO.parent.mkdir(parents=True, exist_ok=True)
    if FIFO.exists() and not FIFO.is_fifo(): raise RuntimeError('%s is not a FIFO' % FIFO)
    if not FIFO.exists(): os.mkfifo(FIFO, 0o620)
    def stop(*_):
        global STOP; STOP = True
    signal.signal(signal.SIGTERM, stop); signal.signal(signal.SIGINT, stop)
    fd = os.open(FIFO, os.O_RDWR | os.O_NONBLOCK)
    buf = b''
    try:
        while not STOP:
            r, _, _ = select.select([fd], [], [], .5)
            if not r: continue
            chunk = os.read(fd, 512)
            if not chunk: continue
            buf += chunk
            while b'\n' in buf:
                raw, buf = buf.split(b'\n', 1)
                cmd = raw.decode('ascii', 'ignore').strip()
                if cmd in ('tap','scroll','navigation','switch','long','error','test'): h.pulse(cmd)
                elif cmd in ('off','suspend'): h.off(); h.state('motor_off=' + cmd)
                else: h.state('refused=unknown_command')
    finally:
        os.close(fd); h.off(); h.state('stopped_motor_off')

if __name__ == '__main__': main()
