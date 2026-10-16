// Nuxel Downloader — UI wiring over DownloadQueue + the Nuxel bridge.
//
// TRANSPORT TRUTH: a browser page cannot write to the filesystem.  Transfers are
// performed by the Nuxel host (nuxel-bridge `download.*`).  When no host answers
// the queue still works — add/pause/resume/cancel/persist are local — but every
// item is marked NO HOST and NOTHING is transferred.  There is no simulated
// "completed" state, because a fake green tick is worse than an honest red one.
(function () {
  'use strict';
  var Q = window.DownloadQueue;
  var STORE_KEY = 'nuxel-downloader-queue-v1';
  var el = function (id) { return document.getElementById(id); };
  var store = Q.newStore();
  var host = { available: false, checked: false };

  function toast(m) {
    var t = el('toast'); t.textContent = m; t.classList.add('show');
    clearTimeout(toast._t); toast._t = setTimeout(function () { t.classList.remove('show'); }, 2800);
  }

  function bridge() { return window.NuxelBridge && typeof window.NuxelBridge.call === 'function' ? window.NuxelBridge.call : null; }
  function liveOnly(res) { return (res && res.success !== false && res.mock !== true) ? res : null; }

  function persist() {
    try { localStorage.setItem(STORE_KEY, Q.serialize(store)); } catch (e) { /* storage full or blocked */ }
  }
  function restore() {
    try {
      var raw = localStorage.getItem(STORE_KEY);
      if (raw) store = Q.deserialize(raw);
    } catch (e) { store = Q.newStore(); }
  }

  /* ---------------- notice ---------------- */

  function renderNotice() {
    el('notice-text').textContent = Q.NOTICE_TEXT;
    var ok = Q.noticeSatisfied(store);
    el('notice-state').textContent = ok
      ? 'Accepted (notice v' + Q.NOTICE_VERSION + '). You can queue downloads.'
      : 'NOT accepted — the queue refuses every item until you accept this notice.';
    el('notice-state').className = 'pill ' + (ok ? 'ok' : 'bad');
    el('accept-notice').disabled = ok;
    el('add-url').disabled = !ok;
    el('enqueue').disabled = !ok;
    el('notice-version').textContent = 'v' + Q.NOTICE_VERSION;
  }

  /* ---------------- queue rendering ---------------- */

  function pillFor(item) {
    if (item.status === 'done') {
      return item.verified === true
        ? { cls: 'ok', text: 'done · sha256 verified' }
        : { cls: 'warn', text: 'done · NO digest published (unverified)' };
    }
    if (item.status === 'blocked') return { cls: 'bad', text: 'blocked' };
    if (item.status === 'failed') return { cls: 'bad', text: 'failed' };
    if (item.status === 'paused') return { cls: 'warn', text: 'paused at ' + Q.formatBytes(item.resumeFrom || 0) };
    if (item.status === 'running') return { cls: 'ok', text: 'running (' + item.strategy + ')' };
    if (item.status === 'cancelled') return { cls: 'warn', text: 'cancelled' };
    return { cls: '', text: 'queued (' + item.strategy + ')' };
  }

  function itemNode(item) {
    var p = pillFor(item);
    var node = document.createElement('div');
    node.className = 'item';
    node.innerHTML =
      '<div class="top"><span class="name">' + esc(item.name) + '</span>' +
      '<span class="pill ' + p.cls + '">' + esc(p.text) + '</span></div>' +
      '<div class="url">' + esc(item.url) + '</div>' +
      '<div class="bar"><i style="width:' + (item.progress || 0) + '%"></i></div>' +
      '<div class="meta"><span>' + (item.bytes ? Q.formatBytes(item.bytesDone || 0) + ' / ' + Q.formatBytes(item.bytes) : Q.formatBytes(item.bytesDone || 0)) + '</span>' +
      '<span>attempts ' + item.attempts + '/' + Q.MAX_ATTEMPTS + '</span>' +
      '<span>strategy ' + esc(item.strategy) + '</span>' +
      '<span>digest ' + (item.sha256 ? esc(item.sha256.slice(0, 12)) + '…' : 'none published') + '</span></div>' +
      (item.error ? '<p class="hint" style="color:#ffb4b4">' + esc(item.error) + '</p>' : '');
    var row = document.createElement('div');
    row.className = 'row'; row.style.marginTop = '8px';
    if (item.status === 'queued' || item.status === 'failed') row.appendChild(btn('Start', function () { startItem(item); }));
    if (item.status === 'running') row.appendChild(btn('Pause', function () { Q.pause(item); persist(); render(); }));
    if (item.status === 'paused') row.appendChild(btn('Resume', function () { Q.resume(item); persist(); render(); }));
    if (item.status !== 'cancelled' && item.status !== 'done') row.appendChild(btn('Cancel', function () { Q.cancel(item); persist(); render(); }, 'danger'));
    if (item.status === 'done' && item.verified === true) row.appendChild(btn('Open in Media', function () {
      toast('Media will only play this if the file really is on disk under /home/nuxel/Downloads.');
      location.href = '../media/index.html';
    }));
    row.appendChild(btn('Remove', function () {
      store.items = store.items.filter(function (x) { return x.id !== item.id; }); persist(); render();
    }, 'ghost'));
    node.appendChild(row);
    return node;
  }

  function btn(label, fn, cls) {
    var b = document.createElement('button');
    b.textContent = label; if (cls) b.className = cls;
    b.addEventListener('click', fn);
    return b;
  }
  function esc(s) { return String(s === null || s === undefined ? '' : s).replace(/[&<>"']/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]; }); }

  function render() {
    var s = Q.summary(store);
    ['queued', 'running'].forEach(function (k) { });
    var qn = el('queue-list'), dn = el('done-list');
    qn.innerHTML = ''; dn.innerHTML = '';
    store.items.filter(function (i) { return i.status !== 'done'; }).forEach(function (i) { qn.appendChild(itemNode(i)); });
    store.items.filter(function (i) { return i.status === 'done'; }).forEach(function (i) { dn.appendChild(itemNode(i)); });
    if (!qn.children.length) qn.innerHTML = '<p class="hint">Queue is empty. Accept the notice, then add an https URL.</p>';
    if (!dn.children.length) dn.innerHTML = '<p class="hint">Nothing has completed on this device yet. A transfer only appears here once the host confirmed it and, when a digest was published, verified it.</p>';
    el('counts').textContent = 'queued ' + s.queued + ' · running ' + s.running + ' · paused ' + s.paused +
      ' · done ' + s.done + (s.unverifiedDone ? ' (unverified ' + s.unverifiedDone + ')' : '') +
      ' · failed ' + s.failed + ' · blocked ' + s.blocked + ' · refused ' + store.counters.refused;
    el('sb-bytes').textContent = 'pending ' + Q.formatBytes(Q.bytesPending(store));
    el('sb-host').textContent = host.available ? 'host: reachable' : (host.checked ? 'host: NOT reachable (nothing transfers)' : 'host: probing…');
    var nb = el('notice-badge');
    var ok = Q.noticeSatisfied(store);
    nb.textContent = ok ? 'notice: accepted v' + Q.NOTICE_VERSION : 'notice: required';
    nb.className = 'badge ' + (ok ? 'ok' : 'warn');
  }

  /* ---------------- transports ---------------- */

  function probeHost() {
    var call = bridge();
    if (!call) { host = { available: false, checked: true }; return Promise.resolve(); }
    return call('download', 'status', {}).then(function (res) {
      var live = liveOnly(res);
      host.available = !!(live && live.available !== false);
      host.info = live || null;
      host.checked = true;
    }).catch(function () { host = { available: false, checked: true }; });
  }

  function startItem(item) {
    Q.start(item);
    var call = bridge();
    if (!call) { blockNoHost(item); return; }
    var payload = { id: item.id, url: item.url, name: item.name, sha256: item.sha256, bytes: item.bytes, resume_from: item.resumeFrom || 0 };
    call('download', 'start', payload).then(function (res) {
      var live = liveOnly(res);
      if (!live) { blockNoHost(item); render(); return; }
      if (live.status) item.status = live.status;
      if (typeof live.bytes_done === 'number') item.bytesDone = live.bytes_done;
      if (live.error) { Q.fail(item, live.error); }
      else if (live.sha256_ok === true) { Q.finish(item, item.sha256); }
      else { item.status = 'running'; }
      persist(); render();
      if (item.status === 'running') toast('Transfer started by the host for ' + item.name);
    }).catch(function (e) { Q.fail(item, 'host call failed: ' + (e && e.message ? e.message : e)); persist(); render(); });
  }

  function blockNoHost(item) {
    item.status = 'blocked';
    item.error = 'NO HOST: the Nuxel host did not answer download.start, so NOTHING was transferred. ' +
      'The queue item is kept so it can be started on the device.';
    persist(); render();
    toast('No host — nothing transferred');
  }

  /* ---------------- wiring ---------------- */

  function enqueue() {
    if (!Q.noticeSatisfied(store)) { toast('Accept the legal-use notice first'); return; }
    var res = Q.addItem(store, {
      url: el('add-url').value,
      name: el('add-name').value || null,
      sha256: el('add-sha').value || null,
      bytes: el('add-bytes').value ? Number(el('add-bytes').value) : null,
      addedAt: new Date().toISOString()
    });
    if (!res.ok) { el('add-error').textContent = 'Refused: ' + res.reason; toast('Refused — see the reason'); persist(); render(); return; }
    el('add-error').textContent = '';
    el('add-url').value = ''; el('add-name').value = ''; el('add-sha').value = ''; el('add-bytes').value = '';
    toast('Queued ' + res.item.name);
    persist(); render();
  }

  function tabs() {
    Array.prototype.forEach.call(document.querySelectorAll('.tab'), function (b) {
      b.addEventListener('click', function () {
        Array.prototype.forEach.call(document.querySelectorAll('.tab'), function (x) { x.classList.remove('active'); });
        Array.prototype.forEach.call(document.querySelectorAll('.panel'), function (x) { x.classList.remove('active'); });
        b.classList.add('active'); el('tab-' + b.dataset.tab).classList.add('active');
      });
    });
  }

  function renderLimits() {
    el('deny-list').textContent = Q.DENY_HOSTS.join(', ');
    el('limits-host').textContent = host.available
      ? 'reachable — transfers are performed by the host and their digests are re-checked here before an item is marked done'
      : (host.checked ? 'NOT reachable — the queue is local only and nothing is transferred' : 'probing…');
  }

  document.addEventListener('DOMContentLoaded', function () {
    restore(); tabs(); renderNotice(); render();
    el('accept-notice').addEventListener('click', function () {
      Q.acceptNotice(store); persist(); renderNotice(); render(); toast('Notice accepted (v' + Q.NOTICE_VERSION + ')'); renderLimits();
    });
    el('enqueue').addEventListener('click', enqueue);
    el('add-url').addEventListener('keydown', function (e) { if (e.key === 'Enter') enqueue(); });
    el('clear-done').addEventListener('click', function () {
      store.items = store.items.filter(function (i) { return i.status !== 'done'; }); persist(); render();
    });
    el('close').addEventListener('click', function () { try { window.close(); } catch (e) {} });
    probeHost().then(function () { render(); renderLimits(); });
  });
}());
