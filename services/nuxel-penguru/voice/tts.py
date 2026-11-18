"""Local Piper talkback. Fail closed if runtime/voice is not provisioned."""
from __future__ import annotations
import base64
from pathlib import Path
import subprocess
import tempfile

PIPER = Path("/opt/nuxel-beak/bin/piper")
VOICE = Path("/var/lib/nuxel-penguru/beak/approved/piper-voice.onnx")


def synthesize(text, cfg):
    if not cfg.get("talkback_enabled"):
        raise ValueError("Talkback is disabled in Beak settings")
    if cfg.get("tts_backend") != "piper":
        raise ValueError("Spark TTS audio decoder is not validated; choose Piper after installing a voice")
    if not isinstance(text, str) or not text.strip() or len(text) > 600:
        raise ValueError("Talkback requires 1-600 characters")
    if not PIPER.is_file() or not VOICE.is_file():
        raise ValueError("Piper executable and approved voice .onnx are required; install and test both on ARM64")
    with tempfile.TemporaryDirectory(prefix="penguru-tts-") as tmp:
        dest = Path(tmp) / "out.wav"
        proc = subprocess.run([str(PIPER), "--model", str(VOICE), "--output_file", str(dest)],
                              input=text, text=True, stdout=subprocess.DEVNULL,
                              stderr=subprocess.PIPE, timeout=45)
        if proc.returncode != 0 or not dest.is_file():
            raise ValueError("Offline Piper synthesis failed")
        data = dest.read_bytes()
        # Bridge IPC has a 1MiB line limit. Never return an unbounded waveform.
        if not (44 <= len(data) <= 500000) or data[:4] != b"RIFF" or data[8:12] != b"WAVE":
            raise ValueError("Piper output exceeds local playback budget or is not WAV")
        return {"audio_base64": base64.b64encode(data).decode("ascii"),
                "mime": "audio/wav", "engine": "piper", "local_only": True}
