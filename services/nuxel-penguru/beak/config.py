"""Canonical Beak settings for both PenGuru Squad and Nuxel Settings.

Never writes /etc or grants microphone access. All settings live in one
unprivileged state file. Continuous capture is opt-in and foreground-only.
"""
from __future__ import annotations
import json
import os
from pathlib import Path
import tempfile
import threading

from common import paths

DEFAULTS = {
    "version": 1,
    "asr_backend": "qwen",
    "vad_enabled": True,
    "interrupt_on_speech": True,
    "noise_suppression": "rnnoise",
    "talkback_enabled": True,
    "tts_backend": "piper",
    "config_owner": "penguru-beak",
    "continuous_listening_enabled": False,
    "push_to_talk_enabled": True,
    "wake_phrase": "Penguru",
}
ALLOWED = {
    "asr_backend": {"qwen", "whisper", "whistle"},
    "noise_suppression": {"rnnoise", "none"},
    "tts_backend": {"piper", "spark", "none"},
    "wake_phrase": {"Penguru"},
}
BOOLS = {"vad_enabled", "interrupt_on_speech", "talkback_enabled",
         "continuous_listening_enabled", "push_to_talk_enabled"}
PATH = Path(paths.STATE_DIR) / "beak.json"
_LOCK = threading.RLock()

def validate_change(change):
    if not isinstance(change, dict) or not change:
        raise ValueError("Expected a nonempty Beak settings object")
    unknown = set(change) - (set(ALLOWED) | BOOLS)
    if unknown:
        raise ValueError("Unknown/read-only Beak setting: " + ", ".join(sorted(unknown)))
    for key, value in change.items():
        if key in BOOLS and type(value) is not bool:
            raise ValueError(key + " must be boolean")
        if key in ALLOWED and (not isinstance(value, str) or value not in ALLOWED[key]):
            raise ValueError(key + " has unsupported value")
    return change

def load():
    cfg = dict(DEFAULTS)
    try:
        doc = json.loads(PATH.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return cfg
    if not isinstance(doc, dict) or doc.get("version") != 1 or doc.get("config_owner") != "penguru-beak":
        raise ValueError("Invalid Beak configuration identity or schema")
    editable = {k:v for k,v in doc.items() if k in ALLOWED or k in BOOLS}
    validate_change(editable) if editable else None
    cfg.update(editable)
    return cfg

def update(change):
    validate_change(change)
    with _LOCK:
        return _update_locked(change)

def _update_locked(change):
    cfg = load()
    cfg.update(change)
    PATH.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix=".beak-", dir=str(PATH.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as out:
            json.dump(cfg, out, indent=2, sort_keys=True)
            out.write("\n")
            out.flush()
            os.fsync(out.fileno())
        os.chmod(name, 0o600)
        os.replace(name, PATH)
    finally:
        if os.path.exists(name):
            os.unlink(name)
    return cfg

def capabilities():
    root = Path(paths.STATE_DIR) / "beak" / "approved"
    return {
        "qwen_asr": Path("/opt/nuxel-beak/bin/qwen3-asr-cli").is_file() and (root / "qwen3-asr-0.6b-q4_k_m.gguf").is_file(),
        "whisper_asr": Path("/opt/nuxel-speech/whisper-cli").is_file(),
        "whistle_asr": False,
        "rnnoise": False,
        "silero_vad": False,
        "piper_tts": Path("/opt/nuxel-beak/bin/piper").is_file() and (root / "piper-voice.onnx").is_file(),
        "spark_tts": False,
        "continuous_foreground_only": True,
    }
