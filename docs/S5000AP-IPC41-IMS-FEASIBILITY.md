# S5000AP IMS / VoLTE Feasibility Research Matrix

Round 07, subjob C. Target device is the **Samsung Galaxy S10+ SM-G975F
(beyond2lte, Exynos 9820, Shannon S5000AP, baseband G975FXXSEFUJ2)** running
native Nuxel Linux. The existing `docs/volte-carrier-strategy.md` targets the
Pixel 10 Pro XL (mustang, Exynos 5500 over MHI v2); it is a **different
modem/transport** and is not reused as evidence for the S5000AP. This matrix
derives every S5000AP claim from the actual pinned vendor binary and reports
the honest outcome per gate.

Evidence source: vendor `libsec-ril.so`, SHA-256
`b02bd095ae44a991b3cb676e584b3209a947160c22e678578f8b0c877e282cb3`
(Android ARM64 ELF, recovered read-only, never redistributed).

## 1. Vendor IMS stack presence (proved from symbols)

`nm -D` on the vendor binary shows a complete proprietary IMS implementation:

- `ImsManager` class: `Initialize`, `DoImsRegistrationState`,
  `ReqImsDeregistration(Reason)`, `IsRegistered(Eib)`, `OnSetImsRegistrationDone`,
  `SaveImsRegistrationInfo`, `DoOemGet/SetImsSdmSetting`, `OnImsPreference`,
  `IsSupportVolteRoaming`, `DoImsHandoffInfoNoti`, `OnEpdnConnected/Disconnected`.
- `ModemProxy`: `SetSipParam`, `SetImsCallList`, `SetImsRegState`,
  `SendImsAuthResp`, `ReqImsDeregistration(E911)`.
- `IpcProtocol41` wire exporters/parsers: `IpcTxSetSipParam`,
  `IpcTxImsAuthResp`, `IpcRxSecImsAuth`, `IpcRxSdmSipTimer`,
  `IpcRxSdmImsSipPort`, `IpcRxSdmImsTestMode`, `IpcRxNetVolteTestmode`,
  `IpcTxGet/SetVolteTestmode`, `IpcTxImsReqSetRegState`, `IpcTxGet/SetImsSdmSettings`,
  `IpcTxCallSetSrvccState`, `IpcRxQmiIms`, `IpcRxImsModeChange`,
  `IpcRxQmiImsEcmFoundSvc`.
- `ImsDefE911RatDeterminer` (emergency/e112 device logic) and a full
  supplementary-service (`Ss*`) family.

Command-family IDs recovered into `ipc41_cmdmap.h` (source-derived, not invented):
`IPC41_MAIN_IMS = 22`, `IPC41_MAIN_QMIIMS = 64`, `IPC41_SEC_IMS_AUTH = 9`,
`IPC41_SEC_IMS_SUPP_AUTH_TYPES = 14`.

Conclusion: the **modern is IMS-capable on its Shannon CP**, and the vendor RIL
contains a matching IMS client. That is a *hardware/firmware capability*, NOT a
Nuxel support claim, and does not make IMS available in userspace.

## 2. What Nuxel has today (truthful)

- Data path: native `radiod` establishes the LTE default EPS bearer and real
  IPv6 routing (round 06 verified). This is the transport IMS media would ride,
  but it is data connectivity, not voice.
- CS voice: native call control (`fmt_call.c`/`call_service.c`) implements
  dial/answer/release/list over the radio stack, but two-way audio routing is
  **unconfigured** (`GetVoiceStatus` reports `audio_route=unconfigured`).
- VoLTE/IMS: **no native signaling or audio path exists**. `GetCapabilities`
  reports `ims=false`, `volte=false`. This is honest, not a placeholder.

## 3. Feasibility matrix

| Path | Requires | Lawful in isolated runtime? | Verdict |
|---|---|---|---|
| Vendor `libsec-ril.so` IMS | Android RIL runtime (libcutils/ril.h framework, vendor init, `/vendor` paths), proprietary AUTH over `SEC_IMS_AUTH` | Only if Samsung binaries run under a compatible isolated Android-ish userspace; no attestation of legality in this repo | `IMS_BLOCKED_VENDOR_STACK` |
| Vendor `ims`/`imsservice` daemons | Additional proprietary binaries not present in the recovered set (`rcs`, `imsservice`, CSC config) | Same as above | `IMS_BLOCKED_VENDOR_STACK` |
| FOSS IMS (oFono-IMS / pmtel / Enosium) | SIP/RTP client on LTE bearer + `SEC_IMS_AUTH`/AKA interworking for the SIM ISIM | Partial; none is carrier-complete | `IMS_UNSUPPORTED` (no mainline-complete client) |
| Carrier provisioning | KPN (PLMN 20408) IMS entitlement + `ims` APN + handset approval | Requires carrier account action, independent of any Nuxel code | `IMS_BLOCKED_PROVISIONING` |
| Emergency e112 over IMS | Regulatory/handset certification; explicitly out of scope | Not pursued; no emergency dialing | `IMS_UNSUPPORTED` |

## 4. Independent components needed (pinned)

1. **ISIM/IMPI/IMPU credentials** from the SIM (`SEC_IMS_AUTH`, USIM ISIM app) —
   only the CP can request these; the AP merely relays AKA challenges via
   `IpcRxSecImsAuth`/`IpcTxImsAuthResp`.
2. **SIP signaling** over the `ims` PDN bearer (`SetSipParam`, SIP port/timer
   SDM settings).
3. **RTP media** with AMR-WB codec over the same bearer (not present natively).
4. **Audio path**: Exynos ABOX codec + ALSA/UCM `VoiceCall` verb + PipeWire
   routing (scaffolded for the *other* device only; not validated on S5000AP).
5. **P-CSCF/S-CSCF discovery** via PCO from the `ims` PDN (CP-supplied).

Without (1) and carrier-provisioned entitlement, none of (2)–(5) can be
exercised. None of these is a kernel/DTS problem; all are userspace + carrier.

## 5. Verdict

**IMS/VoLTE = BLOCKED.**

- `IMS_BLOCKED_VENDOR_STACK`: a complete IMS client exists only inside
  proprietary Samsung binaries (`libsec-ril.so` + the `ims`/`imsservice`/
  `rcs` daemons not present in the recovered set); lawful isolated execution and
  AKA interworking are not established in this repository.
- `IMS_BLOCKED_PROVISIONING`: even with a stack, KPN must provision IMS
  entitlement on the subscriber and approve the handset; that is a carrier
  action independent of Nuxel.
- `IMS_UNSUPPORTED`: no mainline-complete open IMS client exists to substitute.

This does **not** fail basic LTE: the modem is LTE-registered and the default
data bearer works. IMS is a distinct deliverable and remains at 0%.
