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
    if (f->main_cmd == 10 && f->sub_cmd == 32) {
        /* SDM IMS mode=ON: notification, payload [1]. */
        assert(f->len == 8);
        assert(f->buf[4] == 10 && f->buf[5] == 32 && f->buf[6] == 3);
        assert(f->buf[7] == FMT_TX_SDM_IMS_MODE_ON);
    }
    return true;
}

int main(void)
{
    struct ims_init i;
    assert(ims_init_open(&i, write_capture, NULL));

    assert(ims_init_tick(&i, 0, false) == IMS_INIT_IDLE);
    assert(writes == 0);
    assert(!ims_init_done(&i));

    assert(ims_init_tick(&i, 0, true) == IMS_INIT_SEND_GET);
    assert(writes == 0);

    assert(ims_init_tick(&i, 1, true) == IMS_INIT_WAIT_GET_ACK);
    assert(writes == 1);
    assert(!ims_init_done(&i));

    ims_init_capa_response(&i, last_seq);
    assert(i.phase == IMS_INIT_SEND_CAPA);

    assert(ims_init_tick(&i, 2, true) == IMS_INIT_WAIT_ACK);
    assert(writes == 2);

    /* SetDeviceCapa ack -> SEND_SDM */
    ims_init_gen_result(&i, FMT_RX_GEN_OK, last_seq);
    assert(i.phase == IMS_INIT_SEND_SDM);

    assert(ims_init_tick(&i, 3, true) == IMS_INIT_WAIT_SDM_ACK);
    assert(writes == 3);

    /* SDM mode ack -> DONE */
    ims_init_gen_result(&i, FMT_RX_GEN_OK, last_seq);
    assert(ims_init_done(&i));
    assert(i.phase == IMS_INIT_DONE);

    ims_init_close(&i);

    /* SDM rejection does not complete init; bounded retry. */
    struct ims_init i2;
    assert(ims_init_open(&i2, write_capture, NULL));
    writes = 0;
    ims_init_tick(&i2, 0, true);
    ims_init_tick(&i2, 1, true);
    ims_init_capa_response(&i2, last_seq);
    assert(i2.phase == IMS_INIT_SEND_CAPA);
    ims_init_tick(&i2, 2, true);
    assert(i2.phase == IMS_INIT_WAIT_ACK);
    ims_init_gen_result(&i2, FMT_RX_GEN_OK, last_seq);
    assert(i2.phase == IMS_INIT_SEND_SDM);
    ims_init_tick(&i2, 3, true);
    assert(i2.phase == IMS_INIT_WAIT_SDM_ACK);
    ims_init_gen_result(&i2, 0x8001u, last_seq); /* SDM rejected -> retry SDM */
    assert(!ims_init_done(&i2));
    assert(i2.phase == IMS_INIT_SEND_SDM);
    ims_init_close(&i2);

    printf("test_ims_init OK\n");
    return 0;
}
