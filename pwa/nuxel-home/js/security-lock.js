/* Nuxel Security Lock (PWNAGE-45000)
 *
 * Credential verification lives in the root Bridge (security_provider.py), not
 * here.  This file only collects the PIN/pattern and renders the prompt; the
 * authoritative locked/unlocked state and rate limiting are server-side.
 */
(function (global) {
  'use strict';
  var VERSION = 'a85';
  var cache = null;
  /* A84: security RPCs go DIRECTLY to the root bridge, never through the
     shared client.  The shared client's failure path returns FABRICATED mock
     data (`this.mockMode = true`), so any transient miss (a cold token, a
     restarted bridge, a 409) made `/security/status` look like "still locked"
     and the launcher rejected a swipe on a device that was in swipe mode.
     A security answer must always be the host's real answer.
     The pinned X-Nuxel-Bridge-Version header matches what the shared client
     sends, so the host's version gate behaves identically. */
  var RPC_URL = 'http://127.0.0.1:8080/api/v1/rpc';
  var _cachedToken = '';

  function bridgeVersion() {
    if (global.NUXEL_BRIDGE_VERSION) return String(global.NUXEL_BRIDGE_VERSION);
    return '1';
  }

  async function direct(ns, verb, params) {
    try {
      /* Identity is still required after the G0 boundary: Home's app-bound
         session token is fetched from the launcher relay.  The direct fetch is
         kept (no fabricated mock data); only the Authorization header is new. */
      var token = _cachedToken;
      if (!token) {
        try {
          // The Home page is the top frame, so ask the injected launcher
          // relay directly (the app-bound token is delivered as a message).
          token = await global.NuxelBridge._keyringLauncherToken();
          _cachedToken = token || '';
        } catch (e) { token = ''; }
      }
      var headers = { 'Content-Type': 'application/json',
                      'X-Nuxel-Bridge-Version': bridgeVersion() };
      if (token) headers.Authorization = 'Bearer ' + token;
      var res = await fetch(RPC_URL, {
        method: 'POST',
        headers: headers,
        body: JSON.stringify({ app_id: 'org.nuxel.Home', namespace: ns, verb: verb,
                               params: params || {} })
      });
      var doc = null;
      try { doc = await res.json(); } catch (e) { doc = null; }
      if (!res.ok) {
        if (doc && doc.result !== undefined) return doc.result;
        return { success: false, error: 'HTTP ' + res.status,
                 detail: (doc && (doc.detail || doc.error)) || null };
      }
      return doc && doc.result !== undefined ? doc.result : doc;
    } catch (e) { return { success: false, error: String(e && e.message || e) }; }
  }
  function call(ns, verb, params) { return direct(ns, verb, params); }

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
   *
   * A85: a lockhead swipe ON A SWIPE-MODE LOCK is itself the unlock.  The
   * provider is still `locked:true` at the moment this gate runs (the lock
   * overlay is up and nothing has released it yet), so demanding
   * `locked === false` FIRST dead-locked every swipe-mode phone:
   *
   *   gesture -> verify -> provider says locked -> rejected -> still locked
   *
   * The provider's own `security/unlock` verb is the atomic release for a
   * swipe lock -- it re-reads the stored mode server-side and only clears the
   * lock when that mode is `swipe`; on a credentialed mode it answers
   * `invalid_credential` and the overlay keeps the keypad/pattern surface.
   * So: status first (honest, authoritative), then for `swipe`/`unlock` (and
   * only for `opts.direct`, i.e. the direct-swipe path) ask for that release.
   * A credentialed mode is never released here; it goes to the credential
   * surface exactly as before.
   */
  async function verifyUnlock(opts) {
    opts = opts || {};
    var st = await status();
    /* Observation only: the exact status object the unlock gate decided on. */
    try {
      var diag = global.webkit && global.webkit.messageHandlers && global.webkit.messageHandlers.nuxelDiag;
      if (diag) diag.postMessage('SECLOCK[a85] verify status=' + JSON.stringify({
        success: (st && st.success), locked: (st && st.locked), mode: (st && st.mode),
        reason: (st && st.reason), error: (st && st.error), detail: (st && st.detail),
        provider: (st && st.source),
      }));
    } catch (e) { /* observation only */ }
    if (!st || st.success === false) {
      return { ok: false, error: 'lock-provider-unavailable',
        detail: (st && st.error) || 'security provider unavailable' };
    }
    /* A84: a real status ALWAYS carries a boolean `locked`.  An object
       without it is not an answer (a fabricated/mock reply or a refusal);
       treating it as "locked" is what rejected every swipe on a swipe-mode
       device.  Fail closed, but report the true reason. */
    if (typeof st.locked !== 'boolean') {
      return { ok: false, error: 'lock-provider-unavailable',
        detail: 'security status did not report a lock state' };
    }
    if (st.rate_limit && st.rate_limit.locked_out) {
      return { ok: false, error: 'rate_limited',
        detail: 'Try again in ' + st.rate_limit.remaining_s + ' s' };
    }
    if (st.locked === false) {
      return { ok: true, state: 'UNLOCKED', mode: st.mode, via: 'bridge-authority' };
    }
    /* A85 direct swipe on a swipe-mode lock: release it through the provider's
       own verb.  Only the direct path (opts.direct) may release; the locked
       state is re-read SERVER-SIDE and a credentialed mode is never cleared. */
    var mode = String(st.mode || '');
    var swipeLock = (mode === 'swipe' || mode === 'unlock');
    if (opts.direct === true && swipeLock) {
      var rel = await call('security', 'unlock', { secret: '' });
      var ok = !!(rel && rel.success !== false && rel.unlocked === true && rel.locked === false);
      try {
        var d = global.webkit && global.webkit.messageHandlers && global.webkit.messageHandlers.nuxelDiag;
        if (d) d.postMessage('SECLOCK[a85] swipe-release ok=' + (ok ? '1' : '0') +
          ' error=' + ((rel && (rel.error || rel.detail)) || '-'));
      } catch (e) { /* observation only */ }
      if (ok) return { ok: true, state: 'UNLOCKED', mode: mode, via: 'swipe-direct' };
      return { ok: false, error: (rel && rel.error) || 'swipe-release-failed',
        detail: (rel && rel.detail) || 'the security provider did not release the lock' };
    }
    return { ok: false, error: swipeLock
        ? 'swipe-required-on-lockscreen' : 'credential-required-on-lockscreen',
      detail: swipeLock ? 'Swipe the lockhead up to unlock'
                        : 'Enter the credential on the lock screen' };
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
