# Nuxel Galaxy S10+ Native Cellular (Samsung Shannon S5000AP) — Maximum Practical ZIP Audit

**Date:** 2026-11-22. **Input:** `nuxel-ds-ssp (1)(3).zip`; single top directory `nuxel-ds-ssp`, 20,860 ZIP entries, about 0.796 GB uncompressed. **Method:** extracted files, inspected prompt, hardware/technical docs, historical boot/config logs, modem diagnostic code, policies, tests, flash script and recovered source provenance; supplemental public LineageOS checks. This is a static/offline audit of an archive, not SSH access to the physical handset. **No handset was touched. No flashing or firmware transfer was attempted.**

## Executive verdict

**Kernel/AP-side infrastructure: ~90% complete as a stage. Verified end-to-end LTE data bring-up program: ~25% complete as an engineering estimate, with no actual LTE data milestone verified.** Cellular voice/SMS/IMS are also not demonstrated. Percentages are for planning and cannot substitute for physical acceptance. The effort is better positioned than a missing-kernel-driver port because the Samsung Exynos9820 `modem_v1` S5000AP probe has executed on real hardware, initialized shared memory and created radio transport interfaces. But CP bootstrap, secure-image acceptance, RFS/SIPC control services, SIM registration, bearer establishment and user-facing modem integration are still outstanding or at least not evidenced in this archive.

**Most important new input:** root `mobile.md` (latest supplied mission) says a matching TNL DTK9 CP archive on the owner's Mac was found, filenames `modem.bin.lz4` and `modem_debug.bin.lz4`; claims prior CP `OFFLINE (0)` and `ModemManager 1.24.2` no modem. The archive itself does not include the CP archive, hashes, source-built `cbd`, actual successful CP boot receipt, or `reports/S5000AP-RADIO-ENDGAME.md`. Therefore firmware is **ACQUIRED PER DOCUMENT / NOT INDEPENDENTLY VALIDATED FROM ZIP**, not verified signed, flashed or accepted.

## Critical precision about “latest prompts” and omitted paths

The user asked to inspect `./pwn/mobile#.md`. No file matching `pwn/mobile*.md` or similarly named `pwn/mobile*.md` is present. `pwn/` contains `ssp.md` through `ssp6.md`, camera intermediate artifacts and source research; `mobile.md` exists in repository root. `hw/NUXEL_06_S5000AP_CELLULAR_STANDALONE.md` is labeled prompt 6/6 with SSH instruction and a full requirements list. The ZIP **does not contain** `.git`, `reports/`, `packs/mobile/`, full `drivers/misc/modem_v1` source or the original CP archive. `mobile.md` cites last mobile commit `22dd6b3ab46dece28abfe83607d7cc64add76843`, but that commit is not verifiable without Git metadata. The requested host paths may exist on the user's live Mac; agent must inspect them before assuming they do not.

## Architectural history — what is already written versus newly needed

### Kernel (substantially already written upstream)

`docs/Samsung S5000AP - Exynos 9820 Native Linux Modem Bring-up for Nuxel.md` analyzes Samsung downstream Linux 4.14.253 `drivers/misc/modem_v1`, pinned historical upstream kernel SHA `f7194c1d15eded1c2a1a4dc63825b26103435cc0`, including S5000AP modem-control, SHMEM/SBD link, mailbox, CP state ioctls, SIPC5 transport, netdev packet I/O, RFS and boot interface. Running kernel evidence from `docs/beta-finalization/live/evidence/pwnage-51000/kernel/running.config` includes `CONFIG_SEC_SIPC_MODEM_IF=y` at line 1518, `CONFIG_SEC_MODEM_S5000AP=y` at 1519, `CONFIG_CP_DIT=y` at 1532, `CONFIG_CP_PKTPROC=y` at 1534, `CONFIG_LINK_DEVICE_SHMEM=y` at 1537, `CONFIG_UMTS_MODEM_S5000AP=y` at 1542, `CONFIG_CP_SECURE_BOOT=y` at 1546 and `CONFIG_CP_RAM_LOGGING=y` at 1548. An additional saved kernel config in `docs/beta-finalization/live/evidence/pwnage-usbnet-114000/kernel-config-before-scratch-build` independently agrees.

Real historical Nuxel logs from **2026-11-07**, `docs/pwnage-89000/evidence/20261107T151308Z/baseline/journal/full-boot.txt`, show `modem_if_parse_dt_pdata: DT parse complete!` at line 1206; `s5000ap_init_modemctl_device` at 1207; `create_modemctl_device: s5000ap is created!!!` at 1213; `shmem_create_link_device: MODEM:s5000ap LINK:shmem` at 1215; `shmem<->s5000ap: LINK_ATTR_SBD_IPC` at 1216; `packet log device create fail` at 1280; `modem_probe: s5000ap: shmem link created` at 1282; `umts_cass`, `umts_ipc0`, `umts_ipc1`, `umts_rfs0`, diagnostic and other endpoints created between 1283–1304; `rmnet0..7` created at 1292–1299; `BOOT device = umts_boot0` at 1302; probe complete at 1309. `shm_ipc shmem: CP memory map verification: PASS!` at 1186 verifies kernel's own map checks, NOT CP image authenticity or modem registration. The `packet log device create fail` message merits classification but does not stop subsequent link/netdev creation.

**Conclusion:** native kernel driver and DT description exist and already probe. The modem work should be primarily userspace. Do NOT rewrite `modem_v1` or modify device tree to address missing CP userspace boot.

### Previously written Nuxel-specific work

1. `tools/s10plus/a33/nuxel-modem-diag.sh` — an honest-ish diagnostic exposing candidate CP nodes, rmnet interfaces, ModemManager plugin status, SIM information if sourced, fake-root test mode and redaction. No CP loader is implemented. Shell syntax check in archive environment passed; full separate offline test harness did not complete in a short bounded audit run, so do not claim all tests passed now.
2. `tools/s10plus/a33/tests/hw-subsystems/test-modem-diag.py` — fixture tests for absent/transport-only/no-SIM/SIM, redaction, AT allowlist and protective policy. Tests model a **simulated** ready state, not live cellular function.
3. `configs/nuxel/modem/modem.json` — read-only diagnostic policy: plugin glob `*shannon*`/`*s5000ap*`, SIM state source, operator/signal reporting and protected-partition denylist; generic Samsung AT plugin deliberately excluded.
4. `configs/s10plus/modem/README.md` and `configs/nuxel/modem/README.md` — older conservative descriptions: Wi-Fi-only; no voice/SMS/data; suggest missing MM plugin. These are outdated as first-blocker descriptions because later project research says CP boot still OFFLINE.
5. `docs/beta-finalization/release/DEVICE-CAPABILITY-MANIFEST.{json,md}` — historical `NEEDS_OWNER_TEST` for modem/SIM but evidence says `mmcli -L -> No modems were found`, rmnet and umts interface creation; no real SIM or data pass.
6. `docs/Samsung S5000AP - Exynos 9820 Native Linux Modem Bring-up for Nuxel.md` — deep architecture research and proposed read-only status-tool code. It references a separately generated stage-zero `nuxel-s5000ap-stage0.zip` that is **not part of this ZIP**. The document says it was host-tested only; do not invent on-phone execution.
7. `hw/NUXEL_06_S5000AP_CELLULAR_STANDALONE.md` and root `mobile.md` — mission and roadmap; plans are not implemented code.
8. `boot/s10plus/flash.sh`, `scripts/nuxel-adb-flash-pack` and boot-repair history — OS/BOOT deployment tooling, NOT evidence modem CP can load.
9. `services/nuxel-network/` deals with hotspot/Nuxel networking; `services/nuxel-bridge/src/api.py` routes diagnostic tool; no verified native S5000AP `cbd`, `nuxel-cpbootd`, `nuxel-radiod`, working SIM or MM plugin found in extracted tree.

### Firmware situation

`mobile.md` calls out host path `/Users/wicked/x/nuxel/SAMFW.COM_SM-G975F_TNL_G975FXXS9DTK9_fac/CP_G975FXXS9DTK9_CP17435927_CL20034833_QB35905779_REV01_user_low_ship.tar.md5`. It says archive members `modem.bin.lz4` and `modem_debug.bin.lz4`. The original archive is not attached, so one cannot independently verify integrity, matching hardware, Samsung signature acceptance, image sections or MD5 trailer. In `firmware/s10plus/manifest.yml` the `modem_dsp` block describes `vendor/firmware/calliope*` as modem DSP (lines 351–375) but the architecture report specifically warns those are **ABOX/audio Calliope firmware**, not the cellular CP image. This should be corrected rather than used for cellular download.

### Samsung `cbd` is the real next priority

Source research points to LineageOS `android_hardware_samsung_slsi-linaro_exynos/cpboot_v3` and `android_device_samsung_exynos9820-common`: public checked device config sets `cbd` `protocol=sipc`, `use_legacy_sipc_ioctl=true`. Compatible source still needs pinned commit, target-specific old Android 10/Exynos9820 ABI matching and Bionic runtime or shim. The research document lists kernel boot/ioctl services (`IOCTL_MODEM_ON`, `OFF`, `RESET`, `BOOT_ON`, `BOOT_OFF`, `BOOT_DONE`, `STATUS`, `DL_START`, `FW_UPDATE`, `XMIT_BOOT`, `GET_SHMEM_INFO`) and CP state enumeration. The documented read-only `IOCTL_MODEM_STATUS _IO('o',0x27)` must be rechecked against exact running headers; no guessed section offsets. Do not transplant Pixel/tinycbd or Exynos9825 instructions unverified.

### Remaining transport and user-space layers

Even with CP ONLINE, RFS needed for legitimate modem state and SIPC5 control remain to be understood for S5000AP. Without actual CP IPC replies, no SIM status, operator registration, PDP context or bearer can work. A specific `nuxel-radiod` (or compatible isolated vendor RIL) should expose real radio state. Only after this can ModemManager 1.24.2—or the currently installed MM version—use a genuine native backend/adapter and NetworkManager bring up a verifiable data bearer. SMS, two-way call audio and IMS/VoLTE need independent implementation and carrier verification. IMS/VoLTE may remain a significant external/vendor challenge.

## Completion breakdown (subjective estimates and confidence)

| Subsystem | Approximate maturity | Hard evidence / missing gate |
|---|---:|---|
| Samsung S5000AP kernel controller and registration | 90–95% | real probe, nodes, reserved RAM; packet-log issue unclassified |
| SHMEM/SBD kernel transport | 75–85% | initialization verified; actual CP traffic absent |
| CP firmware procurement | 60% *acquisition only* | reported matching CP file; missing file/hashes in ZIP; security compatibility not tested |
| CP boot userspace (`cbd`) | 10–20% | source pointers and architecture plan; compatible build and live CP boot unverified |
| RFS service | 5–10% | kernel node exists; no verified userspace protocol implementation |
| SIPC5 radio-control backend | 10–15% | kernel framing exists; no real CP control transaction |
| SIM and network registration | 0–5% | no actual SIM state or registration result |
| LTE bearer, NetworkManager and carrier traffic | 0–5% | rmnet created but DOWN; no PDP, IP, route, DNS/HTTPS proof |
| ModemManager Shannon backend | 0–5% | no actual modem in `mmcli -L` |
| SMS / calls / IMS | 0–5% each | physical and vendor-stack gates unmet |

**Roll-up estimate ~25%** to reliable mobile data is **nonlinear**: working low-level kernel infrastructure reduces reverse-engineering risk, but not the hardest remaining signed firmware/loader/RIL barriers. Actual *end-to-end proven mobile-data capability* is **0%** as of this evidence. The 25% is progress of prerequisites and planning, NOT 25% cellular functionality. Estimates are intentionally not additive across partial source paths.

## Highest-priority source concerns, not hardware evidence

1. **Wrong first blocker in diagnostic:** `tools/s10plus/a33/nuxel-modem-diag.sh` `verdict()` first checks `-z "$PLUGIN"` and returns `BLOCKED_FIRMWARE|modemmanager_plugin` even with CP host transport but no CP-online evidence; root `mobile.md` says CP OFFLINE. Reorder pipeline: actual CP status/firmware/cbd first; MM is later. Do not use plugin file names as functional proof.
2. **SIM false-positive risk:** `enumerate()` calls `mmcli -L` and sets SIM_STATE="present" merely when any `/Modem/` object appears, but a detected modem is not a SIM-ready modem. JSON source file can also go stale, and string grep treats any state without `'present':true` as 'absent'. Correct into authenticated, timestamped SIM source; unknown≠absent.
3. **Policy mismatches:** `configs/nuxel/modem/modem.json` forbids `twrp`/`heimdall` for modem diagnostics, while owner permits TWRP BOOT recovery and repo's `boot/s10plus/flash.sh` provides such flashing. Keep prohibition on **radio/protected partitions**, document narrowly scoped BOOT-only restore permission.
4. **Potentially unsafe broad flash targets:** `boot/s10plus/flash.sh` accepts arbitrary `--rootfs-partition` and checks a denylist missing `modem`, `radio`, `dtbo` and `bootloader` (relative to modem policy). This script must not be trusted blindly for any trial. Prefer inspecting the separate proven flash pack's current logic, strict by-name map and per-image readback.
5. **Misleading stale firmware label:** `firmware/s10plus/manifest.yml` calls ABOX Calliope audio firmware a modem DSP image. Correct semantic labeling before any firmware decision.
6. **Unverified code artifacts:** research references downloadable stage-zero ZIP and local `packs/mobile`, but they were excluded from input archive; first agent should locate the owner's actual files rather than recreating or misclassifying them as already present.
7. **Old hardware smoke evidence:** `diagnostics/pwnage-91000/hardware/modem-status.txt` says CP nodes absent/`NOT_SUPPORTED_ON_DEVICE`, whereas 2026-11-07 real kernel log shows them created. This is either a different runtime/context or stale diagnostic; inspect timestamps and conditions instead of treating it as final live state.
8. **No guarantee of zero flash/DT risk:** technical guardrails can make DT mutation unnecessary, preserve hashes and provide a reliable BOOT rollback; they cannot logically guarantee no failure. A single A-only partition is especially unforgiving. Avoid flash entirely for loader/radiod source integration whenever possible.

## Roadmap and credible rounds

- **Round A / Thinking + 1–2 Flash:** source/live reconciliation, backup receipts, CP-status read-only tool, fix diagnostic state machine; no BOOT write.
- **Round B / Thinking + 2 Flash:** validate reported original CP archive and Samsung source revisions, pin Exynos9820 UAPI and `cbd` compile/build/runtime compatibility; no physical CP power.
- **Round C / Thinking + 1–3 Flash:** close boot ABI and signed image contract, build and stress-test exact `cbd`/shim. Then request owner authorization for one controlled CP boot trial.
- **Round D / Thinking / actual device:** one approved signed CP boot, actual ONLINE proof and durable logs. A true source/secure-boot barrier may stop the project here.
- **Rounds E–G / Thinking + Flash:** build/port RFS/SIPC radio backend, SIM/registration/PDP, exact MM/NetworkManager integration, carrier LTE proof and UI. These often take **more than a few rounds**, especially reverse-engineering opaque vendor services.
- **Later:** SMS, real voice and carrier IMS/VoLTE; do not budget these as 'just a couple prompts'.

**Realistic expectation:** A few DeepSeek Pro Thinking + Flash rounds could make substantial progress, possibly get the CP ONLINE *if* exact CBD/firmware compatibility is readily recoverable. Fully verified data connectivity is not responsibly predictable in just a few rounds; SMS/voice/IMS are significantly more complex. The best opportunity is to avoid kernel/DT rewrites altogether and focus on exactly matching Samsung's existing CP bootstrap followed by minimal proven native radio userspace.

## Hard acceptance criteria

**Minimum MOBILE DATA PASS:** correct firmware accepted and CP online; CP remains stable; genuine RFS/SIPC response; real SIM ready; real carrier registered; active PDP bearer; rmnet netdev bound to assigned IP, route and DNS; HTTPS using cellular route with Wi-Fi disabled but USB console accessible; verified counter increments, dis/reconnect, airplane mode, cold boot persistence, negative tests and privacy redaction. **SMS PASS:** actual bidirectional test; **CALL PASS:** consenting normal incoming/outgoing two-way audio; **IMS PASS:** real working carrier provisioned VoLTE/IMS, not just data. Distinguish data-only completeness from all-feature completeness.

## Recovery contract distilled

Preserve exact BOOT and embedded DTB hash. No DTB/DTBO changes required for modem. If unavoidable BOOT flash, preflight actual model/partition/known-good backups and independent hash readback. TWRP after reboot **means failure**, gather logs and restore/rebuild a distinct candidate rather than repeat unchanged image. No infinite loops. Restore original known-good if recovery becomes uncertain. Never touch modem/radio/EFS/NV/TEE/userdata. Successful return to Nuxel means independently verified running OS and services, not merely TWRP exit. See prompt 09 for reproducible agreement.

## Reference index

Within ZIP:
- `mobile.md` complete latest root prompt and CP candidate.
- `hw/NUXEL_06_S5000AP_CELLULAR_STANDALONE.md` earlier six-prompt mission.
- `docs/Samsung S5000AP - Exynos 9820 Native Linux Modem Bring-up for Nuxel.md` deep source research.
- `docs/pwnage-89000/evidence/20261107T151308Z/baseline/journal/full-boot.txt` historical proven modem probe.
- `docs/beta-finalization/live/evidence/pwnage-51000/kernel/running.config` kernel flags.
- `docs/beta-finalization/preflight/live/batch-3-audio-radio-power.out` mmcli no modems and rmnet DOWN.
- `diagnostics/pwnage-91000/hardware/modem-status.txt` contradictory older tool verdict.
- `tools/s10plus/a33/nuxel-modem-diag.sh`, `tools/s10plus/a33/tests/hw-subsystems/test-modem-diag.py` and `configs/nuxel/modem/modem.json`.
- `firmware/s10plus/manifest.yml` mislabeled Calliope section.
- `boot/s10plus/flash.sh`; `docs/s10plus-autonomous-boot-repair/A27-BOOT-FLASH-RECEIPT.md`.

External public leads to re-pin/check in implementation:
- `https://github.com/LineageOS/android_device_samsung_exynos9820-common/blob/lineage-23.2/BoardConfigCommon.mk`
- `https://github.com/LineageOS/android_device_samsung_exynos9820-common/blob/lineage-23.2/common.mk`
- `https://github.com/LineageOS/android_hardware_samsung_slsi-linaro_exynos`
- `https://github.com/Linux4/android_kernel_samsung_exynos9820`

No proprietary file or personally identifying radio data has been included in this pack.
