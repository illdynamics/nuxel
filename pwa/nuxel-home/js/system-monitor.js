// Nuxel Home system monitor. One shared, cancellable Home-only polling loop.
// The native loopback endpoint owns all kernel reads; this page never invents
// a number if a source is absent or malformed.
(function (global) {
  'use strict';
  var ENDPOINT = 'http://127.0.0.1:8624/metrics';
  var DEFAULT_INTERVAL = 3;
  var ALLOWED_INTERVALS = [1, 2, 3, 5, 10];
  var timer = null, serial = 0, activeRequest = 0;
  var config = { enabled: true, interval: DEFAULT_INTERVAL, detailed: true };
  var widget;

  function appearance() {
    try { return JSON.parse(global.localStorage.getItem('nuxel.homeAppearance') || '{}'); }
    catch (_) { return {}; }
  }
  function normalize(input) {
    input = input || {};
    var interval = Number(input.systemMonitorInterval || input.interval || DEFAULT_INTERVAL);
    return { enabled: input.systemMonitorEnabled !== false && input.enabled !== false,
      interval: ALLOWED_INTERVALS.indexOf(interval) >= 0 ? interval : DEFAULT_INTERVAL,
      detailed: input.systemMonitorDetailed !== false && input.detailed !== false };
  }
  function homeVisible() {
    return document.visibilityState === 'visible' && document.body.dataset.appState !== 'ACTIVE' &&
      document.body.dataset.appState !== 'LAUNCHING' && document.body.dataset.appState !== 'BACKGROUND';
  }
  function shouldPoll() { return config.enabled && homeVisible(); }
  function meter(name, value, available) {
    var el = widget && widget.querySelector('[data-meter="' + name + '"]');
    if (!el) return;
    var text = el.querySelector('.system-meter-value'), bar = el.querySelector('.system-meter-bar i');
    var valid = available && Number.isFinite(Number(value));
    var percent = valid ? Math.max(0, Math.min(100, Number(value))) : 0;
    el.dataset.unavailable = valid ? 'false' : 'true';
    text.textContent = valid ? Math.round(percent) + '%' : 'N/A';
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
  function render(data) {
    meter('cpu', data.cpu_percent, data.cpu_status === 'ok');
    meter('memory', data.memory_percent, data.memory_status === 'ok');
    meter('gpu', data.gpu_percent, data.gpu_status === 'ok');
    meter('gpu-memory', null, false);
    detail('cpu', mhz(data.cpu_frequency_mhz));
    detail('memory', data.memory_status === 'ok' && Number.isFinite(Number(data.memory_used_kib)) && Number.isFinite(Number(data.memory_total_kib)) ? gib(data.memory_used_kib) + '/' + gib(data.memory_total_kib) : 'N/A');
    detail('gpu', mhz(data.gpu_frequency_mhz));
    detail('gpu-memory', data.gpu_memory_status === 'unavailable_shared_memory' ? 'shared memory' : 'N/A');
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
    var request = ++serial; activeRequest = request;
    global.fetch(ENDPOINT, { cache: 'no-store', credentials: 'omit' })
      .then(function (response) { if (!response.ok) throw new Error('metrics status ' + response.status); return response.json(); })
      .then(function (data) { if (request === activeRequest && shouldPoll()) render(data); })
      .catch(function () { if (request === activeRequest && shouldPoll()) render({}); })
      .then(function () { if (request === activeRequest) schedule(); });
  }
  function configure(input) {
    config = normalize(input || appearance());
    if (widget) { widget.hidden = !config.enabled; widget.dataset.detailed = config.detailed ? 'true' : 'false'; }
    stop();
    if (shouldPoll()) poll();
  }
  function init() {
    widget = document.getElementById('system-monitor');
    if (!widget) return;
    widget.dataset.reducedMotion = global.matchMedia && global.matchMedia('(prefers-reduced-motion: reduce)').matches ? 'true' : 'false';
    document.addEventListener('visibilitychange', function () { configure(config); });
    document.addEventListener('app:lifecycle', function () { configure(config); });
    configure(appearance());
  }
  global.NuxelSystemMonitor = { configure: configure, stop: stop, _normalize: normalize, _shouldPoll: shouldPoll };
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init);
  else init();
})(window);
