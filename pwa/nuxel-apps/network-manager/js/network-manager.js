// Nuxel Network Manager — owner wrapper around the working Settings Wi-Fi
// connector, with private DNS, VPN and ZeroTier controls.
//
// The Wi-Fi panel is rendered by the SAME pwa/nuxel-apps/settings/wifi-settings.js
// module, so there is exactly one NetworkManager connector.  Everything else
// calls fixed bridge verbs; no shell, path or address is accepted from this UI.
(function () {
  'use strict';
  var el = function (id) { return document.getElementById(id); };
  function esc(s) {
    return String(s === null || s === undefined ? '' : s)
      .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }
  function setState(id, text) { var n = el(id); if (n) n.textContent = text; }
  function rowsToText(obj) {
    return Object.keys(obj || {}).map(function (k) {
      var v = obj[k];
      if (Array.isArray(v)) v = v.length ? v.join(', ') : 'none';
      else if (v === null || v === undefined || v === '') v = 'not reported';
      return k.replace(/_/g, ' ') + ': ' + v;
    }).join('\n');
  }

  var bridgePromise = null;
  function bridge() {
    if (window.NuxelBridge && typeof window.NuxelBridge.call === 'function') return Promise.resolve(window.NuxelBridge);
    try {
      if (window.parent && window.parent !== window && window.parent.NuxelBridge &&
          typeof window.parent.NuxelBridge.call === 'function') {
        return Promise.resolve(window.parent.NuxelBridge);
      }
    } catch (e) { /* cross-origin */ }
    if (bridgePromise) return bridgePromise;
    bridgePromise = new Promise(function (resolve, reject) {
      var tries = 0;
      var t = setInterval(function () {
        var b = window.NuxelBridge;
        if (b && typeof b.call === 'function') {
          clearInterval(t); resolve(b); return;
        }
        if (++tries > 80) { clearInterval(t); reject(new Error('Nuxel bridge unavailable')); }
      }, 100);
    });
    return bridgePromise;
  }

  async function rpc(namespace, verb, params, mutate) {
    var b = await bridge();
    if (mutate) {
      try {
        var grant = await b.requestCapability('network:manage', 'Manage network, DNS, VPN and ZeroTier');
        if (grant === false) throw new Error('network:manage was denied');
      } catch (e) {
        if (e && e.message === 'network:manage was denied') throw e;
        // A bridge without requestCapability still must not be blocked here;
        // the bridge enforces the capability server-side.
      }
    }
    var response = await b.call(namespace, verb, params || {});
    if (response && response.result && response.result.success !== undefined) response = response.result;
    if (response && (response.success === false || response.ok === false)) {
      var error = new Error(response.error || response.detail || 'network request failed');
      error.response = response;
      throw error;
    }
    return response || {};
  }

  // ---- tabs ---------------------------------------------------------------
  var tabs = document.querySelectorAll('.tab');
  Array.prototype.forEach.call(tabs, function (tab) {
    tab.addEventListener('click', function () {
      Array.prototype.forEach.call(tabs, function (t) { t.classList.remove('active'); });
      Array.prototype.forEach.call(document.querySelectorAll('.panel'), function (p) { p.classList.remove('active'); });
      tab.classList.add('active');
      var panel = el('tab-' + tab.dataset.tab);
      if (panel) panel.classList.add('active');
      if (tab.dataset.tab === 'wifi') refreshWifi();
      if (tab.dataset.tab === 'dns') refreshDns();
      if (tab.dataset.tab === 'vpn') refreshVpn();
      if (tab.dataset.tab === 'zerotier') refreshZt();
    });
  });

  async function refreshWifi() {
    if (window.NuxelWifiSettings && typeof window.NuxelWifiSettings.refresh === 'function') {
      await window.NuxelWifiSettings.refresh();
    } else {
      setState('wifi-status', 'The shared Settings Wi-Fi module did not load.');
    }
  }

  // ---- private DNS --------------------------------------------------------
  async function refreshDns() {
    setState('dns-status', 'Reading DNS configuration…');
    try {
      var d = await rpc('network', 'dns-status', {});
      var conn = d.connection || {};
      setState('dns-status',
        'Active Wi-Fi profile: ' + (conn.name || 'not connected') + '\n' +
        'IPv4 DNS: ' + ((d.ipv4_dns || []).join(', ') || 'automatic') + '\n' +
        'IPv6 DNS: ' + ((d.ipv6_dns || []).join(', ') || 'automatic') + '\n' +
        'ignore auto DNS: ipv4=' + !!d.ignore_auto_ipv4 + ', ipv6=' + !!d.ignore_auto_ipv6 + '\n' +
        'DoT available (systemd-resolved): ' + !!d.dot_available + '\n' +
        'DoT active: ' + !!d.dot_active);
      if (d.provider && el('dns-provider') && ['cloudflare','quad9','custom','dhcp'].indexOf(d.provider) >= 0) {
        el('dns-provider').value = d.provider;
      }
      if (d.saved_ipv4 || d.saved_ipv6) {
        el('dns-custom').value = [].concat(d.saved_ipv4 || [], d.saved_ipv6 || []).join(', ');
      } else if ((d.ipv4_dns || []).length || (d.ipv6_dns || []).length) {
        el('dns-custom').value = (d.ipv4_dns || []).concat(d.ipv6_dns || []).join(', ');
      }
    } catch (e) {
      setState('dns-status', 'DNS status unavailable: ' + e.message);
    }
  }

  async function saveDns(provider, custom) {
    setState('dns-result', 'Applying private DNS…');
    try {
      var d = await rpc('network', 'dns-set', { provider: provider, servers: custom }, true);
      setState('dns-result', 'Saved. Live apply: ' + !!d.applied + ', DoT active: ' + !!d.dot_active +
        (d.applied ? '' : '\nThe profile is saved; reconnect Wi-Fi to apply it to the live link.'));
      await refreshDns();
    } catch (e) {
      setState('dns-result', 'DNS error: ' + e.message);
    }
  }

  el('dns-save').addEventListener('click', function () {
    saveDns(el('dns-provider').value, el('dns-custom').value);
  });
  el('dns-reset').addEventListener('click', function () {
    saveDns('dhcp', '');
  });

  // ---- VPN ----------------------------------------------------------------
  async function refreshVpn() {
    setState('vpn-status', 'Reading VPN connections…');
    try {
      var d = await rpc('network', 'vpn-status', {});
      var p = d.plugins || {};
      setState('vpn-status', 'OpenVPN plugin: ' + !!p.nm_openvpn + ' · openvpn binary: ' +
        !!p.openvpn + ' · WireGuard tools: ' + !!p.wireguard);
      var list = el('vpn-list');
      list.innerHTML = '';
      (d.connections || []).forEach(function (c) {
        var li = document.createElement('li');
        li.innerHTML = '<b>' + esc(c.name || c.uuid) + '</b><br>' +
          '<span class="hint">' + esc(c.type) + ' · ' + esc(c.uuid) + ' · ' +
          (c.active ? '<span class="ok">connected</span>' : 'disconnected') + '</span>' +
          '<div class="actions">' +
          '<button data-vpn-up="' + esc(c.uuid) + '">Connect</button>' +
          '<button data-vpn-down="' + esc(c.uuid) + '">Disconnect</button>' +
          '<button data-vpn-delete="' + esc(c.uuid) + '">Delete</button></div>';
        list.appendChild(li);
      });
      if (!(d.connections || []).length) {
        list.innerHTML = '<li class="hint">No VPN profiles imported yet.</li>';
      }
      Array.prototype.forEach.call(list.querySelectorAll('[data-vpn-up]'), function (b) {
        b.addEventListener('click', function () { vpnAction('vpn-up', b.dataset.vpnUp); });
      });
      Array.prototype.forEach.call(list.querySelectorAll('[data-vpn-down]'), function (b) {
        b.addEventListener('click', function () { vpnAction('vpn-down', b.dataset.vpnDown); });
      });
      Array.prototype.forEach.call(list.querySelectorAll('[data-vpn-delete]'), function (b) {
        b.addEventListener('click', function () { vpnAction('vpn-delete', b.dataset.vpnDelete); });
      });
    } catch (e) {
      setState('vpn-status', 'VPN status unavailable: ' + e.message);
    }
  }

  async function vpnAction(verb, uuid) {
    setState('vpn-result', 'Working…');
    try {
      await rpc('network', verb, { uuid: uuid }, true);
      setState('vpn-result', 'NetworkManager completed ' + verb + '.');
      await refreshVpn();
    } catch (e) {
      setState('vpn-result', 'VPN error: ' + e.message);
    }
  }

  el('vpn-import').addEventListener('click', async function () {
    var kind = el('vpn-kind').value;
    var config = el('vpn-config').value;
    var name = el('vpn-name').value;
    setState('vpn-result', 'Importing VPN profile…');
    try {
      var d = await rpc('network', 'vpn-import', { kind: kind, config: config, name: name }, true);
      el('vpn-config').value = '';
      setState('vpn-result', 'Imported ' + ((d.imported && d.imported.name) || 'profile') + '.');
      await refreshVpn();
    } catch (e) {
      setState('vpn-result', 'Import error: ' + e.message);
    }
  });

  // ---- ZeroTier -----------------------------------------------------------
  async function refreshZt() {
    setState('zt-status', 'Reading ZeroTier status…');
    try {
      var d = await rpc('network', 'zerotier-status', {});
      setState('zt-status',
        'Installed: ' + !!d.installed + '\n' +
        'Service active: ' + !!d.service_active + '\n' +
        'Node address: ' + (d.address || 'not assigned') + '\n' +
        'Online: ' + (d.online === null || d.online === undefined ? 'unknown' : !!d.online) + '\n' +
        'Version: ' + (d.version || 'not reported') +
        (d.error ? '\nError: ' + d.error : ''));
      var box = el('zt-networks');
      box.innerHTML = '';
      (d.networks || []).forEach(function (n) {
        var li = document.createElement('div');
        li.className = 'card';
        li.innerHTML = '<b>' + esc(n.name || n.nwid || n.id || 'network') + '</b>' +
          '<pre class="state">' + esc(rowsToText(n)) + '</pre>';
        box.appendChild(li);
      });
      if (!(d.networks || []).length) {
        box.innerHTML = '<p class="hint">No joined networks reported yet. If a join was just issued, approve this node in ZeroTier Central and refresh.</p>';
      }
    } catch (e) {
      setState('zt-status', 'ZeroTier status unavailable: ' + e.message);
    }
  }

  async function ztAction(verb, params) {
    setState('zt-result', 'Working…');
    try {
      var d = await rpc('network', verb, params, true);
      setState('zt-result', 'ZeroTier completed ' + verb + '.');
      if (d && d.zerotier) {
        // Refresh below is authoritative; this only gives immediate feedback.
      }
      await refreshZt();
    } catch (e) {
      setState('zt-result', 'ZeroTier error: ' + e.message);
    }
  }

  el('zt-join').addEventListener('click', function () {
    ztAction('zerotier-join', { network_id: el('zt-network').value.trim() });
  });
  el('zt-leave').addEventListener('click', function () {
    ztAction('zerotier-leave', { network_id: el('zt-network').value.trim() });
  });
  el('zt-refresh').addEventListener('click', refreshZt);
  el('zt-toggle').addEventListener('click', async function () {
    try {
      var d = await rpc('network', 'zerotier-status', {});
      await ztAction('zerotier-enabled', { enabled: !d.service_active });
    } catch (e) {
      setState('zt-result', 'ZeroTier error: ' + e.message);
    }
  });

  el('close').addEventListener('click', function () {
    try {
      if (window.parent && window.parent.NuxelLauncherClose) { window.parent.NuxelLauncherClose(); return; }
    } catch (e) { /* cross-origin */ }
    var f = window.frameElement;
    if (f && f.parentNode) f.parentNode.removeChild(f);
  });

  // Initial load: Wi-Fi first, then warm the other panels.
  (async function () {
    try { await bridge(); } catch (e) { setState('headline', e.message); }
    await refreshWifi();
    refreshDns();
    refreshVpn();
    refreshZt();
  })();
})();
