# Stage 06 — Round 21: independent full-symbol differential + live re-confirmation

**Branch:** cs/mob
**Date:** 2026-11-23 CET
**Device:** SM-G975F / beyond2lte / S5000AP, working SIM seated (T-Mobile NL 20416)

## Verdict

STAGE_06 still NOT_PASS. This round adds an independent, full-symbol-table
differential against the pinned vendor RIL (`.vendor-ro/libsec-ril.so`,
GNU Build ID 60889dd714394ae0db7c2ecc2bf2740f) and re-confirms the bearer
blocker on a freshly-booted CP. The blocker is NOT a Nuxel serialization or
sequencing defect; it is upstream of Nuxel (modem persistent initial-attach APN
or carrier data-service provisioning).

## New evidence this round (live + static)

1. Live re-confirmation on a post-reboot CP (uptime ~10 min, CP freshly ONLINE):
   full data-session FSM completes; every prerequisite is GEN-accepted (result 0);
   PS REGISTERED_HOME (domain_sel=3 => PS_ONLY, reject=0); DATA_CALL
   (SetPdpContext sub=4) is GEN-accepted (result 0) but answered
   `GPRS_CALL_STATUS 010300000000000000` = cid1 state3 (NOT connected), pdp_state 0,
   no ESM cause. rmnet0..7 stay DOWN. Deployed binary
   `a9506c24ee2eb8063028a6047b9684c787bde26ccba9d4ff58328b792668bc43` (unchanged).

2. Full dynamic-symbol table recovered from the stripped vendor RIL (`.dynsym`
   is populated; prior rounds only had partial offsets). This enabled exact,
   independent verification of every data-path serializer AND the stub surface:

   - `DataCallManager::DoSetInitialAttachApn @0x22bad8` calls
     `ModemProxy::SetAttachApn` (userspace cache) THEN
     `DataCallManager::SetLteAttachProfile @0x22b518` (wire sub=20).
     This is the exact sequence Nuxel's DS_SET_LTE_ATTACH already emits.
   - `IpcProtocol41::IpcTxSetLteAttachProfile @0x320238`: `flag & 1` selects
     payload[0] == 3 (apply) else 1 (define); the odd-flag 1/3 both select 3.
     Nuxel payload[0]=3 (attach_flag=3) is byte-exact correct.
   - `IpcTxNetSetServiceDomain @0x336dc8` maps NetServiceDomainType
     {1=>4, 2=>2, 3=>1} on the wire. Nuxel's `fmt_tx_set_service_domain` sends
     domain 2 => wire 2 (CS_PS), which IS correct for the current CS_PS call.
     (Latent bug noted: Nuxel's helper maps 1=>1 and 3=>3, which differs from the
     vendor 1=>4 and 3=>1; it does NOT affect the CS_PS=2 path in use.)

3. **Stub surface definitively confirmed (independent).** `IpcModem::` implements
   the following as `mov w0,#0xffffffff; ret` (return -1, no wire transmit):
   - `SetLteAttachtype @0x30dd48`
   - `SetLteDataRetry @0x30dd50`
   - `GetLteAttachPdnList @0x30dd58`
   - `SetLteAttachPdnList @0x30dd60`
   This independently confirms Round 20: there are exactly TWO runtime LTE-
   attach wire paths on this S5000AP — `SetLteAttachProfile` (sub=20, accepted
   but no re-attach) and `SyncProfileInfo` (sub=37, rejected). No hidden
   "attach type" or "attach PDN list" command exists.

4. No runtime read-back of the persistent initial-attach APN exists over FMT:
   `ModemProxy::GetAttachApn @0x1ce3f8` / `IpcModem::GetAttachApn @0x2f1310`
   return the userspace CACHE only (no `IpcTxGetAttachApn` wire command).

## Precise root cause (re-confirmed)

The modem's persistent initial-attach APN (NV/EFS) is not "internet" for
PLMN 20416, so the default EPS bearer is never established during LTE attach.
On an already-registered modem no runtime command can update it:
SetLteAttachProfile is accepted but does not re-attach; SyncProfileInfo is
rejected; the attach-type/PDN-list commands are stubs; there is no read-back.

## Exact requirement (awaiting owner authorization / external check)

Resolving the bearer requires ONE of:
1. Owner-authorized persistent modem configuration (NV/EFS initial-attach APN =
   "internet" for PLMN 20416). mob.md §6 forbids this absent explicit approval.
2. A carrier-side data-service/provisioning check for this SIM/device.
3. An owner-authorized CP power-cycle timed AFTER `SetLteAttachProfile` so the
   modem re-reads the runtime-set attach profile before re-registration.

No NV/EFS/RADIO/BOOT/IMEI/firmware write was performed. RADIO sda16 and BOOT sda8
remain unchanged. Voice registration and all management links (Wi-Fi, ZeroTier,
USB, SSH) remain intact throughout.

## Safety

RADIO sda16 = 9ffa1426a4ef7d1187779a14f22ec4b8cb4c2ab473b6626304a77030d9966fc7 (UNCHANGED)
BOOT  sda8  = 2daeb1f36095b44b318410b3f4e8b5d989dcc7bb023d1426c492dab0a3053e74 (UNCHANGED)
Wi-Fi wlan0 10.20.30.16 UP; ZeroTier 10.11.12.99 UP; USB 10.100.10.1 UP; SSH intact.
Deployed binary a9506c24… (unchanged from round-19/20 baseline).

## Round-21 additional decisive insight (timing proof)

Live boot-journal timing on the current boot proves the runtime attach-profile
path CANNOT work, not even with a CP power-cycle:

- radiod starts                    22:47:29
- PS REGISTERED_HOME first observed 22:47:34  (~5 s after CP ONLINE)
- DS_SET_LTE_ATTACH (SetLteAttachProfile sub=20) sent 22:48:44 (≈75 s later)

The modem auto-registers to LTE/PS within ~5 s of CP ONLINE, while the data-
session FSM only reaches the attach-profile command after ~75 s of prerequisite
commands (service-domain, preferred-net, mobile-data, set-data-profile). Because
the vendor confirms the initial-attach APN is applied ONLY during initial attach,
and SetLteAttachProfile does NOT trigger a re-attach on an already-registered
modem, the runtime command can never be applied in time.

This rules out Round-20 option #3 (CP power-cycle): even a fresh CP boot would
register in ~5 s, before any userspace attach-profile command could land. The
remaining resolution is therefore strictly one of:
  (a) persistent NV/EFS initial-attach APN = "internet" (owner-authorized), or
  (b) carrier-side data-service provisioning for this SIM/device.
