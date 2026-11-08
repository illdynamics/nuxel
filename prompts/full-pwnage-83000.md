# FULL-PWNAGE-83000 — Operation Penguin Vision

**Target:** Working built-in camera system on Nuxel / Samsung Galaxy S10+ (`SM-G975F`, codename `beyond2lte`, Exynos 9820 / `universal9820`).

**Mission class:** Hardware bring-up, kernel/userspace integration, firmware restoration, camera application delivery, and physical-device verification.

**Completion mission:** Do not stop after a source audit, package install, V4L2 enumeration, kernel compile, service launch or UI mockup. Keep moving through the viable implementation paths until the physical internal camera sensor streams real frames into Nuxel. Start with the rear-main sensor; then bring up the other lenses in controlled stages.

---

## 0. Primary instruction

Read this entire document before making code or device changes. Then execute it against the current Nuxel repository and the actual S10+ hardware. This specification supersedes older A52/A53 camera conclusions wherever the evidence below corrects them.

The short kickoff file `pwnage-83000.md` points here. This file is the complete engineering specification.

**Do not restart the camera project from scratch.** The current Nuxel tree already contains a substantial Camera application, Photos application, private camera broker, privileged bridge API, media storage, diagnostics, kernel build machinery, a firmware manifest and prior hardware evidence. Correct the diagnosis, finish the missing hardware stack, and connect real frames to the existing product.

**Do not declare the camera impossible merely because generic V4L2 probing failed.** The existing tests contain a material API mismatch. Correct it first.

**Do not treat “no negotiations” as permission for reckless writes.** Use every technically justified route, including a camera-enabled kernel build or a carefully controlled exact-device vendor compatibility runtime if needed. Preserve the already-working Nuxel installation, user data, radio, calibration, boot chain, display, GPU, networking and recovery path. No blind writes or firmware substitution.

## 0.1 Mission priorities

1. Prove what the current kernel and hardware actually expose.
2. Correct the V4L2 diagnostics and retest with the right ABI.
3. Inspect the exact pinned FIMC-IS2 source and determine the capture state machine.
4. Install the exact matching camera firmware/setfiles required by that state machine.
5. Get one physical rear-main camera frame.
6. Integrate that frame into the existing Nuxel Camera app and MediaStore/Photos workflow.
7. Complete video recording and robust lifecycle/permission handling.
8. Add the other camera modules one at a time.
9. If the native route proves impossible, use the exact Samsung Android stack in a properly engineered, isolated fallback—not an improvised library copy.

The finish line is a working camera in Nuxel, not a long explanation of why the current build does not have one.

---

# PART I — REPOSITORY BASELINE AND CORRECTIONS

## 1. Target device and kernel identity

The supplied ZIP (`nuxel-main (12).zip`) is the current Nuxel repository snapshot, timestamped 2026-11-04. It targets:

- Samsung Galaxy S10+, model `SM-G975F`, device codename `beyond2lte`.
- Samsung Exynos 9820 / `universal9820`, ARM64.
- Downstream Samsung/Linux4 kernel tree `Linux4/android_kernel_samsung_exynos9820`.
- Kernel source pin: `f7194c1d15eded1c2a1a4dc63825b26103435cc0`.
- Historical live kernel evidence: Linux `4.14.253`; the actual running kernel must be re-read at mission start.
- Rear main sensor module: `2L4`.
- Rear telephoto sensor module: `3M3`.
- Rear ultrawide sensor module: `3P9`.
- Front main sensor module: `3J1`.
- Front depth/IR module: `4HA`.

The repository's `docs/a52-camera/HARDWARE-INVENTORY.md` records the following observed hardware:

- FIMC-IS core at platform address `170e0000.fimc_is`.
- Sensor controllers around `17030000`, `17040000`, `17050000`, `17050000.fimc_is_sensor2`, `17060000`, and `17090000`.
- MIPI CSI PHY instances, camera ION/reserved-memory heaps, EEPROM calibration devices, OIS actuators, and an Exynos GDC post-processing block.
- FIMC-IS video-node families recorded as `/dev/video101`–`106`, `/dev/video110`–`114`, `/dev/video120`–`124`, `/dev/video130`–`142`, `/dev/video148`–`149`, `/dev/video160`–`180`, `/dev/video210`–`233`, and `/dev/video250`–`251`.

These node numbers are historical observations, not permanent identifiers. Resolve every node by `/sys/class/video4linux`, `/sys/dev/char`, driver symlink, `VIDIOC_QUERYCAP`, bus/device topology, and current media topology. Never hardcode a video number as if it were stable.

**Node-class warning:** In the recorded inventory, `/dev/video6`–`11` are MFC decoder/encoder devices; `/dev/video12` is Exynos JPEG; `/dev/video50` is scaler; `/dev/video155` is GDC. They are not interchangeable with camera sensor capture nodes. Do not let generic V4L2 discovery open MFC endpoints. Nuxel has a documented previous failure where missing MFC firmware plus generic video-device probing could trigger a blocking firmware request and wedge audio/session management.

## 2. What is already implemented

Retain and extend these existing parts. Do not replace them with a parallel camera architecture without proving a need.

### 2.1 Camera and Photos applications

`pwa/nuxel-apps/camera-gallery/` already implements:

- Photo and Video modes.
- `getUserMedia()` preview path and honest unavailable/error handling.
- Camera permission request flow through Nuxel's permission broker.
- A visible camera-active indicator.
- Rear/front switching with the previous stream released before the next device is opened.
- Still capture through canvas and the bridge.
- Video recording through `MediaRecorder`, using the actual runtime MIME type/extension.
- Conservative 1280×720 ideal resolution rather than confusing screen geometry with camera resolution.

The app deliberately does not fake flash, autofocus, optical zoom, HDR, stabilization, 4K/60, or camera presence. Keep that honesty. Implement controls only when actual device capability and service support are proven.

`pwa/nuxel-apps/photos/` already provides file-backed Photos browsing, thumbnails, search/filtering, date albums, viewer/playback, metadata and deletion.

### 2.2 Bridge, broker, permissions and storage

The existing application route is:

```text
Nuxel Camera / Photos PWA
  -> window.NuxelBridge.call(namespace, verb, params)
  -> nuxel-http-bridge (local HTTP bridge)
  -> org.nuxel.Bridge (system bus)
  -> camera backend / media store
  -> /var/lib/nuxel/media/
```

The current private camera broker is `org.nuxel.Camera`. It was deliberately renamed away from `org.freedesktop.portal.Camera`; it is not a complete implementation of the standard desktop portal Camera interface. Preserve this distinction.

The bridge already has camera verbs such as `camera.status`, `camera.list-captures`, `camera.capture`, `camera.open`, and `camera.delete`; permissions include `camera:preview` and `camera:capture`. Extend the API with a properly versioned stream/session contract rather than bypassing permission checks from JavaScript.

Media is stored outside browser `localStorage`, with collision-safe names, atomic writes, a rebuildable index, MIME/extension validation and bounded payloads. The documented canonical paths include:

- `/var/lib/nuxel/media/pictures/Nuxel Camera/`
- `/var/lib/nuxel/media/videos/Nuxel Camera/`
- `/var/lib/nuxel/media/media-index.json`

Preserve existing media. Do not erase browser migration backups or old media as part of this mission.

### 2.3 Existing diagnostics and evidence

Use and improve, rather than discard:

- `tools/s10plus/a33/nuxel-camera-diag.sh`
- `tools/s10plus/a52/nuxel-v4l2-probe.py`
- `tools/s10plus/a52/nuxel-v4l2-capture-test.py`
- `docs/a52-camera/BASELINE-CAPTURE.json`
- `docs/a52-camera/MEDIA-TOPOLOGY.txt`
- `docs/a52-camera/HARDWARE-INVENTORY.md`
- `docs/a52-camera/HARDWARE-BLOCKERS.md`
- `docs/a52-camera/KERNEL-CAMERA-GAP.md`
- `docs/a52-camera/MEDIA-PIPELINE-ANALYSIS.md`
- `docs/a52-camera/CAMERA-APP-COMPLETE.md`
- `docs/a52-camera/CAMERA-SERVICE-API.md`
- `docs/a52-camera/PHOTOS-MEDIA-STORAGE.md`
- `docs/a52-camera/DEPLOYMENT-AND-ROLLBACK.md`
- `docs/a52-camera/TEST-RESULTS.md`
- `docs/a53/CAMERA-PIPELINE-BLOCKERS.md`
- `docs/a53/NATIVE-CAMERA-SNAPSHOT.md`

The earlier A52/A53 work is valuable evidence, but some conclusions are now stale because the probes were not using the buffer type advertised by the nodes.

## 3. Critical correction: the existing V4L2 test is not valid for the advertised API

This is the first technical task and must be completed before relying on older `ENOTTY` results.

The recorded camera nodes advertise `V4L2_CAP_VIDEO_CAPTURE_MPLANE` (multi-planar capture). However, `tools/s10plus/a52/nuxel-v4l2-capture-test.py` hardcodes:

```python
CAPTURE = 1
```

That is `V4L2_BUF_TYPE_VIDEO_CAPTURE` (single-planar), not `V4L2_BUF_TYPE_VIDEO_CAPTURE_MPLANE` (value 9). It also constructs the single-planar `v4l2_format` layout and single-planar buffer structure. The wider `nuxel-v4l2-probe.py` also uses single-planar type 1 in its format/capture path, despite the inventory reporting multi-planar capture capabilities.

Therefore:

- The old `VIDIOC_S_FMT → ENOTTY` result is not enough to prove that the Samsung driver rejects the standard V4L2 capture ABI.
- The subsequent `REQBUFS`/`QUERYBUF → EINVAL` results are also compromised by the wrong buffer type and structure layout.
- The previous docs' claim that `V4L2_CAP_EXT_PIX_FORMAT` is a Samsung vendor-private signal is incorrect. It is a standard V4L2 capability describing support for extended `struct v4l2_pix_format` fields; it does not mean the ioctl ABI is proprietary.
- `CONFIG_MEDIA_CONTROLLER` being disabled explains why no `/dev/media*` topology is exposed by this kernel build, but does not alone prove the driver has no media-controller support in source.

The Linux V4L2 API requires the application to select the right buffer type in `struct v4l2_format`; the multi-planar API has distinct format and buffer structures. The official Linux documentation distinguishes buffer type 1 from type 9 and describes the `v4l2_pix_format_mplane`/`v4l2_plane` ABI. See the research references in Part VII.

### 3.1 Replace the test with a correct probe

Implement a C diagnostic compiled against the **exact pinned target kernel UAPI headers**. C is preferred for the authoritative test because it avoids hand-recreating architecture-dependent ioctl numbers and structure layouts in Python. A Python wrapper may call the C tool and parse its JSON output.

The diagnostic must:

1. Identify the node by sysfs driver link, card name, bus info, `device_caps` and `capabilities`.
2. Run `VIDIOC_QUERYCAP` first and respect `V4L2_CAP_DEVICE_CAPS` semantics.
3. For multi-planar capture nodes, use `V4L2_BUF_TYPE_VIDEO_CAPTURE_MPLANE` consistently in `G_FMT`, `ENUM_FMT`, `TRY_FMT`, `S_FMT`, `REQBUFS`, `QUERYBUF`, `QBUF`, `DQBUF`, `STREAMON` and `STREAMOFF`.
4. Use `struct v4l2_pix_format_mplane` through the `fmt.pix_mp` union member. Correctly handle `num_planes`, `plane_fmt[]`, `bytesperline`, `sizeimage`, flags and reserved fields.
5. Use `struct v4l2_buffer` with `m.planes` pointing to a correctly sized `struct v4l2_plane[]`, `length` equal to the plane count, and each plane's `length`, `bytesused`, `data_offset` and memory offset handled correctly.
6. For single-planar-only nodes, use type 1 and single-planar structures. Never guess the API from a node number.
7. Run `G_FMT` and `ENUM_FMT` before attempting changes. Run `TRY_FMT` where implemented before `S_FMT`. Do not assume NV12 or 640×480 is supported; enumerate formats and sizes from the driver.
8. Request a small bounded buffer count (2–3) only after the exact node is identified as an image capture endpoint. Correctly unmap/free/release all buffers; always attempt `STREAMOFF` and `REQBUFS(count=0)` during cleanup.
9. Put a timeout around potentially blocking operations. Log each ioctl's exact request, type, structure size, return code and errno. Never hang an audio/session manager.
10. Save results as machine-readable JSON and a human-readable report, including running kernel identity/config, test binary hash, exact headers used and device topology.

Also run a target-compatible `v4l2-ctl` build with its explicit multi-planar type where available, e.g. `--type=video_capture_mplane`. Record tool version and ABI. Do not treat generic output produced using the wrong type as evidence.

### 3.2 Correct meaning of the capability bit

`V4L2_CAP_EXT_PIX_FORMAT` means the device supports extended fields in `struct v4l2_pix_format`. For the single-planar API, the application must handle `V4L2_PIX_FMT_PRIV_MAGIC` and initialize the relevant fields as documented. Do not use this bit as proof of proprietary Samsung commands. It remains possible that FIMC-IS stream configuration requires Samsung-private controls/ioctls; establish that by reading the exact driver implementation, not by interpreting this bit.

### 3.3 Required diagnostic outcome

The corrected diagnostic must distinguish at least:

- `STANDARD_MPLANE_SUPPORTED` — correct multi-planar format negotiation works.
- `STANDARD_MPLANE_FORMAT_ENUM_EMPTY` — ioctl exists but no format enumeration is exposed on this node.
- `STANDARD_MPLANE_UNSUPPORTED` — correct type/ABI gets an unsupported response and exact driver source confirms the callback is absent or rejects it.
- `WRONG_NODE_ROLE` — node is metadata, output, mem2mem, internal processing or a non-capture endpoint.
- `PRIVATE_UAPI_REQUIRED` — standard flow is genuinely unsupported and driver source exposes a vendor-specific contract.
- `MISSING_FIRMWARE` — a specific required firmware request fails.
- `MEDIA_GRAPH_NOT_EXPOSED` — a media-controller config/registration gap is established.
- `SENSOR_POWER_OR_CSI_FAILURE` — sensor/clock/regulator/CSI initialization fails.
- `CAPTURE_STREAM_VERIFIED` — only after real image bytes are obtained.

Do not collapse all failures into one generic `HARDWARE_BLOCKED` status.

---

# PART II — RECOMMENDED TECHNICAL STRATEGY

## 4. Ranked route decision

The correct strategy is a staged hybrid investigation with a strong preference for native Linux capture. Do not skip the cheap, high-value corrections and jump directly to a large Android runtime.

### Path A — Correct standard V4L2 multi-planar capture

**Try this first.** The recorded node capabilities and test mismatch make this the highest-value first experiment. If correct multi-planar streaming works, a private driver adapter may not be needed for the first rear-main camera.

Required result: the rear-main sensor is configured through the existing FIMC-IS pipeline, queued buffers complete, and valid image bytes are returned. If correct ioctls work but the node needs sensor/ISP route setup, proceed to Path B or C without mislabelling the failure as proprietary.

### Path B — Enable the media-controller/subdevice surface supported by the exact kernel

The November 3 live config snapshot includes `CONFIG_VIDEO_EXYNOS_FIMC_IS2=y`, but `CONFIG_MEDIA_CONTROLLER` is not set. The current fragment explicitly kept media-controller support off to protect unrelated MFC/display work during an earlier mission. That was not a camera capability assessment.

Inspect exact source Kconfig and implementation before selecting symbols. If supported and necessary, build a separate camera experiment profile with the required media-controller, V4L2 subdevice API, async notifier, firmware loader, videobuf2 and Exynos dependencies actually referenced by the driver. Do not guess symbol names. Do not enable unrelated Exynos drivers because their names look similar.

If the exact driver does not register media entities/links even with the necessary options, document that from source. `CONFIG_MEDIA_CONTROLLER=y` by itself cannot invent a graph that the driver does not register.

### Path C — Implement the exact Samsung FIMC-IS2 userspace ABI

If the driver genuinely uses a vendor-specific format/stream interface, build an adapter that speaks the actual interface from the exact pinned kernel source. Do not write guessed ioctl numbers, undocumented register writes, or a libcamera pipeline handler based on another Exynos generation.

Preferred engineering choices:

- First create a small isolated C proof-of-concept that follows the exact driver's state machine and captures one frame.
- Define a documented, typed, versioned UAPI wrapper around the proven driver operations.
- Build a privilege-minimized Nuxel camera daemon that owns camera nodes, controls sensor routing, manages buffers, delivers frames, and exposes a narrow D-Bus or PipeWire-facing interface.
- Only after a stable stream is captured, write a libcamera pipeline handler or PipeWire SPA source if those abstractions materially improve application integration.

Do not spend the first week writing libcamera scaffolding before knowing the correct sensor-to-ISP-to-capture-node sequence.

### Path D — Exact-device Samsung Android camera stack as a controlled fallback/reference

Samsung-derived Android distributions for the S10+ provide camera support. Public `beyond2lte` vendor build files list matching Exynos 9820 camera components, including `camera.exynos9820`, `libexynoscamera3`, FIMC-IS firmware and per-sensor setfiles. This establishes that an exact-device vendor HAL route exists; it does **not** mean those binaries can be copied into Fedora as independent libraries.

Use this route in one of two ways:

1. **Reference/ABI discovery:** inspect exact camera-provider/HAL sources and compatible Android device/ROM build metadata, then compare its interactions with the same pinned kernel driver. If a working owner-provided, exact-device Android system is available, use its software/logs as a reference under the owner's control.
2. **Isolated runtime fallback:** only if native Linux capture cannot be made operational after the source/UAPI route is fully exercised, build a properly isolated Android userspace/runtime using the matching `beyond2lte` platform/vendor stack and its required Binder/HwBinder/vendor services. Export camera frames into Nuxel through a narrow explicit bridge. A Bionic `.so` copied into Fedora is not a valid HAL integration.

Any proprietary binary must come from a lawful, owner-authorized, exact-device firmware/source and remain local unless its license permits redistribution. Never substitute `beyond1lte`, `beyondx`, Note10/Exynos 9825, Snapdragon or unrelated camera blobs. The same SoC family does not make every device's calibration, setfile, secure-camera configuration or vendor interface interchangeable.

### Required decision gates

- Do not choose Path C until Path A is correctly tested and exact driver source supports that conclusion.
- Do not choose Path B until Kconfig and the driver's media registration code are inspected.
- Do not choose Path D merely because it looks expedient; first establish precise dependencies and an isolation architecture.
- If native Linux is blocked by genuine driver ABI limits, proceed to the controlled fallback. The outcome remains a working Nuxel Camera app, not a report that the UI is ready.

## 5. Technical conclusion and research-led recommendation

The current evidence supports this order:

1. **Correct the invalid mplane probe.** This is a cheap, high-probability correction and may immediately reveal a standard capture interface.
2. **Restore exact camera firmware.** The firmware manifest and source fetcher already exist; use them rather than inventing blob provenance.
3. **Inspect the pinned FIMC-IS2 implementation.** Decide whether the driver exposes standard mplane, needs media routing, has a private userspace ABI, or combines these.
4. **Build a separate camera-enabled kernel profile only if source/config evidence demands it.** Keep the known-good profile untouched.
5. **Create a real rear-main capture proof.** No application framework work before this minimal hardware proof.
6. **Integrate with the existing Nuxel backend and PWA.** Use PipeWire/portal only if it materially enables WebKit `getUserMedia` and can be filtered to the camera source.
7. **Use exact Samsung Android camera runtime as fallback/reference.** Do not stop if the native attempt reveals genuine proprietary requirements.

A mainline libcamera install alone is not a solution: libcamera needs a pipeline handler for the platform's camera pipeline. Its pipeline-handler model is built around media-controller/V4L2 interfaces and platform-specific configuration. There is no basis in this repository to assume an Exynos 9820 FIMC-IS2 handler already exists in the installed version. Verify the current upstream handler list and, if required, implement a handler only after the raw capture sequence is known.

---

# PART III — EXECUTION PLAN

## 6. Phase 0: preserve the working phone and establish a reproducible baseline

Before changes:

1. Verify repository root, branch, current commit, dirty files, untracked files and active worktree. Do not overwrite unrelated user work.
2. Create a dedicated branch or worktree for camera development. Record the exact base commit and ZIP snapshot timestamp.
3. Back up every file/config/service that will be edited. Keep original camera diagnostics so old findings remain auditable; do not silently rewrite test history.
4. Verify the connected target is S10+ `beyond2lte` / `SM-G975F`. If it is not the expected model, stop device-side writes and re-scope.
5. Use the repository's existing Wi-Fi helper where possible:

   ```sh
   scripts/s10plus-debug-pack/nuxel-live-ssh.sh --transport wlan --status
   ```

   Discover the current address from helper output; do not guess or hardcode an IP. Reuse the user's existing SSH identity and host-key verification. Never display, copy, commit or log private-key contents.
6. Begin with read-only device probes. Capture `uname -a`, `/proc/version`, `/proc/cmdline`, `/proc/config.gz` or the exact installed config, device-tree model/compatible strings, rootfs mount state, free space, temperature and uptime.
7. Collect `dmesg` and journal excerpts filtered for FIMC, camera, sensor, CSI, IOMMU, DMA, firmware, secure camera, OIS, EEPROM and ISP. Preserve original logs privately where appropriate.
8. Inventory `/dev/video*`, `/dev/media*`, `/dev/v4l-subdev*`, `/sys/class/video4linux`, `/sys/class/media`, `/sys/bus/platform/drivers` and `/sys/devices/svc/Camera`. Include permissions, symlinks, driver, bus info and capabilities.
9. Inventory firmware paths actually present: `/lib/firmware`, `/usr/lib/firmware`, `/vendor/firmware` and any device-specific firmware-loader fallback path. Record each expected camera blob's filename, size and SHA-256.
10. Inventory installed/active PipeWire, WirePlumber, libcamera, GStreamer, WebKitGTK, GTK, xdg-desktop-portal, camera portal and browser packages/versions. Do not install anything until the baseline exists.
11. Check whether an Android compatibility runtime, Binder nodes/services or Android userspace is actually installed. The supplied ZIP does not establish that Waydroid/Anbox exists in Nuxel; do not assume SnekByte is an Android runtime. Verify the live rootfs.
12. Write `docs/pwnage-83000/00-baseline.md`, `baseline.json` and raw diagnostic artifacts.

**Deliverable:** a timestamped current hardware/software map that matches the physical phone now, not just October/November snapshots.

## 7. Phase 1: correct and validate the camera diagnostics

This phase must finish before any architecture is selected.

### 7.1 C V4L2 probe

Add a C tool, for example `tools/s10plus/camera/nuxel-v4l2-mplane-probe.c`, compiled against headers from the exact pinned kernel tree (and optionally compile against the host toolchain as a separately labelled comparison). C is preferred for the authoritative test because it avoids hand-recreating architecture-dependent ioctl numbers and structure layouts in Python.

It must report:

- `VIDIOC_QUERYCAP` driver/card/bus/version/capabilities/device_caps.
- Exact node identity from sysfs.
- All supported buffer types relevant to that node.
- `VIDIOC_ENUM_FMT` for the buffer type(s) indicated by `QUERYCAP`.
- `VIDIOC_G_FMT` current format.
- `VIDIOC_TRY_FMT` for formats/sizes reported by enumeration.
- Frame-size and frame-interval enumeration where implemented.
- `VIDIOC_G_PARM`/`S_PARM` where applicable.
- Controls through `VIDIOC_QUERY_EXT_CTRL` or the correct legacy controls supported by this old kernel.
- Exact failures; no swallowed errno or ambiguous `unsupported` output.

When `device_caps` says multi-planar capture, use type 9 and `fmt.pix_mp`. For queueing use valid plane arrays and UAPI structure definitions. Respect `V4L2_CAP_DEVICE_CAPS` semantics.

### 7.2 Correct the Python probe/test

Python may remain as wrapper/reporting tooling, but must not be the authoritative architecture-specific ioctl implementation. If Python ioctl code is retained, generate or validate its constants and structure layout against compiled C `sizeof`/`offsetof` results from the exact ARM64 headers.

Specifically fix:

- `CAPTURE = 1` versus `V4L2_BUF_TYPE_VIDEO_CAPTURE_MPLANE = 9` for mplane nodes.
- `struct v4l2_format` union member/offset for `pix_mp`.
- `struct v4l2_buffer` with multi-planar `m.planes`, `length`, and correct `struct v4l2_plane[]`.
- `bytesused`, `data_offset`, `length`, `mem_offset`, and mapping length handling for every plane.
- `ENUM_FMT`, `G_FMT`, `TRY_FMT`, `S_FMT`, `REQBUFS`, `QUERYBUF`, `QBUF`, `DQBUF`, `STREAMON` and `STREAMOFF` all using the same valid buffer type.

### 7.3 Test progression

Run these steps in order:

1. `QUERYCAP` only.
2. `G_FMT` only with the correct capture type.
3. `ENUM_FMT` and frame-size/interval enumeration.
4. `TRY_FMT` using an enumerated mode.
5. `S_FMT` only on a confirmed capture node and after validation.
6. Small buffer allocation and queue/dequeue test with complete cleanup.
7. A single bounded stream-on test, maximum 2–3 buffers, timeout enforced, one node, one sensor path.
8. Save one frame, verify plane layout/byte lengths, decode and inspect pixels.

Do not attempt to stream every node. Some nodes are internal stages, metadata, mem2mem or vendor endpoints. Identify the pipeline from source first.

### 7.4 External command validation

If available, run a target-compatible `v4l2-ctl` with explicit `--type=video_capture_mplane`. Save command version and output. A command-line tool reporting no format using the wrong type is not evidence.

**Deliverable:** `docs/pwnage-83000/01-v4l2-corrected-report.md`, corrected test source, deterministic host tests and fresh physical-device output.

## 8. Phase 2: inspect the exact FIMC-IS2 kernel implementation

Fetch source into an isolated directory and verify the exact pinned commit:

```sh
git clone https://github.com/Linux4/android_kernel_samsung_exynos9820.git kernel-source
cd kernel-source
git checkout f7194c1d15eded1c2a1a4dc63825b26103435cc0
test "$(git rev-parse HEAD)" = f7194c1d15eded1c2a1a4dc63825b26103435cc0
```

If the Git URL/path changes, obtain the archive at that immutable commit and verify it. Do not silently use the moving default branch.

### 8.1 Trace the complete driver stack

Inspect exact source, Kconfig, headers, device tree and existing Nuxel patches for:

- `VIDEO_EXYNOS_FIMC_IS2` and all dependent Kconfig symbols.
- FIMC-IS2 probe/registration and the `fimc_is` core.
- Video-node initialization/registration and role-specific names.
- `v4l2_ioctl_ops`, `.unlocked_ioctl`, `.vidioc_default`, `vidioc_querycap`, `vidioc_enum_fmt_vid_cap_mplane`, `vidioc_g_fmt_vid_cap_mplane`, `vidioc_try_fmt_vid_cap_mplane`, `vidioc_s_fmt_vid_cap_mplane` and buffer callbacks.
- Whether standard mplane ioctls are registered but constrained by pipeline state.
- Samsung-specific `VIDIOC_PRIVATE`, `V4L2_CID_PRIVATE_BASE`, vendor `S_CTRL`/`G_CTRL`, `EXT_CTRLS`, `setfile`, `stream`, `sensor`, `ischain` or `subdev` operations.
- Exact header files and ioctl values used by matching Samsung userspace.
- `request_firmware()` / `request_firmware_direct()` calls, exact firmware names, optional/required behavior and call order.
- Firmware memory allocation/placement, DMA/CMA/ION requirements, IOMMU attachments, secure-camera SMC calls and error unwinding.
- Sensor power/reset/clock/regulator sequences and link from sensor module to FIMC-IS virtual channel.
- Media entity/pad/link registration, async notifier, subdevice-node creation, `media_device_register()` and config guards.
- Buffer allocator requirements and any use of Android ION, DMA-BUF, secure memory or proprietary gralloc handles.

Do not infer the ABI from another SoC's FIMC or a mainline Exynos4 driver. This is Exynos 9820 FIMC-IS2.

### 8.2 Produce a source-derived map

Create a table with exact source and live evidence:

| Item | Exact source symbol/path | Live evidence | Finding |
|---|---|---|---|
| sensor driver | | | |
| CSI receiver | | | |
| ISP/FIMC-IS core | | | |
| capture endpoint | | | |
| format-negotiation callback | | | |
| queue/buffer callback | | | |
| private ioctls/controls | | | |
| media-entity registration | | | |
| firmware requests | | | |
| memory allocator | | | |
| secure-camera operation | | | |

Every finding must be evidence-backed. If a callback is not registered for a node, record the exact omission. If it is registered, record state prerequisites before it succeeds.

### 8.3 Decide whether kernel source must change

Prioritize using the existing driver unmodified. If the code is correct but config omitted a feature, use a config-only camera profile. If the code has a concrete missing standard callback or broken integration needed by Nuxel, patch it in a minimal isolated patch series. Do not rewrite the camera driver wholesale.

**Deliverable:** `docs/pwnage-83000/02-kernel-source-map.md`, exact source commit record and Kconfig/dependency analysis.

## 9. Phase 3: firmware and sensor setfiles

The current ZIP already contains a pinned vendor-blob fetcher and a camera firmware section in `firmware/s10plus/manifest.yml`. Camera entries are `required: false`, which is reasonable for a general rootfs but not for a camera-enabled S10+ image profile.

### 9.1 Files listed in the current manifest

The manifest currently includes these camera/ISP firmware names:

- `dnn.bin`
- `dual_cal_front_subfront.bin`
- `fimc_is_fw_mcu.bin`
- `fimc_is_lib.bin`
- `fimc_is_rta.bin`
- `fmsb.bin`
- `rxse.bin`
- `setfile_2l4.bin`
- `setfile_3j1.bin`
- `setfile_3m3.bin`
- `setfile_3p9.bin`
- `setfile_4ha.bin`
- `txse1.bin`
- `txse2.bin`
- `txse3.bin`

The supplied manifest includes SHA-256 values for these entries. Treat them as expected values to verify, not proof that each blob exists locally or applies to every sensor. Recompute hashes from the pinned source and compare.

### 9.2 Use the repository's pinned fetcher

Audit and use `firmware/s10plus/fetch-vendor-blobs.sh`. It points at:

- Repository: `Linux4/proprietary_vendor_samsung`
- Pinned commit: `05c9ef8f16e0ad5ab274e408c120dfd99fd5c628`
- Firmware trees: `exynos9820-common/proprietary/vendor/firmware/` and `beyond2lte/proprietary/vendor/firmware/`

This is a promising local build-time acquisition path and may avoid using recovery simply to obtain firmware. Do not rely on comments alone: inspect the fetch script, verify its tree API results, validate each downloaded object against the manifest, and confirm exact `beyond2lte` file origin. Preserve nested source paths to avoid same-basename collisions.

If the pinned source lacks a required exact blob, use only a lawful, owner-authorized extraction from this exact S10+ and its matching Samsung firmware build. Prefer read-only extraction from the owner's own stock/vendor image or owner-held ROM package. Do not use blobs from unrelated phones, board revisions, SoC families or camera module variants.

### 9.3 Firmware request contract first, install path second

Do not assume `/lib/firmware` is correct because the manifest currently uses it. Do not assume `/vendor/firmware` merely because historical kernel command-line evidence includes `firmware_class.path=/vendor/firmware`.

For each firmware file, inspect the exact driver caller and record:

- Requested filename.
- `request_firmware` variant and flags.
- Calling function and initialization stage.
- Synchronous or asynchronous load behavior.
- Required sensor/model/feature dependency.
- Actual search-path behavior on this 4.14 kernel.
- Final Nuxel destination and file permissions.
- Manifest checksum and actual checksum.
- dmesg evidence that the request completed successfully.

Do not create global symlinks or alter boot arguments until source and observed request behavior prove they are required. If a compatibility path is needed, make it a deterministic image-build rule and document it.

### 9.4 Manifest and packaging changes

Implement a **camera-enabled S10+ profile** separate from generic Nuxel rootfs builds:

- In the camera profile, every blob proven necessary for rear-main operation must fail the image build if missing or hash-mismatched.
- Mark front and secondary-rear blobs required only for profiles/features that use those sensors.
- Keep the general image buildable without proprietary camera blobs if that is the intended distribution policy.
- Do not package these blobs into public source releases or public binary artifacts unless the relevant license permits redistribution.
- Store local blobs in ignored build-only storage or the established local firmware cache; do not commit them accidentally.
- Add build-time manifest auditing and a device-side deployment audit.

### 9.5 Sensor mapping corrections

The current hardware inventory records:

| Camera role | FIMC-IS module |
|---|---|
| Rear main | `2L4` |
| Rear telephoto | `3M3` |
| Rear ultrawide | `3P9` |
| Front main | `3J1` |
| Front depth/IR | `4HA` |

The inventory corrects an old front-camera naming assumption: the front main is `3J1`, not the historical `s5k2l4sx_front` guess. Update sensor profiles, camera config, diagnostics, UI labels and firmware lookups to use source-confirmed modules. Do not infer a sensor role from a filename alone.

**Deliverables:** `docs/pwnage-83000/03-firmware-contract.md`, corrected camera firmware profile/manifest logic, local firmware verification log (hashes only in public docs), and a device diagnostic that reports exactly which required sensor/ISP blob is missing or loaded.

## 10. Phase 4: build and test a camera-enabled kernel profile

The main working kernel config contains critical functions that must survive. `kernel/s10plus/configs/nuxel-drm-kbase.fragment` protects the known-good panel/display route and Mali-G76 kbase path. It also keeps generic camera/media-controller features conservative because an earlier PWNAGE-61000 mission focused on MFC stability, not camera bring-up.

### 10.1 Preserve the working hardware baseline

Preserve, unless the exact camera investigation proves a change is required and a separate validated patch is made:

- `CONFIG_EXYNOS_DPU20` and the fbdev AMOLED display path.
- The current non-conflicting DRM setup. Never enable the Exynos7 DECON driver that competes for the existing display registration in this kernel.
- Mali-G76 Bifrost/kbase driver and `/dev/mali0`.
- Existing Wi-Fi, Bluetooth, audio, NFC, storage, USB, charging, touchscreen, sensors and modem behavior.
- Current MFC baseline and its fail-fast missing-firmware behavior.
- Current root filesystem, SSH path and recovery access.

Do not modify the default known-good kernel config in place. Add a dedicated profile/fragment, for example `kernel/s10plus/configs/nuxel-camera-experimental.fragment`, based on the exact base defconfig plus current working fragments and only camera additions.

### 10.2 Configuration audit

Inspect actual Kconfig files. Investigate, by symbols that exist in the pinned tree:

- `CONFIG_MEDIA_SUPPORT`
- `CONFIG_MEDIA_CONTROLLER`
- `CONFIG_VIDEO_DEV`
- `CONFIG_VIDEO_V4L2`
- `CONFIG_VIDEO_V4L2_SUBDEV_API` or the exact historical equivalent
- `CONFIG_V4L2_FWNODE` / async notifier dependencies, if present
- `CONFIG_VIDEO_EXYNOS`
- `CONFIG_VIDEO_EXYNOS_FIMC_IS2`
- Exynos CSI, sensor, camera post-process, GDC, ION and DMA-BUF dependencies referenced by this driver
- `VIDEOBUF2_*` memory backends actually used by capture code
- CMA, IOMMU, DMA mapping and secure-camera dependencies

Do not blindly enable the generic `VIDEO_EXYNOS_FIMC` driver for older Exynos generations; the target uses Exynos 9820 FIMC-IS2. Do not blindly switch on every media/USB capture driver.

### 10.3 Media-controller experiment

If source shows the necessary entities/links are compiled behind `CONFIG_MEDIA_CONTROLLER`, build an experimental kernel with this and the minimum exact dependencies enabled. Check the resulting `.config` and boot logs. Verify whether `/dev/media*` and `/dev/v4l-subdev*` register and whether the camera graph is complete.

If source shows no media-entity registration at all, stop toggling config options. Move to the direct/private driver-contract route.

### 10.4 Build requirements

- Use the exact compiler/toolchain documented by `kernel/s10plus/README-toolchain.md` and existing `kernel/s10plus/build-kernel.sh` logic.
- Build in a separate output directory.
- Save complete `.config`, config diff, kernel image hash, modules hash, source commit, compiler version and build logs.
- Run existing kernel/golden/smoke checks.
- Check `modinfo` and module ABI if anything is modular. Preserve `CONFIG_MODVERSIONS`/`Module.symvers` constraints; never mix module artifacts from another build.
- Ensure the camera driver loads early enough for firmware/service startup without creating a boot race.

### 10.5 Deployment gate

Do not flash a camera test kernel merely because it compiled. Before any write:

1. Verify generated image format and expected target boot component from the exact device's current partition map.
2. Make and verify backups of current boot image/kernel and any DTB/DTBO data that would change.
3. Verify a known recovery route and user-data backups.
4. Validate the kernel image hash after transfer.
5. Change only the exact required boot component. Never write EFS, modem, persist, calibration, bootloader or unrelated partitions.
6. Have an explicit rollback workflow documented and tested before the first write.
7. Use the supported S10+ Download/Heimdall or recovery path only when proven necessary; do not assume generic Android fastboot support.
8. Preserve current userspace and boot path. No simultaneous unrelated system update.

If no kernel/DT change is required, do not flash. Do userspace and firmware deployment through the existing Nuxel update/deploy path over Wi-Fi SSH where possible.

**Deliverable:** separate experimental kernel profile, reproducible build, config diff and device validation/rollback report.

## 11. Phase 5: reconstruct and implement the capture state machine

After the corrected V4L2 probe and source map establish the route, implement a minimal real-frame capture proof before any general framework work.

### 11.1 Start with rear main only

Target rear-main `2L4`. Do not bring up all lenses simultaneously. Record exact sensor module, CSI port, media link or vendor route, ISP instance, video nodes, supported formats/modes and required firmware.

### 11.2 Native standard V4L2 case

If standard mplane capture works:

- Configure the correct sensor/ISP route using the actual media graph or driver interface.
- Select a pixel format and frame size enumerated by the hardware. Do not assume NV12, YUYV, JPEG or any unsupported resolution.
- Negotiate format using the correct API.
- Allocate buffers with MMAP or the allocator supported by the node.
- Queue, stream, dequeue and validate buffers.
- Save one raw frame with metadata describing plane order, stride, color format and timestamp.
- Convert only in a separately tested step; retain the original raw data for debugging.

### 11.3 Vendor UAPI case

If standard V4L2 cannot perform required configuration:

- Locate real Samsung UAPI header(s) in the pinned kernel source.
- Trace every private ioctl/control definition to its implementation and caller.
- Record exact structure layout, alignment, pointer width, endianness, ABI version, return semantics and required call order.
- Build a C test program against those definitions. Do not copy ioctl values from another kernel revision or a forum post.
- Reproduce the smallest working sequence: open correct node, configure sensor/ischain, load setfile/library if required, set format, allocate buffers, queue, stream, dequeue one frame, stop and release.
- Use `strace`, ftrace or dynamic debug only where available and safe. If a matching working Samsung Android system is accessible, its logs/ioctl trace can be a reference under owner control.
- Keep any vendor UAPI adapter in an isolated library with documented C ABI and version compatibility.

### 11.4 Buffer and memory design

The Exynos 9820 camera stack may depend on ION, DMA-BUF, IOMMU and secure-camera memory semantics. Do not assume ordinary CPU `malloc` memory can be passed to ISP hardware.

Use the allocator required by the exact kernel implementation. Validate contiguous/aligned allocation, DMA-BUF import/export, cache sync and ownership transitions, per-plane offsets/strides, IOMMU mapping/device attachment, secure versus nonsecure buffers, memory pressure, and release on service crash/lock/permission revocation.

Never expose a privileged raw DMA handle to a webpage. Keep buffer ownership inside a narrow privileged camera service.

### 11.5 Frame authenticity and image validation

A captured buffer must demonstrably come from the physical sensor—not `videotestsrc`, a test pattern, stale buffer or cached frame:

- Save a short sequence of several frames.
- Inspect pixel dimensions, format, stride, checksums and decoded content.
- Compare frames while the camera points at a changing scene; content and hashes must change.
- Cover/uncover the lens and verify scene changes correspondingly.
- Check exposure changes under changing light.
- Reject uninitialized buffers, black-only frames, color bars, repeated frames or corrupt plane offsets.
- Keep any private evidence image local and remove personal EXIF/location metadata from public reports.

**Deliverable:** `rear-main-frame-proof` with raw/decoded frame metadata, real frame sequence, source state-machine documentation and an owner-observed preview test.

## 12. Phase 6: expose a clean native camera service

Once a real hardware stream exists, turn it into a single authoritative Nuxel camera backend.

### 12.1 Backend architecture

Preferred architecture:

```text
Sensor(s) -> Exynos FIMC-IS2 -> camera capture backend
  -> Nuxel camera service (single owner of nodes and buffers)
  -> PipeWire camera source / native stream API
  -> xdg-desktop-portal Camera (if needed by WebKitGTK)
  -> Nuxel Camera PWA
  -> Nuxel MediaStore -> Photos PWA
```

A direct privileged broker-to-app stream is acceptable if it is the most reliable Nuxel integration, but there must be one owner of hardware nodes and one permission/control authority. Do not run multiple capture daemons against the same ISP.

### 12.2 Service design

Implement or extend the existing camera service rather than introducing a duplicate daemon. It must provide:

- `EnumerateCameras`: stable opaque ID, human label, facing, sensor module, physical role, supported modes and online state.
- `GetCapabilities`: supported formats, sizes, frame intervals, still/video support and controls actually implemented.
- `Open` / `StartStream`: request/session ID, client identity, explicit permission token and requested mode.
- `ReadFrames` / PipeWire node: bounded stream, timestamp, frame format and metadata.
- `CaptureStill`: actual sensor still-capture path or a frame from the actual ISP path, saved atomically.
- `StartRecording` / `StopRecording`: actual encoded/raw path, truthful MIME and extension.
- `Stop` / `Release`: guaranteed close and buffer reclamation.
- `GetStatus`: typed current stage and exact error details.

Use existing `org.nuxel.Bridge` D-Bus/API patterns. Validate payload sizes, format requests, caller UIDs and path inputs.

### 12.3 Permission and privacy

- `camera:preview` authorizes stream start.
- `camera:capture` authorizes still/photo capture and recording according to Nuxel policy.
- The Permission Manager remains the single source of truth; do not build a second camera permission database.
- Revoking permission stops the active stream immediately and releases hardware.
- Locking the phone, app termination, session end, suspend, service shutdown or user switching must stop capture/recording according to existing privacy policy.
- Show an unmistakable shell in-use indicator while the sensor is open or a recording is active. The app cannot suppress it.
- No stealth recording, hidden background capture, remote upload or permission bypass.
- Camera and microphone permissions remain separate; silent camera preview must not implicitly grant microphone access.
- The physical LED/flash is not the sole privacy indicator; the shell indicator is mandatory.

### 12.4 PipeWire, WirePlumber and portal integration

Only integrate PipeWire once the capture service can reliably produce real buffers.

The current Nuxel tree deliberately disables broad WirePlumber video-capture monitoring because generic V4L2 probing/opening could touch MFC nodes and trigger a documented blocking firmware request on the old device. Keep this safety property.

- Use an explicit, narrowly scoped camera source/node created by the Nuxel service.
- Do not re-enable generic all-V4L2 scanning that opens every `/dev/video*` endpoint.
- Ensure the source matches only verified physical FIMC-IS endpoints or the service's own stream socket.
- Keep MFC video6–11, JPEG M2M, scaler, GDC and metadata nodes out of generic camera discovery.
- Test audio playback/recording, MFC decode, startup and WirePlumber while camera is off and on.
- Implement standard `org.freedesktop.portal.Camera` only through the actual xdg-desktop-portal contract and PipeWire remote-FD semantics. Do not hijack the standard name with private `org.nuxel.Camera` methods.
- Verify WebKitGTK's actual portal/backend behavior on the installed version; do not assume upstream WebKit and distro portal wiring are identical.

PipeWire is an integration layer, not a camera driver. Adding PipeWire or `v4l2src` alone does not make an unsupported sensor pipeline work.

### 12.5 Camera status and errors

Expose clear stages such as:

- `NO_CAMERA_HARDWARE`
- `SENSOR_ENUMERATED`
- `ISP_READY`
- `FIRMWARE_MISSING`
- `SENSOR_INIT_FAILED`
- `PIPELINE_NOT_CONFIGURED`
- `FORMAT_NEGOTIATION_FAILED`
- `BUFFER_ALLOCATION_FAILED`
- `STREAM_START_FAILED`
- `STREAMING`
- `CAPTURING`
- `RECORDING`
- `CAMERA_BUSY`
- `PERMISSION_DENIED`
- `THERMAL_PAUSE`
- `STORAGE_FULL`
- `SERVICE_FAILED`

Include source errno and failing stage; never turn a failed capture into a generic “camera unavailable” with no actionable detail.

**Deliverable:** native Nuxel camera service plus unit/integration tests and a PipeWire/portal test demonstrating a real camera node.

## 13. Phase 7: Android vendor HAL fallback, if native route cannot complete

This path is intentionally not first. It is the fallback that prevents the project from stopping if the Samsung driver ABI truly requires Samsung's Android camera stack.

### 13.1 Why copying one library is not enough

Exact-device vendor build files identify `camera.exynos9820`, `libexynoscamera3`, FIMC-IS MCU/library/RTA firmware and sensor setfiles. Related Samsung vendor stacks also depend on camera-provider services, Android camera HIDL interfaces, Samsung vendor interfaces, `libexynosv4l2`, allocator/gralloc/ION support, Binder/HwBinder services, Android properties, linker namespaces, SELinux policy, secure-camera/TrustZone operations and other image-processing libraries.

A Bionic Android `.so` is not automatically compatible with Fedora glibc, and the Android camera provider is not a self-contained program that can be launched in a normal Nuxel shell.

### 13.2 Prove the exact matching stack

- Identify the exact S10+ build/vendor version compatible with the Nuxel kernel and camera firmware.
- Use only `beyond2lte`/exact Exynos 9820 variants and device-specific proprietary files.
- Determine whether the source Android vendor image uses the same FIMC-IS driver ABI as the current kernel.
- Audit shared-library dependencies, symbol versions, linker namespaces, HIDL versions, Binder devices, service init files, SELinux domains, device nodes and permissions.
- Check whether secure-camera/TEE services must be started by Samsung init and cannot be reproduced outside the full vendor system.
- Verify firmware paths and calibration files remain paired with the physical module.

### 13.3 Isolated runtime options

Evaluate a minimal Android userspace/container or dedicated Android camera runtime based on actual available kernel primitives. The supplied ZIP does not prove an existing Nuxel Android runtime, so do not describe this as already installed. A workable fallback may require:

- Android userspace with compatible Bionic linker and framework services.
- Binder/HwBinder/vndbinder support and appropriate device nodes.
- Android init/service supervision for the camera provider.
- Exact vendor HAL and all transitive dependencies.
- Device-specific gralloc/ION/DMA-BUF allocator path.
- Secure-camera dependencies and SELinux/service policy.
- A bridge exporting frames to Nuxel without giving browser processes direct access to Android vendor internals.

If no safe container is possible, an alternate bootable Android userspace for camera operations may be explored as a development/reference proof, but the final product must remain Nuxel with the user-facing camera integrated. Do not present dual boot as the completed Nuxel camera experience.

### 13.4 Legal, privacy and supply-chain rules

- Do not redistribute Samsung proprietary binaries in source code, public CI artifacts or public Nuxel images unless the license permits it.
- Do not commit extracted blobs, calibration data, unique device keys, EFS or secure-world material.
- Keep local-only blob storage outside version control and document provenance/hashes.
- Use only owner-authorized device firmware. Do not fetch files from random file-sharing mirrors or unrelated device variants.
- Do not bypass camera indicators, permission grants, SELinux/security boundaries or secure-camera checks.

### 13.5 Required fallback result

The fallback only counts when the Android provider actually opens the physical sensor, captures real changing frames and Nuxel receives them through a stable service interface. Merely launching the provider or listing the HAL is not a pass.

**Deliverable:** fallback decision record, exact dependency graph, isolated runtime build/deploy recipe, real stream proof and security review.

## 14. Phase 8: complete the Nuxel Camera app and Photos workflow

Once rear-main frames reach the service:

### 14.1 Preview

- Wire the existing `getUserMedia()` UI to the real stream path.
- If WebKitGTK requires PipeWire/portal, use the correct standard portal implementation and ensure `getUserMedia` receives the genuine camera source.
- Avoid duplicate capture sessions when switching modes or toggling preview.
- Start with a mode actually supported by sensor/ISP. Prefer a stable resolution such as 1280×720 only if enumerated/negotiated successfully.
- Show clear loading/permission/initialization states; no fake frame.
- Maintain frame orientation using camera metadata and the current Nuxel rotation model, not simply screen dimensions.

### 14.2 Still photos

- Implement a real still-capture path with sensor mode, exposure, white balance and JPEG/raw processing as supported.
- If still capture uses a different resolution/format from preview, explicitly stop/reconfigure/restart safely or use a proven concurrent path.
- Save through existing MediaStore; no browser-only `localStorage` database.
- Preserve native format and truthful extension/MIME.
- Include EXIF camera make/model, timestamp, orientation and dimensions only when valid. Do not add GPS EXIF by default; require explicit opt-in.
- Make saves atomic and detect low-storage errors.

### 14.3 Video

- Verify sensor/ISP supports the chosen recording mode independently of preview.
- If the driver provides raw frames only, choose an available hardware/software encoder and benchmark it on the S10+ without exhausting memory or thermal budget. H.264/MP4 is valid only when actual encoding/packaging works; never rename WebM bytes as MP4.
- Store actual MIME/extension and duration.
- Handle storage-full, thermal throttling, interrupted stream, suspend and app closure.

### 14.4 Lens switching

After rear-main success, bring up one at a time:

1. Rear telephoto `3M3`.
2. Rear ultrawide `3P9`.
3. Front main `3J1`.
4. Front depth/IR `4HA` as a depth/auxiliary sensor if supported; do not label it a normal selfie camera.

The role-to-sensor map must be source-confirmed and live-verified. The inventory proves physical modules are present, not that every one provides a usable application stream.

Switch only after the previous stream is stopped, buffers released, node handles closed and the new sensor mode configured. Avoid lens-switch crashes.

### 14.5 Controls and flash

- Enumerate real sensor/ISP controls from V4L2 query controls or vendor UAPI.
- Implement autofocus, focus position, exposure, ISO, white balance, zoom/crop, orientation, frame rate and flash only when hardware supports them and mapping is tested.
- For LED flash, inspect the actual LED flash device/driver and its safe torch/strobe interface. Never write arbitrary GPIO/I2C registers.
- Keep unsupported controls honestly disabled until they work.

**Deliverable:** full Nuxel Camera and Photos workflow on physical hardware with accurate features and errors.

## 15. Phase 9: expand multi-camera and image-processing support

After the single rear-main path is stable:

- Enable each additional sensor one at a time.
- Validate per-sensor setfile, EEPROM calibration, OIS, sensor clock/power and CSI endpoint.
- Confirm multi-camera coordination only if hardware and HAL support it; do not assume simultaneous rear sensors work.
- Add JPEG hardware processing only when the JPEG block's actual direction/API support the operation; do not mistake a mem2mem JPEG node for a camera stream.
- Add GDC/distortion correction only when its exact input/output formats and calibration requirements are understood.
- Verify ultrawide distortion correction and telephoto lens selection separately.
- Add front camera preview/capture only after its sensor and route are proven.

Keep the main rear sensor stable as a fallback when an auxiliary lens fails.

## 16. Phase 10: robustness, performance and system integration

### 16.1 Lifecycle and reliability

Test cold boot, first launch after boot, app foreground/background, lock/unlock, permission grant/revoke while streaming, closing during still save, service crash/restart, photo/video mode switching, rapid open/close, lens switching, suspend/resume, thermal pause, audio playback/call path while camera open, MFC decode while camera is closed and (if supported) open, memory pressure and storage-full behavior.

### 16.2 Resource control

- Prefer zero-copy/DMA-BUF only after cache, IOMMU and format semantics are verified.
- Use a bounded buffer pool; never queue unlimited frames through the UI/bridge.
- Drop stale preview frames instead of accumulating latency.
- Separate preview cadence from still capture and video encoding.
- Track CPU, GPU, ISP, DDR bandwidth, temperature, battery drain, dropped frames and frame latency.
- Choose conservative defaults based on observed sensor modes/thermals, not marketing specifications.

### 16.3 Keep system stability

After each kernel/firmware change verify display/fbdev, Mali/Phoc, Wi-Fi SSH, USB console, touch, audio, MFC, Bluetooth, NFC, charging, suspend/resume, boot/reboot, launcher and media playback.

Never re-enable all generic V4L2 scanning or open unrelated video endpoints just to make a camera appear in PipeWire. Route only the proven camera source.

---

# PART IV — TESTING AND ACCEPTANCE

## 17. Test matrix

### 17.1 Host-side deterministic tests

Add tests for:

- C probe capability parsing and single/multi-planar API selection.
- `sizeof`/`offsetof` ABI agreement with exact ARM64 target headers.
- Plane count, buffer mapping, `bytesused` and `data_offset` calculations.
- Correct cleanup on every failure path.
- Firmware manifest hashes and camera-profile required/optional logic.
- Sensor role mapping (`2L4`, `3M3`, `3P9`, `3J1`, `4HA`).
- Firmware request-name-to-manifest mapping.
- Driver state machine and error translation.
- Camera service authorization, session lifecycle and concurrency lock.
- Permission revocation stopping all streams and releasing buffers.
- MediaStore atomic writes, MIME/extension validation and failure handling.
- Camera-active indicator logic.
- No synthetic source reported as hardware and no false `capture_verified` state.
- PipeWire/portal API contracts and filtered node matching.
- Regression that WirePlumber never probes MFC nodes as cameras.

Keep existing Nuxel golden/smoke and camera tests passing. Fixture-only tests never prove physical hardware.

### 17.2 Physical S10+ hardware acceptance

**Gate 1 — Enumeration:** correct target identity, live driver, sensor modules bound and correct capture endpoint identified.

**Gate 2 — Firmware:** every required rear-main blob has exact provenance/hash, correct install path and successful load evidence.

**Gate 3 — Interface:** correct multi-planar standard V4L2 or exact vendor UAPI path negotiates and allocates buffers.

**Gate 4 — Stream:** rear-main sensor starts and produces non-empty, valid frame buffers.

**Gate 5 — Real image:** decoded frames depict the physical scene; cover/uncover and scene movement change captured content as expected.

**Gate 6 — UI preview:** Nuxel Camera shows the real camera, active indicator is visible, and permission denial/revocation works.

**Gate 7 — Still photo:** shutter saves a real photo to existing MediaStore and Photos displays that exact saved file.

**Gate 8 — Video:** records a real scene for at least 15 seconds (or another explicitly declared bounded test duration), stops cleanly, saves with correct MIME/extension and plays in Photos.

**Gate 9 — Stability:** repeated open/close, lock/unlock, permission revoke and reboot pass without wedging audio, MFC, systemd or UI.

**Gate 10 — Owner confirmation:** owner looks at the physical Nuxel screen, confirms preview is the S10+ rear camera, takes a photo and plays a clip. Do not state the phone camera works until this gate passes.

### 17.3 Minimum proof bundle

Save under `docs/pwnage-83000/evidence/`:

- Exact device model/codename and kernel release.
- Kernel source commit and config hash.
- V4L2 node-to-driver map.
- Corrected mplane test output or exact vendor UAPI trace.
- Firmware manifest, provenance, filenames, sizes and SHA-256 values (no proprietary blob bytes in public docs).
- Relevant dmesg/journal excerpts.
- Sensor route and mode data.
- Frame dimensions, pixel format, plane metadata, timestamps and checksums.
- Private image proof with personal metadata removed from public reports.
- Nuxel Camera preview/still/video test results.
- MediaStore file listing and MIME verification.
- Permission and lifecycle test outcomes.
- Kernel deployment/rollback evidence if a kernel change was necessary.
- Known remaining limitations.

## 18. Explicit definition of DONE

`CAMERA_WORKING` may be declared only after all of these are true:

1. The physical rear-main S10+ sensor is selected and initialized by a proven stack.
2. A live sequence of real sensor frames is obtained.
3. Nuxel Camera renders those frames with correct orientation and a functioning in-use indicator.
4. A still is captured, atomically saved, opened and displayed by Nuxel Photos.
5. A real video is captured, saved with correct format metadata and played back.
6. Permission denial/revocation stops capture and the service releases sensor/buffers.
7. No fake/test source is reported as physical camera.
8. The owner confirms preview, still and video on the actual phone.
9. Existing Nuxel phone functionality remains healthy and recovery/rollback is available.
10. Relevant documentation and evidence are updated.

Secondary-lens support may be reported separately, but rear-main camera support is the minimum product milestone. Do not label the overall camera system fully complete while expected lenses remain unimplemented; report each role separately.

Use precise states:

- `SOURCE_AUDITED`
- `V4L2_ABI_CORRECTED`
- `FIRMWARE_VERIFIED`
- `KERNEL_PROFILE_BUILT`
- `KERNEL_DEPLOYED`
- `DRIVER_INITIALIZED`
- `REAR_MAIN_STREAM_VERIFIED`
- `NUXEL_PREVIEW_VERIFIED`
- `STILL_CAPTURE_VERIFIED`
- `VIDEO_CAPTURE_VERIFIED`
- `OWNER_CONFIRMED`
- `SECONDARY_SENSOR_VERIFIED`
- `BLOCKED_WITH_EXACT_STAGE`

A build is not a deployment. A deployment is not a stream. A stream is not an image. An image is not a working Camera app. Keep these states separate.

---

# PART V — SAFETY, CHANGE CONTROL AND ROLLBACK

## 19. Device and data safety

Allowed when evidence supports it:

- Read-only hardware/firmware inventory.
- Installing verified matching camera firmware into the Nuxel rootfs.
- Building a new camera-enabled kernel profile.
- Replacing a test camera service/app in Nuxel.
- Carefully deploying a verified camera kernel if current driver/config makes it necessary and rollback is prepared.
- Controlled use of an exact-device Android camera stack in an isolated runtime.

Never do:

- Blind I²C, SPI, GPIO, regulator, clock or register writes.
- Write to EFS, EFS2, modem/radio, persist, calibration, secure-world, bootloader, RPMB or unknown partitions.
- Substitute calibration/EEPROM/setfile blobs from another phone or camera module.
- Flash an unrelated kernel, DTB, DTBO, recovery image or ROM.
- Assume generic fastboot is supported in the normal bootloader workflow; confirm exact S10+ Download-mode tooling first.
- Commit private keys, owner photos, camera calibration, secure material, proprietary vendor binaries or device serials.
- Disable camera permission controls, camera indicator, SELinux/security boundaries or secure-camera handshakes.
- Leave a camera stream open after app exit, lock or permission revocation.
- Expose a privileged camera device or arbitrary filesystem paths to an untrusted webpage.

## 20. Rollback

Every deployment step must be reversible:

- Keep current rootfs packages/configs and service units backed up.
- Keep a separate copy of current camera and kernel config fragments.
- Keep original boot image/kernel/DT artifacts before any boot-component change.
- Record current partition layout and image hash before any write.
- Verify recovery route before testing a new kernel.
- Make deployment atomic where possible; stage new binaries, then switch a symlink or unit.
- Provide explicit commands to restore prior packages, config, firmware selection and boot image.
- Never wipe user data, existing photos or media as a rollback tactic.

If a test kernel fails to boot or loses Wi-Fi/USB/recovery access, revert to the known-good boot image through the prevalidated recovery workflow. Do not keep making speculative writes.

---

# PART VI — REQUIRED REPOSITORY CHANGES AND DOCUMENTATION

## 21. Files to update or create

Keep the existing documentation history, but revise stale conclusions and add new evidence.

### 21.1 Correct existing files

At minimum, inspect/update as applicable:

- `tools/s10plus/a52/nuxel-v4l2-probe.py`
- `tools/s10plus/a52/nuxel-v4l2-capture-test.py`
- `tools/s10plus/a33/nuxel-camera-diag.sh`
- `configs/nuxel/camera/camera.json`
- `configs/nuxel/privacy/camera.json` (if status/permission model needs new states)
- `firmware/s10plus/manifest.yml`
- `firmware/s10plus/install-firmware.sh` (camera-profile requirement/verification)
- `firmware/s10plus/fetch-vendor-blobs.sh` only if audit finds a real correctness/robustness defect
- Camera service, bridge and Camera/Photos PWA only where necessary to connect real frames.
- Existing A52/A53 blocker docs: append a superseding correction section and link new evidence; do not erase prior test results.

Update the stale camera config rule that blanket-lists `android.hardware.camera.provider`, `libcamera_hal*` and `libexynoscamera*` under `never_install`. Replace it with an explicit policy model:

- Default Nuxel remains native-first and must not install Android vendor binaries into the host namespace.
- A local, owner-authorized, exact-device Android fallback may be built/tested in an isolated runtime when the documented native route is genuinely blocked.
- No random, unrelated, or unlicensed camera blob may enter the image.
- The camera diagnostics must report which backend is selected and why; no silent fallback.

Correct all references that call `V4L2_CAP_EXT_PIX_FORMAT` a Samsung-private ioctl signal. Correct the old single-planar probe conclusion and link the corrected mplane report. Keep the original historical outputs in evidence and mark them `INVALID_FOR_MPLANE_NODES` where appropriate.

### 21.2 New mission documentation

Create:

```text
docs/pwnage-83000/
  README.md
  00-baseline.md
  01-v4l2-corrected-report.md
  02-kernel-source-map.md
  03-firmware-contract.md
  04-kernel-camera-profile.md
  05-capture-state-machine.md
  06-native-camera-service.md
  07-android-fallback-assessment.md
  08-camera-app-integration.md
  09-hardware-validation.md
  10-rollback.md
  status.json
  evidence/
```

A phase document may be marked `NOT_APPLICABLE` only with source-backed explanation. Record unfinished or blocked phases explicitly; do not delete them.

### 21.3 Diagnostic output contract

The hardware diagnostic should emit a stable JSON schema with:

- Device identity and kernel commit/release.
- `camera_backend` (`native-v4l2`, `native-private-uapi`, `android-isolated`, `none`).
- Sensor list and per-sensor mapping.
- Driver binding and capture endpoints.
- Media topology and capabilities.
- Firmware required/present/hash/loaded states.
- Correct V4L2 API type per node.
- Current stream/session and permission state.
- Failure stage, errno, relevant kernel messages and recovery hint.
- Verified frame evidence count and capture status.

Never infer `capture_verified=true` from driver name, video node existence, firmware presence, daemon PID, test pattern, or UI preview element creation.

---

# PART VII — RESEARCH REFERENCES AND FACT CHECKING

## 22. Sources to use

These sources inform the strategy; verify their current content and exact branch/commit before using them as implementation truth.

### 22.1 Exact kernel and target device

- Pinned downstream kernel source: <https://github.com/Linux4/android_kernel_samsung_exynos9820>
- Immutable kernel source commit: <https://github.com/Linux4/android_kernel_samsung_exynos9820/tree/f7194c1d15eded1c2a1a4dc63825b26103435cc0>
- postmarketOS package recipe showing the `Linux4/android_kernel_samsung_exynos9820` repository and same pinned commit: <https://gitlab.com/postmarketOS/pmaports/-/blob/master/device/testing/linux-samsung-beyond1lte/APKBUILD>
- LineageOS device profile for `beyond2lte` / Galaxy S10+: <https://github.com/LineageOS/lineage_wiki/blob/main/_data/devices/beyond2lte.yml>
- Exact-device lineage release information and camera-related changelog history: <https://lineage.linux4.de/devices/beyond2lte.html> and <https://lineage.linux4.de/changes/beyond2lte.html>

### 22.2 V4L2 API correctness

- Linux V4L2 capture interface: <https://docs.kernel.org/userspace-api/media/v4l/dev-capture.html>
- Linux multi-planar API: <https://docs.kernel.org/userspace-api/media/v4l/planar-apis.html>
- Linux V4L2 buffer types and plane buffer structures: <https://docs.kernel.org/userspace-api/media/v4l/buffer.html>
- Linux `VIDIOC_G_FMT`/`S_FMT`/`TRY_FMT`: <https://www.kernel.org/doc/html/v4.10/media/uapi/v4l/vidioc-g-fmt.html>
- Linux `VIDIOC_QUERYCAP`: <https://docs.kernel.org/userspace-api/media/v4l/vidioc-querycap.html>
- `V4L2_CAP_EXT_PIX_FORMAT` and extended pixel-format fields: <https://docs.kernel.org/userspace-api/media/v4l/pixfmt-v4l2.html>

The key definitions to preserve in diagnostics are:

- `V4L2_BUF_TYPE_VIDEO_CAPTURE = 1` (single-planar).
- `V4L2_BUF_TYPE_VIDEO_CAPTURE_MPLANE = 9` (multi-planar).
- `V4L2_CAP_VIDEO_CAPTURE_MPLANE = 0x00001000`.
- `V4L2_CAP_EXT_PIX_FORMAT = 0x00200000` means extended `v4l2_pix_format` fields are supported; it does not by itself identify a vendor-private ABI.

### 22.3 Exact-device firmware/HAL reference

- Exact `beyond2lte` public vendor build file listing the Exynos 9820 camera HAL component, FIMC-IS firmware and sensor setfiles: <https://github.com/Evolution-X-Devices/vendor_samsung_beyond2lte/blob/bka/beyond2lte-vendor.mk>
- Pinned vendor firmware repository used by the Nuxel fetch script: <https://github.com/Linux4/proprietary_vendor_samsung/tree/05c9ef8f16e0ad5ab274e408c120dfd99fd5c628>
- Exact target device tree reference: <https://github.com/whatawurst/android_device_samsung_beyond2lte>

The public vendor makefile is evidence that matching blobs/components exist for this device family, not permission to redistribute them or proof that a particular Android HAL package can run in Fedora. Verify the exact `SM-G975F` variant and vendor firmware version.

### 22.4 libcamera architectural reference

- libcamera pipeline handler writer guide: <https://libcamera.org/guides/pipeline-handler.html>
- libcamera user documentation: <https://libcamera.org/getting-started.html>

A libcamera installation does not create a missing pipeline handler. If a custom Exynos 9820 FIMC-IS2 handler is needed, first establish the raw driver and buffer state machine, then implement and validate the handler against the correct libcamera API version.

## 23. Research conclusions and uncertainty

What is strongly supported by the supplied repository and sources:

- The target is a real Exynos 9820 S10+ with FIMC-IS2 already enabled in the recorded running config and five sensor modules recorded as bound.
- The V4L2 test used single-planar type 1 even though the nodes were recorded as multi-planar capture endpoints. Its `ENOTTY` result does not settle the standard API question.
- `V4L2_CAP_EXT_PIX_FORMAT` is a standard V4L2 capability bit, not proof of Samsung-private ioctls.
- The current config disables media-controller support; absence of `/dev/media*` is therefore not enough to conclude that the driver source lacks media-entity support.
- The repository already has the relevant firmware manifest and a pinned source fetcher. Public `beyond2lte` vendor metadata lists the camera firmware and camera HAL pieces.
- The Nuxel Camera/Photos UI and file-backed storage are already substantially implemented; the major missing element is a proven physical capture source.

What remains to be proven on the live device and exact kernel source:

- Whether the correct `VIDEO_CAPTURE_MPLANE` path is implemented and functional on the actual rear-main capture node.
- Whether the full sensor-to-ISP pipeline needs media-controller routing, Samsung private controls/ioctls, or a mix.
- Exactly which camera firmware files are requested and in what order; whether the current manifest destinations match the request path.
- Whether all setfiles are required for rear-main startup or only for later lenses/features.
- Whether the current live rootfs still lacks camera blobs; old inventory says they were missing, but re-check current state.
- Whether a small camera-specific kernel config change is sufficient or a driver patch is required.
- Whether a native V4L2/libcamera/PipeWire source is practical, or whether the matching Android vendor provider is needed.

Do not claim certainty on these unknowns. Resolve them in the sequence above, keep each hypothesis falsifiable, and continue to the next viable path when one is disproven.

---

# PART VIII — EXECUTION REPORT

## 24. Final report format

At the end of the mission, report:

1. **What was wrong with the previous diagnosis.** Include the corrected mplane test outcome and explain whether old ENOTTY/EINVAL results were invalid for the selected nodes.
2. **What hardware path works.** Name the actual sensor module, driver, node(s), API, firmware files and capture mode.
3. **What changed.** List code, kernel profile/patch, firmware manifest, services, permissions and UI changes.
4. **What was deployed.** Distinguish source build, rootfs installation, kernel deployment and live capture.
5. **Physical proof.** Confirm real preview, still, video, Photos playback, permission revoke and owner validation.
6. **System regressions.** Report display/Mali, Wi-Fi SSH, USB console, audio, MFC, Bluetooth, NFC, suspend/resume and reboot tests.
7. **Remaining lenses/features.** Report main, tele, ultrawide, front main, depth/IR and controls separately.
8. **Rollback.** Give exact tested rollback procedure and backups.
9. **Evidence paths.** Link to the new docs/evidence under `docs/pwnage-83000/`.
10. **Final status.** Use only evidence-backed status values from Section 18.

No green checkmark without the physical test. If a path is blocked, identify the exact kernel function, UAPI command, firmware request, allocation step, sensor initialization stage or security dependency that blocks it, then advance to the next viable method. The mission is to get the S10+ camera working in Nuxel.
