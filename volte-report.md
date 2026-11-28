# NUXEL — NATIVE VOLTE READINESS AND IMPLEMENTATION ROADMAP

*Source-level audit performed in Round 34.5 (2026-11-28), starting from the physically verified native IMS
foundation. No VoLTE signalling was implemented and no voice call was placed in this round.*

---

## 1. Executive summary

Nuxel owns a **working, physically verified native IMS control plane**: the Samsung Shannon S5000AP modem is
driven from Linux over SIPC5/FMT, USIM AKA runs natively, IMS PDN + P-CSCF discovery work, IPsec (XFRM) carries
protected REGISTER and MESSAGE, and native REGISTER reaches the carrier P-CSCF and gets a genuine 200 OK with a
granted lifetime that is refreshed by the FSM. On that foundation, **SMS-over-IMS is end-to-end physically
proven** (MO and MT, RP-ACK correlated, durable store).

**VoLTE itself is essentially greenfield.** Nothing in the tree sends or receives a SIP INVITE, builds or parses
SDP, opens an RTP/RTCP media socket, or negotiates an AMR codec for a call. The only "voice" code is the legacy
circuit-switched FMT call service (`call_service.c`, `fmt_call.c`) which drives modem call verbs and cannot work
on an LTE-only carrier (CS registration is DENIED and there is no CS fallback). Round 34.5 made `Dial` truthfully
return `NOT_SUPPORTED` rather than pretending.

The good news is that the expensive, hardware-specific, physically hostile part — the modem, IMS registration,
AKA, IPsec, SIP transport and the trust boundary to the apps — **already exists and is reusable**. The missing
work is a standards-compliant SIP dialog/transaction layer for INVITE dialogs, an SDP offer/answer engine,
RTP/RTCP with jitter/resilience, AMR-NB/WB endpoints, a call manager with a voice bearer + QoS policy, and a
full-duplex audio path through Samsung ABOX. The native audio stack (ALSA/PipeWire/WirePlumber, RDMA1 playback,
RDMA0 capture) is provably functional for unidirectional playback and capture, but **full-duplex,
voice-call-grade routing, echo cancellation and ABOX call-mode integration have never been demonstrated** and
must be treated as a major unknown, not as "audio is done".

**Overall native VoLTE implementation completeness: ~12 %** (implementation) / **~4 % physical verification**.
**Shared IMS foundation: ~80 %**. Verdict: **READY_FOR_VOLTE_IMPLEMENTATION = TRUE** — the architecture is sound,
the foundation is real, and the gaps are enumerable and dependency-ordered (see §27). It is **not** ready to
place a production VoLTE call today.

---

## 2. Current physically verified telecommunications foundation

| Capability | Status | Evidence |
|---|---|---|
| Native Shannon S5000AP CP communication | **PHYSICALLY_VERIFIED** | `tools/s10plus/s5000ap-05/src/sipc5_fmt.c`, `radiod.c` event tracker; `fmt_rx`/`fmt_tx` journal every boot; Round 34.5 reboot |
| CP boot (no partition writes) | **PHYSICALLY_VERIFIED** | `nuxel-cpbootd-production` exited 0; CP `ONLINE` after Round 34.5 reboot |
| LTE internet | **PHYSICALLY_VERIFIED** | `rmnet0` IPv6; `curl --interface rmnet0 https://www.google.com` → 200 (post-reboot) |
| Native hotspot / USB tethering | **PHYSICALLY_VERIFIED** (prior rounds) | `mobile_data.c`, `services/nuxel-network`; preserved this round |
| IMS PDN + P-CSCF discovery | **PHYSICALLY_VERIFIED** | `ims_pdn.c`, `ims_iil.c`; GetImsStatus `cid_attached/ip_ready/pcscf_ready=true` |
| USIM AKA (native) | **PHYSICALLY_VERIFIED** | `ims_init.c`, `iil_auth.c`, `ims_service.c`; registration succeeds on real SIM |
| IPsec / XFRM 3GPP security | **PHYSICALLY_VERIFIED** | `ims_security.c` (SA install, SPI/port direction), kernel XFRM; Round 31/32 wire proofs |
| Native SIP transport (protected) | **PHYSICALLY_VERIFIED** | `ims_sip.c`, `ims_sip_tr.c`; `sip_tr_send 5070→6000`, inbound 200 OK |
| IMS REGISTER + grant lifetime + renewal scheduling | **PHYSICALLY_VERIFIED (initial + restart recovery)**; natural renewal pending | `ims_grant granted_s=3600 refresh_in_s=2878 sa_lifetime_s=7200`; `SREG_REFRESH_MS=3600000` |
| SMS-over-IMS MO | **PHYSICALLY_VERIFIED** | `sms_ims_submit` → TS 24.341 RP-DATA in SIP MESSAGE; RP-ACK type 3 cause 0 (ids 4/5/7/8) |
| SMS-over-IMS MT | **PHYSICALLY_VERIFIED** (Round 33; not re-run this round) | inbound MESSAGE → `sms_service_deliver_ims`, RP-ACK reply, id 6/10/12/… |
| Persistent SMS store | **PHYSICALLY_VERIFIED** | `sms_store.c` SQLite; 17 rows, integrity ok across reboot |
| External recipient confirmation | **PHYSICALLY_VERIFIED (human)** | Round 33 owner report; not a protocol delivery report |
| Native Messages app integration | **PHYSICALLY_VERIFIED (this round)** | All messages = 17/17 via Radio1Bridge; §7 of `sms34.5.md` |
| VoLTE voice media | **NOT_IMPLEMENTED** | no INVITE/SDP/RTP code in tree |

---

## 3. Native VoLTE target architecture

The target keeps every working layer and adds a voice plane beside the existing SMS plane:

```
Phone app (GTK4/Radio1 client)
   → Radio1Bridge (system bus; caller EUID check + app permissions)
      → Radio1 call-management API (nl.nuxel.Radio1: Dial/AnswerCall/HangupCall/GetCalls/hold/DTMF)
         → Native call manager  (new: call FSM, dialog registry, DTMF, hold/resume, session timers)
            → Native IMS voice signaling  (new: INVITE dialog engine on the existing ims_sip_tr transport)
               → Native media transport   (new: RTP/RTCP, jitter buffer, AMR-NB/WB payload)
                  → Native audio infrastructure (existing: ALSA/PipeWire/WirePlumber + ABOX routes)
```

Key invariants for the design:

- **One SIP transport, one registration, many dialogs.** SMS uses a short MESSAGE transaction; calls use INVITE
  dialogs. They must share the protected transport, CSeq space, and registration refresh without resetting each
  other (today `ims_sip_tr` is transaction-centric and stateless per MESSAGE — see §8).
- **No Android RIL/IMS, no Halium, no vendor blobs.** The modem is spoken to through the recovered SIPC5 vocab;
  IMS through the host sockets.
- **Radio1 stays the authority.** The call manager lives inside radiod (or a sibling service on the same trusted
  bus) so apps never touch SIP, media or security state directly.
- **Modem-family abstraction.** Voice signalling is standards-level (3GPP/GSMA); the modem boundary should stay
  at the existing FMT/IIL vocabulary so a future modem family only re-implements transport, not call logic.

---

## 4. Reusable components from SMS development

| Component | Reuse | Notes |
|---|---|---|
| `ims_sip.c` (message build/parse, Via/Contact/Service-Route) | **Reuse unchanged** | Add request builders for INVITE/PRACK/UPDATE/ACK/CANCEL/BYE |
| `ims_sip_tr.c` (protected transport, REGISTER FSM, re-auth) | **Extend** | Add a dialog/transaction layer; keep registration FSM intact |
| `ims_security.c` (SA lifetime, SPI/port) | **Reuse unchanged** | `sa_lifetime_s` 7200; call media is not IPsec-protected (per carrier policy) |
| `ims_pdn.c`, `ims_iil.c`, `ims_init.c`, `iil_auth.c`, `iil_pdn.c` | **Reuse unchanged** | Bearer, AKA, identity |
| `ims_msisdn.c` (IMPUs, MSISDN) | **Reuse unchanged** | Needed for P-Preferred-Identity / From |
| `ims_service.c` (registration service state) | **Extend** | Add voice service capability reporting |
| `sms_service.c` (durable jobs, state machine patterns) | **Pattern reuse** | Call manager should mirror `sms_service`'s fail-closed semantics |
| `sms_store.c` (SQLite schema patterns) | **Pattern reuse** | New `calls`/`call_events` tables, same durability rules |
| `services/nuxel-radio-bridge` | **Reuse + extend** | Add hold/resume/DTMF methods; keep authorization model |
| `nuxel-phone-data` call log | **Reuse unchanged** | `nuxel_phone_add_call` already used by the dialer |
| `sms-notification` dedupe/burst logic | **NOT useful** for calls | Calls need ringtone policy, not notification dedupe |

Explicit non-reuse: the CS FMT call protocol (`fmt_call.c`, `call_service.c`) is **not** a VoLTE foundation,
but it can serve as a *fallback* only where a carrier still has CS (not this operator/device profile), and its
UI contracts are reused by the new call manager.

---

## 5. Existing voice implementation inventory

| File | What it is | VoLTE relevance |
|---|---|---|
| `tools/s10plus/s5000ap-05/src/call_service.c` | CS FMT call FSM (dial/answer/hangup, list polling, 30 s deadlines, fail-closed on loss) | **PARTIALLY_IMPLEMENTED (CS only)** — FSM patterns reusable, transport not |
| `tools/s10plus/s5000ap-05/src/fmt_call.c` | FMT modem call verbs (Dial/Answer/Release/GetList/Status) | **PARTIALLY_IMPLEMENTED (CS only)** — not used on LTE-only |
| `radiod.c::method_dial/answer_call/hangup_call/get_calls/get_voice_status` | Radio1 call APIs | **IMPLEMENTED_NOT_WIRED** for VoLTE — now returns NOT_SUPPORTED truthfully |
| `services/nuxel-radio-bridge/nuxel-radio-bridge.c` | Call/SMS forwarding with EUID guard | **IMPLEMENTED_NOT_WIRED** for new call verbs |
| `shell/nuxel-shell/nuxel-dialer/main.c` | Phone UI (keypad, recents, honest state) | **PHYSICALLY_VERIFIED (UI)**; ready for call-state wiring |
| `shell/nuxel-shell/nuxel-phone-data/nuxel-phone-data.c` | Call log store | **PHYSICALLY_VERIFIED** (used by dialer) |
| `ims_sip_tr.c` | SIP transport + REGISTER | **PHYSICALLY_VERIFIED** (registration); no dialogs |
| `ims_sip.c` | SIP message codec | **PHYSICALLY_VERIFIED** for REGISTER/MESSAGE; no SDP/INVITE |
| No file | INVITE/SDP/RTP/RTCP/AMR/dialog/session-timer | **NOT_IMPLEMENTED** |

`voice`/`audio` search across `tools/s10plus/s5000ap-05/src`: only CS call files and `GetVoiceStatus` reporting
`"audio_route":"unconfigured","ims":"unimplemented"` — an honest self-description that is still accurate.

---

## 6. Production call graph (as-is)

```
Phone UI → nuxel_radio_call("Dial") → Radio1Bridge (system bus, EUID guard)
   → radiod::method_dial → [Round 34.5] NOT_SUPPORTED
     (previous path: call_service_dial → fmt_call_dial → SIPC5 FMT call verb → modem CS)
   → radiod::call_notify → CallStateChanged / IncomingCall → bridge → dialer
GetCalls → call_service list (FMT) → a(ussb) → dialer
```

There is **no voice-over-PS path** anywhere in this graph. `GetVoiceStatus` reports CS registration
(`DENIED` on this profile). The UI and bridge are therefore ready to receive a new set of call states, but the
states they would receive from a VoLTE stack do not exist yet.

---

## 7. SIP signalling readiness

| Item | Status | Reference |
|---|---|---|
| IMS voice service capability / eligibility | **NOT_IMPLEMENTED** | no `audio`/`mmtel` feature tag in REGISTER; no Service-Caps check |
| Voice service eligibility (carrier) | **UNKNOWN** | not queried; SMS works is not proof of VoLTE entitlement |
| SIP dialog management | **NOT_IMPLEMENTED** | `ims_sip_tr` has transactions (REGISTER/MESSAGE), no dialog layer |
| Outgoing INVITE | **NOT_IMPLEMENTED** | — |
| Incoming INVITE | **NOT_IMPLEMENTED** | no INVITE dispatch in `ims_sip_tr_feed()` |
| Provisional responses (100/180/183) | **NOT_IMPLEMENTED** | — |
| Reliable provisional responses / PRACK (100rel) | **NOT_IMPLEMENTED** | required by TS 24.229 for many networks |
| UPDATE | **NOT_IMPLEMENTED** | needed for preconditions/session refresh |
| ACK (2xx and non-2xx) | **NOT_IMPLEMENTED** | — |
| CANCEL | **NOT_IMPLEMENTED** | — |
| BYE | **NOT_IMPLEMENTED** | — |
| Call rejection (486/603) | **NOT_IMPLEMENTED** | — |
| Call establishment DSL | **NOT_IMPLEMENTED** | — |
| Session timers (RFC 4028) | **NOT_IMPLEMENTED** | IR.92 requires session timer support |
| Call waiting / hold / resume | **NOT_IMPLEMENTED** | — |
| DTMF | **NOT_IMPLEMENTED** | in-band vs RFC 4733 decision pending |
| Caller identification (P-Asserted/P-Preferred-Identity) | **PARTIALLY_IMPLEMENTED** | identity/IMPU helpers exist; not applied to a dialog |
| Call-state correlation | **NOT_IMPLEMENTED** | — |
| Concurrent registration + call | **PARTIALLY_IMPLEMENTED (architecture)** | one protected transport exists; no dialog multiplexer |
| Recovery after interrupted calls | **NOT_IMPLEMENTED** | no dialog persistence |

---

## 8. Dialog and transaction management readiness

`ims_sip_tr.c` is a **transaction-oriented** state machine: it builds/awaits one outcome per REGISTER attempt
(`sreg_*`), matches responses by CSeq/Via, handles AKA re-auth during a renewal, and submits a SIP MESSAGE for
SMS. There is no branch/dialog registry, no `To`-tag pairing, no route-set storage per dialog, no multiple
concurrent clients.

VoLTE needs, at minimum:

- a **transaction layer** (client/server INVITE, non-INVITE), timer A–K as applicable (RFC 3261 §17);
- a **dialog layer** (Call-ID + local/remote tag, route set from Record-Route, remote target, CSeq, state);
- **multiple simultaneous dialogs** (one active call + one held/waiting) on one transport;
- **coexistence with registration refresh and SMS MESSAGE** without resetting each other;
- **persistence** sufficient to survive process restart without sending stale BYE/INVITE.

This is the single largest architectural change. It must be built beside the existing FSM, not by rewriting it.

---

## 9. SDP and codec readiness

| Item | Status | Notes |
|---|---|---|
| SDP offer/answer | **NOT_IMPLEMENTED** | no SDP builder/parser in tree |
| Codec negotiation (m=audio, rtpmap/fmtp) | **NOT_IMPLEMENTED** | — |
| AMR-NB (payload 96–127, octet-aligned) | **PARTIALLY_IMPLEMENTED (libraries present)** | `libopencore-amrnb.so.0`, `libgstamrnb.so` on device; not wired |
| AMR-WB | **PARTIALLY_IMPLEMENTED (libraries present)** | `libopencore-amrwb.so.0`, `libgstamrwbdec.so`; **no AMR-WB encoder found** (`libvo-amrwbenc` present) |
| Other applicable codecs (EVS etc.) | **UNKNOWN / NOT_IMPLEMENTED** | carrier-dependent; must not be advertised until supported |
| RTP payload formats | **NOT_IMPLEMENTED** | — |
| Media endpoint negotiation (host candidates) | **NOT_IMPLEMENTED** | — |
| Media direction negotiation | **NOT_IMPLEMENTED** | — |
| Codec licensing/distribution | **NOTE** | AMR patents require care for redistributed binaries; GStreamer/opencore are the likely path. Legal review is a non-technical blocker to shipping, not to internal testing |
| Codec availability on device | **PHYSICALLY_VERIFIED (presence)** | see §2 audio list from `ldconfig -p` |

TS 26.114 mandates AMR-NB (and AMR-WB where the network supports it) for MTSI; codec mode sets, `mode-change-*`,
`max-red`, and ptime negotiation all need explicit handling. None of it exists.

---

## 10. RTP/RTCP and media readiness

| Item | Status |
|---|---|
| RTP send/receive | **NOT_IMPLEMENTED** |
| RTCP (SR/RR, SDES, BYE) | **NOT_IMPLEMENTED** |
| Media sockets (UDP on rmnet/ims interface, correct source IP) | **NOT_IMPLEMENTED** |
| Jitter buffering | **NOT_IMPLEMENTED** |
| Packet loss concealment / FEC / redundancy (AMR `max-red`) | **NOT_IMPLEMENTED** |
| Packet reordering, timestamp/sequence handling | **NOT_IMPLEMENTED** |
| Media session lifecycle | **NOT_IMPLEMENTED** |
| Voice bearer requirements (dedicated IMS APN / QCI 1) | **NOT_IMPLEMENTED** — only the IMS signalling PDN exists |
| QoS requirements (QCI 1/2 bearer, RTP marking) | **NOT_IMPLEMENTED** |
| Media routing over the carrier interface | **NOT_IMPLEMENTED** — must bind to the IMS PDN address, not rmnet0 default |
| Media recovery and teardown | **NOT_IMPLEMENTED** |

The `ims_pdn` code brings up the IMS PDN for SIP. A **voice bearer** with a guaranteed bit rate and QCI 1 is a
separate request to the modem (IIL/QoS) and is not implemented; carrier networks will often reject or degrade a
call without it. This is a physical-network dependency that must be validated with the carrier.

---

## 11. Voice bearer and QoS readiness

- Current data path: `data_session.c`, `mobile_data.c`, `cellular_link.c` — **PS internet** on rmnet0 and the IMS
  PDN on rmnet1; no dedicated voice bearer.
- VoLTE requires the EPS bearer with QCI 1 (conversational voice) for media, plus the IMS signalling bearer
  (QCI 5). Bringing up QCI 1 is a modem QoS request via the recovered IIL/QMI vocabulary
  (`qbr_items.c` contains NV/QBR items; no runtime bearer request is implemented).
- **Status overall: NOT_IMPLEMENTED / BLOCKED on modem QoS API recovery** and on carrier policy.

---

## 12. Native audio subsystem readiness

Physically available (device inspection during this round):

- Kernel: Samsung ABOX codec; ALSA card `0: beyondmadera` with RDMA0..3, **RDMA1 → UAIF1/SIFS1 @48 kHz** is the
  working playback path (`services/nuxel-s10/README.md`, `alsa/99-nuxel-s10-default.conf`).
- PipeWire 1.4.11 + WirePlumber; static sink `alsa_output.hw_0_1`; **capture `alsa_input.hw_0_13`** (mic route
  service `nuxel-mic-route.service` active).
- `nuxel-audio-route.service`, `nuxel-mic-route.service`, `nuxel-audio-session.service` active after reboot.
- Codec libraries present (AMR-NB/WB, Opus, iLBC, GSM; GStreamer `rtp`, `rtpmanager`, `sdpelem`, `amrnb`, `amrwbdec`).
- Sound service `nuxel-soundd` plays files (POW cue) — proves *playback* only.

| Requirement | Status | Evidence / gap |
|---|---|---|
| Microphone capture | **DEVICE_TESTED (recorder)** / **NOT full-duplex** | mic route exists; Round audio work proved capture |
| Earpiece playback | **DEVICE_TESTED (playback)** | RDMA1 sink works |
| Speakerphone | **UNKNOWN** | no route test |
| Wired headset routing | **UNKNOWN** | — |
| Bluetooth call audio | **UNKNOWN** | Bluetooth stack separate; HFP/SCO path not audited |
| Audio route switching during a call | **NOT_IMPLEMENTED** | `GetVoiceStatus` says `audio_route=unconfigured` |
| Mute / volume during call | **NOT_IMPLEMENTED** | — |
| Echo cancellation | **NOT_IMPLEMENTED** | no AEC in PipeWire graph |
| Noise suppression | **NOT_IMPLEMENTED** | no RNNoise/ABOX NS wiring |
| Full-duplex | **UNKNOWN / BLOCKED** | never demonstrated; ABOX RDMA0/RDMA1 simultaneous capture+playback in call mode is the key unknown |
| ABOX call mode / DSP voice path | **UNKNOWN** | vendor firmware exists (`nuxel-abox-firmware-reload.service`); host-side call-mode programming not reverse-engineered |

**Do not assume microphone recording proves call audio.** The critical question is whether RDMA1 playback and
RDMA0 capture can run simultaneously at call cadence with the ABOX firmware's voice path, and whether echo
cancellation can live host-side (PipeWire) or must be done in the ABOX DSP. This is the largest hardware risk.

---

## 13. Incoming call readiness

`NOT_IMPLEMENTED`: no INVITE dispatch, no paging/ringing state, no answer path over IMS, no AudioFocus/route
change on ringing, no caller-ID from P-Asserted-Identity on a dialog. The ringtone/notification infrastructure
exists and can be reused for the ringing cue once a call manager emits `IncomingCall` for real.

Required: INVITE parse → 100 Trying → 180 Ringing (with/without 100rel) → 200 OK + SDP answer → ACK; reject path
(486/603/404); CANCEL handling; concurrent dialog policy.

---

## 14. Outgoing call readiness

`NOT_IMPLEMENTED`: no INVITE, no SDP offer, no provisional handling, no PRACK/UPDATE/ACK, no BYE. Dial today
returns `NOT_SUPPORTED` (truthful). Required: SDP offer with AMR-NB(+WB), 100rel, preconditions per carrier,
183/180 handling, 200 OK + ACK, early media policy, CANCEL on abandon, BYE on hangup, session timer refresh.

---

## 15. Phone application readiness

**Status: PARTIALLY_IMPLEMENTED / UI READY (PHYSICALLY_VERIFIED).**

- Keypad, backspace/clear, call action, Recents, contact/log store: present and verified.
- In-call presentation, mute, hold, audio route: **NOT_IMPLEMENTED** (no call state to show yet).
- Honesty: Dial shows the Radio1 `NOT_SUPPORTED` text; capability line says `VoLTE voice is pending`.
- Needed: call-state model (idle/calling/ringing/active/held/ended), in-call screen with timer/mute/hold/route,
  DTMF keypad during call, rejecting/answering, call-log states mapped from real events.

---

## 16. Radio1 and Radio1Bridge integration readiness

- Radio1 already exposes `Dial`, `AnswerCall`, `HangupCall`, `GetCalls`, `GetVoiceStatus`, and emits
  `CallStateChanged`/`IncomingCall`. These are the right **API shape** for VoLTE.
- Radio1Bridge forwards only `GetVoiceStatus`/`HangupCall` today (no Dial/Answer allowed). VoLTE will need
  `Dial`/`AnswerCall` allow-listed with the same EUID guard, plus **hold/resume/DTMF/route** verbs.
- The bridge's upstream is the privileged root bus; the Round 34.5 EUID check must be extended to every new
  call verb (no implicit trust of an app-supplied id).
- Idle remote-bus lifecycle must be hardened (`After=nuxel-radiod`, reconnect-on-owner) before calls depend on it.

---

## 17. Carrier voice service eligibility considerations

- The SIM is KPN 204-08 with a working IMS APN and SMS-over-IMS. **VoLTE entitlement is not implied.** The
  network must include `mmtel`/`audio` in the implicit registration set (3GPP TS 24.229 §5.1), and the UE must
  advertise the matching Service-Caps.
- This Nuxel profile has **not** sent `+g.3gpp.icsi-ref="urn%3Aurn-7%3A3gpp-service.ims.icsi.mmtel"` in REGISTER;
  adding it before voice exists would **advertise an unsupported capability** and must not be done until the
  call stack can honour it.
- Voice may require a separate IMS APN profile, an `ims` media bearer, and carrier provisioning checks (P-CSCF
  set, QoS). It may also be gated on device/IMEI provisioning — unknown and to be tested with the carrier.
- Emergency service (TS 24.229 §5.1.6, IR.92) is a distinct, safety-critical capability (§20).

---

## 18. Standards and interoperability gaps

Exact, applicable requirements (not "all options"):

| Spec | Requirement | Nuxel status |
|---|---|---|
| TS 24.229 §5.1 | REGISTER with IMS communication service identifiers (mmtel) and Service-Caps | **GAP** |
| TS 24.229 §5.4 / RFC 3261 | INVITE dialog, ACK, BYE, CANCEL, route sets | **GAP** |
| TS 24.229 / IR.92 | 100rel/PRACK, UPDATE, session timers (RFC 4028) | **GAP** |
| TS 26.114 (MTSI) | AMR-NB (and WB) negotiated via SDP, octet-aligned, mode sets, ptime | **GAP** |
| TS 26.114 | RTP/RTCP, jitter resilience, redundancy (`max-red`) | **GAP** |
| TS 33.203 | IPsec for SIP signalling (implemented) and **media security policy** | signalling **PASS**, media **GAP** |
| IR.92 | IMS profile for voice: codecs, QoS (QCI 1), session timers, emergency | mostly **GAP** |
| RFC 3550/3551 | RTP/RTCP A/V profile | **GAP** |
| RFC 4733 | DTMF (if in-band not chosen) | **GAP** |
| RFC 3325/3326 | P-Asserted/Preferred-Identity and Privacy | helpers partial |

---

## 19. Security and lifecycle considerations

- **Trust boundary:** keep SIP, media and key material inside radiod (root, compositor bus). The bridge must
  never expose an unbounded dial/DTMF/route API to uid-1000 apps without the EUID guard + app permissions.
- **Registration coexistence:** a call must not tear down or reset the registration FSM; SMS and calls must share
  the protected transport with separate CSeq/dialog space.
- **Media security:** confirm whether the carrier requires SRTP for VoLTE media; the current IPsec setup protects
  SIP only. Do not assume SRTP or plain RTP without evidence.
- **Lifecycle:** phone process death must not leave a half-open dialog or a stale bearer; call state must be
  recoverable from disk and reconciled against the network (re-INVITE/BYE) rather than blindly retried.
- **Privacy:** no subscriber secrets (IMPI/keys, IMPU beyond what the UI needs) in app logs; call log stores
  numbers (already the shared-store policy).

---

## 20. Emergency-call limitations

**NOT_IMPLEMENTED and explicitly out of scope for this round.** `radiod::method_dial` still refuses `112`/`911`
with `NOT_SUPPORTED`. Emergency calling has different routing, location (e.g. eCall/NG112 / AML), and regulatory
requirements; it must be treated as a separate, safety-critical workstream and must never be claimed until
verified with the carrier and emergency authorities. **No emergency test calls were placed.**

---

## 21. Existing tests and missing tests

Existing and passing (this round):

- `test_ims_sip.c`, `test_ims_sip_tr.c` (transport/REGISTER/MESSAGE), `test_ims_sms.c`, `test_ims_security.c`,
  `test_ims_service.c`, `test_ims_pdn.c`, `test_ims_init.c`, `test_ims_iil*`, `test_iil_auth.c`, `test_fmt_call.c`,
  `test_call_service.c`, `test_sms_service.c`, `test_sms_store.c`, `test_sms_pdu.c`.

Missing (to be created):

- `test_ims_dialog.c` — INVITE/ACK/BYE/CANCEL/PRACK/UPDATE, To-tag pairing, route sets, timer expiry.
- `test_sdp.c` — offer/answer, AMR mode sets, ptime, direction, malformed rejection, codec refusal.
- `test_rtp.c` / `test_rtcp.c` — sequence/timestamp, jitter, reorder, loss concealment hooks, SR/RR.
- `test_call_manager.c` — state machine, concurrent dialogs, hold/resume, persistence, BYE on teardown.
- `test_volte_peer.c` — an isolated IMS peer on the host netns (no carrier) simulating 100rel, preconditions,
  AMR negotiation, session timer, carrier reject codes.
- Audio loopback harness — full-duplex ABOX capture/playback with latency and AEC measurement.

---

## 22. Exact source files requiring modification

| File | Change |
|---|---|
| `tools/s10plus/s5000ap-05/src/ims_sip_tr.c/.h` | dialog/transaction layer, INVITE dispatch, 100rel, session timers, concurrent dialogs, coexistence with REGISTER/SMS |
| `tools/s10plus/s5000ap-05/src/ims_sip.c/.h` | INVITE/PRACK/UPDATE/ACK/CANCEL/BYE builders + SDP body carriage; headers (Allow, Supported, Require, Session-Expires, P-* identity) |
| NEW `tools/s10plus/s5000ap-05/src/sdp.c/.h` | SDP offer/answer, m=audio, rtpmap/fmtp AMR-NB/WB, ptime, direction, malformed handling |
| NEW `tools/s10plus/s5000ap-05/src/rtp_media.c/.h` | RTP/RTCP sockets on IMS PDN, jitter buffer, AMR payload, SR/RR, teardown |
| NEW `tools/s10plus/s5000ap-05/src/call_manager.c/.h` | call FSM, dialog registry, hold/resume, DTMF, persistence, recovery |
| NEW `tools/s10plus/s5000ap-05/src/audio_call.c/.h` | PipeWire/ALSA full-duplex stream, AEC/NS, route selection |
| `tools/s10plus/s5000ap-05/src/radiod.c` | wire Dial/Answer/Hangup/GetCalls/GetVoiceStatus to the call manager; extend Radio1 vtable (Hold/Resume/Dtmf/SetAudioRoute); telephony diagnostics |
| `tools/s10plus/s5000ap-05/src/radiod.h`, `call_service.c/.h` | keep CS path intact; add IMS path selection |
| `tools/s10plus/s5000ap-05/src/ims_service.c` | register Service-Caps/mmtel only when voice stack is live |
| `tools/s10plus/s5000ap-05/src/ims_pdn.c`, `mobile_data.c` | voice bearer QoS request (QCI 1) when supported |
| `services/nuxel-radio-bridge/nuxel-radio-bridge.c` | allow-list Dial/Answer + new call verbs with EUID guard; upstream lifecycle |
| `shell/nuxel-shell/nuxel-phone-data/nuxel-radio-client.{c,h}` | call-state model, DTMF/hold commands |
| `shell/nuxel-shell/nuxel-dialer/main.c` | in-call screen (timer/mute/hold/route), answer/reject, call log states |
| `services/nuxel-s10/{pipewire,wireplumber,alsa}/*` | call-mode graph, AEC, routes |
| `tools/s10plus/s5000ap-05/build.sh` | build new units + tests |

---

## 23. Missing components (summary)

1. SIP dialog/transaction engine for INVITE dialogs.
2. SDP offer/answer engine (AMR-NB/WB).
3. RTP/RTCP media transport with jitter/loss/redundancy.
4. Voice bearer / QCI 1 QoS request to the modem.
5. Native call manager (state, hold/resume, DTMF, persistence).
6. Full-duplex ABOX call-mode audio + AEC/NS.
7. IMS voice Service-Caps/mmtel signalling (only once #1–#6 exist).
8. In-call Phone UI.
9. Voice-specific tests and an isolated IMS voice peer.
10. Emergency-call support (separate workstream).

---

## 24. Known blockers

| Blocker | Type | Mitigation |
|---|---|---|
| Carrier VoLTE entitlement unknown | external / physical | query with the carrier; test after stack exists |
| No modem QoS/voice-bearer API implemented | reverse engineering (modem IIL) | recover the QoS request path; validate QCI 1 |
| ABOX full-duplex/call-mode unclear | hardware / firmware | bench loopback test early (Round V2) |
| AEC/NS not present | software (PipeWire/WirePlumber) | add host-side AEC or use ABOX DSP once mapped |
| Natural IMS renewal not yet observed (Round 34.5 carry-over) | observation | watch ≈16:50 CET; needed before calls that rely on long-lived registration |
| Bridge upstream lifecycle | software | `After=` + reconnect before calls |
| Codec licensing/distribution (AMR) | legal | confirm distribution terms before shipping |
| SRTP policy unknown | carrier | confirm with carrier; add if required |

---

## 25. Estimated completion percentages (method)

**Scoring rule.** Each capability area is scored as `0.5·implementation + 0.5·physical_verification`, where
implementation is the weighted fraction of mandatory items with code/tests and physical verification is the
fraction proven on the real device/carrier. Weights are *mandatory-path* items only (optional features do not
inflate the score). A component marked PHYSICALLY_VERIFIED counts 1.0 on both axes; HOST_TESTED counts 0.5
implementation and 0 physical; NOT_IMPLEMENTED 0.

| Area | Implementation | Physical | Area score | Basis |
|---|---:|---:|---:|---|
| Shared IMS foundation | 90 % | 70 % | **80 %** | REGISTER/AKA/IPsec/SIP/SMS proven; natural renewal + call coexistence untested |
| VoLTE-specific signalling | 5 % | 0 % | **2.5 %** | no INVITE/dialogs/100rel/timers |
| SIP dialog management | 0 % | 0 % | **0 %** | transaction-only transport |
| SDP and codecs | 10 % | 0 % | **5 %** | codec libraries present; no SDP/negotiation |
| RTP/media | 0 % | 0 % | **0 %** | absent |
| Audio integration | 25 % | 10 % | **17.5 %** | playback/capture proven separately; no full-duplex call audio/AEC |
| Phone application | 55 % | 40 % | **47.5 %** | keypad/recents/honest state proven; no in-call UI |
| Carrier interoperability | 15 % | 20 % | **17.5 %** | IMS SMS interop proven; voice entitlement unknown |
| **Overall VoLTE** | **~14 %** | **~4 %** | **~12 %** | weighted mandatory-path average |

These are estimates with stated basis, not measurements. The overall figure is intentionally conservative: a
call needs every one of signalling, SDP, media, audio and bearer to work end-to-end.

---

## 26. Dependency graph

```
[existing, DONE]  CP ← FMT ← radiod ── IMS PDN ── AKA ── IPsec ── SIP transport ── REGISTER
                                                             │
                ┌────────────────────────────────────────────┴─────────────┐
                │                                                          │
        [DONE] SMS MESSAGE (TS 24.341)                         [NEW] SIP dialog engine
                                                                       │
                                                   ┌───────────────────┴──────────────────┐
                                                   │                                      │
                                          [NEW] SDP offer/answer                 [NEW] 100rel/PRACK,
                                          (AMR-NB/WB)                             UPDATE, session timers
                                                   │                                      │
                                                   └──────────────┬───────────────────────┘
                                                                  │
                                                       [NEW] call manager (FSM, hold, DTMF)
                                                                  │
                                          ┌───────────────────────┼─────────────────────────┐
                                          │                       │                         │
                                   [NEW] RTP/RTCP            [NEW] voice bearer QoS   [NEW] audio call path
                                          │                       │                 (ABOX full-duplex, AEC)
                                          └───────────────────────┼─────────────────────────┘
                                                                  │
                                                   Radio1 vtable ← Radio1Bridge ← Phone UI
                                                                  │
                                                       [DONE] call log (nuxel-phone-data)
```

Registration, security and SMS are prerequisites that must keep working; none of the new boxes may reset them.

---

## 27. Recommended implementation rounds

Minimum credible sequence: **7 implementation rounds** (V1–V7) plus a production-acceptance round (V8).
Rounds V1, V3 (part), V5, V6 and V7 tests are mostly offline; V2, V4, V8 require the device.

| Round | Objective | Components | Offline tests | Physical tests | Device needed? | Gate |
|---|---|---|---|---|---|---|
| **V1** | SIP dialog + transaction layer beside the REGISTER FSM | `ims_sip_tr`, `ims_sip` | dialog/timer/branch unit tests; `test_ims_dialog` | none | No (host netns peer) | dialog FSM passes; REGISTER/SMS tests still green |
| **V2** | ABOX full-duplex + AEC feasibility bench | `audio_call`, PipeWire/WirePlumber, ALSA route | latency/jitter measurement harness | 60 s duplex loopback with AEC, no xruns | **Yes** | duplex capture/playback + AEC acceptable |
| **V3** | SDP + codecs (AMR-NB first, then WB) | `sdp.c`, `rtp_media.c` payload | `test_sdp`, `test_rtp` with fixtures | decode/encode loopback on device | Yes (codec loop) | offer/answer + AMR round-trip |
| **V4** | RTP/RTCP + media session over the IMS PDN + voice bearer | `rtp_media.c`, `ims_pdn`, `mobile_data` | `test_rtcp`, jitter/loss | loopback to host peer over rmnet1; QoS bearer request readback | **Yes** | media path + QCI 1 when carrier supports |
| **V5** | Call manager + Radio1 API + bridge + persistence | `call_manager.c`, `radiod.c`, bridge | `test_call_manager` | state transitions only (no carrier call) | Optional | FSM/hold/persist pass; bridge auth tests |
| **V6** | Outgoing VoLTE call (INVITE → 200 OK → ACK → BYE) | call manager + signalling + media | `test_volte_peer` full scenario | **first real MO VoLTE call** (owner-authorized) | **Yes** | audio both ways with a real callee |
| **V7** | Incoming VoLTE call + Phone in-call UI | signalling, call manager, `nuxel-dialer` | peer-driven MT scenario | **real MT VoLTE call** + UI walk-through | **Yes** | answer/reject/hold/mute/route work |
| **V8** | Production acceptance: concurrency, renewal, reboot, network recovery, emergency gap statement | all | full suite + sanitizers | MO/MT, concurrent SMS+voice, reboot persistence | **Yes** | §28 criteria |

Estimated: **7 engineering rounds + 1 acceptance round**; V2 and V6/V7 carry the highest risk (hardware/carrier).
V1 and V5 are the deep architectural rounds and should not be compressed.

---

## 28. Physical acceptance criteria

1. MO VoLTE call: INVITE sent over protected IMS transport, 183/180 handled, 200 OK + ACK, BYE on hangup;
   call log state truthful; no CS fallback.
2. Bidirectional audio verified by a human callee (and a recording), full-duplex, no echo.
3. MT VoLTE call: INVITE received, Phone rings, answer/reject, audio both ways, BYE.
4. Hold/resume, mute, audio route (earpiece/speaker) during a live call.
5. Concurrent SMS + voice over one registration; registration stays `registered` throughout.
6. Natural registration renewal during a call (long call) without dropping audio.
7. Reboot persistence: registration, call log, no stale dialog.
8. Network interruption recovery: no stuck dialog, no duplicate call, re-registration works.
9. No unintended media/IPsec/registration side effects; SMS acceptance still passes (`sms34.5.md` matrix).
10. Emergency-call behaviour explicitly documented as unimplemented.

---

## 29. Rollback and deployment considerations

- New units are userspace only (`sdp`, `rtp_media`, `call_manager`, `audio_call` inside radiod or a sibling
  service); no partition writes, no modem NV/EFS changes.
- Keep the existing `nuxel-radiod` binary and SMS database rollback copies (Round 34.5 layout:
  `/var/lib/nuxel/rollback-r34.5/`) before each deployment.
- Deploy each round behind a build-time/runtime feature gate so SMS/LTE/registration can be rolled back by
  binary swap without touching the store.
- Never advertise `mmtel`/audio Service-Caps in REGISTER until V6 is physically working.
- Keep Phone UI wired to the honest `NOT_SUPPORTED` path until the call manager is live; never fake a call.

---

## 30. Explicit verdict

```
READY_FOR_VOLTE_IMPLEMENTATION = TRUE
```

The native IMS foundation is physically proven and reusable; the missing components are identified, the
dependency order is known, and the first steps (dialog layer, ABOX duplex bench, SDP) are suitable for offline
development. This verdict means **ready to begin implementation**, not **ready to make calls**.

---

# APPENDIX — CONTINUATION VERIFICATION (2026-11-28, Round 34.5 #2)

*Corrections and evidence gathered after the interrupted session. Section numbers
refer to the main report above.*

## A. Repository-location correction

The README/section numbering says "cite exact repository paths". On `main` (the
merged release tree) the S5000AP sources path `tools/s10plus/s5000ap-05/` is
**absent**. They exist only on `cs/mob-round35-stage06` (184 files, radiod 4 827
lines) and in the deployed binaries. Every path in §2–§8 above was inspected
there. This does not change a verdict; it changes where the files live and is the
largest single repository risk for the VoLTE work (§24 of the main report gains
this item).

## B. Re-confirmed status of the foundation (this continuation)

- radiod, bridge, notifications hub running (`systemctl list-units` all active).
- IMS: `GetImsStatus → registered`, `sms_transport=available` (surfaced in the
  live Messages banner: `Native SMS ready over IMS (registered)`).
- SMS store: `integrity_check=ok`, 17 logical messages, one submission row per id.
- Native Messages (this release) renders every stored SMS and resolves contact
  names — the UI layer the Phone app will mirror for calls.

## C. Voice-specific readiness (unchanged by this continuation)

No INVITE/SDP/RTP/AMR/DTMF/hold code was added. The dialer is the Round-34.5
native-Radio1 build that reports `NOT_SUPPORTED: Native VoLTE voice service is
not implemented; no call was placed`. The readiness percentages in §1 stand:

| Area | Implementation | Physical |
|---|---|---|
| Shared IMS foundation | ~80 % | high (registration/SMS/security proven) |
| VoLTE signalling | ~0 % | 0 % |
| SIP dialog management | ~0 % (transaction FSM only) | 0 % |
| SDP / codecs | ~0 % | 0 % |
| RTP/RTCP / media | ~0 % | 0 % |
| Audio integration | partial (playback/capture proven, duplex/call-mode not) | low |
| Phone application | UI + honest state; no call wiring | n/a |
| Carrier interoperability | eligibility unverified | none |
| **Overall** | **~12 %** | **~4 %** |

Verdict `READY_FOR_VOLTE_IMPLEMENTATION = TRUE` remains correct **for the
foundation**, and that foundation is what this release keeps intact.
