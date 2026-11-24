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
    rm -f test_sipc5_fmt test_rfs_policy fuzz_driver test_sipc5_fmt_asan test_rfs_proto test_live_frame test_ipc41_recovery test_rfs_respond test_fmt_tx test_data_session test_mbim_tx test_qbr_items test_nv_items
    echo "cleaned"
    exit 0
fi

$CC "${CFLAGS[@]}" -Isrc -o test_sipc5_fmt tests/test_sipc5_fmt.c src/sipc5_fmt.c
$CC "${CFLAGS[@]}" -Isrc -o test_rfs_policy tests/test_rfs_policy.c src/rfs_policy.c
$CC "${CFLAGS[@]}" -Isrc -o fuzz_driver tests/fuzz_driver.c src/sipc5_fmt.c src/rfs_proto.c src/rfs_respond.c
$CC "${CFLAGS[@]}" -Isrc -o test_rfs_proto tests/test_rfs_proto.c src/rfs_proto.c
$CC "${CFLAGS[@]}" -Isrc -o test_live_frame tests/test_live_frame.c src/sipc5_fmt.c src/rfs_proto.c
$CC "${CFLAGS[@]}" -Isrc -o test_ipc41_recovery tests/test_ipc41_recovery.c src/sipc5_fmt.c
$CC "${CFLAGS[@]}" -Isrc -o test_rfs_respond tests/test_rfs_respond.c src/rfs_respond.c
$CC "${CFLAGS[@]}" -Isrc -o test_fmt_tx tests/test_fmt_tx.c src/fmt_tx.c
$CC "${CFLAGS[@]}" -Isrc -o test_data_session tests/test_data_session.c src/data_session.c src/fmt_rx.c
$CC "${CFLAGS[@]}" -Isrc -o test_fmt_rx tests/test_fmt_rx.c src/fmt_rx.c src/data_session.c
$CC "${CFLAGS[@]}" -Isrc -o test_ipc41_cmdmap tests/test_ipc41_cmdmap.c
$CC "${CFLAGS[@]}" -Isrc -o test_mbim_tx tests/test_mbim_tx.c src/mbim_tx.c
$CC "${CFLAGS[@]}" -Isrc -o test_qbr_items tests/test_qbr_items.c src/qbr_items.c
$CC "${CFLAGS[@]}" -Isrc -o test_nv_items tests/test_nv_items.c src/nv_items.c
$CC "${CFLAGS[@]}" -Isrc -o test_rfs_nv tests/test_rfs_nv.c src/rfs_nv.c
$CC "${CFLAGS[@]}" -Isrc -o test_efs_nv tests/test_efs_nv.c src/efs_nv.c src/nv_items.c
$CC "${CFLAGS[@]}" -Isrc -o test_oes_cert tests/test_oes_cert.c src/oes_cert.c

echo "=== run SIPC5/FMT unit tests ==="
./test_sipc5_fmt
echo "=== run RFS policy unit tests ==="
./test_rfs_policy
echo "=== run RFS raw-proto unit tests ==="
./test_rfs_proto
echo "=== run LIVE-captured frame tests (real CP bytes) ==="
./test_live_frame
echo "=== run Stage-06 IpcProtocol41 recovery-fact tests ==="
./test_ipc41_recovery
echo "=== run Stage-06 source-backed RFS responder tests ==="
./test_rfs_respond
echo "=== run Stage-06 FMT TX serialization tests ==="
./test_fmt_tx
echo "=== run Stage-06 data-session FSM tests ==="
./test_data_session
./test_fmt_rx
./test_ipc41_cmdmap
echo "=== run Stage-06 MBIM<->SIPC serialization tests ==="
./test_mbim_tx
echo "=== run Stage-06 recovered QBR item dictionary tests ==="
./test_qbr_items
echo "=== run Stage-06 recovered CP-NV record/MD5/policy tests ==="
./test_nv_items
echo "=== run Stage-06 recovered RFS NV transaction tests ==="
./test_rfs_nv
echo "=== run Stage-06 native EFS NV backend tests ==="
./test_efs_nv
./test_oes_cert
echo "=== run SIPC5 fuzzer (host, no writes) ==="
python3 tests/fuzz_sipc5.py ./fuzz_driver --iters=3000

echo "=== ASan/UBSan build + fuzz (memory-safety gate) ==="
CLANG="${CLANG:-clang}"
$CLANG -O1 -g -Wall -Wextra -Werror -fsanitize=address,undefined -fno-sanitize-recover=all \
    -std=gnu11 -Isrc -o test_sipc5_fmt_asan tests/fuzz_driver.c src/sipc5_fmt.c src/rfs_proto.c src/rfs_respond.c
python3 tests/fuzz_sipc5.py ./test_sipc5_fmt_asan --asan --iters=3000

# Both serialization directions, FSM, and NV/backup transactions.
for suite in fmt_tx fmt_rx data_session rfs_nv efs_nv oes_cert; do
    case "$suite" in
        fmt_tx) sources=(src/fmt_tx.c) ;;
        fmt_rx|data_session) sources=(src/fmt_rx.c src/data_session.c) ;;
        rfs_nv) sources=(src/rfs_nv.c) ;;
        efs_nv) sources=(src/efs_nv.c src/nv_items.c) ;;
        oes_cert) sources=(src/oes_cert.c) ;;
    esac
    "$CLANG" -O1 -g -Wall -Wextra -Werror -fsanitize=address,undefined \
        -fno-sanitize-recover=all -std=gnu11 -Isrc -o "test_${suite}_asan" \
        "tests/test_${suite}.c" "${sources[@]}"
    "./test_${suite}_asan"
done

echo "build+test OK"
