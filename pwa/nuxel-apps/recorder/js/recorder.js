/* Nuxel Recorder (PWNAGE-30000)
 * One-tap voice recorder.  Capture uses the browser audio stack when it is
 * really available (getUserMedia + Web Audio), encodes 16-bit PCM WAV with the
 * shared encoder, and persists to the selected save location.  If no capture
 * device is available the app says so and never fakes a recording. */
(function () {
  'use strict';
  var REC_KEY = 'nuxel-recorder-recordings';
  var SET_KEY = 'nuxel-recorder-settings';

  var el = {};
  ['rec','stop','timer','meter','monitor','capability','list','count','export','clear',
   'io-report','path-report','mic-badge','save-loc','save-loc-save'].forEach(function (id) {
    el[id] = document.getElementById(id);
  });

  function load(key, dflt) {
    try { var raw = localStorage.getItem(key); return raw ? JSON.parse(raw) : dflt; }
    catch (e) { return dflt; }
  }
  function save(key, v) { try { localStorage.setItem(key, JSON.stringify(v)); } catch (e) {} }

  var settings = load(SET_KEY, { saveLocation: '/VoiceRecordings', maxSeconds: 600 });
  var recordings = load(REC_KEY, []);
  var stream = null, ctx = null, node = null, startedAt = 0, timerId = null;
  var chunks = [];

  function bridgeCall(ns, verb, params) {
    if (window.NuxelBridge && typeof window.NuxelBridge.call === 'function') {
      return window.NuxelBridge.call(ns, verb, params).catch(function (e) { return { success: false, error: e && e.message }; });
    }
    return Promise.resolve({ success: false, offline: true });
  }

  function toast(msg) {
    el.ioReport.textContent = msg;
    el.micBadge.textContent = msg;
  }
  function status(lines) { el.pathReport.textContent = lines.join('\n'); }

  async function probeMic() {
    el.micBadge.textContent = 'microphone: probing…';
    var lines = [];
    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
      el.micBadge.textContent = 'microphone: unsupported in this webview';
      lines.push('getUserMedia is not available in this webview.');
      lines.push('A real device capture path must be provided by the launcher host.');
      status(lines);
      return { supported: false, error: 'getUserMedia unavailable' };
    }
    try {
      stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      el.micBadge.textContent = 'microphone: available';
      lines.push('getUserMedia returned an audio stream.');
      lines.push('Track label: ' + (stream.getAudioTracks()[0] && stream.getAudioTracks()[0].label || 'unnamed'));
      lines.push('A returned stream is a capture-device claim, not proof the mic can hear.');
    } catch (e) {
      el.micBadge.textContent = 'microphone: unavailable (' + (e.name || e.message) + ')';
      lines.push('getUserMedia failed: ' + (e.name || e.message));
      lines.push('The microphone is unavailable or permission was denied.');
      stream = null;
    }
    var audio = await bridgeCall('audio', 'status', {});
    if (audio && audio.success !== false) {
      lines.push('Audio service: ' + JSON.stringify(audio).slice(0, 240));
    } else {
      lines.push('Audio service: not reported in this session.');
    }
    status(lines);
    return { supported: !!stream, error: stream ? null : 'no audio stream' };
  }

  function fmt(ms) {
    var s = Math.floor(ms / 1000);
    var tenths = Math.floor((ms % 1000) / 100);
    return String(Math.floor(s / 60)).padStart(2, '0') + ':' + String(s % 60).padStart(2, '0') + '.' + tenths;
  }

  el.rec.addEventListener('click', async function () {
    if (stream) { stopRecording(); return; }
    await probeMic();
    if (!stream) { toast('Microphone unavailable — recording did not start.'); return; }
    var AC = window.AudioContext || window.webkitAudioContext;
    if (!AC) { toast('Web Audio is unavailable — recording did not start.'); return; }
    try {
      ctx = new AC();
      var source = ctx.createMediaStreamSource(stream);
      node = ctx.createScriptProcessor(4096, 1, 1);
      chunks = [];
      node.onaudioprocess = function (ev) {
        var input = ev.inputBuffer.getChannelData(0);
        chunks.push(new Float32Array(input));
      };
      source.connect(node);
      node.connect(ctx.destination);
      startedAt = Date.now();
      timerId = setInterval(function () { el.timer.textContent = fmt(Date.now() - startedAt); }, 100);
      el.rec.textContent = 'Stop recording';
      el.stop.disabled = false;
      toast('Recording…');
    } catch (e) {
      toast('Recording failed to start: ' + e.message);
      stopStream();
    }
  });

  el.stop.addEventListener('click', function () { stopRecording(); });

  async function stopRecording() {
    clearInterval(timerId);
    var durationMs = Date.now() - startedAt;
    try { if (node) { node.disconnect(); node.onaudioprocess = null; node = null; } } catch (e) {}
    stopStream();
    el.rec.textContent = 'Start recording';
    el.stop.disabled = true;
    el.timer.textContent = '00:00.0';
    if (!chunks.length) { toast('No audio captured.'); return; }
    var total = chunks.reduce(function (n, c) { return n + c.length; }, 0);
    var flat = new Float32Array(total);
    var off = 0;
    chunks.forEach(function (c) { flat.set(c, off); off += c.length; });
    var wav = window.NuxelWav.encodeWav([flat], ctx ? ctx.sampleRate : 48000, flat);
    var name = 'recording-' + new Date().toISOString().replace(/[:.]/g, '-') + '.wav';
    var path = settings.saveLocation.replace(/\/$/, '') + '/' + name;
    var b64 = btoa(String.fromCharCode.apply(null, wav));
    var saved = { id: 'rec-' + Date.now(), name: name, path: path, durationMs: durationMs, size: wav.length, at: Date.now() };
    var res = await bridgeCall('storage', 'write-file', { path: path, data_b64: b64 });
    if (res && res.success !== false) {
      saved.stored = 'bridge';
    } else {
      saved.stored = 'local';
      save(REC_KEY + ':data:' + saved.id, b64);
    }
    recordings.unshift(saved);
    save(REC_KEY, recordings);
    renderList();
    toast('Saved ' + name + ' (' + (wav.length / 1024).toFixed(1) + ' KiB WAV)' + (saved.stored === 'local' ? ' locally' : ''));
  }

  function stopStream() {
    try { if (stream) { stream.getTracks().forEach(function (t) { t.stop(); }); } } catch (e) {}
    stream = null;
    try { if (ctx) ctx.close(); } catch (e) {}
    ctx = null;
  }

  function renderList() {
    el.count.textContent = String(recordings.length);
    el.list.innerHTML = '';
    recordings.forEach(function (r, i) {
      var li = document.createElement('li');
      var left = document.createElement('div');
      var n = document.createElement('div'); n.textContent = r.name;
      var d = document.createElement('div'); d.className = 'li-sub';
      d.textContent = new Date(r.at).toLocaleString() + ' · ' + fmt(r.durationMs) + ' · ' + (r.size / 1024).toFixed(1) + ' KiB';
      left.appendChild(n); left.appendChild(d);
      var actions = document.createElement('div');
      var del = document.createElement('button'); del.textContent = 'Delete';
      del.addEventListener('click', function () {
        if (window.confirm('Delete this recording?')) {
          recordings.splice(i, 1); save(REC_KEY, recordings); renderList();
        }
      });
      actions.appendChild(del);
      li.appendChild(left); li.appendChild(actions);
      el.list.appendChild(li);
    });
  }

  if (el.saveLoc) {
    el.saveLoc.value = settings.saveLocation;
    el.saveLocSave.addEventListener('click', function () {
      var v = el.saveLoc.value.trim();
      if (!v.startsWith('/')) v = '/' + v;
      settings.saveLocation = v; save(SET_KEY, settings);
      toast('Save location set to ' + v);
    });
  }
  document.getElementById('export').addEventListener('click', function () {
    var text = JSON.stringify({ schema_version: 1, recordings: recordings }, null, 2);
    try {
      var a = document.createElement('a');
      a.href = URL.createObjectURL(new Blob([text], { type: 'application/json' }));
      a.download = 'nuxel-recordings.json';
      document.body.appendChild(a); a.click();
      setTimeout(function () { URL.revokeObjectURL(a.href); a.remove(); }, 2000);
      toast('Exported ' + recordings.length + ' recording record(s)');
    } catch (e) { toast('Export unavailable in this view'); }
  });
  document.getElementById('clear').addEventListener('click', function () {
    if (!recordings.length) return;
    if (window.confirm('Delete all recording records? (Recording data already stored is left on disk.)')) {
      recordings = []; save(REC_KEY, recordings); renderList(); toast('Recording list cleared');
    }
  });

  renderList();
  probeMic();
  window.nuxelRecorder = { probeMic: probeMic, recordings: recordings, settings: settings, fmt: fmt };
})();
