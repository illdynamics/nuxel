#!/usr/bin/env bash
set -euo pipefail
source "$(dirname "$0")/_common.sh"
init_out recovery-kernel
require_recovery
capture_shell kernel/uname.txt 'uname -a; cat /proc/version'
capture_shell kernel/cmdline.txt 'cat /proc/cmdline'
capture_shell kernel/pstore-settings.txt 'for p in /sys/module/pstore/parameters/* /sys/module/ramoops/parameters/*; do [ ! -r "$p" ] || { echo "$p"; cat "$p"; }; done'
capture_shell kernel/kernel-last-reset.txt 'getprop ro.boot.bootreason; getprop sys.boot.reason; cat /proc/sys/kernel/panic 2>&1 || true'
if adb_cmd shell '[ -r /proc/config.gz ]' >/dev/null 2>&1; then
  capture_file kernel/recovery-config.gz /proc/config.gz
  if [ -f "$NUXEL_OUT/kernel/recovery-config.gz" ]; then
    (gzip -dc "$NUXEL_OUT/kernel/recovery-config.gz" | grep -E '^(CONFIG_(PSTORE|RAMOOPS|PRINTK|KMSG_DUMP|BLK_DEV_INITRD|EXT4_FS|DEVTMPFS|SAMSUNG|DRM)|# CONFIG_PSTORE)' > "$NUXEL_OUT/kernel/recovery-kernel-options.txt") || true
  fi
fi
say 'Kernel properties refer to TWRP recovery, unless explicitly named previous-boot.'
