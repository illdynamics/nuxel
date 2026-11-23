# SSP-06_00 — Protocol Validation (ROM vs RPC vs patch-loader)

**Date:** 2026-11-23
**Agent:** Nuxel Stage 06 preflight
**Scope:** Independent re-audit of the Stage 05_16 protocol conclusions and the
"firmware-first" hypothesis, using the actual kernel call graph (not hearsay).

## 0. Verdict

`PROTOCOL = VALIDATED (offline, source-proven)` with one hard, correctly-scoped
consequence: **firmware download is genuinely required before version
identification is reachable through the deployed transport.** This is not a guess;
it is proven from the kernel source call graph. The RPC identifier map
(GetVersion request 0 / response 3, MemoryWrite 5, StartScratch 46, ServiceStart 55)
is validated from hash-bound static analysis of the matched stock lhd.

## 1. The decisive call graph (independently re-read this mission)

`bcm_rxtx_work_func()` (kernel `bcm_gps_spi.c`) begins with:

```c
if (!bcm477x_hello(priv)) {
    pr_err(... timeout!! ...);
    bcm4773_debug_info();
    bbd_mcu_reset(true);
    return;              // <-- ABORTS before any SSI RX/TX
}
```

`bcm477x_hello()` (same file) drives `mcu_req=1` and polls `mcu_resp` up to
`MAX_RESP_CHECK_COUNT=100`; on timeout it deasserts `mcu_req` and returns `false`.
**Every** byte of SSI I/O (`bcm_ssi_rx` / `bcm_ssi_tx`) is sequenced *after* this
handshake. Therefore no `/dev/ttyBCM` write reaches the chip until the MCU handshake
succeeds.

The raw-SSI ROM helper `bcm477x_rpc_get_version()` (`bcm_gps_regs.c:48`) exists but has
**zero callers** (confirmed by source-wide grep this mission: it appears only in its own
definition and one header prototype). It is dead/debug code.

### Four-layer protocol taxonomy (made explicit)

| Layer | Reached when | Framing | GetVersion semantics | Evidence |
|---|---|---|---|---|
| **ROM communication** | MCU handshake succeeds + autobaud | raw SSI (dead helper) | NOT live-reachable | `bcm477x_rpc_get_version` zero callers |
| **Firmware patch-loader** | after autobaud + sync | TL-reliable (`/dev/ttyBCM`) | MemoryWrite id 5 | lhd `memory_write_encoder=0x3d60c` |
| **Application-level RPC** | after ServiceStart | TL-reliable | request id 0 → response id 3 | lhd rpc map + tests |
| **Sensor-hub runtime init** | after post-download GetVersion | TL-reliable | id 3 = 3×LE32 (w0 ASIC) | lhd 0x3d1a8..0x3d364 |

## 2. RPC identifier map (validated)

Authoritative source: `tools/s10plus/ssp-runtime/inspect_lhd_init.py` (hash-bound to lhd
`G975FXXS9DTK9`, SHA-256 `6362e80d1f2ae37c76dd5f468bf08abacb89e1c2d2b80976d5b1c3abbf761dfe`).

| RPC | id | Direction / body | Static evidence |
|---|---|---|---|
| GetVersion request | **0** | host→fw, empty body | state 7/14→8/15 "RPC ID 0 empty body; reliable enqueue; timer 250ms" |
| GetVersion response | **3** | fw→host, 3×LE32 | `rpc_ids['3']` compare_va 0x3d1dc, fields LE32 w1/w2/w3 |
| MemoryWrite | **5** | host→fw, LE32 dest + LE16 len + data | serializer 0x39e74→0x3d60c "RPC ID 5, LE32 destination" |
| StartScratch | **46** | host→fw, LE32 entry, delay 40ms | `scratch` encoder 0x3cee0, rpc_id 46 |
| ServiceStart | **55** | host→fw, LE32 entry + 4×zero LE32, delay 100ms | `service` encoder 0x3cff8, rpc_id 55 |

The kernel GPL enum (`bbd_rpc_lh.c`) names the id-0/id-3 pair only opaquely
(`IRpcA.A` / `IRpcB.A`); the *semantic* request/response split is owned by the matched
lhd and recovered above.

## 3. The firmware-first hypothesis — CONFIRMED, with the correct caveat

**"Firmware download is required before version identification" is TRUE** for the
deployed `/dev/ttyBCM` transport, for the specific reason proven above: `bcm477x_hello`
gates all SSI I/O, and the hub is in a `shutdown=1 resetting=1` loop until firmware
brings it out of reset.

The mission instruction warns: *"Do not treat an unreachable kernel helper as proof that
no alternative protocol path exists."* This is honored. The conclusion is NOT "the dead
helper proves no ROM path exists"; it is "the **live, only** SSI path in
`bcm_rxtx_work_func` is gated behind the MCU handshake, and there is no alternative SSI
driver/routing in the deployed tree that bypasses it." The `--rom-probe` path in
`nuxel_bbd_flash.c` therefore correctly *attempts* the autobaud + GetVersion over the
`/dev/ttyBCM` TL path (matching lhd), and correctly can only succeed once the MCU is out
of reset — which the firmware download performs.

**Corrected framing (adopted for Stage 06):** the minimal physical trial is NOT
"assert GPS_PWR_EN + probe ROM"; it is "bring MCU out of reset via firmware download +
app start, then confirm identity via post-download GetVersion." This is the Stage 06
operation, and it is exactly what the authorization document below requests.

## 4. Where the native `nuxel_bbd_flash.c` is correct (re-audited)

- GetVersion reply classified on **id 3**, not id 0 (Stage 05_16 fix, regression-covered).
- `--rom-probe` emits ONLY autobaud + one `RPC_GET_VERSION(0)`; proven by
  `NUXEL_BBD_TEST_INSTRUMENT` recorder that it never emits MemoryWrite/StartScratch/ServiceStart.
- CRCs, escape/SOP/EOP, reliable ACK/NACK, partial/short reads, timeouts, rollover,
  reentrancy all covered in `test_nuxel_bbd_negative.c` (17 tests, all PASS this mission).

## 5. Remaining protocol items (runtime-only; not resolvable offline)

- The physical ROM/application response identity end-to-end (requires the live trial).
- Whether the ROM autobaud value is 32 (`bcm_gps_regs.c`) or 36 (`lhd VA 0xdfe4`) — the
  downloader tries 32 first then 36 as a bounded fallback; the correct one is confirmed
  only by an actual response on hardware.

## 6. Conclusion

Protocol identifiers and the firmware-first ordering are **offline-validated and
source-proven**. No protocol-vs-RPC ambiguity remains. The physical GetVersion handshake
is folded into the firmware-download trial as the confirmation step.
