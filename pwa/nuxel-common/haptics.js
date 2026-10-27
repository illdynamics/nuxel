/* Nuxel shared haptics client (PWNAGE-30000).
   One path for tap/navigation/alarm haptics: NuxelBridge haptics.pulse, then
   the native NuxelHost action, then navigator.vibrate as a last resort.  It is
   rate-limited, enabled/disabled by persisted settings, and never blocks input.
   A dispatch result means the REQUEST reached a haptics owner — it does not
   prove the motor moved. */
(function (global) {
  'use strict';
  var SETTINGS_KEY = 'nuxel-haptics-settings';
  var lastAt = {};
  var COOLDOWN = { tap: 45, navigation: 70, switch: 80, long: 350, alarm: 0, test: 0 };

  function defaults() { return { enabled: true, intensity: 30, keyboard: true, alarm: true }; }
  function settings() {
    try {
      var raw = global.localStorage && global.localStorage.getItem(SETTINGS_KEY);
      if (!raw) return defaults();
      var d = JSON.parse(raw) || {};
      var out = defaults();
      Object.keys(out).forEach(function (k) { if (typeof d[k] === typeof out[k]) out[k] = d[k]; });
      return out;
    } catch (e) { return defaults(); }
  }
  function saveSettings(s) {
    try { if (global.localStorage) global.localStorage.setItem(SETTINGS_KEY, JSON.stringify(s)); } catch (e) {}
  }
  function cooldown(kind) { return COOLDOWN[kind] || 45; }
  function pulse(kind) {
    var s = settings();
    if (!s.enabled) return Promise.resolve({ ok: false, reason: 'disabled' });
    if (kind === 'tap' && !s.keyboard) return Promise.resolve({ ok: false, reason: 'keyboard_disabled' });
    var now = Date.now();
    if (now - (lastAt[kind] || 0) < cooldown(kind)) {
      return Promise.resolve({ ok: false, reason: 'rate_limited' });
    }
    lastAt[kind] = now;
    if (global.NuxelBridge && typeof global.NuxelBridge.call === 'function') {
      return global.NuxelBridge.call('haptics', 'pulse', { kind: kind }).then(function (res) {
        return { ok: !!(res && res.success !== false), result: res };
      });
    }
    if (global.NuxelHost && global.NuxelHost.available && global.NuxelHost.action) {
      try { global.NuxelHost.action('haptics-' + kind); return Promise.resolve({ ok: true }); } catch (e) {}
    }
    try { if (global.navigator && global.navigator.vibrate) { global.navigator.vibrate(12); return Promise.resolve({ ok: true }); } } catch (e) {}
    return Promise.resolve({ ok: false, reason: 'unavailable' });
  }
  var api = {
    pulse: pulse,
    settings: settings,
    update: function (patch) {
      var s = settings();
      Object.keys(patch || {}).forEach(function (k) { s[k] = patch[k]; });
      saveSettings(s);
      return s;
    },
    tap: function () { return pulse('tap'); },
    navigation: function () { return pulse('navigation'); },
    alarm: function () { return pulse('alarm'); }
  };
  global.NuxelHaptics = api;
})(typeof window !== 'undefined' ? window : this);
