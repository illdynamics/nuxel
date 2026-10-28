// Nuxel Gallery (PWNAGE-33000) — unified photo/video browser.
//
// Sources:
//   * the real user media folders (~/Gallery, ~/Pictures, ~/Videos, ~/DCIM)
//     through bridge `storage.media-list` + a bounded streaming file URL;
//   * captures from the camera media store (`camera.list-captures`), opened
//     through `camera.open` only when such a capture really exists.
//
// No sample images are bundled or generated.  A decode failure is reported as
// an error; it is never replaced with a placeholder that looks like success.
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

  var state = { items: [], filter: '', album: '', index: 0, online: false, cache: {}, order: [] };
  var FILE_BASE = 'http://127.0.0.1:8080/api/v1/storage/file?path=';

  function toast(msg) {
    els.toast.textContent = msg;
    els.toast.classList.remove('hidden');
    clearTimeout(toast._t);
    toast._t = setTimeout(function () { els.toast.classList.add('hidden'); }, 3000);
  }

  function call(ns, verb, params, fallback) {
    var b = window.NuxelBridge;
    if (!b || typeof b.call !== 'function') return Promise.resolve(fallback);
    return b.call(ns, verb, params).catch(function (e) {
      return fallback || { success: false, error: e && e.message };
    });
  }

  function normaliseStorage(raw, i) {
    var modified = Number(raw.modified || 0);
    var taken = Number(raw.taken || (modified * 1000) || Date.now());
    return {
      id: 'storage:' + (raw.path || i),
      source: 'storage',
      name: raw.name || String(raw.path || '').split('/').pop() || ('Media ' + (i + 1)),
      kind: raw.kind || (/(video|mp4|webm|mov|mkv)/i.test(raw.mime || raw.name || '') ? 'video' : 'photo'),
      taken: taken,
      size: raw.size || null,
      mime: raw.mime || null,
      path: raw.path || null,
      album: raw.album || 'Gallery',
      duration: raw.duration || null,
      camera: null,
      orientation: raw.orientation || null
    };
  }

  function normaliseCamera(raw, i) {
    var taken = raw.taken || raw.mtime || raw.timestamp || Date.now();
    return {
      id: 'camera:' + (raw.id || ('capture-' + i)),
      source: 'camera',
      cameraId: raw.id || ('capture-' + i),
      name: raw.name || (raw.path ? String(raw.path).split('/').pop() : ('Capture ' + (i + 1))),
      kind: raw.kind || (/(video|webm|mp4)/i.test(raw.mime || '') ? 'video' : 'photo'),
      taken: typeof taken === 'number' ? taken : (Date.parse(taken) || Date.now()),
      size: raw.size || null,
      w: raw.width || null,
      h: raw.height || null,
      mime: raw.mime || null,
      path: raw.path || null,
      album: 'Camera',
      duration: raw.duration || null,
      camera: raw.camera || null,
      orientation: raw.orientation || null
    };
  }

  async function load() {
    els.badge.textContent = 'media: reading…';
    var storage = await call('storage', 'media-list', {}, null);
    var camera = await call('camera', 'list-captures', { kind: '' }, null);
    var merged = [];
    if (storage && storage.success !== false && Array.isArray(storage.media)) {
      state.online = true;
      storage.media.forEach(function (m, i) { merged.push(normaliseStorage(m, i)); });
    }
    var caps = camera && (camera.captures || camera.items);
    if (Array.isArray(caps)) {
      caps.forEach(function (m, i) { merged.push(normaliseCamera(m, i)); });
    }
    // De-duplicate by path; the same file may be indexed by both sources.
    var seen = {};
    state.items = merged.filter(function (m) {
      var key = m.path || m.id;
      if (seen[key]) return false;
      seen[key] = true;
      return true;
    });
    if (!storage || storage.success === false) {
      els.badge.textContent = 'media: filesystem unavailable';
      els.badge.classList.add('warn');
    } else {
      els.badge.textContent = 'media: ' + state.items.length + ' item(s)';
      els.badge.classList.remove('warn');
    }
    render();
  }

  function albumOf(item) { return item.album || 'Gallery'; }

  function fillAlbums() {
    var names = {};
    state.items.forEach(function (i) { names[albumOf(i)] = true; });
    var current = els.album.value;
    els.album.innerHTML = '<option value="">All albums</option>';
    Object.keys(names).sort().forEach(function (n) {
      var o = document.createElement('option');
      o.value = n;
      o.textContent = n + ' (' + state.items.filter(function (i) { return albumOf(i) === n; }).length + ')';
      els.album.appendChild(o);
    });
    els.album.value = names[current] ? current : '';
    state.album = els.album.value;
  }

  function visible() {
    var q = state.filter.toLowerCase();
    return state.items.filter(function (i) {
      if (state.album && albumOf(i) !== state.album) return false;
      if (!q) return true;
      return (i.name + ' ' + albumOf(i) + ' ' + new Date(i.taken).toLocaleString()).toLowerCase().indexOf(q) >= 0;
    });
  }

  function storageUrl(item) {
    return FILE_BASE + encodeURIComponent(item.path || '');
  }

  async function cameraDataUrl(item) {
    if (state.cache[item.id]) return state.cache[item.id];
    var res = await call('camera', 'open', { id: item.cameraId }, null);
    if (res && res.success && res.capture && res.capture.data_b64) {
      var mime = res.capture.mime || item.mime || 'application/octet-stream';
      var url = 'data:' + mime + ';base64,' + res.capture.data_b64;
      state.cache[item.id] = url;
      return url;
    }
    return null;
  }

  function mediaUrl(item) {
    if (item.source === 'storage' && item.path) return Promise.resolve(storageUrl(item));
    return cameraDataUrl(item);
  }

  function placeholder(label) {
    var d = document.createElement('div');
    d.className = 'noimg';
    d.textContent = label || '…';
    return d;
  }

  function mediaEl(item, url, full) {
    if (item.kind === 'video') {
      var v = document.createElement('video');
      v.src = url;
      v.muted = !full;
      v.playsInline = true;
      v.preload = 'metadata';
      v.controls = !!full;
      v.className = 'media';
      v.addEventListener('error', function () {
        v.replaceWith(placeholder('Video could not be decoded (' + item.name + ')'));
      }, { once: true });
      return v;
    }
    var img = document.createElement('img');
    img.src = url;
    img.alt = item.name;
    img.loading = 'lazy';
    img.decoding = 'async';
    img.className = 'media';
    img.style.imageOrientation = 'from-image';
    img.addEventListener('error', function () {
      img.replaceWith(placeholder('Image could not be decoded (format unsupported)'));
    }, { once: true });
    return img;
  }

  function render() {
    fillAlbums();
    var rows = visible();
    els.grid.innerHTML = '';
    if (!rows.length) {
      els.empty.classList.remove('hidden');
      els.grid.classList.add('hidden');
      els.emptyDetail.textContent = state.items.length
        ? 'No media matches the current filter (' + state.items.length + ' indexed).'
        : 'The media folders are empty. Add files under ~/Gallery, ~/Pictures or ~/Videos, then press Refresh.';
      return;
    }
    els.empty.classList.add('hidden');
    els.grid.classList.remove('hidden');
    rows.forEach(function (item) {
      var cell = document.createElement('div');
      cell.className = 'cell';
      cell.dataset.id = item.id;
      var ph = placeholder(item.kind === 'video' ? 'video' : '…');
      cell.appendChild(ph);
      var cap = document.createElement('div');
      cap.className = 'cap';
      cap.textContent = (item.kind === 'video' ? '▶ ' : '') + item.name;
      cell.appendChild(cap);
      var loadMedia = function () {
        mediaUrl(item).then(function (url) {
          if (!url) return;
          cell.replaceChild(mediaEl(item, url, false), ph);
        });
      };
      if ('IntersectionObserver' in window) {
        var io = new IntersectionObserver(function (entries) {
          entries.forEach(function (en) {
            if (!en.isIntersecting) return;
            io.disconnect(); loadMedia();
          });
        });
        io.observe(cell);
      } else loadMedia();
      cell.addEventListener('click', function () { openViewer(item); });
      els.grid.appendChild(cell);
    });
  }

  function openViewer(item) {
    state.order = visible();
    state.index = Math.max(0, state.order.indexOf(item));
    paintViewer();
    els.viewer.classList.remove('hidden');
  }

  async function paintViewer() {
    var item = state.order[state.index];
    if (!item) { els.viewer.classList.add('hidden'); return; }
    els.viewerTitle.textContent = item.name + '  (' + (state.index + 1) + '/' + state.order.length + ')';
    els.viewerMedia.innerHTML = '<div class="noimg">loading…</div>';
    var url = await mediaUrl(item);
    els.viewerMedia.innerHTML = '';
    if (url) {
      els.viewerMedia.appendChild(mediaEl(item, url, true));
    } else {
      els.viewerMedia.appendChild(placeholder(item.kind === 'video'
        ? 'Video data unavailable (path: ' + (item.path || 'unknown') + ')'
        : 'Pixel data unavailable for this item'));
    }
    var lines = [
      'Kind         : ' + item.kind,
      'Album        : ' + albumOf(item),
      'Taken        : ' + new Date(item.taken).toLocaleString(),
      'Size         : ' + (item.size ? (item.size / 1024).toFixed(1) + ' KiB' : 'not reported'),
      'Dimensions   : ' + (item.w && item.h ? item.w + '×' + item.h : 'not reported'),
      'Duration     : ' + (item.duration ? item.duration + ' s' : 'n/a'),
      'Source       : ' + (item.source === 'camera' ? 'camera store' : 'user files'),
      'Storage path : ' + (item.path || 'not reported')
    ];
    els.viewerInfo.textContent = lines.join('\n');
  }

  function closeViewer() { els.viewer.classList.add('hidden'); }

  document.getElementById('close').addEventListener('click', closeViewer);
  document.getElementById('prev').addEventListener('click', closeViewer);
  document.getElementById('prev-of').addEventListener('click', function () {
    if (state.index > 0) { state.index--; paintViewer(); }
  });
  var next = function () { if (state.index < state.order.length - 1) { state.index++; paintViewer(); } };
  document.getElementById('next-of').addEventListener('click', next);
  document.getElementById('next-of2').addEventListener('click', next);
  document.getElementById('delete').addEventListener('click', async function () {
    var item = state.order[state.index];
    if (!item) return;
    if (!window.confirm('Delete ' + item.name + '? This removes the file.')) return;
    var res;
    if (item.source === 'camera') res = await call('camera', 'delete', { id: item.cameraId }, null);
    else res = await call('storage', 'delete', { path: item.path }, null);
    if (res && res.success !== false) {
      state.items = state.items.filter(function (x) { return x.id !== item.id; });
      state.order = state.order.filter(function (x) { return x.id !== item.id; });
      if (state.index >= state.order.length) state.index = Math.max(0, state.order.length - 1);
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
      return { id: i.id, source: i.source, name: i.name, kind: i.kind, album: albumOf(i),
               taken: new Date(i.taken).toISOString(), size: i.size, path: i.path };
    });
    var text = JSON.stringify({ schema_version: 3, media: rows }, null, 2);
    try {
      var a = document.createElement('a');
      a.href = URL.createObjectURL(new Blob([text], { type: 'application/json' }));
      a.download = 'nuxel-gallery-index.json';
      document.body.appendChild(a); a.click();
      setTimeout(function () { URL.revokeObjectURL(a.href); a.remove(); }, 1500);
      toast('Exported ' + rows.length + ' media record(s)');
    } catch (e) { toast('Export unavailable in this view'); }
  });

  document.addEventListener('visibilitychange', function () {
    if (!document.hidden) load();
  });

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', load, { once: true });
  else load();
  window.nuxelGallery = { load: load, items: function () { return state.items; }, visible: visible };
})();
