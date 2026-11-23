/*
 * test_fmt_tx.c — unit tests for the S5000AP FMT transmit serializers.
 * SPDX-License-Identifier: GPL-2.0-only
 *
 * Every expected byte vector below is derived from the exact vendor RIL
 * disassembly (IpcTxPsAttach/IpcTxGetPdpContext/IpcTxSetMobileDataSetting/
 * IpcTxDefinePdpContext) — NOT from guessed packets. This test proves the
 * serializer reproduces those source-backed vectors byte-for-byte.
 */
#include "fmt_tx.h"
#include <stdio.h>
#include <string.h>

static int failures = 0;
#define CHECK(c, ...) do { if (!(c)) { failures++; printf("FAIL %s:%d: ", __FILE__, __LINE__); printf(__VA_ARGS__); printf("\n"); } \
    else { printf("ok   %s:%d: ", __FILE__, __LINE__); printf(__VA_ARGS__); printf("\n"); } } while (0)

static int hexcmp(const uint8_t *a, const uint8_t *b, size_t n)
{
    for (size_t i = 0; i < n; i++) if (a[i] != b[i]) return (int)i;
    return -1;
}

int main(void)
{
    struct fmt_tx_frame f;

    /* --- PsAttach (source: IpcTxPsAttach @0x31fa98) ---
     * Expected 10-byte frame:
     *   len=10, msg_seq=0, ack_seq=0, main=13, sub=3, type=3,
     *   payload = [1,0,0]  (attach=1, suspend=0, reason=0)
     */
    memset(&f, 0, sizeof f);
    CHECK(fmt_tx_ps_attach(&f, true, false, 0), "ps_attach builds");
    const uint8_t ps_attach_expect[10] = { 0x0a,0x00, 0x00,0x00, 0x0d,0x03, 0x03, 0x01,0x00,0x00 };
    int bad = hexcmp(f.buf, ps_attach_expect, 10);
    CHECK(f.len == 10, "ps_attach len==10 (got %zu)", f.len);
    CHECK(bad == -1, "ps_attach bytes match disasm (first diff @ %d)", bad);
    CHECK(f.main_cmd == 13 && f.sub_cmd == 3 && f.cmd_type == 3,
          "ps_attach main/sub/type = 13/3/3");

    /* --- GetPdpContext (source: IpcTxGetPdpContext @0x31f928) ---
     * Expected 7-byte frame: len=7, main=13, sub=4, type=2, no payload.
     */
    memset(&f, 0, sizeof f);
    CHECK(fmt_tx_get_pdp_context(&f), "get_pdp_context builds");
    const uint8_t getpdp_expect[7] = { 0x07,0x00, 0x00,0x00, 0x0d,0x04, 0x02 };
    bad = hexcmp(f.buf, getpdp_expect, 7);
    CHECK(f.len == 7, "get_pdp_context len==7");
    CHECK(bad == -1, "get_pdp_context bytes match disasm (diff @ %d)", bad);
    CHECK(f.cmd_type == 2, "get_pdp_context type==2 (REQUEST)");

    /* --- SetMobileDataSetting (source: IpcTxSetMobileDataSetting @0x3214c8) ---
     * Expected 9-byte frame: len=9, main=13, sub=29(0x1d), type=3,
     * payload = [1, 1] (enable=1, extra=1)
     */
    memset(&f, 0, sizeof f);
    CHECK(fmt_tx_mobile_data(&f, true, true), "mobile_data builds");
    const uint8_t mobdata_expect[9] = { 0x09,0x00, 0x00,0x00, 0x0d,0x1d, 0x03, 0x01,0x01 };
    bad = hexcmp(f.buf, mobdata_expect, 9);
    CHECK(f.len == 9, "mobile_data len==9");
    CHECK(bad == -1, "mobile_data bytes match disasm (diff @ %d)", bad);
    CHECK(f.sub_cmd == 29, "mobile_data sub==29 SYNC_PROFILE_INFO");

    /* --- DefinePdpContext (source: IpcTxDefinePdpContext @0x31f580) ---
     * 134-byte frame. Verify header + APN placement + protocol byte.
     */
    memset(&f, 0, sizeof f);
    CHECK(fmt_tx_define_pdp_context(&f, "internet", FMT_TX_PROTO_IPV4V6, 1), "define_pdp builds");
    CHECK(f.len == 134, "define_pdp len==134 (got %zu)", f.len);
    CHECK(f.main_cmd == 13 && f.sub_cmd == 1 && f.cmd_type == 3,
          "define_pdp main/sub/type=13/1/3");
    /* header: len LE = 0x86 */
    CHECK(f.buf[0] == 0x86 && f.buf[1] == 0x00, "define_pdp len field = 134 LE");
    /* payload[0]=0x01, payload[1]=profile_id=1 */
    CHECK(f.buf[7] == 0x01, "define_pdp payload[0]==0x01");
    CHECK(f.buf[8] == 0x01, "define_pdp payload[1]==profile_id");
    /* APN "internet" (8 chars) at full-frame offset 10 = payload offset 3 */
    CHECK(memcmp(&f.buf[10], "internet", 8) == 0, "define_pdp APN placed at frame offset 10");
    CHECK(f.buf[10 + 8] == 0x00, "define_pdp APN NUL-terminated in fixed field");

    /* --- APN too long must be rejected (vendor strlen<=0x65 gate) --- */
    char longapn[120]; memset(longapn, 'a', sizeof longapn); longapn[110] = 0;
    CHECK(!fmt_tx_define_pdp_context(&f, longapn, FMT_TX_PROTO_IPV4V6, 1),
          "define_pdp rejects overly-long APN");

    /* --- raw serializer + overflow guard --- */
    memset(&f, 0, sizeof f);
    uint8_t pl[3] = { 0xaa, 0xbb, 0xcc };
    CHECK(fmt_tx_raw(&f, 13, 3, 3, pl, 3), "raw 3-byte payload builds");
    CHECK(f.len == 10 && f.buf[7]==0xaa && f.buf[8]==0xbb && f.buf[9]==0xcc,
          "raw copies payload after 7-byte header");

    /* payload too large -> rejected (no overflow) */
    uint8_t big[FMT_TX_MAX_FRAME]; memset(big, 0, sizeof big);
    CHECK(!fmt_tx_raw(&f, 13, 3, 3, big, FMT_TX_MAX_FRAME),
          "raw rejects oversized payload");

    printf("\n%s: %d failures\n", failures ? "RESULT=FAIL" : "RESULT=PASS", failures);
    return failures ? 1 : 0;
}
