# FULL-PWNAGE-104700 — Display: panel, capture bridges, rotation and HDMI/DP hotplug

**Target:** Samsung Galaxy S10+ `SM-G975F` / `beyond2lte`
**Live access:** `ssh -i ~wicked/.ssh/wicked_wqn_id_rsa root@192.168.178.167`
**Report to produce:** `REPORT-PWNAGE-104700.md`
**Status token:** `FULLY_DONE` | `PARTIAL` | `BLOCKED`

---

## 0. Mission directive

Make the display path truthful and stable: the phone panel renders the real UI, the
framebuffer/screencopy bridges mirror it correctly (cursor included), rotation follows
the existing policy, and USB-C HDMI/DP hot-plug works in both directions.

---

## 1. Current observed state (2026-11-14 16:02 CET)

```
nuxel-displayd.service : active
FB0  (/dev/fb0)        : 1440x6080, 32 bpp   (panel scan-out)
FB1  (/dev/fb1)        : 640x960,  32 bpp    (external bridge, mode-dependent)
dmesg                  : "Displayport: manufacturer :  product : 0 serial num : 0"
                         repeated ~every 2 s (no attached sink right now)
Phoc (Wayland)         : HEADLESS-1, panel-mode 720x1520 @ scale 2 → 360x760 logical
```

Reference material:

- `REPORT-ROTATION.md` — current rotation verdict: `BLOCKED_VENDOR_RUNTIME`
  (SSP MCU not streaming; **the same SSP blocker as PWNAGE-104000 GPS**)
- `REPORT-HDMI-AUDIO-102000.md` — HDMI/DP identity and routing
- `REPORT-PWNAGE-104000.md` — cyan cursor / screencopy overlay-flag fix
- `full-pwnage-103000.md` — LED/edge UI (renders on the panel)

---

## 2. Non-negotiable rules

1. Never change the phone's panel mode from a remote client (VNC/RDP resize must be
   rejected).
2. Screencopy/framebuffer bridges must include the cursor overlay (previous regression:
   `capture_output(scm, 0, output)` dropped it; must be `1`).
3. Do not replace the existing seven-mode rotation policy with a competing daemon.
4. Do not fake sensor samples or force a rotation mode from a static value.
5. Bound HDMI tests; leave the panel in a known-good mode.

---

## 3. Work order

### Step 1 — Panel and bridges

- Confirm the real panel output is what the user sees (compare `grim -c` capture,
  `/dev/fb0` and `/dev/fb1` when an external sink is attached).
- Verify cursor rendering and the cyan Nuxel cursor on panel and external.
- Verify no tearing/partial updates after a long idle.

### Step 2 — Rotation

- Re-confirm `REPORT-ROTATION.md`'s blocker: SSP/LSM6DSO samples are zero.
- If PWNAGE-104000 (SSP/GPS) is completed, re-test auto-rotation with real samples.
- If samples are still unavailable, keep manual/locked modes working and report
  `BLOCKED` honestly — do not force rotation.

### Step 3 — HDMI/DP hotplug

- Attach a USB-C→HDMI monitor: `dmesg` must show a real EDID (manufacturer/product
  non-zero), a DRM mode set, `/dev/fb1` must resize, and the UI must appear.
- Detach: fall back cleanly to the panel without leaving a stale sink.
- Repeat 5× to check stability; watch for the repeated
  `manufacturer : product : 0` loop turning into real values.

### Step 4 — Verify

1. Panel renders UI after reboot.
2. Bridges mirror the real screen, cursor included.
3. HDMI attach/detach ×5 without hang.
4. Rotation per policy (real samples) or documented blocker.
5. Remote desktop (PWNAGE-105000) still shows live updates.

---

## 4. Report contract (`REPORT-PWNAGE-104700.md`)

Panel/bridge evidence, cursor captures, rotation sample data (or SSP blocker
reference), HDMI EDID/mode evidence, hotplug repeat results, rollback. End with
`FULLY_DONE` / `PARTIAL` / `BLOCKED`.

---

## 5. 104000 addendum — `/dev/dri` missing; HDMI video + audio

Measured 2026-11-14 16:25 CET: **`/dev/dri` does not exist** and `/dev/kgsl*` does
not exist. This is the likely cause of both "not smooth" and the remote-desktop
picture problems. Verify whether the DRM/KMS driver (msm/exynos or the Nuxel kernel
fragment in `kernel/s10plus/configs/nuxel-drm-kbase.fragment`) is loaded, bound,
or failed to probe:

```sh
$SSH $PHONE 'ls -la /dev/dri 2>&1; dmesg | grep -iE "drm|msm|kgsl|kbase|dpu|dsi" | tail -60; \
  ls /sys/class/drm 2>&1; lsmod | grep -E "msm|kgsl|drm"'
$SSH $PHONE 'cat /proc/device-tree/soc*/gpu*/status 2>/dev/null; \
  find /sys -name "renderD*" -o -name "card0" 2>/dev/null | head'
```
Then: restore the DRM/KMS path (or identify the KBase/DMA-buf blocker), confirm
`eglinfo`/`glxinfo` (if Xwayland) reports a hardware renderer, and check the
compositor uses it (`phoc` logs, `WAYLAND_DEBUG` sample).

HDMI: verify USB-C→HDMI shows video on the external display **and** routes audio
to HDMI (see 104600). Test with the Mac as source of truth: unplug/replug, change
resolution, confirm no crash and no lost phone touch input.

Acceptance: `/dev/dri/card0` + `renderD128` (or the correct KMS node) present,
hardware renderer string captured, HDMI video + audio working, boot animation
still intact after the reboot test.
