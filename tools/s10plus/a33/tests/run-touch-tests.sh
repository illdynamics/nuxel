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

# nuxel-mt.h intentionally uses the kernel UAPI.  Linux build hosts have it in
# their normal include path; macOS hosts can still run this host-side parser
# test when an installed aarch64 Linux toolchain exposes its sysroot.  Do not
# pretend a missing UAPI header is a parser failure, and do not hard-code a
# Homebrew cellar revision: callers may override NUXEL_LINUX_UAPI_INCLUDE.
mt_uapi_include() {
  if printf '#include <linux/input.h>\n' | cc -E -x c - >/dev/null 2>&1; then
    return 0
  fi
  if [ -n "${NUXEL_LINUX_UAPI_INCLUDE:-}" ] && [ -f "$NUXEL_LINUX_UAPI_INCLUDE/linux/input.h" ]; then
    printf '%s\n' "$NUXEL_LINUX_UAPI_INCLUDE"
    return 0
  fi
  local cross sysroot
  for cross in aarch64-linux-gnu-gcc aarch64-unknown-linux-gnu-gcc; do
    command -v "$cross" >/dev/null 2>&1 || continue
    sysroot="$("$cross" -print-sysroot 2>/dev/null || true)"
    if [ -n "$sysroot" ] && [ -f "$sysroot/usr/include/linux/input.h" ]; then
      printf '%s\n' "$sysroot/usr/include"
      return 0
    fi
  done
  return 1
}

run_mt_parser() {
  local d uapi
  d="$(mktemp -d)" || return 1
  # Expand the private mktemp path while it is in scope; a single-quoted trap
  # body would dereference an unset local after this function returns under
  # `set -u`.
  trap "rm -rf '$d'" RETURN
  if uapi="$(mt_uapi_include)"; then
    if [ -n "$uapi" ]; then
      cc -std=gnu11 -O2 -Wall -Wextra -Wno-unused-function -isystem "$uapi" \
        -o "$d/test-touch-mt" "$HERE/test-touch-mt.c"
    else
      cc -std=gnu11 -O2 -Wall -Wextra -Wno-unused-function \
        -o "$d/test-touch-mt" "$HERE/test-touch-mt.c"
    fi
    "$d/test-touch-mt"
    return $?
  fi
  echo "SKIP MT parser replay: linux/input.h is unavailable (set NUXEL_LINUX_UAPI_INCLUDE)"
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
run_step "libinput shim: the LD_PRELOAD invocation chain" python3 "$HERE/test-libinput-shim-invocation.py"
run_step "touch tracer: layers, gate, boundedness" python3 "$HERE/test-touch-trace.py"
run_step "MT frame parser: DOWN at SYN, tap != back, bottom swipe = home" run_mt_parser
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
