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


def transcribe(registry, encoded):
    if not isinstance(encoded,str) or len(encoded)>427000:
        raise ValueError('Invalid audio payload')
    manifest, why=registry.ready_manifest('sonarbird',VARIANT)
    if manifest is None:
        raise ValueError('Install the optional Voice tiny.en package in Model library first')
    audio=base64.b64decode(encoded,validate=True)
    return recognize(Path(registry.package_dir(manifest))/'ggml-tiny.en.bin',audio)


def self_test(package):
    # Decoder load and bounded silent PCM inference; not a wake-phrase accuracy claim.
    buf=io.BytesIO()
    with wave.open(buf,'wb') as out:
        out.setnchannels(1);out.setsampwidth(2);out.setframerate(16000);out.writeframes(b'\0'*32000)
    recognize(Path(package)/'ggml-tiny.en.bin',buf.getvalue())
