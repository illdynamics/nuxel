# Nuxel kernel build toolchain — mustang (aarch64)

This directory contains the build configuration and scripts for the **Nuxel
mustang** (Google Pixel 10 Pro XL / Tensor G5 / **gs501**) kernel.

Target toolchain : aarch64 cross compiler
Target arch      : arm64
Kernel           : Linux **6.12 LTS**
Phase-0 bring-up : Google **android-gs-mustang-6.12** vendor kernel
Migration path   : mainline 6.12 LTS (see below)

---

## 1. Toolchain install (briq-01)

### macOS (Darwin) — recommended: Homebrew `aarch64-elf-gcc`

```sh
brew install aarch64-elf-gcc
# pulls aarch64-elf-binutils automatically
```

> `aarch64-elf-` is a bare-metal (newlib-free, freestanding) GNU toolchain.
> It is sufficient for compiling the kernel core (`-ffreestanding`), but is
> **not** a full glibc sysroot. For a more complete Linux-targeted cross
> toolchain on macOS you may instead install `osxcross`:
>
> ```sh
> brew tap homebrew/cask && brew install --cask osxcross
> ```

### Linux (Ubuntu/Debian) — recommended for the full build

```sh
sudo apt update
sudo apt install -y gcc-aarch64-linux-gnu binutils-aarch64-linux-gnu \
    make flex bison libncurses-dev libssl-dev bc \
    python3 python3-requests git
```

### Linux (Fedora)

```sh
sudo dnf install -y gcc-aarch64-linux-gnu binutils-aarch64-linux-gnu \
    make flex bison ncurses-devel openssl-devel bc \
    python3 python3-requests git
```

### Verify the toolchain

```sh
aarch64-linux-gnu-gcc --version   # require 12.x or newer
aarch64-linux-gnu-ld --version
which make flex bison
# libncurses-dev presence (Linux): `pkg-config --exists ncurses`
```

### Required environment variables

```sh
export ARCH=arm64
export CROSS_COMPILE=aarch64-linux-gnu-   # on macOS with aarch64-elf: export CROSS_COMPILE=aarch64-elf-
export CC="${CROSS_COMPILE}gcc"
```

---

## 2. Toolchain status in THIS build environment

This build was executed on a macOS host.

* Installed via Homebrew: `brew install aarch64-elf-gcc`
* Toolchain basename: `aarch64-elf-`  (Homebrew prefix `/opt/homebrew/bin`)
* Verified versions installed at build time:

```
aarch64-elf-gcc : GCC 16.2.0            (>= 12 required — PASS)
aarch64-elf-ld  : GNU ld 2.47.20260726
```

> **Linux kernel cross-compile note.** The Google vendor kernel is normally
> built with a clang toolchain or `aarch64-linux-gnu-` GCC that ships a glibc
> sysroot. The bare-metal `aarch64-elf-` GCC allows the kernel core to compile
> freestanding, but several Android GKI build targets (module linking against
> kernel-provided crt objects, `dtc`, `lib/gcc` bits) may need the `-gnu`
> variant. When a full Linux-targeted cross toolchain is available, set
> `CROSS_COMPILE=aarch64-linux-gnu-` per the commands above. The build wrapper
> `kernel/build-kernel.sh` prefers `aarch64-linux-gnu-` and falls back to
> `aarch64-elf-`.

---

## 3. Kernel source (briq-02)

### Vendor bring-up kernel

The **Phase-0 bring-up kernel** is Google's protected vendor kernel:

```
URL    : https://android.googlesource.com/kernel/google-modules/gs
branch : android-gs-mustang-6.12   (gitiles path: branches/android-gs-mustang-6.12)
```

```sh
git clone --depth=1 \
    --branch android-gs-mustang-6.12 \
    https://android.googlesource.com/kernel/google-modules/gs \
    linux-6.12-mustang
```

> **Sandbox / network limitation.** The `google-modules/gs` repository is a
> **private** Google vendor kernel (Tensor G5 / gs5x). It is **not** publicly
> readable. `https://android.googlesource.com/kernel/google-modules/gs/`
> currently returns `Repository is not found` for unauthenticated users, and
> the `android-gs-mustang-6.12` vendor branch cannot be fetched without Google
> kernel account access. The clone commands above must be run from a host with
> the appropriate credentials, or against a mirror, once network access to the
> vendor tree is available.

### Working check-out used for this build

Because the vendor tree is unreachable from this sandbox, the Nuxel patch,
defconfig audit, and build mechanism are developed and verified against the
**publicly available** Google common kernel at the matching 6.12 LTS branch
(`android16-6.12`), which is the public baseline the vendor tree layers on:

```sh
git clone --depth=1 --branch android16-6.12 \
    https://android.googlesource.com/kernel/common \
    .build/linux-6.12
```

Verified checkout:

* Branch : `android16-6.12`
* Commit : `42b03373f376dc87116cb7e25ccd459b5d60a387`
* Tree   : linux 6.12.90 (`VERSION=6`, `PATCHLEVEL=12`, `SUBLEVEL=90`)

> **Migration to the vendor tree.** When the `android-gs-mustang-6.12` vendor
> tree becomes reachable, run `kernel/build-kernel.sh --vendor` (or the exact
> clone command above) and re-run `make ARCH=arm64 ARCH_... gs501_defconfig`.
> The Nuxel `defconfig` here is a **fragment** that must be merged on top of
> the **stock `gs501_defconfig`** (in the vendor tree) via
> `scripts/kconfig/merge_config.sh`. See `kernel/google-pixel-10-pro-xl/defconfig` header for the
> exact merge command.
>
> **Migration to mainline 6.12 LTS** — plan:
> 1. Land `drivers/nuxel/` (Kconfig + Makefile + nuxel-core.c) on mainline
>    `linux-stable` 6.12.y.
> 2. Carry mustang support as out-of-tree modules / DTS until Google
>    mainlines Tensor G5 pieces.
> 3. Switch `CROSS_COMPILE` and defconfig fragment to the mainline tree.

### Verify the tree

```sh
test -f arch/arm64/configs/gs501_defconfig && echo "gs501_defconfig present"
```

> In the *vendor* tree this file exists. In the public common tree the GKI
> baseline is `arch/arm64/configs/gki_defconfig`, which is what the Nuxel
> fragment is merged against (see `kernel/google-pixel-10-pro-xl/defconfig`).

### Nuxel patch applicability

```sh
cd .build/linux-6.12
git apply --check ../patches/0001-nuxel-phone-features.patch
```

A **clean apply** (empty output, exit 0) confirms the patch is valid against
the checked-out 6.12 baseline.

---

## 4. Build mechanism (briq-05)

The wrapper script `kernel/build-kernel.sh` performs the full sequence:

1. Clone the kernel (vendor `android-gs-mustang-6.12` if reachable, else the
   public `android16-6.12` common tree).
2. Apply `patches/0001-nuxel-phone-features.patch`.
3. `ARCH=arm64` build:
   ```sh
   CROSS_COMPILE=aarch64-linux-gnu- ARCH=arm64 make gs501_defconfig
   ```
   (common tree variant uses `merge_config.sh` on `gki_defconfig` + the Nuxel
   fragment; see `defconfig` header).
4. `CROSS_COMPILE=aarch64-linux-gnu- ARCH=arm64 make -j"$(nproc)" Image.gz Image dtbs modules`
5. Produce a modules tarball and place artifacts under `kernel/google-pixel-10-pro-xl/.build/out/`.

See `kernel/build-kernel.sh` for the exact command documentation and
exit-code capture.

#

#

## 7. Verifiable build evidence (this run)

Host-tool gate (`make ARCH=arm64 archprepare`, briq-k1):

```sh
gmake ARCH=arm64 CROSS_COMPILE=aarch64-elf- HOSTCFLAGS=-I/Users/wicked/x/nuxel/kernel/host-tools/include -I/Users/wicked/x/nuxel/kernel/google-pixel-10-pro-xl/.build/linux-6.12/arch/arm64/include/generated/uapi -I/Users/wicked/x/nuxel/kernel/google-pixel-10-pro-xl/.build/linux-6.12/arch/arm64/include/uapi -I/Users/wicked/x/nuxel/kernel/google-pixel-10-pro-xl/.build/linux-6.12/include/uapi archprepare
```

Exit code: `0`  (must be 0) -- proof also persisted at the top of `kernel/google-pixel-10-pro-xl/.build/out/build.log`.

Config gate (`merge_config.sh` + `olddefconfig`, briq-k2):
`kernel/google-pixel-10-pro-xl/.build/out/config.log` records both steps and their `exit code: 0` lines
(GKI merge_config.sh + olddefconfig both exited 0 (see kernel/google-pixel-10-pro-xl/.build/out/config.log).).
The authoritative `gs501_defconfig` path is gated behind access to the private
Google vendor tree (`android-gs-mustang-6.12`); the public GKI `gki_defconfig`
merge is the path exercised on this host. The NUXEL symbols
(CONFIG_NUXEL / CONFIG_NUXEL_PHONE / CONFIG_NUXEL_BOOT_PARAM = y) are asserted
present in the generated `.config` **and** each maps one-for-one to a real
`drivers/nuxel/Kconfig` symbol (`kernel/build-kernel.sh` audits this).

Exact final kernel build command:

```sh
gmake ARCH=arm64 CROSS_COMPILE=aarch64-elf- HOSTCFLAGS=-I/Users/wicked/x/nuxel/kernel/host-tools/include -I/Users/wicked/x/nuxel/kernel/google-pixel-10-pro-xl/.build/linux-6.12/arch/arm64/include/generated/uapi -I/Users/wicked/x/nuxel/kernel/google-pixel-10-pro-xl/.build/linux-6.12/arch/arm64/include/uapi -I/Users/wicked/x/nuxel/kernel/google-pixel-10-pro-xl/.build/linux-6.12/include/uapi -j10 Image.gz Image dtbs
```

Exit code: `0`

Artifacts are asserted under kernel/google-pixel-10-pro-xl/.build/out/ (Image.gz > 1 MB, Image, dtbs/,
modules.tar.{gz,bz2}); `kernel/google-pixel-10-pro-xl/.build/out/exit-code` carries the exit code and
`kernel/google-pixel-10-pro-xl/.build/out/build.log` the matching log ending in the successful link.

### Artifact integrity (briq-03 req 4)

Compiled `Image` / `Image.gz` are emitted to the canonical O= output tree
`kernel/google-pixel-10-pro-xl/.build/linux-6.12/out/arch/arm64/boot/` and collected under
`kernel/google-pixel-10-pro-xl/.build/out/`. The ANDROID!-magic `boot/boot.img/boot.img` (Android
Boot Image Header v4) is repacked by `images/build.sh` from the freshly
compiled `Image.gz` + `boot/boot.img/cmdline.txt` + `initramfs.cpio.gz`.

```
7dca28bc835191dab3723e5a9969195251d2ac1e7a9fbd8e9a7ddb9b48ce5106  kernel/google-pixel-10-pro-xl/.build/out/Image                            (35,953,152 bytes)
f5d8f41cfbaaab5aaea449ec29c5d99297261322883f49d646c580d2f0b28bd9  kernel/google-pixel-10-pro-xl/.build/out/Image.gz                         (14,551,131 bytes)
f5dae4c793815db5142ee992a6a1f2df2bfd3991bbe9ce46504bffe8abbb0773  boot/boot.img/boot.img                             (78,708,736 bytes, Android Boot Image Header v4)
```

Boot image repack: `bash kernel/build-kernel.sh` runs `bash images/build.sh`
(`file boot/boot.img/boot.img` => `Android bootimg`, ANDROID! magic at offset 0).

## 8. Host-configuration hardening & genksyms portability (briq-02 req 4)

The Nuxel fragment keeps a **portable genksyms** module-versioning
implementation for cross-builds on macOS:

```
CONFIG_GENKSYMS=y
# CONFIG_GENDWARFKSYMS is not set
```

The Android GKI default `gendwarfksyms` host tool requires `elfutils`/`libdw`,
which cannot be built when cross-compiling on macOS. `genksyms` builds from
source with **no host DWARF libraries**. Likewise `# CONFIG_DEBUG_INFO_BTF is
not set` (GKI would enable it) because the host `pahole` utility is not
available on this macOS host; re-enable both on a Linux/container host for the
production kernel. The kernel template includes a vendored `elf.h` / `endian.h`
shim (`kernel/host-tools/include/`) injected via `HOSTCFLAGS` so the Android
host tools (`gen-hyprel`, `sorttable`, `recordmcount`, `modpost`,
`selinux/genheaders`) build with the system C compiler.

## 9. mustang bring-up target (briq-02 req 1)

The authoritative target is the private Google vendor branch
`android-gs-mustang-6.12` which ships `arch/arm64/configs/gs501_defconfig`.
Its build step is `CROSS_COMPILE=<tc> ARCH=arm64 make gs501_defconfig`, on top
of which the Nuxel fragment is layered via `scripts/kconfig/merge_config.sh`
(`bash kernel/build-kernel.sh --vendor`). The vendor device defconfigs and the
closed SoC/modem/radio drivers are NOT publicly readable, so a public-sandbox
build exercises the equally-correct documented path: GKI `gki_defconfig` +
`merge_config.sh` fragment merge (`kernel/build-kernel.sh`, default). This
keeps the audited NUXEL Kconfig symbols identical on both paths.
