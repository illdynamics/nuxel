#!/usr/bin/env bash
# generate-fixtures.sh — regenerate camera-DT test fixtures from DTS sources.
# Deterministic and idempotent. Produces .dtb files in fixtures/ from
# fixture-src/*.dts. The large 8MB .img negative containers (bad-magic,
# truncated, wrong-board, wrong-rev) are historical/device-derived and are
# NOT regenerated here (they require the real Samsung DTH container); they are
# documented in README-fixtures.md.
set -euo pipefail
ROOT=$(cd "$(dirname "$0")" && pwd)
SRC="$ROOT/fixture-src"
OUT="$ROOT/fixtures"
mkdir -p "$OUT"

for dts in "$SRC"/*.dts; do
    name=$(basename "$dts" .dts)
    dtc -q -I dts -O dtb -o "$OUT/$name.dtb" "$dts"
    echo "built $name.dtb"
done
echo "fixtures regenerated in $OUT"
