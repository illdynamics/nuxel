#!/bin/sh
set -eu
SRC=/b/k15; OUT=/b/a16/out; INIT=/b/a17/initramfs-a20.cpio; LOG=/b/a17/build-a20.log
exec >"$LOG" 2>&1
say() { printf "[%s] %s\n" "$(date -u +%H:%M:%S)" "$*"; }
say "initramfs $(wc -c <"$INIT") sha256 $(sha256sum "$INIT" | cut -d" " -f1)"
sed -i "s|^CONFIG_INITRAMFS_SOURCE=.*|CONFIG_INITRAMFS_SOURCE=\"$INIT\"|" "$OUT/.config"
grep -E "^CONFIG_INITRAMFS_SOURCE=" "$OUT/.config"
make -C "$SRC" O="$OUT" ARCH=arm64 CROSS_COMPILE= olddefconfig >/dev/null
say building
make -C "$SRC" O="$OUT" ARCH=arm64 CROSS_COMPILE= -j6 Image
cp -f "$OUT/arch/arm64/boot/Image" /b/a17/Image-A20
say "Image-A20 $(stat -c%s /b/a17/Image-A20) sha256 $(sha256sum /b/a17/Image-A20 | cut -d\" \" -f1)"
say A20_KERNEL_BUILD_OK
