/*
 * rfs_nv.h — S5000AP RFS NV (persistent NV/EFS) transaction contract.
 * SPDX-License-Identifier: GPL-2.0-only
 *
 * This module implements the AP-side of the S5000AP RFS NV protocol. It is a
 * PURE serializer/deserializer + policy engine (no I/O); the caller (radiod)
 * performs the actual bounded lseek/write/fsync against a user-supplied
 * nv_data.bin image and the /dev/umts_rfs0 response write.
 *
 * RECOVERED CONTRACT (independent AArch64 disassembly of the exact vendor RIL
 * .vendor-ro/libsec-ril.so, build 60889dd714394ae0db7c2ecc2bf2740f — the same
 * binary fingerprinted by Stage-05/06 rounds):
 *
 *  1. CP->AP RFS request envelope (channel 245 IPC_RFS, format=2):
 *       [u32 total_len LE][u8 op][u8 seq][u32 param][path+'\0' ...]
 *     Opcodes 0x01..0x17 (see rfs_respond.h): NV_READ, NV_BUFFERING,
 *     READ/WRITE/LSEEK/CLOSE_FILE, PUT/GET_FILE, RENAME, GET_FILE_INFO,
 *     UNLINK(0x0b), MAKE_DIR, OPEN(0x11), GET_HANDLE_INFO(0x13),
 *     CREATE(0x14), NV_WRITE_ALL(0x15), NV_BUFFER_START_END(0x16),
 *     NV_RESTORE(0x17).
 *
 *  2. AP->CP RFS response envelope (from Nv::ProcessNvWrite tailepiece):
 *       [u32 total_len][u8 type][u8 op_echo][u8 result][u32 detail]
 *     total_len = result-frame byte count (RECOVERED: 15 for NV write),
 *     type = 2 (format/type byte), op_echo = request byte offset 5,
 *     result = 0 (success) / 1 (failure), detail = echoed u32 (offset
 *     written on success, bytes written / errno on failure).
 *
 *  3. NV write item record (the payload Nv::ProcessNvWrite dereferences at
 *     its +896 member; the SAME record bytes are what the CP streams for an
 *     NV_WRITE / NV_WRITE_ALL operation):
 *       [u8 op][u8 seq][u32 mode/reserved][u32 offset][u32 length][data...]
 *     - byte 4      = read-mode sentinel (ProcessNVRead: `ldrb w8,[x28,#4]`
 *                     must equal 1 for a read; write path ignores it).
 *     - offset (LE) = byte offset INTO nv_data.bin where the value lives
 *                     (ProcessNvWrite/ProcessNVRead `ldur w20/w21,[x28,#6]`).
 *     - length (LE) = byte length of the value (clamped to 0x80000;
 *                     `ldur w8,[x28,#10]`).
 *     - data         = the item value bytes (length bytes).
 *     This is the ONLY authorization the CP gives for a specific item's
 *     physical location; we never invent an offset.
 *
 *  4. Storage write semantics (Nv::ProcessNvWrite @0x1d8550, VERIFIED):
 *       open("/mnt/vendor/efs/nv_data.bin", O_RDWR);
 *       lseek(fd, offset, SEEK_SET);
 *       write(fd, data, length);
 *       fsync(fd);
 *       close(fd);
 *       UpdateChecksumFile()  ->  recompute MD5 == "<file>.md5" (32 ASCII hex).
 *     A single MD5 checksum guards the whole nv_data.bin. There is NO
 *     asymmetric signature in this path (round-38 correction).
 *
 * SAFETY CONTRACT (fail-closed):
 *   - This module NEVER fabricates an offset/length/value. A write is only
 *     serializable for an EXPLICIT (offset,length,data) triple supplied by
 *     the CP, or — for the AP-originated provisioning path — only after an
 *     authenticated CP-originated NV_READ returned that same item's offset
 *     and length.
 *   - NV item id 360 == 0x168 (NASU.LTE.ATTACH.APN.INFO) is the ONLY item the
 *     provisioning policy may target, and ONLY to set the owner-approved APN.
 *   - Protected RF/calibration/IMEI/keys items are deny-classified and can
 *     never reach the serialization path.
 */
#ifndef NUXEL_RFS_NV_H
#define NUXEL_RFS_NV_H

#include <stdint.h>
#include <stddef.h>
#include <stdbool.h>

#ifdef __cplusplus
extern "C" {
#endif

#define RFS_NV_HDR_MIN      14u    /* op+seq+u32reserved+u32offset+u32length */
#define RFS_NV_OFFSET_FIELD  6u    /* offset u32 at record+6 */
#define RFS_NV_LENGTH_FIELD 10u    /* length u32 at record+10 */
#define RFS_NV_DATA_FIELD   14u    /* value bytes at record+14 */
#define RFS_NV_MAX_VALUE     (0x80000u)  /* vendor clamps value to 512 KiB */
#define RFS_NV_RESP_LEN      15u    /* recovered response length for NV ops */

/* RFS NV item-id constants (recovered; qbr_items.h duplicates for dict use). */
#define RFS_NV_ITEM_ATTACH_APN_ID 0x168u  /* 360 */

/* A fully-decoded NV write/read item transaction record. */
struct rfs_nv_item {
    uint8_t  op;          /* RFS opcode (echoed back verbatim) */
    uint8_t  seq;         /* correlation byte (echoed back verbatim) */
    uint32_t offset;      /* byte offset into nv_data.bin */
    uint32_t length;      /* value byte length (<= RFS_NV_MAX_VALUE) */
    const uint8_t *data;  /* value bytes (borrowed; NOT owned) */
    bool     valid;
};

/* Result of parsing an NV item record. */
enum rfs_nv_parse_result {
    RFS_NV_PARSE_OK = 0,
    RFS_NV_PARSE_SHORT = -1,      /* < RFS_NV_HDR_MIN bytes */
    RFS_NV_PARSE_OVERFLOW = -2,   /* length > RFS_NV_MAX_VALUE or OOB */
    RFS_NV_PARSE_BADARG = -3,     /* NULL/empty args */
};

/* Provisioning decision for an AP-originated NV write request. */
enum rfs_nv_provision_decision {
    RFS_NV_ALLOW = 0,
    RFS_NV_DENY_UNKNOWN_ITEM = -1,   /* numeric item id not recovered */
    RFS_NV_DENY_PROTECTED   = -2,    /* RF/cal/IMEI/keys */
    RFS_NV_DENY_NO_OFFSET   = -3,    /* no authenticated offset/length yet */
    RFS_NV_DENY_LENGTH      = -4,    /* length exceeds authenticated length */
    RFS_NV_DENY_BADAPN      = -5,    /* APN empty/oversize/invalid */
};

/*
 * Parse a CP-originated NV item record from buf[0..len) into *out.
 * Pure; never reads past len. `data` points into buf (borrowed).
 * Returns RFS_NV_PARSE_OK (out populated) or a negative error.
 */
enum rfs_nv_parse_result rfs_nv_item_parse(const uint8_t *buf, size_t len,
                                           struct rfs_nv_item *out);

/*
 * Serialize an NV item record into out[0..cap). Returns bytes written
 * (>= RFS_NV_HDR_MIN) on success, 0 on failure. `data` may be NULL when
 * length==0. Cap is the caller buffer size. Pure.
 */
size_t rfs_nv_item_serialize(uint8_t op, uint8_t seq, uint32_t offset,
                             uint32_t length, const uint8_t *data,
                             uint8_t *out, size_t cap);

/*
 * Build the AP->CP NV response envelope (recovered; ProcessNvWrite @0x1d8920).
 * WRITE response (type byte 2) is EXACTLY 15 bytes:
 *   [u32 total_len=15][u8 type=2][u8 seq][u8 result][u32 offset][u32 written]
 * RECOVERED (round-40 independent disassembly): the 3 bytes after total_len
 * are type, SEQUENCE (not op), and result; then two u32 detail words
 * (offset, bytes_written). Previous rounds had op@+5/seq@+6, which is WRONG.
 * `seq` is echoed at +5; `result` at +6; `detail` (offset) at +7; `written`
 * at +11. Returns RFS_NV_RESP_LEN or 0.
 */
size_t rfs_nv_response_build(uint8_t seq, uint8_t result,
                             uint32_t offset, uint32_t written,
                             uint8_t out[RFS_NV_RESP_LEN]);

/*
 * Build the AP->CP NV READ response envelope (recovered; ProcessNVRead
 * @0x1d8c2c). READ uses type byte 1 and APPENDS the read-back data:
 *   [u32 total_len=15+bytes][u8 type=1][u8 seq][u8 result]
 *   [u32 offset][u32 bytes][data...]
 * Returns total bytes written (>=15) into out[0..cap), or 0 on overflow.
 * Pure; never reads past data_len. cap must be >= 15+bytes.
 */
size_t rfs_nv_read_response_build(uint8_t seq, uint8_t result,
                                  uint32_t offset, uint32_t bytes,
                                  const uint8_t *data,
                                  uint8_t *out, size_t cap);

/*
 * Decide whether an AP-originated provisioning write for the given item id
 * and validated APN record may proceed.
 *   item_id       : numeric NV item id (RFS_NV_ITEM_ATTACH_APN_ID == 360)
 *   item_protected: whether the id is RF/cal/IMEI/keys
 *   have_offset   : an authenticated (offset,length) has been read back
 *   length_limit  : the authenticated value length (0 if have_offset false)
 *   apn, apn_len  : the APN value to write (must be 1..127, no embedded NUL)
 * On success out_offset/out_length are set to the authenticated (offset,
 * apn_len) to write. Returns an rfs_nv_provision_decision. Pure.
 */
enum rfs_nv_provision_decision rfs_nv_provision_policy(
    uint32_t item_id, bool item_protected, bool have_offset,
    uint32_t length_limit, uint32_t authenticated_offset,
    const char *apn, size_t apn_len,
    uint32_t *out_offset, uint32_t *out_length);

#ifdef __cplusplus
}
#endif
#endif /* NUXEL_RFS_NV_H */
