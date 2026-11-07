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
  var state = { sounds: [], assignments: {}, dirs: [], busy: false, timer: null };
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
  function bind() {
    var r = $('sound-refresh'); if (r) r.addEventListener('click', function () { refresh(false); });
    var b = $('sound-browse'); if (b) b.addEventListener('click', function () { browseFor('other'); });
    var t = $('sound-test-volume'); if (t) t.addEventListener('click', function () { previewAction('volume', null); });
    var input = $('sound-file-input');
    if (input) input.addEventListener('change', function () { importFor(browseAction || 'other', input.files && input.files[0]); });
    document.querySelectorAll('.tab').forEach(function (tab) {
      if (tab.dataset.tab === 'sound') tab.addEventListener('click', function () { refresh(false); });
    });
    document.addEventListener('visibilitychange', function () { if (!document.hidden) refresh(true); });
    if (state.timer) clearInterval(state.timer);
    state.timer = setInterval(function () { if (!document.hidden) refresh(true); }, 5000);
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', function () { bind(); refresh(false); });
  else { bind(); refresh(false); }
  window.nuxelSoundSettings = { refresh: refresh, state: function () { return state; } };
})();
