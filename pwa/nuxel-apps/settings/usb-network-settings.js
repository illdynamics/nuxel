/* Nuxel Settings — USB networking, USB tethering, Wi-Fi hotspot (PWNAGE-USBNET).
 *
 * One owner surface for the dedicated providers. It reads the SAME state the
 * Quick Settings tile reads; nothing here writes a file or runs a shell
 * command. Every control reports the provider's real result:
 *
 *   usb-net      gadget composition: off / usbnet / tether (NCM + ACM)
 *   usb-tether   Internet sharing over USB (scoped forwarding + NAT)
 *   network      Wi-Fi hotspot (only when the driver advertises AP mode)
 *
 * "USB tether composition" is NOT Internet sharing.  The tether switch stays
 * OFF (and the host is described as having no Internet) until usb-tether
 * reports internet_verified after an explicit start.
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

  function rpc(ns, verb, params) {
    var b = bridge();
    if (!b) return Promise.resolve({ success: false, error: 'bridge unavailable', offline: true });
    try { return Promise.resolve(b.call(ns, verb, params || {})); }
    catch (e) { return Promise.resolve({ success: false, error: String(e && e.message || e), offline: true }); }
  }

  function $ (id) { return document.getElementById(id); }
  function setText(id, v) { var el = $(id); if (el) el.textContent = v; }
  function busy(on) {
    document.querySelectorAll('#tab-usbnet button').forEach(function (b) {
      if (b.id !== 'usbnet-refresh') b.disabled = !!on;
    });
  }

  var lastUsb = null, lastTether = null, lastHotspot = null;

  function renderUsb(r) {
    lastUsb = r;
    if (r && r.offline) { setText('usbnet-state', 'HOST UNAVAILABLE — no state read'); return; }
    if (!r || r.success === false) {
      setText('usbnet-state', 'provider error: ' + ((r && (r.error || r.detail)) || 'unknown'));
      return;
    }
    var mode = r.active ? (r.mode || r.selected || 'off') : 'off';
    var lines = [
      'USB link: ' + (r.active ? mode.toUpperCase() : 'OFF') +
        (r.interface ? '  (' + r.interface + ', ' + (r.function || 'ecm') + ')' : ''),
      'Phone: ' + (r.device_ip || '10.100.10.1') + '   Host: ' + (r.host_ip || '10.100.10.2') +
        '   subnet: ' + (r.subnet || '10.100.10.0/24'),
      'ACM recovery console: ' + (r.acm_preserved ? 'preserved' : 'NOT CONFIRMED') + ' in every mode',
      'SSH: ' + (r.active ? 'USB link up; a host-side key-authenticated probe is what marks it READY' : 'n/a')
    ];
    if (r.last_error) lines.push('last error: ' + r.last_error);
    setText('usbnet-state', lines.join('\n'));
    var t = $('usbnet-tether');
    // Only a live USB link can carry a tether composition; SSH is not required
    // for tethering, but an absent link is.
    if (t) t.disabled = !r.active;
  }

  function renderTether(r) {
    lastTether = r;
    if (r && r.offline) { setText('usbtether-state', 'HOST UNAVAILABLE — no state read'); return; }
    if (!r || r.success === false) {
      setText('usbtether-state', 'provider error: ' + ((r && (r.error || r.detail)) || 'unknown'));
      return;
    }
    var state = String(r.state || (r.enabled ? 'on' : 'off')).toUpperCase();
    var lines = ['Internet sharing: ' + state];
    if (r.upstream) lines.push('upstream: ' + r.upstream + (r.vpn_armed ? '  (VPN kill switch armed)' : ''));
    if (r.usb_interface) lines.push('USB interface: ' + r.usb_interface);
    if (r.source_address) lines.push('host: ' + (r.host_address || '10.100.10.2/24') +
      '  gateway: ' + (r.gateway || '10.100.10.1') + '  (DHCP: ' + (r.dhcp || 'static-host-config') + ')');
    lines.push('Host Internet verified: ' + (r.internet_verified ? 'yes' : 'no') +
      ' (a configured share alone is not proof)');
    if (r.vpn_conflict) lines.push('VPN: ' + r.vpn_conflict);
    if (r.last_error) lines.push('last error: ' + r.last_error);
    var ups = (r.upstreams || []).filter(function (u) { return u.usable; })
      .map(function (u) { return u.interface + ' (' + u.kind + ')'; });
    lines.push('usable upstreams: ' + (ups.length ? ups.join(', ') : 'none'));
    setText('usbtether-state', lines.join('\n'));
    var sel = $('usbtether-upstream');
    if (sel) {
      var want = sel.value;
      sel.innerHTML = '<option value="">(first usable)</option>';
      (r.upstreams || []).forEach(function (u) {
        var o = document.createElement('option');
        o.value = u.interface;
        o.textContent = u.interface + ' (' + u.kind + ')' + (u.usable ? '' : ' — unavailable');
        o.disabled = !u.usable;
        sel.appendChild(o);
      });
      sel.value = want;
    }
    var start = $('usbtether-start');
    if (start) start.disabled = !ups.length || !!r.enabled;
    var stop = $('usbtether-stop');
    if (stop) stop.disabled = !r.enabled;
  }

  function renderHotspot(r) {
    lastHotspot = r;
    if (r && r.offline) { setText('hotspot-state', 'HOST UNAVAILABLE — no state read'); return; }
    if (!r || r.success === false) {
      setText('hotspot-state', 'provider error: ' + ((r && (r.error || r.detail)) || 'unknown'));
      return;
    }
    if (!r.supported) {
      setText('hotspot-state', 'Wi-Fi hotspot: UNSUPPORTED' + (r.reason ? ' — ' + r.reason : ''));
      ['hotspot-start', 'hotspot-stop'].forEach(function (id) { var b = $(id); if (b) b.disabled = true; });
      return;
    }
    setText('hotspot-state', 'Wi-Fi hotspot: ' + String(r.state || 'off').toUpperCase() +
      (r.ssid ? '  SSID: ' + r.ssid : ''));
    var start = $('hotspot-start'); if (start) start.disabled = !!r.enabled;
    var stop = $('hotspot-stop'); if (stop) stop.disabled = !r.enabled;
  }

  function refresh() {
    setText('usbnet-state', 'Reading USB networking state…');
    setText('usbtether-state', 'Reading tethering state…');
    setText('hotspot-state', 'Reading Wi-Fi capabilities…');
    return Promise.all([
      rpc('usb-net', 'status').then(renderUsb),
      rpc('usb-tether', 'status').then(renderTether),
      rpc('network', 'hotspot-status').then(renderHotspot)
    ]);
  }

  function apply(mode) {
    busy(true);
    setText('usbnet-state', 'Applying ' + mode + '…');
    rpc('usb-net', 'set-mode', { mode: mode, function: 'ecm' }).then(function (r) {
      if (!r || r.success === false) {
        setText('usbnet-state', mode + ' FAILED: ' + ((r && (r.error || r.last_error || r.detail)) || 'helper did not confirm'));
      }
      return refresh();
    }).finally(function () { busy(false); });
  }

  function tether(action) {
    busy(true);
    var up = $('usbtether-upstream');
    var upsel = (up && up.value) || null;
    setText('usbtether-state', 'Applying ' + action + '…');
    var call;
    if (action === 'enable') {
      // One explicit owner action: USB network composition + Internet share.
      call = rpc('usb-net', 'enable-for-host', { upstream: upsel });
    } else {
      var params = action === 'start' ? { upstream: upsel } : {};
      call = rpc('usb-tether', action, params);
    }
    call.then(function (r) {
      if (!r || r.success === false) {
        setText('usbtether-state', action + ' FAILED: ' + ((r && (r.error || r.detail)) || 'unknown'));
      }
      return refresh();
    }).finally(function () { busy(false); });
  }

  function hotspot(action) {
    busy(true);
    var ssid = $('hotspot-ssid'), pass = $('hotspot-password');
    var params = action === 'start' ? { ssid: (ssid && ssid.value) || '', password: (pass && pass.value) || '' } : {};
    setText('hotspot-state', 'Applying ' + action + '…');
    rpc('network', action === 'start' ? 'hotspot-start' : 'hotspot-stop', params).then(function (r) {
      if (!r || r.success === false) {
        setText('hotspot-state', action + ' FAILED: ' + ((r && (r.error || r.detail)) || 'unknown'));
      }
      if (pass) pass.value = '';
      return refresh();
    }).finally(function () { busy(false); });
  }

  function wire() {
    var on = $('usbnet-refresh'); if (on) on.addEventListener('click', refresh);
    var u = $('usbnet-usbnet'); if (u) u.addEventListener('click', function () { apply('usbnet'); });
    var t = $('usbnet-tether'); if (t) t.addEventListener('click', function () { apply('tether'); });
    var o = $('usbnet-off'); if (o) o.addEventListener('click', function () { apply('off'); });
    var te = $('usbtether-enable'); if (te) te.addEventListener('click', function () { tether('enable'); });
    var ts = $('usbtether-start'); if (ts) ts.addEventListener('click', function () { tether('start'); });
    var tx = $('usbtether-stop'); if (tx) tx.addEventListener('click', function () { tether('stop'); });
    var tv = $('usbtether-verify'); if (tv) tv.addEventListener('click', function () { tether('verify'); });
    var hs = $('hotspot-start'); if (hs) hs.addEventListener('click', function () { hotspot('start'); });
    var hx = $('hotspot-stop'); if (hx) hx.addEventListener('click', function () { hotspot('stop'); });
    refresh();
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', wire);
  else wire();
})();
