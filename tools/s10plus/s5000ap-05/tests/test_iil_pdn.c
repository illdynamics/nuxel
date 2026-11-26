/* SPDX-License-Identifier: GPL-2.0-only */
#include "iil_pdn.h"
#include <assert.h>
#include <stdio.h>
#include <string.h>

static const struct iil_frame *last_frame;

static bool write_cb(const struct iil_frame *f, void *user)
{
    (void)user;
    last_frame = f;
    return true;
}

int main(void)
{
    struct iil_pdn p;
    assert(iil_pdn_open(&p, write_cb, NULL));

    /* offline -> idle reset */
    assert(iil_pdn_tick(&p, 0, false) == IIL_PDN_IDLE);

    /* online -> DEFINE (transition), then emit on the next tick */
    last_frame = NULL;
    assert(iil_pdn_tick(&p, 1000, true) == IIL_PDN_DEFINE);
    assert(iil_pdn_tick(&p, 1001, true) == IIL_PDN_DEFINE);
    assert(last_frame && last_frame->main_cmd == 13 && last_frame->sub_cmd == 1);
    assert(last_frame->buf[9] == 0x06); /* proto IPV6 */

    /* timeout -> re-arm DEFINE */
    assert(iil_pdn_tick(&p, 1000 + 13000, true) == IIL_PDN_DEFINE);

    /* force ACTIVATE by advancing phase manually (test the builder) */
    p.phase = IIL_PDN_ACTIVATE;
    p.phase_deadline_ms = 0;
    last_frame = NULL;
    iil_pdn_tick(&p, 1000, true);
    assert(last_frame && last_frame->sub_cmd == 4 && last_frame->buf[8] == 2);

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
