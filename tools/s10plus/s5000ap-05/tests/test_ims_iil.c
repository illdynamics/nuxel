/* SPDX-License-Identifier: GPL-2.0-only */
#include "ims_iil.h"
#include <assert.h>
#include <stdio.h>
#include <string.h>

int main(void)
{
    /* IIL 7-byte header: [u16 total][u16 msg_seq][u8 main][u8 sub][u8 type] */
    struct iil_frame f;
    uint8_t *p = iil_begin(&f, 13, 1, 3, 4);
    assert(p == &f.buf[7]);
    assert(f.len == 11);        /* 7 header + 4 payload */
    assert(f.buf[0] == 0x0b && f.buf[1] == 0x00);  /* total_len 11 LE */
    assert(f.buf[2] == 0 && f.buf[3] == 0);        /* msg_seq 0 */
    assert(f.buf[4] == 13);     /* main */
    assert(f.buf[5] == 1);      /* sub */
    assert(f.buf[6] == 3);      /* type */

    /* IpcTxImsAuthResp — emulation-verified: 19 00 00 00 70 02 02 01 10 <16B> */
    uint8_t data[16]; for (int i=0;i<16;i++) data[i]=(uint8_t)i;
    assert(iil_tx_ims_auth_resp(&f, data, 16));
    assert(f.len == 25);        /* 7 header + 2 + 16 */
    assert(f.buf[0] == 0x19 && f.buf[1] == 0x00);  /* total 25 */
    assert(f.buf[4] == 112);    /* main IIL */
    assert(f.buf[5] == 2);      /* sub */
    assert(f.buf[6] == 2);      /* type request */
    assert(f.buf[7] == 1);      /* flag */
    assert(f.buf[8] == 16);     /* len byte */
    assert(!memcmp(&f.buf[9], data, 16));

    /* Reject invalid auth data. */
    assert(!iil_tx_ims_auth_resp(&f, NULL, 1));
    assert(!iil_tx_ims_auth_resp(&f, data, 256));

    /* IpcTxSendRPSMMA — emulation-verified: 07 01 00 00 04 15 03 "hello" */
    assert(iil_tx_send_rpsmma(&f, "hello"));
    assert(f.len == 263);
    assert(f.buf[4] == 4);      /* main=4 */
    assert(f.buf[5] == 21);     /* sub=0x15 */
    assert(f.buf[6] == 3);      /* type=3 notification */
    assert(!memcmp(&f.buf[7], "hello", 5));
    assert(f.buf[7+5] == 0);    /* NUL terminated */

    /* IpcTxDefinePdpContext — emulation-verified:
     *   86 00 00 00 0d 01 03 01 | 00 06 "ims.mnc008.mcc204.gprs" */
    {
        struct iil_frame g;
        assert(iil_tx_define_pdp(&g, "ims.mnc008.mcc204.gprs", 3, 0));
        assert(g.len == 134);
        assert(g.buf[4] == 13 && g.buf[5] == 1 && g.buf[6] == 3 && g.buf[7] == 1);
        assert(g.buf[8] == 0);       /* char flag0 */
        assert(g.buf[9] == 0x06);    /* proto IPV6 */
        assert(!memcmp(&g.buf[10], "ims.mnc008.mcc204.gprs", 22));
    }
    /* IpcTxSetPdpContext — emulation-verified (cid=2):
     *   70 00 00 00 0d 04 03 01 | 02 11 00 00 00 "ims..." */
    {
        struct iil_frame g;
        assert(iil_tx_set_pdp_context(&g, 2, "ims.mnc008.mcc204.gprs"));
        assert(g.len == 112);
        assert(g.buf[4] == 13 && g.buf[5] == 4 && g.buf[6] == 3 && g.buf[7] == 1);
        assert(g.buf[8] == 2);       /* cid */
        assert(g.buf[9] == 0x11);    /* flags */
        assert(!memcmp(&g.buf[13], "ims.mnc008.mcc204.gprs", 22));
    }

    puts("IMS IIL wire contract: PASS");
    return 0;
}
/*** appended only for reference; real assertions -> recompile needed ***/
