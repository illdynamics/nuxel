# NUXEL — OPERATION FINAL BEARER
## STAGE 06: PHYSICAL LTE INTERNET OR PROVEN EXTERNAL BLOCKER
### Autonomous Engineering Directive — No Research Loops, No Premature PASS

**MODE:** Maximum-effort autonomous engineering and hardware verification
**TARGET:** `STAGE_06_FULL_PASS`
**REPOSITORY:** `/Users/wicked/x/nuxel`
**BRANCH:** `cs/mob`
**LAST REPORTED HEAD:** `0f5eeb74`
**DEVICE:** Samsung Galaxy S10+ beyond2lte
**MODEM:** Samsung Shannon S5000AP
**KERNEL:** Linux 4.14.253

---

# 0. MISSION — NO MORE PARTIAL COMPLETION

Your assignment is to complete Stage 06 native cellular networking.

Do not terminate voluntarily after completing research, compilation, deployment, protocol decoding, or command acknowledgment.

Continue through every authorized, reversible implementation and verification step until cellular networking passes the physical acceptance tests.

The only successful final status is:

`STAGE_06_FULL_PASS — CELLULAR IP + DNS + HTTPS + RECONNECT VERIFIED`

If hardware, carrier provisioning, missing authorization, or an unavoidable execution limit prevents completion, report the exact blocker and preserve the next executable action.

Do not fabricate a PASS.

Do not claim that you can override execution limits.

**No more research-only rounds. No more generic progress reports. No more rediscovering previously decoded functions.**

---

# 1. START FROM THE LAST VERIFIED MILESTONE

The previous run reported:

- CP ONLINE.
- RFS handshake operational.
- Native radio daemon running.
- SIM READY previously observed.
- IPC41 command vocabulary recovered.
- PDP protocol-byte mapping corrected.
- Native FMT TX implemented.
- Data-session FSM implemented.
- Always-on-PDN phase added.
- GEN response echo correlation discovered.
- Five consecutive data-session command responses observed.
- Data-session FSM reached `WAIT_IP`.
- No active cellular bearer.
- No cellular IP/DNS/HTTPS.
- RADIO hash unchanged.
- Git HEAD `0f5eeb74`.

The observed GEN response payloads include:

```text
0d1d030380
0d01030180
0d22030080
0d03030080
0302030380
```

These appear to echo the transmitted main/subcommand identifiers.

However, their result semantics are not yet proven.

**Do not equate a GEN response with command success.**

Verify all previous claims against current source, logs, and vendor evidence.

---

# 2. ABSOLUTE PRIORITY — DECODE GEN RESULT SEMANTICS

The first unresolved issue is the response status.

The final byte `0x80` appears repeatedly.

Determine exactly what it means.

Analyze:

- Vendor GEN response dispatcher.
- Response status translation.
- Command completion handlers.
- Error/cause-code mapping.
- Per-command response semantics.
- Relevant `IpcRxGprsCallStatus` behavior.
- Relevant `IpcRxPdpContext` behavior.
- IP-configuration response handling.

Use the vendor EFUJ2 `libsec-ril.so` as a read-only interoperability reference.

Identify whether `0x80` means:

- Success.
- Failure.
- Unsupported command.
- Invalid state.
- Pending operation.
- A generic response category.
- Something else.

Do not assume.

Document the exact evidence.

## Required implementation

Replace the generic response acceptance logic with strict correlation.

Validate:

1. Expected GEN message type.
2. Outstanding command main/sub.
3. Response echo.
4. Transaction identity where available.
5. Result-code semantics.
6. Current FSM phase.
7. Context identifier when applicable.

Never advance on an unrelated response.

Never advance on an error result.

Never advance on an unknown result.

Add tests for successful, rejected, malformed, duplicate, stale, and out-of-order responses.

---

# 3. COMPLETE THE 203-BYTE DATA PROFILE

The previous run identified incomplete `SetDataProfile` reconstruction as a likely blocker.

Treat this as a hypothesis requiring verification.

Recover the complete vendor serializer for:

`IpcTxSetDataProfile`

Inspect the exact function and its relevant callees.

Recover every required field, including:

- Profile ID.
- Context ID.
- APN.
- PDP protocol.
- Roaming protocol.
- Authentication.
- Credential lengths.
- Profile enable flags.
- APN type.
- Reserved fields.
- Length fields.
- LTE-related flags.
- Remaining tail bytes.

Do not assume zero-filled fields are valid.

Do not invent values.

Do not blindly copy arbitrary vendor memory.

Build a field-offset table with evidence.

Implement a deterministic, byte-exact serializer.

Add tests for:

- Correct total length.
- Correct field offsets.
- Correct protocol mapping.
- Valid APN.
- Empty APN.
- Maximum APN length.
- Invalid enum values.
- Overflow rejection.
- Known-good vendor-derived test vectors.

Ensure the serializer is integrated into the live data-session FSM.

---

# 4. IMPLEMENT VERIFIED LTE ATTACH PROFILE HANDLING

Investigate:

`SetLteAttachProfile`

Previously reported subcommand:

`main=13, sub=20`

Verify that mapping against the vendor binary.

Determine:

- Whether the command is required.
- Its prerequisites.
- Its payload structure.
- Its relationship to SetDataProfile.
- Its expected response.
- Its correct position in the initialization sequence.

Implement it only when supported by evidence.

Do not transmit guessed payloads.

Do not assume that the command is mandatory merely because the vendor exposes it.

Add byte-exact tests.

Integrate it into the FSM at the verified point.

---

# 5. RESOLVE THE ACTUAL DATA-CALL FAILURE

Once the serializers and response semantics are verified, determine why the data call does not produce a bearer.

Investigate:

- Packet-data registration.
- PS attachment state.
- PDP activation status.
- Profile acceptance.
- APN provisioning.
- Carrier rejection codes.
- Data-call activation responses.
- GPRS call status.
- IP-configuration notifications.
- Context-to-rmnet mapping.

Use actual modem evidence to distinguish:

**A.** Command rejected.

**B.** Command acknowledged but not executed.

**C.** Attach/profile incomplete.

**D.** Carrier provisioning rejected.

**E.** Data call active but IP configuration missing.

**F.** IP configuration available but Linux interface not configured.

**G.** Other verified root cause.

Fix the identified cause.

Do not repeat the same failed command sequence without a concrete correction.

---

# 6. PHYSICAL TEST — ONE CONTROLLED SESSION

After offline verification:

1. Confirm CP ONLINE.
2. Confirm SIM READY.
3. Confirm packet-data registration.
4. Confirm the correct APN.
5. Confirm non-roaming conditions.
6. Confirm management connectivity.
7. Confirm rollback binary.
8. Deploy the tested daemon.
9. Verify deployed binary hash.
10. Trigger one controlled data-session attempt.
11. Capture complete sanitized FMT TX/RX.
12. Decode every response.
13. Determine the actual bearer state.

If the modem rejects the session, stop retries and decode the failure.

If the modem activates a bearer, proceed immediately to Linux networking integration.

---

# 7. BRING UP CELLULAR NETWORKING

Inspect:

`rmnet0..7`

Determine the actual active interface and its associated modem context.

Do not assume `rmnet0`.

Implement:

- Interface activation.
- Correct MTU.
- IP address configuration.
- IPv4/IPv6 handling.
- Gateway or point-to-point routing.
- DNS configuration.
- Data-session teardown.
- Recovery after disconnect.

Preserve Wi-Fi and USB management.

Use isolated cellular routes for connectivity tests.

Never mistake traffic through Wi-Fi or ZeroTier for cellular connectivity.

---

# 8. CELLULAR CONNECTIVITY ACCEPTANCE

All tests must use the verified cellular interface.

## Test A — Cellular IP

Perform a small, bounded IP connectivity test.

## Test B — Cellular DNS

Resolve a hostname using the cellular connection.

## Test C — Cellular HTTPS

Perform a small HTTPS request with certificate verification enabled.

## Test D — Routing isolation

Prove the traffic traversed the cellular bearer.

## Test E — Disconnect

Cleanly terminate the session.

## Test F — Reconnect

Re-establish the session and repeat IP/DNS/HTTPS.

## Test G — Service recovery

Restart the daemon safely and verify recovery.

Only after all tests pass may Stage 06 be declared complete.

---

# 9. SYSTEM HEALTH IS PART OF THE ACCEPTANCE CRITERIA

The previous run observed:

- Load average approximately 13.
- Python process PID 6784 reportedly consuming 100% CPU.
- Approximately 8,170 zombie processes.
- `ksoftirqd` reportedly consuming approximately 98% CPU.
- Temporary ZeroTier SSH connectivity loss.

Do not dismiss these findings merely because they predate the current session.

Investigate their relationship to:

- Modem interrupts.
- Network processing.
- Excessive process creation.
- Daemon restart loops.
- Resource exhaustion.
- Kernel softirq saturation.
- SSH responsiveness.

Identify the parent of zombie processes.

Inspect CPU, memory, process and interrupt trends.

Determine whether the modem data path contributes to the load.

Do not terminate unrelated processes without authorization.

Do not modify unrelated subsystems unnecessarily.

If system health is unstable, stabilize the testing environment before continuing live modem experiments.

---

# 10. SAFETY INVARIANTS

The RADIO partition:

`/dev/sda16`

Expected SHA256:

`9ffa1426a4ef7d1187779a14f22ec4b8cb4c2ab473b6626304a77030d9966fc7`

Never write to it.

Never modify:

- EFS.
- NV.
- IMEI.
- ICCID.
- SIM PIN/PUK.
- Modem firmware.
- Protected partitions.

Never execute destructive RFS operations.

Never brute-force modem commands.

Never perform unbounded retries.

Never intentionally destroy all management connectivity.

Use reversible deployment with a verified rollback binary.

Keep proprietary Samsung code out of published deliverables.

---

# 11. NO MORE WASTED TOKEN BUDGET

Do not repeat the full IPC41 discovery process.

Do not dump enormous disassemblies.

Do not repeatedly inspect already verified functions.

Do not produce large speculative research reports.

Work directly on the remaining blocker.

Use:

**Evidence → Code → Test → Hardware → Next gate**

Maintain a concise checkpoint, but never treat checkpoint creation as completion.

If an execution budget is nearly exhausted:

1. Finish or safely interrupt the current operation.
2. Preserve verified changes.
3. Commit coherent tested milestones.
4. Record the exact remaining blocker.
5. Leave the device in a known recoverable state.
6. Report `NOT_YET_PASS`.

Do not claim automatic continuation unless an actual supervisor provides it.

---

# 12. BUILD AND DEPLOYMENT RULES

The device has native GCC and libsystemd.

Prefer the existing verified native-build path unless a working cross-build environment is already available.

Do not spend another run searching for toolchains unnecessarily.

Verify actual compiler exit status.

Do not use a pipeline exit code as proof that GCC succeeded.

Use `pipefail` or capture the compiler status directly.

Verify:

- Binary exists.
- Correct architecture.
- Correct source revision.
- Tests pass.
- Executable hash.
- Deployed hash.
- Running process executable.
- Service health.
- Rollback availability.

---

# 13. MANDATORY COMPLETION GATES

The following must all pass:

- [ ] CP ONLINE.
- [ ] RFS handshake operational.
- [ ] SIM READY.
- [ ] LTE registration verified.
- [ ] GEN result semantics decoded.
- [ ] Strict response correlation implemented.
- [ ] Complete data-profile serializer verified.
- [ ] LTE attach-profile requirements resolved.
- [ ] PDP configuration accepted.
- [ ] Packet-data attachment accepted.
- [ ] Data call confirmed active.
- [ ] Correct rmnet interface identified.
- [ ] Cellular IP configuration established.
- [ ] Cellular IP connectivity verified.
- [ ] Cellular DNS verified.
- [ ] Cellular HTTPS verified.
- [ ] Disconnect successful.
- [ ] Reconnect successful.
- [ ] Service recovery successful.
- [ ] Management connectivity preserved.
- [ ] System health acceptable.
- [ ] Protected storage unchanged.
- [ ] Regression tests passing.
- [ ] Final implementation committed.

Do not mark a gate complete without evidence.

---

# 14. FINAL DELIVERABLES

Provide:

1. Corrected response decoder.
2. Strict GEN correlation.
3. Complete data-profile serializer.
4. LTE attach-profile implementation, if required.
5. Corrected data-session FSM.
6. Linux cellular networking integration.
7. Regression tests.
8. Negative-path tests.
9. Live modem logs.
10. Cellular connectivity evidence.
11. Reconnection evidence.
12. System-health findings.
13. Safety verification.
14. Final Git commit.
15. Stage 06 acceptance report.

---

# 15. FINAL RESPONSE CONTRACT

If every gate passes, begin:

`STAGE_06_FULL_PASS — NATIVE LTE INTERNET VERIFIED ON PHYSICAL HARDWARE`

Otherwise begin:

`STAGE_06_NOT_YET_PASS — [EXACT VERIFIED BLOCKER]`

Include:

- Git HEAD.
- Verified fixes.
- Actual hardware results.
- GEN response interpretation.
- Bearer status.
- Cellular interface.
- IP/DNS/HTTPS results.
- Reconnection results.
- Safety status.
- Remaining blockers.

Never report PASS based only on a successful build, an ACK, or a state-machine transition.

---

# EXECUTE NOW

Start from HEAD `0f5eeb74`, verifying the actual current HEAD first.

Resolve GEN `0x80` semantics.

Complete the 203-byte SetDataProfile implementation.

Determine whether SetLteAttachProfile is required.

Fix the bearer-establishment failure.

Bring up the cellular interface.

Prove cellular IP, DNS and HTTPS.

Verify disconnect and reconnect.

Commit the completed implementation.

**Do not voluntarily stop at another partial milestone.**

**Do not repeat completed research.**

**Do not substitute a checkpoint for working hardware.**

**Do not manufacture a PASS.**

**FINISH THE ENGINEERING. PROVE THE CONNECTION. PASS STAGE 06.**

🐧🔥 OPERATION FINAL BEARER — BAAAAAAAAAM.
