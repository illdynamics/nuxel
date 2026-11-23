/*
 * rfs_respond.h — S5000AP RFS (Remote File System) responder contract.
 * SPDX-License-Identifier: GPL-2.0-only
 *
 * This module implements the SOURCE-BACKED RFS request/response contract
 * recovered from the exact vendor RIL (SM-G975F / EFUJ2, lib64/libsec-ril.so
 * GNU Build ID 60889dd714394ae0db7c2ecc2bf2740f), analysed read-only on the
 * SM-G975F device with binutils (objdump/readelf/strings/nm). This is the
 * SAME binary fingerprinted by prior Stage-05/06 rounds.
 *
 * RECOVERED RFS contract (see reports/S5000AP-06-LTE-REAL-LIVE.md §RFS):
 *
 *   Channel:   SIPC5_CH_ID_RFS_0 = 245 (0xF5), /dev/umts_rfs0, format=2 (RFS).
 *   Request (CP->AP):
 *       [u32 total_len LE][u8 op][u8 seq][u32 param][path+'\0']
 *       - total_len counts the WHOLE record including the 4-byte length field.
 *       - op             = RFS operation code (1..23).
 *       - seq            = sequence / correlation byte (echoed verbatim).
 *       - param          = op-specific 32-bit word at offset 6. For
 *                          RFS_UNLINK_FILE (and file ops carrying a path) this
 *                          is path_len (length INCLUDING the trailing NUL).
 *                          For RFS_OPEN/CLOSE/LSEEK it is an fd/handle/offset.
 *       - path           = starts at offset 10 (when param is path_len). For
 *                          op RFS_UNLINK_FILE the CP sends the special boot-time
 *                          marker "DELETE_ALL_VIS" (delete the modem VIG/VIS
 *                          visualizer cache, NOT protected NV).
 *   Response (AP->CP) = EXACTLY 14 bytes, written to /dev/umts_rfs0:
 *       [u32 result  ][u8 op echo][u8 seq echo][u16 reserved][u32 detail]
 *       - result  : 0 = success, else errno-style negative value.
 *       - op      : echo of the request op byte.
 *       - seq     : echo of the request seq byte.
 *       - reserved: zero.
 *       - detail  : 0 on success; errno or -1 on failure (for open: an fd).
 *
 *   OPCODE MAP (recovered from Nv::ProcessRfsMessage jump table + handler
 *   `[x24,#4] == op` checks + NvLog emitters, in libsec-ril.so):
 *
 *      0x01 RFS_NV_READ           (Nv::ProcessNVRead)
 *      0x02 RFS_NV_BUFFERING      (Nv::ProcessNvBuffering)  [guarded]
 *      0x03 RFS_READ_FILE         (Nv::ProcessReadFile)
 *      0x04 RFS_WRITE_FILE        (Nv::ProcessWriteFile)
 *      0x05 RFS_LSEEK_FILE        (Nv::ProcessLseekFile)
 *      0x06 RFS_CLOSE_FILE        (Nv::ProcessCloseFile          - op==0x06)
 *      0x07 RFS_PUT_FILE          (Nv::ProcessPutFile)
 *      0x08 RFS_GET_FILE          (Nv::ProcessGetFile)
 *      0x09 RFS_RENAME_FILE       (Nv::ProcessRenameFile)
 *      0x0a RFS_GET_FILE_INFO     (Nv::ProcessGetFileInfo)
 *      0x0b RFS_UNLINK_FILE       (Nv::ProcessDeleteFile          - op==0x0b)
 *      0x0c RFS_MAKE_DIR          (Nv::ProcessMakeDirectory)
 *      0x0d..0x10 (reserved / unsupported)
 *      0x11 RFS_OPEN_FILE         (Nv::ProcessOpenFile)
 *      0x12 (reserved / unsupported)
 *      0x13 RFS_GET_HANDLE_INFO   (Nv::ProcessGetFileInfoByHandle)
 *      0x14 RFS_CREATE_FILE       (Nv::ProcessCreateFile)
 *      0x15 RFS_NV_WRITE_ALL      (Nv::ProcessNVWriteAll)
 *      0x16 RFS_NV_BUFFER_START_END (Nv::ProcessNVBufferStartEnd)
 *      0x17 RFS_NV_RESTORE        (Nv::ProcessNVRestore)
 *
 * SAFETY / POLICY (this daemon is fail-closed by default):
 *   - We NEVER execute a real filesystem operation against protected NV/EFS
 *     paths. The ONLY operation we answer with success is the boot-stage
 *     RFS_UNLINK_FILE("DELETE_ALL_VIS") cleanup marker, which is a cache-delete
 *     of non-existent VIG/VIS artfacts on a filesystem we do not mount
 *     (no side effect). Every other op is answered with a fail-closed error
 *     response (result = -EPERM / -ENOSYS), never a fabricated success.
 *   - We never open/read/write /mnt/vendor/efs, /efs, NV, calibration, IMEI,
 *     keys, or any protected prefix.
 *   - Responses are bounded to 14 bytes; sequence is echoed, never incremented
 *     speculatively; unknown ops are rejected; timeouts are bounded.
 */
#ifndef NUXEL_RFS_RESPOND_H
#define NUXEL_RFS_RESPOND_H

#include <stdint.h>
#include <stddef.h>
#include <stdbool.h>

#ifdef __cplusplus
extern "C" {
#endif

/* RFS operation codes (recovered; source-backed). */
enum rfs_op {
    RFS_OP_NV_READ            = 0x01,
    RFS_OP_NV_BUFFERING       = 0x02,
    RFS_OP_READ_FILE          = 0x03,
    RFS_OP_WRITE_FILE         = 0x04,
    RFS_OP_LSEEK_FILE         = 0x05,
    RFS_OP_CLOSE_FILE         = 0x06,
    RFS_OP_PUT_FILE           = 0x07,
    RFS_OP_GET_FILE           = 0x08,
    RFS_OP_RENAME_FILE        = 0x09,
    RFS_OP_GET_FILE_INFO      = 0x0a,
    RFS_OP_UNLINK_FILE        = 0x0b,  /* == "DELETE_ALL_VIS" boot marker */
    RFS_OP_MAKE_DIR           = 0x0c,
    /* 0x0d..0x10 reserved */
    RFS_OP_OPEN_FILE          = 0x11,
    /* 0x12 reserved */
    RFS_OP_GET_HANDLE_INFO    = 0x13,
    RFS_OP_CREATE_FILE        = 0x14,
    RFS_OP_NV_WRITE_ALL       = 0x15,
    RFS_OP_NV_BUFFER_START_END= 0x16,
    RFS_OP_NV_RESTORE         = 0x17,
};

#define RFS_REQ_HDR_MIN   10u   /* [u32 len][u8 op][u8 seq][u32 param], path at +10 */
#define RFS_RESP_LEN      14u   /* fixed response record length */
#define RFS_MAX_PATH      512u

/* A fully-parsed RFS request. */
struct rfs_request {
    uint32_t total_len;      /* declared total length (incl 4-byte length word) */
    uint8_t  op;             /* RFS operation code */
    uint8_t  seq;            /* sequence/correlation byte */
    uint32_t param;          /* offset 6..9: op-specific u32 (path_len / fd / off) */
    uint32_t path_len;       /* = param when param is a path length */
    char     path[RFS_MAX_PATH]; /* NUL-terminated printable path (starts at +10) */
    bool     path_valid;     /* path fully printable ASCII */
    bool     special_delete_all_vis; /* op==UNLINK_FILE && path=="DELETE_ALL_VIS" */
};

/* Result of parsing an RFS request. */
enum rfs_request_parse_result {
    RFS_REQ_OK = 0,
    RFS_REQ_SHORT = -1,          /* < RFS_REQ_HDR_MIN bytes */
    RFS_REQ_LEN_MISMATCH = -2,   /* declared length impossible/non-printable path */
    RFS_REQ_OVERFLOW = -3,       /* declared length exceeds sane bounds */
};

/*
 * Parse an RFS request from buf/len. Pure (no I/O). On RFS_REQ_OK, `out`
 * is fully populated. On any negative result, `out` must not be used.
 */
enum rfs_request_parse_result rfs_request_parse(const uint8_t *buf, size_t len,
                                                struct rfs_request *out);

/*
 * Build a 14-byte RFS response for the given (op, seq, result, detail).
 * `op` and `seq` are echoed; `result` is 0 (OK) or a negative errno-style code;
 * `detail` is 0 on success, or an errno/fd - see header contract. Returns the
 * number of bytes written (RFS_RESP_LEN) or 0 if out is NULL/small.
 */
size_t rfs_response_build(uint8_t op, uint8_t seq, int32_t result, int32_t detail,
                          uint8_t out[RFS_RESP_LEN]);

/*
 * Decide the RESPONSE POLICY for a parsed request. This is the fail-closed
 * gate: only the non-destructive, no-op-able boot marker is answered with
 * success; everything else is answered with a fail-closed error. This module
 * never performs filesystem I/O — the caller only writes the returned response.
 *
 * Returns 0 (success) for the approved no-op, or a negative errno-style code.
 * Also sets *detail (0/errno). Never returns a fabricated success for a real
 * filesystem op.
 */
int rfs_response_policy(const struct rfs_request *req, int32_t *detail);

/* Human-readable RFS op name (for diagnostics; never logs the path). */
const char *rfs_op_name(uint8_t op);

#ifdef __cplusplus
}
#endif
#endif /* NUXEL_RFS_RESPOND_H */
