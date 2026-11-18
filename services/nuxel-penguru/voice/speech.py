"""Bounded local speech recognition. Audio is ephemeral and never authorizes actions."""
import base64
import io
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile
import threading
import wave

BINARY = '/opt/nuxel-speech/whisper-cli'
VARIANT = 'speech-whisper-tiny-en'
LOCK = threading.Lock()


def recognize(model, audio):
    if len(audio) > 320044:
        raise ValueError('Audio exceeds ten seconds')
    with wave.open(io.BytesIO(audio)) as stream:
        if stream.getnchannels()!=1 or stream.getsampwidth()!=2 or stream.getframerate()!=16000 or stream.getnframes()>160000:
            raise ValueError('Expected at most ten seconds of mono 16 kHz PCM16 WAV')
    if not LOCK.acquire(blocking=False):
        raise ValueError('Speech recognition is busy')
    try:
        with tempfile.TemporaryDirectory(prefix='penguru-speech-') as tmp:
            wav=Path(tmp)/'input.wav';wav.write_bytes(audio)
            output=Path(tmp)/'transcript'
            result=subprocess.run([BINARY,'-m',str(model),'-f',str(wav),'-l','en','-t','2',
                '-nt','-otxt','-of',str(output),'--no-gpu','--prompt','Penguru is the name of this assistant.'],
                stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE,timeout=45)
            if result.returncode:
                raise ValueError('Local speech decoder failed')
            text=output.with_suffix('.txt').read_text().strip()[:16000]
            match=re.search(r'\bpen\s*guru\b',text,re.I)
            return {'text':text,'wake_detected':bool(match),
                    'after_wake':text[match.end():].lstrip(' ,.!?:') if match else '',
                    'engine':'whisper.cpp','local_only':True}
    finally:
        LOCK.release()


def _validate_wav(audio):
    if len(audio) > 320044:
        raise ValueError("Audio exceeds ten seconds")
    with wave.open(io.BytesIO(audio)) as stream:
        if (stream.getnchannels() != 1 or stream.getsampwidth() != 2 or
                stream.getframerate() != 16000 or stream.getnframes() > 160000):
            raise ValueError("Expected mono 16 kHz PCM16 WAV, at most 10 seconds")


def recognize_qwen(audio):
    """Use a separately verified qwen3-asr.cpp ARM64 CLI. Never execute GGUF via text llama.cpp."""
    binary = Path("/opt/nuxel-beak/bin/qwen3-asr-cli")
    model = Path("/var/lib/nuxel-penguru/beak/approved/qwen3-asr-0.6b-q4_k_m.gguf")
    if not binary.is_file() or not model.is_file():
        raise ValueError("Qwen ASR runtime/model not installed. Stage model in Beak, then validate and provision qwen3-asr.cpp ARM64 runtime; alternatively select Whisper in Beak settings.")
    _validate_wav(audio)
    if not LOCK.acquire(blocking=False):
        raise ValueError("Speech recognition is busy")
    try:
        with tempfile.TemporaryDirectory(prefix="penguru-qwen-") as tmp:
            wav = Path(tmp) / "input.wav"
            output = Path(tmp) / "transcript.txt"
            wav.write_bytes(audio)
            # qwen3-asr.cpp CLI documents -m/-f/-o/-t; avoid shell, server or telemetry.
            result = subprocess.run([str(binary), "-m", str(model), "-f", str(wav),
                                     "-o", str(output), "-t", "2"],
                                    stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                                    stderr=subprocess.PIPE, timeout=90)
            if result.returncode or not output.is_file():
                raise ValueError("Qwen ASR failed; verify CLI/model format parity on S10+")
            raw = output.read_text(encoding="utf-8", errors="replace")[:16000].strip()
            # Upstream CLI may prepend a language identifier.
            raw = re.sub(r"^language\s+[A-Za-z-]+\s+", "", raw, flags=re.I)
            match = re.search(r"\bpen\s*guru\b", raw, re.I)
            return {"text": raw, "wake_detected": bool(match),
                    "after_wake": raw[match.end():].lstrip(" ,.!?:") if match else "",
                    "engine": "qwen3-asr.cpp", "local_only": True}
    finally:
        LOCK.release()


def transcribe(registry, encoded, config=None):
    if not isinstance(encoded, str) or len(encoded) > 427000:
        raise ValueError("Invalid audio payload")
    audio = base64.b64decode(encoded, validate=True)
    backend = (config or {}).get("asr_backend", "whisper")
    if backend == "qwen":
        return recognize_qwen(audio)
    if backend == "whistle":
        raise ValueError("Whistle requires a separately validated Cactus ARM64 adapter; staged .cact files cannot execute")
    if backend != "whisper":
        raise ValueError("Unsupported local speech backend")
    manifest, why = registry.ready_manifest("sonarbird", VARIANT)
    if manifest is None:
        raise ValueError("Install the approved Voice tiny.en package or choose Qwen ASR after ARM64 validation")
    _validate_wav(audio)
    return recognize(Path(registry.package_dir(manifest)) / "ggml-tiny.en.bin", audio)


def self_test(package):
    # Decoder load and bounded silent PCM inference; not a wake-phrase accuracy claim.
    buf=io.BytesIO()
    with wave.open(buf,'wb') as out:
        out.setnchannels(1);out.setsampwidth(2);out.setframerate(16000);out.writeframes(b'\0'*32000)
    recognize(Path(package)/'ggml-tiny.en.bin',buf.getvalue())
