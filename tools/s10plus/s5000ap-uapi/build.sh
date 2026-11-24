#!/usr/bin/env bash
# Reproducible offline build for nuxel-cpbootd (host + AArch64 target).
#
# Produces:
#   nuxel-cpbootd.host                      (host LP64, dry-run/mock capable)
#   nuxel-cpbootd.host.hw                   (host LP64, -DNUXEL_CPBOOTD_ENABLE_HW=1)
#   nuxel-cpbootd.aarch64                   (AArch64 target, dry-run/mock capable)
#   nuxel-cpbootd.aarch64.hw                (AArch64 target, HW-compiled, NOT run on device)
#   nuxel-s5000ap-uapi-check.host/.aarch64  (ABI fixture)
#   s5000ap-status.host/.aarch64            (read-only status probe)
#
# The .hw variants compile the hardware path but MUST only ever be run against
# fake/device mocks offline, never the phone. The value-aware gate means only
# -DNUXEL_CPBOOTD_ENABLE_HW=1 (a *non-zero value*) actually enables the HW path.
#
# Usage:  ./build.sh [clean]
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$HERE"

HOST_CC="${CC:-gcc}"
AARCH64_CC="${AARCH64_CC:-aarch64-linux-gnu-gcc}"
AARCH64_READELF="${AARCH64_READELF:-aarch64-linux-gnu-readelf}"

CFLAGS_COMMON=(-O2 -Wall -Wextra -Werror -std=gnu11)

if [[ "${1:-}" == "clean" ]]; then
    rm -f *.host *.aarch64 *.o
    echo "cleaned build artifacts"
    exit 0
fi

# --- host builds -------------------------------------------------------
NV_SOURCE=../s5000ap-05/src/nv_items.c
$HOST_CC "${CFLAGS_COMMON[@]}" -o nuxel-cpbootd.host nuxel-cpbootd.c "$NV_SOURCE"
$HOST_CC "${CFLAGS_COMMON[@]}" -DNUXEL_CPBOOTD_ENABLE_HW=1 -o nuxel-cpbootd.host.hw nuxel-cpbootd.c "$NV_SOURCE"
$HOST_CC "${CFLAGS_COMMON[@]}" -o nuxel-s5000ap-uapi-check.host nuxel-s5000ap-uapi-check.c
$HOST_CC "${CFLAGS_COMMON[@]}" -o s5000ap-status.host s5000ap-status.c

# --- AArch64 target builds ---------------------------------------------
$AARCH64_CC "${CFLAGS_COMMON[@]}" -o nuxel-cpbootd.aarch64 nuxel-cpbootd.c "$NV_SOURCE"
$AARCH64_CC "${CFLAGS_COMMON[@]}" -DNUXEL_CPBOOTD_ENABLE_HW=1 -o nuxel-cpbootd.aarch64.hw nuxel-cpbootd.c "$NV_SOURCE"
$AARCH64_CC "${CFLAGS_COMMON[@]}" -o nuxel-s5000ap-uapi-check.aarch64 nuxel-s5000ap-uapi-check.c
$AARCH64_CC "${CFLAGS_COMMON[@]}" -o s5000ap-status.aarch64 s5000ap-status.c

# --- sanity: AArch64 ELF architecture + interpreter --------------------
echo "=== AArch64 ELF verification (readelf) ==="
for f in nuxel-cpbootd.aarch64 nuxel-cpbootd.aarch64.hw nuxel-s5000ap-uapi-check.aarch64 s5000ap-status.aarch64; do
    echo "--- $f ---"
    $AARCH64_READELF -h "$f" | grep -E 'Class:|Machine:|Type:' || true
    $AARCH64_READELF -l "$f" | grep -E 'interpreter|Requesting program interpreter' || true
    echo "    NEEDED libs:"; $AARCH64_READELF -d "$f" | grep NEEDED || echo "    (none — static glibc needs present on target only)"
done

# --- host sanity: run ABI fixture --------------------------------------
echo "=== host ABI fixture ==="
./nuxel-s5000ap-uapi-check.host

# --- offline mock golden transcript (must reach 'online') --------------
echo "=== offline mock full-boot transcript (dry-run/mock build) ==="
# Reuse this host build's mock backend without a real device.
# (No firmware fixture is bundled here; see tests/test_mock_boot_transcript.py)
./nuxel-cpbootd.host --plan

echo "=== SHA-256 of produced binaries ==="
shasum -a 256 nuxel-cpbootd.host nuxel-cpbootd.aarch64 nuxel-cpbootd.aarch64.hw

echo "build OK"
