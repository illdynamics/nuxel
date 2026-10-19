#!/bin/sh
# A35: display-commit regression. Run anywhere; optionally build the real
# nuxel-wl-fb.c with a mocked DECON ioctl when Wayland dev headers exist.
set -eu
HERE=$(cd "$(dirname "$0")" && pwd)
ROOT=$(cd "$HERE/../../../.." && pwd)
python3 "$HERE/test-decon-presentation-contract.py"
HEADERS=${NUXEL_TEST_WAYLAND_HEADERS:-/usr/include}
if [ ! -f "$HEADERS/wayland-client.h" ]; then
  echo "SKIP A35 mock-ioctl C test: Wayland C headers unavailable at $HEADERS"
  exit 0
fi
CC=${CC:-cc}
OUT=$(mktemp -d)
trap 'rm -rf "$OUT"' EXIT
"$CC" -std=gnu11 -O2 -Wall -Wextra -ffunction-sections -fdata-sections \
  -Wl,--gc-sections -I "$ROOT" -I "$HEADERS" \
  -I "$ROOT/tools/s10plus/a34/gen" -I "$ROOT/tools/s10plus/a33" \
  -o "$OUT/decon-mock-test" "$HERE/test-decon-frame-commit.c"
"$OUT/decon-mock-test"
