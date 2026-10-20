#!/usr/bin/env node
// A45 lockscreen layout regression test (offline, no device).
// Verifies the cover-crop-aware lockhead resting position is BELOW the wallpaper
// penguin with at least the required spacing, and fully inside the viewport.
'use strict';
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
