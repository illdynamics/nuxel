#!/usr/bin/env bash
set -euo pipefail

# Configuration and Arguments
INPUT_IMG="${1:-boot.img}"
OUTPUT_IMG="${2:-fixed_boot.img}"
WORK_DIR="boot_workspace"

# Default kernel command line (adjust if your pipeline injects this dynamically)
CMDLINE="${BOOT_CMDLINE:-buildvariant=userdebug nuxel.device=s10plus root=/dev/block/platform/13d60000.ufs/by-name/userdata rootfstype=ext4 rootwait rw}"
PAGESIZE="${BOOT_PAGESIZE:-2048}"

echo "==> Starting boot image repair process..."
echo "    Input Image:  $INPUT_IMG"
echo "    Output Image: $OUTPUT_IMG"
echo "    Page Size:    $PAGESIZE"

# Check for required tools
for tool in unpack_bootimg mkbootimg cpio gzip find; do
    if ! command -v "$tool" &> /dev/null; then
        echo "Error: Required tool '$tool' is not installed or not in PATH." >&2
        exit 1
    fi
done

# Clean up any previous workspace
rm -rf "$WORK_DIR"
mkdir -p "$WORK_DIR/unpacked" "$WORK_DIR/ramdisk_root"

echo "==> Unpacking boot image..."
unpack_bootimg --boot_img "$INPUT_IMG" --out "$WORK_DIR/unpacked"

echo "==> Extracting initramfs..."
cd "$WORK_DIR/ramdisk_root"
# Automatically detect compression type or fallback to standard gzip cpio
if gzip -t ../unpacked/ramdisk 2>/dev/null; then
    gzip -dc ../unpacked/ramdisk | cpio -idiv --quiet
else
    cpio -idiv --quiet < ../unpacked/ramdisk
fi
cd - > /dev/null

echo "==> Patching initramfs (creating /bin/sh -> toybox symlink)..."
cd "$WORK_DIR/ramdisk_root"

if [ -f "bin/toybox" ]; then
    # Ensure bin directory exists and create symlink
    mkdir -p bin
    ln -sf toybox bin/sh
    chmod +x bin/toybox
    echo "    Successfully created symbolic link: /bin/sh -> toybox"
else
    echo "Error: /bin/toybox not found in initramfs root!" >&2
    exit 1
fi
cd - > /dev/null

echo "==> Repacking initramfs..."
cd "$WORK_DIR/ramdisk_root"
find . -o -type d | sort | cpio -o -H newc --quiet | gzip > ../new_ramdisk.cpio.gz
cd - > /dev/null

echo "==> Repacking final boot image..."
mkbootimg \
    --kernel "$WORK_DIR/unpacked/kernel" \
    --ramdisk "$WORK_DIR/new_ramdisk.cpio.gz" \
    --pagesize "$PAGESIZE" \
    --cmdline "$CMDLINE" \
    --output "$OUTPUT_IMG"

# Clean up workspace
rm -rf "$WORK_DIR"

echo "==> Success! Fixed boot image generated at: $OUTPUT_IMG"