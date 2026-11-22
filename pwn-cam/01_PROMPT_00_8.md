# 01_PROMPT_00_8 — CLOSE REAL GOLDEN NO-OP, WITHOUT LOSING RECOVERY

**Target:** Nuxel Samsung SM-G975F / beyond2lte, kernel 4.14.253. **Task:** qualify the revised offline Prompt 01 controls against the actual current live baseline and produce a trustworthy Prompt 02 entry decision. **No flashing. No device writes. No reboot.**

## Binding instructions and starting conditions

Read `pwn-cam/00_MASTER_CONTRACT.md`, `pwn-cam/01_PROMPT_00.md`, `pwn-cam/01_PROMPT_00_7.md`, `pwn-cam/02_PROMPT_01.md`, `reports/camera-00_8-offline-audit.md`, `reports/camera-01-dt-gate.md`, and the current revised tools. Treat safety-critical exit conditions as binding; where a requirement cannot be verified, BLOCK. Do not assume any claims based solely on this ZIP.

From the preceding Prompt 00_7 operator report (reported; **reverify**, because the raw evidence is deliberately absent from the public ZIP):
- Nuxel was normally booted; kernel `4.14.253-gf7194c1d15ed-dirty`; board revision 26; DTBO entry 9; active model `BEYOND2LTE EUR OPEN 26`.
- Off-device readbacks of BOOT/DTB/DTBO/recovery were captured and individually hash-checked. Live merged FDT SHA-256 begins `761df64a`; this is an **incomplete hash, not an attestation**.
- `pstore` contains a Samsung-encrypted record. `/dev/video*` has vendor FIMC-IS nodes; sensor probe must not be mistaken for working streaming.
- The old validator incorrectly blocked a stock dual-reference flash/torch GPIO relationship (gpg2 pin4 and gpg3 pin6) between the stock PMIC torch and FIMC flash nodes.
- BOOT reportedly uses separate DTB and DTBO partitions, without an appended BOOT FDT.
- No owner-approved manifest signature or independently trusted key; real golden no-op was BLOCKED; no on-device writes or reboots.

This repo update addresses the two **offline validator compatibility gaps** without allowing an unsigned physical release. It adds hash-pinned `--golden-merged` comparison for byte-identical pre-existing GPIO conflicts and an explicitly attested `separate-dtb-dtbo` BOOT path. **Do not bypass either protection.**

## Phase 0 — Preserve current phone and original evidence

1. Confirm exact source tree, pending local changes and file hashes before applying this drop-in. Work on a dedicated host branch/worktree. Do not erase uncommitted work or overwrite private reports. Preserve previous reports as historical, never rewrite their earlier BLOCK status to PASS.
2. Confirm there have been **zero device writes/reboots** since Prompt 00_7. Before any host-side action, confirm the phone is still normally running (read-only SSH, status, `/proc/cmdline`, `/sys/firmware/fdt` hash; no vendor camera STREAMON). If state changed, stop and recapture the entire live baseline.
3. Locate private off-device BOOT, DTB, DTBO, RECOVERY, active merged FDT, complete partition maps/capacities, board-selection evidence, and current TWRP rollback instructions. Do not copy private artifacts, signing keys, identifiers or sensitive reports into the public repo/ZIP. Recheck full SHA-256 and source-device readback equivalence. If anything cannot be verified independently: BLOCK.

## Phase 1 — Reproduce offline security gates and review the patch

4. Execute `bash tools/s10plus/tests/test-camera-dt-gate.sh` and `bash boot/s10plus/tests/test-boot-image-gates.sh`, capturing exact exit codes and all test/skip statuses. Expect at least 51 synthetic camera tests; do not silently promote a historical skipped A5/A25 test into PASS. A failure is a blocker, not a reason to weaken assertions.
5. Review changes in `tools/s10plus/{camera-dt-gate.py,verify-boot-image.py,camera-release-gate.py}` and the test suite. The new GPIO exception is NOT a hard-coded Samsung pin waiver: the exact same owner paths, full property bytes, GPIO tuple/flags and provider paths must exist in the hash-pinned golden merged FDT. A new owner, changed polarity, mutated tuple, wrong golden SHA or missing baseline must FAIL.
6. Run the exact current merged FDT with `camera-dt-gate.py --merged --golden-merged /PRIVATE/active-merged.fdt --golden-merged-sha256 ACTUAL_64_CHAR_SHA /PRIVATE/active-merged.fdt` and verify exit 0. Inspect remaining diagnostics in full. Be especially cautious of any second, unrelated false positive; repair only with source-grounded evidence and new negative fixtures. No broad allowlist, regex bypass, global ignore, or `--ignore-errors` option.
7. Test the same private baseline with a *temporary copy* containing deliberately altered stock flash flags, a new GPIO consumer, broken endpoints, wrong overlay selection and non-camera properties. Each must fail. Restore nothing on device because nothing was written.
8. Verify that the current BOOT truly has **no appended DTB** and that this is the *intended*, proven Samsung bootloader layout. Do not infer layout solely from a string in a report. The revised `verify-boot-image.py` requires separate DTB, selected DTBO and active merged FDT paths **plus their exact hashes, board revision and DTBO selection index**. It must still reject an absent appended DTB without this explicit evidence or any unexpected trailing payload.

## Phase 2 — Reconcile live boot topology and trust anchor

9. Independently confirm board-revision 26/entry 9 from `/proc/cmdline`, DTBO table entry metadata, live `/model`, board-capture notes, and any available Samsung bootloader evidence. Establish `bootloader_dt_source_verified` only if the current BOOT uses the separate DTB/DTBO source and the active merged FDT is consistent with it. **A signed assertion without physical source evidence is not enough.** If source selection/merge is unknown, BLOCK and document exact missing evidence.
10. Record `dt_layout: "separate-dtb-dtbo"` and `appended_dtb_index: null` only if physically verified; otherwise use the correct documented layout. The manifest must record raw full SHA-256 for current BOOT, DTB, DTBO, recovery, merged FDT, selected board evidence and rollback plan; include exact partition capacities, timestamp, two independent readback/copy checks, and explicit TRUE/FALSE physical proof statements. The template intentionally has non-PASS placeholders. NEVER populate guessed hashes or mark `rollback_ready` TRUE because a file simply exists.
11. **OWNER APPROVAL GATE (may require user action):** Ask the device owner to approve either an existing trusted manifest-signing key or a NEW trust-anchor creation procedure with independently recorded public-key fingerprint. Do not self-generate an unapproved trusted identity. Keep private key and golden backups completely outside Git and public handoff archives. If approval is absent, STOP with `READY_FOR_PROMPT_02=NO`, `SIGNING_TRUST=BLOCKED`.
12. Sign the *exact current* canonical manifest **only after owner approval**, verify the detached signature using the owner-approved public key, record the fingerprint and hashes outside the repo. A valid signature proves signed provenance, not that the physical bootloader was reconstructed or that the phone survived a new flash.
13. Verify recovery details: confirmed TWRP availability from prior trustworthy evidence or owner, raw partition names and image byte sizes, verified off-device restore sources, accessible recovery interface and hashes. Do not reboot to TWRP solely for this audit. If actual restore path is not demonstrated sufficiently for the Master Contract, mark `ROLLBACK_READY=UNKNOWN` and BLOCK.

## Phase 3 — Run REAL signed golden no-op (zero writes)

14. Use **immutable copies of EXACT current** BOOT/DTB/DTBO/FDT, never old A5/A25 binaries. Run from the host, substituting verified real absolute paths (the paths below are NOT existing files):

```bash
bash tools/s10plus/nuxel-camera-release-gate.sh \
  --manifest /PRIVATE/camera-00-artifact-manifest.json \
  --signature /PRIVATE/camera-00-artifact-manifest.json.sig \
  --trusted-pubkey /PRIVATE/owner-trusted-public.pem \
  --candidate-boot /PRIVATE/current-boot.img \
  --candidate-dtb /PRIVATE/current-dtb.img \
  --candidate-dtbo /PRIVATE/current-dtbo.img \
  --candidate-merged /PRIVATE/active-merged.fdt \
  --receipt-dir /PRIVATE/camera-00_8-noop-receipts \
  --receipt-signing-key /PRIVATE/owner-approved-receipt-signing-key.pem
```

15. Require a signed/hashed receipt with `PASS_OFFLINE_ONLY` and all five mandatory gates: `BOOT_CONTAINER_PASS`, `CAMERA_DT_GRAPH_PASS`, `ACTIVE_BOARD_MATCH`, `NO_UNRELATED_DT_DELTA`, `ROLLBACK_READY`. `PASS_OFFLINE_ONLY` **is not** permission to flash or proof that booting a future candidate will work.
16. Repeat the LIVE-BASELINE negative cases on offline copies: no signature, wrong trusted pubkey, stale capture, invalid board revision/index, corrupted DTBO entry, absent/mismatched backup, missing rollback proof, changed boot trailing bytes, changed GPIO consumer/flags, modified NFC/SSP/display property, partition overflow, altered candidate DTB/DTBO. All must exit nonzero. Capture failures and code in private reports without leaking sensitive sources.
17. If the actual no-op still fails despite genuine evidence, determine whether it is a real mismatch or a further gate false positive. Modify only host-side validation logic, add regression fixtures for both the legitimate baseline and the corruption, rerun *all* tests, and repeat the real no-op. Never weaken the input requirements to turn the gate green.

## Phase 4 — Prompt 02 source prerequisites (host only)

18. Inventory actual file availability. The supplied public ZIP has **no** `drivers/s10-camera-v4l2/exynos9820-csis.c`, `s5k-cis.c`, `ak7374.c`, complete `Linux4` tree, or actual module build artifacts; these may exist separately on the owner host and must be located before implementation. Inspect `pwn-cam/03_PROMPT_02.md` verbatim. For a clean port, pin the exact Linux 4.14 kernel commit `f7194c1d15eded1c2a1a4dc63825b26103435cc0` and upstream camera reference `d8135b2465b3` only after verifying provenance. Preserve licensing, and leave non-public camera firmware outside Git.
19. If 00/01 PASS, make an immutable and sanitized Prompt 02 handoff snapshot containing exact kernel source/version, all patches, current `.config`, toolchain, source metadata, native camera driver source, reproducible build instructions, tests and relevant redacted evidence. No driver probe, streaming test or flash in this prompt.

## Exit report and mandatory honesty

Deliver `reports/camera-00_8-real-noop.md`, `reports/camera-01-dt-gate.md` qualification addendum, `reports/camera-01-negative-results-live.txt` and `reports/camera-02-source-readiness.md` (redacted), along with host code diff and test logs. Preserve private signed artifacts outside repository.

Declare exactly:
- `DEVICE_REACHED`, `CURRENT_NUXEL_HEALTHY`, `LIVE_FDT_HASH_MATCH`, `PARTITION_BACKUPS_MATCH`, `BOARD_REV`, `DTBO_INDEX`, `BOOT_DT_LAYOUT`, `OWNER_SIGNING_TRUST`, `ROLLBACK_READY`, `REAL_GOLDEN_NOOP`, `NEGATIVE_GATE_TESTS`, `DEVICE_WRITES`, `DEVICE_REBOOTS`, `PROMPT00_PASS`, `PROMPT01_PASS`, `READY_FOR_PROMPT_02`.
- If any hardware/trust check remains unverified, `READY_FOR_PROMPT_02=NO`. Do not call a synthetic pass a live pass.
- **Only** start `pwn-cam/03_PROMPT_02.md` after BOTH live Prompt00 and real signed Prompt01 gates PASS. Even then, Prompt02 permits offline source/build work, **never flashing or rebooting**. Prompt04's independent deployment permissions remain mandatory.

**STOP immediately** on changed device identity, unavailable off-device backups, contradictory DT selection evidence, unexpectedly rebooting into TWRP, stale or untrusted key, failed recovery verification, any gate reporting a false PASS, or any request to write BOOT/DTB/DTBO during this stage. No automatic recovery loop, no speculative flash, no bootloader/firmware/rail/GPIO manipulation.
