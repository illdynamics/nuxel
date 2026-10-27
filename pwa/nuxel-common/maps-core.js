/**
 * Nuxel Maps core (shared, dependency-free)
 *
 * One source of truth for the Maps configuration, tile-URL validation, pin
 * identity/deduplication, asynchronous search sequencing and provider-state
 * interpretation.  It is loaded as a classic script by the Maps app and the
 * Settings diagnostics page, and it is also require()-able from Node so the
 * offline unit tests exercise the same code the phone runs.
 *
 * This module never fetches anything and never invents a coordinate.  It only
 * describes what a caller should do with real provider/tile responses.
 */
(function (root, factory) {
  'use strict';
  if (typeof module === 'object' && module.exports) {
    module.exports = factory();
  } else {
    root.NuxelMapsCore = factory();
  }
})(typeof globalThis !== 'undefined' ? globalThis : this, function () {
  'use strict';

  var STORAGE_KEY = 'nuxel-maps-config';

  // The default is a real, attributed tile service.  It is deliberately a
  // template (not a hidden URL buried in rendering code) so Settings and the
  // Maps app edit the same configuration.  Requests stay limited to the visible
  // viewport; the app never prefetches or crawls.
  var DEFAULT_TILE_SOURCE = {
    id: 'osm-standard',
    name: 'OpenStreetMap standard',
    template: 'https://tile.openstreetmap.org/{z}/{x}/{y}.png',
    minZoom: 2,
    maxZoom: 19,
    tileSize: 256,
    attribution: '© OpenStreetMap contributors',
    attributionUrl: 'https://www.openstreetmap.org/copyright',
    usagePolicyUrl: 'https://operations.osmfoundation.org/policies/tiles/',
    requiresAttribution: true,
    online: true
  };

  // Geocoding is deliberately separate from tiles: a successful place search
  // proves only that Nominatim answered, never that tiles or GNSS work.
  var DEFAULT_GEOCODER = {
    id: 'nominatim',
    name: 'OpenStreetMap Nominatim',
    url: 'https://nominatim.openstreetmap.org/search',
    attribution: '© OpenStreetMap contributors',
    usagePolicyUrl: 'https://operations.osmfoundation.org/policies/nominatim/',
    limit: 6
  };

  var DEFAULT_CONFIG = {
    schema_version: 1,
    tileSource: DEFAULT_TILE_SOURCE,
    geocoder: DEFAULT_GEOCODER,
    allowNet: true,
    lastView: { lat: 52.3702, lon: 4.8952, zoom: 4 }
  };

  var PROVIDER_STATES = ['unavailable', 'disabled', 'searching', 'no_fix', 'stale', 'fixed', 'error'];

  function clone(value) {
    return JSON.parse(JSON.stringify(value));
  }

  function finiteNumber(value) {
    var n = typeof value === 'number' ? value : parseFloat(value);
    return isFinite(n) ? n : null;
  }

  function isHttpUrl(url) {
    return typeof url === 'string' && /^https?:\/\//i.test(url);
  }

  function hasTilePlaceholders(template) {
    return typeof template === 'string' &&
      template.indexOf('{z}') >= 0 && template.indexOf('{x}') >= 0 && template.indexOf('{y}') >= 0;
  }

  /** Validate a tile URL template.  Returns {ok, error, template}. */
  function validateTileTemplate(template) {
    var t = typeof template === 'string' ? template.trim() : '';
    if (!t) return { ok: false, error: 'tile source is empty', code: 'MISSING_TEMPLATE', template: '' };
    if (!isHttpUrl(t)) return { ok: false, error: 'only http(s) tile sources are accepted', code: 'INVALID_SCHEME', template: t };
    if (!hasTilePlaceholders(t)) {
      return { ok: false, error: 'tile source needs {z}, {x} and {y} placeholders', code: 'MISSING_PLACEHOLDERS', template: t };
    }
    if (/\{[^}]*\}/.test(t.replace(/\{(z|x|y|s)\}/g, ''))) {
      return { ok: false, error: 'tile source has an unknown placeholder', code: 'UNKNOWN_PLACEHOLDER', template: t };
    }
    return { ok: true, error: null, code: 'OK', template: t };
  }

  function normalizeTileSource(raw) {
    var src = Object.assign({}, DEFAULT_TILE_SOURCE, raw || {});
    src.template = typeof src.template === 'string' ? src.template.trim() : '';
    src.name = src.name || (src.template ? 'Custom tile source' : 'No tile source');
    src.minZoom = Math.max(0, Math.min(22, Math.round(finiteNumber(src.minZoom) === null ? 2 : finiteNumber(src.minZoom))));
    src.maxZoom = Math.max(src.minZoom, Math.min(22, Math.round(finiteNumber(src.maxZoom) === null ? 19 : finiteNumber(src.maxZoom))));
    src.tileSize = Math.max(64, Math.min(512, Math.round(finiteNumber(src.tileSize) === null ? 256 : finiteNumber(src.tileSize))));
    src.requiresAttribution = src.requiresAttribution !== false;
    return src;
  }

  function normalizeConfig(raw) {
    var doc = raw && typeof raw === 'object' ? raw : {};
    var out = {
      schema_version: 1,
      tileSource: normalizeTileSource(doc.tileSource || (doc.template ? { template: doc.template, name: 'Custom tile source' } : null)),
      geocoder: Object.assign({}, DEFAULT_GEOCODER, doc.geocoder || {}),
      allowNet: doc.allowNet === undefined ? true : !!doc.allowNet,
      lastView: Object.assign({}, DEFAULT_CONFIG.lastView, doc.lastView || {})
    };
    // Migrate the pre-27000 shape {template, allowNet} without losing a user's
    // deliberate "offline only" choice.
    if (!doc.tileSource && typeof doc.template === 'string') {
      out.tileSource = normalizeTileSource({ template: doc.template, name: 'Custom tile source' });
    }
    var v = out.lastView;
    v.lat = finiteNumber(v.lat);
    v.lon = finiteNumber(v.lon);
    v.zoom = finiteNumber(v.zoom);
    if (v.lat === null || v.lat < -85 || v.lat > 85) v.lat = DEFAULT_CONFIG.lastView.lat;
    if (v.lon === null || v.lon < -180 || v.lon > 180) v.lon = DEFAULT_CONFIG.lastView.lon;
    if (v.zoom === null || v.zoom < 0 || v.zoom > 22) v.zoom = DEFAULT_CONFIG.lastView.zoom;
    return out;
  }

  function loadConfig(storage) {
    var raw = null;
    try {
      raw = storage && storage.getItem ? storage.getItem(STORAGE_KEY) : null;
      if (raw) return normalizeConfig(JSON.parse(raw));
    } catch (e) { /* malformed user config falls back to the shipped default */ }
    return normalizeConfig(DEFAULT_CONFIG);
  }

  function saveConfig(storage, config) {
    var doc = normalizeConfig(config);
    try {
      if (storage && storage.setItem) storage.setItem(STORAGE_KEY, JSON.stringify(doc));
      return { ok: true, config: doc };
    } catch (e) {
      return { ok: false, error: String(e && e.message || e), config: doc };
    }
  }

  function tileUrl(template, z, x, y, subdomain) {
    var v = validateTileTemplate(template);
    if (!v.ok) return null;
    return v.template
      .replace(/\{z\}/g, String(z))
      .replace(/\{x\}/g, String(x))
      .replace(/\{y\}/g, String(y))
      .replace(/\{s\}/g, subdomain || 'a');
  }

  function tileKey(z, x, y) {
    return z + '/' + x + '/' + y;
  }

  function clamp(value, lo, hi) { return Math.max(lo, Math.min(hi, value)); }

  function wrapLon(lon) {
    var v = finiteNumber(lon);
    if (v === null) return null;
    while (v > 180) v -= 360;
    while (v < -180) v += 360;
    return v;
  }

  function validLatLon(lat, lon) {
    var la = finiteNumber(lat), lo = finiteNumber(lon);
    return la !== null && lo !== null && la >= -90 && la <= 90 && lo >= -180 && lo <= 180
      ? { lat: la, lon: lo } : null;
  }

  /* ---------------- pins: stable identity and deduplication ---------------- */

  function coordinateKey(lat, lon) {
    var p = validLatLon(lat, lon);
    if (!p) return null;
    return p.lat.toFixed(6) + ',' + p.lon.toFixed(6);
  }

  function pinIdentity(pin) {
    var label = String((pin && pin.label) || '').trim().toLowerCase().replace(/\s+/g, ' ');
    return coordinateKey(pin && pin.lat, pin && pin.lon) + '|' + label;
  }

  function dedupePins(pins) {
    var seen = Object.create(null);
    var out = [];
    (Array.isArray(pins) ? pins : []).forEach(function (pin) {
      var p = validLatLon(pin && pin.lat, pin && pin.lon);
      if (!p) return;
      var key = pinIdentity({ lat: p.lat, lon: p.lon, label: pin.label });
      if (seen[key]) return;
      seen[key] = true;
      out.push(Object.assign({}, pin, { lat: p.lat, lon: p.lon }));
    });
    return out;
  }

  /** Add a saved pin, refusing an uncontrolled duplicate. */
  function addPin(pins, pin) {
    var list = Array.isArray(pins) ? pins.slice() : [];
    var p = validLatLon(pin && pin.lat, pin && pin.lon);
    if (!p) return { pins: list, added: false, reason: 'invalid-coordinate' };
    var candidate = Object.assign({}, pin, { lat: p.lat, lon: p.lon });
    var key = pinIdentity(candidate);
    for (var i = 0; i < list.length; i++) {
      if (pinIdentity(list[i]) === key) {
        return { pins: list, added: false, reason: 'duplicate', duplicate: list[i] };
      }
    }
    list.push(candidate);
    return { pins: list, added: true, reason: 'added', pin: candidate };
  }

  /* ---------------- asynchronous place search ---------------- */

  function searchResultIdentity(item) {
    var lat = finiteNumber(item && item.lat), lon = finiteNumber(item && item.lon);
    if (lat === null || lon === null) return null;
    var ext = (item && (item.osm_type || item.type || '')) + ':' + (item && (item.osm_id || item.place_id || ''));
    return ext !== ':' ? ext : coordinateKey(lat, lon) + '|' + String(item.display_name || item.name || '').toLowerCase();
  }

  function normalizeSearchResults(results) {
    var seen = Object.create(null);
    var out = [];
    (Array.isArray(results) ? results : []).forEach(function (item) {
      var p = validLatLon(item && item.lat, item && item.lon);
      if (!p) return;
      var id = searchResultIdentity(item);
      if (!id || seen[id]) return;
      seen[id] = true;
      out.push({
        id: 'result-' + id,
        lat: p.lat,
        lon: p.lon,
        label: String(item.display_name || item.name || 'Place').split(',').slice(0, 4).join(',').trim(),
        displayName: String(item.display_name || ''),
        osmType: item.osm_type || null,
        osmId: item.osm_id || null
      });
    });
    return out;
  }

  function newSearchState() {
    return { seq: 0, status: 'idle', query: '', results: [], error: null, startedAt: null };
  }

  function beginSearch(state, query) {
    state = state || newSearchState();
    state.seq += 1;
    state.status = 'loading';
    state.query = String(query || '').trim();
    state.results = [];
    state.error = null;
    state.startedAt = Date.now();
    return state.seq;
  }

  /** Accept only the CURRENT request's results; late replies are discarded. */
  function acceptSearch(state, seq, results) {
    if (!state || seq !== state.seq) return { accepted: false, stale: true, results: [] };
    var normalized = normalizeSearchResults(results);
    state.results = normalized;
    state.status = normalized.length ? 'ok' : 'empty';
    state.error = null;
    return { accepted: true, stale: false, results: normalized };
  }

  function failSearch(state, seq, error) {
    if (!state || seq !== state.seq) return { accepted: false, stale: true };
    state.status = 'error';
    state.results = [];
    state.error = String(error && error.message ? error.message : error || 'search failed');
    return { accepted: true, stale: false };
  }

  /* ---------------- provider state (never a coordinate source) ---------------- */

  function normalizeProviderState(value) {
    var s = String(value || '').toLowerCase();
    return PROVIDER_STATES.indexOf(s) >= 0 ? s : null;
  }

  /**
   * Interpret a bridge LocationGetStatus response.  `now` is injectable so the
   * tests (and deterministic UI) use the same freshness policy.
   */
  function providerView(status, now, options) {
    options = options || {};
    var freshSeconds = finiteNumber(options.freshSeconds);
    var staleSeconds = finiteNumber(options.staleSeconds);
    if (freshSeconds === null) freshSeconds = 60;
    if (staleSeconds === null) staleSeconds = 600;
    now = finiteNumber(now) === null ? Date.now() / 1000 : now;
    var st = status && typeof status === 'object' ? status : {};
    var state = normalizeProviderState(st.state);
    var ts = finiteNumber(st.last_fix_timestamp);
    if (ts === null) ts = finiteNumber(st.fix_timestamp);
    if (ts !== null && ts > 1e12) ts = ts / 1000; // tolerate a millisecond timestamp
    var age = ts === null ? null : Math.max(0, now - ts);
    var lat = finiteNumber(st.latitude);
    var lon = finiteNumber(st.longitude);
    if (lat === null) lat = finiteNumber(st.last_fix_latitude);
    if (lon === null) lon = finiteNumber(st.last_fix_longitude);
    var hasCoord = validLatLon(lat, lon) !== null;
    var accuracy = finiteNumber(st.accuracy);

    if (!state) {
      if (st.enabled === false) state = 'disabled';
      else if (st.provider_ready !== true && st.provider_available !== true) state = 'unavailable';
      else if (st.last_error) state = 'error';
      else if (hasCoord && age !== null && age <= freshSeconds) state = 'fixed';
      else if (hasCoord && age !== null && age <= staleSeconds) state = 'stale';
      else if (hasCoord) state = 'stale';
      else state = 'no_fix';
    }

    // A state without real provider coordinates can never be a fix marker.
    if (!hasCoord && (state === 'fixed' || state === 'stale')) state = 'no_fix';
    if (state === 'fixed' && age !== null && age > freshSeconds) state = 'stale';

    var labels = {
      unavailable: 'provider unavailable',
      disabled: 'location off',
      searching: 'searching for a fix',
      no_fix: 'no fix',
      stale: 'last fix is stale',
      fixed: 'fresh provider fix',
      error: 'provider error'
    };
    var fix = null;
    if (hasCoord && (state === 'fixed' || state === 'stale')) {
      fix = {
        lat: lat, lon: lon, accuracy: accuracy,
        timestamp: ts, ageSeconds: age,
        source: st.fix_source || 'provider',
        kind: st.fix_kind || 'provider',
        gnss: st.gnss_fix === true,
        fresh: state === 'fixed',
        stale: state === 'stale'
      };
    }
    return {
      state: state,
      label: labels[state] || state,
      enabled: st.enabled === true,
      provider: st.provider || 'unknown',
      providerAvailable: st.provider_available === true,
      providerReady: st.provider_ready === true,
      searching: state === 'searching',
      fix: fix,
      lastError: st.last_error || null,
      detail: st.detail || st.provider_detail || null,
      gnss: st.gnss || null
    };
  }

  /* ---------------- tile diagnostics ---------------- */

  function tileSourceView(config, overrides) {
    var cfg = normalizeConfig(config);
    var src = cfg.tileSource;
    var valid = validateTileTemplate(src.template);
    var online = !!(overrides && overrides.allowNet !== undefined ? overrides.allowNet : cfg.allowNet);
    var view = {
      configured: !!src.template,
      valid: valid.ok,
      code: valid.code,
      error: valid.error,
      name: src.name,
      template: src.template,
      attribution: src.attribution,
      attributionUrl: src.attributionUrl,
      online: online,
      status: !src.template ? 'no-source' : (!valid.ok ? 'invalid-source' : (online ? 'online' : 'cached-only'))
    };
    return Object.assign(view, overrides || {});
  }

  function describeTileFailure(error) {
    if (!error) return { code: 'UNKNOWN', message: 'tile request failed' };
    if (error.name === 'AbortError' || error.code === 'TIMEOUT') {
      return { code: 'TIMEOUT', message: 'tile request timed out' };
    }
    if (error.status) {
      return { code: 'HTTP_' + error.status, message: 'tile server returned HTTP ' + error.status };
    }
    if (error.name === 'TypeError' || /fetch|network|failed/i.test(String(error.message || ''))) {
      return { code: 'NETWORK', message: 'network unavailable or tile request blocked' };
    }
    return { code: error.code || 'REQUEST_FAILED', message: String(error.message || error) };
  }

  /**
   * Classify the outcome of a tile lookup.  `cached` is a truthy decoded image
   * or a cache hit; `allowNet` says whether an online fallback is permitted.
   */
  function tileOutcome(cached, allowNet, error) {
    if (cached) return { status: 'cached', source: 'cache', message: 'tile loaded from offline cache' };
    if (!allowNet) return { status: 'offline-miss', source: 'none', message: 'tile is not cached and online downloads are off' };
    if (error) return Object.assign({ status: 'error', source: 'network' }, describeTileFailure(error));
    return { status: 'missing', source: 'network', message: 'tile is not cached; requesting it online' };
  }

  function labelFrame(x, y, width, height, textWidth, textHeight) {
    var w = Math.max(0, width), h = Math.max(0, height);
    var left = clamp(x, 4, Math.max(4, w - textWidth - 6));
    var top = clamp(y, 4, Math.max(4, h - textHeight - 4));
    return { x: left, y: top, width: textWidth, height: textHeight, clipped: left !== x || top !== y };
  }

  function providerSummary(view, now) {
    if (!view) return 'Location provider unavailable';
    if (view.state === 'disabled') return 'Location is off (privacy policy)';
    if (view.state === 'unavailable') return 'Location provider unavailable' + (view.detail ? ': ' + view.detail : '');
    if (view.state === 'error') return 'Location provider error' + (view.lastError ? ': ' + view.lastError : '');
    if (view.state === 'fixed' && view.fix) {
      return 'Fresh provider fix, ' + (view.fix.accuracy === null ? 'accuracy unknown' : '±' + Math.round(view.fix.accuracy) + ' m') +
        ', age ' + Math.round(view.fix.ageSeconds) + ' s';
    }
    if (view.state === 'stale' && view.fix) {
      return view.fix.ageSeconds === null ? 'Stale fix (provider timestamp unavailable)'
        : 'Stale fix, age ' + Math.round(view.fix.ageSeconds) + ' s';
    }
    if (view.state === 'searching') return 'Searching for a fix (provider acquisition requested)';
    return 'No fix';
  }

  return {
    STORAGE_KEY: STORAGE_KEY,
    DEFAULT_CONFIG: DEFAULT_CONFIG,
    DEFAULT_TILE_SOURCE: DEFAULT_TILE_SOURCE,
    DEFAULT_GEOCODER: DEFAULT_GEOCODER,
    PROVIDER_STATES: PROVIDER_STATES,
    clone: clone,
    finiteNumber: finiteNumber,
    isHttpUrl: isHttpUrl,
    validateTileTemplate: validateTileTemplate,
    normalizeTileSource: normalizeTileSource,
    normalizeConfig: normalizeConfig,
    loadConfig: loadConfig,
    saveConfig: saveConfig,
    tileUrl: tileUrl,
    tileKey: tileKey,
    validLatLon: validLatLon,
    wrapLon: wrapLon,
    coordinateKey: coordinateKey,
    pinIdentity: pinIdentity,
    dedupePins: dedupePins,
    addPin: addPin,
    searchResultIdentity: searchResultIdentity,
    normalizeSearchResults: normalizeSearchResults,
    newSearchState: newSearchState,
    beginSearch: beginSearch,
    acceptSearch: acceptSearch,
    failSearch: failSearch,
    providerView: providerView,
    providerSummary: providerSummary,
    tileSourceView: tileSourceView,
    describeTileFailure: describeTileFailure,
    tileOutcome: tileOutcome,
    labelFrame: labelFrame
  };
});
