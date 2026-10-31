#!/bin/sh
# PWNAGE-44000: Power + Volume Down is decided as the screenshot chord before
# any long-press power menu / volume step, using the ACTIVE A34 FSM core.
set -eu
HERE=$(cd "$(dirname "$0")" && pwd)
A34=$(cd "$HERE/.." && pwd)
TRACE="$A34/../a33/tests/fixtures-p3/button-fsm/chord-power-voldown-screenshot.trace"
CC=${CC:-cc}
OUT=$(mktemp -d)
trap 'rm -rf "$OUT"' EXIT
$CC -std=c11 -O1 -DNUXEL_FSM_MAIN -I "$A34" -x c "$A34/nuxel-button-fsm.h" -o "$OUT/sim"
"$OUT/sim" "$TRACE" >"$OUT/out.txt"
cat "$OUT/out.txt"
grep -q 'name=screenshot' "$OUT/out.txt" || { echo 'FAIL: screenshot chord did not fire'; exit 1; }
if grep -q 'menu-open\|name=volume-down' "$OUT/out.txt"; then
  echo 'FAIL: chord leaked into power-menu or volume class'; exit 1
fi
echo 'PASS: Power+VolumeDown maps to screenshot and suppresses single-key classes'
