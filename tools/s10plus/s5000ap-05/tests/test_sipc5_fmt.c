/*
 * test_sipc5_fmt.c — unit tests for sipc5_fmt.c against pinned kernel refs.
 * SPDX-License-Identifier: GPL-2.0-only
 * Build: gcc -I../src -o test_sipc5_fmt test_sipc5_fmt.c ../src/sipc5_fmt.c
 */
#include "sipc5_fmt.h"
#include <stdio.h>
#include <string.h>
#include <stdint.h>

static int failures = 0;
#define CHECK(cond, ...) do { \
    if (!(cond)) { failures++; printf("FAIL %s:%d: ", __FILE__, __LINE__); \
        printf(__VA_ARGS__); printf("\n"); } \
    else { printf("ok   %s:%d: ", __FILE__, __LINE__); \
        printf(__VA_ARGS__); printf("\n"); } \
} while (0)

int main(void)
{
    /* ---- ABI size checks (must match kernel struct sizes) ---- */
    CHECK(sizeof(struct sipc_fmt_hdr) == 7, "sipc_fmt_hdr == 7 (got %zu)",
          sizeof(struct sipc_fmt_hdr));

    /* ---- link header: minimal 4-byte, no ext field ---- */
    {
        u8 h[4] = { 0xF8, 10, 14, 0 }; /* cfg=0xF8 (no ext), ch=PDP0, len=14 */
        struct nuxel_sipc5_link l;
        int r = sipc5_parse_link_header(h, sizeof h, &l);
        CHECK(r == SIPC_PARSE_OK, "min 4-byte hdr parse OK (r=%d)", r);
        CHECK(l.hdr_len == 4, "hdr_len==4 (got %u)", l.hdr_len);
        CHECK(l.frame_len == 14, "frame_len==14 (got %u)", l.frame_len);
        CHECK(l.ch == 10, "ch==10 (got %u)", l.ch);
        CHECK(!l.multi_frame && !l.ext_len && !l.padding_exist,
              "no ext/ctl/padding flags");
    }

    /* ---- link header: multi-frame (ext=0b11 -> ctl field, 5 bytes) ---- */
    {
        u8 h[5] = { 0xFB, 245, 20, 0, 0x81 }; /* cfg 0xFB = start|0x03, RFS ch */
        struct nuxel_sipc5_link l;
        int r = sipc5_parse_link_header(h, sizeof h, &l);
        CHECK(r == SIPC_PARSE_OK, "multi-frame hdr parse OK (r=%d)", r);
        CHECK(l.hdr_len == 5, "hdr_len==5 (got %u)", l.hdr_len);
        CHECK(l.multi_frame, "multi_frame==true");
        CHECK(l.ctrl == 0x81, "ctrl==0x81 (got 0x%02x)", l.ctrl);
        CHECK((l.ctrl & SIPC_MULTI_FRAME_MORE_BIT) != 0, "more-bit set");
        CHECK((l.ctrl & SIPC_MULTI_FRAME_ID_MASK) == 1, "frame-id==1");
        CHECK(l.ch == 245, "RFS ch==245");
    }

    /* ---- link header: ext-length (ext=0b10 -> u32 len, 6 bytes) ---- */
    {
        u8 h[6] = { 0xFA, 235, 0x34, 0x12, 0x00, 0x00 }; /* cfg0xFA=start|0x02 */
        struct nuxel_sipc5_link l;
        int r = sipc5_parse_link_header(h, sizeof h, &l);
        CHECK(r == SIPC_PARSE_OK, "ext-len hdr parse OK (r=%d)", r);
        CHECK(l.hdr_len == 6, "hdr_len==6 (got %u)", l.hdr_len);
        CHECK(l.ext_len, "ext_len==true");
        CHECK(l.frame_len == 0x1234, "frame_len==0x1234 (got 0x%x)", l.frame_len);
    }

    /* ---- link header: bad start nibble ---- */
    {
        u8 h[4] = { 0x70, 10, 0, 0 }; /* top nibble 0x7 != 0xF */
        struct nuxel_sipc5_link l;
        int r = sipc5_parse_link_header(h, sizeof h, &l);
        CHECK(r == SIPC_PARSE_BAD_START, "bad start rejected (r=%d)", r);
    }

    /* ---- link header: truncated (only 1 byte) ---- */
    {
        u8 h[1] = { 0xF8 };
        struct nuxel_sipc5_link l;
        int r = sipc5_parse_link_header(h, sizeof h, &l);
        CHECK(r == SIPC_PARSE_TRUNCATED, "1-byte link truncated (r=%d)", r);
    }

    /* ---- FMT: parse a complete message ---- */
    {
        u8 m[7 + 4] = { 0x04, 0x00,          /* len=4 */
                        0x01, 0x00,          /* msg_seq=1 ack_seq=0 */
                        0x07, 0x00, 0x00,    /* main_cmd=7,sub=0,type=0 */
                        0xDE, 0xAD, 0xBE, 0xEF }; /* payload */
        struct nuxel_sipc_fmt f;
        size_t consumed = 0;
        int r = sipc5_parse_fmt(m, sizeof m, 0x10000, &f, &consumed);
        CHECK(r == SIPC_PARSE_OK, "fmt parse OK (r=%d)", r);
        CHECK(consumed == 11, "consumed==11 (got %zu)", consumed);
        CHECK(f.payload_len == 4, "payload_len==4 (got %u)", f.payload_len);
        CHECK(f.msg_seq == 1 && f.ack_seq == 0, "seq/ack correct");
        CHECK(f.main_cmd == 7 && f.cmd_type == 0, "cmd fields correct");
        CHECK(memcmp(f.payload, "\xDE\xAD\xBE\xEF", 4) == 0, "payload intact");
    }

    /* ---- FMT: truncated payload ---- */
    {
        u8 m[7 + 2] = { 0x08, 0x00, 1, 0, 7, 0, 0, 0xAA, 0xBB }; /* len=8, only 2 */
        struct nuxel_sipc_fmt f;
        size_t consumed = 0;
        int r = sipc5_parse_fmt(m, sizeof m, 0x10000, &f, &consumed);
        CHECK(r == SIPC_PARSE_TRUNCATED, "fmt truncated (r=%d)", r);
        CHECK(f.truncated, "truncated flag set");
    }

    /* ---- FMT: length overflow (declared > cap) ---- */
    {
        u8 m[7] = { 0xFF, 0xFF, 1, 0, 7, 0, 0 };
        struct nuxel_sipc_fmt f;
        size_t consumed = 0;
        int r = sipc5_parse_fmt(m, sizeof m, 0x100, &f, &consumed);
        CHECK(r == SIPC_PARSE_OVERFLOW, "fmt overflow rejected (r=%d)", r);
    }

    /* ---- FMT: partial header (only 3 bytes) ---- */
    {
        u8 m[3] = { 0x04, 0x00, 0x01 };
        struct nuxel_sipc_fmt f;
        size_t consumed = 0;
        int r = sipc5_parse_fmt(m, sizeof m, 0x10000, &f, &consumed);
        CHECK(r == SIPC_PARSE_TRUNCATED, "fmt 3-byte truncated (r=%d)", r);
    }

    printf("\n%s: %d failures\n", failures ? "RESULT=FAIL" : "RESULT=PASS",
           failures);
    return failures ? 1 : 0;
}
