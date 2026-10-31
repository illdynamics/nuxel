/* Nuxel home-screen widgets (PWNAGE-44000).
 *
 * DESKTOP CONTRACT: widget.desktop is a ONE-BASED human desktop number
 * (1..desktopCount).  launcher.currentPage is ZERO-BASED.  renderPage() takes
 * the launcher's zero-based page index and compares desktop === index + 1.
 * Existing PWNAGE-30000 documents already stored the user's chosen desktop
 * number, so schema 1 -> 2 is a lossless marker migration (values unchanged).
 *
 * The Notes widget is a real sticky note: add/remove, note selection, resize
 * and reposition are persisted in localStorage.  Widget content is always
 * rendered with textContent, never interpolated HTML.  The Notes app publishes
 * `nuxel:notes-updated` after a successful save so Home reflects it without
 * relying on cross-document storage events.
 */
(function (global) {
  'use strict';
  var KEY = 'nuxel.widgets';
  var NOTES_KEY = 'nuxel-notes';
  var SCHEMA = 2;
  var MAX_DESKTOPS = 8;

  function clampInt(value, lo, hi, fallback) {
    value = Number(value);
    if (!Number.isFinite(value)) return fallback;
    value = Math.round(value);
    return Math.max(lo, Math.min(hi, value));
  }
  function read() {
    try { var d = JSON.parse(localStorage.getItem(KEY) || '{}'); return d && typeof d === 'object' ? d : {}; }
    catch (e) { return {}; }
  }
  function write(doc) {
    try { localStorage.setItem(KEY, JSON.stringify(doc)); } catch (e) {}
  }
  function state() {
    var d = read();
    if (!Array.isArray(d.items)) d.items = [];
    if (typeof d.enabled !== 'boolean') d.enabled = true;
    // Migrate schema 1 documents in place.  PWNAGE-30000 already used the
    // one-based value the selector showed, so no desktop is silently moved.
    if (Number(d.schema_version || 1) < SCHEMA) {
      d.items.forEach(function (w) { w.desktop = clampInt(w.desktop, 1, MAX_DESKTOPS, 1); });
      d.schema_version = SCHEMA;
      write(d);
    }
    d.items.forEach(function (w) {
      w.desktop = clampInt(w.desktop, 1, MAX_DESKTOPS, 1);
      w.w = clampInt(w.w, 1, 4, 2);
      w.h = clampInt(w.h, 1, 4, 2);
    });
    return d;
  }
  function notes() {
    try {
      var raw = localStorage.getItem(NOTES_KEY);
      var list = raw ? JSON.parse(raw) : [];
      return Array.isArray(list) ? list.filter(function (n) { return n && typeof n === 'object'; }) : [];
    } catch (e) { return []; }
  }
  function noteById(id) {
    if (!id) return null;
    var list = notes();
    for (var i = 0; i < list.length; i++) if (list[i].id === id) return list[i];
    return null;
  }
  function pageIndex() {
    return global.launcher && Number.isFinite(Number(global.launcher.currentPage))
      ? Math.max(0, Number(global.launcher.currentPage)) : 0;
  }
  function launcherColumns() {
    return clampInt(global.launcher && global.launcher.settings && global.launcher.settings.gridColumns, 3, 6, 4);
  }

  function text(tag, cls, value) {
    var n = document.createElement(tag);
    if (cls) n.className = cls;
    if (value !== undefined) n.textContent = String(value);
    return n;
  }

  function openNote(item) {
    if (!item.noteId) return;
    try {
      document.dispatchEvent(new CustomEvent('nuxel:notes-open', { detail: { noteId: item.noteId } }));
      window.dispatchEvent(new CustomEvent('nuxel:notes-open', { detail: { noteId: item.noteId } }));
    } catch (e) {}
    try { localStorage.setItem('nuxel.notes.open', item.noteId); } catch (e) {}
    if (global.appRegistry && global.appRegistry.launchApp) global.appRegistry.launchApp('org.nuxel.Notes');
  }

  var types = {
    notes: {
      name: 'Notes',
      defaults: function () { return { w: 2, h: 2 }; },
      render: function (item, el) {
        var note = noteById(item.noteId) || (!item.noteId ? notes()[0] : null);
        el.className = 'nx-widget nx-widget-notes';
        el.setAttribute('role', 'button');
        el.tabIndex = 0;
        el.title = note ? ('Open ' + (note.title || 'this note') + ' in Notes') : 'Choose a note in Home Settings';
        el.appendChild(text('div', 'nx-widget-title', note ? (note.title || 'Untitled') : 'Notes'));
        var body = text('div', 'nx-widget-body' + (note ? '' : ' dim'),
          note ? String(note.body || '').substring(0, 320) : 'No note selected. Add one from Home Settings.');
        el.appendChild(body);
        if (note) {
          el.addEventListener('click', function (ev) {
            if (ev.target.closest && ev.target.closest('.nx-widget-control')) return;
            openNote(item);
          });
          el.addEventListener('keydown', function (ev) {
            if (ev.key === 'Enter' || ev.key === ' ') { ev.preventDefault(); openNote(item); }
          });
        }
        // Context controls (never part of the note body).
        var controls = text('div', 'nx-widget-controls');
        var resize = text('button', 'nx-widget-control nx-widget-resize', '⇲');
        resize.type = 'button'; resize.title = 'Resize widget'; resize.setAttribute('aria-label', 'Resize Notes widget');
        var remove = text('button', 'nx-widget-control nx-widget-remove', '×');
        remove.type = 'button'; remove.title = 'Remove widget'; remove.setAttribute('aria-label', 'Remove Notes widget');
        controls.appendChild(resize); controls.appendChild(remove);
        el.appendChild(controls);
        resize.addEventListener('click', function (ev) { ev.stopPropagation(); });
        remove.addEventListener('click', function (ev) { ev.stopPropagation(); removeWidget(item.id); });
        bindResize(resize, item, el);
        bindMove(el, item);
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

  function currentRows() {
    var st = state();
    if (!st.enabled) return [];
    var desktop = pageIndex() + 1;
    return st.items.filter(function (w) { return clampInt(w.desktop, 1, MAX_DESKTOPS, 1) === desktop; });
  }

  function renderPage(pageIdx) {
    var l = layer();
    var idx = Number.isFinite(Number(pageIdx)) ? Math.max(0, Number(pageIdx)) : pageIndex();
    var st = state();
    if (!st.enabled) { l.hidden = true; l.textContent = ''; return; }
    var desktop = idx + 1;             // persisted value is one-based
    var rows = st.items.filter(function (w) { return clampInt(w.desktop, 1, MAX_DESKTOPS, 1) === desktop; });
    if (!rows.length) { l.hidden = true; l.textContent = ''; return; }
    l.hidden = false;
    l.style.gridTemplateColumns = 'repeat(' + launcherColumns() + ', 1fr)';
    l.textContent = '';
    rows.forEach(function (w) {
      var el = document.createElement('div');
      el.dataset.widgetId = w.id;
      el.dataset.desktop = String(w.desktop);
      el.style.gridColumn = 'span ' + clampInt(w.w, 1, launcherColumns(), 2);
      el.style.gridRow = 'span ' + clampInt(w.h, 1, 4, 2);
      var type = types[w.type];
      if (type) type.render(w, el);
      l.appendChild(el);
    });
  }

  function add(typeId, config) {
    if (!types[typeId]) return null;
    var st = state();
    var cfg = Object.assign({}, config || {});
    if (typeId === 'notes') {
      var list = notes();
      if (!cfg.noteId) cfg.noteId = list.length ? list[0].id : '';
      if (!cfg.noteId || !noteById(cfg.noteId)) return null;   // no broken empty widget
    }
    var maxDesktop = global.launcher && global.launcher.settings
      ? clampInt(global.launcher.settings.desktopCount, 1, MAX_DESKTOPS, 1) : MAX_DESKTOPS;
    var desktop = clampInt(cfg.desktop, 1, maxDesktop, pageIndex() + 1);
    var item = Object.assign({ id: 'widget-' + Date.now().toString(36) + '-' + Math.floor(Math.random() * 1e4).toString(36),
      type: typeId, desktop: desktop, w: 2, h: 2 }, types[typeId].defaults(), cfg);
    item.desktop = desktop;
    st.items.push(item);
    st.schema_version = SCHEMA;
    write(st);
    if (global.launcher && desktop === pageIndex() + 1) renderPage(pageIndex());
    return item;
  }
  function update(id, patch) {
    var st = state();
    var item = st.items.find(function (w) { return w.id === id; });
    if (!item) return null;
    Object.assign(item, patch || {});
    item.desktop = clampInt(item.desktop, 1, MAX_DESKTOPS, 1);
    item.w = clampInt(item.w, 1, launcherColumns(), 2);
    item.h = clampInt(item.h, 1, 4, 2);
    write(st);
    renderPage(pageIndex());
    return item;
  }
  function removeWidget(id) {
    var st = state();
    st.items = st.items.filter(function (w) { return w.id !== id; });
    write(st);
    renderPage(pageIndex());
  }
  function setEnabled(on) {
    var st = state(); st.enabled = !!on; write(st);
    renderPage(pageIndex());
  }

  // Resize handle: pointer events only, capture on the handle, saved once on
  // release so a drag cannot write localStorage on every move.
  function bindResize(handle, item, el) {
    var start = null;
    handle.addEventListener('pointerdown', function (ev) {
      ev.preventDefault(); ev.stopPropagation();
      try { handle.setPointerCapture(ev.pointerId); } catch (e) {}
      var rect = el.getBoundingClientRect();
      start = { id: ev.pointerId, x: ev.clientX, y: ev.clientY, w: item.w, h: item.h,
        cellW: Math.max(24, rect.width / Math.max(1, item.w)),
        rowH: Math.max(24, rect.height / Math.max(1, item.h)) };
      handle.dataset.resizing = 'true';
    });
    handle.addEventListener('pointermove', function (ev) {
      if (!start || ev.pointerId !== start.id) return;
      ev.preventDefault();
      var w = clampInt(start.w + (ev.clientX - start.x) / start.cellW, 1, launcherColumns(), start.w);
      var h = clampInt(start.h + (ev.clientY - start.y) / start.rowH, 1, 4, start.h);
      el.style.gridColumn = 'span ' + w;
      el.style.gridRow = 'span ' + h;
      start.nextW = w; start.nextH = h;
    });
    var finish = function (ev) {
      if (!start || (ev && ev.pointerId !== start.id)) return;
      try { handle.releasePointerCapture(start.id); } catch (e) {}
      delete handle.dataset.resizing;
      if (start.nextW || start.nextH) update(item.id, { w: start.nextW || start.w, h: start.nextH || start.h });
      start = null;
    };
    handle.addEventListener('pointerup', finish);
    handle.addEventListener('pointercancel', finish);
    handle.addEventListener('lostpointercapture', finish);
  }

  // Reposition: a 350 ms hold on the widget surface, then drag over another
  // widget and release.  The persisted order determines the sticky stack.
  function bindMove(el, item) {
    var press = null, timer = null, moved = false;
    el.addEventListener('pointerdown', function (ev) {
      if (ev.button !== undefined && ev.button !== 0) return;
      if (ev.target.closest && ev.target.closest('.nx-widget-control')) return;
      press = { id: ev.pointerId, x: ev.clientX, y: ev.clientY };
      moved = false;
      timer = setTimeout(function () {
        timer = null;
        if (!press) return;
        el.dataset.moving = 'true';
        try { el.setPointerCapture(press.id); } catch (e) {}
      }, 350);
    });
    el.addEventListener('pointermove', function (ev) {
      if (!press || ev.pointerId !== press.id) return;
      if (Math.abs(ev.clientX - press.x) > 8 || Math.abs(ev.clientY - press.y) > 8) {
        moved = true;
        if (!el.dataset.moving) { if (timer) { clearTimeout(timer); timer = null; } press = null; }
        return;
      }
    });
    var finish = function (ev) {
      if (!press || (ev && ev.pointerId !== press.id)) return;
      if (timer) { clearTimeout(timer); timer = null; }
      var wasMoving = el.dataset.moving === 'true';
      delete el.dataset.moving;
      if (wasMoving) {
        var under = ev && document.elementFromPoint ? document.elementFromPoint(ev.clientX, ev.clientY) : null;
        var target = under && under.closest ? under.closest('.nx-widget') : null;
        if (target && target !== el && target.dataset.widgetId) reorder(item.id, target.dataset.widgetId);
      }
      press = null;
    };
    el.addEventListener('pointerup', finish);
    el.addEventListener('pointercancel', function () { if (timer) clearTimeout(timer); timer = null; press = null; delete el.dataset.moving; });
  }

  function reorder(dragId, targetId) {
    var st = state();
    var from = st.items.findIndex(function (w) { return w.id === dragId; });
    var to = st.items.findIndex(function (w) { return w.id === targetId; });
    if (from < 0 || to < 0 || from === to) return;
    var dragged = st.items.splice(from, 1)[0];
    to = st.items.findIndex(function (w) { return w.id === targetId; });
    st.items.splice(to, 0, dragged);
    write(st);
    renderPage(pageIndex());
  }

  function onNotesChanged() {
    if (global.launcher) renderPage(pageIndex());
  }
  if (typeof global.addEventListener === 'function') global.addEventListener('storage', function (e) {
    if (e && (e.key === NOTES_KEY || e.key === KEY)) onNotesChanged();
  });
  document.addEventListener('nuxel:notes-updated', onNotesChanged);
  if (typeof window.addEventListener === 'function') window.addEventListener('nuxel:notes-updated', onNotesChanged);
  document.addEventListener('nuxel:widgets-changed', onNotesChanged);

  global.NuxelWidgets = {
    types: types,
    state: state,
    add: add,
    update: update,
    remove: removeWidget,
    setEnabled: setEnabled,
    renderPage: renderPage,
    notes: notes,
    currentRows: currentRows,
    KEY: KEY,
    NOTES_KEY: NOTES_KEY,
    SCHEMA: SCHEMA
  };
})(window);
