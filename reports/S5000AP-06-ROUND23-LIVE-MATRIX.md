# Stage 06 — Round 23: live wire-byte + dwell differential (both disproven)

**Branch:** cs/mob
**Date:** 2026-11-24 CET
**Device:** SM-G975F / beyond2lte / S5000AP, T-Mobile NL 20416 SIM seated

## Verdict

STAGE_06 NOT_PASS. Two independently-justified candidates were deployed and
live-tested this round; both are now DISPROVEN with direct modem evidence.

## Test 1: SetPdpContext payload[0] wire-byte correction

New disassembly (Round-22 report) showed the base IpcTxSetPdpContext @0x31f6e0
selects payload[0] via a jump table (@0x149806), NOT the hardcoded "3" that
Nuxel emitted. Added NUXEL_PDP_TYPE runtime selector and tested:

| payload[0] | meaning | GPRS_CALL_STATUS |
|-----------|---------|------------------|
| 3 (prior) | legacy   | state 3 (not connected) |
| 1 (full APN+flags) | full path | state 3 |
| 4 (LTE simple) | LTE/non-APN | state 3 |

All three produce the IDENTICAL `010300000000000000` (cid=1, state=3, cause=0).
The wire byte is NOT the blocker.

## Test 2: receive-path dwell (mob.md §4.5)

Hypothesis: state 3 is a TRANSIENT idle that later transitions to state 1
(connected), and the FSM was prematurely rejecting before that transition.

Added a bounded 5-second dwell: on state 3 during DS_DATA_CALL, hold the phase
and watch for a late state 1/10/11 transition.

LIVE RESULT: `data_call_observing call_state=3` logged; NO subsequent
GPRS_CALL_STATUS ever arrives (no state 1/10/11, no IP_CONFIGURATION) within the
full dwell window. The modem sends state 3 ONCE and stays there.

CONCLUSION: state 3 is the final, persistent "not connected" state. There is NO
missed transition. The receive path is correct; the bearer genuinely never
establishes.

## Test 3: SyncProfileInfo (sub=37) live re-confirmation

Re-enabled the sync-profile phase in the FSM to independently re-test the
attach-APN transmit command. LIVE RESULT: GEN result 1 (rejected), consistent
with prior rounds. The modem rejects SyncProfileInfo regardless of payload.

## Cumulative evidence (rounds 22-23)

- DoSetInitialAttachApn @0x22bad8 is a 68-byte STUB (returns 0; no wire cmd),
  refuting Round-21's central claim.
- Real LTE path is LteEpdgDataCallManager::DoSetupDataCall @0x28d0a8 (derived).
- IpcModem::ActivatePdpContext @0x2f1be8 forwards (cid, PdpActDeactState, apn,
  user, auth, proto) to a virtual IpcTxSetPdpContext at vtable offset 528.
- Two serializers exist: base @0x31f6e0 and Iil @0x357488 (different layouts).
- payload[0] ∈ {1,3,4} all yield state 3.
- No state 1/10/11 transition ever observed (dwell disproves transient theory).
- SyncProfileInfo (sub=37) always GEN-rejected (result 1).

## Remaining (unproven) hypotheses

(a) Modem persistent initial-attach APN (NV/EFS) not "internet" for PLMN 20416,
    so the default EPS bearer never attaches -> SetPdpContext has no default
    bearer to activate against. mob.md §6 forbids writing NV/EFS without
    explicit owner authorization.
(b) Carrier-side data-service/provisioning for this SIM/device.
(c) An as-yet-unidentified initialisation step the vendor performs that Nuxel
    does not (the concrete object is LteEpdgDataCallManager, not ModemProxy).

## Safety

No NV/EFS/RADIO/BOOT/IMEI/firmware write. RADIO sda16 and BOOT sda8 unchanged.
Wi-Fi wlan0 UP, ZeroTier 10.11.12.99 UP, USB/SSH intact. Deployed binary backups
retained under /usr/libexec/nuxel/nuxel-radiod.bak.*.
