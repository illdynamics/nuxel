#!/bin/sh
# Build the external framebuffer bridge on the S10+ (aarch64 Fedora).
# Userspace only: gcc + wayland-client headers are already in the image.
set -eu
BASE="${NUXEL_DISPLAY_BASE:-/usr/lib/nuxel/nuxel-display}"
SRC="$BASE/nuxel-wl-fb-ext.c"
XML="$BASE/protocol/wlr-screencopy-unstable-v1.xml"
OUT="$BASE/nuxel-wl-fb-ext"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
command -v gcc >/dev/null || { echo "BUILD_FAIL missing gcc"; exit 1; }
command -v wayland-scanner >/dev/null || { echo "BUILD_FAIL missing wayland-scanner"; exit 1; }
command -v pkg-config >/dev/null || { echo "BUILD_FAIL missing pkg-config"; exit 1; }
[ -r "$SRC" ] || { echo "BUILD_FAIL missing $SRC"; exit 1; }
[ -r "$XML" ] || { echo "BUILD_FAIL missing $XML"; exit 1; }
if [ -x "$OUT" ] && [ "$OUT" -nt "$SRC" ] && [ "$OUT" -nt "$XML" ]; then
    echo "BUILD_SKIP up-to-date $OUT"
    exit 0
fi
wayland-scanner client-header "$XML" "$TMP/wlr-screencopy-unstable-v1-client-protocol.h"
wayland-scanner private-code "$XML" "$TMP/wlr-screencopy-unstable-v1-protocol.c"
CFLAGS="$(pkg-config --cflags wayland-client)"
LIBS="$(pkg-config --libs wayland-client)"
# shellcheck disable=SC2086
gcc -O2 -g -Wall -Wextra -Wno-unused-parameter -I"$TMP" \
    -o "$OUT.tmp" "$SRC" "$TMP/wlr-screencopy-unstable-v1-protocol.c" \
    $CFLAGS $LIBS -lm
mv "$OUT.tmp" "$OUT"
chmod 0755 "$OUT"
echo "BUILD_OK path=$OUT"
"$OUT" --help >/dev/null 2>&1 || true
