import {bridge} from '../../nuxel-common/bridge.js';
import {modelLibrary} from './penguru-models.js';
const $=id=>document.getElementById('penguru-'+id);let enabled=false;
async function call(op,params={}){const r=await bridge.call('penguru',op,params);if(!r?.ok)throw Error(r?.detail||r?.error||'Unavailable');return r;}
const library = modelLibrary($('models'), call);
async function refresh(){try{const s=(await call('status')).status;enabled=s.enabled;$('toggle').textContent=enabled?'Turn PenGuru off':'Enable PenGuru';$('mode').disabled=$('runtime').disabled=!enabled;$('mode').value=s.mode||'squad';$('runtime').value=s.runtime_preference||'auto';$('status').textContent=enabled?s.state+' · CPU · local only':'OFF — services and microphone stopped';library.render(s.models||[],enabled,s.per_model_engine||{});}catch(e){$('status').textContent=e.message;}}
$('toggle').onclick=async()=>{try{await call('set_enabled',{enabled:!enabled});await refresh();}catch(e){$('status').textContent=e.message;}};
$('mode').onchange=()=>call('set_mode',{mode:$('mode').value}).catch(e=>$('status').textContent=e.message);
$('runtime').onchange=()=>call('set_runtime',{preference:$('runtime').value}).catch(e=>$('status').textContent=e.message);
$('refresh').onclick=refresh;
document.querySelector('[data-tab="penguru"]').addEventListener('click',refresh);
