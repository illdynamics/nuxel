/*
 * sipc5_fmt.h — SIPC5 link-layer + SIPC FORMAT (FMT) message framing.
 *
 * Copyright (C) 2026 Nuxel project.
 *
 * SPDX-License-Identifier: GPL-2.0-only
 *
 * This is a FREESTANDING (no <linux/...>) transcription of the two framing
 * layers that the Samsung Shannon S5000AP driver stack exposes to userspace:
 *
 *  1. SIPC5 link-layer header — drivers/misc/modem_v1/include/sipc5.h
 *  2. SIPC FORMAT message header (sipc_fmt_hdr) — drivers/misc/modem_v1/modem_prj.h
 *
 * Pinned kernel source: android_kernel_samsung_exynos9820 (Linux4)
 *   commit f7194c1d15eded1c2a1a4dc63825b26103435cc0  (4.14.253)
 *   drivers/misc/modem_v1/include/sipc5.h
 *   drivers/misc/modem_v1/modem_prj.h
 *   drivers/misc/modem_v1/modem_v1.h   (enum sipc_ch_id)
 *
 * IMPORTANT READ-MODEL FACT (from modem_io_device.c rx paths):
 *
 *  - The KERNEL strips the SIPC5 link-layer header before delivering FMT and
 *    RAW traffic to userspace (skb_pull(skb, sipc5_get_hdr_len())) and it
 *    gathers SIPC5 multi-frame fragments (gather_multi_frame) before queuing.
 *    Therefore a userspace read() on /dev/umts_ipc0 sees the reassembled SIPC
 *    FORMAT payload beginning with `struct sipc_fmt_hdr`, NOT the link header.
 *
 *  - Fragmentation (multi-frame) is still modelled here because (a) the
 *    link header is what would appear on a raw tap of the SHMEM ring and
 *    (b) Rust/eBPF/diagnostic consumers may need to validate it. The parser
 *    supports BOTH: parse the link header when present (PARSE_LINK flag) or
 *    parse a stripped FMT payload directly.
 *
 * We intentionally do NOT invent message-cmd semantics: the meaning of
 * main_cmd/sub_cmd/cmd_type (SIM ready, registration, bearer, RFS opcodes)
 * is defined only in the closed Samsung libsec-ril.so and is classed UNKNOWN
 * here. This header only validates framing, lengths, channel class and
 * sequence/correlation fields.
 *
 * BITFIELD NOTE: struct multi_frame_control uses a C bitfield (u8 id:7,more:1).
 * On the little-endian AArch64/ARM GCC ABI `id` occupies bits 0..6 and `more`
 * occupies bit 7 (MSB). We therefore model it EXACTLY as the kernel macros do
 * (SIPC_MULTI_FRAME_MORE_BIT=0x80, ID_MASK=0x7F) rather than trusting bitfield
 * layout portability.
 */
#ifndef NUXEL_SIPC5_FMT_H
#define NUXEL_SIPC5_FMT_H

#include <stdint.h>
#include <stddef.h>
#include <stdbool.h>

#ifdef __cplusplus
extern "C" {
#endif

typedef uint8_t  u8;
typedef uint16_t u16;
typedef uint32_t u32;

/* ------------------------------------------------------------------ *
 * SIPC5 link-layer (include/sipc5.h)
 * ------------------------------------------------------------------ */

#define SIPC5_START_MASK        0xF8u
#define SIPC5_CONFIG_MASK       0x07u
#define SIPC5_EXT_FIELD_MASK    0x03u
#define SIPC5_PADDING_EXIST     0x04u
#define SIPC5_EXT_FIELD_EXIST   0x02u
#define SIPC5_CTL_FIELD_EXIST   0x01u
#define SIPC5_MULTI_FRAME_CFG   0x03u
#define SIPC5_EXT_LENGTH_CFG    0x02u

#define SIPC5_MIN_HEADER_SIZE              4u
#define SIPC5_HEADER_SIZE_WITH_CTL_FLD     5u
#define SIPC5_HEADER_SIZE_WITH_EXT_LEN     6u
#define SIPC5_MAX_HEADER_SIZE              6u

#define SIPC5_CONFIG_OFFSET   0u
#define SIPC5_CH_ID_OFFSET    1u
#define SIPC5_LEN_OFFSET      2u
#define SIPC5_CTRL_OFFSET     4u
#define SIPC5_EXT_LEN_OFFSET  4u

/* multi-frame control (modem_prj.h), modelled bit-exact */
#define SIPC_MULTI_FRAME_MORE_BIT  0x80u
#define SIPC_MULTI_FRAME_ID_MASK   0x7Fu

/* ------------------------------------------------------------------ *
 * SIPC FORMAT message header (modem_prj.h struct sipc_fmt_hdr)
 * ------------------------------------------------------------------ */

#define SIPC_FMT_HDR_SIZE 7u

struct __attribute__((__packed__)) sipc_fmt_hdr {
    u16 len;       /* payload length, host-endian (little-endian on target) */
    u8  msg_seq;   /* message sequence number */
    u8  ack_seq;   /* acknowledgement/correlation sequence number */
    u8  main_cmd;  /* command class (message group) */
    u8  sub_cmd;   /* command sub-class */
    u8  cmd_type;  /* command type (request/response/notification) */
};

/* ------------------------------------------------------------------ *
 * SIPC5 channel-id classes (modem_v1.h enum sipc_ch_id)
 * ------------------------------------------------------------------ */
enum sipc5_channel_id {
    SIPC_CH_ID_RAW_0 = 0,
    SIPC_CH_ID_PDP_0 = 10,
    SIPC_CH_ID_PDP_14 = 24,
    SIPC_CH_ID_BT_DUN = 25,
    SIPC_CH_ID_CPLOG1 = 28,
    SIPC_CH_ID_CPLOG2 = 29,
    SIPC_CH_ID_LOOPBACK1 = 30,
    SIPC_CH_ID_LOOPBACK2 = 31,
    SIPC_CH_ID_CASS = 35,
    /* 32..214 reserved */
    SIPC5_CH_ID_BOOT_0 = 215,
    SIPC5_CH_ID_BOOT_9 = 224,
    SIPC5_CH_ID_DUMP_0 = 225,
    SIPC5_CH_ID_DUMP_9 = 234,
    SIPC5_CH_ID_FMT_0 = 235,
    SIPC5_CH_ID_FMT_9 = 244,
    SIPC5_CH_ID_RFS_0 = 245,
    SIPC5_CH_ID_RFS_9 = 254,
    SIPC5_CH_ID_MAX = 255
};

/* Reserved channels per modem_prj.h: sipc5_is_not_reserved_channel() */
static inline bool sipc5_is_reserved_channel(u8 ch)
{
    return (ch == 0 || ch == 5 || ch == 6 || ch == 27 || ch == 255);
}

static inline bool sipc5_fmt_ch(u8 ch)    { return ch >= 235 && ch <= 244; }
static inline bool sipc5_rfs_ch(u8 ch)    { return ch >= 245 && ch <= 254; }
static inline bool sipc5_boot_ch(u8 ch)   { return ch >= 215 && ch <= 224; }
static inline bool sipc5_dump_ch(u8 ch)   { return ch >= 225 && ch <= 234; }
static inline bool sipc5_udl_ch(u8 ch)    { return ch >= 215 && ch <= 234; }
static inline bool sipc5_ipc_ch(u8 ch)    { return ch > 0 && (ch < 215 || ch > 234); }
static inline bool sipc5_pdp_ch(u8 ch)    { return ch >= 10 && ch <= 24; }

/* ------------------------------------------------------------------ *
 * SIPC5 link-header parsing (faithful to sipc5.h inline helpers)
 * ------------------------------------------------------------------ */

struct nuxel_sipc5_link {
    u8  cfg;               /* raw first byte */
    u8  ch;                /* channel id */
    u32 frame_len;         /* uncompressed frame length */
    u32 hdr_len;           /* 4/5/6 bytes */
    u32 total_len;         /* frame + padding */
    u32 padding;           /* padding bytes */
    bool start_valid;
    bool multi_frame;
    bool ext_len;
    bool padding_exist;
    u8  ctrl;              /* multi-frame control byte (if multi_frame) */
};

/*
 * Parse ONLY the SIPC5 link header from `buf` (which must contain at least
 * hdr_len bytes; caller must supply enough). Returns 0 on success and fills
 * `out`, or a negative errno-style code. This function does NOT read beyond
 * `avail`; it validates that `avail` is large enough for the header itself.
 */
int sipc5_parse_link_header(const u8 *buf, size_t avail,
                            struct nuxel_sipc5_link *out);

/* ------------------------------------------------------------------ *
 * SIPC FORMAT message parsing
 * ------------------------------------------------------------------ */

struct nuxel_sipc_fmt {
    const u8 *payload;      /* pointer INTO caller buffer, after fmt hdr */
    u32  payload_len;       /* bytes of payload (len field) */
    u8   msg_seq;
    u8   ack_seq;
    u8   main_cmd;
    u8   sub_cmd;
    u8   cmd_type;
    bool truncated;         /* declared len exceeds available bytes */
};

typedef enum sipc_parse_result {
    SIPC_PARSE_OK = 0,
    SIPC_PARSE_TRUNCATED = -1,   /* need more bytes */
    SIPC_PARSE_BAD_START = -2,   /* start nibble invalid */
    SIPC_PARSE_BAD_CFG   = -3,   /* reserved config bits */
    SIPC_PARSE_OVERFLOW  = -4,   /* length overflow vs sane bound */
    SIPC_PARSE_RESERVED_CH = -5, /* reserved channel id */
} sipc_parse_result;

/*
 * Parse a SIPC FORMAT message that begins with `struct sipc_fmt_hdr`.
 * `buf`/`len` = the bytes available so far (may be a partial read).
 * On OK: *consumed = total bytes consumed (fmt hdr + payload), out filled.
 * On TRUNCATED: more bytes are required; no fields are trusted.
 *
 * `max_payload` is a caller-supplied sanity cap (e.g. 0x10000) to reject
 * corrupt/hostile length fields that would overflow a bounded allocation.
 */
int sipc5_parse_fmt(const u8 *buf, size_t len, u32 max_payload,
                    struct nuxel_sipc_fmt *out, size_t *consumed);

#ifdef __cplusplus
}
#endif

#endif /* NUXEL_SIPC5_FMT_H */
