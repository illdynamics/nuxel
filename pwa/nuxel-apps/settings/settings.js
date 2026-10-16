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
    if (f && window.parent !== window) window.parent.NuxelLauncherClose && window.parent.NuxelLauncherClose();
    else if (f && f.parentNode) f.parentNode.removeChild(f);
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
    var report = '—';
    if (engine) {
      engine.previewZones(WORK.zones, WORK.orientation, 'custom');
      report = JSON.stringify(engine.applyLayout(), null, 1);
      if (engine.preview && engine.preview.zones.length) {
        var pf = engine.previewZones;  // no-op, keeps the call explicit
      }
    }
    // local mirror of the constraint pass for the preview strip
    var w = bar.clientWidth || 320;
    var zoneW = w / 10;
    var pad = (WORK.padding || 0) * 2;
    var intervals = WORK.zones.map(function (z) {
      return { a: (z - 1) * zoneW - pad, b: z * zoneW + pad, z: z };
    });
    ['status-left', 'status-center', 'status-right'].forEach(function (cls) {
      var el = bar.querySelector('.' + cls);
      if (!el) return;
      el.style.transform = '';
      var r = el.getBoundingClientRect(), br = bar.getBoundingClientRect();
      var a = r.left - br.left, b = r.right - br.left;
      var hit = intervals.find(function (iv) { return a < iv.b && b > iv.a; });
      if (!hit) return;
      var shift = (cls === 'status-left') ? (intervals[0].a - b - 2)
                : (cls === 'status-right') ? (intervals[intervals.length - 1].b - a + 2)
                : ((intervals[0].a > (w - intervals[intervals.length - 1].b)) ? (intervals[0].a - b - 2)
                                                                            : (intervals[intervals.length - 1].b - a + 2));
      el.style.transform = 'translateX(' + Math.round(shift) + 'px)';
      el.classList.add('moved');
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

  // ---------- boot ----------
  loadZonesDoc().then(loadButtons).then(function () {
    refreshDev();
    setInterval(refreshDev, 4000);
    window.addEventListener('resize', previewLayout);
  });
})();
