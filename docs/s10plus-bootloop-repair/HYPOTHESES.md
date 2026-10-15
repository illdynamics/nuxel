# Hypotheses (evidence-first)

Format: Hypothesis | Evidence | Confidence | Test | Result

| # | Hypothesis | Evidence | Confidence | Test | Result |
|---|---|---|---|---|---|
| **H1** | S-Boot replaces `/chosen/bootargs` with its own cmdline and drops the Android boot-image header `cmdline` field, so `nuxel.device=s10plus root=... rw` never reaches the kernel | TWRP `recovery.img` header cmdline = `buildvariant=eng` (read of `/dev/block/sda15` offset 64); `/proc/device-tree/chosen/bootargs` == `/proc/cmdline` and contains **no** `buildvariant`; S-Boot log `init_cmdline: default: console=ram loglevel=4`, `avb_cmdline: root=PARTUUID=...`, `dtb_merge_bootargs`, `Updating device tree @0x8a000000: done` | **High** | `adb shell 'cat /proc/device-tree/chosen/bootargs; cat /proc/cmdline'` vs boot-image header | **SUPPORTED** |
| **H2** | With no `nuxel.device=`, Nuxel `/init` takes the generic branch, cannot resolve a root device, and PID 1 reboots (`reboot -f`) → Samsung-logo bootloop | Source `boot/initramfs/init.sh`: `case "${DEVICE}" in mustang\|vm\|"")` → `find_root()` ⇒ probes `/dev/disk/by-partlabel/system*`, `/dev/sda2`, `/dev/sda1`… ; no mountable root → `emergency_shell`, `NUXXEL PANIC`, `sleep 60`, `reboot -f`. Device has **no** `/dev/disk/by-partlabel`; `/dev/sda2` is `bota1` (bootloader) | **High** (static) | Source walk + device partition map | **SUPPORTED (static)** |
| **H3** | The already-merged DTB plus S-Boot's DTBO entry[9] overlay is a *double* application that breaks the tree | `-merged` image embeds base+overlay; S-Boot always applies DTBO entry[9] | Low | `fdtoverlay -i merged.dtb -o out.dtb dtbo9.dtb` then compare | **REJECTED** — output is byte-identical to input (`cmp` clean); overlay re-application is idempotent |
| **H4** | Wrong/placeholder load addresses make S-Boot reject the image | `pack-boot-v1.sh` defaults are placeholders | Low | compare flashed header with TWRP recovery header | **REJECTED** — flashed header kernel=0x10008000 ramdisk=0x11000000 tags=0x10000100, **identical** to TWRP's proven image |
| **H5** | S-Boot rejects the image for lack of AVB/secure-boot signature | `avb_footer.c: ERROR: Footer magic is incorrect` (recovery) | Low | observe that recovery has the same condition and still boots | **REJECTED** — unsigned/custom images boot (orange state, `vbmeta: VERIFICATION_DISABLED`) |
| **H6** | The Fedora rootfs is corrupt / unbootable | `e2fsck -fn` exit 0, clean; `/sbin/init -> ../lib/systemd/systemd`; systemd, phoc, phosh, python3 present; `nuxel:x:1000:1000::/home/nuxel:/bin/bash` | — | offline audit | **REJECTED** (rootfs structurally sound) |
| **H7** | The kernel fails before init (driver/DTB problem) | no Nuxel log available; kernel is the downstream 4.14 Exynos 9820 kernel whose sibling in TWRP boots this unit | Low–Medium | not testable without persistent logs | **UNKNOWN** — cannot be excluded; this is why the fix adds persistent diagnostics |
| **H8** | Phoc/Phosh cannot drive the panel on this kernel | TWRP kernel exposes `/dev/graphics/fb0` only; no `/dev/dri`, no `/sys/class/drm` | **High** | device read (`device/display-state.txt`) | **SUPPORTED** — DRM/KMS absent downstream; blocks Milestone 6 on this kernel |

## Ranking

1. **H1 + H2 are the demonstrated, sufficient explanation** of the bootloop and
   are fixable in Nuxel source without touching the kernel or the DTB.
2. **H7 remains genuinely open** and is the reason any fix must be accompanied by
   persistent instrumentation (USERDATA + BOOT-slack diagnostic log, including
   `dmesg`), so that the next hardware attempt produces evidence of *how far* the
   kernel got — even if the boot still fails.
3. **H8 is a separate, equally serious gap** for the "visible Nuxel interface"
   milestone and is *not* addressed by this repair.
