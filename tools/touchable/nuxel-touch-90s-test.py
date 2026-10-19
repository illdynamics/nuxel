#!/usr/bin/env python3
"""Prepare a passive phone recorder, announce, capture 90 monotonic seconds, retrieve.

Exit 0: capture + owner PASS; 2: owner pending; 3: transport/setup blocked;
4: invalid/missing physical/DOM evidence; 5: owner FAIL.
Never grabs input, opens the framebuffer, injects events or restarts the GUI.
The serial library enforces exclusive ownership. The phone recorder has its own
deadline, alarm and systemd RuntimeMaxSec, even if this host process disappears.
"""
import argparse
import base64
import gzip
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import shlex
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools/beta/live'))
import nuxel_live as nl

spec = importlib.util.spec_from_file_location('owner_window', ROOT / 'tools/beta/live/nuxel-owner-window.py')
owner_window = importlib.util.module_from_spec(spec)
spec.loader.exec_module(owner_window)
MISSION = ROOT / 'docs/touchable'
ACTIONS = {
    1: ('PLEASE USE YOUR FINGER ON THE PHONE.\n\n'
        '1. Tap the Settings icon five times, allowing it to open if possible.\n'
        '2. Tap another visible application icon.\n'
        '3. Tap the center of the screen five times.\n'
        '4. Try to return Home.\n'
        '5. Repeat whichever action appears unresponsive.'),
    2: ('PLEASE:\n\n1. Swipe LEFT across the middle of the screen.\n'
        '2. Swipe RIGHT to return.\n3. Repeat five times.\n'
        '4. Tap an icon on Desktop 1.\n5. Return Home.\n'
        '6. Swipe to Desktop 2.\n7. Tap an icon on Desktop 2.\n8. Return Home.'),
    3: ('PLEASE:\n\n1. Swipe DOWN from the center of the Home screen.\n'
        '2. Confirm the top panel appears.\n3. Swipe UP to dismiss it.\n'
        '4. Swipe UP from the center to open Applications.\n'
        '5. Tap an application icon in the drawer.\n6. Return Home.\n'
        '7. Repeat from different areas of the screen.\n'
        '8. If available, repeat while an application is open.'),
}


def feedback(trial):
    path = MISSION / 'owner-feedback.jsonl'
    rows = [json.loads(line) for line in path.read_text().splitlines()] if path.exists() else []
    return next((r for r in reversed(rows) if r['trial'] == trial), {'verdict': 'PENDING'})


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--round', type=int, choices=ACTIONS, required=True)
    ap.add_argument('--trial', required=True)
    ap.add_argument('--await-announcement', action='store_true',
                    help='Wait up to 30 seconds for evidence/TRIAL/announce before starting')
    ap.add_argument('--retrieve-only', action='store_true')
    ap.add_argument('--resume-armed', action='store_true')
    args = ap.parse_args()
    if not re.fullmatch(r'[a-z0-9-]{1,45}', args.trial):
        ap.error('trial must be a unique lowercase id')
    evidence = MISSION / 'evidence' / args.trial
    evidence.mkdir(parents=True, exist_ok=args.retrieve_only or args.resume_armed)
    receipts_path = evidence / 'console-receipts.json'
    frames = json.loads(receipts_path.read_text()) if receipts_path.exists() else []

    def run(c, command, timeout=15):
        result = c.run(command, timeout=timeout)
        frames.append(dict(command=command, output=result.output if result.framed and result.sha_ok else 'UNVERIFIED', **result.as_dict()))
        receipts_path.write_text(json.dumps(frames, indent=2) + '\n')
        if not result.ok:
            raise RuntimeError('Unverified/failed console command: ' + command)
        return result.output

    data = (ROOT / 'tools/beta/live/nuxel_owner_capture.py').read_bytes()
    sha = hashlib.sha256(data).hexdigest()
    target = '/var/tmp/nuxel-owner-capture-' + sha[:16] + '.py'
    phone, unit = '/var/tmp/nuxel-' + args.trial, 'nuxel-' + args.trial
    c, node, _ = nl.open_console(serial=nl.DEFAULT_SERIAL, timeout=15)
    with c:
        if not args.retrieve_only:
            print('Checking phone and preparing passive diagnostics.', flush=True)
            run(c, 'test ! -e ' + phone + '/start' if args.resume_armed else 'test ! -e ' + phone + ' && test ! -e /run/nuxel-owner-test.lock')
            baseline = run(c, "uname -smr; cat /proc/sys/kernel/random/boot_id; cat /proc/bus/input/devices; systemctl is-active nuxel-wayland nuxel-wl-fb nuxel-touch-arm")
            (evidence / 'baseline.txt').write_text(baseline)
            if 'sec_touchscreen' not in baseline:
                raise RuntimeError('Touchscreen absent; cannot arm physical test')
            present = run(c, 'if test -f ' + target + '; then sha256sum ' + target + '; else echo ABSENT; fi')
            if sha not in present:
                staged = nl.push_bytes(c, gzip.compress(data, mtime=0), target + '.gz', mode='0600')
                (evidence / 'diagnostic-deploy.json').write_text(json.dumps(staged, indent=2) + '\n')
                run(c, 'gzip -dc ' + target + '.gz > ' + target + '.stage && test "$(sha256sum ' + target + '.stage | cut -d\' \' -f1)" = ' + sha + ' && chmod 0600 ' + target + '.stage && mv ' + target + '.stage ' + target)
            if sha not in run(c, 'sha256sum ' + target):
                raise RuntimeError('Recorder hash mismatch')
            if not args.resume_armed:
                run(c, 'systemd-run --quiet --unit=' + unit + ' --property=RuntimeMaxSec=170 --property=TimeoutStopSec=5 /usr/bin/python3 ' + target + ' --out ' + phone + ' --seconds 90')
            ready = None
            for _ in range(10):
                text = run(c, 'if test -f ' + phone + '/ready.json; then cat ' + phone + '/ready.json; elif test -f ' + phone + '/receipt.json; then cat ' + phone + '/receipt.json; else echo WAITING; fi')
                if 'armed_at' in text:
                    ready = json.loads(text)
                    break
                if 'CAPTURE_BLOCKED' in text:
                    raise RuntimeError(text)
                time.sleep(.25)
            if not ready:
                raise RuntimeError('Recorder never armed')
            (evidence / 'ready.json').write_text(json.dumps(ready, indent=2) + '\n')
            print('ARMED: ' + str(evidence), flush=True)
            if args.await_announcement:
                deadline = time.monotonic() + 30
                while not (evidence / 'announce').exists():
                    if time.monotonic() >= deadline:
                        raise RuntimeError('No host announcement signal; phone arm expires automatically')
                    time.sleep(.1)
            print('\n' + '=' * 50 + f'\nNUXEL — PHYSICAL TOUCH TEST {args.round}\n90 SECONDS — STARTING NOW\n' + '=' * 50, flush=True)
            print(ACTIONS[args.round], flush=True)
            print('\nI am recording touchscreen, compositor, WebKit and application events.\nDO NOT unplug the USB cable.\nWhen the timer ends, I will analyze the results and automatically continue.\n' + '=' * 50, flush=True)
            (MISSION / 'active-trial.json').write_text(json.dumps(dict(trial=args.trial, round=args.round, announced_at=time.time())) + '\n')
            print('Feedback: tools/touchable/touchable-owner PASS\nOr: tools/touchable/touchable-owner FAIL "what you saw"', flush=True)
            run(c, 'touch ' + phone + '/start')
            started = json.loads(run(c, 'cat ' + phone + '/started.json'))
            (evidence / 'started.json').write_text(json.dumps(started, indent=2) + '\n')
            host_start = time.monotonic()
        else:
            host_start = None
    if host_start is not None:
        for elapsed in (30, 60, 90):
            time.sleep(max(0, host_start + elapsed - time.monotonic()))
            print(f'{90 - elapsed} seconds remaining.', flush=True)
    c, _, _ = nl.open_console(serial=nl.DEFAULT_SERIAL, timeout=25)
    with c:
        archive_sha = owner_window.retrieve(c, run, phone, unit, evidence)
    receipt = json.loads((evidence / 'receipt.json').read_text())
    owner = feedback(args.trial)
    valid = (receipt.get('requested_seconds') == 90 and 90 <= receipt.get('capture_seconds', 0) < 92
             and not receipt.get('errors'))
    physical = receipt.get('totals', {}).get('tracking_down', 0) > 0
    delivered = receipt.get('totals', {}).get('dom_touch_events', 0) > 0
    code = 5 if owner['verdict'] == 'FAIL' else 4 if not (valid and physical and delivered) else 0 if owner['verdict'] == 'PASS' else 2
    result = dict(trial=args.trial, round=args.round, recorder_sha256=sha,
                  archive_sha256=archive_sha, console=node, capture=receipt,
                  owner=owner, exit_code=code, completed_at=time.time())
    (evidence / 'result.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(dict(trial=args.trial, capture=receipt, owner=owner, exit_code=code), indent=2), flush=True)
    return code


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except (RuntimeError, OSError, ValueError) as exc:
        print('TEST BLOCKED: ' + str(exc), file=sys.stderr, flush=True)
        raise SystemExit(3)
