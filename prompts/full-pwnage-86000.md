# FULL-PWNAGE-86000 — Operation Penguin Vision 2

**Target device:** Samsung Galaxy S10+ (`SM-G975F`, codename `beyond2lte`), Exynos 9820 / `universal9820`, ARM64  
**Target OS:** Nuxel, Fedora-based ARM64 mobile Linux  
**Mission class:** camera firmware restoration, ISP/CSI bring-up, Linux media-driver integration, optional kernel driver engineering, optional Android vendor-camera compatibility runtime, camera service integration, physical-device validation  
**Primary finish line:** capture and save a real photograph from the physical rear-main camera on the S10+ from Nuxel. Then complete real video and the remaining camera modules in controlled stages.

> **Execution directive:** Do not stop at an explanation, a source audit, firmware downloads, enumerated sensors, a compiled kernel, a running service, an open Camera UI, a test pattern, or a `getUserMedia()` promise. Keep executing the technically justified path until real sensor frames flow into Nuxel. The owner explicitly authorizes serious engineering, including modifying the existing driver and writing a replacement driver if genuinely necessary. That authorization does not mean blind register writes, unrelated firmware, destructive partition operations, or avoidable device-bricking risk.

The short execution entry point is `pwnage-86000.md`. Read this complete document before changing the repository or phone. Keep this mission camera-only: do not bundle unrelated desktop, Doom, Flatpak, theme, or performance work into this change set.

---

# 0. Mission context and current known state

## 0.1 Current device facts

The supplied repository snapshot (`nuxel-main (12).zip`) is a 2026-11-04-era snapshot. Its camera work is substantial: the Camera and Photos applications, permission flow, bridge API, media store, private camera broker, hardware diagnostics, FIMC-IS inventory, firmware fetcher, firmware manifest and kernel build wrapper already exist.

The current phone state is newer than that ZIP because PWNAGE-84000 has since deployed changes. At the end of the owner's 84000 run the agent reported:

- Live host: `root@192.168.178.167` (this is a last-known address, not a guarantee that DHCP has not changed it).
- Root access was verified (`id -u == 0`).
- Device: Samsung Galaxy S10+ SM-G975F, Fedora 43 ARM64.
- Running kernel: `Linux 4.14.253-gf7194c1d15ed-dirty #5 SMP aarch64` at the time of that report. Re-read the current value.
- The kernel's Samsung FIMC-IS family is present and camera nodes enumerate.
- The 84000 run corrected `tools/s10plus/a52/nuxel-v4l2-probe.py` to use the multi-planar V4L2 ABI: buffer type 9, `v4l2_pix_format_mplane`, and `v4l2_plane`.
- On-device probe correctly classified `/dev/video111` as `exynos-fimc-is-30c` (and other Exynos FIMC-IS nodes as multi-planar endpoints).
- That diagnostic correction did **not** produce a verified frame.
- The previous report explicitly said camera streaming still required firmware/setfile/media-graph or vendor-pipeline work.
- The working display stack (Phoc/Wayland + `nuxel-wl-fb` + `/dev/fb0`), Mali/EGL, audio, MFC and Wi-Fi were to remain undisturbed.

The helper's previously pinned Wi-Fi host `10.20.30.16` was stale during 84000. The owner-supplied `192.168.178.167` worked then. Discover the current host again; never repeatedly hammer an old address or silently disable SSH host-key checks.

**Important distinction:** the 84000 result proves the diagnostic now recognizes multi-planar FIMC-IS nodes. It does not prove that every standard V4L2 ioctl is implemented by those nodes, that a sensor/ISP is configured, that required firmware is present, or that a frame can be dequeued. Continue from the new evidence, not from an assumed success or the old failed probe.

## 0.2 Historical repository observations that must be revalidated

The ZIP's `docs/a52-camera/HARDWARE-INVENTORY.md` records these observations from the actual SM-G975F:

| Camera role | Sensor module identifier | Reported kernel device |
|---|---|---|
| Rear main / wide | 2L4 | `fimc-is_sensor_2l4@20` |
| Rear telephoto | 3M3 | `fimc-is_sensor_3m3@5A` |
| Rear ultrawide | 3P9 | `fimc-is_sensor_3p9@2D` |
| Front main | 3J1 | `fimc-is_sensor_3j1@10` |
| Front depth / IR | 4HA | `fimc-is_sensor_4ha@10` |

The old inventory specifically corrects an earlier manifest/UI assumption: the front main sensor is 3J1, not a front-facing 2L4 alias. Do not reintroduce the wrong mapping.

Other historically observed platform components:

- FIMC-IS core platform device: `170e0000.fimc_is`.
- Sensor-controller platform devices around `17030000`, `17040000`, `17050000`, `17050000.fimc_is_sensor2`, `17060000`, and `17090000`.
- MIPI CSI PHY devices including `dphy_m4s4_csis0` and `dphy_m0s4s4s4_csis1/2/3`.
- OIS / actuator devices, including AK737x actuators and an Exynos FIMC-IS OIS controller.
- Camera calibration EEPROM devices were observed probing.
- Exynos GDC post-processing block at `17530000.gdc`.
- Camera-related reserved-memory / ION heaps were observed (`secure_camera`, `camera_contig`, `camera`, and FIMC-IS library/DDK/RTA memory regions).
- The earlier kernel log reported successful secure-camera TrustZone setup (`SMC_SECCAM_SETENV/INIT`) and a warning about FIMC-IS library memory address fallback. Re-check current logs and exact return codes.

Historical video-node naming from the same inventory:

| Node family recorded in the ZIP | Historical role | Handling rule |
|---|---|---|
| `exynos-fimc-is-ss0..ss5` | sensor sub-stream nodes | identify from sysfs and driver source |
| `exynos-fimc-is-30{s,c,p,f,g}` | sensor-slot 0 pipeline family | map each suffix by the exact driver's registered node/queue role |
| `exynos-fimc-is-31{s,c,p,f,g}` | sensor-slot 1 pipeline family | same; do not assume every member is image capture |
| `exynos-fimc-is-32s/32p` | sensor-slot 2 family | same |
| `exynos-fimc-is-i0*`, `i1*` | ISP input paths | source-driven role mapping |
| `exynos-fimc-is-me0c`, `me1c` | metadata | never treat as image pixels |
| `exynos-fimc-is-m0*..m5*`, `vra` | metadata / VRA-related nodes | never choose by node number alone |
| `exynos-fimc-is-ssinstancevc*` | virtual channel endpoints | trace the graph and queue role |
| `/dev/video6`–`11` | MFC decoder/encoder | NOT camera capture |
| `/dev/video12` | Exynos JPEG M2M | JPEG processing, not raw sensor capture |
| `/dev/video50` | scaler M2M | post-processing, not sensor capture |
| `/dev/video155` | GDC M2M | post-processing, not sensor capture |

Node numbers are dynamic and may change between boots or builds. Never hardcode `/dev/video111` as “the rear camera” in production code. Resolve through `/sys/class/video4linux`, `/sys/dev/char`, driver/device links, `VIDIOC_QUERYCAP`, media topology if present, and exact source.

## 0.3 The exact repository assets to inspect

Start with these current-tree paths (names can change; search if moved):

```text
firmware/s10plus/manifest.yml
firmware/s10plus/fetch-vendor-blobs.sh
firmware/s10plus/gen-manifest.py
firmware/s10plus/install-firmware.sh
firmware/s10plus/verify-firmware.sh
firmware/s10plus/blobs/README.md

kernel/s10plus/build-kernel.sh
kernel/s10plus/configs/live-required.config
kernel/s10plus/configs/nuxel-drm-kbase.fragment
kernel/s10plus/patches/

 tools/s10plus/a52/nuxel-v4l2-probe.py
 tools/s10plus/a52/nuxel-v4l2-capture-test.py
 docs/a52-camera/
 docs/a53/
 configs/nuxel/camera/camera.json
 configs/nuxel/privacy/camera.json
 configs/nuxel/camera/README.md

pwa/nuxel-apps/camera-gallery/
pwa/nuxel-apps/photos/
services/nuxel-bridge/
shell/nuxel-camera-portal/
```

Remove the leading space shown before `tools/` when copying a path; it is only a visual grouping artifact.

The old snapshot says the actual proprietary camera binaries are **not committed** in `firmware/s10plus/blobs/`; only README and `.gitkeep` are present. Do not mistake manifest entries for files already installed. Check the current working tree and phone independently.

## 0.4 Previous conclusions that are now superseded or unproven

Several old documents (`HARDWARE-BLOCKERS.md`, `KERNEL-CAMERA-GAP.md`, `MEDIA-PIPELINE-ANALYSIS.md`, and historical A53 notes) concluded that `VIDIOC_S_FMT -> ENOTTY` on a node tested with the single-planar API proved a Samsung-private-only interface. PWNAGE-84000 fixed the probe to use the correct multi-planar ABI. Therefore:

- Do not carry forward the old `HARDWARE_BLOCKED` conclusion as a settled technical fact.
- Do not treat the old single-planar test as valid evidence about an mplane queue.
- Do not infer that `V4L2_CAP_EXT_PIX_FORMAT` is a Samsung-private ioctl. It is a standard V4L2 capability concerning extended pixel-format fields.
- Do not infer that `CONFIG_MEDIA_CONTROLLER=y` alone will create a topology. The driver must actually register a `media_device`, entities, pads and links.
- Do not infer that no `/dev/media*` means capture can never work. A vendor driver may configure internal links or expose a private pipeline API without a standard media graph.
- Do not assume the standard Exynos4/S5P FIMC driver documented upstream is the same hardware or software interface as the S10+'s Exynos 9820 FIMC-IS2. It is useful architectural context only, not a drop-in driver.

Re-test the current implementation and update the diagnosis with fresh evidence.

---

# PART I — RESEARCH FINDINGS AND TECHNICAL DIRECTION

## 1. Research-backed facts

### 1.1 The platform is a supported Android camera target, not an unknown sensor board

The LineageOS device information identifies `beyond2lte` as the Samsung Galaxy S10+ with Exynos 9820, ARM64, and five camera modules (rear wide, telephoto, ultrawide, front main, depth). Its current device page identifies the downstream 4.14 kernel family and the `SM-G975F` supported model. This corroborates the Nuxel inventory and confirms that a mature device-specific camera stack exists in the Android ecosystem.

References:

- https://lineageos.github.io/lineage_wiki/devices/beyond2lte/
- https://github.com/whatawurst/android_device_samsung_beyond2lte

### 1.2 Exact-device vendor-camera components are discoverable

A public `beyond2lte` vendor proprietary-file inventory identifies a full Samsung camera stack, including:

**Provider / HAL layer (representative entries):**

```text
vendor/etc/init/vendor.samsung.hardware.camera.provider@3.0-service.rc
vendor/bin/hw/vendor.samsung.hardware.camera.provider@3.0-service
vendor/lib/hw/camera.exynos9820.so
vendor/lib64/hw/camera.exynos9820.so
vendor/lib/camera.device@1.0-impl.so
vendor/lib/camera.device@3.2-impl.so
vendor/lib/camera.device@3.3-impl.so
vendor/lib/camera.device@3.4-impl.so
vendor/lib/camera.device@3.5-impl.so
vendor/lib/vendor.samsung.camera.device@1.0-impl.so
vendor/lib/vendor.samsung.camera.device@4.0-impl.so
vendor/lib/vendor.samsung.hardware.camera.device@1.0.so
vendor/lib/vendor.samsung.hardware.camera.device@4.0.so
vendor/lib/vendor.samsung.hardware.camera.provider@3.0.so
vendor/lib64/camera.device@1.0-impl.so
vendor/lib64/camera.device@3.2-impl.so
vendor/lib64/camera.device@3.3-impl.so
vendor/lib64/camera.device@3.4-impl.so
vendor/lib64/camera.device@3.5-impl.so
vendor/lib64/vendor.samsung.camera.device@1.0-impl.so
vendor/lib64/vendor.samsung.camera.device@4.0-impl.so
vendor/lib64/vendor.samsung.hardware.camera.device@1.0.so
vendor/lib64/vendor.samsung.hardware.camera.device@4.0.so
vendor/lib64/vendor.samsung.hardware.camera.provider@3.0.so
```

**Core camera / vendor dependencies (representative entries):**

```text
vendor/lib/libexynoscamera3.so
vendor/lib64/libexynoscamera3.so
vendor/lib/libacryl.so
vendor/lib/libcsc.so
vendor/lib/libdualcam_optical_zoom.so
vendor/lib/libdualcapture.so
vendor/lib/libdualcapture_interface.so
vendor/lib/libdualpreview_interface.so
vendor/lib/libgiantmscl.so
vendor/lib/libhwjpeg.so
vendor/lib/libhwjsqz.so
vendor/lib/libsensorlistener.so
vendor/lib/libuniapi.so
vendor/lib/libuniplugin.so
vendor/lib/libvkmanager_vendor.so
```

The list also includes dual-camera/refocus features, image-processing libraries and framework/vendor interface libraries. The current branch and exact installed vendor build must be re-inspected: the public inventory found during research is a valuable reference, not proof that every listed file or version applies unchanged to this particular phone's current firmware.

The important implication is that a working fallback is not “copy `libexynoscamera3.so` and hope.” The service, HIDL interfaces, Bionic environment, Android property handling, vendor dependencies, allocator, memory sharing and device permissions form one integrated runtime.

Source reference:

- https://github.com/whatawurst/android_device_samsung_beyond2lte/blob/lineage-17.1/proprietary-files-vendor.txt (camera section and firmware inventory)

### 1.3 Exact-device camera ISP firmware and sensor setfiles are identified

The Nuxel firmware manifest is pinned to:

```text
Repository: Linux4/proprietary_vendor_samsung
Commit:     05c9ef8f16e0ad5ab274e408c120dfd99fd5c628
```

The manifest's `camera_isp` group contains these candidate firmware files:

| File | Manifest SHA-256 | Intended role stated by source/manifest |
|---|---|---|
| `dnn.bin` | `306fdcf5e888d5efdae95da2fa26333b3fe026cc8c4a3dec99f8e94430e33bb7` | ISP/DNN support; verify exact caller |
| `dual_cal_front_subfront.bin` | `629444ee8e442091cbd0530e611dcd80ba7547990cf0006ced7139288cfa4ae9` | dual-camera calibration; verify consumer and applicability |
| `fimc_is_fw_mcu.bin` | `0887a6c5f2ad8b4d261473889b3b4c5e44497df4b487775e86ae9cf9e535acdf` | FIMC-IS MCU firmware |
| `fimc_is_lib.bin` | `08e54ac3817b4c9d4851a90a7b3ac3e5b30ba98378c217ce8ea51db0ff98f1db` | FIMC-IS library/DDK image |
| `fimc_is_rta.bin` | `12809be7b38919b7f98ad14c85d55d3b6d2b029304e7baef1141aca7dd94b1e9` | FIMC-IS RTA image |
| `fmsb.bin` | `a2105f9a89e5a185296d2fa246b557ebf19ab108536ec7304a23bdc2ca6d7f3e` | FIMC-IS support firmware; exact role/path from source |
| `rxse.bin` | `7f430939e464e5cfe7947331992cec30923c416343b81eb03e52c01df333e42a` | support firmware; exact role/path from source |
| `setfile_2l4.bin` | `876638f09d7ec4ad4ca695d7219267f236c9ea832252fd93296724c176a6b0f3` | rear-main 2L4 sensor configuration |
| `setfile_3j1.bin` | `4e68f97def312d9b4827d9eab3c3a10f2d476ed4aa76a9c42d4b7b84ef571bb9` | front-main 3J1 sensor configuration |
| `setfile_3m3.bin` | `92c4bf1c197215d9a870e27051c04ff677c58dafc530355ecff69b85fddac1cd` | rear-tele 3M3 sensor configuration |
| `setfile_3p9.bin` | `6e774bc773833d49046d3d3cb750181a990fb10ea76654d8b87501b23e1883fd` | rear-ultrawide 3P9 sensor configuration |
| `setfile_4ha.bin` | `4e68f97def312d9b4827d9eab3c3a10f2d476ed4aa76a9c42d4b7b84ef571bb9` | front-depth/IR 4HA sensor configuration; notably same checksum as `setfile_3j1` in this manifest—verify source bytes and mapping; do not silently “correct” or assume this is valid |
| `txse1.bin` | `9da74071f31e28e70544eaf2cb4b7f9e9d81f70ff776d82b2a521ca609337c07` | support firmware; exact role/path from source |
| `txse2.bin` | `ba7243afb3d0ed12427b8cd44484ce5a3c665c08e434ae7ee9a9563829401828` | support firmware; exact role/path from source |
| `txse3.bin` | `f7acfe27e4df05faf038596fd7a854c9ffb0a409f3aef634396bf90f086bebc9` | support firmware; exact role/path from source |

**Manifest warning:** these entries were historically marked `required: false` to keep generic Nuxel images buildable. That is not the correct validation policy for a camera-enabled S10+ image. Create a camera-specific firmware verification profile that makes only the blobs proven necessary for that camera path mandatory. Do not simply mark all files in all generic firmware categories required.

**Manifest hygiene warning:** `vts.bin` currently appears in the same `camera_isp` block in the older manifest even though VTS is voice-trigger/audio-related in this platform's context. Audit and correct category descriptions/ownership so camera verification does not accidentally require unrelated audio firmware. Preserve its existing audio behavior.

**Potential checksum anomaly:** the manifest lists the same SHA-256 for `setfile_3j1.bin` and `setfile_4ha.bin`. Verify the exact source tree, source paths, generated manifest, blob lengths and contents. It could be a genuine shared payload, a generated-manifest bug or a mistaken mapping. Do not decide based only on the hash's appearance.

The firmware fetcher already pins a source commit and retrieves both common Exynos9820 and `beyond2lte` vendor firmware trees. Audit its HTTP failure handling, tree API handling, output layout and checksum generation. It must fail closed on 404/API errors, partial downloads, empty files, wrong commit, missing expected paths and hash mismatches. Download to temporary files, verify, then atomically rename into the ignored local blob staging area.

References:

- Nuxel repository: `firmware/s10plus/manifest.yml`
- Nuxel repository: `firmware/s10plus/fetch-vendor-blobs.sh`
- Public device firmware inventory: https://github.com/Evolution-X-Devices/vendor_samsung_beyond2lte/blob/bka/beyond2lte-vendor.mk
- Public S10+ device blob list: https://github.com/whatawurst/android_device_samsung_beyond2lte/blob/lineage-17.1/proprietary-files-vendor.txt

### 1.4 V4L2 multi-planar API requirements are standard and precise

The Linux V4L2 documentation explicitly defines separate multi-planar buffer types and structures. For an mplane capture queue, the selected buffer type must consistently be `V4L2_BUF_TYPE_VIDEO_CAPTURE_MPLANE` (value 9); format negotiation uses `struct v4l2_pix_format_mplane`; buffer query/queue/dequeue uses a userspace array of `struct v4l2_plane` through `v4l2_buffer.m.planes`, with `v4l2_buffer.length` equal to the number of elements in that array. The same queue type must be used consistently across format/buffer/stream ioctls.

References:

- https://cdn.kernel.org/doc/html/latest/userspace-api/media/v4l/planar-apis.html
- https://github.com/torvalds/linux/blob/master/Documentation/userspace-api/media/v4l/vidioc-qbuf.rst

The current 84000 Python probe uses ctypes. Audit its native alignment, pointer width, ioctl encoding and structure sizes against target headers. The authoritative capture proof should be a small C utility compiled on the device or cross-compiled using the exact target UAPI headers. Python can wrap the C tool and format its JSON report, but do not rely on a hand-maintained ctypes layout as the only proof.

### 1.5 Do not confuse Exynos4 FIMC with S10+ FIMC-IS2

Upstream Linux documentation describes the S5P/Exynos4 FIMC driver and its media-controller topology, mplane capture nodes and subdevices. This is a useful reference for how a Linux camera pipeline can be modelled, but those documents explicitly identify older SoCs such as S5PV210/Exynos4210—not the S10+'s Exynos 9820 FIMC-IS2. Do not copy that driver or its node topology as if it implements the S10+ ISP.

Use the exact downstream `Linux4/android_kernel_samsung_exynos9820` source and its `VIDEO_EXYNOS_FIMC_IS2` implementation for all hardware claims. The upstream FIMC docs can inspire standard media-controller design only after confirming it matches the actual register blocks and device tree.

Reference:

- https://www.kernel.org/doc/html/latest/admin-guide/media/fimc.html
- https://www.kernel.org/doc/html/next/driver-api/media/drivers/fimc-devel.html

### 1.6 Android vendor camera is a system, not a standalone shared library

AOSP documents that the camera HAL is the boundary between Android's camera framework/service and hardware-specific implementation. Android 8 introduced binderized HIDL HALs; Android 13 introduced AIDL for new camera HAL development, while existing HIDL camera HALs remain supported for compatibility. The matching S10+ blob inventory found here specifically lists a Samsung `camera.provider@3.0` service and HIDL-era camera device/provider implementation libraries. The exact installed ROM's provider interface and dependencies must be inspected, not assumed from generic AOSP guidance.

This matters if a vendor runtime is needed: the required service manager/Binder/HIDL interfaces, Bionic, Android properties, service init sequence, allocator/gralloc/ION interfaces, memory-sharing semantics, SELinux assumptions and related Samsung services all matter. A `dlopen()` of one proprietary `.so` under Fedora's glibc is not a complete camera HAL port.

References:

- https://source.android.com/docs/core/camera/camera3
- https://source.android.com/docs/core/architecture/hal
- https://github.com/libhybris/libhybris
- https://halium.org/

### 1.7 A libcamera pipeline handler is possible, but only after the hardware sequence is understood

libcamera's own pipeline-handler guide describes the handler as the component that detects cameras and configures/manages device-specific sensor, input, ISP, processing and memory resources through V4L2 and media-controller interfaces. That makes it a good final Linux integration point **after** a real low-level capture path is known. It is not a magic driver generator: it cannot create a missing kernel UAPI, missing ISP firmware or absent media entities.

Reference:

- https://docs.libcamera.org/master/guides/pipeline-handler.html

## 2. Recommended route ranking

Execute the routes in order, but do not artificially block a promising fallback once evidence justifies it.

### Route A — complete the existing FIMC-IS2 driver path (first choice)

Use the running kernel's actual FIMC-IS2 driver and matching firmware. The driver and sensors already enumerate. First discover whether the standard mplane queue is usable when configured correctly, whether a specific initialization handshake is missing, or whether Samsung-private pipeline setup is required.

This route preserves the existing kernel architecture and may need only firmware, correct pipeline configuration and a typed userspace adapter.

### Route B — expose a real Linux media/V4L2 interface by patching the existing driver

If the in-tree FIMC-IS2 code contains the relevant sensor/CSI/ISP setup but fails to expose a usable standard interface, patch the existing driver in the pinned kernel tree. Prefer adding/repairing:

- V4L2 video device ioctl ops and multi-planar formats;
- vb2 queue setup, buffer preparation, queueing, start/stop streaming and cleanup;
- media device/entity/pad/link registration where supported by the actual topology;
- V4L2 subdevice ops for sensors/CSI, async notifier/binding where appropriate for this 4.14 tree;
- documented controls and per-sensor format/mode exposure;
- DMA/IOMMU/ION buffer ownership, cache synchronization and error handling;
- the driver-to-userspace contract needed for firmware/ISP boot and session configuration.

Do not just set `CONFIG_MEDIA_CONTROLLER=y` and declare success. Confirm the driver source registers an actual media graph and the necessary subdevice nodes.

### Route C — implement the exact Samsung private FIMC-IS2 UAPI in userspace

If the existing driver intentionally exposes a private V4L2 ioctl/control interface, reconstruct it precisely from the exact driver source/header and the matching Samsung HAL's call flow. Build a small typed C proof of concept first. Use exact ioctl structures, command IDs, enum values, firmware names, memory sizes, sensor-slot mappings, buffer rules, timeouts and state transitions from source. Then wrap the proven sequence in a maintainable Nuxel daemon or libcamera pipeline handler.

This is valid engineering. Do not invent a convenient API that does not match the kernel.

### Route D — exact-device Samsung Android vendor camera compatibility runtime

If the real camera can only be operated through the matching Samsung provider/HAL, treat this as a serious, supported alternative—not as an excuse to abandon the camera. Determine the exact installed system/vendor firmware generation; acquire only owner-authorized exact-device files; reconstruct a complete compatible Android userspace/service environment; start the exact camera provider; validate capture in that environment; then bridge frames to Nuxel using a narrow, local IPC/shared-buffer interface.

Consider a maintained Halium/libhybris-derived approach only after testing the actual target vendor stack and Android interface versions. Do not assume libhybris automatically makes a HIDL provider service callable; prove every ABI and service dependency.

### Route E — new driver from scratch (explicitly permitted last resort)

If the exact FIMC-IS2 source has a fundamental architectural defect, is missing required functionality, or its proprietary userspace contract cannot be used in Nuxel, write a new Linux kernel driver or a clean in-tree replacement. Do this only after a written technical decision record shows why Routes A–D cannot deliver a maintainable stream.

A new driver must reuse and respect the existing platform's:

- device-tree sensor endpoints and module identity;
- I²C sensor drivers and sensor mode tables;
- regulator, clock, reset, GPIO, pinctrl and MCLK sequencing;
- MIPI CSI-2 PHY/receiver, lanes, virtual channels and link frequencies;
- Exynos 9820 FIMC-IS/ISP/processing hardware;
- secure-camera/TEE constraints and reserved-memory contracts;
- IOMMU, DMA API, contiguous memory and cache-maintenance rules;
- video buffer queueing, format negotiation, stream lifecycle and PM.

Do not start programming guessed ISP registers. Reuse exact vendor source/register definitions or authoritative SoC documentation. A driver that creates `/dev/videoX` but cannot safely power, program and capture through the sensor/ISP is not a driver completion.

---

# PART II — CONNECTION, BACKUPS AND BASELINE

## 3. Wi-Fi SSH to the real root console

The phone is the source of truth for live runtime behavior. Connect over Wi-Fi SSH, not only through an offline ZIP analysis.

Private key path:

```text
~wicked/.ssh/wicked_wqn_id_rsa
```

Required connection flow:

1. From the Nuxel repository, inspect and use the existing helper:

   ```sh
   scripts/s10plus-debug-pack/nuxel-live-ssh.sh --transport wlan --status
   ```

2. If its configured IP is stale/unreachable, discover the current WLAN address using the project's existing owner-approved mechanism or recent network status. The last successful host reported by PWNAGE-84000 was `192.168.178.167`; test it only as a last-known candidate, not a hardcoded permanent endpoint.
3. Connect using the existing host-key database and the specified key:

   ```sh
   ssh -i ~wicked/.ssh/wicked_wqn_id_rsa \
     -o IdentitiesOnly=yes \
     -o BatchMode=yes \
     -o ConnectTimeout=10 \
     root@<CURRENT_S10_WIFI_IP>
   ```

4. Keep normal SSH host-key verification. Do not add `StrictHostKeyChecking=no`, delete `known_hosts`, print private-key contents, copy the private key to the device, or put credentials in logs/scripts.
5. Verify:

   ```sh
   id -u
   uname -a
   cat /proc/device-tree/model 2>/dev/null | tr '\0' '\n'
   cat /proc/cmdline
   ```

   `id -u` must print `0`; device-tree identity must correspond to the S10+ Exynos 9820 target. If any of this differs, stop device writes and investigate.

Use Wi-Fi SSH for read-only diagnostics, firmware staging, user-space service deployment and log retrieval. For bootloader/TWRP operations that require USB, keep the operation separate and only use it after the safety gates below.

## 4. Establish repository and phone baseline

### 4.1 Repository

Capture:

```sh
git status --short --branch
git rev-parse HEAD
git log -1 --oneline --decorate
```

Record uncommitted changes. Do not reset, clean, checkout over, or overwrite owner work. Create a timestamped working branch or checkpoint commit only if safe and consistent with the repo workflow. Record all modified paths and why they are in scope.

Read:

- `docs/pwnage-84000/evidence/20261106T144537Z/ENGINEERING-REPORT.md`;
- the latest PWNAGE-83000 report/evidence (find actual path; do not assume it is present if not);
- `docs/a52-camera/HARDWARE-INVENTORY.md`;
- `docs/a52-camera/KERNEL-CAMERA-GAP.md`;
- `docs/a52-camera/MEDIA-TOPOLOGY.txt`;
- `docs/a52-camera/MEDIA-PIPELINE-ANALYSIS.md`;
- `docs/a52-camera/HARDWARE-BLOCKERS.md`;
- `docs/a52-camera/CAMERA-SERVICE-API.md`;
- `docs/a52-camera/DEPLOYMENT-AND-ROLLBACK.md`;
- `firmware/s10plus/manifest.yml` and all four firmware scripts;
- kernel build wrapper, kernel config fragments and existing S10+ patches;
- current camera PWA, Photos app, bridge and broker.

Mark old findings as historical when not re-proven. Update rather than erase evidence.

### 4.2 Phone state

Collect into a timestamped evidence directory:

- `/proc/version`, `uname -a`, `/proc/cmdline`, running DT model/compatible;
- live kernel configuration (from `/proc/config.gz`, `/boot/config-*`, build artifacts or exact extraction method); include hash and source;
- `rpm -qa` subset for media, PipeWire, GStreamer, libcamera and camera-related packages;
- `/dev/video*`, `/dev/media*`, `/dev/v4l-subdev*`, `/dev/bus/` and relevant character-device permissions;
- `/sys/class/video4linux/*/name`, device symlinks, driver links and `/sys/dev/char` mappings;
- media topology if `media-ctl` exists, and exact tool version;
- platform driver bindings, sensor device nodes, CSI PHY, OIS, EEPROM, reserved memory, ION heaps and IOMMU state;
- `dmesg` from boot and camera-probe attempts, filtered but with full raw capture retained;
- firmware request/loading errors and every firmware file's exact path/size/hash;
- camera-related services, process trees, D-Bus names, PipeWire and portal status;
- current app and bridge status, storage state and permissions configuration.

Do not log serial numbers, IMEI, subscriber identifiers, Wi-Fi passwords, user credentials, private keys or unrelated personal data. Redact unique identifiers in shared reports.

### 4.3 Existing product state

Preserve these already implemented components unless a concrete defect is demonstrated:

- `pwa/nuxel-apps/camera-gallery` Camera UI;
- `pwa/nuxel-apps/photos` Photos gallery;
- `services/nuxel-bridge` camera/media-store verbs;
- private camera broker `org.nuxel.Camera` (not the standard freedesktop portal name);
- camera permission policy and permission manager integration;
- file-backed media store and Photos thumbnail/open/delete path.

The user-visible app should become backed by real frames. Do not rewrite all of it as a native app just because the hardware layer is difficult.

## 5. Backup and deployment safety

Before changing firmware, kernel, device tree, services or access-control rules:

- Create a timestamped device backup for every changed file and unit.
- Record current file permissions, ownership, SELinux labels if applicable, hashes, symlink targets and service enablement.
- Record exact current kernel image and DTB build ID/hash and establish the current boot/restore path.
- Verify recovery access and the exact restore artifact before any boot image deployment.
- Preserve the current known-good kernel build and current boot image.
- Keep the current FIMC-IS driver behavior as a rollback baseline.
- Do not write to modem, EFS/EFSG, persist, param/up_param, steady, keystorage, carrier, CP debug, calibration EEPROM, secure storage or user-data partitions.
- Never run broad `dd` or flash commands generated by guesswork.

The existing `kernel/s10plus/build-kernel.sh` pins the downstream source and builds the S10+ image. Inspect its exact behavior before invoking it; it may clone/patch/build and apply the default Nuxel kernel fragment. Use a separate camera experiment config/profile rather than silently replacing the established default kernel profile.

If a kernel modification must be deployed to test a real stream, the operation is in scope after all safeguards pass. Back up the exact boot partition/image, validate the built image and DTB against the target, verify boot-chain packaging, verify restore instructions, and flash only the intended boot/kernel artifact. Do not touch the vendor/system/modem partitions merely to install a camera app or a blob. Do not wipe data. If the restore path is not verifiable, continue offline and report the specific blocker rather than risking an unrecoverable phone.

---

# PART III — CORRECT CAMERA HARDWARE DIAGNOSTICS

## 6. Make the 84000 mplane diagnostic authoritative

### 6.1 Audit the current code before reworking it

Inspect the current `nuxel-v4l2-probe.py` and the deployed phone version. The 84000 report says the tool was rewritten with ctypes-correct mplane structures, but verify:

- V4L2 ioctl request values/encoding match the target's 64-bit ARM UAPI;
- structure sizes, alignment, unions and pointer fields match the target kernel headers;
- `VIDIOC_QUERYCAP` uses `device_caps` when `V4L2_CAP_DEVICE_CAPS` is set;
- each node's actual queue direction and capabilities are interpreted correctly;
- mplane queue type value is 9 (`V4L2_BUF_TYPE_VIDEO_CAPTURE_MPLANE`), not 1;
- every related format and buffer ioctl consistently uses the same queue type;
- the mplane `v4l2_buffer.m.planes` pointer is valid for the lifetime of each ioctl and `length` is the actual number of plane structures;
- structure padding/`__aligned_u64` behavior is correct on AArch64;
- `bytesperline`, `sizeimage`, per-plane `bytesused`, `length`, `data_offset` and offsets are handled independently;
- timeout and cleanup paths always try `STREAMOFF` and release queued buffers;
- a failed `ENUM_FMT` is represented accurately, not as an empty list without errno.

Do not rely exclusively on manually reconstructed ioctl layouts. Build a small C diagnostic using the UAPI headers from the exact kernel source or a header set proven ABI-compatible with that kernel. The C utility should produce structured JSON plus readable trace lines. Python may orchestrate it and present the results.

### 6.2 Probe before capture

For each candidate endpoint:

1. Resolve node by sysfs/driver and source role; do not use a remembered `/dev/videoN` as identity.
2. Open read-only or non-mutating where possible for initial `QUERYCAP` and enumerate capabilities.
3. Record `driver`, `card`, `bus_info`, `version`, `capabilities`, `device_caps`.
4. Query format with the correct type. Use `VIDIOC_G_FMT` before modifying format.
5. Enumerate every format and supported frame size/interval where the driver supplies it.
6. Use `VIDIOC_TRY_FMT` for each carefully selected supported tuple if implemented; only then attempt `S_FMT`.
7. Record exact ioctl number, buffer type, structure size, return value and errno.
8. Distinguish unsupported ioctl, wrong queue, wrong node role, wrong format, invalid state, missing setup, missing firmware and hardware fault.

Do not assume NV12, NV21, YUYV, RAW10/RAW12, 640x480 or 1280x720. Obtain the real formats from exact source/vendor metadata and valid enumeration. A RAW Bayer path may require a sensor/ISP path not yet configured; it must not be presented as a final processed preview unless a valid processing route exists.

### 6.3 Bounded buffer proof

Only when the exact node is proven to be the real image capture endpoint and all required initialization is performed:

- Try a small bounded number of buffers (start with 2 or 3).
- Use the supported memory model (`MMAP`, `DMABUF` or other exact-source-supported choice); do not force DMA-BUF merely because it is desirable.
- Correctly calculate/map each plane separately when required.
- Verify DMA ownership, cache synchronization and device/IOMMU compatibility.
- Queue buffers with fully initialized structures and correct per-plane arrays.
- Start streaming only after sensor/CSI/ISP state is confirmed initialized.
- Dequeue with a finite deadline; record frame sequence, timestamp, flags, per-plane bytesused and actual image layout.
- Stop streaming and release all buffers on success, failure, timeout, signal or process exit.
- Never leave the device streaming after an unsuccessful test.

A successful `S_FMT` or `REQBUFS` is not a frame. Only `DQBUF` returning image bytes that decode to a genuine, changing view of the physical scene advances the mission to `CAPTURE_VERIFIED`.

### 6.4 Node-selection discipline

Do not open all `/dev/video*` endpoints with streaming requests. FIMC-IS exposes internal processing/metadata/virtual-channel nodes, and MFC/JPEG/scaler/GDC devices share the V4L2 namespace. Build a node classifier from exact driver source and sysfs metadata. Camera diagnostics must explicitly skip:

- MFC decode/encode nodes (`video6`–`11` historical labels);
- JPEG M2M (`video12` historical label);
- scaler M2M (`video50` historical label);
- GDC M2M (`video155` historical label);
- metadata/VRA/virtual channels unless the source explicitly identifies a needed part of the camera graph.

Do not regress the known working MFC path or its firmware policy.

### 6.5 Diagnostic status taxonomy

Emit explicit machine-readable outcomes, at minimum:

```text
NODE_NOT_PRESENT
WRONG_NODE_ROLE
PERMISSION_DENIED
QUERYCAP_FAILED
STANDARD_MPLANE_SUPPORTED
STANDARD_MPLANE_FORMAT_ENUM_EMPTY
STANDARD_MPLANE_FORMAT_NEGOTIATION_FAILED
STANDARD_MPLANE_UNSUPPORTED
BUFFER_ALLOCATION_FAILED
BUFFER_QUEUE_FAILED
STREAM_START_FAILED
STREAM_TIMEOUT
FRAME_DEQUEUED
FRAME_DECODE_FAILED
MISSING_FIRMWARE
FIRMWARE_HASH_MISMATCH
FIRMWARE_REQUEST_PATH_MISMATCH
SENSOR_POWER_FAILURE
SENSOR_I2C_FAILURE
CSI_LINK_FAILURE
ISP_BOOT_FAILURE
SECURE_CAMERA_TEE_FAILURE
MEDIA_GRAPH_NOT_EXPOSED
PRIVATE_UAPI_REQUIRED
CAPTURE_STREAM_VERIFIED
```

Each status must identify the exact failing stage and supporting evidence. Do not collapse all failures into `HARDWARE_BLOCKED`.

---

# PART IV — FIRMWARE, SETFILES AND CALIBRATION

## 7. Restore exact S10+ camera firmware

### 7.1 Use the pinned source of record first

The existing Nuxel fetcher identifies:

```text
Linux4/proprietary_vendor_samsung
05c9ef8f16e0ad5ab274e408c120dfd99fd5c628
```

The matching firmware tree includes `exynos9820-common/proprietary/vendor/firmware/` and `beyond2lte/proprietary/vendor/firmware/` paths. Use the existing fetcher only after auditing its implementation and hash validation. Improve it where necessary:

- `curl --fail --location --silent --show-error` (or equivalent) so HTTP errors cannot be saved as firmware files;
- validate GitHub API response, tree SHA and pinned commit before iterating;
- detect API pagination/truncation/rate-limit responses and fail closed;
- preserve source-relative directories where paths overlap;
- require non-zero, plausible file sizes;
- calculate SHA-256 and compare with the manifest/source evidence;
- write to `.tmp`, verify, then atomically rename;
- produce a machine-readable provenance manifest with source URL, repository, commit, path, byte size, SHA-256 and destination mapping;
- never silently accept a changed upstream branch or latest release instead of the pinned commit.

If the pinned source is unavailable or a checksum mismatch occurs, investigate. Do not downgrade validation or silently fetch a different branch.

### 7.2 Required camera firmware profile

Create or extend a separate S10+ camera firmware verification mode. Do not change generic `required:false` semantics for all Nuxel targets. Once exact kernel/HAL source confirms which camera files are required, make those files required for the S10+ camera profile and fail closed if absent/wrong.

The likely core group includes:

```text
fimc_is_fw_mcu.bin
fimc_is_lib.bin
fimc_is_rta.bin
fmsb.bin
rxse.bin
txse1.bin
txse2.bin
txse3.bin
dnn.bin                  # only if source confirms it is used by the required path
setfile_2l4.bin
setfile_3m3.bin
setfile_3p9.bin
setfile_3j1.bin
setfile_4ha.bin
```

Add dual-camera calibration files only to the features that require them and only when exact camera configuration/source indicates that dependency. Do not make dual-camera-only features block single rear-main capture unless the actual driver/HAL requires them.

**Do not put `vts.bin` into the camera required set simply because the old manifest grouped it under `camera_isp`.** Audit/correct the manifest category: VTS is voice-trigger DSP/audio-related in this device's firmware inventory. Preserve existing audio behavior.

### 7.3 Determine the exact runtime lookup path

The manifest historically maps many blobs to `/lib/firmware`, while the device inventory noted the former Android vendor location `/vendor/firmware` was absent in Nuxel. Do not assume either path is correct for the camera driver.

Read the exact pinned kernel and vendor userspace source for every firmware load:

- `request_firmware()` names and device context;
- `request_firmware_direct()` or async firmware helpers;
- direct `filp_open()` / `kernel_read()` paths;
- Android vendor hardcoded path assumptions;
- fallback paths, path prefixes and firmware class search order;
- request timing (probe, sensor power-up, ISP boot or stream-on);
- firmware filename construction based on sensor slot/module/revision;
- whether blobs are uploaded by the HAL rather than loaded by the kernel.

Trace kernel logs and/or instrument the exact firmware request point. Stage the blob under the path actually consumed. If a vendor HAL reads `/vendor/firmware`, decide whether to provide a narrow compatibility path/bind mount or configure the HAL appropriately. Do not create misleading symlink forests before proving the requested names.

### 7.4 Exact sensor setfile pairing

Build an explicit table from actual hardware and the matching camera source:

| Module | Expected sensor file | Must verify |
|---|---|---|
| Rear-main 2L4 | `setfile_2l4.bin` | sensor ID, revision, modes, source/hash |
| Rear tele 3M3 | `setfile_3m3.bin` | sensor ID, revision, modes, source/hash |
| Rear ultra-wide 3P9 | `setfile_3p9.bin` | sensor ID, revision, modes, source/hash |
| Front-main 3J1 | `setfile_3j1.bin` | sensor ID, revision, modes, source/hash |
| Front depth/IR 4HA | `setfile_4ha.bin` | sensor ID, revision, modes, source/hash |

Verify the physical module ID/device-tree compatible, kernel sensor driver and vendor setfile selection logic. Do not map based solely on marketing camera order, device-tree alias name, or an old `camera.json` candidate list.

Check the suspicious identical manifest hash for `setfile_3j1.bin` and `setfile_4ha.bin` against the pinned repository tree and generated manifest. Record exact file sizes and content hashes; if the source actually has identical bytes, explain why the matching HAL expects the same payload. If the manifest was generated incorrectly, fix the generator/source mapping and tests.

### 7.5 Read-only extraction from the owner's own stock firmware as a fallback

If the pinned public source is incomplete or has a mismatch with this exact device firmware revision, inspect the existing owner-owned stock vendor partition using the repository's documented TWRP pull mode. The Nuxel README describes `--twrp-pull` as read-only acquisition with device identity checks. Re-audit the script before using it.

Requirements:

- verify the target is `beyond2lte` / SM-G975F using device properties and known bootloader/vendor build IDs;
- mount/read the relevant partitions read-only;
- perform `adb pull` only;
- do not flash, wipe, remount read-write or modify EFS/calibration/security partitions;
- retain source build fingerprint and SHA-256 provenance;
- compare local hashes with the pinned source and current installed image;
- keep proprietary binary data local and excluded from Git.

Never pull firmware from a different phone and call it a match. Never use `beyond1lte`, `beyondx`, Snapdragon S10, Exynos 9825 Note10, or a random device's camera setfiles as substitutes.

### 7.6 Calibration and actuator policy

The old hardware inventory records EEPROM devices, OIS actuators and OIS controller. These are not decorative peripherals:

- identify each EEPROM's sensor/module role from exact source/DT;
- check whether the HAL reads calibration from EEPROM, a file, or both;
- keep original calibration untouched and read-only during investigation;
- verify checksum/length/version before passing calibration into a vendor component;
- do not fabricate calibration defaults for OIS/lens alignment;
- do not run actuator/OIS commands outside the documented driver control path;
- do not overwrite EEPROM, calibration data or persistent camera parameters.

A first basic rear-main capture can proceed without fully enabling every OIS or dual-camera feature only if the driver/HAL supports that mode safely. Never disable an essential calibration requirement merely to get an image.

---

# PART V — EXACT KERNEL DRIVER AND HARDWARE PIPELINE AUDIT

## 8. Fetch and inspect the exact downstream kernel source

The repository build wrapper identifies this source pin:

```text
Repository: https://github.com/Linux4/android_kernel_samsung_exynos9820
Commit:     f7194c1d15eded1c2a1a4dc63825b26103435cc0
Defconfig:  exynos9820-beyond2lte_defconfig
Kernel:     downstream Linux 4.14.253
```

Verify the current wrapper and the live kernel build ID against this before use. If current source/commit differs, use the actual current build's source of record and clearly explain why.

Inspect the complete relevant tree, not only one file. Search for:

```text
VIDEO_EXYNOS_FIMC_IS2
exynos-fimc-is
fimc_is
fimc-is-video
fimc-is-interface
fimc-is-core
fimc-is-device
fimc-is-cis
fimc-is-sensor
fimc-is-hardware
fimc-is-firmware
fimc-is-vb2
fimc-is-video-
VIDIOC_
video_ioctl2
v4l2_ioctl_ops
vb2_ops
vb2_queue
request_firmware
fimc_is_fw_mcu.bin
fimc_is_lib.bin
fimc_is_rta.bin
setfile_
MEDIA_CONTROLLER
media_device_register
media_entity_pads_init
v4l2_async
subdev
ION
DMA-BUF
IOMMU
SMC_SECCAM
```

The actual source paths may differ. Search by symbols, not assumed filenames.

## 9. Build a full driver-state map

Produce a source-referenced state diagram and table for the complete rear-main capture path:

```text
Camera app / Nuxel service
    -> user-space camera API / Samsung-private API (if any)
    -> FIMC-IS video-node or control endpoint
    -> FIMC-IS firmware/MCU/library initialization
    -> sensor slot + sensor subdevice + setfile
    -> sensor power/clock/reset and I2C control
    -> MIPI CSI-2 PHY/receiver, lane count/link frequency/VC
    -> FIMC-IS ISP/processing graph
    -> capture endpoint and vb2 queue
    -> DMA/ION/IOMMU buffer
    -> completed frame
    -> Nuxel stream transport
```

For each hop, record:

- source file and symbol/line range;
- initialization owner (kernel driver, HAL or service);
- exact input/output structure or ioctl/control;
- expected state transition and completion event;
- firmware/data dependency;
- device-tree dependency;
- clock/regulator/pinctrl/GPIO dependency;
- memory type and allocator;
- failure errno/log message;
- how to test safely without breaking another camera or media subsystem.

### 9.1 Kconfig and media-controller reality

The old live evidence says `CONFIG_VIDEO_EXYNOS_FIMC_IS2=y` was enabled while `CONFIG_MEDIA_CONTROLLER` was unset. Re-read the current config first. Then:

1. Inspect the exact `drivers/media/.../Kconfig` and `Makefile` for FIMC-IS2.
2. Determine whether this driver has media-controller code compiled conditionally or simply lacks a media-device implementation.
3. Determine whether V4L2 subdevice support, async notifier, vb2, DMA-contig, DMA-BUF, ION or other Android downstream allocator interfaces are needed.
4. Inspect the current DT: `ports`, `endpoint`, `remote-endpoint`, `data-lanes`, `clock-lanes`, `link-frequencies`, virtual channels, sensor `reg`, GPIOs, regulators, clocks and reserved-memory nodes.
5. Compare with the Samsung source tree's working `beyond2lte` DT and vendor configuration, not with a different Exynos family.
6. If config enables a media surface, prove the driver actually registers `media_device`, entities, pads, links, async sensor binding and subdevice devnodes.

Do not assume `CONFIG_MEDIA_CONTROLLER=y` is the fix. It may be a prerequisite, but code must register the graph. Conversely, if the driver internally sets up the pipeline from a single video endpoint, an external media graph may not be needed for an initial proof.

### 9.2 V4L2 ioctl and private UAPI audit

For every FIMC-IS video node that matters, inspect its actual `v4l2_ioctl_ops` and `video_device` registration:

- Does it advertise `V4L2_CAP_VIDEO_CAPTURE_MPLANE`?
- Are `vidioc_querycap`, `vidioc_enum_fmt_vid_cap_mplane`, `vidioc_g_fmt_vid_cap_mplane`, `vidioc_try_fmt_vid_cap_mplane`, `vidioc_s_fmt_vid_cap_mplane`, `vidioc_reqbufs`, `vidioc_querybuf`, `vidioc_qbuf`, `vidioc_dqbuf`, `vidioc_streamon` and `vidioc_streamoff` present?
- Do the ops delegate to a Samsung-specific state machine that requires other controls first?
- Is a different queue type used on input/output/metadata nodes?
- Are private `VIDIOC_PRIVATE` or extended control IDs defined? What exact header/ABI owns them?
- Are private controls exposed through `VIDIOC_S_EXT_CTRLS`, `VIDIOC_G_EXT_CTRLS`, standard control handlers or vendor-specific `ioctl` callbacks?
- Does opening the capture endpoint require a prior sensor-slot allocation, pipeline resource acquisition, firmware setup, group ID, stream ID, or frame manager initialization?
- Which user-space layer normally performs this sequence?

Build a typed header from authoritative source definitions. If an ioctl is private, give it a unique named wrapper and a struct with compile-time size/offset assertions. Do not manually calculate `_IOC` numbers from a blog or a different kernel revision. Never test random private ioctl values against a live device.

### 9.3 Sensor, CSI and ISP initialization

Trace exactly:

- sensor subdevice matching and `probe()`;
- I²C sensor ID read and expected ID/revision;
- rails/regulators, GPIOs, clocks, pinctrl and reset sequencing;
- sensor mode table / setfile application;
- CSI PHY/receiver lane/clock/virtual-channel configuration;
- ISP MCU boot and firmware upload;
- shared memory / DDK / RTA initialization;
- interface/command queue, interrupt and completion handling;
- stream group/resource allocation;
- output node format, dimensions, crop, stride and plane count;
- buffer allocator and IOMMU mapping;
- frame completion/metadata and error reporting;
- teardown and runtime PM.

Do not power on all modules at once. Start with rear-main 2L4 only. Leave other sensor slots untouched until a repeatable main-camera stream exists.

### 9.4 Secure camera / TEE path

The inventory says the secure-camera SMC setup succeeded historically. Determine whether the normal non-secure still/video capture path depends on:

- secure camera memory initialization;
- secure monitor calls;
- protected camera buffer heaps;
- secure/non-secure pipeline selection;
- TrustZone resource ownership;
- firmware authentication or signature checks.

Do not disable the secure monitor, delete secure memory reservation, fake successful SMC return values, or route protected camera buffers through untrusted memory. Use the existing secure/non-secure modes exactly as the vendor source intends. If non-secure capture is supported, prove it through source and hardware testing.

---

# PART VI — IMPLEMENTATION PATHS

## 10. Phase 1: prove the existing native V4L2 path

Create `tools/s10plus/camera86000/` (or an appropriate repository location) for versioned diagnostics. Include:

- a C `nuxel-camera-uapi-probe` compiled against exact target UAPI headers;
- a node/topology resolver based on sysfs, not fixed node numbers;
- a read-only query/format report;
- a separate explicit capture command requiring an affirmative flag;
- timeout, signal-safe cleanup, bounded buffers and structured JSON;
- unit tests/fixtures for node roles, single-planar and mplane structs, 64-bit offsets, pointer layout and error reporting;
- a hardware diagnostic report with kernel commit, headers hash and executable hash.

Run the corrected query/format path on the exact rear-main capture node. If standard mplane is accepted, proceed to the bounded capture proof. If it fails, inspect the exact driver's callback table and state requirements before declaring the standard path unsupported.

**Do not try standard ioctls on all internal nodes with mutating calls.** Query capabilities first and select only the source-proven image output endpoint.

### 10.1 If standard V4L2 works

Complete a minimal rear-main single-frame C proof:

1. Initialize the sensor/ISP using the proven public interfaces/controls.
2. Enumerate and select a supported size/format.
3. Allocate 2–3 buffers through the driver's supported memory model.
4. Queue and stream.
5. Dequeue a completed frame.
6. Save a raw payload with a sidecar describing FOURCC, plane offsets, strides, dimensions and colorimetry.
7. Convert/decode using a known-correct tool/library.
8. Inspect the image; confirm it shows the physical scene and correct orientation.
9. Capture another frame after physically changing the scene; verify the data changes in a meaningful way.
10. Stop and release hardware cleanly.

If this works, move directly to the Nuxel service work. Do not write a replacement kernel driver for a path already working.

## 11. Phase 2: implement the existing Samsung FIMC-IS2 interface if required

If source proves the pipeline needs a private userspace sequence:

### 11.1 Build the smallest possible native PoC

- Use C, exact target source headers, explicit structure definitions and compile-time ABI assertions.
- Keep each hardware operation in a named function (`open_device`, `acquire_sensor_slot`, `boot_isp`, `configure_sensor`, `configure_csi`, `configure_capture_node`, `allocate_buffers`, `start_stream`, `dequeue_frame`, `stop_stream`, `release_resources`).
- Add trace logging for every request/response, state, return code and timing.
- Keep all timeouts bounded; do not allow unbounded waits on the UI thread.
- Do not hide errors with fallback defaults; unknown values fail closed.
- Start with rear-main 2L4 only.

### 11.2 Derive the command sequence from the actual Samsung source

Use the exact driver and matching Android HAL source/binaries as evidence. Determine whether the HAL:

- issues private ioctls to allocate/configure sensor slots;
- uses V4L2 extended controls for stream parameters;
- sends `setfile`/firmware data to the kernel via an ioctl or firmware file path;
- allocates buffers with ION or another vendor allocator and imports DMABUF FDs;
- uses a camera request manager, frame manager or group/shot metadata structure;
- configures a sensor pipeline through a specific chain of nodes;
- sets up OTF versus DMA paths;
- uses JPEG/GDC/MCFP/TPU processing blocks for the mode;
- depends on Android camera metadata/camera3 stream configuration.

Create an ABI note that maps each operation to source lines/header structures. No guessed sequence.

### 11.3 Wrap the proven path

When the PoC can repeatedly capture a frame, create a supported integration layer:

- Prefer a stable, narrow internal C API for the kernel-facing sequence.
- Keep privileged device ownership in one daemon.
- Export only the required camera operations to the UI through the existing bridge/private broker.
- Use a single exclusive lock for the physical camera pipeline to prevent another app or service from opening it concurrently.
- Add robust service shutdown and cleanup, including handling app crash, daemon restart, user logout, suspend and device removal.

Only after the low-level PoC is repeatably successful should you consider writing a libcamera pipeline handler. It should model the S10+ as a real camera with sensor-specific streams, formats, controls, metadata, buffer lifecycle, frame sequence and camera acquire/release. It must not call a test pattern or hardcoded `/dev/video111` path as if it were a camera.

## 12. Phase 3: patch the existing kernel driver if required

If existing V4L2/private UAPI is incomplete, patch the existing FIMC-IS2 source in the pinned downstream kernel. Prefer targeted changes over an entire rewrite.

### 12.1 Build a camera-only experiment profile

- Leave `kernel/s10plus/configs/nuxel-drm-kbase.fragment` and the known-good default build profile intact.
- Add a documented camera-experimental fragment/profile with only symbols required by the exact FIMC-IS2/media/CSI/V4L2/vb2/firmware implementation.
- Inspect exact Kconfig dependencies first; use `olddefconfig` and diff the resolved config.
- Verify final `.config` has every intended symbol and no unexpected unrelated changes.
- Save `savedefconfig`/config diff and compiler/toolchain hashes.
- Preserve kbase/Mali, UDMABUF behavior, DECON/fbdev, audio/ABOX, MFC, Wi-Fi/BCMDHD, Bluetooth, NFC, input, touch, sensors, suspend/resume and user namespaces.
- Do not enable unrelated camera drivers because the names look similar.

If a built-in `CONFIG_VIDEO_EXYNOS_FIMC_IS2=y` driver must be modified, change/build that exact in-tree source. Do not compile a duplicate module and expect it to replace a built-in instance.

### 12.2 Kernel patch goals

Depending on source findings, implement the minimum set of missing behavior:

- standard multi-planar capture queue if currently incomplete;
- explicit supported FourCC, frame-size and frame-interval enumeration;
- correct `v4l2_ioctl_ops` and `vb2_ops`;
- complete vb2 buffer setup/prepare/queue/finish/release functions;
- correct MMAP/DMABUF support using the real allocator and importer/exporter path;
- cache synchronization, IOMMU maps/unmaps and buffer ownership;
- media-controller entities/pads/links only where the hardware graph supports them;
- sensor and CSI subdevice format/control paths if supported;
- per-sensor asynchronous binding and error unwind;
- controls for exposure, gain, focus, zoom, flash, frame rate and orientation only when hardware/source proves they exist;
- proper interrupt/completion processing and frame timestamps;
- clean stream stop, runtime PM and suspend/resume;
- clear `dmesg` diagnostics for each stage and errno.

A userspace compatibility layer for a private HAL API is acceptable if a standard media graph cannot safely represent the vendor's existing path. The objective is a secure and maintainable working camera, not forcing a fashionable abstraction at the cost of hardware correctness.

### 12.3 Build verification off-device

Before deployment:

- build against the pinned source commit and exact target defconfig/config fragment;
- verify compiler, linker, cross-prefix and environment;
- preserve the existing toolchain workarounds but do not suppress new driver warnings without investigation;
- compile all changed objects and image/DTB successfully;
- run static checks and kernel self-tests where practical;
- inspect symbols and module versions where applicable;
- compare the new configuration against the current live config;
- compare DTB changes; do not add guessed endpoints or clocks;
- extract/check the output image/DTB and ensure packaging matches the current boot image method;
- verify the new kernel retains the known-good non-camera hardware configuration.

### 12.4 Controlled physical deployment

If the only way to test the driver is a new boot image, deployment is in scope after the exact rollback path is verified:

1. Back up the exact current boot image/partition to two independent host locations and verify both hashes.
2. Record current DTB and boot image identities.
3. Verify the recovery/TWRP/Download-mode path and owner access.
4. Verify the new image is built for the exact SM-G975F/beyond2lte target, not another Exynos device.
5. Verify boot image packaging, kernel compression, DTB selection and boot header expectations.
6. Confirm no modem, vendor, EFS, calibration or user-data image is included in the write.
7. Flash only the intended boot/kernel artifact using the already documented device workflow.
8. Immediately verify boot, display, touch, Wi-Fi SSH, sound, MFC, thermal state and existing services before camera tests.
9. If any existing critical function regresses, restore the exact backup using the verified path.

Never make a camera test depend on wiping or replacing the whole root filesystem. Never test an unverified kernel with no rollback artifact.

## 13. Phase 4: write a driver from scratch if necessary

This route is explicitly allowed, but it is the final engineering fallback after the existing driver and exact vendor stack have been studied.

### 13.1 Mandatory go/no-go design record

Before coding a new kernel driver, write `docs/pwnage-86000/DRIVER-REWRITE-DECISION.md` showing:

- what the pinned FIMC-IS2 driver does and why it cannot be reused/extended;
- exact failed interfaces and source lines;
- which parts of the existing driver can be reused;
- whether the replacement is a new sensor/CSI driver, an ISP driver, a video queue bridge, or a complete pipeline driver;
- hardware registers/resources involved and source of every definition;
- secure-camera/TEE dependencies;
- DMA/IOMMU/reserved-memory contract;
- expected device-tree changes;
- risks to display/audio/MFC/Wi-Fi/power;
- build/test/rollback plan.

Do not create a monolithic “camera driver” if the actual work is a single missing queue or a userspace state machine. Split driver responsibilities along real hardware blocks.

### 13.2 New driver architecture

Where needed, design a clean Linux media driver using the actual 4.14 kernel APIs—not modern kernel API calls copied from current documentation. It must include:

- a platform driver matched to the exact Exynos9820 device-tree compatible;
- explicit clock/regulator/reset/pinctrl/PM handling;
- sensor subdevice integration or a source-backed sensor control interface;
- correct MIPI CSI-2 receiver/PHY setup;
- FIMC-IS firmware/MCU/ISP boot and error reporting;
- media device, entities, pads and links if the pipeline is modelled through MC;
- V4L2 video device and `video_ioctl2`/ioctl ops;
- multi-planar formats and correct `v4l2_pix_format_mplane` structures;
- vb2 queue lifecycle and safe buffer allocation;
- DMA API/IOMMU/DMABUF ownership and cache synchronization;
- interrupt handling and frame-completion events;
- explicit controls and metadata;
- resource arbitration between multiple sensor/capture contexts;
- stream stop/error recovery and complete resource unwind;
- runtime PM and suspend/resume correctness;
- clear `dev_err`/debug diagnostics and tracing;
- kernel documentation, ABI documentation and tests.

If the ISP's firmware protocol is proprietary, use the exact version-matched firmware and protocol source/reference. Do not attempt to replace Samsung ISP firmware with an invented open implementation in this mission. A new Linux driver may be a Linux-facing driver around the existing firmware processor; it is not permission to guess undocumented MCU firmware commands.

### 13.3 Safe reverse engineering boundaries

Permitted:

- read and analyze the exact open-source kernel driver and matching owner-authorized vendor metadata;
- inspect device-tree values, register definitions and logs;
- trace ioctl sequences and firmware request points;
- instrument source with debug logs;
- compare matching device trees/build manifests;
- read non-secret sysfs/debugfs information;
- perform bounded tests using documented operations.

Not permitted:

- blind I²C or MMIO writes;
- arbitrary register sequences copied from different SoCs;
- dumping protected/secure-camera memory;
- disabling TrustZone/secure-camera enforcement to “make it work”;
- bypassing sensor overtemperature/current protections;
- overwriting EEPROM or camera calibration;
- loading firmware of unknown provenance/version;
- leaving DMA enabled after buffers are freed;
- running all sensor slots simultaneously to discover which one reacts.

---

# PART VII — EXACT ANDROID VENDOR FALLBACK

## 14. Inspect the matching Samsung camera HAL stack

The exact-device vendor inventory provides a concrete list to inspect. Start with the current device's installed Android firmware/vendor version and corresponding device tree/manifest. The public `lineage-17.1` blob list is historical evidence; the currently supported branch or stock image may use different versioned files.

### 14.1 Identify full dependency closure

Inventory, where present:

- `vendor.samsung.hardware.camera.provider@3.0-service` binary and init rc;
- `camera.exynos9820.so` in the correct 32-bit/64-bit directory;
- vendor provider implementation library;
- camera.device HIDL interface libraries and implementations;
- `libexynoscamera3.so`;
- Samsung camera dependencies (`libacryl`, `libcsc`, dual-camera/refocus libraries, `libgiantmscl`, JPEG helpers, sensor listener, uniapi/uniplugin, vendor Vulkan/graphics dependencies);
- hardware allocator/gralloc/ION dependencies;
- required Android framework camera service/metadata/runtime libraries;
- vendor service manager and Binder/HwBinder devices;
- init rc properties, service classes, user/group and capability configuration;
- SELinux policy and device-node labels/permissions;
- TEE/secure-camera services and firmware;
- any required power/sensor listener/thermal services.

Run dependency tools (`readelf -d`, `lddtree` where appropriate, symbol scans, service manifests, init rc inspection) on the exact artifacts. Do not execute a vendor service on the host glibc process and assume it will load correctly.

### 14.2 Verify ABI generation

AOSP camera HAL documentation states that Android 8+ uses binderized HIDL for the HAL and Android 13+ supports AIDL for new HAL development while still supporting legacy HIDL HALs. The `beyond2lte` device blob list found during research specifically identifies a Samsung `camera.provider@3.0` service. Determine what the exact currently installed vendor build uses.

Do not convert the provider interface to AIDL by assumption. Do not replace the camera provider with a mock. Use exactly the vendor interfaces and versions the binary expects.

### 14.3 Runtime fallback architecture

If the Android vendor HAL is the only working camera path, evaluate a separate, minimal Android vendor runtime rather than contaminating Fedora:

- keep Android Bionic libraries, service-manager/HIDL support, properties and vendor services in an isolated rootfs/container/chroot/mount namespace compatible with the device;
- pass through only the required camera device nodes, firmware, memory heaps and IPC endpoints;
- maintain device ownership and security labels deliberately;
- prevent the Android runtime from replacing Nuxel systemd, Phoc, graphics, audio, networking, or other core services;
- ensure only one camera manager owns the physical camera at a time;
- export frames to Nuxel through a narrow AF_UNIX socket, memfd/shared memory, DMA-BUF FD passing or another proven low-copy transport;
- define a versioned, typed bridge API with frame metadata, timestamps, dimensions, pixel format and lifecycle;
- validate size/stride/plane counts and every incoming message length;
- restrict the service to a dedicated user/group and only the camera capabilities it needs;
- prevent Android camera provider from recording in the background without the Nuxel user's explicit action and visible indicator.

Investigate Halium/libhybris as a reference ecosystem. But note that `libhybris` is a compatibility approach for Bionic-linked Android libraries within glibc/musl Linux processes; that statement alone does not prove compatibility with this device's binderized Samsung HIDL provider. Test the exact API, services, symbols, binder model and buffer allocator. If a minimal Android userspace/container is more reliable, implement that instead.

### 14.4 The fallback must still feed Nuxel

The Android stack is not the user-facing product. The user must still be able to open the Nuxel Camera app, see a preview, take a picture, record video, and browse the results in Nuxel Photos. Android Settings or the Android camera app appearing in a container is not mission completion.

---

# PART VIII — NUXEL CAMERA SERVICE AND APPLICATION INTEGRATION

## 15. Preserve and complete the existing camera contract

The current repo's `docs/a52-camera/CAMERA-SERVICE-API.md` specifies:

- system bus bridge: `org.nuxel.Bridge` for camera status/media list/capture/open/delete;
- private session broker: `org.nuxel.Camera`;
- durable media store;
- permission-gated preview/capture;
- no claim to own standard `org.freedesktop.portal.Camera` unless a real freedesktop portal implementation is added;
- explicit lifecycle from authorization to stream and release;
- honest `NO_CAMERA`, `PERMISSION_DENIED`, `CAMERA_BUSY`, `LOW_STORAGE`, `THERMAL_PAUSE`, `DRIVER_UNAVAILABLE` states.

Keep this separation. Do not hijack the freedesktop portal well-known name with an incompatible API. When the pipeline becomes real, either:

A. implement a genuine standard camera path compatible with PipeWire/xdg-desktop-portal/WebKit `getUserMedia`; or  
B. retain a private Nuxel app-only stream endpoint and document its capability boundary.

If PipeWire and a real portal are selected, install/configure the proper portal interfaces and camera backend—not just a service with the expected bus name. Verify the web runtime actually sees the physical source.

## 16. Recommended Nuxel service architecture

Use one authoritative daemon to own the camera hardware. A suggested architecture (adapt to existing service conventions):

```text
Nuxel Camera PWA
   | permission request / camera status / select / capture / stream
   v
NuxelBridge (existing authenticated local bridge)
   | typed RPC / D-Bus
   v
org.nuxel.Camera (private broker / capture control)
   |
   +--> nuxel-camera-service (single hardware owner)
            |
            +--> native V4L2/private FIMC-IS2 adapter
            |       OR isolated exact Samsung camera runtime adapter
            |
            +--> frame transport (PipeWire source or authenticated local stream)
            +--> still/video encoder path
            +--> MediaStore
```

Requirements:

- no direct raw `/dev/video*` access from the PWA;
- no root-owned unlimited HTTP capture API;
- no user-facing camera preview until permission is granted;
- visible active-camera indicator while streaming/recording;
- explicit camera close when app exits, visibility changes, lock occurs or permission is revoked;
- exclusive camera lock and clean `CAMERA_BUSY` handling;
- no hidden camera/mic usage;
- no synthetic source except an explicit developer test mode clearly labelled `TEST SOURCE`;
- all frame buffers have bounds, formats, stride and timestamps validated;
- no unlimited base64 transport for full-resolution raw video frames;
- no remote network exposure of camera frames;
- no capture data uploaded externally;
- no GPS EXIF unless user enabled location tagging;
- audio microphone permission is separate from camera permission.

## 17. Video/frame transport decision

Compare real options and choose the least fragile path supported by the current Fedora/Phoc/WebKit build:

1. **PipeWire camera source**: ideal if the matching PipeWire/WirePlumber/portal/WebKit path is available and can publish the real camera format/buffers.
2. **libcamera integration**: suitable only after a custom FIMC-IS2 pipeline handler has a proven kernel interface. Implement real sensor discovery, configuration, controls, stream start/stop and buffer import/export.
3. **GStreamer pipeline**: viable if the exact plugin build supports the capture source/private source; do not assume `v4l2src` supports Samsung private calls.
4. **Private app bridge**: acceptable for a Nuxel-owned PWA when WebKit's portal path is unavailable. Use a tightly scoped per-session token, local-only endpoint, explicit stream permission, correct MIME/format and automatic expiry. Use low-copy/shared-memory transport for video where possible.
5. **V4L2 loopback**: only if the module is available, kernel-compatible and its security/permissions/lifecycle are sound. Do not make a loopback device look like a physical camera in diagnostics.

A test source may validate the UI transport, but it is never camera evidence. Every path must expose source identity and `synthetic=false` for the real physical device.

## 18. Still image pipeline

Once the first real frame is available:

- inspect the actual format, bit depth, Bayer pattern/YUV layout, planes, offsets, padding, stride and colorimetry;
- use proper demosaic/ISP output or hardware processing where the pipeline provides it;
- convert to JPEG through a correct libjpeg-turbo or proven Exynos JPEG path;
- use hardware JPEG node only after verifying its independent format/memory contract; do not assume MFC/JPEG M2M is part of the sensor path;
- preserve EXIF orientation and timestamps;
- do not invent sensor focal length, lens identity or camera intrinsics;
- write atomically through the existing file-backed media store;
- verify file magic/MIME/decode, dimensions and file hash;
- open the actual saved file in Nuxel Photos.

Store a test capture in the configured Nuxel media directory and preserve the existing media-store path policy. No photo may be silently discarded because of localStorage quota.

## 19. Video recording pipeline

After still capture is reliable:

- start with conservative video settings (for example 720p at a measured stable frame rate, only if the pipeline supports that mode);
- inspect actual supported sensor/ISP output sizes and frame intervals;
- use MFC hardware encoding only after proving the exact encoder path, firmware and queue format; preserve the already-working MFC configuration;
- use microphone audio only when the microphone permission is granted and the user starts recording;
- mux video/audio with correct timestamps and handle clock drift;
- show recording duration, active indicator, stop control, storage checks and errors;
- stop immediately on lock/app termination according to existing privacy design;
- save atomically and validate playback using `ffprobe`/`ffmpeg` or another reliable decoder.

A camera frame does not prove video encoding. A silent video does not prove mic capture. Track each separately.

## 20. Camera controls and multi-lens progression

Start with the rear-main 2L4 only. After repeated success, bring up one additional camera at a time:

1. Rear main 2L4 — first required camera.
2. Front main 3J1 — selfie preview and still capture.
3. Rear telephoto 3M3 — validate optical path/sensor switch.
4. Rear ultrawide 3P9 — validate sensor and correct field of view.
5. Front depth/IR 4HA — investigate actual function (depth, IR, assistance); do not promise normal RGB preview if it is not a normal RGB sensor.

Per-camera implementation should include:

- stable camera ID derived from hardware/module identity, not node number;
- camera name/lens-facing/role;
- supported formats, dimensions and frame intervals from actual driver data;
- exposure/gain/focus controls only where supported;
- physical lens switch that stops/releases prior pipeline before opening the next;
- per-module calibration/metadata;
- no false flash/zoom/AF capabilities;
- graceful unavailable states for features the module does not support.

Do not enable simultaneous multi-camera use until resource arbitration, memory bandwidth, ISP group configuration and thermal limits have been proven.

---

# PART IX — TESTING, SECURITY AND QUALITY GATES

## 21. Test ladder

Every stage needs a named gate, reproducible test and evidence artifact. Keep the distinction among `DISCOVERED`, `INITIALIZED`, `FORMAT_CONFIGURED`, `STREAMING`, `FRAME_CAPTURED`, `REAL_SCENE_VERIFIED`, `APP_PREVIEW_VERIFIED`, `STILL_SAVED`, and `VIDEO_SAVED`.

### Gate 0 — baseline

- verified target hardware/kernel/source;
- backup and rollback evidence complete;
- camera devices and services inventoried;
- no changes to working hardware.

### Gate 1 — firmware provenance

- each required blob exists in local staging;
- exact source repo/commit/path recorded;
- exact SHA-256 and size verified;
- manifest agrees with fetched bytes;
- driver request path and timing proven;
- no `vts.bin` accidentally required as camera firmware;
- sensor setfile mapping resolved including the 3J1/4HA checksum anomaly.

### Gate 2 — sensor and ISP initialization

- rear-main sensor I²C ID detected;
- correct sensor module bound;
- rails/clocks/GPIOs configured;
- CSI PHY/link ready;
- ISP firmware/library/RTA initialization reaches explicit success;
- no fatal firmware request, IOMMU, TEE or memory errors;
- every failure trace has an exact reason.

### Gate 3 — valid native or vendor capture configuration

- correct node identity;
- correct ioctl or vendor ABI;
- supported size/format successfully selected;
- buffers safely allocated/imported;
- stream-on acknowledged;
- no guessed or synthetic data.

### Gate 4 — first real frame

- dequeue completed frame with nonzero bytes;
- valid timestamps/sequence;
- frame decodes to an image;
- at least two captures made after physical scene movement show meaningful scene differences;
- human inspection confirms it is the live phone camera, not a cached/test image;
- write all raw and decoded evidence with metadata, but no private data.

This is the first true hardware milestone.

### Gate 5 — Camera app preview

- Nuxel Camera permission granted;
- app sees the real physical rear-main device;
- live preview updates continuously for at least 30 seconds;
- report actual resolution, fps, dropped frames, CPU, memory, temperature and stream transport;
- no UI freeze, excessive latency or stale single frame;
- permission revocation stops capture and releases hardware.

Target a conservative initial mode and publish measured results. A reasonable first target is a stable 720p stream at 15 fps or better; 30 fps is a follow-up target if the sensor/ISP/thermal pipeline supports it. Do not lie about fps or upsample and claim native sensor rate.

### Gate 6 — still capture and Photos

- physical shutter action triggers a fresh frame/capture request;
- JPEG/HEIF/other selected format is genuinely encoded and saved;
- correct dimensions and MIME are verified;
- image opens in Nuxel Photos;
- preview thumbnail and full-resolution image both work;
- metadata/EXIF valid and no GPS unless explicitly enabled;
- app restart/reboot retains saved media.

### Gate 7 — video and microphone

- record at least 10 seconds of real live scene;
- playback confirms changing footage and correct duration;
- verify frame rate, resolution and audio stream;
- audio exists only with microphone permission and explicit record action;
- no corruption on stop/exit/low storage;
- recording indicator is visible throughout.

### Gate 8 — reliability/regression

- 25 consecutive open/preview/close cycles;
- camera switching and repeated still capture;
- app crash/daemon restart cleanup;
- permission revoke during streaming;
- screen lock/unlock and display-off behavior;
- suspend/resume;
- reboot persistence;
- low-storage and device busy errors;
- sensor disconnect/failure handling;
- no lingering buffers, DMA/IOMMU mappings, open FDs, streaming state, or powered sensor after close;
- no regression to Wi-Fi SSH, display, touch, sound, microphone, MFC, BT, NFC, charging, battery or suspend.

## 22. Physical image verification

A byte count alone is not proof. A frame can be corrupted, all-black, stale or synthetic.

For the first captured frame:

- save raw planes with exact layout sidecar;
- convert with a toolchain capable of parsing the actual FOURCC and colorimetry;
- inspect image dimensions and decoder warnings;
- create a small contact sheet of several time-separated frames;
- ask the owner to verify the live scene physically if no direct display feedback is available;
- include evidence of scene movement and current frame timestamp;
- label test-pattern captures as test-pattern and keep them out of hardware acceptance evidence.

Never use `videotestsrc` or a generated bitmap to satisfy a physical camera gate.

## 23. Performance, memory and thermals

Camera work must be useful on the S10+, not just functional for two seconds.

Measure:

- capture start latency;
- first-frame latency;
- sustained fps and frame-time distribution;
- dropped/corrupt frames;
- copy/conversion time;
- CPU frequency and per-core load;
- IOMMU/DMABUF/ION memory pressure;
- memory bandwidth;
- device temperature and thermal throttling;
- battery discharge while previewing/recording;
- camera open/close cleanup latency.

Use zero-copy DMA-BUF only where importer/exporter compatibility, ownership and cache synchronization are proven. Do not chase zero-copy at the cost of memory corruption. Use bounded frame queues, drop old preview frames rather than accumulating latency, and avoid repeated full-resolution allocations per frame.

## 24. Permission and privacy checks

- Camera permission is required before the hardware is powered or acquired for app capture.
- Microphone permission is separate and only requested when recording with audio.
- Active camera indicator is visible while camera streaming/recording is active.
- Hardware closes on app close, pagehide/visibility transition, lock, service release or permission revoke.
- Background camera capture is not allowed unless a future explicit user-controlled feature is designed with a persistent indicator and clear UI.
- Camera frames remain on-device; no network listener or analytics upload.
- D-Bus APIs validate caller identity, capability and payload size.
- Device nodes are not world-writable. Use dedicated group/service account or narrowly scoped udev/systemd permissions.
- The daemon gets only the privileges necessary for the selected kernel operations; no unbounded root web API.
- Frame IPC is local, authenticated, bounded and resistant to FD leaks/replay.
- Save only user-requested stills/video.

---

# PART X — PROJECT DELIVERABLES

## 25. Required repository outputs

Create an evidence and implementation directory such as:

```text
docs/pwnage-86000/
  README.md
  RESEARCH-AND-DECISION.md
  DEVICE-BASELINE.md
  SENSOR-AND-NODE-MAP.md
  FIRMWARE-PROVENANCE.md
  FIRMWARE-REQUEST-MAP.md
  FIMC-IS2-STATE-MACHINE.md
  V4L2-ABI-RESULTS.md
  MEDIA-TOPOLOGY.md
  DRIVER-IMPLEMENTATION.md
  ANDROID-HAL-FALLBACK.md
  CAMERA-SERVICE-ARCHITECTURE.md
  PERFORMANCE-THERMALS.md
  TEST-PLAN-AND-RESULTS.md
  DEPLOYMENT-AND-ROLLBACK.md
  FINAL-STATUS.md
  evidence/<UTC_TIMESTAMP>/
```

Use actual names as appropriate, but preserve the intent. Evidence folder must include timestamp, machine-readable JSON, relevant dmesg, node maps, kernel config diff, firmware hashes, command transcripts, tests, frame metadata, and sanitized sample images. Keep large raw captures and proprietary binaries out of Git; record their paths and hashes only.

Also deliver as applicable:

- corrected and tested V4L2 C utility;
- exact target UAPI/private ioctl headers or wrappers;
- firmware manifest/generator/fetcher/verifier fixes;
- kernel camera profile and source patch series;
- camera service / daemon and unit;
- Nuxel camera bridge/PipeWire source integration;
- unit/integration/hardware tests;
- rollback scripts or precise restore commands.

## 26. Reporting format

At the end, provide a clear table:

| Requirement | State | Evidence |
|---|---|---|
| Rear-main sensor binding | | |
| Required firmware verified | | |
| FIMC-IS firmware booted | | |
| CSI link established | | |
| Correct capture ABI identified | | |
| Physical frame dequeued | | |
| Real scene verified | | |
| Nuxel Camera live preview | | |
| Still saved and opened in Photos | | |
| Real video saved and played | | |
| Front camera | | |
| Telephoto | | |
| Ultrawide | | |
| Depth/IR module | | |
| Permission and privacy checks | | |
| Reboot/suspend/release reliability | | |
| Existing phone functions regressed | | |

For every status use `PASS`, `PARTIAL`, `BLOCKED`, `NOT TESTED`, or `FAIL`, with evidence. Do not say “camera works” if only one sensor or one stage works. Say exactly which camera and modes were tested.

Include:

- exact kernel source commit and live kernel build ID;
- exact config and DTB hashes;
- firmware repository, commit, source path, hashes and installed paths;
- ABI version and capture method;
- service/app versions and changed files;
- tests run and pass/fail counts;
- physical tests run;
- known limitations;
- every deployment operation and rollback procedure.

## 27. Definition of done

**Minimum successful mission:** The real rear-main 2L4 sensor on the physical SM-G975F produces a live stream. The existing Nuxel Camera application previews it, captures a real photograph, saves it through the Nuxel media store, and the image opens in Nuxel Photos. A real video recording is also saved and plays correctly. The system releases the camera safely, permissions and privacy indicator work, and previously working Nuxel hardware is not regressed.

**Extended successful mission:** The front 3J1, rear tele 3M3 and rear ultrawide 3P9 are individually functional, with 4HA depth/IR support implemented to the extent its actual hardware function allows. Supported camera controls and switching work honestly.

**Not done:** installed firmware without a stream; sensor I²C enumeration only; node classification only; a media graph with no frames; a compiled but unbooted driver; a daemon that reports STREAMING but has no dequeued frames; a UI preview of test bars; a JPEG made from a test frame; an Android camera app running outside Nuxel; one frame that cannot be repeated; or a written future plan.

---

# PART XI — EXECUTION CHECKLIST AND HARD RULES

## 28. The execution checklist

Use this sequence and check off every stage in the evidence report:

- [ ] Read the entire specification and 84000 evidence.
- [ ] Inspect current repo worktree without destroying uncommitted changes.
- [ ] Discover phone over Wi-Fi and connect as root with `~wicked/.ssh/wicked_wqn_id_rsa`.
- [ ] Reconfirm model, kernel, DTB and config.
- [ ] Back up every file/image to be changed and verify rollback artifacts.
- [ ] Audit the 84000 mplane tool and build authoritative C UAPI probe.
- [ ] Reclassify live nodes from sysfs/source, not fixed node numbers.
- [ ] Verify correct mplane query/format support on the selected rear-main path.
- [ ] Audit exact FIMC-IS2 source and map all operations/firmware requests.
- [ ] Verify firmware fetcher, pinned source and manifest checksums.
- [ ] Fetch/stage exact firmware locally; correct camera-required policy.
- [ ] Resolve sensor setfile/checksum mapping, including 3J1/4HA anomaly.
- [ ] Determine exact firmware load path and prove firmware load at runtime.
- [ ] Trace secure-camera/TEE, DMA/IOMMU/ION and reserved-memory requirements.
- [ ] Complete native standard V4L2 capture attempt based on source evidence.
- [ ] If needed, complete exact Samsung private-ABI proof of concept.
- [ ] If needed, patch existing FIMC-IS2 driver and build separate camera kernel profile.
- [ ] If absolutely necessary, execute the documented driver rewrite path.
- [ ] If native driver path is not viable, bring up exact-device Android camera provider runtime.
- [ ] Capture and inspect the first physical rear-main frame.
- [ ] Integrate the stream into Nuxel Camera with real permission/lifecycle handling.
- [ ] Save a still and verify it in Photos.
- [ ] Save and play back real video with correctly gated microphone audio.
- [ ] Verify repeated open/close, lock, suspend, reboot, and clean resource release.
- [ ] Bring up front/tele/ultrawide/depth modules sequentially.
- [ ] Run regression tests for display, audio, MFC, networking, power and normal Nuxel use.
- [ ] Publish evidence, exact changed-file list, current limitations and rollback procedure.

## 29. Non-negotiable engineering rules

1. **Real frames are the goal.** Keep moving through viable routes until the physical camera works.
2. **Do not guess.** Every sensor mode, ioctl, buffer layout, firmware path, register, clock, regulator and DMA contract must come from exact source or direct evidence.
3. **No unrelated blobs.** Exact `beyond2lte` / Exynos 9820 firmware only; validate every hash and version.
4. **No synthetic success.** Test patterns are explicitly labeled and never count as camera proof.
5. **No stale diagnostics.** PWNAGE-84000 corrected mplane probing. Use that ABI and verify it against actual headers.
6. **No kernel API mismatch.** This is a downstream Linux 4.14 target. Modern V4L2/libcamera APIs may have changed; adapt to the exact target tree.
7. **No unsafe DMA.** Buffer ownership, cache maintenance, DMA mapping and cleanup are mandatory.
8. **No secure-camera bypass.** Respect TEE and protected memory requirements.
9. **No broad regressions.** Keep current boot, display, Mali, audio, MFC, Wi-Fi/BCMDHD, Bluetooth, NFC, input, suspend and user-data intact.
10. **No careless flashing.** Use a separate experiment build, verified boot backup and tested restore path.
11. **No unnecessary framework rewrite.** Preserve Nuxel's working Camera/Photos UI, bridge, broker and media store.
12. **No overclaiming.** Distinguish what was source-audited, compiled, deployed, initialized, streamed, physically inspected and owner-verified.
13. **No proprietary binary redistribution.** Keep vendor blobs local/ignored unless the license explicitly permits redistribution.
14. **Keep evidence.** Every important decision and live test must be reproducible from the report.

## 30. Final instruction

You are not being asked to write another document explaining why the S10+ camera is difficult. The repository already contains years—or at least many rounds—of camera investigation, and the 84000 report finally corrected a major diagnostic flaw. Use that head start.

Find the exact working firmware, understand the real FIMC-IS2 pipeline, select the right native or vendor route, implement the missing driver/interface, and feed genuine camera frames into Nuxel. Modify the existing kernel or write a new driver if the source proves that is what it takes. Keep the phone recoverable, protect calibration and user data, and test on the actual device.

**Get the rear-main S10+ camera producing real photographs in Nuxel. Then finish the other lenses. The camera is not complete until the Penguin can actually see.**

---

# Research links used as technical references

These references are starting points; the exact pinned source tree and live phone remain authoritative for the Nuxel implementation.

1. LineageOS device page — Samsung Galaxy S10+ / `beyond2lte`, Exynos 9820, ARM64, current device/kernel information: https://lineageos.github.io/lineage_wiki/devices/beyond2lte/
2. S10+ device tree and source manifest: https://github.com/whatawurst/android_device_samsung_beyond2lte
3. Matching S10+ vendor proprietary-file inventory — provider service, camera HAL, dependencies, setfiles: https://github.com/whatawurst/android_device_samsung_beyond2lte/blob/lineage-17.1/proprietary-files-vendor.txt
4. Matching S10+ vendor makefile — firmware install list: https://github.com/Evolution-X-Devices/vendor_samsung_beyond2lte/blob/bka/beyond2lte-vendor.mk
5. Linux V4L2 single/multi-planar API: https://cdn.kernel.org/doc/html/latest/userspace-api/media/v4l/planar-apis.html
6. Linux `VIDIOC_QBUF` multi-planar buffer requirements: https://github.com/torvalds/linux/blob/master/Documentation/userspace-api/media/v4l/vidioc-qbuf.rst
7. Linux upstream S5P/Exynos4 FIMC documentation (architectural context only; not the S10+ FIMC-IS2 implementation): https://www.kernel.org/doc/html/latest/admin-guide/media/fimc.html
8. libcamera pipeline-handler writer's guide: https://docs.libcamera.org/master/guides/pipeline-handler.html
9. Android Camera HAL architecture / HIDL and AIDL background: https://source.android.com/docs/core/camera/camera3
10. Android HAL architecture: https://source.android.com/docs/core/architecture/hal
11. libhybris overview: https://github.com/libhybris/libhybris
12. Halium overview: https://halium.org/
