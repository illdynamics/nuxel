/*
 * test_rfs_respond.c — unit tests for the source-backed RFS responder.
 * SPDX-License-Identifier: GPL-2.0-only
 *
 * Validates the recovered RFS request/response contract (O4/O5 source-backed)
 * without any device I/O. Uses the LIVE-captured 25-byte DELETE_ALL_VIS request
 * and synthetic variants to prove:
 *   1. The live request parses to {op=UNLINK_FILE, seq=1, path=DELETE_ALL_VIS}.
 *   2. The response is EXACTLY 14 bytes with the documented field layout.
 *   3. Only the boot marker is answered with success (result 0); every other op
 *      (incl. NV write/read/destructive) is fail-closed (negative result).
 *   4. Malformed/truncated/oversized/non-printable inputs are rejected.
 */
#include "rfs_respond.h"
#include <stdio.h>
#include <string.h>

static int failures = 0;
#define CHECK(c, ...) do { if (!(c)) { failures++; printf("FAIL %s:%d: ", __FILE__, __LINE__); printf(__VA_ARGS__); printf("\n"); } \
    else { printf("ok   %s:%d: ", __FILE__, __LINE__); printf(__VA_ARGS__); printf("\n"); } } while (0)

int main(void)
{
    /* LIVE-captured DELETE_ALL_VIS request (25 bytes). Note the observed bytes
     * actually encode: len=25, op=0x0b, seq=0x01, reserved=0x0000,
     * path_len=15, path="DELETE_ALL_VIS\0". */
    const uint8_t live[] = {
        0x19,0x00,0x00,0x00, 0x0b,0x01, 0x0f,0x00,0x00,0x00,
        'D','E','L','E','T','E','_','A','L','L','_','V','I','S',0x00
    };

    struct rfs_request r;
    enum rfs_request_parse_result pr = rfs_request_parse(live, sizeof live, &r);
    CHECK(pr == RFS_REQ_OK, "live DELETE_ALL_VIS parses OK (pr=%d)", pr);
    CHECK(r.total_len == 25, "total_len==25 (got %u)", r.total_len);
    CHECK(r.op == RFS_OP_UNLINK_FILE, "op==UNLINK_FILE 0x0b (got 0x%02x)", r.op);
    CHECK(r.seq == 1, "seq==1 (got %u)", r.seq);
    CHECK(r.path_len == 15, "path_len==15 (got %u)", r.path_len);
    CHECK(strcmp(r.path, "DELETE_ALL_VIS") == 0, "path==DELETE_ALL_VIS (got '%s')", r.path);
    CHECK(r.path_valid, "path printable");
    CHECK(r.special_delete_all_vis, "special_delete_all_vis flagged");

    /* Policy: the boot marker is the ONLY success case. */
    {
        int32_t detail = -999;
        int res = rfs_response_policy(&r, &detail);
        CHECK(res == 0, "DELETE_ALL_VIS policy -> success (res=%d)", res);
        CHECK(detail == 0, "DELETE_ALL_VIS detail == 0 (got %d)", detail);
    }

    /* Response build: 14 bytes, correct fields. */
    {
        uint8_t resp[RFS_RESP_LEN + 4];
        memset(resp, 0xAA, sizeof resp);
        size_t n = rfs_response_build(r.op, r.seq, 0, 0, resp);
        CHECK(n == RFS_RESP_LEN, "response length == 14 (got %zu)", n);
        CHECK(resp[0]==0 && resp[1]==0 && resp[2]==0 && resp[3]==0, "result==0");
        CHECK(resp[4] == 0x0b, "resp op echo==0x0b (got 0x%02x)", resp[4]);
        CHECK(resp[5] == 0x01, "resp seq echo==0x01 (got 0x%02x)", resp[5]);
        CHECK(resp[6]==0 && resp[7]==0, "resp reserved==0");
        CHECK(resp[8]==0 && resp[9]==0 && resp[10]==0 && resp[11]==0, "resp detail==0");
    }

    /* Fail-closed: NV_WRITE_ALL (0x15) must be refused with a negative result. */
    {
        uint8_t req[16] = { 0 };
        req[0] = 16; req[4] = RFS_OP_NV_WRITE_ALL; req[5] = 0x37;
        req[6] = 4; req[10] = 'X'; req[11] = 'Y'; req[12] = 'Z'; req[13] = 0;
        struct rfs_request rr;
        CHECK(rfs_request_parse(req, sizeof req, &rr) == RFS_REQ_OK, "NV_WRITE_ALL parses");
        int32_t detail = 0;
        int res = rfs_response_policy(&rr, &detail);
        CHECK(res < 0, "NV_WRITE_ALL policy fail-closed (res=%d)", res);
    }

    /* Fail-closed: OPEN_FILE (0x11) of any path must be refused. */
    {
        uint8_t req[24] = { 0 };
        req[0] = 24; req[4] = RFS_OP_OPEN_FILE; req[5] = 2;
        req[6] = 12; memcpy(req+10, "nv_data.bin\0", 12);
        struct rfs_request rr;
        CHECK(rfs_request_parse(req, sizeof req, &rr) == RFS_REQ_OK, "OPEN_FILE parses");
        int32_t detail = 0;
        CHECK(rfs_response_policy(&rr, &detail) < 0, "OPEN_FILE fail-closed");
    }

    /* Reject truncated (fewer than header bytes). */
    CHECK(rfs_request_parse(live, 9, &r) == RFS_REQ_SHORT, "truncated -> SHORT");
    /* Reject huge declared path_len. */
    {
        uint8_t req[16] = { 0 };
        req[0] = 16; req[4] = 0x0b; req[5] = 1;
        req[6] = 0x00; req[7] = 0x04; req[8] = 0; req[9] = 0; /* path_len=1024 */
        req[10]='D'; req[11]='E'; req[12]='L'; req[13]=0;
        CHECK(rfs_request_parse(req, sizeof req, &r) == RFS_REQ_OVERFLOW, "path_len 1024 -> OVERFLOW");
    }
    /* Reject non-printable path. */
    {
        uint8_t req[16] = { 0 };
        req[0] = 16; req[4] = 0x0b; req[5] = 1; req[6] = 4;
        req[10]=0xff; req[11]=0xfe; req[12]=0xfd; req[13]=0;
        CHECK(rfs_request_parse(req, sizeof req, &r) != RFS_REQ_OK, "non-printable path rejected");
    }
    /* Unlink of a DIFFERENT (non-marker) path must be fail-closed, not success. */
    {
        uint8_t req[16] = { 0 };
        req[0] = 16; req[4] = RFS_OP_UNLINK_FILE; req[5] = 3; req[6] = 4;
        memcpy(req+10, "foo\0", 4);
        struct rfs_request rr;
        CHECK(rfs_request_parse(req, sizeof req, &rr) == RFS_REQ_OK, "unlink foo parses");
        CHECK(!rr.special_delete_all_vis, "unlink foo NOT special");
        int32_t detail = 0;
        CHECK(rfs_response_policy(&rr, &detail) < 0, "unlink other path fail-closed");
    }

    printf("\n%s: %d failures\n", failures ? "RESULT=FAIL" : "RESULT=PASS", failures);
    return failures ? 1 : 0;
}
