set -eu
cd /var/lib/nuxel/lte-consolidation-20261124/source/tools/s10plus/s5000ap-05
gcc -O2 -Wall -Wextra -Werror -std=gnu11 -Isrc -o nuxel-radiod src/radiod.c src/oes_cert.c src/transport.c src/sipc5_fmt.c src/rfs_proto.c src/rfs_respond.c src/fmt_tx.c src/fmt_rx.c src/data_session.c src/mbim_tx.c src/rfs_nv.c src/efs_nv.c src/nv_items.c src/fmt_sms.c src/sms_pdu.c src/sms_store.c src/sms_service.c src/fmt_call.c src/call_service.c src/cellular_link.c -lsystemd -lsqlite3
for suite in fmt_tx fmt_rx data_session rfs_nv efs_nv oes_cert fmt_sms sms_pdu sms_store sms_service fmt_call call_service; do
    libs=''
    case "$suite" in
        fmt_tx) sources='src/fmt_tx.c' ;;
        fmt_rx|data_session) sources='src/fmt_rx.c src/data_session.c' ;;
        rfs_nv) sources='src/rfs_nv.c' ;;
        efs_nv) sources='src/efs_nv.c src/nv_items.c' ;;
        oes_cert) sources='src/oes_cert.c' ;;
        fmt_sms) sources='src/fmt_sms.c src/fmt_tx.c' ;;
        sms_pdu) sources='src/sms_pdu.c' ;;
        sms_store) sources='src/sms_store.c src/sms_pdu.c'; libs=-lsqlite3 ;;
        sms_service) sources='src/sms_service.c src/sms_store.c src/sms_pdu.c src/fmt_sms.c src/fmt_tx.c'; libs=-lsqlite3 ;;
        fmt_call) sources='src/fmt_call.c src/fmt_tx.c' ;;
        call_service) sources='src/call_service.c src/fmt_call.c src/fmt_tx.c' ;;
    esac
    gcc -O2 -Wall -Wextra -Werror -std=gnu11 -Isrc -o "test_$suite" "tests/test_$suite.c" $sources $libs
    "./test_$suite"
done
cd ../s5000ap-uapi
gcc -O2 -Wall -Wextra -Werror -std=gnu11 -DNUXEL_CPBOOTD_ENABLE_HW=1 -o cpboot-built-not-run nuxel-cpbootd.c ../s5000ap-05/src/nv_items.c
file cpboot-built-not-run ../s5000ap-05/nuxel-radiod
sha256sum cpboot-built-not-run ../s5000ap-05/nuxel-radiod
