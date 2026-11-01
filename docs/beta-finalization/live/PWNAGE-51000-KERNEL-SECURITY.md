# PWNAGE-51000 — kernel build, security review and TWRP flash record

## Source of truth

- Repo: `https://github.com/Linux4/android_kernel_samsung_exynos9820`
- Commit: `f7194c1d15eded1c2a1a4dc63825b26103435cc0`
- Release: `4.14.253-gf7194c1d15ed-dirty`
- Build tree: exact known-good container tree `/work/src` (same tree that built
  the running `#7` kbase kernel), not `/root/kbuild`.
- Defconfig: `exynos9820-beyond2lte_defconfig`
- Patches: `kernel/s10plus/patches/0005-nuxel-udmabuf-kbase-buffers.patch` and
  the existing `kernel-relax-werror.sh` toolchain relaxations.
- Initramfs: `/work/a25-kbase/initramfs.cpio`,
  `sha256 d10bdb4a09a98ddad667aee9203042a3d9827e0b4ba0bee7a391cbfd70af9a4c`.

## Config delta

```
-# CONFIG_USER_NS is not set
+CONFIG_USER_NS=y
```

Required prerequisites verified in the final Image (extracted IKCONFIG):

```
CONFIG_MULTIUSER=y
CONFIG_NAMESPACES=y
CONFIG_UTS_NS=y
CONFIG_IPC_NS=y
CONFIG_PID_NS=y
CONFIG_NET_NS=y
CONFIG_USER_NS=y
CONFIG_SECCOMP=y
CONFIG_SECCOMP_FILTER=y
CONFIG_CGROUPS=y
CONFIG_MEMCG=y
CONFIG_CGROUP_PIDS=y
CONFIG_UDMABUF=y
CONFIG_DRM=y
CONFIG_MALI_BIFROST_R26P0=y
CONFIG_INITRAMFS_SOURCE="/work/a25-kbase/initramfs.cpio"
```

`CONFIG_OVERLAY_FS` was **not** enabled: Flatpak/Bubblewrap does not require it
for the tested model, and enabling it would add attack surface without need.

## Why the old p50000 artifact was rejected

`/root/pwnage50000/boot14.new.img`:

- `CONFIG_INITRAMFS_SOURCE=""` — the S-Boot kernel relies on the **embedded**
  initramfs, so this image cannot reach userspace (the bootloader ramdisk is not
  executed on this board).
- Release `4.14.253` without `-gf7194c1d15ed-dirty`, so module ABI did not match
  the rootfs.
- No udmabuf driver in that source tree.
- A prior readback was stored as `build/backup/boot-sda14-p50000-bootloop.img`.

It was not reused. The new build keeps the initramfs embedded and the exact live
ramdisk/DTB.

## Security review (4.14.253)

- 4.14 is an old LTS with a large unprivileged-userns attack surface. Enabling
  userns alone is not sufficient for a security claim.
- The running rootfs has SELinux **permissive** (pre-existing; not changed by
  this mission), so SELinux is not a compensating control until that is fixed.
- The device is single-user, but Flatpak apps are untrusted code and would run
  under this userns. A correct deployment must keep the userns count bounded and
  must not use a setuid bwrap fallback.
- `user.max_user_namespaces` and `user.max_mnt_namespaces` are `27213` (kernel
  default, not unlimited). They can be lowered after a working sandbox is proven.
- The actual runtime result is still negative: `unshare -Ur true` returns EPERM.

### Vendor gate

`kernel/user_namespace.c::create_user_ns()` in this tree:

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

`CONFIG_LOD_SEC=y` is set. The root case is rejected without the LOD print
(consistent with `current_chrooted()`); the non-root case would additionally be
blocked by LOD. Kprobe/function_graph instrumentation was unavailable, so this is
a source+behaviour conclusion, not a traced one. `unshare -m/-p/-n/-i/-u` all work,
so namespace support itself is present. This is a vendor policy gate, not a
missing Kconfig option.

A second kernel attempt would need a reviewed patch to this path and a **new
owner-approved flash**. It was not attempted in this run.

## TWRP flash record

- Device: SM-G975F / `beyond2lte`, TWRP 3.7.0_9-2, ADB `R58M75KDB2X`.
- Target: `/dev/block/by-name/boot` -> `/dev/block/sda14`, 57,671,680 bytes.
- Pre-flash SHA: `97f78f5da871ef5df55113814096c9fb0c1de2671b04e11c7edd77630a6bc7da`.
- Image SHA: `574c239c910152fcf8321a132df9c567c8ce63da787fb2f7f0a8300a10b2fa59`.
- Readback SHA matched exactly.
- First boot: PASS (Outcome A), no rollback.
- No unrelated partition was written. No fastboot/Heimdall/Odin was used.

## Rollback

```sh
adb push twrp/sda14.current.img /tmp/
adb shell 'dd if=/tmp/sda14.current.img of=/dev/block/by-name/boot bs=1M; sync'
adb shell 'sha256sum /dev/block/sda14'   # 97f78f5d…
adb reboot
```

Do not retry another kernel without a new build and explicit approval.
