# S5000AP — Prompt 04: One Controlled, Owner-Approved CP Boot Trial

**Status: NO-GO — STOPPED BEFORE ANY CP POWER/LOAD ACTION (no explicit owner approval).**
**TRIAL_ID:** `S5000AP-04-20261123T025707Z`
**Branch/HEAD:** `cs/mob` @ `45b9097f3c989347ebc8572d733ca4e3a72f63e4` (unchanged this round)
**Round window:** `2026-11-23T02:57Z` → `2026-11-23T03:05Z`
**Handset actions:** **READ-ONLY ONLY.** A single `IOCTL_MODEM_STATUS` read (via the
already-deployed read-only `nuxel-cp-status` probe), plus read-only inspection of
systemd health, `/dev/umts_*` permissions, `rmnet*` state, route table, process table,
and kernel journal excerpt. **No CP power-on, reset, boot-on, XMIT_BOOT, SECURITY_REQ,
DL_START, or any other mutating ioctl. No flash, no reboot, no partition write, no
DT/DTBO/DTS change.**

Classification: `PROVED_LIVE`, `CAPTURED_LIVE_OLDER`, `OFFLINE_TESTED`, `SOURCE_ONLY`,
`DOCUMENTED_ONLY`, `ASSUMPTION`, `UNVERIFIED`, `BLOCKED`.

---

## 0. Headline decision

**CP BOOT WAS NOT ATTEMPTED.** Per the task's own acceptance gate — *"No CP power/load
action until explicit approval of the precise reviewed trial plan"* — and per the
Deliverables clause — *"If no explicit approval, STOP at a complete reviewable
`CP-FIRST-BOOT-PROPOSAL.md` and continue only safe offline follow-up work"* — the run
halted at the authorization boundary.

The round-03.5 closing state was `NOT_READY` with gates **A (firmware provenance)** and
**F (owner approval)** unresolved. Neither has closed in this run. No owner approval
document, file, commit message, or terminal signal granting this precise trial exists
anywhere in the worktree, the private workspace, or the environment.

| Question | Answer | Class |
|---|---|---|
| Explicit owner approval of this precise CP trial? | **NO** (absent everywhere) | `UNVERIFIED`/absence-confirmed |
| Firmware provenance closed? | **NO** (`STRUCTURALLY_VALID_PROVENANCE_UNKNOWN`) | round-02/03.5 |
| CP boot attempted? | **NO** | — |
| Protected-partition write? | **NO** | `PROVED_LIVE` (none) |
| DT/DTBO modified? | **NO** (hashes re-verified matching) | `CAPTURED_LIVE_OLDER` + round-03.5 |

---

## 1. Preflight acceptance checklist — actual status

| # | Checklist item | Actual status | Evidence |
|---|---|---|---|
| 1 | Device physically reachable; working Nuxel, Wi-Fi/SSH + USB/TWRP; exact BOOT/DT hashes; host rollback image(s) | **PARTIAL → PASS for reachability; PARTIAL for freshness** | SSH OK via `root@10.11.12.99` (`PROVED_LIVE` this round). BOOT/DT hashes last independently verified round-03.5 (`CAPTURED_LIVE_OLDER`): `sda14`=boot `1be1ded8…`, `sda12`=dtb `abc9d45d…`, `sda13`=dtbo `de3bc025…`, `sda15`=recovery `4cc71d62…`; host rollback `boot-0029`/`boot-0028`/`boot-0020` present. No DT/DTBO modification. |
| 2 | Current CP state from real read-only ioctl immediately before trial; no competing cbd/rild; no node owner conflict; no modem kernel crash/pstore warning; correct perms | **PASS** | `IOCTL_MODEM_STATUS` → `OFFLINE (0)` (`PROVED_LIVE`, 2026-11-23T02:57:24Z). `ps` shows **no cbd/rild**. `/dev/umts_*` all `crw------- root root`. `dmesg` modem excerpt shows only benign `misc_open`/`misc_release` from the probe — no panic/warning. |
| 3 | Exact model build, decompressed CP primary image hashes + structural metadata; not from another board; valid signed path; no signature/TEE patch plans | **FAIL (provenance)** | Image `1e4280d2…` structurally valid, DTK9/model-matched, but `STRUCTURALLY_VALID_PROVENANCE_UNKNOWN`: original `.tar.md5` absent; `CL1535157/QB17435920` ≠ documented `CL20034833/QB35905779`; `NONEmrk`; signature chain unverifiable. **No signature/TEE patch is planned or allowed.** |
| 4 | Verified pinned S5000AP kernel UAPI + controller path; approved sequence/section mappings from matching cbd; logged dry-run compare + provenance | **PARTIAL** | Kernel UAPI verified (`s5000ap_uapi.h`, 21 pytest + `_Static_assert`, `OFFLINE_TESTED`). Boot sequence recovered from source (`SOURCE_ONLY`). But S5000AP `-t` type-string detail unresolved; no *approved* (owner-blessed) sequence/section mapping exists. |
| 5 | No modem/CP/RADIO/EFS-family/NV/calibration writes; no user-data overwrite; no generic fastboot; runtime takes firmware only from immutable verified private input | **PASS (no action taken)** | Zero writes performed. RADIO partition not even addressable on this boot (no by-name/PIT map). |
| 6 | Process manager `Restart=no`/manual-only; `TimeoutStartSec` + per-stage bounded timeouts; exclusive ownership; clear abort paths; no infinite loops | **PASS (design) / not deployed** | `nuxel-cpbootd` is dry-run only; HW path gated behind `-DNUXEL_CPBOOTD_ENABLE_HW=1` + `--really-boot`; exclusive `flock(LOCK_EX|LOCK_NB)`; no auto-retry. No unit was installed/started this round. |
| 7 | Redacted state collection enabled; no raw SIM/RFS/payload dumps | **PASS (by design)** | Probe prints only `{node,state,state_code,errno,errno_name,ts}` JSON. No identity/payload captured. |

**Result: checklist items 3 and partially 4 FAIL (or remain UNRESOLVED) — therefore the
trial is NO-GO regardless of the approval gate.**

---

## 2. Before-snapshot (captured this round, all read-only)

| Fact | Value | Class |
|---|---|---|
| Model | `SM-G975F` / `beyond2lte` / Exynos9820, `revision=26` | `PROVED_LIVE` |
| Kernel | `4.14.253-gf7194c1d15ed-dirty` | `PROVED_LIVE` |
| systemd | `is-system-running` = `running`; `--failed` = none | `PROVED_LIVE` |
| CP status | `OFFLINE (0)` via `/usr/local/bin/nuxel-cp-status /dev/umts_boot0` | `PROVED_LIVE` (02:57:24Z) |
| `/dev/umts_*` perms | `boot0 cass csd dm0 ipc0 ipc1 ramdump0 rfs0 router` all `crw------- root root` | `PROVED_LIVE` |
| rmnet | `rmnet0..7` all `down` | `PROVED_LIVE` |
| Default route | `default via 10.20.30.1 dev wlan0 ... src 10.20.30.16` | `PROVED_LIVE` |
| Interfaces up | `wlan0` UP (IPv4+IPv6); USB/ZeroTier previously observed up | `PROVED_LIVE` / `CAPTURED_LIVE_OLDER` |
| Competing cbd/rild | **none** | `PROVED_LIVE` |
| Modem kernel log excerpt | `mif: misc_open: umts_boot0 (opened 1) by nuxel-cp-status` / `misc_release` (only benign probe activity; no panic/warning) | `PROVED_LIVE` |

Wi-Fi, SSH, and all user functions were left untouched and intact.

---

## 3. Why the trial is NO-GO (exact, itemized blockers)

1. **Owner approval absent.** The task explicitly requires *explicit approval of the
   precise reviewed trial plan* before any CP power/load action. No such approval
   exists. The standing TWRP/BOOT-reflashing agreement (§09) is **not** authorization
   to boot/energize the CP or run CP commands — a boundary the master contract restates.
2. **Firmware provenance unresolved (gate A).** The candidate `modem.bin`
   (`1e4280d2…`) is `STRUCTURALLY_VALID_PROVENANCE_UNKNOWN`: original `.tar.md5`
   absent, package stamp `CL/QB` mismatch, `NONEmrk`, signature chain unverifiable
   offline. A CP boot cannot proceed on unauthenticated firmware.
3. **Installed RADIO partition identity unresolved.** Cannot be correlated with the
   derived `.bin` on this boot (no by-name/PIT map; raw UFS guessing forbidden).
4. **S5000AP `-t` type/section detail unresolved.** Recovered stock cbd `-tss310`
   maps (source-proven) to Shannon 310/ModAP, NOT the S5000AP/SIPC path. The correct
   type string is not in any recovered source.

These are genuine authorization/provenance boundaries. None is bypassed here.

---

## 4. State transition observation (as mandated, but observed as NO TRANSITION)

No `OFFLINE → BOOTING/LOADER_DONE → ONLINE` transition was attempted or observed. The
CP remained `OFFLINE (0)` across every read-only probe this round. This is the correct,
expected, un-forced state given the NO-GO decision.

---

## 5. Protected-partition-write attestation

**I attest that no modem/CP/RADIO/EFS/EFSG/SEC_EFS/NV/calibration, no DT/DTBO, no
bootloader/TEE/RPMB/secure-store, and no user-data write was performed in this round.**
No partition was read beyond the previously-authorized round-03.5 BOOT/DTB/DTBO/
recovery hashes. No signature was stripped, no TEE bypass attempted, no firmware or
`cbd` blob committed or redistributed.

Rollback status: **not entered** (nothing was flashed or written to warrant a rollback).

---

## 6. Deliverable resolution

Per the Deliverables clause, with no explicit approval, the run **stops at a complete
reviewable first-boot proposal**: `reports/S5000AP-03_5-CP-FIRST-BOOT-PROPOSAL.md`
(already produced in round 03.5, re-validated below), and does **only safe offline
follow-up work** — re-running the offline test suites, which remain green.

| Deliverable in Prompt 04 | Produced? | Where |
|---|---|---|
| `reports/S5000AP-04-CP-BOOT-LIVE.md` | **YES** (this file) | records the NO-GO with hard before-evidence, hashes, trial ID, failure signature |
| Exact signed candidate hash | **UNKNOWN** (not signed/proven) | round-02 §2.1 |
| Binary SHA | `modem.bin` = `1e4280d2…`; `modem.bin.lz4` = `05371984…` | round-02 |
| Key ABI UAPI hash | `s5000ap_uapi.h` pinned; ioctl `0x6F27/0x6F22/0x6F28/0x6F40/0x6F24/0x6F53`; `struct modem_firmware`=28 B | round-03 |
| State/timing | CP `OFFLINE(0)` @ 02:57:24Z | §2 |
| Unique trial ID | `S5000AP-04-20261123T025707Z` | §0 |
| Failure signature | `CP_BOOT_NOT_AUTHORIZED` + `FIRMWARE_PROVENANCE_UNKNOWN` | §0/§3 |
| Rollback status | NOT ENTERED | §5 |
| No-protected-write attestation | **YES** | §5 |
| Build reproducibility + source changes committed | offline suites re-run green; **no new source change this round** (nothing to commit) | §7 |

---

## 7. Offline follow-up work (the only work performed)

Re-run of the three offline suites — all green, no change to production paths:

```
python3 tools/s10plus/tests/test-cp-firmware-identity-offline.py   → Ran 22 tests ... OK
python3 -m pytest tools/s10plus/s5000ap-uapi/tests/ -q             → 21 passed
python3 tools/s10plus/tests/test-flash-preflight-offline.py        → all checks PASS
```

No source change was made this round; HEAD remains `45b9097f…`. The pre-existing
uncommitted items (round-02/03.5 tooling + reports, `pwn-mobile`→`pwn-mob` migration)
remain unstaged, as established in prior rounds.

---

## 8. Capability matrix (unchanged)

| Capability | LTE data | SMS | Voice | IMS/VoLTE |
|---|---|---|---|---|
| Status | **BLOCKED** | **BLOCKED** | **BLOCKED** | **BLOCKED** |
| Why | CP OFFLINE; firmware provenance unproven; no owner-approved trial; no RFS/SIPC/SIM/registration/bearer | same CP gate | same CP gate | same CP gate + no IMS |

Wi-Fi / SSH / USB remain **PASS** (`PROVED_LIVE`).

---

## 9. Next highest-value task and exact blocker

**Task:** obtain explicit owner approval of the precise reviewed trial **and** close
gate A (firmware provenance, `CL/QB` stamp resolution, or original `.tar.md5`) /
gate C (S5000AP `-t` type string + installed-RADIO identity).

**Exact blockers (all require owner/device input, none safe to self-resolve):**

1. Owner explicit approval of the exact round-03.5 operation set (`POWER_ON →
   XMIT_BOOT → BOOT_ON → DL_START → MAIN download → SECURITY_REQ → BOOT_OFF →
   BOOT_DONE → STATUS`, per-stage ≤30s abort, no blind retry).
2. Firmware provenance: original `.tar.md5`, or explicit confirmation that the
   derived `modem.bin.lz4`/`modem_debug.bin.lz4` are authoritative, plus `CL/QB`
   stamp resolution.
3. Correct S5000AP `-t` modem-type string (real DTK9 vendor runtime, or a bounded
   authorized live trace).
4. Installed RADIO partition identity (TWRP-side authorized read or safe recovery-
   context partition map).

No CP boot will be attempted until all of these close. No improvisation.
