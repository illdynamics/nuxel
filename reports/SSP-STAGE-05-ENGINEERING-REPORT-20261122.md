# SSP Stage-05 — First-Light Engineering Report (2026-11-22)

**Generated:** 2026-11-22T18:10:00+01:00 (Europe/Amsterdam)
**Agent:** DeepSeek-V4-Pro-Thinking (Stage-05 session)
**Device:** SM-G975F (beyond2lte), serial R58M75KDB2X
**Session outcome:** `BOOT_NUXEL=PASS`; SSP feature = `BLOCKED` (MCU silent; firmware-download state machine deployed but physical ROM response unresolved)

---

## 1. Executive summary

The handset started this session in a TWRP recovery session. It was booted into
normal Nuxel (verified healthy), and the critical rollback + partition-mapping
gates were closed with fresh dual-endpoint evidence. **No BOOT flash was
performed and none is justified**: the running kernel `4.14.253-gf7194c1d15ed-dirty`
already carries the complete SSP/BBD userspace passthrough (0020+0023), so the
correct Stage-05 approach is a **software-only bounded MCU first-light trial**
through existing nodes, not a reflash.

The software-only trial is currently **BLOCKED** on the unresolved physical
root cause (`mcu_test=NG, rx=0`): the BCM47752 RAM firmware must be downloaded
over the BBD transport *before* the WHOAMI handshake, and although
`nuxel_bbd_flash --flash` implements the full download state machine, the MCU
has historically returned `0xffffffff` / zero RX. This is an unresolved
electrical/protocol/cold-start matter, not a build or flash problem.

## 2. Final evidence table (timestamped, independent PASS/FAIL/BLOCKED)

| Gate | Status | Evidence location |
|---|---|---|
| PREVIOUS_STAGE04_FAILS_RESOLVED | PASS | Historical `SSP-CANDIDATE-PREFLIGHT.json` (NO_FLASH) preserved; Stage-04_5 `NO_FLASH_NEEDED` receipt + corrected packer/build-script/source-auditor/gate-tool |
| SOFTWARE_ONLY_PATH_REVIEWED | PASS | Running kernel exposes `/dev/ttyBCM`(10,91), `/dev/bbd_sensor`(236,1)/`control`(236,2)/`patch`(236,3), `nuxel_bringup` sysfs; kallsyms shows `nuxel_ssp_bringup_hw`, `nuxel_ssp_register_data`, `bbd_nuxel_peer_*`, `nuxel_ssp_bcm_diag` (36 nuxel symbols) |
| CLEAN_PINNED_KERNEL | N/A (software-only) | No local kernel checkout; no kernel change justified |
| PATCHES_EXACT | PASS | All 4 patch SHA-256 verified (0020/0023/0025/0027) per `SSP-CANDIDATE-PREFLIGHT-REVALIDATED.json` |
| FULL_KERNEL_IMAGE_BUILT | N/A (software-only) | No build needed; kernel already has passthrough |
| BOOT_CANDIDATE_VALID | N/A (software-only) | No candidate; no flash justified |
| RAMDISK_UNCHANGED | PASS | Live sda14 boot hash unchanged (`0e6aa34c...`); ramdisk LZMA at 45,852,672 |
| NO_APPENDED_FDT | PASS | FDT magic 0xD00DFEED count = 0 in full 57,671,680-byte boot partition |
| EXTERNAL_DTB_UNCHANGED | PASS | sda12 `abc9d45d...` fresh (TWRP + live) == Stage-01 |
| EXTERNAL_DTBO_UNCHANGED | PASS | sda13 `de3bc025...` fresh (TWRP + live) == Stage-01 |
| RECOVERY_UNCHANGED | PASS | sda15 `4cc71d62...` fresh (TWRP + live) == Stage-01 |
| ROLLBACK_HOST_VERIFIED | PASS | 2 host seeds (`/tmp/nuxel-ssp-preflight/boot-sda14-fresh.img`, `/tmp/nuxel-ssp-baseline/boot-sda14.img`), both 57,671,680 B, SHA `0e6aa34c...` |
| ROLLBACK_TWRP_VERIFIED | PASS | TWRP copy `/cache/nuxel-ssp-rollback/boot-sda14-known-good.img` (sda28), 57,671,680 B, SHA `0e6aa34c...` — established this session |
| TWRP_PARTITION_MAP_VERIFIED | PASS | by-name: boot=sda14, dtb=sda12, dtbo=sda13, recovery=sda15, system=sda25, cache=sda28, userdata=sda31 |
| BOOT_READBACK_VERIFIED | N/A (no write) | No BOOT write performed; nothing to read back |
| BOOT_NUXEL | PASS | `uname 4.14.253-gf7194c1d15ed-dirty`, systemd=running, 0 failed units, SSH+Wayland healthy |
| ROM_REPLY_VALID | BLOCKED | `mcu_test=NG,NG,NG`, `rx=0`, `resetting=1` — no genuine ROM GetVersion reply |
| FW_RECORDS_COMPLETE | BLOCKED | Firmware download not verified physically; state machine present in `nuxel_bbd_flash.c` but hardware trial unresolved |
| APP_VERSION_VALID | BLOCKED | No app-level GetVersion; MCU silent |
| SSP_WHOAMI | BLOCKED | No WHOAMI response |
| ACCEL_STREAM | BLOCKED | raw_data = 0,0,0; no streaming |
| GYRO_STREAM | BLOCKED | raw_data = 0,0,0; no streaming |

## 3. What was actually done this session (truthful, ordered)

1. **Read** historical `SSP-CANDIDATE-PREFLIGHT.json` (NO_FLASH) and
   `SSP-CANDIDATE-PREFLIGHT-REVALIDATED.json` (NO_FLASH_NEEDED/software-only);
   both preserved unchanged.
2. **Detected device in TWRP** (`adb devices` = `R58M75KDB2X recovery`,
   recovery kernel `4.14.113-g55f042627`), SSH (10.11.12.99) down.
3. **Verified TWRP by-name mapping** (`/dev/block/platform/13d60000.ufs/by-name/*`):
   boot=sda14, dtb=sda12, dtbo=sda13, recovery=sda15, system=sda25, cache=sda28,
   userdata=sda31. Matched recorded Stage-01 mapping exactly.
4. **Fresh read-only hashes from TWRP** for dtb/dtbo/boot/recovery: all UNCHANGED
   vs Stage-01 (see §table). Boot donor SHA `0e6aa34c...` confirmed intact on-device.
5. **Established second TWRP-accessible rollback copy** at
   `/cache/nuxel-ssp-rollback/boot-sda14-known-good.img` (55 MiB, `dd bs=1M`,
   sync'd), SHA `0e6aa34c...` == live donor == host seeds. Immutable partition
   hashes staged alongside. This closes dual-endpoint rollback readiness.
6. **Issued normal reboot** (`adb reboot`; misc partition was all-zero, no
   recovery command pending). Device booted into normal Nuxel.
7. **Verified Nuxel health**: kernel `4.14.253-gf7194c1d15ed-dirty`,
   systemd=running, 0 failed units, `/dev/ttyBCM` + `/dev/bbd_*` nodes present,
   MCU identified `BCM47752KUB1G`.
8. **Re-confirmed live partition hashes** from normal Nuxel: all UNCHANGED.
9. **Re-ran all offline tests**: native C harness (PASS), orientation pytest
   (77 PASS), recovery unittest (14 PASS), boot-packer (9), kernel-source-audit
   (4), stage05-gate (3). All green.
10. **Ran `verify_stage05_gate.py`** against revalidated receipt → `NO_FLASH`
    (correct: it's a software-only receipt; the flash-oriented tool fail-closed).

## 4. Truthful SSP-feature status

The SSD feature remains **BLOCKED**. The MCU reports `mcu_test=NG,NG,NG`,
`resetting=1`, `rx=0`. The historical root-cause analysis (pwn/ssp4.md,
pwn-ssp/99_SSP_DEEP_AUDIT.md) is that the BCM47752 RAM firmware patch must be
downloaded over BBD *before* WHOAMI, and the vendor `lhd` daemon normally does
this. `nuxel_bbd_flash.c` implements the state machine (autobaud 36×0x80,
GetVersion reliable RPC, 479×F1 MemoryWrite records, app-start, post-download
GetVersion) and gates device I/O behind `--flash`, but prior hardware trials
still read `0xffffffff` / zero RX. Cold power-on timing, SPI electrical state,
and 32-vs-36-byte autobaud reconciliation remain unresolved hypotheses.

**No genuine ROM response, app version, WHOAMI, accelerometer or gyroscope
streaming was observed, and none is claimed.**

## 5. Decision & next action

- **BOOT_NUXEL = PASS** — safe normal boot verified (recovery success).
- **SSP feature = BLOCKED** — the MCU is silent; physically-proven first light
  requires resolving the `rx=0` root cause and/or a separately reviewed,
  bounded firmware-download trial. This is NOT a flash problem.
- **No BOOT flash performed or authorized in this session.**
- Next concrete engineering item: source-verify and (only under separate,
  bounded owner authorization) trial the `nuxel_bbd_flash --flash` firmware
  download path with full instrumentation (SPI mode/CS/CS-duration, IRQ counts,
  runtime-PM, regulator consumers), reconciling the 32-vs-36 autobaud and
  cold-start timing hypotheses. Do NOT force orientation values; Stage 07
  handles the sideways-phone test.

## 6. Provenance / artifacts (no candidate built)

- Historical `SSP-CANDIDATE-PREFLIGHT.json` = NO_FLASH (unchanged).
- `SSP-CANDIDATE-PREFLIGHT-REVALIDATED.json` = NO_FLASH_NEEDED / software-only.
- This report + `SSP-STAGE-05-TWRP-LIVE-EVIDENCE-20261122.md`.
- Rollback: 2 host seeds + 1 TWRP copy, all SHA `0e6aa34c...`.
- No kernel Image, candidate BOOT, or firmware was produced or written.
