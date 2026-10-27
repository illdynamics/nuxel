/* Nuxel Files (PWNAGE-30000)
 * Real directory browser + CRUD/copy/move/archive through the bridge storage
 * store.  The modal lifecycle is single-dialog (no hidden overlay stealing
 * input), selection is explicit, and clipboard mode clears only after a
 * successful move.  No file tree is invented when the backend is unavailable. */
(function () {
  'use strict';
  var el = {};
  ['back-btn','refresh-btn','select-btn','selection-bar','selection-label','sel-all','sel-none','sel-cancel',
   'toolbar','new-folder-btn','upload-btn','rename-btn','delete-btn','copy-btn','cut-btn','paste-btn',
   'archive-btn','extract-btn','clipboard-info','file-grid','status','file-input',
   'prompt-dialog','prompt-title','prompt-input','prompt-error','prompt-cancel','prompt-ok',
   'confirm-dialog','confirm-text','confirm-cancel','confirm-ok','breadcrumb'].forEach(function (id) {
    el[id] = document.getElementById(id);
  });

  function bridgeCall(ns, verb, params) {
    if (window.NuxelBridge && typeof window.NuxelBridge.call === 'function') {
      return window.NuxelBridge.call(ns, verb, params).catch(function (e) { return { success: false, error: e && e.message }; });
    }
    return Promise.resolve({ success: false, offline: true, error: 'bridge unavailable' });
  }

  var app = {
    cwd: '/',
    entries: [],
    selected: new Set(),
    selecting: false,
    clipboard: null,           // {mode:'copy'|'cut', paths:[...]}
    busy: false,
    prompt: null,              // {kind, title, placeholder, ok}

    init: async function () {
      this.bind();
      await this.refresh();
    },

    bind: function () {
      var self = this;
      el.backBtn.addEventListener('click', function () { self.goUp(); });
      el.refreshBtn.addEventListener('click', function () { self.refresh(); });
      el.selectBtn.addEventListener('click', function () { self.toggleSelect(); });
      el.selAll.addEventListener('click', function () { self.entries.forEach(function (e) { self.selected.add(e.path); }); self.render(); });
      el.selNone.addEventListener('click', function () { self.selected.clear(); self.render(); });
      el.selCancel.addEventListener('click', function () { self.selecting = false; self.selected.clear(); self.render(); });

      el.newFolderBtn.addEventListener('click', function () {
        self.openPrompt('mkdir', 'New folder', 'Folder name', function (name) { return self.mkdir(name); });
      });
      el.uploadBtn.addEventListener('click', function () { el.fileInput.click(); });
      el.fileInput.addEventListener('change', function (ev) { self.upload(ev.target.files); ev.target.value = ''; });
      el.renameBtn.addEventListener('click', function () {
        var one = self.oneSelected(); if (!one) return;
        self.openPrompt('rename', 'Rename', 'New name', function (name) { return self.rename(one, name); });
      });
      el.deleteBtn.addEventListener('click', function () { self.confirmDelete(); });
      el.copyBtn.addEventListener('click', function () { self.clipboard = { mode: 'copy', paths: Array.from(self.selected) }; self.render(); });
      el.cutBtn.addEventListener('click', function () { self.clipboard = { mode: 'cut', paths: Array.from(self.selected) }; self.render(); });
      el.pasteBtn.addEventListener('click', function () { self.paste(); });
      el.archiveBtn.addEventListener('click', function () {
        var paths = Array.from(self.selected); if (!paths.length) return;
        self.openPrompt('archive', 'Create ZIP archive', 'Archive name (e.g. backup.zip)', function (name) { return self.archive(paths, name); });
      });
      el.extractBtn.addEventListener('click', function () {
        var one = self.oneSelected(); if (!one) return;
        if (!one.name.toLowerCase().endsWith('.zip')) { self.status('Select a .zip file to extract'); return; }
        self.openPrompt('extract', 'Extract archive', 'Destination folder (blank = here)', function (name) { return self.extract(one, name); });
      });

      el.promptCancel.addEventListener('click', function () { self.closePrompt(); });
      el.promptOk.addEventListener('click', function () { self.submitPrompt(); });
      el.promptInput.addEventListener('keydown', function (e) { if (e.key === 'Enter') self.submitPrompt(); });
      el.confirmCancel.addEventListener('click', function () { el.confirmDialog.classList.add('hidden'); });
      el.confirmOk.addEventListener('click', function () { self.doDelete(); });
    },

    async refresh() {
      this.status('Loading…');
      var res = await bridgeCall('storage', 'list-dir', { path: this.cwd });
      if (res && res.success !== false && Array.isArray(res.entries)) {
        this.entries = res.entries;
        this.selected = new Set(Array.from(this.selected).filter(function (p) { return res.entries.some(function (e) { return e.path === p; }); }));
        this.status(res.count ? (res.count + ' item(s)') : 'Folder is empty');
      } else {
        this.entries = [];
        this.status('Cannot list this folder: ' + ((res && res.error) || 'bridge unavailable'));
      }
      this.render();
    },

    render() {
      this.renderBreadcrumb();
      var self = this;
      el.selectionBar.classList.toggle('hidden', !this.selecting);
      el.selectionLabel.textContent = this.selected.size + ' selected';
      el.renameBtn.disabled = this.selected.size !== 1;
      el.deleteBtn.disabled = this.selected.size === 0;
      el.copyBtn.disabled = this.selected.size === 0;
      el.cutBtn.disabled = this.selected.size === 0;
      el.pasteBtn.disabled = !this.clipboard || this.clipboard.paths.length === 0;
      el.archiveBtn.disabled = this.selected.size === 0;
      el.extractBtn.disabled = this.selected.size !== 1;
      el.clipboardInfo.textContent = this.clipboard ? ((this.clipboard.mode === 'cut' ? 'Moving: ' : 'Copying: ') + this.clipboard.paths.length) : '';

      if (!this.entries.length) {
        el.fileGrid.innerHTML = '<div class="empty-state"><div class="empty-icon">📁</div><p>This folder is empty</p><p class="hint">Use New folder or Upload to add content. Listing comes from the Nuxel bridge storage store — nothing is invented.</p></div>';
        return;
      }
      el.fileGrid.innerHTML = this.entries.map(function (f) {
        var isSel = self.selected.has(f.path);
        var icon = f.type === 'folder' ? '📁' : self.iconFor(f.name);
        var meta = f.type === 'folder' ? 'Folder' : self.formatSize(f.size);
        return '<div class="file-item' + (isSel ? ' selected' : '') + (f.type === 'unreadable' ? ' unreadable' : '') + '" data-path="' + self.esc(f.path) + '" data-type="' + self.esc(f.type) + '">' +
          '<div class="file-icon">' + icon + '</div>' +
          '<div class="file-name">' + self.esc(f.name) + '</div>' +
          '<div class="file-meta">' + self.esc(meta) + '</div></div>';
      }).join('');
      el.fileGrid.querySelectorAll('.file-item').forEach(function (item) {
        item.addEventListener('click', function () { self.onItem(item); });
      });
    },

    renderBreadcrumb() {
      var parts = this.cwd.split('/').filter(Boolean);
      var html = '<span data-path="/">Files</span>';
      var cum = '';
      parts.forEach(function (p) {
        cum += '/' + p;
        html += '<span class="sep">/</span><span data-path="' + cum + '">' + app.esc(p) + '</span>';
      });
      el.breadcrumb.innerHTML = html;
      el.breadcrumb.querySelectorAll('span[data-path]').forEach(function (sp) {
        sp.addEventListener('click', function () { app.cwd = sp.dataset.path || '/'; app.refresh(); });
      });
    },

    onItem(item) {
      var path = item.dataset.path, type = item.dataset.type;
      if (this.selecting) {
        if (this.selected.has(path)) this.selected.delete(path); else this.selected.add(path);
        this.render();
        return;
      }
      if (type === 'folder') { this.cwd = path; this.refresh(); }
      else this.status('Open file "' + path + '" with the platform handler (bridge stores metadata, not an inline viewer).');
    },

    goUp() {
      if (this.cwd === '/') return;
      var parts = this.cwd.split('/').filter(Boolean);
      parts.pop();
      this.cwd = parts.length ? '/' + parts.join('/') : '/';
      this.refresh();
    },

    toggleSelect() {
      this.selecting = !this.selecting;
      this.selected.clear();
      this.render();
    },

    oneSelected() {
      if (this.selected.size !== 1) { this.status('Select exactly one item'); return null; }
      var p = Array.from(this.selected)[0];
      return this.entries.find(function (e) { return e.path === p; }) || null;
    },

    // ---- dialogs ---------------------------------------------------------
    openPrompt(kind, title, placeholder, cb) {
      this.prompt = { kind: kind, title: title, placeholder: placeholder, ok: cb };
      el.promptTitle.textContent = title;
      el.promptInput.value = '';
      el.promptInput.placeholder = placeholder;
      el.promptError.textContent = '';
      el.promptDialog.classList.remove('hidden');
      setTimeout(function () { el.promptInput.focus(); }, 50);
    },
    closePrompt() {
      el.promptDialog.classList.add('hidden');
      this.prompt = null;
    },
    async submitPrompt() {
      if (!this.prompt) return;
      var value = el.promptInput.value.trim();
      if (!value) { el.promptError.textContent = 'A value is required'; return; }
      el.promptError.textContent = '';
      var cb = this.prompt.ok;
      this.closePrompt();
      await cb(value);
    },
    confirmDelete() {
      if (!this.selected.size) return;
      el.confirmText.textContent = 'Delete ' + this.selected.size + ' item(s)? This cannot be undone.';
      el.confirmDialog.classList.remove('hidden');
    },
    async doDelete() {
      el.confirmDialog.classList.add('hidden');
      var paths = Array.from(this.selected);
      var failed = 0;
      for (var i = 0; i < paths.length; i++) {
        var res = await bridgeCall('storage', 'delete', { path: paths[i] });
        if (!res || res.success === false) failed++;
      }
      this.selected.clear();
      this.status(failed ? ('Deleted with ' + failed + ' failure(s)') : 'Deleted');
      await this.refresh();
    },

    // ---- operations ------------------------------------------------------
    async mkdir(name) {
      var path = this.cwd === '/' ? '/' + name : this.cwd + '/' + name;
      var res = await bridgeCall('storage', 'mkdir', { path: path });
      this.status(res && res.success !== false ? 'Folder created' : ('Create failed: ' + (res && res.error)));
      await this.refresh();
    },
    async rename(item, name) {
      var base = item.path.substring(0, item.path.lastIndexOf('/'));
      var dst = (base || '') + '/' + name;
      var res = await bridgeCall('storage', 'rename', { src: item.path, dst: dst });
      this.status(res && res.success !== false ? 'Renamed' : ('Rename failed: ' + (res && res.error)));
      await this.refresh();
    },
    async paste() {
      if (!this.clipboard || !this.clipboard.paths.length) return;
      var failed = 0;
      for (var i = 0; i < this.clipboard.paths.length; i++) {
        var src = this.clipboard.paths[i];
        var name = src.split('/').filter(Boolean).pop();
        var dst = (this.cwd === '/' ? '' : this.cwd) + '/' + name;
        if (dst === src) continue;
        var res = this.clipboard.mode === 'copy'
          ? await bridgeCall('storage', 'copy', { src: src, dst: dst })
          : await bridgeCall('storage', 'move', { src: src, dst: dst });
        if (!res || res.success === false) failed++;
      }
      if (failed) this.status('Paste finished with ' + failed + ' failure(s)');
      else {
        if (this.clipboard.mode === 'cut') this.clipboard = null;
        this.status(this.clipboard ? 'Copied' : 'Moved');
      }
      await this.refresh();
    },
    async archive(paths, name) {
      if (!/\.zip$/i.test(name)) name += '.zip';
      var dest = (this.cwd === '/' ? '' : this.cwd) + '/' + name;
      var res = await bridgeCall('storage', 'archive-create', { sources: paths, dest: dest });
      this.status(res && res.success !== false ? 'Archive created' : ('Archive failed: ' + (res && res.error)));
      await this.refresh();
    },
    async extract(item, name) {
      var dest = name ? (this.cwd === '/' ? '/' + name : this.cwd + '/' + name) : this.cwd;
      var res = await bridgeCall('storage', 'archive-extract', { archive: item.path, dest: dest });
      this.status(res && res.success !== false ? 'Extracted' : ('Extract failed: ' + (res && res.error)));
      await this.refresh();
    },
    async upload(files) {
      var done = 0, failed = 0;
      for (var i = 0; i < files.length; i++) {
        var f = files[i];
        var path = (this.cwd === '/' ? '' : this.cwd) + '/' + f.name;
        try {
          var b64 = await readAsDataURL(f);
          var comma = b64.indexOf(',');
          var res = await bridgeCall('storage', 'write-file', { path: path, data_b64: comma >= 0 ? b64.slice(comma + 1) : b64 });
          if (res && res.success !== false) done++; else failed++;
        } catch (e) { failed++; }
      }
      this.status('Uploaded ' + done + (failed ? ', ' + failed + ' failed' : ''));
      await this.refresh();
    },

    iconFor(name) {
      var ext = (name.split('.').pop() || '').toLowerCase();
      if (['jpg','jpeg','png','gif','webp','svg'].includes(ext)) return '🖼️';
      if (['mp3','wav','flac','ogg'].includes(ext)) return '🎵';
      if (['mp4','mov','avi','mkv','webm'].includes(ext)) return '🎬';
      if (['zip','tar','gz','bz2','7z'].includes(ext)) return '📦';
      if (['txt','md','log'].includes(ext)) return '📃';
      if (['pdf'].includes(ext)) return '📄';
      if (['json','xml','yaml','yml'].includes(ext)) return '📋';
      return '📄';
    },
    formatSize(n) {
      if (!n && n !== 0) return '';
      var units = ['B','KB','MB','GB'];
      var i = 0, size = n;
      while (size >= 1024 && i < units.length - 1) { size /= 1024; i++; }
      return size.toFixed(i === 0 ? 0 : 1) + ' ' + units[i];
    },
    status(msg) { el.status.textContent = msg; },
    esc(s) {
      var d = document.createElement('div');
      d.textContent = String(s == null ? '' : s);
      return d.innerHTML;
    }
  };

  function readAsDataURL(file) {
    return new Promise(function (resolve, reject) {
      var r = new FileReader();
      r.onload = function () { resolve(r.result); };
      r.onerror = function () { reject(r.error); };
      r.readAsDataURL(file);
    });
  }

  window.nuxelFiles = { app: function () { return app; } };
  document.addEventListener('DOMContentLoaded', function () { app.init(); });
})();
