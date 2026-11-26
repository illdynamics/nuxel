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
    /* DEFINEOF_PDP frame = main 13 sub 1; ACTIVATE = main 13 sub 4. */
    if (writes==1) assert(f->main_cmd==13 && f->sub_cmd==1);
    if (writes==2) assert(f->main_cmd==13 && f->sub_cmd==4);
    return true;
}

int main(void)
{
    struct ims_pdn p;
    assert(ims_pdn_open(&p, write_capture, NULL));
    assert(ims_pdn_tick(&p, 0, true) == IMS_PDN_DEFINE);
    assert(ims_pdn_tick(&p, 1, true) == IMS_PDN_DEFINE && writes==1);
    /* define OK -> activate */
    ims_pdn_gen_result(&p, FMT_RX_GEN_OK, last_seq);
    assert(p.phase == IMS_PDN_ACTIVATE);
    assert(ims_pdn_tick(&p, 2, true) == IMS_PDN_ACTIVATE && writes==2);
    /* activate OK -> verify */
    ims_pdn_gen_result(&p, FMT_RX_GEN_OK, last_seq);
    assert(p.phase == IMS_PDN_VERIFY);
    /* CID attached -> active */
    ims_pdn_report_cid(&p, 2, true);
    assert(ims_pdn_active(&p));

    /* offline never leaves active */
    ims_pdn_tick(&p, 3, false);
    assert(!ims_pdn_active(&p));

    ims_pdn_close(&p);
    printf("test_ims_pdn OK\n");
    return 0;
}
