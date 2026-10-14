#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
for s in "$ROOT"/scripts/*.sh "$ROOT"/tools/*.sh; do
  bash -n "$s"
done
python3 -m compileall -q "$ROOT/tools" "$ROOT/tests"
echo 'PASS: shell syntax and Python bytecode compilation'
