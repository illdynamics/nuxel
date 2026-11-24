# S5000AP SIPC data protocol and native boot requirements

The live CP independently reports **G975FXXSEFUJ2**, not the DTK9 version in
previous reports. The AP serializer artifact is pinned below. DTK9 was the
initial offline CP reference; EFUJ2 was then extracted read-only from the live
RADIO partition and its command dispatch and payload handling cross-checked.
Command acceptance and LTE camping do not establish network registration,
a default EPS bearer, persistent APN configuration or Internet access.

## Reproduction and source identity

The DTK9 AP package's `vendor/lib64/libsec-ril.so` is byte-identical to the local
`.vendor-ro/libsec-ril.so`. SHA-256:
`b02bd095ae44a991b3cb676e584b3209a947160c22e678578f8b0c877e282cb3`.
Its build ID is `60889dd714394ae0db7c2ecc2bf2740f`.
CP `MAIN` is loaded at `0x40010000`; its SHA-256 is
`dd991cf657e7703ea5e0e2c0b0c3ff9cf4430246d825f05ea26bb6ad0fe22398`.
The live EFUJ2 MAIN SHA-256 is
`16bfb9fef7a32dcb5feb314d96d5d56d2a496e4d5d6956f0ce840f356042213c`.
The complete live RADIO SHA-256 is
`9ffa1426a4ef7d1187779a14f22ec4b8cb4c2ab473b6626304a77030d9966fc7`.
Unless identified as EFUJ2, CP function addresses below refer to DTK9 only.


`tools/s10plus/s5000ap-05/scripts/recover_vendor_vectors.py` runs the pinned
AArch64 serializer functions in Unicorn with an intercepted transport. It does
not contact hardware. Regenerate the complete vectors with:

```sh
python3 tools/s10plus/s5000ap-05/scripts/recover_vendor_vectors.py \
  .vendor-ro/libsec-ril.so --header
python3 tools/s10plus/s5000ap-05/scripts/recover_cp_apn_metadata.py \
  /tmp/cp_extract/MAIN.bin
```

The only normalization in the vendor vectors is zeroing the padding after the
`lte_internet` label's NUL. The vendor copies adjacent `PB_CMD` literal bytes
into that padding. Nuxel does not reproduce the unrelated literal over-read.

## Transport and response framing

Userspace writes a complete FMT message to the exclusively owned
`/dev/umts_ipc0`; the kernel adds the SIPC5 link header. FMT bytes are:

| Offset | Type | Meaning |
|---|---|---|
| 0 | u16 LE | Total length, including seven-byte header |
| 2 | u8 | Message sequence |
| 3 | u8 | Acknowledgment sequence |
| 4 | u8 | Main command |
| 5 | u8 | Subcommand |
| 6 | u8 | Direction-dependent command type |
| 7 | bytes | Payload |

AP GET uses type 2; AP SET uses type 3. CP response uses type 2 and notification
uses type 3. A GEN response is main `0x80`, sub 1, type 2, with exactly five
payload bytes `{origin_main, origin_sub, origin_type, result_u16_LE}`.
`0x8000` is success; `0x8001` is rejection/invalid parameter; `0x8003` is
unsupported and `0x8006` occurs on allocation failure. The complete result must
be retained. A low byte of zero alone does not prove success.
For example, `0d 1b 03 00 80` accepts SET_APN_INFO, while `0d 14 03 04 00`
rejects the initial-attach protocol value. Only the outstanding origin tuple
can acknowledge a state-machine phase. Command acceptance does not prove an
EPS bearer, NV persistence or configured Linux networking.

## SET_APN_INFO: main 13, sub 27, AP SET type 3

Payload length **196**, total FMT length **203**. Offsets below are relative to
the payload. AP `IpcTxSetDataProfile` is at `0x31ff48`. The CP SET handler is
`0x4121b7a8`, registered by `0x40b5f31e` at GPRS dispatch base `0x4385bed0`
plus `0x224`. EFUJ2 registers the same SET at `0x4130367c`, from
initializer `0x40b6f226`, dispatch base `0x4388a084` + `0x224`.
EFUJ2's sub-20 SET is `0x41302f46`; PS GET is `0x4130230e`.
The table uses 20-byte command entries with per-type handlers.
The old report's `0x4034a9e0` structure is logging metadata, not this dispatch
table.

| Offset | Size/type | Meaning and values |
|---|---|---|
| 0 | u8 | Profile ID. Default internet is 1; CP accepts 1–11 here. |
| 1 | char[20] | `lte_internet`, NUL terminated and padded |
| 21 | u8 | IP protocol: IPv4 5, IPv6 6, IPv4v6 4 |
| 22 | char[101] | APN, at most 100 bytes plus NUL |
| 123 | char[32] | Username; empty for this KPN profile |
| 155 | char[32] | Password; empty for this KPN profile |
| 187 | u8 | Authentication: none 0, PAP 1, CHAP 2; vendor auto maps to PAP 1 |
| 188 | u8 | P-CSCF request; 0 for this profile |
| 189 | u8 | **APN disabled**: enabled 0, disabled 1 |
| 190 | u16 LE | Maximum PDN connections; 0 in this profile |
| 192 | u16 LE | Maximum-connection timer; 0 |
| 194 | u16 LE | Wait interval; 0 |

Both CP versions consume only the low byte of each AP u16 timer field.
The CP handler also has a four-byte PCO load after these fields. The matching
AP serializer transmits exactly 196 payload bytes. Nuxel does not append guessed
extension bytes.

AP path: DataCallManager/ModemProxy → IpcModem → IpcProtocol41 serializer →
device transport. CP path: SET handler → `0x40699f30`, event **10**, carrying
the copied APN/profile/auth fields → NS_PDN_GENERAL_REQ (`0x603b`) through
`0x40677ec2` and `0x405b5656` → PDNM/PMPM. The GPRS APN preprocessor at
`0x4168efc4` calls `0x40712474`; selector 1 selects `PMPM_CreateProfile`
(`0x407115c0`), while selector 3 selects `PMPM_AddAlwaysOnProfile`
(`0x40711db2`, profile 12). SET_APN_INFO uses selector 1 and profile ID 1.
It does not directly call `sm_SetApn` or the NV writer. Do not equate this
event with the separate initial-attach event **9**.

This establishes the profile-update operation. It does **not** establish that
profile 1 becomes the persisted initial-attach profile, that it independently
detaches the modem, or that GEN success proves persistence. Those require the
subsequent state transitions and readback described below.

## Initial-attach sequence recovered from the vendor

`DataCallManager::DoSetInitialAttachApn` at `0x22bad8` is a stub.
`LteEpdgDataCallManager::DoSetInitialAttachApn` at `0x28c6c8` is implemented;
it checks the existing profile and whether detach can be skipped. This is not
evidence that the SIPC path is unimplemented. `SetLteAttachProfile` at
`0x22b518` has an explicit SIPC branch through IpcModem `0x2f1870` and
IpcProtocol41 `0x320238`; its MBIM branch is separate.

`DoDetachForIA` (`0x22bdf0`) calls PsAttach with attach=false, suspend=false,
reason=4. The vendor oracle emits `0a 00 00 00 0d 03 03 00 00 04`.
`OnPsDetachDone` (`0x22beb0`) waits for the asynchronous PS state change with a
120-second vendor timeout. `OnPsStateChanged` (`0x22e568`) clears the cached
attach profile and calls `SetLteAttachProfile` after detached notification.
The AP-side `GetAttachApn` (`0x2f1310`) copies a cache; it is **not CP readback**.

Nuxel's optional `NUXEL_REATTACH_IA=1` transaction waits for the detached CP
state before applying the initial profile. It queries NET PS registration first and skips
an actual detach request when the CP is already detached; that request was
rejected with `0x8001` after the corrected NV boot. Failure after issuing detach enters
a bounded PS attach/re-registration recovery sequence, retaining the original
failure. A GEN acknowledgment by itself never proves detach completion.
CP GET 13/3/type 2 (`0x4121a43c`) returns two control-state bytes.
CP notification 13/3/type 3 has three bytes including a detach reason; vendor
`IpcRxGprsPsState` (`0x322318`) decodes attached when byte 0 equals 1.
That AP function ignores GET responses entirely. EFUJ2's GET handler
`0x4130230e` reads `PDNCOMMON_PSINFO` via `0x406a9d22`, `0x406e9ec0` and
`0x40f74614`; it returned `00 00` even with actual NET PS registration and an
active CID 1. It must not override NET registration or gate normal activation.
When NET already reports registered, Nuxel skips redundant PS_ATTACH (observed
`0x8005`) and proceeds to normal PDP activation, still requiring CALL_STATUS,
PDP-list state and actual IP configuration.

### Initial profile SET: main 13, sub 20, AP type 3

Payload **194**, total **201**; CP handler `0x4121b070`. This firmware has a
working SET handler, contradicting earlier report-only claims.

| Offset | Type | Meaning |
|---|---|---|
| 0 | u8 | 1 creates initial profile zero; 3 adds always-on profile 12 |
| 1 | u8 | Attach CID |
| 2 | u8 | Home IP protocol |
| 3 | char[101] | APN |
| 104 | bytes[23] | Reserved, zero |
| 127 | char[32] | Username |
| 159 | char[32] | Password |
| 191 | u8 | Authentication |
| 192 | u8 | Roaming IP protocol |
| 193 | u8 | P-CSCF request |

The vendor's final boolean selects **1 or 3**, never 4. The CP's flag-1
validator at `0x4121af42` accepts protocol bytes 2, 5, 6 and rejects 4 with
GEN result `0x0004`. IPv4 (5) has been accepted live. Flag 3 bypassing this
validation did not prove that the initial profile had been applied.

`GetAttachCid` at `0x1e4500` reads GOT `0x3ad028`, relocated to
**Feature::mRilIndex**. RIL slot 0 uses CID 1; slot 1 uses CID 5. This is not
`DataCallManager::mModelType`. Sysfs `sim/ds_detect` is board configuration,
not a SIM-presence detector.

## Ordinary PDP and activation

NET service-domain SET **8/8/type 3** has one payload byte. The vendor's
`NetServiceDomainType` values are 0=CS+PS, 1=PS-only, 2=CS-only. Instructions
`0x336e30–0x336e48` map these to **wire 1, 3, 2**, respectively. The previous
native constant and serializer selected wire 2 while calling it CS+PS. This
disabled packet service before every attempted attachment. The corrected
CS+PS frame is `08 00 00 00 08 08 03 01`. GET is
`07 00 00 00 08 08 02`; its response has one byte with the same wire enum.
`IpcRxNetServiceDomain` at `0x33b2e0` uses the reverse table `{0,2,1}` at
`0x14a0b8`. Executed vendor vectors cover all three selections and GET.
The native transaction requires a wire-1 readback before proceeding.

DEFINE 13/1/type 3 has payload 127 / total 134: byte 0=1, byte 1=CID,
byte 2=protocol, bytes 3–103=APN[101], remaining bytes zero for this profile.
CP validator `0x41219fe4` accepts protocol 2/5/6; the old dual-stack value 4
caused `0x8001`. An IPv4 DEFINE now succeeds live. The command was not
demonstrated unsupported.

ACTIVATE 13/4/type 3 has payload 105 / total 112, AP serializer `0x31f6e0`:
byte 0=activation state 1, byte 1=CID, bytes 2–5=credential flags (zero for
no auth), bytes 6–37=username, 38–69=password, 70–101=reserved string,
102=auth, 103=reserved, 104=deactivation cause (zero). **The APN is not a
username, and byte 104 is not the IP protocol.** The vendor normal activation
path `ContextActivationDca::ActivateContext` (`0x26ad88`) → IpcModem
`0x2f1be8` uses activation state 1.

CALL_STATUS 13/16/type 3 has nine bytes. CID is byte 0, state byte 1 and cause
byte 2. Vendor connected states are 1/10/11, not state 3. PDP-list response
13/4/type 2 is a count followed by `{CID,state}` pairs; a lone `00` means empty.
IP notification 13/9/type 3 is decoded against `IpcRxIpConfiguration`
`0x321620`: CID at 0; flags u16 LE at 1; IPv4 at 3; DNS at 7 and 11;
gateway at 15; netmask at 19; IPv6 at 35; IPv6 DNS at 99/115; MTU u32 LE at
152 when its flag is set. Addresses use network byte order. Receipt is not
Linux interface configuration or Internet acceptance.

NET 8/10/type 3 maps Android preference 9 to wire mask `0x0b` (LTE/WCDMA/GSM)
and preference 11 to `0x08` (LTE only). GET returns the requested mask.
It does not prove the serving RAT. NET_REGIST's first payload byte is a
Samsung enum: 1=GSM, 4=UMTS, 33=LTE (`0x33a028`). Its domain selector at
byte 1 must identify PS (3) before byte 2 is treated as PS registration.

**The registration wire enum is not an identity mapping.** Executing the
vendor conversion block at `0x3399cc`, jump table `0x14a212`, produces:

| Wire state | Converted state | Meaning |
|---:|---:|---|
| 1, 8 | 0 | Not registered |
| 2 | 1 | Registered home |
| 3 | 2 | Searching |
| 4, 9 | 3 | Denied |
| 6 | 5 | Registered roaming (before carrier-specific exemption) |
| 0, 5, 7, 10, others | 4 | Unknown under non-EPDG policy |

Raw 7/10 can map to vendor EPDG state 6; neither is accepted as home/roaming
registration. `NetRegState::IsRegistered` accepts only converted 1/5. The prior
raw-1-as-home decoder falsely reported PS registration throughout earlier
rounds. Golden receive vectors now execute all 256 wire values. GPRS_PS GET
is a separate control-state query and cannot prove or disprove registration.

The registration reject cause is payload byte **10**, loaded at `0x339c5c`,
passed into `NetRegState` and stored at object offset `0x2c` by `0x2a9484`.
`BuildVoiceRegResponse` (`0x2c7784`) and `BuildDataRegResponse` (`0x2c7a40`)
use that member for the denied-registration reason. It is not payload byte 3
and not the LTE voice-support indication (which comes from payload byte 13).
CS notifications (domain 2) must be tracked separately from PS (domain 3).
The CP reported CS denied with cause 11 while camping on KPN EDGE at
2026-11-24 21:10:53 CET. Cause 11 is PLMN not allowed under
[3GPP TS 24.008](https://www.etsi.org/deliver/etsi_ts/124000_124099/124008/04.02.00_60/ts_124008v040200p.pdf).
This is evidence for that access path, not proof that LTE is barred.


## NV: corrected identity, size and unresolved storage mapping

The CP descriptor table is at `0x4014d0a4`, **20-byte** entries of five u32 LE
words: name pointer, element size, count, flags, type-descriptor pointer.
Hash initialization `0x40c92bf2` stores the table index, and lookup
`0x40c92bb2` / `0x40c92b50` returns that index. NV read `0x40c92e76` and size
lookup `0x40c92ee2` use index × 20 and element size × count.

| Name | Descriptor VA | Item index | Value size |
|---|---|---:|---:|
| NASU.LTE.ATTACH.APN.INFO | 0x4014e1d4 | **220 (0xdc)** | **360 (0x168)** |
| DS_NASU.LTE.ATTACH.APN.INFO | 0x4014e224 | **224 (0xe0)** | **360 (0x168)** |

The previous item-360 / 159-byte / NUL-padded-APN interpretation was wrong.
Neither the descriptor VA nor the item index is a physical file offset.

The separate initial-attach handler `0x41692d7e` reads a 360-byte NV value via
`0x406d0da6` (selector 1), compares the RAM profile-zero structure and can copy
its 324-byte body before writing via `0x406d0dbe`. The RAM structure contains
APN[101] at offset 216 and APN length at 317, plus credentials, protocol and
other fields. A plain APN string at record offset zero would corrupt this
structure. The complete persisted schema and live file mapping remain
unverified. Nuxel now refuses that unsafe provisioning operation even when a
caller supplies a plausible offset and length.

`sm_SetApn` (`0x40c8ae74`), `sm_GetApn` (`0x40c8aeee`) and
`sm_SetApnLength` (`0x40c8b194`) operate on per-SIM/per-PDP RAM buffers.
Their APN offsets are `0x243` and `0x6b6`; corresponding length bytes are
`0x242` and `0x6b5`. These routines are not NV writers. Earlier addresses
around `0x400b5bd7` referred to strings, not these functions.

EFUJ2's descriptor base is `0x4014d084` (index lookup at `0x40c8291a`):
APN descriptors are `0x4014e1b4` and `0x4014e204`, retaining indices 220/224
and sizes 360. Neither firmware's descriptor address is an EFS byte offset.

The existing RFS NV backend is retained. Live RFS writes require both
`--write-enable` and `NUXEL_NV_WRITE=1`. The current transaction has not enabled
NV writes. No CP-supplied offset/length identifying the approved APN record
has been captured. The existing sidecar **is valid** under the actual vendor
algorithm: `MD5(image || "Samsung_Android_RIL")`. `Nv::ComputeChecksum`
(`0x1d57f0`) makes two MD5_Update calls; the previous implementation omitted
the fixed 19-byte suffix and incorrectly reported corruption. Nuxel now
matches the vendor algorithm. The existing file and sidecar remain unchanged;
a complete EFS backup was verified by extraction and byte comparison.

Searching a binary for plaintext `internet` cannot establish whether this
structured NV record is empty, encrypted, compressed, present or authoritative.

## Boot NV download and OES startup

The old native bootstrap skipped the entire NV TOC stage. The pinned vendor
`cpboot_v3/BootDump.cpp::build_std_dload_control_nv_fd` explicitly uses
FD_NV_DATA for SIPC. `BootDumpModap::load_cp_images` downloads it just like
other stages, using the EFS file as the source instead of RADIO.

The live EFUJ2 TOC specifies NV load address `0x45600000`, length `0x100000`.
This is a **whole-image volatile boot transfer**, not the APN record's file
offset. The corrected bootstrap opens existing image/checksum read-only,
checks exact TOC size and vendor checksum before reset, snapshots the bytes,
and downloads in 62 KiB chunks to the TOC's masked address. It never creates,
repairs or writes an EFS file. Physical boot requires both NV inputs.
Corrupted, missing, mismatched or symlinked inputs fail before CP mutation.

The corrected boot was physically executed: 1,048,576 NV bytes downloaded,
CP ONLINE, SIM ready, explicit PWR state 2 (radio on), and KPN LTE camping.
This did not yet establish PS registration or a bearer.

The CP also requests OES 38/1/EXEC with four payload bytes at startup.
`OesManager::OnOesDrkCpInfo` (`0x263bb0`) confirms then calls
`SendDrkCpInfo` (`0x263dd0`), which reads the existing
`/mnt/vendor/efs/DAK/sakeccert0.der` certificate. The native handler follows
that exchange; it never generates/replaces a certificate or exposes its bytes.

- CONFIRM: main 38, sub 1, AP type 4, zero payload (7-byte FMT).
- EVENT: main 38, sub 1, AP type 5, **704-byte payload** (711-byte FMT).
  Payload 0: u16 LE `chunk_length + 2`; byte 2: result 0 (data) or 1 (missing);
  byte 3: zero-based chunk index; bytes 4..703: up to 700 original certificate
  bytes, zero-padded. The final short chunk still uses the full frame length.
- Vendor transmit functions: `0x34e2d8` / `0x34e388`; both are executed by the
  oracle to produce golden frames. A transmit result does not prove the CP
  accepted the certificate or that registration succeeded.

## Carrier evidence

The SIM home network was read as `20408` without retaining/logging the
subscriber portion of its identifier. KPN's published APN and AOSP's 20408
configuration specify `internet`; AOSP includes `default,ia` and IPv4v6.
The matching firmware package here is **TNL** and its CSC APN is
`smartsites.t-mobile`, not a KPN PHN configuration. Therefore a matching KPN
CSC has not been verified. The IPv4 test is a CP-compatible subset, not proof
of the carrier's current provisioning or data entitlement.

Sources: [KPN APN instructions](https://www.kpn.com/service/ugs/slecht-bereik-in-het-buitenland), [AOSP APN configuration](https://android.googlesource.com/device/sample/+/main/etc/apns-full-conf.xml).
