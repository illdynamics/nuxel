#!/usr/bin/env bash
# Offline runner for the Priority 7b hardware-subsystem work (build group bg-08).
# Runs every per-subsystem offline suite and every tool self-test. These suites
# prove CONFIG + DIAGNOSTIC behaviour offline; they can never yield
# VERIFIED_ON_S10PLUS and they never touch real hardware.
set -u
HERE="$(cd "$(dirname "$0")" && pwd)"
TOOLS="$(cd "$HERE/../.." && pwd)"
rc=0
run() { printf '\n=== %s ===\n' "$*"; "$@" || rc=1; }
for t in "$HERE"/test-*.py; do run python3 "$t"; done
for s in power haptics led bluetooth nfc gnss sensors camera modem microsd; do
  [ -x "$TOOLS/nuxel-$s-diag.sh" ] && run bash "$TOOLS/nuxel-$s-diag.sh" selftest
done
printf '\n%s\n' "$([ $rc = 0 ] && echo 'ALL HARDWARE-SUBSYSTEM OFFLINE SUITES PASS (OFFLINE_TESTED; owner tests remain NEEDS_OWNER_TEST)' || echo 'FAILURES ABOVE')"
exit $rc
