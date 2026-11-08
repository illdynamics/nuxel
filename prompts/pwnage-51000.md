# PWNAGE-51000 — NUXEL FINAL BLOCKERS, FLATPAK KERNEL SUPPORT, WEBKIT DMA-BUF STABILITY, MTP/macOS, BOOT & UI PERFORMANCE

**Target:** Samsung Galaxy S10+ SM-G975F / `beyond2lte` / Exynos 9820  
**OS:** Nuxel, custom Fedora-based ARM64 Linux  
**Current graphics:** vendor Mali-G76 kbase GPU path, Phoc GPU context active, `nuxel-wl-fb` single `/dev/fb0` owner, DECON presentation confirmed  
**Current kernel:** Samsung downstream 4.14.253 unless live verification proves otherwise  
**Recovery state:** Owner intends to begin with the handset in TWRP and USB connected, ready for an explicitly approved kernel flash  
**Mission:** resolve the remaining support blockers safely, preserve the working GPU/display baseline, then optimize boot, shutdown/reboot and the app drawer.

## 0. MISSION DIRECTIVE

Implement the remaining items in the real Nuxel repository and deployed S10+ image. Do not report a feature as fixed merely because a config flag, package, menu option or status file exists. Every result must be backed by runtime evidence and, where relevant, a physical-device test.

Latest owner-provided state to treat as the starting hypothesis and re-verify:

- `phoc` holds 3× `/dev/mali0`, 1× `/dev/udmabuf` and an `anon_inode:dmabuf_udmabuf`.
- kbase debugfs shows a GPU context owned by `phoc`.
- `nuxel-wayland`, `nuxel-wl-fb` and `nuxel-web` are active.
- Bridge reports `FRAMES_OK`; `decon_pan_failed=0`.
- `/run/nuxel-gpu-fallback` is absent.
- `/dev/fb0` is restored; panel is 1440×3040 with virtual geometry 1440×6080.
- `/dev/dri` is absent, as expected for the current vendor kbase path.
- Phoc GPU acceleration works. WebKitGTK/GTK GL still falls back to software because GTK GL initialization fails; an attempted Mesa Wayland build failed and was reverted.
- The final screencopy → `/dev/fb0` copy/upscale still consumes CPU.
- Kernel has `CONFIG_USER_NS=n`; Flatpak is blocked.
- USB MTP enumerates, but macOS Finder does not mount MTP. Use OpenMTP/MTPLX; mass-storage is not compiled into the kernel.
- Mobile network, camera, NFC and sensor services remain at their existing honest driver/firmware blockers.
- WebKit acceleration must remain disabled until the live Phoc `linux-dmabuf` crash is understood and fixed.
- TWRP backups are under `/var/backups/nuxel/kbase-gpu-*`; the pre-Wayland-test EGL backup is `/var/backups/nuxel/libEGL_mesa.so.0.0.0.pre-wayland`.
- `boot-original.img` in the repository is a dummy and MUST NOT be treated as a valid recovery image.

## 1. TWRP / KERNEL FLASH AGREEMENT — EXPLICIT TWO-OUTCOME GATE

The owner intends to start with the phone in TWRP, connected by USB, ready for a kernel reflash. Before flashing:

1. Confirm the exact phone model/variant and current partition layout. Do not assume a partition name, A/B slot, image format or TWRP interface.
2. Establish the actual TWRP transport (`adb devices`, TWRP ADB, TWRP MTP or another verified path). An empty `adb devices` is a blocker to ADB-based commands, not permission to guess another device.
3. Make a fresh TWRP backup of the exact currently working boot/kernel partition(s) required to restore the current Nuxel kernel. Verify backup size, checksum, readable contents and copy it off-device to the Mac/host. The old `boot-original.img` is not valid evidence.
4. Identify the exact kernel image produced by the pinned Nuxel kernel source/build. Verify architecture, image format, DTB/DTBO packaging, kernel release, config, build ID and SHA-256. Confirm the image contains the currently required display, touch, storage, Wi-Fi and kbase components plus the planned user-namespace changes.
5. Review `CONFIG_USER_NS=y` and every required namespace/seccomp/cgroup prerequisite. Do not assume changing one flag is sufficient. Review the security implications of enabling unprivileged user namespaces on the old 4.14.253 kernel and its patch level.
6. Present the exact image, exact target partition and exact rollback steps to the owner. Flash only the confirmed kernel/boot target using the verified TWRP workflow. No unrelated partitions.
7. Reboot once to Nuxel and observe the complete boot. **If Nuxel reaches the expected login/Home state, display stack, touch, Wi-Fi/SSH and services all work, record PASS and continue with the remaining tasks. If it bootloops, hangs, returns to TWRP, loses display/touch/network, or fails the readiness deadline, stop all further changes and restore the verified pre-flash backup from TWRP.** After successful restoration, verify the original Nuxel boot before continuing with non-kernel work. Never keep retrying an unbootable image.
8. Do not automate repeated flash/reboot cycles. The owner must explicitly authorize the first flash and any later flash attempt.

## 2. FLATPAK — ENABLE SECURE USER NAMESPACES, NOT A SETUID SHORTCUT

- Update the pinned kernel config to `CONFIG_USER_NS=y` only after reviewing the exact 4.14 source and dependent options. Ensure required namespace features (UTS, IPC, PID, mount, network as appropriate), seccomp/filter, cgroups and filesystem support required by the shipped Flatpak/Bubblewrap versions are present.
- Check runtime limits such as `/proc/sys/user/max_user_namespaces` and `/proc/sys/user/max_mnt_namespaces`; handle `kernel.unprivileged_userns_clone` only if this vendor kernel actually has the patched sysctl.
- Use unprivileged Bubblewrap (`0755`, not setuid root) as the preferred model. Do not make `bwrap` setuid root to make Flatpak appear to work. Do not disable sandboxing, grant host-wide filesystem/device access, or weaken SELinux.
- Test the exact Fedora 43 Flatpak/Bubblewrap versions against the new 4.14 kernel: create user/mount/PID/network namespaces; run `bwrap --unshare-*`; install and launch a harmless ARM64 test Flatpak; test portals, Wayland socket, D-Bus, audio, file chooser, app updates and sandbox denial of forbidden host paths.
- If current Flatpak/Bubblewrap requires kernel features absent from 4.14, document the exact missing feature and do not report Flatpak supported merely because `unshare -Ur true` works.

## 3. WEBKITGTK / PHOC LINUX-DMABUF CRASH — FIX BEFORE ENABLING ACCELERATION

- Preserve the working Phoc kbase GPU path. Keep WebKit accelerated compositing disabled by default until the crash is reproducibly fixed.
- Capture core dumps/backtraces and Phoc/WebKit/EGL/kbase logs. Identify whether the failure is protocol negotiation, invalid format/modifier, FD lifetime, plane metadata, dma-buf coherency/synchronization, unsupported import, feedback/main-device reporting or a Phoc bug.
- Inspect the actual `zwp_linux_dmabuf_v1` version, advertised formats/modifiers, feedback tranches, target device and import path. Do not advertise formats/modifiers kbase/EGL cannot import.
- Use a minimal Wayland dmabuf test client before testing WebKit. Test allocate → export FD → send planes → compositor import → attach/commit → release/destroy. Exercise failed import paths and client disconnects.
- Correct protocol error handling: failed imports must be rejected/returned as protocol-defined failures without crashing Phoc. A later import failure after a buffer was created must not bring down the compositor. Ensure FD ownership/lifetime and buffer cleanup are correct.
- Test with `udmabuf` only if its format, coherency, mmap/export behavior and EGL import are verified. Do not infer full DMA-BUF/GBM support from `/dev/udmabuf` or `/dev/mali0`.
- Enable WebKitGTK accelerated backing store only after repeated stability tests with real WebKit frames, navigation, video/canvas, app switching, lock/unlock and memory pressure. Keep a runtime fallback switch to the current shared-memory path.

## 4. macOS FILE TRANSFER REALITY

MTP enumeration is already working. Finder does not natively mount MTP devices as volumes. Do not waste time changing the phone's MTP descriptors to force Finder to mount it and do not add USB mass-storage export of live filesystems. Instead:

- document and test OpenMTP or MTPLX on macOS;
- verify phone → Mac and Mac → phone copies with hashes;
- provide a Nuxel lockscreen/USB-mode hint explaining that MTP requires an MTP client on macOS;
- optionally investigate a Finder-visible SMB/WebDAV share over Wi-Fi, and USB only if a safe ECM/RNDIS path exists on this kernel. Do not use the previously known unsafe NCM teardown path.

## 5. HONESTLY RECHECK MOBILE NETWORK / CAMERA / NFC / SENSORS

Re-run each existing diagnostic and update Settings with the current exact blocker. Fix any userspace-only issue that is genuinely fixable. Do not claim working hardware without a physical test. Do not fetch random firmware, patch in proprietary Android HAL binaries or flash another kernel outside the agreed kernel change.

## 6. PERFORMANCE AFTER GRAPHICS STABILIZATION

Only after the dmabuf/WebKit path is stable:

- profile boot with `systemd-analyze time`, `critical-chain`, `blame`, journal timestamps and service readiness markers; do not optimize based on `blame` alone;
- profile lockscreen and app drawer open/first-paint/scroll, identify long tasks, unnecessary image decode, repeated DOM rebuilds, timers and Bridge polling;
- make drawer open immediately without accidental scroll, preserve tap-vs-swipe discrimination, virtualize only if measured necessary, and retain software-rendering fallback;
- benchmark CPU, memory, dropped frames and WebKit rendering before/after;
- fix the long black screen before normal reboot by tracing systemd stop jobs, units, `TimeoutStopSec`, `ExecStop`, display-owner shutdown and pending Wayland/screencopy work. Do not globally shorten every shutdown timeout; fix the actual blocking unit with bounded, ordered shutdown.

## 7. HARD SAFETY RULES

- The current known-good Nuxel boot/display stack is the recovery baseline. Back it up before any kernel change.
- No kernel flash without owner approval, verified backup, verified target partition and verified image hash.
- No flashing `vendor`, `vbmeta`, `dtbo`, modem or unrelated partitions unless the exact driver port technically requires a named artifact and the owner explicitly approves a separate plan.
- Do not use the dummy `boot-original.img`.
- No setuid-root Bubblewrap, no Flatpak sandbox bypass, no mass-storage export, no unsafe NCM, no second `/dev/fb0` owner.
- Never remove the current working GPU/EGL libraries until the candidate is proven and rollback is prepared.
- Preserve user data, SSH/Wi-Fi recovery, TWRP access, USB serial and display ownership.

## 8. DEFINITION OF DONE

- Verified kernel image boots into Nuxel after the TWRP-authorized flash; otherwise the backup is restored and further kernel work stops.
- Unprivileged namespaces work on the actual kernel with bounded sysctl values and Bubblewrap remains non-setuid; a real Flatpak installs, launches, uses portals and cannot access forbidden host resources.
- Phoc no longer crashes on valid/invalid dmabuf negotiation; the compositor remains stable under repeated WebKit accelerated rendering tests, or WebKit stays safely on shared memory with the precise blocker documented.
- MTP copies work using OpenMTP/MTPLX on macOS; Finder limitation is clearly explained; no unsafe mass storage.
- Mobile network/camera/NFC/sensors have current evidence-backed capability states.
- Boot, app drawer and shutdown/reboot are measurably faster/more reliable, with before/after evidence.
- All changes are reproducible in the source build, tests pass, rollback instructions and evidence are complete.

**Do not declare completion because a kernel config says `USER_NS=y`, a Wayland protocol is advertised, or an app icon appears. Prove the real sandbox, real compositor stability and real device behavior.**
