#!/bin/sh
set -eu
ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/../../../.." && pwd)
python3 "$ROOT/tools/s10plus/a40/tests/test_launcher_contract.py"
python3 "$ROOT/tools/s10plus/a40/tests/test_system_monitor.py"
node "$ROOT/tools/s10plus/a34/tests/test-touch-keyboard.js"
python3 "$ROOT/tools/s10plus/a39/tests/test_a39_assets.py"
