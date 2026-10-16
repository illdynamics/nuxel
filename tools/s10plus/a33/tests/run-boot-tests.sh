#!/usr/bin/env bash
# run-boot-tests.sh — the whole offline bg-02 test set ("Priority 2 — Boot
# stability, animation handoff & UTM launcher parity"), one command.
#
#   ./tools/s10plus/a33/tests/run-boot-tests.sh            # all legs
#   ./tools/s10plus/a33/tests/run-boot-tests.sh --quick     # skip the optional build
#   ./tools/s10plus/a33/tests/run-boot-tests.sh --build     # also build the aarch64 bridge
#
# Everything here runs on a workstation with NO phone, NO root, NO display and NO
# /dev/fb0.  Nothing in this script writes to the phone, starts a service, takes the
# framebuffer, reboots anything or touches a partition.
#
# The compiled-artefact legs (the golden-bytes test's binary layer and the optional
# build) need a Linux/aarch64 toolchain: they use $VM (default nuxel@192.168.64.3,
# the UTM Fedora 43 guest) when it is reachable, and REPORT A SKIP — never a pass —
# when it is not.  The source-level proofs always run.
set -uo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
A33="$(cd "$HERE/.." && pwd)"
ROOT="$(cd "$A33/../../.." && pwd)"
VM="${VM:-nuxel@192.168.64.3}"
QUICK=0
DO_BUILD=0
for a in "$@"; do
  case "$a" in
    --quick) QUICK=1 ;;
    --build) DO_BUILD=1 ;;
    -h|--help) sed -n '2,22p' "$0"; exit 0 ;;
    *) echo "run-boot-tests: unknown option: $a" >&2; exit 2 ;;
  esac
done

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
skip_step() { echo; echo "==================== $1 ===================="; echo "SKIP  $2"; RESULTS+=("SKIP  $1"); }

echo "== Nuxel A33 boot-surface offline test set (bg-02) =="
echo "root: $ROOT"
echo "vm:   $VM (compiled-artefact legs run there; a skip is never a pass)"

# Compiled-artefact legs: hand the tests the VM so they can run the real aarch64
# binary when it exists, and degrade to the source layer when it does not.
export NUXEL_VM="$VM"

run_step "boot-surface wiring contract (briq-02a..02e)" \
  python3 "$HERE/test-boot-surface-contract.py"
run_step "colour order: XRGB8888 -> DECON ABGR8888 golden bytes (briq-02c)" \
  python3 "$HERE/test-colour-order.py"
run_step "handoff: shared decision table + single-owner proof (briq-02a)" \
  python3 "$A33/nuxel-anim-handoff.py" selftest
run_step "handoff: replayable timing harness (briq-02a)" \
  python3 "$A33/nuxel-anim-handoff.py" simulate
run_step "verbose boot: durable setting, migration, upgrade-safety (briq-02b)" \
  python3 "$A33/nuxel-verbose-boot.py" --selftest
if command -v node >/dev/null 2>&1; then
  run_step "settings store contract (briq-02b)" node "$HERE/settings-store-test.js"
  run_step "launcher registry / cache parity (briq-02d)" node "$HERE/launcher-registry-test.js"
  run_step "ten-zone safe areas: geometry + cluster exclusion (briq-02e)" \
    node "$HERE/../../a32/tests/safe-zones-test.js"
else
  skip_step "settings store contract (briq-02b)" "node absent"
  skip_step "launcher registry / cache parity (briq-02d)" "node absent"
  skip_step "ten-zone safe areas: geometry + cluster exclusion (briq-02e)" "node absent"
fi

if [ "$QUICK" = 0 ] || [ "$DO_BUILD" = 1 ]; then
  if [ "$DO_BUILD" = 1 ]; then
    echo
    echo "==================== build the A33 bridge (aarch64) ===================="
    "$A33/build-a33-boot.sh"
    brc=$?
    case "$brc" in
      0) RESULTS+=("PASS  A33 bridge built as an aarch64 ELF and self-tested on the build channel") ;;
      3) RESULTS+=("SKIP  A33 bridge build skipped: BLOCKED_EXTERNAL_RESOURCE (NOT a pass)") ;;
      *) RESULTS+=("FAIL  A33 bridge build (rc=$brc)"); rc_total=1 ;;
    esac
    if [ -x "$ROOT/build/out/s10plus/a33-boot/nuxel-wl-fb" ]; then
      run_step "colour golden bytes against the compiled artefact" \
        python3 "$HERE/test-colour-order.py"
    else
      skip_step "colour golden bytes against the compiled artefact" "no artefact was built"
    fi
  else
    skip_step "aarch64 build of the A33 bridge" "pass --build to attempt it (needs the UTM guest or CROSS_COMPILE)"
  fi
fi

echo
echo "==================== summary ===================="
for r in "${RESULTS[@]}"; do echo "$r"; done
if [ "$rc_total" = 0 ]; then
  echo "BOOT-TESTS: ALL PASS"
  echo "NOTE: no boot, no panel and no finger was involved.  The on-glass handoff, the"
  echo "      colour order on the glass, the verbose-boot effect and the launcher parity"
  echo "      stay NEEDS_OWNER_TEST (handset) / VERIFIED_IN_VM_ONLY (VM) until observed."
else
  echo "BOOT-TESTS: FAILURES PRESENT"
fi
exit "$rc_total"
