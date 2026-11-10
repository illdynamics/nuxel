#!/usr/bin/env python3
"""Nuxel audio-output discovery and routing policy (PWNAGE-102000).

This module is deliberately split from ``nuxel-soundd`` so the policy is
testable without a sound server.  It owns one question:

    Given the real PipeWire sinks and the real Samsung DisplayPort audio
    capability, which physical output should new and existing playback use?

The S10+ does not expose HDMI audio through DRM.  A real endpoint is the
Samsung DP DMA PCM (``DP Audio`` in ``/proc/asound/pcm``), and the vendor
display driver publishes an EDID-derived audio-info word through
``/sys/class/switch/ch_hdmi_audio/state``.  That word is *not* a boolean:
the live value is ``0x043b0102``.  Treating it as ``== 1`` was the original
false-negative that hid a working endpoint.
"""
from __future__ import annotations

import json
import os
import re
import socket
import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Optional, Tuple

SCHEMA = "nuxel.audio-outputs/1"
ROUTING_AUTOMATIC = "automatic"
ROUTING_MANUAL = "manual"
ROUTING_MODES = (ROUTING_AUTOMATIC, ROUTING_MANUAL)

AUDIO_ABSENT = "ABSENT"
AUDIO_DISCOVERING = "DISCOVERING"
AUDIO_PRESENT_UNVERIFIED = "PRESENT_UNVERIFIED"
AUDIO_AVAILABLE = "AVAILABLE"
AUDIO_ACTIVE = "ACTIVE"
AUDIO_UNAVAILABLE = "UNAVAILABLE"
AUDIO_RECONNECTING = "RECONNECTING"

KIND_SPEAKER = "speaker"
KIND_HDMI = "hdmi"
KIND_BLUETOOTH = "bluetooth"
KIND_USB = "usb"
KIND_OTHER = "other"

SPEAKER_SINK = "alsa_output.hw_0_1"
HDMI_SINK = "alsa_output.nuxel_hdmi"
SPEAKER_ID = "alsa:beyond-madera:rdma1"
HDMI_ID = "alsa:beyond-madera:dp-audio"
DEFAULT_POLICY_PATH = "/var/lib/nuxel/audio/output-policy.json"
DEFAULT_STATE_PATH = "/run/nuxel/audio-outputs.json"
DEFAULT_RUNTIME = "/run/nuxel-wayland"

_VALID_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9:._+@/-]{0,255}$")
_DP_PCM = re.compile(r"^\s*(\d+)-(\d+):\s+DP Audio\b(.*)$", re.I)
_DP_EXTCON = re.compile(r"(?:^|\s)DP=(?:1|true|on)(?:\s|$)", re.I)


def _int_or_none(value: Any) -> Optional[int]:
    try:
        if isinstance(value, str):
            return int(value.strip(), 0)
        return int(value)
    except (TypeError, ValueError):
        return None


def parse_dp_audio_info(value: Any, dp_link: bool,
                        pcm_present: bool) -> Dict[str, Any]:
    """Decode ``edid_audio_informs()`` from the vendor display driver.

    Layout (drivers/video/fbdev/exynos/dpu20/displayport_edid.c):
        bits  0..7   channel mask (1 << (channels - 1))
        bits  8..15  speaker allocation
        bits 16..18  bit-rate flags
        bits 19..21  sample-rate flags
        bit  26      1 = DisplayPort, 0 = HDMI

    The live value ``0x043b0102`` therefore means two channels, 48 kHz LPCM,
    on the DP path.  A disconnected/unsupported sink yields -1 (usually shown
    as ``0xffffffff``) or a zero sample/channel mask.
    """
    raw = _int_or_none(value)
    out: Dict[str, Any] = {
        "raw": raw,
        "value_hex": (None if raw is None else "0x%08x" % (raw & 0xffffffff)),
        "dp_link": bool(dp_link),
        "pcm_present": bool(pcm_present),
        "channel_mask": 0,
        "channels": 0,
        "speaker_allocation": 0,
        "bit_rate_flags": 0,
        "sample_rate_flags": 0,
        "is_dp": None,
        "valid": False,
        "available": False,
        "reason": None,
    }
    if raw is None:
        out["reason"] = "ch_hdmi_audio state is unavailable"
        return out
    if raw < 0 or raw == 0xffffffff:
        out["reason"] = "display sink reported no EDID audio information"
        return out
    mask = raw & 0xff
    out.update({
        "channel_mask": mask,
        "channels": mask.bit_length(),
        "speaker_allocation": (raw >> 8) & 0xff,
        "bit_rate_flags": (raw >> 16) & 0x7,
        "sample_rate_flags": (raw >> 19) & 0x7,
        "is_dp": bool(raw & (1 << 26)),
    })
    if mask == 0:
        out["reason"] = "EDID audio block advertises zero LPCM channels"
        return out
    if out["sample_rate_flags"] == 0:
        out["reason"] = "EDID audio block advertises no LPCM sample rate"
        return out
    out["valid"] = True
    if not dp_link:
        out["reason"] = "DisplayPort link is not ready"
    elif not pcm_present:
        out["reason"] = "kernel exposes no Samsung DP Audio PCM"
    else:
        out["available"] = True
        out["reason"] = None
    return out


def parse_dp_pcm(pcm_text: Optional[str]) -> Optional[Dict[str, Any]]:
    """Return the live Samsung DP DMA PCM, if the kernel registered it."""
    for line in (pcm_text or "").splitlines():
        m = _DP_PCM.match(line)
        if not m:
            continue
        return {
            "card": int(m.group(1)),
            "device": int(m.group(2)),
            "hw_path": "hw:%d,%d" % (int(m.group(1)), int(m.group(2))),
            "line": line.strip(),
        }
    return None


def dp_link_ready(secdp: Optional[str], extcon: Optional[str]) -> bool:
    try:
        sec = int(str(secdp or "").strip(), 0) == 1
    except (TypeError, ValueError):
        sec = str(secdp or "").strip().lower() in ("1", "true", "on")
    return bool(sec and _DP_EXTCON.search(str(extcon or "")))


def _valid_id(value: Any) -> Optional[str]:
    text = str(value or "").strip()
    return text if _VALID_ID.match(text) else None


def _volume_percent(sink: Dict[str, Any]) -> Optional[int]:
    volume = sink.get("volume")
    values: List[float] = []
    if isinstance(volume, dict):
        for item in volume.values():
            if isinstance(item, dict):
                try:
                    values.append(float(item.get("value")))
                except (TypeError, ValueError):
                    continue
    if not values:
        return None
    return max(0, min(100, int(round((sum(values) / len(values)) * 100.0 / 65536.0))))


def _sink_name(sink: Dict[str, Any]) -> str:
    return str(sink.get("name") or (sink.get("properties") or {}).get("node.name") or "").strip()


def classify_sink(sink: Dict[str, Any]) -> str:
    name = _sink_name(sink).lower()
    props = sink.get("properties") if isinstance(sink.get("properties"), dict) else {}
    if _sink_name(sink) == SPEAKER_SINK or name.endswith("nuxel_speaker"):
        return KIND_SPEAKER
    if _sink_name(sink) == HDMI_SINK or name.endswith("nuxel_hdmi"):
        return KIND_HDMI
    if name.startswith("bluez_output.") or props.get("device.api") == "bluez":
        return KIND_BLUETOOTH
    if name.startswith("alsa_output.usb-") or props.get("device.bus") == "usb":
        return KIND_USB
    return KIND_OTHER


def is_real_output(sink: Dict[str, Any]) -> bool:
    name = _sink_name(sink)
    if not name:
        return False
    props = sink.get("properties") if isinstance(sink.get("properties"), dict) else {}
    low = name.lower()
    if props.get("node.virtual") in (True, "true", 1, "1"):
        return False
    if props.get("media.class") not in (None, "", "Audio/Sink"):
        return False
    if any(token in low for token in ("monitor", "null", "dummy", "freewheel")):
        return False
    if low in ("auto_null", "dummy_output"):
        return False
    return True


def stable_id_for(sink: Dict[str, Any]) -> str:
    kind = classify_sink(sink)
    if kind == KIND_SPEAKER:
        return SPEAKER_ID
    if kind == KIND_HDMI:
        return HDMI_ID
    return "pipewire:" + _sink_name(sink)


def endpoint_from_sink(sink: Dict[str, Any], default_name: Optional[str],
                       hdmi_status: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
    if not is_real_output(sink):
        return None
    name = _sink_name(sink)
    kind = classify_sink(sink)
    props = sink.get("properties") if isinstance(sink.get("properties"), dict) else {}
    state = str(sink.get("state") or props.get("node.state") or "unknown").lower()
    if state in ("error", "removed", "unlinked"):
        return None
    stable = stable_id_for(sink)
    description = str(sink.get("description") or props.get("node.description") or name)
    if kind == KIND_SPEAKER:
        description = "Phone speaker"
    elif kind == KIND_HDMI:
        # Keep the stable role name.  The vendor's monitor_info is advisory
        # (and its built-in unit-test EDID has produced stale identities), so
        # it is exposed separately in diagnostics rather than used as the
        # routing identity or a possibly-wrong UI label.
        description = "HDMI / USB-C display"
    elif kind == KIND_BLUETOOTH:
        description = description or "Bluetooth audio"
    elif kind == KIND_USB:
        description = description or "USB audio"
    available = True
    reason = None
    if kind == KIND_HDMI and not bool((hdmi_status or {}).get("available")):
        available = False
        reason = (hdmi_status or {}).get("blocker") or "HDMI audio endpoint unavailable"
    return {
        "id": stable,
        "stable_id": stable,
        "node_name": name,
        "description": description,
        "kind": kind,
        "state": state,
        "available": available,
        "reason": reason,
        "default": bool(default_name and name == default_name),
        "volume_percent": _volume_percent(sink),
        "muted": bool(sink.get("mute", False)),
        "hardware_path": props.get("api.alsa.path"),
        "object_id": sink.get("index", props.get("object.id")),
        "properties_source": "pipewire",
        "display_name": (hdmi_status or {}).get("display_name") if kind == KIND_HDMI else None,
    }


def choose_output(endpoints: Iterable[Dict[str, Any]], mode: str,
                  preferred_id: Optional[str], fallback_id: Optional[str],
                  current_id: Optional[str] = None) -> Dict[str, Any]:
    """Choose a route without side effects.

    Priority:
      * Automatic: verified HDMI, then last valid non-HDMI, then current
        non-HDMI, then speaker, then the normal Nuxel default (BT/USB/other).
      * Manual: the explicit stable id while available; otherwise the same
        safe fallback order, while the preference stays pending.
    """
    by_id = {e.get("stable_id") or e.get("id"): e for e in endpoints
             if e.get("stable_id") or e.get("id")}
    available = {k: v for k, v in by_id.items() if v.get("available")}

    def pick(ids: Iterable[Optional[str]]) -> Optional[Dict[str, Any]]:
        for item in ids:
            if item and item in available:
                return available[item]
        return None

    speaker = next((e for e in available.values() if e.get("kind") == KIND_SPEAKER), None)
    hdmi = next((e for e in available.values() if e.get("kind") == KIND_HDMI), None)

    if mode == ROUTING_MANUAL:
        preferred = pick([preferred_id])
        if preferred is not None:
            return {"target": preferred, "reason_code": "manual-selected",
                    "reason": "manual: retaining user-selected %s" % preferred.get("description"),
                    "fallback": False}
        target = pick([fallback_id, current_id])
        if target is None:
            target = speaker
        if target is None:
            for kind in (KIND_BLUETOOTH, KIND_USB, KIND_OTHER):
                target = next((e for e in available.values() if e.get("kind") == kind), None)
                if target is not None:
                    break
        if target is not None:
            reason = ("manual: preferred output unavailable; safe fallback to %s"
                      % target.get("description"))
            return {"target": target, "reason_code": "manual-fallback",
                    "reason": reason, "fallback": True}
        return {"target": None, "reason_code": "manual-no-output",
                "reason": "manual: preferred output unavailable and no fallback exists",
                "fallback": True}

    if hdmi is not None:
        return {"target": hdmi, "reason_code": "automatic-hdmi",
                "reason": "automatic: verified HDMI audio endpoint became available; selected %s"
                          % hdmi.get("description"),
                "fallback": False}
    target = pick([fallback_id, current_id])
    if target is None:
        target = speaker
    if target is None:
        for kind in (KIND_BLUETOOTH, KIND_USB, KIND_OTHER):
            target = next((e for e in available.values() if e.get("kind") == kind), None)
            if target is not None:
                break
    if target is not None:
        return {"target": target, "reason_code": "automatic-fallback",
                "reason": "automatic: no HDMI audio; selected %s" % target.get("description"),
                "fallback": True}
    return {"target": None, "reason_code": "automatic-no-output",
            "reason": "automatic: no usable physical output is available",
            "fallback": True}


class Preferences:
    """Persist only stable identities and routing mode."""

    def __init__(self, path: str = DEFAULT_POLICY_PATH):
        self.path = Path(path)
        self.mode = ROUTING_AUTOMATIC
        self.preferred_id: Optional[str] = None
        self.preferred_name: Optional[str] = None
        self.fallback_id: Optional[str] = None
        self.load_error: Optional[str] = None
        self.load()

    def load(self) -> None:
        try:
            doc = json.loads(self.path.read_text(encoding="utf-8"))
        except OSError:
            return
        except (ValueError, TypeError) as exc:
            self.load_error = str(exc)
            return
        if not isinstance(doc, dict):
            self.load_error = "policy document is not an object"
            return
        mode = str(doc.get("mode") or "").strip().lower()
        if mode in ROUTING_MODES:
            self.mode = mode
        self.preferred_id = _valid_id(doc.get("preferred_id"))
        self.fallback_id = _valid_id(doc.get("fallback_id"))
        name = str(doc.get("preferred_name") or "").strip()
        self.preferred_name = name[:160] or None
        if self.mode == ROUTING_MANUAL and not self.preferred_id:
            # A malformed manual document must never leave the system without
            # a policy.  Missing identity means Automatic.
            self.mode = ROUTING_AUTOMATIC

    def as_dict(self) -> Dict[str, Any]:
        return {
            "schema": 1,
            "mode": self.mode,
            "preferred_id": self.preferred_id,
            "preferred_name": self.preferred_name,
            "fallback_id": self.fallback_id,
            "updated": int(time.time()),
        }

    def save(self) -> bool:
        doc = self.as_dict()
        tmp = self.path.with_name(self.path.name + ".tmp.%d" % os.getpid())
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            tmp.write_text(json.dumps(doc, indent=2, sort_keys=True) + "\n",
                           encoding="utf-8")
            os.chmod(tmp, 0o600)
            os.replace(tmp, self.path)
            return True
        except OSError:
            return False


class PactlBackend:
    """Small, bounded adapter over PipeWire's PulseAudio-compatible API."""

    def __init__(self, root: str = "/", runtime: str = DEFAULT_RUNTIME,
                 pactl: str = "/usr/bin/pactl", timeout: float = 6.0):
        self.root = root
        self.runtime = runtime
        self.pactl = pactl
        self.timeout = float(timeout)
        self.last_error: Optional[str] = None

    def _abs(self, rel: str) -> str:
        return os.path.join(self.root, rel.lstrip("/")) if rel.startswith("/") else rel

    def _env(self) -> Dict[str, str]:
        env = dict(os.environ)
        env.update({
            "XDG_RUNTIME_DIR": self.runtime,
            "PIPEWIRE_RUNTIME_DIR": self.runtime,
            "PULSE_SERVER": "unix:%s/pulse/native" % self.runtime,
            "PATH": "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",
            "LANG": "C",
        })
        return env

    def _run(self, args: List[str], timeout: Optional[float] = None) -> Optional[subprocess.CompletedProcess]:
        try:
            return subprocess.run(
                [self.pactl] + list(args), capture_output=True, text=True,
                timeout=float(timeout or self.timeout), env=self._env(),
                stdin=subprocess.DEVNULL,
            )
        except (OSError, subprocess.SubprocessError) as exc:
            self.last_error = str(exc)
            return None

    def available(self) -> bool:
        if self.root != "/":
            return True
        return Path(self.runtime, "pipewire-0").is_socket()

    def list_sinks(self) -> List[Dict[str, Any]]:
        proc = self._run(["-f", "json", "list", "sinks"])
        if proc is not None and proc.returncode == 0:
            try:
                doc = json.loads(proc.stdout or "[]")
                if isinstance(doc, list):
                    self.last_error = None
                    return [s for s in doc if isinstance(s, dict)]
            except ValueError as exc:
                self.last_error = "pactl JSON: %s" % exc
        # Older servers may not implement -f json.  Keep discovery honest
        # with the short form rather than inventing a description or volume.
        proc = self._run(["list", "short", "sinks"])
        if proc is None or proc.returncode != 0:
            self.last_error = (proc.stderr if proc is not None else None) or self.last_error or "pactl list sinks failed"
            return []
        out = []
        for line in (proc.stdout or "").splitlines():
            cols = line.split("\t")
            if len(cols) < 2:
                continue
            out.append({
                "index": cols[0], "name": cols[1], "driver": cols[2] if len(cols) > 2 else None,
                "state": cols[4] if len(cols) > 4 else "unknown",
                "description": cols[1], "mute": False,
                "volume": {}, "properties": {},
            })
        self.last_error = None
        return out

    def default_sink(self) -> Optional[str]:
        proc = self._run(["get-default-sink"])
        if proc is None or proc.returncode != 0:
            return None
        value = (proc.stdout or "").strip()
        return value if value and value.lower() != "null" else None

    def set_default(self, name: str) -> bool:
        proc = self._run(["set-default-sink", name])
        return bool(proc is not None and proc.returncode == 0)

    def set_volume(self, name: str, percent: int) -> bool:
        percent = max(0, min(100, int(percent)))
        proc = self._run(["set-sink-volume", name, "%d%%" % percent])
        return bool(proc is not None and proc.returncode == 0)

    def set_muted(self, name: str, muted: bool) -> bool:
        proc = self._run(["set-sink-mute", name, "1" if muted else "0"])
        return bool(proc is not None and proc.returncode == 0)

    def list_sink_inputs(self) -> List[str]:
        proc = self._run(["list", "short", "sink-inputs"])
        if proc is None or proc.returncode != 0:
            return []
        return [line.split("\t", 1)[0] for line in (proc.stdout or "").splitlines()
                if "\t" in line]

    def move_sink_input(self, index: str, target: str) -> bool:
        proc = self._run(["move-sink-input", str(index), target])
        return bool(proc is not None and proc.returncode == 0)

    def load_hdmi(self, hw_path: str, sink_name: str = HDMI_SINK) -> Tuple[bool, Optional[int], Optional[str]]:
        proc = self._run([
            "load-module", "module-alsa-sink",
            "sink_name=%s" % sink_name,
            "device=%s" % hw_path,
            "rate=48000", "channels=2", "format=s16le",
        ], timeout=10.0)
        if proc is None:
            return False, None, self.last_error or "pactl load-module failed"
        if proc.returncode != 0:
            detail = ((proc.stderr or "") + (proc.stdout or "")).strip()
            return False, None, detail[-300:] or "pactl load-module failed"
        try:
            return True, int((proc.stdout or "").strip().splitlines()[-1]), None
        except (TypeError, ValueError):
            return False, None, "module index was not reported"

    def unload_hdmi(self, sink_name: str = HDMI_SINK) -> Tuple[bool, Optional[str]]:
        proc = self._run(["list", "short", "modules"])
        if proc is None or proc.returncode != 0:
            return False, self.last_error or "pactl list modules failed"
        module_ids: List[str] = []
        for line in (proc.stdout or "").splitlines():
            cols = line.split("\t")
            if len(cols) < 2:
                continue
            args = cols[2] if len(cols) > 2 else ""
            if cols[1] == "module-alsa-sink" and sink_name in args:
                module_ids.append(cols[0])
        errors: List[str] = []
        for mid in module_ids:
            p = self._run(["unload-module", mid])
            if p is None or p.returncode != 0:
                errors.append("unload-module %s failed" % mid)
        return not errors, "; ".join(errors) or None

    def sink_available(self, name: str) -> bool:
        return any(_sink_name(s) == name for s in self.list_sinks())


class AudioOutputManager:
    """Single owner of output discovery, routing mode and route application."""

    def __init__(self, root: str = "/", policy_path: str = DEFAULT_POLICY_PATH,
                 state_path: str = DEFAULT_STATE_PATH,
                 runtime: str = DEFAULT_RUNTIME,
                 backend: Optional[PactlBackend] = None,
                 on_route: Optional[Callable[[Optional[Dict[str, Any]]], None]] = None,
                 hdmi_reader: Optional[Callable[[], Dict[str, Any]]] = None,
                 reconcile_interval: float = 2.0):
        self.root = root
        self.runtime = runtime
        self.backend = backend or PactlBackend(root=root, runtime=runtime)
        self.prefs = Preferences(policy_path)
        self.state_path = Path(state_path)
        self.on_route = on_route
        self.hdmi_reader = hdmi_reader
        self.reconcile_interval = max(0.5, float(reconcile_interval))
        self.lock = threading.RLock()
        self._wake = threading.Event()
        self._stop = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._uevent_thread: Optional[threading.Thread] = None
        self._last_sinks: List[Dict[str, Any]] = []
        self._endpoints: List[Dict[str, Any]] = []
        self._default_name: Optional[str] = None
        self._hdmi_status: Dict[str, Any] = {}
        self._last_decision: Dict[str, Any] = {}
        self._last_route: Dict[str, Any] = {}
        self._last_error: Optional[str] = None
        self._last_event: Optional[str] = None
        self._last_event_at = 0.0
        self._last_hdmi_load_attempt = 0.0
        self._hdmi_load_backoff = 0.0
        self._backend_available = False
        self._updated = 0.0

    # ---- immutable reads -------------------------------------------------
    def _abs(self, rel: str) -> str:
        return os.path.join(self.root, rel.lstrip("/")) if rel.startswith("/") else rel

    def _read(self, rel: str) -> Optional[str]:
        try:
            with open(self._abs(rel), "r", encoding="utf-8", errors="replace") as fh:
                return fh.read().strip()
        except OSError:
            return None

    def read_hdmi_status(self) -> Dict[str, Any]:
        secdp = self._read("/sys/class/switch/secdp/state")
        extcon = self._read("/sys/class/extcon/extcon0/state")
        pcm = parse_dp_pcm(self._read("/proc/asound/pcm"))
        raw = self._read("/sys/class/switch/ch_hdmi_audio/state")
        link = dp_link_ready(secdp, extcon)
        info = parse_dp_audio_info(raw, link, bool(pcm))
        display_name = None
        display_state = None
        try:
            doc = json.loads(Path(self._abs("/run/nuxel-display/status.json")).read_text(encoding="utf-8"))
            if isinstance(doc, dict):
                display_state = doc.get("state")
                if link:
                    display_name = doc.get("display_name")
        except (OSError, ValueError, TypeError):
            pass
        blockers: List[str] = []
        if not link:
            blockers.append("DisplayPort link is not ready (secdp=%s, extcon=%s)"
                            % (secdp or "?", extcon or "?"))
        if pcm is None:
            blockers.append("kernel exposes no 'DP Audio' PCM in /proc/asound/pcm")
        if info.get("reason"):
            blockers.append(str(info["reason"]))
        available = bool(link and pcm is not None and info.get("available"))
        if available:
            blockers = []
        if not link:
            endpoint_state = AUDIO_ABSENT
        elif pcm is None or not info.get("valid"):
            endpoint_state = AUDIO_UNAVAILABLE
        else:
            endpoint_state = AUDIO_AVAILABLE
        return {
            "state": endpoint_state,
            "available": available,
            "dp_link": bool(link),
            "secdp": secdp,
            "extcon": extcon,
            "pcm": pcm,
            "pcm_present": pcm is not None,
            "ch_hdmi_audio": info.get("raw"),
            "ch_hdmi_audio_hex": info.get("value_hex"),
            "audio_info": info,
            "display_state": display_state,
            "display_name": display_name,
            "sink_name": HDMI_SINK,
            "blockers": blockers,
            "blocker": "; ".join(blockers) if blockers else None,
        }

    # ---- endpoint model --------------------------------------------------
    def _build_endpoints(self, sinks: List[Dict[str, Any]],
                         default_name: Optional[str],
                         hdmi: Dict[str, Any]) -> List[Dict[str, Any]]:
        out: List[Dict[str, Any]] = []
        seen = set()
        for sink in sinks:
            endpoint = endpoint_from_sink(sink, default_name, hdmi)
            if endpoint is None:
                continue
            if endpoint["kind"] == KIND_HDMI and not hdmi.get("available"):
                continue
            sid = endpoint["stable_id"]
            if sid in seen:
                continue
            seen.add(sid)
            out.append(endpoint)
        priority = {KIND_SPEAKER: 10, KIND_HDMI: 20, KIND_BLUETOOTH: 30,
                    KIND_USB: 40, KIND_OTHER: 50}
        out.sort(key=lambda e: (priority.get(e.get("kind"), 99),
                                str(e.get("description") or "").lower()))
        return out

    @staticmethod
    def _find_endpoint(endpoints: List[Dict[str, Any]], stable_id: Optional[str] = None,
                       node_name: Optional[str] = None) -> Optional[Dict[str, Any]]:
        for endpoint in endpoints:
            if stable_id and endpoint.get("stable_id") == stable_id:
                return endpoint
            if node_name and endpoint.get("node_name") == node_name:
                return endpoint
        return None

    def _sink_by_name(self, name: Optional[str]) -> Optional[Dict[str, Any]]:
        if not name:
            return None
        for sink in self._last_sinks:
            if _sink_name(sink) == name:
                return sink
        return None

    def _copy_volume_and_mute(self, old_name: Optional[str], target: Dict[str, Any]) -> List[str]:
        notes: List[str] = []
        target_name = str(target.get("node_name") or "")
        if not old_name or old_name == target_name:
            return notes
        old = self._sink_by_name(old_name)
        if old is None:
            return notes
        old_vol = _volume_percent(old)
        old_mute = bool(old.get("mute", False))
        if old_vol is not None:
            if self.backend.set_volume(target_name, old_vol):
                notes.append("volume=%d%%" % old_vol)
            else:
                notes.append("volume copy failed")
        if self.backend.set_muted(target_name, old_mute):
            notes.append("muted=%s" % ("yes" if old_mute else "no"))
        else:
            notes.append("mute copy failed")
        return notes

    def _apply_route_locked(self, target: Dict[str, Any], decision: Dict[str, Any],
                            prior_name: Optional[str]) -> Dict[str, Any]:
        target_name = str(target.get("node_name") or "")
        if not target_name or not target.get("available"):
            return {"success": False, "error": "TARGET_UNAVAILABLE",
                    "detail": "selected output is no longer available"}
        if target_name == prior_name:
            self._call_route_callback(target)
            return {"success": True, "changed": False, "sink": target_name,
                    "moved_streams": 0, "volume_notes": []}
        volume_notes = self._copy_volume_and_mute(prior_name, target)
        if not self.backend.set_default(target_name):
            self._last_error = "pactl set-default-sink %s failed" % target_name
            return {"success": False, "error": "ROUTE_FAILED",
                    "detail": self._last_error, "sink": target_name,
                    "rollback": False, "volume_notes": volume_notes}
        readback = self.backend.default_sink()
        if readback != target_name:
            self._last_error = "default sink readback=%r expected=%r" % (readback, target_name)
            rollback = False
            if prior_name:
                rollback = bool(self.backend.set_default(prior_name))
            return {"success": False, "error": "ROUTE_NOT_CONFIRMED",
                    "detail": self._last_error, "sink": target_name,
                    "readback": readback, "rollback": rollback,
                    "volume_notes": volume_notes}
        moved = 0
        move_errors: List[str] = []
        for index in self.backend.list_sink_inputs():
            if self.backend.move_sink_input(index, target_name):
                moved += 1
            else:
                move_errors.append(str(index))
        if move_errors:
            self._last_error = "active stream move failed for input(s): %s" % ", ".join(move_errors)
        else:
            self._last_error = None
        self._call_route_callback(target)
        return {"success": True, "changed": True, "sink": target_name,
                "moved_streams": moved, "move_errors": move_errors,
                "volume_notes": volume_notes, "decision": decision.get("reason")}

    def _call_route_callback(self, endpoint: Optional[Dict[str, Any]]) -> None:
        if self.on_route is None:
            return
        try:
            self.on_route(endpoint)
        except Exception as exc:  # noqa: BLE001 - routing must survive a UI hook
            self._last_error = "route callback failed: %s" % exc

    # ---- reconciliation --------------------------------------------------
    def _reconcile_locked(self) -> Dict[str, Any]:
        self._backend_available = bool(self.backend.available())
        hdmi = (self.hdmi_reader or self.read_hdmi_status)()
        self._hdmi_status = hdmi
        if not self._backend_available:
            self._endpoints = []
            self._default_name = None
            self._last_error = "PipeWire server is unavailable"
            self._last_decision = {
                "reason_code": "backend-unavailable",
                "reason": "PipeWire server is unavailable; no route was changed",
                "fallback": False,
            }
            self._publish_locked()
            return self.status()

        sinks = self.backend.list_sinks()
        hdmi_name = str((hdmi.get("pcm") or {}).get("hw_path") or "")
        hdmi_present = any(_sink_name(s) == HDMI_SINK for s in sinks)
        if hdmi.get("available") and not hdmi_present and hdmi_name:
            now = time.monotonic()
            wait = self._last_hdmi_load_attempt + self._hdmi_load_backoff - now
            if wait <= 0:
                self._last_hdmi_load_attempt = now
                ok, _module_id, err = self.backend.load_hdmi(hdmi_name, HDMI_SINK)
                if ok:
                    self._hdmi_load_backoff = 0.0
                    # module-alsa-sink publishes its node asynchronously.
                    time.sleep(0.12)
                    sinks = self.backend.list_sinks()
                else:
                    self._hdmi_load_backoff = min(8.0, max(1.0, self._hdmi_load_backoff * 2))
                    self._last_error = "HDMI sink activation failed: %s" % (err or "unknown")
            else:
                self._last_error = "HDMI sink activation backoff %.1fs" % wait

        sinks = self.backend.list_sinks() if not sinks else sinks
        self._last_sinks = sinks
        default_name = self.backend.default_sink()
        self._default_name = default_name
        endpoints = self._build_endpoints(sinks, default_name, hdmi)
        self._endpoints = endpoints
        if not self.prefs.fallback_id:
            speaker = self._find_endpoint(endpoints, stable_id=SPEAKER_ID)
            if speaker is not None and speaker.get("available"):
                self.prefs.fallback_id = SPEAKER_ID
                self.prefs.save()
        current = self._find_endpoint(endpoints, node_name=default_name)
        current_id = current.get("stable_id") if current else None
        decision = choose_output(endpoints, self.prefs.mode, self.prefs.preferred_id,
                                 self.prefs.fallback_id, current_id)
        self._last_decision = {
            "reason_code": decision.get("reason_code"),
            "reason": decision.get("reason"),
            "at": time.time(),
            "target_id": (decision.get("target") or {}).get("stable_id"),
            "target_sink": (decision.get("target") or {}).get("node_name"),
        }
        target = decision.get("target")
        if target is not None:
            self._last_route = self._apply_route_locked(target, decision, default_name)
        else:
            self._last_route = {"success": False, "error": "NO_OUTPUT",
                                "detail": decision.get("reason")}
            self._last_error = decision.get("reason")
            self._call_route_callback(None)

        # The HDMI module is only removed after routing has left it.  Unloading
        # first would leave active streams pointing at a vanished sink.
        if not hdmi.get("available"):
            after_default = self.backend.default_sink()
            if after_default != HDMI_SINK and any(_sink_name(s) == HDMI_SINK for s in self._last_sinks):
                ok, err = self.backend.unload_hdmi(HDMI_SINK)
                if not ok and err:
                    self._last_error = "HDMI sink cleanup failed: %s" % err
                self._last_sinks = [s for s in self._last_sinks
                                    if _sink_name(s) != HDMI_SINK]
                self._endpoints = self._build_endpoints(self._last_sinks, after_default, hdmi)
            self._default_name = after_default
        else:
            self._default_name = self.backend.default_sink() or self._default_name

        current = self._find_endpoint(self._endpoints, node_name=self._default_name)
        if current and current.get("kind") != KIND_HDMI:
            if self.prefs.fallback_id != current.get("stable_id"):
                self.prefs.fallback_id = current.get("stable_id")
                self.prefs.save()
        self._updated = time.time()
        self._publish_locked()
        return self.status()

    def reconcile(self) -> Dict[str, Any]:
        with self.lock:
            try:
                return self._reconcile_locked()
            except Exception as exc:  # noqa: BLE001 - a hardware read must not kill audio
                self._last_error = "reconcile failed: %s" % exc
                self._publish_locked()
                return self.status()

    # ---- status / persistence -------------------------------------------
    def status(self) -> Dict[str, Any]:
        with self.lock:
            endpoints = [dict(e) for e in self._endpoints]
            current = self._find_endpoint(endpoints, node_name=self._default_name)
            if current is not None:
                for endpoint in endpoints:
                    endpoint["default"] = endpoint.get("node_name") == current.get("node_name")
            hdmi_state = self._hdmi_status.get("state") or AUDIO_ABSENT
            if current is not None and current.get("kind") == KIND_HDMI:
                hdmi_state = AUDIO_ACTIVE
            hdmi_doc = dict(self._hdmi_status)
            hdmi_doc["state"] = hdmi_state
            endpoint_state = AUDIO_ACTIVE if current is not None else (
                AUDIO_AVAILABLE if endpoints else hdmi_state)
            preferred = self._find_endpoint(endpoints, stable_id=self.prefs.preferred_id)
            fallback = self._find_endpoint(endpoints, stable_id=self.prefs.fallback_id)
            preferred_available = bool(preferred and preferred.get("available"))
            manual = self.prefs.mode == ROUTING_MANUAL
            volume = current.get("volume_percent") if current else None
            muted = current.get("muted") if current else None
            return {
                "success": True,
                "schema": SCHEMA,
                "backend_available": self._backend_available,
                "endpoint_state": endpoint_state,
                "backend": "pipewire" if self._backend_available else "unavailable",
                "sound_server": "pipewire" if self._backend_available else "unavailable",
                "mode": self.prefs.mode,
                "routing_mode": self.prefs.mode,
                "manual_override": bool(manual and self.prefs.preferred_id),
                "preferred_id": self.prefs.preferred_id,
                "preferred_name": (preferred.get("description") if preferred else
                                   self.prefs.preferred_name),
                "preferred_available": preferred_available,
                "preferred": preferred,
                "fallback_id": self.prefs.fallback_id,
                "fallback": fallback,
                "fallback_active": bool(
                    manual and self.prefs.preferred_id and current is not None and
                    current.get("stable_id") != self.prefs.preferred_id),
                "current": current,
                "current_id": current.get("stable_id") if current else None,
                "current_output": current,
                "selected_output": current,
                "volume_percent": volume,
                "muted": muted,
                "volume_supported": bool(current),
                "mute_supported": bool(current),
                "endpoints": endpoints,
                "outputs": endpoints,
                "hdmi": hdmi_doc,
                "last_decision": self._last_decision,
                "last_route": self._last_route,
                "last_error": self._last_error,
                "last_event": self._last_event,
                "last_event_at": self._last_event_at,
                "updated": self._updated or time.time(),
            }

    def _publish_locked(self) -> None:
        doc = self.status()
        self._updated = time.time()
        doc["updated"] = self._updated
        try:
            self.state_path.parent.mkdir(parents=True, exist_ok=True)
            tmp = self.state_path.with_name(self.state_path.name + ".tmp.%d" % os.getpid())
            tmp.write_text(json.dumps(doc, indent=2, sort_keys=True) + "\n",
                           encoding="utf-8")
            os.chmod(tmp, 0o644)
            os.replace(tmp, self.state_path)
        except OSError:
            pass

    # ---- user actions ----------------------------------------------------
    def _normalize_mode(self, mode: Any) -> Optional[str]:
        text = str(mode or "").strip().lower()
        aliases = {
            "auto": ROUTING_AUTOMATIC, "automatic": ROUTING_AUTOMATIC,
            "manual": ROUTING_MANUAL, "user": ROUTING_MANUAL,
        }
        return aliases.get(text)

    def set_routing(self, mode: Any, preferred_id: Optional[str] = None) -> Dict[str, Any]:
        normalized = self._normalize_mode(mode)
        if normalized is None:
            return {"success": False, "error": "INVALID_ROUTING_MODE",
                    "detail": "mode must be automatic or manual"}
        with self.lock:
            if normalized == ROUTING_MANUAL:
                candidate = _valid_id(preferred_id) or self.prefs.preferred_id
                current = self._find_endpoint(self._endpoints, node_name=self._default_name)
                if candidate is None and current:
                    candidate = current.get("stable_id")
                if candidate is None:
                    return {"success": False, "error": "PREFERRED_OUTPUT_REQUIRED",
                            "detail": "manual mode needs a real output identity"}
                known = self._find_endpoint(self._endpoints, stable_id=candidate)
                if known is not None and not known.get("available"):
                    return {"success": False, "error": "OUTPUT_UNAVAILABLE",
                            "detail": "selected output is not available"}
                self.prefs.preferred_id = candidate
            if normalized == ROUTING_MANUAL and self.prefs.preferred_id:
                known = self._find_endpoint(self._endpoints, stable_id=self.prefs.preferred_id)
                if known is not None:
                    self.prefs.preferred_name = str(known.get("description") or "")[:160] or None
            self.prefs.mode = normalized
            self.prefs.save()
            result = self._reconcile_locked()
            return result

    def select_output(self, stable_id: Any) -> Dict[str, Any]:
        sid = _valid_id(stable_id)
        if sid is None:
            return {"success": False, "error": "INVALID_OUTPUT_ID"}
        with self.lock:
            endpoint = self._find_endpoint(self._endpoints, stable_id=sid)
            if endpoint is None or not endpoint.get("available"):
                return {"success": False, "error": "OUTPUT_UNAVAILABLE",
                        "detail": "that output is not currently available",
                        "status": self.status()}
            self.prefs.mode = ROUTING_MANUAL
            self.prefs.preferred_id = sid
            self.prefs.preferred_name = str(endpoint.get("description") or "")[:160] or None
            self.prefs.save()
            return self._reconcile_locked()

    def set_automatic(self) -> Dict[str, Any]:
        return self.set_routing(ROUTING_AUTOMATIC)

    def set_volume(self, percent: Any) -> Dict[str, Any]:
        try:
            value = int(round(float(percent)))
        except (TypeError, ValueError):
            return {"success": False, "error": "INVALID_VOLUME"}
        value = max(0, min(100, value))
        with self.lock:
            name = self._default_name
            if not name:
                return {"success": False, "error": "NO_CURRENT_OUTPUT"}
            if not self.backend.set_volume(name, value):
                return {"success": False, "error": "VOLUME_SET_FAILED",
                        "detail": self.backend.last_error}
            self._last_sinks = self.backend.list_sinks()
            for sink in self._last_sinks:
                if _sink_name(sink) == name:
                    break
            self._endpoints = self._build_endpoints(self._last_sinks, name, self._hdmi_status)
            self._publish_locked()
            return {"success": True, "volume_percent": value, "sink": name}

    def set_muted(self, muted: Any) -> Dict[str, Any]:
        value = bool(muted)
        with self.lock:
            name = self._default_name
            if not name:
                return {"success": False, "error": "NO_CURRENT_OUTPUT"}
            if not self.backend.set_muted(name, value):
                return {"success": False, "error": "MUTE_SET_FAILED",
                        "detail": self.backend.last_error}
            self._last_sinks = self.backend.list_sinks()
            self._endpoints = self._build_endpoints(self._last_sinks, name, self._hdmi_status)
            self._publish_locked()
            return {"success": True, "muted": value, "sink": name}

    def diagnostics(self) -> Dict[str, Any]:
        doc = self.status()
        doc["backend_error"] = getattr(self.backend, "last_error", None)
        doc["policy_path"] = str(self.prefs.path)
        doc["policy_load_error"] = self.prefs.load_error
        doc["state_path"] = str(self.state_path)
        return doc

    # ---- event-driven lifecycle -----------------------------------------
    def start(self) -> None:
        with self.lock:
            if self._thread is not None:
                return
            self._stop.clear()
            self._thread = threading.Thread(target=self._loop,
                                            name="nuxel-audio-output-policy",
                                            daemon=True)
            self._thread.start()
            self._start_uevent_listener()

    def stop(self) -> None:
        self._stop.set()
        self._wake.set()

    def _loop(self) -> None:
        while not self._stop.is_set():
            self.reconcile()
            self._wake.wait(self.reconcile_interval)
            self._wake.clear()

    def _start_uevent_listener(self) -> None:
        if self.root != "/" or self._uevent_thread is not None:
            return

        def worker() -> None:
            sock = None
            try:
                proto = getattr(socket, "NETLINK_KOBJECT_UEVENT", 15)
                sock = socket.socket(socket.AF_NETLINK, socket.SOCK_DGRAM, proto)
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 1 << 20)
                sock.bind((0, 1))
                sock.settimeout(1.0)
                markers = ("SUBSYSTEM=extcon", "SUBSYSTEM=switch", "SUBSYSTEM=typec",
                           "SUBSYSTEM=usb", "SUBSYSTEM=drm", "SUBSYSTEM=sound",
                           "ch_hdmi_audio", "secdp", "displayport", "hdmi")
                while not self._stop.is_set():
                    try:
                        data = sock.recv(8192)
                    except socket.timeout:
                        continue
                    except OSError:
                        break
                    text = data.decode("utf-8", "replace")
                    if any(marker in text for marker in markers):
                        self._last_event = text.splitlines()[0][:180] if text else "uevent"
                        self._last_event_at = time.time()
                        self._wake.set()
            except Exception as exc:  # noqa: BLE001
                self._last_error = "uevent listener unavailable: %s" % exc
            finally:
                if sock is not None:
                    try:
                        sock.close()
                    except OSError:
                        pass

        self._uevent_thread = threading.Thread(target=worker,
                                               name="nuxel-audio-uevent", daemon=True)
        self._uevent_thread.start()
