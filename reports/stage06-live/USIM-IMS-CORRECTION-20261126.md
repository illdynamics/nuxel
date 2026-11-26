# USIM IMS correction — 2026-11-26

This supersedes the ISIM/entitlement conclusions in sms8.md–sms11.md.
SMS has **not** been submitted. Absence of ISIM does not establish lack of
IMS entitlement. The inspected native implementation has local defects and
has not performed a legitimate SIP registration attempt.

## Artifact provenance

- Actual device CP firmware: G975FXXSEFUJ2 (previously identified; recheck at
  deployment without printing equipment/subscriber identifiers).
- `.vendor-ro/libsec-ril.so`, the mounted device vendor library, and the
  library extracted from `packs/SAMFW.COM_SM-G975F_TNL_G975FXXS9DTK9_fac/vendor.img`
  have Build ID `60889dd714394ae0db7c2ecc2bf2740f`.
- Local library and pack-extracted library are byte-identical: SHA-256
  `b02bd095ae44a991b3cb676e584b3209a947160c22e678578f8b0c877e282cb3`.
- Stock `system/priv-app/imsservice/imsservice.apk` extracted from the DTK9 AP
  archive has SHA-256
  `a55daa764af90ef134164c767f10c9eb4695c7b7962d7b0be701e5e583631ef8`.
  This is the APK accompanying the identical RIL in the available pack, **not
  an independently identified EFUJ2 system APK**. Static analysis only; no
  Android software was executed on the phone.

## Standards and stock fallback

TS 24.229 5.1.1.1A and C.2 specify deriving IMS parameters when a USIM is
present without an ISIM. Lack of stored ISIM identities does not rule out
legitimate IMS registration. [Release 15 specification](https://www.etsi.org/deliver/etsi_ts/124200_124299/124229/15.08.00_60/ts_124229v150800p.pdf).

TS 23.003 13.2, 13.3 and 13.4B specify the home domain, private identity and
temporary public identity derived from the subscription's IMSI and MCC/MNC.
The MNC must be zero-padded to three digits in the domain; its actual length
must not be guessed from IMSI length. [Release 15 specification](https://www.etsi.org/deliver/etsi_ts/123000_123099/123003/15.08.00_60/ts_123003v150800p.pdf).

TS 33.203 8.0 permits USIM as the IMS security application, while preferring
ISIM when both applications exist. [Release 15 specification](https://www.etsi.org/deliver/etsi_ts/133200_133299/133203/15.01.00_60/ts_133203v150100p.pdf).

TS 31.102 7.1 specifies the USIM AUTHENTICATE command, including the 3G
security context and authentication/synchronization outcomes. The long-term
SIM key remains inside the card. [Release 15 specification](https://www.etsi.org/deliver/etsi_ts/131100_131199/131102/15.10.00_60/ts_131102v151000p.pdf).

Static DEX analysis of the packaged Samsung
`com.sec.internal.ims.imsservice.SimManager` shows:

- `getImpuFromSim()` takes the derived-identity path when `hasIsim()` is false.
- `getDerivedImpi()` and `getDerivedImpu()` format IMSI-based IMS identities.
- `getIsimAuthentication(String)` selects application type 5 when ISIM is
  loaded, otherwise application type 2 when the SIM is loaded.
- Its overload invokes `ITelephonyManager.getIccAuthentication` with the
  selected application and authentication context 129 (`0x81`, 3G).

The identical native RIL implements the corresponding path:
`SimManager::DoSimAuthentication` at `0x1f2058` preserves USIM auth selector 2
when no matching ISIM application is found, then invokes `DoUiccAuth`.
`UiccAuth::UpdateAuthTypeByAid` at `0x2bbf70` changes it to selector 0 only for
a matching ISIM AID. An ISIM-only request has a separate handler at `0x1ebd70`;
that handler's restrictions must not be generalized to all authentication.

## Corrected protocol interpretation

1. `IpcTxImsReqSetRegState` at `0x34d230` reports existing AP IMS registration
   state to the CP. `ImsManager::OnImsRegistrationChanged` at `0x23d528` calls
   `ModemProxy::SetImsRegState` through vtable offset 4408. Sending status
   REGISTERED does not perform SIP REGISTER or prove carrier acceptance.
2. CP `IpcRxIms` at `0x34d178` dispatches subcommand **16** to
   `IpcRxImsModeChange` at `0x34cfa0`. That constructs a mode-switch broadcast
   intent. It is not a status-byte registration event. The previous decoder
   incorrectly promoted any main-22 notification beginning with 1.
3. Actual stock registration is received through
   `IpcProtocol41Iil::IpcRxIilRegistration` at `0x356528`, on the separate IMS
   interface. It is a different, much larger structure.
4. CP `IpcTxImsAuthResp` at `0x34ce10` logs unsupported and returns -1.
   The previous main-22/sub-6 serializer had no supporting CP implementation.
   `SEC_IMS_AUTH` RX at `0x343ec0` builds a **UiccAuthResult**, not a challenge.
5. Supported USIM authentication is AP -> CP `IpcTxDoUiccAuth` at `0x341c50`,
   main 5/sub 9/type 2, payload `[2,16,RAND[16],16,AUTN[16]]`. A synthetic
   isolated emulator capture is committed as a test vector. No synthetic
   authentication challenge was sent to the physical SIM.
6. `SmsManager::DoImsSendIms` at `0x21b320` invokes vtable slot +64, which
   resolves to `DoSendSms(Request*, int, ModemType)`, with ModemType **8**.
   `DoSendSms` retains this in w22 and passes it to `GetModemProxy` at
   `0x219428`/`0x219524`. It is not the payload domain. `ConvertDomainToIPC`
   at `0x344b98` emits only 0..3. The previously added wire-domain-8 route
   is invalid and has been removed.
7. `LteEpdgDataCallManager::ImsPdnTriggered` at `0x28f0e0` only checks whether
   an existing IMS DataCall is connecting/connected. It does not establish
   that SetDataProfile alone activates a bearer. Profile acceptance and CID
   attachment alone do not prove IP/P-CSCF readiness or entitlement denial.

## Native implementation

- Removed false CP registration decoding and the fabricated registration
  retry loop. Runtime reports `sip-registration-backend-missing` explicitly.
- Added standards-based USIM identity derivation in memory, fed by the
  existing SIM IMSI response. Current runtime scope is the already recognized
  KPN 204-08 subscription, with known two-digit MNC; unknown operators are
  not guessed. Identities are not exposed in diagnostics and are cleared
  when the SIM/CP is unavailable and on close.
- Added the vendor-exact USIM authentication request builder, bounded response
  decoder, and asynchronous broker in the existing IMS service. Only one
  request is outstanding; responses require the correct command, type and
  acknowledgment sequence. Timeout/offline/rejection does not auto-retry.
  Borrowed RES/CK/IK/AUTS views exist only during the synchronous callback.
- The broker has no public raw-authentication D-Bus method. A real SIP backend
  must supply a real network challenge; there is currently no such caller.
  This is an implemented prerequisite, not completed IMS registration.
- IMS PDN readiness now requires CID attachment, IP and a P-CSCF of a usable
  address family. Added bounded P-CSCF decoding from the vendor IP structure.
  Disconnect/offline clears readiness; CID 1 cannot satisfy CID 2 readiness.
- Matched profile/capability generic responses against command and sequence.
- Kept queued SMS intact when IMS is the only asserted registration. The CP
  FMT writer cannot be turned into the stock IMS transport by a domain byte.
- Reports AP VoLTE not-ready until a native SIP backend exists. Previously
  rejected SDM SMS probes and redundant SIM-inventory polling are not repeated.
- Added read-only `GetImsStatus` on `nl.nuxel.Radio1` at `/nl/nuxel/Radio1`
  on `unix:path=/run/nuxel-wayland/bus`; only readiness/state metadata is returned.

## Remaining local implementation — not a carrier blocker

There is no native SIP REGISTER/401/AKA/REGISTER/200 implementation or connected
IMS SMS submission endpoint in the inspected Nuxel controller. The previous
controller was a CP state-report sender, not an IMS registration engine.
Identity derivation and a secure USIM broker cannot replace that engine.

A continuation needs to connect a native IMS backend to the existing PDN
manager and USIM broker, verify P-CSCF reachability and negotiated IMS security,
then connect the supported IMS SMS transport/correlation path. The user
explicitly ruled out rewriting the whole IMS stack or running Android; do not
silently substitute either. Recover/identify a compatible existing native
backend before claiming this is a small missing modem initialization command.

No correctly implemented SIP registration has received a carrier rejection.
No subscription provisioning restriction has been verified. There is no
established need to replace the SIM or request carrier entitlement changes.
Message 4 must remain queued until genuine transport readiness exists; never
release historical messages 1–3 or automatically retry an ambiguous submission.
