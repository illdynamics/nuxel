#!/usr/bin/env node
'use strict';
// Offline unit tests for the shared Maps core (no browser, no network, no phone).
import assert from 'node:assert';
import '../../pwa/nuxel-common/maps-core.js';
const C = globalThis.NuxelMapsCore;

let pass = 0, fail = 0;
function test(name, fn) {
  try { fn(); pass++; console.log('PASS ' + name); }
  catch (e) { fail++; console.log('FAIL ' + name + ' — ' + (e && e.stack || e)); }
}

test('default tile source is valid, HTTPS and attributed OSM', () => {
  const v = C.validateTileTemplate(C.DEFAULT_TILE_SOURCE.template);
  assert.strictEqual(v.ok, true);
  assert.ok(/^https:\/\//.test(C.DEFAULT_TILE_SOURCE.template));
  assert.ok(/OpenStreetMap/.test(C.DEFAULT_TILE_SOURCE.attribution));
  assert.ok(/openstreetmap\.org/.test(C.DEFAULT_TILE_SOURCE.attributionUrl));
});

test('missing, invalid scheme and missing placeholders are rejected with codes', () => {
  assert.strictEqual(C.validateTileTemplate('').code, 'MISSING_TEMPLATE');
  assert.strictEqual(C.validateTileTemplate('ftp://x/{z}/{x}/{y}.png').code, 'INVALID_SCHEME');
  assert.strictEqual(C.validateTileTemplate('https://x/tile.png').code, 'MISSING_PLACEHOLDERS');
  assert.strictEqual(C.validateTileTemplate('https://x/{z}/{x}/{y}/{q}.png').code, 'UNKNOWN_PLACEHOLDER');
});

test('tile URL substitution and cache key', () => {
  assert.strictEqual(C.tileUrl('https://x/{z}/{x}/{y}.png', 4, 8, 5), 'https://x/4/8/5.png');
  assert.strictEqual(C.tileKey(4, 8, 5), '4/8/5');
  assert.strictEqual(C.tileUrl('bad', 4, 8, 5), null);
});

test('legacy config migrates without losing offline-only choice', () => {
  const cfg = C.normalizeConfig({ template: 'https://x/{z}/{x}/{y}.png', allowNet: false });
  assert.strictEqual(cfg.tileSource.template, 'https://x/{z}/{x}/{y}.png');
  assert.strictEqual(cfg.allowNet, false);
});

test('default config enables the valid OSM source', () => {
  const cfg = C.normalizeConfig({});
  assert.ok(/openstreetmap/.test(cfg.tileSource.template));
  assert.strictEqual(cfg.allowNet, true);
});

test('tile outcomes distinguish cache, offline miss, HTTP error and network error', () => {
  assert.strictEqual(C.tileOutcome({ fake: true }, true).status, 'cached');
  assert.strictEqual(C.tileOutcome(null, false).status, 'offline-miss');
  const http = new Error('HTTP 503'); http.status = 503;
  assert.strictEqual(C.tileOutcome(null, true, http).status, 'error');
  assert.strictEqual(C.tileOutcome(null, true, http).code, 'HTTP_503');
  assert.strictEqual(C.tileOutcome(null, true, new TypeError('Failed to fetch')).code, 'NETWORK');
  const abort = new Error('aborted'); abort.name = 'AbortError';
  assert.strictEqual(C.tileOutcome(null, true, abort).code, 'TIMEOUT');
});

test('tile source view reports missing and invalid configuration', () => {
  const missing = C.tileSourceView({ tileSource: { template: '' }, allowNet: true });
  assert.strictEqual(missing.status, 'no-source');
  assert.strictEqual(missing.valid, false);
  const invalid = C.tileSourceView({ tileSource: { template: 'https://x/tile.png' }, allowNet: true });
  assert.strictEqual(invalid.status, 'invalid-source');
  const cached = C.tileSourceView(C.DEFAULT_CONFIG, { allowNet: false });
  assert.strictEqual(cached.status, 'cached-only');
});

test('provider states are distinct and never inferred from a coordinate alone', () => {
  const now = 1000;
  assert.strictEqual(C.providerView({ enabled: false }, now).state, 'disabled');
  assert.strictEqual(C.providerView({ enabled: true, provider_ready: false, provider_available: false }, now).state, 'unavailable');
  assert.strictEqual(C.providerView({ enabled: true, provider_ready: true, state: 'searching' }, now).state, 'searching');
  assert.strictEqual(C.providerView({ enabled: true, provider_ready: true }, now).state, 'no_fix');
  assert.strictEqual(C.providerView({ enabled: true, provider_ready: true, state: 'error', last_error: 'boom' }, now).state, 'error');
  assert.strictEqual(C.providerView({ enabled: true, provider_ready: true, latitude: 1, longitude: 2, last_fix_timestamp: now - 100 }, now).state, 'stale');
  assert.strictEqual(C.providerView({ enabled: true, provider_ready: true, latitude: 1, longitude: 2, last_fix_timestamp: now - 5 }, now).state, 'fixed');
  const noTimestamp = C.providerView({ enabled: true, provider_ready: true, latitude: 1, longitude: 2 }, now);
  assert.strictEqual(noTimestamp.state, 'stale');
  assert.strictEqual(noTimestamp.fix.fresh, false);
});

test('fixed requires a real validity window; stale is not fresh', () => {
  const now = 2000;
  const v = C.providerView({ enabled: true, provider_ready: true, latitude: 52, longitude: 4, last_fix_timestamp: now - 120 }, now, { freshSeconds: 60, staleSeconds: 600 });
  assert.strictEqual(v.state, 'stale');
  assert.strictEqual(v.fix.fresh, false);
  assert.strictEqual(v.fix.stale, true);
});

test('invalid coordinates cannot become a fix marker', () => {
  const v = C.providerView({ enabled: true, provider_ready: true, state: 'fixed', latitude: 999, longitude: 4, last_fix_timestamp: 1 }, 2);
  assert.strictEqual(v.state, 'no_fix');
  assert.strictEqual(v.fix, null);
});

test('search results are transient and de-duplicated', () => {
  const results = C.normalizeSearchResults([
    { lat: '52.1', lon: '4.2', display_name: 'Eindhoven, NL', osm_type: 'node', osm_id: 1 },
    { lat: '52.1', lon: '4.2', display_name: 'Eindhoven, NL', osm_type: 'node', osm_id: 1 },
    { lat: 'bad', lon: '4.2', display_name: 'Broken' }
  ]);
  assert.strictEqual(results.length, 1);
  assert.strictEqual(results[0].label.split(',')[0], 'Eindhoven');
});

test('repeated identical searches replace, never append, search results', () => {
  const s = C.newSearchState();
  const seq1 = C.beginSearch(s, 'Eindhoven');
  let r = C.acceptSearch(s, seq1, [{ lat: 52.1, lon: 4.2, display_name: 'Eindhoven' }]);
  assert.strictEqual(r.results.length, 1);
  const seq2 = C.beginSearch(s, 'Eindhoven');
  r = C.acceptSearch(s, seq2, [{ lat: 52.1, lon: 4.2, display_name: 'Eindhoven' }]);
  assert.strictEqual(s.results.length, 1);
});

test('late asynchronous search responses are discarded', () => {
  const s = C.newSearchState();
  const oldSeq = C.beginSearch(s, 'old');
  const newSeq = C.beginSearch(s, 'new');
  const late = C.acceptSearch(s, oldSeq, [{ lat: 1, lon: 2, display_name: 'Old' }]);
  assert.strictEqual(late.accepted, false);
  assert.strictEqual(s.results.length, 0);
  const good = C.acceptSearch(s, newSeq, [{ lat: 3, lon: 4, display_name: 'New' }]);
  assert.strictEqual(good.accepted, true);
  assert.strictEqual(s.results[0].label, 'New');
});

test('saved pins reject exact duplicates and invalid coordinates', () => {
  let r = C.addPin([], { lat: 52.1, lon: 4.2, label: 'Home' });
  assert.strictEqual(r.added, true);
  r = C.addPin(r.pins, { lat: 52.1, lon: 4.2, label: 'Home' });
  assert.strictEqual(r.added, false);
  assert.strictEqual(r.reason, 'duplicate');
  r = C.addPin(r.pins, { lat: 100, lon: 4.2, label: 'Bad' });
  assert.strictEqual(r.added, false);
  assert.strictEqual(r.reason, 'invalid-coordinate');
});

test('duplicate display pins are de-duplicated without mutating input', () => {
  const input = [
    { id: 'a', lat: 1, lon: 2, label: 'same' },
    { id: 'b', lat: 1, lon: 2, label: 'same' },
    { id: 'c', lat: 1, lon: 2, label: 'other' }
  ];
  const out = C.dedupePins(input);
  assert.strictEqual(out.length, 2);
  assert.strictEqual(input.length, 3);
});

test('labels are clamped inside the viewport', () => {
  const f = C.labelFrame(350, 290, 320, 200, 80, 14);
  assert.ok(f.x >= 4 && f.x + f.width <= 320);
  assert.ok(f.y >= 4 && f.y + f.height <= 200);
  assert.strictEqual(f.clipped, true);
});

test('a fresh provider summary reports accuracy and age without satellites', () => {
  const v = C.providerView({ enabled: true, provider_ready: true, latitude: 1, longitude: 2, accuracy: 12, last_fix_timestamp: 100 }, 120);
  const text = C.providerSummary(v, 120);
  assert.ok(/Fresh provider fix/.test(text));
  assert.ok(/12 m/.test(text));
  assert.ok(!/satellite/i.test(text));
});

console.log('\n' + (fail ? fail + ' FAILURE(S)' : 'ALL PASS') + ' (' + pass + ' passed)');
process.exit(fail ? 1 : 0);
