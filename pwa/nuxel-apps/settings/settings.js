// Nuxel Settings (A32)
//
// The real configuration surface of Nuxel.  It is a normal Nuxel registry app
// (id "nuxel-settings") opened inside the launcher's .pwa-frame, so it uses the
// launcher's own design language instead of being a second dashboard.
//
// Backend: window.NuxelHost (in-page) or the parent frame's NuxelHost (inside the
// .pwa-frame iframe) -> nuxel-pwa-host -> the Nuxel services.  Nothing here writes
// a file itself and nothing executes a shell command.
(function () {
  'use strict';

  var HOST = null;
  function host() {
    if (HOST) return HOST;
    HOST = (window.NuxelHost && window.NuxelHost.available) ? window.NuxelHost
         : (window.parent && window.parent !== window && window.parent.NuxelHost) ? window.parent.NuxelHost
         : null;
    return HOST;
  }
  // Same-origin iframe: talk to the parent, which owns the real host channel.
  function call(method, params) {
    var h = host();
    if (h && h.available) return h.call(method, params);
    return new Promise(function (resolve) { resolve({ ok: false, offline: true }); });
  }
  var act = function (action) { return call('system.action', { action: action }); };
  var cfgGet = function (n) { return call('config.get', { name: n }); };
  var cfgSet = function (n, t) { return call('config.set', { name: n, text: t }); };

  // ---------- tabs ----------
  document.querySelectorAll('.tab').forEach(function (t) {
    t.addEventListener('click', function () {
      document.querySelectorAll('.tab').forEach(function (x) { x.classList.remove('active'); });
      document.querySelectorAll('.panel').forEach(function (x) { x.classList.remove('active'); });
      t.classList.add('active');
      document.getElementById('tab-' + t.dataset.tab).classList.add('active');
    });
  });
  var closeBtn = document.getElementById('close');
  if (closeBtn) closeBtn.addEventListener('click', function () {
    var f = window.frameElement;
    if (!f) return;
    var closedByLauncher = false;
    try {
      if (window.parent !== window && window.parent.NuxelLauncherClose) {
        window.parent.NuxelLauncherClose();
        closedByLauncher = true;
      }
    } catch (e) { /* cross-origin parent: fall through */ }
    if (!closedByLauncher && f.parentNode) f.parentNode.removeChild(f);
  });

  // ---------- shared config documents ----------
  var DEFAULT_ZONES = {
    schema_version: 1, zones: 10,
    profiles: {
      s10plus: { portrait: [9, 10], landscape_left: [], landscape_right: [] },
      pixel_center: { portrait: [5, 6], landscape_left: [], landscape_right: [] },
      none: { portrait: [], landscape_left: [], landscape_right: [] },
      left_camera: { portrait: [1, 2], landscape_left: [1, 2], landscape_right: [9, 10] },
      right_camera: { portrait: [9, 10], landscape_left: [9, 10], landscape_right: [1, 2] }
    },
    padding_dp: 6, profile: 'none', orientation: 'portrait',
    custom: { portrait: [], landscape_left: [], landscape_right: [] }
  };
  var DEFAULT_BUTTONS = {
    schema_version: 1,
    bixby_short: 'open-terminal', bixby_long: 'disabled',
    power_short: 'screen-toggle', power_long: 'power-menu',
    volume_up: 'volume-up', volume_down: 'volume-down'
  };

  var zonesDoc = null;
  var WORK = { zones: [], orientation: 'portrait', padding: 6, profile: 'none' };

  function parse(text, dflt) {
    try { var o = JSON.parse(text); return (o && typeof o === 'object') ? o : JSON.parse(JSON.stringify(dflt)); }
    catch (e) { return JSON.parse(JSON.stringify(dflt)); }
  }

  // ---------- ten-zone editor ----------
  function zonesForOrientation(doc, profile, orientation) {
    var alias = { center_camera: 'pixel_center', pixel_center: 'pixel_center' }[profile] || profile;
    if (alias === 'custom') return (doc.custom && doc.custom[orientation]) || [];
    var p = doc.profiles[alias] || doc.profiles.none;
    return (p && p[orientation]) || [];
  }

  function renderZones() {
    var box = document.getElementById('zones');
    box.innerHTML = '';
    for (var i = 1; i <= 10; i++) {
      var b = document.createElement('button');
      b.className = 'zone' + (WORK.zones.indexOf(i) >= 0 ? ' blocked' : '');
      b.dataset.zone = String(i);
      b.textContent = String(i);
      b.addEventListener('click', function (ev) {
        var z = Number(ev.currentTarget.dataset.zone);
        var idx = WORK.zones.indexOf(z);
        if (idx >= 0) WORK.zones.splice(idx, 1); else WORK.zones.push(z);
        WORK.zones.sort(function (a, b) { return a - b; });
        WORK.profile = 'custom';
        document.getElementById('preset').value = 'custom';
        renderZones();
        previewLayout();
      });
      box.appendChild(b);
    }
  }

  function renderPreviewZones() {
    var wrap = document.getElementById('preview-zones');
    wrap.innerHTML = '';
    for (var i = 1; i <= 10; i++) {
      var s = document.createElement('span');
      if (WORK.zones.indexOf(i) >= 0) s.className = 'blocked';
      s.textContent = String(i);
      wrap.appendChild(s);
    }
  }

  // The preview reuses the LAUNCHER's own layout engine when available (same
  // document OR the parent frame), so what the user sees here is what the real
  // status bar does.
  function layoutEngine() {
    if (window.NuxelSafeZones) return window.NuxelSafeZones;
    try { if (window.parent && window.parent.NuxelSafeZones) return window.parent.NuxelSafeZones; } catch (e) {}
    return null;
  }

  function previewLayout() {
    renderPreviewZones();
    var engine = layoutEngine();
    var bar = document.getElementById('preview-bar');
    var w = bar.clientWidth || 320;
    if (!engine) {
      // No launcher engine reachable (Settings opened outside Nuxel Home).  The
      // editor shows the zone strip and says the placement preview is unavailable
      // instead of running a SECOND copy of the placement arithmetic: a duplicate
      // model is how a preview starts disagreeing with the real status bar (the
      // A32 copy still pushed the right cluster off the panel for zones 9,10).
      document.getElementById('preview-report').textContent =
        'blocked zones: [' + WORK.zones.join(', ') + ']  padding: ' + WORK.padding + ' dp\n' +
        'placement preview needs the launcher safe-zone engine (open Settings from Nuxel Home)';
      return;
    }
    engine.padding(WORK.padding);
    engine.previewZones(WORK.zones, WORK.orientation, 'custom');   // drives the REAL bar
    var report = JSON.stringify(engine.applyLayout(), null, 1);
    // The preview strip below mirrors the real bar with the SAME planner
    // (engine.planCluster), bar-relative so the strip's own coordinates are used.
    var ivals = engine.blockedIntervals(w);
    var ALIGN = { 'status-left': 'start', 'status-center': 'center', 'status-right': 'end' };
    ['status-left', 'status-center', 'status-right'].forEach(function (cls) {
      var el = bar.querySelector('.' + cls);
      if (!el) return;
      el.style.transform = '';          // reset BEFORE measuring (no compounding shift)
      el.classList.remove('moved');
      var r = el.getBoundingClientRect(), br = bar.getBoundingClientRect();
      var natural = { left: r.left - br.left, right: r.right - br.left, width: r.width };
      var plan = engine.planCluster(natural, ALIGN[cls], ivals, w);
      if (plan && plan.shift) {
        el.style.transform = 'translateX(' + plan.shift + 'px)';
        el.classList.add('moved');
      }
    });
    document.getElementById('preview-report').textContent =
      'blocked zones: [' + WORK.zones.join(', ') + ']  padding: ' + WORK.padding + ' dp\n' + report;
  }

  function loadZonesDoc() {
    return cfgGet('statusbar-safezones').then(function (res) {
      zonesDoc = (res && res.ok && res.text) ? parse(res.text, DEFAULT_ZONES) : parse(null, DEFAULT_ZONES);
      var engine = layoutEngine();
      var profile = zonesDoc.profile && zonesDoc.profile !== 'none' ? zonesDoc.profile
                  : (engine && engine.deviceProfile ? engine.deviceProfile() : 'none');
      WORK.profile = profile;
      WORK.orientation = zonesDoc.orientation || 'portrait';
      WORK.padding = typeof zonesDoc.padding_dp === 'number' ? zonesDoc.padding_dp : 6;
      WORK.zones = zonesForOrientation(zonesDoc, profile, WORK.orientation).slice();
      var sel = document.getElementById('preset');
      if (['none', 'right_camera', 'center_camera', 'left_camera', 'custom'].indexOf(profile) >= 0) sel.value = profile;
      else sel.value = (profile === 's10plus' || profile === 'pixel_center') ? 'custom' : 'none';
      document.getElementById('orientation').value = WORK.orientation;
      document.getElementById('padding').value = String(WORK.padding);
      document.getElementById('padding-val').textContent = WORK.padding + ' dp';
      renderZones();
      previewLayout();
      return zonesDoc;
    });
  }

  document.getElementById('preset').addEventListener('change', function (e) {
    WORK.profile = e.target.value;
    WORK.zones = zonesForOrientation(zonesDoc || DEFAULT_ZONES, WORK.profile, WORK.orientation).slice();
    renderZones();
    previewLayout();
  });
  document.getElementById('orientation').addEventListener('change', function (e) {
    WORK.orientation = e.target.value;
    WORK.zones = zonesForOrientation(zonesDoc || DEFAULT_ZONES, WORK.profile, WORK.orientation).slice();
    renderZones();
    previewLayout();
  });
  document.getElementById('padding').addEventListener('input', function (e) {
    WORK.padding = Number(e.target.value);
    document.getElementById('padding-val').textContent = WORK.padding + ' dp';
    previewLayout();
  });
  document.getElementById('apply-zones').addEventListener('click', function () {
    var engine = layoutEngine();
    if (engine) engine.previewZones(WORK.zones, WORK.orientation, 'custom');
    previewLayout();
    document.getElementById('save-zones').textContent = 'Save (unsaved preview)';
  });
  document.getElementById('cancel-zones').addEventListener('click', function () {
    var engine = layoutEngine();
    if (engine) engine.cancelPreview();
    loadZonesDoc();
  });
  document.getElementById('save-zones').addEventListener('click', function () {
    var doc = zonesDoc || JSON.parse(JSON.stringify(DEFAULT_ZONES));
    doc.profile = WORK.profile === 'custom' ? 'custom' : WORK.profile;
    doc.orientation = WORK.orientation;
    doc.padding_dp = WORK.padding;
    doc.custom = doc.custom || { portrait: [], landscape_left: [], landscape_right: [] };
    if (WORK.profile === 'custom') {
      doc.custom[WORK.orientation] = WORK.zones.slice();
    } else {
      var alias = WORK.profile;
      doc.profiles[alias] = doc.profiles[alias] || {};
      doc.profiles[alias][WORK.orientation] = WORK.zones.slice();
    }
    cfgSet('statusbar-safezones', JSON.stringify(doc, null, 2)).then(function (res) {
      var engine = layoutEngine();
      if (engine) {
        engine.cancelPreview();
        engine.load(function () { engine.applyLayout(); });
      }
      document.getElementById('preview-report').textContent =
        (res && res.ok) ? 'saved to /etc/nuxel/display/statusbar-safezones.json (no reboot needed)'
                        : 'NOT saved: launcher host unavailable (offline fallback only)';
    });
  });

  // ---------- buttons & gestures ----------
  var ACTION_CHOICES = [
    ['open-terminal', 'Terminal (default)'],
    ['home', 'Home'], ['search', 'Search'], ['settings', 'Settings'],
    ['screen-toggle', 'Screen on/off'], ['volume-up', 'Volume up'], ['volume-down', 'Volume down'],
    ['volume-mute', 'Mute'], ['disabled', 'Disabled']
  ];
  function appChoices() {
    var out = [];
    try {
      var reg = (window.parent && window.parent.appRegistry) || window.appRegistry;
      if (reg && reg.getAllApps) out = reg.getAllApps().map(function (a) { return ['app:' + a.id, a.name + ' (' + a.id + ')']; });
    } catch (e) {}
    return out;
  }
  function fillSelect(id, value) {
    var sel = document.getElementById(id);
    sel.innerHTML = '';
    ACTION_CHOICES.concat(appChoices()).forEach(function (pair) {
      var o = document.createElement('option');
      o.value = pair[0]; o.textContent = pair[1];
      sel.appendChild(o);
    });
    if (value && !Array.prototype.some.call(sel.options, function (o) { return o.value === value; })) {
      var o2 = document.createElement('option'); o2.value = value; o2.textContent = value + ' (custom)';
      sel.appendChild(o2);
    }
    if (value) sel.value = value;
  }
  var buttonsDoc = null;
  function loadButtons() {
    return cfgGet('buttons').then(function (res) {
      buttonsDoc = (res && res.ok && res.text) ? parse(res.text, DEFAULT_BUTTONS) : JSON.parse(JSON.stringify(DEFAULT_BUTTONS));
      if (buttonsDoc.mappings && typeof buttonsDoc.mappings === 'object') {
        buttonsDoc = Object.assign({}, DEFAULT_BUTTONS, {
          bixby_short: buttonsDoc.mappings.bixby && buttonsDoc.mappings.bixby.short,
          bixby_long: buttonsDoc.mappings.bixby && buttonsDoc.mappings.bixby.long,
          power_short: buttonsDoc.mappings.power && buttonsDoc.mappings.power.short,
          power_long: buttonsDoc.mappings.power && buttonsDoc.mappings.power.long,
          volume_up: buttonsDoc.mappings.volume_up, volume_down: buttonsDoc.mappings.volume_down
        });
      }
      // migrate the legacy nested layout once, so old customisations survive
      if (buttonsDoc.mappings) delete buttonsDoc.mappings;
      fillSelect('bixby-short', buttonsDoc.bixby_short || 'open-terminal');
      fillSelect('bixby-long', buttonsDoc.bixby_long || 'disabled');
      fillSelect('power-short', buttonsDoc.power_short || 'screen-toggle');
      fillSelect('power-long', buttonsDoc.power_long || 'power-menu');
      fillSelect('vol-up', buttonsDoc.volume_up || 'volume-up');
      fillSelect('vol-down', buttonsDoc.volume_down || 'volume-down');
    });
  }
  document.getElementById('save-buttons').addEventListener('click', function () {
    var doc = buttonsDoc || JSON.parse(JSON.stringify(DEFAULT_BUTTONS));
    doc.schema_version = 1;
    doc.bixby_short = document.getElementById('bixby-short').value;
    doc.bixby_long = document.getElementById('bixby-long').value;
    doc.power_short = document.getElementById('power-short').value;
    doc.power_long = document.getElementById('power-long').value;
    doc.volume_up = document.getElementById('vol-up').value;
    doc.volume_down = document.getElementById('vol-down').value;
    delete doc.mappings;
    cfgSet('buttons', JSON.stringify(doc, null, 2)).then(function (res) {
      document.getElementById('buttons-report').textContent =
        (res && res.ok) ? 'saved to /etc/nuxel/input/buttons.json — the button manager reloads it within 1 s'
                        : 'NOT saved: launcher host unavailable';
    });
  });
  document.getElementById('reload-buttons').addEventListener('click', function () { loadButtons(); });

  // ---------- display / sound actions ----------
  document.querySelectorAll('[data-action]').forEach(function (b) {
    b.addEventListener('click', function () { act(b.dataset.action); setTimeout(refreshDev, 400); });
  });

  // ---------- developer status ----------
  function statusLine(name) {
    return call('status.read', { name: name }).then(function (res) {
      var t = (res && res.ok && res.text) ? res.text.trim() : '(unavailable)';
      return name + ': ' + t;
    });
  }
  function refreshDev() {
    Promise.all(['wlfb-state', 'launcher-state', 'anim-state', 'display-state', 'touch-arm-state']
      .map(statusLine)).then(function (lines) {
        document.getElementById('dev-state').textContent = lines.join('\n\n');
        document.getElementById('display-state').textContent = lines[3];
      });
    Promise.all([['volume', 'Volume OSD'], ['touch-arm-state', 'Touch arming']].map(function (p) {
      return call('status.read', { name: p[0] }).then(function (r) {
        return p[1] + ': ' + ((r && r.ok && r.text) ? r.text.trim() : '(unavailable)');
      });
    })).then(function (l) { document.getElementById('dev-input').textContent = l.join('\n'); });
    fetch('/runtime/osd.json', { cache: 'no-store' }).then(function (r) { return r.ok ? r.text() : null; })
      .then(function (t) { if (t) document.getElementById('volume-state').textContent = t; })
      .catch(function () {});
  }
  document.getElementById('refresh-dev').addEventListener('click', refreshDev);

  // ---------- verbose boot (briq-02b) ----------
  // The SAME durable document `nuxelctl verbose-boot on|off` writes and
  // nuxel-verbose-boot.service reads: /etc/nuxel/boot/verbose-boot.json (through
  // the host's config channel, which is an atomic same-directory rename).  The
  // write MERGES into the loaded document, so a key this revision does not know
  // about survives - an upgrade or a newer/older launcher never clobbers the
  // operator's choice.
  var VERBOSE_NAME = 'verbose-boot';
  function verboseDoc() {
    return cfgGet(VERBOSE_NAME).then(function (res) {
      if (res && res.ok && res.text) {
        try { var d = JSON.parse(res.text); if (d && typeof d === 'object') return d; } catch (e) {}
      }
      return {};
    }, function () { return {}; });
  }
  // The three boot-diagnostics controls, their legal values and the one
  // precedence rule.  Kept next to the panel so the UI cannot invent a value the
  // console / the boot-time consumer would reject.
  var ANIMATION_MODES = ['standard', 'short', 'off'];
  var VERBOSITY_MIN = 0, VERBOSITY_MAX = 3;
  function animationMode(doc) {
    var m = String((doc && doc.animation_mode) || 'standard').toLowerCase();
    return ANIMATION_MODES.indexOf(m) >= 0 ? m : 'standard';
  }
  function verbosityLevel(doc) {
    var n = parseInt((doc && doc.verbosity_level), 10);
    if (isNaN(n) || n < VERBOSITY_MIN || n > VERBOSITY_MAX) return 1;
    return n;
  }
  // The precedence rule as the boot-time consumer implements it
  // (tools/s10plus/a33/nuxel-verbose-boot.py): off > short > verbose_boot > standard.
  function effectiveAnimation(doc) {
    var mode = animationMode(doc);
    if (mode === 'off') return { mode: 'off', reason: 'animation_mode_off' };
    if (mode === 'short') return { mode: 'short', reason: 'animation_mode_short' };
    if (doc && doc.verbose_boot) return { mode: 'short', reason: 'verbose_boot_requested' };
    return { mode: 'standard', reason: 'standard' };
  }

  function loadBoot() {
    var state = document.getElementById('verbose-boot-state');
    var toggle = document.getElementById('verbose-boot-toggle');
    var animSel = document.getElementById('animation-mode');
    var verbSel = document.getElementById('verbosity-level');
    var eff = document.getElementById('boot-effective');
    var override = document.getElementById('verbose-boot-override');
    if (!state || !toggle) return Promise.resolve();
    return verboseDoc().then(function (doc) {
      toggle.checked = !!doc.verbose_boot;
      if (animSel) animSel.value = animationMode(doc);
      if (verbSel) verbSel.value = String(verbosityLevel(doc));
      var policy = effectiveAnimation(doc);
      return call('status.read', { name: 'verbose-boot-state' }).then(function (res) {
        var bootState = (res && res.ok && res.text) ? res.text.trim() : '';
        var lines = [
          'verbose_boot: ' + (doc.verbose_boot ? 'ON — applies from the NEXT boot' : 'off (default)'),
          'animation_mode: ' + animationMode(doc) + ' → effective ' + policy.mode + ' (' + policy.reason + ')',
          'verbosity_level: ' + verbosityLevel(doc),
          'stored in: /etc/nuxel/boot/verbose-boot.json',
          'set_by: ' + (doc.set_by || 'default') + '   schema_version: ' + (doc.schema_version || 1)
        ];
        if (doc.migrated_from) lines.push('migrated_from: ' + doc.migrated_from);
        if (bootState) lines.push('this boot: ' + bootState.split('\n').join(' | '));
        else lines.push('this boot: (nuxel-verbose-boot has not reported yet)');
        state.textContent = lines.join('\n');
        if (eff) {
          eff.textContent = 'Next boot will ' + (policy.mode === 'standard'
            ? 'play the full 192-frame / 24 fps animation and then hand over to the launcher'
            : 'hand over without the full animation') + ' — reason ' + policy.reason + '. '
            + (doc.verbose_boot ? 'The boot log WILL be shown on the glass. ' : 'The boot log will NOT be shown. ')
            + 'Verbosity ' + verbosityLevel(doc) + ' (' + verbosityLabel(verbosityLevel(doc)) + ').';
        }
        var supported = /OVERRIDE_CAPABILITY=supported/.test(bootState);
        override.textContent = supported
          ? 'One-time Bixby-hold override: available on the installed early boot stage.'
          : 'One-time Bixby-hold override: BOOT_UPDATE_REQUIRED — the installed early boot stage ' +
            'cannot read the Bixby key state, so the override is refused with a kernel marker ' +
            '(NUXEL_VERBOSE_BOOT_OVERRIDE_REFUSED) rather than faked behind this switch. ' +
            'Userspace fallback: turn Verbose boot on here (or "nuxelctl verbose-boot on"), which ' +
            'needs no BOOT partition write.';
      });
    });
  }
  function verbosityLabel(n) {
    return { 0: 'quiet (markers only)', 1: 'normal', 2: 'verbose (per-stage)', 3: 'debug' }[n] || 'normal';
  }
  // One write for the whole panel: the three controls are stored in ONE document,
  // so a single failed write cannot leave them disagreeing with the file.  The
  // write MERGES into the loaded document, preserving keys this revision does not
  // know about (an upgrade or a downgrade never clobbers the operator's choice).
  function saveBoot() {
    var toggle = document.getElementById('verbose-boot-toggle');
    var animSel = document.getElementById('animation-mode');
    var verbSel = document.getElementById('verbosity-level');
    var btn = document.getElementById('save-boot');
    if (!toggle || !animSel || !verbSel) return Promise.resolve();
    var want = {
      verbose_boot: !!toggle.checked,
      animation_mode: animationMode({ animation_mode: animSel.value }),
      verbosity_level: verbosityLevel({ verbosity_level: verbSel.value })
    };
    if (btn) btn.disabled = true;
    return verboseDoc().then(function (doc) {
      doc.schema_version = doc.schema_version || 1;
      doc.verbose_boot = want.verbose_boot;
      doc.animation_mode = want.animation_mode;
      doc.verbosity_level = want.verbosity_level;
      doc.set_by = 'user';
      doc.updated_at = Date.now();
      return cfgSet(VERBOSE_NAME, JSON.stringify(doc, null, 2) + '\n');
    }).then(function (res) {
      if (btn) btn.disabled = false;
      if (!res || !res.ok) {
        // Never leave the panel lying about what is stored: put the controls back.
        return loadBoot().then(function () {
          document.getElementById('verbose-boot-state').textContent =
            'save failed — nothing was changed (no host channel?)\nwanted: ' + JSON.stringify(want);
        });
      }
      return loadBoot();
    }, function () {
      if (btn) btn.disabled = false;
      return loadBoot().then(function () {
        document.getElementById('verbose-boot-state').textContent =
          'save failed — nothing was changed';
      });
    });
  }
  if (document.getElementById('save-boot')) {
    document.getElementById('save-boot').addEventListener('click', saveBoot);
  }
  if (document.getElementById('verbose-boot-toggle')) {
    document.getElementById('verbose-boot-toggle').addEventListener('change', function () {
      var el = this;
      var want = !!el.checked;
      el.disabled = true;
      verboseDoc().then(function (doc) {
        doc.schema_version = doc.schema_version || 1;
        doc.verbose_boot = want;
        doc.set_by = 'user';
        doc.updated_at = Date.now();
        return cfgSet(VERBOSE_NAME, JSON.stringify(doc, null, 2) + '\n');
      }).then(function (res) {
        el.disabled = false;
        if (!res || !res.ok) {
          el.checked = !want;   // never leave the switch lying about what is stored
          document.getElementById('verbose-boot-state').textContent =
            'save failed — the setting was NOT changed (no host channel?)\nwanted verbose_boot=' + want;
        }
        return loadBoot();
      }, function () {
        el.disabled = false;
        el.checked = !want;
        document.getElementById('verbose-boot-state').textContent =
          'save failed — the setting was NOT changed';
      });
    });
  }
  if (document.getElementById('reload-boot')) {
    document.getElementById('reload-boot').addEventListener('click', function () { loadBoot(); });
  }

  // ---------- screen rotation (A49) ----------
  // One source of truth: nuxel-orientationd, reached through the shared bridge
  // (home document owns it in the VM build). The seven modes below mirror the
  // daemon; the authoritative list is the orientation.modes RPC response.
  var ROTATE_MODES = [
    ['portrait', 'Portrait'], ['reverse_portrait', 'Reverse portrait'],
    ['landscape', 'Landscape'], ['reverse_landscape', 'Reverse landscape'],
    ['auto', 'Auto (all four)'], ['auto_portrait', 'Auto portrait'],
    ['auto_landscape', 'Auto landscape']
  ];
  function orientationBridge() {
    try {
      if (window.bridge && window.bridge.call) return window.bridge;
      if (window.parent && window.parent !== window && window.parent.bridge && window.parent.bridge.call) return window.parent.bridge;
      if (window.NuxelBridge && window.NuxelBridge.call) return window.NuxelBridge;
    } catch (e) { /* cross-origin parent */ }
    return null;
  }
  function orientationCall(verb, params) {
    var b = orientationBridge();
    if (!b) return Promise.resolve({ success: false, offline: true, error: 'bridge unavailable' });
    try { return b.call('orientation', verb, params || {}); }
    catch (e) { return Promise.resolve({ success: false, offline: true, error: String(e && e.message || e) }); }
  }
  var rotationBlock = document.getElementById('orientation-modes');
  var rotationState = document.getElementById('orientation-state');
  var rotationHint = document.getElementById('orientation-hint');
  function renderRotationModes(current) {
    if (!rotationBlock) return;
    rotationBlock.replaceChildren();
    ROTATE_MODES.forEach(function (entry) {
      var id = entry[0], label = entry[1];
      var wrap = document.createElement('label');
      wrap.className = 'radio';
      var input = document.createElement('input');
      input.type = 'radio';
      input.name = 'orientation-mode';
      input.value = id;
      if (id === current) input.checked = true;
      input.addEventListener('change', function () {
        if (!input.checked) return;
        rotationState.textContent = 'Applying ' + label + '…';
        orientationCall('set', { mode: id }).then(function (res) {
          if (res && res.success === true) {
            rotationState.textContent = 'Rotation mode: ' + (res.mode_label || res.mode) +
              ' (effective ' + res.effective_orientation + '°)';
            if (res.compositor && res.compositor.applied === false) {
              rotationHint.textContent = 'Compositor did not apply the transform yet: ' +
                (res.compositor.error || 'no transform backend');
            } else {
              rotationHint.textContent = 'Compositor transform applied via ' +
                (res.compositor && res.compositor.backend ? res.compositor.backend : 'backend');
            }
            renderRotationModes(res.mode || id);
          } else {
            rotationState.textContent = 'Rotation unchanged: ' +
              (res && res.error ? res.error : 'backend unavailable');
          }
        });
      });
      wrap.appendChild(input);
      var text = document.createElement('span');
      text.textContent = label;
      wrap.appendChild(text);
      rotationBlock.appendChild(wrap);
    });
  }
  function loadRotation() {
    orientationCall('get').then(function (st) {
      if (!st || st.mode === undefined) {
        rotationState.textContent = st && st.error
          ? ('Orientation service unavailable: ' + st.error)
          : 'Orientation service unavailable (offline)';
        return;
      }
      renderRotationModes(st.mode);
      var sensor = st.sensor || {};
      rotationState.textContent = 'Mode: ' + (st.mode_label || st.mode) +
        ' | effective ' + st.effective_orientation + '°' +
        (st.auto ? (' | sensor ' + (sensor.available ? 'available' : 'unavailable')) : '');
      rotationHint.textContent = 'Mount matrix / gravity reference: ' +
        ((st.calibration && st.calibration.mount_matrix) || 'unverified') +
        '. Owner proof: docs/A49/OWNER-TEST-ORIENTATION.md';
    }, function () {
      rotationState.textContent = 'Orientation service unavailable (offline)';
    });
  }
  loadRotation();

  // ---------- boot ----------
  loadZonesDoc().then(loadButtons).then(loadBoot).then(function () {
    refreshDev();
    setInterval(refreshDev, 4000);
    window.addEventListener('resize', previewLayout);
  });
})();
