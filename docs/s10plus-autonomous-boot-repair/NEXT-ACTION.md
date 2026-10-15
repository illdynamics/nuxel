# NEXT-ACTION (after A12)

## Where the boot stands (all hardware-measured)
| Milestone | State |
|---|---|
| 1 S-Boot starts our kernel | ACHIEVED |
| 2 kernel runs + persistent logging | ACHIEVED |
| 3 initramfs unpacks | **ACHIEVED (A7)** — `message=(none) state=7`, twice per boot |
| 4 Nuxel `/init` executes | **ACHIEVED (A8)** — its own lines in the ram console |
| 5 USERDATA discovered | **ACHIEVED (A12)** — `USERDATA_FALLBACK /dev/sda31` |
| 6 Fedora rootfs mounts | **ACHIEVED (A12)** — `EXT4-fs (sda31): mounted filesystem ...` + `ROOTFS_MOUNTED` |
| 7 Fedora userspace runs | HANDOFF STARTED (A12) — `switch_root -> /newroot` executed; nothing observable after it |
| 8-14 (init system, services, display, Phoc, Phosh, UI) | NOT REACHED |

**Root cause of the whole cycle-1/2 blocker (measured, see ROOT-CAUSE.md):** on a
normal BOOT-partition boot S-Boot writes `/chosen/linux,initrd-start = 0x89000000`
and `initrd-end = start + round_up(header ramdisk_size, 2048)` but **never loads
the payload** — the bytes there are the kernel's own console text or zeros. No
container-format change could ever have fixed that. Embedding the initramfs in the
kernel (`CONFIG_INITRAMFS_SOURCE`) removed the handoff from the critical path.

## Immediate next steps (in order)
1. **Open a channel that survives `switch_root`.** Everything after the handoff is
   currently invisible: the kernel log stops at `switching root`, Fedora's systemd
   writes to a `/dev/console` that does not exist on this device, and the shipped
   diagnostics never reached `diag_persist()`. Two cheap options, both
   initramfs-only:
   * write a `pre-handoff` record into the **BOOT partition slack** *unconditionally*
     just before `exec switch_root` (currently only the failure paths persist it),
     so every attempt leaves a readable breadcrumb;
   * have the staged rootfs's `/sbin/init` (or a `sysinit` unit) write to
     `/dev/kmsg` early, which is the only console-independent channel this kernel
     offers.
2. **Verify the root before trusting it.** A12 logged `rootfs os-release: <none>`
   (the mount was `ro`), so the Fedora/Nuxel identity gate had no data and the
   handoff proceeded unverified. Mount read-write, read
   `/usr/lib/os-release` (or `/etc/os-release`), require `Fedora`/`Nuxel`, and only
   then `switch_root`.
3. **Explain two kernel-side oddities** that the logs expose and that will bite the
   rootfs too: `/sys/class/block` is empty (with sysfs mounted) so
   `PARTNAME=userdata` discovery always fails, and `/proc/device-tree` does not
   exist on this arm64 kernel (the DT is readable under `/sys/firmware/devicetree`,
   but `/sys/firmware/devicetree/base` was absent — A9 fell through to the
   `/proc` path). Fixing `/sys/class/block` would restore identity-based
   discovery and remove the need for the `sda31` fallback.
4. **Fedora 43 systemd 258.11 vs Linux 4.14.253** — the known hard risk. It needs
   `>= 5.4` and cgroup v2 (no cgroup v1 support). Before fighting it, prove the
   rootfs with a *small* Fedora binary (`/bin/sh -c 'echo marker > /dev/kmsg'`
   from a diagnostic init) and then choose a supported init strategy while keeping
   Fedora as the distribution. Do not silently swap in Alpine/OpenRC.
5. **Vendor leashes**: the boot is still time-limited — `hard_reset_hook` fires as
   a force-reset key combo (10-75 s in) and `softdog.soft_margin=100
   soft_panic=1` is armed from S-Boot's cmdline. A12 temperes them from userspace
   (`hung_task_panic=0`, 600 s timeout, softdog keeper). If they still cut a valid
   boot short, patch `drivers/samsung/sec_hard_reset_hook.c` in the kernel build
   (the tree and toolchain are now in place and an incremental rebuild is ~90 s).

## Reproducing the pipeline (everything is committed and gated)
```
boot/s10plus/build-candidate.sh --kernel <Image> --initramfs-cpio <cpio> \
    --no-dev-nodes --compress lzma --out <A13/boot.img>       # gate runs automatically
sh boot/s10plus/tests/test-boot-image-gates.sh                 # 11 regression tests
sh boot/s10plus/tests/test-init-cmdline-independence.sh         # 8 tests
kernel/s10plus/patches/0003-nuxel-initramfs-delivery-diagnostics.patch
boot/s10plus/build-kernel-a7-embedded-initramfs.sh             # run inside the container
```
Kernel build host: `podman machine` (now 6 CPU/8 GiB) + container `a7kb2`
(Fedora 43, native aarch64, gcc 15.3.1 = the same compiler as the proven kernel);
sources at `/var/tmp/a7/src` in the VM, artifacts copied back to
`build/out/s10plus/debug-candidates/A{7..12}/`.
**Host caution:** the macOS data volume is 99% full; a nearly-full host silently
truncated files inside the VM twice this cycle. Keep >20 GiB free and re-verify
file sizes after any large copy.

## Standing risks
* No real stock BOOT backup exists (`backups/s10plus/boot-original.img` is a
  `DUMMY`). RECOVERY is untouched and backed up; every write this cycle was
  BOOT-only, and USERDATA has never been written.
* `Freeing initrd memory: <N>K` reports reclaimed pages only — it is not evidence
  that our payload was delivered. The KDIAG lines are the evidence.
