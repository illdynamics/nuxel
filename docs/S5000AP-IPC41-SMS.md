# Native S5000AP SMS protocol and delivery contract

Round 43, matching AP `libsec-ril.so` SHA-256
`b02bd095ae44a991b3cb676e584b3209a947160c22e678578f8b0c877e282cb3`.
The active CP is EFUJ2. These are recovered AP serializers/parsers, followed
by native implementation and tests; end-to-end SMS acceptance is still pending
an authorized test endpoint. No Android process is used by the implementation.

All commands use main **4** and the existing 7-byte FMT header. Total length
is u16 little-endian including that header. Header byte 2 is the AP sequence:
`IpcProtocol41::SetMsgSequence` at `0x316860`, generator at `0x314cc0`, cycles
0..254. CP response byte 3 is used for correlation. Payload offsets below
start immediately after the header. Protocol identifiers are never delivery proof.

| Operation | Subcommand / AP type | Payload |
|---|---|---|
| Send GSM SMS | 1 / EXEC 1 | 4+N bytes: p0=2 GSM, p1=1 last/single or 2 more, p2=domain, p3=u8 N, p4..=SCA+TPDU |
| Incoming GSM | 2 / CP notification 3 | 6+N bytes: p0=2, p1=category, p2..3 reserved, p4=ACK reference, p5=u8 N, p6..=SCA+TPDU |
| Acknowledge incoming | 6 / EXEC 1 | 5 bytes: p0=2, p1..2=u16 LE result, p3=ACK reference, p4=0 |
| Device ready | 7 / SET 3 | zero bytes |
| Get SMS service center | 10 / GET 2 | zero bytes |

`IpcTxSendSms` at `0x344df8` accepts SCA+TPDU, N=1..255. It does not encode
text. `SmsManager::DoSendSms` (`0x218fc8`) calls the modem path at `0x2fa5d8`,
which prepends the configured service-center address. Native code follows that
split: `sms_pdu.c` constructs TPDU, `sms_service.c` adds the actual CP SMSC.
SMSC response p0 is following-octet count; subsequent bytes are TON/NPI and
semi-octet BCD with an optional final F nibble. Zero selects the SIM's default.
The live SMSC response is a padded **12-byte field**, not necessarily the
logical length. `SmsCenter(char *,int)` at `0x2b0ed8` copies p0+1 bytes and
ignores padding. Native parsing retains bounds while following that behavior;
operation 23 exposed and corrected the earlier overly strict equality check.
No phone number is fabricated or used in tests against hardware.

`ConvertDomainToIPC` (`0x344b98`) maps internal 0/1/2/3 to wire 2/3/0/1.
`DomainSelector::GetDomain` (`0x222c90`) identifies internal 2 as CS. Native
SMS uses wire **0**; it does not pretend to implement the separate IMS path.
Whether KPN permits this domain on the current subscription remains a live test.

Send response 4/1/CP type 2, parser `0x3463c0`, has **5+N** bytes:
p0=2, p1..2=u16 LE result, p3=message reference, p4=PDU length, p5..=PDU.
Result **0** means network submission, never recipient delivery. Nonzero raw
results are retained. `GetSmsResult` (`0x344a30`) maps raw 11→7, 12/13→2,
18→8, 19→12 in the vendor error enum; cause-coded values exceed `0x8000`.
Native consumers receive the raw value rather than an invented interpretation.
GEN responses also identify original main/sub/type and carry a u16 LE result;
`0x8000` is command acceptance, not delivery.

`IpcTxDeliveryReport` (`0x344f48`) is the incoming-message acknowledgement.
Its result is **0** on successful durable receipt, **0x8016** for storage
failure/memory full, and **0x806f** for malformed or unsupported content.
The 4/6 CP reply acknowledges this operation; it is not a recipient report.
Actual delivery arrives in an incoming **SMS-STATUS-REPORT TPDU (MTI 2)**.
Only matching peer/message reference with **TP-ST 0** marks `delivered`.
Forwarded-without-confirmation (1) remains `submitted`; terminal failures are
reported as `failed`. A late report cannot downgrade confirmed delivery.

The AP command-name table at `0x3a85f8` enumerates the complete SMS family:
1 SEND_MSG, 2 INCOMING_MSG, 3 READ_MSG, 4 SAVE_MSG, 5 DELETE_MSG,
6 DELIVER_REPORT, 7 DEVICE_READY, 8 SEL_MEM, 9 STORED_MSG_COUNT,
10 SVC_CENTER_ADDR, 11 SVC_OPTION, 12 MEM_STATUS, 13 CBS_MSG, 14 CBS_CFG,
15 STORED_MSG_STATUS, 16 PARAM_COUNT, 17 PARAM, 18 STATUS, 19 CBS_CBMI_CFG,
20 CBS_ACTIVATION, 21 RP_SMMA. The unused command payloads are not guessed.

## Native behavior and verification

The codec implements the GSM default/extension alphabet, UTF-8 conversion,
UCS-2 for BMP text, and up to eight concatenated segments. Non-BMP text and
unimplemented national alphabets return explicit errors. Incoming 8/16-bit
concatenation references are parsed with strict lengths. No escape pair is
split across outgoing segments. Every outgoing segment requests a status report.

SQLite transactions in private `/var/lib/nuxel-radio/sms.sqlite3` persist
outgoing intent before CP writes and incoming content before positive ACK.
Exact retransmissions are deduplicated. Conflicting concatenated parts are
refused instead of silently losing or mixing content. References remain reserved
for outstanding messages and for at least 24 hours after completion.
A timeout, failed write, or crash during submission leaves `unknown` and blocks
further automatic sending; restarting the daemon does not resend it.

Native `nl.nuxel.Radio1` methods are `SendSms(ss)->u`, `ListSms()->au`,
`GetSms(u)->a{ss}`, and `GetSmsStatus()->a{ss}`. `SmsReceived(u)` and
`SmsStateChanged(us)` expose local IDs/state, never text or recipient numbers.
Content and controls check the actual bus sender UID against root or the
`nuxel` session account. There is no claimed polkit enforcement.

`scripts/recover_vendor_vectors.py --sms-header` executes isolated vendor code
to generate the golden wire vectors. Host tests independently check known GSM
packing, UCS-2 bytes, segment boundaries, malformed PDUs, durable commit/ACK
ordering, duplicate receipt, submission correlation and crash recovery.
These tests use synthetic destinations and in-memory/temporary stores only.

Encoding references: [3GPP TS 23.038, ETSI publication](https://www.etsi.org/deliver/etsi_ts/123000_123099/123038/15.00.00_60/ts_123038v150000p.pdf),
[3GPP TS 23.040, ETSI publication](https://www.etsi.org/deliver/etsi_ts/123000_123099/123040/16.00.00_60/ts_123040v160000p.pdf).
