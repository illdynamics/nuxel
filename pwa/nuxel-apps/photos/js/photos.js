// Nuxel Photos — completed file-backed gallery (A52).
//
// Reads real media records from the bridge `camera.list-captures` (metadata
// only: no base64 in the list) and lazily loads pixel data per visible item via
// `camera.open`.  Deletes real files via `camera.delete`.  Videos render as
// playable <video> when small enough to inline; otherwise metadata + path are
// shown honestly.  Never fabricates imagery.
(function () {
  'use strict';

  var els = {
    grid: document.getElementById('grid'),
    empty: document.getElementById('empty'),
    emptyDetail: document.getElementById('empty-detail'),
    search: document.getElementById('search'),
    album: document.getElementById('album'),
    badge: document.getElementById('src-badge'),
    viewer: document.getElementById('viewer'),
    viewerMedia: document.getElementById('viewer-media'),
    viewerTitle: document.getElementById('viewer-title'),
    viewerInfo: document.getElementById('viewer-info'),
    toast: document.getElementById('toast')
  };

  var state = { items: [], filter: '', album: '', index: 0, online: false, cache: {} };
  var order = [];

  function toast(msg) {
    els.toast.textContent = msg;
    els.toast.classList.remove('hidden');
    clearTimeout(toast._t);
    toast._t = setTimeout(function () { els.toast.classList.add('hidden'); }, 2400);
  }

  function bridge() { return window.NuxelBridge || null; }

  function call(ns, verb, params, fb) {
    var b = bridge();
    if (!b || typeof b.call !== 'function') return Promise.resolve(fb);
    return b.call(ns, verb, params).catch(function () { return fb; });
  }

  function albumOf(item) {
    var d = new Date(item.taken || Date.now());
    return d.toLocaleDateString(undefined, { year: 'numeric', month: 'long' });
  }

  function normalise(raw, i) {
    var taken = raw.taken || raw.mtime || raw.timestamp || Date.now();
    return {
      id: raw.id || ('capture-' + i),
      name: raw.name || (raw.path ? String(raw.path).split('/').pop() : ('Capture ' + (i + 1))),
      kind: raw.kind || (/(video|webm|mp4)/i.test(raw.mime || '') ? 'video' : 'photo'),
      taken: typeof taken === 'number' ? taken : (Date.parse(taken) || Date.now()),
      size: raw.size || null,
      w: raw.width || null,
      h: raw.height || null,
      mime: raw.mime || null,
      path: raw.path || null,
      duration: raw.duration || null,
      camera: raw.camera || null,
      orientation: raw.orientation || null
    };
  }

  async function load() {
    els.badge.textContent = 'media store: reading…';
    var res = await call('camera', 'list-captures', { kind: '' }, null);
    var raw = res && (res.captures || res.items);
    if (!raw || !Array.isArray(raw)) {
      state.online = false;
      showEmpty('The camera service returned no media list. Take a photo in the Camera app, then press Refresh.');
      return;
    }
    state.online = true;
    state.items = raw.map(normalise);
    render();
  }

  function showEmpty(detail) {
    els.badge.textContent = 'media store: offline/empty';
    els.badge.classList.add('warn');
    els.emptyDetail.textContent = detail;
    els.grid.classList.add('hidden');
    els.empty.classList.remove('hidden');
  }

  function fillAlbums() {
    var names = {};
    state.items.forEach(function (i) { names[i.album || albumOf(i)] = true; });
    var current = els.album.value;
    els.album.innerHTML = '<option value="">All</option>';
    Object.keys(names).sort().forEach(function (n) {
      var o = document.createElement('option');
      o.value = n;
      o.textContent = n + ' (' + state.items.filter(function (i) { return (i.album || albumOf(i)) === n; }).length + ')';
      els.album.appendChild(o);
    });
    els.album.value = names[current] ? current : '';
    state.album = els.album.value;
  }

  function visible() {
    var q = state.filter.toLowerCase();
    return state.items.filter(function (i) {
      var alb = i.album || albumOf(i);
      if (state.album && alb !== state.album) return false;
      if (!q) return true;
      return (i.name + ' ' + alb + ' ' + new Date(i.taken).toLocaleString()).toLowerCase().indexOf(q) >= 0;
    });
  }

  async function openData(item) {
    if (state.cache[item.id]) return state.cache[item.id];
    var res = await call('camera', 'open', { id: item.id }, null);
    if (res && res.success && res.capture && res.capture.data_b64) {
      var mime = res.capture.mime || item.mime || (item.kind === 'video' ? 'video/webm' : 'image/jpeg');
      var url = 'data:' + mime + ';base64,' + res.capture.data_b64;
      state.cache[item.id] = url;
      return url;
    }
    return null;
  }

  function noImage(label) {
    var d = document.createElement('div');
    d.className = 'noimg';
    d.textContent = label || 'metadata only';
    return d;
  }

  function render() {
    fillAlbums();
    var rows = visible();
    els.grid.innerHTML = '';
    els.badge.textContent = 'media store: ' + (state.online ? 'connected' : 'offline');
    els.badge.classList.toggle('warn', !state.online);
    if (!rows.length) {
      els.empty.classList.remove('hidden');
      els.grid.classList.add('hidden');
      els.emptyDetail.textContent = state.items.length
        ? 'No media matches the current filter (' + state.items.length + ' indexed).'
        : 'The media store is empty: take a photo in the Camera app, then press Refresh.';
      return;
    }
    els.empty.classList.add('hidden');
    els.grid.classList.remove('hidden');
    rows.forEach(function (item) {
      var cell = document.createElement('div');
      cell.className = 'cell';
      cell.dataset.id = item.id;
      var placeholder = noImage(item.kind === 'video' ? 'video' : '…');
      cell.appendChild(placeholder);
      cell.appendChild(noImageCaption(item));
      // Lazy-load pixel data only when the cell becomes visible.
      if ('IntersectionObserver' in window) {
        var io = new IntersectionObserver(function (entries) {
          entries.forEach(function (en) {
            if (!en.isIntersecting) return;
            io.disconnect();
            openData(item).then(function (url) {
              if (!url) return;
              cell.replaceChild(mediaEl(item, url, false), placeholder);
            });
          });
        });
        io.observe(cell);
      }
      cell.addEventListener('click', function () { openViewer(item); });
      els.grid.appendChild(cell);
    });
  }

  function noImageCaption(item) {
    var cap = document.createElement('div');
    cap.className = 'cap';
    cap.textContent = new Date(item.taken).toLocaleDateString();
    return cap;
  }

  function mediaEl(item, url, controls) {
    if (item.kind === 'video') {
      var v = document.createElement('video');
      v.src = url; v.muted = true; v.playsInline = true; v.controls = !!controls;
      v.className = 'media';
      return v;
    }
    var img = document.createElement('img');
    img.src = url; img.alt = item.name; img.className = 'media';
    return img;
  }

  function openViewer(item) {
    order = visible();
    state.index = Math.max(0, order.indexOf(item));
    paintViewer();
    els.viewer.classList.remove('hidden');
  }

  async function paintViewer() {
    var item = order[state.index];
    if (!item) { els.viewer.classList.add('hidden'); return; }
    els.viewerTitle.textContent = item.name + '  (' + (state.index + 1) + '/' + order.length + ')';
    els.viewerMedia.innerHTML = '';
    var url = await openData(item);
    if (url) {
      els.viewerMedia.appendChild(mediaEl(item, url, true));
    } else {
      var d = document.createElement('div');
      d.className = 'noimg';
      d.textContent = item.kind === 'video'
        ? 'Video too large to inline — metadata only (path: ' + (item.path || 'unknown') + ')'
        : 'Pixel data not available in this session (metadata only)';
      els.viewerMedia.appendChild(d);
    }
    var lines = [
      'Kind         : ' + item.kind,
      'Taken        : ' + new Date(item.taken).toLocaleString(),
      'Size         : ' + (item.size ? (item.size / 1024).toFixed(1) + ' KiB' : 'not reported'),
      'Dimensions   : ' + (item.w && item.h ? item.w + '×' + item.h : 'not reported'),
      'Duration     : ' + (item.duration ? item.duration + ' s' : 'n/a'),
      'Camera       : ' + (item.camera || 'not reported'),
      'Storage path : ' + (item.path || 'not reported')
    ];
    els.viewerInfo.textContent = lines.join('\n');
  }

  document.getElementById('close').addEventListener('click', function () { els.viewer.classList.add('hidden'); });
  document.getElementById('prev').addEventListener('click', function () { els.viewer.classList.add('hidden'); });
  document.getElementById('prev-of').addEventListener('click', function () { if (state.index > 0) { state.index--; paintViewer(); } });
  document.getElementById('next-of').addEventListener('click', function () { if (state.index < order.length - 1) { state.index++; paintViewer(); } });
  document.getElementById('next-of2').addEventListener('click', function () { if (state.index < order.length - 1) { state.index++; paintViewer(); } });
  document.getElementById('delete').addEventListener('click', async function () {
    var item = order[state.index];
    if (!item) return;
    var res = await call('camera', 'delete', { id: item.id }, null);
    if (res && res.success) {
      state.items = state.items.filter(function (x) { return x.id !== item.id; });
      order = order.filter(function (x) { return x.id !== item.id; });
      if (state.index >= order.length) state.index = Math.max(0, order.length - 1);
      delete state.cache[item.id];
      paintViewer(); render();
      toast('Deleted ' + item.name);
    } else {
      toast('Delete failed: ' + ((res && res.error) || 'unknown error'));
    }
  });

  els.search.addEventListener('input', function (ev) { state.filter = ev.target.value || ''; render(); });
  els.album.addEventListener('change', function (ev) { state.album = ev.target.value; render(); });
  document.getElementById('refresh').addEventListener('click', function () { load(); });
  document.getElementById('export').addEventListener('click', function () {
    var rows = state.items.map(function (i) {
      return { id: i.id, name: i.name, kind: i.kind, taken: new Date(i.taken).toISOString(), size: i.size, path: i.path };
    });
    var text = JSON.stringify({ schema_version: 2, online: state.online, media: rows }, null, 2);
    try {
      var a = document.createElement('a');
      a.href = URL.createObjectURL(new Blob([text], { type: 'application/json' }));
      a.download = 'nuxel-photos-index.json';
      document.body.appendChild(a); a.click();
      setTimeout(function () { URL.revokeObjectURL(a.href); a.remove(); }, 2000);
      toast('Exported ' + rows.length + ' entries');
    } catch (e) { toast('Export unavailable in this view'); }
  });

  load();
  window.nuxelPhotos = { state: state, normalise: normalise, albumOf: albumOf, visible: visible, render: render };
})();
