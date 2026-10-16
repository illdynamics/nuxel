// Nuxel Media — UI wiring.  Playback goes through a REAL HTMLMediaElement; every
// claim about the route/audibility comes from MediaLibrary.describeRoute().
(function () {
  'use strict';
  var M = window.MediaLibrary;
  var el = function (id) { return document.getElementById(id); };
  var audio = el('audio'), video = el('video');
  var state = {
    lib: null, queue: null, filter: '', source: 'sample', order: 1,
    route: null, volume: null, volumeControl: null, lastError: null
  };

  function toast(msg) {
    var t = el('toast');
    t.textContent = msg; t.classList.add('show');
    clearTimeout(toast._t);
    toast._t = setTimeout(function () { t.classList.remove('show'); }, 2600);
  }

  function badge(node, text, cls) {
    node.textContent = text;
    node.className = 'badge' + (cls ? ' ' + cls : '');
  }

  function md() { return (window.NuxelBridge && typeof window.NuxelBridge.call === 'function') ? window.NuxelBridge.call : null; }
  // The shared bridge never rejects: when it cannot reach the host it returns a
  // mock object.  A mock answer is NOT device state, so every caller here treats
  // `mock: true` as "no live answer" instead of showing it as truth.
  function isMock() { return !!(window.NuxelBridge && window.NuxelBridge.isMockMode && window.NuxelBridge.isMockMode()); }
  function liveOnly(res) { return (res && res.success !== false && res.mock !== true) ? res : null; }

  /* ---------- library ---------- */

  function probeCodecs() {
    var list = [];
    if (!audio || !audio.canPlayType) return list;
    [['wav', 'audio/wav'], ['mp3', 'audio/mpeg'], ['ogg', 'audio/ogg'], ['opus', 'audio/ogg; codecs=opus'],
     ['flac', 'audio/flac'], ['m4a', 'audio/mp4'], ['mp4', 'video/mp4'], ['webm', 'video/webm']]
      .forEach(function (pair) {
        try { if (audio.canPlayType(pair[1])) list.push(pair[0]); } catch (e) { /* probing must never throw */ }
      });
    return list;
  }

  function sampleLibrary() {
    return fetch('samples/library.json', { cache: 'force-cache' })
      .then(function (r) { return r.ok ? r.json() : null; })
      .then(function (doc) { return (doc && doc.tracks) || []; })
      .catch(function () { return []; });
  }

  function liveLibrary() {
    if (!md()) return Promise.reject(new Error('no bridge'));
    return window.NuxelBridge.call('media', 'scan', { paths: null, mode: 'read-only' })
      .then(function (res) {
        if (liveOnly(res) && res.tracks && res.tracks.length) return res.tracks;
        throw new Error(res && res.mock === true
          ? 'the bridge answered in mock mode (no host) — refusing to present a mock library as a device scan'
          : (res && res.error) || 'media.scan returned no tracks');
      });
  }

  function setSource(source, note) {
    state.source = source;
    badge(el('source-badge'), 'library: ' + source, source === 'live' ? 'live' : 'sample');
    el('source-note').textContent = note || (source === 'live'
      ? 'Track list read from the device through the Nuxel bridge (media.scan).'
      : 'The Nuxel bridge did not answer, so this is the bundled offline sample library — it is NOT a scan of this device.');
  }

  function loadLibrary() {
    var codecs = probeCodecs();
    el('codecs').textContent = codecs.length ? codecs.join(', ') : 'none reported by this build';
    return liveLibrary()
      .then(function (tracks) {
        var lib = M.buildLibrary(tracks, 'live');
        setSource('live', 'Track list read from the device through the Nuxel bridge (media.scan, read-only).');
        return lib;
      })
      .catch(function (err) {
        state.lastScanError = String(err && err.message || err);
        return sampleLibrary().then(function (tracks) {
          var lib = M.buildLibrary(tracks, 'sample');
          setSource('sample', 'The Nuxel bridge did not answer (' + state.lastScanError +
            '), so this is the bundled offline sample library — it is NOT a scan of this device.');
          return lib;
        });
      })
      .then(function (lib) {
        state.lib = lib;
        state.queue = M.newQueue(lib.tracks);
        renderTracks();
        renderNow();
      });
  }

  function renderTracks() {
    var host = el('track-list');
    var list = M.search(state.lib, state.filter);
    host.innerHTML = '';
    if (!list.length) {
      host.innerHTML = '<p class="hint">No tracks match' + (state.filter ? ' “' + state.filter + '”' : '') + '.</p>';
      return;
    }
    list.forEach(function (t) {
      var row = document.createElement('div');
      row.className = 'track' + (state.queue && M.current(state.queue) && M.current(state.queue).id === t.id ? ' playing' : '');
      var sup = M.decodeSupport(t.name, probeCodecs());
      var c = M.current(state.queue);
      row.innerHTML = '<span class="kind">' + t.kind + '</span>' +
        '<span class="tname">' + escapeHtml(t.title) + ' <span class="hint">— ' + escapeHtml(t.artist) + '</span></span>' +
        '<span class="tlen">' + M.formatTime(t.seconds) + '</span>';
      if (c && c.id === t.id) row.querySelector('.tname').textContent = '▶ ' + t.title + ' — ' + t.artist;
      row.title = t.note || (sup.supported === false ? sup.note : '');
      row.addEventListener('click', function () { playTrack(t); });
      host.appendChild(row);
    });
    el('lib-count').textContent = list.length + ' of ' + state.lib.tracks.length + ' shown · source ' + state.lib.source;
  }

  function escapeHtml(s) {
    return String(s === null || s === undefined ? '' : s).replace(/[&<>"']/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c];
    });
  }

  /* ---------- playback ---------- */

  function mediaElementFor(t) { return t.kind === 'video' ? video : audio; }

  function playTrack(t) {
    state.lastError = null;
    if (!t.url || t.playable === false) {
      var why = t.note || 'no media file is bundled for this entry';
      toast('Cannot play “' + t.title + '” — ' + why);
      el('error-line').textContent = 'Refused to play “' + t.title + '”: ' + why;
      return;
    }
    var ix = state.queue.tracks.findIndex(function (x) { return x.id === t.id; });
    if (ix >= 0) state.queue.index = ix;
    var node = mediaElementFor(t);
    var other = t.kind === 'video' ? audio : video;
    try { other.pause(); } catch (e) { /* nothing playing */ }
    node.src = t.url;
    var p = node.play();
    if (p && p.catch) {
      p.then(function () {
        el('error-line').textContent = '';
      }).catch(function (e) {
        state.lastError = e && e.message ? e.message : String(e);
        el('error-line').textContent = 'Playback refused by the media pipeline: ' + state.lastError;
        toast('Playback failed: ' + state.lastError);
      });
    }
    renderTracks();
    renderNow();
  }

  function renderNow() {
    var t = state.queue ? M.current(state.queue) : null;
    if (!t) {
      el('np-title').textContent = 'Nothing queued';
      el('np-sub').textContent = '';
      el('np-state').textContent = 'idle';
      return;
    }
    el('np-title').textContent = t.title;
    el('np-sub').textContent = t.artist + ' · ' + t.kind + ' · ' + t.container +
      (t.seconds !== null ? ' · ' + M.formatTime(t.seconds) : '');
    el('cover').textContent = t.kind === 'video' ? '🎬' : '♪';
    if (t.art) el('cover').style.backgroundImage = 'url(' + t.art + ')';
    else el('cover').style.backgroundImage = '';
  }

  function updateTimes() {
    var node = state.queue && M.current(state.queue) && M.current(state.queue).kind === 'video' ? video : audio;
    var dur = isFinite(node.duration) ? node.duration : (M.current(state.queue) ? M.current(state.queue).seconds : null);
    el('t-cur').textContent = M.formatTime(node.currentTime || 0);
    el('t-dur').textContent = M.formatTime(dur);
    var seek = el('seek');
    if (dur) { seek.max = String(Math.floor(dur)); seek.value = String(Math.floor(node.currentTime || 0)); }
    el('np-state').textContent = node.paused ? 'paused' : (node.ended ? 'ended' : 'playing');
    el('sb-src').textContent = 'library source: ' + state.source;
    el('sb-route').textContent = 'route: ' + (state.route ? (state.route.audible === 'verified' ? 'audible verified' : 'audible UNVERIFIED') : '—');
  }

  function togglePlay() {
    var q = state.queue;
    if (!q || !q.tracks.length) { toast('Library is empty'); return; }
    var t = M.current(q);
    var node = t && t.kind === 'video' ? video : audio;
    if (node.paused) playTrack(t || q.tracks[0]); else node.pause();
    updateTimes();
  }

  function step(forward) {
    var q = state.queue;
    if (!q || !q.tracks.length) return;
    var r = M.advance(q, state.order++);
    if (r.ended) { toast('End of queue (repeat: ' + q.repeat + ')'); renderNow(); return; }
    playTrack(r.track);
  }

  /* ---------- volume over the real mixer ---------- */

  function routeProbe() {
    if (!md()) return Promise.resolve(null);
    return window.NuxelBridge.call('audio', 'route', {})
      .then(function (res) {
        if (res && res.mock === true) {
          el('vol-note').textContent = 'bridge mock mode: the mixer was not read and NOT changed';
          return null;
        }
        return liveOnly(res);
      })
      .catch(function () { return null; });
  }

  function renderRoute(probe) {
    state.route = M.describeRoute(probe);
    var dl = el('route-kv');
    dl.innerHTML = '';
    state.route.lines.forEach(function (pair) {
      var dt = document.createElement('dt'); dt.textContent = pair[0];
      var dd = document.createElement('dd'); dd.textContent = pair[1];
      dl.appendChild(dt); dl.appendChild(dd);
    });
    el('route-summary').textContent = state.route.summary;
    el('route-summary').className = 'pill ' + (state.route.audible === 'verified' ? 'ok' : 'warn');
  }

  function setVolume(percent) {
    var pct = M.clampVolume(percent);
    if (pct === null) return;
    var call = md();
    if (!call) {
      el('vol-note').textContent = 'bridge unavailable — the mixer was not changed (slider position is local only)';
      return;
    }
    call('audio', 'setVolume', { percent: pct })
      .then(function (res) {
        if (res && res.mock === true) {
          el('vol-note').textContent = 'bridge mock mode — the mixer was NOT changed (no host to change it)';
          return;
        }
        if (res && res.percent !== undefined && res.percent !== null) {
          state.volume = M.clampVolume(res.percent);
          el('vol').value = String(state.volume);
          el('vol-note').textContent = 'mixer reports ' + state.volume + '% on ' + (res.control || 'the default control');
        } else if (res && res.success === false) {
          el('vol-note').textContent = 'mixer refused: ' + (res.error || 'unknown reason') + ' — volume NOT changed';
        } else {
          el('vol-value').textContent = pct + '%';
          el('vol-note').textContent = 'requested ' + pct + '% — the mixer did not echo a value, so this is a request, not a reading';
        }
      })
      .catch(function (e) {
        el('vol-note').textContent = 'mixer call failed (' + (e && e.message ? e.message : e) + ') — volume NOT changed';
      });
    el('vol-value').textContent = pct + '%';
  }

  /* ---------- tabs + wiring ---------- */

  function tabs() {
    Array.prototype.forEach.call(document.querySelectorAll('.tab'), function (b) {
      b.addEventListener('click', function () {
        Array.prototype.forEach.call(document.querySelectorAll('.tab'), function (x) { x.classList.remove('active'); });
        Array.prototype.forEach.call(document.querySelectorAll('.panel'), function (x) { x.classList.remove('active'); });
        b.classList.add('active');
        el('tab-' + b.dataset.tab).classList.add('active');
        if (b.dataset.tab === 'route') refreshRoute();
      });
    });
  }

  function refreshRoute() {
    el('route-summary').textContent = 'probing…';
    return routeProbe().then(renderRoute);
  }

  function wire() {
    el('play').addEventListener('click', togglePlay);
    el('prev').addEventListener('click', function () { step(false); });
    el('next').addEventListener('click', function () { step(true); });
    el('stop').addEventListener('click', function () {
      var t = state.queue && M.current(state.queue);
      var node = t && t.kind === 'video' ? video : audio;
      node.pause(); try { node.currentTime = 0; } catch (e) {}
      updateTimes();
    });
    el('seek').addEventListener('input', function () {
      var t = state.queue && M.current(state.queue);
      var node = t && t.kind === 'video' ? video : audio;
      if (isFinite(node.duration)) node.currentTime = Number(el('seek').value);
      el('t-cur').textContent = M.formatTime(Number(el('seek').value));
    });
    el('vol').addEventListener('change', function () { setVolume(el('vol').value); });
    el('repeat').addEventListener('click', function () {
      var order = ['off', 'all', 'one'];
      var q = state.queue; if (!q) return;
      var nextm = order[(order.indexOf(q.repeat) + 1) % order.length];
      M.setRepeat(q, nextm);
      el('repeat').textContent = 'repeat: ' + nextm;
    });
    el('shuffle').addEventListener('click', function () {
      if (!state.queue) return;
      state.queue.shuffle = !state.queue.shuffle;
      el('shuffle').textContent = 'shuffle: ' + (state.queue.shuffle ? 'on' : 'off');
    });
    el('search').addEventListener('input', function () { state.filter = el('search').value; renderTracks(); });
    el('refresh-route').addEventListener('click', refreshRoute);
    el('reload').addEventListener('click', function () { loadLibrary().then(refreshRoute); });
    [audio, video].forEach(function (node) {
      node.addEventListener('timeupdate', updateTimes);
      node.addEventListener('durationchange', updateTimes);
      node.addEventListener('play', updateTimes);
      node.addEventListener('pause', updateTimes);
      node.addEventListener('error', function () {
        var code = node.error ? (node.error.message || ('MediaError ' + node.error.code)) : 'unknown error';
        el('error-line').textContent = 'media pipeline error: ' + code;
      });
      node.addEventListener('ended', function () {
        var q = state.queue; if (!q) return;
        if (q.repeat === 'one') { playTrack(M.current(q)); return; }
        step(true);
      });
      node.addEventListener('volumechange', function () {
        el('vol-value').textContent = Math.round((node.volume || 0) * 100) + '%';
      });
    });
    document.addEventListener('keydown', function (e) {
      if (e.target && /input|textarea/i.test(e.target.tagName || '')) return;
      if (e.code === 'Space') { e.preventDefault(); togglePlay(); }
      else if (e.code === 'ArrowRight') { step(true); }
      else if (e.code === 'ArrowLeft') { step(false); }
      else if (e.code === 'ArrowUp') { setVolume((state.volume === null ? 50 : state.volume) + 5); }
      else if (e.code === 'ArrowDown') { setVolume((state.volume === null ? 50 : state.volume) - 5); }
    });
    el('close').addEventListener('click', function () { try { window.close(); } catch (e) {} });
  }

  document.addEventListener('DOMContentLoaded', function () {
    tabs(); wire();
    el('vol-value').textContent = '—';
    setSource('sample', 'loading the library…');
    loadLibrary().then(function () {
      return refreshRoute();
    }).then(function () {
      el('owner-steps').innerHTML = state.route && state.route.audible === 'verified'
        ? '<b>Owner listening test recorded.</b> The build may cite audibility in manual proof area 41.'
        : '<b>Owner listening test NOT recorded for this build.</b> Everything else can be exercised without it; audibility stays unclaimed.';
    });
  });
}());
