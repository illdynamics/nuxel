#!/usr/bin/env bash
# Offline test entry point for Priority 4 (bg-04-userspace-completion).
#
# One command that re-derives every briq-04a/04b/04c acceptance claim from the
# repository alone:
#
#   briq-04a  docs/beta-finalization/system/DEPENDENCY-REPORT.md
#             images/s10plus/packages-manifest.json   (real Fedora 43 metadata)
#             tools/s10plus/a33/verify-packages.py
#   briq-04b  services/** + shell/config/systemd-user/**   (boot graph)
#             tools/s10plus/a33/verify-service-graph.py
#             services/nuxel-console/test-console-ownership.py (single-owner guard)
#   briq-04c  pwa/nuxel-common/**, services/nuxel-{bridge,portal,notifications,web}/**
#             services/nuxel-bridge/test-launcher-activation.py (registry -> launch)
#             services/nuxel-web (static PWA server)
#             tools/s10plus/a33/verify-app-registry.py
#
# Nothing here starts the phone, writes a partition, or touches .qq / RUN_ROOT.
# The result is OFFLINE_TESTED: a green run is NOT a claim that the handset boots
# (`systemctl is-system-running` belongs to the live-deployment group).
#
# Usage:
#   tools/s10plus/a33/tests/run-userspace-tests.sh            # everything
#   tools/s10plus/a33/tests/run-userspace-tests.sh --fast     # skip the network
#                                                             # metadata refresh
set -uo pipefail

ROOT="$(cd "$(dirname "$0")/../../../.." && pwd)"
TESTS="$ROOT/tools/s10plus/a33/tests"
OUT="$ROOT/build/pkgmeta/userspace-test-results.json"
FAST=0
[ "${1:-}" = "--fast" ] && FAST=1

PASS=0; FAIL=0; SKIP=0
declare -a RESULTS=()

record() { # name, status, detail
  RESULTS+=("{\"name\": \"$1\", \"status\": \"$2\", \"detail\": \"$3\"}")
  case "$2" in
    PASS) PASS=$((PASS+1)); printf '  PASS  %s\n' "$1" ;;
    SKIP) SKIP=$((SKIP+1)); printf '  SKIP  %s (%s)\n' "$1" "$3" ;;
    *)    FAIL=$((FAIL+1)); printf '  FAIL  %s (%s)\n' "$1" "$3" ;;
  esac
}

run_py() { # name, script, [args...]
  local name="$1"; shift
  local script="$1"; shift
  local log; log="$(mktemp)"
  if python3 "$script" "$@" >"$log" 2>&1; then
    record "$name" PASS "$(tail -n 1 "$log" | tr -d '"' | cut -c1-120)"
  else
    record "$name" FAIL "$(grep -m1 -E 'FAIL|Error|Traceback' "$log" | tr -d '"' | cut -c1-160)"
    echo "----- $name (tail) -----"; tail -n 15 "$log"
  fi
  rm -f "$log"
}

run_node() { # name, script
  local name="$1" script="$2"
  local log; log="$(mktemp)"
  if ! command -v node >/dev/null 2>&1; then
    record "$name" SKIP "node not installed on this host"
    rm -f "$log"; return
  fi
  if node "$script" >"$log" 2>&1; then
    record "$name" PASS "$(grep -m1 -E 'ALL .*OK|ALL TESTS PASSED|OK$' "$log" | cut -c1-120)"
  else
    record "$name" FAIL "$(grep -m1 -E 'FAIL|Error' "$log" | cut -c1-160)"
    echo "----- $name (tail) -----"; tail -n 12 "$log"
  fi
  rm -f "$log"
}

echo "== Priority 4 userspace offline tests =="
echo "-- briq-04a  Fedora 43 package manifest + dependency report"
if [ "$FAST" = "1" ]; then
  run_py "packages: manifest + real metadata resolution" \
         "$ROOT/tools/s10plus/a33/verify-packages.py" --offline --quiet \
         --report "$ROOT/build/pkgmeta/report-offline.json"
else
  run_py "packages: manifest + real metadata resolution" \
         "$TESTS/test-packages-manifest.py"
fi

echo "-- briq-04b  service definitions + boot graph"
run_py "service-graph: repository boot graph" \
       "$ROOT/tools/s10plus/a33/verify-service-graph.py" --quiet \
       --json "$ROOT/build/pkgmeta/service-graph.json"
run_py "service-graph: validator detects defects (mutation test)" \
       "$TESTS/test-service-graph.py"
run_py "console: single-owner live console (unit + flock guard + builder)" \
       "$ROOT/services/nuxel-console/test-console-ownership.py"

echo "-- briq-04c  application infrastructure"
run_py "apps: canonical registry + manifests + bridge pin" \
       "$ROOT/tools/s10plus/a33/verify-app-registry.py"
run_py "apps: bridge/HTTP/registry/D-Bus policy" \
       "$TESTS/test-app-infrastructure.py"
run_py "apps: launcher -> bridge activation (mediating, non-executing)" \
       "$ROOT/services/nuxel-bridge/test-launcher-activation.py"
run_py "web: static PWA server docroot + wiring" \
       "$TESTS/test-web-server.py"
run_py "portal: consent + one-shot grant policy" \
       "$ROOT/services/nuxel-portal/test-portal-policy.py"
run_py "notifications: persistence + bounded history" \
       "$ROOT/services/nuxel-notifications/test-notifications-persistence.py"
run_node "apps: shared bridge client (node)" "$ROOT/pwa/nuxel-common/test-bridge.js"
run_node "apps: PWA wiring (node)" "$ROOT/pwa/nuxel-common/verify-wiring.js"

mkdir -p "$(dirname "$OUT")"
{
  printf '{\n  "tool": "run-userspace-tests.sh",\n  "component": "bg-04-userspace-completion",\n'
  printf '  "verdict": "%s",\n' "$([ "$FAIL" -eq 0 ] && echo OFFLINE_TESTED || echo FAILED)"
  printf '  "pass": %d, "fail": %d, "skip": %d,\n' "$PASS" "$FAIL" "$SKIP"
  printf '  "results": [\n'
  for i in "${!RESULTS[@]}"; do
    printf '    %s%s\n' "${RESULTS[$i]}" "$([ "$i" -lt $((${#RESULTS[@]}-1)) ] && echo ,)"
  done
  printf '  ]\n}\n'
} > "$OUT"

echo
echo "pass=$PASS fail=$FAIL skip=$SKIP -> $([ "$FAIL" -eq 0 ] && echo OFFLINE_TESTED || echo FAILED)"
echo "results: $OUT"
[ "$FAIL" -eq 0 ]
