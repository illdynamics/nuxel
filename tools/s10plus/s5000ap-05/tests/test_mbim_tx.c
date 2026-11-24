/*
 * test_mbim_tx.c — golden-vector tests for the recovered MBIM<->SIPC builders.
 * SPDX-License-Identifier: GPL-2.0-only
 *
 * Every assertion derives from the exact vendor RIL disassembly (round-31):
 *   - IpcProtocol41::IpcTxRawIpc @0x3180f0  => FMT frame main=0x16/sub=0x0c/
 *     type=0x05, 1-byte forward flag, then MBIM payload.
 *   - FillMbimMsLteAttachContext @0x2d5e18 => UTF-16LE strings, ipType/auth.
 * Plus the public USB-IF/Microsoft MBIM v1.0 spec (CID 0x0A).
 */
#include "mbim_tx.h"
#include <stdio.h>
#include <string.h>

static int failures = 0;
#define CHECK(c, ...) do { if (!(c)) { failures++; printf("FAIL %s:%d: ", __FILE__, __LINE__); printf(__VA_ARGS__); printf("\n"); } \
    else { printf("ok   %s:%d: ", __FILE__, __LINE__); printf(__VA_ARGS__); printf("\n"); } } while (0)

static uint32_t rd_u32le(const uint8_t *p) {
    return (uint32_t)p[0] | ((uint32_t)p[1] << 8) | ((uint32_t)p[2] << 16) | ((uint32_t)p[3] << 24);
}

int main(void)
{
    /* MBIM message = 12-byte header + 8-byte command header (CID+type), info
     * buffer begins at byte 20. */
    #define IBASE 20u

    /* --- 1. IpcTxRawIpc FMT frame --- */
    {
        const uint8_t mbim_payload[8] = { 0xde,0xad,0xbe,0xef,0x01,0x02,0x03,0x04 };
        uint8_t fr[64];
        size_t n = mbim_tx_build_raw_ipc_frame(fr, sizeof fr, mbim_payload, 8, 0x11, 0x22);
        CHECK(n == 16, "rawipc frame len == 16 (got %zu)", n);
        CHECK(fr[0] == (uint8_t)n && fr[1] == 0, "rawipc total_len u16 LE");
        CHECK(fr[2] == 0x11, "rawipc msg_seq = 0x11");
        CHECK(fr[3] == 0x22, "rawipc ack_seq = 0x22");
        CHECK(fr[4] == 0x16, "rawipc main_cmd = 0x16");
        CHECK(fr[5] == 0x0c, "rawipc sub_cmd = 0x0c");
        CHECK(fr[6] == 0x05, "rawipc cmd_type = 0x05");
        CHECK(fr[7] == 0x01, "rawipc forward-flag = 0x01");
        CHECK(memcmp(fr + 8, mbim_payload, 8) == 0, "rawipc MBIM payload copied");
    }

    /* --- 2. single context MS LTE Attach Config --- */
    {
        struct mbim_attach_context ctx[1];
        uint8_t mb[512];
        memset(ctx, 0, sizeof ctx);
        ctx[0].apn = "internet"; ctx[0].username = ""; ctx[0].password = "";
        ctx[0].ip_type = MBIM_CONTEXT_IP_TYPE_IPV4V6; ctx[0].auth = MBIM_AUTH_PROTOCOL_NONE;
        size_t n = mbim_tx_build_lte_attach_config(mb, sizeof mb, ctx, 1, 0x01);
        CHECK(n > 40, "attach config built (len %zu)", n);
        CHECK(rd_u32le(mb + 0) == MBIM_MSG_TYPE_COMMAND, "msg type = COMMAND");
        CHECK(rd_u32le(mb + 4) == (uint32_t)n, "msg length == total");
        CHECK(rd_u32le(mb + 8) == 0x01u, "transaction id");
        CHECK(rd_u32le(mb + 12) == MBIM_CID_MS_LTE_ATTACH_CONFIG, "CID = 0x0A");
        CHECK(rd_u32le(mb + 16) == 0u, "command type = SET");

        const uint8_t *info = mb + IBASE;
        uint32_t nctx = rd_u32le(info + 0);
        uint32_t data_off = rd_u32le(info + 4);
        CHECK(nctx == 1u, "elementCount = 1");
        CHECK(data_off >= 28u, "info buffer data offset >= 28 (got %u)", data_off);

        /* per-context {offset,size} slot lives at info+8 (2-word header) */
        uint32_t off = rd_u32le(info + 8);
        uint32_t sz  = rd_u32le(info + 12);
        CHECK(sz > 44u, "context 0 size > 44 (got %u)", sz);
        uint32_t c = IBASE + off;   /* absolute position of context record */
        CHECK(rd_u32le(mb + c + 0) == 0u, "ctx0 index = 0");
        CHECK(rd_u32le(mb + c + 4) == MBIM_CONTEXT_IP_TYPE_IPV4V6, "ctx0 ipType = 5");
        CHECK(rd_u32le(mb + c + 8) == MBIM_AUTH_PROTOCOL_NONE, "ctx0 auth = 0");
        uint32_t apn_off = rd_u32le(mb + c + 12);
        uint32_t apn_len = rd_u32le(mb + c + 16);
        CHECK(apn_len == 16u, "ctx0 APN UTF-16 len = 16 (got %u)", apn_len);
        const uint8_t internet16[16] = {'i',0,'n',0,'t',0,'e',0,'r',0,'n',0,'e',0,'t',0};
        CHECK(memcmp(mb + IBASE + apn_off, internet16, 16) == 0, "ctx0 APN = 'internet' UTF-16LE");
    }

    /* --- 3. three contexts --- */
    {
        struct mbim_attach_context ctx[3];
        uint8_t mb[1024];
        memset(ctx, 0, sizeof ctx);
        ctx[0].apn = "internet"; ctx[0].ip_type = MBIM_CONTEXT_IP_TYPE_IPV4V6; ctx[0].auth = MBIM_AUTH_PROTOCOL_NONE;
        ctx[1].apn = "ims";      ctx[1].ip_type = MBIM_CONTEXT_IP_TYPE_IPV4V6; ctx[1].auth = MBIM_AUTH_PROTOCOL_NONE;
        ctx[2].apn = "internet"; ctx[2].ip_type = MBIM_CONTEXT_IP_TYPE_IPV4V6; ctx[2].auth = MBIM_AUTH_PROTOCOL_NONE;
        size_t n = mbim_tx_build_lte_attach_config(mb, sizeof mb, ctx, 3, 0x02);
        CHECK(n > 60, "3-ctx built (len %zu)", n);
        const uint8_t *info = mb + IBASE;
        CHECK(rd_u32le(info + 0) == 3u, "3-ctx elementCount = 3");
        uint32_t o0 = rd_u32le(info + 8);
        uint32_t o1 = rd_u32le(info + 16);
        uint32_t o2 = rd_u32le(info + 24);
        CHECK(rd_u32le(mb + IBASE + o0 + 0) == 0u, "ctx0 index = 0");
        CHECK(rd_u32le(mb + IBASE + o1 + 0) == 1u, "ctx1 index = 1");
        CHECK(rd_u32le(mb + IBASE + o2 + 0) == 2u, "ctx2 index = 2");
        CHECK(o0 < o1 && o1 < o2, "3-ctx offsets monotonic");
    }

    /* --- 4. fail-closed --- */
    {
        uint8_t tiny[8];
        struct mbim_attach_context ctx[1];
        memset(ctx, 0, sizeof ctx);
        ctx[0].apn = "internet";
        CHECK(mbim_tx_build_lte_attach_config(tiny, sizeof tiny, ctx, 1, 1) == 0, "overflow -> 0");
        CHECK(mbim_tx_build_lte_attach_config(tiny, sizeof tiny, ctx, 0, 1) == 0, "0 contexts -> 0");
        ctx[0].apn = "";
        CHECK(mbim_tx_build_lte_attach_config(tiny, sizeof tiny, ctx, 1, 1) == 0, "empty APN -> 0");
    }

    /* --- 5. MBIM session control-plane primitives (OPEN/CLOSE/CAPS query) --- */
    {
        uint8_t b[64];
        size_t n;

        /* OPEN: 16 bytes, type=1 */
        memset(b, 0xaa, sizeof b);
        n = mbim_tx_build_open(b, sizeof b, 0x07, MBIM_MAX_CONTROL_TRANSFER);
        CHECK(n == 16u, "OPEN len == 16 (got %zu)", n);
        CHECK(rd_u32le(b + 0) == MBIM_MSG_TYPE_OPEN, "OPEN msg type = 1");
        CHECK(rd_u32le(b + 4) == 16u, "OPEN length = 16");
        CHECK(rd_u32le(b + 8) == 0x07u, "OPEN transaction id");
        CHECK(rd_u32le(b + 12) == MBIM_MAX_CONTROL_TRANSFER, "OPEN max_control_transfer = 4096");
        CHECK(b[16] == 0xaa, "OPEN does not overflow buffer");

        /* CLOSE: 12 bytes, type=2 */
        memset(b, 0xbb, sizeof b);
        n = mbim_tx_build_close(b, sizeof b, 0x08);
        CHECK(n == 12u, "CLOSE len == 12 (got %zu)", n);
        CHECK(rd_u32le(b + 0) == MBIM_MSG_TYPE_CLOSE, "CLOSE msg type = 2");
        CHECK(rd_u32le(b + 4) == 12u, "CLOSE length = 12");
        CHECK(rd_u32le(b + 8) == 0x08u, "CLOSE transaction id");

        /* Device caps QUERY: 20 bytes, CID 0x01, type=QUERY */
        memset(b, 0xcc, sizeof b);
        n = mbim_tx_build_caps_query(b, sizeof b, 0x09);
        CHECK(n == 20u, "caps query len == 20 (got %zu)", n);
        CHECK(rd_u32le(b + 0) == MBIM_MSG_TYPE_COMMAND, "caps query msg type = COMMAND(3)");
        CHECK(rd_u32le(b + 4) == 20u, "caps query length = 20");
        CHECK(rd_u32le(b + 8) == 0x09u, "caps query transaction id");
        CHECK(rd_u32le(b + 12) == MBIM_CID_DEVICE_CAPS, "caps query CID = 0x01");
        CHECK(rd_u32le(b + 16) == 0u, "caps query type = QUERY(0)");

        /* generic attach-status QUERY: CID 0x0B */
        memset(b, 0xdd, sizeof b);
        n = mbim_tx_build_query(b, sizeof b, 0x0a, MBIM_CID_MS_LTE_ATTACH_STATUS);
        CHECK(n == 20u, "attach-status query len == 20 (got %zu)", n);
        CHECK(rd_u32le(b + 12) == MBIM_CID_MS_LTE_ATTACH_STATUS, "attach-status CID = 0x0B");
        CHECK(rd_u32le(b + 16) == 0u, "attach-status type = QUERY(0)");

        /* fail-closed on tiny buffers */
        uint8_t tiny[8];
        CHECK(mbim_tx_build_open(tiny, sizeof tiny, 1, 1) == 0, "OPEN tiny -> 0");
        CHECK(mbim_tx_build_close(tiny, sizeof tiny, 1) == 0, "CLOSE tiny -> 0");
        CHECK(mbim_tx_build_caps_query(tiny, sizeof tiny, 1) == 0, "caps tiny -> 0");
    }
    if (failures) { printf("%d failures\n", failures); return 1; }
    printf("test_mbim_tx: all PASS\n");
    return 0;
}
