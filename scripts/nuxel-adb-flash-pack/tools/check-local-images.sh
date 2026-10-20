#!/usr/bin/env bash
set -euo pipefail
if [[ $# -ne 2 ]]; then
  echo 'Usage: bash tools/check-local-images.sh BOOT.img ROOTFS.img' >&2
  exit 2
fi
BOOT="$1"; ROOT="$2"
[[ -s "$BOOT" && -s "$ROOT" ]] || { echo 'Both image files must exist and be non-empty' >&2; exit 2; }
echo '=== SHA-256 ==='
shasum -a 256 "$BOOT" "$ROOT"
echo '=== Image identification ==='
file "$BOOT" "$ROOT"
if command -v brew >/dev/null 2>&1; then
 E2FSCK="$(brew --prefix e2fsprogs 2>/dev/null)/sbin/e2fsck"
else
 E2FSCK="$(command -v e2fsck 2>/dev/null || true)"
fi
if [[ -n "$E2FSCK" && -x "$E2FSCK" ]]; then
 echo '=== Read-only ext4 fsck ==='
 "$E2FSCK" -fn "$ROOT"
else
 echo 'SKIP: e2fsprogs not installed (optional: brew install e2fsprogs)'
fi
