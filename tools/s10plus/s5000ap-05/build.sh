#!/usr/bin/env bash
# Reproducible build + host tests for S5000AP Stage-05 (RFS + SIPC5 + radiod).
# SPDX-License-Identifier: GPL-2.0-only
#
# Produces/verifies:
#   test_sipc5_fmt   (SIPC5 link+FMT parser unit tests)
#   test_rfs_policy  (RFS fail-closed path validator unit tests)
#   fuzz_driver      (deterministic stdin fuzz driver for the parser)
#
# Usage:  ./build.sh [clean]
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$HERE"

CC="${CC:-gcc}"
CFLAGS=(-O2 -Wall -Wextra -Werror -std=gnu11)

if [[ "${1:-}" == "clean" ]]; then
    rm -f test_sipc5_fmt test_rfs_policy fuzz_driver test_sipc5_fmt_asan
    echo "cleaned"
    exit 0
fi

$CC "${CFLAGS[@]}" -Isrc -o test_sipc5_fmt tests/test_sipc5_fmt.c src/sipc5_fmt.c
$CC "${CFLAGS[@]}" -Isrc -o test_rfs_policy tests/test_rfs_policy.c src/rfs_policy.c
$CC "${CFLAGS[@]}" -Isrc -o fuzz_driver tests/fuzz_driver.c src/sipc5_fmt.c

echo "=== run SIPC5/FMT unit tests ==="
./test_sipc5_fmt
echo "=== run RFS policy unit tests ==="
./test_rfs_policy
echo "=== run SIPC5 fuzzer (host, no writes) ==="
python3 tests/fuzz_sipc5.py ./fuzz_driver --iters=3000

echo "=== ASan/UBSan build + fuzz (memory-safety gate) ==="
CLANG="${CLANG:-clang}"
$CLANG -O1 -g -fsanitize=address,undefined -fno-sanitize-recover=all \
    -std=gnu11 -Isrc -o test_sipc5_fmt_asan tests/fuzz_driver.c src/sipc5_fmt.c
python3 tests/fuzz_sipc5.py ./test_sipc5_fmt_asan --asan --iters=3000

echo "build+test OK"
