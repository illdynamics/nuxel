# REPORT-PWNAGE-100000 — USB-C → HDMI / DisplayPort Alt Mode

**Device:** Samsung Galaxy S10+ SM-G975F (`beyond2lte`, Exynos 9820)  
**Kernel:** Linux 4.14.253-gf7194c1d15ed-dirty (#5 SMP PREEMPT, built 2026-11-01)  
**Userspace:** Fedora 43 aarch64 / Nuxel 0.8.2-beta  
**Live access:** `ssh -i ~/.ssh/wicked_wqn_id_rsa root@10.20.30.16`  
**Run date:** 2026-11-09 17:50–18:36 CET  
**Adapter electrical identity:** USB-PD VID `0x35A3`, PID `0x2003`; DP DFP type HDMI; orientation CC1; 4 lanes; link rate 6 (HBR2)  
**Adapter physical markings:** not captured (unknown; the user should record them)  
**Sink identity (real EDID):** `PHILIPS FTV`, PNP `PHL`, product `0x0000`, serial `0x1010101`  
**Sink EDID support observed:** `V1920X1080P60`, `V1920X1080P50`, `V1920X1080P30`, `V1920X1080P25`, `V1920X1080P24`, `V1280X1024P60`, `V1280X720P50/60`, `V720X576P50`, `V720X480P60`

---

## A. Executive result

**Primary status: `PARTIALLY_FIXED_PHYSICAL_HDMI`**

The real 1080p picture path is now implemented and proven at the controller/scan-out
level, but the agent could not see the TV, and the cable-unplug reboot fix is
prepared but **not flashed** because the recovery safety gate was not verified.

Proven in this run:

- The adapter negotiates USB-PD and DisplayPort Alt Mode with the S10+:
  `usbpd_ids=35a3:2003`, `secdp=1`, `extcon0=DP=1`.
- The DP link trains at **4 lanes, HBR2** (`Full Link Training Finish - : 06 04`).
- The real TV EDID is read: **PHILIPS FTV**, DFP type HDMI.
- The vendor driver is put into **1920x1080p60** through
  `EXYNOS_SET_DISPLAYPORT_CONFIG` on `/dev/fb1` (state `PRESET`), which sets
  `displayport->cur_video` and refreshes `decon->lcd_info`.
- `displayport_enable video: V1920X1080P60` and
  `decon_2 output size for displayport 1920x1080`.
- `19050000.decon_t` frame-done IRQ advances at ~60 Hz (61 per second measured)
  with no DP underflow and no SysMMU faults.
- The exact scanned ION dma-buf contains non-black mirrored UI content
  (`nz=5700` portrait, `17992` landscape, `21377` fullscreen).
- All three real modes work and switch reliably:
  **mirror portrait**, **mirror landscape**, **fullscreen**.
- A connection notification with all real choices is submitted to the Nuxel
  notification hub (`Mirror portrait`, `Mirror landscape`, `Fullscreen`, and
  `Display settings` when separate desktop is unavailable; `Separate desktop`
  is offered only when a real second output exists).
- The internal AMOLED remains active (`/dev/fb0` 1440x6080, 32 bpp; both
  `nuxel-wayland` and `nuxel-wl-fb` active).

Not proven / not done:

- The TV picture was **not observed by the agent**; the final physical check is
  the TV screen itself.
- The **cable-unplug reboot** is caused by a kernel `BUG()` and still exists on
  the running kernel. A validated boot image that removes it is ready in
  `build/out/s10plus/debug-candidates/p100000/`, but it was not flashed because
  TWRP/ADB recovery was not verified from this session.
- **Separate desktop** is not supported by the live compositor: Phoc exposes only
  `HEADLESS-1`. The daemon refuses it truthfully with
  `DESKTOP_OUTPUT_UNAVAILABLE`; no second compositor was introduced.
- HDMI audio was not physically verified.

---

## B. Root cause

### B.1 The previous report was wrong about the link

PWNAGE-99000 concluded that the adapter never negotiated DP because a snapshot
showed `usbpd_ids=0000:0000`, `secdp=0`, `extcon DP=0`, and
`supports_usb_power_delivery=no`. That was transient or incomplete evidence.
On this boot the same adapter reports:

```text
/sys/class/sec/ccic/usbpd_ids      = 35a3:2003
/sys/class/switch/secdp/state      = 1
/sys/class/extcon/extcon0/state    = DP=1
Displayport: CCIC_NOTIFY_ID_DP_CONNECT, 1
Displayport: mon name: PHILIPS FTV
Displayport: Full Link Training Finish - : 06 04   (4 lanes, HBR2)
Displayport: DFP type: HDMI(0x1C)
```

The link, adapter, PHY, AUX, DPCD, EDID, and HPD path are healthy.

### B.2 Primary display defect — the vendor driver kept `cur_video` at 640x480

`displayport_hpd_changed()` resets `displayport->cur_video = V640X480P60` on
unplug (`drivers/video/fbdev/exynos/dpu20/displayport_drv.c:1139`). On a normal
(non-BIST) plug, `displayport_enable()` calls
`displayport_reg_set_video_configuration(displayport->cur_video, ...)` and never
promotes `cur_video` to `best_video`. Only the BIST branch does
(`displayport_drv.c:2140-2144`). Result: the link trains and the TV receives a
valid but 640x480 picture even when the EDID advertises 1080p.

**Fix:** userspace calls `EXYNOS_SET_DISPLAYPORT_CONFIG` on `/dev/fb1` with
`state=EXYNOS_DISPLAYPORT_STATE_PRESET` and the V4L2
`V4L2_DV_BT_CEA_1920X1080P60` timing. That reaches
`displayport_s_dv_timings()`, sets `displayport->cur_video`, and calls
`decon_displayport_get_out_sd()` so `decon->lcd_info` becomes 1920x1080.
A subsequent `FBIOBLANK(FB_BLANK_POWERDOWN)` / `FBIOBLANK(FB_BLANK_UNBLANK)`
reconfigures the decon_t timing generator at 1920x1080.
This is a userspace-only fix; no kernel/DTB/firmware change is needed for 1080p.

### B.3 Reboot on cable unplug — kernel `BUG()` in the decon update worker

The previous boot's ramoops dump (`/proc/last_kmsg`, `dmesg-ramoops-0`) contains
the definitive sequence:

```text
decon2 timeout of updating decon registers
kernel BUG at drivers/video/fbdev/exynos/dpu20/decon_core.c:2612!
Internal error: Oops - BUG: 0 [#1] PREEMPT SMP
PC is at decon_update_regs_handler+0x814/0x900
LR is at decon_update_regs_handler+0x814/0x900
Kernel panic - not syncing: Fatal exception
```

`decon_update_regs_handler()` waits for the decon2 shadow-register update with a
300 ms timeout (`SHADOW_UPDATE_TIMEOUT`). When the USB-C/DP cable is pulled,
an in-flight frame can no longer receive VSTATUS/update-done, the wait times
out, and the vendor driver executes `BUG()`. With `oops=panic` on the command
line this becomes a full reboot. The userspace link monitor cannot eliminate the
race because one frame is always in flight when the cable is pulled.

**Fix prepared:** `kernel/s10plus/patches/0010-nuxel-dp-shadow-timeout-recovery.patch`
makes the DP path treat the register-write failure and shadow-update timeout as
recoverable, exactly as `decon_update_last_regs()` already does:
`decon_err(...); goto end;`. The `end:` path releases old dma-bufs and signals
the retire fence. DSI behavior is unchanged.

**Status:** patch is applied to the build tree, the patched ARM64 Image is built,
and a boot candidate is validated. It is **not flashed** (see Section H).

### B.4 Secondary userspace defects found and fixed

1. **Release-fence fd leak.** The Samsung driver installs one release-fence fd
   per active window in `win_data->config[i].rel_fence`. The bridge closed only
   `retire_fence`, so it leaked one fd per frame. After ~10 minutes the process
   fd table was exhausted and every frame logged
   `decon_create_release_fences: failed to get unused fd`.
   Fixed by closing every returned `rel_fence` and `retire_fence` after the
   ioctl. Live fd count is now stable at 8–10.
2. **Mode-switch restart race.** `systemctl restart` let the old bridge write
   `STOPPED` after the daemon wrote `STARTING`, so alternating mode switches
   aborted. Fixed with explicit `stop -> write STARTING -> start`.
3. **Stale `RUNNING` after SIGKILL.** A killed bridge leaves its last state file
   saying `RUNNING`. The supervisor now requires the systemd unit itself to be
   active before trusting `RUNNING`. A SIGKILL test now restarts the bridge and
   resumes 60 Hz scan-out.
4. **Self-inflicted link-loss events.** The bridge powers decon_t down/up when
   changing modes; that can briefly clear the DP switch state. The daemon now
   ignores non-ready states for a 4 s grace window that it explicitly opens
   around its own bridge restart.
5. **`unit_test` EDID pollution.** Reading `/sys/class/dp_sec/unit_test` runs
   `secdp_unit_test_edid_parse()` and overwrites the sink identity with the
   built-in BenQ SW320 EDID. The daemon never reads it. This run restored the
   real EDID with a driver-level reconnect (`dex` 1 → 0), yielding
   `PHL,0x0,0x1010101` and `mon name: PHILIPS FTV`.
6. **Kernel log spam from polling.** Reads of `ccic/usbpd_ids`,
   `dp_sec/monitor_info`, `dp_sec/dex`, and `dp_sec/dp_drm` each print kernel
   lines. The model now caches them on the live root (2–30 s TTL) and no longer
   polls diagnostic-only ccic attributes. Poll interval is 0.2 s for disconnect
   response without a 12-lines/second log storm.

---

## C. Negotiation and scan-out timeline (observed)

| Time (CET) | Event | Raw evidence |
|---|---|---|
| 17:50:39 | `nuxel-displayd` starts; adapter already attached | journal |
| 17:51:39 | CCIC `ID_DP_CONNECT, 1`; `usbpd_ids=35a3:2003` | `journal-current-kernel.txt` |
| 17:51:40 | `displayport hpd changed 1`; link training | same |
| 17:51:40 | `mon name: PHILIPS FTV`; EDID advertises 1080p60 | same |
| 17:51:40 | `Full Link Training Finish - : 06 04` (4 lanes, HBR2) | same |
| 17:51:40 | `DFP type: HDMI(0x1C)`; `hpd changed 1` | same |
| 17:56:44 | `EXYNOS_SET_DISPLAYPORT_CONFIG`: `set timing 1920x1080p60.0` | dmesg |
| 17:56:44 | `decon_2 output size for displayport 1920x1080` | dmesg |
| 17:56:44 | `displayport_enable video: V1920X1080P60` | dmesg |
| 18:02:12 | Driver reconnect restores real EDID (`dex` 1→0) | dmesg |
| 18:02:26 | Bridge sets 1920x1080p60 and enables decon2 | `ext.log` |
| 18:02:28 | `decon_t` IRQ advances 120 frames in 2 s (60 Hz) | `/proc/interrupts` |
| 18:03:00–18:03:37 | mirror-landscape, fullscreen, mirror-portrait all RUNNING | `mode-matrix.txt` |
| 18:34:19 | SIGKILL bridge → supervisor restart → 60 Hz resumed | journal + IRQ |
| 18:35:24 | Final matrix: all three modes 1080p60, 61 IRQ/s, fds=9 | `mode-matrix.txt` |

**Observed, not inferred:** CC attach, PD identity, DP Alt Mode entry, HBR2
4-lane link, real EDID, 1080p preset, decon2 enable, 60 Hz frame-done IRQ,
non-black dma-buf content, all mode switches, supervisor restart.
**Not observed by the agent:** the physical TV picture and physical audio.

---

## D. Kernel and vendor comparison

| Component | Required function | Live status | Samsung reference | Finding |
|---|---|---|---|---|
| max77705 CCIC | CC attach, orientation, PD | Working (`35a3:2003`, CC1) | max77705 CCIC | Present |
| USB-PD / SVDM | Discover Identity, DP Alt Mode | Working | max77705 + displayport_drv | Present |
| DP Alt Mode entry | `CCIC_NOTIFY_ID_DP_CONNECT` | Working | same | Present |
| DP link training | 4 lanes, HBR2 | Working (`06 04`) | same | Present |
| AUX / DPCD | DPCD reads, branch revision | Working | `displayport_aux`/`secdp_aux_control` | Present |
| EDID | Real sink identity/timings | Working (`PHILIPS FTV`) | `displayport_edid.c` | Present |
| HPD | `CCIC_NOTIFY_ID_DP_HPD`, extcon | Working | same | Present |
| Combo PHY | DP lane mux / PHY enable | Working (link trains) | `exynos_usbdrd` | Present |
| DP controller | Video stream | Working (1920x1080p60) | `displayport_drv.c` | Present |
| Video preset selection | Promote EDID best mode on normal plug | **Vendor defect**: `cur_video` stays 640x480 | vendor HAL sets it via V4L2 | **Fixed in userspace** |
| `decon_t` enable | `FBIOBLANK(UNBLANK)` | Working | vendor display HAL | Present |
| decon2 scan-out | `S3CFB_WIN_CONFIG` + dma-buf | Working (60 Hz) | vendor HWC | Present |
| Release-fence fds | Close driver-installed fds | **Was leaking** | vendor HAL closes them | **Fixed in bridge** |
| Shadow-update timeout | Do not panic on DP unplug | **Vendor `BUG()`** | `decon_update_last_regs()` recovers | **Kernel patch prepared** |
| External fb | `/dev/fb1` (decon_t) | Present, 64x480 var; actual scanout 1920x1080 via own ION buffer | fbdev | Present |
| Separate desktop | Second compositor output | **Not available**; only `HEADLESS-1` | — | **Unsupported by live Phoc** |
| Internal AMOLED | Preserve fb0 writer | Active (1440x6080) | vendor | Preserved |

**Relevant live config:**

```text
CONFIG_EXYNOS_DISPLAYPORT=y
CONFIG_SND_SOC_SAMSUNG_DISPLAYPORT=y
CONFIG_EXYNOS_MCD_HDR=y
CONFIG_DRM_EXYNOS is not set
CONFIG_ION=y
CONFIG_UDMABUF=y
CONFIG_SWITCH=y
CONFIG_EXTCON=y
```

No missing kernel symbol was found for the picture path. The only kernel change
needed is the DP-timeout recovery patch.

---

## E. Changes implemented

All changes are userspace except the prepared kernel patch. No boot, DTB, modem,
or firmware partition was written.

### E.1 `services/nuxel-display/bin/nuxel-wl-fb-ext.c`

- Added the Samsung `EXYNOS_GET/SET_DISPLAYPORT_CONFIG` ABI and preset selection:
  `1920x1080p60` → `1280x720p60` → `640x480p60` fallback.
- The bridge now allocates its own ION dma-buf at the selected mode
  (1920x1080 double-buffered, 16,588,800 bytes) and programs decon2 window 4
  with `src.f_w/f_h` and `dst.f_w/f_h` matching the real mode.
- `fb_open()` powers down decon_t, sets the DP preset, allocates ION, unblanks,
  and submits the first window config.
- Added `--resolution WxH`, `--fit fit|fill`, and `--no-link-watch`.
- Mode defaults: `mirror-portrait` = rot 0/fit, `mirror-landscape` = rot 90/fit,
  `fullscreen` = rot 90/fill.
- The bridge checks `secdp` + `extcon DP` before every submit and stops on link
  loss.
- Close every driver-returned `rel_fence` fd and `retire_fence` after each
  `S3CFB_WIN_CONFIG` (fixes the fd leak).
- On exit, `FBIOBLANK(POWERDOWN)` disables the DP stream and decon2.
- State file now reports mode, source, dst, rotation, fit, frames and `nz`.

### E.2 `services/nuxel-display/lib/nuxel_display.py`

- New modes: `mirror-portrait`, `mirror-landscape`, `fullscreen`, `desktop`
  (with legacy `mirror` alias normalized to portrait).
- `mode_rotation()` and `mode_fit()` helpers.
- `parse_dp_presets()` / `preferred_preset()` selects `V1920X1080P60` from the
  driver preset table and reports `selected_resolution`.
- `mode_choices` list for the UI/notification.
- `display_name_from_monitor_info()` maps `PHL` → `Philips`, `BNQ` → `BenQ`,
  and uses the product identity, never a fabricated model.
- Cached Samsung sysfs reads on the live root to stop log storms; no
  `unit_test` read.
- Notification payload offers portrait, landscape, fullscreen, and desktop
  only when a second compositor output is genuinely available; otherwise the
  fourth action is `Display settings`.

### E.3 `services/nuxel-display/bin/nuxel-displayd`

- 0.2 s poll interval with cached slow attributes.
- `start_mode()` normalizes modes, sets the mode's rotation, passes
  `--resolution`, `--fit`, `--rotate`.
- `_restart_ext()` uses explicit `stop -> write STARTING -> start` to avoid the
  old bridge's `STOPPED` race.
- `_supervise_ext()` restarts a dead bridge and requires the systemd unit to be
  active (fixes stale `RUNNING` after SIGKILL).
- 4 s `_link_grace_until` window around deliberate bridge restarts.
- Status includes `mode_rotation`, `mode_fit`, `mode_choices`,
  `selected_resolution`, `dp_presets`.
- Disconnect still archives the notification and stops the external bridge; the
  internal display is never stopped.

### E.4 `services/nuxel-display/bin/nuxel-display-ctl`

- Accepts `mirror-portrait`, `mirror-landscape`, `fullscreen`, `desktop`, `off`
  (plus legacy aliases) and adds `mode-choices`.

### E.5 Bridge/UI integration

- `services/nuxel-bridge/src/api.py`: display `set-mode` whitelist accepts the
  new mode names.
- `services/nuxel-bridge/src/hw_providers.py`: maps all mirror/fullscreen modes
  to `MIRRORING`, surfaces `selected_resolution`, `mode_choices`, `dp_presets`.
- `pwa/nuxel-home/js/status-bar.js`: notification action handler accepts all new
  mode keys.
- `pwa/nuxel-apps/settings/index.html` / `hardware-settings.js`: four buttons
  (Mirror portrait, Mirror landscape, Fullscreen, Separate desktop), real 1080p
  timing display, mode/fit/rotation state, truthful desktop blocker.

### E.6 Kernel patch (prepared, not flashed)

`kernel/s10plus/patches/0010-nuxel-dp-shadow-timeout-recovery.patch` (+
`.required`) removes the two DP `BUG()` paths in `decon_update_regs()`:

- `__decon_update_regs()` failure → log and `goto end` for `DECON_OUT_DP`.
- shadow-update timeout → log and `goto end` for `DECON_OUT_DP`.

DSI still uses the original fatal path. The patch matches the already-applied
source tree (`git apply --reverse --check` passes).

### E.7 Tests updated/added

- `test-display-model.py`: new notification actions, BenQ/Philips identity.
- `test-display-daemon.py`: four mode actions, new mode names, stop/start
  restart, rotation override, bridge supervisor restart.
- `test-hw-providers.py`: identity expectation.
- All three suites pass (`ALL PASS`).

---

## F. Verification

### F.1 Automated

| Test | Result |
|---|---|
| `services/nuxel-display/tests/test-display-model.py` | **ALL PASS** |
| `services/nuxel-display/tests/test-display-daemon.py` | **ALL PASS** (incl. supervisor) |
| `services/nuxel-bridge/test-hw-providers.py` | **ALL PASS** |
| `python3 -m py_compile` on changed Python files | **OK** |

### F.2 Live software/controller (S10+)

| Test | Expected | Actual | Evidence |
|---|---|---|---|
| PD identity | non-zero | `35a3:2003` | `live/final/verification.txt` |
| DP switch | 1 | `secdp=1`, `DP=1` | same |
| Real EDID | Philips FTV | `PHL`, `PHILIPS FTV` | `dp_error_info` |
| Link training | 4 lanes HBR2 | `06 04` | journal |
| DFP type | HDMI | `HDMI(0x1C)` | journal |
| Selected timing | 1920x1080p60 | `V1920X1080P60` | `mode-matrix.txt` |
| decon_t scan-out | ~60 Hz | 61 IRQ/s | `mode-matrix.txt` |
| Mirror portrait | 1920x1080, rot 0, fit | RUNNING, `nz=5700` | same |
| Mirror landscape | 1920x1080, rot 90, fit | RUNNING, `nz=17992` | same |
| Fullscreen | 1920x1080, rot 90, fill | RUNNING, `nz=21377` | same |
| Bridge fds | stable | 9 per process | same |
| SG/MMU faults | 0 | `fault : 0` | verification |
| DP underflow | none | none | dmesg |
| Internal AMOLED | active | fb0 1440x6080, 32 bpp; services active | verification |
| Supervisor | restart after SIGKILL | restarted, 60 Hz resumed | journal + IRQ |
| Notification actions | real choices | `#47` = portrait/landscape/fullscreen/settings; desktop only when supported | notification store |

### F.3 Physical acceptance test (required, pending human observation)

The agent cannot see the TV. The decisive check is:

1. TV on the correct HDMI input.
2. Adapter remains connected to the S10+.
3. The TV shows the Nuxel desktop in the selected mode:
   - portrait mirror: centered portrait image with side bars,
   - landscape mirror: rotated image with top/bottom bars,
   - fullscreen: cropped fill.
4. Moving/changing something on the phone updates the TV.

Until this is observed by a human, the physical status remains
`PARTIALLY_FIXED_PHYSICAL_HDMI`, not `FULLY_VERIFIED_PHYSICAL_HDMI`.

### F.4 Separate desktop

`wlr-randr` exposes exactly one output:

```text
HEADLESS-1 "Headless output 1"
  Enabled: yes
  Modes:
    720x1520 px (current)
  Position: 0,0
```

There is no second compositor output. `nuxel-display-ctl set-mode desktop`
returns `DESKTOP_OUTPUT_UNAVAILABLE` with the exact blocker. This is reported
truthfully; no second compositor was introduced.

---

## G. Deployment and rollback

- **Repository:** `/Users/wicked/x/nuxel`
- **Branch:** `feature/v0.8.2-beta-pwnage-97000`
- **Commit:** `b6154b67ec1e421729cea8053839ce9cfae9095d`
- **Official deployment:**
  ```bash
  python3 scripts/nuxel-deploy-live.py --host 10.20.30.16 --user root \
    --key ~/.ssh/wicked_wqn_id_rsa --apply --no-restart
  ```
- **Latest official rollback:** `/var/lib/nuxel/live-deploy/rollback-20261109T170058Z/`
- **Manual display-module backups:**
  - `/var/lib/nuxel/manual-backup-20261109T170131Z/nuxel_display.py`
  - `/var/lib/nuxel/manual-backup-20261109T173259Z-nuxel-displayd` (and earlier)
- **Bridge binary rebuilt on-device:**
  `/usr/lib/nuxel/nuxel-display/build-nuxel-wl-fb-ext.sh`
- **Services restarted:** `nuxel-displayd.service`, `nuxel-wl-fb-ext.service`
- **No boot/DTB/firmware/modem/partition writes occurred in this run.**

### Rollback procedure

1. `systemctl stop nuxel-wl-fb-ext.service nuxel-displayd.service`
2. Restore every file under
   `/var/lib/nuxel/live-deploy/rollback-20261109T170058Z/` to its absolute path.
3. Restore the manual display-module backups if needed.
4. `systemctl daemon-reload`
5. `systemctl restart nuxel-displayd.service`
6. The internal display (`nuxel-wayland`, `nuxel-wl-fb`, `/dev/fb0`) was never
   stopped or reconfigured and needs no rollback.

---

## H. Prepared kernel/boot reflash package

### H.1 Why a flash is needed

The running kernel still contains the DP shadow-update `BUG()`. Userspace cannot
remove it; the race is caused by an in-flight decon2 frame when the cable is
pulled. The patch is the minimal correct fix.

### H.2 Package

```text
build/out/s10plus/debug-candidates/p100000/
├── boot-current-s10plus.img                          # exact current boot backup
├── nuxel-beyond2lte-boot-p100000-dp-recovery.img     # candidate
├── Image.patched-final                               # patched raw ARM64 Image
├── config-running.gz                                # live config
├── config-patched                                   # build config (same except initramfs source)
├── current/                                         # unpacked current boot image
└── sha256.txt
```

Hashes:

```text
boot-current-s10plus.img
  2cbc5085d871d043baea6e64aec6c94df60adae18b86fa8696ad942f46b748fc
nuxel-beyond2lte-boot-p100000-dp-recovery.img
  11d13427a3df629f9ab86296c82abbcf6d798ef5c3f5a6bea8f0f9c67432ddac
Image.patched-final
  e42813084477c71a45415466b4bf469e22f5c4ab45b078bb5c9d992148d5d3ff
0010-nuxel-dp-shadow-timeout-recovery.patch
  bea30e7834f9c69faead19c35dcaeb3a4cc0f4c68313d75ebe21aa41d24ec2f0
```

### H.3 Reproducible build

1. Source: `Linux4/android_kernel_samsung_exynos9820`,
   commit `f7194c1d15eded1c2a1a4dc63825b26103435cc0`.
2. Apply all `kernel/s10plus/patches/*.patch` (including `0010`).
3. Use the live `/proc/config.gz` as `.config`; the only build-time difference
   is `CONFIG_INITRAMFS_SOURCE="/root/kbuild/initramfs.cpio"` (the initramfs
   extracted from the current boot image), so the embedded initramfs matches the
   boot image.
4. Build natively on the S10+ with `ARCH=arm64 CROSS_COMPILE=` and
   `KCFLAGS="-fcommon -Wno-error"`.
5. Repack the exact current boot image with
   `boot/s10plus/pack-boot-v1.sh`:
   - kernel `Image.patched-final`
   - ramdisk `current/ramdisk.raw` (byte-identical LZMA-alone)
   - DTB `current/appended.dtb` (byte-identical)
   - addresses `0x10008000/0x11000000/0x10000100`, header v1.
6. Gate: `python3 tools/s10plus/verify-boot-image.py <candidate>` → **PASS**,
   partition slack 65,536 bytes.

### H.4 Flash prerequisites (safety gate — not yet passed)

- Boot the S10+ into a verified TWRP recovery with working ADB. The S10+ has no
  Android-fastboot path; use TWRP `adb` + `dd` or heimdall/Odin Download Mode.
- Physically connect USB data to the Mac (the USB-C port is currently occupied
  by the HDMI adapter).
- Back up BOOT to the Mac first (`scripts/nuxel-adb-flash-pack/scripts/02-backup.sh`).
- Confirm device identity `beyond2lte`, BOOT partition `/dev/block/by-name/boot`
  (or `/dev/block/platform/13d60000.ufs/by-name/boot`), and recovery rollback.
- Battery sufficient; do not flash a mounted target.

### H.5 Boot-only flash command (after the gate passes)

```bash
cd ~/x/nuxel/scripts/nuxel-adb-flash-pack
bash scripts/05-preflight.sh --profile s10plus --boot-only \
  --boot ~/x/nuxel/build/out/s10plus/debug-candidates/p100000/nuxel-beyond2lte-boot-p100000-dp-recovery.img
bash scripts/03-flash.sh --profile s10plus --boot-only --execute \
  --boot ~/x/nuxel/build/out/s10plus/debug-candidates/p100000/nuxel-beyond2lte-boot-p100000-dp-recovery.img \
  --backup-dir ~/x/nuxel/backups/s10plus
```

**Rollback:** flash `boot-current-s10plus.img` with the same BOOT-only command
(the current boot image is preserved and hash-verified). Do not flash
bootloader, modem, PIT, recovery, DTBO, or unrelated firmware.

### H.6 Expected result after flash

- `uname -a` shows a new build identity.
- Pulling the USB-C/DP cable produces
  `decon%d: DP shadow update timeout; recovering` (or the register-update
  variant) instead of `kernel BUG`/panic.
- The phone stays up; the internal AMOLED remains active; re-plugging re-runs
  PD/DP Alt Mode and the display daemon reconnects.

---

## I. Remaining work

1. **Physical TV confirmation (required).** Observe the TV in each mode and
   confirm the picture updates with the phone.
2. **Flash the validated boot image** to remove the unplug reboot, after
   verifying TWRP/ADB recovery and backing up BOOT. This is the only remaining
   hard blocker for safe disconnect/reconnect.
3. **Record adapter markings** (manufacturer/model/revision) for comparison with
   the Pixel 10 Pro XL test.
4. **Separate desktop:** blocked by the live compositor exposing only
   `HEADLESS-1`; do not claim it works.
5. **HDMI audio:** DP audio infoframe/PCM state was not physically verified.
6. **Optional kernel cleanup:** a future kernel patch could also promote
   `cur_video` to `best_video` on normal plug, removing the need for the
   userspace preset ioctl; this is not required because the userspace path is
   proven.

---

## Evidence index

```text
evidence/pwnage-100000/
├── live/initial-20261109T1755.tar.gz      # pre-change snapshot + last_kmsg/ramoops
├── live/final/verification.txt            # final live state, EDID, IRQ, services
├── live/final/connect-notification.json   # real connect notification (#47) with choices
├── live/final/mode-matrix.txt             # portrait/landscape/fullscreen matrix
└── live/final/                            # (add TV photos / human confirmation)

build/out/s10plus/debug-candidates/p100000/
├── boot-current-s10plus.img
├── nuxel-beyond2lte-boot-p100000-dp-recovery.img
├── Image.patched-final
├── config-running.gz
├── config-patched
├── current/
└── sha256.txt
```

**Final honest status:** the S10+ now drives the connected adapter at
**1920x1080p60**, with real DP Alt Mode, real TV EDID, 4-lane HBR2, 60 Hz
decon_t scan-out, and working portrait/landscape/fullscreen modes. The TV
picture itself still requires human visual confirmation, and the cable-unplug
reboot requires the prepared boot-image flash.
