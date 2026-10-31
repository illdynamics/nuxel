#!/bin/sh
# PWNAGE-44000 regression gate.
set -eu
ROOT=$(cd "$(dirname "$0")/../.." && pwd)
cd "$ROOT"
fail=0
run() { echo; echo "==== $* ===="; "$@" || fail=1; }
run node pwa/nuxel-home/tests/test-widgets.js
run node pwa/nuxel-home/tests/test-launcher-drag.js
run node pwa/nuxel-home/tests/test-status-indicators.js
run node pwa/nuxel-home/tests/test-qs-indicators.js
run node pwa/nuxel-home/tests/test-qs-wifi-state.js
run node pwa/nuxel-apps/notes/tests/test-notes-save.js
run python3 tests/pwnage44000/test_flashlight_provider.py
run python3 tests/pwnage44000/test_media_thumbnails.py
run python3 tests/pwnage44000/test_files_send_and_render.py
run node tools/s10plus/a33/tests/launcher-registry-test.js
run python3 tools/s10plus/a33/tests/test-button-fsm.py
run python3 tools/s10plus/a33/tests/hw-subsystems/test-led-diag.py
run bash tools/s10plus/a34/tests/run-a34-tests.sh
if [ "$fail" -eq 0 ]; then echo; echo 'PWNAGE-44000 TESTS: ALL PASS'; else echo; echo 'PWNAGE-44000 TESTS: FAILURES'; fi
exit "$fail"
