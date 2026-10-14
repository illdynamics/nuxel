#!/usr/bin/env bash
set -euo pipefail
source "$(dirname "$0")/_common.sh"
init_out twrp-logs
require_recovery
for p in /tmp/recovery.log /cache/recovery/last_log /cache/recovery/log /tmp/dmesg.log; do
  if adb_cmd shell "[ -r '$p' ]" >/dev/null 2>&1; then
    name="${p#/}"; capture_file "recovery/$name" "$p"
  fi
done
capture_shell recovery/recovery-properties.txt 'getprop ro.twrp.version; getprop ro.product.device; getprop ro.bootmode; getprop ro.boot.bootreason; getprop sys.boot.reason'
capture_shell recovery/recovery-mounts.txt 'cat /proc/mounts'
# dmesg is from recovery kernel, not the failed Nuxel kernel unless pstore exposes it.
capture_shell recovery/current-recovery-dmesg.txt 'dmesg 2>&1'
say 'Recovery logs captured; current-recovery-dmesg is NOT the failed Nuxel boot log.'
