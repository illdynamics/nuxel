/* SPDX-License-Identifier: GPL-2.0-only
 *
 * ims_iil.c — recovered IIL (IpcProtocol41Iil) wire serialization.
 * See ims_iil.h for provenance. Pure serializer; never transmits; never logs
 * SIP AKA secret material.
 */
#include "ims_iil.h"
#include <string.h>
#include <stdio.h>

uint8_t *iil_begin(struct iil_frame *f, uint8_t main, uint8_t sub,
                   uint8_t type, uint8_t flag, size_t payload_len)
{
    if (!f || payload_len > IIL_TX_MAX_FRAME - 8u) return NULL;
    f->main_cmd = main;
    f->sub_cmd  = sub;
    f->cmd_type = type;
    f->flag     = flag;
    f->len      = 8u + payload_len;
    uint16_t total = (uint16_t)f->len;
    f->buf[0] = (uint8_t)(total & 0xff);
    f->buf[1] = (uint8_t)(total >> 8);
    f->buf[2] = 0;   /* msg_seq lo */
    f->buf[3] = 0;   /* msg_seq hi */
    f->buf[4] = main;
    f->buf[5] = sub;
    f->buf[6] = type;
    f->buf[7] = flag;
    return &f->buf[8];
}

/* IpcTxImsAuthResp: 9-byte header (extra payload-length byte at [8]), then data. */
bool iil_tx_ims_auth_resp(struct iil_frame *f, const uint8_t *data, size_t len)
{
    if (!f || len > 255 || (len && !data)) return false;
    /* total_len = 9 (header incl. length byte) + len. Build manually. */
    size_t total = 9u + len;
    if (total > IIL_TX_MAX_FRAME) return false;
    f->main_cmd = IIL_MAIN_IIL;
    f->sub_cmd  = IIL_SUB_IMS_AUTH_RESP;
    f->cmd_type = 2u;  /* REQUEST (recovered: type byte 0x02) */
    f->flag     = 1u;
    f->len      = total;
    f->buf[0]   = (uint8_t)(total & 0xff);
    f->buf[1]   = (uint8_t)(total >> 8);
    f->buf[2]   = 0;   /* msg_seq lo */
    f->buf[3]   = 0;   /* msg_seq hi */
    f->buf[4]   = IIL_MAIN_IIL;   /* 112 */
    f->buf[5]   = IIL_SUB_IMS_AUTH_RESP; /* 2 */
    f->buf[6]   = 2u;   /* type */
    f->buf[7]   = 1u;   /* flag */
    f->buf[8]   = (uint8_t)len;
    if (len) memcpy(&f->buf[9], data, len);
    return true;
}

/* IpcTxSendRPSMMA: main=4 sub=21(0x15) type=2, 263-byte frame, NUL-text body. */
bool iil_tx_send_rpsmma(struct iil_frame *f, const char *text)
{
    if (!f || !text) return false;
    size_t tlen = strlen(text);
    if (tlen > 255) return false;
    f->main_cmd = IIL_MAIN_SMS_RP;   /* 4 */
    f->sub_cmd  = 21u;               /* 0x15 */
    f->cmd_type = 2u;
    f->flag     = 0;
    f->len      = 263u;
    uint16_t total = 263u;
    f->buf[0] = (uint8_t)(total & 0xff);   /* 0x07 */
    f->buf[1] = (uint8_t)(total >> 8);     /* 0x01 */
    f->buf[2] = 0;
    f->buf[3] = 0;
    f->buf[4] = IIL_MAIN_SMS_RP;           /* 4 */
    f->buf[5] = 21u;                        /* sub 0x15 */
    f->buf[6] = 2u;                         /* type */
    f->buf[7] = 0;
    /* text at offset 7 (recovered: strlcpy target sp+7), zero padded. */
    size_t cap = sizeof f->buf - 7u;
    memset(&f->buf[7], 0, cap);
    memcpy(&f->buf[7], text, tlen);
    return true;
}

/* IpcTxDefinePdpContext (IIL): 134-byte frame, main=13 sub=1 type=3.
 * Payload starts at [8] (8-byte header), no length prefix. */
bool iil_tx_define_pdp(struct iil_frame *f, const char *apn, uint8_t proto,
                       uint8_t selector, bool with_auth)
{
    if (!f || !apn) return false;
    size_t alen = strlen(apn);
    if (alen > 99) return false;
    /* proto wire byte: 0x05 IP, 0x06 IPV6, 0x04 IPV4V6 (vendor DataProtocol). */
    uint8_t w;
    if (proto == 2) w = 0x05;
    else if (proto == 3) w = 0x06;
    else if (proto == 4) w = 0x04;
    else w = 0x06;
    uint8_t *p = iil_begin(f, IIL_MAIN_GPRS, IIL_SUB_GPRS_DEFINE, 3u, 1u, 126u);
    if (!p) return false;
    p[0] = selector;         /* char field (recovered strb w2,[sp,#8]) */
    p[1] = w;                /* proto wire byte (recovered strb w8,[sp,#9]) */
    memset(p + 2, 0, 124);
    memcpy(p + 2, apn, alen); /* APN strncpy to offset 10 (sp+10) */
    if (with_auth) {
        /* recovered: proto marker at payload[125] (sp+133) when auth flag set */
        p[125] = 1u;
    }
    return true;
}

/* IpcTxSetPdpContext (IIL): 112-byte frame, main=13 sub=4 type=3.
 * payload[8] = cid; [9:12] = 0; [12]=flag selector. */
bool iil_tx_set_pdp_context(struct iil_frame *f, uint8_t cid, uint8_t pdp_type)
{
    uint8_t *p = iil_begin(f, IIL_MAIN_GPRS, IIL_SUB_GPRS_ACTIVATE, 3u, 0, 104u);
    if (!p) return false;
    p[0] = cid;              /* recovered strb w1,[sp,#8] */
    /* [9:12] = 0 (stur wzr,[sp,#9]) */
    memset(p + 1, 0, 3);
    /* flag selector at payload[12] (sp+? recovered jump-table branch sets [7]
     * in header but ACTIVATE keeps payload simple). */
    p[4] = pdp_type;
    return true;
}
