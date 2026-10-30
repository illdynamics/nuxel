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
import os
import re
import select
import subprocess
import time

# Low-volume bring-up cap, shared with configs/nuxel/audio/audio.json
# (``safety.volume_cap_percent``).  A Settings/QS volume request is clamped to
# this ceiling until an owner raises it deliberately.
DEFAULT_VOLUME_CAP_PERCENT = 25

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
        """Make the static RDMA1 sink the PipeWire default node.

        After a cold boot WirePlumber can publish the sink without selecting a
        default.  ``pw-play`` then fails with "Translate ID error: '-1' is not
        a valid ID (returned by default-nodes-api)" while the sink is present.
        Selecting by stable node name is idempotent and works before any
        client has asked for a default.
        """
        proc, err = self._run_bounded(
            ["pactl", "set-default-sink", "alsa_output.hw_0_1"], timeout=4.0)
        if err or proc is None or proc.returncode != 0:
            return False
        return True

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
        self._ensure_default_sink()
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
            self._ensure_default_sink()
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

    def test_audio(self, asset="/usr/share/nuxel/assets/nuxel-pow.mp3", gain_percent=25):
        """Play the test asset through the currently selected output.

        Returns an HONEST result: 'played' means the player exited zero after
        sending the stream to the selected PipeWire sink; it does NOT assert
        that a human heard the sound."""
        if not self._sound_mode_ok():
            return {"success": False, "played": False,
                    "error": "sound mode is silent or vibrate",
                    "audible": "unverified"}
        if self._pipewire_available():
            ok, detail = self._pipewire_play(asset, gain_percent)
            return {"success": ok, "played": ok, "detail": detail,
                    "route": "pipewire:@DEFAULT_AUDIO_SINK@",
                    "asset": asset, "audible": "unverified"}
        return {"success": False, "played": False,
                "error": "PipeWire playback session unavailable",
                "audible": "unverified"}

class DisplayProvider:
    """Honest USB-C/display path inventory (no DRM, no invented monitor).

    The S10+ image renders through the framebuffer backend (wl-fb/phoc) and its
    kernel has ``CONFIG_DRM`` unset, so there are no DRM connectors and no
    Mirror/Desktop output can be driven by userspace.  This provider records
    that exact blocker plus the Type-C / extcon / framebuffer evidence.
    """

    def __init__(self, root="/"):
        self.root = root

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

    def get_status(self):
        drm_entries = self._list("/sys/class/drm")
        typec_ports = [p for p in self._list("/sys/class/typec") if p.startswith("port")]
        ports = []
        for p in typec_ports:
            base = "/sys/class/typec/" + p
            partner = self._read(base + "-partner/type")
            ports.append({
                "name": p,
                "data_role": self._read(base + "/data_role"),
                "power_role": self._read(base + "/power_role"),
                "partner": partner,
            })
        extcon = []
        for e in self._list("/sys/class/extcon"):
            base = "/sys/class/extcon/" + e
            name = self._read(base + "/name")
            state = self._read(base + "/state")
            extcon.append({"name": name, "state": state})

        drm_kernel = self._kernel_config("CONFIG_DRM")
        typec_kernel = self._kernel_config("CONFIG_TYPEC")
        dp_kernel = self._kernel_config("CONFIG_EXYNOS_DISPLAYPORT")

        drm_present = bool(drm_entries)
        mirror_supported = drm_present
        desktop_supported = drm_present  # an independent workspace needs a DRM output too

        blockers = []
        if not drm_present:
            blockers.append(
                "no /sys/class/drm: kernel CONFIG_DRM=%s (S10+ image renders via "
                "framebuffer, so no DRM connector/CRTC exists for USB-C DP Alt Mode)" % drm_kernel)
        elif not typec_ports:
            blockers.append("no /sys/class/typec port: USB-C role/Alt-Mode stack not exposed")
        else:
            partner_seen = any(p["partner"] for p in ports)
            if not partner_seen:
                blockers.append("no Type-C partner currently attached")

        return {
            "success": True,
            "state": "external_display_detected" if drm_present else "no_external_display_path",
            "drm_present": drm_present,
            "drm_entries": drm_entries,
            "drm_kernel": drm_kernel,
            "typec_kernel": typec_kernel,
            "displayport_kernel": dp_kernel,
            "type_c_ports": ports,
            "extcon": extcon,
            "mirror_supported": mirror_supported,
            "desktop_supported": desktop_supported,
            "supported_modes": [],
            "connector": None,
            "blocker": "; ".join(blockers) if blockers else None,
            "blockers": blockers,
        }


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


def bluetooth_set_power(enabled, root="/", timeout=15.0):
    """Real Bluetooth power bring-up attempt (root-only, bounded).

    Unblock/block rfkill (which powers the BCM4375's BT rail) and start/stop
    bluetooth.service.  It returns what actually happened; the authoritative
    controller state is read back by the caller from the D-Bus bridge.
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

    unit = "start" if enabled else "stop"
    try:
        proc = subprocess.run(
            ["/usr/bin/systemctl", unit, "bluetooth.service"],
            capture_output=True, text=True, timeout=timeout,
            env={"PATH": "/usr/sbin:/usr/bin:/sbin:/bin", "LANG": "C"},
        )
        if proc.returncode != 0:
            errors.append("systemctl %s bluetooth.service rc=%d: %s"
                          % (unit, proc.returncode,
                             (proc.stderr or proc.stdout or "").strip()[:200]))
        else:
            steps.append("bluetooth.service %s" % ("started" if enabled else "stopped"))
    except (OSError, subprocess.SubprocessError) as exc:
        errors.append("systemctl %s failed: %s" % (unit, exc))

    return {
        "success": not errors,
        "requested": enabled,
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
    """Root-owned GNSS bring-up: power rail + bounded NMEA sampling.

    The BCM4773 GNSS path on beyond2lte is present in the kernel
    (``/dev/ttyBCM`` + ``brcm gps spi`` bound to ``spi17.0`` + the ``GPS_PWR_EN``
    gpio rail), but the receiver does not emit NMEA until the vendor firmware
    and the Android bionic ``gpsd``/``lhd`` userspace are available.  This
    provider powers the rail safely for a bounded acquisition window and reads
    back whatever the serial node produces; it never invents a coordinate or
    a fix.
    """

    POWER_RAIL = "/sys/devices/virtual/sec/gps/GPS_PWR_EN/value"
    NMEA_NODE = "/dev/ttyBCM"

    def power_rail(self, enabled=True, timeout=5.0):
        enabled = bool(enabled)
        try:
            with open(self.POWER_RAIL, "w") as f:
                f.write("1" if enabled else "0")
        except OSError as exc:
            return {"success": False, "enabled": None, "error": str(exc)}
        try:
            with open(self.POWER_RAIL) as f:
                state = int(f.read().strip()) == 1
        except (OSError, ValueError):
            state = None
        return {"success": True, "requested": enabled, "enabled": state}

    def sample_nmea(self, seconds=5, timeout=12.0):
        """Power the rail, read /dev/ttyBCM bounded, then power it back off.

        Returns the raw text and a count of NMEA sentences observed; an empty
        stream is reported as ``stream=empty`` rather than as a fix.
        """
        try:
            seconds = int(seconds)
        except (TypeError, ValueError):
            seconds = 5
        seconds = max(1, min(30, seconds))
        self.power_rail(True)
        data = b""
        try:
            fd = os.open(self.NMEA_NODE, os.O_RDONLY | os.O_NONBLOCK)
        except OSError as exc:
            self.power_rail(False)
            return {"success": False, "error": "open %s: %s" % (self.NMEA_NODE, exc)}
        try:
            t0 = time.time()
            while time.time() - t0 < seconds:
                r, _, _ = select.select([fd], [], [], 0.25)
                if r:
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
            self.power_rail(False)
        text = data.decode("utf-8", "replace")
        sentences = re.findall(r"\$G[A-Z]{2,4}", text)
        return {
            "success": True,
            "node": self.NMEA_NODE,
            "sample_seconds": seconds,
            "bytes": len(data),
            "nmea_sentence_count": len(sentences),
            "sentences": list(dict.fromkeys(sentences))[:16],
            "stream": "nmea" if sentences else "empty",
            "raw": text[:500],
        }
