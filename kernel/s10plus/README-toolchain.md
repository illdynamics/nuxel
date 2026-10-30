# S10+ Kernel Toolchain (Exynos 9820)

This directory builds the pinned Samsung downstream kernel used by the Nuxel
S10+ target (SM-G975F / beyond2lte), not a postmarketOS mainline kernel.

## Required toolchain

The wrapper defaults to `aarch64-linux-gnu-`. Select an installed cross-GCC
and binutils pair that can build this older Linux 4.14.253 source. The wrapper
probes warning flags and records unsupported options; it does not guarantee
that every modern compiler version is compatible.

Example on Debian/Ubuntu:

```sh
sudo apt install gcc-aarch64-linux-gnu binutils-aarch64-linux-gnu
NUXEL_DEVICE=s10plus bash kernel/s10plus/build-kernel.sh --cross aarch64-linux-gnu-
```

Pass an explicit prefix with `--cross` if your toolchain uses a versioned
name. Do not assume a distro's `aarch64-linux-gnu-10-` naming exists without
checking `command -v` first.

## Authoritative kernel source

- Repository: `https://github.com/Linux4/android_kernel_samsung_exynos9820`
- Commit: `f7194c1d15eded1c2a1a4dc63825b26103435cc0`
- Kernel: Samsung downstream Linux 4.14.253
- Defconfig: `exynos9820-beyond2lte_defconfig`

The wrapper pins this exact commit and stores the checkout at:

`kernel/s10plus/.build/src`

Do not substitute the obsolete/nonexistent `postmarketOS/linux-postmarketos`
`exynos9820` branch. Older references to a close-to-mainline S10+ tree are
historical and do not describe the current build wrapper.

## Patch application

After clone/checkout, `build-kernel.sh` now applies `kernel/s10plus/patches/*.patch`
in lexical order. Its behavior is:

1. Documentation-only stubs beginning with `# STUB` are skipped explicitly.
2. A patch already present is recognized with `git apply --reverse --check`.
3. A clean unapplied patch is checked and applied, then reverse-checked.
4. A failed optional patch is logged as a warning in
   `.build/out/patch-application.log`.
5. A patch with a sibling `<patch-file>.required` marker aborts the build if it
   cannot be applied and verified.

The current 0003/0004 patch files remain optional until their applicability is
verified against the pinned checkout. Do not mark a future CS35L41 driver patch
required until it has been ported and successfully checked against this exact
source revision. The 0001 phone-features file is a documentation stub.

## Build

```sh
NUXEL_DEVICE=s10plus bash kernel/s10plus/build-kernel.sh --clone
```

Outputs (actual paths are also printed by the wrapper):

- `kernel/s10plus/.build/out/arch/arm64/boot/Image.gz`
- matching beyond2lte DTB under `kernel/s10plus/.build/out/arch/arm64/boot/dts/`

The wrapper builds artifacts only. It does not flash a boot image or kernel.

## Safety

- This build is for S10+ only; device selection is checked.
- Do not flash the kernel, boot image or DTB as part of ordinary audio
  deployment. Any boot-image installation requires a separately approved,
  device-specific recovery/rollback plan.
- Do not modify the bootloader, modem, EFS or firmware partitions.
- Keep the current boot image and a verified recovery route intact.
- Preserve the build log, compiler version, source commit and patch-application
  log with every artifact.
