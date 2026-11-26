/* SPDX-License-Identifier: GPL-2.0-only */
#include "ims_pdn.h"
#include "fmt_tx.h"
#include "fmt_rx.h"
#include <stdio.h>
#include <string.h>
#include <assert.h>

static int writes;
static uint8_t last_seq;
static uint8_t written_sub;
static bool write_capture(const struct fmt_tx_frame *f, uint8_t *seq, void *u)
{
    (void)u; writes++; last_seq = (uint8_t)(writes*3); *seq = last_seq;
    written_sub = f->sub_cmd;
    return true;
}

int main(void)
{
    struct fmt_tx_frame f;
    assert(fmt_tx_ims_profile(&f,"ims",FMT_TX_PROTO_IPV4V6));
    assert(f.buf[7+188]==1);
    /* DefinePdpContext payload[1] must be AccessNetworkType EUTRAN(1), not
     * DataProfile id 2. This is the corrected CP contract. */
    assert(fmt_tx_ims_define(&f,"ims",FMT_TX_PROTO_IPV6));
    assert(f.buf[7+126]==3);   /* P-CSCF selector byte */
    assert(f.buf[7+1]==1);     /* payload[1] = EUTRAN AccessNetworkType */

    struct ims_pdn p;
    assert(ims_pdn_open(&p, write_capture, NULL));

    /* Phase 1: SET_PROFILE (sub=27) */
    assert(ims_pdn_tick(&p, 0, true) == IMS_PDN_SET_PROFILE);
    assert(ims_pdn_tick(&p, 1, true) == IMS_PDN_SET_PROFILE && writes==1);
    assert(written_sub == 27);

    /* An unrelated ACK must not accept the profile. */
    ims_pdn_gen_result(&p, FMT_RX_GEN_OK, last_seq+1);
    assert(p.phase == IMS_PDN_SET_PROFILE);

    /* Profile acceptance -> DEFINE (sub=1), not straight to VERIFY. */
    ims_pdn_gen_result(&p, FMT_RX_GEN_OK, last_seq);
    assert(p.phase == IMS_PDN_DEFINE);
    assert(!ims_pdn_active(&p));

    /* Phase 2: DEFINE (sub=1) with EUTRAN */
    assert(ims_pdn_tick(&p, 2, true) == IMS_PDN_DEFINE && writes==2);
    assert(written_sub == 1);
    ims_pdn_gen_result(&p, FMT_RX_GEN_OK, last_seq);
    assert(p.phase == IMS_PDN_ACTIVATE);

    /* Phase 3: ACTIVATE (sub=4) for CID 2 */
    assert(ims_pdn_tick(&p, 3, true) == IMS_PDN_ACTIVATE && writes==3);
    assert(written_sub == 4);
    ims_pdn_gen_result(&p, FMT_RX_GEN_OK, last_seq);
    assert(p.phase == IMS_PDN_VERIFY);
    assert(!ims_pdn_active(&p));

    /* modem-reported CID attachment alone is not readiness */
    ims_pdn_report_cid(&p, 2, true);
    assert(!ims_pdn_active(&p));

    /* wrong CID IP must not activate */
    struct fmt_rx_ip ip = {.cid=1, .ipv6_valid=true, .pcscf6_count=1};
    ims_pdn_report_ip(&p,&ip); assert(!ims_pdn_active(&p));

    /* CID-2 IP without P-CSCF is not ready */
    ip.cid=2; ip.pcscf6_count=0;
    ims_pdn_report_ip(&p,&ip); assert(!ims_pdn_active(&p));

    /* CID-2 IP + P-CSCF is ready */
    ip.pcscf6_count=1;
    ims_pdn_report_ip(&p,&ip); assert(ims_pdn_active(&p));

    /* detach/reattach preserve correctness */
    ims_pdn_report_cid(&p,2,false); assert(!ims_pdn_active(&p));
    ims_pdn_report_cid(&p,2,true); assert(!ims_pdn_active(&p));
    ims_pdn_report_ip(&p,&ip); assert(ims_pdn_active(&p));

    /* stale GEN cannot undo an already confirmed context */
    ims_pdn_gen_result(&p,0x8001,last_seq); assert(ims_pdn_active(&p));

    /* offline never leaves active */
    ims_pdn_tick(&p, 4, false);
    assert(!ims_pdn_active(&p));

    ims_pdn_close(&p);
    printf("test_ims_pdn OK\n");
    return 0;
}
