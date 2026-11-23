# NUXEL — STAGE 06: OPERATION BOOMBATSCH
## AUTONOMOUS EXECUTION MISSION — REAL LTE MOBILE INTERNET

### MISSION DIRECTIVE

You are the lead modem integration engineer responsible for finishing Stage 06 of Nuxel, the native Linux mobile operating system running on the Samsung Galaxy S10+ SM-G975F (beyond2lte), Exynos 9820, Shannon S5000AP.

**Your mission is to establish and independently verify real LTE mobile internet through the physical SIM and modem.**

This is an **EXECUTION mission**, not another research report.

You have authorization to inspect, reverse-engineer, modify, build, test, deploy, troubleshoot and commit the Nuxel userspace modem implementation as necessary.

Do not stop merely because you have found a plausible root cause. Continue through diagnosis, implementation, live validation and correction.

Do not substitute documentation, simulated success, passing unit tests or command acknowledgements for a working cellular bearer.

**The goal is a genuine `STAGE_06_PASS`.**

There is no artificial time or token budget. Work iteratively and make measurable progress.

---

## 1. CURRENT VERIFIED BASELINE

Repository:

`/Users/wicked/x/nuxel`

Device:

`root@10.11.12.99`

Current branch:

`cs/mob`

Latest documented commits:

- `df3d2c19` — Stage 06 modem source fixes.
- `effd616d` — Round 14 documentation.

Current deployed daemon SHA-256:

`e50b9c820c97e0bdab9aad816c0b4cba9d4c5ad28fa706774b5d9a08d212df01`

Device:

- Modem CP ONLINE.
- SIM detected and READY.
- PLMN 20416.
- CS registration reported REGISTERED.
- PS registration reported DENIED.
- `rmnet0` through `rmnet7` DOWN.
- No verified cellular IP, DNS or HTTPS.

Live generic responses previously observed:

| Command | Observed result |
|---|---|
| SetServiceDomain | 0 |
| SetPreferredNetType | 0 |
| SetMobileDataSetting | 3 |
| SyncProfileInfo | 1 |
| SetDataProfile | 0 |
| SetLteAttachProfile | 0 |
| DefinePdpContext | 1 |
| SetAlwaysOnPdn | 0 |
| PsAttach | 0 |
| SetPdpContext | 0 |
| DataCall | 0 |

These are observed generic response values. Independently verify their exact vendor semantics before interpreting zero as success or nonzero as rejection.

Final data-call indication:

`GPRS_CALL_STATUS main=13 sub=16 type=3`

Reported:

`call_state=3, pdp_state=0`

The existing daemon transitions through its data-session FSM but does not establish a bearer.

The SIM's data subscription has been confirmed functional in another phone.

### Existing implementation

Relevant source:

`tools/s10plus/s5000ap-05/`

Relevant files include:

- `src/radiod.c`
- `src/data_session.c`
- `src/data_session.h`
- `src/fmt_tx.c`
- `src/fmt_tx.h`
- SIPC5 transport and parser files
- Data-session and TX tests

Vendor reference:

`/tmp/vendor-ro/lib64/libsec-ril.so`

Read-only vendor analysis is permitted.

Do not assume the vendor library or its temporary path is still available. Verify before using it.

---

## 2. NON-NEGOTIABLE ENGINEERING RULES

1. Preserve the existing working Nuxel installation.
2. Preserve SSH, Wi-Fi, USB and ZeroTier management connectivity.
3. Never fabricate a successful registration, bearer, IP address or network test.
4. Never declare PASS based on the FSM reaching ACTIVE alone.
5. Never advance the FSM solely because an unrelated response arrived.
6. Never silently ignore a modem error.
7. Never guess an IPC payload and transmit it as though vendor-verified.
8. Never use a successful build as proof of a successful deployment.
9. Never overwrite a working binary without a recoverable backup.
10. Never modify IMEI, subscriber identity, carrier authorization, CP firmware, bootloader, partition tables, EFS or protected NV data.
11. Do not bypass SIM PIN, network locks, carrier authentication or access controls.
12. Do not use destructive modem resets or repeated uncontrolled registration attempts.
13. Honor network backoff timers and modem retry limits.
14. Preserve user data and management access.
15. Do not reboot into recovery or reflash partitions merely to investigate userspace LTE.
16. Keep unrelated Nuxel functionality outside this mission.

You may perform reversible, verified userspace changes and controlled service restarts.

If a proposed action could affect protected persistent modem state, stop that specific action, document the precise requirement, and continue all safe alternative paths.

**Authorization to finish the mission does not justify bypassing network controls or destroying the device.**

---

## 3. EXECUTION PHASE A — ESTABLISH A TRUSTWORTHY LIVE BASELINE

Immediately:

1. Read `mob.md` and the existing Stage 06 safety documentation.
2. Inspect the current branch, working tree and latest commits.
3. Confirm the modem is ONLINE and the SIM is READY.
4. Confirm the deployed daemon's binary hash and running process.
5. Confirm that management connectivity is independent of cellular interfaces.
6. Inspect the current radio daemon configuration and APN source.
7. Capture a timestamped baseline of relevant modem responses.
8. Preserve the currently working daemon for rollback.

Record the current modem registration state, data-call status, active network interfaces and routing configuration.

Do not clear or overwrite the existing `mob.md` content.

Do not expose IMSI, ICCID, IMEI, PIN, subscriber secrets or authentication material in logs or reports.

### Mandatory deployment correction

Replace the existing unsafe deployment pattern:

`gcc ...; install ...; systemctl restart ...`

with a fail-closed deployment workflow.

The workflow must:

- Abort on unsuccessful file transfer.
- Verify transferred source hashes.
- Abort on unsuccessful compilation.
- Run applicable tests before installation.
- Back up the previous executable.
- Install the new executable atomically.
- Restart only after successful installation.
- Verify the service is active and running the expected executable.
- Verify management connectivity.
- Automatically restore the previous executable on a failed health check.

A command returning exit code zero is insufficient if an earlier step failed.

---

## 4. EXECUTION PHASE B — CORRECT THE RESPONSE/ACK STATE MACHINE

Inspect every data-session FSM transition.

A transition is valid only when supported by the correct response to the correct outstanding request, or by an explicitly documented asynchronous state event.

Implement robust correlation using available IPC identifiers, command identity, transaction sequencing and modem-specific response rules.

Ensure that:

- NET_REGIST events are not treated as successful registration merely because they arrived.
- Generic responses are associated with their originating commands.
- Nonzero results are decoded using vendor-confirmed semantics.
- Timeouts are distinguished from successful acknowledgements.
- Unsolicited modem notifications cannot advance unrelated FSM phases.
- Failed attach prerequisites prevent dependent data-call operations.
- Retry logic is bounded and respects backoff.
- Duplicate or delayed responses cannot corrupt state.
- Logs preserve sufficient context to reconstruct each transaction.

Add deterministic tests for these cases.

The FSM must distinguish:

`COMMAND_SENT`

`COMMAND_ACCEPTED`

`REGISTRATION_CONFIRMED`

`PS_ATTACHED`

`BEARER_ESTABLISHED`

`IP_CONFIGURED`

`CONNECTIVITY_VERIFIED`

These states must not be conflated.

---

## 5. EXECUTION PHASE C — RECOVER THE ACTUAL ATTACH PREREQUISITES

This is the highest-priority remaining implementation investigation.

The vendor library contains relevant routines including:

- `DataCallManager::DoAttach`
- `DataCallManager::TryAttach`
- `DataCallManager::OnPsAttachDone`
- `DataCallManager::DoSetInitialAttachApn`
- `ModemProxy::SetAttachApn`
- `ModemProxy::SetLteAttachProfile`
- `IpcTxSetLteAttachProfile`
- `IpcTxSyncProfileInfo`
- `IpcTxPsAttach`

Recover the real call chain.

Determine:

1. Which operations must occur before PS registration.
2. Whether an initial attach APN must be explicitly supplied.
3. Whether SetAttachApn uses an existing IPC command.
4. Whether SetLteAttachPdnList is required.
5. Whether SetLteAttachtype is required.
6. Which profile identifiers and CID values are expected.
7. Whether LTE attach profiles and data-call profiles must match.
8. Whether a particular command requires a preceding query.
9. Whether profile synchronization is failing because of missing initialization.
10. Whether registration is being attempted before the modem reaches the required state.

Use read-only static analysis of the actual vendor implementation, including internal call paths and virtual dispatch where necessary.

Do not rely on exported symbol names alone.

For every recovered wire command, document:

- Vendor function and binary build ID.
- Exact command family, main, sub and type.
- Payload size.
- Field offsets.
- Field semantics.
- Preconditions.
- Expected response.
- Evidence supporting the reconstruction.

Implement only verified commands.

Add byte-exact tests.

---

## 6. EXECUTION PHASE D — RECOVER REGISTRATION AND FAILURE CAUSES

Investigate the receive-side vendor implementations responsible for:

- NET_REGIST
- GPRS_PS
- GPRS_CALL_STATUS
- PDP context responses
- IP configuration
- GPRS backoff timer
- Relevant reject and status notifications

Determine the exact meaning of:

`ps=3`

`cs=1`

`call_state=3`

`pdp_state=0`

`gen_result=0/1/3`

The reported PS registration denial is an important finding, but identify whether it is caused by:

- An incomplete modem initialization sequence.
- An attach profile mismatch.
- A missing or incorrect APN.
- An unsupported PDP protocol.
- A radio access technology configuration issue.
- A modem-imposed backoff.
- A SIM/subscription/carrier restriction.
- A genuine network registration rejection.

Do not collapse these into a generic "carrier issue" diagnosis.

If the modem exposes an EMM/ESM reject cause, decode it against the appropriate specification and vendor implementation.

If no cause is exposed, state that explicitly.

Do not infer a backoff merely because the vendor library contains a backoff handler.

Do not repeatedly trigger attach requests while a backoff timer is active.

---

## 7. EXECUTION PHASE E — IMPLEMENT AND TEST THE CORRECTED LTE SEQUENCE

Once the actual prerequisites are established:

1. Implement the smallest complete vendor-supported attach sequence.
2. Keep all changes confined to the modem userspace integration unless a separate, verified prerequisite requires otherwise.
3. Preserve existing voice/SIM behavior.
4. Run unit tests, sanitizer tests and fuzzing.
5. Compare serialized frames against the vendor reference.
6. Deploy using the corrected fail-closed mechanism.
7. Verify the deployed binary and active process.
8. Capture live registration and attach responses.
9. Diagnose any failure and iterate.

Do not repeatedly retry the same unchanged sequence without new evidence.

Every failed iteration must produce a specific correction or a newly validated diagnostic result before another live attempt.

Avoid changing multiple independent modem settings in a single experiment unless the vendor reference proves they form one required sequence.

---

## 8. EXECUTION PHASE F — ESTABLISH THE CELLULAR BEARER

After successful PS registration and attach:

- Request the appropriate PDP/PDN context.
- Verify the modem reports successful data-call establishment.
- Identify the correct cellular network interface.
- Obtain or configure the IP parameters provided by the modem.
- Apply the appropriate address, prefix, gateway and DNS settings.
- Verify interface state and packet counters.
- Preserve existing management routing.
- Ensure cellular routing is explicitly selected for validation.
- Support the IP protocol actually negotiated by the modem.

Do not assume that `rmnet0` is necessarily the active bearer.

Inspect all supported cellular interfaces and select the one associated with the successful modem data call.

Do not synthesize an IP address, gateway or DNS server to manufacture apparent connectivity.

---

## 9. EXECUTION PHASE G — INDEPENDENT REAL-WORLD VALIDATION

Stage 06 may be marked PASS only when all of the following are independently verified on the physical device:

- [ ] Modem CP ONLINE.
- [ ] SIM READY.
- [ ] Valid PS registration.
- [ ] Successful PS attach or equivalent confirmed packet-service state.
- [ ] Successful cellular data-call establishment.
- [ ] A real cellular bearer interface is active.
- [ ] A modem-provided cellular IP configuration is installed.
- [ ] Cellular routing is functional.
- [ ] DNS resolution works through the cellular connection.
- [ ] HTTPS succeeds through the cellular connection.
- [ ] At least one independent connectivity test explicitly uses the cellular interface.
- [ ] Packet counters demonstrate actual cellular traffic.
- [ ] Wi-Fi/USB/ZeroTier are not carrying the supposedly cellular test.
- [ ] A controlled disconnect/reconnect restores the bearer.
- [ ] The service remains healthy after reconnection.
- [ ] No persistent corruption or regression is observed.
- [ ] The implementation and test results are committed and documented.

Use interface-bound tests, routing inspection and packet counters to prove the traffic path.

Do not disable the management network to prove cellular connectivity.

Prefer a dedicated routing table or network namespace for cellular tests when supported and safe.

A successful HTTPS request over Wi-Fi is NOT Stage 06 PASS.

A generic response of zero is NOT Stage 06 PASS.

A successful PDP command without an active bearer is NOT Stage 06 PASS.

A manually assigned cellular IP without actual packet connectivity is NOT Stage 06 PASS.

---

## 10. ITERATION AND AUTONOMY

You are expected to continue working through successive engineering iterations.

For each iteration:

**OBSERVE → IDENTIFY → IMPLEMENT → TEST → DEPLOY → VERIFY → CORRECT**

Prioritize actions that can change the functional outcome.

Do not spend an entire iteration rewriting documentation.

Do not stop at the first failed hypothesis.

Do not repeat previously disproven experiments without new evidence.

Do not broaden into unrelated hardware or Nuxel subsystems.

Use vendor reverse engineering as an implementation tool, not as an end in itself.

If a required external action cannot be performed autonomously, isolate that dependency precisely. Do not invent a workaround or silently assume it has been completed.

When a genuine blocker requires carrier intervention or a user-supplied configuration value, provide the exact minimum request and preserve all completed work.

---

## 11. REQUIRED DELIVERABLES

Maintain the following:

**A. Working implementation**

Production-ready modem source changes with regression tests.

**B. Live evidence**

Timestamped evidence of registration, attach, bearer establishment, IP configuration and cellular HTTPS.

**C. Safe deployment**

A repeatable, fail-closed deployment and rollback procedure.

**D. Documentation**

Update `mob.md` with the verified current state, changes, failure causes and actual test results.

**E. Git checkpoint**

Commit coherent, tested changes on the current feature branch.

Preserve unrelated modifications and do not force-push or rewrite history.

**F. Final verdict**

Use exactly one of:

`STAGE_06_PASS`

Only if every mandatory physical-device acceptance criterion passes.

`STAGE_06_NOT_YET_PASS`

If LTE data is still not established, including when a genuine external dependency prevents completion.

Never claim PASS because the source compiles, tests pass, the modem responds, or a report is complete.

---

## 12. START NOW

Begin with the actual repository and live device.

Do not produce another preliminary research plan.

Do not ask for permission to perform ordinary, reversible userspace engineering actions already authorized here.

Do not request another prompt between iterations.

Do not stop after producing a diagnostic report if a safe implementation path remains.

**Your first priority is to identify and implement the missing attach prerequisite or registration correction that actually changes the live PS registration result.**

Then establish the cellular bearer.

Then configure IP.

Then prove real cellular DNS and HTTPS.

Then test reconnection.

Then commit the finished work.

The mission is not complete until the physical device has verified working LTE mobile internet.

**EXECUTE. VERIFY. ITERATE. DELIVER.**

# OPERATION BOOMBATSCH — GO.ZZ

---

# STAGE 06 — LIVE EXECUTION LOG (OPERATION BOOMBATSCH) — appending, not overwriting

## VERIFIED BASELINE (timestamped 2026-11-23 ~20:39 CET, device root@10.11.12.99)

- CP: ONLINE (sysfs modem_state == ONLINE, ioctl code 4).
- SIM: present/READY (sim/ds_detect == 1; SEC_PIN_STATUS protocol-backed READY seen).
- Management connectivity (ZeroTier 10.11.12.99 + wlan0 + usb) independent of cellular — preserved.
- Deployed baseline daemon SHA-256: e50b9c820c97e0bdab9aad816c0b4cba9d4c5ad28fa706774b5d9a08d212df01.

## AUTHORITATIVE CORRECTIONS IMPLEMENTED (commit 454df1f3)

1. **NET_REGIST decode was WRONG.** The old code read payload[1]/[2] (query selector echo) and
   falsely reported "PS DENIED, CS REGISTERED". Correct field map recovered from
   IpcRxNetRegState @0x339818 (libsec-ril.so build 60889dd714394ae0db7c2ecc2bf2740f):
   payload[7]=RAT, payload[8]=NetServiceDomainType selector, payload[9]=RegState selector,
   payload[10]=reject cause. LIVE READBACK is now correct and consistent:
   `"ps":0,"ps_name":"NOT_REGISTERED","domain_sel":0,"domain":0,"reject":0`
   => the modem's data/PS registration is genuinely NOT-REGISTERED (state 0), NOT denied.
   Reject cause 0 => no EMM/ESM reject was reported.

2. **SetPdpContext layout was WRONG.** payload[0] was protocol, payload[1] was pdp_type, and cid
   was dropped. Correct (IpcTxSetPdpContext @0x31f6e0): payload[0]=pdp_type(3 EUTRAN/LTE),
   payload[1]=cid, flags@[2..5]=0x11 (APN|ACTIVATE), APN@[6..37]. Fixed byte-exact.

3. **GEN result FAIL-CLOSED.** Nonzero general-result byte (IpcRxGeneral payload[3]) is now a
   hard rejection for all setup phases. Exception (live-verified): SetMobileDataSetting
   (sub=29) returns result=3 idempotently ("mobile data already ON") — treated as already-configured.

4. **Minimal vendor attach sequence.** Removed SyncProfileInfo (sub=37, live result=1) and
   DefinePdpContext (sub=1, live result=1) — both rejected and NOT in vendor DoAttach. Added
   DS_PS_REGIST_VERIFY after PsAttach to gate data-call activation on a real NET_REGIST
   PS-attached state. LTE attach CID corrected to 5 (GetAttachCid @0x1e4500), distinct from
   DataProfile id 1 (ConvertProfileId).

5. SetLteAttachProfile payload[0]=3 is LIVE-VERIFIED (result 0 accepted); value 4 is
   REJECTED (result 1) — 3 is the correct apply-flag for beyond2lte.

## REMAINING BLOCKER (precise)

After a full, mostly-accepted attach sequence:
   SetServiceDomain(CS_PS=2) -> result 0
   SetPreferredNet(LTE auto 9) -> result 0
   SetMobileDataSetting -> result 3 (idempotent)
   SetDataProfile(APN "internet", IPV4V6) -> result 0
   SetLteAttachProfile(cid=5, flag=3, IPV4V6) -> result 0
   SetAlwaysOnPdn -> result 0
   PsAttach(attach=1) -> result 0
   GetDataRegState re-query -> RegState still 0 (NOT_REGISTERED), reject 0

The PsAttach is ACK-ed (GEN result 0) but the CP never moves PS/data registration off
NOT_REGISTERED(0). CS stays registered (RSSI heartbeat continues). There is no EMM/ESM
reject exposed on the data path (reject byte 0). This is NOT a carrier DENIED; it is an
incomplete/ineffective PS attach (missing prerequisite in the userspace sequence).

Next investigation targets (ranked, to be tested one at a time):
  A. Initial-attach APN via SetAttachApn state (IpcModem::SetAttachApn @0x2f1410 is a pure
     state-store; the CP must receive the initial attach APN through a yet-unverified wire path).
  B. DataProtocol: initial EPS attach bearer is IPv4 (wire 0x05), while the data PDN is
     IPV4V6 (0x04). Test IP for the attach profile.
  C. NET_POWERON_ATTACH (main=8 sub=9) power-on attach trigger.

No PASS is claimed. Verified daemon SHA-256 (current): e4aa6b27a94b8cc0d1fe794d8c5dd21699ac157df4222f966930a56b9047fb26.
