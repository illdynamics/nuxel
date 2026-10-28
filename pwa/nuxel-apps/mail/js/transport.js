// Nuxel Mail — mail transport (js/transport.js)
//
// WHAT THIS FILE IS NOT: it is not an IMAP or SMTP implementation and it does
// not pretend to be one. A PWA cannot open a raw IMAP socket, and no mail
// service is proven on this device in this run, so the only honest transports
// are:
//
//   'bridge'      the nuxel-bridge exposes mail verbs (imap-list / smtp-send)
//                 and answered them; results come from the host.
//   'unavailable' the bridge is absent, refused the verb, or reported no mail
//                 service. Nothing is fabricated: fetched mail stays as it was
//                 and a send becomes a QUEUED message.
//   'unconfigured' no account has been added yet.
//
// Every method returns the transport state it actually reached, so the UI can
// label it. A queued message is never labelled "sent".
(function (global) {
  'use strict';

  var APP_ID = 'org.nuxel.Mail';

  function bridge() {
    var b = global.NuxelBridge;
    if (b && typeof b.call === 'function') return b;
    try {
      if (global.parent && global.parent !== global && global.parent.NuxelBridge) return global.parent.NuxelBridge;
    } catch (e) { /* cross-origin frame */ }
    return null;
  }

  function Transport() {
    this.state = 'unconfigured';
    this.last_error = null;
    this.last_verb = null;
    this.idle_timers = {};
  }

  Transport.prototype.describe = function () {
    var b = bridge();
    return {
      state: this.state,
      bridge_present: !!b,
      credentials: 'not-stored',
      last_verb: this.last_verb,
      last_error: this.last_error,
      detail: this.state === 'bridge'
        ? 'The Nuxel bridge answered the mail verbs; fetched and sent items are real.'
        : b
          ? 'A bridge is present but it did not answer a mail verb: sends are queued, nothing is faked.'
          : 'No bridge in this context (desktop/VM/pre-host): the store is local-only; sends are queued.'
    };
  };

  Transport.prototype._call = function (verb, params, fallback) {
    var b = bridge();
    var self = this;
    if (!b) { this.last_error = 'no bridge'; return Promise.resolve(fallback); }
    try {
      return Promise.resolve(b.call('mail', verb, params)).then(function (res) {
        if (!res || res.success === false) throw new Error((res && res.error) || 'bridge refused ' + verb);
        return res;
      }).catch(function () {
        self.last_error = self.last_error || ('bridge did not complete ' + verb);
        return fallback;
      });
    } catch (e) {
      this.last_error = String(e && e.message || e);
      return Promise.resolve(fallback);
    }
  };

  // Fetch messages for a folder. Never invents messages: when the transport is
  // unavailable, the caller's local store contents are returned unchanged.
  Transport.prototype.fetch = function (account, folder, localMessages, password) {
    var self = this;
    this.last_verb = 'imap-list';
    var verb = account.incoming_type === 'pop3' ? 'pop3-list' : 'imap-list';
    return this._call(verb, { app_id: APP_ID, account: account.id, folder: folder, password: password || '' }, null)
      .then(function (res) {
        if (res && Array.isArray(res.messages)) {
          self.state = 'bridge';
          self.last_error = null;
          return {
            state: 'bridge',
            messages: res.messages.map(function (m) {
              return Object.assign({}, m, {
                account_id: account.id,
                folder: m.folder || folder,
                delivery: 'received'
              });
            })
          };
        }
        self.state = 'unavailable';
        return { state: 'unavailable', messages: localMessages, reason: self.last_error };
      });
  };

  // Send. The result state is exactly one of:
  //   sent   — the bridge confirmed the SMTP send (message_id present)
  //   queued — stored in OUTBOX, NOT sent (the reason travels with it)
  Transport.prototype.send = function (account, msg, password) {
    var self = this;
    this.last_verb = 'smtp-send';
    var payload = {
      app_id: APP_ID,
      account: account.id,
      to: Array.isArray(msg.to) ? msg.to : [msg.to],
      subject: msg.subject,
      body: msg.body,
      password: password || ''
    };
    return this._call('smtp-send', payload, null).then(function (res) {
      if (res && res.success !== false && (res.accepted || res.message_id)) {
        self.state = 'bridge';
        self.last_error = null;
        return { state: 'sent', message_id: res.message_id || null };
      }
      self.state = 'unavailable';
      self.last_error = self.last_error || 'the mail transport is unavailable in this context';
      return { state: 'queued', reason: self.last_error };
    });
  };

  // IDLE/push. The bridge may support a poll verb; otherwise nothing happens and
  // "push" is never claimed.
  Transport.prototype.startIdle = function (account, onNew) {
    var self = this;
    if (this.idle_timers[account.id]) return;
    if (!bridge()) { this.state = this.state === 'bridge' ? 'unavailable' : this.state; return; }
    this.idle_timers[account.id] = setInterval(function () {
      self._call('imap-idle-poll', { app_id: APP_ID, account: account.id }, null).then(function (res) {
        if (res && Array.isArray(res.messages) && res.messages.length) {
          self.state = 'bridge';
          onNew(res.messages);
        }
      });
    }, 60000);
  };

  Transport.prototype.stopIdle = function (accountId) {
    if (this.idle_timers[accountId]) {
      clearInterval(this.idle_timers[accountId]);
      delete this.idle_timers[accountId];
    }
  };

  global.MailTransport = Transport;
  global.mailTransport = new Transport();
})(typeof window !== 'undefined' ? window : this);
