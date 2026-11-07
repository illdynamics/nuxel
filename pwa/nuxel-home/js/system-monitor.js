// Nuxel Home system monitor. One shared, cancellable Home-only polling loop.
// The native loopback endpoint owns all kernel reads; this page never invents
// a number if a source is absent or malformed.
(function (global) {
  'use strict';
  var ENDPOINT = 'http://127.0.0.1:8624/metrics';
  var DEFAULT_INTERVAL = 10;
  var ALLOWED_INTERVALS = [1, 2, 3, 5, 10];
  var timer = null, serial = 0, activeRequest = 0;
  var config = { enabled: true, interval: DEFAULT_INTERVAL, detailed: true, gpuMemoryDisplay: 'amount-percent' };
  var widget;

  function appearance() {
    try { return JSON.parse(global.localStorage.getItem('nuxel.homeAppearance') || '{}'); }
    catch (_) { return {}; }
  }
  function normalize(input) {
    input = input || {};
    var interval = Number(input.systemMonitorInterval || input.interval || DEFAULT_INTERVAL);
    var gpuMode = String(input.gpuMemoryDisplay || 'amount-percent');
    if (['amount-percent','percentage','amount'].indexOf(gpuMode) < 0) gpuMode = 'amount-percent';
    return { enabled: input.systemMonitorEnabled !== false && input.enabled !== false,
      interval: ALLOWED_INTERVALS.indexOf(interval) >= 0 ? interval : DEFAULT_INTERVAL,
      detailed: input.systemMonitorDetailed !== false && input.detailed !== false,
      gpuMemoryDisplay: gpuMode };
  }
  function homeVisible() {
    // BACKGROUND means an app iframe is hidden and Home is on the glass; it is
    // still visible Home. Only a foreground app, an in-flight launch, the
    // lockscreen, or an actually powered-down panel hides Home.
    var state = document.body.dataset.appState;
    var off = document.body.dataset.displayOff === '1' || document.body.classList.contains('display-off');
    var locked = document.body.classList.contains('lockscreen-active') ||
      (document.getElementById('lockscreen') && !document.getElementById('lockscreen').hidden);
    // Quick Settings / Applications drawer / Recents are interactive overlays.
    // Their open animation must not compete with a metrics fetch + four DOM
    // meter writes; the loop resumes on the next lifecycle/visibility event.
    var qs = document.getElementById('quick-settings');
    if (qs && !qs.classList.contains('hidden')) return false;
    if (document.body.classList.contains('app-drawer-open')) return false;
    var recents = document.getElementById('recents-view');
    if (recents && !recents.classList.contains('hidden')) return false;
    return document.visibilityState === 'visible' && state !== 'ACTIVE' &&
      state !== 'LAUNCHING' && state !== 'CLOSING' && !off && !locked;
  }
  function shouldPoll() { return config.enabled && homeVisible(); }
  function meter(name, value, available, display) {
    var el = widget && widget.querySelector('[data-meter="' + name + '"]');
    if (!el) return;
    var text = el.querySelector('.system-meter-value'), bar = el.querySelector('.system-meter-bar i');
    var valid = available && Number.isFinite(Number(value));
    var percent = valid ? Math.max(0, Math.min(100, Number(value))) : 0;
    el.dataset.unavailable = valid ? 'false' : 'true';
    text.textContent = valid ? (display || Math.round(percent) + '%') : 'N/A';
    bar.style.width = percent + '%';
  }
  function detail(name, value) {
    var el = widget && widget.querySelector('[data-meter="' + name + '"] .system-meter-detail');
    if (el) el.textContent = value;
  }
  function mhz(value) {
    return Number.isFinite(Number(value)) ? Math.round(Number(value)) + ' MHz' : 'N/A';
  }
  function gib(kib) { return (Number(kib) / 1048576).toFixed(1) + ' GiB'; }
  function memAmount(kib) {
    var value = Number(kib);
    if (!Number.isFinite(value)) return 'N/A';
    var mib = value / 1024;
    return mib >= 1024 ? (mib / 1024).toFixed(1) + ' GiB' : Math.round(mib) + ' MiB';
  }
  function render(data) {
    meter('cpu', data.cpu_percent, data.cpu_status === 'ok');
    meter('memory', data.memory_percent, data.memory_status === 'ok');
    meter('gpu', data.gpu_percent, data.gpu_status === 'ok');

    // The Mali driver tracks allocations in shared system RAM (debugfs
    // used_pages on this kernel).  MemTotal is the budget REFERENCE/upper bound,
    // not dedicated GPU capacity; the VRAM cell reports the tracked amount only.
    var gpuUsed = Number(data.gpu_memory_kib);
    var gpuTotal = Number(data.gpu_memory_total_kib);
    var gpuMemoryOk = (data.gpu_memory_status === 'ok_shared_budget_reference' || data.gpu_memory_status === 'ok') &&
      Number.isFinite(gpuUsed) && Number.isFinite(gpuTotal) && gpuTotal > 0;
    var gpuPct = gpuMemoryOk ? (gpuUsed / gpuTotal) * 100 : null;
    var mode = config.gpuMemoryDisplay || 'amount-percent';
    var amount = Number.isFinite(gpuUsed) ? memAmount(gpuUsed) : null;
    var display = null;
    if (gpuMemoryOk) {
      if (mode === 'percentage') display = gpuPct.toFixed(1) + '% of RAM';
      else if (mode === 'amount') display = amount;
      else display = amount + ' · ' + gpuPct.toFixed(1) + '%';
    } else if (amount) {
      display = mode === 'percentage' ? 'N/A' : amount;
    }
    meter('gpu-memory', gpuPct, gpuMemoryOk, display);

    detail('cpu', mhz(data.cpu_frequency_mhz));
    detail('memory', data.memory_status === 'ok' && Number.isFinite(Number(data.memory_used_kib)) && Number.isFinite(Number(data.memory_total_kib)) ? gib(data.memory_used_kib) + '/' + gib(data.memory_total_kib) : 'N/A');
    detail('gpu', mhz(data.gpu_frequency_mhz));
    detail('gpu-memory', gpuMemoryOk ? (mode === 'amount' ? 'shared system RAM (percentage unavailable by setting)' : 'of ' + memAmount(gpuTotal) + ' shared system RAM') : 'percentage unavailable (no allocation/budget pair)');
  }
  // PWNAGE-52000: the GPU meter label must not imply whole-GUI acceleration.
  // We ask the authoritative graphics provider (bounded, low frequency) and
  // only append (ACC) when every measured interactive layer is accelerated.
  var gpuLabelTimer = null, gpuLabelState = 'unknown', gpuLabelChecked = 0;
  function setGpuLabel(state) {
    gpuLabelState = state;
    var el = widget && widget.querySelector('[data-meter="gpu"] .system-meter-label');
    if (!el) return;
    var text = 'GPU';
    var title = 'GPU utilization and clock; acceleration state unknown';
    if (state === 'ACCELERATED') { text = 'GPU (ACC)'; title = 'Phoc and WebKitGTK are both proved hardware-accelerated'; }
    else if (state === 'PARTIAL') { text = 'GPU (PARTIAL)'; title = 'Phoc kbase is accelerated; WebKitGTK/GTK GL is software. Copy to fbdev/DECON is CPU work.'; }
    else if (state === 'SOFTWARE') { text = 'GPU'; title = 'No live accelerated GUI path proved'; }
    el.textContent = text;
    var meter = el.closest('.system-meter'); if (meter) meter.title = title;
  }
  function bridgeCall(ns, verb, params) {
    var b = global.NuxelBridge;
    if (!b || typeof b.call !== 'function') {
      try { b = global.parent && global.parent.NuxelBridge; } catch (_) {}
    }
    if (!b || typeof b.call !== 'function') return Promise.reject(new Error('bridge unavailable'));
    return Promise.resolve(b.call(ns, verb, params || {}));
  }
  function refreshGpuLabel(force) {
    if (!shouldPoll()) return;
    var now = Date.now();
    if (!force && now - gpuLabelChecked < 60000) return;
    gpuLabelChecked = now;
    var timer;
    var timeout = new Promise(function (resolve) { timer = setTimeout(function () { resolve(null); }, 2500); });
    Promise.race([bridgeCall('graphics', 'status', {}), timeout]).then(function (st) {
      if (timer) clearTimeout(timer);
      if (!st || st.success === false) { setGpuLabel('unknown'); return; }
      setGpuLabel(st.verdict || 'unknown');
    }).catch(function () { if (timer) clearTimeout(timer); setGpuLabel('unknown'); });
  }
  function stop() {
    if (timer !== null) { global.clearTimeout(timer); timer = null; }
    activeRequest = ++serial;
  }
  function schedule() {
    if (!shouldPoll()) return;
    timer = global.setTimeout(poll, config.interval * 1000);
  }
  function poll() {
    timer = null;
    if (!shouldPoll()) return;
    var request = ++serial;
    activeRequest = request;

    // Cache-bust every sample. WebKit kept serving a cached 200 with frozen
    // values after the socket-activated collector had exited; the query is
    // accepted by nuxel-metricsd and forces a fresh kernel read each time.
    var url = ENDPOINT + '?t=' + Date.now() + '-' + request;
    var controller = global.AbortController ? new global.AbortController() : null;
    var abortTimer = controller ? global.setTimeout(function () { controller.abort(); }, 5000) : null;
    function finished() {
      if (abortTimer !== null) { global.clearTimeout(abortTimer); abortTimer = null; }
    }
    global.fetch(url, {
      cache: 'no-store',
      credentials: 'omit',
      signal: controller ? controller.signal : undefined
    })
      .then(function (response) {
        if (!response.ok) throw new Error('metrics status ' + response.status);
        return response.json();
      })
      .then(function (data) { finished(); if (request === activeRequest && shouldPoll()) render(data); })
      .catch(function () { finished(); if (request === activeRequest && shouldPoll()) render({}); })
      .then(function () {
        if (request === activeRequest) { refreshGpuLabel(false); schedule(); }
      });
  }
  function configure(input) {
    config = normalize(input || appearance());
    if (gpuLabelTimer !== null) { global.clearTimeout(gpuLabelTimer); gpuLabelTimer = null; }
    if (widget) { widget.hidden = !config.enabled; widget.dataset.detailed = config.detailed ? 'true' : 'false'; widget.dataset.gpuMemoryDisplay = config.gpuMemoryDisplay; }
    stop();
    if (shouldPoll()) { poll(); refreshGpuLabel(true); }
  }
  function init() {
    widget = document.getElementById('system-monitor');
    if (!widget) return;
    widget.dataset.reducedMotion = global.matchMedia && global.matchMedia('(prefers-reduced-motion: reduce)').matches ? 'true' : 'false';
    document.addEventListener('visibilitychange', function () { configure(config); });
    document.addEventListener('app:lifecycle', function () { configure(config); });
    document.addEventListener('nuxel:overlay-changed', function () { configure(config); });
    configure(appearance());
  }
  global.NuxelSystemMonitor = { configure: configure, stop: stop, _normalize: normalize, _shouldPoll: shouldPoll,
    _config: function () { return config; },
    _gpuLabel: function () { return gpuLabelState; }, _setGpuLabel: setGpuLabel };
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init);
  else init();
})(window);
