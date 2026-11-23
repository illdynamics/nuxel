# NUXEL — PROMPT 03.7: STAGE-04 PHYSICAL CP BOOT CLEARANCE
## Eliminate the remaining executable/firmware blockers; leave Nuxel ready for one reviewed CP boot trial

**Lead model:** DeepSeek V4 Pro Thinking. Delegate isolated mechanical tasks to Flash Thinking.  
**Target:** Samsung SM-G975F / beyond2lte / Exynos9820 / Shannon S5000AP; Nuxel native glibc/systemd Linux.  
**Repo:** `cs/mob`, last reported commit `45b9097f3c989347ebc8572d733ca4e3a72f63e4` (verify live HEAD).  
**Goal:** Leave the codebase and actual handset at **`READY_FOR_04_OWNER_REVIEW`** with a real, source-backed bootstrap implementation, verified EFUJ2 input, reproducible AArch64 build, validated safety properties and a complete, precise single-trial proposal.

### 0 — Execution authority: do not stop for permission already given

**The owner explicitly authorizes, for this preparation round:** bounded owner-host and handset **read-only** inventory, hashing, public firmware metadata parsing, stream-only verification of the installed `radio` partition, live status diagnostics through the verified read-only `IOCTL_MODEM_STATUS`, offline source acquisition from legitimate repositories, compilation, tests, static analysis, simulated boot-protocol tests, reversible **userspace-only** installation of inert/dry-run helpers with verified backups and uninstall plans, creation of owner-private evidence, and scoped Git commits. Do the work; do not return a permission questionnaire for these operations.

The owner also selects the **currently installed EFUJ2 RADIO** as the preferred **read-only** firmware source, not the older DTK9 candidate. Do not block on the missing DTK9 archive unless there is specific evidence it is needed for the EFUJ2 execution path. Obtain any available independently trustworthy EFUJ2 OEM provenance/firmware metadata without silently upgrading weak sources to cryptographic proof.

**Not authorized in this round:** any CP power, boot, firmware load/transmission, security-request, reset, RF activation, TWRP reboot/flash, BOOT/DTB/DTBO changes, partition writes, EFS/NV/identity operations, signature bypass or changes to radio state. This round must finish *before* physical Prompt 04. The owner will review and approve the exact physical execution manifest after it exists. No request text can substitute for unknown firmware hashes or missing hardware evidence. Do not weaken verification gates to avoid a blocker.

**Operating principle:** advance autonomously through *all* non-mutating/offline and expressly approved reversible userspace work. If a genuine verification problem remains, name the exact evidence deficit, try every safe legitimate route to resolve it, and stop with a useful artifact rather than another generic report.

### 1 — Read the actual latest worktree and authoritative evidence

Read and reconcile all of:

- `pwn-mob/00_MASTER_SAFETY_AND_TRUTH.md`
- `pwn-mob/02_CP_FIRMWARE_VALIDATION.md`
- `pwn-mob/03_CBD_ABI_AND_OFFLINE_BUILD.md`
- `pwn-mob/04_CP_BOOT_CONTROLLED_TRIAL.md`
- `pwn-mob/09_TWRP_A_ONLY_RECOVERY_AGREEMENT.md`
- `reports/S5000AP-02-CP-FIRMWARE-IDENTITY.md`
- `reports/S5000AP-03-BOOT-CONTRACT-ABI.md`
- `reports/S5000AP-03-BUILD-RECEIPT.md`
- ALL `reports/S5000AP-03_5-*`
- ALL `reports/S5000AP-03_6-*`
- `reports/S5000AP-04-CP-BOOT-LIVE.md`
- `tools/s10plus/s5000ap-uapi/*`, `tools/s10plus/cp-firmware/*`
- root `mobile.md`, `configs/nuxel/modem/modem.json`
- pinned *actual* kernel source `drivers/misc/modem_v1/` and matching build `.config`
- pinned Lineage Samsung `cpboot_v3` and Exynos9820 `BoardConfigCommon.mk` sources.

Audit Git status and owner changes without accidental `git add -A`. Resolve or properly document the pending `pwn-mobile/`→`pwn-mob/` migration. Preserve private firmware outside Git. Rebuild the evidence matrix, marking older stale claims as superseded without deleting historical reports.

**Critical reconciliation:** Round-04 NO-GO occurred before the 03.6 improvements. `03.6` established `-t ss310` under **SIPC+legacy** and installed RADIO=`EFUJ2`, not DTK9. Old `03.5` proposal body has stale assumptions and must be superseded, not reused uncritically.

### 2 — Prove the exact EFUJ2 firmware source contract read-only

The last live report identifies:

- Device: `SM-G975F`, Exynos9820, revision 26.
- `radio` GPT PARTLABEL: `/dev/sda16`, size **52,428,800 bytes**.
- Installed image build: `G975FXXSEFUJ2_CL2054966_QB20745891`, model `SM-G975F_EUR_XX_EUR0`.
- Previous full-partition SHA256: `9ffa1426a4ef7d1187779a14f22ec4b8cb4c2ab473b6626304a77030d9966fc7`.
- Old derived DTK9 file SHA256: `1e4280d26de704281c01ddf59407fbfdfb714d3f87a55b780f6f74d1ab0e7881`; **DO NOT use that file or DTK9 offsets for the EFUJ2 plan**.

Refresh board identity and block mapping. Re-confirm `radio` by actual GPT PARTLABEL, not by blindly trusting `sda16`. Stream/hash exact partition contents using bounded **read-only** access, without modifying or publishing the blob. Parse the **installed EFUJ2** ITOC safely, validate available part CRC32, offsets, sizes, bounds, duplicates, alignment, metadata/signing fields and complete source size. Record EFUJ2 BOOT/MAIN/VSS/NV/OFFSET section metadata and SHA256/CRC receipts *from EFUJ2*, not from DTK9. Avoid copying private firmware to repo or logs.

Investigate available trustworthy OEM EFUJ2 package/chain-of-custody and device bootloader identity. Distinguish: physical source identity, container structural integrity, trusted distribution provenance, secure-boot signature verification and actual device/TEE acceptance. A hash or CRC does NOT authenticate Samsung origin. If TEE acceptance is fundamentally hardware-only, label `DEVICE_ACCEPTANCE_PENDING_04` instead of hallucinating PASS. Do not request the unrelated DTK9 archive when the selected source is installed EFUJ2. If provenance is still insufficient even for a bounded physical trial, make that a precise BLOCKED gate with evidence.

Verify source input contract (`-P` or equivalent): read-only RADIO source, exact format expected, source-open flags, what reaches kernel through `XMIT_BOOT`, runtime path resolution, and **never any RADIO writes**. Do not assume the full partition is identical to a standalone `.bin` without proof.

### 3 — Fix the REAL blocker: source-faithful functional CP bootstrap

Do **not** stop at another dry-run-only report. Build a complete **offline-testable** userland bootstrap that faithfully implements the exact matching Samsung legacy SIPC protocol, while leaving hardware actions disabled unless a future reviewed Stage 04 binary is deliberately built and enabled.

Evaluate both realistic architectures with evidence:

**A. Port the pinned `cpboot_v3` boot transaction and narrowly necessary helpers to glibc/systemd.** The Android Soong/Bionic binary is not directly runnable, but Android build dependencies do not by themselves prove that source-level porting would require an entire Android framework. Replace logging/property/SELinux wrappers at the smallest verified boundary; preserve the actual Samsung boot transaction, state machine and error behavior. Keep all dependencies pinned and licensing compliant.

**B. Finish the native `nuxel-cpbootd` using the exact extracted Samsung transaction.** Use this only if the port is demonstrably more risky or impractical. Show a source-to-implementation mapping for every message, struct, ioctl, firmware section and state transition.

Source pins reported previously:
- Kernel base `f7194c1d15eded1c2a1a4dc63825b26103435cc0` (verify running diff/config).
- `cpboot_v3` reference `234b138716426c36ed801a71052bc144f7d8d806` (verify repo/commit).
- Exynos9820 config `protocol=sipc`, `use_legacy_sipc_ioctl=true`.
- Correct command type `ss310` for that compile configuration.
- `struct modem_firmware` = **28 bytes**, `modem_sec_req` = **16 bytes**; verify target compiler, kernel handlers and all field semantics again.

**Current `nuxel-cpbootd.c` has critical defects that MUST be fixed:**

1. `execute_boot_stage` silently returns 0 for POWER_ON, BOOT_OFF, SIPC MAIN transfer, the initial status stage and ONLINE validation; these are **not implemented**. No silent success for required stages, ever.
2. `IOCTL_MODEM_XMIT_BOOT` and `IOCTL_SECURITY_REQ` are explicit stubs. Implement correct bounded request construction and parsing from the *EFUJ2* container only after comparing matching source semantics.
3. The software does not implement genuine SIPC UDL framing/handshake, stage response verification, security request sequencing or boot completion. Reproduce them in deterministic hardware-disabled mocks with golden transcripts grounded in Samsung source.
4. Failure exits through cleanup with process status **0**. Every error/abort/invalid response must return nonzero with machine-readable first failing stage.
5. `#ifdef NUXEL_CPBOOTD_ENABLE_HW` compiles hardware code even if macro value is 0. Replace with a value-aware compile-time guard; require a runtime one-shot flag plus an exact immutable manifest in future 04. Dry-run must not open writable hardware interfaces.
6. `--deadline-ms` uses unchecked `atol`; a completed blocking syscall is measured after the fact, not bounded. Validate numeric ranges and design real stage-wide deadlines/interrupt handling where possible, documenting kernel-call cancellation limitations; no endless retry/power cycles.
7. `flock` on the character node alone does not establish exclusion against stock CBD or other drivers/userspace. Use a well-defined lock contract plus process/node ownership preflight; verify concurrency and release on error.
8. The `--node` argument must not permit arbitrary device selection for a physical run. Bind it to the independently verified node and identity, with a separate synthetic test endpoint for mocks.
9. Current plan reports DTK9 BOOT/MAIN sizes; the EFUJ2 source must be parsed at runtime under strict bounds, never populated from DTK9 constants.
10. The latest source-report stage ordering and older proposal ordering do not fully agree. Produce one **canonical call graph** from pinned source with exact ioctl/packet operations, expected responses, timeout, and kernel source references. Do not invent sequence details.

All paths must fail closed on invalid firmware/ABI, unexpected state, partial read/write, timeout, bad response, out-of-range address, insecure source, competing owner or kernel error. No negative test should leave hardware enabled.

### 4 — Prove complete build and test quality

Create repeatable offline build scripts and test artifacts for the selected implementation:

- Host native compilation; target **AArch64 Linux** compilation; `readelf` architecture/interpreter/NEEDED checks against the actual Nuxel rootfs.
- Verified 28-byte packed ABI, numeric ioctl set, expected enums and meaningful type assertions.
- Mock backend **must not** use real `/dev/umts_*`, `/dev/sda*`, RF or system services.
- Source-derived golden stage sequence including firmware read/parser, actual MAIN framing, verified responses, boot-off, and final status `ONLINE` in the simulator.
- Negative tests: invalid ITOC; swapped stage entries; corrupt section CRC; wrong family/board; bounds overflow; user pointer invalid; partial/short reads; stale reply; wrong SIPC channel; truncation; no status transition; TEE failure; kernel timeout; daemon race; lock already held; signal interruption; subsystem crash; user abort; unreachable endpoint; no recovery route; no network service.
- Confirm no test fixture or mock CP ONLINE can be mistaken for physical ONLINE in reports or diagnostics.
- Test **release** and **hardware-compiled** variants offline, especially that no-op stage paths and success-on-failure are impossible. For the hardware-compiled binary, use fake kernel/device operations only; never run it against the phone this round.
- Add sanitizer/fuzzer/static analyzer coverage where available, with bounded time and resource caps.
- Verify systemd manual-only service (`Restart=no`, no timer/autostart, hard `TimeoutStartSec`, privilege limitation as practical) and uninstall/rollback receipts; do not enable or start its physical mode.

**ZIP portability issues to fix:** `test_kernel_header_crosscheck.py` expects a host-generated kernel path not bundled in ZIP; explicitly require genuine checkout and pinned SHA, or honestly skip with a reason instead of false PASS. `test_s5000ap_uapi.py` calls `pytest.skip` but only imports `pytest` under `__main__`, producing `NameError` when cross-compiler is absent. Remove duplicate definitions in `test_kernel_header_crosscheck.py`. Re-run 22 firmware fixtures and 21 UAPI tests plus new full-loader tests. Archive real receipts with code SHAs.

### 5 — Reconcile operational policy and stale documentation

- Update root `mobile.md`: the originally documented DTK9 `.tar.md5` was **not** present in subsequent host searches. Do not leave the false "archive found" assertion as live truth.
- Produce a **new** immutable `reports/S5000AP-04-PHYSICAL-CP-BOOT-PROPOSAL.md` selecting **EFUJ2** as read-only source. Do not merely prepend a revision header to the stale 03.5 proposal containing DTK9 section sizes and DTK9 provenance demands.
- Reconcile `configs/nuxel/modem/modem.json` describing `radio` as `never_read_or_write` while authoritative source selection requires **bounded, approved read-only** RADIO input. Retain **absolute write prohibition**.
- Mark the 04 NO-GO record as historically correct but superseded in its claims that `-t ss310`/RADIO identity are unknown after round 03.6.
- Avoid reclassifying missing DTK9 `.tar.md5` as a blocker for the installed EFUJ2 execution path without actual evidence.
- Correct any overconfident `MISMATCH_EXPLAINED_AND_COMPATIBLE` language: device model match is not proof of exact origin/cryptographic signature acceptance.
- Scoped commits only; no private firmware blobs, SIM identifiers, partition dumps or keys in public Git.

### 6 — Fresh read-only recovery and physical prerequisites

Use Nuxel normal boot, **not TWRP**. Read-only verify model, current CP OFFLINE, actual GPT partition labels, BOOT/DTB/DTBO/recovery hashes, known-good independent host backups and hashes, Wi-Fi+SSH, USB/TWRP fallback, no competing CBD/RIL, no kernel modem faults, and exact firmware source identity. Previous live hashes are baseline, not fresh truth.

Historically reported:
- BOOT `1be1ded89f9e04a6a2ca0d32d9273bd363c2e200f478ab10213ea3927674a599`
- DTB `abc9d45d3745866346fd94c7c04028cc2c62ade4dd274b400dbbfec0c2ef4780`
- DTBO `de3bc02526c66647992a744608fdf61548823866e822a7400619d74126095c23`
- RECOVERY `4cc71d6277e020cdec729b85934cfb6111e9abee8db2fbcc344aad3173335d87`

Verify the most recent known-good image remains recoverable independently even if SSH fails. No new BOOT flash, DT modification, reboot or CP-changing action is needed for this preparation.

### 7 — Write one exact Stage 04 proposal and acceptance matrix

Produce a comprehensive owner-readable manifest with:

1. Exact commit/dirty files and build source revisions.
2. Physical device model/revision, running BOOT/DTB/DTBO/recovery hashes and the trusted recovery files.
3. Explicit EFUJ2 firmware source identity (GPT label + partition size + full SHA256 + ITOC structure + EFUJ2 section table), provenance level and residual hardware-only TEE acceptance uncertainty.
4. Exact native executable hash, reproducible build and dependencies, hardware-disabled default.
5. Exact canonical stage order based on pinned matching Samsung source: source function and target kernel handler, operation category, verified structure/section, expected result/state, deadline, abort condition and redacted observation for EVERY stage.
6. Demonstrated end-to-end mock transcript with trace equivalence and no unimplemented or silently skipped stages.
7. One-shot service and exclusive owner; Wi-Fi/USB preservation; no SIM required for first CP ONLINE proof; RF/network activity not assumed or claimed.
8. Verifiable PASS: **real** `IOCTL_MODEM_STATUS` transitions to stable ONLINE with kernel confirms; standalone daemon activity/`rmnet` existence does not count.
9. Abort on TEE refusal/error/unexpected state, with process disabled, evidence preserved and zero automatic retry/power cycling. No protected writes.
10. Recovery paths, no DTB/DTBO changes, clear boundary between CP boot and later SIPC/RFS/LTE work.
11. Concise exact owner-approval clause for **that manifest only**, NOT an open-ended hardware permission request.

Report gate verdicts independently:

| Gate | PASS criterion |
|---|---|
| A | EFUJ2 source identity + structural validation + defensible provenance/risk characterization, no wrong-family firmware |
| B | Kernel ABI and controller match pinned source/live kernel |
| C | **Complete**, source-faithful, tested physical-capable native bootstrap binary; no stub/no-op stage |
| D | End-to-end offline simulator, negative/safety, target build and dependency checks all pass |
| E | Fresh device recovery and connectivity preflight passed |
| F | Exact manifest issued; physical authorization remains a separate owner decision |

Declare `READY_FOR_04_OWNER_REVIEW` ONLY if A–E genuinely pass. Declare `BLOCKED_...` with exact evidence otherwise. Do not use `AUTHORIZED_FOR_04` in this prep round, and **do not execute Stage 04 now**.

### 8 — Mandatory work style, delegation, and final response

Lead: **Pro Thinking** performs protocol reconstruction, safety-critical implementation review, signature/provenance verdict, architecture choice, and final QA. Delegate to **Flash Thinking**: A) EFUJ2 read-only metadata hashing/analyzer fixtures, B) pinned source/API cross-checks, C) test harness/fuzzer/CI, D) build/dependency script, E) document/test drift. Do **not** delegate physical CP actions; none are authorized in this round. Pro Non-Thinking may handle purely mechanical formatting after an approved technical design, not the boot transaction.

DO NOT STOP EARLY at the first failing test or absent archive. Fix every safe, agent-resolvable issue, execute the tests, and commit only reviewed work. If genuinely blocked by unavailable OEM authenticity evidence or missing hardware access, state it precisely with a minimal next action and do not fake readiness. Do not promise future work; perform all feasible work now.

**Deliverables:**

- `reports/S5000AP-03_7-EFUJ2-SOURCE-AND-PROVENANCE.md`
- `reports/S5000AP-03_7-BOOT-PROTOCOL-CALLGRAPH.md`
- `reports/S5000AP-03_7-BOOTSTRAP-CODE-REVIEW.md`
- `reports/S5000AP-03_7-BUILD-AND-TEST-RECEIPT.md`
- `reports/S5000AP-03_7-LIVE-SAFETY-PREFLIGHT.md`
- `reports/S5000AP-04-PHYSICAL-CP-BOOT-PROPOSAL.md`
- Complete focused source/test/dependency/CI changes and scoped Git commits.

**Final reply (not just 'done'):** HEAD/branch/worktree, firmware source and full SHA, provenance/evidence classification, verified EFUJ2 section table, source-to-loader mapping, architecture decision, code diff, target binary SHA, complete offline tests (including warnings/skips), fresh versus historical hardware evidence, recovery status, A–F gate matrix, exact unresolved blockers, whether the physical Prompt 04 may now be presented for approval, and exact path to the new proposal.

**START STAGE-04 CLEARANCE WORK NOW. NO PHYSICAL CP BOOT DURING THIS ROUND.**
