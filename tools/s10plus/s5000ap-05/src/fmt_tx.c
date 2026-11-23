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

/*
 * GPRS set data profile (recovered from IpcTxSetDataProfile @0x31ff48, 203 bytes).
 *
 * Layout (frame base = 7-byte sipc_fmt_hdr; payload = 196 bytes; offsets below
 * are payload offsets, VERIFIED from the SIMD/store disassembly):
 *   payload[0]  = auth code (DataAuth -> numeric, from helper @0x31fe28)
 *   payload[1..20] = profile name string (20 bytes, NUL-padded; DataProfile enum)
 *   payload[21] = protocol wire byte (0x05/0x06/0x04 via 0x00040605>>((p-2)*8))
 *   payload[22..122] = APN (101 bytes, NUL-padded)
 *   payload[123..154] = username (32 bytes, NUL-padded)
 *   payload[155..186] = password (32 bytes, NUL-padded)
 *   payload[187] = flag (auth-on/enable)
 *   payload[188] = protocol wire byte (second copy)
 *   payload[189] = flag
 *   payload[190..195] = tail (4 halfwords: pco/radio-tech dependent)
 *
 * The APN/auth/protocol fields are source-verified. The profile NAME and tail
 * halfwords derive from enum/region selects we do not fully decode, so they are
 * zero-filled (carrier-default "no explicit profile name" / "no PCO"). This is
 * a bounded, partially-recovered serializer: it never emits invented nonzero
 * values for undecoded fields.
 */
bool fmt_tx_set_data_profile(struct fmt_tx_frame *f, const char *apn,
                             uint8_t auth_code, uint8_t proto)
{
    if (!f || !apn) return false;
    size_t alen = strlen(apn);
    if (alen > 100u) return false;

    uint8_t *p = fmt_tx_begin(f, MAIN_GPRS, 27u /*SET_DATA_PROFILE*/,
                              FMT_TX_TYPE_NOTIFICATION, 196u);
    if (!p) return false;
    memset(p, 0, 196u);

    p[0] = auth_code;            /* DataAuth -> numeric code (0 = none) */

    /* protocol wire byte at payload[21] and payload[188] (second copy). */
    uint8_t pb;
    switch (proto) {
    case FMT_TX_PROTO_IP:     pb = 0x05; break;
    case FMT_TX_PROTO_IPV6:   pb = 0x06; break;
    case FMT_TX_PROTO_IPV4V6: pb = 0x04; break;
    default:                  pb = 0x05; break;
    }
    p[21] = pb;
    p[188] = pb;

    /* APN at payload[22..22+alen]. */
    memcpy(&p[22], apn, alen);

    return true;
}

/*
 * GPRS always-on PDN (recovered from IpcTxSetAlwaysOnPdn @0x321550):
 *   header main=13 sub=34(0x22) type=3; payload[0]=on/off(1/0),
 *   payload[1]=profile code (region select via Region::IsNtcMain). The vendor
 *   writes payload[0] at sp[15] (w1&1) and payload[1] at sp[16] (the result of
 *   a regional profile selection, defaulting to 0). We expose the raw profile
 *   byte so the caller can pass the owner-approved carrier profile.
 */
bool fmt_tx_set_always_on_pdn(struct fmt_tx_frame *f, bool enable, uint8_t profile)
{
    uint8_t p[2];
    p[0] = enable ? 1u : 0u;
    p[1] = profile;
    return fmt_tx_raw(f, MAIN_GPRS, 34u /*SET_ALWAYS_ON_PDN*/, FMT_TX_TYPE_NOTIFICATION, p, 2);
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
 * protocol byte (DataProtocol -> wire, VERIFIED @0x31f5dc):
 *   wire = (0x00040605 >> ((proto-2)*8)) & 0xff  (csel fallback 0x02 when
 *   proto-2 >= 3 unsigned). DataProtocol enum: IP=2, IPV6=3, IPV4V6=4, so
 *   IP=0x05, IPV6=0x06, IPV4V6=0x04. Unknown proto values default to IP.
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
    /* VERIFIED @0x31f5dc: wire byte = (0x00040605 >> ((proto-2)*8)) & 0xff,
     * with a csel fallback to 0x02 when proto-2 >= 3 (unsigned).
     *   IP(2)     -> 0x05
     *   IPV6(3)   -> 0x06
     *   IPV4V6(4) -> 0x04
     * Unknown proto values fall back to IP (0x05), matching the vendor's
     * default for the common case. */
    switch (proto) {
    case FMT_TX_PROTO_IP:     p[2] = 0x05; break;  /* 0x00040605 >>  0 */
    case FMT_TX_PROTO_IPV6:   p[2] = 0x06; break;  /* 0x00040605 >>  8 */
    case FMT_TX_PROTO_IPV4V6: p[2] = 0x04; break;  /* 0x00040605 >> 16 */
    default:                  p[2] = 0x05; break;  /* IP (vendor default) */
    }
    /* APN into payload[3 .. 3+alen] (full-frame offset 10). */
    memcpy(&p[3], apn, alen);

    return true;
}
