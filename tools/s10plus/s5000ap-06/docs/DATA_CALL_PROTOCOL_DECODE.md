# S5000AP Stage-06 — Complete decoder findings (GEN result + SetDataProfile + SetLteAttachProfile)

## GEN response semantics (DECODED)
Live GEN response format (main=128, sub=1, type=2, plen=5):
  [echo_main][echo_sub][echo_type][seq][result]
Observed uniformly after every data-path command:
  0d1d030380  -> main=13, sub=29, type=3, seq=3, result=0x80  (mobile data)
  0d1b030180  -> main=13, sub=27, type=3, seq=1, result=0x80  (set data profile)
  0d01030180  -> main=13, sub=1,  type=3, seq=1, result=0x80  (define pdp)
  0d22030080  -> main=13, sub=34, type=3, seq=0, result=0x80  (always on pdn)
  0d03030080  -> main=13, sub=3,  type=3, seq=0, result=0x80  (ps attach)
  0302030380  -> main=3,  sub=2,  type=3, seq=3, result=0x80  (data call establish)

The result byte 0x80 is UNIFORM across all commands (including mobile-data which
provably produced a valid NET_REGIST follow-up). Conclusion: 0x80 is the
Samsung "generic completion/ACK" marker (command accepted, processing), NOT a
failure. It is NOT success-by-itself either: a following data-plane response
(GPRS_IP_CONFIGURATION / CALL_STATUS / NET_REGIST) is required to prove the
command actually took effect.

## SetDataProfile (IpcTxSetDataProfile @0x31ff48) FULL 203-byte layout
Signature (mangled): IpcProtocol41::IpcTxSetDataProfile(
    const char* apn, const char* user, const char* pass,
    DataAuth auth, DataProtocol proto, DataProfile profile,
    bool enable, PcscfViaPco pco, int a, int b, int c)

Implicit this = x0, so:
  x0=this(frm base), x1=apn, x2=user, x3=pass, w4=auth, w5=proto,
  w6=profile(enum idx), w7=enable(bool), stack=pco,a,b,c

Frame header (7 bytes): total=203(0xcb), msg_seq=0, ack_seq=0, main=13(0x0d),
sub=27(0x1b), type=3(0x03).
Payload = 196 bytes at payload[0]=frame[7].

  payload[  0] = auth code (helper @31fe28 returns 1 for "none", region-dep)
  payload[1..20] = profile name (DataProfile enum -> 20-char NUL-padded)
  payload[ 21] = protocol byte: 0x00040605 >> ((proto-2)*8)  [IP=2->0x05,
                 IPV6=3->0x06, IPV4V6=4->0x04; proto-2>=3 -> fallback 0x02]
  payload[22..122] = APN (101 bytes NUL-padded)
  payload[123..154] = username (32 bytes NUL-padded)
  payload[155..186] = password (32 bytes NUL-padded)
  payload[187] = auth flag: 0x00010201 >> ((auth-1)*8), 0 if auth-1>=3
  payload[188] = protocol byte 2nd copy (special-cased when pco==1)
  payload[189] = pco flag: (~pco)&1
  payload[190..191] = halfword int a (PcscfViaPco-related, default 0)
  payload[192..193] = halfword int b (default 0)
  payload[194..195] = halfword int c (default 0)

For a plain "no-auth, IPV4V6, internet" profile:
  payload[0]=1 (auth none), protocol=0x04 at [21]+[188],
  auth flag at [187]=0 (auth-1=0, shifted 0x01... wait auth=0 -> auth-1 = -1)
  -> correctly must use auth enum numeric: NONE likely = a specific value.

## DataAuth enum (from helper @31fe28 switch)
The helper IpcTxSyncProfileInfo+0x2e0 (31fe28) maps DataAuth -> code:
  input w0 (DataAuth). Returns:
    <= 0x3ea and > 3, region-dependent: 3 (NTC) or 1 (other)
    == 0x3eb -> 11
    == 0x3ec -> 5
    == 0x3ee -> region-dependent 3 or 1
    default -> 1 (with android log "unknown auth")
So DataAuth::NONE == some value that returns **1**. For our no-auth profile,
auth code = 1.

The 0x00010201 pattern for payload[187] maps:
  auth-1 = 0 -> 0x01 (PAP?), but this is the SAME enum index. Given NO_AUTH
  maps to code 1, the flag byte should be 1.

## SetLteAttachProfile (IpcTxSetLteAttachProfile @0x320238) 201-byte layout
Signature: IpcProtocol41::IpcTxSetLteAttachProfile(
    u8 cid, const char* apn, const char* user, const char* pass,
    DataAuth auth, DataProtocol proto, RadioTechnologyType rat,
    PcscfViaPco pco, u8* a, u8* b, bool enable)

Frame: total=201(0xc9), main=13(0x0d), sub=20(0x14), type=3.
Payload = 194 bytes:
  payload[0] = flag (3 or 4, csinc on bool enable)
  payload[1] = cid (u8, first arg)
  payload[2] = protocol byte (0x00040605 pattern)
  payload[3..103] = APN (101 bytes)
  payload[104..135] = username (32 bytes)
  payload[136..167] = password (32 bytes)
  payload[168] = auth flag
  payload[169..] = pco flag + tail halfwords

## Root cause of no-bearer
The data-session sequence ACKs every command (0x80=generic ACK) but produces no
IP config. Two probable causes:
  1. SetDataProfile tail fields (187..195) were zero-filled (now decoded above).
  2. SetLteAttachProfile (sub=20) is MISSING from the attach sequence — required
     for LTE PS attach to be accepted by the CP.

## ROOT CAUSE: SetDataCallEstablish is the WRONG command for LTE
The LTE data activation uses IpcTxSetPdpContext (main=13, sub=4, type=3, 112-byte)
to ACTIVATE a PDP context, NOT the CDMA SetDataCallEstablish (main=3, sub=2).
The sequence should be:
  mobile-data(29) -> SetDataProfile(27) -> SetLteAttachProfile(20) ->
  DefinePdpContext(1) -> AlwaysOnPdn(34) -> PsAttach(3) -> SetPdpContext(4, ACTIVATE)
The SetDataCallEstablish (CDMA main=3) is unneeded for the LTE/GPRS bearer.

## IpcTxSetPdpContext (0x31f6e0) FULL decode
Signature: SetPdpContext(u8 cid, int pdp_type, const char* apn, const char* user,
                         int auth, int pdp_act_deact)
Frame: total=112(0x70), main=13(0x0d), sub=4(0x04), type=3.
Payload = 105 bytes:
  payload[0]     = pdp_type wire code (from 8-entry jump table; see below)
  payload[1]     = cid (u8)
  payload[2..5]  = flags word (bit0=apn, bit1=user, bit4=ACTIVATE)
  payload[6..37] = APN (32 bytes NUL-padded)
  payload[38..69] = username (32 bytes)
  payload[70..101] = password (32 bytes)
  payload[102]   = auth flag (0x00010201 >> ((auth-1)*8))
  payload[103]   = reserved (0)
  payload[104]   = protocol/tech byte

pdp_type wire code table (from jump table @31f760):
  0 -> (default, full path w/ apn) code=1
  code 7 = (some LTE variant)
  code 4 = IPV6?
  code 2 = IPV4?
  code 3 = IPV4V6?
  code 1 = "full" (apn+user present)
  code 5 = ...
  code 6 = ...
  code 8 = ...
For a standard "internet" IPV4V6 no-auth attach, the vendor emits the
"full" path: pdp_type code=1, flags=0x11 (apn + activate), auth=0.

The ACTIVATE bit: `orr w8, w22, #0x10` where w22 = flags (bit0/bit1 for
apn/user presence). pdp_act_deact != 0 => bit4 (0x10) set = ACTIVATE.
pdp_act_deact == 0 => bit4 clear = DEACTIVATE.

## Live results this session (2026-11-23 ~19:xx CET)

Full corrected data-session sequence now executes on hardware and ACKs:
  SyncProfileInfo(sub=37,326B) -> SetDataProfile(sub=27,203B) ->
  SetLteAttachProfile(sub=20,201B) -> DefinePdpContext(sub=1,134B) ->
  AlwaysOnPdn(sub=34,9B) -> PsAttach(sub=3,10B) ->
  SetPdpContext(sub=4,112B ACTIVATE) -> GetPdpContextList(sub=4,type=2)

CP responses (all source-decoded):
  - GEN ACK (main=128 sub=1 type=2, payload [echo_main][echo_sub][echo_type][seq][0x80])
    for every command. 0x80 = generic ACK (accepted, processing).
  - GPRS_CALL_STATUS (main=13 sub=16, 9B) payload "01 03 00..." = cid 1, state 3 (NOT connected).
  - GPRS_PDP_CONTEXT (main=13 sub=4 type=2, 3B) payload "01 14 00" = 1 context, state 0 (DISCONNECTED).

GEN 0x80 semantics: UNIFORM across all commands including mobile-data (which
provably yields NET_REGIST). Therefore 0x80 = generic completion ACK, NOT a
per-command success indicator and NOT a failure.

## Root cause of the remaining block (honest)
The CP accepts the entire byte-exact (vendor-disassembly-derived) data-session
sequence and returns a GPRS_CALL_STATUS "disconnected" (state 3 -> internal 0)
and GPRS_PDP_CONTEXT "disconnected" (state 0). No GPRS_IP_CONFIGURATION /
CALL_STATUS(connected) ever arrives; rmnet0..7 stay DOWN.

Most probable remaining causes (unverified against a known-good live reference):
  1. Carrier data plan not provisioned/active on this SIM (data call rejected
     at the network with a disconnected state).
  2. A remaining undecoded profile requirement (exact RadioTechnologyType/
     AccessNetworkType enum value in SyncProfileInfo/SetDataProfile — the three
     "int" tail args and the rat byte are carrier-dependent and were emitted
     as their zero/default values because their exact enum selects are not yet
     proven for this EFUJ2 build).

Both require either an active carrier data-plan reference or the exact RAT enum
values from the paired AP+CP build, which are not fully recoverable from the
read-only libsec-ril.so alone.
