# Stage-06 Authoritative Reverse-Engineering Findings (round 17)

Date: 2026-11-23
Vendor lib: /tmp/vendor-ro/lib64/libsec-ril.so (build 60889dd714394ae0db7c2ecc2bf2740f)
Tools: aarch64-linux-gnu-objdump

## 1. GetAttachCid() @0x1e4500 — CORRECTED semantics

Disassembly (aarch64):
```
mov  w9, #5
ldr  w8, [global]          ; mModelType
cmp  w8, #1
csinc w9, w9, wzr, eq      ; if model==1: w9=5 else w9=1
cmp  w8, #0
csinc w0, w9, wzr, ne      ; if model!=0: w0=w9 else w0=1
ret
```

RESULT:
- model_type==1  -> 5
- model_type==0  -> 1
- model_type>=2  -> 1

The current code comment (and prior mob.md note) claims "modem_type 0 -> 5".
That is WRONG. GetAttachCid returns 5 ONLY for model_type==1; otherwise 1.

## 2. IpcTxSetAlwaysOnPdn(bool, DataProfile, int) @0x321550

Signature from mangled name: `IpcTxSetAlwaysOnPdn(bool, DataProfile, int)`.
Wire frame:
  main=13 (0x0d), sub=34 (0x22), type=3, total_len=9
  payload[0] = enable (0/1)
  payload[1] = the `int` 3rd arg (NOT the DataProfile; NOT a CID)

Caller IpcModem::SetAlwaysOnPdn(Message*, DataProfile, RadioTechnologyType, int)
passes the `int` (4th arg) as payload[1]; DoAlwaysOnPdn passes 1 (or 2 depending
on IsEsmFlagZeroNetwork). So the correct payload[1] is 1 (default), NOT 5.

Current code passes `DS_ATTACH_CID=5` -> WRONG semantic value.

## 3. IpcTxSetLteAttachProfile(unsigned char, char*, ...) @0x320238

payload[0] (frame[7]) = 3 if trailing bool arg bit0 set, else 1
payload[1] (frame[8]) = the first unsigned-char arg (the "int"/cid from caller)
payload[2]  = protocol-home wire byte
payload[3..103]  = APN (101 bytes)
payload[104..119]= extra (16)
payload[120..123]= int
payload[127..158]= username (32)
payload[159..190]= password (32)
payload[191] = auth flag
payload[192] = protocol-roaming wire byte
payload[193] = protocol (2nd copy)

This MATCHES the current fmt_tx_set_lte_attach_profile layout.

## 4. IpcTxSetPdpContext(unsigned char cid, int pdp_type, char*, char*, int, int) @0x31f6e0

payload[0] (frame[7]) = pdp_type-derived byte (from outer jump table keyed on
  pdp_type; for pdp_type in 2..8 it is the pdp_type value directly; pdp_type 0/1
  use an auth+21 inner table).
payload[1] (frame[8]) = cid
payload[2..5] (frame[9..12]) = flags word LE (bit0 APN, bit1 password, bit4 ACTIVATE)
payload[6..37]  = APN (32)
payload[38..69] = username (32)
payload[70..101]= password (32)
payload[102] = auth flag
payload[104] = protocol wire byte

For LTE: pdp_type=3 -> payload[0]=3, flags=0x11 (APN|ACTIVATE). This MATCHES the
current fmt_tx_set_pdp_context layout (payload[0]=3, payload[1]=cid, flags=0x11).

## 5. GPRS_CALL_STATUS decode (IpcRxGprsCallStatus @0x321ab0)

payload[0]=cid, payload[1]=call_state:
  state 1 -> internal 4, 10 -> 5, 11 -> 6 (connected)
  ANY other (incl 3) -> internal 0 (NOT connected)
payload[2] = pdp state (converted by helper @0x321d08)
payload[4] = a flag byte (nonzero)
payload[5..8] = a 32-bit word (cause code)

Live observed: payload = 05 03 00 00 00 00 00 00 00
  -> cid=5, call_state=3 (NOT connected), pdp_state=0, cause=0

## 6. ConvertProfileId(DataProfile) @0x22c890

DataProfile DEFAULT(0) -> 1 (non-NTC); other OEM profiles -> 4/5/11.
This is DISTINCT from GetAttachCid.

## 7. KEY OPEN QUESTION: model_type value for beyond2lte (SM-G975F)

GetAttachCid depends on mModelType (set via DataCallManager::GetInstance(SecRil*,
ModelType)). Value TBD empirically.
