// Voice input for PenGuru. On Android this uses the built-in SpeechRecognizer
// (on-device where the device supports it). The Web Audio path remains a
// fallback for browsers and for a future whisper.cpp bridge.
//
// The conversation mic is a toggle:
//   tap once  -> start listening
//   tap again -> finish and send the transcript
// If "auto-send after silence" is enabled, the recognizer finishes and sends
// by itself after the configured silence window. With it disabled the owner
// can talk for as long as they like and the second tap submits.
//
// Every native session has both a JavaScript deadline and a native watchdog so
// the microphone is always released even when a speech service never calls
// back. That "listening forever" state was the previous beta's biggest bug.
const WAKE_RE = /\bpen[\s-]?guru\b[\s,.:;!?-]*(.*)$/i;
const KEY_AUTOSEND = 'penguru-voice-autosend';
const KEY_SILENCE = 'penguru-voice-silence';
const DEFAULT_SILENCE_MS = 2500;
const SILENCE_CHOICES = [0, 1500, 2500, 4000, 7000];

function stored(key, fallback) {
  try {
    const value = localStorage.getItem(key);
    return value == null ? fallback : value;
  } catch (error) {
    return fallback;
  }
}

function save(key, value) {
  try { localStorage.setItem(key, String(value)); } catch (error) { /* unavailable */ }
}

export function voiceControls(call, available, onText) {
  const $ = id => document.getElementById(id);
  const host = typeof window !== 'undefined' ? window.NuxelAndroid : null;
  let active = false, stream = null, context = null, processor = null, chunks = [], timer = null;
  let epoch = 0;
  // Android can return ERROR_RECOGNIZER_BUSY / ERROR_CLIENT for a moment while
  // the speech service releases the background listener. Retry those
  // automatically instead of making the owner tap the microphone again.
  let busyRetries = 0;
  let autoSend = stored(KEY_AUTOSEND, '1') === '1';
  let silenceMs = Number(stored(KEY_SILENCE, String(DEFAULT_SILENCE_MS)));
  if (!Number.isFinite(silenceMs) || silenceMs <= 0) silenceMs = DEFAULT_SILENCE_MS;
  let manualStop = false;   // the second mic tap asked to finish + send
  let pendingText = '';     // transcript waiting for a second tap / Send

  const status = text => {
    for (const id of ['voice-status', 'mic-status']) {
      const el = $(id);
      if (el) el.textContent = text;
    }
  };
  const nativeAvailable = () => {
    try { return !!(host && typeof host.speechAvailable === 'function' && host.speechAvailable()); }
    catch (error) { return false; }
  };

  function syncSilenceControls() {
    const value = String(autoSend ? silenceMs : 0);
    for (const id of ['voice-silence', 'convo-silence']) {
      const select = $(id);
      if (!select) continue;
      if (![...select.options].some(option => option.value === value)) {
        const option = document.createElement('option');
        option.value = value;
        option.textContent = (silenceMs / 1000).toFixed(1) + ' seconds';
        select.append(option);
      }
      select.value = value;
    }
  }

  function setSilenceMs(value) {
    const ms = Math.max(0, Number(value) || 0);
    if (ms <= 0) {
      autoSend = false;
    } else {
      autoSend = true;
      silenceMs = ms;
    }
    save(KEY_AUTOSEND, autoSend ? '1' : '0');
    save(KEY_SILENCE, silenceMs);
    syncSilenceControls();
    status(autoSend
      ? 'Voice requests send automatically after ' + (silenceMs / 1000).toFixed(1) + ' seconds of silence.'
      : 'Voice requests stay open until you tap the mic again and send.');
  }

  function updateMicUi() {
    const mic = $('mic');
    if (mic) {
      const recording = active;
      mic.classList.toggle('recording', recording);
      mic.setAttribute('aria-pressed', String(recording || !!pendingText));
      mic.setAttribute('aria-label', recording
        ? 'Stop recording and send request'
        : pendingText ? 'Send recorded request' : 'Record a request');
      mic.title = recording
        ? 'Stop and send'
        : pendingText ? 'Send recorded request' : 'Record a request';
    }
    if ($('voice-stop')) $('voice-stop').disabled = !active;
    if ($('voice-talk')) $('voice-talk').disabled = active;
    if ($('voice-wake')) $('voice-wake').disabled = active;
  }

  function finishNative() {
    active = false;
    clearTimeout(timer);
    timer = null;
    updateMicUi();
  }

  function deliver(text, auto) {
    const value = String(text || '').trim();
    if (!value) { status('No speech detected. Try again.'); return; }
    pendingText = '';
    try {
      const result = onText(value, !!auto);
      if (result && typeof result.catch === 'function') result.catch(() => {});
    } catch (error) { /* the caller reports UI errors */ }
    updateMicUi();
  }

  function sendPending() {
    const text = pendingText;
    pendingText = '';
    const prompt = $('prompt');
    if (prompt) prompt.value = '';
    updateMicUi();
    if (!text) return;
    status('Sending recorded request…');
    deliver(text, true);
  }

  async function stop() {
    active = false;
    manualStop = false;
    pendingText = '';
    epoch++;
    busyRetries = 0;
    clearTimeout(timer);
    timer = null;
    try {
      if (host && typeof host.stopSpeechRecognition === 'function') {
        try { host.stopSpeechRecognition(); } catch (error) { /* already stopped */ }
      }
      if (processor) { processor.disconnect(); processor.onaudioprocess = null; processor = null; }
      if (stream) { stream.getTracks().forEach(t => t.stop()); stream = null; }
      if (context) { const c = context; context = null; try { await c.close(); } catch (error) { /* closed */ } }
    } finally {
      chunks = [];
      updateMicUi();
      status('Microphone closed');
    }
  }

  function finishNow(reason) {
    if (!active) return;
    manualStop = true;
    status(reason === 'timeout' ? 'Finishing your request…' : 'Finishing and sending…');
    if (host && typeof host.finishSpeechRecognition === 'function') {
      try { host.finishSpeechRecognition(); return; } catch (error) { /* fall back */ }
    }
    // Older bridge: cancel and report rather than leaving the mic open.
    try { host.stopSpeechRecognition(); } catch (error) { /* stopped */ }
    finishNative();
    status('Microphone closed. Tap the mic to try again.');
  }

  function errorText(error) {
    switch (error) {
      case 'microphone_permission_denied':
        return 'Microphone permission denied. Enable it for PenGuru Squad in Android Settings.';
      case 'speech_recognizer_unavailable':
      case 'speech_start_failed':
        return 'This phone has no working Android speech recognition service. Enable Google speech services or a system speech recognizer.';
      case 'language_unavailable':
      case 'language_not_supported':
        return 'Android has no speech model for this language. Add English (US) voice input in Android Settings → System → Languages & input.';
      case 'network_error':
      case 'network_timeout':
      case 'speech_service_error':
        return 'The speech service could not answer. Check the network or install an offline speech language pack, then try again.';
      case 'client_error':
      case 'recognizer_busy':
        return 'The phone is switching microphones. PenGuru is retrying automatically — keep the app open for a moment.';
      case 'no_speech_detected':
        return 'No speech detected. Tap the mic and try again.';
      case 'speech_timeout':
        return 'The microphone timed out and has been released. Try again.';
      default:
        return 'Speech recognition: ' + error + '. Tap the microphone to retry.';
    }
  }

  function handleNativeResult(result, nextMode, own) {
    if (!active || own !== epoch) return;
    finishNative();
    if (!result || result.ok !== true) {
      const error = result && result.error ? result.error : 'unavailable';
      if ((error === 'recognizer_busy' || error === 'client_error') && busyRetries < 4) {
        busyRetries++;
        status('Reconnecting the microphone…');
        timer = setTimeout(() => {
          if (!document.hidden) nativeListen(nextMode);
        }, 700 * busyRetries);
        return;
      }
      if ((nextMode === 'wake' || nextMode === 'followup') && error === 'no_speech_detected') {
        status(nextMode === 'wake' ? 'No “Penguru” detected. Listening again…' : 'No speech detected. Listening again…');
        timer = setTimeout(() => { if (!document.hidden) nativeListen(nextMode); }, 500);
        return;
      }
      status(errorText(error));
      return;
    }
    busyRetries = 0;
    const text = String(result.text || '').trim();
    if (!text) {
      if (nextMode === 'wake' || nextMode === 'followup') {
        status('No speech detected. Listening again…');
        timer = setTimeout(() => { if (!document.hidden) nativeListen(nextMode); }, 500);
      } else {
        status('No speech detected. Tap the mic and try again.');
      }
      return;
    }
    if (nextMode === 'wake') {
      const match = text.match(WAKE_RE);
      if (!match) {
        status('No “Penguru” detected. Listening again…');
        timer = setTimeout(() => { if (!document.hidden) nativeListen('wake'); }, 500);
        return;
      }
      const rest = match[1].trim();
      if (rest) {
        deliver(rest, true);
        status('Heard “Penguru” · sending: ' + rest);
      } else {
        status('“Penguru” detected · listening for your message…');
        timer = setTimeout(() => { if (!document.hidden) nativeListen('followup'); }, 350);
      }
      return;
    }
    if (nextMode === 'followup') {
      deliver(text, true);
      status('“Penguru” request sent: ' + text);
      return;
    }
    // Ad-hoc dictation from the conversation mic.
    const tappedToSend = manualStop;
    manualStop = false;
    if (autoSend || tappedToSend) {
      deliver(text, true);
      status('Transcript sent: ' + text);
    } else {
      pendingText = text;
      const prompt = $('prompt');
      if (prompt) { prompt.value = text; try { prompt.focus(); } catch (error) { /* no focus */ } }
      try { window.dispatchEvent(new CustomEvent('penguru:transcript-ready')); } catch (error) { /* old WebView */ }
      updateMicUi();
      status('Transcript ready · tap the mic again or press Send');
    }
  }

  function nativeListen(nextMode) {
    if (active) return;
    if (!available() || document.hidden) {
      status('Enable PenGuru and finish the current response first.');
      return;
    }
    if (!nativeAvailable()) {
      status(errorText('speech_recognizer_unavailable'));
      return;
    }
    active = true;
    manualStop = false;
    const own = ++epoch;
    const effectiveSilence = nextMode === 'dictate'
      ? (autoSend ? silenceMs : 0)
      : nextMode === 'followup' ? Math.max(1200, silenceMs) : 0;
    updateMicUi();
    status(nextMode === 'dictate'
      ? (autoSend
          ? 'Microphone on · speak now · sends after ' + (silenceMs / 1000).toFixed(1) + 's of silence'
          : 'Microphone on · speak now · tap the mic again to send')
      : nextMode === 'followup'
        ? 'Listening for your message after “Penguru”…'
        : 'Microphone on · say “Penguru” and then your message');

    window.__nuxelSpeechResult = result => handleNativeResult(result, nextMode, own);

    try {
      if (typeof host.startSpeechRecognitionEx === 'function') {
        if (!host.startSpeechRecognitionEx(nextMode, effectiveSilence)) {
          throw new Error('Could not start Android speech recognition');
        }
      } else if (!host.startSpeechRecognition(nextMode !== 'dictate')) {
        throw new Error('Could not start Android speech recognition');
      }
    } catch (error) {
      finishNative();
      status(error.message);
      return;
    }
    // The native watchdog is authoritative; this one keeps the UI honest if
    // the WebView throttles or the bridge disappears. It asks for the final
    // hypothesis rather than cancelling so a spoken request is not lost.
    const fallback = nextMode === 'dictate'
      ? (autoSend ? silenceMs + 8000 : 50000)
      : 16000;
    timer = setTimeout(() => {
      if (!active || own !== epoch) return;
      if (fallback > 20000) {
        finishNow('timeout');
        return;
      }
      finishNative();
      try { host.stopSpeechRecognition(); } catch (error) { /* already stopped */ }
      status('Microphone timed out and has been released. Tap the mic to try again.');
    }, fallback);
  }

  function wav(samples, rate) {
    const count = Math.floor(samples.length * 16000 / rate);
    const bytes = new Uint8Array(44 + count * 2), v = new DataView(bytes.buffer);
    const word = (at, s) => [...s].forEach((c, i) => v.setUint8(at + i, c.charCodeAt(0)));
    word(0, 'RIFF'); v.setUint32(4, 36 + count * 2, true); word(8, 'WAVE'); word(12, 'fmt ');
    v.setUint32(16, 16, true); v.setUint16(20, 1, true); v.setUint16(22, 1, true);
    v.setUint32(24, 16000, true); v.setUint32(28, 32000, true); v.setUint16(32, 2, true); v.setUint16(34, 16, true);
    word(36, 'data'); v.setUint32(40, count * 2, true);
    for (let i = 0; i < count; i++) {
      const begin = Math.floor(i * rate / 16000), end = Math.max(begin + 1, Math.floor((i + 1) * rate / 16000));
      let sum = 0; for (let j = begin; j < end; j++) sum += samples[j] || 0;
      const x = Math.max(-1, Math.min(1, sum / (end - begin))); v.setInt16(44 + i * 2, x < 0 ? x * 32768 : x * 32767, true);
    }
    let text = ''; for (let i = 0; i < bytes.length; i += 8192) text += String.fromCharCode(...bytes.subarray(i, i + 8192));
    return btoa(text);
  }

  async function recordListen(wake) {
    if (!available() || document.hidden) { status('Enable PenGuru and finish the current response first.'); return; }
    if (active) return;
    const own = ++epoch;
    try {
      const launcherHost = window.NuxelHost || window.parent?.NuxelHost;
      if (launcherHost?.micAuthorize) { const grant = await launcherHost.micAuthorize(); if (grant?.ok === false && !grant.offline) throw Error('Microphone permission denied'); }
      const acquired = await navigator.mediaDevices.getUserMedia({audio: true, video: false});
      if (own !== epoch || document.hidden) { acquired.getTracks().forEach(t => t.stop()); return; }
      stream = acquired; context = new AudioContext(); await context.resume(); active = true;
      updateMicUi();
      const source = context.createMediaStreamSource(stream); processor = context.createScriptProcessor(4096, 1, 1);
      const silent = context.createGain(); silent.gain.value = 0;
      source.connect(processor); processor.connect(silent); silent.connect(context.destination);
      processor.onaudioprocess = e => { if (active) chunks.push(new Float32Array(e.inputBuffer.getChannelData(0))); };
      status(wake ? 'Microphone on · say “Penguru” · foreground only' : 'Microphone on · speak for up to 5 seconds');
      timer = setTimeout(async () => {
        if (!active || own !== epoch) return;
        const rate = context.sampleRate;
        const samples = new Float32Array(chunks.reduce((n, c) => n + c.length, 0)); let at = 0;
        for (const chunk of chunks) { samples.set(chunk, at); at += chunk.length; }
        await stop(); const recognitionEpoch = epoch;
        status('Microphone closed · recognizing locally…');
        try {
          const result = await call('transcribe', {audio: wav(samples, rate)});
          if (epoch !== recognitionEpoch || document.hidden || !available()) return;
          if (wake && !result.wake_detected) { status('No “Penguru” detected. Listening again…'); timer = setTimeout(() => start(true), 500); return; }
          const text = wake ? result.after_wake : result.text;
          if (text) deliver(text, true);
          status('Transcript sent automatically.');
        } catch (e) { status(e.message); }
      }, 5000);
    } catch (e) { await stop(); status(e.message); }
  }

  function start(wake) {
    busyRetries = 0;
    if (nativeAvailable()) nativeListen(wake ? 'wake' : 'dictate');
    else recordListen(wake);
  }

  function toggleMic() {
    if (pendingText) { sendPending(); return; }
    if (active) { finishNow('manual'); return; }
    start(false);
  }

  if ($('voice-talk')) $('voice-talk').onclick = () => start(false);
  if ($('voice-wake')) $('voice-wake').onclick = () => start(true);
  if ($('voice-stop')) $('voice-stop').onclick = stop;
  if ($('mic')) $('mic').onclick = toggleMic;
  for (const id of ['voice-silence', 'convo-silence']) {
    if ($(id)) $(id).onchange = () => setSilenceMs($(id).value);
  }
  document.addEventListener('visibilitychange', () => { if (document.hidden) stop(); });
  window.addEventListener('pagehide', stop);
  syncSilenceControls();
  updateMicUi();

  return {
    stop,
    start,
    startDictation: () => start(false),
    startWake: () => start(true),
    toggleMic,
    setSilenceMs,
    get autoSend() { return autoSend; },
    get silenceMs() { return silenceMs; },
    get recording() { return active; },
    get pending() { return !!pendingText; },
  };
}
