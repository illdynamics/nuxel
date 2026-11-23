/*
 * rfs_respond.c — S5000AP RFS responder (parse + policy + response builder).
 * SPDX-License-Identifier: GPL-2.0-only
 *
 * See rfs_respond.h for the recovered on-wire contract and provenance. This
 * file is PURE (no I/O, no filesystem access) so it is host-fuzzable and can be
 * unit-tested without a device. The caller (radiod.c) performs the actual
 * write() to /dev/umts_rfs0 only after this module has produced a valid,
 * policy-approved 14-byte response.
 */
#include "rfs_respond.h"
#include <string.h>

static bool ascii_printable(const uint8_t *p, size_t n, bool allow_nul_end)
{
    size_t i;
    if (n == 0) return false;
    for (i = 0; i < n; i++) {
        uint8_t c = p[i];
        if (c == 0) {
            /* a NUL terminates the path; it must be the last consumed byte */
            if (allow_nul_end && (i + 1 >= n || p[i+1] == 0)) return true;
            return (i + 1 <= n);
        }
        if (c < 0x20 || c > 0x7e) return false;
    }
    return true;
}

enum rfs_request_parse_result rfs_request_parse(const uint8_t *buf, size_t len,
                                                struct rfs_request *out)
{
    size_t want;
    if (!buf || !out) return RFS_REQ_SHORT;
    memset(out, 0, sizeof(*out));

    if (len < RFS_REQ_HDR_MIN) return RFS_REQ_SHORT;

    out->total_len = (uint32_t)buf[0] | ((uint32_t)buf[1] << 8) |
                     ((uint32_t)buf[2] << 16) | ((uint32_t)buf[3] << 24);
    out->op        = buf[4];
    out->seq       = buf[5];
    /* offset 6..9 is an op-specific u32 (path_len for path-carrying ops,
     * fd/handle/offset for open/close/lseek). */
    out->param     = (uint32_t)buf[6] | ((uint32_t)buf[7] << 8) |
                     ((uint32_t)buf[8] << 16) | ((uint32_t)buf[9] << 24);
    out->path_len  = out->param;

    /* Sane bounds. The vendor Nv class rejects len > 0x80000 (ProcessRfsPacket
     * `cmp w6,#0x80,lsl#12`). A path longer than RFS_MAX_PATH-1 is implausible
     * and is rejected to avoid unbounded copies. */
    if (out->total_len > (1u << 19) || out->path_len == 0 ||
        out->path_len >= RFS_MAX_PATH)
        return RFS_REQ_OVERFLOW;

    /* The path starts at offset 10 (4B len + 1B op + 1B seq + 4B param = 10).
     * It is path_len bytes incl NUL. */
    want = (size_t)out->path_len;
    if (10u + want > len) return RFS_REQ_LEN_MISMATCH;

    /* Copy at most RFS_MAX_PATH-1 bytes, always NUL-terminate. */
    {
        size_t n = want;
        if (n >= RFS_MAX_PATH) n = RFS_MAX_PATH - 1;
        memcpy(out->path, buf + 10, n);
        out->path[n] = '\0';
    }

    /* Path must be printable ASCII (the exact observed DELETE_ALL_VIS is). */
    if (!ascii_printable(buf + 10, want, true)) {
        out->path_valid = false;
        return RFS_REQ_LEN_MISMATCH;
    }
    out->path_valid = true;

    /* The special boot-stage marker: RFS_UNLINK_FILE of "DELETE_ALL_VIS".
     * Note: "DELETE_ALL_VIS" is the PATH (a cache-clean marker), the op is
     * RFS_UNLINK_FILE (delete/unlink). */
    out->special_delete_all_vis =
        (out->op == RFS_OP_UNLINK_FILE && strcmp(out->path, "DELETE_ALL_VIS") == 0);

    return RFS_REQ_OK;
}

size_t rfs_response_build(uint8_t op, uint8_t seq, int32_t result, int32_t detail,
                          uint8_t out[RFS_RESP_LEN])
{
    if (!out) return 0;
    /* [u32 result][u8 op][u8 seq][u16 reserved][u32 detail] = 14 bytes */
    out[0] = (uint8_t)((uint32_t)result & 0xff);
    out[1] = (uint8_t)(((uint32_t)result >> 8) & 0xff);
    out[2] = (uint8_t)(((uint32_t)result >> 16) & 0xff);
    out[3] = (uint8_t)(((uint32_t)result >> 24) & 0xff);
    out[4] = op;
    out[5] = seq;
    out[6] = 0;
    out[7] = 0;
    out[8] = (uint8_t)((uint32_t)detail & 0xff);
    out[9] = (uint8_t)(((uint32_t)detail >> 8) & 0xff);
    out[10] = (uint8_t)(((uint32_t)detail >> 16) & 0xff);
    out[11] = (uint8_t)(((uint32_t)detail >> 24) & 0xff);
    return RFS_RESP_LEN;
}

int rfs_response_policy(const struct rfs_request *req, int32_t *detail)
{
    if (!req) { if (detail) *detail = 0; return -1; }

    /*
     * FAIL-CLOSED DEFAULT: every RFS operation except the single approved,
     * no-side-effect boot marker is answered with an error. We do NOT execute
     * filesystem operations (open/read/write/unlink on real paths), and we do
     * NOT fabricate success for destructive or unknown operations.
     *
     * The ONLY success case is RFS_OP_UNLINK_FILE with path "DELETE_ALL_VIS":
     *   - This is the CP's boot-stage request to delete stale VIG/VIS
     *     visualizer-cache files under its RFS dir (/mnt/vendor/efs/...).
     *   - On Nuxel that filesystem IS NOT MOUNTED and those cache files DO NOT
     *     EXIST, so "deleting" them is an exact no-op (same observable result
     *     as a successful unlink() of already-absent cache entries).
     *   - No protected NV/EFS/IMEI/calibration data is touched by this marker.
     */
    if (req->special_delete_all_vis) {
        if (detail) *detail = 0;
        return 0;   /* success: no-op cleanup of non-existent VIG/VIS cache */
    }

    /* Everything else (including RFS_OPEN_FILE, *_READ/WRITE, NV_READ/WRITE,
     * RENAME, MAKE_DIR, CREATE, GET/PUT, NV_WRITE_ALL, NV_RESTORE) is refused.
     * Use -ENOSYS for unsupported opcodes, -EPERM for opcodes that would touch
     * protected filesystem state. */
    if (detail) *detail = 0;
    switch (req->op) {
    case RFS_OP_NV_READ:
    case RFS_OP_NV_WRITE_ALL:
    case RFS_OP_NV_RESTORE:
    case RFS_OP_WRITE_FILE:
    case RFS_OP_RENAME_FILE:
    case RFS_OP_CREATE_FILE:
    case RFS_OP_MAKE_DIR:
    case RFS_OP_PUT_FILE:
        /* These would touch NV/EFS protected state. Refuse with EPERM. */
        return -13;  /* -EPERM */
    default:
        /* Read-only or unknown/unsupported ops: ENOSYS (not supported here). */
        return -38;  /* -ENOSYS */
    }
}

const char *rfs_op_name(uint8_t op)
{
    switch (op) {
    case RFS_OP_NV_READ:             return "NV_READ";
    case RFS_OP_NV_BUFFERING:        return "NV_BUFFERING";
    case RFS_OP_READ_FILE:           return "READ_FILE";
    case RFS_OP_WRITE_FILE:          return "WRITE_FILE";
    case RFS_OP_LSEEK_FILE:          return "LSEEK_FILE";
    case RFS_OP_CLOSE_FILE:          return "CLOSE_FILE";
    case RFS_OP_PUT_FILE:            return "PUT_FILE";
    case RFS_OP_GET_FILE:            return "GET_FILE";
    case RFS_OP_RENAME_FILE:         return "RENAME_FILE";
    case RFS_OP_GET_FILE_INFO:       return "GET_FILE_INFO";
    case RFS_OP_UNLINK_FILE:         return "UNLINK_FILE";
    case RFS_OP_MAKE_DIR:            return "MAKE_DIR";
    case RFS_OP_OPEN_FILE:           return "OPEN_FILE";
    case RFS_OP_GET_HANDLE_INFO:     return "GET_HANDLE_INFO";
    case RFS_OP_CREATE_FILE:         return "CREATE_FILE";
    case RFS_OP_NV_WRITE_ALL:        return "NV_WRITE_ALL";
    case RFS_OP_NV_BUFFER_START_END: return "NV_BUFFER_START_END";
    case RFS_OP_NV_RESTORE:          return "NV_RESTORE";
    default:                          return "UNKNOWN";
    }
}
