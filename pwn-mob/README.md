# Nuxel S10+ S5000AP Mobile Recovery — Evidence-Based Prompt Pack v1

**Source audit:** supplied `nuxel-ds-ssp (1)(3).zip` snapshot, examined 2026-11-22. **No live handset access was available to the auditor.** The user requested `pwn/mobile*.md`, but the snapshot contains none; use repository-root `mobile.md` and `hw/NUXEL_06_S5000AP_CELLULAR_STANDALONE.md`. The report `reports/S5000AP-RADIO-ENDGAME.md`, `packs/mobile/` stage-zero tool pack, original CP firmware archive, Git metadata and full external kernel checkout are **NOT** present in this ZIP. They may exist on the owner's actual host: verify rather than assume.

## How to run

1. Give DeepSeek V4 Pro Thinking **`00_MASTER_SAFETY_AND_TRUTH.md` + `01_LIVE_RECONCILIATION.md`**. Keep `00` as the standing contract in **every subsequent round**, not just the first. Its job is a live baseline, not firmware flashing.
2. Give **`02_CP_FIRMWARE_VALIDATION.md`** to Thinking and delegate bounded extraction, hash validation and compatibility checks to Flash as suggested therein.
3. Give **`03_CBD_ABI_AND_OFFLINE_BUILD.md`** to Thinking; delegate deterministic builds, lint and tests to Flash. This is the most important programming phase.
4. Give **`04_CP_BOOT_CONTROLLED_TRIAL.md`** to Thinking when the offline prerequisites are satisfied. This phase requires explicit authorization for the **specific CP power/boot trial**. The standing TWRP recovery permission is not blanket permission to modify radio/secure partitions.
5. Once CP is genuinely online, run **`05_RFS_SIPC_RADIOD.md`**, then **`06_SIM_LTE_MODEMMANAGER.md`**. Run these serially: do not create an MM plugin before proving CP/SIPC.
6. After end-to-end LTE data, use **`07_SMS_VOICE_IMS_UI.md`**. Voice and IMS are *separate* acceptance gates.
7. Finally use **`08_REGRESSION_AND_HANDOFF.md`**. If any boot flash is genuinely needed, read **`09_TWRP_A_ONLY_RECOVERY_AGREEMENT.md`** *before* that work, not after a failure.

**Start recommendation:** Rounds 1–3 should be essentially zero DT/DTBO changes and preferably **zero BOOT flashes**. There is no evidence a DT rewrite is required for modem recovery. Use isolated Linux userspace integration first. Successful mobile data is **not** proven by the archive: present S5000AP host layer + CP `OFFLINE` as last reported. Audit-based estimates: **~90% AP-side kernel infrastructure; ~25% route to independently verified LTE data; 0% demonstrated physical end-to-end cellular function.** Percentages are subjective planning indicators, not measurements.

## Files

- `AUDIT_REPORT.md` — findings, source distinctions, component matrix, code concerns, milestones, realistic effort.
- `00_MASTER_SAFETY_AND_TRUTH.md` — required guardrails, source classification and go/no-go rules.
- `01_LIVE_RECONCILIATION.md` — audit the *actual* live worktree and phone; correct misleading diagnostic gates.
- `02_CP_FIRMWARE_VALIDATION.md` — validate exact Samsung G975F CP archive offline only.
- `03_CBD_ABI_AND_OFFLINE_BUILD.md` — pinned kernel UAPI, matching Samsung cbd, reproducible host-build and tests.
- `04_CP_BOOT_CONTROLLED_TRIAL.md` — one fully reviewed, bounded, authorized CP boot attempt with real state evidence.
- `05_RFS_SIPC_RADIOD.md` — minimal protocol stack, security, verifiable CP request/response.
- `06_SIM_LTE_MODEMMANAGER.md` — SIM, network registration, APN and real LTE bearer through NetworkManager.
- `07_SMS_VOICE_IMS_UI.md` — strictly independent SMS, calling, IMS and UI gates.
- `08_REGRESSION_AND_HANDOFF.md` — repeatability, CI/tests, artifacts, truthful completion.
- `09_TWRP_A_ONLY_RECOVERY_AGREEMENT.md` — explicit your-TWRP agreement, DTB/DTBO freeze, bounded retry + rollback rules.

## Current source pointers

- `mobile.md` — most recent supplied CP-acquired mission; says `CP OFFLINE (0)` and `ModemManager 1.24.2` discovers no modem.
- `docs/Samsung S5000AP - Exynos 9820 Native Linux Modem Bring-up for Nuxel.md` — 1169-line architecture analysis, pinned kernel source, read-only status code *described*, full CP/RFS/SIPC pathway.
- `docs/pwnage-89000/evidence/20261107T151308Z/baseline/journal/full-boot.txt` — actual November 7 modem probe and rmnet creation logs.
- `docs/beta-finalization/live/evidence/pwnage-51000/kernel/running.config` — built-in modem driver flags.
- `tools/s10plus/a33/nuxel-modem-diag.sh` + `configs/nuxel/modem/modem.json` — read-only diagnostic, presently models wrong first blocker.
- `boot/s10plus/flash.sh` — legacy flash helper; **not** to run blindly. It permits arbitrary `--rootfs-partition` destinations and has a denylist that differs from modem policy.
- `docs/s10plus-autonomous-boot-repair/A27-BOOT-FLASH-RECEIPT.md` — historical example of BOOT-only, hashed readback and rollback (not proof backup still exists on current host).

## Provenance / external candidates (pin before porting)

- Samsung kernel vendor source: `https://github.com/Linux4/android_kernel_samsung_exynos9820` historical pinned revision `f7194c1d15eded1c2a1a4dc63825b26103435cc0` (verify it actually matches live config before modifying anything).
- Exynos9820 LineageOS device config: `https://github.com/LineageOS/android_device_samsung_exynos9820-common`; it configures `cbd` with `protocol=sipc` and `use_legacy_sipc_ioctl=true` on the checked branch. Source is *candidate*, not established binary compatibility.
- Samsung cpboot source: `https://github.com/LineageOS/android_hardware_samsung_slsi-linaro_exynos` path `cpboot_v3`.

**Not allowed:** speculative DT edits; fake modem enumeration, blind firmware-section offsets, secure boot bypass, EFS/NV/IMEI changes, CP/modem partition writes, unconditional boot retries, mixing Pixel/Exynos9825 UAPI into S5000AP, or success claims from simulated traffic.
