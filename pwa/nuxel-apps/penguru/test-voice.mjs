// Regression test for the Android voice session state machine.
//
// Run with: node pwa/nuxel-apps/penguru/test-voice.mjs
//
// Covers the failure that made a long dictation disappear: tapping the mic
// must keep the session alive while transcription runs, and the held
// tap-to-send hypothesis must be delivered on the second tap.

const elements = new Map();
function el(id) {
  if (!elements.has(id)) {
    const item = {
      id,
      textContent: '',
      value: '',
      hidden: false,
      disabled: false,
      checked: false,
      options: [{ value: '900', textContent: '0.90 seconds' }],
      classes: new Set(),
      classList: {
        toggle: (name, on) => { if (on) item.classes.add(name); else item.classes.delete(name); },
        contains: name => item.classes.has(name),
      },
      setAttribute: (key, value) => { item[key] = value; },
      append: () => {},
      closest: () => null,
      addEventListener: () => {},
    };
    elements.set(id, item);
  }
  return elements.get(id);
}

globalThis.document = {
  getElementById: el,
  hidden: false,
  addEventListener: () => {},
  createElement: () => ({ value: '', textContent: '' }),
};
const storage = new Map();
globalThis.localStorage = {
  getItem: key => (storage.has(key) ? storage.get(key) : null),
  setItem: (key, value) => storage.set(key, String(value)),
  removeItem: key => storage.delete(key),
};
const calls = { finish: 0, results: [] };
globalThis.window = {
  NuxelAndroid: {
    isStandalone: () => true,
    speechInputAvailable: () => true,
    speechAvailable: () => true,
    speechConfigure: () => true,
    startSpeechRecognitionConfig: () => true,
    stopSpeechRecognition: () => {},
    finishSpeechRecognition: () => { calls.finish++; },
  },
  addEventListener: () => {},
  parent: null,
};
globalThis.navigator = { mediaDevices: {} };
let clock = 0;
globalThis.performance = { now: () => clock++ };

const { voiceControls, parseVoiceText } = await import(new URL('./voice.js', import.meta.url));
const { speakable } = await import(new URL('./talkback.js', import.meta.url));
const voice = voiceControls(async () => ({}), () => true, (text, auto, meta) => {
  calls.results.push({ text, auto, meta: meta || {} });
});

const codeCommand = parseVoiceText('Penguru code write a sort function');
if (!codeCommand.hadWake || codeCommand.mode !== 'codebird'
    || codeCommand.rest !== 'write a sort function') {
  throw new Error('wake/mode parsing failed: ' + JSON.stringify(codeCommand));
}
if (parseVoiceText('chat').hadWake || parseVoiceText('chat').mode) {
  throw new Error('a bare "chat" must not force a mode without the wake word');
}

// Talkback must not read the decorative middle dot in "PenGuru · on-device".
const spoken = speakable('PenGuru · on-device\n\nCPU · 4 threads');
if (spoken.includes('·') || spoken.includes('•')) {
  throw new Error('talkback left a decorative separator in: ' + spoken);
}
if (!spoken.includes('PenGuru on-device')) {
  throw new Error('talkback header was not cleaned: ' + spoken);
}

voice.start();
await new Promise(resolve => setTimeout(resolve, 10));
if (!voice.recording) throw new Error('mic did not enter the recording state');

window.__nuxelSpeechStatus({ state: 'recording', text: 'Microphone open · listening now' });
if (!el('mic-status').textContent.includes('Microphone open')) {
  throw new Error('recording status was not shown');
}

voice.toggleMic();
if (calls.finish !== 1) throw new Error('finishSpeechRecognition was not requested');
if (!el('mic-status').textContent.includes('transcribing')) {
  throw new Error('session did not switch to transcribing');
}

// A 56 s dictation can take a while to transcribe. The result must still be
// accepted instead of being discarded by the old 14 s watchdog.
await new Promise(resolve => setTimeout(resolve, 50));
window.__nuxelSpeechResult({ ok: true, text: 'hello world', wake: false });
await new Promise(resolve => setTimeout(resolve, 10));
if (calls.results.length !== 1 || calls.results[0].text !== 'hello world') {
  throw new Error('long transcript was dropped: ' + JSON.stringify(calls.results));
}
if (voice.recording) throw new Error('mic stayed active after the transcript');

// Tap-to-talk can hold a finished hypothesis until the second tap.
voice.start();
await new Promise(resolve => setTimeout(resolve, 10));
window.__nuxelSpeechStatus({ state: 'held', text: 'Recorded · tap the mic again' });
if (!el('mic-status').textContent.includes('Recorded')) {
  throw new Error('held status was not shown');
}
voice.toggleMic();
if (calls.finish !== 2) throw new Error('held transcript was not sent on the second tap');
window.__nuxelSpeechResult({ ok: true, text: 'held sentence', wake: false });
await new Promise(resolve => setTimeout(resolve, 10));
if (calls.results.length !== 2 || calls.results[1].text !== 'held sentence') {
  throw new Error('held transcript was dropped');
}

// Every microphone mode strips "Penguru" and takes the rest as the request.
voice.start();
await new Promise(resolve => setTimeout(resolve, 10));
window.__nuxelSpeechResult({ok: true, text: 'Penguru code write a sort function', wake: false});
await new Promise(resolve => setTimeout(resolve, 10));
const codeResult = calls.results[calls.results.length - 1];
if (codeResult.text !== 'write a sort function' || codeResult.meta.mode !== 'codebird') {
  throw new Error('wake/mode command was not routed: ' + JSON.stringify(codeResult));
}

// A mode-only command switches the assistant without sending an empty message.
voice.start();
await new Promise(resolve => setTimeout(resolve, 10));
window.__nuxelSpeechResult({ok: true, text: 'Penguru chat', wake: false});
await new Promise(resolve => setTimeout(resolve, 10));
const chatResult = calls.results[calls.results.length - 1];
if (chatResult.text !== '' || chatResult.meta.mode !== 'chatbird') {
  throw new Error('mode-only command was not routed: ' + JSON.stringify(chatResult));
}

console.log('voice.js state-machine test PASSED');
