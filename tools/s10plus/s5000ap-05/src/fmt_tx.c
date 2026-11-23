/*
 * fmt_tx.c — S5000AP IpcProtocol41 FMT transmit serialization.
 * SPDX-License-Identifier: GPL-2.0-only
 *
 * See fmt_tx.h for the framing-resolution rationale. This module is a pure
 * serializer: it builds byte-exact sipc_fmt_hdr + payload frames and NEVER
 * transmits. All layouts below are recovered from the exact vendor RIL
 * (vendor/lib64/libsec-ril.so, SM-G975F/EFUJ2, build 60889dd7) disassembly.
 */
#include "fmt_tx.h"
#include <string.h>

/* constant channel-independent command tables (main_cmd values) */
#define MAIN_GPRS  13u
#define MAIN_NET   8u
#define MAIN_SEC   5u

uint8_t *fmt_tx_begin(struct fmt_tx_frame *f, uint8_t main, uint8_t sub,
                      uint8_t type, size_t payload_len)
{
    if (!f || payload_len > FMT_TX_MAX_FRAME - 7u) return NULL;
    f->main_cmd = main;
    f->sub_cmd  = sub;
    f->cmd_type = type;
    f->len      = 7u + payload_len;

    uint16_t total = (uint16_t)f->len;
    f->buf[0] = (uint8_t)(total & 0xff);
    f->buf[1] = (uint8_t)(total >> 8);
    f->buf[2] = 0;   /* msg_seq */
    f->buf[3] = 0;   /* ack_seq */
    f->buf[4] = main;
    f->buf[5] = sub;
    f->buf[6] = type;
    return &f->buf[7];
}

bool fmt_tx_raw(struct fmt_tx_frame *f, uint8_t main, uint8_t sub,
                uint8_t type, const uint8_t *payload, size_t payload_len)
{
    uint8_t *p = fmt_tx_begin(f, main, sub, type, payload_len);
    if (!p) return false;
    if (payload_len > 0) {
        if (!payload) return false;
        memcpy(p, payload, payload_len);
    }
    return true;
}

/*
 * GPRS/data-call establish (recovered from IpcTxSetDataCallEstablish @0x320a10):
 *   8-byte frame: len=8, msg_seq=0, ack_seq=0, main=3, sub=2, type=3,
 *   payload[0]=1 when establish else 2.
 */
bool fmt_tx_set_data_call_establish(struct fmt_tx_frame *f, bool establish)
{
    uint8_t p[1];
    p[0] = establish ? 1u : 2u;
    return fmt_tx_raw(f, 3u /*CDMA_DATA*/, 2u /*CDMA_DATA_CALL_ESTABLISH*/,
                      FMT_TX_TYPE_NOTIFICATION, p, 1);
}

/* SIM query: vendor sends SEC interrogations as 7-byte frames (type=2). */
bool fmt_tx_get_sim_status(struct fmt_tx_frame *f)
{
    return fmt_tx_raw(f, MAIN_SEC, 1 /*SEC_PIN_STATUS*/, FMT_TX_TYPE_REQUEST, NULL, 0);
}

bool fmt_tx_get_atr(struct fmt_tx_frame *f)
{
    return fmt_tx_raw(f, MAIN_SEC, 10 /*SEC_ATR_INFO*/, FMT_TX_TYPE_REQUEST, NULL, 0);
}

bool fmt_tx_get_serving_network(struct fmt_tx_frame *f)
{
    return fmt_tx_raw(f, MAIN_NET, 3 /*NET_SERVING_NETWORK*/, FMT_TX_TYPE_REQUEST, NULL, 0);
}

bool fmt_tx_get_registration(struct fmt_tx_frame *f)
{
    return fmt_tx_raw(f, MAIN_NET, 5 /*NET_REGIST*/, FMT_TX_TYPE_REQUEST, NULL, 0);
}

/*
 * GPRS PS attach (recovered from IpcTxPsAttach disasm @0x31fa98):
 *   header main=13 sub=3 type=3; payload[0]=attach, payload[1]=suspend,
 *   payload[2]=detach_reason (clamped 0..4).
 */
bool fmt_tx_ps_attach(struct fmt_tx_frame *f, bool attach, bool suspend,
                      uint8_t detach_reason)
{
    uint8_t p[3];
    p[0] = attach ? 1u : 0u;
    p[1] = suspend ? 1u : 0u;
    p[2] = (detach_reason > 4u) ? 0u : detach_reason;
    return fmt_tx_raw(f, MAIN_GPRS, 3 /*GPRS_PS*/, FMT_TX_TYPE_NOTIFICATION, p, 3);
}

/* GPRS get PDP context: 7-byte query (recovered from IpcTxGetPdpContext). */
bool fmt_tx_get_pdp_context(struct fmt_tx_frame *f)
{
    return fmt_tx_raw(f, MAIN_GPRS, 4 /*GPRS_PDP_CONTEXT*/, FMT_TX_TYPE_REQUEST, NULL, 0);
}

/*
 * GPRS mobile-data on/off (recovered from IpcTxSetMobileDataSetting @0x3214c8):
 *   main=13 sub=0x1d(29 SYNC_PROFILE_INFO) type=3;
 *   payload[0]=enable, payload[1]=extra.
 */
bool fmt_tx_mobile_data(struct fmt_tx_frame *f, bool enable, bool extra)
{
    uint8_t p[2];
    p[0] = enable ? 1u : 0u;
    p[1] = extra ? 1u : 0u;
    return fmt_tx_raw(f, MAIN_GPRS, 29 /*GPRS_SYNC_PROFILE_INFO*/,
                      FMT_TX_TYPE_NOTIFICATION, p, 2);
}

/*
 * GPRS define PDP context (recovered from IpcTxDefinePdpContext @0x31f580).
 * 134-byte frame: 7-byte header + 127-byte payload.
 *   payload[0]   = 0x01 (fixed profile flag)
 *   payload[1]   = profile id (u8)
 *   payload[2]   = protocol byte (see below)
 *   payload[3..103] = APN (101 bytes, NUL padded)  (offset 10 in full frame)
 *   payload[104..119] = reserved (16 bytes, zero)
 *   payload[120..123] = reserved (4 bytes, zero)
 *   payload[124..125] = reserved (2 bytes, zero)
 *   payload[126]  = 0 (protocol-dependent default)
 *
 * The APN field begins at full-frame offset 10 (payload offset 3), i.e. the
 * vendor copies the NUL-terminated APN into `buf[10]`. Maximum APN length the
 * vendor accepts is 100 (strlen <= 0x65), so the APN field is 101 bytes.
 *
 * protocol byte (DataProtocol -> wire): IP=0x05, IPV6=0x60, IPV4V6=0x06
 * (recovered from the `0x00040605 >> ((proto-2)*8)` selection). For the common
 * case (proto==IPV4V6/2) the wire byte is 0x05... note this selection was
 * recovered from the shift of 0x00040605; the exact mapping for proto 0/1
 * collapses to the default 0x02. We map the three documented enum values to
 * their observed wire bytes and default unknown values to IPV4V6(0x05).
 */
bool fmt_tx_define_pdp_context(struct fmt_tx_frame *f, const char *apn,
                               uint8_t proto, uint8_t profile_id)
{
    if (!f || !apn) return false;
    size_t alen = strlen(apn);
    if (alen > 100u) return false;   /* vendor strlen<=0x65 gate */

    uint8_t *p = fmt_tx_begin(f, MAIN_GPRS, 1 /*GPRS_DEFINE_PDP_CONTEXT*/,
                              FMT_TX_TYPE_NOTIFICATION, 127u);
    if (!p) return false;
    memset(p, 0, 127u);

    p[0] = 0x01;             /* fixed profile flag */
    p[1] = profile_id;       /* profile id */
    switch (proto) {
    case FMT_TX_PROTO_IP:     p[2] = 0x05; break;
    case FMT_TX_PROTO_IPV6:   p[2] = 0x60; break;
    case FMT_TX_PROTO_IPV4V6: p[2] = 0x06; break;
    default:                  p[2] = 0x05; break;   /* IP */
    }
    /* APN into payload[3 .. 3+alen] (full-frame offset 10). */
    memcpy(&p[3], apn, alen);

    return true;
}
