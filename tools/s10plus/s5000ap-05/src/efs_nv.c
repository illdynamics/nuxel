/*
 * efs_nv.c — native Nuxel NV storage backend (bounded, fail-closed).
 * SPDX-License-Identifier: GPL-2.0-only
 *
 * See efs_nv.h for the recovered contract. This file reuses the proven MD5
 * from nv_items.c (nv_md5_hex / nv_md5_verify, RFC 1321) rather than
 * duplicating it, and performs the bounded lseek/read/write/fsync that the
 * vendor `Nv::ProcessNvRead`/`ProcessNvWrite` apply.
 */
#include "efs_nv.h"
#include "nv_items.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <fcntl.h>
#include <sys/stat.h>
#include <sys/types.h>

int efs_nv_md5_hex(const uint8_t *data, size_t len, char out[EFS_NV_MD5_HEX])
{
    return nv_vendor_md5_hex(data, len, out);
}

int efs_nv_md5_verify(const uint8_t *data, size_t len, const char *stored_hex)
{
    if (!stored_hex || strlen(stored_hex) != 32) return -1;
    char actual[EFS_NV_MD5_HEX];
    if (efs_nv_md5_hex(data, len, actual)) return -1;
    for (size_t i = 0; i < 32; i++) {
        char c = stored_hex[i];
        if (c >= 'A' && c <= 'F') c = (char)(c + ('a'-'A'));
        if (!((c >= '0' && c <= '9') || (c >= 'a' && c <= 'f'))) return -1;
        if (c != actual[i]) return 1;
    }
    return 0;
}

enum efs_nv_result efs_nv_read_at(int fd, uint32_t offset, uint32_t length,
                                  uint64_t file_size, uint8_t *out)
{
    ssize_t got, want;
    if (fd < 0 || !out) return EFS_NV_BADARG;
    if ((uint64_t)offset + (uint64_t)length > file_size) return EFS_NV_OVERFLOW;
    if (lseek(fd, (off_t)offset, SEEK_SET) < 0) return EFS_NV_SEEK;
    want = (ssize_t)length;
    got = 0;
    while (got < want) {
        ssize_t r = read(fd, out + got, (size_t)(want - got));
        if (r < 0) return EFS_NV_IO;
        if (r == 0) break;
        got += r;
    }
    if (got != want) return EFS_NV_SHORT_READ;
    return EFS_NV_OK;
}

enum efs_nv_result efs_nv_write_at(int fd, uint32_t offset, uint32_t length,
                                   uint64_t file_size, const uint8_t *data,
                                   bool allow_write)
{
    ssize_t got, want;
    if (fd < 0 || !data) return EFS_NV_BADARG;
    if (!allow_write) return EFS_NV_AUTH_DENY;
    if ((uint64_t)offset + (uint64_t)length > file_size) return EFS_NV_OVERFLOW;
    if (lseek(fd, (off_t)offset, SEEK_SET) < 0) return EFS_NV_SEEK;
    want = (ssize_t)length;
    got = 0;
    while (got < want) {
        ssize_t w = write(fd, data + got, (size_t)(want - got));
        if (w < 0) return EFS_NV_IO;
        if (w == 0) break;
        got += w;
    }
    if (got != want) return EFS_NV_SHORT_WRITE;
    if (fsync(fd) != 0) return EFS_NV_IO;
    return EFS_NV_OK;
}

enum efs_nv_result efs_nv_update_checksum_sidecar(const char *image_path,
                                                  const char *md5_path)
{
    uint8_t *buf = NULL;
    char md5[EFS_NV_MD5_HEX];
    FILE *f = NULL;
    struct stat st;
    int fd = -1;
    ssize_t total = 0;
    size_t want;

    if (!image_path || !md5_path) return EFS_NV_BADARG;
    fd = open(image_path, O_RDONLY | O_CLOEXEC);
    if (fd < 0) return EFS_NV_IO;
    if (fstat(fd, &st) != 0 || st.st_size < 0) { close(fd); return EFS_NV_IO; }
    if ((uint64_t)st.st_size > (64u << 20)) { close(fd); return EFS_NV_OVERFLOW; }
    want = (size_t)st.st_size;
    buf = malloc(want ? want : 1u);
    if (!buf) { close(fd); return EFS_NV_IO; }
    while (total < (ssize_t)want) {
        ssize_t r = read(fd, buf + total, want - (size_t)total);
        if (r < 0) { free(buf); close(fd); return EFS_NV_IO; }
        if (r == 0) break;
        total += r;
    }
    close(fd);
    if (total != (ssize_t)want) { free(buf); return EFS_NV_SHORT_READ; }

    if (efs_nv_md5_hex(buf, want, md5) != 0) { free(buf); return EFS_NV_IO; }
    free(buf);

    f = fopen(md5_path, "w");
    if (!f) return EFS_NV_IO;
    if (fwrite(md5, 1, 32, f) != 32) { fclose(f); return EFS_NV_IO; }
    if (fclose(f) != 0) return EFS_NV_IO;
    return EFS_NV_OK;
}
