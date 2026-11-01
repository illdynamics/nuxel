# PWNAGE-51000 — task / evidence tracker (final)

Live target: Samsung Galaxy S10+ SM-G975F (`beyond2lte`), Fedora 43 ARM64,
Exynos 9820, vendor kbase Mali-G76, Phoc on DPU20 fbdev.
Final kernel: `4.14.253-gf7194c1d15ed-dirty #8` (2026-11-01 10:16:28 UTC).

| # | Task | Status | Evidence |
|---|---|---|---|
| 1 | Baseline: TWRP transport, partition map, live boot hash | **PASS** | `baseline/twrp-device-and-boot.txt`, `twrp/sda14.current.img` |
| 2 | Off-device verified boot backup | **PASS** | `twrp/sda14.current.img` + `build/backup/sda14-known-good-20261101.img` (97f78f5d…) |
| 3 | Reject dummy/stale boot images | **PASS** | p50000 image rejected (empty initramfs, wrong release); documented |
| 4 | Kernel source/config security review | **PASS** | `PWNAGE-51000-KERNEL-SECURITY.md` |
| 5 | Minimal `USER_NS=y` build from known-good tree | **PASS** | `kernel/Image-userns` 513eedaa…; final IKCONFIG |
| 6 | Boot image pin/verification | **PASS** | `kernel/boot14.userns.padded.img` 574c239c…; verifier PASS |
| 7 | TWRP flash + readback | **PASS** | `sda14` readback 574c239c… |
| 8 | Outcome A boot (display, kbase, touch node, Wi-Fi/SSH) | **PASS** | `baseline/final-kernel-and-services.txt` |
| 9 | Rollback | **NOT NEEDED**; image verified | `PWNAGE-51000-ROLLBACK.md` |
| 10 | Flatpak unprivileged namespaces | **BLOCKED_KERNEL_RUNTIME** | `flatpak/live-runtime-tests.txt`; vendor LOD/chroot gate |
| 11 | Bubblewrap non-setuid | **PASS (mode)** | `/usr/bin/bwrap` 0755; setuid removed |
| 12 | Flatpak app + portals | **BLOCKED** (no userns) | no claim made |
| 13 | Phoc kbase GPU/display baseline | **PASS** | 3× `/dev/mali0`, ctx 2902, `FRAMES_OK`, `decon_pan_failed=0` |
| 14 | Phoc linux-dmabuf root cause | **DIAGNOSED / BLOCKED** | `PWNAGE-51000-DMABUF-CRASH.md` |
| 15 | WebKitGTK acceleration | **STAYS DISABLED** | software fallback; no false claim |
| 16 | kbase Mesa regression repair | **PASS** | kbase EGL/gallium/wlroots restored; rootfs builder updated |
| 17 | macOS MTP phone→Mac | **PASS** | SHA 699b9927… |
| 18 | macOS MTP Mac→phone | **PASS** | SHA caba21e6… |
| 19 | Finder limitation / OpenMTP hint | **DEPLOYED** | lockscreen connection-mode dialog |
| 20 | MTP persistence across reboot | **PASS** | `/var/lib/nuxel/usb-mode`, restore unit |
| 21 | Mobile network recheck | **NOT_SUPPORTED_ON_DEVICE** | `drivers/capability-diagnostics.txt` |
| 22 | Camera recheck | **BLOCKED_FIRMWARE** | same |
| 23 | NFC recheck | **BLOCKED_FIRMWARE** | same |
| 24 | Sensors recheck | **PRESENT_UNREADABLE** | same |
| 25 | Boot critical path | **PASS** | 61.825 s → 13.473 s; multi-user 17.259 s → 9.996 s |
| 26 | ABOX off boot path | **PASS** | boot timer; `PWNAGE-51000-PERF.md` |
| 27 | App drawer initial-scroll guard | **SOURCE_DONE/TEST_PASS** | 250 ms guard; 12 px discrimination |
| 28 | Drawer scroll-vs-tap launch | **SOURCE_DONE/TEST_PASS** | `test_drawer_gesture_guard.py` |
| 29 | Physical drawer/touch confirmation | **NEEDS_OWNER_TEST** | cannot be proven over SSH |
| 30 | Shutdown black screen | **PASS** | wayland 8.03 s → 3.29 s; audio 8.15 s → 0.11 s |
| 31 | Reboot repetition | **PASS (3 measured)** | 92 s → 83/84/86 s round-trip |
| 32 | Reproducible rootfs kbase install | **PASS** | `build-phone-rootfs-inside-fedora.sh` updated |
| 33 | Truthful Settings/bridge status | **PASS** | live `software_provider` JSON |

## Honest blockers

1. **Flatpak**: `CONFIG_USER_NS=y` is present, but `create_user_ns()` still
   returns EPERM. The vendor `CONFIG_LOD_SEC` gate plus the earlier
   `current_chrooted()` check must be addressed in a reviewed kernel patch.
   A second flash requires explicit owner approval.
2. **WebKit/Phoc dmabuf**: the kbase renderer advertises no DMA-BUF texture
   formats, so Phoc has no linux-dmabuf global; forcing it crashes; the Mesa
   Wayland EGL probe crashes in `dri2_destroy_surface`. WebKit remains on
   shared memory.
3. **Physical tests**: touch, drawer gestures, camera/NFC/sensor hardware
   behavior need the owner.
