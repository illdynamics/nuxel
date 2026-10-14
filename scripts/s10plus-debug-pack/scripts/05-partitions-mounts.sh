#!/usr/bin/env bash
set -euo pipefail
source "$(dirname "$0")/_common.sh"
init_out partitions
require_recovery
capture_shell device/partition-by-name.txt 'ls -la /dev/block/by-name 2>&1'
capture_shell device/proc-partitions.txt 'cat /proc/partitions'
capture_shell device/fstab.txt 'cat /etc/recovery.fstab /etc/twrp.fstab 2>&1 || true'
capture_shell device/mounts.txt 'cat /proc/mounts'
capture_shell device/boot-properties.txt 'getprop ro.product.device; getprop ro.boot.bootloader; getprop ro.boot.revision; getprop ro.boot.hardware'
capture_shell device/read-only-block-sizes.txt '
for p in boot userdata recovery dtb dtbo system vendor; do
  b="/dev/block/by-name/$p"
  if [ -e "$b" ]; then
    echo "=== $p -> $(readlink "$b" 2>/dev/null) ==="
    blockdev --getsize64 "$b" 2>&1 || cat "/sys/class/block/$(basename "$(readlink "$b")")/size" 2>&1
  fi
done'
say 'Read-only block facts collected. No partition readback or write was performed.'
# Recovery's live DTB identity (not necessarily the Nuxel kernel's DTB).
capture_shell device/recovery-dtb-identity.txt 'echo "=== Recovery DTB ==="; cat /proc/device-tree/model 2>&1; echo; cat /proc/device-tree/compatible 2>&1 || true'
