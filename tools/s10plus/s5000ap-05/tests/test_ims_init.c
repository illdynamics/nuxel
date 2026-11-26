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
            /* IpcTxGetDeviceCapa: request, no payload, len 7. */
            assert(f->len == 7);
            assert(f->buf[4] == 10 && f->buf[5] == 45 && f->buf[6] == 2);
        } else {
            /* IpcTxSetDeviceCapa: notification, payload [PS_ONLY, PS_ONLY]. */
            assert(f->len == 9);
            assert(f->buf[4] == 10 && f->buf[5] == 45 && f->buf[6] == 3);
            assert(f->buf[7] == FMT_TX_VOICE_DOMAIN_PS_ONLY);
            assert(f->buf[8] == FMT_TX_VOICE_DOMAIN_PS_ONLY);
        }
    }
    return true;
}

int main(void)
{
    struct ims_init i;
    assert(ims_init_open(&i, write_capture, NULL));

    /* Offline: no write, not done. */
    assert(ims_init_tick(&i, 0, false) == IMS_INIT_IDLE);
    assert(writes == 0);
    assert(!ims_init_done(&i));

    /* Online tick 1: IDLE -> SEND_GET (no write yet). */
    assert(ims_init_tick(&i, 0, true) == IMS_INIT_SEND_GET);
    assert(writes == 0);

    /* Online tick 2: SEND_GET -> WAIT_GET_ACK (emits GetDeviceCapa). */
    assert(ims_init_tick(&i, 1, true) == IMS_INIT_WAIT_GET_ACK);
    assert(writes == 1);
    assert(!ims_init_done(&i));

    /* Generic ack for GET moves to SEND_CAPA. */
    ims_init_gen_result(&i, FMT_RX_GEN_OK, last_seq);
    assert(i.phase == IMS_INIT_SEND_CAPA);

    /* SEND_CAPA -> WAIT_ACK (emits SetDeviceCapa). */
    assert(ims_init_tick(&i, 2, true) == IMS_INIT_WAIT_ACK);
    assert(writes == 2);
    assert(!ims_init_done(&i));

    /* Generic ack for SET completes init. */
    ims_init_gen_result(&i, FMT_RX_GEN_OK, last_seq);
    assert(ims_init_done(&i));
    assert(i.phase == IMS_INIT_DONE);

    ims_init_close(&i);

    /* Non-zero GEN result does NOT complete init. */
    struct ims_init i2;
    assert(ims_init_open(&i2, write_capture, NULL));
    writes = 0;
    ims_init_tick(&i2, 0, true);
    ims_init_tick(&i2, 1, true);
    ims_init_gen_result(&i2, 0x8001u, last_seq);
    assert(!ims_init_done(&i2));
    assert(i2.phase == IMS_INIT_SEND_GET);
    ims_init_close(&i2);

    printf("test_ims_init OK\n");
    return 0;
}
