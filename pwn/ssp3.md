The device is currently sideways (landscape) as you noted, so auto-rotation should immediately detect landscape once physical streaming works.

**Say the word and I'll execute the flash** — reflashing and re-fixing if it lands in TWRP, per your agreement, until it boots back into Nuxel with real accelerometer/gyroscope motion data.
The offline portion of Operation Sensor First Light is complete. Here's the summary of what I accomplished:

## ✅ Operation Sensor First Light — Offline Phase Complete

### What I did

**1. Answered the pending question** (from `pwn/ssp2.md`): **YES** — proceeded with offline kernel reconciliation and build.

**2. Established a fresh read-only live baseline** (device reachable at `10.11.12.99`):
- Kernel `4.14.253-gf7194c1d15ed-dirty`, bootloader `G975FXXSEFUL1`, root `sda25`, dtbo_idx=9
- MCU **BCM47752KUB1G** identified, sensor_state=0x3feff (enumerated, not streaming)
- `nuxel diag: host_req=0 mcu_req=0 mcu_resp=1 irq_en=0 irq_cnt=0 tx=32 rx=0` — the smoking gun: live kernel has 0013's native bringup (tx=32) but **lacks 0020's rail/SPI-PM fix** (rx=0).

**3. Reconciliated kernel patches** into `0023-nuxel-ssp-native-bringup-reconciled.patch` (999 lines, 10 files + 1 header), layering 0013's native peer/bringup on top of 0020's rail + SPI re-init, de-duplicating the `ssp_dev.c`/`ssp_sysfs.c` overlap. Critically wired `set_nuxel_bringup` → `nuxel_ssp_bringup_hw()` (no more `-EOPNOTSUPP`).

**4. Compiled the kernel** — `EXIT=0`, all my sensorhub code compiles cleanly, symbols linked into `vmlinux`, capability config parity + NFC/USBNET/userns gates all **PASS**.

### Deliverables (all hash-verified)

| Artifact | SHA-256 |
|---|---|
| Reconciled `Image` | `0e553484...1c081a7163d` |
| New boot.img `nuxel-s10plus-boot-ssp-reconciled.img` | `04e43e93...7a3ef7beb6bac25` |
| Known-good `nuxel-boot-known-good.img` (rollback) | `8fe74777...1bc34d1bd859` |

### ⚠️ Gate: FLASH requires your approval

Per the mission's Phase 7 (and your TWRP agreement), the **physical BOOT (sda14) flash is NOT yet performed**. The complete proposal is in:

- `reports/SSP-FIRST-LIGHT-RECONCILIATION-2026-11-21.md`
- `reports/SSP-BOOT-SAFETY-AND-ROLLBACK.md`

**The plan** (BOOT-only, preserving DTB/DTBO/RECOVERY):
```
# push to /sdcard, then in TWRP:
dd if=/sdcard/nuxel-s10plus-boot-ssp-reconciled.img of=/dev/block/sda14 bs=4096
sync && reboot
```

**Rollback if it boots to TWRP** (defined failure):
```
dd if=/sdcard/nuxel-boot-known-good.img of=/dev/block/sda14 bs=4096
sync && reboot
```

**Post-boot first-light test** (after your approval and successful boot):
```bash
echo 1 > /sys/class/sensors/ssp_sensor/nuxel_bringup
echo 1 > /sys/class/sensors/ssp_sensor/nuxel_stream
cat /sys/class/sensors/accelerometer_sensor/raw_data   # must change with tilt
cat /sys/class/sensors/gyro_sensor/raw_data            # must change with rotation
```

The device is currently sideways (landscape) as you noted, so auto-rotation should immediately detect landscape once physical streaming works.

**Say the word and I'll execute the flash** — reflashing and re-fixing if it lands in TWRP, per your agreement, until it boots back into Nuxel with real accelerometer/gyroscope motion data.
tokens used
8,554,980
[codeseeq] stopping owned bridge process (pid=40415)
(base) ╭─[ꝖꝖ]─wicked↯infranux in ~/x/nuxel
╰─❯❯❯ 

