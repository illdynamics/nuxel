#!/usr/bin/env bash
# Reproducible build + offline unit tests for S5000AP Stage-06 (radio FSM).
# SPDX-License-Identifier: GPL-2.0-only
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$HERE"

CC="${CC:-gcc}"
CFLAGS=(-O2 -Wall -Wextra -Werror -std=gnu11)

if [[ "${1:-}" == "clean" ]]; then
    rm -f test_radio_fsm test_radio_fsm_asan
    echo "cleaned"
    exit 0
fi

$CC "${CFLAGS[@]}" -Isrc -o test_radio_fsm tests/test_radio_fsm.c src/radio_fsm.c

echo "=== run radio FSM unit tests ==="
./test_radio_fsm

echo "=== ASan/UBSan build (memory-safety gate) ==="
CLANG="${CLANG:-clang}"
$CLANG -O1 -g -fsanitize=address,undefined -fno-sanitize-recover=all \
    -std=gnu11 -Isrc -o test_radio_fsm_asan tests/test_radio_fsm.c src/radio_fsm.c
./test_radio_fsm_asan

echo "build+test OK"
