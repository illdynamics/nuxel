# 01_PROMPT_00_7 — POST-PATCH LIVE BASELINE, CAMERA GATE QUALIFICATION & PROMPT 02 HANDOFF

**Role:** Senior Exynos9820/Samsung S10+ Linux recovery engineer and independent release-gate auditor. **Device:** Nuxel SM-G975F / beyond2lte (verify; never assume). **Starting artifact:** extracted `nuxel-cs-cam-PROMPT01-PATCHED-2026-11-22.zip`. **Purpose:** close the real-world evidence gaps from Prompt 00, qualify the offline Prompt 01 gates on the actual running system, and decide whether it is safe to start **Prompt 02 (native camera driver port)**. This is NOT a flashing prompt.

## Authority and absolute rules

Read and obey `pwn-cam/00_MASTER_CONTRACT.md`, `pwn-cam/01_PROMPT_00.md`, `pwn-cam/01_PROMPT_00_5.md`, `pwn-cam/01_PROMPT_00_6.md`, `reports/camera-00-postincident-baseline.md`, `reports/camera-01-dt-gate.md`, and the original `02_PROMPT_01(3).md` if supplied. Where instructions conflict, choose the stricter non-writing/recovery-preserving rule, document the conflict, and ask the owner before any operation with ambiguous risk.

**HARD RULES:** No writes to BOOT, DTB, DTBO, RECOVERY, bootloader, partitions, GPIO, regulators, firmware, kernel installation, or persistent device-tree settings. No reboots, TWRP entry, STREAMON, camera stress tests, or recovery restore just to complete this checklist. No speculative board revisions, DTBO indices, partition paths, golden hashes, health statuses, or evidence signatures. No automatic retry loops. Never alter the signed baseline or original backup in place. Never treat a successful synthetic test, historical A5/A25 image, signed assertion, or source compile as proof of the current phone's health. If Nuxel is already in TWRP unexpectedly, stop and follow Emergency Prompt R with owner approval; do not attempt a new experimental boot.

This stage may make normal changes to the **host-side repository, reports and off-device private evidence directory**; on-device actions must be read-only. Do not place private partitions, keys, device identifiers, or sensitive logs into Git or a public handoff ZIP. Explicit owner approval is required before any later flashing stage.

## Phase A — Unpack, identify, and freeze the source of truth

1. Verify the supplied ZIP's integrity and SHA-256 against `NUXEL_CAMERA_PROMPT01_ARCHIVE_SHA256SUMS.txt` / reconstruction manifest if present. Expected complete ZIP hash from the previous handoff: `4456cb6df57bc92bcb5aa5c3593e10444b99494ceafedd9cb8ca3b5cdc23a643`. If mismatch: **STOP**, report discrepancy; do not silently substitute another snapshot.
2. Extract into a fresh host-side directory. Inventory actual top-level root and ensure no unexpected traversal/symlinks escaped extraction. Do not overwrite the live repo blindly. Compare source trees, staged patches, and the working host repository. This ZIP may not contain `.git`; report unknown branch/HEAD rather than inventing them.
3. Preserve the unmodified extracted tree and create an isolated working copy/branch for any host-side report or test changes. Record source hashes and all differences. Avoid running repository-provided scripts as root until inspected.
4. Confirm presence and contents of `tools/s10plus/verify-boot-image.py`, `tools/s10plus/camera-dt-gate.py`, `tools/s10plus/camera-release-gate.py`, `tools/s10plus/nuxel-camera-release-gate.sh`, `tools/s10plus/tests/test-camera-dt-gate.sh`, `boot/s10plus/tests/test-boot-image-gates.sh`, and `reports/camera-00-artifact-manifest.template.json`. Check whether any script has changed since the delivered patch.

## Phase B — Reproduce offline Prompt 01 qualification

5. Run `bash tools/s10plus/tests/test-camera-dt-gate.sh` and `bash boot/s10plus/tests/test-boot-image-gates.sh` from the extracted repo. Capture stdout/stderr, exit status, tool versions, test count, skips and timeouts. Previous synthetic result was **44/44 PASS**, but you must reproduce it, not copy that claim. If tests fail, diagnose and repair host-side scripts/fixtures without weakening the invariants; rerun the entire suite. Never call a skipped required test PASS.
6. Independently inspect the gate implementation for missing manifest checks, malformed DTBO table/entry selection, FDT bounds, phandle graph correctness, invalid address-cells, GPIO/clock/PHY/reset/regulator/pinctrl references, endpoint reciprocity, I2C collisions, FIMC-vs-CSIS exclusivity, unexpected NFC/SSP/display changes, partition overflow, kernel header/offset 40/page-size/ramdisk checks, image hashes, candidate approvals and receipt-signature handling. Run targeted negative fixtures and record exact exit codes. Tests must fail closed; do not add a bypass or fake PASS fixture.
7. Confirm that the release gate cannot be made green merely by supplying a board string or synthetic manifest. Explicitly verify that modified separate DTB/DTBO images remain blocked and that a supplied candidate-merged FDT is not accepted as proof of a proprietary bootloader merge.

## Phase C — Establish fresh current-device truth (read-only)

8. Confirm Nuxel is reachable and normally booted before running SSH commands. Ask for connection details/authorization if unavailable. Record timestamp and clock skew, `uname -a`, `/proc/version`, `/proc/cmdline`, `/proc/config.gz` if available, current kernel modules, systemd state, root filesystem/mounts, `/proc/mounts`, device model and board revision from independent available sources. Do not assume the historical revision 26 / DTBO entry 9 is current.
9. Capture the **live merged FDT** from `/sys/firmware/fdt` if present, otherwise a carefully documented read-only snapshot of `/sys/firmware/devicetree/base` or `/proc/device-tree` with limitations. Preserve the raw FDT when available; a reconstructed tree is not byte-identical to the active blob. Record SHA-256, board identity, `/chosen`, camera nodes, regulators, clocks, CSI/PHY links and all other relevant enabled nodes. Document the actual DTBO selection if independently observable; if not, mark it **UNKNOWN** and block the affected gate.
10. Discover actual partition mappings and capacities from the live device; never assume `by-name` paths. Determine whether BOOT, DTB, DTBO, RECOVERY exist separately and whether they are safe to read. Capture full raw images using **read-only access** into a private, off-device location via a verified transfer path. Never dump into a mounted device partition, overwrite a partition, or stream secrets into the repo. Record source block device identity, byte size, full SHA-256, partition capacity, acquisition time, and second independent hash verification after transfer. If permissions prohibit safe reads, stop and report a blocker rather than using a dangerous workaround.
11. Compare the live BOOT container, appended FDT(s), separate DTB/DTBO images, selected overlay evidence and active merged tree. Do not conflate Android BOOT v1 `recovery_dtbo` header fields with the separate DTBO partition. Identify any bootloader merge/variant-selection uncertainty explicitly. Do not claim semantic equivalence unless it is actually established.
12. Gather read-only service and health evidence: SSH, Wi-Fi, display/touch/graphics, audio/microphone, sensors/SSP, NFC where applicable, `/dev/video*`, camera driver binding and firmware identities. Do not issue vendor streaming ioctls. Collect relevant `dmesg`, pstore and incident logs without reproducing the crash. Sanitize exports.
13. Establish a **credible TWRP recovery plan** using current partition names, sizes, golden image locations, expected restore hashes and owner-accessible recovery method. Verify backups exist **off-device** and are readable; verify TWRP availability only from already-existing trustworthy evidence or owner confirmation, without rebooting just to check. A documented plan is not a tested restore. Keep `ROLLBACK_READY=UNKNOWN/FAIL` until the evidence satisfies the Master Contract.

## Phase D — Complete Prompt 00 evidence and cryptographic provenance

14. Create/update `reports/camera-00-postincident-baseline.md` with exact findings, timestamps, evidence pointers, discrepancies, incident timeline, `CURRENT_NUXEL_HEALTHY`, `ROLLBACK_READY`, `PROMPT00_EXIT_GATE` and every remaining UNKNOWN. Preserve the previous blocked report in history; do not rewrite it as though it had originally passed.
15. Populate a **private** copy of `reports/camera-00-artifact-manifest.template.json` using only verified actual file paths, hashes, sizes, board revision, overlay selection, active FDT and rollback evidence. Inspect `camera-release-gate.py`'s `check_manifest` contract before populating. Store sensitive artifacts and keys outside Git. If trusted signing infrastructure is available, sign the exact canonical manifest with an owner-controlled key, verify the detached signature using the trusted public key, and record its fingerprint. **Never generate a key and call it independently trusted without owner approval.** A valid signature proves provenance, not hardware correctness.
16. Require two independent forms of consistency evidence wherever practical: partition readback hashes versus off-device copy, BOOT members versus manifest, active FDT versus documented selection, actual board identity versus signed manifest. Any unresolved mismatch = BLOCK.

## Phase E — Real golden no-op release gate (no flash)

17. Use **copies of the exact current verified golden** BOOT, DTB and DTBO images and the actual active merged FDT as the candidate for a no-change test. Never synthesize a current golden from an old release file. Execute the real release gate with its documented flags:

```bash
bash tools/s10plus/nuxel-camera-release-gate.sh \
  --manifest /PRIVATE/camera-00-artifact-manifest.json \
  --signature /PRIVATE/camera-00-artifact-manifest.json.sig \
  --trusted-pubkey /PRIVATE/trusted-camera-audit-pubkey.pem \
  --candidate-boot /PRIVATE/golden-boot.img \
  --candidate-dtb /PRIVATE/golden-dtb.img \
  --candidate-dtbo /PRIVATE/golden-dtbo.img \
  --candidate-merged /PRIVATE/active-merged.fdt \
  --receipt-dir /PRIVATE/camera-golden-noop-receipts \
  --receipt-signing-key /PRIVATE/owner-approved-receipt-signing-key.pem
```

These paths are placeholders, **not** permission to create fake files. Inspect `--help` and the code first. If the device has no separate DTB/DTBO partitions or the required selection cannot be proven, report the current tool's limitation and **BLOCK**, rather than inventing a partition image or weakening the gate.
18. Require the real no-op to pass: `BOOT_CONTAINER_PASS + CAMERA_DT_GRAPH_PASS + ACTIVE_BOARD_MATCH + NO_UNRELATED_DT_DELTA + ROLLBACK_READY`. Verify the receipt is hash-linked to actual input artifacts, has the expected provenance/signature, and that all inputs remained unchanged. Capture negative tests on the **same current baseline** using copies modified offline only (e.g. wrong revision, missing backup, altered hash, unexpected non-camera property). Do not corrupt original evidence.
19. If a genuine known-good no-op is rejected, determine whether the gate is detecting a real mismatch or has a false positive. Repair validators only with source-backed evidence and fresh negative tests. Do not bypass checks or fabricate acceptance. Rerun the full regression suite after any change.

## Phase F — Strict decision and handoff to Prompt 02

20. Deliver:
    - `reports/camera-00-postincident-baseline.md` (fresh factual update)
    - `reports/camera-00-live-evidence-index.md` (redacted paths, timestamps, provenance, gaps)
    - private signed manifest and off-device backup bundle **outside repository**
    - `reports/camera-01-dt-gate.md` (current-device qualification addendum)
    - `reports/camera-01-real-noop-receipt.md` (or explicit BLOCK and cause)
    - `reports/camera-01-negative-results-live.txt`
    - `reports/camera-00_7-prompt02-readiness.md` with exact PASS/BLOCK decision, remaining risks, source diff, test commands/results and SHA-256 identities
    - updated scripts/tests only where proven necessary, plus a patch and checksums for host-side changes.
21. **Prompt 02 readiness** requires BOTH Prompt 00 live-device EXIT GATE PASS and Prompt 01 real golden no-op/negative gates PASS. Only then state `READY_FOR_PROMPT_02=YES`. Otherwise `READY_FOR_PROMPT_02=NO`, enumerate exact blockers and give the smallest read-only next steps. Prompt 02 is driver-port/source work, **not permission to flash**. Future Prompt 04 still requires independent authorization and the Master Contract's flashing gates.
22. At end, state explicitly: whether the device was reached; whether the active FDT and partition backups were truly captured; current board/overlay identity; test totals; signed manifest status; real golden no-op result; rollback evidence status; whether any on-device writes/reboots occurred (expected **ZERO**); and whether Prompt 02 can begin. Never report a future action as already completed.

## STOP conditions

Stop immediately and preserve evidence if: unexpected TWRP boot, device instability, identity mismatch, absent/invalid off-device backup, unknown DTBO selection, missing active FDT proof, signed manifest failure, unexpected non-camera DT changes, test bypass, release-gate false PASS, unexpected partition mapping, or any request to flash during this stage. Escalate to owner with evidence. Do not loop on experimental boots or attempt a rescue write under this prompt.

**Final instruction:** The prior ZIP's **44/44 synthetic tests and historical BOOT PASS are not sufficient**. Your mission is to close the real Prompt 00 evidence gap and prove Prompt 01 against the current Nuxel state, or return an honest BLOCK. Do not begin Prompt 02 unless the entry conditions are satisfied.
