// Voice input for PenGuru.
//
// On Android this uses the native SpeechRecognizer bridge. The bridge exposes
// three endpointing policies:
//
//   toggle  (default) tap the mic to talk; tap it again to stop, transcribe and
//           send. Nothing waits for a silence timeout.
//   vad     adaptive voice-activity detection: sends as soon as the owner has
//           actually stopped talking. The end-of-speech window is configurable.
//   fixed   "Speak a message" records for exactly five seconds, then transcribes
//           and sends everything captured in that window.
//
// The persistent SonarBird listener has the same adaptive endpointing, and the
// voice-command vocabulary ("Penguru stop", "stop listening", "send it") is
// handled natively as well as here.
// The same wake-word variants as the native SonarBird service. Requiring a
// real word boundary keeps unrelated words such as "pengurus" out.
const WAKE_WORD = '(?:pen|peng|ping|pang)[\\s-]*(?:g[uo]{0,2})?[\\s-]*[uo]{0,2}[\\s-]*r[ou]{1,2}';
const WAKE_RE = new RegExp('\\b(?:' + WAKE_WORD + ')\\b[\\s,.:;!?-]*(.*)$', 'i');
const STOP_RE = new RegExp('^(?:(?:hey|hi|ok|okay|oi)\\s+)?(?:' + WAKE_WORD + ')\\b[\\s,.:;!?-]*(?:stop(?:\\s+(?:listening|recording|now|it|that|the\\s+mic))?|abort|halt|never[\\s-]?mind|that\'?s\\s+all|that\\s+is\\s+all|cancel|quiet|silence|shut\\s+up|enough)[\\s.!,]*$', 'i');
const SEND_RE = new RegExp('^(?:(?:hey|hi|ok|okay|oi)\\s+)?(?:' + WAKE_WORD + ')\\b[\\s,.:;!?-]*(?:send(?:\\s+(?:it|now|this|that|message))?|submit|finish|done|that\'?s\\s+it|go\\s+ahead)[\\s.!,]*$', 'i');
const MODE_RE = /^(chat\s*bird|chatbird|chat|code\s*bird|codebird|code|squad)\b[\s,.:;!?-]*(.*)$/i;

const KEY_MODE = 'penguru-voice-mode';
const KEY_END_SILENCE = 'penguru-voice-end-silence';
const KEY_COMMANDS = 'penguru-voice-commands';
const KEY_NOISE = 'penguru-voice-noise';
const DEFAULT_END_SILENCE_MS = 900;
const FIXED_RECORD_MS = 5000;
const MODES = ['toggle', 'vad', 'fixed'];
// Whisper tiny.en on a phone can take a while for a long dictation. The old
// 14 s watchdog released the UI and threw away the transcript while the
// recorder was still working.
const TRANSCRIBE_WATCHDOG_MS = 330000;

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

function clamp(value, min, max) {
  return Math.max(min, Math.min(max, Number(value) || min));
}

export function modeName(word) {
  const value = String(word || '').toLowerCase().replace(/\s+/g, '');
  if (value === 'chat' || value === 'chatbird') return 'chatbird';
  if (value === 'code' || value === 'codebird') return 'codebird';
  if (value === 'squad') return 'squad';
  return '';
}

export function modeLabel(mode) {
  if (mode === 'chatbird') return 'ChatBird';
  if (mode === 'codebird') return 'CodeBird';
  if (mode === 'squad') return 'PenGuru Squad';
  return 'PenGuru';
}

/**
 * Split a transcript into an optional wake phrase, an optional forced mode and
 * the actual request. Works in every microphone mode: "Penguru code write a
 * sort function" sends only "write a sort function" to CodeBird.
 */
export function parseVoiceText(raw) {
  const text = String(raw || '').trim();
  const match = text.match(WAKE_RE);
  if (!match) {
    return {hadWake: false, rest: text, mode: ''};
  }
  let rest = String(match[1] || '').trim();
  let mode = '';
  const modeMatch = rest.match(MODE_RE);
  if (modeMatch) {
    mode = modeName(modeMatch[1]);
    rest = String(modeMatch[2] || '').trim();
  }
  return {hadWake: true, rest, mode};
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
  let mode = stored(KEY_MODE, 'toggle');
  if (!MODES.includes(mode)) mode = 'toggle';
  let endSilenceMs = Math.round(clamp(stored(KEY_END_SILENCE, DEFAULT_END_SILENCE_MS), 350, 5000));
  let commands = stored(KEY_COMMANDS, '1') === '1';
  let noise = stored(KEY_NOISE, 'auto');
  let manualStop = false;
  let pendingText = '';
  let currentMode = mode;
  let finishing = false;
  let transcribing = false;
  let held = false;

  const status = text => {
    for (const id of ['voice-status', 'mic-status']) {
      const el = $(id);
      if (el) el.textContent = text;
    }
  };
  const nativeAvailable = () => {
    try {
      if (!host) return false;
      if (typeof host.speechInputAvailable === 'function') return !!host.speechInputAvailable();
      return typeof host.speechAvailable === 'function' && !!host.speechAvailable();
    } catch (error) { return false; }
  };

  function persistNative() {
    try {
      if (host && typeof host.speechConfigure === 'function') {
        host.speechConfigure(JSON.stringify({
          end_silence_ms: endSilenceMs,
          commands,
          noise,
        }));
      }
    } catch (error) { /* older bridge */ }
  }

  function syncModeControls() {
    for (const id of ['voice-mode', 'convo-mode']) {
      const select = $(id);
      if (select) select.value = mode;
    }
    for (const id of ['voice-silence', 'convo-silence']) {
      const select = $(id);
      if (!select) continue;
      const value = String(endSilenceMs);
      if (![...select.options].some(option => option.value === value)) {
        const option = document.createElement('option');
        option.value = value;
        option.textContent = (endSilenceMs / 1000).toFixed(2) + ' seconds';
        select.append(option);
      }
      select.value = value;
      const label = select.closest('label');
      if (label) label.hidden = mode !== 'vad';
    }
    if ($('voice-commands')) $('voice-commands').checked = commands;
    if ($('voice-noise')) $('voice-noise').value = noise;
  }

  function setMode(value) {
    mode = MODES.includes(value) ? value : 'toggle';
    save(KEY_MODE, mode);
    persistNative();
    syncModeControls();
    status(mode === 'toggle'
      ? 'Tap the mic to talk; tap it again to stop, transcribe and send.'
      : mode === 'vad'
        ? 'Voice activity detection is on; PenGuru sends when you stop talking.'
        : 'The mic records for 5 seconds, then transcribes and sends.');
  }

  function setEndSilenceMs(value) {
    endSilenceMs = Math.round(clamp(value, 350, 5000));
    save(KEY_END_SILENCE, endSilenceMs);
    persistNative();
    syncModeControls();
    status('End-of-speech silence: ' + (endSilenceMs / 1000).toFixed(2) + ' seconds.');
  }

  function setCommands(value) {
    commands = !!value;
    save(KEY_COMMANDS, commands ? '1' : '0');
    persistNative();
    if ($('voice-commands')) $('voice-commands').checked = commands;
  }

  function setNoise(value) {
    noise = value === 'off' ? 'off' : 'auto';
    save(KEY_NOISE, noise);
    persistNative();
    if ($('voice-noise')) $('voice-noise').value = noise;
  }

  function updateMicUi() {
    const mic = $('mic');
    if (mic) {
      const recording = active && !transcribing && !held;
      const busy = active && transcribing;
      const readyToSend = !!pendingText || held;
      mic.classList.toggle('recording', recording);
      mic.classList.toggle('transcribing', busy);
      mic.classList.toggle('pending', readyToSend);
      mic.setAttribute('aria-pressed', String(recording || readyToSend));
      mic.setAttribute('aria-label', busy
        ? 'Transcribing recording'
        : recording ? 'Stop recording and send request'
          : readyToSend ? 'Send recorded request' : 'Record a request');
      mic.title = busy
        ? 'Transcribing on this device'
        : recording ? 'Stop, transcribe and send'
          : readyToSend ? 'Send recorded request' : 'Record a request';
    }
    if ($('voice-stop')) $('voice-stop').disabled = !active;
    if ($('voice-talk')) $('voice-talk').disabled = active;
    if ($('voice-wake')) $('voice-wake').disabled = active;
  }

  function finishNative() {
    active = false;
    finishing = false;
    manualStop = false;
    transcribing = false;
    held = false;
    clearTimeout(timer);
    timer = null;
    updateMicUi();
  }

  function deliver(text, auto, meta) {
    const value = String(text || '').trim();
    if (!value) { status('No speech detected. Try again.'); return false; }
    pendingText = '';
    try {
      const result = onText(value, !!auto, meta || {});
      if (result && typeof result.catch === 'function') result.catch(() => {});
    } catch (error) { /* the caller reports UI errors */ }
    updateMicUi();
    return true;
  }

  function deliverMode(mode) {
    if (!mode) return false;
    pendingText = '';
    try {
      const result = onText('', true, {mode});
      if (result && typeof result.catch === 'function') result.catch(() => {});
    } catch (error) { /* the caller reports UI errors */ }
    updateMicUi();
    return true;
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
    transcribing = false;
    held = false;
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
    if (!active || finishing) return;
    if (!host) {
      // Browser fallback: finish the Web Audio capture and transcribe locally.
      finishing = true;
      recordFinish();
      return;
    }
    finishing = true;
    manualStop = true;
    transcribing = true;
    held = false;
    updateMicUi();
    status(reason === 'fixed'
      ? 'Five seconds recorded · transcribing on this device…'
      : reason === 'timeout'
        ? 'Finishing your request…'
        : 'Stopping the mic · transcribing on this device…');
    if (host && typeof host.finishSpeechRecognition === 'function') {
      try {
        host.finishSpeechRecognition();
        // Transcription of a long recording can legitimately take minutes.
        // Keep the session alive so the native result is not discarded by the
        // page before it arrives.
        clearTimeout(timer);
        timer = setTimeout(() => {
          if (active) {
            finishNative();
            status('Transcription took too long. Tap the mic to try again.');
          }
        }, TRANSCRIBE_WATCHDOG_MS);
        return;
      } catch (error) { /* fall back */ }
    }
    // Older bridge: cancel and report rather than leaving the mic open.
    try { host && host.stopSpeechRecognition && host.stopSpeechRecognition(); } catch (error) { /* stopped */ }
    finishNative();
    status('Microphone closed. Tap the mic to try again.');
  }

  function errorText(error) {
    switch (error) {
      case 'voice_stop_command':
        return 'Stopped by voice command. Microphone closed.';
      case 'voice_cancel_command':
        return 'Cancelled by voice command. Microphone closed.';
      case 'voice_send_command':
        return 'Send command heard, but there was no transcript to send.';
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
      case 'speech_retry_needed':
        return 'Android’s recognizer did not capture that sentence. Tap the mic to record again with the on-device engine.';
      case 'whisper_model_missing':
        return 'Whisper is not ready. Open Model library → Whisper · tiny.en speech recognition and download it to this phone.';
      case 'whisper_runtime_missing':
        return 'The bundled Whisper speech engine is missing from this APK. Reinstall the latest PenGuru APK.';
      case 'whisper_audio_unavailable':
      case 'whisper_capture_failed':
        return 'Whisper could not open the microphone. Close other voice apps and tap the mic again.';
      case 'whisper_timeout':
        return 'Whisper took too long to transcribe. Try a shorter sentence.';
      case 'whisper_failed':
        return 'Whisper could not transcribe that recording. Tap the mic and try again.';
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
      if (result && result.command === 'stop') {
        status(errorText('voice_stop_command'));
        return;
      }
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
        timer = setTimeout(() => { if (!document.hidden) nativeListen(nextMode); }, 450);
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
        timer = setTimeout(() => { if (!document.hidden) nativeListen(nextMode); }, 450);
      } else {
        status('No speech detected. Tap the mic and try again.');
      }
      return;
    }

    const spoken = parseVoiceText(text);
    const wakeMode = nextMode === 'wake';
    const followup = nextMode === 'followup';
    if (wakeMode && !spoken.hadWake) {
      status('No “Penguru” detected. Listening again…');
      timer = setTimeout(() => { if (!document.hidden) nativeListen('wake'); }, 450);
      return;
    }

    const rest = spoken.hadWake ? spoken.rest : text;
    if (spoken.mode) {
      if (!rest) {
        deliverMode(spoken.mode);
        status('“Penguru” detected · ' + modeLabel(spoken.mode) + ' selected'
          + (wakeMode || followup ? ' · listening for your message…' : ''));
        if (wakeMode || followup) {
          timer = setTimeout(() => { if (!document.hidden) nativeListen('followup'); }, 300);
        }
        return;
      }
      if (commands && STOP_RE.test(rest)) {
        status(errorText('voice_stop_command'));
        return;
      }
      deliver(rest, true, {mode: spoken.mode});
      status('Heard “Penguru” · ' + modeLabel(spoken.mode) + ' · sending: ' + rest);
      return;
    }

    if (spoken.hadWake && !rest) {
      status('“Penguru” detected · listening for your message…');
      timer = setTimeout(() => { if (!document.hidden) nativeListen('followup'); }, 300);
      return;
    }
    if (commands && STOP_RE.test(rest)) {
      status(errorText('voice_stop_command'));
      return;
    }
    if (commands && SEND_RE.test(rest)) {
      status(errorText('voice_send_command'));
      return;
    }
    if (followup) {
      deliver(rest, true);
      status('“Penguru” request sent: ' + rest);
      return;
    }
    if (wakeMode || spoken.hadWake) {
      deliver(rest, true);
      status('Heard “Penguru” · sending: ' + rest);
      return;
    }
    // Conversation mic and the five-second "Speak a message" mode always
    // stop, transcribe and send. This is the owner-selected default.
    deliver(rest, true);
    status((nextMode === 'fixed' ? 'Five-second transcript sent: ' : 'Transcript sent: ') + rest);
  }

  function nativeConfig(nextMode) {
    if (nextMode === 'fixed') {
      return {mode: 'fixed', record_ms: FIXED_RECORD_MS, end_silence_ms: 0,
        max_ms: FIXED_RECORD_MS + 6000, commands, noise};
    }
    if (nextMode === 'vad') {
      return {mode: 'vad', end_silence_ms: endSilenceMs, max_ms: 26000, commands, noise};
    }
    if (nextMode === 'wake' || nextMode === 'followup') {
      return {mode: nextMode, end_silence_ms: Math.min(endSilenceMs, 1200), max_ms: 22000, commands, noise};
    }
    return {mode: 'toggle', end_silence_ms: 0, max_ms: 95000, commands, noise};
  }

  function nativeListen(nextMode) {
    if (active) return;
    if (document.hidden) {
      status('Open PenGuru to use the microphone.');
      return;
    }
    if (!available()) {
      status('Wait for the current answer to finish, or press Stop generation first.');
      return;
    }
    if (!nativeAvailable()) {
      status('No speech recognizer is installed. Open Android Settings → System → Languages & input → Voice input and enable one.');
      return;
    }
    active = true;
    finishing = false;
    manualStop = false;
    transcribing = false;
    held = false;
    currentMode = nextMode;
    const own = ++epoch;
    updateMicUi();
    status(nextMode === 'fixed'
      ? 'Microphone on for 5 seconds · speak now · it will transcribe and send automatically'
      : nextMode === 'vad'
        ? 'Microphone on · speak now · sends after ' + (endSilenceMs / 1000).toFixed(2) + 's of real silence'
        : nextMode === 'followup'
          ? 'Listening for your message after “Penguru”…'
          : nextMode === 'wake'
            ? 'Microphone on · say “Penguru” and then your message'
            : 'Microphone on · tap the mic again to stop, transcribe and send');

    window.__nuxelSpeechResult = result => handleNativeResult(result, nextMode, own);
    window.__nuxelSpeechStatus = update => {
      if (!active || own !== epoch) return;
      const state = update && update.state;
      if (state === 'recording') {
        transcribing = false;
        held = false;
        finishing = false;
      } else if (state === 'transcribing') {
        transcribing = true;
        held = false;
        finishing = true;
      } else if (state === 'held') {
        transcribing = false;
        held = true;
        finishing = false;
      }
      updateMicUi();
      if (update && update.text) status(update.text);
    };

    try {
      if (typeof host.startSpeechRecognitionConfig === 'function') {
        if (!host.startSpeechRecognitionConfig(JSON.stringify(nativeConfig(nextMode)))) {
          throw new Error('Could not start Android speech recognition');
        }
      } else if (typeof host.startSpeechRecognitionEx === 'function') {
        const fallbackSilence = nextMode === 'vad' ? endSilenceMs
          : nextMode === 'fixed' ? FIXED_RECORD_MS : 0;
        if (!host.startSpeechRecognitionEx(nextMode, fallbackSilence)) {
          throw new Error('Could not start Android speech recognition');
        }
      } else if (!host.startSpeechRecognition(nextMode === 'wake' || nextMode === 'followup')) {
        throw new Error('Could not start Android speech recognition');
      }
    } catch (error) {
      finishNative();
      status(error.message);
      return;
    }
    // Native endpointing is authoritative. These timers only release the UI if
    // the WebView or bridge disappears, so they must outlive a long local
    // transcription instead of closing the session early.
    const fallback = nextMode === 'fixed' ? FIXED_RECORD_MS + 1000
      : nextMode === 'vad' ? 150000
      : nextMode === 'wake' || nextMode === 'followup' ? 60000 : 305000;
    timer = setTimeout(() => {
      if (!active || own !== epoch) return;
      finishNow('timeout');
    }, fallback);
    if (nextMode === 'fixed') {
      // Belt-and-braces: ask for the transcript at 5 s even if the native
      // timer could not be scheduled.
      clearTimeout(timer);
      timer = setTimeout(() => {
        if (!active || own !== epoch) return;
        finishNow('fixed');
      }, FIXED_RECORD_MS + 250);
    }
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
    if (!available() || document.hidden) { status('Wait for the current answer to finish, or press Stop generation first.'); return; }
    if (active) return;
    const own = ++epoch;
    const targetMs = currentMode === 'fixed' ? FIXED_RECORD_MS : 30000;
    try {
      const launcherHost = window.NuxelHost || window.parent?.NuxelHost;
      if (launcherHost?.micAuthorize) { const grant = await launcherHost.micAuthorize(); if (grant?.ok === false && !grant.offline) throw Error('Microphone permission denied'); }
      const acquired = await navigator.mediaDevices.getUserMedia({audio: true, video: false});
      if (own !== epoch || document.hidden) { acquired.getTracks().forEach(t => t.stop()); return; }
      stream = acquired; context = new AudioContext(); await context.resume(); active = true; finishing = false;
      updateMicUi();
      const source = context.createMediaStreamSource(stream); processor = context.createScriptProcessor(4096, 1, 1);
      const silent = context.createGain(); silent.gain.value = 0;
      source.connect(processor); processor.connect(silent); silent.connect(context.destination);
      // Lightweight browser-side VAD: learn the noise floor and finish after
      // the configured real-silence window once speech has started.
      let noiseFloor = 0.005, speechStarted = false, lastVoice = performance.now();
      processor.onaudioprocess = e => {
        if (!active) return;
        const chunk = new Float32Array(e.inputBuffer.getChannelData(0));
        chunks.push(chunk);
        let sum = 0; for (let i = 0; i < chunk.length; i++) sum += chunk[i] * chunk[i];
        const rms = Math.sqrt(sum / chunk.length);
        const threshold = Math.max(0.018, noiseFloor * 3.2);
        if (rms >= threshold) {
          speechStarted = true; lastVoice = performance.now();
        } else if (!speechStarted) {
          noiseFloor = noiseFloor * 0.92 + rms * 0.08;
        } else if (currentMode !== 'fixed' && performance.now() - lastVoice >= endSilenceMs) {
          finishNow('vad');
        }
      };
      status(currentMode === 'fixed'
        ? 'Microphone on for 5 seconds · speak now'
        : currentMode === 'vad' ? 'Microphone on · speak now · sends when you stop'
        : 'Microphone on · tap the mic again to stop, transcribe and send');
      timer = setTimeout(() => {
        if (!active || own !== epoch) return;
        finishNow(currentMode === 'fixed' ? 'fixed' : 'timeout');
      }, targetMs);
    } catch (e) { await stop(); status(e.message); }
  }

  function recordFinish() {
    if (!active) { finishing = false; return; }
    const own = epoch;
    const rate = context ? context.sampleRate : 16000;
    const samples = new Float32Array(chunks.reduce((n, c) => n + c.length, 0)); let at = 0;
    for (const chunk of chunks) { samples.set(chunk, at); at += chunk.length; }
    const audio = wav(samples, rate);
    const nextMode = currentMode;
    stop().then(async () => {
      status('Microphone closed · recognizing locally…');
      try {
        const result = await call('transcribe', {audio});
        if (epoch !== own + 1 || document.hidden || !available()) return;
        if (nextMode === 'wake' && !result.wake_detected) { status('No “Penguru” detected. Listening again…'); return; }
        const spoken = parseVoiceText(nextMode === 'wake' ? result.after_wake : result.text);
        if (spoken.mode) {
          if (spoken.rest) deliver(spoken.rest, true, {mode: spoken.mode});
          else deliverMode(spoken.mode);
        } else if (spoken.rest) {
          deliver(spoken.rest, true);
        }
        status('Transcript sent automatically.');
      } catch (e) { status(e.message); }
    }).finally(() => { finishing = false; });
  }

  function startMode(nextMode) {
    busyRetries = 0;
    if (nativeAvailable()) {
      nativeListen(nextMode);
    } else if (host) {
      status('No speech recognizer is installed. Open Android Settings → System → Languages & input → Voice input and enable one.');
    } else {
      currentMode = nextMode;
      recordListen(nextMode === 'wake' || nextMode === 'followup');
    }
  }

  function start(wake) {
    startMode(wake ? 'wake' : mode);
  }

  function toggleMic() {
    if (pendingText) { sendPending(); return; }
    if (active) { finishNow('manual'); return; }
    startMode(mode);
  }

  if ($('voice-talk')) $('voice-talk').onclick = () => startMode('fixed');
  if ($('voice-wake')) $('voice-wake').onclick = () => startMode('wake');
  if ($('voice-stop')) $('voice-stop').onclick = stop;
  if ($('mic')) $('mic').onclick = toggleMic;
  for (const id of ['voice-mode', 'convo-mode']) {
    if ($(id)) $(id).onchange = () => setMode($(id).value);
  }
  for (const id of ['voice-silence', 'convo-silence']) {
    if ($(id)) $(id).onchange = () => setEndSilenceMs($(id).value);
  }
  if ($('voice-commands')) $('voice-commands').onchange = () => setCommands($('voice-commands').checked);
  if ($('voice-noise')) $('voice-noise').onchange = () => setNoise($('voice-noise').value);
  document.addEventListener('visibilitychange', () => { if (document.hidden) stop(); });
  window.addEventListener('pagehide', stop);
  syncModeControls();
  persistNative();
  updateMicUi();
  status(mode === 'toggle'
    ? 'Tap the mic to talk; tap it again to stop, transcribe and send.'
    : mode === 'vad'
      ? 'Voice activity detection is on; PenGuru sends when you stop talking.'
      : 'The mic records for 5 seconds, then transcribes and sends.');

  return {
    stop,
    start,
    startDictation: () => startMode(mode),
    startWake: () => startMode('wake'),
    startFixed: () => startMode('fixed'),
    toggleMic,
    setMode,
    setSilenceMs: setEndSilenceMs,
    setEndSilenceMs,
    setCommands,
    setNoise,
    syncModeControls,
    get mode() { return mode; },
    get autoSend() { return mode !== 'toggle'; },
    get silenceMs() { return endSilenceMs; },
    get endSilenceMs() { return endSilenceMs; },
    get commands() { return commands; },
    get noise() { return noise; },
    get recording() { return active; },
    get pending() { return !!pendingText; },
  };
}
