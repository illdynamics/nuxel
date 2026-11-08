# FULL-PWNAGE-51000
# NUXEL FINAL SYSTEM BLOCKERS — USER NAMESPACES & FLATPAK, PHOC LINUX-DMABUF STABILITY, WEBKITGTK ACCELERATION, macOS MTP WORKFLOW, DRIVER STATUS, BOOT PERFORMANCE, APP DRAWER PERFORMANCE AND CLEAN REBOOT

## Complete kernel preparation, TWRP-authorized deployment, graphics reliability, application sandbox validation and system performance mission

**Mission ID:** PWNAGE-51000  
**Target:** Samsung Galaxy S10+ SM-G975F / `beyond2lte` / Exynos 9820  
**OS:** Nuxel, custom Fedora-based ARM64 mobile Linux  
**Current kernel hypothesis:** Samsung downstream 4.14.253; verify live  
**GPU:** Mali-G76 MP12 using Samsung/vendor kbase (`/dev/mali0`)  
**Compositor:** Phoc / Wayland, GPU context active  
**Presentation:** Wayland screencopy → `nuxel-wl-fb` → single `/dev/fb0` owner → Samsung DECON panel  
**Panel:** 1440×3040; framebuffer virtual geometry reported as 1440×6080  
**Current recovery state:** Owner plans to begin with phone in TWRP, USB connected and ready for a carefully authorized kernel reflash  
**Mission type:** hardware/kernel capability work, crash diagnosis, graphics-stack repair, secure sandbox enablement, app/runtime integration, measured performance optimization, TWRP recovery and physical verification.

---

# 0. PRIMARY OBJECTIVE

Resolve the remaining hard blockers without destroying the working Nuxel installation. The mission is deliberately staged: verify and back up the functioning kbase/Phoc/fbdev baseline; prepare and, with explicit owner authorization, flash a kernel enabling the namespace support needed by Flatpak; validate the new kernel using a strict two-outcome boot/recovery agreement; then continue with the Phoc linux-dmabuf crash, WebKitGTK acceleration, macOS file-transfer user experience, outstanding device capability diagnostics, boot speed, sluggish app drawer and the long black screen during ordinary reboot.

Do not confuse a kernel option with a working product feature. `CONFIG_USER_NS=y` is only a kernel prerequisite; Flatpak must successfully create a secure Bubblewrap sandbox, integrate with the Nuxel Wayland/D-Bus/portal session and launch a real ARM64 application. Likewise, advertising the Linux DMA-BUF Wayland protocol is not proof that the Mali kbase exporter, Phoc importer and WebKitGTK accelerated backing store agree on formats, modifiers, FD ownership, coherency and synchronization.

The working compositor GPU path is valuable and must be preserved. Do not regress Phoc acceleration to Pixman merely to make WebKit start. Keep a reliable shared-memory fallback and a fast rollback mechanism.

---

# 1. OWNER-PROVIDED LIVE STATE — USE AS THE INITIAL HYPOTHESIS

The owner reports this post-PWNAGE-48000 state:

- `phoc` holds three references to `/dev/mali0`, one to `/dev/udmabuf`, and an `anon_inode:dmabuf_udmabuf`.
- kbase debugfs lists a GPU context owned by `phoc`.
- `nuxel-wayland`, `nuxel-wl-fb` and `nuxel-web` are all active.
- Bridge reports `FRAMES_OK` and `decon_pan_failed=0`.
- `/run/nuxel-gpu-fallback` is absent.
- `/dev/fb0` is restored. Physical display is 1440×3040, with virtual geometry 1440×6080.
- `/dev/dri` is absent. This is expected in the current vendor kbase architecture and is not, by itself, proof that the GPU is unused.
- Phoc has a working vendor kbase GPU context and the main display is alive.
- WebKitGTK/GTK GL remains on software fallback: `GTK failed to initialize GL` was reported. WebKit's Wayland EGL path expects a buffer-sharing path the current Mesa kbase userspace does not provide. A Wayland-enabled Mesa build was tried and failed; it was reverted.
- The final Wayland screencopy → `/dev/fb0` copy/upscale is CPU work.
- Current kernel config has `CONFIG_USER_NS=n`; Flatpak is blocked.
- USB MTP enumerates successfully, but macOS Finder does not mount MTP. OpenMTP/MTPLX is the appropriate Mac-side client. USB mass-storage mode is not compiled into this kernel.
- Mobile network, camera, NFC and sensor capability states remain at their existing driver/firmware blockers.
- WebKit acceleration must not be enabled until the live Phoc `linux-dmabuf` crash has been isolated and repaired.
- Recovery evidence was saved under `/var/backups/nuxel/kbase-gpu-*`; pre-Wayland-test EGL backup is `/var/backups/nuxel/libEGL_mesa.so.0.0.0.pre-wayland`.
- The earlier PWNAGE-48000 source report is `docs/beta-finalization/live/PWNAGE-48000-KBASE-GPU-REPORT.md`.
- The earlier evidence directory is `docs/beta-finalization/live/evidence/pwnage-48000-kbase-gpu/`.
- Relevant commits supplied by the owner: `90ff0d6` (kbase GPU acceleration), `9340301` (post-reboot BOOT partition readback), `01cd482` (post-reboot AMOLED frame capture).
- `boot-original.img` in the repository is a dummy and is not a valid backup.

Treat all of the above as owner-provided evidence, not as an excuse to skip rechecking. State may have changed since the capture. Before modifying anything, reproduce the facts, save a new timestamped baseline and reconcile the source commit/live kernel/build IDs.

---

# 2. GLOBAL NON-NEGOTIABLE SAFETY AND PRESERVATION RULES

## 2.1 Kernel/TWRP operation boundary

The owner explicitly authorizes preparing a kernel change for the `CONFIG_USER_NS` requirement and intends to start in TWRP with USB connected. This is not blanket permission to flash arbitrary partitions or to repeatedly risk a working phone.

- Obtain explicit owner approval for the exact built image and exact target partition immediately before the first flash.
- Verify the handset variant is exactly SM-G975F / beyond2lte; do not assume another S10/S10e/S10 5G image is compatible.
- Read the actual partition map from the running recovery/device. Do not guess partition names or offsets.
- Verify whether the device is A-only or A/B from actual partition metadata and current bootloader/recovery state. Do not rely on memory.
- Use the repository's pinned kernel source/config and actual S10+ image packaging. Preserve matching DTB/DTBO and ramdisk/header expectations for the installed kernel format.
- Do not flash `vendor`, `vbmeta`, `dtbo`, modem, EFS, bootloader or unrelated partitions as a convenience. If a particular related partition is technically required, explain why, provide a separate verified artifact and ask the owner for explicit approval.
- Do not use Heimdall/Odin/fastboot/bootloader commands unless the owner separately approves a documented recovery plan. The intended deployment route is TWRP.
- Do not use a dummy file, unverified image, stale kernel artifact or a build from a different device tree.
- Do not automatically retry a failed flash or boot. One properly backed-up attempt, then evaluate the two outcomes below.

## 2.2 Preserve a real known-good recovery image

Before flash:

1. Inspect the existing TWRP backups under `/var/backups/nuxel/kbase-gpu-*` and confirm which one represents the current known-good boot/kernel image and matching device tree.
2. Create a fresh TWRP backup of the exact partition(s) that will be replaced. Do not rely on `boot-original.img`; the owner explicitly says it is dummy content.
3. Verify backup file size, checksum, archive integrity and that it can be read from the host computer. Copy it off-device to the Mac/host. A backup only on the phone is not a sufficient recovery plan if storage becomes inaccessible.
4. Save the currently installed kernel version, config, build ID, boot image manifest, DTB hashes, command line and partition identity to the evidence directory.
5. Keep the EGL backup `/var/backups/nuxel/libEGL_mesa.so.0.0.0.pre-wayland` intact. Do not replace/delete it. Also record the hash and current working vendor/Mesa libraries.
6. Ensure TWRP can access the backup and the new image before flashing. Do not proceed if the only rollback copy is unreadable or has not been copied off-device.

A read-only raw partition backup may be taken only after verifying the exact block-device path. Prefer TWRP's proper Boot partition backup UI when it captures the exact partition. Never issue a guessed `dd of=/dev/block/...` command. Any write to a block partition must be through the owner-approved TWRP flashing operation and verified target image.

## 2.3 Exact two-outcome boot agreement

After the owner approves and the new kernel has been flashed:

**Outcome A — Nuxel boots successfully:**

- Boot reaches the expected Nuxel Home/lockscreen.
- `nuxel-wayland`, Phoc, `nuxel-wl-fb`, Bridge and web host become healthy.
- kbase GPU context is present and display output works.
- touch works, `/dev/fb0` and panel geometry are correct, DECON presentation succeeds, Wi-Fi/SSH and any expected USB/serial recovery path work.
- record the new kernel hash/version/config and boot log; run smoke tests.
- only after all boot acceptance checks pass may the agent continue with the non-kernel tasks in this mission.

**Outcome B — Nuxel does not boot successfully:**

This includes bootloop, hang on black screen beyond the agreed boot deadline, return to TWRP, lost display, unusable touch, kernel panic, missing storage/Wi-Fi required for recovery, or any critical service/display failure.

- Stop. Do not try alternative kernel flags, another boot image or a different partition in the same recovery session.
- The owner returns to/remains in TWRP. Restore the verified pre-flash boot/kernel backup through the exact known TWRP path.
- Verify the restoration by checksum/readback if the TWRP process allows it.
- Boot the restored known-good Nuxel kernel once and confirm display, touch, kbase and SSH are back.
- Record the failed image hash and failure evidence. Keep the `CONFIG_USER_NS` experiment reverted/branched; do not repeat without a revised build and explicit owner approval.
- Continue with non-kernel tasks only after the original system is verified healthy.

Do not interpret a TWRP screen by itself as an automatically successful boot. The success condition is a full Nuxel boot with verified core services and input/display. Never leave the phone in an unknown half-booted state and never loop TWRP flashes.

## 2.4 Never weaken sandbox/security to claim Flatpak support

- No setuid-root Bubblewrap workaround as a default.
- No `--no-sandbox`/unconfined Flatpak mode.
- No broad `--filesystem=host`, `--device=all`, privileged container or disabled SELinux.
- No making all GTK apps run as root.
- No broad world-writable `/dev` or configfs permissions.
- No claiming `CONFIG_USER_NS=y` proves the Flatpak sandbox works.

## 2.5 Display ownership and GPU baseline

- `nuxel-wl-fb` remains the sole `/dev/fb0` writer.
- Phoc remains the compositor and uses the currently working kbase graphics route.
- Never start a second framebuffer presenter or direct display writer.
- Never enable WebKit accelerated backing store on the normal boot path until Phoc's dmabuf crash is fixed and repeated stability tests pass.
- Keep the existing shared-memory/software fallback and known-good EGL backup.
- Do not replace the working kbase EGL path with the failed experimental Mesa Wayland build.

---

# 3. PHASE 0 — AUDIT, BASELINE AND REPRODUCIBILITY

Create/update:

`docs/beta-finalization/live/PWNAGE-51000-TODO.md`  
`docs/beta-finalization/live/evidence/pwnage-51000/`

Subdirectories:

- `baseline/`
- `kernel/`
- `twrp/`
- `flatpak/`
- `dmabuf/`
- `webkit/`
- `mtp-macos/`
- `drivers/`
- `boot-performance/`
- `drawer-performance/`
- `shutdown/`
- `deployment/`

## 3.1 Repository baseline

Record:

- branch/commit/dirty state and all owner-provided commits above;
- active kernel source repo, branch, commit, local patches and exact build command;
- kernel config source and defconfig fragments;
- rootfs builder and package manifests;
- kernel packaging script, image header/DTB layout and recovery installation instructions;
- systemd version and all active Nuxel units relevant to display/boot/shutdown;
- WebKitGTK version/build flags and GTK version;
- Phoc/wlroots/Wayland protocol versions;
- Mesa and vendor kbase userspace libraries and hashes;
- current graphics environment variables and service overrides;
- current fallback marker semantics.

Do not modify the running system until this record exists.

## 3.2 Live device and graphics baseline

Collect safely:

```sh
uname -a
cat /proc/cmdline
zcat /proc/config.gz 2>/dev/null | grep -E 'CONFIG_(USER_NS|NAMESPACES|UTS_NS|IPC_NS|PID_NS|NET_NS|SECCOMP|SECCOMP_FILTER|CGROUPS|OVERLAY_FS)'
ls -l /dev/mali0 /dev/udmabuf /dev/fb0 /dev/dri 2>&1
ps -ef | grep -E 'phoc|nuxel-wayland|nuxel-wl-fb|nuxel-web'
```

Use the actual config source if `/proc/config.gz` is unavailable. Capture:

- Phoc open FDs for `/dev/mali0`, `/dev/udmabuf` and dma-buf anon inode;
- kbase debugfs context owner and GPU job/activity information if available;
- `nuxel-metricsd`/socket state, `FRAMES_OK`, `decon_pan_failed`, bridge status;
- `/run/nuxel-gpu-fallback` existence/content;
- framebuffer fixed/variable screen info and virtual geometry;
- actual panel mode and DECON handoff state;
- `/dev/dri` absence/presence, but do not treat absence alone as GPU failure under kbase;
- vendor and Mesa EGL/GLES library paths, SONAMEs, symbols, architecture and build IDs;
- `eglinfo`, `glxinfo` only if the environment genuinely supports them; label each test path (surfaceless, Wayland, GBM, etc.).

Verify no new GPU experiment has regressed the compositor. Keep current graphics baseline as a named, tested configuration.

## 3.3 Baseline user experience metrics

Record before changes:

- power-on to first visible boot splash/frame;
- power-on to lockscreen interactive;
- power-on to Home fully interactive;
- service readiness timestamps and the actual critical path;
- normal reboot request → screen goes black;
- normal reboot request → actual kernel reset/reboot/bootloader handoff;
- app drawer gesture → first visible drawer frame;
- drawer first paint → all visible app icons ready;
- drawer scroll frame-time/jank on a representative app count;
- CPU and memory during idle, lockscreen, drawer and app launch;
- WebKit software fallback renderer and GPU/CPU utilization.

Use the same test data and cache state before/after.

---

# 4. KERNEL CHANGE FOR FLATPAK — ENABLE USER NAMESPACES THE RIGHT WAY

## 4.1 Why this kernel change is being considered

The current kernel has `CONFIG_USER_NS=n`. Flatpak uses Bubblewrap to construct isolation boundaries. Flatpak's own user-namespace requirements identify `CONFIG_USER_NS=y` as the minimum for preferred unprivileged Bubblewrap mode, along with relevant namespace support and adequate namespace limits. It recommends that `bwrap` not be setuid root in that mode. See the official Flatpak user-namespace requirements:

https://github.com/flatpak/flatpak/wiki/User-namespace-requirements

Flatpak's sandbox also uses kernel namespaces, bind mounts, seccomp, cgroups and D-Bus; its current architecture documentation describes these dependencies:

https://docs.flatpak.org/en/latest/under-the-hood.html

This device is on an old Samsung downstream 4.14.253 kernel. Enabling user namespaces expands kernel attack surface. A secure implementation requires evaluating the exact patch level and backported security fixes; do not treat `CONFIG_USER_NS=y` as a harmless boolean.

## 4.2 Inspect the actual 4.14 Kconfig dependencies

Use the pinned kernel's own Kconfig, defconfig and compiler. Determine the exact dependency relationships and available options in this source revision, rather than copying a current mainline config into an old downstream tree.

At minimum investigate:

- `CONFIG_NAMESPACES=y`
- `CONFIG_USER_NS=y`
- `CONFIG_UTS_NS=y`
- `CONFIG_IPC_NS=y`
- `CONFIG_PID_NS=y`
- `CONFIG_NET_NS=y` if required by the sandbox/runtime
- mount namespace support (part of the kernel namespace implementation)
- `CONFIG_SECCOMP=y`
- `CONFIG_SECCOMP_FILTER=y`
- `CONFIG_CGROUPS=y` and the resource/pid controllers required by the installed Flatpak/systemd versions
- `CONFIG_OVERLAY_FS` if the specific packaging/runtime uses it; do not enable it without verifying relevance
- required VFS, bind mount, procfs, tmpfs, devpts and filesystem options.

Do not assume every listed item is an unconditional Flatpak kernel requirement. Resolve them against the exact Fedora 43 Flatpak, Bubblewrap, systemd, portal and runtime versions that Nuxel will ship. Document the minimum set and why each option is enabled.

Check config dependency errors using the kernel's actual `olddefconfig`/config tooling. Preserve all currently working S10+ features and compare full config diffs. Do not use a random generic defconfig that silently drops Samsung display, touch, Wi-Fi, modem, camera, kbase, storage or charging support.

## 4.3 Security review for unprivileged namespaces on 4.14

Before setting the flag:

- Determine the kernel's real upstream base and vendor patch level.
- Identify security fixes already backported and missing fixes that affect user namespaces, namespace creation, mount handling, netlink, keyrings, OverlayFS, seccomp and container-related attack surfaces.
- Search the kernel source tree for user namespace CVE fix history and vendor patches; do not assume the reported version string proves patch completeness.
- Establish whether Nuxel is an effectively single-user phone, whether untrusted local applications can run, and what threat model applies.
- Keep SELinux/enforcing policy and file permissions intact.
- Set conservative but sufficient `user.max_user_namespaces` and `user.max_mnt_namespaces` limits based on actual RAM/usage. Do not set unlimited values.
- If this kernel cannot be responsibly secured for unprivileged user namespaces, report that enabling the flag is not advisable and propose the next safe kernel baseline as a separate project. Do not sacrifice security to tick the Flatpak box.

## 4.4 Build and verify the exact kernel artifact

- Use the repository's pinned `beyond2lte` kernel source/build script and current toolchain.
- Keep the current working kbase GPU support and exact display/touch configuration.
- Build with the smallest config delta, plus only dependencies proved necessary.
- Run config comparison and module/DTB dependency checks.
- Verify kernel release/version, ARM64 ELF/image type, image header, appended DTB/DTBO if applicable, load address/entry point where relevant, ramdisk packaging and boot image size.
- Verify expected kernel modules/firmware are packaged and versions match.
- Verify `CONFIG_USER_NS=y` in the final image's kernel config, not merely the source `.config` before build.
- Test user namespace creation in a controlled local environment using the exact produced kernel where possible; a host kernel test is not proof for the phone kernel.
- Produce SHA-256 hashes, build logs, config diff and image manifest.

## 4.5 TWRP transport and preparation

Owner intends to be in TWRP with USB connected. First discover what is actually visible:

- `adb devices -l` from the Mac/host;
- if empty, inspect TWRP ADB state and driver/authorization; do not assume the cable is data-capable;
- determine whether TWRP MTP exposes storage and whether the host can read/write a harmless staging file;
- confirm battery level/charging and stable USB connection;
- confirm the backup has enough free storage and the off-device copy exists.

Do not confuse TWRP MTP with ADB or the Android OS booted state. Do not use an ADB command that is unavailable in this TWRP build.

## 4.6 Exact flash approval handoff

Before flash, the agent must give the owner a concise approval manifest:

- exact device/model;
- exact image filename and SHA-256;
- kernel release/config hash;
- exact target partition and how it was verified;
- backup filename/SHA-256 and off-device location;
- TWRP action/steps;
- expected first-boot time and readiness checks;
- rollback sequence.

Wait for explicit owner approval to flash. Do not interpret the owner's general statement about being in TWRP as unlimited consent to every partition write.

## 4.7 Two-outcome boot and rollback protocol

After the owner flashes the approved kernel:

**Pass:** Nuxel reaches lockscreen/Home; Wayland/Phoc, kbase, `nuxel-wl-fb`, Bridge, web host, framebuffer/DECON, touch, Wi-Fi/SSH and required storage work. Verify no GPU fallback marker and no new kernel crash. Record a new baseline. Continue with Flatpak and remaining work.

**Fail:** Nuxel bootloops/hangs/returns to TWRP/black screens or loses critical input/display/network. Stop all further work. Use TWRP to restore the verified backup. Reboot the old kernel and verify the old working Nuxel baseline. Continue with non-kernel work only after recovery is confirmed. Do not attempt another kernel build/flash in the same unattended run.

A successful kernel boot is not a successful Flatpak feature. It simply clears the kernel capability gate for runtime testing.

---

# 5. FLATPAK — END-TO-END UNPRIVILEGED SANDBOX, PORTALS AND SOFTWARE CENTER

## 5.1 Verify kernel runtime capabilities

After the new kernel boots, capture:

- actual `/proc/config.gz`/config for namespace/seccomp/cgroup options;
- `unshare -Ur true` as the intended non-root Nuxel user;
- `unshare -Urnmipf --mount-proc ...` or equivalent supported namespace test, respecting exact utility syntax;
- namespace counts/limits;
- mount namespace creation and bind mount behavior;
- PID namespace and procfs isolation;
- seccomp filter support;
- user/group ID map creation for the user namespace;
- network namespace support if required;
- Bubblewrap behavior as non-root, without setuid bit.

Check `stat`/permissions on `/usr/bin/bwrap` and any `flatpak-bwrap`; expected preferred unprivileged mode is ordinary executable permissions (typically 0755), not setuid. Inspect `getcap` and SELinux labels too.

If `unshare -Ur true` succeeds but Bubblewrap/Flatpak fails, continue diagnosing the exact missing capability; do not call the feature ready.

## 5.2 Exact Flatpak/Bubblewrap version compatibility

The target rootfs is Fedora 43 userspace on the existing 4.14 vendor kernel. Verify exact package versions and syscall requirements. Old kernels may lack newer optional features or interfaces expected by current tools/runtimes. Pin compatible package versions only if they are supported/security-maintained. Do not freeze security updates indefinitely to keep a demo working.

Test:

- `bwrap --unshare-user --uid 0 --gid 0 ...` with valid ID maps;
- creation of mount, PID, IPC, UTS and network namespaces as required;
- proc, dev, tmpfs and read-only host bind mounts;
- seccomp profile installation;
- D-Bus socket access through approved portal/proxy only;
- Wayland socket access through explicit `--socket=wayland` permission;
- no host `/etc`, `/root`, SSH keys, authenticator secrets or unrelated home files exposed by default;
- filesystem permissions and read-only policy;
- exit/cleanup of namespaces and mounts after crash.

Never enable Flatpak with a setuid-root fallback merely because namespaces are unavailable. Flatpak documents setuid Bubblewrap as a legacy fallback with security trade-offs and reduced functionality; this mission deliberately requires unprivileged sandboxing.

## 5.3 Install the Flatpak runtime and portal stack

- Install supported Fedora ARM64 Flatpak packages from trusted configured repositories.
- Configure the intended local/system Flatpak installation scopes.
- Install AppStream metadata support and a trusted remote only after owner approval and package signature/metadata checks.
- Configure XDG Desktop Portal and the GTK portal backend for Phoc/Nuxel. Test portal activation under the real interactive user session, not from a root SSH shell.
- Configure D-Bus session services and polkit agent as needed.
- Verify file chooser, open URI, screenshot (if supported), notification, settings and document portal operations.
- Verify audio/clipboard/windowing behavior within the intended permission model.
- Test portal restart after user logout/login or Home restart.
- Keep Software/NuXTore UI state truthful: Native RPM and Flatpak have different package identities, install locations and removal semantics.

## 5.4 Real sandbox acceptance app

Install a small harmless ARM64 Flatpak test app from an owner-approved trusted source. Verify:

- app launches through its real desktop entry;
- GTK UI appears in the real Phoc session;
- Wayland display access works without X11 fallback unless explicitly permitted;
- file chooser opens through portal;
- app can read a user-approved portal-selected file;
- app cannot read a deliberately created sensitive sentinel outside its permitted sandbox (use a harmless test sentinel, not real secrets);
- app cannot read SSH keys, arbitrary `/etc` or other user's data;
- network policy is correct;
- the app and its subprocesses are in expected namespaces;
- app removal cleans up deployment and leaves user data according to explicit policy.

Capture a test matrix and evidence. Mark Flatpak done only after a real application passes.

---

# 6. PHOC LINUX-DMABUF CRASH — REPRODUCE, ROOT-CAUSE, FIX AND STRESS TEST

## 6.1 Why this is the critical WebKit gate

The owner reports that WebKit accelerated compositing cannot yet be enabled because the live Phoc `linux-dmabuf` path crashes. WebKitGTK's accelerated GTK backing store uses DMA-BUF buffers between the Web process and GTK UI process; its non-accelerated path uses shared-memory images. See WebKit's current rendering documentation:

https://docs.webkit.org/Ports/WebKitGTK%20and%20WPE%20WebKit/Graphics.html

Wayland's `zwp_linux_dmabuf_v1` protocol creates wl_buffers from DMA-BUF FDs and advertises formats/modifiers/feedback. It has explicit import failure semantics and rules for FD lifetime and coherency. See:

https://wayland.app/protocols/linux-dmabuf-v1  
https://wayland.freedesktop.org/docs/book/Architecture.html

Do not “fix” the crash by suppressing errors, disabling protocol validation or simply turning WebKit compositing on in the production session.

## 6.2 Capture reproducible crash evidence

- Record exact Phoc and wlroots versions/build IDs, protocol XML and enabled protocol versions.
- Capture Phoc stderr/journal around startup and client dmabuf connection.
- Ensure core dumps are enabled for Phoc in a bounded test environment; retrieve core and full backtrace with symbols.
- Capture kernel log/dmesg for kbase, udmabuf, DMA-BUF, IOMMU/cache/coherency/fence errors.
- Capture WebKit Web process and UI process logs separately.
- Record renderer/backend environment and which process owns each GPU/dma-buf FD.
- Identify whether the crash occurs at protocol bind, feedback setup, format/modifier advertisement, params.add, create, create_immed, attach, commit, buffer release, surface destroy or client disconnect.
- Repeat with a minimal test client, not only WebKit. If minimal client also crashes Phoc, the fault is below WebKit. If only WebKit triggers it, compare its exact allocation/format/modifier path.
- Keep a reliable software fallback active while diagnosing.

## 6.3 Inspect protocol negotiation and device semantics

Query actual `zwp_linux_dmabuf_v1` globals and versions. Determine:

- protocol version exposed by Phoc;
- whether `get_default_feedback` and `get_surface_feedback` are exposed at that version;
- main device/tranche target device values and device identity;
- format table and modifiers advertised;
- any implicit-modifier vs explicit-modifier path;
- whether the compositor advertises a DRM device even though `/dev/dri` is absent;
- whether the kbase EGL stack exposes a usable dma-buf importer/exporter extension;
- which actual format/modifier pairs kbase, udmabuf and Phoc can import/export.

Do not manufacture a DRM `dev_t` or claim a render node exists. If the protocol version does not support newer feedback requests, negotiate only the version actually supported. Do not expose protocol events unsupported by the generated server code.

## 6.4 Audit every buffer field and resource lifecycle

For every test buffer verify:

- width/height positive, bounded and consistent with client allocation;
- DRM fourcc/pixel format valid and actually supported;
- modifier exact and advertised; do not map an unknown modifier to linear;
- plane count appropriate for format;
- plane FDs valid, correctly duplicated/owned, and retained until buffer lifetime ends;
- stride and offset meet format/allocator requirements and do not overflow;
- allocation size is large enough for every plane;
- alignment and tiling modifiers match the actual kbase/udmabuf allocation;
- file descriptor not closed prematurely or reused after close;
- every object cleaned exactly once on success/failure/client disconnect;
- DMA-BUF coherency and cache synchronization are valid for all CPU/GPU access;
- implicit fences or explicit sync requirements are correctly handled. Do not assume the presence of a DMA-BUF FD proves producer completion or coherency.

Use ASan/UBSan where feasible in a test build, but recognize that kernel/GPU driver faults may not be instrumented. Use valgrind only where practical; do not use tools that alter timing so much that the only reproduction disappears without recording that caveat.

## 6.5 Fix importer and protocol error handling

- An unsupported format/modifier must be rejected cleanly before the compositor enters an invalid import path.
- `create` import failure must use the protocol's failed event rather than killing Phoc.
- `create_immed` failure must use the correct protocol error semantics and not dereference invalid state.
- If import fails later after the wl_buffer was successfully created (e.g. device disappears/driver failure), handle it as an implementation failure without incorrectly raising a client protocol error; the protocol specification explicitly distinguishes this case.
- Do not crash, abort or use-after-free when clients disconnect during an in-flight import.
- Do not hold server/global locks while blocking on GPU driver calls or waiting for fences.
- Do not attempt a CPU mapping of a GPU-only/non-mappable tiled buffer without proving it is mappable and synchronized.
- Add bounded timeout and safe resource cleanup for hung imports.
- If Phoc/wlroots is too old or has a known bug, identify the minimal safe upstream/backport patch compatible with the current runtime and kernel. Do not blindly upgrade Phoc/wlroots across incompatible Wayland protocols or replace the working compositor stack wholesale.

## 6.6 DMA-BUF and udmabuf experiment matrix

Test each candidate separately:

1. vendor kbase-allocated exportable buffer, if the vendor API supports export;
2. `/dev/udmabuf`-created buffer with verified alignment and coherency;
3. any available DMA-BUF heap allocator (only if actually installed and compatible);
4. Mesa/kbase EGL `EGL_EXT_image_dma_buf_import` path if exposed;
5. Mesa/kbase EGL Wayland WSI path, but only after the Phoc importer works;
6. WebKitGTK accelerated backing store after all earlier tests pass.

For each route record:

- allocator/export API;
- buffer format and modifier;
- physical device and `dev_t` where valid;
- FD ownership;
- EGL extensions;
- importer path;
- synchronization strategy;
- CPU fallback availability;
- test client result;
- Phoc stability and dmesg output.

Do not assume `udmabuf` is zero-copy to Mali or display-compatible. A buffer may be CPU-mappable and still not be a valid scanout or EGL texture source.

## 6.7 Regression tests for Phoc stability

Create a dedicated dmabuf test suite that covers:

- valid supported buffer import;
- unsupported fourcc;
- unsupported modifier;
- invalid dimensions;
- invalid plane count;
- invalid stride/offset;
- duplicate FD/close ordering;
- client closes before create response;
- client destroys buffer immediately after attach;
- surface destroyed during import;
- importer temporarily fails;
- allocator/FD exhaustion;
- repeated creation/destruction (thousands of cycles);
- multiple surfaces and app switching;
- GPU context loss/reset if safely reproducible;
- WebKit process crash/restart;
- compositor restart and fallback.

The test must confirm that a bad client buffer cannot take down Phoc or leave the display bridge with stale frames. Use an isolated test session first. Only then test on the daily session.

## 6.8 WebKitGTK acceleration gate

WebKit documentation states that GTK accelerated mode uses DMA-BUF buffers for its accelerated backing store while the non-accelerated mode exchanges shared-memory images. Enable accelerated mode only when:

- the selected EGL implementation initializes in the actual WebKit Web process;
- GTK UI process can import the exported DMA-BUF;
- Phoc safely handles the relevant Wayland buffers/protocol path;
- the renderer is genuinely Mali/kbase, not llvmpipe/software masquerading as EGL success;
- repeated WebKit frame creation, damage updates, resizing, navigation and surface teardown work;
- screenshots from the display bridge remain correct;
- no Phoc crash or kbase error occurs under sustained stress.

Use runtime feature flags per user session, not global systemwide environment variables that make unrelated apps fail. Preserve the current fallback switch and known-good shared-memory path.

Test WebKit with:

- a static HTML page;
- CSS transforms/opacity/animations;
- Canvas 2D;
- WebGL only if actual supported GL/GLES capability is proved;
- image decode/scroll;
- video playback if the codec path is available;
- app drawer and Home PWAs;
- lockscreen animations/clock;
- repeated app open/close and backgrounding;
- device suspend/resume and compositor restart.

Record renderer strings, EGL vendor/renderer, WebKit accelerated backing-store state, protocol activity and process CPU. Do not treat `GDK_GL=...` or the mere presence of `/dev/mali0` as proof.

## 6.9 Feature rollout and rollback

- Default remains the last known-good software path until the crash fix passes.
- Add a safe config switch, e.g. `webkit_accelerated_backing_store=disabled|testing|enabled` with safe default `disabled` in the release image until acceptance.
- If accelerated WebKit crashes or fails health checks after enablement, set it back to disabled and restart only the web process/session component as appropriate; do not restart Phoc unnecessarily.
- Keep old libraries and environment in a versioned rollback location. Do not overwrite the known-good Mesa/EGL backup.

---

# 7. MACOS MTP AND USB FILE-TRANSFER EXPECTATIONS

## 7.1 Clarify the platform limitation

The owner reports MTP now enumerates from the Nuxel phone but does not appear as a Finder-mounted drive. macOS Finder does not natively mount MTP devices as ordinary volumes. This is not necessarily a device-side enumeration bug. The supported workflow is an MTP client such as OpenMTP or MTPLX.

Do not attempt to fix Finder by changing MTP USB descriptors until the device protocol is proven wrong. Do not enable mass-storage mode to satisfy Finder: the current kernel does not compile the required mass-storage gadget function, and exporting a live mounted filesystem as raw block storage is unsafe.

## 7.2 Test OpenMTP/MTPLX workflow

- Confirm device exposes an MTP interface on macOS.
- Provide the owner with an accurate UI/help hint: “On macOS use OpenMTP/MTPLX; Finder does not mount MTP devices directly.”
- Verify OpenMTP/MTPLX sees the Nuxel device and allowed folders.
- Test phone → Mac and Mac → phone transfer using a harmless test file with SHA-256 before/after.
- Confirm allowed folder permissions, filename encoding, Unicode, large files, disconnect recovery and storage refresh.
- Test microSD (if mounted) and phone internal storage only through explicitly exported safe roots.
- Do not expose rootfs, `/etc`, `/var`, SSH secrets, app-private credentials or the entire live root/home tree.
- Ensure a transfer in progress is not left partially committed; use temp file + atomic rename where possible.

## 7.3 Optional Finder-compatible alternatives

If the owner wants actual Finder sidebar/volume integration, investigate a separate file-service protocol rather than MTP:

- SMB share over Wi-Fi (standard Finder compatibility) using a dedicated restricted Nuxel share user and only explicit media/download/shared folders;
- WebDAV or SFTP as alternative Finder/third-party file client paths;
- USB network share only if the exact S10+ gadget kernel safely supports ECM/RNDIS and the USB function can coexist with required console/MTP behavior.

Do not use the known unsafe NCM teardown path. Do not assume RNDIS/ECM is present. Probe actual `CONFIG_USB_CONFIGFS_F_ECM`, `CONFIG_USB_CONFIGFS_F_RNDIS`, relevant modules, UDC and composite gadget owner before considering it. Keep Wi-Fi/SSH and serial console recovery intact.

If none of the USB networking functions can be safely used, label USB Finder-compatible sharing unavailable and recommend OpenMTP/MTPLX over MTP; do not fake a Finder mount.

---

# 8. MOBILE NETWORK, CAMERA, NFC AND SENSORS — RECHECK, REPAIR ONLY REAL USERSpace GAPS

These capabilities remain at previously documented driver/firmware blockers. The mission must not ignore them, but it must also not pretend this kernel flag or GPU work will solve them.

For each subsystem:

1. Re-run its canonical Nuxel diagnostic and capture raw evidence.
2. Identify current device node, driver binding, kernel config, firmware load, service owner and userspace API.
3. Distinguish `NOT_PRESENT`, `DRIVER_MISSING`, `FIRMWARE_MISSING`, `SERVICE_MISSING`, `PERMISSION_DENIED`, `PARTIAL` and `PHYSICAL_TEST_REQUIRED`.
4. Fix service/config/package/API problems when the driver already works.
5. Do not fetch random firmware, copy undocumented Android HAL blobs, write arbitrary registers or use vendor binaries with unclear license/provenance.
6. Do not modify modem/NV/EFS data or flash unrelated partitions.
7. If hardware requires new kernel driver/firmware, report the exact source/firmware/license dependency and leave the UI in a truthful blocked state.
8. Test physically only when it is safe and the hardware is known to be functional.

## 8.1 Mobile network

Check modem enumeration, USB/PCIe/platform link, kernel driver, firmware, modem manager/QMI/MBIM/RIL compatibility and SIM/eSIM state. Do not call service registered merely because the modem node exists. If X9 modem firmware/driver remains unavailable, preserve existing no-network status.

## 8.2 Camera

Check sensor enumeration, CSI/ISP path, camera driver/media graph, firmware and userspace capture API. A `/dev/video*` node alone is not proof. Keep camera app disabled/truthful if stream cannot be acquired.

## 8.3 NFC

Run existing S3FWRN5/sec-nfc diagnostics and physical tag test. An I2C address or kernel log is not proof. Do not claim NFC on until a real tag is read and the provider correctly toggles.

## 8.4 Sensors

Check SSP sensor hub and LSM6DSO accelerometer/gyro path. Verify changing real gravity readings, units, scale, mount matrix and event timing. Keep auto-rotation blocked if it uses zeros, stale readings or manual fixtures.

---

# 9. BOOT PERFORMANCE — MEASURE THE ACTUAL CRITICAL PATH

## 9.1 Baseline and instrumentation

Use systemd tools and kernel/init logs. `systemd-analyze time` reports kernel/initrd/userspace startup timing; `critical-chain` identifies dependencies; `blame` is useful but can mislead because it reports activation duration and not every wait/job queue or hardware latency. See:

https://www.freedesktop.org/software/systemd/man/261/systemd-analyze.html

Collect:

```sh
systemd-analyze time
systemd-analyze critical-chain
systemd-analyze blame
systemd-analyze plot > /run/nuxel/boot-before.svg
journalctl -b -o short-monotonic
systemctl --failed
```

Run from the actual handset and keep the results. Separate:

- bootloader/firmware time (only what can be observed);
- kernel decompression/startup;
- initramfs time;
- systemd userspace activation;
- critical display/Wayland/Phoc readiness;
- first compositor frame;
- Home/WebKit first interactive time;
- deferred background readiness.

Do not call the time until `multi-user.target` “phone ready” if Home is not interactive yet. Add explicit readiness markers to Nuxel's real user-facing components where useful.

## 9.2 Find blockers, not hide them

Inspect:

- long `ExecStartPre` scripts and fixed `sleep` statements;
- serial/network dependency waits;
- mount/fstab timeouts for missing/optional devices;
- firmware loading delays;
- repeated retry loops;
- service dependency cycles;
- `network-online.target` dependencies that do not need to block Home;
- metrics or diagnostics running synchronously on the critical path;
- web server/Bridge readiness ordering;
- WebKit cache initialization and asset preload;
- GPU/EGL probing during startup;
- journal/log I/O and filesystem fsync delays.

Do not simply disable services. Classify each as critical (display/input/Bridge) or deferred (optional telemetry, package metadata, media scans, NFC, sensor diagnostics, update checks). Start noncritical work after Home is interactive and make it cancellable/bounded.

## 9.3 Optimize safely

- Remove unnecessary fixed sleeps; replace with event/socket readiness where possible.
- Avoid waiting for a disabled hardware subsystem before Home appears.
- Use systemd dependencies that reflect actual required ordering.
- Use asynchronous startup and stale response cancellation in Bridge/UI.
- Defer media thumbnails, app catalog scans and noncritical metrics.
- Preserve display-owner and kbase initialization ordering; do not parallelize mutually exclusive hardware ownership.
- Keep service restart policies bounded so a failing sensor/camera does not cause boot storms.
- Do not hide errors to shave time.

## 9.4 Boot acceptance

Run at least five cold boots and five warm/restart boots where feasible. Compare median and p95 to baseline. Record first visible frame, lockscreen ready, Home interactive, Bridge ready and key device services. Set realistic targets based on hardware; aim to reduce measured user-visible boot time by at least 20% without reducing functionality or increasing boot failure rate. If a blocker is firmware/bootloader bound, report separately.

---

# 10. APP DRAWER PERFORMANCE AND GESTURE CORRECTNESS AFTER GPU/WEBKIT WORK

Do not start app drawer optimization until WebKit's graphics mode has been established and stable. First measure with the stable path (whether accelerated or fallback), then optimize the actual costs.

## 10.1 Profile the drawer

Measure:

- swipe gesture start → drawer first visible frame;
- drawer animation duration and dropped frames;
- icon/image ready time;
- scroll frame time and long tasks;
- CPU/memory and texture/buffer allocations;
- Bridge calls and JSON registry parsing;
- layout/reflow and image decode activity.

Test realistic installed app counts (current set, 50, 100, and 250 synthetic entries if needed) and real icon assets.

## 10.2 Fix swipe-down immediately scrolling the drawer

The user reports that swiping down to open the app drawer also causes the newly opened drawer to start scrolling. Diagnose gesture ownership and event timing:

- identify whether the same pointer sequence is used both for Home swipe detection and the drawer's internal scroll container;
- inspect pointerdown/move/up/cancel timing, pointer capture and scroll offset initialization;
- ensure the opening gesture is consumed by the Home/root gesture recognizer and is not replayed into the drawer scroller;
- only after opening completes should a new pointer sequence scroll the drawer;
- preserve touch momentum for subsequent scrolls.

Use a clear state machine (`IDLE → OPENING_GESTURE → DRAWER_OPEN → DRAWER_SCROLL`) and ignore scroll deltas from the opening gesture. Do not globally set `touch-action:none` on the entire UI.

## 10.3 Fix scroll-versus-tap app launching

The user reports that scrolling the app drawer or Home desktop starts apps accidentally. Implement robust movement/intent discrimination:

- record pointer ID, pointer type, origin and timestamp;
- defer activation until a valid pointerup/tap that stayed within movement slop;
- cancel launch when movement exceeds configured slop (tune using real touch; start around 8–12 CSS px and measure);
- handle pointercancel/lostpointercapture;
- ignore secondary pointer events;
- distinguish vertical scroll, horizontal page swipe, long-press and tap;
- only launch on deliberate tap, not pointerdown/click generated after scroll;
- prevent synthetic click after drag or scroll;
- ensure nested scroll containers do not both process same gesture;
- preserve keyboard/assistive technology activation with semantic buttons/links and correct click behavior.

Apply the same intent logic to desktop app icons, folders, widgets and drawer items without breaking icon rearrangement and long-press editing.

## 10.4 Rendering optimization

- Avoid full `innerHTML` replacement on every drawer open/scroll/selection change.
- Cache app registry parsing and icon metadata; invalidate only on registry changes.
- Lazy-load images outside viewport and bound image decode concurrency.
- Use `DocumentFragment` or progressive chunks for large app lists.
- Virtualize only if measurements justify it, and preserve scroll position/focus/stable keys.
- Use transform/opacity for short transitions; avoid expensive blur/backdrop filters, giant shadows and continuous idle animations on Pixman/software fallback.
- On accelerated WebKit, avoid texture churn and needless giant composited layers; GPU memory is still limited.
- Stop timers and image work when the drawer is closed.
- Preserve app order, folders, hidden-app state and home-screen drag behavior.

## 10.5 Acceptance

- Swiping down opens drawer without jumping its scroll position.
- Scrolling never launches apps.
- A deliberate tap launches exactly one app.
- Horizontal Home page swipe does not launch apps.
- Long-press/edit mode still works.
- Drawer open latency and scroll p95 improve measurably without regressions.

---

# 11. NORMAL REBOOT — REMOVE LONG BLACK SCREEN BEFORE ACTUAL RESTART

## 11.1 Reproduce and measure

The user reports that a normal reboot spends a long time on a black screen before the phone actually reboots. Do not assume the black screen itself means the system is hung. Measure each stage with monotonic time markers:

1. reboot request accepted;
2. Nuxel power/reboot manager begins shutdown;
3. user sessions/clients stop;
4. WebKit/PWA host/Bridge stop;
5. Phoc/Wayland stop or display handoff begins;
6. `nuxel-wl-fb` releases `/dev/fb0` and DECON/panel state;
7. remaining systemd units stop;
8. sync and unmount phase;
9. systemd-shutdown executes final reboot syscall;
10. hardware actually resets/bootloader starts.

Capture journal with monotonic timestamps, systemd stop jobs, kernel logs and unit status. If the final journal cannot be persisted, add a small persistent shutdown trace with bounded atomic writes (never write sensitive data).

## 11.2 Find the blocking unit

Inspect:

- `systemctl list-jobs` during shutdown if observable;
- stop-timeout messages in journal;
- unit `TimeoutStopSec`, `ExecStop`, `ExecStopPost`, `KillMode`, `SendSIGKILL`, `FinalKillSignal`;
- services waiting for network, USB, Wayland, a Bridge RPC or a hardware sysfs node;
- socket activation and lingering workers;
- WebKit web process shutdown or GPU buffer releases;
- Phoc clients that never destroy surfaces/buffers;
- `nuxel-wl-fb` waiting on screencopy callbacks or a frame fence;
- metrics/diagnostic services flushing sockets forever;
- mount units or network filesystems;
- any service with `TimeoutStopSec=infinity` or an overly long custom timeout.

Do not rely on `systemd-analyze blame` for shutdown. Use logs and job timing. systemd unit stop timeouts govern how long a service may be allowed to stop before it is terminated; fix the offending unit rather than globally reducing every timeout. See systemd service documentation:

https://www.freedesktop.org/software/systemd/man/261/systemd.service.html

## 11.3 Correct shutdown ordering

Define an explicit, deterministic sequence for display stack shutdown:

- stop accepting new UI/app work;
- close/cancel pending WebKit/Bridge tasks with bounded waits;
- stop the web host/clients cleanly;
- stop Phoc/Wayland only after clients have stopped;
- stop `nuxel-wl-fb` after the compositor has released screencopy and after it can safely release the framebuffer/panel owner lock;
- stop telemetry/optional workers with short, appropriate timeouts;
- complete filesystem sync/unmount and systemd final reboot.

The exact order must be based on the actual unit graph. Do not invent ordering that breaks `nuxel-wl-fb`/Phoc dependencies. Keep display visible until the appropriate final handoff where practical, but never keep the system in a long black state merely because the display has been blanked before a slow unit stop.

## 11.4 Safety of forced termination

- Do not kill random process IDs or indiscriminately `pkill -9` the graphical stack.
- Give each service an explicit clean shutdown request and a bounded timeout.
- If a hung client must be terminated after timeout, terminate only the unit's cgroup or owned process tree according to systemd semantics.
- Do not remove global stop timeout safeguards or set all units to 1 second.
- Preserve filesystem sync and unmount correctness. A shorter black screen is not worth filesystem corruption.

## 11.5 Reboot acceptance

Run at least five ordinary reboots after fixing. Record from user request to actual reboot start, and black-screen duration separately. Ensure all boots return to healthy Nuxel. Target a material reduction in the measured black-screen interval; do not promise an arbitrary duration if a real kernel/bootloader delay dominates. No data loss, no stuck services and no user-facing reboot success toast before the restart has been accepted.

---

# 12. PERFORMANCE METRICS AND `nuxel-metricsd`

The active rootfs builder already compiles/installs `nuxel-metricsd` and its socket. Reuse that infrastructure; do not create another daemon.

Add or verify measurements for:

- compositor renderer/backend and GPU renderer string;
- GPU context presence and kbase activity where safe;
- WebKit accelerated backing-store enabled/fallback state;
- WebKit Web/UI process CPU/memory;
- DMA-BUF allocation/import success/failure counters (bounded, no FD leaks);
- Phoc crashes/restarts and Wayland protocol errors;
- `nuxel-wl-fb` capture/copy/present timing and `decon_pan_failed`;
- first frame, Home-ready and drawer-ready timestamps;
- app drawer input-to-frame latency, scroll frame time and long tasks;
- service boot/readiness/stop times;
- reboot request-to-reset phases.

Avoid high-frequency polling that itself causes lag. Prefer event/counter updates and short diagnostic sampling windows. Expose metrics in Settings/Developer or diagnostics, not a permanent high-cost overlay.

---

# 13. UI/SETTINGS STATUS AND OPERATOR EXPERIENCE

Add or update honest Settings status cards for:

### Flatpak / Sandbox
- Kernel `CONFIG_USER_NS` state (from actual running kernel config, not build source only).
- Runtime unprivileged user namespace test.
- Bubblewrap mode and setuid bit state.
- Namespace limits.
- Seccomp support.
- Portal service/GTK backend status.
- Last real sandbox app test.
- Supported / blocked reason.

### Graphics / WebKit
- Phoc renderer and kbase context.
- WebKit GTK accelerated backing store state.
- EGL vendor/renderer and relevant extensions.
- Linux DMA-BUF protocol version and supported formats/modifiers.
- Last Phoc dmabuf import test and crash count.
- `nuxel-wl-fb` backend, frames, copy/present time and DECON pan failures.
- Current fallback mode and whether acceleration is safe to enable.

### USB / macOS file transfer
- MTP endpoint state, connected host and export roots.
- macOS help: MTP does not appear as a Finder-mounted volume; use OpenMTP/MTPLX.
- Optional Finder-compatible share state only if SMB/WebDAV path is really configured.

### Device capabilities
- Mobile network, camera, NFC and sensor state using the existing canonical diagnostics/provider. Display blockers with specific stage names and last-tested timestamps.

Never report `supported` simply because a package/config exists. Use `UNKNOWN`, `BLOCKED_KERNEL`, `BLOCKED_FIRMWARE`, `NOT_INSTALLED`, `UNAVAILABLE`, `READY`, `ACTIVE` with semantics documented consistently.

---

# 14. TEST PLAN AND REQUIRED REGRESSION COVERAGE

## 14.1 Kernel / recovery tests

- Source config contains required namespaces and seccomp features.
- Final built kernel config confirms them.
- Image hash and package manifest match.
- TWRP can access verified pre-flash backup and new image.
- First boot success test includes display, kbase, touch, Wi-Fi/SSH and services.
- Failure branch restores old boot image and verifies old system.
- No unrelated partition changed.

## 14.2 Flatpak tests

- user namespace creation by non-root user;
- user/mount/PID/IPC/UTS/network namespace behavior required by Bubblewrap;
- mount/bind/proc/tmpfs behavior;
- seccomp filter;
- non-setuid Bubblewrap;
- portal activation and file chooser;
- Wayland window rendering;
- audio and clipboard where supported;
- sandbox isolation sentinel test;
- no access to arbitrary SSH keys, `/etc` or private user data;
- Flatpak app install/update/remove and crash cleanup;
- no regression to native RPM software installation.

## 14.3 DMA-BUF/Phoc tests

- valid/invalid format/modifier/plane import;
- FD lifetime and close behavior;
- unsupported buffer rejected without server crash;
- import failure returns correct protocol semantics;
- client disconnect and surface destruction cleanup;
- repeated allocation/import/release cycles;
- no Phoc crash or memory/FD leak;
- display continues with shared-memory fallback;
- compositor restart and recovery.

## 14.4 WebKit tests

- EGL initialization under actual web process;
- accelerated backing store reports active only when actual DMA-BUF path succeeds;
- static page, CSS animation, image decode, canvas, scrolling, app drawer, lockscreen, navigation, app switch, resize and stress;
- renderer string and CPU evidence;
- repeated start/stop without Phoc crash;
- software fallback still works after acceleration is disabled.

## 14.5 MTP/macOS tests

- MTP enumeration on Mac;
- OpenMTP/MTPLX connection;
- bidirectional file transfer with SHA-256;
- large file, unicode names, microSD, disconnect during transfer;
- allowed-root security and no rootfs exposure;
- no USB mass-storage function.

## 14.6 Performance tests

- at least five boots before/after;
- at least five ordinary reboot/shutdown cycles after fix;
- app drawer launch and scroll with realistic registry sizes;
- lockscreen first paint and idle behavior;
- CPU/memory/long-task/frame-time comparison;
- no regression when WebKit acceleration feature flag is disabled.

---

# 15. EXECUTION ORDER — DO NOT MIX ALL RISKS AT ONCE

1. **Baseline and recovery:** collect source/live state, confirm owner-reported state, TWRP transport and valid backup. No modifications yet.
2. **Kernel security review:** inspect 4.14.253 source/Kconfig/security patch status and exact Flatpak requirements. Decide whether safe `CONFIG_USER_NS=y` is viable.
3. **Kernel build:** make the minimal config delta, build the exact S10+ image, verify hash/config/DTB/package.
4. **TWRP approval and flash:** show manifest, wait for explicit approval, flash exact target. Apply the two-outcome boot agreement. If failure, roll back and stop kernel experiments.
5. **Flatpak runtime:** after successful boot only, test unprivileged namespaces, bwrap, seccomp, portals and a real ARM64 app. Do not proceed to software center “supported” labels until the real app works.
6. **Phoc DMA-BUF crash:** gather crash evidence and reproduce with minimal client; fix importer/protocol/lifetime/coherency/feedback; repeated stress; preserve fallback.
7. **WebKitGTK:** test EGL and accelerated backing store behind a feature flag, repeated stability, actual renderer verification, fallback rollback.
8. **MTP/macOS:** document OpenMTP/MTPLX, validate transfers, optionally assess SMB/WebDAV Finder path without unsafe USB functions.
9. **Device capability audit:** recheck mobile network, camera, NFC and sensors; fix userspace only if supported; preserve honest blockers.
10. **Boot optimization:** profile and remove unnecessary critical-path waits; preserve hardware ordering.
11. **App drawer optimization:** fix gesture/tap/scroll ownership and rendering costs with before/after tests.
12. **Normal reboot black-screen fix:** trace systemd shutdown jobs and display handoff; fix only blocking units; test repeated restarts.
13. **Release integration:** image build, package/units/config, Settings status, tests, documentation, evidence and rollback.

---

# 16. RELEASE / ROOTFS / SOURCE-OF-TRUTH REQUIREMENTS

- Update the actual S10+ rootfs builder, not only a developer workstation.
- Kernel config fragment and exact kernel source commit must be pinned/reproducible.
- All Flatpak packages/portals and Bubblewrap setup must be installed from the verified build manifest.
- All Phoc/wlroots patches and generated protocol code must be built from source and versioned.
- Preserve current kbase vendor libraries and known-good EGL backup; candidate Mesa libraries must install side-by-side or be versioned for atomic rollback.
- WebKit flags/env must be applied to the actual `nuxel-web` service/process, not a developer terminal.
- Runtime feature flag defaults to safe software backing store until explicit validation.
- Update systemd units for Flatpak portal, metrics, graphics status, boot/shutdown services as needed; verify with `systemd-analyze verify`.
- Do not copy stale systemd unit overrides into the image unintentionally.
- Add build checks that every binary/helper/config/portal backend exists and has correct architecture/permissions.
- Preserve the user's installed apps, profile, authenticator vault, downloads, media and notes.
- Use a clean staging deployment and atomic file replacement where appropriate.

---

# 17. REQUIRED DELIVERABLES

1. `docs/beta-finalization/live/PWNAGE-51000-TODO.md` — tasks, owners, dependencies, statuses and evidence.
2. `docs/beta-finalization/live/evidence/pwnage-51000/` with all baseline/kernel/TWRP/Flatpak/dmabuf/WebKit/MTP/performance/shutdown/deployment artifacts.
3. Minimal kernel config diff and security review; built image manifest and SHA-256.
4. TWRP backup verification and flash/rollback record.
5. Flatpak/Bubblewrap/portal capability matrix and actual app test record.
6. Phoc dmabuf crash root-cause report, fix patch, test client and stress-test results.
7. WebKitGTK accelerated rendering enable/disable decision and performance data.
8. macOS MTP help and verified OpenMTP/MTPLX copy results; Finder limitation clearly documented.
9. Mobile network/camera/NFC/sensor current capability report.
10. Boot/app drawer/shutdown before/after performance report.
11. Rootfs build/test logs, service/unit verification, cache/version updates.
12. Exact deployment and rollback steps.
13. Final report separating PASS, PARTIAL, BLOCKED_KERNEL, BLOCKED_FIRMWARE, NEEDS_OWNER_TEST and NOT_SUPPORTED.

Never include private keys, credentials, TOTP seeds, auth tokens or personal data in the evidence archive.

---

# 18. FINAL DEFINITION OF DONE

## Kernel / TWRP

- [ ] Exact current boot image backup is verified and copied off-device.
- [ ] The kernel image has a minimal, reviewed `CONFIG_USER_NS=y` change and all required namespace/security features.
- [ ] The owner approves the exact image/hash/partition before flash.
- [ ] New kernel reaches healthy Nuxel with GPU, display, touch, Wi-Fi/SSH and services intact; otherwise verified rollback restores known-good system and kernel work stops.

## Flatpak

- [ ] Unprivileged namespaces work as the real Nuxel user.
- [ ] Bubblewrap is not setuid root.
- [ ] Required namespace, mount and seccomp behavior passes.
- [ ] Portals work in Phoc/Wayland session.
- [ ] A real ARM64 Flatpak app launches and passes sandbox isolation tests.
- [ ] No sandbox bypass, broad permission or unsafe setuid fallback was used.

## DMA-BUF / WebKit

- [ ] Phoc dmabuf crash has a demonstrated root cause and source fix.
- [ ] Invalid/unsupported import does not crash Phoc.
- [ ] FD lifetime, modifiers, planes, coherency and sync are tested.
- [ ] Repeated test-client stress produces no crash/leak.
- [ ] WebKit accelerated backing store works with actual GPU/EGL/DMA-BUF evidence, or remains safely disabled with precise limitation.
- [ ] Existing Phoc kbase acceleration and fbdev/DECON path are preserved.

## USB / hardware

- [ ] macOS MTP workflow succeeds with OpenMTP/MTPLX and hash-verified copies.
- [ ] Finder limitation is documented; no unsafe mass-storage export.
- [ ] Optional SMB/WebDAV Finder path is implemented only if genuinely supported and secure.
- [ ] Mobile network, camera, NFC and sensors have fresh evidence-backed states and no fake green results.

## Performance and stability

- [ ] Boot critical path and first interactive frame improve measurably without hardware readiness regressions.
- [ ] App drawer opens without accidental initial scroll.
- [ ] Scrolling the drawer never launches an app; deliberate tap launches exactly once.
- [ ] App drawer scroll and lockscreen are measurably more responsive.
- [ ] Normal reboot no longer spends an unexplained excessive interval on a black screen; shutdown blocker is identified and fixed with bounded unit-specific behavior.
- [ ] Repeated reboot tests pass without data loss or service hang.

## Delivery

- [ ] Changes are reproducible from source and clean rootfs build.
- [ ] Tests and exact PASS/FAIL/SKIP counts recorded.
- [ ] Kernel/TWRP and runtime rollback instructions complete.
- [ ] User data, SSH/USB recovery and known-good GPU path preserved.
- [ ] Unsupported features reported honestly; no claim based on a config flag alone.

**PWNAGE-51000 is complete only when the kernel, actual Flatpak sandbox, Phoc DMA-BUF path, WebKitGTK, MTP workflow and performance changes are each proven at their real layer. A successful kernel boot is permission to continue, not proof that Flatpak works. An advertised Wayland protocol is not proof of safe DMA-BUF import. And a shorter black screen is not success if filesystem shutdown is unsafe.**

🐧 **NUXEL — SECURE SANDBOX. STABLE GPU. FASTER BOOT. NO REGRESSIONS.**
