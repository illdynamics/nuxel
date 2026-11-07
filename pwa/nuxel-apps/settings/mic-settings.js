/* Nuxel Settings — real S10+ microphone controls (PWNAGE-84000). */
(function () {
  'use strict';
  var state = null, busy = false;
  function $(id) { return document.getElementById(id); }
  function bridge() {
    if (window.NuxelBridge && typeof window.NuxelBridge.call === 'function') return window.NuxelBridge;
    try { if (window.parent && window.parent.NuxelBridge) return window.parent.NuxelBridge; } catch (e) {}
    return null;
  }
  function call(verb, params) {
    var b = bridge();
    if (!b) return Promise.resolve({ success: false, error: 'Nuxel bridge unavailable' });
    try { return Promise.resolve(b.call('microphone', verb, params || {})); }
    catch (e) { return Promise.resolve({ success: false, error: String(e && e.message || e) }); }
  }
  function text(id, value) { var e = $(id); if (e) e.textContent = value; }
  function render(doc) {
    state = doc;
    if (!doc || doc.success === false) {
      text('mic-state', 'Microphone controls unavailable: ' + ((doc && (doc.detail || doc.error)) || 'unknown error'));
      return;
    }
    var src = doc.source || {};
    var vol = Number(doc.volume_percent);
    if (Number.isFinite(vol)) {
      var slider = $('mic-volume'); if (slider) slider.value = String(Math.max(0, Math.min(100, vol)));
      text('mic-volume-val', Math.round(vol) + '%');
    }
    var mute = $('mic-mute'); if (mute) { mute.textContent = doc.muted ? 'Unmute' : 'Mute'; mute.setAttribute('aria-pressed', doc.muted ? 'true' : 'false'); }
    var supp = doc.noise_suppression || {};
    var suppBox = $('mic-noise-suppression');
    if (suppBox) {
      suppBox.disabled = !supp.available;
      suppBox.checked = !!supp.enabled;
      suppBox.title = supp.available ? 'Enable the verified suppression node' : (supp.reason || 'unavailable');
    }
    text('mic-state',
      'source        : ' + (src.name || 'unavailable') + '\n' +
      'PipeWire id   : ' + (src.id == null ? '—' : src.id) + '\n' +
      'volume        : ' + (Number.isFinite(vol) ? Math.round(vol) + '%' : '—') + (doc.muted ? ' (muted)' : '') + '\n' +
      'gain path     : ' + ((doc.gain && doc.gain.control) || 'unknown') + '\n' +
      'hardware gain : ' + ((doc.gain && doc.gain.hardware_available) ? doc.gain.hardware_controls.map(function (c) { return c.name + '=' + c.value; }).join(', ') : 'not exposed') + '\n' +
      'suppression   : ' + (supp.available ? 'available' : 'unavailable — ' + (supp.reason || 'no verified node')));
    text('mic-detail', (doc.gain && doc.gain.note) || '');
  }
  function refresh() {
    if (busy) return Promise.resolve(null);
    busy = true; text('mic-state', 'Reading capture source…');
    return call('status', {}).then(function (r) { busy = false; render(r); return r; }, function (e) { busy = false; text('mic-state', String(e)); });
  }
  function setVolume(v) {
    text('mic-volume-val', String(v) + '%');
    call('volume', { percent: Number(v) }).then(function (r) {
      if (!r || r.success === false) text('mic-detail', 'Volume change failed: ' + ((r && (r.detail || r.error)) || 'unknown'));
      else refresh();
    });
  }
  function toggleMute() {
    var mute = !(state && state.muted);
    call('mute', { muted: mute }).then(function (r) {
      if (!r || r.success === false) text('mic-detail', 'Mute change failed: ' + ((r && (r.detail || r.error)) || 'unknown'));
      else refresh();
    });
  }
  function testMic() {
    text('mic-detail', 'Capturing a 300 ms private test window…');
    var fill = $('mic-meter-fill'); if (fill) fill.style.width = '0%';
    call('level', { duration_ms: 300 }).then(function (r) {
      if (!r || r.success === false) {
        text('mic-detail', 'Capture failed: ' + ((r && (r.detail || r.error)) || 'unknown'));
        return;
      }
      var m = (r.metrics && r.metrics.left) || {};
      var pct = Math.max(0, Math.min(100, Math.round((m.rms || 0) * 500)));
      if (fill) fill.style.width = pct + '%';
      text('mic-detail', 'Measured RMS ' + (r.rms_dbfs == null ? '—' : r.rms_dbfs + ' dBFS') +
        ' · peak ' + ((m.peak || 0) * 100).toFixed(1) + '% · L/R ' +
        (((r.metrics || {}).left || {}).rms || 0).toFixed(4) + '/' + ((((r.metrics || {}).right || {}).rms) || 0).toFixed(4) +
        (r.clipped ? ' · CLIPPING' : '') + ' · intelligibility needs a spoken-word check.');
    });
  }
  function bind() {
    var slider = $('mic-volume');
    if (slider) slider.addEventListener('change', function () { setVolume(slider.value); });
    var mute = $('mic-mute'); if (mute) mute.addEventListener('click', toggleMute);
    var test = $('mic-test'); if (test) test.addEventListener('click', testMic);
    var supp = $('mic-noise-suppression');
    if (supp) supp.addEventListener('change', function () {
      call('suppression', { enabled: supp.checked }).then(function (r) {
        if (!r || r.success === false) {
          supp.checked = false;
          text('mic-detail', 'Noise suppression unavailable: ' + ((r && (r.detail || r.error)) || 'unknown'));
        } else refresh();
      });
    });
    document.querySelectorAll('.tab').forEach(function (tab) {
      if (tab.dataset.tab === 'sound') tab.addEventListener('click', refresh);
    });
    refresh();
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', bind);
  else bind();
  window.nuxelMicSettings = { refresh: refresh, state: function () { return state; } };
})();
