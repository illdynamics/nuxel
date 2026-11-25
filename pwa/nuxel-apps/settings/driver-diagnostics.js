/* Native mobile-data controls and read-only Camera / Sensors driver status.
 *
 * The page renders the bridge's own diagnostic JSON.  It never invents a
 * sensor value, a carrier, a signal or a captured frame.  A class that the
 * kernel does not expose stays visibly "absent"/"present-unreadable".
 */
(function () {
  'use strict';
  var $ = function (id) { return document.getElementById(id); };
  function bridge() {
    if (window.NuxelBridge && typeof window.NuxelBridge.call === 'function') return window.NuxelBridge;
    try { if (window.parent && window.parent.NuxelBridge) return window.parent.NuxelBridge; } catch (e) {}
    return null;
  }
  function call(ns, verb, params) {
    var b = bridge();
    if (!b) return Promise.reject(new Error('Nuxel bridge unavailable'));
    return b.call(ns, verb, params || {});
  }
  function show(id, text) { var el = $(id); if (el) el.textContent = text; }
  function pretty(obj) {
    try { return JSON.stringify(obj, null, 2); } catch (e) { return String(obj); }
  }
  function load(kind, target, label) {
    show(target, 'Reading ' + label + ' driver status…');
    return call('system', 'diagnostics', { kind: kind }).then(function (doc) {
      if (!doc || doc.success === false) {
        show(target, label + ' diagnostic unavailable:\n' + pretty(doc));
        return;
      }
      show(target, pretty(doc));
    }).catch(function (err) {
      show(target, label + ' diagnostic failed: ' + (err && err.message ? err.message : err));
    });
  }
  var mobileBusy = false;
  function mobileStatus() {
    if (mobileBusy) return Promise.resolve();
    return call('phone', 'status', {}).then(function (doc) {
      var m = doc && doc.modem, toggle = $('mobile-enabled');
      if (!m || !m.available) throw new Error('Native radio unavailable');
      if (toggle) {
        toggle.checked = m.mobile_data_enabled === true;
        toggle.disabled = typeof m.mobile_data_enabled !== 'boolean' || ['connecting', 'disconnecting'].indexOf(m.connection_state) >= 0;
      }
      var stats = m.statistics || {};
      function value(v, unit) { return v == null ? 'unavailable' : Math.round(v) + unit; }
      show('mobile-state', [
        'SIM: ' + (m.sim_state || 'unknown'), 'Operator: ' + (m.operator || 'unknown'),
        'Home operator: ' + (m.home_operator || 'unknown'),
        'Roaming: ' + (m.roaming == null ? 'unknown' : m.roaming ? 'yes' : 'no'),
        'Registration: ' + m.registration + ' (raw ' + m.registration_raw + ')', 'Technology: ' + (m.technology || 'unknown'),
        'Signal: ' + (m.signal_valid ? m.signal_quality + '%' : 'unknown'),
        'Data: ' + m.connection_state, 'APN: ' + (m.apn || 'unknown'),
        'Session: ' + m.phase, 'Failure: ' + m.failure_phase + ' / ' + m.failure_result,
        'IPv4: ' + (m.ipv4 || 'none'), 'IPv6: ' + (m.ipv6 || 'none'),
        'Interface: ' + (m.interface || 'unknown'), 'Network result: ' + m.link_result,
        'DNS: ' + ((stats.dns || []).join(', ') || 'unavailable'),
        'Connected: ' + value(stats.duration_seconds, ' seconds'),
        'Received: ' + value(stats.rx_bytes, ' bytes') + ' / ' + value(stats.rx_bytes_per_second, ' B/s'),
        'Sent: ' + value(stats.tx_bytes, ' bytes') + ' / ' + value(stats.tx_bytes_per_second, ' B/s'),
        'Disconnect result: ' + m.disconnect_result, 'Error: ' + (m.error || 'none')
      ].join('\n'));
    }).catch(function (err) {
      if ($('mobile-enabled')) $('mobile-enabled').disabled = true;
      show('mobile-state', err.message);
    });
  }
  function sensorRead(cls, target) {
    show(target, 'Reading ' + cls + ' (raw kernel values only)…');
    call('system', 'sensor-read', { 'class': cls }).then(function (doc) {
      show(target, pretty(doc));
    }).catch(function (err) {
      show(target, cls + ' read failed: ' + (err && err.message ? err.message : err));
    });
  }
  document.addEventListener('DOMContentLoaded', function () {
    var m = $('mobile-refresh'), c = $('camera-refresh'), s = $('sensors-refresh');
    if (m) m.addEventListener('click', mobileStatus);
    var toggle = $('mobile-enabled');
    if (toggle) toggle.addEventListener('change', function () {
      if (mobileBusy) return;
      mobileBusy = true; toggle.disabled = true;
      call('network', 'mobile-data-enabled', {enabled: toggle.checked}).then(function (result) {
        if (!result || result.success === false) throw new Error((result && result.error) || 'Operation refused');
        mobileBusy = false; return mobileStatus();
      }).catch(function (err) {
        mobileBusy = false; show('mobile-state', err.message); toggle.disabled = false;
      });
    });
    setInterval(function () {
      var panel = $('tab-mobile');
      if (panel && panel.classList.contains('active')) mobileStatus();
    }, 3000);
    if (c) c.addEventListener('click', function () { load('camera', 'camera-state', 'Camera'); });
    if (s) s.addEventListener('click', function () { load('sensors', 'sensors-state', 'Sensor'); });
    var a = $('sensors-read-accel'), g = $('sensors-read-gyro');
    if (a) a.addEventListener('click', function () { sensorRead('accelerometer', 'sensors-state'); });
    if (g) g.addEventListener('click', function () { sensorRead('gyroscope', 'sensors-state'); });
    document.querySelectorAll('.tab').forEach(function (t) {
      t.addEventListener('click', function () {
        if (t.dataset.tab === 'mobile') mobileStatus();
        else if (t.dataset.tab === 'camera') load('camera', 'camera-state', 'Camera');
        else if (t.dataset.tab === 'sensors') load('sensors', 'sensors-state', 'Sensor');
      });
    });
  });
})();
