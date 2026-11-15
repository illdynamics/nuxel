#!/usr/bin/env python3
"""Nuxel S10+ UI sound cues: no raw hardware writes or persistent volume changes.

BOOT plays ONCE per boot only after the bridge's *actual* UI ownership receipt
and a live `nuxel-audio-route.sh --check` readiness probe (Calliope MUB0, both
CS35L41 DSP1s booted/running, every route control, the 48 kHz static sink, the
default sink, and the volume ceiling).  VOLUME is launched after a successful
PipeWire default-sink change by the button manager.  BOOT plays the supplied
nuxel-boot-audio.mp3 and VOLUME plays nuxel-pow.mp3, both at 100% decoder gain
into the verified default sink (owner policy: 100% ceiling, 50% default), so
there is exactly one attenuation stage.  Failures are logged, never faked; a
player exit code is never recorded as audible.
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
# nuxel-preload-cinema owns the panel between the boot animation and the real
# lockscreen.  Its overlay receipt appears when the preloading video starts and
# disappears when the video releases the glass to the lockscreen, so the boot
# cue can be started while the video is still playing.
CINEMA_OVERLAY = Path('/run/nuxel/preload-cinema.overlay')
CINEMA_CONFIG = Path('/etc/nuxel/boot/preload-cinema.json')
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
# The supplied boot cue is the long nuxel-boot-audio.mp3; short interactive
# feedback (volume / Test Audio) keeps using nuxel-pow.mp3.
BOOT_FILE = 'nuxel-boot-audio.mp3'
VOL_FILE = 'nuxel-pow.mp3'
BOOT_PCM_PERCENT = 100
WAIT_SECONDS = 180
LOG = os.environ.get('NUXEL_SOUND_LOG', '/var/log/nuxel/sound-cues.log')
ROUTE_CHECK = os.environ.get('NUXEL_AUDIO_ROUTE_CHECK', '/usr/lib/nuxel/nuxel-audio-route.sh')
SOUND_AT_CAP = 1.0  # owner-approved ceiling (100%)
SOUNDCTL = os.environ.get('NUXEL_SOUNDCTL', '/usr/libexec/nuxel/nuxel-soundctl')


def audio_route_ready():
    """Use the route script's live, read-only readiness probe.

    This verifies the ABOX Calliope version, both CS35L41 DSP1s, every required
    mixer readback, the static PipeWire sink, the real default sink, and the
    volume ceiling.  Merely finding /run/nuxel-audio-route.state is not proof.
    """
    if not os.path.isfile(ROUTE_CHECK):
        return False, 'route check missing: %s' % ROUTE_CHECK
    try:
        proc = subprocess.run([ROUTE_CHECK, '--check'], stdout=subprocess.PIPE,
                              stderr=subprocess.STDOUT, text=True, timeout=20,
                              env=dict(os.environ, XDG_RUNTIME_DIR='/run/nuxel-wayland',
                                       PIPEWIRE_RUNTIME_DIR='/run/nuxel-wayland',
                                       PULSE_SERVER='unix:/run/nuxel-wayland/pulse/native'))
    except (OSError, subprocess.SubprocessError) as exc:
        return False, 'route check failed to run: %s' % exc
    text = (proc.stdout or '').strip()
    return proc.returncode == 0, text[-600:]


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


def play_via_manager(event, percentage):
    """Ask the pre-initialized sound manager to play an assigned action.

    This is the fast path: soundd owns one persistent pw-cat stream and decodes
    the cue once, so no route check, CS35L41 warmup, player fork or MP3 decoder
    starts on a volume-key repeat.  A missing daemon falls back to the historic
    path below and is logged honestly.
    """
    if not (os.path.isfile(SOUNDCTL) and os.access(SOUNDCTL, os.X_OK)):
        return False
    try:
        proc = subprocess.run([SOUNDCTL, '--json', 'play', event],
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                              text=True, timeout=5,
                              env=dict(os.environ, XDG_RUNTIME_DIR='/run/nuxel-wayland'))
        out = (proc.stdout or '').strip()
        ok = proc.returncode == 0 and '"success": true' in out
        record(event, 'soundd_queued' if ok else 'soundd_refused',
               pcm_gain_percent=percentage, audible='unverified',
               detail=out[-400:])
        return ok
    except (OSError, subprocess.SubprocessError) as exc:
        record(event, 'soundd_unavailable', detail=str(exc), audible='unverified')
        return False


def play(event, percentage):
    src = ASSETS / (BOOT_FILE if event == 'boot' else VOL_FILE)
    if not src.is_file():
        record(event, 'missing_file', path=str(src)); return 3
    if not PLAYER:
        record(event, 'player_unavailable', detail='Install mpg123 in the Fedora rootfs'); return 4
    ready, detail = audio_route_ready()
    if not ready:
        record(event, 'route_not_ready', detail=detail, audible='unverified')
        return 9
    # The CS35L41 output stage is left muted by the previous playback's
    # hw_free, and a cold speaker DAPM path can swallow this 366 ms cue.
    # The helper repairs the cache, applies the proven registers and keeps an
    # inaudible stream on the speaker path until DAPM SPEAKER=On.
    patch_path = '/usr/lib/nuxel/nuxel-cs35l41-apply.sh'
    if os.path.isfile(patch_path) and os.access(patch_path, os.X_OK):
        try:
            patch = subprocess.run([patch_path], stdout=subprocess.DEVNULL,
                                   stderr=subprocess.PIPE, timeout=10)
            if patch.returncode != 0:
                record(event, 'cs35_patch_failed',
                       detail=(patch.stderr or b'').decode('utf-8', 'replace')[-200:],
                       audible='unverified')
                return 10
        except (OSError, subprocess.SubprocessError) as exc:
            record(event, 'cs35_patch_failed', detail=str(exc), audible='unverified')
            return 10
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


def _cinema_active():
    """True while nuxel-preload-cinema's video overlay owns the glass.

    The overlay document is written once when playback starts and again (state
    'done') before the lockscreen is revealed, so its TEXT is the signal; a
    plain non-empty file would stay "covered" forever.
    """
    try:
        if not CINEMA_OVERLAY.is_file():
            return False
        doc = json.loads(CINEMA_OVERLAY.read_text())
    except (OSError, ValueError):
        return False
    return isinstance(doc, dict) and doc.get('state') in ('starting', 'covered')


def _cue_wait_seconds():
    """How long before the lockscreen handoff the boot cue is started.

    Derived from the shipped documents, never hardcoded: the cue must END when
    the preloading video ends and the real lockscreen is revealed.  Cue length
    + player start latency is subtracted from the clip length, and the result
    is clamped to the video's own duration.
    """
    clip_s = 6.0
    try:
        doc = json.loads(CINEMA_CONFIG.read_text())
        # `asset` is the installer path; the media facts (duration) live in the
        # sibling `_asset` document.  Accept either shape, never guess a value.
        asset = None
        if isinstance(doc, dict):
            for key in ('_asset', 'asset'):
                cand = doc.get(key)
                if isinstance(cand, dict):
                    asset = cand
                    break
        if isinstance(asset, dict) and isinstance(asset.get('duration_ms'), (int, float)):
            clip_s = max(0.5, float(asset['duration_ms']) / 1000.0)
    except (OSError, ValueError, TypeError):
        pass
    cue_s = 0.0
    try:
        path = ASSETS / BOOT_FILE
        # MPEG-1 Layer III: 1152 samples per frame.  Read the first valid
        # frame header for the rate instead of trusting the file name.
        import struct
        data = path.read_bytes()
        i = 0
        if data[:3] == b'ID3':
            sz = ((data[6] & 0x7f) << 21) | ((data[7] & 0x7f) << 14) | \
                 ((data[8] & 0x7f) << 7) | (data[9] & 0x7f)
            i = 10 + sz
        frames = 0
        rate = 44100
        while i + 4 <= len(data):
            if data[i] != 0xFF or (data[i + 1] & 0xE0) != 0xE0:
                i += 1
                continue
            h = struct.unpack('>I', data[i:i + 4])[0]
            ver, layer, bri, sri, pad = (h >> 19) & 3, (h >> 17) & 3, (h >> 12) & 0xF, (h >> 10) & 3, (h >> 9) & 1
            brs = (0, 32, 40, 48, 56, 64, 80, 96, 112, 128, 160, 192, 224, 256, 320)
            if ver != 3 or layer != 1 or bri == 0 or sri == 3:
                i += 1
                continue
            rate = (44100, 48000, 32000)[sri]
            i += (144 * brs[bri] * 1000) // rate + pad
            frames += 1
        cue_s = frames * 1152.0 / rate
    except (OSError, ValueError, IndexError, struct.error):
        cue_s = 0.0
    # 250 ms covers decoder/pw-play start-up measured in sound-cues.log
    # (queue_ms < 5 ms, measured, plus the first audio period).
    lead = clip_s - cue_s - 0.25
    # The supplied cue (7.7 s) is LONGER than the clip (6.0 s).  A negative
    # lead would mean "start after the lockscreen"; that is exactly what the
    # owner does not want.  Start at the first confirmed video frame instead, so
    # the cue plays DURING the preloading video and only its tail follows the
    # lockscreen.
    if lead < 0.0:
        lead = 0.0
    if lead > clip_s:
        lead = clip_s
    return lead


def _handoff_mtime():
    """Seconds since the UI handoff receipt was written, or None."""
    try:
        return max(0.0, time.time() - HANDOFF.stat().st_mtime)
    except OSError:
        return None


def do_boot():
    RUNTIME.mkdir(parents=True, exist_ok=True)
    done_file = RUNTIME / 'boot-sound-attempted'
    with (RUNTIME / 'boot-sound.lock').open('a+') as fd:
        fcntl.flock(fd, fcntl.LOCK_EX)
        if done_file.exists():
            record('boot', 'already_attempted'); return 0
        started = time.monotonic()
        deadline = started + WAIT_SECONDS
        handoff = False
        route_detail = 'not checked'
        route_ok = False
        while True:
            handoff = ready_handoff()
            if handoff:
                route_ok, route_detail = audio_route_ready()
                if route_ok:
                    break
            if time.monotonic() >= deadline:
                record('boot', 'not_ready_before_deadline', waited_seconds=WAIT_SECONDS,
                       handoff=handoff, detail=route_detail)
                return 7
            time.sleep(0.5)
        # Only one attempt per boot even if playback fails. Prevents repeated
        # loud restart loops when the audio device is broken or unavailable.
        done_file.write_text(str(int(time.time())) + '\n')
        # PWNAGE-SSP: the operator asked for the cue to land as the lockscreen
        # arrives, not after it has been unlocked.  Whether that is true is
        # measured here (cue start relative to the UI handoff receipt, and to
        # the first /run/nuxel-lockscreen receipt if present) so the offset can
        # be tuned from evidence instead of guessed.
        timing = {"waited_s": round(time.monotonic() - started, 3),
                  "cue_started_after_handoff_s": _handoff_mtime()}
        try:
            lock_receipt = Path('/run/nuxel-lockscreen')
            if lock_receipt.exists():
                timing["cue_started_after_lockscreen_s"] = round(
                    max(0.0, time.time() - lock_receipt.stat().st_mtime), 3)
        except OSError:
            pass
        # Start the cue just before the preloading video hands over to the
        # lockscreen: the cue then plays WHILE nuxel-preloading-screen.mp4 is
        # still on the glass and ends as the real lockscreen is revealed.
        wait_s = _cue_wait_seconds()
        timing["cue_lead_s"] = round(wait_s, 3)
        timing["cinema_active_at_play"] = _cinema_active()
        if wait_s > 0.0:
            # Anchor the lead to the moment the video is confirmed ON the glass
            # ('covered'), not to the controller's earlier 'starting' write.
            # The document only changes again when the video ends.
            cover_deadline = time.monotonic() + 5.0
            while time.monotonic() < cover_deadline and _cinema_active():
                try:
                    doc = json.loads(CINEMA_OVERLAY.read_text())
                except (OSError, ValueError):
                    doc = {}
                if isinstance(doc, dict) and doc.get('state') == 'covered':
                    break
                time.sleep(0.05)
            wait_until = time.monotonic() + wait_s
            while _cinema_active() and time.monotonic() < wait_until:
                time.sleep(0.05)
            timing["cinema_wait_s"] = round(max(0.0, wait_until - time.monotonic()), 3)
            timing["cinema_active_at_play"] = _cinema_active()
        ok = play_via_manager('boot', BOOT_PCM_PERCENT)
        record('boot', 'played' if ok else 'play_failed', timing=timing,
               pcm_gain_percent=BOOT_PCM_PERCENT, audible='unverified')
        if ok:
            return 0
        return play('boot', BOOT_PCM_PERCENT)


def do_volume(level):
    RUNTIME.mkdir(parents=True, exist_ok=True)
    if play_via_manager('volume', 100):
        return 0
    lock_path = RUNTIME / 'volume-sound.lock'
    with lock_path.open('a+') as fd:
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return 0  # suppress overlapping feedback while last cue plays
        # The actual ALSA mixer was already set to level by button manager.
        # The PipeWire sink follows the owner policy (100% ceiling, 50% default);
        # do not multiply it by a second software attenuation.
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
