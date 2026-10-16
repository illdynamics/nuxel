// Safe Cleanup — preview-then-delete with a hard confirmation gate.
//
// The scan comes from the Nuxel bridge (`system.cleanup` with dryRun: true).  If
// no bridge is reachable the bundled snapshot is used and the UI says so, and
// the DELETE step is refused outright: a cleanup tool must never report freeing
// bytes it did not free.
(function () {
  'use strict';
  var C = window.CleanupPlan;
  var el = function (id) { return document.getElementById(id); };
  function esc(s) {
    return String(s === null || s === undefined ? '' : s)
      .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
  }
  function bridge() {
    if (window.NuxelBridge && typeof window.NuxelBridge.call === 'function') return window.NuxelBridge;
    return null;
  }

  var scan = null, plan = null, liveDelete = false;
  var logLines = [];

  function log(line) {
    logLines.push(new Date().toISOString() + '  ' + line);
    el('activity').textContent = logLines.slice(-40).join('\n');
  }

  async function runScan() {
    el('source-badge').textContent = 'scan: running…';
    var b = bridge(), res = null, source = 'sample';
    if (b) {
      try {
        res = await b.call('system', 'cleanup', { dryRun: true, allowlist: C.ALLOWLIST.map(function (a) { return a.path; }) });
        if (res && res.success !== false && Array.isArray(res.entries) && res.entries.length) {
          source = 'live'; liveDelete = true;
        }
      } catch (e) { res = null; }
    }
    if (!res || source !== 'live') {
      liveDelete = false;
      try {
        res = await (await fetch('js/sample-scan.json', { cache: 'force-cache' })).json();
      } catch (e) { res = { entries: [] }; }
      var note = el('source-note');
      note.className = 'note show';
      note.innerHTML = '<b>Sample scan.</b> The Nuxel host is not reachable, so this is the bundled scan ' +
        'snapshot. The dry run below is computed from it, and the delete step is disabled: ' +
        'a cleanup tool must not claim to have removed files it never touched.';
    } else {
      el('source-note').className = 'note';
    }
    scan = res;
    plan = C.plan(scan);
    render();
  }

  function render() {
    var live = scan.source === 'live';
    el('source-badge').textContent = 'scan: ' + (live ? 'live' : 'sample snapshot');
    el('source-badge').className = 'badge ' + (live ? 'live' : 'sample');
    el('total-bytes').textContent = plan.reclaimable;
    el('total-files').textContent = plan.totalFiles;
    el('total-dirs').textContent = plan.entries.length;
    el('total-skipped').textContent = plan.blocked;
    el('phrase-label').textContent = plan.confirmPhrase;
    el('sb-source').textContent = 'scan source: ' + plan.source + (live ? '' : ' (not a live device read)');
    el('sb-at').textContent = 'scanned at ' + (plan.scanned_at || '—');
    el('sb-allowlist').textContent = 'allowlist v' + plan.allowlist_version + ' · ' + C.ALLOWLIST.length + ' permitted paths';

    el('entries').innerHTML = '<table><thead><tr><th>Path</th><th>Kind</th><th class="num">Files</th>' +
      '<th class="num">Size</th><th>Risk</th></tr></thead><tbody>' +
      plan.entries.map(function (e) {
        return '<tr class="' + esc(e.risk) + '"><td>' + esc(e.path) + '<div class="consequence">' +
          esc(e.consequence) + '</div></td><td>' + esc(e.kind) + '</td><td class="num">' + e.files +
          '</td><td class="num">' + C.formatBytes(e.bytes) + '</td><td class="risk">' + esc(e.risk) + '</td></tr>';
      }).join('') + '</tbody></table>';

    el('skipped').innerHTML = plan.skipped.length ? plan.skipped.map(function (s) {
      return '<li>' + esc(s.path) + ' — ' + C.formatBytes(s.bytes) + ', ' + s.files + ' files — ' + esc(s.reason) + '</li>';
    }).join('') : '<li>Nothing outside the allowlist was seen by this scan.</li>';
    el('nevertouch').innerHTML = plan.neverTouch.map(function (n) {
      return '<li><b>' + esc(n.pattern) + '</b> — ' + esc(n.reason) + '</li>';
    }).join('');
    updateGate();
  }

  function updateGate() {
    var typed = el('confirm').value;
    var g = C.gate(typed, plan);
    var ready = g.ok && (liveDelete || false);
    el('execute').disabled = !ready;
    el('gate-reason').textContent = !g.ok ? g.reason
      : (!liveDelete ? 'Dry run is ready, but the Nuxel host is offline so delete is refused. ' +
          'Run this app on the handset (or with the host running) to perform the deletion.' : g.reason);
  }

  async function execute() {
    var g = C.gate(el('confirm').value, plan);
    if (!g.ok || !liveDelete) { updateGate(); return; }
    var b = bridge();
    var results = [];
    el('results').innerHTML = '<p class="hint">Deleting…</p>';
    for (var i = 0; i < plan.entries.length; i++) {
      var e = plan.entries[i];
      try {
        var res = await b.call('system', 'cleanup', { dryRun: false, path: e.path, confirm: plan.confirmPhrase });
        results.push({ path: e.path, ok: !!(res && res.success !== false),
                       bytes: (res && res.bytes) || e.bytes, files: e.files,
                       error: res && res.error });
      } catch (err) {
        results.push({ path: e.path, ok: false, error: String(err && err.message || err) });
      }
    }
    var summary = C.applyDelete(plan, results);
    el('results').innerHTML = '<h4>Result</h4><p class="results-ok">Freed ' + summary.freed +
      ' across ' + summary.removed.length + ' paths.</p>' +
      (summary.failed.length ? '<p class="results-bad">Failed: ' + summary.failed.map(function (f) {
        return esc(f.path) + ' (' + esc(f.error) + ')'; }).join('; ') + '</p>' : '');
    log('delete run: freed ' + summary.freed + ', ' + summary.removed.length + ' paths, ' +
        summary.failed.length + ' failures');
    el('confirm').value = '';
    await runScan();
  }

  el('rescan').addEventListener('click', runScan);
  el('preview').addEventListener('click', runScan);
  el('confirm').addEventListener('input', updateGate);
  el('execute').addEventListener('click', execute);
  el('cancel').addEventListener('click', function () {
    el('confirm').value = ''; el('results').innerHTML = ''; updateGate();
  });
  el('close').addEventListener('click', function () {
    var f = window.frameElement;
    if (f && window.parent !== window && window.parent.NuxelLauncherClose) window.parent.NuxelLauncherClose();
    else if (f && f.parentNode) f.parentNode.removeChild(f);
  });

  log('app opened; dry run only until the phrase is typed');
  runScan();
})();
