#!/bin/sh
# ============================================================================
# build-a28.sh — build the A28 Nuxel Home launcher for the Galaxy S10+.
#
# A28 = the UTM launcher (Nuxel Home, pwa/nuxel-home/) on the S10+ panel:
#   * the app registry, order, docking, colours, geometry and icons are
#     REGENERATED from the launcher's own files (js/apps.js, css/style.css,
#     app_registry.json) — never hand-edited;
#   * the freestanding aarch64 renderer draws the launcher, decodes the
#     launcher's wallpaper asset at runtime, and launches apps through the
#     registry's own commands;
#   * the A23..A27 diagnostic pages are retained as the fallback interface.
#
# Every step is gated.  The script never claims success it cannot show:
# a failing gate exits non-zero and names the gate.
#
# Usage:
#   sh tools/s10plus/a28/build-a28.sh            # regenerate + gate + build
#   sh tools/s10plus/a28/build-a28.sh --report   # also write the build report
#   sh tools/s10plus/a28/build-a28.sh --rev      # print the delivery rev only
# Exit: 0 ok, 1 a gate failed, 2 a required tool/input is missing.
# ============================================================================
set -eu
ROOT=$(cd "$(dirname "$0")/../../.." && pwd)
A28="$ROOT/tools/s10plus/a28"
WORK="$ROOT/build/out/s10plus/a28"
CROSS=${NUXEL_AARCH64_CC:-aarch64-linux-gnu-gcc}
REPORT=0
for a in "$@"; do
    case "$a" in
        --report) REPORT=1 ;;
        --rev) cat "$A28/nuxel-ui.rev"; exit 0 ;;
        -h|--help) sed -n '2,22p' "$0"; exit 0 ;;
        *) echo "unknown option: $a" >&2; exit 2 ;;
    esac
done
command -v python3 >/dev/null 2>&1 || { echo "ERROR: python3 required" >&2; exit 2; }
command -v "$CROSS" >/dev/null 2>&1 || { echo "ERROR: $CROSS required" >&2; exit 2; }
mkdir -p "$WORK"

echo "[a28] 1/4 regenerating the launcher tables from the launcher's own sources"
python3 "$A28/gen-launcher.py"
python3 "$A28/make-emoji-atlas.py"

echo "[a28] 2/4 running the A28 gate (registry, ABI, host-measured launcher, wallpaper)"
sh "$A28/test-launcher.sh" >"$WORK/gate.log" 2>&1 || { tail -30 "$WORK/gate.log"; echo "[a28][FAIL] gate"; exit 1; }
grep -E "checks passed|WALLPAPER_OK|WALLPAPER_DECODE_OK|PASS nuxel-ui-a28|A28_LAUNCHER_GATE_OK" "$WORK/gate.log"

REV=$(cat "$A28/nuxel-ui.rev")
echo "[a28] 3/4 installing the delivery binary"
cp -f "$WORK/nuxel-ui-a28" "$WORK/nuxel-ui-a28.$REV"
ls -l "$WORK/nuxel-ui-a28.$REV" | awk '{print "        " $NF "  " $5 " bytes"}'
shasum -a 256 "$WORK/nuxel-ui-a28.$REV" | awk '{print "        sha256 " $1}'

echo "[a28] 4/4 delivery pointers"
cat <<EOF
        rev         : $REV
        live deploy : scripts/s10plus-debug-pack/nuxel-live-deploy.sh \\
                        $WORK/nuxel-ui-a28.$REV \\
                        --to /usr/bin/nuxel-ui --restart nuxel-ui --pin $REV
        BOOT carrier: sh tools/s10plus/a25/../build-a25-initramfs.sh   (stages
                        tools/s10plus/a28/nuxel-ui.service + nuxel-ui.rev)
        verify      : sh tools/s10plus/a28/test-launcher.sh
EOF

if [ "$REPORT" = 1 ]; then
    R="$WORK/a28-report.txt"
    {
        echo "nuxel-a28-build-report"
        echo "rev=$REV"
        echo "built_at_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
        echo "binary=$WORK/nuxel-ui-a28.$REV"
        echo "size_bytes=$(wc -c <"$WORK/nuxel-ui-a28.$REV" | tr -d ' ')"
        echo "sha256=$(shasum -a 256 "$WORK/nuxel-ui-a28.$REV" | cut -d' ' -f1)"
        echo "apps_js_sha256=$(grep -o 'apps.js *sha256 [0-9a-f]*' "$A28/generated/nuxel-launcher.h" | awk '{print $3}')"
        echo "style_css_sha256=$(grep -o 'style.css *sha256 [0-9a-f]*' "$A28/generated/nuxel-launcher.h" | awk '{print $3}')"
        echo "gate_log=$WORK/gate.log"
        echo "gate_result=OK"
    } >"$R"
    echo "[a28] report: $R"
fi
echo "[a28] A28 BUILD OK — deploy with the command above (no reflash needed)."
