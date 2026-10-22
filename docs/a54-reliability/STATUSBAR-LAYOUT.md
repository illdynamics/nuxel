# A54 Status-bar Layout

## Root cause
Two layout owners disagreed: the CSS grid split the right-hand indicators across
`.status-center` (signal + Wi-Fi) and `.status-right` (battery + percent) as two
separately `flex-end`-aligned grid cells, while `safe-zones.js` treated the same
regions as independently moved clusters. During the S10+ right-edge cutout
(zones 9/10) the two clusters could be pushed into the same free interval, and
the duplicated `.battery-slot`/`.battery-icon` CSS blocks provided a second,
conflicting size source — producing the Wi-Fi/arc-over-battery bleed.

## Fix applied
- `index.html`: one right-hand cluster now owns signal + Wi-Fi + battery +
  percent (`#status-signal`, `#status-wifi`, `#status-battery`,
  `#status-battery-pct` all inside `.status-right`). `.status-center` removed.
- `status-bar.css`: grid changed to `1fr auto`; `.status-right` is a measured
  flex cluster with a fixed `gap:7px` and fixed non-shrinking cells, so siblings
  are laid out sequentially and can never overlap. Duplicate battery size rules
  consolidated to one rule set.
- `status-bar.js`: added `_assertNoOverlap()` — measures every VISIBLE status
  cell's bounding box and reports any intersecting pair on the diagnostic
  channel after each render.
- Launcher cache bumped to `v32-a54-reliability` so the redeployed bundle is not
  served from the stale service-worker cache.

## Live evidence (device diagnostic channel, not a desktop preview)
```
STATUSBAR_READY version=0.6.3-beta safezones=present
SAFEZONES profile=s10plus orientation=portrait blocked=[9,10] padding_dp=6
  width=360 moved=[{"cluster":"status-right","shift":-68,"zone":9,"free":[0,276]}] dropped=[]
STATUSBAR_OVERLAP_CHECK cells=2 overlaps=none
```
Interpretation: logical width 360 px (720 physical @ DPR 2); the S10+ cutout
blocks zones 9/10; the single right cluster is shifted −68 px into the free
interval `[0,276]`; the collision detector measured 2 visible cells (Wi-Fi +
battery; signal hidden with no SIM) and reported **zero overlaps**.

## Gate
- **STATUS:** PASS_INTEGRATION — single layout owner, measured cells, automated
  collision assertion reports no overlap on-device. Startup/rotation visual
  checks remain owner-observable.
