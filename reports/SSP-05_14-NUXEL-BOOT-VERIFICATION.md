# SSP-05_14 — Nuxel Boot Verification

**Date:** 2026-11-23
**Agent:** DeepSeek-V4-Pro-Thinking

## Result: BOOT_NUXEL = PASS

The 0029-corrected BOOT candidate was flashed to /dev/block/sda14 in TWRP,
and the device rebooted **normally into Nuxel** (not TWRP).

## Kernel identity (live)

```
Linux WIN-CLIENT 4.14.253-gf7194c1d15ed-dirty #1 SMP PREEMPT Mon Nov 23 00:43:30 CET 2026 aarch64 GNU/Linux
```

- Build timestamp `00:43:30 CET 2026-11-23` matches this session's clean build.
- Release `gf7194c1d15ed-dirty` = pinned commit f7194c1d15ed + patches (dirty).
- `regulator_force_enable` symbol present in /proc/kallsyms.

## System health (live)

| Check | Result |
|---|---|
| systemd is-system-running | running |
| failed units | 0 |
| /dev/ttyBCM | present |
| /dev/bbd_sensor/control/patch/urgent_patch | present |
| mcu_power sysfs | 1 |
| vdd_mcu_1p8 regulator | state=enabled num_users=0 |
| storage /data | 45G free |
| networking | wlan0, usb0, zerotier (10.11.12.99) up |
| SSP symbols in kallsyms | 8 (set_mcu_power, nuxel_ssp_bringup_hw, bbd_nuxel_peer*) |
| regulator count | 73 |
| open_count WARN_ON in dmesg | none |

## TWRP agreement

The device was commanded to `adb reboot` and returned to Nuxel (not TWRP).
`BOOT_NUXEL = PASS` per Section 8.1.

## DTB/DTBO/Recovery unchanged

Verified in TWRP immediately post-write (authoritative readback):
- dtb sda12 = abc9d45d3745866346fd94c7c04028cc2c62ade4dd274b400dbbfec0c2ef4780 (unchanged)
- dtbo sda13 = de3bc02526c66647992a744608fdf61548823866e822a7400619d74126095c23 (unchanged)
- recovery sda15 = 4cc71d6277e020cdec729b85934cfb6111e9abee8db2fbcc344aad3173335d87 (unchanged)
