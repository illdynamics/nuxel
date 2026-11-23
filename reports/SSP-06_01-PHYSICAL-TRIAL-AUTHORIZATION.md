# SSP-06_01 — Physical Trial Authorization (EXPLICIT OWNER APPROVAL REQUIRED)

**Date:** 2026-11-23
**Agent:** Nuxel Stage 06_01
**Status:** `READY_FOR_SPECIFIC_OWNER_APPROVAL`
**This is NOT the owner decision. This master prompt is NOT the owner decision.**

## 0. What is requested

Authorize ONE bounded, supervised **firmware-download + application-start** trial
on the target device, using the native `nuxel_bbd_flash --flash` userspace
downloader (NOT the `nuxel_bringup`/`nuxel_ssp_bringup_hw` kernel path, which
auto-cold-cycles the regulator — see the exclusion below).

## 1. Exact target

| Item | Value |
|---|---|
| Device | Samsung Galaxy S10+ `SM-G975F`, serial `R58M75KDB2X` |
| Product | `beyond2lte`, EXYNOS9820 |
| Kernel | `4.14.253-gf7194c1d15ed-dirty #1 SMP PREEMPT` |
| MCU | `BCM47752KUB1G`, rev `BR0121080900,BR010` |
| Firmware blob SHA-256 | `56e8b1ea4b34077f0c5c31b54c8619343d95d4f109c8ae54b99ed54a6b1e6d2d` |
| Firmware records | 479 × F1; ASIC `0x004775B0`; entry `0x00800161` |

## 2. Exact operation (ordered, bounded, reversible)

1. **Preflight (read-only):** hub diag `mcu_probe=1 shutdown=1 resetting=1`;
   `GPS_PWR_EN`=0; `vdd_mcu_1p8`=enabled; `nuxel-ssp-bridge.service` masked; no
   holder of `/dev/ttyBCM` (advisory flock).
2. **GPS_PWR_EN:** assert `=1` (gpio145) — **this energises GNSS logic AND RF.**
   This is the RF step and is subject to owner RF authorization (Section 7).
3. **MCU handshake (readiness gate):** the kernel's `bcm477x_hello` performs
   MCU_REQ(167)=1 → poll MCU_RESP(168) ≤100 ms. This is the observable readiness
   signal; NOT an invented sleep.
4. **Autobaud:** 32 × `0x80`, bounded fallback 36 × `0x80`.
5. **GetVersion (request id 0)** → expect response **id 3 (3×LE32)**.
6. **Patch download:** 479 × MemoryWrite (id 5), each F1 = LE32 dest + data, each
   requiring a reliable-ACK (1500 ms budget). Any NACK/partial → abort.
7. **Application start:** StartScratch (id 46, LE32 entry + 40 ms), then
   ServiceStart (id 55, LE32 entry + 4×zero LE32 + 100 ms).
8. **Confirmation:** post-download GetVersion (id 0 → id 3) validating
   `w0 == 0x4775b0`. ONLY then `ESW:READY` + `BBD:PassThru=0`.
9. **Recovery bound (finally, unconditional):** `MCU_REQ=0`, `GPS_PWR_EN=0`,
   `BBD:PassThru=0`; `bbd_mcu_reset` reachable via `/dev/bbd_control`. NO
   regulator cold-cycle. NO BOOT/DTB/DTBO/recovery write.

## 3. Hardware interfaces affected

- GPIO 145 (`GPS_PWR_EN`, gpg0-2) — output, energises GNSS logic + RF.
- GPIO 167 (`MCU_REQ`), GPIO 168 (`MCU_RESP`) — handshake toggles (kernel-driven).
- GPIO 15 (`ssp-host-req`) — host IRQ in.
- `/dev/ttyBCM` (10,91) — SSI transport stream.
- `/dev/bbd_control`, `/dev/bbd_patch`, `/dev/bbd_sensor` (236,1-4) — control/patch/sensor.
- `vdd_mcu_1p8` (regulator.62) — **NOT touched** (already enabled; left enabled).

## 4. Power and timing prerequisites

- `vdd_mcu_1p8` already enabled (no regulator transition).
- `GPS_PWR_EN` assertion (RF step) — owner RF authorization required.
- **Timing spec source:** the readiness gate is the OBSERVABLE MCU handshake
  (≤100 ms) plus bounded per-step timeouts (1500 ms/write, 2500 ms GetVersion).
  The `GPS_PWR_EN`→ROM-ready settle delay is **NOT available** (Broadcom
  datasheet absent). See TIMING-EVIDENCE report. *Owner may provide the datasheet
  value, or accept handshake-gated readiness, or block.*

## 5. Expected observable responses

- MCU_RESP rises within 100 ms of MCU_REQ (if MCU out of reset).
- GetVersion request id 0 → response id 3, 3×LE32, w0 ASIC `0x4775b0`.
- 479 reliable MemoryWrite ACKs (exact count match).
- StartScratch + ServiceStart ACKs.
- post-download GetVersion `w0 == 0x4775b0`.

## 6. Finite timeout and recovery criteria

Every step has an explicit monotonic-deadline timeout. A timeout is a **failure**
with a distinct exit code — never an invitation to retry. One attempt only. On any
unexpected result the finally-path restores `GPS_PWR_EN=0`, `MCU_REQ=0`,
`BBD:PassThru=0` and the trial terminates.

## 7. Risks and required owner decisions

1. **RF emission.** `GPS_PWR_EN=1` powers GNSS RF. Requires explicit owner
   confirmation that bounded, supervised GNSS RF energisation is acceptable.
2. **Unknown settle delay.** Datasheet value absent. Requires either (a) the
   datasheet value, (b) an explicit bounded-settle instruction, or (c) acceptance
   of handshake-gated readiness + bounded timeouts.
3. **Deployed-service staleness.** The currently deployed `nuxel_lhd.py`
   (sha256 `6d90a2c0…`) asserts GPS_PWR_EN + writes ESW:READY at every boot
   without authorization (see LIVE-BASELINE). Recommend masking/disabling
   `nuxel-gnss-lhd.service` (or deploying the hardened repo HEAD binary) BEFORE or
   as part of the trial authorization, so the trial's GPS_PWR_EN ownership is
   exclusive and non-ambiguous.

## 8. Evidence captured

Raw RX bytes, decoded RPC records, per-write ACK/NACK, handshake timing, post-
download GetVersion words, exit code, and full finally-path restore state. Saved
to the SSP evidence directory. Simulated vs physical clearly distinguished.

## 9. Physically verified vs offline-only

- **Offline-validated:** protocol ids, framing, firmware identity, recovery design,
  boundedness. (Done.)
- **Physically unverified (this trial proves/denies):** ROM autobaud acceptance,
  firmware die acceptance, post-download GetVersion, MCU reaching ESW:READY.

## 10. Conditions requiring immediate termination

NACK on any MemoryWrite; GetVersion mismatch; no post-download GetVersion; any
regulator transition; any unexpected GPIO state; any timeout. Terminate, restore,
preserve evidence, no retry.

---

**This document requires a separate, explicit owner decision. The agent will not
proceed to physical execution based on this master prompt alone.**
