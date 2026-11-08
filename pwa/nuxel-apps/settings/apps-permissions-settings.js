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

  var CAP_LABELS = {
    'microphone': 'Microphone', 'camera': 'Camera', 'location': 'Location',
    'contacts': 'Contacts', 'calendar': 'Calendar', 'call': 'Phone calls',
    'sms': 'SMS', 'notifications': 'Notifications', 'network': 'Network',
    'bluetooth': 'Bluetooth', 'usb': 'USB devices', 'storage': 'Files & storage',
    'media_library': 'Media library', 'downloads': 'Downloads',
    'background': 'Background execution', 'local_shell': 'Local shell / PTY',
    'system_inspect': 'System inspection (read-only)', 'input_devices': 'Input devices',
    'catalog_read': 'App catalog (read)', 'app_install': 'Install apps',
    'app_remove': 'Remove apps', 'clipboard': 'Clipboard', 'display': 'Display ownership',
    'audio': 'Audio playback', 'clock_status': 'Clock & alarms', 'phone_status': 'Phone status',
    'sms_send_raw': 'Raw modem access'
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

  function getAllApps() {
    var reg = appRegistry();
    if (reg && typeof reg.getAllApps === 'function') {
      var apps = reg.getAllApps();
      if (Array.isArray(apps)) return apps;
    }
    return [];
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
  function canonicalCaps(app) {
    var caps = Array.isArray(app.capabilities) ? app.capabilities.slice() : [];
    var out = {};
    NUXEL_CONTROLS.forEach(function (pair) { out[pair[0]] = true; });
    caps.forEach(function (c) { var id = resolveToken(c); if (id) out[id] = true; });
    return Object.keys(out).sort();
  }

  // ---- Apps tab -----------------------------------------------------------
  function renderApps(orientationDoc) {
    var box = $('apps-list');
    if (!box) return;
    var apps = getAllApps().filter(function (a) { return a && a.id; });
    var defaults = (orientationDoc && orientationDoc.apps) || {};
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
      sel.addEventListener('change', function () {
        sel.disabled = true;
        rpc('apps', 'set-orientation-default', { app_id: a.id, orientation: sel.value })
          .then(function (r) {
            sel.disabled = false;
            if (!r || r.success === false) {
              sel.value = defaults[a.id] || 'inherit';
            } else {
              defaults[a.id] = sel.value;
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

      row.appendChild(info); row.appendChild(sel); row.appendChild(perm);
      box.appendChild(row);
    });
    var st = $('apps-state');
    if (st) st.textContent = apps.length + ' installed app' + (apps.length === 1 ? '' : 's') + '.';
  }

  function loadApps() {
    rpc('apps', 'orientation-defaults', {}).then(function (r) {
      renderApps(r && r.result ? r.result : r);
    });
  }

  // ---- Permissions tab ----------------------------------------------------
  var currentAppId = null;

  function decisionOn(doc, cap) {
    var d = (doc && doc.decisions && doc.decisions[cap]) || null;
    if (d) return d.decision === 'allow';
    return Array.isArray(doc && doc.capabilities) && doc.capabilities.indexOf(cap) !== -1;
  }

  function enforcementMeta(doc, cap) {
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

      NUXEL_CONTROLS.forEach(function (pair) {
        var name = pair[0], label = pair[1], description = pair[2];
        var on = onFor(name);
        var meta = enforcementMeta(doc, name);
        detail.appendChild(toggleRow(name, label, description, on, meta, function (wantOn) {
          return rpc('permissions', wantOn ? 'grant' : 'deny', { app_id: appId, capability: name });
        }));
      });

      var shown = {}; NUXEL_CONTROLS.forEach(function (p) { shown[p[0]] = true; });
      var others = caps.filter(function (c) { return !shown[c]; });
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
    var appsTab = document.querySelector('.tab[data-tab="apps"]');
    if (appsTab) appsTab.addEventListener('click', loadApps);
    var permTab = document.querySelector('.tab[data-tab="permissions"]');
    if (permTab) permTab.addEventListener('click', populatePermissionsSelect);
  });
})();
