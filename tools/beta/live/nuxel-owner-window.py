#!/usr/bin/env python3
"""Arm, announce, time and retrieve one real 90-second owner trial over USB.

This deploys only a content-addressed diagnostic in /var/tmp, never an OS asset.
The console is closed throughout the timed window. No synthetic input is sent.
"""
import argparse
import base64
import gzip
import hashlib
import io
import json
from pathlib import Path
import re
import shlex
import sys
import tarfile
import time

import nuxel_live as nl

ACTIONS = {
    'WIN1': 'With Nuxel visible, tap the CENTER 5 times, tap the SETTINGS icon 3 times, then swipe from the TOP down and from the BOTTOM up. Repeat slowly.',
    'WIN2': 'Tap Settings and Close; open Calendar and return Home; drag down Quick Settings and close it; tap the search field and type NUXEL using the onscreen keyboard. Repeat if time allows.',
    'WIN3': 'Open and close two different apps twice, scroll in one app, use Back/Home, then press Power once to turn screen off and once to wake; do not double-press it. Report whether everything moved visibly as expected.',
}


def retrieve(c, run, phone, unit, evidence):
    status = run(c, 'systemctl show ' + unit + ' -p ActiveState -p SubState -p ExecMainStatus; cat ' + phone + '/receipt.json')
    print(status, flush=True)
    # Minimal phone images need not ship tar. Python is already required by the
    # recorder. A single process propagates packing errors instead of a shell
    # pipeline reporting base64's success after tar failed.
    code = ('import io,tarfile,base64; b=io.BytesIO(); '
            't=tarfile.open(fileobj=b,mode="w:gz"); '
            't.add(' + repr(phone) + ',arcname=' + repr(Path(phone).name) + '); '
            't.close(); print(base64.b64encode(b.getvalue()).decode())')
    packed = run(c, 'python3 -c ' + shlex.quote(code), timeout=25)
    archive = base64.b64decode(packed.strip(), validate=True)
    (evidence / 'phone-capture.tar.gz').write_bytes(archive)
    with tarfile.open(fileobj=io.BytesIO(archive), mode='r:gz') as tf:
        for item in tf.getmembers():
            if item.isfile():
                rel = Path(item.name)
                if len(rel.parts) != 2 or rel.parts[0] != Path(phone).name or item.size > 12 * 1024 * 1024:
                    raise RuntimeError('unsafe archive member')
                (evidence / rel.name).write_bytes(tf.extractfile(item).read())
    return hashlib.sha256(archive).hexdigest()


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--window', choices=ACTIONS, required=True)
    ap.add_argument('--label', required=True, help='Unique lowercase identifier; existing trials are never overwritten')
    ap.add_argument('--evidence-dir', type=Path, required=True)
    ap.add_argument('--resume-armed', action='store_true', help='Resume an armed trial after a lost console frame; never restart it')
    ap.add_argument('--retrieve-only', action='store_true', help='Retrieve an already completed trial without asking for more touches')
    args = ap.parse_args()
    if not re.fullmatch(r'[a-z0-9-]{1,50}', args.label):
        ap.error('invalid label')
    args.evidence_dir.mkdir(parents=True, exist_ok=args.resume_armed or args.retrieve_only)
    previous = args.evidence_dir / 'console-receipts.json'
    frames = json.loads(previous.read_text()) if previous.exists() else []
    def run(c, cmd, timeout=15):
        r = c.run(cmd, timeout=timeout)
        frames.append(dict(command=cmd, output=r.output if r.framed and r.sha_ok else 'UNVERIFIED', **r.as_dict()))
        (args.evidence_dir / 'console-receipts.json').write_text(json.dumps(frames, indent=2) + '\n')
        if not r.ok:
            raise RuntimeError('command failed or receipt unverified: ' + cmd)
        return r.output

    data = (Path(__file__).parent / 'nuxel_owner_capture.py').read_bytes()
    sha = hashlib.sha256(data).hexdigest()
    target = '/var/tmp/nuxel-owner-capture-' + sha[:16] + '.py'
    phone = '/var/tmp/nuxel-' + args.label
    unit = 'nuxel-' + args.label
    feedback = Path(nl.repo_root_from_here()) / 'docs/beta-finalization/v0.5.2/owner-feedback.local.txt'
    feedback_size = feedback.stat().st_size if feedback.exists() else 0
    c, node, _ = nl.open_console(serial=nl.DEFAULT_SERIAL, timeout=15)
    if args.retrieve_only:
        with c:
            archive_sha = retrieve(c, run, phone, unit, args.evidence_dir)
        (args.evidence_dir / 'host-receipt.json').write_text(json.dumps({
            'window': args.window, 'retrieved_at': time.time(), 'archive_sha256': archive_sha,
            'source_sha256': sha, 'phone_started': json.loads((args.evidence_dir / 'started.json').read_text()),
            'note': 'retrieved completed capture after transport/packing interruption; no repeated owner actions'}, indent=2) + '\n')
        print('Saved full capture:', args.evidence_dir, flush=True)
        return
    with c:
        baseline = run(c, "uname -smr; cat /proc/sys/kernel/random/boot_id; tr ' ' '\\n' < /proc/cmdline | grep -E '^(androidboot.mode|lpcharge|charging_mode|androidboot.em.model)='; df -Pk / /var /run; systemctl is-active nuxel-wayland nuxel-wl-fb nuxel-touch-arm; grep -A6 sec_touchscreen /proc/bus/input/devices; true")
        print(baseline, flush=True)
        if 'androidboot.mode=charger' in baseline or 'Name="sec_touchscreen"' not in baseline:
            raise RuntimeError('CAPTURE_BLOCKED: no registered touchscreen on this boot')
        run(c, ('test ! -e ' + phone + '/start && test -f ' + phone + '/ready.json') if args.resume_armed else 'test ! -e ' + phone)
        present = run(c, 'if test -f ' + target + '; then sha256sum ' + target + '; else echo ABSENT; fi')
        if sha not in present:
            run(c, 'test ! -e ' + target)
            staged = nl.push_bytes(c, gzip.compress(data, mtime=0), target + '.gz', mode='0600')
            (args.evidence_dir / 'diagnostic-deploy.json').write_text(json.dumps(staged, indent=2) + '\n')
            run(c, 'gzip -dc ' + target + '.gz > ' + target + '.stage && test "$(sha256sum ' + target + '.stage | cut -d\' \' -f1)" = ' + sha + ' && chmod 0600 ' + target + '.stage && mv ' + target + '.stage ' + target)
        installed = run(c, 'sha256sum ' + target)
        if sha not in installed:
            raise RuntimeError('diagnostic destination hash mismatch')
        if not args.resume_armed:
            run(c, 'systemd-run --quiet --unit=' + unit + ' --property=RuntimeMaxSec=170 --property=TimeoutStopSec=5 /usr/bin/python3 ' + target + ' --out ' + phone + ' --seconds 90')
        run(c, 'test "$(systemctl is-active ' + unit + ')" = active')
        ready = ''
        for _ in range(10):
            ready = run(c, 'if test -f ' + phone + '/ready.json; then cat ' + phone + '/ready.json; elif test -f ' + phone + '/receipt.json; then cat ' + phone + '/receipt.json; else echo WAITING; fi')
            if 'armed_at' in ready:
                break
            if 'CAPTURE_BLOCKED' in ready:
                raise RuntimeError(ready)
            time.sleep(.5)
        if 'armed_at' not in ready:
            raise RuntimeError('CAPTURE_BLOCKED: no ready receipt')
        print('\n' + '=' * 66, flush=True)
        print('NUXEL — LIVE TOUCH TEST ' + args.window[3:] + ' — STARTING NOW (90 SECONDS)', flush=True)
        print('PLEASE TOUCH THE PHONE NOW. You have 90 seconds.', flush=True)
        print('DO THESE ACTIONS: ' + ACTIONS[args.window], flush=True)
        print('I AM RECORDING EVENTS; YOU DO NOT NEED TO TYPE ANYTHING.', flush=True)
        print('=' * 66 + '\a', flush=True)
        print('Optional owner feedback in a second terminal (replace the description):', flush=True)
        print("printf '%s\\n' '" + args.window + " FAIL: describe what you saw' >> " + str(feedback), flush=True)
        announced = time.time()
        run(c, 'touch ' + phone + '/start')
        started = json.loads(run(c, 'cat ' + phone + '/started.json'))
        # Start the HOST wait after the phone acknowledges. This intentionally
        # waits slightly longer than the phone's full 90-second monotonic timer.
        host_start = time.monotonic()
        print('Phone recorder acknowledged; host deadline:', time.strftime('%H:%M:%S %Z', time.localtime(time.time() + 90)), flush=True)
    for elapsed in (30, 60, 80, 90):
        time.sleep(max(0, host_start + elapsed - time.monotonic()))
        print(args.window + ': ' + str(90 - elapsed) + ' seconds remaining' if elapsed < 90 else args.window + ': capture deadline reached; retrieving evidence.', flush=True)
    # The owner file is read only after the deadline. Never write feedback here.
    feedback_result = {'state': 'OWNER_TEST_REQUIRED', 'applicable_lines': [], 'window': args.window}
    if feedback.exists():
        st = feedback.stat()
        if announced <= st.st_mtime <= time.time() and st.st_size > feedback_size:
            with feedback.open('rb') as f:
                f.seek(feedback_size)
                lines = f.read(16384).decode('utf-8', 'replace').splitlines()
            feedback_result['applicable_lines'] = [l for l in lines if l.startswith(args.window + ' ')]
            feedback_result['updated_at'] = st.st_mtime
            if feedback_result['applicable_lines']:
                feedback_result['state'] = 'OWNER_FEEDBACK_RECEIVED_REVIEW_REQUIRED'
    (args.evidence_dir / 'owner-feedback.local.json').write_text(json.dumps(feedback_result, indent=2) + '\n')
    c, _, _ = nl.open_console(serial=nl.DEFAULT_SERIAL, timeout=20)
    with c:
        archive_sha = retrieve(c, run, phone, unit, args.evidence_dir)
    result = {'window': args.window, 'announced_at': announced, 'phone_started': started,
              'source_sha256': sha, 'target': target, 'console_node': node['callout'],
              'archive_sha256': archive_sha,
              'owner_feedback_state': feedback_result['state'], 'finished_at': time.time()}
    (args.evidence_dir / 'host-receipt.json').write_text(json.dumps(result, indent=2) + '\n')
    print('Saved full capture:', args.evidence_dir, flush=True)
    print('Owner feedback:', feedback_result['state'], flush=True)


if __name__ == '__main__':
    main()
