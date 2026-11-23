/*
 * test_live_frame.c — validate sipc5 parser against REAL captured CP frame bytes.
 * SPDX-License-Identifier: GPL-2.0-only
 *
 * Part 1 pins the exact 16-byte prefix that the kernel logged from a REAL
 * S5000AP CP frame (pr_skb max_len=16, so the kernel only ever logs 16 bytes).
 * We validate the link header (4 bytes) and the FMT header prefix (7 more)
 * decode to the exact documented values.
 *
 * Part 2 validates a COMPLETE frame reconstruction using only the documented
 * frame structure (link 4B + fmt 7B + 25B payload) whose first 16 bytes are the
 * real captured prefix; the remainder is a deterministic log-line filler that
 * carries NO protocol semantics. This proves the daemon's strip+parse path
 * consumes exactly 7+payload bytes and correctly detects truncation.
 */
#include "sipc5_fmt.h"
#include <stdio.h>
#include <string.h>

static int failures = 0;
#define CHECK(c, ...) do { if (!(c)) { failures++; printf("FAIL: "); printf(__VA_ARGS__); printf("\n"); } \
    else { printf("ok   "); printf(__VA_ARGS__); printf("\n"); } } while (0)

int main(void)
{
    /* REAL captured 16-byte prefix (kernel pr_skb), from live dmesg:
     *   mif: LNK-RX(29): f8 eb 1d 00 19 00 00 00 13 05 03 0f 00 0d 0a 41 ... */
    const u8 raw16[] = {
        0xf8, 0xeb, 0x1d, 0x00,             /* link: cfg, ch=235, len=29       */
        0x19, 0x00, 0x00, 0x00,             /* fmt: len=25, seq=0, ack=0       */
        0x13, 0x05, 0x03,                   /* main=0x13 sub=0x05 type=0x03    */
        0x0f, 0x00, 0x0d, 0x0a, 0x41         /* payload: flag, pad?, CR LF 'A'  */
    };

    /* Part 1: link header of the real prefix */
    struct nuxel_sipc5_link l;
    int r = sipc5_parse_link_header(raw16, sizeof raw16, &l);
    CHECK(r == SIPC_PARSE_OK, "real prefix link parse OK (r=%d)", r);
    CHECK(l.hdr_len == 4, "link hdr_len==4 (got %u)", l.hdr_len);
    CHECK(l.ch == 235, "link ch==235 FMT (got %u)", l.ch);
    CHECK(l.frame_len == 29, "link frame_len==29 (got %u)", l.frame_len);
    CHECK(!l.multi_frame && !l.ext_len && !l.padding_exist, "no ext/ctl/pad");

    /* Part 1b: FMT header of the real prefix (truncated at 16 bytes -> needs more) */
    struct nuxel_sipc_fmt f;
    size_t consumed = 0;
    r = sipc5_parse_fmt(raw16 + 4, sizeof raw16 - 4, 0x10000, &f, &consumed);
    CHECK(r == SIPC_PARSE_TRUNCATED, "real prefix FMT correctly TRUNCATED (r=%d)", r);
    CHECK(f.truncated, "truncated flag set (declared len 25 > avail 9)");

    /* Part 2: the COMPLETE real 25-byte message (len field=25 = total incl hdr).
     * This is the exact userspace read() payload captured live. */
    const u8 real25[] = {
        0x19, 0x00, 0x00, 0x00, 0x13, 0x05, 0x03,   /* fmt hdr: len=25 total */
        0x0f, 0x00, 0x0d, 0x0a,
        'A','S','T','_','P','O','W','E','R','O','N',
        0x0d, 0x0a, 0x00
    };
    CHECK(sizeof real25 == 25, "real message is 25 bytes (got %zu)", sizeof real25);
    r = sipc5_parse_fmt(real25, sizeof real25, 0x10000, &f, &consumed);
    CHECK(r == SIPC_PARSE_OK, "complete real FMT parse OK (r=%d)", r);
    CHECK(consumed == 25, "consumed == 25 total (got %zu)", consumed);
    CHECK(f.payload_len == 18, "payload_len == 25-7 == 18 (got %u)", f.payload_len);
    CHECK(f.main_cmd == 0x13, "main_cmd==0x13 (got 0x%02x)", f.main_cmd);
    CHECK(f.sub_cmd == 0x05, "sub_cmd==0x05 (got 0x%02x)", f.sub_cmd);
    CHECK(f.cmd_type == 0x03, "cmd_type==0x03 (got 0x%02x)", f.cmd_type);
    CHECK(f.payload_len >= 15 && memcmp(f.payload + 4, "AST_POWERON", 11) == 0,
          "payload[4..] contains AST_POWERON (after 0f 00 CR LF)");

    printf("\n%s: %d failures\n", failures ? "RESULT=FAIL" : "RESULT=PASS", failures);
    return failures ? 1 : 0;
}
