#!/bin/sh
# ============================================================================
# test-launcher.sh — the A28 release gate for the UTM-launcher port.
#
#   1. the generated tables are up to date (the phone's app registry IS
#      pwa/nuxel-home/js/apps.js and its palette IS pwa/nuxel-home/css/style.css);
#   2. the evdev request numbers the touchscreen code hard-codes match the ARM64
#      kernel UAPI headers — checked against <linux/input.h>, compiled with the
#      cross toolchain, not against a hand-derived copy of the same numbers;
#   3. the SAME renderer the handset runs is compiled for the host and the
#      launcher screen is measured numerically (colour, glyph ink, hit-testing,
#      dock band, the console surface, honest unavailable-app reporting, and the
#      layout checker on all 7 pages);
#   4. the freestanding PNG decoder's cover-fitted output is compared, pixel for
#      pixel, with an independent numpy reference of the same asset;
#   5. the ARM64 binary is built, must be an aarch64 static ELF, must contain the
#      launcher/telemetry markers, and must stay inside the live-deploy budget
#      (this binary travels over the CDC-ACM console with a base64 line
#      protocol, so its size is a deployment constraint, not a taste).
#
# Usage: sh tools/s10plus/a28/test-launcher.sh
# Exit: 0 pass, 1 a gate failed, 2 a required tool/input is missing.
# ============================================================================
set -eu
ROOT=$(cd "$(dirname "$0")/../../.." && pwd)
A28="$ROOT/tools/s10plus/a28"
WORK="$ROOT/build/out/s10plus/a28"
CC=${CC:-cc}
CROSS=${NUXEL_AARCH64_CC:-aarch64-linux-gnu-gcc}
SIZE_BUDGET=${A28_SIZE_BUDGET:-1200000}
mkdir -p "$WORK" "$WORK/host"

echo "== 1. generated launcher tables are up to date =="
python3 "$A28/gen-launcher.py" --check
python3 "$A28/make-emoji-atlas.py" --check

echo "== 2. evdev request numbers vs the ARM64 kernel UAPI =="
"$CROSS" -c -o /dev/null "$A28/evdev-abi-probe.c" || {
    echo "   FAIL the UI's evdev ioctls/struct sizes disagree with <linux/input.h>"; exit 1; }
echo "   PASS A28_ABI_PROBE_OK (EVIOCGBIT/EVIOCGABS/EVIOCGPROP + 24-byte input_event)"

echo "== 3. host gate: the launcher screen, measured =="
"$CC" -O1 -w -o "$WORK/test-launcher" "$A28/test-launcher.c" || exit 2
"$WORK/test-launcher" "$WORK/host" \
    --wallpaper="$ROOT/assets/nuxel-background.png" \
    --wallpaper-dump="$WORK/wall.ppm" >"$WORK/host.log" 2>&1 || {
    echo "   FAIL host launcher checks:"; grep -E "FAIL|A28_" "$WORK/host.log" | head -20; exit 1; }
grep -c "   PASS" "$WORK/host.log" | sed 's/^/   checks passed: /'
grep -q A28_LAUNCHER_TESTS_OK "$WORK/host.log" || { tail -20 "$WORK/host.log"; exit 1; }
grep -q "WALLPAPER_OK" "$WORK/host.log" || { echo "   FAIL the wallpaper never loaded"; exit 1; }
grep "WALLPAPER_OK" "$WORK/host.log" | sed 's/^UI_LOG /   /'

echo "== 4. the wallpaper decoder vs an independent reference =="
python3 "$A28/compare-wallpaper.py" --asset "$ROOT/assets/nuxel-background.png" --dump "$WORK/wall.ppm"

echo "== 5. the ARM64 binary =="
"$CROSS" -Os -w -ffreestanding -fno-builtin -nostdlib -static -s -Wl,--build-id=none \
     -o "$WORK/nuxel-ui-a28" "$ROOT/tools/s10plus/nuxel-ui.c" || exit 2
BIN="$WORK/nuxel-ui-a28"
file -b "$BIN" | grep -q aarch64 || { echo "   FAIL not an aarch64 ELF"; exit 1; }
for m in NUXEL_UI_DISPLAY_LOCK_ACQUIRED NUXEL_UI_LAYOUT_VIOLATIONS INPUT_CAPS \
         TOUCH_TAP APP_LAUNCH_RESULT WALLPAPER_OK no-pwa-engine \
         "A28-nuxel-home-launcher-1" NUXEL_UI_STARTING; do
    strings -a "$BIN" | grep -q "$m" || { echo "   FAIL binary lacks marker: $m"; exit 1; }
done
SZ=$(wc -c <"$BIN" | tr -d ' ')
[ "$SZ" -le "$SIZE_BUDGET" ] || { echo "   FAIL $SZ bytes exceeds the live-deploy budget $SIZE_BUDGET"; exit 1; }
echo "   PASS $(basename "$BIN") $SZ bytes (budget $SIZE_BUDGET) $(shasum -a 256 "$BIN" | cut -c1-16)…"
echo "A28_LAUNCHER_GATE_OK"
