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
    struct fmt_tx_frame f;
    assert(fmt_tx_ims_profile(&f,"ims",FMT_TX_PROTO_IPV4V6));
    assert(f.buf[7+188]==1);
    assert(fmt_tx_ims_define(&f,"ims",FMT_TX_PROTO_IPV6));
    assert(f.buf[7+126]==3);
    struct ims_pdn p;
    assert(ims_pdn_open(&p, write_capture, NULL));
    assert(ims_pdn_tick(&p, 0, true) == IMS_PDN_SET_PROFILE);
    assert(ims_pdn_tick(&p, 1, true) == IMS_PDN_SET_PROFILE && writes==1);
    /* An unrelated ACK must not accept the profile. */
    ims_pdn_gen_result(&p, FMT_RX_GEN_OK, last_seq+1);
    assert(p.phase == IMS_PDN_SET_PROFILE);
    /* Profile acceptance is not bearer readiness. */
    ims_pdn_gen_result(&p, FMT_RX_GEN_OK, last_seq);
    /* SetDataProfile accepted -> VERIFY (modem-managed attach), not Define. */
    assert(p.phase == IMS_PDN_VERIFY);
    assert(!ims_pdn_active(&p));

    /* modem-reported CID attachment (optional) also keeps it active */
    ims_pdn_report_cid(&p, 2, true);
    assert(!ims_pdn_active(&p));

    struct fmt_rx_ip ip = {.cid=1, .ipv6_valid=true, .pcscf6_count=1};
    ims_pdn_report_ip(&p,&ip); assert(!ims_pdn_active(&p));
    ip.cid=2; ip.pcscf6_count=0;
    ims_pdn_report_ip(&p,&ip); assert(!ims_pdn_active(&p));
    ip.pcscf6_count=1;
    ims_pdn_report_ip(&p,&ip); assert(ims_pdn_active(&p));
    ims_pdn_report_cid(&p,2,false); assert(!ims_pdn_active(&p));
    ims_pdn_report_cid(&p,2,true); assert(!ims_pdn_active(&p));
    ims_pdn_report_ip(&p,&ip); assert(ims_pdn_active(&p));
    /* stale GEN cannot undo an already confirmed context */
    ims_pdn_gen_result(&p,0x8001,last_seq); assert(ims_pdn_active(&p));
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
