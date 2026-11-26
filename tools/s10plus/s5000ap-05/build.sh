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
    rm -f test_mobile_data test_mobile_data_asan test_sipc5_fmt test_rfs_policy fuzz_driver test_sipc5_fmt_asan test_rfs_proto test_live_frame test_ipc41_recovery test_rfs_respond test_fmt_tx test_data_session test_mbim_tx test_qbr_items test_nv_items
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
$CC "${CFLAGS[@]}" -Isrc -o test_fmt_sms tests/test_fmt_sms.c src/fmt_sms.c src/fmt_tx.c
$CC "${CFLAGS[@]}" -Isrc -o test_sms_pdu tests/test_sms_pdu.c src/sms_pdu.c
$CC "${CFLAGS[@]}" -Isrc -o test_sms_store tests/test_sms_store.c src/sms_store.c src/sms_pdu.c -lsqlite3
$CC "${CFLAGS[@]}" -Isrc -o test_sms_service tests/test_sms_service.c src/sms_service.c src/sms_store.c src/sms_pdu.c src/fmt_sms.c src/fmt_tx.c -lsqlite3
$CC "${CFLAGS[@]}" -Isrc -o test_fmt_call tests/test_fmt_call.c src/fmt_call.c src/fmt_tx.c
$CC "${CFLAGS[@]}" -Isrc -o test_call_service tests/test_call_service.c src/call_service.c src/fmt_call.c src/fmt_tx.c
$CC "${CFLAGS[@]}" -Isrc -o test_ims_service tests/test_ims_service.c src/ims_service.c src/fmt_tx.c src/fmt_rx.c
$CC "${CFLAGS[@]}" -Isrc -o test_ims_pdn tests/test_ims_pdn.c src/ims_pdn.c src/fmt_tx.c src/fmt_rx.c

$CC "${CFLAGS[@]}" -Isrc -o test_mobile_data tests/test_mobile_data.c src/mobile_data.c src/fmt_tx.c src/fmt_rx.c
./test_mobile_data

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
./test_ims_service
./test_ims_pdn
echo "=== run Stage-06 recovered QBR item dictionary tests ==="
./test_qbr_items
echo "=== run Stage-06 recovered CP-NV record/MD5/policy tests ==="
./test_nv_items
echo "=== run Stage-06 recovered RFS NV transaction tests ==="
./test_rfs_nv
echo "=== run Stage-06 native EFS NV backend tests ==="
./test_efs_nv
./test_oes_cert
./test_fmt_sms
./test_sms_pdu
./test_sms_store
./test_sms_service
./test_fmt_call
./test_call_service
echo "=== run SIPC5 fuzzer (host, no writes) ==="
python3 tests/fuzz_sipc5.py ./fuzz_driver --iters=3000

echo "=== ASan/UBSan build + fuzz (memory-safety gate) ==="
CLANG="${CLANG:-clang}"
$CLANG -O1 -g -Wall -Wextra -Werror -fsanitize=address,undefined -fno-sanitize-recover=all \
    -std=gnu11 -Isrc -o test_sipc5_fmt_asan tests/fuzz_driver.c src/sipc5_fmt.c src/rfs_proto.c src/rfs_respond.c
python3 tests/fuzz_sipc5.py ./test_sipc5_fmt_asan --asan --iters=3000

# Both serialization directions, FSM, and NV/backup transactions.
for suite in fmt_tx fmt_rx data_session rfs_nv efs_nv oes_cert fmt_sms sms_pdu sms_store sms_service fmt_call call_service mobile_data ims_service ims_pdn; do
    libs=()
    case "$suite" in
        mobile_data) sources=(src/mobile_data.c src/fmt_tx.c src/fmt_rx.c) ;;
        fmt_tx) sources=(src/fmt_tx.c) ;;
        fmt_rx|data_session) sources=(src/fmt_rx.c src/data_session.c) ;;
        rfs_nv) sources=(src/rfs_nv.c) ;;
        efs_nv) sources=(src/efs_nv.c src/nv_items.c) ;;
        oes_cert) sources=(src/oes_cert.c) ;;
        fmt_sms) sources=(src/fmt_sms.c src/fmt_tx.c) ;;
        sms_pdu) sources=(src/sms_pdu.c) ;;
        sms_store) sources=(src/sms_store.c src/sms_pdu.c);libs=(-lsqlite3) ;;
        sms_service) sources=(src/sms_service.c src/sms_store.c src/sms_pdu.c src/fmt_sms.c src/fmt_tx.c);libs=(-lsqlite3) ;;
        fmt_call) sources=(src/fmt_call.c src/fmt_tx.c) ;;
        call_service) sources=(src/call_service.c src/fmt_call.c src/fmt_tx.c) ;;
        ims_service) sources=(src/ims_service.c src/fmt_tx.c src/fmt_rx.c) ;;
        ims_pdn) sources=(src/ims_pdn.c src/fmt_tx.c src/fmt_rx.c) ;;
    esac
    "$CLANG" -O1 -g -Wall -Wextra -Werror -fsanitize=address,undefined \
        -fno-sanitize-recover=all -std=gnu11 -Isrc -o "test_${suite}_asan" \
        "tests/test_${suite}.c" "${sources[@]}" "${libs[@]:+${libs[@]}}"
    "./test_${suite}_asan"
done

echo "build+test OK"
