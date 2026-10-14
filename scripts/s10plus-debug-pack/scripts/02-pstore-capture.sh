#!/usr/bin/env bash
set -euo pipefail
source "$(dirname "$0")/_common.sh"
init_out pstore
require_recovery
capture_shell pstore/listing.txt 'ls -lah /sys/fs/pstore 2>&1 || true'
listing="$(adb_cmd shell 'for f in /sys/fs/pstore/*; do [ -f "$f" ] && printf "%s\n" "$f"; done' 2>/dev/null | tr -d '\r' || true)"
n=0
while IFS= read -r path; do
  [ -n "$path" ] || continue
  case "$path" in
    /sys/fs/pstore/*) ;;
    *) warn "Unrecognized remote pstore path: $path"; continue ;;
  esac
  # Allow only plain safe pstore filenames before passing to device shell.
  base="${path##*/}"
  case "$base" in ''|*[!a-zA-Z0-9_.-]*) warn "Skipping unsafe filename"; continue ;; esac
  capture_file "pstore/$base" "$path"
  n=$((n+1))
done <<EOF_LIST
$listing
EOF_LIST
if [ "$n" -eq 0 ]; then
  printf 'No readable files in /sys/fs/pstore. This does not prove the kernel never started.\n' > "$NUXEL_OUT/pstore/NO-PSTORE-FILES.txt"
fi
say "Pstore attempted: $n file(s)."
