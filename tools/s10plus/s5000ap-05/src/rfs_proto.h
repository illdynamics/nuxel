/*
 * rfs_proto.h — S5000AP RFS raw-request header parsing + classification.
 * SPDX-License-Identifier: GPL-2.0-only
 *
 * LIVE-observed RFS wire format (ch 245, IPC_RFS; NOT sipc_fmt_hdr):
 *   [u32 len LE][u8 op_class][u8 flags][u16 path_len][u16 reserved][path+'\0'...]
 *
 * This module is PURE (no I/O). It parses/classifies only. It NEVER executes an
 * RFS operation. Destructive op-classes are flagged so the caller can fail
 * closed. It is freestanding and host-fuzzable.
 */
#ifndef NUXEL_RFS_PROTO_H
#define NUXEL_RFS_PROTO_H

#include <stdint.h>
#include <stddef.h>
#include <stdbool.h>

#ifdef __cplusplus
extern "C" {
#endif

#define RFS_PROTO_HDR_MIN   10u   /* fixed header before the path */
#define RFS_PROTO_OP_MAX    48u

typedef enum rfs_proto_result {
    RFS_PROTO_OK = 0,
    RFS_PROTO_SHORT = -1,     /* fewer than RFS_PROTO_HDR_MIN bytes */
    RFS_PROTO_LEN_MISMATCH = -2, /* declared len inconsistent with buffer */
} rfs_proto_result;

struct rfs_proto_msg {
    uint32_t len;        /* declared length field */
    uint8_t  op_class;
    uint8_t  flags;
    uint16_t path_len;   /* declared path length (incl NUL) */
    char     opcode[RFS_PROTO_OP_MAX]; /* printable, NUL-terminated */
    bool     opcode_valid;   /* opcode is fully printable ASCII */
    bool     destructive;    /* matched a known destructive op-class */
    bool     known;          /* op-class present in knowledge table */
};

/*
 * Parse an RFS raw request header from `data`/`len`. Pure; never touches I/O.
 * Returns RFS_PROTO_OK on a parseable header (even if op unknown), else a
 * negative rfs_proto_result. `out` is fully populated on OK.
 */
int rfs_proto_parse(const uint8_t *data, size_t len, struct rfs_proto_msg *out);

#ifdef __cplusplus
}
#endif
#endif /* NUXEL_RFS_PROTO_H */
