// Nuxel Settings — Power surface (battery modes + power menu)
//
// Mission areas 17 (power menu) and 18 (battery/power modes) for the S10+
// (beyond2lte). This is a Nuxel registry app surface: it is opened inside the
// launcher's .pwa-frame (or standalone) and talks to the SHARED host channel
// (window.NuxelHost, or the parent frame's when iframed). It writes nothing
// itself and executes no shell command.
//
// Single source of truth: the menu table and the three profiles are read from
// the SAME documents the console tool uses —
//     /etc/nuxel/power/power-menu.json   (menu entries + per-entry gate)
//     /etc/nuxel/power/power.json        (adaptive / balanced / performance)
// so the finger path and `nuxel-power-diag.sh` can never disagree. When the
// documents are not reachable (offline / VM without the service), the embedded
// defaults below are used and the UI says so instead of pretending.
//
// NO-FLASH INVARIANT: the Recovery and Download Mode entries are rendered so the
// device's capabilities are visible, but they are REFUSED here as well as in the
// gate — clicking them shows the refusal reason and performs no action. Nothing
// in this file can reach a bootloader, a partition or a block device.
(function () {
  'use strict';

  // ---------- host channel (same shape as settings.js / nuxel-pwa-host) -------
  var HOST = null;
  function host() {
    if (HOST) return HOST;
    HOST = (window.NuxelHost && window.NuxelHost.available) ? window.NuxelHost
         : (window.parent && window.parent !== window && window.parent.NuxelHost) ? window.parent.NuxelHost
         : null;
    return HOST;
  }
  function call(method, params) {
    var h = host();
    if (h && h.available) return h.call(method, params);
    return Promise.resolve({ ok: false, offline: true });
  }
  function action(name, extra) {
    var p = { action: name };
    if (extra) { for (var k in extra) { if (Object.prototype.hasOwnProperty.call(extra, k)) p[k] = extra[k]; } }
    return call('system.action', p);
  }

  // ---------- embedded defaults (identical shape to the shipped JSON) --------
  var DEFAULT_MENU = {
    schema_version: 1, invoked_by: { timeout_ms: 15000 },
    entries: [
      { id: 'lock', label: 'Lock screen', action: 'screen-lock', trigger_allowed: true,
        requires_owner_confirmation: false,
        note: 'Screen off + lock. Reversible with a short POWER press.' },
      { id: 'restart', label: 'Restart', action: 'restart', trigger_allowed: false,
        requires_owner_confirmation: true,
        refusal_reason: 'gated — reboot-gate.json is closed because the owner is absent and no repository-side reboot policy has authorised a restart in this cycle.' },
      { id: 'power-off', label: 'Power off', action: 'poweroff', trigger_allowed: false,
        requires_owner_confirmation: true,
        refusal_reason: 'gated — powering the handset off with no owner present would strand the mission.' },
      { id: 'recovery', label: 'Recovery', action: 'boot-recovery', trigger_allowed: false,
        requires_owner_confirmation: true,
        refusal_reason: 'NO_FLASH_INVARIANT — entering Recovery means leaving Linux for the Samsung bootloader; this mission triggers no bootloader interface.' },
      { id: 'download-mode', label: 'Download Mode', action: 'boot-download-mode', trigger_allowed: false,
        requires_owner_confirmation: true,
        refusal_reason: 'NO_FLASH_INVARIANT — Download Mode exists only to flash, and this mission performs no flashing of any kind.' }
    ]
  };
  var DEFAULT_POLICY = {
    default: 'balanced',
    list: {
      adaptive: { label: 'Adaptive', summary: 'Longest runtime. Low-power governor; background work idles aggressively.', brightness_cap_percent: 70 },
      balanced: { label: 'Balanced', summary: 'Default. Keeps the interactive feel of the launcher without pinning the big cores.', brightness_cap_percent: 100 },
      performance: { label: 'Performance', summary: 'Highest responsiveness while charging or plugged in.', brightness_cap_percent: 100 }
    }
  };

  var WORK = { menu: null, policy: null, active: 'balanced', state: null, docSource: 'embedded' };

  function parse(text, dflt) {
    try {
      var o = JSON.parse(text);
      return (o && typeof o === 'object') ? o : JSON.parse(JSON.stringify(dflt));
    } catch (e) { return JSON.parse(JSON.stringify(dflt)); }
  }
  function el(id) { return document.getElementById(id); }
  function esc(s) {
    return String(s == null ? '' : s).replace(/[&<>"]/g, function (c) {
      return ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' })[c];
    });
  }

  // ---------- document loading ---------------------------------------------
  // The canonical documents live at /etc/nuxel/power/. We ask the host for them
  // by name; a host that does not implement config.get for these names is
  // reported as "embedded defaults" rather than silently faked.
  function loadDocs() {
    return Promise.all([
      call('config.get', { name: 'power-menu', path: '/etc/nuxel/power/power-menu.json' }),
      call('config.get', { name: 'power', path: '/etc/nuxel/power/power.json' }),
      call('power.status', {})
    ]).then(function (r) {
      var menuRes = r[0] || {}, polRes = r[1] || {}, stRes = r[2] || {};
      if (typeof menuRes.text === 'string' && menuRes.text) { WORK.menu = parse(menuRes.text, DEFAULT_MENU); WORK.docSource = 'live'; }
      else { WORK.menu = JSON.parse(JSON.stringify(DEFAULT_MENU)); }
      if (typeof polRes.text === 'string' && polRes.text) {
        var p = parse(polRes.text, null);
        if (p && p.profiles && p.profiles.list) {
          WORK.policy = { default: p.profiles.default || 'balanced', list: p.profiles.list };
        }
      }
      if (!WORK.policy) {
        WORK.policy = { default: DEFAULT_POLICY.default, list: {} };
        for (var k in DEFAULT_POLICY.list) { WORK.policy.list[k] = DEFAULT_POLICY.list[k]; }
      }
      if (stRes && typeof stRes === 'object' && !stRes.offline) { WORK.state = stRes; }
      if (WORK.state && WORK.state.profile && WORK.state.profile.active) { WORK.active = WORK.state.profile.active; }
      render();
    });
  }

  // ---------- rendering -----------------------------------------------------
  function render() {
    renderBattery();
    renderModes();
    renderMenu();
    var note = el('power-source');
    if (note) {
      note.textContent = WORK.docSource === 'live'
        ? 'Reading /etc/nuxel/power/power-menu.json and power.json (single source of truth).'
        : 'Power documents not reachable from this context — showing the embedded defaults. Battery state is NOT claimed.';
    }
  }

  function renderBattery() {
    var box = el('battery-state');
    if (!box) return;
    var s = WORK.state;
    if (!s || s.offline || s.state === undefined) {
      box.innerHTML = '<span class="bad">no live battery evidence</span> — ' +
        'run <code>nuxel-power-diag.sh status</code> on the handset; a readable node is not proof of charging.';
      return;
    }
    var g = s.gauge || {};
    var cap = g.capacity_percent === '' || g.capacity_percent == null ? '—' : esc(g.capacity_percent) + '%';
    var row = function (k, v) { return '<div class="kv"><span>' + k + '</span><b>' + esc(v || '—') + '</b></div>'; };
    box.innerHTML =
      row('boot mode', s.boot_mode) +
      row('gauge', g.present ? (g.device || 'present') : 'none (BLOCKED_KERNEL)') +
      row('capacity', cap) +
      row('status', g.status) +
      row('health', g.health) +
      row('verdict', s.state) +
      '<p class="hint">Charging behaviour stays NEEDS_OWNER_TEST until observed with a real charger ' +
      '(manual-proof/24-battery-power.md).</p>';
  }

  function renderModes() {
    var box = el('modes');
    if (!box) return;
    box.innerHTML = '';
    var list = WORK.policy.list;
    Object.keys(list).forEach(function (id) {
      var m = list[id];
      var card = document.createElement('button');
      card.type = 'button';
      card.className = 'mode-card' + (id === WORK.active ? ' active' : '');
      card.setAttribute('data-mode', id);
      card.setAttribute('aria-pressed', id === WORK.active ? 'true' : 'false');
      card.innerHTML = '<span class="mode-name">' + esc(m.label || id) + '</span>' +
        '<span class="mode-sum">' + esc(m.summary || '') + '</span>' +
        (m.brightness_cap_percent ? '<span class="mode-cap">brightness cap ' + esc(m.brightness_cap_percent) + '%</span>' : '');
      card.addEventListener('click', function () { applyMode(id); });
      box.appendChild(card);
    });
  }

  function applyMode(id) {
    var status = el('mode-status');
    if (status) status.textContent = 'applying ' + id + '…';
    // One channel: the same action the console tool calls. The tool maps the
    // profile to a REAL governor + cgroup weight and persists the choice.
    call('power.apply-profile', { mode: id }).then(function (r) {
      if (r && r.offline) {
        if (status) status.textContent = 'host unavailable — profile NOT applied (no fake success)';
        return;
      }
      if (r && r.ok === false) {
        if (status) status.textContent = 'refused: ' + (r.error || r.reason || 'unknown');
        return;
      }
      WORK.active = id;
      renderModes();
      if (status) status.textContent = 'profile ' + id + ' applied and persisted' +
        (r && r.governor ? ' (governor ' + r.governor + ')' : '');
    });
  }

  function renderMenu() {
    var box = el('menu-entries');
    if (!box) return;
    box.innerHTML = '';
    WORK.menu.entries.forEach(function (e) {
      var b = document.createElement('button');
      b.type = 'button';
      b.className = 'menu-entry' + (e.trigger_allowed ? ' allowed' : ' refused');
      b.setAttribute('data-entry', e.id);
      b.innerHTML = '<span class="me-label">' + esc(e.label) + '</span>' +
        '<span class="me-state">' + (e.trigger_allowed ? 'ready' : 'refused') + '</span>';
      b.addEventListener('click', function () { fire(e, b); });
      box.appendChild(b);
    });
  }

  function fire(e, node) {
    var out = el('menu-result');
    if (!e.trigger_allowed) {
      // Refusal is the designed behaviour — show WHY, do nothing else.
      if (out) out.innerHTML = '<b>' + esc(e.label) + ' refused:</b> ' + esc(e.refusal_reason || 'refused by policy');
      node.classList.add('shake');
      window.setTimeout(function () { node.classList.remove('shake'); }, 400);
      return;
    }
    if (e.requires_owner_confirmation && !window.confirm('Confirm: ' + e.label + '?')) {
      if (out) out.textContent = e.label + ' cancelled';
      return;
    }
    action(e.action, { entry: e.id }).then(function (r) {
      if (out) {
        out.textContent = (r && r.offline) ? 'host unavailable — no action taken'
          : (r && r.ok === false) ? (e.label + ' refused: ' + (r.error || r.reason || 'unknown'))
          : e.label + ' done';
      }
    });
  }

  // ---------- wire up -------------------------------------------------------
  function boot() {
    var btn = el('power-close');
    if (btn) btn.addEventListener('click', function () {
      var f = window.frameElement;
      if (f && window.parent !== window && window.parent.NuxelLauncherClose) window.parent.NuxelLauncherClose();
      else if (f && f.parentNode) f.parentNode.removeChild(f);
    });
    var refresh = el('power-refresh');
    if (refresh) refresh.addEventListener('click', function () { loadDocs(); });
    loadDocs();
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', boot);
  else boot();

  // Expose the load path for the offline test (no side effects).
  window.NuxelPowerSurface = { load: loadDocs, defaults: { menu: DEFAULT_MENU, policy: DEFAULT_POLICY } };
})();
