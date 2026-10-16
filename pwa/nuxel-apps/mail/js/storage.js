// Nuxel Mail — local store (js/storage.js)
//
// ONE data model for the whole app, used by mail.js and transport.js:
//
//   account : { id, email, name, imap_host, imap_port, smtp_host, smtp_port,
//               use_tls, created_at, transport, credentials: 'not-stored' }
//   message : { id, account_id, folder, from, to[], subject, body,
//               timestamp, flags[], read, direction, delivery }
//
// `delivery` is the honest per-message state and is never guessed:
//   'received'   — it came from a real transport
//   'sent'       — the transport confirmed the send
//   'queued'     — written to OUTBOX because no transport could send it
//   'draft'      — the user has not pressed Send
//   'imported'   — it came from an import file
//
// BACKENDS. IndexedDB is used when the engine provides it (WebKitGTK on the
// phone does). When it is missing or blocked (plain webview, private mode,
// stripped engine) the SAME async API is served from localStorage. When even
// localStorage is unavailable the store keeps the session in memory and SAYS SO
// through `backend` / `degraded` instead of silently losing data.
//
// Credentials are deliberately NOT stored in this revision: `credentials` is
// always 'not-stored' and a transport that needs a password reports
// NEEDS_CREDENTIALS. That is a real limitation, not a placeholder.
(function (global) {
  'use strict';

  var DB_NAME = 'nuxel-mail';
  var DB_VERSION = 2;
  var LS_KEY = 'nuxel-mail-store-v2';
  var FOLDERS = ['INBOX', 'OUTBOX', 'SENT', 'ARCHIVE', 'DRAFTS'];

  function uid(prefix) {
    return prefix + '-' + Date.now().toString(36) + '-' + Math.random().toString(36).slice(2, 8);
  }

  function MailStorage() {
    this.backend = 'memory';
    this.degraded = false;
    this.db = null;
    this.mem = { accounts: [], messages: [] };
  }

  MailStorage.prototype.init = function () {
    var self = this;
    if (typeof global.indexedDB === 'undefined' || !global.indexedDB) {
      this._initFallback('indexedDB unavailable in this engine');
      return Promise.resolve(this.backend);
    }
    return new Promise(function (resolve) {
      var req;
      try {
        req = global.indexedDB.open(DB_NAME, DB_VERSION);
      } catch (e) {
        self._initFallback('indexedDB refused to open: ' + e.message);
        return resolve(self.backend);
      }
      req.onupgradeneeded = function (ev) {
        var db = ev.target.result;
        if (!db.objectStoreNames.contains('accounts')) {
          var a = db.createObjectStore('accounts', { keyPath: 'id' });
          a.createIndex('email', 'email', { unique: true });
        }
        if (!db.objectStoreNames.contains('messages')) {
          var m = db.createObjectStore('messages', { keyPath: 'id' });
          m.createIndex('account_id', 'account_id', { unique: false });
          m.createIndex('folder', 'folder', { unique: false });
          m.createIndex('timestamp', 'timestamp', { unique: false });
        }
      };
      req.onsuccess = function (ev) {
        self.db = ev.target.result;
        self.backend = 'indexeddb';
        resolve(self.backend);
      };
      req.onerror = function () {
        self._initFallback('indexedDB open failed');
        resolve(self.backend);
      };
      req.onblocked = function () {
        self._initFallback('indexedDB blocked by another connection');
        resolve(self.backend);
      };
    });
  };

  MailStorage.prototype._initFallback = function (why) {
    try {
      if (global.localStorage) {
        global.localStorage.setItem(LS_KEY + ':probe', '1');
        global.localStorage.removeItem(LS_KEY + ':probe');
        this.backend = 'localStorage';
        this.fallback_reason = why;
        return;
      }
    } catch (e) { /* storage denied (private mode): fall through to memory */ }
    this.backend = 'memory';
    this.degraded = true;
    this.fallback_reason = why + '; localStorage unavailable -> session-only store';
  };

  /* ---------------- localStorage / memory helpers ---------------- */
  MailStorage.prototype._readLS = function () {
    if (this.backend === 'memory') return this.mem;
    try {
      var raw = global.localStorage.getItem(LS_KEY);
      var doc = raw ? JSON.parse(raw) : null;
      if (!doc || typeof doc !== 'object') doc = { accounts: [], messages: [] };
      doc.accounts = doc.accounts || []; doc.messages = doc.messages || [];
      return doc;
    } catch (e) { return { accounts: [], messages: [] }; }
  };
  MailStorage.prototype._writeLS = function (doc) {
    if (this.backend === 'memory') { this.mem = doc; return true; }
    try { global.localStorage.setItem(LS_KEY, JSON.stringify(doc)); return true; }
    catch (e) { this.backend = 'memory'; this.degraded = true; this.mem = doc; return false; }
  };

  /* ---------------- accounts ---------------- */
  MailStorage.prototype.addAccount = function (config) {
    var self = this;
    var account = {
      id: config.id || uid('acct'),
      email: String(config.email || '').trim(),
      name: config.name || String(config.email || '').split('@')[0],
      imap_host: config.imap_host || '',
      imap_port: Number(config.imap_port || 993),
      smtp_host: config.smtp_host || '',
      smtp_port: Number(config.smtp_port || 587),
      use_tls: config.use_tls !== false,
      created_at: new Date().toISOString(),
      // no credential material is ever written by this app
      credentials: 'not-stored',
      transport: 'unconfigured'
    };
    if (!account.email) return Promise.reject(new Error('an email address is required'));
    return this.getAccounts().then(function (accounts) {
      if (accounts.some(function (a) { return a.email === account.email; })) {
        throw new Error('that account is already configured');
      }
      if (self.backend === 'indexeddb') {
        return self._idbPut('accounts', account).then(function () { return account; });
      }
      var doc = self._readLS();
      doc.accounts.push(account);
      self._writeLS(doc);
      return account;
    });
  };

  MailStorage.prototype.getAccounts = function () {
    var self = this;
    if (this.backend === 'indexeddb') {
      return this._idbAll('accounts');
    }
    return Promise.resolve(this._readLS().accounts.slice());
  };

  MailStorage.prototype.updateAccount = function (id, patch) {
    var self = this;
    return this.getAccounts().then(function (accounts) {
      var found = accounts.filter(function (a) { return a.id === id; })[0];
      if (!found) throw new Error('no such account: ' + id);
      var next = Object.assign({}, found, patch || {}, { id: id, credentials: 'not-stored' });
      if (self.backend === 'indexeddb') return self._idbPut('accounts', next).then(function () { return next; });
      var doc = self._readLS();
      doc.accounts = doc.accounts.map(function (a) { return a.id === id ? next : a; });
      self._writeLS(doc);
      return next;
    });
  };

  MailStorage.prototype.deleteAccount = function (id) {
    var self = this;
    if (this.backend === 'indexeddb') return this._idbDelete('accounts', id);
    var doc = this._readLS();
    doc.accounts = doc.accounts.filter(function (a) { return a.id !== id; });
    this._writeLS(doc);
    return Promise.resolve(true);
  };

  /* ---------------- messages ---------------- */
  MailStorage.prototype.saveMessages = function (list) {
    var self = this;
    var messages = (list || []).map(function (msg) {
      var out = Object.assign({}, msg);
      out.id = out.id || uid('msg');
      out.folder = out.folder || 'INBOX';
      out.flags = out.flags || [];
      out.timestamp = out.timestamp || new Date().toISOString();
      return out;
    });
    if (!messages.length) return Promise.resolve([]);
    if (this.backend === 'indexeddb') {
      return Promise.all(messages.map(function (m) { return self._idbPut('messages', m); }))
        .then(function () { return messages; });
    }
    var doc = this._readLS();
    messages.forEach(function (m) {
      var at = doc.messages.findIndex(function (x) { return x.id === m.id; });
      if (at >= 0) doc.messages[at] = m; else doc.messages.push(m);
    });
    this._writeLS(doc);
    return Promise.resolve(messages);
  };

  MailStorage.prototype.getMessages = function (accountId, folder, limit) {
    var f = folder || 'INBOX';
    var lim = limit || 200;
    var self = this;
    var filter = function (list) {
      return list.filter(function (m) {
        return (!accountId || m.account_id === accountId) && m.folder === f;
      }).sort(function (a, b) { return new Date(b.timestamp) - new Date(a.timestamp); }).slice(0, lim);
    };
    if (this.backend === 'indexeddb') {
      return this._idbAll('messages').then(filter);
    }
    return Promise.resolve(filter(self._readLS().messages));
  };

  MailStorage.prototype.getMessage = function (id) {
    if (this.backend === 'indexeddb') return this._idbGet('messages', id);
    var found = this._readLS().messages.filter(function (m) { return m.id === id; })[0];
    return Promise.resolve(found || null);
  };

  MailStorage.prototype.markAsRead = function (id) {
    return this._patchMessage(id, { read: true, flags: ['\\Seen'] });
  };

  MailStorage.prototype.moveMessage = function (id, folder) {
    return this._patchMessage(id, { folder: folder });
  };

  MailStorage.prototype.deleteMessage = function (id) {
    var self = this;
    if (this.backend === 'indexeddb') return this._idbDelete('messages', id);
    var doc = this._readLS();
    doc.messages = doc.messages.filter(function (m) { return m.id !== id; });
    this._writeLS(doc);
    return Promise.resolve(true);
  };

  MailStorage.prototype._patchMessage = function (id, patch) {
    var self = this;
    return this.getMessage(id).then(function (msg) {
      if (!msg) throw new Error('no such message: ' + id);
      var next = Object.assign({}, msg, patch);
      if (next.flags && next.flags.indexOf('\\Seen') >= 0) next.read = true;
      if (self.backend === 'indexeddb') return self._idbPut('messages', next).then(function () { return next; });
      var doc = self._readLS();
      doc.messages = doc.messages.map(function (m) { return m.id === id ? next : m; });
      self._writeLS(doc);
      return next;
    });
  };

  MailStorage.prototype.counts = function () {
    var self = this;
    return (this.backend === 'indexeddb' ? this._idbAll('messages') : Promise.resolve(this._readLS().messages))
      .then(function (list) {
        var out = { total: list.length, unread: 0, by_folder: {} };
        list.forEach(function (m) {
          out.by_folder[m.folder] = (out.by_folder[m.folder] || 0) + 1;
          if (!m.read && m.folder === 'INBOX') out.unread++;
        });
        return out;
      });
  };

  /* ---------------- import / export (portable JSON) ---------------- */
  MailStorage.prototype.exportAll = function () {
    var self = this;
    return Promise.all([this.getAccounts(), this._allMessages()]).then(function (res) {
      return {
        schema: 'nuxel.mail/1',
        exported_at: new Date().toISOString(),
        backend: self.backend,
        credentials: 'not-included (this app never stores them)',
        accounts: res[0],
        messages: res[1]
      };
    });
  };

  MailStorage.prototype.importAll = function (doc) {
    var self = this;
    if (!doc || typeof doc !== 'object' || !Array.isArray(doc.accounts) || !Array.isArray(doc.messages)) {
      return Promise.reject(new Error('not a nuxel.mail export (schema nuxel.mail/1 expected)'));
    }
    var accounts = doc.accounts.map(function (a) {
      return Object.assign({}, a, { credentials: 'not-stored' });
    });
    var messages = doc.messages.map(function (m) {
      return Object.assign({}, m, { delivery: m.delivery === 'sent' ? 'sent' : 'imported' });
    });
    return self.getAccounts().then(function (existing) {
      var known = existing.map(function (a) { return a.email; });
      var added = accounts.filter(function (a) { return known.indexOf(a.email) < 0; });
      var skip = accounts.length - added.length;
      return Promise.all(added.map(function (a) {
        if (self.backend === 'indexeddb') return self._idbPut('accounts', a);
        var d = self._readLS(); d.accounts.push(a); self._writeLS(d); return a;
      })).then(function () {
        return self.saveMessages(messages);
      }).then(function () {
        return { accounts_added: added.length, accounts_skipped: skip, messages_imported: messages.length };
      });
    });
  };

  MailStorage.prototype.clearAll = function () {
    var self = this;
    if (this.backend === 'indexeddb') {
      return Promise.all([this._idbClear('accounts'), this._idbClear('messages')]).then(function () { return true; });
    }
    this._writeLS({ accounts: [], messages: [] });
    return Promise.resolve(true);
  };

  MailStorage.prototype._allMessages = function () {
    if (this.backend === 'indexeddb') return this._idbAll('messages');
    return Promise.resolve(this._readLS().messages.slice());
  };

  /* ---------------- IndexedDB plumbing ---------------- */
  MailStorage.prototype._idbTx = function (store, mode, fn) {
    var self = this;
    return new Promise(function (resolve, reject) {
      var tx, os;
      try {
        tx = self.db.transaction(store, mode);
        os = tx.objectStore(store);
      } catch (e) { return reject(e); }
      var req = fn(os);
      if (req) {
        req.onsuccess = function () { resolve(req.result); };
        req.onerror = function () { reject(req.error); };
      } else {
        tx.oncomplete = function () { resolve(true); };
        tx.onerror = function () { reject(tx.error); };
      }
    });
  };
  MailStorage.prototype._idbPut = function (store, value) { return this._idbTx(store, 'readwrite', function (os) { return os.put(value); }); };
  MailStorage.prototype._idbGet = function (store, key) { return this._idbTx(store, 'readonly', function (os) { return os.get(key); }); };
  MailStorage.prototype._idbDelete = function (store, key) { return this._idbTx(store, 'readwrite', function (os) { return os.delete(key); }); };
  MailStorage.prototype._idbClear = function (store) { return this._idbTx(store, 'readwrite', function (os) { return os.clear(); }); };
  MailStorage.prototype._idbAll = function (store) {
    return this._idbTx(store, 'readonly', function (os) { return os.getAll(); }).then(function (r) { return r || []; });
  };

  global.MailStorage = MailStorage;
  global.FOLDERS = FOLDERS;
  global.mailStorage = new MailStorage();
  global.nuxelMailSchema = { schema: 'nuxel.mail/1', folders: FOLDERS, backend: 'reported by mailStorage.backend' };
})(typeof window !== 'undefined' ? window : this);
