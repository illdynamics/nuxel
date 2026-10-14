#!/usr/bin/env bash
set -euo pipefail
echo '=== Nuxel Mac diagnostic tool doctor ==='
uname -a
for c in adb python3 shasum zip unzip system_profiler ioreg fdtget dtc lz4 zstd brew; do
  if command -v "$c" >/dev/null 2>&1; then printf 'OK      %-18s %s\n' "$c" "$(command -v "$c")";
  else printf 'MISSING %-18s\n' "$c"; fi
done
if command -v brew >/dev/null 2>&1; then
  p="$(brew --prefix e2fsprogs 2>/dev/null || true)"
  for c in debugfs e2fsck dumpe2fs; do
    if [ -x "$p/sbin/$c" ]; then echo "OK      $c  $p/sbin/$c"; else echo "MISSING $c"; fi
  done
fi
if command -v adb >/dev/null 2>&1; then
  echo '=== Connected devices (no root or write operations) ==='
  adb devices -l || true
fi
echo '=== Note: Nuxel Fedora ARM64 system boots may have no ADB daemon ==='
