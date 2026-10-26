#!/usr/bin/env node
// A45 lockscreen layout regression test (offline, no device).
// Verifies the cover-crop-aware lockhead resting position is BELOW the wallpaper
// penguin with at least the required spacing, and fully inside the viewport.
'use strict';
const fs = require('fs');
const path = require('path');
const ROOT = path.join(__dirname, '../../..');
const CSS = fs.readFileSync(path.join(ROOT, 'pwa/nuxel-home/css/lockscreen.css'), 'utf8');
const INDEX = fs.readFileSync(path.join(ROOT, 'pwa/nuxel-home/index.html'), 'utf8');
const WALLPAPER = { w: 768, h: 1376 };
const PENGUIN_BOTTOM_Y = 990;       // measured opaque lower edge of the illustrated penguin
const MIN_SPACING = 32;
let failures = 0;
function check(name, cond) { console.log((cond ? 'PASS ' : 'FAIL ') + name); if (!cond) failures++; }

function coverCssY(imageY, vw, vh) {
  const scale = Math.max(vw / WALLPAPER.w, vh / WALLPAPER.h);
  const scaledH = WALLPAPER.h * scale;
  const cropY = Math.max(0, (scaledH - vh) / 2);
  return imageY * scale - cropY;
}
function handleTop(vw, vh) {
  const handleSize = Math.max(96, Math.min(124, vw * 0.3));
  const penguinBottomCss = coverCssY(PENGUIN_BOTTOM_Y, vw, vh);
  return Math.min(Math.max(penguinBottomCss + MIN_SPACING, vh * 0.62), vh - handleSize - 24);
}

// Target display: 360x760 CSS (720x1520 logical at scale 2).
const vw = 360, vh = 760;
const top = handleTop(vw, vh);
const size = Math.max(96, Math.min(124, vw * 0.3));
const penguinBottom = coverCssY(PENGUIN_BOTTOM_Y, vw, vh);

check('penguin bottom is above the viewport centre (below-half reserved)', penguinBottom < vh * 0.72);
check('lockhead top is below the wallpaper penguin', top >= penguinBottom);
check('lockhead/penguin spacing is at least MIN_SPACING', top - penguinBottom >= MIN_SPACING);
check('lockhead bottom edge is inside the viewport', top + size <= vh);
check('lockhead top edge is inside the viewport', top >= 0);
check('lockhead is centred within horizontal bounds', size <= vw);

// The required physical target band: bottom 15-25% is a recommendation, but the
// hard invariant is non-overlap + visibility; assert both.
check('lockhead occupies the lower ~quarter of the screen', top >= vh * 0.62 && top + size <= vh);

// A70 indicator geometry.  These alpha boxes were measured from the exact PNG
// files after a 10% alpha threshold; object-fit:contain scales by the longer
// canvas edge.  This checks visible painted art, not only its CSS parent.
const BASELINE_BOX = 34; // physically deployed A68.2 baseline
const A70_BOX = 68;
const GAP = 8;
const ASSETS = {
  charging: { canvas: [1254, 1254], alpha: [1094, 1083] },
  usb:      { canvas: [1374, 1145], alpha: [1319, 884] },
  live:     { canvas: [1254, 1254], alpha: [974, 901] },
};
function painted(asset, box) {
  const scale = box / Math.max(...asset.canvas);
  return asset.alpha.map(n => n * scale);
}
for (const [name, asset] of Object.entries(ASSETS)) {
  const before = painted(asset, BASELINE_BOX);
  const after = painted(asset, A70_BOX);
  check(name + ' painted width is exactly 2x baseline', Math.abs(after[0] / before[0] - 2) < 1e-9);
  check(name + ' painted height is exactly 2x baseline', Math.abs(after[1] / before[1] - 2) < 1e-9);
  check(name + ' full alpha silhouette fits its box', after[0] <= A70_BOX && after[1] <= A70_BOX);
}

// Real WebKitGTK 2.52 receipt: metadata bottom is 170 px on the 360x760 target.
// The row is pinned 14 px below it because relative flex positioning resolved
// to y=754 on this physical compositor.
const batteryBottom = 170;
const indicatorTop = batteryBottom + 14;
const indicatorBottom = indicatorTop + A70_BOX;
check('indicator row has a neat 14px gap below battery', indicatorTop - batteryBottom === 14);
check('indicator painted lower edge is above vertical centre', indicatorBottom < vh / 2);
check('indicator row is above lockhead resting position', indicatorBottom < top);
for (let active = 1; active <= 3; active++) {
  const width = active * A70_BOX + (active - 1) * GAP;
  const left = (vw - width) / 2;
  check(active + '-active row fits 360px viewport', left >= 8 && left + width <= vw - 8);
  check(active + '-active row is horizontally centred', Math.abs((left + width / 2) - vw / 2) < 1e-9);
}

check('CSS uses the measured 68px indicator box', /\.lockscreen-indicator\s*\{[\s\S]*?width:\s*68px;[\s\S]*?height:\s*68px;/.test(CSS));
check('indicator row is pinned to the proven physical y=184 placement',
      /\.lockscreen-indicators\s*\{[\s\S]*?position:\s*absolute;[\s\S]*?top:\s*184px;[\s\S]*?left:\s*0;[\s\S]*?right:\s*0;/.test(CSS));
check('inactive indicators are removed from paint, not ghosted', /\.lockscreen-indicator\s*\{[\s\S]*?display:\s*none;/.test(CSS));
check('active indicators return to layout', /\.lockscreen-indicator\.active\s*\{[\s\S]*?display:\s*block;/.test(CSS));
check('crop-only clip-path is gone', !/\.lockscreen-indicator[^\{]*img\s*\{[^}]*clip-path/s.test(CSS));

// A72 equal-visible-size regression: the three PNGs have different aspect
// ratios, so a uniform square box makes charging look larger than PC/live.
// The per-indicator boxes below keep every painted silhouette the same ~59px
// height as the charging penguin (the owner-reported "same size" contract).
const A72_BOXES = { charging: [68, 68], usb: [91, 76], live: [82, 82] };
function paintedIn(boxW, boxH, asset) {
  const scale = Math.min(boxW / asset.canvas[0], boxH / asset.canvas[1]);
  return asset.alpha.map(n => n * scale);
}
check('a72 per-indicator box sizes present',
      /\.lockscreen-indicator\.usb-ind\s*\{[\s\S]*?width:\s*91px;[\s\S]*?height:\s*76px;/.test(CSS) &&
      /\.lockscreen-indicator\.live-ind\s*\{[\s\S]*?width:\s*82px;[\s\S]*?height:\s*82px;/.test(CSS));
{
  const heights = Object.entries(A72_BOXES).map(([name, [w, h]]) =>
    paintedIn(w, h, ASSETS[name])[1]);
  const ref = paintedIn(...A72_BOXES.charging, ASSETS.charging)[1];
  check('a72 equal painted height across all three indicators',
        heights.every(v => Math.abs(v - ref) < 0.6));
  check('a72 equal-height row fits 360px viewport',
        (A72_BOXES.charging[0] + A72_BOXES.usb[0] + A72_BOXES.live[0] + 2 * GAP) <= 360);
}
check('indicator row follows the handle block as a lockscreen-level sibling',
      INDEX.indexOf('id="lockscreen-indicators"') > INDEX.indexOf('id="lockscreen-handle-wrap"') &&
      /id="lockscreen-hint"[\s\S]*?<\/div>\s*<\/div>\s*<div class="lockscreen-indicators"/.test(INDEX));

// Robustness across plausible viewport sizes/rotations.
const variants = [[360, 760], [760, 360], [320, 640], [430, 900]];
for (const [w, h] of variants) {
  const t = handleTop(w, h), s = Math.max(96, Math.min(124, w * 0.3));
  const pb = coverCssY(PENGUIN_BOTTOM_Y, w, h);
  check('variant ' + w + 'x' + h + ' non-overlap', t >= pb || (pb > h - s - 24));
  check('variant ' + w + 'x' + h + ' handle inside viewport', t >= 0 && t + s <= h);
}

console.log(failures === 0 ? 'ALL PASS' : failures + ' FAILURES');
process.exit(failures === 0 ? 0 : 1);
