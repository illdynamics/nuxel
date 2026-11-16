/* Nuxel Permission Manager — wrapper around the central permD policy service.
 * Settings is the same source of truth; this app only reads/writes that store. */
(function () {
  'use strict';

  var NUXEL_CONTROLS = [
    ['zoom', 'Zoom with two fingers', 'Whole-app two-finger zoom (separate from in-app zoom).'],
    ['fullscreen', 'Fullscreen', 'App-requested exclusive fullscreen / hide system chrome.'],
    ['casting', 'Casting', 'Future Nuxel casting (not available until a casting service exists).'],
    ['mirroring', 'Mirroring', 'Show this app on a mirrored external display.']
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
  function rpc(verb, params) {
    var b = bridge();
    if (!b) return Promise.resolve({ success: false, error: 'Nuxel bridge unavailable', offline: true });
    try { return Promise.resolve(b.call('permissions', verb, params || {})); }
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
    NUXEL_CONTROLS.forEach(function (p) { out[p[0]] = true; });
    caps.forEach(function (c) { var id = resolveToken(c); if (id) out[id] = true; });
    return Object.keys(out).sort();
  }

  function decisionOn(doc, cap) {
    var d = (doc && doc.decisions && doc.decisions[cap]) || null;
    if (d) return d.decision === 'allow';
    return Array.isArray(doc && doc.capabilities) && doc.capabilities.indexOf(cap) !== -1;
  }

  function enforcementMeta(doc, cap) {
    var enf = (doc && doc.enforcement && doc.enforcement[cap]) || null;
    if (!enf) return { available: true, why: '' };
    var mech = enf.mechanisms || [];
    var unavailable = enf.verdict === 'NOT_SUPPORTED_ON_DEVICE' || enf.enforceable === 'no' ||
        (mech.length === 1 && mech[0] === 'none');
    return { available: !unavailable, why: enf.limitation || (unavailable ? 'Unsupported on this device' : '') };
  }

  var currentAppId = null;
  function load(appId) {
    currentAppId = appId;
    var state = $('state');
    var detail = $('detail');
    var apps = getAllApps();
    var app = null;
    for (var i = 0; i < apps.length; i++) if (apps[i].id === appId) { app = apps[i]; break; }
    if (!app) { detail.innerHTML = ''; state.textContent = 'Unknown app: ' + appId; return; }
    state.textContent = 'Loading permissions for ' + (app.name || app.id) + '…';
    rpc('list', { app_id: appId }).then(function (r) {
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

      function addRow(cap, label, desc) {
        var on = onFor(cap);
        var meta = enforcementMeta(doc, cap);
        var row = document.createElement('div');
        row.className = 'perm-row';
        var text = document.createElement('div');
        text.className = 'perm-row-text';
        var t = document.createElement('div'); t.className = 'perm-row-name'; t.textContent = label;
        var d = document.createElement('div'); d.className = 'perm-row-desc';
        d.textContent = meta.available ? desc : (meta.why || 'Unsupported on this device');
        text.appendChild(t); text.appendChild(d);
        var sw = document.createElement('button');
        sw.type = 'button';
        sw.className = 'toggle' + (on ? ' on' : '');
        sw.setAttribute('role', 'switch');
        sw.setAttribute('aria-checked', on ? 'true' : 'false');
        sw.textContent = meta.available ? (on ? 'Allowed' : 'Denied') : 'Unavailable';
        sw.disabled = !meta.available;
        sw.addEventListener('click', function () {
          if (!meta.available) return;
          sw.disabled = true;
          var verb = on ? 'deny' : 'grant';
          rpc(verb, { app_id: appId, capability: cap }).then(function (res) {
            sw.disabled = false;
            load(appId);
          });
        });
        row.appendChild(text); row.appendChild(sw);
        detail.appendChild(row);
      }

      NUXEL_CONTROLS.forEach(function (p) { addRow(p[0], p[1], p[2]); });
      var shown = {}; NUXEL_CONTROLS.forEach(function (p) { shown[p[0]] = true; });
      var others = caps.filter(function (c) { return !shown[c]; });
      if (others.length) {
        var h = document.createElement('div'); h.className = 'perm-group';
        h.textContent = 'Other declared capabilities'; detail.appendChild(h);
        others.forEach(function (c) { addRow(c, CAP_LABELS[c] || c, 'Declared by this app.'); });
      }
      var note = document.createElement('div');
      note.className = 'perm-note';
      note.textContent = 'Grants are confirmed by the central permD policy service; unsupported enforcement is never shown as granted.';
      detail.appendChild(note);
      state.textContent = 'Reviewing ' + (app.name || app.id) + '.';
      $('policy-line').textContent = 'Central permD policy · same store as Settings';
    });
  }

  function populate() {
    var sel = $('app-select');
    var apps = getAllApps().filter(function (a) { return a && a.id; });
    sel.innerHTML = '';
    apps.forEach(function (a) {
      var o = document.createElement('option');
      o.value = a.id; o.textContent = (a.name || a.id) + ' — ' + a.id;
      sel.appendChild(o);
    });
    sel.addEventListener('change', function () { load(sel.value); });
    if (apps.length) load(apps[0].id);
    else { $('state').textContent = 'No installed apps found.'; }
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', populate);
  else populate();
})();
