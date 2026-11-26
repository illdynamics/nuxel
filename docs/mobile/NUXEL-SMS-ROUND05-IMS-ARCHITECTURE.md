# NUXEL SMS ROUND 05 — IMS Transport Architecture (evidence-backed)

Status: **Implementation continuation checkpoint**. Root cause definitively
established; IMS transport design recovered from the matching EFUJ2 vendor
RIL (`libsec-ril.so`, GNU Build ID 60889dd714394ae0db7c2ecc2bf2740f).

## Root cause (physical evidence)

Live radiod state (round 05, KPN 204-08):

- PS registration: `REGISTERED_HOME` (network mode readback mask 11, LTE).
- CS registration: `DENIED` (raw state 4), reject cause 0.
- network mode auto (mask 0x0b) already applied; no 2G/3G CS fallback exists
  at the current serving cell.
- Prior physical SMS submission: `result 0x0002` (CS No Service), modem ref 158.

Conclusion: **KPN provides LTE-only service here. CS/SGs SMS is unavailable.
SMS requires IMS (SMSoIP).** This is carrier condition #2 + #7 (IMS deployed
but Nuxel does not consume the `ims` provisioning) + #4 (native userspace does
not implement the IMS transport).

## Stock Samsung SMS transport architecture (recovered from libsec-ril.so)

1. CS SMS: `SmsManager::DoSendSms` -> `DomainSelector::GetDomain()` ->
   `ConvertDomainToIPC(domain)` -> `IpcTxSendSms(domain_wire, ...)` with
   `domain_wire=0` (CS). This is what Nuxel already implements.

2. IMS SMS: `DomainSelector::GetDomain()` returns 4 (IMS) when
   `ImsManager::IsRegistered()` and registered network type == LTE. Then
   `SmsManager::DoImsSendIms()` routes through the modem IMS stack.

`ConvertDomainToIPC` mapping (VERIFIED @0x344b98):
    GetDomain 0 -> wire 2;  1 -> 3;  2 -> 0 (CS);  3 -> 1.

## Stock Samaritan IMS stack is IN the modem, AP-driven

The modem firmware (modem.bin, 46 MB) contains a full IMS/VoLTE stack (MMC,
PLMN, EMM combined/SGs, SRVCC, IMS registration). The AP drives it over SIPC5
`main=22 (IMS)`:

- `IpcTxImsReqSetRegState`  (0x318920/0x31... ) — request IMS registration.
- `IpcTxImsAuthResp`        — forward SIM AKA response to modem.
- `IpcTxImsReqDeregistration` — deregister.
- `IpcRxIms` / `IpcRxImsModeChange` — registration state/mode notifications.

SIM auth: `SEC` main=5 sub=9 `SEC_IMS_AUTH` and sub=14
`SEC_IMS_SUPP_AUTH_TYPES`.

IMS connectivity: dedicated `ims` APN (KPN MCC-MNC 204-08) with chap auth,
established as a second PDN alongside the working `internet` bearer.

SDM (modem service domain) commands: `SdmImsDomainGet/Set`, `SdmImsModeGet/Set`,
`SdmImsPortGet/Set`, `SdmImsSmsFmtGet/Set`, `SdmImsTimerGet/Set` — these select
the SMSoIP format and IMS SMS transport.

## Remaining implementation (does not exist yet in Nuxel)

1. `fmt_tx`/`fmt_rx` serializers for `main=22 IMS` (registration/auth drive).
2. IMS APN (`ims`) PDN establishment alongside the internet bearer.
3. Native IMS registration state machine (drive modem IMS, report truthful state).
4. SMSoIP SMS submission via IMS when CS/SGs unavailable.
5. Carrier provisioning (`ims` APN) consumption.

None of this can be fabricated; physical validation requires the modem to
actually register with KPN IMS before the held authorized SMS may be released.
