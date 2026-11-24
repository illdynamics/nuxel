/*
 * test_efs_nv.c — regression tests for the native EFS NV storage backend.
 * Golden assertions encode the bounded read/write + MD5 sidecar contract
 * recovered from the vendor Nv class (round-40 independent disassembly).
 * SPDX-License-Identifier: GPL-2.0-only
 */
#include "efs_nv.h"
#include "nv_items.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <fcntl.h>
#include <sys/stat.h>

static int failures = 0;
#define CHECK(cond) do { \
    if (!(cond)) { printf("FAIL %s:%d: %s\n", __FILE__, __LINE__, #cond); failures++; } \
    else printf("ok: %s\n", #cond); \
} while (0)

static int make_tmp(uint8_t **out, size_t *sz)
{
    char tmpl[] = "/tmp/nuxel_efsnv_XXXXXX";
    int fd = mkstemp(tmpl);
    if (fd < 0) return -1;
    unlink(tmpl);
    *sz = 0x80000;
    if (ftruncate(fd, (off_t)*sz) != 0) { close(fd); return -1; }
    *out = malloc(*sz);
    if (!*out) { close(fd); return -1; }
    memset(*out, 0xCC, *sz);
    return fd;
}

int main(void)
{
    /* --- MD5 correctness (RFC 1321 vectors) --- */
    {
        char h[33];
        efs_nv_md5_hex((const uint8_t*)"", 0, h);
        CHECK(strcmp(h, "d41d8cd98f00b204e9800998ecf8427e") == 0);
        efs_nv_md5_hex((const uint8_t*)"abc", 3, h);
        CHECK(strcmp(h, "900150983cd24fb0d6963f7d28e17f72") == 0);
        CHECK(efs_nv_md5_verify((const uint8_t*)"abc", 3, "900150983cd24fb0d6963f7d28e17f72") == 0);
        CHECK(efs_nv_md5_verify((const uint8_t*)"abc", 3, "00000000000000000000000000000000") == 1);
        CHECK(efs_nv_md5_verify((const uint8_t*)"abc", 3, "zzz") == -1);
    }

    /* --- bounded write + read round-trip at CP-supplied offset --- */
    {
        uint8_t *img; size_t sz = 0;
        int fd = make_tmp(&img, &sz);
        CHECK(fd >= 0);
        const uint8_t apn[8] = { 'i','n','t','e','r','n','e','t' };
        /* Write "internet" at offset 0x1234, length 8 */
        CHECK(efs_nv_write_at(fd, 0x1234u, 8u, sz, apn, true) == EFS_NV_OK);
        uint8_t back[16];
        memset(back, 0, sizeof back);
        CHECK(efs_nv_read_at(fd, 0x1234u, 8u, sz, back) == EFS_NV_OK);
        CHECK(memcmp(back, "internet", 8) == 0);

        /* offset+length > file_size -> OVERFLOW */
        CHECK(efs_nv_read_at(fd, 0x7fffeu, 8u, sz, back) == EFS_NV_OVERFLOW);
        /* write without allow_write -> AUTH_DENY */
        CHECK(efs_nv_write_at(fd, 0x1234u, 8u, sz, apn, false) == EFS_NV_AUTH_DENY);
        /* write overflow */
        CHECK(efs_nv_write_at(fd, 0x7ffffu, 2u, sz, apn, true) == EFS_NV_OVERFLOW);
        close(fd); free(img);
    }

    /* --- MD5 sidecar recompute matches a known value --- */
    {
        /* write a known image, compute sidecar, verify it round-trips */
        const char *path = "/tmp/nuxel_efsnv_img.bin";
        const char *md5p = "/tmp/nuxel_efsnv_img.bin.md5";
        FILE *f = fopen(path, "wb");
        CHECK(f != NULL);
        const uint8_t data[8] = { 'i','n','t','e','r','n','e','t' };
        CHECK(fwrite(data, 1, sizeof data, f) == sizeof data);
        fclose(f);
        CHECK(efs_nv_update_checksum_sidecar(path, md5p) == EFS_NV_OK);
        /* read back sidecar and verify against an independently computed MD5 */
        char hex[33];
        efs_nv_md5_hex(data, sizeof data, hex);
        FILE *m = fopen(md5p, "r");
        char stored[33] = {0};
        CHECK(m != NULL);
        CHECK(fread(stored, 1, 32, m) == 32);
        fclose(m);
        CHECK(memcmp(stored, hex, 32) == 0);
        unlink(path); unlink(md5p);
    }

    if (failures) { printf("\n%d FAILURES\n", failures); return 1; }
    printf("\nALL test_efs_nv PASS\n");
    return 0;
}
