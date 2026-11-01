#!/bin/sh
# PWNAGE-45000 regression gate.
set -eu
ROOT=$(cd "$(dirname "$0")/../.." && pwd)
cd "$ROOT"
fail=0
run() { echo; echo "==== $* ===="; "$@" || fail=1; }
run python3 tests/pwnage45000/test_pwnage45000.py
run python3 tools/s10plus/a33/tests/hw-subsystems/test-nfc-diag.py
run python3 tools/s10plus/a33/tests/hw-subsystems/test-led-diag.py
run python3 tests/pwnage44000/test_flashlight_provider.py
run node tools/s10plus/a33/tests/launcher-registry-test.js
run python3 tests/pwnage34000/test_connection_modes.py
run python3 -m compileall -q services/nuxel-bridge/src services/nuxel-notifications/src services/nuxel-s10/bin/nuxel-mtp-server
if [ "$fail" -eq 0 ]; then echo; echo 'PWNAGE-45000 TESTS: ALL PASS'; else echo; echo 'PWNAGE-45000 TESTS: FAILURES'; fi
exit "$fail"
