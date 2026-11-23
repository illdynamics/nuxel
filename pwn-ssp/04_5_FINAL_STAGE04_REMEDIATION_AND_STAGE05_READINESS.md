# PROMPT 04_5 — NUXEL S10+ SSP: FINAL STAGE-04 REMEDIATION, VERIFIED BOOT CANDIDATE & STAGE-05 HANDOFF

**Agent:** DeepSeek-V4-Pro-Thinking with access to the actual Nuxel development checkout, build host and (where available) the running S10+ / TWRP.

**Mission:** Integrate the supplied `NUXEL_SSP_STAGE04A_FULL_DROPIN.zip` (or its concatenated parts), independently audit its changes, resolve the Stage-04 `NO FLASH` blockers, and produce a **verifiable, reproducible, safely staged Stage-05 handoff**. **DO NOT FLASH A CANDIDATE IN THIS PROMPT.** Stage 05 alone governs any authorized BOOT-only write and subsequent physical first-light trial.

## 0. Governing constraints — no exceptions

- The recorded `reports/SSP-CANDIDATE-PREFLIGHT.json` is historically `NO_FLASH`. Preserve it unchanged; write new timestamped evidence instead. Never mark a gate PASS based on an assertion, stale report or mere existence of a file.
- Preserve all known-good data and unrelated local modifications. Never blindly run `git reset --hard`, `git clean -fdx`, overwrite `.build/src`, or delete the 28 unrelated netfilter modifications. If a clean checkout is needed, create a **separate** pinned worktree/clone on a case-sensitive filesystem, with the exact source commit and documented toolchain. Leave the original dirty tree untouched.
- Absolutely no writes to `dtb`, `dtbo`, `recovery`, bootloader, modem or other non-BOOT partitions; no device-tree source, overlay, merged-DT or embedded-BOOT-DT alterations. This S10+ donor was reported to have **no appended FDT** and zero-filled partition slack. Independently confirm rather than assume.
- **No BOOT flash in Stage 04_5.** Read-only verification of device partitions and staging a second known-good rollback copy on approved storage are allowed, provided current device mapping is verified. Do not execute a risky rail/reset/firmware trial or change persistent services here.
- Prefer the already-running kernel's `/dev/ttyBCM`, `/dev/bbd_sensor/control/patch` and `nuxel_bringup` userspace transport if a bounded, separately reviewed software-only first-light trial is sufficient. **Do not manufacture a new kernel merely to move a parser into kernel space.** If a BOOT change is not justified, document `NO_FLASH_NEEDED` and propose a safe Stage-05 software-only path; do not fabricate a candidate to satisfy this prompt.
- Maintain zero Android userspace dependencies. Keep the phone recoverable, preserve Nuxel's working functions and be truthful about missing physical evidence.
- If prerequisites are unavailable, stop with **BLOCKED / NO FLASH**, specify exactly what is missing, and produce a safe actionable handoff. Never weaken validation to force green.

## 1. Intake and provenance

1. Verify the input ZIP or parts against their accompanying checksums and test archive integrity. Extract into a staging directory; do not overwrite the live checkout immediately. Identify the actual repository root and compare every replacement file with the live version. Reject path traversal, unexpected symlinks, absolute paths, or unrelated changes.
2. Read, in order, `pwn/ssp*.md`, the revised Stage-05 prompt, `reports/SSP-STAGE-04A-OFFLINE-REPAIR.md`, `SSP_STAGE04A_AUDIT_AND_REMAINING_GATES.md` if provided, `reports/SSP-CANDIDATE-PREFLIGHT.json`, `reports/SSP-SOURCE-BUILD-MANIFEST.json`, kernel patch series, native SSP transport and relevant tests.
3. Establish exact live host/kernel/source versions and hash identities. Confirm whether the ZIP is older than the actual checkout. Produce an integration diff with every file accepted, rejected or manually reconciled. Do not overwrite newer work without review.
4. Review the replacement `pack-ssp-boot.py`, strict `build-kernel.sh`, source auditor, Stage-05 gate validator and synthetic tests **as untrusted proposed code**. The earlier offline tests are evidence, not proof of suitability for the actual donor.

## 2. Resolve the four Stage-04 blockers

### A. Clean pinned kernel source — previously FAIL

- Establish a fresh independent, case-sensitive source checkout at the **exact pinned commit** (`f7194c1d…` is only a prefix: obtain and verify the full commit from the manifest). Confirm repository origin, commit and submodules, if any.
- Preserve the dirty original tree and the 28 unrelated netfilter changes (historical diff digest `7340907c…`) without losing any work. Diagnose whether the dirty state was caused by a prior build, vendor patches or unrelated development; do not silently carry it into the SSP build.
- Apply only the reviewed SSP patch stack in the documented order. Verify the exact required patch digests/receipts (`0020`, `0023`, `0025`, `0027` where applicable), patch contents, no duplicate hunks, and no missing required changes. The historical digest prefixes `62a33964`, `b21abad6`, `ab293ae6`, `cc33f15e` are hints, not substitutes for full SHA-256 verification.
- Run `tools/s10plus/ssp-stage04/audit_kernel_source.py` in its intended strict mode, inspect the resulting source diff, and reject foreign changes. Verify critical kernel code paths, locking, firmware parser bounds, transport ownership and failure unwinding against the actual pinned tree.
- If the toolchain or pinned source cannot be obtained, mark this gate BLOCKED; do not invent a successful build.

### B. Exact full kernel build — previously FAIL

- First determine whether the BOOT candidate is **actually required** given the running kernel's existing BBD userspace passthrough. Record an evidence-based software-only versus kernel-change decision.
- If justified, use the exact toolchain, defconfig, live capability fragment and known firmware dependencies to run a full clean ARM64 build with `NUXEL_SSP_STRICT=1`; never set `NUXEL_SKIP_PATCHES=1`.
- Capture complete build logs, compiler version, config hash, patch receipts, `.config`, `System.map`, `arch/arm64/boot/Image`, size/hash, module and symbol evidence, and proof that expected Nuxel features remain present. Inspect the actual output rather than trusting a zero exit code alone.
- Run the native SSP C tests, negative/replay tests, orientation tests (historical 77), recovery tests (historical 14), and all Stage-04A synthetic/gate tests (historical 16). Also run `bash -n` on the build script and any additional relevant build tests. Fail closed on any regression.

### C. BOOT packaging for separate-DTB layout — previously FAIL

- Obtain a freshly verified **full-size known-good BOOT donor** from the established read-only source. Cross-check its SHA-256 with the independently recorded donor identity and the running device where possible. The previous report cites donor SHA `0e6aa34cdc550fd975129d9fc0f9dc785733e0483e3b8c119eb4592b5463621c`, but this is not a substitute for current verification.
- Confirm the real BOOT header version, addresses, page alignment, kernel/ramdisk sizes, zero-filled slack, lack of appended FDT, and exact BOOT partition size. If the actual donor differs from the supported layout, **do not guess or patch around the mismatch**; investigate and extend the packer with tests first.
- If a new kernel is justified and built, use the corrected `tools/s10plus/pack-ssp-boot.py` to construct a candidate from the verified donor. Only the intended raw kernel payload and corresponding kernel-size header field may change. Preserve ramdisk bytes, all other header fields and slack, and never append or alter DT data.
- Independently run `verify-boot-image.py` with **real** separate-DTB, DTBO, selected overlay index, board revision and merged-FDT evidence. Do not fabricate merged-FDT hashes or reuse a stale device selection. Verify candidate SHA, partition fit, header, unchanged ramdisk and zero slack, and document independent read-only DTB/DTBO partition hashes.
- If no BOOT change is justified, mark packaging `NOT_APPLICABLE_NO_FLASH_NEEDED` with an explicit reviewed rationale; do not falsely label an unbuilt candidate PASS.

### D. Second independently verified TWRP-accessible rollback — previously PARTIAL

- Preserve and revalidate the existing host known-good BOOT seed, size and full SHA-256.
- Arrange a **second independently accessible** known-good BOOT copy on owner-approved storage that TWRP can actually read if the candidate fails to boot. This may require an intentional TWRP session for **staging only**, not flashing. Confirm the recovery session, available storage, accessibility and current partition mapping before proceeding.
- Compare SHA-256 and exact byte length at both the host and TWRP endpoints, and verify that the TWRP copy remains accessible independently of the normal Nuxel boot. Do not confuse two filenames on one inaccessible filesystem with two recovery endpoints.
- Record a restoration plan and read-only partition map evidence. **Do not execute a restore or write BOOT in this stage.** If TWRP is not available, leave rollback BLOCKED and tell the owner precisely when TWRP access is needed.

## 3. Preflight and evidence gate

1. Preserve the old `reports/SSP-CANDIDATE-PREFLIGHT.json` unchanged. Generate a **new** timestamped `reports/SSP-CANDIDATE-PREFLIGHT-REVALIDATED.json` and detailed Markdown report with independently evidenced PASS/FAIL/BLOCKED for each original Stage-04 gate and new safeguards.
2. Include exact artifact paths, byte lengths, SHA-256, source commit, build/toolchain/config, patch receipts, test commands/results, BOOT donor/candidate hashes, DTB/DTBO and merged-DT evidence, host/TWRP rollback receipts, current device state and explicit software-only necessity review.
3. Run `tools/s10plus/ssp-stage04/verify_stage05_gate.py` against the new receipt. Understand that exit 0 means **reported gates** passed, not that hardware has been proven or that a flash is automatically authorized. Validate the tool's accepted schema against actual required evidence.
4. Require explicit trial scope and owner authorization for the specific Stage-05 BOOT-only operation; do not infer permission for power-rail experiments, other partitions or unlimited retries. The owner's existing agreement permits *only verified BOOT-only candidate flashes* once all safety gates pass.
5. Publish a binary decision: `READY_FOR_STAGE_05_BOOT_ONLY_REVIEW`, `READY_FOR_STAGE_05_SOFTWARE_ONLY`, or `BLOCKED_NO_FLASH`. No partial/conditional PASS disguised as readiness.

## 4. TWRP agreement to carry into Stage 05 (do not execute here)

When Stage 05 later intentionally boots into TWRP and flashes a fully verified BOOT-only candidate, the agent must then explicitly request a **normal Nuxel boot**. If the phone instead unexpectedly returns to TWRP, bootloops, hangs, or fails bounded SSH/systemd/UI checks, the candidate **FAILED** even if the flash/readback succeeded. Distinguish intentional recovery entry from unexpected fallback.

On failure, preserve logs and hashes, diagnose the root cause, restore the independently verified known-good BOOT via the validated recovery procedure when necessary, and confirm Nuxel boots normally. Never blindly retry the same candidate. Only after an evidence-backed correction, fresh offline rebuild, complete Stage-04 preflight and verified *different* candidate may another BOOT-only trial occur. At most **two distinct candidate flashes per Stage-05 session**, with new owner approval required beyond that. If known-good BOOT also fails, stop safely and report; do not touch DTB, DTBO, recovery or other partitions. The objective is verified Nuxel recovery, **not** infinite automated reflashing.

## 5. Required deliverables

- `reports/SSP-STAGE-04_5-FINAL-REMEDIATION.md`: detailed root-cause analysis and every completed/uncompleted gate.
- `reports/SSP-CANDIDATE-PREFLIGHT-REVALIDATED.json`: fresh, machine-checkable evidence, preserving original NO_FLASH receipt.
- `reports/SSP-STAGE-04_5-SOURCE-BUILD-MANIFEST.json`: pinned source, exact patches, toolchain, config, build artifacts and test receipts.
- `reports/SSP-STAGE-04_5-BOOT-AND-ROLLBACK-MANIFEST.json`: actual BOOT donor/candidate identities if applicable, separate-DT evidence, host and TWRP rollback hashes/locations and exact recovery readiness.
- Reviewable source diffs/patches, all tests and logs, any corrected packaging code, and a minimal Stage-05 handoff note explaining the exact next action.
- If the candidate is actually needed: a **verified BOOT candidate staged but NOT flashed**; if not needed: a reviewed software-only plan with no artificial BOOT candidate.

## 6. Exit criteria and mandatory final response

Print a table with status and evidence for: `CLEAN_PINNED_SOURCE`, `PATCH_STACK_EXACT`, `FULL_KERNEL_BUILD` (or justified N/A), `OFFLINE_TESTS`, `SOFTWARE_ONLY_ALTERNATIVE`, `BOOT_DONOR_VERIFIED`, `BOOT_CANDIDATE_INDEPENDENTLY_VERIFIED` (or justified N/A), `EXTERNAL_DTB_UNCHANGED`, `EXTERNAL_DTBO_UNCHANGED`, `TWRP_PARTITION_MAPPING`, `HOST_ROLLBACK_VERIFIED`, `TWRP_ROLLBACK_VERIFIED`, `PREFLIGHT_MACHINE_GATE`, `OWNER_SCOPE`, `NUXEL_HEALTHY`.

End with one of the exact decisions above, then say either **"Stage 05 may begin with its own live checks; no candidate has been flashed"** or **"NO FLASH: Stage 05 is blocked; here are the exact missing proofs."** Do not claim physical SSP first light, working accelerometer/gyroscope, or autorotation from offline evidence.

**Start now:** inspect the supplied ZIP, current checkout and historical preflight. Work through the blockers until all verifiable prerequisites are satisfied, without destructive cleanup or any candidate flash. If an external dependency prevents completion, produce the complete partial deliverables and a precise owner-action request rather than pretending readiness.
