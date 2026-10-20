#!/usr/bin/env bash
set -euo pipefail
ADB=(adb)
if [[ "${1:-}" == '--serial' ]]; then
 [[ -n "${2:-}" ]] || { echo 'Missing serial' >&2; exit 2; }
 ADB+=( -s "$2" )
fi
"${ADB[@]}" shell 'for d in /dev/block/by-name /dev/block/bootdevice/by-name /dev/block/platform/13d60000.ufs/by-name; do ls -l "$d" 2>/dev/null; done; echo ===SLOT===; getprop ro.boot.slot_suffix; echo ===MOUNTS===; cat /proc/mounts; echo ===PARTITIONS===; cat /proc/partitions'
