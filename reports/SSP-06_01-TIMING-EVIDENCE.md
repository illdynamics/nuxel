# SSP-06_01 — Timing Evidence (ROM-ready / autobaud)

**Date:** 2026-11-23
**Agent:** Nuxel Stage 06_01

## 0. Verdict

`TIMING = PARTIALLY_RESOLVED`. Ordering and the two internal delays are
source-proven; **the single outstanding timing datum is the
`GPS_PWR_EN`-rise → ROM-autobaud-ready settle duration**, which is a Broadcom
datasheet value not present in any authorized local material.

This mission searched all authorized local sources and did **not** find the
value; it is reported as missing evidence rather than substituted with an
arbitrary sleep.

## 1. What IS source-proven (readiness conditions, not guesses)

| Timing item | Value | Source | Type |
|---|---|---|---|
| MCU handshake poll | up to 100 ms (`MAX_RESP_CHECK_COUNT=100`, 1 ms steps) | `bcm_gps_spi.c:499` | observable readiness gate |
| Handshake re-toggle | every 20 polls: `mcu_req=0`, 1 ms, `mcu_req=1`, 1 ms | `bcm_gps_spi.c:517-523` | observable |
| Autobaud byte count | 32 × `0x80`, bounded fallback 36 × `0x80` | `bcm_gps_regs.c` vs lhd VA 0xdfe4 | bounded (2 attempts) |
| StartScratch settle | 40 ms | lhd `scratch` encoder (0x3cee0, rpc_id 46) | recovered, source-proven |
| ServiceStart settle | 100 ms | lhd `service` encoder (0x3cff8, rpc_id 55) | recovered, source-proven |
| MemoryWrite ACK wait | 1500 ms each | `nuxel_bbd_flash.c` `reliable_rpc(...,1500)` | finite |
| GetVersion wait | 2500 ms | `nuxel_bbd_flash.c` `reliable_rpc(...,2500)` | finite |
| Power-domain transition | `GPS_PWR_EN` = GPIO output write (reversible), distinct from regulator | live evidence | N/A (no settle value) |

The two internal delays (40 ms / 100 ms) are recovered from the lhd encoders,
NOT invented.

## 2. What is UNKNOWN (reported, not substituted)

1. **`GPS_PWR_EN` rise → ROM autobaud-ready settle duration.** A Broadcom
   BCM47752 datasheet power-on/ROM-ready value. Not in the GPL kernel source,
   not derivable from the lhd binary without the vendor datasheet, not present
   in the repository's captured traces/logs.

2. **Whether the GNSS-domain ROM must be energized before the MCU handshake.**
   The Stage 05_16 analysis proposed "GNSS ROM shares the MCU SSI slave select,"
   but this is INFERRED, not asserted on-wire.

3. **Which autobaud prefix (32 vs 36) is accepted on hardware.** The downloader
   tries both as a bounded fallback; the correct one is confirmed only by a real
   response.

## 3. Search performed for the timing specification

Authorized local materials searched this mission:

- `kernel/s10plus/.build/src.polluted.case-insensitive/drivers/sensorhub/brcm/` — kernel GPL driver source (`bcm_gps_spi.c`, `bcm_gps_regs.c`, `bbd.c`, `bbd_rpc_lh.c`).
- `kernel/s10plus/patches/` — all SSP patches 0020/0023/0025/0026(retired)/0027/0028/0029.
- `tools/s10plus/ssp-native/` and `tools/s10plus/ssp-runtime/` — downloader + lhd reverse-engineering fixtures.
- `services/nuxel-gnss/` — native service/tl/control sources.
- `reports/` and `evidence/` — prior captured traces, logs, engineering reports.
- Vendor `lhd` binary — **absent** (gitignored, owner-provided, proprietary).

**Result:** no source-backed `GPS_PWR_EN`→ROM-ready settle value was found. No
arbitrary sleep is introduced.

## 4. Impact

The physical trial (authorization doc) therefore gates readiness on the
**observable MCU handshake** plus bounded, finite timeouts at every step, and does
NOT hard-code a speculative power-settle delay.

If the owner requires a fixed settle delay, it must be accompanied by evidence of
its applicability, assumptions, and upper bound (datasheet value or explicit
instruction). Absent that, the trial proceeds handshake-gated. If neither is
available, the physical trial is blocked with this exact missing-evidence request.
