/* SPDX-License-Identifier: GPL-2.0-only
 * ims_msisdn.c — see ims_msisdn.h. Pure, bounded, secret/PII-safe.
 */
#include "ims_msisdn.h"
#include <string.h>

bool ims_msisdn_decode(const uint8_t *ef, size_t ef_len, char *out, size_t cap)
{
    if (!ef || !out || cap == 0) return false;
    out[0] = 0;
    if (ef_len < 2) return false;
    uint8_t ndigits = ef[0];
    uint8_t ton_npi = ef[1];
    /* Only international ISDN (TON 0b001=001, NPI 0b0001=0001 => 0x91) is a
     * valid MSISDN for an E.164-derived IMS IMPU. Anything else is rejected:
     * never guess a domestic/unknown number. */
    if (ton_npi != 0x91) return false;
    if (ndigits == 0 || ndigits > IMS_MSISDN_MAX_DIGITS) return false;
    /* BCD bytes needed to hold ndigits nibbles, with a possible filler. */
    size_t nbcd = (size_t)(ndigits + 1u) / 2u;
    if (nbcd > IMS_MSISDN_MAX_BCDBYTES || (size_t)2u + nbcd > ef_len) return false;
    char digits[IMS_MSISDN_MAX_DIGITS + 1];
    size_t d = 0;
    for (size_t i = 0; i < nbcd && d < ndigits; i++) {
        uint8_t b = ef[2 + i];
        /* Low nibble first. */
        digits[d++] = (char)('0' + (b & 0x0f));
        if (d < ndigits) {
            uint8_t hi = (b >> 4) & 0x0f;
            if (hi > 9 || (b & 0x0f) > 9) return false; /* non-digit nibble */
            digits[d++] = (char)('0' + hi);
        } else {
            /* final filler nibble must be 0xF */
            if ((b & 0x0f) > 9) return false;
        }
    }
    digits[d] = 0;
    if (cap <= d) return false;
    memcpy(out, digits, d + 1);
    return true;
}

bool ims_msisdn_impu(const char *digits, const char *domain,
                     char *out, size_t cap)
{
    if (!digits || !domain || !out || cap == 0) return false;
    out[0] = 0;
    size_t n = strlen(digits);
    if (n == 0 || n > IMS_MSISDN_MAX_DIGITS) return false;
    for (size_t i = 0; i < n; i++)
        if (digits[i] < '0' || digits[i] > '9') return false;
    /* "+<digits>@<domain>", prefixed by "sip:". */
    size_t need = 4 + 1 + n + 1 + strlen(domain) + 1;
    if (need > cap) return false;
    char *p = out;
    memcpy(p, "sip:+", 5); p += 5;
    memcpy(p, digits, n); p += n;
    *p++ = '@';
    size_t dl = strlen(domain);
    memcpy(p, domain, dl); p += dl;
    *p = 0;
    return true;
}
