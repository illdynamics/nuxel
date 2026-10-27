// Nuxel Mail — application logic (js/mail.js)
//
// HONESTY RULES ENCODED HERE (mission area 30 "Mail" + area 55):
//   * a message is only labelled "Sent" when the transport confirmed it;
//     otherwise it is written to Outbox and labelled "Queued — not sent" with
//     the reason the transport gave;
//   * no message, account, recipient or delivery receipt is ever invented;
//   * the local store backend (IndexedDB / localStorage / memory) and the
//     transport state are both shown in the UI, because "where is my mail" and
//     "can this send" must be answerable without reading code.
//
// The account model, message model and import/export format all live in
// js/storage.js (schema 'nuxel.mail/1') so the app, an export file and a future
// native client agree on one shape.
(function () {
  'use strict';

  var els = {};
  var FOLDERS = ['INBOX', 'OUTBOX', 'SENT', 'ARCHIVE'];

  function $(id) { return document.getElementById(id); }

  function MailApp() {
    this.account = null;
    this.folder = 'INBOX';
    this.messages = [];
    this.backend = 'unknown';
    this.last_fetch = null;
  }

  MailApp.prototype.init = function () {
    var self = this;
    ['menu-btn', 'sidebar-close', 'add-account-btn', 'refresh-btn', 'compose-btn', 'compose-back',
     'send-btn', 'msg-back', 'msg-reply', 'msg-archive', 'msg-delete', 'data-export', 'data-import',
     'data-file', 'data-clear', 'acct-save', 'acct-cancel', 'acct-discover', 'acct-test',
     'acct-password', 'acct-test-result', 'acct-email', 'acct-imap-host', 'acct-imap-port',
     'acct-smtp-host', 'acct-smtp-port'].forEach(function (id) { els[id] = $(id); });
    return global_mailStorage().init().then(function (backend) {
      self.backend = backend;
      self.bind();
      self.renderStorageReport();
      return self.loadAccounts();
    }).then(function (accounts) {
      if (!accounts.length) { self.showSetup(); return; }
      self.account = accounts[0];
      return self.loadMessages().then(function () { self.renderTransport(); });
    }).catch(function (e) {
      // A broken store must be visible, not silent.
      var list = $('message-list');
      if (list) {
        list.innerHTML = '<div class="empty-state"><div class="empty-icon">⚠️</div>' +
          '<h3>Local mail store unavailable</h3><p>' + escapeHtml(String(e && e.message || e)) +
          '</p><p class="hint">The list below is empty because nothing could be read — not because the inbox is empty.</p></div>';
      }
    });
  };

  function global_mailStorage() { return window.mailStorage; }

  MailApp.prototype.bind = function () {
    var self = this;
    els['menu-btn'].addEventListener('click', function () { $('sidebar').classList.toggle('open'); });
    els['sidebar-close'].addEventListener('click', function () { $('sidebar').classList.remove('open'); });
    els['refresh-btn'].addEventListener('click', function () { self.loadMessages(true); });
    els['compose-btn'].addEventListener('click', function () { self.openCompose(); });
    els['compose-back'].addEventListener('click', function () { $('compose-view').classList.add('hidden'); });
    els['send-btn'].addEventListener('click', function () { self.send(); });
    els['msg-back'].addEventListener('click', function () { $('message-view').classList.add('hidden'); });
    els['add-account-btn'].addEventListener('click', function () { $('account-form').classList.remove('hidden'); });
    els['acct-cancel'].addEventListener('click', function () { $('account-form').classList.add('hidden'); });
    els['acct-save'].addEventListener('click', function () { self.saveAccount(); });
    els['acct-discover'].addEventListener('click', function () { self.discoverAccount(); });
    els['acct-test'].addEventListener('click', function () { self.testAccountConnection(); });
    document.querySelectorAll('.folder').forEach(function (btn) {
      btn.addEventListener('click', function () {
        self.folder = btn.dataset.folder;
        document.querySelectorAll('.folder').forEach(function (b) { b.classList.remove('active'); });
        btn.classList.add('active');
        self.loadMessages();
      });
    });
    els['data-export'].addEventListener('click', function () { self.exportData(); });
    els['data-import'].addEventListener('click', function () { els['data-file'].click(); });
    els['data-file'].addEventListener('change', function (ev) { self.importData(ev.target.files[0]); });
    els['data-clear'].addEventListener('click', function () {
      if (window.confirm('Delete every locally stored message and account? Mail already delivered elsewhere is not affected.')) {
        window.mailStorage.clearAll().then(function () {
          self.account = null; self.messages = [];
          self.renderStorageReport();
          self.showSetup();
          self.toast('Local mail deleted');
        });
      }
    });
  };

  MailApp.prototype.renderStorageReport = function () {
    var backend = window.mailStorage.backend;
    var why = window.mailStorage.fallback_reason ? ' (' + window.mailStorage.fallback_reason + ')' : '';
    var label = backend === 'indexeddb' ? 'IndexedDB (durable, per-origin)'
              : backend === 'localStorage' ? 'localStorage fallback' + why
              : 'memory only — this session will not survive a reload' + why;
    els['storage-report'].textContent = 'Local store: ' + label;
    els['storage-report'].classList.toggle('warn', backend !== 'indexeddb');
  };

  MailApp.prototype.renderTransport = function () {
    var d = window.mailTransport.describe();
    var banner = $('transport-banner');
    banner.textContent = 'Transport: ' + d.state.toUpperCase() + ' — ' + d.detail +
      ' Credentials: ' + d.credentials + '.';
    banner.classList.toggle('offline', d.state !== 'bridge');
  };

  MailApp.prototype.loadAccounts = function () {
    var self = this;
    return window.mailStorage.getAccounts().then(function (accounts) {
      var list = $('account-list');
      list.innerHTML = accounts.length ? '' :
        '<p class="hint">No account configured. Mail stays local: you can still read imported or queued messages.</p>';
      accounts.forEach(function (a) {
        var row = document.createElement('button');
        row.className = 'account-item' + (self.account && self.account.id === a.id ? ' active' : '');
        row.textContent = a.email;
        row.addEventListener('click', function () {
          self.account = a;
          window.mailTransport.state = 'unconfigured';
          self.loadMessages().then(function () { self.renderTransport(); });
          $('sidebar').classList.remove('open');
        });
        list.appendChild(row);
      });
      var unassigned = document.createElement('button');
      unassigned.className = 'account-item' + (!self.account ? ' active' : '');
      unassigned.textContent = 'Local mail (no account)';
      unassigned.addEventListener('click', function () {
        self.account = null;
        self.loadMessages().then(function () { self.renderTransport(); });
      });
      list.appendChild(unassigned);
      return accounts;
    });
  };

  MailApp.prototype.bridgeCall = function (verb, params) {
    var b = window.NuxelBridge;
    if (b && typeof b.call === 'function') return b.call('mail', verb, params);
    return Promise.resolve({ success: false, offline: true, error: 'bridge unavailable' });
  };

  MailApp.prototype.discoverAccount = function () {
    var self = this;
    var email = els['acct-email'].value.trim();
    this.bridgeCall('discover', { email: email }).then(function (res) {
      if (res && res.found && res.provider) {
        var p = res.provider;
        if (!els['acct-imap-host'].value) { els['acct-imap-host'].value = p.incoming.host; els['acct-imap-port'].value = p.incoming.port; }
        if (!els['acct-smtp-host'].value) { els['acct-smtp-host'].value = p.outgoing.host; els['acct-smtp-port'].value = p.outgoing.port; }
        els['acct-test-result'].textContent = p.note || ('Discovered endpoints for ' + res.domain + '.');
      } else {
        els['acct-test-result'].textContent = (res && res.detail) || 'No official autodiscover entry; enter hosts manually.';
      }
    });
  };

  MailApp.prototype.testAccountConnection = function () {
    var self = this;
    var email = els['acct-email'].value.trim();
    if (!email) { els['acct-test-result'].textContent = 'Enter an email address first.'; return; }
    els['acct-test-result'].textContent = 'Testing connection…';
    this.bridgeCall('test-connection', {
      account: email,
      password: els['acct-password'].value
    }).then(function (res) {
      if (res && res.success === true) {
        els['acct-test-result'].textContent = 'Connection test passed (incoming and outgoing).';
      } else {
        els['acct-test-result'].textContent = 'Test failed at ' + ((res && res.stage) || 'unknown') +
          ' stage: ' + ((res && res.error) || 'unknown error');
      }
    });
  };

  MailApp.prototype.saveAccount = function () {
    var self = this;
    var email = $('acct-email').value.trim();
    var err = $('acct-error');
    err.classList.add('hidden');
    if (!email) { err.textContent = 'An email address is required.'; err.classList.remove('hidden'); return; }
    window.mailStorage.addAccount({
      email: email,
      imap_host: $('acct-imap-host').value.trim(),
      imap_port: $('acct-imap-port').value,
      smtp_host: $('acct-smtp-host').value.trim(),
      smtp_port: $('acct-smtp-port').value,
      use_tls: $('acct-tls').checked
    }).then(function (account) {
      // Mirror the account CONFIG (never a password) to the bridge store so the
      // transport owner can resolve it for connection tests and fetch/send.
      self.bridgeCall('account-save', {
        account: {
          id: account.id, email: account.email, name: account.name,
          imap_host: account.imap_host, imap_port: account.imap_port,
          smtp_host: account.smtp_host, smtp_port: account.smtp_port, tls: account.use_tls
        }
      }).catch(function () { /* local account still usable */ });
      $('account-form').classList.add('hidden');
      self.account = account;
      window.mailTransport.state = 'unconfigured';
      return self.loadAccounts().then(function () { return self.loadMessages(); });
    }).then(function () {
      self.toast('Account stored locally (no credentials kept)');
      self.renderTransport();
    }).catch(function (e) {
      err.textContent = String(e && e.message || e);
      err.classList.remove('hidden');
    });
  };

  MailApp.prototype.loadMessages = function (fromTransport) {
    var self = this;
    var list = $('message-list');
    var local;
    return window.mailStorage.getMessages(self.account ? self.account.id : null, self.folder)
      .then(function (rows) {
        local = rows;
        if (!fromTransport || !self.account) return { state: self.account ? 'local' : 'unconfigured', messages: local };
        return window.mailTransport.fetch(self.account, self.folder, local);
      })
      .then(function (res) {
        self.last_fetch = res.state;
        if (res.state === 'bridge' && self.account) {
          var incoming = res.messages.map(function (m) {
            return Object.assign({}, m, { account_id: self.account.id, folder: self.folder, delivery: 'received' });
          });
          return window.mailStorage.saveMessages(incoming).then(function () {
            return window.mailStorage.getMessages(self.account.id, self.folder);
          });
        }
        return res.messages;
      })
      .then(function (rows) {
        self.messages = rows.filter(function (m) { return !m.account_id || !self.account || m.account_id === self.account.id; });
        self.renderList();
        self.renderCounts();
        self.renderTransport();
      })
      .catch(function (e) {
        list.innerHTML = '<div class="empty-state"><div class="empty-icon">⚠️</div><h3>Could not read local mail</h3><p>' +
          escapeHtml(String(e && e.message || e)) + '</p></div>';
      });
  };

  MailApp.prototype.renderCounts = function () {
    var self = this;
    return window.mailStorage.counts().then(function (c) {
      FOLDERS.forEach(function (f) {
        var el = $('count-' + f);
        if (el) el.textContent = String((c.by_folder && c.by_folder[f]) || 0);
      });
      var title = $('mail-title');
      if (title) {
        var names = { INBOX: 'Inbox', OUTBOX: 'Outbox (not sent)', SENT: 'Sent', ARCHIVE: 'Archive' };
        title.textContent = names[self.folder] + (self.folder === 'INBOX' && c.unread ? ' · ' + c.unread + ' unread' : '');
      }
    });
  };

  MailApp.prototype.renderList = function () {
    var self = this;
    var list = $('message-list');
    if (!this.messages.length) {
      var empty = this.folder === 'OUTBOX'
        ? 'Outbox is empty. A message that the transport cannot send is stored here and marked not sent.'
        : this.folder === 'SENT'
          ? 'Nothing has been sent yet. Only transport-confirmed sends appear here.'
          : 'No messages in this folder. Nothing is generated to fill the screen.';
      list.innerHTML = '<div class="empty-state"><div class="empty-icon">📨</div><h3>Empty</h3><p>' +
        escapeHtml(empty) + '</p></div>';
      return;
    }
    list.innerHTML = '';
    this.messages.forEach(function (msg) {
      var item = document.createElement('div');
      item.className = 'msg-item' + (msg.read ? '' : ' unread');
      var badge = msg.delivery === 'sent' ? '<span class="delivery sent">sent</span>'
                : msg.delivery === 'queued' ? '<span class="delivery queued">queued — not sent</span>'
                : msg.delivery === 'imported' ? '<span class="delivery imported">imported</span>'
                : msg.delivery === 'received' ? '<span class="delivery received">received</span>'
                : '<span class="delivery local">local</span>';
      item.innerHTML = '<div class="msg-avatar" style="background:' + colorOf(msg.from || msg.to) + '">' +
        escapeHtml(String(msg.from || msg.to || '?').charAt(0).toUpperCase()) + '</div>' +
        '<div class="msg-info"><div class="msg-from">' + escapeHtml(msg.from || (msg.to ? 'To ' + String(msg.to) : 'Unknown')) + badge + '</div>' +
        '<div class="msg-subject">' + escapeHtml(msg.subject || '(no subject)') + '</div>' +
        '<div class="msg-preview">' + escapeHtml(String(msg.body || '').slice(0, 80)) + '</div></div>' +
        '<div class="msg-time">' + formatTime(msg.timestamp) + '</div>';
      item.addEventListener('click', function () { self.openMessage(msg.id); });
      list.appendChild(item);
    });
  };

  MailApp.prototype.openMessage = function (id) {
    var self = this;
    var msg = this.messages.filter(function (m) { return m.id === id; })[0];
    if (!msg) return;
    window.mailStorage.markAsRead(id).catch(function () { /* read flag is cosmetic */ });
    msg.read = true;
    this.renderList();
    var view = $('message-view');
    view.classList.remove('hidden');
    var delivery = msg.delivery === 'queued'
      ? '<p class="delivery-note">This message was <b>not sent</b>: it is stored locally in Outbox.</p>' : '';
    $('msg-content').innerHTML = '<div class="msg-full-from">' + escapeHtml(msg.from || '(local)') + '</div>' +
      '<div class="msg-full-subject">' + escapeHtml(msg.subject || '(no subject)') + '</div>' +
      '<div class="msg-full-date">' + escapeHtml(new Date(msg.timestamp).toLocaleString()) + '</div>' + delivery +
      '<div class="msg-full-body">' + escapeHtml(msg.body || '') + '</div>';
    $('msg-back').onclick = function () { view.classList.add('hidden'); };
    $('msg-delete').onclick = function () {
      window.mailStorage.deleteMessage(id).then(function () {
        view.classList.add('hidden');
        return self.loadMessages();
      }).then(function () { self.toast('Message deleted locally'); });
    };
    $('msg-archive').onclick = function () {
      window.mailStorage.moveMessage(id, 'ARCHIVE').then(function () {
        view.classList.add('hidden');
        return self.loadMessages();
      }).then(function () { self.toast('Moved to Archive'); });
    };
    $('msg-reply').onclick = function () {
      view.classList.add('hidden');
      self.openCompose(msg.from || '', 'Re: ' + (msg.subject || ''), '\n\n--- ' + (msg.subject || '') + ' ---\n' +
        String(msg.body || '').slice(0, 400));
    };
  };

  MailApp.prototype.openCompose = function (to, subject, body) {
    $('compose-view').classList.remove('hidden');
    $('compose-to').value = to || '';
    $('compose-subject').value = subject || '';
    $('compose-body').value = body || '';
    var t = window.mailTransport.describe();
    $('compose-status').textContent = t.state === 'bridge'
      ? 'Transport READY: the bridge answered a mail verb, so Send attempts a real submission.'
      : 'Transport ' + t.state.toUpperCase() + ': a send that the transport cannot complete is written to Outbox and marked "not sent".';
  };

  MailApp.prototype.send = function () {
    var self = this;
    var to = $('compose-to').value.trim();
    var subject = $('compose-subject').value.trim();
    var body = $('compose-body').value;
    if (!to) { this.toast('A recipient is required'); return; }
    var draft = {
      account_id: this.account ? this.account.id : null,
      folder: 'OUTBOX',
      from: this.account ? this.account.email : '(local draft)',
      to: to.split(',').map(function (s) { return s.trim(); }).filter(Boolean),
      subject: subject,
      body: body,
      timestamp: new Date().toISOString(),
      read: true,
      direction: 'sent',
      delivery: 'queued'
    };
    var doSend = this.account
      ? window.mailTransport.send(this.account, draft)
      : Promise.resolve({ state: 'queued', reason: 'no account is configured, so there is no transport to send with' });

    doSend.then(function (res) {
      if (res.state === 'sent') {
        draft.delivery = 'sent';
        draft.folder = 'SENT';
        return window.mailStorage.saveMessages([draft]).then(function () {
          $('compose-view').classList.add('hidden');
          self.folder = 'SENT';
          return self.loadMessages();
        }).then(function () { self.toast('Sent (transport-confirmed)'); });
      }
      draft.delivery = 'queued';
      draft.queue_reason = res.reason || 'transport unavailable';
      return window.mailStorage.saveMessages([draft]).then(function () {
        $('compose-view').classList.add('hidden');
        self.folder = 'OUTBOX';
        document.querySelectorAll('.folder').forEach(function (b) { b.classList.toggle('active', b.dataset.folder === 'OUTBOX'); });
        return self.loadMessages();
      }).then(function () { self.toast('Saved to Outbox — NOT sent: ' + (res.reason || 'transport unavailable')); });
    }).catch(function (e) {
      self.toast('Could not store the message: ' + (e && e.message || e));
    });
  };

  MailApp.prototype.exportData = function () {
    window.mailStorage.exportAll().then(function (doc) {
      var blob = new Blob([JSON.stringify(doc, null, 2)], { type: 'application/json' });
      var url = URL.createObjectURL(blob);
      var a = document.createElement('a');
      a.href = url;
      a.download = 'nuxel-mail-' + new Date().toISOString().slice(0, 10) + '.json';
      document.body.appendChild(a);
      a.click();
      a.remove();
      setTimeout(function () { URL.revokeObjectURL(url); }, 1000);
      window.__nuxelMailLastExport = doc;
      return null;
    });
  };

  MailApp.prototype.importData = function (file) {
    var self = this;
    if (!file) return;
    var reader = new FileReader();
    reader.onload = function () {
      var doc;
      try { doc = JSON.parse(String(reader.result)); }
      catch (e) { self.toast('Import failed: not valid JSON'); return; }
      window.mailStorage.importAll(doc).then(function (summary) {
        self.toast('Imported ' + summary.messages_imported + ' message(s), ' + summary.accounts_added +
          ' account(s), skipped ' + summary.accounts_skipped);
        return self.loadAccounts();
      }).then(function () { return self.loadMessages(); })
        .catch(function (e) { self.toast('Import failed: ' + (e && e.message || e)); });
    };
    reader.onerror = function () { self.toast('Import failed: the file could not be read'); };
    reader.readAsText(file);
  };

  MailApp.prototype.showSetup = function () {
    var self = this;
    $('message-list').innerHTML = '<div class="empty-state"><div class="empty-icon">📧</div>' +
      '<h3>Nuxel Mail</h3><p>Local-first mail: messages you import or queue live in this app\'s store. ' +
      'Add an account to try the configured mail transport — this build stores no password, so a transport ' +
      'that needs one will say NEEDS_CREDENTIALS rather than pretend to log in.</p>' +
      '<div class="row-actions"><button id="setup-account" class="btn-primary">Add account</button>' +
      '<button id="setup-import" class="btn-ghost">Import JSON</button></div></div>';
    $('setup-account').addEventListener('click', function () { $('account-form').classList.remove('hidden'); });
    $('setup-import').addEventListener('click', function () { $('data-file').click(); });
    void self;
  };

  MailApp.prototype.toast = function (msg) {
    var existing = document.querySelector('.toast');
    if (existing) existing.remove();
    var toast = document.createElement('div');
    toast.className = 'toast';
    toast.textContent = msg;
    document.body.appendChild(toast);
    setTimeout(function () { toast.remove(); }, 4000);
  };

  /* ---------- helpers ---------- */
  function escapeHtml(str) {
    var div = document.createElement('div');
    div.textContent = str === undefined || str === null ? '' : String(str);
    return div.innerHTML;
  }
  function colorOf(str) {
    var colors = ['#FF9800', '#E91E63', '#9C27B0', '#2196F3', '#4CAF50', '#F44336', '#607D8B', '#795548'];
    var s = String(str || '');
    var hash = 0;
    for (var i = 0; i < s.length; i++) hash = s.charCodeAt(i) + ((hash << 5) - hash);
    return colors[Math.abs(hash) % colors.length];
  }
  function formatTime(ts) {
    if (!ts) return '';
    var date = new Date(ts);
    if (isNaN(date.getTime())) return '';
    var diff = Date.now() - date.getTime();
    if (diff < 86400000) return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    if (diff < 604800000) return date.toLocaleDateString([], { weekday: 'short' });
    return date.toLocaleDateString([], { month: 'short', day: 'numeric' });
  }

  window.MailApp = MailApp;
  window.mailApp = new MailApp();
  document.addEventListener('DOMContentLoaded', function () { window.mailApp.init(); });
  // headless smoke-test hook (documented app API; used by tools/s10plus/a33/tests/test-core-apps.py)
  window.nuxelMail = {
    app: function () { return window.mailApp; },
    schema: function () { return window.nuxelMailSchema; },
    transport: function () { return window.mailTransport.describe(); },
    backend: function () { return window.mailStorage.backend; }
  };
})();
