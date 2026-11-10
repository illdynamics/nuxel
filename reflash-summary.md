# Nuxel Live Phone — Reflash Summary (Galaxy S10+, `beyond2lte`)

**Target:** Samsung Galaxy S10+ SM-G975F (`beyond2lte`, Exynos 9820)
**Live OS:** Fedora Linux 43 aarch64 · Kernel `4.14.253-gf7194c1d15ed-dirty` (#5 SMP PREEMPT, 2026-11-01)
**SSH:** `root@192.168.178.167` (`~/.ssh/wicked_wqn_id_rsa`)
**Source of truth:** all `./REPORT-*.md` files in this repo (see "Sources" at the bottom).

---

## 0. TL;DR — what needs a flash vs. what does not

The reports repeatedly distinguish **userspace-only** changes (deploy over SSH, no flash) from
**flash-required** changes (need firmware/runtime and/or a boot/kernel rebuild baked into an A/B image).

- **FLASH REQUIRED (boot + system image):** Camera ISP, Fingerprint TEE, Satellite GNSS, NFC kernel class, Auto-rotation sensor hub, Mobile networking / Shannon modem, MFC hardware decode, DP Alt Mode/HDMI/casting, USB gadget data plane. These need missing firmware blobs and/or missing/boot/kernel config+DT baked into one A/B flash.
- **NO FLASH (userspace only):** Edge screen v1 (PWA), LED/flashlight + edge-lighting overlay, PWNAGE-93000 userspace, PWNAGE-94000 userspace. These ride along in the system image for free but do not force a flash themselves.

All flash-required items point to the **same A/B batch**: boot/kernel (all missing kernel flags + DT) + system image (all firmware/runtime blobs), deployed over TWRP recovery with USB connected, keeping ACM serial as the recovery path and a rollback slot ready.

---

## 1. Components that NEED reflashing

Grouped by subsystem. Each entry lists **what specifically** must be baked in and whether it needs boot/kernel, system image, or both.

### 1.1 Camera — Exynos FIMC-IS (`beyond2lte`) → BLOCKED_FIRMWARE
- **Reflash payload (system image):** vendor sensor setfiles `s5k2l4/3m3/3p9/3j1/4h7_setfile.bin`; Exynos ISP firmware + calibration `exynos9820_camera.bin`, `is-camera*.bin`, `camera_calibration.bin`.
- **Userspace in system image:** dedicated libcamera Exynos FIMC-IS pipeline handler (new; no upstream for this generation).
- **Boot/kernel?** Only if the private FIMC-IS ioctl ABI / DT needs changes. Current kernel already binds the five sensor modules (`fimc-is_sensor_2l4/3m3/3p9/3j1/4ha`).
- **Verified live:** 5 sensor modules bound, 39+ `exynos-fimc-is-*` video nodes, but no `/dev/media*`, no `/dev/v4l-subdev*`, no verified frame.

### 1.2 Fingerprint — Samsung/QCOM qbt2000 → BLOCKED_SECURE_PROVIDER
- **Reflash payload (system/vendor image):** vendor-authorised TEE trusted application / secure provider + secure storage for enrollment/template compare.
- **Boot/kernel?** Likely yes if the secure-provider/TEE handshake needs firmware or a vendor-partition change. The qbt2000 kernel driver itself is present (`/dev/qbt2000_fd`, `/dev/qbt2000_ipc`).
- **Verified live:** sensor/driver/nodes present, `secure_tee=false`, enrollment refused (fail-closed), PIN fallback preserved.

### 1.3 Satellite GNSS — Broadcom BCM4773/47752 BBD → BLOCKED_FIRMWARE
- **Reflash payload (system image):** exact BCM4773 BBD patch/loader firmware + vendor LHD/GPS runtime (`lhd`, `gpsd`).
- **Boot/kernel?** Only if the BBD loader path / DT changes. SPI transport already binds (`spi17.0` → `brcm gps spi`).
- **Verified live:** `/dev/ttyBCM`, `/dev/bbd_patch`, `/dev/bbd_control` present; loader-only; SSP down (`GPS: false`); no NMEA, no fix.

### 1.4 NFC — Samsung S3NRN82 `sec-nfc` → BLOCKED_KERNEL
- **Reflash payload (boot/kernel):** missing kernel NFC class/netlink support is the primary gate (`/sys/class/nfc` empty; no `/dev/nfc0`).
- **Reflash payload (system image):** keep `S3NRN82` firmware `/lib/firmware/nfc/sec_s3nrn82_firmware.bin` (already present + hash-verified) and `nuxel-nfcd` userspace.
- **Verified live:** controller I2C + chardev present, firmware found/verified, daemon running OFF.

### 1.5 Auto-rotation / sensor hub — LSM6DSO + BCM47752 SSP/BBD → BLOCKED_VENDOR_RUNTIME
- **Reflash payload (system image):** SSP/BBD vendor runtime + sensor-hub patch/firmware for the Broadcom hub.
- **Boot/kernel?** Only if the SSP driver/DT must change to bring the MCU out of `ssp_down`.
- **Verified live:** classes/IIO nodes present, accel raw `0,0,0`, `ssp_sensor/enable=0`, kernel log `ssp_down == true`; manual/locked modes work, auto does not.

### 1.6 Mobile networking / Shannon LTE modem → BLOCKED_FIRMWARE / host_transport
- **Reflash payload (system image):** Shannon ModemManager plugin + CP transport userspace.
- **Boot/kernel?** Likely yes if the CP transport/DT must be exposed (shared-memory/IPC/CPIF/SIPC ABI).
- **Verified live:** `/dev/umts_*` nodes present but opaque; `mmcli -L → No modems were found`; no data netdevs, no SIM.

### 1.7 MFC hardware decode (video) → BLOCKED / BLOCKED_GUARDED (PWNAGE-61000/68000/71000)
- **Reflash payload (boot/kernel):** matching patched kernel for MFC.
- **Reflash payload (system image):** MFC firmware + userspace decoder.
- **Verified live:** design implemented; no physical decode proven on the live build.

### 1.8 DP Alt Mode / HDMI / casting → BLOCKED / NOT_IMPLEMENTED (PWNAGE-69000)
- **Reflash payload (boot/kernel):** DRM connector support for DisplayPort Alt Mode.
- **Reflash payload (system image):** NuXtream/casting product + USB-C audio path.
- **Verified live:** no DRM connector; diagnostics/config groundwork only.

### 1.9 USB gadget data plane (NCM/RNDIS/ECM) → PARTIAL / YES (PWNAGE-92000, REPORT-USBNET)
- **Reflash payload (boot/kernel):** kernel config + DT for the needed gadget mode(s). NCM is safe on a fixed path; RNDIS NEEDS_VALIDATION; ECM/ECM-subset/EEM not compiled.
- **Reflash payload (system image):** the safe, mode-aware USB-net helper that lives in the base image.
- **Preserve:** CDC-ACM serial recovery (`acm.usb0`, UDC `10c00000.dwc3`) — keep it alive across every experiment. The recorded 4.14.253 NCM teardown panic must be fixed in the patched kernel (idempotent `misc_deregister`).
- **Verified live:** ACM serial present; no USB network interface exposed on macOS host.

---

## 2. Components that do NOT need a flash (userspace only — ride along free)

These are not forced by a flash, but they belong in the same system image so one A/B flash carries everything:

- **Edge screen v1** — PWA edge-band recognizer + panel + overlay (`pwa/nuxel-home`). Controller `set_grip_data` tuning is optional and read-back only.
- **LED / flashlight + edge-lighting** — rear torch via `/sys/class/leds/torch-sec1`; notification/"edge lighting" is an AMOLED display overlay, not a hardware LED.
- **PWNAGE-93000 userspace** — GTK/Flatpak duplicate icons, sound-mode icons, notification hub + read/archive API + icon resolver (live but uncommitted).
- **PWNAGE-94000 userspace** — Doom SFX audio path, canonical top bar + progressive gestures, app startup fixes, global Adwaita dark, Back lifecycle, desktop geometry (deployed stamp `20261108T173717`, uncommitted).

> Note: the reports recommend **batching** P93/P94 userspace payloads into the same A/B system image as the flash-required items so one TWRP flash carries both.

---

## 3. "All missing kernel flags and stuff" — what to bake into the boot/kernel rebuild

From every report's kernel/DT needs, the combined boot/kernel rebuild should enable/fix:

- **NFC:** register the kernel NFC class/netlink for `sec-nfc` (the primary gate).
- **USB gadget data plane:** NCM (with fixed `misc_deregister` teardown), RNDIS; consider ECM-subset/EEM if host-validated. Keep `CONFIG_USB_CONFIGFS=y`, `CONFIG_USB_DWC3_DUAL_ROLE=y`; preserve ACM (`CONFIG_USB_F_ACM`/`CONFIG_USB_CONFIGFS_ACM`).
- **SSP/Broadcom sensor hub:** bring the MCU out of `ssp_down`; expose accel/gyro/mag enable + decode so auto-rotation and GNSS share a working SSP path.
- **Shannon LTE modem CP transport:** expose the documented shared-memory/IPC ABI so ModemManager finds a modem.
- **MFC hardware decode:** matching MFC driver/firmware path for video decode.
- **DP Alt Mode / DRM:** DisplayPort connector registration (HDMI/casting).
- Keep `CONFIG_TOUCHSCREEN_SEC_TS_Y771` and any other already-working flags intact; do not regress them.

---

## 4. Controlled batch plan (one A/B flash)

| Piece | Partition | Source |
|---|---|---|
| Boot/kernel rebuild (all missing kernel flags + DT fixes above) | `boot` / `dtb` | patched kernel image |
| System image carrying all firmware/runtime blobs + userspace (P93/P94, camera libcamera handler, NFC daemon, orientationd, modem plugin, MFC/DP, USB-net helper) | system (`slot A/B`) | packaged payload |
| Firmware/runtime blobs baked in | `system` (or `vendor`) setfile / ISP / BBD patch + LHD / SSP hub patch / MFC / NFC S3NRN82 firmware | owner-supplied or extracted from vendor partition |

Deployment sequence:
1. Put phone in **TWRP recovery mode**, **USB connected** (owner does this).
2. Flash the patched **boot/kernel** image + package the combined **system** image into the **inactive** A/B slot.
3. Verify critical pieces enumerate/capture on the new slot (camera frame, GNSS fix, NFC class populated, modem found, auto-rotation samples, MFC/DP/USB-net as applicable).
4. Switch to the new slot; keep the previous slot and ACM serial console available for rollback.

---

## 5. Rollback & recovery (keep these ready)

- **Serial:** CDC-ACM `/dev/ttyGS0` on host `/dev/ttyACM*` — preserved in every experiment.
- **WLAN SSH:** `root@192.168.178.167` pinned key — verified before/after.
- **A/B rollback:** switch back to the previous slot if camera/boot/modem/NFC fails.
- **Per-task rollback** (userspace): `./tools/pwnage93000/rollback-pwnage93000.sh`, `./tools/pwnage94000/rollback-pwnage94000.sh`.

---

## 6. Owner inputs still required before/at the flash

- Vendor setfiles + ISP/calibration for camera (`s5k2l4/3m3/3p9/3j1/4h7`), exact BCM4773 BBD patch, SSP/BHD hub patch, MFC firmware, NFC S3NRN82 firmware (provenance/hash/license).
- Lawful access to the qbt2000 TEE trusted application / secure provider.
- A real active SIM for modem/data registration test.
- Physical acceptance: camera scene, GNSS outdoors, NFC tag read, fingerprint enrollment, tilt/rotation, and USB data plane on the owner's macOS host.

---

## 7. Sources (reports used)

| Report | Reflight verdict |
|---|---|
| `REPORT-CAMERA.md` | YES — firmware + ISP/setfiles; boot/kernel only if ABI/DT changes |
| `REPORT-FINGERPRINT.md` | YES — TEE trusted app/provider + secure storage; boot/kernel likely |
| `REPORT-GPS.md` | YES — BBD patch loader firmware + LHD/GPS runtime |
| `REPORT-NFC.md` | YES — kernel NFC class/netlink (primary) + S3NRN82 firmware |
| `REPORT-ROTATION.md` | PARTIAL/YES — SSP/BBD vendor runtime + patch; boot/kernel if driver/DT changes |
| `REPORT-MOBILE-NETWORKING.md` | PARTIAL/YES — Shannon plugin + CP transport (+ DT) |
| `REPORT-USBNET.md` | PARTIAL/YES — NCM/RNDIS/ECM gadget modes kernel+DT; ACM preserved |
| `REPORT-PWNAGE-95000.md` | master audit: MFC/DP/casting blocked, one A/B batch recommended |
| `REPORT-PWNAGE-94000.md`, `REPORT-EDGE.md`, `REPORT-LEDS.md` | userspace-only (ride along in system image) |

---

## 8. Prompt for your agent (copy/paste below)

> See **PROMPT-FOR-MY-AGENT** section at the bottom of this file.

---

## PROMPT-FOR-MY-AGENT (copy/paste into your agent)

```
Nuxel live-phone reflash — Galaxy S10+ (`beyond2lte`, Exynos 9820), Fedora Linux 43 aarch64, kernel `4.14.253-gf7194c1d15ed-dirty`.

CONTEXT
-------
I (the owner) am putting my phone into TWRP recovery mode and connecting it over USB. You have root SSH access (`root@192.168.178.167`, key `~/.ssh/wicked_wqn_id_rsa`) plus WLAN SSH as backup. Reflash the Nuxel live phone with ALL missing kernel flags + firmware/runtime so every hardware-blocked feature is carried in one controlled A/B flash, and batch the userspace-only changes (PWNAGE-93000, PWNAGE-94000) into the same system image.

GOAL
----
Produce ONE boot/kernel rebuild (all missing kernel flags + DT fixes) + ONE system image (all firmware/runtime blobs + userspace), flash them into the INACTIVE A/B slot from TWRP over USB, verify the previously-blocked pieces enumerate/capture on the new slot, then switch slots. Keep ACM serial recovery and a rollback slot ready throughout.

WHAT MUST BE REFLASHED (from ./REPORT-*.md)
-------------------------------------------
Boot/kernel rebuild — enable/fix and bake in:
- NFC: register the kernel NFC class/netlink for `sec-nfc` (primary gate).
- USB gadget data plane: NCM with a fixed idempotent `misc_deregister` teardown (the 4.14.253 panic), RNDIS; preserve CDC-ACM (`acm.usb0`, UDC `10c00000.dwc3`).
- SSP/Broadcom sensor hub: bring the MCU out of `ssp_down` so auto-rotation + GNSS share a working path.
- Shannon LTE modem CP transport: expose the documented shared-memory/IPC/CPIF/SIPC ABI so ModemManager finds a modem.
- MFC hardware decode: matching MFC driver/firmware path.
- DP Alt Mode / DRM: DisplayPort connector registration.
Do not regress already-working flags (e.g. `CONFIG_TOUCHSCREEN_SEC_TS_Y771`).

System image — bake in all missing firmware/runtime + userspace:
- Camera: vendor setfiles (`s5k2l4/3m3/3p9/3j1/4h7_setfile.bin`), Exynos ISP firmware/calibration (`exynos9820_camera.bin`, `is-camera*.bin`, `camera_calibration.bin`), and the libcamera FIMC-IS pipeline handler.
- Fingerprint: qbt2000 TEE trusted application / secure provider + secure storage.
- GNSS: exact BCM4773 BBD patch/loader firmware + vendor LHD/GPS runtime.
- NFC: keep S3NRN82 firmware (`/lib/firmware/nfc/sec_s3nrn82_firmware.bin`) + `nuxel-nfcd`.
- Auto-rotation: SSP/BBD hub patch + vendor runtime; re-enable orientationd.
- Mobile networking: Shannon ModemManager plugin + CP transport userspace.
- MFC / DP casting: matching firmware + userspace decoders.
- USB-net helper (mode-aware) in the base image.
- Batch along: PWNAGE-93000 and PWNAGE-94000 userspace payloads (GTK/Flatpak icons, notification hub/API, Doom SFX audio, canonical top bar, startup fixes, Adwaita dark, Back lifecycle, geometry).

PROCEDURE
---------
1. Confirm the phone is in TWRP recovery mode with USB connected (owner did this); verify `adb devices` / TWRP side and root SSH still works as a fallback path.
2. Build/verify the combined boot/kernel + system payload from the working tree; record commit + build ID + SHA-256 for both images.
3. Flash boot/kernel + package system into the INACTIVE A/B slot via TWRP over USB.
4. On the new slot, verify enumeration/capture: camera frames, GNSS fix, NFC class populated, modem found, auto-rotation samples nonzero, MFC/DP/USB-net as applicable — not just that nodes exist.
5. Switch to the new A/B slot; keep the previous slot and ACM serial console (`/dev/ttyGS0`) available for rollback.
6. Rollback if anything fails: switch back to the previous slot; revert P93/P94 userspace files with `./tools/pwnage93000/rollback-pwnage93000.sh` / `./tools/pwnage94000/rollback-pwnage94000.sh`.

CONSTRAINTS
-----------
- Keep NFC OFF by default until a physical tag read succeeds; keep fingerprint fail-closed (PIN fallback preserved); keep ACM serial recovery alive throughout.
- Do not regress already-working kernel flags or the display/touch framebuffer writer.
- Preserve protected paths (EFS/IMEI/NV) — Nuxel diagnostics never read/write them.
- Do not fake fixes; report each piece as verified, partially verified, or still-blocked with evidence.

DONE WHEN
---------
One boot/kernel rebuild + one system image flashed into the inactive A/B slot over USB from TWRP, all missing kernel flags baked in, all firmware/runtime blobs present, at least one previously-blocked feature per subsystem enumerated/captured on the new slot, slots switched, and a rollback slot + ACM serial console verified.
```
