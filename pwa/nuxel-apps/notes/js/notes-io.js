// Nuxel Notes - data layer extension (mission area 30)
//
// Adds what the core inventory requires of a notes app without rewriting the
// existing editor: offline search, pinning, Markdown/JSON export, JSON import
// and a real storage report.  Everything stays in localStorage key
// "nuxel-notes" plus the optional bridge copy; notes never leave the device.
(function () {
  'use strict';

  function whenReady(cb) {
    if (window.notesApp) { cb(window.notesApp); return; }
    var tries = 0;
    var t = setInterval(function () {
      tries++;
      if (window.notesApp) { clearInterval(t); cb(window.notesApp); }
      else if (tries > 60) { clearInterval(t); }
    }, 100);
  }

  function download(name, text, mime) {
    try {
      var a = document.createElement('a');
      a.href = URL.createObjectURL(new Blob([text], { type: mime || 'text/plain' }));
      a.download = name;
      document.body.appendChild(a); a.click();
      setTimeout(function () { URL.revokeObjectURL(a.href); a.remove(); }, 2000);
      return true;
    } catch (e) { return false; }
  }

  whenReady(function (app) {
    var query = '';

    /* ---------- search + pin wiring around the existing renderer ---------- */
    var originalRender = app._renderList.bind(app);
    app._renderList = function () {
      originalRender();
      var list = document.getElementById('notes-list');

      // pinned notes first, then the search filter
      if (query) {
        var q = query.toLowerCase();
        var matches = (app.notes || []).filter(function (n) {
          return ((n.title || '') + ' ' + (n.body || '')).toLowerCase().indexOf(q) >= 0;
        });
        if (!matches.length) {
          list.innerHTML = '<div class="empty-state"><div class="empty-icon">🔍</div>' +
            '<h3>No note matches “' + query.replace(/[<>&]/g, '') + '”</h3>' +
            '<p>Search covers note titles and bodies, entirely on this device.</p></div>';
          return;
        }
        list.innerHTML = matches.map(function (note) { return card(note); }).join('');
      } else {
        var sorted = (app.notes || []).slice().sort(function (a, b) {
          if (!!b.pinned !== !!a.pinned) return (b.pinned ? 1 : 0) - (a.pinned ? 1 : 0);
          return new Date(b.updatedAt) - new Date(a.updatedAt);
        });
        if (sorted.length) list.innerHTML = sorted.map(function (note) { return card(note); }).join('');
      }

      list.querySelectorAll('.note-card').forEach(function (el) {
        var id = el.dataset.id;
        var note = (app.notes || []).filter(function (n) { return n.id === id; })[0];
        el.addEventListener('click', function (ev) {
          if (ev.target && ev.target.classList.contains('pin-toggle')) return;
          if (note) app._openEditor(note);
        });
        var star = el.querySelector('.pin-toggle');
        if (star) {
          star.addEventListener('click', function (ev) {
            ev.stopPropagation();
            if (!note) return;
            note.pinned = !note.pinned;
            app._saveNotes();
            app._renderList();
          });
        }
      });
    };

    function escapeHtml(str) {
      var d = document.createElement('div');
      d.textContent = String(str == null ? '' : str);
      return d.innerHTML;
    }
    function card(note) {
      return '<div class="note-card" data-id="' + escapeHtml(note.id) + '">' +
        '<button class="pin-toggle" title="Pin this note" aria-label="Pin">' + (note.pinned ? '★' : '☆') + '</button>' +
        '<div class="note-card-title">' + escapeHtml(note.title || 'Untitled') + '</div>' +
        '<div class="note-card-preview">' + escapeHtml((note.body || '').substring(0, 100)) + '</div>' +
        '<div class="note-card-date">' + escapeHtml(app._formatDate(note.updatedAt)) +
        ' · ' + (note.body || '').split(/\s+/).filter(Boolean).length + ' words</div>' +
        '</div>';
    }

    /* ---------- toolbar (search / export / import / counts) ---------- */
    var bar = document.createElement('div');
    bar.id = 'notes-io-bar';
    bar.style.cssText = 'display:flex;gap:6px;align-items:center;padding:6px 10px;flex-wrap:wrap;' +
      'background:#141c2b;border-bottom:1px solid #223049;';
    bar.innerHTML =
      '<input id="notes-search" type="search" placeholder="Search notes (offline)" ' +
      'style="flex:1 1 130px;background:#0f1622;border:1px solid #2a3a56;color:#e7eefc;border-radius:9px;padding:7px 9px;font-size:13px">' +
      '<button id="notes-export-json" style="font-size:12px">Export JSON</button>' +
      '<button id="notes-export-md" style="font-size:12px">Export Markdown</button>' +
      '<button id="notes-import" style="font-size:12px">Import</button>' +
      '<span id="notes-count" style="font-size:11px;color:#8fa0c4"></span>' +
      '<input id="notes-file" type="file" accept="application/json,.json" style="display:none">';
    var top = document.querySelector('.top-bar');
    if (top && top.parentNode) top.parentNode.insertBefore(bar, top.nextSibling);

    document.getElementById('notes-search').addEventListener('input', function (ev) {
      query = ev.target.value || '';
      app._renderList();
    });

    function counts() {
      var notes = app.notes || [];
      var words = notes.reduce(function (n, x) { return n + (x.body || '').split(/\s+/).filter(Boolean).length; }, 0);
      var pinned = notes.filter(function (n) { return n.pinned; }).length;
      document.getElementById('notes-count').textContent =
        notes.length + ' notes · ' + words + ' words · ' + pinned + ' pinned';
    }
    var originalSave = app._saveNotes.bind(app);
    app._saveNotes = function () { originalSave(); counts(); };

    document.getElementById('notes-export-json').addEventListener('click', function () {
      var text = JSON.stringify({ schema_version: 1, exported_at: new Date().toISOString(), notes: app.notes || [] }, null, 2);
      if (download('nuxel-notes.json', text, 'application/json')) {
        document.getElementById('notes-count').textContent = 'exported ' + (app.notes || []).length + ' notes';
      }
    });
    document.getElementById('notes-export-md').addEventListener('click', function () {
      var md = '# Nuxel Notes export\n\n';
      (app.notes || []).forEach(function (n) {
        md += '## ' + (n.title || 'Untitled') + (n.pinned ? '  ★' : '') + '\n\n';
        md += '_created ' + n.createdAt + ' · updated ' + n.updatedAt + '_\n\n';
        md += (n.body || '') + '\n\n---\n\n';
      });
      if (download('nuxel-notes.md', md, 'text/markdown')) {
        document.getElementById('notes-count').textContent = 'exported Markdown';
      }
    });
    document.getElementById('notes-import').addEventListener('click', function () {
      document.getElementById('notes-file').click();
    });
    document.getElementById('notes-file').addEventListener('change', function (ev) {
      var f = ev.target.files && ev.target.files[0];
      if (!f) return;
      var reader = new FileReader();
      reader.onload = function () {
        try {
          var incoming = JSON.parse(String(reader.result));
          var notes = Array.isArray(incoming) ? incoming : incoming.notes;
          if (!Array.isArray(notes)) throw new Error('no note list in that file');
          var added = 0;
          notes.forEach(function (n) {
            if (!n || typeof n !== 'object') return;
            var note = {
              id: n.id || ('note-' + Date.now() + '-' + added),
              title: n.title || 'Imported note',
              body: n.body || '',
              createdAt: n.createdAt || new Date().toISOString(),
              updatedAt: n.updatedAt || new Date().toISOString(),
              pinned: !!n.pinned
            };
            var dup = (app.notes || []).some(function (x) { return x.id === note.id; });
            if (dup) note.id = 'note-' + Date.now() + '-' + added;
            app.notes.push(note);
            added++;
          });
          app._saveNotes();
          app._renderList();
          document.getElementById('notes-count').textContent = 'imported ' + added + ' notes';
        } catch (e) {
          document.getElementById('notes-count').textContent = 'import failed: ' + e.message;
        }
        ev.target.value = '';
      };
      reader.readAsText(f);
    });

    counts();
    app._renderList();

    // headless smoke-test hook
    window.nuxelNotesIO = { counts: counts, card: card, setQuery: function (q) { query = q; app._renderList(); } };
  });
})();
