/* Nuxel Quick Settings — Firewall tile (briq-05b).
 * Safe enable/disable through the authoritative firewall service.  Long press
 * opens the full Firewall app.  The tile reflects live readback, not a saved flag. */
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
    catch (e) { return Promise.resolve({ success: false, error: String(e), offline: true }); }
  }

  function openApp() {
    var b = bridge();
    if (b) { b.call('apps', 'launch', { app_id: 'org.nuxel.Firewall', target: 'org.nuxel.Firewall', source: 'quicksettings' }); }
  }

  function render() {
    var tile = document.getElementById('qs-firewall');
    var label = tile && tile.querySelector('.qs-label');
    rpc('status', {}).then(function (r) {
      var d = (r && r.data) || null;
      if (!d) {
        tile.setAttribute('data-enabled', 'unknown');
        if (label) label.innerHTML = 'Firewall<br>unknown';
        return;
      }
      if (d.backend === 'none') {
        tile.setAttribute('data-enabled', 'false');
        if (label) label.innerHTML = 'Firewall<br>no backend';
      } else if (d.enabled) {
        tile.setAttribute('data-enabled', 'true');
        if (label) label.innerHTML = 'Firewall<br>active';
      } else {
        tile.setAttribute('data-enabled', 'false');
        if (label) label.innerHTML = 'Firewall<br>off';
      }
    }).catch(function () {
      tile.setAttribute('data-enabled', 'unknown');
      if (label) label.innerHTML = 'Firewall<br>unknown';
    });
  }

  function toggle() {
    var tile = document.getElementById('qs-firewall');
    rpc('status', {}).then(function (r) {
      var d = (r && r.data) || null;
      if (!d || d.backend === 'none') { openApp(); return; }
      if (d.enabled) {
        rpc('disable', {}).then(render);
      } else {
        rpc('enable', {}).then(render);
      }
    });
  }

  document.addEventListener('DOMContentLoaded', function () {
    var tile = document.getElementById('qs-firewall');
    if (!tile) return;
    var pressTimer = null;
    tile.addEventListener('click', function () {
      if (pressTimer) { clearTimeout(pressTimer); pressTimer = null; }
      toggle();
    });
    tile.addEventListener('touchstart', function () { pressTimer = setTimeout(openApp, 600); });
    tile.addEventListener('touchend', function () { if (pressTimer) { clearTimeout(pressTimer); pressTimer = null; } });
    render();
    setInterval(render, 15000);
  });
})();
