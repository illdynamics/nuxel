/* Nuxel Security Lock (PWNAGE-45000)
 *
 * Credential verification lives in the root Bridge (security_provider.py), not
 * here.  This file only collects the PIN/pattern and renders the prompt; the
 * authoritative locked/unlocked state and rate limiting are server-side.
 */
(function (root) {
  'use strict';
  /* The global this module publishes into is the REAL document's window.  A
     test harness (or a previous realm) can pass a different object as the
     IIFE argument; the live page must always answer on its own window. */
  var global = root;
  try {
    if (root && root.document && root.document.defaultView) global = root.document.defaultView;
    else if (typeof window !== 'undefined' && window.document) global = window;
  } catch (e) { /* keep the passed object */ }
  var VERSION = 'a84';
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

  /* The legacy text-input sheet ("Enter PIN", "Enter pattern", "PIN fallback")
     is GONE for good (A82).  Every credential is entered on the lock screen
     surface: pattern/PIN on the glass, the Vault master password in the
     Vault's own password field.  A second prompt overlaying the lock screen
     only ever asked the owner twice.  promptSecret is kept as an API name that
     always resolves to "no prompt": callers fall back to the credential
     surface (or treat the attempt as cancelled). */
  function promptSecret() { return Promise.resolve(null); }

  async function status() {
    var st = await call('security', 'status', {});
    if (st && st.success !== false) cache = st;
    return st;
  }

  /* A80: the authoritative credential surface is the lockscreen overlay
     (#lockscreen-auth: pattern matrix / keypad / fingerprint).  It verifies
     against the bridge itself before it asks Home to complete the unlock.

     This legacy prompt must therefore NEVER open while that surface is up:
     the old code re-prompted here after the overlay had already accepted a
     PIN, which produced a second "Enter PIN" sheet ("At least 6 digits")
     on top of the just-unlocked phone.  When the surface owns the credential,
     verifyUnlock just reports the bridge truth: the caller reconciles. */
  function overlayOwnsCredential() {
    try {
      var box = document.getElementById('lockscreen-auth');
      if (!box || box.hidden) return false;
      var pad = document.getElementById('lockscreen-pinpad');
      var pat = document.getElementById('lockscreen-pattern');
      var fp = document.getElementById('lockscreen-fingerprint');
      return !!((pad && !pad.hidden) || (pat && !pat.hidden) || (fp && !fp.hidden));
    } catch (e) { return false; }
  }

  /* verifyUnlock is the HOST/NAV gate, not a credential collector.
   *
   * Every credential is entered on the lock screen surface (pattern matrix,
   * keypad or fingerprint) and verified there against the root bridge.  This
   * function therefore only reports the bridge's authoritative state:
   *
   *   unlocked -> {ok:true}   let the host/nav transition proceed
   *   locked   -> {ok:false}  the overlay owns the unlock; the caller keeps
   *                           the session locked (it will re-render the
   *                           credential surface, never a second prompt)
   *
   * It NEVER opens a prompt of its own.  The old implementation opened a
   * legacy text-input sheet here ("Enter PIN", "At least 6 digits"), which is
   * exactly the unexplained second PIN request the owner saw after a correct
   * unlock -- the phone was unlocked, then the host's nav gate asked again.
   */
  async function verifyUnlock() {
    var st = await status();
    if (!st || st.success === false) {
      return { ok: false, error: 'lock-provider-unavailable',
        detail: (st && st.error) || 'security provider unavailable' };
    }
    if (st.rate_limit && st.rate_limit.locked_out) {
      return { ok: false, error: 'rate_limited',
        detail: 'Try again in ' + st.rate_limit.remaining_s + ' s' };
    }
    if (st.locked === false) {
      return { ok: true, state: 'UNLOCKED', mode: st.mode, via: 'bridge-authority' };
    }
    return { ok: false, error: 'credential-required-on-lockscreen',
      detail: 'Enter the credential on the lock screen' };
  }

  /* A84: the swipe unlock.  In swipe mode the provider has no verifier, so an
     empty-secret unlock IS the authoritative transition.  It is refused - and
     the session stays locked - if a credential mode is active, so this can
     never bypass a PIN/pattern/fingerprint.  The status read is deliberate: it
     keeps the decision in the provider, not in the gesture handler. */
  async function unlockSwipe() {
    var st = await status();
    if (!st || st.success === false) {
      return { ok: false, error: 'lock-provider-unavailable',
        detail: (st && st.error) || 'security provider unavailable' };
    }
    if (st.mode && st.mode !== 'swipe') {
      return { ok: false, error: 'credential-required-on-lockscreen',
        mode: st.mode, detail: 'Enter the credential on the lock screen' };
    }
    if (st.locked === false) {
      return { ok: true, state: 'UNLOCKED', via: 'swipe-already-unlocked' };
    }
    var res = await call('security', 'unlock', { secret: '' });
    if (!res || res.success !== true || res.unlocked !== true) {
      return { ok: false, error: (res && (res.error || res.detail)) || 'swipe-unlock-refused',
        detail: 'provider refused the swipe unlock' };
    }
    cache = null;
    return { ok: true, state: 'UNLOCKED', via: 'swipe', result: res };
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
    unlockSwipe: unlockSwipe,
    lock: lock,
    setMode: setMode,
    call: call,
    promptSecret: promptSecret
  };
})(typeof window !== 'undefined' ? window : this);
