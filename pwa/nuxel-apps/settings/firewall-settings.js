/* Nuxel Settings — Firewall (briq-05b). Full owner editor.
 *
 * Settings is the source-of-truth surface for firewall policy. It reads and
 * writes the SAME `services/nuxel-firewall` provider that the dedicated
 * Firewall app wraps; nothing here stores a second copy of the policy.
 */
(function () {
  'use strict';

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
    if (!b) return Promise.resolve({ success: false, error: 'bridge unavailable', offline: true });
    try { return Promise.resolve(b.call('firewall', verb, params || {})); }
    catch (e) { return Promise.resolve({ success: false, error: String(e && e.message || e), offline: true }); }
  }

  function $ (id) { return document.getElementById(id); }
  function setText(id, v) { var el = $(id); if (el) el.textContent = v; }

  var S = { status: null, rules: null, apps: null, listeners: null, pending: null };
  var timer = null;

  function data(r) { return r && r.data ? r.data : r; }

  function stateLabel() {
    var st = S.status;
    if (!st) return 'UNKNOWN';
    if (S.pending && S.pending.txid) return 'UNCONFIRMED';
    if (st.backend === 'none') return 'NOT ENFORCED';
    if (st.enabled) return 'ACTIVE';
    return 'INACTIVE';
  }

  function renderStatus() {
    var st = S.status || {};
    var d = st.defaults || {};
    setText('fw-settings-state', JSON.stringify({
      state: stateLabel(),
      backend: st.backend || 'unknown',
      kernel: st.kernel_release || '?',
      enabled: !!st.enabled,
      incoming: (d.input || 'deny') + ' by default',
      forwarded: (d.forward || 'deny') + ' by default',
      outgoing: (d.output || 'allow') + ' by default',
      ipv4: st.ipv4 === true, ipv6: st.ipv6 === true,
      per_app_enforceable: !!(st.per_app && st.per_app.enforceable_now)
    }, null, 2));
    renderRollback();
  }

  function renderRollback() {
    var p = S.pending;
    var confirm = $('fw-confirm'), rollback = $('fw-rollback'), apply = $('fw-apply');
    if (!confirm || !rollback) return;
    if (p && p.txid) {
      confirm.disabled = false;
      rollback.disabled = false;
      if (apply) apply.disabled = true;
      if (timer) clearInterval(timer);
      var deadline = p.deadline || 0;
      var tick = function () {
        var left = Math.max(0, Math.round((deadline - (Date.now() / 1000))));
        setText('fw-action-result', 'Unconfirmed apply — confirm or roll back in ' + left + 's');
        if (left <= 0) load();
      };
      tick();
      timer = setInterval(tick, 1000);
    } else {
      confirm.disabled = true;
      rollback.disabled = true;
      if (apply) apply.disabled = false;
    }
  }

  function renderDefaults() {
    var r = S.rules || {};
    var d = r.defaults || {};
    var input = $('fw-input'), forward = $('fw-forward'), output = $('fw-output');
    if (input) input.value = d.input || 'deny';
    if (forward) forward.value = d.forward || 'deny';
    if (output) output.value = d.output || 'allow';
  }

  function svcRow(id, label, port, cidrs, enabled) {
    var row = document.createElement('div');
    row.className = 'svc-row';
    var info = document.createElement('div');
    info.className = 'svc-info';
    var name = document.createElement('div');
    name.className = 'svc-name';
    name.textContent = label;
    var state = document.createElement('div');
    state.className = 'svc-state';
    state.textContent = 'port ' + port + (cidrs && cidrs.length ? ' · from ' + cidrs.join(', ') : '');
    info.appendChild(name); info.appendChild(state);
    var actions = document.createElement('div');
    actions.className = 'svc-actions';
    var btn = document.createElement('button');
    btn.type = 'button';
    btn.textContent = enabled ? 'Enabled' : 'Disabled';
    btn.className = enabled ? 'primary' : 'ghost';
    btn.addEventListener('click', function () {
      btn.disabled = true;
      rpc('set-service-rule', { service_id: id, source_cidrs: cidrs || [], enabled: !enabled })
        .then(function () { load(); });
    });
    actions.appendChild(btn);
    row.appendChild(info); row.appendChild(actions);
    return row;
  }

  function renderServices() {
    var box = $('fw-services');
    if (!box) return;
    box.innerHTML = '';
    var rules = (S.rules && S.rules.services) || {};
    var listeners = S.listeners || {};

    var sshCidrs = (listeners.sshd && listeners.sshd.allow_cidrs) || [];
    var sshPort = ((listeners.sshd && listeners.sshd.port) || [22]);
    if (Array.isArray(sshPort)) sshPort = sshPort.length ? sshPort : [22];
    var sshEnabled = !!(listeners.ssh_listeners && listeners.ssh_listeners.length);
    if (rules['nuxel-ssh-owner']) {
      var rr = rules['nuxel-ssh-owner'];
      sshCidrs = rr.source_cidrs || sshCidrs;
      sshPort = rr.port || sshPort;
      sshEnabled = !!rr.enabled;
    }
    box.appendChild(svcRow('nuxel-ssh-owner', 'SSH console (key-only)', Array.isArray(sshPort) ? sshPort[0] : sshPort, sshCidrs, sshEnabled));

    if (listeners.xrdp_listeners && listeners.xrdp_listeners.length || rules['nuxel-xrdp-owner-lan']) {
      var xr = rules['nuxel-xrdp-owner-lan'] || {};
      box.appendChild(svcRow('nuxel-xrdp-owner-lan', 'XRDP (TLS+PAM)', xr.port || 3389,
        xr.source_cidrs || ['127.0.0.1/32'], !!(xr.enabled)));
    }
    if (listeners.vnc_listeners && listeners.vnc_listeners.length || rules['nuxel-vnc-owner-lan']) {
      var vr = rules['nuxel-vnc-owner-lan'] || {};
      box.appendChild(svcRow('nuxel-vnc-owner-lan', 'VNC / wayvnc (loopback/SSH tunnel only)', vr.port || 5900,
        vr.source_cidrs || ['127.0.0.1/32'], !!(vr.enabled)));
    }
    if (!box.children.length) {
      var e = document.createElement('div');
      e.className = 'svc-row';
      e.innerHTML = '<div class="svc-info"><div class="svc-name">No inbound service rules prepared</div><div class="svc-state">Run Dry run to populate rules from live sshd/socket facts.</div></div>';
      box.appendChild(e);
    }
  }

  function renderApps() {
    var box = $('fw-apps');
    if (!box) return;
    box.innerHTML = '';
    var apps = (S.apps && S.apps.apps) || [];
    var perApp = !!(S.apps && S.apps.per_app_supported);
    var rules = (S.rules && S.rules.apps) || {};
    if (!apps.length) {
      var e = document.createElement('div'); e.className = 'app-row'; e.textContent = 'No installed apps reported.';
      box.appendChild(e); return;
    }
    apps.forEach(function (a) {
      var row = document.createElement('div');
      row.className = 'app-row';
      var info = document.createElement('div');
      info.className = 'app-row-info';
      var name = document.createElement('div');
      name.className = 'app-row-name';
      name.textContent = a.name || a.app_id;
      var id = document.createElement('div');
      id.className = 'app-row-id';
      id.textContent = a.app_id + ' · ' + (a.type || 'app');
      info.appendChild(name); info.appendChild(id);
      row.appendChild(info);

      if (perApp) {
        var sel = document.createElement('select');
        sel.className = 'app-orientation-select';
        [['inherit', 'Inherit'], ['allow', 'Allow'], ['deny', 'Block']].forEach(function (p) {
          var o = document.createElement('option'); o.value = p[0]; o.textContent = p[1]; sel.appendChild(o);
        });
        var cur = (rules[a.app_id] && rules[a.app_id].outbound) || 'inherit';
        sel.value = cur;
        sel.addEventListener('change', function () {
          sel.disabled = true;
          rpc('set-app-rule', { app_id: a.app_id, outbound: sel.value }).then(function () { load(); });
        });
        row.appendChild(sel);
      } else {
        var badge = document.createElement('span');
        badge.className = 'toggle';
        badge.textContent = 'unsupported';
        badge.disabled = true;
        row.appendChild(badge);
      }
      box.appendChild(row);
    });
  }

  function load() {
    return Promise.all([
      rpc('status', {}).then(function (r) { S.status = data(r); }),
      rpc('rules', {}).then(function (r) { S.rules = data(r); }),
      rpc('installed-apps', {}).then(function (r) { S.apps = data(r); }),
      rpc('listeners', {}).then(function (r) { S.listeners = data(r); }),
      rpc('pending-transaction', {}).then(function (r) {
        var d = data(r);
        S.pending = (d && d.txid) ? d : null;
      })
    ]).then(function () {
      renderStatus(); renderDefaults(); renderServices(); renderApps();
    }).catch(function () {
      S.status = null; renderStatus();
    });
  }

  function action(verb, params) {
    setText('fw-action-result', 'Working…');
    return rpc(verb, params).then(function (r) {
      setText('fw-action-result', JSON.stringify(data(r), null, 2));
      load();
    }).catch(function (e) {
      setText('fw-action-result', 'Error: ' + (e && e.message || e));
    });
  }

  function openApp() {
    var b = bridge();
    var target = { app_id: 'org.nuxel.Firewall', target: 'org.nuxel.Firewall', source: 'settings' };
    if (b) { b.call('apps', 'launch', target); return; }
    fetch('/api/v1/apps/exec', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(target)
    });
  }

  document.addEventListener('DOMContentLoaded', function () {
    var open = $('fw-settings-open');
    var refresh = $('fw-settings-refresh');
    if (open) open.addEventListener('click', openApp);
    if (refresh) refresh.addEventListener('click', load);
    if ($('fw-save-defaults')) $('fw-save-defaults').addEventListener('click', function () {
      var btn = this;
      btn.disabled = true;
      var jobs = ['fw-input', 'fw-forward', 'fw-output'].map(function (id) {
        var sel = $(id);
        return rpc('set-direction-default', { direction: sel.dataset.direction, action: sel.value });
      });
      Promise.all(jobs).then(function () {
        btn.disabled = false;
        setText('fw-action-result', 'Direction defaults saved. Dry run / Apply to enforce.');
        load();
      });
    });
    if ($('fw-dry-run')) $('fw-dry-run').addEventListener('click', function () { action('dry-run', {}); });
    if ($('fw-apply')) $('fw-apply').addEventListener('click', function () { action('apply', { rollback_after: 60 }); });
    if ($('fw-confirm')) $('fw-confirm').addEventListener('click', function () { action('confirm', {}); });
    if ($('fw-rollback')) $('fw-rollback').addEventListener('click', function () { action('rollback', {}); });
    var tab = document.querySelector('.tab[data-tab="firewall"]');
    if (tab) tab.addEventListener('click', load);
    load();
  });
})();
