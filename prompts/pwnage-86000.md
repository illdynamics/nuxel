# PWNAGE-86000 — Operation Penguin Vision 2: Camera Hardware Bring-Up Kickstarter

**Mission:** Make the built-in cameras on the Samsung Galaxy S10+ (`SM-G975F`, `beyond2lte`, Exynos 9820) actually capture real photographs and video in Nuxel. The complete source-led specification, implementation phases, technical decision tree, safety requirements and acceptance tests are in **[`full-pwnage-86000.md`](./full-pwnage-86000.md)**. Read and execute that document; this short file is only the kickoff.

## Read first — current position

The 84000 run made a meaningful camera diagnostic correction: `tools/s10plus/a52/nuxel-v4l2-probe.py` was rewritten to use the V4L2 multi-planar ABI (buffer type 9, `v4l2_pix_format_mplane`, and `v4l2_plane`). The live device correctly identifies FIMC-IS nodes such as `/dev/video111` as `exynos-fimc-is-30c`. **This proves correct node classification, not a working stream.** The camera still has no verified physical frame.

The supplied Nuxel snapshot already has a camera PWA, Photos app, private `org.nuxel.Camera` broker, bridge/media-store support, S10+ firmware fetcher/manifest and camera diagnostics. Do not restart the project or replace working UI/backend components with a mock. Inspect the current working tree first because the repository ZIP predates the 84000 deployment.

## Required device connection

Work on the actual S10+ over **Wi-Fi SSH**, using the existing Nuxel live-SSH discovery helper where possible. Use this private key path:

```sh
~wicked/.ssh/wicked_wqn_id_rsa
```

The last successful 84000 report used `root@192.168.178.167`; the repository helper previously had a stale pinned address (`10.20.30.16`). Rediscover the current phone IP and use the latest verified address rather than trusting the stale one. Connect with `IdentitiesOnly=yes`, `BatchMode=yes`, a timeout, and normal host-key verification. Never use `StrictHostKeyChecking=no`, remove host keys, copy/print the private key, or log secrets. Verify `id -u == 0`, device model, kernel and current boot before writing anything.

## Execution order

1. **Establish live truth.** Read the latest `docs/pwnage-84000/evidence/20261106T144537Z/ENGINEERING-REPORT.md`, current PWNAGE-83000 evidence, actual running kernel/config, current V4L2 probe source and output, firmware state, boot logs, sensor bindings, media nodes, DTB and existing camera service. Separate historical observations from current facts.
2. **Re-run the corrected V4L2 tests properly.** Use the target kernel's UAPI headers and a small C diagnostic as the authority. For mplane nodes, use type 9 consistently for `QUERYCAP`-guided `G_FMT`, `ENUM_FMT`, `TRY_FMT`, `S_FMT`, `REQBUFS`, `QUERYBUF`, `QBUF`, `DQBUF`, `STREAMON/OFF`; pass valid plane arrays. Do not trust the old single-planar capture test or infer private ioctls from `V4L2_CAP_EXT_PIX_FORMAT`.
3. **Restore the exact S10+ camera firmware contract.** Audit `firmware/s10plus/manifest.yml`, `fetch-vendor-blobs.sh`, `install-firmware.sh`, and `verify-firmware.sh`. The known candidate set includes `fimc_is_fw_mcu.bin`, `fimc_is_lib.bin`, `fimc_is_rta.bin`, `fmsb.bin`, `rxse.bin`, `txse1.bin`–`txse3.bin`, `dnn.bin`, and sensor-specific `setfile_2l4.bin`, `setfile_3m3.bin`, `setfile_3p9.bin`, `setfile_3j1.bin`, `setfile_4ha.bin` plus applicable calibration data. Verify every required file against the pinned source, exact driver request path, SHA-256 and sensor mapping. The ZIP contains no actual proprietary blobs—only the README and `.gitkeep`—so fetch/stage them locally through the existing pinned source or read-only from this owner's own device if necessary. Do not commit or redistribute proprietary firmware.
4. **Trace the exact FIMC-IS2 driver.** Use the pinned `Linux4/android_kernel_samsung_exynos9820` source at commit `f7194c1d15eded1c2a1a4dc63825b26103435cc0` unless the current tree/live kernel proves it has changed. Follow Kconfig, device-tree endpoints, sensor probe/power, CSI, ISP firmware, secure-camera/TEE, node registration, ioctl ops, vb2 queue ops, DMA/ION/IOMMU and stream state machine. The prior live config had `CONFIG_VIDEO_EXYNOS_FIMC_IS2=y` while `CONFIG_MEDIA_CONTROLLER` was unset; verify the current state and source dependencies. Merely enabling `CONFIG_MEDIA_CONTROLLER` cannot create entities/links that the driver never registers.
5. **Produce the first real rear-main frame.** Start with the 2L4 rear-wide sensor. If standard mplane works, complete a bounded stream proof. If the driver requires Samsung-private ioctls, implement a typed adapter from the exact pinned driver headers/source. If the driver is missing a usable userspace surface, patch the existing in-tree driver to expose a correct V4L2/media-controller pipeline. Only if those paths are genuinely insufficient, design a replacement driver from the exact source/register/DT knowledge. No guessed ioctl numbers, register pokes, unrelated SoC code or random setfiles.
6. **Use the exact Samsung camera stack as a serious reference/fallback.** The matching `beyond2lte` vendor sources list `vendor.samsung.hardware.camera.provider@3.0-service`, `camera.exynos9820.so`, camera device/provider interfaces, `libexynoscamera3.so`, dependencies and sensor firmware. Investigate the complete dependency/runtime contract. Do not copy one `.so` into Fedora and call it a port. If required, build a properly isolated, version-matched Android vendor runtime and export frames through a narrow Nuxel bridge.
7. **Integrate the real stream into Nuxel.** Preserve the existing Camera/Photos PWAs, permissions, privacy indicator, private broker name `org.nuxel.Camera`, bridge and durable media store. Prefer a real PipeWire camera source/portal path where compatible; otherwise build an explicitly documented, authenticated Nuxel stream bridge. No hidden capture, fake frames, or test-pattern fallback presented as a camera.
8. **Then bring up the remaining sensors.** After rear-wide is stable, add front 3J1, telephoto 3M3, ultrawide 3P9, then depth/IR 4HA if supported by its actual function. Validate each one independently; preserve sensor identity, calibration and lens metadata.

## Kernel / driver work is allowed — but controlled

Do not stop merely because userspace capture is blocked. A separate camera-experimental kernel configuration and a source patch series are explicitly in scope. The current known-good kernel must remain recoverable. Build and validate off-device first; compare configs, preserve kbase/Mali, DECON/fbdev, audio, MFC, Wi-Fi, NFC, suspend and boot features. If a kernel update is necessary, back up the exact current boot image/partition, verify recovery access and the restore artifact, validate image/DTB/headers/build ID, and only then deploy the camera-specific boot image. Never touch modem, EFS, calibration, persistent security or user-data partitions. No blind I²C writes or arbitrary secure-camera/TEE changes.

A driver from scratch is permitted only after a written source audit proves the current driver cannot be adapted. Reuse the sensor subdevice, CSI, clock/regulator, reset, reserved-memory, ISP, IOMMU and vb2 work wherever possible. A new capture driver must implement correct power sequencing, media entities/pads, format negotiation, buffer lifecycle, DMA safety, stream control, error recovery and suspend/resume—not just expose a `/dev/video*` node.

## Completion gate — physical evidence, not a green UI

This mission is complete only when all of the following are proven on the physical S10+:

- The rear-main 2L4 sensor is powered, initialized through the matching ISP path and produces changing real-scene frames (not a test pattern or cached image).
- The Nuxel Camera app shows a live preview, captures a genuine JPEG, and the saved photo opens in Photos.
- A real video recording is saved and plays back; microphone audio is included when permission is granted.
- Camera release/reopen, app exit, permission revocation, suspend/resume and reboot do not wedge the device or leave camera hardware powered indefinitely.
- Firmware loads are verified by exact source/hash/path and kernel logs; no calibration, thermal, display, audio, MFC, Wi-Fi or boot regressions occur.
- At least 30 seconds of live preview is stable at a documented conservative mode; report actual resolution, frame rate, drops, temperature and memory use.
- Owner manually confirms the physical preview and saved image. Record all limitations for the remaining lenses rather than claiming all five work because one does.

Keep timestamped evidence under `docs/pwnage-86000/evidence/<UTC_TIMESTAMP>/`, update the camera status docs, provide a precise rollback plan and report what was actually deployed. Continue until the rear camera works; do not stop at firmware installation, sensor enumeration, an app opening, a kernel compiling or an architectural proposal.

**No fake pass. No guessed hardware commands. No unrelated-device firmware. No reckless flashing. Do the real engineering, and get the Penguin taking pictures.**
