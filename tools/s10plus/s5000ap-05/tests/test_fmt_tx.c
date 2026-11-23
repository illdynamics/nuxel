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

    /* --- SetDataCallEstablish (source: IpcTxSetDataCallEstablish @0x320a10) ---
     * Expected 8-byte frame: len=8, main=3, sub=2, type=3, payload=[1].
     */
    memset(&f, 0, sizeof f);
    CHECK(fmt_tx_set_data_call_establish(&f, true), "data_call_establish builds");
    const uint8_t dc_est_expect[8] = { 0x08,0x00, 0x00,0x00, 0x03,0x02, 0x03, 0x01 };
    bad = hexcmp(f.buf, dc_est_expect, 8);
    CHECK(f.len == 8, "data_call_establish len==8");
    CHECK(bad == -1, "data_call_establish bytes match disasm (diff @ %d)", bad);
    CHECK(f.main_cmd == 3 && f.sub_cmd == 2, "data_call_establish main/sub=3/2");

    /* --- SetAlwaysOnPdn (source: IpcTxSetAlwaysOnPdn @0x321550) ---
     * 9-byte frame: len=9, main=13, sub=34(0x22), type=3, payload=[1, profile].
     */
    memset(&f, 0, sizeof f);
    CHECK(fmt_tx_set_always_on_pdn(&f, true, 1), "always_on_pdn builds");
    const uint8_t aopn_expect[9] = { 0x09,0x00, 0x00,0x00, 0x0d,0x22, 0x03, 0x01,0x01 };
    bad = hexcmp(f.buf, aopn_expect, 9);
    CHECK(f.len == 9, "always_on_pdn len==9");
    CHECK(bad == -1, "always_on_pdn bytes match disasm (diff @ %d)", bad);
    CHECK(f.main_cmd == 13 && f.sub_cmd == 34, "always_on_pdn main/sub=13/34");

    /* --- SetDataProfile (source: IpcTxSetDataProfile @0x31ff48) ---
     * 203-byte frame: len=203, main=13, sub=27, type=3. APN at payload[22],
     * auth=0 at payload[0], protocol byte at payload[21]+payload[188].
     */
    memset(&f, 0, sizeof f);
    CHECK(fmt_tx_set_data_profile(&f, "internet", FMT_TX_AUTH_NONE, FMT_TX_PROTO_IPV4V6), "set_data_profile builds");
    CHECK(f.len == 203, "set_data_profile len==203 (got %zu)", f.len);
    CHECK(f.main_cmd == 13 && f.sub_cmd == 27 && f.cmd_type == 3,
          "set_data_profile main/sub/type=13/27/3");
    CHECK(f.buf[0] == 0xcb && f.buf[1] == 0x00, "set_data_profile len field = 203 LE");
    CHECK(f.buf[7 + 0] == FMT_TX_AUTH_NONE, "set_data_profile auth code = 1 (NONE)");
    CHECK(f.buf[7 + 21] == 0x04 && f.buf[7 + 188] == 0x04,
          "set_data_profile protocol IPV4V6=0x04 at payload[21]+payload[188]");
    CHECK(memcmp(&f.buf[7 + 22], "internet", 8) == 0,
          "set_data_profile APN placed at payload offset 22");
    /* COMPLETE tail fields (recovered from disasm @0x31ff48):
     * payload[187]=auth flag (NONE -> 0x01), payload[189]=pco flag (1),
     * tail halfwords 0. */
    CHECK(f.buf[7 + 187] == 0x01, "set_data_profile auth flag payload[187] == 0x01");
    CHECK(f.buf[7 + 189] == 0x01, "set_data_profile pco flag payload[189] == 0x01");
    CHECK(f.buf[7 + 190] == 0x00 && f.buf[7 + 191] == 0x00,
          "set_data_profile tail int a == 0");
    CHECK(f.buf[7 + 192] == 0x00 && f.buf[7 + 193] == 0x00,
          "set_data_profile tail int b == 0");
    CHECK(f.buf[7 + 194] == 0x00 && f.buf[7 + 195] == 0x00,
          "set_data_profile tail int c == 0");
    CHECK(f.buf[7 + 123] == 0x00 && f.buf[7 + 154] == 0x00,
          "set_data_profile username field zero-filled");
    CHECK(f.buf[7 + 155] == 0x00 && f.buf[7 + 186] == 0x00,
          "set_data_profile password field zero-filled");

    /* --- SetLteAttachProfile (source: IpcTxSetLteAttachProfile @0x320238) ---
     * 201-byte frame: len=201(0xc9), main=13, sub=20(0x14), type=3.
     * payload[0]=3 (enable), payload[1]=cid, payload[2]=protocol, APN at +3. */
    memset(&f, 0, sizeof f);
    CHECK(fmt_tx_set_lte_attach_profile(&f, "internet", FMT_TX_AUTH_NONE,
                                        FMT_TX_PROTO_IPV4V6, 1),
          "set_lte_attach_profile builds");
    CHECK(f.len == 201, "set_lte_attach_profile len==201 (got %zu)", f.len);
    CHECK(f.main_cmd == 13 && f.sub_cmd == 20 && f.cmd_type == 3,
          "set_lte_attach_profile main/sub/type=13/20/3");
    CHECK(f.buf[0] == 0xc9 && f.buf[1] == 0x00, "set_lte_attach_profile len field = 201 LE");
    CHECK(f.buf[7 + 0] == 0x03, "set_lte_attach_profile payload[0] flag == 3");
    CHECK(f.buf[7 + 1] == 0x01, "set_lte_attach_profile payload[1] cid == 1");
    CHECK(f.buf[7 + 2] == 0x04, "set_lte_attach_profile payload[2] protocol == 0x04");
    CHECK(memcmp(&f.buf[7 + 3], "internet", 8) == 0,
          "set_lte_attach_profile APN placed at payload offset 3");
    CHECK(f.buf[7 + 168] == 0x01, "set_lte_attach_profile auth flag == 0x01");
    CHECK(f.buf[7 + 169] == 0x01, "set_lte_attach_profile pco flag == 0x01");

    /* --- SetPdpContext / ACTIVATE (source: IpcTxSetPdpContext @0x31f6e0) ---
     * 112-byte frame: len=112(0x70), main=13, sub=4, type=3.
     * payload[0]=1 (pdp_type), payload[1]=cid, flags=0x11, APN at +6. */
    memset(&f, 0, sizeof f);
    CHECK(fmt_tx_set_pdp_context(&f, "internet", FMT_TX_AUTH_NONE,
                                 FMT_TX_PROTO_IPV4V6, 1),
          "set_pdp_context builds");
    CHECK(f.len == 112, "set_pdp_context len==112 (got %zu)", f.len);
    CHECK(f.main_cmd == 13 && f.sub_cmd == 4 && f.cmd_type == 3,
          "set_pdp_context main/sub/type=13/4/3");
    CHECK(f.buf[0] == 0x70 && f.buf[1] == 0x00, "set_pdp_context len field = 112 LE");
    CHECK(f.buf[7 + 0] == 0x03, "set_pdp_context payload[0] pdp_type == 3 (LTE)");
    CHECK(f.buf[7 + 1] == 0x01, "set_pdp_context payload[1] cid == 1");
    CHECK(f.buf[7 + 2] == 0x11, "set_pdp_context payload[2] flags == 0x11 (APN+ACTIVATE)");
    CHECK(memcmp(&f.buf[7 + 6], "internet", 8) == 0,
          "set_pdp_context APN placed at payload offset 6");
    CHECK(f.buf[7 + 102] == 0x01, "set_pdp_context auth flag == 0x01");
    CHECK(f.buf[7 + 104] == 0x04, "set_pdp_context protocol byte == 0x04 IPV4V6");

    /* --- SyncProfileInfo (source: IpcTxSyncProfileInfo @0x31fb48) ---
     * 326-byte frame: len=326(0x146), main=13, sub=37(0x25), type=3.
     * payload[0]=1, payload[1..2]=1, APN at +4, protocol at +109/110. */
    memset(&f, 0, sizeof f);
    CHECK(fmt_tx_sync_profile_info(&f, "internet", FMT_TX_AUTH_NONE,
                                   FMT_TX_PROTO_IPV4V6),
          "sync_profile_info builds");
    CHECK(f.len == 326, "sync_profile_info len==326 (got %zu)", f.len);
    CHECK(f.main_cmd == 13 && f.sub_cmd == 37 && f.cmd_type == 3,
          "sync_profile_info main/sub/type=13/37/3");
    CHECK(f.buf[0] == 0x46 && f.buf[1] == 0x01, "sync_profile_info len field = 326 LE");
    CHECK(f.buf[7 + 0] == 0x01, "sync_profile_info payload[0] enable == 1");
    CHECK(f.buf[7 + 1] == 0x01, "sync_profile_info payload[1] region == 1");
    CHECK(memcmp(&f.buf[7 + 4], "internet", 8) == 0,
          "sync_profile_info APN placed at payload offset 4");
    CHECK(f.buf[7 + 109] == 0x04 && f.buf[7 + 110] == 0x04,
          "sync_profile_info protocol IPV4V6=0x04 at payload[109]+[110]");
    CHECK(f.buf[7 + 311] == 0x01, "sync_profile_info auth flag == 0x01");
    CHECK(f.buf[7 + 314] == 0x01, "sync_profile_info pco flag == 0x01");

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
