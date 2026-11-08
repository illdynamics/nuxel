/* Nuxel PWA Back contract (PWNAGE-90000).
 *
 * Apps include this script and register a truthful Back implementation:
 *
 *   NuxelBackProtocol.register({
 *     canGoBack: () => router.depth > 0,
 *     back: () => router.pop(),
 *     atRoot: () => router.depth === 0,   // optional, confirmed state
 *   });
 *
 * A normal document/SPA answers from its real navigation stack.  An app with
 * no internal navigation calls NuxelBackProtocol.declareAtRoot().  "No response"
 * is never interpreted as at-root by the launcher; it becomes unsupported.
 *
 * The message channel is same-origin and correlated by requestId; the launcher
 * validates event.source before accepting a result.
 */
(function (global) {
  'use strict';

  var handler = null;       // {canGoBack, back, atRoot}
  var declaredAtRoot = false;

  function safeBool(fn, fallback) {
    try { return typeof fn === 'function' ? !!fn() : fallback; }
    catch (e) { return fallback; }
  }

  function currentStatus() {
    if (declaredAtRoot) return 'at_root';
    if (!handler) return 'unsupported';
    if (typeof handler.canGoBack === 'function') {
      return safeBool(handler.canGoBack, false) ? 'handled' : 'at_root';
    }
    return 'handled';
  }

  function performBack() {
    if (declaredAtRoot) return 'at_root';
    if (!handler) return 'unsupported';
    if (typeof handler.canGoBack === 'function' && !safeBool(handler.canGoBack, false)) {
      return 'at_root';
    }
    if (typeof handler.back !== 'function') return 'unsupported';
    var ok;
    try { ok = handler.back(); }
    catch (e) { return 'failed'; }
    if (ok === false) return 'at_root';
    if (ok && typeof ok.then === 'function') {
      // Async routers answer through their own state after the transition.
      return 'handled';
    }
    return 'handled';
  }

  function register(impl) {
    if (!impl || typeof impl !== 'object') throw new TypeError('NuxelBackProtocol.register needs an object');
    handler = impl;
    declaredAtRoot = false;
    // Legacy/direct API used by the launcher for same-origin frames.
    global.NuxelBack = {
      canGoBack: function () {
        if (declaredAtRoot) return false;
        if (typeof impl.canGoBack === 'function') return !!impl.canGoBack();
        return true;
      },
      back: function () { return performBack(); },
      status: currentStatus,
    };
    return global.NuxelBack;
  }

  function declareAtRoot() {
    declaredAtRoot = true;
    handler = null;
    global.NuxelBack = {
      canGoBack: function () { return false; },
      back: function () { return false; },
      status: function () { return 'at_root'; },
    };
  }

  global.addEventListener('message', function (event) {
    if (event.origin !== global.location.origin) return;
    var data = event.data;
    if (!data || data.type !== 'nuxel:back-request') return;
    // Only the embedding launcher may ask.  A nested untrusted frame cannot
    // use this helper to answer for another app/session.
    if (event.source !== global.parent && event.source !== global) return;
    var status = performBack();
    try {
      if (event.source && event.source.postMessage) {
        event.source.postMessage({
          type: 'nuxel:back-result',
          requestId: data.requestId,
          session: data.session,
          status: status,
        }, event.origin);
      }
    } catch (e) {}
  }, false);

  global.NuxelBackProtocol = {
    register: register,
    declareAtRoot: declareAtRoot,
    status: currentStatus,
    performBack: performBack,
  };
})(window);
