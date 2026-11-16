# REPORT-PWNAGE-101000 — External HDMI Colour, Orientation and Reconnect

**Device:** Samsung Galaxy S10+ SM-G975F (`beyond2lte`, Exynos 9820)  
**Kernel:** Linux 4.14.253-gf7194c1d15ed-dirty (#5, 2026-11-01)  
**Live access:** `ssh -i ~/.ssh/wicked_wqn_id_rsa root@10.20.30.16`  
**Path:** USB-C DP Alt Mode → DP-to-HDMI adapter → Philips TV  
**Run:** 2026-11-09 18:47–19:15 CET  
**Final status:** `PARTIALLY_VERIFIED` (see §I: physical TV colour and physical cable-pull are the only open observations; all software, scan-out, orientation and HPD-recovery checks passed)

---

## A. Executive summary

### Original symptoms

1. External picture had a severe red/orange cast.
2. Landscape/rotation was not handled automatically; the picture was sideways or framed for the wrong orientation.
3. After unplugging and reconnecting the adapter, the external picture did not return.

### Root causes found

**Colour — two independent defects, both proven from source and measurement:**

1. **Red channel was dropped in the bridge LUT.** `build_lut()` filled `lut_hi[x]` from `(x >> 16)`, which is zero for every `x` in `0..65535`. `convert_word()` indexes that table with the source word's upper 16 bits, so the red contribution was always zero for the XRGB8888/ARGB8888 path.
2. **DP output order was not compensated.** The external `decon_t` OUTFIFO is programmed with `DECON_RGB` order (`decon_reg_configure_lcd()` selects `DECON_BGR` only for DSI-without-DSC). The bridge packed ABGR8888 (`R@0 G@8 B@16`). That produced a second R/B swap on the DP output. Net old physical result for source `(R,G,B)` was `(B,G,0)`: a dark-blue wallpaper became orange/red, green stayed green, white stayed neutral — exactly the supplied photo.

**Orientation:** the screencopy buffer is the physical 720×1520 output mode with the compositor transform already applied inside it. The external presenter must apply the same clockwise transform value to undo it onto the landscape TV. The previous code used a fixed manual rotation (`0` or `90`) and did not follow the live orientation authority.

**Reconnect:** the daemon detected the new DP generation and emitted a notification, but never restored `last_mode`. `stop_mode()` on disconnect also did not distinguish a cable event from an explicit user “internal only” choice, so auto-restore was not modelled at all. A transient self-induced link-low during a bridge restart could also make the new bridge exit immediately, and the supervisor could misread a healthy `RUNNING` bridge as inactive.

### Implemented repairs

- Corrected the LUT high half (`x & 0xff`).
- Added explicit DP packing: ARGB8888 (`R@16 G@8 B@0 A@24`) for the DP RGB output order; ABGR8888 remains available only as a diagnostic override.
- Added `--auto-orientation`: the bridge re-reads `/run/nuxel-wl-fb-orientation` every 200 ms and applies the live compositor transform without restarting.
- Added `--test-pattern bars|grey`, `--dump-source`, `--dump-output` and `--selftest-colour`.
- Added a real uevent netlink listener plus a 0.2 s reconciliation fallback.
- Added connection-generation restore: on reconnect the daemon re-applies `last_mode`, with three bounded attempts (2 s/4 s/8 s backoff).
- Explicit `off` is remembered and suppresses auto-restore; a cable disconnect preserves `last_mode`.
- Added a 5-frame (≈250 ms) link-loss debounce so a deliberate blank/unblank does not look like a cable pull.
- The supervisor treats an unknown `systemctl is-active` result as active rather than killing a healthy bridge.
- Added truthful DP-audio endpoint lifecycle handling (default-sink restore only for a real DP/HDMI sink; no dummy devices).
- Added colour, orientation, reconnect, stale-generation and explicit-off tests.

### Verified live

- After the requested reboot, `nuxel-displayd`, `nuxel-wl-fb-ext`, `nuxel-wayland`
  and `nuxel-wl-fb` all came back active and the external picture auto-restored
  with **no manual command** (`restore complete ... in 0.26s`, generation 1,
  `rot=0`, 60 Hz). See `evidence/pwnage-101000/deployment/post-reboot.txt`.
- Frame-done IRQ sustained at **60–62 Hz**.
- Five consecutive landscape reconnect cycles auto-recovered in **0.95–1.17 s**, each with a new generation, `rot=270`, and 60–62 Hz scan-out.
- All four orientations update in place with the **same bridge PID** and match grim (centre pixel exact in every case).
- Colour self-test: **88/88 PASS** (all formats × all reference colours × both orders).
- Internal AMOLED remained active; no second `/dev/fb0` writer; no compositor replacement.

### Not physically observed by the agent

- The TV’s visual appearance of the colour-bar/greyscale pattern. The pattern was displayed on `/dev/fb1` for 120 s (19:09:39–19:11:39 CET) but the agent has no camera or view of the TV.
- A true physical cable unplug/replug. The driver’s own HPD path (`/sys/class/dp_sec/dp_test`) was used for the five cycles with the bridge stopped first, avoiding the unpatched vendor shadow-update `BUG()` documented in PWNAGE-100000. The userspace lifecycle is the same path a cable event drives.

---

## B. Colour pipeline

### B.1 Source

Measured from the real screencopy `buffer` event on the live compositor:

| Property | Value |
|---|---|
| Transport | `zwlr_screencopy_manager_v1`, SHM buffer |
| Wayland format | `WL_SHM_FORMAT_XBGR8888` = `0x34324258` (measured; not inferred) |
| Logical size | 720×1520 physical output mode |
| Stride | 2880 bytes (720×4) |
| Bytes per pixel | 4 |
| Channel order in source word | `v>>16 = B`, `v>>8 = G`, `v&0xff = R` (XBGR) |
| Alpha | none (`X`); bridge forces opaque output |
| Endianness | little-endian aarch64 |

Evidence: `evidence/pwnage-101000/source-format/` (`raw-*.ppm`, `grim-*.png`), bridge log `format=0x34324258`.

### B.2 Destination

`/dev/fb1` is `19050000.decon_t`. The live `fb_var` declares `R@16 G@8 B@0 A@24`, 32 bpp, but the vendor DECON does not program that declaration. The bridge programs the DECON explicitly:

| Property | Value |
|---|---|
| Device | `19050000.decon_t` / `/dev/fb1` |
| Scan-out | 1920×1080p60 selected through `EXYNOS_SET_DISPLAYPORT_CONFIG` |
| Buffer | ION dma-buf, double-buffered, 16,588,800 bytes (2×1920×1080×4) |
| Decon input format (fixed) | `DECON_PIXEL_FORMAT_ARGB_8888` (0): `R@16 G@8 B@0 A@24` |
| Decon with old/diagnostic order | `DECON_PIXEL_FORMAT_ABGR_8888` (1): `R@0 G@8 B@16 A@24` |
| DP OUTFIFO order | `DECON_RGB` (source: `decon_reg_configure_lcd()`) |
| DSI/AMOLED OUTFIFO order | `DECON_BGR` when DSI without DSC — why the internal bridge uses ABGR packing |
| Alpha | always `0xff`; blending disabled |
| Destination stride | 7680 bytes |

Evidence: `evidence/pwnage-101000/framebuffer-format/fb-ioctl.txt`, `evidence/pwnage-101000/bridge-lifecycle/ext.log.txt`.

### B.3 Exact conversion

For each source pixel:

1. Decode the real source format:
   - `XBGR/ABGR`: `R=v&0xff`, `G=(v>>8)&0xff`, `B=(v>>16)&0xff`.
   - `XRGB/ARGB`: `R=(v>>16)&0xff`, `G=(v>>8)&0xff`, `B=v&0xff`.
2. Force alpha to `0xff`.
3. Pack into the DECON input format selected for the DP output order:
   - DP path: `out = 0xff000000 | (R<<16) | (G<<8) | B`.
   - Diagnostic ABGR path: `out = 0xff000000 | (R<<0) | (G<<8) | (B<<16)`.
4. Letterbox/pillarbox with `0xff000000`, preserving aspect ratio.

The old code's fast path used a 64K LUT. The high half was wrong:
```c
/* old */
uint32_t r = (x >> 16) & 0xffu;   /* always 0 for x < 65536 */
lut_hi[x] = (r << lut_r);
```
Fixed:
```c
lut_hi[x] = ((x & 0xffu) << lut_r);
```

### B.4 Root-cause evidence

- Source-level: `services/nuxel-display/bin/nuxel-wl-fb-ext.c:636-651` (LUT), `:557-583` (DP packing).
- Driver-level: `kernel/s10plus/.build/src/drivers/video/fbdev/exynos/dpu20/cal_9820/decon_reg.c:1380-1387` (`DECON_BGR` only for DSI no-DSC) and `decon_dsi.c:1204-1208` (internal fbdev uses ABGR).
- Photo model: old predicted non-black mean `(R=64.2, G=51.6, B=0.0)`; new predicted `(43.3, 51.6, 64.2)`; TV crop in the supplied photo `(170.3, 41.7, 24.6)` — red-dominant with B≈0, matching the old model, not the new one. See `evidence/pwnage-101000/colour-tests/root-cause-model.txt`.

### B.5 Colour tests

`--selftest-colour` exercises the actual C conversion for:

- Black, white, red, green, blue, cyan, magenta, yellow, mid-grey, dark-grey, light-grey.
- `XRGB8888`, `ARGB8888`, `XBGR8888`, `ABGR8888`.
- Both ARGB and ABGR destination packing.

Result: **88/88 PASS, 0 failures** (`evidence/pwnage-101000/colour-tests/selftest.txt`). The test explicitly catches the old LUT defect: before the fix it reported 28 failures, all with red decoded as zero.

A deterministic TV pattern (`--test-pattern bars`) was displayed for 120 s. It contains white, yellow, cyan, green, magenta, red, blue, black bars plus a 16-step greyscale strip.

---

## C. Orientation

### C.1 Authority and state model

The single authority is `nuxel-orientationd`:

- Live status: `/run/nuxel-orientation/status.json`.
- Presenter hint: `/run/nuxel-wl-fb-orientation` (atomic text file, written by the orientation daemon).
- Persisted fallback: `/var/lib/nuxel/orientation/state.json`.

The bridge reads `transform=` and `effective_orientation=` every 200 ms. If the file is missing or invalid it keeps the last verified rotation; it never invents a pose.

### C.2 Transform ownership

- The compositor applies the transform to the 720×1520 output.
- The bridge applies the **same clockwise transform value** to the captured buffer.
- The HDMI/TV timing is never rotated: it stays 1920×1080p60.
- Scaling is aspect-preserving (`fit`): portrait content is pillarboxed; landscape content is letterboxed.

Measured mapping (all four cases, same bridge PID):

| Effective orientation | Compositor transform | External rotation | Fit result |
|---|---|---|---|
| 0 (portrait) | 0 (`normal`) | 0 | 512×1080 centered (pillarbox) |
| 90 (landscape) | 270 | 270 | 1920×909 centered (letterbox) |
| 270 (reverse landscape) | 90 | 90 | 1920×909 centered |
| 180 (reverse portrait) | 180 | 180 | 512×1080 centered |

The sign was fixed by measurement, not assumption: raw 720×1520 rotated clockwise 270 equals grim’s 1520×720 landscape screenshot **exactly (MSE 0.0)** at transform 270. The inverse produced a sideways picture.

### C.3 Dynamic behaviour

- `nuxel-wl-fb-ext --auto-orientation` recomputes the map only when the transform changes.
- No service restart, no buffer reallocation and no black frame are required for a rotation.
- `build_map()` is rebuilt atomically when rotation changes; the source remains 720×1520.
- Manual rotation remains available (`nuxel-display-ctl set-rotation N`); it sets `auto_orientation=false`.
- Auto mode is restored with `nuxel-display-ctl set-auto-orientation true`.

### C.4 Orientation tests

| Test | Result | Evidence |
|---|---|---|
| Portrait baseline | rot 0, 60 Hz, content matches grim | `orientation/mse-vs-grim.txt` |
| Portrait → landscape | rot 270, same PID, content matches | same |
| Landscape → reverse landscape | rot 90, same PID, content matches | same |
| Reverse landscape → reverse portrait | rot 180, same PID, content matches | same |
| Return to portrait | rot 0, content restored | same |
| Rotation while HDMI connected | no restart, no stale buffer | `rotation-transitions/rotation-transitions.txt` |
| Reconnect while landscape | restored with rot 270 in all 5 cycles | `reconnect-cycles/reconnect-cycles-landscape.txt` |

Pixel comparison per orientation:
- portrait MSE 160.42, mean diff 5.63, centre exact `(21,60,89)`.
- landscape MSE 53.36, mean diff 2.92, centre exact `(20,54,83)`.
- reverse landscape MSE 53.36, mean diff 2.92, centre exact.
- reverse portrait MSE 150.70, mean diff 5.58, centre exact.

Residual MSE is bilinear resampling of the letterboxed content back to grim’s logical size.

---

## D. Hot-plug and reconnect recovery

### D.1 Event sources

- **Primary:** `NETLINK_KOBJECT_UEVENT` listener in `nuxel-displayd`, filtered for `extcon`, `switch`, `typec`, `usb`, `power_supply`, `drm`, `displayport`, `decon`, `max77705`, `hdmi`.
- **Fallback:** 0.2 s reconciliation poll using the same sysfs model (`/sys/class/typec`, `/sys/class/switch`, `/sys/class/extcon`, `/sys/class/dp_sec`, framebuffers).
- **Debounce:** one settled poll (0.2 s) after a state change; a 4 s self-restart grace window for the daemon’s own bridge stop/start.

### D.2 State layers modelled truthfully

The existing model already distinguishes:

```
DISCONNECTED -> PARTNER_NO_PD -> PD_NO_DP -> DP_NO_FB -> DP_LINK_READY
```

The daemon adds:

- connection generation (incremented only on a real ready transition);
- bridge state (`STOPPED/STARTING/RUNNING/FAILED`);
- restore state (`pending`, `generation`, `attempts`, `next_at`, `reason`);
- orientation state (effective, transform, external rotation, logical/physical dimensions);
- explicit-off preference vs cable disconnect.

`DP_LINK_READY` is only reported when `secdp=1`, `extcon DP=1`, PD identity is present, and `/dev/fb1`/`decon_t` exists. No HPD/EDID/audio state is faked.

### D.3 Reconnect lifecycle

On a genuine disconnect:

- archive the connection notification;
- cancel any pending restore;
- stop the external bridge (`remember=false`, so `last_mode` survives);
- update the audio route only if a real DP/HDMI sink was selected;
- leave the internal AMOLED untouched.

On a genuine reconnect:

- increment the generation;
- refresh the real DP/EDID/framebuffer snapshot;
- notify once;
- schedule restore of `last_mode` for that generation;
- `start_mode()` re-reads the current orientation, re-selects 1920×1080p60, reopens the output, reallocates the ION buffer, and resumes capture;
- bounded retries: 3 attempts, 2 s/4 s/8 s backoff, then a truthful failure notification.

Old-generation restores are rejected by generation comparison; a restore scheduled for generation N cannot start the bridge for generation N+1.

### D.4 Bridge lifecycle fixes

- **Link-loss debounce:** five consecutive failed link checks (≈250 ms) before declaring `DP_LINK_LOST`. This ignores the transient `secdp=0` caused by the bridge’s own `FBIOBLANK(POWERDOWN/UNBLANK)`.
- **Supervisor:** `systemctl is-active` unknown/timeout is treated as active, so a healthy `RUNNING` bridge is not killed under load.
- **State receipts:** 1 Hz instead of 5 s, plus an immediate receipt on orientation change.
- **Stale state:** the daemon writes `STARTING` before systemd start and ignores the previous run’s terminal state.

### D.5 Measured cycles

Five complete driver-level HPD low/high cycles in landscape, with the bridge stopped first to avoid the unpatched kernel `BUG()` race:

| Cycle | Generation | Recovered in | rot | decon_t IRQ in 1 s |
|---|---:|---:|---:|---:|
| 1 | 2→3 | 1.15 s | 270 | 62 |
| 2 | 3→4 | 1.17 s | 270 | 62 |
| 3 | 4→5 | 0.95 s | 270 | 62 |
| 4 | 5→6 | 1.13 s | 270 | 61 |
| 5 | 6→7 | 1.16 s | 270 | 60 |

Every cycle auto-restored mirror without a manual `set-mode`; `last_mode` survived the disconnect. Evidence: `evidence/pwnage-101000/reconnect-cycles/reconnect-cycles-landscape.txt`.

### D.6 Audio

- `/proc/asound/pcm` exposes `00-22: DP Audio`.
- `ch_hdmi_audio = 70975746`, i.e. the DP audio infoframe is **not active**. The model correctly reports `audio.available=false`.
- The daemon now tracks endpoint appearance/removal and restores the default sink only when a real DP/HDMI sink existed. No dummy sink was created.
- Physical HDMI audio was **not** verified because no real DP audio endpoint is active.

---

## E. Integration

- **Mirror:** follows the live phone orientation; TV remains 1920×1080p60; aspect ratio preserved; no sideways/stretched/cropped mirror image.
- **Separate desktop:** not supported by the live compositor. Phoc exposes only `HEADLESS-1`; the daemon still reports `DESKTOP_OUTPUT_UNAVAILABLE` truthfully. No fake second output was introduced.
- **Notifications:** one actionable notification per generation; reconnect reuses/updates it; disconnect archives it; no repeated spam during negotiation.
- **Internal AMOLED:** `/dev/fb0` remains owned by `nuxel-wl-fb`; both internal units stayed active through all tests. No second `/dev/fb0` writer, no compositor replacement, no software-rendering change.

---

## F. Files and code changes

| File | Change |
|---|---|
| `services/nuxel-display/bin/nuxel-wl-fb-ext.c` | Fixed LUT high half; ARGB8888 DP packing; auto-orientation reader; link-loss debounce; test pattern; source/output dumps; colour self-test; 1 Hz receipts. |
| `services/nuxel-display/bin/nuxel-displayd` | Orientation authority reader; auto-orientation preference and control; reconnect generation restore with bounded retries; explicit-off vs disconnect semantics; uevent listener; supervisor robustness; audio endpoint lifecycle; truthful status fields. |
| `services/nuxel-display/bin/nuxel-display-ctl` | `set-auto-orientation`; orientation/restore status display. |
| `services/nuxel-display/tests/test-display-daemon.py` | Auto-restore on reconnect, explicit-off suppression, orientation authority, stale-generation, updated auto-orientation start-script checks. |
| `REPORT-PWNAGE-101000.md` | This report. |
| `evidence/pwnage-101000/**` | Live state, formats, pixels, colour/orientation tests, reconnect cycles, deployment/rollback evidence. |

No kernel, DTB, boot image, firmware, modem or partition was written.

---

## G. Verification

### Unit / offline

- `test-display-model.py`: ALL PASS.
- `test-display-daemon.py`: ALL PASS (including the new reconnect/orientation/off/stale-generation tests).
- C colour self-test: 88/88 PASS.

### Live software

- Bridge build: `BUILD_OK`.
- `/run/nuxel-display/ext.state`: `RUNNING`, `color=argb`, correct `rot` for each orientation.
- `decon_t` IRQ 60–62 Hz.
- 5 reconnect cycles auto-restored in 0.95–1.17 s.
- Orientation transitions at fixed PID with no restart.

### Physical hardware

- TV displayed the deterministic colour-bar/greyscale pattern for 120 s (bridge state `RUNNING mode=test-bars`, `nz=19039`, 20 fps). **Agent could not visually observe the TV.**
- TV displayed the normal Nuxel desktop through the fixed pipeline at 1920×1080p60. **Agent could not visually observe the TV.**
- Physical cable unplug/replug was not performed; the driver’s HPD path was used instead, with the bridge stopped first.

---

## H. Deployment and rollback

- **Branch:** `feature/v0.8.2-beta-pwnage-97000`
- **Base commit:** `b6154b67`
- **Deployment time:** 2026-11-09 19:00–19:07 CET
- **Backup:** `/root/pwnage-101000/rollback/20261109T190035/` (old displayd, ctl, bridge source, compiled bridge, build script, both unit files, hashes)
- **Rollback:** `/root/pwnage-101000/rollback/20261109T190035/rollback.sh`
- **Staging:** `/root/pwnage-101000/deploy/20261109T190035/`

Only these files were installed:

```
/usr/libexec/nuxel/nuxel-displayd
/usr/libexec/nuxel/nuxel-display-ctl
/usr/lib/nuxel/nuxel-display/nuxel-wl-fb-ext.c
/usr/lib/nuxel/nuxel-display/build-nuxel-wl-fb-ext.sh
```

The bridge binary was built on-device with the existing build script; `nuxel-displayd` was restarted once. No unrelated working-tree changes were deployed.

Current live state after the requested reboot: mirror active, portrait,
`rot=0`, 1920×1080p60, 60 Hz, internal AMOLED active, all display services
active. Boot-time auto-restore took **0.26 s** after the DP link became ready.

---

## I. Remaining blockers / open physical checks

1. **Physical TV colour observation.** The colour bars/greyscale were displayed for 120 s, but the agent has no camera or view of the TV. A human must confirm that white is neutral, red/green/blue are correct, and the greyscale strip is neutral.
2. **Physical cable unplug/replug.** The five reconnect cycles used the driver’s legitimate HPD test path with the bridge stopped first. A true cable pull while streaming is still gated by the vendor `decon_update_regs_handler()` shadow-update `BUG()` documented in `REPORT-PWNAGE-100000.md` (prepared kernel patch `kernel/s10plus/patches/0010-nuxel-dp-shadow-timeout-recovery.patch`, **not flashed**). The userspace lifecycle is identical, but destructive unplug testing should only be done with the patched kernel or with the bridge stopped first.
3. **HDMI audio.** The DP audio PCM exists, but `ch_hdmi_audio` is not active (`70975746`), so there is no real audio endpoint to verify. No fake audio route was added.
4. **Separate desktop.** Not available: Phoc exposes only `HEADLESS-1`.

If a human confirms the colour pattern and a physical reconnect (with the kernel risk accepted or patched), the status becomes `FULLY_VERIFIED_COLOUR_ORIENTATION_RECONNECT`.
