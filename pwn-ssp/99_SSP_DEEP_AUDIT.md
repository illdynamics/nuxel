# NUXEL S10+ — SSP / BCM47752 / LSM6DSO / Auto-Rotation Engineering Audit

**Date:** 2026-11-22. **Basis:** user-uploaded `nuxel-ds-ssp (1).zip`, 20,860 archive entries, approximately 795.7 MB uncompressed. **No live-device access** was performed. This is an audit of the archive and historical reports inside it, not proof of the current handset state.

## Executive determination

- **Estimated engineering preparation / implementation:** **~60%**. Not a measured percentage.
- **Estimated progress toward fully proven, persistent end-to-end physical sensors plus automatic rotation:** **~40%**, with considerable uncertainty because the hardware startup blocker is still unresolved.
- **Reproducibly proven physical accelerometer streaming:** **No**. Latest historical logs/notes report zeros.
- **Reproducibly proven physical gyro streaming:** **No**. Latest historical logs/notes report zeros.
- **Physical automatic rotation based on true sensors:** **No**. Manual rotation and seven-mode software policy are significantly more mature.
- **Known-good OS baseline:** `pwn/ssp4.md` claims a BOOT-only reconciled-kernel flash succeeded on 2026-11-21 and booted Nuxel; this must be re-established live. The archive does not contain a current BOOT image to verify that claim.
- **Newest explicit SSP handoffs:** `pwn/ssp5.md` and `pwn/ssp6.md` have **identical SHA-256** (`692735cedbd73064f6570ede992adae648084b7db4da6d0d3fa880997e659ca1`). There are additional kernel patch files, including a large `0027`, which are *not* thereby proved deployed or safe.

**The single critical path:** electrical/clock/reset/PM ready → valid bidirectional MCU boot-ROM response → correctly completed RAM firmware download → application GetVersion + normal SSP handshake → physical accel/gyro samples → automatic orientation → cold boot and suspend/resume robustness.

## Source/evidence boundaries

**Available:** `pwn/ssp.md` through `pwn/ssp6.md`; `ssp.md`; `NUXEL_SSP_{RECOVERY_V2,CONTINUATION_PACK}`; `tools/s10plus/ssp-native/*.c`; `tools/s10plus/ssp-runtime/`; `kernel/s10plus/patches/{0020,0023,0025,0026,0027}*.patch`; `services/nuxel-orientation/`; `configs/nuxel/orientation/`; historical reports under `docs/` and `evidence/`; `tools/s10plus/pack-ssp-boot.py`; `kernel/s10plus/build-kernel.sh`.

**Not available in archive:** `.git`, `reports/` (including `reports/SSP-BBD-DOWNLOAD-STATEMACHINE-IMPLEMENTED-2026-11-21.md`), built kernel working tree `kernel/s10plus/.build/src`, original embedded `bbd_patch_file_beyond.h`, a verifiable current BOOT/DTB/DTBO/RECOVERY partition dump, and a direct live phone connection. The historical reports claim a matching stock Samsung runtime and exact embedded firmware identity, but these bytes cannot all be reverified from this archive. Seek the actual active checkout/worktrees and phone, and avoid confusing missing archival evidence with nonexistent live work.

## Chronological reconstruction

1. **Before November 2026:** Orientation support implemented: a single Nuxel orientation owner, manual compositor transforms, touchscreen and viewport adaptation, seven policies. Historical hardware boundary in `docs/a69/ROTATION-HARDWARE-BOUNDARY.md` established no live SSP gravity; IIO devices showed timestamp-only entries, not usable accel x/y/z channels. `evidence/pwnage-101000/rotation-transitions/rotation-transitions.txt` proves compositor/external-presenter *manual* rotation transitions, **not sensor-driven auto-rotation**.
2. **November 13–17:** Recovered matching vendor anchors (`lhd`, `lhd.conf`, sensorhub HAL), analyzed Samsung BBD/RPC protocol, extracted patch metadata and partial firmware state machine, created read-only/runtime tooling and simulations. `ssp.md` identifies branch `feat/ssp`, commit `6bcbcea6`, and two missing November 17 reports, but these are historical pointers only.
3. **November 21 — `pwn/ssp2.md`:** Diagnosed split kernel: native bring-up stub in release tree versus earlier experimental kernel lacking regulator/SPI runtime PM changes. Reported `tx=32 rx=0`, accelerometer `0,0,0`, gyro `0,0,0`.
4. **November 21 — `pwn/ssp3.md`:** Constructed `0023-nuxel-ssp-native-bringup-reconciled.patch` layered after required `0020`. Reported successful offline kernel compilation and packaging. It did **not** flash yet.
5. **November 21 — `pwn/ssp4.md`:** Reported entering TWRP, flashing **BOOT only** (historically `/dev/block/sda14`, reverify!), and booting successfully back to Nuxel. `nuxel_ssp_bringup_hw` symbols present, real `initialize_mcu` invoked. No valid WHOAMI: `0xffffffff`, `tx=32 rx=0`. Firmware download needed before the normal handshake; fixed by neither recompilation nor device enumeration alone.
6. **November 21 — `pwn/ssp5.md` and `ssp6.md`:** Identical newest handoff, citing missing `reports/SSP-BBD-DOWNLOAD-STATEMACHINE-IMPLEMENTED-2026-11-21.md`. The previous agent reportedly built a firmware-download state machine, but hardware trial read `0xFFFFFFFF`, `HSI_ERROR_STATUS=0xFF`, RX count zero; warm reboot/runtime PM did not establish communication. **Cold power-on timing is a hypothesis, not exclusively proven.**
7. **Additional present files:** `0025` force-rail-disable, `0026` phase-1 ROM sync, `0027` purported full kernel downloader. Their presence does not establish successful application, compilation, flashed image identity, or on-device evidence. In particular, `0027` must **NOT** be flashed as-is.

## What is implemented and what is not

| Subsystem | Status from archive | Evidence / caveat |
|---|---|---|
| Physical platform discovery | Largely complete | S10+ SM-G975F/beyond2lte, Exynos9820, Broadcom BCM47752KUB1G, STM LSM6DSO, downstream Linux 4.14.253 |
| SSP/BBD base driver | Present | Samsung `drivers/sensorhub/brcm/` patches; not a mainline sensor exposing ordinary IIO accel channels |
| Hub 1.8V regulator and SPI runtime PM | `0020` patch prepared/reported deployed | `regulator_enable`, SPI host reinit; a reported regulator-enabled state is **not** a physical voltage measurement |
| Native bring-up peer | `0023` reconciled and **historically** flashed | User/agent notes report `nuxel_ssp_bringup_hw`, BBD peer, sysfs diagnostics, real `initialize_mcu` |
| Firmware identity and ROM protocol research | Substantial | Claimed ASIC `0x004775b0`, patch entry `0x00800161`, decoded blob 438,895 B and IEEE CRC32 `0x93d35bb4`; exact blob absent in this ZIP |
| Vendor runtime | Historically isolated and inspected | Native Nuxel runtime must have zero Android userspace dependency; vendor `lhd` is only a protocol/behavior reference |
| Older `nuxel_bbd_download.c` | **Not** a verified firmware uploader | Program explicitly refuses firmware download and only permits offline inspection or bounded live version query |
| `nuxel_bbd_flash.c` | F0/F1 parser, RPC transport, ACK/NACK, application-start flow written | Local tests are simulated. `--flash` means **RAM firmware download**, not BOOT partition flash. No physical completion demonstrated; `write_control` ignores return status. |
| `0025` rail cold-cycle | Proposed patch | Calls `regulator_force_disable`, potentially affects shared consumers; physical rail fall/unshared regulator path must be proved |
| `0026` ROM-sync | Proposed patch | Calls original direct-SSI function on retry; its return semantics and reception must be independently verified |
| `0027` full kernel download | Experimental **not deployment-ready** patch | Duplicate earlier changes, significant error-path risks, no recorded kernel build/physical validation |
| Native bridge | Present (`nuxel_ssp_bridge.py`) | Opens `/dev/bbd_sensor`, `/dev/ttyBCM`; requests `nuxel_bringup`, attempts streaming, does not fabricate samples |
| Seven-mode orientation service | Strongly implemented | Four fixed modes and auto / auto-portrait / auto-landscape; compositor `wlr-randr` state verification, touch ownership, hysteresis; calibrated actual sensor-to-screen axes still unverified |
| Actual accelerometer and gyroscope | **BLOCKED** | Latest documented zero readings and no valid MCU response |
| Physical auto-rotation and endurance | **BLOCKED** | Requires true sample input, actual landscape detection, screen/touch checks, suspend/resume and normal reboot |

## Important newly surfaced code risks (specific, actionable)

### 1. Patch `0027` duplicates `0023` changes and must not silently skip

`0027-nuxel-ssp-kernel-firmware-download.patch` re-introduces many changes already in `0023-nuxel-ssp-native-bringup-reconciled.patch`: `bbd.c` includes, BBD peer functions, and a large `ssp_bbd.c` peer implementation. Both diffs use an earlier base and overlapping context. The build wrapper in `kernel/s10plus/build-kernel.sh` treats unmarked patches as **optional**, logging a warning when a patch cannot apply and continuing. Because `0027.patch` has no `.required` companion in this snapshot, a successful kernel build can omit the intended firmware logic. **Rebase/split/replace the series, verify each `git apply --check`/applied-manifest outcome, require exact expected symbols, and abort on missing mandatory SSP changes.** Do not simply mark the conflict `.required` without resolving it.

### 2. Potential deadlock in `0027` failure path

The `bbd_do_transfer()` hunk at about patch lines 1225–1280 enters with `mutex_lock(&data->pending_mutex)`. On the failure branch the new code calls `mutex_lock(&data->pending_mutex)` again without first unlocking it, then performs more unlock/cleanup operations. This is an obvious **same-thread mutex re-acquisition hazard**, capable of hanging SSP or kernel workers. Audit all `comm_mutex`, `pending_mutex`, IRQ and callback paths and repair before even an offline kernel build is marked ready.

### 3. Firmware parser can misrepresent completeness

The `dl_next_record()` function returns false for truncated/invalid records. The firmware download loop simply `break`s and accepts any previously transmitted F1 count greater than zero as enough to proceed to application start. Non-F1 records are skipped rather than interpreted or rejected according to verified vendor semantics. The required invariant is **entire firmware container parsed and every required record completed, with exact count, destination map, total bytes, identity and per-operation receipts**. Any truncated data, unrecognized command, overflow, wrong tag, missing final record or changed digest must hard-fail.

### 4. Memory allocation and arithmetic risks

`dl_decode_blob()` uses `kmalloc()` for a decoded firmware blob reported at 438,895 bytes; a large contiguous kmalloc allocation under kernel 4.14 may fail due to fragmentation. Use a version-supported, bounded large-buffer strategy (`kv[m]alloc`/`vmalloc` or streaming chunks), validate the actual available APIs, and match the correct free function. Audit hex parser termination, capacity, integer bounds and CRC. Do not assume the `Crc` patch-header field is IEEE CRC32 (the earlier audit explicitly warns it is not).

### 5. ACK/version state and hardware timing need stronger gates

`0027` maintains session ACK sequence bytes across many writes, but does not visibly reset the stored ACK fields before each transaction; stale/wrapped sequence numbers must not satisfy a later operation. The patch also accepts a GetVersion-like RPC without yet proving vendor-expected boot/application identity and session state. Validate framing, payload, CRC, reply ID, protocol status, correlation, firmware version and expected state. Direct SPI transfers must be serialized with the regular `ttyBCM` worker and SPI runtime PM. Never claim a cold rail power-cycle from `regulator_is_enabled()` alone.

### 6. BOOT packaging preserves DTB tail by design, but needs hard proof

`tools/s10plus/pack-ssp-boot.py` is explicitly designed to carry the donor DTB/hash tail byte-for-byte while replacing only the kernel payload. That is valuable, but it locates the FDT magic and includes heuristic fallback logic; verify parsing, kernel offsets and exact DTB tail SHA-256 *externally*, with `tools/s10plus/verify-boot-image.py` and a second independent parser, against the **currently running known-good donor**. A BOOT-only flash can still change embedded/appended DT data if the packer is wrong. The preflight must compare DTB data inside the BOOT image, not just the separately stored DTB/DTBO partitions.

### 7. Existing `nuxel_bbd_flash` return status must be interpreted correctly

The no-argument read-only verification path in `nuxel_bbd_flash.c` returns `EXIT_SUCCESS_VERIFIED` (0) after **only** validating container identity and records, while logging that no device I/O occurred. This is acceptable as a local file-verification exit code **only if the caller explicitly distinguishes it from physical firmware success**; rename/split state reporting or enforce unambiguous machine-readable output. Its `--flash` path uses 36 autobaud bytes via ttyBCM, while the experimental `0027` kernel path sends 32 via raw SPI; reconcile those with actual vendor code, including which transport and moment the boot ROM accepts. The `write_control()` helper returns `void` and logs failed control writes without failing the final result, so successful `ESW:READY` propagation is not independently proved. These are separate from the simulated C tests.

### 8. Native bridge and RAM firmware downloader need single ownership

The bridge opens `/dev/bbd_sensor` and `/dev/ttyBCM`; `nuxel_bbd_flash --flash` also attempts to open them and changes BBD pass-through. A kernel downloader would add a third possible actor. Only **one** verified initialization/download owner may drive the transport in a given session. Serialize ownership, define restart/cancellation/error behavior, remove false `ESW:READY`, and leave the unrelated GNSS path stable.

### 9. Rotation must discriminate real physical evidence from mocks

The orientation software normalizes sysfs accelerometer readings and has 7 policies, but the mount matrix and `gravity_reference` entries are marked **unverified** in `configs/nuxel/orientation/orientation.json`. `_streaming()` in the bridge treats any nonzero accel/gyro vector as streaming; that is useful for a diagnostic hint, not a physical acceptance criterion. A stationary gyro can legitimately be zero. Confirm correlated gravity sign changes while moving, gyro bursts during rotations, fresh timestamps, correct axis remapping, screen dimensions/transform and touchscreen alignment.

## Offline tests actually reproduced during this audit

- `make -C tools/s10plus/ssp-native OUT=/tmp/ssp-audit-build check` — **PASS**. Compiled C firmware/transport harnesses, two Python embedded-patch verifier tests, and simulated framing replay. Replay itself explicitly says `hardware_verified=false`, `operation_completion_verified=false`.
- `PYTHONPATH=services/nuxel-orientation python3 -m pytest -q services/nuxel-orientation/tests` — **68 passed**.
- `python3 -S -m unittest discover -s NUXEL_SSP_RECOVERY_V2 -p 'test_*.py'` — **14 passed**.
- Python `unittest discover` on the orientation directory yielded `0 tests` because they are **pytest** tests; run them with pytest.
- **Not tested:** full kernel build/application, the `0025/0026/0027` series on an exact working kernel tree, correct live firmware container image, any hardware transactions, or physically observed rotation. No BOOT/DT changes were made.

## Proposed completion sequence

**Round A — Live baseline + recovery seal (read-only):** inspect original development checkout, missing reports, active branch, phone boot identity; dump/hash BOOT, DTB, DTBO and RECOVERY safely with partition sizes, and independently validate owner-held known-good images and TWRP restoration path. Include embedded BOOT DT tail manifest. If no complete known-good rollback, do not flash.

**Round B — Code correctness, source-backed vendor parity (offline):** de-duplicate/rebase `0027` after `0020/0023`, fix mutex lock order, parser strictness, buffer strategy, fresh ACK matching, exact lifecycle, transport concurrency and optional patch skipping. Compare to pinned Samsung `lhd` and source without inventing protocol commands. Prefer minimal userspace correction if kernel change is avoidable.

**Round C — Full host tests/build/preflight (offline):** negative/error tests, exact F0..F5 fixture map and hash checks, kernel patch apply manifest, compile target, symbol and config audit, package BOOT with identical ramdisk and embedded DT tail, verify against current device identity. Keep camera/NFC untouched.

**Round D — Controlled first-light trial (physical, bounded):** run read-only then an explicitly agreed hardware session with a single authoritative firmware owner. Capture regulator and SPI state/timestamps; verify a real ROM response; require all firmware writes/operation receipts and valid app version before WHOAMI and readiness. If all-ones SPI continues, stop and diagnose exact clock/rail/reset/IRQ/window instead of blindly repeating downloads.

**Round E — SSP motion samples:** bring up the accelerometer and gyroscope with real raw samples and timestamps; prove motion-correlated axes, scale and stability at multiple poses. No fake data or synthetic success.

**Round F — Auto-rotation and physical sideways acceptance:** on the phone set `auto` and put it physically sideways; sample true gravity and verify the compositor **automatically** reports effective orientation `90` or `270`, with corresponding verified transform, landscape logical geometry, touchscreen and apps. Test both sides, portrait and reverse portrait, auto restrictions, fixed locks, device flat, service loss.

**Round G — Persistence:** repeated clean cold and warm boots, screen suspend/resume, service crash/restart, GNSS and other peripheral checks, rollback drills and finalized evidence-backed runbook.

## Effort / flashing forecast

An organized engineering effort may take **4–8 substantial Pro-Thinking rounds**, supported by smaller fast/flash-model passes for test fixes, logs, fixtures and documentation. **0–2 candidate BOOT flashes is plausible if the source-verified solution is right and the ROM responds**, but **several more or an unresolved hardware fault** are also plausible. Every candidate flash must be justified by new evidence. A repeated failed flash is not progress; restoring a previously proven Nuxel BOOT image is the preferred route to bring the phone back.

## DT and TWRP protection agreement — non-negotiable

1. **Never write DTB, DTBO, RECOVERY, modem, EFS, bootloader, PIT or unrelated block devices. Never run a general multi-partition flash package.** Read-only hash capture of DT partitions is permitted with validated, real partition mapping and capacity.
2. Reverify live BOOT/DTB/DTBO/RECOVERY partition identities and `androidboot.dtbo_idx` (historically 9). Do not hardcode `sda12`/`sda13`/`sda14`/`sda15` from old notes.
3. Before every BOOT-only candidate flash, independently verify donor BOOT hash, candidate boot header, payload bounds, load addresses, ramdisk hash, embedded DTB tail bytes/hash, cmdline, and unchanged external DTB and DTBO hashes. Preserve an on-host and TWRP-accessible known-good BOOT rollback image, verified with byte-for-byte readback or hash. Never use a new untrusted image as rollback.
4. Capture target and candidate image SHA-256 and exact write size, with expected BOOT partition bounds. Write **only** the independently verified BOOT target through the established TWRP procedure; verify write/readback, then reboot to Nuxel system. No boot-chain experimentation.
5. **Unexpected return to TWRP after an intended system boot = failed candidate.** Diagnose logs/artifact/partition/hash/bootreason, restore the verified known-good BOOT first if the cause is unclear, and confirm Nuxel is back. Try a corrected candidate only after a new causal fix and repeated full preflight. Do not blind-loop flashes or power cycles. If no normal boot from known-good, preserve TWRP and escalate instead of touching DT.
6. You cannot guarantee zero probability of brick from an agent prompt. This policy minimizes known high-risk causes, preserves a verified rollback, and *excludes* DT changes from the mission.

## Strict definition of DONE

PASS only after: real MCU boot-ROM bidirectional traffic and version; **complete authenticated/validated firmware load and app-start evidence**; normal SSP WHOAMI/scan; physical accel **and** gyro motion-correlated streams; seven-mode automatic/manual rotation with calibrated axes, correct screen/touch mapping; normal reboot, cold boot and suspend/resume; no GNSS/camera/NFC/network regressions; boot/DT/DTBO integrity checks; complete logs, hashes and test results. A passing simulation or successful BOOT flash alone is not DONE.

**Companion:** `NUXEL_SSP_ULTIMATE_PROMPT_PACK_2026-11-22.md` and the individual prompts in `NUXEL_SSP_ENDGAME_PROMPT_PACK_2026-11-22.zip`.
