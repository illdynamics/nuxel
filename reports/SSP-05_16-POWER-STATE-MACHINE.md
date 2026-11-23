# SSP-05_16 — BCM47752 Power State Machine

**Date:** 2026-11-23
**Agent:** DeepSeek-V4-Pro-Thinking

## 0. Confirmed electrical relationships (live + GPL source)

- Sensor-hub MCU rail: `vdd_mcu_1p8` (`regulator.62`, enabled, num_users=0).
- GNSS logic+RF enable: `GPS_PWR_EN` = gpio145 (gpg0-2), output, currently 0.
- MCU handshake: `ssp-mcu-req` = gpio167 (output), `ssp-mcu-resp` = gpio168 (input).
- Host IRQ/wake: `ssp-host-req` = gpio15 (input, IRQ 441).
- Controller: BCM47752 (live `mcu_name=BCM47752KUB1G`).

The BCM47752 is a single package with a sensor-hub MCU and a GNSS core. The MCU rail
(`vdd_mcu_1p8`) and the GNSS enable (`GPS_PWR_EN`) are **distinct** domains per source:
`bcm477x_hello()` toggles only MCU_REQ/MCU_RESP (no GPS_PWR_EN); `GPS_PWR_EN` is exported
separately and asserted only by userspace GNSS bring-up.

## 1. State machine

```
                      +---------------------+   vdd_mcu_1p8 off
   P0 POWER_ABSENT    | MCU rail absent,    |-------------------------> P1 (via regulator)
                      | GNSS domain off     |
                      +----------+----------+
                                 | vdd_mcu_1p8 enabled (probe, no user)
                                 v
   P1 MCU_RAIL_ON     +-------------------------+
                      | rail on, MCU not booted |
                      +------------+------------+
                                   | MCU_RESET released / _bringup
                                   v
   P2 MCU_BOOT_PROBE  +--------------------------------+
                      | mcu_probe=1; boot-ROM waiting  |
                      +---------------+----------------+
                                      | GPS_PWR_EN=1 (GNSS domain on, owner-authorized)
                                      v
   P3 GNSS_DOMAIN_ON  +------------------------------------+
                      | GNSS logic+RF powered; ROM autobaud |
                      +---------------+--------------------+
                                      | ROM GetVersion exchange (RPC 0 -> 3)
                                      v
   P4 ROM_READY       +------------------------------------+
                      | version response validates identity|
                      +---------------+--------------------+
                                      | patch: MemoryWrite x479 (RPC id 5)
                                      v
   P5 FW_DOWNLOADING  +------------------------------------+
                      | F1 records ACKed, then StartScratch |
                      +---------------+--------------------+
                                      | StartScratch(46) -> ServiceStart(55)
                                      v
   P6 FW_ACTIVE       +------------------------------------+
                      | sensor-hub app running; sensor/gnss |
                      +---------------+--------------------+
                     (failure at any point) -> P7 RECOVERY (MCU reset / rail restore)
```

## 2. Transition table (owner / polarity / ordering / observation)

| # | Transition | Owner | Signal & polarity | Precondition | Expected observation |
|---|---|---|---|---|---|
| T0 | P0→P1 | regulator core | vdd_mcu_1p8 = enabled, active-high | probe | `state=enabled` |
| T1 | P1→P2 | SSP probe | MCU_RESET release (internal) | rail stable | `mcu_probe=1`, `mcu_name=BCM47752KUB1G` |
| T2 | P2→P3 | userspace (gpsd/lhd equiv) | GPS_PWR_EN=1, active-high (gpio145) | owner RF authorization | gpio145 readback=1 |
| T3 | P3→P4 | host | MCU_REQ=1 (gpio167), then MCU_RESP=1 (gpio168) within 100 ms; then RPC 0→3 | GNSS ROM powered | valid TL response id 3 |
| T4 | P4→P5 | host | MemoryWrite RPC 5 ×479, each reliable-ACKed | ROM_READY | 479 ACKs |
| T5 | P5→P6 | host | StartScratch(46, entry) then ServiceStart(55) | all writes ACKed | post-download GetVersion id 3 == ASIC |
| T6 | any→P7 | kernel `bbd_mcu_reset` / userspace `finally` | MCU_REQ=0, GPS_PWR_EN=0 | fault | deassert + restore |

## 3. Why the ROM probe currently cannot succeed

Live `nuxel_hub_diag = mcu_probe=1 shutdown=1 resetting=1 ...`. The kernel
`bcm477x_hello()` requires MCU_RESP (gpio168) to assert HIGH within 100 ms of MCU_REQ
(gpio167) being driven HIGH; with the hub in a shutdown/reset loop (no firmware loaded),
that handshake fails and `bcm_rxtx_work_func` aborts before any SSI I/O. So:

1. Correct framing alone (fixed this mission) is insufficient.
2. A valid ROM GetVersion additionally requires the MCU handshake to succeed, which in
   turn requires the hub to be out of its reset/shutdown loop.

Because the boot-ROM *GetVersion* path itself is behind the same `bcm477x_hello` gate
(the raw-SSI `bcm477x_rpc_get_version()` helper is dead code with zero callers), there
is **no** demonstrated route to a ROM-only GetVersion without first bringing the MCU out
of reset — which is exactly the firmware-download (Stage 06) prerequisite. This is a
*fundamental ordering* finding, not a guess.

## 4. Readiness detection vs arbitrary sleep

The authoritative readiness signal is the MCU_REQ→MCU_RESP handshake succeeding (the
kernel polls it in `bcm477x_hello`), not an invented settle delay. Vendor settle timing
(Broadcom datasheet) remains the only missing externally-authored item for the exact
`GPS_PWR_EN` rise → autobaud-ready duration; it is NOT required to know the *ordering*
above, only to bound the trial delay. Documented as a known missing-evidence item in
the physical-trial decision.
