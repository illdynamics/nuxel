# NUXEL — PROMPT 03.6
## S5000AP Firmware Provenance Recovery & CP Boot Clearance

**Execution model:** DeepSeek V4 Pro Thinking
**Delegation:** Flash Thinking for read-only discovery, hashing, comparison and offline tests
**Target:** Samsung Galaxy S10+ SM-G975F / beyond2lte / Exynos9820 / S5000AP
**Current branch:** `cs/mob` — verify actual HEAD
**Mission:** Resolve the firmware provenance, CL/QB, CBD type-string and installed-RADIO identity blockers so that Prompt 04 can be safely presented for owner approval.

---

## 0. PRIMARY OBJECTIVE

Prompt 04 was correctly stopped with:

- `CP_BOOT_NOT_AUTHORIZED`
- `FIRMWARE_PROVENANCE_UNKNOWN`

The last verified physical CP state is `OFFLINE (0)`.

Our objective is to eliminate all technically resolvable blockers and establish a trustworthy, compatible CP firmware source for this exact handset.

**Do not attempt to boot the CP during this round.**

Do not interpret this prompt as authorization for a physical CP trial.

The desired final state is:

`FIRMWARE_PROVENANCE_RESOLVED`
+
`INSTALLED_RADIO_IDENTITY_VERIFIED`
+
`CBD_TYPE_STRING_VERIFIED`
+
`BOOTSTRAP_SOURCE_COMPATIBILITY_VERIFIED`
+
`RECOVERY_PREFLIGHT_PASS`
=
`READY_FOR_04_OWNER_APPROVAL`

If any required evidence cannot be obtained, identify the exact missing item and the smallest legitimate owner action necessary to obtain it.

Do not fabricate evidence or silently downgrade acceptance criteria.

---

## 1. READ AND RECONCILE ALL EXISTING EVIDENCE

Inspect the actual repository and existing private workspace.

Read:

- `pwn-mob/00_MASTER_SAFETY_AND_TRUTH.md`
- `pwn-mob/02_CP_FIRMWARE_VALIDATION.md`
- `pwn-mob/03_CBD_ABI_AND_OFFLINE_BUILD.md`
- `pwn-mob/04_CP_BOOT_CONTROLLED_TRIAL.md`
- `pwn-mob/09_TWRP_A_ONLY_RECOVERY_AGREEMENT.md`
- `reports/S5000AP-02-CP-FIRMWARE-IDENTITY.md`
- `reports/S5000AP-03-BOOT-CONTRACT-ABI.md`
- `reports/S5000AP-03-BUILD-RECEIPT.md`
- `reports/S5000AP-03_5-FIRMWARE-PROVENANCE.md`
- `reports/S5000AP-03_5-CBD-RUNTIME-DECISION.md`
- `reports/S5000AP-03_5-CP-FIRST-BOOT-PROPOSAL.md`
- `reports/S5000AP-04-CP-BOOT-LIVE.md`
- Root `mobile.md`

Inspect actual filenames if any differ.

Do not trust historical report conclusions without checking their supporting evidence.

Reconcile the current branch, commit, uncommitted changes and private firmware artifacts.

Preserve unrelated changes and do not commit proprietary firmware.

---

## 2. RECONSTRUCT THE EXACT FIRMWARE CHAIN OF CUSTODY

Previously reported derived workspace:

`/Users/wicked/.local/share/nuxel-s5000ap/G975FXXS9DTK9-CP-20261117`

Primary candidate:

`modem.bin`

Expected SHA-256:

`1e4280d26de704281c01ddf59407fbfdfb714d3f87a55b780f6f74d1ab0e7881`

Reported characteristics:

- Size: 46,062,992 bytes
- S5000AP ITOC container
- BOOT, MAIN and VSS CRC32 checks pass
- Model metadata: `SM-G975F_EUR_XX_EUR0`
- Firmware family: `G975FXXS9DTK9`
- Embedded CL/QB: `CL1535157 / QB17435920`

Documented missing archive:

`CP_G975FXXS9DTK9_CP17435927_CL20034833_QB35905779_REV01_user_low_ship.tar.md5`

Investigate all available owner-controlled sources of provenance, including:

1. Original extraction logs and commands.
2. Download receipts, source URLs and recorded hashes.
3. Existing backup manifests.
4. Local firmware package inventories.
5. Git history and previous engineering reports.
6. Immutable copies or archives in authorized owner workspaces.
7. Trusted official or otherwise independently verifiable firmware records.

Determine whether the derived image can be tied to an authentic, model-compatible Samsung firmware release.

Distinguish:

- Filename identity
- Package identity
- Internal modem build identity
- Cryptographic integrity
- Source authenticity
- Device compatibility
- Actual secure-boot acceptance

A matching filename, CRC32 or SHA-256 of an unknown-origin file is insufficient to prove authenticity.

Do not fetch random firmware, alter signed images or bypass verification.

---

## 3. RESOLVE THE CL/QB MISMATCH

Investigate why:

**Documented package:**

`CL20034833 / QB35905779`

**Embedded modem image:**

`CL1535157 / QB17435920`

Both appear associated with the DTK9 firmware family, but equivalence is not established.

Determine whether these identifiers belong to different build namespaces, components, release stages or genuinely different firmware variants.

Use source-backed evidence, not assumptions.

Compare:

- Samsung firmware package naming conventions.
- CP build identifiers versus AP/PDA build identifiers.
- Existing package manifests.
- Original extraction records.
- Image metadata.
- Bootloader compatibility constraints.
- Matching firmware releases for SM-G975F.
- Trusted source records, where available.

Provide an evidence table showing which identity fields must match and which may legitimately differ.

Do not require literal CL/QB equality if trustworthy evidence establishes that the fields describe different components.

Equally, do not dismiss a mismatch merely because the DTK9 label matches.

Final verdict must be one of:

- `MISMATCH_EXPLAINED_AND_COMPATIBLE`
- `MISMATCH_GENUINE_INCOMPATIBILITY`
- `MISMATCH_UNRESOLVED`

---

## 4. VERIFY THE INSTALLED RADIO PARTITION — READ ONLY

If the handset is reachable, perform bounded, authorized read-only inspection.

Confirm the physical device identity and verify the partition mapping using the actual device's evidence.

Establish:

- Exact RADIO partition identity and size.
- Whether the partition contains a valid S5000AP firmware image.
- Its container structure and metadata.
- Its relevant build identifiers.
- Whether it matches the derived candidate.
- Whether its origin can be independently established.
- Whether stock CBD expects to read it directly.

Use minimal reads and metadata where possible.

Do not make a complete partition copy unless explicitly authorized and necessary.

Do not modify the partition.

**Forbidden:**

- RADIO writes
- MODEM/CP writes
- EFS/NV writes
- Partition repair or replacement
- Bootloader changes
- Secure-boot bypasses
- IMEI or calibration changes

If the RADIO partition cannot be inspected, report the reason and the exact missing evidence.

Never assume an existing partition image is compatible simply because it is installed.

---

## 5. VERIFY THE SAMSUNG CBD TYPE STRING

The existing first-boot proposal has an unresolved `-t` type-string question.

Investigate the exact Samsung `cbd` implementation and its supported options.

Compare the pinned source, stock executable, original device configuration and target kernel.

Determine:

1. What the `-t` argument selects.
2. Which type is correct for SM-G975F / Exynos9820 / S5000AP.
3. Whether `ss310` is actually correct for this hardware and firmware.
4. Whether type selection affects memory mapping, boot protocol, firmware source or secure verification.
5. Whether the selected executable is compatible with the historical kernel ABI.

Use source and binary evidence.

Do not experimentally invoke modem boot or power ioctls to discover the correct type.

If a definitive type cannot be established, mark this gate BLOCKED rather than guessing.

---

## 6. CLOSE THE BOOTSTRAP RUNTIME GAP

Round 03 established that stock Samsung CBD is Bionic-linked and a newly compiled glibc `cpboot_v3` is not automatically a drop-in replacement.

Review the actual Prompt 03.5 runtime decision.

Determine whether a compatible bootstrap execution path is now available.

Verify:

- Exact executable identity and SHA-256.
- ELF architecture and interpreter.
- Required shared libraries.
- Runtime isolation.
- Kernel ABI compatibility.
- Firmware source compatibility.
- Service permissions.
- Device-node access.
- Error handling.
- Timeouts.
- Recovery behavior.
- Whether all required operations are backed by matching source evidence.

If a compatibility runtime is needed, implement and test it offline without introducing Android framework services into Nuxel.

Do not claim readiness merely because the executable starts or a dry-run passes.

If no trustworthy executable boot path exists, identify that as a separate blocker.

---

## 7. CHECK CRYPTOGRAPHIC AND SECURE-BOOT REQUIREMENTS

Determine what can actually be verified before physical CP boot.

Inspect available trusted metadata and source to establish:

- Expected image signing/container scheme.
- Which component performs signature verification.
- Whether firmware authentication occurs in CBD, kernel, secure monitor or modem boot ROM.
- Whether a trusted authenticity reference is available.
- Whether the proposed source is consistent with the device's secure-boot expectations.

Do not claim cryptographic verification from CRC32 checks, a container parser or a successful decompression.

If device-side acceptance can only be demonstrated during an authorized physical boot, document it as a residual hardware-only uncertainty.

Do not bypass, disable or modify signature enforcement.

---

## 8. VERIFY THE CURRENT RECOVERY BASELINE

Before recommending Prompt 04, refresh the required read-only safety evidence.

Verify:

- Physical SM-G975F identity.
- Current running Nuxel kernel.
- Current BOOT and DT identity.
- Existing DTBO identity where available.
- Known-good BOOT backups.
- Backup hashes and readability.
- Recovery access.
- Wi-Fi and SSH health.
- USB access.
- Current read-only CP status.
- No competing CBD/RIL owner.
- No unexpected modem-related kernel faults.

Use existing verified recovery procedures.

Do not flash, reboot or change partitions.

Do not modify DTS, DTB or DTBO.

If current recovery evidence cannot be refreshed, record the exact missing preflight item.

---

## 9. IMPLEMENT ALL SAFE CORRECTIONS

Where evidence reveals a fixable issue, make the smallest appropriate correction.

Examples:

- Incorrect firmware filename in documentation.
- Incorrect package-versus-component build comparison.
- Incorrect CBD type-string assumption.
- Incorrect firmware-source path.
- Missing provenance manifest.
- Incorrect bootstrap dependency.
- Outdated first-boot proposal.
- Incomplete offline test.
- Incorrectly classified firmware validation gate.

Do not modify signed firmware to make metadata match.

Do not silently replace the candidate with an unrelated build.

Do not install or activate the modem bootstrap.

All changes must be reproducible, tested and supported by evidence.

Preserve existing user work.

---

## 10. REQUIRED DELIVERABLES

Create or update:

`reports/S5000AP-03_6-FIRMWARE-PROVENANCE-RESOLUTION.md`

`reports/S5000AP-03_6-CL-QB-IDENTITY-ANALYSIS.md`

`reports/S5000AP-03_6-INSTALLED-RADIO-IDENTITY.md`

`reports/S5000AP-03_6-CBD-TYPE-STRING-VERIFICATION.md`

`reports/S5000AP-03_6-BOOTSTRAP-RUNTIME-CLEARANCE.md`

`reports/S5000AP-03_6-PHYSICAL-BOOT-READINESS.md`

Update:

`reports/S5000AP-03_5-CP-FIRST-BOOT-PROPOSAL.md`

Preserve the previous proposal's history and document every material change.

Include source references, artifact hashes, test receipts and confidence levels.

Keep proprietary firmware and sensitive information outside public Git.

---

## 11. ACCEPTANCE MATRIX

Return a verdict for each gate:

| Gate | Acceptance requirement |
|---|---|
| A1 | Firmware source provenance established |
| A2 | CL/QB discrepancy explained or resolved |
| A3 | Firmware compatible with physical device |
| A4 | Installed RADIO identity established |
| A5 | Secure-boot requirements understood |
| B | Kernel ABI verified |
| C1 | CBD type-string verified |
| C2 | Compatible bootstrap executable available |
| C3 | Firmware source contract verified |
| D | Offline tests passing |
| E | Current recovery preflight passing |
| F | Explicit owner approval pending |

For each item, report:

- PASS / FAIL / BLOCKED / UNKNOWN
- Exact evidence
- Remaining uncertainty
- Smallest next action
- Whether owner intervention is necessary

### Final status rules

**READY_FOR_04_OWNER_APPROVAL**

All technical and recovery prerequisites are satisfied. The exact trial proposal is ready for review. Owner approval is still required.

**BLOCKED_FIRMWARE**

Firmware identity, provenance or compatibility cannot be sufficiently established.

**BLOCKED_BOOTSTRAP**

No verified compatible CBD execution path exists.

**BLOCKED_RECOVERY**

Current recovery prerequisites cannot be demonstrated.

**AUTHORIZED_FOR_04**

This status is forbidden in Prompt 03.6. It may only be established after separate explicit owner approval of the exact reviewed trial.

---

## 12. EXECUTION RULES

Work autonomously through every safe, read-only or offline investigation.

Delegate bounded mechanical tasks to Flash Thinking.

Do not stop at the first ambiguous filename.

Investigate the underlying provenance and component identity.

Do not treat missing evidence as permission to weaken a gate.

Do not fabricate success.

Do not perform physical CP boot, power, load or reset operations.

Do not energize RF.

Do not flash BOOT, DTB, DTBO, RADIO or any protected partition.

Do not alter secure-boot enforcement.

Do not proceed automatically to Prompt 04.

If a genuine blocker remains, return the precise owner input required and why it cannot be obtained safely by the agent.

---

## 13. FINAL MANDATORY RESPONSE

Return:

1. Git HEAD, branch and worktree status.
2. Firmware source and SHA-256.
3. Provenance chain and evidence.
4. CL/QB mismatch verdict.
5. Installed RADIO identity verdict.
6. CBD type-string verdict.
7. Bootstrap runtime verdict.
8. Secure-boot compatibility assessment.
9. Current recovery readiness.
10. All tests executed and results.
11. Source and report changes.
12. Complete GO/NO-GO matrix.
13. Exact remaining blockers.
14. Exact updated first-boot proposal path.
15. Final `READY_FOR_04_OWNER_APPROVAL` or blocked status.

**Do not stop until all safely resolvable issues are addressed and documented.**

**Never substitute assumptions for evidence or cross the physical CP activation boundary.**

START PROMPT 03.6 NOW.
