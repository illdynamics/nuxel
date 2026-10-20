#!/bin/bash
# Offline test suite for the Nuxel permission manager (briq-05a).
# No root, no device, no network required.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PERM_DIR="$(dirname "$HERE")"
REPO="$(cd "$PERM_DIR/../../.." && pwd)"
PY="${PYTHON:-python3}"

echo "== nuxel-permd self-test =="
"$PY" "$PERM_DIR/nuxel-permd.py" self-test

echo
echo "== unit tests =="
"$PY" "$HERE/test-permissions.py"

echo
echo "== verify-permissions.py (repo mode, throwaway store) =="
STORE="$(mktemp -d)"
trap 'rm -rf "$STORE"' EXIT
"$PY" "$REPO/tools/s10plus/a33/verify-permissions.py" --store "$STORE" --quiet

echo
echo "== enforcement matrix against the S10+ 4.14.253 fixture =="
"$PY" "$PERM_DIR/nuxel-permd.py" \
    --fixture "$REPO/tools/s10plus/a33/security-fixtures/s10plus-4.14.253.json" \
    enforcement-matrix

echo
echo "ALL PERMISSION TESTS PASSED"
