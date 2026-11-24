/*
 * nv_items.c — S5000AP CP-NV record decoder + MD5 integrity + provisioning
 * policy. GPL-2.0-only. PURE (no I/O). See nv_items.h for the ABI contract.
 *
 * MD5 is the ACTUAL vendor integrity mechanism (nv.log "MD5 on/off"), NOT a
 * mandatory asymmetric signature. This module carries a self-contained
 * RFC 1321 MD5 so it stays freestanding (no OpenSSL) and cross-compilable.
 */
#include "nv_items.h"

#include <string.h>

#define ROTL(x, n) (((x) << (n)) | ((x) >> (32 - (n))))

static uint32_t rd32(const uint8_t *p)
{
    return ((uint32_t)p[0]) | ((uint32_t)p[1] << 8) |
           ((uint32_t)p[2] << 16) | ((uint32_t)p[3] << 24);
}

size_t nv_record_parse(const uint8_t *buf, size_t len, struct nv_record *out)
{
    if (!buf || !out) return 0;
    memset(out, 0, sizeof(*out));
    if (len < NV_REC_HDR_MIN) return 0;

    out->size     = rd32(buf + 0);
    out->name_ptr = rd32(buf + 4);
    out->type     = rd32(buf + 8);
    out->aux_ptr  = rd32(buf + 12);

    out->size_valid = out->size >= NV_REC_HDR_MIN && out->size <= len;

    /* CP runtime RAM/BSS/text spans recovered from the live snapshot. */
    uint32_t hi16 = out->name_ptr & 0xFFFF0000u;
    out->name_is_ram = (hi16 == 0x41600000u || hi16 == 0x41700000u ||
                        hi16 == 0x40fc0000u || hi16 == 0x40010000u ||
                        (out->name_ptr & 0xFF000000u) == 0x42000000u ||
                        (out->name_ptr & 0xFF000000u) == 0x47000000u);

    return out->size_valid ? out->size : 0;
}

const char *nv_name_ptr_span(uint32_t name_ptr)
{
    uint32_t hi16 = name_ptr & 0xFFFF0000u;
    if (hi16 == 0x41600000u || hi16 == 0x41700000u) return "CP-RAM/data";
    if (hi16 == 0x40fc0000u) return "CP-text/rodata";
    if (hi16 == 0x40010000u) return "CP-MAIN/text";
    uint32_t hi = name_ptr & 0xFF000000u;
    if (hi == 0x42000000u) return "CP-data/rodata";
    if (hi == 0x47000000u) return "CP-VSS";
    return "unknown";
}

/* --- Self-contained RFC 1321 MD5 --- */

typedef struct { uint32_t a, b, c, d; } md5_state;

static void md5_process(md5_state *s, const uint8_t block[64])
{
    static const uint32_t K[64] = {
        0xd76aa478,0xe8c7b756,0x242070db,0xc1bdceee,0xf57c0faf,0x4787c62a,
        0xa8304613,0xfd469501,0x698098d8,0x8b44f7af,0xffff5bb1,0x895cd7be,
        0x6b901122,0xfd987193,0xa679438e,0x49b40821,0xf61e2562,0xc040b340,
        0x265e5a51,0xe9b6c7aa,0xd62f105d,0x02441453,0xd8a1e681,0xe7d3fbc8,
        0x21e1cde6,0xc33707d6,0xf4d50d87,0x455a14ed,0xa9e3e905,0xfcefa3f8,
        0x676f02d9,0x8d2a4c8a,0xfffa3942,0x8771f681,0x6d9d6122,0xfde5380c,
        0xa4beea44,0x4bdecfa9,0xf6bb4b60,0xbebfbc70,0x289b7ec6,0xeaa127fa,
        0xd4ef3085,0x04881d05,0xd9d4d039,0xe6db99e5,0x1fa27cf8,0xc4ac5665,
        0xf4292244,0x432aff97,0xab9423a7,0xfc93a039,0x655b59c3,0x8f0ccc92,
        0xffeff47d,0x85845dd1,0x6fa87e4f,0xfe2ce6e0,0xa3014314,0x4e0811a1,
        0xf7537e82,0xbd3af235,0x2ad7d2bb,0xeb86d391
    };
    static const int S[64] = {
        7,12,17,22,7,12,17,22,7,12,17,22,7,12,17,22,
        5,9,14,20,5,9,14,20,5,9,14,20,5,9,14,20,
        4,11,16,23,4,11,16,23,4,11,16,23,4,11,16,23,
        6,10,15,21,6,10,15,21,6,10,15,21,6,10,15,21
    };
    uint32_t M[16];
    for (int i = 0; i < 16; i++) M[i] = rd32(&block[i * 4]);

    uint32_t A = s->a, B = s->b, C = s->c, D = s->d;
    for (int i = 0; i < 64; i++) {
        uint32_t F; int g;
        if (i < 16)      { F = (B & C) | (~B & D); g = i; }
        else if (i < 32) { F = (D & B) | (~D & C); g = (5 * i + 1) & 15; }
        else if (i < 48) { F = B ^ C ^ D; g = (3 * i + 5) & 15; }
        else             { F = C ^ (B | ~D); g = (7 * i) & 15; }
        uint32_t tmp = D;
        D = C;
        C = B;
        B = B + ROTL(A + F + K[i] + M[g], S[i]);
        A = tmp;
    }
    s->a += A; s->b += B; s->c += C; s->d += D;
}

int nv_md5_hex(const uint8_t *data, size_t len, char out[33])
{
    if (!out) return -1;
    md5_state s = { 0x67452301u, 0xefcdab89u, 0x98badcfeu, 0x10325476u };
    uint64_t bitlen = (uint64_t)len * 8u;
    uint8_t block[64];

    size_t i = 0;
    for (; i + 64 <= len; i += 64) md5_process(&s, data + i);

    /* final block with padding */
    size_t rem = len - i;
    memset(block, 0, sizeof block);
    if (rem) memcpy(block, data + i, rem);
    block[rem] = 0x80;
    if (rem >= 56) {
        md5_process(&s, block);
        memset(block, 0, sizeof block);
    }
    for (int k = 0; k < 8; k++) block[56 + k] = (uint8_t)((bitlen >> (8 * k)) & 0xff);
    md5_process(&s, block);

    static const char hex[] = "0123456789abcdef";
    uint32_t w[4] = { s.a, s.b, s.c, s.d };
    for (unsigned j = 0; j < 4; j++) {
        for (int k = 0; k < 4; k++) {
            out[j * 8 + k * 2]     = hex[(w[j] >> (k * 8 + 4)) & 0x0f];
            out[j * 8 + k * 2 + 1] = hex[(w[j] >> (k * 8)) & 0x0f];
        }
    }
    out[32] = '\0';
    return 0;
}

static int hexval(char c)
{
    if (c >= '0' && c <= '9') return c - '0';
    if (c >= 'a' && c <= 'f') return c - 'a' + 10;
    if (c >= 'A' && c <= 'F') return c - 'A' + 10;
    return -1;
}

int nv_md5_verify(const uint8_t *data, size_t len, const char *stored_hex)
{
    if (!data || !stored_hex) return -1;
    char computed[33];
    if (nv_md5_hex(data, len, computed) != 0) return -1;
    for (int i = 0; i < 32; i++) {
        int a = hexval(computed[i]);
        int b = hexval(stored_hex[i]);
        if (a < 0 || b < 0) return -1;
        if (a != b) return 1;
    }
    return stored_hex[32] == '\0' ? 0 : -1;
}

enum nv_provision_decision nv_provision_policy(bool write_requested,
                                               bool item_known,
                                               bool item_protected,
                                               bool md5_ok)
{
    if (!write_requested)
        return NV_PROV_ALLOW_BACKUP_READ;
    if (item_protected)
        return NV_PROV_DENY_PROTECTED;
    if (!item_known)
        return NV_PROV_DENY_UNKNOWN_ID;
    if (!md5_ok)
        return NV_PROV_DENY_MD5_MISMATCH;
    return NV_PROV_ALLOW_BACKUP_READ;
}

/* --- Round-38: initial-attach APN record builder (semantic contract) --- */
int nv_apn_record_init(struct nv_apn_record *rec, const char *apn, size_t apn_len)
{
    if (!rec || !apn)
        return -1;
    if (apn_len == 0 || apn_len >= NV_ATTACH_APN_NAME_MAX)
        return -1;
    /* Reject embedded NUL within the stated length (must be a single C string). */
    if (memchr(apn, '\0', apn_len) != NULL && memchr(apn, '\0', apn_len) != apn + apn_len - 1)
        return -1;
    memset(rec, 0, sizeof(*rec));
    memcpy(rec->apn, apn, apn_len);
    rec->apn[apn_len] = '\0';
    rec->apn_len = apn_len;
    rec->valid = true;
    return 0;
}
