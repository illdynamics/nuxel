# Stage 06 — Round 43: implementation and physical evidence

Date: 2026-11-24 CET. Branch: `cs/mob-round35-stage06`.
Target: Samsung SM-G975F / beyond2lte / S5000AP, Linux 4.14.253 AArch64.

**Stage 06 is incomplete. No victory marker has been created.**
This report supersedes the earlier text at this path, including its assertions
about registration, item 360, a 159-byte APN record, command support and the
running firmware. Those assertions did not follow from the executable code.
The byte-exact specification and reproducible vendor-emulation commands are in
[the protocol document](../docs/S5000AP-IPC41-DATA.md).

## Implemented corrections

- SET_APN_INFO 13/27 has 196 payload bytes, profile selector 1, and an
  **APN-disabled** byte at offset 189. The enabled value is zero. Complete
  vendor-executed golden vectors replace the prior self-consistent guesses.
- The vendor's derived initial-APN manager has an actual SIPC path. The initial
  profile uses selector 1, not the always-on selector 3 or invented selector 4.
  An already detached CP skips the otherwise rejected detach request.
- DEFINE and activation frames now match the AP serializer. The earlier DEFINE
  rejection was a protocol-value rejection, not evidence that DEFINE was absent.
  IPv4 DEFINE succeeds. Activation no longer sends the APN as a username or the
  IP protocol as a deactivation cause.
- Registration raw state 1 is **not registered**. Raw 2/6 map to home/roaming.
  The receive oracle executes all 256 states. Actual NET PS registration gates
  data-call activation; GPRS_PS GET does not report that state reliably.
- The native service-domain command was selecting **CS-only**, despite being
  labeled CS+PS. Vendor enum 0 maps to wire 1 for CS+PS; wire 2 means CS-only.
  The corrected transaction queries and verifies the service domain.
- The network rejection field is payload byte 10. CS and PS registration are
  tracked separately, preserving the actual rejection rather than reporting a
  generic bearer failure.
- Samsung NV checksums are MD5(image + `Samsung_Android_RIL`), not plain MD5.
  Both the existing live image and its backup passed the correct algorithm.
  No checksum repair or EFS modification was needed.
- Native CP bootstrap previously omitted the NV download performed by vendor
  cpboot. It now validates a read-only snapshot before any reset, then downloads
  exactly the firmware TOC's NV size/address. This is volatile boot transfer,
  not a guessed APN filesystem offset or an EFS write.
- The native daemon now answers the CP's OES startup request and transfers the
  existing DAK certificate in the vendor's fixed frames. Only lengths and
  transfer results are logged; no certificate, subscriber or device identity
  content is included in this report.

## Firmware and storage evidence

The CP's MISC software-version query returns **G975FXXSEFUJ2**, not DTK9.
Read-only extraction of the live RADIO partition independently identifies the
same image. RADIO SHA-256:
`9ffa1426a4ef7d1187779a14f22ec4b8cb4c2ab473b6626304a77030d9966fc7`.
The offline DTK9 AP serializer is byte-identical to `.vendor-ro/libsec-ril.so`;
both CP command tables and handler layouts were cross-checked.

The descriptors identify APN items **220 and 224**, each **360 bytes**.
360 is not the item ID. The full record schema and physical file offset have
not been established. Merely finding no ASCII `internet` in the whole image
never proved that a specific APN record was empty. Direct APN provisioning
therefore remains denied, even if a caller supplies a guessed offset/length.
The Round 42 RFS serving implementation remains present; its live NV write gate
has not been enabled.

KPN's official APN guidance and the AOSP 20408 carrier entry specify `internet`.
The available DTK9 TNL CSC targets T-Mobile; it is not a matching KPN PHN CSC.
Matching KPN CSC confirmation and persistent CP APN readback remain outstanding.

## Physical executions

Private operation records, immutable backup checks, builds and logs are retained
under `/var/lib/nuxel/round43-20261124-fixed-wire` on the phone and
`/tmp/nuxel-round43` on the workstation. They contain private recovery material
and must not be committed wholesale.

1. Corrected profile/initial-profile/DEFINE commands were accepted with full
   GEN result `0x8000`. The optional mobile-data toggle returned `0x8003` and
   was reported unsupported, not already enabled. Earlier activation attempts
   returned call state 3, with no cellular address.
2. The corrected registration decoder disproved the old PS-registered baseline:
   raw registration 1 means not registered. GPRS_PS GET returned `00 00`; later
   evidence showed that these control flags cannot independently establish
   network attachment.
3. CP-only restart operation 10 transferred the unchanged, checksum-verified
   1,048,576-byte NV snapshot at TOC RAM offset `0x05600000`. All boot/security
   stages succeeded. CP returned ONLINE, radio notification 2 indicated ON,
   SIM became ready, and KPN LTE camping was observed. No EPS bearer followed.
4. Operation 13 repeated that verified bootstrap and handled the actual OES
   request: confirmation length 7, two event frames of 711 bytes, 987 certificate
   bytes transferred. This proves transfer, not CP certificate authentication.
   EFS image and checksum remained byte-identical to the verified backup.
5. Operation 14 applied the initial APN while already detached. Profile SET,
   initial-profile SET, DEFINE, always-on PDN and PS attach all returned
   `0x8000`. Repeated PS GET returned `00 00`. The then-incorrect gate blocked PDP
   activation. EDGE CS registration reported denied with cause 11 at 21:10:53.
6. Operation 15 read back LTE-only mask `0x08`; the modem nevertheless fell back
   to an unregistered UMTS cell. This led to discovering the
   erroneous CS-only command described above. The failed transaction terminated
   on its bounded deadline; management and CP remained healthy.
7. Operation 16 corrected CS+PS selection and verified wire-1 readback. KPN LTE
   PS registration became raw 2 / REGISTERED_HOME and PDP CID 1 became active.
   Redundant PS_ATTACH returned `0x8005`. Vendor AP analysis then established
   that GPRS_PS GET responses are ignored; their `00 00` was not detachment.
8. Operation 17 skipped that redundant attach using real NET registration.
   ACTIVATE returned `0x8000`, followed by an actual IP notification (313-byte
   payload, flags `0x2340`, IPv6 present), CALL_STATUS CID 1 / state 1 / cause 0,
   and a PDP list confirming CID 1 active. Linux interface configuration and
   traffic verification remain outstanding. Build-10 deployed SHA-256:
   `1f262cdbdf7d44ce68f02f41338e562ab44428fb590189693cb8287a849ee5e9`.

No BOOT, DTB, DTBO, RADIO partition, identity, calibration or EFS record has been
modified. CP restarts had independent timed rollback and retained Wi-Fi/ZeroTier
management. All completed restart timers were cancelled after health checks.

## Validation and acceptance

The latest completed build-10 gate passed all 16 host suites, 3,000 ordinary fuzz
iterations, 3,000 ASan/UBSan fuzz iterations, targeted sanitizer suites, and native
AArch64 compilation with `-Wall -Wextra -Werror`. Bootstrap tests passed all 34 tests;
its 13 mock-boot tests also passed ASan/UBSan, including invalid NV preflight
rejection before mutation. Safe EFS fixtures verify write, checksum, bounds,
backup and rollback behavior. The live NV backup was extracted and compared.

| Requirement | Current evidence |
|---|---|
| CP initialization | PASS: two corrected NV boots, ONLINE |
| SIM detection | PASS: native ready responses, KPN home prefix |
| Network registration | PASS in operation 16/17: KPN LTE, raw 2, home |
| PS registration | PASS: NET domain 3 registered; no rejection |
| LTE profile / initial APN persistence | Command accepted; persistent readback unverified |
| EPS bearer / cellular IP | Active CID 1, CALL_STATUS 1, IPv6 configuration received |
| Cellular routing / DNS / HTTPS | Not achieved |
| SMS outbound / inbound | Not delivered or received; test number still required |
| Voice outbound / inbound / audio | Not demonstrated |
| Reconnection / APN restart persistence | Not demonstrated |
| Wi-Fi / ZeroTier / SSH regression | PASS during completed operations |
| USB physical regression | Unverified: configured listener, carrier=0 |
| Host / sanitizer / AArch64 regression | Build 10 PASS |

Cause 11 establishes a denial on the observed EDGE access path. KPN documents
selective 2G retirement beginning in March 2026, but this does not establish the
subscription's LTE eligibility or excuse the independently found Nuxel defects.
No carrier-wide or SIM-specific LTE limitation has yet been proven.

Continuation uses the running native service and its `GetDataSessionState` /
`RefreshStatus` methods. Do not run older binaries' data sequences: their
service-domain setter disables packet service. Do not write APN NV until the
record representation and CP-authoritative storage mapping are proven.
