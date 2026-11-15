# Nuxel S10+ Kernel Patches (Exynos 9820)

These patches target the exact downstream source pinned by
`kernel/s10plus/build-kernel.sh`:

- `https://github.com/Linux4/android_kernel_samsung_exynos9820`
- commit `f7194c1d15eded1c2a1a4dc63825b26103435cc0` (Linux 4.14.253)

The build wrapper now actually processes `*.patch` files in lexical order.
It logs outcomes to `kernel/s10plus/.build/out/patch-application.log`, skips
files explicitly marked `# STUB`, detects already-applied patches, performs a
forward `git apply --check` before applying, and verifies the result with a
reverse check.

A sibling file named `<patch-name>.patch.required` (the full patch filename
plus `.required`) makes failure fatal. Without that marker, a failed patch is
reported as a warning and the build continues. Use `.required` only for a
patch that is mandatory for the artifact being built and has been validated
against the pinned checkout.

## Current patch inventory

- `0001-nuxel-phone-features.patch`: documentation-only stub; intentionally
  skipped by the build wrapper.
- `0003-nuxel-initramfs-delivery-diagnostics.patch`: optional initramfs
  diagnostics patch; applicability is checked during build.
- `0004-nuxel-abox-boot-done-and-bt-hciuart.patch`: optional ABOX boot-done
  and Bluetooth UART patch; applicability is checked during build.

- `0011-nuxel-usb-ncm-idempotent-misc-deregister.patch` (**RETIRED**): the
  first NCM teardown fix only added a boolean around `misc_deregister()`. It
  did not address `ncm_alloc()` running again on every bind, the ignored
  `misc_register()` failure, a second instance deregistering the singleton, or
  `ncm_work()` touching freed state. Superseded by the patch below.
- `0011-nuxel-usb-ncm-lifecycle.patch` (**required**): owns the Samsung
  `CONFIG_USB_ANDROID_SAMSUNG_COMPOSITE` NCM mirrorlink singleton exactly once.
  The vendor code registered a global misc device + work item from
  `ncm_alloc()` (re-run for every bind), ignored `misc_register()` failure, let
  a second instance deregister the shared device, freed `_ncm_dev` while
  `ncm_work()` could still run, and called `misc_deregister()` unconditionally
  from `ncm_free_inst()`.  The recorded panic
  (`configfs_rmdir -> ncm_attr_release -> ncm_free_inst -> misc_deregister`)
  comes from that lifecycle.

  Fix (ownership model): `mirrorlink_users` / `mirrorlink_refs` /
  `mirrorlink_active` guarded by `mirrorlink_lock`; register/deregister run
  outside the spinlock under `mirrorlink_txn`; the last instance clears
  `mirrorlink_active`, waits for in-flight `ncm_alloc()/ncm_free()`, drains the
  work with `cancel_work_sync()`, removes the fix attribute and performs
  exactly one `misc_deregister()`.  `ncm_work()` and `set_ncm_ready()` re-check
  liveness under the lock, `ncm_alloc()` propagates registration failure
  (`ERR_PTR(status)`), and module exit releases the singleton via
  `nuxel_ncm_mod_exit()`.

  Marker: `const char nuxel_ncm_lifecycle_marker[]` (exported) and
  `/sys/class/misc/usb_ncm/nuxel_fix` both return
  `nuxel-ncm-lifecycle-fix-v2`.  `tools/beta/live/nuxel-usb-net.py`,
  `services/nuxel-s10/bin/nuxel-usb-mode.sh` and
  `services/nuxel-bridge/src/tri_link_status.py` require the RUNNING build to
  expose it before creating an NCM function — the 4.14.253 version string is
  not a safety verdict, and there is no override.

  Validation: applies to the pinned commit's pristine `f_ncm.c`, `f_ncm.o`
  compiles with the CI toolchain (no `f_ncm.c` warnings), and the object
  contains the marker in `.rodata` (`R nuxel_ncm_lifecycle_marker`).  Evidence:
  `docs/beta-finalization/live/evidence/pwnage-usbnet-114000/`.  Physical
  create/bind/unbind/remove soak on the handset is still required before the
  combined reflash can be called PASS.

## Important audio note

Do not add an unconditional CS35L41 external-boost speaker-output patch based
only on the fact that the speaker is silent. The upstream
`CSPL_MBOX_CMD_SPK_OUT_ENABLE` sequence is specifically for external-boost
hardware. The actual S10+ board/DT configuration and each amplifier's boost
mode must first be identified. See:

`docs/beta-finalization/live/PWNAGE-40000-AUDIO-ROOT-CAUSE.md`

A future driver patch must port the complete upstream sequencing, firmware
compatibility check, error handling, test-key lock/unlock, and power-up/down
behavior to this exact 4.14.253 driver. Never replace it with userspace writes
to amplifier registers.

## Camera (2026-11-14)

- `0022-nuxel-fimc-is-linux-firmware-paths.patch` (**required**): the pinned
  FIMC-IS loader (`fimc-is-binary.c` `request_binary()`) only opened
  `/system/vendor/firmware/` and `/data/vendor/camera/` before falling back to
  `request_firmware()`. On Nuxel both are absent, so `fimc_is_lib.bin`,
  `fimc_is_rta.bin` and the DDK file could never load from `/lib/firmware`.
  The patch adds `/lib/firmware/` and `/usr/lib/firmware/` as additional file
  paths (Android paths unchanged) and logs every attempt as
  `path-linux load(<path>) ret(<rc>)`. No blob content/name/CRC/ABI check is
  altered.

  The boot rootfs must contain an empty `/lib/firmware` before the camera
  group starts. Blob provenance, hashes and the exact required names are
  documented in `PWNAGE-CAM-FIRMWARE-PROVENANCE.md`; the measurement tool is
  `tools/s10plus/fimc-capture/nuxel-fimc-capture` (drives the FIMC-IS MPLANE
  ioctls, because generic `v4l2-ctl` gets ENOTTY on these nodes).

