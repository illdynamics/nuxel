#!/bin/sh
# Cross-build the tiny libc-only metrics endpoint for the S10+; no host GTK or
# WebKit dependencies are involved.
set -eu
ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/../../.." && pwd)
OUT=${1:-"$ROOT/build/a40/nuxel-metricsd"}
CC=${CC:-aarch64-linux-gnu-gcc}
mkdir -p "$(dirname "$OUT")"
"$CC" -std=c11 -O2 -Wall -Wextra -Werror "$ROOT/services/nuxel-metrics/nuxel-metricsd.c" -o "$OUT"
file "$OUT"
