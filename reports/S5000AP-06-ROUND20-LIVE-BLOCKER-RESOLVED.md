# Stage 06 — Round 20: live decomposition of the remaining bearer blocker

**Branch:** cs/mob
**Date:** 2026-11-23 CET
**Device:** SM-G975F / beyond2lte / S5000AP, working SIM seated (T-Mobile NL 20416)

## Verdict

STAGE_06 still NOT_PASS. This round PROVES the remaining blocker is not a Nuxel
serialization defect and pinpoints the exact modem-side failure: the modem
accepts every byte-exact data-path command (GEN result 0) EXCEPT the one that
sets the initial-attach APN at runtime, and it rejects every re-attach trigger.

## New evidence (this round, live)

Verified byte-exact against on-device vendor disassembly and live-tested each
independently-justified candidate on the physical modem:

| Candidate | Result |
|---|---|
| SetLteAttachProfile flag=4 ("apply" per csinc) | GEN reject 1 (flag=3 is correct) |
| DefinePdpContext (main=13 sub=1) in FSM | GEN reject 1 (legacy 3G) |
| PS_DETACH reason=4 (DoDetachForIA) | GEN reject 1 |
| PS_DETACH reason=6->wire-0 (DoGprsDetach) | GEN reject 1 |
| SyncProfileInfo (main=13 sub=37) un-skip | GEN reject 1 |
| APN internet/smartsites/t-mobile/web.nl | GPRS_CALL_STATUS state=3 (all) |

## Precise root cause (now evidence-locked)

The default EPS bearer in LTE is established during the INITIAL ATTACH using the
"initial-attach APN". Nuxel sets this via the ONLY two runtime paths available on
this S5000AP:

1. `SetLteAttachProfile` (main=13 sub=20) — ACCEPTED (GEN 0), but it does NOT
   trigger a re-attach, so the already-registered modem never applies it to the
   default bearer.
2. `SyncProfileInfo` (main=13 sub=37, the `SetAttachApn` transmit path per
   IpcModem::SetAttachApn @0x2f1410 caching + IpcModem::SyncProfileInfo @0x2f1518)
   — REJECTED (GEN 1). This is the only command that pushes the attach APN to the
   modem's runtime default-bearer config.

Consequently the modem stays PS REGISTERED_HOME with NO default EPS bearer, every
`SetPdpContext` (sub=4, ACTIVATE) is accepted but answered GPRS_CALL_STATUS
state=3, and GPRS_IP_CONFIGURATION never arrives; rmnet0..7 stay DOWN.

## Vendored confirmation of sender identity

- `IpcModem::SetAttachApn` @0x2f1410 is a CACHING setter (stores APN at object
  +0x9c/+0x101/+0x165; returns 0 without transmitting). It is NOT the wire cmd.
- `IpcModem::SyncProfileInfo` @0x2f1518 allocates an IpcHistory transaction and
  dispatches to IpcTxSyncProfileInfo (sub=37) — this is the actual transmit of the
  cached attach APN. Its live rejection (GEN 1) is the definitive blocker.

## Exact requirement (awaiting owner authorization)

The remaining action is NOT a serialization change. The modem's runtime attach-APN
cannot be updated because SyncProfileInfo (sub=37) is rejected and no detach/
reattach is accepted. Resolving it requires one of:

1. Owner-authorized persistent modem configuration (NV/EFS initial-attach APN =
   "internet" for PLMN 20416), which mob.md forbids without explicit approval; OR
2. A carrier-side data-service check (the SIM's data plan/provisioning for this
   device); OR
3. An owner-authorized CP power-cycle so the modem re-reads its attach APN after
   SetLteAttachProfile, then re-registers with a default bearer.

No NV/EFS/RADIO/BOOT/IMEI/firmware write was performed. RADIO sda16 and BOOT sda8
hashes remain unchanged.

## Safety

RADIO sda16 = 9ffa1426a4ef7d1187779a14f22ec4b8cb4c2ab473b6626304a77030d9966fc7 (UNCHANGED)
BOOT  sda8  = 2daeb1f36095b44b318410b3f4e8b5d989dcc7bb023d1426c492dab0a3053e74 (UNCHANGED)
Wi-Fi wlan0 10.20.30.16 UP, ZeroTier 10.11.12.99 UP, USB/SSH intact.
Deployed binary a9506c24ee2eb8063028a6047b9684c787bde26ccba9d4ff58328b792668bc43 (unchanged round-19 baseline).
