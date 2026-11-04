# PWNAGE-61000 — MFC baseline and driver/firmware compatibility matrix

Captured: 2026-11-03 (Europe/Amsterdam)
Repository: `/x/nuxel`, branch `main`, HEAD `0bed35d881ba674a21f67d31501e84f1031992b5`
Mission: safe Exynos 9820 MFC hardware video decode on Samsung Galaxy S10+ SM-G975F (`beyond2lte`).

> This file is the pre-implementation snapshot. It is not retroactively edited to make a former state look proven. Implementation evidence lives in `PWNAGE-61000-MFC-REPORT.md` and `evidence/pwnage-61000/`.

## 1. Source commit and file hashes

Pinned downstream kernel source:

```text
repo    https://github.com/Linux4/android_kernel_samsung_exynos9820
commit  f7194c1d15eded1c2a1a4dc63825b26103435cc0
family  Linux 4.14.253 downstream (Samsung Exynos 9820)
defconfig exynos9820-beyond2lte_defconfig
```

Verified in the local build cache:

```text
$ git -C kernel/s10plus/.build/src rev-parse HEAD
f7194c1d15eded1c2a1a4dc63825b26103435cc0
```

SHA-256 of the repository files that define this mission's baseline:

```text
de4f245ac3f735859d29fb56cbbc0470018c2839a02536d93b61893c364e65fa  kernel/s10plus/build-kernel.sh
eb35afc2062ac21c1b8f6984fd883c405d3d255dee987553045d0e608d423825  firmware/s10plus/manifest.yml
5977d24edd86f2f54089dcd126342f0878e227e8b205122ae6af8aaf05d0ce1f  firmware/s10plus/install-firmware.sh
60ce4baa7a106b4560ab031a261627be69e40af5b444584e8554cdd4b343534f  firmware/s10plus/fetch-vendor-blobs.sh
3927239dd01ec27f898b140a8906f603409bd2c0105ad44ac1af20c44a425711  tools/s10plus/a29/nuxel-gstreamer-guard.sh
5059335bbe725589c54ac683785eb993d9cfbc7aa4e43a57ff439c60ab603db1  configs/s10plus/wireplumber/99-nuxel-no-v4l2.conf
```

Relevant kernel-source hashes before the PWNAGE-61000 patch:

```text
69c27d0a11a790b3fa6371e6bc19f9bdaa1a8960f3bfc15ed6e281924655f37b  drivers/media/platform/exynos/mfc/mfc.c
a0fb5449ab46441cfa559b5c22d653016bf0823b7456cc709770f7b6f5adf44e  drivers/media/platform/exynos/mfc/mfc_buf.c
81fbd3e66fa05124edd966d5f2fe9899ebc18fe694a4ae425bfb4c70595277fa  drivers/media/platform/exynos/mfc/mfc_dec_v4l2.c
9d3a6441c74a5d8158ef36d7214580fb1ec264e80fc794ba86879065646019c5  drivers/media/platform/exynos/mfc/mfc_sync.c
36f43b1fdf27babec70f0ef2e6d92b4db62aae7b4bceb1679485e09c4420959b  arch/arm64/boot/dts/exynos/exynos9820.dts
ec1f52de525b26bd408111e7bb109886b009429143c1c0e804903dde783e3e4d  .build/out/.config (build of 2026-10-28)
```

## 2. Live handset identity and boot state

Read-only SSH inventory, no device node opened:

```text
host             root@10.20.30.16  (Wi-Fi SSH, key ~/.ssh/wicked_wqn_id_rsa)
boot id          954ea1bf-732c-4274-825f-ff2788b14467
kernel           Linux 4.14.253-gf7194c1d15ed-dirty #5 SMP PREEMPT
                 built Sun Nov 1 13:38:15 CET 2026, gcc 15.2.0
OS               Fedora Linux 43 (Forty Three), aarch64
board            SM-G975F, Exynos 9820, 8 GB
cmdline          androidboot.hardware=exynos9820, firmware_class.path=/vendor/firmware,
                 root=/dev/sda25, rootwait ro, androidboot.dtbo_idx=9
```

The live kernel string contains `-dirty`; it is a locally built kernel from the pinned commit plus Nuxel capability changes. The **patched** PWNAGE-61000 kernel has not been deployed.

Full capture: `evidence/pwnage-61000/live-inventory.txt`.

## 3. Discovered video/media nodes (sysfs only)

The MFC platform device is `188d0000.mfc`, bound to driver `s5p-mfc`, with six video nodes:

| Node | sysfs name | Role |
|---|---|---|
| `/dev/video6` | `s5p-mfc-dec0` | **normal decoder — the only candidate for MFC decode** |
| `/dev/video7` | `s5p-mfc-enc0` | encoder (out of scope) |
| `/dev/video8` | `s5p-mfc-dec-secure0` | DRM/secure decoder (out of scope) |
| `/dev/video9` | `s5p-mfc-enc-secure0` | secure encoder (out of scope) |
| `/dev/video10` | `s5p-mfc-enc-otf0` | OTF encoder (out of scope) |
| `/dev/video11` | `s5p-mfc-enc-otf-secure0` | OTF secure encoder (out of scope) |

Other nodes are camera/ISP/scaler/JPEG (`exynos-fimc-is-*`, `camerapp-gdc`, `exynos-jpeg`) and are explicitly out of scope. No `/dev/media*` node exists. `CONFIG_MEDIA_CONTROLLER` is not set.

No node was opened during inventory. The historical failure was an open, not a directory read.

## 4. Device-tree identity

Live `/sys/firmware/devicetree/base/mfc@188D0000` and the pinned `exynos9820.dts` node agree:

```text
compatible   "samsung,exynos-mfc"
reg          0x188d0000, length 0x10000
interrupts   GIC SPI 0x152
clock-names  "aclk_mfc"
clocks       clock index 0x1a6
iommus       <sysmmu_mfc0 sysmmu_mfc1>  (0x18890000 / 0x188b0000)
ip_ver       0x1300
nal_q        enabled with entry size 0x200, dump size 0x178
support_10bit = 1, support_422 = 1, P010_decoding = 1, support_rgb = 0
power domain pd-mfc@15862600 (cal_id 0xb138000c)
hwfc         0x18a28000, mmcache 0x1a300000
```

The node has no `status = "disabled"` property; it is active. It has no `firmware-name` property: the driver hard-codes the request name.

The DT describes the silicon's declared capability (10-bit, 4:2:2, P010, HDR10+ metadata). **None of that is a verified Nuxel capability** until the driver, firmware and userspace decode path pass on the handset.

## 5. Driver identity and ABI

Driver: `drivers/media/platform/exynos/mfc/` (Samsung vendor driver, `MFC_DRIVER_INFO 180315`), selected by `CONFIG_VIDEO_EXYNOS_MFC`, object `exynos_mfc.o`.

Key source facts:

| Fact | Source location |
|---|---|
| Match string `samsung,exynos-mfc` | `mfc.c:1793` |
| Decoder video name `s5p-mfc-dec` | `mfc.c:55` |
| Node index / minor mapping: decoder = index 0, minor 60·id + 0 | `mfc.c:1140` |
| Firmware request name `MFC_FW_NAME = "mfc_fw.bin"` | `mfc_common.h:68` |
| Firmware loaded on first open, not probe | `mfc.c:354`, `mfc.c:586` |
| `request_firmware()` in `mfc_load_firmware()` | `mfc_buf.c:580` |
| FW size cap = `firmware_code = PAGE_ALIGN(0x100000)` (1 MiB) | `mfc.c:1781`, `mfc_buf.c:591` |
| FW/hardware version check | `mfc_run.c` after `RISC_ON` / `SYS_INIT`, compares `mfc_get_mfc_version()` with DT `ip_ver` |
| Interrupt timeout 4000 ms, one retry at 2× | `mfc_common.h:40`, `mfc_sync.c:54-67` |
| Short close timeout 800 ms | `mfc_common.h:42`, `mfc_sync.c:91-94` |
| hwlock timeout 5000 ms | `mfc_common.h:44` |
| Queues advertise `VB2_USERPTR | VB2_DMABUF` only | `mfc.c:196,209` |
| MMAP explicitly rejected | `mfc_dec_v4l2.c` `mfc_dec_reqbufs()` |
| Capture buffers are imported as DMA-BUF fds (`dma_buf_get`) | `mfc_mem.c:297-337` |
| QUERYCAP sets separate CAPTURE/OUTPUT mplane caps; no `V4L2_CAP_VIDEO_M2M_MPLANE` | `mfc_dec_v4l2.c:95-101` |
| No `vidioc_decoder_cmd`, no `subscribe_event`, no Request API | `mfc_dec_v4l2.c:1262-1283` |

### API classification

**Vendor-specific nonstandard V4L2 M2M-style decoder ABI.** It has OUTPUT and CAPTURE multi-planar queues on one node, but:

- it does not use the `v4l2_m2m` framework;
- it has no stateful-decoder `VIDIOC_DECODER_CMD` (START/STOP/PAUSE) or `V4L2_EVENT_SOURCE_CHANGE`;
- it has no stateless Request API;
- it rejects `V4L2_MEMORY_MMAP`;
- its capture side requires DMA-BUF import;
- its source side accepts USERPTR or DMA-BUF.

Consequences:

- GStreamer `v4l2codecs` (stateless) is **not** a match.
- A standard stateful GStreamer `v4l2*h264dec` element and FFmpeg's `v4l2_m2m` are also not expected to match without an adapter, because they require MMAP and/or decoder-command/event support.
- The first userspace milestone must be a purpose-built vendor-ABI helper, not a generic player checkbox.

## 6. Firmware requirement and provenance

Exact request string: `mfc_fw.bin`.
Search path on the running handset includes `/lib/firmware` and `/vendor/firmware` (`firmware_class.path=/vendor/firmware`).

Actual blob found in the approved source-of-record:

```text
repo          Linux4/proprietary_vendor_samsung
commit        05c9ef8f16e0ad5ab274e408c120dfd99fd5c628
path          exynos9820-common/proprietary/vendor/firmware/mfc_fw.bin
size          685832 bytes
sha256        f3802d34524f5919c16505c03b4cbfe184963f98787feed6232b643bda68b55f
header        ARM32 little-endian code (first word 0xea000077)
manifest      checksum matches exactly
```

The manifest entry's checksum is therefore **real**, not a placeholder. The earlier statement that the binary was absent from the supplied archive was correct: it was not bundled, but it is reproducible from the pinned upstream tree with `firmware/s10plus/fetch-vendor-blobs.sh`.

Live `/lib/firmware/mfc_fw.bin`: **absent** at baseline.

The driver cannot validate the firmware version until it has loaded the blob, powered the block and executed `RISC_ON`/`SYS_INIT`; therefore firmware-ABI acceptance is `NOT_TESTED_ON_DEVICE` at baseline.

## 7. Existing safety guard and WirePlumber state

`tools/s10plus/a29/nuxel-gstreamer-guard.sh` disables, by renaming to `.nuxel-disabled`:

```text
libgstvideo4linux2.so
libgstv4l2codecs.so
libgstkms.so
libgstopengl.so
```

and removes stale GStreamer registry caches. It is invoked from both `nuxel-session.sh` paths.

Live state at baseline:

```text
/usr/lib64/gstreamer-1.0/libgstvideo4linux2.so.nuxel-disabled
/usr/lib64/gstreamer-1.0/libgstv4l2codecs.so.nuxel-disabled
/usr/lib64/gstreamer-1.0/libgstkms.so.nuxel-disabled
/usr/lib64/gstreamer-1.0/libgstopengl.so.nuxel-disabled
```

WirePlumber `/etc/wireplumber/wireplumber.conf.d/99-nuxel-no-v4l2.conf` keeps:

```text
hardware.audio     = required
hardware.bluetooth = required
hardware.video-capture = disabled
```

The guard and the WirePlumber setting are safety controls and remain in place. No camera capture is enabled by MFC decode.

## 8. Kernel config at baseline

From the last local build and the live `/proc/config.gz`:

```text
CONFIG_MEDIA_SUPPORT=y
# CONFIG_MEDIA_CONTROLLER is not set
CONFIG_VIDEO_DEV=y
CONFIG_V4L2_MEM2MEM_DEV=y
CONFIG_VIDEOBUF2_CORE=y
CONFIG_VIDEOBUF2_MEMOPS=y
CONFIG_VIDEOBUF2_DMA_SG=y
CONFIG_VIDEO_EXYNOS=y
CONFIG_VIDEO_EXYNOS_MFC=y
CONFIG_EXYNOS_IOMMU=y
CONFIG_IOMMU_API=y
CONFIG_IOMMU_DMA=y
CONFIG_IOMMU_IOVA=y
CONFIG_EXYNOS_CONTENT_PATH_PROTECTION=y
CONFIG_FW_LOADER=y
CONFIG_FW_LOADER_USER_HELPER=y
CONFIG_FW_LOADER_USER_HELPER_FALLBACK=y
```

`CONFIG_FW_LOADER_USER_HELPER_FALLBACK=y` is the root of the historical 60-second stall: `request_firmware()` falls back to the userspace helper when `/lib/firmware/mfc_fw.bin` is missing. `/sys/class/firmware/timeout` is `60`.

## 9. Userspace media inventory at baseline

```text
gstreamer1                       1.26.11-1.fc43.aarch64
gstreamer1-plugins-base          1.26.11-1.fc43.aarch64
gstreamer1-plugins-good          1.26.11-1.fc43.aarch64
gstreamer1-plugins-bad-free      1.26.11-1.fc43.aarch64
gstreamer1-plugins-ugly-free     not installed
gstreamer1-plugin-libav          not installed
gstreamer1-plugin-openh264       1.26.11-1.fc43.aarch64
mpv                              0.40.0-3.fc43.aarch64
libavcodec-free                  7.1.5-1.fc43.aarch64
ffmpeg-free / ffmpeg             not installed
v4l-utils                        not installed
```

`mpv --hwdec=help` lists nvdec/vaapi/vulkan/vdpau only. There is **no** `v4l2m2m` entry in this build. The installed mpv/FFmpeg-free chain therefore cannot use the vendor MFC ABI directly.

The existing boot/preload path uses `mpv --hwdec=no` and remains unchanged.

## 10. Risks and facts still unknown

Known risks:

1. The running kernel still contains the old `request_firmware()` path and the 60 s userspace fallback. Do not open `/dev/video6` on this kernel.
2. Installing the firmware without the patched kernel would change the failure mode from "missing firmware" to "hardware init possible", which is not safer if the firmware/driver ABI is wrong.
3. The vendor ABI is not compatible with generic GStreamer/FFmpeg M2M clients; a helper is required.
4. Capture buffers require DMA-BUF, so a first decode test needs `/dev/udmabuf` or `/dev/ion` and correct IOMMU mapping.
5. `CONFIG_EXYNOS_CONTENT_PATH_PROTECTION=y` means secure/DRM paths exist; normal decode should stay on the non-secure node.
6. Thermal/CPU claims require matched software and hardware runs; none have been made.

Unknown until on-device test:

- firmware-reported MFC version (`0x1300` expected);
- whether the pinned blob's ABI is accepted by this exact hardware revision;
- actual H.264/HEVC/VP9 profile/level/resolution limits;
- decode latency, dropped frames, CPU and thermal deltas;
- whether UDMABUF capture buffers map correctly through the MFC SysMMU.

## 11. Compatibility matrix

| Item | Required evidence | Result |
|---|---|---|
| MFC hardware IP revision | DT `ip_ver = 0x1300`; live DT and source agree | **PASS** (declared; silicon version readback pending) |
| Kernel driver implementation | `drivers/media/platform/exynos/mfc/`, pinned commit `f7194c1d…` | **PASS** |
| Kernel config | `CONFIG_VIDEO_EXYNOS_MFC=y`, `VIDEOBUF2_DMA_SG=y`, `EXYNOS_IOMMU=y` in live and built config | **PASS** |
| DT binding | compatible/resources/IOMMU/power domain match the live node | **PASS** |
| Firmware filename | exact `request_firmware*` string `mfc_fw.bin` | **PASS** |
| Firmware version | driver acceptance check after `RISC_ON`/`SYS_INIT` | **UNKNOWN** (`NOT_TESTED_ON_DEVICE`) |
| Firmware hash | actual blob SHA-256 = manifest candidate | **PASS** |
| DMA/IOMMU path | source uses two SysMMUs + DMA-BUF capture; runtime untested | **UNKNOWN** (runtime) |
| V4L2 API mode | vendor-specific nonstandard M2M-style; no decoder_cmd/events/MMAP | **PASS** (classified) |
| Missing-firmware failure | source patch uses `request_firmware_direct()`; not yet booted | **PASS** (source) / **NOT_TESTED_ON_DEVICE** |
| GStreamer/FFmpeg direct use | no matching generic backend in installed packages | **FAIL** (expected; adapter required) |

Any `UNKNOWN` in IP compatibility, firmware ABI, memory path or device tree is a stop sign for opening the live node. At baseline, firmware ABI and runtime DMA/IOMMU are `UNKNOWN`; therefore **the live node was not opened**.
