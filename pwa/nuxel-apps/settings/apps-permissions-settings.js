/* Nuxel Settings — Apps & Permissions (PWNAGE-86000 / briq-05a).
 *
 * Apps: per-app default orientation (launch preference) plus a shortcut to
 * the app's permission controls.
 *
 * Permissions: the owner-facing control surface for the central permD policy.
 * It reads the SAME store that nuxel-permd owns and the bridge enforces, so a
 * toggle here is a real grant/revoke — not a localStorage label. Offline or
 * unsupported enforcement is always shown as Denied/Unavailable, never green.
 */
(function () {
  'use strict';

  var ORIENTATIONS = [
    ['inherit', 'Default (inherit)'],
    ['portrait', 'Portrait'],
    ['reverse-portrait', 'Reverse portrait'],
    ['landscape', 'Landscape'],
    ['reverse-landscape', 'Reverse landscape']
  ];

  var NUXEL_CONTROLS = [
    ['zoom', 'Zoom with two fingers',
      'Allow two-finger pinch/drag to zoom this app\u2019s whole interface. App-internal zoom (maps, browser) is separate.'],
    ['fullscreen', 'Fullscreen',
      'Allow this app to request exclusive fullscreen / hide system chrome.'],
    ['casting', 'Casting',
      'Allow this app to initiate future Nuxel casting (not available until a casting service exists).'],
    ['mirroring', 'Mirroring',
      'Show this app on a connected mirrored display. Off shows a privacy blank on the external screen only.']
  ];

  // Split the location group into the two real broker capabilities.  permD
  // canonicalises both tokens to ``location`` in its grant store, so the
  // permission surface must remember which resource token was shown or the
  // "Location control" switch would silently toggle plain read access too.
  var LOCATION_CONTROLS = [
    ['location:read', 'Location',
      'Allow this app to request the current device position from the system location provider.'],
    ['location:manage', 'Location control',
      'Allow this app to enable or disable the global location policy for the whole device.']
  ];

  var CAP_LABELS = {
    'microphone': 'Microphone', 'camera': 'Camera', 'location': 'Location',
    'location:manage': 'Location control',
    'contacts': 'Contacts', 'calendar': 'Calendar', 'call': 'Phone calls',
    'sms': 'SMS', 'notifications': 'Notifications', 'network': 'Network',
    'bluetooth': 'Bluetooth', 'usb': 'USB devices', 'storage': 'Files & storage',
    'media_library': 'Media library', 'downloads': 'Downloads',
    'background': 'Background execution', 'local_shell': 'Local shell / PTY',
    'system_inspect': 'System inspection (read-only)', 'input_devices': 'Input devices',
    'catalog_read': 'App catalog (read)', 'app_install': 'Install apps',
    'app_remove': 'Remove apps', 'clipboard': 'Clipboard', 'display': 'Display ownership',
    'audio': 'Audio playback', 'clock_status': 'Clock & alarms', 'phone_status': 'Phone status',
    'sms_send_raw': 'Raw modem access', 'nfc': 'NFC'
  };

  function bridge() {
    try {
      if (window.NuxelBridge && typeof window.NuxelBridge.call === 'function') return window.NuxelBridge;
      if (window.parent && window.parent !== window && window.parent.NuxelBridge &&
          typeof window.parent.NuxelBridge.call === 'function') return window.parent.NuxelBridge;
    } catch (e) {}
    return null;
  }

  function rpc(namespace, verb, params) {
    var b = bridge();
    if (!b) return Promise.resolve({ success: false, error: 'Nuxel bridge unavailable', offline: true });
    try { return Promise.resolve(b.call(namespace, verb, params || {})); }
    catch (e) { return Promise.resolve({ success: false, error: String(e && e.message || e), offline: true }); }
  }

  function appRegistry() {
    try { return (window.parent && window.parent.appRegistry) || window.appRegistry || null; }
    catch (e) { return null; }
  }

  // The canonical registry as published by the web root.  The launcher usually
  // injects `appRegistry`; when this page is opened on its own (or that object
  // is not ready yet) the SAME registry file is the authority, so the owner can
  // still review every app's permissions.
  var canonicalApps = null;
  var canonicalAppsPromise = null;
  function loadCanonicalApps() {
    if (canonicalAppsPromise) return canonicalAppsPromise;
    canonicalAppsPromise = fetch('/pwa/nuxel-common/app-registry.json', { cache: 'no-cache' })
      .then(function (r) { return r.ok ? r.json() : null; })
      .then(function (doc) {
        var list = doc && (Array.isArray(doc.apps) ? doc.apps : (doc.registry && doc.registry.apps));
        canonicalApps = Array.isArray(list) ? list.filter(function (a) { return a && a.id; }) : [];
        return canonicalApps;
      })
      .catch(function () { canonicalApps = []; return canonicalApps; });
    return canonicalAppsPromise;
  }

  function getAllApps() {
    var reg = appRegistry();
    if (reg && typeof reg.getAllApps === 'function') {
      var apps = reg.getAllApps();
      if (Array.isArray(apps) && apps.length) return apps;
    }
    return canonicalApps || [];
  }

  function $ (id) { return document.getElementById(id); }
  function esc(v) { return String(v == null ? '' : v).replace(/[&<>"']/g, function (c) { return ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'})[c]; }); }

  var CANONICAL = {
    audio: 1, background: 1, bluetooth: 1, calendar: 1, call: 1, camera: 1,
    clipboard: 1, clock_status: 1, contacts: 1, display: 1, location: 1,
    microphone: 1, network: 1, notifications: 1, phone_status: 1, sms: 1,
    sms_send_raw: 1, storage: 1, usb: 1, input_devices: 1, local_shell: 1,
    system_inspect: 1, downloads: 1, media_library: 1, catalog_read: 1,
    app_install: 1, app_remove: 1, zoom: 1, fullscreen: 1, casting: 1, mirroring: 1
  };
  var TOKEN_MAP = {
    'phone:status': 'phone_status',
    'system:inspect': 'system_inspect',
    'media:library': 'media_library',
    'download:queue': 'downloads',
    'audio:playback': 'audio',
    'shell:local-pty': 'local_shell'
  };
  function resolveToken(token) {
    var t = String(token || '');
    if (TOKEN_MAP[t]) return TOKEN_MAP[t];
    var base = t.split(':')[0];
    return CANONICAL[base] ? base : null;
  }
  function rawCaps(app) {
    return Array.isArray(app.capabilities) ? app.capabilities.slice() : [];
  }

  function canonicalCaps(app) {
    var caps = rawCaps(app);
    var out = {};
    NUXEL_CONTROLS.forEach(function (pair) { out[pair[0]] = true; });
    caps.forEach(function (c) { var id = resolveToken(c); if (id) out[id] = true; });
    return Object.keys(out).sort();
  }

  // A concrete manifest token (location:read / location:manage) is checked
  // against its own permD decision.  The token-free groups (camera, network …)
  // fall back to the canonical group decision.
  function tokenOn(doc, token) {
    var d = tokenDecision(doc, token);
    if (ACTUATOR_TOKENS[token]) {
      if (d) return d.decision === 'allow';
    }
    return d ? d.decision === 'allow'
             : decisionOn(doc, resolveToken(token) || token);
  }

  // ---- Apps tab -----------------------------------------------------------
  function renderApps(orientationDoc) {
    var box = $('apps-list');
    if (!box) return;
    var apps = getAllApps().filter(function (a) { return a && a.id; });
    var defaults = (orientationDoc && orientationDoc.apps) || {};
    var forced = (orientationDoc && orientationDoc.force) || {};
    box.innerHTML = '';
    if (!apps.length) {
      var st = $('apps-state'); if (st) st.textContent = 'No installed apps found.';
      return;
    }
    apps.forEach(function (a) {
      var row = document.createElement('div');
      row.className = 'app-row';
      var info = document.createElement('div');
      info.className = 'app-row-info';
      var name = document.createElement('div');
      name.className = 'app-row-name';
      name.textContent = (a.name || a.id);
      var id = document.createElement('div');
      id.className = 'app-row-id';
      id.textContent = a.id + ' · ' + (a.type || 'app');
      info.appendChild(name); info.appendChild(id);

      var sel = document.createElement('select');
      sel.className = 'app-orientation-select';
      ORIENTATIONS.forEach(function (pair) {
        var o = document.createElement('option');
        o.value = pair[0]; o.textContent = pair[1];
        sel.appendChild(o);
      });
      sel.value = defaults[a.id] || 'inherit';
      sel.setAttribute('aria-label', 'Default orientation for ' + (a.name || a.id));

      // Force: lock the app to the selected orientation while it is in front.
      // Unforced (the default) means it merely STARTS in that pose and may
      // still be rotated afterwards.  Force only applies to an explicit mode.
      var forceLabel = document.createElement('label');
      forceLabel.className = 'app-orientation-force';
      var forceBox = document.createElement('input');
      forceBox.type = 'checkbox';
      forceBox.setAttribute('aria-label', 'Force orientation for ' + (a.name || a.id));
      forceBox.checked = !!forced[a.id];
      forceBox.disabled = sel.value === 'inherit';
      var forceText = document.createElement('span');
      forceText.textContent = 'Force';
      forceText.title = 'ON: the app can only run in this orientation until Force is unchecked. OFF: the app starts in this orientation but can still rotate.';
      forceLabel.appendChild(forceBox);
      forceLabel.appendChild(forceText);

      sel.addEventListener('change', function () {
        sel.disabled = true;
        forceBox.disabled = true;
        var wantedForce = sel.value === 'inherit' ? false : forceBox.checked;
        rpc('apps', 'set-orientation-default', {
          app_id: a.id, orientation: sel.value, force: wantedForce
        }).then(function (r) {
          sel.disabled = false;
          if (!r || r.success === false) {
            sel.value = defaults[a.id] || 'inherit';
            forceBox.checked = !!forced[a.id];
          } else {
            defaults[a.id] = sel.value;
            if (r.force) { forced[a.id] = r.forced_orientation || sel.value; }
            else { delete forced[a.id]; }
            forceBox.checked = !!forced[a.id];
          }
          forceBox.disabled = sel.value === 'inherit';
        });
      });

      forceBox.addEventListener('change', function () {
        // A forced app must name a concrete mode; turning Force on with an
        // inherited entry is refused by the bridge, so ask for a mode first.
        if (forceBox.checked && sel.value === 'inherit') {
          forceBox.checked = false;
          if (st) st.textContent = 'Choose a rotation before forcing ' + (a.name || a.id) + '.';
          return;
        }
        forceBox.disabled = true;
        rpc('apps', 'set-orientation-default', {
          app_id: a.id, orientation: sel.value, force: forceBox.checked
        }).then(function (r) {
          forceBox.disabled = false;
          if (!r || r.success === false) {
            forceBox.checked = !!forced[a.id];
          } else {
            if (r.force) { forced[a.id] = r.forced_orientation || sel.value; }
            else { delete forced[a.id]; }
            forceBox.checked = !!forced[a.id];
          }
        });
      });

      var perm = document.createElement('button');
      perm.className = 'ghost';
      perm.textContent = 'Permissions';
      perm.addEventListener('click', function () {
        var tab = document.querySelector('.tab[data-tab="permissions"]');
        if (tab) tab.click();
        var select = $('permissions-app-select');
        if (select) { select.value = a.id; loadPermissions(a.id); }
      });

      row.appendChild(info); row.appendChild(sel); row.appendChild(forceLabel); row.appendChild(perm);
      box.appendChild(row);
    });
    var st = $('apps-state');
    if (st) st.textContent = apps.length + ' installed app' + (apps.length === 1 ? '' : 's') + '.';
  }

  function loadApps() {
    loadCanonicalApps().then(function () {
      rpc('apps', 'orientation-defaults', {}).then(function (r) {
        renderApps(r && r.result ? r.result : r);
      });
    });
  }

  // ---- Permissions tab ----------------------------------------------------
  var currentAppId = null;

  // For location, a concrete manifest token is the delegate the bridge
  // enforces.  ``location:manage`` is checked by the actuator RPC below; both
  // switches are also reconciled against permissions.check before first paint.
  var ACTUATOR_TOKENS = { 'location:manage': 1, 'location:read': 1 };

  // The permission manager tells the truth about what permD enforces.  The
  // location resource is honestly partial (there is no satellite GNSS path on
  // this handset), but the global provider policy and the per-app read/control
  // gates ARE enforced by nuxel-bridge.  Do not render those switches as
  // "Unavailable" merely because the resource verdict is BLOCKED_HARDWARE.
  var ACTUATOR_ENFORCEMENT = {
    'location:read': {
      available: true,
      // The bridge gate is real but the satellite/GNSS path is not yet
      // available on this handset.  Surface that honest limitation instead of
      // turning the working permission switch into "Unavailable".
      why: 'position access is gated by nuxel-bridge while requesting provider coordinates. '
         + 'The provider currently returns network/Wi-Fi position; satellite GNSS remains unavailable.'
    },
    'location:manage': {
      available: true,
      why: 'enforced by nuxel-bridge on every global location policy change'
    }
  };

  function tokenDecision(doc, token) {
    var decisions = (doc && doc.decisions) || {};
    var d = decisions[token];
    if (d && d.decision) return d;
    var resolved = resolveToken(token);
    if (!resolved) return null;
    // permD returns ``location`` once, with capability=location.  That row is
    // not evidence for the OTHER delegate: a resource grant written by read
    // must not paint the control switch Allowed (and vice versa).  The bridge
    // check below is authoritative for the concrete token.
    Object.keys(decisions).forEach(function (key) {
      var row = decisions[key];
      if (!row || row.decision === undefined || row.capability !== resolved) return;
      if (key === token) d = row;
    });
    return d;
  }

  function decisionOn(doc, cap) {
    var d = tokenDecision(doc, cap);
    if (d) return d.decision === 'allow';
    return Array.isArray(doc && doc.capabilities) && doc.capabilities.indexOf(cap) !== -1;
  }

  function enforcementMeta(doc, cap) {
    if (ACTUATOR_ENFORCEMENT[cap]) return ACTUATOR_ENFORCEMENT[cap];
    var enf = (doc && doc.enforcement && doc.enforcement[cap]) || null;
    if (!enf) return { available: true, why: '' };
    var mech = enf.mechanisms || [];
    var unavailable = enf.verdict === 'NOT_SUPPORTED_ON_DEVICE' ||
        enf.enforceable === 'no' || (mech.length === 1 && mech[0] === 'none');
    return { available: !unavailable, why: enf.limitation || (unavailable ? 'Unsupported on this device' : '') };
  }

  function toggleRow(name, label, description, state, meta, onToggle) {
    var row = document.createElement('div');
    row.className = 'perm-row';
    var text = document.createElement('div');
    text.className = 'perm-row-text';
    var t = document.createElement('div'); t.className = 'perm-row-name'; t.textContent = label;
    var d = document.createElement('div'); d.className = 'perm-row-desc';
    d.textContent = meta.available ? description : (meta.why || 'Unsupported on this device');
    text.appendChild(t); text.appendChild(d);

    var sw = document.createElement('button');
    sw.type = 'button';
    sw.className = 'toggle' + (state ? ' on' : '');
    sw.setAttribute('role', 'switch');
    sw.setAttribute('aria-checked', state ? 'true' : 'false');
    sw.textContent = state ? 'Allowed' : 'Denied';
    sw.disabled = !meta.available;
    if (!meta.available) sw.textContent = 'Unavailable';
    sw.addEventListener('click', function () {
      if (!meta.available) return;
      sw.disabled = true;
      onToggle(!state).then(function (ok) {
        sw.disabled = false;
        loadPermissions(currentAppId);
      });
    });
    row.appendChild(text); row.appendChild(sw);
    return row;
  }

  function loadPermissions(appId) {
    var detail = $('permissions-detail');
    var state = $('permissions-state');
    if (!detail) return;
    currentAppId = appId;
    var apps = getAllApps();
    var app = null;
    for (var i = 0; i < apps.length; i++) if (apps[i].id === appId) { app = apps[i]; break; }
    if (!app) {
      detail.innerHTML = '';
      state.textContent = 'Unknown app: ' + appId;
      return;
    }
    state.textContent = 'Loading permissions for ' + (app.name || app.id) + '…';
    rpc('permissions', 'list', { app_id: appId }).then(function (r) {
      var doc = (r && r.result) ? r.result : (r || {});
      if (!doc || doc.success === false) {
        detail.innerHTML = '';
        state.textContent = 'Permission policy unavailable: ' + ((doc && (doc.error || doc.detail)) || 'bridge offline');
        return;
      }
      var granted = Array.isArray(doc.capabilities) ? doc.capabilities : [];
      var caps = canonicalCaps(app);
      function onFor(cap) { return decisionOn(doc, cap); }

      detail.innerHTML = '';
      var head = document.createElement('div');
      head.className = 'perm-head';
      head.innerHTML = '<strong>' + esc(app.name || app.id) + '</strong> <span class="perm-app-id">' + esc(app.id) + '</span>';
      detail.appendChild(head);

      var raw = rawCaps(app);
      if (raw.indexOf('location:read') !== -1 || raw.indexOf('location:manage') !== -1) {
        var locationHead = document.createElement('div');
        locationHead.className = 'perm-group';
        locationHead.textContent = 'Location';
        detail.appendChild(locationHead);
      }
      LOCATION_CONTROLS.forEach(function (pair) {
        var token = pair[0];
        if (raw.indexOf(token) === -1) return;
        var on = tokenOn(doc, token);
        var meta = enforcementMeta(doc, token);
        var row = toggleRow(token, pair[1], pair[2], on, meta, function (wantOn) {
          return rpc('permissions', wantOn ? 'grant' : 'deny', { app_id: appId, capability: token });
        });
        if (ACTUATOR_TOKENS[token]) {
          // Verify the actuator gate, not just the shared resource grant.
          // Settings must never paint a green switch that bridge RPC refuses.
          rpc('permissions', 'check', { app_id: appId, capability: token }).then(function (r) {
            var res = (r && r.result) ? r.result : (r || {});
            var denied = res.denied === true || res.success === false;
            if (!denied) return;
            var sw = row.querySelector('.toggle');
            if (!sw) return;
            sw.className = 'toggle';
            sw.setAttribute('aria-checked', 'false');
            sw.textContent = 'Denied';
            var desc = row.querySelector('.perm-row-desc');
            if (desc) desc.textContent = pair[2] + ' The bridge gate is not granted; toggle on to re-grant it.';
          });
        }
        detail.appendChild(row);
      });

      NUXEL_CONTROLS.forEach(function (pair) {
        var name = pair[0], label = pair[1], description = pair[2];
        var on = onFor(name);
        var meta = enforcementMeta(doc, name);
        detail.appendChild(toggleRow(name, label, description, on, meta, function (wantOn) {
          return rpc('permissions', wantOn ? 'grant' : 'deny', { app_id: appId, capability: name });
        }));
      });

      // Microphone and NFC are hardware gates the owner must be able to manage
      // for EVERY app, whether or not the app's manifest declares them: an app
      // that only requests them at runtime (Ferdium voice notes, a tag reader)
      // otherwise has no switch at all.  Show them before the declared list so
      // the toggle is always one tap away (and the same shared store feeds the
      // on-screen consent prompt).
      ['microphone', 'nfc'].forEach(function (cap) {
        if (caps.indexOf(cap) !== -1) return;
        var on = onFor(cap);
        var meta = enforcementMeta(doc, cap);
        detail.appendChild(toggleRow(cap, CAP_LABELS[cap] || cap,
          cap === 'microphone'
            ? 'Allow this app to record audio from the microphone.'
            : 'Allow this app to use NFC and read or write tags.', on, meta, function (wantOn) {
            return rpc('permissions', wantOn ? 'grant' : 'deny', { app_id: appId, capability: cap });
          }));
      });

      // Location read and location control are separate real resources.  Only
      // expose a row for a token the app actually declares, and never repeat
      // either one under "Other declared capabilities".
      var shown = {}; NUXEL_CONTROLS.forEach(function (p) { shown[p[0]] = true; });
      var others = caps.filter(function (c) { return !shown[c] && !c.match(/^location:/); });
      if (others.length) {
        var h = document.createElement('div'); h.className = 'perm-group';
        h.textContent = 'Other declared capabilities'; detail.appendChild(h);
        others.forEach(function (c) {
          var on = onFor(c);
          var label = CAP_LABELS[c] || c;
          var meta = enforcementMeta(doc, c);
          detail.appendChild(toggleRow(c, label, 'Declared by this app.', on, meta, function (wantOn) {
            return rpc('permissions', wantOn ? 'grant' : 'deny', { app_id: appId, capability: c });
          }));
        });
      }

      var note = document.createElement('div');
      note.className = 'perm-note';
      note.textContent = 'Grants are confirmed by the central permD policy service. Unsupported enforcement is never shown as granted.';
      detail.appendChild(note);
      state.textContent = 'Reviewing ' + (app.name || app.id) + '.';
    });
  }

  function populatePermissionsSelect() {
    var sel = $('permissions-app-select');
    if (!sel) return;
    var apps = getAllApps().filter(function (a) { return a && a.id; });
    sel.innerHTML = '';
    apps.forEach(function (a) {
      var o = document.createElement('option');
      o.value = a.id; o.textContent = (a.name || a.id) + ' — ' + a.id;
      sel.appendChild(o);
    });
    sel.addEventListener('change', function () { loadPermissions(sel.value); });
    if (apps.length) loadPermissions(apps[0].id);
  }

  // ---- boot ---------------------------------------------------------------
  function ready(fn) {
    if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', fn);
    else fn();
  }

  ready(function () {
    loadCanonicalApps().then(function () {
      // Populate the App select up-front so the Permissions tab is usable even
      // before the launcher-injected registry exists.
      var sel = $('permissions-app-select');
      if (sel && !sel.options.length) populatePermissionsSelect();
    });
    var appsTab = document.querySelector('.tab[data-tab="apps"]');
    if (appsTab) appsTab.addEventListener('click', loadApps);
    var permTab = document.querySelector('.tab[data-tab="permissions"]');
    if (permTab) permTab.addEventListener('click', function () {
      loadCanonicalApps().then(populatePermissionsSelect);
    });
  });
})();
