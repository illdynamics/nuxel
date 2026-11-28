#!/usr/bin/env bash
# Self-contained SYNTHETIC binary-FDT, DTBO, BOOT, semantic-diff and signed
# release-gate negative tests. Exit nonzero on any fixture failure.
# This is NOT a real-device Prompt00 pass or a flashing authorization.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
python3 "$ROOT/tools/s10plus/tests/test-camera-offline-gates.py" -v
printf '\nSYNTHETIC OFFLINE REGRESSIONS PASS; LIVE PROMPT00 STATUS: NOT VERIFIED\n'
