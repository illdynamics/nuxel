# SSP-05_11 — Final Deployment Review

**Date:** 2026-11-22 (Europe/Amsterdam)
**Agent:** DeepSeek-V4-Pro-Thinking
**Device:** Samsung Galaxy S10+ (SM-G975F / beyond2lte / Exynos 9820), serial R58M75KDB2X

## Overall verdict

**`BOOT_DEPLOYED_POWER_TRIAL_PENDING`**

The BOOT-only flash of candidate `9805d519...` to `/dev/block/sda14` was
authorized by the owner this session ("go flash it NOW its in TWRP mode for it"),
executed, independently verified, and the device booted normally into the
intended Nuxel kernel with the 0025 correction live. ROM first light remains
unverified because no MCU power transition has been performed (the power-safety
gate remains separately authorized).

## 1. Preflight re-validation (live this session)

Read and cross-checked against live TWRP observations:

- `reports/SSP-05_10-TWRP-PREFLIGHT.md`
- `reports/SSP-05_10-PREFLIGHT-RESULT.json`
- `reports/SSP-05_10-ROLLBACK-STATUS.md`
- `reports/SSP-05_9-KERNEL-MANIFEST.json`
- `reports/SSP-05_9-CANDIDATE-PREFLIGHT.json`

**Conclusion:** latest reports and current TWRP observations AGREE. No gate regressed.

## 2. Device identity & partition mapping (live)

| Item | Live value |
|---|---|
| ADB serial | R58M75KDB2X |
| ADB state (pre-flash) | recovery |
| Recovery | TWRP 3.7.0_9-2, kernel 4.14.113-g55f042627 |
| product.device | beyond2lte |
| Shell uid | root (uid=0) |

| by-name | Block device |
|---|---|
| boot | /dev/block/sda14 |
| dtb | /dev/block/sda12 |
| dtbo | /dev/block/sda13 |
| recovery | /dev/block/sda15 |

## 3. Candidate identity (independently verified)

| Field | Value |
|---|---|
| File | evidence/pwnage-ssp-05_9/candidate-boot-0020-0023-0025.img |
| SHA-256 | 9805d519b61c38a960158753679e1e2af0cf1783ce4f4c6e3c8b0ba6be5fbca7 (MATCH) |
| Size | 57,671,680 B (= partition size) |
| Patch set | 0020 + 0023 + 0025 (0027 excluded) |
| Kernel | 4.14.253-gf7194c1d15ed-dirty |

## 4. Rollback readiness (re-verified BEFORE flash)

| # | Location | Storage | SHA-256 | Verified |
|---|---|---|---|---|
| 1 | /tmp/nuxel-ssp-preflight/boot-sda14-fresh.img | host fs | 0e6aa34c... | YES |
| 2 | /data/media/nuxel-boot/boot-sda14-known-good-0e6aa34c-20261122.img | sda31 | 0e6aa34c... | YES |
| 3 | /cache/nuxel-ssp-rollback/boot-sda14-known-good.img | sda28 | 0e6aa34c... | YES |

Three genuine physical storage locations. Device copies TWRP-accessible via ext4 ro.
`ROLLBACK_READY = TRUE` preserved throughout.

## 5. Flash execution (authorized + verified)

Owner authorization recorded this session. BOOT-only `dd` performed:

```
adb push candidate -> /tmp/boot-candidate-0020-0023-0025.img (57671680 B; on-device sha256 MATCH)
adb shell 'dd if=/tmp/boot-candidate-0020-0023-0025.img of=/dev/block/sda14 bs=4096; sync'
# 14080+0 records in / out = 57,671,680 B, rc=0
```

Post-write independent readback:

| Partition | SHA-256 | Result |
|---|---|---|
| boot sda14 | 9805d519... | MATCH candidate (FLASHED) |
| dtb sda12 | abc9d45d... | MATCH baseline (unchanged) |
| dtbo sda13 | de3bc025... | MATCH baseline (unchanged) |
| recovery sda15 | 4cc71d62... | MATCH baseline (unchanged) |

## 6. Normal Nuxel boot (PASS)

`adb reboot` -> device dropped BUS, reappeared on USB-net/RNDIS + ZeroTier.
SSH `root@10.11.12.99`:

```
Linux WIN-CLIENT 4.14.253-gf7194c1d15ed-dirty #2 SMP PREEMPT Sun Nov 22 19:30:50 CET 2026 aarch64 GNU/Linux
```

- Running kernel = intended candidate kernel identity. PASS
- systemd `is-system-running` = running. PASS
- Display/audio/bridge/NFC/touch/orientation services active. PASS
- Storage /data 50G free; wlan0/usb0/zerotier up. PASS
- No critical kernel errors (only unrelated qbt2000 debug). PASS

## 7. Post-boot SSP validation (read-only)

- SSP symbols present: set_mcu_power, show_mcu_power, bbd_nuxel_peer_*, bbd_do_transfer, bbd_* callbacks. PASS
- BBD raw transport nodes: /dev/bbd_sensor, /dev/bbd_control, /dev/bbd_patch, /dev/bbd_urgent_patch, /dev/ttyBCM. PASS
- 0025 mcu_power sysfs: /sys/devices/virtual/sec/sensorhub/mcu_power (value=1). PASS
- Corrected userspace BBD tooling: nuxel_bbd_tl.py, nuxel_bbd_host, nuxel_bbd_download. PASS
- Regulator vdd_mcu_1p8: state=enabled num_users=0 (cold-start blocker physically present; NOT transitioned).

## 8. Decision

**`BOOT_DEPLOYED_POWER_TRIAL_PENDING`** — Nuxel boots with 0025. ROM first light
unverified pending a separately-authorized, bounded MCU power transition.
