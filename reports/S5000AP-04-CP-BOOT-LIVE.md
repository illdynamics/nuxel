# S5000AP — Round 04: One Controlled, Owner-Approved CP Boot Trial

**STATUS: NO-GO — NO CP POWER/LOAD ACTION PERFORMED (explicit owner approval ABSENT).**
**TRIAL_ID:** `S5000AP-04-20261123-<owner-approval-timestamp>` (unassigned; no approval timestamp exists)
**Branch/HEAD:** `cs/mob` @ `e554f0ef2b7f38c889b993fc2efcd74a24e54124`
**Round window:** `2026-11-23` (current) — this run reconciled rounds 01–03 receipts and the
round-03.7 Stage-04 clearance deliverables; no device was contacted for any mutating action.
**Handset actions:** **NONE.** No CP power-on/reset/boot-on/XMIT_BOOT/SECURITY_REQ/DL_START,
no firmware load/transmission, no flash, no reboot, no RF change, no partition read or write,
no DT/DTBO/DTS change, no `/dev/umts_*` open beyond read-only status (and not even that this
run, as no read-only status probe was warranted ahead of the authorization gate).

Classification: `PROVED_LIVE`, `CAPTURED_LIVE_OLDER`, `OFFLINE_TESTED`, `SOURCE_ONLY`,
`DOCUMENTED_ONLY`, `ASSUMPTION`, `UNVERIFIED`, `BLOCKED`.

# S5000AP — Stage-04 FINAL EXECUTION DIRECTIVE status (2026-11-23)

**STATUS: ENGINEERING COMPLETE — READY FOR OWNER APPROVAL GATE F.**
**NO physical CP action performed. NO live device connected this run.**

**Final Git commit:** `116d5d45c0efed55b3e71de2ae6616460223d9c0` (`cs/mob`).
**Exact executable SHA-256:** `2b630d4a8c7219c468a4aff94881029b23547d867f4f5a30898f080f2cb4fae7`
  (`tools/s10plus/s5000ap-uapi/nuxel-cpbootd.aarch64.hw`; reproducible — rebuild verified byte-identical).
**Exact firmware SHA-256 (read-only source):** `9ffa1426a4ef7d1187779a14f22ec4b8cb4c2ab473b6626304a77030d9966fc7`
  (installed EFUJ2 `/dev/sda16` RADIO; DTK9 is the OFFLINE TEST fixture only, NOT the trial source).
**Exact immutable manifest SHA-256:** `edc4f1e1b484a8d0cadd7e3be1a7321a100551422b15195f51d5c08a90dc3f4d`
  (`reports/S5000AP-04-PHYSICAL-CP-BOOT-PROPOSAL.md`, post-correction).

## Stage-04 final fields (directive §9)

| Field | Value |
|---|---|
| Final Git commit | `116d5d45c0efed55b3e71de2ae6616460223d9c0` (`cs/mob`) |
| Exact executable SHA-256 | `2b630d4a8c7219c468a4aff94881029b23547d867f4f5a30898f080f2cb4fae7` (`nuxel-cpbootd.aarch64.hw`, reproducible) |
| Exact firmware SHA-256 | `9ffa1426a4ef7d1187779a14f22ec4b8cb4c2ab473b6626304a77030d9966fc7` (EFUJ2 `/dev/sda16`, read-only source) |
| Exact immutable manifest SHA-256 | `edc4f1e1b484a8d0cadd7e3be1a7321a100551422b15195f51d5c08a90dc3f4d` (`S5000AP-04-PHYSICAL-CP-BOOT-PROPOSAL.md`) |
| Software fixes | proposal HEAD `ae26b271`→`d8d772c4`; explicit approval-record fields (conditional reset, 300 s max duration); `nuxel-cpbootd-manifest-check.sh` preflight (closes documented gap); `services/nuxel-modem` deployment (read-only probe + fail-closed one-shot unit + reversible install). |
| Test results | 31/31 UAPI pass; 22/22 firmware identity pass; flash preflight PASS; reproducible build (`2b630d4a…`); mock transcript `{"verdict":"online","backend":"mock"}`. |
| Deployment result | Prepared (`services/nuxel-modem`); NOT deployed — no live device; reversible userspace-only; physical unit `Restart=no`, never auto-enabled. |
| Owner approval reference | **PENDING (Gate F)** — exact manifest requires single owner decision. |
| Actual physical operations performed | **NONE** (no `--really-boot`, no mutating ioctl). |
| Actual CP state | **OFFLINE(0)** (last live read round 03.6; NOT re-measured — no device connected). |
| First failure | **None** (no physical attempt). |
| Protected-partition-write attestation | **NONE** — no BOOT/DTB/DTBO/RADIO/EFS/NV/calibration/IMEI/bootloader/TEE write; RADIO read-only only. |

**Gate F (owner approval of the unchanged manifest) is the sole remaining blocker.**


---

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
| `nuxel-cpbootd.aarch64.hw` (target) | `2b630d4a8c7219c468a4aff94881029b23547d867f4f5a30898f080f2cb4fae7` |
| `nuxel-cpbootd.aarch64` | `28c906564958ad9a0c33bf61019627a693991cdda1f9b9d5353be829047c3e3f` |
| `nuxel-cpbootd.host` | `7d8a69289868c709dc15f9916c0f87e42cf175fb04cdc9b3bd8acf7382547dad` |

- UAPI suite: **31 passed** (was 29; +2 regression tests for section-mapping and TOC-m_offset).
- Firmware identity suite: **22 passed**.
- End-to-end mock boot against the real DTK9 `modem.bin` ITOC reaches
  `{"verdict":"online","backend":"mock"}` with `ITOC parsed: stages=5 BOOT@1 MAIN@2 VSS@3 NV@4 OFFSET@5 TOC(m_off=0x40008000 size=1040)`.

### 9.3 Firmware source (unchanged)

Installed RADIO = EFUJ2 at `/dev/sda16` (52,428,800 B; full SHA-256
`9ffa1426a4ef7d1187779a14f22ec4b8cb4c2ab473b6626304a77030d9966fc7`). The daemon parses its
ITOC at runtime; no DTK9 constant or hardcoded offset is used.

### 9.4 Deployment / physical state

**No deployment executed.** The physical CP boot remains **NOT authorized**: no explicit
owner approval of the exact manifest exists (gate F PENDING). Per §4 of the directive, the
trial requires the exact firmware hash, executable hash, operation sequence, and abort
conditions to receive explicit owner approval first.

### 9.5 Remaining blocker

Gate F (explicit owner approval of `reports/S5000AP-04-PHYSICAL-CP-BOOT-PROPOSAL.md`) —
**the decisive, self-unresolvable blocker**. The proposal's binary/SHA/stage table must be
updated to the new `nuxel-cpbootd.aarch64.hw` hash `2b630d4a…` before approval is requested
against it.

No protected-partition write, no firmware transmission, no `/dev/umts_*` mutate, no flash,
and no reboot were performed this run.
