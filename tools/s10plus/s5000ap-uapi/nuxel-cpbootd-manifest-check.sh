#!/usr/bin/env bash
# nuxel-cpbootd-manifest-check.sh — caller-side preflight for nuxel-cpbootd.
#
# Verifies that the immutable Stage-04 execution manifest file hashes to an
# exact expected SHA-256 BEFORE nuxel-cpbootd is invoked with --really-boot.
#
# This closes the loop documented in nuxel-cpbootd.c: the daemon deliberately
# does NOT hardcode the expected manifest hash (to avoid a stale inline value
# silently passing). This tool verifies the manifest file against a value that
# the owner/operator supplies at the moment of the trial.
#
# Usage:
#   nuxel-cpbootd-manifest-check.sh <manifest-file> <expected-sha256-hex>
#
# Exit status:
#   0  — match (prints the verified lowercase hex to stdout)
#   1  — file missing/unreadable or hash mismatch
#   2  — usage error (bad arg count / malformed hex)
#
# This script NEVER touches the modem, /dev/umts_*, a block device, or any
# system service. It is pure userspace file hashing.
set -euo pipefail

usage() { echo "usage: $0 <manifest-file> <expected-sha256-hex>" >&2; exit 2; }

[[ $# -eq 2 ]] || usage
MANIFEST="$1"
EXPECT="$2"

# Validate the expected hex is exactly 64 lowercase/uppercase hex chars.
[[ "$EXPECT" =~ ^[0-9a-fA-F]{64}$ ]] || { echo "error: expected sha256 not 64 hex chars" >&2; exit 2; }

[[ -f "$MANIFEST" ]] || { echo "error: manifest not a regular file: $MANIFEST" >&2; exit 1; }

# Prefer sha256sum (coreutils) then shasum (BSD/macOS) fallback.
if command -v sha256sum >/dev/null 2>&1; then
    ACTUAL="$(sha256sum "$MANIFEST" | awk '{print $1}')"
elif command -v shasum >/dev/null 2>&1; then
    ACTUAL="$(shasum -a 256 "$MANIFEST" | awk '{print $1}')"
else
    echo "error: no sha256sum/shasum available" >&2
    exit 1
fi

# Case-insensitive compare.
ACTUAL_LC="$(printf '%s' "$ACTUAL" | tr 'A-F' 'a-f')"
EXPECT_LC="$(printf '%s' "$EXPECT" | tr 'A-F' 'a-f')"

if [[ "$ACTUAL_LC" != "$EXPECT_LC" ]]; then
    echo "error: manifest sha mismatch (got $ACTUAL_LC, want $EXPECT_LC)" >&2
    exit 1
fi

printf '%s\n' "$ACTUAL_LC"
