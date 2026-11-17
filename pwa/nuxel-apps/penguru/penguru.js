import {bridge} from '../../nuxel-common/bridge.js';
const $ = id => document.getElementById(id);
let enabled = false, request = null, lastOutput = '', currentReply = null;
const jobs = new Map();
const esc = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
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
  renderCards(s.models || []);
}
function renderCards(cards) {
  $('cards').replaceChildren();
  if (!enabled) { $('cards').textContent = 'Enable PenGuru to inspect and download model packages.'; return; }
  for (const card of cards) {
    const box = document.createElement('article'); box.className = 'card';
    box.innerHTML = `<h3>${esc(card.name || ({sonarbird:'SonarBird',chatbird:'ChatBird',codebird:'CodeBird'}[card.model_id]))}</h3>`;
    if (!card.variants.length) box.innerHTML += '<p>Deterministic routing is available in Squad mode. No approved encoder + classifier bundle is published for download.</p><button disabled>Hugging Face package unavailable</button>';
    for (const v of card.variants) {
      const area = document.createElement('div');
      area.innerHTML = `<p>${esc(v.format)} · ${esc(v.quantization)} · ${(v.size_bytes/1e9).toFixed(2)} GB · ${esc(v.engine)}</p><p><a target="_blank" rel="noopener noreferrer" href="https://huggingface.co/${esc(v.source_repo)}">${esc(v.source_repo)}</a></p><p class="revision">Revision ${esc(v.source_revision)}</p><p><strong>${esc(v.status)}</strong> — ${esc(v.detail)}</p><details><summary>Files, integrity &amp; license</summary><pre>${esc(JSON.stringify(v.files,null,2))}</pre><p>${esc(v.license.spdx)}: ${esc(v.license.notice)}</p><p>Redistribution review: ${esc(v.license.provenance_review)}</p></details>`;
      const ack = document.createElement('label'); const check = document.createElement('input'); check.type='checkbox'; ack.append(check,document.createTextNode(' I have reviewed the license and provenance notice for this revision.'));
      const download = document.createElement('button'); download.textContent = v.status === 'ready' ? 'Verified & ready' : v.status === 'verified_signed' ? 'Verify installed model' : 'Download from Hugging Face'; download.disabled = true;
      check.onchange = () => download.disabled = !check.checked || v.status === 'ready';
      const progress = document.createElement('progress'); progress.max=1; progress.value=0; progress.hidden=true;
      const state = document.createElement('p'); state.setAttribute('role','status');
      const cancel = document.createElement('button'); cancel.textContent='Cancel download'; cancel.hidden=true;
      download.onclick = async () => {
        try { download.disabled=true; const r=await call('start_download',{model_id:card.model_id,variant_id:v.variant_id,license_accepted:check.checked,license_revision:v.source_revision}); jobs.set(r.job_id,{progress,state,cancel,download}); progress.hidden=false;cancel.hidden=false; cancel.onclick=()=>call('cancel_download',{job_id:r.job_id}).catch(e=>notice(e.message)); }
        catch(e){state.textContent=e.message;download.disabled=false;}
      };
      const remove=document.createElement('button');remove.textContent='Delete package'; remove.disabled=v.status==='not_installed';remove.onclick=async()=>{if(!confirm(`Delete ${card.model_id} ${v.variant_id} from this device?`))return;try{await call('delete_model',{model_id:card.model_id,variant_id:v.variant_id});await refresh();}catch(e){notice(e.message);}};
      const override=document.createElement('select');override.setAttribute('aria-label',card.model_id+' runtime override');override.innerHTML='<option value="inherit">Inherit global runtime</option><option value="llama.cpp">llama.cpp</option><option value="onnxruntime-genai">ORT GenAI</option>';override.onchange=()=>call('set_runtime',{model_id:card.model_id,engine:override.value}).catch(e=>notice(e.message));
      area.append(ack,download,remove,cancel,progress,state,override);box.append(area);
    }
    $('cards').append(box);
  }
}
$('power').onclick=async()=>{try{await call('set_enabled',{enabled:!enabled});request=null; jobs.clear();$('cancel').disabled=true;await refresh();}catch(e){notice(e.message);}};
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
  for(const [id,ui] of jobs){const j=(await call('download_status',{job_id:id})).job;ui.progress.value=j.progress;ui.state.textContent=`${j.state}: ${Math.round(j.progress*100)}% — ${j.detail||''}`;if(['ready','error','quarantined','cancelled'].includes(j.state)){jobs.delete(id);ui.cancel.hidden=true;ui.download.disabled=false;if(j.state==='ready')await refresh();}}
}catch(e){notice(e.message);}finally{polling=false;}},1000);
page(location.hash==='#models'?'models':location.hash==='#settings'?'settings':'chat');
refresh().catch(e=>notice(e.message));
