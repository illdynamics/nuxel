/*
 * test_rfs_nv.c — regression tests for the recovered RFS NV transaction
 * contract (rfs_nv.c). Golden assertions encode the byte-exact on-wire
 * contract recovered from the vendor RIL.
 * SPDX-License-Identifier: GPL-2.0-only
 */
#include "rfs_nv.h"
#include <stdio.h>
#include <string.h>

static int failures = 0;
#define CHECK(cond) do { \
    if (!(cond)) { printf("FAIL %s:%d: %s\n", __FILE__, __LINE__, #cond); failures++; } \
    else printf("ok: %s\n", #cond); \
} while (0)

int main(void)
{
    /* --- serialize a 0x168 attach-APN "internet" item record --- */
    {
        const char *apn = "internet";
        size_t alen = strlen(apn);
        uint8_t buf[128];
        memset(buf, 0xAA, sizeof buf);
        size_t n = rfs_nv_item_serialize(0x15 /*NV_WRITE_ALL*/, 0x2b,
                                         0x00012340u /*offset*/,
                                         (uint32_t)alen, (const uint8_t*)apn,
                                         buf, sizeof buf);
        CHECK(n == RFS_NV_HDR_MIN + alen);         /* 14 + 8 = 22 */
        CHECK(buf[0] == 0x15);                     /* op */
        CHECK(buf[1] == 0x2b);                     /* seq */
        CHECK(buf[2] == 0 && buf[3] == 0 && buf[4] == 0 && buf[5] == 0);
        CHECK(buf[6] == 0x40 && buf[7] == 0x23 && buf[8] == 0x01 && buf[9] == 0x00);
        CHECK(buf[10] == 0x08);                    /* length 8 */
        CHECK(memcmp(buf + 14, "internet", 8) == 0);

        /* parse round-trip */
        struct rfs_nv_item it;
        enum rfs_nv_parse_result pr = rfs_nv_item_parse(buf, n, &it);
        CHECK(pr == RFS_NV_PARSE_OK);
        CHECK(it.valid && it.op == 0x15 && it.seq == 0x2b);
        CHECK(it.offset == 0x00012340u && it.length == 8);
        CHECK(it.data && memcmp(it.data, "internet", 8) == 0);
    }

    /* --- parse short buffer -> SHORT --- */
    {
        uint8_t buf[10];
        struct rfs_nv_item it;
        memset(&it, 0, sizeof it);
        CHECK(rfs_nv_item_parse(buf, 10, &it) == RFS_NV_PARSE_SHORT);
        CHECK(!it.valid);
    }

    /* --- parse length overflow -> OVERFLOW --- */
    {
        uint8_t buf[RFS_NV_HDR_MIN];
        memset(buf, 0, sizeof buf);
        buf[0] = 0x15; buf[1] = 1;
        /* claim length 0x80001 (> vendor clamp) */
        buf[10] = 0x01; buf[11] = 0x00; buf[12] = 0x08; buf[13] = 0x00;
        struct rfs_nv_item it;
        memset(&it, 0, sizeof it);
        CHECK(rfs_nv_item_parse(buf, sizeof buf, &it) == RFS_NV_PARSE_OVERFLOW);
    }

    /* --- parse declared length exceeds buffer -> OVERFLOW --- */
    {
        uint8_t buf[RFS_NV_HDR_MIN + 4];
        memset(buf, 0, sizeof buf);
        buf[0] = 0x15; buf[1] = 1;
        buf[10] = 0x20; buf[11] = 0x00; buf[12] = 0x00; buf[13] = 0x00; /* len 32 */
        struct rfs_nv_item it;
        memset(&it, 0, sizeof it);
        CHECK(rfs_nv_item_parse(buf, sizeof buf, &it) == RFS_NV_PARSE_OVERFLOW);
    }

    /* --- NULL data on non-zero length serialize -> 0 --- */
    {
        uint8_t buf[64];
        CHECK(rfs_nv_item_serialize(0x15, 0, 0, 4, NULL, buf, sizeof buf) == 0);
    }

    /* --- response build 15 bytes layout --- */
    {
        uint8_t out[RFS_NV_RESP_LEN];
        memset(out, 0xFF, sizeof out);
        size_t n = rfs_nv_response_build(0x15, 0x2b, 0, 0x00012340u, out);
        CHECK(n == RFS_NV_RESP_LEN);
        CHECK(out[0] == 15);   /* total len */
        CHECK(out[4] == 2);    /* type byte */
        CHECK(out[5] == 0x15); /* op echo */
        CHECK(out[6] == 0x2b); /* seq echo */
        CHECK(out[7] == 0);    /* result success */
        CHECK(out[8] == 0x40 && out[9] == 0x23 && out[10] == 0x01 && out[11] == 0x00);
    }

    /* --- provisioning policy --- */
    {
        uint32_t off = 0, len = 0;
        /* OK: item 360, known offset/length, valid APN */
        enum rfs_nv_provision_decision d = rfs_nv_provision_policy(
            0x168u, false, true, 16u, 0x12340u, "internet", 8, &off, &len);
        CHECK(d == RFS_NV_ALLOW);
        CHECK(off == 0x12340u && len == 8);

        /* unknown item */
        CHECK(rfs_nv_provision_policy(0x169u, false, true, 16u, 0x12340u,
                                      "internet", 8, &off, &len) == RFS_NV_DENY_UNKNOWN_ITEM);
        /* protected */
        CHECK(rfs_nv_provision_policy(0x168u, true, true, 16u, 0x12340u,
                                      "internet", 8, &off, &len) == RFS_NV_DENY_PROTECTED);
        /* no offset */
        CHECK(rfs_nv_provision_policy(0x168u, false, false, 0, 0,
                                      "internet", 8, &off, &len) == RFS_NV_DENY_NO_OFFSET);
        /* length too big */
        CHECK(rfs_nv_provision_policy(0x168u, false, true, 4u, 0x12340u,
                                      "internet", 8, &off, &len) == RFS_NV_DENY_LENGTH);
        /* empty APN */
        CHECK(rfs_nv_provision_policy(0x168u, false, true, 16u, 0x12340u,
                                      "", 0, &off, &len) == RFS_NV_DENY_BADAPN);
        /* oversize APN */
        {
            char big[200]; memset(big, 'a', sizeof big);
            CHECK(rfs_nv_provision_policy(0x168u, false, true, 256u, 0x12340u,
                                          big, 128, &off, &len) == RFS_NV_DENY_BADAPN);
        }
        /* embedded NUL */
        CHECK(rfs_nv_provision_policy(0x168u, false, true, 16u, 0x12340u,
                                      "inter\0net", 10, &off, &len) == RFS_NV_DENY_BADAPN);
    }

    if (failures) { printf("\n%d FAILURES\n", failures); return 1; }
    printf("\nALL test_rfs_nv PASS\n");
    return 0;
}
