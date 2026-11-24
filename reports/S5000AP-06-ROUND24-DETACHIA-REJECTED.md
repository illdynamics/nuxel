# Stage 06 — Round 24: detach-for-initial-attach is REJECTED (conclusive)

**Branch:** cs/mob
**Date:** 2026-11-24 CET
**Device:** SM-G975F / beyond2lte / S5000AP, T-Mobile NL 20416

## Verdict

STAGE_06 NOT_PASS. The final remaining software candidate — the vendor's
"detach for initial attach" (`DoDetachForIA`) — is REJECTED by this modem.

## New finding: the real SetInitialAttachApn path

This round resolved the mob.md §3 hint ("resolve indirect calls using their
actual concrete object types"). The BASE `DataCallManager::DoSetInitialAttachApn
@0x22bad8` is a 68-byte STUB, but the DERIVED override exists:

- `LteEpdgDataCallManager::DoSetInitialAttachApn @0x28c6c8` (0x7c0 bytes) is the
  REAL function. It builds a DataCallSetup, calls `ModemProxy::GetAttachApn`
  (cached), checks `IsSkipDetach`/`CheckProfileZero`/`IsEqual`, `DoSyncPhoneType`,
  and ends with `DataCallManager::DoDetachForIA @0x22bdf0`.

- `DoDetachForIA @0x22bdf0` calls `PsAttach` (vtable 704) with
  `DataDetachReason=4` ("detach for initial attach"). Wire serializer is
  `IpcProtocol41::IpcTxPsAttach @0x31fa98`:
    payload[0]=attach(1)/detach(0), payload[1]=suspend, payload[2]=reason(0..4).

So the vendor's complete IA-APN application sequence is:
  SetAttachApn (cache) -> SetLteAttachProfile (wire sub=20) -> DoDetachForIA
  (PsAttach detach reason=4) -> OnPsDetachDone -> re-attach (default bearer).

## Live test (correct in-sequence position)

Added a DS_DETACH_IA phase AFTER SetLteAttachProfile + SetAlwaysOnPdn, emitting
`fmt_tx_ps_attach(false, false, 4)` (detach, reason=4).

LIVE RESULT: `data_session_reject_gen phase=DETACH_IA gen_result=1`
(GEN result 1 = command rejected by the CP).

## Cumulative conclusion (rounds 22-24, all live)

Every runtime path to (re)apply the modem's initial-attach APN is rejected:

| Command | Wire | Result |
|---|---|---|
| SetLteAttachProfile | main=13 sub=20 | GEN 0 (accepted), no re-attach |
| SyncProfileInfo | main=13 sub=37 | GEN 1 (rejected) |
| PsAttach(detach, reason=4) | main=13 sub=3 | GEN 1 (rejected) |
| DefinePdpContext | main=13 sub=1 | GEN 1 (rejected, legacy 3G) |
| SetPdpContext (ACTIVATE) | main=13 sub=4 | GEN 0, GPRS_CALL_STATUS state=3 (not connected), cause=0 |

The modem is PS REGISTERED_HOME (reject=0) but never establishes the default EPS
bearer. GPRS_CALL_STATUS state 3 is final (no state 1/10/11 transition observed
even with a 5s receive dwell). SetPdpContext payload[0] ∈ {1,3,4} all yield
state 3.

## Precise root cause (now exhaustively evidence-locked)

The default EPS bearer is established from the modem's PERSISTENT initial-attach
APN during initial attach. That APN is NOT "internet" for PLMN 20416, so no
default bearer forms. There is NO userspace/runtime command on this S5000AP that
can update or re-trigger the initial-attach APN (all five paths above rejected
or non-effectual). This is a modem NV/EFS (persistent) configuration, or a
carrier-side data-service provisioning issue.

## Exact requirement (owner authorization needed)

Per mob.md §6, NO NV/EFS write may be attempted without explicit owner
authorization. Resolving the bearer requires ONE of:
1. Owner-authorized one-time persistent modem configuration: set the initial-
   attach APN to "internet" for PLMN 20416 (NV/EFS), OR
2. Carrier-side data-service/provisioning confirmation for this SIM/device
   (verify the T-Mobile NL 20416 data plan is active and the IMEI/device is
   allowed data), OR
3. A known-good Android/vendor RIL trace for the SAME hardware to diff against
   (none exists in-repo).

## Safety

No NV/EFS/RADIO/BOOT/IMEI/firmware write. RADIO sda16 and BOOT sda8 unchanged.
Wi-Fi/ZeroTier/USB/SSH intact. Rollback binaries retained under
/usr/libexec/nuxel/nuxel-radiod.bak.*.
