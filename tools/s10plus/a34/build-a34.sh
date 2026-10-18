#!/usr/bin/env bash
# build-a34.sh — build the A34 TOUCHDOWN userspace artifacts and run the
# deterministic offline tests.  No phone access, no flash, no partition write.
#
#   CROSS_COMPILE=aarch64-linux-gnu- ./build-a34.sh
#
# The cross sysroot must provide wayland headers and alsa.  libwayland-client
# and libffi are pulled once from the running phone into the output sysroot
# (read-only console) because the bridge links the phone's own runtime ABI.
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$HERE/../../.." && pwd)"
OUT="${OUT:-$ROOT/build/out/s10plus/a34}"
SYS="$OUT/sysroot"
CROSS="${CROSS_COMPILE:-aarch64-linux-gnu-}"
CC="${CC:-${CROSS}gcc}"
SCANNER="${WAYLAND_SCANNER:-wayland-scanner}"
XML="$ROOT/tools/s10plus/a29/wlr-screencopy-unstable-v1.xml"

mkdir -p "$OUT/gen" "$SYS/include" "$SYS"
if [ ! -f "$OUT/gen/wlr-screencopy-unstable-v1-client-protocol.h" ]; then
  "$SCANNER" client-header "$XML" "$OUT/gen/wlr-screencopy-unstable-v1-client-protocol.h"
  "$SCANNER" private-code  "$XML" "$OUT/gen/wlr-screencopy-unstable-v1-protocol.c"
fi
if [ ! -f "$SYS/include/wayland-client.h" ]; then
  cp /usr/include/wayland-client.h /usr/include/wayland-client-core.h \
     /usr/include/wayland-client-protocol.h /usr/include/wayland-util.h \
     /usr/include/wayland-version.h "$SYS/include/" 2>/dev/null || true
fi
if [ ! -f "$SYS/libwayland-client.so.0" ] || [ ! -f "$SYS/libffi.so.8" ]; then
  echo "build-a34: pull libwayland-client.so.0 and libffi.so.8 into $SYS first:" >&2
  echo "  scripts/s10plus-debug-pack/nuxel-live.sh --pull /usr/lib64/libwayland-client.so.0.26.0 --out $SYS/libwayland-client.so.0" >&2
  echo "  scripts/s10plus-debug-pack/nuxel-live.sh --pull /usr/lib64/libffi.so.8 --out $SYS/libffi.so.8" >&2
  exit 3
fi

COMMON=(-O2 -Wall -Wextra -I "$OUT/gen" -I "$SYS/include" -I "$ROOT/tools/s10plus/a34")
LIBS=(-L"$SYS" -Wl,-rpath-link,"$SYS" -l:libwayland-client.so.0 -l:libffi.so.8)

echo "== nuxel-wl-snapshot =="
"$CC" "${COMMON[@]}" -o "$OUT/nuxel-wl-snapshot" \
  "$HERE/nuxel-wl-snapshot.c" "$OUT/gen/wlr-screencopy-unstable-v1-protocol.c" "${LIBS[@]}"

echo "== nuxel-wl-fb (A34 display-off) =="
"$CC" "${COMMON[@]}" -I "$ROOT/tools/s10plus/a33" -o "$OUT/nuxel-wl-fb" \
  "$HERE/nuxel-wl-fb.c" "$OUT/gen/wlr-screencopy-unstable-v1-protocol.c" "${LIBS[@]}"

echo "== nuxel-button-manager (A34 SYN_REPORT + Bixby/back) =="
"$CC" -std=gnu11 -O2 -Wall -Wextra -I "$HERE" -I /usr/aarch64-linux-gnu/sys-root/usr/include \
  -o "$OUT/nuxel-button-manager" "$HERE/nuxel-button-manager.c" \
  -L/usr/aarch64-linux-gnu/sys-root/usr/lib64 -lasound

echo "== offline tests =="
"$HERE/tests/test-fsm-power-bixby.sh"
python3 "$HERE/tests/test-touch-syn-translation.py"
node "$HERE/tests/test-qs-gesture.js"

echo "built in $OUT"
sha256sum "$OUT/nuxel-wl-snapshot" "$OUT/nuxel-wl-fb" "$OUT/nuxel-button-manager"
