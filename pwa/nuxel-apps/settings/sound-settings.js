/* Nuxel Settings — central per-action sound assignments (PWNAGE-81000).
 *
 * All state lives in nuxel-soundd.  This page never opens audio itself and
 * never passes a filesystem path to a shell.  Browse uploads the selected
 * file's bytes through the bridge; the daemon validates and installs it in
 * ~/Sounds with user ownership.
 */
(function () {
  'use strict';
  var ACTIONS = [
    ['volume', 'Volume change'],
    ['boot', 'Boot-up'],
    ['alarm', 'Alarm'],
    ['timer', 'Timer'],
    ['message', 'Receiving messages'],
    ['notification', 'Notifications'],
    ['other', 'Other future events']
  ];
  var state = { sounds: [], assignments: {}, dirs: [], busy: false, timer: null,
                output: null, outputBusy: false, outputTimer: null,
                outputDragging: false, outputInitialized: false };
  var rows = {};
  function bridge() {
    if (window.NuxelBridge && typeof window.NuxelBridge.call === 'function') return window.NuxelBridge;
    try {
      if (window.parent && window.parent !== window && window.parent.NuxelBridge &&
          typeof window.parent.NuxelBridge.call === 'function') return window.parent.NuxelBridge;
    } catch (e) {}
    return null;
  }
  function call(verb, params) {
    var b = bridge();
    if (!b) return Promise.resolve({ success: false, error: 'Nuxel bridge unavailable' });
    try { return Promise.resolve(b.call('sound', verb, params || {})); }
    catch (e) { return Promise.resolve({ success: false, error: String(e && e.message || e) }); }
  }
  function $(id) { return document.getElementById(id); }
  function esc(v) { return String(v == null ? '' : v).replace(/[&<>"']/g, function (c) { return ({ '&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;' })[c]; }); }
  function fmtBytes(n) {
    if (!Number.isFinite(Number(n))) return '—';
    var u = ['B', 'KiB', 'MiB', 'GiB'], i = 0, v = Number(n);
    while (v >= 1024 && i < u.length - 1) { v /= 1024; i++; }
    return (i ? v.toFixed(1) : v) + ' ' + u[i];
  }
  function fmtDuration(d) {
    if (!Number.isFinite(Number(d))) return 'duration unknown';
    return Number(d).toFixed(Number(d) < 10 ? 2 : 1) + ' s';
  }
  function metaFor(path) {
    for (var i = 0; i < state.sounds.length; i++) if (state.sounds[i].path === path || state.sounds[i].id === path) return state.sounds[i];
    return null;
  }
  function text(id, value) { var e = $(id); if (e) e.textContent = value; }
  function optionLabel(s) {
    var base = s.name || String(s.path || '').split('/').pop();
    var bits = [];
    if (s.format) bits.push(s.format);
    if (s.duration != null) bits.push(fmtDuration(s.duration));
    if (s.sample_rate) bits.push(s.sample_rate + ' Hz');
    if (s.channels) bits.push(s.channels + ' ch');
    if (s.size != null) bits.push(fmtBytes(s.size));
    return base + (bits.length ? '  ·  ' + bits.join(' · ') : '');
  }
  function render() {
    var box = $('sound-assignments');
    if (!box) return;
    box.innerHTML = '';
    rows = {};
    ACTIONS.forEach(function (pair) {
      var action = pair[0], label = pair[1];
      var current = (state.assignments[action] || {}).path || '';
      var row = document.createElement('div');
      row.className = 'sound-assignment-row';
      var head = document.createElement('label');
      head.className = 'sound-assignment-label';
      head.textContent = label;
      var select = document.createElement('select');
      select.className = 'sound-assignment-select';
      select.setAttribute('aria-label', label + ' sound');
      var empty = document.createElement('option');
      empty.value = '';
      empty.textContent = state.sounds.length ? 'Choose a sound…' : 'No sounds discovered yet';
      select.appendChild(empty);
      state.sounds.forEach(function (s) {
        var opt = document.createElement('option');
        opt.value = s.path;
        opt.textContent = optionLabel(s);
        if (s.path === current) opt.selected = true;
        select.appendChild(opt);
      });
      if (current && !metaFor(current)) {
        var missing = document.createElement('option');
        missing.value = current;
        missing.textContent = current.split('/').pop() + '  ·  MISSING/UNDECODABLE';
        missing.selected = true;
        select.appendChild(missing);
      }
      select.addEventListener('change', function () {
        assign(action, select.value, '');
      });
      var preview = document.createElement('button');
      preview.type = 'button';
      preview.textContent = 'Preview';
      preview.addEventListener('click', function () { previewAction(action, select.value); });
      var browse = document.createElement('button');
      browse.type = 'button';
      browse.textContent = 'Browse…';
      browse.addEventListener('click', function () { browseFor(action); });
      var meta = document.createElement('div');
      meta.className = 'sound-assignment-meta';
      var m = metaFor(select.value);
      meta.textContent = m ? optionLabel(m) : (select.value ? 'Selected file is not currently decodable.' : 'No file assigned.');
      select.addEventListener('change', function () {
        var mm = metaFor(select.value);
        meta.textContent = mm ? optionLabel(mm) : (select.value ? 'Selected file is not currently decodable.' : 'No file assigned.');
      });
      var line = document.createElement('div');
      line.className = 'sound-assignment-controls';
      line.appendChild(select); line.appendChild(preview); line.appendChild(browse);
      row.appendChild(head); row.appendChild(line); row.appendChild(meta);
      box.appendChild(row);
      rows[action] = { select: select, meta: meta };
    });
    text('sound-manager-state',
      state.sounds.length + ' compatible sound file(s) in ' + (state.dirs || []).join(' and ') +
      '\nAssignments persist in /var/lib/nuxel/sound/assignments.json. New files are discovered automatically.');
  }
  function refresh(quiet) {
    if (state.busy) return Promise.resolve(null);
    state.busy = true;
    if (!quiet) text('sound-manager-state', 'Reading sound library…');
    return call('state', {}).then(function (doc) {
      state.busy = false;
      if (!doc || doc.success === false) {
        text('sound-manager-state', 'Sound manager unavailable: ' + ((doc && (doc.error || doc.detail)) || 'unknown error'));
        return doc;
      }
      state.sounds = Array.isArray(doc.sounds) ? doc.sounds : [];
      state.assignments = doc.assignments || {};
      state.dirs = Array.isArray(doc.dirs) ? doc.dirs : [];
      render();
      return doc;
    }, function (err) {
      state.busy = false;
      text('sound-manager-state', 'Sound manager error: ' + (err && err.message ? err.message : err));
      return null;
    });
  }
  function assign(action, path, note) {
    return call('assign', { action: action, path: path || null }).then(function (r) {
      if (!r || r.success === false) {
        text('sound-import-state', 'Assignment failed: ' + ((r && (r.error || r.detail)) || 'unknown error'));
        return r;
      }
      state.assignments[action] = r.assignment || { path: path };
      var row = rows[action];
      if (row && row.meta) {
        var m = metaFor(path);
        row.meta.textContent = (m ? optionLabel(m) : 'No file assigned.') + (note ? ' · ' + note : '');
      }
      text('sound-import-state', 'Saved ' + action + ' sound: ' + (path ? String(path).split('/').pop() : 'none') + '.');
      return r;
    });
  }
  function previewAction(action, path) {
    text('sound-import-state', 'Previewing ' + action + '…');
    return call('preview', { action: action, path: path || null }).then(function (r) {
      text('sound-import-state', r && r.success === false
        ? ('Preview failed: ' + (r.error || r.detail || 'unknown'))
        : 'Preview queued on the central sound stream (audible result is owner-verified).');
      return r;
    });
  }
  var browseAction = null;
  function browseFor(action) {
    browseAction = action;
    var input = $('sound-file-input');
    if (input) { input.value = ''; input.click(); }
    else text('sound-import-state', 'File picker unavailable in this webview.');
  }
  function importFor(action, file) {
    if (!file) return;
    if (file.size > 24 * 1024 * 1024) { text('sound-import-state', 'File is larger than 24 MiB.'); return; }
    var reader = new FileReader();
    text('sound-import-state', 'Validating and importing ' + file.name + '…');
    reader.onerror = function () { text('sound-import-state', 'Could not read the selected file.'); };
    reader.onload = function () {
      var data = String(reader.result || '');
      var comma = data.indexOf(',');
      if (comma >= 0) data = data.slice(comma + 1);
      call('import', { name: file.name, data_b64: data }).then(function (r) {
        if (!r || r.success === false) {
          text('sound-import-state', 'Import rejected: ' + ((r && (r.error || r.detail)) || 'unknown error'));
          return;
        }
        text('sound-import-state', 'Imported ' + file.name + ' to the Nuxel sound library. Assigning to ' + action + '…');
        assign(action, r.path || r.id, 'custom file');
        refresh(true);
      });
    };
    reader.readAsDataURL(file);
  }

  // ---- Output routing (PWNAGE-102000) -------------------------------------
  function outputKindLabel(kind) {
    return ({ speaker: 'Phone speaker', hdmi: 'HDMI / USB-C display',
              bluetooth: 'Bluetooth audio', usb: 'USB audio',
              other: 'Audio output' })[kind] || 'Audio output';
  }
  function outputKindIcon(kind) {
    return ({ speaker: '🔈', hdmi: '📺', bluetooth: '🎧', usb: '🔌',
              other: '🔊' })[kind] || '🔊';
  }
  function outputEl(id) { return $(id); }
  function setOutputText(id, value) { text(id, value); }

  function renderOutputDevices(policy, currentMuted) {
    var box = outputEl('sound-output-devices');
    if (!box) return;
    box.innerHTML = '';
    var mode = policy && policy.mode === 'manual' ? 'manual' : 'automatic';
    var preferred = policy && policy.preferred_id;

    function addChoice(id, label, detail, selected, disabled) {
      var button = document.createElement('button');
      button.type = 'button';
      button.className = 'sound-output-choice' + (selected ? ' selected' : '') +
        (disabled ? ' unavailable' : '');
      button.setAttribute('role', 'radio');
      button.setAttribute('aria-checked', selected ? 'true' : 'false');
      button.disabled = !!disabled;
      var head = document.createElement('span');
      head.className = 'sound-output-choice-label';
      head.textContent = label;
      var sub = document.createElement('span');
      sub.className = 'sound-output-choice-detail';
      sub.textContent = detail || '';
      button.appendChild(head);
      button.appendChild(sub);
      if (id === null) {
        button.addEventListener('click', function () {
          return setRoutingMode('automatic');
        });
      } else {
        button.dataset.outputId = id;
        button.addEventListener('click', function () { return selectOutput(id); });
      }
      box.appendChild(button);
    }

    addChoice(null, 'Automatic',
      'Prefer verified HDMI; fall back safely when it disappears.',
      mode === 'automatic', false);
    ((policy && policy.endpoints) || []).forEach(function (ep) {
      var selected = mode === 'manual' && preferred === ep.stable_id;
      var bits = [];
      bits.push(ep.kind === 'hdmi' ? 'Verified HDMI audio endpoint' :
        (ep.kind === 'speaker' ? 'Internal speaker' :
         (ep.kind === 'bluetooth' ? 'Bluetooth output' :
          (ep.kind === 'usb' ? 'USB audio output' : 'Physical audio output'))));
      if (ep.state) bits.push(ep.state);
      if (ep.muted) bits.push('muted');
      if (typeof ep.volume_percent === 'number') bits.push(ep.volume_percent + '%');
      addChoice(ep.stable_id, outputKindIcon(ep.kind) + '  ' + (ep.description || ep.node_name),
        bits.join(' · '), selected, !ep.available);
    });
  }

  function disableOutputControls() {
    ['sound-output-volume', 'sound-output-mute', 'sound-output-test'].forEach(function (id) {
      var el = outputEl(id);
      if (el) el.disabled = true;
    });
    var devices = outputEl('sound-output-devices');
    if (devices) devices.innerHTML = '';
  }

  function renderOutput(policy) {
    state.output = policy;
    var stateEl = outputEl('sound-output-state');
    if (!stateEl) return policy;
    if (!policy || policy.success === false) {
      disableOutputControls();
      setOutputText('sound-output-state', 'Audio output manager unavailable' +
        ((policy && (policy.detail || policy.error)) ? ': ' + (policy.detail || policy.error) : '.'));
      setOutputText('sound-output-detail', 'No route was changed. The bridge or nuxel-soundd is not answering.');
      return policy;
    }
    if (policy.mock === true) {
      disableOutputControls();
      setOutputText('sound-output-state', 'Audio output manager is in mock mode; no real route was read or changed.');
      return policy;
    }
    if (policy.backend_available === false) {
      disableOutputControls();
      setOutputText('sound-output-state', 'PipeWire audio server unavailable. No output can be selected.');
      setOutputText('sound-output-detail', policy.last_error || 'The audio session is not reachable.');
      return policy;
    }
    var current = policy.current || null;
    var hdmi = policy.hdmi || {};
    var lines = [];
    lines.push('Current output : ' + (current ? current.description : 'none routed'));
    if (current) {
      lines.push('Type           : ' + outputKindLabel(current.kind));
      lines.push('State          : ' + (current.state || 'available') +
        (current.default ? ' · default' : ''));
      lines.push('Volume         : ' + (current.muted ? 'muted' :
        (typeof current.volume_percent === 'number' ? current.volume_percent + '%' : 'unknown')));
    }
    lines.push('Routing mode   : ' + (policy.mode === 'manual' ? 'Manual override' : 'Automatic'));
    if (policy.mode === 'manual') {
      var pref = policy.preferred_name || policy.preferred_id || 'none';
      lines.push('Preferred      : ' + pref + (policy.preferred_available ? ' (available)' : ' (disconnected / pending)'));
    } else {
      lines.push('Policy         : Automatic prefers verified HDMI, then the last valid non-HDMI output.');
    }
    if (hdmi.available) {
      var pcm = hdmi.pcm || {};
      lines.push('HDMI/DP audio  : available · ' + (pcm.hw_path || hdmi.sink_name || 'real endpoint'));
    } else {
      lines.push('HDMI/DP audio  : unavailable' + (hdmi.blocker ? ' · ' + hdmi.blocker : ''));
    }
    var decision = policy.last_decision || {};
    if (decision.reason) lines.push('Last decision  : ' + decision.reason);
    if (policy.last_error) lines.push('Last error     : ' + policy.last_error);
    setOutputText('sound-output-state', lines.join('\n'));

    var routing = policy.mode === 'manual'
      ? 'Manual override: ' + (current ? current.description : 'no output') +
        ' is held. HDMI hotplug will not change this selection.'
      : 'Automatic routing is active. A verified HDMI endpoint takes priority; disconnect falls back safely.';
    if (policy.mode === 'manual' && policy.preferred_id && !policy.preferred_available) {
      routing += '\nThe preferred output is disconnected. ' +
        (current ? ('Fallback is active: ' + current.description + '.') : 'No fallback output is available.') +
        ' The preference is retained.';
    }
    setOutputText('sound-output-routing', routing);

    renderOutputDevices(policy, current && current.muted);
    var auto = outputEl('sound-output-auto');
    if (auto) {
      auto.classList.toggle('primary', policy.mode !== 'manual');
      auto.setAttribute('aria-pressed', policy.mode === 'automatic' ? 'true' : 'false');
    }
    var vol = outputEl('sound-output-volume');
    if (vol && !state.outputDragging) {
      var level = (current && typeof current.volume_percent === 'number') ? current.volume_percent : 0;
      vol.value = String(level);
      vol.disabled = !current;
    }
    setOutputText('sound-output-volume-val', (current && typeof current.volume_percent === 'number')
      ? current.volume_percent + '%' : '—');
    var mute = outputEl('sound-output-mute');
    if (mute) {
      mute.disabled = !current;
      mute.textContent = current && current.muted ? 'Unmute' : 'Mute';
    }
    var test = outputEl('sound-output-test');
    if (test) test.disabled = !current;
    if (policy.preferred_id && !policy.preferred_available && policy.mode === 'manual') {
      setOutputText('sound-output-detail',
        'Preferred output is disconnected. The current fallback is safe; choose another output or Automatic.');
    } else if (current) {
      setOutputText('sound-output-detail',
        'Test sound plays through the current output. Physical audibility is not inferred from a successful command.');
    } else {
      setOutputText('sound-output-detail', 'No physical output is currently routed.');
    }
    return policy;
  }

  function refreshOutputs(quiet) {
    if (state.outputBusy) return Promise.resolve(state.output);
    state.outputBusy = true;
    if (!quiet) setOutputText('sound-output-state', 'Reading real audio outputs…');
    return call('outputs', {}).then(function (doc) {
      state.outputBusy = false;
      state.outputInitialized = true;
      renderOutput(doc);
      return doc;
    }, function (err) {
      state.outputBusy = false;
      setOutputText('sound-output-state', 'Audio output error: ' +
        (err && err.message ? err.message : err));
      return null;
    });
  }

  function applyOutputResult(result, action) {
    if (!result || result.success === false) {
      setOutputText('sound-output-detail', action + ' failed: ' +
        ((result && (result.detail || result.error)) || 'no confirmation'));
      return refreshOutputs(true);
    }
    renderOutput(result);
    return result;
  }

  function setRoutingMode(mode) {
    setOutputText('sound-output-detail', 'Applying ' + mode + ' routing…');
    return call('set-routing', { mode: mode }).then(function (r) {
      return applyOutputResult(r, mode + ' routing');
    });
  }

  function selectOutput(id) {
    if (!id) return Promise.resolve(null);
    setOutputText('sound-output-detail', 'Selecting output…');
    return call('select-output', { id: id }).then(function (r) {
      return applyOutputResult(r, 'Output selection');
    });
  }

  function setOutputVolume(percent) {
    var pct = Math.max(0, Math.min(100, Number(percent)));
    setOutputText('sound-output-volume-val', pct + '%');
    return call('set-volume', { percent: pct }).then(function (r) {
      if (!r || r.success === false) {
        setOutputText('sound-output-detail', 'Volume unchanged: ' +
          ((r && (r.detail || r.error)) || 'backend error'));
      }
      return refreshOutputs(true);
    });
  }

  function toggleOutputMute() {
    var cur = state.output && state.output.current;
    var want = !(cur && cur.muted);
    return call('set-muted', { muted: want }).then(function (r) {
      if (!r || r.success === false) {
        setOutputText('sound-output-detail', 'Mute unchanged: ' +
          ((r && (r.detail || r.error)) || 'backend error'));
      }
      return refreshOutputs(true);
    });
  }

  function testOutput() {
    var btn = outputEl('sound-output-test');
    if (btn) btn.disabled = true;
    setOutputText('sound-output-detail', 'Queueing nuxel-pow.mp3 on the current output…');
    return call('test-output', {}).then(function (r) {
      if (r && r.success === false) {
        setOutputText('sound-output-detail', 'Test sound failed: ' +
          (r.detail || r.error || 'playback error'));
      } else {
        setOutputText('sound-output-detail', 'Queued through ' +
          ((r && (r.output || r.sink)) || 'the current output') +
          '. Confirm audibility on the physical speaker/TV; software cannot prove it.');
      }
      if (btn) btn.disabled = false;
      return refreshOutputs(true);
    }, function (e) {
      if (btn) btn.disabled = false;
      setOutputText('sound-output-detail', 'Test sound error: ' +
        (e && e.message ? e.message : e));
    });
  }

  function bindOutputs() {
    var refresh = outputEl('sound-output-refresh');
    if (refresh) refresh.addEventListener('click', function () { refreshOutputs(false); });
    var auto = outputEl('sound-output-auto');
    if (auto) auto.addEventListener('click', function () { setRoutingMode('automatic'); });
    var vol = outputEl('sound-output-volume');
    if (vol) {
      vol.addEventListener('pointerdown', function () { state.outputDragging = true; });
      vol.addEventListener('input', function () {
        setOutputText('sound-output-volume-val', vol.value + '%');
      });
      vol.addEventListener('change', function () {
        state.outputDragging = false;
        setOutputVolume(vol.value);
      });
    }
    var mute = outputEl('sound-output-mute');
    if (mute) mute.addEventListener('click', toggleOutputMute);
    var test = outputEl('sound-output-test');
    if (test) test.addEventListener('click', testOutput);
    document.querySelectorAll('.tab').forEach(function (tab) {
      if (tab.dataset.tab === 'sound') tab.addEventListener('click', function () { refreshOutputs(false); });
    });
    if (state.outputTimer) clearInterval(state.outputTimer);
    state.outputTimer = setInterval(function () {
      var sound = document.getElementById('tab-sound');
      if (!document.hidden && sound && sound.classList.contains('active')) refreshOutputs(true);
    }, 2000);
  }

  function bind() {
    var r = $('sound-refresh'); if (r) r.addEventListener('click', function () { refresh(false); });
    var b = $('sound-browse'); if (b) b.addEventListener('click', function () { browseFor('other'); });
    var t = $('sound-test-volume'); if (t) t.addEventListener('click', function () { previewAction('volume', null); });
    var input = $('sound-file-input');
    if (input) input.addEventListener('change', function () { importFor(browseAction || 'other', input.files && input.files[0]); });
    document.querySelectorAll('.tab').forEach(function (tab) {
      if (tab.dataset.tab === 'sound') tab.addEventListener('click', function () { refresh(false); });
    });
    document.addEventListener('visibilitychange', function () {
      if (!document.hidden) { refresh(true); refreshOutputs(true); }
    });
    if (state.timer) clearInterval(state.timer);
    state.timer = setInterval(function () { if (!document.hidden) refresh(true); }, 5000);
    bindOutputs();
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', function () {
    bind(); refresh(false); refreshOutputs(false);
  });
  else { bind(); refresh(false); refreshOutputs(false); }
  window.nuxelSoundSettings = { refresh: refresh, refreshOutputs: refreshOutputs,
                                state: function () { return state; } };
})();
