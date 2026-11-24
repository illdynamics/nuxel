// Foreground-only local speech. Never auto-sends transcripts or system actions.
// On Android this uses the built-in SpeechRecognizer (on-device where the device
// supports it) so no Nuxel host is required. The Web Audio path remains as a
// fallback for browsers and for a future whisper.cpp bridge.
export function voiceControls(call, available, onText) {
  const $ = id => document.getElementById(id);
  const host = typeof window !== 'undefined' ? window.NuxelAndroid : null;
  const nativeSpeech = !!(host && typeof host.speechAvailable === 'function' && host.speechAvailable());
  let active = false, stream = null, context = null, processor = null, chunks = [], timer = null;
  let epoch = 0;

  const status = text => { $('voice-status').textContent = text; };

  function idleUi() {
    $('voice-stop').disabled = true;
    $('voice-talk').disabled = false;
    $('voice-wake').disabled = false;
  }

  function finishNative() {
    active = false;
    clearTimeout(timer);
    idleUi();
  }

  async function stop() {
    active = false;
    epoch++;
    clearTimeout(timer);
    if (nativeSpeech && host && typeof host.stopSpeechRecognition === 'function') {
      try { host.stopSpeechRecognition(); } catch (error) { /* already stopped */ }
    }
    if (processor) { processor.disconnect(); processor.onaudioprocess = null; processor = null; }
    if (stream) { stream.getTracks().forEach(t => t.stop()); stream = null; }
    if (context) { const c = context; context = null; try { await c.close(); } catch (error) { /* closed */ } }
    chunks = [];
    idleUi();
    status('Microphone closed');
  }

  function nativeListen(wake) {
    if (active) return;
    if (!available() || document.hidden) { status('Enable PenGuru and finish the current response first.'); return; }
    active = true;
    const own = ++epoch;
    $('voice-stop').disabled = false;
    $('voice-talk').disabled = $('voice-wake').disabled = true;
    status(wake ? 'Microphone on · say “Penguru” · foreground only' : 'Microphone on · speak now');

    window.__nuxelSpeechResult = result => {
      if (!active || own !== epoch) return;
      finishNative();
      if (!result || result.ok !== true) {
        status('Speech recognition: ' + (result && result.error ? result.error : 'unavailable'));
        return;
      }
      const text = String(result.text || '').trim();
      if (!text) { status('No speech detected. Try again.'); return; }
      if (wake) {
        const match = text.match(/\bpenguru\b[\s,.:;!?-]*(.*)$/i);
        if (!match) {
          status('No “Penguru” detected. Listening again…');
          timer = setTimeout(() => { if (!document.hidden) nativeListen(true); }, 600);
          return;
        }
        const rest = match[1].trim();
        if (rest) onText(rest);
        status(rest ? '“Penguru” detected. Review your message and press Send.' : '“Penguru” detected. Say your message and tap again.');
      } else {
        onText(text);
        status('Transcript ready. Review it and press Send.');
      }
    };

    try {
      if (!host.startSpeechRecognition(wake)) throw new Error('Could not start Android speech recognition');
    } catch (error) {
      finishNative();
      status(error.message);
      return;
    }
    timer = setTimeout(() => {
      if (!active || own !== epoch) return;
      finishNative();
      try { host.stopSpeechRecognition(); } catch (error) { /* already stopped */ }
      status('Speech recognition timed out. Try again.');
    }, 15000);
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
          if (text) onText(text);
          status(wake ? '“Penguru” detected. Review your message and press Send.' : 'Transcript ready. Review it and press Send.');
        } catch (e) { status(e.message); }
      }, 5000);
    } catch (e) { await stop(); status(e.message); }
  }

  function start(wake) {
    if (nativeSpeech) nativeListen(wake);
    else recordListen(wake);
  }

  $('voice-talk').onclick = () => start(false);
  $('voice-wake').onclick = () => start(true);
  $('voice-stop').onclick = stop;
  document.addEventListener('visibilitychange', () => { if (document.hidden) stop(); });
  window.addEventListener('pagehide', stop);
  return {stop};
}
