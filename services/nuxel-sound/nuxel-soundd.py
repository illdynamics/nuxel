#!/usr/bin/env python3
"""Nuxel central sound manager (PWNAGE-81000).

One daemon owns:
  * discovery/metadata for the user sound library (~/Sounds) and the shipped
    library (/usr/share/nuxel/sounds);
  * the per-action assignments (volume, boot, alarm, timer, message,
    notification, other), persisted in /var/lib/nuxel/sound/assignments.json;
  * one already-initialized PipeWire playback stream (pw-cat) that is kept
    alive with inaudible silence.  A cue is pre-decoded to 48 kHz stereo PCM,
    so a volume change never forks a player, decoder, audio server or route
    check.  Repeated requests replace the pending cue instead of queueing stale
    sounds.

The daemon is control-plane only over a private Unix socket.  It never reads
cookies, credentials, message contents or any user document.  Paths are
resolved and constrained to the two sound directories; imports are validated by
FFprobe before they are installed and are written as the nuxel user.
"""
from __future__ import annotations

import base64
import concurrent.futures
import fcntl
import json
import logging
import os
import re
import shutil
import signal
import socket
import subprocess
import sys
import threading
import time
from pathlib import Path

ACTIONS = ["volume", "boot", "alarm", "timer", "message", "notification", "other"]
ACTION_LABELS = {
    "volume": "Volume change",
    "boot": "Boot-up",
    "alarm": "Alarm",
    "timer": "Timer",
    "message": "Receiving messages",
    "notification": "Notifications",
    "other": "Other future events",
}
ALLOWED_EXT = {".mp3", ".wav", ".ogg", ".oga", ".flac", ".m4a", ".aac", ".opus"}
DEFAULT_FILES = {
    "volume": "nuxel-pow.mp3",
    "boot": "nuxel-boot-audio.mp3",
    "alarm": "nuxel-alarm.mp3",
    "timer": "nuxel-alarm.mp3",
    "message": "nuxel-pow.mp3",
    "notification": "nuxel-pow.mp3",
    "other": "nuxel-pow.mp3",
}
HOME = Path(os.environ.get("NUXEL_HOME", "/home/nuxel"))
USER_DIR = HOME / "Sounds"
SHARED_DIR = Path(os.environ.get("NUXEL_SOUND_LIBRARY", "/usr/share/nuxel/sounds"))
ASSIGN_FILE = Path(os.environ.get("NUXEL_SOUND_ASSIGNMENTS", "/var/lib/nuxel/sound/assignments.json"))
PROBE_CACHE_FILE = Path(os.environ.get("NUXEL_SOUND_PROBE_CACHE", "/var/lib/nuxel/sound/metadata-cache.json"))
SOCKET_PATH = Path(os.environ.get("NUXEL_SOUNDD_SOCKET", "/run/nuxel/soundd.sock"))
RUNTIME = Path(os.environ.get("NUXEL_RUNTIME", "/run/nuxel"))
PW_RUNTIME = os.environ.get("NUXEL_PW_RUNTIME", "/run/nuxel-wayland")
WARMUP = "/usr/lib/nuxel/nuxel-audio-warmup"
LOG = os.environ.get("NUXEL_SOUNDD_LOG", "/var/log/nuxel/soundd.log")
RATE = 48000
CHANNELS = 2
FRAME_MS = 10
FRAME_SAMPLES = RATE * FRAME_MS // 1000
FRAME_BYTES = FRAME_SAMPLES * CHANNELS * 2
# The persistent pw-cat stream must never be paced by a Python timer.  A timer
# drifts under load and starves the graph (measured: ~9 PipeWire errors every
# 5 s while idle).  Keep a small kernel pipe buffer full and let pw-cat's
# blocking read own the clock.  8 KiB is about 43 ms of 48 kHz stereo PCM, so
# even the worst-case cue delay stays below the 100 ms feedback budget.
STREAM_LATENCY = os.environ.get("NUXEL_SOUND_STREAM_LATENCY", "40ms")
PIPE_BUFFER_BYTES = int(os.environ.get("NUXEL_SOUND_PIPE_BYTES", "8192"))
MAX_CUE_SECONDS = 45
MAX_IMPORT_BYTES = 24 * 1024 * 1024
FFMPEG = shutil.which("ffmpeg") or "/usr/bin/ffmpeg"
FFPROBE = shutil.which("ffprobe") or "/usr/bin/ffprobe"
PW_CAT = shutil.which("pw-cat") or "/usr/bin/pw-cat"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[logging.StreamHandler(sys.stderr)],
)
LOG_HANDLER = None
try:
    Path(LOG).parent.mkdir(parents=True, exist_ok=True)
    LOG_HANDLER = logging.FileHandler(LOG)
    LOG_HANDLER.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    logging.getLogger().addHandler(LOG_HANDLER)
except OSError:
    pass


def _atomic_json(path: Path, doc: dict, mode: int = 0o644) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp.%d" % os.getpid())
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(doc, fh, indent=2, sort_keys=True)
        fh.write("\n")
        fh.flush()
        os.fsync(fh.fileno())
    os.chmod(tmp, mode)
    os.replace(tmp, path)


def _safe_within(path: Path, roots: list[Path]) -> bool:
    try:
        real = path.resolve(strict=True)
    except OSError:
        return False
    for root in roots:
        try:
            real.relative_to(root.resolve())
            return True
        except (ValueError, OSError):
            continue
    return False


def _sanitize_name(name: str) -> str:
    name = os.path.basename(str(name or "")).strip()
    name = re.sub(r"[^A-Za-z0-9._ -]+", "_", name)
    name = name.strip(" .")
    if not name:
        name = "nuxel-sound"
    stem, ext = os.path.splitext(name)
    ext = ext.lower()
    if ext not in ALLOWED_EXT:
        ext = ".mp3"
    return (stem[:80] or "nuxel-sound") + ext


def probe(path: Path) -> dict:
    info = {
        "path": str(path),
        "name": path.name,
        "format": path.suffix.lower().lstrip("."),
        "size": None,
        "duration": None,
        "codec": None,
        "sample_rate": None,
        "channels": None,
        "valid": False,
        "error": None,
    }
    try:
        st = path.stat()
        info["size"] = st.st_size
        info["mtime"] = st.st_mtime
    except OSError as exc:
        info["error"] = str(exc)
        return info
    if path.suffix.lower() not in ALLOWED_EXT:
        info["error"] = "unsupported extension %s" % path.suffix
        return info
    if not shutil.which("ffprobe") and not Path(FFPROBE).exists():
        # Minimal offline fallback: magic bytes only.  The live image installs
        # FFprobe; a missing decoder is reported honestly instead of guessed.
        try:
            head = path.read_bytes()[:12]
        except OSError as exc:
            info["error"] = str(exc)
            return info
        if head.startswith(b"RIFF") and b"WAVE" in head[:12]:
            info["codec"] = "pcm"
            info["valid"] = True
        elif head.startswith(b"ID3") or head[:2] in (b"\xff\xfb", b"\xff\xf3", b"\xff\xf2"):
            info["codec"] = "mp3"
            info["valid"] = True
        else:
            info["error"] = "ffprobe unavailable and no known audio magic"
        return info
    try:
        proc = subprocess.run(
            [FFPROBE, "-v", "error", "-show_entries",
             "format=duration,format_name:stream=codec_name,sample_rate,channels,bit_rate",
             "-of", "json", str(path)],
            capture_output=True, text=True, timeout=8,
            stdin=subprocess.DEVNULL,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        info["error"] = "ffprobe failed: %s" % exc
        return info
    if proc.returncode != 0:
        info["error"] = (proc.stderr or "ffprobe rejected the file").strip()[-300:]
        return info
    try:
        doc = json.loads(proc.stdout or "{}")
    except ValueError as exc:
        info["error"] = "ffprobe JSON: %s" % exc
        return info
    fmt = doc.get("format") or {}
    streams = doc.get("streams") or []
    audio = next((s for s in streams if s.get("codec_name")), {})
    info["format"] = fmt.get("format_name") or info["format"]
    try:
        info["duration"] = float(fmt.get("duration")) if fmt.get("duration") else None
    except (TypeError, ValueError):
        pass
    info["codec"] = audio.get("codec_name")
    try:
        info["sample_rate"] = int(audio.get("sample_rate")) if audio.get("sample_rate") else None
    except (TypeError, ValueError):
        pass
    try:
        info["channels"] = int(audio.get("channels")) if audio.get("channels") else None
    except (TypeError, ValueError):
        pass
    if info["codec"]:
        info["valid"] = True
    else:
        info["error"] = "no audio stream reported by ffprobe"
    return info


def decode_pcm(path: Path, gain: float = 1.0) -> bytes:
    if not Path(FFMPEG).exists():
        raise RuntimeError("ffmpeg is not installed; cannot decode %s" % path)
    proc = subprocess.run(
        [FFMPEG, "-nostdin", "-v", "error", "-i", str(path),
         "-t", str(MAX_CUE_SECONDS), "-f", "s16le", "-acodec", "pcm_s16le",
         "-ac", str(CHANNELS), "-ar", str(RATE), "-"],
        capture_output=True, timeout=30, stdin=subprocess.DEVNULL,
    )
    if proc.returncode != 0 or not proc.stdout:
        detail = (proc.stderr or b"")[-400:].decode("utf-8", "replace")
        raise RuntimeError("ffmpeg decode failed rc=%d %s" % (proc.returncode, detail))
    pcm = bytearray(proc.stdout)
    if len(pcm) % 2:
        pcm = pcm[:-1]
    gain = max(0.0, min(1.0, float(gain)))
    if abs(gain - 1.0) > 0.001:
        import array
        samples = array.array("h")
        samples.frombytes(bytes(pcm))
        if sys.byteorder != "little":
            samples.byteswap()
        scale = gain
        if scale == 0:
            samples = array.array("h", [0]) * len(samples)
        else:
            for i, value in enumerate(samples):
                samples[i] = max(-32768, min(32767, int(value * scale)))
        if sys.byteorder != "little":
            samples.byteswap()
        pcm = bytearray(samples.tobytes())
    return bytes(pcm)


class SoundPlayer:
    def __init__(self) -> None:
        self.lock = threading.Condition()
        self.active = None
        self.pending = None
        self.running = True
        self.proc = None
        self.last_error = None
        self.started_at = None
        self.restarts = 0
        self._start_lock = threading.Lock()
        self._last_start_attempt = 0.0
        self._start_backoff = 0.0
        self._stream_ready_at = None
        self._cue_requested_at = None
        self._cue_first_audio_at = None
        self._last_cue_latency_ms = None
        self._last_cue_finished_at = None
        self._last_cue_action = None
        self._last_write_restart = 0.0
        self.thread = threading.Thread(target=self._loop, name="nuxel-sound-player", daemon=True)

    def start(self) -> None:
        self.thread.start()

    def play(self, cue: dict) -> None:
        cue = dict(cue)
        cue.setdefault("loop", False)
        cue.setdefault("token", None)
        cue.setdefault("action", "other")
        cue["requested_monotonic"] = time.monotonic()
        with self.lock:
            # A volume slider can produce many events while one short cue is
            # still playing.  A newer volume cue supersedes the active one
            # instead of queueing behind it and sounding stale.  Alarm/timer
            # cues retain their explicit stop/token ownership.
            if cue.get("action") == "volume" and self.active and \
                    self.active.get("action") == "volume":
                self.active = None
            self.pending = cue
            self.lock.notify_all()
        logging.info("cue queued action=%s path=%s loop=%s token=%s bytes=%d",
                     cue.get("action"), cue.get("path"), cue.get("loop"),
                     cue.get("token"), len(cue.get("pcm") or b""))

    def stop(self, token: str | None = None, action: str | None = None) -> None:
        with self.lock:
            def matches(cue):
                if cue is None:
                    return False
                if token is not None:
                    # A token uniquely owns one cue.  The C client includes a
                    # default action=other on stop; it must not defeat an exact
                    # token match (that left alarm/timer loops running).
                    return cue.get("token") == token
                if action is not None and cue.get("action") != action:
                    return False
                return True
            if matches(self.pending):
                self.pending = None
            if matches(self.active):
                self.active = None
            self.lock.notify_all()
        logging.info("cue stop token=%s action=%s", token, action)

    def status(self) -> dict:
        with self.lock:
            active = self.active or {}
            pending = self.pending or {}
            return {
                "running": self.running,
                "stream_alive": bool(self.proc and self.proc.poll() is None),
                "active_action": active.get("action"),
                "active_token": active.get("token"),
                "pending_action": pending.get("action"),
                "restarts": self.restarts,
                "last_error": self.last_error,
                "stream_ready_at": self._stream_ready_at,
                "stream_latency": STREAM_LATENCY,
                "pipe_buffer_bytes": PIPE_BUFFER_BYTES,
                "last_cue_latency_ms": self._last_cue_latency_ms,
                "last_cue_action": self._last_cue_action,
                "last_cue_finished_at": self._last_cue_finished_at,
            }

    def _pw_env(self) -> dict:
        env = dict(os.environ)
        env.update({
            "XDG_RUNTIME_DIR": PW_RUNTIME,
            "PIPEWIRE_RUNTIME_DIR": PW_RUNTIME,
            "PULSE_SERVER": "unix:%s/pulse/native" % PW_RUNTIME,
            "PATH": "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",
        })
        return env

    def _warm_once(self) -> None:
        if not (Path(WARMUP).exists() and os.access(WARMUP, os.X_OK)):
            logging.warning("warmup helper missing: %s", WARMUP)
            return
        try:
            proc = subprocess.run([WARMUP], capture_output=True, timeout=25,
                                  env=self._pw_env(), stdin=subprocess.DEVNULL)
            if proc.returncode != 0:
                logging.warning("warmup rc=%d %s", proc.returncode,
                                (proc.stderr or b"")[-300:].decode("utf-8", "replace"))
            else:
                logging.info("audio path warmed once; persistent stream keeps it live")
        except (OSError, subprocess.SubprocessError) as exc:
            logging.warning("warmup failed: %s", exc)

    def _start_stream(self) -> bool:
        with self._start_lock:
            if not self.running:
                return False
            if self.proc and self.proc.poll() is None:
                return True
            if not Path(PW_CAT).exists():
                self.last_error = "pw-cat missing"
                return False
            # The sink can take a moment to appear during boot.  The old loop
            # retried every 10 ms and logged/spawned ~20 processes in a second.
            # A bounded exponential backoff keeps the first cue prompt once the
            # sink exists without turning a transient failure into a storm.
            now = time.monotonic()
            wait = self._last_start_attempt + self._start_backoff - now
            if wait > 0:
                self.last_error = "pw-cat restart backoff %.0f ms" % (wait * 1000)
                return False
            self._last_start_attempt = now
            argv = [PW_CAT, "--playback", "--raw", "--format", "s16",
                    "--rate", str(RATE), "--channels", str(CHANNELS),
                    "--latency", STREAM_LATENCY, "--volume", "1.0",
                    "-P", '{"node.suspend-on-idle":false,"session.suspend-timeout-seconds":0}', "-"]
            try:
                self.proc = subprocess.Popen(
                    argv, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL,
                    stderr=subprocess.PIPE, env=self._pw_env(), start_new_session=True,
                    bufsize=0,
                )
                # Let the pipe itself provide the real-time cushion.  pw-cat
                # drains it at exactly 48 kHz; a blocking write therefore paces
                # this thread without sleep() jitter and without a decoder or
                # audio-server restart.  Failure to resize is non-fatal (the
                # kernel default is larger, which only increases cue latency).
                pipe_bytes = None
                try:
                    pipe_bytes = fcntl.fcntl(self.proc.stdin.fileno(), fcntl.F_SETPIPE_SZ,
                                             max(4096, int(PIPE_BUFFER_BYTES)))
                except (OSError, ValueError, TypeError) as exc:
                    logging.warning("could not resize sound pipe: %s", exc)
                self.started_at = time.time()
                self._stream_ready_at = time.time()
                self._start_backoff = 0.0
                logging.info("persistent pw-cat stream started pid=%s latency=%s pipe_bytes=%s",
                             self.proc.pid, STREAM_LATENCY, pipe_bytes or "default")
                return True
            except OSError as exc:
                self.last_error = str(exc)
                self._start_backoff = min(2.0, max(0.5, self._start_backoff * 2 or 0.5))
                logging.error("pw-cat start failed (backoff %.1fs): %s", self._start_backoff, exc)
                return False

    def _restart_stream(self) -> None:
        self.restarts += 1
        try:
            if self.proc and self.proc.poll() is None:
                self.proc.terminate()
                try:
                    self.proc.wait(timeout=1)
                except subprocess.TimeoutExpired:
                    self.proc.kill()
        except OSError:
            pass
        self.proc = None
        if self.restarts > 1:
            self._start_backoff = min(2.0, max(0.5, self._start_backoff * 2))
        self._last_start_attempt = time.monotonic()
        self._start_stream()

    def _write(self, data: bytes) -> None:
        if not self.running:
            return
        if not self.proc or self.proc.poll() is not None:
            now = time.monotonic()
            if now - self._last_write_restart < 0.5:
                time.sleep(FRAME_MS / 1000.0)
                return
            self._last_write_restart = now
            self._start_backoff = min(2.0, max(0.5, self._start_backoff * 2 or 0.5))
            self._last_start_attempt = 0.0
            if not self._start_stream():
                time.sleep(FRAME_MS / 1000.0)
                return
        try:
            view = memoryview(data)
            fd = self.proc.stdin.fileno()
            while view:
                # This blocks when the bounded pipe is full.  pw-cat drains it
                # in real time, so the pipe is the clock.  Do not add sleep().
                n = os.write(fd, view)
                if n <= 0:
                    raise BrokenPipeError("pw-cat accepted no PCM")
                view = view[n:]
        except (BrokenPipeError, OSError) as exc:
            self.last_error = str(exc)
            logging.warning("pw-cat stream write failed: %s", exc)
            self._restart_stream()

    def _loop(self) -> None:
        self._warm_once()
        self._start_stream()
        silence = b"\x00" * FRAME_BYTES
        pos = 0
        while self.running:
            with self.lock:
                if self.pending is not None:
                    self.active = self.pending
                    self.pending = None
                    pos = 0
                    self._cue_requested_at = self.active.get("requested_monotonic") or time.monotonic()
                    self._cue_first_audio_at = None
                    self._last_cue_action = self.active.get("action")
                active = self.active
            chunk = silence
            if active is not None:
                pcm = active.get("pcm") or b""
                if pos >= len(pcm):
                    if active.get("loop"):
                        pos = 0
                    else:
                        with self.lock:
                            if self.active is active:
                                self.active = None
                        self._last_cue_finished_at = time.time()
                        active = None
                        pos = 0
                if active is not None:
                    chunk = pcm[pos:pos + FRAME_BYTES]
                    pos += FRAME_BYTES
                    if len(chunk) < FRAME_BYTES:
                        chunk += b"\x00" * (FRAME_BYTES - len(chunk))
                    if self._cue_first_audio_at is None and any(chunk):
                        self._cue_first_audio_at = time.monotonic()
                        if self._cue_requested_at:
                            self._last_cue_latency_ms = round(
                                (self._cue_first_audio_at - self._cue_requested_at) * 1000, 2)
            self._write(chunk)
            # No sleep here: _write blocks on the kernel pipe when pw-cat has a
            # full real-time cushion.  Sleeping as well would underrun.

    def shutdown(self) -> None:
        self.running = False
        with self.lock:
            self.active = None
            self.pending = None
            self.lock.notify_all()
        try:
            if self.proc and self.proc.poll() is None:
                if self.proc.stdin:
                    self.proc.stdin.close()
                self.proc.terminate()
                self.proc.wait(timeout=2)
        except (OSError, subprocess.SubprocessError):
            try:
                if self.proc:
                    self.proc.kill()
            except OSError:
                pass


class SoundManager:
    def __init__(self) -> None:
        self.player = SoundPlayer()
        self.cache: dict[str, tuple[float, int, bytes]] = {}
        self.cache_lock = threading.Lock()
        self.assignments = {}
        self.assign_mtime = 0.0
        self.sounds: list[dict] = []
        self.sounds_mtime = 0.0
        self.last_scan = 0.0
        self.scan_lock = threading.Lock()
        # Metadata probes fork ffprobe.  Cache by (path, mtime, size) so a
        # library of dozens of supplied sounds is not re-probed every time a
        # Settings page reads state or the daemon restarts.  The cache is
        # plain metadata; no user audio or personal content is copied.
        self.probe_cache: dict[str, tuple[float, int, dict]] = self._load_probe_cache()
        self.load_assignments()
        # Do not block daemon startup on 70+ ffprobe forks.  The socket is the
        # latency-critical interface; a background scan fills the library while
        # the first ordinary state request can still use cached metadata.
        self.prewarm_state = {"complete": False, "started": time.time(), "items": {}}
        threading.Thread(target=self.prewarm, name="nuxel-sound-prewarm", daemon=True).start()

    # ---- library ---------------------------------------------------------
    def prewarm(self) -> None:
        """Decode assigned cues once so the first hardware-key cue is warm.

        The persistent pw-cat stream removes server/route startup.  This pass
        removes the remaining first-use ffmpeg decode cost from the volume path
        and reports exactly which assignments could not be decoded.
        """
        items = {}
        for action in ACTIONS:
            source = self.sound_for(action)
            if source is None:
                items[action] = {"ok": False, "error": "no file assigned"}
                continue
            try:
                pcm = self.cached_pcm(source, self.gain_for(action))
                items[action] = {"ok": True, "path": str(source), "bytes": len(pcm)}
            except RuntimeError as exc:
                items[action] = {"ok": False, "path": str(source), "error": str(exc)}
        self.prewarm_state = {"complete": True, "finished": time.time(), "items": items}
        logging.info("sound prewarm complete: %s",
                     ", ".join("%s=%s" % (k, "ok" if v.get("ok") else "failed")
                               for k, v in sorted(items.items())))
    def library_roots(self) -> list[Path]:
        return [USER_DIR, SHARED_DIR]

    def _load_probe_cache(self) -> dict[str, tuple[float, int, dict]]:
        out: dict[str, tuple[float, int, dict]] = {}
        try:
            doc = json.loads(PROBE_CACHE_FILE.read_text())
            rows = doc.get("files") if isinstance(doc, dict) else None
            if not isinstance(rows, dict):
                return out
            for path, row in rows.items():
                if not isinstance(row, dict):
                    continue
                mtime = float(row.get("mtime"))
                size = int(row.get("size"))
                info = row.get("info")
                if isinstance(info, dict) and info.get("valid"):
                    out[str(path)] = (mtime, size, info)
        except (OSError, ValueError, TypeError):
            pass
        return out

    def _save_probe_cache(self) -> None:
        rows = {}
        for path, (mtime, size, info) in self.probe_cache.items():
            rows[path] = {"mtime": mtime, "size": size, "info": info}
        try:
            _atomic_json(PROBE_CACHE_FILE, {"schema_version": 1, "files": rows})
        except OSError as exc:
            logging.warning("could not save sound metadata cache: %s", exc)

    def scan(self, force: bool = False) -> list[dict]:
        now = time.time()
        if not force and now - self.last_scan < 1.5 and self.sounds:
            return self.sounds
        with self.scan_lock:
            candidates: list[tuple[Path, os.stat_result]] = []
            seen = set()
            for root in self.library_roots():
                try:
                    entries = sorted(root.iterdir(), key=lambda p: p.name.lower())
                except OSError:
                    continue
                for path in entries:
                    if path.name.startswith("."):
                        continue
                    if not path.is_file() or path.is_symlink():
                        continue
                    if path.suffix.lower() not in ALLOWED_EXT:
                        continue
                    real = str(path.resolve())
                    if real in seen:
                        continue
                    seen.add(real)
                    try:
                        candidates.append((path, path.stat()))
                    except OSError:
                        continue

            # User library wins over the identical shared copy.  Deduplicate
            # before probing so the shipped collection is not passed to
            # ffprobe twice (the two directories are both intentional).
            unique_candidates = []
            seen_pairs = set()
            for path, st in candidates:
                pair = (path.name, st.st_size)
                if pair in seen_pairs:
                    continue
                seen_pairs.add(pair)
                unique_candidates.append((path, st))
            candidates = unique_candidates

            cache_hits = 0
            pending = []
            results: dict[str, dict] = {}
            for path, st in candidates:
                key = str(path)
                hit = self.probe_cache.get(key)
                if hit and hit[0] == st.st_mtime and hit[1] == st.st_size:
                    results[key] = dict(hit[2])
                    cache_hits += 1
                else:
                    pending.append((path, st))

            def _probe(item):
                path, st = item
                info = probe(path)
                return path, st, info

            if pending:
                workers = max(1, min(8, len(pending)))
                with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
                    for path, st, info in pool.map(_probe, pending):
                        key = str(path)
                        if info.get("valid"):
                            self.probe_cache[key] = (st.st_mtime, st.st_size, dict(info))
                        results[key] = info

            found = []
            seen_names = set()
            for path, _st in candidates:
                info = results.get(str(path))
                if not info:
                    continue
                if not info.get("valid"):
                    logging.warning("ignoring invalid sound %s: %s", path, info.get("error"))
                    continue
                info = dict(info)
                # The supplied library is installed both in ~/Sounds and
                # the shared directory.  Prefer the user copy and do not
                # list the identical shared duplicate twice.
                dup = (path.name, info.get("size"))
                if dup[1] and dup in seen_names:
                    continue
                seen_names.add(dup)
                info["id"] = str(path.resolve())
                found.append(info)

            live = set()
            for root in self.library_roots():
                try:
                    live.update(str(p) for p in root.iterdir() if p.is_file() and not p.is_symlink())
                except OSError:
                    pass
            stale = set(self.probe_cache) - live
            for item in stale:
                self.probe_cache.pop(item, None)
            if pending or stale:
                self._save_probe_cache()
            self.sounds = found
            self.last_scan = now
            self.sounds_mtime = now
            logging.info("sound library scan: %d file(s), %d metadata probe(s), %d cached",
                         len(found), len(pending), cache_hits)
            return found

    def sound_for(self, action: str) -> Path | None:
        entry = (self.assignments.get(action) or {}).get("path")
        if entry:
            path = Path(entry)
            if path.is_file() and _safe_within(path, self.library_roots()):
                return path
        name = DEFAULT_FILES.get(action)
        for root in self.library_roots():
            if name:
                candidate = root / name
                if candidate.is_file():
                    return candidate
        # Last resort: first discovered compatible file.
        for info in self.sounds:
            p = Path(info["path"])
            if p.is_file():
                return p
        return None

    def gain_for(self, action: str) -> float:
        try:
            return max(0.0, min(1.0, float((self.assignments.get(action) or {}).get("gain", 1.0))))
        except (TypeError, ValueError):
            return 1.0

    def cached_pcm(self, path: Path, gain: float) -> bytes:
        key = str(path.resolve())
        try:
            st = path.stat()
        except OSError as exc:
            raise RuntimeError(str(exc))
        cache_key = (key, gain)
        with self.cache_lock:
            hit = self.cache.get(cache_key)
            if hit and hit[0] == st.st_mtime and hit[1] == st.st_size:
                return hit[2]
        pcm = decode_pcm(path, gain)
        with self.cache_lock:
            self.cache[cache_key] = (st.st_mtime, st.st_size, pcm)
            if len(self.cache) > 24:
                for old in list(self.cache)[:-24]:
                    self.cache.pop(old, None)
        return pcm

    # ---- assignments -----------------------------------------------------
    def default_assignments(self) -> dict:
        out = {}
        for action in ACTIONS:
            path = None
            name = DEFAULT_FILES.get(action)
            for root in self.library_roots():
                candidate = root / (name or "")
                if name and candidate.is_file():
                    path = str(candidate)
                    break
            out[action] = {"path": path, "gain": 1.0}
        return out

    def load_assignments(self) -> None:
        try:
            mtime = ASSIGN_FILE.stat().st_mtime
            doc = json.loads(ASSIGN_FILE.read_text())
            assigns = doc.get("assignments") if isinstance(doc, dict) else None
            if not isinstance(assigns, dict):
                raise ValueError("missing assignments")
            self.assignments = assigns
            self.assign_mtime = mtime
        except (OSError, ValueError, TypeError):
            self.assignments = self.default_assignments()
            self._save_assignments()

    def _save_assignments(self) -> None:
        doc = {"schema_version": 1, "actions": ACTIONS,
               "assignments": self.assignments, "updated": int(time.time())}
        _atomic_json(ASSIGN_FILE, doc)
        try:
            self.assign_mtime = ASSIGN_FILE.stat().st_mtime
        except OSError:
            self.assign_mtime = time.time()

    def maybe_reload(self) -> None:
        try:
            mtime = ASSIGN_FILE.stat().st_mtime
        except OSError:
            return
        if mtime != self.assign_mtime:
            self.load_assignments()

    def assign(self, action: str, path: str | None, gain: float | None = None) -> dict:
        if action not in ACTIONS:
            return {"success": False, "error": "unknown action %s" % action}
        p = Path(path) if path else None
        if p is not None:
            if not p.is_file() or not _safe_within(p, self.library_roots()):
                return {"success": False, "error": "path is not in a Nuxel sound library"}
            info = probe(p)
            if not info.get("valid"):
                return {"success": False, "error": "unsupported/undecodable sound",
                        "detail": info.get("error")}
        current = dict(self.assignments.get(action) or {})
        if p is not None:
            current["path"] = str(p.resolve())
        if gain is not None:
            current["gain"] = max(0.0, min(1.0, float(gain)))
        current.setdefault("gain", 1.0)
        self.assignments[action] = current
        self._save_assignments()
        return {"success": True, "action": action, "assignment": current}

    def state(self) -> dict:
        self.maybe_reload()
        return {
            "success": True,
            "actions": [{"id": a, "label": ACTION_LABELS[a]} for a in ACTIONS],
            "assignments": self.assignments,
            "sounds": self.scan(),
            "dirs": [str(p) for p in self.library_roots()],
            "player": self.player.status(),
            "prewarm": self.prewarm_state,
            "ffmpeg": Path(FFMPEG).exists(),
            "ffprobe": Path(FFPROBE).exists(),
        }

    def import_file(self, name: str, data_b64: str) -> dict:
        try:
            raw = base64.b64decode(data_b64, validate=True)
        except (ValueError, TypeError) as exc:
            return {"success": False, "error": "invalid base64: %s" % exc}
        if not raw:
            return {"success": False, "error": "empty file"}
        if len(raw) > MAX_IMPORT_BYTES:
            return {"success": False, "error": "file exceeds %d MiB" % (MAX_IMPORT_BYTES // 1048576)}
        safe = _sanitize_name(name)
        USER_DIR.mkdir(parents=True, exist_ok=True)
        stem, ext = os.path.splitext(safe)
        candidate = USER_DIR / safe
        n = 2
        while candidate.exists():
            candidate = USER_DIR / ("%s-%d%s" % (stem, n, ext))
            n += 1
        tmp = USER_DIR / (".%s.import-%d" % (safe, os.getpid()))
        try:
            with open(tmp, "wb") as fh:
                fh.write(raw)
                fh.flush()
                os.fsync(fh.fileno())
            os.chmod(tmp, 0o600)
            info = probe(tmp)
            if not info.get("valid"):
                return {"success": False, "error": "file is not a decodable audio format",
                        "detail": info.get("error")}
            os.replace(tmp, candidate)
            os.chmod(candidate, 0o644)
            try:
                import pwd
                pw = pwd.getpwnam("nuxel")
                os.chown(candidate, pw.pw_uid, pw.pw_gid)
            except (KeyError, OSError):
                pass
        finally:
            try:
                if tmp.exists():
                    tmp.unlink()
            except OSError:
                pass
        self.scan(force=True)
        result = probe(candidate)
        result["success"] = True
        result["id"] = str(candidate.resolve())
        return result

    def play_action(self, action: str, path: str | None = None,
                    loop: bool = False, token: str | None = None) -> dict:
        self.maybe_reload()
        if action not in ACTIONS:
            return {"success": False, "error": "unknown action"}
        source = Path(path) if path else self.sound_for(action)
        if source is None:
            return {"success": False, "error": "no sound assigned for %s" % action}
        if not source.is_file():
            return {"success": False, "error": "assigned file is missing", "path": str(source)}
        if not _safe_within(source, self.library_roots()):
            return {"success": False, "error": "assigned file is outside the sound library"}
        gain = self.gain_for(action)
        started = time.monotonic()
        try:
            pcm = self.cached_pcm(source, gain)
        except RuntimeError as exc:
            return {"success": False, "error": "decode failed", "detail": str(exc),
                    "path": str(source)}
        self.player.play({"action": action, "path": str(source), "pcm": pcm,
                          "loop": bool(loop), "token": token})
        return {"success": True, "queued": True, "action": action,
                "path": str(source), "bytes": len(pcm),
                "queue_ms": round((time.monotonic() - started) * 1000, 2),
                "player": self.player.status()}


MANAGER: SoundManager | None = None


def handle(req: dict) -> dict:
    global MANAGER
    if MANAGER is None:
        return {"success": False, "error": "daemon initializing"}
    cmd = str(req.get("cmd") or "").strip()
    if cmd in ("state", "status", "list"):
        return MANAGER.state()
    if cmd == "rescan":
        MANAGER.scan(force=True)
        return MANAGER.state()
    if cmd == "assign":
        return MANAGER.assign(str(req.get("action") or ""),
                              req.get("path"), req.get("gain"))
    if cmd == "preview":
        action = str(req.get("action") or "other")
        return MANAGER.play_action(action, req.get("path"), loop=False,
                                   token="preview-%d" % time.time())
    if cmd == "play":
        return MANAGER.play_action(str(req.get("action") or "other"),
                                   req.get("path"), bool(req.get("loop")),
                                   req.get("token"))
    if cmd == "stop":
        MANAGER.player.stop(req.get("token"), req.get("action"))
        return {"success": True, "stopped": True}
    if cmd == "import":
        return MANAGER.import_file(str(req.get("name") or "sound.mp3"),
                                   str(req.get("data_b64") or ""))
    if cmd == "ping":
        return {"success": True, "pong": True, "version": 1}
    return {"success": False, "error": "unknown command %s" % cmd}


def serve_connection(conn: socket.socket) -> None:
    try:
        conn.settimeout(10)
        buf = b""
        while b"\n" not in buf and len(buf) < 32 * 1024 * 1024:
            chunk = conn.recv(65536)
            if not chunk:
                break
            buf += chunk
        line = buf.split(b"\n", 1)[0]
        req = json.loads(line.decode("utf-8")) if line else {}
        resp = handle(req if isinstance(req, dict) else {})
        conn.sendall((json.dumps(resp, sort_keys=True) + "\n").encode("utf-8"))
    except Exception as exc:  # noqa: BLE001
        try:
            conn.sendall((json.dumps({"success": False, "error": str(exc)}) + "\n").encode())
        except OSError:
            pass
    finally:
        try:
            conn.close()
        except OSError:
            pass


def server_loop(sock: socket.socket) -> None:
    while True:
        try:
            conn, _ = sock.accept()
        except socket.timeout:
            continue
        except OSError:
            break
        threading.Thread(target=serve_connection, args=(conn,), daemon=True).start()


def main() -> int:
    global MANAGER
    USER_DIR.mkdir(parents=True, exist_ok=True)
    try:
        import pwd
        pw = pwd.getpwnam("nuxel")
        os.chown(USER_DIR, pw.pw_uid, pw.pw_gid)
        os.chmod(USER_DIR, 0o755)
    except (KeyError, OSError):
        pass
    MANAGER = SoundManager()
    MANAGER.player.start()
    threading.Thread(target=MANAGER.scan, name="nuxel-sound-scan", daemon=True).start()

    stop_event = threading.Event()

    def _stop(_signum, _frame):
        stop_event.set()
        MANAGER.player.shutdown()

    signal.signal(signal.SIGTERM, _stop)
    signal.signal(signal.SIGINT, _stop)
    signal.signal(signal.SIGHUP, _stop)

    try:
        if SOCKET_PATH.exists():
            SOCKET_PATH.unlink()
    except OSError:
        pass
    SOCKET_PATH.parent.mkdir(parents=True, exist_ok=True)
    sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    sock.bind(str(SOCKET_PATH))
    os.chmod(SOCKET_PATH, 0o660)
    sock.listen(16)
    sock.settimeout(1.0)
    logging.info("nuxel-soundd ready socket=%s dirs=%s", SOCKET_PATH,
                 [str(p) for p in MANAGER.library_roots()])
    thread = threading.Thread(target=server_loop, args=(sock,), daemon=True)
    thread.start()
    while not stop_event.is_set():
        time.sleep(1.0)
    try:
        sock.close()
        SOCKET_PATH.unlink()
    except OSError:
        pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
