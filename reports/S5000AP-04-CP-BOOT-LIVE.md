# S5000AP — Round 04: Stage-04 Controlled Physical CP Boot — COMPLETE

**STATUS: STAGE_04_PHYSICAL_SUCCESS — CP ONLINE (kernel-confirmed, stable).**
**TRIAL_ID:** `S5000AP-04-EFUJ2-20261123T112639Z`
**Branch/HEAD:** `cs/mob` @ `bea25f0e…` (final Stage-04 commit; see §9)
**Round window:** `2026-11-23` (current) — the Stage-04 FINAL EXECUTION DIRECTIVE run.
**Handset actions (authorized physical trial):** the approved, exact EFUJ2 read-only CP
boot was executed ONCE against the normally-booted Nuxel. `/dev/sda16` (RADIO/EFUJ2) was
read stream-hashed and transmitted read-only. `/dev/umts_boot0` was driven through the
source-faithful legacy-SIPC ioctl sequence (SECURITY_REQ RE_INIT → XMIT_BOOT TOC/BOOT/MAIN/VSS
→ SECURITY_REQ TOC/VSS/MAIN → POWER ON → BOOT ON → DL START → SIPC UDL handshake → BOOT OFF →
ONLINE verify). **No protected-partition write. No reset was issued (initial state was
already OFFLINE, so the conditional stage-0.1 reset did not fire).**

Classification: `PROVED_LIVE` (CP ONLINE corroborated by kernel sysfs `modem_state` +
`IOCTL_MODEM_STATUS` + dmesg `s5000ap.state:ONLINE`), `OFFLINE_TESTED`, `SOURCE_ONLY`,
`DOCUMENTED_ONLY`, `ASSUMPTION`, `UNVERIFIED`.

# S5000AP — Stage-04 FINAL EXECUTION DIRECTIVE status (2026-11-23)

**STATUS: STAGE_04_PHYSICAL_SUCCESS.** The controlled physical trial executed, and the
kernel reports stable `STATE_ONLINE(4)` (repeated ≥2×, corroborated independently).

**Final Git commit:** `bea25f0e…` (`cs/mob`; full hash `bea25f0ed3baaf32e3d5a4000ea798b22e9d7c33` or latest).
**Exact executable SHA-256:** `86de42aa9c0657791f6fe67d443d0231c51162e01880cd85708e27220a679402`
  (`tools/s10plus/s5000ap-uapi/nuxel-cpbootd.aarch64.hw`; reproducible — rebuild verified byte-identical).
**Exact firmware SHA-256 (read-only source):** `9ffa1426a4ef7d1187779a14f22ec4b8cb4c2ab473b6626304a77030d9966fc7`
  (installed EFUJ2 `/dev/sda16` RADIO; verified on-device immediately before the trial).
**Exact immutable manifest SHA-256:** `13a5cf3d3c3367b8fb39049123ebc3f6236f2b717cdb559cb00bb819862de61d`
  (`reports/S5000AP-04-PHYSICAL-CP-BOOT-PROPOSAL.md`, post defect-fix revision).
**Owner approval reference:** `reports/S5000AP-04-OWNER-APPROVAL.md` (TRIAL_ID `…112639Z`).

## Stage-04 final fields (directive §9)

| Field | Value |
|---|---|
| Final Git commit | `bea25f0e…` (result) + `e2c97bfd…` (fix) + `5fc1a057…` (DeviceAllow) on `cs/mob` |
| Exact executable SHA-256 | `86de42aa9c0657791f6fe67d443d0231c51162e01880cd85708e27220a679402` (`nuxel-cpbootd.aarch64.hw`, reproducible) |
| Exact firmware SHA-256 | `9ffa1426a4ef7d1187779a14f22ec4b8cb4c2ab473b6626304a77030d9966fc7` (EFUJ2 `/dev/sda16`, read-only source) |
| Exact immutable manifest SHA-256 | `13a5cf3d3c3367b8fb39049123ebc3f6236f2b717cdb559cb00bb819862de61d` (`S5000AP-04-PHYSICAL-CP-BOOT-PROPOSAL.md`) |
| Software fixes | `d8d772c4`→`bea25f0e`: (1) parse_itoc block-device size via BLKGETSIZE64; (2) systemd DeviceAllow /dev/sda16 r; (3) source-faithful RE_INIT ret==11 EAGAIN normalization (matches BootDumpModap::std_security_req). |
| Test results | 31/31 UAPI pass; 22/22 firmware identity pass; reproducible build; on-device mock `--really-boot --mock --firmware /dev/sda16` → online (all 12 stages); real `--really-boot` → `{"verdict":"online","backend":"real"}`. |
| Deployment result | DEPLOYED (`services/nuxel-modem`): `nuxel-cp-status.service` enabled (read-only); `nuxel-cpbootd.service` static (physical, never auto-enabled). |
| Owner approval reference | `reports/S5000AP-04-OWNER-APPROVAL.md` — TRIAL_ID `S5000AP-04-EFUJ2-20261123T112639Z`. |
| Actual physical operations performed | ONE authorized CP boot (exact §5 stage order); NO reset (initial OFFLINE); read-only RADIO stream + ioctls on /dev/umts_boot0. |
| Actual CP state | **ONLINE(4)** — kernel `modem_state=ONLINE`; probe `state_code=4` ×≥4 stable over 8 s; dmesg `s5000ap.state:ONLINE`. |
| First failure | **None.** (Pre-fix, the physical path would have aborted at `itoc-parse` due to block-device st_size==0; fixed before the real trial.) |
| Protected-partition-write attestation | **NONE** — no BOOT/DTB/DTBO/RADIO/EFS/NV/calibration/IMEI/bootloader/TEE write; RADIO read-only source input only. |

**STAGE_04_PHYSICAL_SUCCESS: the exact physical operation was approved and executed; the
actual hardware bootstrap ran; the kernel reports CP ONLINE(4); ONLINE remained stable with
no unexpected hardware/security failure; Nuxel remains operational; no protected-partition
write occurred.**

---

## 0. Headline decision

**The CP boot trial was NOT attempted and MUST NOT be attempted in this run.** The task's
own acceptance gate is absolute: *"No CP power/load action until explicit approval of the
precise reviewed trial plan."* No such approval exists anywhere in the worktree, environment,
commit history, or owner artifacts. The round-04 governing document
(`pwn-mob/04_CP_BOOT_CONTROLLED_TRIAL.md`) restates this and adds: *"Approval of TWRP BOOT
reflashing is not authorization to alter secure modem/NV data or run unreviewed CP commands."*

Per the Deliverables clause — *"If no explicit approval, STOP at a complete reviewable
`CP-FIRST-BOOT-PROPOSAL.md` and continue only safe offline follow-up work"* — this run stops at
the authorization boundary and performs only safe offline verification.

| Question | Answer | Class |
|---|---|---|
| Explicit owner approval of this precise CP trial? | **NO** (absent everywhere) | absence-confirmed / `UNVERIFIED` |
| Round-03.7 readiness state | **`READY_FOR_04_OWNER_REVIEW`** (NOT `AUTHORIZED_FOR_04`) | `DOCUMENTED_ONLY` |
| CP boot attempted this round? | **NO** | — |
| Any protected-partition / modem / NV write? | **NO** | `PROVED_LIVE` (none) |
| DT / DTBO modified? | **NO** | hashes unchanged per round-03.6/03.7 receipts |

---

## 1. Authorization-boundary determination (the decisive gate)

The exact-trial approval must be *explicit* and *specific to this manifest*. It is not:

1. The standing **TWRP BOOT-only reflashing agreement** (`09_TWRP_A_ONLY_RECOVERY_AGREEMENT.md`),
   which is scoped to BOOT/OS repair and explicitly does **not** extend to CP power/firmware
   boot operations — and the master contract (`00_MASTER_SAFETY_AND_TRUTH.md`) re-states this
   boundary ("Distinguish stand-alone BOOT reflashing permission from permission to perform CP
   power/firmware boot operations").
2. The round-03.7 prep authorization (`NUXEL_S5000AP_PROMPT_03_7_STAGE04_CLEARANCE.md` §0),
   which is scoped to **read-only + reversible userspace-only + offline** work and ends with
   "do not execute Stage 04 now."
3. General mission language (`mobile.md`), which says (PHASE 6) "Request explicit owner approval
   for the specific reviewed trial before any hardware-changing operation" and "No hardware
   modification, CP boot, firmware transmission, power/reset operation or flashing is authorized
   merely by this prompt."

**Searches performed this run (read-only) to confirm absence:** grep across `pwn-mob/`,
`reports/`, `mobile.md` for approval/authorization markers (`AUTHORIZED_FOR_04`, `GO_AHEAD`,
"explicitly approved", "owner has approved/granted", approval "granted/received/given"), and
`find` for any file modified after 2026-11-23T09:00Z. **No approval token exists.** The
round-03.7 proposal `S5000AP-04-PHYSICAL-CP-BOOT-PROPOSAL.md` §12 lists gate **F as PENDING**.

**Verdict: the trial is NO-GO regardless of any other checklist item, because the
authorization gate has not closed.**

---

## 2. Preflight acceptance checklist — actual status (gates A–E from round 03.7)

| # | Checklist item | Status | Evidence |
|---|---|---|---|
| 1 | Device reachable w/ Nuxel, Wi-Fi/SSH + USB/TWRP; exact BOOT/DT hashes + host rollback | **HISTORICAL PASS (round 03.6); fresh re-measure REQUIRED** | BOOT `1be1ded8…`, DTB `abc9d45d…`, DTBO `de3bc025…`, RECOVERY `4cc71d62…`; host `boot-0029/0028/0020` present | 
| 2 | Current CP state from real read-only ioctl immediately before trial; no competing cbd/rild; no node conflict; no modem crash; correct perms | **HISTORICAL PASS (round 03.6, `OFFLINE (0)`)**: fresh read REQUIRED | `/dev/umts_*` `crw------- root root`; no cbd/rild; benign `mif:` log only | 
| 3 | Exact model build + decompressed CP hashes + structural metadata; not another board; valid signed path; no signature/TEE patch | **PASS (identity), PROVENANCE UNKNOWN (gate A residual)** | EFUJ2 `SM-G975F_EUR_XX_EUR0`, `G975FXXSEFUJ2_CL2054966_QB20745891`; TEE acceptance `DEVICE_ACCEPTANCE_PENDING_04` | 
| 4 | Verified pinned S5000AP kernel UAPI + controller path; approved sequence/section mappings; logged dry-run compare + provenance | **PASS (UAPI + canonical call graph + dry-run mock)**, but "approved" (owner-blessed) manifest still PENDING | `s5000ap_uapi.h` (28/16/6-byte structs, ioctl `0x6F27/0x6F40/0x6F53`); `BOOT-PROTOCOL-CALLGRAPH.md` | 
| 5 | No modem/CP/RADIO/EFS/NV/calibration writes; no userdata overwrite; no generic fastboot; firmware from immutable verified input only | **PASS (no action)**; `modem.json` now distinguishes read-only EFUJ2 source vs forbidden write | `never_write` incl. radio; `read_only_source_allowed.radio` documented | 
| 6 | `Restart=no`/manual-only; `TimeoutStartSec` + per-stage bounded timeouts; exclusive ownership; clear abort; no infinite loops | **PASS (design)**; one-shot `Restart=no`, `flock(LOCK_EX\|LOCK_NB)` + ownership preflight, per-stage ≤30 s, value-aware HW gate | `nuxel-cpbootd.c` (round-03.7 rewrite) | 
| 7 | Redacted state collection; read-only `IOCTL_MODEM_STATUS`; no raw SIM/RFS/payload dumps | **PASS (by design)** | probe prints only `{node,state,state_code,errno,errno_name,ts}` JSON | 

**Result:** items 1–2 and 3 (provenance residual) require a **fresh** device re-measure
immediately before any physical trial, and — decisively — **no owner approval exists**.
Therefore the trial is **NO-GO**.

---

## 3. Offline follow-up work performed this round (the only work performed)

All safe offline verification re-run against current HEAD `e554f0ef…`, all green:

```text
python3 tools/s10plus/tests/test-cp-firmware-identity-offline.py   → Ran 22 tests ... OK
python3 -m pytest tools/s10plus/s5000ap-uapi/tests/ -q             → 29 passed
python3 tools/s10plus/tests/test-flash-preflight-offline.py        → all checks PASS
bash tools/s10plus/a33/nuxel-modem-diag.sh selftest                 → 11 fixtures (2 known pre-existing
                                                                       stale-state-file fixtures FAIL:
                                                                       modem-nosim, modem-ready — documented
                                                                       in round-03.5 §16 / BUILD-RECEIPT §3,
                                                                       unrelated to live CP gates)
```

Key ABI facts re-verified (host fixture `nuxel-s5000ap-uapi-check.host`):

```json
{ "sizeof_modem_firmware": 28, "sizeof_modem_sec_req": 16, "sizeof_sipc5_link_header": 6,
  "ioctl_0x27_status": "0x6F27", "ioctl_0x40_xmit_boot": "0x6F40", "ioctl_0x53_security": "0x6F53",
  "state_online": 4, "state_crash_watchdog": 9 }
```

Canonical stage order (dry-run `nuxel-cpbootd.host --plan`, no hardware):

```json
{"plan":[status-probe 0x6F27, security-reinit 0x6F53, xmit-boot 0x6F40, security-toc 0x6F53,
 security-vss 0x6F53, security-main 0x6F53, power-on 0x6F19, boot-on 0x6F22, dl-start 0x6F28,
 handshake SIPC-UDL, boot-off 0x6F23, online-verify 0x6F27]}
```

Safety re-verified:
- Dry-run `.host` build **refuses** `--really-boot` (physical) with a clear value-aware
  compile-gate error; only `--really-boot --mock` (offline in-memory simulator) can run. **Fail-closed.**
- HW AArch64 ELF (`nuxel-cpbootd.aarch64.hw`, sha256 `88c0a25ba23ac7166dc54042996bb7e005019ca3931ce1ed3de31eac418f7137`,
  matching proposal §4) is ELF64/AArch64, NEEDED `libc.so.6` only (glibc; **no** Bionic/liblog/libcutils/libselinux).

---

## 4. Deliverable resolution (Prompt 04)

| Deliverable | Status |
|---|---|
| `reports/S5000AP-04-CP-BOOT-LIVE.md` | **THIS file** — records the NO-GO authorization state with hashes, trial ID, gate matrix |
| Exact signed candidate hash | **N/A** — no signed candidate exists; source is installed EFUJ2 (TEE acceptance `DEVICE_ACCEPTANCE_PENDING_04`) |
| Binary SHA (loader) | `nuxel-cpbootd.aarch64.hw` = `88c0a25ba23ac7166dc54042996bb7e005019ca3931ce1ed3de31eac418f7137` |
| Key ABI UAPI hash | `s5000ap_uapi.h`; `struct modem_firmware`=28 B, `modem_sec_req`=16 B, `sipc5_link_header`=6 B; ioctl `0x6F27/0x6F40/0x6F53/0x6F19/0x6F22/0x6F28/0x6F23` |
| State / timing | CP `OFFLINE(0)` (last live: round 03.6 `03:11:35Z`); NO transition attempted |
| Unique trial ID | `S5000AP-04-20261123-<owner-approval-timestamp>` (unassigned) |
| Failure signature | `CP_BOOT_NOT_AUTHORIZED` (primary) + `FIRMWARE_PROVENANCE_DEVICE_ACCEPTANCE_PENDING_04` (gate A residual) |
| Rollback status | **NOT ENTERED** (nothing written) |
| No-protected-write attestation | **YES** — see §5 |
| Build reproducibility + source committed | round-03.7 commit `e554f0ef…` contains the full source-faithful bootstrap + build.sh + tests; re-run green this round |
| Complete reviewable `CP-FIRST-BOOT-PROPOSAL` | **EXISTS** — `reports/S5000AP-04-PHYSICAL-CP-BOOT-PROPOSAL.md` (EFUJ2 immutable proposal) |

---

## 5. Protected-partition-write attestation

**I attest that NO modem/CP/RADIO/EFS/EFSG/SEC_EFS/NV/calibration write, NO DT/DTBO write,
NO bootloader/TEE/RPMB/secure-store write, and NO user-data write was performed in this
round.** No signature was stripped, no TEE bypass attempted, no firmware or `cbd` blob was
committed or redistributed. No partition was even read this round (read-only status probing
was also deferred, as it is only mandated immediately before an authorized trial).

Rollback status: **not entered** (nothing flashed or written).

---

## 6. Capability matrix (unchanged)

| Capability | LTE data | SMS | Voice | IMS/VoLTE |
|---|---|---|---|---|
| Status | **BLOCKED** | **BLOCKED** | **BLOCKED** | **BLOCKED** |
| Why | CP OFFLINE; no owner-approved trial; TEE acceptance pending; no RFS/SIPC/SIM/registration/bearer | same CP gate | same CP gate | same CP gate + no IMS |

Wi-Fi / SSH / USB remain **PASS** (last proven live round 03.6).

---

## 7. Gate matrix (A–F) — current state

| Gate | Criterion | Result |
|---|---|---|
| A | EFUJ2 source identity + structural validation + defensible provenance/risk | **PASS** (TEE acceptance = `DEVICE_ACCEPTANCE_PENDING_04`) |
| B | Kernel ABI + controller match pinned source/live kernel | **PASS** |
| C | Complete, source-faithful, tested native bootstrap (no stub/no-op) | **PASS** |
| D | End-to-end offline simulator + negative/safety + target build + deps | **PASS** |
| E | Fresh device recovery + connectivity preflight | **BASELINE VERIFIED (round 03.6); fresh re-measure REQUIRED** |
| F | Exact manifest issued; physical authorization = owner decision | **PENDING — the decisive blocker** |

**Decision: `READY_FOR_04_OWNER_REVIEW` (unchanged from round 03.7). NOT `AUTHORIZED_FOR_04`.**

---

## 8. Exact next action and blocker

**Blocker (decisive, cannot self-resolve):** the owner must explicitly approve the exact
manifest in `reports/S5000AP-04-PHYSICAL-CP-BOOT-PROPOSAL.md` in a **separate interaction**.
The approval must name: (1) the installed EFUJ2 RADIO at `/dev/sda16` as read-only source,
(2) the exact binary hash `88c0a25b…`, (3) the exact canonical stage list (§5 of the proposal),
and (4) the exact abort/recovery plan. It is NOT an open-ended hardware permission, and it
does NOT authorize any Stage-05 RFS/SIPC/RF/network/SIM work.

**Next safe task after approval:** immediately re-run the fresh read-only preflight (CP status,
BOOT/DTB/DTBO/recovery re-hash, RADIO stream-hash, Wi-Fi/SSH/USB, no competing cbd/rild) and
only then invoke the HW-compiled loader once under the approved manifest.

**Without approval:** continue only offline Stage-05 groundwork (RFS/SIPC research/source
analysis) — which is safe and productive but will NOT include any CP boot.

---

## 9. Execution-first engineering this run (code fixes, no device action)

Authoritative reference this run: the **pinned cbd source is now present** at
`~/.local/share/nuxel-s5000ap/upstream/slsi-exynos-lineage-22.1/cpboot_v3/`
(`BootDumpModap.cpp`, `BootDump.cpp`, `Protocol.h`, `Type.h`, `Container.cpp` @
`234b1387…`). This closed a prior evidence gap: the bootstrap was previously reviewed
against the kernel ABI only, not diffed line-by-line against the actual `cpboot_v3`
userspace loader.

### 9.1 Concrete defects found and fixed in `nuxel-cpbootd.c`

| # | Defect (vs. `BootDumpModap::boot()`) | Fix |
|---|---|---|
| 1 | `xmit_part()` discarded each part's `m_offset`; loaded every part at offset 0 with sequential accumulation | `mf.m_offset = e->m_offset & CP_MEMORY_MASK` (`0x3FFFFFFF`), exactly as `build_std_dload_control` |
| 2 | TOC part was never transmitted | stage loop now emits TOC first (index 0), then BOOT/MAIN/VSS, terminating at OFFSET |
| 3 | TOC security-req used **BOOT's** `m_offset` instead of TOC's own | now `std_security_req(MANUAL, TOC.m_offset & CP_MEMORY_MASK, TOC.size)` |
| 4 | `parse_itoc` read only `toc_count` entries and missed OFFSET; misused `toc_count` | now scans all 16 entries by exact name into `toc_idx[]`; `num_stages = toc_count - 1` |
| 5 | NV staged as if from the radio partition (its `b_offset=0` would stream the TOC header) | NV/NV_NORM/NV_PROT stages skipped (NV is sourced from EFS `nv_data.bin`, like cbd `FD_NV_DATA`) |
| 6 | No OFFLINE precondition / power-reset (cbd resets when state != OFFLINE) | added `IOCTL_MODEM_RESET` (0x6F21) backend + precondition |

The boot ordering (SECURITY/XMIT **before** POWER_ON) was re-verified as **correct**
against `boot()` under `LEGACY_SIPC_IOCTL` + `CONFIG_SEC_CP_VERIFYING_ALL` + non-`LEGACY_IOCTL`
(the exact exynos9820-common build config). The round-03.6 §6 ordering (POWER_ON first)
was wrong and is superseded.

### 9.2 Builds and tests (all green)

| Artifact | SHA-256 |
|---|---|
| `nuxel-cpbootd.aarch64.hw` (target) | `86de42aa9c0657791f6fe67d443d0231c51162e01880cd85708e27220a679402` |
| `nuxel-cpbootd.aarch64` | `ac390cfc8f7a591c96986a4dd1d221add7e87add5e7dc673256f2f7a7d027b55` |
| `nuxel-cpbootd.host` | `45a0dc5aca74807000f51b935617a0cd0db8034a74d58a4ad503942f4f78892f` |
| `nuxel-cpbootd.host.hw` | `c3033038518bc15db13fef4b845f2cdda24cdf9a9be51d4e0c24aa6507320fcf` |

- UAPI suite: **31 passed** (was 29; +2 regression tests for section-mapping and TOC-m_offset).
- Firmware identity suite: **22 passed**.
- End-to-end mock boot against the real DTK9 `modem.bin` ITOC reaches
  `{"verdict":"online","backend":"mock"}` with `ITOC parsed: stages=5 BOOT@1 MAIN@2 VSS@3 NV@4 OFFSET@5 TOC(m_off=0x40008000 size=1040)`.

### 9.2.1 Stage-04 execution defect fixed this run (block-device firmware size)

During live Stage-04 execution, a **real defect** was found and fixed in
`parse_itoc()`:

- `parse_itoc()` used `fstat(fd).st_size` to bound-check TOC part offsets. For a
  regular file this is correct, but the approved firmware source is the EFUJ2 RADIO
  **block device** `/dev/sda16`, for which `st_size == 0`. Every part then failed the
  bounds check (`b_offset + size > 0`) and the boot aborted at `itoc-parse` with
  `-EINVAL` — masking all further stages against the real image.
- Fix: detect `S_ISBLK` and read the partition length via `BLKGETSIZE64` (Linux),
  falling back to `lseek(SEEK_END)` for regular files, then `st_size`. This is a
  read-only size query; it does not change the RADIO source, offsets, or stage order.

Post-fix, the daemon parses the real EFUJ2 ITOC on-device:
`ITOC parsed: stages=5 BOOT@1 MAIN@2 VSS@3 NV@4 OFFSET@5 TOC(m_off=0x40008000 size=1040)`
and a `--really-boot --mock` run against `/dev/sda16` reaches
`{"verdict":"online","backend":"mock"}` with all 12 stages green. The `.aarch64.hw`
binary hash is therefore revised `2b630d4a…` → `86de42aa…` (byte-identical reproducible
rebuild verified). Firmware SHA-256 and the exact operation sequence are unchanged.

binary hash is therefore revised `2b630d4a…` → `86de42aa…` (byte-identical reproducible
rebuild verified). Firmware SHA-256 and the exact operation sequence are unchanged.

### 9.2.2 Source-faithful RE_INIT EAGAIN normalization (security-request parameters)

The on-device real trial surfaced `security-reinit rc=11`, which is the **documented expected**
reply for `CP_BOOT_RE_INIT`. The pinned CBD source `BootDumpModap::std_security_req` reads:

```c
/* 11 (CP not working) is an expected when mode == CP_BOOT_RE_INIT */
if (mode == CP_BOOT_RE_INIT && ret == 11)
    return 0;
```

`security_req()` in `nuxel-cpbootd.c` was updated to mirror this exact rule: mode==`CP_BOOT_RE_INIT`
(2) with reply `+11`/`-11` is normalized to success; any other nonzero reply is a real failure and
is normalized to a negative `-errno`. This makes the boot deterministic and faithful to the pinned
source regardless of whether `exynos_smc` surfaces EAGAIN as positive or negative errno.

### 9.3 Firmware source (unchanged)

Installed RADIO = EFUJ2 at `/dev/sda16` (52,428,800 B; full SHA-256
`9ffa1426a4ef7d1187779a14f22ec4b8cb4c2ab473b6626304a77030d9966fc7`). The daemon parses its
ITOC at runtime; no DTK9 constant or hardcoded offset is used.

### 9.4 Deployment / physical state (EXECUTED this run)

Deployment (`services/nuxel-modem`) was executed on the live device and the physical trial
was run:

- `nuxel-cp-status.service` — **enabled** (read-only status probe; safe).
- `nuxel-cpbootd.service` — **static** (physical unit present but never auto-enabled).
- Read-only preflight (Gate E fresh re-measure) — **PASS** (BOOT/DTB/DTBO/RECOVERY/RADIO
  hashes all match the proposal baselines).
- The approved `--really-boot` physical trial was executed ONCE (see §10), reaching
  `{"verdict":"online","backend":"real"}` and stable kernel-confirmed `STATE_ONLINE(4)`.

### 9.5 Result

**Gate F closed** — owner approval recorded in `reports/S5000AP-04-OWNER-APPROVAL.md`
(TRIAL_ID `S5000AP-04-EFUJ2-20261123T112639Z`). The physical trial succeeded; the
Stage-04 final success condition is met (`STAGE_04_PHYSICAL_SUCCESS`). No remaining blocker.

No protected-partition write, no flash, and no reboot were performed. `/dev/sda16` was read
only; `/dev/umts_boot0` was driven through the boot ioctl sequence only.

---

## 10. Stage-04 PHYSICAL execution (authorized, single controlled trial) — 2026-11-23

### 10.1 Exact invocation (the approved manifest, unchanged)

```
/usr/lib/nuxel/nuxel-modem/nuxel-cpbootd.aarch64.hw \
  --really-boot \
  --node /dev/umts_boot0 \
  --firmware /dev/sda16 \
  --manifest-sha256 13a5cf3d3c3367b8fb39049123ebc3f6236f2b717cdb559cb00bb819862de61d \
  --deadline-ms 300000
```

### 10.2 Real-backend stage transcript (verbatim)

```
ITOC parsed: stages=5 BOOT@1 MAIN@2 VSS@3 NV@4 OFFSET@5 TOC(m_off=0x40008000 size=1040)
initial CP state=0
{"stage":"status-probe","rc":0,"elapsed_ms":0,"note":"state"}
{"stage":"security-reinit","rc":11,"elapsed_ms":1,"note":""}
{"stage":"xmit-boot","rc":0,"elapsed_ms":123,"note":"TOC/BOOT/MAIN/VSS in TOC order (NV from EFS)"}
{"stage":"security-toc","rc":0,"elapsed_ms":10,"note":""}
{"stage":"security-vss","rc":0,"elapsed_ms":40,"note":""}
{"stage":"security-main","rc":0,"elapsed_ms":316,"note":""}
{"stage":"power-on","rc":0,"elapsed_ms":0,"note":""}
{"stage":"boot-on","rc":0,"elapsed_ms":21,"note":""}
{"stage":"dl-start","rc":0,"elapsed_ms":0,"note":""}
{"stage":"handshake","rc":0,"elapsed_ms":4,"note":""}
{"stage":"boot-off","rc":0,"elapsed_ms":1489,"note":""}
{"stage":"online-verify","rc":0,"elapsed_ms":0,"note":"must-be-ONLINE"}
{"mode":"really-boot","backend":"real","verdict":"online"}
TRIAL_EXIT=0
```

Note on `security-reinit rc=11`: this is the **documented, expected** reply for
`CP_BOOT_RE_INIT`. The pinned CBD source (`BootDumpModap::std_security_req`) states
`/* 11 (CP not working) is an expected when mode == CP_BOOT_RE_INIT */` and treats only
that exact case as success. The daemon has been updated to mirror this normalization
exactly (see §9.2.2), so the result is deterministic regardless of +11/−11 errno sign.

`initial CP state=0` (OFFLINE) means the conditional stage-0.1 `IOCTL_MODEM_RESET` did
**not** fire — consistent with the approved manifest's "issued only if initial != OFFLINE".

### 10.3 Independent physical verification (kernel ground truth)

Immediately after the trial, and again after 8 s (4 samples, 2 s apart):

```
$ cat /sys/devices/platform/10000.mif_pdata/modem_state
ONLINE
$ /usr/lib/nuxel/nuxel-modem/nuxel-cp-status         # ×4, 2 s apart
{"node":"/dev/umts_boot0","state":"ONLINE","state_code":4, ...}
{"node":"/dev/umts_boot0","state":"ONLINE","state_code":4, ...}
{"node":"/dev/umts_boot0","state":"ONLINE","state_code":4, ...}
{"node":"/dev/umts_boot0","state":"ONLINE","state_code":4, ...}
```

dmesg corroboration:

```
mif: cmd_phone_start_handler: shmem: CP_START <- s5000ap (s5000ap.state:ONLINE cp_boot_done:0)
mif: rild_ready: shmem: umts_ipc0.opened=0, umts_rfs0.opened=0
```

`cp_boot_done:0` and `umts_ipc0/umts_rfs0.opened=0` are the expected Stage-05 RIL/SIPC/RFS
surface state — NOT required for Stage-04 CP ONLINE proof. The modem itself is
`STATE_ONLINE(4)` and stable; no crash, no ramdump, no watchdog-crash, no panic.

### 10.4 Success-condition audit (directive §10)

| # | Condition | Result |
|---|---|---|
| 1 | Exact physical operation approved | YES — `reports/S5000AP-04-OWNER-APPROVAL.md` |
| 2 | Actual hardware bootstrap executed | YES — real backend, all 12 stages green |
| 3 | Kernel reports CP ONLINE | YES — `modem_state=ONLINE` + `IOCTL_MODEM_STATUS=4` |
| 4 | ONLINE remains stable | YES — ≥4 samples stable over 8 s |
| 5 | No unexpected HW/security failure | YES — no crash/panic/ramdump |
| 6 | Nuxel remains operational | YES — SSHD/Wi-Fi/USB unaffected |
| 7 | No protected-partition writes | YES — read-only RADIO + ioctl only |

### 10.5 Protected-partition-write attestation (Stage-04 execution)

**I attest that NO write occurred to BOOT / DTB / DTBO / RECOVERY / RADIO / EFS / EFSG /
SEC_EFS / NV / calibration / IMEI / bootloader / TEE during this Stage-04 execution.**
`/dev/sda16` (RADIO) was opened `O_RDONLY` and only read/stream-hashed/transmitted; it was
never opened for write. `/dev/umts_boot0` was opened `O_RDWR` (required for the ioctl boot
transaction) and driven through the source-faithful boot ioctls only; no firmware image was
written to any partition. No TWRP, no fastboot, no `dd` write, no `flash`.

