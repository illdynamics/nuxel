# 05 — STATUS-BAR CAMERA & CUTOUT SAFE ZONES (ten-zone system)

**Status: implemented, unit-tested offline, deployed and measured reflowing the real
status bar on the handset.  This is a general Nuxel feature, not an S10+ offset.**

## 1. Model

The status-bar width is divided into **ten logical zones**, numbered 1..10 left to
right.  A blocked zone is not a warning graphic: it is an **excluded horizontal
interval**, and no status item may be laid out inside it.  The editor stores, per
device profile and per orientation:

```json
{
  "schema_version": 1,
  "zones": 10,
  "profiles": {
    "s10plus":      { "portrait": [9, 10], "landscape_left": [],     "landscape_right": [] },
    "pixel_center": { "portrait": [5, 6],  "landscape_left": [],     "landscape_right": [] },
    "none":         { "portrait": [],      "landscape_left": [],     "landscape_right": [] },
    "left_camera":  { "portrait": [1, 2],  "landscape_left": [1, 2], "landscape_right": [9, 10] },
    "right_camera": { "portrait": [9, 10], "landscape_left": [9, 10],"landscape_right": [1, 2] }
  },
  "padding_dp": 6,
  "profile": "s10plus",
  "orientation": "portrait",
  "custom": { "portrait": [], "landscape_left": [], "landscape_right": [] }
}
```

* File: `/etc/nuxel/display/statusbar-safezones.json` — **one** configuration, used by
  the Settings app, by the launcher layout engine and by `nuxelctl`.
* Device identity picks the starting profile (`navigator.userAgent`:
  S10+/G975/beyond2 → `s10plus`, Pixel → `pixel_center`), so one device’s choice never
  leaks into another; `custom` is stored per orientation.
* Padding is configurable (`padding_dp`, in CSS pixels × devicePixelRatio).

## 2. Constraint-aware layout (no item is ever placed under the cutout)

`pwa/nuxel-home/js/safe-zones.js` turns the blocked zones into intervals, measures the
three real clusters (`.status-left`, `.status-center`, `.status-right`) and moves each
one out of any interval it intersects, choosing the wider free side for the centre
cluster.  Items keep an explicit priority (time, battery icon, battery %, signal,
Wi-Fi); nothing is hidden to make the arithmetic easy, and a cluster that cannot be
placed is reported in `dropped[]` instead of being drawn under the cutout.

## 3. Live editor (Settings → Display → Status Bar → Camera & Cutout Areas)

`pwa/nuxel-apps/settings/` implements the interactive row of ten tappable boxes
(green = available, hatched red = blocked), preset selector
(none / right camera / centre camera / left camera / custom), orientation selector
(portrait / landscape left / landscape right), padding slider, a **live preview strip**
with the same constraint pass, and Save / Cancel.  Preview state is temporary; only
Save persists, and `NUXEL_SAFEZONES` receives a change event so the running status bar
reflows immediately (no reboot, no restart).

## 4. Console fallback (same configuration, no second settings system)

```
nuxelctl statusbar show
nuxelctl statusbar zones 9,10
nuxelctl statusbar preset right_camera|center_camera|left_camera|none|custom
nuxelctl statusbar orientation portrait|landscape_left|landscape_right
nuxelctl statusbar padding 8
```

## 5. Measured on the handset (no screenshot involved)

```
$ grep SAFEZONES /run/nuxel-home.state | tail -1
NUXEL_INPUT SAFEZONES profile=s10plus orientation=portrait blocked=[9,10] padding_dp=6
  width=360 moved=[{"cluster":"status-right","shift":112,"zone":9}] dropped=[]
```

The right cluster (battery + percentage + notifications) was moved **112 CSS px to the
left**, i.e. fully out of zones 9–10 where the S10+ front camera sits; the time and the
centre cluster were already clear (`moved=[]` for them).  The report is produced by the
launcher itself and relayed through the host’s diagnostic channel, so the verdict is
machine-checkable.

## 6. Tests

`tools/s10plus/a32/tests/safe-zones-test.js` (DOM-free harness) asserts: ten zones;
interval geometry including padding and devicePixelRatio; “zones 1..8 free” and “centre
is not covered” for the S10+ preset; the centre preset blocks exactly zones 5–6 and
leaves the edge free; the right-camera preset is `[9,10]` in portrait but `[1,2]` in
landscape-right; preset aliasing (`center_camera` → `pixel_center`); device-profile
detection; configurable padding; preview→commit persistence; and that the persisted
document is valid JSON with `schema_version`.
