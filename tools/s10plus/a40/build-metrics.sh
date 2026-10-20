#!/bin/sh
# Build the tiny libc-only metrics endpoint for the S10+.  No host GTK or
# WebKit dependencies are involved.  Selection is capability-based:
#   * aarch64 host  -> native gcc
#   * cross host    -> aarch64-linux-gnu-gcc
# CC always overrides for an explicit toolchain.
set -eu
ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/../../.." && pwd)
OUT=${1:-"$ROOT/build/a40/nuxel-metricsd"}
if [ -z "${CC:-}" ]; then
  case "$(uname -m)" in
    aarch64|arm64) CC=gcc ;;
    *) CC=aarch64-linux-gnu-gcc ;;
  esac
fi
mkdir -p "$(dirname "$OUT")"
# -ffile-prefix-map and -fno-record-gcc-switches remove checkout-path and
# invocation-path variability.  Build-id is content-derived and deterministic.
"$CC" -std=c11 -O2 -Wall -Wextra -Werror \
  -ffile-prefix-map="$ROOT"=. -fno-record-gcc-switches \
  -Wl,--build-id=sha1 \
  "$ROOT/services/nuxel-metrics/nuxel-metricsd.c" -o "$OUT"
file "$OUT"
case "$(file -b "$OUT")" in
  *aarch64*|*ARM\ aarch64*) ;;
  *) echo "ERROR: $OUT is not aarch64" >&2; exit 1 ;;
esac
