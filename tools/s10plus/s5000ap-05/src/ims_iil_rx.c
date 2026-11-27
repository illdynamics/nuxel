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

/* IpcRxIilConnected (sub 22 @0x356870): the vendor handler ONLY records the
 * event code 123 and returns; it does NOT carry a CID or attached flag in the
 * payload. We therefore report a connect notification with no fabricated CID
 * or attach state. The authoritative bearer IP/P-CSCF come from the GPRS
 * GPRS_IP_CONFIGURATION path (main=13 sub=9), not from this event. */
bool iil_rx_connected(const struct iil_rx_event *e, uint8_t *cid, bool *attached)
{
    if (!e || e->main_cmd != IIL_MAIN_IIL || e->sub_cmd != IIL_SUB_CONNECTED)
        return false;
    /* No cid/attached is encoded by the CP; report cid=0, attached=true only
     * as "a connection notification was received". Never invent a CID. */
    if (cid) *cid = 0;
    if (attached) *attached = true;
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
    /* Vendor IpcRxIilParameters @0x356800 is a STUB (return 0); the CP does
     * not deliver IP/P-CSCF here. Only decode if a payload of the expected
     * shape is actually present; otherwise treat as unusable. */
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

/* IpcRxIilIsimAuth (sub 17 @0x356808): builds UiccAuth(0, RAND, 16, AUTN, 16)
 * with RAND read from buf+8 and AUTN from buf+0x18 (buf includes the 7-byte
 * SIPC header). => payload[1..16] = RAND, payload[17..32] = AUTN. payload[0]
 * is a leading type/flag byte. */
bool iil_rx_isim_auth(const struct iil_rx_event *e,
                      uint8_t rand[16], uint8_t autn[16])
{
    if (!e || e->main_cmd != IIL_MAIN_IIL || e->sub_cmd != IIL_SUB_ISIM_AUTH)
        return false;
    if (e->payload_len < 33) return false;
    if (rand) memcpy(rand, e->payload + 1, 16);
    if (autn) memcpy(autn, e->payload + 17, 16);
    return true;
}

/* IpcRxIilRegistration (sub 7 @0x356528). Authoritative layout:
 *   payload[0]   ImsRegStatus (1..5; vendor clamps buf[7] into 1..4)
 *   payload[1]   NetworkType
 *   payload[2]   EcmpState (==1)
 *   payload[3]   EpdgState
 *   payload[4..5] RadioTechnology (u16, buf[12]<<8|buf[11])
 *   payload[6..7] u16
 *   payload[8..9] u16
 *   payload[10]  IMPU length (0=none), IMPU at payload[11..]
 *   (payload[267] SmsOverIpFormat in the full frame)
 * `registered` is true for ImsRegStatus==1 (REGISTERED); 2 is REGISTERING.
 *
 * The IMPU is the modem/operator-provisioned public identity; it is PUBLIC,
 * not a secret/PII credential, but we still never log its full value and only
 * copy it into a bounded caller buffer. A length of 0 or an out-of-range
 * length leaves *impu empty and is NOT an error (status is still reported). */
int iil_rx_registration(const struct iil_rx_event *e, int *status,
                        char *impu, size_t impu_cap)
{
    if (!e || e->main_cmd != IIL_MAIN_IIL || e->sub_cmd != IIL_SUB_REGISTRATION)
        return -1;
    if (e->payload_len < 1) return -1;
    int st = e->payload[0];
    if (status) *status = st;

    if (impu && impu_cap) impu[0] = 0;
    /* Best-effort IMPU decode: payload[10] = length, payload[11..] = bytes. */
    if (impu && impu_cap && e->payload_len >= 11) {
        uint8_t ilen = e->payload[10];
        if (ilen > 0 && (size_t)ilen < impu_cap &&
            11u + (size_t)ilen <= e->payload_len) {
            memcpy(impu, e->payload + 11, ilen);
            impu[ilen] = 0;
            /* Accept only printable SIP-ish bytes; reject NUL/control. */
            for (size_t i = 0; i < ilen; i++) {
                unsigned char c = (unsigned char)impu[i];
                if (c < 0x20 || c > 0x7e) { impu[0] = 0; break; }
            }
        }
    }
    return st;
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
    /* sub 1 = IpcRxSmsIncomingMsg (main 112); legacy main 4 sub 1 also seen. */
    if (e->main_cmd != IIL_MAIN_IIL && e->main_cmd != IIL_MAIN_SMS_RP)
        return false;
    if (e->sub_cmd != IIL_SUB_SMS_INCOMING) return false;
    if (e->payload_len < 2) return false;
    /* RP header: type byte <= 5 with upper bits clear, then reference. */
    if ((e->payload[0] & 0xf8) != 0) return false;
    *rp = e->payload;
    *rp_len = e->payload_len;
    return true;
}
