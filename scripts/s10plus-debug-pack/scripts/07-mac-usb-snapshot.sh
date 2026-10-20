#!/usr/bin/env bash
set -euo pipefail
source "$(dirname "$0")/_common.sh"
init_out mac-usb
{ date -u; uname -a; command -v adb && adb version; adb devices -l; } > "$NUXEL_OUT/host-usb-summary.txt" 2>&1 || true
if [ "$(uname -s)" = Darwin ]; then
  system_profiler SPUSBDataType > "$NUXEL_OUT/host-system_profiler-usb.txt" 2>&1 || true
  ioreg -p IOUSB -l -w 0 > "$NUXEL_OUT/host-ioreg-usb.txt" 2>&1 || true
else
  if command -v lsusb >/dev/null 2>&1; then lsusb -v > "$NUXEL_OUT/host-lsusb.txt" 2>&1 || true; fi
fi
say 'Host USB snapshot saved. Device serial numbers may be present.'
