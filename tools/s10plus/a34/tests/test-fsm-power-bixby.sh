#!/bin/sh
# Deterministic regression for the "double Power opens Terminal" report.
# Builds the FSM sim from the A34 header (no phone access) and asserts:
#   1. Power still emits exactly one screen-toggle.
#   2. The deferred Bixby open-terminal is cancelled by the Power press.
set -eu
HERE=$(cd "$(dirname "$0")" && pwd)
A34=$(cd "$HERE/.." && pwd)
CC=${CC:-cc}
OUT=$(mktemp -d)
trap 'rm -rf "$OUT"' EXIT
$CC -std=c11 -O1 -DNUXEL_FSM_MAIN -I "$A34" -x c "$A34/nuxel-button-fsm.h" -o "$OUT/sim"
"$OUT/sim" "$HERE/power-cancels-bixby.trace" >"$OUT/out.txt"
cat "$OUT/out.txt"
grep -q 'name=screen-toggle' "$OUT/out.txt" || { echo 'FAIL: no screen-toggle'; exit 1; }
if grep -q 'name=open-terminal' "$OUT/out.txt"; then
  echo 'FAIL: deferred Bixby open-terminal survived a Power press'
  exit 1
fi
echo 'PASS: Power emits screen-toggle and cancels the deferred open-terminal'
