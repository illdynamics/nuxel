# G7 Power Kernel Toolchain (SDM632 / msm8953)

Everything you need to build `linux-postmarketos-qcom-msm8953` for the
Motorola Moto G7 Power (XT1955, codename ocean, Snapdragon 632 / SDM632,
msm8953 DT family).

## Required toolchain

- **`aarch64-linux-gnu-` (GCC 10+)** — any modern aarch64 cross GCC works;
  the msm8953-mainline tree is a 5.x-era close-to-mainline tree and builds
  fine with GCC 10 or newer. The build wrapper defaults to
  `CROSS_COMPILE=aarch64-linux-gnu-` (override with `--cross <prefix>` or the
  `CROSS_COMPILE` env var).
- **Alternative: LLVM clang** with an aarch64 target (plus an
  `aarch64-linux-gnu-` binutils set on `PATH` for the assembler/linker, i.e.
  `CROSS_COMPILE=aarch64-linux-gnu-` with `LLVM=1` semantics). This is an
  alternative, not the default; GCC is the commonly used configuration for
  this tree.

Install on Debian/Ubuntu:

```sh
sudo apt install gcc-aarch64-linux-gnu bc bison flex libssl-dev libelf-dev
```

This installs `aarch64-linux-gnu-gcc` under `/usr/bin`, which is exactly the
prefix the build wrapper uses by default.

### macOS

Use a prebuilt `aarch64-linux-gnu` cross toolchain from Homebrew:

```sh
brew tap messense/macos-cross-toolchains
brew install aarch64-unknown-linux-gnu
```

Then pass the matching prefix:

```sh
NUXEL_DEVICE=g7power bash kernel/g7power/build-kernel.sh \
    --cross aarch64-unknown-linux-gnu-
```

## Kernel source

- **Primary:** `msm8953-mainline/linux` (the close-to-mainline Snapdragon
  632 / msm8953 tree used by postmarketOS as
  `linux-postmarketos-qcom-msm8953`):
  `https://github.com/msm8953-mainline/linux`, branch `master`.
  `kernel/g7power/build-kernel.sh --clone` clones it into
  `kernel/g7power/.build/src` (depth 1).

## Building

```sh
NUXEL_DEVICE=g7power bash kernel/g7power/build-kernel.sh --clone
```

What the wrapper does:

1. Verifies the device selection is `g7power` (via
   `tools/nuxel-device-select.sh`) and that the Phase 0 inventory
   (`docs/g7power-device-inventory.md`) has been filled — it refuses to build
   while KERNEL_ADDR / RAMDISK_ADDR / TAGS_ADDR are PLACEHOLDER or
   WIFI_FW_FILENAMES is UNKNOWN.
2. Clones `msm8953-mainline/linux` branch `master` into
   `kernel/g7power/.build/src` (skipped if already present).
3. Applies `kernel/g7power/patches/*.patch` **non-fatally** — a patch that
   does not apply prints a WARN with a per-patch `.README` hint and the build
   continues (see `kernel/g7power/patches/README.md`).
4. Configures with the tree's base defconfig — named `msm8953_defconfig`, or
   a variant of it (SDM632 is part of the msm8953 family; the exact base
   config name is verified against the cloned tree, with a plain `defconfig`
   fallback) — then merges `kernel/g7power/defconfig` on top with
   `scripts/kconfig/merge_config.sh -m` and runs `olddefconfig`.
5. Builds `Image.gz`, the DTBs, and modules with `O=.../.build/out`, then
   installs modules into `kernel/g7power/.build/modules-staging`.

Expected artifacts:

```sh
kernel/g7power/.build/out/arch/arm64/boot/Image.gz
kernel/g7power/.build/out/arch/arm64/boot/dts/qcom/sdm632-motorola-ocean.dtb
kernel/g7power/.build/modules-staging/lib/modules/
```

Flags: `--clone`, `--clean`, `--jobs N`, `--cross <prefix>`, `--help`.
The device is selected explicitly via `NUXEL_DEVICE=g7power` (or
`--device g7power`); any other selection aborts.

## Notes

- **SDM632 = msm8953 family.** The Snapdragon 632 is a member of the msm8953
  DT family, so the base defconfig is named `msm8953_defconfig` or a variant;
  the wrapper tries `msm8953_defconfig` first and falls back to `defconfig`.
- The G7 Power boot image is a **legacy Android boot image header v1** (page
  2048) — see `boot/g7power/pack-boot-v1.sh` and `boot/g7power/boot-config.txt`.
- The device is **A-only** (no A/B slots); partition layout is
  `boot, system, vendor, dtbo, userdata, recovery`.
- Do not build until Phase 0 inventory has been collected
  (`docs/g7power-device-inventory.md`); the build wrapper refuses to run
  while the inventory is incomplete.
- This build never touches `kernel/google-pixel-10-pro-xl/` or
  `kernel/s10plus/` — all artifacts and sources stay under `kernel/g7power/`.
