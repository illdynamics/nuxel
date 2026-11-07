/* Nuxel shared theme client (PWNAGE-30000).
   DOM-light so it can be unit-tested in node; in a browser it applies the
   persisted theme to <html data-theme=…> immediately and on change. */
(function (global) {
  'use strict';
  var THEMES = [
    { id: 'nuxel-grove', name: 'Nuxel Grove', accent: '#3beaa1', default: true },
    { id: 'test-theme', name: 'Test Theme', accent: '#ff9f43', default: false }
  ];
  var KEY = 'nuxel-theme';
  var APPEARANCE_KEY = 'nuxel.appearance';
  var APPEARANCES = ['system', 'light', 'dark'];
  // PWNAGE-85000: motion preference.  'system' follows prefers-reduced-motion;
  // 'full' is the explicit opt-in; 'reduced' keeps only essential feedback;
  // 'off' is near-instant.  Persisted per origin and shared with open frames.
  var MOTION_KEY = 'nuxel.motion';
  var MOTIONS = ['system', 'full', 'reduced', 'off'];

  function storageGet() {
    try { return global.localStorage && global.localStorage.getItem(KEY); }
    catch (e) { return null; }
  }
  function storageSet(v) {
    try { if (global.localStorage) global.localStorage.setItem(KEY, v); }
    catch (e) { /* ignore */ }
  }
  function valid(id) {
    for (var i = 0; i < THEMES.length; i++) if (THEMES[i].id === id) return THEMES[i];
    return null;
  }
  function current() {
    var id = storageGet();
    if (!valid(id)) id = 'nuxel-grove';
    return valid(id);
  }
  function apply(id) {
    if (!valid(id)) id = 'nuxel-grove';
    storageSet(id);
    if (global.document && global.document.documentElement) {
      global.document.documentElement.setAttribute('data-theme', id);
      var meta = global.document.querySelector('meta[name="theme-color"]');
      if (meta) meta.setAttribute('content', valid(id).accent);
    }
    if (global.NuxelSettings && typeof global.NuxelSettings.set === 'function') {
      try { global.NuxelSettings.set('appearance', { theme: id }); } catch (e) { /* optional */ }
    }
    try {
      global.dispatchEvent(new CustomEvent('nuxel:theme-changed', { detail: { id: id } }));
    } catch (e) { /* node harness */ }
    return { id: id, name: valid(id).name, accent: valid(id).accent };
  }
  function appearance() {
    try {
      var v = global.localStorage && global.localStorage.getItem(APPEARANCE_KEY);
      return APPEARANCES.indexOf(v) >= 0 ? v : 'system';
    } catch (e) { return 'system'; }
  }
  function applyAppearance(mode) {
    if (APPEARANCES.indexOf(mode) < 0) mode = 'system';
    try { if (global.localStorage) global.localStorage.setItem(APPEARANCE_KEY, mode); } catch (e) {}
    try {
      if (global.document && global.document.documentElement)
        global.document.documentElement.setAttribute('data-appearance', mode);
    } catch (e) {}
    try { global.dispatchEvent(new CustomEvent('nuxel:appearance-changed', { detail: { mode: mode } })); } catch (e) {}
    return mode;
  }
  function motion() {
    try {
      var v = global.localStorage && global.localStorage.getItem(MOTION_KEY);
      return MOTIONS.indexOf(v) >= 0 ? v : 'system';
    } catch (e) { return 'system'; }
  }
  function applyMotion(mode) {
    if (MOTIONS.indexOf(mode) < 0) mode = 'system';
    try { if (global.localStorage) global.localStorage.setItem(MOTION_KEY, mode); } catch (e) {}
    try {
      if (global.document && global.document.documentElement)
        global.document.documentElement.setAttribute('data-motion', mode);
    } catch (e) {}
    try { global.dispatchEvent(new CustomEvent('nuxel:motion-changed', { detail: { mode: mode } })); } catch (e) {}
    return mode;
  }

  var listeners = [];
  var api = {
    THEMES: THEMES,
    KEY: KEY,
    valid: valid,
    current: current,
    apply: apply,
    appearance: appearance,
    applyAppearance: applyAppearance,
    APPEARANCES: APPEARANCES,
    MOTION_KEY: MOTION_KEY,
    MOTIONS: MOTIONS,
    motion: motion,
    applyMotion: applyMotion,
    subscribe: function (cb) { listeners.push(cb); return function () { listeners = listeners.filter(function (l) { return l !== cb; }); }; },
    _emit: function (ev) { listeners.forEach(function (l) { try { l(ev); } catch (e) {} }); }
  };
  if (global.document && global.document.documentElement) {
    apply(current().id);
    applyAppearance(appearance());
    applyMotion(motion());
    try {
      global.addEventListener('nuxel:theme-changed', function (e) {
        api._emit(e.detail);
      });
    } catch (e) { /* node */ }
    // Same-origin frames (launcher + every PWA) share localStorage; the
    // storage event lets a Settings change apply immediately to already-open
    // apps and the launcher without a reload.
    try {
      global.addEventListener('storage', function (e) {
        if (e && e.key === KEY && e.newValue) apply(e.newValue);
        if (e && e.key === APPEARANCE_KEY && e.newValue) applyAppearance(e.newValue);
        if (e && e.key === MOTION_KEY && e.newValue) applyMotion(e.newValue);
      });
    } catch (e) { /* node */ }
  }
  global.NuxelTheme = api;
})(typeof window !== 'undefined' ? window : this);
