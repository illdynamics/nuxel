/* PWNAGE-50000: read-only Modem / Camera / Sensors driver status.
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
    if (m) m.addEventListener('click', function () { load('modem', 'mobile-state', 'Mobile network'); });
    if (c) c.addEventListener('click', function () { load('camera', 'camera-state', 'Camera'); });
    if (s) s.addEventListener('click', function () { load('sensors', 'sensors-state', 'Sensor'); });
    var a = $('sensors-read-accel'), g = $('sensors-read-gyro');
    if (a) a.addEventListener('click', function () { sensorRead('accelerometer', 'sensors-state'); });
    if (g) g.addEventListener('click', function () { sensorRead('gyroscope', 'sensors-state'); });
    document.querySelectorAll('.tab').forEach(function (t) {
      t.addEventListener('click', function () {
        if (t.dataset.tab === 'mobile') load('modem', 'mobile-state', 'Mobile network');
        else if (t.dataset.tab === 'camera') load('camera', 'camera-state', 'Camera');
        else if (t.dataset.tab === 'sensors') load('sensors', 'sensors-state', 'Sensor');
      });
    });
  });
})();
