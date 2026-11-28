# NUXEL S10+ — OPERATION CAMERA RESURRECTION
## DeepSeek-V4-Pro-Thinking — Autonomous Kernel, Driver, Firmware and Application Engineering Mission

### YOUR MISSION

You are now acting as the principal Linux kernel, embedded camera, V4L2, libcamera, PipeWire and systems integration engineer for **NUXEL**, our custom native Linux operating system running on a Samsung Galaxy S10+ SM-G975F (`beyond2lte`), Exynos9820.

**Your objective is to make the physical cameras fully operational under Nuxel, from the kernel all the way through our own Camera application, native GTK applications and Flatpak applications.**

You have permission to research, retrieve, adapt, patch, port, replace, rewrite and implement all necessary camera-related software components.

This explicitly includes:

- Fetching public upstream source repositories and compatible driver implementations.
- Porting an existing camera driver from the related Galaxy S10.
- Writing new kernel drivers or adapting existing Exynos9820 drivers.
- Modifying V4L2, Media Controller, DMA-BUF, ION, sensor and ISP integration.
- Implementing or replacing the Samsung FIMC-IS2 userspace control layer.
- Creating custom libcamera pipeline handlers and IPA integrations where needed.
- Developing native PipeWire camera stream producers.
- Fixing XDG Camera portal and Flatpak camera integration.
- Modifying and upgrading our Nuxel Camera application.
- Building and deploying changes to the physical device.
- Rebuilding and flashing a verified kernel image if userspace solutions cannot resolve the problem.
- Downloading necessary publicly available source files and legally usable firmware references, with provenance and integrity checks.

**You are not restricted to the existing architecture.** If the Samsung FIMC-IS2 vendor driver fundamentally prevents reliable native Linux camera operation, replace the relevant camera subsystem with a better implementation.

Do not replace working operating-system components unnecessarily.

Our architectural requirement remains:

**ZERO ANDROID USERSPACE DEPENDENCIES.**

Linux kernel drivers, native libcamera, standard V4L2, PipeWire, GStreamer, Mesa, GTK and systemd are welcome.

Android userspace camera services, Camera2 runtime libraries, Binder-based camera HAL services and Android framework dependencies are not acceptable final runtime solutions.

Android kernel source and vendor camera implementations may be studied for hardware behavior, initialization order and compatibility.

---

# PHASE 0 — READ THE EXISTING EVIDENCE

You have already completed significant investigation. Do not start over from scratch.

Read:

1. `./pwn/ULTIMATE_CAMERA_AGENT_PROMPT.md`
2. `./pwn/COMPONENT_STATE_AND_CAMERA_AUDIT.md`
3. `./pwn/VERIFIED_PUBLIC_REFERENCES.md`
4. `cam-report.md` — locate the latest report and use it as the authoritative starting point for this continuation.

Also inspect:

- `./tools/s10plus/fimc-capture/`
- `./tools/s10plus/v4l2-uapi/`
- `./kernel/s10plus/`
- `./firmware/s10plus/`
- `./services/`
- `./scripts/`
- The existing Nuxel Camera and gallery application source.
- The existing camera broker, portal and PipeWire integration.
- Relevant packaging, deployment and systemd configuration.

Determine the actual checkout, active branch and uncommitted changes. Preserve existing work.

## Hardware and running kernel

Device: Samsung Galaxy S10+ SM-G975F, Exynos9820.

Recorded kernel:

`4.14.253-gf7194c1d15ed-dirty`

Recorded exact kernel source:

`/root/kbuild/src`

Recorded kernel Git HEAD:

`f7194c1d15eded1c2a1a4dc63825b26103435cc0`

Recorded host repository:

`/Users/wicked/x/nuxel`

Live device:

`root@10.11.12.99`

Use the previously configured SSH key and SSH access. The phone also has USB recovery connectivity.

Verify the current state rather than assuming none of these values have changed.

---

# PHASE 1 — PRESERVE WHAT WE HAVE ALREADY FIXED

THE CAMERA FIRMWARE PROBLEM IS RESOLVED.

The previous `-EIO` failure occurred because the Samsung vendor driver directly called `filp_open()` against:

`/system/vendor/firmware/`

The owner-stock `G975FXXS9DTK9` camera firmware has already been deployed there.

This includes:

- `fimc_is_lib.bin`
- `fimc_is_rta.bin`
- `fimc_is_fw_mcu.bin`
- `setfile_2l4.bin`
- `setfile_3m3.bin`
- `setfile_3p9.bin`
- `setfile_3j1.bin`
- `setfile_4ha.bin`

All eight were previously verified against their owner-stock hash manifest.

Successful recorded initialization includes:

```text
fimc_is_sec_run_fw_sel rom id[0] 1
fimc_is_sec_fw_find rta name is fimc_is_rta.bin
sensor_cis_check_rev : Sensor version. Rev. 0xA102
sensor_2l4_cis_select_setfile 3 stack sensor revision
fimc_is_ois_init_mcu gyro init data applied
[sensor_ak737x_actuator_init] product_id=0xE
[MOD:SAK2L4] sensor_module_init(0)
```

The 2L4 sensor binds successfully.

**Do not revert this progress. Do not repeat the earlier firmware-path investigation unless a regression is demonstrated.**

Also preserve the successful DMA buffer work.

The previously implemented `nuxel-ion-capture.c` allocates ION DMA-BUFs from `camera_heap` (recorded heap ID 5), then queues them on:

`/dev/video131` — `exynos-fimc-is-i0c`

Four `VIDIOC_QBUF` operations have succeeded.

These are real milestones, but they are not yet physical frame capture.

---

# PHASE 2 — THE ACTUAL REMAINING PROBLEM

The Samsung FIMC-IS2 vendor camera driver implements a proprietary leader/follower capture pipeline.

The previously observed problems include:

### Problem A — Nonstandard video format behavior

`fimc_is_ixc_video_get_format_mplane()` returns success without populating the V4L2 format structure.

Do not mistake this for successful format negotiation.

### Problem B — Proprietary camera state machine

The vendor driver requires private controls and ordering constraints such as:

`S_INPUT`, `S_BUFS`, `S_FORMAT`, leader initialization, group start and ISP start.

Ordinary V4L2 camera initialization does not establish the required state.

### Problem C — Sensor node rejects normal S_FMT

The sensor leader:

`/dev/video101` — `ss0`

was observed rejecting `VIDIOC_S_FMT`.

Investigate how the sensor's format and crop are actually established.

Do not keep brute-forcing arbitrary formats against an interface that was not designed to accept them.

### Problem D — ISP capture cannot stream without the group leader

The capture node reports:

```text
fimc_is_queue_start_streaming: [I0C] start_streaming is fail(-22)
fimc_is_subdev_buffer_finish: frame(0) is not com state(1)
```

The previous analysis points to missing initialization of the 3AA/ISP leader and the subsequent `fimc_is_itf_process_start()` path.

**Our next engineering milestone is a real `DQBUF` containing actual sensor pixels.**

No application integration can substitute for this milestone.

---

# PHASE 3 — FETCH AND STUDY WORKING LINUX CAMERA IMPLEMENTATIONS

Research and clone the most relevant public source repositories into an isolated workspace, for example:

`./pwn/upstream-camera-research/`

Start with:

## Reference A — Native Samsung S10 Linux implementation

https://github.com/butztill/s10-linux

This is an experimental native Linux port for the Samsung Galaxy S10 SM-G973F (`beyond1lte`), also based on Exynos9820.

Its public hardware status documents successful still-image capture from four sensors, but does not qualify video, OIS or every camera feature.

**THIS IS YOUR FIRST HIGH-PRIORITY PORTING CANDIDATE.**

Inspect its actual contents, including:

- Camera-related kernel drivers.
- `s10-camera-v4l2`, if present in the current tree.
- Sensor drivers and sensor-specific register configuration.
- Device-tree camera descriptions.
- Exynos CSI receiver implementation.
- Clock and regulator management.
- Reset and power sequencing.
- DMA and buffer handling.
- V4L2 ioctl implementations.
- Media Controller topology.
- Camera userspace programs.
- libcamera modifications and pipeline handlers.
- Any Megapixels application configuration.
- External firmware, calibration and runtime table requirements.
- Build instructions and kernel version.
- Licensing and provenance documentation.

Find the exact code responsible for a successful physical camera frame.

Trace it from sensor initialization to completed capture buffer.

Do not settle for repository summaries or README claims.

## Reference B — Exact-model S10+ Linux port

https://github.com/gangg111/S10Plus_Linux

This targets the exact SM-G975F (`beyond2lte`).

The project reports working camera support in its Droidian configuration.

Investigate:

- Camera-related kernel patches and device trees.
- Exact S10+ sensor configuration.
- Camera power and clocks.
- ISP and CSI routing.
- Dependencies required for reported camera operation.
- Whether any parts can work in Nuxel without Android userspace.
- Whether the project exposes genuinely reusable native code.

DO NOT install the project's complete ROM, rootfs or bootloader over Nuxel.

DO NOT import Android-dependent camera services into the final Nuxel runtime.

Extract useful architecture and hardware knowledge only.

## Reference C — Upstream Linux camera stack

https://gitlab.freedesktop.org/camera/libcamera

https://docs.libcamera.org/master/

Inspect the relevant libcamera architecture, V4L2 subdevice expectations, pipeline handlers and buffer interfaces.

Also research upstream Linux media drivers for compatible Exynos generations, carefully distinguishing older FIMC hardware from Exynos9820 FIMC-IS2.

Do not assume that matching names imply matching register interfaces.

## Source retrieval rules

For every relevant external repository:

1. Record its URL, commit SHA, branch, license and actual relevant files.
2. Determine the supported phone model and kernel version.
3. Determine whether reported hardware behavior was physically tested.
4. Identify dependencies, especially proprietary runtime components.
5. Classify each potentially reusable component as directly compatible, adaptable, reference-only or unsuitable.
6. Keep third-party provenance and license notices intact.
7. Never commit third-party proprietary firmware, calibration dumps, device secrets or private data to our public source tree.

Do not download random prebuilt kernels or firmware and flash them.

Use retrieved source to implement a Nuxel-specific solution.

---

# PHASE 4 — MAKE THE ENGINEERING DECISION

Investigate two implementation strategies.

## STRATEGY A — COMPLETE THE EXISTING FIMC-IS2 PIPELINE

This is potentially the fastest solution because:

- Firmware loading now works.
- The real sensor initializes.
- The Samsung DDK and RTA appear to load.
- ION buffers can be allocated.
- Capture buffers can be queued.
- The vendor driver already contains hardware-specific camera implementation.

Inspect the actual kernel source and reconstruct the complete initialization and streaming sequence.

Focus on:

- Sensor state initialization.
- Correct V4L2 node roles and capabilities.
- 3AA leader initialization.
- ISP/ISCHAIN configuration.
- Necessary private controls.
- Valid sensor input and setfile selection.
- Clock and firmware readiness.
- Group-start prerequisites.
- Actual leader node stream-on behavior.
- Completed frame callbacks.
- Buffer ownership and DMA synchronization.
- Error paths and clean stream teardown.

Use source-backed, deterministic logic.

Do not generate hundreds of arbitrary ioctl combinations.

Construct a native Linux camera capture backend that provides the required controls and streams real sensor data.

You may implement a userspace capture service that communicates with Samsung's private driver, provided it does not depend on Android runtime services.

If this route produces verified stable physical frames, continue with it.

## STRATEGY B — PORT OR WRITE A REPLACEMENT NATIVE CAMERA DRIVER

If the existing FIMC-IS2 interface proves impractical, or if the native S10 implementation offers a demonstrably superior path, develop a Nuxel-specific kernel camera driver.

**You are explicitly authorized to replace the current camera subsystem.**

Do not assume that the entire Samsung kernel must be replaced.

Prefer a narrowly scoped camera driver backport or port compatible with our existing 4.14 kernel when feasible.

The implementation must properly account for:

- Exynos9820 camera controllers and hardware registers.
- MIPI CSI-2 PHY and receiver initialization.
- Actual sensor I²C configuration.
- Regulators, clocks, GPIO and reset sequencing.
- Device-tree binding and driver probe order.
- Sensor selection and lane configuration.
- Media Controller and V4L2 subdevice topology.
- Frame size, crop, pixel format and frame-rate configuration.
- DMA allocation and cache synchronization.
- Interrupts and completed-buffer delivery.
- Compatible image processing paths.
- Lens actuator, autofocus and OIS where supported.
- Sensor calibration and legitimate external tuning data.
- Runtime power management.
- Proper camera resource cleanup.

**Important:** Determine whether the upstream native solution produces raw Bayer frames, ISP-processed images or both.

Do not assume that a CSI-only driver automatically provides autofocus, color processing, image correction or video-ready frames.

If required, implement a libcamera pipeline handler and appropriate image processing.

Use the exact S10+ sensor modules and device-tree topology, not blindly copied S10 configurations.

Handle coexistence carefully. The new driver and old FIMC-IS2 driver must not simultaneously bind or control the same sensors, registers, clocks or hardware blocks.

Preserve the existing driver as a rollback option.

## Decision requirement

Choose the architecture based on actual source analysis, portability, observed failures, maintainability and risk.

Do not choose a new kernel driver simply because it sounds cleaner.

Do not continue forcing the old driver if objective testing proves its interface fundamentally unsuitable.

Write a short decision record containing:

- Chosen architecture.
- Evidence supporting the choice.
- Alternatives considered.
- Reusable components.
- Required changes.
- Rollback plan.

Then IMPLEMENT the chosen solution immediately.

This decision record is not the final deliverable.

---

# PHASE 5 — IMPLEMENT AND VERIFY FIRST PHYSICAL FRAME

Start with the rear-main SAK2L4 camera.

The initial capture target should be a stable low-resolution mode supported by the sensor and actual pipeline.

Prove the entire path:

```text
Physical camera sensor
        ↓
Sensor initialization / I²C
        ↓
MIPI CSI-2 receiver
        ↓
ISP or raw capture pipeline
        ↓
DMA-BUF / V4L2 buffers
        ↓
Successfully completed DQBUF
        ↓
Real image pixels
        ↓
Saved physical capture file
```

Your capture tool must:

- Select the actual physical sensor.
- Initialize the relevant controller.
- Select a valid stream format.
- Allocate buffers correctly.
- Start the complete capture pipeline.
- Queue and dequeue completed frames.
- Read the actual captured bytes.
- Save a correctly described raw image or an encoded image.
- Release all buffers, file descriptors and camera resources.
- Report actual dimensions, pixel format, bytes used, timestamps and failures.

Do not confuse successful QBUF with successful DQBUF.

Verify at least two physically distinct scenes and confirm the resulting pixel content differs meaningfully.

Reject synthetic sources, cached images, filled test buffers and zero-byte captures.

Inspect:

- Frame timestamps.
- Pixel-content statistics.
- Buffer lengths.
- Image integrity.
- Frame-to-frame variation.
- Driver and kernel logs.
- Recovery after stream stop.
- Repeated camera initialization.

Once this passes, mark:

`FIRST_FRAME_VERIFIED = PASS`

Not before.

---

# PHASE 6 — EXPAND TO FRONT AND REAR CAMERA HARDWARE

After the rear-main camera works, extend support to the actual camera modules installed on the S10+.

Previously identified firmware and sensor groups include:

- Rear main: 2L4.
- Rear telephoto: 3M3.
- Rear ultrawide: 3P9.
- Front main: 3J1.
- Auxiliary/front depth: 4HA.

Verify each device's identity and capabilities on the physical phone.

For the main rear and front cameras, implement working preview, still capture and video capture.

For additional sensors, implement all technically supported capabilities and explicitly document hardware limitations.

Do not assume that an auxiliary depth sensor can be exposed as an ordinary RGB camera.

Also investigate and implement, where supported:

- Autofocus.
- Exposure.
- White balance.
- Resolution selection.
- Frame-rate selection.
- Rear lens selection.
- Zoom and supported camera switching.
- Rotation/orientation metadata.
- Correct front-camera mirroring behavior.
- OIS.
- Flash strobe.
- Continuous flashlight/video torch.

Investigate the real LED flash hardware and driver interface.

Do not control the LED using invented sysfs paths or unsupported power/current values.

The torch must turn off safely after recording stops, an application exits or an error occurs.

Avoid keeping multiple sensors powered unnecessarily.

---

# PHASE 7 — PROVIDE A STANDARD NATIVE LINUX CAMERA STACK

When physical frame capture works, integrate it properly into Nuxel.

The preferred application-facing architecture is:

```text
S10+ physical camera hardware
                ↓
Nuxel native camera kernel driver
                ↓
V4L2 / Media Controller / DMA-BUF
                ↓
libcamera or compatible native capture backend
                ↓
PipeWire camera stream provider
                ↓
Camera portal and permissions
                ↓
Nuxel GTK / WebKitGTK PWA / Flatpak applications
```

You may adjust this architecture if your chosen working driver requires a different arrangement.

The result must provide real camera frames through standard, supported Linux interfaces.

Use libcamera where its device model fits.

Use a custom libcamera pipeline handler where necessary.

Use GStreamer integration when practical.

Keep DMA-BUF and zero-copy options where supported, but do not sacrifice correctness or stability merely to obtain zero-copy rendering.

Investigate software image processing for raw Bayer capture if the native driver does not provide suitable ISP-processed frames.

Implement appropriate color correction, demosaicing, exposure and white-balance controls.

Do not expose incorrectly decoded Bayer data as a successful color camera.

### Fix existing camera portal problems

Review the Nuxel camera broker and portal.

In particular:

- Camera presence must reflect a usable physical source.
- PipeWire remote handoff must use the correct connection and file-descriptor mechanism.
- Access permissions must be enforced.
- Revoked permissions must stop unauthorized access.
- Front and rear camera identities must be stable.
- Device ownership must be handled correctly.
- Multiple applications must not corrupt or wedge the hardware.
- Camera resources must be released on app exit and crash.

Replace any incorrect assumptions that the Samsung private camera node can be opened as a normal generic `v4l2src` webcam.

Avoid exposing raw hardware devices unnecessarily to sandboxed applications.

Ensure application-facing APIs identify available cameras honestly.

---

# PHASE 8 — FULL NUXEL CAMERA APPLICATION

Upgrade our existing Nuxel Camera application into a functional mobile camera application.

Do not build a second disconnected camera application if we already have a maintained application to extend.

Required functionality:

## Photo mode

- Live rear camera preview.
- Live front camera preview.
- Rear/front switching.
- Capture button.
- Save photographs to the gallery.
- Correct photo orientation.
- Flash control where available.
- Resolution selection using supported modes.
- Autofocus and exposure behavior where supported.
- Proper capture error reporting.

## Video mode

- Live preview.
- Start/stop recording.
- Recording duration indicator.
- Microphone audio capture.
- Video/audio synchronization.
- Save the completed video to the gallery.
- Play recorded video.
- Switch to supported camera devices between recordings.
- Continuous video torch where hardware-supported.
- Recovery from interrupted recording.
- Valid finalization of the media container.

Start with an achievable, stable recording mode.

Prefer H.264 encoding when supported by the actual system.

Evaluate Exynos MFC hardware encoding, but do not make a nonworking MFC driver an unnecessary blocker for basic camera recording.

A tested software encoder is acceptable as an interim solution if CPU load, thermal behavior and recording quality are reasonable.

## Gallery integration

Use the existing Nuxel gallery infrastructure.

Require real files to appear in the normal gallery, with valid metadata and thumbnails.

Both photos and videos must open correctly.

Videos must play with captured microphone audio.

Do not declare success because a media file exists; decode it and verify its actual content.

## User experience

The application should feel like a proper mobile camera app:

- Responsive controls.
- Correct aspect ratio.
- No stretched image.
- Correct orientation.
- Predictable photo/video modes.
- Useful error messages.
- Flash and torch availability accurately represented.
- No frozen preview after switching.
- No stale camera locks after closing.

Keep the existing Nuxel design language.

---

# PHASE 9 — VERIFY THREE DIFFERENT CAMERA APPLICATIONS

Our Nuxel Camera application is only one acceptance target.

We also need an independently packaged native GTK application and a Flatpak application to prove that the shared Linux camera stack actually works.

## Application A — Nuxel Camera

Our own native application must capture and save:

- Rear photo.
- Front photo.
- Rear video with microphone sound.
- Front video with microphone sound.

Verify media playback and gallery integration.

## Application B — Native GTK application from Fedora

Find a maintained, compatible GTK camera application available from the official Fedora repositories.

Inspect the actual repository metadata and supported camera backend before selecting it.

Install it using Fedora's normal package management.

Make only the minimum necessary integration changes.

Verify physical front and rear camera capture where the application's capabilities permit.

If an application does not support a feature, document that application limitation separately from the underlying hardware.

Do not fabricate package names or claim official Fedora availability without checking.

## Application C — Independent Flatpak camera application

Choose a maintained camera-capable application from a trusted Flatpak remote.

Install it normally.

Verify:

- Camera enumeration.
- Correct permissions.
- PipeWire/portal access.
- Physical camera preview.
- Still or video capture as supported.
- Correct cleanup.
- Repeated successful launches.

Do not solve a sandbox problem by permanently granting unnecessary unrestricted hardware access.

If the application depends on features missing from our camera portal, fix the portal properly.

### Shared-stack requirement

The three applications must use the same underlying camera implementation wherever technically practical.

We must not end up with three unrelated hacks.

The goal is a genuinely reusable native Linux camera subsystem.

---

# PHASE 10 — LIVE DEPLOYMENT AND RECOVERY

Inspect `./scripts/` and use our existing Nuxel deployment mechanisms.

Prefer deployment of userspace packages, binaries, libraries, configuration and services without entering recovery.

Only rebuild or flash the kernel when the chosen technical solution requires it.

The user has previously authorized necessary TWRP-based camera recovery and boot-image work.

However, before any boot-critical modification:

1. Identify the exact target partition and current boot configuration.
2. Verify the target device model.
3. Preserve the last known-good boot image and relevant configuration.
4. Verify build output and source provenance.
5. Check that the replacement image matches the expected device and partition format.
6. Keep a tested recovery path available through USB/TWRP.
7. Do not alter EFS, IMEI, modem calibration, protected keys or unrelated partitions.
8. Avoid data-destructive operations.
9. Record precisely which image was installed and its hash.
10. Verify boot recovery and basic operating-system function afterward.

Do not interpret an unexpected TWRP boot as definitive proof of a failed flash.

Diagnose boot selection, active recovery configuration, filesystem mounting, kernel logs and actual boot behavior.

Do not repeatedly flash identical failed images.

Each retry must be based on a new diagnosis or an identifiable correction.

Preserve working Wi-Fi, SSH, touchscreen, display, microphone, audio and graphics functionality.

The camera repair must not destroy the rest of Nuxel.

If a new operation creates an irreversible risk outside the previously authorized camera/boot recovery scope, obtain explicit approval first.

---

# PHASE 11 — COMPLETE PHYSICAL ACCEPTANCE MATRIX

Run tests on the actual device, not only through emulation or offline builds.

Maintain this matrix:

| Test | Required result |
|---|---|
| Rear sensor initialization | PASS |
| Rear physical frame capture | PASS |
| Front physical frame capture | PASS |
| Rear live preview | PASS |
| Front live preview | PASS |
| Rear JPEG/photo saved | PASS |
| Front JPEG/photo saved | PASS |
| Rear video recording | PASS |
| Front video recording | PASS |
| Recorded microphone audio | PASS |
| Audio/video synchronization | PASS |
| Gallery photo playback/viewing | PASS |
| Gallery video playback | PASS |
| Photo flash where supported | PASS |
| Video torch where supported | PASS |
| Native Nuxel Camera | PASS |
| Native Fedora GTK camera | PASS for supported functions |
| Flatpak camera access | PASS |
| Camera permissions | PASS |
| Repeated camera switching | PASS |
| Camera cleanup on exit | PASS |
| Kernel stability after capture | PASS |

For each test, record:

- Hardware sensor.
- Application.
- Actual operation.
- Result.
- Relevant logs.
- Output media file.
- Evidence of physical capture.
- Any limitation.

Record short test videos with genuine microphone audio.

Verify video container integrity, video frames, audio streams, duration and synchronization.

Play the resulting files on the device.

View still images on the device.

Repeat important tests after reboot.

Do not treat an application launch or a visible preview widget as proof of physical capture.

Do not use a test pattern as evidence that the camera hardware works.

Distinguish physical hardware limitations from unfinished software support.

---

# PHASE 12 — STABILITY, QUALITY AND REGRESSION TESTING

Once all basic capture gates pass, investigate:

- Repeated start/stop cycles.
- Front/rear switching.
- Camera application restarts.
- Recovery after failed captures.
- Long-running previews.
- Sustained video recording.
- CPU and memory behavior.
- Resource leaks.
- Thermal behavior.
- Suspend/resume interaction.
- Camera access conflicts.
- DMA buffer lifetime.
- Race conditions in stream teardown.
- Kernel warnings, timeouts and panics.
- Orientation and screen rotation.
- Correct focus and exposure behavior.
- Image and video color accuracy.
- Torch cleanup after errors.

Measure actual behavior.

Do not claim 30 FPS or 1080p support unless those modes are demonstrated by captured output and performance measurements.

Use modest, reliable modes first and improve performance afterward.

Avoid destabilizing unrelated features.

---

# PHASE 13 — ENGINEERING WORKFLOW

You are expected to execute code changes, not merely generate ideas or a design proposal.

Work iteratively:

```text
Inspect existing evidence
        ↓
Retrieve relevant source
        ↓
Trace actual failing code
        ↓
Select and implement a repair
        ↓
Build and run offline tests
        ↓
Deploy safely
        ↓
Run a bounded physical test
        ↓
Inspect results and logs
        ↓
Fix the next demonstrated problem
        ↓
Repeat until acceptance gates pass
```

Use small, logically isolated commits.

Keep the build reproducible.

Record upstream source revisions and patches.

Do not overwrite unrelated uncommitted work.

Do not conceal test failures.

Do not silently downgrade camera functionality to make an easier test pass.

Whenever an approach fails, use the evidence to change the implementation instead of merely repeating the same attempt.

If the existing vendor camera stack becomes a dead end, move to the custom-driver architecture.

If the first custom-driver port is incomplete, inspect and adapt its missing kernel, sensor, DMA or userspace components.

If a new libcamera pipeline handler is required, implement it.

If an application expects an unsupported interface, implement the appropriate compatibility layer rather than pretending the device works.

Use host-side cross-compilation and static tests aggressively to minimize unnecessary live-device experiments.

---

# PHASE 14 — REQUIRED REPOSITORY DELIVERABLES

Add or update the appropriate Nuxel source files and produce the following engineering documentation:

`./pwn/CAMERA_DRIVER_ARCHITECTURE.md`

Document the working driver, source provenance, firmware dependencies, hardware path, kernel interfaces and architecture decisions.

`./pwn/CAMERA_IMPLEMENTATION_LOG.md`

Record major tests, changes, failures, corrections and verified milestones.

`./pwn/CAMERA_LIVE_ACCEPTANCE.md`

Provide the complete physical-device acceptance results.

`./pwn/CAMERA_REPRODUCIBLE_BUILD.md`

Document how to reproduce the exact working camera build from the repository and properly sourced external dependencies.

`./pwn/CAMERA_RECOVERY_AND_ROLLBACK.md`

Document known-good images, deployment method, recovery process and rollback.

Also update the relevant build configuration, install manifests, Nuxel Camera packaging, service definitions, existing README files and changelog where appropriate.

Keep proprietary firmware and private device data out of public commits.

---

# NON-NEGOTIABLE REQUIREMENTS

1. Do not stop at camera enumeration.
2. Do not stop at successful firmware loading.
3. Do not stop at successful DMA buffer allocation.
4. Do not stop at successful QBUF.
5. Do not stop at a synthetic frame.
6. Do not stop at a libcamera device being listed.
7. Do not stop at a PipeWire node being created.
8. Do not stop at a camera application opening.
9. Do not declare complete while physical photos or videos remain unverified.
10. Do not introduce Android userspace dependencies as the final solution.

**You are explicitly allowed to implement an entirely new native camera driver if that is the most technically sound way forward.**

Aim for a proper Linux camera implementation that can be maintained, rebuilt, redeployed and extended.

Keep progressing through verified implementation milestones rather than producing another speculative research report.

When a test fails, investigate and fix the concrete failure.

When a design becomes unsuitable, replace it with a better supported design.

Continue the engineering task until the physical acceptance matrix passes, or until a genuinely external blocker prevents further safe progress. In that case, complete all other feasible work and report the precise blocker, evidence, attempted solutions and the exact required next action. Never invent progress or hide unfinished requirements.

---

# START EXECUTING NOW

First, read `cam-report.md` and inspect the source already added during the successful firmware and ION investigations.

Then immediately clone and inspect the actual camera implementation in:

https://github.com/butztill/s10-linux

Compare its working capture path with our running Exynos9820 kernel.

Determine whether we can port its native implementation directly, need a compatibility backport, or can use its findings to complete our current FIMC-IS2 pipeline.

**Do not spend another full round rediscovering the already-solved firmware problem.**

Your first implementation deliverable is:

**A verified physical image frame from the rear-main SAK2L4 camera on the live Nuxel phone.**

Your final implementation deliverable is:

**A working native Nuxel camera stack with tested front and rear photos, video with microphone audio, supported flash/torch controls, working gallery integration, and camera operation through Nuxel Camera, a native Fedora GTK application and a Flatpak application.**

BEGIN THE IMPLEMENTATION.
