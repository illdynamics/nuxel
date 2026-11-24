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
    /* --- Vendor checksum vectors, independently generated with hashlib. --- */
    {
        char h[33];
        efs_nv_md5_hex((const uint8_t*)"", 0, h);
        CHECK(strcmp(h, "2d44b1b4d8b512c006e8dfa559eaad1a") == 0);
        efs_nv_md5_hex((const uint8_t*)"abc", 3, h);
        CHECK(strcmp(h, "8b558dbf8cefc62e27d58a07e9c6ef2b") == 0);
        CHECK(efs_nv_md5_verify((const uint8_t*)"abc", 3, "8b558dbf8cefc62e27d58a07e9c6ef2b") == 0);
        CHECK(efs_nv_md5_verify((const uint8_t*)"abc", 3, "00000000000000000000000000000000") == 1);
        CHECK(efs_nv_md5_verify((const uint8_t*)"abc", 3, "zzz") == -1);
    }

    /* Suffix and MD5 padding straddle both 64-byte block boundaries. */
    {
        static const struct { size_t len; const char *hash; } vectors[] = {
            {36, "e6eaad646c68a9307c398b0c08138bd3"},
            {37, "23eccc74bc08b2e5a19b361c4a21cd6f"},
            {44, "28be8bf85665874bfe5b8791c6358391"},
            {45, "0aed06e9834f4d7a059ea618ca608f8a"},
            {63, "b3cd3b2c12936bc89b3a36aef9d41c61"},
            {64, "7bf43de43eeec29b7ed9e82dc5826f74"},
            {65, "bca7a4970e05d158bce2fe54e4da5d02"},
            {1048576, "7ba6a80d263cbee33643a8e6806fd25c"}
        };
        uint8_t *fixture = malloc(1048576);
        CHECK(fixture != NULL);
        memset(fixture, 0xcc, 1048576);
        for (size_t i=0; i<sizeof vectors / sizeof vectors[0]; i++)
            CHECK(efs_nv_md5_verify(fixture, vectors[i].len, vectors[i].hash) == 0);
        fixture[0] ^= 1;
        CHECK(efs_nv_md5_verify(fixture, 1048576, vectors[7].hash) == 1);
        free(fixture);
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
        CHECK(efs_nv_md5_hex(data, sizeof data, hex) == 0);
        CHECK(strcmp(hex, "ccc0536e0f7561ba76afd12234614dae") == 0);
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
