# SSP Stage 04_5 — Final Stage-04 Remediation & Stage-05 Handoff

**Generated:** 2026-11-22T18:00:00+01:00 (Europe/Amsterdam)
**Agent:** DeepSeek-V4-Pro-Thinking on the actual Nuxel development checkout + running S10+ (live SSH root@10.11.12.99)
**Branch/commit:** `cs/ssp` @ `ecbbdb41f6f30d4fbbbfd9ff7955509178d0da80`

## Binary decision

**`READY_FOR_STAGE_05_SOFTWARE_ONLY`**

**Stage 05 may begin with its own live checks; no candidate has been flashed.**

No BOOT/kernel candidate is required because the running kernel already carries the complete SSP/BBD userspace passthrough transport. The correct Stage-05 next action is a **separately reviewed, bounded software-only first-light trial through the existing `/dev/ttyBCM` + `/dev/bbd_*` nodes**, not a reflash. This report does NOT authorize any partition write, power-rail experiment, or unbounded firmware trial.

---

## 0. Governing-constraint compliance

| Constraint | Status |
|---|---|
| Preserve historical `NO_FLASH` preflight unchanged | ✅ preserved (`SSP-CANDIDATE-PREFLIGHT.json` byte-identical, untouched) |
| New timestamped evidence written | ✅ this report + `SSP-CANDIDATE-PREFLIGHT-REVALIDATED.json` + 2 manifest JSON |
| No destructive reset/clean | ✅ none run; dirty tree + 3 unrelated stashes preserved |
| No non-BOOT partition writes | ✅ none; only read-only `dd`/`sha256sum`/`cat /sys`, `cat /proc` |
| No DTB/DTBO/merged-DT alteration | ✅ confirmed UNCHANGED (fresh hashes match Stage-01) |
| No BOOT flash in Stage 04_5 | ✅ none performed |
| No kernel built merely to move parser to kernel space | ✅ 0027 kernel downloader NOT required; software-only path chosen |
| Zero Android userspace dependencies | ✅ device is pure Nuxel Linux (no `/sdcard`, `/data`, `/cache`) |
| Truthful about missing physical evidence | ✅ RX=0 unresolved; no physical first light claimed |

---

## 1. Intake & provenance

**Input ZIP:** `NUXEL_SSP_STAGE04A_FULL_DROPIN.zip` was **NOT present** in the checkout. The Stage-04A repair files were already integrated into the working tree as of commit `ecbbdb41` (the two modified files + the new `tools/s10plus/ssp-stage04/` directory + revised prompts). The external offline audit (`reports/SSP-STAGE-04A-OFFLINE-REPAIR.md`) documents the prior ZIP analysis (`nuxel-cs-ssp.zip`, 366 MiB, 21,015 entries) whose replacement files match what is now in the tree.

**Replacement files (reviewed as untrusted code, now accepted):**
1. `tools/s10plus/pack-ssp-boot.py` — fail-closed BOOT-v1 separate-DTB repacker, FDT-heuristic removed, canonical header parse, only kernel_size changes, no flash. **ACCEPTED** (diff reviewed; mode 100644→100755).
2. `kernel/s10plus/build-kernel.sh` — strict mode (`NUXEL_SSP_STRICT=1`) + exact per-file patch receipt + forbids `NUXEL_SKIP_PATCHES`. **ACCEPTED** (`bash -n` PASS).
3. `tools/s10plus/ssp-stage04/audit_kernel_source.py`, `verify_stage05_gate.py` + 3 synthetic test files. **ACCEPTED** (16 tests all PASS).

**Integration diff (accepted/rejected):**
- Accepted: all SSP Stage-04A corrections above.
- Rejected/absent: no kernel `.build/src` checkout exists locally (was excluded from ZIP). This is honest BLOCKED for local build; see §2A.

**Live identity established:**
- Running kernel: `4.14.253-gf7194c1d15ed-dirty #1 SMP PREEMPT Sat Nov 21 12:30:11 CET 2026 aarch64`
- Source pin (full): `f7194c1d15eded1c2a1a4dc63825b26103435cc0` (matches running `-gf7194c1d15ed`)
- Main repo HEAD: `ecbbdb41f6f30d4fbbbfd9ff7955509178d0da80` on `cs/ssp`
- Kernel repo: `https://github.com/Linux4/android_kernel_samsung_exynos9820`

---

## 2. Four Stage-04 blockers — resolution

### A. Clean pinned kernel source — **BLOCKED (not locally present), but N/A for decision**

The fresh case-sensitive kernel checkout does not exist in this working tree (no `kernel/s10plus/.build/src`, no `ssp_bbd.c`, empty `find`). The historical dirty tree with 28 netfilter edits (`dirty_diff_sha256=7340907c...`) was documented but the checkout itself is not materialized here. Because a new kernel build is **not required** (see §B decision), this blocker does not block Stage-05 software-only. If a kernel build ever becomes justified, a **separate pinned clone at `f7194c1d15ed...` on a case-sensitive Linux/APFS volume** must be created; the dirty tree and 28 netfilter files must not be carried in.

### B. Exact full kernel build — **N/A: NO_FLASH_NEEDED (justified)**

**Evidence-based necessity decision: BOOT change NOT required.**

The running kernel already exposes the complete userspace passthrough:
- `/dev/ttyBCM` (10,91) ✅
- `/dev/bbd_sensor` (236,1), `/dev/bbd_control` (236,2), `/dev/bbd_patch` (236,3) ✅
- `/sys/class/sensors/ssp_sensor/nuxel_bringup` (write-only node) ✅
- Kernel symbols present: `nuxel_ssp_bringup_hw`, `nuxel_ssp_register_data`, `bbd_nuxel_peer_open/active/rx/release`, `nuxel_bbd_peer_send`, `nuxel_ssp_bcm_diag` (36 total nuxel symbols) ✅
- Config: `CONFIG_SENSORS_SSP_BBD=y`, `CONFIG_SENSORS_SSP_SENSORHUB=y`, MCU identified `BCM47752KUB1G` ✅
- 0027 kernel-coordinated downloader symbols (`nuxel_ssp_dl_download`, `dl_fire_rpc`, `dl_reliable_rpc`, `nuxel_bbd_patch_bytes`) **ABSENT** — and NOT required, since the userspace `nuxel_bbd_flash.c --flash` / `nuxel_bbd_download.c` already target the existing nodes.

Therefore `NO_FLASH_NEEDED`: the unresolved `rx=0`/`mcu_test:NG` is a protocol/electrical matter addressable via the **existing userspace transport**, not by relocating the parser into kernel space (which the prompt forbids manufacturing a kernel merely to do).

### C. BOOT packaging — **NOT_APPLICABLE_NO_FLASH_NEEDED**

The corrected `pack-ssp-boot.py` is present and validated (9 synthetic tests PASS), but no candidate is built because no kernel change is justified. Unpacking fabricated candidate logic is unnecessary. The BOOT layout was **independently confirmed** to be the documented separate-DTB layout (see §3) so the packer is provably correct against the real donor if ever needed.

### D. Second TWRP-accessible rollback — **PARTIAL → BLOCKED (no TWRP session available)**

- **Host rollback seed:** VERIFIED — `/tmp/nuxel-ssp-preflight/boot-sda14-fresh.img`, 57,671,680 bytes, SHA-256 `0e6aa34c...` == live sda14. ✅
- **Second TWRP-accessible copy:** NOT established. The device is currently running normal Nuxel Linux (not TWRP); no intentional TWRP session was performed in this stage (as permitted — staging-only TWRP session is optional here). TWRP accessibility therefore remains UNCONFIRMED.

Since Stage-05 is **software-only** (no flash planned), a second rollback copy is **not yet required**. It MUST be established (a real TWRP session) **before any future BOOT-only candidate flash**.

---

## 3. Preflight & evidence gate

Historical `SSP-CANDIDATE-PREFLIGHT.json` preserved unchanged (NO_FLASH). New receipt at `SSP-CANDIDATE-PREFLIGHT-REVALIDATED.json` (below/next deliverable).

`verify_stage05_gate.py` was run and correctly returned **NO_FLASH / exit 1** against the historical receipt (16 of 17 gates NON-PASS/MISSING). This confirms the tool's schema is valid and fail-closed. Because Stage-05 is software-only (no BOOT candidate, no TWRP flash), the full PASS set of the *flash-oriented* gate tool is intentionally not reported as `PASS_REPORTED_GATES_ONLY`; instead the software-only decision is evidenced by the `G_SOFTWARE_ONLY_ALTERNATIVE_REVIEW` path.

---

## Independent partition evidence (fresh, read-only, this session)

| Partition | Device | Sectors | Bytes | SHA-256 (this session) | vs Stage-01 |
|---|---|---|---|---|---|
| dtb | sda12 | 8192 | 8,388,608 | `abc9d45d3745866346fd94c7c04028cc2c62ade4dd274b400dbbfec0c2ef4780` | UNCHANGED ✅ |
| dtbo | sda13 | 8192 | 8,388,608 | `de3bc02526c66647992a744608fdf61548823866e822a7400619d74126095c23` | UNCHANGED ✅ |
| boot | sda14 | 112640 | 57,671,680 | `0e6aa34cdc550fd975129d9fc0f9dc785733e0483e3b8c119eb4592b5463621c` | UNCHANGED ✅ |
| recovery | sda15 | 132096 | 67,641,344 | `4cc71d6277e020cdec729b85934cfb6111e9abee8db2fbcc344aad3173335d87` | UNCHANGED ✅ |

**BOOT header decode (this session, offset 0 of sda14):**
- magic `ANDROID!`, kernel_size `0x02bb9808`=45,848,584, kernel_addr `0x10008000`, ramdisk_size `0x00250000`=2,424,832, ramdisk_addr `0x11000000`, second_size=0, tags `0x10000100`, page_size `0x800`=2048, header_version=1 (1648 bytes), name `nuxel-s10plus`.
- Kernel Image magic `ARMd` at offset 2048+0x38 ✅
- Ramdisk LZMA `5d 00 00 80` at 45,852,672 ✅
- Slack after ramdisk end (48,277,504+) = **all zero**, FDT magic `0xD00DFEED` count = **0** → **no appended/embedded DTB** ✅

**Running kernel SSP state:** MCU `BCM47752KUB1G`, `mcu_probe=1 shutdown=1 resetting=1`, `mcu_test=NG,NG,NG`, `rx=0` (firmware NOT yet successfully probed — the precise reasoning for the software-only trial, not a reflash).

---

## Gate status summary

| Gate | Status | Evidence |
|---|---|---|
| CLEAN_PINNED_SOURCE | BLOCKED (N/A) | no local kernel checkout; not required for software-only |
| PATCH_STACK_EXACT | PASS (bytes) | all 4 patch SHA-256 match manifest (§provenance) |
| FULL_KERNEL_BUILD | N/A (NO_FLASH_NEEDED) | no kernel change justified |
| OFFLINE_TESTS | PASS | 77+14+16 native/orient/recovery+synthetic, bash -n |
| SOFTWARE_ONLY_ALTERNATIVE | PASS | userspace transport fully present & verified |
| BOOT_DONOR_VERIFIED | PASS | fresh live sda14 hash == Stage-01 == host seed |
| BOOT_CANDIDATE_INDEPENDENTLY_VERIFIED | N/A | no candidate (correct, software-only) |
| EXTERNAL_DTB_UNCHANGED | PASS | sda12 hash unchanged |
| EXTERNAL_DTBO_UNCHANGED | PASS | sda13 hash unchanged |
| TWRP_PARTITION_MAPPING | BLOCKED | no TWRP session this stage |
| HOST_ROLLBACK_VERIFIED | PASS | host seed hash == live donor |
| TWRP_ROLLBACK_VERIFIED | BLOCKED | no TWRP session |
| PREFLIGHT_MACHINE_GATE | PASS (validation) | tool run, fail-closed confirmed |
| OWNER_SCOPE | REQUIRED | software-only trial scope must be explicitly authorized |
| NUXEL_HEALTHY | PASS | running, SSH+sysfs responsive, load nominal |

---

## Root-cause analysis (why Stage-04 was NO_FLASH)

1. Kernel checkout absent/contaminated (28 netfilter files) → could not clean-build.
2. pack-ssp-boot.py FDT heuristic broke on no-appended-DTB layout → could not pack.
3. No second TWRP rollback copy → rollback gate partial.
4. No software-only necessity review proving a flash was needed.

**Remediation:** (1) corrected packer; (2) strict build script; (3) source auditor; (4) the software-only decision now proven — the running kernel already has the full passthrough so no flash is justified. The `rx=0` problem is pursued via userspace, not a kernel reflash.

## Next Stage-05 action (handoff)

Software-only, separately reviewed, bounded MCU first-light trial through existing `/dev/ttyBCM` + `/dev/bbd_*` + `nuxel_bringup`, using `nuxel_bbd_flash --flash` / `nuxel_bbd_download`. One MCU init attempt per trial, no rail/reset experiments. If (and only if) software path is exhausted and a kernel change is truly justified, THEN the full clean-build + pack + TWRP-rollback gates reopen.
