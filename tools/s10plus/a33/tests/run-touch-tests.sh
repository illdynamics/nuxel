#!/usr/bin/env bash
# run-touch-tests.sh — the whole offline touch-pipeline test set, one command.
#
# Everything here runs on a workstation with NO phone, NO libinput, NO /dev/input
# and NO root.  It is the gate for build group "Priority 0 — Touchscreen &
# Reliable Interactive Input".  Nothing in this script writes to the phone, starts
# a service, arms an input node or reboots anything.
#
#   ./tools/s10plus/a33/tests/run-touch-tests.sh            # all tests
#   ./tools/s10plus/a33/tests/run-touch-tests.sh --quick     # skip the shim build
set -uo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
A33="$(cd "$HERE/.." && pwd)"
ROOT="$(cd "$A33/../../.." && pwd)"
QUICK=0
[ "${1:-}" = "--quick" ] && QUICK=1

rc_total=0
declare -a RESULTS=()

run_step() {   # run_step <name> <cmd...>
  local name="$1"; shift
  echo
  echo "==================== $name ===================="
  "$@"
  local rc=$?
  if [ "$rc" = 0 ]; then RESULTS+=("PASS  $name"); else RESULTS+=("FAIL  $name (rc=$rc)"); rc_total=1; fi
  return 0
}

echo "== Nuxel A33 touch-pipeline offline test set =="
echo "root: $ROOT"
echo "quick: $QUICK"

if [ "$QUICK" = 0 ]; then
  run_step "build the libinput shim (host selftest + aarch64 .so)" \
    "$A33/build-libinput-shim.sh" --selftest
fi
run_step "libinput shim: capability fixtures"      python3 "$HERE/test-libinput-path-fixture.py"
run_step "libinput shim: A31/A33 parity"           python3 "$HERE/test-libinput-parity.py"
run_step "touch tracer: layers, gate, boundedness" python3 "$HERE/test-touch-trace.py"
run_step "boot-mode guard: LPM detection + gates"  python3 "$HERE/test-bootmode-guard.py"
run_step "capture harness: commands, gate, no repo litter" python3 "$HERE/test-capture-harness.py"
run_step "no hard-coded /dev/input/event<N> gate"  python3 "$HERE/test-no-eventn-literal.py"

# OPTIONAL cross-check: the A32 baseline regression guard (owned by the preflight
# group).  Its result is reported verbatim and does NOT gate the touch test set,
# because another build group may be writing it concurrently.
echo
echo "==================== A32 baseline regression guard (optional) ===================="
if [ -x "$ROOT/tools/beta/regression-guard.sh" ]; then
  # --no-tests keeps this fast (hash-only); run it without it for the full gate.
  bash "$ROOT/tools/beta/regression-guard.sh" --no-tests
  echo "regression-guard rc=$?"
else
  echo "SKIP tools/beta/regression-guard.sh not present in this tree"
fi

echo
echo "==================== summary ===================="
for r in "${RESULTS[@]}"; do echo "$r"; done
if [ "$rc_total" = 0 ]; then
  echo "TOUCH-TESTS: ALL PASS"
else
  echo "TOUCH-TESTS: FAILURES PRESENT"
fi
exit "$rc_total"
