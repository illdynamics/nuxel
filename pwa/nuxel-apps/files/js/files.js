/* Nuxel Files (PWNAGE-30000)
 * Real directory browser + CRUD/copy/move/archive through the bridge storage
 * store.  The modal lifecycle is single-dialog (no hidden overlay stealing
 * input), selection is explicit, and clipboard mode clears only after a
 * successful move.  No file tree is invented when the backend is unavailable. */
(function () {
  'use strict';
  var el = {};
  ['back-btn','home-btn','refresh-btn','select-btn','selection-bar','selection-label','sel-all','sel-none','sel-cancel',
   'toolbar','new-folder-btn','rename-btn','delete-btn','copy-btn','cut-btn','paste-btn',
   'archive-btn','extract-btn','send-btn','clipboard-info','file-grid','status','cwd-abs',
   'prompt-dialog','prompt-title','prompt-input','prompt-error','prompt-cancel','prompt-ok',
   'confirm-dialog','confirm-text','confirm-cancel','confirm-ok','breadcrumb',
   'send-dialog','send-summary','send-device','send-progress','send-status','send-error',
   'send-close','send-ok','share-bluetooth','share-wifi','share-nearby'].forEach(function (id) {
    el[id] = document.getElementById(id);
    el[id.replace(/-([a-z])/g, function (_m, c) { return c.toUpperCase(); })] = el[id];
  });

  function bridgeCall(ns, verb, params) {
    if (window.NuxelBridge && typeof window.NuxelBridge.call === 'function') {
      return window.NuxelBridge.call(ns, verb, params).catch(function (e) { return { success: false, error: e && e.message }; });
    }
    return Promise.resolve({ success: false, offline: true, error: 'bridge unavailable' });
  }

  var app = {
    cwd: '/',
    home: '/home/nuxel',
    entries: [],
    selected: new Set(),
    selecting: false,
    clipboard: null,           // {mode:'copy'|'cut', paths:[...]}
    busy: false,
    prompt: null,              // {kind, title, placeholder, ok}
    _renderToken: 0,
    _sendTargets: [],

    init: async function () {
      this.bind();
      var info = await bridgeCall('storage', 'home', {});
      if (info && info.success !== false && info.home) this.home = info.home;
      await this.refresh();
    },

    bind: function () {
      var self = this;
      el.backBtn.addEventListener('click', function () { self.goUp(); });
      el.homeBtn.addEventListener('click', function () { self.cwd = '/'; self.refresh(); });
      el.refreshBtn.addEventListener('click', function () { self.refresh(); });
      el.selectBtn.addEventListener('click', function () { self.toggleSelect(); });
      el.selAll.addEventListener('click', function () { self.entries.forEach(function (e) { self.selected.add(e.path); }); self.updateSelection(); });
      el.selNone.addEventListener('click', function () { self.selected.clear(); self.updateSelection(); });
      el.selCancel.addEventListener('click', function () { self.selecting = false; self.selected.clear(); self.render(); });

      // ONE delegated grid listener instead of one listener per tile.
      el.fileGrid.addEventListener('click', function (ev) {
        var item = ev.target.closest && ev.target.closest('.file-item');
        if (item) self.onItem(item);
      });
      // ONE delegated breadcrumb listener.
      el.breadcrumb.addEventListener('click', function (ev) {
        var sp = ev.target.closest && ev.target.closest('span[data-path]');
        if (!sp) return;
        self.cwd = sp.dataset.path || '/';
        self.refresh();
      });
      el.sendBtn.addEventListener('click', function () { self.openSend(); });
      el.sendClose.addEventListener('click', function () { self.closeSend(); });
      el.sendOk.addEventListener('click', function () { self.sendSelected(); });
      el.shareBluetooth.addEventListener('click', function () { /* only working method */ });
      [el.shareWifi, el.shareNearby].forEach(function (b) {
        b.addEventListener('click', function (ev) { ev.preventDefault(); });
      });

      el.newFolderBtn.addEventListener('click', function () {
        self.openPrompt('mkdir', 'New folder', 'Folder name', function (name) { return self.mkdir(name); });
      });
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
        if (res.home) this.home = res.home;
        this.status(res.count ? (res.count + ' item(s)') : 'Folder is empty');
      } else {
        this.entries = [];
        this.status('Cannot list this folder: ' + ((res && res.error) || 'bridge unavailable'));
      }
      this.render();
    },

    render() {
      this.renderBreadcrumb();
      el.cwdAbs.textContent = this.absolutePath();
      this._syncControls();
      var token = ++this._renderToken;
      if (!this.entries.length) {
        el.fileGrid.innerHTML = '<div class="empty-state"><div class="empty-icon">📁</div><p>This folder is empty</p><p class="hint">Use New folder to add content. The listing is the real filesystem: nothing is invented.</p></div>';
        return;
      }
      // Progressive rendering: a 1000-entry directory must not create a
      // thousand nodes (and force layout) in one long task.  Each batch is
      // appended as a fragment; the scroll container keeps its native range as
      // the batches arrive.  A new directory/render cancels the old token.
      el.fileGrid.textContent = '';
      var rows = this.entries;
      var batch = 120;
      var index = 0;
      var append = function () {
        if (token !== app._renderToken) return;
        var frag = document.createDocumentFragment();
        var end = Math.min(rows.length, index + batch);
        for (; index < end; index++) frag.appendChild(app.itemNode(rows[index]));
        el.fileGrid.appendChild(frag);
        if (index < rows.length) {
          if (window.requestAnimationFrame) requestAnimationFrame(append);
          else setTimeout(append, 0);
        }
      };
      var raf = window.requestAnimationFrame || function (fn) { return setTimeout(fn, 0); };
      raf(append);
    },

    itemNode(f) {
      var isSel = this.selected.has(f.path);
      var node = document.createElement('div');
      node.className = 'file-item' + (isSel ? ' selected' : '') + (f.type === 'unreadable' ? ' unreadable' : '');
      node.dataset.path = f.path;
      node.dataset.type = f.type;
      var icon = f.type === 'folder' ? '📁' : (f.type === 'symlink' ? '🔗' : this.iconFor(f.name));
      var meta = f.type === 'folder' ? 'Folder'
        : (f.type === 'symlink' ? 'Symlink' : this.formatSize(f.size)) +
          (f.modified ? ' · ' + new Date(f.modified * 1000).toLocaleDateString() : '');
      var ic = document.createElement('div'); ic.className = 'file-icon'; ic.textContent = icon;
      var name = document.createElement('div'); name.className = 'file-name'; name.textContent = f.name;
      var mm = document.createElement('div'); mm.className = 'file-meta'; mm.textContent = meta;
      node.appendChild(ic); node.appendChild(name); node.appendChild(mm);
      return node;
    },

    _syncControls() {
      el.selectionBar.classList.toggle('hidden', !this.selecting);
      el.selectionLabel.textContent = this.selected.size + ' selected';
      el.renameBtn.disabled = this.selected.size !== 1;
      el.deleteBtn.disabled = this.selected.size === 0;
      el.copyBtn.disabled = this.selected.size === 0;
      el.cutBtn.disabled = this.selected.size === 0;
      el.sendBtn.disabled = this.selected.size === 0;
      el.pasteBtn.disabled = !this.clipboard || this.clipboard.paths.length === 0;
      el.archiveBtn.disabled = this.selected.size === 0;
      el.extractBtn.disabled = this.selected.size !== 1;
      el.clipboardInfo.textContent = this.clipboard ? ((this.clipboard.mode === 'cut' ? 'Moving: ' : 'Copying: ') + this.clipboard.paths.length) : '';
    },

    // Selection changes toggle only the affected tiles and the summary row;
    // they never rebuild the file grid.
    updateSelection() {
      var self = this;
      el.fileGrid.querySelectorAll('.file-item').forEach(function (node) {
        node.classList.toggle('selected', self.selected.has(node.dataset.path));
      });
      this._syncControls();
    },

    renderBreadcrumb() {
      var parts = this.cwd.split('/').filter(Boolean);
      var frag = document.createDocumentFragment();
      var root = document.createElement('span');
      root.dataset.path = '/'; root.title = this.home; root.textContent = '~';
      frag.appendChild(root);
      var cum = '';
      parts.forEach(function (p) {
        cum += '/' + p;
        var sep = document.createElement('span'); sep.className = 'sep'; sep.textContent = '/';
        var sp = document.createElement('span'); sp.dataset.path = cum; sp.textContent = p;
        frag.appendChild(sep); frag.appendChild(sp);
      });
      el.breadcrumb.textContent = '';
      el.breadcrumb.appendChild(frag);
    },

    onItem(item) {
      var path = item.dataset.path, type = item.dataset.type;
      if (this.selecting) {
        if (this.selected.has(path)) this.selected.delete(path); else this.selected.add(path);
        this.updateSelection();
        return;
      }
      if (type === 'folder') { this.cwd = path; this.refresh(); }
      else if (type === 'symlink') this.status('Symlink "' + path + '" — select it to rename, copy or delete the link.');
      else this.status('File "' + path + '" — use Gallery for photos/videos or another app to open this type.');
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
    // ---- Send -> Bluetooth OBEX -----------------------------------------
    openSend() {
      var paths = Array.from(this.selected);
      if (!paths.length) { this.status('Select one or more files first'); return; }
      this._sendPaths = paths;
      el.sendSummary.textContent = paths.length + ' file(s) selected';
      el.sendError.textContent = '';
      el.sendStatus.textContent = 'Reading paired Bluetooth devices…';
      el.sendProgress.hidden = true;
      el.sendProgress.value = 0;
      el.sendOk.disabled = true;
      el.sendDialog.classList.remove('hidden');
      this.loadSendTargets();
    },

    closeSend() {
      el.sendDialog.classList.add('hidden');
      el.sendOk.disabled = true;
      this._sending = false;
    },

    async loadSendTargets() {
      var res = await bridgeCall('bluetooth', 'send-targets', {});
      if (!res || res.success === false) {
        this._sendTargets = [];
        el.sendDevice.innerHTML = '<option value="">No devices</option>';
        el.sendStatus.textContent = 'Bluetooth OBEX unavailable';
        el.sendError.textContent = (res && (res.error || res.error_code)) || 'provider error';
        el.sendOk.disabled = true;
        return;
      }
      this._sendTargets = (res.devices || []).filter(function (d) { return d.paired; });
      if (!this._sendTargets.length) {
        this._sendTargets = res.devices || [];
      }
      el.sendDevice.replaceChildren();
      if (!this._sendTargets.length) {
        var empty = document.createElement('option');
        empty.value = ''; empty.textContent = 'No paired devices';
        el.sendDevice.appendChild(empty);
        el.sendStatus.textContent = 'Pair a receiving device in Settings → Bluetooth first.';
        el.sendOk.disabled = true;
        return;
      }
      this._sendTargets.forEach(function (d) {
        var o = document.createElement('option');
        o.value = d.address;
        o.textContent = d.name + ' · ' + d.address + (d.paired ? '' : ' (not paired)');
        el.sendDevice.appendChild(o);
      });
      el.sendStatus.textContent = 'Transfers use BlueZ OBEX Object Push.';
      el.sendOk.disabled = false;
    },

    async sendSelected() {
      if (this._sending) return;
      var address = el.sendDevice.value;
      if (!address) { el.sendError.textContent = 'Choose a receiving device'; return; }
      this._sending = true;
      el.sendOk.disabled = true;
      el.sendError.textContent = '';
      el.sendProgress.hidden = false;
      el.sendProgress.value = 10;
      el.sendStatus.textContent = 'Sending ' + this._sendPaths.length + ' file(s)…';
      try {
        if (window.bridge && typeof window.bridge.requestCapability === 'function') {
          var grant = await window.bridge.requestCapability('bluetooth:connect', 'Send files over Bluetooth');
          if (grant === false || (grant && grant.granted === false)) {
            throw new Error('Bluetooth send permission denied');
          }
        }
        var res = await bridgeCall('bluetooth', 'send-files', { paths: this._sendPaths, address: address });
        if (!res || res.success === false) {
          el.sendProgress.hidden = true;
          el.sendError.textContent = (res && res.error) || 'transfer failed';
          var rows = (res && res.files) || [];
          var sent = rows.filter(function (r) { return r.success; }).length;
          el.sendStatus.textContent = 'Sent ' + sent + ' of ' + (rows.length || this._sendPaths.length) +
            ' · failed ' + (rows.length ? rows.length - sent : this._sendPaths.length);
          this.status(el.sendStatus.textContent);
        } else {
          el.sendProgress.value = 100;
          el.sendStatus.textContent = 'Sent ' + res.sent + ' file(s) over Bluetooth';
          this.status('Bluetooth send complete: ' + res.sent + ' file(s)');
          setTimeout(function () { el.sendDialog.classList.add('hidden'); }, 900);
        }
      } catch (e) {
        el.sendError.textContent = e && e.message ? e.message : 'transfer error';
      } finally {
        this._sending = false;
        el.sendOk.disabled = false;
      }
    },

    absolutePath() {
      return this.cwd === '/' ? this.home : this.home.replace(/\/$/, '') + this.cwd;
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

  window.nuxelFiles = { app: function () { return app; } };
  document.addEventListener('DOMContentLoaded', function () { app.init(); });
})();
