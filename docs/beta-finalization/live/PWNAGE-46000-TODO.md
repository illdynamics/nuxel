# PWNAGE-46000 — physical rotation, touch, auto sensor, seven-mode policy

Status: **IN PROGRESS — single-transform + keyboard repair deployed; owner physical acceptance pending**

## Root causes confirmed in current checkout/live device

- [x] All seven policy keys/allowed sets existed, but visible labels were the old
  “Forced/Reverse/advanced” strings. Exact owner labels are now used in the
  policy, JSON, Quick Settings and Settings.
- [x] Bridge `orientation.set` persisted only; it now requests `--apply`.
- [x] `wlr-randr` discovery used the shell builtin `command`; replaced with
  `shutil.which`, live JSON output discovery and post-change readback.
- [x] The live output is **HEADLESS-1**, not the configured `DSI-1`; the daemon
  resolves the enabled output dynamically (`auto`).
- [x] Hardware test-pattern probe proved the real path: phoc transforms the
  screencopy frame inside the 720x1520 binding, so presenting it directly is the
  correct single transform. `nuxel-wl-fb` still supports presenter rotation for
  explicit alternate backends, but the live config now sets
  `screencopy_already_transformed=true` to prevent a double rotation. The
  effective-angle -> phoc-transform map is currently identity.
- [x] The blue DOM keyboard behind Stevia was removed at three layers: the
  fallback is permanently disabled, CSS hides any stale panel, and the native
  provider marker is now served and precached. All PWA manifests allow `any`.
- [x] The orientation unit was `Type=oneshot` (`status`) and had no continuous
  sensor owner. It is now a `Type=simple` daemon with a status/request protocol.
- [x] The S10+ rootfs builder omitted orientation entirely. It now installs the
  daemon, package, config/schema, unit, enablement link and clean-rootfs checks.
- [x] The old rollback interval was 4 s. Transform trials are now 75 s by
  default, bounded to 60–90 s, and restored on `no`, saved blank, timeout,
  compositor loss or daemon restart.
- [x] Real sensor remains blocked: LSM6DSO is behind BCM47752 SSP; SSP is down,
  `raw_data=0,0,0`, IIO has no accel channels/scale and no sensor-proxy service.
  Auto modes truthfully report `blocked_sensor_unavailable`; no synthetic data
  is used.
- [x] Console artwork had opaque/large source files in the worktree; the three
  serial/USB/WLAN images are now 256×256 RGBA with real transparency and
  `p46000` cache keys.
- [x] Lockscreen order is Charging, Live console, PC (console middle). The middle
  live-console light also lights for a WLAN-only console, and the transport row
  is larger and moved below the primary row.

## Display path selected

`orientation policy -> effective 0/90/180/270 -> wlr-randr transform on the live
HEADLESS-1 output -> screencopy frame -> nuxel-wl-fb inverse quarter-turn ->
1440x3040 portrait AMOLED scanout`.

Touch is handled by wlroots' output transform and output/device association; the
presenter does not inject pointer coordinates, so the transform is applied once
in each direction.

## Remaining physical acceptance

- [ ] Portrait lock (touch corners, dock, QS, Notes editor)
- [ ] Landscape lock — test L3 armed in Notes; use QS long-press -> Landscape
- [ ] RPortrait lock
- [ ] RLandscape lock
- [ ] Auto (blocked until a real live gravity source exists)
- [ ] Auto (PT) (blocked)
- [ ] Auto (LS) (blocked)
- [ ] 75 s trial commit / no / blank / timeout rollback on the physical phone

## Evidence

`docs/beta-finalization/live/evidence/pwnage-46000/`
