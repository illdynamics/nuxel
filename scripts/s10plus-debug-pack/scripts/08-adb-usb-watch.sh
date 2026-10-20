#!/usr/bin/env bash
# Passive monitor: does not reboot the phone; Ctrl+C stops collection.
set -euo pipefail
source "$(dirname "$0")/_common.sh"
init_out adb-watch
require_cmd adb
INTERVAL="${NUXEL_WATCH_INTERVAL:-2}"
DURATION="${NUXEL_WATCH_SECONDS:-180}"
case "$INTERVAL:$DURATION" in *[!0-9:]*|'') die 'Use positive integers for NUXEL_WATCH_INTERVAL and NUXEL_WATCH_SECONDS';; esac
[ "$INTERVAL" -gt 0 ] && [ "$DURATION" -gt 0 ] || die 'Intervals must be > 0'
say "Passive watch for $DURATION seconds, every $INTERVAL second(s). Press Ctrl+C to stop."
log="$NUXEL_OUT/adb-watch.tsv"
printf 'utc_epoch\tdevices_lines\n' > "$log"
start="$(date +%s)"
while [ $(( $(date +%s) - start )) -lt "$DURATION" ]; do
  now="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  # Do not poll shell: repeated connect attempts can interfere with early recovery/boot.
  state="$(adb devices | awk 'NR>1 && NF>=2 {printf "%s:%s,",$1,$2}' 2>/dev/null || true)"
  printf '%s\t%s\n' "$now" "$state" >> "$log"
  printf '%s  %s\n' "$now" "${state:-no-adb-device}"
  sleep "$INTERVAL"
done
say "Saved $log"
