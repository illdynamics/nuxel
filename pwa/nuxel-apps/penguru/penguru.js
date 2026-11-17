import {bridge} from '../../nuxel-common/bridge.js';
import {modelLibrary} from '../settings/penguru-models.js';
const $ = id => document.getElementById(id);
let enabled = false, request = null, lastOutput = '', currentReply = null;
const library = modelLibrary($('cards'), call);
async function call(op, params = {}) {
  const r = await bridge.call('penguru', op, params);
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
  notice(enabled ? `${s.state} · ${s.engine || 'No model loaded'} · CPU · local only` : 'PenGuru is OFF. Enable it to manage models and start a conversation.');
  library.render(s.models || [], enabled, s.per_model_engine || {});
}
$('power').onclick=async()=>{try{await call('set_enabled',{enabled:!enabled});request=null;$('cancel').disabled=true;await refresh();}catch(e){notice(e.message);}};
$('mode').onchange=()=>call('set_mode',{mode:$('mode').value}).catch(e=>notice(e.message));
$('runtime').onchange=()=>call('set_runtime',{preference:$('runtime').value}).catch(e=>notice(e.message));
$('compose').onsubmit=async e=>{e.preventDefault();if(request)return;const text=$('prompt').value.trim();if(!text)return;try{message('user',text);currentReply=message('assistant','Routing…');const r=await call('submit',{text,route_override:$('route').value||null});request=r.request_id;$('prompt').value='';$('cancel').disabled=false;$('send').disabled=true;}catch(err){notice(err.message);}};
$('cancel').onclick=()=>request&&call('cancel',{request_id:request}).catch(e=>notice(e.message));
$('clear').onclick=async()=>{try{if(request)await call('cancel',{request_id:request});await call('clear_all');request=null;lastOutput='';$('messages').replaceChildren();$('cancel').disabled=true;$('send').disabled=!enabled;}catch(e){notice(e.message);}};
$('export').onclick=()=>{if(!lastOutput){notice('No response to export yet.');return;}const a=document.createElement('a');a.href=URL.createObjectURL(new Blob([lastOutput],{type:'text/plain'}));a.download='penguru-response.txt';a.click();setTimeout(()=>URL.revokeObjectURL(a.href),1000);};
$('refresh').onclick=async()=>{try{$('details').textContent=JSON.stringify(await call('diagnostics'),null,2);}catch(e){notice(e.message);}};
let polling=false;
setInterval(async()=>{if(polling)return;polling=true;try{
  if(request){const r=(await call('get',{request_id:request})).request;currentReply.meta.textContent=[r.route,r.reason_code,r.confidence!=null?Math.round(r.confidence*100)+'%':'',r.engine,r.variant_id,r.revision].filter(Boolean).join(' · ');lastOutput=r.output||'';currentReply.pre.textContent=r.output||r.error||(r.status==='awaiting_user'?'Please clarify, or choose CHAT or CODE and send again.':r.status);if(['done','error','cancelled','awaiting_user'].includes(r.status)){request=null;$('cancel').disabled=true;$('send').disabled=!enabled;}}
}catch(e){notice(e.message);}finally{polling=false;}},1000);
page(location.hash==='#models'?'models':location.hash==='#settings'?'settings':'chat');
refresh().catch(e=>notice(e.message));
