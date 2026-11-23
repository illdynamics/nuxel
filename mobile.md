# NUXEL S10+ — SHANNON S5000AP COMPLETE MOBILE RECOVERY

## PRIMARY MISSION

You are the lead Linux kernel, Samsung Exynos9820, Shannon modem, SIPC and cellular integration engineer working on the Nuxel operating system.

Your mission is to restore genuine, fully verified mobile networking on the Samsung Galaxy S10+ SM-G975F.

> **Correction (Prompt 03.6/03.7).** The earlier "CP archive has now been located" claim is
> superseded. The documented DTK9 `.tar.md5`
> `CP_G975FXXS9DTK9_CP17435927_CL20034833_QB35905779_REV01_user_low_ship.tar.md5`
> was **NOT present** in subsequent host searches (`find / -xdev -iname 'CP_G975F*'` → empty).
> What was recovered offline is a derived DTK9 `.lz4` pair (structurally valid, provenance
> UNKNOWN), and — decisively — the **installed RADIO partition is EFUJ2 (`G975FXXSEFUJ2`),
> not DTK9**. The selected read-only firmware source for Stage-04 is therefore the installed
> EFUJ2 RADIO at `/dev/sda16` (PARTLABEL `radio`), not the DTK9 archive. Do not treat the
> DTK9 archive as "found"; do not block the EFUJ2 path on the missing DTK9 archive.
> **Do not stop at another missing-firmware report.**

Continue through all independently executable research, implementation, compilation and offline verification work. Advance from one validated engineering milestone to the next rather than repeatedly rewriting reports.

The ultimate goal is a working S5000AP modem, SIM detection, mobile network registration, LTE data, SMS, voice calling and IMS/VoLTE where supported.

Do not claim functionality without actual physical evidence. No hardware modification, CP boot, firmware transmission, power/reset operation or flashing is authorized merely by this prompt.

## PROJECT STATE

Repository:

`/Users/wicked/x/nuxel`

Last reported mobile commit:

`22dd6b3ab46dece28abfe83607d7cc64add76843`

Authoritative existing report:

`reports/S5000AP-RADIO-ENDGAME.md`

Previously verified:

- Exynos9820 / beyond2lte hardware.
- S5000AP kernel controller compiled and present.
- SIPC, SHMEM and secure CP boot support.
- `/dev/umts_boot0` and IPC/RFS nodes available.
- `rmnet0` through `rmnet7` exist.
- CP reports `OFFLINE (0)`.
- ModemManager 1.24.2 running, no modem discovered.
- Generic Samsung ModemManager plugin is not a Shannon backend.
- Honest modem diagnostics deployed with rollback.
- Existing Wi-Fi and SSH operational.

Preserve all existing commits, user changes and working subsystems.

## PHASE 1 — ACQUIRE AND VALIDATE THE CP IMAGE

**Selected read-only firmware source: the INSTALLED EFUJ2 RADIO at `/dev/sda16`**
(PARTLABEL `radio`, 52,428,800 B, model `SM-G975F_EUR_XX_EUR0`, build
`G975FXXSEFUJ2_CL2054966_QB20745891`, ITOC magic `TOC\0`). See
`reports/S5000AP-03_6-INSTALLED-RADIO-IDENTITY.md` and
`reports/S5000AP-03_7-EFUJ2-SOURCE-AND-PROVENANCE.md`.

The previously-documented DTK9 archive
`CP_G975FXXS9DTK9_CP17435927_CL20034833_QB35905779_REV01_user_low_ship.tar.md5`
was **not found** in subsequent searches; the derived DTK9 `.lz4` pair
(`modem.bin`/`modem_debug.bin`) is `STRUCTURALLY_VALID_PROVENANCE_UNKNOWN` and is
a **different build** than the installed EFUJ2 image. The old "archive found" and
"exact-build candidate" statements are superseded.

First verify the installed EFUJ2 source identity is readable and has not been altered.

Perform the following offline:

1. Record the archive's size, SHA-256 and complete member listing.
2. Validate TAR structure, member CRC/integrity where applicable, and Samsung MD5 trailer.
3. Understand that MD5 validates archive consistency but is not proof of Samsung authenticity.
4. Safely decompress both LZ4 members into a new owner-local host directory outside Git.
5. Preserve the compressed originals.
6. Record decompressed sizes and SHA-256 hashes.
7. Inspect the binary formats and available modem version, build and model metadata.
8. Compare the CP image's version against the original AP/vendor build and known device hardware.
9. Inspect any firmware signing or image-container metadata without modifying or bypassing it.
10. Determine which component the stock Samsung bootstrap actually uses and whether the debug image has any legitimate diagnostic purpose.

Never assume that `modem_debug.bin` is a safe alternative to the primary modem image.

Do not flash or upload either image.

Do not commit proprietary modem images or extracted firmware to Git.

If the firmware passes structural validation, classify it as a verified local CP candidate—not a successfully booted modem.

## PHASE 2 — RECOVER AND ANALYZE SAMSUNG CBD

Prioritize reusing Samsung's existing CP bootstrap implementation rather than writing a new one.

Research and inspect:

`https://github.com/LineageOS/android_hardware_samsung_slsi-linaro_exynos`

Focus on:

`cpboot_v3`

Also inspect:

`https://github.com/LineageOS/android_device_samsung_exynos9820-common`

Its relevant configuration selects:

- CBD bootloader implementation.
- SIPC protocol.
- Legacy SIPC ioctl compatibility.

Pin exact upstream source revisions.

Analyze whether the available implementation and its configuration actually match the running Exynos9820/S5000AP kernel and Android 10 vendor interfaces.

Do not blindly assume the latest LineageOS branch is compatible with this older Samsung kernel.

Document the exact build configuration, required runtime libraries, transport dependencies, device paths, firmware expectations and any incompatibilities.

Investigate whether the previously recovered matching Samsung Android/Bionic/VNDK runtime can support an isolated native `cbd` experiment.

Prefer the exact Samsung implementation and existing compatibility layers wherever possible.

## PHASE 3 — RECONSTRUCT THE VERIFIED CP BOOT INTERFACE

Study the local kernel source:

`drivers/misc/modem_v1/`

Focus on the S5000AP controller, boot interface, secure-boot integration, SIPC/SHMEM and RFS paths.

Build a compatibility matrix connecting:

1. The physical S5000AP controller.
2. The kernel's boot and state interfaces.
3. The recovered primary modem firmware.
4. The selected Samsung `cbd` implementation.
5. The required userspace runtime.
6. The subsequent radio-control interfaces.

Determine the documented ABI and structures expected by `cbd`.

Identify which boot stages are supported by the running kernel and which still lack evidence.

Differentiate device presence, modem power state, firmware loading, security verification, IPC readiness and full CP boot completion.

Do not substitute driver interfaces from a different Samsung generation.

Do not invent memory offsets, ioctl semantics, firmware signatures or undocumented reset sequences.

## PHASE 4 — IMPLEMENT THE NECESSARY USERSPACE COMPONENTS

Build the compatible Samsung CP bootstrap implementation for the Nuxel environment if the available evidence supports it.

Where a genuine incompatibility exists, implement the smallest justified compatibility adaptation.

Work on the host first.

Provide:

- Reproducible source builds.
- Exact upstream revision provenance.
- Compiler warnings and static analysis.
- Verified executable architecture.
- Dynamic library dependency analysis.
- Firmware identity and version validation.
- Safe failure handling and error reporting.
- Exclusive device ownership checks.
- Strict time and resource bounds.
- Reproducible unit and integration tests.
- Hardware-denied isolation tests where practical.

Use the original CP archive as an offline input only.

Do not invent successful CP responses in tests or treat a simulated bootstrap as real modem boot.

Complete all safe source and build investigations before proposing a physical trial.

## PHASE 5 — IDENTIFY THE ACTUAL BOOT BLOCKER

Determine whether successful CP initialization requires anything beyond the recovered modem image and Samsung `cbd`.

Investigate:

- Missing runtime dependencies.
- Device-specific boot configuration.
- Firmware image format compatibility.
- Kernel/bootloader ABI differences.
- Required vendor components.
- Protected partition dependencies.
- Shared-memory configuration.
- Legitimate secure-boot prerequisites.
- Existing Samsung RIL support.

Maintain an evidence-based decision table.

Every unresolved item must state whether it is:

- Confirmed missing.
- Present but unverified.
- Verified compatible.
- Verified incompatible.
- Dependent on a live, authorized hardware test.

Do not claim another proprietary artifact is indispensable unless the existing sources demonstrate that dependency.

## PHASE 6 — PREPARE ONE CONTROLLED HARDWARE TRIAL

After the offline boot contract and recovery provisions have been verified, prepare a concrete CP first-boot proposal for owner approval.

Document:

- Exact verified firmware hashes.
- Exact executable and kernel build identities.
- Expected device-state transitions.
- Intended device operations.
- Preconditions and exclusive ownership.
- Hardware and software rollback provisions.
- Limits, abort conditions and failure detection.
- Recovery from daemon failure or lost SSH.
- Expected evidence of secure initialization and IPC readiness.

Preserve the original boot image and established TWRP/ADB recovery route.

The handset is A-only; do not assume an inactive boot slot.

Do not modify EFS/NV data, device identity, calibration, carrier locks or secure-boot integrity.

Do not implement unattended flashing, reboot loops or repeated speculative CP startups.

Request explicit owner approval for the specific reviewed trial before any hardware-changing operation.

If a trial fails, preserve evidence and return to offline diagnosis.

## PHASE 7 — COMPLETE PHYSICAL MODEM VERIFICATION

Once a validated CP bootstrap succeeds, establish that the modem genuinely becomes operational.

Verify separately:

1. CP state transitions to ONLINE.
2. SIPC and shared-memory exchange operate.
3. RFS behavior is functional.
4. The modem stays online without crashing.
5. Legitimate SIM presence and readiness are recognized.
6. Network registration works.
7. LTE data can establish and maintain an authorized connection.
8. Data disconnection and reconnection work.
9. SMS works in both directions.
10. Incoming and outgoing voice calls work with audio.
11. IMS/VoLTE works where supported and provisioned.
12. Airplane mode, suspend/resume and service restart behave correctly.

Do not infer working LTE data, SMS or calls merely because the CP boots.

Never expose private SIM or subscriber identifiers in committed logs.

## PHASE 8 — COMPLETE NUXEL INTEGRATION

Once the CP and native radio transport are verified, integrate the required userspace radio-control implementation.

Do not force an unrelated generic ModemManager plugin to claim the modem.

Investigate reusable Samsung RIL/SIPC components first, and only implement a new backend when necessary.

Integrate accurate service state, network status, mobile data controls and user-facing failure reporting.

Preserve existing Wi-Fi, USB, SSH, display, sensors, GNSS, camera and NFC functionality.

Test device and service restarts, reconnect behavior and authorized reboot persistence.

Keep independently verified status for mobile data, SMS, voice and IMS.

## PHASE 9 — CONTINUOUS ENGINEERING PROCESS

After every substantial task:

1. Identify the highest-value unresolved blocker.
2. Verify the relevant source or hardware evidence.
3. Research existing implementations first.
4. Implement the smallest justified fix.
5. Build and test it.
6. Record meaningful results and limitations.
7. Commit focused code changes.
8. Proceed to the next safely executable milestone.

Do not stop merely because the first analysis is complete.

Do not repeatedly perform completed firmware searches or produce another report without investigating a concrete unresolved issue.

If external approval, additional physical measurements or indispensable artifacts are required, identify the exact prerequisite and stop only the affected operation.

Never force unsafe hardware changes simply to achieve the requested outcome.

## REQUIRED DELIVERABLE

Maintain:

`reports/S5000AP-RADIO-FINAL-RECOVERY.md`

Include:

- Git commit and branch information.
- Primary CP archive and image hashes.
- Samsung CBD source provenance.
- Complete compatibility findings.
- Implemented source code and tests.
- Live modem-state evidence.
- Cellular capability acceptance matrix.
- Hardware trial authorization and recovery requirements.
- Precise remaining blockers, if any.
- Reproducible build and deployment instructions.

**FINAL GOAL: A genuine operational Samsung S5000AP modem with fully verified cellular networking on Nuxel.**

The matching CP archive is already available. Continue from that confirmed acquisition milestone, not from the obsolete missing-firmware blocker.

Do all safe engineering work possible within this run. Do not fabricate completion or bypass secure hardware protections. Continue toward each real milestone until full functionality is verified or an independently demonstrated external constraint prevents further progress.
