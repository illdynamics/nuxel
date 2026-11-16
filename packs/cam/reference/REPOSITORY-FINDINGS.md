# Nuxel S10+ camera repository findings

**Snapshot inspected:** uploaded `nuxel-main (5).zip`, dated 2026-11-10 in the ZIP entries. The archive starts with the snapshot identifier `a637cc0918b2bdcdd26f46048ae7d52c20880f7d`; verify the active repository/commit separately.

## Current engineering verdict

`REPORT-CAMERA.md` says `BLOCKED_FIRMWARE`. Five Exynos FIMC-IS sensor modules were observed bound, but no real integrated frame had been captured. The captured root filesystem did not have the expected setfiles/ISP firmware and lacked `/dev/media*` and `/dev/v4l-subdev*`. Prior standard capture tests on `/dev/video111` showed `VIDIOC_S_FMT -> ENOTTY`, `REQBUFS -> EINVAL` and `QUERYBUF -> EINVAL`.

## Existing sensor evidence

- Rear main: `fimc-is_sensor_2l4@20` / S5K2L4.
- Rear tele: `fimc-is_sensor_3m3@5A` / S5K3M3.
- Rear ultrawide: `fimc-is_sensor_3p9@2D` / S5K3P9.
- Front main: `fimc-is_sensor_3j1@10` / S5K3J1.
- Front IR/depth: `fimc-is_sensor_4ha@10` / S5K4H7.

The kernel evidence also mentions FIMC-IS core, MIPI CSI PHYs, GDC, ION camera heaps, OIS actuators/controller and EEPROM driver probes. The 3P9 path reported `gpio_subcam_sel` and `gpio_mipi_sel` errors. These are leads to verify against current `dmesg`, live sysfs and exact device tree; do not use guessed GPIOs or sensor register writes.

## Missing vendor inputs

The report/policy candidates include per-sensor `s5k*_setfile.bin`, Exynos9820 camera firmware (`exynos9820_camera.bin`, `is-camera*.bin`), FIMC-IS MCU/library/RTA (`fimc_is_fw_mcu.bin`, `fimc_is_lib.bin`, `fimc_is_rta*`), calibration/tuning, and possibly OIS files. The exact required set must be derived from the pinned kernel's firmware requests and the matching Samsung vendor stack.

No usable OEM camera binaries are included in the uploaded repository. In particular, `tools/s10plus/a33/tests/hw-subsystems/fixtures/camera-ready/lib/firmware/s5k2l4_setfile.bin` is only a **3-byte test placeholder**. It is not firmware and must never be installed.

The repository says EEPROM drivers probed and calibration data is present, while no external setfiles/ISP firmware are present. Reconcile the difference. Never dump or overwrite raw EEPROM calibration.

## Current userspace is partially built, not camera-ready

- `pwa/nuxel-apps/camera-gallery/` has a camera PWA using browser `getUserMedia`, a photo/video UI and bridge media-store verbs.
- `pwa/nuxel-apps/photos/` is the file-backed gallery.
- `services/nuxel-bridge/src/media_store.py` persists media under `/var/lib/nuxel/media`.
- `bridge.py` exposes `CameraStatus`, `CameraListCaptures`, `CameraCapture`, `CameraOpen`, `CameraDelete`.
- `shell/nuxel-camera-native/nuxel_camera_native.py` is a native GTK4 app but its viewfinder is currently a placeholder/honest blocked state; it does not show a real stream.
- `shell/nuxel-camera-portal/nuxel_camera_portal.py` owns a **private** `org.nuxel.Camera` interface (`RunCamera`, `Release`, etc.). It is not the standard `org.freedesktop.portal.Camera`. Its real path has historically defaulted to `v4l2src` on `/dev/video0`, which is not proven to be a capture node on this phone.
- The current camera service unit is a user/session unit, not a system service. Preserve correct D-Bus/PipeWire session context.

## Permission manager already has a camera permission

`capabilities.json` already defines canonical high-risk `camera`, with aliases `camera:capture` and `camera:preview`, grant-required/default-deny intent, portal/sandbox/AppArmor mechanisms, partial enforcement, and honest kernel limitations. The Permission Manager PWA already labels and canonicalizes `camera`. The Camera manifest additionally declares `camera:read`, which is not currently listed in the canonical camera aliases (the generic UI resolver maps base tokens; the permission semantics still need explicit alignment).

Current Bridge semantics need auditing:

- `CameraCapture` requires `camera:capture`.
- `CameraListCaptures` and `CameraOpen` use `camera:preview`, conflating access to saved media with live sensor access.
- `CameraDelete` also uses `camera:capture`, which should be reviewed as a media-write/delete permission.
- `CameraCapture` stores caller-supplied base64; this is not proof of a physical sensor capture and should be bound to an authorized live camera session if used in the final architecture.
- `bridge.py` catches camera privacy-provider exceptions and treats the provider as unblocked; `privacy_provider.camera_capture_blocked()` returns false on read error. This is a fail-open privacy path to fix.
- Camera status currently reports no tracked active camera sessions. This is insufficient for an indicator that must also reflect ZapZap/Ferdium.

The permission project notes that `/dev/video*` DAC/AppArmor protection is partial, AppArmor is effective only if present in the live LSM list, Landlock is not available on the recorded 4.14 kernel, and systemd `DeviceAllow` is not proven. Never claim stronger enforcement than the current kernel actually provides.

## Portal and third-party app gap

The repository's A53 snapshot says `xdg-desktop-portal`, its GTK backend, PipeWire and WirePlumber were absent at that time. It also records `CONFIG_USER_NS` unset and Flatpak absent. Verify the live state; do not assume it remains true. A custom `org.nuxel.Camera` D-Bus service cannot automatically make Chromium/Electron/WebKit clients see the camera. Compatible external clients need the standard camera portal + PipeWire access model or another specifically supported browser capture path.

The repo does not list ZapZap or Ferdium manifests/package IDs. Discover their installed package types and actual app IDs on the running device; do not hardcode guessed IDs.

## Diagnostic defects

`tools/s10plus/a33/nuxel-camera-diag.sh` currently considers the firmware stage passed if **any** expected candidate file is present. It can return `READY_UNTESTED` with only one candidate file and a media node. Its `capture` branch selects the first `/dev/video*` entry and uses generic `v4l2-ctl --stream-mmap`, despite the known Samsung private ioctl path. Harden both behaviors; never choose arbitrary video nodes.

## Kernel build and flash mechanics

- `kernel/s10plus/build-kernel.sh` pins `Linux4/android_kernel_samsung_exynos9820` at `f7194c1d15eded1c2a1a4dc63825b26103435cc0`, Linux 4.14.253, defconfig `exynos9820-beyond2lte_defconfig`, active config fragment `kernel/s10plus/configs/nuxel-drm-kbase.fragment`.
- It applies `kernel/s10plus/patches/*.patch` in sorted order. A patch is fatal only with a `.required` sidecar; don't mark an unverified patch required.
- It builds `Image.gz` and DTBs. The boot-candidate tool expects the correct raw arm64 `Image` payload; do not put `Image.gz` in place of raw Image.
- `boot/s10plus/build-candidate.sh` repacks a candidate from a known-good base and passes the result through boot-image validation.
- `boot/s10plus/flash.sh` is the TWRP + ADB path and writes its `--uboot` image to `/dev/block/platform/13d60000.ufs/by-name/boot`. It requires `docs/s10plus-device-inventory.md` to be completed for real writes and checks device identity. Its `--rootfs` option defaults to `userdata`; do not use it blindly because it can overwrite user data.
- `flash-heimdall.sh` is Download Mode, not the starting TWRP path.
- `REFLASH-PLAN.md` recommends an A/B inactive-slot flow, but this must be reconciled with the actual S10+ PIT/by-name topology and current custom Nuxel rootfs. Do not assume an A/B layout or invent slots.

## SSH/deployment mechanics

- `scripts/s10plus-debug-pack/nuxel-live-ssh.sh` launches the existing Tri-Link SSH/console tool.
- `nuxel-live-deploy.sh` uses framed CDC-ACM serial-console transport and atomic/hash-verified deployment. It is **not automatically a Wi-Fi SSH deployer**.
- Owner-directed post-boot SSH target for this task: `root@192.168.178.167`, key path `~wicked/.ssh/wicked_wqn_id_rsa`. Preserve normal SSH host-key validation; never log/copy the private key. Deploy safe userspace files over SSH with staging, hashes, atomic promotion and rollback.

## Recommended order

1. Reverify handset/kernel/runtime while still in TWRP; inspect active repository and concurrent NFC work.
2. Read-only acquire exact OEM files from the owner's already-mounted matching vendor/system paths using the helper in this pack.
3. Trace the exact FIMC-IS ABI and choose a real pipeline architecture; don't assume a generic libcamera install fixes it.
4. Bring up rear-main first, then front-main and other supported sensors.
5. Complete native Camera app + standard camera portal/PipeWire + third-party clients.
6. Correct Permission Manager/portal enforcement and fail-closed privacy.
7. Build/flash one coherent kernel batch with concurrent ready NFC work; use the prescribed TWRP-return failure loop.
8. After Nuxel boots, SSH to the owner-specified endpoint and live-deploy remaining safe userspace pieces.
9. Physical test actual frames in app and supported ZapZap/Ferdium sessions; collect evidence.

## External technical references

- XDG Camera portal API: `https://flatpak.github.io/xdg-desktop-portal/docs/doc-org.freedesktop.portal.Camera.html`
- XDG portal PipeWire access-control model: `https://flatpak.github.io/xdg-desktop-portal/docs/pipewire.html`
- libcamera pipeline-handler writer guide: `https://docs.libcamera.org/master/guides/pipeline-handler.html`
- libcamera pipeline-handler API: `https://docs.libcamera.org/master/internal-api/classlibcamera_1_1PipelineHandler.html`

These explain the standard APIs; they do not prove this proprietary S10+ FIMC-IS interface is already compatible.
