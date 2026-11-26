/* SPDX-License-Identifier: GPL-2.0-only */
#include "iil_pdn.h"
#include <assert.h>
#include <stdio.h>
#include <string.h>

static const struct iil_frame *last_iil_frame;
static const struct fmt_tx_frame *last_fmt_frame;

static bool write_cb(const struct iil_frame *f, uint8_t *seq, void *user)
{
    (void)user;
    last_iil_frame = f;
    if (seq) *seq = 1;
    return true;
}

static bool fmt_write_cb(const struct fmt_tx_frame *f, uint8_t *seq, void *user)
{
    (void)user;
    last_fmt_frame = f;
    if (seq) *seq = 4;
    return true;
}

int main(void)
{
    struct iil_pdn p;
    assert(iil_pdn_open(&p, write_cb, NULL));
    /* No FMT writer configured initially: SET_PROFILE degrades to PROVISION. */
    iil_pdn_set_fmt_write(&p, NULL, NULL);

    /* offline -> idle reset */
    assert(iil_pdn_tick(&p, 0, false) == IIL_PDN_IDLE);

    /* online -> SET_PROFILE (transition). With no FMT writer, it degrades to
     * PROVISION on the following tick. */
    last_fmt_frame = NULL;
    assert(iil_pdn_tick(&p, 1000, true) == IIL_PDN_SET_PROFILE);
    assert(iil_pdn_tick(&p, 1001, true) == IIL_PDN_PROVISION);
    assert(last_fmt_frame == NULL);

    /* Now configure the FMT writer and re-arm: SET_PROFILE emits the IMS
     * DataProfile (main=13 sub=27, profile id 2, label "ims"). */
    p.phase = IIL_PDN_IDLE;
    iil_pdn_set_fmt_write(&p, fmt_write_cb, NULL);
    last_fmt_frame = NULL;
    assert(iil_pdn_tick(&p, 1000, true) == IIL_PDN_SET_PROFILE);
    assert(iil_pdn_tick(&p, 1001, true) == IIL_PDN_SET_PROFILE);
    assert(last_fmt_frame != NULL);
    assert(last_fmt_frame->main_cmd == 13 && last_fmt_frame->sub_cmd == 27);
    assert(last_fmt_frame->cmd_type == 3 && last_fmt_frame->len == 203);
    assert(last_fmt_frame->buf[7] == 2);                 /* DataProfile type 2 */
    assert(memcmp(last_fmt_frame->buf + 8, "ims", 3) == 0);
    assert(last_fmt_frame->buf[7 + 21] == 0x06);         /* IPv6 wire byte */
    assert(memcmp(last_fmt_frame->buf + 7 + 22, IIL_PDN_APN, strlen(IIL_PDN_APN)) == 0);
    assert(p.last_write_kind == 1);                      /* FMT write */

    /* GEN ack (OK) advances SET_PROFILE -> PROVISION */
    iil_pdn_gen_result(&p, 0x8000u, 4);
    assert(p.phase == IIL_PDN_PROVISION);

    /* PROVISION -> emit the 2332-byte E911 provisioner (IIL write) */
    last_iil_frame = NULL;
    assert(iil_pdn_tick(&p, 1002, true) == IIL_PDN_PROVISION);
    assert(last_iil_frame && last_iil_frame->main_cmd == 112 && last_iil_frame->sub_cmd == 10);
    assert(last_iil_frame->len == 2332);
    assert(last_iil_frame->buf[4] == 112 && last_iil_frame->buf[5] == 10 && last_iil_frame->buf[6] == 1);
    assert(p.last_write_kind == 0);                      /* IIL write */

    /* GEN ack (OK) advances PROVISION -> DEFINE */
    iil_pdn_gen_result(&p, 0x8000u, 1);
    assert(p.phase == IIL_PDN_DEFINE);

    /* Rejected/unsupported provisioner is non-blocking: it still advances to
     * DEFINE so the direct IIL GPRS Define/Activate path is not skipped. */
    p.phase = IIL_PDN_PROVISION; p.phase_deadline_ms = 1;
    iil_pdn_gen_result(&p, 0x8003u, 1);
    assert(p.phase == IIL_PDN_DEFINE);
    p.phase = IIL_PDN_PROVISION; p.phase_deadline_ms = 1;
    iil_pdn_gen_result(&p, 0x8001u, 1);
    assert(p.phase == IIL_PDN_DEFINE);

    /* DEFINE emits main=13 sub=1 on next tick */
    last_iil_frame = NULL;
    iil_pdn_tick(&p, 1003, true);
    assert(last_iil_frame && last_iil_frame->main_cmd == 13 && last_iil_frame->sub_cmd == 1);
    assert(last_iil_frame->buf[9] == 0x06); /* proto IPV6 */

    /* timeout -> re-arm SET_PROFILE */
    assert(iil_pdn_tick(&p, 1003 + 13000, true) == IIL_PDN_SET_PROFILE);

    /* force ACTIVATE by advancing phase manually (test the builder) */
    p.phase = IIL_PDN_ACTIVATE;
    p.phase_deadline_ms = 0;
    last_iil_frame = NULL;
    iil_pdn_tick(&p, 1000, true);
    assert(last_iil_frame && last_iil_frame->sub_cmd == 4 && last_iil_frame->buf[8] == 2);

    /* feed connected + parameters to reach active */
    p.phase = IIL_PDN_VERIFY;
    uint8_t cbuf[12] = {9,0,0,0,112,10,3, 2,1, 0,0,0};
    struct iil_rx_event ce; size_t c=0;
    iil_rx_parse(cbuf, 9, &ce, &c);
    iil_pdn_on_connected(&p, &ce);
    assert(p.attached);

    uint8_t pbuf[64]; memset(pbuf,0,sizeof pbuf);
    size_t total = 7 + 18 + 1 + 1 + 16;
    pbuf[0]=(uint8_t)total; pbuf[1]=0; pbuf[4]=112; pbuf[5]=8; pbuf[6]=3;
    pbuf[7]=10; pbuf[8]=64; pbuf[25]=1; pbuf[26]=16; memset(pbuf+27,0xaa,16);
    struct iil_rx_event pe; size_t pc=0;
    iil_rx_parse(pbuf, total, &pe, &pc);
    iil_pdn_on_parameters(&p, &pe);
    assert(p.ip_ready && p.pcscf_ready && p.pcscf_count == 1);
    assert(iil_pdn_active(&p));

    puts("IIL PDN driver: PASS");
    iil_pdn_close(&p);
    return 0;
}
