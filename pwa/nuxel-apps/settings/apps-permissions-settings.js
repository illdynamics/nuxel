/* Nuxel Settings — Apps & Permissions (PWNAGE-86000).
 *
 * Apps: per-app default orientation (launch preference) plus a shortcut to
 * the app's permission controls.
 *
 * Permissions: a touch-first review of every installed app's declared
 * capabilities and the four Nuxel-specific controls (zoom, fullscreen,
 * casting, mirroring).  State is rendered from the bridge; anything offline
 * or unsupported is shown as denied, never invented as granted.
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
    'audio': 'Audio playback', 'clock_status': 'Clock & alarms', 'phone_status': 'Phone status'
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

  function canonicalCaps(app) {
    var caps = Array.isArray(app.capabilities) ? app.capabilities.slice() : [];
    var base = caps.map(function (c) { return String(c).split(':')[0]; });
    var out = {};
    NUXEL_CONTROLS.forEach(function (pair) { out[pair[0]] = true; });
    base.forEach(function (c) { if (c) out[c] = true; });
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
      $('apps-state').textContent = 'No installed apps found.';
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
    $('apps-state').textContent = apps.length + ' installed app' + (apps.length === 1 ? '' : 's') + '.';
  }

  function loadApps() {
    rpc('apps', 'orientation-defaults', {}).then(function (r) {
      renderApps(r && r.result ? r.result : r);
    });
  }

  // ---- Permissions tab ----------------------------------------------------
  var GRANTS = {};

  function toggleRow(name, label, description, state, onToggle) {
    var row = document.createElement('div');
    row.className = 'perm-row';
    var text = document.createElement('div');
    text.className = 'perm-row-text';
    var t = document.createElement('div'); t.className = 'perm-row-name'; t.textContent = label;
    var d = document.createElement('div'); d.className = 'perm-row-desc'; d.textContent = description;
    text.appendChild(t); text.appendChild(d);

    var sw = document.createElement('button');
    sw.className = 'toggle' + (state ? ' on' : '');
    sw.setAttribute('role', 'switch');
    sw.setAttribute('aria-checked', state ? 'true' : 'false');
    sw.textContent = state ? 'Allowed' : 'Denied';
    sw.disabled = true;
    sw.addEventListener('click', function () {
      sw.disabled = true;
      onToggle(!state).then(function () { loadPermissions(currentAppId); });
    });
    row.appendChild(text); row.appendChild(sw);
    return row;
  }

  var currentAppId = null;

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
      GRANTS[appId] = doc;
      var granted = Array.isArray(doc.capabilities) ? doc.capabilities : [];
      var caps = canonicalCaps(app);

      detail.innerHTML = '';
      var head = document.createElement('div');
      head.className = 'perm-head';
      head.innerHTML = '<strong>' + esc(app.name || app.id) + '</strong> <span class="perm-app-id">' + esc(app.id) + '</span>';
      detail.appendChild(head);

      // Four Nuxel-specific controls first.
      NUXEL_CONTROLS.forEach(function (pair) {
        var name = pair[0], label = pair[1], description = pair[2];
        var on = granted.indexOf(name) !== -1;
        detail.appendChild(toggleRow(name, label, description, on, function (wantOn) {
          var verb = wantOn ? 'request' : 'revoke';
          return rpc('permissions', verb, { app_id: appId, capability: name });
        }));
      });

      // Remaining declared capabilities.
      var shown = {}; NUXEL_CONTROLS.forEach(function (p) { shown[p[0]] = true; });
      var others = caps.filter(function (c) { return !shown[c]; });
      if (others.length) {
        var h = document.createElement('div'); h.className = 'perm-group';
        h.textContent = 'Other declared capabilities'; detail.appendChild(h);
        others.forEach(function (c) {
          var on = granted.indexOf(c) !== -1;
          var label = CAP_LABELS[c] || c;
          detail.appendChild(toggleRow(c, label, 'Declared by this app.', on, function (wantOn) {
            var verb = wantOn ? 'request' : 'revoke';
            return rpc('permissions', verb, { app_id: appId, capability: c });
          }));
        });
      }

      var note = document.createElement('div');
      note.className = 'perm-note';
      note.textContent = 'Offline, unsupported or unverified enforcement is always denied. Grants are confirmed by the central policy service only.';
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
