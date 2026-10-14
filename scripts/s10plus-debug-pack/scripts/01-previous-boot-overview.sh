#!/usr/bin/env bash
set -euo pipefail
source "$(dirname "$0")/_common.sh"
init_out previous-boot
require_recovery
capture_shell previous-boot/pstore-listing.txt 'ls -lah /sys/fs/pstore 2>&1 || true'
capture_shell previous-boot/last-kmsg-presence.txt 'ls -lah /proc/last_kmsg 2>&1 || true'
capture_shell previous-boot/boot-reason.txt 'cat /proc/cmdline 2>&1 | tr " " "\n" | grep -E "reset_reason|bootmode|revision|dtbo_idx|verifiedbootstate|hardware|androidboot.revision" || true'
capture_shell previous-boot/boot-environment.txt 'id; getprop ro.product.device; getprop ro.twrp.version; getprop ro.boot.hardware; getprop ro.boot.revision; getprop ro.boot.verifiedbootstate; uname -a'
say 'Previous-boot overview captured. This is TWRP context, not proof of what happened inside Nuxel.'
