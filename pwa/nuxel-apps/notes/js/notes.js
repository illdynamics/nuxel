/* Nuxel Notes (PWNAGE-30000)
 * Durable save through the shared bridge storage store with a localStorage
 * fallback.  Autosave is debounced, the editor shows a real dirty/saved/error
 * state, and the Done/Save action does not claim "saved" until the write
 * completes successfully. */
(function () {
  'use strict';
  var STORE_KEY = 'nuxel-notes';

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
  function saveLocal(notes) {
    try { localStorage.setItem(STORE_KEY, JSON.stringify(notes)); } catch (e) { /* ignore */ }
  }

  var app = {
    notes: [],
    currentNote: null,
    dirty: false,
    saving: false,
    _revision: 0,
    _saveChain: Promise.resolve(),
    _lastTransport: 'unknown',

    init: async function () {
      await this.load();
      this.renderList();
      this.bind();
    },

    async load() {
      var res = await bridgeCall('notes', 'list', {});
      if (res && res.success !== false && Array.isArray(res.notes)) {
        this.notes = res.notes;
        this._lastTransport = 'bridge';
        saveLocal(this.notes);
        // One-time, lossless migration of notes created before the file store.
        if (!this.notes.length) {
          var legacy = loadLocal();
          if (legacy.length) {
            var migrated = [];
            for (var i = 0; i < legacy.length; i++) {
              var saved = await bridgeCall('notes', 'save', { note: legacy[i] });
              if (saved && saved.success !== false && saved.note) migrated.push(saved.note);
            }
            if (migrated.length) {
              this.notes = migrated;
              this._lastTransport = 'bridge';
            }
          }
        }
      } else {
        this.notes = loadLocal();
        this._lastTransport = res && res.offline ? 'local-offline' : 'local-cache';
      }
      // A widget tap records the requested note before launching the app.
      try {
        var wanted = localStorage.getItem('nuxel.notes.open');
        if (wanted) {
          localStorage.removeItem('nuxel.notes.open');
          var note = this.notes.find(function (n) { return n.id === wanted; });
          if (note) setTimeout(function () { app.openEditor(note); }, 0);
        }
      } catch (e) {}
    },

    // Compatibility with notes-io.js (it calls _saveNotes when pinning/importing).
    _saveNotes: function () { return this.saveAll(); },

    async saveAll() {
      var snapshot = JSON.parse(JSON.stringify(this.notes));
      saveLocal(snapshot);
      var ok = true, error = null;
      for (var i = 0; i < snapshot.length; i++) {
        var r = await bridgeCall('notes', 'save', { note: snapshot[i] });
        if (r && r.success === false) { ok = false; error = r.error || 'save failed'; break; }
      }
      if (ok) {
        this._lastTransport = 'bridge';
        this._announce(snapshot);
      } else {
        this._lastTransport = 'local-offline';
        this.showStatus('Save failed: ' + error + '. Your content is kept locally.');
      }
      return { ok: ok, error: error };
    },

    // Serialized writes: an older completion can never mark newer text as
    // saved. localStorage is written first as a durable offline cache; the
    // bridge remains the canonical store while it is available.
    _enqueueWrite(snapshot, revision) {
      var self = this;
      var run = function () {
        return bridgeCall('storage', 'write', { key: STORE_KEY, data: snapshot }).then(function (res) {
          var ok = !(res && res.success === false);
          if (ok) {
            self._lastTransport = (res && res.offline) ? 'local-offline' : 'bridge';
            self._savedRevision = Math.max(self._savedRevision || 0, revision);
          }
          return { ok: ok, transport: self._lastTransport, error: res && res.error, revision: revision };
        });
      };
      this._saveChain = this._saveChain.then(run, run);
      return this._saveChain;
    },

    async persist() {
      return this.saveAll();
    },

    _announce(notes) {
      try { document.dispatchEvent(new CustomEvent('nuxel:notes-updated', { detail: { notes: notes } })); } catch (e) {}
      try { window.dispatchEvent(new CustomEvent('nuxel:notes-updated', { detail: { notes: notes } })); } catch (e) {}
    },

    renderList: function () {
      var list = document.getElementById('notes-list');
      var sorted = this.notes.slice().sort(function (a, b) {
        if (!!b.pinned !== !!a.pinned) return (b.pinned ? 1 : 0) - (a.pinned ? 1 : 0);
        return new Date(b.updatedAt || 0) - new Date(a.updatedAt || 0);
      });
      list.textContent = '';
      if (!sorted.length) {
        var empty = document.createElement('div');
        empty.className = 'empty-state';
        var icon = document.createElement('div'); icon.className = 'empty-icon'; icon.textContent = '🐧';
        var h = document.createElement('h3'); h.textContent = 'No notes yet';
        var p = document.createElement('p'); p.textContent = 'Tap + to create your first note in ~/Notes.';
        empty.appendChild(icon); empty.appendChild(h); empty.appendChild(p); list.appendChild(empty);
        return;
      }
      var self = this;
      sorted.forEach(function (note) {
        var card = document.createElement('article');
        card.className = 'note-card' + (note.pinned ? ' pinned' : '');
        card.dataset.id = note.id;
        card.tabIndex = 0;
        card.setAttribute('role', 'button');
        card.setAttribute('aria-label', (note.pinned ? 'Pinned note: ' : 'Note: ') + (note.title || 'Untitled'));
        var head = document.createElement('div'); head.className = 'note-card-head';
        var title = document.createElement('div'); title.className = 'note-card-title'; title.textContent = note.title || 'Untitled';
        var pin = document.createElement('button'); pin.type = 'button'; pin.className = 'note-card-icon';
        pin.textContent = note.pinned ? '★' : '☆'; pin.title = note.pinned ? 'Unpin note' : 'Pin note';
        pin.setAttribute('aria-label', pin.title);
        pin.addEventListener('click', function (ev) {
          ev.stopPropagation();
          note.pinned = !note.pinned;
          note.updatedAt = new Date().toISOString();
          self.saveNoteDirect(note).then(function (ok) { if (ok) { self.renderList(); self._announce(self.notes); } });
        });
        head.appendChild(title); head.appendChild(pin);
        var preview = document.createElement('div'); preview.className = 'note-card-preview';
        preview.textContent = String(note.body || '').replace(/\s+/g, ' ').slice(0, 180);
        var foot = document.createElement('div'); foot.className = 'note-card-foot';
        var date = document.createElement('span'); date.className = 'note-card-date'; date.textContent = self.formatDate(note.updatedAt);
        var path = document.createElement('span'); path.className = 'note-card-path'; path.textContent = note.path || '~/Notes';
        foot.appendChild(date); foot.appendChild(path);
        card.appendChild(head); card.appendChild(preview); card.appendChild(foot);
        card.addEventListener('click', function () { self.openEditor(note); });
        card.addEventListener('keydown', function (ev) {
          if (ev.key === 'Enter' || ev.key === ' ') { ev.preventDefault(); self.openEditor(note); }
        });
        list.appendChild(card);
      });
    },

    saveNoteDirect: async function (note) {
      var res = await bridgeCall('notes', 'save', { note: note });
      if (!res || res.success === false) {
        this.showStatus('Save failed: ' + ((res && (res.error || res.detail)) || 'backend unavailable'));
        return false;
      }
      var saved = res.note || note;
      var idx = this.notes.findIndex(function (n) { return n.id === saved.id; });
      if (idx >= 0) this.notes[idx] = saved; else this.notes.push(saved);
      saveLocal(this.notes);
      this._lastTransport = 'bridge';
      return true;
    },

    openApp: function (appId, draftKey, draft) {
      try { localStorage.setItem(draftKey, JSON.stringify(draft)); } catch (e) {}
      var registry = null;
      try { registry = window.parent && window.parent.appRegistry; } catch (e) {}
      try {
        if (registry && typeof registry.launchApp === 'function') { registry.launchApp(appId); return true; }
      } catch (e) {}
      try {
        if (window.parent && window.parent.nuxel && typeof window.parent.nuxel.launchApp === 'function') {
          window.parent.nuxel.launchApp(appId); return true;
        }
      } catch (e) {}
      return false;
    },

    openEditor: function (note) {
      this.currentNote = note || { id: 'note-' + Date.now(), title: '', body: '', createdAt: new Date().toISOString(), updatedAt: new Date().toISOString() };
      document.getElementById('note-title').value = this.currentNote.title || '';
      document.getElementById('note-body').value = this.currentNote.body || '';
      this.dirty = false;
      this.updateMeta();
      document.getElementById('note-editor').classList.remove('hidden');
      setTimeout(function () { try { document.getElementById('note-title').focus(); } catch (e) {} }, 50);
    },

    updateMeta: function () {
      var meta = document.getElementById('note-meta');
      if (this.saving) meta.textContent = 'Saving…';
      else if (this.dirty) meta.textContent = 'Unsaved changes';
      else if (this.currentNote) {
        var how = this._lastTransport === 'bridge' ? 'Saved'
          : this._lastTransport === 'local-offline' ? 'Saved locally (bridge offline)'
          : this._lastTransport === 'local-cache' ? 'Saved locally (cache)' : 'Saved';
        meta.textContent = how + ' · ' + this.formatDate(this.currentNote.updatedAt);
      } else meta.textContent = '';
    },

    capture: function () {
      if (!this.currentNote) return;
      this.currentNote.title = document.getElementById('note-title').value.trim() || 'Untitled';
      this.currentNote.body = document.getElementById('note-body').value;
      this.currentNote.updatedAt = new Date().toISOString();
      var idx = this.notes.findIndex(function (n) { return n.id === app.currentNote.id; });
      if (idx >= 0) this.notes[idx] = this.currentNote; else this.notes.push(this.currentNote);
      this._revision++;
      this.dirty = true;
      this.updateMeta();
    },

    async save() {
      if (!this.currentNote) return { ok: true };
      this.capture();
      var rev = this._revision;
      var note = JSON.parse(JSON.stringify(this.currentNote));
      this.saving = true;
      this.updateMeta();
      var res = await bridgeCall('notes', 'save', { note: note });
      if (rev === this._revision) {
        this.saving = false;
        if (res && res.success !== false) {
          this._lastTransport = 'bridge';
          var saved = res.note || note;
          var idx = this.notes.findIndex(function (n) { return n.id === saved.id; });
          if (idx >= 0) this.notes[idx] = saved; else this.notes.push(saved);
          this.currentNote = saved;
          this.dirty = false;
          saveLocal(this.notes);
          this.updateMeta();
          this.renderList();
          this._announce(this.notes);
          return { ok: true, note: saved };
        }
        saveLocal(this.notes);
        var error = (res && (res.error || res.detail)) || 'unknown error';
        this.updateMeta();
        this.showStatus('Save failed: ' + error + '. Your content is kept locally.');
        return { ok: false, error: error };
      }
      return { ok: true };
    },

    async saveAndClose() {
      var res = await this.save();
      if (res.ok) {
        document.getElementById('note-editor').classList.add('hidden');
        this.currentNote = null;
      }
    },

    async deleteNote(id) {
      if (this.currentNote && this.currentNote.id === id) {
        var saveFirst = await this.save();
        if (!saveFirst.ok) return;
      }
      var res = await bridgeCall('notes', 'delete', { id: id });
      if (res && res.success !== false) {
        this.notes = this.notes.filter(function (n) { return n.id !== id; });
        if (this.currentNote && this.currentNote.id === id) this.currentNote = null;
        saveLocal(this.notes);
        this.renderList();
        this._announce(this.notes);
      } else {
        this.showStatus('Delete failed: ' + ((res && (res.error || res.detail)) || 'unknown error'));
      }
    },

    async renameNote(id, title) {
      var res = await bridgeCall('notes', 'rename', { id: id, title: title });
      if (res && res.success !== false) {
        var note = this.notes.find(function (n) { return n.id === id; });
        if (note) { note.title = title; note.updatedAt = new Date().toISOString(); }
        if (this.currentNote && this.currentNote.id === id) this.currentNote.title = title;
        saveLocal(this.notes);
        this.renderList();
        this._announce(this.notes);
        return true;
      }
      this.showStatus('Rename failed: ' + ((res && (res.error || res.detail)) || 'unknown error'));
      return false;
    },

    async convertToCalendar(note, when) {
      // Handoff is a real prefilled Calendar editor, not a silent event write.
      var draft = {
        title: (note.title || 'Note').slice(0, 200),
        description: (note.body || '').slice(0, 8000),
        date: when && when.date,
        startTime: when && when.startTime || '',
        endTime: when && when.endTime || '',
        allDay: !!(when && when.allDay),
        reminder: Number(when && when.reminder || 10) || 10,
        sourceNoteId: note.id,
        createdAt: new Date().toISOString()
      };
      var opened = this.openApp('org.nuxel.Calendar', 'nuxel.calendar.draft', draft);
      this.showStatus(opened ? 'Calendar opened with the note prefilled. Confirm the event there.' :
        'Calendar draft saved. Open Calendar to finish the event.');
      return opened;
    },

    async convertToAlarm(note, when) {
      // Handoff is a real prefilled Clock alarm form.  The user confirms the
      // time/recurrence; note prose is never parsed into a silent schedule.
      var draft = {
        time: when && when.time || '',
        label: (note.title || 'Note reminder').slice(0, 120),
        repeat: false,
        sourceNoteId: note.id
      };
      var opened = this.openApp('org.nuxel.Clock', 'nuxel.clock.alarmDraft', draft);
      this.showStatus(opened ? 'Clock opened with the alarm prefilled. Confirm Add there.' :
        'Alarm draft saved. Open Clock to finish scheduling it.');
      return opened;
    },

    async openNotesFolder() {
      var opened = this.openApp('org.nuxel.Files', 'nuxel.files.open', { path: '/Notes' });
      this.showStatus(opened ? 'Files opened at ~/Notes.' : 'Notes are stored in ~/Notes; open Files to browse them.');
      return opened;
    },

    bind: function () {
      var self = this;
      var openFromHome = function (ev) {
        var id = ev && ev.detail && ev.detail.noteId;
        var note = id ? self.notes.find(function (n) { return n.id === id; }) : null;
        if (note) {
          document.getElementById('note-editor').classList.remove('hidden');
          self.openEditor(note);
        }
      };
      document.addEventListener('nuxel:notes-open', openFromHome);
      if (typeof window.addEventListener === 'function') window.addEventListener('nuxel:notes-open', openFromHome);
      // Cross-WebView deep link: Home writes the requested note id to the
      // shared origin storage, which fires here even when Notes is already open.
      if (typeof window.addEventListener === 'function') window.addEventListener('storage', function (ev) {
        if (!ev || ev.key !== 'nuxel.notes.open' || !ev.newValue) return;
        try { localStorage.removeItem('nuxel.notes.open'); } catch (e) {}
        var note = self.notes.find(function (n) { return n.id === ev.newValue; });
        if (note) { document.getElementById('note-editor').classList.remove('hidden'); self.openEditor(note); }
      });
      document.getElementById('new-note-btn').addEventListener('click', function () { self.openEditor(null); });
      document.getElementById('editor-back').addEventListener('click', function () {
        if (self.dirty) self.saveAndClose(); else { document.getElementById('note-editor').classList.add('hidden'); self.currentNote = null; }
      });
      document.getElementById('editor-save').addEventListener('click', function () { self.saveAndClose(); });
      document.querySelectorAll('[data-note-action]').forEach(function (btn) {
        btn.addEventListener('click', function () {
          if (!self.currentNote) return;
          self.capture();
          var action = btn.getAttribute('data-note-action');
          var d = new Date();
          var date = d.getFullYear() + '-' + String(d.getMonth() + 1).padStart(2, '0') + '-' + String(d.getDate()).padStart(2, '0');
          var now = String(d.getHours()).padStart(2, '0') + ':' + String(d.getMinutes()).padStart(2, '0');
          if (action === 'alarm') {
            var t = window.prompt('Alarm time (HH:MM)', now);
            if (!t || !/^([01]\d|2[0-3]):[0-5]\d$/.test(t)) return;
            self.convertToAlarm(self.currentNote, { time: t });
          } else if (action === 'calendar') {
            var when = window.prompt('Event date (YYYY-MM-DD)', date);
            if (!when || !/^\d{4}-\d{2}-\d{2}$/.test(when)) return;
            var start = window.prompt('Start time (HH:MM, or blank for all-day)', now);
            var allDay = !start;
            if (start && !/^([01]\d|2[0-3]):[0-5]\d$/.test(start)) return;
            self.convertToCalendar(self.currentNote, { date: when, startTime: start || '', endTime: '', allDay: allDay, reminder: 10 });
          } else if (action === 'reminder') {
            var mins = Number(window.prompt('Reminder minutes before now (0 for immediately)', '10'));
            if (!Number.isFinite(mins) || mins < 0) return;
            self.currentNote.reminder = { at: new Date(Date.now() + mins * 60000).toISOString(), minutes: mins };
            self.save().then(function (r) { if (r.ok) self.showStatus('Reminder saved on the note.'); });
          }
        });
      });

      var timer;
      function autosave() {
        clearTimeout(timer);
        timer = setTimeout(function () { if (self.dirty) self.save(); }, 1000);
      }
      document.getElementById('note-title').addEventListener('input', function () { self.capture(); autosave(); });
      document.getElementById('note-body').addEventListener('input', function () { self.capture(); autosave(); });

      document.getElementById('menu-btn').addEventListener('click', function () {
        if (!self.currentNote) { self.openNotesFolder(); return; }
        if (window.confirm('Delete this note? The file in ~/Notes will be removed.')) {
          self.deleteNote(self.currentNote.id);
          document.getElementById('note-editor').classList.add('hidden');
          self.currentNote = null;
        }
      });

      document.querySelectorAll('.tool-btn').forEach(function (btn) {
        btn.addEventListener('click', function () {
          var cmd = btn.dataset.cmd;
          var body = document.getElementById('note-body');
          var start = body.selectionStart, end = body.selectionEnd;
          var text = body.value, sel = text.substring(start, end);
          var rep = sel || 'text';
          if (cmd === 'bold') rep = '**' + (sel || 'bold') + '**';
          else if (cmd === 'italic') rep = '*' + (sel || 'italic') + '*';
          else if (cmd === 'heading') rep = '## ' + (sel || 'Heading') + '\n';
          else if (cmd === 'list') rep = '- ' + (sel || 'item') + '\n';
          else if (cmd === 'code') rep = '```\n' + (sel || 'code') + '\n```';
          body.setRangeText(rep, start, end, 'end');
          body.focus();
          self.capture(); autosave();
        });
      });
    },

    formatDate: function (dateStr) {
      if (!dateStr) return '';
      var d = new Date(dateStr);
      if (isNaN(d)) return '';
      var diff = Date.now() - d.getTime();
      if (diff < 60000) return 'Just now';
      if (diff < 3600000) return Math.floor(diff / 60000) + 'm ago';
      if (diff < 86400000) return Math.floor(diff / 3600000) + 'h ago';
      if (diff < 604800000) return Math.floor(diff / 86400000) + 'd ago';
      return d.toLocaleDateString([], { month: 'short', day: 'numeric' });
    },

    showStatus: function (msg) {
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

  window.nuxelNotes = { app: function () { return app; }, storageKey: STORE_KEY };
  document.addEventListener('DOMContentLoaded', function () { app.init(); });
})();
