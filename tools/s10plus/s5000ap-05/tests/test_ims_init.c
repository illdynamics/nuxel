/* SPDX-License-Identifier: GPL-2.0-only */
#include "ims_init.h"
#include "fmt_tx.h"
#include "fmt_rx.h"
#include <stdio.h>
#include <string.h>
#include <assert.h>

static int writes;
static uint8_t last_seq;
static bool write_capture(const struct fmt_tx_frame *f, uint8_t *seq, void *u)
{
    (void)u;
    writes++;
    last_seq = (uint8_t)(writes * 11);
    *seq = last_seq;
    if (f->main_cmd == 10 && f->sub_cmd == 45) {
        if (f->cmd_type == 2) {
            assert(f->len == 7);
            assert(f->buf[4] == 10 && f->buf[5] == 45 && f->buf[6] == 2);
        } else {
            assert(f->len == 9);
            assert(f->buf[4] == 10 && f->buf[5] == 45 && f->buf[6] == 3);
            assert(f->buf[7] == FMT_TX_VOICE_DOMAIN_PS_ONLY);
            assert(f->buf[8] == FMT_TX_VOICE_DOMAIN_PS_ONLY);
        }
    }
    return true;
}

/* Drive a bounded FSM to terminal (done/failed) by feeding a GEN OK after
 * each SDK write and a direct capa response after GetDeviceCapa. */
static enum ims_init_phase drive(struct ims_init *i, uint64_t *now)
{
    for (int guard = 0; guard < 1000; guard++) {
        enum ims_init_phase p = ims_init_tick(i, *now, true);
        (*now)++;
        if (p == IMS_INIT_DONE || p == IMS_INIT_FAILED) return p;
        /* Feed responses keyed on the last write. */
        switch (p) {
        case IMS_INIT_WAIT_GET_ACK:
            ims_init_capa_response(i, last_seq);
            break;
        case IMS_INIT_WAIT_ACK:
        case IMS_INIT_WAIT_SDM_MODE:
        case IMS_INIT_WAIT_SDM_FMT:
        case IMS_INIT_WAIT_SDM_OIP:
        case IMS_INIT_WAIT_SDM_DOM:
            ims_init_gen_result(i, FMT_RX_GEN_OK, last_seq);
            break;
        default: break;
        }
    }
    return IMS_INIT_FAILED;
}

int main(void)
{
    struct ims_init i;
    assert(ims_init_open(&i, write_capture, NULL));

    /* Offline: no write, not done. */
    assert(ims_init_tick(&i, 0, false) == IMS_INIT_IDLE);
    assert(writes == 0);
    assert(!ims_init_done(&i));

    uint64_t now = 1;
    enum ims_init_phase end = drive(&i, &now);
    assert(end == IMS_INIT_DONE);
    assert(ims_init_done(&i));
    /* GetDeviceCapa + SetDeviceCapa + 4 SDM writes = 6 writes. */
    assert(writes == 6);
    ims_init_close(&i);

    /* Non-zero GEN on SET (capa) must NOT advance to SDM; instead it retries
     * the capability stage. */
    struct ims_init i2;
    assert(ims_init_open(&i2, write_capture, NULL));
    writes = 0;
    now = 1;
    ims_init_tick(&i2, now++, true);        /* IDLE -> SEND_GET */
    ims_init_tick(&i2, now++, true);        /* SEND_GET -> WAIT_GET_ACK */
    ims_init_capa_response(&i2, last_seq);  /* -> SEND_CAPA */
    ims_init_tick(&i2, now++, true);        /* SEND_CAPA -> WAIT_ACK */
    ims_init_gen_result(&i2, 0x8001u, last_seq); /* non-zero -> SEND_CAPA retry */
    assert(i2.phase == IMS_INIT_SEND_CAPA);
    assert(!ims_init_done(&i2));
    ims_init_close(&i2);

    printf("test_ims_init OK\n");
    return 0;
}
