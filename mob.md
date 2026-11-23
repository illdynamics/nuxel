# NUXEL — STAGE 06 FINAL
## OPERATION MULTIBASS 9000: FINAL BOSS EXTERMINATOR
### Complete Native Samsung Shannon LTE Data Integration

**Agent:** DeepSeek V4 Pro Thinking
**Execution:** Autonomous, live hardware, full repository access
**Repository:** `/Users/wicked/x/nuxel`
**Branch:** `cs/mob`
**Last known committed checkpoint:** `426e7c97`
**Device:** Samsung Galaxy S10+ SM-G975F / beyond2lte
**Modem:** Samsung Shannon S5000AP
**Kernel:** Linux 4.14.253
**SSH:** `root@10.11.12.99`
**Vendor RIL:** SM-G975F EFUJ2, Build ID beginning `60889dd7`

# 0. PRIMARY OBJECTIVE

Finish Stage 06 completely.

The final acceptance target is:

`STAGE_06_FULL_PASS — NATIVE CELLULAR IP/DNS/HTTPS AND RECONNECT VERIFIED`

This is an implementation-and-validation mission, not another open-ended reverse-engineering report.

You must recover the remaining protocol details, implement the missing functionality, test it offline, deploy it safely, and verify a genuine cellular internet connection on the physical Nuxel device.

Do not stop after finding another symbol, packet format, or disassembly offset.

Do not repeat completed Stage 01–05 work.

Continue through all authorized and technically justified work until the acceptance target is reached or a specific hard blocker is demonstrated.

# 1. OWNER AUTHORIZATION

The owner authorizes the following operations for this Stage 06 mission:

- Read-only analysis of the existing Samsung vendor binaries.
- Static disassembly and protocol recovery.
- Source-code modifications within the Nuxel project.
- Compilation, testing, sanitizers and fuzzing.
- Creation and execution of offline protocol test harnesses.
- Installation of tested Nuxel userspace binaries.
- Reversible systemd service changes.
- Controlled restart of `nuxel-radiod`.
- Bounded, evidence-backed modem data-session requests.
- Cellular packet-data attachment and disconnection.
- Cellular APN configuration after verification.
- Small cellular IP/DNS/HTTPS test requests.
- Cellular interface configuration.
- Isolated cellular routing tests.
- Controlled modem resets when required and supported by the established recovery procedure.
- Controlled service recovery and reconnection tests.
- Git commits on `cs/mob`.
- Documentation and test-report updates.

The owner also authorizes bounded cellular data usage necessary for verification, provided the subscription supports it and roaming is not enabled without separate approval.

## Authorization boundaries

This prompt does not authorize:

- Writes to protected boot, radio, firmware or recovery partitions.
- EFS/NV modifications or destructive RFS operations.
- Security bypasses.
- SIM PIN guessing.
- Firmware flashing.
- Unbounded modem-command experimentation.
- Destructive filesystem operations.
- Disabling the only remaining management connection.
- Unbounded or unexpected cellular charges.
- Publishing proprietary Samsung binaries.
- Git merge, release or tag creation.

If a protected or destructive operation becomes necessary, stop that operation and request a separate, specific authorization.

Do not treat the general instruction to finish Stage 06 as permission to bypass these boundaries.

# 2. EXACT STARTING POINT

The previous run reported:

- CP ONLINE.
- Native RFS communication functional.
- SIM READY.
- USIM recognized.
- Serving PLMN `20416`.
- Live IPC41 FMT receive traffic.
- Complete IPC41 command-name mapping.
- Native data-session TX not implemented.
- `rmnet0..7` DOWN.
- USB and Wi-Fi management preserved.
- RADIO partition unchanged.

The previous run also recovered a possible alternative TX packet layout from:

`IpcProtocol41::IpcTxExchange` at approximately `0x342a80`.

Cached analysis:

`/tmp/s5000ap06/IpcTx_data.txt`

Additional analysis may exist under:

`/tmp/analysis/`

First inspect the current Git HEAD, repository state and available analysis artifacts.

Do not assume temporary files survived a reboot.

If the files are missing, regenerate the analysis from the exact read-only vendor binary.

Do not waste tokens repeating unrelated protocol research.

# 3. PRIORITY ZERO — RESOLVE THE TX FRAMING CONTRADICTION

This is the first critical blocker.

The existing Nuxel receive parser uses:

`[u16 len][u8 msg_seq][u8 ack_seq][u8 main][u8 sub][u8 type]`

The latest vendor disassembly reportedly shows:

`[u16 total_len][u16 cmd_id][u8 type][u8 cksum_hi][u8 cksum][op0][op1][op2][op3][payload]`

These structures cannot be assumed interchangeable.

## Required investigation

Trace `IpcTxExchange` through the complete call chain:

1. Function arguments.
2. Internal command construction.
3. Intermediate buffers.
4. Any framing or wrapping functions.
5. Transport abstraction.
6. Final kernel write or ioctl.
7. Kernel framing and channel handling.
8. Corresponding receive-side representation.

Determine whether the apparent discrepancy is caused by:

- Different protocol layers.
- Intermediate versus final buffers.
- Distinct command and transport headers.
- Command-ID packing.
- Checksums.
- Direction-specific framing.
- Different device channels.
- Incorrect interpretation of disassembly.
- Different IPC protocol versions.

Identify the exact bytes that must be written to the actual device interface.

Do not assume the vendor function's internal buffer is the final on-wire frame.

## Mandatory evidence

Produce:

- A documented TX call graph.
- A byte-level diagram of each framing layer.
- The exact transformation between command ID and main/subcommand fields.
- Verified frame-length semantics.
- Verified checksum semantics, if applicable.
- Sequence and acknowledgment behavior.
- Evidence identifying the final transport write.
- At least one source-backed offline serialization test vector.

Do not modify the working RX parser merely to match the new TX hypothesis.

Preserve both representations if they belong to different layers.

**Gate TX-FRAME-01 passes only when the actual transport framing is unambiguous.**

# 4. FINISH THE DATA-PATH PAYLOAD DECODING

Use the existing disassembly and exact vendor binary.

Previously identified functions:

- `IpcTxDefinePdpContext` — `0x31f580`
- `IpcTxPsAttach` — `0x31fa98`
- `IpcTxSetDataProfile` — `0x31ff48`
- `IpcTxSetDataCallEstablish` — `0x320a10`
- `IpcTxSetMobileDataSetting` — `0x3214c8`

Reported command words:

- Define PDP context: `0x0605`
- PS attach: `0x030d`
- Set data profile: `0x1b0d`, possible fallback `0x090d`

Reported payload sizes:

- Define PDP context: 134 bytes.
- Set data profile: up to 203 bytes.

Treat all values as findings to verify against the exact call chain.

## Recover every required field

For each data-path command, establish:

- Exact payload size.
- Field offsets and widths.
- Byte order.
- APN representation.
- IP-family selection.
- Authentication configuration.
- Profile and context identifiers.
- Command flags.
- Reserved fields.
- String length and termination.
- Optional field handling.
- Transaction identifiers.
- Response and error-code interpretation.

Document every field with its source evidence.

If a field is genuinely unknown, do not guess.

Determine whether it is required for the minimum valid data session.

Do not confuse structure allocation size with serialized payload length.

# 5. RECOVER THE ACTUAL TRANSACTION SEQUENCE

Determine the modem-supported sequence for establishing a cellular data session.

Investigate:

- Registration prerequisites.
- Packet-data attachment.
- Mobile-data enablement.
- Profile configuration.
- PDP-context definition.
- Data-call establishment.
- Data-call result.
- IP configuration.
- Data-call teardown.

Do not assume the order above is the actual protocol order.

Trace the vendor control flow and response handlers.

Determine which steps are already satisfied by the modem and which require native commands.

Implement only the minimum evidence-backed sequence required for one data session.

# 6. IMPLEMENT NATIVE IPC41 TX

Implement a complete native TX facility in `nuxel-radiod`.

Requirements:

- Correct transport framing.
- Correct command serialization.
- Validated lengths and offsets.
- Correct command types.
- Correct sequence handling.
- Safe buffer management.
- Partial-write handling.
- Error propagation.
- Response correlation.
- Asynchronous notification handling.
- Timeout handling.
- Bounded retries.
- Sensitive-data redaction.

Keep the implementation modular.

Do not introduce an Android RIL dependency.

Do not execute Samsung's proprietary RIL at runtime.

Preserve the existing receive path and RFS responder.

Do not block the FMT receive loop while waiting for a command response.

# 7. IMPLEMENT A REAL DATA-SESSION STATE MACHINE

Implement explicit state tracking for:

- CP offline/online.
- SIM unavailable/ready.
- Network searching/registered.
- LTE RAT confirmed.
- Packet-data detached/attached.
- Profile unconfigured/configured.
- PDP context inactive/configured.
- Data-call pending/active/rejected.
- Interface unavailable/available.
- IP unconfigured/configured.
- Data-session disconnecting/disconnected.
- Recoverable and terminal failures.

Transitions must be based on actual modem responses or authoritative kernel state.

Never treat successful transmission as successful session establishment.

Handle:

- Modem rejection.
- Timeouts.
- Lost registration.
- Service restart.
- Unexpected disconnect.
- Repeated unsolicited notifications.
- Modem recovery.
- Controlled teardown.

Retries must be bounded and justified.

# 8. CONFIRM LTE REGISTRATION AND CARRIER PROFILE

Revalidate the actual registration-status value and radio access technology.

A serving PLMN and RSSI alone do not prove successful LTE registration.

Confirm the correct APN for the active subscription.

The previously suggested APN `internet` is a candidate, not proof.

Determine whether authentication is required.

Do not invent credentials.

Do not enable roaming without separate authorization.

Implement APN and data-session configuration independently of the protocol serializer.

Do not expose subscriber identifiers or credentials in logs.

# 9. COMPLETE OFFLINE VALIDATION

Before live data-command transmission:

- Compile with strict warnings.
- Run existing regression tests.
- Run protocol serialization tests.
- Run known-good packet-vector tests.
- Test invalid lengths.
- Test truncated frames.
- Test invalid command types.
- Test invalid profile parameters.
- Test timeout and rejection handling.
- Test state-machine transitions.
- Test reconnect behavior.
- Run applicable sanitizers.
- Run bounded fuzz tests.

Do not use self-generated guessed packets as the only source of truth.

All mandatory tests must pass.

Document the test results.

# 10. VERIFY DEPLOYMENT PROVENANCE

The project previously had a mismatch between canonical source, compiled output and deployed executable.

Verify:

- Canonical source path.
- Complete build inputs.
- Build-script source list.
- Resulting executable.
- Systemd `ExecStart`.
- Deployed executable hash.
- Running process executable.

Deploy only the tested binary.

Keep a verified rollback copy.

Preserve USB and Wi-Fi management access.

# 11. EXECUTE THE AUTHORIZED PHYSICAL DATA TEST

Once the framing, serialization, state machine, carrier profile and offline tests are verified, perform a bounded cellular data-session test.

This prompt authorizes that test subject to the safety boundaries in Section 1.

Use one controlled attempt.

Capture:

- Outgoing command identifiers.
- Sanitized request metadata.
- Modem acknowledgments.
- Packet-data attach status.
- PDP-context result.
- Data-call establishment result.
- Context identifier.
- Activated network interface.
- Rejection/cause codes.

If rejected:

1. Stop additional speculative requests.
2. Decode the exact failure.
3. Investigate offline.
4. Correct the implementation.
5. Re-run tests.
6. Retry only when a concrete correction is supported by evidence.

Do not brute-force commands, APNs, flags or enum values.

# 12. BRING UP CELLULAR NETWORKING

After the modem accepts the data session, identify the correct Linux data interface.

The device previously exposed `rmnet0..7`, all DOWN.

Determine the actual modem-context-to-interface mapping.

Verify:

- Interface activation.
- Link configuration.
- MTU.
- IP address and prefix.
- IPv4/IPv6 negotiation.
- Routing.
- DNS.
- Packet counters.
- Interface teardown.

Use native Linux networking facilities.

Preserve USB SSH.

Do not overwrite the system default route during initial validation.

Use isolated routing or interface-specific tests to prove traffic uses cellular.

# 13. PROVE REAL CELLULAR INTERNET

Perform these mandatory physical tests:

**Test A — Active bearer**

The modem confirms an active data session and the corresponding Linux interface is usable.

**Test B — Cellular IP**

A small IP request succeeds through cellular, with no Wi-Fi fallback.

**Test C — Cellular DNS**

A hostname resolves through cellular.

**Test D — Cellular HTTPS**

A bounded HTTPS request succeeds through cellular with certificate verification.

**Test E — Routing proof**

Evidence demonstrates the successful traffic traversed the cellular interface.

**Test F — Disconnect and reconnect**

The data session disconnects cleanly and reconnects successfully.

**Test G — Service recovery**

The daemon recovers correctly after a controlled restart.

**Test H — Management preservation**

USB management remains available throughout.

Do not claim cellular success from Wi-Fi connectivity.

# 14. PROTECTED-HARDWARE SAFETY

Preserve the known RADIO partition integrity hash.

Do not write protected partitions.

Do not perform destructive NV/EFS or RFS operations.

Do not guess protocol bytes.

Do not execute uncontrolled modem resets.

Do not log sensitive subscriber identifiers.

Do not create unbounded data usage.

Do not modify unrelated device subsystems.

Maintain rollback capability throughout.

If the only path forward requires an unapproved destructive operation, stop and report the exact intervention required.

# 15. CONTINUATION POLICY — NO MORE RESEARCH-ONLY LOOPS

Work through the following sequence:

**A.** Resolve TX framing completely.

**B.** Finish payload decoding.

**C.** Recover data-session response semantics.

**D.** Implement native TX.

**E.** Implement data-session state management.

**F.** Pass offline tests.

**G.** Deploy reversibly.

**H.** Establish the cellular data session.

**I.** Configure the Linux cellular interface.

**J.** Verify cellular IP, DNS and HTTPS.

**K.** Verify teardown and reconnect.

**L.** Commit and document the completed implementation.

Do not repeatedly inventory already known symbols.

Do not restart earlier stages.

Do not spend the entire run rewriting documentation before implementing the missing functionality.

Do not stop at the first partial milestone.

If a hard blocker is reached, report the exact unresolved issue and the minimum next action.

If the execution budget is nearly exhausted, prioritize preserving the current implementation and an actionable checkpoint rather than starting another unfinishable investigation.

# 16. REQUIRED FINAL ACCEPTANCE MATRIX

| Gate | Required result |
|---|---|
| CP ONLINE | PASS |
| RFS handshake | PASS |
| SIM READY | PASS |
| LTE registration and RAT | PASS |
| TX framing reconciled | PASS |
| PDP/profile serialization verified | PASS |
| Native IPC41 TX implemented | PASS |
| Offline protocol tests | PASS |
| Packet-data attach | PASS |
| PDP context accepted | PASS |
| Data call active | PASS |
| Cellular interface usable | PASS |
| Cellular IP connectivity | PASS |
| Cellular DNS | PASS |
| Cellular HTTPS | PASS |
| Cellular disconnect/reconnect | PASS |
| Management preserved | PASS |
| Protected storage unchanged | PASS |

Only declare:

`STAGE_06_FULL_PASS`

when every mandatory gate passes on physical hardware.

Otherwise declare:

`STAGE_06_NOT_YET_PASS — [EXACT BLOCKER]`

# 17. REQUIRED DELIVERABLES

Commit to `cs/mob`:

1. Verified TX framing implementation.
2. PDP/profile serializers.
3. Native data-session command handling.
4. Data-session state machine.
5. Response decoders.
6. Carrier configuration support.
7. Linux cellular networking integration.
8. Unit and negative-path tests.
9. Sanitizer/fuzz results.
10. Sanitized hardware verification evidence.
11. Updated build and deployment scripts.
12. Rollback procedure.
13. Final Stage 06 report.
14. Stage 07 handoff notes if Stage 06 passes.

Do not merge or publish a release without separate authorization.

# 18. FINAL RESPONSE CONTRACT

Your response must begin with exactly one of:

`STAGE_06_FULL_PASS — VERIFIED NATIVE CELLULAR INTERNET`

or:

`STAGE_06_NOT_YET_PASS — [EXACT REMAINING BLOCKER]`

Then report:

- Git HEAD.
- Implemented files.
- Recovered protocol details.
- Offline tests.
- Physical modem results.
- Cellular IP/DNS/HTTPS evidence.
- Reconnection evidence.
- Safety verification.
- Remaining blockers.
- Stage 07 readiness.

No fabricated evidence.

No inflated milestone claims.

No premature PASS.

# FINAL DIRECTIVE

The modem is alive.

The SIM is initialized.

The proprietary protocol is substantially understood.

The remaining challenge is the native data-session implementation.

**Resolve the TX framing discrepancy, finish the protocol recovery, implement the missing code, and prove real cellular internet.**

Continue through all authorized, reversible engineering work until Stage 06 passes or a genuine blocker is demonstrated.

**OPERATION MULTIBASS 9000 — FINISH THE JOB.**

🐧🔥 BAAAAAAAAAM.
