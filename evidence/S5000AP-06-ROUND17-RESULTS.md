# Stage-06 Round 17 — Authoritative protocol correction + live validation

Date: 2026-11-23 (Europe/Amsterdam)
Branch: cs/mob
Commit: 6aca39e6
Deployed binary SHA256: 9f12323ef2b53879f08e383365b7564c778735c85db8aa845d2b07bcdd1f624a

## Result: STAGE_06_NOT_YET_PASS

PS registration is now REGISTERED_HOME. The default EPS bearer still does NOT
establish: GPRS_CALL_STATUS reports call_state=3 (authoritatively "not
connected", IpcRxGprsCallStatus @0x321ab0), pdp_state=0, no cause code.

## What was definitively corrected (source-backed, live-verified)

All from authoritative AArch64 disassembly of
/tmp/vendor-ro/lib64/libsec-ril.so (build 60889dd714394ae0db7c2ecc2bf2740f).

1. GetAttachCid() @0x1e4500 — returns 5 ONLY for model_type==1 (dual-sim);
   returns 1 for model_type 0 or >=2. Device is single-SIM (_EUR0), so
   DS_ATTACH_CID corrected 5 -> 1.

2. IpcTxSetAlwaysOnPdn(bool, DataProfile, int) @0x321550 — wire payload[1] is
   the int argument DoAlwaysOnPdn() supplies as 1, NOT the attach CID and NOT
   the DataProfile. Corrected payload[1] 5 -> 1.

3. IpcTxSetLteAttachProfile @0x320238 with caller DataCallManager::
   SetLteAttachProfile @0x22b518 — wire payload[1] is the vendor-hardcoded
   profile-selector int (=1), NOT the attach CID. Corrected.

4. Confirmed byte-exact (unchanged, now verified):
   - IpcTxSetPdpContext @0x31f6e0 (112-byte activate): payload[0]=pdp_type=3
     (LTE/EUTRAN), payload[1]=cid, flags=0x11, APN@6, auth@102, proto@104.
   - IpcTxDefinePdpContext @0x31f580 (134B, sub=1): payload[0]=1, cid@1,
     proto@2, APN@3. This is legacy-3G; the CP rejects it (gen=1), and the
     vendor uses SetPdpContext(sub=4) for LTE define+activate in one command.
   - IpcTxSetDataProfile, IpcTxSyncProfileInfo, IpcTxPsAttach,
     IpcTxSetDataCallEstablish, IpcTxGetPdpContext.

## Live sequence (deployed 9f12323e)

NET_REGIST_CHECK: ps=1 REGISTERED_HOME (voice+PS registration OK)
SET_SERVICE_DOMAIN(8/8=2): gen=0 accepted
SET_PREFERRED_NET(8/10=9): gen=0 accepted
ENABLE_MOBILE_DATA(13/29): gen=3 (already-ON)
SET_DATA_PROFILE(13/27): gen=0 accepted
SET_LTE_ATTACH(13/20, flag=3): gen=0 accepted
ALWAYS_ON_PDN(13/34): gen=0 accepted
PS_ATTACH(13/3): gen=0 accepted
PS_REGIST_VERIFY: ps=1 REGISTERED_HOME
DATA_CALL SetPdpContext(13/4): gen=0 accepted
-> GPRS_CALL_STATUS(13/16): payload 01 03 00 00 00 00 00 00 00
   cid=1 (echoed), call_state=3 (NOT connected), pdp_state=0, no cause

## Hypotheses tested and DISPROVEN this round

- flag=1 "initial attach APN" via SetLteAttachProfile: GEN result 4 (rejected).
  flag=3 "set profile" is the correct/accepted value.
- DefinePdp(sub=1) re-enable: GEN result 1 (rejected). Legacy 3G; correctly skipped.
- SetLteAttachPdnList / SetLteAttachtype: these are STUBS in the vendor
  (IpcModem::* return -1); not real wire commands, not the missing prerequisite.

## Remaining hypotheses (unresolved)

1. Carrier/SIM data provisioning or network-side ESM rejection with no AP-facing
   cause code. mob.md Phase D: verify the SIM has working data in a known-good
   phone. This is a genuinely external check.
2. APN ("internet") or protocol (IPv4v6) mismatch for Odido NL (PLMN 20416).
3. The PS attach reported REGISTERED_HOME may be LTE-in-idle without the
   default EPS bearer being requested because the always-on-PDN / default
   bearer selector differs from the values tested.

## Safety / rollback

- Deployed binary 9f12323e... replaced prior 37c90ab5...; rollback copies
  preserved in /usr/libexec/nuxel/nuxel-radiod.bak.*.
- No firmware/NV/EFS/DT/partition writes. WiFi (wlan0), USB (usb0), ZeroTier
  management all preserved.
- No IMSI/ICCID/IMEI/MSISDN logged.
