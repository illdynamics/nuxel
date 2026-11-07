/* Nuxel Media Downloader — yt-dlp backend UI (PWNAGE-81000).
 * Metadata, progress and cancellation are real bridge calls.  No URL is ever
 * passed through a shell; the host builds a yt-dlp argv array and validates the
 * URL before starting.  Cookie contents are never logged or shown.
 */
(function () {
  'use strict';
  var meta = null, job = null, poll = null;
  var PREF_FORMAT = 'nuxel.downloader.format';
  var PREF_COOKIES = 'nuxel.downloader.cookieSource';
  function $(id) { return document.getElementById(id); }
  function saved(key, fallback) { try { return localStorage.getItem(key) || fallback; } catch (e) { return fallback; } }
  function remember(key, value) { try { localStorage.setItem(key, value); } catch (e) {} }
  function bridge() {
    if (window.NuxelBridge && typeof window.NuxelBridge.call === 'function') return window.NuxelBridge;
    try {
      if (window.parent && window.parent.NuxelBridge && typeof window.parent.NuxelBridge.call === 'function') return window.parent.NuxelBridge;
    } catch (e) {}
    return null;
  }
  function call(verb, params) {
    var b = bridge();
    if (!b) return Promise.resolve({ success: false, error: 'Nuxel bridge unavailable' });
    return Promise.resolve(b.call('downloader', verb, params || {})).catch(function (e) {
      return { success: false, error: String(e && e.message || e) };
    });
  }
  function text(id, value) { var e = $(id); if (e) e.textContent = value; }
  function show(id, on) { var e = $(id); if (e) e.classList.toggle('hidden', !on); }
  function noticeAccepted() {
    try {
      if (!window.DownloadQueue) return false;
      var store = window.DownloadQueue.deserialize(localStorage.getItem('nuxel-downloader-queue-v1') || '{}');
      return window.DownloadQueue.noticeSatisfied(store);
    } catch (e) { return false; }
  }
  function fmtDur(s) {
    if (!Number.isFinite(Number(s))) return 'duration unknown';
    var n = Number(s), h = Math.floor(n / 3600), m = Math.floor((n % 3600) / 60), sec = Math.floor(n % 60);
    return (h ? h + ':' : '') + String(m).padStart(2, '0') + ':' + String(sec).padStart(2, '0');
  }
  function fmtBytes(n) {
    if (!Number.isFinite(Number(n)) || Number(n) <= 0) return '—';
    var u = ['B', 'KiB', 'MiB', 'GiB'], i = 0, v = Number(n);
    while (v >= 1024 && i < u.length - 1) { v /= 1024; i++; }
    return (i ? v.toFixed(1) : v) + ' ' + u[i];
  }
  function renderMeta(doc) {
    meta = doc;
    show('md-meta', true);
    text('md-title', doc.title || 'Untitled media');
    text('md-info', (doc.extractor || 'site unknown') + ' · ' + fmtDur(doc.duration) +
      (doc.uploader ? ' · ' + doc.uploader : '') +
      ' · formats: ' + (doc.format_count || 0) +
      ' · audio: ' + (doc.audio_available ? 'yes' : 'no') +
      ' · video: ' + (doc.video_available ? 'yes' : 'no'));
    var thumb = $('md-thumb');
    if (thumb) {
      if (doc.thumbnail) { thumb.src = doc.thumbnail; thumb.style.display = ''; }
      else { thumb.removeAttribute('src'); thumb.style.display = 'none'; }
    }
    var lines = (doc.formats || []).slice(0, 30).map(function (f) {
      return (f.format_id || '?') + '  ' + (f.ext || '?') + '  ' +
        (f.resolution || f.format_note || '') + '  ' +
        (f.vcodec && f.vcodec !== 'none' ? 'v:' + f.vcodec : 'audio-only') +
        '  ' + fmtBytes(f.filesize);
    });
    text('md-formats', lines.join('\n') || 'No format list returned.');
    var start = $('md-start');
    if (start) start.disabled = !noticeAccepted();
    if (!noticeAccepted()) text('md-error', 'Accept the legal-use notice in the Legal notice tab before downloading.');
    else text('md-error', '');
  }
  function fetchMeta() {
    var url = ($('md-url') || {}).value || '';
    var cookies = ($('md-cookies') || {}).value || 'none';
    if (!url) { text('md-error', 'Paste a URL first.'); return; }
    text('md-state', 'Validating URL and extracting metadata with yt-dlp…');
    text('md-error', '');
    meta = null;
    return call('metadata', { url: url, cookie_source: cookies }).then(function (r) {
      if (!r || r.success === false) {
        text('md-state', 'Metadata failed.');
        text('md-error', (r && (r.detail || r.error)) || 'unknown error');
        show('md-meta', false);
        return r;
      }
      text('md-state', 'Metadata extracted. Choose MP3/MP4 and press Download.');
      renderMeta(r);
      return r;
    });
  }
  function start() {
    var url = meta && meta.webpage_url || ($('md-url') || {}).value || '';
    if (!url) { text('md-error', 'Paste a URL first.'); return; }
    if (!noticeAccepted()) { text('md-error', 'Accept the legal-use notice first.'); return; }
    var fmt = ($('md-format') || {}).value || 'mp3';
    var cookies = ($('md-cookies') || {}).value || 'none';
    remember(PREF_FORMAT, fmt); remember(PREF_COOKIES, cookies);
    var startBtn = $('md-start');
    if (startBtn) startBtn.disabled = true;
    text('md-state', 'Starting real yt-dlp ' + fmt.toUpperCase() + ' job…');
    return call('start', { url: url, format: fmt, cookie_source: cookies }).then(function (r) {
      if (!r || r.success === false) {
        if (startBtn) startBtn.disabled = false;
        text('md-state', 'Download did not start.');
        text('md-error', (r && (r.detail || r.error)) || 'unknown error');
        return r;
      }
      job = r.job;
      var cancel = $('md-cancel'); if (cancel) cancel.disabled = false;
      text('md-state', 'Downloading with yt-dlp…');
      startPolling();
      return r;
    });
  }
  function setProgress(j) {
    var pct = Number(j.progress || 0);
    var bar = $('md-bar'); if (bar) bar.style.width = Math.max(0, Math.min(100, pct)) + '%';
    var speed = j.speed ? fmtBytes(j.speed) + '/s' : 'speed —';
    var eta = Number.isFinite(Number(j.eta)) ? ' · ETA ' + fmtDur(j.eta) : '';
    text('md-state', (j.status || '?') + ': ' + pct.toFixed(1) + '% · ' + fmtBytes(j.bytes) +
      (j.total_bytes ? ' / ' + fmtBytes(j.total_bytes) : '') + ' · ' + speed + eta);
    if (j.error) text('md-error', j.error);
    else if (j.status !== 'failed') text('md-error', '');
  }
  function pollStatus() {
    if (!job) return;
    call('status', { job_id: job.id }).then(function (r) {
      if (!r || !r.job) { stopPolling(); return; }
      job = r.job;
      setProgress(job);
      if (job.status === 'completed' || job.status === 'done') {
        stopPolling();
        text('md-state', 'Completed and verified: ' + (job.file || 'file in ~/Downloads') +
          (job.verification ? ' · ' + job.verification.format_name : ''));
        var cancel = $('md-cancel'); if (cancel) cancel.disabled = true;
        var startBtn = $('md-start'); if (startBtn) startBtn.disabled = false;
        var open = $('md-open'); if (open) open.disabled = false;
        try { document.dispatchEvent(new CustomEvent('nuxel:media-changed', { detail: { path: job.file } })); } catch (e) {}
      } else if (job.status === 'failed' || job.status === 'cancelled') {
        stopPolling();
        var c = $('md-cancel'); if (c) c.disabled = true;
        var s = $('md-start'); if (s) s.disabled = false;
      }
    });
  }
  function startPolling() {
    stopPolling();
    pollStatus();
    poll = setInterval(pollStatus, 1000);
  }
  function stopPolling() { if (poll) { clearInterval(poll); poll = null; } }
  function cancel() {
    if (!job) return;
    text('md-state', 'Requesting cancellation…');
    call('cancel', { job_id: job.id }).then(function (r) {
      if (r && r.success === false) text('md-error', r.error || 'cancel failed');
    });
  }
  function loadCookies() {
    return call('cookies', {}).then(function (r) {
      var sel = $('md-cookies');
      if (!sel || !r || !r.sources) return;
      var savedSource = saved(PREF_COOKIES, '');
      sel.innerHTML = '';
      var chosen = null;
      r.sources.forEach(function (s) {
        var o = document.createElement('option');
        o.value = s.id;
        o.textContent = s.label + (s.available ? '' : ' (unavailable: ' + (s.detail || 'not present') + ')');
        o.disabled = !s.available || s.id === 'none';
        if (s.available && s.id !== 'none' && !chosen) chosen = s.id;
        if (s.available && s.id === savedSource) chosen = s.id;
        sel.appendChild(o);
      });
      if (chosen) sel.value = chosen;
      remember(PREF_COOKIES, sel.value || 'none');
      sel.addEventListener('change', function () { remember(PREF_COOKIES, sel.value); });
    });
  }
  function openDownloads() {
    try {
      var reg = window.parent && window.parent.appRegistry;
      if (reg && typeof reg.launchApp === 'function') { reg.launchApp('org.nuxel.Files'); return; }
    } catch (e) {}
    location.href = '../files/index.html';
  }
  function bind() {
    var f = $('md-fetch'); if (f) f.addEventListener('click', fetchMeta);
    var s = $('md-start'); if (s) s.addEventListener('click', start);
    var c = $('md-cancel'); if (c) c.addEventListener('click', cancel);
    var u = $('md-url'); if (u) u.addEventListener('keydown', function (e) { if (e.key === 'Enter') fetchMeta(); });
    var fmt = $('md-format');
    if (fmt) { fmt.value = saved(PREF_FORMAT, 'mp3'); fmt.addEventListener('change', function () { remember(PREF_FORMAT, fmt.value); }); }
    var o = $('md-open'); if (o) o.addEventListener('click', openDownloads);
    loadCookies();
    // Recover the latest real job after app reload.
    call('status', {}).then(function (r) {
      if (!r || !Array.isArray(r.jobs) || !r.jobs.length) return;
      var latest = r.jobs[0];
      if (latest && ['queued','validating','extracting metadata','downloading','post-processing','verifying output'].indexOf(latest.status) >= 0) {
        job = latest; startPolling();
      } else if (latest && (latest.status === 'completed' || latest.status === 'done')) {
        job = latest; setProgress(latest);
        text('md-state', 'Last job completed: ' + (latest.file || 'file in ~/Downloads'));
        var open = $('md-open'); if (open) open.disabled = false;
      }
    });
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', bind);
  else bind();
  window.nuxelMediaDownloader = { fetchMeta: fetchMeta, start: start, cancel: cancel, status: function () { return job; } };
})();
