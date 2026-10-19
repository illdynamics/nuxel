#!/bin/sh
# ============================================================================
# test-ui-layout.sh — the A27 release gate for the phone interface.
#
#   1. the embedded font atlas is regenerated from the committed DejaVu source and
#      must come out byte-identical (a drifting atlas is a silently different UI);
#   2. the SAME renderer the handset runs is built for the host and rendered at
#      all four mission scales (360x760, 720x1520, 1080x2280, 1440x3040) with four
#      fixtures (normal, long strings, unreadable battery/no network, huge
#      uptime+charging): every page must report ZERO layout violations
#      (no overlap, nothing outside the safe area, nothing in the camera cutout);
#   3. the ARM64 binary is built and must be an aarch64 ELF that actually contains
#      the A27 display-ownership and layout machinery.
#
# Usage: sh tools/s10plus/a27/test-ui-layout.sh
# Exit: 0 pass, 1 fail, 2 missing tool/input.
# ============================================================================
set -eu
ROOT=$(cd "$(dirname "$0")/../../.." && pwd)
A27="$ROOT/tools/s10plus/a27"
WORK="$ROOT/build/out/s10plus/a27/uitests"
mkdir -p "$WORK"
CC=${CC:-cc}
CROSS=${NUXEL_AARCH64_CC:-aarch64-linux-gnu-gcc}

echo "== 1. font atlas is reproducible =="
python3 "$A27/make-font-atlas.py" --out "$WORK/atlas.c" >"$WORK/atlas.json" || exit 2
if cmp -s "$WORK/atlas.c" "$A27/generated/nuxel-font-atlas.c"; then
    echo "   PASS atlas identical ($(wc -c <"$A27/generated/nuxel-font-atlas.c" | tr -d ' ') bytes of C)"
else
    echo "   FAIL regenerated atlas differs from the committed one"; exit 1
fi

echo "== 2. offline layout harness (4 scales x 4 fixtures x 6 pages) =="
"$CC" -O1 -w -o "$WORK/test-ui-layout" "$A27/test-ui-layout.c" || exit 2
"$WORK/test-ui-layout" "$WORK/render" >"$WORK/layout.log" 2>&1 || {
    echo "   FAIL layout violations:"; grep -E "OVERLAP|SAFE_AREA|CUTOUT" "$WORK/layout.log" | head -20; exit 1; }
grep -q "A27_UI_LAYOUT_TESTS_OK" "$WORK/layout.log" || { echo "   FAIL harness did not report OK"; exit 1; }
grep "HOST_UI_LAYOUT" "$WORK/layout.log"
grep -c "NUXEL_UI_SELFTEST_LAYOUT_OK" "$WORK/layout.log" | sed 's/^/   page-group renders clean: /'

echo "== 3. ARM64 binary =="
"$CROSS" -Os -w -ffreestanding -fno-builtin -nostdlib -static -s -Wl,--build-id=none \
     -o "$ROOT/build/out/s10plus/nuxel-ui-a27" "$ROOT/tools/s10plus/nuxel-ui.c" || exit 2
BIN="$ROOT/build/out/s10plus/nuxel-ui-a27"
file -b "$BIN" | grep -q aarch64 || { echo "   FAIL not an aarch64 ELF"; exit 1; }
for marker in NUXEL_UI_DISPLAY_LOCK_ACQUIRED NUXEL_UI_LAYOUT_VIOLATIONS \
              NUXEL_UI_DISPLAY_OWNER_REFUSED INPUT_CAPS TOUCH_TAP ui-small.ppm; do
    strings -a "$BIN" | grep -q "$marker" || { echo "   FAIL binary lacks $marker"; exit 1; }
done
# the malformed A26 ioctl requests must be gone: the constants are asserted at
# compile time in nuxel-ui.c against the values the target Linux ABI produces
# (EVIOCGBIT(EV_ABS,32)=0x80204523, EVIOCGABS(MT_X)=0x80184575).
if grep -q "0x80000000u|(((u32)(ev))<<8)|0x20" "$ROOT/tools/s10plus/nuxel-ui.c"; then
    echo "   FAIL the malformed EVIOCGBIT encoding is still in the source"; exit 1
fi
echo "   PASS $(basename "$BIN") $(wc -c <"$BIN" | tr -d ' ') bytes $(shasum -a 256 "$BIN" | cut -c1-16)…"
echo "A27_UI_GATE_OK"
