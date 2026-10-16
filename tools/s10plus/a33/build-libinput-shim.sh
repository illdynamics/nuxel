#!/usr/bin/env bash
# build-libinput-shim.sh — build the A33 capability-based libinput shim.
#
# Two artifacts, two purposes:
#   1. nuxel-libinput-path-selftest  (HOST cc, -DNUXEL_SHIM_SELFTEST)
#        the decision + hotplug logic compiled for this machine, driven by the
#        synthetic sysfs fixtures in tools/s10plus/a33/tests/fixtures/.  This is
#        what the offline tests run; it never touches /dev/input or libinput.
#   2. libnuxel-libinput-path.so     (aarch64-linux-gnu, -shared -fPIC)
#        the deployed interposer, LD_PRELOADed into phoc.  Undefined libinput /
#        libseat symbols are resolved from the process at load time (that is the
#        point of an interposer), so the build needs no libinput headers.
#
# Cross-compiler resolution order:
#   $CROSS (default aarch64-linux-gnu-gcc)  ->  the UTM guest (VM=...)  ->  FAIL
# There is no flashing, no device write and no service restart anywhere here.
#
# Usage:
#   ./build-libinput-shim.sh              # selftest (always) + .so (best effort)
#   ./build-libinput-shim.sh --selftest   # host selftest only
#   ./build-libinput-shim.sh --vm         # force the UTM-guest build for the .so
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$HERE/../../.." && pwd)"
SRC="$HERE/nuxel-libinput-path.c"
OUT="$ROOT/build/out/s10plus/a33"
VM="${VM:-nuxel@192.168.64.3}"
CROSS="${CROSS:-aarch64-linux-gnu-gcc}"
MODE="${1:-all}"
mkdir -p "$OUT"

HOSTCC="${HOSTCC:-cc}"
CFLAGS_COMMON="-O2 -Wall -Wextra -Wno-unused-parameter -std=gnu11"

echo "== 1. host selftest binary (offline decision logic) =="
"$HOSTCC" $CFLAGS_COMMON -DNUXEL_SHIM_SELFTEST -o "$OUT/nuxel-libinput-path-selftest" "$SRC"
echo "   -> $OUT/nuxel-libinput-path-selftest"
"$OUT/nuxel-libinput-path-selftest" --scan "$HERE/tests/fixtures/sec-ts-only" | tail -4
[ "$MODE" = "--selftest" ] && { echo "== selftest only: done =="; exit 0; }

echo "== 2. aarch64 shared object (deployed interposer) =="
built=0
if [ "$MODE" != "--vm" ] && command -v "$CROSS" >/dev/null 2>&1; then
  echo "-- cross: $CROSS"
  if "$CROSS" $CFLAGS_COMMON -shared -fPIC -o "$OUT/libnuxel-libinput-path.so" "$SRC" -ldl 2>"$OUT/cross.log" ||
     "$CROSS" $CFLAGS_COMMON -shared -fPIC -o "$OUT/libnuxel-libinput-path.so" "$SRC" 2>>"$OUT/cross.log"; then
    built=1
  else
    echo "-- cross build failed:"; tail -20 "$OUT/cross.log"
  fi
fi
if [ "$built" = 0 ]; then
  echo "-- falling back to the UTM guest ($VM); this is the build channel A31 used"
  if scp -q -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o ConnectTimeout=8 \
        "$SRC" "$VM:/tmp/nuxel-libinput-path-a33.c" 2>/dev/null &&
     ssh -q -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o ConnectTimeout=8 "$VM" \
        "gcc $CFLAGS_COMMON -shared -fPIC -o /tmp/libnuxel-libinput-path-a33.so /tmp/nuxel-libinput-path-a33.c -ldl && \
         file /tmp/libnuxel-libinput-path-a33.so" 2>&1 | tee "$OUT/vm-build.log" | grep -q aarch64 &&
     scp -q -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null \
        "$VM:/tmp/libnuxel-libinput-path-a33.so" "$OUT/libnuxel-libinput-path.so" 2>/dev/null; then
    built=1
  fi
fi

if [ "$built" = 1 ]; then
  file "$OUT/libnuxel-libinput-path.so" | grep -q aarch64 || { echo "NOT aarch64"; exit 1; }
  file "$OUT/libnuxel-libinput-path.so"
  ( cd "$OUT" && sha256sum libnuxel-libinput-path.so nuxel-libinput-path-selftest | tee SHA256SUMS )
  echo "== shim build OK =="
else
  echo "== shim cross/VM build UNAVAILABLE (host selftest still built and valid) =="
  echo "   set CROSS=/path/to/aarch64-linux-gnu-gcc or VM=user@host and re-run"
  exit 3
fi
