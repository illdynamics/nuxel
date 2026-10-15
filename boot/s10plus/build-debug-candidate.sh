#!/usr/bin/env bash
# Build the S10+ BOOT diagnostic/fix candidate (cmdline-independent init).
#
# What it does: takes the last verified boot image (kernel + merged DTB are
# preserved byte-for-byte), replaces only the initramfs /init with the current
# boot/initramfs/init.sh, and repacks an Android v1 boot image with the load
# addresses taken from the input header (0x10008000/0x11000000/0x10000100 —
# identical to this unit's TWRP recovery image, which S-Boot boots).
#
# Why /init changed: Samsung S-Boot replaces /chosen/bootargs and drops the boot
# image header `cmdline`, so the initramfs must identify the device from the
# device tree and resolve USERDATA by the kernel's PARTNAME uevent instead of
# relying on `nuxel.device=`/`root=`. Failures are persisted to
# <rootfs>/nuxel-boot-diag.log and to the BOOT partition tail, including dmesg.
#
# Usage: boot/s10plus/build-debug-candidate.sh [INPUT_IMG] [OUTPUT_IMG]
set -euo pipefail
HERE=$(cd "$(dirname "$0")" && pwd)
ROOT=$(cd "$HERE/../.." && pwd)
IN="${1:-$ROOT/build/out/s10plus/nuxel-beyond2lte-boot-merged-fixed.img}"
OUT="${2:-$ROOT/build/out/s10plus/debug-candidates/nuxel-beyond2lte-boot-diag-cmdline-free.img}"
[ -f "$IN" ] || { echo "input image not found: $IN" >&2; exit 2; }
mkdir -p "$(dirname "$OUT")"
sh "$ROOT/boot/s10plus/tests/test-init-cmdline-independence.sh"
python3 "$ROOT/tools/s10plus/patch-boot-from-upload.py" "$IN" "$OUT"
echo "built: $OUT"
shasum -a 256 "$OUT" 2>/dev/null || sha256sum "$OUT"
