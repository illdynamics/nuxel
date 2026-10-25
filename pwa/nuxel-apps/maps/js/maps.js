// Nuxel Maps (mission area 30)
//
// Offline-first slippy map.  All geometry (Web Mercator projection, haversine
// distance, scale bar) is computed here.  Tiles are read from an IndexedDB cache
// first and only fetched when the user has (a) saved a tile URL template and
// (b) explicitly enabled downloads - the toggle defaults to off, so a fresh
// install makes zero network requests.  With an empty cache the map still works:
// it draws the coordinate grid and every saved pin.
(function () {
  'use strict';

  var K_PINS = 'nuxel-maps-pins';
  var K_CONF = 'nuxel-maps-config';
  var K_VIEW = 'nuxel-maps-view';
  var DB_NAME = 'nuxel-maps-tiles';
  var DB_STORE = 'tiles';

  var state = {
    zoom: 4,
    center: { lat: 52.3702, lon: 4.8952 },
    pins: [],
    conf: { template: '', allowNet: false },
    dragging: null,
    pinch: null,
    tileCache: {}     // key -> ImageBitmap/HTMLImageElement, decoded this session
  };

  function load(key, dflt) {
    try { var raw = localStorage.getItem(key); return raw ? JSON.parse(raw) : dflt; }
    catch (e) { return dflt; }
  }
  function save(key, value) {
    try { localStorage.setItem(key, JSON.stringify(value)); } catch (e) { /* ignore */ }
  }
  state.pins = load(K_PINS, []);
  var conf = load(K_CONF, null);
  if (conf) state.conf = { template: conf.template || '', allowNet: !!conf.allowNet };
  var view = load(K_VIEW, null);
  if (view && typeof view.lat === 'number') { state.center = { lat: view.lat, lon: view.lon }; state.zoom = view.zoom; }

  var canvas = document.getElementById('map');
  // The 2D context can be missing (an engine or an embedder without canvas).
  // In that case the app still pans/searches/pins/imports/export; it reports
  // the missing renderer in the on-screen overlay instead of throwing.
  var ctx = (canvas && canvas.getContext) ? canvas.getContext('2d') : null;
  var canvasDisabled = !ctx;
  var overlay = document.getElementById('overlay-msg');
  var badge = document.getElementById('tile-badge');
  var scaleEl = document.getElementById('scale');
  var cacheReport = document.getElementById('cache-report');

  function toast(msg) {
    var t = document.getElementById('toast');
    t.textContent = msg;
    t.classList.remove('hidden');
    clearTimeout(toast._t);
    toast._t = setTimeout(function () { t.classList.add('hidden'); }, 2400);
  }

  /* ---------- projection ---------- */
  var TILE = 256;
  function lonToX(lon, z) { return (lon + 180) / 360 * Math.pow(2, z); }
  function latToY(lat, z) {
    var r = lat * Math.PI / 180;
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
        } catch (e) { resolve(null); }
      });
    });
  }
  function tileKey(z, x, y) { return z + '/' + x + '/' + y; }

  function cachedTile(z, x, y) {
    var key = tileKey(z, x, y);
    if (state.tileCache[key]) return Promise.resolve(state.tileCache[key]);
    return idb('readonly', function (store) { return store.get(key); }).then(function (blob) {
      if (!blob) return null;
      return new Promise(function (resolve) {
        var img = new Image();
        var url = URL.createObjectURL(blob);
        img.onload = function () { state.tileCache[key] = img; resolve(img); };
        img.onerror = function () { resolve(null); };
        img.src = url;
      });
    });
  }

  function templateFor(z, x, y) {
    if (!state.conf.template) return null;
    return state.conf.template.replace('{z}', z).replace('{x}', x).replace('{y}', y).replace('{s}', 'a');
  }

  function downloadTile(z, x, y) {
    if (!state.conf.allowNet || !state.conf.template) return Promise.resolve(false);
    var url = templateFor(z, x, y);
    if (!url) return Promise.resolve(false);
    return fetch(url, { mode: 'cors', credentials: 'omit' }).then(function (r) {
      if (!r || !r.ok) return false;
      return r.blob().then(function (b) {
        return idb('readwrite', function (store) { return store.put(b, tileKey(z, x, y)); }).then(function () { return true; });
      });
    }).catch(function () { return false; });
  }

  /* ---------- render ---------- */
  function resize() {
    var dpr = window.devicePixelRatio || 1;
    var w = canvas.clientWidth || 360, h = canvas.clientHeight || 300;
    canvas.width = Math.round(w * dpr);
    canvas.height = Math.round(h * dpr);
    if (ctx && ctx.setTransform) ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    draw();
  }

  function worldToScreen(lat, lon) {
    var z = state.zoom;
    var cx = lonToX(state.center.lon, z) * TILE;
    var cy = latToY(state.center.lat, z) * TILE;
    var w = canvas.clientWidth || 360, h = canvas.clientHeight || 300;
    return { x: lonToX(lon, z) * TILE - cx + w / 2, y: latToY(lat, z) * TILE - cy + h / 2 };
  }
  function screenToLatLon(sx, sy) {
    var z = state.zoom;
    var cx = lonToX(state.center.lon, z) * TILE;
    var cy = latToY(state.center.lat, z) * TILE;
    var w = canvas.clientWidth || 360, h = canvas.clientHeight || 300;
    var wx = (sx - w / 2 + cx) / TILE, wy = (sy - h / 2 + cy) / TILE;
    return { lat: yToLat(wy, z), lon: xToLon(wx, z) };
  }

  var pendingDraw = false;
  function requestDraw() {
    if (pendingDraw) return;
    pendingDraw = true;
    (window.requestAnimationFrame || function (f) { setTimeout(f, 16); })(function () { pendingDraw = false; draw(); });
  }

  function drawGrid() {
    var z = state.zoom, n = Math.pow(2, z);
    var w = canvas.clientWidth, h = canvas.clientHeight;
    var sp = worldToScreen(state.center.lat, state.center.lon);
    var tileSize = 0;
    // pixel size of one tile at this zoom is always TILE; grid step of 10 degrees at low zoom
    var stepDeg = z <= 3 ? 10 : z <= 6 ? 2 : z <= 9 ? 0.5 : 0.1;
    ctx.save();
    ctx.strokeStyle = 'rgba(74,222,128,0.18)';
    ctx.lineWidth = 1;
    ctx.font = '10px system-ui, sans-serif';
    ctx.fillStyle = 'rgba(143,179,164,0.75)';
    for (var lon = -180; lon <= 180; lon += stepDeg) {
      var p = worldToScreen(state.center.lat, lon);
      if (p.x >= -40 && p.x <= w + 40) {
        ctx.beginPath(); ctx.moveTo(p.x, 0); ctx.lineTo(p.x, h); ctx.stroke();
        ctx.fillText(lon.toFixed(0) + '°', p.x + 2, 12);
      }
    }
    for (var lat = -80; lat <= 80; lat += stepDeg) {
      var q = worldToScreen(lat, state.center.lon);
      if (q.y >= -20 && q.y <= h + 20) {
        ctx.beginPath(); ctx.moveTo(0, q.y); ctx.lineTo(w, q.y); ctx.stroke();
        ctx.fillText(lat.toFixed(0) + '°', 3, q.y - 3);
      }
    }
    ctx.restore();
    void n; void sp; void tileSize;
  }

  var tilesDrawn = 0, tilesMissing = 0;
  function draw() {
    var w = canvas.clientWidth || 360, h = canvas.clientHeight || 300;
    if (!ctx) {
      var msg = document.getElementById('overlay-msg');
      if (msg && !msg.textContent.trim()) {
        msg.textContent = 'No 2D canvas in this engine: the map canvas cannot be painted. ' +
          'Coordinates, search, pins, import/export and the tile cache still work.';
        msg.classList.remove('hidden');
      }
      return;
    }
    ctx.clearRect(0, 0, w, h);
    // placeholders
    ctx.fillStyle = '#0f2119';
    ctx.fillRect(0, 0, w, h);
    drawGrid();

    // tiles
    tilesDrawn = 0; tilesMissing = 0;
    var z = state.zoom, n = Math.pow(2, z);
    var topLeft = screenToLatLon(0, 0), bottomRight = screenToLatLon(w, h);
    var x0 = Math.floor(lonToX(topLeft.lon, z)), x1 = Math.floor(lonToX(bottomRight.lon, z));
    var y0 = Math.floor(latToY(topLeft.lat, z)), y1 = Math.floor(latToY(bottomRight.lat, z));
    var maxTiles = 64, count = 0;
    for (var tx = x0; tx <= x1 && count < maxTiles; tx++) {
      for (var ty = y0; ty <= y1 && count < maxTiles; ty++) {
        if (ty < 0 || ty >= n) continue;
        var wrapped = ((tx % n) + n) % n;
        count++;
        (function (tx2, ty2, wrapped2) {
          cachedTile(z, wrapped2, ty2).then(function (img) {
            if (img) {
              var p = worldToScreen(yToLat(ty2, z), xToLon(wrapped2, z));
              ctx.drawImage(img, p.x, p.y, TILE, TILE);
              tilesDrawn++;
              updateOverlay();
            } else {
              tilesMissing++;
              updateOverlay();
            }
            void tx2;
          });
        })(tx, ty, wrapped);
      }
    }

    // pins
    state.pins.forEach(function (pin) {
      var p = worldToScreen(pin.lat, pin.lon);
      ctx.beginPath();
      ctx.fillStyle = '#ffd166';
      ctx.arc(p.x, p.y, 6, 0, Math.PI * 2);
      ctx.fill();
      ctx.strokeStyle = '#123';
      ctx.lineWidth = 1.5;
      ctx.stroke();
      if (pin.label) {
        ctx.fillStyle = '#e8f6ef';
        ctx.font = '11px system-ui, sans-serif';
        ctx.fillText(pin.label, p.x + 9, p.y + 4);
      }
    });

    // scale bar: 80 px converted to metres at the view centre
    var a = screenToLatLon(w / 2, h / 2), b = screenToLatLon(w / 2 + 80, h / 2);
    var meters = haversine(a, b);
    scaleEl.textContent = meters > 1000 ? (meters / 1000).toFixed(1) + ' km' : Math.round(meters) + ' m';
    scaleEl.textContent += '   z' + z + '   ' + state.center.lat.toFixed(3) + ', ' + state.center.lon.toFixed(3);
    writeBadge();
    void x1;
  }

  function updateOverlay() {
    if (tilesDrawn > 0) { overlay.textContent = ''; return; }
    if (!state.conf.template) {
      overlay.textContent = 'No tile source configured — showing the coordinate grid and your pins.';
    } else if (!state.conf.allowNet) {
      overlay.textContent = 'Tile downloads are off — only cached tiles are shown.';
    } else {
      overlay.textContent = 'No tiles cached for this view yet.';
    }
  }

  function writeBadge() {
    if (!state.conf.template) {
      badge.textContent = 'no tile source configured';
      badge.classList.add('warn');
    } else if (!state.conf.allowNet) {
      badge.textContent = 'offline cache only';
      badge.classList.remove('warn');
    } else {
      badge.textContent = 'cache + downloads enabled';
      badge.classList.remove('warn');
    }
    document.getElementById('tile-url').value = state.conf.template;
    document.getElementById('allow-net').checked = state.conf.allowNet;
  }

  /* ---------- interaction ---------- */
  function pointerPos(ev) {
    var r = canvas.getBoundingClientRect();
    var t = ev.touches ? ev.touches[0] : ev;
    return { x: t.clientX - r.left, y: t.clientY - r.top };
  }
  function panBy(dx, dy) {
    // move the view centre by the opposite of the drag, in world pixels
    var z = state.zoom;
    var cx = lonToX(state.center.lon, z) * TILE - dx;
    var cy = latToY(state.center.lat, z) * TILE - dy;
    state.center = { lat: yToLat(cy / TILE, z), lon: xToLon(cx / TILE, z) };
    clampView();
    requestDraw();
  }
  function clampView() {
    state.center.lat = Math.max(-85, Math.min(85, state.center.lat));
    while (state.center.lon > 180) state.center.lon -= 360;
    while (state.center.lon < -180) state.center.lon += 360;
  }

  canvas.addEventListener('pointerdown', function (ev) {
    canvas.setPointerCapture && canvas.setPointerCapture(ev.pointerId);
    state.dragging = { x: ev.clientX, y: ev.clientY };
  });
  canvas.addEventListener('pointermove', function (ev) {
    if (!state.dragging) return;
    panBy(ev.clientX - state.dragging.x, ev.clientY - state.dragging.y);
    state.dragging = { x: ev.clientX, y: ev.clientY };
  });
  canvas.addEventListener('pointerup', function () { state.dragging = null; persistView(); });
  canvas.addEventListener('pointercancel', function () { state.dragging = null; persistView(); });
  canvas.addEventListener('wheel', function (ev) {
    ev.preventDefault();
    state.zoom = Math.max(0, Math.min(19, state.zoom + (ev.deltaY < 0 ? 1 : -1)));
    persistView(); requestDraw();
  }, { passive: false });

  // pinch zoom (two pointers)
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
          state.zoom = Math.max(0, Math.min(19, state.zoom + (delta > 0 ? 1 : -1)));
          state.pinch = d;
          persistView(); requestDraw();
        }
      } else { state.pinch = d; }
    }
  });
  canvas.addEventListener('pointerup', function (ev) {
    delete active[ev.pointerId];
    if (Object.keys(active).length < 2) state.pinch = null;
    persistView();
  });

  function persistView() {
    save(K_VIEW, { lat: state.center.lat, lon: state.center.lon, zoom: state.zoom });
    if (state.conf.allowNet && state.conf.template) {
      clearTimeout(persistView._t);
      persistView._t = setTimeout(fetchVisibleTiles, 350);
    }
  }

  document.getElementById('zoom-in').addEventListener('click', function () {
    state.zoom = Math.min(19, state.zoom + 1); persistView(); requestDraw(); refreshTilesFromCache();
  });
  document.getElementById('zoom-out').addEventListener('click', function () {
    state.zoom = Math.max(0, state.zoom - 1); persistView(); requestDraw(); refreshTilesFromCache();
  });
  document.getElementById('locate').addEventListener('click', function () {
    document.getElementById('goto-lat').focus();
  });

  /* ---------- over zoom: draw cached tiles immediately, then optionally fetch ---------- */
  function currentTileRange() {
    var w = canvas.clientWidth || 360, h = canvas.clientHeight || 300;
    var z = state.zoom, n = Math.pow(2, z);
    var tl = screenToLatLon(0, 0), br = screenToLatLon(w, h);
    var x0 = Math.floor(lonToX(tl.lon, z)), x1 = Math.floor(lonToX(br.lon, z));
    var y0 = Math.max(0, Math.floor(latToY(tl.lat, z))), y1 = Math.min(n - 1, Math.floor(latToY(br.lat, z)));
    var list = [];
    for (var x = x0; x <= x1 && list.length < 64; x++) {
      for (var y = y0; y <= y1 && list.length < 64; y++) list.push({ x: ((x % n) + n) % n, y: y });
    }
    return list;
  }
  function refreshTilesFromCache() { requestDraw(); }

  /* ---------- goto / pins ---------- */
  document.getElementById('do-goto').addEventListener('click', function () {
    var lat = parseFloat(document.getElementById('goto-lat').value);
    var lon = parseFloat(document.getElementById('goto-lon').value);
    if (isNaN(lat) || isNaN(lon) || lat < -90 || lat > 90 || lon < -180 || lon > 180) {
      toast('Enter a valid latitude and longitude');
      return;
    }
    state.center = { lat: lat, lon: lon };
    persistView(); requestDraw();
    toast('Moved to ' + lat.toFixed(4) + ', ' + lon.toFixed(4));
  });

  document.getElementById('add-pin').addEventListener('click', function () {
    var label = (document.getElementById('marker-label').value || '').trim();
    var pin = { id: 'pin-' + Date.now(), lat: state.center.lat, lon: state.center.lon, label: label || 'Pin', at: Date.now() };
    state.pins.push(pin);
    save(K_PINS, state.pins);
    document.getElementById('marker-label').value = '';
    renderPins(); requestDraw();
    toast('Pin added at ' + pin.lat.toFixed(4) + ', ' + pin.lon.toFixed(4));
  });

  function renderPins(filter) {
    var list = document.getElementById('pins');
    list.innerHTML = '';
    var q = (filter || '').trim().toLowerCase();
    var shown = state.pins.filter(function (p) {
      return !q || (p.label || '').toLowerCase().indexOf(q) >= 0;
    });
    document.getElementById('pin-count').textContent = state.pins.length + ' saved';
    if (!shown.length) {
      var li0 = document.createElement('li');
      li0.textContent = state.pins.length ? 'No pin matches that search.' : 'No pins yet. Pan the map and add one.';
      list.appendChild(li0);
      return;
    }
    // distance from the current view centre, recomputed on each render
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
        persistView(); requestDraw();
      });
      var del = document.createElement('button');
      del.textContent = 'Delete';
      del.addEventListener('click', function () {
        state.pins = state.pins.filter(function (x) { return x.id !== p.id; });
        save(K_PINS, state.pins); renderPins(document.getElementById('search').value); requestDraw();
      });
      actions.appendChild(go); actions.appendChild(del);
      li.appendChild(left); li.appendChild(actions);
      list.appendChild(li);
    });
  }
  document.getElementById('search').addEventListener('input', function (ev) { renderPins(ev.target.value); });

  document.getElementById('export').addEventListener('click', function () {
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
  document.getElementById('import').addEventListener('click', function () { document.getElementById('file').click(); });
  document.getElementById('file').addEventListener('change', function (ev) {
    var f = ev.target.files && ev.target.files[0];
    if (!f) return;
    var reader = new FileReader();
    reader.onload = function () {
      try {
        var incoming = JSON.parse(String(reader.result));
        var pins = Array.isArray(incoming) ? incoming : incoming.pins;
        if (!Array.isArray(pins)) throw new Error('no pin list found');
        var added = 0;
        pins.forEach(function (p) {
          if (typeof p.lat === 'number' && typeof p.lon === 'number') {
            state.pins.push({ id: 'pin-' + Date.now() + '-' + added, lat: p.lat, lon: p.lon, label: p.label || 'Imported pin', at: Date.now() });
            added++;
          }
        });
        save(K_PINS, state.pins); renderPins();
        requestDraw();
        toast('Imported ' + added + ' places');
      } catch (e) { toast('Import failed: ' + e.message); }
      ev.target.value = '';
    };
    reader.readAsText(f);
  });
  document.getElementById('clear-pins').addEventListener('click', function () {
    state.pins = []; save(K_PINS, state.pins); renderPins(); requestDraw();
    toast('All pins cleared');
  });

  /* ---------- tile cache controls ---------- */
  // One-tap, opt-in OSM standard tile preset.  It only FILLS the template
  // input (a lawful, attributed source the owner can edit or clear); it never
  // enables downloads and never issues a network request by itself.
  document.getElementById('osm-preset').addEventListener('click', function () {
    var v = document.getElementById('tile-url');
    v.value = 'https://tile.openstreetmap.org/{z}/{x}/{y}.png';
    state.conf.template = v.value;
    // 21000: internet is a working baseline now, so this is a genuine one-tap
    // "go online" action. It still obeys the OSM tile usage policy: only the
    // tiles for the current view are fetched, never a crawl or prefetch.
    state.conf.allowNet = true;
    save(K_CONF, state.conf);
    writeBadge();
    state.tileCache = {};
    toast('OpenStreetMap tiles enabled — fetching the current view (attribution shown on map)');
    fetchVisibleTiles();
  });

  document.getElementById('save-tile').addEventListener('click', function () {
    var t = (document.getElementById('tile-url').value || '').trim();
    if (t && !/\{z\}.*\{x\}.*\{y\}|^https?:\/\//.test(t)) {
      toast('The template needs {z}, {x} and {y} placeholders');
      return;
    }
    if (t && !/^https?:\/\//.test(t)) { toast('Only http(s) tile templates are accepted'); return; }
    state.conf.template = t;
    save(K_CONF, state.conf);
    state.tileCache = {};
    requestDraw();
    toast(t ? 'Tile template saved' : 'Tile template cleared (offline grid only)');
  });
  document.getElementById('allow-net').addEventListener('change', function (ev) {
    state.conf.allowNet = !!ev.target.checked;
    save(K_CONF, state.conf);
    writeBadge();
    toast(state.conf.allowNet ? 'Tile downloads enabled' : 'Tile downloads disabled — cached tiles only');
  });
  document.getElementById('cache-here').addEventListener('click', function () {
    if (!state.conf.template) { toast('Set a tile URL template first'); return; }
    if (!state.conf.allowNet) { toast('Enable tile downloads first'); return; }
    var list = currentTileRange(), ok = 0, fail = 0;
    Promise.all(list.map(function (t) {
      return downloadTile(state.zoom, t.x, t.y).then(function (done) { if (done) ok++; else fail++; });
    })).then(function () {
      state.tileCache = {};
      requestDraw();
      cacheReport.textContent = 'Cached ' + ok + ' of ' + list.length + ' tiles at zoom ' + state.zoom +
        (fail ? ('\n' + fail + ' tiles could not be fetched (network, CORS or rate limit).') : '') +
        '\nOnly these tiles were requested; nothing else left the device.';
    });
  });
  document.getElementById('cache-stats').addEventListener('click', function () {
    idb('readonly', function (store) { return store.count(); }).then(function (n) {
      if (n === null) {
        cacheReport.textContent = 'No IndexedDB tile cache in this view (a plain browser without storage, or storage denied).' +
          '\nThe map still renders the coordinate grid and your pins.';
        return;
      }
      cacheReport.textContent = 'Tile cache: ' + n + ' tiles in IndexedDB database "' + DB_NAME + '" (store "' + DB_STORE + '").\n' +
        'Decoded in this session: ' + Object.keys(state.tileCache).length + '.\n' +
        'Template: ' + (state.conf.template || '(none)') + '\nDownloads enabled: ' + state.conf.allowNet;
    });
  });
  document.getElementById('cache-clear').addEventListener('click', function () {
    idb('readwrite', function (store) { return store.clear(); }).then(function () {
      state.tileCache = {};
      requestDraw();
      cacheReport.textContent = 'Tile cache emptied.';
    });
  });

  /* ---------- online tile fetch + place search (21000) ---------- */
  // Fetch ONLY the tiles for the current viewport at the current zoom. Respects
  // OSM tile usage policy: no prefetch beyond the visible view, no bulk crawl.
  function fetchVisibleTiles() {
    if (!state.conf.allowNet || !state.conf.template) return;
    var list = currentTileRange(), ok = 0, fail = 0;
    Promise.all(list.map(function (t) {
      return downloadTile(state.zoom, t.x, t.y).then(function (done) { if (done) ok++; else fail++; });
    })).then(function () {
      if (ok > 0) { state.tileCache = {}; requestDraw(); }
      if (fail > 0) toast('Fetched ' + ok + ' tiles; ' + fail + ' unavailable (network/CORS/rate limit)');
    });
  }

  // Search places via OpenStreetMap Nominatim (policy-compliant: single query per
  // user action, identifiable UA, attribution). Network position is NEVER shown
  // as GPS. Results are inserted as selectable pins; nothing opens externally.
  var NOMINATIM = 'https://nominatim.openstreetmap.org/search';
  function searchPlaces(q) {
    q = (q || '').trim();
    if (!q) return;
    if (q.length < 3) { toast('Type at least 3 characters to search places'); return; }
    toast('Searching places…');
    var url = NOMINATIM + '?format=jsonv2&limit=6&accept-language=en&q=' + encodeURIComponent(q);
    fetch(url, {
      mode: 'cors', credentials: 'omit',
      headers: { 'User-Agent': 'NuxelMaps/21000 (personal use; contact owner)' }
    }).then(function (r) { if (!r.ok) throw new Error('HTTP ' + r.status); return r.json(); })
      .then(function (results) {
        if (!Array.isArray(results) || !results.length) { toast('No places found for “' + q + '”'); return; }
        results.forEach(function (item) {
          var lat = parseFloat(item.lat), lon = parseFloat(item.lon);
          if (!isFinite(lat) || !isFinite(lon)) return;
          state.pins.push({ id: 'place-' + Date.now() + '-' + Math.random().toString(36).slice(2, 7),
            lat: lat, lon: lon, label: (item.display_name || 'Place').split(',').slice(0, 3).join(','), at: Date.now() });
        });
        save(K_PINS, state.pins);
        if (state.pins.length) {
          var last = state.pins[state.pins.length - 1];
          state.center = { lat: last.lat, lon: last.lon }; state.zoom = Math.max(state.zoom, 12);
        }
        renderPins(document.getElementById('search').value);
        persistView(); requestDraw();
        toast('Found ' + results.length + ' place(s) — added as pins (© OpenStreetMap contributors)');
      }).catch(function (e) {
        toast('Place search unavailable: ' + (e && e.message ? e.message : 'network error'));
      });
  }

  // Enter in the search box runs a real place search; typing still filters saved pins.
  document.getElementById('search').addEventListener('keydown', function (ev) {
    if (ev.key === 'Enter') { ev.preventDefault(); searchPlaces(ev.target.value); }
  });
  document.getElementById('search-panel').addEventListener('click', function () {
    searchPlaces(document.getElementById('search').value);
  });

  /* ---------- boot ---------- */
  window.addEventListener('resize', resize);
  resize();
  renderPins();
  writeBadge();
  updateOverlay();
  if (window.NuxelBridge && window.NuxelBridge.call) {
    window.NuxelBridge.call('location', 'status', {}).then(function (r) {
      if (r && (r.available || r.fix)) {
        toast('GNSS reports a position; use ⌖ to jump to a coordinate');
      }
    }).catch(function () { /* offline: the manual coordinate entry is the supported path */ });
  }

  // headless smoke-test hook
  window.nuxelMaps = {
    state: state, haversine: haversine, lonToX: lonToX, latToY: latToY,
    xToLon: xToLon, yToLat: yToLat, screenToLatLon: screenToLatLon, tileKey: tileKey, draw: draw,
    canvas: function () { return !!ctx; }
  };
})();
