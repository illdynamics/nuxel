# PROMPT 01 — MAKE A BROKEN DEVICE TREE UNFLASHABLE (OFFLINE GUARDRAIL ENGINEERING)

**Entry:** PROMPT 00 PASS with verified off-device current BOOT/DT backups and active merged FDT. **Zero writes this round.**

**Implement in repository:**

1. Extend (do not weaken) `tools/s10plus/verify-boot-image.py` and `boot/s10plus/tests/test-boot-image-gates.sh` to enforce actual BOOT v1 header, 2048 page size, raw ARM64 Image, correct header field at offset 40, ramdisk cpio `/init` contract, source and size identity. Warn-only on missing/malformed boot-critical DT is NOT safe; use hard failure. Detect appended multiple FDT payloads versus actual bootloader variant selection. Do not mistake header `recovery_dtbo` fields for the separate DTBO partition.
2. Add `tools/s10plus/camera-dt-gate.py` plus tests. Parse the real DTB/DTBO formats: `dtc`, `fdtdump`/libfdt where available, Android DTBO table header/entries where applicable, selected board revision/overlay ID and merged in-memory FDT. Check structural integrity, size/offset/alignment, phandles, `#address-cells`, endpoints bidirectionality, `remote-endpoint`, lane count/map, I2C bus/address collisions, clock/reset/PHY/regulator/pinctrl references, GPIO ownership and polarity, mutual exclusivity of vendor FIMC and native CSIS. Reject missing or truncated entry selection and unknown board variants.
3. Build a **golden no-change baseline** with exact same kernel/ramdisk/DTB/DTBO members and validate semantic equivalence against current active tree. Distinguish harmless serialization changes from functional properties. Compare flash candidate member SHA hashes, and produce a machine-readable before/after diff. Include an allowlist: only camera nodes/explicit dependent resources for a camera candidate. Every other changed property must hard-fail pending review.
4. Add negative test fixtures proving fail-closed behavior for: wrong model/board revision, malformed header, gzip-kernel payload, bad DTB magic/totalsize, wrong DTBO selection, invalid/missing `remote-endpoint`, I2C address collision, unknown/nonexistent clock, PHY/reset, wrong lane count, wrong GPIO ownership, simultaneous FIMC/CSIS binding, unexpected NFC/SSP/display change, partition overflow, absent backup, absent rollback manifest, image-hash mismatch.
5. Validate scripts against actual historical BOOT repair cases, but clearly label historic fixtures `HISTORICAL`. Do not treat an old A5/A25 candidate as current known-good. Ensure automated verification never edits or overwrites the input golden image.
6. Produce a one-command release gate that returns nonzero on any violated invariant and creates signed/hashed provenance/validation receipts. The only acceptable release state is `BOOT_CONTAINER_PASS + CAMERA_DT_GRAPH_PASS + ACTIVE_BOARD_MATCH + NO_UNRELATED_DT_DELTA + ROLLBACK_READY`.

**Deliver:** tests, deterministic validators, `reports/camera-01-dt-gate.md`, negative-fixture outputs, example golden no-op pass + intentionally broken failure. No hardware flash, no board edits. **EXIT GATE:** hard FAIL on every injected broken-case and exact baseline semantic PASS.

---
