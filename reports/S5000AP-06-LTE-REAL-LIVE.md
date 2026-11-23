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

