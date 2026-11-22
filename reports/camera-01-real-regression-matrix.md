# Camera Prompt 01 — REAL regression matrix (2026-11-22, read-only)

**Status: tooling PASS (synthetic), live negative matrix BLOCKED on signing.**

## Offline synthetic suite (reproduced this session)

`bash tools/s10plus/tests/test-camera-dt-gate.sh` → **exit 0, 51/51 PASS**.

`bash boot/s10plus/tests/test-boot-image-gates.sh` → **exit 3 SKIP-PREREQ**
(historical A5/A25/A4 fixtures absent; not a pass, not a code regression).

## Real-image gate results (captured current baseline)

| Gate | Input | Result | Key evidence |
|---|---|---|---|
| BOOT container | current-boot.img | PASS | v1 header, 2048 page, raw arm64 Image, no appended DTB |
| DT base | current-dtb.img | PASS | 1 entry, 1117 nodes, FIMC=7/CSIS=0 |
| DT overlay | current-dtbo.img | PASS | 10 entries, entry 9 covers rev 26, FIMC=9/CSIS=0 |
| Merged FDT | active-merged.fdt | PASS | 1860 nodes, FIMC=16/CSIS=0, stock GPIO overlaps hash-pinned |

## Fail-closed negative cases verified by synthetic suite (51/51)

Covered (each must exit nonzero; verified by the suite):
absent signature, wrong trusted pubkey, stale capture, wrong board revision,
wrong DTBO index, corrupted DTBO entry, absent/mismatched backup, missing
rollback proof, changed BOOT trailing bytes, new/changed GPIO owner/flags,
modified NFC/SSP/display property, partition overflow, altered candidate DTB/
DTBO, simultaneous FIMC+native-CSIS binding, unknown PHY/clock, I2C collision,
wrong DT layout, missing source proof.

## Live-baseline negative matrix

**NOT executed** against real captured copies because it first requires the
owner-signed manifest + trusted pubkey. It is NOT reported as PASS. Once the
owner authorizes/signs, the exact real-image negative matrix (offline mutated
copies only; originals immutable) must be run and recorded.

## Mandatory note

`LIVE_FDT_HASH_MATCH = YES` (full `761df64a...` verified fresh from
`/sys/firmware/fdt`, not a copied prefix).

## Declaration

- CAMERA_DT_GRAPH_PASS = YES (on real captured DTB/DTBO/merged FDT)
- NO_UNRELATED_DT_DELTA = YES (golden self-comparison on real merged FDT)
- NEGATIVE_GATE_TESTS = synthetic PASS; live matrix BLOCKED (needs signature)
- DEVICE_PARTITION_WRITES = 0
- DEVICE_REBOOTS = 0
