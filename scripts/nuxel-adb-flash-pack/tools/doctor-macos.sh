#!/usr/bin/env bash
set -euo pipefail
printf 'Nuxel ADB flash pack — host preflight\n'
printf 'Platform: %s %s\n' "$(uname -s)" "$(uname -m)"
for tool in python3 adb shasum; do
  if command -v "$tool" >/dev/null 2>&1; then
    printf 'PASS: %s -> %s\n' "$tool" "$(command -v "$tool")"
  else
    printf 'MISSING: %s\n' "$tool"
  fi
done
python3 - <<'PY'
import sys
print('Python:', sys.version.split()[0])
if sys.version_info < (3,9): raise SystemExit('Python >=3.9 required')
PY
if command -v adb >/dev/null 2>&1; then
  adb version | head -n 2
  printf '\nConnected devices:\n'
  adb devices
fi
cat <<'NOTE'

No device state was changed. Read README.md and run 01-discover.sh first.
For Moto G7 Power (ocean), A/B slot awareness and explicit partitions are mandatory.
NOTE
