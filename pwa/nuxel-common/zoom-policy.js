/* Nuxel centralized zoom policy (PWNAGE-80000).
 *
 * Default: DENY.  There is deliberately no UI toggle in this mission; the
 * policy document /usr/share/nuxel/runtime/zoom-policy.json is the single
 * future integration point for the Permission Manager's `zoom` permission.
 * An app is allowed only when the policy explicitly names it with
 * { "zoom": true } (or legacy boolean true).  Missing file, malformed JSON,
 * fetch failure and unknown app ids all resolve to DENY.
 *
 * This is one layer of a defence-in-depth policy.  The native host also:
 *   - pins WebKitWebView magnification/zoom-level to 1.0,
 *   - denies GtkGestureZoom and double-tap gestures in the capture phase,
 *   - swallows Ctrl/Meta+wheel and Ctrl/Meta +/-/0,
 *   - injects this script into EVERY WebKit frame.
 * Ordinary single-finger scrolling, dragging, text selection and OS/accessibility
 * text sizing are never intercepted.
 */
(function (global) {
  'use strict';
  var VERSION = 'p80000';
  var appId = '';
  try {
    var m = document.querySelector('meta[name="nuxel-app-id"]');
    appId = (m && m.getAttribute('content')) || '';
  } catch (e) {}
  var state = { default: 'deny', apps: {} };

  function allowed(id) {
    var key = String(id || appId || '');
    var entry = state.apps && state.apps[key];
    // An explicit per-app denial always wins over a global default.
    if (entry === false) return false;
    if (entry && typeof entry === 'object' && entry.zoom === false) return false;
    if (entry === true) return true;
    if (entry && typeof entry === 'object' && entry.zoom === true) return true;
    // The shipped document is default-deny.  A future Permission Manager may
    // switch the global default while still denying individual apps above.
    return state.default === 'allow';
  }

  function refresh() {
    try {
      if (!global.fetch) return Promise.resolve(false);
      return fetch('/runtime/zoom-policy.json', { cache: 'no-store' })
        .then(function (r) { return r && r.ok ? r.json() : null; })
        .then(function (doc) {
          if (doc && doc.apps && typeof doc.apps === 'object') {
            state = { default: doc.default === 'allow' ? 'allow' : 'deny', apps: doc.apps };
          }
          return true;
        }).catch(function () { return false; });
    } catch (e) { return Promise.resolve(false); }
  }

  function stop(e) {
    try { if (e.cancelable) e.preventDefault(); } catch (x) {}
    try { e.stopPropagation(); } catch (x) {}
    return false;
  }

  // Pinch / magnify gesture events (WebKit/Safari legacy event family).
  ['gesturestart', 'gesturechange', 'gestureend'].forEach(function (name) {
    document.addEventListener(name, function (e) { allowed(appId) ? null : stop(e); },
      { capture: true, passive: false });
  });

  // Ctrl/Meta + wheel is the desktop zoom path (also emitted by some trackpads).
  document.addEventListener('wheel', function (e) {
    if ((e.ctrlKey || e.metaKey) && !allowed(appId)) stop(e);
  }, { capture: true, passive: false });

  // Ctrl/Meta +/-/0 keyboard zoom.  Alt+/- and plain +/- are untouched.
  document.addEventListener('keydown', function (e) {
    if (!(e.ctrlKey || e.metaKey) || allowed(appId)) return;
    if (e.key === '+' || e.key === '=' || e.key === '-' || e.key === '_' || e.key === '0') stop(e);
  }, { capture: true, passive: false });

  // Two-finger touch is the mobile pinch path.  A one-finger touch is never
  // cancelled, so scrolling, dragging, selection and app controls are intact.
  document.addEventListener('touchstart', function (e) {
    if (!allowed(appId) && e.touches && e.touches.length > 1) stop(e);
  }, { capture: true, passive: false });
  document.addEventListener('touchmove', function (e) {
    if (!allowed(appId) && e.touches && e.touches.length > 1) stop(e);
  }, { capture: true, passive: false });

  // The native host calls this after orientation changes and app transitions.
  function reset(win) {
    win = win || global;
    try { if (win.scrollTo) win.scrollTo(win.scrollX || 0, win.scrollY || 0); } catch (e) {}
    try { win.dispatchEvent(new CustomEvent('nuxel:zoom-reset')); } catch (e) {}
    return true;
  }

  global.NuxelZoomPolicy = {
    version: VERSION,
    defaultDeny: true,
    appId: appId,
    allowed: allowed,
    refresh: refresh,
    reset: reset,
    // Future Permission Manager integration point.  This does not expose a UI.
    setPolicy: function (doc) {
      if (doc && doc.apps && typeof doc.apps === 'object') {
        state = { default: doc.default === 'allow' ? 'allow' : 'deny', apps: doc.apps };
      }
    }
  };
  refresh();
})(typeof window !== 'undefined' ? window : this);
