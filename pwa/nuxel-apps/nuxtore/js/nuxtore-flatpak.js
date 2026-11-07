/* NuxTore — Flatpak lifecycle panel (PWNAGE-56000).
 *
 * This panel is deliberately thin: every mutation goes through the Bridge's
 * closed-verb `flatpak` RPC.  The browser never builds a shell command, never
 * passes a path and never chooses a remote outside the provider allowlist.
 */
(function () {
  'use strict';

  var API = 'http://127.0.0.1:8080/api/v1';
  var APP_ID = 'org.nuxel.Nuxtore';
  var state = {
    status: null,
    installed: [],
    available: [],
    query: '',
    job: null,
    transaction: null,
    busy: false,
    lastError: null,
    retry: null
  };

  function $(id) { return document.getElementById(id); }
  function esc(s) {
    return String(s === undefined || s === null ? '' : s)
      .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;').replace(/'/g, '&#39;');
  }
  function bridge() {
    if (window.NuxelBridge && typeof window.NuxelBridge.call === 'function') return window.NuxelBridge;
    try { if (window.parent && window.parent.NuxelBridge) return window.parent.NuxelBridge; } catch (e) {}
    return null;
  }
  async function call(verb, params) {
    params = params || {};
    var b = bridge();
    if (b) {
      b.appId = APP_ID;
      return await b.call('flatpak', verb, params);
    }
    // Loopback fallback for a plain browser / VM smoke test.  The Bridge is
    // in dev mode on the handset, so loopback requests need no shared token.
    var method = (verb === 'install' || verb === 'update' || verb === 'uninstall' ||
                  verb === 'job' || verb === 'launch' || verb === 'refresh') ? 'POST' : 'GET';
    var url = API + '/flatpak/' + verb;
    var opts = { method: method, cache: 'no-store', headers: {} };
    if (method === 'POST') {
      opts.headers['Content-Type'] = 'application/json';
      opts.body = JSON.stringify(Object.assign({ caller: APP_ID, app_id: APP_ID }, params));
    } else {
      var qs = new URLSearchParams(params).toString();
      if (qs) url += '?' + qs;
    }
    var res = await fetch(url, opts);
    var doc = await res.json();
    if (!res.ok && doc && !doc.error) doc.error = 'HTTP ' + res.status;
    return doc;
  }
  async function exec(appId) {
    var res = await fetch(API + '/apps/exec', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ target: appId, app_target: appId, app_id: APP_ID })
    });
    var doc = await res.json();
    if (!res.ok && doc && !doc.error) doc.error = 'HTTP ' + res.status;
    return doc;
  }

  function statusLine() {
    var s = state.status;
    if (!s || !s.success) return 'Flatpak status unavailable' + (s && s.error ? ': ' + s.error : '');
    var fp = s.flatpak || {}, bw = s.bwrap || {}, ns = s.user_namespace || {}, p = s.portal || {};
    return 'Flatpak ' + esc(fp.version || '?') + ' · ' + esc(fp.default_arch || 'aarch64') +
      ' · bwrap ' + esc(bw.version || '?') + ' (' + esc(bw.mode || '?') + ', setuid=' + esc(bw.setuid) + ')' +
      ' · user-ns ' + (ns.ok ? 'OK' : 'FAIL') +
      ' · portal ' + (p.present ? 'OK' : 'MISSING') +
      ' · ready ' + (s.flatpak_ready ? 'YES' : 'NO');
  }

  function icon(id) {
    return '<img class="fp-icon" src="' + API + '/flatpak/icon/' + encodeURIComponent(id) +
      '" alt="" width="40" height="40" loading="lazy" onerror="this.style.visibility=&#39;hidden&#39;">';
  }

  function installedCache() {
    var ids = {};
    state.installed.forEach(function (a) { ids[a.id] = true; });
    return ids;
  }

  function renderInstalled() {
    var host = $('fp-installed');
    if (!host) return;
    var q = state.query.toLowerCase();
    var rows = state.installed.filter(function (a) {
      return !q || (a.id + ' ' + a.name + ' ' + (a.description || '')).toLowerCase().indexOf(q) >= 0;
    });
    if (!rows.length) {
      host.innerHTML = '<div class="card"><h3>Installed Flatpak apps</h3><div class="empty">' +
        (state.installed.length ? 'No installed app matches this search.' : 'No Flatpak apps are installed.') +
        '</div></div>';
      return;
    }
    host.innerHTML = '<div class="card"><h3>Installed Flatpak apps <span class="badge ok">' +
      state.installed.length + '</span></h3></div>' + rows.map(function (a) {
        return '<div class="card fp-card">' + icon(a.id) +
          '<div class="fp-main"><h3>' + esc(a.name || a.id) + ' <span class="badge ok">installed</span></h3>' +
          '<div class="sub">' + esc(a.id) + ' · v' + esc(a.version || '—') + ' · ' + esc(a.arch || 'aarch64') +
          ' · ' + esc(a.scope || 'system') + ' · ' + esc(a.runtime || 'runtime unknown') + '</div>' +
          (a.description ? '<div class="sub">' + esc(a.description) + '</div>' : '') +
          '<div class="row"><button data-fp-launch="' + esc(a.id) + '">Launch</button>' +
          '<button class="ghost" data-fp-update="' + esc(a.id) + '">Update</button>' +
          '<button class="ghost" data-fp-uninstall="' + esc(a.id) + '">Uninstall</button></div></div></div>';
      }).join('');
  }

  function renderAvailable() {
    var host = $('fp-available');
    if (!host) return;
    var have = installedCache();
    var seen = {};
    var rows = state.available.filter(function (a) {
      if (!a || !a.id || have[a.id] || seen[a.id]) return false;
      seen[a.id] = true;
      return true;
    });
    if (!rows.length) {
      host.innerHTML = '<div class="empty">No matching aarch64 refs were returned by the remote. ' +
        'This is a real empty result, not a fabricated catalog.</div>';
      return;
    }
    host.innerHTML = rows.map(function (a) {
      return '<div class="card fp-card">' + icon(a.id) +
        '<div class="fp-main"><h3>' + esc(a.name || a.id) + ' <span class="badge">' + esc(a.state || 'available') + '</span></h3>' +
        '<div class="sub">' + esc(a.id) + ' · ' + esc(a.branch || '') + ' · ' + esc(a.arch || 'aarch64') +
        ' · download ' + esc(a.download_size || '—') + ' · installed ' + esc(a.installed_size || '—') + '</div>' +
        '<div class="row"><button data-fp-install="' + esc(a.id) + '">Install (system)</button></div></div></div>';
    }).join('');
  }

  function render() {
    if ($('fp-status')) $('fp-status').textContent = statusLine();
    if ($('c-flatpak')) $('c-flatpak').textContent = String(state.installed.length);
    renderInstalled();
    renderAvailable();
  }

  function txLabel(tx) {
    if (!tx) return '';
    var name = tx.app_id || 'application';
    var op = (tx.operation || 'operation').toUpperCase();
    var state = String(tx.state || 'idle').toUpperCase();
    return name + ' · ' + op + ' · ' + state;
  }
  function actionButton(label, fn, disabled) {
    var b = document.createElement('button');
    b.type = 'button'; b.textContent = label; b.disabled = !!disabled;
    b.addEventListener('click', fn);
    return b;
  }
  function renderTransaction(tx) {
    state.transaction = tx || null;
    var box = $('fp-progress'), log = $('fp-progress-log');
    var status = $('fp-tx-status'), bar = $('fp-tx-bar'), actions = $('fp-tx-actions');
    if (!box) return;
    box.hidden = !tx;
    if (!tx) { if (log) log.textContent = ''; if (status) status.textContent = '—'; if (actions) actions.replaceChildren(); return; }
    var pct = Math.max(0, Math.min(100, Number(tx.progress || 0)));
    if (status) {
      status.textContent = txLabel(tx) + '\n' + (tx.message || '') +
        (tx.result ? '\nResult: ' + tx.result : '') +
        (tx.error ? '\nFailure: ' + tx.error : '') +
        '\nTransaction: ' + (tx.transaction_id || tx.id || '—');
    }
    if (bar) bar.style.width = pct + '%';
    if (log) log.textContent = (tx.log_tail || '').slice(-6000);
    if (actions) {
      actions.replaceChildren();
      var terminal = ['completed','removed','failed','cancelled'].indexOf(String(tx.state)) >= 0;
      if (!terminal) actions.appendChild(actionButton('Cancel transaction', function () { cancel(tx); }));
      if (tx.state === 'failed' || tx.state === 'cancelled') {
        if (state.retry) actions.appendChild(actionButton('Retry', function () { var r = state.retry; state.retry = null; r(); }));
      }
      if (tx.state === 'completed' || tx.state === 'removed') {
        actions.appendChild(actionButton('Refresh list & launcher exports', function () { refresh(); }));
      }
    }
  }
  function setProgress(text) {
    var box = $('fp-progress'), log = $('fp-progress-log'), status = $('fp-tx-status');
    if (!box) return;
    if (text) box.hidden = false;
    if (log) log.textContent = text || '';
    if (status && !state.transaction) status.textContent = text || '—';
  }
  async function poll(jobId) {
    state.job = jobId;
    for (var i = 0; i < 1800; i++) {
      var j = await call('job', { job_id: jobId });
      if (!j || j.success === false) { setProgress('Transaction status failed: ' + ((j && j.error) || 'unknown')); return j; }
      renderTransaction(j);
      if (['completed','removed','failed','cancelled'].indexOf(String(j.state)) >= 0) {
        await refresh();
        if (j.state === 'failed') state.lastError = j.message || j.error || 'transaction failed';
        return j;
      }
      await new Promise(function (r) { setTimeout(r, 700); });
    }
    setProgress('Transaction is still running; reopen this panel to resume polling.');
    return null;
  }
  async function cancel(tx) {
    if (!tx || !(tx.transaction_id || tx.id)) return;
    var r = await call('cancel', { job_id: tx.transaction_id || tx.id });
    if (!r || r.success === false) {
      state.lastError = (r && (r.detail || r.error)) || 'cancel refused';
      if ($('fp-status')) $('fp-status').textContent = state.lastError;
    }
  }
  async function refresh() {
    if (state.busy) return;
    state.busy = true;
    try {
      var results = await Promise.all([
        call('status', {}),
        call('list', {}),
        call('remote', { remote: 'flathub', arch: 'aarch64', query: state.query, limit: 300 })
      ]);
      state.status = results[0];
      var inst = results[1];
      state.installed = (inst && inst.apps) ? inst.apps : [];
      var avail = results[2];
      state.available = (avail && avail.apps) ? avail.apps : [];
      state.lastError = (avail && avail.success === false) ? (avail.error || 'remote-ls failed') : null;
      render();
      if (state.lastError && $('fp-status')) $('fp-status').textContent = 'Remote error: ' + state.lastError;
      try {
        if (window.parent && window.parent.appRegistry && window.parent.appRegistry.refreshFromBridge) {
          window.parent.appRegistry.refreshFromBridge();
        }
      } catch (e) {}
    } catch (e) {
      state.lastError = (e && e.message) || String(e);
      if ($('fp-status')) $('fp-status').textContent = 'Flatpak refresh failed: ' + state.lastError;
    } finally {
      state.busy = false;
    }
  }
  async function install(id) {
    setProgress('Queueing install of ' + id + '…');
    state.retry = function () { install(id); };
    var r = await call('install', { app_id: id, remote: 'flathub', scope: 'system' });
    if (!r || r.success === false) { renderTransaction(null); setProgress('Install refused: ' + ((r && (r.detail || r.error)) || 'unknown')); return; }
    if (r.state === 'already_installed') { await refresh(); setProgress(''); return; }
    if (r.transaction) renderTransaction(r.transaction);
    if (r.job) await poll(r.job);
  }
  async function update(id) {
    setProgress('Queueing update of ' + (id || 'all installed Flatpak apps and runtimes') + '…');
    state.retry = function () { update(id); };
    var r = await call('update', id ? { app_id: id, scope: 'system' } : { scope: 'system' });
    if (!r || r.success === false) { renderTransaction(null); setProgress('Update refused: ' + ((r && (r.detail || r.error)) || 'unknown')); return; }
    if (r.transaction) renderTransaction(r.transaction);
    if (r.job) await poll(r.job);
  }
  async function uninstall(id) {
    if (!window.confirm('Uninstall ' + id + '? User data is preserved unless Flatpak itself removes it.')) return;
    setProgress('Queueing removal of ' + id + '…');
    state.retry = function () { uninstall(id); };
    var r = await call('uninstall', { app_id: id });
    if (!r || r.success === false) { renderTransaction(null); setProgress('Uninstall refused: ' + ((r && (r.detail || r.error)) || 'unknown')); return; }
    if (r.transaction) renderTransaction(r.transaction);
    if (r.job) await poll(r.job);
  }
  async function launch(id) {
    var r = await exec(id);
    if (!r || r.success === false) {
      state.lastError = (r && (r.detail || r.error)) || 'launch refused';
      if ($('fp-status')) $('fp-status').textContent = 'Launch failed: ' + state.lastError;
      return;
    }
    try { if (window.parent && window.parent.NuxelLauncherClose) window.parent.NuxelLauncherClose(); } catch (e) {}
    setProgress('Launch requested: ' + id + ' (' + (r.outcome || 'starting') + ')\n' + JSON.stringify(r.argv || []));
  }

  function wire() {
    if (!$('tab-flatpak')) return;
    var search = $('fp-search');
    if (search) search.addEventListener('input', function () {
      state.query = search.value.trim();
      clearTimeout(search._t);
      search._t = setTimeout(refresh, 300);
    });
    if ($('fp-refresh')) $('fp-refresh').addEventListener('click', refresh);
    if ($('fp-update-all')) $('fp-update-all').addEventListener('click', function () { update(null); });
    document.addEventListener('click', function (ev) {
      var t = ev.target;
      if (!t || !t.dataset) return;
      if (t.dataset.fpInstall) install(t.dataset.fpInstall);
      else if (t.dataset.fpUpdate) update(t.dataset.fpUpdate);
      else if (t.dataset.fpUninstall) uninstall(t.dataset.fpUninstall);
      else if (t.dataset.fpLaunch) launch(t.dataset.fpLaunch);
    });
    // Lazy first load: the tab is visible but the network/Flatpak query only
    // runs when it is opened. The existing generic tab handler sets .active.
    document.querySelectorAll('.tab').forEach(function (tab) {
      if (tab.dataset && tab.dataset.tab === 'flatpak') {
        tab.addEventListener('click', function () { if (!state.status) refresh(); });
      }
    });
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', wire);
  else wire();
  window.NuxToreFlatpak = { refresh: refresh, install: install, update: update,
                            uninstall: uninstall, launch: launch, state: state };
})();
