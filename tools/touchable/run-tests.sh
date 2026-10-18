#!/bin/sh
set -eu
ROOT=$(CDPATH= cd -- "$(dirname "$0")/../.." && pwd)
node "$ROOT/tools/touchable/test-launcher-input.js"
python3 "$ROOT/tools/touchable/test-transfer-retry.py"
python3 "$ROOT/tools/beta/live/tests/test_owner_capture.py"
python3 -m py_compile "$ROOT/tools/touchable/nuxel-touch-90s-test.py" "$ROOT/tools/touchable/deploy-pwa.py"
if [ "${TOUCHABLE_BROWSER_TESTS:-0}" = 1 ]; then
    node "$ROOT/tools/touchable/test-browser.cjs"
else
    echo 'SKIP synthetic browser coverage: set TOUCHABLE_BROWSER_TESTS=1 after installing Playwright in build/touchable/browser'
fi
