// Voice input for PenGuru. On Android this uses the built-in SpeechRecognizer
// (on-device where the device supports it). Transcripts are auto-sent by the
// caller. The Web Audio path remains a fallback for browsers and for a future
// whisper.cpp bridge.
//
// Every native session has both a JavaScript deadline and a native watchdog so
// the microphone is always released even when a speech service never calls
// back. That "listening forever" state was the previous beta's biggest bug.
const WAKE_RE = /\bpen[\s-]?guru\b[\s,.:;!?-]*(.*)$/i;

export function voiceControls(call, available, onText) {
  const $ = id => document.getElementById(id);
  const host = typeof window !== 'undefined' ? window.NuxelAndroid : null;
  let active = false, stream = null, context = null, processor = null, chunks = [], timer = null;
  let epoch = 0;

  const status = text => { const el = $('voice-status'); if (el) el.textContent = text; };
  const nativeAvailable = () => {
    try { return !!(host && typeof host.speechAvailable === 'function' && host.speechAvailable()); }
    catch (error) { return false; }
  };

  function idleUi() {
    $('voice-stop').disabled = true;
    $('voice-talk').disabled = false;
    $('voice-wake').disabled = false;
  }

  function finishNative() {
    active = false;
    clearTimeout(timer);
    timer = null;
    idleUi();
  }

  function deliver(text, auto) {
    const value = String(text || '').trim();
    if (!value) { status('No speech detected. Try again.'); return; }
    try {
      const result = onText(value, !!auto);
      if (result && typeof result.catch === 'function') result.catch(() => {});
    } catch (error) { /* the caller reports UI errors */ }
  }

  async function stop() {
    active = false;
    epoch++;
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
      idleUi();
      status('Microphone closed');
    }
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
        return 'Android’s speech service is still releasing the previous session. Wait a moment, then tap the microphone again.';
      case 'no_speech_detected':
        return 'No speech detected. Try again.';
      case 'speech_timeout':
        return 'The microphone timed out and has been released. Try again.';
      default:
        return 'Speech recognition: ' + error + '. Tap the microphone button to retry.';
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
    const own = ++epoch;
    $('voice-stop').disabled = false;
    $('voice-talk').disabled = $('voice-wake').disabled = true;
    status(nextMode === 'dictate'
      ? 'Microphone on · speak now · the transcript is sent automatically'
      : nextMode === 'followup'
        ? 'Listening for your message after “Penguru”…'
        : 'Microphone on · say “Penguru” and then your message');

    window.__nuxelSpeechResult = result => {
      if (!active || own !== epoch) return;
      finishNative();
      if (!result || result.ok !== true) {
        const error = result && result.error ? result.error : 'unavailable';
        if (nextMode === 'wake' && error === 'no_speech_detected') {
          status('No “Penguru” detected. Listening again…');
          timer = setTimeout(() => { if (!document.hidden) nativeListen('wake'); }, 500);
          return;
        }
        status(errorText(error));
        return;
      }
      const text = String(result.text || '').trim();
      if (!text) {
        if (nextMode === 'wake' || nextMode === 'followup') {
          status('No speech detected. Listening again…');
          timer = setTimeout(() => { if (!document.hidden) nativeListen(nextMode); }, 500);
        } else {
          status('No speech detected. Try again.');
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
      deliver(text, true);
      status('Transcript sent automatically: ' + text);
    };

    try {
      if (!host.startSpeechRecognition(nextMode !== 'dictate')) throw new Error('Could not start Android speech recognition');
    } catch (error) {
      finishNative();
      status(error.message);
      return;
    }
    // The native watchdog is authoritative; this one keeps the UI honest if
    // the WebView throttles or the bridge disappears.
    timer = setTimeout(() => {
      if (!active || own !== epoch) return;
      finishNative();
      try { host.stopSpeechRecognition(); } catch (error) { /* already stopped */ }
      status('Microphone timed out and has been released. Try again.');
    }, 16000);
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
      const source = context.createMediaStreamSource(stream); processor = context.createScriptProcessor(4096, 1, 1);
      const silent = context.createGain(); silent.gain.value = 0;
      source.connect(processor); processor.connect(silent); silent.connect(context.destination);
      processor.onaudioprocess = e => { if (active) chunks.push(new Float32Array(e.inputBuffer.getChannelData(0))); };
      $('voice-stop').disabled = false; $('voice-talk').disabled = $('voice-wake').disabled = true;
      status(wake ? 'Microphone on · say “Penguru” · foreground only' : 'Microphone on · speak for up to 5 seconds');
      timer = setTimeout(async () => {
        if (!active || own !== epoch) return;
        const rate = context.sampleRate;
        const samples = new Float32Array(chunks.reduce((n, c) => n + c.length, 0)); let at = 0;
        for (const chunk of chunks) { samples.set(chunk, at); at += chunk.length; }
        await stop(); const recognitionEpoch = epoch;
        $('voice-stop').disabled = false;
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
    if (nativeAvailable()) nativeListen(wake ? 'wake' : 'dictate');
    else recordListen(wake);
  }

  $('voice-talk').onclick = () => start(false);
  $('voice-wake').onclick = () => start(true);
  $('voice-stop').onclick = stop;
  document.addEventListener('visibilitychange', () => { if (document.hidden) stop(); });
  window.addEventListener('pagehide', stop);
  return {stop};
}
