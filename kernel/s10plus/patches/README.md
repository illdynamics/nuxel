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
