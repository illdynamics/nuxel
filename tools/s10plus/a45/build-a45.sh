#!/usr/bin/env bash
# build-a45.sh — cross-build the A45 native userspace pieces (no GTK required).
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$HERE/../../.." && pwd)"
OUT="${OUT:-$ROOT/build/out/s10plus/a45}"
SYS="$ROOT/build/out/s10plus/a34/sysroot"
CROSS="${CROSS_COMPILE:-aarch64-linux-gnu-}"
CC="${CC:-${CROSS}gcc}"
SCANNER="${WAYLAND_SCANNER:-wayland-scanner}"

mkdir -p "$OUT/gen" "$OUT"

gen() { # xml -> basename
  local xml="$1" base="$2"
  if [ ! -f "$OUT/gen/${base}-client-protocol.h" ]; then
    "$SCANNER" client-header "$xml" "$OUT/gen/${base}-client-protocol.h"
    "$SCANNER" private-code "$xml" "$OUT/gen/${base}-protocol.c"
  fi
}
gen "$HERE/wlr-layer-shell-unstable-v1.xml" wlr-layer-shell-unstable-v1
gen "$HERE/xdg-shell.xml" xdg-shell
gen "$HERE/text-input-unstable-v3.xml" text-input-unstable-v3
python3 "$HERE/gen-navdock-art.py"

COMMON=(-O2 -Wall -Wextra -Wno-unused-parameter -I "$OUT/gen" -I "$SYS/include" -I "$HERE")
LIBS=(-L"$SYS" -Wl,-rpath-link,"$SYS" -l:libwayland-client.so.0 -l:libffi.so.8)

echo "== nuxel-navdock =="
"$CC" "${COMMON[@]}" -o "$OUT/nuxel-navdock" \
  "$HERE/nuxel-navdock.c" \
  "$OUT/gen/wlr-layer-shell-unstable-v1-protocol.c" \
  "$OUT/gen/xdg-shell-protocol.c" "${LIBS[@]}"

echo "== nuxel-text-input-probe =="
"$CC" "${COMMON[@]}" -o "$OUT/nuxel-text-input-probe" \
  "$HERE/nuxel-text-input-probe.c" \
  "$OUT/gen/text-input-unstable-v3-protocol.c" \
  "$OUT/gen/xdg-shell-protocol.c" "${LIBS[@]}"

file "$OUT/nuxel-navdock" | grep -q 'ARM aarch64' || { echo "NOT aarch64"; exit 1; }
sha256sum "$OUT/nuxel-navdock" "$OUT/nuxel-text-input-probe"
echo "built in $OUT"
