#!/usr/bin/env bash
# run-p3-tests.sh — the whole offline test set for build group
# "Priority 3 — Wi-Fi, Time/RTC, Audio, Headphones & Hardware Buttons".
#
# Everything here runs on a workstation with NO phone, NO radio, NO speakers,
# NO headphones, NO /dev/input, NO root and NO network. Nothing in this script
# writes to the phone, starts a service, triggers Recovery / Download Mode,
# reboots anything or claims that any hardware works: live association,
# audibility and an on-device RTC already stay NEEDS_OWNER_TEST by design.
#
#   ./tools/s10plus/a33/tests/run-p3-tests.sh            # all tests
#   ./tools/s10plus/a33/tests/run-p3-tests.sh --quick     # skip the C build leg
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

echo "== Nuxel A33 P3 (connectivity / time / audio / buttons) offline test set =="
echo "root: $ROOT"
echo "quick: $QUICK"

# --- in-tool selftests against the faked roots (verdict logic) --------------------
run_step "wifi diag selftest (5 fixtures)"        bash "$A33/nuxel-wifi-diag.sh" selftest
run_step "time diag selftest (5 fixtures)"        bash "$A33/nuxel-time.sh" selftest
run_step "audio diag selftest (8 fixtures)"       bash "$A33/nuxel-audio-diag.sh" selftest
run_step "headphone diag selftest (7 fixtures)"   bash "$A33/nuxel-headphone-diag.sh" selftest

# --- offline test programs --------------------------------------------------------
run_step "wifi: policy, doc and no-flash invariants"       python3 "$HERE/test-wifi-diag.py"
run_step "time: RTC, timesync, mark/compare arithmetic"    python3 "$HERE/test-time-rtc.py"
run_step "audio: pipeline, low-volume cap, UCM generation" python3 "$HERE/test-audio-diag.py"
run_step "headphone: jack/USB-C detection and routing"     python3 "$HERE/test-headphone-route.py"
run_step "buttons: JSON<->C<->A32 FSM parity + power menu" python3 "$HERE/test-button-fsm.py"
run_step "no hard-coded /dev/input/event<N> gate"          python3 "$HERE/test-no-eventn-literal.py"

# --- daemon syntax gate (stub alsa header; catches a real C error on any host) ----
# This is NOT a build: nothing is linked and the aarch64 build on the guest is
# still the only build. It exists so a syntax error in the daemon cannot hide
# behind "no alsa-lib on this host".
if command -v gcc >/dev/null 2>&1; then
  echo
  echo "==================== daemon syntax gate (stub alsa header) ===================="
  if gcc -std=gnu11 -fsyntax-only -Wall -Wextra -I "$A33/tests/stub-include" "$A33/nuxel-button-manager.c"; then
    RESULTS+=("PASS  daemon syntax gate (nuxel-button-manager.c parses)")
  else
    RESULTS+=("FAIL  daemon syntax gate (nuxel-button-manager.c parses)"); rc_total=1
  fi
fi

# --- optional C build leg (host replay helper; daemon needs a Linux toolchain) ----
# rc=3 is the script's explicit "this host cannot build the daemon" environment
# fact (no alsa-lib / linux/input.h) — a SKIP, never a pass and never a failure.
if [ "$QUICK" = 0 ]; then
  echo
  echo "==================== build the FSM replay helper (host C build) ===================="
  if bash "$A33/build-a33-buttons.sh"; then
    RESULTS+=("PASS  build the FSM replay helper (host C build)")
  else
    rc=$?
    if [ "$rc" = 3 ]; then
      RESULTS+=("SKIP  build the FSM replay helper (host lacks alsa-lib/linux headers; builds on the UTM guest)")
    else
      RESULTS+=("FAIL  build the FSM replay helper (host C build) (rc=$rc)"); rc_total=1
    fi
  fi
fi

# --- optional cross-check: the protected A32 baseline regression guard -------------
# Owned by the preflight group; reported verbatim and does NOT gate this set.
echo
echo "==================== A32 baseline regression guard (optional) ===================="
if [ -x "$ROOT/tools/beta/regression-guard.sh" ]; then
  bash "$ROOT/tools/beta/regression-guard.sh" --no-tests
  echo "regression-guard rc=$?"
else
  echo "SKIP tools/beta/regression-guard.sh not present in this tree"
fi

echo
echo "==================== summary ===================="
for r in "${RESULTS[@]}"; do echo "$r"; done
if [ "$rc_total" = 0 ]; then
  echo "P3-TESTS: ALL PASS"
else
  echo "P3-TESTS: FAILURES PRESENT"
fi
exit "$rc_total"
