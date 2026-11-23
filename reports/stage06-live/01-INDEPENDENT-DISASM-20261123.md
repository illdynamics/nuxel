# Stage 06 — Independent vendor-RIL disassembly (round-18 ground truth)

**Date:** 2026-11-23 CET
**Branch:** cs/mob @ 9c0365cc
**Source binary:** /tmp/vendor-ro/lib64/libsec-ril.so (SHA256 b02bd095...c877e282cb3)
**Tool:** aarch64-linux-gnu-objdump (host) on a local copy (same hash).

## Purpose
Re-derive the full Samsung default-bearer path from first principles to
close the remaining Stage-06 gap, and resolve prior contradictory report
decodes.

## 1. IpcTxSetPdpContext @0x31f6e0 — frame layout CONFIRMED
Symbol `_ZN13IpcProtocol4118IpcTxSetPdpContextEhiPKcS1_ii` demangles to:
  IpcTxSetPdpContext(unsigned char cid, int pdp_type, char const* apn,
                     char const* password, int auth, int pdp_act_deact)
Frame = 112 bytes (0x70), header main=13 sub=4 type=3 (0x0d 0x04 0x03).
Key stores (frame base = sp, payload = sp+7):
  31f730 strb w1,[sp,#8]   -> payload[1] = cid
  31f738 strb w8,[sp,#6]   -> cmd_type = 3
  31f764 strb wzr,[sp,#7]  -> payload[0] init 0, then pdp_type (jump table)
  31f7d4/31814/31820/3182c/31838 -> pdp_type wire codes (1/5/6/8... path) at payload[0]
  31f808 stur w22,[sp,#9]  -> flags word payload[2..5] (bit0=APN, bit1=user)
  31f8a8 orr w8,w22,#0x10 -> ACTIVATE bit (bit4) when pdp_act_deact != 0
=> payload[0]=pdp_type, payload[1]=cid. CURRENT CODE IS CORRECT.

## 2. GetAttachCid @0x1e4500 — CONFIRMED
  mov w9,#5; cmp w8,#1; csinc w9,w9,wzr,eq  (EQ -> w9 unchanged=5, else w9=1)
  cmp w8,#0; csinc w0,w9,wzr,ne           (NE -> w0=w9, else w0=1)
=> model_type==1 -> 5 ; model_type==0 or >=2 -> 1. Single-SIM -> attach CID = 1.

## 3. ModemProxy::SetAttachApn @0x1ce430 -> vtable[816] = IpcModem::SetAttachApn
##    IpcModem::SetAttachApn @0x2f1410 — USERSpace-ONLY (answer A)
Disassembly shows this function ONLY:
  - copies APN/user/pass into IpcModem self+0x9c / 0x101 / 0x165 (3 string bufs)
  - stores w2(DataProfile)@self+152, w6(DataAuth)@self+460, w7@self+464,
    stack[8]@self+472, stack@self+468
  - returns 0, NO IPC frame emitted.
=> There is NO IpcTxSetAttachApn command. SetAttachApn is a userspace-state
   setter (mob.md section 5 answer A). It does NOT send a modem IPC command.

## 4. SetLteAttachPdnList / SetLteAttachtype — VENDOR STUBS CONFIRMED
  IpcModem::SetLteAttachPdnList @0x30dd60 = size 8 (ret only)
  IpcModem::SetLteAttachtype     @0x30dd48 = size 8 (ret only)
=> No separate LTE attach-PDN-list / attach-type wire command exists.

## 5. DataCallManager::DoSetInitialAttachApn @0x22bad8 — STUB (log + return 0)

## 6. ContextActivationDca::ActivateContext @0x26ad88 — real LTE activation path
Final dispatch (26af5c..26af88):
  x0=[x20,#40] (ModemProxy), x1=Msg, w2=[x19,#20]=cid, w3=w22=pdp_type(LTE=3),
  x4=x19+0x7d=apn, x5=x19+0xe1=password, w6=[x19,#356]=auth, w7=0,
  -> [vtable+736] ModemProxy::ActivatePdpContext -> IpcTxSetPdpContext.
=> The full default-bearer path is: SetLteAttachProfile -> PsAttach ->
   SetPdpContext(ACTIVATE). ALL of these are already implemented byte-exact.

## 7. IpcRxGprsCallStatus @0x321ab0 — state decode CONFIRMED
  ldrb w8,[x19,#8] = payload[1] = call state.
  state==1 -> 4, ==11 -> 6, ==10 -> 5 (connected); ELSE (incl 3) -> 0 (NOT connected).
=> payload[1]==3 => NOT connected. Current decode correct.

## 8. IpcRxGeneral @0x32b0f0 — GEN result
  ldrh w1,[x1,#10] = payload[3..4] as 16-bit LE result. Live echoes:
    0808030080 / 0d1d030380 / 0d04030080 -> payload[3..4]=0x03,0x80 = 0x8003 (uniform OK).

## LIVE RE-VERIFICATION (21:58 CET)
PS REGISTERED_HOME (genuine). Full sequence ACKs (GEN 0x8003 = generic OK):
  NET_REGIST -> SET_SERVICE_DOMAIN -> SET_PREFERRED_NET -> ENABLE_MOBILE_DATA
  -> SET_DATA_PROFILE -> SET_LTE_ATTACH -> ALWAYS_ON_PDN -> PS_ATTACH
  -> PS_REGIST_VERIFY(REGISTERED_HOME) -> DATA_CALL(SetPdpContext)
  -> GPRS_CALL_STATUS payload 010300000000000000 = cid1, state3 (NOT connected).
No GPRS_IP_CONFIGURATION. No ESM cause surfaced. rmnet0..7 DOWN.

## CONCLUSION
The Nuxel data-call implementation is byte-exact correct vs libsec-ril.so.
There is NO missing wire command in the default-bearer path (SetAttachApn and
SetLteAttachPdnList/SetLteAttachtype are userspace-only/stubs). PS registration
is genuinely REGISTERED_HOME yet the CP reports the default EPS bearer as
NOT connected with no cause code. Remaining root cause is NETWORK/carrier-side
ESM denial or SIM data-service provisioning, which the CP does not expose to the AP.
