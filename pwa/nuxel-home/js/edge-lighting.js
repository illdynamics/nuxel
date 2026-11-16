/* Nuxel Edge Lighting — the ONE presentation controller for notification
 * edge effects and the Nuxel Edge Panel (PWNAGE-103000).
 *
 * WHAT THIS IS
 *   A DOM overlay on the curved AMOLED display.  One reusable root, one
 *   cancellable animation lifecycle, eight S10-style effects.  It is NOT a
 *   physical notification LED (the S10+ has none), never touches the camera
 *   flash, never writes the framebuffer and never mutates notification state.
 *
 * WHERE THE EVENT COMES FROM
 *   The bridge watches org.nuxel.Notifications.NotificationAdded on the system
 *   bus and records accepted events in a bounded journal.  This module polls
 *   that journal (GET /api/v1/edge-lighting/events?since=N) with a plain fetch
 *   so a real notification always reaches Home even if the bridge client's
 *   token/version handshake is degraded.  A poll only runs while this page is
 *   visible and not in display sleep; the journal is read-only.
 *
 * SETTINGS (one document: /etc/nuxel/edge-lighting/edge-lighting.json)
 *   The bridge provider owns validation + persistence.  This module applies the
 *   user's choice to the running overlay immediately and sends the patch over
 *   the existing `edge-lighting` RPC namespace.
 *
 * REDUCED MOTION
 *   The system `prefers-reduced-motion` media query and the Nuxel motion
 *   preference (NuxelTheme.motion(): system|full|reduced|off) are honoured.
 *   Reduced motion shows a short static edge pulse; `off` shows nothing.
 *
 * The module is DOM-light enough to be unit-tested in node: the effect registry,
 * settings normalisation and the recognizer primitives are pure functions.
 */
(function (global) {
  'use strict';

  var BASE = global.NUXEL_API_URL || 'http://127.0.0.1:8080/api/v1';
  // Subtle cyan/blue fallback ONLY when the live theme exposes no accent token
  // (theme.css defines --nx-accent; this is never used as a forked effect colour).
  var DEFAULT_ACCENT = '#63f0bd';
  var EFFECTS = ['basic', 'wave', 'bubble', 'multicolor', 'heart', 'fireworks', 'eclipse', 'echo'];
  var EFFECT_LABELS = {
    basic: 'Basic', wave: 'Wave', bubble: 'Bubble', multicolor: 'Multicolor',
    heart: 'Heart', fireworks: 'Fireworks', eclipse: 'Eclipse', echo: 'Echo'
  };
  var DEFAULTS = {
    enabled: true, effect: 'wave', color_mode: 'theme', color: null,
    width: 'medium', transparency: 'medium', duration_ms: 1800,
    screen_mode: 'screen_on', respect_dnd: true, respect_reduced_motion: true,
    reduced_motion_style: 'static', source_mode: 'all', allowed_apps: [], blocked_apps: [],
    // Lifecycle edge effects (PWNAGE-SSP): each OFF unless the owner enables it.
    // The engine default is the configured Nuxel behaviour: waking / unlocking
    // the phone plays the configured effect.  A stored (user) document always
    // wins, so the owner's persisted switches are never overwritten.
    lifecycle: { screen_on: true, screen_off: false, lock: false, unlock: true }
  };
  var LIFECYCLE_KEYS = ['screen_on', 'screen_off', 'lock', 'unlock'];
  var WIDTH_SCALE = { thin: 0.6, medium: 1, wide: 1.5 };
  var TRANSPARENCY_ALPHA = { low: 0.35, medium: 0.55, high: 0.8 };  // high = more transparent
  var MAX_DURATION_MS = 6000;
  var MIN_DURATION_MS = 600;

  function clone(o) { return JSON.parse(JSON.stringify(o)); }

  function normaliseDuration(ms) {
    var n = parseInt(ms, 10);
    if (isNaN(n)) n = DEFAULTS.duration_ms;
    return Math.max(MIN_DURATION_MS, Math.min(MAX_DURATION_MS, n));
  }

  function normaliseSettings(raw) {
    var out = clone(DEFAULTS);
    // The Home engine may receive the provider document or an RPC response.
    // `allowed_apps: null` is the UI's explicit "All apps" marker; normalise it
    // to the provider's canonical empty list so a re-render cannot show every
    // app as individually selected after "Allow all apps".
    if (raw && typeof raw === 'object' && raw.allowed_apps === null) {
      raw = clone(raw);
      raw.allowed_apps = [];
    }
    if (raw && typeof raw === 'object') {
      for (var k in DEFAULTS) {
        if (Object.prototype.hasOwnProperty.call(raw, k) && raw[k] !== undefined) {
          // A NULL means "not configured": keep the engine default rather than
          // letting an absent document silently disable a lifecycle effect.
          if (raw[k] === null && k === 'lifecycle') continue;
          out[k] = raw[k];
        }
      }
    }
    if (EFFECTS.indexOf(String(out.effect).toLowerCase()) < 0) out.effect = 'wave';
    else out.effect = String(out.effect).toLowerCase();
    if (['thin', 'medium', 'wide'].indexOf(out.width) < 0) out.width = 'medium';
    if (['low', 'medium', 'high'].indexOf(out.transparency) < 0) out.transparency = 'medium';
    out.duration_ms = normaliseDuration(out.duration_ms);
    out.screen_mode = 'screen_on';   // only this mode is supported by the stack
    if (['all', 'allowlist'].indexOf(out.source_mode) < 0) out.source_mode = 'all';
    if (!Array.isArray(out.allowed_apps)) out.allowed_apps = [];
    out.enabled = out.enabled !== false;
    // Lifecycle toggles: strict booleans; a legacy document means all OFF.
    var lcIn = (raw && typeof raw === 'object' && raw.lifecycle && typeof raw.lifecycle === 'object')
      ? raw.lifecycle : {};
    var lc = {};
    LIFECYCLE_KEYS.forEach(function (k) { lc[k] = lcIn[k] === true; });
    out.lifecycle = lc;
    return out;
  }

  /* Resolve a colour from mode + value + the live Nuxel theme accent.
   * Never invents an app colour: 'app' mode uses the registry colour only when
   * the caller supplies a real #rrggbb, otherwise the theme accent. */
  function resolveColor(settings, themeAccent, appColor) {
    var s = settings || {};
    var accent = /^#[0-9a-fA-F]{6}$/.test(String(themeAccent || '')) ? String(themeAccent) : DEFAULT_ACCENT;
    var own = /^#[0-9a-fA-F]{6}$/.test(String(s.color || '')) ? String(s.color) : null;
    if (s.color_mode === 'custom' || s.color_mode === 'preset') return own || accent;
    if (s.color_mode === 'app') {
      return /^#[0-9a-fA-F]{6}$/.test(String(appColor || '')) ? String(appColor) : accent;
    }
    return accent;
  }

  function liveThemeAccent() {
    try {
      var v = global.getComputedStyle && global.getComputedStyle(global.document.documentElement)
        .getPropertyValue('--nx-accent');
      v = String(v || '').trim();
      if (/^#[0-9a-fA-F]{6}$/.test(v)) return v;
    } catch (e) { /* fall through */ }
    try {
      if (global.NuxelTheme && global.NuxelTheme.current) return global.NuxelTheme.current().accent;
    } catch (e) { /* fall through */ }
    return DEFAULT_ACCENT;
  }

  function reducedMotionState() {
    var systemReduce = false;
    try { systemReduce = !!(global.matchMedia && global.matchMedia('(prefers-reduced-motion: reduce)').matches); }
    catch (e) { systemReduce = false; }
    var mode = 'system';
    try { if (global.NuxelTheme && global.NuxelTheme.motion) mode = global.NuxelTheme.motion(); } catch (e) { /* default */ }
    if (mode === 'off') return 'off';
    if (mode === 'reduced') return 'reduced';
    if (mode === 'full') return 'full';
    return systemReduce ? 'reduced' : 'full';
  }

  function rgba(hex, alpha) {
    var h = String(hex || DEFAULT_ACCENT).replace('#', '');
    if (h.length !== 6) h = DEFAULT_ACCENT.replace('#', '');
    var r = parseInt(h.slice(0, 2), 16), g = parseInt(h.slice(2, 4), 16), b = parseInt(h.slice(4, 6), 16);
    return 'rgba(' + r + ',' + g + ',' + b + ',' + alpha + ')';
  }

  /* Deterministic per-effect scene description.  Kept free of DOM so tests can
   * assert the particle budget and effect identity without a browser. */
  function sceneSpec(effect, opts) {
    opts = opts || {};
    var width = WIDTH_SCALE[opts.width] || 1;
    var spec = { effect: effect, width: width, elements: 0, particles: 0, duration_ms: normaliseDuration(opts.duration_ms) };
    switch (effect) {
      case 'basic': spec.elements = 2; break;                               // one band per side
      case 'wave': spec.elements = 6; spec.particles = 6; break;            // 3 traces per side
      case 'bubble': spec.elements = 2; spec.particles = 8; break;          // 4 per side
      case 'multicolor': spec.elements = 2; spec.gradient = true; break;
      case 'heart': spec.elements = 2; spec.particles = 6; break;           // 3 per side
      case 'fireworks': spec.elements = 2; spec.particles = 10; break;      // 5 per side
      case 'eclipse': spec.elements = 2; spec.particles = 2; break;         // upper corner crescents
      case 'echo': spec.elements = 2; spec.particles = 6; break;            // 3 bands per side
      default: return null;
    }
    return spec;
  }

  /* ---------------------------------------------------------------- */
  var EdgeLighting = {
    EFFECTS: EFFECTS,
    EFFECT_LABELS: EFFECT_LABELS,
    DEFAULTS: DEFAULTS,
    normaliseSettings: normaliseSettings,
    normaliseDuration: normaliseDuration,
    resolveColor: resolveColor,
    reducedMotionState: reducedMotionState,
    sceneSpec: sceneSpec,
    rgba: rgba
  };

  if (global.document && global.document.createElement) install(EdgeLighting);
  global.NuxelEdgeLighting = EdgeLighting;

  function raf(fn) {
    var r = global.requestAnimationFrame || function (f) { return global.setTimeout(function () { f(Date.now()); }, 16); };
    return r(fn);
  }

  function isSleeping() {
    var b = global.document.body;
    if (!b) return false;
    // A85: `document.hidden` is FOCUS visibility.  The Nuxel launcher always
    // owns the glass, but a WebKit window that is not the focused GTK window
    // reports hidden -- and that silently suppressed every notification edge
    // effect.  Only the real display sleep state (Nuxel's own class / host API)
    // counts here.
    var nuxel = global.nuxel;
    try {
      if (nuxel && typeof nuxel.isDisplayOff === 'function') return !!nuxel.isDisplayOff();
    } catch (e) { /* fall through */ }
    return b.classList.contains('screen-off') || b.classList.contains('display-off') ||
      b.classList.contains('screen-sleep');
  }

  function isLocked() {
    try {
      if (global.nuxel && typeof global.nuxel.isLocked === 'function') return !!global.nuxel.isLocked();
    } catch (e) { /* fall through */ }
    var b = global.document.body;
    return !!(b && (b.classList.contains('locked') || b.classList.contains('lockscreen-active') ||
                    b.classList.contains('security-lock')));
  }

  function escHtml(s) {
    return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c];
    });
  }

  function install(api) {
    var root = null, layer = null, panel = null, panelApps = null, panelNotifs = null;
    var settings = api.normaliseSettings(api.DEFAULTS);
    var current = null;            // the ONE active animation descriptor
    var lastSeq = 0;
    var pollTimer = null, polling = false;
    var panelOpen = false, panelSide = 'left';
    var status = { provider: 'unknown', lastError: null, lastPreviewAt: 0, lastEventAt: 0, lastPollAt: 0, capability: null, dnd: null };

    function diag(line) {
      try {
        if (global.webkit && global.webkit.messageHandlers && global.webkit.messageHandlers.nuxelDiag) {
          global.webkit.messageHandlers.nuxelDiag.postMessage(line);
        }
      } catch (e) { /* diagnostics must never break the UI */ }
    }

    /* ---------------- overlay root (one instance, ever) ---------------- */
    function ensureRoot() {
      if (root && root.isConnected) return root;
      var old = global.document.querySelectorAll('#nuxel-edge-lighting');
      for (var i = 0; i < old.length; i++) old[i].remove();
      root = global.document.createElement('div');
      root.id = 'nuxel-edge-lighting';
      root.className = 'edge-root';
      root.setAttribute('aria-hidden', 'true');
      layer = global.document.createElement('div');
      layer.id = 'nuxel-edge-lighting-layer';
      layer.className = 'edge-layer';
      root.appendChild(layer);
      global.document.body.appendChild(root);
      return root;
    }

    function stop(reason) {
      if (current) {
        try { current.cancel(); } catch (e) { /* already gone */ }
        current = null;
      }
      if (layer) layer.textContent = '';
      if (root) {
        root.classList.remove('active', 'edge-preview-requested');
        if (root.style) root.style.zIndex = '';
      }
      diag('EDGE_LIGHTING_STOP reason=' + reason);
    }

    function visibleNow() {
      return settings.enabled !== false && !isSleeping();
    }

    /* Lifecycle effects are explicit owner opt-ins and are independent of the
       notification master switch: turning edge lighting off for notifications
       must not silently disable a screen-on pulse the owner asked for. */
    function lifecycleWanted(key) {
      var lc = settings.lifecycle || {};
      return lc[key] === true && api.reducedMotionState() !== 'off';
    }

    function playLifecycle(key) {
      var color = resolveColor(settings, liveThemeAccent(), null);
      var res = play(settings.effect, color, {
        duration_ms: Math.min(settings.duration_ms, 1200),
        width: settings.width, transparency: settings.transparency
      }, { lifecycle: key });
      diag('EDGE_LIFECYCLE event=' + key + ' played=' + (res ? 'yes' : 'no'));
      return res;
    }

    function setStyleVars(el, color, transparency) {
      el.style.setProperty('--edge-color', color);
      el.style.setProperty('--edge-glow', rgba(color, 0.55));
      el.style.setProperty('--edge-alpha', String(TRANSPARENCY_ALPHA[transparency] || 0.55));
    }

    /* Build the scene: both curved sides, logical CSS pixels, no layout reads. */
    function buildScene(effect, color, opts) {
      ensureRoot();
      layer.textContent = '';
      root.classList.add('active');
      var spec = api.sceneSpec(effect, opts);
      for (var s = 0; s < 2; s++) {
        var side = global.document.createElement('div');
        side.className = 'edge-side edge-side-' + (s === 0 ? 'left' : 'right');
        side.style.setProperty('--edge-width-scale', String(spec.width));
        setStyleVars(side, color, opts.transparency);
        var band = global.document.createElement('div');
        band.className = 'edge-band edge-fx-' + effect;
        side.appendChild(band);
        var particles = particlesFor(effect, color, opts.transparency);
        for (var k = 0; k < particles.length; k++) side.appendChild(particles[k]);
        layer.appendChild(side);
      }
      return spec;
    }

    function particlesFor(effect, color, transparency) {
      var out = [];
      var i;
      function mk(cls, idx) {
        var p = global.document.createElement('div');
        p.className = cls;
        p.style.setProperty('--i', String(idx));
        setStyleVars(p, color, transparency);
        return p;
      }
      if (effect === 'wave') {
        for (i = 0; i < 3; i++) out.push(mk('edge-particle edge-wave-trace', i));
      } else if (effect === 'bubble') {
        for (i = 0; i < 4; i++) out.push(mk('edge-particle edge-bubble', i));
      } else if (effect === 'heart') {
        for (i = 0; i < 3; i++) out.push(mk('edge-particle edge-heart', i));
      } else if (effect === 'fireworks') {
        for (i = 0; i < 5; i++) out.push(mk('edge-particle edge-spark', i));
      } else if (effect === 'eclipse') {
        out.push(mk('edge-particle edge-crescent edge-crescent-a', 0));
        out.push(mk('edge-particle edge-crescent edge-crescent-b', 1));
      } else if (effect === 'echo') {
        for (i = 0; i < 3; i++) out.push(mk('edge-particle edge-echo-band', i));
      }
      return out;
    }

    /* One cancellable animation.  A new event while one is running does not
     * spawn a second animation: the bridge coalesces overlaps, and this layer
     * keeps exactly one animation lifecycle. */
    function play(effect, color, opts, meta) {
      // An explicit preview is user-initiated.  It is still bounded and never
      // bypasses reduced-motion/off, but a stale app/presentation layer must not
      // swallow the owner's Preview tap (the reported Edge FX defect).
      var isPreview = !!(meta && meta.preview);
      if (!visibleNow()) {
        if (isPreview) {
          // A preview while the Edge Lighting master switch is off is still a
          // one-shot presentation request; it never enables notifications and
          // never survives beyond its bounded duration.  Sleeping display is a
          // hard refusal: do not wake the panel just to show a preview.
          if (isSleeping()) {
            diag('EDGE_LIGHTING_SUPPRESSED reason=sleeping-preview');
            return null;
          }
        } else {
          diag('EDGE_LIGHTING_SUPPRESSED reason=' + (settings.enabled === false ? 'disabled' : 'sleeping'));
          return null;
        }
      }
      var motion = api.reducedMotionState();
      if (settings.respect_reduced_motion !== false && motion === 'off') {
        diag('EDGE_LIGHTING_SUPPRESSED reason=motion_off');
        return null;
      }
      stop('replace');
      if (isPreview && root) {
        root.classList.add('edge-preview-requested');
        root.style.zIndex = '1000';
      }
      var staticOnly = settings.respect_reduced_motion !== false && motion !== 'full';
      var duration = api.normaliseDuration(opts.duration_ms);
      if (staticOnly) duration = Math.min(duration, 900);
      var spec = buildScene(effect, color, {
        width: opts.width, transparency: opts.transparency, duration_ms: duration
      });
      layer.classList.toggle('edge-static', staticOnly);
      // Force one style flush so animations start from a known initial frame.
      void layer.offsetWidth;
      if (!staticOnly) layer.classList.add('edge-running');
      var timer = setTimeout(function () { stop('complete'); }, duration + 60);
      var desc = {
        effect: effect, seq: meta && meta.seq == null ? null : meta.seq,
        spec: spec, started_at: Date.now(), duration_ms: duration, static: staticOnly,
        cancel: function () {
          clearTimeout(timer);
          layer.classList.remove('edge-running', 'edge-static');
          if (root) {
            root.classList.remove('edge-preview-requested');
            if (root.style) root.style.zIndex = '';
          }
        }
      };
      current = desc;
      diag('EDGE_LIGHTING_PLAY effect=' + effect + ' seq=' + (desc.seq == null ? '-' : desc.seq) +
        ' ms=' + duration + ' static=' + staticOnly + ' color=' + color);
      return desc;
    }

    /* ---------------- journal polling (real notification events) -------- */
    /* Read-only fetches go through the shared bridge client when it is loaded,
       so token/version handling has exactly ONE implementation (no vendored
       token logic in Home).  The direct loopback GET is only the fallback for
       the static preview harness, whose endpoint is unauthenticated locally. */
    function apiFetch(path) {
      var b = global.NuxelBridge;
      // b.get()/b._request() concatenate `apiUrl` (/api/v1) with the endpoint.
      // Passing the full '/edge-lighting' path silently requested
      // /api/v1/edge-lighting/edge-lighting, so the engine kept a legacy
      // document from the unauthenticated fallback (the source_mode bug).
      var endpoint = String(path || '').replace(/^\/api\/v1/, '');
      if (b && typeof b.get === 'function') {
        return Promise.resolve(b.get(endpoint));
      }
      if (b && typeof b._request === 'function') {
        return Promise.resolve(b._request(endpoint, null, 'GET'));
      }
      return fetch(BASE + path, {
        method: 'GET',
        headers: { 'X-Nuxel-Bridge-Version': '1' },
        cache: 'no-store'
      }).then(function (r) { return r.json(); });
    }

    function poll() {
      if (polling || !visibleNow()) return;
      polling = true;
      var cursor = lastSeq;
      apiFetch('/edge-lighting/events?since=' + cursor).then(function (res) {
        polling = false;
        status.lastPollAt = Date.now();
        if (!res || !res.success) { status.provider = 'unavailable'; return; }
        status.provider = 'ok';
        if (cursor === 0) {
          // First contact: adopt the journal head as a baseline.  The journal is
          // shared by every Home/WebKit instance (the live launcher, a preview
          // frame, diagnostics), so replaying entries that predate this tab
          // would make one surface steal another surface's alert.
          if (typeof res.last_seq === 'number' && res.last_seq > lastSeq) lastSeq = res.last_seq;
          return;
        }
        if (typeof res.last_seq === 'number' && res.last_seq < lastSeq) {
          // Journal rotated: resynchronise without replaying old alerts.
          lastSeq = res.last_seq;
          return;
        }
        if (typeof res.last_seq === 'number' && res.last_seq > lastSeq && !list.length) {
          // The journal was trimmed past our cursor: move forward, never replay.
          lastSeq = res.last_seq;
          return;
        }
        var list = Array.isArray(res.events) ? res.events : [];
        for (var i = 0; i < list.length; i++) {
          var ev = list[i];
          if (!ev || typeof ev.seq !== 'number' || ev.seq <= lastSeq) continue;
          lastSeq = ev.seq;
          status.lastEventAt = Date.now();
          applyEvent(ev);
        }
      }, function (err) {
        polling = false;
        if (status.provider !== 'unavailable') diag('EDGE_LIGHTING_POLL_FAIL ' + String((err && err.message) || err));
        status.provider = 'unavailable';
        status.lastError = String((err && err.message) || err);
      });
    }

    function applyEvent(ev) {
      var effective = api.normaliseSettings({
        enabled: settings.enabled, effect: ev.effect, color_mode: ev.color_mode,
        color: ev.color, width: ev.width, transparency: ev.transparency,
        duration_ms: ev.duration_ms, reduced_motion_style: ev.reduced_motion_style
      });
      var color = api.resolveColor(effective, liveThemeAccent(), null);
      return play(effective.effect, color, effective, { seq: ev.seq, app_id: ev.app_id });
    }

    function startPolling() {
      if (pollTimer) return;
      poll();
      pollTimer = setInterval(poll, 2000);
      diag('EDGE_LIGHTING_POLL_START since=' + lastSeq);
    }
    function stopPolling() {
      if (pollTimer) { clearInterval(pollTimer); pollTimer = null; }
    }

    /* ---------------- settings sync ---------------- */
    /* bridge.js is an ES module loaded after this classic script.  Do not
       issue the first settings read against the unauthenticated fallback path:
       that old document shape omits newer fields (source_mode) and the UI then
       silently uses legacy semantics.  Wait briefly for the shared singleton. */
    function bridgeReady() {
      if (global.NuxelBridge && typeof global.NuxelBridge.call === 'function') return Promise.resolve(global.NuxelBridge);
      return new Promise(function (resolve) {
        var done = false;
        function check() {
          if (done) return;
          if (global.NuxelBridge && typeof global.NuxelBridge.call === 'function') {
            done = true; clearInterval(iv); clearTimeout(to); resolve(global.NuxelBridge);
          }
        }
        var iv = setInterval(check, 50);
        var to = setTimeout(function () { if (!done) { done = true; clearInterval(iv); resolve(null); } }, 4000);
        check();
      });
    }

    function loadSettings() {
      return bridgeReady().then(function () { return apiFetch('/edge-lighting'); }).then(function (res) {
        if (res && res.success && res.config) {
          settings = api.normaliseSettings(res.config);
          status.provider = 'ok';
          status.capability = res.capability || null;
          status.dnd = res.dnd || null;
          announce(false);
        }
        return settings;
      }, function () { status.provider = 'unavailable'; return settings; });
    }

    function announce(saved) {
      try {
        global.dispatchEvent(new CustomEvent('nuxel:edge-lighting-changed', {
          detail: { config: clone(settings), capability: status.capability, dnd: status.dnd, saved: !!saved }
        }));
      } catch (e) { /* harness */ }
    }

    function saveSettings(patch) {
      var next = api.normaliseSettings(Object.assign({}, settings, patch || {}));
      var req = (global.NuxelBridge && global.NuxelBridge.call)
        ? global.NuxelBridge.call('edge-lighting', 'set', next)
        : Promise.resolve(null);
      return Promise.resolve(req).then(function (res) {
        if (res && res.success && res.config) settings = api.normaliseSettings(res.config);
        else settings = next;
        // An explicit disable takes effect immediately, including a running effect.
        if (settings.enabled === false) stop('disabled');
        announce(!!(res && res.success));
        return { ok: !!(res && res.success), config: settings, result: res };
      }, function (err) {
        status.lastError = String((err && err.message) || err);
        return { ok: false, config: settings, error: status.lastError };
      });
    }

    /* Make sure wake/unlock plays the configured effect.  The owner chose the
       Nuxel Edge FX as the screen-wake effect; an older settings document (or a
       document written by an app that only knew the notification fields) left
       every lifecycle switch false, so pressing the power button showed the
       lockscreen with no effect.  Enable the two wake switches when they are
       NOT explicitly true and persist the document once.  An explicit `false`
       that was written together with the rest of a complete lifecycle object is
       kept: the owner's Edge FX switches always win. */
    function ensureWakeLifecycle() {
      var lc = settings.lifecycle || {};
      var partial = lc.screen_on !== true || lc.unlock !== true;
      // A complete lifecycle object means the owner (Edge FX / Settings) made a
      // deliberate choice for every switch; never rewrite it.
      if (!partial) return Promise.resolve({ ok: true, changed: false, lifecycle: clone(lc) });
      var next = { screen_on: true, screen_off: !!lc.screen_off, lock: !!lc.lock, unlock: true };
      return saveSettings({ lifecycle: next }).then(function (r) {
        diag('EDGE_LIFECYCLE_WAKE_ENABLED ok=' + (r && r.ok ? 'yes' : 'no'));
        return { ok: !!(r && r.ok), changed: true, lifecycle: clone(settings.lifecycle || next) };
      });
    }

    function preview(effect, opts) {
      opts = opts || {};
      var eff = EFFECTS.indexOf(effect) >= 0 ? effect : settings.effect;
      // An app-supplied presentation override.  Edge FX owns its own colour,
      // width and duration controls; without this a preview rendered the stale
      // Home copy (measured: the app said "Previewing Heart" while the edge
      // showed the previous effect/colour).  Only presentation fields are
      // accepted; notification policy and the enabled flag are never overridden.
      var ov = (opts.settings && typeof opts.settings === 'object') ? opts.settings : {};
      function pick(key) { return ov[key] === undefined ? settings[key] : ov[key]; }
      var ambient = api.normaliseSettings({
        enabled: true, effect: eff, color_mode: pick('color_mode'), color: pick('color'),
        width: pick('width'), transparency: pick('transparency'),
        duration_ms: pick('duration_ms'), respect_reduced_motion: pick('respect_reduced_motion')
      });
      status.lastPreviewAt = Date.now();
      status.lastPreviewError = null;
      var color = api.resolveColor(ambient, liveThemeAccent(), null);
      var desc = play(eff, color, ambient, { seq: null, preview: true });
      var result = { ok: !!desc, effect: eff, color: color, duration_ms: ambient.duration_ms,
                     static: !!(desc && desc.static), notification_state_changed: false,
                     label: 'Preview — no notification was created or changed' };
      if (!desc) {
        // Never report success for an animation that was not rendered: that is
        // exactly the "Preview does nothing" the owner sees.  Say why.
        result.ok = false;
        result.error = isSleeping() ? 'display-asleep' :
          (settings.enabled === false ? 'edge-lighting-off' : 'reduced-motion-suppressed');
        status.lastPreviewError = result.error;
      }
      status.lastPreview = result;
      diag('EDGE_LIGHTING_PREVIEW effect=' + eff + ' ok=' + result.ok + ' surface=' + (opts.surface || 'home'));
      return result;
    }

    /* A same-origin app iframe cannot rely on parent globals being reachable
       before it paints.  This is the explicit, validated message bridge: the
       iframe asks; Home (the single overlay owner) performs the preview. */
    function onAppMessage(ev) {
      if (!ev || ev.source === global) return;
      var origin = global.location && global.location.origin;
      if (origin && ev.origin && ev.origin !== origin) return;
      var msg = ev.data || {};
      if (msg.type === 'nuxel:edge-lighting-preview') {
        var res = preview(String(msg.effect || ''), { surface: 'app-message', settings: msg.settings });
        try { ev.source.postMessage({ type: 'nuxel:edge-lighting-preview-result', request_id: msg.request_id || null, result: res }, origin || '*'); } catch (e) {}
      } else if (msg.type === 'nuxel:edge-lighting-resync') {
        // Edge FX (or Settings) persisted a change through the provider.  The
        // engine's in-memory copy must adopt that authoritative document, or a
        // stale copy competes with the app (measured: provider saved
        // source_mode=all while Home still held the old allowlist).
        if (msg.config && typeof msg.config === 'object') {
          settings = api.normaliseSettings(msg.config);
          announce(true);
        } else {
          loadSettings().then(function () { announce(true); });
        }
        try {
          ev.source.postMessage({ type: 'nuxel:edge-lighting-resync-result', request_id: msg.request_id || null,
            result: { ok: true, config: clone(settings) } }, origin || '*');
        } catch (e) {}
      } else if (msg.type === 'nuxel:edge-panel-open') {
        var side = msg.side === 'right' ? 'right' : 'left';
        var opened = openPanel(side, 'app-message');
        try { ev.source.postMessage({ type: 'nuxel:edge-panel-open-result', request_id: msg.request_id || null, opened: opened, side: side, refusal: status.lastRefusal }, origin || '*'); } catch (e) {}
      }
    }
    /* ---------------- Edge Panel ---------------- */
    function ensurePanel() {
      if (panel && panel.isConnected) return panel;
      panel = global.document.createElement('div');
      panel.id = 'nuxel-edge-panel';
      panel.className = 'edge-panel-root';
      panel.hidden = true;
      panel.innerHTML = '' +
        '<div class="edge-panel-scrim" data-edge-panel-close></div>' +
        '<aside class="edge-panel" role="dialog" aria-modal="true" aria-label="Edge panel">' +
        '  <header class="edge-panel-head">' +
        '    <div class="edge-panel-tabs" role="tablist">' +
        '      <button type="button" role="tab" class="edge-panel-tab active" data-edge-tab="apps" aria-selected="true">Apps</button>' +
        '      <button type="button" role="tab" class="edge-panel-tab" data-edge-tab="notifications" aria-selected="false">Notifications</button>' +
        '    </div>' +
        '    <button type="button" class="edge-panel-close" data-edge-panel-close aria-label="Close Edge panel">\u00d7</button>' +
        '  </header>' +
        '  <div class="edge-panel-body" data-edge-body="apps"><div class="edge-panel-list" data-edge-apps></div></div>' +
        '  <div class="edge-panel-body" data-edge-body="notifications" hidden><div class="edge-panel-list" data-edge-notifs></div></div>' +
        '  <footer class="edge-panel-foot"><span data-edge-panel-status>Edge panel</span></footer>' +
        '</aside>';
      global.document.body.appendChild(panel);
      panelApps = panel.querySelector('[data-edge-apps]');
      panelNotifs = panel.querySelector('[data-edge-notifs]');
      panel.addEventListener('click', function (ev) {
        if (ev.target.closest('[data-edge-panel-close]')) { ev.preventDefault(); closePanel('outside'); return; }
        var tab = ev.target.closest('[data-edge-tab]');
        if (tab) { setTab(tab.getAttribute('data-edge-tab')); return; }
        var app = ev.target.closest('[data-edge-app-id]');
        if (app) {
          var appId = app.getAttribute('data-edge-app-id');
          closePanel('launch');
          var reg = global.appRegistry;
          if (reg && reg.launchApp) {
            try { reg.launchApp(appId); } catch (e) { diag('EDGE_PANEL_LAUNCH_FAILED id=' + appId); }
          }
          return;
        }
        var notif = ev.target.closest('[data-edge-notification-id]');
        if (notif) {
          // Existing canonical notification surface.  The panel itself never
          // marks read or dismisses: that remains the Quick Settings action.
          closePanel('notification');
          try {
            if (global.statusBar && global.statusBar._openNotificationsInQuickSettings) {
              global.statusBar._openNotificationsInQuickSettings();
            }
          } catch (e) {}
        }
      });
      return panel;
    }

    function setTab(name) {
      if (!panel) return;
      var tabs = panel.querySelectorAll('[data-edge-tab]');
      for (var i = 0; i < tabs.length; i++) {
        var on = tabs[i].getAttribute('data-edge-tab') === name;
        tabs[i].classList.toggle('active', on);
        tabs[i].setAttribute('aria-selected', on ? 'true' : 'false');
      }
      var bodies = panel.querySelectorAll('[data-edge-body]');
      for (i = 0; i < bodies.length; i++) bodies[i].hidden = bodies[i].getAttribute('data-edge-body') !== name;
      if (name === 'notifications') renderNotifications();
    }

    function renderApps() {
      if (!panelApps) return;
      var apps = [];
      try {
        if (global.appRegistry && global.appRegistry.getAllApps) apps = global.appRegistry.getAllApps() || [];
      } catch (e) { apps = []; }
      // Canonical registry only.  No placeholder apps, no invented icon paths.
      apps = apps.filter(function (a) { return a && a.id && a.name; });
      apps.sort(function (a, b) { return String(a.name).localeCompare(String(b.name)); });
      panelApps.innerHTML = apps.map(function (a) {
        var icon = a.icon || '\u2022';
        var glyph;
        if (/^(https?:|\/|\.\.?\/)/.test(String(icon))) {
          glyph = '<img src="' + escHtml(icon) + '" alt="" draggable="false">';
        } else {
          glyph = '<span class="edge-app-glyph" aria-hidden="true">' + escHtml(icon) + '</span>';
        }
        return '<button type="button" class="edge-panel-app" data-edge-app-id="' + escHtml(a.id) + '">' +
          '<span class="edge-app-icon" style="--edge-app-color:' + escHtml(a.color || '#78909c') + '">' + glyph + '</span>' +
          '<span class="edge-app-name">' + escHtml(a.name) + '</span></button>';
      }).join('') || '<p class="edge-panel-empty">The app registry is unavailable</p>';
    }

    function renderNotifications() {
      if (!panelNotifs) return;
      if (isLocked()) {
        panelNotifs.innerHTML = '<p class="edge-panel-empty">Notifications are hidden while the device is locked</p>';
        return;
      }
      var list = [];
      try {
        list = (global.statusBar && global.statusBar.state && global.statusBar.state.notifications) || [];
      } catch (e) { list = []; }
      list = list.filter(function (n) { return n && !n.archived_at; }).slice(0, 30);
      panelNotifs.innerHTML = list.map(function (n) {
        var unread = !n.read_at;
        return '<button type="button" class="edge-panel-notif' + (unread ? ' unread' : '') +
          '" data-edge-notification-id="' + escHtml(n.id) + '">' +
          '<span class="edge-panel-notif-app">' + escHtml(n.app_name || n.app_id || 'System') + '</span>' +
          (n.summary ? '<span class="edge-panel-notif-title">' + escHtml(n.summary) + '</span>' : '') + '</button>';
      }).join('') || '<p class="edge-panel-empty">No notifications</p>';
      if (!list.length && global.statusBar && global.statusBar._pollNotifications) {
        try { global.statusBar._pollNotifications(); } catch (e) {}
      }
    }

    function refusePanel(reason) {
      status.lastRefusal = { reason: reason, at: Date.now() };
      diag('EDGE_PANEL_REFUSED reason=' + reason);
      return false;
    }

    function openPanel(side, how) {
      // A refusal is a real outcome (not a silent false): the reason is kept in
      // status()/diag so an owner or diagnostic can see why the panel did not open.
      if (panelOpen) {
        // A stale "open" flag with no visible panel would wedge the feature;
        // the DOM is authoritative.
        if (panel && panel.isConnected && !panel.hidden) return refusePanel('already-open');
        panelOpen = false;
        if (global.document.body) global.document.body.classList.remove('edge-panel-open');
        diag('EDGE_PANEL_STATE_RECOVERED stale-open-flag');
      }
      if (isSleeping() || !global.document.body) return refusePanel('display-off');
      // The Apps drawer and the Quick Settings shade already own these layers;
      // opening the Edge panel over them would stack two gestures on one screen.
      if (global.launcher && global.launcher.drawerOpen) return refusePanel('drawer-open');
      // Only an OPEN shade blocks the panel: window.qs exposes a method named
      // open(), so a truthiness test would refuse every panel permanently.
      var qsOpen = false;
      try {
        // qs.js maintains `level` (0 = closed, 2 = compact, 3 = extended) as the
        // authoritative shade state; the method `open` must never be truth-tested.
        if (global.qs) qsOpen = typeof global.qs.level === 'number' ? global.qs.level > 0 : false;
      } catch (e) { qsOpen = false; }
      if (qsOpen) return refusePanel('quick-settings-open');
      var body = global.document.body;
      if (!panel) ensurePanel();
      panelSide = side === 'right' ? 'right' : 'left';
      panel.classList.toggle('from-right', panelSide === 'right');
      panel.hidden = false;
      panelOpen = true;
      body.classList.add('edge-panel-open');
      renderApps();
      setTab('apps');
      status.lastOpen = { side: panelSide, how: how || 'gesture', at: Date.now() };
      status.lastRefusal = null;
      diag('EDGE_PANEL_OPEN side=' + panelSide + ' how=' + (how || 'gesture'));
      try {
        global.dispatchEvent(new CustomEvent('nuxel:edge-panel', {
          detail: { open: true, side: panelSide, how: how || 'gesture' }
        }));
      } catch (e) {}
      return true;
    }

    function closePanel(how) {
      if (!panelOpen || !panel) return false;
      panelOpen = false;
      panel.hidden = true;
      global.document.body.classList.remove('edge-panel-open');
      status.lastClose = { how: how || 'close', at: Date.now() };
      diag('EDGE_PANEL_CLOSE how=' + (how || 'close'));
      try {
        global.dispatchEvent(new CustomEvent('nuxel:edge-panel', {
          detail: { open: false, how: how || 'close' }
        }));
      } catch (e) {}
      return true;
    }

    function togglePanel(side) {
      if (panelOpen) return closePanel('toggle');
      return openPanel(side || panelSide, 'accessible');
    }

    /* ---------------- lifecycle wiring ---------------- */
    function wire() {
      global.addEventListener('message', onAppMessage, false);
      global.addEventListener('resize', function () { if (panelOpen) renderApps(); });
      global.addEventListener('orientationchange', function () {
        closePanel('orientation');
        stop('orientation');
      });
      global.addEventListener('blur', function () { closePanel('blur'); });
      global.addEventListener('nuxel:display-sleep', function () { closePanel('sleep'); stop('sleep'); });
      global.addEventListener('nuxel:screen-off', function () {
        closePanel('screen-off');
        // The display is about to blank: a lifecycle pulse gets the one
        // frame-duration window the renderer still has, then stop() runs.
        if (lifecycleWanted('screen_off')) playLifecycle('screen_off');
        stop('screen-off');
      });
      global.addEventListener('nuxel:display-on', function () {
        // The launcher only knows the panel woke after its status sample; keep
        // the pre-wake body class from suppressing the effect.
        var b = global.document.body;
        if (b && b.classList) { b.classList.remove('screen-off', 'screen-sleep'); }
        if (lifecycleWanted('screen_on')) playLifecycle('screen_on');
      });
      global.document.addEventListener('nuxel:lockscreen-shown', function () {
        if (lifecycleWanted('lock')) playLifecycle('lock');
      });
      global.document.addEventListener('nuxel:lockscreen-hidden', function () {
        if (lifecycleWanted('unlock')) playLifecycle('unlock');
      });
      global.document.addEventListener('keydown', function (ev) {
        // Back closes the panel only while the panel is the open surface.
        if ((ev.key === 'Escape' || ev.key === 'BrowserBack') && panelOpen) {
          ev.preventDefault();
          ev.stopPropagation();
          closePanel('back');
        }
      }, true);
      global.document.addEventListener('visibilitychange', function () {
        // A85: focus visibility is not display sleep.  Stop polling only when
        // the Nuxel display layer really went to sleep; otherwise keep the
        // notification journal watch alive (it is a plain 2 s local fetch).
        if (isSleeping()) { closePanel('hidden'); stop('hidden'); stopPolling(); }
        else startPolling();
      });
      ['pointercancel', 'touchcancel'].forEach(function (name) {
        global.document.addEventListener(name, function () {
          if (global.NuxelEdgePanelGesture) global.NuxelEdgePanelGesture.cancel(name);
        }, { capture: true, passive: true });
      });
      global.addEventListener('nuxel:qs-open', function () { closePanel('quick-settings'); });
      global.addEventListener('nuxel:overlay-changed', function () {
        // The Applications drawer or another Home overlay took the screen.
        if (panelOpen && global.launcher && global.launcher.drawerOpen) closePanel('overlay');
      });
    }

    function installApi() {
      api.getSettings = function () { return clone(settings); };
      api.status = function () {
        return {
          settings: clone(settings), provider: status.provider, capability: status.capability,
          dnd: status.dnd, lastError: status.lastError, lastEventAt: status.lastEventAt,
          lastPreviewAt: status.lastPreviewAt, lastPollAt: status.lastPollAt, seq: lastSeq,
          lastOpen: status.lastOpen || null, lastClose: status.lastClose || null,
          lastRefusal: status.lastRefusal || null, lastPreview: status.lastPreview || null,
          lastPreviewError: status.lastPreviewError || null,
          active: current ? {
            effect: current.effect, seq: current.seq, static: current.static,
            remaining_ms: Math.max(0, current.duration_ms - (Date.now() - current.started_at))
          } : null
        };
      };
      api.applySettings = saveSettings;
      api.syncConfig = function (config) {
        // Adopt a document that a same-origin app just persisted.  No write.
        if (!config || typeof config !== 'object') return clone(settings);
        settings = api.normaliseSettings(config);
        announce(false);
        return clone(settings);
      };
      api.ensureWakeLifecycle = ensureWakeLifecycle;
      api.reload = loadSettings;
      api.preview = preview;
      api.stop = function (reason) { stop(reason || 'api'); };
      api.themeAccent = liveThemeAccent;
      api.openPanel = openPanel;
      api.closePanel = closePanel;
      api.togglePanel = togglePanel;
      api.isPanelOpen = function () { return panelOpen; };
      api._diag = function () {
        return {
          panelOpen: panelOpen, sleeping: isSleeping(), hasBody: !!global.document.body,
          drawer: !!(global.launcher && global.launcher.drawerOpen),
          qsLevel: (global.qs || {}).level, lastRefusal: status.lastRefusal,
          panelConnected: !!(panel && panel.isConnected), panelHidden: panel ? panel.hidden : null,
          body: global.document.body ? global.document.body.className : null
        };
      };
      api.pollOnce = poll;
      // Edge FX / Settings live in the same UI stack and use the one engine.
      api.effects = EFFECTS;
      api.lifecycle = function () { return clone(settings.lifecycle || {}); };
      api.playLifecycle = playLifecycle;
      api.labels = EFFECT_LABELS;
      api.defaultAccent = DEFAULT_ACCENT;
      api._test = {
        applyEvent: applyEvent,
        play: play,
        pollFailure: function (why) { status.provider = 'unavailable'; status.lastError = why; },
        setSettings: function (s) { settings = api.normaliseSettings(s); }
      };
    }

    function boot() {
      try { wire(); } catch (e) { diag('EDGE_LIGHTING_WIRE_FAIL ' + (e && e.message)); }
      try { installApi(); } catch (e) { diag('EDGE_LIGHTING_API_FAIL ' + (e && e.message)); }
      // A85: notification Edge FX must survive a settings hiccup.  Previously a
      // rejected loadSettings()/ensureWakeLifecycle() skipped startPolling()
      // for the rest of the session: the journal had events, the overlay never
      // polled, and no notification produced an edge effect.  Polling is the
      // product feature; configuration is optional, so it always starts.
      startPolling();
      loadSettings().then(function () {
        return ensureWakeLifecycle();
      }).catch(function (e) {
        diag('EDGE_LIGHTING_BOOT_DEGRADED ' + (e && (e.message || e)));
        return null;
      }).then(function () {
        diag('EDGE_LIGHTING_READY effect=' + settings.effect + ' provider=' + status.provider +
          ' accent=' + liveThemeAccent() + ' polling=' + (pollTimer ? 'yes' : 'no'));
      });
    }

    if (global.document.readyState === 'loading') {
      global.document.addEventListener('DOMContentLoaded', boot, { once: true });
    } else {
      boot();
    }
  }

})(typeof window !== 'undefined' ? window : this);
