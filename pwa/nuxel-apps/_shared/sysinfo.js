// Nuxel shared system-information client (pwa/nuxel-apps/_shared/sysinfo.js)
//
// One place decides WHERE a power-user app gets its facts from, and it always
// tells the truth about that source:
//
//   live    — the Nuxel bridge/host answered `system.read` for the real path
//   sample  — the bridge is unreachable (VM, desktop browser, or a handset where
//             the host is not running) and the app is showing the bundled
//             snapshot under samples/.  The UI MUST label this.
//   denied  — the read was refused by policy/permission
//   error   — the read failed for another reason
//
// A power-user tool that silently shows invented hardware state is worse than no
// tool at all, so the source is part of every result and is rendered in the UI.
(function (root, factory) {
  if (typeof module === 'object' && module.exports) module.exports = factory(null);
  else root.NuxelSysInfo = factory(root);
}(typeof self !== 'undefined' ? self : this, function (g) {
  'use strict';

  var SAMPLE_URL = '../_shared/samples/sys-snapshot.json';
  var _sample = null;

  function bridge() {
    if (!g) return null;
    if (g.NuxelBridge && typeof g.NuxelBridge.call === 'function') return g.NuxelBridge;
    try { if (g.parent && g.parent !== g && g.parent.NuxelBridge) return g.parent.NuxelBridge; } catch (e) {}
    return null;
  }

  function host() {
    if (!g) return null;
    if (g.NuxelHost && g.NuxelHost.available) return g.NuxelHost;
    try { if (g.parent && g.parent !== g && g.parent.NuxelHost) return g.parent.NuxelHost; } catch (e) {}
    return null;
  }

  async function loadSample() {
    if (_sample) return _sample;
    try {
      var res = await fetch(SAMPLE_URL, { cache: 'force-cache' });
      if (!res.ok) return null;
      _sample = await res.json();
      return _sample;
    } catch (e) { return null; }
  }

  // Read one path.  Returns {ok, source, path, text, error}.
  async function read(path) {
    var b = bridge();
    if (b) {
      try {
        var res = await b.call('system', 'read', { path: path, mode: 'read-only' });
        if (res && res.success !== false && typeof res.text === 'string' && res.text.length) {
          return { ok: true, source: 'live', path: path, text: res.text };
        }
        if (res && res.denied) {
          return { ok: false, source: 'denied', path: path, error: res.error || 'permission denied by policy' };
        }
      } catch (e) { /* fall through to the sample snapshot */ }
    }
    var h = host();
    if (h) {
      try {
        var out = await h.statusRead(path);
        if (out && out.ok && out.text) return { ok: true, source: 'live', path: path, text: out.text };
      } catch (e) { /* fall through */ }
    }
    var s = await loadSample();
    if (s && s.files && typeof s.files[path] === 'string') {
      return { ok: true, source: 'sample', path: path, text: s.files[path],
               snapshot: { device: s.device, captured: s.captured, warning: s.warning } };
    }
    return { ok: false, source: 'error', path: path, error: 'path not available from any source' };
  }

  async function readMany(paths) {
    var out = {};
    for (var i = 0; i < paths.length; i++) {
      out[paths[i]] = await read(paths[i]);
    }
    return out;
  }

  function sourceLabel(results) {
    var sources = {};
    Object.keys(results || {}).forEach(function (k) { sources[results[k].source] = 1; });
    var keys = Object.keys(sources);
    if (!keys.length) return 'no data';
    return keys.sort().join(' + ');
  }

  return { read: read, readMany: readMany, loadSample: loadSample,
           sourceLabel: sourceLabel, SAMPLE_URL: SAMPLE_URL };
}));
