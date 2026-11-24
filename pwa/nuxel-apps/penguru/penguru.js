import {voiceControls} from './voice.js';
import {bridge} from '../../nuxel-common/bridge.js';
import {modelLibrary} from './model-library.js';
import {createLocalEngine} from './local-engine.js';

const $ = id => document.getElementById(id);
let enabled = false, request = null, lastOutput = '', currentReply = null;
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

function renderRuntimes() {
  if (!$('runtimes')) return;
  const container = $('runtimes');
  container.replaceChildren();
  if (engineMode !== 'local') {
    container.textContent = 'Runtime installation is available in On-device mode.';
    return;
  }
  for (const runtime of local.runtimeCatalog()) container.append(runtimeCard(runtime));
}

if (engineMode === 'local') renderRuntimes();
$('refresh-storage').onclick = () => {
  renderPaths();
  renderRuntimes();
  refresh().catch(error => notice(error.message));
};

const library = modelLibrary($('cards'), call);
const voice = voiceControls(call, () => enabled && !request, text => { $('prompt').value = text; page('chat'); $('prompt').focus(); });

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
  return {meta, pre};
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
$('mode').onchange=()=>call('set_mode',{mode:$('mode').value}).catch(e=>notice(e.message));
$('runtime').onchange=()=>call('set_runtime',{preference:$('runtime').value}).catch(e=>notice(e.message));
$('compose').onsubmit=async e=>{e.preventDefault();if(request)return;await voice.stop();const text=$('prompt').value.trim();if(!text)return;try{message('user',text);currentReply=message('assistant','Routing…');const r=await call('submit',{text,route_override:$('route').value||null});request=r.request_id;$('prompt').value='';$('cancel').disabled=false;$('send').disabled=true;}catch(err){notice(err.message);}};
$('cancel').onclick=()=>request&&call('cancel',{request_id:request}).catch(e=>notice(e.message));
$('clear').onclick=async()=>{try{if(request)await call('cancel',{request_id:request});await call('clear_all');request=null;lastOutput='';$('messages').replaceChildren();$('cancel').disabled=true;$('send').disabled=!enabled;}catch(e){notice(e.message);}};
$('export').onclick=()=>{if(!lastOutput){notice('No response to export yet.');return;}const filename='penguru-response.txt';const host=window.NuxelAndroid;if(host&&typeof host.saveText==='function'){try{const saved=host.saveText(filename,lastOutput);notice(saved?'Response saved to '+saved:'Could not save the response.');return;}catch(e){notice('Could not save the response: '+e.message);return;}}const a=document.createElement('a');a.href=URL.createObjectURL(new Blob([lastOutput],{type:'text/plain'}));a.download=filename;a.click();setTimeout(()=>URL.revokeObjectURL(a.href),1000);};
$('refresh').onclick=async()=>{try{$('details').textContent=JSON.stringify(await call('diagnostics'),null,2);}catch(e){notice(e.message);}};

let polling=false;
setInterval(async()=>{if(polling)return;polling=true;try{
  if(request){const r=(await call('get',{request_id:request})).request;currentReply.meta.textContent=[r.route,r.reason_code,r.confidence!=null?Math.round(r.confidence*100)+'%':'',r.engine,r.variant_id,r.revision].filter(Boolean).join(' · ');lastOutput=r.output||'';currentReply.pre.textContent=r.output||r.error||(r.status==='awaiting_user'?'Please clarify, or choose CHAT or CODE and send again.':r.status);if(['done','error','cancelled','awaiting_user'].includes(r.status)){request=null;$('cancel').disabled=true;$('send').disabled=!enabled;}}
  if(engineMode==='local'&&runtimeJobs.size){for(const [jobId,view] of runtimeJobs){try{const r=await call('runtime_status',{job_id:jobId,id:view.id});const job=r.job;view.progress.value=job.progress||0;view.status.textContent=`${job.state} · ${Math.round((job.progress||0)*100)}% · ${job.detail||''}`;if(['ready','error','cancelled','quarantined'].includes(job.state)){runtimeJobs.delete(jobId);if(job.state==='ready'){view.button.textContent='Installed';view.button.disabled=true;}else{view.button.disabled=false;}}}catch(e){view.status.textContent=e.message;runtimeJobs.delete(jobId);}}}
}catch(e){notice(e.message);}finally{polling=false;}},1000);

applyEngineMode();
page(location.hash==='#models'?'models':location.hash==='#settings'?'settings':'chat');
refresh().catch(e=>notice(e.message));
