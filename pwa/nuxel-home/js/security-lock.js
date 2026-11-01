/* Nuxel Security Lock (PWNAGE-45000)
 *
 * Credential verification lives in the root Bridge (security_provider.py), not
 * here.  This file only collects the PIN/pattern and renders the prompt; the
 * authoritative locked/unlocked state and rate limiting are server-side.
 */
(function (global) {
  'use strict';
  var VERSION = 'p45000';
  var cache = null;

  function bridge() {
    if (global.NuxelBridge && global.NuxelBridge.call) return global.NuxelBridge;
    // Home's lowercase wrapper rejects mock fallbacks and carries the session
    // token; prefer it when the shared module has not published yet.
    if (global.bridge && typeof global.bridge.call === 'function') return global.bridge;
    try { if (global.parent && global.parent !== global && global.parent.NuxelBridge) return global.parent.NuxelBridge; } catch (e) {}
    return null;
  }
  async function direct(ns, verb, params) {
    try {
      // The PWA static server (:8000) is not the API.  The root bridge API is
      // loopback :8080; prefer the shared client when it has loaded.
      var res = await fetch('http://127.0.0.1:8080/api/v1/rpc', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ app_id: 'org.nuxel.Home', namespace: ns, verb: verb, params: params || {} })
      });
      if (!res.ok) return { success: false, error: 'HTTP ' + res.status };
      var doc = await res.json();
      return doc && doc.result !== undefined ? doc.result : doc;
    } catch (e) { return { success: false, error: String(e && e.message || e) }; }
  }
  async function call(ns, verb, params) {
    var b = bridge();
    if (b) {
      try { return await b.call(ns, verb, params || {}); } catch (e) { /* fall through */ }
    }
    return direct(ns, verb, params);
  }

  function esc(s) { return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) { return ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'})[c]; }); }

  function ensurePrompt() {
    var el = document.getElementById('nuxel-lock-prompt');
    if (el) return el;
    el = document.createElement('div');
    el.id = 'nuxel-lock-prompt';
    el.hidden = true;
    el.style.cssText = 'position:fixed;inset:0;z-index:700;display:flex;align-items:flex-end;justify-content:center;padding:14px;background:rgba(0,0,0,.55)';
    el.innerHTML = '<div style="width:100%;max-width:340px;background:#0b192d;border:1px solid #3d6b9c;border-radius:18px;padding:16px;color:#eaf4ff">' +
      '<h2 id="nlp-title" style="margin:0 0 6px;font-size:19px">Enter PIN</h2>' +
      '<p id="nlp-hint" style="margin:0 0 10px;font-size:12px;color:#a9c5e4">Unlock this device</p>' +
      '<input id="nlp-secret" inputmode="numeric" autocomplete="off" type="password" style="width:100%;box-sizing:border-box;padding:12px;border-radius:10px;border:1px solid #3d6b9c;background:#081425;color:#fff;font-size:18px">' +
      '<p id="nlp-error" role="alert" style="min-height:16px;margin:8px 0;color:#ff9a9a;font-size:12px"></p>' +
      '<div style="display:flex;gap:8px"><button id="nlp-submit" type="button" style="flex:1;min-height:44px;border:0;border-radius:11px;background:#2f5f96;color:#fff;font-weight:600">Unlock</button>' +
      '<button id="nlp-cancel" type="button" style="min-height:44px;padding:0 14px;border:1px solid #3d6b9c;border-radius:11px;background:transparent;color:#dbeafe">Cancel</button></div>' +
      '<p style="margin:10px 0 0;font-size:11px;color:#7f9cbb">Fingerprint, when supported, always keeps this PIN fallback.</p></div>';
    document.body.appendChild(el);
    return el;
  }

  function promptSecret(status) {
    return new Promise(function (resolve) {
      var el = ensurePrompt();
      var input = document.getElementById('nlp-secret');
      var err = document.getElementById('nlp-error');
      var title = document.getElementById('nlp-title');
      var hint = document.getElementById('nlp-hint');
      var mode = status && status.mode || 'pin';
      if (mode === 'pattern') {
        title.textContent = 'Enter pattern';
        hint.textContent = 'Use dot numbers, e.g. 0-1-2-5-8';
        input.type = 'text'; input.inputMode = 'numeric';
      } else if (mode === 'fingerprint') {
        title.textContent = 'PIN fallback';
        hint.textContent = 'Fingerprint provider unavailable or not ready; enter the PIN fallback';
        input.type = 'password'; input.inputMode = 'numeric';
      } else {
        title.textContent = 'Enter PIN';
        hint.textContent = 'At least 6 digits';
        input.type = 'password'; input.inputMode = 'numeric';
      }
      input.value = ''; err.textContent = '';
      el.hidden = false;
      setTimeout(function () { try { input.focus(); } catch (e) {} }, 30);
      function done(v) {
        el.hidden = true;
        document.getElementById('nlp-submit').onclick = null;
        document.getElementById('nlp-cancel').onclick = null;
        input.onkeydown = null;
        resolve(v);
      }
      document.getElementById('nlp-submit').onclick = function () { done(input.value); };
      document.getElementById('nlp-cancel').onclick = function () { done(null); };
      input.onkeydown = function (ev) { if (ev.key === 'Enter') { ev.preventDefault(); done(input.value); } };
    });
  }

  async function status() {
    var st = await call('security', 'status', {});
    if (st && st.success !== false) cache = st;
    return st;
  }

  async function verifyUnlock() {
    var st = await status();
    if (!st || st.success === false) {
      return { ok: false, error: 'lock-provider-unavailable', detail: (st && st.error) || 'security provider unavailable' };
    }
    if (st.rate_limit && st.rate_limit.locked_out) {
      return { ok: false, error: 'rate_limited', detail: 'Try again in ' + st.rate_limit.remaining_s + ' s' };
    }
    var secret = '';
    if (st.mode !== 'swipe') {
      secret = await promptSecret(st);
      if (secret === null) return { ok: false, error: 'cancelled' };
    }
    var res = await call('security', 'unlock', { secret: secret });
    if (res && res.success === true && res.unlocked === true) {
      cache = null;
      try { document.dispatchEvent(new CustomEvent('nuxel:security-unlocked', { detail: { mode: st.mode } })); } catch (e) {}
      return { ok: true, state: 'UNLOCKED', mode: st.mode };
    }
    var msg = (res && (res.error || res.detail)) || 'invalid credential';
    if (res && res.error === 'rate_limited') msg = 'Too many attempts; wait ' + (res.remaining_s || 30) + ' s';
    return { ok: false, error: 'credential-rejected', detail: msg, remaining_s: res && res.remaining_s };
  }

  async function lock(reason) {
    var res = await call('security', 'lock', { reason: reason || 'manual' });
    cache = null;
    return res;
  }

  async function setMode(mode, secret, opts) {
    var p = Object.assign({ mode: mode, secret: secret || '' }, opts || {});
    return call('security', 'set-mode', p);
  }

  global.NuxelSecurityLock = {
    version: VERSION,
    status: status,
    verifyUnlock: verifyUnlock,
    lock: lock,
    setMode: setMode,
    call: call,
    promptSecret: promptSecret
  };
})(window);
