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

  var state = { items: [], filter: '', album: '', index: 0, online: false, cache: {}, order: [], gridScroll: 0, viewerOpen: false };
  var sharedObserver = null;
  var FILE_BASE = 'http://127.0.0.1:8080/api/v1/storage/file?path=';
  var THUMB_BASE = 'http://127.0.0.1:8080/api/v1/storage/thumbnail?path=';

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
      kind: raw.kind || (/(video|mp4|webm|mov|mkv)/i.test(raw.mime || raw.name || '') ? 'video' : (/(audio|wav|mp3|ogg|flac|m4a|opus)/i.test(raw.mime || raw.name || '') ? 'audio' : 'photo')),
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

  function thumbnailUrl(item) {
    return THUMB_BASE + encodeURIComponent(item.path || '');
  }

  // Grid/card still.  A video card NEVER instantiates <video>: that created a
  // decoder per cell.  The server generates a real JPEG frame (ffmpeg/mpv/
  // GStreamer, whichever is installed) and caches it by path+size+mtime.
  function thumbEl(item) {
    if (item.kind === 'audio') {
      var aw = document.createElement('div');
      aw.className = 'thumb-wrap audio-thumb';
      var ac = document.createElement('canvas');
      ac.width = 300; ac.height = 120; ac.className = 'media';
      aw.appendChild(ac);
      var ab = document.createElement('span');
      ab.className = 'video-badge'; ab.textContent = '♪';
      aw.appendChild(ab);
      var wf = 'http://127.0.0.1:8080/api/v1/storage/waveform?buckets=80&path=' + encodeURIComponent(item.path || '');
      fetch(wf, { cache: 'no-store' }).then(function (r) { return r.json(); }).then(function (doc) {
        if (!doc || !doc.success || !Array.isArray(doc.peak)) return;
        var c = ac.getContext('2d'); c.fillStyle = '#150e20'; c.fillRect(0, 0, ac.width, ac.height);
        var n = doc.peak.length || 1, bw = ac.width / n;
        for (var i = 0; i < n; i++) {
          var h = Math.max(1, (doc.peak[i] || 0) * (ac.height - 12));
          c.fillStyle = '#c084fc'; c.fillRect(i * bw, (ac.height - h) / 2, Math.max(1, bw - 1), h);
        }
      }).catch(function () {});
      return aw;
    }
    if (item.kind === 'video') {
      var wrap = document.createElement('div');
      wrap.className = 'thumb-wrap';
      if (item.source === 'storage' && item.path) {
        var img = document.createElement('img');
        img.src = thumbnailUrl(item);
        img.alt = 'Still frame from ' + item.name;
        img.loading = 'lazy';
        img.decoding = 'async';
        img.className = 'media';
        img.addEventListener('error', function () {
          img.replaceWith(placeholder('No thumbnail (codec unavailable)'));
        }, { once: true });
        wrap.appendChild(img);
        var badge = document.createElement('span');
        badge.className = 'video-badge';
        badge.textContent = '▶';
        wrap.appendChild(badge);
        return wrap;
      }
      return placeholder('Video thumbnail unavailable');
    }
    var photo = document.createElement('img');
    photo.src = storageUrl(item);
    photo.alt = item.name;
    photo.loading = 'lazy';
    photo.decoding = 'async';
    photo.className = 'media';
    photo.style.imageOrientation = 'from-image';
    var retried = false;
    photo.addEventListener('error', function () {
      // The thumbnail endpoint serves the same verified rung for stills and
      // has its own strict path check.  Retry once there before giving up; a
      // transient full-file read must not leave a permanent "undecodable" tile.
      if (!retried && item.path) {
        retried = true;
        photo.src = thumbnailUrl(item);
        return;
      }
      photo.replaceWith(placeholder('Image could not be decoded (format unsupported)'));
    });
    return photo;
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
    if (item.kind === 'audio') {
      var a = document.createElement('audio');
      a.src = url; a.controls = true; a.preload = 'metadata'; a.className = 'media';
      a.addEventListener('error', function () {
        a.replaceWith(placeholder('Audio playback unavailable in WebKit; the file is still stored.'));
      }, { once: true });
      return a;
    }
    if (item.kind === 'video') {
      var v = document.createElement('video');
      v.src = url;
      v.muted = !full;
      v.playsInline = true;
      v.preload = full ? 'metadata' : 'none';
      v.controls = !!full;
      v.className = 'media';
      if (full && item.source === 'storage' && item.path) v.poster = thumbnailUrl(item);
      v.addEventListener('error', function () {
        // Keep the still visible and report the real codec limitation.  A
        // generated thumbnail is not proof that WebKit can play the video.
        var box = document.createElement('div');
        box.className = 'playback-error';
        var poster = document.createElement('img');
        poster.className = 'media';
        poster.alt = 'Poster for ' + item.name;
        if (item.source === 'storage' && item.path) poster.src = thumbnailUrl(item);
        box.appendChild(poster);
        var note = document.createElement('p');
        note.textContent = 'Playback unavailable: WebKit cannot decode ' + item.name +
          '. The still frame is shown; open it in the native player for this codec.';
        box.appendChild(note);
        if (full && item.source === 'storage' && item.path) {
          var openNative = document.createElement('button');
          openNative.type = 'button';
          openNative.className = 'icon-btn';
          openNative.textContent = 'Open in Player';
          openNative.addEventListener('click', function (e) {
            e.stopPropagation();
            openNative.disabled = true;
            fetch('http://127.0.0.1:8080/api/v1/apps/open-media', {
              method: 'POST', headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({ app_id: 'org.nuxel.MediaPlayer', path: item.path })
            }).then(function (r) { return r.json(); }).then(function (res) {
              if (!res || res.success !== true) {
                openNative.disabled = false;
                openNative.textContent = 'Player: ' + ((res && (res.error || res.detail)) || 'not available');
              } else {
                openNative.textContent = 'Opening in Player…';
              }
            }).catch(function (err) {
              openNative.disabled = false;
              openNative.textContent = 'Player: ' + (err && err.message ? err.message : 'failed');
            });
          });
          box.appendChild(openNative);
        }
        v.replaceWith(box);
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
      var ph = placeholder(item.kind === 'video' ? 'video' : (item.kind === 'audio' ? '♪ audio' : '…'));
      cell.appendChild(ph);
      var cap = document.createElement('div');
      cap.className = 'cap';
      cap.textContent = (item.kind === 'video' ? '▶ ' : (item.kind === 'audio' ? '♪ ' : '')) + item.name;
      cell.appendChild(cap);
      var loaded = false;
      var loadMedia = function () {
        if (loaded) return;
        loaded = true;
        var node = thumbEl(item);
        if (cell.firstChild === ph) cell.replaceChild(node, ph);
        else cell.insertBefore(node, cap);
      };
      // One shared observer instead of one per card.  This bounds the number
      // of live observers for a 2000-item Gallery and only loads visible stills.
      if ('IntersectionObserver' in window) {
        if (!sharedObserver) {
          sharedObserver = new IntersectionObserver(function (entries) {
            entries.forEach(function (en) {
              if (!en.isIntersecting) return;
              sharedObserver.unobserve(en.target);
              var fn = en.target.__nuxelLoad;
              if (fn) { en.target.__nuxelLoad = null; fn(); }
            });
          }, { rootMargin: '160px' });
        }
        cell.__nuxelLoad = loadMedia;
        sharedObserver.observe(cell);
      } else loadMedia();
      cell.addEventListener('click', function () {
        if (item.kind === 'video') openNativePlayer(item); else openViewer(item);
      });
      els.grid.appendChild(cell);
    });
  }

  function openNativePlayer(item) {
    if (!item || item.source !== 'storage' || !item.path) {
      openViewer(item);
      return;
    }
    toast('Opening ' + item.name + ' in the native player…');
    fetch('http://127.0.0.1:8080/api/v1/apps/open-media', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ app_id: 'org.nuxel.MediaPlayer', path: item.path })
    }).then(function (r) { return r.json(); }).then(function (res) {
      if (!res || res.success !== true) {
        toast('Player: ' + ((res && (res.error || res.detail)) || 'not available') + ' — showing still');
        openViewer(item);
      }
    }).catch(function (err) {
      toast('Player launch failed: ' + (err && err.message ? err.message : 'unknown'));
      openViewer(item);
    });
  }

  function openViewer(item) {
    state.order = visible();
    state.index = Math.max(0, state.order.indexOf(item));
    state.gridScroll = els.grid ? els.grid.scrollTop : 0;
    state.viewerOpen = true;
    paintViewer();
    els.viewer.classList.remove('hidden');
  }

  function stopViewerMedia() {
    try {
      var nodes = els.viewerMedia ? els.viewerMedia.querySelectorAll('video') : [];
      for (var i = 0; i < nodes.length; i++) {
        var v = nodes[i];
        try { v.pause(); } catch (e) {}
        try { v.removeAttribute('src'); v.load(); } catch (e) {}
      }
      if (els.viewerMedia) els.viewerMedia.innerHTML = '';
    } catch (e) {}
  }

  async function paintViewer() {
    var item = state.order[state.index];
    if (!item) { closeViewer(); return; }
    stopViewerMedia();
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

  function closeViewer() {
    stopViewerMedia();
    els.viewer.classList.add('hidden');
    state.viewerOpen = false;
    try { if (els.grid) els.grid.scrollTop = state.gridScroll || 0; } catch (e) {}
  }

  /* Central-home Back contract.  When a preview is open, Back closes ONLY the
     preview and restores the gallery grid scroll position; Gallery stays the
     foreground app and its process/document is never torn down.  Video
     playback is paused and its source released before the viewer is hidden. */
  try {
    window.NuxelBack = {
      canGoBack: function () { return !!state.viewerOpen; },
      back: function () { closeViewer(); return true; }
    };
  } catch (e) {}

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
