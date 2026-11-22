# NUXEL Galaxy S10+ Camera — Recovery-Sensitive Engineering Audit

**Audit date:** 2026-11-21  
**Evidence input:** user-supplied `nuxel-ds-cam (2).zip` (387,494,204-byte ZIP; 20,865 entries, 805,605,144 total uncompressed bytes).  
**Device:** Samsung Galaxy S10+ SM-G975F (`beyond2lte`), Exynos9820, downstream kernel 4.14.253.  
**Method:** read-only static examination of the attached archive; firmware SHA-256 recomputation; source, workflow, and historical-report comparison; public-reference documentation check. **No connection to the user's actual phone, no compilation against its live source tree, and no flash were performed.**

## Decision in one paragraph

**NOT nearly finished end-to-end.** Estimate ~20% (range 15–25%) of a genuinely working complete physical camera system, ~70–80% of investigation/architecture groundwork, and zero physical-frame acceptance for Nuxel. Stage A (Samsung FIMC-IS2) reached real stock firmware loading, rear 2L4 sensor init, S_FMT, REQBUFS and QBUF but a live STREAMON caused a hardware-watchdog panic. Strategy B (native Exynos9820 CSI-2/V4L2 driver based on butztill/s10-linux) is chosen and its source is staged; **the port is not completed or integrated, its camera DTS/DTBO is not present, and no first frame was captured**. The ZIP does **not** contain a live post-DT incident baseline. Treat current DT state as unknown, even if the handset appears healthy now. The immediate mission is recovery provenance and an offline-only exact-delta DT audit, not another flash.

## Scope and confidence key

- **VERIFIED_STATIC:** direct code/file inspection or SHA-256 calculation in this supplied ZIP.
- **REPORTED_LIVE:** the included November 20 records describe tests on the physical phone, but not independently retested in this review.
- **HISTORICAL:** older A52 / October boot work may not describe the current running phone.
- **NOT VERIFIED:** no reproducible end-to-end evidence in the archive, or relevant files missing.

The ZIP entries all carry 2026-11-20 timestamps. The specific recent DTB/DTBO wrecking and subsequent recovery mentioned by the owner are **not documented in this ZIP**; no assumption about the final active kernel, BOOT content, dtb, dtbo or runtime state is justified.

## What has actually happened, in sequence

1. The original A52 camera/gallery UI, permissions, bridge media save path, native GTK placeholder and camera broker were built offline and reported as `APPLICATION_READY_HARDWARE_BLOCKED` (`docs/a52-camera/FINAL-STATUS.md`). The UI is not equivalent to camera functionality.
2. An older camera audit found sensor-bound private FIMC-IS nodes but failed or misleading generic V4L2 formatting, absent usable firmware and no real image (`pwn/COMPONENT_STATE_AND_CAMERA_AUDIT.md`, A52 docs, older Camera V2 recovery audit).
3. The owner-stock camera firmware root cause was traced to a vendor `filp_open('/system/vendor/firmware/' + name)` path, **not** the earlier `request_binary()` search-path patch (`cam-report.md`, lines 15–37). Eight firmware blobs were copied to that directory and `/usr/lib/firmware/`, matching `firmware/s10plus/camera-stock-DTK9.json`. Rear SAK2L4 sensor rev 0xA102, actuator/OIS initialization and mode enumeration were recorded live.
4. `nuxel-ion-capture` demonstrated the Samsung camera `camera_heap` ION DMABUF path and capture-node QBUF acceptance (`cam-report.md`, lines 74–93). Earlier simple mmap attempts were invalid for this driver.
5. Vendor leader private control `V4L2_CID_IS_S_SENSOR_SIZE = 0x009A1045` fixed rear sensor S_FMT failure: 2016x1512, Bayer `SBGGR10`, two planes including metadata, REQBUFS and four QBUFs returned success (`pwn/CAMERA_IMPLEMENTATION_LOG.md`, lines 142–173). **QBUF is not a physical frame.**
6. Sensor `STREAMON` out of the completed proprietary ISP chain sequence caused hardware-watchdog **Panic#2** and reboot to Nuxel; there was no DQBUF or physical file (`pwn/CAMERA_IMPLEMENTATION_LOG.md`, lines 174–205). The recorded device recovered after the crash. Do **not** repeat that test as a probe.
7. The architectural choice pivoted to **Strategy B**, taking the independently tested native Exynos9820 driver from `butztill/s10-linux` rather than reconstructing the full proprietary Android Samsung HAL (`pwn/CAMERA_DRIVER_ARCHITECTURE.md`).
8. The source was copied into `drivers/s10-camera-v4l2/`; media framework files were reportedly compiled offline, the media Kconfig fragment was created, and four sensor runtime tables were reportedly reproduced in an external working tree (`pwn/CAMERA_IMPLEMENTATION_LOG.md`, lines 211–269). This was **not** a successful native-driver port or phone deployment.
9. `pwn/cam.md`, `cam2.md`, `cam3.md` set the mission, earlier narrow firmware task, and later Strategy-B expansion, respectively. `cam3.md` is primarily a **future task specification**, not proof that its phases executed.

## Inspectable technical inventory

| Layer | Evidence in archive | Real status |
|---|---|---|
| Stock DDK/RTA/MCU + five setfiles | 8 blobs and owner-stock manifest | Blob hashes verified independently; recorded phone deployment and sensor init. Manifest expressly says `kernel_abi_verified:false`. |
| Rear 2L4 physical sensor | Recorded `SAK2L4` rev 0xA102 with actuator/OIS init | Module init, not captured pixels. |
| Rear 2L4 mode | 2016x1512 @ 30 nominal; `V4L2_CID_IS_S_SENSOR_SIZE` | Vendor driver S_FMT reportedly PASS. No frame/FPS verified. |
| FIMC-IS2 buffer allocation | ION camera_heap id=5, image+metadata DMABUF | Capture QBUF reportedly PASS. DQBUF FAIL/not reached. |
| FIMC-IS2 streaming | Crash during sensor STREAMON | Unsafe to retry without full HAL state; not primary path. |
| Native CSI driver | `drivers/s10-camera-v4l2/exynos9820-csis.c`, 1380 lines | Upstream-style code still contains post-6.x kernel API calls and needs 4.14 port. |
| Sensor driver | `drivers/s10-camera-v4l2/s5k-cis.c`, 1115 lines | Still needs API, clock, reset and mux/pinctrl adaptation, plus external tables. |
| Lens actuator | `drivers/s10-camera-v4l2/ak7374.c`, 361 lines | Staged only; modern PM API remains. |
| Driver build wiring | Makefile present, no repository-visible native driver Kconfig/Kbuild integration | NOT built with Nuxel kernel; `obj-m += vb2/` refers to a `vb2/` subdirectory **absent** from this ZIP. |
| Kernel media framework | `kernel/s10plus/configs/nuxel-camera-v4l2.fragment` | Created but `kernel/s10plus/build-kernel.sh` defaults to `nuxel-drm-kbase.fragment`; does NOT automatically consume the camera fragment. Exact config parity must be checked. |
| Camera DTS/DTBO | No new beyond2lte camera DTS/DTBO port or tested candidate identifiable | NOT COMPLETE, and user's later incident suggests heightened danger. |
| Generated S5K tables | Docs describe external generation | No `.s5k` runtime outputs or generator scripts available in extracted archive; must retrieve pinned source privately, verify hashes and stage on phone if required. |
| libcamera and software ISP | Described in prompt/references | No complete Nuxel-target libcamera pipeline port/build/physical test in ZIP. |
| PipeWire publisher | `shell/nuxel-camera-portal/` | Existing hardware path still uses generic `v4l2src io-mode=mmap`, impossible on the private FIMC path; must be replaced/adapted for native RAW V4L2 path. |
| Standard XDG camera portal | `shell/nuxel-camera-portal/nuxel_camera_portal_impl.py` | Exists but `camera_present()` checks FIMC node + socket path, **not working frames**; `OpenPipeWireRemote` uses `os.open()` on a PipeWire Unix socket path, which is not an ordinary connected PipeWire remote. Requires protocol correction and live tests. |
| Bridge CameraStatus | `services/nuxel-bridge/src/bridge.py` around lines 3120–3165 | Returns `capture_verified: False` unconditionally. Must change only when trustworthy backend evidence exists. |
| Nuxel Camera PWA | `pwa/nuxel-apps/camera-gallery/js/camera.js` | `getUserMedia`, photo canvas and `MediaRecorder`/mic path exist, plus file-backed save through bridge; they cannot function without a real camera source. |
| Native GTK camera | `shell/nuxel-camera-native/nuxel_camera_native.py` | Real GTK shell with honest no-preview fallback, not proven capture. |
| Official Fedora GTK and independent Flatpak apps | No successful live acceptance | Both still required to prove reusable camera stack. |
| Flash/torch | Historical flashlight service and camera-gpio references | No demonstrated photo flash, safe video torch or camera synchronization. |
| Photo and video acceptance | `pwn/CAMERA_LIVE_ACCEPTANCE.md` | No physical rear/front frame, JPEG, video, audio-sync, gallery playback or three-app PASS. |

### Specific reasons the staged driver is not a build-ready port

Direct source inspection found these legacy-incompatible interfaces **still present**:

- `exynos9820-csis.c`: 14 uses of `v4l2_subdev_state`, modern `.enable_streams`/`.disable_streams`, `v4l2_async_connection`, `v4l2_async_nf_init`, `video_device_pipeline_start`, `pm_runtime_resume_and_get`, modern asynchronous graph hookup.
- `s5k-cis.c`: 9 uses of `v4l2_subdev_state`, modern stream enable/disable, `v4l2_fwnode_endpoint_alloc_parse`, `__v4l2_ctrl_modify_range`, `pm_runtime_resume_and_get`, SoC mux-control dependence.
- `ak7374.c`: `pm_runtime_resume_and_get` remains.
- Driver directory contains seven files only, including Makefile with `obj-m += vb2/`, but no `vb2/` child exists. No compile proof of these staged files under the Nuxel 4.14 kernel is included.
- `pwn/upstream-camera-research` is just empty ZIP directory entries, not a usable checkout of pinned reference/source scripts.
- Building media framework alone does not prove the native CSI/sensor/actuator driver builds, probes, streams or coexists safely with FIMC-IS2.

### Firmware/provenance warning

I independently computed SHA-256 of **all eight** `firmware/s10plus/blobs/device-vendor-firmware/*.bin` archive members; each matches its `camera-stock-DTK9.json` entry. That is solid archive integrity evidence, not a live device hash and **not** kernel ABI compatibility. The ZIP does contain proprietary owner-stock blobs notwithstanding some documents saying they are never committed; keep them outside any public Git commit, GitHub PR, redistribution or release bundle unless rights have been established.

## Why DT/DTBO is the critical safety workstream

- The handset uses **A-only BOOT**, not A/B slots (`device/s10plus/deviceinfo`). There is no standby-slot kernel rollback. The established recovery routes are TWRP ADB and Download Mode; **not fastboot**.
- Historic BOOT packaging mistakes have already been documented: S-Boot executes a raw arm64 `Image`, not `Image.gz`, and a legacy packer once wrote the DTB size at Android BOOT header offset 40 where `header_version=1` belongs. See `boot/s10plus/build-candidate.sh` and `tools/s10plus/verify-boot-image.py`.
- The existing boot validator is valuable for Android v1 header, page size, raw Image, ramdisk/cpio and partition-capacity checks. **It is NOT a complete camera-DT/DTBO verifier.** In particular its device-tree checks focus on historical NFC GPIOs; a syntactically valid DT can still have wrong camera clock, GPIO polarity, regulator, I2C endpoint, lane mapping, board revision or DT overlay selection. DTBO partition and final merged active tree require separate validation.
- There is an appended DTB in historical boot evidence, but source comments also describe a separate bootloader-selected DTB/DTBO merge. Determine **from currently running live evidence** which tree and overlay variant actually boot, before changing any DTS, BOOT or DTBO.
- The ZIP has older extracted DTBs and DTBO partition capture in debug evidence, but **no verified November 21 current BOOT+DTB+DTBO capture and rollback bundle**. Old historical A5/A25 images are not safe assumptions about the current known-good device.
- A BOOT flash success, verified write hash, or ability to access TWRP **does not prove a healthy Nuxel boot**. Observe Nuxel SSH/device identity and core services after reboot.

### Minimum fail-closed guardrails before one more candidate

1. In **read-only mode**, confirm exact model/board revision, live kernel hash/config, boot source, `/proc/device-tree` / `/sys/firmware/devicetree/base`, dtb selection, overlays, `dmesg` OF probing, exact BOOT/DTB/DTBO/RECOVERY by-name partition existence/size/mount state. Never assume all partition names exist; discover first.
2. Capture full exact **currently working BOOT**, separately present DTB/DTBO, and recovery image where safely readable, off-device on the Mac; verify sizes and SHA-256 by readback and immutable manifests. Preserve also relevant kernel config, initramfs and deployment logs. Never store private partition backups in public Git.
3. Inspect the active merged FDT and all overlay-table entries for the actual board variant. Disassemble/recompile and verify semantic graph equivalence where no change is intended; diff every node/property in the candidate. Require stable clocks/phys/regulators/pinctrl/I2C and no unrelated changes.
4. Fix/add the missing **camera-focused** validator; include negative fixtures for missing nodes, wrong phandles/endpoints, lane counts, incompatible board revisions, reused GPIOs, conflicting CSIS/FIMC owners, truncated DTBO, malformed header, wrong container, and unchanged baseline equivalence.
5. Preserve proven BOOT container/ramdisk, active DTB/DTBO and all working non-camera drivers through **one-variable-at-a-time** staging. First enable media framework with zero DT changes if an image rewrite is necessary; when possible use externally built signed/version-matching modules instead of flashing. Verify chosen driver has exclusive hardware ownership.
6. Candidate BOOT must pass both the existing boot image gate and new camera-DT/merged-tree gates, complete kernel/module build, config parity, image format and size, artifact provenance and an explicit off-device rollback trial plan. A visual checklist is not an automated PASS; every gate must output evidence and a hash.
7. Use the repo's `scripts/nuxel-adb-flash-pack/scripts/05-preflight.sh` and `03-flash.sh --profile s10plus --boot-only --execute` workflow, after verifying actual CLI and target partitions. BOOT-only means **NO USERDATA, SYSTEM, RECOVERY, EFS, modem, parameter or unrelated partition writes**. Do not use permissive generic `boot/s10plus/flash.sh` defaults or manual dd if the stronger existing pack applies.
8. If reboot unexpectedly returns to TWRP, treat the camera candidate as a **FAILED BOOT**. Collect pstore/last_kmsg/recovery logs and actual partition hashes; immediately recover known-good BOOT and any modified DT partition, verify Nuxel boots, then revise the failure hypothesis. Never reflash the identical failed candidate or destroy the working backup. Stop experimenting if known-good Nuxel cannot be restored; remain safely in recovery instead of blind loops.
9. A candidate passes only when Nuxel boots, SSH/services/display/touch/Wi-Fi/USB/mic etc. are healthy, active device-tree identity matches intended hash/variant, and no camera/kern warnings regress. Preserve result receipts and revert before escalating.

**No workflow can mathematically guarantee that the phone never lands in a bad DT state.** The achievable goal is to prevent *untested, unvalidated or non-recoverable* DT writes, to make every experiment reversible, and to finish each failed trial on the known-good Nuxel baseline whenever technically recoverable.

## Recommended engineering sequence

| Round | Mission | Boot/DT writes? | Pass gate |
|---|---|---|---|
| 0 | Post-incident read-only forensic baseline and exact backup/restore proof | No | Full current-device evidence and verified off-device backups; no stale assumptions |
| 1 | Add automated boot/DTB/DTBO regression gates; make zero-DT-change golden baseline repeatable | No | Negative tests fail, baseline roundtrip passes, recovery artifact manifest complete |
| 2 | Native driver port into exact 4.14 tree, fix Kbuild, generated firmware/source provenance, exclusive binding | No | Entire integrated driver and kernel build without unsupported API, config parity, static and fixture tests |
| 3 | Exact `beyond2lte` camera topology and board-revision camera DTS adaptation; validate overlay selection | No | Base/merged DT diff isolated, no unrelated change, camera graph and clocks/regulators checked |
| 4 | One narrowly scoped BOOT-only deployment to establish boot and first real rear SAK2L4 DQBUF | Possibly one well-gated BOOT candidate; additional trials based only on fresh diagnosis | Nuxel healthy + 2 distinct physical scenes with real dequeued frame bytes |
| 5 | libcamera software ISP, PipeWire publisher, portal and privacy correctness | Usually userspace-only | Working rear color preview/still and shared provider route |
| 6 | Front main + supported other sensors, photo/video+microphone, torch, Nuxel GTK/PWA, Fedora GTK, Flatpak | Usually userspace; another kernel/DT change only if verified necessary | Full live acceptance matrix and correct resource cleanup |
| 7 | Robustness, repeat-after-reboot, thermal, suspend, rollback and delivery | No by default | All gate evidence plus reproducible build/runbook |

**Effort estimate:** A first genuine rear frame may take **4–6 focused DeepSeek engineering rounds**, and perhaps **1–3 well-controlled BOOT candidates**, if the 4.14 port and board topology behave reasonably. More attempts may be required; never budget flash cycles as proof of progress. A complete multi-sensor, color-correct, photo/video/torch, three-application stack likely takes **8–15+ rounds**, potentially much more if CSIS/PHY, proprietary color calibration, autofocus or device-specific camera routing fail. The reference project's four camera stills were on **SM-G973F beyond1lte and an experimental 7.2-based kernel**, not proof your S10+ 4.14 port will be drop-in. Its source-preview loader itself is reported as host-tested only.

## Hard no-go conditions

- Fresh, working phone BOOT + active tree identity cannot be established.
- Off-device recovery backups missing, unverified, or stored only on the phone.
- The target is any unexpected partition, active board revision doesn't match, or recovery is inaccessible.
- BOOT/DT/DTBO gate only issues warnings for a structural or semantic mismatch.
- New driver and old FIMC-IS2 claim the same physical CSIS/sensor/controller resources.
- Candidate fails kernel build, kernel config parity, or changed-DT semantic diff.
- Agent starts repeating vendor FIMC STREAMON watchdog crashes.
- A camera attempt cannot be attributed to a source SHA, image SHA and exactly one approved delta.
- A failed experimental boot has not first been returned to a verified good baseline.
- Only camera enumeration/QBUF is available, but a physical image is claimed.

## Read first on next DeepSeek session

1. `pwn/cam.md`, `pwn/cam2.md`, `pwn/cam3.md` **as historical prompts**, not deployment receipts.
2. `pwn/CAMERA_IMPLEMENTATION_LOG.md`, `pwn/CAMERA_DRIVER_ARCHITECTURE.md`, `pwn/CAMERA_LIVE_ACCEPTANCE.md`, `pwn/CAMERA_RECOVERY_AND_ROLLBACK.md`, `pwn/CAMERA_REPRODUCIBLE_BUILD.md`.
3. `cam-report.md` but note that later November 20 log updates supersede its S_FMT failure claim.
4. `drivers/s10-camera-v4l2/*`, `kernel/s10plus/build-kernel.sh`, config fragments, `boot/s10plus/build-candidate.sh`, `tools/s10plus/verify-boot-image.py`, `scripts/nuxel-adb-flash-pack/README.md`.
5. `docs/s10plus-autonomous-boot-repair/*`, `docs/s10plus-device-inventory.md`, `device/s10plus/deviceinfo`, existing captures under `scripts/s10plus-debug-pack/` as **historical** comparative inputs only.
6. `shell/nuxel-camera-portal/*`, `shell/nuxel-camera-native/*`, `services/nuxel-bridge/src/bridge.py`, `pwa/nuxel-apps/camera-gallery/js/camera.js`, `docs/a52-camera/*`.
7. Pinned public source `https://github.com/butztill/s10-linux` (review `docs/public/STATUS.md` and `docs/public/BUILD-VALIDATION.md`) and pinned Samsung 4.14 fork. Do not assume upstream S10 status transfers to beyond2lte.

**Recommendation:** Execute the separate prompt pack beginning with PROMPT 00. Do **not** jump straight to the first flash prompt. The first three rounds should make progress while writing **zero** BOOT, DTB or DTBO sectors.
