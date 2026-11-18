"""Allowlisted sources for on-device download-to-STAGING, not runtime activation.

These links never point to expiring Xet CDN signatures supplied by a browser.
Any staged file requires trusted manifest, license and runtime acceptance
before being copied to approved/ and used as code/model input.
"""
CATALOG = (
  # This is intentionally the owner-required official endpoint. HF redirects
  # are checked as HTTPS by downloader.py; the observed SHA-256 is recorded in
  # the staging receipt and is never treated as signed provenance.
  {"id": "qwen-asr", "name": "Qwen3 ASR 0.6B INT4", "role": "Speech-to-text",
   "source": "OpenVoiceOS/qwen3-asr-0.6b-q4-k-m", "revision": "main",
   "filename": "qwen3-asr-0.6b-q4_k_m.gguf", "size_bytes": 685284096, "max_bytes": 900000000,
   "url": "https://huggingface.co/OpenVoiceOS/qwen3-asr-0.6b-q4-k-m/resolve/main/qwen3-asr-0.6b-q4_k_m.gguf?download=true",
   "source_verified": True, "download_allowed": True,
   "note": "Official source. Requires separately built and verified qwen3-asr-cli for Linux ARM64; NOT a llama.cpp text generation package."},
  {"id": "needle3", "name": "Needle3", "role": "Cactus voice model",
   "source": "Cactus-Compute/needle3", "revision": "afb64c7f069abd958aa9cadb2cee0b17ca6bf757",
   "filename": "needle3.cact", "size_bytes": 46393604, "max_bytes": 150000000, "source_verified": True, "download_allowed": True,
   "note": "Requires Cactus Compute Linux ARM64 runtime; does NOT replace MiniLM or the Supervisor."},
  {"id": "whistle", "name": "Whistle", "role": "Cactus voice model",
   "source": "Cactus-Compute/whistle", "revision": "557a18bb60b49497a0a3a0125d3bb65dda6200bf",
   "filename": "whistle.cact", "size_bytes": 16919407, "max_bytes": 150000000, "source_verified": True, "download_allowed": True,
   "note": "Requires a tested Cactus Linux ARM64 runtime. Not the selected Qwen ASR default."},
  {"id": "spark-tts", "name": "Spark TTS", "role": "Text-to-speech",
   "source": "mradermacher/spark-tts-tunartts-v1-GGUF", "revision": "46312d4291ba212220ddd45e26ab26c302231922",
   "filename": "spark-tts-tunartts-v1.Q4_K_M.gguf", "size_bytes": 411690816, "max_bytes": 650000000, "source_verified": True, "download_allowed": True,
   "note": "Pinned repository revision. Requires a tested audio tokenizer/codec and ARM64 decoder before activation."},
  # The following are deliberately visible but not installable until an exact
  # ABI, license and checksum manifest is accepted. A source link is not an
  # executable compatibility claim.
  {"id": "piper-tts", "name": "Piper TTS", "role": "Default speech output",
   "source": "rhasspy/piper", "revision": "SOURCE UNVERIFIED", "filename": "piper + voice.onnx + voice.onnx.json", "max_bytes": 0,
   "source_verified": False, "download_allowed": False, "url": "https://github.com/rhasspy/piper",
   "note": "SOURCE UNVERIFIED for this device: select a licensed Linux ARM64 release and compatible voice before automatic installation."},
  {"id": "silero-vad", "name": "Silero VAD", "role": "Voice activity detection",
   "source": "snakers4/silero-vad", "revision": "SOURCE UNVERIFIED", "filename": "silero_vad.onnx", "max_bytes": 0,
   "source_verified": False, "download_allowed": False, "url": "https://github.com/snakers4/silero-vad",
   "note": "SOURCE UNVERIFIED for the required ONNX model/version and license acceptance; RMS gating is not Silero VAD."},
  {"id": "rnnoise", "name": "RNNoise", "role": "Noise suppression",
   "source": "xiph/rnnoise", "revision": "SOURCE UNVERIFIED", "filename": "ARM64 library/runtime", "max_bytes": 0,
   "source_verified": False, "download_allowed": False, "url": "https://github.com/xiph/rnnoise",
   "note": "SOURCE UNVERIFIED for a compatible ARM64 build. Browser noise suppression is not RNNoise."},
  {"id": "cactus-runtime", "name": "Cactus runtime", "role": ".cact execution",
   "source": "Cactus-Compute", "revision": "SOURCE UNVERIFIED", "filename": "Linux ARM64 runtime", "max_bytes": 0,
   "source_verified": False, "download_allowed": False, "url": "https://huggingface.co/Cactus-Compute/needle3",
   "note": "SOURCE UNVERIFIED as a shared runtime package. Needle3/Whistle staging does not install or execute Cactus."},
  {"id": "qwen-asr-runtime", "name": "Qwen ASR runtime", "role": "GGUF ASR decoder",
   "source": "OpenVoiceOS/qwen3-asr-0.6b-q4-k-m", "revision": "SOURCE UNVERIFIED", "filename": "Linux ARM64 qwen3-asr-cli", "max_bytes": 0,
   "source_verified": False, "download_allowed": False, "url": "https://huggingface.co/OpenVoiceOS/qwen3-asr-0.6b-q4-k-m",
   "note": "SOURCE UNVERIFIED: the GGUF requires a Qwen-ASR-compatible ARM64 decoder; llama.cpp text inference is not a substitute."},
)

def listing():
    return [{**x, "url": x.get("url", "https://huggingface.co/{}/resolve/{}/{}".format(x["source"], x["revision"], x["filename"])),
             "status": "download_to_staging_only" if x.get("download_allowed") else "source_unverified",
             "runtime_ready": False} for x in CATALOG]
