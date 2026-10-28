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
    el[id.replace(/-([a-z])/g, function (_m, c) { return c.toUpperCase(); })] = el[id];
  });

  function load(key, dflt) {
    try { var raw = localStorage.getItem(key); return raw ? JSON.parse(raw) : dflt; }
    catch (e) { return dflt; }
  }
  function save(key, v) { try { localStorage.setItem(key, JSON.stringify(v)); } catch (e) {} }

  var settings = load(SET_KEY, { saveLocation: '/VoiceRecordings', maxSeconds: 600 });
  var recordings = load(REC_KEY, []);
  var stream = null, ctx = null, node = null, gain = null, startedAt = 0, timerId = null;
  var recording = false;
  var chunks = [];
  var homePath = '/home/nuxel';

  function bridgeCall(ns, verb, params) {
    if (window.NuxelBridge && typeof window.NuxelBridge.call === 'function') {
      return window.NuxelBridge.call(ns, verb, params).catch(function (e) { return { success: false, error: e && e.message }; });
    }
    return Promise.resolve({ success: false, offline: true });
  }

  function toast(msg) {
    el.ioReport.textContent = msg;
    // Keep the badge as the precise device state; the toast report may be a
    // higher-level consequence (e.g. "recording did not start").
  }
  function status(lines) { el.pathReport.textContent = lines.join('\n'); }

  function logicalLocation(value) {
    var v = String(value || '').trim();
    if (!v) return '/VoiceRecordings';
    if (homePath && (v === homePath || v.indexOf(homePath + '/') === 0)) {
      v = v.slice(homePath.length) || '/';
    }
    if (v.charAt(0) !== '/') v = '/' + v;
    return v.replace(/\/+$/, '') || '/';
  }

  function absoluteLocation() {
    var rel = logicalLocation(settings.saveLocation);
    return rel === '/' ? homePath : homePath.replace(/\/$/, '') + rel;
  }

  function showLocation() {
    if (el.saveLoc) el.saveLoc.value = absoluteLocation();
    var resolved = document.getElementById('resolved-path');
    if (resolved) resolved.textContent = 'Resolved: ' + absoluteLocation() + '  (logical: ' + settings.saveLocation + ')';
  }

  async function resolveHome() {
    var info = await bridgeCall('storage', 'home', {});
    if (info && info.success !== false && info.home) homePath = info.home;
    showLocation();
  }

  function withTimeout(promise, ms, label) {
    return Promise.race([
      promise,
      new Promise(function (_resolve, reject) {
        setTimeout(function () {
          var e = new Error(label || 'operation timed out');
          e.name = 'TimeoutError';
          reject(e);
        }, ms);
      })
    ]);
  }

  async function probeMicDevices() {
    if (!navigator.mediaDevices || !navigator.mediaDevices.enumerateDevices) {
      el.micBadge.textContent = 'microphone: unsupported in this webview';
      return [];
    }
    try {
      var devices = await navigator.mediaDevices.enumerateDevices();
      var inputs = devices.filter(function (d) { return d.kind === 'audioinput'; });
      if (!inputs.length) {
        el.micBadge.textContent = 'microphone: unavailable (no audio input device)';
        status(['No audio input device is exposed by the session audio service.',
                'The Recorder will not open a capture stream until one exists.']);
      } else {
        el.micBadge.textContent = 'microphone: device present';
      }
      return inputs;
    } catch (e) {
      el.micBadge.textContent = 'microphone: probe failed (' + (e.name || e.message) + ')';
      return [];
    }
  }

  async function probeMic() {
    el.micBadge.textContent = 'microphone: probing…';
    var lines = [];
    // The S10+ vendor audio driver can block in D state (abox_wait_restored)
    // when a capture PCM is opened without a routed source.  The bridge checks
    // the session audio server's Sources list first; no source means no
    // getUserMedia call at all.
    var route = await bridgeCall('audio', 'capture-route', {});
    if (!route || route.success === false || route.available !== true) {
      el.micBadge.textContent = 'microphone: unavailable (no capture route)';
      el.capability.textContent = 'Recording unavailable: no capture source is routed by the session audio server.';
      lines.push('No capture source is routed by the session audio server.');
      if (route && route.reason) lines.push('Reason: ' + route.reason);
      if (route && route.error) lines.push('Audio query: ' + route.error);
      lines.push('Recording did not start. The UI is not frozen; fix the capture route and retry.');
      status(lines);
      return { supported: false, error: 'no capture route', route: route || null };
    }
    // Do not call getUserMedia when the session exposes no audio input: on this
    // kernel a media probe can block in the vendor audio driver.  enumerateDevices
    // is non-blocking and gives the user an accurate reason instead.
    var inputs = await probeMicDevices();
    if (!inputs.length) {
      el.capability.textContent = 'Recording unavailable: no audio input device is exposed.';
      status(['No audio input device is available; recording did not start.',
              'Connect/route a microphone source in the audio session first.']);
      return { supported: false, error: 'no audio input device' };
    }
    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
      el.micBadge.textContent = 'microphone: unsupported in this webview';
      el.capability.textContent = 'This webview does not expose a microphone capture API.';
      lines.push('getUserMedia is not available in this webview.');
      lines.push('A real device capture path must be provided by the launcher host.');
      status(lines);
      return { supported: false, error: 'getUserMedia unavailable' };
    }
    try {
      stream = await withTimeout(navigator.mediaDevices.getUserMedia({ audio: true }), 8000, 'microphone request timed out');
      el.micBadge.textContent = 'microphone: available';
      el.capability.textContent = 'Microphone stream is available; Start recording will capture WAV audio.';
      lines.push('getUserMedia returned an audio stream.');
      lines.push('Track label: ' + (stream.getAudioTracks()[0] && stream.getAudioTracks()[0].label || 'unnamed'));
      lines.push('A returned stream is a capture-device claim, not proof the mic can hear.');
    } catch (e) {
      el.micBadge.textContent = 'microphone: unavailable (' + (e.name || e.message) + ')';
      el.capability.textContent = 'Recording unavailable: ' + (e.name || e.message);
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
    if (recording) { stopRecording(); return; }
    if (!stream) await probeMic();
    if (!stream) { toast('Microphone unavailable — recording did not start.'); return; }
    var AC = window.AudioContext || window.webkitAudioContext;
    if (!AC) { toast('Web Audio is unavailable — recording did not start.'); return; }
    try {
      ctx = new AC();
      if (ctx.state === 'suspended' && ctx.resume) await ctx.resume();
      var source = ctx.createMediaStreamSource(stream);
      node = ctx.createScriptProcessor(4096, 1, 1);
      gain = ctx.createGain();
      gain.gain.value = el.monitor.checked ? 1 : 0;
      chunks = [];
      node.onaudioprocess = function (ev) {
        var input = ev.inputBuffer.getChannelData(0);
        chunks.push(new Float32Array(input));
      };
      source.connect(node);
      node.connect(gain);
      gain.connect(ctx.destination);
      recording = true;
      startedAt = Date.now();
      timerId = setInterval(function () { el.timer.textContent = fmt(Date.now() - startedAt); }, 100);
      el.rec.textContent = 'Stop recording';
      el.stop.disabled = false;
      toast('Recording…');
    } catch (e) {
      recording = false;
      toast('Recording failed to start: ' + e.message);
      stopStream();
    }
  });

  el.stop.addEventListener('click', function () { stopRecording(); });

  async function stopRecording() {
    recording = false;
    clearInterval(timerId);
    var durationMs = Date.now() - startedAt;
    var sampleRate = ctx ? ctx.sampleRate : 48000;
    try { if (node) { node.disconnect(); node.onaudioprocess = null; node = null; } } catch (e) {}
    try { if (gain) { gain.disconnect(); gain = null; } } catch (e) {}
    stopStream();
    el.rec.textContent = 'Start recording';
    el.stop.disabled = true;
    el.timer.textContent = '00:00.0';
    if (!chunks.length) { toast('No audio captured.'); return; }
    var total = chunks.reduce(function (n, c) { return n + c.length; }, 0);
    var flat = new Float32Array(total);
    var off = 0;
    chunks.forEach(function (c) { flat.set(c, off); off += c.length; });
    if (!window.NuxelWav) { toast('WAV encoder did not load — recording was not written.'); return; }
    var wav;
    try {
      wav = window.NuxelWav.encodeWav([flat], sampleRate, [flat]);
    } catch (e) {
      toast('WAV encoding failed: ' + (e && e.message || e)); return;
    }
    var name = 'recording-' + new Date().toISOString().replace(/[:.]/g, '-') + '.wav';
    var logical = logicalLocation(settings.saveLocation);
    var path = (logical === '/' ? '' : logical) + '/' + name;
    var actual = homePath.replace(/\/$/, '') + path;
    var b64 = bytesToB64(wav);
    var saved = { id: 'rec-' + Date.now(), name: name, path: actual, logicalPath: path,
                  durationMs: durationMs, size: wav.length, at: Date.now() };
    var res = await bridgeCall('storage', 'write-file', { path: path, data_b64: b64 });
    if (res && res.success !== false) {
      saved.stored = 'bridge';
      if (res.absolute_path) saved.path = res.absolute_path;
      toast('Saved ' + name + ' to ' + saved.path + ' (' + (wav.length / 1024).toFixed(1) + ' KiB WAV)');
    } else {
      saved.stored = 'local';
      saved.error = (res && res.error) || 'filesystem write failed';
      save(REC_KEY + ':data:' + saved.id, b64);
      toast('Could not write ' + actual + ': ' + saved.error + ' — the audio is kept only in this session.');
    }
    recordings.unshift(saved);
    save(REC_KEY, recordings);
    renderList();
  }

  function stopStream() {
    try { if (stream) { stream.getTracks().forEach(function (t) { t.stop(); }); } } catch (e) {}
    stream = null;
    try { if (ctx) ctx.close(); } catch (e) {}
    ctx = null;
    gain = null;
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
        if (!window.confirm('Delete this recording?')) return;
        var rec = recordings[i];
        var logical = rec.logicalPath || logicalLocation(rec.path || '');
        bridgeCall('storage', 'delete', { path: logical }).then(function (res) {
          if (res && res.success !== false) {
            recordings.splice(i, 1); save(REC_KEY, recordings); renderList();
            toast('Deleted ' + rec.name);
          } else {
            toast('Delete failed: ' + ((res && res.error) || 'unknown error'));
          }
        });
      });
      actions.appendChild(del);
      li.appendChild(left); li.appendChild(actions);
      el.list.appendChild(li);
    });
  }

  if (el.saveLoc) {
    el.saveLocSave.addEventListener('click', function () {
      settings.saveLocation = logicalLocation(el.saveLoc.value);
      save(SET_KEY, settings);
      showLocation();
      toast('Save location set to ' + absoluteLocation());
    });
  }
  el.monitor.addEventListener('change', function () { if (gain) gain.gain.value = el.monitor.checked ? 1 : 0; });
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

  function bytesToB64(bytes) {
    var out = '';
    var step = 0x8000;
    for (var i = 0; i < bytes.length; i += step) {
      out += String.fromCharCode.apply(null, bytes.subarray(i, i + step));
    }
    return btoa(out);
  }

  function bootRecorder() {
    renderList();
    resolveHome();
    el.micBadge.textContent = 'microphone: press Start to check';
    status(['Microphone access is checked when you press Start recording.']);
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', bootRecorder, { once: true });
  else bootRecorder();
  window.nuxelRecorder = { probeMic: probeMic, probeMicDevices: probeMicDevices, recordings: recordings, settings: settings, fmt: fmt,
                           home: function () { return homePath; }, absoluteLocation: absoluteLocation };
})();
