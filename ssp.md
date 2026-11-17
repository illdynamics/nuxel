connect to Nuxel over ssh use key ~wicked/.ssh/wicked_wqn_id_rsa to connect to Nuxel, use root user and IP 10.11.12.99

# NUXEL S10+ — SSP/BCM47752 FINAL RECOVERY MISSION

## PRIMARY OBJECTIVE

You are the lead kernel, firmware, reverse-engineering and Linux systems engineer responsible for restoring the Samsung Galaxy S10+ (SM-G975F, Exynos9820) BCM47752 sensor hub under Nuxel.

**Your ultimate objective is genuine, physically verified accelerometer and gyroscope streaming, followed by fully functional automatic screen rotation.**

Do not declare success based on tests, process startup, device nodes, fake readings, successful compilation, or an incomplete handshake.

Continue independently through successive research, implementation, verification and debugging stages. Do not stop at a research summary when further safe engineering work is possible.

Do not attempt to force the result through undocumented firmware transactions, guessed hardware sequencing or unrestricted flashing. Stop for explicit authorization whenever a live hardware-changing operation is necessary.

## 1. PROJECT AND CURRENT STATE

Repository:

`/Users/wicked/x/nuxel`

Branch:

`feat/ssp`

Latest known commit:

`6bcbcea6`

Authoritative report:

`reports/SSP-PROTOCOL-CONTRACT-2026-11-17.md`

Also read:

- `reports/SSP-STOCK-RUNTIME-2026-11-17.md`
- The existing first-light and SSP recovery reports
- All associated evidence directories
- `tools/s10plus/ssp-runtime/inspect_lhd_init.py`
- The native BBD downloader and its tests
- The existing kernel SSP, BBD, SPI and RPC implementations
- The existing orientation daemon

Reconcile actual Git HEAD before editing.

Preserve all previous work, commits, firmware artifacts, hardware evidence and unrelated functionality.

## 2. WHAT HAS ALREADY BEEN SOLVED

Do not waste another entire session repeating completed investigations.

Verified accomplishments include:

- Exact matched Samsung Android 10 runtime recovered.
- All four stock vendor anchors matched.
- Android dynamic linker and VNDK dependencies resolved.
- Original Samsung `lhd` executes in hardware-denied isolation.
- Transport framing, escaping and CRC are substantially validated.
- Unrelated packets are no longer accepted as operation completion.
- Premature Python `ESW:READY` emission has been eliminated.
- Packet ACK versus reliable ACK/NACK distinctions established.
- Multiple firmware-initialization states identified from the matched daemon.
- The isolated AF_INET permission issue explained.
- Native and AArch64 host simulations passing.
- No successful physical MCU startup yet.

Do not download another generic Samsung runtime unless new compatibility evidence requires it.

The original matched vendor binary and stock runtime remain the preferred implementation.

## 3. NEW DISCOVERY — CALLBACK SIDE EFFECTS

Commit `6bcbcea6` established critical new static evidence.

Matched `lhd` binary SHA-256:

`6362e80d1f2ae37c76dd5f468bf08abacb89e1c2d2b80976d5b1c3abbf761dfe`

Normal version callback:

`0x39b9c`

Extended version callback:

`0x39d08`

Expected initialization transitions:

- State 8 → 9
- State 15 → 16

Both callbacks modify internal metadata before testing the expected state.

The owner object's pointer member at offset 24 provides access to:

- Offset 2320: argument w1
- Offset 2324: argument w2
- Offset 2328: argument w3
- Offset 2332: conditional assignment from w2 when previous value is `0xffffffff`

The normal callback also writes w1 through pointer member offset 32 to field offset 18832.

Associated adjustor thunks:

- `0x39d00`
- `0x39e64`

**Critical implication:** an unexpected-state callback may change internal metadata without advancing the initialization state.

This does not establish that arbitrary incoming wire data reaches the callback.

Your next job is to determine the validated decoding and dispatch path that invokes these callbacks.

## 4. RECONSTRUCT THE COMPLETE RESPONSE PATH

Prioritize backward and forward control-flow analysis around the verified callbacks.

For every invocation path, determine:

- Which function invokes the callback.
- Which virtual interface or dispatch table owns it.
- The exact validated message type.
- How arguments w1, w2 and w3 are decoded.
- Whether bytes originate from an internal transport packet, RPC message, ROM response or application response.
- What checks occur before dispatch.
- How message length, CRC, sequence and session identity are validated.
- Whether delayed or duplicated responses can reach the callback.
- Whether unexpected-state responses leave persistent metadata changes.
- What must happen for the next state transition.
- How timeout, cancellation and failure paths behave.

Trace the path back toward the actual transport decoder and forward toward the next initialization state.

Do not infer protocol command identifiers from ELF virtual addresses or callback relocations.

Produce evidence-backed call graphs, annotated disassembly, pseudocode and testable invariants.

Every reconstructed protocol element must include its evidence source and confidence classification.

Use the exact matched binary; retain the existing SHA-256 guard.

## 5. COMPLETE THE FIRMWARE OPERATION CONTRACT

Investigate the original Samsung daemon's initialization sequence, including:

- Download requests
- Autobaud and internal synchronization
- Initial ROM identification
- Firmware patch selection
- Firmware validation
- Memory-write operations
- Scratch-application versus service-application paths
- Download completion
- Application startup
- Confirmation synchronization
- Final version verification
- MCU-ready notification
- Abort, reset and retry behavior

Determine which operations are actual host-to-device requests and which are internal daemon states.

Distinguish transport acknowledgement, reliable transport acknowledgement and actual firmware-operation completion.

A transport ACK must never be treated as proof of successful firmware execution.

Identify how the original implementation validates the final response and advances to DONE.

Determine timer units and failure behavior from evidence rather than assuming that constants such as 100 or 250 are milliseconds.

Prioritize analysis of the existing matched implementation over writing an independent downloader.

## 6. RESEARCH EXISTING IMPLEMENTATIONS FIRST

Continue targeted research of Samsung and Broadcom implementations, especially:

- Exynos9820 Samsung downstream kernel history
- BCM47752-specific BBD integrations
- Related Broadcom BBD transports
- Samsung `lhd` implementations and compatible vendor configurations
- Existing firmware-loading interfaces
- Available public source archives and kernel patches

Reuse compatible upstream implementations where their behavior is supported by device-specific evidence.

Code for different Broadcom chips may clarify architecture but must not be treated as authoritative for this BCM47752 ROM.

Record exact source URLs, revisions, hashes, licenses, differences and applicability.

Do not replace the working kernel transport because a newer generic implementation exists.

If trustworthy source is unavailable, continue evidence-driven analysis of the already recovered binary.

## 7. IMPLEMENT MISSING OFFLINE ENGINEERING TOOLS

Write actual code whenever it can close a demonstrated gap.

Potential useful deliverables include:

- An expanded hash-bound daemon call-graph inspector.
- A decoder-to-callback mapping tool.
- A deterministic internal-message replay harness.
- A model of the verified initialization state transitions.
- A strict operation-completion validator.
- Tests for stale, duplicated, truncated, reordered and malformed responses.
- State mutation and callback-order regression tests.
- A mock BBD endpoint backed only by verified fixture data.
- A transcript comparator for independently obtained reference traces.
- A source-linked protocol evidence inventory.

Prefer extending existing repository tools rather than introducing redundant frameworks.

Every implementation must be compiled or executed and tested.

Use sanitizers, fuzzing or property-based tests where appropriate.

Never invent expected firmware responses to make tests pass.

Synthetic test cases are permitted for validating rejection and parser invariants, but must be clearly marked as synthetic.

## 8. CLOSE THE REMAINING HARDWARE-SAFETY GAPS

Before designing any physical initialization trial, analyze:

- `/dev/ttyBCM` ownership and open side effects
- `/dev/bbd_control`
- `/dev/bbd_patch`
- `/dev/bbd_sensor`
- `/sys/bbd/lk_enable`
- MCU power-control interfaces
- Kernel watchdog behavior
- Existing reset and regulator fallback logic
- Competing native and Samsung daemon ownership
- Firmware write boundaries
- Timeout and abort behavior

Account for the fact that opening the transport can change device state.

Do not expose unrestricted host `/sys`, GPIO controls, reset interfaces or the live BBD device merely to make `lhd` progress beyond its existing sandbox assertion.

Construct and validate an explicit device-specific recovery plan before proposing any hardware-changing action.

That plan must address loss of SSH, daemon crashes, watchdog activity, persistent MCU state and restoration of Nuxel bootability.

A process exit is not proof that firmware or power state has been restored.

## 9. PHYSICAL FIRST-LIGHT TRIAL — APPROVAL REQUIRED

Only when an actual end-to-end protocol contract and recovery strategy are supported by sufficient evidence should you prepare a live hardware trial.

Before execution, present:

1. Exact operations requiring approval.
2. Expected device-state changes.
3. Verified response and completion criteria.
4. Hardware and software prerequisites.
5. Failure detection and abort criteria.
6. Bounded execution limits.
7. Confirmed recovery mechanism.
8. Files and artifacts that will be modified.
9. Reasons the trial is justified by the evidence.

Request explicit approval before touching live firmware, MCU power, hardware reset, watchdog settings or boot partitions.

Do not conduct repeated speculative hardware trials or automated reflash loops.

Once approved, execute only the reviewed scope and collect complete evidence.

If the result differs from expectation, stop that trial, preserve the evidence and investigate before proposing another.

## 10. RESTORE REAL SENSOR STREAMING

After successful, verified MCU initialization, validate the kernel SSP handshake.

Prove that:

- Expected chip identity is obtained.
- MCU firmware revision is read.
- SSP initialization completes.
- Required sensor metadata is accepted.
- Scanning configuration becomes active.
- Real incoming sensor packets arrive.
- Accelerometer and gyroscope measurements change under actual physical movement.

Do not inject fabricated motion vectors into the production sensor pipeline.

The success condition requires genuine measurements from the actual handset.

## 11. RESTORE AUTOMATIC ROTATION

Once real streaming is established, integrate it with Nuxel's existing sensor and orientation services.

Verify:

- All four screen orientations.
- Stable orientation detection.
- Correct sensor-axis mapping.
- Correct touchscreen mapping.
- Manual rotation controls.
- Lock and unlock behavior.
- Sensor recovery after suspend/resume.
- Normal boot initialization.
- No GNSS, top-bar or power-menu regressions.

Do not classify simulated rotation tests as physical acceptance.

## 12. REQUIRED WORKING STYLE

Work as an implementation engineer, not merely a report generator.

For each independently verifiable engineering milestone:

1. Identify the most consequential unresolved question.
2. Gather the evidence required to answer it.
3. Reuse existing source where possible.
4. Implement a justified correction or diagnostic.
5. Execute relevant tests.
6. Record observed results and limitations.
7. Commit the working improvement.
8. Select the next unresolved milestone.

Avoid repeating previously completed analysis unless contradictory evidence appears.

Avoid spending large amounts of reasoning effort on a small function after its behavior has been established.

Prioritize investigation that closes an entire causal path.

Do not ask the owner to perform tasks that can safely be completed from existing local sources.

Do not claim that an unknown protocol is impossible merely because documentation is absent.

Continue safe static analysis, source comparison, offline implementation and reproducible testing as long as useful work remains within the session.

When execution limits or missing external evidence prevent continued progress, preserve an exact restart checkpoint with the next concrete action.

## 13. REQUIRED DELIVERABLES

Maintain:

`reports/SSP-FIRST-LIGHT-FINAL-RECOVERY.md`

And supporting evidence in a dedicated dated directory.

Include:

- Verified findings and exact source references.
- Completed call graphs.
- Reconstructed protocol elements and unresolved fields.
- Source changes and commit hashes.
- Test outputs and failures.
- Current actual physical handset state.
- Remaining authorization requirements.
- Next safe investigation or implementation action.

Preserve unrelated work and existing successful tests.

Only mark the SSP recovery complete when physical accelerometer and gyro data have been verified.

Only mark automatic rotation complete after hardware-driven physical testing.

## FINAL DIRECTIVE

The matching firmware and Samsung runtime have already been recovered.

The priority is now to understand and correctly use their existing initialization behavior.

**Do not restart the project. Do not endlessly rewrite reports. Do not manufacture success.**

Continue solving the next highest-value technical problem, repeatedly, with verifiable implementation and test evidence.

The target is a real operational BCM47752 sensor hub and working Nuxel automatic rotation.

If completion requires a hardware-changing operation, obtain explicit approval with a defensible recovery plan.

If a missing external artifact is genuinely indispensable, explain exactly why and preserve all progress.

Otherwise, continue engineering toward the next verified milestone.
