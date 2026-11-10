# REPORT-PWNAGE-100000 — USB-C → HDMI / DisplayPort Alt Mode

**Device:** Samsung Galaxy S10+ SM-G975F (`beyond2lte`, Exynos 9820)
**Kernel:** Linux 4.14.253-gf7194c1d15ed-dirty (#5 SMP PREEMPT)
**Userspace:** Fedora 43 aarch64 / Nuxel 0.8.2-beta
**Live access:** `ssh -i ~/.ssh/wicked_wqn_id_rsa root@10.20.30.16`
**Date:** 2026-11-09
**Adapter (electrical identity):** USB-PD VID `0x35A3`, PID `0x2003`; DP DFP type HDMI; orientation CC1; 4 lanes; link rate 6 (HBR2). Physical model markings: unknown (not captured this run).

---

## A. Executive result

**Primary status: `FIX_IMPLEMENTED_AWAITING_PHYSICAL_TEST`**

This run disproved the previous report's central conclusion and found the real defect.

The attached adapter **does** negotiate USB-PD Structured VDM and DisplayPort Alt Mode with the S10+. On the current boot the S10+ reports:

```
/sys/class/sec/ccic/usbpd_ids      = 35a3:2003
/sys/class/switch/secdp/state      = 1
/sys/class/extcon/extcon0/state    = DP=1
Displayport: CCIC_NOTIFY_ID_DP_CONNECT, 1
Displayport: VID:0x35A3, PID:0x2003
Displayport: Read DPCD REV NUM ...        (AUX works)
Displayport: Full Link Training Finish - : 06 04   (4 lanes, HBR2)
Displayport: DFP type: HDMI(0x1C)
```

The DP link trains and the DP controller is healthy. The failure was **Nuxel userspace never enabling and programming the external decon (`decon_t`) scan-out path**. The vendor DP driver only raises the `secdp` switch and waits for userspace to start the external display; `decon2` starts scan-out only when userspace unblanks `/dev/fb1` and submits the vendor `S3CFB_WIN_CONFIG` ioctl with a dma-buf.

After implementing that path (userspace-only), the hardware is demonstrably streaming video:

- `decon-2 decon_enable  (state: OFF -> ON)`
- `Displayport: displayport_enable video: V640X480P60`
- `decon_t` SFR dump is programmed for **640×480** (`01e00280`)
- `decon2` event log shows repeated `WIN_CONFIG`, `DPP_WINCON`, `DPP_FRAMEDONE`, `FENCE_RELEASE`
- `19050000.decon_t` frame-done IRQ and `130b0000.displayport` IRQ both advance at ~60 Hz
- the exact scanned ION dma-buf half samples **nz=1123** non-black pixels (mirrored UI content)
- SysMMU faults: 0; no persistent DP FIFO underflow after startup
- internal AMOLED (`/dev/fb0`, `nuxel-wl-fb`) remained active throughout

**What is not yet proven:** the actual TV picture was not observed by the agent. This report does not claim physical success. The final physical check is the TV screen itself (Section F.3). All controller-level and software-level prerequisites are now green.

**Kernel / DTB / firmware reflash is NOT required.** The repair is a userspace integration fix.

---

## B. Root cause

### B.1 The previous diagnosis was wrong

PWNAGE-99000 concluded that the adapter “never presents a USB-PD identity and never completes DP Alt Mode VDM negotiation”, based on:

```
supports_usb_power_delivery=no
usbpd_ids=0000:0000
usbpd_type=0
secdp=0
extcon DP=0
```

That snapshot was not the steady-state truth for the currently attached adapter. On this boot the same adapter reports `35a3:2003`, `secdp=1`, `extcon DP=1`, and a fully trained 4-lane HBR2 DP link with readable DPCD and a DFP of type HDMI. The `99000` report therefore blamed the adapter/TV while the actual defect was downstream in Nuxel.

### B.2 Primary defect — decon2 was never enabled

`displayport_hpd_changed()` in `drivers/video/fbdev/exynos/dpu20/displayport_drv.c`:

```c
displayport_set_switch_state(displayport, 1);       /* raises secdp/extcon */
timeout = wait_event_interruptible_timeout(..., displayport->state == DISPLAYPORT_STATE_ON, 3000ms);
if (!timeout) displayport_err("enable timeout\n");
```

The vendor design expects userspace (Samsung's display HAL) to react to `secdp=1` by:

1. enabling `decon_t` (`FBIOBLANK(FB_BLANK_UNBLANK)` on `/dev/fb1`), which reaches `decon_enable()` and then `displayport_enable()`; and
2. programming decon2 scan-out with the vendor `S3CFB_WIN_CONFIG` ioctl using a dma-buf.

Nuxel had neither. The old bridge only wrote pixels into the `/dev/fb1` mapping. That mapping is a kernel-owned ION dma-buf (`ion-24`, 2,457,600 bytes, attached to `130b0000.displayport`) that **cannot be exported to userspace**, and memory writes alone never start decon2. Result: the link trained, `secdp` went high, and the TV received no video.

### B.3 Secondary defect — the deployed bridge was stale

The deployed `/usr/lib/nuxel/nuxel-display/nuxel-wl-fb-ext` was built at 16:59:50, before the source that contains `FBIOBLANK`. `strings` on the running binary contained no `unblank`/`FBIOBLANK` text, and `/run/nuxel-display/ext.log` never printed `fb /dev/fb1 unblanked`. The service reported `RUNNING` and wrote frames, but decon2 stayed `suspended` with 0 frame-done IRQs. A service “RUNNING” state and framebuffer writes were therefore not proof of scan-out — exactly the trap the specification warned about.

### B.4 Secondary defect — daemon race killed the new bridge

`nuxel-displayd.start_mode()` restarted the bridge and then polled `ext.state`. If the previous run had left `state STOPPED`, the poll returned failure immediately and the daemon ran `systemctl stop`, killing the new bridge after frame 1. This was reproduced live (`EXT_BRIDGE_NOT_READY`, `STOPPED`, `frames=1`).

Fix: the daemon now writes `state STARTING` before restarting the bridge, and the bridge publishes `state STARTING` at startup. A regression test covers the stale-`STOPPED` case.

### B.5 Secondary defect — daemon polled `unit_test` and falsified the sink identity

The deployed `nuxel_display.py` read `/sys/class/dp_sec/unit_test` on every poll. Reading that attribute invokes `secdp_unit_test_edid_parse()`, which parses a built-in BenQ SW320 EDID and overwrites the driver's sink identity and timing tables. That is why `monitor_info` showed `BNQ,0x7f54,0x5445` and why the driver log was flooded with `unit test edid parse`. The fixed daemon never reads `unit_test`. The current driver fields are still the last write from the old daemon; a reboot or a real reconnect is required to refresh the true TV EDID. This does not block the 640×480 video path.

### B.6 Why the Pixel reference matters

The Pixel 10 Pro XL proved the TV and HDMI cable can carry an external picture. This run proved the S10+ USB-C/PD/VDM/DP link is also capable. The only missing piece was the Samsung-specific userspace handshake into `decon_t`, not the TV, cable, adapter, PHY, or link training.

---

## C. Negotiation and scan-out timeline (observed)

All entries are from raw kernel logs/sysfs captured under `evidence/pwnage-100000/`.

| Time | Event | Evidence |
|---|---|---|
| 17:26:05 | Displayport driver probe; `CCIC_NOTIFY_ID_DP_CONNECT, 1` | `protocol/dp-driver-link-17-26.txt` |
| 17:26:05 | PD identity `VID:0x35A3, PID:0x2003`; AUX powered | same |
| 17:26:05 | `CCIC_NOTIFY_ID_DP_HPD, 0` then `1`; `hpd changed 1` | same |
| 17:26:06 | `CCIC_NOTIFY_ID_DP_LINK_CONF 3` | same |
| 17:26:06 | DPCD reads succeed (`REV NUM`, link status, branch revision) | same |
| 17:26:06 | Full link training: 4 lanes, rate `0x6` (HBR2), `lane_cr_done=f` | same |
| 17:26:06 | `DFP type: HDMI(0x1C)`; audio init; HPD status 1 | same |
| 17:26:30 | `secdp=1`, `extcon0=DP=1`, `usbpd_ids=35a3:2003`, `fb1=640x960` | `protocol/after-reboot-dp-link.txt` |
| 17:27:09 | old bridge `RUNNING`, writing frames, **decon2 still suspended, IRQ 0** | `physical-tests/mirror-fb1-live.txt` |
| 17:35:07 | controlled `FBIOBLANK(UNBLANK)` → `decon-2 decon_enable OFF->ON`; `displayport_enable video: V640X480P60` | journal, this run |
| 17:36:52 | fixed bridge with unblank → decon2 enables, but without win-config no scan-out (IRQ 0) | this run |
| 17:41:34 | ION dma-buf + `S3CFB_WIN_CONFIG` window 4 → decon2 IRQ 227 at ~60 Hz | this run |
| 17:44:29 | deployed daemon mirror; decon2 stable | `protocol/live-scanout.txt` |
| 17:45:03 | decon2 SFR dump: `01e00280` (640×480), decon enabled | `protocol/decon2-sfr-and-config.txt` |
| 17:47:41 | decon2 event log: `WIN_CONFIG`, `DPP_WINCON`, `DPP_FRAMEDONE`, `FENCE_RELEASE` | `protocol/decon2-sfr-and-config.txt` |

**Observed:** CC attach, PD identity, DP Alt Mode entry, link config 3, HPD, DPCD/AUX, link training, DFP HDMI, decon2 enable, window programming, frame-done at 60 Hz.
**Inferred:** none of the above; each step has a raw kernel/sysfs record. The only inferred item is the final TV picture, which is why the status is not `FULLY_VERIFIED_PHYSICAL_HDMI`.

---

## D. Kernel / vendor comparison matrix

| Component | Required function | Nuxel status | Samsung reference | Finding |
|---|---|---|---|---|
| Type-C controller (max77705 CCIC) | CC attach, orientation, PD | Present, working (`usbpd_ids=35a3:2003`, CC1) | `max77705` CCIC driver | Present |
| USB-PD / SVDM | Discover Identity, DP Alt Mode | Present, working | `max77705` + `displayport_drv.c` | Present |
| DP Alt Mode entry | `CCIC_NOTIFY_ID_DP_CONNECT`, link config 3 | Present, working | same | Present |
| DP link training | 4 lanes, HBR2 | Present, working | same | Present |
| AUX / DPCD | DPCD reads, branch revision | Present, working | `displayport_aux`/`secdp_aux_control.c` | Present |
| HPD | `CCIC_NOTIFY_ID_DP_HPD` | Present, working | same | Present |
| Combo PHY | DP lane mux | Present, working | `exynos_usbdrd` | Present |
| DP controller | Video stream | Present, working (`130b0000.displayport` IRQ 60 Hz) | `displayport_drv.c` | Present |
| `decon_t` enable | `FBIOBLANK(UNBLANK)` handshake | **Was never called; fixed** | vendor display HAL | Fixed |
| decon2 scan-out | `S3CFB_WIN_CONFIG` with dma-buf | **Was never called; fixed** | vendor display HAL / HWC | Fixed |
| External framebuffer | `/dev/fb1` (decon_t) | Present, 640×480 | vendor fbdev | Present |
| Decon window ownership | single external writer | Bridge owns fb1 + ION buffer, single flock | HWC | Present |
| EDID identity | real sink identity | **Falsified by `unit_test` polling; fixed** | vendor | Fixed (refresh pending) |
| DP audio | infoframe / PCM | `ch_hdmi_audio=71237634`, PCM exists; physical audio unverified | vendor | Present, physical pending |
| Internal display | AMOLED + internal bridge | Active throughout | vendor | Preserved |

**Kernel configuration relevant to this path (live `/proc/config.gz`):**

```
CONFIG_EXYNOS_DISPLAYPORT=y
CONFIG_SND_SOC_SAMSUNG_DISPLAYPORT=y
CONFIG_EXYNOS_MCD_HDR=y
CONFIG_EXYNOS_VIRTUAL_DISPLAY is not set
CONFIG_DRM_EXYNOS is not set
CONFIG_ION=y
CONFIG_UDMABUF=y
CONFIG_SWITCH=y
CONFIG_EXTCON=y
```

No missing kernel symbol was found. No kernel/DTB/firmware change is required for this fix.

---

## E. Changes implemented

All changes are userspace-only.

### E.1 `services/nuxel-display/bin/nuxel-wl-fb-ext.c`

- Added the Samsung decon_t / ION vendor ABI (`S3CFB_WIN_CONFIG`, `ION_IOC_ALLOC`) mirroring `drivers/video/fbdev/exynos/dpu20/decon.h` for this exact build (`CONFIG_EXYNOS_MCD_HDR=y`, 64-bit `dma_addr_t`, `MAX_DECON_WIN=6`).
- `fb_open()` now:
  - opens `/dev/fb1` for `FBIOBLANK` and the decon ioctl;
  - allocates a 2,457,600-byte ION system-heap dma-buf and mmaps it as the pixel target;
  - calls `FBIOBLANK(FB_BLANK_UNBLANK)` (reaches `displayport_enable`);
  - submits `S3CFB_WIN_CONFIG` for decon window 4 (decon_t `default_win=4`, `default_ch=2`, `ABGR_8888`).
- Added double buffering: each frame writes the inactive half of the 640×960 buffer, submits `src.y = half*480`, then flips.
- Added a sampled non-black counter (`nz`) over the exact scanned half, published in `ext.state` and logs.
- Added a startup `state STARTING` record.
- `fb_release()` closes the ION fd and fb1 cleanly; the internal `/dev/fb0` path is untouched.

### E.2 `services/nuxel-display/bin/nuxel-displayd`

- `_mark_ext_starting()` writes `state STARTING` before restarting the bridge, eliminating the stale-`STOPPED` race.
- Called before both mode start and rotation restart.

### E.3 `services/nuxel-display/lib/nuxel_display.py`

- Never reads `/sys/class/dp_sec/unit_test`; that attribute is a trigger for the vendor test-EDID parser, not a status flag.

### E.4 Tests

- `services/nuxel-display/tests/test-display-daemon.py`
  - fake runner now simulates the bridge publishing `RUNNING` on restart;
  - added `test_stale_stopped_state_does_not_abort_start()`.
- All display model/daemon/provider tests pass (see Section F).

### E.5 No changes to

- kernel, DTB, boot image, firmware, modem, partitions;
- internal `/dev/fb0` writer (`nuxel-wl-fb`);
- compositor / Phoc;
- software rendering or DPI.

---

## F. Verification

### F.1 Automated

| Test | Result |
|---|---|
| `services/nuxel-display/tests/test-display-model.py` | **ALL PASS** |
| `services/nuxel-display/tests/test-display-daemon.py` | **ALL PASS** (incl. stale-state regression) |
| `services/nuxel-bridge/test-hw-providers.py` | **ALL PASS** |

### F.2 Live software / controller (S10+)

| Test | Method | Expected | Actual | Evidence |
|---|---|---|---|---|
| PD identity | `/sys/class/sec/ccic/usbpd_ids` | non-zero | `35a3:2003` | `protocol/live-scanout.txt` |
| DP switch | `/sys/class/switch/secdp/state` | 1 | 1 | same |
| extcon DP | `/sys/class/extcon/extcon0/state` | `DP=1` | `DP=1` | same |
| DP link | kernel log | 4 lanes / HBR2 | finish `06 04`, 4 lanes | `protocol/dp-driver-link-17-26.txt` |
| DFP type | kernel log | HDMI | `DFP type: HDMI(0x1C)` | same |
| decon2 enable | journal | `OFF -> ON` | `decon-2 decon_enable - (state:OFF -> ON)` | this run |
| DP video | journal | `displayport_enable` | `video: V640X480P60` | this run |
| decon2 SFR | debugfs dump2 | 640×480 | `01e00280`, enabled `0x13` | `protocol/decon2-sfr-and-config.txt` |
| window config | debugfs event2 | WIN_CONFIG / DPP_FRAMEDONE | present, repeating | same |
| scan-out rate | `/proc/interrupts` | 60 Hz | +120 per 2 s on both IRQs | `protocol/live-scanout.txt` |
| buffer content | bridge `nz` | >0 | `nz=1123` (rot 90: `1999`) | `ext.state` |
| SysMMU | dmesg | 0 faults | `fault : 0` | `protocol/live-scanout.txt` |
| DP underflow | dmesg | none steady-state | only during bridge restart transition | this run |
| internal display | services + fb0 | active | `nuxel-wayland`/`nuxel-wl-fb` active, fb0 `1440,6080` | `protocol/live-scanout.txt` |
| lifecycle off→mirror→rot90→rot0 | `nuxel-display-ctl` | all RUNNING | all RUNNING, scan-out resumes | this run |
| adapter identity | CCIC + DP | recorded | VID 0x35A3, PID 0x2003 | `protocol/live-scanout.txt` |

### F.3 Physical acceptance test (required, pending)

The agent cannot see the TV. The current live state is a 640×480 mirror of the Nuxel desktop onto the connected adapter/TV. The decisive check is:

1. TV is on the correct HDMI input.
2. Adapter remains connected to the S10+.
3. The TV should show the Nuxel desktop mirrored (letterboxed to 227×480 content inside 640×480).
4. Changing something on the phone should update the TV.

Until this is observed, the status remains `FIX_IMPLEMENTED_AWAITING_PHYSICAL_TEST`, not `FULLY_VERIFIED_PHYSICAL_HDMI`.

### F.4 Notes on the display identity

`monitor_info` still reads `BNQ,0x7f54,0x5445` (BenQ SW320) because the old daemon's `unit_test` polling left the driver's identity/timing tables overwritten. The fixed daemon no longer does this. A reboot or a real disconnect/reconnect is required to read the actual TV EDID and potentially select a higher mode. This is a quality/truthfulness improvement, not a blocker for the 640×480 picture.

---

## G. Deployment and rollback

- **Repository:** `/Users/wicked/x/nuxel`
- **Branch:** `feature/v0.8.2-beta-pwnage-97000`
- **Commit:** `b6154b67ec1e421729cea8053839ce9cfae9095d`
- **Deployment command:**
  ```
  python3 scripts/nuxel-deploy-live.py --host 10.20.30.16 --user root \
    --key ~/.ssh/wicked_wqn_id_rsa --apply --no-restart
  ```
- **Install semantics:** userspace-only; the live installer backs up every replaced file. No kernel, boot, DTB, firmware, modem or partition write.
- **Latest rollback:** `/var/lib/nuxel/live-deploy/rollback-20261109T164532Z` (27 MB)
- **Previous rollbacks:** `rollback-20261109T164352Z`, `rollback-20261109T164231Z`, `rollback-20261109T155518Z`
- **Services restarted:** `nuxel-displayd.service`, `nuxel-wl-fb-ext.service`
- **Bridge binary:** rebuilt on-device by `/usr/lib/nuxel/nuxel-display/build-nuxel-wl-fb-ext.sh` (source is newer than the old binary).

### Rollback procedure

1. `systemctl stop nuxel-wl-fb-ext.service`
2. Restore every file listed under `/var/lib/nuxel/live-deploy/rollback-20261109T164532Z/` to its absolute path.
3. `systemctl daemon-reload`
4. `systemctl restart nuxel-displayd.service`
5. The internal display path (`nuxel-wayland`, `nuxel-wl-fb`) was never stopped or reconfigured, so it needs no rollback.

---

## H. Remaining work

1. **Physical TV confirmation (required).** Observe the TV while the mirror is RUNNING. If the picture is present and updates, the status becomes `FULLY_VERIFIED_PHYSICAL_HDMI`.
2. **Real EDID refresh (recommended).** Reboot or perform a real disconnect/reconnect with the fixed daemon deployed. This clears the stale BenQ test-EDID fields and should make the driver select a TV-supported mode (likely 1080p) and report the real TV name.
3. **HDMI audio physical check.** The DP audio infoframe is active (`ch_hdmi_audio=71237634`) and the `DP Audio` PCM exists, but no sound has been physically verified.
4. **Separate desktop.** Still unavailable until the compositor exposes a second output; the daemon reports this truthfully.
5. **Adapter markings.** The user should record the printed adapter model/revision for the report and for comparison with the Pixel test.

No kernel/DTB/firmware reflash package is required. If physical output fails despite the green controller state, the next step is to inspect the DP video mute/HDCP path and the adapter’s DFP registers, not to rebuild the kernel.

---

## Evidence index

```
evidence/pwnage-100000/
├── initial/                     # pre-change Type-C/CCIC/PD/DP/extcon/dmesg/journal
├── protocol/
│   ├── dp-driver-link-17-26.txt        # real VDM/DP/link-training trace
│   ├── after-reboot-dp-link.txt        # link + state after boot
│   ├── live-scanout.txt                # live IRQs, services, switches, nz
│   └── decon2-sfr-and-config.txt       # decon2 SFR dump, event log, config
├── implementation/dp_win_test.c        # minimal S3CFB_WIN_CONFIG probe
├── physical-tests/                     # mirror/fb1 transport evidence
├── devicetree/                         # decon_t/displayport nodes
└── comparison/                         # Samsung reference excerpts
```
