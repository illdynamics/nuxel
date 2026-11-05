/* Nuxel Calendar (PWNAGE-30000)
 * Real save/delete via the shared bridge `caldav` store with a localStorage
 * fallback.  Validation is visible, duplicate saves are blocked while a write
 * is in flight, and time/date use the platform picker (never a legacy keyboard).
 */
(function () {
  'use strict';
  function calDiag(msg) { try { window.webkit.messageHandlers.nuxelDiag.postMessage(msg); } catch (e) {} }
  window.addEventListener('error', function (e) { calDiag('CAL_JS_ERROR ' + (e.message || e) + ' @' + (e.filename || '?') + ':' + (e.lineno || 0) + ':' + (e.colno || 0)); });
  var STORE_KEY = 'nuxel-calendar-events';

  var el = {};
  /* The controller uses camelCase properties while the HTML ids are
     kebab-case.  Keeping this map explicit is the single place the two naming
     worlds meet; the old code only populated kebab-case keys, so the first
     `el.prevMonth.addEventListener` threw and Calendar never bound at all. */
  var ELEMENT_IDS = {
    calTitle: 'cal-title', todayBtn: 'today-btn', addEventBtn: 'add-event-btn',
    dayGrid: 'day-grid', prevMonth: 'prev-month', nextMonth: 'next-month',
    monthLabel: 'month-label', selectedDate: 'selected-date', eventsList: 'events-list',
    eventEditor: 'event-editor', editorBack: 'editor-back', editorTitle: 'editor-title',
    editorSave: 'editor-save', editorDelete: 'event-delete', eventTitle: 'event-title', eventDate: 'event-date',
    eventStart: 'event-start', eventEnd: 'event-end', eventAllDay: 'event-all-day',
    eventLocation: 'event-location', eventDesc: 'event-desc', eventReminder: 'event-reminder',
    eventDelete: 'event-delete', editorError: 'editor-error', timeKeypad: 'time-keypad',
    timeKeypadLabel: 'time-keypad-label'
  };
  Object.keys(ELEMENT_IDS).forEach(function (name) {
    el[name] = document.getElementById(ELEMENT_IDS[name]);
  });
  el.ids = ELEMENT_IDS;
  var timeTarget = null;

  function bridgeCall(ns, verb, params) {
    if (window.NuxelBridge && typeof window.NuxelBridge.call === 'function') {
      return window.NuxelBridge.call(ns, verb, params).catch(function (e) { return { success: false, error: e && e.message }; });
    }
    return Promise.resolve({ success: false, offline: true });
  }
  function loadLocal() {
    try { var raw = localStorage.getItem(STORE_KEY); return raw ? JSON.parse(raw) : []; }
    catch (e) { return []; }
  }
  function saveLocal(events) {
    try { localStorage.setItem(STORE_KEY, JSON.stringify(events)); } catch (e) { /* ignore */ }
  }

  function pad(n) { return String(n).padStart(2, '0'); }
  // Text time fields use the numeric OSK.  Accept "9", "930", "0930" and
  // "09:30" and normalise to the stored HH:MM form.
  function normaliseTime(value) {
    var v = String(value == null ? '' : value).trim();
    if (!v) return '';
    var digits = v.replace(/[^0-9]/g, '');
    if (digits.length === 3) digits = '0' + digits;
    if (digits.length !== 4) return null;
    var h = Number(digits.slice(0, 2)), m = Number(digits.slice(2));
    if (h > 23 || m > 59) return null;
    return String(h).padStart(2, '0') + ':' + String(m).padStart(2, '0');
  }
  function dateKey(d) { return d.getFullYear() + '-' + pad(d.getMonth() + 1) + '-' + pad(d.getDate()); }

  var app = {
    viewDate: new Date(),
    selectedDate: new Date(),
    events: [],
    saving: false,
    editingId: null,
    color: '#3beaa1',
    bound: false,

    init: function () {
      if (this.bound) return;
      this.bind();
      this.load().then(this.render.bind(this));
    },

    bind: function () {
      if (this.bound) return;
      var missing = Object.keys(ELEMENT_IDS).filter(function (name) { return !el[name]; });
      if (missing.length) throw new Error('Calendar missing elements: ' + missing.join(','));
      el.prevMonth.addEventListener('click', function () { app.viewDate = new Date(app.viewDate.getFullYear(), app.viewDate.getMonth() - 1, 1); app.render(); });
      el.nextMonth.addEventListener('click', function () { app.viewDate = new Date(app.viewDate.getFullYear(), app.viewDate.getMonth() + 1, 1); app.render(); });
      el.todayBtn.addEventListener('click', function () { var n = new Date(); app.viewDate = new Date(n.getFullYear(), n.getMonth(), 1); app.selectedDate = n; app.render(); });
      el.addEventBtn.addEventListener('click', function () { app.openEditor(null); });
      el.editorBack.addEventListener('click', function () { app.closeEditor(); });
      el.editorSave.addEventListener('click', function () { app.save(); });
      el.editorDelete.addEventListener('click', function () { app.removeCurrent(); });
      el.eventAllDay.addEventListener('change', function () { app.toggleAllDay(); });
      [el.eventStart, el.eventEnd].forEach(function (input) {
        input.addEventListener('focus', function () { app.openTimeKeypad(input); });
        input.addEventListener('click', function () { app.openTimeKeypad(input); });
        input.addEventListener('blur', function () {
          var n = normaliseTime(input.value);
          if (n != null) input.value = n;
        });
      });
      if (el.timeKeypad) {
        el.timeKeypad.querySelectorAll('[data-time-key]').forEach(function (btn) {
          btn.addEventListener('click', function (ev) {
            ev.preventDefault(); ev.stopPropagation();
            app.timeKey(btn.getAttribute('data-time-key'));
          });
        });
      }
      document.addEventListener('keydown', function (ev) {
        if (ev.key === 'Escape' && !el.eventEditor.classList.contains('hidden')) {
          ev.preventDefault(); app.closeEditor();
        }
      });
      // Calendar is a normal, non-immersive app: the Nuxel triple buttons stay
      // visible by default and the native dock reserves its exclusive zone above
      // the keyboard, so Back/Home/Tabs remain reachable with the OSK open.
      try {
        window.parent.postMessage({ type: 'nuxel:immersive', active: false }, window.location.origin);
        window.parent.postMessage({ type: 'nuxel:nav-visible', active: true }, window.location.origin);
        if (window.parent && window.parent.nuxel && window.parent.nuxel.setNavVisible) window.parent.nuxel.setNavVisible(true);
      } catch (e) {}
      document.querySelectorAll('.color-opt').forEach(function (c) {
        c.addEventListener('click', function () {
          document.querySelectorAll('.color-opt').forEach(function (x) { x.classList.remove('selected'); });
          c.classList.add('selected');
          app.color = c.dataset.color;
        });
      });
      this.bound = true;
    },

    async load() {
      var res = await bridgeCall('caldav', 'list', { app_id: 'org.nuxel.Calendar' });
      if (res && res.success !== false && Array.isArray(res.events)) {
        this.events = res.events;
        saveLocal(this.events);
      } else {
        this.events = loadLocal();
      }
    },

    async persist() {
      var events = this.events.slice();
      saveLocal(events);
      var res = await bridgeCall('caldav', 'put', { app_id: 'org.nuxel.Calendar', events: events });
      if (res && res.success === false) {
        // Keep the local copy; the user still sees a real error and their data
        // is not lost from the local fallback.
        return { ok: false, error: res.error || 'calendar write failed' };
      }
      return { ok: true };
    },

    render: function () {
      this.renderMonth();
      this.renderEvents();
      this.renderTitle();
    },

    renderTitle: function () {
      var label = this.viewDate.toLocaleDateString([], { month: 'long', year: 'numeric' });
      el.calTitle.textContent = label;
      el.monthLabel.textContent = label;
    },

    renderMonth: function () {
      var year = this.viewDate.getFullYear(), month = this.viewDate.getMonth();
      var first = new Date(year, month, 1).getDay();
      var days = new Date(year, month + 1, 0).getDate();
      var prevDays = new Date(year, month, 0).getDate();
      var offset = first === 0 ? 6 : first - 1;
      var now = new Date();
      var todayKey = dateKey(now);
      var selKey = dateKey(this.selectedDate);
      var cells = [];
      for (var i = offset - 1; i >= 0; i--) {
        cells.push(this.dayCell(prevDays - i, true, new Date(year, month - 1, prevDays - i), todayKey, selKey));
      }
      for (var d = 1; d <= days; d++) {
        cells.push(this.dayCell(d, false, new Date(year, month, d), todayKey, selKey));
      }
      var remaining = 42 - cells.length;
      for (var n = 1; n <= remaining; n++) {
        cells.push(this.dayCell(n, true, new Date(year, month + 1, n), todayKey, selKey));
      }
      el.dayGrid.innerHTML = cells.join('');
      var self = this;
      el.dayGrid.querySelectorAll('.day-cell').forEach(function (cell) {
        cell.addEventListener('click', function () {
          self.selectedDate = new Date(+cell.dataset.year, +cell.dataset.month, +cell.dataset.day);
          self.renderMonth();
          self.renderEvents();
        });
      });
    },

    dayCell: function (day, other, date, todayKey, selKey) {
      var key = dateKey(date);
      var cls = 'day-cell';
      if (other) cls += ' other-month';
      if (key === todayKey) cls += ' today';
      if (key === selKey) cls += ' selected';
      if (this.events.some(function (e) { return e.date === key; })) cls += ' has-events';
      return '<div class="' + cls + '" data-day="' + day + '" data-month="' + date.getMonth() + '" data-year="' + date.getFullYear() + '">' + day + '</div>';
    },

    renderEvents: function () {
      var key = dateKey(this.selectedDate);
      el.selectedDate.textContent = this.selectedDate.toLocaleDateString([], { weekday: 'long', month: 'long', day: 'numeric' });
      var dayEvents = this.events.filter(function (e) { return e.date === key; });
      if (!dayEvents.length) { el.eventsList.innerHTML = '<div class="empty-state">No events</div>'; return; }
      dayEvents.sort(function (a, b) { return (a.startTime || '00:00').localeCompare(b.startTime || '00:00'); });
      var self = this;
      el.eventsList.innerHTML = dayEvents.map(function (e, i) {
        var time = e.allDay ? 'All day' : ((e.startTime || '') + (e.endTime ? ' – ' + e.endTime : ''));
        return '<div class="event-item" data-i="' + i + '" style="border-left-color:' + self.esc(e.color || '#3beaa1') + '">' +
          '<div class="event-time">' + self.esc(time) + '</div>' +
          '<div class="event-title">' + self.esc(e.title) + '</div></div>';
      }).join('');
      el.eventsList.querySelectorAll('.event-item').forEach(function (item) {
        item.addEventListener('click', function () {
          var e = dayEvents[+item.dataset.i];
          if (e) app.openEditor(e);
        });
      });
    },

    openEditor: function (event) {
      this.editingId = event ? event.id : null;
      el.editorTitle.textContent = event ? 'Edit Event' : 'New Event';
      el.eventTitle.value = event ? (event.title || '') : '';
      el.eventDate.value = event ? (event.date || dateKey(this.selectedDate)) : dateKey(this.selectedDate);
      el.eventStart.value = event && event.startTime ? event.startTime : '';
      el.eventEnd.value = event && event.endTime ? event.endTime : '';
      el.eventAllDay.checked = !!(event && event.allDay);
      el.eventLocation.value = event && event.location ? event.location : '';
      el.eventDesc.value = event && event.description ? event.description : '';
      el.eventReminder.value = event && event.reminder ? String(event.reminder) : '';
      this.color = event && event.color ? event.color : '#3beaa1';
      document.querySelectorAll('.color-opt').forEach(function (c) { c.classList.toggle('selected', c.dataset.color === app.color); });
      el.editorError.textContent = '';
      this.closeTimeKeypad();
      el.editorDelete.style.display = event ? '' : 'none';
      this.toggleAllDay();
      el.eventEditor.classList.remove('hidden');
    },

    openTimeKeypad: function (input) {
      if (!el.timeKeypad || !input || input.disabled) return;
      timeTarget = input;
      if (el.timeKeypadLabel) el.timeKeypadLabel.textContent = (input === el.eventStart ? 'Start time' : 'End time') + ' · HH:MM';
      el.timeKeypad.hidden = false;
      try { el.timeKeypad.scrollIntoView({ block: 'nearest' }); } catch (e) {}
    },

    closeTimeKeypad: function () {
      if (el.timeKeypad) el.timeKeypad.hidden = true;
      timeTarget = null;
    },

    timeKey: function (key) {
      if (!timeTarget) return;
      var v = String(timeTarget.value || '').replace(/[^0-9:]/g, '');
      if (key === 'clear') v = '';
      else if (key === 'back') v = v.slice(0, -1);
      else if (key === 'done') {
        var n = normaliseTime(v);
        if (n != null) timeTarget.value = n;
        try { timeTarget.blur(); } catch (e) {}
        this.closeTimeKeypad();
        return;
      } else if (key === 'now') {
        var now = new Date();
        v = pad(now.getHours()) + ':' + pad(now.getMinutes());
      } else if (key === ':') {
        var d = v.replace(/:/g, '');
        if (d.length === 0) v = '00:';
        else if (d.length === 1) v = '0' + d + ':';
        else v = d.slice(0, 2) + ':' + d.slice(2);
      } else if (/^[0-9]$/.test(key)) {
        var digits = v.replace(/:/g, '');
        if (digits.length < 4) {
          digits += key;
          v = digits.length > 2 ? digits.slice(0, 2) + ':' + digits.slice(2) : digits;
        }
      }
      v = v.slice(0, 5);
      timeTarget.value = v;
      timeTarget.dispatchEvent(new Event('input', { bubbles: true }));
    },

    closeEditor: function () {
      el.eventEditor.classList.add('hidden');
      this.closeTimeKeypad();
      this.saving = false;
      el.editorSave.disabled = false;
    },

    toggleAllDay: function () {
      var allDay = el.eventAllDay.checked;
      el.eventStart.disabled = allDay;
      el.eventEnd.disabled = allDay;
    },

    validate: function () {
      var title = el.eventTitle.value.trim();
      if (!title) return 'A title is required.';
      if (!el.eventDate.value) return 'Pick a date.';
      if (!el.eventAllDay.checked) {
        var st = normaliseTime(el.eventStart.value);
        var en = normaliseTime(el.eventEnd.value);
        if (el.eventStart.value && st == null) return 'Start time must be HH:MM (24-hour).';
        if (el.eventEnd.value && en == null) return 'End time must be HH:MM (24-hour).';
        if (st && en && en <= st) return 'End time must be after start time.';
      }
      return null;
    },

    async save() {
      if (this.saving) return;
      var err = this.validate();
      if (err) { el.editorError.textContent = err; return; }
      var title = el.eventTitle.value.trim();
      var event = {
        id: this.editingId || ('evt-' + Date.now()),
        title: title,
        date: el.eventDate.value,
        startTime: el.eventAllDay.checked ? '' : (normaliseTime(el.eventStart.value) || ''),
        endTime: el.eventAllDay.checked ? '' : (normaliseTime(el.eventEnd.value) || ''),
        allDay: el.eventAllDay.checked,
        location: el.eventLocation.value.trim(),
        description: el.eventDesc.value,
        reminder: el.eventReminder.value ? Number(el.eventReminder.value) : null,
        color: this.color,
        updatedAt: new Date().toISOString()
      };
      this.saving = true;
      el.editorSave.disabled = true;
      el.editorError.textContent = 'Saving…';
      var idx = this.events.findIndex(function (e) { return e.id === event.id; });
      if (idx >= 0) this.events[idx] = event; else this.events.push(event);
      var res = await this.persist();
      if (!res.ok) {
        el.editorError.textContent = 'Save failed: ' + (res.error || 'unknown error') + '. Your entry is kept.';
        this.saving = false;
        el.editorSave.disabled = false;
        return;
      }
      this.closeEditor();
      this.render();
    },

    async removeCurrent() {
      if (!this.editingId) return;
      if (!window.confirm('Delete this event?')) return;
      this.events = this.events.filter(function (e) { return e.id !== app.editingId; });
      var res = await this.persist();
      this.closeEditor();
      if (res.ok) this.render();
      else this.showError('Delete failed: ' + (res.error || 'unknown error'));
    },

    showError: function (msg) {
      var t = document.createElement('div');
      t.className = 'toast'; t.textContent = msg;
      document.body.appendChild(t);
      setTimeout(function () { t.remove(); }, 3000);
    },

    esc: function (s) {
      var d = document.createElement('div');
      d.textContent = String(s == null ? '' : s);
      return d.innerHTML;
    }
  };

  window.nuxelCalendar = { app: function () { return app; }, storageKey: STORE_KEY, dateKey: dateKey };
  window.__nuxelCalendarVersion = 'p80000e';

  /* Explicit Back contract for the central Home dispatcher.  The editor and
     the custom time keypad are separate app-level screens; when neither is
     open, Back has reached the app root and Home may close it gracefully. */
  function canAppGoBack() {
    return !!((el.timeKeypad && !el.timeKeypad.hidden) ||
              (el.eventEditor && !el.eventEditor.classList.contains('hidden')));
  }
  function appGoBack() {
    if (el.timeKeypad && !el.timeKeypad.hidden) { app.closeTimeKeypad(); return true; }
    if (el.eventEditor && !el.eventEditor.classList.contains('hidden')) { app.closeEditor(); return true; }
    return false;
  }
  window.NuxelBack = { canGoBack: canAppGoBack, back: appGoBack };
  window.addEventListener('message', function (event) {
    if (event.origin !== window.location.origin) return;
    if (!event.data || event.data.type !== 'nuxel:close-request') return;
    app.closeTimeKeypad();
    app.closeEditor();
    try { if (document.activeElement && document.activeElement.blur) document.activeElement.blur(); } catch (e) {}
  });
  window.addEventListener('pagehide', function () {
    app.closeTimeKeypad();
    try { if (document.activeElement && document.activeElement.blur) document.activeElement.blur(); } catch (e) {}
  });
  function boot() { try { app.init(); } catch (e) { calDiag('CAL_INIT_ERROR ' + ((e && (e.stack || e.message)) || e)); } }
  // This script is at the end of <body>; initialise immediately, then keep the
  // DOMContentLoaded call as an idempotent fallback.  The old listener-only
  // path could miss the event in a long-lived WebKit frame, leaving every
  // Calendar control unbound while the page still looked normal.
  boot();
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', boot, { once: true });
})();
