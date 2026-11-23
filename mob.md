√# NUXEL — STAGE 04: FINAL EXECUTION DIRECTIVE
## Resolve the Remaining Blockers, Deploy the Bootstrap, and Complete the Controlled Physical Trial

**Lead agent:** DeepSeek Pro Thinking  
**Device:** Samsung Galaxy S10+ SM-G975F / beyond2lte / Exynos9820 / S5000AP  
**Branch:** `cs/mob`  
**Starting commit:** `d8d772c4`  
**Execution environment:** Normally booted Nuxel  
**TWRP flashing:** NOT AUTHORIZED

# MISSION

The engineering preparation phase is over.

The objective is to complete Stage 04 and establish a physically verified, stable CP ONLINE state.

Do not launch another broad research phase.

Do not spend the session rewriting readiness reports.

Do not stop for routine development approvals.

Do not treat a fixable software problem as a reason to abandon the mission.

**Fix, build, test, deploy, verify, and advance.**

The only mandatory physical-activation authorization is approval of the exact final trial manifest.

Obtain that decision once, within this execution session. Do not terminate the agent merely because approval was absent at startup.

---

# 1. EXISTING ENGINEERING BASELINE

Round 04 engineering work has already produced:

Commit:

`d8d772c4`

Hardware executable:

`tools/s10plus/s5000ap-uapi/nuxel-cpbootd.aarch64.hw`

SHA-256:

`2b630d4a8c7219c468a4aff94881029b23547d867f4f5a30898f080f2cb4fae7`

Reported test results:

- 31 UAPI tests passing.
- 22 firmware tests passing.
- Flash preflight passing.
- AArch64/glibc executable built successfully.
- Mock bootstrap reaches ONLINE.

Implemented corrections reportedly include:

- `CP_MEMORY_MASK` firmware mapping.
- TOC-first firmware transmission.
- TOC security-request parameters.
- Correct ITOC parsing.
- NV section exclusion.
- OFFLINE reset handling.

Treat these as existing implementation results.

Do not repeat previous work unless new evidence demonstrates a defect.

---

# 2. IMMEDIATE EXECUTION PRIORITIES

Work in this order:

1. Reconcile the current firmware source with the actual device.
2. Verify that the hardware executable matches the pinned CBD implementation.
3. Fix any remaining demonstrable implementation defects.
4. Build the final executable.
5. Complete the required targeted tests.
6. Deploy reversible userspace components.
7. Obtain exact approval for the physical operation.
8. Execute the single controlled trial.
9. Verify the physical CP state.
10. Record the outcome.

Do not replace implementation work with another proposal-writing exercise.

---

# 3. RESOLVE THE FIRMWARE SOURCE DISCREPANCY

Previous investigations identified:

- DTK9 firmware candidate used by offline tests.
- EFUJ2 firmware reportedly installed in the physical RADIO partition.

Determine which exact firmware source the current approved proposal specifies.

Verify the selected image against the device's identity, firmware metadata, expected bootloader protocol and available authenticity evidence.

Do not assume that passing mock tests against DTK9 proves the EFUJ2 physical path.

If the actual source differs from the tested source, update the relevant test fixtures and validate the correct image.

Do not alter signed firmware, substitute an unrelated image or bypass authentication.

If provenance cannot be established sufficiently, identify the precise missing evidence rather than guessing.

---

# 4. CLOSE REMAINING BOOTSTRAP DEFECTS

Inspect the real hardware-enabled code.

Resolve all reproducible implementation defects, including any involving:

- Firmware section mapping.
- Firmware source offsets.
- Security-request parameters.
- Reset preconditions.
- Modem state handling.
- Error propagation.
- Timeouts.
- Exclusive device ownership.
- False ONLINE reporting.

The recent addition of `IOCTL_MODEM_RESET` requires particular attention.

Confirm that its use is consistent with the pinned CBD source and that it cannot trigger an uncontrolled reset loop.

Do not invoke reset, power or firmware-load operations merely to diagnose an uncertain implementation.

Use offline evidence and targeted tests first.

For each verified defect:

**FIX → BUILD → TEST → CONTINUE**

Do not ask the owner to approve ordinary source changes or offline testing.

---

# 5. OWNER AUTHORIZATION FOR SAFE ENGINEERING

The owner authorizes, without further confirmation:

- Source modifications.
- Reproducible builds.
- Offline firmware analysis.
- Mocked boot tests.
- Read-only device inspection.
- Read-only kernel and modem diagnostics.
- Reversible userspace deployment.
- Service configuration with automatic CP activation disabled.
- Test and documentation updates.
- Safe cleanup of temporary development artifacts.

Preserve working access and existing recovery assets.

No TWRP flashing is authorized.

No BOOT, DTB, DTBO, RADIO, EFS, NV, calibration, IMEI or bootloader modifications are authorized.

No signature-enforcement bypass is authorized.

---

# 6. PHYSICAL TRIAL AUTHORIZATION — SINGLE DECISION

Use:

`reports/S5000AP-04-PHYSICAL-CP-BOOT-PROPOSAL.md`

Prepare the exact physical operation for approval.

The approval record must identify:

- Device identity.
- Complete firmware SHA-256.
- Complete executable SHA-256.
- Exact operation sequence.
- Whether a modem reset is included.
- Maximum execution duration.
- Abort conditions.
- Recovery procedure.
- Protected-partition exclusions.

Present this exact record to the owner once.

**Do not stop the entire execution session merely because approval is required.**

Wait for the owner's explicit decision.

Once approval is granted for the unchanged manifest, continue directly into the controlled Stage 04 trial without requiring another prompt or another approval round.

If the manifest changes materially, obtain approval for the revised version.

General authorization to finish the project is not a substitute for approval of an unidentified hardware operation.

---

# 7. EXECUTE STAGE 04

After the exact trial is approved and all required safeguards are satisfied:

Run the controlled physical CP boot on normally booted Nuxel.

Execute only the approved operation sequence.

Observe the actual kernel-reported CP state.

A successful process exit or mocked ONLINE response does not establish physical success.

Success requires a genuine stable CP ONLINE state corroborated by real device evidence.

Stop physical activation on:

- Unexpected ioctl failure.
- Firmware authentication failure.
- Unexpected modem state.
- Kernel fault.
- Hardware timeout.
- Abnormal power or thermal behavior.
- Loss of the required recovery capability.

Do not automatically retry the physical operation with alternate firmware, offsets, security parameters or reset sequences.

---

# 8. HANDLE FAILURES WITHOUT ABANDONING ENGINEERING

For software defects:

Fix, rebuild and retest automatically.

For reversible deployment failures:

Diagnose, correct and redeploy safely.

For physical trial failures:

Stop the physical operation, preserve evidence and investigate offline.

Continue correcting independently verifiable software defects.

If another physical attempt is justified, prepare the revised exact trial for owner approval.

Do not repeatedly power-cycle the modem in pursuit of ONLINE.

Do not enter TWRP or flash anything.

If TWRP becomes necessary, report the exact condition and stop before recovery flashing.

---

# 9. MINIMAL REPORTING

Update the existing:

`reports/S5000AP-04-CP-BOOT-LIVE.md`

Include:

- Final Git commit.
- Exact firmware and executable hashes.
- Software fixes.
- Test results.
- Deployment result.
- Owner approval reference.
- Actual physical operations performed.
- Actual CP state.
- First failure, if any.
- Protected-partition-write attestation.

Avoid duplicate documentation.

Do not claim Stage 04 success without physical evidence.

---

# 10. FINAL SUCCESS CONDITION

Return:

`STAGE_04_PHYSICAL_SUCCESS`

Only if:

1. The exact physical operation was approved.
2. The actual hardware bootstrap executed.
3. The kernel reports CP ONLINE.
4. ONLINE remains stable.
5. No unexpected hardware or security failure occurred.
6. Nuxel remains operational.
7. No protected-partition writes occurred.

Otherwise report the precise blocker or failure.

**Execute every authorized engineering action necessary to reach the physical trial. Do not stop for redundant approvals, routine fixes or repeated planning. Preserve the single-trial and hardware-safety boundaries.**

BEGIN EXECUTION.
