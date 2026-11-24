import {voiceControls, modeLabel} from './voice.js';
import {bridge} from '../../nuxel-common/bridge.js';
import {modelLibrary} from './model-library.js';
import {createLocalEngine} from './local-engine.js';
import {talkbackControls} from './talkback.js';
import {confirmDownload, formatBytes, sumBytes} from './download-confirm.js';

const $ = id => document.getElementById(id);
let enabled = false, request = null, lastOutput = '', currentReply = null;
let spokenRequest = '';
const API_DEFAULT = 'http://127.0.0.1:8080/api/v1';
const nativeHost = typeof window !== 'undefined' ? window.NuxelAndroid : null;
const onAndroid = !!(nativeHost && typeof nativeHost.isStandalone === 'function' && nativeHost.isStandalone());
const local = createLocalEngine();
let engineMode = 'nuxel';

function stored(key) { try { return localStorage.getItem(key) || ''; } catch (e) { return ''; } }
function saveStored(key, value) { try { value ? localStorage.setItem(key, value) : localStorage.removeItem(key); } catch (e) { /* storage unavailable */ } }

engineMode = stored('nuxel-engine-mode') || (onAndroid ? 'local' : 'nuxel');
if (!['local', 'nuxel'].includes(engineMode)) engineMode = 'local';

function connectionLabel() {
  if (engineMode === 'local') return 'On-device engine · no Nuxel server, URL or token required';
  const url = stored('nuxel-api-url') || API_DEFAULT;
  return `Bridge: ${url}${stored('nuxel-penguru-token') ? ' · launcher token configured' : ' · no launcher token'}`;
}

function applyEngineMode() {
  const localPanel = $('local-panel');
  const remotePanel = $('connection-fields');
  if (localPanel) localPanel.hidden = engineMode !== 'local';
  if (remotePanel) remotePanel.hidden = engineMode !== 'nuxel';
  if ($('engine-mode')) $('engine-mode').value = engineMode;
  if ($('connection-status')) $('connection-status').textContent = connectionLabel();
}

if ($('api-url')) $('api-url').value = stored('nuxel-api-url') || API_DEFAULT;
if ($('api-token')) $('api-token').value = stored('nuxel-penguru-token');
if ($('connection-status')) $('connection-status').textContent = connectionLabel();
$('engine-mode').onchange = () => {
  saveStored('nuxel-engine-mode', $('engine-mode').value);
  location.reload();
};
$('connect').onclick = () => {
  let url = $('api-url').value.trim() || API_DEFAULT;
  if (!/^https?:\/\/[^\s]+$/i.test(url)) { $('connection-status').textContent = 'Enter an http(s) API URL.'; return; }
  url = url.replace(/\/+$/, '');
  saveStored('nuxel-api-url', url);
  const token = $('api-token').value.trim();
  saveStored('nuxel-penguru-token', token);
  if (token) {
    saveStored('nuxel-bridge-token', token);
    saveStored('nuxel-bridge-token-app', JSON.stringify({app_id: 'org.nuxel.PenGuru'}));
  } else {
    saveStored('nuxel-bridge-token', '');
    saveStored('nuxel-bridge-token-app', '');
  }
  location.reload();
};
$('forget').onclick = () => {
  for (const key of ['nuxel-api-url','nuxel-penguru-token','nuxel-bridge-token','nuxel-bridge-token-app']) saveStored(key, '');
  location.reload();
};

function renderPaths() {
  try {
    const paths = local.paths();
    if ($('storage-paths')) {
      $('storage-paths').textContent =
        'Models: ' + (paths.models || 'app storage/Models') + '\n' +
        'Runtimes: ' + (paths.runtimes || 'app storage/Runtimes') + '\n' +
        'Exports: Downloads/PenGuru';
    }
    if ($('models-path')) $('models-path').textContent = 'Storage on this phone: ' + (paths.models || 'app storage/Models');
  } catch (error) { /* storage paths are informational */ }
}
renderPaths();

const runtimeJobs = new Map();
let runtimeBulk = null;
let runtimeBulkPolling = false;

function pendingRuntimes(runtimes) {
  return runtimes.filter(runtime => !runtime.bundled && !runtime.installed);
}

const RUNTIME_STORAGE_RESERVE = 256 * 1024 * 1024;
function freeStorageBytes() {
  try {
    const host = window.NuxelAndroid;
    if (!host || typeof host.deviceInfo !== 'function') return 0;
    const info = JSON.parse(host.deviceInfo() || '{}');
    return Math.max(0, Number(info.free_storage) || 0);
  } catch (error) {
    return 0;
  }
}

function runtimeCard(runtime) {
  const article = document.createElement('article');
  article.className = 'card';
  const title = document.createElement('h4');
  title.textContent = runtime.name;
  const detail = document.createElement('p');
  detail.textContent = runtime.detail + ' · ' + (runtime.size_bytes / 1e6).toFixed(1) + ' MB';
  const status = document.createElement('p');
  status.setAttribute('role', 'status');
  status.textContent = runtime.installed ? 'Installed · ' + (runtime.installed_path || '') : 'Not installed';
  const progress = document.createElement('progress');
  progress.max = 1; progress.value = 0; progress.hidden = !runtime.installed ? true : false;
  if (runtime.installed) progress.value = 1;
  const button = document.createElement('button');
  button.type = 'button';
  button.textContent = runtime.installed ? 'Installed' : 'Install on this phone';
  button.disabled = !!runtime.installed;
  button.onclick = async () => {
    button.disabled = true;
    const confirmed = await confirmDownload({
      title: `Install ${runtime.name}?`,
      sizeBytes: runtime.size_bytes,
      packageCount: 1,
      detail: 'Runtime archive ' + runtime.filename + '.',
    });
    if (!confirmed) {
      button.disabled = !!runtime.installed;
      return;
    }
    status.textContent = 'Starting download…';
    try {
      const result = await call('install_runtime', {id: runtime.id});
      progress.hidden = false;
      runtimeJobs.set(result.job_id, {id: runtime.id, status, progress, button});
    } catch (error) {
      status.textContent = error.message;
      button.disabled = false;
    }
  };
  article.append(title, detail, button, progress, status);
  return article;
}

function renderRuntimeBulk(runtimes, message) {
  const host = $('runtimes-bulk');
  if (!host) return;
  const installable = runtimes.filter(runtime => !runtime.bundled);
  if (!installable.length) {
    host.replaceChildren();
    host.hidden = true;
    return;
  }
  host.hidden = false;
  if (runtimeBulk && runtimeBulk.running) return;
  host.replaceChildren();
  const total = sumBytes(installable, runtime => runtime.size_bytes);
  const todo = pendingRuntimes(runtimes);
  const todoBytes = sumBytes(todo, runtime => runtime.size_bytes);
  const free = freeStorageBytes();
  const fits = !todo.length || !free || free >= todoBytes + RUNTIME_STORAGE_RESERVE;
  const panel = document.createElement('article');
  panel.className = 'card bulk-panel';
  const heading = document.createElement('h4');
  heading.textContent = 'All on-device runtimes';
  const summary = document.createElement('p');
  summary.textContent = `Complete set: ${formatBytes(total)} across ${installable.length} runtimes. `
    + (todo.length ? `${formatBytes(todoBytes)} remains to install.` : 'Everything is installed.')
    + ' The bundled Whisper.cpp engine is already inside this APK.';
  panel.append(heading, summary);
  if (free > 0) {
    const storage = document.createElement('p');
    storage.textContent = `Free storage on this phone: ${formatBytes(free)}`
      + (fits ? '.' : ` — not enough for this install (${formatBytes(todoBytes + RUNTIME_STORAGE_RESERVE)} needed).`);
    panel.append(storage);
  }
  const warning = document.createElement('p');
  warning.className = 'hint bulk-warning';
  warning.textContent = 'Mobile-data warning: runtime archives can be hundreds of megabytes. '
    + 'On mobile data this can use up your allowance and may cost money. Wi-Fi is strongly recommended.';
  panel.append(warning);
  if (message) {
    const status = document.createElement('p');
    status.setAttribute('role', 'status');
    status.textContent = message;
    panel.append(status);
  }
  if (todo.length) {
    const button = document.createElement('button');
    button.type = 'button';
    button.className = 'primary';
    button.textContent = `Accept all & install remaining (${formatBytes(todoBytes)})`;
    button.disabled = !fits;
    if (!fits) button.title = 'Not enough free storage for all runtimes';
    button.onclick = () => startRuntimeBulk(runtimes).catch(error => {
      const status = document.createElement('p');
      status.textContent = error.message || String(error);
      panel.append(status);
    });
    panel.append(button);
  }
  host.append(panel);
}

function renderRuntimes(message) {
  if (!$('runtimes')) return;
  const container = $('runtimes');
  container.replaceChildren();
  if (engineMode !== 'local') {
    container.textContent = 'Runtime installation is available in On-device mode.';
    const host = $('runtimes-bulk');
    if (host) { host.replaceChildren(); host.hidden = true; }
    return;
  }
  const runtimes = local.runtimeCatalog();
  for (const runtime of runtimes) container.append(runtimeCard(runtime));
  renderRuntimeBulk(runtimes, message);
}

function showRuntimeBulkProgress() {
  const host = $('runtimes-bulk');
  if (!host) return null;
  host.hidden = false;
  host.replaceChildren();
  const panel = document.createElement('article');
  panel.className = 'card bulk-panel';
  const heading = document.createElement('h4');
  heading.textContent = 'Installing all on-device runtimes';
  const warning = document.createElement('p');
  warning.className = 'hint';
  warning.textContent = 'Keep this phone on Wi-Fi if possible. The foreground service keeps '
    + 'downloading when the screen turns off.';
  const progress = document.createElement('progress');
  progress.max = 1;
  progress.value = 0;
  const status = document.createElement('p');
  status.setAttribute('role', 'status');
  status.textContent = 'Starting downloads…';
  const cancel = document.createElement('button');
  cancel.type = 'button';
  cancel.textContent = 'Cancel all runtime downloads';
  cancel.onclick = async () => {
    cancel.disabled = true;
    status.textContent = 'Cancelling downloads…';
    for (const jobId of (runtimeBulk ? runtimeBulk.items.keys() : [])) {
      try { await call('cancel_download', {job_id: jobId}); } catch (error) { /* already stopped */ }
    }
  };
  panel.append(heading, warning, progress, status, cancel);
  host.append(panel);
  return {progress, status, cancel};
}

function runtimeBulkTotals() {
  let doneBytes = 0;
  let ready = 0;
  let failed = runtimeBulk ? runtimeBulk.startFailures : 0;
  let active = 0;
  for (const entry of (runtimeBulk ? runtimeBulk.items.values() : [])) {
    if (entry.state === 'ready') {
      ready += 1;
      doneBytes += entry.size;
    } else if (['error', 'quarantined', 'cancelled'].includes(entry.state)) {
      failed += 1;
    } else {
      active += 1;
      doneBytes += entry.progress * entry.size;
    }
  }
  return {doneBytes, ready, failed, active,
    progress: runtimeBulk && runtimeBulk.total ? Math.min(1, doneBytes / runtimeBulk.total) : 0};
}

function updateRuntimeBulkProgress() {
  if (!runtimeBulk || !runtimeBulk.ui) return;
  const totals = runtimeBulkTotals();
  runtimeBulk.ui.progress.value = totals.progress;
  runtimeBulk.ui.status.textContent = `${totals.ready} of ${runtimeBulk.totalCount} installed · `
    + `${Math.round(totals.progress * 100)}% · `
    + `${formatBytes(Math.max(0, runtimeBulk.total - totals.doneBytes))} left`
    + (totals.failed ? ` · ${totals.failed} failed` : '')
    + (totals.active ? ` · ${totals.active} active` : '');
}

async function finishRuntimeBulk() {
  if (!runtimeBulk || !runtimeBulk.running) return;
  runtimeBulk.running = false;
  const totals = runtimeBulkTotals();
  const finished = `Runtime install finished: ${totals.ready} installed`
    + (totals.failed ? `, ${totals.failed} failed.` : '.');
  if (runtimeBulk.ui) {
    runtimeBulk.ui.progress.value = 1;
    runtimeBulk.ui.status.textContent = finished;
    runtimeBulk.ui.cancel.hidden = true;
  }
  runtimeBulk = null;
  renderRuntimes(finished);
}

async function pollRuntimeBulk() {
  if (!runtimeBulk || !runtimeBulk.running || runtimeBulkPolling) return;
  runtimeBulkPolling = true;
  try {
    let settled = true;
    for (const [jobId, entry] of runtimeBulk.items) {
      if (['ready', 'error', 'quarantined', 'cancelled'].includes(entry.state)) continue;
      try {
        const result = await call('runtime_status', {job_id: jobId, id: entry.runtime.id});
        const job = result.job || {};
        entry.progress = Math.max(0, Math.min(1, Number(job.progress) || 0));
        if (['ready', 'error', 'quarantined', 'cancelled'].includes(job.state)) {
          entry.state = job.state;
          if (job.state === 'ready') entry.progress = 1;
        } else {
          settled = false;
        }
      } catch (error) {
        entry.state = 'error';
      }
    }
    updateRuntimeBulkProgress();
    if (settled) await finishRuntimeBulk();
  } finally {
    runtimeBulkPolling = false;
  }
}

async function startRuntimeBulk(runtimes) {
  if (runtimeBulk && runtimeBulk.running) return;
  const todo = pendingRuntimes(runtimes);
  if (!todo.length) return;
  const todoBytes = sumBytes(todo, runtime => runtime.size_bytes);
  const totalBytes = sumBytes(runtimes.filter(runtime => !runtime.bundled),
    runtime => runtime.size_bytes);
  const free = freeStorageBytes();
  if (free > 0 && free < todoBytes + RUNTIME_STORAGE_RESERVE) {
    renderRuntimes(`Not enough free storage for all runtimes: `
      + `${formatBytes(todoBytes + RUNTIME_STORAGE_RESERVE)} needed, ${formatBytes(free)} free.`);
    return;
  }
  const accepted = await confirmDownload({
    title: 'Install all on-device PenGuru runtimes?',
    sizeBytes: todoBytes,
    packageCount: todo.length,
    detail: `The complete runtime set is ${formatBytes(totalBytes)}. `
      + (free > 0 ? `Free storage on this phone: ${formatBytes(free)}. ` : '')
      + 'This installs llama.cpp, the Snapdragon build and ONNX Runtime in one go.',
  });
  if (!accepted) return;
  runtimeBulk = {
    running: true,
    total: todoBytes,
    totalCount: todo.length,
    startFailures: 0,
    items: new Map(),
    ui: showRuntimeBulkProgress(),
  };
  for (const runtime of todo) {
    try {
      const result = await call('install_runtime', {id: runtime.id});
      if (result.bundled) continue;
      if (!result.job_id) throw new Error('Download did not start');
      runtimeBulk.items.set(result.job_id, {
        runtime,
        size: Number(runtime.size_bytes) || 0,
        state: 'downloading',
        progress: 0,
      });
    } catch (error) {
      runtimeBulk.startFailures += 1;
      if (runtimeBulk.ui) runtimeBulk.ui.status.textContent = 'Could not start '
        + runtime.name + ': ' + error.message;
    }
  }
  updateRuntimeBulkProgress();
  if (!runtimeBulk.items.size) await finishRuntimeBulk();
}

if (engineMode === 'local') renderRuntimes();

$('refresh-storage').onclick = () => {
  renderPaths();
  renderRuntimes();
  refresh().catch(error => notice(error.message));
};

const library = modelLibrary($('cards'), call);
const voice = voiceControls(call, () => !request, (text, auto, meta) =>
  autoSendText(text, Object.assign({auto}, meta || {})));
const talkback = talkbackControls();
window.addEventListener('penguru:transcript-ready', () => page('chat'));

// A voice command heard by the persistent SonarBird listener (for example
// "Penguru stop" or "Penguru cancel") controls the foreground conversation too.
window.__penguruVoiceCommand = command => {
  const value = String(command || '').toLowerCase();
  if (value === 'stop' || value === 'cancel') {
    voice.stop().catch(() => {});
    if (request) call('cancel', {request_id: request}).catch(() => {});
    notice(value === 'stop' ? 'Stopped by voice command.' : 'Cancelled by voice command.');
    page('chat');
    return true;
  }
  if (value === 'send') {
    const text = $('prompt').value.trim();
    if (text) sendMessage(text).catch(error => notice(error.message));
    return true;
  }
  return false;
};

/* ------------------------------------------------ speech engine selection */

function populateSpeechEngines() {
  const select = $('speech-engine');
  if (!select || document.activeElement === select) return;
  const host = window.NuxelAndroid;
  if (!host || typeof host.speechEngines !== 'function') {
    select.replaceChildren();
    const option = document.createElement('option');
    option.value = '';
    option.textContent = 'Automatic · local Whisper when installed';
    select.append(option);
    if ($('speech-engine-status')) {
      $('speech-engine-status').textContent = 'Speech-engine selection is available in the Android APK.';
    }
    return;
  }
  let engines = [];
  try {
    const raw = host.speechEngines();
    const parsed = JSON.parse(raw || '[]');
    if (Array.isArray(parsed)) engines = parsed;
  } catch (error) { /* keep the default entry */ }
  if (!engines.length) engines = [{component: '', label: 'Automatic · local Whisper when installed', default: true}];
  const current = wakeJson(host.speechConfig && host.speechConfig()).engine || '';
  select.replaceChildren();
  for (const engine of engines) {
    const option = document.createElement('option');
    option.value = engine.component || '';
    option.textContent = engine.label || engine.component || 'System default recognizer';
    select.append(option);
  }
  select.value = current;
  select.onchange = () => {
    if (typeof host.speechConfigure === 'function') {
      host.speechConfigure(JSON.stringify({engine: select.value}));
    }
    if ($('speech-engine-status')) {
      $('speech-engine-status').textContent = select.value === 'system'
        ? 'Using the phone\'s system default recognizer.'
        : select.value
          ? 'Selected recognizer: ' + (select.selectedOptions[0]?.textContent || select.value)
          : 'Automatic: PenGuru records locally when the Whisper model is installed, otherwise it uses the phone\'s recognizer.';
    }
  };
  if ($('speech-engine-status')) {
    $('speech-engine-status').textContent = engines.length > 1
      ? engines.length + ' speech engines found. The bundled Whisper engine works offline; GrapheneOS / Google / vendor recognizers can also be chosen.'
      : 'Only the system default recognizer was found. Install a speech-recognition service to add more choices.';
  }
}

function updateVoiceDiagnostics() {
  const host = window.NuxelAndroid;
  if (!$('voice-diagnostics')) return;
  if (!host || typeof host.voiceDiagnostics !== 'function') {
    $('voice-diagnostics').textContent = 'VAD and noise diagnostics are available in the Android APK.';
    return;
  }
  const state = wakeJson(host.voiceDiagnostics());
  const noise = state.noise_suppressor ? 'Android NoiseSuppressor on'
    : state.noise_mode === 'off' ? 'noise suppression off' : 'noise suppression unavailable';
  const silero = state.native_silero_installed ? 'Silero VAD package installed'
    : 'Silero VAD package not installed';
  const rnnoise = state.native_rnnoise_installed ? 'RNNoise package installed'
    : 'RNNoise package not installed';
  const whisper = state.whisper_ready
    ? 'Whisper offline engine ready'
    : 'Whisper offline engine needs the tiny.en model';
  $('voice-diagnostics').textContent = [
    'VAD: ' + (state.vad || 'off') + ' · end-of-speech ' + ((state.end_silence_ms || 0) / 1000).toFixed(2) + ' s',
    noise,
    state.acoustic_echo_canceler ? 'echo cancellation available' : 'no echo cancellation',
    state.automatic_gain_control ? 'AGC available' : 'no AGC',
    silero,
    rnnoise,
    whisper,
    state.engine ? 'speech engine: ' + state.engine : 'speech engine: system default'
  ].join(' · ');
}

if ($('speech-engine')) {
  populateSpeechEngines();
  setInterval(updateVoiceDiagnostics, 4000);
  setInterval(populateSpeechEngines, 8000);
  updateVoiceDiagnostics();
}

async function call(op, params = {}) {
  if (engineMode === 'local') {
    let result;
    try {
      result = await local.call(op, params);
    } catch (error) {
      throw new Error(String(error && error.message || error));
    }
    if (!result || result.ok !== true) throw new Error(result?.detail || result?.error || 'On-device engine is unavailable');
    return result;
  }
  let r;
  try {
    r = await bridge.call('penguru', op, params);
  } catch (error) {
    const text = String(error && error.message || error);
    if (text.includes('launcher_token_required')) {
      throw new Error('Launcher token required. Open Settings → Connection and paste a freshly minted token.');
    }
    if (error && error.status === 401) {
      throw new Error('The bridge rejected the launcher token (expired or revoked). Re-mint it and reconnect in Settings → Connection.');
    }
    throw error;
  }
  if (!r || r.ok !== true) throw new Error(r?.detail || r?.error || 'PenGuru is unavailable');
  return r;
}

function notice(text) { $('notice').textContent = text; }
function page(name) {
  for (const id of ['chat','models','settings','diagnostics']) $(id).hidden = id !== name;
  document.querySelectorAll('[data-page]').forEach(b => b.setAttribute('aria-current', String(b.dataset.page === name)));
}
document.querySelectorAll('[data-page]').forEach(b => b.onclick = () => page(b.dataset.page));

function message(role, text) {
  const el = document.createElement('article'); el.className = 'message ' + role;
  const meta = document.createElement('div'); meta.className = 'meta'; meta.textContent = role === 'user' ? 'You' : 'PenGuru';
  const pre = document.createElement('pre'); pre.textContent = text; el.append(meta, pre); $('messages').append(el);
  try { el.scrollIntoView({block: 'end', behavior: 'smooth'}); } catch (error) { /* older WebView */ }
  return {meta, pre};
}

// Voice transcripts and background wake-word commands are sent immediately.
// Nothing is left waiting in the textarea: the user asked for hands-free use.
const ASSISTANT_MODES = ['squad', 'chatbird', 'codebird'];

// A spoken "Penguru chat" / "Penguru code" forces the matching assistant mode.
async function applyMode(name) {
  const mode = ASSISTANT_MODES.includes(name) ? name : '';
  if (!mode) return '';
  if ($('mode')) $('mode').value = mode;
  try {
    await call('set_mode', {mode});
  } catch (error) {
    notice(error.message);
  }
  return mode;
}

async function sendMessage(rawText, options = {}) {
  const text = String(rawText || '').trim();
  if (!text || request) return false;
  if (!enabled) {
    try {
      await call('set_enabled', {enabled: true});
      await refresh();
    } catch (error) {
      notice(error.message);
      return false;
    }
  }
  try { await voice.stop(); } catch (error) { /* already closed */ }
  $('prompt').value = text;
  page('chat');
  try {
    message('user', text);
    currentReply = message('assistant', 'Routing…');
    const override = Object.prototype.hasOwnProperty.call(options, 'routeOverride')
      ? options.routeOverride : ($('route').value || null);
    const r = await call('submit', {text, route_override: override});
    request = r.request_id;
    $('prompt').value = '';
    $('cancel').disabled = false;
    $('send').disabled = true;
    if (options.auto) {
      notice(options.heard ? `Heard “${options.heard}” · sent automatically` : 'Sent automatically');
    }
    return true;
  } catch (error) {
    notice(error.message);
    if (currentReply) currentReply.pre.textContent = error.message;
    return false;
  }
}

let ready = false;
const queuedVoice = [];
async function autoSendText(text, meta = {}) {
  const value = String(text || '').trim();
  const mode = ASSISTANT_MODES.includes(meta.mode) ? meta.mode : '';
  if (!ready) { queuedVoice.push({value, meta}); return false; }
  if (mode) await applyMode(mode);
  if (!value) {
    if (mode) {
      notice(modeLabel(mode) + ' selected' + (meta.heard ? ' by voice' : '') + '.');
      page('chat');
      return true;
    }
    return false;
  }
  const options = Object.assign({auto: true}, meta);
  if (mode) {
    options.routeOverride = mode === 'codebird' ? 'CODE'
      : mode === 'chatbird' ? 'CHAT' : null;
  }
  return sendMessage(value, options);
}
// MainActivity forwards commands recognised by the persistent background
// SonarBird listener into this hook. mode is "" for an ordinary message, or
// "chatbird"/"codebird" when the owner said "Penguru chat"/"Penguru code".
window.__penguruWakeCommand = (text, mode) => { autoSendText(text, {heard: text || '', mode}); };
window.__penguruWakeStatus = text => {
  const el = $('wake-service-status');
  if (el) el.textContent = text;
  const live = $('wake-live');
  if (live) { live.hidden = false; live.textContent = text; }
};
// Activity may have delivered a wake command before this module finished
// parsing. Drain that tiny hand-off queue now.
if (Array.isArray(window.__penguruWakeQueue)) {
  for (const item of window.__penguruWakeQueue.splice(0)) {
    if (item && typeof item === 'object') {
      window.__penguruWakeCommand(item.text || '', item.mode || '');
    } else {
      window.__penguruWakeCommand(item, '');
    }
  }
}

async function refresh() {
  const r = await call('status'); const s = r.status;
  enabled = s.enabled; $('power').textContent = enabled ? 'Turn PenGuru off' : 'Enable PenGuru';
  $('send').disabled = !enabled || !!request; $('mode').disabled = $('runtime').disabled = !enabled;
  $('mode').value = s.mode || 'squad'; $('runtime').value = s.runtime_preference || 'auto';
  notice(enabled
    ? `${s.state} · ${s.engine || 'No model loaded'} · CPU · local only`
    : 'PenGuru is OFF. Enable it to manage models and start a conversation.');
  library.render(s.models || [], enabled, s.per_model_engine || {});
}

$('power').onclick=async()=>{try{await voice.stop();await call('set_enabled',{enabled:!enabled});request=null;$('cancel').disabled=true;await refresh();}catch(e){notice(e.message);}};
$('mode').onchange=()=>applyMode($('mode').value).catch(e=>notice(e.message));
$('runtime').onchange=()=>call('set_runtime',{preference:$('runtime').value}).catch(e=>notice(e.message));
$('compose').onsubmit=e=>{e.preventDefault();sendMessage($('prompt').value).catch(err=>notice(err.message));};
$('cancel').onclick=()=>request&&call('cancel',{request_id:request}).catch(e=>notice(e.message));
$('clear').onclick=async()=>{try{if(request)await call('cancel',{request_id:request});await call('clear_all');request=null;lastOutput='';$('messages').replaceChildren();$('cancel').disabled=true;$('send').disabled=!enabled;}catch(e){notice(e.message);}};
$('export').onclick=()=>{if(!lastOutput){notice('No response to export yet.');return;}const filename='penguru-response.txt';const host=window.NuxelAndroid;if(host&&typeof host.saveText==='function'){try{const saved=host.saveText(filename,lastOutput);notice(saved?'Response saved to '+saved:'Could not save the response.');return;}catch(e){notice('Could not save the response: '+e.message);return;}}const a=document.createElement('a');a.href=URL.createObjectURL(new Blob([lastOutput],{type:'text/plain'}));a.download=filename;a.click();setTimeout(()=>URL.revokeObjectURL(a.href),1000);};
$('refresh').onclick=async()=>{try{$('details').textContent=JSON.stringify(await call('diagnostics'),null,2);}catch(e){notice(e.message);}};

let polling=false;
setInterval(async()=>{if(polling)return;polling=true;try{
  if(request){
    const owner=request;
    const r=(await call('get',{request_id:owner})).request;
    currentReply.meta.textContent=[r.route,r.reason_code,r.confidence!=null?Math.round(r.confidence*100)+'%':'',r.engine,r.variant_id,r.revision].filter(Boolean).join(' · ');
    lastOutput=r.output||'';
    currentReply.pre.textContent=r.output||r.error||(r.status==='awaiting_user'?'Please clarify, or choose CHAT or CODE and send again.':r.status);
    // Talkback reads each completed answer once, even if polling sees it again.
    if(r.status==='done'&&r.output&&spokenRequest!==owner){spokenRequest=owner;talkback.speak(r.output);}
    if(['done','error','cancelled','awaiting_user'].includes(r.status)){request=null;$('cancel').disabled=true;$('send').disabled=!enabled;}
  }
  if(engineMode==='local'&&runtimeJobs.size){for(const [jobId,view] of runtimeJobs){try{const r=await call('runtime_status',{job_id:jobId,id:view.id});const job=r.job;view.progress.value=job.progress||0;view.status.textContent=`${job.state} · ${Math.round((job.progress||0)*100)}% · ${job.detail||''}`;if(['ready','error','cancelled','quarantined'].includes(job.state)){runtimeJobs.delete(jobId);if(job.state==='ready'){view.button.textContent='Installed';view.button.disabled=true;}else{view.button.disabled=false;}}}catch(e){view.status.textContent=e.message;runtimeJobs.delete(jobId);}}}
  if(engineMode==='local'&&runtimeBulk&&runtimeBulk.running){await pollRuntimeBulk();}
}catch(e){notice(e.message);}finally{polling=false;}},1000);

/* ---------------------------------------------- persistent wake listening */

const androidWake = window.NuxelAndroid;
function wakeJson(raw) {
  try { return JSON.parse(raw || '{}'); } catch (error) { return {}; }
}
function updateWakePanel() {
  const start = $('wake-service-start'), stop = $('wake-service-stop');
  if (!start || !stop) return;
  if (!androidWake || typeof androidWake.startWakeWordService !== 'function') {
    start.disabled = stop.disabled = true;
    $('wake-service-status').textContent = 'Background listening is available in the Android APK.';
    return;
  }
  const state = wakeJson(androidWake.wakeServiceStatus && androidWake.wakeServiceStatus());
  const running = !!state.running;
  start.disabled = running;
  stop.disabled = !running;
  let summary;
  if (running) {
    const partial = state.last_partial ? ` · heard “${state.last_partial}”` : '';
    const heard = state.last_heard ? ` · last heard “${state.last_heard}”` : '';
    const error = state.last_error ? ` · ${state.last_error}` : '';
    const endpoint = state.vad ? ` · VAD ${state.vad}` : '';
    if (state.in_app_speech) {
      summary = 'SonarBird is paused while the in-app microphone is recording. It resumes automatically.';
    } else if (state.handoff) {
      summary = 'SonarBird heard your request and is sending it to the conversation…';
    } else if (state.command_pending) {
      summary = 'SonarBird is hearing your sentence' + partial + ' · it sends when you stop talking' + endpoint;
    } else if (state.listening) {
      summary = 'SonarBird is listening for “Penguru” · persistent notification active' + heard + error + endpoint;
    } else if (state.paused) {
      summary = 'SonarBird is reopening the speech session…' + heard + error;
    } else {
      summary = 'SonarBird is starting the speech session…' + heard + error;
    }
  } else if (state.error) {
    summary = state.error;
  } else {
    summary = 'Background listening is off. Start it once; it keeps listening while the screen is off.';
  }
  $('wake-service-status').textContent = summary;
  const live = $('wake-live');
  if (live) {
    live.hidden = !running;
    live.textContent = running ? summary : '';
  }
}

function updatePermissionPanel() {
  if (!$('permission-status')) return;
  if (!androidWake || typeof androidWake.permissionStatus !== 'function') {
    $('permission-status').textContent = 'Android permission checks are available in the APK.';
    if ($('battery-exempt')) $('battery-exempt').disabled = true;
    return;
  }
  const state = wakeJson(androidWake.permissionStatus());
  const lines = [
    'Microphone: ' + (state.microphone ? 'granted' : 'not granted'),
    'Notifications: ' + (state.notifications ? 'granted' : 'not granted'),
    'Battery optimization: ' + (state.battery_optimized ? 'ON · Android may stop background work' : 'off · protected'),
    'Reinstall-safe storage: ' + (state.all_files_access
      ? 'on · ' + (state.storage_root || 'Download/PenGuru')
      : 'off · allow All files access to reuse downloads'),
  ];
  $('permission-status').textContent = lines.join(' · ');
  if ($('battery-exempt')) {
    $('battery-exempt').disabled = !state.battery_optimized;
    $('battery-exempt').textContent = state.battery_optimized
      ? 'Disable battery optimization' : 'Battery optimization disabled';
  }
  if ($('all-files-access')) {
    $('all-files-access').disabled = !!state.all_files_access;
    $('all-files-access').textContent = state.all_files_access
      ? 'All files access enabled' : 'Allow all files access';
  }
  if ($('background-status')) {
    const active = Array.isArray(state.downloads) ? state.downloads
      : (typeof state.downloads === 'string' ? wakeJson(state.downloads) : []);
    $('background-status').textContent = active.length
      ? `${active.length} download${active.length === 1 ? '' : 's'} running in the background · the screen can turn off safely.`
      : 'No download is running in the background right now.';
  }
}
if ($('wake-service-start')) {
  $('wake-service-start').onclick = () => {
    try {
      androidWake.startWakeWordService();
      $('wake-service-status').textContent = 'Requesting microphone and notification permission…';
    } catch (error) { notice(error.message); }
    setTimeout(updateWakePanel, 400);
  };
  $('wake-service-stop').onclick = () => {
    try { androidWake.stopWakeWordService(); } catch (error) { notice(error.message); }
    setTimeout(updateWakePanel, 300);
  };
  if ($('permission-request')) {
    $('permission-request').onclick = () => {
      try {
        androidWake.requestAppPermissions();
        $('permission-status').textContent = 'Requesting Android permissions…';
      } catch (error) { notice(error.message); }
      setTimeout(updatePermissionPanel, 600);
    };
  }
  if ($('battery-exempt')) {
    $('battery-exempt').onclick = () => {
      try {
        androidWake.requestBatteryExemption();
        $('background-status').textContent = 'Choose PenGuru Squad in the Android battery optimization screen and allow background activity.';
      } catch (error) { notice(error.message); }
    };
  }
  if ($('all-files-access')) {
    $('all-files-access').onclick = () => {
      try {
        androidWake.requestAllFilesAccess();
        $('background-status').textContent = 'Enable All files access for PenGuru Squad, then return to the app. Existing downloads will be reused instead of fetched again.';
      } catch (error) { notice(error.message); }
    };
  }
  setInterval(updateWakePanel, 2000);
  setInterval(updatePermissionPanel, 3000);
  updateWakePanel();
  updatePermissionPanel();
}

/* --------------------------------------------------------------- talkback */

function syncTalkbackControls() {
  const enabledBox = $('talkback-toggle');
  const settingsBox = $('talkback-enabled');
  const on = talkback.state.enabled;
  if (enabledBox) enabledBox.checked = on;
  if (settingsBox) settingsBox.checked = on;
  if ($('talkback-status')) {
    const status = talkback.status();
    let text;
    if (status.browser) text = 'Browser speech synthesis talkback is available.';
    else if (status.ready) text = 'Android talkback ready · ' + (status.engine || 'system default engine');
    else if (status.available) text = 'Android talkback is starting…';
    else text = 'No Android talkback engine found. Install one in Android Settings → Accessibility → Text-to-speech.';
    if (status.error) text += ' · ' + status.error;
    if (status.speaking) text += ' · speaking';
    $('talkback-status').textContent = text;
  }
}

function populateTalkbackEngines() {
  const select = $('talkback-engine');
  if (!select) return;
  const current = talkback.state.engine;
  const engines = talkback.engines();
  const choices = engines.length ? engines : [{name: '', label: 'System default engine'}];
  select.replaceChildren();
  for (const engine of choices) {
    const option = document.createElement('option');
    option.value = engine.name || '';
    option.textContent = engine.label || engine.name || 'System default engine';
    select.append(option);
  }
  select.value = current;
  select.onchange = () => talkback.setEngine(select.value);
}

talkback.onChange(syncTalkbackControls);
for (const id of ['talkback-toggle', 'talkback-enabled']) {
  if ($(id)) $(id).onchange = () => talkback.setEnabled($(id).checked);
}
if ($('talkback-rate')) {
  $('talkback-rate').value = String(talkback.state.rate);
  $('talkback-rate').oninput = () => talkback.setRate($('talkback-rate').value);
}
if ($('talkback-pitch')) {
  $('talkback-pitch').value = String(talkback.state.pitch);
  $('talkback-pitch').oninput = () => talkback.setPitch($('talkback-pitch').value);
}
if ($('talkback-test')) {
  $('talkback-test').onclick = () => {
    if (!talkback.state.enabled) talkback.setEnabled(true);
    talkback.speak('PenGuru talkback is ready. This is what an answer sounds like.');
  };
}
if ($('talkback-stop')) $('talkback-stop').onclick = () => talkback.stop();
window.__nuxelTalkbackState = state => {
  if (state === 'speaking' && $('talkback-status')) $('talkback-status').textContent = 'Talkback is speaking…';
  else syncTalkbackControls();
};
populateTalkbackEngines();
syncTalkbackControls();
setInterval(syncTalkbackControls, 2500);
setTimeout(populateTalkbackEngines, 1500);
setTimeout(populateTalkbackEngines, 5000);

applyEngineMode();
page(location.hash==='#models'?'models':location.hash==='#settings'?'settings':'chat');
refresh().catch(e=>notice(e.message)).finally(() => {
  ready = true;
  for (const item of queuedVoice.splice(0)) autoSendText(item.value, item.meta);
});
