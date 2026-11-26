/* SPDX-License-Identifier: GPL-2.0-only
 *
 * ims_iil.c — recovered IIL (IpcProtocol41Iil) wire serialization.
 * See ims_iil.h for provenance. Pure serializer; never transmits; never logs
 * SIP AKA secret material.
 */
#include "ims_iil.h"
#include <string.h>

uint8_t *iil_begin(struct iil_frame *f, uint8_t main, uint8_t sub,
                   uint8_t type, size_t payload_len)
{
    if (!f || payload_len > IIL_TX_MAX_FRAME - 7u) return NULL;
    f->main_cmd = main;
    f->sub_cmd  = sub;
    f->cmd_type = type;
    f->len      = 7u + payload_len;
    uint16_t total = (uint16_t)f->len;
    f->buf[0] = (uint8_t)(total & 0xff);
    f->buf[1] = (uint8_t)(total >> 8);
    f->buf[2] = 0;   /* msg_seq lo */
    f->buf[3] = 0;   /* msg_seq hi */
    f->buf[4] = main;
    f->buf[5] = sub;
    f->buf[6] = type;
    return &f->buf[7];
}

/* IpcTxImsAuthResp: header + [flag=1][len byte][data]. */
bool iil_tx_ims_auth_resp(struct iil_frame *f, const uint8_t *data, size_t len)
{
    if (!f || len > 255 || (len && !data)) return false;
    uint8_t *p = iil_begin(f, IIL_MAIN_IIL, IIL_SUB_IMS_AUTH_RESP, 2u, 2u + len);
    if (!p) return false;
    p[0] = 1u;              /* flag */
    p[1] = (uint8_t)len;    /* payload length byte */
    if (len) memcpy(p + 2, data, len);
    return true;
}

/* IpcTxSendRPSMMA: header + NUL-terminated text at [7], 256-byte body. */
bool iil_tx_send_rpsmma(struct iil_frame *f, const char *text)
{
    if (!f || !text) return false;
    size_t tlen = strlen(text);
    if (tlen > 255) return false;
    uint8_t *p = iil_begin(f, IIL_MAIN_SMS_RP, IIL_SUB_RPSMMA, 3u, 256u);
    if (!p) return false;
    memset(p, 0, 256);
    memcpy(p, text, tlen);
    return true;
}

/* IpcTxDefinePdpContext: 8-byte header (flag=1) + [char=0][proto][APN]. */
bool iil_tx_define_pdp(struct iil_frame *f, const char *apn, uint8_t proto,
                       uint8_t flag0)
{
    if (!f || !apn) return false;
    size_t alen = strlen(apn);
    if (alen > 99) return false;
    uint8_t w;
    if (proto == 2) w = 0x05;
    else if (proto == 3) w = 0x06;
    else if (proto == 4) w = 0x04;
    else w = 0x06;
    /* header(7) + flag(1) + char(1) + proto(1) + APN(100) = 110; pad to 134. */
    uint8_t *p = iil_begin(f, IIL_MAIN_GPRS, IIL_SUB_GPRS_DEFINE, 3u, 127u);
    if (!p) return false;
    memset(p, 0, 127);
    p[0] = 1u;       /* flag byte (part of 8-byte header) */
    p[1] = flag0;    /* char field (recovered strb w2,[sp,#8]) */
    p[2] = w;        /* proto wire byte */
    memcpy(p + 3, apn, alen);
    return true;
}

/* IpcTxSetPdpContext: 8-byte header (flag=1) + [cid][0x11][0][0][0][APN]. */
bool iil_tx_set_pdp_context(struct iil_frame *f, uint8_t cid, const char *apn)
{
    if (!f || !apn) return false;
    size_t alen = strlen(apn);
    if (alen > 31) return false;
    uint8_t *p = iil_begin(f, IIL_MAIN_GPRS, IIL_SUB_GPRS_ACTIVATE, 3u, 105u);
    if (!p) return false;
    memset(p, 0, 105);
    p[0] = 1u;       /* flag byte */
    p[1] = cid;      /* recovered strb w1,[sp,#8] */
    p[2] = 0x11;     /* flags */
    memcpy(p + 6, apn, alen);
    return true;
}
