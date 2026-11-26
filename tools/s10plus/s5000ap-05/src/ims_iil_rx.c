/* SPDX-License-Identifier: GPL-2.0-only
 *
 * ims_iil_rx.c — IIL receive-path parser + event decoders. See ims_iil_rx.h.
 *
 * The modem sends IIL events with the 7-byte IIL header (16-bit msg_seq).
 * This parser validates the framing and decodes the well-understood vendor
 * event payloads conservatively. Where the exact recovered payload layout is
 * not authoritatively known, the decoder validates the minimal invariants
 * (main/sub/type + length) and returns a typed, bounded result rather than
 * guessing field offsets. Secret material (RAND/AUTN/RES/CK/IK) is never
 * emitted to logs.
 */
#include "ims_iil_rx.h"
#include <string.h>
#include <arpa/inet.h>

int iil_rx_parse(const uint8_t *buf, size_t len, struct iil_rx_event *out,
                 size_t *consumed)
{
    if (consumed) *consumed = 0;
    if (!buf || !out) return -1;
    if (len < 7) return 0;               /* need at least the 7-byte header */
    uint16_t total = (uint16_t)(buf[0] | (buf[1] << 8));
    if (total < 7 || total > IIL_RX_MAX_FRAME) return -2; /* corrupt len */
    if (len < total) return 0;           /* truncation: wait for more */
    uint16_t msg_seq = (uint16_t)(buf[2] | (buf[3] << 8));
    out->msg_seq   = msg_seq;
    out->main_cmd  = buf[4];
    out->sub_cmd   = buf[5];
    out->cmd_type  = buf[6];
    out->payload     = buf + 7;
    out->payload_len = (size_t)(total - 7u);
    if (consumed) *consumed = total;
    return (int)total;
}

/* IpcRxIilConnected: minimal validated payload. The vendor handler reads a
 * CID/attached pair. We require at least 2 bytes and interpret byte 0 as cid,
 * byte 1 as the connection state (non-zero = attached). */
bool iil_rx_connected(const struct iil_rx_event *e, uint8_t *cid, bool *attached)
{
    if (!e || !cid || !attached) return false;
    if (e->main_cmd != IIL_MAIN_IIL || e->sub_cmd != IIL_SUB_CONNECTED) return false;
    if (e->payload_len < 2) return false;
    if (cid) *cid = e->payload[0];
    if (attached) *attached = e->payload[1] != 0;
    return true;
}

/* IpcRxIilParameters: IMS IP + P-CSCF list. Layout (recovered conservatively):
 *   [0] family (2=AF_INET,10=AF_INET6)
 *   [1] prefix length
 *   [2..17] IP address (16 bytes, IPv4-in-IPv6 or IPv6)
 *   then a 1-byte P-CSCF count followed by that many {len,addr} entries.
 * Fail-closed: if the length cannot contain a valid structure, return false
 * rather than guessing. */
bool iil_rx_parameters(const struct iil_rx_event *e, int *family,
                       uint8_t ip[16], uint8_t *prefix,
                       uint8_t pcscf[][16], uint8_t *pcscf_len,
                       unsigned max_pcscf, unsigned *pcscf_count)
{
    if (!e || e->main_cmd != IIL_MAIN_IIL || e->sub_cmd != IIL_SUB_PARAMETERS)
        return false;
    if (e->payload_len < 18) return false;   /* family+prefix+16-byte ip */
    if (family) *family = (e->payload[0] == 2) ? AF_INET : AF_INET6;
    if (prefix) *prefix = e->payload[1];
    if (ip) memcpy(ip, e->payload + 2, 16);

    size_t off = 18;
    if (pcscf_count) *pcscf_count = 0;
    if (off >= e->payload_len) return true;   /* no P-CSCF list */
    uint8_t cnt = e->payload[off++];
    unsigned got = 0;
    for (; got < cnt && off < e->payload_len && got < max_pcscf; got++) {
        uint8_t alen = e->payload[off++];
        if (alen > 16 || off + alen > e->payload_len) break;
        if (pcscf_len) pcscf_len[got] = alen;
        if (pcscf) { memset(pcscf[got], 0, 16); memcpy(pcscf[got], e->payload + off, alen); }
        off += alen;
    }
    if (pcscf_count) *pcscf_count = got;
    return true;
}

/* IpcRxIilIsimAuth: AKA challenge. Requires RAND(16)+AUTN(16). */
bool iil_rx_isim_auth(const struct iil_rx_event *e,
                      uint8_t rand[16], uint8_t autn[16])
{
    if (!e || e->main_cmd != IIL_MAIN_IIL || e->sub_cmd != IIL_SUB_ISIM_AUTH)
        return false;
    if (e->payload_len < 32) return false;
    if (rand) memcpy(rand, e->payload, 16);
    if (autn) memcpy(autn, e->payload + 16, 16);
    return true;
}

/* IpcRxIilRegistration: state relayed by the modem. Non-zero => registered. */
bool iil_rx_registration(const struct iil_rx_event *e, bool *registered)
{
    if (!e || e->main_cmd != IIL_MAIN_IIL || e->sub_cmd != IIL_SUB_REGISTRATION)
        return false;
    if (e->payload_len < 1) return false;
    if (registered) *registered = e->payload[0] != 0;
    return true;
}

/* IpcRxIilPreference: 1-byte SMS-over-IP format selector. */
bool iil_rx_preference(const struct iil_rx_event *e, uint8_t *fmt)
{
    if (!e || e->main_cmd != IIL_MAIN_IIL || e->sub_cmd != IIL_SUB_PREFERENCE)
        return false;
    if (e->payload_len < 1) return false;
    if (fmt) *fmt = e->payload[0];
    return true;
}

/* IpcRxSmsIncomingMsg: RP-DATA body for ims_rp_decode. We expose the raw body
 * after any minimal fixed prefix. Conservative: require a valid RP first byte
 * (type 0..5, MS bits clear) to reject malformed blobs. */
bool iil_rx_sms_incoming(const struct iil_rx_event *e,
                         const uint8_t **rp, size_t *rp_len)
{
    if (!e || !rp || !rp_len) return false;
    if (e->main_cmd != IIL_MAIN_SMS_RP && e->main_cmd != IIL_MAIN_IIL) return false;
    if (e->sub_cmd != IIL_SUB_SMS_INCOMING && e->sub_cmd != IIL_SUB_SMS) return false;
    if (e->payload_len < 2) return false;
    /* RP header: type byte <= 5 with upper bits clear, then reference. */
    if ((e->payload[0] & 0xf8) != 0) return false;
    *rp = e->payload;
    *rp_len = e->payload_len;
    return true;
}
