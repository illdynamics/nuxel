#!/bin/sh
# A34 TOUCHDOWN offline regression set.  No phone, no display, no input device.
#
# Every leg compiles/loads the REAL shipped source:
#   * the button FSM from nuxel-button-fsm.h (Power cancels deferred Bixby);
#   * the real status-bar.js in a minimal DOM (Quick Settings pull-down);
#   * the real button-manager.c source (MT translation on SYN_REPORT).
set -eu
HERE=$(cd "$(dirname "$0")" && pwd)
fail=0

run() {
  echo
  echo "==================== $* ===================="
  if ! "$@"; then fail=1; fi
}

run sh "$HERE/test-fsm-power-bixby.sh"
run python3 "$HERE/test-touch-syn-translation.py"
run sh "$HERE/run-decon-tests.sh"
run node "$HERE/test-qs-gesture.js"
run node "$HERE/test-touch-keyboard.js"
run python3 "$HERE/test-terminal-keyboard.py"
run python3 "$HERE/test-terminal-lifecycle.py"
run sh "$HERE/../../../touchable/run-tests.sh"

echo
if [ "$fail" -eq 0 ]; then
  echo "A34-TESTS: ALL PASS"
else
  echo "A34-TESTS: FAILURES PRESENT"
fi
exit "$fail"
