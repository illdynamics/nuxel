/* Nuxel Firewall — PWA (AFWall+-inspired, honest wrapper).
 * Every state is derived from the live `services/nuxel-firewall` provider
 * readback. No saved JSON is treated as ACTIVE. */
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
    if (!b) {
      return fetch('/api/v1/rpc', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ app_id: 'org.nuxel.Firewall', namespace: 'firewall', verb: verb, params: params || {} })
      }).then(function (r) { return r.json(); }).then(function (r) {
        return (r && r.result !== undefined) ? r.result : { success: false, error: 'bad bridge response', offline: true };
      }).catch(function () {
        return { success: false, error: 'bridge unavailable', offline: true };
      });
    }
    try { return Promise.resolve(b.call('firewall', verb, params || {})); }
    catch (e) { return Promise.resolve({ success: false, error: String(e), offline: true }); }
  }

  var $ = function (id) { return document.getElementById(id); };
  function setText(id, v) { var el = $(id); if (el) el.textContent = v; }
  function data(r) { return r && r.data ? r.data : r; }

  var state = { status: null, capabilities: null, apps: null, services: null, rules: null, pending: null };
  var pendingTimer = null;

  function shieldState() {
    var s = state.status;
    if (!s) return { label: 'UNKNOWN', detail: 'Firewall daemon unavailable' };
    if (state.pending && state.pending.txid) return { label: 'UNCONFIRMED', detail: 'Rollback armed — confirm or roll back' };
    if (s.backend === 'none') return { label: 'NOT ENFORCED', detail: 'No supported backend available' };
    if (s.enabled) return { label: 'ACTIVE', detail: 'Live policy is enforced' };
    return { label: 'INACTIVE', detail: 'Firewall not enabled' };
  }

  function renderStatus() {
    var st = shieldState();
    setText('big-state', st.label);
    setText('state-detail', st.detail);
    var s = state.status || {};
    setText('backend-line', 'Backend: ' + (s.backend || 'unknown') + ' · kernel ' + (s.kernel_release || '?'));
    var d = s.defaults || {};
    setText('sum-input', d.input === 'deny' ? 'Deny by default' : 'Allow');
    setText('sum-forward', d.forward === 'deny' ? 'Deny by default' : 'Allow');
    setText('sum-output', d.output === 'deny' ? 'Block by default' : 'Allow by default');
    setText('sum-families', (s.ipv4 ? 'IPv4' : 'no IPv4') + ' / ' + (s.ipv6 ? 'IPv6' : 'no IPv6'));
    var perapp = s.per_app || {};
    setText('sum-perapp', perapp.enforceable_now ? 'Verified (UID)' : 'Unsupported on this device');
    setText('rule-input', d.input);
    setText('rule-forward', d.forward);
    setText('rule-output', d.output);
    if ($('outbound-mode')) $('outbound-mode').value = d.output || 'allow';
    renderRollback();
  }

  function renderRollback() {
    var p = state.pending;
    var banner = $('rollback-banner');
    if (!p || !p.txid) { banner.hidden = true; return; }
    banner.hidden = false;
    var deadline = p.deadline || 0;
    function refresh() {
      var left = Math.max(0, Math.round((deadline - (Date.now() / 1000))));
      setText('rollback-text', 'Unconfirmed — rollback in ' + left + 's');
      if (left <= 0) load();
    }
    refresh();
    $('btn-confirm').disabled = false;
    $('btn-rollback').disabled = false;
    $('btn-apply').disabled = true;
    if (pendingTimer) clearInterval(pendingTimer);
    pendingTimer = setInterval(refresh, 1000);
  }

  function renderCapabilities() {
    var c = state.capabilities || {};
    var kern = c.kernel || {};
    setText('backend-diag', JSON.stringify({
      backend: c.backend, supported: c.supported, ipv4: c.ipv4, ipv6: c.ipv6,
      per_app: c.per_app, per_app_mechanism: c.per_app_mechanism,
      kernel: kern, active_managers: c.active_managers
    }, null, 2));
    var banner = $('perapp-banner');
    if (c.per_app === 'unsupported' || !kern) {
      banner.textContent = 'Per-app enforcement: unsupported on this kernel/device (shared process UID). Global direction policy and inbound service rules still apply.';
    } else {
      banner.textContent = 'Per-app enforcement: ' + (c.per_app || 'checking…');
    }
  }

  function appRule(appId) {
    var rules = (state.rules && state.rules.apps) || {};
    var r = rules[appId] || {};
    return r.outbound || 'inherit';
  }

  function renderApps() {
    var apps = (state.apps && state.apps.apps) || [];
    var perApp = !!(state.apps && state.apps.per_app_supported);
    var list = $('app-list');
    var q = ($('app-search') && $('app-search').value || '').toLowerCase();
    list.innerHTML = '';
    var shown = 0;
    apps.forEach(function (a) {
      if (q && (a.app_id + ' ' + (a.name || '')).toLowerCase().indexOf(q) === -1) return;
      shown++;
      var li = document.createElement('li');
      li.className = 'matrix-row';

      var name = document.createElement('div');
      name.className = 'appname';
      var b = document.createElement('b'); b.textContent = a.name || a.app_id;
      var sp = document.createElement('span'); sp.textContent = a.app_id + ' · ' + (a.type || 'unknown');
      name.appendChild(b); name.appendChild(sp);
      li.appendChild(name);

      if (perApp) {
        var sel = document.createElement('select');
        sel.className = 'mini-select';
        [['inherit', 'Inherit'], ['allow', 'Allow'], ['deny', 'Block']].forEach(function (p) {
          var o = document.createElement('option'); o.value = p[0]; o.textContent = p[1]; sel.appendChild(o);
        });
        sel.value = appRule(a.app_id);
        sel.addEventListener('change', function () {
          sel.disabled = true;
          rpc('set-app-rule', { app_id: a.app_id, outbound: sel.value }).then(load);
        });
        li.appendChild(sel);
        for (var i = 0; i < 5; i++) {
          var cell = document.createElement('span');
          cell.className = 'cell'; cell.textContent = '—';
          li.appendChild(cell);
        }
      } else {
        var badge = document.createElement('span');
        badge.className = 'cell unsupported'; badge.textContent = 'unsupported';
        li.appendChild(badge);
        for (var j = 0; j < 5; j++) {
          var c2 = document.createElement('span');
          c2.className = 'cell'; c2.textContent = '—';
          li.appendChild(c2);
        }
      }
      list.appendChild(li);
    });
    if (!shown) { var empty = document.createElement('li'); empty.textContent = 'No apps match.'; list.appendChild(empty); }
  }

  function renderServices() {
    var svc = state.services || {};
    var rules = (state.rules && state.rules.services) || {};
    var list = $('service-list');
    list.innerHTML = '';

    function row(id, label, port, cidrs, enabled) {
      var li = document.createElement('li');
      var info = document.createElement('div');
      info.className = 'appname';
      var b = document.createElement('b'); b.textContent = label;
      var sp = document.createElement('span'); sp.textContent = 'port ' + port + ' — ' + (cidrs || []).join(', ');
      info.appendChild(b); info.appendChild(sp);
      li.appendChild(info);
      var btn = document.createElement('button');
      btn.className = 'ghost';
      btn.textContent = enabled ? 'Enabled' : 'Disabled';
      btn.addEventListener('click', function () {
        btn.disabled = true;
        rpc('set-service-rule', { service_id: id, source_cidrs: cidrs || [], enabled: !enabled }).then(load);
      });
      li.appendChild(btn);
      list.appendChild(li);
    }

    var sshCidrs = (svc.sshd && svc.sshd.allow_cidrs) || [];
    var sshPort = (svc.sshd && svc.sshd.port) || [22];
    if (Array.isArray(sshPort)) sshPort = sshPort.length ? sshPort : [22];
    if (rules['nuxel-ssh-owner']) {
      var rr = rules['nuxel-ssh-owner'];
      sshCidrs = rr.source_cidrs || sshCidrs; sshPort = rr.port || sshPort;
    }
    row('nuxel-ssh-owner', 'SSH console', Array.isArray(sshPort) ? sshPort[0] : sshPort, sshCidrs,
      !!(rules['nuxel-ssh-owner'] ? rules['nuxel-ssh-owner'].enabled : (svc.ssh_listeners && svc.ssh_listeners.length)));

    if (rules['nuxel-xrdp-owner-lan'] || (svc.xrdp_listeners && svc.xrdp_listeners.length)) {
      var xr = rules['nuxel-xrdp-owner-lan'] || {};
      row('nuxel-xrdp-owner-lan', 'XRDP', xr.port || 3389, xr.source_cidrs || ['127.0.0.1/32'], !!(xr.enabled));
    }
    if (rules['nuxel-vnc-owner-lan'] || (svc.vnc_listeners && svc.vnc_listeners.length)) {
      var vr = rules['nuxel-vnc-owner-lan'] || {};
      row('nuxel-vnc-owner-lan', 'VNC / wayvnc', vr.port || 5900, vr.source_cidrs || ['127.0.0.1/32'], !!(vr.enabled));
    }

    if (svc.listeners) {
      var known = { 22: 1, 3389: 1, 5900: 1 };
      svc.listeners.forEach(function (l) {
        if (!known[l.port]) row('listener-' + l.port, l.process || l.protocol, l.port, [l.address], true);
      });
    }
    if (!list.children.length) { var e = document.createElement('li'); e.textContent = 'No active listeners besides SSH.'; list.appendChild(e); }
  }

  function load() {
    var jobs = [
      rpc('status').then(function (r) { state.status = data(r); }),
      rpc('backend-capabilities').then(function (r) { state.capabilities = data(r); }),
      rpc('installed-apps').then(function (r) { state.apps = data(r); }),
      rpc('listeners').then(function (r) { state.services = data(r); }),
      rpc('rules').then(function (r) { state.rules = data(r); }),
      rpc('pending-transaction').then(function (r) { var d = data(r); state.pending = (d && d.txid) ? d : null; })
    ];
    Promise.all(jobs).then(function () {
      renderStatus(); renderCapabilities(); renderApps(); renderServices();
    }).catch(function () {
      state.status = null; renderStatus();
    });
  }

  function action(verb, params) {
    setText('action-result', 'Working…');
    return rpc(verb, params).then(function (r) {
      setText('action-result', JSON.stringify(data(r), null, 2));
      load();
    }).catch(function (e) {
      setText('action-result', 'Error: ' + (e && e.message || e));
    });
  }

  function wire() {
    document.querySelectorAll('#tabs .tab').forEach(function (t) {
      t.addEventListener('click', function () {
        document.querySelectorAll('#tabs .tab').forEach(function (x) { x.classList.remove('active'); });
        document.querySelectorAll('.panel').forEach(function (x) { x.classList.remove('active'); });
        t.classList.add('active');
        var p = $('tab-' + t.dataset.tab); if (p) p.classList.add('active');
      });
    });
    $('btn-dryrun').addEventListener('click', function () { action('dry-run', {}); });
    $('btn-apply').addEventListener('click', function () { action('apply', { rollback_after: 60 }); });
    $('btn-confirm').addEventListener('click', function () { action('confirm', {}); });
    $('btn-rollback').addEventListener('click', function () { action('rollback', {}); });
    $('btn-refresh').addEventListener('click', load);
    if ($('app-search')) $('app-search').addEventListener('input', renderApps);
    if ($('outbound-mode')) $('outbound-mode').addEventListener('change', function () {
      action('set-direction-default', { direction: 'output', action: this.value });
    });
  }

  wire();
  load();
})();
