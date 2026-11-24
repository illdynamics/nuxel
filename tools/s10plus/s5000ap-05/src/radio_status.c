/* SPDX-License-Identifier: GPL-2.0-only
 * Bounded, read-only CP status queries for a free SIPC FMT endpoint.
 * Shares radiod's exclusive transport lock. No subscriber identifier output.
 */
#define _POSIX_C_SOURCE 200809L
#include "transport.h"
#include "sipc5_fmt.h"
#include "fmt_tx.h"
#include "fmt_rx.h"
#include <stdio.h>
#include <string.h>
#include <time.h>

static uint64_t now_ms(void)
{
    struct timespec t;
    clock_gettime(CLOCK_MONOTONIC, &t);
    return (uint64_t)t.tv_sec * 1000 + (uint64_t)t.tv_nsec / 1000000;
}

static void report(const struct nuxel_sipc_fmt *f)
{
    printf("rx main=%u sub=%u type=%u length=%u", f->main_cmd,
           f->sub_cmd, f->cmd_type, f->payload_len);
    if (f->main_cmd == 10 && f->sub_cmd == 2) {
        char plmn[6];
        printf(" home_plmn=%s", fmt_rx_sim_network(f->payload, f->payload_len, plmn) ? plmn : "unknown");
    } else if ((f->main_cmd == 5 && f->sub_cmd == 1) ||
               (f->main_cmd == 8 && (f->sub_cmd == 3 || f->sub_cmd == 5 || f->sub_cmd == 10)) ||
               (f->main_cmd == 13 && (f->sub_cmd == 3 || f->sub_cmd == 4)) || f->main_cmd == 128) {
        printf(" payload=");
        for (size_t i = 0; i < f->payload_len && i < 32; i++) printf("%02x", f->payload[i]);
    }
    putchar('\n');
}

int main(int argc, char **argv)
{
    if (argc != 2 || (strcmp(argv[1], "0") && strcmp(argv[1], "1"))) {
        fprintf(stderr, "Usage: %s <FMT endpoint: 0|1> (requires endpoint unowned)\n", argv[0]);
        return 2;
    }
    unsigned slot = (unsigned)(argv[1][0] - '0');
    const char *node = slot ? "/dev/umts_ipc1" : "/dev/umts_ipc0";
    struct nuxel_sipc_dev d;
    int rc = nuxel_dev_open(&d, node, (uint8_t)(235 + slot), 0);
    if (rc) { fprintf(stderr, "cannot exclusively open %s: %d\n", node, rc); return 1; }
    bool (*queries[])(struct fmt_tx_frame *) = {
        fmt_tx_get_sim_status, fmt_tx_get_sim_network, fmt_tx_get_data_reg_state,
        fmt_tx_get_preferred_net_type, fmt_tx_get_pdp_context, fmt_tx_get_serving_network,
        fmt_tx_get_ps_attach
    };
    unsigned replies = 0;
    for (size_t q = 0; q < sizeof queries / sizeof queries[0]; q++) {
        struct fmt_tx_frame tx;
        if (!queries[q](&tx) || nuxel_dev_write(&d, tx.buf, tx.len) != NUXEL_IO_OK) {
            fprintf(stderr, "query %zu write failed\n", q); break;
        }
        printf("slot=%u query main=%u sub=%u\n", slot, tx.main_cmd, tx.sub_cmd);
        uint64_t end = now_ms() + 3000;
        bool matched = false;
        uint8_t buf[8192]; size_t used = 0;
        while (!matched && now_ms() < end) {
            if (nuxel_dev_poll(&d, 100) != NUXEL_IO_OK) continue;
            ssize_t n = 0;
            if (used == sizeof buf) break;
            if (nuxel_dev_read(&d, buf+used, sizeof buf-used, &n) != NUXEL_IO_OK || n <= 0) continue;
            used += (size_t)n;
            size_t off = 0;
            while (off < used) {
                struct nuxel_sipc_fmt f; size_t consumed = 0;
                int status = sipc5_parse_fmt(buf+off, used-off, 4096, &f, &consumed);
                if (status != 0 || !consumed) break;
                report(&f);
                if (f.main_cmd == tx.main_cmd && f.sub_cmd == tx.sub_cmd && f.cmd_type == 2) matched = true;
                off += consumed;
            }
            memmove(buf, buf+off, used-off); used -= off;
        }
        memset(buf, 0, sizeof buf);
        if (matched) replies++; else printf("query_timeout main=%u sub=%u\n", tx.main_cmd, tx.sub_cmd);
        fflush(stdout);
    }
    nuxel_dev_close(&d);
    printf("endpoint=%u query_responses=%u/%zu\n", slot, replies, sizeof queries / sizeof queries[0]);
    return replies == sizeof queries / sizeof queries[0] ? 0 : 1;
}
