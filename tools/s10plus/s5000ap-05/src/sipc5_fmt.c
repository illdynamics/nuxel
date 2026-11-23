/*
 * sipc5_fmt.c — SIPC5 link-header + SIPC FORMAT message parser (freestanding).
 * SPDX-License-Identifier: GPL-2.0-only
 *
 * Faithful transcription of the pinned kernel inline helpers:
 *   drivers/misc/modem_v1/include/sipc5.h
 *   drivers/misc/modem_v1/modem_prj.h
 * See sipc5_fmt.h for provenance and the read-model rationale.
 *
 * This parser is SAFE OFF BY DEFAULT for writes: it only parses bytes and
 * never issues an ioctl/write to any device. All "command" semantics are
 * deliberately absent — framing validation only.
 */

#include "sipc5_fmt.h"

#include <limits.h>
#include <string.h>

/* On the little-endian target this == 7 (8-byte word), matching the kernel's
 * BITS_PER_LONG/8 - 1. It is expressed here as a constant parameterisable for
 * hosts whose long is 8 bytes (macOS LP64 also 8). */
static const u32 SIPC_PAD_ALIGN_MINUS_1 = 7u;

static u32 calc_padding(u32 len)
{
    u32 residue = len & SIPC_PAD_ALIGN_MINUS_1;
    return residue ? (8u - residue) : 0u;
}

int sipc5_parse_link_header(const u8 *buf, size_t avail,
                            struct nuxel_sipc5_link *out)
{
    u8  cfg;
    u8  ext_mask;
    int hdr_len;
    u32 frame_len;

    if (!buf || !out)
        return -22 /* EINVAL */;

    if (avail < 1)
        return SIPC_PARSE_TRUNCATED;

    cfg = buf[0];

    /* start mask: top 5 bits must equal 0xF8 */
    if ((cfg & SIPC5_START_MASK) != SIPC5_START_MASK)
        return SIPC_PARSE_BAD_START;

    ext_mask = cfg & SIPC5_EXT_FIELD_MASK;

    if (ext_mask == SIPC5_MULTI_FRAME_CFG) {           /* 0b11 */
        hdr_len = SIPC5_HEADER_SIZE_WITH_CTL_FLD;      /* 5 */
    } else if (ext_mask == SIPC5_EXT_LENGTH_CFG) {     /* 0b10 */
        hdr_len = SIPC5_HEADER_SIZE_WITH_EXT_LEN;      /* 6 */
    } else {
        hdr_len = SIPC5_MIN_HEADER_SIZE;               /* 4 */
    }

    if (avail < (size_t)hdr_len)
        return SIPC_PARSE_TRUNCATED;

    /* channel */
    out->ch = buf[SIPC5_CH_ID_OFFSET];

    /* length: multi-frame uses u16, ext-length uses u32, else u16.
     * The kernel reads the field starting at SIPC5_LEN_OFFSET (byte 2). */
    if (ext_mask == SIPC5_EXT_LENGTH_CFG) {
        /* 32-bit length (little-endian) */
        frame_len = (u32)buf[2] | ((u32)buf[3] << 8) |
                    ((u32)buf[4] << 16) | ((u32)buf[5] << 24);
    } else {
        /* 16-bit length (little-endian) */
        frame_len = (u32)buf[2] | ((u32)buf[3] << 8);
    }

    out->cfg = cfg;
    out->frame_len = frame_len;
    out->hdr_len = (u32)hdr_len;
    out->multi_frame = (ext_mask == SIPC5_MULTI_FRAME_CFG);
    out->ext_len     = (ext_mask == SIPC5_EXT_LENGTH_CFG);
    out->padding_exist = (cfg & SIPC5_PADDING_EXIST) != 0;
    out->start_valid = true;

    if (out->multi_frame)
        out->ctrl = buf[SIPC5_CTRL_OFFSET];
    else
        out->ctrl = 0;

    out->padding = out->padding_exist ? calc_padding(frame_len) : 0u;
    out->total_len = frame_len + out->padding;

    return SIPC_PARSE_OK;
}

int sipc5_parse_fmt(const u8 *buf, size_t len, u32 max_payload,
                    struct nuxel_sipc_fmt *out, size_t *consumed)
{
    const struct sipc_fmt_hdr *hdr;
    u32 plen;

    if (!buf || !out || !consumed)
        return -22 /* EINVAL */;

    *consumed = 0;
    memset(out, 0, sizeof(*out));

    if (len < SIPC_FMT_HDR_SIZE)
        return SIPC_PARSE_TRUNCATED;

    hdr = (const struct sipc_fmt_hdr *)buf;

    /* length is host-endian; on the AArch64 target this is little-endian.
     * (Linux x86_64/aarch64/arm all little-endian in practice.) */
    plen = hdr->len;

    if (plen > max_payload)
        return SIPC_PARSE_OVERFLOW;

    if ((size_t)SIPC_FMT_HDR_SIZE + (size_t)plen > len) {
        *consumed = 0;
        out->truncated = true;
        return SIPC_PARSE_TRUNCATED;
    }

    out->msg_seq = hdr->msg_seq;
    out->ack_seq = hdr->ack_seq;
    out->main_cmd = hdr->main_cmd;
    out->sub_cmd = hdr->sub_cmd;
    out->cmd_type = hdr->cmd_type;
    out->payload_len = plen;
    out->payload = buf + SIPC_FMT_HDR_SIZE;
    out->truncated = false;

    *consumed = (size_t)SIPC_FMT_HDR_SIZE + (size_t)plen;
    return SIPC_PARSE_OK;
}

/* String names for parser results (for logs/diagnostics; no secrets). */
const char *sipc_parse_result_name(int r)
{
    switch (r) {
    case SIPC_PARSE_OK:           return "OK";
    case SIPC_PARSE_TRUNCATED:    return "TRUNCATED";
    case SIPC_PARSE_BAD_START:    return "BAD_START";
    case SIPC_PARSE_BAD_CFG:      return "BAD_CFG";
    case SIPC_PARSE_OVERFLOW:     return "OVERFLOW";
    case SIPC_PARSE_RESERVED_CH:  return "RESERVED_CH";
    default:                      return "UNKNOWN";
    }
}
