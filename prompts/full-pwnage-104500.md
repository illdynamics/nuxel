# FULL-PWNAGE-104500 — Camera: restore real frame capture on Nuxel

**Target:** Samsung Galaxy S10+ `SM-G975F` / `beyond2lte` / Exynos 9820
**Live access:** `ssh -i ~wicked/.ssh/wicked_wqn_id_rsa root@192.168.178.167`
**Report to produce:** `REPORT-PWNAGE-104500.md`
**Status token:** `FULLY_DONE` | `PARTIAL` | `BLOCKED`

---

## 0. Mission directive

Camera worked previously and must produce a real frame again. A bound driver and
V4L2 device nodes are **not** a camera. Success = the Nuxel camera pipeline opens the
sensor/ISP, captures a frame, and displays it in the Nuxel camera UI, reproducibly,
with the evidence captured.

---

## 1. Current observed state (2026-11-14 15:40–16:00 CET)

```
/dev/video*   : 68 nodes (exynos-fimc-is-* present)
/dev/media*   : NONE
/dev/v4l-subdev* : NONE
nuxel-camera-diag.sh status --json : state=BLOCKED_FIRMWARE,
                                      first_failing_stage=firmware
frame_captured_verified : false
```

`dmesg` shows bound FIMC-IS sensor modules: `2L4` (S5K2L4 rear main), `3M3`
(S5K3M3 tele), `3P9` (S5K3P9 ultra-wide), `3J1` (S5K3J1 front), `4HA` (S5K4H7 IR).

Previously reported missing firmware (re-verify):
`s5k2l4_setfile.bin`, `s5k3m3_setfile.bin`, `s5k3p9_setfile.bin`,
`s5k3j1_setfile.bin`, `s5k4h7_setfile.bin`, `exynos9820_camera.bin`,
`is-camera.bin`, `is-camera-3.bin`, `camera_calibration.bin`, `setfile.bin`.

Sibling mission: the camera, GNSS and rotation paths all depend on the SSP/sensor-hub
runtime — see **`full-pwnage-104400.md`** (TEE stall) and **`full-pwnage-104100.md`**
(GPS restore). Fix those first if the SSP MCU is down.

Relevant existing material:

- `REPORT-CAMERA.md`, `PWNAGE-CAM-REPORT.md`, `full-pwnage-cam.md`,
  `README-CAM.md`, `PWNAGE-CAM-FIRMWARE-PROVENANCE.md`
- `configs/nuxel/camera/camera.json`, `configs/nuxel/camera/README.md`
- UI: `shell/nuxel-camera-native/`, `shell/nuxel-camera-portal/`
- Diagnostics: `tools/s10plus/a33/nuxel-camera-diag.sh`, `tests/pwnage65000`
- Firmware search paths: `/lib/firmware`, `/vendor/firmware`,
  `/vendor/firmware/camera`, `/vendor/etc/firmware`, `/etc/firmware`

---

## 2. Non-negotiable rules

1. Never present a synthetic/mock/replayed image as a capture.
2. Do not use firmware for a different sensor, device, or region. Verify provenance,
   SHA-256, and exact SM-G975F/beyond2lte compatibility.
3. Samsung ISP/setfiles are proprietary: state precisely what is missing and provide
   a reproducible extraction procedure from the owner's own SM-G975F firmware.
   Do not invent or synthesise binaries.
4. No flashing without explicit approval. Produce a reflash manifest.
5. Do not weaken SELinux or permissions to get nodes to open.
6. Bound every capture attempt with a timeout and guaranteed power/cleanup.

---

## 3. Work order

### Step 1 — Regression window (same method as PWNAGE-104000)

- What changed since it last worked? Kernel rebuilt 2026-11-14 09:51. Compare
  `dmesg`, firmware paths, DTBs and FIMC-IS driver/config against the previous boot
  image (`/root/boot-*.img`, `.bak` copies).
- Check whether the missing blobs were previously present and are now absent
  (deleted, moved, different mount, different path resolution).
- Check `nuxel-camera-diag.sh status --json` and `tools/s10plus/a33/*` output.

### Step 2 — Re-prove the firmware inventory

For each required file: searched paths, result, expected sensor, expected size/hash,
and whether a stock-S10+ copy exists. Classify: present-and-valid /
present-but-wrong / missing. Nothing else counts.

### Step 3 — Media graph

- Determine why there is no `/dev/media*` or subdev graph (DT? driver config?
  deferred probe?).
- If the media controller is expected but absent, fix that first — frames cannot be
  routed without it.

### Step 4 — Capture path

- Use the existing diagnostics to open the correct FIMC-IS pipeline for the rear
  main sensor.
- Capture one frame; verify it is a real 4032×3024 (or sensor-native) image with
  plausible entropy, not black/green/uninitialised.
- Display it in the Nuxel camera UI and capture the UI.

### Step 5 — Verify and persist

1. Capture succeeds after fresh boot, without manual setup.
2. Front, rear main, ultra-wide and tele each produce a distinct real frame if the
   sensor modules allow it.
3. Nuxel camera app preview + still capture work.
4. Nothing regressed in audio/GPU/GPS.
5. Evidence: raw frame hash, `v4l2-ctl` output, dmesg, UI capture.

---

## 4. Report contract (`REPORT-PWNAGE-104500.md`)

Firmware inventory table, regression findings, media-graph state, exact capture
commands and outputs, frame hashes, UI evidence, rollback and any reflash manifest.
End with `FULLY_DONE` / `PARTIAL` / `BLOCKED` (`BLOCKED_FIRMWARE` is acceptable only
with the precise missing set and an acquisition procedure).
