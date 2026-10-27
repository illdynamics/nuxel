// Recorder WAV encoder unit test (node).
const wav = require('../js/recorder-wav.js');
let failures = 0;
function check(name, cond, extra) {
  console.log((cond ? 'PASS ' : 'FAIL ') + name + (cond ? '' : '  ' + (extra === undefined ? '' : extra)));
  if (!cond) failures++;
}

// Generate a known 1 kHz sine at 8000 Hz mono.
const rate = 8000;
const samples = [];
for (let i = 0; i < 8000; i++) samples.push(Math.sin(2 * Math.PI * 1000 * i / rate) * 0.5);
const bytes = wav.encodeWav([samples], rate, samples);
check('encoder returns a Uint8Array', bytes instanceof Uint8Array);
check('WAV header is valid RIFF/WAVE/fmt', wav.wavHeaderInfo(bytes).valid === true, JSON.stringify(wav.wavHeaderInfo(bytes)));
const info = wav.wavHeaderInfo(bytes);
check('WAV declares mono', info.channels === 1);
check('WAV declares 16-bit PCM', info.bitsPerSample === 16);
check('WAV declares the requested sample rate', info.sampleRate === rate);
check('data chunk size matches samples', info.dataSize === samples.length * 2);
check('total size matches header + data', info.totalBytes === 44 + samples.length * 2);

let threw = false;
try { wav.encodeWav([[1,2],[1,2,3]], 8000, [1,2,3]); } catch (e) { threw = true; }
check('rejects mismatched channel lengths', threw);
process.exit(failures ? 1 : 0);
