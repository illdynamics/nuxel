#!/bin/sh
# A27: rebuild the ARM64 Image with the A27 initramfs EMBEDDED.
# Run INSIDE the nuxel-kb container (the S10+ bootloader never populates the
# initrd memory it advertises, so only the kernel's built-in initramfs runs).
set -eu
SRC=/b/k15; OUT=/b/a16/out; INIT=/b/a27/initramfs-a27.cpio; LOG=/b/a27/build-a27.log
exec >"$LOG" 2>&1
say() { printf "[%s] %s\n" "$(date -u +%H:%M:%S)" "$*"; }
say "initramfs $(wc -c <"$INIT") sha256 $(sha256sum "$INIT" | cut -d" " -f1)"
sed -i "s|^CONFIG_INITRAMFS_SOURCE=.*|CONFIG_INITRAMFS_SOURCE=\"$INIT\"|" "$OUT/.config"
grep -E "^CONFIG_INITRAMFS_SOURCE=" "$OUT/.config"
make -C "$SRC" O="$OUT" ARCH=arm64 CROSS_COMPILE= olddefconfig >/dev/null
say building
make -C "$SRC" O="$OUT" ARCH=arm64 CROSS_COMPILE= -j6 Image
cp -f "$OUT/arch/arm64/boot/Image" /b/a27/Image-A27
say "Image-A27 $(stat -c%s /b/a27/Image-A27) sha256 $(sha256sum /b/a27/Image-A27 | cut -d" " -f1)"
say A27_KERNEL_BUILD_OK
