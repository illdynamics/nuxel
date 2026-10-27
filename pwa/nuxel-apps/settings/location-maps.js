// Nuxel Settings — Location & GPS + Maps diagnostics (PWNAGE 27000)
//
// This panel reads the SAME canonical provider status as the Location Quick
// Setting and edits the SAME maps configuration as pwa/nuxel-apps/maps.  It
// never creates a location, never reports a geocoding hit as a fix, and never
// pretends a tile source worked because a URL was saved.
(function () {
  'use strict';

  var C = window.NuxelMapsCore;
  var refreshTimer = null;

  function $(id) { return document.getElementById(id); }
  function bridge() {
    if (window.NuxelBridge && window.NuxelBridge.call) return window.NuxelBridge;
    try { if (window.parent && window.parent !== window && window.parent.NuxelBridge) return window.parent.NuxelBridge; } catch (e) {}
    return null;
  }
  function call(ns, verb, params) {
    var b = bridge();
    if (!b) return Promise.resolve({ success: false, state: 'unavailable', error: 'Nuxel bridge unavailable' });
    try { return Promise.resolve(b.call(ns, verb, params || {})); }
    catch (e) { return Promise.resolve({ success: false, state: 'unavailable', error: String(e && e.message || e) }); }
  }
  function fmtAge(seconds) {
    if (seconds === null || seconds === undefined || isNaN(seconds)) return 'no real fix recorded';
    if (seconds < 90) return Math.round(seconds) + ' s ago';
    if (seconds < 5400) return Math.round(seconds / 60) + ' min ago';
    return Math.round(seconds / 3600) + ' h ago';
  }

  function renderLocation(raw) {
    var now = Date.now() / 1000;
    var v = C ? C.providerView(raw, now) : { state: 'error', label: 'Maps core unavailable', fix: null };
    var lines = [
      'state          : ' + v.state + ' (' + v.label + ')',
      'provider       : ' + (v.provider || 'unknown'),
      'provider ready : ' + (v.providerReady ? 'yes' : 'no') +
        ' | installed: ' + (v.providerAvailable ? 'yes' : 'no'),
      'policy enabled : ' + (v.enabled ? 'yes' : 'no'),
      'last provider fix: ' + fmtAge(v.fix ? v.fix.ageSeconds : null) +
        (v.fix && typeof v.fix.accuracy === 'number' ? (' | accuracy ±' + Math.round(v.fix.accuracy) + ' m') : '') +
        ' | GNSS fix: ' + (raw && raw.gnss_fix === true ? 'yes' : 'no (provider data only)'),
      'freshness limit: ' + (raw && raw.freshness_seconds ? raw.freshness_seconds + ' s' : '60 s') +
        ' | stale after: ' + (raw && raw.stale_after_seconds ? raw.stale_after_seconds + ' s' : '600 s')
    ];
    if (v.detail) lines.push('detail         : ' + v.detail);
    if (v.lastError) lines.push('last error     : ' + v.lastError);
    var g = raw && raw.gnss;
    if (g) {
      lines.push('');
      lines.push('GNSS path:');
      lines.push('  nodes        : ' + ((g.nodes && g.nodes.length) ? g.nodes.join(', ') : 'none detected'));
      lines.push('  driver       : ' + (g.driver || 'unknown') + ' | bound: ' + (g.driver_bound ? 'yes' : 'no'));
      lines.push('  firmware     : ' + (g.firmware_present ? (g.firmware || []).join(', ') : 'missing'));
      lines.push('  fix support  : ' + (g.fix_supported ? 'reported by provider path' : 'not wired (no fix claimed)'));
      if (g.blocker) lines.push('  blocker      : ' + g.blocker);
    }
    var el = $('location-state');
    if (el) el.textContent = lines.join('\n');
    var detail = $('location-detail');
    if (detail) {
      detail.textContent = (v.state === 'fixed' && v.fix)
        ? 'Fresh provider fix. Accuracy and age are provider values; no GNSS or satellite count is fabricated.'
        : (v.state === 'disabled'
          ? 'Location is disabled by the global privacy/provider policy. Enable it with the Location Quick Setting.'
          : 'No current fix is being claimed. This panel shows the real provider state and blocker.');
    }
  }

  var bridgeTries = 0;
  function refreshLocation() {
    if (!bridge() && bridgeTries < 12) {
      bridgeTries++;
      setTimeout(refreshLocation, 300);
      return Promise.resolve(null);
    }
    bridgeTries = 0;
    return call('location', 'get-status', {}).then(function (st) {
      renderLocation(st || {});
      return st;
    });
  }

  function acquireLocation() {
    var el = $('location-state');
    if (el) el.textContent = 'Requesting provider acquisition (no fix is being claimed)…';
    function acquire() { return call('location', 'acquire', {}); }
    function consentThenAcquire(st) {
      if (!st || st.error_code !== 'CAPABILITY_DENIED') return st;
      return call('permissions', 'request', {
        capability: 'location:read', reason: 'Show current location provider diagnostics'
      }).then(function (grant) {
        if (grant === false || (grant && grant.granted === false)) {
          throw new Error('Location read permission denied');
        }
        return acquire();
      });
    }
    return acquire().then(consentThenAcquire).then(function (st) {
      renderLocation(st || {});
      if (!st || st.state !== 'fixed') {
        var detail = $('location-detail');
        if (detail) detail.textContent = 'Acquisition requested. Current state: ' +
          ((st && st.state) || 'unavailable') + '. No coordinate is shown until the provider supplies one.';
      }
      return st;
    }).catch(function (err) {
      var detail = $('location-detail');
      if (detail) detail.textContent = 'Fix acquisition refused: ' + (err && err.message ? err.message : err);
      renderLocation({ success: false, state: 'error', last_error: String(err && err.message || err) });
      return null;
    });
  }

  function mapsConfig() {
    return C ? C.loadConfig(window.localStorage) : null;
  }

  function renderMaps(config, extra) {
    var el = $('maps-state');
    if (!el || !C) return;
    var src = C.tileSourceView(config || mapsConfig());
    var lines = [
      'source      : ' + (src.name || 'none'),
      'template    : ' + (src.template || '(none)'),
      'status      : ' + src.status + (src.valid ? '' : (' — ' + (src.error || 'invalid'))),
      'online      : ' + (src.online ? 'enabled' : 'off (cache only)'),
      'attribution : ' + (src.attribution || 'none'),
      'settings    : ' + C.STORAGE_KEY + ' (shared with Maps)'
    ];
    if (extra) lines.push('last action : ' + extra);
    if (!src.valid) lines.push('error       : ' + src.error);
    el.textContent = lines.join('\n');
    var url = $('maps-tile-url');
    var net = $('maps-allow-net');
    if (url) url.value = src.template || '';
    if (net) net.checked = !!src.online;
  }

  function saveMaps() {
    if (!C) return;
    var url = ($('maps-tile-url') && $('maps-tile-url').value || '').trim();
    var allow = !!($('maps-allow-net') && $('maps-allow-net').checked);
    var check = C.validateTileTemplate(url);
    if (url && !check.ok) {
      renderMaps(mapsConfig(), 'not saved: ' + check.error);
      return;
    }
    var next = C.clone(mapsConfig() || C.DEFAULT_CONFIG);
    next.tileSource.template = url;
    next.tileSource.name = url ? 'Custom tile source' : 'No tile source';
    if (url && /openstreetmap\.org/i.test(url)) {
      next.tileSource.attribution = C.DEFAULT_TILE_SOURCE.attribution;
      next.tileSource.attributionUrl = C.DEFAULT_TILE_SOURCE.attributionUrl;
      next.tileSource.usagePolicyUrl = C.DEFAULT_TILE_SOURCE.usagePolicyUrl;
    }
    next.allowNet = allow;
    var saved = C.saveConfig(window.localStorage, next);
    renderMaps(saved.config, saved.ok ? 'saved; Maps picks it up on its next load' : ('save failed: ' + saved.error));
  }

  function restoreDefault() {
    if (!C) return;
    var saved = C.saveConfig(window.localStorage, C.DEFAULT_CONFIG);
    renderMaps(saved.config, 'restored attributed OpenStreetMap default');
  }

  function bind() {
    var refresh = $('location-refresh');
    var acquire = $('location-acquire');
    var mapsSave = $('maps-save');
    var mapsDefault = $('maps-default');
    var mapsRefresh = $('maps-refresh');
    if (refresh) refresh.addEventListener('click', refreshLocation);
    if (acquire) acquire.addEventListener('click', acquireLocation);
    if (mapsSave) mapsSave.addEventListener('click', saveMaps);
    if (mapsDefault) mapsDefault.addEventListener('click', restoreDefault);
    if (mapsRefresh) mapsRefresh.addEventListener('click', function () { renderMaps(mapsConfig(), 'checked'); });
    document.querySelectorAll('.tab').forEach(function (t) {
      t.addEventListener('click', function () {
        if (t.dataset.tab !== 'location') {
          if (refreshTimer) { clearInterval(refreshTimer); refreshTimer = null; }
          return;
        }
        refreshLocation();
        renderMaps(mapsConfig());
        if (refreshTimer) clearInterval(refreshTimer);
        refreshTimer = setInterval(refreshLocation, 8000);
      });
    });
    renderMaps(mapsConfig());
    refreshLocation();
  }

  window.nuxelLocationMaps = {
    refresh: refreshLocation,
    acquire: acquireLocation,
    saveMaps: saveMaps,
    restoreDefault: restoreDefault,
    mapsConfig: mapsConfig
  };

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', bind);
  else bind();
})();
