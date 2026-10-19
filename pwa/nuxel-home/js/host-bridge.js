// Nuxel Host Bridge (A32)
//
// The UTM build talks to nuxel-bridge/nuxel-http-bridge.  The handset has
// neither, so the process that hosts this page (nuxel-pwa-host) serves the same
// logical operations over WebKit's script-message channel as window.NuxelHost.
//
// Everything here is additive: if no host is present (VM, desktop, plain
// browser) every call resolves to {ok:false, offline:true} and the caller falls
// back to its own storage.  No launcher feature depends on the host being there.
//
// API (all async, all bounded):
//   NuxelHost.available            -> boolean
//   NuxelHost.configGet(name)      -> {ok, text}
//   NuxelHost.configSet(name, text)-> {ok}
//   NuxelHost.statusRead(name)     -> {ok, text}
//   NuxelHost.action(action)       -> {ok}    screen-off|screen-on|screen-toggle|
//                                             home|search|settings|open-terminal|
//                                             volume-up|volume-down|volume-mute|
//                                             haptics-tap|haptics-navigation|
//                                             haptics-switch|haptics-long
//   NuxelHost.termInput(data)      -> {ok}
//   NuxelHost.termOpen() / termClose()
//   NuxelHost.onEvent(cb)          -> subscription to host-pushed events
(function (global) {
  'use strict';

  var pending = {};
  var nextId = 1;
  var eventHandlers = [];
  var hostPresent = !!(global.webkit && global.webkit.messageHandlers &&
                       global.webkit.messageHandlers.nuxelHost);

  // The native side calls this back with `window.__nuxelHostReply(rid, ok, payload)`.
  global.__nuxelHostReply = function (rid, ok, payload) {
    var p = pending[rid];
    if (!p) return;
    delete pending[rid];
    var res = payload && typeof payload === 'object' ? payload : {};
    res.ok = !!ok;
    p.resolve(res);
  };

  // Host-pushed events (OSD/volume/display) use the same delivery channel.
  function deliverEvent(name, data) {
    eventHandlers.forEach(function (cb) {
      try { cb(name, data); } catch (e) { /* a listener must never break the launcher */ }
    });
  }
  global.__nuxelHostEvent = deliverEvent;

  function call(method, params, timeoutMs) {
    return new Promise(function (resolve) {
      if (!hostPresent) { resolve({ ok: false, offline: true }); return; }
      var rid = String(nextId++);
      var msg = { id: rid, method: method };
      for (var k in params) if (Object.prototype.hasOwnProperty.call(params, k)) msg[k] = params[k];
      var timer = setTimeout(function () {
        if (pending[rid]) { delete pending[rid]; resolve({ ok: false, timeout: true }); }
      }, timeoutMs || 6000);
      pending[rid] = { resolve: function (r) { clearTimeout(timer); resolve(r); } };
      try {
        global.webkit.messageHandlers.nuxelHost.postMessage(JSON.stringify(msg));
      } catch (e) {
        clearTimeout(timer); delete pending[rid]; resolve({ ok: false, error: String(e) });
      }
    });
  }

  // In-page relay for SAME-ORIGIN iframes (the Settings and Terminal PWAs run
  // inside the launcher's .pwa-frame).  An iframe posts
  //   parent.postMessage({nuxel: 'call', id, method, params}, '*')
  // and receives {nuxel:'reply', id, res}.
  global.addEventListener('message', function (ev) {
    if (!ev.data || ev.data.nuxel !== 'call' || !ev.source) return;
    call(ev.data.method, ev.data.params || {}).then(function (res) {
      try { ev.source.postMessage({ nuxel: 'reply', id: ev.data.id, res: res }, '*'); } catch (e) {}
    });
  });

  function iframeCall(method, params) {
    return new Promise(function (resolve) {
      if (global.parent === global) { call(method, params).then(resolve); return; }
      var id = 'if' + Math.random().toString(36).slice(2);
      function onMsg(ev) {
        if (!ev.data || ev.data.nuxel !== 'reply' || ev.data.id !== id) return;
        global.removeEventListener('message', onMsg);
        resolve(ev.data.res || { ok: false });
      }
      global.addEventListener('message', onMsg);
      try { global.parent.postMessage({ nuxel: 'call', id: id, method: method, params: params || {} }, '*'); }
      catch (e) { resolve({ ok: false, error: String(e) }); }
      setTimeout(function () { global.removeEventListener('message', onMsg); }, 8000);
    });
  }

  var NuxelHost = {
    available: hostPresent,
    inIframe: global.parent !== global,
    call: function (method, params) {
      return (global.parent !== global) ? iframeCall(method, params) : call(method, params);
    },
    configGet: function (name) { return this.call('config.get', { name: name }); },
    configSet: function (name, text) { return this.call('config.set', { name: name, text: text }); },
    statusRead: function (name) { return this.call('status.read', { name: name }); },
    action: function (action) { return this.call('system.action', { action: action }); },
    termInput: function (data) { return this.call('term.input', { data: data }); },
    termOpen: function () { return this.call('term.open', {}); },
    termClose: function () { return this.call('term.close', {}); },
    onEvent: function (cb) { eventHandlers.push(cb); },
    offEvent: function (cb) { eventHandlers = eventHandlers.filter(function (h) { return h !== cb; }); }
  };

  global.NuxelHost = NuxelHost;

  /* Evidence marker: the native terminal window is a TOP-LEVEL WebKit view and
   * therefore must load this file itself.  Without this line, a page that forgot
   * the include looked identical to a host outage (the Close button and every
   * on-screen key silently did nothing).  The host's nuxelDiag channel is only
   * a logger; it never synthesises input. */
  try {
    if (global.webkit && global.webkit.messageHandlers && global.webkit.messageHandlers.nuxelDiag) {
      global.webkit.messageHandlers.nuxelDiag.postMessage(
        'HOSTBRIDGE_READY available=' + NuxelHost.available + ' inIframe=' + NuxelHost.inIframe);
    }
  } catch (e) { /* diagnostics must never break the bridge */ }
})(window);
