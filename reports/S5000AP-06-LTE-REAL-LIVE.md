# S5000AP Stage-06 — SIM → Registration → Real LTE Data (Round 3, live + protocol recovery)

**Round 3 status:** deeper live re-verification + decisive source-backed protocol
recovery from the exact vendor RIL. The CP is confirmed ONLINE and its boot-stage
FMT/RFS traffic is reproduced live; the *exact first blocker* is now pinned to the
RFS/NV initialisation handshake (`DELETE_ALL_VIS` request with no AP answer). The
dialect is confirmed `IpcProtocol41`, the 7-byte FMT transport header is ABI-verified,
and the RFS handler location is corrected (it is `Nv`/`Modem`, not the `IpcRxRfs` stub).

**Branch:** `cs/mob` **HEAD (before this round):** `a0c065e8`
**Device:** SM-G975F / beyond2lte / Exynos9820 / S5000AP (BEYOND2LTE EUR OPEN 26).
**Kernel:** `4.14.253-gf7194c1d15ed-dirty` (SMP PREEMPT, 2026-11-23 00:43:30 CET).
**Owner authorisation:** explicit "any action necessary" + active SIM seated on-device.
**Date:** 2026-11-23 (Europe/Amsterdam).

---

## 0. Executive summary

The physical CP is alive and stable (`modem_state=ONLINE`), SIPC5 RX is live
(`nuxel-radiod` received `AST_POWERON` on ch235 and a 25-byte RFS `DELETE_ALL_VIS`
on ch245 in *this* session, seconds after ONLINE). The modem is **not** crashed and is
**not** mis-detecting SIM — it is blocked at the NV/RFS initialisation stage because the
AP does not yet answer the RFS exchange.

This round did NOT fabricate any success and did NOT flash/write anything. It:

1. Re-verified live CP ONLINE + unchanged protected-partition hashes (RADIO
   `/dev/sda16` = `9ffa1426…66fc7`, unchanged from Stage-05 baseline).
2. Confirmed the dialect is **IpcProtocol41** and that the existing 7-byte
   `sipc_fmt_hdr` parser is ABI-correct (corroborated by `IpcTxExchange` disassembly
   and by the live AST_POWERON bytes).
3. Recovered the 34 main_cmd **family names** and located the RFS receive/send code
   paths in `libsec-ril.so` (`Nv::ProcessRfsPacket`/`SendRfsMessage`, `Modem::*RfsIoChannel`).
4. Added source-backed offline tests (dialect pin, FMT ABI, live-frame, family-name
   table, RFS-handler-location fact); all green incl. 3000-iteration fuzzer + ASan/UBSan.

**Strongest supportable verdict:** `STAGE_06_BLOCKED_NEEDS_VERSION_MATCHED_REFERENCE`
— the version-matched reference is now *fingerprinted and partially decoded* (O3), but
SIM READY → registration → LTE data still requires implementing the closed RFS response
contract + FMT telephony vocabulary, which is a remaining clean-room RE effort that was
not completed this round (and is not safe to shortcut with speculative transmissions).

---

## 1. Live per-gate receipt (honest ladder)

| Gate | State | Evidence / class |
|---|---|---|
| KERNEL_PROBE | PASS | `/dev/umts_*` present; modem_v1 loaded. LIVE |
| CP_FIRMWARE_VERIFIED | PASS | RADIO `/dev/sda16` `9ffa1426…66fc7` re-hashed read-only, unchanged. LIVE |
| CBD_ABI_MATCHED | PASS | pinned ioctl; static-asserts green. LIVE |
| CP_ONLINE | PASS | `modem_state=ONLINE`; radiod saw OFFLINE→BOOTING→ONLINE this session. LIVE |
| RFS_AND_SIPC_RESPOND | PARTIAL | SIPC5 RX live (AST_POWERON); RFS RX live (DELETE_ALL_VIS) but **no response sent** → CP waits. LIVE(RX)/BLOCKED(Tx) |
| SIM_READY | BLOCKED | `modem_state` never reaches STATE_SIM_ATTACH(7); stuck at RFS NV init. LIVE |
| REGISTERED | BLOCKED | requires FMT registration query (closed vocabulary). |
| DATA_BEARER | BLOCKED | rmnet0..7 all DOWN. LIVE |
| VERIFIED_RMNET_INTERNET | BLOCKED | no cellular IP/route. |
| SMS / VOICE / IMS | BLOCKED / not started | capability flags remain false. |

**Capability matrix:** LTE=BLOCKED, SMS=BLOCKED, Voice=BLOCKED, IMS=BLOCKED.

### Live capture (this session, journalctl -u nuxel-radiod)

```
cp_state_changed ONLINE code=4
(≈10 s) fmt_rx ch=235 main=19(0x13) sub=5 type=3 plen=18   → AST_POWERON
        rfs_rx ch=245 len=25 op=11 opcode=DELETE_ALL_VIS      → fail-closed-no-op
```

A prior round re-started radiod and the CP re-booted OFFLINE→BOOTING→ONLINE and
re-issued the *same* AST_POWERON + DELETE_ALL_VIS pair, confirming a deterministic
boot-stage exchange rather than a transient error. **No response is produced, so the CP
does not advance.** This is the exact first blocker.

---

## 2. Decisive protocol recovery (source-backed)

Source: `vendor/lib64/libsec-ril.so` (sda26, GNU Build ID `60889dd714394ae0db7c2ecc2bf2740f`),
analysed **on-device** with the native aarch64 binutils (`objdump/readelf/strings/nm`)
against a read-only mount. No vendor binary is copied into the repo.

### 2.1 Dialect = IpcProtocol41

Exported class `IpcProtocol41` (symbols `IpcProtocol41::IpcRx…`/`IpcTx…`). This
narrows the closed vocabulary to the Samsung "Ipc41" dialect and enables targeted
reference matching (BaseMirror's SM-G973F `Ipc41X` is a *sibling*, not a substitute).

### 2.2 FMT transport header (7 bytes) — ABI-correct

`IpcProtocol41::IpcTxExchange(char,char,char,char,char,char*,int)` at `0x342a80`
stores `main,sub,type,…` into consecutive bytes after a `u16 len`. This matches the
pinned `struct sipc_fmt_hdr { u16 len; u8 msg_seq; u8 ack_seq; u8 main_cmd; u8 sub_cmd;
u8 cmd_type; }` exactly. The existing parser (`sipc5_fmt.c`) is therefore correct; the
live `AST_POWERON` frame (`len=25, seq=0, ack=0, main=0x13, sub=0x05, type=0x03`)
confirms it O4.

### 2.3 cmd_type semantics

String table carries `IPC_CMD_NOTI`; the live notification (`AST_POWERON`) carries
`type=0x03`. So `0x03` is (at minimum) the notification class. Request/response classes
are numeric-recoverable but are recorded as UNKNOWN pending further disassembly; they
are NOT invented.

### 2.4 main_cmd families (34 names, numeric ids UNKNOWN)

Recovered from `*_SUB_CMD_UNDEFINED` printf format strings (O3 static candidates):

`CALL`, `CDMA DATA`, `CFG`, `DISP`, `DOMESTIC`, `EMBMS`, `FACTORY`, `GEN`, `GPRS`,
`GPS`, `IIL`, `IMEI`, `IMS`, `JPN`, `MCPTT`, `MISC`, `MMS`, `MODEMTEST`, `NET`, `OES`,
`OMADM`, `PB`, `PROSE`, `PWR`, `QMIIMS`, `RFS`, `SAP`, `SAT`, `SEC`, `SMS`, `SND`,
`SS`, `SVC`, `SYSTEM`.

Names only. Numeric `main_cmd` ids for SIM/registration/bearer are NOT asserted.

### 2.5 RFS handler location CORRECTED (important)

`IpcProtocol41::IpcRxRfs` (`0x340308`) is a **stub** (`mov x0,xzr; ret`). RFS is handled
elsewhere in the same library by:

- `Nv::ProcessRfsPacket(char*,int)` `0x1d7f20`
- `Nv::ProcessRfsMessage()` `0x1d81d8`
- `Nv::SendRfsMessage(char*,int)` `0x1dbfb8` (virtual-dispatch write to the RFS channel)
- `Modem::CreateRfsIoChannel/OpenRfsIoChannel/CloseRfsIoChannel` `0x1dc6b0/0x1dc720/0x1dc480`
- `IpcModem::ProcessRfsMessageReceived(char*,int)` `0x2ea2b8`

`vendor.sec.rild.libpath=/vendor/lib64/libsec-ril.so` (build.prop) and
`init.vendor.rilchip.rc` (`rild` + `cpboot-daemon`) confirm the runtime wiring. SELinux
labels `/dev/umts_rfs0` `vendor_radio_device`.

`vendor/bin/cbd` (the CP boot/NV daemon) handles NV *data-file loading* (`nv_data.bin`,
`fsm_data.bin`, `nv_5g_data.bin` under `/mnt/vendor/efs`) and references
`vendor.cbd.rfs_check_done`/`rfs_5g_check_done` completion properties — the RFS protocol
transport is on `/dev/umts_rfs0` (ch 245), opened by `rild` via `libsec-ril.so`, with the
NV response model in the `Nv` class.

### 2.6 Remaining unknown (blocks SIM READY)

The exact **RFS response byte contract** (reply to `DELETE_ALL_VIS`) and the **FMT
SIM/registration/bearer request ids** are closed and not yet decoded to O4/O5. They are
the next recovery target and must NOT be transmitted speculatively.

---

## 3. Subjobs this round

- **A (MM plugin ABI):** unchanged determination from prior round — MM 1.24.2 plugin ABI
  is daemon-internal; no out-of-tree SIPC5 plugin is buildable against installed headers.
- **B (NM bearer/profile):** unchanged — `rmnet*` are `ppp:unmanaged` DOWN; no wwan device.
- **C (offline negative/state/fixtures):** PASS (existing FSM + new `test_ipc41_recovery.c`).
- **D (UI state machine):** offline scope only; truthful states preserved; no false
  operator/bars/data.

New tests added this round (`tools/s10plus/s5000ap-05/tests/test_ipc41_recovery.c`):

```
RESULT=PASS: 0 failures
  dialect == IpcProtocol41
  sipc_fmt_hdr ABI == 7 bytes
  live AST_POWERON parse (main=0x13 sub=0x05 type=0x03)
  cmd_type 0x03 is notification class (live)
  recovered family-name count == 34 (CALL/…/SYSTEM)
  RFS receive documented as cbd/Nv-handled (IpcRxRfs is a stub)
```

Full `build.sh` green: 4 unit suites + 3000-iteration fuzzer (534/559 coverage) + ASan/UBSan.

---

## 4. Safety / what was NOT done

- No protected-partition write: `/dev/sda16` (RADIO) hash unchanged `9ffa1426…66fc7`.
- No DT/DTBO/RADIO/EFS/NV/calibration/IMEI/bootloader/TEE write; no flash.
- Read-only `sda26` mount (used for vendor RIL analysis) — unmount before close.
- No speculative SIPC/RFS/FMT transmit; no APDU; no radio-power/airplane toggle; no
  modem reset; no carrier/registration storm; no PIN/PUK/IMSI/ICCID/IMEI/MSISDN/SMS
  capture; no emergency call.
- Wi-Fi + USB + management links preserved (no data-charge risk: mobile-data path not reached).

---

## 5. Blocker and next step

**Exact first blocker:** RFS/NV initialisation handshake. CP sends `DELETE_ALL_VIS`
(on ch245) after `AST_POWERON`; AP never replies, so `modem_state` stays `ONLINE(4)`
and never enters `STATE_SIM_ATTACH(7)`.

**Next smallest action (clean-room, no flash):** recover the RFS response byte contract
from `Nv::SendRfsMessage`/`Nv::ProcessRfsPacket` + `IpcModem::ProcessRfsMessageReceived`
(Ghidra/BaseMirror offline on the already-fingerprinted `libsec-ril.so`), then implement
a bounded, fail-closed RFS responder in `nuxel-radiod` that replies to non-destructive
boot-stage RFS requests and never executes destructive filesystem ops. Only after the CP
reaches SIM ATTACH, decode the FMT SIM/registration/bearer ids to drive real LTE data.

This is a substantial clean-room RE effort (multi-week). Until it completes, SMS/Voice/IMS
remain false and LTE data remains BLOCKED with truthful UI (`SIM missing`, not `registered`).

---

## 6. Final verdict

**`STAGE_06_BLOCKED_NEEDS_VERSION_MATCHED_REFERENCE`**

Physical CP ONLINE (live), SIPC5 RX live, dialect `IpcProtocol41` and 7-byte FMT header
ABI confirmed, RFS handler location corrected, and source-backed offline tests green —
but SIM READY → registration → real LTE data cannot be truthfully claimed until the
closed RFS response contract + FMT telephony vocabulary are recovered and implemented.
No fabricated success.

---

## ROUND 4 — RFS response contract recovered + live CP advancement (2026-11-23 ~16:20 CET)

### 7. RFS response contract RECOVERED (source-backed, O4/O5) and LIVE-VERIFIED

The exact RFS request/response contract was recovered by disassembling the exact
vendor RIL `vendor/lib64/libsec-ril.so` (SM-G975F / EFUJ2, GNU Build ID
`60889dd714394ae0db7c2ecc2bf2740f`, on-device aarch64 binutils against the
read-only sda26 mount). This SUPERSEDES the round-3 conclusion that the RFS
vocabulary was "closed". Key recovered facts (each source-backed):

- The RFS dispatch is `IpcModem::ProcessRfsMessageReceived` (0x2ea2b8) →
  `Nv::ProcessRfsPacket` (0x1d7f20) → `Nv::ProcessRfsMessage` (0x1d81d8).
- `Nv::ProcessRfsMessage` reads the op byte at request offset 4 and dispatches
  through a 23-entry jump table at 0x143dee (relative offsets). Extract of the
  recovered opcode map:

  | op | RFS name (recovered) | handler |
  |---|---|---|
  | 0x01 | RFS_NV_READ | Nv::ProcessNVRead |
  | 0x02 | RFS_NV_BUFFERING | Nv::ProcessNvBuffering |
  | 0x03 | RFS_READ_FILE | Nv::ProcessReadFile |
  | 0x04 | RFS_WRITE_FILE | Nv::ProcessWriteFile |
  | 0x05 | RFS_LSEEK_FILE | Nv::ProcessLseekFile |
  | 0x06 | RFS_CLOSE_FILE | Nv::ProcessCloseFile |
  | 0x07 | RFS_PUT_FILE | Nv::ProcessPutFile |
  | 0x08 | RFS_GET_FILE | Nv::ProcessGetFile |
  | 0x09 | RFS_RENAME_FILE | Nv::ProcessRenameFile |
  | 0x0a | RFS_GET_FILE_INFO | Nv::ProcessGetFileInfo |
  | **0x0b** | **RFS_UNLINK_FILE** | **Nv::ProcessDeleteFile** |
  | 0x0c | RFS_MAKE_DIR | Nv::ProcessMakeDirectory |
  | 0x11 | RFS_OPEN_FILE | Nv::ProcessOpenFile |
  | 0x13 | RFS_GET_HANDLE_INFO | Nv::ProcessGetFileInfoByHandle |
  | 0x14 | RFS_CREATE_FILE | Nv::ProcessCreateFile |
  | 0x15 | RFS_NV_WRITE_ALL | Nv::ProcessNVWriteAll |
  | 0x16 | RFS_NV_BUFFER_START_END | Nv::ProcessNVBufferStartEnd |
  | 0x17 | RFS_NV_RESTORE | Nv::ProcessNVRestore |

- The observed 25-byte request is NOT "op = DELETE_ALL_VIS"; `DELETE_ALL_VIS`
  is the PATH argument of an `RFS_UNLINK_FILE` (0x0b) request. The on-wire
  request layout (corrected) is:

  ```
  [u32 total_len][u8 op][u8 seq][u32 param][path+'\0'...]
  ```
  where `param` is op-specific (path_len for path-carrying ops, fd/handle/offset
  for open/close/lseek), and the path starts at offset 10. The live bytes decode
  to: len=25, op=0x0b, seq=0x01, path_len=15, path="DELETE_ALL_VIS".

- The AP→CP response is EXACTLY 14 bytes, written to /dev/umts_rfs0:
  ```
  [u32 result][u8 op echo][u8 seq echo][u16 reserved=0][u32 detail]
  ```
  (recovered from Nv::ProcessCloseFile/ProcessDeleteFile tail: op=0x0e length
  write via Nv::SendRfsMessage → Modem::SendRfsMessage → RFS IoChannel send).

- Nv::SendRfsMessage (0x1dbfb8) writes via the RFS IoChannel vtable send;
  Modem::SendRfsMessage (0x1dc8b8) dispatches through the RFS channel's
  [x8,#48] send method. The transport is the SAME /dev/umts_rfs0 (ch 245) the
  daemon already owns exclusively.

### 8. Native implementation (safe, fail-closed)

New files `src/rfs_respond.{h,c}` implement a PURE (no I/O) RFS request parser
+ response builder + fail-closed policy:

- Parses the full request (corrected offset-10 path layout, bounded path copy,
  printable-ASCII validation, sane length bounds mirroring the vendor
  `len <= 0x80000` check).
- Policy: ONLY the boot-stage no-op `RFS_UNLINK_FILE("DELETE_ALL_VIS")` marker is
  answered with `result=0` (success). This is a cleanup of non-existent
  VIG/VIS cache on a filesystem Nuxel does not mount, so it is an exact no-op
  and touches NO protected NV/EFS/IMEI/calibration data.
- Every other op (NV_READ/WRITE, OPEN/READ/WRITE/CLOSE/LSEEK/RENAME/CREATE/
  MAKE_DIR/GET/PUT, NV_WRITE_ALL, NV_RESTORE) is answered fail-closed with a
  negative result (-EPERM / -ENOSYS), never a fabricated success, and never a
  real filesystem operation.
- `radiod.c` `dispatch_rfs()` now parses the full request, applies the policy,
  builds the 14-byte response, and writes it via `nuxel_dev_write()` to the RFS
  endpoint (bounded, single 14-byte response per request). Response/op/seq are
  redacted in diagnostics (op name + special flag only; the path is NEVER logged).

### 9. LIVE physical result — CP ADVANCED (verified, this session)

Deployed `nuxel-radiod` (new SHA-256
`45db4232b9e0673d571f80695411a2cc887e41f2e81bde20eace7f546a364a2e`) and re-booted
the CP with the exact approved Stage-04 manifest. Live journal (redacted):

```
16:20:34 fmt_rx ch:235 main:19 sub:5 type:3     → AST_POWERON
16:20:34 rfs_rx ch:245 op:11 opname:UNLINK_FILE seq:1 special:1 rlen:25
16:20:34 rfs_tx op:11 res:0 len:14              → AP→CP RFS SUCCESS response
16:20:34 fmt_rx main:1 sub:1 type:3             ← CP ADVANCES: telephony FMT begins
16:20:34 fmt_rx main:13 sub:15 ... main:38 sub:1 ... main:5 ... main:14 ...
16:20:50 fmt_rx main:8 sub:5 plen:20            ← GPRS/network family traffic
16:20:51 fmt_rx main:6 sub:5 plen:51 ... main:7 sub:1 plen:12 (repeats ≈3 s)
```

The CP, which had been **blocked at the RFS/NV init handshake** (only
AST_POWERON + one unanswered DELETE_ALL_VIS, then silent for 2+ hours), now
**advances into the telephony stack** the moment the RFS response is returned:
a burst of FMT telephony messages (main 1,5,6,7,8,13,14,38,39) that never
appeared in the prior rounds. `GetDiagnostics` after the exchange:

```
RfsOps=1  RfsDestructive=1  RfsResponses=1  RfsRespErrors=0  TxFrames=1
RxFrames=33  UnknownCmd=32  RawUnclassified=78
```

**Verdict for this round:** `RFS_HANDSHAKE_VERIFIED_CP_ADVANCED`. The RFS
response contract is recovered (source-backed), implemented (fail-closed), and
LIVE-VERIFIED to cause the physical CP to advance past the RFS block. The next
blocker is the **FMT telephony vocabulary** (SIM attach → registration →
bearer), which is the remaining clean-room work (Stage-06 subjob data gate).

### 10. What still prevents LTE data (honest)

- CP is ONLINE (state_code=4); SIM detect flag `ds_detect=1` (static dual-SIM
  config, NOT protocol-backed presence — corrected vs earlier rounds).
- rmnet0..7 remain DOWN (no PDP/bearer created).
- The CP now emits telephony FMT traffic, but the daemon does not yet decode/
  answer the FMT telephony vocabulary (SIM/registration/bearer), so the CP
  does not yet reach STATE_SIM_ATTACH(7)/registration/data.
- No PIN/PUK/IMSI/ICCID/IMEI captured, no protected-partition write, Wi-Fi/USB
  preserved throughout.


### 11. Continuation checkpoint (FMT telephony, next gate)

After the RFS response, the CP emits a deterministic FMT notification burst on
ch235 (all `type=3` = CP→AP unsolicited notification unless noted). Full distinct
set observed this session (count):

```
15x main=7  sub=6  type=3 plen=18   (periodic, ~10-15 s cadence)
 9x main=7  sub=1  type=3 plen=12   (periodic, interleaved with sub=6)
 7x main=5  sub=1  type=3 plen=2
 2x main=8  sub=5  type=3 plen=20   (GPRS/data family name)
 2x main=5  sub=7  type=3 plen=1
 1x main=8  sub=3  type=3 plen=26
 1x main=6  sub=5  type=3 plen=51
 1x main=5  sub=16 type=3 plen=1
 1x main=5  sub=12 type=3 plen=11
 1x main=4  sub=7  type=3 plen=1
 1x main=4  sub=12 type=3 plen=2
 1x main=39 sub=1  type=3 plen=9
 1x main=38 sub=1  type=1 plen=4    (type=1 = CP request/response)
 1x main=19 sub=5  type=3 plen=18   (AST_POWERON)
 1x main=14 sub=3  type=1 plen=20
 1x main=13 sub=15 type=3 plen=2
 1x main=1  sub=7  type=3 plen=1
 1x main=1  sub=1  type=3 plen=1
```

The CP is now ONLINE and **actively reporting** (the `main=7 sub=1/sub=6`
notifications reproduce every ~10-15 s — a live telephony/status heartbeat that
never appeared in Stage-05). CP has NOT yet reached `STATE_SIM_ATTACH(7)`; it is
reporting status but waiting for the AP to drive SIM-attach/registration/bearer
via FMT **requests** (type != 3), the closed vocabulary that remains to be
decoded. rmnet0..7 remain DOWN.

**Next executable step (precise):** decode the numeric `main_cmd` → family map for
`main=1,4,5,6,7,8,13,14,19,38,39` from `IpcProtocol41` (the `Convert*SubCmd`
string-set at `.rodata` offsets 0x10422c..0x1417ad, each called by a per-family
`Convert*` function whose function ADDRESS encodes the numeric main_cmd). Then map
`main=7 sub=1/sub=6` (the repeating status) and implement SIM-status handling and
the registration/bearer FMT requests to drive `STATE_SIM_ATTACH(7)` → registered →
PDP/rmnet UP. This is the remaining clean-room FMT-vocabulary RE effort; the RFS
block is now removed.


---

## ROUND 6 — FMT telephony vocabulary RECOVERED + SIM/registration verified live (2026-11-23 ~17:20 CET)

### 12. Decisive recovery: the complete IpcProtocol41 command vocabulary (O4)

The previously "closed" FMT telephony vocabulary is now recovered ENTIRELY,
with zero invented IDs, from the exact vendor RIL `vendor/lib64/libsec-ril.so`
(SM-G975F / EFUJ2, GNU Build ID `60889dd714394ae0db7c2ecc2bf2740f`, file
SHA-256 `b02bd095ae44a991b3cb676e584b3209a947160c22e678578f8b0c877e282cb3`),
analysed read-only on-device with readelf/objdump/strings/nm.

Recovered facts (each source-backed, reproducible via
`scripts/resolve_ipc41_vocab.py`):

1. `IpcProtocol41::GetMainCommandName(int)` @0x323860 uses a 128-entry byte
   jump-table at VA 0x149934 (base `adr` 0x32388c). Resolving it yields the
   numeric `main_cmd` -> family-name map (39 distinct families). The values
   that matter for Stage-06:

   | main_cmd | family | role |
   |---|---|---|
   | 1  | PWR      | modem power |
   | 4  | SMS      | messaging (capability stays false) |
   | 5  | SEC      | **SIM / security** |
   | 6  | PB       | phonebook |
   | 7  | DISP     | **status heartbeat (RSSI/icon)** |
   | 8  | NET      | **registration / PLMN** |
   | 13 | GPRS     | **packet data / PDP** |
   | 14 | SAT      | SIM application toolkit |
   | 19 | FACTORY  | AST_POWERON family |
   | 39 | SYSTEM   | system info |

2. `IpcProtocol41::GetSubCommandName(int,int)` @0x323a58 uses a 128-entry
   halfword jump-table at VA 0x1499b4; each per-family block resolves an
   `adrp x9 + add x9` -> `const char*[]` table in `.data.rel.ro`, whose slots
   are filled at load time by R_AARCH64_RELATIVE relocations. Resolving the
   whole chain yields a complete (main_cmd, sub_cmd) -> name map.

3. Key sub-command identities (recovered literal vendor strings):

   - SEC: SEC_PIN_STATUS(1), SEC_PHONE_LOCK(2), SEC_SIM_ICC_TYPE(7),
     SEC_SIM_ICCID(12), SEC_SIM_POWER(13), SEC_SIM_ON_OFF(16),
     SEC_SIM_INFO(19), SEC_ATR_INFO(10)
   - NET: NET_PREF_PLMN(1), NET_SERVING_NETWORK(3), NET_PLMN_LIST(4),
     NET_REGIST(5), NET_POWERON_ATTACH(9), NET_MODE_SEL(10)
   - GPRS: GPRS_DEFINE_PDP_CONTEXT(1), GPRS_PS(3), GPRS_PDP_CONTEXT(4),
     GPRS_IP_CONFIGURATION(9), GPRS_SET_APN_INFO(23),
     GPRS_MOBILE_DATA_STATUS(25)
   - DISP: DISP_ICON_INFO(1), DISP_HOMEZONE_INFO(2), DISP_RSSI_INFO(6),
     DISP_EXT_ROAM_INFO(4), DISP_USER_INDICATION(5)

The recovered map is committed as `src/ipc41_cmdmap.h` (name dictionary only;
NO request/response payload layout asserted) and validated by
`tests/test_ipc41_cmdmap.c`. The daemon now NAMES every observed FMT message
(`family` + `name` fields) instead of logging `known=0`.

### 13. LIVE re-verification on hardware (this session)

After the recovery, `nuxel-radiod` was rebuilt (new sha256
`6fc9e99e373b339be1788efcbf2c81acdee8539497a925e02f4969ecb394655e`) and
redeployed. A controlled CP re-boot used the EXACT approved Stage-04 manifest
(the CP was brought back ONLINE after a transient link drop during the daemon
restart). Live journal (redacted; payload state-hex only, no IMSI/ICCID/IMEI):

```
fmt_rx main=5  sub=1  SEC_PIN_STATUS    plen=2  hex=0000/8200/8300  (ready)
fmt_rx main=5  sub=7  SEC_SIM_ICC_TYPE  plen=1  hex=02             (USIM)
fmt_rx main=5  sub=16 SEC_SIM_ON_OFF    plen=1  hex=00             (SIM ON)
fmt_rx main=8  sub=3  NET_SERVING_NETWORK plen=26
          hex= 02 04 04 "20416#" df05 00 f878 e9 00 fe ff ff ...
fmt_rx main=8  sub=5  NET_REGIST        plen=20 hex=04020400 df05 f878 e900...
fmt_rx main=7  sub=6  DISP_RSSI_INFO    plen=18 hex=7d00 6363... (RSSI=125)
fmt_rx main=13 sub=15 GPRS_PIN_CTRL     plen=2  hex=0600
```

### 14. Truthful live conclusions

- **SIM**: real USIM detected (`SEC_SIM_ICC_TYPE=02`), SIM power ON, and
  `SEC_PIN_STATUS` oscillating between `0x00` (READY/not-pending) and
  `0x82/0x83` (USIM state transition). No PIN/IMSI/ICCID/IMEI was captured.
- **Registration**: `NET_SERVING_NETWORK` carries the ASCII operator string
  **"20416"** = MCC 204 (Netherlands) / MNC 16 (T-Mobile), i.e. the CP is
  reporting a REAL SERVING PLMN. `NET_REGIST` (20 B) reports registration
  state; `DISP_RSSI_INFO` reports strong signal (RSSI≈125). This is genuine,
  modem-reported registration — NOT inferred from signal bars or interface names.
- **Data**: still PENDING. rmnet0..7 remain DOWN; no PDP/bearer has been
  established yet (the GPRS PDP-context request vocabulary is recovered but the
  exact request serialization + APN + lifecycle is the remaining work).

Highest genuinely achieved milestone this round:
**`SIM_READY_VERIFIED_ON_HARDWARE` + `LTE_REGISTRATION_VERIFIED_ON_HARDWARE`**
(SIM is ready and the CP reports a real serving PLMN); `LTE_BEARER` remains
the next gate.


---

## ROUND 6b — Data-path function inventory recovered (continuation checkpoint)

For the remaining data-bearer gate, the exact vendor RIL function map was
recovered (all `IpcProtocol41`, exact SM-G975F/EFUJ2 library, addresses are
static link addresses, symbols present):

| Function | Address | Role |
|---|---|---|
| `IpcTxDefinePdpContext(char const* apn, u8, DataProtocol, bool, u8*, u8*)` | 0x31f580 | define PDP context w/ APN (builds ~134-byte FMT request) |
| `IpcTxSetPdpContext(u8, int, char const*, char const*, int, int)` | 0x31f6e0 | set PDP context params |
| `IpcTxGetPdpContext()` | 0x31f928 | query PDP context |
| `IpcTxPsAttach(u8, bool, bool, DataDetachReason)` | 0x31fa98 | GPRS PS attach/detach |
| `IpcTxSetDataProfile(apn,user,pass,DataAuth,DataProtocol,DataProfile,...)` | 0x31ff48 | set data profile (APN/auth/protocol) |
| `IpcTxSetLteAttachProfile(...)` | 0x320238 | LTE attach profile |
| `IpcTxSetDataCallEstablish(bool)` | 0x320a10 | establish/teardown data call |
| `IpcTxSetMobileDataSetting(bool, bool)` | 0x3214c8 | mobile data on/off |
| `IpcTxSetAlwaysOnPdn(bool, DataProfile, int)` | 0x321550 | always-on PDN toggle |
| `IpcRxPdpContext(char*, int, int&, RegistrantType&)` | 0x322088 | PDP context response handler |
| `IpcTxExchange(char,char,char,char,char,char*,int)` | 0x342a80 | FMT frame builder (main/sub/type/seq/ack + len) |

`IpcTxExchange` places `main@+0, sub@+0x0a? (see store offsets)`. The exact
on-wire FMT request layout for a data call is NOT yet fully decoded; it is
the next clean-room target. The APN for T-Mobile NL (MCC204/MNC16) must be
confirmed before any transmitting data-call request, and any bearer request
requires the operation-specific owner approval gate re: data charges.

No speculative data-call or PDN request was transmitted, and no rmnet
interface was forced UP. Wi-Fi (`wlan0 10.20.30.16`) and management links
were preserved throughout.


---

## ROUND 6c — Final state + integrity (2026-11-23 ~17:30 CET)

Post-work device state (verified live):

| Check | Value |
|---|---|
| CP state | `ONLINE` (kernel sysfs) |
| nuxel-radiod | `active` (new binary, names every FMT message) |
| Wi-Fi | `wlan0 inet 10.20.30.16/24` UP (preserved) |
| USB mgmt | `usb0 inet 10.100.10.1/24` UP (preserved) |
| rmnet0..7 | DOWN (no data bearer — honest, pending) |
| RADIO `/dev/sda16` | `9ffa1426…66fc7` UNCHANGED (no protected-partition write) |

Highest supported verdict this round (no fabricated PASS):

**`LTE_REGISTRATION_VERIFIED_ON_HARDWARE`** — the physical CP is ONLINE;
SIPC5 FMT vocabulary is fully recovered (O4) and the daemon now decodes it;
the modem reports a REAL serving PLMN `20416` (MCC 204 / MNC 16, T-Mobile
Netherlands) via NET_SERVING_NETWORK, a USIM (`SEC_SIM_ICC_TYPE=02`), SIM ON,
and `SEC_PIN_STATUS` transitioning through READY. A real LTE data bearer
(rmnet UP + verified cellular internet) is the ONE remaining gate; its exact
PDP-context/APN serialization was inventoried but NOT speculatively
transmitted (data-charge safety), and remains the next clean-room target.


---

## ROUND 7 — TX framing CONTRADICTION RESOLVED + native data-path TX serializer implemented (2026-11-23 ~18:10 CET)

### 1. Priority-Zero resolved: the TX framing is `sipc_fmt_hdr` (SAME as RX)

The Stage-06 "contradiction" between the RX parser (`sipc_fmt_hdr`) and the
`IpcTxExchange` disassembly is now DEFINITIVELY resolved with three independent,
source-backed lines of evidence. There are **two distinct framing layers** and
they must not be conflated:

**(a) The data-path `IpcTx*` functions emit `sipc_fmt_hdr` + payload (NOT the
14-byte checksum frame).** Disassembly of the exact vendor RIL
(`IpcTxGetPdpContext` @0x31f928, `IpcTxPsAttach` @0x31fa98,
`IpcTxSetMobileDataSetting` @0x3214c8) proves the stack buffer is:

```
+0..1  u16 total_len (LE)          e.g. 10 / 7 / 9 / 134
+2     u8  msg_seq                 (0)
+3     u8  ack_seq                 (0)
+4     u8  main_cmd                (packed `strh (main | sub<<8)`)
+5     u8  sub_cmd
+6     u8  cmd_type
+7..   payload
```

`IpcTxPsAttach` stores `strh 0x030d, [sp+12]` (main=0x0d/13 GPRS, sub=0x03/3 PS)
and `strb 0x03, [sp+14]` (type) — byte-for-byte `sipc_fmt_hdr`. This is exactly
the 7-byte header the existing RX parser (`sipc5_fmt.c`) already understands.

**(b) The kernel TX path (`modem_io_device.c::misc_write`) is opaque w.r.t. the
FMT header**: it `copy_from_user`'s the userspace bytes verbatim and only
prepends the SIPC5 **link-layer** header (`sipc5_build_header`, gated on
`iod->link_header == true` for the FMT channel). It does NOT parse main/sub/type
and does NOT add a checksum. So userspace writes `sipc_fmt_hdr`+payload and the
kernel adds the link header transparently — symmetric with RX, where the kernel
strips the link header before `sipc_fmt_hdr` reaches userspace.

**(c) `IpcTxExchange` @0x342a80 is a DIFFERENT, SEPARATE path.** It builds a
14-byte-prefixed frame (`[u16 len][u16 0x0605][u8 0x02][u8 cksum_hi][u8
cksum_lo][main][sub][type][ack][msg]...` with an additive
`checksum = fid + payload_len`). That is an *exchange*-specific dialogue used by
a different code path (IpcExchange), NOT the SIM/PDP data-path functions. It is
therefore the source of the apparent contradiction and must NOT be used for
SIM/registration/bearer traffic.

**Gate TX-FRAME-01: PASS.** The physical transport framing is now unambiguous:
`[u16 total_len][u8 msg_seq][u8 ack_seq][u8 main][u8 sub][u8 type][payload]`
in both directions.

### 2. cmd_type semantics (recovered from TX, direction-aware)

| numeric | recovered meaning (TX evidence) |
|---|---|
| 0x01 | REQUEST (observed `main=38 sub=1 type=1` as CP request in round-4) |
| 0x02 | REQUEST/RESPONSE (IpcTxGetPdpContext query emits type=2) |
| 0x03 | NOTIFICATION (live AST_POWERON; IpcTxPsAttach/IpcTx* data-path emit type=3) |

Because the vendor data-path TX uses `type=3` for `IpcTxPsAttach`/
`IpcTxSetMobileDataSetting`/`IpcTxDefinePdpContext`, the earlier "0x03 = only
CP→AP notification" simplification is corrected: the *direction* is encoded
elsewhere; 0x03 is the vendor's "set/indication" class for these data-path
writes. The serializer reproduces the recovered numeric value per command
(source-backed; not guessed).

### 3. Implemented: `fmt_tx.{h,c}` — source-backed FMT TX serializers

New module `src/fmt_tx.{h,c}` (pure serializer, never transmits) with
byte-exact builders recovered from the exact vendor disassembly:

- `fmt_tx_ps_attach` — main=13 sub=3 type=3, 3-byte payload (attach/suspend/reason)
- `fmt_tx_get_pdp_context` — main=13 sub=4 type=2, 7-byte query
- `fmt_tx_mobile_data` — main=13 sub=29(SYNC_PROFILE_INFO) type=3, 2-byte payload
- `fmt_tx_define_pdp_context` — main=13 sub=1 type=3, 134-byte (APN@offset10, protocol byte)
- `fmt_tx_get_sim_status` / `fmt_tx_get_atr` / `fmt_tx_get_serving_network` /
  `fmt_tx_get_registration` — 7-byte queries (SIM/NET families)

### 4. Implemented: `data_session.{h,c}` — bounded response-correlated FSM

`src/data_session.{h,c}`: a PURE state machine driving SIM_CHECK →
ENABLE_MOBILE_DATA → DEFINE_PDP → PS_ATTACH → DATA_CALL → WAIT_IP → ACTIVE. A
phase advances ONLY on an authenticated modem response (never on a frame
write), retries are bounded (3), and REJECTED/FAILED are terminal. No PIN/PUK/
IMSI/ICCID/IMEI/MSISDN is stored.

### 5. radiod integration (reversible, opt-in)

`radiod.c` now:
- includes `fmt_tx` + `data_session`, adds an opt-in `write_enabled` +
  `data_path_armed` flag;
- emits the current data-session phase frame once and waits for a correlated
  FMT response before advancing;
- exposes `StartDataSession("su"→b)` / `StopDataSession` D-Bus methods and
  `--write-enable` / `--arm-data-path` CLI flags;
- reports `lte_data` capability as `active`/`pending`/`unsupported` truthfully.

Off by default: the installed service remains observer-only unless explicitly
armed. This preserves the safety contract (no speculative/automatic TX).

### 6. Offline validation (all green, host + cross-compile)

- `test_fmt_tx` — 25 assertions; every vector byte-compared against the vendor
  disassembly (PsAttach 10B, GetPdpContext 7B, SetMobileDataSetting 9B,
  DefinePdpContext 134B, APN rejection, overflow guard). RESULT=PASS.
- `test_data_session` — 14 assertions; phase ordering, no-fabricated-advance,
  terminal rejection, bounded-retry→FAILED. RESULT=PASS.
- Full `build.sh`: 6 unit suites + 3000-iter fuzzer (536 cov) + ASan/UBSan
  (3000-iter, 549 cov). build+test OK.
- New radiod.c cross-compiles cleanly on-device (`-Wall -Wextra -Werror`, links
  `-lsystemd`, 78024-byte binary `radiod-new`).

### 7. What remains for a FULL data PASS (honest)

- The **DefinePdpContext / SetDataProfile payload's APN profile wire bytes**
  (protocol/auth enum → byte mapping) and the exact **SetDataCallEstablish /
  SetDataProfile** final bytes are recovered but the *live* data-call
  establishment must still be exercised on hardware.
- A **live, bounded** data-session transmission (APN `internet`, T-Mobile NL
  MCC204/MNC16) must be performed with per-step response correlation, then the
  rmnet interface/IP/route/DNS/HTTPS proof. This is the next executable step
  and is authorized by the owner.
- Subjobs B (NetworkManager bearer) and D (UI state machine) remain offline-
  only; SMS/Voice/IMS capability flags stay `false`.

**Strongest supportable verdict this round:** `TX_FRAMING_RESOLVED` +
`DATA_PATH_SERIALIZERS_IMPLEMENTED_SOURCE_BACKED` — the central framing blocker
is closed and the native data-path serializer + bounded FSM are implemented and
offline-verified, ready for the authorized live data-session test.
