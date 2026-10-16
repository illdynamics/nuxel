// Nuxel Recorder (mission area 30; audio provisioning - mission area 6)
//
// SCOPE: media provisioning only.  This app asks WebKitGTK/the OS for a capture
// stream and stores what it gets in IndexedDB.  It does NOT claim that the S10+
// CS47L93/CS35L40 capture path works - that is a hardware question owned by the
// audio workstream and is reported here from whatever the platform answers.
// If there is no capture device the UI says so and disables the record button.
(function () {
  'use strict';

  var DB_NAME = 'nuxel-recorder';
  var DB_STORE = 'clips';
  var K_PREFS = 'nuxel-recorder-prefs';

  var els = {
    meter: document.getElementById('meter'),
    timer: document.getElementById('timer'),
    rec: document.getElementById('rec'),
    stop: document.getElementById('stop'),
    monitor: document.getElementById('monitor'),
    capability: document.getElementById('capability'),
    list: document.getElementById('list'),
    count: document.getElementById('count'),
    badge: document.getElementById('mic-badge'),
    pathReport: document.getElementById('path-report'),
    ioReport: document.getElementById('io-report')
  };
  // A 2D context can be absent (engine without canvas, or canvas disabled).
  // The meter is cosmetic; the recorder must still record and export, so a
  // missing context degrades to a numeric level instead of throwing.
  var mctx = (els.meter && els.meter.getContext) ? els.meter.getContext('2d') : null;
  var meterUnavailable = !mctx;
  if (meterUnavailable && els.meter) {
    els.meter.setAttribute('data-context', 'unavailable');
    els.meter.title = 'this engine exposes no 2D canvas context - level shown numerically';
  }

  var ctx = null, stream = null, recorder = null, analyser = null, monitorNode = null;
  var chunks = [], startedAt = 0, rafId = 0, mimeType = '';

  var prefs = {};
  try { prefs = JSON.parse(localStorage.getItem(K_PREFS) || '{}') || {}; } catch (e) { prefs = {}; }
  els.monitor.checked = !!prefs.monitor;

  function toast(msg) {
    var t = document.getElementById('toast');
    t.textContent = msg;
    t.classList.remove('hidden');
    clearTimeout(toast._t);
    toast._t = setTimeout(function () { t.classList.add('hidden'); }, 2600);
  }
  function setBadge(text, cls) {
    els.badge.textContent = text;
    els.badge.className = 'badge' + (cls ? ' ' + cls : '');
  }

  /* ---------- IndexedDB ---------- */
  function db() {
    return new Promise(function (resolve) {
      if (!window.indexedDB) { resolve(null); return; }
      try {
        var req = window.indexedDB.open(DB_NAME, 1);
        req.onupgradeneeded = function () {
          var d = req.result;
          if (!d.objectStoreNames.contains(DB_STORE)) d.createObjectStore(DB_STORE, { keyPath: 'id' });
        };
        req.onsuccess = function () { resolve(req.result); };
        req.onerror = function () { resolve(null); };
      } catch (e) { resolve(null); }
    });
  }
  function store(mode, fn) {
    return db().then(function (d) {
      if (!d) return null;
      return new Promise(function (resolve) {
        var tx = d.transaction(DB_STORE, mode);
        var s = tx.objectStore(DB_STORE);
        var r = fn(s);
        tx.oncomplete = function () { resolve(r ? r.result : null); };
        tx.onerror = function () { resolve(null); };
      });
    });
  }

  /* ---------- capability probe (honest) ---------- */
  function probe() {
    var hasMedia = !!(navigator.mediaDevices && navigator.mediaDevices.getUserMedia);
    var hasRec = typeof window.MediaRecorder !== 'undefined';
    var lines = [];
    lines.push('navigator.mediaDevices.getUserMedia : ' + (hasMedia ? 'present' : 'absent'));
    lines.push('MediaRecorder                      : ' + (hasRec ? 'present' : 'absent'));
    lines.push('AudioContext                       : ' + ((window.AudioContext || window.webkitAudioContext) ? 'present' : 'absent'));
    if (!hasMedia || !hasRec) {
      setBadge('microphone: unavailable', 'bad');
      els.capability.textContent = 'This view exposes no capture API. Recording stays disabled and ' +
        'the app reports the limitation instead of offering a button that cannot work.';
      els.rec.disabled = true;
    } else {
      setBadge('microphone: not requested yet', 'warn');
      els.capability.textContent = 'Capture API present. Press Start and grant the portal permission prompt; ' +
        'the actual S10+ microphone path is reported separately below.';
    }
    lines.push('');
    lines.push('Note: an available API is not proof of a working microphone. Only a recording you');
    lines.push('can hear back proves the capture path - that is an owner test (proof area 06).');
    return lines;
  }

  function reportAudioPath() {
    var lines = probe();
    var host = null;
    try { host = (window.parent && window.parent.NuxelHost) || window.NuxelHost; } catch (e) { host = null; }
    var p = (host && host.available)
      ? host.statusRead('audio')
      : Promise.resolve({ ok: false, offline: true });
    p.then(function (r) {
      if (r && r.ok && r.text) {
        lines.push('');
        lines.push('Launcher host status.read audio:');
        lines.push(String(r.text).trim());
      } else {
        lines.push('');
        lines.push('Launcher host audio status: not reported (no host in this view).');
      }
      lines.push('');
      lines.push('Bridge: ' + (window.NuxelBridge ? (window.NuxelBridge.isConnected ? (window.NuxelBridge.isConnected() ? 'connected' : 'offline') : 'present') : 'absent') +
        ' - the recorder does not require the bridge; capture and storage are local.');
      els.pathReport.textContent = lines.join('\n');
    });
  }

  /* ---------- meter ---------- */
  function drawMeter(level) {
    if (!mctx) {                       // no canvas context: keep the state visible, never throw
      els.timer.setAttribute('data-level', String(Math.round((level || 0) * 100)));
      return;
    }
    var w = els.meter.width, h = els.meter.height;
    mctx.clearRect(0, 0, w, h);
    mctx.fillStyle = '#150e20';
    mctx.fillRect(0, 0, w, h);
    mctx.strokeStyle = 'rgba(192,132,252,0.18)';
    for (var i = 0; i <= 10; i++) {
      var x = (w / 10) * i;
      mctx.beginPath(); mctx.moveTo(x, 0); mctx.lineTo(x, h); mctx.stroke();
    }
    var bars = 40;
    for (var b = 0; b < bars; b++) {
      var t = b / bars;
      var hgt = Math.max(2, (h - 8) * (level * (1 - t * 0.35)));
      mctx.fillStyle = t > 0.85 ? '#ff6b6b' : (t > 0.65 ? '#ffd166' : '#c084fc');
      mctx.fillRect(4 + b * ((w - 8) / bars), (h - hgt) / 2, ((w - 8) / bars) - 2, hgt);
    }
  }

  function tickMeter() {
    if (!analyser) { requestAnimationFrame(tickMeter); return; }
    var data = new Uint8Array(analyser.fftSize);
    analyser.getByteTimeDomainData(data);
    var peak = 0;
    for (var i = 0; i < data.length; i++) {
      var v = Math.abs(data[i] - 128) / 128;
      if (v > peak) peak = v;
    }
    drawMeter(Math.min(1, peak * 1.6));
    var ms = Date.now() - startedAt;
    els.timer.textContent = String(Math.floor(ms / 60000)).padStart(2, '0') + ':' +
      String(Math.floor(ms % 60000 / 1000)).padStart(2, '0') + '.' +
      String(Math.floor(ms % 1000 / 100)).padStart(1, '0');
    rafId = requestAnimationFrame(tickMeter);
  }

  /* ---------- recording ---------- */
  function start() {
    els.rec.disabled = true;
    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
      els.capability.textContent = 'No capture API in this view — recording cannot start.';
      els.rec.disabled = true;
      return;
    }
    var constraints = { audio: { echoCancellation: false, noiseSuppression: false, autoGainControl: false } };
    navigator.mediaDevices.getUserMedia(constraints).then(function (s) {
      stream = s;
      setBadge('microphone: live', 'ok');
      var Ctx = window.AudioContext || window.webkitAudioContext;
      ctx = new Ctx();
      analyser = ctx.createAnalyser();
      analyser.fftSize = 2048;
      var src = ctx.createMediaStreamSource(s);
      src.connect(analyser);
      if (els.monitor.checked) {
        monitorNode = ctx.createGain();
        monitorNode.gain.value = 0.25;
        analyser.connect(monitorNode).connect(ctx.destination);
      }
      var options = {};
      ['audio/webm;codecs=opus', 'audio/webm', 'audio/ogg;codecs=opus', 'audio/mp4'].some(function (m) {
        if (window.MediaRecorder && MediaRecorder.isTypeSupported && MediaRecorder.isTypeSupported(m)) { options.mimeType = m; return true; }
        return false;
      });
      mimeType = options.mimeType || '';
      recorder = new MediaRecorder(stream, options);
      chunks = [];
      recorder.ondataavailable = function (ev) { if (ev.data && ev.data.size) chunks.push(ev.data); };
      recorder.onstop = function () { finalise(); };
      recorder.start(500);
      startedAt = Date.now();
      els.stop.disabled = false;
      els.timer.textContent = '00:00.0';
      cancelAnimationFrame(rafId);
      tickMeter();
      els.capability.textContent = 'Recording with ' + (mimeType || 'the platform default codec') +
        '. Audio stays on this device: nothing is uploaded.';
      toast('Recording started');
    }).catch(function (err) {
      setBadge('microphone: denied', 'bad');
      els.rec.disabled = false;
      els.capability.textContent = 'Capture was refused or is not provisioned: ' + (err && err.name ? err.name : 'error') +
        '. Grant microphone access in Settings → Privacy, then try again.';
    });
  }

  function stop() {
    if (recorder && recorder.state !== 'inactive') recorder.stop();
    els.stop.disabled = true;
  }

  function finalise() {
    var durationMs = Date.now() - startedAt;
    var blob = new Blob(chunks, { type: mimeType || 'audio/webm' });
    if (stream) { stream.getTracks().forEach(function (t) { t.stop(); }); stream = null; }
    if (ctx && ctx.close) { try { ctx.close(); } catch (e) { /* already closed */ } }
    ctx = null; analyser = null;
    cancelAnimationFrame(rafId);
    drawMeter(0);
    setBadge('microphone: idle');
    els.rec.disabled = false;
    var clip = {
      id: 'clip-' + Date.now(),
      name: 'Recording ' + new Date().toLocaleString(),
      at: Date.now(),
      durationMs: durationMs,
      mime: mimeType || 'audio/webm',
      size: blob.size,
      blob: blob
    };
    store('readwrite', function (s) { return s.put(clip); }).then(function () {
      if (blob.size === 0) {
        toast('Nothing was captured - the stream produced no audio data');
      } else {
        toast('Saved ' + (blob.size / 1024).toFixed(1) + ' KiB of audio');
      }
      render();
    });
  }

  /* ---------- list ---------- */
  function fmtDuration(ms) {
    var s = Math.round(ms / 1000);
    return String(Math.floor(s / 60)).padStart(2, '0') + ':' + String(s % 60).padStart(2, '0');
  }
  function render() {
    store('readonly', function (s) { return s.getAll ? s.getAll() : null; }).then(function (rows) {
      var list = document.getElementById('list');
      list.innerHTML = '';
      if (rows === null) {
        els.ioReport.textContent = 'Recording storage (IndexedDB) is unavailable in this view. ' +
          'Capture itself still works, but clips cannot be kept between sessions.';
        return;
      }
      rows = (rows || []).sort(function (a, b) { return b.at - a.at; });
      els.count.textContent = rows.length + ' saved';
      if (!rows.length) {
        var li0 = document.createElement('li');
        li0.textContent = 'No recordings yet.';
        list.appendChild(li0);
        return;
      }
      rows.forEach(function (r) {
        var li = document.createElement('li');
        var head = document.createElement('div');
        head.className = 'head';
        var name = document.createElement('div');
        name.textContent = r.name;
        var meta = document.createElement('div');
        meta.className = 'mono';
        meta.textContent = fmtDuration(r.durationMs) + ' · ' + (r.size / 1024).toFixed(1) + ' KiB · ' + r.mime.replace('audio/', '');
        head.appendChild(name); head.appendChild(meta);
        li.appendChild(head);
        try {
          var audio = document.createElement('audio');
          audio.controls = true;
          audio.src = URL.createObjectURL(r.blob);
          li.appendChild(audio);
        } catch (e) { /* no object URLs in this view */ }
        var row = document.createElement('div');
        row.className = 'row';
        var dl = document.createElement('button');
        dl.textContent = 'Save to device';
        dl.addEventListener('click', function () {
          try {
            var a = document.createElement('a');
            a.href = URL.createObjectURL(r.blob);
            a.download = r.name.replace(/[^a-z0-9]+/gi, '-').toLowerCase() + '.webm';
            document.body.appendChild(a); a.click();
            setTimeout(function () { URL.revokeObjectURL(a.href); a.remove(); }, 2000);
          } catch (e) { toast('Export unavailable in this view'); }
        });
        var del = document.createElement('button');
        del.textContent = 'Delete';
        del.addEventListener('click', function () {
          store('readwrite', function (s) { return s.delete(r.id); }).then(function () { render(); toast('Recording deleted'); });
        });
        row.appendChild(dl); row.appendChild(del);
        li.appendChild(row);
        list.appendChild(li);
      });
    });
  }

  els.rec.addEventListener('click', start);
  els.stop.addEventListener('click', stop);
  els.monitor.addEventListener('change', function () {
    prefs.monitor = !!els.monitor.checked;
    try { localStorage.setItem(K_PREFS, JSON.stringify(prefs)); } catch (e) { /* ignore */ }
  });
  document.getElementById('export').addEventListener('click', function () {
    store('readonly', function (s) { return s.getAll ? s.getAll() : null; }).then(function (rows) {
      var manifest = (rows || []).map(function (r) {
        return { id: r.id, name: r.name, at: r.at, durationMs: r.durationMs, mime: r.mime, size: r.size };
      });
      var text = JSON.stringify({ schema_version: 1, clips: manifest }, null, 2);
      try {
        var a = document.createElement('a');
        a.href = URL.createObjectURL(new Blob([text], { type: 'application/json' }));
        a.download = 'nuxel-recordings.json';
        document.body.appendChild(a); a.click();
        setTimeout(function () { URL.revokeObjectURL(a.href); a.remove(); }, 2000);
        els.ioReport.textContent = 'Exported the manifest of ' + manifest.length + ' recordings (audio blobs stay in the device store).';
      } catch (e) { els.ioReport.textContent = 'Export unavailable in this view.'; }
    });
  });
  document.getElementById('clear').addEventListener('click', function () {
    store('readwrite', function (s) { return s.clear(); }).then(function () { render(); toast('All recordings deleted'); });
  });

  drawMeter(0);
  render();
  reportAudioPath();

  // headless smoke-test hook
  // headless smoke-test hook (documented app API; also used by
  // tools/s10plus/a33/tests/test-core-apps.py)
  window.nuxelRecorder = { probe: probe, fmtDuration: fmtDuration, drawMeter: drawMeter,
                           render: render, meterContext: function () { return !!mctx; } };
})();
