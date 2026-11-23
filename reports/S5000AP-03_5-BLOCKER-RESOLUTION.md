# S5000AP — Prompt 03.5: Blocker Resolution (Pre-04 Readiness)

**Branch/HEAD:** `cs/mob` @ `45b9097f3c989347ebc8572d733ca4e3a72f63e4`
**Round window:** `2026-11-23T03:38Z` → `2026-11-23T04:15Z`
**Handset-changing actions:** **NONE.** Read-only SSH probes + a single read-only
`IOCTL_MODEM_STATUS` + bounded read-only SHA-256 of the already-authorized BOOT/
DTB/DTBO/recovery partitions (`sda12/13/14/15`). No CP boot/reset/power, no RADIO/
MODEM/EFS read or write, no DT/DTBO change, no flash, no reboot.

Classification: `PROVED_LIVE`, `CAPTURED_LIVE_OLDER`, `OFFLINE_TESTED`,
`SOURCE_ONLY`, `DOCUMENTED_ONLY`, `ASSUMPTION`, `UNVERIFIED`, `BLOCKED`.

---

## 0. Objective and result

Transition target required by the prompt:

```
ABI_VERIFIED + OFFLINE_BUILD_TESTED + FIRMWARE_IDENTITY_UNRESOLVED
→
FIRMWARE_COMPATIBILITY_PROVED + BOOTSTRAP_RUNTIME_READY + RECOVERY_VERIFIED + FIRST_BOOT_PROPOSAL_READY
```

**Result:** Each blocker was resolved to the maximum extent legally provable offline
and read-only. The outcome is **NOT_READY for physical CP boot** — exactly as the
evidence demands — but **READY_FOR_OWNER_REVIEW** on every gate that does not require
the owner's proprietary artifact or the future authorized physical trial.

Final gate matrix (full detail in §10 of the proposal):

| Gate | Offline/read-only result |
|---|---|
| A — Firmware provenance | `STRUCTURALLY_VALID_PROVENANCE_UNKNOWN` (blocker = missing original `.tar.md5` + `CL/QB` stamp mismatch) |
| B — Kernel ABI | `PASS` (28-byte struct, ioctl set, enum order — re-verified this round) |
| C — Bootstrap implementation | `PARTIAL` → selected path = native Linux bootstrap (options A/B genuinely infeasible, source-proven) |
| D — Offline build/tests | `PASS` (43 offline tests re-run green) |
| E — Current recovery readiness | `PASS` (PROVED_LIVE this round: BOOT/DTB/DTBO/recovery hashes all match baseline) |
| F — Owner approval | `PENDING` (never requested, never granted) |

---

## 1. What each blocker actually resolved to

### Blocker A — Firmware identity & provenance → `STRUCTURALLY_VALID_PROVENANCE_UNKNOWN`

- Original archive `/Users/wicked/x/nuxel/SAMFW.COM_.../CP_..._tar.md5` still **absent**
  (re-confirmed; `find / -xdev -iname 'CP_G975F*'` empty, analyzer `ARCHIVE_MISSING`).
- Derived `modem.bin` (46,062,992 B, sha256 `1e4280d2…`) is structurally valid (ITOC
  BOOT/MAIN/VSS CRC32 pass, `SM-G975F_EUR_XX_EUR0`, DTK9 base) but:
  - `CL1535157/QB17435920` (image) ≠ `CL20034833/QB35905779` (`mobile.md` target).
  - Appended MBN metadata carries `NONEmrk`; signature region never decoded.
- **Live RADIO partition identity cannot be hashed** on this boot: `/dev/block` dir
  is absent, `/dev/disk/by-partlabel` empty, and no PIT/by-name map exists to safely
  identify the radio partition among `sda16..sda31`. Reading raw UFS by guessing is a
  boundary this round does NOT cross. → on-device RADIO identity remains `UNVERIFIED`.
- Verdict: **`STRUCTURALLY_VALID_PROVENANCE_UNKNOWN`** (a compatible DTK9-family,
  model-matched candidate whose signing/provenance is unproven and whose package
  stamp does not match the documented archive).

### Blocker B — Real compatible CBD execution path → native Linux bootstrap

Decision evidence (full detail in `S5000AP-03_5-CBD-RUNTIME-DECISION.md`):

- **Option A (stock Bionic cbd)** — INFEASIBLE natively. `readelf -d` on the owner
  blob shows NEEDED `liblog.so, libcutils.so, libc++.so, libc.so, libm.so, libdl.so`
  and interpreter `/system/bin/linker64` → all Android Bionic, absent on Nuxel's
  glibc/systemd rootfs. Also requires `u:r:cbd:s0` SELinux + `/mnt/vendor/efs`,
  `/mnt/vendor/cpefs` ext4 mounts + Android `vendor.cbd.*` properties.
- **Option B (cpboot_v3 rebuild)** — INFEASIBLE natively. `Android.bp` links
  `liblog, libcutils, libc (Bionic), libselinux`; relies on Android property system
  and `radio_device` SELinux label. No glibc rebuild path exists without porting the
  entire Android Bionic surface.
- **Option C (minimal native Linux bootstrap)** — SELECTED as the only executable
  path that does not introduce Android runtime into Nuxel. This requires deriving
  the exact S5000AP boot transaction from the pinned kernel UAPI (done in round 03)
  AND resolving the `-t` type-string question (below).

### Blocker C — Firmware source contract → resolved with a critical correction

Source-proven findings (cpboot_v3 @ `234b1387`, lineage-22.1):

1. `Container.cpp:100-125` — `-tss310` → `new BootDumpModap()` (`.cpp:413` `name =
   "ss310"`). **`ss310` is the Shannon 310 (ModAP/SIT) modem, NOT the S5000AP.**
2. Kernel taxonomy (`modem_variation.h/c`) confirms `SS310AP`, `S5000AP`, `S5100`
   are **three distinct modem controllers**. `CONFIG_UMTS_MODEM_S5000AP=y` selects
   `modem_ctrl_s5000ap.c`; `ss310ap` is driven by a different file.
3. Therefore the owner DTK9 `init.baseband.rc` invocation
   `-d -tss310 -bm -mm -P platform/13d60000.ufs/by-name/radio` carries a **type
   string that does not resolve to the S5000AP path** in any recovered source. This
   is either (a) a wrong transcription for "the S5000AP is not `ss310`", or (b) the
   DTK9 image predates the rename. Either way it is a **genuine open question** that
   no offline source resolves.
4. `-P` sets `cbd_args.cpn.path_bin = "/dev/block/<arg>"` → the stock cbd reads the
   **installed RADIO partition** (read-only block device) and streams it through
   `IOCTL_MODEM_XMIT_BOOT`. Confirmed source contract: image source = RADIO
   partition, transfer = XMIT_BOOT (kernel `shmem_xmit_boot` does `copy_from_user`,
   no file path open). **An extracted `.bin` is NOT equivalent to the RADIO source**
   until the installed RADIO contents are proven byte-identical to the derived
   `modem.bin` — which cannot be established on this boot (no partition map).

### Blocker D — Offline bootstrap implementation → dry-run complete; HW path gated

`nuxel-cpbootd` (round 03) remains a correct dry-run coordinator. It is NOT a
physical bootstrap and is NOT claimed as one. The HW-mutating path stays behind
`-DNUXEL_CPBOOTD_ENABLE_HW=1` + runtime `--really-boot`. All negative tests pass;
no automatic retry; no CP power-on at startup; exclusive `flock(LOCK_EX|LOCK_NB)`.

### Blocker E — Live safety & recovery → **PROVED_LIVE this round**

Device reachable at `10.11.12.99` (owner ZeroTier). Fresh read-only evidence:
- CP status = `OFFLINE (0)` via `nuxel-cp-status` (read-only ioctl), kernel log shows
  only `misc_open/misc_release` (no mutation).
- `sda12`(dtb)=`abc9d45d…`, `sda13`(dtbo)=`de3bc025…`, `sda14`(boot)=`1be1ded8…`,
  `sda15`(recovery)=`4cc71d62…` — **all four match the established baseline exactly.**
- Device tree **immutable fence VERIFIED live**: no DT/DTBO drift.
- Known-good host BOOT backups verified: `boot-0029-candidate.img` = `1be1ded8…`
  (matches live `sda14`), plus `boot-0028` (`760c0e44…`) and `boot-0020…` (`9805d519…`).
- systemd `running`, zero failed units, Wi-Fi/SSH/USB intact.

### Blocker F — First-boot proposal → produced (this round's key deliverable)

`reports/S5000AP-03_5-CP-FIRST-BOOT-PROPOSAL.md` — a complete, evidence-backed,
source-referenced execution manifest with explicit owner-authorization request.
It is **a proposal only**, never authorization, and is **NO-GO for physical trial**
until gates A (firmware provenance) and F (owner approval) close.

---

## 2. pwn-mobile → pwn-mob migration reconciliation

- Tracked `pwn-mobile/{00,01,AUDIT_REPORT}.md` are **byte-identical** to the
  untracked `pwn-mob/{00,01,AUDIT_REPORT}.md` (`cmp` clean).
- `pwn-mobile/NUXEL_S5000AP_MOBILE_RECOVERY_V1.zip` was deleted from the worktree;
  a copy is preserved at `~/.Trash/NUXEL_S5000AP_MOBILE_RECOVERY_V1.zip` (round 02),
  and `pwn-mob/` gained NEW prompt files (02–09) + `FILE_MANIFEST.json` + `README.md`
  not present in the old `pwn-mobile/`.
- **Recommendation:** the migration is safe to commit as a rename+addition, but this
  round does NOT stage it (the prompt pack is owner input; committing it would mix
  owner provenance with my engineering changes). Left as-is, documented.

---

## 3. What was NOT done (and why)

- **No CP boot/reset/power-on.** No `IOCTL_MODEM_ON/OFF/RESET/BOOT_*/XMIT_BOOT/
  SECURITY_REQ/DL_START` issued.
- **No RADIO/MODEM/CP/EFS/EFSG/SEC_EFS/NV partition read or write.** The radio
  partition is not even addressable on this boot without unsafe guessing.
- **No DT/DTBO/DTS/DTC/overlay/fdtput/repack; no kernel config/patch.**
- **No signature strip, TEE bypass, offset patch, or fabricated verification.**
- **No firmware/`cbd` blob committed or redistributed.**
- **No owner approval requested for anything beyond the written proposal.**

---

## 4. Final verdict

`**NOT_READY**` for physical CP execution — unambiguous and honest closed-loop of
gates A (firmware provenance) and F (owner approval). `**READY_FOR_OWNER_REVIEW**`
for the proposal itself, since B–E are satisfied and a complete, reviewable proposal
exists. The open items below are the only remaining blockers to Prompt 04.

**Remaining blockers (exact, minimal, itemized):**

1. **Provenance of the CP image** — provide the original `.tar.md5` at the exact
   `mobile.md` path, OR explicitly confirm the derived
   `/Users/wicked/.local/share/nuxel-s5000ap/G975FXXS9DTK9-CP-20261117/{modem.bin.lz4,
   modem_debug.bin.lz4}` are authoritative. Also resolve the `CL1535157/17435920`
   vs `CL20034833/35905779` stamp mismatch. (owner input, no device access)
2. **`-t` modem type string for the S5000AP** — the recovered stock cbd uses
   `-tss310`, which source-proven maps to Shannon 310 (ModAP/SIT), NOT the S5000AP
   (SIPC). The correct S5000AP type string is not in any recovered source. (owner
   input: the real DTK9 vendor runtime, or a bounded live trace on an authorized
   device — device access)
3. **Installed RADIO partition identity** — cannot be read on the current boot
   (no `/dev/block/*`, no by-name map, no PIT). Requires either a TWRP-side
   authorized read or a safe recovery-context partition map to correlate the derived
   `modem.bin` with the installed radio image. (physical device access)

These are genuine authorization boundaries. None is bypassed here.
