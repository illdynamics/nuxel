// Offline test of the status-bar safe-zone engine (mission 9/17).
// A DOM-free harness: the module only needs a window/document shell to load.
const fs = require('fs');
const path = require('path');
const vm = require('vm');

const src = fs.readFileSync(path.join(__dirname, '../../../../pwa/nuxel-home/js/safe-zones.js'), 'utf8');
let failures = 0;
function check(name, cond, extra) {
  console.log((cond ? 'PASS ' : 'FAIL ') + name + (cond ? '' : '  ' + (extra || '')));
  if (!cond) failures++;
}

const store = {};
const win = {
  devicePixelRatio: 2,
  addEventListener() {}, removeEventListener() {},
  dispatchEvent() {},
  localStorage: { getItem: (k) => (k in store ? store[k] : null), setItem: (k, v) => { store[k] = v; } },
  navigator: { userAgent: 'Mozilla/5.0 (Linux; aarch64) Nuxel/1.0 (S10+, like Gecko) WebKitGTK' },
  document: {
    readyState: 'complete',
    addEventListener() {},
    getElementById: () => null,
    querySelector: () => null
  }
};
win.window = win;
// minimal CustomEvent/Event stubs: the module dispatches a change event after a save
class CE { constructor(type, opts) { this.type = type; Object.assign(this, opts || {}); } }
win.CustomEvent = CE;
win.Event = CE;
const ctx = vm.createContext(win);
vm.runInContext(src, ctx);
const Z = win.NuxelSafeZones;
check('module exposes NuxelSafeZones', !!Z);
check('ten zones', Z && Z.ZONES === 10, Z && Z.ZONES);

Z.previewZones([9, 10], 'portrait', 'custom');
let iv = Z.blockedIntervals(360);          // 360 px wide -> 36 px per zone
check('two blocked zones -> two intervals', iv.length === 2, JSON.stringify(iv));
const pad = 6 * 2;                          // padding_dp 6 * dpr 2
check('zone 9 interval starts at 8*36 - pad', Math.abs(iv[0].start - (8 * 36 - pad)) < 0.01, JSON.stringify(iv[0]));
check('zone 10 interval ends at 360 + pad', Math.abs(iv[1].end - (360 + pad)) < 0.01, JSON.stringify(iv[1]));
check('zones 1..8 are free', iv[0].start > 8 * 36 - pad - 0.01);
check('no interval covers zone 5 (centre preset must differ)',
      !iv.some((i) => 4 * 36 >= i.start && 4 * 36 < i.end));

Z.previewZones([5, 6], 'portrait', 'custom');
iv = Z.blockedIntervals(360);
check('centre preset blocks the middle', iv.length === 2 &&
      Math.abs(iv[0].start - (4 * 36 - pad)) < 0.01 && Math.abs(iv[1].end - (6 * 36 + pad)) < 0.01,
      JSON.stringify(iv));
check('centre preset leaves the right edge free', iv[iv.length - 1].end <= 360 + pad + 0.01);

Z.cancelPreview();
Z.applyPreset('right_camera');
check('right_camera preset = zones 9,10 in portrait', JSON.stringify(Z.zonesFor(Z.state.profile, 'portrait')) === '[9,10]',
      JSON.stringify(Z.zonesFor(Z.state.profile, 'portrait')));
check('right_camera preset = zones 1,2 in landscape_right',
      JSON.stringify(Z.zonesFor(Z.state.profile, 'landscape_right')) === '[1,2]',
      JSON.stringify(Z.zonesFor(Z.state.profile, 'landscape_right')));
Z.applyPreset('center_camera');
check('center_camera aliases to pixel_center (zones 5,6)',
      JSON.stringify(Z.zonesFor(Z.state.profile, 'portrait')) === '[5,6]',
      JSON.stringify(Z.zonesFor(Z.state.profile, 'portrait')));
Z.applyPreset('none');
check('no-cutout preset blocks nothing', Z.zonesFor(Z.state.profile, 'portrait').length === 0);
check('device profile detected from hardware identity', Z.deviceProfile() === 's10plus', Z.deviceProfile());
check('padding is configurable', (Z.padding(12), Z.padding() === 12));
Z.previewZones([3], 'portrait', 'custom');
Z.commitPreview((ok, how) => { check('preview commit persists (offline → localStorage)', how === 'localStorage', how); });
check('committed zones stored in custom/portrait',
      JSON.stringify(Z.state.custom.portrait) === '[3]', JSON.stringify(Z.state.custom.portrait));
check('saved document is valid JSON', (() => { try { JSON.parse(store['nuxel.safezones']); return true; } catch (e) { return false; } })());
check('schema_version present in the persisted document', JSON.parse(store['nuxel.safezones']).schema_version === 1);


// --------------------------------------------------------------------------- //
// A33 (briq-02e): every zone of the ten-zone split, and the LEFT/CENTRE/RIGHT
// cluster layout must EXCLUDE the blocked intervals.
//
// The ten-zone system is a protected A32 asset.  Two properties have to hold no
// matter which zone is blocked:
//   (a) zone k is exactly the interval [ (k-1)*W/10 , k*W/10 ] grown by the
//       configured padding - the geometry contract, not an opinion;
//   (b) after applyLayout() every cluster's final rectangle is outside every
//       blocked interval, for the left, the centre AND the right cluster.
// A "painted warning" that leaves an item sitting in the cutout is exactly the
// failure mode this asserts against.
// --------------------------------------------------------------------------- //
const W = 360;
const ZONE_W = W / Z.ZONES;
Z.padding(6);                           // the shipped contract: padding_dp 6
const PAD = Z.state.padding_dp * 2;     // padding_dp * devicePixelRatio 2
check('the ten-zone contract uses padding_dp 6', PAD === 12, Z.state.padding_dp);

// (a) zone-by-zone geometry: block ONE zone at a time and check its interval.
let zoneGeometryOk = true, zoneDetail = '';
for (let z = 1; z <= Z.ZONES; z++) {
  Z.previewZones([z], 'portrait', 'custom');
  const ivs = Z.blockedIntervals(W);
  const want = { start: (z - 1) * ZONE_W - PAD, end: z * ZONE_W + PAD };
  const got = ivs[0];
  const ok = ivs.length === 1 && got.zone === z &&
             Math.abs(got.start - want.start) < 1e-9 && Math.abs(got.end - want.end) < 1e-9;
  if (!ok) { zoneGeometryOk = false; zoneDetail = 'zone ' + z + ': ' + JSON.stringify(got); }
}
check('every one of the ten zones maps to its own padded interval', zoneGeometryOk, zoneDetail);

// the ten zones tile the bar: consecutive zone boundaries are contiguous
Z.previewZones([1, 2, 3, 4, 5, 6, 7, 8, 9, 10], 'portrait', 'custom');
let ivAll = Z.blockedIntervals(W);
check('all ten blocked zones tile the whole bar', ivAll.length === 10 &&
      Math.abs(ivAll[0].start - (0 - PAD)) < 1e-9 &&
      Math.abs(ivAll[9].end - (W + PAD)) < 1e-9 &&
      ivAll.every((iv, i) => Math.abs(iv.start - (i * ZONE_W - PAD)) < 1e-9),
      JSON.stringify(ivAll));

// blocking NOTHING is the identity: no excluded interval at all
Z.previewZones([], 'portrait', 'custom');
check('no blocked zone -> no excluded interval', Z.blockedIntervals(W).length === 0,
      JSON.stringify(Z.blockedIntervals(W)));
Z.cancelPreview();

// (b) cluster layout: a DOM-free status bar with the three real clusters.
function cluster(cls, left, right) {
  return {
    className: cls,
    style: {},
    getBoundingClientRect() { return { left: left, right: right, width: right - left, top: 0, bottom: 24, height: 24 }; },
  };
}
function parseShift(t) {
  const m = /translateX\((-?\d+(?:\.\d+)?)px\)/.exec(t || '');
  return m ? parseFloat(m[1]) : 0;
}
let clusters = {
  '.status-left': cluster('status-left', 0, 60),
  '.status-center': cluster('status-center', 150, 210),
  '.status-right': cluster('status-right', 300, 360),
};
const bar = {
  clientWidth: W, offsetWidth: W,
  setAttribute() {},
  querySelector(sel) { return clusters[sel] || null; },
};
win.document.getElementById = (id) => (id === 'status-bar' ? bar : null);

function layoutExcludes(zones, expectMoved) {
  Z.previewZones(zones, 'portrait', 'custom');
  const report = Z.applyLayout();
  const ivs = Z.blockedIntervals(W);
  const bad = [];
  const seen = [];
  Object.keys(clusters).forEach((sel) => {
    const c = clusters[sel];
    const shift = parseShift(c.style.transform);
    const r = c.getBoundingClientRect();
    const fin = { left: r.left + shift, right: r.right + shift };
    seen.push(sel + ':' + Math.round(fin.left) + '..' + Math.round(fin.right));
    ivs.forEach((iv) => {
      if (fin.left < iv.end && fin.right > iv.start) bad.push(sel + ' in zone ' + iv.zone);
    });
  });
  const movedOk = expectMoved === undefined || (report.moved.length > 0) === expectMoved;
  check('cluster layout excludes blocked zones ' + JSON.stringify(zones) +
        (expectMoved === undefined ? '' : expectMoved ? ' (a cluster is pushed)' : ' (nothing to push)'),
        bad.length === 0 && movedOk, bad.length ? bad.join(',') : 'moved=' + JSON.stringify(report.moved) + ' ' + seen.join(' '));
  return report;
}

// S10+ portrait: zones 9,10 are the right-hand camera cutout.  The right cluster
// sits at 300..360 (zone 9-10) and MUST be pushed out of it.
const r910 = layoutExcludes([9, 10], true);
check('the right cluster was moved out of zones 9,10 by a negative shift',
      r910.moved.length === 1 && r910.moved[0].cluster === 'status-right' && r910.moved[0].shift < 0,
      JSON.stringify(r910.moved));

// Left camera: zones 1,2 blocked - the LEFT cluster must move.
layoutExcludes([1, 2], true);
// Centre camera: zones 5,6 blocked - the CENTRE cluster must move.
layoutExcludes([5, 6], true);
// No cutout: nothing may move (a layout that shifts for no reason is a defect).
clusters['.status-right'].style.transform = '';
clusters['.status-center'].style.transform = '';
clusters['.status-left'].style.transform = '';
const rNone = layoutExcludes([], false);
check('with no blocked zone the clusters are left exactly where they are',
      rNone.moved.length === 0, JSON.stringify(rNone));
check('the report names the blocked zones it solved against',
      JSON.stringify(rNone.blocked) === '[]', JSON.stringify(rNone.blocked));

// Idempotency: a CSS transform is included in getBoundingClientRect(), so a
// layout pass that measures before it resets would stack another translate on
// every render (the A32 drift).  Two consecutive passes must agree exactly.
Z.previewZones([9, 10], 'portrait', 'custom');
const pass1 = Z.applyLayout();
const t1 = clusters['.status-right'].style.transform;
const pass2 = Z.applyLayout();
const t2 = clusters['.status-right'].style.transform;
check('applyLayout is idempotent (no compounding translate)',
      t1 === t2 && JSON.stringify(pass1.moved) === JSON.stringify(pass2.moved),
      t1 + ' -> ' + t2);
check('the right cluster stays on the panel after the push',
      parseShift(t2) + 360 <= W + 0.5 && parseShift(t2) + 360 > 0,
      'right edge ' + (parseShift(t2) + 360));
check('the moved cluster reports the free interval it moved into',
      pass1.moved.length === 1 && Array.isArray(pass1.moved[0].free) &&
      pass1.moved[0].free[1] <= 9 * ZONE_W + 0.5,
      JSON.stringify(pass1.moved));
Z.cancelPreview();

// --------------------------------------------------------------------------- //
// A33 (briq-02e): the SHARED pure planner.  The Settings safe-zone editor used
// to carry a second copy of the placement arithmetic, and that copy still did the
// A32 one-way push (it moved the right cluster further right, i.e. off the panel,
// for the S10+ profile [9,10]).  The planner is now exported once and both the
// real status bar and the editor call it, so these assertions pin the geometry
// AND the absence of a divergent second copy.
// --------------------------------------------------------------------------- //
check('engine exports the pure planner', typeof Z.planCluster === 'function' &&
      typeof Z.freeIntervals === 'function' && typeof Z.overlaps === 'function');

// zones 9,10 grow with the padding and OVERLAP, so the free space left of the
// cutout is ONE gap: [0, 8*36 - 12].
Z.previewZones([9, 10], 'portrait', 'custom');
const free910 = Z.freeIntervals(W, Z.blockedIntervals(W));
check('padded zones 9,10 merge into a single free interval',
      free910.length === 1 && Math.abs(free910[0].start) < 1e-9 &&
      Math.abs(free910[0].end - (8 * ZONE_W - PAD)) < 1e-9,
      JSON.stringify(free910));

const right910 = Z.planCluster({ left: 300, right: 360, width: 60 }, 'end', Z.blockedIntervals(W), W);
check('planner pushes the right cluster LEFT out of the S10+ cutout (never off-panel)',
      right910.hit === true && right910.zone === 9 && right910.shift < 0 &&
      right910.reason === 'moved' && right910.narrow === false,
      JSON.stringify(right910));
check('the planned right-cluster rectangle lands inside the free interval',
      300 + right910.shift >= free910[0].start &&
      360 + right910.shift <= free910[0].end + 0.5,
      'right edge after shift = ' + (360 + right910.shift));

Z.previewZones([1, 2], 'portrait', 'custom');
const fb = Z.blockedIntervals(W);
const left12 = Z.planCluster({ left: 0, right: 60, width: 60 }, 'start', fb, W);
check('planner pushes the left cluster RIGHT out of zones 1,2 (never off the left edge)',
      left12.shift > 0 && left12.zone === 1 && left12.reason === 'moved',
      JSON.stringify(left12));
check('the planned left-cluster rectangle is clear of every blocked interval',
      !Z.overlaps(left12.target.start, left12.target.start + 60, fb),
      JSON.stringify(left12.target) + ' vs ' + JSON.stringify(fb));

Z.previewZones([5, 6], 'portrait', 'custom');
const centre56 = Z.planCluster({ left: 150, right: 210, width: 60 }, 'center', Z.blockedIntervals(W), W);
check('planner moves the centre cluster out of zones 5,6',
      centre56.hit === true && centre56.reason === 'moved' &&
      centre56.shift + 150 >= 0 && centre56.shift + 150 <= W,
      JSON.stringify(centre56));

Z.previewZones([9, 10], 'portrait', 'custom');
const clearCluster = Z.planCluster({ left: 0, right: 60, width: 60 }, 'start', Z.blockedIntervals(W), W);
check('a cluster already in free space is not moved', clearCluster.hit === false &&
      clearCluster.shift === 0 && clearCluster.reason === 'clear', JSON.stringify(clearCluster));

Z.previewZones([1, 2, 3, 4, 5, 6, 7, 8, 9, 10], 'portrait', 'custom');
const hopeless = Z.planCluster({ left: 0, right: 60, width: 60 }, 'start', Z.blockedIntervals(W), W);
check('a fully blocked bar yields no placement (and is reported, not faked)',
      hopeless.reason === 'no_free_interval' && hopeless.shift === 0, JSON.stringify(hopeless));
Z.cancelPreview();

// The drift gate: the Settings editor must CALL the shared planner and must not
// contain the A32 one-way arithmetic any more.
const settingsSrc = fs.readFileSync(path.join(__dirname, '../../../../pwa/nuxel-apps/settings/settings.js'), 'utf8');
check('the Settings editor uses the shared planner (no second copy)',
      /engine\.planCluster\(/.test(settingsSrc) && /engine\.blockedIntervals\(/.test(settingsSrc) &&
      !/intervals\[0\]\.a/.test(settingsSrc) && !/intervals\[intervals\.length - 1\]\.b/.test(settingsSrc));
check('the Settings editor states that the preview needs the launcher engine when it is absent',
      /placement preview needs the launcher safe-zone engine/.test(settingsSrc));

console.log(failures ? ('\n' + failures + ' FAILURES') : '\nall safe-zone tests passed');
process.exit(failures ? 1 : 0);
