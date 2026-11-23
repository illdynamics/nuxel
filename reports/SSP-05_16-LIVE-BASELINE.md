# SSP-05_16 — Live Baseline (precheck)

**Date:** 2026-11-23 (Europe/Amsterdam)
**Agent:** DeepSeek-V4-Pro-Thinking
**Device:** SM-G975F (beyond2lte), serial R58M75KDB2X
**Transport:** SSH nuxel@10.11.12.99 (key ~/.ssh/wicked_wqn_id_rsa)
**Kernel:** 4.14.253-gf7194c1d15ed-dirty #1 SMP PREEMPT Mon Nov 23 00:43:30 CET 2026

## Result — baseline HEALTHY

No hardware state was modified during collection (read-only).

| # | Check | Actual | Verdict |
|---|---|---|---|
| 1 | Device model | `Samsung BEYOND2LTE EUR OPEN 26 board based on EXYNOS9820` | PASS |
| 2 | Kernel | `4.14.253-gf7194c1d15ed-dirty #1 SMP PREEMPT ...` | PASS |
| 3 | systemd | `running`, `0 loaded units listed` (0 failed) | PASS |
| 4 | BBD nodes | `/dev/ttyBCM`(10,91 root:audio), `/dev/bbd_sensor`(236,1), `/dev/bbd_control`(236,2), `/dev/bbd_patch`(236,3), `/dev/bbd_urgent_patch`(236,4) | PASS |
| 5 | GPS_PWR_EN | gpio145 (gpg0-2), direction=out, value=0 | PASS |
| 6 | Regulator vdd_mcu_1p8 | `regulator.62 name=vdd_mcu_1p8 state=enabled num_users=0` | PASS |
| 7 | MCU identity | `mcu_name=BCM47752KUB1G`, `mcu_rev=BR0121080900,BR010` | PASS (see finding) |
| 8 | MCU power ctl | `/sys/devices/virtual/sec/sensorhub/mcu_power=1` | PASS |
| 9 | GNSS service | `nuxel-gnss-lhd.service` inactive(dead) status=2 (bounded one-shot) | PASS (documented) |
| 10 | Rollback artifacts | 5+ copies under /media/nuxel-boot/, /var/backups/nuxel/ | PASS |

## NEW decisive live finding: controller identity confirmed BCM47752

`/sys/devices/virtual/sensors/ssp_sensor/nuxel_hub_diag` returns:
`mcu_probe=1 shutdown=1 resetting=1 sensor_state=0x3feff enable=0x0 shub_irq=443`

- `mcu_name = BCM47752KUB1G` — the controller is **BCM47752** (mission target identity
  confirmed at runtime, not assumed).
- `mcu_probe=1` — the sensor-hub probe completed.
- `shutdown=1 resetting=1` — the hub is in a shutdown/reset loop; no firmware patch
  has been downloaded/re-started by userspace (no lhd/gpsd equivalent). This is the
  concrete reason a raw `/dev/ttyBCM` ROM probe times out: kernel `bcm477x_hello()`
  (MCU_REQ->MCU_RESP handshake) cannot establish before any SSI I/O.

## GPIO map (confirmed live from this boot journal)

`[SSPBBD] ssp-host-req=15, ssp-mcu_req=167, ssp-mcu-resp=168, ssp-gps-pwr-en=145`

| Signal | GPIO | Direction | Live state |
|---|---|---|---|
| ssp-host-req | 15 | input (IRQ 441/443) | 0 |
| ssp-mcu-req  | 167 | output | 0 |
| ssp-mcu-resp | 168 | input | 1 (glitching; hub not running) |
| ssp-gps-pwr-en (GPS_PWR_EN) | 145 | output | 0 |

Evidence file: `evidence/pwnage-ssp-05_15/live-baseline.txt` (carried forward),
supplemented this mission by live SSH collection (see session logs).
