// Spoken answers ("talkback") for PenGuru.
//
// The Android APK exposes a small TextToSpeech bridge (NuxelAndroid.tts*).
// That uses any installed Android talkback engine immediately. The pinned
// Spark-TTS / Kokoro packages in the Model library are staged for the future
// on-device neural voice runtime; they are not required for talkback to work.
//
// In a desktop browser the Web Speech API is used instead, so the same UI is
// useful outside the APK.

const KEY_ENABLED = 'penguru-talkback-enabled';
const KEY_RATE = 'penguru-talkback-rate';
const KEY_PITCH = 'penguru-talkback-pitch';
const KEY_ENGINE = 'penguru-talkback-engine';

function read(key, fallback) {
  try {
    const value = localStorage.getItem(key);
    return value == null ? fallback : value;
  } catch (error) {
    return fallback;
  }
}

function write(key, value) {
  try {
    if (value == null || value === '') localStorage.removeItem(key);
    else localStorage.setItem(key, String(value));
  } catch (error) {
    /* storage unavailable */
  }
}

function number(value, fallback) {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : fallback;
}

/** Turn an assistant answer into something worth hearing. Code fences are
 *  skipped instead of read character by character; long answers are trimmed. */
export function speakable(text) {
  let value = String(text == null ? '' : text);
  value = value.replace(/```[\s\S]*?```/g, ' Code block omitted. ');
  value = value.replace(/`([^`]*)`/g, '$1');
  value = value.replace(/!\[[^\]]*\]\([^)]*\)/g, ' ');
  value = value.replace(/\[([^\]]+)\]\([^)]*\)/g, '$1');
  value = value.replace(/https?:\/\/\S+/g, ' link ');
  value = value.replace(/[#*_>~|]/g, ' ');
  value = value.replace(/\s+/g, ' ').trim();
  if (!value) value = 'The response is on screen.';
  return value.length > 1800 ? value.slice(0, 1799) + '…' : value;
}

export function talkbackControls() {
  const host = typeof window !== 'undefined' ? window.NuxelAndroid : null;
  const native = !!(host && typeof host.ttsSpeak === 'function');
  const listeners = new Set();
  const state = {
    enabled: read(KEY_ENABLED, '0') === '1',
    rate: number(read(KEY_RATE, '1'), 1),
    pitch: number(read(KEY_PITCH, '1'), 1),
    engine: read(KEY_ENGINE, ''),
  };

  function notify() {
    for (const listener of listeners) {
      try { listener(state); } catch (error) { /* UI listener */ }
    }
  }

  function persist() {
    write(KEY_ENABLED, state.enabled ? '1' : '0');
    write(KEY_RATE, state.rate);
    write(KEY_PITCH, state.pitch);
    write(KEY_ENGINE, state.engine);
  }

  function configure() {
    if (!native || typeof host.ttsConfigure !== 'function') return false;
    try {
      return !!host.ttsConfigure(JSON.stringify({
        engine: state.engine,
        rate: state.rate,
        pitch: state.pitch,
      }));
    } catch (error) {
      return false;
    }
  }

  function speak(text) {
    if (!state.enabled) return false;
    const value = speakable(text);
    if (!value) return false;
    if (native) {
      configure();
      try { return !!host.ttsSpeak(value); } catch (error) { return false; }
    }
    try {
      if (typeof window !== 'undefined' && 'speechSynthesis' in window) {
        window.speechSynthesis.cancel();
        const utterance = new SpeechSynthesisUtterance(value);
        utterance.rate = state.rate;
        utterance.pitch = state.pitch;
        window.speechSynthesis.speak(utterance);
        return true;
      }
    } catch (error) { /* no browser voices */ }
    return false;
  }

  function stop() {
    if (!native || typeof host.ttsStop !== 'function') {
      try { window.speechSynthesis?.cancel(); } catch (error) { /* no-op */ }
      return;
    }
    try { host.ttsStop(); } catch (error) { /* already stopped */ }
  }

  function setEnabled(value) {
    state.enabled = !!value;
    persist();
    if (!state.enabled) stop();
    notify();
  }

  function setRate(value) {
    state.rate = Math.max(0.4, Math.min(2.5, number(value, state.rate)));
    persist();
    configure();
    notify();
  }

  function setPitch(value) {
    state.pitch = Math.max(0.4, Math.min(2.5, number(value, state.pitch)));
    persist();
    configure();
    notify();
  }

  function setEngine(value) {
    state.engine = String(value || '');
    persist();
    configure();
    notify();
  }

  function status() {
    if (!native || typeof host.ttsStatus !== 'function') {
      const available = typeof window !== 'undefined' && 'speechSynthesis' in window;
      return { available, ready: available, engine: '', browser: true, state: 'idle' };
    }
    try { return JSON.parse(host.ttsStatus() || '{}'); }
    catch (error) { return { available: false, ready: false }; }
  }

  function engines() {
    if (!native || typeof host.ttsEngines !== 'function') return [];
    try {
      const list = JSON.parse(host.ttsEngines() || '[]');
      return Array.isArray(list) ? list : [];
    } catch (error) {
      return [];
    }
  }

  function onChange(listener) {
    listeners.add(listener);
    return () => listeners.delete(listener);
  }

  return {
    native,
    state,
    speak,
    stop,
    setEnabled,
    setRate,
    setPitch,
    setEngine,
    configure,
    status,
    engines,
    onChange,
  };
}
