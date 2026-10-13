# S10+ Kernel Toolchain (Exynos 9820)

Everything you need to build `linux-postmarketos-exynos9820` for the
Samsung Galaxy S10+ (SM-G975F, codename beyond2lte, Exynos 9820).

## Required toolchain

- **`aarch64-linux-gnu-gcc-10`** — the same GCC 10 requirement as
  `chiffathefox/u-boot` (branch `exynos9820`, `exynos9820_defconfig`). Use
  GCC 10, not a newer default GCC: the Exynos 9820 vendor/pmOS trees are
  built and tested with GCC 10, and the U-Boot chainload image for this SoC
  is also built with `gcc-10`. A newer GCC may work but is not the tested
  configuration.

Install on Debian/Ubuntu:

```sh
sudo apt install gcc-10-aarch64-linux-gnu
```

This installs `aarch64-linux-gnu-gcc-10` under `/usr/bin`. The build wrapper
defaults to `CROSS_COMPILE=aarch64-linux-gnu-`, which makes the kernel build
invoke `aarch64-linux-gnu-gcc`. On Debian/Ubuntu that name is an
`update-alternatives` symlink — point it at the GCC 10 binary:

```sh
sudo update-alternatives --install \
    /usr/bin/aarch64-linux-gnu-gcc aarch64-linux-gnu-gcc \
    /usr/bin/aarch64-linux-gnu-gcc-10 10
```

or simply pass an explicit prefix to the wrapper:

```sh
NUXEL_DEVICE=s10plus bash kernel/s10plus/build-kernel.sh --cross aarch64-linux-gnu-10-
```

(The `aarch64-linux-gnu-10-` prefix is only valid if your distro provides
version-suffixed `aarch64-linux-gnu-*-10` binaries; adjust to whatever your
installation actually provides. `CROSS_COMPILE` env var works the same way.)

### macOS

Use a prebuilt `aarch64-linux-gnu` cross toolchain from Homebrew:

```sh
brew tap messense/macos-cross-toolchains
brew install aarch64-unknown-linux-gnu
```

Then pass the matching prefix:

```sh
NUXEL_DEVICE=s10plus bash kernel/s10plus/build-kernel.sh \
    --cross aarch64-unknown-linux-gnu-
```

### Clang alternative

If you prefer clang/LLVM, you can drive the build with
`CROSS_COMPILE=clang` (plus `LLVM=1` semantics) as long as you have an
`aarch64-linux-gnu-` binutils set on `PATH`. This is an alternative, not the
default; the pmOS tree and U-Boot are commonly built with GCC 10.

## Kernel source

- **Primary:** `linux-postmarketos-exynos9820` from postmarketOS GitHub:
  `https://github.com/postmarketOS/linux-postmarketos`, branch `exynos9820`.
  This is the close-to-mainline Exynos 9820 tree used for the Nuxel S10+
  bring-up (mainline DRM/DSI, Panfrost for Mali-G76, UFS, etc.).
  `kernel/s10plus/build-kernel.sh --clone` clones it into
  `kernel/s10plus/.build/src`.

- **Alternative (reference only):** Samsung Open Source Release Center (OSRC):
  `https://opensource.samsung.com` — search for **SM-G975F** and download the
  Exynos 9820 kernel source tarball. This is the vendor (Android) kernel and
  is NOT required for the Nuxel Phase 1 bring-up; it is a fallback reference
  for driver/firmware details. OSRC tarballs must be downloaded manually by
  the operator — the build wrapper never fetches them.

## Building

```sh
NUXEL_DEVICE=s10plus bash kernel/s10plus/build-kernel.sh --clone
```

What the wrapper does:

1. Clones `linux-postmarketos` branch `exynos9820` into
   `kernel/s10plus/.build/src` (skipped if already present).
2. Applies `kernel/s10plus/patches/*.patch` **non-fatally** — a patch that
   does not apply prints a WARN with a per-patch `.README` hint and the build
   continues (see `kernel/s10plus/patches/README.md`).
3. Merges `kernel/s10plus/defconfig` on top of the tree's
   `exynos9820_defconfig` with `scripts/kconfig/merge_config.sh -m`, then
   runs `olddefconfig`.
4. Builds `Image.gz` and the device trees with `O=.../.build/out`:

```sh
kernel/s10plus/.build/out/arch/arm64/boot/Image.gz
kernel/s10plus/.build/out/arch/arm64/boot/dts/exynos/exynos9820-beyond2lte.dtb
```

Flags: `--clone`, `--clean`, `--jobs N`, `--cross <prefix>`, `--help`.
The device is selected explicitly via `NUXEL_DEVICE=s10plus` (or
`--device s10plus`); any other selection aborts.

## Notes

- The S10+ boot image is a **legacy Android boot image header v1** (page
  2048) — see `boot/s10plus/pack-boot-v1.sh` and `boot/s10plus/boot-config.txt`.
- Flash tooling for the S10+ is TWRP (adb + dd) and Download Mode
  (Odin/heimdall). There is no Android-bootloader-mode flashing on Exynos.
- Do not flash the kernel until Phase 0 inventory has been collected
  (`docs/s10plus-device-inventory.md`); the build wrapper refuses to run
  while the inventory is incomplete (KERNEL_ADDR / RAMDISK_ADDR / TAGS_ADDR /
  WIFI_FW_FILENAME still PLACEHOLDER/UNKNOWN).
- This build never touches `kernel/google-pixel-10-pro-xl/` — all artifacts
  and sources stay under `kernel/s10plus/`.
