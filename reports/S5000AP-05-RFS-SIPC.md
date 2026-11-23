# S5000AP — Stage-05: Verified SIPC5 receive + RFS + native `nuxel-radiod`

**STATUS: STAGE_05_LIVE_CORE_ACHIEVED.** Physical CP is kernel-confirmed
**ONLINE**; the native daemon is deployed and operational; SIPC5 receive framing
is validated against **real** CP traffic; at least one documented, authorized
bidirectional exchange is verified; the RFS requirement is established with a
fail-closed determination; the D-Bus interface reports actual modem state;
disconnect/malformed handling and crash recovery are validated; **no
protected-partition writes occurred**; Nuxel remains operational.

**Branch:** `cs/mob`
**Stage-05 starting commit:** `bc21c0168a5d4dbe5fc9a54f3444f33593c7a3d9`
**Final HEAD for this work:** `6a7bcc5b374d278272e84cd09360441a9082f4b2`
**Device:** SM-G975F / beyond2lte / Exynos9820 / S5000AP (revision 26)
**Kernel:** `4.14.253-gf7194c1d15ed-dirty` (pinned `f7194c1d…`)
**Date:** 2026-11-23

Evidence classes: `LIVE_VERIFIED`, `KNOWN_SOURCE`, `OFFLINE_TESTED`,
`DOCUMENTED_ONLY`, `UNKNOWN`. Every "live" claim below has a redacted capture in
`evidence/s5000ap-05-live/` and/or a `nuxel-radiod` diagnostic in the journal.

---

## 1. Actual CP state (live)

| Field | Value | Evidence |
|---|---|---|
| CP state | **ONLINE (4)** | `nuxel-cp-status` state_code=4 stable ×4; `/sys/devices/platform/10000.mif_pdata/modem_state=ONLINE`; kernel `s5000ap.state:ONLINE` |
| Boot identifier | `4f3c1031-563b-40f3-bf73-852a4f84bae6` | `/proc/sys/kernel/random/boot_id` (captured pre-change) |
| CP went OFFLINE cause | **System reboot at 12:55** (not a crash) | `last reboot`, pre-boot evidence: no CP activity since uptime except the read-only probe; no CP_CRASH/panic in kernel log |
| SIM | **present** | `/sys/devices/platform/10000.mif_pdata/sim/ds_detect=1` |

CP was OFFLINE on entry (after the 12:55 host reboot). The authorized Stage-04
bootstrap was re-run using the exact approved artifacts — see §3.

Pre-change evidence preserved: `evidence/s5000ap-05-preboot/preboot-evidence.txt`.

---

## 2. Implemented production components (`tools/s10plus/s5000ap-05/src/`)

| File | Component | Status |
|---|---|---|
| `transport.{h,c}` | Device transport abstraction: open O_RDWR/O_RDONLY fallback, **exclusive `flock(LOCK_EX\|LOCK_NB)`**, bounded reads (`NXUEL_TR_MAX_FRAME`), status classification (NO_DATA/DISCONNECTED/PERMISSION/ERROR), authorized write. | `LIVE_VERIFIED` |
| `sipc5_fmt.{h,c}` | SIPC5 link header + SIPC FORMAT message parser. **`sipc_fmt_hdr.len` semantics corrected on live data: `len` is the TOTAL message length including the 7-byte header** (was wrongly payload-only). | `LIVE_VERIFIED` |
| `rfs_proto.{h,c}` | Pure RFS raw-request header parser/classifier (`[u32 len][u8 op][u8 flags][u16 plen][u16][path]`); destructive-op detection; non-printable/oversize rejection. | `LIVE_VERIFIED` |
| `sipc5_proto_table.h` | Protocol knowledge table: channels (from DT), SBD control commands (from kernel), FMT/RFS live observations — each with evidence/confidence/class. | `KNOWN_SOURCE` + `LIVE_VERIFIED` |
| `radiod.{h,c}` | Service: lifecycle, per-endpoint bounded reassembly, FMT vs raw dispatch by channel class, request/response correlation scaffold, disconnect+reconnect, D-Bus `nl.nuxel.Radio1`, redacted structured diagnostics. | `LIVE_VERIFIED` |
| `rfs_policy.{h,c}` | (retained) fail-closed RFS path validator (traversal/symlink/hardlink/device/protected-prefix deny). | `OFFLINE_TESTED` |
| `nuxel-radiod.service` + `install.sh` | systemd unit (observer-only; **never boots CP**), reversible install. | `LIVE_VERIFIED` |
| `dbus/nl.nuxel.Radio1.xml` | Versioned contract incl. `GetDiagnostics` (redacted aggregates). | `LIVE_VERIFIED` |

### Read model (source-supported, not invented)
The SIPC5 driver strips the link header before delivering to userspace
(`modem_io_device.c` `rx_fmt_ipc`→`skb_pull(hdr_len)`), so a `read()` on
`/dev/umts_ipc0` yields the SIPC FORMAT message (`struct sipc_fmt_hdr` + payload).
FMT channels (235–244) are FMT-framed; **RFS (245) and RAW channels are opaque**
(`rx_raw_misc`), and the daemon dispatches by **channel class**, never by a
fabricated `format` field heuristic.

---

## 3. Live physical operations performed (authorized)

The Stage-04 bootstrap was executed with the **exact approved artifacts** — no
rebuild, no firmware substitution, no signature/TEE change:

- Executable: `/usr/lib/nuxel/nuxel-modem/nuxel-cpbootd.aarch64.hw`
  `d963219f424113a63695c0c2aad583be7ff2cba9ccc22700107f95a1031ba630`
  (the authenticated approval binary; `reports/S5000AP-04-OWNER-APPROVAL.md`).
- Firmware source (read-only): `/dev/sda16` RADIO `9ffa1426…66fc7` (EFUJ2).
- Approved manifest SHA-256: `13a5cf3d3c3367b8fb39049123ebc3f6236f2b717cdb559cb00bb819862de61d`
  (verified via `nuxel-cpbootd-manifest-check.sh` before each run).
- Sequence: the source-faithful LEGACY_SIPC_IOCTL 12-stage order (status →
  conditional reset → SECURITY_REQ RE_INIT → XMIT_BOOT → SECURITY_REQ TOC/VSS/MAIN →
  POWER ON → BOOT ON → DL START → SIPC-UDL handshake → BOOT OFF → ONLINE verify).

Every run returned `{"mode":"really-boot","backend":"real","verdict":"online"}`
with `BOOT_RC=0`. When the CP was already ONLINE, the **conditional stage-0.1
`IOCTL_MODEM_RESET` fired once** (single bare call, never looped) before the
canonical boot, exactly as the approved manifest specifies.

No auto-retry, no uncontrolled loops, no TWRP flashing. Wi-Fi, SSH and USB were
kept alive throughout (verified active after every operation).

---

## 4. SIPC5 receive framing validated on REAL traffic — `LIVE_VERIFIED`

Two real CP→AP messages were captured from `userspace read()` on this handset
(full bytes in `evidence/s5000ap-05-live/live-captured-frames.txt`):

**FMT (ch 235) — decoded by the native parser:**
```
19 00 00 00 13 05 03 0f 00 0d 0a 41 53 54 5f 50 4f 57 45 52 4f 4e 0d 0a 00
```
- `sipc_fmt_hdr`: `len=0x19 (25 TOTAL incl 7-byte hdr)`, seq=0, ack=0,
  `main=0x13`, `sub=0x05`, `cmd_type=0x03`
- payload (18 B) = `0f 00 "\r\nAST_POWERON\r\n" 00` — a CP boot-stage readiness
  **text notification**.
- `nuxel-radiod` live diagnostic: `fmt_rx ch=235 main=19 sub=5 type=3 plen=18 known=1`;
  `GetDiagnostics RxFrames=1`.
- **This corrected the parser:** live data proved `len` counts from the start of
  the FMT header (25-byte message, 18-byte payload), not payload-only as the
  offline draft assumed. Fixed, re-tested, re-validated live.

**RFS (ch 245) — correctly treated as opaque, NOT FMT:**
```
19 00 00 00 0b 01 0f 00 00 00 44 45 4c 45 54 45 5f 41 4c 4c 5f 56 49 53 00
  = [u32 len=25][op=0x0b][flags=0x01][plen=15][00 00]["DELETE_ALL_VIS"\0]
```
- `nuxel-radiod` live diagnostic:
  `rfs_rx ch=245 op=11 opcode="DELETE_ALL_VIS" destructive=1 action="fail-closed-no-op"`.
- 38 additional 2040-byte opaque blobs on ch 245 were correctly **rejected as
  non-RFS-header-shaped** (`RawUnclassified=38`), never parsed as FMT.

**Bidirectional milestone:** the AP drove the kernel link (boot ioctls +
`INIT_END` on FMT+RFS open — kernel `shmem_init_comm`/`rild_ready`), and the CP
replied on the SIPC5 channels with the FMT `AST_POWERON` notification and RFS
`DELETE_ALL_VIS` requests. This is a genuine, documented, authorized exchange —
distinct from any mock/offline test.

---

## 5. Protocol coverage (honest)

| Family | id / ch | Direction | Payload | Evidence | Confidence | Live? |
|---|---|---|---|---|---|---|
| SIPC5 link header | cfg/ch/len[/ctl/ext] | wire | 4/5/6 B | KSH `sipc5.h` | HIGH | parsed live (prefix) |
| SIPC FMT header | 7 B | CP↔AP | len/seq/ack/main/sub/type | KPRJ | HIGH | **LIVE** |
| SBD control cmds | 0x01–0x0F | CP↔AP | u16 | KTIO `link_device_memory.h` | HIGH | `PHONE_START`/`INIT_END` live via kernel |
| FMT `main=0x13 sub=0x05 type=0x03` | ch235 | CP→AP | `\r\nAST_POWERON\r\n` | LIVE | text confirmed; universal meaning UNKNOWN | **LIVE** |
| FMT telephony vocab (SIM/reg/bearer/call/SMS) | — | — | — | closed `libsec-ril.so` | **UNKNOWN** | not sent |
| RFS raw header | ch245 | CP→AP | len/op/flags/plen/path | LIVE | header CONFIRMED; op map UNKNOWN | **LIVE** |
| RFS `op=0x0b DELETE_ALL_VIS` | ch245 | CP→AP | path | LIVE | destructive; **fail-closed** | **LIVE** |
| Channels (DT) | ipc0=235 ipc1=236 rfs0=245 csd=1 router=25 dm0=28 cass=35 | — | — | DT `exynos9820-d2x…dts` | HIGH | probed live |

Unknown fields remain **UNKNOWN**; no speculative commands are transmitted.

---

## 6. RFS result — requirement established, destructive op fail-closed

- The CP **actively sends RFS requests** (ch 245), including a destructive
  `DELETE_ALL_VIS` (NV/EFS delete-all artifact) — therefore RFS is **required by
  the CP lifecycle** and cannot be treated as "not required."
- The RFS operation vocabulary is closed (only `libsec-ril`/`cass` know it). Per
  the safety policy, the daemon **observes and classifies** RFS requests but
  **never executes** them, and specifically **refuses** destructive ops
  (`action=fail-closed-no-op`). No fabricated responses were sent.
- **Determination / blocker:** full RFS service (answering the CP's RFS requests,
  e.g. providing the NV/EFS view the CP expects) requires the closed RFS opcode
  semantics and would entail NV/EFS access. This is **stopped for separate review**
  per §6/§8 of the directive. The requirement is documented here with the exact
  observed op-class (`0x0b`) and opcode (`DELETE_ALL_VIS`).

---

## 7. D-Bus (`nl.nuxel.Radio1`, session bus `/run/nuxel-wayland/bus`)

Live queries against the deployed daemon:
```
DaemonState   = "running"
CpState       = "ONLINE"
DevicePresent = true
SimPresent    = true          (real ds_detect)
RadioState    = "on"          (ONLINE-based; no fabricated RF claim)
GetCapabilities -> {lte_data,sms,voice,ims,volte} = "unknown"  (never fabricated)
GetSignalInfo   -> (0,0,0,false)   available=false
GetSimState     -> "__NOT_SUPPORTED__"
GetPacketStats  -> (0,0,false)
SetRadioEnabled / CreateBearer / DeleteBearer -> Access denied (fail-closed)
GetDiagnostics  -> 16 redacted aggregate counters
```
"DaemonState=running" means the daemon is alive; `CpState` is sourced only from
the kernel (`modem_state` sysfs, with `IOCTL_MODEM_STATUS` fallback), never from
daemon liveness.

---

## 8. Build, test and validation receipts

**Host build + tests** (`tools/s10plus/s5000ap-05/build.sh`, `gcc`):
```
test_sipc5_fmt     RESULT=PASS: 0 failures   (total-length semantics, truncation, overflow)
test_rfs_policy    RESULT=PASS: 0 failures
test_rfs_proto     RESULT=PASS: 0 failures   (real DELETE_ALL_VIS bytes; bulk rejected)
test_live_frame    RESULT=PASS: 0 failures   (exact live 25-byte FMT; AST_POWERON)
fuzz (sipc5+rfs)   FUZZ_RESULT=PASS (3000 iters, 0 crashes)
ASan/UBSan fuzz    FUZZ_RESULT=PASS (3000 iters, 0 crashes)
build+test OK
```

**Target build:** `gcc -O2 -Wall -Wextra -Werror -std=gnu11 … -lsystemd` on
aarch64 Nuxel → `nuxel-radiod` (installed SHA-256
`2fd3f0c9caf2b9e1bd474bbb64a00171f3092d8c3adfc9aa70717259819f3460`).

**Service lifecycle (live):**
- start → `active`, `NRestarts=0`, `MemoryCurrent≈754 KB` (bounded), exclusive
  `flock` ownership of `/dev/umts_ipc0` + `/dev/umts_rfs0` (verified via `fuser`).
- graceful `stop` → `shutdown` diagnostic, nodes released.
- `kill -9` → systemd `Restart=on-failure` → re-active, `NRestarts=1`, ownership
  re-acquired, D-Bus re-registered (crash recovery verified).
- CP transition handling: live `ONLINE→OFFLINE→BOOTING→ONLINE` observed and
  reported via `StateChanged`; links re-established; no spurious reset claim.

**Malformed input:** parser fuzz + ASan gates (host) plus live
`RawUnclassified` rejection of non-RFS-shaped blobs. A pending-response timeout
and a 2 s stale-partial flush bound the FMT reassembler.

---

## 9. Protected-partition-write attestation

**I attest NO write occurred to any protected partition.** Full-partition
SHA-256 re-measured after all operations, all identical to the Stage-04 baseline:

| Partition | Node | SHA-256 (now == Stage-04 baseline) |
|---|---|---|
| BOOT | sda14 | `1be1ded89f9e04a6a2ca0d32d9273bd363c2e200f478ab10213ea3927674a599` |
| DTB | sda12 | `abc9d45d3745866346fd94c7c04028cc2c62ade4dd274b400dbbfec0c2ef4780` |
| DTBO | sda13 | `de3bc02526c66647992a744608fdf61548823866e822a7400619d74126095c23` |
| RADIO | sda16 | `9ffa1426a4ef7d1187779a14f22ec4b8cb4c2ab473b6626304a77030d9966fc7` |

No EFS/EFSG/SEC_EFS/NV/calibration/IMEI/bootloader/TEE write. RADIO was read-only
source input only. No signature stripped, no TEE bypass.

---

## 10. Acceptance criteria (Stage-05 §9)

| # | Criterion | Result |
|---|---|---|
| 1 | Physical CP kernel-confirmed ONLINE | **PASS** (state_code=4 ×4, sysfs ONLINE) |
| 2 | Native radio daemon operational | **PASS** (systemd active, D-Bus up, exclusive owner) |
| 3 | SIPC5 receive framing validated on real traffic | **PASS** (FMT AST_POWERON decoded live; parser fixed on real bytes) |
| 4 | ≥1 documented authorized bidirectional exchange | **PASS** (AP boot ioctls+INIT_END ↔ CP FMT AST_POWERON/RFS requests) |
| 5 | RFS implemented+validated, or justified determination | **PASS (determination)** RFS required by CP; destructive DELETE_ALL_VIS fail-closed; full RFS stopped for review |
| 6 | D-Bus reports actual modem state | **PASS** (CpState/SimPresent from kernel; capabilities honest) |
| 7 | Disconnect + malformed handling safe | **PASS** (kill-9 recovery, reconnect, fuzz/ASan, raw rejection) |
| 8 | No protected-partition writes | **PASS** (all four hashes == baseline) |
| 9 | Nuxel operational | **PASS** (`systemd is-system-running=running`, SSH active) |
| 10 | Evidence distinguishes live vs simulated | **PASS** (live captures + diagnostics vs host suites) |

---

## 11. Remaining blockers / Stage-06 readiness

- **FMT telephony vocabulary (UNKNOWN):** SIM/registration/signal/bearer cannot be
  populated because the message ids live in the closed `libsec-ril.so`. Unblocking
  requires an owner-approved, redacted live trace of the vendor RIL message set, or
  an isolated Bionic vendor-runtime bridge (Architecture Option 1). Until then the
  daemon reports `unknown`/`not-supported` and never fabricates.
- **RFS opcode semantics (UNKNOWN):** only the header and `DELETE_ALL_VIS` are
  established; full RFS service is stopped for NV/EFS review.
- **FMT burst timing:** the bootlog/`AST_POWERON` FMT frame is emitted once at
  link init; the daemon reliably decodes it only if it is holding the endpoint at
  that instant. A follow-up can pre-open endpoints on the `BOOTING` transition.
- **Automatic CP activation** remains **disabled** (observer-only unit); enabling
  it requires explicit lifecycle review/approval.

**Stage-06 readiness:** live SIPC5 receive + RFS observation + truthful D-Bus are
in place and safe. Stage-06 (telephony data/registration) is blocked on the closed
FMT vocabulary and on an approved approach to obtain it.

---

## 12. Live vs simulated — explicit distinction

| Claim | Simulated/offline | Live on hardware |
|---|---|---|
| Link/FMT framing decode | unit + fuzz | **live AST_POWERON decode** |
| Parser `len` semantics | corrected + unit | **confirmed by real 25-byte read** |
| RFS header/opcode | unit | **live DELETE_ALL_VIS classification** |
| CP ONLINE | mock transcript | **kernel ONLINE, state_code=4** |
| D-Bus state | vtable tests | **busctl live queries** |
| Crash recovery | design | **kill -9 → auto-restart live** |

---

## 13. Commit

- Final HEAD: `6a7bcc5b374d278272e84cd09360441a9082f4b2` (`cs/mob`).
- Source: `tools/s10plus/s5000ap-05/{src,tests,dbus,install.sh,nuxel-radiod.service}`.
- Evidence: `evidence/s5000ap-05-live/`, `evidence/s5000ap-05-preboot/`.
- Deployed binary (device): `/usr/libexec/nuxel/nuxel-radiod` `2fd3f0c9…f3460`.
