/* SPDX-License-Identifier: GPL-2.0-only */
#include "fmt_sms.h"
#include <string.h>

bool fmt_sms_send(struct fmt_tx_frame *f, bool more, uint8_t domain_wire,
                  const uint8_t *pdu, size_t len)
{
    if (!pdu || !len || len > 255 || domain_wire > 3) return false;
    uint8_t *p = fmt_tx_begin(f, 4, 1, 1, 4+len);
    if (!p) return false;
    p[0] = 2; p[1] = more ? 2 : 1; p[2] = domain_wire; p[3] = (uint8_t)len;
    memcpy(p+4, pdu, len);
    return true;
}

bool fmt_sms_ack(struct fmt_tx_frame *f, uint8_t ref, uint16_t result)
{
    /* GetSmsResult / IpcTxDeliveryReport: success 0; memory full 0x8016;
     * malformed/unsupported 0x806f. No caller-controlled arbitrary cause. */
    if (result != 0 && result != 0x8016 && result != 0x806f) return false;
    const uint8_t p[] = {2, (uint8_t)result, (uint8_t)(result >> 8), ref, 0};
    return fmt_tx_raw(f, 4, 6, 1, p, sizeof p);
}

bool fmt_sms_ready(struct fmt_tx_frame *f) { return fmt_tx_raw(f, 4, 7, 3, NULL, 0); }
bool fmt_sms_get_smsc(struct fmt_tx_frame *f) { return fmt_tx_raw(f, 4, 10, 2, NULL, 0); }

bool fmt_sms_incoming(const uint8_t *p, size_t n, struct fmt_sms_incoming *out)
{
    if (!p || !out || n < 7 || p[0] != 2 || n != 6u+p[5] || !p[5]) return false;
    *out = (struct fmt_sms_incoming){.reference=p[4], .category=p[1], .pdu=p+6, .len=p[5]};
    return true;
}

bool fmt_sms_submit_result(const uint8_t *p, size_t n, struct fmt_sms_submit_result *out)
{
    if (!p || !out || n < 5 || p[0] != 2 || n != 5u+p[4]) return false;
    *out = (struct fmt_sms_submit_result){.result=(uint16_t)p[1] | ((uint16_t)p[2]<<8),
                                        .reference=p[3], .pdu=p+5, .len=p[4]};
    return true;
}

bool fmt_sms_smsc(const uint8_t *p, size_t n, uint8_t out[12], size_t *len)
{
    /* SmsCenter(char *,int) @0x2b0ed8 accepts a <=12-byte field and
     * copies only p[0]+1 bytes. The live CP returns a padded 12-byte field. */
    if (!p || !out || !len || !n || n>12 || p[0] > 11 || n < 1u+p[0]) return false;
    n=1u+p[0];
    if (p[0]) {
        if (p[0] < 2 || !(p[1] & 0x80) || (p[1]&0x70) == 0x50) return false;
        for (size_t i = 2; i < n; i++) {
            if ((p[i]&15) > 9 || ((p[i]>>4) > 9 && !(i == n-1 && (p[i]>>4) == 15))) return false;
        }
    }
    memset(out, 0, 12); memcpy(out, p, n); *len = n;
    return true;
}
