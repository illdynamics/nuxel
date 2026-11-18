// Shared Beak configuration and artifact staging. No microphone opens here.
export function mountBeak(container, call) {
  const fields = [
    ['asr_backend','Speech recognition', [['qwen','Qwen 0.6B (requires verified ARM64 runtime)'],['whisper','Whisper tiny.en'],['whistle','Whistle (requires Cactus runtime)']]],
    ['vad_enabled','Voice activity detection',null],
    ['interrupt_on_speech','Interrupt talkback when speaking',null],
    ['noise_suppression','Noise suppression', [['rnnoise','RNNoise (pending native integration)'],['none','Off']]],
    ['talkback_enabled','Enable spoken responses',null],
    ['tts_backend','Speech output', [['piper','Piper (requires installed voice)'],['spark','Spark TTS (pending decoder)'],['none','Off']]],
    ['push_to_talk_enabled','Push-to-talk available',null],
    ['continuous_listening_enabled','Continuous listening while app visible (opt-in)',null],
    ['wake_phrase','Wake phrase', [['Penguru','Penguru (foreground ASR only)']]],
  ];
  const el = (tag,txt) => { const x=document.createElement(tag); x.textContent=txt; return x; };
  let current={};
  const status=el('p','Reading Beak settings…');status.setAttribute('role','status');
  const settings=el('div',''); const downloads=el('div','');
  container.replaceChildren(settings,status,el('h3','Beak component downloads'),
    el('p','Downloads are staged, not activated. ARM64 runtime, license, signed provenance and hardware tests are still required.'),downloads);
  async function refresh() {
    try {
      const result=await call('get_beak');current=result.config;
      settings.replaceChildren();
      for (const [key,label,options] of fields) {
        const row=el('label',label+' ');
        const control=options?el('select',''):document.createElement('input');
        if (options) {
          for (const [value,title] of options) { const option=el('option',title);option.value=value;control.append(option); }
          control.value=current[key];
        } else { control.type='checkbox';control.checked=current[key]===true; }
        control.dataset.beak=key;
        // Use a real change listener (rather than a label click handler) so
        // mouse, touch and keyboard activation all follow the same path.
        control.addEventListener('change', async()=>{
          const before=current[key];const value=options?control.value:control.checked;
          control.disabled=true;
          try { const result=await call('set_beak',{changes:{[key]:value}});current=result.config;
            status.textContent='Saved to the single PenGuru Beak configuration. Changes to capture apply on the next recording.';
          } catch (error) { if(options)control.value=before;else control.checked=before;status.textContent=error.message; }
          finally {control.disabled=false;}
        });
        row.append(control);settings.append(row,document.createElement('div'));
      }
      const caps=result.capabilities||{};
      const missing=Object.keys(caps).filter(x=>caps[x]===false);
      const availability=el('p','Available: '+Object.keys(caps).filter(x=>caps[x]===true).join(', ')+'. Not installed/verified: '+missing.join(', '));
      settings.append(availability);
    } catch(error) {status.textContent=error.message;}
  }
  async function showDownloads() {
    try {
      const catalog=(await call('beak_catalog')).components;
      downloads.replaceChildren();
      for(const item of catalog) {
        const section=el('article','');section.className='card';
        const source=el('a',item.name+' · '+item.role);source.href=item.url;
        source.target='_blank';source.rel='noopener noreferrer';
        const size=item.size_bytes ? ' Download size: '+formatBytes(item.size_bytes)+'.' : '';
        const info=el('p',item.note+' Source revision: '+item.revision+'.'+size);
        const verification=el('p',item.source_verified ? 'SOURCE VERIFIED · staging only' : 'SOURCE UNVERIFIED · automatic installation disabled');
        const agreement=document.createElement('input');agreement.type='checkbox';
        const ack=el('label',' Reviewed source and license (staging only) ');ack.prepend(agreement);
        const button=el('button',item.download_allowed ? 'Download to device staging' : 'Download unavailable');button.disabled=true;
        agreement.onchange=()=>button.disabled=!agreement.checked || !item.download_allowed;
        const state=el('p','');state.setAttribute('role','status');
        const bar=document.createElement('progress');bar.max=1;bar.value=0;bar.hidden=true;
        const cancel=el('button','Cancel');cancel.hidden=true;
        let timer=null;
        button.onclick=async()=>{
          button.disabled=true;agreement.disabled=true;
          try {
            const task=await call('start_beak_download',{component_id:item.id,reviewed:true});
            bar.hidden=cancel.hidden=false;
            cancel.onclick=()=>call('cancel_download',{job_id:task.job_id}).catch(e=>state.textContent=e.message);
            const poll=async()=>{
              try {
                const result=(await call('download_status',{job_id:task.job_id})).job;
                bar.value=result.progress||0;state.textContent=result.state+' · '+(result.detail||'')+(result.received_bytes!=null ? ' · '+formatBytes(result.received_bytes)+' / '+(result.total_bytes ? formatBytes(result.total_bytes) : 'unknown')+' ('+Math.round((result.progress||0)*100)+'%)' : '');
                if(['staged','error','cancelled','quarantined'].includes(result.state)) {
                  clearInterval(timer);timer=null;cancel.hidden=true;
                  agreement.disabled=false;button.disabled=!agreement.checked || !item.download_allowed;
                }
              }catch(error){state.textContent=error.message;clearInterval(timer);timer=null;}
            };
            timer=setInterval(poll,1800);await poll();
          }catch(error){state.textContent=error.message;agreement.disabled=false;button.disabled=!agreement.checked || !item.download_allowed;}
        };
        section.append(source,info,verification,ack,button,cancel,bar,state);downloads.append(section);
      }
      const links=[['Silero VAD source','https://github.com/snakers4/silero-vad'],
                   ['RNNoise source','https://github.com/xiph/rnnoise'],
                   ['Piper voice catalog','https://huggingface.co/rhasspy/piper-voices']];
      for(const [name,url] of links){const a=el('a',name+' (runtime/source guidance; not an install)');a.href=url;a.target='_blank';a.rel='noopener noreferrer';downloads.append(a,document.createElement('div'));}
    }catch(error){downloads.textContent=error.message;}
  }
  refresh();showDownloads();
  return {refresh, getConfig:()=>({...current})};
}

function formatBytes(bytes) {
  if (!Number.isFinite(bytes) || bytes < 1024) return String(bytes || 0)+' B';
  const units=['KiB','MiB','GiB']; let n=bytes/1024, i=0;
  while(n>=1024 && i<units.length-1) { n/=1024; i++; }
  return n.toFixed(n>=100 ? 0 : 1)+' '+units[i];
}
