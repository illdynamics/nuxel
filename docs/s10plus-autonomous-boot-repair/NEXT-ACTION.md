# NEXT-ACTION (after A13 is flashed)

## Where the boot stands (hardware-measured unless marked)

| Milestone | State |
|---|---|
| 1 S-Boot starts our kernel | ACHIEVED |
| 2 kernel runs + persistent logging | ACHIEVED |
| 3 initramfs unpacks | ACHIEVED (A7) |
| 4 Nuxel `/init` executes | ACHIEVED (A8) |
| 5 USERDATA discovered | ACHIEVED (A12) |
| 6 Fedora rootfs mounts | ACHIEVED (A12) |
| 7 `switch_root` → Fedora PID 1 | ACHIEVED (A12) |
| 8 systemd reaches `basic.target` | ACHIEVED (A12) |
| 9 exact ENOSYS cause | **ACHIEVED, source-exact** (cycle 4) — measured on hardware by A13 |
| 10 a core service really runs | A13 |
| 11 Fedora binary executes | A13 |
| 12 first light executes / panel shows it | A13 |
| 13 Phoc / Phosh / phone UI | BLOCKED: `# CONFIG_DRM is not set` |

## The A13 candidate

* `build/out/s10plus/debug-candidates/A13/boot.img`
  `sha256 bdc06dfe8a8cabe2de904e6224403741eb43fcd1d36eb491e699911f090df086`
  (50,604,032 B, partition slack 7,067,648 B, gate PASS)
* `Image-A13` `sha256 aa28769a95303ce42e79ecc212936418f27a5b68a6631ee8f0b95abac7871bd7`
* `initramfs.cpio` `sha256 f1333d79e403dcd0ad832db6eb6af1184b566eb42913b25b69e7a30ef498bc96`
* carries `opt/nuxel/libsystemd-shared-258.11-1.fc43.so`
  `sha256 502507a7b6237a03cfcff49e389d2a38836916abdea40e36e5ba4653e9bc1234`
  (rebuilt from `systemd-258.11-1.fc43.src.rpm`, fallback verified present by
  disassembly: `posix_spawn_wrapper` now calls `posix_spawn@plt` as well as
  `pidfd_spawn@plt`)

A13 is **BOOT-only**: the kernel source, defconfig, board-revision-26 DTB and
header layout are unchanged from A12; the sole kernel difference is the embedded
initramfs. USERDATA is not written; the repair is copied into the mounted rootfs
at boot, with the original library preserved as `…so.nuxel-orig`.

## Reading the A13 result

Everything the attempt proves lands in the Samsung ram console, readable as
`/proc/last_kmsg` from TWRP. Look for, in order:

1. `NUXEL_MARKER SYSCALL_PROBE_DONE` and the `NUXEL-SYSCALL …` table
   (`waitid(P_PIDFD…)`, `clone3`, `pidfd_open`, `clone(PIDFD)`,
   `clone(SIGCHLD)+execve(/bin/sh)`, `fsopen`, `fspick`, `open_tree`, `memfd_create`).
2. `ROOTFS_IDENTITY_RAW … text='…Fedora…'` and `NUXEL_MARKER ROOTFS_IDENTITY_OK`.
3. `ROOTFS_MOUNTED /dev/sda31 ext4 rw` (rw, not ro).
4. `NUXEL_MARKER SPAWN_PROBE_STATIC_RAN` + `SPAWNPROBE-STATIC …` lines, then
   `NUXEL_MARKER FEDORA_BINARY_EXECUTED` + `FEDORA_EXEC -> FEDORA_EXEC_OK …`, then
   `NUXEL_MARKER SPAWN_PROBE_RAN` + `SPAWNPROBE … pidfd_spawn … rc=38 ENOSYS`.
5. `NUXEL_MARKER SYSTEMD_PATCH_INSTALLED` (or `…_PRESENT` on a re-boot).
6. `FIRSTLIGHT …` lines, `NUXEL_MARKER FIRSTLIGHT_FRAME_WRITTEN`.
7. `NUXEL_MARKER ROOTFS_HANDOFF_STARTED`, then systemd again — and this time
   `systemd-journald.service` / `dbus-broker.service` / `systemd-udevd.service`
   should **start** instead of failing with `Function not implemented`.

Interpretation rules:

* `pidfd_spawn … rc=38 ENOSYS` **plus** `posix_spawn … rc=0` is the measurement
  that closes milestone 9 and justifies the repair.
* If services still fail after `SYSTEMD_PATCH_INSTALLED`, the next blocker is a
  *different* one; read the exact errno and unit before changing anything.
* If the first-light program exits 0 but the panel does not change, that is a
  display-driver result, not a process-execution result, and must be recorded as
  such.
* If the phone returns to TWRP: record `BOOT_RESULT=FAILED_USER_RETURNED_TO_TWRP`,
  capture `last_kmsg` + pstore into
  `scripts/s10plus-debug-pack/captures/<stamp>-A13-postfail/`, compare against A12
  and continue.

## If systemd services now start, the next questions in order

1. Does the boot reach `multi-user.target` / a login prompt, or does it stall on a
   unit that needs a cgroup-v2 or BPF feature this 4.14 kernel lacks?
2. `/sys/class/block` is empty with sysfs mounted, so `PARTNAME=userdata`
   discovery always fails and the `sda31` fallback carries the boot. Fix or
   permanently document.
3. Rootfs writability: `/etc/machine-id` exists, `/etc/fstab` does not. Decide
   whether to add one (and what systemd should remount).
4. Then, and only then, the compositor question: **this kernel has no DRM/KMS**
   (`# CONFIG_DRM is not set`), so Phoc/Phosh cannot run. Milestones 15-16 need a
   5.4+ Exynos 9820 port that keeps UFS, rev-26 DTB, DECON/DSIM, AMOLED, panel
   power, USB and touchscreen working (Option C in the mission). That is an
   engineering project, not a version bump, and it must not replace the
   known-executing 4.14 kernel until the listed hardware is demonstrated.

## Reproducing this cycle's pipeline (all committed and gated)

```
# 1. systemd repair (Fedora 43 aarch64, in container sd258)
.scratch/s10plus-cycle4/a13/build-systemd3.sh      # -> out3/libsystemd-shared-patched.so
# 2. probes
.scratch/s10plus-cycle4/a13/build-probes.sh        # -> probes/nuxel-spawn-probe{,-static}
aarch64-linux-gnu-gcc -O2 -static -nostdlib -ffreestanding -fno-stack-protector \
    -fno-builtin -Wl,-e,_start -o tools/s10plus/nuxel-syscall-probe \
    tools/s10plus/nuxel-syscall-probe.c
# 3. init script (anchored, fails loudly on a missing anchor)
python3 .scratch/s10plus-cycle4/a13/edit-init.py
# 4. initramfs + kernel + container
sh .scratch/s10plus-cycle4/a13/build-a13-initramfs.sh
#    (in container a7kb2) /b/kbuild-a13.sh          -> Image-A13
boot/s10plus/build-candidate.sh --kernel …/A13/Image-A13 \
    --initramfs-cpio …/A13/initramfs.cpio --init none --no-dev-nodes \
    --compress lzma --out …/A13/boot.img
# 5. tests
sh boot/s10plus/tests/test-boot-image-gates.sh          # 11 tests
sh boot/s10plus/tests/test-init-cmdline-independence.sh # 8 tests
```

## Standing risks
* No real stock BOOT backup exists. RECOVERY untouched; every write is BOOT-only.
* A12 remains the regression baseline and is never overwritten.
