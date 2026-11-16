/* Nuxel Edge FX (PWNAGE-103000)
 *
 * The installable app surface for Edge Lighting + the Edge Panel:
 *   - enable/disable, pick and preview any of the eight effects;
 *   - colour mode, width, transparency, duration, DND / reduced-motion policy,
 *     screen-state capability (screen-off is reported unavailable, not faked);
 *   - notification source allowlist from the CANONICAL registry;
 *   - open the Edge panel from either side;
 *   - uninstall / reinstall this app through the canonical app registry RPC
 *     (`apps` namespace, owner-gated to Home / Settings / NuxTore on the host).
 *
 * All state lives in the one Edge Lighting document owned by the bridge
 * provider; this page never writes a file and never touches an LED.
 */
(function () {
  'use strict';
  var FALLBACK_EFFECTS = ['basic', 'wave', 'bubble', 'multicolor', 'heart', 'fireworks', 'eclipse', 'echo'];
  var LABELS = { basic: 'Basic', wave: 'Wave', bubble: 'Bubble', multicolor: 'Multicolor',
                 heart: 'Heart', fireworks: 'Fireworks', eclipse: 'Eclipse', echo: 'Echo' };
  var PRESETS = ['#63f0bd', '#4aa8ff', '#ffb454', '#ff6b6b', '#c77dff', '#ffffff', '#ff8fab'];
  var APP_ID = 'nuxel-edge-fx';
  var START_URL = '/pwa/nuxel-apps/edge-fx/index.html';
  var $ = function (id) { return document.getElementById(id); };
  var settings = null, capability = null, effects = FALLBACK_EFFECTS, registryApps = [];
  var fixtureMode = /(?:^|[?&])fixture=1(?:&|$)/.test(String(window.location.search || ''));

  var API_BASE = window.NUXEL_API_URL || 'http://127.0.0.1:8080/api/v1';
  /* Prefer the shared bridge client (version pin + session token).  A plain
     bootstrap-token fetch is the fallback on the local loopback API so the
     effect picker still works if the ES module failed to load; a version-skew
     refusal from the shared client is never masked. */
  function bridge() { return window.NuxelBridge; }

  /* bridge.js is loaded as an ES module AFTER this classic script in the page
     markup.  The old code therefore saw `undefined` for the first save (and
     near-instantly on fast taps) and reported a failure even though the
     provider was healthy.  Wait for the shared singleton instead of racing it. */
  function bridgeReady(timeoutMs) {
    var b = bridge();
    if (b && typeof b.call === 'function') return Promise.resolve(b);
    return new Promise(function (resolve) {
      var done = false;
      function check() {
        if (done) return;
        var now = bridge();
        if (now && typeof now.call === 'function') {
          done = true; clearInterval(iv); clearTimeout(to); resolve(now);
        }
      }
      var iv = setInterval(check, 50);
      var to = setTimeout(function () {
        if (done) return;
        done = true; clearInterval(iv);
        // A plain loopback RPC is still a real bridge (with its own session
        // token); only fall back to it when the shared client never loaded.
        resolve(null);
      }, timeoutMs == null ? 4000 : timeoutMs);
      check();
    });
  }

  function isMock(res) {
    // The SHARED bridge client falls back to fabricated mock data when its RPC
    // cannot be reached.  For this page a mock answer is indistinguishable from
    // a silent failure: "Allow all apps" then looks accepted while nothing was
    // persisted (measured on a host whose origin was not on the bridge's CORS
    // allowlist).  Never treat a mock as a real provider reply.
    return !!(res && typeof res === 'object' && res.mock === true);
  }
  function call(ns, verb, params) {
    return bridgeReady().then(function (b) {
      if (b && b.call) {
        return Promise.resolve(b.call(ns, verb, params || {})).then(function (res) {
          return isMock(res) ? fetchApi(ns, verb, params) : res;
        });
      }
      return fetchApi(ns, verb, params);
    });
  }

  var token = null;
  function apiFetch(path, opts) {
    opts = opts || {};
    opts.headers = opts.headers || { 'Content-Type': 'application/json', 'X-Nuxel-Bridge-Version': '1' };
    if (token) opts.headers.Authorization = 'Bearer ' + token;
    opts.cache = 'no-store';
    return fetch(API_BASE + path, opts).then(function (r) {
      return r.json().then(function (body) {
        if (!r.ok) {
          var e = new Error('HTTP ' + r.status + (body && body.error ? ' (' + body.error + ')' : ''));
          e.body = body;
          throw e;
        }
        return body;
      });
    });
  }
  function fetchApi(ns, verb, params) {
    if (token) return rpc();
    return apiFetch('/auth/token', {
      method: 'POST', body: JSON.stringify({ app_id: 'nuxel-edge-fx' })
    }).then(function (res) { token = (res && res.token) || ''; return rpc(); });
    function rpc() {
      return apiFetch('/rpc', {
        method: 'POST',
        body: JSON.stringify({ app_id: 'nuxel-edge-fx', namespace: ns, verb: verb, params: params || {} })
      }).then(function (res) { return (res && res.result !== undefined) ? res.result : res; });
    }
  }

  function say(msg) { var el = $('state'); if (el) el.textContent = msg; }
  function DEFAULTS() {
    var e = homeEngine();
    return (e && e.DEFAULTS) ? e.DEFAULTS : { effect: 'wave' };
  }

  /* Preview must be visible even though this app's full-screen iframe is above
     Home's edge overlay.  Ask the single overlay owner through a same-origin
     postMessage (validated by Home); fall back to the direct parent call only
     when there is no message bridge. */
  var previewSeq = 0;
  /* Presentation-only override so the app's visible colour/width/duration are
     what the owner previews (Home keeps the persisted copy). */
  function previewSettings(effect) {
    var s = settings || {};
    return {
      effect: effect,
      color_mode: s.color_mode, color: s.color,
      width: s.width, transparency: s.transparency,
      duration_ms: s.duration_ms, respect_reduced_motion: s.respect_reduced_motion
    };
  }
  function previewEffect(effect) {
    var reqId = 'fx-' + (++previewSeq) + '-' + Date.now();
    return new Promise(function (resolve) {
      var settled = false, timer = null;
      function finish(res) {
        if (settled) return;
        settled = true;
        if (timer) clearTimeout(timer);
        window.removeEventListener('message', onReply);
        resolve(res || { ok: false, error: 'preview unavailable' });
      }
      function onReply(ev) {
        if (!ev || ev.source !== window.parent) return;
        var d = ev.data || {};
        if (d.type !== 'nuxel:edge-lighting-preview-result' || d.request_id !== reqId) return;
        finish(d.result);
      }
      window.addEventListener('message', onReply);
      try {
        if (window.parent && window.parent !== window) {
          window.parent.postMessage({ type: 'nuxel:edge-lighting-preview', effect: effect,
            settings: previewSettings(effect), request_id: reqId }, window.location.origin);
        }
      } catch (e) { /* fall through to the direct call */ }
      timer = setTimeout(function () {
        if (settled) return;
        var engine = homeEngine();
        if (engine && engine.preview) {
          finish(engine.preview(effect, { allowWhileDisabled: true, settings: previewSettings(effect) }) ||
            { ok: false, error: 'preview refused' });
        } else finish({ ok: false, error: 'Home preview bridge unavailable' });
      }, 450);
    });
  }

  /* The Home engine is the single source of effect names/labels.  Reach it
     through the framing Home document (same origin on the phone) and fall back
     to the local list only when there is no Home frame (desktop preview). */
  function homeEngine() {
    try {
      var p = window.parent;
      if (p && p !== window && p.NuxelEdgeLighting && p.NuxelEdgeLighting.effects) return p.NuxelEdgeLighting;
    } catch (e) { /* cross-origin */ }
    return null;
  }
  /* Use Home's shipped engine functions directly for normalisation/registry.
     The app frame is same-origin; the provider remains the single persistence
     owner, so this shares code without introducing a second state store. */
  function engineFn(name, fallback) {
    var e = homeEngine();
    return (e && typeof e[name] === 'function') ? e[name] : fallback;
  }
  (function adoptEngine() {
    var engine = homeEngine();
    if (!engine) return;
    effects = engine.effects.slice();
    engine.effects.forEach(function (e) { LABELS[e] = engine.labels[e] || LABELS[e] || e; });
  })();

  function renderEffects() {
    var host = $('effects');
    host.textContent = '';
    effects.forEach(function (eff) {
      var tile = document.createElement('button');
      tile.type = 'button';
      tile.className = 'effect-tile';
      tile.setAttribute('role', 'radio');
      tile.setAttribute('data-effect', eff);
      tile.setAttribute('aria-checked', settings && settings.effect === eff ? 'true' : 'false');
      var sample = '<span class="fx-sample fx-' + eff + '">';
      var count = eff === 'wave' || eff === 'bubble' || eff === 'heart' || eff === 'fireworks' || eff === 'echo' ? 3 : 1;
      for (var i = 0; i < count; i++) sample += '<i></i>';
      sample += '</span>';
      tile.innerHTML = sample + '<span class="fx-name">' + LABELS[eff] + (eff === 'wave' ? ' (default)' : '') + '</span>';
      tile.addEventListener('click', function () {
        // Preview first on the real display, then persist the selection.  A
        // suppressed preview (master off / display asleep) must never prevent
        // the selection itself from being saved.
        var commit = fixtureMode ? Promise.resolve(false) : save({ effect: eff }, 'Effect ' + LABELS[eff]);
        commit.then(function (ok) {
          return previewEffect(eff).then(function (res) {
            say('Effect: ' + LABELS[eff] + (ok ? ' — saved' : ' — not saved') +
                (res && res.ok === false ? ' · preview: ' + (res.error || 'unavailable') : ' · previewed'));
          });
        });
      });
      host.appendChild(tile);
    });
  }

  function renderSwatches() {
    var host = $('swatches');
    host.textContent = '';
    PRESETS.forEach(function (c) {
      var b = document.createElement('button');
      b.type = 'button';
      b.style.background = c;
      b.setAttribute('aria-label', 'Colour ' + c);
      b.setAttribute('aria-pressed', settings && String(settings.color).toLowerCase() === c ? 'true' : 'false');
      b.addEventListener('click', function () { save({ color_mode: 'preset', color: c }); });
      host.appendChild(b);
    });
  }

  var sourcesBusy = false;
  function allowedList() {
    if (!settings) return [];
    var a = settings.allowed_apps;
    // `null` is this UI's explicit clear-filter marker.
    if (a === null || a === undefined) return [];
    return Array.isArray(a) ? a : [];
  }
  function isAllowAll() {
    if (!settings) return true;
    // Explicit persisted mode.  If a stale/legacy provider response omits it,
    // an empty allowlist is All apps; a non-empty one is an allowlist.
    if (settings.source_mode === 'all' || settings.source_mode === 'allowlist') {
      return settings.source_mode === 'all';
    }
    return !allowedList().length;
  }
  function sourceState(configured) {
    var allowed = allowedList();
    if (isAllowAll()) return 'All apps';
    if (!allowed.length) return 'All apps';
    return allowed.length + ' of ' + (registryApps.length || '?') + ' apps';
  }
  function renderSources() {
    var host = $('sources');
    host.textContent = '';
    var allowed = allowedList();
    var allowAll = isAllowAll();
    // In All apps mode the explicit allowlist is genuinely empty; showing 48
    // checked rows made it impossible for the owner to see what Allow all did.
    registryApps.slice(0, 80).forEach(function (app) {
      var label = document.createElement('label');
      var cb = document.createElement('input');
      cb.type = 'checkbox';
      cb.checked = !allowAll && allowed.indexOf(app.id) >= 0;
      cb.disabled = sourcesBusy;
      cb.addEventListener('change', function () {
        if (sourcesBusy) return;
        // Read the authoritative current list, not the closure captured when
        // this row was rendered.  Sequential row changes used to overwrite one
        // another (the last click won), which is why "Allow all apps" seemed to
        // do nothing.
        // Read the event's resulting check state explicitly.  From All apps:
        //   * checking one row means "only this app"
        //   * unchecking one row means "every app except this one"
        // (The previous full-list materialisation inverted the uncheck case.)
        var current;
        if (isAllowAll()) {
          current = cb.checked
            ? [app.id]
            : registryApps.map(function (a) { return a.id; }).filter(function (id) { return id !== app.id; });
        } else {
          current = allowedList().slice();
          var i = current.indexOf(app.id);
          if (cb.checked && i < 0) current.push(app.id);
          if (!cb.checked && i >= 0) current.splice(i, 1);
        }
        if (!current.length) {
          cb.checked = true;
          say('At least one source must stay selected; tap “Allow all apps” to clear filtering.');
          return;
        }
        sourcesBusy = true;
        say('Saving notification sources…');
        // Any explicit per-app selection ends ALL-APPS mode.
        save({ source_mode: 'allowlist', allowed_apps: current, blocked_apps: [] }).then(function (ok) {
          sourcesBusy = false;
          if (!ok) cb.checked = !cb.checked;
          say(ok ? 'Notification sources: ' + sourceState(true) : 'Could not save sources');
          renderSources();
        });
      });
      label.appendChild(cb);
      label.appendChild(document.createTextNode(app.name || app.id));
      host.appendChild(label);
    });
    var emptyHint = $('sources-empty');
    if (emptyHint) emptyHint.hidden = !allowAll;
    if (!registryApps.length) host.textContent = 'App registry unavailable — source filtering stays unchanged.';
    var summary = $('sources-summary');
    if (summary) summary.textContent = 'Currently: ' + sourceState(true) + '.';
  }

  function fill(s) {
    // A fixture page (/index.html?fixture=1) only proves the UI; it must never
    // write the real persisted document.
    if (fixtureMode) s = Object.assign({}, s, { enabled: true, effect: DEFAULTS().effect,
      color_mode: 'theme', color: null, width: 'medium', transparency: 'medium',
      duration_ms: 1800, respect_dnd: true, respect_reduced_motion: true,
      source_mode: 'all', allowed_apps: [], blocked_apps: [] });
    settings = s;
    if ($('enabled')) $('enabled').checked = !!s.enabled;
    if ($('color-mode')) $('color-mode').value = s.color_mode || 'theme';
    if ($('width')) $('width').value = s.width || 'medium';
    if ($('transparency')) $('transparency').value = s.transparency || 'medium';
    if ($('duration')) $('duration').value = s.duration_ms;
    if ($('duration-out')) $('duration-out').textContent = (s.duration_ms / 1000).toFixed(1) + ' s';
    if ($('dnd')) $('dnd').checked = s.respect_dnd !== false;
    if ($('rm')) $('rm').checked = s.respect_reduced_motion !== false;
    if ($('screen-mode')) $('screen-mode').value = 'screen_on';
    // Lifecycle toggles: a missing/legacy document means all four OFF (the
    // pre-PWNAGE-SSP behaviour), never "on because the key was absent".
    var lc = (s.lifecycle && typeof s.lifecycle === 'object') ? s.lifecycle : {};
    [['lc-screen-on', 'screen_on'], ['lc-screen-off', 'screen_off'],
     ['lc-lock', 'lock'], ['lc-unlock', 'unlock']].forEach(function (pair) {
      if ($(pair[0])) $(pair[0]).checked = lc[pair[1]] === true;
    });
    if ($('custom-color') && s.color) $('custom-color').value = s.color;
    $('swatches').hidden = s.color_mode !== 'preset';
    $('custom-row').hidden = s.color_mode !== 'custom';
    renderEffects();
    renderSwatches();
    renderSources();
  }

  /* Writes are serialized: two quick taps must not interleave and leave the
     UI showing a document the provider never accepted. */
  var saveChain = Promise.resolve();
  function save(patch, label) {
    if (fixtureMode) return Promise.resolve(false);
    function run() {
      return call('edge-lighting', 'set', patch).then(function (res) {
        if (res && res.success && res.config) {
          // Some cached/legacy provider responses omit newer schema fields.
          // Do not let that re-enter legacy all-apps semantics: an explicit
          // Allow-all patch always renders as all.
          var cfg = res.config;
          if (!('source_mode' in cfg) && patch && ('source_mode' in patch || (Array.isArray(patch.allowed_apps) && !patch.allowed_apps.length))) {
            cfg = Object.assign({}, cfg, { source_mode: patch.source_mode || 'all' });
          }
          fill(cfg);
          notifyHome(cfg);
          return true;
        }
        say(notSaved(res, label));
        return false;
      }, function (err) {
        say('Not saved' + (label ? ' (' + label + ')' : '') + ': ' +
            ((err && (err.message || err.code)) || 'bridge error'));
        return false;
      });
    }
    var next = saveChain.then(run, run);
    saveChain = next.then(function () {}, function () {});
    return next;
  }

  /* Every failure keeps the cause: the provider's own reason, a load-state
     hiccup (the page was opened before its first status read finished), or a
     bridge refusal.  "Could not save" with no cause was unactionable. */
  function notSaved(res, label) {
    var why = (res && (res.error || res.detail)) ||
      (settings ? 'provider refused the change' : 'settings not loaded yet — wait a moment and tap again');
    return 'Not saved' + (label ? ' (' + label + ')' : '') + ': ' + why;
  }

  /* The single persisted config also feeds Home's overlay engine.  Tell that
     engine to adopt the provider's authoritative document so its copy can never
     disagree with this page (the "Allow all apps did nothing" defect: the
     provider saved source_mode=all while Home still held an allowlist). */
  var syncSeq = 0;
  function notifyHome(cfg) {
    if (!cfg) return;
    try {
      if (window.parent && window.parent !== window) {
        window.parent.postMessage({ type: 'nuxel:edge-lighting-resync', config: cfg,
          request_id: 'resync-' + (++syncSeq) }, window.location.origin);
      }
    } catch (e) { /* cross-origin: nothing to sync */ }
    var engine = homeEngine();
    if (engine && engine.syncConfig) {
      try { engine.syncConfig(cfg); } catch (e) { /* engine owns its own state */ }
    }
  }

  function loadStatus() {
    return call('edge-lighting', 'status', {}).then(function (res) {
      if (!res || !res.success) {
        say('Edge lighting provider unavailable: ' + ((res && res.error) || 'no response'));
        return;
      }
      capability = res.capability || null;
      if (capability && capability.effects_supported) effects = capability.effects_supported;
      fill(res.config || {});
      var lines = [];
      lines.push('Effect: ' + LABELS[settings.effect] + ' · ' + (settings.enabled ? 'enabled' : 'off') +
        ' · ' + settings.duration_ms + ' ms');
      lines.push('DND: ' + (res.dnd && res.dnd.active ? 'active (' + res.dnd.reason + ')' : 'off') +
        ' · provider: ' + (res.last_error ? 'last error: ' + res.last_error : 'ok'));
      say(lines.join('\n'));
      if (capability && $('capability')) {
        var modes = (capability.screen_modes || []).map(function (m) {
          return m.id + ': ' + (m.available ? 'available' : 'unavailable');
        }).join(' · ');
        $('capability').textContent = 'AMOLED display effect, not a hardware LED. Screen modes — ' + modes;
        var off = (capability.screen_modes || []).filter(function (m) { return m.id === 'screen_off'; })[0];
        if ($('screen-note')) $('screen-note').textContent = off && off.reason ? off.reason : '';
      }
    }, function (err) {
      say('Edge lighting provider unavailable: ' + (err && err.message ? err.message : 'bridge error'));
    });
  }

  function refreshStatus(quiet) {
    return call('edge-lighting', 'status', {}).then(function (res) {
      if (res && res.success && res.config) {
        fill(res.config);
        if (!quiet) {
          say('Effect: ' + LABELS[res.config.effect] + ' · ' + (res.config.enabled ? 'enabled' : 'off') +
              ' · ' + res.config.duration_ms + ' ms');
        }
      }
      return res;
    }, function () { return null; });
  }

  function loadRegistry() {
    return call('apps', 'inventory', {}).then(function (res) {
      var list = (res && res.apps) || [];
      registryApps = list.map(function (a) { return { id: a.id, name: a.name || a.id, state: a.state }; });
      var me = list.filter(function (a) { return a.id === APP_ID; })[0];
      var installed = !!(me && me.registered !== false);
      $('install-state').textContent = installed
        ? 'Installed (state: ' + (me.state || 'registered') + '). Uninstall removes only the launcher entry.'
        : 'Uninstalled — this app is no longer in the launcher. “Install / reinstall” adds it back; your settings and the Edge engine stay.';
      $('uninstall').disabled = !installed;
      $('reinstall').disabled = false;
      renderSources();
    }, function (err) {
      $('install-state').textContent = 'Registry unavailable: ' + (err && err.message ? err.message : 'bridge error');
    });
  }

  function bind() {
    $('close').addEventListener('click', function () {
      try { if (window.parent && window.parent !== window && window.parent.nuxel && window.parent.nuxel.home) window.parent.nuxel.home(); } catch (e) {}
      try { history.back(); } catch (e) {}
    });
    $('enabled').addEventListener('change', function () {
      save({ enabled: $('enabled').checked }).then(function (ok) { if (ok) say('Edge lighting ' + ($('enabled').checked ? 'on' : 'off')); });
    });
    $('color-mode').addEventListener('change', function () {
      var mode = $('color-mode').value;
      $('swatches').hidden = mode !== 'preset';
      $('custom-row').hidden = mode !== 'custom';
      save({ color_mode: mode, color: mode === 'theme' ? null : (settings.color || $('custom-color').value) });
    });
    $('custom-color').addEventListener('change', function () {
      save({ color_mode: 'custom', color: $('custom-color').value });
    });
    $('width').addEventListener('change', function () { save({ width: $('width').value }); });
    $('transparency').addEventListener('change', function () { save({ transparency: $('transparency').value }); });
    $('duration').addEventListener('input', function () {
      $('duration-out').textContent = (parseInt($('duration').value, 10) / 1000).toFixed(1) + ' s';
    });
    $('duration').addEventListener('change', function () { save({ duration_ms: parseInt($('duration').value, 10) }); });
    $('dnd').addEventListener('change', function () { save({ respect_dnd: $('dnd').checked }); });
    $('rm').addEventListener('change', function () { save({ respect_reduced_motion: $('rm').checked }); });
    // Partial lifecycle updates: send the whole object so the provider's
    // strict-boolean normaliser never has to guess the other three.
    function saveLifecycle() {
      save({ lifecycle: {
        screen_on: !!($('lc-screen-on') && $('lc-screen-on').checked),
        screen_off: !!($('lc-screen-off') && $('lc-screen-off').checked),
        lock: !!($('lc-lock') && $('lc-lock').checked),
        unlock: !!($('lc-unlock') && $('lc-unlock').checked)
      } });
    }
    ['lc-screen-on', 'lc-screen-off', 'lc-lock', 'lc-unlock'].forEach(function (id) {
      if ($(id)) $(id).addEventListener('change', saveLifecycle);
    });
    $('sources-clear').addEventListener('click', function () {
      if (sourcesBusy) return;
      sourcesBusy = true;
      // Persist the empty allowlist; the returned config is then normalised to
      // the same empty list, so no checkbox can be resurrected from a closure.
      save({ source_mode: 'all', allowed_apps: [], blocked_apps: [] }, 'Allow all apps').then(function (ok) {
        if (ok) {
          // The provider response is the truth: refresh the persisted document,
          // not only a local flag, before re-rendering the list.
          return refreshStatus(true).then(function (res) {
            sourcesBusy = false;
            var cfg = res && res.success ? res.config : settings;
            var all = !!(cfg && (cfg.source_mode === 'all' ||
              (cfg.source_mode !== 'allowlist' && !(cfg.allowed_apps || []).length)));
            say(all ? 'Notification sources: All apps may now light the edge.'
                    : 'Allow all apps was not persisted — the provider still reports ' +
                      ((cfg && (cfg.source_mode || 'unknown')) + '.'));
            renderSources();
            return all;
          }, function (err) {
            // The save itself already succeeded; only the read-back failed.
            // Say exactly that instead of implying the change was lost.
            sourcesBusy = false;
            say('Allow all apps was saved, but the read-back failed' +
                (err && err.message ? ' (' + err.message + ')' : '') + '. Tap it again to confirm.');
            renderSources();
            return false;
          });
        }
        sourcesBusy = false;
        say('Could not save sources');
        renderSources();
        return false;
      });
    });
    $('preview').addEventListener('click', function () {
      if (!settings) { say('Preview unavailable: settings are still loading.'); return; }
      $('preview').disabled = true;
      previewEffect(settings.effect).then(function (res) {
        $('preview').disabled = false;
        if (res && res.ok) {
          say('Previewing ' + LABELS[res.effect || settings.effect] + ' — no notification was created or changed.');
        } else {
          var why = (res && (res.error || res.detail)) || 'Home did not acknowledge the request';
          var hints = {
            'edge-lighting-off': ' (Edge lighting is off — enable it to preview.)',
            'display-asleep': ' (The display is off; wake the phone first.)',
            'reduced-motion-suppressed': ' (Reduced motion is set to off.)',
            'suppressed': settings.enabled === false ? ' (Edge lighting is off — enable it to preview.)' : ''
          };
          say('Preview unavailable: ' + why + (hints[why] || ''));
        }
      });
    });
    $('reset').addEventListener('click', function () {
      call('edge-lighting', 'reset', {}).then(function (res) {
        if (res && res.success && res.config) { fill(res.config); say('Reset to defaults: Wave, theme accent, 1800 ms.'); }
        else say('Reset failed: ' + ((res && res.error) || 'provider refused'));
      });
    });
    $('panel-left').addEventListener('click', function () { openPanel('left'); });
    $('panel-right').addEventListener('click', function () { openPanel('right'); });
    $('uninstall').addEventListener('click', function () {
      // The launcher entry is the only thing removed; files, settings and the
      // Edge engine stay, so the reverse action is always the reinstall button.
      var approved = true;
      try {
        approved = typeof window.confirm !== 'function' || window.confirm(
          'Uninstall Edge FX from the launcher? Settings and the Edge engine stay.');
      } catch (e) { approved = false; /* a blocked dialog is not consent */ }
      if (!approved) return;
      $('uninstall').disabled = true;
      $('install-state').textContent = 'Uninstalling…';
      call('apps', 'unregister', { app_id: APP_ID }).then(function (res) {
        if (res && res.success) { loadRegistry(); }
        else { $('uninstall').disabled = false; $('install-state').textContent = 'Uninstall refused: ' + ((res && (res.error || res.detail)) || 'unknown'); }
      }, function (err) {
        $('uninstall').disabled = false;
        $('install-state').textContent = 'Uninstall failed: ' + ((err && (err.message || err.code)) || 'bridge error');
      });
    });
    $('reinstall').addEventListener('click', function () {
      call('apps', 'register', {
        app_id: APP_ID, name: 'Edge FX', start_url: START_URL, version: '0.8.6-beta'
      }).then(function (res) {
        if (res && res.success) { $('install-state').textContent = 'Installed (state: ' + (res.state || 'installed') + ').'; loadRegistry(); }
        else $('install-state').textContent = 'Install refused: ' + ((res && (res.error || res.detail)) || 'unknown');
      });
    });
  }

  function openPanel(side) {
    // This page is usually framed inside Home; the panel belongs to the Home
    // document so it can overlay the app frame and reuse the Home registry.
    try {
      if (window.parent && window.parent !== window) {
        window.parent.postMessage({ type: 'nuxel:edge-panel-open', side: side, request_id: 'panel-' + Date.now() },
          window.location.origin);
      }
    } catch (e) { /* direct fallback below */ }
    var targets = [window.parent, window];
    for (var i = 0; i < targets.length; i++) {
      try {
        var api = targets[i].NuxelEdgeLighting;
        if (api && api.openPanel) { api.openPanel(side, 'edge-fx-app'); return; }
      } catch (e) { /* cross-origin frame: try the next target */ }
    }
    say('The Edge panel is available from Home (side swipe or the Quick Settings Edge tile).');
  }

  function init() {
    bind();
    bridgeReady().then(loadStatus).then(loadRegistry);
    document.addEventListener('nuxel:edge-lighting-changed', function (ev) {
      if (ev && ev.detail && ev.detail.config) fill(ev.detail.config);
    });
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init, { once: true });
  else init();
})();
