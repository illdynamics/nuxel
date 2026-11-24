/*
 * rfs_nv.c — S5000AP RFS NV (persistent NV/EFS) transaction implementation.
 * SPDX-License-Identifier: GPL-2.0-only
 *
 * PURE (no I/O). See rfs_nv.h for the recovered contract and provenance.
 * This file only parses/serializes byte records and applies the fail-closed
 * provisioning policy; the caller performs the actual device/EFS I/O.
 */
#include "rfs_nv.h"
#include <string.h>

enum rfs_nv_parse_result rfs_nv_item_parse(const uint8_t *buf, size_t len,
                                           struct rfs_nv_item *out)
{
    uint32_t offset, length;
    if (!buf || !out) return RFS_NV_PARSE_BADARG;
    memset(out, 0, sizeof(*out));
    if (len < RFS_NV_HDR_MIN) return RFS_NV_PARSE_SHORT;

    out->op  = buf[0];
    out->seq = buf[1];
    /* buf[2..5] = reserved u32 (ignored, preserved nowhere) */
    offset = (uint32_t)buf[RFS_NV_OFFSET_FIELD]
           | ((uint32_t)buf[RFS_NV_OFFSET_FIELD + 1] << 8)
           | ((uint32_t)buf[RFS_NV_OFFSET_FIELD + 2] << 16)
           | ((uint32_t)buf[RFS_NV_OFFSET_FIELD + 3] << 24);
    length = (uint32_t)buf[RFS_NV_LENGTH_FIELD]
           | ((uint32_t)buf[RFS_NV_LENGTH_FIELD + 1] << 8)
           | ((uint32_t)buf[RFS_NV_LENGTH_FIELD + 2] << 16)
           | ((uint32_t)buf[RFS_NV_LENGTH_FIELD + 3] << 24);

    /* Vendor clamps ->0x80000 (ProcessNvWrite `cmp w6,#0x80,lsl#12`). */
    if (length > RFS_NV_MAX_VALUE) return RFS_NV_PARSE_OVERFLOW;
    /* The value must be fully present inside buf. */
    if ((size_t)length + RFS_NV_DATA_FIELD > len) return RFS_NV_PARSE_OVERFLOW;

    out->offset = offset;
    out->length = length;
    out->data   = (length == 0) ? NULL : (buf + RFS_NV_DATA_FIELD);
    out->valid  = true;
    return RFS_NV_PARSE_OK;
}

size_t rfs_nv_item_serialize(uint8_t op, uint8_t seq, uint32_t offset,
                             uint32_t length, const uint8_t *data,
                             uint8_t *out, size_t cap)
{
    if (!out || cap < RFS_NV_HDR_MIN) return 0;
    if (length > RFS_NV_MAX_VALUE) return 0;
    if (RFS_NV_HDR_MIN + (size_t)length > cap) return 0;
    if (length > 0 && !data) return 0;

    out[0] = op;
    out[1] = seq;
    out[2] = 0; out[3] = 0; out[4] = 0; out[5] = 0;  /* reserved u32 */
    out[6] = (uint8_t)(offset & 0xff);
    out[7] = (uint8_t)((offset >> 8) & 0xff);
    out[8] = (uint8_t)((offset >> 16) & 0xff);
    out[9] = (uint8_t)((offset >> 24) & 0xff);
    out[10] = (uint8_t)(length & 0xff);
    out[11] = (uint8_t)((length >> 8) & 0xff);
    out[12] = (uint8_t)((length >> 16) & 0xff);
    out[13] = (uint8_t)((length >> 24) & 0xff);
    if (length > 0) memcpy(out + RFS_NV_DATA_FIELD, data, length);
    return RFS_NV_HDR_MIN + (size_t)length;
}

size_t rfs_nv_response_build(uint8_t op, uint8_t seq, uint8_t result,
                             uint32_t detail, uint8_t out[RFS_NV_RESP_LEN])
{
    if (!out) return 0;
    /* [u32 total_len][u8 type][u8 op_echo][u8 result][u32 detail] = 15 */
    out[0] = RFS_NV_RESP_LEN;   /* total length (15) */
    out[1] = 0;                 /* length hi byte (0) */
    out[2] = 0;
    out[3] = 0;
    out[4] = 2;                 /* type = 2 (NV format) */
    out[5] = op;                /* op echo (request byte offset 5 -> op) */
    out[6] = (uint8_t)(seq ? seq : 0);  /* seq/correlation echo */
    out[7] = result;            /* 0 success / 1 failure */
    out[8] = (uint8_t)(detail & 0xff);
    out[9] = (uint8_t)((detail >> 8) & 0xff);
    out[10] = (uint8_t)((detail >> 16) & 0xff);
    out[11] = (uint8_t)((detail >> 24) & 0xff);
    out[12] = 0; out[13] = 0; out[14] = 0;
    return RFS_NV_RESP_LEN;
}

enum rfs_nv_provision_decision rfs_nv_provision_policy(
    uint32_t item_id, bool item_protected, bool have_offset,
    uint32_t length_limit, uint32_t authenticated_offset,
    const char *apn, size_t apn_len,
    uint32_t *out_offset, uint32_t *out_length)
{
    if (out_offset) *out_offset = 0;
    if (out_length) *out_length = 0;

    if (!apn) return RFS_NV_DENY_BADAPN;
    if (apn_len == 0 || apn_len >= 128u) return RFS_NV_DENY_BADAPN;
    /* Reject any embedded NUL within the APN length (must be one C string). */
    if (memchr(apn, '\0', apn_len) != NULL) return RFS_NV_DENY_BADAPN;

    if (item_protected) return RFS_NV_DENY_PROTECTED;
    if (item_id != RFS_NV_ITEM_ATTACH_APN_ID) return RFS_NV_DENY_UNKNOWN_ITEM;

    /* A write is only authorized when an authenticated, read-back
     * (offset,length) is already held; never guess. */
    if (!have_offset || length_limit == 0) return RFS_NV_DENY_NO_OFFSET;
    if (apn_len > length_limit) return RFS_NV_DENY_LENGTH;

    if (out_offset) *out_offset = authenticated_offset;
    if (out_length) *out_length = (uint32_t)apn_len;
    return RFS_NV_ALLOW;
}
