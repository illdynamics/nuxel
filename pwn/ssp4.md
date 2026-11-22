
1. **Confirmed device in TWRP** (`adb` = `recovery`), pushed both images, MD5-verified on-device against host.
2. **Flashed the reconciled kernel** to `sda14` (BOOT only) → `48,277,504` bytes, `dd` EXIT 0. DTB/DTBO/RECOVERY untouched.
3. **Rebooted — device booted into NUXEL** (via `10.11.12.99`, Nuxel banner, not TWRP). **No rollback needed.**

### Key wins proven through the flash

- **Reconciled native-bringup kernel is now live running.** `/proc/kallsyms` shows `nuxel_ssp_bringup_hw`, `nuxel_ssp_bcm_diag`, `nuxel_ssp_register_data` all present (`T` symbol) — the old `-EOPNOTSUPP` stub build is gone.
- **`nuxel_bringup` now triggers the real `initialize_mcu()`** (dmesg confirms real reset + WHOAMI attempt), not "unsupported".
- **Firmware verified intact** on host: `asic=0x004775b0` (BCM47752), `blob_length=438895`, `blob_crc32_ieee=93d35bb4`, patch SHA `0b53f3b04...` — all match the known-good values exactly.

### The genuine remaining blocker (PHASE 5/6, honest report)

The MCU does not answer `WHOAMI` (`get_chipid` reads `0xffffffff`, `tx=32 rx=0`, MCU never asserts host-req). Root cause identified from the driver source:

**The BCM47752's RAM firmware patch must be downloaded over the BBD transport *before* the `WHOAMI` handshake.** The kernel's `nuxel_ssp_bringup_hw()` calls `initialize_mcu()` before any patch download — the vendor `lhd` daemon normally performs that download first. The patch is embedded in the kernel as `bbd_patch_file_beyond.h` and exposed read-only at `/dev/bbd_patch`, but nothing downloads it natively yet.

`nuxel_bbd_download.c` (the existing native downloader) deliberately refuses device I/O with *"no source-verified command/ACK state machine"* — that verified download protocol is the **exact next engineering item**.

### Current device state
- Healthy, booted into Nuxel, SSH/ADB up, known-good rollback image still on `/sdcard` + host.
- I left `GPS_PWR_EN` (gpio145) = HIGH from a power-on test (harmless, reversible; noted in report).
- **No** camera/NFC/modem/DTB/DTBO/RECOVERY changes made.

### Deliverable
`reports/SSP-FIRST-LIGHT-PHYSICAL-FLASH-2026-11-21.md` — full evidence, hashes, dmesg, root-cause, and the precise next step.

The next concrete work (which I can continue now, as it's pure offline engineering) is **implementing the verified BBD firmware-download state machine** — either in the native bridge or inside `nuxel_ssp_bringup_hw()` before `initialize_mcu()`. The recovered protocol constants (ESC/EOP framing, flag bits, CRC table, callback addresses) are all present in the repo to ground this. Want me to proceed with that offline protocol implementation next?
## Operation Sensor First Light — Flash Executed ✅

### What I did (per your "reflash it now" directive + TWRP agreement)

1. **Confirmed device in TWRP** (`adb` = `recovery`), pushed both images, MD5-verified on-device against host.
2. **Flashed the reconciled kernel** to `sda14` (BOOT only) → `48,277,504` bytes, `dd` EXIT 0. DTB/DTBO/RECOVERY untouched.
3. **Rebooted — device booted into NUXEL** (via `10.11.12.99`, Nuxel banner, not TWRP). **No rollback needed.**

### Key wins proven through the flash

- **Reconciled native-bringup kernel is now live running.** `/proc/kallsyms` shows `nuxel_ssp_bringup_hw`, `nuxel_ssp_bcm_diag`, `nuxel_ssp_register_data` all present (`T` symbol) — the old `-EOPNOTSUPP` stub build is gone.
- **`nuxel_bringup` now triggers the real `initialize_mcu()`** (dmesg confirms real reset + WHOAMI attempt), not "unsupported".
- **Firmware verified intact** on host: `asic=0x004775b0` (BCM47752), `blob_length=438895`, `blob_crc32_ieee=93d35bb4`, patch SHA `0b53f3b04...` — all match the known-good values exactly.

### The genuine remaining blocker (PHASE 5/6, honest report)

The MCU does not answer `WHOAMI` (`get_chipid` reads `0xffffffff`, `tx=32 rx=0`, MCU never asserts host-req). Root cause identified from the driver source:

**The BCM47752's RAM firmware patch must be downloaded over the BBD transport *before* the `WHOAMI` handshake.** The kernel's `nuxel_ssp_bringup_hw()` calls `initialize_mcu()` before any patch download — the vendor `lhd` daemon normally performs that download first. The patch is embedded in the kernel as `bbd_patch_file_beyond.h` and exposed read-only at `/dev/bbd_patch`, but nothing downloads it natively yet.

`nuxel_bbd_download.c` (the existing native downloader) deliberately refuses device I/O with *"no source-verified command/ACK state machine"* — that verified download protocol is the **exact next engineering item**.

### Current device state
- Healthy, booted into Nuxel, SSH/ADB up, known-good rollback image still on `/sdcard` + host.
- I left `GPS_PWR_EN` (gpio145) = HIGH from a power-on test (harmless, reversible; noted in report).
- **No** camera/NFC/modem/DTB/DTBO/RECOVERY changes made.

### Deliverable
`reports/SSP-FIRST-LIGHT-PHYSICAL-FLASH-2026-11-21.md` — full evidence, hashes, dmesg, root-cause, and the precise next step.

The next concrete work (which I can continue now, as it's pure offline engineering) is **implementing the verified BBD firmware-download state machine** — either in the native bridge or inside `nuxel_ssp_bringup_hw()` before `initialize_mcu()`. The recovered protocol constants (ESC/EOP framing, flag bits, CRC table, callback addresses) are all present in the repo to ground this. Want me to proceed with that offline protocol implementation next?
tokens used
3,198,053
[codeseeq] stopping owned bridge process (pid=99985)
(base) ╭─[ꝖꝖ]─wicked↯infranux in ~/x/nuxel

