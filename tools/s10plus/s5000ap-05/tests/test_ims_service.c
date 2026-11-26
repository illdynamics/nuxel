/* SPDX-License-Identifier: GPL-2.0-only */
#include "ims_service.h"
#include "fmt_tx.h"
#include <stdio.h>
#include <string.h>
#include <assert.h>

static int writes;
static uint8_t last_seq;
static bool write_capture(const struct fmt_tx_frame *f, uint8_t *seq, void *u)
{
    (void)u;
    writes++;
    last_seq = (uint8_t)(writes * 7);
    *seq = last_seq;
    /* Assert the SetRegState frame layout. */
    if (f->main_cmd == 22 && f->sub_cmd == 8) {
        assert(f->len == 13);
        assert(f->buf[4] == 22 && f->buf[5] == 8 && f->buf[6] == 3);
        assert(f->buf[7] == FMT_TX_IMS_REGSTATUS_REGISTERED); /* ImsRegStatus (arg1) */
        assert(f->buf[8] == 1);   /* request flag (arg2 int) */
        assert(f->buf[9] == FMT_TX_RAT_LTE);  /* NetworkType (arg3) */
        assert(f->buf[10] == 0);  /* EcmpState (arg4) */
        assert(f->buf[11] == 6);  /* EpdgAvailableState (derived, LTE) */
        assert(f->buf[12] == 0);  /* second int (arg7) */
    }
    return true;
}

int main(void)
{
    struct ims_service s;
    assert(ims_service_open(&s, write_capture, NULL, NULL));

    /* No PRN: no write on tick. */
    assert(ims_service_tick(&s, 0, true, false) == IMS_WAIT_PDN);
    assert(writes == 0);

    /* PDN up: request registration. */
    assert(ims_service_tick(&s, 0, true, true) == IMS_REQUEST_REG);
    assert(ims_service_tick(&s, 1, true, true) == IMS_WAIT_REGISTERED);
    assert(writes == 1);

    /* Modem confirms registration. */
    struct fmt_rx_ims_state st = {.status=1, .registered=true};
    ims_service_notify_state(&s, &st);
    assert(ims_service_registered(&s));
    assert(s.phase == IMS_REGISTERED);

    ims_service_close(&s);

    /* Offline never fabricates registration. */
    struct ims_service s2;
    assert(ims_service_open(&s2, write_capture, NULL, NULL));
    writes = 0;
    ims_service_notify_state(&s2, &st);
    assert(!ims_service_registered(&s2));
    ims_service_close(&s2);

    printf("test_ims_service OK\n");
    return 0;
}
