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

console.log(failures ? ('\n' + failures + ' FAILURES') : '\nall safe-zone tests passed');
process.exit(failures ? 1 : 0);
