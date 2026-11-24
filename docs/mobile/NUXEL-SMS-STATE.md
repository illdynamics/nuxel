# Nuxel SMS implementation and evidence

Consolidation source/evidence audit, 2026-11-24 CET. Native SMS serialization,
encoding, decoding, durable storage and asynchronous service exist. **No
confirmed recipient delivery or real network-delivered incoming SMS is
established by the reviewed evidence.** No messages were sent in this pass.

## Functionality matrix

| Capability | Category | Evidence / remaining acceptance |
|---|---|---|
| Outbound native submission | Implemented but not physically verified | `SendSms`, queued TPDU, correlated send response; no actual message sent in the reviewed operation logs |
| Actual recipient delivery | Blocked | Requires explicitly authorized recipient and working carrier SMS path; `delivery_verified=false` live |
| Incoming network SMS | Implemented but not physically verified | Native notification decoder, durable store and ACK path; tests are synthetic |
| Incoming backend notifications | Implemented but not physically verified | Radio1 `SmsReceived` / `SmsStateChanged`; no real incoming event acceptance |
| User notification integration | Missing for native Radio1 | Existing desktop/app notification infrastructure has no audited native SMS event adapter |
| Message decoding | Implemented but not physically verified | GSM SMS-DELIVER / STATUS-REPORT codec, strict malformed-input tests |
| Message encoding | Implemented but not physically verified | GSM alphabet/extensions and UCS-2 TPDU serialization tested offline |
| Delivery reports | Implemented but not physically verified | Actual TP-STATUS-REPORT matching logic exists; no physical carrier report received |
| Unicode | Partially implemented | BMP UCS-2 supported; non-BMP and unsupported national alphabet forms explicitly rejected |
| Multipart SMS | Implemented but not physically verified | Up to eight outbound parts; inbound 8/16-bit concat references, ordering/dedup/conflict checks; synthetic fixtures only |
| Message persistence | Partially implemented end to end | Native SQLite store live available and offline durability tests pass; real message/reboot/application synchronization not accepted |
| Messaging app integration | Partially implemented | Existing app/MM/local-store path; native Radio1 SQLite/API is not connected to it |
| Error handling | Implemented but not physically verified | Raw failure results, malformed/storage ACKs, uncertainty on timeout/crash, sender authorization |
| Retry behavior | Partially implemented | Bounded setup, no automatic resend after uncertain submission; no user-facing reconciliation/retry workflow |
| IMS SMS | Unsupported by current native path | Service selects CS domain; no IMS registration or IMS SMS implementation |

Read-only live status: storage available, DEVICE_READY accepted, SMSC received,
no pending submission, not blocked, domain CS, delivery not verified. These
prove service initialization and storage access only. The current radio has
PS NOT_REGISTERED and CS DENIED; the readiness/SMSC responses do not establish
that a carrier will accept SMS.

## Architecture and source map

The exact recovered wire contract is
[`../S5000AP-IPC41-SMS.md`](../S5000AP-IPC41-SMS.md). Preserve it rather than
inventing main/subcommands or assuming generic AT/QMI/MBIM behavior.
All native source/test paths below are under `tools/s10plus/s5000ap-05/`.

| Component | Verified functions / contract |
|---|---|
| `src/fmt_sms.c`, `.h` | `fmt_sms_send`, `fmt_sms_ack`, `fmt_sms_ready`, `fmt_sms_get_smsc`, `fmt_sms_incoming`, `fmt_sms_submit_result`, `fmt_sms_smsc` |
| `src/sms_pdu.c`, `.h` | `sms_encode`, `sms_decode`, `sms_codec_name`; UTF-8 validation, GSM packing, UCS-2, address/timestamp/UDH parsing |
| `src/sms_store.c`, `.h` | `sms_store_open`, `sms_store_queue`, `sms_store_next`, `sms_store_sending`, `sms_store_submit`, `sms_store_fail`, `sms_store_receive`, `sms_store_get`, `sms_store_list`, internal `delivery` / `recalc` |
| `src/sms_service.c`, `.h` | `sms_service_open`, `sms_service_tick`, `sms_service_receive`, `sms_service_close`, internal `uncertain` / `notify`; one active segment and response correlation |
| `src/radiod.c` | `method_send_sms`, `method_list_sms`, `method_get_sms`, `method_get_sms_status`, `sms_write`, `sms_notify`, `tick_handler`, `require_control` |
| `tests/test_fmt_sms.c`, `tests/vendor_sms_vectors.h` | Wire vectors, service-center padding and malformed-response rejection |
| `tests/test_sms_pdu.c` | Encoding/decoding, alphabet extensions, Unicode boundaries, multipart and malformed input |
| `tests/test_sms_store.c` | Durable queue/inbox, retransmission deduplication, delivery report matching and recovery |
| `tests/test_sms_service.c` | Store-before-send / store-before-ACK ordering, sequence correlation, timeouts and crash uncertainty |
| `scripts/recover_vendor_vectors.py --sms-header` | Isolated vendor serialization oracle; synthetic outputs are not sent to the phone |

Radio1 is the existing daemon on the Nuxel session bus, not a separate modem
writer. Its object is `/nl/nuxel/Radio1`, destination/interface `nl.nuxel.Radio1`.

| IPC | Signature / meaning |
|---|---|
| `SendSms` | `ss -> u`, recipient/text to durable local message ID |
| `ListSms` | ` -> au`, local IDs |
| `GetSms` | `u -> a{ss}`, content/state, credential checked |
| `GetSmsStatus` | ` -> a{ss}`, aggregate transport/storage state |
| `SmsReceived` | signal `u`, local message ID only |
| `SmsStateChanged` | signal `us`, ID and state only |

Controls and private message retrieval use `require_control()` and actual
sender EUID. Bridge app permissions must remain in front of this API. Do not
copy recipients, message bodies, SMSC numbers or subscriber identifiers into
handover evidence. Native signals deliberately carry IDs rather than contents.

## Wire behavior and message state

FMT main 4 carries send (sub1), incoming (sub2), incoming ACK (sub6), device
ready (sub7), and service-center query (sub10). The native service prepends the
actual CP/SIM SMSC to the encoded TPDU. `fmt_sms_smsc()` handles the physically
observed padded 12-byte field while validating its logical length; the earlier
strict equality bug was corrected during Round43 operation 23.

Native SMS chooses **CS wire domain 0** using the recovered domain conversion.
It does not silently switch to IMS. `tick_handler()` currently permits queued
sending if either converted PS or CS registration is registered. That is an
implementation gate, not evidence that CS SMS is available on LTE-only service;
validate the carrier-supported path before treating this condition as enough.

```mermaid
stateDiagram-v2
    [*] --> Queued: durable SendSms intent
    Queued --> Sending: durable segment claim before FMT write
    Sending --> Submitted: matching CP send result 0
    Sending --> Failed: explicit rejection
    Sending --> Unknown: timeout, failed write or crash
    Submitted --> Delivered: matching STATUS_REPORT TP_ST 0
    Submitted --> Failed: terminal delivery failure
    Unknown --> Unknown: automatic resend prohibited
```

A generic GEN success 0x8000 accepts a command. A send result 0 confirms
submission. Neither proves recipient delivery. Only a matching status-report
TPDU with TP-ST 0 marks delivered; forwarded-without-confirmation remains
submitted. Recipient observation is still necessary for physical acceptance.
A late negative report cannot downgrade confirmed delivery.

Incoming notification -> strict frame/PDU decode -> SQLite commit -> positive
ACK. Storage failure sends 0x8016; malformed/unsupported content sends 0x806f.
An ACK response acknowledges the local receive operation, not recipient
delivery. Exact retransmissions are deduplicated; conflicting multipart
segments are rejected. A complete incoming synthetic fixture only tests code.

`command` send processing is asynchronous and uses sequence correlation;
`sms_service_tick()` bounds setup and applies a 120-second submission timeout.
`uncertain()` prevents automatic resend after ambiguous outcomes. Restarting
radiod must not turn an unknown result into a second billable message.

## Encoding, storage and app boundary

Encoding supports GSM default/extension alphabet, UTF-8 input and BMP UCS-2,
with up to eight outbound parts. GSM escape pairs are not split at boundaries.
Incoming concatenation handles 8-bit and 16-bit references. Non-BMP Unicode
and unimplemented national alphabets fail explicitly. Do not render a rejected
emoji message as sent. Outgoing segments request status reports, subject to
carrier support; lack of a report is not proof of recipient failure.

Private database: `/var/lib/nuxel-radio/sms.sqlite3`, optionally overridden by
`NUXEL_SMS_DATABASE`. SQLite persists outgoing intent before any modem send,
and incoming content before positive ACK. Outstanding references and recently
completed references remain reserved to reduce report collisions. The daemon
has only one active segment, preventing concurrent write/correlation races.

Repository unit `nuxel-radiod.service` contains `StateDirectory=nuxel-radio`,
mode 0700 and UMask 0077. The installed older base unit instead relies on
`20-sms-storage.conf` with `ReadWritePaths=/var/lib/nuxel-radio`. This currently
works (live storage available), but the service/unit installer must be checked
on a fresh install and reboot. Do not commit the private SQLite database.

`shell/nuxel-shell/nuxel-messages/main.c` speaks the MM Messaging/Sms API
through `mm_conn`, `mm_modem_path`, `mm_messaging`, and async send callbacks
including `on_mm_send_ready`. It uses the shared local phone-data layer and
also has an explicitly labelled mock bridge path. It does not subscribe to
Radio1's native inbox/outbox. `nuxel-phone-data` JSON and the native SQLite
store are separate existing stores; adding a third store is not a solution.
Use native IDs/state as transport authority and map application presentation
without duplicating sends or conflating queued/submitted/delivered.

`services/nuxel-bridge/src/bridge.py::ModemManagerConnector.send_sms()` still
returns a `mock:true` success when MM is disconnected and keeps an in-memory
mock list. That is not carrier delivery. The API adapter must preserve explicit
unavailable state on physical hardware and never map that mock result to real
sent/delivered status. Native `sms_notify()` emits D-Bus signals; a complete
native-to-user-notification path was not found in the reviewed integration.

## Evidence and exact remaining implementation

Historical evidence:

- Commit `2c377487`: native SMS transactions and recovered cellular-only HTTPS.
- Commit `24e61763`: recovery/installation reconciliation and call integration.
- `/tmp/nuxel-round43/live-sms-23-initial.log`, `live-sms-23-status.log`,
  `verify-23.log`, `verify-24.log`, `verify-25-final.log`: initialization,
  SMSC parsing/storage and retained LTE. No confirmed recipient exchange.
- `reports/S5000AP-06-ROUND43-SET-APN-INFO-CP-TRACE.md` explicitly records an
  empty inbox/outbox and no outgoing SMS/call initiated. Round44 leaves
  physical delivery unverified. No reviewed artifact supersedes that boundary.

Ordered next work, only for incomplete capabilities:

1. Preserve/recover LTE and normal CP initialization; retain CS+PS, SIM and
   separate registration states. Fix data OFF without powering down SMS.
2. Connect the existing permission-checked bridge and Messages app to Radio1.
   Read native IDs/status, subscribe to receive/state changes, resynchronize
   on service restart, and show queued/submitted/delivered/failed/unknown
   distinctly. Test denied app access and avoid exposing raw modem commands.
3. Wire native receive events to one user notification and durable app view.
   Test app closed, reopened, duplicate signals, retransmitted network PDU,
   reordered multipart segments and database failures offline first.
4. Add a deliberate user reconciliation/retry action for unknown submissions;
   never auto-resend after timeout or reboot. Keep failed vs uncertain distinct.
5. With explicit recipient authorization, perform one bounded outbound SMS,
   inspect recipient receipt and correlate any actual carrier delivery report.
   Then have that consenting peer send one real incoming SMS; verify decoding,
   store-before-ACK, app update and notification. Do not run repeated billable
   loops or use synthetic fixture numbers on hardware.
6. Only if authorized and basic traffic succeeds, cover one Unicode and one
   multipart exchange, verify exact text on both ends, and test persistence
   across app/service restart and normal reboot. Keep all message content
   private and record only redacted result/IDs/timing.
7. Regress LTE DNS/HTTPS after SMS, data OFF while SMS remains usable, and
   service loss without duplicate transmissions. Document carrier restrictions
   separately from implementation failures; IMS-dependent SMS requires a
   supported IMS path, not a guessed domain-byte substitution.

## Tests and limitations

This pass re-ran the host radio build/test script, its 3,000 ordinary and 3,000
sanitized fuzz inputs, and the twelve ASan/UBSan component suites including
all four SMS suites. Twelve core native AArch64 suites also ran, including SMS.
See the [handover](DEEPSEEK-STAGE06-HANDOVER.md) for actual exit statuses,
full-suite native build failure and evidence locations. These are software
regression results, not carrier-delivered messages.

The ordinary phone-data runner failed to compile on this macOS host due to its
strict-C11 `mkdtemp` declaration issue. No live SMS app acceptance was performed.
No telephone number has been authorized for a new chargeable experiment.
