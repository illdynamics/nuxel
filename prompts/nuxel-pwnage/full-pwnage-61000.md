# FULL-PWNAGE-61000 — Bring up safe, real Exynos 9820 MFC hardware video decoding on Nuxel

**Mission ID:** PWNAGE-61000  
**Project:** Nuxel — Mobile Linux for Control Freaks  
**Primary device:** Samsung Galaxy S10+ SM-G975F (`beyond2lte`)  
**SoC:** Samsung Exynos 9820  
**OS target:** Nuxel Fedora 43 aarch64  
**Known kernel build source:** `Linux4/android_kernel_samsung_exynos9820` at pinned commit `f7194c1d15eded1c2a1a4dc63825b26103435cc0` (Linux 4.14.253 downstream; verify every item against the active checkout and handset)  
**Mission type:** implementation, kernel/userspace integration, physical validation, safe enablement, performance measurement and deployable deliverables — not research-only  
**Scope:** Exynos MFC hardware video decode. Encoder, camera capture, HDMI, Miracast and unrelated GPU work are explicitly out of scope unless a dependency must be inspected to prevent regression.

---

## 0. Mission order — continue the GPU work, do not restart it

The previous GPU mission (PWNAGE-60000) established that Nuxel already has a partially working Mali-G76 graphics path. This mission is the next, separate subsystem: bring up the S10+'s **Multi-Format Codec (MFC) hardware decoder** safely and make it usable by a real media playback pipeline.

Do not treat “GPU acceleration” and “hardware video decoding” as synonyms:

- Mali-G76 is the graphics GPU used for GLES/compositing.
- MFC is a separate fixed-function video codec engine with its own kernel driver, firmware, queues, memory handling, clocks, power state and userspace ABI.
- A video can be hardware-decoded by MFC and then copied through CPU memory for display. That is still hardware decoding, but it is not a zero-copy display pipeline.
- A video can be GPU-composited while software-decoded by CPU. That is not hardware video decoding.
- A GStreamer element existing, a V4L2 node existing, an MP4 playing, or a codec name appearing in a list is not proof that MFC processed a frame.

The mission is successful only when a known test stream is demonstrably decoded by the physical MFC on the S10+, the result is displayed correctly, CPU use is measured against a matched software baseline, and the existing Nuxel desktop remains stable when firmware is missing, malformed, unsupported or the decoder is unused.

**Do not remove the existing MFC/V4L2 safety guard as an early step.** Its history is a critical safety requirement, not stale clutter.

### Non-negotiable priorities

1. Keep the handset bootable and usable at every stage.
2. Identify the exact MFC hardware IP, kernel driver implementation and firmware ABI before changing anything.
3. Make missing/invalid firmware and hardware faults fail promptly and cleanly; never leave the desktop/UI in a blocked state.
4. Prove the kernel driver and V4L2 M2M contract before enabling any general plugin scanner.
5. Demonstrate at least one actual decoded frame from MFC before integrating a media player.
6. Keep software decoding as a reliable fallback.
7. Only claim codec/resolution capabilities that are discovered from the actual device and measured.
8. Do not flash or reboot the physical handset without explicit owner approval in the active task. Build and stage artifacts first.
9. Do not fabricate successful hardware tests when the S10+ is unavailable. Mark them `NOT_RUN` or `BLOCKED_DEVICE` with exact reason.
10. Implement and test. Do not return a plan-only report.

---

## 1. Current repository ground truth — revalidate before edits

The supplied repository archive contains important existing safeguards and candidates. Read the actual current branch first: these details are the baseline to confirm, not an instruction to trust stale files blindly.

### 1.1 Kernel build baseline

`kernel/s10plus/build-kernel.sh` pins:

```text
DOWNSTREAM_REPO   https://github.com/Linux4/android_kernel_samsung_exynos9820
DOWNSTREAM_COMMIT f7194c1d15eded1c2a1a4dc63825b26103435cc0
DEFCONFIG         exynos9820-beyond2lte_defconfig
Kernel family     Linux 4.14.253 downstream
```

The kernel source is fetched into `kernel/s10plus/.build/src`; it is not vendored as a complete source tree in the Nuxel repository archive. Use the wrapper and pinned commit as the source of truth unless the active branch has intentionally changed the pin. Never silently build against the latest branch tip.

The existing wrapper applies patches in order and may treat patches as optional unless a `.required` sidecar exists. If this mission adds a required MFC patch, mark it required and make patch application/build failures visible. Do not make a dangerous MFC patch “optional” merely to preserve a green build.

### 1.2 Existing GStreamer safety guard

`tools/s10plus/a29/nuxel-gstreamer-guard.sh` currently renames these plugins when present:

```text
libgstvideo4linux2.so
libgstv4l2codecs.so
libgstkms.so
libgstopengl.so
```

The source comment records that vendor MFC `/dev/video*` opens previously blocked inside `request_firmware()` / `mfc_open`; GStreamer's plugin scanner and a WebKit media process were observed entering uninterruptible `D` state. The script also removes stale user/root GStreamer registry files.

The guard is invoked from both session paths:

- `tools/s10plus/a29/nuxel-session.sh`
- `tools/s10plus/a45/nuxel-session.sh`

It is installed in the runtime as `/usr/lib/nuxel/nuxel-gstreamer-guard.sh`.

**Do not delete, bypass or globally disable this guard at the beginning of the mission.** Design a narrow, explicit, reversible exception only after the exact decoder node has passed the kernel safety gate. Do not restore KMS or OpenGL plugins as a side effect of enabling MFC.

### 1.3 WirePlumber V4L2 monitor is intentionally disabled

`configs/s10plus/wireplumber/99-nuxel-no-v4l2.conf` disables `hardware.video-capture` while preserving audio and Bluetooth. Its comments explain that the old MFC firmware path could hang device enumeration and WirePlumber startup.

This setting is about preventing a general video-capture monitor from scanning unsafe video nodes. **MFC decode does not require PipeWire/WirePlumber to enable camera capture.** Keep `hardware.video-capture = disabled` unless a separately proven need exists and all camera nodes are independently safe. Do not conflate camera capture with decoder operation.

### 1.4 Existing firmware candidate

`firmware/s10plus/manifest.yml` currently has this optional entry under `video`:

```yaml
- source_path: "vendor/firmware/mfc_fw.bin"
  dest: "/lib/firmware/mfc_fw.bin"
  description: "MFC video codec firmware"
  required: false
  checksum: "f3802d34524f5919c16505c03b4cbfe184963f98787feed6232b643bda68b55f"
```

That is a **candidate metadata record**, not proof that the current kernel requests this exact name, that the binary is present, that its version matches this kernel, or that it successfully loads. In the supplied ZIP, `firmware/s10plus/blobs/` contains only placeholder/README material; the actual MFC blob is not present.

`firmware/s10plus/fetch-vendor-blobs.sh` pins a vendor firmware source repository/commit. `firmware/s10plus/install-firmware.sh` supports checksum verification, a device-identity-checked TWRP pull, and controlled rootfs staging. Reuse and harden these mechanisms rather than creating an untracked firmware download shortcut.

### 1.5 Current userspace media chain is software-first

`images/s10plus/build-phone-rootfs-inside-fedora.sh` installs `mpv`. The existing PWNAGE-31000 implementation explicitly documents a lean FFmpeg-free playback chain, and its preloading invocation uses:

```text
--hwdec=no
```

That is intentional for the boot splash and must remain stable. Do not silently change the boot-time preload controller to depend on MFC. The supplied test clip is H.264 High, 1080x1920, 24 fps, yuv420p, but the fact that it decodes successfully today proves software decoding only.

The current build installs `pipewire`, `wireplumber`, `pipewire-utils`, `alsa-lib`, `mpg123` and `mpv`; do not assume the needed GStreamer V4L2 plugins, FFmpeg M2M backend or codec libraries are currently installed. Inspect the actual RPM transaction and binary feature set.

### 1.6 No proven MFC driver enablement yet

The supplied Nuxel kernel config fragments do not establish a working MFC decoder. Do not assume that enabling a familiar config symbol is enough. Inspect the exact pinned Linux4 source, its MFC implementation, Kconfig, Makefiles, device tree and built kernel config. A generic `s5p-mfc` driver from another SoC or a recent Exynos MFC driver for a different IP generation is not automatically compatible with Exynos 9820.

### 1.7 Previous camera diagnostics are not MFC decoder tests

`tools/s10plus/a52/nuxel-v4l2-probe.py` and `nuxel-v4l2-capture-test.py` were created around camera/V4L2 capture investigation. The probe may open enumerated `/dev/video*` nodes, and the capture test targets a camera node. Do not run these against suspect MFC nodes. Do not reinterpret `/dev/video111` FIMC-IS camera behavior as MFC decoder behavior.

Create a purpose-built MFC diagnostic with an allow-listed device identity and safe opt-in semantics. Keep camera scope blocked; do not claim camera recording as a side benefit.

---

## 2. Required startup inventory and safety snapshot

Before changing source, config, firmware or services:

```sh
git status --short --branch
git rev-parse HEAD
git log -8 --oneline --decorate
sha256sum kernel/s10plus/build-kernel.sh \
  firmware/s10plus/manifest.yml \
  firmware/s10plus/install-firmware.sh \
  firmware/s10plus/fetch-vendor-blobs.sh \
  tools/s10plus/a29/nuxel-gstreamer-guard.sh \
  configs/s10plus/wireplumber/99-nuxel-no-v4l2.conf
```

Record the exact live handset state when available:

```sh
uname -a
cat /proc/version
cat /proc/cmdline
cat /etc/os-release
id
ls -l /dev/video* /dev/media* 2>/dev/null || true
find /sys/class/video4linux -maxdepth 3 -type f -print 2>/dev/null | sort
find /sys/class/media -maxdepth 3 -type f -print 2>/dev/null | sort
find /sys/bus/platform/drivers -maxdepth 2 -type l -print 2>/dev/null | sort | grep -Ei 'mfc|video|media|codec' || true
dmesg -T | grep -iE 'mfc|firmware|v4l2|video codec|iommu|sysmmu|s5p|exynos' | tail -250
```

Also capture, when permitted and available:

- `/proc/config.gz` or the exact `/boot/config-*` for the running kernel;
- `/sys/firmware/devicetree/base` relevant MFC node paths and properties;
- `/sys/kernel/debug/clk/clk_summary` (read-only, if mounted and available);
- `/sys/kernel/debug/pm_genpd/` summaries (read-only, if mounted and available);
- installed MFC firmware names, sizes and SHA-256 values under `/lib/firmware`;
- installed RPM names/versions for GStreamer, FFmpeg, mpv and libav*;
- GStreamer plugin registry state without triggering unsafe device opens;
- `mpv --version`, `mpv --hwdec=help`, and supported FFmpeg feature output **only if these commands are known not to open media devices**.

### Read-only first principle

The inventory phase must not call `open()` on any suspected MFC `/dev/videoN` or `/dev/mediaN` node. Merely listing directory entries, reading sysfs attributes, inspecting device-tree data and reading logs is allowed. Device nodes are not safe to open just because they accept `O_NONBLOCK`; the driver may block in its `.open()` callback before userspace can make a later ioctl.

Produce `docs/beta-finalization/live/PWNAGE-61000-MFC-BASELINE.md` with:

- source commit and file hashes;
- live kernel version and config provenance;
- exact device identity and boot ID;
- discovered media/video node names and sysfs names (without opening them);
- candidate MFC driver binding and device-tree identity, if discoverable;
- firmware candidate presence/hash/version;
- GStreamer guard and WirePlumber state;
- media package inventory;
- known risks and facts still unknown.

Do not edit the baseline after implementation to make it appear that a former state was already proven.

---

## 3. Workstream A — inspect the exact Exynos 9820 MFC driver and ABI

This workstream is mandatory and must complete before hardware probing.

### A1. Fetch and inspect the pinned kernel source

Use the project's wrapper or clone the exact commit into the intended build cache. Verify:

```sh
git -C kernel/s10plus/.build/src rev-parse HEAD
# Must equal the repository's current DOWNSTREAM_COMMIT.
```

Search the exact source tree for:

```sh
rg -n -i 'mfc|multi.?format.?codec|s5p.?mfc|video.*codec|request_firmware|mfc_load_firmware|mfc_open' \
  kernel/s10plus/.build/src/drivers \
  kernel/s10plus/.build/src/arch/arm64/boot/dts \
  kernel/s10plus/.build/src/arch/arm64/configs
```

Inspect at minimum:

- MFC driver source files and all included headers;
- exact Kconfig symbols and dependency graph;
- Makefile object selection;
- device-tree bindings and Exynos9820/beyond2lte DTS/DTSI definitions;
- firmware request calls and exact requested firmware filename(s);
- firmware format/version checking and load sequence;
- `probe`, `remove`, `.open`, `.release`, `mmap`, `poll`, `ioctl`, runtime PM, suspend/resume and error paths;
- IRQ handler and completion/wait logic;
- clocks, regulators, reset, power-domain, interconnect and IOMMU/SysMMU setup;
- reserved-memory, CMA, DMA mask, coherent allocation and cache-maintenance assumptions;
- secure-world/TEE, mailbox or firmware-authentication dependencies if present;
- codec command ABI, hardware IP revision checks and firmware version compatibility.

Do not stop at a symbol named `S5P_MFC`. The source must demonstrate that this driver supports the exact MFC generation integrated into Exynos 9820. Record evidence from source, device tree and matching stock implementation. If version identity cannot be established, do not enable the driver.

### A2. Establish the actual device and version

Triangulate at least these sources:

1. Pinned Linux4 downstream kernel source.
2. The exact built DTB/DTS for `exynos9820-beyond2lte`.
3. The actual live device-tree node and compatible string on the handset.
4. Matching Samsung stock kernel/vendor source or exact stock binary/module metadata, if available from authorized sources.
5. Firmware metadata and the driver’s exact firmware request path.

Never infer MFC generation from the SoC name alone. Never use firmware from an unrelated Exynos model simply because the file is called `mfc_fw.bin` or `s5p-mfc-v*.fw`.

### A3. Decide driver strategy explicitly

Choose one of these, with evidence:

- **Reuse existing compatible driver:** it is already in the pinned source and needs correct config/DT/firmware setup.
- **Repair existing downstream implementation:** the driver is present but has a confirmed bug in firmware lookup, resource sequencing, error handling or queue API.
- **Port a matching upstream driver:** only if the actual hardware IP and ABI match, and all required resources/firmware interface are understood.
- **Build a minimal vendor-compatible implementation:** only when the matching source/ABI is available and port scope is realistic. Do not reverse-engineer blindly from a node name.
- **BLOCKED_UNSUPPORTED:** if no trustworthy matching implementation or required firmware exists. Keep guard active, provide a precise blocker and do not fake a decoder.

Do not cherry-pick a driver series for a later Exynos MFC IP version without proving its register interface, firmware protocol and device-tree ABI match the S10+.

### A4. Produce a driver/firmware compatibility matrix

Add a table to the report covering:

| Item | Required evidence | Result |
|---|---|---|
| MFC hardware IP revision | exact DT/source/stock evidence | PASS / UNKNOWN / FAIL |
| kernel driver implementation | source path and commit | PASS / UNKNOWN / FAIL |
| kernel config | symbols present in built config | PASS / UNKNOWN / FAIL |
| DT binding | compatible/resources match | PASS / UNKNOWN / FAIL |
| firmware filename | exact `request_firmware*()` string | PASS / UNKNOWN / FAIL |
| firmware version | driver acceptance check / vendor provenance | PASS / UNKNOWN / FAIL |
| firmware hash | SHA-256 of actual file | PASS / UNKNOWN / FAIL |
| DMA/IOMMU path | source + runtime evidence | PASS / UNKNOWN / FAIL |
| V4L2 API mode | stateful / stateless / vendor-specific | PASS / UNKNOWN / FAIL |

Any `UNKNOWN` in IP compatibility, firmware ABI, memory path or device tree is a stop sign for opening the live node.

---

## 4. Workstream B — retrieve and install the correct MFC firmware safely

### B1. Determine the exact firmware requirement first

The manifest currently names `vendor/firmware/mfc_fw.bin`, installs it to `/lib/firmware/mfc_fw.bin`, and records a SHA-256 candidate. Do not assume the kernel asks for that path. Read the exact driver source and capture its request string, directory rules, firmware header parsing and expected version.

If the driver requests a different filename, fix the source metadata and installer destination coherently. Do not create a symlink or duplicate file as a guess. Do not embed firmware in the kernel unless the current driver’s early boot ordering demonstrably requires it and the licensing/provenance is cleared.

### B2. Use approved source-of-record acquisition

Preferred sources, in order:

1. An authorized vendor firmware tree already pinned in `firmware/s10plus/fetch-vendor-blobs.sh`, after confirming the exact file and license/provenance.
2. A TWRP pull from the owner's own S10+ using the existing `install-firmware.sh --twrp-pull` identity checks, if the device is available and the owner has authorized it.
3. A separate legally redistributable firmware package, only if it is demonstrably byte-compatible with this exact MFC driver.

Do not read EFS, modem partitions, IMEI, calibration secrets, user data or unrelated protected partitions. The existing firmware pull's intended `/vendor/firmware`, module and selected system paths must remain scoped; do not widen it.

### B3. Verify actual binary provenance

For the actual MFC blob record:

- source repository and exact commit or source-device build fingerprint;
- relative source path and destination path;
- byte size;
- SHA-256;
- file magic/header and version fields, if the format exposes them;
- the kernel driver check that accepts/rejects this firmware;
- whether binary redistribution in the Nuxel repository/image is allowed;
- whether it is pulled at build time or acquired by the device owner.

The current manifest checksum is a candidate reference. Compare it with the real acquired file. If it differs, do not silently replace the checksum. Explain why the difference exists and require an explicit resolution. Never fabricate a firmware file, pad a placeholder, skip a checksum, or set an unknown blob to `required: true` merely to make the image builder pass.

### B4. Firmware packaging policy

Use the existing manifest and installer flow. Keep the MFC blob optional for generic/rootfs builds until a correct, legally sourced file is actually present. If a specific MFC-enabled S10+ release profile requires it, make that profile's build check fail clearly when absent or mismatched, but keep software-only fallback images buildable.

Test all of these cases:

1. Correct blob available and valid → staged at exact path.
2. Blob missing → no fake file; hardware decoder reports blocked; software playback remains available.
3. Blob hash mismatch → install fails closed; no copy into live rootfs.
4. Wrong firmware version → driver returns a prompt, diagnosable error; no endless wait.
5. Wrong device identity during pull → existing identity check refuses.
6. Permission/ownership error → clear failure before session launch.

Do not assume `request_firmware()` can always see a rootfs file at early probe. Inspect actual init/driver timing. If firmware is required before switch_root, use a verified initramfs inclusion path or a driver defer/probe policy; do not hack around it by blocking forever.

---

## 5. Workstream C — kernel config, device tree, driver safety and failure handling

### C1. Kernel config

Derive the required config symbols from the exact driver. Inspect the generated config after `olddefconfig` and after the final kernel build; the presence of a fragment is not proof that Kconfig accepted it.

Potential dependency families to inspect (not an assertion that all are required):

- media controller core (`CONFIG_MEDIA_SUPPORT`, `CONFIG_MEDIA_CONTROLLER`);
- V4L2 core (`CONFIG_VIDEO_DEV`);
- V4L2 memory-to-memory framework (`CONFIG_V4L2_MEM2MEM_DEV`);
- videobuf2 (`CONFIG_VIDEOBUF2_*` matching the driver's memory types);
- exact Samsung/Exynos MFC driver symbol from this pinned source;
- IOMMU/SysMMU and DMA support required by the DT and driver;
- firmware loader and required firmware class behavior;
- debug options only in development kernels, not accidentally shipped in production.

Avoid enabling unrelated camera ISP, FIMC, media capture or every V4L2 driver as a shortcut. Keep camera capture disabled and unchanged.

### C2. Device tree must match the exact phone

Inspect the actual beyond2lte device tree and the live `/sys/firmware/devicetree/base` node. Verify the MFC node's:

- `compatible` string;
- `reg` region(s);
- interrupt(s);
- clock names/IDs;
- power domain and reset;
- operating points/interconnect bandwidth if used;
- IOMMU/SysMMU attachments and stream IDs;
- memory-region/reserved-memory/CMA requirements;
- firmware-name property, if any;
- status and probe ordering.

Do not copy a DT node from another Exynos phone. Do not guess register offsets, interrupt numbers, IOMMU stream IDs or memory regions. Do not alter the active DTB selection or add an overlay unless the exact target DTB is proven and rollback exists.

### C3. Eliminate the old unbounded failure mode

The current problem is not just that MFC is missing; a failed open can freeze callers in kernel space. Audit every wait and failure edge from `.open()` through firmware load and hardware init.

Required behavior:

- missing firmware returns a documented error promptly;
- invalid firmware header/version returns a documented error promptly;
- unsupported device revision returns `-ENODEV` / an appropriate error before touching invalid registers;
- missing clocks, power domain, IOMMU or memory resource unwinds partial setup;
- IRQ timeout returns a controlled error and resets/releases state where safe;
- closing a partially initialized file handle does not double-free or leave device busy;
- repeated open/close and suspend/resume does not leak resources;
- no infinite wait, unbounded polling loop or `wait_for_completion()` without a real finite deadline for an operation that can fail;
- no `BUG()`, `BUG_ON()`, panic, or kernel log flood for expected firmware absence.

A userspace `timeout` is not a safety fix for a task stuck in uninterruptible `D` state. SIGKILL does not reliably release such a task. The kernel code must be made safe first. Do not claim an isolated child process makes a broken `.open()` harmless.

Use kernel-appropriate timeouts based on the source protocol and observed hardware timing. Do not add arbitrary tiny timeouts that cause false failures; document the rationale and record elapsed time for firmware load, reset and command completion.

### C4. Runtime power management

Verify balanced `pm_runtime_get/put` (or this kernel's matching API), clocks, regulators, resets and power-domain references across:

- first open;
- initialization success;
- firmware failure;
- unsupported codec request;
- normal decode;
- streamoff/drain;
- close;
- suspend/resume;
- client crash/disconnect.

The decoder must not hold the MFC block at full clocks while idle. It must not power down while buffers or hardware jobs are active. Keep thermal governor and DVFS policy intact; do not hardcode maximum clocks to pass one benchmark.

### C5. Memory/DMA correctness

Identify the driver's exact memory model: CMA, reserved memory, contiguous DMA, DMA-BUF, IOMMU or a vendor-specific allocator. Verify address width, alignment, plane layout, stride, cache synchronization, ownership and lifetime rules. Check that no userspace pointer or physical address is trusted directly.

If MFC cannot consume generic DMA-BUF safely, provide an explicit copy fallback initially. Do not advertise zero-copy until import/export, fences, cache sync and ownership have passed sustained tests. A stable copied path is an acceptable first hardware decode milestone.

---

## 6. Workstream D — V4L2 decoder contract and node-specific diagnostic

### D1. Confirm the API family from the actual driver

Classify the driver as one of:

- V4L2 stateful M2M decoder;
- V4L2 stateless M2M decoder using Request API;
- vendor-specific nonstandard ABI requiring a documented adapter;
- not a decoder / camera capture / encoder / unrelated media node.

Do not choose userspace integration before this classification.

The Linux V4L2 memory-to-memory model uses OUTPUT and CAPTURE queues: compressed input goes to OUTPUT; decoded frames leave through CAPTURE. Both queues must be configured and streamed correctly. An M2M node is not a camera capture node.

Stateful and stateless decoders are different contracts:

- Stateful decoder: hardware/driver maintains stream state; the client feeds encoded bytestream buffers and dequeues decoded frames, including drain and dynamic source-change handling.
- Stateless decoder: userspace maintains codec state and submits per-frame Request API controls with buffers; a stateless plugin is not interchangeable with a stateful decoder.

References for implementation—not a substitute for reading the driver's actual ABI:

- Linux V4L2 M2M: https://docs.kernel.org/userspace-api/media/v4l/dev-mem2mem.html
- Linux stateful decoder interface: https://docs.kernel.org/userspace-api/media/v4l/dev-decoder.html
- Linux stateless decoder interface: https://docs.kernel.org/userspace-api/media/v4l/dev-stateless-decoder.html
- GStreamer `v4l2codecs`: https://gstreamer.freedesktop.org/documentation/v4l2codecs/index.html

### D2. Build a dedicated `nuxel-mfc-diag`

Create a diagnostic utility rather than extending the camera probe with unsafe defaults. Requirements:

- default mode is `--inventory` and never opens a device;
- resolve a device only by exact sysfs driver/name/compatible/known device identity;
- never scan/open every `/dev/video*` node;
- require an explicit `--device /dev/videoN` or validated sysfs identity for active testing;
- require an explicit `--allow-hardware-open` flag for any operation that opens an MFC device;
- require a prior recorded safety receipt (driver/firmware audit) before enabling the flag;
- print exactly which node will be opened and why it is classified as MFC;
- support `--query-only`, `--self-test`, `--decode-test FILE`, `--json` and `--version` with clear semantics;
- never run hardware tests from package post-install, desktop autostart, plugin scanning or a normal Settings page;
- save structured output to `/var/log/nuxel/mfc/` or `/run/nuxel/` without logging user media contents.

For active testing only after the kernel safety gate, query:

- `VIDIOC_QUERYCAP`, with correct interpretation of `capabilities` and `device_caps`;
- OUTPUT and CAPTURE queue type support;
- single-planar vs multi-planar API;
- `VIDIOC_ENUM_FMT` for both queues;
- frame sizes/intervals where supported;
- codec profiles/levels and controls supported by the driver;
- selection/crop/compose support;
- Request API capabilities if stateless;
- streaming, MMAP and/or DMABUF support;
- driver/card/bus information and actual sysfs binding.

Do not use the old capture-only structure layouts/IOCTL sequence for a multi-planar MFC device. Use system V4L2 headers for the target ABI. Validate structure sizes/alignment on aarch64.

### D3. Validate a complete decoder lifecycle

After opening is declared safe, test in increasing scope:

1. QUERYCAP and format enumeration only.
2. Allocate one queue buffer on each side and close cleanly.
3. Configure a known supported input format and output pixel format.
4. Queue a single short stream and capture a decoded frame.
5. Drain, streamoff and reopen.
6. Seek/source-change/flush behavior as applicable.
7. Multiple streams only if actual driver design supports them.

For a stateful decoder, support the actual driver’s required decoder command controls, event subscriptions, source-change resolution handling, capture buffer renegotiation and drain semantics. For stateless decode, implement Request API controls and request/fence lifetime correctly. Never emulate a stateful protocol by guessing at ioctls.

### D4. Prove the node is the decoder

A `/dev/videoN` name alone is not enough. Record sysfs name, platform device, bound driver, device tree compatible, capabilities and formats. Distinguish the MFC node from:

- FIMC-IS camera nodes;
- camera sensor subdevices;
- ISP capture nodes;
- scaler/rotator nodes;
- encoders;
- test/virtual nodes.

Do not change permissions globally to `0666`. Use a narrowly scoped udev rule/group or a privileged service boundary only after validating that the node is MFC and that userspace has a legitimate need.

---

## 7. Workstream E — isolate the kernel test from the production desktop

The first device-open test must never be initiated by Phoc, WebKit, WirePlumber, a GStreamer plugin scanner or a desktop login service.

### E1. Test-mode boundary

Create an explicit maintenance/test mode:

- invoked by an operator from SSH or a recovery-capable console;
- does not start at boot;
- does not execute on the lockscreen;
- logs boot ID, kernel version, firmware hash and exact node;
- refuses if the source audit receipt or firmware verification is absent;
- uses one active test process at a time;
- never shares the decoder with normal media apps during bring-up;
- exits cleanly and reports the last completed stage.

A systemd scope/cgroup can contain process resources, but it does not rescue an uninterruptible kernel task. The kernel path must already be bounded.

### E2. Safety checks before first open

Do not attempt first open until all are true:

- exact hardware IP identified;
- exact driver path audited;
- driver config and DT verified;
- firmware name/path/hash/version verified;
- missing-firmware behavior tested in a safe lab or source-level fault-injection build;
- device node uniquely identified as MFC;
- the owner has explicitly authorized the on-device hardware test;
- live SSH/recovery path is known to remain available.

If any check is `UNKNOWN`, do not open. Continue offline kernel/source tests instead.

### E3. First open procedure

Use a disposable maintenance session with SSH open from a second machine where possible. Capture `dmesg`, service status and CPU state before opening. Run exactly one query/open action, with a clear log. If it does not return within the driver's documented bounded time, stop further tests and classify as a kernel safety blocker. Do not launch additional openers. Do not repeatedly hammer the node. Do not suggest that killing the caller solves `D` state.

Only after first open/close returns promptly should you run small repetition counts (5, then 20, then 100). Include open failures and incomplete init paths, not just successful sessions.

---

## 8. Workstream F — userspace decoder integration

### F1. Do not assume the GStreamer `v4l2codecs` plugin fits

GStreamer documents `v4l2codecs` as support for V4L2 **stateless** video codec drivers. It dynamically generates elements based on system capabilities. If the Exynos MFC is a stateful decoder, `v4l2codecs` may be the wrong plugin. Identify whether the matching stateful MFC implementation is supported by the standard V4L2 plugin in the exact GStreamer version available for Fedora 43, or whether a small, maintainable adapter is required.

Do not compile GStreamer plugin code that merely exposes a fake decoder element. Do not set rank to primary until the actual stream passes.

### F2. Choose one narrow integration path first

Recommended order:

1. Standalone MFC test app or FFmpeg/V4L2 test harness that proves decode without the desktop.
2. A GStreamer element/pipeline if driver ABI and plugin support match.
3. mpv/VLC integration only after the target build's actual FFmpeg/libavcodec backend supports the specific V4L2 M2M API.
4. Browser/WebKit playback only after normal media playback is safe and the existing WebKit media policy is understood.

Do not integrate all players at once. Keep the boot preloading video on the existing safe `--hwdec=no` path unless a separate opt-in test demonstrates no boot-order or firmware dependency. MFC must not become a required boot gate.

### F3. Audit the exact Fedora packages and build options

Before adding packages, inspect the actual Fedora 43 aarch64 repo metadata and current RPMs:

- GStreamer base/good/bad-free/ugly/openh264 components as relevant;
- `gstreamer1-plugin-libav` or equivalent if a codec parser is required;
- the package containing V4L2 stateful or stateless decode integration;
- FFmpeg-free vs full FFmpeg packages and codec/driver compile flags;
- mpv build features and available decoder backends;
- VLC build features, only if VLC integration is in scope after first decode.

Do not pull random packages from an unrelated Fedora release or third-party unsigned COPR. Keep Fedora repository signing/GPG validation enabled. Ensure there is no conflicting `ffmpeg-free` / full FFmpeg ABI overwrite.

For mpv, collect `mpv --version`, `mpv --hwdec=help`, and the linked libavcodec feature matrix. The existing preload command's `--hwdec=no` must remain explicit. Add hardware mode only to normal media playback preferences, never to the preload controller by default.

### F4. Safe plugin and registry behavior

The global GStreamer guard exists for a reason. Implement a device-specific allowlist or a decoder access path that does not cause plugin scanners to probe arbitrary video devices.

Requirements:

- keep KMS/OpenGL GStreamer plugins disabled unless independently justified;
- keep WirePlumber `hardware.video-capture = disabled`;
- do not enable generic camera capture;
- do not let WebKit's autodetect path scan all V4L2 devices;
- do not restore every disabled plugin when one MFC decoder is ready;
- ensure plugin scanning cannot open the MFC device during boot/login;
- provide a known-safe registry/cache lifecycle;
- if a specific plugin is enabled, test plugin scanning while MFC is busy and after MFC exits;
- if global discovery cannot be safely restricted, expose MFC only through a small daemon/helper that owns the device and provides a narrow IPC API to approved clients.

### F5. Player policy and fallback

Implement a truthful decode policy, for example:

- `auto`: use MFC only when kernel/firmware/decoder state is `AVAILABLE` and requested codec/profile/size is supported; otherwise software decode.
- `hardware`: attempt only a verified MFC backend; show an explicit error and offer software fallback if unavailable.
- `software`: never open an MFC node.

Never silently claim “hardware” after fallback. The player or diagnostics should show the actual active decoder and why fallback occurred. Default normal playback to `auto` only after MFC passes the full safety gate. Default to `software` while the MFC path is unverified.

Handle:

- unsupported codec/profile/level;
- unsupported resolution/bit depth/chroma format;
- truncated/corrupt streams;
- variable frame rate and timestamps;
- seek, pause, resume, rate change, EOF and drain;
- dynamic resolution change where supported;
- device busy and simultaneous application requests;
- process termination while buffers are queued;
- firmware/driver error after playback starts.

---

## 9. Workstream G — DMA-BUF / GPU presentation is a separate optimization

The MFC may output a decoded frame into DMA-BUF, but it does not follow that Mali, EGL, Phoc or the current framebuffer bridge can consume that buffer without copying.

Current Nuxel graphics evidence documents a kbase/Mali path and a CPU-based final framebuffer bridge. The previous GPU mission must not be treated as proof of MFC buffer import or direct scanout.

### G1. Separate the claims

Track at least these independent states:

1. `MFC_DECODE`: MFC produced a decoded frame.
2. `MFC_DMABUF_EXPORT`: capture buffer can be exported as DMA-BUF.
3. `MALI_EGL_IMPORT`: Mali EGL can import that exact fourcc/modifier/plane layout.
4. `PHOC_COMPOSE`: compositor can sample the imported frame correctly.
5. `FB_BRIDGE_PRESENT`: final panel path displays it correctly.
6. `ZERO_COPY_END_TO_END`: no CPU copy exists at every handoff and synchronization is correct.

Do not combine them into one `hardware_accelerated=true` boolean.

### G2. Buffer correctness

For each supported decoded pixel format, record:

- fourcc and any modifier;
- width, height, stride, offsets and plane count;
- buffer memory type and exporter;
- import method and importing process;
- explicit/implicit fence support and synchronization behavior;
- cache maintenance requirements;
- CPU map/copy points and byte counts;
- lifetime and release timing;
- visual correctness with odd dimensions, crop, rotation and color conversion.

If DMA-BUF cannot be safely shared with Mali, implement one conversion/copy boundary and report it honestly. Never pass an unsupported format/modifier to EGL based on a guessed mapping.

### G3. Keep first milestone simple

The first MFC milestone may use a CPU-mapped or copied decoded frame and ordinary Wayland SHM presentation. Prove the decoder itself first. Optimize DMA-BUF later without destabilizing the successful hardware decode path.

---

## 10. Codec support discovery and staged playback matrix

Do not assume Samsung marketing maxima are Nuxel capabilities. The driver, firmware, codec profile, format, queue memory model, thermal system and userspace all constrain actual support.

### Stage 0 — identify actual capabilities

Collect the driver's advertised compressed OUTPUT formats and raw CAPTURE formats, profile/level controls, maximum frame sizes, supported frame intervals, bit depths, chroma subsampling, pixel layouts and memory types. Produce a machine-readable capability file generated from real device reports, not hand-authored specs.

### Stage 1 — minimum hardware proof

Try one short, known-good H.264 stream at 720p30, 8-bit 4:2:0, only if actual caps include it. Verify at least one decoded frame, checksum or pixel comparison against a trusted software reference, monotonic timestamps and clean teardown.

### Stage 2 — everyday HD

If Stage 1 passes, test:

- H.264 720p30;
- H.264 1080p30;
- H.264 1080p60 only if advertised;
- HEVC Main 1080p30 only if advertised.

### Stage 3 — higher bitrate / codecs

Only if the driver's caps expose them:

- H.264 High profile and higher levels;
- HEVC Main / Main10;
- VP9 profile 0 / 2;
- other formats supported by exact V4L2 driver.

### Stage 4 — 4K experiments

4K is not an initial acceptance requirement. Attempt 3840×2160 at 24/30 fps only when the decoder advertises the format/profile/resolution and the buffer/memory budget supports it. Test 4K60 only if frame-rate/level/throughput evidence justifies it. Do not write “4K supported” after a single short 4K sample begins playing. Require sustained playback and thermal stability.

### Stage 5 — 10-bit / HDR

Treat decode bit depth and HDR display as separate claims. A decoder accepting 10-bit input does not prove a complete HDR path. Validate output pixel format, colorimetry, range, transfer function, chroma sampling, compositor handling, panel capabilities and external display separately. Nuxel may decode a 10-bit stream and tone-map it to SDR; that is not HDR display.

### Test media rules

Use small, lawful test streams with documented provenance, exact codec/profile/level, resolution, frame rate, pixel format, bit depth, bitrate, duration and SHA-256. Prefer generated fixtures or freely licensed samples. Do not commit huge media binaries. Keep a local hardware test directory and a fixture manifest. Use identical source files for software and hardware benchmarks.

---

## 11. Benchmarking — prove the real performance impact

Benchmark MFC vs software decode with identical input, resolution, frame rate, output sink and playback duration. Separate decoder time from presentation cost.

### Required metrics

For every test record:

- input codec/profile/level, resolution, fps, bitrate, bit depth and file hash;
- decoder backend name and device identity;
- negotiated input/output pixel formats and memory type;
- proof MFC was active;
- playback duration and decoded frame count;
- dropped/repeated frames and timestamp discontinuities;
- A/V sync offset where audio is included;
- decoder latency and end-to-end render frame time;
- process CPU use and total system CPU use (normalized and explained);
- memory peak and buffer count;
- copied bytes per frame and estimated memory bandwidth where possible;
- MFC clock/power state if reliably exposed;
- SoC temperature and thermal throttle state before/during/after;
- battery/energy only if a trustworthy supported measurement exists;
- suspend/resume, seek, pause/resume and teardown result.

### Baseline methodology

1. Reboot to a clean known state and record boot ID.
2. Wait for the same idle settling period.
3. Run the same source file at the same output resolution and display path.
4. Use software decode explicitly, not automatic selection.
5. Repeat at least three runs and report median plus range.
6. Cool to a comparable starting temperature for the hardware test.
7. Run hardware decode explicitly and capture the same metrics.
8. Repeat at least three runs.
9. Compare CPU use, dropped frames, thermals and battery only under comparable conditions.

Do not compare software decode with display disabled to hardware decode with the compositor active. Do not infer energy savings from CPU percentage alone. Do not claim a speedup from a one-off run.

### Required report table

| Stream | Software decode | MFC decode | CPU reduction | Dropped frames | Sustained pass | Temperature/throttle |
|---|---|---|---:|---:|---|---|
| H.264 720p30 | measured | measured | measured | measured | PASS/FAIL | measured |
| H.264 1080p30 | measured | measured | measured | measured | PASS/FAIL | measured |
| H.264 1080p60 | if supported | if supported | measured | measured | PASS/FAIL | measured |
| HEVC 1080p30 | if software package supports | if MFC caps support | measured | measured | PASS/FAIL | measured |
| 4K30 | optional | only if caps permit | measured | measured | PASS/FAIL | measured |
| 4K60 | optional | only if caps permit | measured | measured | PASS/FAIL | measured |

---

## 12. Service boundaries and diagnostics state model

Implement a machine-readable status interface, for example `/run/nuxel/mfc/status.json` and a stable CLI `nuxel-mfc-diag status --json`. Use a versioned schema such as `nuxel.mfc.status/1`.

Suggested truthful states:

- `NOT_PRESENT`
- `UNIDENTIFIED_VIDEO_NODE`
- `BLOCKED_DRIVER_MISSING`
- `BLOCKED_DRIVER_UNSAFE`
- `BLOCKED_FIRMWARE_MISSING`
- `BLOCKED_FIRMWARE_HASH`
- `BLOCKED_FIRMWARE_ABI`
- `BLOCKED_DT_RESOURCE`
- `BLOCKED_IOMMU_DMA`
- `BLOCKED_UNSUPPORTED_CODEC`
- `AVAILABLE_PROBE_ONLY`
- `AVAILABLE_HARDWARE_DECODE`
- `AVAILABLE_HARDWARE_DECODE_WITH_COPY`
- `AVAILABLE_HARDWARE_DECODE_DMABUF`
- `AVAILABLE_SOFTWARE_ONLY`
- `TEST_FAILED`
- `NOT_TESTED_ON_DEVICE`

Each state needs `reason`, `source_commit`, `kernel_release`, `device`, `firmware_sha256` when available, `last_test_time`, and a capability array. Do not say `AVAILABLE_HARDWARE_DECODE` until an actual test file has been decoded by MFC and proof is stored.

Diagnostics must be read-only by default. A normal Settings page may read the JSON status file; it must never open a decoder node or run a benchmark. Any hardware test button must be explicit, privileged, maintenance-mode-only and explain the device/stream before starting.

---

## 13. Build and release integration

### 13.1 Kernel build

- Use only the pinned kernel source commit unless deliberately updated with a matching evidence-based reason.
- Add exact config symbols and DT changes only after source analysis.
- Add a required patch sidecar for a mission-critical patch.
- Verify the generated `.config` contains the expected MFC symbols after defconfig/fragment/olddefconfig.
- Build the kernel and target DTB(s) from the canonical wrapper.
- Record toolchain version, compiler, source commit, patch hashes and resulting artifact hashes.
- Compare kernel config and DTB selection against the last known-good S10+ image.
- Keep prior kernel/DTB available for rollback.

### 13.2 Rootfs integration

- Add only packages that are actually needed and available from signed Fedora repositories.
- Do not make MFC firmware or plugin scanner probes required for generic Nuxel boot.
- Preserve mpv boot-splash path, software fallback and `--hwdec=no`.
- Install diagnostic tools and the versioned capability schema.
- Install firmware only after exact checksum and provenance verification.
- Keep WirePlumber audio/Bluetooth settings unchanged and video-capture disabled.
- Keep the GStreamer guard active by default unless a narrowly tested decoder-only path is introduced.
- Verify that fresh clean image build includes all required packages/files and never relies on manual installs from a previously provisioned handset.

### 13.3 Image verification

Add rootfs verification that checks:

- MFC config/driver state expected by the image profile;
- required firmware file presence/hash only for MFC-enabled images;
- software decoder fallback always present;
- GStreamer guard installed and session hooks correct;
- WirePlumber video-capture remains disabled;
- `nuxel-mfc-diag` exists and defaults to inventory-only;
- no package install or service startup attempts MFC device open;
- no boot-time decoder test or MFC hard dependency.

If a release image advertises hardware decode but the required driver/firmware/plugin/test receipt is missing, fail the release build. A normal software-only recovery image may still build.

---

## 14. Test suite — automated, simulated and on-device

### 14.1 Unit and static tests

Add tests for:

- parsing firmware manifest and destination paths;
- checksum match/mismatch/missing files;
- firmware status classification;
- kernel config symbol verification;
- capability JSON schema and state transitions;
- video node identity allowlist;
- inventory mode never opening device nodes;
- active mode refusing without explicit opt-in and safety receipt;
- no generic `/dev/video*` scan/open;
- guard default behavior and reversible plugin restoration;
- session scripts still invoke the guard before desktop media discovery;
- WirePlumber retains audio/Bluetooth and camera capture stays disabled;
- software fallback selection when MFC is unavailable;
- no boot controller changes to hardware decode;
- no MFC test runs at install/boot/login/Settings render.

Mock device file operations and ioctl results. Unit tests must never touch real `/dev/video*` or `/dev/media*` nodes by default.

### 14.2 Kernel/source tests

- config fragment merge and final `.config` assertions;
- patch applies to the exact pinned source;
- compile affected driver objects and full kernel;
- sparse/smatch/checkpatch where compatible with this 4.14 tree;
- firmware missing/invalid path source tests or a safe fault-injected test kernel;
- verify every error path unwinds clocks, PM refs, memory and queues;
- verify no unbounded wait remains on expected firmware absence.

### 14.3 Hardware tests (opt-in only)

Hardware tests require an owner-approved physical S10+ and the complete safety checklist. Run in a maintenance SSH session, not desktop startup.

Minimum acceptance:

1. MFC node identified unambiguously.
2. QUERYCAP and formats complete promptly.
3. First open and close complete promptly.
4. Repeated open/close succeeds or fails cleanly 100 times.
5. Missing firmware returns promptly in a controlled test and does not freeze system services.
6. One known-supported H.264 clip yields real decoded output from MFC.
7. Decoded frame is validated against reference output.
8. Playback appears on the real Nuxel display without new flicker, corruption or UI lockup.
9. Hardware vs software benchmarks are recorded.
10. Pause, resume, seek, EOF, drain and teardown work.
11. Thermal stability is tested for 20–30 minutes at the highest currently claimed everyday mode.
12. After test, all desktop/session services remain responsive and software fallback still works.

### 14.4 Regression tests

Re-run relevant existing test suites and capture outputs:

- repository formatter/linter/unit tests;
- `make golden-gate` or current equivalent;
- `make smoke` or current equivalent;
- kernel config/build tests;
- image rootfs verifier;
- Nuxel session startup tests;
- preload-cinema tests;
- graphics-profile and GPU presentation tests;
- WebKit/PWA boot, lockscreen and app-switch tests;
- PipeWire/WirePlumber audio and Bluetooth smoke tests.

GPU and desktop acceleration must not regress because MFC is added. Audio and Bluetooth must remain operational. Camera capture must remain honestly blocked unless independently implemented in another mission.

---

## 15. Guard transition plan — never switch all at once

The existing GStreamer guard must remain in place through kernel and first-decode development. Once a real MFC decoder has passed the V4L2 and lifecycle tests, transition in small steps:

**Transition A — explicit diagnostic only:** leave all plugins disabled; MFC test utility talks directly to the known decoder node.

**Transition B — one approved integration:** enable one decoder integration in a private test registry/process, restricted to the identified MFC node. Keep desktop scanner, WebKit autodetect and WirePlumber camera monitor blocked.

**Transition C — media-player test session:** enable hardware decode only for a separate user-invoked media test, preserving software fallback and boot behavior.

**Transition D — normal media `auto` policy:** after sustained tests and all regressions pass, expose MFC as an optional decoder for the normal media app.

At each transition, maintain a one-command rollback that restores the previous plugin guard, registry and player preference. The rollback must not delete software codecs, audio elements or media files.

If a specific GStreamer shared object contains both V4L2 camera probing and MFC decoder support and cannot safely be separated, do not restore it globally. Keep direct helper or a safer user-space integration until the risk is resolved.

---

## 16. Documentation and capability claims

Update or create:

- `docs/beta-finalization/live/PWNAGE-61000-MFC-BASELINE.md`
- `docs/beta-finalization/live/PWNAGE-61000-MFC-REPORT.md`
- `docs/beta-finalization/live/PWNAGE-61000-MFC-TODO.md`
- `docs/beta-finalization/live/evidence/pwnage-61000/`
- versioned MFC status/capability schema;
- decoder test media manifest;
- kernel/firmware compatibility matrix;
- operator procedure for safe on-device tests;
- recovery and rollback procedure.

The report must state separately:

1. silicon potential (not a software feature claim);
2. kernel driver implementation status;
3. firmware availability/compatibility status;
4. V4L2 API mode and capabilities;
5. actual codec/profile/resolution tests;
6. userspace integration status;
7. memory-copy / DMA-BUF status;
8. measured CPU and thermal impact;
9. known limitations and blocked features.

Never use wording such as “4K supported”, “hardware accelerated”, “zero-copy”, “smooth 4K” or “HDR enabled” unless the exact corresponding test is documented. Prefer a precise statement like “MFC H.264 1080p30 decode verified for 20 minutes; output copied to SHM; no 4K test yet.”

---

## 17. Rollback and recovery

Provide explicit rollback for each layer:

- kernel/DTB: retain the last known-good image and recovery instructions;
- firmware: remove only the MFC firmware file staged by this mission; do not remove shared ABOX/audio firmware;
- config: revert only MFC config and driver patches;
- userspace: restore the GStreamer guard and previous registry state;
- player: restore software-only playback;
- service/status: report `BLOCKED` without auto-retrying the hardware;
- rootfs: preserve boot splash and audio policy.

Do not flash BOOT, recovery, modem, EFS or other partitions automatically. Do not run Heimdall or `dd` to a live block device unless the owner gives a direct, explicit instruction for that action in the active task. Build and stage first. Include checksums and exact rollback commands. Verify the fallback path before any owner-supervised physical deployment.

---

## 18. Definition of done

PWNAGE-61000 is **FULLY_DONE** only when all applicable conditions below are met:

### Core decoder

- [ ] Exact Exynos 9820 MFC IP and driver compatibility documented.
- [ ] Exact kernel source/commit and selected driver implementation recorded.
- [ ] MFC device-tree node proven to match the real S10+ board/revision.
- [ ] Firmware filename, binary version, provenance and SHA-256 verified.
- [ ] Driver config and build output verified from final `.config` and built image.
- [ ] Missing/invalid firmware and failed hardware init unwind cleanly without unbounded waits.
- [ ] MFC node identified by sysfs/driver, not by `/dev/videoN` guess.
- [ ] V4L2 API type and queues work as implemented.
- [ ] At least one real supported video frame is decoded by the MFC, with objective proof.

### Player integration

- [ ] A single tested software fallback remains intact.
- [ ] One normal media player/pipeline can explicitly select verified MFC decode.
- [ ] Actual backend is shown; fallback is not misreported as hardware.
- [ ] GStreamer guard is only relaxed narrowly and reversibly.
- [ ] WirePlumber camera capture remains disabled; audio/Bluetooth regressions absent.
- [ ] Boot preload remains software-safe and does not depend on MFC.

### Quality and performance

- [ ] Identical-file software vs MFC benchmarks are saved.
- [ ] CPU/frame-drop/latency/thermal results recorded with methodology.
- [ ] Every codec and resolution claim is backed by hardware caps and on-device playback.
- [ ] At least 20–30 minutes of sustained playback passes at the highest claimed everyday mode.
- [ ] Pause, resume, seek, EOF, drain, suspend/resume and close paths tested as supported.
- [ ] DMA-BUF/zero-copy status is reported independently from MFC decode.

### Delivery

- [ ] Clean kernel build and clean rootfs/image build pass.
- [ ] Unit, static, regression and hardware tests are documented.
- [ ] Recovery/rollback procedure is complete and tested where possible.
- [ ] `PWNAGE-61000-MFC-REPORT.md` includes links/hashes to evidence.
- [ ] No unresolved safety issue is hidden behind a green overall status.

If one of the hardware-specific items cannot be run because the phone or firmware is unavailable, label the mission `IMPLEMENTED_NOT_PHYSICALLY_VERIFIED` or `BLOCKED_<reason>`. Do not claim `FULLY_DONE`.

---

## 19. Required execution order and agent behavior

Follow this order. Do not skip ahead to GStreamer packages or a player checkbox.

1. Inspect current branch, source, live image and handset state.
2. Write the baseline and the exact MFC source/DT/firmware compatibility matrix.
3. Determine whether the pinned 4.14.253 tree has a compatible implementation.
4. Resolve exact firmware ABI, provenance and actual binary availability.
5. Implement kernel config/DT/driver corrections and safe failure paths.
6. Build kernel and rootfs; run static and unit tests.
7. Validate inventory-only MFC diagnostic and the explicit safety gate.
8. Obtain owner approval before first physical node open/test.
9. Run staged V4L2 query/open/decode tests.
10. Prove one actual MFC-decoded frame and capture evidence.
11. Integrate one userspace playback path with software fallback.
12. Measure performance and sustained thermal behavior.
13. Relax the plugin guard narrowly only if proven necessary.
14. Run full desktop/audio/Bluetooth/GPU/preload regression tests.
15. Produce rollback, release artifacts, evidence and a final honest report.

### How to work

- Keep a concise live checklist in `PWNAGE-61000-MFC-TODO.md` and update it as work is completed.
- Commit changes in small logical commits if the user's workflow permits; do not amend unrelated history.
- Use explicit `PASS`, `FAIL`, `BLOCKED`, `NOT_RUN` labels.
- Every claimed pass must link to a command output, test, source location or physical evidence file.
- Do not delete existing safeguards, tests or reports to make the tree look cleaner.
- Do not hide warnings or change tests to weaken acceptance criteria.
- If the exact hardware or source support is missing, do as much offline implementation/testing as safely possible, then identify the single concrete blocker and the next action.
- Do not ask the user to repeat facts already present in the repo or supplied task.
- Do not ask for permission to read/analyze/build source. Ask for approval only before a consequential physical-device action such as opening the previously wedged MFC node, rebooting/flashing the handset, or acquiring proprietary firmware from the owner's phone.
- Do not perform irreversible actions without that approval.

---

## 20. Final response format from the agent

When finished, return:

1. **Status:** `FULLY_DONE`, `IMPLEMENTED_NOT_PHYSICALLY_VERIFIED`, `BLOCKED_<reason>` or `FAILED`.
2. **What changed:** exact files and behavior, not generic summaries.
3. **Driver/firmware compatibility:** actual IP, kernel driver, DT, requested firmware name, version and hash.
4. **MFC proof:** exact device identity, ioctl/decode test, file properties and evidence paths.
5. **Codec matrix:** only physically verified combinations.
6. **Performance:** matched software vs hardware results, with methodology and thermal status.
7. **Userspace integration:** plugin/player backend, actual selected decoder, fallback behavior.
8. **Safety:** what still stays disabled and why; any former D-state risk resolved or remaining.
9. **Build/test results:** exact commands and pass/fail counts.
10. **Deployment:** built artifacts and checksums; clearly state whether a physical flash/reboot was performed (default: no).
11. **Rollback:** exact commands and retained known-good images.
12. **Next blocker:** one concise action if anything remains.

**Do not report “MFC enabled” merely because a kernel config symbol or GStreamer plugin is present. The mission is about a real, safe, measured hardware decode pipeline on the S10+.**
