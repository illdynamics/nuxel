/*
 * test_rfs_proto.c — unit tests for the RFS raw-request parser/classifier.
 * SPDX-License-Identifier: GPL-2.0-only
 */
#include "rfs_proto.h"
#include <stdio.h>
#include <string.h>

static int failures = 0;
#define CHECK(c, ...) do { if (!(c)) { failures++; printf("FAIL %s:%d: ", __FILE__, __LINE__); printf(__VA_ARGS__); printf("\n"); } \
    else { printf("ok   %s:%d: ", __FILE__, __LINE__); printf(__VA_ARGS__); printf("\n"); } } while (0)

int main(void)
{
    /* LIVE-captured DELETE_ALL_VIS request (25 bytes) */
    const unsigned char live[] = {
        0x19,0x00,0x00,0x00, 0x0b,0x01, 0x0f,0x00, 0x00,0x00,
        'D','E','L','E','T','E','_','A','L','L','_','V','I','S',0x00
    };
    struct rfs_proto_msg m;
    int r = rfs_proto_parse(live, sizeof live, &m);
    CHECK(r == RFS_PROTO_OK, "live DELETE_ALL_VIS parses OK (r=%d)", r);
    CHECK(m.len == 25, "len==25 (got %u)", m.len);
    CHECK(m.op_class == 0x0b, "op_class==0x0b (got 0x%02x)", m.op_class);
    CHECK(m.path_len == 15, "path_len==15 (got %u)", m.path_len);
    CHECK(strcmp(m.opcode, "DELETE_ALL_VIS") == 0, "opcode==DELETE_ALL_VIS (got '%s')", m.opcode);
    CHECK(m.opcode_valid, "opcode printable");
    CHECK(m.known, "op_class known");
    CHECK(m.destructive, "DELETE_ALL_VIS is destructive (fail-closed)");

    /* short buffer must be rejected, not overread */
    r = rfs_proto_parse(live, 5, &m);
    CHECK(r == RFS_PROTO_SHORT, "short buffer -> SHORT (r=%d)", r);

    /* an opaque bulk blob (hi-entropy) is header-shaped but non-printable */
    unsigned char bulk[32];
    for (int i = 0; i < 32; i++) bulk[i] = (unsigned char)(0x80 + (i * 7) % 0x7f);
    r = rfs_proto_parse(bulk, sizeof bulk, &m);
    CHECK(r != RFS_PROTO_OK, "non-printable bulk REJECTED as RFS (r=%d)", r);

    /* unknown op_class with a clean printable opcode -> known=false */
    unsigned char unk[] = { 0x08,0,0,0, 0x42,0x00, 0x04,0x00, 0,0, 'R','E','A','D',0 };
    r = rfs_proto_parse(unk, sizeof unk, &m);
    CHECK(r == RFS_PROTO_OK && m.op_class == 0x42, "unknown op parses (op=0x%02x)", m.op_class);
    CHECK(!m.known && !m.destructive, "unknown op not known/destructive");

    printf("\n%s: %d failures\n", failures ? "RESULT=FAIL" : "RESULT=PASS", failures);
    return failures ? 1 : 0;
}
