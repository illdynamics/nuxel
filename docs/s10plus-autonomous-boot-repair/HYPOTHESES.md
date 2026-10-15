# HYPOTHESES (cycle 2, after the A2 result)

## H-KERNEL-GZIP — CONFIRMED (hardware)
S-Boot branches to `kernel_addr` (0x10008000) without decompressing. With the
gzip payload (`1f 8b 08 …`) the CPU took an immediate UNDEFINED-instruction
exception: 7 identical loads -> zero console bytes. With the raw `Image` (A2) the
kernel ran until t≈1.96 s and its panic dump is in pstore.
**Evidence:** E1/E2 (7 silent loads) + A2 panic with
`linux_banner: Linux version 4.14.253 (nuxel@nuxel-phosh)`.

## H-RAMDISK-DELIVERY — the ramdisk handed to the kernel is unusable  (CONFIRMED mechanism, A3 = fix)
`unpack_to_rootfs()` returned "junk in compressed archive", which per
`init/initramfs.c` means the buffer had no recognisable magic or never reached
`TRAILER!!!`. S-Boot reports `ramdisk size = 0x5be800` = 6,022,144 while our
payload is 6,022,352 B, and the live DT shows S-Boot relocates the initrd to
`0x89000000` with `initrd-end = 0x89a66800` = its own rounded length. A 6,022,352
B gzip stream delivered as 6,022,144 B is truncated; `lib/decompress_inflate.c`
does not treat `Z_BUF_ERROR` as fatal, so the partial cpio parse ends in
`state != Reset` = "junk in compressed archive".
**Fix under test (A3):** uncompressed `newc` cpio zero-padded to exactly
8,194,048 B (multiple of 2048/512). No decompressor, and any S-Boot size
rounding can only discard trailing zeros.

## H-CONTAINER-VERSION — the packer wrote the DTB size where `header_version` lives (FIXED in A3)
S-Boot logs `[UFDT] BOOT IMG HDR V376101` for our image and `V1` for the
recovery image, so it really does branch on offset 40. A3 writes a real v1
header. Kept in the same candidate as the ramdisk fix because both are
"make the container match the device's own booting image", and the mission's
cycle budget is 3 hardware candidates.

## H-SAR-OOM — Samsung's in-kernel ramdisk fallback cannot load a >4 MB ramdisk (EXPLAINED, not a target)
`init/do_mounts.c`: when `android_bootmode != 2` the kernel calls
`mount_sar_ramdisk("/dev/android_boot")`, which kmallocs the ramdisk from the
boot partition. `mm/page_alloc.c:4258` WARN + `SAR_RD: Out of memory` for
6.0 MB (order > MAX_ORDER-1 = 4 MB). A3's uncompressed cpio is 8 MB, which is
**larger**, so this fallback would fail again - which is fine: A3 must succeed
via the *initramfs* path, and that is what the diagnostics will show.

## H-INIT-GROUP-EXIT — Samsung panics when PID 1 exits (SYMPTOM)
`Kernel panic - not syncing: init group exit` fires when PID 1's group exits;
here PID 1 was the init of the *fallback* root (sda25, from S-Boot's
`root=PARTUUID=…`), i.e. downstream of the ramdisk failure. It is a symptom and
does not indicate a Fedora or systemd defect.

## Still open
* H-DISPLAY: the Nuxel kernel *did* initialise display drivers (`130b0000.displa`,
  `decon0/2`, `dsim0-wq`, `panel-bl-thread`, `decon_devfreq_change_task` appear
  in the A2 task dump), so DRM should exist; whether fbdev/`/dev/fb0` exists for
  `nuxel-firstlight.service` is untested.
* H-FEDORA: systemd 258.11 on a 4.14 kernel warns about the version baseline; it
  is not fatal. Untested until the rootfs handoff succeeds.

---

# HYPOTHESES (cycle 3, after source + DT forensics)

## H-HEADER-LEGACY — the packer's offset-40 defect (CONFIRMED, now gated)
`pack-boot-v1.sh` wrote the DTB size at header offset 40, where `boot_img_hdr_v1`
requires `header_version == 1`. S-Boot logs the field
(`[UFDT] BOOT IMG HDR V376101` vs `HDR V1`). Fixed in cycle 2 (`--v1-spec`) and now
**enforced** by `tools/s10plus/verify-boot-image.py` + `--strict`.
Candidates A2 and the legacy diagnostic image fail the gate on exactly this.

## H-KERNEL-GZIP — gzip kernel payload (CONFIRMED, now gated)
S-Boot jumps to `kernel_addr` without decompressing. A gzip payload is executed as
code (A1: seven silent loads, zero console bytes). The gate rejects `1f 8b`
kernels, so A1 and `nuxel-beyond2lte-boot-merged-fixed.img` fail.

## H-INITRD-MEM — for a normal BOOT boot the 0x89000000 window is not populated (STRONG, under test)
* For the **recovery** boot the window is populated: the booting kernel's own DT
  says `linux,initrd-start = 0x89000000`, `end = 0x89a66800`, and that LZMA stream
  decompresses to a complete 48,020,736-byte `070701` cpio with `TRAILER!!!`.
* For our **normal** boots the kernel is told the same fixed base and a length
  that exactly matches our header (`Freeing initrd memory: 8128K` for an
  8,323,072-byte payload) yet reads bytes that are not a cpio at all — and in one
  boot the parser failed 0.21 ms after starting, which is only possible if the
  first non-NUL byte is neither `'0'` nor a compression magic.
* Prediction: with an LZMA ramdisk (A6) the failure *mode* changes if the payload
  is delivered (`decompressor failed` or success) and stays
  `junk in compressed archive` if it is not.
* `bootmode=` is absent on a normal boot and `bootmode=2` on recovery, so S-Boot
  / the kernel really do take different ramdisk paths.

## H-RAMDISK-CONTAINER — S-Boot's ramdisk path is format-aware (UNDER TEST, = A6)
The only ramdisk proven to be both delivered and unpacked on this handset is
TWRP's LZMA-alone stream. A6 rebuilds the Nuxel initramfs in exactly that shape
(props `5d`, dict 8 MiB, size `0xffffffffffffffff`) and additionally aligns the
container to 65,536 bytes so no S-Boot rounding rule (up, down or exact) can clip
the end-of-stream marker. Container bytes after the EOS marker are zeros, which is
exactly what the working TWRP ramdisk already carries (+23 bytes).

## H-NO-DEV-CONSOLE — no initramfs console (CONFIRMED, fixed in A6)
`prepare_namespace()` is skipped for a built-in initramfs, so devtmpfs is never
mounted by the kernel and `/dev/console` must come from the archive. Ours was
missing, hence `Warning: unable to open an initial console.` This made ALL
previous "no initramfs output" observations uninformative. A6 adds
`dev/console` (5:1) and `dev/null` (1:3).

## H-SAR-RD-OOM — Samsung's in-kernel fallback cannot carry our ramdisk
`init/do_mounts.c`: when `android_bootmode != 2` the kernel calls
`mount_sar_ramdisk("/dev/android_boot")`, kmalloc'ing the ramdisk out of the BOOT
partition. 8.3 MB exceeds kmalloc's max order, giving `WARN` at
`mm/page_alloc.c:4258` + `SAR_RD: Out of memory`, then the `root=PARTUUID=...`
fallback mounts SYSTEM (sda25) and its `init` exits -> `init group exit`.
Not a target to fix, but it identifies a *third* route to userspace that does not
depend on `/chosen` at all.

## H-INIT-GROUP-EXIT — Samsung panics when PID 1 exits (SYMPTOM)
Fires only downstream of the ramdisk failure (the fallback root's init exits).

## H-SYSTEMD-4.14 — Fedora 43 userspace vs Linux 4.14 (OPEN, milestone 8)
Not diagnosable until `/init` runs. Plan: prove USERDATA mounts, prove a small
Fedora binary executes, then establish a supported init strategy (systemd requires
>= 5.4 + cgroup v2) rather than assuming the systemd ELF existing implies it runs.

## Closed / retired by evidence
* **H-RAMDISK-ADDRESS (was A8):** retired. S-Boot ignores the header
  `ramdisk_addr` and uses the fixed 0x89000000 base for TWRP *and* for us.
* **H-CHOSEN-PLACEHOLDER (was A5):** retired. S-Boot overwrites
  `/chosen/linux,initrd-*`; removing the placeholders changed nothing. Keeping
  them out remains correct hygiene (a change there must never be counted as an
  effective device-tree experiment).
* **H-PADDING-ONLY:** retired by the argument in ROOT-CAUSE.md §2 — with the raw
  cpio present in memory, no padding scheme could have failed.

---

# HYPOTHESES — cycle 3 FINAL (after A7's instrumentation)

## H-INITRD-MEM — CONFIRMED BY DIRECT MEASUREMENT
The instrumented kernel printed the address, the length and the first 16 bytes of
the initrd S-Boot declares:
```
external_initrd=1 start=ffffffc009000000 end=ffffffc009080000 len=524288
initrd head: 5b 20 20 20 20 31 2e 30 34 35 36 36 35 5d 20 5b   ascii "[    1.0"
unpack attempt: first=0x5b this_header=0 remaining=524288 method=(none)
```
`0xffffffc009000000` is the linear alias of `0x89000000`; `len` is exactly our
header's ramdisk size rounded to 2048; and the bytes there are the kernel's own
console text (zeros on another boot). **S-Boot publishes the initrd entry in
`/chosen` without loading the payload on the normal BOOT-partition path.** The
`bootmode=2` recovery path does load it, which is why TWRP's LZMA ramdisk unpacks.
Not fixable from the container; A7 removes the dependency by embedding the
initramfs in the kernel.

## H-RAMDISK-CONTAINER — REFUTED (hardware, A6)
A6 shipped our initramfs as LZMA-alone with the exact properties, dictionary and
unknown-size EOS-marker layout of the TWRP ramdisk, page-aligned to 65536 bytes.
S-Boot consumed the new size (`ramdisk size = 0x5c0000`, `Freeing initrd memory:
5888K`) and the kernel still rejected the payload **0.21 ms** after starting — an
immediate, first-byte rejection that an LZMA stream at that address could not
produce. Container format was never the problem. **No further format experiments.**

## H-NO-CONSOLE — CONFIRMED, and larger than first thought
`/dev/console` (char 5:1) exists but `open()` returns **ENODEV** on this handset
(measured live): `console=ram` registers a `struct console` with no tty. So
`kernel_init` cannot open an initial console, PID 1 has invalid stdio, and **no
initramfs output could ever be captured** — regardless of `/init` running.
Fix: `/dev/kmsg` (1:11) works (S-Boot sets `printk.devkmsg=on`); A8 ships
`dev/kmsg` in the archive and routes every diagnostic through it first.

## H-VENDOR-BOOT-TIMEOUT — NEW, CONFIRMED
A7's boots ended at t=37 s / 68 s (`hard_reset_hook_callback` ->
`Fatal exception in interrupt`) and t=242 s (`hung_task: blocked tasks`, with
EXYNOS thermal `tz_worker_threa`, `scsi_srpmb_work`, `ree_time` blocked). These are
the vendor kernel's "boot never signalled success" mechanisms, not our path.
Consequence: candidates must finish and persist evidence within ~40 s -> A8's
`NUXEL_BOOT_WATCHDOG=45` and the early BOOT-slack heartbeat.

## H-KERNEL-EMBEDDED-INITRAMFS — CONFIRMED (hardware, A7)
`CONFIG_INITRAMFS_SOURCE` works on this device: `unpack verdict: message=(none)
state=7` (success) for the built-in archive, and `/init` is then executed because
`kernel_init_freeable()` finds it and skips `prepare_namespace()` (no `RAMDISK:`,
no `SAR_RD`, no `init group exit`). Also verified offline: the generated
`usr/initramfs_data.cpio.gz` (551,027 B) is embedded **byte-for-byte** in the
`Image` at file offset `0x203E510`, and the archive contains
`dev/console`, `dev/kmsg`, `dev/null`, `bin/sh -> toybox` and `/init` byte-identical
to `boot/initramfs/init.sh`.

## H-SAR-RD-OOM — now moot for the critical path
Unchanged in mechanism (Samsung's `mount_sar_ramdisk()` kmallocs the ramdisk out of
the BOOT partition and 8 MB exceeds kmalloc's max order). With A7/A8 the ramdisk is
512 KB, so even that fallback would now fit — but `prepare_namespace()` is not
reached at all once `/init` exists.

## H-SYSTEMD-4.14 — OPEN (milestone 8)
Fedora 43 ships systemd 258.11 (requires Linux >= 5.4, cgroup v2, no cgroup v1
support); the kernel is 4.14.253. To be attacked only after USERDATA mounts and a
small Fedora process can be shown to execute.

## Retired by evidence (do not retry)
* **H-RAMDISK-CONTAINER** — refuted by A6.
* **H-RAMDISK-ADDRESS / A8-old ("set header ramdisk_addr := 0x89000000")** — S-Boot
  ignores the header address and uses the fixed 0x89000000 for both images.
* **H-CHOSEN-PLACEHOLDER** — S-Boot overwrites `/chosen/linux,initrd-*`.
* **H-PADDING-ONLY** — immaterial: the raw `newc` cpio cannot fail with "junk in
  compressed archive" if it is present in memory at all.

---

# HYPOTHESES — cycle 4 (2026-10-15, after A12)

## H-PIDFD-SPAWN-ENOSYS — CONFIRMED (source-exact, hardware-consistent); fix = A13
`posix_spawn_wrapper()` in systemd 258.11, built with glibc ≥ 2.39
(`HAVE_PIDFD_SPAWN`), calls `pidfd_spawn()` **only** and retries the same
function. glibc's `pidfd_spawn()` requires `waitid(P_PIDFD)` (Linux **5.4**) and
returns `ENOSYS` with **no fallback** on this 4.14.253 kernel. Result: every
unit spawn fails with `Failed to spawn executor: Function not implemented`.
Fix: backport upstream's `pidfd_spawn` → `posix_spawn` fallback. Details,
including why this is *not* clone3, in ROOT-CAUSE.md (cycle 4).

## H-WATCHDOG-SELF-REBOOT — CONFIRMED (A12, hardware)
A12's boot was **ended by our own initramfs watchdog**, not by the vendor:
`NUXEL_BOOT_WATCHDOG=30` was armed at t≈1.97 s, and a process with comm `init`
(only the pre-`switch_root` subshells inherit that comm) called `reboot(RB_AUTOBOOT)`
at t=31.971 s (`debug-snapshot: normal reboot starting`, `sec_debug: set magic
code (0x0)`). The intended disarm before `switch_root`
(`kill "$NUXEL_WATCHDOG_PID"`, init.sh:766) evidently did not take effect.
Prime suspect: the initramfs carries no `kill` applet/builtin (the toybox applet
list in `init.sh` symlinks `sync reboot poweroff dd ...` but **not `kill`**), and
the failure is invisible because that line redirects stderr to /dev/null.
Consequence: A12's systemd had only ~18 s of life, and evidence after t≈14.4 s
was destroyed. A13 must (a) ship/verify `kill`, (b) re-arm the watchdog for a
realistic window, (c) keep the kmsg fd open so a firing watchdog *always* leaves
a marker, and (d) keep the softdog fed across the handoff via a held fd.

## H-FB0-PRESENT — CONFIRMED (A12 log, hardware)
`show_boot_splash()` reached its "no splash data — showing navy boot screen"
branch, which is only reachable when `/dev/fb0` or `/dev/graphics/fb0` exists as
a character device. So **a framebuffer node is present** at t≈1.96 s on this
kernel. S-Boot's own log shows the panel path being brought up before the kernel
(`s6e3ha9_panel_read_id READ ID : A1 10 13`, `init_decon: xres 1440 yres 3040`,
`reset_panel:system rev : 26`) and passes `s3cfb.bootloaderfb=0xca000000
lcdtype=10555411`, i.e. the kernel reuses the bootloader's framebuffer. First
light is therefore an fbdev write, not a DRM/KMS bring-up.

## H-NO-DRM — CONFIRMED (shipping kernel config)
`# CONFIG_DRM is not set` in the config embedded in the A12 `Image`
(IKCFG_ST, 6123 lines). There is no KMS path on this kernel ⇒ **no
`/dev/dri/card*`**, so Phoc/Phosh (Wayland/DRM) cannot run on this kernel even
after systemd is repaired. fbdev first light is the achievable next milestone;
a DRM/KMS phone session needs a different kernel (see Option C, Phase 2).

## H-WRITABLE-ROOT — SUPPORTED (offline, needs hardware confirmation)
The USERDATA ext4 superblock's incompat mask is `0x000022c2`
(FILETYPE|EXTENTS|64BIT|FLEX_BG|CSUM_SEED) and its ro_compat mask `0x0000046b`
(SPARSE_SUPER|LARGE_FILE|DIR_NLINK|EXTRA_ISIZE|BTREE_DIR|METADATA_CSUM) — every
bit is in this kernel's `EXT4_FEATURE_INCOMPAT_SUPP`/`RO_COMPAT_SUPP`
(`fs/ext4/ext4.h`). `s_state=1` (clean), 716,137 of 1,048,576 blocks free.
A read-write mount is therefore supported in principle; A12 rendered `ro` only
because `ROOT_MOUNT_MODE` was `ro` (the code path that logs `mode=` prints the
*variable*), which is itself a diagnostic defect to fix in A13.

## H-SYSTEMD-4.14 (cycle 3) — superseded by H-PIDFD-SPAWN-ENOSYS
The version mismatch is real (systemd warns about the 5.7 baseline) but it is
**not** a blanket incompatibility: PID 1 ran to `basic.target`, generators ran,
the cgroup tree was created, and only the pidfd-based spawn path failed.


---

# HYPOTHESES — cycle 4 (A13), added after the A12 read-through

| ID | Hypothesis | Status | How A13 discriminates |
|---|---|---|---|
| H-C4-A | `Failed to spawn executor: ENOSYS` is glibc `pidfd_spawn()` gated on `waitid(P_PIDFD)` (Linux 5.4) | **CONFIRMED at source level**; hardware confirmation in A13 | `NUXEL-SPAWN-PROBE … waitid(P_PIDFD,…) errno=22 EINVAL`, `posix_spawn rc=0`, `pidfd_spawn rc=38 ENOSYS` |
| H-C4-B | The pidfd_spawn→posix_spawn backport makes services start | OPEN | `systemd-journald.service` starts instead of `Failed to spawn executor` |
| H-C4-C | The A12 `os-release: <none>` came from a defective read, not from a bad rootfs | OPEN (mechanism unexplained; the rootfs is offline-verified Fedora) | new `ROOTFS_IDENTITY_RAW file=… text=…` line names the file and its content; `nuxel_marker ROOTFS_IDENTITY_OK` |
| H-C4-D | A12's reset was our watchdog, not `hard_reset_hook` | **CONFIRMED** | t=31.971 s, `comm=init`, `set magic code (0x0)`; `NUXEL_BOOT_WATCHDOG=30` armed at t≈1.97 s |
| H-C4-E | The watchdog survived `switch_root` because toybox has no `kill` applet | **CONFIRMED** | `strings toybox-a12` lists `killall` but not `kill` |
| H-C4-F | Our `mount --move /dev` severed the evidence channel | **CONFIRMED as the mechanism** for the missing watchdog message | A13 mounts fresh `/proc`, `/sys`, `/dev` inside the new root |
| H-C4-G | `/dev/fb0` exists and is writable, so first light is an fbdev write, not a DRM problem | OPEN | `FIRSTLIGHT …` lines; `nuxel-fb-phone` prints a named `NUXEL_FB_*` reason on every failure path |
| H-C4-H | The panel may be driven by the bootloader's DECON and ignore kernel fb writes | OPEN — this is the main first-light risk | operator-visible result; a zero exit with no visible change confirms it |
| H-C4-I | cgroup v2 / BPF gaps are cosmetic for service startup on 4.14 | OPEN | BPF attach failures were already non-fatal in A12 (`Proceeding WITHOUT applying ACL`); check whether any *unit* fails for a cgroup reason after the repair |

---

# CYCLE 5 HYPOTHESES (A15)

## H-C5-1 — the A14 spontaneous reboot was our own initramfs dead-man watchdog — **CONFIRMED (hardware)**

*Prediction:* if the watchdog is the cause, the reboot request appears at exactly
`arm_time + NUXEL_BOOT_WATCHDOG` and comes from an initramfs-lineage process
(comm inherited `init`), with the *normal* reboot magic and no panic.
*Measurement:* probe error at t=47.163135 s, reboot notifier at t=47.171346 s
(armed t≈2.15 s, `NUXEL_BOOT_WATCHDOG=45`) from PIDs 3557/3558/3561, comm `init`,
`sec_debug: set magic code (0x0)`, `debug-snapshot: normal reboot starting`, no
panic/BUG, HW watchdog petted every 10 s. A12 showed the same pattern with its
30 s deadline (single rebooting PID 3466, comm `init`, t=31.971 s).
*Residual uncertainty (recorded honestly):* the script's `*) exit 0` branch
*should* have made an empty PID-1 probe exit silently, and three tasks rebooted
within 8 ms where one `sync; reboot -f` was expected. The empty-string `case`
behaviour of this toybox `sh` (0.8.14) cannot be tested off-hardware, and the
watchdog's own evidence lines were discarded to `/dev/null`. What is *not* in
doubt is that the reboot originates in the initramfs shell lineage at the
watchdog's deadline — hence P-C5-1 removes the block rather than "fixing" it, and
A15's log will show whether any reboot request remains.

## H-C5-2 — mounting cgroup v2 lets systemd actually start services

*Prediction:* with `/sys/fs/cgroup` a cgroup2 mount inside the new root,
`Failed to attach to cgroup /system.slice/…` disappears, `system.slice` and
`init.scope` are created, and units progress from `Failed at step CGROUP` to
either running or failing for a *different*, readable reason.
*Supporting evidence:* kernel has `CONFIG_CGROUPS=y` + all controllers
(A15 config); A14's failure message is a missing destination, and A14's own probe
reported `cgroup2_unified=absent`.
*Falsifier:* `CGROUP2_MOUNT_FAILED` in the A15 log, or the same
`Failed at step CGROUP` after a successful mount (which would move the
investigation to controller delegation).

## H-C5-3 — the panel is black because the DECON scans a buffer we do not paint

*Prediction:* painting **both** halves of the 1440×6080 virtual framebuffer makes
the frame appear even though A14's single-buffer paint did not.
*Alternative (D2/D3 in DISPLAY-BRINGUP.md):* the DECON window is simply not
enabled, in which case no amount of fbdev writing helps and the next cycle must
work in `drivers/video/fbdev/exynos/decon/`.

## H-C5-4 — the A14 black screen is not a userspace failure at all

*Prediction:* with the watchdog gone and cgroup v2 present, the boot continues
long past 47 s; the only open question is the panel.
*Falsifier:* a new reboot or a new fatal error before the handoff.

---

# CYCLE 6 — hypotheses (A16)

| ID | Hypothesis | Status | Evidence / test |
|---|---|---|---|
| H-C6-A | The A15 reset is Samsung's operator hard-reset hook, not a boot defect | **CONFIRMED** | `kernel BUG at drivers/samsung/sec_hard_reset_hook.c:157!` + `hard_reset_hook_callback` in the panic stack; no other panic/watchdog/reboot line in 1892 s |
| H-C6-B | The A15 initramfs watchdog removal was correct | **CONFIRMED** | 1892 s uptime with HW watchdog keepalives throughout; A14's `normal reboot starting` at t=47.171 s is absent |
| H-C6-C | `FIRSTLIGHT_FRAME_WRITTEN` in A15 was not display evidence | **CONFIRMED** | the A15 log contains `FIRSTLIGHT exit=0` and *no* `NUXEL_FB_INFO`/`NUXEL_FB_ANIM`; the shell's `read` cannot run in this toybox, which is logged verbatim |
| H-C6-D | A command-mode DECON needs an explicit fbdev commit before a paint is visible | **OPEN — instrumented in A16** | `NUXEL_FB_UNBLANK_rc` / `NUXEL_FB_ACTIVATE_rc` / `NUXEL_FB_PAN_rc` return codes are now logged; ABOLISHED if the panel is still black with all three rc=0 |
| H-C6-E | The DECON scans a buffer other than the one A14/A15 painted | **OPEN — instrumented in A16** | A16 paints every virtual buffer (max 4) and animates in all of them; `NUXEL_FB_BUFFERS_PAINTED` reports how many |
| H-C6-F | The fbdev memory is scanout for the DECON at all | **OPEN** | if A16 shows a coloured panel, yes; if the panel is still black with `NUXEL_FB_DRAW_SUCCESS`, the scanout source is elsewhere and `decon_initial_display` must be inspected |
| H-C6-G | The A13 `posix_spawn` fallback is not in effect despite the rootfs tag | **OPEN** | local image has no `.nuxel-patches` tag and a third library hash; needs USERDATA readback + on-device library dump |
| H-C6-H | `ERRNO_IS_NOT_SUPPORTED()` does not catch glibc's positive ENOSYS in the patched wrapper | **OPEN** | source-level: inspect `src/basic/errno-util.h` for the 258.11 revision before changing anything |

| H-C6-G | The A13 `posix_spawn` fallback is not in effect despite the rootfs tag | **CONFIRMED, root cause identified** | `libsystemd-core-258.11-1.fc43.so` contains both `exec_spawn` and its own `posix_spawn_wrapper`, but the installer only replaces `libsystemd-shared-*.so`; see ROOT-CAUSE RC-6.4 |
| H-C6-H | `ERRNO_IS_NOT_SUPPORTED()` fails to catch glibc's positive ENOSYS | **REFUTED** | `_DEFINE_ABS_WRAPPER` → `ERRNO_IS_NEG_##name(-ABS(r))`, and `ERRNO_IS_NEG_NOT_SUPPORTED()` includes `-ENOSYS` |
| H-C6-I | A build with `HAVE_PIDFD_SPAWN=0` removes the failure without any source patch | **OPEN, promising** | `process-util.c` `#if HAVE_PIDFD_SPAWN` … `#else` uses plain `posix_spawn()` + caller `cg_attach()` |

---

# CYCLE 7 — hypotheses resolved (2026-10-15)

| # | Hypothesis (cycle 6) | Verdict | Evidence |
|---|---|---|---|
| H1 | A16 reboots itself repeatedly | **REFUTED** | A16 ran 168 s; only reset is `sec_hard_reset_hook` (operator). A16-POSTMORTEM §3 |
| H2 | The penguin loop hides a bootloop | **REFUTED** | one boot session in the ram console; systemd reached `basic.target` behind the animation |
| H3 | The A13 `pidfd_spawn` patch was never installed | **REFUTED** | rootfs library hash == A13 artifact hash; `posix_spawn@plt` present in the loaded `.so` |
| H4 | A marker file can be trusted as proof of deployment | **REFUTED** | the marker was accurate *by luck*; A17 replaces it with SHA-256+ELF verification + post-install re-verification |
| H5 | Something *else* fails in the spawn path after `posix_spawn()` succeeds | **CONFIRMED** | `pidref_set_pid()` → `pidfd_open()` → `ENOSYS`, reproduced offline and on hardware |
| H6 | Merely mounting cgroup2 fixes service attachment | **REFUTED** | the mount existed but was shadowed by the later sysfs mount; A17 mounts it last and verifies the result |
| H7 | The executor never runs at all | **REFUTED** | `sd-executor` ran (its own `Failed at step CGROUP spawning …` lines) and was orphaned |
| H8 | A live USB diagnostic channel is impossible in Nuxel userspace | **REFUTED (design)** | UDC `10c00000.dwc3` + `CONFIG_USB_CONFIGFS_ACM=y`; `nuxel-console` implements it. Hardware proof pending |
