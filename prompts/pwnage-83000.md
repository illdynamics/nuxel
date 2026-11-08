# PWNAGE-83000 — Camera Bring-Up Kickstarter

**Mission:** Make the built-in cameras on the Samsung Galaxy S10+ (`SM-G975F`, `beyond2lte`, Exynos 9820) work in Nuxel. This is the execution brief. The authoritative requirements, research, implementation sequence, safety rules and acceptance gates are in **[`full-pwnage-83000.md`](./full-pwnage-83000.md)**.

## Read this first

1. Read `full-pwnage-83000.md` completely before changing anything. It is the mission specification, not optional background.
2. Work in the actual Nuxel repository and current branch. Preserve the working phone OS. Start with a clean status check, current commit and backups of every file you intend to modify.
3. Do not accept the existing `HARDWARE_BLOCKED` conclusion as proven. The repository's V4L2 tests advertise multi-planar capture capability but send single-planar capture ioctls. Correct this before making an architectural decision.
4. Inspect the exact pinned Samsung kernel source and the real phone before writing a driver, a libcamera handler or an Android compatibility layer.
5. Keep the existing Camera/Photos UI, permission checks, `org.nuxel.Bridge`, `org.nuxel.Camera` private broker and durable media store. Connect them to actual sensor frames; do not replace them with a mock camera.

## Initial execution order

**A. Re-establish truth.** Discover the connected S10+ using the repository's existing Wi-Fi SSH helper. Capture the device model, kernel release, boot command line, active kernel config, camera sysfs topology, every V4L2 node's `QUERYCAP`, firmware files, boot logs, installed PipeWire/GStreamer/WebKit components and camera-service state. Save a timestamped baseline.

**B. Fix the V4L2 probe.** Rebuild the probe against the target kernel's UAPI headers. For nodes advertising `V4L2_CAP_VIDEO_CAPTURE_MPLANE`, use `V4L2_BUF_TYPE_VIDEO_CAPTURE_MPLANE` (value 9), `struct v4l2_pix_format_mplane`, and the multi-planar `v4l2_buffer`/`v4l2_plane` queueing ABI. Do not use single-planar type 1 on those nodes. Re-run `QUERYCAP`, `G_FMT`, `ENUM_FMT`, `TRY_FMT`, then a bounded capture test on the node the exact driver source identifies as the rear-main capture endpoint. `V4L2_CAP_EXT_PIX_FORMAT` is a standard V4L2 feature flag, not proof of a Samsung-private ioctl.

**C. Read the exact driver.** Fetch/verify the kernel source pinned by this repository (`Linux4/android_kernel_samsung_exynos9820`, commit `f7194c1d15eded1c2a1a4dc63825b26103435cc0`). Trace FIMC-IS2 Kconfig, probe, sensor binding, video-node registration, `v4l2_ioctl_ops`, multi-planar callbacks, media-controller registration, subdevice APIs, private ioctl definitions, firmware requests and buffer allocator/IOMMU requirements. Every node number and ioctl sequence must come from source plus live evidence—not guesses.

**D. Restore the exact firmware contract.** Audit the existing pinned firmware fetcher and manifest. Verify FIMC-IS MCU/library/RTA, `fmsb`, `rxse`, `txse*`, DNN and each sensor's exact `setfile_*.bin` against the manifest and exact `beyond2lte` source. Stage required files locally and install them to the path proven by the kernel's `request_firmware()` calls. Keep proprietary blobs local; do not commit or redistribute them.

**E. Make the hardware stream.** Prefer native V4L2 if the corrected ABI works. If Samsung-private ioctls are genuinely required, implement a typed, version-matched adapter from the exact source/UAPI. If the driver needs a media graph, build a separate camera-enabled kernel profile with only the necessary media-controller/subdevice options. Preserve the production Mali-G76, fbdev/DECON, audio, MFC, Wi-Fi and boot path. Use the exact matching Samsung Android camera stack only as the engineered fallback described in the full specification—not as a loose `.so` copy.

**F. Integrate and prove it.** Deliver a real rear-main preview, photo and video on the physical phone first. Then add front, telephoto, ultrawide and depth paths one at a time. Publish the stream through a narrowly scoped Nuxel camera service and then PipeWire/portal/WebKit as appropriate. Preserve permission gating, the active-camera indicator, foreground-only capture and file-backed Photos storage.

## Non-negotiable completion gate

This mission is **not complete** when packages install, sensor names appear, a daemon starts, the UI preview opens or a synthetic pattern displays. It is complete only when the physical rear-main sensor produces changing real-scene frames, Nuxel Camera previews them, a real still and video are saved and opened by Photos, and the owner verifies the result on the S10+. Record source, firmware, kernel, service and physical-device evidence as specified in `full-pwnage-83000.md`.

**No fake pass. No silent fallback to a test pattern. No blind register writes. No unrelated-device blobs. No careless partition flashing. Keep going through the native path, the exact Samsung interface and the controlled fallback until one real camera path works.**
