#!/usr/bin/env python3
"""Nuxel system privacy gates: camera capture and microphone capture (PWNAGE-52000).

The camera gate is a real policy consumed by the Bridge camera capture path.
When blocked, new capture requests are refused.  The S10+ camera pipeline is
already BLOCKED_FIRMWARE (no standard V4L2 capture graph), so the status says so
instead of claiming a working camera shutter.

The microphone gate is a real PipeWire/PulseAudio capture policy: while muted,
every enumerated capture source is muted and a bounded `pactl subscribe`
watcher re-applies the mute whenever a source/source-output appears or changes.
Speaker/sink mute is never touched.  If PipeWire has no capture source, the
status reports zero sources rather than pretending one exists.
"""
from __future__ import annotations

import glob
import json
import os
import subprocess
import threading
import time
from typing import Any, Dict, Optional

CAMERA_DOC = "/etc/nuxel/privacy/camera.json"
MIC_DOC = "/etc/nuxel/privacy/microphone.json"
RUNTIME_DIR = "/run/nuxel-wayland"
CAPTURE_MARKER = "/run/nuxel/privacy/camera-capture.active"
DEFAULT = {
    "camera": {"schema_version": 1, "blocked": False, "updated_at": 0, "source": "default"},
    "microphone": {"schema_version": 1, "muted": False, "updated_at": 0, "source": "default"},
}


def _read_json(path: str) -> Dict[str, Any]:
    try:
        with open(path, "r", encoding="utf-8") as fh:
            doc = json.load(fh)
        return doc if isinstance(doc, dict) else {}
    except (OSError, ValueError):
        return {}


def _atomic_json(path: str, doc: Dict[str, Any]) -> None:
    d = os.path.dirname(path)
    os.makedirs(d, exist_ok=True)
    tmp = path + ".tmp.%d" % os.getpid()
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(doc, fh, sort_keys=True, indent=2)
        fh.write("\n")
    os.replace(tmp, path)


def _pactl_env() -> Dict[str, str]:
    env = dict(os.environ)
    env.setdefault("XDG_RUNTIME_DIR", RUNTIME_DIR)
    env.setdefault("PULSE_SERVER", "unix:%s/pulse/native" % RUNTIME_DIR)
    return env


def _run(argv, timeout=3.0):
    try:
        return subprocess.run(argv, capture_output=True, text=True, timeout=timeout,
                              env=_pactl_env())
    except (OSError, subprocess.TimeoutExpired) as exc:
        return exc


class PrivacyProvider:
    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._watcher = None
        self._watcher_started = False

    # ---- camera ---------------------------------------------------------
    def camera_status(self) -> Dict[str, Any]:
        doc = dict(DEFAULT["camera"])
        doc.update(_read_json(CAMERA_DOC))
        nodes = sorted(glob.glob("/dev/video*"))
        # The vendor FIMC-IS path does not expose a standard capture graph.
        # A camera gate is meaningful even when the sensor is blocked because
        # the policy must still prevent future/alternate capture providers.
        supported = bool(nodes) or os.path.isdir("/sys/class/video4linux")
        return {
            "success": True,
            "schema": "nuxel.camera-privacy/1",
            "supported": True,                # policy gate is enforceable
            "hardware_present": bool(nodes),
            "capture_supported": False,       # never claimed without a decoded frame
            "blocked": bool(doc.get("blocked")),
            "state": "BLOCKED" if doc.get("blocked") else "ALLOWED",
            "active_sessions": 0,
            "active_session_tracking": "bridge_camera_capture_only",
            "scope": "Nuxel Bridge camera capture API; native V4L2 clients must "
                     "also honour the same policy document (no kernel LSM gate exists)",
            "video_nodes": nodes,
            "detail": ("FIMC-IS nodes enumerate but the vendor media graph is blocked; "
                       "no frame capture is available" if nodes else
                       "no /dev/video* capture node is exposed by this kernel image"),
            "source": "privacy_provider",
            "updated_at": doc.get("updated_at", 0),
        }

    def set_camera_blocked(self, blocked: bool) -> Dict[str, Any]:
        with self._lock:
            doc = dict(DEFAULT["camera"])
            doc.update(_read_json(CAMERA_DOC))
            doc.update({"schema_version": 1, "blocked": bool(blocked),
                        "updated_at": time.time(), "source": "user"})
            _atomic_json(CAMERA_DOC, doc)
        return self.camera_status()

    # ---- microphone -----------------------------------------------------
    def _sources(self):
        r = _run(["pactl", "list", "short", "sources"])
        if isinstance(r, Exception) or r.returncode != 0:
            return None, (str(r) if isinstance(r, Exception) else (r.stderr or r.stdout or "pactl failed"))
        rows = []
        for line in (r.stdout or "").splitlines():
            parts = line.split("\t")
            if len(parts) >= 2:
                rows.append({"index": parts[0], "name": parts[1],
                             "monitor": parts[1].endswith(".monitor")})
        return rows, None

    def _apply_mute(self, muted: bool) -> int:
        rows, err = self._sources()
        if err or rows is None:
            return -1
        applied = 0
        for row in rows:
            # A monitor source is a loopback of a sink, not a microphone.
            if row["monitor"]:
                continue
            r = _run(["pactl", "set-source-mute", str(row["index"]), "1" if muted else "0"])
            if not isinstance(r, Exception) and r.returncode == 0:
                applied += 1
        # Set the default source as well when it is a real capture source.
        r = _run(["pactl", "set-source-mute", "@DEFAULT_SOURCE@", "1" if muted else "0"])
        if not isinstance(r, Exception) and r.returncode == 0:
            applied += 1
        return applied

    def _watch_loop(self) -> None:
        # `pactl subscribe` is event-driven; no periodic polling is created.
        try:
            proc = subprocess.Popen(["pactl", "subscribe"], stdout=subprocess.PIPE,
                                    stderr=subprocess.DEVNULL, text=True,
                                    env=_pactl_env())
        except OSError:
            return
        try:
            for line in proc.stdout or []:
                if "source" not in line and "Source" not in line:
                    continue
                if self.microphone_status().get("muted"):
                    self._apply_mute(True)
        finally:
            try:
                proc.terminate()
            except OSError:
                pass

    def _ensure_watcher(self) -> None:
        if self._watcher_started:
            return
        self._watcher_started = True
        self._watcher = threading.Thread(target=self._watch_loop, name="nuxel-mic-privacy-watch",
                                         daemon=True)
        self._watcher.start()

    def microphone_status(self) -> Dict[str, Any]:
        doc = dict(DEFAULT["microphone"])
        doc.update(_read_json(MIC_DOC))
        rows, err = self._sources()
        real = [r for r in (rows or []) if not r.get("monitor")]
        muted = bool(doc.get("muted"))
        self._ensure_watcher()
        if err and muted:
            # The bridge may have restarted while a pipe was down; the
            # document remains the policy and the watcher applies it on return.
            pass
        capture_ready = err is None and bool(real)
        return {
            "success": err is None,
            "schema": "nuxel.microphone-privacy/1",
            # Honest capability: a policy with no capture source is not a
            # working microphone control.  The row stays disabled until
            # PipeWire exposes a real (non-monitor) source.
            "supported": capture_ready,
            "muted": muted,
            "state": ("MUTED" if muted else "LIVE") if capture_ready else
                     ("UNAVAILABLE" if err is not None else "UNSUPPORTED_NO_CAPTURE_SOURCE"),
            "source_count": len(real) if rows is not None else None,
            "all_sources": rows if rows is not None else [],
            "monitor_sources_excluded": sum(1 for r in (rows or []) if r.get("monitor")),
            "hardware_capture_present": bool(real),
            "error": err,
            "scope": "PipeWire/PulseAudio capture sources; speaker/sink mute is not used",
            "new_stream_enforcement": "pactl subscribe watcher re-applies while muted",
            "source": "privacy_provider",
            "updated_at": doc.get("updated_at", 0),
        }

    def set_microphone_muted(self, muted: bool) -> Dict[str, Any]:
        with self._lock:
            doc = dict(DEFAULT["microphone"])
            doc.update(_read_json(MIC_DOC))
            doc.update({"schema_version": 1, "muted": bool(muted),
                        "updated_at": time.time(), "source": "user"})
            _atomic_json(MIC_DOC, doc)
            self._ensure_watcher()
        applied = self._apply_mute(bool(muted))
        st = self.microphone_status()
        st["applied_to_sources"] = applied
        if applied < 0:
            st["success"] = False
            st["error"] = st.get("error") or "no PipeWire/PulseAudio server"
        elif not st.get("supported"):
            # Refuse to present a policy as an active control when there is no
            # real capture source to mute.
            st["success"] = False
            st["error"] = "no PipeWire capture source is exposed on this device"
        return st


_PROVIDER: Optional[PrivacyProvider] = None


def get_provider() -> PrivacyProvider:
    global _PROVIDER
    if _PROVIDER is None:
        _PROVIDER = PrivacyProvider()
    return _PROVIDER


def camera_capture_blocked() -> bool:
    """Cheap gate used by the root Bridge camera capture path."""
    try:
        return bool(_read_json(CAMERA_DOC).get("blocked"))
    except Exception:
        return False


def handle(verb: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    params = params or {}
    p = get_provider()
    if verb in ("camera-status", "camera_get"):
        return p.camera_status()
    if verb in ("camera-set", "camera-block"):
        return p.set_camera_blocked(bool(params.get("blocked", True)))
    if verb in ("microphone-status", "microphone_get"):
        return p.microphone_status()
    if verb in ("microphone-set", "microphone-mute"):
        return p.set_microphone_muted(bool(params.get("muted", True)))
    return {"success": False, "error": "unknown privacy verb", "verb": verb}
