/* Nuxel home-screen widgets (PWNAGE-30000).
   A real, registry-based widget layer integrated with the launcher's desktop
   pages.  Widget placement is per desktop and persisted in localStorage, so it
   survives launcher restarts.  The first widget type is Notes: it reads the
   same `nuxel-notes` document the Notes app persists, so edits appear without
   a reboot, and it never invents note content. */
(function (global) {
  'use strict';
  var KEY = 'nuxel.widgets';
  var NOTES_KEY = 'nuxel-notes';

  function read() {
    try { return JSON.parse(localStorage.getItem(KEY) || '{}'); }
    catch (e) { return {}; }
  }
  function write(doc) {
    try { localStorage.setItem(KEY, JSON.stringify(doc)); } catch (e) {}
  }
  function state() {
    var d = read();
    if (!Array.isArray(d.items)) d.items = [];
    if (typeof d.enabled !== 'boolean') d.enabled = true;
    return d;
  }
  function notes() {
    try { var raw = localStorage.getItem(NOTES_KEY); var list = raw ? JSON.parse(raw) : []; return Array.isArray(list) ? list : []; }
    catch (e) { return []; }
  }
  function esc(s) {
    var d = document.createElement('div');
    d.textContent = String(s == null ? '' : s);
    return d.innerHTML;
  }

  var types = {
    notes: {
      name: 'Notes',
      defaults: function () { return { w: 2, h: 2 }; },
      render: function (item, el) {
        var list = notes();
        var note = list.find(function (n) { return n.id === item.noteId; });
        el.className = 'nx-widget nx-widget-notes';
        if (!note) {
          el.innerHTML = '<div class="nx-widget-title">Notes</div>' +
            '<div class="nx-widget-body dim">Choose a note from the Notes widget menu.</div>';
          return;
        }
        el.innerHTML = '<div class="nx-widget-title">📝 ' + esc(note.title || 'Untitled') + '</div>' +
          '<div class="nx-widget-body">' + esc((note.body || '').substring(0, 220)) + '</div>';
        el.title = 'Open ' + (note.title || 'this note') + ' in Notes';
        el.addEventListener('click', function () {
          if (global.appRegistry && global.appRegistry.launchApp) global.appRegistry.launchApp('org.nuxel.Notes');
        });
      }
    }
  };

  function layer() {
    var l = document.getElementById('widgets-layer');
    if (l) return l;
    l = document.createElement('section');
    l.id = 'widgets-layer';
    l.className = 'widgets-layer';
    l.setAttribute('aria-label', 'Home screen widgets');
    var appList = document.getElementById('app-list');
    var grid = document.getElementById('app-grid');
    if (appList && appList.parentNode) appList.parentNode.insertBefore(l, appList);
    else if (grid) grid.appendChild(l);
    return l;
  }

  function renderPage(desktop) {
    var l = layer();
    var st = state();
    if (!st.enabled) { l.hidden = true; l.innerHTML = ''; return; }
    var rows = st.items.filter(function (w) { return Number(w.desktop) === Number(desktop); });
    if (!rows.length) { l.hidden = true; l.innerHTML = ''; return; }
    l.hidden = false;
    l.style.gridTemplateColumns = 'repeat(' + (global.launcher ? (global.launcher.settings.gridColumns || 4) : 4) + ', 1fr)';
    l.innerHTML = '';
    rows.forEach(function (w) {
      var el = document.createElement('div');
      el.dataset.widgetId = w.id;
      el.style.gridColumn = 'span ' + Math.max(1, Math.min(4, Number(w.w) || 2));
      el.style.gridRow = 'span ' + Math.max(1, Math.min(3, Number(w.h) || 2));
      var type = types[w.type];
      if (type) type.render(w, el);
      l.appendChild(el);
    });
  }

  function add(typeId, config) {
    if (!types[typeId]) return null;
    var st = state();
    var item = Object.assign({ id: 'widget-' + Date.now().toString(36), type: typeId, desktop: 1 }, types[typeId].defaults(), config || {});
    st.items.push(item);
    write(st);
    renderPage(global.launcher ? global.launcher.currentPage : 0);
    return item;
  }
  function remove(id) {
    var st = state();
    st.items = st.items.filter(function (w) { return w.id !== id; });
    write(st);
    renderPage(global.launcher ? global.launcher.currentPage : 0);
  }
  function setEnabled(on) {
    var st = state(); st.enabled = !!on; write(st);
    renderPage(global.launcher ? global.launcher.currentPage : 0);
  }

  // Re-render when the Notes app writes its document (same-origin storage event)
  // or when the launcher's own scripts change the visible desktop.
  global.addEventListener('storage', function (e) {
    if (e && e.key === NOTES_KEY && global.launcher) renderPage(global.launcher.currentPage);
  });

  global.NuxelWidgets = {
    types: types,
    state: state,
    add: add,
    remove: remove,
    setEnabled: setEnabled,
    renderPage: renderPage,
    notes: notes,
    KEY: KEY,
    NOTES_KEY: NOTES_KEY
  };
})(window);
