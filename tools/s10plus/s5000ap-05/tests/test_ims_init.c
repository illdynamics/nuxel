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
    } else if (f->main_cmd == 10 && f->sub_cmd == 26) {
        /* SdmImsSmsFmtSet: 8-byte frame, payload[0]=SmsOverIpFormat=3GPP(2). */
        assert(f->len == 8);
        assert(f->buf[4] == 10 && f->buf[5] == 26 && f->buf[6] == 3);
        assert(f->buf[7] == FMT_TX_SDM_SMSOVERIP_FORMAT_3GPP);
    } else if (f->main_cmd == 10 && f->sub_cmd == 27) {
        /* SdmImsSmsOverIPSet: 8-byte frame, payload[0]=enable=1. */
        assert(f->len == 8);
        assert(f->buf[4] == 10 && f->buf[5] == 27 && f->buf[6] == 3);
        assert(f->buf[7] == FMT_TX_SDM_SMSOVERIP_ENABLE);
    } else if (f->main_cmd == 8 && f->sub_cmd == 52) {
        /* IpcTxSetVolteStateNotification: NET sub=52, 8-byte frame,
         * payload[0]=ready=1. */
        assert(f->len == 8);
        assert(f->buf[4] == 8 && f->buf[5] == 52 && f->buf[6] == 3);
        assert(f->buf[7] == FMT_TX_VOLTE_STATE_NOT_READY);
    }
    return true;
}

static void drive_to_done(struct ims_init *i)
{
    /* Query/set preference, then truthfully report missing AP backend. */
    assert(ims_init_tick(i, 0, true) == IMS_INIT_SEND_GET);
    assert(ims_init_tick(i, 1, true) == IMS_INIT_WAIT_GET_ACK); /* writes GetDeviceCapa */
    ims_init_capa_response(i, last_seq);
    assert(i->phase == IMS_INIT_SEND_CAPA);
    assert(ims_init_tick(i, 2, true) == IMS_INIT_WAIT_ACK);     /* writes SetDeviceCapa */
    ims_init_gen_result(i, FMT_RX_GEN_OK, last_seq+1);
    assert(i->phase == IMS_INIT_WAIT_ACK);
    ims_init_gen_result(i, FMT_RX_GEN_OK, last_seq);
    /* Capability ACK satisfies the registration gate and now arms SMS-over-IP
     * (SMS_FMT, SMS_OIP) BEFORE the VoLTE-state report. */
    assert(ims_init_done(i));
    assert(i->phase == IMS_INIT_SEND_SMS_FMT);
    assert(ims_init_tick(i, 3, true) == IMS_INIT_WAIT_SMS_FMT);   /* writes SMS_FMT */
    ims_init_gen_result(i, FMT_RX_GEN_OK, last_seq);
    assert(i->phase == IMS_INIT_SEND_SMS_OIP);
    assert(ims_init_tick(i, 4, true) == IMS_INIT_WAIT_SMS_OIP);   /* writes SMS_OIP */
    ims_init_gen_result(i, FMT_RX_GEN_OK, last_seq);
    assert(i->phase == IMS_INIT_SEND_VOLTE_STATE);
    assert(ims_init_tick(i, 5, true) == IMS_INIT_WAIT_VOLTE_STATE);
    ims_init_gen_result(i, FMT_RX_GEN_OK, last_seq);
    assert(ims_init_done(i));
    assert(i->phase == IMS_INIT_DONE);
}

int main(void)
{
    struct ims_init i;
    assert(ims_init_open(&i, write_capture, NULL));

    /* Offline: no write, not done. */
    assert(ims_init_tick(&i, 0, false) == IMS_INIT_IDLE);
    assert(writes == 0);
    assert(!ims_init_done(&i));

    writes = 0;
    drive_to_done(&i);
    /* Get, Set, SMS_FMT, SMS_OIP, truthful VoLTE not-ready. */
    assert(writes == 5);

    ims_init_close(&i);

    /* Non-zero GEN on SET retries SET and does not arm SMS-over-IP. */
    struct ims_init i2;
    assert(ims_init_open(&i2, write_capture, NULL));
    writes = 0;
    ims_init_tick(&i2, 0, true);                /* -> SEND_GET */
    ims_init_tick(&i2, 1, true);                /* -> WAIT_GET_ACK (write Get) */
    ims_init_capa_response(&i2, last_seq);      /* -> SEND_CAPA */
    ims_init_tick(&i2, 2, true);                /* -> WAIT_ACK (write Set) */
    ims_init_gen_result(&i2, 0x8001u, last_seq);/* non-zero -> retry SET */
    assert(!ims_init_done(&i2));
    assert(i2.phase == IMS_INIT_SEND_CAPA);

    ims_init_tick(&i2, 3, true);                /* re-write Set -> WAIT_ACK */
    assert(i2.phase == IMS_INIT_WAIT_ACK);
    ims_init_gen_result(&i2, FMT_RX_GEN_OK, last_seq);
    assert(ims_init_done(&i2) && i2.phase == IMS_INIT_SEND_SMS_FMT);
    ims_init_tick(&i2, 4, true);                /* -> WAIT_SMS_FMT (write SMS_FMT) */
    ims_init_gen_result(&i2, FMT_RX_GEN_OK, last_seq);
    assert(i2.phase == IMS_INIT_SEND_SMS_OIP);
    ims_init_tick(&i2, 5, true);                /* -> WAIT_SMS_OIP (write SMS_OIP) */
    ims_init_gen_result(&i2, FMT_RX_GEN_OK, last_seq);
    assert(i2.phase == IMS_INIT_SEND_VOLTE_STATE);
    ims_init_tick(&i2, 6, true);
    ims_init_gen_result(&i2, FMT_RX_GEN_OK, last_seq);
    assert(i2.phase == IMS_INIT_DONE);
    ims_init_close(&i2);

    printf("test_ims_init OK\n");
    return 0;
}
