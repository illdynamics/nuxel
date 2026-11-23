# Nuxel S5000AP Mobile Networking — ZIP Repository Audit

**Date:** 2026-11-23  
**Input:** `nuxel-cs-mob.zip` (~367 MiB compressed, 21,359 ZIP entries, ~797 MiB uncompressed)  
**Assessment:** Source/report evidence in ZIP, plus a limited local compile/test review; no live handset connection available to this reviewer.

## Executive verdict

**NOT READY for Stage 04 physical CP boot.** Significant kernel/transport groundwork and recovery preparation is complete, but no complete, correct and verified physical CP bootstrap implementation is present. `nuxel-cpbootd.c` is explicitly a dry-run coordinator, and its optional hardware branch is not safe/complete. Installed RADIO provenance is partly characterized but not independently authenticated; original DTK9 archive is missing, and DTK9 is *not* the installed EFUJ2 image. The last measured physical CP state in the supplied reports was `OFFLINE (0)`; LTE data, SMS, voice, and IMS/VoLTE have not been demonstrated.

**Estimates — engineering judgment, NOT measured KPIs:** pre-04 preparation ~55–60%; end-to-end usable LTE ~20–25%; complete LTE+SMS+voice+IMS package ~10–15%. Actual real-world mobile data working: **0% verified**, not "0% of implementation". A strict readiness gate remains NO-GO.

## Important new evidence (03.6)

1. The installed RADIO partition is reported identified by live read-only `blkid` as **`/dev/sda16`, PARTLABEL `radio`, 52,428,800 B**, firmware family **`G975FXXSEFUJ2`** (2021-10-20), metadata `SM-G975F_EUR_XX_EUR0`. Read-only full-partition SHA256 reported `9ffa1426a4ef7d1187779a14f22ec4b8cb4c2ab473b6626304a77030d9966fc7`. This is **not** the derived DTK9 firmware image.
2. Derived `modem.bin` is DTK9, 46,062,992 B, SHA256 `1e4280d26de704281c01ddf59407fbfdfb714d3f87a55b780f6f74d1ab0e7881`. Its BOOT/MAIN/VSS CRC32 and LZ4 consistency passed, but source archive and independent authentication were not established.
3. `-t ss310` is **reported resolved** in `S5000AP-03_6-CBD-TYPE-STRING-VERIFICATION.md` for `cpboot_v3` **compiled with `protocol=sipc` and legacy ioctl compatibility**. The earlier 03.5 and 04 statements that `ss310` is definitely wrong are superseded. The associated Lineage `BoardConfigCommon.mk` flags exist in public source (independently checked).
4. Kernel UAPI checks: `struct modem_firmware` **28 B**, `modem_sec_req` **16 B**, SIPC5 header max struct **6 B**, Linux `_IO('o',N)` numeric ioctl contract. Kernel pin `f7194c1d15eded1c2a1a4dc63825b26103435cc0`, Nuxel commit in the reports `45b9097f3c989347ebc8572d733ca4e3a72f63e4`. The kernel checkout itself is **not included in the ZIP**, so the historical source-side cross-check cannot be reproduced from the archive alone.
5. The latest supplied recovery receipt reports BOOT `1be1ded89f9e04a6a2ca0d32d9273bd363c2e200f478ab10213ea3927674a599`, DTB `abc9d45d3745866346fd94c7c04028cc2c62ade4dd274b400dbbfec0c2ef4780`, DTBO `de3bc02526c66647992a744608fdf61548823866e822a7400619d74126095c23`, RECOVERY `4cc71d6277e020cdec729b85934cfb6111e9abee8db2fbcc344aad3173335d87`; Wi-Fi/SSH operational and CP OFFLINE. These are **reported historical live observations**, not new measurements by this audit.

## Readiness and capability matrix

| Layer | Evidence | Assessment |
| --- | --- | --- |
| Physical board / modem driver probed | Reports with live read-only probe; `/dev/umts_*`, `rmnet0..7` | **Strong / previously live-verified** |
| Shared memory, controller, kernel ABI | Source and compiler reports, UAPI C header | **Strong source/compile evidence** |
| Read-only CP status diagnostic | CP `OFFLINE(0)` recorded multiple times | **Previously live verified; CP remains OFFLINE** |
| Firmware container analysis | Host analyzer, 22 tests | **Strong structural checks for DTK9 candidate** |
| Installed RADIO source mapping | `blkid` + bounded read-only metadata and hashes in report | **Partition and model identity verified by reported live reads** |
| Installed RADIO full per-entry structural validation | TOC magic and strings recorded; full entry CRC not reported | **Incomplete** |
| Provenance / trusted OEM source | Original DTK9 archive missing; EFUJ2 source archive not supplied | **Open; must not claim signature proof** |
| Correct legacy CBD type | `ss310` resolved under SIPC/legacy flags | **Source-supported** |
| Running stock CBD on glibc | Bionic-linked proprietary binary, different loader/dependencies | **Not available as-is** |
| Source-faithful native CBD/bootstrap | Dry-run-only C implementation; HW stages missing | **Critical NO-GO** |
| Fail-safe hardware execution | Present code does not fully execute/validate stages | **Critical NO-GO** |
| BOOT / DTB / DTBO / TWRP rollback | Historical hashes and backups documented | **Strong, refresh just before trial** |
| CP physically ONLINE | Never reached | **0 live proof** |
| SIPC response, RFS | Source-only future stage 05, no reports/implementation in ZIP | **Not live tested** |
| SIM / network registration | CP offline | **Blocked** |
| LTE data and rmnet Internet | rmnet down, no bearer | **Blocked** |
| SMS / voice / IMS/VoLTE | No CP/SIM/radio backend | **Blocked** |

## Code-level critical findings

Inspection of `tools/s10plus/s5000ap-uapi/nuxel-cpbootd.c` reveals:

- `#ifdef NUXEL_CPBOOTD_ENABLE_HW` enables the hardware branch **even if the macro is defined to 0**. Use a value-aware compile-time fence.
- The hardware `execute_boot_stage` dispatch only issues BOOT_ON, DL_START and BOOT_DONE. `IOCTL_MODEM_XMIT_BOOT` and `IOCTL_SECURITY_REQ` explicitly refuse. POWER_ON, BOOT_OFF and pure SIPC download **fall through `default: return 0` without work**.
- The status-probe and online-verify stages also effectively return 0 instead of interrogating and checking the real CP status. No end-to-end ONLINE verification.
- On abort the function goes to `cleanup:` and ultimately **returns process status 0**. This could falsely signal success to a supervisor.
- `--deadline-ms` uses unchecked `atol()` and checks elapsed time only **after** the call returns. It does not enforce a real interruptible deadline for a stalled ioctl/IPC operation.
- The hardware branch doesn't read firmware, validate EFUJ2 ITOC, stream MAIN frames or implement secure request arguments. There is no implemented source-backed boot transaction.
- `flock` on the opened character device alone does not demonstrate mutual exclusion with unrelated CBD processes, which may not participate in that advisory lock. A separate well-defined process lock and competing-process check are needed.
- `--node` allows arbitrary paths without strict identity validation in the HW branch. The real operation requires verified character device major/minor and device identity.
- The plan's BOOT/MAIN lengths (7,744 and 39,895,408 B) are from the **DTK9** candidate, not parsed and verified from **EFUJ2**. Reusing them for EFUJ2 would be unsound.
- The 03.6 CBD type-string report and older proposal give different abbreviated boot-sequence descriptions. Reconstruct one authoritative operation-by-operation call graph from pinned source before any hardware-enable build.

These are concrete **pre-04 blockers**, independent of missing original archive paperwork.

## Local tests performed against ZIP-extracted source

- `tools/s10plus/tests/test-cp-firmware-identity-offline.py`: **22/22 passed** (synthetic fixtures only).
- `python3 -m pytest tools/s10plus/s5000ap-uapi/tests -q`: **15 passed, 6 failed** in this review environment. Five failures arise because the actual kernel source under `kernel/s10plus/.build/src.polluted.case-insensitive/drivers/misc/modem_v1/` is not bundled in the archive. One failure is a **real portability defect**: `test_s5000ap_uapi.py` invokes `pytest.skip` but imports `pytest` only inside `if __name__ == '__main__'`, resulting in `NameError` when AArch64 GCC is unavailable. The reported 21/21 result on the original Mac may still be valid with its toolchain and kernel checkout; it is **not reproducible from ZIP alone**.
- `gcc -O2 -Wall -Wextra -Werror` successfully compiled dry-run `nuxel-cpbootd.c` on local Linux. The optional `-DNUXEL_CPBOOTD_ENABLE_HW=1` branch also compiles here, but was **not executed**, and successful compilation is NOT a functionality/safety pass.

Additional test code quality: `test_kernel_header_crosscheck.py` contains duplicate definitions of `kernel_ioctl_values` and `test_no_extra_dangerous_ioctl_injected` (later definitions shadow earlier ones); clean these up. There is no full hardware branch end-to-end transcript test against matching Samsung bootloader source.

## Documentation and policy drift

- Root `mobile.md` says the exact DTK9 `.tar.md5` **has been found**, but 02/03.6 reports say it was absent after host searches; supersede the stale assertion.
- 03.5 proposal's 03.6 revision header correctly switches to installed EFUJ2 read-only source, but older body sections still cite DTK9 hashes, BOOT/MAIN lengths, old prerequisites and obsolete `RADIO equivalence` requirements. **Write a completely fresh immutable Stage 04 proposal** based on EFUJ2, not a header patch.
- `reports/S5000AP-04-CP-BOOT-LIVE.md` (02:57Z) predates 03.6 corrections, so its `-t` and installed-RADIO unresolved items are obsolete; its **NO-GO/no-boot** facts remain valid.
- `configs/nuxel/modem/modem.json` places RADIO in `protected_partitions.never_read_or_write`, while stock source contract and 03.6 live tests read RADIO **read-only**. Reconcile policy to distinguish allowed scoped read-only identification/source input from forbidden writes; do not weaken write protection.
- `S5000AP-03_6-CL-QB-IDENTITY-ANALYSIS.md` labels a mismatch "explained and compatible" but original DTK9 archive is absent. Component-namespace differences are plausible; exact DTK9 image-to-package lineage remains **unproven**. Do not conflate model compatibility with authenticated provenance.
- The archive contains no vendor stock CBD binary, no firmware blob, and no full kernel checkout. Historical reports cite artifacts in owner-private locations; agent must verify them **on the original host/handset**.
- No Stage 05 `S5000AP-05-RFS-SIPC.md` report or implemented `nuxel-radiod` was found among targeted ZIP paths; do not claim live SIPC/RFS integration.

## Recommended stage 04 clearance criteria

1. **Source selection:** Explicitly use currently installed **EFUJ2 RADIO** as a *read-only input*, unless a different exact provenance-verified source is justified. Do not require DTK9 archive for a plan that doesn't use DTK9. Resolve source path, full size, firmware ITOC, section-specific offsets/sizes/checks and hash from **EFUJ2**, not DTK9.
2. **Authenticity:** Independently verify obtainable OEM package/chain-of-custody information; distinguish OS-side structural checks from firmware's **TEE/device-side acceptance**, which can only be known after a genuine trial in some circumstances. Never bypass secure boot or invent authentication evidence.
3. **Bootstrap:** Build/port a real source-backed SIPC/legacy `cbd`-compatible transaction in glibc, minimally changing dependencies while preserving protocol behavior. Prove stages including power/boot, transfers, security requests, handshake, boot completion and actual ONLINE status. Re-evaluate source-porting `cpboot_v3` instead of assuming full Android runtime is required solely because its Android.bp links Bionic libraries.
4. **Fail closed:** Real watchdog/deadline strategy, safe abort without reboot/reset loops, nonzero failure return, exclusive ownership, exact per-stage kernel state evidence, one-shot disabled-by-default service, no protected writes.
5. **Test hard:** Offline fake-device/kernel-protocol transcript comparisons, negative tests and fuzzing; AArch64 target build + dependency verification; validated unit tests with kernel source present or explicit skipped classification, no fake simulated successes.
6. **Recovery:** Refresh BOOT/DTB/DTBO/recovery hashes; confirm two host known-good backups, Wi-Fi/USB/TWRP and modem log redaction. No BOOT/DT changes should be needed.
7. **Authorization:** Existing request can cover **scoped read-only checks and reversible userspace dry-run staging** in preparation. It is not proof of an unknown future exact live CP execution plan. Present one concrete immutable manifest and ask the owner to explicitly approve that exact physical boot operation. Do not automatically execute Stage 04 during prep.

**Best model:** DeepSeek Pro Thinking as lead for protocol fidelity/security/architecture and GO/NO-GO; Flash Thinking for isolated extraction/tests/documentation; non-thinking only for mechanical, bounded edits after design is settled.

**Bottom line:** The best next round is **Prompt 03.7 / Stage 04 clearance**, not another generic firmware-archive hunt and not an immediate unsafe CP trial. The most important blocker is the incomplete native bootstrap, followed by EFUJ2-specific source validation and the accurate revised trial manifest.
