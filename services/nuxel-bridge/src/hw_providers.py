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
    """Real ALSA audio inventory + low-volume volume/mute controls.

    The phone's audio backend is ALSA directly (the image ships no
    PipeWire/WirePlumber systemd units), so this provider reports the actual
    cards/PCMs from ``/proc/asound`` and operates ``amixer`` with bounded,
    shell-free subprocesses.  It probes a small set of MADERA playback-volume
    candidate names directly instead of enumerating the entire (very large)
    control namespace, so a status call cannot stall the single-threaded HTTP
    bridge for tens of seconds.
    """

    def __init__(self, root="/", card=0, amixer="/usr/sbin/amixer",
                 timeout=4.0, volume_cap=DEFAULT_VOLUME_CAP_PERCENT):
        self.root = root
        self.card = card
        self.amixer = amixer
        self.timeout = float(timeout)
        self.volume_cap = int(volume_cap)
        self._control_cache = None
        self._control_cache_valid = False
        # MADERA's name-based sget can sleep in D-state; the numid form is fast.
        self._control_numid = None
        self._control_min = None
        self._control_max = None
        self._control_channels = None

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

    def _service_state(self):
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

    # ---- amixer ----------------------------------------------------------
    def _run_amixer(self, *args):
        """Run amixer without ever blocking on a D-state child.

        The MADERA codec has controls whose unmute/read path can sleep in an
        uninterruptible kernel state (I2C to the ABox), where SIGKILL has no
        effect.  A normal ``subprocess.run(timeout=...)`` still blocks in its
        internal re-``communicate`` when that happens, which would wedge this
        single-threaded HTTP bridge.  This runner instead reads the pipes
        non-blocking with ``select`` and, on deadline, kills the process group
        and ABANDONS the child (it becomes an orphan and exits when the kernel
        I/O completes) without ever calling ``waitpid`` on it.
        """
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
        """Return the first observed volume-control name, without a full walk.

        ``amixer scontrols`` is ONE bounded call (~2 s on the S10+ for 813
        controls) and is authoritative: the MADERA card exposes
        ``HPOUT1 Digital Volume``, not ``HPOUT1 Digital``.  Probing candidates
        with ``sget`` first was both wrong and slow (up to N * 4 s when a
        candidate sits behind a sleeping codec).  A fake/absent amixer falls
        back to the old sget probe so offline tests remain deterministic.
        """
        if self._control_cache_valid:
            return self._control_cache
        # `amixer controls` is ONE bounded call and carries the numid.  Prefer
        # the numid form for every read/write: on this MADERA codec the
        # name-based sget can sleep in kernel D-state for ~50 s, while
        # `cget numid=N` answers immediately.
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
        # Fallback for an amixer that cannot list controls (offline fixtures).
        for candidate in VOLUME_CONTROL_CANDIDATES:
            out, err = self._run_amixer("sget", candidate)
            if err:
                continue
            if out and "unable to find" not in out.lower():
                self._control_cache = candidate
                self._control_cache_valid = True
                return candidate
        # Mark the (empty) result as valid so repeated status calls do not
        # re-probe the same absent controls forever.
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

    # ---- public API ------------------------------------------------------
    def capture_route(self):
        """Report whether the session audio server exposes a capture source.

        This is deliberately a *read-only* probe: opening an ALSA capture PCM
        on this vendor kernel can block in abox_wait_restored (D state), so the
        Recorder must not call getUserMedia until a routed source exists.  The
        check runs wpctl with a bounded timeout and only parses the Sources
        section; it never opens /dev/snd.
        """
        import shutil
        wpctl = shutil.which("wpctl") or "/usr/bin/wpctl"
        env = dict(os.environ)
        env.setdefault("XDG_RUNTIME_DIR", "/run/nuxel-wayland")
        env.setdefault("PULSE_SERVER", "unix:/run/nuxel-wayland/pulse/native")
        try:
            proc = subprocess.run([wpctl, "status"], env=env,
                                  capture_output=True, text=True,
                                  timeout=self.timeout)
        except (OSError, subprocess.TimeoutExpired) as exc:
            return {"success": False, "available": False,
                    "error": "audio session query failed: %s" % exc,
                    "sources": []}
        sources = []
        in_sources = False
        for line in (proc.stdout or "").splitlines():
            if re.search(r"\bSources\s*:", line):
                in_sources = True
                continue
            if in_sources and re.search(r"\b(Filters|Streams|Settings)\s*:", line):
                break
            if not in_sources:
                continue
            if not line.strip():
                continue
            if re.search(r"\b\d+\.\s+", line):
                sources.append(re.sub(r"^[^0-9]*", "", line).strip())
        return {"success": True, "available": bool(sources),
                "sources": sources,
                "reason": None if sources else "no capture source routed by the session audio server"}

    def get_status(self):
        cards = self._cards()
        pcms = self._pcms()
        svc = self._service_state()

        volume_control = self._probe_candidates()
        volume = None
        mixer_error = None
        if volume_control:
            volume, verr = self._parse_amixer_value(volume_control)
            if verr:
                mixer_error = verr

        present = bool(cards)
        playback = pcms["playback"]
        capture = pcms["capture"]
        volume_supported = bool(volume_control and volume and volume["percent"] is not None)
        # The MADERA "HPOUT1 Digital" control accepts `mute` but its `unmute`
        # path sleeps in the kernel (D-state) on this 4.14 port.  A one-way
        # mute would leave the owner unable to unmute, so mute/unmute is
        # honestly reported unsupported rather than half-offered.
        mute_supported = False
        mute_blocker = (
            "MADERA HPOUT1 Digital unmute hangs the kernel I2C control "
            "(measured 2026-10-27); mute is not offered to avoid wedging the codec"
        ) if volume_control else None

        detail = []
        if not present:
            detail.append("no ALSA cards in /proc/asound/cards")
        elif not playback:
            detail.append("no playback PCM in /proc/asound/pcm")
        if mixer_error:
            detail.append("mixer read failed: %s" % mixer_error)
        elif not volume_control:
            detail.append("no safe playback volume control discovered on card %d" % self.card)

        return {
            "success": True,
            "state": "present" if present else "unavailable",
            "backend": svc["backend"],
            "sound_server": svc["sound_server"],
            "sound_server_units_present": svc["units_present"],
            "sound_server_units_active": svc["units_active"],
            "cards": cards,
            "playback_devices": playback,
            "capture_devices": capture,
            "volume_control": volume_control,
            "volume_percent": volume["percent"] if volume else None,
            "muted": volume["muted"] if volume else None,
            "volume_supported": volume_supported,
            "mute_supported": mute_supported,
            "mute_blocker": mute_blocker,
            "unmute_supported": False,
            "volume_cap_percent": self.volume_cap,
            "detail": "; ".join(detail) if detail else None,
            "mixer_error": mixer_error,
            "timestamp": None,
        }

    def set_volume(self, percent):
        try:
            percent = int(percent)
        except (TypeError, ValueError):
            return {"success": False, "error": "invalid volume value"}
        percent = max(0, min(self.volume_cap, percent))

        control = self._probe_candidates()
        if not control:
            return {"success": False,
                    "error": "no safe playback volume control discovered"}
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
        # Unmute is blocked: it wedges the codec I2C control on this kernel
        # (D-state amixer, measured).  Never attempt it from the UI.
        if not muted:
            return {"success": False,
                    "error": "unmute is unsupported on this codec path "
                             "(MADERA HPOUT1 Digital unmute hangs the kernel control)",
                    "error_code": "UNMUTE_UNSUPPORTED"}
        control = self._probe_candidates()
        if not control:
            return {"success": False,
                    "error": "no safe playback volume control discovered"}
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
