// Nuxel Photos (mission area 30; camera/gallery proof area 15)
//
// Reads the captures the Camera PWA produced through the shared Nuxel bridge
// (verb camera.list-captures) and shows them here.  When the bridge is offline
// the app reports that honestly and shows only the metadata it has indexed
// locally - it never renders placeholder imagery pretending to be a photo.
(function () {
  'use strict';
  var K_INDEX = 'nuxel-photos-index';

  var els = {
    grid: document.getElementById('grid'),
    empty: document.getElementById('empty'),
    emptyDetail: document.getElementById('empty-detail'),
    search: document.getElementById('search'),
    album: document.getElementById('album'),
    badge: document.getElementById('src-badge'),
    viewer: document.getElementById('viewer'),
    viewerImg: document.getElementById('viewer-img'),
    viewerTitle: document.getElementById('viewer-title'),
    viewerInfo: document.getElementById('viewer-info'),
    toast: document.getElementById('toast')
  };

  var state = { items: [], filter: '', album: '', index: 0, bridgeOnline: false };

  function toast(msg) {
    els.toast.textContent = msg;
    els.toast.classList.remove('hidden');
    clearTimeout(toast._t);
    toast._t = setTimeout(function () { els.toast.classList.add('hidden'); }, 2400);
  }

  function localIndex() {
    try { return JSON.parse(localStorage.getItem(K_INDEX) || '[]') || []; } catch (e) { return []; }
  }
  function saveIndex(rows) {
    var meta = rows.map(function (r) {
      return { id: r.id, name: r.name, taken: r.taken, size: r.size, w: r.w, h: r.h };
    });
    try { localStorage.setItem(K_INDEX, JSON.stringify(meta)); } catch (e) { /* ignore */ }
  }

  function albumOf(item) {
    var d = new Date(item.taken || Date.now());
    return d.toLocaleDateString(undefined, { year: 'numeric', month: 'long' });
  }

  function normalise(raw, i) {
    var taken = raw.taken || raw.timestamp || raw.created_at || raw.mtime || Date.now();
    return {
      id: raw.id || raw.path || ('capture-' + i),
      name: raw.name || raw.filename || (raw.path ? String(raw.path).split('/').pop() : ('Capture ' + (i + 1))),
      taken: typeof taken === 'number' ? taken : Date.parse(taken) || Date.now(),
      size: raw.size || raw.bytes || null,
      w: raw.width || raw.w || null,
      h: raw.height || raw.h || null,
      album: raw.album || null,
      path: raw.path || raw.url || null,
      url: raw.data_url || raw.thumbnail || raw.url || null
    };
  }

  function load() {
    var bridge = window.NuxelBridge;
    els.badge.textContent = 'camera store: reading…';
    if (!bridge || typeof bridge.call !== 'function') {
      state.bridgeOnline = false;
      showOffline('The shared bridge client is not present in this view.');
      return;
    }
    bridge.call('camera', 'list-captures', {}).then(function (res) {
      var raw = (res && (res.captures || res.items)) || null;
      state.bridgeOnline = !!(res && res.success !== false && raw);
      if (!raw) { showOffline('The camera service returned no capture list.'); return; }
      state.items = raw.map(normalise);
      saveIndex(state.items);
      render();
    }).catch(function () {
      state.bridgeOnline = false;
      showOffline('The camera service could not be reached.');
    });
  }

  function showOffline(detail) {
    var cached = localIndex();
    els.badge.textContent = 'camera store: offline';
    els.badge.classList.add('warn');
    els.emptyDetail.textContent = detail + ' Indexed locally: ' + cached.length +
      ' capture(s). Nuxel Photos will not invent images; re-run Refresh once the bridge is up.';
    if (!cached.length) {
      els.grid.classList.add('hidden');
      els.empty.classList.remove('hidden');
      return;
    }
    state.items = cached.map(function (c, i) { return normalise(c, i); });
    render();
  }

  function fillAlbums() {
    var names = {};
    state.items.forEach(function (i) { names[i.album || albumOf(i)] = true; });
    var current = els.album.value;
    els.album.innerHTML = '<option value="">All albums</option>';
    Object.keys(names).sort().forEach(function (n) {
      var o = document.createElement('option');
      o.value = n; o.textContent = n + ' (' + state.items.filter(function (i) { return (i.album || albumOf(i)) === n; }).length + ')';
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

  function render() {
    fillAlbums();
    var rows = visible();
    els.grid.innerHTML = '';
    els.badge.textContent = 'camera store: ' + (state.bridgeOnline ? 'connected' : 'offline');
    els.badge.classList.toggle('warn', !state.bridgeOnline);
    if (!rows.length) {
      els.empty.classList.remove('hidden');
      els.grid.classList.add('hidden');
      els.emptyDetail.textContent = state.items.length
        ? 'No capture matches the current filter (' + state.items.length + ' indexed).'
        : 'The camera store is empty: take a photo in the Camera app, then press Refresh.';
      return;
    }
    els.empty.classList.add('hidden');
    els.grid.classList.remove('hidden');
    rows.forEach(function (item) {
      var cell = document.createElement('div');
      cell.className = 'cell';
      if (item.url) {
        var img = document.createElement('img');
        img.loading = 'lazy';
        img.alt = item.name;
        img.src = item.url;
        img.onerror = function () { img.remove(); cell.insertBefore(noImage(), cell.firstChild); };
        cell.appendChild(img);
      } else {
        cell.appendChild(noImage());
      }
      var cap = document.createElement('div');
      cap.className = 'cap';
      cap.textContent = new Date(item.taken).toLocaleDateString();
      cell.appendChild(cap);
      cell.addEventListener('click', function () { openViewer(item); });
      els.grid.appendChild(cell);
    });
  }
  function noImage() {
    var d = document.createElement('div');
    d.className = 'noimg';
    d.textContent = 'metadata only — the thumbnail is provided by the camera service';
    return d;
  }

  var order = [];
  function openViewer(item) {
    order = visible();
    state.index = Math.max(0, order.indexOf(item));
    paintViewer();
    els.viewer.classList.remove('hidden');
  }
  function paintViewer() {
    var item = order[state.index];
    if (!item) { els.viewer.classList.add('hidden'); return; }
    els.viewerTitle.textContent = item.name + '  (' + (state.index + 1) + '/' + order.length + ')';
    if (item.url) {
      els.viewerImg.style.display = '';
      els.viewerImg.src = item.url;
    } else {
      els.viewerImg.removeAttribute('src');
      els.viewerImg.style.display = 'none';
    }
    var lines = [
      'Album        : ' + (item.album || albumOf(item)),
      'Taken        : ' + new Date(item.taken).toLocaleString(),
      'Size         : ' + (item.size ? (item.size / 1024).toFixed(1) + ' KiB' : 'not reported'),
      'Dimensions   : ' + (item.w && item.h ? item.w + '×' + item.h : 'not reported'),
      'Storage path : ' + (item.path || 'not reported by the camera service'),
      'Pixel data   : ' + (item.url ? 'provided by the camera service' : 'not available in this session (metadata only)')
    ];
    els.viewerInfo.textContent = lines.join('\n');
  }
  document.getElementById('prev').addEventListener('click', function () { els.viewer.classList.add('hidden'); });
  document.getElementById('close').addEventListener('click', function () { els.viewer.classList.add('hidden'); });
  document.getElementById('prev-of').addEventListener('click', function () { if (state.index > 0) { state.index--; paintViewer(); } });
  document.getElementById('next-of').addEventListener('click', function () { if (state.index < order.length - 1) { state.index++; paintViewer(); } });
  document.getElementById('next-of2').addEventListener('click', function () { if (state.index < order.length - 1) { state.index++; paintViewer(); } });
  document.getElementById('delete').addEventListener('click', function () {
    var item = order[state.index];
    if (!item) return;
    var bridge = window.NuxelBridge;
    var done = function () {
      state.items = state.items.filter(function (x) { return x.id !== item.id; });
      order = order.filter(function (x) { return x.id !== item.id; });
      if (state.index >= order.length) state.index = Math.max(0, order.length - 1);
      saveIndex(state.items);
      paintViewer();
      render();
      toast('Removed ' + item.name + ' from the index');
    };
    if (bridge && typeof bridge.call === 'function') {
      bridge.call('camera', 'delete', { id: item.id, path: item.path }).then(done).catch(done);
    } else { done(); }
  });

  els.search.addEventListener('input', function (ev) { state.filter = ev.target.value || ''; render(); });
  els.album.addEventListener('change', function (ev) { state.album = ev.target.value; render(); });
  document.getElementById('refresh').addEventListener('click', function () { load(); });
  document.getElementById('export').addEventListener('click', function () {
    var rows = state.items.map(function (i) {
      return { id: i.id, name: i.name, taken: new Date(i.taken).toISOString(), size: i.size, album: i.album || albumOf(i), path: i.path };
    });
    var text = JSON.stringify({ schema_version: 1, bridge_online: state.bridgeOnline, captures: rows }, null, 2);
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

  // headless smoke-test hook
  window.nuxelPhotos = { state: state, normalise: normalise, albumOf: albumOf, visible: visible, render: render };
})();
