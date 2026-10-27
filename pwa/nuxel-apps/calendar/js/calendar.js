/* Nuxel Calendar (PWNAGE-30000)
 * Real save/delete via the shared bridge `caldav` store with a localStorage
 * fallback.  Validation is visible, duplicate saves are blocked while a write
 * is in flight, and time/date use the platform picker (never a legacy keyboard).
 */
(function () {
  'use strict';
  var STORE_KEY = 'nuxel-calendar-events';

  var el = {};
  ['cal-title','today-btn','add-event-btn','day-grid','prev-month','next-month','month-label',
   'selected-date','events-list','event-editor','editor-back','editor-title','editor-save',
   'event-title','event-date','event-start','event-end','event-all-day','event-location',
   'event-desc','event-reminder','event-delete','editor-error'].forEach(function (id) {
    el[id] = document.getElementById(id);
  });

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
  function dateKey(d) { return d.getFullYear() + '-' + pad(d.getMonth() + 1) + '-' + pad(d.getDate()); }

  var app = {
    viewDate: new Date(),
    selectedDate: new Date(),
    events: [],
    saving: false,
    editingId: null,
    color: '#3beaa1',

    init: function () {
      this.bind();
      this.load().then(this.render.bind(this));
    },

    bind: function () {
      el.prevMonth.addEventListener('click', function () { app.viewDate = new Date(app.viewDate.getFullYear(), app.viewDate.getMonth() - 1, 1); app.render(); });
      el.nextMonth.addEventListener('click', function () { app.viewDate = new Date(app.viewDate.getFullYear(), app.viewDate.getMonth() + 1, 1); app.render(); });
      el.todayBtn.addEventListener('click', function () { var n = new Date(); app.viewDate = new Date(n.getFullYear(), n.getMonth(), 1); app.selectedDate = n; app.render(); });
      el.addEventBtn.addEventListener('click', function () { app.openEditor(null); });
      el.editorBack.addEventListener('click', function () { app.closeEditor(); });
      el.editorSave.addEventListener('click', function () { app.save(); });
      el.editorDelete.addEventListener('click', function () { app.removeCurrent(); });
      el.eventAllDay.addEventListener('change', function () { app.toggleAllDay(); });
      document.querySelectorAll('.color-opt').forEach(function (c) {
        c.addEventListener('click', function () {
          document.querySelectorAll('.color-opt').forEach(function (x) { x.classList.remove('selected'); });
          c.classList.add('selected');
          app.color = c.dataset.color;
        });
      });
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
      el.editorDelete.style.display = event ? '' : 'none';
      this.toggleAllDay();
      el.eventEditor.classList.remove('hidden');
    },

    closeEditor: function () {
      el.eventEditor.classList.add('hidden');
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
        if (el.eventStart.value && el.eventEnd.value && el.eventEnd.value <= el.eventStart.value) {
          return 'End time must be after start time.';
        }
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
        startTime: el.eventAllDay.checked ? '' : el.eventStart.value,
        endTime: el.eventAllDay.checked ? '' : el.eventEnd.value,
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
  document.addEventListener('DOMContentLoaded', function () { app.init(); });
})();
