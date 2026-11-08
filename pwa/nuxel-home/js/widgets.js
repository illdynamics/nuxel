/* Nuxel home widgets rendered from the unified desktop layout (PWNAGE-84000).
 *
 * Positions, desktop ownership and collision checking live in
 * NuxelDesktopLayout.  This module only renders the current page's widget
 * entities and provides their content-specific controls.
 */
(function (global) {
  'use strict';
  var NOTES_KEY = 'nuxel-notes';
  var LEGACY_KEY = 'nuxel.widgets';
  var MAX_DESKTOPS = 8;
  var clockTimer = null;

  function clampInt(value, lo, hi, fallback) {
    value = Number(value);
    if (!Number.isFinite(value)) return fallback;
    return Math.max(lo, Math.min(hi, Math.round(value)));
  }
  function notes() {
    try {
      var list = JSON.parse(localStorage.getItem(NOTES_KEY) || '[]');
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
  function launcherRows() {
    return clampInt(global.launcher && global.launcher.settings && global.launcher.settings.gridRows, 4, 7, 5);
  }
  function layout() {
    if (global.launcher && global.launcher.desktopLayout) return global.launcher.desktopLayout;
    if (!window.NuxelDesktopLayout) return null;
    if (!layout._instance) {
      var legacy = null;
      try { legacy = JSON.parse(localStorage.getItem(LEGACY_KEY) || 'null'); } catch (e) {}
      layout._instance = window.NuxelDesktopLayout.load({
        columns: launcherColumns(), rows: launcherRows(),
        desktopCount: clampInt(global.launcher && global.launcher.settings && global.launcher.settings.desktopCount, 1, MAX_DESKTOPS, 2),
        apps: [], appOrder: [], legacyWidgets: legacy
      });
    }
    return layout._instance;
  }
  function save() {
    var L = layout();
    if (L) L.save();
    try { document.dispatchEvent(new CustomEvent('nuxel:widgets-changed')); } catch (e) {}
  }
  function text(tag, cls, value) {
    var n = document.createElement(tag);
    if (cls) n.className = cls;
    if (value !== undefined) n.textContent = String(value);
    return n;
  }
  function toast(msg) {
    try { global.dispatchEvent(new CustomEvent('nuxel:toast', { detail: { text: msg } })); } catch (e) {}
  }
  function openNote(item) {
    if (!item.noteId) return;
    try { localStorage.setItem('nuxel.notes.open', item.noteId); } catch (e) {}
    try { document.dispatchEvent(new CustomEvent('nuxel:notes-open', { detail: { noteId: item.noteId } })); } catch (e) {}
    try {
      var reg = global.appRegistry || (global.parent && global.parent.appRegistry);
      if (reg && typeof reg.launchApp === 'function') reg.launchApp('org.nuxel.Notes');
    } catch (e) {}
  }
  function openCalendar(date) {
    try { if (date) localStorage.setItem('nuxel.calendar.openDate', date); } catch (e) {}
    try {
      var reg = global.appRegistry || (global.parent && global.parent.appRegistry);
      if (reg && typeof reg.launchApp === 'function') reg.launchApp('org.nuxel.Calendar');
    } catch (e) {}
  }
  function bridgeCall(ns, verb, params) {
    var b = global.NuxelBridge;
    if (!b || typeof b.call !== 'function') return Promise.resolve({ success: false, offline: true });
    return Promise.resolve(b.call(ns, verb, params || {})).catch(function (e) { return { success: false, error: String(e) }; });
  }

  var types = {
    notes: {
      name: 'Notes', description: 'A chosen note from ~/Notes, updated when Notes saves.',
      sizes: [[2, 2], [3, 2], [2, 3]], dataSources: ['~/Notes', 'nuxel:notes-updated'],
      defaults: function () { return { w: 2, h: 2 }; },
      render: function (item, el) {
        var note = noteById(item.noteId) || (!item.noteId ? notes()[0] : null);
        el.className = 'nx-widget nx-widget-notes';
        el.setAttribute('role', 'button'); el.tabIndex = 0;
        el.title = note ? ('Open ' + (note.title || 'this note') + ' in Notes') : 'Choose a note in Home Settings';
        el.appendChild(text('div', 'nx-widget-title', note ? (note.title || 'Untitled') : 'Notes'));
        el.appendChild(text('div', 'nx-widget-body' + (note ? '' : ' dim'),
          note ? String(note.body || '').substring(0, 420) : 'No note selected. Add one from Home Settings.'));
        if (note) {
          el.addEventListener('click', function (ev) {
            if (ev.target.closest && ev.target.closest('.nx-widget-control')) return;
            openNote(item);
          });
          el.addEventListener('keydown', function (ev) {
            if (ev.key === 'Enter' || ev.key === ' ') { ev.preventDefault(); openNote(item); }
          });
        }
      }
    },
    clock: {
      name: 'Clock', description: 'Live kernel clock and date.',
      sizes: [[2, 1], [2, 2], [3, 1]], dataSources: ['system clock'],
      defaults: function () { return { w: 2, h: 1 }; },
      render: function (item, el) {
        el.className = 'nx-widget nx-widget-clock';
        el.appendChild(text('div', 'nx-widget-title', 'Clock'));
        var time = text('div', 'nx-clock-time', '--:--');
        var date = text('div', 'nx-clock-date', '—');
        el.appendChild(time); el.appendChild(date);
        var update = function () {
          var n = new Date();
          // Minutes are all the widget shows.  The old seconds display forced a
          // full WebKit/phoc/wl-fb composite every second on this software-
          // rendered handset; this is the single largest idle cost we measured.
          time.textContent = String(n.getHours()).padStart(2, '0') + ':' +
            String(n.getMinutes()).padStart(2, '0');
          date.textContent = n.toLocaleDateString([], { weekday: 'long', month: 'long', day: 'numeric' });
        };
        update(); el.__nuxelClockUpdate = update;
        if (!clockTimer) {
          var scheduleMinute = function () {
            var now = new Date();
            var delay = Math.max(1000, 60000 - (now.getSeconds() * 1000 + now.getMilliseconds()));
            clockTimer = global.setTimeout(function () {
              document.querySelectorAll('.nx-widget-clock').forEach(function (node) {
                if (node.__nuxelClockUpdate) node.__nuxelClockUpdate();
              });
              scheduleMinute();
            }, delay);
          };
          scheduleMinute();
        }
      }
    },
    calendar: {
      name: 'Calendar', description: 'Real Calendar events; opens the chosen date.',
      sizes: [[2, 2], [3, 2], [4, 2]], dataSources: ['caldav', 'nuxel:calendar-updated'],
      defaults: function () { return { w: 2, h: 2 }; },
      render: function (item, el) {
        el.className = 'nx-widget nx-widget-calendar';
        el.appendChild(text('div', 'nx-widget-title', 'Calendar'));
        var body = text('div', 'nx-widget-body', 'Reading Calendar…');
        el.appendChild(body);
        var draw = function (events) {
          var now = new Date();
          var today = now.getFullYear() + '-' + String(now.getMonth() + 1).padStart(2, '0') + '-' + String(now.getDate()).padStart(2, '0');
          var upcoming = (Array.isArray(events) ? events : []).filter(function (e) {
            return e && typeof e.date === 'string' && e.date >= today;
          }).sort(function (a, b) { return (a.date + (a.startTime || '')).localeCompare(b.date + (b.startTime || '')); }).slice(0, 3);
          body.textContent = upcoming.length ? upcoming.map(function (e) {
            return e.date + (e.allDay ? ' · all day' : (e.startTime ? ' · ' + e.startTime : '')) + ' · ' + (e.title || 'Untitled');
          }).join('\n') : 'No upcoming events. Tap to open Calendar.';
        };
        var cached = [];
        try { cached = JSON.parse(localStorage.getItem('nuxel-calendar-events') || '[]'); } catch (e) {}
        draw(cached);
        bridgeCall('caldav', 'list', {}).then(function (r) {
          if (r && r.success !== false && Array.isArray(r.events)) {
            draw(r.events);
            try { localStorage.setItem('nuxel-calendar-events', JSON.stringify(r.events)); } catch (e) {}
          }
        });
        el.addEventListener('click', function (ev) {
          if (ev.target.closest && ev.target.closest('.nx-widget-control')) return;
          openCalendar();
        });
      }
    }
  };

  function layer() {
    var appList = document.getElementById('app-list');
    var l = document.getElementById('widgets-layer');
    if (!l) {
      l = document.createElement('section');
      l.id = 'widgets-layer';
      (appList || document.body).appendChild(l);
    }
    if (appList && l.parentNode !== appList) appList.appendChild(l);
    l.className = 'widgets-layer unified-widget-layer';
    l.setAttribute('aria-label', 'Home screen widgets');
    return l;
  }
  function currentEntities(page) {
    var L = layout();
    if (!L || L.widgetsEnabled === false) return [];
    return L.widgets(page).map(function (e) {
      return Object.assign({}, e.config || {}, {
        id: e.id, type: e.widget_type, desktop: e.desktop + 1,
        x: e.x, y: e.y, w: e.w, h: e.h
      });
    });
  }
  function renderPage(pageIdx) {
    var l = layer();
    var idx = Number.isFinite(Number(pageIdx)) ? Math.max(0, Number(pageIdx)) : pageIndex();
    var L = layout();
    if (!L || L.widgetsEnabled === false) { l.hidden = true; l.textContent = ''; return; }
    var rows = currentEntities(idx);
    if (!rows.length) { l.hidden = true; l.textContent = ''; return; }
    l.hidden = false;
    l.textContent = '';
    rows.forEach(function (w) {
      var el = document.createElement('div');
      el.dataset.widgetId = w.id;
      el.dataset.desktop = String(w.desktop);
      el.style.gridColumn = (w.x + 1) + ' / span ' + w.w;
      el.style.gridRow = (w.y + 1) + ' / span ' + w.h;
      var type = types[w.type];
      if (type) type.render(w, el);
      if (!el.className) el.className = 'nx-widget nx-widget-' + w.type;
      var controls = text('div', 'nx-widget-controls');
      var resize = text('button', 'nx-widget-control nx-widget-resize', '⇲');
      resize.type = 'button'; resize.title = 'Resize widget'; resize.setAttribute('aria-label', 'Resize widget');
      var remove = text('button', 'nx-widget-control nx-widget-remove', '×');
      remove.type = 'button'; remove.title = 'Remove widget'; remove.setAttribute('aria-label', 'Remove widget');
      // PWNAGE-88000: widgets share the Desktop-N picker with app icons.  Move
      // remains the existing long-press drag (bindMove) on a non-control area.
      var desktopBtn = text('button', 'nx-widget-control nx-widget-desktop', 'D' + w.desktop);
      desktopBtn.type = 'button'; desktopBtn.title = 'Move widget to another desktop';
      desktopBtn.setAttribute('aria-label', 'Move widget to another desktop');
      controls.appendChild(resize); controls.appendChild(remove); controls.appendChild(desktopBtn);
      el.appendChild(controls);
      resize.addEventListener('click', function (ev) { ev.stopPropagation(); });
      remove.addEventListener('click', function (ev) { ev.stopPropagation(); removeWidget(w.id); });
      desktopBtn.addEventListener('click', function (ev) { ev.stopPropagation(); pickDesktop(w); });
      bindResize(resize, w, el);
      bindMove(el, w);
      l.appendChild(el);
    });
  }

  function add(typeId, config) {
    if (!types[typeId]) return null;
    var L = layout();
    if (!L) return null;
    var cfg = Object.assign({}, config || {});
    if (typeId === 'notes') {
      var list = notes();
      if (!cfg.noteId) cfg.noteId = list.length ? list[0].id : '';
      if (!cfg.noteId || !noteById(cfg.noteId)) return null;
    }
    var maxDesktop = global.launcher && global.launcher.settings
      ? clampInt(global.launcher.settings.desktopCount, 1, MAX_DESKTOPS, 1) : MAX_DESKTOPS;
    cfg.desktop = clampInt(cfg.desktop, 1, maxDesktop, pageIndex() + 1);
    var entity = L.addWidget(typeId, cfg, types[typeId].defaults());
    if (!entity) return null;
    save();
    renderPage(pageIndex());
    return Object.assign({}, cfg, { id: entity.id, type: typeId, desktop: entity.desktop + 1, x: entity.x, y: entity.y, w: entity.w, h: entity.h });
  }
  function update(id, patch) {
    var L = layout(); if (!L) return null;
    var e = L.entity(id); if (!e) return null;
    if (patch.w !== undefined || patch.h !== undefined) L.resize(id, patch.w === undefined ? e.w : patch.w, patch.h === undefined ? e.h : patch.h);
    if (patch.desktop !== undefined || patch.x !== undefined || patch.y !== undefined) {
      var d = patch.desktop === undefined ? e.desktop : clampInt(Number(patch.desktop) - 1, 0, L.desktopCount - 1, e.desktop);
      var x = patch.x === undefined ? e.x : patch.x, y = patch.y === undefined ? e.y : patch.y;
      L.move(id, d, x, y);
    }
    if (patch.noteId !== undefined) e.config.noteId = patch.noteId;
    if (patch.view !== undefined) e.config.view = patch.view;
    save(); renderPage(pageIndex());
    var out = Object.assign({}, e.config || {}, { id: e.id, type: e.widget_type, desktop: e.desktop + 1, x: e.x, y: e.y, w: e.w, h: e.h });
    return out;
  }
  function removeWidget(id) {
    var L = layout(); if (!L) return;
    L.remove(id); save(); renderPage(pageIndex());
  }
  function pickDesktop(w) {
    var menu = document.getElementById('nuxel-widget-desktop-picker');
    if (!menu) {
      menu = document.createElement('div');
      menu.id = 'nuxel-widget-desktop-picker';
      menu.className = 'launcher-edit-toolbar desktop-picker';
      document.body.appendChild(menu);
    }
    menu.replaceChildren();
    var L = layout();
    var max = L ? L.desktopCount : (global.launcher && global.launcher.settings && global.launcher.settings.desktopCount) || 2;
    for (var i = 0; i < max; i++) {
      (function (d) {
        var b = document.createElement('button');
        b.type = 'button';
        b.textContent = 'Desktop ' + (d + 1);
        b.onclick = function () {
          menu.remove();
          update(w.id, { desktop: d + 1 });
        };
        menu.appendChild(b);
      })(i);
    }
  }
  function setEnabled(on) {
    var L = layout(); if (!L) return;
    L.widgetsEnabled = !!on; save(); renderPage(pageIndex());
  }
  function registry() {
    return Object.keys(types).map(function (id) {
      var t = types[id];
      return { id: id, name: t.name || id, description: t.description || '',
               sizes: t.sizes || [[2, 2]], dataSources: t.dataSources || [] };
    });
  }

  function bindResize(handle, item, el) {
    var start = null;
    handle.addEventListener('pointerdown', function (ev) {
      ev.preventDefault(); ev.stopPropagation();
      try { handle.setPointerCapture(ev.pointerId); } catch (e) {}
      var rect = el.getBoundingClientRect();
      start = { id: ev.pointerId, x: ev.clientX, y: ev.clientY, w: item.w, h: item.h,
        cellW: Math.max(24, rect.width / Math.max(1, item.w)),
        rowH: Math.max(24, rect.height / Math.max(1, item.h)) };
      el.classList.add('resizing');
    });
    handle.addEventListener('pointermove', function (ev) {
      if (!start || ev.pointerId !== start.id) return;
      ev.preventDefault();
      var w = clampInt(start.w + (ev.clientX - start.x) / start.cellW, 1, launcherColumns(), start.w);
      var h = clampInt(start.h + (ev.clientY - start.y) / start.rowH, 1, launcherRows(), start.h);
      el.style.gridColumn = (item.x + 1) + ' / span ' + w;
      el.style.gridRow = (item.y + 1) + ' / span ' + h;
      start.nextW = w; start.nextH = h;
    });
    var finish = function (ev) {
      if (!start || (ev && ev.pointerId !== start.id)) return;
      try { handle.releasePointerCapture(start.id); } catch (e) {}
      el.classList.remove('resizing');
      if ((start.nextW && start.nextW !== item.w) || (start.nextH && start.nextH !== item.h)) {
        var L = layout();
        var ok = L && L.resize(item.id, start.nextW || item.w, start.nextH || item.h);
        if (!ok) toast('That size collides with another icon or widget.');
        save();
      }
      start = null; renderPage(pageIndex());
    };
    handle.addEventListener('pointerup', finish);
    handle.addEventListener('pointercancel', finish);
    handle.addEventListener('lostpointercapture', finish);
  }

  // Drag state machine: long-press on a non-control area, stable body ghost,
  // pointer capture on the document, one-second edge dwell, drop by grid cell.
  function bindMove(el, item) {
    var press = null, holdTimer = null, dragging = false, ghost = null, edge = 0, edgeTimer = null, last = null;
    function cleanup(cancel) {
      if (holdTimer) { clearTimeout(holdTimer); holdTimer = null; }
      if (edgeTimer) { clearTimeout(edgeTimer); edgeTimer = null; }
      if (ghost) { ghost.remove(); ghost = null; }
      document.body.classList.remove('launcher-dragging', 'edge-dwell-left', 'edge-dwell-right');
      el.classList.remove('nx-widget-dragging');
      global.removeEventListener('pointermove', move, true);
      global.removeEventListener('pointerup', finish, true);
      global.removeEventListener('pointercancel', cancelFn, true);
      if (cancel && last) { try { el.releasePointerCapture(last.id); } catch (e) {} }
      press = null; dragging = false; edge = 0; last = null;
    }
    function startDrag(ev) {
      dragging = true;
      try { el.setPointerCapture(ev.pointerId); } catch (e) {}
      el.classList.add('nx-widget-dragging');
      document.body.classList.add('launcher-dragging');
      ghost = el.cloneNode(true);
      ghost.classList.add('drag-ghost', 'widget-drag-ghost');
      ghost.style.position = 'fixed';
      ghost.style.pointerEvents = 'none';
      ghost.style.zIndex = '99999';
      ghost.style.width = el.getBoundingClientRect().width + 'px';
      ghost.style.height = el.getBoundingClientRect().height + 'px';
      ghost.style.opacity = '.84';
      document.body.appendChild(ghost);
      toast('Drag to a free cell; hold at an edge to change desktop.');
    }
    function move(ev) {
      if (!press || ev.pointerId !== press.id) return;
      if (!dragging) {
        if (Math.hypot(ev.clientX - press.x, ev.clientY - press.y) > 9) { cleanup(true); return; }
        return;
      }
      ev.preventDefault();
      last = { id: ev.pointerId, x: ev.clientX, y: ev.clientY };
      if (ghost) {
        ghost.style.left = (ev.clientX - 34) + 'px';
        ghost.style.top = (ev.clientY - 34) + 'px';
      }
      var e = 0;
      if (ev.clientX < 28) e = -1;
      else if (ev.clientX > innerWidth - 28) e = 1;
      if (e !== edge) {
        edge = e;
        if (edgeTimer) { clearTimeout(edgeTimer); edgeTimer = null; }
        document.body.classList.toggle('edge-dwell-left', edge === -1);
        document.body.classList.toggle('edge-dwell-right', edge === 1);
        if (edge) {
          edgeTimer = setTimeout(function () {
            edgeTimer = null;
            if (!dragging || !global.launcher) return;
            var next = global.launcher.currentPage + edge;
            if (next >= 0 && next < global.launcher.settings.desktopCount) {
              global.launcher.currentPage = next;
              global.launcher._renderAppGrid();
              renderPage(next);
              toast('Desktop ' + (next + 1));
            }
          }, 1000);
        }
      }
    }
    function dropPoint(ev) {
      var appList = document.getElementById('app-list');
      if (!appList) return { x: 0, y: 0 };
      var rect = appList.getBoundingClientRect();
      var cols = launcherColumns(), rows = launcherRows();
      return {
        x: Math.max(0, Math.min(cols - 1, Math.floor((ev.clientX - rect.left) / (rect.width / cols)))),
        y: Math.max(0, Math.min(rows - 1, Math.floor((ev.clientY - rect.top) / (rect.height / rows))))
      };
    }
    function finish(ev) {
      if (!press || ev.pointerId !== press.id) return;
      if (!dragging) { cleanup(false); return; }
      ev.preventDefault();
      var L = layout();
      var page = global.launcher ? global.launcher.currentPage : pageIndex();
      var point = dropPoint(ev);
      var moved = L && L.move(item.id, page, point.x, point.y);
      if (!moved) toast('No free cell there; widget kept on its previous desktop.');
      save();
      cleanup(false);
      if (global.launcher && typeof global.launcher._renderAppGrid === 'function') global.launcher._renderAppGrid();
      renderPage(page);
    }
    function cancelFn(ev) { if (press && ev.pointerId !== press.id) return; cleanup(true); renderPage(pageIndex()); }
    el.addEventListener('pointerdown', function (ev) {
      if (ev.button !== undefined && ev.button !== 0) return;
      if (ev.target.closest && ev.target.closest('.nx-widget-control')) return;
      cleanup(true);
      press = { id: ev.pointerId, x: ev.clientX, y: ev.clientY };
      last = press;
      holdTimer = setTimeout(function () { holdTimer = null; if (press) startDrag({ pointerId: press.id, clientX: press.x, clientY: press.y }); }, 350);
      global.addEventListener('pointermove', move, true);
      global.addEventListener('pointerup', finish, true);
      global.addEventListener('pointercancel', cancelFn, true);
    });
  }

  function onChange() { if (global.launcher) renderPage(pageIndex()); }
  if (typeof global.addEventListener === 'function') global.addEventListener('storage', function (e) {
    if (e && (e.key === NOTES_KEY || e.key === LEGACY_KEY || e.key === (window.NuxelDesktopLayout && window.NuxelDesktopLayout.KEY))) onChange();
  });
  document.addEventListener('nuxel:notes-updated', onChange);
  document.addEventListener('nuxel:widgets-changed', onChange);
  document.addEventListener('nuxel:calendar-updated', onChange);

  global.NuxelWidgets = {
    types: types,
    registry: registry,
    state: function () {
      var L = layout();
      var items = L ? L.asWidgets() : [];
      return { schema_version: 1, enabled: L ? L.widgetsEnabled !== false : true, items: items,
               layout_key: window.NuxelDesktopLayout ? window.NuxelDesktopLayout.KEY : null };
    },
    add: add,
    update: update,
    remove: removeWidget,
    setEnabled: setEnabled,
    renderPage: renderPage,
    notes: notes,
    currentRows: function () { return currentEntities(pageIndex()); },
    KEY: window.NuxelDesktopLayout ? window.NuxelDesktopLayout.KEY : LEGACY_KEY,
    NOTES_KEY: NOTES_KEY,
    SCHEMA: 1
  };
})(window);
