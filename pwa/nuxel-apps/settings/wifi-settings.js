/* v0.6.3-beta: NetworkManager-only Wi-Fi Settings, no independent supplicant. */
(function () {
  'use strict';
  const $ = id => document.getElementById(id);
  const list = $('wifi-list'), status = $('wifi-status'), result = $('wifi-result'), form = $('wifi-connect-form');
  function client() {
    try { if (window.parent && window.parent.NuxelBridge) return window.parent.NuxelBridge; } catch (_) {}
    return window.NuxelBridge || null;
  }
  function report(message) { result.textContent = message; }
  async function rpc(verb, data, mutate) {
    const api = client();
    if (!api || !api.call) throw new Error('Nuxel bridge unavailable; check nuxel-http-bridge');
    if (mutate) {
      const grant = await api.requestCapability('network:manage', 'Manage Wi-Fi in Nuxel Settings');
      if (grant === false) throw new Error('Network permission denied');
    }
    const response = await api.call(mutate ? 'network' : 'phone', mutate ? verb : 'status', data || {});
    if (response && (response.success === false || response.ok === false)) throw new Error(response.error || 'NetworkManager command failed');
    return response;
  }
  let wifiState = null;
  let selectedAp = null;
  async function refresh() {
    try {
      const response = await rpc(null, {}, false);
      wifiState = response.network || (response.data && response.data.network) || null;
      if (!wifiState || wifiState.available === false) {
        status.textContent = 'Wi-Fi unavailable: check S10+ driver/firmware, rfkill and NetworkManager. ' + ((wifiState && wifiState.error) || '');
      } else {
        status.textContent = 'Radio: ' + (wifiState.wifi_enabled ? 'ON' : 'OFF') + '\nDevice: ' + (wifiState.wifi_available ? 'detected' : 'not detected') + '\nAssociation: ' + (wifiState.wifi_state || 'unknown') + '\nStage: ' + (wifiState.wifi_stage || 'idle') + '\nInternet check: ' + (wifiState.connectivity === 4 ? 'NetworkManager full' : 'not confirmed') + '\nInterface: ' + (wifiState.wifi_devices || []).map(x => x.interface + (x.path ? '@' + x.path : '')).join(', ');
      }
    } catch (e) { status.textContent = 'Network status unavailable: ' + e.message; }
  }
  async function mutate(verb, data) {
    report('Working…');
    try {
      const response = await rpc(verb, data, true);
      if (response.stage) {
        const labels = { associating: 'Associating / DHCP…', activated: 'Activated; waiting for address…',
          ip: 'IP address obtained; waiting for route/DNS…', route: 'Default route present; waiting for DNS…',
          dns: 'DNS configured. Internet is still verified by browsing.', online: 'NetworkManager reports full connectivity.' };
        report((labels[response.stage] || ('Stage: ' + response.stage)) +
          (response.note ? ' ' + response.note : ''));
      } else {
        report(response.state === 'connecting' ? 'Connecting… wait for association and DHCP. Internet is not yet verified.' : 'NetworkManager confirmed request.');
      }
      await refresh();
      return response;
    } catch (e) { report('Error: ' + e.message); return null; }
  }
  $('wifi-refresh').addEventListener('click', refresh);
  $('wifi-scan').addEventListener('click', async () => {
    list.replaceChildren(); report('Scanning…');
    const response = await mutate('wifi-scan', {});
    if (!response) return;
    const seen = new Set();
    for (const ap of (response.networks || [])) {
      // Duplicate SSIDs are real (2.4/5 GHz, mesh nodes). Keep every AP and
      // identify it by the AP's own D-Bus path/BSSID instead of dropping rows.
      const key = (ap.bssid || ap.ap_path) + '|' + ap.ssid + '|' + ap.security + '|' + (ap.frequency || '');
      if (!ap.ssid || seen.has(key)) continue;
      seen.add(key);
      const button = document.createElement('button');
      button.type = 'button'; button.className = 'wifi-network';
      const band = ap.frequency ? (ap.frequency < 3000 ? '2.4 GHz' : '5 GHz') : '';
      button.textContent = ap.ssid + ' · ' + ap.strength + '% · ' + ap.security + (band ? ' · ' + band : '');
      button.addEventListener('click', () => {
        if (!['wpa2','wpa3','open'].includes(ap.security)) { report('This network security type is not supported by the Settings connector.'); return; }
        selectedAp = ap;
        $('wifi-ssid').value = ap.ssid; $('wifi-security').value = ap.security;
        $('wifi-target-label').textContent = ap.ssid + (band ? ' (' + band + ')' : '');
        $('wifi-password').value = '';
        $('wifi-password').required = ap.security !== 'open';
        $('wifi-password').closest('label').hidden = ap.security === 'open';
        form.hidden = false;
        if (ap.security !== 'open') { try { $('wifi-password').focus({ preventScroll: false }); } catch (e) { $('wifi-password').focus(); } }
      });
      list.append(button);
    }
    report(seen.size + ' AP(s) reported; select one to connect.');
  });
  $('wifi-power').addEventListener('click', () => mutate('wifi-enabled', {enabled: !(wifiState && wifiState.wifi_enabled)}));
  $('wifi-disconnect').addEventListener('click', () => mutate('wifi-disconnect', {}));
  $('wifi-cancel').addEventListener('click', () => {
    $('wifi-password').value = ''; selectedAp = null; form.hidden = true;
    try { document.activeElement && document.activeElement.blur(); } catch (e) {}
  });
  form.addEventListener('submit', async event => {
    event.preventDefault();
    const pass = $('wifi-password').value, ssid = $('wifi-ssid').value, security = $('wifi-security').value;
    if (security === 'open' && !confirm('Connect to an unencrypted wireless network?')) return;
    const selected = selectedAp || {};
    const ok = await mutate('wifi-connect', {
      ssid, password: pass, security,
      ap_path: selected.ap_path || '',
      bssid: selected.bssid || '',
      device: selected.device || '',
      ssid_hex: selected.ssid_hex || ''
    });
    $('wifi-password').value = '';
    // Release text-input focus once the activation request is in flight. The
    // compositor (Stevia) hides its keyboard; no repeated focus loop follows.
    try { document.activeElement && document.activeElement.blur(); } catch (e) {}
    if (ok && ok.stage !== 'associating') form.hidden = true;
  });
  document.querySelectorAll('[data-tab=network]').forEach(tab => tab.addEventListener('click', refresh));
})();
