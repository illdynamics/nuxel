#!/usr/bin/env bash
# Nuxel S10+ — passive USB/ADB boot observation (READ-ONLY, macOS).
#
# Samples `adb devices` and the macOS USB device tree every N seconds for a
# bounded duration and appends timestamped lines to a log file. It never
# reboots, writes or mounts anything; it exists so a failed Nuxel boot can be
# described from tool evidence instead of assumption.
#
# Usage: bash scripts/19-usb-boot-watch.sh <log-file> [seconds] [interval-seconds]
set -uo pipefail
LOG="${1:?usage: 19-usb-boot-watch.sh <log-file> [seconds] [interval]}"
DUR="${2:-300}"
INT="${3:-2}"
mkdir -p "$(dirname "$LOG")"
end=$(( $(date +%s) + DUR ))
echo "# nuxel usb/adb boot watch start=$(date -u +%Y-%m-%dT%H:%M:%SZ) duration=${DUR}s interval=${INT}s" >> "$LOG"
prev=""
while [ "$(date +%s)" -lt "$end" ]; do
  ts="$(date -u +%H:%M:%SZ)"
  adbs="$(adb devices 2>/dev/null | tail -n +2 | tr '\n' '|' | tr -s ' ' | tr -d '\t')"
  usb="$(ioreg -p IOUSB -w0 2>/dev/null | grep -o '+-o [^<]*' | sed 's/+-o //; s/[[:space:]]*$//' | grep -v '^Root$' | tr '\n' ',')"
  cur="adb=[${adbs}] usb=[${usb}]"
  if [ "$cur" != "$prev" ]; then
    printf '%s CHANGE %s\n' "$ts" "$cur" >> "$LOG"
    prev="$cur"
  else
    printf '%s steady %s\n' "$ts" "$cur" >> "$LOG"
  fi
  sleep "$INT"
done
echo "# watch end=$(date -u +%Y-%m-%dT%H:%M:%SZ)" >> "$LOG"
