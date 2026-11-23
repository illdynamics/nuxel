# S5000AP Stage-06 — Continuation checkpoint (round 9, 2026-11-23 ~19:00 CET)

## Verdict
`STAGE_06_NOT_YET_PASS — data-call sequence live-verified but no bearer; SetDataProfile tail-fields and GEN result semantics unresolved`

## Git
- Branch `cs/mob`, HEAD `7662c1e3`.
- This round committed 4 coherant milestones (see git log).

## LIVE hardware evidence (this session, VERIFIED)
- CP ONLINE (kernel sysfs `/sys/devices/platform/10000.mif_pdata/modem_state`).
- SIM present (`sim/ds_detect=1`); prior rounds verified SEC_PIN_STATUS=READY + USIM + serving PLMN 20416 (T-Mobile NL).
- RADIO /dev/sda16 SHA256 UNCHANGED = `9ffa1426a4ef7d1187779a14f22ec4b8cb4c2ab473b6626304a77030d9966fc7`.
- Wi-Fi (wlan0 10.20.30.16) + USB (usb0 10.100.10.1) + ZeroTier preserved throughout.
- mmcli -L still "No modems were found" (native SIPC path is the active radio transport).

## Huge progress this round (all source-backed O5, live-verified)
1. Recovered exact DataProtocol wire bytes from IpcTxDefinePdpContext @0x31f580:
   wire = (0x00040605 >> ((proto-2)*8)) & 0xff  => IP(2)=0x05, IPV6(3)=0x06,
   IPV4V6(4)=0x04. Fixed the stale 0x60/0x06 mapping + enum (0/1/2 -> 2/3/4).
2. Recovered the complete data-path command map (--dyn-syms authoritative):
   DefinePdpContext@0x31f580 (main13/sub1/134B), GetPdpContext@0x31f928 (13/4),
   PsAttach@0x31fa98 (13/3/10B), SetDataProfile@0x31ff48 (13/**27**/203B),
   SetLteAttachProfile@0x320238 (13/**20**/201B), SetDataCallEstablish@0x320a10
   (**3/2**/8B), SetMobileDataSetting@0x3214c8 (13/29/9B), SetAlwaysOnPdn@0x321550
   (13/**34**/9B). Corrected cmdmap's stale sub-27 name (it is SET_DATA_PROFILE;
   sub=34 is the true SET_ALWAYS_ON_PDN).
3. LIVE-VERIFIED the FULL data-session command sequence now executes on hardware:
   mobile-data(29) -> SetDataProfile(27) -> DefinePdp(1) -> AlwaysOnPdn(34) ->
   PsAttach(3) -> DataCallEstablish(3/2). Each command is ACKNOWLEDGED by the CP
   via a GEN echo response.
4. DISCOVERED the response-correlation mechanism: the CP replies to every data
   command with `main=128 (GEN) sub=1 type=2 plen=5`, payload `[echo_main][echo_sub]
   [echo_type][seq?][result]`. Example (DefinePdp): `0d01030180`. Fixed the
   correlator + a latent `wrote_phase` reset bug so the FSM actually advances.

## Genuine remaining blocker (honest)
- After DataCallEstablish the CP returns result byte `0x80` (uniform across all 6
  commands) and NO GPRS IP-config / PDP-context / call-status response follows;
  rmnet0..7 stay DOWN. Either (a) 0x80 == generic failure because the carrier
  data profile is incomplete, or (b) additional steps (SetLteAttachProfile sub=20,
  or a get-data-call-list query) are required before the bearer is granted.
- SetDataProfile(203B) is a PARTIAL reconstruction: APN offset 22, auth offset 0,
  protocol offsets 21+188 are source-verified; profile-name (payload 1..20) and
  tail halfwords (payload 190..195) are zero-filled because their enum/region
  selects are not yet decoded. This is the most likely reason the CP rejects the
  profile (0x80) and never brings up a bearer.

## Exact next action (no speculation)
1. Disassemble IpcTxSetDataProfile tail (IpcRxGeneral @0x32b0f0 result handling +
   the `iii` int params at x29+16/24/32) to complete the 203-byte profile.
2. Add SetLteAttachProfile (main13/sub20/201B) to the attach sequence.
3. Re-test: data-call then OBSERVE a non-0x80 result + incoming GPRS_IP_CONFIGURATION
   (sub=9) / CALL_STATUS (sub=16), then bring up the correct rmnet interface.

## Safety
- No protected-partition write; RADIO hash unchanged; no DT/EFS/NV/IMEI/ICCID/
  IMSI/PIN/PUK captured; no speculative malformed frames (all TX byte-exact vs
  disassembly); bounded retries; Wi-Fi/USB management preserved.
