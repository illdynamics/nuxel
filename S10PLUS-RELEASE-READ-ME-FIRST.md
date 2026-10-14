# Nuxel Galaxy S10+ patched first-light release

**Not production-ready, not a hardware-confirmed boot and not a complete phone UI.**
This repo contains *offline-validated* merged boot + first-light diagnostic
rootfs and a separate builder for a full ARM64 Linux phone userspace.

## Fixed artifacts and boundaries

- `build/out/s10plus/nuxel-beyond2lte-boot-merged-fixed.img` (kernel/DTB
  unchanged, safer initramfs and verified ARM64 `/bin/sh`).
- `build/out/s10plus/nuxel-beyond2lte-rootfs-fixed.img` (static ARM64
  Nuxel first-light display binary, Nuxel Home source, S10+ overlays;
  **NO installed Python/OpenRC/Phosh**, because none of those packages was
  available locally to compile/install without an ARM64 package mirror).
- `images/s10plus/build-phone-rootfs-alpine.sh` can acquire those real native
  ARM64 packages on a connected Mac Docker Desktop/Fedora machine. Its output
  is different from the supplied fixed diagnostic rootfs. Runtime package
  presence does not prove display, bootloader or phone compatibility.

**The Motorola G7 Power / ocean files have been removed from the S10+ fixed
rootfs image**, not from the general multi-device repo. This repo continues to
support the Motorola independently.

The original merged DTB is an **EUR OPEN revision 26** board overlay. It is not
verified against your exact physical device. Heimdall previously reported
100% BOOT and USERDATA transfers, *but* no session-end confirmation. Neither
is proof of a bootable OS or successful flash.

Read `macbook-s10plus-flash-guide-final-full.md` and `S10PLUS-PROGRESS.md` first.
