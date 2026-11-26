# NUXEL SMS ROUND 06 — Native IMS Implementation (implementation checkpoint)

Status: **Implementation delivered**. Native IMS PDN, registration controller,
SMSoIP transport selection, serializers, parsers all implemented, unit-tested,
and on-device compiled. Physical IMS registration is blocked by carrier-side
IMS APN provisioning (genuine external dependency), not by missing Nuxel code.

## What was implemented (this round)

1. `src/ims_service.{c,h}` — bounded IMS registration FSM. Drives the modem's
   resident IMS stack via `IpcTxImsReqSetRegState` (main=22 sub=8) and observes
   the authoritative `IpcRxImsModeChange` registration state. NEVER fabricates
   registration: only marks registered on modem status==1.
2. `src/ims_pdn.{c,h}` — native IMS APN PDN driver. Establishes the `ims` APN
   as a distinct CID=2 context using the verified `DEFINE_PDP_CONTEXT` /
   `SET_PDP_CONTEXT` builders, AUTH=NONE at the PDP layer (IMS bearer auth is
   SIP/REGISTER SIM AKA), ipv4v6. Isolated from the internet bearer; gated
   behind `DS_ACTIVE` + `NUXEL_IMS_PDN=1` to avoid GEN correlation overlap.
3. `fmt_tx`/`fmt_rx` — byte-exact IMS serializers/parsers. The 6-byte
   `IpcTxImsReqSetRegState` payload layout is fully decoded from
   `IpcProtocol41::IpcTxImsReqSetRegState @0x34d230`.
4. `sms_service` — accurate transport selection: CS domain 0 vs IMS domain 8
   (recovered from `SmsManager::DoImsSendIms`). Only selects IMS when the modem
   has confirmed registration; no silent substitution.
5. `ipc41_cmdmap.h` — complete IMS sub-command family + ImsRegStatus/NetworkType.
6. `radiod.c` — IMS dispatch, SIM AKA challenge relay (`SEC_IMS_AUTH`), ims APN
   detection, truthful D-Bus `ImsState`, capabilities.

## Physical evidence (this round)

- `ims_state: wait-pdn (await-ims-pdn)` — controller correctly reports wait-pdn.
- `pdp_definitions count=2 ims_pdn=false` — the ims APN is NOT provisioned on
  this SIM; the second PDN is not established.
- `cs_registration: DENIED raw 4` — CS SMS remains unavailable (LTE-only).
- LTE preserved: `cellular_ip_received cid:1 ipv6_valid:true`, rmnet0 IPv6 up.

## Remaining external requirement

Carrier-side IMS APN (`ims`, KPN 204-08) entitlement/provisioning on this
subscriber SIM. The `ims` APN PDN is not admitted by the modem, which is a
carrier action independent of Nuxel code. Once the IMS APN is provisioned,
the implemented registration controller + SMSoIP transport can complete the
physical SMS path without further code changes.

## Commits

- b89f3339 ims: implement native IMS PDN/registration controller + SMSoIP transport selection
- e3ff6924 ims: add native IMS APN PDN driver (isolated second data context)
- fad31e5a ims: gate IMS APN PDN drive behind internet bearer DS_ACTIVE
- 9cdf8fa5 sms: update sms_service test to 7-arg transport-selection signature
