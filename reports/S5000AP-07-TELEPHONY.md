# Stage 07 — SMS, Voice, IMS/VoLTE and UI as Independent Deliverables

**Date:** 2026-11-24 CET
**Branch:** cs/mob-round35-stage06
**Device:** Samsung Galaxy S10+ SM-G975F (beyond2lte, Exynos 9820, Shannon
S5000AP, baseband G975FXXSEFUJ2, KPN SIM PLMN 20408)
**Precondition checked:** LTE data PASS from round 06 (commits `9dc13efd`
"establish verified LTE bearer" and `24e61763` automatic data session ACTIVE).
This round does **not** collapse SMS/voice/IMS into a single "modem working"
flag; each is reported independently.

---

## 1. SMS gate — HOST_TESTED (physical delivery BLOCKED)

### Source-validated protocol/API

Recovered from vendor `libsec-ril.so` (`IpcProtocol41` SMS family, main=4) and
the vendor command-name table at `0x3a85f8`: SEND_MSG(1), INCOMING_MSG(2),
READ_MSG(3), SAVE_MSG(4), DELETE_MSG(5), DELIVER_REPORT(6), DEVICE_READY(7),
SEL_MEM(8), STORED_MSG_COUNT(9), SVC_CENTER_ADDR(10), SVC_OPTION(11),
MEM_STATUS(12), CBS_MSG(13), CBS_CFG(14), STORED_MSG_STATUS(15),
PARAM_COUNT(16), PARAM(17), STATUS(18), CBS_CBMI_CFG(19),
CBS_ACTIVATION(20), RP_SMMA(21). All IDs are recovered from the pinned vendor
binary — none invented from other Samsung generations.

### Implemented and host-verified

- GSM 03.38/03.40 codec: default/extension alphabet, UCS-2, UTF-8, ≤8
  concatenated segments, strict incoming concat-length parsing, no split escape
  pairs, per-segment status-report request (`sms_pdu.c`).
- Durable SQLite store (`sms_store.c`): outgoing intent before CP write, incoming
  content before positive ACK, dedup, concat-conflict refusal, ≥24 h reference
  hold, crash-leaves-`unknown` (no auto-resend on daemon restart).
- Service layer (`sms_service.c`): SMSC/CP correlation, send, delivery tracking
  (TP-ST=0 → delivered; forwarded-unconfirmed stays submitted; terminal →
  failed).
- D-Bus: SendSms/ListSms/GetSms/GetSmsStatus + SmsReceived/SmsStateChanged
  signals that carry only local IDs/state — never text, recipient or SMSC.

### Verification status

- Host: `test_fmt_sms`, `test_sms_pdu`, `test_sms_store`, `test_sms_service`
  PASS; golden wire vectors from isolated vendor execution match; ASan/UBSan
  fuzz clean. Receipt: `reports/S5000AP-07-HOST-TEST-RECEIPT.json`.
- Physical bidirectional SMS: **BLOCKED** — requires owner consent plus two
  actual non-premium non-emergency test numbers, and redacted log discipline.
  Not performed this round; no outbound SMS or recipient number was used.

### Verdict

`HOST_TESTED` (implementation + codec + storage + D-Bus), physical
send/receive `BLOCKED` on owner consent + two test numbers.

---

## 2. Voice gate — HOST_TESTED (physical two-way audio BLOCKED)

### Source-validated call control

Recovered CALL family (main=2): Originate(1), Release(3), Answer(4),
GetCallList(6). Wire bytes match golden vectors (answer `07 00 00 00 02 04 01`,
release `07 00 00 00 02 03 01`, list `07 00 00 00 02 06 02`). Dial serializes
normal CS voice only (type 0x0100); it rejects empty/over-length/non-digit
numbers and produces **no** emergency or supplementary-service encoding.

### Implemented and host-verified

- `fmt_call.c`: dial/answer/release/get_list + fail-closed list/status parsing
  (self-consistent count, fixed 8-byte header + digit run, type==0x100, unique
  ids, exact end-of-payload).
- `call_service.c`: single-command FSM, 30 s deadline, 1 s/60 s list re-query,
  CP-offline → clear pending + emit "unknown" for prior calls, answer refused
  unless an incoming call is in the list, hangup supersedes setup.
- D-Bus Dial/AnswerCall/HangupCall/GetCalls/GetVoiceStatus + signals; `Dial`
  explicitly rejects 112/911 (`SD_BUS_ERROR_NOT_SUPPORTED`).

### Audio path — NOT implemented (truthful)

`GetVoiceStatus` reports `audio_route=unconfigured`, `ims=unimplemented`. No
Exynos ABOX ALSA/UCM `VoiceCall` verb, no PipeWire call routing, no SCO/HFP
path has been wired or validated on S5000AP. Call control is independent of
microphone/recording permission.

### Verification status

- Host: `test_fmt_call`, `test_call_service` PASS; golden vectors match;
  ASan/UBSan clean.
- Physical dial/ring/connect/hangup + two-way intelligibility + earpiece/
  speaker routing + radio-loss teardown: **BLOCKED** — needs owner consent, a
  consenting non-emergency number, and no automatic dialing loops. Not
  performed.

### Verdict

`HOST_TESTED` (call control + FSM), physical call + two-way audio `BLOCKED`
(audio route unconfigured + owner consent + test number required).

---

## 3. IMS / VoLTE gate — BLOCKED

See `docs/S5000AP-IPC41-IMS-FEASIBILITY.md`. The vendor `libsec-ril.so`
contains a complete IMS stack (`ImsManager`, `SetSipParam`, `SendImsAuthResp`,
`IpcRxSecImsAuth`, `IpcTxImsAuthResp`, `IpcRxQmiIms`, full `Ss*` family), and
the command IDs `IPC41_MAIN_IMS=22`, `IPC41_MAIN_QMIIMS=64`,
`IPC41_SEC_IMS_AUTH=9`, `IPC41_SEC_IMS_SUPP_AUTH_TYPES=14` are recovered. That
is modem/vendor capability, **not** Nuxel support.

Nuxel has **no** native IMS signaling, audio, or registration path.
`GetCapabilities` reports `ims=false`, `volte=false`.

Sub-blockers (each independent):

- `IMS_BLOCKED_VENDOR_STACK` — the complete client exists only inside
  proprietary Samsung binaries (`libsec-ril.so` + not-present `ims`/`imsservice`/
  `rcs` daemons); lawful isolated execution and AKA interworking are not
  established here.
- `IMS_BLOCKED_PROVISIONING` — KPN must provision IMS entitlement and approve the
  handset; a carrier action independent of Nuxel.
- `IMS_UNSUPPORTED` — no mainline-complete open IMS client substitutes.

This does **not** fail basic LTE. IMS remains a distinct deliverable at 0%.

### Verdict

`BLOCKED` (`IMS_BLOCKED_VENDOR_STACK` + `IMS_BLOCKED_PROVISIONING` +
`IMS_UNSUPPORTED`).

---

## 4. UI and permissions

- Honest modem/SIM/network status via `GetCapabilities` (`lte_data`,
  `sms=implemented-unverified`, `voice=call-control-only`, `ims=false`,
  `volte=false`) and `GetVoiceStatus` (`audio_route=unconfigured`,
  `ims=unimplemented`). No false signal bars; no enabled buttons that cannot
  act.
- `nuxel-dialer`/`nuxel-contacts`/`nuxel-messages` share the plain-C
  `nuxel-phone-data` layer whose capability label is probe-derived and never
  over-claims (no modem → "no calls, no SMS", a mock is labelled offline, a
  queued message is shown "not sent").
- D-Bus access: state-changing methods are gated by actual sender EUID
  (`sd_bus_query_sender_creds`, never a caller-supplied UID) against root or
  the `nuxel` account; `require_control` is applied to SendSms/Dial/AnswerCall/
  HangupCall and every state change. `Dial` refuses 112/911.
- Logs are redacted: only aggregate counters and local IDs; no IMSI/ICCID/
  IMEI/PIN/PUK/MSISDN/APN/user SMS bodies or phone numbers (`GetDiagnostics`
  exposes aggregate counters only).

### Host regression fixes this round

- Fixed `nuxel-phone-data` test-host regression: `mkdtemp` now compiles under
  macOS by defining `_DARWIN_C_SOURCE` before `_POSIX_C_SOURCE` (74 checks
  pass; previously `FAIL build` on this host).
- Phone-app offline acceptance: `PASS=37 FAIL=0 verdict=OFFLINE_TESTED`.

---

## 5. Negative tests (added / enumerated)

- No-SIM / no-service / airplane / CP-offline: `call_service_tick` refuses dial,
  refuses answer (no incoming in list), emits "unknown" for prior calls;
  `sms_service_tick` refuses outbound when the transport is not ready. Physical
  airplane/SIM-absent runs remain owner-gated.
- Offline SMS/message staging: the local messages app stores `queued`/`no-modem`
  and never reports `sent` without a transport confirmation; mock local storage
  is never presented as radio SMS.

---

## 6. Independent result table

| Gate | Result | Physical evidence | Precondition / limitation |
|---|---|---|---|
| SMS | HOST_TESTED (+physical BLOCKED) | none physical; host receipt only | owner consent + 2 test numbers |
| Ordinary voice | HOST_TESTED (+physical BLOCKED) | none physical | audio route unconfigured + consent + test number |
| IMS/VoLTE | BLOCKED | vendor symbols only | vendor stack + carrier provisioning |
| UI/permissions | HOST_TESTED (offline) | phone-app acceptance PF=37/0 | GTK4 sysroot for live UI |

## 7. Licensing and limitations

- Native code is GPL-2.0-only (SPDX headers). Vendor `libsec-ril.so` is
  proprietary, recovered read-only, and never redistributed.
- A few thinking rounds cannot replace missing secure vendor IMS
  interoperability or carrier provisioning; neither is claimed here.
