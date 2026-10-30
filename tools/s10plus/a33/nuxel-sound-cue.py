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
import signal
import subprocess
import sys
import time

ASSETS = Path(os.environ.get('NUXEL_SOUND_ASSET_DIR', '/usr/share/nuxel/assets'))
RUNTIME = Path(os.environ.get('NUXEL_SOUND_RUNTIME_DIR', '/run/nuxel'))
HANDOFF = Path(os.environ.get('NUXEL_SOUND_HANDOFF', '/run/nuxel-anim-handoff'))
SOUND_MODE = Path(os.environ.get('NUXEL_SOUND_MODE', '/var/lib/nuxel/audio/sound-mode'))
# Prefer the PipeWire pulse path when the live session owns the ALSA device;
# direct ALSA opens fail with EBUSY while PipeWire holds hw:0,1.  GStreamer's
# pulsesink reaches the SAME default sink as every other Nuxel app.
PIPEWIRE_SOCKET = Path(os.environ.get('NUXEL_PIPEWIRE_SOCKET', '/run/nuxel-wayland/pipewire-0'))
GST = shutil.which('gst-launch-1.0') or '/usr/bin/gst-launch-1.0'
PWPLAY = shutil.which('pw-play') or '/usr/bin/pw-play'
PLAYER = os.environ.get('NUXEL_SOUND_PLAYER')
if not PLAYER:
    # pw-play blocks until EOS and links immediately; gst-launch pulsesink is
    # too slow to start for this 0.36 s cue and never posts EOS on this image.
    if PIPEWIRE_SOCKET.exists() and Path(PWPLAY).exists():
        PLAYER = PWPLAY
    elif Path('/usr/libexec/nuxel/nuxel-mp3-play').is_file():
        PLAYER = '/usr/libexec/nuxel/nuxel-mp3-play'
    else:
        PLAYER = shutil.which('mpg123')
ALSA_DEVICE = os.environ.get('NUXEL_SOUND_ALSA_DEVICE', '').strip()
# PWNAGE-38000 requires the confirmation cue to use the same nuxel-pow.mp3
# asset as the volume feedback and the Test Audio button.
BOOT_FILE = 'nuxel-pow.mp3'
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
    # No ALSA mixer volume adjustment is made here: retain the button-manager
    # hardware cap.  Select a device only if confirmed on hardware; empty lets
    # ALSA/UCM choose its default route.
    if ALSA_DEVICE and (any(c.isspace() for c in ALSA_DEVICE) or ALSA_DEVICE.startswith('-')):
        record(event, 'invalid_alsa_device', detail=ALSA_DEVICE); return 8
    if Path(PLAYER).name == 'nuxel-mp3-play':
        cmd = [str(PLAYER), '--gain', str(max(0, min(100, percentage)))]
        if ALSA_DEVICE:
            cmd += ['--device', ALSA_DEVICE]
        cmd += [str(src)]
    elif Path(PLAYER).name == 'gst-launch-1.0':
        # PipeWire owns the ALSA device on the live image, so route through the
        # Pulse-compatible pipewire-pulse socket (the same default-sink path
        # every app uses).  ALSA_DEVICE, when explicitly set, is still honoured
        # for a direct ALSA sink.
        gain = max(0, min(100, percentage)) / 100.0
        if ALSA_DEVICE:
            sink = 'alsasink' + (f' device={ALSA_DEVICE}' if ALSA_DEVICE else '')
        else:
            sink = 'pulsesink'
        cmd = [str(PLAYER), '-q', 'filesrc', f'location={src}', '!', 'decodebin',
               '!', 'audioconvert', '!', 'audioresample', '!', 'volume',
               f'volume={gain:.2f}', '!', sink]
    elif Path(PLAYER).name == 'pw-play':
        gain = max(0, min(100, percentage)) / 100.0
        cmd = [str(PLAYER), '--volume', f'{gain:.3f}', str(src)]
    else:
        # mpg123 -f accepts linear PCM gain in fixed-point units: 32768 = unity.
        scale = round(32768 * max(0, min(100, percentage)) / 100)
        cmd = [str(PLAYER), '-q', '-o', 'alsa']
        if ALSA_DEVICE:
            cmd += ['-a', ALSA_DEVICE]
        cmd += ['-f', str(scale), str(src)]
    timeout = 11 if event == 'boot' else 6
    output = 'pipewire' if (Path(PLAYER).name in ('gst-launch-1.0', 'pw-play') and not ALSA_DEVICE) else 'alsa'
    pulse_bounded = output == 'pipewire' and Path(PLAYER).name == 'gst-launch-1.0'
    proc = None
    try:
        # GStreamer can fork helper processes which inherit stderr.  Killing only
        # its parent then makes communicate() wait forever for that pipe; give
        # every cue a separate process group so timeout always returns control to
        # the single button manager.
        env = dict(os.environ)
        env.setdefault('XDG_RUNTIME_DIR', '/run/nuxel-wayland')
        env.setdefault('PIPEWIRE_RUNTIME_DIR', '/run/nuxel-wayland')
        env.setdefault('PULSE_SERVER', 'unix:/run/nuxel-wayland/pulse/native')
        proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE,
                                env=env, start_new_session=True)
        _, stderr = proc.communicate(timeout=timeout)
        rc = proc.returncode
        record(event, 'player_ok' if rc == 0 else 'player_error', exit_code=rc,
               pcm_gain_percent=percentage, output=output, alsa_device=ALSA_DEVICE or 'default',
               audible='unverified', detail=stderr.decode('utf-8', 'replace')[-400:])
        return 0 if rc == 0 else 5
    except subprocess.TimeoutExpired:
        # On this image gst-launch pulsesink never posts EOS back through the
        # bus, so a bounded window IS the expected successful completion for the
        # PipeWire path.  Record it as player_ok but never as audible.
        try:
            os.killpg(proc.pid, signal.SIGTERM)
            _, stderr = proc.communicate(timeout=1)
        except subprocess.TimeoutExpired:
            try:
                os.killpg(proc.pid, signal.SIGKILL)
                _, stderr = proc.communicate(timeout=2)
            except (OSError, subprocess.TimeoutExpired):
                stderr = b'player process group did not reap after SIGKILL'
        except OSError:
            stderr = b'player process group was already gone'
        result = 'player_ok' if pulse_bounded else 'player_timeout'
        record(event, result, timeout_seconds=timeout, output=output,
               pcm_gain_percent=percentage, audible='unverified',
               note=('bounded PipeWire window: gst-launch pulsesink does not post EOS on this image' if pulse_bounded else None),
               detail=stderr.decode('utf-8', 'replace')[-400:])
        return 0 if pulse_bounded else 5
    except (OSError, KeyboardInterrupt) as e:
        if proc is not None:
            try:
                os.killpg(proc.pid, signal.SIGKILL)
            except OSError:
                pass
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
