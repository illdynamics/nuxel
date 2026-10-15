# Phase 2/3 — boot-failure analysis and exact failure stage

## Stage-by-stage determination

| Stage | Question | Verdict | Basis |
|---|---|---|---|
| **A — Samsung S-Boot** | Does S-Boot accept and launch the Nuxel image? | **Probably YES; structure and load parameters are correct.** The only structural deviation (pre-merged DTB vs. S-Boot's DTBO overlay) is proven harmless | Flashed BOOT header: `ANDROID!`, page 2048, kernel_addr `0x10008000`, ramdisk_addr `0x11000000`, tags `0x10000100`, dt_size 376101 — kernel/ramdisk/tags addresses are **byte-identical to TWRP's recovery.img, which this unit boots**. Image size 22,431,744 ≤ BOOT partition 57,671,680. Unsigned/custom images boot here (orange state, `vbmeta: VERIFICATION_DISABLED bit is set`). Merged-DTB + DTBO[9] re-application is idempotent (`cmp` clean) |
| **B — Linux kernel** | Does the kernel start? | **Unknown; most likely yes.** No Nuxel log survived (S-Boot clears the log buffer on the next boot) | Kernel is the downstream Samsung 4.14 Exynos 9820 `Image.gz` (44,980,232 B) whose sibling (TWRP's 44,838,924 B kernel) boots this exact unit and drives UFS + panel. Kernel cmdline actually used is the bootloader's, which includes `console=ram loglevel=4` |
| **C — initramfs `/init`** | Does `/init` find the root? | **NO — this is the demonstrated failure point** | `/init` (= `boot/initramfs/init.sh`) selects the device from `nuxel.device=` on the cmdline. That parameter is dropped by S-Boot (Stage A finding), so `DEVICE=""` → generic branch → `find_root()` probes `/dev/disk/by-partlabel/system*` (absent on this unit), `/dev/sda2` (`bota1`), `/dev/sda1` (`bota0`)… → no ext4 root → `emergency_shell` → `sleep 60` → `reboot -f` |
| **D — Fedora rootfs / systemd** | Would the handoff work? | **Not reached; prerequisites look sound** | `e2fsck -fn` clean (21571/262144 files, exit 0); `/sbin/init` → `../lib/systemd/systemd` (0755, 201,024 B); systemd units, phoc, phosh, python3.14 present; `/etc/passwd` has `nuxel:x:1000:1000::/home/nuxel:/bin/bash`; `/home/nuxel` 0700 nuxel:nuxel. `/etc/fstab` absent (non-fatal for systemd) |
| **E — display / Nuxel shell** | Would the panel come up? | **Blocked separately** | Recovery kernel has no `/dev/dri`, no `/sys/class/drm`, only `/dev/graphics/fb0`. Phoc/Phosh require DRM/KMS ⇒ cannot start on the downstream 4.14 kernel. Also `greetd` config still points at `agreety --cmd /bin/sh` (no `[initial_session]` for Phosh) |

## The failure chain (chain of evidence)

1. Flashing wrote the exact bytes (already proven by readback) — so the outcome is
   decided by the boot chain, not by transfer integrity.
2. Nuxel's boot image carries its whole configuration in the header `cmdline`
   (`boot/s10plus/boot-config.txt`: `cmdline_base="buildvariant=userdebug
   nuxel.device=s10plus"`, `cmdline_root="root=/dev/block/platform/13d60000.ufs/by-name/userdata
   rootfstype=ext4 rootwait rw"`; `tools/s10plus/patch-boot-from-upload.py`
   preserves `header_cmdline` verbatim).
3. S-Boot does not propagate that field. Proof: TWRP's own recovery image declares
   `cmdline='buildvariant=eng'`, yet the kernel's cmdline — `/proc/device-tree/chosen/bootargs`,
   which is exactly what S-Boot wrote into the DTB — contains no `buildvariant`
   token at all, and equals `/proc/cmdline` token-for-token. S-Boot instead
   constructs its own: `console=ram loglevel=4 sec_debug.* sec_watchdog.*
   androidboot.* oops=panic softdog.soft_margin=100 softdog.soft_panic=1
   root=PARTUUID=…`.
4. Therefore Nuxel's kernel receives a cmdline with **neither `nuxel.device=s10plus`
   nor `root=`**.
5. `/init` then warns `nuxel-init: [warn] no nuxel.device= on cmdline; assuming
   generic ARM64` (that exact warn/err path exists in `boot/initramfs/init.sh`)
   and enters the generic `mustang|vm|""` branch.
6. `find_root()` cannot produce a mountable root on this device: there is no
   `/dev/disk/by-partlabel` directory, and the only early `/dev/sdaN` candidates
   are bootloader/LUN partitions. Mount fails, `mountpoint -q` fails →
   `emergency_shell` → `echo "=== NUXXEL PANIC: root mount failed ==="` /
   `no root block device found` → `sleep 60` → `reboot -f`.
7. `reboot -f` re-enters S-Boot, which redraws the Samsung logo
   (`drawimg ... 'logo.jpg'`) — the user sees exactly "bootloop at the Samsung
   logo". If instead the kernel or `/init` simply wedged, the Samsung softdog
   (`soft_margin=100`) would reboot it and produce the same visible symptom.

## Why no kernel log could be retrieved

- The Samsung persistent log buffer is **cleared at the next S-Boot run**
  (`[SECD] sec_debug_init_buffer: this is PIN RESET, clear all`, wiping
  `first2m_kmsg`), so a failed Nuxel boot leaves nothing behind after the user
  forces the phone back into TWRP.
- ramoops/`pstore` exists but with `console_size=0` on this kernel — no
  `console-ramoops` records, `/sys/fs/pstore` empty.
- Consequence: absence of a Nuxel panic log is **not** evidence that the kernel
  never started, and no panic may be invented.

## Correction required (smallest sufficient change)

Make the boot flow **independent of the kernel cmdline** and make it
**self-observing**:

1. `/init` must self-identify the platform from the device tree
   (`/proc/device-tree/model` / `compatible` ⇒ exynos9820/beyond2lte ⇒ s10plus)
   when `nuxel.device=` is absent. This alone converts the failing generic branch
   into the s10plus branch, which already resolves USERDATA by the kernel-provided
   `PARTNAME=userdata` uevent (verified present: `/sys/class/block/sda31/uevent`
   contains `PARTNAME=userdata`) — i.e. verified partition identity, not a
   hard-coded `/dev/sda31`.
2. Never let a failure be silent: persist a boot diagnostic record to USERDATA
   **and** to the unused tail of the BOOT partition (readable with `dd` alone),
   including `/proc/cmdline`, the device-tree model, the block-device map, mount
   results and `dmesg` (the kernel ring buffer ⇒ hard evidence of kernel
   execution on the next attempt).
3. Keep the merged-DTB strategy unchanged (proven idempotent) and change nothing
   about DTBO, kernel, load addresses or the Fedora rootfs.
