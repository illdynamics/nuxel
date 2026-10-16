# Ten-zone status-bar safe areas — protected-asset verification and editor polish
### briq-02e · build group `bg-02-boot-animation-launcher` · manual proof area **2 (Launcher)**

Device: Samsung Galaxy S10+ **SM-G975F / beyond2lte**, Exynos 9820 — panel 1440x3040,
launcher viewport 360x760 CSS px, `devicePixelRatio` 2.
Launcher truth: the Nuxel Home PWA (`pwa/nuxel-home/`) as served by WebKitGTK inside the
UTM VM and on the handset.

**Terminal states for this briQ**

| Item | State |
|---|---|
| Ten-zone geometry contract (ZONES=10, S10+ portrait = zones 9,10, padding_dp 6, blocked = excluded interval) | `OFFLINE_TESTED` |
| Left/centre/right cluster layout never lands inside a blocked interval | `OFFLINE_TESTED` |
| Settings safe-zone editor preview (shared planner, honest fallback) | `OFFLINE_TESTED` |
| Same geometry + layout seen on the glass / in the VM launcher | `NEEDS_OWNER_TEST` (handset) / VM run owned by `bg-11-vm-parity` |

No claim in this document is `VERIFIED_ON_S10PLUS`.

---

## 1. The geometry contract (unchanged by A33 — this is the A32 floor)

The status bar is divided into **ten equal logical zones**, numbered 1..10 left to right.

```
zone k  =  [ (k-1) * W/10 , k * W/10 ]         W = bar width in px
interval(k) = [ (k-1) * W/10 - pad , k * W/10 + pad ]     pad = padding_dp * devicePixelRatio
```

| Contract item | Value | Where it lives |
|---|---|---|
| Zone count | `ZONES = 10` | `pwa/nuxel-home/js/safe-zones.js` |
| S10+ portrait preset | `[9, 10]` (the right-hand hole-punch cutout) | `profiles.s10plus.portrait` + `configs/nuxel/statusbar-safezones.json` |
| S10+ landscape presets | `landscape_left: []`, `landscape_right: []` | same |
| Padding | `padding_dp 6` (`= 12 px` at dpr 2) | config default; adjustable in the editor |
| Storage | `/etc/nuxel/display/statusbar-safezones.json`, read/written with `NuxelHost.configGet/configSet` (launcher host → atomic same-directory rename), `localStorage` fallback when no host is reachable | `safe-zones.js` (`CFG_NAME = 'statusbar-safezones'`) |
| Device profile | chosen from **hardware identity** (`navigator.userAgent/platform`: `S10+|G975|beyond2` → `s10plus`, `Pixel` → `pixel_center`, else `none`), never a global assumption | `deviceProfile()` |
| Presets offered | `none · right_camera · center_camera (alias of pixel_center) · left_camera · custom` | `DEFAULTS.presets`, `preset_alias` |
| Shipped presets in the document | `s10plus`, `pixel_center`, `none`, `left_camera`, `right_camera` | `configs/nuxel/statusbar-safezones.json` |

The ten-zone contract is a **protected A32 asset** (`INV-3` in
`docs/beta-finalization/baseline-protection.json`): the hard assertions pin `ZONES = 10`,
the S10+ portrait preset and the padding. A33 changed the *placement* algorithm around the
contract, not the contract. Verified: `tools/beta/regression-guard.sh` → `INV-3` green.

## 2. “Blocked” is an EXCLUDED INTERVAL, not a painted warning

A zone marked blocked produces an interval that status items must not be laid out inside.
Nothing is painted, dimmed or annotated in the bar itself; the consequence is geometric:

* each cluster (`.status-left`, `.status-center`, `.status-right`) is measured, and if it
  overlaps a blocked interval it is moved to the **nearest free interval**, honouring its
  alignment (start / centre / end);
* free space is the **complement** of the blocked intervals inside the bar, with overlapping
  intervals merged — padded zones 9 and 10 overlap, so they leave **one** free gap
  `[0, 8*W/10 - pad]`, not two;
* if a whole bar were blocked, the cluster is *reported* as `dropped: no_free_interval`,
  never silently drawn inside the cutout.

### What A33 hardened (and why)

Two real defects in the A32 placement pass were found and fixed in this briQ. Both were
invisible on a screenshot and only show up when a *left* or *right* zone is blocked:

1. **One-way push.** A32 only ever pushed a cluster away from the cutout in one direction, so
   the S10+ portrait profile (zones 9,10 = the right edge) pushed the right cluster further
   **right — off the panel** — and blocking zones 1,2 pushed the left cluster off the left
   edge, still inside the excluded interval. A33 solves against the free intervals
   (`freeIntervals` + `bestFreeInterval` + `targetLeft`), clamped to the panel.
2. **Non-idempotent layout.** A CSS `transform` is included in `getBoundingClientRect()`, so
   measuring before resetting the previous push stacked another translate on every render and
   the row drifted a little further each time. `applyLayout()` now resets the transform first;
   two consecutive passes produce byte-identical reports.
3. **Editor drift (this is the "editor polish").** The Settings safe-zone editor carried a
   *second copy* of the placement arithmetic that still had defect (1): its preview strip
   showed the right cluster pushed off the panel for the shipped S10+ profile, i.e. the
   preview disagreed with the real bar. The planner is now a single exported pure function
   (`planCluster`) used by both the launcher and the editor; when the launcher engine is not
   reachable (Settings opened outside Nuxel Home) the editor says the placement preview is
   unavailable rather than inventing its own geometry.

## 3. Files

| File | Role |
|---|---|
| `pwa/nuxel-home/js/safe-zones.js` | the engine: `ZONES`, presets, storage, `blockedIntervals`, `freeIntervals`, `overlaps`, `planCluster`, `applyLayout`, preview/commit API |
| `pwa/nuxel-home/js/status-bar.js` | the bar itself; calls `NuxelSafeZones.applyLayout()` on render/resize and reports engine presence in its state line |
| `pwa/nuxel-apps/settings/settings.js` | the editor: zone toggles 1..10, preset/orientation/padding controls, live preview, **Save** / **Cancel** / **Apply to real status bar (preview)** |
| `configs/nuxel/statusbar-safezones.json` | the shipped default document (installs to `/etc/nuxel/display/statusbar-safezones.json`) |
| `tools/s10plus/a32/tests/safe-zones-test.js` | the offline suite (geometry per zone, cluster exclusion, idempotency, shared-planner contract, editor drift gate) |

## 4. Evidence channel (verifiable from the live console, not from a screenshot)

`applyLayout()` publishes a single line through the launcher host diagnostic channel
(`webkit.messageHandlers.nuxelDiag` → `/run/nuxel-home.state`) — **only when the verdict
changes**, because the render paths call it several times per state update and a channel that
repeats itself is noise rather than evidence:

```
SAFEZONES profile=s10plus orientation=portrait blocked=[9,10] padding_dp=6 width=360 \
          moved=[{"cluster":"status-right","shift":-84,"zone":9,"free":[0,276]}] dropped=[]
```

The bar also carries the state as attributes for a DOM-level check:
`data-safezone-profile`, `data-safezone-orientation`, `data-safezone-blocked`,
`data-safezone-padding-dp`. The full report object is on `window.__nuxelSafeZoneReport`.

Typical shape on the handset (360 px bar, zones 9,10, padding 6 dp): the right cluster at
`300..360` shifts **−84 px** into the free interval `[0, 276]`. Blocking zones 1,2 shifts the
left cluster **+84 px**; blocking 5,6 shifts the centre cluster **−114 px** (free `[0, 132]`).

## 5. How to re-verify (offline — no phone, no root, no display)

```sh
node tools/s10plus/a32/tests/safe-zones-test.js     # 44 assertions, 0 failures
bash tools/s10plus/a33/tests/run-boot-tests.sh      # the whole bg-02 gate (includes this suite)
bash tools/beta/regression-guard.sh                 # INV-3 hard, INV-9 soft: the A32 floor
```

The suite is DOM-free: `safe-zones.js` is loaded into a `vm` context with a minimal
`window`/`document` shell, so it runs on the build host with no WebKitGTK and no panel.

## 6. What the owner must do (manual proof area 2 / 3)

See `docs/beta-finalization/manual-proof/02-launcher.md` for the exact procedure. In short:
open Nuxel Home on the handset with the launcher in **portrait**, confirm the clock, battery,
signal and Wi-Fi items are all visible **left of the hole-punch cutout** and none is drawn
under it; then open **Settings → Display → Safe zones**, block/unblock zones and confirm the
preview strip matches what the real status bar does. The status bar must not show a painted
"blocked zone" marker — the effect is the item moving, nothing else.

## 7. Rollback

Repository-only, no device state: `git revert` the commit(s) touching
`pwa/nuxel-home/js/safe-zones.js`, `pwa/nuxel-apps/settings/settings.js`,
`configs/nuxel/statusbar-safezones.json` and `tools/s10plus/a32/tests/safe-zones-test.js`.
The deployed launcher bundle is restored by rolling the PWA cache back with the A32
cache-invalidation path (`sw.js` namespace + host purge) — no BOOT/USERDATA/DTB write, and
**no flashing of any kind**. If the whole safe-zone revision is being undone, the A32 engine
behaviour (one-way push) returns with it; that is the regression `INV-3` guards.
