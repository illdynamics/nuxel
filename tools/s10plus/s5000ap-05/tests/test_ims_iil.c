/* SPDX-License-Identifier: GPL-2.0-only */
#include "ims_iil.h"
#include <assert.h>
#include <stdio.h>
#include <string.h>

int main(void)
{
    /* IIL header: [u16 total][u16 msg_seq][u8 main][u8 sub][u8 type][u8 flag] */
    struct iil_frame f;
    uint8_t *p = iil_begin(&f, 13, 1, 3, 1, 4);
    assert(p == &f.buf[8]);
    assert(f.len == 12);        /* 8 header + 4 payload */
    assert(f.buf[0] == 0x0c && f.buf[1] == 0x00);  /* total_len 12 LE */
    assert(f.buf[2] == 0 && f.buf[3] == 0);        /* msg_seq 0 */
    assert(f.buf[4] == 13);     /* main GPRS */
    assert(f.buf[5] == 1);      /* sub */
    assert(f.buf[6] == 3);      /* type */
    assert(f.buf[7] == 1);      /* flag */

    /* IpcTxImsAuthResp: 9-byte header + len byte + data. */
    uint8_t data[16]; for (int i=0;i<16;i++) data[i]=(uint8_t)i;
    assert(iil_tx_ims_auth_resp(&f, data, 16));
    assert(f.len == 25);        /* 9 + 16 */
    assert(f.buf[4] == 112);    /* IIL main */
    assert(f.buf[5] == 2);      /* sub=2 */
    assert(f.buf[6] == 2);      /* type=2 request */
    assert(f.buf[7] == 1);      /* flag=1 */
    assert(f.buf[8] == 16);     /* payload length byte */
    assert(!memcmp(&f.buf[9], data, 16));

    /* Reject overly-long / NULL auth data. */
    assert(!iil_tx_ims_auth_resp(&f, NULL, 1));
    assert(!iil_tx_ims_auth_resp(&f, data, 256));

    /* IpcTxSendRPSMMA: 263-byte frame, main=4 sub=21 type=2. */
    assert(iil_tx_send_rpsmma(&f, "hello"));
    assert(f.len == 263);
    assert(f.buf[4] == 4);      /* main=4 */
    assert(f.buf[5] == 21);     /* sub=0x15 */
    assert(f.buf[6] == 2);      /* type=2 */
    assert(!memcmp(&f.buf[7], "hello", 5));
    assert(f.buf[7+5] == 0);    /* NUL terminated */

    puts("IMS IIL wire contract: PASS");
    return 0;
}
