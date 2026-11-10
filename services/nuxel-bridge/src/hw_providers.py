#!/usr/bin/env python3
"""Privileged hardware providers for the Nuxel HTTP bridge (api.py).

The D-Bus bridge runs as the ``nuxel-bridge`` user inside a hardened unit
(PrivateDevices=true, ProtectKernelTunables=true), so it cannot open
``/dev/snd``, write ``/sys/class/rfkill/*/soft`` or start ``bluetooth.service``.
The HTTP bridge (api.py) runs as root with ``PrivateDevices=no`` precisely so
one narrow, audited place can perform those real hardware operations.

Every subprocess uses an argv list (no shell), a bounded timeout, and strict
input validation.  Nothing here flashes a kernel/partition, wipes data, invents
a device, or claims a fix/route is audible without an observation.
"""
from __future__ import annotations

import fcntl
import json
import os
import re
import select
import subprocess
import sys
import threading
import time

# Shared with nuxel-soundd.  The deployed module lives at
# /usr/lib/nuxel/nuxel_audio_outputs.py.
for _cand in ("/usr/lib/nuxel",
              os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "nuxel-sound"))):
    if os.path.isdir(_cand) and _cand not in sys.path:
        sys.path.insert(0, _cand)
try:
    from nuxel_audio_outputs import parse_dp_audio_info, parse_dp_pcm
except ImportError:  # pragma: no cover - provider still reports raw evidence
    parse_dp_audio_info = None  # type: ignore
    parse_dp_pcm = None  # type: ignore

from gnss_inventory import (
    PROTOCOL,
)

# Owner-approved ceiling, shared with configs/nuxel/audio/audio.json
# (``safety.volume_cap_percent``).  The 25% low-volume bring-up cap was retired
# on 2026-10-30 after the CS35L41 speaker path became owner-confirmed audible.
# The default level is 50%.
DEFAULT_VOLUME_CAP_PERCENT = 100

# MADERA/CS47L93 playback-volume control names, in priority order.  These are
# only ever used as *candidates*; the provider runs ``amixer scontrols`` on the
# real card and picks the first name it actually observes, so no control name
# is invented.
VOLUME_CONTROL_CANDIDATES = (
    "HPOUT1 Digital Volume",
    "HPOUT2 Digital Volume",
    "HPOUT1 Digital",
    "HPOUT2 Digital",
    "DAC1 Playback Volume",
    "DAC2 Playback Volume",
    "DAC Playback Volume",
    "Speaker Playback Volume",
    "Playback Volume",
    "PCM Playback Volume",
    "Master Playback Volume",
    "Nuxel Safe Volume",
)
# Additional loose pattern for discovery (a real "Playback Volume" element on
# the card that is not in the explicit candidate list).
VOLUME_CONTROL_PATTERN = re.compile(
    r"(digital|playback|volume|speaker|spk|hpout|dac)", re.IGNORECASE)


class AudioProvider:
    """Authoritative Nuxel S10+ audio provider (PipeWire-first, ALSA fallback).

    The live image runs PipeWire + WirePlumber as root with its runtime under
    /run/nuxel-wayland, and the actual playback sink is the static ALSA PCM
    ``hw:0,1`` (RDMA1).  When that PipeWire graph is reachable this provider
    reports it and drives volume/mute/test-audio through it, because direct
    ALSA opens fail with EBUSY while PipeWire owns the device.

    If PipeWire is not reachable (early boot, broken session, or the offline
    VM fixtures), the provider falls back to the original bounded-amixer ALSA
    inventory so the UI still shows real card/PCM truth instead of a fake.
    """

    def __init__(self, root="/", card=0, amixer="/usr/sbin/amixer",
                 timeout=4.0, volume_cap=DEFAULT_VOLUME_CAP_PERCENT,
                 pw_runtime="/run/nuxel-wayland"):
        self.root = root
        self.card = card
        self.amixer = amixer
        self.timeout = float(timeout)
        self.volume_cap = int(volume_cap)
        self.pw_runtime = pw_runtime
        self._control_cache = None
        self._control_cache_valid = False
        # MADERA's name-based sget can sleep in D-state; the numid form is fast.
        self._control_numid = None
        self._control_min = None
        self._control_max = None
        self._control_channels = None
        self._pw_status_cache = None
        self._pw_status_cache_at = 0.0

    # ---- generic helpers --------------------------------------------------
    def _abs(self, rel):
        return os.path.join(self.root, rel.lstrip("/")) if rel.startswith("/") else rel

    def _read(self, rel):
        try:
            with open(self._abs(rel), "r") as f:
                return f.read().strip()
        except OSError:
            return None

    def _exists(self, rel):
        return os.path.exists(self._abs(rel))

    def _pipewire_env(self):
        env = dict(os.environ)
        env["PATH"] = "/usr/sbin:/usr/bin:/sbin:/bin"
        env["LANG"] = "C"
        env["XDG_RUNTIME_DIR"] = self.pw_runtime
        env["PIPEWIRE_RUNTIME_DIR"] = self.pw_runtime
        env["PULSE_SERVER"] = "unix:%s/pulse/native" % self.pw_runtime
        return env

    def _run_bounded(self, argv, timeout=None, env=None):
        """subprocess.run with a real timeout; used only for PipeWire CLIs
        (wpctl/pw-dump/gst-launch), never for amixer, whose D-state needs the
        abandon-child runner below."""
        try:
            return subprocess.run(
                argv, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                text=True, timeout=float(timeout or self.timeout),
                env=env or self._pipewire_env()), None
        except subprocess.TimeoutExpired:
            return None, "timeout"
        except (OSError, subprocess.SubprocessError) as exc:
            return None, str(exc)

    def _pipewire_available(self):
        return self._exists("%s/pipewire-0" % self.pw_runtime)

    # ---- cards / PCMs ----------------------------------------------------
    def _cards(self):
        cards = []
        text = self._read("/proc/asound/cards") or ""
        for line in text.splitlines():
            m = re.match(r"\s*(\d+)\s+\[([^\]]*)\]\s*:\s*(.*)", line)
            if not m:
                continue
            cards.append({
                "index": int(m.group(1)),
                "id": m.group(2).strip(),
                "name": m.group(3).strip(),
            })
        return cards

    def _pcms(self):
        pcms = {"playback": [], "capture": []}
        text = self._read("/proc/asound/pcm") or ""
        for line in text.splitlines():
            m = re.match(r"(\d+)-(\d+):\s+([^\s]+)\s+.*?:\s+:\s+(playback|capture)\s+\d+", line)
            if not m:
                continue
            pcms[m.group(4)].append({
                "card": int(m.group(1)),
                "device": int(m.group(2)),
                "id": m.group(3),
            })
        return pcms

    # ---- PipeWire session / sinks ---------------------------------------
    def _wpctl_status(self, force=False):
        now = time.time()
        if not force and self._pw_status_cache is not None and now - self._pw_status_cache_at < 1.0:
            return self._pw_status_cache
        proc, err = self._run_bounded(["wpctl", "status"])
        if err:
            self._pw_status_cache = {"available": False, "error": err, "sinks": [], "sources": [], "streams": [], "default_sink_id": None}
            self._pw_status_cache_at = now
            return self._pw_status_cache
        out = proc.stdout or ""
        sinks = []
        sources = []
        streams = []
        default_sink_id = None
        section = None
        for line in out.splitlines():
            if re.search(r"\bSinks\s*:", line):
                section = "sinks"; continue
            if re.search(r"\bSources\s*:", line):
                section = "sources"; continue
            if re.search(r"\bStreams\s*:", line):
                section = "streams"; continue
            if re.search(r"\b(Filters|Video|Settings)\s*:", line):
                section = None; continue
            if not section or not line.strip():
                continue
            # wpctl status uses box-drawing characters and indentation around
            # the numeric id (e.g. "│  *   31. S10+ speaker ...").  Match the
            # first "N. description" token anywhere in the line.
            m = re.search(r"(\d+)\.\s+([^\n]+)$", line)
            if not m:
                continue
            node_id = int(m.group(1))
            desc = m.group(2).strip()
            # Strip trailing WirePlumber metadata like [vol: 1.00].
            desc = re.sub(r"\s*\[.*\]\s*$", "", desc)
            is_default = ("*" in line)
            item = {"id": node_id, "description": desc, "default": is_default}
            if section == "sinks":
                sinks.append(item)
                if is_default:
                    default_sink_id = node_id
            elif section == "sources":
                sources.append(item)
            elif section == "streams":
                streams.append(item)
        # Fallback: PipeWire metadata default sink may not be starred; use Settings.
        if default_sink_id is None:
            for line in out.splitlines():
                if "Audio/Sink" in line:
                    m = re.search(r"(\d+)\.\s+Audio/Sink\s+(\S+)", line)
                    if m:
                        default_sink_id = int(m.group(1))
        self._pw_status_cache = {
            "available": True,
            "error": None,
            "sinks": sinks,
            "sources": sources,
            "streams": streams,
            "default_sink_id": default_sink_id,
            "raw": out[:2000],
        }
        self._pw_status_cache_at = now
        return self._pw_status_cache

    def _default_sink_volume_mute(self):
        """Return (volume_float, muted_bool, node_id) for the default sink."""
        proc, err = self._run_bounded(["wpctl", "get-volume", "@DEFAULT_AUDIO_SINK@"])
        volume = None
        if not err and proc:
            m = re.search(r"Volume:\s*([0-9]*\.?[0-9]+)", proc.stdout or "")
            if m:
                volume = float(m.group(1))
        # wpctl in this WirePlumber has no get-mute; read the sink Props from
        # pw-dump so mute is real, not guessed.
        muted = False
        node_id = None
        proc, err = self._run_bounded(["pw-dump"], timeout=6.0)
        if not err and proc:
            try:
                import json
                dump = json.loads(proc.stdout or "[]")
            except ValueError:
                dump = []
            default_meta = None
            sink_nodes = []
            for obj in dump:
                if not isinstance(obj, dict):
                    continue
                info = obj.get("info") or {}
                props = info.get("props") or {}
                if props.get("media.class") == "Audio/Sink":
                    sink_nodes.append(obj)
                if obj.get("type") == "PipeWire:Interface:Metadata":
                    metas = obj.get("metadata") or []
                    for m in metas:
                        if m.get("key") == "default.audio.sink":
                            default_meta = m.get("value")
            for obj in sink_nodes:
                oid = obj.get("id")
                info = obj.get("info") or {}
                props = info.get("props") or {}
                params = info.get("params") or {}
                props_list = params.get("Props") or []
                is_default = (default_meta is not None and str(default_meta).startswith(str(oid))) or (oid and str(default_meta) == str(oid))
                if is_default or node_id is None:
                    node_id = oid
                    for p in props_list:
                        if isinstance(p, dict) and "mute" in p:
                            muted = bool(p.get("mute"))
                            break
                    if is_default:
                        break
        return volume, muted, node_id

    def _sound_mode_ok(self):
        mode = self._read("/var/lib/nuxel/audio/sound-mode")
        return mode not in ("silent", "vibrate")

    def _ensure_default_sink(self):
        """Make the static RDMA1 sink the PipeWire default node, then verify it.

        After a cold boot WirePlumber can publish the sink without selecting a
        default.  ``pw-play`` then fails with "Translate ID error: '-1' is not
        a valid ID (returned by default-nodes-api)" while the sink is present.
        Selecting by stable node name is idempotent.  A successful pactl exit
        code alone is not enough: read the live default back and require the
        exact node name, so playback cannot silently land on another output.

        Three conditions must hold, not just the exit code:
          * the sink exists AND is the RDMA1 48 kHz node (a graph/sink rate
            mismatch would resample despite the hardware capability);
          * ``set-default-sink`` returned success;
          * ``get-default-sink`` reads back exactly the expected name.  A
            literal ``null`` (what WirePlumber prints when no default node is
            selected) is a failure, not a selected sink.
        """
        expected = "alsa_output.hw_0_1"
        proc, err = self._run_bounded(
            ["pactl", "list", "short", "sinks"], timeout=4.0)
        if err or proc is None or proc.returncode != 0:
            return False
        sink_line = None
        for line in (proc.stdout or "").splitlines():
            cols = line.split("\t")
            if len(cols) > 3 and cols[1] == expected:
                sink_line = line
                break
        if sink_line is None:
            return False
        # cols[3] is the sample spec, e.g. "s16le 2ch 48000Hz".
        if "48000Hz" not in sink_line:
            return False
        proc, err = self._run_bounded(
            ["pactl", "set-default-sink", expected], timeout=4.0)
        if err or proc is None or proc.returncode != 0:
            return False
        proc, err = self._run_bounded(
            ["pactl", "get-default-sink"], timeout=4.0)
        if err or proc is None or proc.returncode != 0:
            return False
        value = (proc.stdout or "").strip()
        return value == expected

    def _sink_volume_within_cap(self):
        """Return the current default-sink volume, or None if it cannot be read."""
        proc, err = self._run_bounded(
            ["wpctl", "get-volume", "@DEFAULT_AUDIO_SINK@"], timeout=4.0)
        if err or proc is None or proc.returncode != 0:
            return None
        m = re.search(r"Volume:\s*([0-9]*\.?[0-9]+)", proc.stdout or "")
        if not m:
            return None
        return float(m.group(1))


    def _cs35l41_output_patch(self):
        """Re-apply the owner-confirmed CS35L41 clock/boost/output patch.

        The CS35L41 driver's hw_free mutes the amplifier output stage after
        every completed playback (DIG_VOL_CTRL leaves 0 dB and AMP_OUT_MUTE
        re-asserts).  A cold DAPM speaker path can also swallow the 366 ms cue.
        The helper repairs the driver cache, applies the proven registers and
        keeps an inaudible stream on the speaker path until DAPM SPEAKER=On.
        It is the single audited pre-play path for every short cue.
        """
        script = "/usr/lib/nuxel/nuxel-cs35l41-apply.sh"
        if not os.path.isfile(self._abs(script)) or not os.access(self._abs(script), os.X_OK):
            return False, "CS35L41 patch helper missing at %s" % script
        proc, err = self._run_bounded([self._abs(script)], timeout=12.0)
        if err or proc is None or proc.returncode != 0:
            detail = ((proc.stderr or "").strip() or (proc.stdout or "").strip()) if proc is not None else (err or "no process")
            return False, "CS35L41 patch re-apply failed: %s" % detail[-200:]
        return True, "CS35L41 output stage re-applied"

    def _pipewire_play(self, asset, gain_percent):
        """Play an MP3 through the default PipeWire sink with ``pw-play``.

        The earlier implementation used ``gst-launch-1.0 ... ! pulsesink`` and
        killed it after a 2.5 s bounded window because pulsesink never posts
        EOS on this image.  On the S10+ that window starts before decodebin
        has linked, so the UI Test Audio path produced no samples at all while
        a direct ``pw-play`` on the same sink was audible.  ``pw-play`` blocks
        until EOS, applies the decoder gain itself, exits cleanly for this
        short cue, and therefore reports something the caller can trust.

        The result is honest: rc=0 means the player finished, never that the
        owner heard anything.
        """
        import shutil

        asset = self._abs(asset)
        if not os.path.isfile(asset):
            return False, "missing asset %s" % asset
        if not self._sound_mode_ok():
            return False, "sound mode muted"
        if not self._ensure_default_sink():
            return False, "PipeWire default sink alsa_output.hw_0_1 is unavailable or could not be selected"
        volume = self._sink_volume_within_cap()
        if volume is None:
            return False, "cannot read the PipeWire default-sink volume"
        cap = self.volume_cap / 100.0
        if volume > cap + 0.0001:
            # The route script owns the hardware/session setup.  Do not silently
            # raise or lower a live level here; refuse playback above the safety
            # ceiling and let the caller surface the real routing defect.
            return False, "PipeWire sink volume %.3f exceeds safety cap %.2f; reapply the audio route" % (volume, cap)
        patched, patch_detail = self._cs35l41_output_patch()
        if not patched:
            return False, patch_detail
        gain = max(0.0, min(1.0, max(0, int(gain_percent)) / 100.0))
        player = shutil.which("pw-play") or "/usr/bin/pw-play"
        argv = [player, "--volume", "%.3f" % gain, asset]
        proc, err = self._run_bounded(argv, timeout=8.0)
        if err or proc is None:
            return False, "pw-play failed: %s" % (err or "no process")
        detail = ((proc.stderr or "").strip() or (proc.stdout or "").strip()
                  or "pw-play completed")[-400:]
        if proc.returncode != 0:
            return False, "pw-play rc=%d; %s" % (proc.returncode, detail)
        return True, "pw-play completed; " + detail

    # ---- ALSA fallback ----------------------------------------------------
    def _service_state(self):
        pw_avail = self._pipewire_available()
        if pw_avail:
            return {
                "backend": "pipewire",
                "sound_server": "pipewire",
                "units_present": ["pipewire", "pipewire-pulse", "wireplumber"],
                "units_active": ["pipewire", "pipewire-pulse", "wireplumber"],
            }
        units = (
            ("pipewire", "/usr/lib/systemd/system/pipewire.service"),
            ("pipewire-pulse", "/usr/lib/systemd/system/pipewire-pulse.service"),
            ("wireplumber", "/usr/lib/systemd/system/wireplumber.service"),
            ("pulseaudio", "/usr/lib/systemd/system/pulseaudio.service"),
        )
        present = [name for name, path in units if self._exists(path)]
        active = []
        for name, _ in units:
            found = False
            for root in ("/run/systemd/system/", "/etc/systemd/system/"):
                for suffix in (".service", ".socket"):
                    if self._exists(os.path.join(root, name + suffix)):
                        active.append(name)
                        found = True
                        break
                if found:
                    break
        if not present:
            backend = "alsa-direct"
            server = "unavailable"
        else:
            backend = "session-manager"
            server = "active" if active else "stopped"
        return {
            "backend": backend,
            "sound_server": server,
            "units_present": present,
            "units_active": active,
        }

    def _run_amixer(self, *args):
        """Run amixer without ever blocking on a D-state child.

        See the pre-PWNAGE-38000 implementation: it reads the pipes with
        select() and abandons the child on deadline because SIGKILL has no
        effect on a kernel I2C D-state child."""
        argv = [self.amixer, "-c", str(self.card)] + [str(a) for a in args]
        try:
            proc = subprocess.Popen(
                argv, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                env={"PATH": "/usr/sbin:/usr/bin:/sbin:/bin", "LANG": "C"},
                start_new_session=True)
        except (OSError, subprocess.SubprocessError) as exc:
            return None, "amixer unavailable: %s" % exc
        for stream in (proc.stdout, proc.stderr):
            fd = stream.fileno()
            flags = fcntl.fcntl(fd, fcntl.F_GETFL)
            fcntl.fcntl(fd, fcntl.F_SETFL, flags | os.O_NONBLOCK)
        out = bytearray()
        err = bytearray()
        open_streams = {proc.stdout, proc.stderr}
        deadline = time.time() + self.timeout
        while open_streams and time.time() < deadline:
            try:
                ready, _, _ = select.select(list(open_streams), [], [], 0.2)
            except (OSError, ValueError):
                break
            for stream in ready:
                try:
                    chunk = os.read(stream.fileno(), 65536)
                except (BlockingIOError, OSError):
                    continue
                if not chunk:
                    open_streams.discard(stream)
                    continue
                (out if stream is proc.stdout else err).extend(chunk)
        if time.time() >= deadline:
            try:
                os.killpg(proc.pid, 9)
            except (OSError, AttributeError):
                try:
                    proc.kill()
                except OSError:
                    pass
            return None, "amixer timed out after %.0fs (kernel control may be wedged)" % self.timeout
        rc = proc.poll()
        if rc is not None and rc != 0:
            return None, (err or out).decode("utf-8", "replace").strip() or ("amixer rc=%d" % rc)
        return out.decode("utf-8", "replace"), None

    def _probe_candidates(self):
        if self._control_cache_valid:
            return self._control_cache
        out, err = self._run_amixer("controls")
        if not err and out:
            control_map = {}
            for line in out.splitlines():
                m = re.search(r"numid=(\d+).*name='([^']+)'", line)
                if m:
                    control_map[m.group(2)] = int(m.group(1))
            chosen = None
            for candidate in VOLUME_CONTROL_CANDIDATES:
                if candidate in control_map:
                    chosen = candidate
                    break
            if chosen is None:
                ranked = []
                for name in control_map:
                    low = name.lower()
                    if "volume" not in low or "switch" in low:
                        continue
                    if not VOLUME_CONTROL_PATTERN.search(name):
                        continue
                    score = 0
                    if "hpout1" in low: score += 40
                    elif "hpout" in low: score += 30
                    elif "speaker" in low or "spk" in low: score += 20
                    elif "dac" in low: score += 10
                    if "digital" in low: score += 5
                    ranked.append((-score, name))
                if ranked:
                    chosen = sorted(ranked)[0][1]
            if chosen:
                self._control_cache = chosen
                self._control_numid = control_map[chosen]
                self._control_cache_valid = True
                return chosen
        for candidate in VOLUME_CONTROL_CANDIDATES:
            out, err = self._run_amixer("sget", candidate)
            if err:
                continue
            if out and "unable to find" not in out.lower():
                self._control_cache = candidate
                self._control_cache_valid = True
                return candidate
        self._control_cache_valid = True
        return None

    def _parse_amixer_value(self, control):
        text = None
        if self._control_numid is not None and control == self._control_cache:
            out, err = self._run_amixer("cget", "numid=%d" % self._control_numid)
            if err:
                return None, err
            text = out or ""
            mm = re.search(r"min=(-?\d+),max=(-?\d+)", text)
            mv = re.search(r"^\s*:\s*values=([\d,]+)", text, re.M)
            if not mm or not mv:
                return None, "cannot parse numid control %d" % self._control_numid
            lo, hi = int(mm.group(1)), int(mm.group(2))
            vals = [int(v) for v in mv.group(1).split(",") if v != ""]
            if not vals or hi <= lo:
                return None, "invalid numid control range"
            self._control_min, self._control_max = lo, hi
            self._control_channels = len(vals)
            avg = sum(vals) / float(len(vals))
            percent = int(round((avg - lo) * 100.0 / (hi - lo)))
            return {
                "control": control,
                "numid": self._control_numid,
                "percent": max(0, min(100, percent)),
                "muted": None,
                "raw": text.strip()[:240],
            }, None
        out, err = self._run_amixer("sget", control)
        if err:
            return None, err
        text = out or ""
        if "unable to find" in text.lower():
            return None, "control %r not found" % control
        m = re.search(r"\[(-?\d+)%\]", text)
        percent = int(m.group(1)) if m else None
        muted = bool(re.search(r"\[off\]", text))
        return {
            "control": control,
            "percent": percent,
            "muted": muted,
            "raw": text.strip()[:200],
        }, None

    def capture_route(self):
        """Report whether the session audio server exposes a capture source."""
        if self._pipewire_available():
            status = self._wpctl_status(force=True)
            return {
                "success": True,
                "available": bool(status.get("sources")),
                "sources": [s["description"] for s in status.get("sources", [])],
                "reason": None if status.get("sources") else "no capture source routed by PipeWire",
            }
        # ALSA fallback: read-only; opening a capture PCM can block on this kernel.
        return {"success": True, "available": False, "sources": [],
                "reason": "PipeWire capture session unavailable"}

    def _hdmi_audio_status(self):
        """Read the real DP/HDMI audio path (read-only, no dummy sink).

        The S10+ exposes a ``DP Audio`` ALSA PCM through the Samsung DP driver,
        and the driver publishes ``ch_hdmi_audio`` when the sink advertises
        audio and the audio infoframe is active.  A visible PipeWire sink is
        never invented here: if the DP link or the WirePlumber route is missing,
        the blocker is reported instead.
        """
        pcm_text = self._read("/proc/asound/pcm") or ""
        parsed_pcm = parse_dp_pcm(pcm_text) if parse_dp_pcm is not None else None
        pcm_line = (parsed_pcm or {}).get("line")
        ch_switch = self._read("/sys/class/switch/ch_hdmi_audio/state")
        secdp = self._read("/sys/class/switch/secdp/state")
        extcon = self._read("/sys/class/extcon/extcon0/state") or ""
        dp_link = bool(secdp and secdp.strip() == "1" and "DP=1" in extcon)
        try:
            ch_value = int(ch_switch) if ch_switch is not None else None
        except (TypeError, ValueError):
            ch_value = None
        if parse_dp_audio_info is not None:
            audio_info = parse_dp_audio_info(ch_value, dp_link, bool(pcm_line))
        else:
            audio_info = {"available": bool(dp_link and pcm_line and ch_value and ch_value > 0),
                          "reason": None, "raw": ch_value}
        available = bool(audio_info.get("available"))
        blockers = []
        if not dp_link:
            blockers.append("DP link is not ready (secdp=%s, extcon=%s)"
                            % (secdp, extcon or "unknown"))
        if not pcm_line:
            blockers.append("kernel exposes no 'DP Audio' PCM in /proc/asound/pcm")
        if pcm_line and not available:
            blockers.append(str(audio_info.get("reason") or
                                "DP sink advertises no usable LPCM endpoint (ch_hdmi_audio=%s)"
                                % ch_switch))
        sink = None
        if available and self._pipewire_available():
            proc, err = self._run_bounded(["pactl", "list", "short", "sinks"], timeout=4.0)
            if not err and proc is not None and proc.returncode == 0:
                for line in (proc.stdout or "").splitlines():
                    cols = line.split("	")
                    if len(cols) > 1 and re.search(r"(hdmi|displayport|dp)", cols[1], re.I):
                        sink = {"id": cols[0], "name": cols[1],
                                "sample_spec": cols[3] if len(cols) > 3 else None}
                        break
                if sink is None:
                    blockers.append("DP link is active but PipeWire exposes no HDMI/DP sink")
                    available = False
        return {
            "available": available,
            "dp_link": dp_link,
            "secdp": secdp,
            "extcon": extcon,
            "ch_hdmi_audio": ch_value,
            "ch_hdmi_audio_hex": (None if ch_value is None else "0x%08x" % (ch_value & 0xffffffff)),
            "audio_info": audio_info,
            "pcm": pcm_line,
            "pcm_present": bool(pcm_line),
            "pcm_device": parsed_pcm,
            "sink": sink,
            "blockers": blockers,
            "blocker": "; ".join(blockers) if blockers else None,
        }

    # ---- public API ------------------------------------------------------
    def get_status(self):
        cards = self._cards()
        pcms = self._pcms()
        svc = self._service_state()

        base = {
            "success": True,
            "state": "present" if cards else "unavailable",
            "backend": svc["backend"],
            "sound_server": svc["sound_server"],
            "sound_server_units_present": svc["units_present"],
            "sound_server_units_active": svc["units_active"],
            "cards": cards,
            "playback_devices": pcms["playback"],
            "capture_devices": pcms["capture"],
            "volume_cap_percent": self.volume_cap,
            "timestamp": time.time(),
        }

        if self._pipewire_available():
            status = self._wpctl_status(force=True)
            sinks = status.get("sinks", [])
            sources = status.get("sources", [])
            vol, muted, node_id = self._default_sink_volume_mute()
            volume_percent = int(round((vol or 0.0) * 100.0))
            # Cap the reported value for UI clamping, but report the real value too.
            selected = next((s for s in sinks if s.get("default")), sinks[0] if sinks else None)
            return {
                **base,
                "state": "present" if cards and sinks else ("present" if cards else "unavailable"),
                "backend": "pipewire",
                "sound_server": "pipewire",
                "outputs": sinks,
                "selected_output": selected,
                "capture_sources": sources,
                "volume_control": "pipewire:@DEFAULT_AUDIO_SINK@",
                "volume_percent": min(volume_percent, self.volume_cap),
                "volume_real_percent": volume_percent,
                "muted": muted,
                "volume_supported": bool(sinks),
                "mute_supported": bool(sinks),
                "mute_blocker": None,
                "unmute_supported": bool(sinks),
                "playback_available": bool(sinks),
                "hdmi_audio": self._hdmi_audio_status(),
                "detail": "PipeWire default sink: %s" % (selected["description"] if selected else "none"),
            }

        # ALSA fallback (unchanged behaviour).
        volume_control = self._probe_candidates()
        volume = None
        mixer_error = None
        if volume_control:
            volume, verr = self._parse_amixer_value(volume_control)
            if verr:
                mixer_error = verr
        playback = pcms["playback"]
        volume_supported = bool(volume_control and volume and volume["percent"] is not None)
        detail = []
        if not cards:
            detail.append("no ALSA cards in /proc/asound/cards")
        elif not playback:
            detail.append("no playback PCM in /proc/asound/pcm")
        if mixer_error:
            detail.append("mixer read failed: %s" % mixer_error)
        elif not volume_control:
            detail.append("no safe playback volume control discovered on card %d" % self.card)
        return {
            **base,
            "backend": "alsa-direct",
            "sound_server": "unavailable",
            "outputs": [],
            "selected_output": None,
            "capture_sources": [],
            "volume_control": volume_control,
            "volume_percent": volume["percent"] if volume else None,
            "muted": volume["muted"] if volume else None,
            "volume_supported": volume_supported,
            "mute_supported": False,
            "mute_blocker": ("MADERA HPOUT1 Digital unmute hangs the kernel I2C control "
                             "(measured 2026-10-27); mute is not offered to avoid wedging the codec") if volume_control else None,
            "unmute_supported": False,
            "playback_available": bool(cards and playback),
            "hdmi_audio": self._hdmi_audio_status(),
            "detail": "; ".join(detail) if detail else None,
            "mixer_error": mixer_error,
        }

    def set_volume(self, percent):
        try:
            percent = int(percent)
        except (TypeError, ValueError):
            return {"success": False, "error": "invalid volume value"}
        percent = max(0, min(self.volume_cap, percent))

        if self._pipewire_available():
            if not self._ensure_default_sink():
                return {"success": False,
                        "error": "PipeWire default sink alsa_output.hw_0_1 is unavailable or could not be selected",
                        "control": "pipewire:@DEFAULT_AUDIO_SINK@"}
            vol = percent / 100.0
            proc, err = self._run_bounded(
                ["wpctl", "set-volume", "@DEFAULT_AUDIO_SINK@", "%.3f" % vol])
            if err or proc is None or proc.returncode != 0:
                return {"success": False,
                        "error": err or (proc.stderr or "").strip() or "wpctl set-volume failed",
                        "control": "pipewire:@DEFAULT_AUDIO_SINK@"}
            new_vol, muted, node_id = self._default_sink_volume_mute()
            new_percent = int(round((new_vol or 0.0) * 100.0))
            return {
                "success": True,
                "control": "pipewire:@DEFAULT_AUDIO_SINK@",
                "volume_percent": new_percent,
                "requested_percent": percent,
                "muted": muted,
            }

        control = self._probe_candidates()
        if not control:
            return {"success": False, "error": "no safe playback volume control discovered"}
        if self._control_numid is not None and control == self._control_cache:
            read, rerr = self._parse_amixer_value(control)
            if rerr or not read:
                return {"success": False, "error": rerr, "control": control}
            lo, hi = self._control_min, self._control_max
            raw = int(round(lo + (hi - lo) * percent / 100.0))
            channels = self._control_channels or 1
            _, err = self._run_amixer(
                "cset", "numid=%d" % self._control_numid,
                ",".join([str(raw)] * channels))
        else:
            _, err = self._run_amixer("sset", control, "%d%%" % percent)
        if err:
            return {"success": False, "error": err, "control": control}
        read, rerr = self._parse_amixer_value(control)
        return {
            "success": rerr is None and read is not None and read["percent"] == percent,
            "control": control,
            "volume_percent": read["percent"] if read else None,
            "requested_percent": percent,
            "error": rerr,
        }

    def set_muted(self, muted):
        muted = bool(muted)

        if self._pipewire_available():
            val = "1" if muted else "0"
            proc, err = self._run_bounded(
                ["wpctl", "set-mute", "@DEFAULT_AUDIO_SINK@", val])
            if err or proc is None or proc.returncode != 0:
                return {"success": False,
                        "error": err or (proc.stderr or "").strip() or "wpctl set-mute failed",
                        "error_code": "MUTE_FAILED"}
            new_vol, new_muted, node_id = self._default_sink_volume_mute()
            return {
                "success": True,
                "control": "pipewire:@DEFAULT_AUDIO_SINK@",
                "muted": new_muted,
                "requested_muted": muted,
            }

        if not muted:
            return {"success": False,
                    "error": "unmute is unsupported on this codec path "
                             "(MADERA HPOUT1 Digital unmute hangs the kernel control)",
                    "error_code": "UNMUTE_UNSUPPORTED"}
        control = self._probe_candidates()
        if not control:
            return {"success": False, "error": "no safe playback volume control discovered"}
        _, err = self._run_amixer("sset", control, "mute")
        if err:
            return {"success": False, "error": err, "control": control}
        read, rerr = self._parse_amixer_value(control)
        return {
            "success": rerr is None and read is not None and read["muted"] is True,
            "control": control,
            "muted": read["muted"] if read else None,
            "requested_muted": muted,
            "error": rerr,
        }

    def set_output(self, target):
        """Select a real output route; never create a phantom HDMI sink."""
        target = str(target or "").strip().lower()
        if target in ("speaker", "phone", "internal"):
            ok = self._ensure_default_sink() if self._pipewire_available() else False
            if not ok:
                return {"success": False, "error": "SPEAKER_ROUTE_UNAVAILABLE",
                        "detail": "the internal speaker sink could not be selected and verified"}
            return {"success": True, "output": "speaker",
                    "sink": "alsa_output.hw_0_1", "verified": True}
        if target in ("hdmi", "displayport", "dp", "external"):
            hdmi = self._hdmi_audio_status()
            if not hdmi.get("available"):
                return {"success": False, "error": "HDMI_AUDIO_UNAVAILABLE",
                        "detail": hdmi.get("blocker") or "HDMI/DP audio is not available",
                        "hdmi_audio": hdmi}
            sink = hdmi.get("sink") or {}
            name = sink.get("name")
            if not name:
                return {"success": False, "error": "HDMI_SINK_NOT_EXPOSED",
                        "detail": hdmi.get("blocker") or "no HDMI/DP PipeWire sink",
                        "hdmi_audio": hdmi}
            proc, err = self._run_bounded(["pactl", "set-default-sink", name], timeout=4.0)
            if err or proc is None or proc.returncode != 0:
                return {"success": False, "error": "HDMI_ROUTE_FAILED",
                        "detail": err or (proc.stderr or "").strip() or "set-default-sink failed",
                        "sink": name}
            proc, err = self._run_bounded(["pactl", "get-default-sink"], timeout=4.0)
            readback = (proc.stdout or "").strip() if proc is not None and not err else ""
            if readback != name:
                return {"success": False, "error": "HDMI_ROUTE_NOT_CONFIRMED",
                        "detail": "readback=%r expected=%r" % (readback, name),
                        "sink": name}
            return {"success": True, "output": "hdmi", "sink": name,
                    "verified": True, "hdmi_audio": hdmi}
        return {"success": False, "error": "INVALID_OUTPUT",
                "detail": "output must be speaker or hdmi"}

    def _route_ready(self, timeout=30.0):
        """Read-only route readiness via the same probe the boot cue uses.

        Settings -> Test Audio must not play into a half-applied route: a
        successful pw-play exit says nothing when Calliope is not MUB0 or a
        CS35L41 DSP1 has not booted.  The script itself is the single source
        of truth (`nuxel-audio-route.sh --check`), so no mixer names are
        duplicated here.
        """
        script = "/usr/lib/nuxel/nuxel-audio-route.sh"
        if not os.path.isfile(self._abs(script)):
            return False, "route check missing: %s" % script
        proc, err = self._run_bounded(
            [self._abs(script), "--wait", "%.0f" % max(1.0, timeout)],
            timeout=timeout + 10.0)
        if err or proc is None:
            return False, "route check failed: %s" % (err or "no process")
        text = ((proc.stderr or "") + (proc.stdout or "")).strip()
        if proc.returncode != 0:
            return False, "audio route not ready: %s" % text[-400:]
        return True, "route verified (MUB0, both DSP1s, 48 kHz sink)"

    def test_audio(self, asset="/usr/share/nuxel/assets/nuxel-pow.mp3", gain_percent=50):
        """Play the test asset through the currently selected output.

        Returns an HONEST result: 'played' means the player exited zero after
        sending the stream to the verified PipeWire sink; it does NOT assert
        that a human heard the sound."""
        if not self._sound_mode_ok():
            return {"success": False, "played": False,
                    "error": "sound mode is silent or vibrate",
                    "audible": "unverified"}
        if self._pipewire_available():
            ready, route_detail = self._route_ready()
            if not ready:
                return {"success": False, "played": False,
                        "error": route_detail,
                        "route": "pipewire:@DEFAULT_AUDIO_SINK@",
                        "asset": asset, "audible": "unverified"}
            ok, detail = self._pipewire_play(asset, gain_percent)
            return {"success": ok, "played": ok,
                    "detail": route_detail + "; " + detail,
                    "route": "pipewire:@DEFAULT_AUDIO_SINK@",
                    "asset": asset, "audible": "unverified"}
        return {"success": False, "played": False,
                "error": "PipeWire playback session unavailable",
                "audible": "unverified"}

class DisplayProvider:
    """Authoritative USB-C / DisplayPort / HDMI inventory (read-only).

    The S10+ does not expose DRM/KMS.  Its real external path is the Samsung
    vendor chain: max77705 Type-C -> USB-PD/DP Alt Mode VDM -> exynos-displayport
    -> 19050000.decon_t -> /dev/fb1.  This provider reports that path as it is,
    including the exact failing stage.  It never invents a monitor or a mode.
    """

    def __init__(self, root="/", control_status_path="/run/nuxel-display/status.json"):
        self.root = root
        self.control_status_path = control_status_path

    def _abs(self, rel):
        return os.path.join(self.root, rel.lstrip("/")) if rel.startswith("/") else rel

    def _read(self, rel):
        try:
            with open(self._abs(rel), "r") as f:
                return f.read().strip()
        except OSError:
            return None

    def _list(self, rel):
        try:
            return sorted(os.listdir(self._abs(rel)))
        except OSError:
            return []

    def _kernel_config(self, key):
        try:
            import gzip
            with gzip.open(self._abs("/proc/config.gz"), "rb") as f:
                cfg = f.read().decode("utf-8", "replace")
        except Exception:
            return "unknown"
        if key + "=y" in cfg:
            return "y"
        if key + "=m" in cfg:
            return "m"
        if "# %s is not set" % key in cfg:
            return "not_set"
        return "unknown"

    def _control_status(self):
        try:
            with open(self.control_status_path, "r") as f:
                doc = json.load(f)
            return doc if isinstance(doc, dict) else {}
        except (OSError, ValueError):
            return {}

    def panel_state(self):
        """Truthful panel on/off state for the Home wake/lock watcher."""
        bl_power = self._read("/sys/class/backlight/panel/bl_power")
        brightness = self._read("/sys/class/backlight/panel/brightness")
        state_text = self._read("/run/nuxel-wl-fb.state") or ""
        off = False
        try:
            if bl_power is not None and int(bl_power) != 0:
                off = True
        except (TypeError, ValueError):
            pass
        if not off and ("display=off" in state_text or "DISPLAY_SLEEP" in state_text):
            off = True
        return {
            "success": True,
            "off": off,
            "bl_power": bl_power,
            "brightness": brightness,
            "source": "panel-backlight",
        }

    def _import_model(self):
        try:
            import nuxel_display  # type: ignore
            return nuxel_display
        except Exception:
            pass
        here = os.path.dirname(os.path.abspath(__file__))
        candidates = (
            "/usr/lib/nuxel/nuxel-display",
            os.path.join(here, "..", "..", "nuxel-display", "lib"),
            os.path.join(here, "..", "..", "..", "services", "nuxel-display", "lib"),
        )
        for cand in candidates:
            cand = os.path.abspath(cand)
            if os.path.isdir(cand) and cand not in sys.path:
                sys.path.insert(0, cand)
                try:
                    import nuxel_display  # type: ignore
                    return nuxel_display
                except Exception:
                    pass
        return None

    def get_status(self):
        nd = self._import_model()
        drm_class_entries = self._list("/sys/class/drm")
        # /sys/class/drm/version exists whenever DRM core is built even when no
        # KMS driver/connector is registered.  Only card*/connector entries
        # prove a usable DRM output path.
        drm_entries = [e for e in drm_class_entries if e.startswith("card")]
        typec_ports = [p for p in self._list("/sys/class/typec")
                       if p.startswith("port") and "-" not in p]
        drm_kernel = self._kernel_config("CONFIG_DRM")
        drm_exynos_kernel = self._kernel_config("CONFIG_DRM_EXYNOS")
        typec_kernel = self._kernel_config("CONFIG_TYPEC")
        dp_kernel = self._kernel_config("CONFIG_EXYNOS_DISPLAYPORT")
        ctl = self._control_status()

        # Legacy keys remain present for older Settings builds.
        base = {
            "success": True,
            "drm_present": bool(drm_entries),
            "drm_entries": drm_entries,
            "drm_class_entries": drm_class_entries,
            "drm_kernel": drm_kernel,
            "drm_exynos_kernel": drm_exynos_kernel,
            "typec_kernel": typec_kernel,
            "displayport_kernel": dp_kernel,
            "type_c_port_count": len(typec_ports),
        }

        if nd is None:
            # Honest fallback: the model module is missing.
            ports = []
            for p in typec_ports:
                base_path = "/sys/class/typec/" + p
                ports.append({
                    "name": p,
                    "data_role": self._read(base_path + "/data_role"),
                    "power_role": self._read(base_path + "/power_role"),
                    "partner": self._read(base_path + "-partner/type"),
                })
            blockers = []
            if not drm_entries:
                blockers.append(
                    "no /sys/class/drm (CONFIG_DRM=%s); the S10+ external path is "
                    "decon_t/fb1, but the nuxel-display model module is unavailable"
                    % drm_kernel)
            base.update({
                "state": "MODEL_UNAVAILABLE",
                "type_c_ports": ports,
                "extcon": [],
                "mirror_supported": False,
                "desktop_supported": False,
                "supported_modes": [],
                "connector": None,
                "blocker": "; ".join(blockers) if blockers else None,
                "blockers": blockers,
            })
            return base

        snap = nd.read_snapshot(self.root)
        mode = nd.normalize_mode(ctl.get("mode") or "off") or "off"
        hardware_state = snap.get("state")
        if mode in (nd.MODE_MIRROR_PORTRAIT, nd.MODE_MIRROR_LANDSCAPE,
                    nd.MODE_FULLSCREEN) and hardware_state == nd.DP_LINK_READY:
            state = nd.MIRRORING
        elif mode == nd.MODE_DESKTOP and hardware_state == nd.DP_LINK_READY:
            state = nd.SEPARATE_DESKTOP
        else:
            state = hardware_state

        desktop_supported = bool(ctl.get("desktop_supported"))
        desktop_blocker = ctl.get("desktop_blocker")
        if hardware_state == nd.DP_LINK_READY and not desktop_supported:
            desktop_blocker = desktop_blocker or (
                "Separate desktop needs a second compositor output; "
                "only %s is currently exposed."
                % (", ".join((ctl.get("outputs") or {}).get("enabled_names") or [])
                   or "the phone output"))

        blockers = list(snap.get("blockers") or [])
        if desktop_blocker and desktop_blocker not in blockers:
            blockers.append(desktop_blocker)
        audio = snap.get("audio") or {}
        if audio.get("blocker"):
            blockers.append("HDMI audio: " + audio["blocker"])
        blocker = "; ".join(blockers) if blockers else None
        if not blocker and snap.get("state") != nd.DP_LINK_READY:
            blocker = "external display is not ready"

        # Only surface a monitor identity when the kernel reports a live DP
        # link.  monitor_info is also written by the driver's unit-test EDID
        # (BenQ SW320), so an unlinked value must never leak into the UI.
        display_name = snap.get("display_name") if snap.get("dp_link") else None
        external_modes = snap.get("external_modes") or []
        supported_modes = [m for m in external_modes if m.get("width") and m.get("height")]

        connector = None
        if snap.get("dp_link"):
            connector = {
                "type": "displayport",
                "name": "decon_t",
                "fb": "/dev/fb1",
                "status": "connected",
                "mode_source": "fbdev",
            }

        payload = dict(base)
        payload.update({
            "schema": nd.SCHEMA,
            "state": state,
            "hardware_state": hardware_state,
            "mode": mode,
            "rotation": ctl.get("rotation", 0),
            "mode_rotation": ctl.get("mode_rotation", ctl.get("rotation", 0)),
            "mode_fit": ctl.get("mode_fit", "fit"),
            "mode_choices": ctl.get("mode_choices") or snap.get("mode_choices") or [],
            "selected_resolution": ctl.get("selected_resolution") or snap.get("selected_resolution"),
            "dp_presets": ctl.get("dp_presets") or snap.get("dp_presets") or [],
            "generation": ctl.get("generation"),
            "notification_id": ctl.get("notification_id"),
            "last_error": ctl.get("last_error"),
            "display_name": display_name,
            "monitor_info_raw": snap.get("monitor_info_raw"),
            "partner": snap.get("partner"),
            "pd_identity": snap.get("pd_identity"),
            "pd_ids": snap.get("pd_ids"),
            "pd_type": snap.get("pd_type"),
            "dp_link": snap.get("dp_link"),
            "secdp": snap.get("secdp"),
            "secdp_msg": snap.get("secdp_msg"),
            "extcon": snap.get("extcon") or [],
            "extcon_dp": snap.get("extcon_dp"),
            "type_c_ports": snap.get("typec_ports") or [],
            "ccic": snap.get("ccic") or {},
            "dp_sec": snap.get("dp_sec") or {},
            "internal_fb": snap.get("internal_fb"),
            "external_fb_present": snap.get("external_fb_present"),
            "external_fb": snap.get("external_fb"),
            "external_modes": external_modes,
            "supported_modes": supported_modes,
            "connector": connector,
            "mirror_supported": bool(snap.get("mirror_supported")),
            "desktop_supported": desktop_supported,
            "desktop_blocker": desktop_blocker,
            "mirror_output": (ctl.get("outputs") or {}).get("primary") and
                             (ctl.get("outputs") or {}).get("primary", {}).get("name"),
            "desktop_output": (ctl.get("outputs") or {}).get("external") and
                              (ctl.get("outputs") or {}).get("external", {}).get("name"),
            "audio": audio,
            "blocker": blocker,
            "blockers": blockers,
            "safety": {
                "internal_display_preserved": True,
                "single_fb0_writer": True,
                "compositor_restarted": False,
            },
        })
        return payload

def _find_bluetooth_rfkill(root):
    base = os.path.join(root, "sys/class/rfkill")
    try:
        entries = sorted(os.listdir(base))
    except OSError:
        return None
    for e in entries:
        p = os.path.join(base, e)
        try:
            with open(os.path.join(p, "type")) as f:
                if f.read().strip().lower() != "bluetooth":
                    continue
        except OSError:
            continue
        return p
    return None


def bluetooth_set_power(enabled, root="/", timeout=15.0, persist=True):
    """Real Bluetooth power bring-up attempt (root-only, bounded).

    Unblock/block rfkill (which powers the BCM4375's BT rail) and start/stop
    bluetooth.service.  It returns what actually happened; the authoritative
    controller state is read back by the caller from the D-Bus bridge.

    The requested state is also written to the durable interface document when
    ``persist`` is true and this is the real root (``root='/'``).  Unit tests
    inject a fake root and must not touch the host's /var/lib/nuxel.
    """
    enabled = bool(enabled)
    steps = []
    errors = []

    rfkill = _find_bluetooth_rfkill(root)
    if rfkill:
        soft = os.path.join(rfkill, "soft")
        try:
            with open(soft, "w") as f:
                f.write("0" if enabled else "1")
            steps.append("rfkill soft-block=%s" % (not enabled))
        except OSError as exc:
            errors.append("rfkill write failed: %s" % exc)
    else:
        steps.append("no bluetooth rfkill node (radio not visible to kernel)")

    # The transport attach (patchram + btattach) and BlueZ are one power
    # domain.  Keeping nuxel-bluetooth.service running while the owner wants
    # Bluetooth OFF would re-power the radio after every reboot and on every
    # service restart, so both units are managed together:
    #   ON  -> rfkill unblock, attach HCI first, then start BlueZ
    #   OFF -> stop BlueZ first, detach HCI, then soft-block rfkill
    verb = "start" if enabled else "stop"
    units = (("nuxel-bluetooth.service", "bluetooth.service") if enabled
             else ("bluetooth.service", "nuxel-bluetooth.service"))
    for unit_name in units:
        try:
            proc = subprocess.run(
                ["/usr/bin/systemctl", verb, unit_name],
                capture_output=True, text=True, timeout=timeout,
                env={"PATH": "/usr/sbin:/usr/bin:/sbin:/bin", "LANG": "C"},
            )
            if proc.returncode != 0:
                errors.append("systemctl %s %s rc=%d: %s"
                              % (verb, unit_name, proc.returncode,
                                 (proc.stderr or proc.stdout or "").strip()[:200]))
            else:
                steps.append("%s %s" % (unit_name, "started" if enabled else "stopped"))
        except (OSError, subprocess.SubprocessError) as exc:
            errors.append("systemctl %s %s failed: %s" % (verb, unit_name, exc))
    if enabled and not any("nuxel-bluetooth.service" in e for e in errors):
        # BlueZ can start a fraction before btattach has published hci0.  Give
        # the adapter a bounded moment to appear so the caller's readback is
        # meaningful (this never invents an adapter; it still reports failure).
        import glob
        deadline = time.monotonic() + min(8.0, float(timeout or 15.0))
        while time.monotonic() < deadline and not glob.glob("/sys/class/bluetooth/hci*"):
            time.sleep(0.1)

    persisted = None
    if persist and root == "/":
        try:
            import interface_state
            interface_state.set_desired(
                "bluetooth", enabled,
                source="hw_providers.bluetooth_set_power")
            persisted = True
            steps.append("desired state persisted")
        except Exception as exc:  # noqa: BLE001 - never mask the hardware result
            persisted = False
            errors.append("persist desired state failed: %s" % exc)

    return {
        "success": not errors,
        "requested": enabled,
        "persisted": persisted,
        "steps": steps,
        "error": "; ".join(errors) if errors else None,
    }


class BluetoothManagerProvider:
    """Root-owned BlueZ manager for the Settings Bluetooth page.

    The privileged HTTP bridge runs as root and drives ``bluetoothctl`` in
    non-interactive, bounded subprocesses.  It only enumerates, scans, pairs,
    connects, disconnects, trusts and removes devices; it never invents a peer,
    never marks a failed pair/connect as successful, and returns the exact
    BlueZ text so the UI can show the real outcome.  Every subprocess is an argv
    list (no shell) with a hard timeout.
    """

    BTCTL = "/usr/bin/bluetoothctl"
    DEVICE_IFACE = "org.bluez.Device1"

    def __init__(self, timeout=12.0):
        self.timeout = timeout

    def _run(self, *args, timeout=None):
        env = {"PATH": "/usr/sbin:/usr/bin:/sbin:/bin", "LANG": "C",
               "TERM": "dumb"}
        try:
            proc = subprocess.run(
                [self.BTCTL, *args],
                capture_output=True, text=True,
                timeout=timeout or self.timeout, env=env,
            )
        except subprocess.TimeoutExpired as exc:
            # Discovery/scan is interrupted by design; preserve the partial
            # output (NEW/CHG lines) instead of discarding it.
            def _txt(chunk):
                if isinstance(chunk, bytes):
                    return chunk.decode("utf-8", "replace")
                return chunk or ""
            return {"success": False, "rc": None, "timed_out": True,
                    "stdout": _txt(exc.stdout), "stderr": _txt(exc.stderr)}
        except (OSError, subprocess.SubprocessError) as exc:
            return {"success": False, "error": str(exc), "rc": None,
                    "stdout": "", "stderr": ""}
        return {"success": proc.returncode == 0, "rc": proc.returncode,
                "stdout": proc.stdout or "", "stderr": proc.stderr or ""}

    @staticmethod
    def _strip_ansi(text):
        return re.sub(r"\x1b\[[0-9;?]*[a-zA-Z]", "", text)

    def _devices_from_stdout(self, out):
        """Parse ``bluetoothctl devices`` and ``info`` lines.

        Returns a list of device dicts keyed by MAC, merging alias/paired/trusted/
        connected where possible.  Only stable fields are parsed; missing data is
        left absent rather than guessed.
        """
        devices = {}
        current = None
        for line in out.splitlines():
            line = line.strip()
            if not line:
                continue
            m = re.match(r"Device\s+([0-9A-Fa-f:]{17})\s+(.*)$", line)
            if m:
                mac = m.group(1).upper()
                current = devices.setdefault(mac, {
                    "mac": mac, "alias": m.group(2).strip() or mac,
                })
                continue
            m = re.match(r"(\w+):\s*(.*)$", line)
            if m and current is not None:
                key = m.group(1).lower()
                val = m.group(2).strip()
                if key in ("paired", "bonded", "trusted", "blocked",
                           "connected", "legacypairing"):
                    current[key] = val == "yes"
                elif key in ("name", "alias"):
                    current["alias"] = val or current.get("alias")
                elif key == "icon":
                    current["icon"] = val
        return list(devices.values())

    def list_devices(self, paired_only=False):
        """Return devices BlueZ currently knows (cached from scans too)."""
        args = ("devices", "paired") if paired_only else ("devices",)
        r = self._run(*args)
        if not r["success"]:
            return {"success": False, "error": r["stderr"].strip() or r["stdout"].strip()}
        devices = self._devices_from_stdout(self._strip_ansi(r["stdout"]))
        return {"success": True, "devices": devices, "paired_only": paired_only}

    def scan(self, duration=8):
        """Run a bounded discovery and return the devices BlueZ saw.

        ``bluetoothctl scan on`` returns immediately unless it is given its own
        ``--timeout``; without it the NEW/CHG discovery lines are emitted after
        the command has already exited.  Keep the command alive for the bounded
        scan window so the discovery output is actually captured.
        """
        try:
            duration = int(duration)
        except (TypeError, ValueError):
            duration = 8
        duration = max(2, min(30, duration))
        env = {"PATH": "/usr/sbin:/usr/bin:/sbin:/bin", "LANG": "C", "TERM": "dumb"}
        try:
            proc = subprocess.run(
                [self.BTCTL, "--timeout", str(duration), "scan", "on"],
                capture_output=True, text=True, timeout=duration + 8, env=env,
            )
            r = {"success": proc.returncode == 0, "rc": proc.returncode,
                 "stdout": proc.stdout or "", "stderr": proc.stderr or ""}
        except subprocess.TimeoutExpired as exc:
            r = {"success": False, "rc": None, "timed_out": True,
                 "stdout": exc.stdout.decode("utf-8", "replace") if isinstance(exc.stdout, bytes) else (exc.stdout or ""),
                 "stderr": exc.stderr.decode("utf-8", "replace") if isinstance(exc.stderr, bytes) else (exc.stderr or "")}
        except (OSError, subprocess.SubprocessError) as exc:
            r = {"success": False, "error": str(exc), "rc": None,
                 "stdout": "", "stderr": ""}
        out = self._strip_ansi(r["stdout"] + "\n" + r["stderr"])
        # A scan always "fails" to return 0 when it is interrupted by the
        # command's own timeout; the discovery text is still the useful result.
        devices = self._devices_from_stdout(out)
        # Merge with the cache; a device may appear only as NEW during the scan.
        cached = self.list_devices()
        if cached.get("success"):
            by_mac = {d["mac"]: d for d in cached["devices"]}
            for d in devices:
                by_mac.setdefault(d["mac"], d)
            devices = list(by_mac.values())
        return {"success": True, "devices": devices, "scan_seconds": duration,
                "raw_rc": r.get("rc")}

    def _info(self, mac):
        mac = self._validate_mac(mac)
        if not mac:
            return {"success": False, "error": "invalid Bluetooth address"}
        r = self._run("info", mac)
        out = self._strip_ansi(r["stdout"])
        devs = self._devices_from_stdout(out)
        info = devs[0] if devs else {"mac": mac, "alias": mac}
        info["success"] = True
        return info

    @staticmethod
    def _validate_mac(mac):
        m = str(mac or "").strip().upper()
        return m if re.fullmatch(r"[0-9A-F]{2}(:[0-9A-F]{2}){5}", m) else None

    def pair(self, mac, timeout=30.0):
        mac = self._validate_mac(mac)
        if not mac:
            return {"success": False, "error": "invalid Bluetooth address"}
        r = self._run("pair", mac, timeout=timeout)
        info = self._info(mac)
        info["raw_rc"] = r.get("rc")
        info["raw"] = self._strip_ansi(r["stdout"]).strip()[-300:]
        info["success"] = "Pairing successful" in r["stdout"] or info.get("paired") is True
        if not info["success"]:
            info["error"] = (r["stderr"].strip() or r["stdout"].strip() or
                             "pairing did not confirm")[-300:]
        return info

    def connect(self, mac, timeout=30.0):
        mac = self._validate_mac(mac)
        if not mac:
            return {"success": False, "error": "invalid Bluetooth address"}
        r = self._run("connect", mac, timeout=timeout)
        info = self._info(mac)
        info["raw_rc"] = r.get("rc")
        info["raw"] = self._strip_ansi(r["stdout"]).strip()[-300:]
        info["success"] = "Connection successful" in r["stdout"] or info.get("connected") is True
        if not info["success"]:
            info["error"] = (r["stderr"].strip() or r["stdout"].strip() or
                             "connect did not confirm")[-300:]
        return info

    def disconnect(self, mac, timeout=20.0):
        mac = self._validate_mac(mac)
        if not mac:
            return {"success": False, "error": "invalid Bluetooth address"}
        r = self._run("disconnect", mac, timeout=timeout)
        info = self._info(mac)
        info["raw_rc"] = r.get("rc")
        info["raw"] = self._strip_ansi(r["stdout"]).strip()[-300:]
        info["success"] = "Successful disconnected" in r["stdout"] or info.get("connected") is False
        if not info["success"]:
            info["error"] = (r["stderr"].strip() or r["stdout"].strip() or
                             "disconnect did not confirm")[-300:]
        return info

    def trust(self, mac, trusted=True, timeout=20.0):
        mac = self._validate_mac(mac)
        if not mac:
            return {"success": False, "error": "invalid Bluetooth address"}
        args = ("trust", mac) if trusted else ("untrust", mac)
        r = self._run(*args, timeout=timeout)
        info = self._info(mac)
        info["raw_rc"] = r.get("rc")
        info["raw"] = self._strip_ansi(r["stdout"]).strip()[-300:]
        info["success"] = "Changing" in r["stdout"] and info.get("trusted") == trusted
        if not info["success"]:
            info["success"] = info.get("trusted") == trusted
        if not info["success"]:
            info["error"] = (r["stderr"].strip() or r["stdout"].strip() or
                             "trust change did not confirm")[-300:]
        return info

    def remove(self, mac, timeout=20.0):
        mac = self._validate_mac(mac)
        if not mac:
            return {"success": False, "error": "invalid Bluetooth address"}
        r = self._run("remove", mac, timeout=timeout)
        out = self._strip_ansi(r["stdout"])
        return {"success": "Device has been removed" in out or "not available" in out,
                "raw_rc": r.get("rc"), "raw": out.strip()[-300:],
                "error": (r["stderr"].strip() or r["stdout"].strip() or
                          "remove did not confirm")[-300:] if not ("Device has been removed" in out or "not available" in out) else None}


class GnssProvider:
    """Root-owned BCM4773 BBD/LHD lifecycle; no NMEA assumptions.

    The S10+ GNSS receiver is a BCM4773 behind the Broadcom BBD/LHD RPC
    stack.  The kernel exposes ``/dev/ttyBCM`` (BBD packet transport),
    ``/dev/bbd_patch`` (sensor-hub patch loader) and friends, plus the
    ``GPS_PWR_EN`` GPIO145 rail.  The vendor userspace consists of the
    Android/Bionic ``lhd`` and ``gpsd`` daemons; stock Linux gpsd cannot
    decode this protocol and no compatible patch firmware is present in the
    Nuxel image.

    This provider therefore implements the truthful, battery-safe subset:
    verified power-rail control, lease/refcount ownership with bounded
    deadlines, hardware/protocol inventory, and a bounded byte observation on
    the BBD transport.  It never parses NMEA, never invents a coordinate and
    never reports a fix.
    """

    POWER_RAIL = "/sys/devices/virtual/sec/gps/GPS_PWR_EN/value"
    BBD_PACKET_NODE = "/dev/ttyBCM"
    BBD_NODES = ("/dev/bbd_patch", "/dev/bbd_control",
                 "/dev/bbd_sensor", "/dev/bbd_urgent_patch")
    VENDOR_FILES = {
        "lhd": ("/vendor/bin/hw/lhd", "/vendor/bin/lhd"),
        "gpsd": ("/vendor/bin/hw/gpsd", "/vendor/bin/gpsd"),
        "android_linker": ("/system/bin/linker64",),
        "lhd_config": ("/vendor/etc/sensor/lhd.conf",),
        "gps_config": ("/vendor/etc/gnss/gps.xml",),
        "gnss_impl": ("/vendor/lib64/vendor.samsung.hardware.gnss@2.0.so",),
    }
    POLICY_PATH = os.environ.get("NUXEL_LOCATION_POLICY",
                                 "/var/lib/nuxel/permissions/location-policy.json")
    MAX_LEASE_SECONDS = 300.0

    def __init__(self, root="/"):
        """Optional ``root`` prefix for the sysfs/dev/firmware paths.

        Defaults to "/" (the real device). Unit tests inject a fake root so they
        can exercise power-on gating without touching the phone. The rail and
        BBD node constants below stay absolute; only firmware/vendor enumeration
        honors the prefix.
        """
        self.root = root

    _rail_lock = threading.Lock()
    _rail_owners = set()
    _rail_initial_state = None
    _lease_seq = 0

    # ------------------------------------------------------------------ power
    def _read_rail(self):
        try:
            with open(self.POWER_RAIL) as f:
                raw = f.read().strip()
            return int(raw) == 1, None
        except (OSError, ValueError) as exc:
            return None, str(exc)

    def power_rail(self, enabled=True, timeout=5.0):
        """Set the rail and require an exact readback.

        ``success`` is never true unless the state actually read back equals
        the requested state.  A write error, a missing readback or a mismatch
        is reported with the concrete reason.
        """
        enabled = bool(enabled)
        requested = "1" if enabled else "0"
        result = {
            "success": False,
            "requested": enabled,
            "enabled": None,
            "actual": None,
            "write_ok": False,
            "readback_ok": False,
            "readback": None,
            "error": None,
            "protocol": "broadcom-bbd-lhd-rpc",
        }
        deadline = time.monotonic() + max(0.1, float(timeout or 5.0))
        try:
            with open(self.POWER_RAIL, "w") as f:
                f.write(requested)
                f.flush()
                try:
                    os.fsync(f.fileno())
                except OSError:
                    pass
            result["write_ok"] = True
        except OSError as exc:
            result["error"] = "write %s: %s" % (self.POWER_RAIL, exc)
            return result
        # Read back immediately; sysfs GPIO writes are synchronous, but retry
        # briefly so we do not misreport a real state transition as a failure.
        while time.monotonic() <= deadline:
            state, err = self._read_rail()
            result["readback"] = state
            result["actual"] = state
            result["enabled"] = state
            if err is None and state == enabled:
                result["readback_ok"] = True
                result["success"] = True
                return result
            if err is not None:
                result["error"] = "readback %s: %s" % (self.POWER_RAIL, err)
            time.sleep(0.02)
        if result["error"] is None:
            result["error"] = ("readback mismatch: requested %s, actual %r"
                               % (requested, result["readback"]))
        return result

    # ----------------------------------------------------------------- leases
    def _policy_enabled(self):
        try:
            with open(self.POLICY_PATH) as f:
                return bool(json.load(f).get("enabled", False))
        except (OSError, ValueError, AttributeError):
            return False

    def acquire(self, seconds=30, timeout=60.0):
        """Acquire GNSS power under a lease only when a consumer exists.

        Returns a lease dict.  If the BBD/LHD/RPC userspace and firmware are
        absent, no rail power is applied: powering a receiver with no consumer
        only drains the battery and cannot produce a fix.
        """
        try:
            seconds = float(seconds)
        except (TypeError, ValueError):
            seconds = 30.0
        try:
            timeout = float(timeout)
        except (TypeError, ValueError):
            timeout = 60.0
        start = time.monotonic()
        deadline = start + max(1.0, min(seconds, timeout, self.MAX_LEASE_SECONDS))
        inventory = self.inventory()
        result = {
            "success": False,
            "acquired": False,
            "lease_id": None,
            "protocol": "broadcom-bbd-lhd-rpc",
            "deadline": deadline,
            "inventory": inventory,
            "fix": None,
            "stream": "not_opened",
            "error": None,
        }
        if not self._policy_enabled():
            result["error"] = "global location policy is OFF"
            result["error_code"] = "LOCATION_DISABLED"
            return result
        if not inventory["vendor_runtime_complete"]:
            result["error"] = inventory["blocker"]
            result["error_code"] = "UNSUPPORTED_PROTOCOL"
            return result
        with self._rail_lock:
            first_owner = not self._rail_owners
            if not self._rail_owners:
                self._rail_initial_state = self._read_rail()[0]
            self._lease_seq += 1
            lease_id = "gnss-%d" % self._lease_seq
            self._rail_owners.add(lease_id)
        if first_owner:
            powered = self.power_rail(True, timeout=max(1.0, deadline - time.monotonic()))
        else:
            powered = {"success": True, "enabled": True, "already_powered": True}
        result["power"] = powered
        if not powered.get("success"):
            self.release(lease_id)
            result["error"] = powered.get("error") or "GPS rail power-on failed"
            result["error_code"] = "POWER_FAILED"
            return result
        result.update(success=True, acquired=True, lease_id=lease_id)
        # Observe a bounded window.  The transport is BBD RPC, so bytes are
        # evidence of traffic only; they are never decoded as NMEA here.
        observed = self._observe_bbd(deadline)
        result.update(observed)
        result["fix"] = None
        result["error"] = ("valid BBD/LHD frames require the vendor lhd/gpsd "
                           "runtime; no fix is claimed") if observed.get("bytes") else None
        result["error_code"] = "NO_FIX" if observed.get("bytes") else "NO_DATA"
        return result

    def release(self, lease_id):
        """Release one lease; power off only when the last owner leaves."""
        with self._rail_lock:
            if lease_id not in self._rail_owners:
                return {"success": True, "released": False,
                        "reason": "lease not owned", "owners": len(self._rail_owners)}
            self._rail_owners.discard(lease_id)
            last = not self._rail_owners
            restore = self._rail_initial_state
            if last:
                self._rail_initial_state = None
        if not last:
            return {"success": True, "released": True, "powered": True,
                    "owners": self._active_owners()}
        if restore is True:
            return {"success": True, "released": True, "powered": True,
                    "restored_initial_state": True, "owners": 0}
        powered = self.power_rail(False)
        return {"success": bool(powered.get("success")), "released": True,
                "powered": False, "power": powered, "owners": 0,
                "error": powered.get("error")}

    @classmethod
    def _active_owners(cls):
        with cls._rail_lock:
            return len(cls._rail_owners)

    def _observe_bbd(self, deadline):
        out = {"bytes": 0, "stream": "no_data", "node": self.BBD_PACKET_NODE,
               "protocol": "broadcom-bbd-lhd-rpc", "nmea": False}
        if not os.path.exists(self.BBD_PACKET_NODE):
            out["stream"] = "node_absent"
            return out
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            out["stream"] = "deadline_expired"
            return out
        try:
            fd = os.open(self.BBD_PACKET_NODE, os.O_RDONLY | os.O_NONBLOCK)
        except OSError as exc:
            out.update(stream="open_failed", error=str(exc))
            return out
        data = b""
        try:
            while time.monotonic() < deadline and len(data) < 65536:
                r, _, _ = select.select([fd], [], [], 0.25)
                if not r:
                    continue
                try:
                    chunk = os.read(fd, 4096)
                except OSError:
                    break
                if not chunk:
                    break
                data += chunk
        finally:
            try:
                os.close(fd)
            except OSError:
                pass
        out["bytes"] = len(data)
        if data:
            out["stream"] = "bbd_bytes_observed"
            out["hex_prefix"] = data[:64].hex()
            # Deliberately no NMEA parsing: a $G match inside a BBD packet
            # would not make the stream NMEA or a fix.
            out["nmea"] = False
        return out

    # -------------------------------------------------------------- inventory
    def inventory(self):
        vendor = {}
        for name, candidates in self.VENDOR_FILES.items():
            vendor[name] = any(os.path.exists(p) for p in candidates)
        vendor_complete = all(vendor.values())
        nodes = [n for n in (self.BBD_PACKET_NODE,) + self.BBD_NODES if os.path.exists(n)]
        # Strict, loader-aware BBD patch inventory (single classifier). A random
        # gps.bin/gnss.bin/ssp* blob is NOT accepted as the BCM4773 patch.
        fw = __import__("gnss_inventory").firmware(root=self.root)
        firmware = [f["path"] for f in fw]
        spi_bound = []
        driver_dir = "/sys/bus/spi/drivers/brcm gps spi"
        try:
            spi_bound = [os.path.join(driver_dir, n)
                         for n in sorted(os.listdir(driver_dir)) if n.startswith("spi")]
        except OSError:
            pass
        rail_state, rail_err = self._read_rail()
        blocker = None
        if not nodes and not spi_bound:
            blocker = "no BCM4773 BBD node and no brcm gps spi binding"
        elif not firmware:
            blocker = "no compatible BCM4773 BBD sensor-hub patch firmware"
        elif not vendor_complete:
            missing = [k for k, v in vendor.items() if not v]
            blocker = "vendor BBD/LHD runtime missing: " + ", ".join(missing)
        else:
            blocker = ("BCM4773 BBD/LHD stack present but not initialized; "
                       "no fix has been verified")
        return {
            "protocol": "broadcom-bbd-lhd-rpc",
            "nmea": False,
            "nodes": nodes,
            "bbd_patch_node": "/dev/bbd_patch" if os.path.exists("/dev/bbd_patch") else None,
            "spi_bindings": spi_bound,
            "power_rail": self.POWER_RAIL,
            "power_rail_state": rail_state,
            "power_rail_readable": rail_err is None,
            "power_rail_error": rail_err,
            "active_leases": self._active_owners(),
            "firmware": firmware,
            "firmware_candidates": fw,
            "firmware_identity_verified": __import__("gnss_inventory").firmware_identity_verified(fw),
            "firmware_present": bool(firmware),
            "firmware_loaded": False,
            "vendor_files": vendor,
            "vendor_runtime_complete": vendor_complete,
            "android_linker": vendor["android_linker"],
            "vendor_userspace": vendor["lhd"] and vendor["gpsd"],
            "fix_supported": False,
            "blocker": blocker,
        }

    def probe(self, seconds=3, timeout=8.0, power=False):
        """Bounded, read-only-by-default diagnostic probe (never a fix)."""
        try:
            seconds = max(0.2, min(30.0, float(seconds)))
        except (TypeError, ValueError):
            seconds = 3.0
        try:
            timeout = max(0.2, float(timeout))
        except (TypeError, ValueError):
            timeout = 8.0
        started = time.monotonic()
        deadline = started + min(seconds, timeout)
        inv = self.inventory()
        out = {
            "success": True,
            "protocol": "broadcom-bbd-lhd-rpc",
            "node": self.BBD_PACKET_NODE,
            "nmea_stream": False,
            "inventory": inv,
            "power": None,
            "stream": "not_opened",
            "bytes": 0,
            "fix": None,
            "error": None,
            "error_code": None,
            "elapsed_s": 0.0,
        }
        if power:
            if self._active_owners() > 0:
                out.update(success=False,
                           error='GNSS rail is owned by an active lease',
                           error_code='BUSY')
                out['elapsed_s'] = round(time.monotonic() - started, 3)
                return out
            if not inv.get("vendor_runtime_complete"):
                out.update(success=False, error=inv["blocker"],
                           error_code="UNSUPPORTED_PROTOCOL")
            else:
                initial_rail = inv.get("power_rail_state")
                powered = self.power_rail(True, timeout=min(2.0, deadline - time.monotonic()))
                out["power"] = powered
                if not powered.get("success"):
                    out.update(success=False, error=powered.get("error"),
                               error_code="POWER_FAILED")
                else:
                    out.update(self._observe_bbd(deadline))
                    # Restore the exact pre-probe state, not a hard-coded OFF.
                    self.power_rail(True if initial_rail is True else False)
        else:
            out.update(self._observe_bbd(deadline))
        if out["bytes"]:
            out.update(success=False, stream="bbd_bytes_observed",
                       error="bytes observed on BBD transport; no BBD/LHD decoder available",
                       error_code="UNSUPPORTED_PROTOCOL")
        elif out.get("success"):
            out.update(error=inv["blocker"], error_code="NO_DATA")
        out["elapsed_s"] = round(time.monotonic() - started, 3)
        out["fix"] = None
        return out

    def sample_nmea(self, seconds=5, timeout=12.0):
        """Deprecated compatibility entry point; deliberately never claims NMEA."""
        return self.probe(seconds=seconds, timeout=timeout, power=False)
