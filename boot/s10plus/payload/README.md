# boot/s10plus/payload — committed S10+ boot payloads

Files here are **inputs to the S10+ BOOT image build**, not build output. They are
committed for the same reason `images/initramfs/bin/toybox` is: the release CI has
to be able to rebuild the *exact* image that runs on the handset, and one of those
inputs cannot be produced on a GitHub runner without a full RPM rebuild.

## `libsystemd-shared-258.11-1.fc43.so`

The kernel-4.14-compatible `libsystemd-shared` for Fedora 43 aarch64
(`pidfd_spawn()` / `pidref` fallbacks, see `tools/s10plus/a17/nuxel-systemd-edit.py`
and `docs/s10plus-autonomous-boot-repair/ROOT-CAUSE.md` §RC-6).

* size    : 5,072,280 bytes
* sha256  : `848149cf4b506aef00c0f777840c8e0b5306b65dcf1ae0a1b8c1a63057b4d981`
* ELF     : `ELF 64-bit LSB shared object, ARM aarch64`, machine 183

`boot/initramfs/init.sh` carries those exact values as constants
(`NUXEL_SD_SHA256` / `NUXEL_SD_BYTES`) and installs this file over
`/usr/lib64/systemd/libsystemd-shared-258.11-1.fc43.so` in the Fedora rootfs at
boot (preserving the original as `.nuxel-orig`), only after re-verifying its
SHA-256 and ELF identity. Without it the Fedora 43 userspace cannot spawn
children on this kernel (A15: 28/28 units died with
`Failed to spawn executor: Function not implemented`).

Produced by `tools/s10plus/a17/build-systemd4.sh` (podman + dnf, Fedora 43
aarch64, patched via `tools/s10plus/a17/nuxel-systemd-edit.py`).

`tools/s10plus/build-a25-initramfs.sh` refuses to build unless this file's
SHA-256 matches `848149cf…`, so a corrupted or swapped blob fails the build
instead of shipping.
