#!/usr/bin/env bash
# =============================================================================
# build-kernel-a7-embedded-initramfs.sh — rebuild the S10+ kernel with a
# built-in initramfs (CONFIG_INITRAMFS_SOURCE) plus initramfs-delivery
# diagnostics, and emit a raw arm64 Image for the BOOT container.
#
# WHY: attempt A6 proved the container format is irrelevant —
#   S-Boot: "kernel size = 0x2ae6000, ramdisk size = 0x5c0000"  (= A6's ramdisk)
#   Kernel: "Trying to unpack rootfs image as initramfs... " then
#           "rootfs image is not initramfs (junk in compressed archive)"
#           0.21 ms later
# An LZMA stream at the address the kernel reads could only yield
# "decompressor failed" or success, never "junk".  So the bootloader advertises
# /chosen/linux,initrd-start|end without populating that memory on the normal
# BOOT-partition path.  Embedding the initramfs removes that handoff from the
# critical path: populate_rootfs() installs the built-in archive first, and
# because /init then exists, kernel_init() skips prepare_namespace() (which also
# bypasses the SAR_RD / root=PARTUUID fallback that causes "init group exit").
#
# RUNTIME: run inside a Linux aarch64 container (this tree cannot be built on
# macOS).  All paths below are container paths.
#
# Usage (inside the container):
#   SRC=/b/src INITRAMFS=/b/a7/initramfs.cpio OUT=/b/a7/out \
#   PATCH=/b/a7/0003-nuxel-initramfs-delivery-diagnostics.patch \
#   RELAX=/b/a7/kernel-relax-werror.sh \
#   bash /b/a7/build-kernel-a7.sh
# =============================================================================
set -euo pipefail
SRC="${SRC:-/b/src}"
INITRAMFS="${INITRAMFS:-/b/a7/initramfs.cpio}"
OUT="${OUT:-/b/a7/out}"
PATCH="${PATCH:-/b/a7/0003-nuxel-initramfs-delivery-diagnostics.patch}"
RELAX="${RELAX:-/b/a7/kernel-relax-werror.sh}"
DEFCONFIG="${DEFCONFIG:-exynos9820-beyond2lte_defconfig}"
JOBS="${JOBS:-$(nproc)}"

[ -f "$SRC/Makefile" ] || { echo "kernel tree missing at $SRC" >&2; exit 2; }
[ -f "$INITRAMFS" ]     || { echo "initramfs cpio missing: $INITRAMFS" >&2; exit 2; }
if [ -f "$PATCH" ] && ! command -v patch >/dev/null 2>&1; then
  echo "ERROR: 'patch' is required to apply $PATCH but is not installed." >&2
  echo "       In a Fedora container: dnf -y install patch" >&2
  exit 2
fi

echo "=== source: $(grep -m1 -E '^(VERSION|PATCHLEVEL|SUBLEVEL)' "$SRC/Makefile" | tr '\n' ' ')"
echo "=== initramfs: $INITRAMFS ($(wc -c <"$INITRAMFS") bytes)"
echo "=== bits: $(getconf LONG_BIT), $(nproc) cpus, $(free -m | awk '/Mem:/{print $2}') MiB"

# 1. neutralise the tree's hard-coded -Werror (GCC 14/15 diagnostics)
if [ -f "$RELAX" ]; then bash "$RELAX" "$SRC"; fi

# 2. delivery diagnostics
if [ -f "$PATCH" ]; then
  if patch -p1 -d "$SRC" --dry-run -s < "$PATCH" >/dev/null 2>&1; then
    patch -p1 -d "$SRC" -s < "$PATCH"
    echo "=== applied $(basename "$PATCH")"
  elif grep -q "NUXEL-KDIAG" "$SRC/init/initramfs.c"; then
    echo "=== $(basename "$PATCH") already applied"
  else
    echo "ERROR: diagnostics patch does not apply:" >&2
    patch -p1 -d "$SRC" --dry-run --verbose < "$PATCH" 2>&1 | tail -20 >&2
    exit 1
  fi
fi

mkdir -p "$OUT"

# 3. configure: the in-tree downstream defconfig, untouched, plus the
#    built-in initramfs.  No foreign fragment is merged.
make -C "$SRC" O="$OUT" ARCH=arm64 CROSS_COMPILE= "$DEFCONFIG" >/dev/null
sed -i -e "s|^CONFIG_INITRAMFS_SOURCE=.*|CONFIG_INITRAMFS_SOURCE=\"$INITRAMFS\"|" \
       -e "s|^# CONFIG_INITRAMFS_SOURCE is not set|CONFIG_INITRAMFS_SOURCE=\"$INITRAMFS\"|" \
       "$OUT/.config"
grep -q '^CONFIG_INITRAMFS_SOURCE="' "$OUT/.config" || \
  echo "CONFIG_INITRAMFS_SOURCE=\"$INITRAMFS\"" >> "$OUT/.config"
grep -q '^CONFIG_INITRAMFS_COMPRESSION_GZIP=y' "$OUT/.config" || \
  sed -i 's|^\(# CONFIG_INITRAMFS_COMPRESSION_\)|CONFIG_INITRAMFS_COMPRESSION_GZIP=y\n\1|' "$OUT/.config"
grep -q '^CONFIG_INITRAMFS_FORCE=y' "$OUT/.config" && \
  sed -i 's|^CONFIG_INITRAMFS_FORCE=y|# CONFIG_INITRAMFS_FORCE is not set|' "$OUT/.config" || true
make -C "$SRC" O="$OUT" ARCH=arm64 CROSS_COMPILE= olddefconfig >/dev/null

echo "=== config of interest:"
grep -E '^CONFIG_(INITRAMFS_SOURCE|INITRAMFS_COMPRESSION|INITRAMFS_FORCE|BLK_DEV_INITRD|RD_LZMA|RD_GZIP|CMDLINE)' "$OUT/.config"

# 4. build
echo "=== building Image + dtbs with -j$JOBS ..."
make -C "$SRC" O="$OUT" ARCH=arm64 CROSS_COMPILE= -j"$JOBS" Image dtbs

echo "=== results:"
ls -l "$OUT/arch/arm64/boot/Image"
find "$OUT/arch/arm64/boot/dts" -name 'exynos9820-beyond2lte*.dtb' 2>/dev/null | head
