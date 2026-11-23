# SSP-06_00 — Physical Trial Authorization (EXPLICIT OWNER APPROVAL REQUIRED)

**Date:** 2026-11-23
**Agent:** Nuxel Stage 06 preflight
**Status:** `READY_FOR_SPECIFIC_OWNER_APPROVAL` — every safe offline correction is
complete; this document presents the evidence-backed trial for explicit owner approval.
**No physical firmware execution has been performed.** It is NOT marked successful.

## 0. What is being requested

Authorize ONE bounded, supervised **firmware-download + application-start** trial on the
target device (`SM-G975F`, serial `R58M75KDB2X`, controller `BCM47752KUB1G`) using the
native, verified `nuxel_bbd_flash --flash` path (or the equivalent decomposed sequence),
in the normal Nuxel environment. This is Stage 06.

The minimal correct trial is **not** "assert GPS_PWR_EN + probe ROM" (that path is
unreachable behind the kernel MCU handshake gate, proven). It is: **bring the MCU out of
reset via the firmware patch download + app start, then confirm identity.**

## 1. Exact proposed operation (ordered, bounded, reversible)

1. **Preflight (read-only):** assert `nuxel_hub_diag` still `mcu_probe=1 shutdown=1
   resetting=1`; `GPS_PWR_EN` (gpio145)=0; `vdd_mcu_1p8` enabled `num_users=0`;
   `nuxel-ssp-bridge.service` masked; no holder of `/dev/ttyBCM` (advisory flock).
2. **Rail/domain:** `vdd_mcu_1p8` already enabled (no regulator change). Optionally
   energize GNSS domain via `GPS_PWR_EN=1` (gpio145) — **this is the RF step** and is
   subject to owner RF authorization in §4.
3. **MCU handshake (readiness gate):** MCU_REQ(gpio167)=1 → MCU_RESP(gpio168)=1
   (observable, ≤100 ms kernel poll). This is the authoritative readiness signal, not a
   sleep.
4. **Autobaud:** 32 × `0x80`; bounded fallback 36 × `0x80`.
5. **GetVersion (request id 0)** → expect response **id 3 (3×LE32)**.
6. **Patch download:** 479 × MemoryWrite (id 5), each `F1 = LE32 dest + data`, each
   requiring a transport reliable-ACK (1500 ms budget each). Any NACK/partial → abort.
7. **Application start:** StartScratch (id 46, LE32 entry `0x00800161` + 40 ms), then
   ServiceStart (id 55, LE32 entry + 4 zero LE32 + 100 ms).
8. **Confirmation:** post-download GetVersion (id 0 → id 3) validating `w0 == 0x4775b0`.
   ONLY then emit `ESW:READY` and `BBD:PassThru=0`.
9. **Recovery bound (finally, unconditional):** MCU_REQ=0, GPS_PWR_EN=0,
   `BBD:PassThru=0`; kernel `bbd_mcu_reset` available. No BOOT/DTB/DTBO/recovery write.

## 2. Supporting evidence (each independently re-verified this mission)

| Fact | Evidence |
|---|---|
| Controller identity `BCM47752KUB1G` | live `mcu_name` sysfs (re-collected) |
| Firmware SHA-256 `56e8b1ea…`, 479 F1, ASIC `0x004775B0`, entry `0x00800161` | independent decode of `r_os/bbd_patch_file_beyond.h` |
| Stock provenance `G975FXXS9DTK9` | `firmware/s10plus/camera-stock-DTK9.json`; lhd hash `6362e80d…` |
| RPC ids 0/3/5/46/55 | `inspect_lhd_init.py` (hash-bound) + `nuxel_bbd_flash.c` |
| Firmware-first ordering | `bcm_rxtx_work_func` + `bcm477x_hello` source + live diag |
| Recovery independent of firmware execution | `bbd_mcu_reset` (host-side control-request) |
| Offline correctness | 3 C suites + replay + kernel-identity/isolation tests PASS |
| No accidental startup | hard gate, mutual exclusion, hardened service, no deploy |

## 3. Remaining risks (explicitly carried into the authorization)

1. **RF emission.** Energizing `GPS_PWR_EN` powers GNSS logic AND RF. This is a policy
   decision the owner must confirm (bounded, supervised trial).
2. **Unknown power-settle delay.** `GPS_PWR_EN` rise → ROM autobaud-ready duration is a
   Broadcom datasheet value NOT available in this environment. Mitigation: gate on the
   observable MCU handshake + bounded timeouts, not an invented sleep (see
   `SSP-06_00-POWER-TIMING-EVIDENCE.md`).
3. **ROM/application response identity end-to-end** is unproven until first light (that
   is exactly what the trial confirms).
4. **Load-address/stepping final acceptance** is runtime-only (see firmware-compat report);
   a NACK/mismatch surfaces as a distinct failure exit code and is not dangerous.

## 4. Recovery prerequisites (must be confirmed before the operation)

- 5+ known-good BOOT images retained (`/media/nuxel-boot/`, inventory re-verified this
  mission). No BOOT flash is planned or required for this trial.
- `bbd_mcu_reset` reachable via `/dev/bbd_control`; the reset is host-side (SIGKILL lhd or
  control request), independent of downloaded firmware.
- Cleanup path restores `GPS_PWR_EN=0`, `MCU_REQ=0`, `BBD:PassThru=0` unconditionally.
- The repo-HARDENED `nuxel_lhd.py` (not the older deployed copy) is the correct service
  to deploy before any trial; the older deployed revision asserts power at boot.

## 5. Owner action required (minimum)

1. **RF authorization** — GNSS RF energisation acceptable for a bounded, supervised trial.
2. **Timing artifact** — Broadcom BCM47752 power/ROM-ready datasheet value, OR explicit
   bounded settle-delay instruction, OR acceptance of handshake-gated readiness + bounded
   timeouts.
3. **Explicit bounded-trial grant** — for MCU wake + MemoryWrite×479 + StartScratch +
   ServiceStart + post-download GetVersion, with recovery bound
   (MCU_REQ=0 / GPS_PWR_EN=0 / `bbd_mcu_reset`).

Until these are provided, no GPS_PWR_EN assertion, no MemoryWrite, no app-start is
performed. **This trial has NOT been run and is NOT marked successful.**
