# SSP — ROM Wake-Up First Light: Trial Plan + Baseline Evidence + Gates

**Prompt:** 05_7 §4–§10
**Agent:** DeepSeek-V4-Pro-Thinking
**Date:** 2026-11-22
**Result as of this prompt:** **`POWER_FIX_IMPLEMENTED_AWAITING_AUTHORIZATION`** —
software correction complete, physical ROM wake-up and `GetVersion` await owner
authorization of a nuclear-fenced trial (and, if a kernel BOOT flash is required
to deploy 0025, a separately authorized BOOT-only flash).

---

## 0. Pre/post device health comparison (read-only, this session)

| Measure | Value | Hash/Note |
|---|---|---|
| Kernel | `4.14.253-gf7194c1d15ed-dirty` #1 SMP PREEMPT | matches baseline |
| Boot identity | hostname `2001-1c00-…`, arch aarch64 | healthy |
| uptime | 18:32 up 28 min | systemd running |
| `vdd_mcu_1p8` | state=enabled, num_users=0, 1.8 V | **root-cause evidence** |
| `GPS_PWR_EN` (gpio145) | out lo (0) | GNSS stand-by, unchanged |
| `reset_info` | `GPS OFF` | cached status |
| `nuxel_hub_diag` | mcu_probe=1 shutdown=1 resetting=1 sensor_state=0x3feff enable=0x0 shub_irq=443 | |
| `mcu_test` | `NG,NG,NG` | honest |
| `[SSPBBD] nuxel diag` | host_req=0 mcu_req=0 mcu_resp=1 irq_en=0 irq_cnt=0 tx=80 rx=0 | rx still 0 |
| IRQ 441 "ttyBCM" | count=0 | never fired |
| IRQ 443 "ssp-shub-int" | count=1 | historical edge |
| Transport owner | `lsof` empty on tty/bbd nodes | single-owner |
| Deployed symbols | `nuxel_ssp_bringup_hw` present; `nuxel_ssp_dl_download`/`dl_*` **absent** | = 0020+0023 only |
| BOOT / DTB / DTBO / recovery | unchanged | `0e6aa34c…` / `abc9d45d…` / `de3bc025…` / `4cc71d62…` (from prior read-only capture; no writes this session) |

No accelerometer/gyroscope/orientation success is claimed (real streaming not
independently verified; `raw_data` is `0,0,0`).

---

## 1. Physical power-transition authorization gate (§5)

The following is a **narrow, bounded trial plan**. It is NOT executed, and it is
NOT self-authorized. It is presented here for explicit owner approval.

### 1.1 Proposed kernel API / service operation

1. (If required) Deploy patch `0025-nuxel-ssp-rail-force-coldcycle.patch` via a
   separately authorized **BOOT-only** flash (`/dev/block/.../boot`, currently
   mapped to `sda14` per the Stage-05 handoff), after the full §8 preflight.
2. Cold-cycle the sensor-hub MCU rail via the driver-owned sysfs node:
   `echo 0 > /sys/devices/virtual/sensors/ssp_sensor/mcu_power`
   (case 0 → `regulator_force_disable(vdd_mcu_1p8)`),
   wait for `regulator_is_enabled() == 0`,
   then `echo 1` (case 1 → `regulator_enable()`).
   Alternatively the kernel bring-up recovery (`echo 1 > nuxel_bringup`) already
   sequences force-disable → enable → (with 0027) download, but for the *ROM
   identity* step we prefer `mcu_power` + userspace `--rom-probe`.

### 1.2 Hardware component controlled (source-verified)

`vdd_mcu_1p8` regulator (the BCM47752 **sensor-hub MCU** 1.8 V rail), owner
`ssp_dev.c`. This is **distinct** from `GPS_PWR_EN` (GNSS stand-by, gpio145),
which is **not** touched.

### 1.3 Shared GNSS / other consumers

- `vdd_mcu_1p8` may be **physically shared with GNSS** (0025's own AUDIT note).
  A force-disable drops **every** consumer reference. Classification: **shared
  relationship UNRESOLVED from source** — the two software controls are distinct,
  but a shared physical rail cannot be excluded.
- Consequence: GNSS will briefly power-cycle if it shares the rail. This is the
  single permitted side effect, and the plan restores the rail in the same
  bounded operation.

### 1.4 Can it affect a working subsystem?

Yes — GNSS (if it shares the rail) and the sensor hub itself will briefly lose
power. No effect on Wi-Fi, touch, display, boot chain, or storage. The rail is
restored within the same bounded operation.

### 1.5 Expected precondition and resulting power state

- Precondition: `vdd_mcu_1p8` enabled, `num_users=0` (measured).
- During: rail physically drops (poll `regulator_is_enabled()==0`), then rises.
- Result: a **genuine MCU cold power-on**, opening the boot-ROM autobaud window.

### 1.6 Exact ROM identity exchange afterward

Run the already-tested userspace tool:
`/tmp/nuxel_bbd_flash.romprobe --rom-probe` (SHA-256 `5f05dba1…`), which sends
autobaud (32 then 36 bytes) and one `GetVersion` (RPC 0) per attempt, and reads
the raw SSI reply from `/dev/ttyBCM`. Acceptance: a well-formed TL packet with
valid SOP/EOP/CRC-8 (nibble-swapped GlUtlCrc), payload = RPC 0 with a non-zero
LE32 `w0`. Reject `0xFF` idle, CRC errors, NACK, wrong length.

### 1.7 Max duration / attempt count

- 1 session; at most **one** rail cold-cycle.
- ≤ 2 autobaud variants within the single `--rom-probe` (already built-in).
- Hard wall clock: ≤ 30 s total.

### 1.8 Abort conditions

Any reboot/hang, `GPS_PWR_EN` change, unexpected partition/GPIO/rail activity,
`mcu_resp` drop without recovery, or a third failed retry.

### 1.9 Recovery procedure

Restore `mcu_power=1` (rail on), close all transport FDs, `BBD:PassThru=0`. The
known-good BOOT image (host + TWRP copies) remains staged for rollback if a kernel
flash is involved. No DTB/DTBO/recovery/bootloader write, ever.

### 1.10 Post-test health checks

Re-read `mcu_power`, `nuxel_hub_diag`, `[SSPBBD] nuxel diag` (tx/rx/irq), IRQ
441/443 counts, `GPS_PWR_EN`, immutable partition hashes, systemd health.

---

## 2. Acceptance gates (§9)

| Gate | Status | Evidence |
|---|---|---|
| Nuxel boots normally | **PASS** | live kernel + systemd, 0 failed units |
| BOOT unchanged or independently authorized | **PASS (unchanged)** | no write this session; `0e6aa34c…` |
| DTB unchanged | **PASS** | `abc9d45d…` |
| DTBO unchanged | **PASS** | `de3bc025…` |
| BCM47752 power dependency verified | **PASS** | `vdd_mcu_1p8` enabled + `num_users=0` measured; `mcu_power`↔regulator mapped |
| Reset/standby dependency verified | **PARTIAL/BLOCKED** | `reset_info`/`shutdown`/`resetting` are software flags, not measured pin states; `GPS_PWR_EN` is GNSS stand-by (separate) |
| No unintended shared-consumer disruption | **PASS (this session)** | no rail touched; GNSS untouched |
| Correct MCU init sequence established | **PARTIAL** | sequence source-verified; not yet executed |
| SPI transfer completed | **PASS** | `tx=80` (prior trial), controller completes without CS error |
| Raw ROM RX observed | **BLOCKED** | `rx=0` (awaiting cold-cycle) |
| ROM GetVersion valid | **BLOCKED** | silent ROM |
| Firmware-download readiness verified | **BLOCKED** | 479-record parsing verified offline; physical transfer not run |
| GNSS and other subsystems healthy | **PASS (this session)** | no disruption |

## 3. Explicit Prompt 06 readiness decision

**`POWER_FIX_IMPLEMENTED_AWAITING_AUTHORIZATION`**

A genuine ROM `GetVersion` has **not** been obtained, and firmware-download
prerequisites have **not** been physically verified. Prompt 06 must **not** begin
until:

1. The owner authorizes the §1.1–1.10 bounded trial (rail cold-cycle + `--rom-probe`),
2. and, because deploying the `regulator_force_disable` fix requires a kernel
   change, the §8 BOOT-only flash preflight is completed and separately authorized.

Once a genuine ROM `GetVersion` (correct framing/CRC/length/identity) is captured,
the handoff to Prompt 06 can declare `READY_FOR_06`. Until then it is
`POWER_FIX_IMPLEMENTED_AWAITING_AUTHORIZATION`, with the remaining defect
identified and evidence preserved.

**No `ESW:READY`, sensor value, ROM identity, or success indicator was synthesized.**
