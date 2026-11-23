# SSP-06_01 — MCU Root-Cause Analysis (independent re-audit)

**Date:** 2026-11-23
**Agent:** Nuxel Stage 06_01

## 0. Verdict

The MCU is blocked by **one proven cause with one unresolved external-evidence
dependency**:

1. **PROVEN:** the live SSI transport is gated behind the MCU_REQ→MCU_RESP
   handshake (`bcm477x_hello`), and the hub sits in `shutdown=1 resetting=1`
   until firmware download brings it out of the boot-ROM/reset loop. Therefore
   firmware download is *genuinely required* before any version identification
   is reachable. (Call-graph proven in kernel source, independent of hearsay.)

2. **UNKNOWN (external):** the `GPS_PWR_EN` rise → ROM autobaud-ready settle
   duration is a Broadcom datasheet value absent from all authorized local
   material. It is reported as missing evidence, NOT substituted.

Everything else is resolved or classified.

## 1. Audit of the ten instructed causes

| # | Cause | Classification | Evidence |
|---|---|---|---|
| 1 | Missing power/clock prerequisite | PARTIAL | `vdd_mcu_1p8` enabled; `GPS_PWR_EN` (GNSS logic+RF) is LOW. Whether GNSS ROM shares the MCU handshake path is INFERRED, not measured. |
| 2 | Incorrect init ordering | RESOLVED | Ordering recovered from lhd encoders + kernel source (rail→probe→handshake→autobaud→GetVersion→MemoryWrite→StartScratch→ServiceStart→GetVersion). |
| 3 | Handshake dependency | PROVEN-CAUSE | `bcm_rxtx_work_func` aborts before any SSI I/O if `bcm477x_hello` fails. |
| 4 | Unavailable ROM-ready timing spec | UNKNOWN-EXTERNAL | Datasheet value absent; observable handshake is used as readiness gate instead. |
| 5 | Firmware incompatibility | NOT-A-CAUSE (structurally confirmed; runtime acceptance unknown) | 479 F1, ASIC `0x004775B0`, entry `0x00800161`, SHA `56e8b1ea…` all independently re-verified. Runtime acceptance delegated to trial. |
| 6 | RPC framing/response defect | RESOLVED | GetVersion response id `3` (not `0`) fixed + regression-covered; RX full TL state machine. |
| 7 | Missing userspace loader action | RESOLVED-OFFLINE | `nuxel_bbd_flash --flash` implements the full download; not yet run (physical). |
| 8 | Conflicting service ownership | RESOLVED | `nuxel-ssp-bridge.service` masked; `/dev/ttyBCM` single-holder via advisory flock recommended. |
| 9 | Kernel state-machine defect | RESOLVED | 0023/0025/0028/0029 reconcile bring-up, rail force-disable, power-cycle symmetry. 0027 in-kernel downloader deliberately excluded (dangling extern), superseded by userspace `nuxel_bbd_flash`. |
| 10 | Unresolved hardware/firmware dependency | UNKNOWN | Physical die acceptance + ROM autobaud value (32 vs 36) + GNSS/SSP domain sharing = runtime-only. |

## 2. The decisive call graph (re-read this mission)

`bcm_rxtx_work_func()` (`bcm_gps_spi.c:884`) begins:

```c
if (!bcm477x_hello(priv)) {
    pr_err(...timeout!!...);
    bcm4773_debug_info();
    bbd_mcu_reset(true);
    return;   // ABORTS before any SSI RX/TX
}
```

`bcm477x_hello()` (`bcm_gps_spi.c:496`) sets `mcu_req=1`, polls `mcu_resp`
up to `MAX_RESP_CHECK_COUNT=100`, and on timeout deasserts `mcu_req` and
returns `false`. Every SSI byte is sequenced *after* this gate.

`bcm477x_rpc_get_version()` (`bcm_gps_regs.c:48`) has **zero callers** (only its
definition + one header prototype) — dead code, NOT a live bypass.

Conclusion: no `/dev/ttyBCM` write reaches the chip until the handshake succeeds,
and the handshake only succeeds once the MCU is out of reset — which is exactly
what the firmware download performs. This is a **proven cause**, not a hypothesis.

## 3. Critical safety-relevant correction (new this mission)

The deployed kernel's `nuxel_ssp_bringup_hw()` (patch `0023-nuxel-ssp-native-
bringup-reconciled.patch`, lines ~493-577) **automatically performs a regulator
cold-cycle on handshake failure**:

```c
ret = initialize_mcu(data);
...
if (data->regulator_vdd_mcu_1p8 && !IS_ERR(...)) {
    pr_err("[SSPBBD] Nuxel bring-up: retrying after MCU power-cycle\n");
    if (regulator_is_enabled(data->regulator_vdd_mcu_1p8))
        regulator_disable(data->regulator_vdd_mcu_1p8);
    msleep(120);
    ...regulator_enable(...); msleep(300);
    ret = initialize_mcu(data);
}
```

This means the `nuxel_bringup` sysfs node (and any service that writes `1` to it)
would cold-cycle `vdd_mcu_1p8` automatically on a failed handshake. The Stage 06
rules **forbid** "cold-cycle MCU regulators as an exploratory debugging technique."

**Consequence for the trial:** the physical trial MUST NOT use the
`nuxel_ssp_bringup_hw` / `nuxel_bringup` path; it MUST use the `nuxel_bbd_flash
--flash` userspace downloader, which touches only `/dev/ttyBCM` + `/dev/bbd_*`
nodes and never drives the regulator. This is recorded here so the trial document
can exclude the cold-cycle path explicitly.

## 4. Proven vs supported vs unknown (final)

- **PROVEN:** firmware-first ordering (call graph); recovery is host-side
  (`bbd_mcu_reset` pushes a control request / SIGKILLs lhd, does not reset the
  die directly); firmware identity (hash/records/ASIC/entry); RPC id map (0/3/5/46/55).
- **SUPPORTED (inferred):** GNSS ROM shares the MCU SSI slave select; `GPS_PWR_EN`
  governs GNSS logic+RF and is distinct from `vdd_mcu_1p8`. Not directly asserted
  on-wire.
- **UNKNOWN:** `GPS_PWR_EN`→ROM-ready settle delay (datasheet, absent); 32 vs 36
  autobaud on hardware; whether the GNSS domain must be energized before the MCU
  handshake. `zero interrupt counter` is NOT treated as a hardware-defect proof.
