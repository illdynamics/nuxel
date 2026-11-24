/*
 * test_nv_items.c — unit tests for the recovered CP-NV record decoder + MD5
 * integrity + fail-closed provisioning policy. GPL-2.0-only.
 *
 * Golden vectors are taken VERBATIM from the physical CP EFS snapshot recovered
 * from the live SM-G975F (cpefs .nv_core.bak / efs nv_data.bin), see
 * reports/S5000AP-06-ROUND37-NV-PROVISIONING.md.
 */
#include "nv_items.h"

#include <stdio.h>
#include <string.h>

static int failures = 0;
#define CHECK(cond, name) do { \
    if (!(cond)) { printf("FAIL: %s (%s:%d)\n", name, __FILE__, __LINE__); failures++; } \
    else { printf("ok: %s\n", name); } \
} while (0)

static const uint8_t rec_scalar[24] = {
    /* size=0x18? no — use real header + 4 payload bytes */
    0x18,0x00,0x00,0x00,  /* size = 24 */
    0xbf,0xd5,0x60,0x41,  /* name_ptr = 0x4160d5bf */
    0x04,0x00,0x00,0x00,  /* type = 0x04 (scalar item) */
    0xcf,0x19,0x77,0x41,  /* aux_ptr = 0x417719cf */
    0xde,0xad,0xbe,0xef,  /* payload 4 bytes */
    0x00,0x00,0x00,0x00
};

static const uint8_t rec_guard[24] = {
    0x18,0x00,0x00,0x00,
    0x2d,0xbb,0x60,0x41,  /* 0x4160bb2d */
    0x05,0x00,0x00,0x00,  /* guard type */
    0x00,0x00,0x00,0x00,  /* aux 0 */
    0xaa,0xaa,0xaa,0xaa,
    0x00,0x00,0x00,0x00
};

int main(void)
{
    struct nv_record r;

    /* 1. valid scalar record */
    size_t used = nv_record_parse(rec_scalar, sizeof rec_scalar, &r);
    CHECK(used == 24, "scalar record size");
    CHECK(r.size == 24, "scalar size field");
    CHECK(r.name_ptr == 0x4160d5bfu, "scalar name_ptr");
    CHECK(r.type == NV_TYPE_ITEM, "scalar type");
    CHECK(r.aux_ptr == 0x417719cfu, "scalar aux_ptr");
    CHECK(r.size_valid, "scalar size_valid");
    CHECK(r.name_is_ram, "scalar name_is_ram");
    CHECK(strcmp(nv_name_ptr_span(0x4160d5bfu), "CP-RAM/data") == 0, "name span");

    /* 2. guard record */
    used = nv_record_parse(rec_guard, sizeof rec_guard, &r);
    CHECK(used == 24, "guard record size");
    CHECK(r.type == NV_TYPE_GUARD, "guard type");
    CHECK(r.aux_ptr == 0, "guard aux zero");

    /* 3. truncated buffer fails closed */
    CHECK(nv_record_parse(rec_scalar, 8, &r) == 0, "short buffer -> 0");

    /* 4. size larger than buffer fails closed */
    {
        uint8_t big_hdr[16] = { 0x00,0x04,0x00,0x00, 0,0,0,0, 0,0,0,0, 0,0,0,0 };
        big_hdr[0] = 0x00; big_hdr[1] = 0x04; /* size=0x400 */
        CHECK(nv_record_parse(big_hdr, sizeof big_hdr, &r) == 0, "size>len -> 0");
    }

    /* 5. name_ptr in text (0x40fcxxxx) still classified RAM-ish */
    CHECK(strcmp(nv_name_ptr_span(0x40fc3fa9u), "CP-text/rodata") == 0, "text span");
    CHECK(strcmp(nv_name_ptr_span(0x47800000u), "CP-VSS") == 0, "vss span");
    CHECK(strcmp(nv_name_ptr_span(0x12345678u), "unknown") == 0, "unknown span");

    /* 6. MD5 known-answer test (RFC 1321): md5("") = d41d8cd98f00b204e9800998ecf8427e */
    {
        char out[33];
        CHECK(nv_md5_hex((const uint8_t*)"", 0, out) == 0, "md5 empty rc");
        CHECK(strcmp(out, "d41d8cd98f00b204e9800998ecf8427e") == 0, "md5 empty vector");

        /* md5("abc") = 900150983cd24fb0d6963f7d28e17f72 */
        CHECK(nv_md5_hex((const uint8_t*)"abc", 3, out) == 0, "md5 abc rc");
        CHECK(strcmp(out, "900150983cd24fb0d6963f7d28e17f72") == 0, "md5 abc vector");
    }

    /* 7. MD5 verify: match / mismatch / malformed */
    {
        const uint8_t *d = (const uint8_t*)"abc";
        CHECK(nv_md5_verify(d, 3, "900150983cd24fb0d6963f7d28e17f72") == 0, "verify match");
        CHECK(nv_md5_verify(d, 3, "00000000000000000000000000000000") == 1, "verify mismatch");
        CHECK(nv_md5_verify(d, 3, "zzzz") == -1, "verify malformed");
    }

    /* 8. provisioning policy */
    CHECK(nv_provision_policy(false, false, false, false) == NV_PROV_ALLOW_BACKUP_READ, "read allowed");
    CHECK(nv_provision_policy(true, false, false, true) == NV_PROV_DENY_UNKNOWN_ID, "write unknown id");
    CHECK(nv_provision_policy(true, true, true, true) == NV_PROV_DENY_PROTECTED, "write protected");
    CHECK(nv_provision_policy(true, true, false, false) == NV_PROV_DENY_MD5_MISMATCH, "write bad md5");
    CHECK(nv_provision_policy(true, true, false, true) == NV_PROV_ALLOW_BACKUP_READ, "write known+ok");

    /* 9. Round-38: recovered initial-attach APN item contract. */
    CHECK(NV_ATTACH_APN_ITEM_ID == 0x168u, "attach APN NV item id == 360");
    {
        struct nv_apn_record rec;
        CHECK(nv_apn_record_init(&rec, "internet", 8) == 0, "apn record init rc");
        CHECK(rec.valid, "apn record valid");
        CHECK(rec.apn_len == 8, "apn length 8");
        CHECK(strcmp((const char *)rec.apn, "internet") == 0, "apn bytes == internet");

        /* fail-closed: empty / oversize / NULL */
        CHECK(nv_apn_record_init(&rec, "", 0) == -1, "empty apn rejected");
        CHECK(nv_apn_record_init(&rec, NULL, 8) == -1, "NULL apn rejected");
        {
            char big[200];
            memset(big, 'a', sizeof big);
            CHECK(nv_apn_record_init(&rec, big, 200) == -1, "oversize apn rejected");
        }
        CHECK(nv_apn_record_init(&rec, "internet", 0) == -1, "zero-length rejected");
    }

    if (failures == 0) {
        printf("\nALL test_nv_items PASS\n");
        return 0;
    }
    printf("\n%d test_nv_items FAILURES\n", failures);
    return 1;
}
