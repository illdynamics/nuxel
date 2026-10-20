#!/usr/bin/env bash
# Offline test runner for the Nuxel phone data layer.
#
# No device, no display, no glib, no ModemManager: plain C11 plus the C library.
# The build output goes to build/nuxel-phone-data/ inside the repository tree so
# nothing is written outside the workspace.
set -uo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$HERE/../../.." && pwd)"
OUT="${ROOT}/build/nuxel-phone-data"
CC="${CC:-cc}"

mkdir -p "$OUT"
echo "== building nuxel-phone-data tests with ${CC} =="
if ! "$CC" -std=c11 -Wall -Wextra -Werror -O1 \
      "$HERE/nuxel-phone-data.c" "$HERE/nuxel-phone-data-test.c" \
      -o "$OUT/nuxel-phone-data-test"; then
    echo "FAIL build"
    exit 1
fi
echo "PASS build ($OUT/nuxel-phone-data-test)"
"$OUT/nuxel-phone-data-test"
rc=$?
[ "$rc" -eq 0 ] && echo "== phone data layer OK ==" || echo "== $rc failing check(s) =="
exit "$rc"
