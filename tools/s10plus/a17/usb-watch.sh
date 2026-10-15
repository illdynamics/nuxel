#!/bin/sh
# Broad USB watch: logs every change in the Mac's USB device inventory.
OUT="$1"; DUR="${2:-3600}"
i=0
prev=""
while [ "$i" -lt "$DUR" ]; do
  cur="$(system_profiler SPUSBDataType 2>/dev/null | grep -E 'Product ID|Manufacturer|Serial Number|^        [A-Za-z].*:' | tr -d ' ' | tr '\n' '|')"
  if [ "$cur" != "$prev" ]; then
    printf '%s CHANGE %s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$cur" >> "$OUT/usb-watch.log"
    prev="$cur"
  fi
  tty_now="$(ls /dev/cu.usbmodem* /dev/tty.usbmodem* 2>/dev/null | tr '\n' ' ')"
  if [ -n "$tty_now" ]; then
    printf '%s TTY %s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$tty_now" >> "$OUT/usb-watch.log"
  fi
  adb_now="$(adb devices 2>/dev/null | sed -n '2p')"
  if [ -n "$adb_now" ] && [ "$adb_now" != "$adb_prev" ]; then
    printf '%s ADB %s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$adb_now" >> "$OUT/usb-watch.log"
    adb_prev="$adb_now"
  fi
  i=$((i+5))
  sleep 5
done
