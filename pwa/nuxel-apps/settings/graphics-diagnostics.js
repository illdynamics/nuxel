/* PWNAGE-52000 Graphics Acceleration card + layered diagnostics.
 *
 * The Displays tab owns TWO independent requests:
 *   graphics.status  (bounded 3 s)  -> this card
 *   display.status   (bounded 4 s)  -> external connector card (hardware-settings.js)
 * Neither request can block or overwrite the other.  Expensive EGL probes run
 * only from the explicit Graphics Test / probe buttons, never on refresh.
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
    return Promise.resolve(b.call(ns, verb, params || {}));
  }
  function pretty(o) { try { return JSON.stringify(o, null, 2); } catch (e) { return String(o); } }
  function bounded(ns, verb, params, ms) {
    var timer;
    var timeout = new Promise(function (resolve) {
      timer = setTimeout(function () {
        resolve({ success: false, timeout: true, state: 'timeout',
                  error: 'no response within ' + (ms / 1000) + ' s' });
      }, ms);
    });
    return Promise.race([call(ns, verb, params), timeout]).then(function (r) {
      if (timer) clearTimeout(timer);
      return r;
    }, function (e) {
      if (timer) clearTimeout(timer);
      return { success: false, error: String(e && e.message || e) };
    });
  }
  function val(x, fallback) {
    if (x === true) return 'yes';
    if (x === false) return 'no';
    if (x === null || x === undefined || x === '') return fallback || 'not measured';
    return String(x);
  }
  function renderGraphics(st) {
    var out = $('graphics-acceleration-state');
    var detail = $('graphics-acceleration-detail');
    var verdict = $('graphics-acceleration-verdict');
    if (!out) return;
    if (!st || st.success === false) {
      out.textContent = 'Graphics status unavailable' +
        (st && st.timeout ? ' (timed out after 3 s)' : '') +
        (st && st.error ? (': ' + st.error) : '') +
        '\nExternal connector discovery is independent and did not cause this.';
      if (detail) detail.textContent = 'Retry with Refresh graphics status. No GPU state was changed.';
      if (verdict) verdict.textContent = 'VERDICT: UNKNOWN';
      return;
    }
    var g = st.gpu || {}, p = st.phoc || {}, e = st.egl || {}, k = st.webkitgtk || {};
    var d = st.dmabuf || {}, w = st.display_bridge || {}, f = st.fbdev_drm || {};
    var lines = [
      'GPU            : ' + val(g.hardware) + ' / ' + val(g.kernel_driver),
      'GPU NODE       : ' + val(g.device_node) + '  present=' + val(g.device_present),
      'KBASE CONTEXT  : ' + val(g.context_owner) + '  compositor-opened=' + val(g.context_opened_by_compositor),
      'PHOC           : ' + val(p.renderer) + '  WLR_RENDERER=' + val(p.wlr_renderer) +
                          '  mali_fds=' + val(p.mali_fds) + '  udmabuf_fds=' + val(p.udmabuf_fds),
      'PHOC ACCEL     : ' + val(p.accelerated) + '  fallback=' + val(p.fallback_marker),
      'EGL            : ' + val(e.library) + '  init=' + val(e.init),
      'EGL VENDOR     : ' + val(e.vendor) + '  version=' + val(e.version),
      'GLES           : ' + val(e.gles_version) + '  renderer=' + val(e.gles_renderer),
      'GTK GL         : ' + val((st.gtk_gl || {}).status) + '  ' + val((st.gtk_gl || {}).detail),
      'WEBKITGTK      : ' + val(k.status) + '  process=' + val(k.process_running),
      'DMA-BUF        : udmabuf=' + val(d.udmabuf_device) + '  linux-dmabuf-global=' + val(d.linux_dmabuf_global) +
                          '  status=' + val(d.status),
      'NUXEL-WL-FB    : frames_ok=' + val(w.frames_ok) + '  decon_pan_failed=' + val(w.decon_pan_failed) +
                          '  fb=' + val(w.fb_virtual_size),
      'DISPLAY PATH   : ' + val(w.path) + '  fbdev=' + val(f.fb0) + '  /dev/dri=' + val(f.drm_render_node)
    ];
    out.textContent = lines.join('\n');
    if (detail) detail.textContent = st.honest_summary || (st.blocked_reason || 'No further detail reported.');
    if (verdict) {
      verdict.textContent = 'VERDICT: ' + (st.verdict || 'UNKNOWN') +
        '  ·  acceleration label=' + (st.acceleration_label || 'UNKNOWN') +
        '\nPhoc and WebKit are judged independently. A kbase compositor context does not make WebKit accelerated.';
    }
  }
  var graphicsReq = 0;
  function showGraph() {
    var out = $('graphics-acceleration-state');
    if (out) out.textContent = 'Reading GPU, Phoc, EGL, GTK, WebKit and framebuffer path (3 s deadline)…';
    var req = ++graphicsReq;
    return bounded('graphics', 'status', {}, 3000).then(function (st) {
      if (req !== graphicsReq) return st;
      renderGraphics(st);
      return st;
    });
  }
  function runGraphicsTest() {
    var out = $('graphics-acceleration-state');
    var v = $('graphics-acceleration-verdict');
    if (out) out.textContent = 'Running bounded Wayland GLES test in this Phoc session…';
    if (v) v.textContent = 'VERDICT: TESTING';
    return bounded('graphics', 'test', { kind: 'wayland' }, 25000).then(function (res) {
      if (v) {
        v.textContent = 'GRAPHICS TEST: ' + (res && res.success ? 'PASS' : 'FAIL') +
          '\nexit=' + val(res && res.exit_code) + ' elapsed=' + val(res && res.elapsed_s) + ' s' +
          (res && (res.error || res.detail) ? '\n' + (res.error || res.detail) : '') +
          '\n' + ((res && (res.stdout || res.stderr)) ? String(res.stdout || res.stderr).slice(-2000) : '');
      }
      return showGraph();
    });
  }
  // The legacy Graphics tab retains its detailed JSON/probe surface.
  function showGraphTab() {
    var out = $('graphics-state');
    if (out) out.textContent = 'Reading graphics layers…';
    return bounded('graphics', 'status', {}, 3000).then(function (doc) {
      if (!out) return;
      out.textContent = (doc && doc.success !== false)
        ? pretty(doc) : 'Graphics diagnostic unavailable:\n' + pretty(doc);
    });
  }
  function probe(kind) {
    var out = $('graphics-probes');
    if (out) out.textContent = 'Running ' + kind + ' EGL probe…';
    return bounded('graphics', 'test', { kind: kind }, 25000).then(function (res) {
      if (out) out.textContent = pretty(res);
      showGraph();
      showGraphTab();
    });
  }
  document.addEventListener('DOMContentLoaded', function () {
    var r = $('graphics-accel-refresh'), t = $('graphics-accel-test');
    var gr = $('graphics-refresh'), s = $('graphics-probe-surfaceless'), w = $('graphics-probe-wayland');
    if (r) r.addEventListener('click', showGraph);
    if (t) t.addEventListener('click', runGraphicsTest);
    if (gr) gr.addEventListener('click', showGraphTab);
    if (s) s.addEventListener('click', function () { probe('surfaceless'); });
    if (w) w.addEventListener('click', function () { probe('wayland'); });
    document.querySelectorAll('.tab').forEach(function (tab) {
      if (tab.dataset.tab === 'displays') tab.addEventListener('click', showGraph);
      if (tab.dataset.tab === 'graphics') tab.addEventListener('click', showGraphTab);
    });
    var panel = document.getElementById('tab-displays');
    if (panel && panel.classList.contains('active')) showGraph();
  });
  window.NuxelGraphicsSettings = { refresh: showGraph, test: runGraphicsTest };
})();
