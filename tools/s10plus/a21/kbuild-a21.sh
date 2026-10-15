#!/bin/sh
# Build Image-A21 with the A21 initramfs EMBEDDED in the kernel.
# Required on this board: the S10+ bootloader never populates the initrd memory it
# advertises, so only the kernel's built-in initramfs is ever executed.
set -eu
SRC=/b/k15; OUT=/b/a16/out; INIT=/b/a21/initramfs-a21.cpio; LOG=/b/a21/build-a21.log
exec >"$LOG" 2>&1
say() { printf "[%s] %s\n" "$(date -u +%H:%M:%S)" "$*"; }
say "initramfs $(wc -c <"$INIT") sha256 $(sha256sum "$INIT" | cut -d" " -f1)"
sed -i "s|^CONFIG_INITRAMFS_SOURCE=.*|CONFIG_INITRAMFS_SOURCE=\"$INIT\"|" "$OUT/.config"
grep -E "^CONFIG_INITRAMFS_SOURCE=" "$OUT/.config"
make -C "$SRC" O="$OUT" ARCH=arm64 CROSS_COMPILE= olddefconfig >/dev/null
say building
make -C "$SRC" O="$OUT" ARCH=arm64 CROSS_COMPILE= -j6 Image
cp -f "$OUT/arch/arm64/boot/Image" /b/a21/Image-A21
say "Image-A21 $(stat -c%s /b/a21/Image-A21) sha256 $(sha256sum /b/a21/Image-A21 | cut -d\" \" -f1)"
say A21_KERNEL_BUILD_OK
