#!/usr/bin/env python3
"""Nuxel S10+ UI sound cues: no raw hardware writes or persistent volume changes.

BOOT plays ONCE per boot only after the bridge's *actual* UI ownership receipt.
VOLUME is launched after a successful ALSA mixer change by the button manager.
Sound levels: boot MP3 decoder PCM gain = 44%; volume MP3 decoder PCM gain =
100% of the CURRENT protected ALSA mixer setting, not another attenuation.
The physical speaker path is unverified; failures are logged, never faked.
"""
import argparse
import fcntl
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time

ASSETS = Path(os.environ.get('NUXEL_SOUND_ASSET_DIR', '/usr/share/nuxel/assets'))
RUNTIME = Path(os.environ.get('NUXEL_SOUND_RUNTIME_DIR', '/run/nuxel'))
HANDOFF = Path(os.environ.get('NUXEL_SOUND_HANDOFF', '/run/nuxel-anim-handoff'))
SOUND_MODE = Path(os.environ.get('NUXEL_SOUND_MODE', '/var/lib/nuxel/audio/sound-mode'))
PLAYER = os.environ.get('NUXEL_SOUND_PLAYER') or shutil.which('mpg123')
ALSA_DEVICE = os.environ.get('NUXEL_SOUND_ALSA_DEVICE', '').strip()
BOOT_FILE = 'nuxel-boot-audio.mp3'
VOL_FILE = 'nuxel-pow.mp3'
BOOT_PCM_PERCENT = 44
WAIT_SECONDS = 180
LOG = os.environ.get('NUXEL_SOUND_LOG', '/var/log/nuxel/sound-cues.log')


def record(event, result, **kw):
    line = json.dumps(dict(time=int(time.time()), event=event, result=result, **kw), sort_keys=True)
    print(line, flush=True)
    try:
        log = Path(LOG)
        log.parent.mkdir(parents=True, exist_ok=True)
        with log.open('a') as handle:
            handle.write(line + '\n')
    except OSError:
        pass


def ready_handoff():
    try:
        h = json.loads(HANDOFF.read_text())
        return h.get('owner') == 'ui' and h.get('stage') == 'LAUNCHER_DISPLAY_OWNER'
    except (OSError, ValueError, TypeError):
        return False


def normal_sound_mode():
    try:
        return SOUND_MODE.read_text().strip() not in ('silent', 'vibrate')
    except OSError:
        return True


def play(event, percentage):
    src = ASSETS / (BOOT_FILE if event == 'boot' else VOL_FILE)
    if not src.is_file():
        record(event, 'missing_file', path=str(src)); return 3
    if not PLAYER:
        record(event, 'player_unavailable', detail='Install mpg123 in the Fedora rootfs'); return 4
    if not normal_sound_mode():
        record(event, 'muted_policy'); return 0
    # mpg123 -f accepts linear PCM gain in fixed-point units: 32768 = unity.
    # No ALSA mixer volume adjustment is made here: retain hardware cap.
    scale = round(32768 * max(0, min(100, percentage)) / 100)
    cmd = [str(PLAYER), '-q', '-o', 'alsa']
    # Select a device ONLY if confirmed on hardware. Empty => distro's ALSA
    # default policy/UCM; do not guess a beyond-madera PCM/card number.
    if ALSA_DEVICE:
        if any(c.isspace() for c in ALSA_DEVICE) or ALSA_DEVICE.startswith('-'):
            record(event, 'invalid_alsa_device', detail=ALSA_DEVICE); return 8
        cmd += ['-a', ALSA_DEVICE]
    cmd += ['-f', str(scale), str(src)]
    try:
        done = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE,
                              timeout=11 if event == 'boot' else 4, check=False)
        rc = done.returncode
        record(event, 'player_ok' if rc == 0 else 'player_error', exit_code=rc,
               pcm_gain_percent=percentage, output='alsa', alsa_device=ALSA_DEVICE or 'default',
               audible='unverified', detail=done.stderr.decode('utf-8', 'replace')[-400:])
        return 0 if rc == 0 else 5
    except (OSError, subprocess.TimeoutExpired) as e:
        record(event, 'player_exception', detail=str(e), output='alsa', pcm_gain_percent=percentage, audible='unverified')
        return 6


def do_boot():
    RUNTIME.mkdir(parents=True, exist_ok=True)
    done_file = RUNTIME / 'boot-sound-attempted'
    with (RUNTIME / 'boot-sound.lock').open('a+') as fd:
        fcntl.flock(fd, fcntl.LOCK_EX)
        if done_file.exists():
            record('boot', 'already_attempted'); return 0
        deadline = time.monotonic() + WAIT_SECONDS
        while not ready_handoff():
            if time.monotonic() >= deadline:
                record('boot', 'handoff_not_seen', waited_seconds=WAIT_SECONDS)
                return 7
            time.sleep(0.25)
        # Only one attempt per boot even if playback fails. Prevents repeated
        # loud restart loops when the audio device is broken or unavailable.
        done_file.write_text(str(int(time.time())) + '\n')
        return play('boot', BOOT_PCM_PERCENT)


def do_volume(level):
    RUNTIME.mkdir(parents=True, exist_ok=True)
    lock_path = RUNTIME / 'volume-sound.lock'
    with lock_path.open('a+') as fd:
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return 0  # suppress overlapping feedback while last cue plays
        # The actual ALSA mixer was already set to level by button manager.
        # Play the MP3 at unity PCM gain; the mixer determines the output.
        return play('volume', 100)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('event', choices=['boot', 'volume'])
    parser.add_argument('--level', type=int, default=0, help='current ALSA percentage (diagnostics only)')
    opts = parser.parse_args()
    if opts.event == 'boot':
        return do_boot()
    if opts.level < 0 or opts.level > 100:
        parser.error('--level must be 0..100')
    if opts.level == 0:
        record('volume', 'zero_volume_skipped'); return 0
    return do_volume(opts.level)

if __name__ == '__main__':
    sys.exit(main())
