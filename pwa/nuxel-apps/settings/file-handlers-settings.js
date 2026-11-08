/* Nuxel Settings — File Handlers (PWNAGE-97000).
 *
 * The panel is a view over the bridge-owned schema.  It never writes a file,
 * shells out or keeps authoritative state in localStorage.  Every change is
 * validated and persisted by file-handlers.set; MIME defaults are written to
 * the user's mimeapps.list by that same backend.
 */
(function () {
  'use strict';

  var state = { view: null, draft: null, dirty: false, busy: false };
  var MIME_LABELS = {
    'image/jpeg': 'JPEG image', 'image/png': 'PNG image', 'image/webp': 'WebP image',
    'image/gif': 'GIF image', 'image/bmp': 'BMP image', 'image/tiff': 'TIFF image',
    'image/heic': 'HEIC image', 'image/heif': 'HEIF image', 'image/avif': 'AVIF image',
    'video/mp4': 'MP4 video', 'video/webm': 'WebM video',
    'video/x-matroska': 'Matroska video', 'video/quicktime': 'QuickTime video',
    'video/x-m4v': 'M4V video', 'video/x-msvideo': 'AVI video',
    'video/3gpp': '3GPP video', 'video/mpeg': 'MPEG video',
    'inode/directory': 'Folder', 'text/plain': 'Plain text',
    'application/pdf': 'PDF document', 'application/zip': 'ZIP archive',
    'application/x-tar': 'TAR archive', 'application/gzip': 'Gzip archive'
  };

  function $(id) { return document.getElementById(id); }
  function bridge() {
    try {
      if (window.NuxelBridge && typeof window.NuxelBridge.call === 'function') return window.NuxelBridge;
      if (window.parent && window.parent !== window && window.parent.NuxelBridge &&
          typeof window.parent.NuxelBridge.call === 'function') return window.parent.NuxelBridge;
    } catch (e) {}
    return null;
  }
  function rpc(verb, params) {
    var b = bridge();
    if (!b) return Promise.resolve({ success: false, error: 'Nuxel bridge unavailable', offline: true });
    try { return Promise.resolve(b.call('file-handlers', verb, params || {})); }
    catch (e) { return Promise.resolve({ success: false, error: String(e && e.message || e) }); }
  }
  function setState(text, warn) {
    var el = $('fh-state');
    if (!el) return;
    el.textContent = text;
    el.style.color = warn ? '#ffd166' : '';
  }
  function clone(o) { return JSON.parse(JSON.stringify(o || {})); }
  function esc(v) {
    return String(v == null ? '' : v).replace(/[&<>"']/g, function (c) {
      return ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'})[c];
    });
  }

  function markDirty() {
    state.dirty = true;
    setState('Unsaved changes — press Save File Handlers.', true);
  }

  function ensureDraft() {
    if (!state.draft) state.draft = clone((state.view && state.view.settings) || {});
    state.draft.schema_version = 1;
    state.draft.global_picker_policy = state.draft.global_picker_policy || 'ask';
    state.draft.app_picker_overrides = state.draft.app_picker_overrides || {};
    state.draft.mime_defaults = state.draft.mime_defaults || {};
    return state.draft;
  }

  function renderGlobal() {
    var sel = $('fh-global-policy');
    if (!sel) return;
    ensureDraft();
    sel.value = state.draft.global_picker_policy || 'ask';
    if (!sel.dataset.bound) {
      sel.dataset.bound = '1';
      sel.addEventListener('change', function () {
        ensureDraft().global_picker_policy = sel.value;
        markDirty();
      });
    }
  }

  function renderApps() {
    var box = $('fh-apps');
    var note = $('fh-apps-state');
    if (!box) return;
    var apps = (state.view && Array.isArray(state.view.apps)) ? state.view.apps : [];
    box.innerHTML = '';
    if (!apps.length) {
      if (note) note.textContent = 'No installed apps were discovered; unknown callers still inherit the global preference.';
      return;
    }
    ensureDraft();
    apps.forEach(function (app) {
      var row = document.createElement('div');
      row.className = 'app-row';
      var info = document.createElement('div');
      info.className = 'app-row-info';
      var name = document.createElement('div');
      name.className = 'app-row-name';
      name.textContent = app.name || app.id;
      var id = document.createElement('div');
      id.className = 'app-row-id';
      id.textContent = app.id + ' · ' + (app.package_format || app.type || 'app') +
        (app.installed === false ? ' · not installed' : '');
      info.appendChild(name); info.appendChild(id);
      var sel = document.createElement('select');
      sel.className = 'app-orientation-select';
      [['inherit', 'Inherit global'], ['ask', 'Ask every time'], ['gallery', 'Prefer Gallery'], ['files', 'Prefer Files']]
        .forEach(function (pair) {
          var o = document.createElement('option');
          o.value = pair[0]; o.textContent = pair[1];
          sel.appendChild(o);
        });
      sel.value = state.draft.app_picker_overrides[app.id] || 'inherit';
      sel.setAttribute('aria-label', 'Picker source for ' + (app.name || app.id));
      sel.addEventListener('change', function () {
        ensureDraft().app_picker_overrides[app.id] = sel.value;
        markDirty();
      });
      row.appendChild(info); row.appendChild(sel);
      box.appendChild(row);
    });
    if (note) note.textContent = apps.length + ' installed app' + (apps.length === 1 ? '' : 's') + '.';
  }

  function handlerLabel(handler) {
    return (handler.name || handler.desktop_id) + ' — ' + handler.desktop_id +
      (handler.package_format ? ' (' + handler.package_format + ')' : '');
  }

  function mimeGroups() {
    return [
      ['Images', ['image/jpeg', 'image/png', 'image/webp', 'image/gif', 'image/avif']],
      ['Videos', ['video/mp4', 'video/webm', 'video/x-matroska', 'video/quicktime']],
      ['Directories', ['inode/directory']],
      ['Documents and archives', ['text/plain', 'application/pdf', 'application/zip', 'application/gzip']]
    ];
  }

  function renderMime() {
    var box = $('fh-mime-list');
    var note = $('fh-mime-state');
    if (!box) return;
    var catalog = (state.view && state.view.mime_catalog) || {};
    var mimeMap = catalog.mime || {};
    ensureDraft();
    box.innerHTML = '';
    var rows = 0;
    mimeGroups().forEach(function (group) {
      var heading = document.createElement('div');
      heading.className = 'perm-group';
      heading.textContent = group[0];
      box.appendChild(heading);
      group[1].forEach(function (mime) {
        if (!mimeMap[mime]) return;
        var info = mimeMap[mime];
        var row = document.createElement('div');
        row.className = 'fh-mime-row';
        var label = document.createElement('label');
        var name = document.createElement('div');
        name.className = 'fh-mime-name';
        name.textContent = MIME_LABELS[mime] || mime;
        var meta = document.createElement('div');
        meta.className = 'fh-mime-meta';
        meta.textContent = mime + ' · effective: ' + (info.default || 'no default');
        label.appendChild(name); label.appendChild(meta);
        var select = document.createElement('select');
        select.setAttribute('aria-label', 'Default handler for ' + mime);
        var none = document.createElement('option');
        none.value = ''; none.textContent = 'No default';
        select.appendChild(none);
        (info.handlers || []).forEach(function (handler) {
          var option = document.createElement('option');
          option.value = handler.desktop_id;
          option.textContent = handlerLabel(handler);
          select.appendChild(option);
        });
        var chosen = state.draft.mime_defaults[mime] || '';
        if (chosen) {
          var exists = Array.prototype.some.call(select.options, function (o) { return o.value === chosen; });
          if (!exists) {
            var unavailable = document.createElement('option');
            unavailable.value = chosen;
            unavailable.textContent = chosen + ' (not associated)';
            select.appendChild(unavailable);
          }
        }
        select.value = chosen;
        select.addEventListener('change', function () {
          var draft = ensureDraft();
          if (select.value) draft.mime_defaults[mime] = select.value;
          else delete draft.mime_defaults[mime];
          markDirty();
        });
        row.appendChild(label); row.appendChild(select);
        box.appendChild(row);
        rows++;
      });
    });
    if (note) note.textContent = rows ? (rows + ' MIME type(s) with installed handler data.') :
      'No installed MIME handlers were discovered.';
  }

  function renderPortal() {
    var pre = $('fh-portal');
    if (!pre) return;
    var portal = (state.view && state.view.portal) || {};
    var last = portal.last_chooser || {};
    pre.textContent = [
      'XDG frontend:        ' + (portal.frontend_available ? 'available ' + (portal.frontend_owner || '') : 'NOT AVAILABLE'),
      'FileChooser backend: ' + (portal.filechooser_backend || 'missing') +
        (portal.backend_available ? ' (available)' : ' (NOT AVAILABLE)'),
      'Backend owner:       ' + (portal.backend_owner || 'not running / activatable'),
      'Backend descriptor:  ' + (portal.filechooser_backend_descriptor || 'missing'),
      'portals.conf:        ' + (portal.portals_conf || 'missing'),
      'Documents portal:    ' + (portal.documents_portal_available ? 'available' : 'not running'),
      'Desktop identity:    ' + (portal.desktop || 'unknown'),
      'Last chooser:        ' + (last.last_outcome || 'none') +
        (last.last_source ? ' · ' + last.last_source : '') +
        (last.selected_count ? ' · ' + last.selected_count + ' selected' : ''),
      'Note: ' + (portal.note || '')
    ].join('\n');
  }

  function renderAll() {
    renderGlobal();
    renderApps();
    renderMime();
    renderPortal();
    document.getElementById('tab-file-handlers').classList.toggle('fh-dirty', !!state.dirty);
    var save = $('fh-save');
    if (save) save.disabled = !!state.busy;
    var test = $('fh-test');
    if (test) test.disabled = !!state.busy;
  }

  function load() {
    if (state.busy) return;
    state.busy = true;
    setState('Loading File Handlers…');
    rpc('get', {}).then(function (view) {
      state.busy = false;
      if (!view || view.success === false) {
        setState('File Handlers unavailable: ' + ((view && (view.error || view.detail)) || 'bridge offline'), true);
        return;
      }
      state.view = view;
      state.draft = clone(view.settings || {});
      state.dirty = false;
      setState('Loaded from ' + (view.settings_path || 'the Nuxel bridge') + '.');
      renderAll();
    });
  }

  function save() {
    if (state.busy) return;
    state.busy = true;
    setState('Saving and validating MIME defaults…');
    rpc('set', { settings: ensureDraft() }).then(function (view) {
      state.busy = false;
      if (!view || view.success === false) {
        setState('Save failed: ' + ((view && (view.error || view.detail)) || 'unknown error'), true);
        return;
      }
      state.view = view;
      state.draft = clone(view.settings || {});
      state.dirty = false;
      setState('Saved. MIME defaults were re-read from the user mimeapps.list.');
      renderAll();
    });
  }

  function reset() {
    if (!window.confirm('Reset picker policies and restore system MIME defaults? Existing unrelated mimeapps.list entries are preserved.')) return;
    state.busy = true;
    setState('Resetting…');
    rpc('reset', {}).then(function (view) {
      state.busy = false;
      if (!view || view.success === false) {
        setState('Reset failed: ' + ((view && (view.error || view.detail)) || 'unknown error'), true);
        return;
      }
      state.view = view;
      state.draft = clone(view.settings || {});
      state.dirty = false;
      setState('Reset complete.');
      renderAll();
    });
  }

  function refreshHealth() {
    if (state.busy) return;
    state.busy = true;
    setState('Refreshing portal health…');
    rpc('get', {}).then(function (view) {
      state.busy = false;
      if (!view || view.success === false) {
        setState('Health refresh failed: ' + ((view && (view.error || view.detail)) || 'unknown error'), true);
        return;
      }
      state.view = view;
      if (!state.dirty) state.draft = clone(view.settings || {});
      setState('Portal health refreshed.');
      renderAll();
    });
  }

  function testPicker() {
    if (state.busy) return;
    state.busy = true;
    var out = $('fh-test-result');
    if (out) out.textContent = 'Opening the real XDG FileChooser… choose a harmless test file.';
    setState('Waiting for the real picker response…');
    rpc('test-picker', {}).then(function (result) {
      state.busy = false;
      if (out) out.textContent = JSON.stringify(result, null, 2);
      setState(result && result.success ? 'Test picker returned a real file.' :
        (result && result.cancelled ? 'Test picker cancelled cleanly.' :
         'Test picker did not complete: ' + ((result && (result.error || result.detail)) || 'unknown')), true);
      var test = $('fh-test'); if (test) test.disabled = false;
    });
  }

  function ready() {
    var tab = document.querySelector('.tab[data-tab="file-handlers"]');
    if (tab) tab.addEventListener('click', load);
    var saveBtn = $('fh-save'); if (saveBtn) saveBtn.addEventListener('click', save);
    var resetBtn = $('fh-reset'); if (resetBtn) resetBtn.addEventListener('click', reset);
    var refreshBtn = $('fh-refresh'); if (refreshBtn) refreshBtn.addEventListener('click', load);
    var healthBtn = $('fh-health'); if (healthBtn) healthBtn.addEventListener('click', refreshHealth);
    var testBtn = $('fh-test'); if (testBtn) testBtn.addEventListener('click', testPicker);
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', ready, { once: true });
  else ready();

  // Exported for the focused DOM-free source tests.
  window.NuxelFileHandlersSettings = {
    _labels: MIME_LABELS, _state: state, load: load, save: save
  };
})();
