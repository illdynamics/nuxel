/* SPDX-License-Identifier: GPL-2.0-only */
#include "ims_pdn.h"
#include "fmt_tx.h"
#include "fmt_rx.h"
#include <stdio.h>
#include <string.h>
#include <assert.h>

static int writes;
static uint8_t last_seq;
static bool write_capture(const struct fmt_tx_frame *f, uint8_t *seq, void *u)
{
    (void)u; writes++; last_seq = (uint8_t)(writes*3); *seq = last_seq;
    if (writes==1) assert(f->main_cmd==13 && f->sub_cmd==27); /* SET_DATA_PROFILE */
    return true;
}

int main(void)
{
    struct ims_pdn p;
    assert(ims_pdn_open(&p, write_capture, NULL));
    assert(ims_pdn_tick(&p, 0, true) == IMS_PDN_SET_PROFILE);
    assert(ims_pdn_tick(&p, 1, true) == IMS_PDN_SET_PROFILE && writes==1);
    /* set-profile OK -> profile armed == active (modem-managed bearer) */
    ims_pdn_gen_result(&p, FMT_RX_GEN_OK, last_seq);
    assert(p.phase == IMS_PDN_VERIFY);
    assert(ims_pdn_active(&p));

    /* modem-reported CID attachment (optional) also keeps it active */
    ims_pdn_report_cid(&p, 2, true);
    assert(ims_pdn_active(&p));

    /* offline never leaves active */
    ims_pdn_tick(&p, 3, false);
    assert(!ims_pdn_active(&p));

    /* rejection -> failed, not active */
    ims_pdn_gen_result(&p, 0x8001, last_seq);
    assert(!ims_pdn_active(&p));

    ims_pdn_close(&p);
    printf("test_ims_pdn OK\n");
    return 0;
}
