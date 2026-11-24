> Historical report. Round 43 supersedes its registration, APN item identity, checksum and startup conclusions. See [corrected implementation and hardware evidence](S5000AP-06-ROUND43-SET-APN-INFO-CP-TRACE.md).

# Stage 06 — Round 42: THE ULTIMATE ANSWER (execution pass — NV serving implemented + external dependency precisely re-verified)

**Date:** 2026-11-24 CET
**Branch:** cs/mob-round35-stage06 (HEAD cae90269)
**Device:** SM-G975F / beyond2lte / Shannon S5000AP, KPN SIM (PLMN 20408)
**Live:** ZeroTier 10.11.12.99 — CP ONLINE, SIM READY, PS REGISTERED_HOME, RSSI live, no default EPS bearer.

## Objective of this round

Round 42 was an *execution* pass (per the ROUND-42 mission): re-inspect the actual
repository/firmware/live-device state, do NOT repeat already-completed investigations,
and implement the missing integration. A real implementation was delivered and committed;
the remaining single blocker was re-derived and is reported with reproducible evidence, not
reasserted from prior reports.

## What was independently re-verified this round (not trusted from prior reports)

1. Full repo/state audit: HEAD f138ab5b (round-41 report) → now cae90269; one pre-existing
   uncommitted user change (`mobile.md`, the ROUND-42 mission doc) preserved untouched.
2. Live device: CP ONLINE, SIM READY (ds_detect=1), PS REGISTERED_HOME, RSSI heartbeat
   (DISP_RSSI_INFO) flowing; rmnet0..7 DOWN; ZeroTier/Wi-Fi/USB/SSH intact.
3. Firmware re-extracted: CP modem.bin (46,062,992 B) TOC →
   BOOT/MAIN/VSS/NV/OFFSET. Re-derived the exact TOC layout independently:
     BOOT    off 0x420    load 0x40000000 size 0x1e40
     MAIN    off 0x2260   load 0x40010000 size 0x260c170
     VSS     off 0x260e3e0 load 0x47800000 size 0x5df6a0
     NV      off 0x0      load 0x45600000 size 0x100000   (placeholder: not in file)
     OFFSET  off 0x7aa00  load 0x0        size 0x85600    (546,304 B == .nv_core.bak size)
4. Re-derived the CP "NASU.LTE.ATTACH.APN.INFO" string at MAIN load 0x404793e3 and the
   "internet"/"ims" string absence in BOTH the AP EFS nv_data.bin (1 MiB) and CP EFS
   .nv_core.bak (0x85600). Independently confirmed item 360 (0x168) is EMPTY.
5. Independent disassembly (capstone 5.0.7) of the vendor derived
   `LteEpdgDataCallManager::DoSetInitialAttachApn @0x28c6c8` (1984 B) fresh: it drives an
   MBIM MS-LTE-Attach-Config flow (0x8b51d9b magic; 0x498-stride context lists), NOT a
   persistent FMT write — corroborating round-32's "MBIM is a non-path for SIPC" verdict
   and round-41's "DoSetInitialAttachApn is the base no-op / derived uses MBIM" verdict.

## IMPLEMENTATION DELIVERED + COMMITTED (cae90269)

`radiod` previously FAIL-CLOSED every RFS NV op (every NV_READ/NV_WRITE_ALL answered with
an error), which is NOT cbd-equivalent. This round wired the recovered RFS NV transaction
contract (rfs_nv.h) into an ACTUAL serving path using the existing bounded, fail-closed
`efs_nv` backend (the native AP-side NV store, replacing vendor cbd):

- NV_READ      → bounded `efs_nv_read_at` from `/mnt/vendor/efs/nv_data.bin` at the
                 CP-supplied (offset,length), then `rfs_nv_read_response_build` (15+N).
- NV_WRITE_ALL → bounded `efs_nv_write_at` + fsync at the CP-supplied (offset,length),
                 then `efs_nv_update_checksum_sidecar` (Nv::UpdateChecksumFile equivalent),
                 then a 15-byte write response.

Safety preserved: the AP NEVER invents offset/length (the CP always supplies them); writes
require `--write-enable` AND `NUXEL_NV_WRITE=1`; all ops bounded against the real file
size; no payload bytes/item ids are ever logged; the default (observer-only) configuration
gains no write surface. `install.sh` now links `efs_nv.c` + `nv_items.c`.

Verification: host `build.sh` full suite (14 suites + 3000-iter fuzzer `crashes=0` +
ASan/UBSan `crashes=0`) PASS; on-device `gcc -Wall -Wextra -Werror` cross-build of
nuxel-radiod + new modules `BUILD_EXIT=0`.

## Remaining single blocker (re-derived, evidence-locked)

The default EPS bearer still requires the PERSISTENT initial-attach APN = NV item 360
(0x168, "NASU.LTE.ATTACH.APN.INFO") to be "internet" in the Samsung NV container. Two facts
now independently re-confirmed this round:

1. The CP NEVER computes item-360's physical offset from anything the AP can see ahead of
   time. The OFFSET segment's per-item name fields are CP-RUNTIME-RELOCATED addresses
   (0x416axxxx), which resolve to non-string data in the MAIN image (verified: they do NOT
   yield "NASU.LTE.ATTACH.APN.INFO" at file offset main_off + (ptr - 0x40010000)). The
   mapping item-id → physical offset is fixed at CP boot by the vendor cbd/CP NvCoreInfo
   list, which is assigned at runtime and not statically recoverable.
2. The vendor `nv.log` (live /mnt/vendor/efs/nv.log) shows the last cbd NvCore run on
   2024-02-03 with "NvBackup backup failed" — i.e. the stock Samsung provisioning path last
   ran without ever persisting an "internet" attach-APN (KPN item 360 left empty), and no
   Nuxel process has since populated it.

Therefore item 360 remains addressable ONLY by one of, neither present locally:
  (a) the Samsung cbd NV item→offset table (runtime-generated, proprietary), or
  (b) a known-good nv_data.bin reference from an IDENTICAL SM-G975F provisioned on KPN
      (attach APN already "internet").

No blind write, no guessed offset, no fabricated offset was performed. The NV serving path
is now implemented and available so that the MOMENT a legitimate (offset,length) for item
360 is supplied (by the CP, or by a recovered reference), radiod can provision + persist it
with backup/MD5/rollback end-to-end.

## Safety

No NV/EFS/RADIO/BOOT/IMEI/calibration write was performed. Wi-Fi, USB, ZeroTier, SSH
intact. `./wonqed4real` NOT created (bearer not physically verified; no fabricated pass).
All host tests + fuzzer + ASan/UBSan green; on-device AArch64 cross-build green.
