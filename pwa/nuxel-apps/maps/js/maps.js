// Nuxel Maps (mission area 30 / PWNAGE 27000)
//
// A slippy map with one configured OpenStreetMap tile source, an offline
// IndexedDB tile cache, explicit Nominatim place search and an honest provider
// status feed.  Three kinds of marker are deliberately distinct:
//
//   * saved pins      -> persisted by the user (localStorage)
//   * search results  -> transient, replaced by every successful search
//   * current position-> only ever drawn from a fresh bridge/GeoClue fix
//
// The map does not require a GPS fix, a geocoding response or a network
// connection to render its grid, saved pins and cached tiles.  A search result
// or manual coordinate is NEVER labelled as a GPS position.
(function () {
  'use strict';

  var C = window.NuxelMapsCore;
  if (!C) {
    var missing = document.getElementById('overlay-msg');
    if (missing) {
      missing.textContent = 'Maps core failed to load: nuxel-common/maps-core.js is missing.';
      missing.classList.remove('hidden');
    }
    return;
  }

  var K_PINS = 'nuxel-maps-pins';
  var K_VIEW = 'nuxel-maps-view';
  var DB_NAME = 'nuxel-maps-tiles';
  var DB_STORE = 'tiles';
  var TILE_TIMEOUT_MS = 9000;
  var SEARCH_TIMEOUT_MS = 10000;
  var MAX_PARALLEL_TILES = 4;
  var TILE_RETRY_MS = 60000;
  var SEARCH_REPEAT_MS = 10000;

  function load(key, dflt) {
    try { var raw = localStorage.getItem(key); return raw ? JSON.parse(raw) : dflt; }
    catch (e) { return dflt; }
  }
  function save(key, value) {
    try { localStorage.setItem(key, JSON.stringify(value)); } catch (e) { /* ignore */ }
  }

  var config = C.loadConfig(window.localStorage);
  var savedView = load(K_VIEW, config.lastView || C.DEFAULT_CONFIG.lastView);
  var state = {
    config: config,
    zoom: savedView.zoom,
    center: { lat: savedView.lat, lon: savedView.lon },
    pins: load(K_PINS, []),
    search: C.newSearchState(),
    selected: null,
    dragging: null,
    pinch: null,
    provider: C.providerView(null, Date.now() / 1000),
    providerRaw: null,
    providerCheckedAt: 0,
    tileCache: {},
    inflight: {},
    failedAt: {},
    queue: [],
    activeFetches: 0,
    renderSeq: 0,
    drawStats: { drawn: 0, missing: 0, failed: 0 },
    tileStatus: { code: 'IDLE', message: 'checking tile source', at: null },
    lastQuery: '',
    lastQueryAt: 0
  };
  if (!Array.isArray(state.pins)) state.pins = [];

  var canvas = document.getElementById('map');
  var ctx = (canvas && canvas.getContext) ? canvas.getContext('2d') : null;
  var overlay = document.getElementById('overlay-msg');
  var badge = document.getElementById('tile-badge');
  var scaleEl = document.getElementById('scale');
  var cacheReport = document.getElementById('cache-report');
  var attributionEl = document.querySelector('.attribution');

  function tileSize() { return state.config.tileSource.tileSize || 256; }
  function maxZoom() { return state.config.tileSource.maxZoom || 19; }
  function minZoom() { return state.config.tileSource.minZoom || 0; }

  var logged = { tileOk: false, tileError: false, provider: '' };
  function appLog(msg) {
    try { if (typeof console !== 'undefined' && console.info) console.info('[Maps] ' + msg); } catch (e) {}
  }

  function toast(msg) {
    var t = document.getElementById('toast');
    if (!t) return;
    t.textContent = msg;
    t.classList.remove('hidden');
    clearTimeout(toast._t);
    toast._t = setTimeout(function () { t.classList.add('hidden'); }, 3200);
  }

  /* ---------- projection (Web Mercator, 256px tiles by default) ---------- */
  function lonToX(lon, z) { return (lon + 180) / 360 * Math.pow(2, z); }
  function latToY(lat, z) {
    var r = Math.max(-85.05112878, Math.min(85.05112878, lat)) * Math.PI / 180;
    return (1 - Math.log(Math.tan(r) + 1 / Math.cos(r)) / Math.PI) / 2 * Math.pow(2, z);
  }
  function xToLon(x, z) { return x / Math.pow(2, z) * 360 - 180; }
  function yToLat(y, z) {
    var n = Math.PI - 2 * Math.PI * y / Math.pow(2, z);
    return 180 / Math.PI * Math.atan(0.5 * (Math.exp(n) - Math.exp(-n)));
  }
  function haversine(a, b) {
    var R = 6371008.8;
    var dLat = (b.lat - a.lat) * Math.PI / 180, dLon = (b.lon - a.lon) * Math.PI / 180;
    var la1 = a.lat * Math.PI / 180, la2 = b.lat * Math.PI / 180;
    var h = Math.sin(dLat / 2) * Math.sin(dLat / 2) + Math.cos(la1) * Math.cos(la2) * Math.sin(dLon / 2) * Math.sin(dLon / 2);
    return 2 * R * Math.asin(Math.min(1, Math.sqrt(h)));
  }
  function viewWidth() { return (canvas && canvas.clientWidth) || 360; }
  function viewHeight() { return (canvas && canvas.clientHeight) || 300; }
  function worldToScreen(lat, lon) {
    var z = state.zoom, T = tileSize();
    var cx = lonToX(state.center.lon, z) * T;
    var cy = latToY(state.center.lat, z) * T;
    return { x: lonToX(lon, z) * T - cx + viewWidth() / 2, y: latToY(lat, z) * T - cy + viewHeight() / 2 };
  }
  function screenToLatLon(sx, sy) {
    var z = state.zoom, T = tileSize();
    var cx = lonToX(state.center.lon, z) * T;
    var cy = latToY(state.center.lat, z) * T;
    var wx = (sx - viewWidth() / 2 + cx) / T, wy = (sy - viewHeight() / 2 + cy) / T;
    return { lat: yToLat(wy, z), lon: xToLon(wx, z) };
  }

  function clampView() {
    state.center.lat = Math.max(-85, Math.min(85, state.center.lat));
    var lon = C.wrapLon(state.center.lon);
    state.center.lon = lon === null ? 0 : lon;
    state.zoom = Math.max(minZoom(), Math.min(maxZoom(), state.zoom));
  }

  /* ---------- IndexedDB tile cache ---------- */
  var dbPromise = null;
  function db() {
    if (dbPromise) return dbPromise;
    dbPromise = new Promise(function (resolve) {
      try {
        if (!window.indexedDB) { resolve(null); return; }
        var req = window.indexedDB.open(DB_NAME, 1);
        req.onupgradeneeded = function () {
          var d = req.result;
          if (!d.objectStoreNames.contains(DB_STORE)) d.createObjectStore(DB_STORE);
        };
        req.onsuccess = function () { resolve(req.result); };
        req.onerror = function () { resolve(null); };
      } catch (e) { resolve(null); }
    });
    return dbPromise;
  }
  function idb(mode, fn) {
    return db().then(function (d) {
      if (!d) return null;
      return new Promise(function (resolve) {
        try {
          var tx = d.transaction(DB_STORE, mode);
          var store = tx.objectStore(DB_STORE);
          var r = fn(store);
          tx.oncomplete = function () { resolve(r && r.result !== undefined ? r.result : r); };
          tx.onerror = function () { resolve(null); };
          tx.onabort = function () { resolve(null); };
        } catch (e) { resolve(null); }
      });
    });
  }
  function cachedTile(z, x, y) {
    var key = C.tileKey(z, x, y);
    if (state.tileCache[key]) return Promise.resolve(state.tileCache[key]);
    return idb('readonly', function (store) { return store.get(key); }).then(function (blob) {
      if (!blob) return null;
      if (typeof blob === 'string') { state.tileCache[key] = blob; return blob; }
      return new Promise(function (resolve) {
        var img = new Image();
        var url = URL.createObjectURL(blob);
        img.onload = function () { state.tileCache[key] = img; resolve(img); };
        img.onerror = function () { resolve(null); };
        img.src = url;
      });
    });
  }
  function storeTile(z, x, y, blob) {
    return idb('readwrite', function (store) { return store.put(blob, C.tileKey(z, x, y)); });
  }

  /* ---------- tile loading ---------- */
  function tileUrlFor(z, x, y) {
    return C.tileUrl(state.config.tileSource.template, z, x, y, 'a');
  }
  function tileAllowed() {
    return !!state.config.allowNet && C.validateTileTemplate(state.config.tileSource.template).ok;
  }
  function tileKeyFor(z, x, y) { return C.tileKey(z, x, y); }

  function enqueueTile(z, x, y) {
    var key = tileKeyFor(z, x, y);
    if (state.tileCache[key] || state.inflight[key]) return;
    var failedAt = state.failedAt[key] || 0;
    if (failedAt && Date.now() - failedAt < TILE_RETRY_MS) return;
    for (var i = 0; i < state.queue.length; i++) {
      if (state.queue[i].key === key) return;
    }
    state.queue.push({ z: z, x: x, y: y, key: key });
    pumpTileQueue();
  }

  function pumpTileQueue() {
    if (!tileAllowed()) { state.queue.length = 0; return; }
    while (state.activeFetches < MAX_PARALLEL_TILES && state.queue.length) {
      var job = state.queue.shift();
      if (state.tileCache[job.key] || state.inflight[job.key]) continue;
      state.activeFetches++;
      fetchTile(job).then(function () {
        state.activeFetches--;
        pumpTileQueue();
      });
    }
  }

  function fetchTile(job) {
    if (typeof fetch !== 'function') {
      state.tileStatus = { code: 'NETWORK', message: 'this engine has no fetch API; cached tiles only', at: Date.now() };
      return Promise.resolve(false);
    }
    var url = tileUrlFor(job.z, job.x, job.y);
    if (!url) {
      state.tileStatus = { code: 'INVALID_SOURCE', message: 'tile source is invalid', at: Date.now() };
      return Promise.resolve(false);
    }
    var controller = null, timer = null;
    var opts = { mode: 'cors', credentials: 'omit', cache: 'default' };
    try {
      if (typeof AbortController === 'function') { controller = new AbortController(); opts.signal = controller.signal; }
    } catch (e) { controller = null; }
    if (controller) timer = setTimeout(function () { try { controller.abort(); } catch (e) {} }, TILE_TIMEOUT_MS);

    if (state.inflight[job.key]) return state.inflight[job.key];
    var work = fetch(url, opts).then(function (res) {
      if (!res || !res.ok) {
        var err = new Error('HTTP ' + (res ? res.status : '0'));
        err.status = res ? res.status : 0;
        throw err;
      }
      return res.blob();
    }).then(function (blob) {
      if (!blob || !blob.size) throw new Error('empty tile response');
      return storeTile(job.z, job.x, job.y, blob).then(function () {
        return new Promise(function (resolve) {
          var img = new Image();
          var obj = URL.createObjectURL(blob);
          img.onload = function () { URL.revokeObjectURL(obj); state.tileCache[job.key] = img; resolve(true); };
          img.onerror = function () { URL.revokeObjectURL(obj); resolve(false); };
          img.src = obj;
        });
      });
    }).then(function (ok) {
      if (timer) clearTimeout(timer);
      if (ok) {
        delete state.failedAt[job.key];
        state.tileStatus = { code: 'LOADED', message: 'tiles loaded from the configured source', at: Date.now() };
        if (!logged.tileOk) { logged.tileOk = true; appLog('tile loaded ' + job.key + ' from configured source'); }
      } else {
        state.failedAt[job.key] = Date.now();
        state.tileStatus = { code: 'DECODE', message: 'tile response was not a decodable image', at: Date.now() };
      }
      requestDraw();
      return ok;
    }).catch(function (err) {
      if (timer) clearTimeout(timer);
      state.failedAt[job.key] = Date.now();
      state.tileStatus = Object.assign({ at: Date.now() }, C.describeTileFailure(err));
      if (!logged.tileError) {
        logged.tileError = true;
        appLog('tile failure ' + state.tileStatus.code + ': ' + state.tileStatus.message);
      }
      requestDraw();
      return false;
    }).then(function (ok) {
      delete state.inflight[job.key];
      return ok;
    });
    state.inflight[job.key] = work;
    return work;
  }

  function visibleTileRange() {
    var z = state.zoom, n = Math.pow(2, z);
    var tl = screenToLatLon(0, 0), br = screenToLatLon(viewWidth(), viewHeight());
    var x0 = Math.floor(lonToX(tl.lon, z)), x1 = Math.floor(lonToX(br.lon, z));
    var y0 = Math.max(0, Math.floor(latToY(tl.lat, z))), y1 = Math.min(n - 1, Math.floor(latToY(br.lat, z)));
    var list = [];
    for (var x = x0; x <= x1 && list.length < 64; x++) {
      for (var y = y0; y <= y1 && list.length < 64; y++) {
        list.push({ z: z, x: ((x % n) + n) % n, y: y });
      }
    }
    return list;
  }
  function requestVisibleTiles() {
    if (!tileAllowed()) return;
    visibleTileRange().forEach(function (t) { enqueueTile(t.z, t.x, t.y); });
  }

  /* ---------- drawing ---------- */
  var pendingDraw = false;
  function requestDraw() {
    if (pendingDraw) return;
    pendingDraw = true;
    (window.requestAnimationFrame || function (f) { setTimeout(f, 16); })(function () { pendingDraw = false; draw(); });
  }

  function drawGrid() {
    var stepDeg = state.zoom <= 3 ? 10 : state.zoom <= 6 ? 2 : state.zoom <= 9 ? 0.5 : 0.1;
    ctx.save();
    ctx.strokeStyle = 'rgba(74,222,128,0.16)';
    ctx.lineWidth = 1;
    ctx.font = '10px system-ui, sans-serif';
    ctx.fillStyle = 'rgba(143,179,164,0.65)';
    for (var lon = -180; lon <= 180; lon += stepDeg) {
      var p = worldToScreen(state.center.lat, lon);
      if (p.x >= -40 && p.x <= viewWidth() + 40) {
        ctx.beginPath(); ctx.moveTo(p.x, 0); ctx.lineTo(p.x, viewHeight()); ctx.stroke();
        ctx.fillText(lon.toFixed(0) + '°', p.x + 2, 12);
      }
    }
    for (var lat = -80; lat <= 80; lat += stepDeg) {
      var q = worldToScreen(lat, state.center.lon);
      if (q.y >= -20 && q.y <= viewHeight() + 20) {
        ctx.beginPath(); ctx.moveTo(0, q.y); ctx.lineTo(viewWidth(), q.y); ctx.stroke();
        ctx.fillText(lat.toFixed(0) + '°', 3, q.y - 3);
      }
    }
    ctx.restore();
  }

  function drawLabel(text, x, y, color) {
    if (!text) return;
    ctx.save();
    ctx.font = '11px system-ui, sans-serif';
    var w = ctx.measureText(text).width;
    var frame = C.labelFrame(x + 9, y - 8, viewWidth(), viewHeight(), w + 8, 16);
    ctx.fillStyle = 'rgba(13,27,22,0.82)';
    ctx.fillRect(frame.x, frame.y, frame.width, frame.height);
    ctx.fillStyle = color || '#e8f6ef';
    ctx.fillText(text, frame.x + 4, frame.y + 12);
    ctx.restore();
  }

  function drawMarker(lat, lon, kind, label) {
    var p = worldToScreen(lat, lon);
    if (p.x < -20 || p.x > viewWidth() + 20 || p.y < -20 || p.y > viewHeight() + 20) return;
    ctx.save();
    ctx.lineWidth = 1.5;
    if (kind === 'gps') {
      ctx.fillStyle = '#3fb950';
      ctx.strokeStyle = '#06140c';
      ctx.beginPath(); ctx.arc(p.x, p.y, 7, 0, Math.PI * 2); ctx.fill(); ctx.stroke();
      ctx.strokeStyle = 'rgba(63,185,80,0.55)';
      ctx.beginPath(); ctx.arc(p.x, p.y, 13, 0, Math.PI * 2); ctx.stroke();
    } else if (kind === 'stale-gps') {
      ctx.fillStyle = '#8b949e';
      ctx.strokeStyle = '#06140c';
      ctx.beginPath(); ctx.arc(p.x, p.y, 6, 0, Math.PI * 2); ctx.fill(); ctx.stroke();
    } else if (kind === 'search') {
      ctx.fillStyle = '#58a6ff';
      ctx.strokeStyle = '#04101f';
      ctx.beginPath();
      ctx.moveTo(p.x, p.y - 7); ctx.lineTo(p.x + 7, p.y); ctx.lineTo(p.x, p.y + 7); ctx.lineTo(p.x - 7, p.y); ctx.closePath();
      ctx.fill(); ctx.stroke();
    } else {
      ctx.fillStyle = '#ffd166';
      ctx.strokeStyle = '#123';
      ctx.beginPath(); ctx.arc(p.x, p.y, 6, 0, Math.PI * 2); ctx.fill(); ctx.stroke();
    }
    drawLabel(label, p.x, p.y, kind === 'search' ? '#c9e2ff' : '#e8f6ef');
    if (state.selected && kind !== 'gps' && Math.abs(state.selected.lat - lat) < 1e-9 && Math.abs(state.selected.lon - lon) < 1e-9) {
      ctx.strokeStyle = '#f0f6fc';
      ctx.lineWidth = 2;
      ctx.beginPath(); ctx.arc(p.x, p.y, 11, 0, Math.PI * 2); ctx.stroke();
    }
    ctx.restore();
  }

  function draw() {
    if (!ctx) {
      if (overlay) {
        overlay.textContent = 'No 2D canvas in this engine: the map canvas cannot be painted. ' +
          'Coordinates, search, pins, import/export and the tile cache still work.';
        overlay.classList.remove('hidden');
      }
      return;
    }
    var seq = ++state.renderSeq;
    var w = viewWidth(), h = viewHeight();
    ctx.clearRect(0, 0, w, h);
    ctx.fillStyle = '#0f2119';
    ctx.fillRect(0, 0, w, h);
    drawGrid();

    var drawn = 0, missing = 0, failed = 0;
    var z = state.zoom;
    var range = visibleTileRange();
    range.forEach(function (t) {
      cachedTile(t.z, t.x, t.y).then(function (img) {
        if (seq !== state.renderSeq) return; // never paint a reply for an older viewport
        if (img) {
          var p = worldToScreen(yToLat(t.y, t.z), xToLon(t.x, t.z));
          ctx.drawImage(img, p.x, p.y, tileSize(), tileSize());
        } else {
          requestDraw();
        }
      });
      var key = tileKeyFor(t.z, t.x, t.y);
      if (!state.tileCache[key]) {
        missing++;
        if (state.failedAt[key]) failed++;
        else if (tileAllowed()) enqueueTile(t.z, t.x, t.y);
      } else {
        drawn++;
      }
    });
    state.drawStats = { drawn: drawn, missing: missing, failed: failed };

    // Search results are transient and are never stored as pins.
    state.search.results.forEach(function (item) {
      drawMarker(item.lat, item.lon, 'search', item.label);
    });
    // Saved pins, de-duplicated for display only (user data is not destroyed).
    C.dedupePins(state.pins).forEach(function (pin) {
      drawMarker(pin.lat, pin.lon, 'pin', pin.label);
    });
    // Current position only when the provider returned real coordinates.
    if (state.provider && state.provider.fix) {
      drawMarker(state.provider.fix.lat, state.provider.fix.lon,
        state.provider.state === 'fixed' ? 'gps' : 'stale-gps',
        state.provider.state === 'fixed' ? 'provider position' : 'last provider position (stale)');
    }

    var a = screenToLatLon(w / 2, h / 2), b = screenToLatLon(w / 2 + 80, h / 2);
    var meters = haversine(a, b);
    if (scaleEl) {
      scaleEl.textContent = (meters > 1000 ? (meters / 1000).toFixed(1) + ' km' : Math.round(meters) + ' m') +
        '   z' + z + '   ' + state.center.lat.toFixed(3) + ', ' + state.center.lon.toFixed(3);
    }
    updateTileChrome();
  }

  function tileStatusText() {
    var src = C.tileSourceView(state.config, state.tileStatus);
    if (!src.configured) return { code: 'NO_SOURCE', text: 'no tile source configured', detail: 'Open Settings → Location & Maps or use the Maps tile controls to choose a source.' };
    if (!src.valid) return { code: 'INVALID_SOURCE', text: 'invalid tile source', detail: src.error };
    if (!state.config.allowNet) return { code: 'CACHED_ONLY', text: 'offline cache only', detail: 'Online tile downloads are off. Cached tiles are still shown.' };
    if (state.tileStatus.code === 'LOADED') return { code: 'ONLINE', text: 'OpenStreetMap tiles', detail: 'Visible tiles are loaded from the configured source.' };
    if (state.tileStatus.code === 'NETWORK' || state.tileStatus.code === 'TIMEOUT' || /^HTTP_/.test(state.tileStatus.code)) {
      return { code: 'ERROR', text: 'tile source error', detail: state.tileStatus.message };
    }
    if (state.tileStatus.code === 'DECODE') return { code: 'ERROR', text: 'invalid tile data', detail: state.tileStatus.message };
    return { code: 'LOADING', text: 'loading tiles', detail: 'Requesting only the tiles visible in this viewport.' };
  }

  function updateTileChrome() {
    var t = tileStatusText();
    if (badge) {
      badge.textContent = t.text;
      badge.classList.toggle('warn', t.code === 'NO_SOURCE' || t.code === 'INVALID_SOURCE' || t.code === 'ERROR');
    }
    if (attributionEl) {
      var src = state.config.tileSource;
      if (src.attribution) {
        attributionEl.innerHTML = src.attributionUrl
          ? 'Map data <a href="' + src.attributionUrl + '" target="_blank" rel="noopener">' + src.attribution + '</a>'
          : 'Map data ' + src.attribution;
        if (src.usagePolicyUrl) {
          attributionEl.innerHTML += ' · <a href="' + src.usagePolicyUrl + '" target="_blank" rel="noopener">usage policy</a>';
        }
      } else {
        attributionEl.textContent = 'No map data attribution configured.';
      }
    }
    if (overlay) {
      if (state.drawStats.drawn > 0) {
        overlay.textContent = '';
        overlay.classList.add('hidden');
      } else {
        var msg;
        if (!state.config.tileSource.template) msg = 'No tile source configured — showing the coordinate grid, saved pins and any offline tiles.';
        else if (!C.validateTileTemplate(state.config.tileSource.template).ok) msg = 'Tile source invalid: ' + C.validateTileTemplate(state.config.tileSource.template).error;
        else if (!state.config.allowNet) msg = 'Tile downloads are off — showing cached tiles only.';
        else if (t.code === 'ERROR') msg = t.detail + ' — cached tiles and the grid are still usable.';
        else msg = 'Loading tiles for this view…';
        overlay.textContent = msg;
        overlay.classList.remove('hidden');
      }
    }
  }

  /* ---------- interaction ---------- */
  function pointerPos(ev) {
    var r = canvas.getBoundingClientRect();
    var t = ev.touches ? ev.touches[0] : ev;
    return { x: t.clientX - r.left, y: t.clientY - r.top };
  }
  function panBy(dx, dy) {
    var z = state.zoom, T = tileSize();
    var cx = lonToX(state.center.lon, z) * T - dx;
    var cy = latToY(state.center.lat, z) * T - dy;
    state.center = { lat: yToLat(cy / T, z), lon: xToLon(cx / T, z) };
    clampView();
    requestDraw();
  }
  function selectAt(lat, lon, label) {
    var p = C.validLatLon(lat, lon);
    if (!p) return false;
    state.selected = { lat: p.lat, lon: p.lon, label: label || 'Selected point' };
    return true;
  }

  if (canvas) {
    canvas.addEventListener('pointerdown', function (ev) {
      canvas.setPointerCapture && canvas.setPointerCapture(ev.pointerId);
      state.dragging = { x: ev.clientX, y: ev.clientY, moved: false };
    });
    canvas.addEventListener('pointermove', function (ev) {
      if (!state.dragging) return;
      var dx = ev.clientX - state.dragging.x, dy = ev.clientY - state.dragging.y;
      if (Math.abs(dx) + Math.abs(dy) > 2) state.dragging.moved = true;
      panBy(dx, dy);
      state.dragging.x = ev.clientX; state.dragging.y = ev.clientY;
    });
    canvas.addEventListener('pointerup', function (ev) {
      var wasDrag = state.dragging && state.dragging.moved;
      state.dragging = null;
      if (!wasDrag) {
        var p = pointerPos(ev);
        var ll = screenToLatLon(p.x, p.y);
        selectAt(ll.lat, ll.lon, 'Selected point');
        requestDraw();
      }
      persistView();
    });
    canvas.addEventListener('pointercancel', function () { state.dragging = null; persistView(); });
    canvas.addEventListener('wheel', function (ev) {
      ev.preventDefault();
      state.zoom = Math.max(minZoom(), Math.min(maxZoom(), state.zoom + (ev.deltaY < 0 ? 1 : -1)));
      persistView(); requestDraw();
    }, { passive: false });

    var active = {};
    canvas.addEventListener('pointerdown', function (ev) { active[ev.pointerId] = pointerPos(ev); });
    canvas.addEventListener('pointermove', function (ev) {
      if (!(ev.pointerId in active)) return;
      active[ev.pointerId] = pointerPos(ev);
      var ids = Object.keys(active);
      if (ids.length === 2) {
        var d = Math.hypot(active[ids[0]].x - active[ids[1]].x, active[ids[0]].y - active[ids[1]].y);
        if (state.pinch) {
          var delta = d - state.pinch;
          if (Math.abs(delta) > 24) {
            state.zoom = Math.max(minZoom(), Math.min(maxZoom(), state.zoom + (delta > 0 ? 1 : -1)));
            state.pinch = d; persistView(); requestDraw();
          }
        } else state.pinch = d;
      }
    });
    canvas.addEventListener('pointerup', function (ev) {
      delete active[ev.pointerId];
      if (Object.keys(active).length < 2) state.pinch = null;
      persistView();
    });
  }

  function persistView() {
    save(K_VIEW, { lat: state.center.lat, lon: state.center.lon, zoom: state.zoom });
    requestDraw();
  }

  function resize() {
    if (!canvas) return;
    var dpr = window.devicePixelRatio || 1;
    var w = canvas.clientWidth || 360, h = canvas.clientHeight || 300;
    canvas.width = Math.round(w * dpr);
    canvas.height = Math.round(h * dpr);
    if (ctx && ctx.setTransform) ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    draw();
  }

  /* ---------- manual navigation / pins ---------- */
  function gotoLatLon(lat, lon, label) {
    var p = C.validLatLon(lat, lon);
    if (!p) { toast('Enter a valid latitude and longitude'); return false; }
    state.center = { lat: p.lat, lon: p.lon };
    state.selected = { lat: p.lat, lon: p.lon, label: label || 'Manual coordinate' };
    state.zoom = Math.max(state.zoom, 12);
    clampView(); persistView();
    toast('Moved to ' + p.lat.toFixed(4) + ', ' + p.lon.toFixed(4) + ' (manual coordinate, not a provider fix)');
    return true;
  }

  var gotoBtn = document.getElementById('do-goto');
  if (gotoBtn) gotoBtn.addEventListener('click', function () {
    gotoLatLon(parseFloat(document.getElementById('goto-lat').value), parseFloat(document.getElementById('goto-lon').value));
  });

  function addPinAt(lat, lon, label) {
    var p = C.validLatLon(lat, lon);
    if (!p) { toast('Select a map point or enter valid coordinates first'); return false; }
    var pin = {
      id: 'pin-' + Date.now() + '-' + Math.random().toString(36).slice(2, 6),
      lat: p.lat, lon: p.lon, label: (label || '').trim() || 'Pin', at: Date.now()
    };
    var result = C.addPin(state.pins, pin);
    if (!result.added) {
      toast(result.reason === 'duplicate' ? 'That pin already exists' : 'Invalid pin coordinates');
      return false;
    }
    state.pins = result.pins;
    save(K_PINS, state.pins);
    renderPins();
    requestDraw();
    toast('Pin saved at ' + p.lat.toFixed(5) + ', ' + p.lon.toFixed(5));
    return true;
  }

  var addPinBtn = document.getElementById('add-pin');
  if (addPinBtn) addPinBtn.addEventListener('click', function () {
    var labelEl = document.getElementById('marker-label');
    var label = labelEl ? labelEl.value : '';
    var target = state.selected || state.center;
    if (addPinAt(target.lat, target.lon, label) && labelEl) labelEl.value = '';
  });

  function renderPins(filter) {
    var list = document.getElementById('pins');
    if (!list) return;
    list.innerHTML = '';
    var q = (filter || '').trim().toLowerCase();
    var all = C.dedupePins(state.pins);
    var shown = all.filter(function (p) { return !q || (p.label || '').toLowerCase().indexOf(q) >= 0; });
    var count = document.getElementById('pin-count');
    if (count) count.textContent = all.length + ' saved' + (all.length !== state.pins.length ? ' (' + (state.pins.length - all.length) + ' duplicate hidden)' : '');
    if (!shown.length) {
      var li0 = document.createElement('li');
      li0.textContent = state.pins.length ? 'No pin matches that search.' : 'No saved pins yet. Select a point and add one.';
      list.appendChild(li0);
      return;
    }
    shown.forEach(function (p) {
      var li = document.createElement('li');
      var left = document.createElement('div');
      var name = document.createElement('div');
      name.textContent = p.label;
      var pos = document.createElement('div');
      pos.className = 'mono';
      pos.textContent = p.lat.toFixed(5) + ', ' + p.lon.toFixed(5) + '  ·  ' +
        (haversine(state.center, p) / 1000).toFixed(2) + ' km from view centre';
      left.appendChild(name); left.appendChild(pos);
      var actions = document.createElement('div');
      actions.className = 'row';
      var go = document.createElement('button');
      go.textContent = 'Go';
      go.addEventListener('click', function () {
        state.center = { lat: p.lat, lon: p.lon };
        state.zoom = Math.max(state.zoom, 12);
        selectAt(p.lat, p.lon, p.label);
        persistView(); renderPins(document.getElementById('search').value);
      });
      var del = document.createElement('button');
      del.textContent = 'Delete';
      del.addEventListener('click', function () {
        state.pins = state.pins.filter(function (x) { return x.id !== p.id && C.pinIdentity(x) !== C.pinIdentity(p); });
        save(K_PINS, state.pins);
        renderPins(document.getElementById('search').value); requestDraw();
      });
      actions.appendChild(go); actions.appendChild(del);
      li.appendChild(left); li.appendChild(actions);
      list.appendChild(li);
    });
  }

  function renderSearchResults() {
    var box = document.getElementById('search-results');
    if (!box) return;
    box.innerHTML = '';
    var s = state.search;
    if (s.status === 'loading') {
      var l = document.createElement('li'); l.textContent = 'Searching…'; box.appendChild(l); return;
    }
    if (s.status === 'error') {
      var e = document.createElement('li'); e.textContent = 'Search unavailable: ' + s.error; box.appendChild(e); return;
    }
    if (s.status === 'empty') {
      var z = document.createElement('li'); z.textContent = 'No places found for “' + s.query + '”.'; box.appendChild(z); return;
    }
    if (!s.results.length) return;
    s.results.forEach(function (r) {
      var li = document.createElement('li');
      var left = document.createElement('div');
      var name = document.createElement('div'); name.textContent = r.label;
      var pos = document.createElement('div'); pos.className = 'mono';
      pos.textContent = r.lat.toFixed(5) + ', ' + r.lon.toFixed(5);
      left.appendChild(name); left.appendChild(pos);
      var actions = document.createElement('div'); actions.className = 'row';
      var show = document.createElement('button'); show.textContent = 'Show';
      show.addEventListener('click', function () {
        state.center = { lat: r.lat, lon: r.lon };
        state.zoom = Math.max(state.zoom, 12);
        selectAt(r.lat, r.lon, r.label);
        persistView(); renderSearchResults(); renderPins(document.getElementById('search').value);
      });
      var pin = document.createElement('button'); pin.textContent = 'Save pin';
      pin.addEventListener('click', function () { addPinAt(r.lat, r.lon, r.label); });
      actions.appendChild(show); actions.appendChild(pin);
      li.appendChild(left); li.appendChild(actions);
      box.appendChild(li);
    });
  }

  var searchInput = document.getElementById('search');
  if (searchInput) searchInput.addEventListener('input', function (ev) { renderPins(ev.target.value); });

  /* ---------- export / import ---------- */
  var exportBtn = document.getElementById('export');
  if (exportBtn) exportBtn.addEventListener('click', function () {
    var text = JSON.stringify({ schema_version: 1, pins: state.pins, center: state.center, zoom: state.zoom }, null, 2);
    try {
      var blob = new Blob([text], { type: 'application/json' });
      var a = document.createElement('a');
      a.href = URL.createObjectURL(blob); a.download = 'nuxel-maps-places.json';
      document.body.appendChild(a); a.click();
      setTimeout(function () { URL.revokeObjectURL(a.href); a.remove(); }, 2000);
      toast('Exported ' + state.pins.length + ' places');
    } catch (e) { toast('Export unavailable in this view'); }
  });
  var importBtn = document.getElementById('import');
  var fileInput = document.getElementById('file');
  if (importBtn && fileInput) {
    importBtn.addEventListener('click', function () { fileInput.click(); });
    fileInput.addEventListener('change', function (ev) {
      var f = ev.target.files && ev.target.files[0];
      if (!f) return;
      var reader = new FileReader();
      reader.onload = function () {
        try {
          var incoming = JSON.parse(String(reader.result));
          var pins = Array.isArray(incoming) ? incoming : incoming.pins;
          if (!Array.isArray(pins)) throw new Error('no pin list found');
          var added = 0, skipped = 0;
          pins.forEach(function (p) {
            var r = C.addPin(state.pins, {
              id: 'pin-' + Date.now() + '-' + added,
              lat: p.lat, lon: p.lon, label: p.label || 'Imported pin', at: Date.now()
            });
            state.pins = r.pins;
            if (r.added) added++; else skipped++;
          });
          save(K_PINS, state.pins); renderPins(); requestDraw();
          toast('Imported ' + added + ' place(s)' + (skipped ? ', skipped ' + skipped + ' duplicate/invalid' : ''));
        } catch (e) { toast('Import failed: ' + e.message); }
        ev.target.value = '';
      };
      reader.readAsText(f);
    });
  }
  var clearBtn = document.getElementById('clear-pins');
  if (clearBtn) clearBtn.addEventListener('click', function () {
    state.pins = []; save(K_PINS, state.pins); renderPins(); requestDraw(); toast('All saved pins cleared');
  });

  /* ---------- tile source configuration ---------- */
  function applyConfig(next, message) {
    state.config = C.normalizeConfig(next);
    state.tileCache = {};
    state.failedAt = {};
    state.queue.length = 0;
    C.saveConfig(window.localStorage, state.config);
    syncConfigFields();
    requestDraw();
    if (message) toast(message);
  }
  function syncConfigFields() {
    var url = document.getElementById('tile-url');
    var net = document.getElementById('allow-net');
    if (url) url.value = state.config.tileSource.template;
    if (net) net.checked = !!state.config.allowNet;
  }
  var saveTileBtn = document.getElementById('save-tile');
  if (saveTileBtn) saveTileBtn.addEventListener('click', function () {
    var el = document.getElementById('tile-url');
    var t = el ? el.value.trim() : '';
    if (t) {
      var v = C.validateTileTemplate(t);
      if (!v.ok) { toast('Tile source invalid: ' + v.error); return; }
    }
    var next = C.clone(state.config);
    next.tileSource.template = t;
    next.tileSource.name = t ? 'Custom tile source' : 'No tile source';
    if (t && /openstreetmap\.org/i.test(t)) {
      next.tileSource.attribution = C.DEFAULT_TILE_SOURCE.attribution;
      next.tileSource.attributionUrl = C.DEFAULT_TILE_SOURCE.attributionUrl;
      next.tileSource.usagePolicyUrl = C.DEFAULT_TILE_SOURCE.usagePolicyUrl;
      next.tileSource.requiresAttribution = true;
    }
    applyConfig(next, t ? 'Tile source saved' : 'Tile source cleared — offline grid only');
  });
  var presetBtn = document.getElementById('osm-preset');
  if (presetBtn) presetBtn.addEventListener('click', function () {
    var next = C.clone(state.config);
    next.tileSource = C.clone(C.DEFAULT_TILE_SOURCE);
    next.allowNet = true;
    applyConfig(next, 'OpenStreetMap standard tiles enabled — visible tiles only');
    requestVisibleTiles();
  });
  var netToggle = document.getElementById('allow-net');
  if (netToggle) netToggle.addEventListener('change', function (ev) {
    var next = C.clone(state.config);
    next.allowNet = !!ev.target.checked;
    applyConfig(next, next.allowNet ? 'Online tile downloads enabled' : 'Online tile downloads off — cached tiles only');
    if (next.allowNet) requestVisibleTiles();
  });

  function cacheVisible() {
    if (!state.config.tileSource.template) { toast('Set a tile source first'); return; }
    if (!C.validateTileTemplate(state.config.tileSource.template).ok) { toast('Tile source is invalid'); return; }
    if (!state.config.allowNet) { toast('Enable online tile downloads first'); return; }
    var list = visibleTileRange(), before = 0, after = 0;
    Promise.all(list.map(function (t) {
      var key = tileKeyFor(t.z, t.x, t.y);
      if (state.tileCache[key]) { before++; return Promise.resolve(true); }
      return fetchTile({ z: t.z, x: t.x, y: t.y, key: key }).then(function (ok) { if (ok) after++; return ok; });
    })).then(function () {
      state.renderSeq++;
      requestDraw();
      if (cacheReport) {
        cacheReport.textContent = 'Visible tiles: ' + list.length + ' requested; ' + before + ' already cached; ' +
          after + ' fetched now.' + (state.tileStatus.code !== 'LOADED' && state.tileStatus.code !== 'IDLE'
            ? '\nLast tile error: ' + state.tileStatus.message : '') +
          '\nOnly the current viewport was requested; nothing was prefetched.';
      }
    });
  }
  var cacheHere = document.getElementById('cache-here');
  if (cacheHere) cacheHere.addEventListener('click', cacheVisible);
  var cacheStats = document.getElementById('cache-stats');
  if (cacheStats) cacheStats.addEventListener('click', function () {
    idb('readonly', function (store) { return store.count(); }).then(function (n) {
      var src = C.tileSourceView(state.config, state.tileStatus);
      if (cacheReport) {
        cacheReport.textContent =
          'Tile cache: ' + (n === null ? 'unavailable (IndexedDB denied)' : n + ' tiles in IndexedDB') + '\n' +
          'Decoded this session: ' + Object.keys(state.tileCache).length + '\n' +
          'Source: ' + (src.name || 'none') + ' (' + (src.valid ? 'valid' : src.error || 'not configured') + ')\n' +
          'Online: ' + (state.config.allowNet ? 'enabled' : 'off') + ' | status: ' + src.status + '\n' +
          'Attribution: ' + (src.attribution || 'none');
      }
    });
  });
  var cacheClear = document.getElementById('cache-clear');
  if (cacheClear) cacheClear.addEventListener('click', function () {
    idb('readwrite', function (store) { return store.clear(); }).then(function () {
      state.tileCache = {}; state.failedAt = {}; state.renderSeq++; requestDraw();
      if (cacheReport) cacheReport.textContent = 'Tile cache emptied. Saved pins were not touched.';
    });
  });

  var zoomIn = document.getElementById('zoom-in');
  if (zoomIn) zoomIn.addEventListener('click', function () {
    state.zoom = Math.min(maxZoom(), state.zoom + 1); persistView(); requestVisibleTiles();
  });
  var zoomOut = document.getElementById('zoom-out');
  if (zoomOut) zoomOut.addEventListener('click', function () {
    state.zoom = Math.max(minZoom(), state.zoom - 1); persistView(); requestVisibleTiles();
  });
  var locateBtn = document.getElementById('locate');
  if (locateBtn) locateBtn.addEventListener('click', function () { refreshProvider(true); });

  /* ---------- place search (Nominatim, one explicit action) ---------- */
  var activeSearchController = null;
  function searchPlaces(query) {
    var q = String(query || '').trim();
    if (!q) return;
    if (typeof fetch !== 'function') { toast('Place search unavailable: this engine has no fetch API'); return; }
    if (q.length < 3) { toast('Type at least 3 characters to search places'); return; }
    if (q === state.lastQuery && Date.now() - state.lastQueryAt < SEARCH_REPEAT_MS &&
        (state.search.status === 'ok' || state.search.status === 'empty' || state.search.status === 'loading')) {
      renderSearchResults();
      toast('Showing the current results for “' + q + '”');
      return;
    }
    state.lastQuery = q; state.lastQueryAt = Date.now();
    var seq = C.beginSearch(state.search, q);
    if (activeSearchController) { try { activeSearchController.abort(); } catch (e) {} }
    activeSearchController = null;
    renderSearchResults();
    var url = state.config.geocoder.url + '?format=jsonv2&limit=' + (state.config.geocoder.limit || 6) +
      '&accept-language=en&q=' + encodeURIComponent(q);
    var opts = { mode: 'cors', credentials: 'omit', referrerPolicy: 'strict-origin-when-cross-origin',
      headers: { 'Accept': 'application/json' } };
    var timer = null;
    try {
      if (typeof AbortController === 'function') {
        activeSearchController = new AbortController();
        opts.signal = activeSearchController.signal;
        timer = setTimeout(function () { try { activeSearchController.abort(); } catch (e) {} }, SEARCH_TIMEOUT_MS);
      }
    } catch (e) { activeSearchController = null; }
    fetch(url, opts).then(function (r) {
      if (!r || !r.ok) throw new Error('Nominatim HTTP ' + (r ? r.status : '0'));
      return r.json();
    }).then(function (results) {
      if (timer) clearTimeout(timer);
      var accepted = C.acceptSearch(state.search, seq, results);
      if (!accepted.accepted) return; // a newer query already owns the panel
      appLog('search results=' + accepted.results.length + ' (transient, not a provider fix)');
      renderSearchResults();
      if (accepted.results.length) {
        var first = accepted.results[0];
        state.center = { lat: first.lat, lon: first.lon };
        state.zoom = Math.max(state.zoom, 12);
        selectAt(first.lat, first.lon, first.label);
        persistView();
        toast('Found ' + accepted.results.length + ' place(s) — search results are not provider positions');
      } else {
        toast('No places found for “' + q + '”');
      }
    }).catch(function (err) {
      if (timer) clearTimeout(timer);
      if (err && err.name === 'AbortError') return;
      var failed = C.failSearch(state.search, seq, err);
      if (failed.accepted) { renderSearchResults(); toast('Place search unavailable: ' + state.search.error); }
    });
  }
  var searchPanel = document.getElementById('search-panel');
  if (searchPanel) searchPanel.addEventListener('click', function () { searchPlaces(document.getElementById('search').value); });
  if (searchInput) searchInput.addEventListener('keydown', function (ev) {
    if (ev.key === 'Enter') { ev.preventDefault(); searchPlaces(ev.target.value); }
  });

  /* ---------- canonical location provider ---------- */
  function bridge() {
    if (window.NuxelBridge && window.NuxelBridge.call) return window.NuxelBridge;
    try { if (window.parent && window.parent.NuxelBridge) return window.parent.NuxelBridge; } catch (e) {}
    return null;
  }
  function updateProviderChrome() {
    var p = state.provider;
    var line = document.getElementById('provider-state');
    if (line) line.textContent = C.providerSummary(p, Date.now() / 1000);
    if (p.state === 'fixed' && p.fix) {
      var count = 0; // no fabricated satellite count
      void count;
    }
  }
  function applyProviderStatus(raw) {
    state.providerRaw = raw;
    state.providerCheckedAt = Date.now();
    state.provider = C.providerView(raw, Date.now() / 1000);
    if (logged.provider !== state.provider.state) {
      logged.provider = state.provider.state;
      appLog('provider state=' + state.provider.state + ' ready=' + state.provider.providerReady +
        ' available=' + state.provider.providerAvailable +
        (state.provider.detail ? (' detail=' + state.provider.detail) : ''));
    }
    updateProviderChrome();
    requestDraw();
  }
  var providerBridgeTries = 0;
  function refreshProvider(requestAcquisition) {
    var b = bridge();
    if (!b) {
      // The shared bridge is an ES module and is evaluated after this classic
      // script.  Wait briefly for the global instead of reporting a false
      // "unavailable" during that startup window.
      if (providerBridgeTries < 12) {
        providerBridgeTries++;
        setTimeout(function () { refreshProvider(requestAcquisition); }, 300);
        return Promise.resolve(state.provider);
      }
      applyProviderStatus({ enabled: false, state: 'unavailable', detail: 'Nuxel bridge is not available in this view' });
      return Promise.resolve(state.provider);
    }
    providerBridgeTries = 0;
    var action;
    if (requestAcquisition) {
      action = Promise.resolve(b.call('location', 'acquire', {})).then(function (res) {
        if (!res || res.error_code !== 'CAPABILITY_DENIED') return res;
        return Promise.resolve(
          b.requestCapability ? b.requestCapability('location:read', 'Show the current map position')
                              : true
        ).then(function (grant) {
          if (grant === false || (grant && grant.granted === false)) {
            throw new Error('Location read permission denied');
          }
          return b.call('location', 'acquire', {});
        });
      });
    } else {
      action = b.call('location', 'get-status', {});
    }
    return Promise.resolve(action).then(function (res) {
      if (res && res.success === false && !res.state) {
        applyProviderStatus({ enabled: !!res.enabled, state: 'error', last_error: res.error || 'location provider error' });
        return state.provider;
      }
      applyProviderStatus(res || { enabled: false, state: 'unavailable' });
      if (requestAcquisition && state.provider.state === 'fixed' && state.provider.fix) {
        state.center = { lat: state.provider.fix.lat, lon: state.provider.fix.lon };
        state.zoom = Math.max(state.zoom, 16);
        persistView();
        toast('Centred on the current provider position');
      } else if (requestAcquisition && state.provider.fix) {
        toast('Provider has a stale fix; not treating it as current');
      } else if (requestAcquisition) {
        toast('No provider fix: ' + C.providerSummary(state.provider, Date.now() / 1000));
      }
      return state.provider;
    }, function (e) {
      applyProviderStatus({ enabled: false, state: 'error', last_error: String(e && e.message || e) });
      return state.provider;
    });
  }

  /* ---------- boot ---------- */
  window.addEventListener('resize', resize);
  appLog('boot tileSource=' + (state.config.tileSource.id || 'custom') +
    ' valid=' + C.validateTileTemplate(state.config.tileSource.template).ok +
    ' online=' + !!state.config.allowNet);
  resize();
  renderPins();
  renderSearchResults();
  syncConfigFields();
  updateTileChrome();
  updateProviderChrome();
  requestVisibleTiles();
  refreshProvider(false);

  // headless smoke-test hook
  window.nuxelMaps = {
    core: C,
    state: state,
    haversine: haversine,
    lonToX: lonToX,
    latToY: latToY,
    xToLon: xToLon,
    yToLat: yToLat,
    screenToLatLon: screenToLatLon,
    tileKey: tileKeyFor,
    draw: draw,
    canvas: function () { return !!ctx; },
    providerView: function (raw) { return C.providerView(raw, Date.now() / 1000); },
    addPinAt: addPinAt,
    gotoLatLon: gotoLatLon,
    refreshProvider: refreshProvider,
    searchPlaces: searchPlaces
  };
})();
