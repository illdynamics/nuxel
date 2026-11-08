#!/bin/sh
# Power+Volume must not leak the single-key classes.
#   * Volume-first: the already-sent volume step is undone by volume-restore.
#   * Power release: no screen-toggle while a chord was being formed.
set -eu
HERE=$(cd "$(dirname "$0")" && pwd)
CC=${CC:-cc}
OUT=$(mktemp -d)
trap 'rm -rf "$OUT"' EXIT
"$CC" -std=c11 -O1 -DNUXEL_FSM_MAIN -x c "$HERE/../nuxel-button-fsm.h" -o "$OUT/fsm-sim"
"$OUT/fsm-sim" "$HERE/chord-no-side-effects.trace" > "$OUT/out.txt"
grep -q 'name=volume-up' "$OUT/out.txt" || { echo 'FAIL: plain volume step was lost'; exit 1; }
grep -q 'name=volume-restore' "$OUT/out.txt" || { echo 'FAIL: chord did not restore the volume step'; exit 1; }
grep -q 'name=sound-mode-cycle' "$OUT/out.txt" || { echo 'FAIL: sound-mode chord did not fire'; exit 1; }
if grep -q 'name=screen-toggle' "$OUT/out.txt"; then echo 'FAIL: chord also toggled the display'; exit 1; fi
echo 'PASS: Power+Volume chord restores volume and suppresses screen-toggle'
