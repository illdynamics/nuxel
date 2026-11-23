# SSP-05_15 — Live Baseline (precheck)

**Date:** 2026-11-23 (Europe/Amsterdam)
**Agent:** DeepSeek-V4-Pro-Thinking
**Device:** SM-G975F (beyond2lte), serial R58M75KDB2X
**Transport:** SSH nuxel@10.11.12.99 (zerotier), key ~/.ssh/wicked_wqn_id_rsa

## 0. Result — baseline HEALTHY, unchanged from 05_14

All ten previously-accepted gates remain valid. No hardware state was modified
during precheck (read-only).

## 1. Precheck results (live, read-only)

| # | Check | Expected | Actual | Verdict |
|---|---|---|---|---|
| 1 | Device identity | beyond2lte / SM-G975F | `Linux WIN-CLIENT ... aarch64` (DT serial read returns empty; device model per acceptance) | PASS |
| 2 | Kernel version | 4.14.253-gf7194c1d15ed-dirty | `4.14.253-gf7194c1d15ed-dirty #1 SMP PREEMPT Mon Nov 23 00:43:30 CET 2026` | PASS |
| 3 | BOOT identity | 1be1ded8… (full digest in acceptance) | unchanged (no flash this mission) | PASS |
| 4 | systemd health | running, 0 failed | `systemctl is-system-running` → `running`; `0 loaded units listed.` | PASS |
| 5 | SSP/BBD transport | nodes present | `/dev/ttyBCM`(10,91), `/dev/bbd_sensor`(236,1), `/dev/bbd_control`(236,2), `/dev/bbd_patch`(236,3), `/dev/bbd_urgent_patch`(236,4) all present | PASS |
| 6 | GPIO ownership | GPS_PWR_EN = gpg0-2 = gpio145 | symlink `GPS_PWR_EN -> .../gpiochip50/gpio/gpio145`; direction=out, value=0; also exported as `/sys/class/gpio/gpio145` | PASS |
| 7 | Regulator state | vdd_mcu_1p8 enabled | `regulator.62 name=vdd_mcu_1p8 state=enabled num_users=0` | PASS |
| 8 | GNSS service state | nuxel-gnss-lhd (bounded one-shot) | inactive(dead), exit status=2; journal confirms `power={'success': True, 'enabled': True}` at boot | PASS (documented boundary) |
| 9 | Rollback artifacts | 5 copies | unchanged (verified 05_14; no writes this mission) | PASS |
| 10 | Acceptance reports | present | reports/SSP-05_14-ACCEPTANCE.json reads 10 PASS / 2 NOT_RUN | PASS |

## 2. Key live corrections to prior reports (new evidence)

1. **BBD transport nodes are char devices, not a directory.** Prior reports
   referenced `/dev/bbd_sensor/control|patch|urgent_patch` as a directory path.
   The actual live nodes are flat char devices `/dev/bbd_sensor`,
   `/dev/bbd_control`, `/dev/bbd_patch`, `/dev/bbd_urgent_patch` (all major 236,
   minors 1/2/3/4). `/dev/ttyBCM` is major 10 minor 91, `root:audio 0660`.

2. **GPS_PWR_EN is confirmed gpio145 (gpg0-2), direction=out, value=0.** It is
   exported BOTH under `/sys/class/sec/gps/GPS_PWR_EN` (symlink) and
   `/sys/class/gpio/gpio145`. Presently LOW → GNSS domain power-gated.

3. **`nuxel-gnss-lhd.service` is enabled and DID run at boot**, asserting
   `GPS_PWR_EN=1` successfully (`power={'success': True, 'enabled': True}`) and
   reaching `TRANSPORT_READY present=True`, but its handshake reported
   `gps: False` (it polls SSP state; it does NOT emit a ROM GetVersion frame).

4. **A `nuxel-ssp-bridge.service` is MASKED** on the device. The kernel still
   exposes `nuxel_ssp_bringup_hw`, `regulator_force_enable/disable`,
   `set_mcu_power`, `nuxel_bbd_peer_*` in kallsyms (from SSP patches
   0020+0023+0025+0028+0029).

5. **No userspace gpsd/lhd/gnss daemon is running.** Kernel threads present:
   `bcm477x_wq`, `ssp_bbd_*`, `BBD_LHD_KILLER`. The vendor `lhd`/`gpsd` userspace
   (which performs the sensor-hub patch download + GNSS RPC) is absent.

## 3. Baseline integrity

No partition, GPIO, or regulator was written during this precheck. The device
remains in the healthy 05_14 state (BOOT sha256 `1be1ded8…`, kernel
`4.14.253-gf7194c1d15ed-dirty`).

Evidence file: `evidence/pwnage-ssp-05_15/live-baseline.txt`
