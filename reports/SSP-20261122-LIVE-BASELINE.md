# SSP-20261122 — LIVE BASELINE (Stage 01)

**Date:** 2026-11-22 ~15:40 CET
**Verdict:** `DEVICE_VERIFIED` (live, normal Nuxel boot, no writes performed)
**Agent:** DeepSeek-V4-Pro-Thinking (orchestrator). Read-only stage. No flash, no firmware, no rail/GPIO/reset.

## Connectivity
- SSH `root@10.11.12.99` BatchMode reachable: **ALIVE**.
- `uname -a`: `Linux <hostid> 4.14.253-gf7194c1d15ed-dirty #1 SMP PREEMPT Sat Nov 21 12:30:11 CET 2026 aarch64 GNU/Linux`
- `uptime`: 1 day, load ~12.7 (elevated but responsive; unrelated to SSP, likely idle/wakework). Normal userspace (systemd, Wayland/phoc) healthy.

## Git checkout / deployment state
- Live checkout: `/Users/wicked/x/nuxel`, branch `cs/ssp`, HEAD `21a56e40` ("fixes").
- Working tree clean. `feat/ssp` (`32c8a8a7`) and `ds/ssp` (`29c66402`) present as branches; `ds/ssp` carries the full firmware-download commit series (833baf6f etc.).
- Deployed running kernel == reconciled **0020 + 0023** ONLY (see kallsyms below). **0025/0026/0027 are NOT deployed** — confirmed safe, no dangerous 0027 in the running kernel.

## Kernel symbol evidence (live `/proc/kallsyms`)
- Present (0023 native bring-up): `nuxel_ssp_bringup_hw`, `nuxel_ssp_register_data`, `bbd_nuxel_peer_open/release/active/rx`, `nuxel_bbd_peer_send`, `bbd_do_transfer`, `nuxel_ssp_bcm_diag`, bbd callbacks.
- **Absent**: `nuxel_ssp_dl_download`, `dl_decode_blob`, `dl_next_record`, `nuxel_ssp_dl_phase1`, `dl_reliable_rpc` — i.e. **0027 firmware downloader is NOT in the running kernel.**

## Partition map (live, verified by PARTLABEL)
| Partition | Device | Size (512-blocks) | Bytes | PARTLABEL |
|---|---|---|---|---|
| dtb | /dev/sda12 | 16384 | 8 MiB | dtb |
| dtbo | /dev/sda13 | 16384 | 8 MiB | dtbo |
| boot | /dev/sda14 | 112640 | 55 MiB (57,671,680 B) | boot |
| recovery | /dev/sda15 | 132096 | 64.5 MiB | recovery |

Historical `sda12/13/14/15` mapping is **exact and re-confirmed**. No `/dev/block/by-name` symlinks exist on this image; PARTLABEL via blkid is the authoritative identity.

## Immutable partition hashes (read-only dd, sha256sum)
- `dtb`   (sda12): `abc9d45d3745866346fd94c7c04028cc2c62ade4dd274b400dbbfec0c2ef4780`
- `dtbo`  (sda13): `de3bc02526c66647992a744608fdf61548823866e822a7400619d74126095c23`
- `boot`  (sda14): `0e6aa34cdc550fd975129d9fc0f9dc785733e0483e3b8c119eb4592b5463621c`
- `recovery`(sda15): `4cc71d6277e020cdec729b85934cfb6111e9abee8db2fbcc344aad3173335d87`

## Boot image structure (donor sda14, captured to host, hash verified == live)
- Android bootimg v1 header. magic `ANDROID!`, header_version=1, header_size=1648.
- `name = "nuxel-s10plus"`, `kernel_addr=0x10008000`, `ramdisk_addr=0x11000000`, `tags_addr=0x10000100`.
- kernel_size = 45,848,584 B; kernel_offset = 2048.
- ramdisk_size = 2,424,832 B (LZMA-alone, uncompressed 8,791,372 B), ramdisk_offset = 45,852,672.
- **appended_dtb_count = 0 — NO appended FDT/DTB tail in this live boot image.** The DTB/DTBO are external partitions (`sda12`/`sda13`), selected via `androidboot.dtbo_idx=9`.

### Implication for repack
Because there is no appended DT tail, the "preserve donor DTB/hash tail byte-for-byte" concern reduces to: **preserve ramdisk + header fields byte-for-byte, replace only the arm64 `Image` payload, keep external dtb/dtbo partitions untouched.** The verify tool's `FAIL` ("no valid appended BOOT FDT") is *expected* and *correct* for this device — it is not a defect to fix by adding a DT tail; doing so would be a hard DT change and is **forbidden**.

## Boot chain / cmdline facts
- `androidboot.dtbo_idx=9`, `androidboot.bootloader=G975FXXSEFUL1`, `androidboot.hardware=exynos9820`, `androidboot.selinux=enforcing`, `verifiedbootstate=orange`, `androidboot.revision=26`, serial `R58M75KDB2X`, `sales_code=PHN`, `root=/dev/sda25` (userdata), `root=PARTUUID=...userdata`.
- `reset_reason=7` (normal-ish warm reset). smd_offset etc. standard.

## SSP / sensor live state (read-only)
- `/sys/class/sensors/ssp_sensor` present.
- `mcu_name = BCM47752KUB1G`, `mcu_rev = BR0121080900,BR010`, `mcu_reset = OK`.
- `nuxel_hub_diag = mcu_probe=1 shutdown=1 resetting=1 sensor_state=0x3feff enable=0x0 shub_irq=443`.
- Newer SSPBBD diag line: `host_req=0 mcu_req=0 mcu_resp=1 irq_en=0 irq_cnt=0 tx=184 rx=0`.
- latest dmesg tail includes `[SSP]: reset_mcu` (an MCU reset was triggered; correlated to bring-up recovery path).
- `accelerometer_sensor/raw_data = 0,0,0`; `gyro_sensor/raw_data = 0,0,0`. Names/vendors: `LSM6DSO@STM` (enumeration metadata only, not data).
- `/dev/bbd_sensor` (236,1) and `/dev/ttyBCM` (10,91) both present. `ttyBCM` group `audio`.
- `nuxel-gnss-lhd.service` = **inactive/dead** (vendor lhd NOT running). `nuxel-orientationd.service` = active/running.

### Key diagnostic insight
`resetting=1`, `shutdown=1`, `enable=0x0`, and `mcu_resp=1` with `tx=184 rx=0` indicate the MCU is **halted/reset but its MCU_REQ/MCU_RESP line is asserted with no RX data**. `rx=0` across a 184-byte TX means the ROM never answered. This is the exact "no bidirectional ROM traffic" blocker. Root cause is not yet proven electrical vs protocol — that is Stage 02/05 work.

## Orientation service state
- `nuxel-orientationd` running (`pid 5848`), mode=`portrait` (Locked PT), `auto=false`, `auto_state=fixed`.
- `sensor.available=false`, `auto_blocked_reason="BCM47752 MCU is not streaming after the kernel bring-up"`.
- `transform_map = {"0":"normal","180":"180","270":"90","90":"270"}` — **verified correct** (config maps effective 90->w/l transform 270 and vice versa, per spec).
- `mount_matrix="unverified"`, `gravity_reference="unverified"`, `touch_calibration_verified=false`.
- Display: HEADLESS-1, logical 360x760 @ scale 2.0, physical 720x1520. Presenter rotation 0.

## Vendor lhd reference
- `lhd` binary is **NOT present in the live checkout** (only scripts/analyzers and docs reference it). Expected SHA256 `6362e80d1f2ae37c76dd5f468bf08abacb89e1c2d2b80976d5b1c3abbf761dfe` cannot be re-verified locally against live bytes; treat as `ARCHIVE_ONLY` until the binary can be sourced from an isolated reference tree.

## Rollback readiness (preliminary)
- Live donor BOOT captured to host `/tmp/nuxel-ssp-baseline/boot-sda14.img`, sha256 `0e6aa34cdc...` == live partition hash. This is a valid host-side rollback seed but must be copied to a *second* TWRP-accessible location and byte-verified on both endpoints before any BOOT write is permitted (Stage 04/05).
- RECOVERY partition (`sda15`) hash recorded; TWRP accessibility to be re-confirmed at Stage 05 (no recovery boot triggered in Stage 01).

## Gate 01 status
- `NUXEL_HEALTHY` = PASS (normal boot, SSH alive, systemd healthy).
- `DEVICE_VERIFIED` (not just ARCHIVE_ONLY) = PASS for connectivity, partition map, kernel symbols, and live sensor state.
- `ROLLBACK_READY` = **PENDING** — two distinct known-good copies (host + TWRP-accessible) with byte-verify not yet completed; deferred to Stage 04/05.
- No writes performed. No flash. No firmware. No rail/GPIO/reset.

## Unresolved root cause
MCU halts in reset/shutdown with no RX despite 184B TX: either (a) boot-ROM never entered its autobaud window (cold-start timing/rail), or (b) electrical/SPI/clock/IRQ issue, or (c) protocol/framing mismatch. Not established. 0025/0026/0027 address candidate fixes but are **not deployed** and 0027 has known safety bugs that MUST be fixed (Stage 02) before any build/flash.
