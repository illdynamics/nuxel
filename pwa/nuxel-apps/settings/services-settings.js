/* Nuxel Settings -> Services (PWNAGE-88000).
 *
 * Read-only inventory first, an explicit unlock gate, and allowlisted systemctl
 * actions through the bridge's `services` namespace.  Essential units cannot be
 * stopped/disabled and their restart/reload requires confirmation.  The bridge
 * never accepts a unit name that is not in the shipped service policy.
 */
(function () {
  'use strict';
  function bridge() {
    if (window.NuxelBridge && typeof window.NuxelBridge.call === 'function') return window.NuxelBridge;
    try {
      if (window.parent && window.parent !== window && window.parent.NuxelBridge &&
          typeof window.parent.NuxelBridge.call === 'function') return window.parent.NuxelBridge;
    } catch (e) {}
    return null;
  }
  function call(verb, params) {
    var b = bridge();
    if (!b) return Promise.resolve({ success: false, error: 'Nuxel bridge unavailable', offline: true });
    try { return Promise.resolve(b.call('services', verb, params || {})); }
    catch (e) { return Promise.resolve({ success: false, error: String(e && e.message || e) }); }
  }

  var unlocked = false;
  function setUnlocked(v) {
    unlocked = v;
    var gate = document.getElementById('services-unlock');
    var body = document.getElementById('services-actions');
    if (gate) gate.textContent = v ? 'LOCK SERVICES' : 'UNLOCK SERVICES';
    if (body) body.hidden = !v;
  }
  function toast(msg) {
    var el = document.getElementById('services-toast');
    if (!el) return;
    el.textContent = msg;
    el.classList.remove('hidden');
    clearTimeout(toast._t);
    toast._t = setTimeout(function () { el.classList.add('hidden'); }, 3200);
  }

  function confirmEssential(verb, unit) {
    return window.confirm(unit + ' is system-essential. ' + verb + ' it anyway?');
  }
  function confirmDaemon(verb) {
    return window.confirm('This runs systemd ' + verb + ' across the whole system and can interrupt core Nuxel services. Continue?');
  }

  function renderServices(doc) {
    var list = document.getElementById('services-list');
    if (!list) return;
    setUnlocked(!!doc.unlocked);
    list.textContent = '';
    (doc.services || []).forEach(function (s) {
      var row = document.createElement('div');
      row.className = 'svc-row' + (s.essential ? ' essential' : '');
      var info = document.createElement('div');
      info.className = 'svc-info';
      var name = document.createElement('div');
      name.className = 'svc-name';
      name.textContent = s.unit;
      var sub = document.createElement('div');
      sub.className = 'svc-state';
      sub.textContent = (s.active ? 'active' : 'inactive') + ' · ' + (s.enabled ? 'enabled' : 'disabled') +
        (s.essential ? ' · SYSTEM-ESSENTIAL' : '');
      info.appendChild(name); info.appendChild(sub);
      row.appendChild(info);

      var actions = document.createElement('div');
      actions.className = 'svc-actions';
      function btn(label, verb, extra) {
        var b = document.createElement('button');
        b.type = 'button';
        b.textContent = label;
        b.addEventListener('click', function () {
          var params = { unit: s.unit };
          if (extra) params.confirm = true;
          call(verb, params).then(function (r) {
            if (r && r.success !== false) { toast(s.unit + ' ' + verb + ' → ok'); refresh(); }
            else toast((r && (r.detail || r.error)) || (verb + ' failed'));
          });
        });
        return b;
      }
      if (s.active) {
        actions.appendChild(btn('Stop', 'stop'));
        actions.appendChild(btn('Restart', 'restart', s.essential));
        actions.appendChild(btn('Reload', 'reload', s.essential));
      } else {
        actions.appendChild(btn('Start', 'start'));
      }
      actions.appendChild(btn(s.enabled ? 'Disable' : 'Enable', s.enabled ? 'disable' : 'enable'));
      row.appendChild(actions);
      list.appendChild(row);
    });
  }

  function refresh() {
    call('list', {}).then(function (r) {
      if (r && r.success !== false) renderServices(r);
      else {
        var list = document.getElementById('services-list');
        if (list) list.textContent = '';
        var st = document.getElementById('services-state');
        if (st) st.textContent = 'Services unavailable: ' + ((r && (r.detail || r.error)) || 'no bridge');
      }
    });
  }

  document.addEventListener('DOMContentLoaded', function () {
    var unlockBtn = document.getElementById('services-unlock');
    if (unlockBtn) unlockBtn.addEventListener('click', function () {
      call(unlocked ? 'lock' : 'unlock', {}).then(function (r) {
        if (r && r.success !== false) setUnlocked(!!r.unlocked);
        else toast((r && (r.error || r.detail)) || 'unlock failed');
      });
    });
    var reloadBtn = document.getElementById('services-daemon-reload');
    if (reloadBtn) reloadBtn.addEventListener('click', function () {
      if (!confirmDaemon('daemon-reload')) return;
      call('daemon-reload', { confirm: true }).then(function (r) {
        toast((r && r.success !== false) ? 'daemon-reload ok' : ((r && (r.detail || r.error)) || 'daemon-reload failed'));
        refresh();
      });
    });
    var reexecBtn = document.getElementById('services-daemon-reexec');
    if (reexecBtn) reexecBtn.addEventListener('click', function () {
      if (!confirmDaemon('daemon-reexec')) return;
      call('daemon-reexec', { confirm: true }).then(function (r) {
        toast((r && r.success !== false) ? 'daemon-reexec ok' : ((r && (r.detail || r.error)) || 'daemon-reexec failed'));
        refresh();
      });
    });
    var refreshBtn = document.getElementById('services-refresh');
    if (refreshBtn) refreshBtn.addEventListener('click', refresh);
    var tab = document.querySelector('.tab[data-tab="services"]');
    if (tab) tab.addEventListener('click', refresh);
    refresh();
  });
}());
