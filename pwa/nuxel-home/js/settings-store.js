// Nuxel Settings Store (A33) — one durable settings document per setting name.
//
// WHY THIS EXISTS
//   The verbose-boot switch (briq-02b) has to be a real, durable setting: it
//   must survive a reboot, survive a package/rootfs update WITHOUT being
//   clobbered, and it must be the SAME value whether the user flips it in the
//   Quick Settings panel, in the Nuxel Settings app, or from the console with
//   `nuxelctl verbose-boot on`.  There must not be a UI path and a console path
//   that can disagree.
//
// STORAGE CONTRACT
//   * Durable file:  /etc/nuxel/boot/<name>.json   (through NuxelHost.configSet,
//                    which is an atomic same-directory rename in nuxel-pwa-host;
//                    the console writes the same file atomically).
//   * Fallback:      localStorage['nuxel.settings.<name>']  (VM / desktop /
//                    plain browser, and any host that refuses the name).
//   * Upgrades never clobber: a write MERGES into the document that was loaded,
//     preserving keys this revision does not know about, and the installer ships
//     the default with the 'keep' rule (existing file wins).
//   * Migration: older launcher revisions kept ad-hoc flags in localStorage
//     (nuxel.verboseBoot, nuxel.verbose_boot, nuxel.settings.verboseBoot).  They
//     are read ONCE, only when the durable document has no user-set value, and
//     the origin is recorded in the document as `migrated_from`.
//
// BOOT DIAGNOSTICS (briq-02b, extended in the bg-02 verification pass)
//   The SAME document carries three independent controls, because they are three
//   questions about the same thing (what the boot shows and says) and splitting
//   them across three files would let them contradict each other:
//     * verbose_boot      - show the on-glass boot log at all
//     * animation_mode    - standard | short | off boot-animation policy
//     * verbosity_level   - 0 quiet .. 3 debug detail of that log
//   Precedence for the animation: off > short > verbose_boot > standard.
//   verbosity_level never turns the log on; it only selects how much it says.
//
// The module is DOM-free so its behaviour can be unit-tested in node
// (tools/s10plus/a33/tests/settings-store-test.js).
(function (global) {
  'use strict';

  var HOST_NAME = {};                 // store name -> NuxelHost config name
  HOST_NAME['verbose-boot'] = 'verbose-boot';
  HOST_NAME['animation-handoff'] = 'animation-handoff';
  HOST_NAME['statusbar-safezones'] = 'statusbar-safezones';

  // The boot-diagnostics controls the UI and the console share.  Exported so the
  // Settings app and the Quick Settings tile cannot invent a fourth value.
  var ANIMATION_MODES = ['standard', 'short', 'off'];
  var VERBOSITY_MIN = 0;
  var VERBOSITY_MAX = 3;
  var DEFAULT_VERBOSITY = 1;

  var DEFAULTS = {
    'verbose-boot': {
      schema_version: 1,
      verbose_boot: false,
      animation_mode: 'standard',
      verbosity_level: DEFAULT_VERBOSITY,
      set_by: 'default',
      updated_at: 0,
      migrated_from: null
    },
    'animation-handoff': {
      schema_version: 1,
      mode: 'receipt',
      mp4_frames: 192,
      mp4_fps: 24,
      min_cycles: 1,
      max_wait_s: 24
    }
  };

  // Legacy localStorage keys migrated on first read (name -> list of keys).
  var LEGACY_KEYS = {
    'verbose-boot': ['nuxel.verboseBoot', 'nuxel.verbose_boot', 'nuxel.settings.verboseBoot']
  };

  var cache = {};                     // name -> { doc, transport, loaded }
  var listeners = [];

  function clone(o) { return JSON.parse(JSON.stringify(o)); }

  function lsGet(key) { try { return global.localStorage.getItem(key); } catch (e) { return null; } }
  function lsSet(key, val) { try { global.localStorage.setItem(key, val); } catch (e) { /* storage may be denied */ } }

  function defaults(name) {
    if (!DEFAULTS[name]) {
      DEFAULTS[name] = { schema_version: 1 };
    }
    return clone(DEFAULTS[name]);
  }

  function host() {
    var h = global.NuxelHost;
    if (h && h.available) return h;
    return null;
  }

  function diag(line) {
    // Evidence channel: the same hook safe-zones.js uses, so a settings change
    // is visible in the live console instead of only in a JSON file.
    try {
      if (global.webkit && global.webkit.messageHandlers && global.webkit.messageHandlers.nuxelDiag) {
        global.webkit.messageHandlers.nuxelDiag.postMessage(line);
      } else if (global.console && global.console.log) {
        global.console.log('[settings] ' + line);
      }
    } catch (e) { /* never break the launcher for evidence */ }
  }

  function merge(base, patch) {
    var out = clone(base);
    for (var k in patch) {
      if (Object.prototype.hasOwnProperty.call(patch, k) && patch[k] !== undefined) out[k] = patch[k];
    }
    return out;
  }

  function migrate(name, doc) {
    var keys = LEGACY_KEYS[name] || [];
    // Only migrate when the durable document carries no user decision yet.
    var userSet = doc && (doc.set_by === 'user' || doc.updated_at > 0);
    if (userSet) return doc;
    for (var i = 0; i < keys.length; i++) {
      var raw = lsGet(keys[i]);
      if (raw === null) continue;
      var val = raw;
      if (val === '1' || val === 'true') val = true;
      else if (val === '0' || val === 'false') val = false;
      else continue;
      if (name === 'verbose-boot') doc.verbose_boot = !!val;
      doc.set_by = 'migrated';
      doc.migrated_from = keys[i];
      doc.updated_at = Date.now();
      diag('SETTINGS_MIGRATED name=' + name + ' from=' + keys[i] + ' value=' + JSON.stringify(val));
      save(name, doc, { silent: true });
      return doc;
    }
    return doc;
  }

  function load(name, cb) {
    var dflt = defaults(name);
    var done = function (doc, transport) {
      doc = migrate(name, doc);
      cache[name] = { doc: doc, transport: transport, loaded: true };
      if (cb) cb(cache[name]);
      return cache[name];
    };
    var h = host();
    if (h) {
      var cfgName = HOST_NAME[name] || name;
      try {
        return h.configGet(cfgName).then(function (res) {
          if (res && res.ok && res.text) {
            try { return done(merge(dflt, JSON.parse(res.text)), 'host'); }
            catch (e) { /* fall through to storage */ }
          }
          return doneFromStorage();
        }, doneFromStorage);
      } catch (e) { /* fall through */ }
    }
    return doneFromStorage();

    function doneFromStorage() {
      var raw = lsGet('nuxel.settings.' + name);
      if (raw) { try { return done(merge(dflt, JSON.parse(raw)), 'localStorage'); } catch (e) { /* keep default */ } }
      return done(dflt, 'default');
    }
  }

  function current(name) {
    if (!cache[name] || !cache[name].loaded) return defaults(name);
    return cache[name].doc;
  }

  function save(name, patchOrDoc, opts) {
    opts = opts || {};
    var before = current(name);
    var doc = merge(before, patchOrDoc);
    doc.schema_version = doc.schema_version || 1;
    if (!opts.silent) {
      doc.set_by = patchOrDoc.set_by || 'user';
      doc.updated_at = Date.now();
    }
    var text = JSON.stringify(doc, null, 2) + '\n';
    cache[name] = { doc: doc, transport: cache[name] && cache[name].transport, loaded: true };

    var announce = function (how) {
      if (cache[name]) cache[name].transport = how;
      diag('SETTINGS_SET name=' + name + ' transport=' + how + ' doc=' + JSON.stringify(doc));
      var ev = { name: name, doc: clone(doc), transport: how };
      listeners.slice().forEach(function (cb) { try { cb(ev); } catch (e) { /* a listener must never break a setting */ } });
      try { global.dispatchEvent(new CustomEvent('nuxel:settings-changed', { detail: ev })); } catch (e) { /* DOM-free harness */ }
    };

    var h = host();
    if (h) {
      var cfgName = HOST_NAME[name] || name;
      try {
        var p = h.configSet(cfgName, text);
        if (p && p.then) {
          return p.then(function (res) {
            if (res && res.ok) { announce('host'); return { ok: true, transport: 'host', doc: doc }; }
            lsSet('nuxel.settings.' + name, text);
            announce('localStorage');
            return { ok: true, transport: 'localStorage', doc: doc, degraded: true };
          }, function () {
            lsSet('nuxel.settings.' + name, text);
            announce('localStorage');
            return { ok: true, transport: 'localStorage', doc: doc, degraded: true };
          });
        }
      } catch (e) { /* fall through to storage */ }
    }
    lsSet('nuxel.settings.' + name, text);
    announce('localStorage');
    return { ok: true, transport: 'localStorage', doc: doc };
  }

  var API = {
    // Observable, testable surface.
    DEFAULTS: DEFAULTS,
    hostName: function (name) { return HOST_NAME[name] || name; },
    load: load,
    get: function (name) { return clone(current(name)); },
    value: function (name, key) { var d = current(name); return d ? d[key] : undefined; },
    set: function (name, patch) { return save(name, patch); },
    toggle: function (name, key) {
      var d = current(name);
      var patch = {};
      patch[key] = !d[key];
      return save(name, patch);
    },
    subscribe: function (cb) { listeners.push(cb); return function () { listeners = listeners.filter(function (l) { return l !== cb; }); }; },
    transport: function (name) { return cache[name] ? cache[name].transport : undefined; },
    reset: function () { cache = {}; listeners = []; },   // harness use only
    // Convenience wrappers for the boot-diagnostics controls (verbose-boot
    // document).  They all go through save(), so they MERGE: a key this
    // revision does not know about survives, which is what makes a downgrade
    // safe, and the three controls are written to one durable file.
    verboseBoot: function () { return !!current('verbose-boot').verbose_boot; },
    setVerboseBoot: function (on) { return save('verbose-boot', { verbose_boot: !!on }); },
    animationMode: function () {
      var m = String(current('verbose-boot').animation_mode || 'standard').toLowerCase();
      return ANIMATION_MODES.indexOf(m) >= 0 ? m : 'standard';
    },
    setAnimationMode: function (mode) {
      var m = String(mode == null ? '' : mode).toLowerCase();
      if (ANIMATION_MODES.indexOf(m) < 0) return { ok: false, error: 'bad animation_mode', allowed: ANIMATION_MODES.slice() };
      return save('verbose-boot', { animation_mode: m });
    },
    verbosityLevel: function () {
      var n = parseInt(current('verbose-boot').verbosity_level, 10);
      if (isNaN(n) || n < VERBOSITY_MIN || n > VERBOSITY_MAX) return DEFAULT_VERBOSITY;
      return n;
    },
    setVerbosityLevel: function (level) {
      var n = parseInt(level, 10);
      if (isNaN(n) || n < VERBOSITY_MIN || n > VERBOSITY_MAX) {
        return { ok: false, error: 'bad verbosity_level', min: VERBOSITY_MIN, max: VERBOSITY_MAX };
      }
      return save('verbose-boot', { verbosity_level: n });
    },
    // One read/write for the whole panel (the Settings app uses this so a single
    // failed write cannot leave three controls disagreeing with the document).
    bootDiagnostics: function () {
      var d = current('verbose-boot');
      return { verbose_boot: !!d.verbose_boot, animation_mode: API.animationMode(), verbosity_level: API.verbosityLevel() };
    },
    setBootDiagnostics: function (patch) {
      var out = {};
      if (patch && Object.prototype.hasOwnProperty.call(patch, 'verbose_boot')) out.verbose_boot = !!patch.verbose_boot;
      if (patch && Object.prototype.hasOwnProperty.call(patch, 'animation_mode')) {
        var m = String(patch.animation_mode).toLowerCase();
        if (ANIMATION_MODES.indexOf(m) < 0) return { ok: false, error: 'bad animation_mode', allowed: ANIMATION_MODES.slice() };
        out.animation_mode = m;
      }
      if (patch && Object.prototype.hasOwnProperty.call(patch, 'verbosity_level')) {
        var n = parseInt(patch.verbosity_level, 10);
        if (isNaN(n) || n < VERBOSITY_MIN || n > VERBOSITY_MAX) {
          return { ok: false, error: 'bad verbosity_level', min: VERBOSITY_MIN, max: VERBOSITY_MAX };
        }
        out.verbosity_level = n;
      }
      if (!Object.keys(out).length) return { ok: false, error: 'nothing to change' };
      return save('verbose-boot', out);
    },
    // The precedence rule, in one place, so the UI can explain it and the tests
    // can assert it: off > short > verbose_boot > standard.
    effectiveAnimation: function () {
      var mode = API.animationMode();
      if (mode === 'off') return { mode: 'off', reason: 'animation_mode_off' };
      if (mode === 'short') return { mode: 'short', reason: 'animation_mode_short' };
      if (API.verboseBoot()) return { mode: 'short', reason: 'verbose_boot_requested' };
      return { mode: 'standard', reason: 'standard' };
    },
    ANIMATION_MODES: ANIMATION_MODES,
    VERBOSITY_MIN: VERBOSITY_MIN,
    VERBOSITY_MAX: VERBOSITY_MAX,
    VERBOSITY_LABELS: {
      0: 'quiet (markers only)',
      1: 'normal (default)',
      2: 'verbose (per-stage)',
      3: 'debug (everything)'
    }
  };

  global.NuxelSettings = API;
})(typeof window !== 'undefined' ? window : this);
