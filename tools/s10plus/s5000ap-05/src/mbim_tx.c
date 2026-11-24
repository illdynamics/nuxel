/*
 * mbim_tx.c — S5000AP MBIM<->SIPC builders (serialize-only).
 *
 * SPDX-License-Identifier: GPL-2.0-only
 *
 * See mbim_tx.h for the recovered-facts provenance. This module only builds
 * bytes; transmission is performed by radiod.c under explicit write
 * authorization (--write-enable) via the existing transport + policy gates.
 *
 * MBIM "MS LTE Attach Config" (CID 0x0A) info-buffer (recovered + public spec):
 *   [u32 elementCount][u32 dataOffset=0x1c]
 *   then per context: [u32 offset][u32 size]  (3 slots)
 *   then concatenated MbimMsLteAttachContext records, each:
 *     +0x00 u32 contextIndex
 *     +0x04 u32 ipType
 *     +0x08 u32 authProtocol
 *     +0x0c u32 apnOffset     (relative to the whole info buffer)
 *     +0x10 u32 apnSize       (UTF-16LE bytes)
 *     +0x14 u32 userNameOffset
 *     +0x18 u32 userNameSize
 *     +0x1c u32 passwordOffset
 *     +0x20 u32 passwordSize
 *     +0x24 u32 compression
 *     +0x28 u32 spare
 *     +0x2c ... UTF-16LE strings (APN, username, password), 4-byte aligned
 *
 * The offsets are ABSOLUTE within the info buffer (the recovered
 * FillMbimMsLteAttachContext uses absolute string offsets; this matches the
 * public MBIM disposition where data starts at a fixed offset).
 */
#include "mbim_tx.h"

#include <string.h>
#include <stdint.h>

static uint8_t *put_u32le(uint8_t *p, uint32_t v)
{
    p[0] = (uint8_t)(v & 0xffu);
    p[1] = (uint8_t)((v >> 8) & 0xffu);
    p[2] = (uint8_t)((v >> 16) & 0xffu);
    p[3] = (uint8_t)((v >> 24) & 0xffu);
    return p + 4;
}

static uint32_t align4(uint32_t v) { return (v + 3u) & ~3u; }

size_t mbim_tx_utf8_to_utf16le(uint8_t *out16, size_t cap16,
                               const char *s, size_t max_bytes)
{
    size_t n = 0;
    const unsigned char *p = (const unsigned char *)s;
    if (!s || !out16) return 0;
    while (*p) {
        uint32_t cp = *p++;
        if (cp < 0x80) {
        } else if ((cp & 0xE0) == 0xC0) {
            cp = ((cp & 0x1F) << 6) | (*p++ & 0x3F);
        } else if ((cp & 0xF0) == 0xE0) {
            uint32_t c2 = *p++;
            uint32_t c3 = *p++;
            cp = ((cp & 0x0F) << 12) | ((c2 & 0x3F) << 6) | (c3 & 0x3F);
        } else {
            uint32_t c2 = *p++;
            uint32_t c3 = *p++;
            uint32_t c4 = *p++;
            cp = ((cp & 0x07) << 18) | ((c2 & 0x3F) << 12) |
                 ((c3 & 0x3F) << 6) | (c4 & 0x3F);
        }
        if (cp >= 0x10000u) {
            cp -= 0x10000u;
            if (n + 4 > cap16 || n + 4 > max_bytes) return 0;
            uint32_t hi = 0xD800u + (cp >> 10);
            uint32_t lo = 0xDC00u + (cp & 0x3FFu);
            out16[n++] = (uint8_t)(hi & 0xff);
            out16[n++] = (uint8_t)((hi >> 8) & 0xff);
            out16[n++] = (uint8_t)(lo & 0xff);
            out16[n++] = (uint8_t)((lo >> 8) & 0xff);
        } else {
            if (n + 2 > cap16 || n + 2 > max_bytes) return 0;
            out16[n++] = (uint8_t)(cp & 0xff);
            out16[n++] = (uint8_t)((cp >> 8) & 0xff);
        }
    }
    return n;
}

size_t mbim_tx_build_lte_attach_config(uint8_t *out, size_t cap,
                                       const struct mbim_attach_context *contexts,
                                       size_t ncontexts, uint32_t transaction_id)
{
    enum { MAX_CTX = 3, HDR = 12, CMD_HDR = 16, DATA_BASE = 28 };
    uint8_t body[MBIM_TX_MAX_FRAME];
    uint32_t ctx_off[MAX_CTX];          /* absolute info-buffer offset of each ctx */
    uint32_t ctx_size[MAX_CTX];
    uint32_t cursor = DATA_BASE;        /* absolute offset within info buffer */
    size_t i;

    if (!out || !contexts) return 0;
    if (ncontexts == 0 || ncontexts > MAX_CTX) return 0;

    /* Pass 1: pre-encode each context's UTF-16LE strings into a scratch and
     * compute sizes/offsets. */
    for (i = 0; i < ncontexts; i++) {
        if (!contexts[i].apn || !contexts[i].apn[0]) return 0;
        uint8_t t[512];
        uint32_t n_apn = (uint32_t)mbim_tx_utf8_to_utf16le(t, sizeof t,
                                                             contexts[i].apn, 0x100);
        uint32_t n_usr = contexts[i].username
            ? (uint32_t)mbim_tx_utf8_to_utf16le(t + n_apn, sizeof t - n_apn,
                                                contexts[i].username, 0x100) : 0u;
        uint32_t n_pwd = contexts[i].password
            ? (uint32_t)mbim_tx_utf8_to_utf16le(t + n_apn + n_usr, sizeof t - n_apn - n_usr,
                                                contexts[i].password, 0x100) : 0u;
        if (n_apn == 0) return 0;
        ctx_off[i] = cursor;
        ctx_size[i] = align4(44u + n_apn + n_usr + n_pwd);
        cursor += ctx_size[i];
        if (cursor + 4 > sizeof body) return 0;
    }

    uint32_t data_off_val = DATA_BASE; /* first context data begins at fixed 0x1c */
    /* HDR words: elementCount then dataOffset (0x1c) — matches recovered layout */
    size_t bl = 0;
    put_u32le(body + bl, (uint32_t)ncontexts); bl += 4;
    put_u32le(body + bl, data_off_val); bl += 4;

    /* per-context {offset,size} pairs */
    for (i = 0; i < ncontexts; i++) {
        put_u32le(body + bl, ctx_off[i]); bl += 4;
        put_u32le(body + bl, ctx_size[i]); bl += 4;
    }

    /* keep track of absolute data position; ctx_off[0] == DATA_BASE */
    uint32_t datap = ctx_off[0];
    for (i = 0; i < ncontexts; i++) {
        uint8_t t[512];
        uint32_t n_apn = (uint32_t)mbim_tx_utf8_to_utf16le(t, sizeof t,
                                                             contexts[i].apn, 0x100);
        uint32_t n_usr = contexts[i].username
            ? (uint32_t)mbim_tx_utf8_to_utf16le(t + n_apn, sizeof t - n_apn,
                                                contexts[i].username, 0x100) : 0u;
        uint32_t n_pwd = contexts[i].password
            ? (uint32_t)mbim_tx_utf8_to_utf16le(t + n_apn + n_usr, sizeof t - n_apn - n_usr,
                                                contexts[i].password, 0x100) : 0u;

        /* fixed 44-byte context header */
        uint8_t c[256];
        memset(c, 0, sizeof c);
        put_u32le(c + 0x00, (uint32_t)i);
        put_u32le(c + 0x04, contexts[i].ip_type);
        put_u32le(c + 0x08, contexts[i].auth);
        /* string offsets are absolute within info buffer */
        uint32_t apn_off = datap + 44u;
        uint32_t usr_off = apn_off + n_apn;
        uint32_t pwd_off = usr_off + n_usr;
        put_u32le(c + 0x0c, apn_off);
        put_u32le(c + 0x10, n_apn);
        put_u32le(c + 0x14, usr_off);
        put_u32le(c + 0x18, n_usr);
        put_u32le(c + 0x1c, pwd_off);
        put_u32le(c + 0x20, n_pwd);
        put_u32le(c + 0x24, 0u); /* compression */
        put_u32le(c + 0x28, 0u); /* spare */
        memcpy(c + 44, t, (size_t)(n_apn + n_usr + n_pwd));

        /* place into body at absolute offset datap */
        memcpy(body + datap, c, (size_t)ctx_size[i]);
        datap += ctx_size[i];
    }

    /* Compose the full MBIM message. */
    size_t info_len = cursor; /* total info-buffer length */
    size_t total = HDR + CMD_HDR + info_len;
    if (total > cap) return 0;

    uint8_t *p = out;
    p = put_u32le(p, MBIM_MSG_TYPE_COMMAND);
    p = put_u32le(p, (uint32_t)total);
    p = put_u32le(p, transaction_id);
    p = put_u32le(p, MBIM_CID_MS_LTE_ATTACH_CONFIG);
    p = put_u32le(p, 0u); /* SET */
    memcpy(p, body, info_len);
    return total;
}

size_t mbim_tx_build_raw_ipc_frame(uint8_t *out, size_t cap,
                                   const uint8_t *mbim, size_t mbim_len,
                                   uint8_t seq, uint8_t ack)
{
    size_t payload = 1u + mbim_len;
    size_t total = 7u + payload;
    if (!out || total > cap) return 0;
    out[0] = (uint8_t)(total & 0xff);
    out[1] = (uint8_t)((total >> 8) & 0xff);
    out[2] = seq;
    out[3] = ack;
    out[4] = MBIM_RAW_IPC_MAIN_CMD;
    out[5] = MBIM_RAW_IPC_SUB_CMD;
    out[6] = MBIM_RAW_IPC_CMD_TYPE;
    out[7] = MBIM_RAW_IPC_FWD_FLAG;
    if (mbim_len) memcpy(out + 8, mbim, mbim_len);
    return total;
}
