#!/usr/bin/env bash
# build-a67.sh — build the A67 SLIDE PENGUIN optimized framebridge.
# No phone access, no flash, no partition write.
#
#   CROSS_COMPILE=aarch64-linux-gnu- ./build-a67.sh
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$HERE/../../.." && pwd)"
OUT="${OUT:-$ROOT/build/out/s10plus/a67}"
SYS="$ROOT/build/out/s10plus/a34/sysroot"   # reuse the validated A34 sysroot
CROSS="${CROSS_COMPILE:-aarch64-linux-gnu-}"
CC="${CC:-${CROSS}gcc}"
SCANNER="${WAYLAND_SCANNER:-wayland-scanner}"
XML="$ROOT/tools/s10plus/a29/wlr-screencopy-unstable-v1.xml"

mkdir -p "$OUT/gen" "$SYS/include" "$SYS"
if [ ! -f "$OUT/gen/wlr-screencopy-unstable-v1-client-protocol.h" ]; then
  "$SCANNER" client-header "$XML" "$OUT/gen/wlr-screencopy-unstable-v1-client-protocol.h"
  "$SCANNER" private-code  "$XML" "$OUT/gen/wlr-screencopy-unstable-v1-protocol.c"
fi
[ -f "$SYS/libwayland-client.so.0" ] && [ -f "$SYS/libffi.so.8" ] || {
  echo "build-a67: sysroot incomplete (need $SYS/libwayland-client.so.0 + libffi.so.8)" >&2; exit 3; }

COMMON=(-O2 -Wall -Wextra -I "$OUT/gen" -I "$SYS/include" -I "$ROOT/tools/s10plus/a67")
LIBS=(-L"$SYS" -Wl,-rpath-link,"$SYS" -l:libwayland-client.so.0 -l:libffi.so.8)

echo "== nuxel-wl-fb (A67 NEON blit) =="
"$CC" "${COMMON[@]}" -I "$ROOT/tools/s10plus/a33" -o "$OUT/nuxel-wl-fb" \
  "$HERE/nuxel-wl-fb.c" "$OUT/gen/wlr-screencopy-unstable-v1-protocol.c" "${LIBS[@]}"

echo "== bench-blit (offline, no /dev/fb0, no Wayland) =="
"$CC" -O2 -Wall -Wextra -std=gnu11 -o "$OUT/bench-blit" "$HERE/bench-blit.c"

echo "built in $OUT"
sha256sum "$OUT/nuxel-wl-fb" "$OUT/bench-blit"
