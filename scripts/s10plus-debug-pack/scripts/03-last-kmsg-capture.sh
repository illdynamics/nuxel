#!/usr/bin/env bash
set -euo pipefail
source "$(dirname "$0")/_common.sh"
init_out last-kmsg
require_recovery
capture_shell previous-boot/last-kmsg-stat.txt 'ls -lah /proc/last_kmsg 2>&1 || true'
if adb_cmd shell '[ -r /proc/last_kmsg ]' >/dev/null 2>&1; then
  capture_file previous-boot/last_kmsg.txt /proc/last_kmsg
else
  mkdir -p "$NUXEL_OUT/previous-boot"
  printf 'Not exposed by TWRP; check pstore instead.\n' > "$NUXEL_OUT/previous-boot/NO-LAST-KMSG.txt"
  say '/proc/last_kmsg is missing; this is common on some recovery kernels.'
fi
