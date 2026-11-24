/*
 * efs_nv.h — native Nuxel NV storage backend (bounded, fail-closed).
 * SPDX-License-Identifier: GPL-2.0-only
 *
 * Round-40 implementation. This replaces the vendor `cbd` NV serving on the
 * AP side: it applies the SAME byte contract as `Nv::ProcessNVRead` (@0x1d8a10)
 * and `Nv::ProcessNvWrite` (@0x1d8550) in the vendor RIL, but as clean native
 * Linux code with NO Android/Bionic dependency.
 *
 * The caller supplies an already-open file descriptor to nv_data.bin (or a
 * temp/test image). This module performs bounded lseek/read/write/fsync and
 * the MD5 sidecar recompute that the vendor `Nv::UpdateChecksumFile` applies.
 * It NEVER fabricates an offset/length/value; offset+length are ALWAYS supplied
 * by the CP-originated RFS request (verified by independent disassembly: the
 * AP does not compute item offsets — the CP sends them).
 *
 * SAFETY:
 *   - offset+length are validated against the file size before any I/O.
 *   - length is clamped to RFS_NV_MAX_VALUE (0x80000) exactly like the vendor.
 *   - a write is refused (fail-closed) unless `allow_write` is true AND the
 *     MD5 pre-image verifies (checksum-on), matching `Nv::ProcessNvWrite`.
 *   - no path-name logging, no item-ID logging, no payload logging.
 */
#ifndef NUXEL_EFS_NV_H
#define NUXEL_EFS_NV_H

#include <stdint.h>
#include <stddef.h>
#include <stdbool.h>
#include <sys/types.h>

#ifdef __cplusplus
extern "C" {
#endif

#define EFS_NV_MAX_VALUE 0x80000u   /* vendor 512 KiB clamp */
#define EFS_NV_MD5_HEX   33u

/* Result of an EFS NV I/O operation. */
enum efs_nv_result {
    EFS_NV_OK = 0,
    EFS_NV_BADARG = -1,
    EFS_NV_SHORT_READ = -2,      /* read returned fewer than length bytes */
    EFS_NV_SHORT_WRITE = -3,
    EFS_NV_SEEK = -4,
    EFS_NV_IO = -5,
    EFS_NV_OVERFLOW = -6,        /* offset+length exceeds file size */
    EFS_NV_AUTH_DENY = -7,       /* write refused by policy (no write / md5) */
    EFS_NV_MD5_MISMATCH = -8,    /* stored sidecar did not match pre-image */
};

/*
 * Vendor sidecar checksum: MD5(image || "Samsung_Android_RIL").
 * Writes 32 lowercase hex + NUL into out[33]. Returns 0 on success, -1 on NULL.
 */
int efs_nv_md5_hex(const uint8_t *data, size_t len, char out[EFS_NV_MD5_HEX]);

/*
 * Verify a stored 32-hex MD5 against `data`. Returns 0 (match), 1 (mismatch),
 * -1 (malformed stored hex).
 */
int efs_nv_md5_verify(const uint8_t *data, size_t len, const char *stored_hex);

/*
 * Bounded read of exactly `length` bytes at `offset` into out[0..length).
 * `file_size` is the caller-known nv_data.bin size (fstat). Fails (OVERFLOW)
 * if offset+length > file_size. Returns efs_nv_result.
 */
enum efs_nv_result efs_nv_read_at(int fd, uint32_t offset, uint32_t length,
                                  uint64_t file_size, uint8_t *out);

/*
 * Bounded write of exactly `length` bytes from data at `offset`, then fsync.
 * Fails (OVERFLOW) if offset+length > file_size. Fails (AUTH_DENY) unless
 * allow_write is true. Does NOT recompute the MD5 sidecar here; the caller
 * recomputes it via efs_nv_write_checksum_sidecar after a successful write,
 * exactly like Nv::UpdateChecksumFile (`Nv::ProcessNvWrite` @0x1d8880).
 */
enum efs_nv_result efs_nv_write_at(int fd, uint32_t offset, uint32_t length,
                                   uint64_t file_size, const uint8_t *data,
                                   bool allow_write);

/*
 * Recompute and atomically write the "<image>.md5" sidecar (32 ASCII hex) for
 * `image_path`. This mirrors Nv::UpdateChecksumFile. Reads the whole image,
 * computes the MD5, and writes image_path + ".md5". Returns efs_nv_result.
 * Uses bounded reads (never loads huge images in one go).
 */
enum efs_nv_result efs_nv_update_checksum_sidecar(const char *image_path,
                                                  const char *md5_path);

#ifdef __cplusplus
}
#endif
#endif /* NUXEL_EFS_NV_H */
