#!/usr/bin/env node
'use strict';
/* PWNAGE-42000: geolocation shim correctness tests (no browser required). */
const assert = require('node:assert');
const path = require('node:path');

let fail = 0;
function check(name, fn) {
  try { fn(); console.log('PASS ' + name); }
  catch (e) { fail++; console.log('FAIL ' + name + ' — ' + (e && e.stack || e)); }
}
function eq(a, b, msg) { assert.strictEqual(a, b, msg); }
function ok(v, msg) { assert.ok(v, msg); }

const calls = [];
let response = null;
const fakeBridge = {
  call(ns, verb, params) {
    calls.push({ ns, verb, params });
    if (verb === 'stop') return Promise.resolve({ success: true });
    if (typeof response === 'function') return Promise.resolve(response(ns, verb, params));
    return Promise.resolve(response || { success: false, error_code: 'PROVIDER_UNAVAILABLE',
      error: 'no provider' });
  },
};
globalThis.NuxelBridge = fakeBridge;
globalThis.document = new EventTarget();

require(path.join(__dirname, '..', '..', 'pwa', 'nuxel-common', 'geolocation.js'));
const Geo = globalThis.NuxelGeolocation;
ok(Geo, 'geolocation shim exports NuxelGeolocation');
Geo._setWatchIntervalForTests(20);

function wait(ms) { return new Promise(r => setTimeout(r, ms)); }

async function run() {
  check('missing coordinates never become 0,0', () => {
    const out = Geo._positionFromResponse({ success: true, latitude: null, longitude: null });
    eq(out.ok, false);
  });
  check('NaN coordinates rejected', () => {
    const out = Geo._positionFromResponse({ success: true, latitude: 'x', longitude: 4 });
    eq(out.ok, false);
  });
  check('out-of-range latitude rejected', () => {
    eq(Geo._positionFromResponse({ success: true, latitude: 95, longitude: 4 }).ok, false);
  });
  check('out-of-range longitude rejected', () => {
    eq(Geo._positionFromResponse({ success: true, latitude: 50, longitude: 190 }).ok, false);
  });
  check('missing timestamp stays null, not Date.now()', () => {
    const out = Geo._positionFromResponse({ success: true, latitude: 50, longitude: 4 });
    ok(out.ok);
    eq(out.position.timestamp, null);
    eq(out.position.timestampSource, 'missing');
    eq(out.position.freshnessEvidence, false);
  });
  check('provider timestamp converted seconds->ms and preserved', () => {
    const out = Geo._positionFromResponse({ success: true, latitude: 50, longitude: 4, timestamp: 1793400000 });
    eq(out.position.timestamp, 1793400000000);
    eq(out.position.timestampSource, 'provider');
  });
  check('invalid accuracy becomes null (no fabricated default)', () => {
    const out = Geo._positionFromResponse({ success: true, latitude: 50, longitude: 4, accuracy: 'nope' });
    eq(out.position.coords.accuracy, null);
  });
  check('negative accuracy becomes null', () => {
    const out = Geo._positionFromResponse({ success: true, latitude: 50, longitude: 4, accuracy: -3 });
    eq(out.position.coords.accuracy, null);
  });
  check('network source is labelled network, not GPS', () => {
    const out = Geo._positionFromResponse({ success: true, latitude: 50, longitude: 4,
      source: 'network_wifi', kind: 'network', gnss: false });
    eq(out.position.source, 'network_wifi');
    eq(out.position.kind, 'network');
    eq(out.position.gnss, false);
    eq(out.position.network, true);
  });
  check('GNSS source is labelled gnss', () => {
    const out = Geo._positionFromResponse({ success: true, latitude: 50, longitude: 4,
      source: 'gnss', kind: 'satellite', gnss: true });
    eq(out.position.gnss, true);
    eq(out.position.kind, 'satellite');
  });
  check('W3C enableHighAccuracy/timeout/maximumAge mapping', () => {
    const p = Geo._buildPayload({ enableHighAccuracy: true, timeout: 1234, maximumAge: 5000, accuracy: false });
    eq(p.highAccuracy, true);
    eq(p.timeout, 1234);
    eq(p.maximumAge, 5000);
  });
  check('permission denied maps to W3C code 1', () => {
    const out = Geo._positionFromResponse({ success: false, error_code: 'CAPABILITY_DENIED' });
    eq(out.ok, false);
    eq(out.code, 1);
  });

  await new Promise((resolve, reject) => {
    response = { success: true, latitude: 51.4, longitude: 5.47, accuracy: 25000,
      timestamp: 1793405000, source: 'network_wifi', kind: 'network', gnss: false, state: 'fixed' };
    Geo.getCurrentPosition((pos) => {
      try {
        eq(pos.coords.latitude, 51.4);
        eq(pos.source, 'network_wifi');
        eq(pos.gnss, false);
        resolve();
      } catch (e) { reject(e); }
    }, reject, { enableHighAccuracy: true, timeout: 3000 });
  });
  check('getCurrentPosition delivers a real network position and releases one-shot lease', () => {
    ok(calls.some(c => c.verb === 'stop'));
  });

  // watchPosition: repeated updates while active, then no timer/request after clear.
  let updates = 0;
  let lat = 51.0;
  response = () => ({ success: true, latitude: lat, longitude: 5.0, accuracy: 100,
    timestamp: 1793405000 + updates, source: 'network_wifi', kind: 'network', gnss: false, state: 'fixed' });
  const wid = Geo.watchPosition(() => { updates++; lat += 0.0001; }, () => {}, { watchInterval: 20 });
  await wait(110);
  check('watchPosition produces repeated updates', () => ok(updates >= 2, 'updates=' + updates));
  eq(Geo._activeWatchCount(), 1);
  const beforeClear = calls.length;
  Geo.clearWatch(wid);
  eq(Geo._activeWatchCount(), 0);
  eq(Geo._hasScheduler(), false, 'no timer after clearWatch');
  await wait(80);
  check('clearWatch stops future location requests', () => {
    eq(Geo._activeWatchCount(), 0);
    eq(Geo._hasScheduler(), false);
    // Allow the one in-flight request to finish; no *new* poll should start.
    ok(calls.length - beforeClear <= 1, 'calls after clear=' + (calls.length - beforeClear));
  });

  // Multiple watches share the scheduler and can be cleared independently.
  let a = 0, b = 0;
  const wa = Geo.watchPosition(() => { a++; }, () => {}, { watchInterval: 20 });
  const wb = Geo.watchPosition(() => { b++; }, () => {}, { watchInterval: 20 });
  await wait(80);
  Geo.clearWatch(wa);
  const aAfter = a;
  await wait(80);
  check('multiple watches update independently', () => ok(a > 0 && b > 0));
  check('clearing one watch keeps the other active', () => {
    eq(Geo._activeWatchCount(), 1);
    ok(b > 0);
  });
  Geo.clearWatch(wb);
  eq(Geo._activeWatchCount(), 0);
  eq(Geo._hasScheduler(), false, 'both watches cleared -> no timer');

  // Global policy OFF during a watch must stop the timer.
  let off = 0;
  const woff = Geo.watchPosition(() => { off++; }, () => {}, { watchInterval: 20 });
  await wait(50);
  const policyOff = new Event('nuxel:location-policy');
  policyOff.detail = { enabled: false };
  document.dispatchEvent(policyOff);
  check('global policy OFF stops an active watch timer immediately', () => {
    eq(Geo._hasScheduler(), false);
    eq(Geo._activeWatchCount(), 1, 'watch registration remains so it can resume');
  });
  Geo.clearWatch(woff);
  eq(Geo._hasScheduler(), false);

  console.log('');
  if (fail) { console.log(fail + ' CHECK(S) FAILED'); process.exit(1); }
  console.log('ALL PASS — geolocation shim validates data, preserves provider time, labels sources and stops watches');
}
run().catch((e) => { console.error(e); process.exit(1); });

// Maps core must not label a network fix as GNSS.
require(path.join(__dirname, '..', '..', 'pwa', 'nuxel-common', 'maps-core.js'));
const Core = globalThis.NuxelMapsCore;
const netView = Core.providerView({
  success: true, state: 'fixed', enabled: true,
  latitude: 51.4, longitude: 5.47, accuracy: 25000,
  last_fix_timestamp: 1793405000, fix_source: 'network_wifi', fix_kind: 'network',
  gnss_fix: false, network_fix: true,
}, 1793405010);
check('maps-core keeps network fix labelled network (not GNSS)', () => {
  eq(netView.fix.kind, 'network');
  eq(netView.fix.gnss, false);
  eq(netView.fix.network, true);
  ok(Core.providerSummary(netView, 1793405010).indexOf('network') >= 0);
});
const gnssView = Core.providerView({
  success: true, state: 'fixed', enabled: true,
  latitude: 51.4, longitude: 5.47, accuracy: 5,
  last_fix_timestamp: 1793405000, fix_source: 'gnss', fix_kind: 'satellite',
  gnss_fix: true, network_fix: false,
}, 1793405010);
check('maps-core keeps GNSS fix labelled GNSS', () => {
  eq(gnssView.fix.kind, 'satellite');
  eq(gnssView.fix.gnss, true);
  ok(Core.providerSummary(gnssView, 1793405010).indexOf('GNSS') >= 0);
});
const noTs = Core.providerView({ success: true, state: 'fixed', enabled: true,
  latitude: 51.4, longitude: 5.47, fix_source: 'network_wifi' }, 1793405010);
check('maps-core never presents a fix without a provider timestamp as fresh', () => {
  eq(noTs.state, 'stale');
  eq(noTs.fix.fresh, false);
  eq(noTs.fix.timestamp, null);
});
