#!/usr/bin/env python3
"""S10+ microphone control and real signal probe.

Controls the existing static PipeWire source (alsa_input.hw_0_13 / WDMA1).
The vendor ABOX/CS47L93 route is owned by nuxel-mic-route.service and is never
rewritten here.  No control is reported as hardware gain unless a real writable
ALSA capture-gain control exists; otherwise the change is labelled digital
PipeWire input volume.
"""
from __future__ import annotations

import math
import os
import re
import shutil
import struct
import subprocess
import time
from pathlib import Path

RUNTIME = os.environ.get("NUXEL_PW_RUNTIME", "/run/nuxel-wayland")
WPCTL = shutil.which("wpctl") or "/usr/bin/wpctl"
PW_CLI = shutil.which("pw-cli") or "/usr/bin/pw-cli"
PW_CAT = shutil.which("pw-cat") or "/usr/bin/pw-cat"
AMIXER = shutil.which("amixer") or "/usr/bin/amixer"
FILTER_MODULE = "/usr/lib64/pipewire-0.3/libpipewire-module-filter-chain.so"
SUPPRESSION_CONFIG = "/etc/pipewire/pipewire.conf.d/52-nuxel-noise-suppression.conf"
STATE_FILE = "/var/lib/nuxel/audio/microphone.json"
STUB = {
    "schema_version": 1,
    "volume_percent": 100,
    "muted": False,
    "noise_suppression": False,
    "updated_at": 0,
}


def _run(argv, timeout=5.0, binary=False):
    env = dict(os.environ)
    env["XDG_RUNTIME_DIR"] = RUNTIME
    env["PIPEWIRE_RUNTIME_DIR"] = RUNTIME
    try:
        return subprocess.run(argv, capture_output=True, timeout=timeout,
                              stdin=subprocess.DEVNULL, env=env, text=not binary)
    except (OSError, subprocess.SubprocessError) as exc:
        return None if binary else type("R", (), {"returncode": 127, "stdout": "", "stderr": str(exc)})()


def _state() -> dict:
    import json
    try:
        doc = json.loads(Path(STATE_FILE).read_text())
        if isinstance(doc, dict):
            base = dict(STUB)
            base.update(doc)
            return base
    except (OSError, ValueError):
        pass
    return dict(STUB)


def _save_state(doc: dict) -> None:
    import json
    try:
        path = Path(STATE_FILE)
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_name(path.name + ".tmp")
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(doc, fh, indent=2, sort_keys=True)
            fh.write("\n")
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, path)
        # This file contains only control values, never captured audio.
        try:
            import pwd
            pw = pwd.getpwnam("nuxel")
            os.chown(path, pw.pw_uid, pw.pw_gid)
        except (KeyError, OSError):
            pass
        os.chmod(path, 0o600)
    except OSError:
        pass


def _sources():
    proc = _run([WPCTL, "status"], timeout=5)
    if not proc or proc.returncode != 0:
        return [], (proc.stderr.strip() if proc else "wpctl unavailable")
    rows = []
    in_sources = False
    for line in (proc.stdout or "").splitlines():
        if line.strip() == "Sources:":
            in_sources = True
            continue
        if in_sources and re.match(r"^\s*[├└]", line) and "Sources:" not in line and not re.search(r"^\s*[│ ]*[├└]?\s*\*?\s*\d+\.", line):
            # Header lines like Filters/Streams end the sources section.
            if re.search(r"^\s*[├└]─\s*(Filters|Streams|Sinks|Devices):", line):
                break
        if not in_sources:
            continue
        m = re.search(r"^\s*[│ ]*[├└]?\s*(\*)?\s*(\d+)\.\s+(.+?)\s+\[vol:\s*([0-9.]+)(?:\s+MUTED)?\]\s*$", line)
        if m:
            rows.append({"default": bool(m.group(1)), "id": int(m.group(2)),
                         "name": m.group(3).strip(), "volume": float(m.group(4)),
                         "muted": "MUTED" in line})
    return rows, None


def _inspect(node_id: int):
    proc = _run([WPCTL, "inspect", str(node_id)], timeout=4)
    fields = {}
    if proc and proc.returncode == 0:
        for line in (proc.stdout or "").splitlines():
            line = line.strip()
            if "=" in line:
                k, v = line.split("=", 1)
                fields[k.strip()] = v.strip().strip('"')
    return fields


def _hardware_gain_controls():
    """Return real writable capture-gain controls, if this codec exposes any."""
    cards = Path("/proc/asound/cards")
    try:
        text = cards.read_text()
    except OSError:
        return []
    m = re.search(r"^\s*(\d+)\s+\[beyondmadera", text, re.M)
    if not m:
        return []
    card = m.group(1)
    proc = _run([AMIXER, "-c", card, "scontrols"], timeout=5)
    if not proc or proc.returncode != 0:
        return []
    candidates = []
    for line in (proc.stdout or "").splitlines():
        m = re.search(r"Simple mixer control '([^']+)'", line)
        if not m:
            continue
        name = m.group(1)
        low = name.lower()
        if not any(k in low for k in ("mic", "in3", "pga", "adc", "boost", "capture")):
            continue
        if any(k in low for k in ("input", "switch", "route", "src", "rate", "width", "mux", "asrc", "isrc", "sifm", "nsrc")):
            continue
        detail = _run([AMIXER, "-c", card, "sget", name], timeout=4)
        text = (detail.stdout or "") + (detail.stderr or "") if detail else ""
        if "type=INTEGER" not in text or "access=rw" not in text:
            continue
        lim = re.search(r"Limits:\s*(?:Playback|Capture)\s+(-?\d+)\s+-\s+(-?\d+)", text)
        val = re.search(r":\s*values=(-?\d+)", text)
        if lim and val:
            candidates.append({"card": card, "name": name,
                               "min": int(lim.group(1)), "max": int(lim.group(2)),
                               "value": int(val.group(1)), "kind": "hardware"})
    return candidates


def status() -> dict:
    sources, err = _sources()
    source = next((s for s in sources if s["default"]), sources[0] if sources else None)
    hw = _hardware_gain_controls()
    saved = _state()
    supp = suppression_status()
    return {
        "success": True,
        "available": bool(source),
        "source": source,
        "sources": sources,
        "error": err,
        "volume_percent": int(round((source["volume"] if source else saved.get("volume_percent", 100) / 100.0) * 100)),
        "muted": bool(source["muted"]) if source else bool(saved.get("muted")),
        "gain": {
            "hardware_controls": hw,
            "hardware_available": bool(hw),
            "control": "hardware ALSA capture gain" if hw else "digital PipeWire input volume",
            "note": ("A real writable ALSA capture-gain control is present." if hw else
                     "No writable ALSA capture-gain control matched this route; the 0-100% slider changes digital input gain only."),
        },
        "noise_suppression": supp,
        "state_file": STATE_FILE,
        "route_state": "/run/nuxel-mic-route.state",
    }


def suppression_status() -> dict:
    module = os.path.exists(FILTER_MODULE)
    config = os.path.exists(SUPPRESSION_CONFIG)
    return {
        "available": bool(module and config),
        "enabled": False,
        "module_present": module,
        "config_present": config,
        "reason": (None if module and config else
                   ("Pipeline module exists but no verified Nuxel suppression graph is installed"
                    if module else "libpipewire-module-filter-chain is not installed")),
        "implementation": "PipeWire filter-chain (not simulated)",
    }


def set_volume(percent: int) -> dict:
    sources, err = _sources()
    source = next((s for s in sources if s["default"]), sources[0] if sources else None)
    if not source:
        return {"success": False, "error": "no capture source", "detail": err,
                "error_code": "NO_MIC"}
    try:
        percent = max(0, min(100, int(percent)))
    except (TypeError, ValueError):
        return {"success": False, "error": "volume must be 0..100", "error_code": "INVALID_VOLUME"}
    proc = _run([WPCTL, "set-volume", str(source["id"]), "%.2f" % (percent / 100.0)], timeout=5)
    if not proc or proc.returncode != 0:
        return {"success": False, "error": "PipeWire rejected the input-volume change",
                "detail": (proc.stderr.strip() if proc else "wpctl unavailable")}
    saved = _state()
    saved["volume_percent"] = percent
    saved["updated_at"] = int(time.time())
    _save_state(saved)
    again = status()
    return {"success": True, "service_state": again, "applied": "digital",
            "volume_percent": again.get("volume_percent")}


def set_mute(muted: bool) -> dict:
    sources, err = _sources()
    source = next((s for s in sources if s["default"]), sources[0] if sources else None)
    if not source:
        return {"success": False, "error": "no capture source", "detail": err,
                "error_code": "NO_MIC"}
    proc = _run([WPCTL, "set-mute", str(source["id"]), "1" if muted else "0"], timeout=5)
    if not proc or proc.returncode != 0:
        return {"success": False, "error": "PipeWire rejected the mute change",
                "detail": (proc.stderr.strip() if proc else "wpctl unavailable")}
    saved = _state()
    saved["muted"] = bool(muted)
    saved["updated_at"] = int(time.time())
    _save_state(saved)
    return {"success": True, "service_state": status()}


def level(duration_ms: int = 280) -> dict:
    """Capture a short private PCM window and return measured metrics only."""
    sources, err = _sources()
    source = next((s for s in sources if s["default"]), sources[0] if sources else None)
    if not source:
        return {"success": False, "error": "no capture source", "detail": err,
                "error_code": "NO_MIC"}
    duration_ms = max(120, min(1000, int(duration_ms or 280)))
    env = dict(os.environ, XDG_RUNTIME_DIR=RUNTIME, PIPEWIRE_RUNTIME_DIR=RUNTIME)
    argv = [PW_CAT, "--record", "--target", str(source["id"]), "--raw",
            "--format", "s16", "--rate", "48000", "--channels", "2",
            "--latency", "30ms", "-"]
    try:
        proc = subprocess.run(argv, capture_output=True, timeout=duration_ms / 1000.0 + 2.0,
                              stdin=subprocess.DEVNULL, env=env)
    except (OSError, subprocess.SubprocessError) as exc:
        return {"success": False, "error": "capture failed", "detail": str(exc),
                "error_code": "CAPTURE_FAILED"}
    # A timeout is expected: pw-cat is a continuous stream.
    data = proc.stdout or b""
    # Keep only a bounded window even if pw-cat drained more than requested.
    data = data[:48000 * 2 * 2]
    n = len(data) // 2
    if n <= 0:
        return {"success": False, "error": "capture returned no samples",
                "error_code": "NO_SAMPLES", "stderr": (proc.stderr or b"")[-300:].decode("utf-8", "replace")}
    vals = struct.unpack("<%dh" % n, data[:n * 2])
    metrics = {}
    for ch, label in ((0, "left"), (1, "right")):
        v = vals[ch::2]
        peak = max(abs(x) for x in v) / 32768.0 if v else 0.0
        rms = math.sqrt(sum(x * x for x in v) / len(v)) / 32768.0 if v else 0.0
        dc = sum(v) / len(v) / 32768.0 if v else 0.0
        clip = sum(1 for x in v if abs(x) >= 32700)
        metrics[label] = {"peak": round(peak, 6), "rms": round(rms, 6),
                          "dc": round(dc, 6), "clipped_samples": clip,
                          "samples": len(v)}
    db = 20 * math.log10(max(metrics["left"]["rms"], 1e-9))
    return {"success": True, "duration_ms": int(n / 48000 * 1000 / 2),
            "sample_rate": 48000, "channels": 2, "metrics": metrics,
            "rms_dbfs": round(db, 2), "clipped": any(m["clipped_samples"] for m in metrics.values()),
            "source": source}


def set_suppression(enabled: bool) -> dict:
    st = suppression_status()
    if enabled and not st["available"]:
        return {"success": False, "error": "noise suppression unavailable",
                "detail": st["reason"], "error_code": "NO_SUPPRESSION_NODE",
                "status": st}
    # Enabling a real filter requires a verified graph and a PipeWire restart;
    # this build does not pretend it exists.
    return {"success": False, "error": "not implemented in this build",
            "detail": "A verified low-latency suppression graph is not installed; toggle stays disabled.",
            "error_code": "NO_VERIFIED_FILTER", "status": st}


def rpc(app_id: str, verb: str, params: dict) -> dict:
    params = params if isinstance(params, dict) else {}
    allowed = {"status", "volume", "mute", "level", "suppression"}
    if verb not in allowed:
        return {"success": False, "error": "unknown microphone verb: %s" % verb,
                "error_code": "UNKNOWN_VERB"}
    if verb == "status":
        return status()
    if verb == "volume":
        return set_volume(params.get("percent", 100))
    if verb == "mute":
        return set_mute(bool(params.get("muted", True)))
    if verb == "level":
        return level(params.get("duration_ms", 280))
    return set_suppression(bool(params.get("enabled", False)))
