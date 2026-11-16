/* Settings -> Notifications -> Edge lighting (PWNAGE-103000).
 * A thin surface over the SAME provider/document as Edge FX and Quick Settings;
 * it never keeps its own copy of the settings. */
(function () {
  'use strict';
  var stateEl = document.getElementById('edge-lighting-state');
  if (!stateEl) return;
  var resultEl = document.getElementById('edge-lighting-result');
  var capEl = document.getElementById('edge-lighting-capability');
  var LABELS = { basic: 'Basic', wave: 'Wave', bubble: 'Bubble', multicolor: 'Multicolor',
                 heart: 'Heart', fireworks: 'Fireworks', eclipse: 'Eclipse', echo: 'Echo' };

  function bridge() { return window.NuxelBridge; }
  function call(ns, verb, params) {
    var b = bridge();
    if (b && b.call) return Promise.resolve(b.call(ns, verb, params || {}));
    var token = '';
    var base = window.NUXEL_API_URL || 'http://127.0.0.1:8080/api/v1';
    function rpc() {
      return fetch(base + '/rpc', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-Nuxel-Bridge-Version': '1',
                   Authorization: 'Bearer ' + token },
        body: JSON.stringify({ app_id: 'nuxel-settings', namespace: ns, verb: verb, params: params || {} })
      }).then(function (r) { return r.json(); }).then(function (res) {
        return (res && res.result !== undefined) ? res.result : res;
      });
    }
    return fetch(base + '/auth/token', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ app_id: 'nuxel-settings' })
    }).then(function (r) { return r.json(); }).then(function (res) { token = (res && res.token) || ''; return rpc(); });
  }

  function render(status) {
    if (!status || !status.success) {
      stateEl.textContent = 'Edge lighting provider unavailable: ' + ((status && status.error) || 'no response');
      return;
    }
    var c = status.config || {};
    stateEl.textContent = 'Effect: ' + (LABELS[c.effect] || c.effect) +
      ' · ' + (c.enabled ? 'enabled' : 'off') +
      '\nColour: ' + (c.color_mode === 'theme' ? 'Nuxel theme accent' : (c.color || c.color_mode)) +
      ' · width ' + c.width + ' · transparency ' + c.transparency +
      '\nDuration: ' + c.duration_ms + ' ms · screen: while screen is on' +
      '\nDND: ' + (status.dnd && status.dnd.active ? 'active (lights suppressed)' : 'off') +
      ' · last notification effect seq: ' + (status.last_seq || 0);
    var modes = ((status.capability || {}).screen_modes || []).map(function (m) {
      return m.id + '=' + (m.available ? 'available' : 'unavailable');
    }).join(', ');
    capEl.textContent = 'AMOLED display effect, not a physical LED. Screen modes: ' + modes +
      '. Reduced motion uses a short static pulse.';
  }

  function refresh() {
    call('edge-lighting', 'status', {}).then(render, function (e) {
      stateEl.textContent = 'Edge lighting provider unavailable: ' + (e && e.message ? e.message : e);
    });
  }

  var open = document.getElementById('edge-lighting-open');
  if (open) open.addEventListener('click', function () {
    if (window.appRegistry) window.appRegistry.launchApp('nuxel-edge-fx');
    else if (window.parent && window.parent.appRegistry) window.parent.appRegistry.launchApp('nuxel-edge-fx');
  });
  var preview = document.getElementById('edge-lighting-preview');
  if (preview) preview.addEventListener('click', function () {
    call('edge-lighting', 'status', {}).then(function (st) {
      var eff = st && st.config && st.config.effect;
      try {
        var p = window.parent && window.parent.NuxelEdgeLighting;
        if (p && p.preview) p.preview(eff);
      } catch (e) { /* framed */ }
      if (resultEl) resultEl.textContent = 'Preview requested for ' + (LABELS[eff] || eff) + ' (no notification changed).';
    });
  });
  var toggle = document.getElementById('edge-lighting-toggle');
  if (toggle) toggle.addEventListener('click', function () {
    call('edge-lighting', 'status', {}).then(function (st) {
      var want = !(st && st.config && st.config.enabled);
      return call('edge-lighting', 'set', { enabled: want }).then(function (res) {
        if (resultEl) resultEl.textContent = res && res.success
          ? 'Edge lighting ' + (want ? 'on' : 'off') + '.'
          : 'Not changed: ' + ((res && (res.error || res.detail)) || 'provider refused');
        refresh();
      });
    });
  });
  var panel = document.getElementById('edge-panel-open');
  if (panel) panel.addEventListener('click', function () {
    var opened = false;
    try { if (window.parent && window.parent.NuxelEdgeLighting) opened = !!window.parent.NuxelEdgeLighting.togglePanel('left'); } catch (e) { opened = false; }
    if (resultEl) resultEl.textContent = opened ? 'Edge panel opened on Home.' :
      'Close Settings to use the Home Edge panel (or swipe from the side on Home).';
  });

  refresh();
  document.addEventListener('nuxel:edge-lighting-changed', function () { refresh(); });
})();
