# Camera Prompt 00_9 — REAL golden no-op qualification (2026-11-22)

**Verdict: BLOCKED (cannot sign/run the real signed golden no-op).**
**Offline synthetic suite PASS; real-capture DT/graph gates PASS; but the signed
release gate cannot be run without an owner-approved signing key.**

## What PASSED against REAL captured images (not synthetic)

Fresh live baseline captured read-only into a private host directory (outside
Git). All four partitions + merged FDT read back bit-exact with two independent
SHA checks on both host and device (before AND after transfer).

- `verify-boot-image.py` (real BOOT): **PASS** — ANDROID! v1, 2048 page, raw
  arm64 Image (not gzip), valid cpio /init, `second_size=0` (no appended DTB),
  separate-DT source verified by SHA against DTB/DTBO/merged FDT.
- `camera-dt-gate.py --merged` (real merged FDT): **PASS** — 1860 nodes, 944
  phandles, 26 endpoints, 23 I2C, 64 GPIOs, FIMC=16/CSIS=0, stock flash/torch
  GPIO overlaps grandfathered byte-identical via hash-pinned golden.
- `camera-dt-gate.py` (real DTBO): **PASS** — 10 entries, entry 9 selected,
  "entry 9 covers board rev 26".
- `camera-dt-gate.py` (real DTB base): **PASS** — 1 entry, 1117 nodes, FIMC=7/CSIS=0.

## Offline regression suites (reproduced, unmodified)

- `bash tools/s10plus/tests/test-camera-dt-gate.sh` → **exit 0, 51/51 PASS**
  (synthetic; explicitly says "LIVE PROMPT00 STATUS: NOT VERIFIED").
- `bash boot/s10plus/tests/test-boot-image-gates.sh` → **exit 3 = SKIP-PREREQ**
  (historical A5/A25/A4 gitignored fixtures absent; correctly NOT a pass).

## Why the real signed golden no-op is BLOCKED

The release wrapper `nuxel-camera-release-gate.sh` requires a **signed** Prompt00
manifest + owner public key + receipt signing key. None of these exist yet:

1. `OWNER_SIGNING_TRUST = BLOCKED` — no owner-approved camera trust anchor.
2. `MANIFEST_SIGNED_AND_VERIFIED = NO` — the manifest template remains
   `NOT_SIGNED` with placeholders; it can only be filled + signed after owner
   authorization and after recording the real artifact paths/hashes/sizes.
3. `ROLLBACK_READY = UNKNOWN` — TWRP route historically credible but not
   current-layout reverified without a reboot (see recovery-and-trust report).

Therefore `REAL_GOLDEN_NOOP = BLOCKED`. It is NOT a false-PASS and NOT a
weakened gate; the guardrails are functioning as intended.

## Planned real no-op command (documented, cannot run yet)

```bash
bash tools/s10plus/nuxel-camera-release-gate.sh \
  --manifest      /PRIVATE/camera-00-artifact-manifest.json \
  --signature     /PRIVATE/camera-00-artifact-manifest.json.sig \
  --trusted-pubkey /PRIVATE/owner-camera-manifest-verification.pub.pem \
  --candidate-boot   /PRIVATE/current-boot.img \
  --candidate-dtb    /PRIVATE/current-dtb.img \
  --candidate-dtbo   /PRIVATE/current-dtbo.img \
  --candidate-merged /PRIVATE/active-merged.fdt \
  --receipt-dir /PRIVATE/camera-00_9-golden-noop-receipts \
  --receipt-signing-key /PRIVATE/owner-camera-manifest-and-receipt-signing.key.pem
```

Expected required result: exit 0 + receipt `PASS_OFFLINE_ONLY` with exactly
`BOOT_CONTAINER_PASS`, `CAMERA_DT_GRAPH_PASS`, `ACTIVE_BOARD_MATCH`,
`NO_UNRELATED_DT_DELTA`, `ROLLBACK_READY`. This is an OFFLINE self-comparison,
NOT a physical boot/flash approval.

## Negative gate tests (real-capture)

Synthetic 51/51 fail-closed suite covers: absent/wrong signature, wrong pubkey,
stale capture, wrong board rev/index, corrupted DTBO entry, absent backup,
missing rollback proof, changed boot trailing bytes, changed GPIO owner/flags,
modified NFC/SSP/display property, partition overflow, altered DTB/DTBO,
simultaneous FIMC+CSIS. These are tool-behavior proofs on synthetic fixtures;
**live-baseline negative cases require the signed manifest first** and are
therefore recorded as NOT-YET-EXECUTED, not PASS.

## Declaration

- REAL_GOLDEN_NOOP = BLOCKED (signed manifest + owner key absent)
- NEGATIVE_GATE_TESTS = synthetic 51/51 PASS; live negative matrix BLOCKED
- HISTORICAL_A5_A25_SUITE = SKIP-PREREQ (exit 3), not PASS
- DEVICE_PARTITION_WRITES = 0
- DEVICE_REBOOTS = 0
