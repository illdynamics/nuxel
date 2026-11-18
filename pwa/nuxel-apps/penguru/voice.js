// Foreground-only local voice capture. No auto-send, no privilege escalation.
// Continuous mode is opt-in and stops on app hiding, microphone stop or OFF.
export function voiceControls(call, available, onText) {
  const $=id=>document.getElementById(id);
  let epoch=0, timer=null, stream=null, context=null, processor=null, chunks=[], active=false;
  const status=text=>{$('voice-status').textContent=text;};
  async function stop() {
    active=false;epoch++;clearTimeout(timer);timer=null;
    if(processor){processor.onaudioprocess=null;processor.disconnect();processor=null;}
    if(stream){stream.getTracks().forEach(t=>t.stop());stream=null;}
    if(context){const c=context;context=null;try{await c.close();}catch{}}
    chunks=[];
    $('voice-stop').disabled=true;
    for(const id of ['voice-talk','voice-wake','voice-continuous']) $(id).disabled=false;
    status('Microphone closed');
  }
  function pcmWav(chunks,rate) {
    const length=chunks.reduce((n,c)=>n+c.length,0),merged=new Float32Array(length);
    let n=0;for(const c of chunks){merged.set(c,n);n+=c.length;}
    const count=Math.min(160000,Math.floor(merged.length*16000/rate));
    const bytes=new Uint8Array(44+count*2),v=new DataView(bytes.buffer);
    function word(at,s){for(let i=0;i<s.length;i++)v.setUint8(at+i,s.charCodeAt(i));}
    word(0,'RIFF');v.setUint32(4,36+2*count,true);word(8,'WAVE');word(12,'fmt ');
    v.setUint32(16,16,true);v.setUint16(20,1,true);v.setUint16(22,1,true);
    v.setUint32(24,16000,true);v.setUint32(28,32000,true);v.setUint16(32,2,true);v.setUint16(34,16,true);
    word(36,'data');v.setUint32(40,count*2,true);
    let energy=0;
    for(let i=0;i<count;i++){
      const a=Math.floor(i*rate/16000),b=Math.max(a+1,Math.floor((i+1)*rate/16000));
      let sum=0;for(let j=a;j<b;j++)sum+=merged[j]||0;
      const val=Math.max(-1,Math.min(1,sum/(b-a)));energy+=val*val;
      v.setInt16(44+2*i,Math.round(val<0?val*32768:val*32767),true);
    }
    let text='';for(let i=0;i<bytes.length;i+=8192)text+=String.fromCharCode(...bytes.subarray(i,i+8192));
    return {audio:btoa(text),rms:count?Math.sqrt(energy/count):0};
  }
  async function start(mode) {
    if(active || document.hidden || !available()) {status('Enable PenGuru and finish the current response first.');return;}
    const own=++epoch;
    let cfg;
    try {
      cfg=(await call('get_beak')).config;
      if(mode==='talk' && !cfg.push_to_talk_enabled) throw Error('Push-to-talk is disabled in Beak.');
      if(!navigator.mediaDevices?.getUserMedia) throw Error('This Nuxel webview does not expose microphone capture.');
      if(mode==='continuous' && !cfg.continuous_listening_enabled) throw Error('Enable continuous listening in Beak settings first.');
      if(own!==epoch || document.hidden)return;
      const host=window.NuxelHost||window.parent?.NuxelHost;
      if(host?.micAuthorize){const perm=await host.micAuthorize();if(perm?.ok===false)throw Error('Microphone permission denied');}
      const acquired=await navigator.mediaDevices.getUserMedia({audio:{echoCancellation:true,
        noiseSuppression:cfg.noise_suppression!=='none'},video:false});
      if(own!==epoch || document.hidden){acquired.getTracks().forEach(t=>t.stop());return;}
      stream=acquired;
      // If OS/user revokes the microphone mid-session, stop immediately.
      for (const track of stream.getAudioTracks()) {
        track.addEventListener('ended', () => { if (stream === acquired) stop(); }, {once:true});
      }
      context=new AudioContext();await context.resume();active=true;chunks=[];
      const source=context.createMediaStreamSource(stream);
      processor=context.createScriptProcessor(4096,1,1);
      const silence=context.createGain();silence.gain.value=0;
      source.connect(processor);processor.connect(silence);silence.connect(context.destination);
      processor.onaudioprocess=e=>{if(active)chunks.push(new Float32Array(e.inputBuffer.getChannelData(0)));};
      $('voice-stop').disabled=false;
      for(const id of ['voice-talk','voice-wake','voice-continuous']) $(id).disabled=true;
      window.dispatchEvent(new Event('penguru:microphone-open'));
      status(mode==='talk'?'Listening for 5s…':mode==='continuous'?'Foreground continuous listening · say Penguru':'Say Penguru · foreground microphone on');
      timer=setTimeout(async()=>{
        if(!active || own!==epoch)return;
        const data=pcmWav(chunks,context.sampleRate);
        await stop();
        const afterStop=epoch;
        $('voice-stop').disabled=false; // allow abort during transcription/retry
        if(cfg.vad_enabled && data.rms<0.006) {
          status('Silence detected (simple RMS gate, Silero not installed).');
          if(mode==='continuous' && !document.hidden && available())timer=setTimeout(()=>start(mode),400);
          return;
        }
        status('Recognizing on device; microphone closed…');
        try {
          const result=await call('transcribe',{audio:data.audio});
          if(afterStop!==epoch || document.hidden || !available())return;
          const matched=mode==='talk'||result.wake_detected;
          if(matched) {
            const transcript=mode==='talk'?result.text:result.after_wake;
            if(transcript?.trim()){onText(transcript);status('Transcript ready. Review and press Send.');return;}
          }
          if(mode==='continuous'&&available()&&!document.hidden){status('Wake word not detected; continuing while visible…');timer=setTimeout(()=>start(mode),350);}
          else status('No wake phrase detected. Microphone closed.');
        }catch(e){status(e.message);}
      },5000);
    }catch(e){await stop();status(e.message);}
  }
  $('voice-talk').onclick=()=>start('talk');
  $('voice-wake').onclick=()=>start('wake');
  $('voice-continuous').onclick=()=>start('continuous');
  $('voice-stop').onclick=stop;
  document.addEventListener('visibilitychange',()=>{if(document.hidden)stop();});
  window.addEventListener('pagehide',stop);
  return {stop};
}
