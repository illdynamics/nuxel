#!/usr/bin/env bash
# A52 camera offline suite.  These prove app/backend/config correctness offline;
# they can never yield a VERIFIED_ON_S10PLUS hardware claim.
set -u
HERE="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$HERE/../.." && pwd)"
rc=0
run() { printf '\n=== %s ===\n' "$*"; "$@" || rc=1; }

run python3 "$HERE/test-portal-contract.py"
run python3 "$HERE/test-camera-frontend.py"
run python3 "$HERE/test-camera-inventory.py"
run python3 "$ROOT/services/nuxel-bridge/test-media-store.py"
run python3 "$ROOT/services/nuxel-bridge/test-camera-bridge.py" 2>/dev/null
run python3 "$ROOT/tools/s10plus/a33/tests/hw-subsystems/test-camera-diag.py"
run bash "$ROOT/tools/s10plus/a33/nuxel-camera-diag.sh" selftest

printf '\n%s\n' "$([ $rc = 0 ] && echo 'ALL A52 OFFLINE SUITES PASS (APPLICATION_READY; hardware remains HARDWARE_BLOCKED)' || echo 'FAILURES ABOVE')"
exit $rc
