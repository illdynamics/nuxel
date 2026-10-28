# Nuxel A82 — lockscreen touch recovery, battery truth and software-render performance

Date: 2026-10-27 (Europe/Amsterdam)  
Target: Samsung Galaxy S10+ SM-G975F / beyond2lte / Linux 4.14.253  
Host: `/x/nuxel` (Fedora 43 x86_64)

## Verdict

| Item | Result | Evidence |
|---|---|---|
| Lockscreen access | **PASS (physical)** | Normal reboot cleared the charger/LPM boot; `sec_touchscreen` registered; real contacts reached the arming service; `unlock:home reason=unlock`, `home:complete`, `unlock:complete` were logged. |
| Battery 100% → 0% flicker | **FIXED + unit-tested** | Host reading stayed `100 / Full` after reboot. The bridge no longer fabricates `100 charging`; `Full + 0` is treated as unknown and the UI requires 3 consecutive zero samples before replacing a known-good value. |
| Performance | **IMPROVED (measured)** | Removed alpha filters that forced a software raster pass every frame. Lockscreen WebKit CPU fell from ~250–440% to ~150–195%; unlocked Home idles at ~31%. The 28–29 fps framebuffer ceiling is unchanged. |
| Reboot | **DONE** | Boot ID changed `7340fe04-…` → `582cb05b-…`; `androidboot.mode=charger` is absent. |

## Root cause of “cannot get into the lockscreen”

The phone had been powered on **from off with a charger attached**, so S-Boot passed
`androidboot.mode=charger`. The vendor kernel's `sec_bat_is_lpm_check()` sets
`lpcharge=1`, and `sec_ts_init()` deliberately returns `-ENODEV` before registering
the touchscreen. On that boot:

```text
/proc/cmdline      androidboot.mode=charger  charging_mode=0x3030
/proc/bus/input    no sec_touchscreen
/sys/class/sec/tsp absent
nuxel-touch-arm    NO_TOUCH_DEVICE devices=7
```

No userspace gesture can fix this boot: the driver was never registered. A
Linux-initiated normal reboot clears the mode, even with the cable attached.

## What changed

- `pwa/nuxel-home/css/lockscreen.css`
  - Removed the idle `filter: drop-shadow()` from the lockhead and the
    `saturate()/brightness()` filter from the status icons. These forced the
    WebKitGTK/llvmpipe renderer to re-rasterise every frame. The short-lived
    drop-shadow is retained only for `.grabbed`, `.armed` and `.unlocking`.
  - Added the `lockscreen-touch-warning` styles.
- `pwa/nuxel-home/index.html`
  - Added the explanatory warning element and bumped the CSS/JS cache-busters
    to `a82`.
- `pwa/nuxel-home/js/lockscreen.js`
  - Battery reads are validated and debounced: `Full + 0%` is rejected; a 0% or
    >30-point swing needs repeated samples; unchanged text is not rewritten.
  - Detects charger/LPM/no-touch state from `/run/nuxel-touch-arm.state` and
    shows “Touch unavailable — unplug the charger, then hold POWER to restart.”
  - The unlock gesture now also starts anywhere in the lower screen band, not
    only exactly on the 108 px lockhead artwork.
  - Clock DOM writes only when the visible minute/date changes.
- `pwa/nuxel-home/js/status-bar.js`
  - Same battery guard, render-key deduplication, minute-change DOM guard, and
    slower 10 s fallback polls with immediate display-on refresh.
- `services/nuxel-bridge/src/api.py`
  - Unreadable battery is now `level: null, available: false`, not a fabricated
    `100% charging`; `Full` is no longer reported as actively charging and a
    `Full + 0` sample is not published.
- `pwa/nuxel-home/sw.js`, `pwa/nuxel-home/manifest.json`
  - Cache namespace `v50-a82-lock-battery-perf`.
- `tools/s10plus/a45/test-lockscreen-unlock.js` and
  `tools/s10plus/a45/test-lockscreen-layout.js`
  - Added battery-flicker, touch-warning, lower-band-swipe and filter-regression
    checks.

## Deployment

Manifest: `tools/beta/live/nuxel-a82-lock-battery-perf-manifest.json`  
Evidence: `docs/beta-finalization/live/evidence/deploy-20261027T222442+0100/`

- 7 files, SHA-256 verified, atomically installed.
- `nuxel-wayland` and `nuxel-http-bridge` restarted; health checks passed.
- No rollback was required; every target matched its source hash after install.
- No kernel, boot, partition, modem, DTB or USB-gadget write occurred.

## Post-reboot live checks

```text
boot_id            582cb05b-2d25-4e81-aa68-3d90079014af
androidboot.mode   absent (normal boot)
sec_touchscreen    present: /devices/platform/104b0000.hsi2c/i4/4-0048/input/input2
nuxel-touch-arm    active; real TOUCH_POINT events recorded
lockscreen         boot lock shown; touch-warning show=0
unlock             unlock:home reason=unlock / home:complete / unlock:complete
battery            100 / Full; API level=100 status=full
services           nuxel-wayland, nuxel-http-bridge, nuxel-bridge, nuxel-web, sshd all active
```

Measured CPU after the fix (WebKitWebProcess):

- lockscreen with charging + USB + live-console indicators active: ~150–195%
  (pre-fix baseline with the same indicators: ~250–440%)
- unlocked Home: ~31%
- `nuxel-wl-fb`: 28–29 fps, `blit_avg_ms≈57`, failures=0

The remaining cost is the software-rendered 720×1520 → 1440×3040 framebuffer
pipeline itself, not the lockhead/indicator filters.

## Tests

```text
python3 -m pytest tests/ -q                                      77 passed
node tools/s10plus/a45/test-lockscreen-unlock.js                 ALL PASS (66/66)
node tools/s10plus/a45/test-lockscreen-layout.js                 ALL PASS
node tools/s10plus/a45/test-lockscreen-indicators.js             ALL PASS
node tools/s10plus/a33/tests/launcher-registry-test.js           passed
python3 tools/s10plus/a33/tests/test-no-eventn-literal.py        passed
python3 tools/s10plus/a33/tests/test-bootmode-guard.py           passed
```

`tools/s10plus/a33/tests/test-boot-surface-contract.py` still reports its two
pre-existing executable-bit failures (`runner is executable`, `build script is
executable`); neither file was touched by this change.

## Rollback

Each target has a `.nuxel-rollback.pre-deploy-20261027T222442-…` copy. Restore
the seven files and restart `nuxel-wayland` and `nuxel-http-bridge`.
