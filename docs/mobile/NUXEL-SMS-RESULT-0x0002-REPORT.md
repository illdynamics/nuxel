# SMS submission result 0x0002 — root-cause investigation

Authoritative evidence recovered from EFUJ2 vendor RIL
`lib64/libsec-ril.so`, SHA-256
`b02bd095ae44a991b3cb676e584b3209a947160c22e678578f8b0c877e282cb3`,
GNU build-id `60889dd714394ae0db7c2ecc2bf2740f`, armv8, stripped dynamic
symbols retained. No recipient number, message body, SMSC or subscriber
identifier appears in this document.

## Result 0x0002 meaning

Result **2** is a low-level CP submission rejection with **no TP-FCS/reject
cause** (`SendSMS Result: 0x2, Tp cause: 0xFF`). It is not a 3GPP TS 23.040
cause and not an Android `RIL_Errno`; the vendor RIL does not map raw 2 to any
recognized enum value.

Evidence:

- `IpcProtocol41::GetSmsResult(int,int)` at `0x344a30` maps the raw CP result
  through a jump table at rodata `0x14a5d0` (base `0x344a74`). Raw 2 lands on
  the default entry (offset 0x05 -> `0x344a88`), which subtracts `0x8000` and,
  since `2 < 0x8000`, falls to `0x344ac4` and returns enum **0xff**
  (unknown/generic). The mapped values the vendor actually recognizes are
  raw 0->0, 11->7, 12->2, 17->8, 18->12 (RIL-style enum), cause-coded raw
  `>0x8000`->4. Raw 2 is outside that table.
- `IpcProtocol41::IpcRxSendMsg(char*,int,int&,RegistrantType&)` at `0x3463c0`
  parses the send response. For the GSM submission (payload[0]==2) short path
  it reads the u16 result at payload[1..2] and, when the PDU length at
  payload[4] is <4, logs `SendSMS Result: 0x%X, Tp cause: 0xFF` (string
  `0x122595`); no TP cause is present, hence `0xFF`.
- The u16 result == 2 therefore means the CP rejected the send command itself,
  before a network/SMSC TP-SUBMIT could produce a failure cause.

## Root cause

The native SMS path hard-codes the **CS** SMS wire domain
(`fmt_sms_send(..., domain_wire=0, ...)` == `ConvertDomainToIPC(2)`, i.e.
internal `DomainSelector` CS domain). Live physical state shows:

- PS (LTE) REGISTERED_HOME, `ps_attached=true`.
- CS registration **DENIED** (`cs_registration="DENIED"`, raw wire 4 ->
  `fmt_rx_reg_state()=3`).
- `service_domain_wire=1` (NET `CS_PS` configuration), `rat=LTE`.

The EFUJ2 vendor `SmsManager::DoSendSms` (`0x218fc8`) would refuse this same
configuration before touching the CP: at `0x2197b0` it checks
`NetRegState::IsRegistered()` and, on failure, reports
`%s: CS No Service, SMS send fail` (string `0x105013`) with vendor error `0x65`
(101), never issuing the CS submit.

The native daemon did not perform that check: it treated `PS registered ||
CS registered` as "registered", submitted the CS-domain `SEND_MSG`, and the CP
returned raw result 2 with no cause. The message then timed out to `unknown`.

## Implemented correction

`tools/s10plus/s5000ap-05/src/radiod.c`:

- Added `sms_cs_registered()`, which requires `cs_registration_valid &&
  fmt_rx_registered(cs_registration.state)`.
- `tick_handler` now passes `sms_cs_registered()` (CS only) to
  `sms_service_tick` instead of the previous PS-or-CS disjunction.
- `GetSmsStatus` now reports `registration` as `"cs-denied"` (and `ready`
  false) when CS is not registered, instead of `"registered"`.

This makes the daemon stop issuing CS-domain submissions with no CS bearer and
truthfully expose the blocker. It does not implement IMS, SGs, or any
alternative bearer, and it does not guess a different domain byte.

## Physical test outcome

The new owner authorized test was **not transmitted**. Under the corrected
truthfulness gate the daemon reports `registration="cs-denied"`; there is no
evidence-supported path to a genuine carrier submission because CS is denied
and IMS SMS is unimplemented (and out of scope this round). Sending against a
known-denied CS domain would reproduce the same raw result 2, so the
authorization is left unused rather than consumed on an identical
known-failing test.

Remaining dependencies for genuine outgoing SMS on this device/carrier:

1. Establish a real SMS bearer for the LTE-only, CS-denied subscription
   (SMS over SGs, or another supported NAS-based SMS transport), or
2. Implement IMS registration + SMSoIP (explicitly out of scope this round).

Telephony (voice/IMS) remains a separate mission.
