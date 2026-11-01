# PWNAGE-51000 — final blockers, kernel uplink, graphics and performance

Date: 2026-11-01
Target: Samsung Galaxy S10+ SM-G975F (`beyond2lte`, Exynos 9820)
OS: Nuxel / Fedora 43 ARM64
Transport: TWRP ADB `R58M75KDB2X`, then Wi-Fi SSH `root@192.168.178.167`
Live kernel after flash: `4.14.253-gf7194c1d15ed-dirty #8` (2026-11-01 10:16:28 UTC)

## Executive result

| Area | Result |
|---|---|
| Kernel `CONFIG_USER_NS=y` build, verified backup, TWRP flash, first boot | **PASS** |
| Phoc kbase GPU/display baseline after reboot | **PASS** (Mali-G76 MC12 Panfrost, 3× `/dev/mali0`, kbase context, `FRAMES_OK`, `decon_pan_failed=0`) |
| Flatpak / Bubblewrap unprivileged sandbox | **BLOCKED_KERNEL_RUNTIME** (vendor `create_user_ns()` gate; not a config-flag issue) |
| Phoc linux-dmabuf / WebKit acceleration | **BLOCKED_DIAGNOSED**; WebKit stays on shared memory |
| macOS MTP workflow | **PASS** (bidirectional SHA-256 verified with libmtp; Finder limitation documented; OpenMTP/MTPLX hint deployed) |
| Mobile network / camera / NFC / sensors | **NOT_SUPPORTED / BLOCKED_FIRMWARE / PRESENT_UNREADABLE** (fresh diagnostics) |
| Boot time | **PASS**: 61.825 s → **13.473 s** total; multi-user 17.259 s → **9.996 s** |
| Normal reboot / black screen | **PASS**: wayland stop 8.0 s → **3.3 s**; audio stop 8.0 s → **0.11 s**; reboot target ~4.2 s after audio stop |
| App drawer gesture/scroll source fix | **SOURCE_DONE + TEST_PASS**; physical touch confirmation **NEEDS_OWNER_TEST** |
| macOS MTP lockscreen hint | **DEPLOYED** |

The mission is **not** declared fully complete: Flatpak and WebKit acceleration remain honestly blocked. Everything else above is backed by the live handset and the evidence directory.

## 1. Kernel change — what was actually flashed

Built from the exact known-good tree `/work/src` at `f7194c1d15ed` (Linux 4.14.253 downstream), with the **minimal one-line config delta**:

```
-# CONFIG_USER_NS is not set
+CONFIG_USER_NS=y
```

Everything else is byte-identical in the final Image config, including
`CONFIG_UDMABUF=y`, `CONFIG_DRM=y`, `CONFIG_MALI_BIFROST_R26P0=y`,
`CONFIG_EXYNOS_DPU20=y`, and `CONFIG_INITRAMFS_SOURCE="/work/a25-kbase/initramfs.cpio"`.
The final Image's embedded IKCONFIG was extracted and checked directly.

The prior PWNAGE-50000 candidate `/root/pwnage50000/boot14.new.img` was **not reused**:
it had `CONFIG_INITRAMFS_SOURCE=""`, a different release (`4.14.253` without the
`gf7194c1d15ed-dirty` suffix) and a prior bootloop record. Its failure is recorded
in `PWNAGE-51000-KERNEL-SECURITY.md`.

Artifacts (evidence `kernel/`):

| Artifact | Bytes | SHA-256 |
|---|---|---|
| `Image-userns` | 49,508,360 | `513eedaaff70b82ac3112911fdbfee45de2ffac48fea98239870b6b3ffbf7a61` |
| `boot14.userns.img` | 52,445,184 | `9c339535e5affb3eff71bed74953938d4a8b309c8afbca58084e57e7d0929d11` |
| `boot14.userns.padded.img` | 57,671,680 | `574c239c910152fcf8321a132df9c567c8ce63da787fb2f7f0a8300a10b2fa59` |

`verify-a25-boot.py` PASS: raw arm64 Image, embedded initramfs member-for-member,
live ramdisk and appended DTB byte-identical, fits the 57,671,680-byte BOOT partition.
Readback of `/dev/block/sda14` after flash matched `574c239c…` exactly.

Recovery:
- Off-device known-good: `twrp/sda14.current.img` (SHA `97f78f5d…`) and
  `build/backup/sda14-known-good-20261101.img`.
- On-device: `/root/pwnage51000/sda14.known-good.img` (SHA `7f3f4454…`, same
  kernel payload as the known-good image; only the partition tail differs).

## 2. Boot acceptance (Outcome A)

Verified after the flash and after later reboots:

- Nuxel reached lockscreen/Home; Wi-Fi SSH up.
- `nuxel-wayland`, `nuxel-wl-fb`, `nuxel-web`, `nuxel-http-bridge`, `nuxel-mtp` active.
- `/dev/fb0` present; virtual geometry `1440,6080`; physical panel 1440×3040.
- `/dev/mali0` and `/dev/udmabuf` present; `/dev/dri` absent as expected.
- Phoc holds **3× `/dev/mali0`**, `/dev/udmabuf`, and `anon_inode:dmabuf_udmabuf`.
- kbase context owned by `phoc` (e.g. ctx 2902).
- `nuxel-wl-fb.state`: `FRAMES_OK … decon_pan_failed=0`.
- `/run/nuxel-gpu-fallback` absent.
- Touch controller `sec_touchscreen` accepted; physical touch remains an owner check.
- No rollback was needed.

## 3. Flatpak — exact remaining blocker

Live facts:

```
CONFIG_USER_NS=y
CONFIG_MULTIUSER=y
CONFIG_SECCOMP=y / CONFIG_SECCOMP_FILTER=y
CONFIG_CGROUPS=y / MEMCG / CGROUP_PIDS
user.max_user_namespaces = 27213
user.max_mnt_namespaces  = 27213
/usr/bin/bwrap = 0755 root:root (setuid bit removed; no setuid fallback)
unshare -Ur true  -> EPERM
bwrap --unshare-user ... -> EPERM
```

The kernel config gate is cleared, but the real sandbox is not. The vendor
`kernel/user_namespace.c::create_user_ns()` contains:

```c
ret = -EPERM;
if (current_chrooted())
    goto fail_dec;
...
#ifdef CONFIG_LOD_SEC
if (0 != (current_cred()->uid.val)) {
    ret = -EPERM;
    printk(KERN_ERR "LOD: blocking USERNS from non-root ...");
    goto fail_keyring;
}
#endif
```

`CONFIG_LOD_SEC=y` is set in the running kernel. Root `unshare -U` is rejected
without the LOD print, which is consistent with the earlier `current_chrooted()`
check; non-root would additionally hit LOD. The exact root gate could not be
instrumented because kprobes/function_graph were unavailable on this kernel. A correct next kernel would need a
reviewed patch to the userns creation path (or a different kernel baseline),
followed by a **new explicit owner-approved flash**. No such second flash was
attempted.

The bridge now reports the live result, not the config flag:

```json
"user_namespace": {"ok": false, "detail": "unshare: unshare failed: Operation not permitted"},
"flatpak_ready": false,
"flatpak_blocker": "user namespace creation denied by the kernel: unshare: unshare failed: Operation not permitted"
```

Flatpak 1.16.6 and runtimes are installed, but no ARM64 Flatpak launch or portal
test is claimed. No setuid bwrap, no `--no-sandbox`, no host filesystem grant,
no SELinux change.

## 4. Phoc linux-dmabuf / WebKitGTK

The live Phoc global list does **not** contain `zwp_linux_dmabuf_v1`. The patched
wlroots only creates it when the renderer reports DMA-BUF texture formats; the
kbase GLES2 renderer reports none, so no global is advertised. Forcing the live
global previously produced SIGSEGV/SIGBUS, and the `nuxel-wayland-egl-probe`
crashes inside Mesa `dri2_destroy_surface` (libEGL_mesa) on the Wayland EGL path.
Coredumps and the journal are preserved in `evidence/pwnage-51000/dmabuf/`.

Decision: **WebKit accelerated backing store stays disabled.** The live
`nuxel-pwa-host` continues to log the honest software fallback
(“GTK failed to initialize GL”). The compositor itself remains on the proven
kbase GPU path. See `PWNAGE-51000-DMABUF-CRASH.md`.

A regression found during this run was repaired: the stock Mesa
`libgallium_dri.so` and stock `libEGL_mesa.so.0` symlink had replaced the kbase
set. Restored:

```
/usr/lib64/libEGL_mesa.so.0 -> libEGL_mesa.so.0.0.0 (3800718…)
/usr/lib64/libgallium_dri.so (b5e167e…, Mesa 26.3.0-devel)
/usr/lib64/libwlroots-0.19.so (2ccada1…)
/usr/lib64/dri/panfrost_dri.so -> ../libgallium_dri.so
/usr/lib64/dri/exynos_dri.so   -> ../libgallium_dri.so
```

The rootfs builder now installs this set from `build/out/s10plus/kbase-gpu`
so a clean image cannot regress it silently.

## 5. macOS MTP — PASS

Live gadget: `acm.usb0` + `mtp.gs0`, UDC configured at high-speed.
`/dev/mtp_usb` present, `nuxel-mtp.service` active, root = `/home/nuxel/Shared`
(plus Gallery/Pictures/Videos/Downloads). No mass-storage function, no rootfs
export, no unsafe NCM path.

macOS libmtp 1.1.23:
- Device `18d1:4ee7`, Manufacturer `Nuxel`, Model `Nuxel S10+`.
- Phone → Mac: file ID 17 → `699b99276f09ec5…` (matches the phone).
- Mac → phone: `mtp-sendfile` → `/home/nuxel/Shared/mac-to-phone-nuxel.txt`,
  SHA-256 `caba21e6766f5ad47a4f75a1bd0f2fc812696d495699a6ad657a7f5d3eee5a3`
  (matches the Mac source).

Finder does not natively mount MTP. The lockscreen connection-mode dialog now
says: “On macOS use OpenMTP or MTPLX; Finder does not mount MTP volumes.”
The USB mode choice is persisted in `/var/lib/nuxel/usb-mode` and restored by
`nuxel-usb-mode-restore.service`; MTP survived the final reboot.

## 6. Device capabilities (fresh evidence)

- Mobile network: `NOT_SUPPORTED_ON_DEVICE` — no CP host interface, no
  ModemManager Shannon plugin, no SIM source.
- Camera: `BLOCKED_FIRMWARE` — FIMC-IS nodes/sensor names enumerate, but no
  media graph/subdev nodes and all expected setfiles/`is-camera` blobs are absent.
  No frame claimed.
- NFC: `BLOCKED_FIRMWARE` — `sec-nfc` chardev and subsystem exist, firmware and
  userspace stack do not.
- Sensors: `PRESENT_UNREADABLE` — 9 IIO/input classes enumerate, 0 readable raw
  channels (SSP hub down). No synthetic readings.

## 7. Performance

Boot (same handset, same session data):

| Metric | Before | After | Change |
|---|---|---|---|
| Kernel | 3.449 s | 3.446 s | — |
| Userspace | 58.375 s | **10.027 s** | −83% |
| Total | 61.825 s | **13.473 s** | −78% |
| multi-user.target | 17.259 s | **9.996 s** | −42% |
| ABOX reload | 48.329 s on boot path | 23.85 s, deferred after Home | off critical path |

Shutdown (previous boot, monotonic):
- `nuxel-wayland` stop: 8.03 s timeout → **3.29 s**.
- `nuxel-audio-session` stop: 8.15 s timeout → **0.11 s**.
- audio-route stop → reboot.target: **4.2 s** (was ~9 s).
- Final reboot round-trip to SSH: 92 s → 86 s (shutdown + boot + SSH).

App drawer source fixes:
- 250 ms drawer-open guard; the opening swipe cannot replay into the scroller.
- 12 CSS px tap/scroll discrimination; movement cancels launch.
- Cached drawer list already present; no full rebuild on normal open.
- Regression test `tests/pwnage50000/test_drawer_gesture_guard.py` PASS.

Physical drawer/swipe/tap confirmation remains `NEEDS_OWNER_TEST`.

## 8. Tests run

- Kernel config/Image extraction: `CONFIG_USER_NS=y`, embedded initramfs.
- `verify-a25-boot.py`: PASS.
- Flash readback SHA-256: PASS.
- `unshare -U/-m/-p/-n/-i/-u`: all non-userns namespaces work; userns EPERM.
- `bwrap` non-setuid, mode 0755.
- MTP phone↔Mac hashes: PASS.
- Local JS/shell/Python checks: PASS.
- `systemd-analyze verify`: PASS on changed units.
- Boot/shutdown measurements: recorded above.

## 9. Honest limitations

1. Flatpak is **not supported** on this kernel yet. `CONFIG_USER_NS=y` is present
   but the vendor LOD/root userns gate denies creation. A second kernel build/flash
   requires explicit owner approval.
2. WebKitGTK acceleration is **not enabled**. The live compositor has no
   linux-dmabuf global; forcing it crashes; the Mesa Wayland EGL path crashes in
   `dri2_destroy_surface`.
3. MTP works with a client; Finder does not mount MTP by design.
4. Touch, drawer gestures, camera/NFC/sensor physical behavior need owner tests.
5. The current `systemd-analyze time` is measured with the ABOX timer running
   after boot; it no longer holds the initial transaction.

## 10. Rollback

See `PWNAGE-51000-ROLLBACK.md`. The kernel rollback image is verified and copied
off-device; no second flash was attempted.
