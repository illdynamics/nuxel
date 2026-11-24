/**
 * PenGuru Squad — on-device engine.
 *
 * This module replaces the Nuxel HTTP bridge for ordinary Android phones. It
 * implements the same `call(op, params)` contract as the `penguru` RPC
 * namespace (status, model library, downloads, conversation, diagnostics), so
 * the PWA UI runs unchanged without a Nuxel host, URL, token or launcher.
 *
 * Heavy work (multi-gigabyte downloads, runtime archives, speech recognition)
 * is delegated to the small `window.NuxelAndroid` bridge exposed by
 * MainActivity. When that bridge is absent (desktop browser), model management
 * reports a clear error instead of pretending to work.
 */

const STORE_KEY = 'penguru-ondevice-state-v1';
const DOWNLOAD_HISTORY_KEY = 'penguru-ondevice-downloads-v1';

function android() {
  try {
    return (typeof window !== 'undefined' && window.NuxelAndroid) || null;
  } catch (error) {
    return null;
  }
}

function parseJson(text, fallback) {
  try {
    return JSON.parse(text);
  } catch (error) {
    return fallback;
  }
}

function hf(repo, revision, file) {
  return `https://huggingface.co/${repo}/resolve/${revision}/${file}`;
}

function bytes(value) {
  const n = Number(value) || 0;
  if (n >= 1e9) return (n / 1e9).toFixed(2) + ' GB';
  if (n >= 1e6) return (n / 1e6).toFixed(1) + ' MB';
  if (n >= 1e3) return (n / 1e3).toFixed(1) + ' KB';
  return n + ' B';
}

/* ------------------------------------------------------------------ catalog */

const CHATBIRD_REV = '084c0f4eee820a4e2052de264d3bb60de14555b7';
const CODEBIRD_REV = '391fc7d103e3942a408def3e4f51c2f85d464417';
const MINILM_REV = '1110a243fdf4706b3f48f1d95db1a4f5529b4d41';
const WHISPER_REV = '5359861c739e955e79d9a303bcbc70fb988958b1';
const SPARK_REV = '642071559bfc6346c2359d19dcb6be3f9dd8a05d';
const KOKORO_REV = 'f3ff3571791e39611d31c381e3a41a3af07b4987';
const SILERO_VAD_REV = 'bfa5f8cef40abb5de2bd4a2f4c3f22778172dfec';
const RNNOISE_REV = 'v0.2';

const MINILM_REPO = 'sentence-transformers/all-MiniLM-L6-v2';
const MINILM_FILES = [
  ['encoder.onnx', 23026053, '4278337fd0ff3c68bfb6291042cad8ab363e1d9fbc43dcb499fe91c871902474', 'onnx/model_qint8_arm64.onnx'],
  ['tokenizer.json', 466247, 'be50c3628f2bf5bb5e3a7f17b1f74611b2561a3a27eeab05e5aa30f411572037', 'tokenizer.json'],
  ['config.json', 612, '953f9c0d463486b10a6871cc2fd59f223b2c70184f49815e7efbcab5d8908b41', 'config.json'],
  ['tokenizer_config.json', 350, 'acb92769e8195aabd29b7b2137a9e6d6e25c476a4f15aa4355c233426c61576b', 'tokenizer_config.json'],
  ['pooling.json', 190, '4be450dde3b0273bb9787637cfbd28fe04a7ba6ab9d36ac48e92b11e350ffc23', '1_Pooling/config.json'],
  ['sentence_bert_config.json', 53, 'fc1993fde0a95c24ec6c022539d41cf6e2f7c9721e5415d6fb6897472a9cd4b7', 'sentence_bert_config.json'],
].map(([path, size, sha256, remote]) => ({
  path, size_bytes: size, sha256, url: hf(MINILM_REPO, MINILM_REV, remote),
}));

const SPARK_REPO = 'SparkAudio/Spark-TTS-0.5B';
const SPARK_FILES = [
  ['config.yaml', 169, '49a07abffcdfb5358e91eda83b1f4f8068f54b0a4e1ef1ef6ac22d9a312a7ae3'],
  ['BiCodec/config.yaml', 1164, '744f4093ae2381a2eb44ea8c4a5268a8d1e581498e9bf0808c034d1b076429be'],
  ['BiCodec/model.safetensors', 625518756, 'e9940cd48d4446e4340ced82d234bf5618350dd9f5db900ebe47a4fdb03867ec'],
  ['LLM/config.json', 658, 'a08401458b097cceb08bc40b26ec799b685ca44cebc7fa71c56721b6634e4ae8'],
  ['LLM/model.safetensors', 2026568968, '54825baf0a2f6076eb3c78fa1d22a95aee225f59070a8b295f8169db860eb109'],
  ['LLM/tokenizer.json', 14129172, '9c8b057d6ca205a429cc3428b9fc815f0d6ee1d53106dd5e5b129ef9db2ff057'],
  ['LLM/tokenizer_config.json', 2579652, 'd4b4dff03ac7e25aa2873a429b80bf255b27a1aec2e6a9879bbbed113dbb7cf8'],
  ['LLM/vocab.json', 2776833, 'ca10d7e9fb3ed18575dd1e277a2579c16d108e32f27439684afa0e10b1440910'],
  ['LLM/merges.txt', 1671853, '8831e4f1a044471340f7c0a83d7bd71306a5b867e95fd870f74d0c5308a904d5'],
  ['LLM/added_tokens.json', 508522, '3b2b3e1c3fd4e50a340e85e9b76c26ebc2bab0bf72f4c5bb88d085e3929930ac'],
  ['LLM/special_tokens_map.json', 613, '76862e765266b85aa9459767e33cbaf13970f327a0e88d1c65846c2ddd3a1ecd'],
  ['wav2vec2-large-xlsr-53/config.json', 1768, '48576e4a1b0f02c7770f57e236747169459db9a8b9a529bbd7a58bbbf52c45b5'],
  ['wav2vec2-large-xlsr-53/preprocessor_config.json', 212, 'a2254a5b58f72cd4de3632f8eee64f3f098b7c1402128d2f419e7d00ae13e335'],
  ['wav2vec2-large-xlsr-53/pytorch_model.bin', 1269737156, '314340227371a608f71adcd5f0de5933824fe77e55822aa4b24dba9c1c364dcb'],
].map(([path, size, sha256]) => ({path, size_bytes: size, sha256,
  url: hf(SPARK_REPO, SPARK_REV, path)}));

const KOKORO_REPO = 'hexgrad/Kokoro-82M';
const KOKORO_FILES = [
  ['config.json', 2351, '5abb01e2403b072bf03d04fde160443e209d7a0dad49a423be15196b9b43c17f'],
  ['kokoro-v1_0.pth', 327212226, '496dba118d1a58f5f3db2efc88dbdc216e0483fc89fe6e47ee1f2c53f18ad1e4'],
  ['voices/af_heart.pt', 523425, '0ab5709b8ffab19bfd849cd11d98f75b60af7733253ad0d67b12382a102cb4ff'],
  ['voices/am_michael.pt', 523435, '9a443b79a4b22489a5b0ab7c651a0bcd1a30bef675c28333f06971abbd47bd37'],
].map(([path, size, sha256]) => ({path, size_bytes: size, sha256,
  url: hf(KOKORO_REPO, KOKORO_REV, path)}));

const MODELS = [
  {
    model_id: 'silero-vad',
    name: 'Silero VAD · ONNX voice activity',
    role: 'voice_activity',
    variants: [{
      variant_id: 'silero-vad-onnx',
      format: 'ONNX',
      quantization: 'FP32 · VAD',
      architecture: 'silero-vad',
      size_bytes: 2204103,
      engine: 'onnxruntime',
      source_repo: 'snakers4/silero-vad',
      source_revision: SILERO_VAD_REV,
      // The ONNX asset lives under src/silero_vad/data/, not src/. The old
      // path returned HTTP 404 for every install attempt.
      source_url: 'https://raw.githubusercontent.com/snakers4/silero-vad/'
        + SILERO_VAD_REV + '/src/silero_vad/data/silero_vad.onnx',
      files: [{
        path: 'silero_vad.onnx',
        size_bytes: 2204103,
        sha256: 'f6f4407b41e05e277e7f5cfd9b9ae957b1dfe763c6076a934734c0b448e09b31',
      }],
      license: {
        spdx: 'MIT',
        notice: 'Silero VAD is MIT-licensed. This pinned ONNX file is optional; PenGuru uses adaptive RMS endpointing immediately and can use the ONNX model when an ONNX runtime is installed.',
      },
      download_allowed: true,
      download_reason: 'Pinned upstream Silero VAD ONNX file from the recorded revision.',
      detail: 'Optional neural voice-activity model for the ONNX runtime. Adaptive endpointing already works without it.',
    }],
  },
  {
    model_id: 'rnnoise',
    name: 'RNNoise · noise suppression',
    role: 'noise_suppression',
    variants: [{
      variant_id: 'rnnoise-0.2',
      format: 'SOURCE_TARBALL',
      quantization: 'v0.2',
      architecture: 'rnnoise',
      size_bytes: 2294308,
      engine: 'rnnoise',
      source_repo: 'xiph/rnnoise',
      source_revision: RNNOISE_REV,
      source_url: 'https://github.com/xiph/rnnoise/releases/download/v0.2/rnnoise-0.2.tar.gz',
      files: [{
        path: 'rnnoise-0.2.tar.gz',
        size_bytes: 2294308,
        sha256: '90fce4b00b9ff24c08dbfe31b82ffd43bae383d85c5535676d28b0a2b11c0d37',
      }],
      license: {
        spdx: 'BSD-3-Clause',
        notice: 'RNNoise is BSD-3-Clause. Separately compiled native runtime required; Android NoiseSuppressor is used automatically in the APK.',
      },
      download_allowed: true,
      download_reason: 'Pinned upstream RNNoise 0.2 source release.',
      detail: 'Optional RNNoise source/package for a future JNI noise-suppression runtime. Android NoiseSuppressor already runs automatically.',
    }],
  },
  {
    model_id: 'chatbird',
    name: 'ChatBird',
    role: 'chat',
    variants: [{
      variant_id: 'gguf-q4km',
      format: 'GGUF',
      quantization: 'Q4_K_M',
      architecture: 'llama',
      size_bytes: 2778282752,
      engine: 'llama.cpp',
      source_repo: 'SicariusSicariiStuff/Impish_LLAMA_4B_Abliterated_GGUF',
      source_revision: CHATBIRD_REV,
      source_url: hf('SicariusSicariiStuff/Impish_LLAMA_4B_Abliterated_GGUF', CHATBIRD_REV, 'Impish_LLAMA_4B_Abliterated-Q4_K_M.gguf'),
      files: [{
        path: 'Impish_LLAMA_4B_Abliterated-Q4_K_M.gguf',
        size_bytes: 2778282752,
        sha256: '8827d0e2850e47cb78fe13bdb583618be9c07dab1f20149c0918e5c399a3733c',
      }],
      license: {
        spdx: 'Apache-2.0',
        notice: 'GGUF repository metadata tags Apache-2.0, but the fine-tune card declares llama3.1 and the NVIDIA base model uses the NVIDIA Open Model License. Redistribution is blocked pending provenance review.',
      },
      download_allowed: true,
      download_reason: 'Direct upstream download from the pinned Hugging Face revision.',
      detail: 'Chat assistant package. Download to this phone, then install a compatible llama.cpp runtime.',
    }],
  },
  {
    model_id: 'codebird',
    name: 'CodeBird',
    role: 'code',
    variants: [{
      variant_id: 'gguf-q4km',
      format: 'GGUF',
      quantization: 'Q4_K_M',
      architecture: 'qwen35',
      size_bytes: 2783446304,
      engine: 'llama.cpp',
      source_repo: 'empero-ai/Qwen3.8-4B-Distill-GGUF',
      source_revision: CODEBIRD_REV,
      source_url: hf('empero-ai/Qwen3.8-4B-Distill-GGUF', CODEBIRD_REV, 'Qwen3.8-4B-Q4_K_M.gguf'),
      files: [{
        path: 'Qwen3.8-4B-Q4_K_M.gguf',
        size_bytes: 2783446304,
        sha256: 'dec96e8cf2e11b613bb46513dec485377f9ca5a351e71712ee0e244f287c6790',
      }],
      license: {
        spdx: 'Apache-2.0',
        notice: 'GGUF repository tags Apache-2.0; derived from empero-ai/Qwen3.8-4B-Distill (Apache-2.0). Preserve upstream model and source notices.',
      },
      download_allowed: true,
      download_reason: 'Direct upstream download from the pinned Hugging Face revision.',
      detail: 'Coding assistant package. Download to this phone, then install a compatible llama.cpp runtime.',
    }],
  },
  {
    model_id: 'sonarbird',
    name: 'SonarBird · MiniLM-L6',
    role: 'routing',
    variants: [{
      variant_id: 'onnx-int8-arm64',
      format: 'ONNX_CLASSIFIER',
      quantization: 'INT8 ARM64',
      architecture: 'bert',
      size_bytes: MINILM_FILES.reduce((sum, file) => sum + file.size_bytes, 0),
      engine: 'onnxruntime',
      source_repo: MINILM_REPO,
      source_revision: MINILM_REV,
      source_url: hf(MINILM_REPO, MINILM_REV, 'onnx/model_qint8_arm64.onnx'),
      files: MINILM_FILES,
      license: {
        spdx: 'Apache-2.0',
        notice: 'MiniLM encoder and tokenizer: sentence-transformers/all-MiniLM-L6-v2, Apache-2.0. Routing in this standalone build uses built-in language rules.',
      },
      download_allowed: true,
      download_reason: 'Upstream encoder files from the pinned Hugging Face revision.',
      detail: 'Local text-routing encoder. The standalone build routes with built-in rules while the encoder is optional.',
    }],
  },
  {
    model_id: 'sonarbird',
    name: 'Whisper · tiny.en speech recognition (SonarBird Voice)',
    role: 'speech_recognition',
    variants: [{
      variant_id: 'speech-whisper-tiny-en',
      format: 'WHISPER',
      quantization: 'FP16 · Voice tiny.en (optional)',
      architecture: 'whisper',
      size_bytes: 77704715,
      engine: 'whisper.cpp',
      source_repo: 'ggerganov/whisper.cpp',
      source_revision: WHISPER_REV,
      source_url: hf('ggerganov/whisper.cpp', WHISPER_REV, 'ggml-tiny.en.bin'),
      files: [{
        path: 'ggml-tiny.en.bin',
        size_bytes: 77704715,
        sha256: '921e4cf8686fdd993dcd081a5da5b6c365bfde1162e72b08d75ac75289920b1f',
      }],
      license: {
        spdx: 'MIT',
        notice: 'Optional local English speech model. Android speech recognition is used by default and needs no download.',
      },
      download_allowed: true,
      download_reason: 'Upstream Whisper tiny.en model, pinned revision.',
      detail: 'Whisper tiny.en is used by the bundled on-device speech engine. Android speech recognition remains the fast primary path; Whisper takes over when no recognizer is installed or it keeps hearing nothing.',
    }],
  },
  {
    model_id: 'spark-tts',
    name: 'Spark-TTS · 0.5B talkback voice',
    role: 'talkback_voice',
    variants: [{
      variant_id: 'spark-tts-0.5b',
      format: 'TTS_TORCH',
      quantization: 'FP32 · BiCodec + LLM + wav2vec2',
      architecture: 'spark-tts',
      size_bytes: SPARK_FILES.reduce((sum, file) => sum + file.size_bytes, 0),
      engine: 'spark-tts',
      source_repo: SPARK_REPO,
      source_revision: SPARK_REV,
      source_url: hf(SPARK_REPO, SPARK_REV, 'LLM/model.safetensors'),
      files: SPARK_FILES,
      license: {
        spdx: 'CC-BY-NC-SA-4.0',
        notice: 'SparkAudio/Spark-TTS-0.5B is licensed CC-BY-NC-SA-4.0 (non-commercial, share-alike). Review the upstream card before use. PenGuru downloads the pinned upstream files directly; the APK does not bundle them.',
      },
      download_allowed: true,
      download_reason: 'Pinned upstream Spark-TTS download for the neural talkback runtime.',
      detail: 'Neural talkback voice package. Android TextToSpeech is active immediately; these files are staged for the on-device Spark-TTS runtime.',
    }],
  },
  {
    model_id: 'kokoro-tts',
    name: 'Kokoro · 82M talkback voice',
    role: 'talkback_voice',
    variants: [{
      variant_id: 'kokoro-82m',
      format: 'TTS_TORCH',
      quantization: 'FP32 · 82M + voice embeddings',
      architecture: 'kokoro',
      size_bytes: KOKORO_FILES.reduce((sum, file) => sum + file.size_bytes, 0),
      engine: 'kokoro-tts',
      source_repo: KOKORO_REPO,
      source_revision: KOKORO_REV,
      source_url: hf(KOKORO_REPO, KOKORO_REV, 'kokoro-v1_0.pth'),
      files: KOKORO_FILES,
      license: {
        spdx: 'Apache-2.0',
        notice: 'hexgrad/Kokoro-82M is Apache-2.0. Voice embeddings are pinned by revision and SHA-256.',
      },
      download_allowed: true,
      download_reason: 'Pinned upstream Kokoro-82M download for the neural talkback runtime.',
      detail: 'Lightweight neural talkback voice package. Android TextToSpeech is active immediately; these files are staged for the on-device Kokoro runtime.',
    }],
  },
];

const RUNTIMES = [
  {
    id: 'whisper.cpp',
    name: 'Whisper.cpp · on-device speech engine',
    detail: 'Bundled arm64-v8a + x86_64 whisper-cli v1.9.6 speech engine. Download the Whisper tiny.en model in the Model library; no separate runtime download is needed.',
    bundled: true,
    version: 'v1.9.6',
    url: '',
    filename: '',
    size_bytes: 4665944,
    sha256: '',
    extract: null,
  },
  {
    id: 'llama.cpp',
    name: 'llama.cpp for Android arm64',
    detail: 'Official b12675 Android arm64 build (llama-cli, llama-server and shared libraries).',
    url: 'https://github.com/ggml-org/llama.cpp/releases/download/b12675/llama-b12675-bin-android-arm64.tar.gz',
    filename: 'llama-b12675-bin-android-arm64.tar.gz',
    size_bytes: 82520261,
    sha256: 'fbe76190d82f02e1c2f3d4b2f1a03c9663d7c968e165f7e6eb07ad3092258f6c',
    extract: 'tar.gz',
  },
  {
    id: 'llama.cpp-snapdragon',
    name: 'llama.cpp Snapdragon / Adreno (OpenCL)',
    detail: 'Official b12675 Android arm64 build with the Snapdragon OpenCL CPU backend.',
    url: 'https://github.com/ggml-org/llama.cpp/releases/download/b12675/llama-b12675-bin-android-arm64-snapdragon.tar.gz',
    filename: 'llama-b12675-bin-android-arm64-snapdragon.tar.gz',
    size_bytes: 68598141,
    sha256: 'bdd94b3106a73dd538ec7e6e2389f5a3c8a9e2c5b0f25a2845d7af399b477ede',
    extract: 'tar.gz',
  },
  {
    id: 'onnxruntime',
    name: 'ONNX Runtime for Android (AAR)',
    detail: 'Microsoft ONNX Runtime 1.20.0 Android archive, including the arm64-v8a native library.',
    url: 'https://repo1.maven.org/maven2/com/microsoft/onnxruntime/onnxruntime-android/1.20.0/onnxruntime-android-1.20.0.aar',
    filename: 'onnxruntime-android-1.20.0.aar',
    size_bytes: 27867924,
    sha256: '07a8f71ef890afed8c6087a56220e6d558a492804276ee2dd7cb7f6262242027',
    extract: 'zip',
  },
];

/* -------------------------------------------------------------------- state */

function defaultState() {
  return {
    enabled: true,
    mode: 'squad',
    runtimePreference: 'auto',
    perModel: {},
    requests: {},
    installed: {},
  };
}

function loadState() {
  try {
    const raw = localStorage.getItem(STORE_KEY);
    const parsed = raw ? JSON.parse(raw) : null;
    return Object.assign(defaultState(), parsed || {});
  } catch (error) {
    return defaultState();
  }
}

function saveState(state) {
  try {
    localStorage.setItem(STORE_KEY, JSON.stringify(state));
  } catch (error) {
    /* storage unavailable: keep the in-memory state */
  }
}

/* ------------------------------------------------------------------ helpers */

function choice(list) {
  return list[Math.floor(Math.random() * list.length)];
}

function firstLine(text, max) {
  const clean = String(text || '').replace(/\s+/g, ' ').trim();
  return clean.length > max ? clean.slice(0, max - 1) + '…' : clean;
}

// PenGuru's identity is part of the engine itself, not only the page copy.
// The host-side system prompt carries the same facts in optional Nuxel mode.
export const PENGURU_IDENTITY = 'I am PenGuru, a virtual penguin and the most '
  + 'advanced AI subsystem of NUXAI. NUXAI was originally designed for Nuxel, '
  + 'and now I also run on Android.';

export function identityReply() {
  return PENGURU_IDENTITY + '\n\n'
    + 'I can chat, outline code, check this phone\'s status and keep the '
    + 'conversation on-device. What would you like to do?';
}

function identityQuestion(text) {
  const value = String(text || '').toLowerCase();
  return /\b(who are you|what are you|what(?:'s| is) your name|your name|introduce yourself|tell me about yourself)\b/.test(value)
    || /\b(who is penguru|what is penguru|what(?:'s| is) penguru|who is pengu ru)\b/.test(value)
    || /\b(nuxai|nux ai)\b/.test(value);
}

function routeFor(text, mode) {
  if (mode === 'chatbird') return 'CHAT';
  if (mode === 'codebird') return 'CODE';
  const value = String(text || '').toLowerCase();
  if (/\b(code|function|method|class|bug|error|exception|stack trace|python|javascript|typescript|java|kotlin|rust|golang|sql|regex|compile|refactor|api|json)\b/.test(value)) {
    return 'CODE';
  }
  if (/\b(battery|storage|disk|free space|device|android|microphone|mic|cpu|memory|ram|model|download|install|diagnostic|folder|path)\b/.test(value)) {
    return 'SYSTEM';
  }
  if (/\?\s*$/.test(value) || /^(how|what|why|when|where|who|which|can|does|do|is|are|should)\b/.test(value)) {
    return 'ASK';
  }
  return 'CHAT';
}

function reasonFor(route) {
  if (route === 'CODE') return { code: 'R_ONDEVICE_CODE', confidence: 0.82 };
  if (route === 'SYSTEM') return { code: 'R_ONDEVICE_SYSTEM', confidence: 0.78 };
  if (route === 'ASK') return { code: 'R_ONDEVICE_ASK', confidence: 0.7 };
  return { code: 'R_ONDEVICE_CHAT', confidence: 0.72 };
}

function deviceInfo() {
  const host = android();
  if (!host || typeof host.deviceInfo !== 'function') return {};
  return parseJson(host.deviceInfo(), {});
}

function formatDevice() {
  const info = deviceInfo();
  const lines = [
    'On-device diagnostics (read-only):',
    `• Device: ${info.manufacturer || 'Android'} ${info.model || ''}`.trim(),
    `• Android: ${info.release || '?'} (API ${info.sdk || '?'})`,
    `• CPU ABIs: ${info.abis || '?'}`,
    `• Battery: ${info.battery >= 0 ? info.battery + '%' + (info.charging ? ' · charging' : '') : 'unknown'}`,
    `• Free storage: ${bytes(info.free_storage)}`,
    `• Models: ${info.models_dir || 'unavailable'}`,
    `• Runtimes: ${info.runtimes_dir || 'unavailable'}`,
    `• Android speech: ${info.speech_available ? 'available' : 'unavailable'}`,
  ];
  return lines.join('\n');
}

function codeReply(text) {
  const value = String(text || '').toLowerCase();
  const header = 'CodeBird · on-device assistant\n';
  if (/\bsort\b/.test(value) && /\bpython\b/.test(value)) {
    return header + '\nA small, dependency-free Python example:\n\n' +
      'def quicksort(items):\n' +
      '    if len(items) <= 1:\n' +
      '        return items\n' +
      '    pivot = items[len(items) // 2]\n' +
      '    lower = [x for x in items if x < pivot]\n' +
      '    same = [x for x in items if x == pivot]\n' +
      '    higher = [x for x in items if x > pivot]\n' +
      '    return quicksort(lower) + same + quicksort(higher)\n\n' +
      'print(quicksort([5, 2, 9, 1]))\n';
  }
  if (/\b(fetch|http|api|request)\b/.test(value) && /\b(javascript|typescript|js|node)\b/.test(value)) {
    return header + '\nA minimal fetch example with error handling:\n\n' +
      'async function getJson(url) {\n' +
      '  const response = await fetch(url, { headers: { Accept: "application/json" } });\n' +
      '  if (!response.ok) throw new Error(`HTTP ${response.status}`);\n' +
      '  return response.json();\n' +
      '}\n\n' +
      'getJson("https://example.com/api").then(console.log).catch(console.error);\n';
  }
  return header + '\nRequest: ' + firstLine(text, 300) + '\n\n' +
    'A practical outline:\n' +
    '1. State the input, the expected output and the failure cases.\n' +
    '2. Keep the smallest reproduction alongside the fix so the behaviour is testable.\n' +
    '3. Add one automated check for the bug you are fixing, then re-run it after each change.\n\n' +
    'Paste the relevant code or error text and I will turn this into a more specific patch outline.';
}

function chatReply(text) {
  const value = String(text || '').toLowerCase();
  if (/^(hi|hello|hey|yo|good morning|good evening)\b/.test(value)) {
    return 'Hi. ' + PENGURU_IDENTITY + '\n\n' +
      'I can report device status, outline code, help route a request, and keep the conversation local. ' +
      'No Nuxel server, API URL or token is involved. Use the Model library to download models and Settings → On-device dependencies to stage runtimes.';
  }
  if (/\b(what can you do|help|capabilit|feature)/.test(value)) {
    return 'This standalone build works without a Nuxel host:\n\n' +
      '• Conversation: local routing plus a built-in responder.\n' +
      '• Model library: download verified model files from Hugging Face to this phone.\n' +
      '• Dependencies: install llama.cpp and ONNX Runtime archives into app storage.\n' +
      '• Voice: Android speech recognition, foreground only, transcript reviewed before sending.\n' +
      '• Diagnostics: read-only device and storage status.\n\n' +
      'Full neural generation needs a native model runtime loaded by the app; the download/install controls are ready for that.';
  }
  const time = /\b(time|date|today)\b/.test(value);
  if (time) {
    return 'On this phone it is ' + new Date().toLocaleString() + '.';
  }
  return 'PenGuru · on-device\n\nI received: "' + firstLine(text, 300) + '"\n\n' +
    'I am PenGuru, the NUXAI penguin running on this phone. This standalone build keeps the ' +
    'conversation on the handset and answers with local logic. Ask about device status, request ' +
    'a code outline, or use the voice button. For full neural answers, download a model and ' +
    'install a runtime in Settings.';
}

function askReply(text) {
  return 'I am PenGuru, and I can help. I need one detail first.\n\n' +
    'You asked: "' + firstLine(text, 300) + '"\n\n' +
    'Which outcome do you want — a short explanation, a code example, or a device/storage check?';
}

function replyFor(text, route) {
  if (identityQuestion(text)) return identityReply();
  if (route === 'SYSTEM') return formatDevice();
  if (route === 'CODE') return codeReply(text);
  if (route === 'ASK') return askReply(text);
  return chatReply(text);
}

/* ------------------------------------------------------------ engine object */

export function createLocalEngine() {
  const state = loadState();
  const pendingJobs = new Map();
  const confirmed = new Set(Object.keys(state.installed || {}).filter((key) => state.installed[key]));
  const host = android();
  let counter = 0;

  function nativeInstalled(kind, id, files = null) {
    const key = kind + ':' + id;
    // A download that just reached READY is trustworthy even before the
    // native installed.json round-trip is observed by the page.
    if (confirmed.has(key)) return true;
    if (!host || typeof host.isInstalled !== 'function') {
      return !!state.installed[key];
    }
    try {
      // Reinstall-safe detection: the native side verifies each expected file
      // and byte length, so packages downloaded before an APK reinstall are
      // reported as installed even when the WebView localStorage was reset.
      if (files && files.length && typeof host.isInstalledWithFiles === 'function') {
        const expected = files.map(file => ({
          path: file.path,
          size: file.size_bytes != null ? file.size_bytes : file.size,
        }));
        if (host.isInstalledWithFiles(kind, id, JSON.stringify(expected))) {
          confirmed.add(key);
          state.installed[key] = true;
          saveState(state);
          return true;
        }
      }
      return !!host.isInstalled(kind, id);
    } catch (error) {
      return !!state.installed[key];
    }
  }

  function markInstalled(kind, id, value) {
    const key = kind + ':' + id;
    if (value) confirmed.add(key); else confirmed.delete(key);
    state.installed[key] = !!value;
    saveState(state);
  }

  function cards() {
    return MODELS.map((model) => ({
      model_id: model.model_id,
      name: model.name,
      role: model.role,
      variants: model.variants.map((variant) => {
        const id = model.model_id + '/' + variant.variant_id;
        const ready = nativeInstalled('model', id, variant.files);
        return Object.assign({}, variant, {
          status: ready ? 'ready' : 'not_installed',
          detail: ready
            ? 'Downloaded and verified in ' + (paths().models || 'app storage') + '/' + id
            : variant.detail,
          installed_path: ready ? (paths().models || '') + '/' + id : null,
        });
      }),
    }));
  }

  function paths() {
    if (host && typeof host.storagePaths === 'function') {
      return parseJson(host.storagePaths(), {});
    }
    return { models: 'app storage/Models', runtimes: 'app storage/Runtimes' };
  }

  function runtimeCatalog() {
    return RUNTIMES.map((runtime) => {
      const installed = runtime.bundled ? true : nativeInstalled('runtime', runtime.id,
        [{path: runtime.filename, size: runtime.size_bytes}]);
      return Object.assign({}, runtime, {
        installed,
        status: installed ? 'ready' : 'not_installed',
        installed_path: runtime.bundled ? 'bundled in this APK'
          : installed ? (paths().runtimes || '') + '/' + runtime.id : null,
      });
    });
  }

  function status() {
    const modelCards = cards();
    const ready = [];
    for (const card of modelCards) {
      for (const variant of card.variants) {
        if (variant.status === 'ready') ready.push(card.model_id + '/' + variant.variant_id);
      }
    }
    const speech = !!(host && (typeof host.speechInputAvailable === 'function'
      ? host.speechInputAvailable()
      : typeof host.speechAvailable === 'function' && host.speechAvailable()));
    const whisper = !!(host && typeof host.whisperAvailable === 'function'
      && host.whisperAvailable());
    let wakeWord = false;
    let listening = false;
    if (host && typeof host.wakeServiceStatus === 'function') {
      try {
        const wake = parseJson(host.wakeServiceStatus(), {});
        wakeWord = !!wake.running;
        listening = !!wake.listening;
      } catch (error) { /* status is informational */ }
    }
    return {
      ok: true,
      status: {
        schema_version: 1,
        enabled: !!state.enabled,
        state: state.enabled ? (ready.length ? 'IDLE · local package ready' : 'IDLE · local') : 'DISABLED',
        mode: state.mode,
        runtime_preference: state.runtimePreference,
        per_model_engine: Object.assign({}, state.perModel),
        loaded_model: ready.length ? ready[0].split('/')[0] : null,
        loaded_variant: ready.length ? ready[0].split('/')[1] : null,
        engine: ready.length ? 'on-device · runtime staged' : 'on-device · built-in responder',
        provider: 'CPU',
        queue_depth: 0,
        models: modelCards,
        sonarbird: { available: true, mode: 'built-in language rules' },
        providers: { CPU: { status: 'baseline' }, 'GPU/NPU': { status: 'not validated on this device' } },
        network: { workers: 'not required', local_only: true },
        voice: { wake_word: wakeWord, foreground_speech: speech, listening: listening,
          vad: 'adaptive-rms', noise_suppression: 'system-native', whisper },
        whisper: { ready: whisper },
        storage: paths(),
      },
    };
  }

  function startRemoteJob(kind, id, files, extract) {
    if (!host || typeof host.startDownload !== 'function') {
      return { ok: false, error: 'android_bridge_required', detail: 'Downloads require the Android app.' };
    }
    const spec = JSON.stringify({ kind, id, files, extract: extract || null });
    let jobId = '';
    try {
      jobId = host.startDownload(spec) || '';
    } catch (error) {
      return { ok: false, error: 'download_start_failed', detail: String(error && error.message || error) };
    }
    if (!jobId) return { ok: false, error: 'download_start_failed' };
    pendingJobs.set(jobId, { kind, id });
    return { ok: true, job_id: jobId, state: 'downloading' };
  }

  function jobStatus(jobId, fallbackKind, fallbackId) {
    if (!host || typeof host.downloadStatus !== 'function') {
      return { ok: false, error: 'android_bridge_required' };
    }
    const raw = host.downloadStatus(jobId);
    const job = parseJson(raw, null);
    if (!job) return { ok: false, error: 'unknown_job' };
    const info = pendingJobs.get(jobId) || { kind: fallbackKind, id: fallbackId };
    if (job.state === 'ready') {
      markInstalled(info.kind, info.id, true);
      pendingJobs.delete(jobId);
    }
    return { ok: true, job: Object.assign({ job_id: jobId }, job) };
  }

  async function call(op, params) {
    params = params || {};
    if (op === 'status') return status();
    if (op === 'list_models') return { ok: true, models: cards() };
    if (op === 'set_enabled') {
      state.enabled = params.enabled !== false;
      saveState(state);
      return Object.assign({ ok: true, enabled: state.enabled }, status().status);
    }
    if (op === 'set_mode') {
      if (!['squad', 'chatbird', 'codebird'].includes(params.mode)) {
        return { ok: false, error: 'invalid_mode' };
      }
      state.mode = params.mode;
      saveState(state);
      return { ok: true, mode: state.mode };
    }
    if (op === 'set_runtime') {
      if (params.model_id) {
        state.perModel[params.model_id] = params.engine || 'inherit';
      } else {
        state.runtimePreference = params.preference || 'auto';
      }
      saveState(state);
      return { ok: true, runtime_preference: state.runtimePreference, per_model_engine: state.perModel };
    }
    if (op === 'start_download') {
      // Several cards can share a logical model_id (SonarBird routing and
      // SonarBird Voice). Match on model_id *and* variant_id so e.g. the
      // tiny.en speech package resolves to its own card instead of failing
      // with unknown_package against the MiniLM card.
      const card = MODELS.find((model) => model.model_id === params.model_id
        && model.variants.some((item) => item.variant_id === params.variant_id));
      const variant = card && card.variants.find((item) => item.variant_id === params.variant_id);
      if (!card || !variant) return { ok: false, error: 'unknown_package' };
      if (!params.license_accepted || params.license_revision !== variant.source_revision) {
        return { ok: false, error: 'license_ack_required', detail: 'Accept the exact revision notice first.' };
      }
      const files = variant.files.map((file) => ({
        url: file.url || variant.source_url,
        path: file.path,
        sha256: file.sha256,
        size: file.size_bytes,
      }));
      return startRemoteJob('model', card.model_id + '/' + variant.variant_id, files);
    }
    if (op === 'download_status') return jobStatus(String(params.job_id || ''));
    if (op === 'cancel_download') {
      const jobId = String(params.job_id || '');
      if (!host || typeof host.cancelDownload !== 'function') return { ok: false, error: 'android_bridge_required' };
      return { ok: !!host.cancelDownload(jobId), job_id: jobId };
    }
    if (op === 'delete_model') {
      const id = params.model_id + '/' + params.variant_id;
      if (!host || typeof host.deleteInstalled !== 'function') return { ok: false, error: 'android_bridge_required' };
      const deleted = !!host.deleteInstalled('model', id);
      if (deleted) markInstalled('model', id, false);
      return { ok: deleted, deleted: deleted ? id : null, error: deleted ? null : 'delete_failed' };
    }
    if (op === 'submit') {
      if (!state.enabled) return { ok: false, error: 'disabled', detail: 'Enable PenGuru first.' };
      if (!params.text || !String(params.text).trim()) return { ok: false, error: 'invalid_text' };
      const route = params.route_override || routeFor(params.text, state.mode);
      if (!['CHAT', 'CODE', 'ASK', 'SYSTEM'].includes(route)) return { ok: false, error: 'invalid_override' };
      const id = 'local-' + Date.now().toString(36) + '-' + (++counter).toString(36);
      const reason = reasonFor(route);
      const request = {
        request_id: id,
        status: 'generating',
        route,
        reason_code: reason.code,
        confidence: reason.confidence,
        worker: route === 'CODE' ? 'codebird' : route === 'CHAT' ? 'chatbird' : null,
        engine: 'on-device-rules',
        variant_id: 'builtin',
        revision: 'local',
        output: '',
      };
      state.requests[id] = request;
      saveState(state);
      setTimeout(() => {
        if (request.status === 'cancelled') return;
        request.status = 'done';
        request.output = replyFor(params.text, route);
        saveState(state);
      }, 320);
      return { ok: true, request_id: id, status: 'queued' };
    }
    if (op === 'get') {
      const request = state.requests[String(params.request_id || '')];
      if (!request) return { ok: false, error: 'not_owner' };
      return { ok: true, request };
    }
    if (op === 'cancel') {
      const request = state.requests[String(params.request_id || '')];
      if (request) request.status = 'cancelled';
      saveState(state);
      return { ok: true, cancelled: !!request };
    }
    if (op === 'clear_all') {
      const count = Object.keys(state.requests).length;
      state.requests = {};
      saveState(state);
      return { ok: true, deleted: count };
    }
    if (op === 'transcribe') {
      return { ok: false, error: 'use_android_speech', detail: 'Use the microphone button; Android speech recognition is built in.' };
    }
    if (op === 'diagnostics') {
      return {
        ok: true,
        status: status().status,
        device: deviceInfo(),
        paths: paths(),
        runtimes: runtimeCatalog(),
        speech: { available: !!(host && host.speechAvailable && host.speechAvailable()) },
        whisper: host && typeof host.whisperStatus === 'function'
          ? parseJson(host.whisperStatus(), { ready: false }) : { ready: false },
      };
    }
    if (op === 'install_runtime') {
      const runtime = RUNTIMES.find((item) => item.id === params.id);
      if (!runtime) return { ok: false, error: 'unknown_runtime' };
      if (runtime.bundled) {
        return { ok: true, bundled: true, runtime: runtimeCatalog().find((item) => item.id === runtime.id) };
      }
      return startRemoteJob('runtime', runtime.id, [{
        url: runtime.url,
        path: runtime.filename,
        sha256: runtime.sha256,
        size: runtime.size_bytes,
      }], runtime.extract);
    }
    if (op === 'runtime_status') {
      if (params.job_id) return jobStatus(String(params.job_id), 'runtime', params.id);
      const runtime = RUNTIMES.find((item) => item.id === params.id);
      if (!runtime) return { ok: false, error: 'unknown_runtime' };
      const installed = nativeInstalled('runtime', runtime.id,
        [{path: runtime.filename, size: runtime.size_bytes}]);
      return { ok: true, runtime: Object.assign({}, runtime, {
        installed,
        status: installed ? 'ready' : 'not_installed',
      }) };
    }
    if (op === 'paths') return { ok: true, paths: paths(), device: deviceInfo() };
    return { ok: false, error: 'unknown_op' };
  }

  return { call, runtimeCatalog, paths, status, cards };
}

export { RUNTIMES };
