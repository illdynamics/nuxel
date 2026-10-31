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
      var res = await bridgeCall('storage', 'read', { key: STORE_KEY });
      if (res && res.success !== false && Array.isArray(res.data)) {
        this.notes = res.data;
        this._lastTransport = 'bridge';
        saveLocal(this.notes);
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
    _saveNotes: function () { return this.persist(); },

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
      var notes = JSON.parse(JSON.stringify(this.notes));
      saveLocal(notes);
      this._revision++;
      var res = await this._enqueueWrite(notes, this._revision);
      if (res.ok) this._announce(notes);
      return res;
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
      if (!sorted.length) {
        list.innerHTML = '<div class="empty-state"><div class="empty-icon">📝</div><h3>No notes yet</h3><p>Tap + to create your first note</p></div>';
        return;
      }
      var self = this;
      list.innerHTML = sorted.map(function (note) {
        return '<div class="note-card" data-id="' + self.esc(note.id) + '">' +
          '<div class="note-card-title">' + self.esc(note.title || 'Untitled') + '</div>' +
          '<div class="note-card-preview">' + self.esc((note.body || '').substring(0, 100)) + '</div>' +
          '<div class="note-card-date">' + self.esc(self.formatDate(note.updatedAt)) + '</div></div>';
      }).join('');
      list.querySelectorAll('.note-card').forEach(function (card) {
        card.addEventListener('click', function () {
          var note = self.notes.find(function (n) { return n.id === card.dataset.id; });
          if (note) self.openEditor(note);
        });
      });
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
      // Capture first even if a write is already in flight: the queued write
      // uses this snapshot and a newer revision, so text is never dropped.
      this.capture();
      var rev = this._revision;
      var snapshot = JSON.parse(JSON.stringify(this.notes));
      this.saving = true;
      this.updateMeta();
      saveLocal(snapshot);
      var res = await this._enqueueWrite(snapshot, rev);
      // Only the newest revision may clear the dirty flag / print "Saved".
      if (rev === this._revision) {
        this.saving = false;
        if (res.ok) {
          this.dirty = false;
          this.updateMeta();
          this.renderList();
          this._announce(snapshot);
        } else {
          this.updateMeta();
          this.showStatus('Save failed: ' + (res.error || 'unknown error') + '. Your content is kept.');
        }
      }
      return res;
    },

    async saveAndClose() {
      var res = await this.save();
      if (res.ok) {
        document.getElementById('note-editor').classList.add('hidden');
        this.currentNote = null;
      }
    },

    async deleteNote(id) {
      this.notes = this.notes.filter(function (n) { return n.id !== id; });
      var res = await this.persist();
      this.renderList();
      if (!res.ok) this.showStatus('Delete failed: ' + (res.error || 'unknown error'));
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

      var timer;
      function autosave() {
        clearTimeout(timer);
        timer = setTimeout(function () { if (self.dirty) self.save(); }, 1000);
      }
      document.getElementById('note-title').addEventListener('input', function () { self.capture(); autosave(); });
      document.getElementById('note-body').addEventListener('input', function () { self.capture(); autosave(); });

      document.getElementById('menu-btn').addEventListener('click', function () {
        if (self.currentNote && window.confirm('Delete this note?')) {
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
