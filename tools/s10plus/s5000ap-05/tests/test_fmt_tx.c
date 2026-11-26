/* SPDX-License-Identifier: GPL-2.0-only
 * Protocol regression vectors executed from the matching DTK9 vendor ELF.
 * Byte-for-byte comparison includes all reserved bytes, lengths and headers.
 */
#include "fmt_tx.h"
#include <stdio.h>
#include <string.h>
#include "vendor_data_vectors.h"

static int failures;
#define CHECK(c) do { if (!(c)) { \
    fprintf(stderr, "FAIL %s:%d: %s\n", __FILE__, __LINE__, #c); failures++; \
} } while (0)

static void vector(const struct fmt_tx_frame *f, const uint8_t *v, size_t n,
                   const char *name)
{
    CHECK(f->len == n);
    CHECK(f->main_cmd == v[4] && f->sub_cmd == v[5] && f->cmd_type == v[6]);
    for (size_t i = 0; i < n; i++) {
        if (f->buf[i] != v[i]) {
            fprintf(stderr, "%s: byte %zu: got %02x, vendor %02x\n",
                    name, i, f->buf[i], v[i]);
            failures++;
        }
    }
}
#define VECTOR(v) vector(&f, (v), sizeof(v), #v)

int main(void)
{
    struct fmt_tx_frame f;
    memset(&f, 0xa5, sizeof f);
    CHECK(fmt_tx_set_data_profile(&f, "internet", FMT_TX_AUTH_NONE, FMT_TX_PROTO_IPV4V6));
    VECTOR(golden_profile_enabled_1);
    CHECK(f.buf[7 + 189] == 0); /* APN disabled flag: enabled profile MUST be 0 */
    CHECK(golden_profile_enabled_0[7 + 189] == 1);
    CHECK(memcmp(f.buf, golden_profile_enabled_0, sizeof golden_profile_enabled_0) != 0);
    CHECK(fmt_tx_set_data_profile(&f, "internet", FMT_TX_AUTH_PAP, FMT_TX_PROTO_IPV4V6));
    VECTOR(golden_pap_profile);
    CHECK(fmt_tx_set_data_profile(&f, "internet", FMT_TX_AUTH_PAP_OR_CHAP, FMT_TX_PROTO_IPV4V6));
    VECTOR(golden_pap_profile);

    CHECK(fmt_tx_set_lte_attach_profile(&f, "internet", 0, 4, 1, 1));
    VECTOR(golden_attach_bool_0);
    CHECK(fmt_tx_set_lte_attach_profile(&f, "internet", 0, 4, 1, 3));
    VECTOR(golden_attach_bool_1);
    CHECK(fmt_tx_set_lte_attach_profile(&f, "internet", FMT_TX_AUTH_CHAP, FMT_TX_PROTO_IP, 5, 1));
    VECTOR(golden_chap_attach);
    CHECK(!fmt_tx_set_lte_attach_profile(&f, "internet", 0, 4, 1, 4));
    CHECK(!fmt_tx_set_lte_attach_profile(&f, "internet", 0, 4, 0, 3));
    CHECK(!fmt_tx_set_lte_attach_profile(&f, "internet", 0, 4, 16, 3));

    CHECK(fmt_tx_define_pdp_context(&f, "internet", 4, 1));
    VECTOR(golden_define_pdp);
    CHECK(fmt_tx_define_pdp_context(&f, "internet", FMT_TX_PROTO_IP, 1));
    VECTOR(golden_define_pdp_ipv4);
    CHECK(fmt_tx_set_pdp_context(&f, "internet", 0, 4, 1, FMT_TX_PDP_TYPE_FULL));
    VECTOR(golden_activate_pdp);
    CHECK(fmt_tx_set_pdp_context(&f, "internet", FMT_TX_AUTH_PAP, 4, 1, FMT_TX_PDP_TYPE_FULL));
    VECTOR(golden_pap_activate);
    CHECK(fmt_tx_sync_profile_info(&f, "internet", 0, 4));
    VECTOR(golden_sync_profile);
    CHECK(fmt_tx_set_preferred_net_type(&f, FMT_TX_PREFERRED_NET_LTE_AUTO));
    VECTOR(golden_preferred_lte_auto);
    CHECK(fmt_tx_set_preferred_net_type(&f, FMT_TX_PREFERRED_NET_LTE_ONLY));
    VECTOR(golden_preferred_lte_only);
    CHECK(fmt_tx_get_preferred_net_type(&f)); VECTOR(golden_get_preferred_network);
    CHECK(fmt_tx_get_sim_status(&f)); VECTOR(golden_get_pin_status);
    CHECK(fmt_tx_get_sim_network(&f)); VECTOR(golden_get_sim_network);
    CHECK(fmt_tx_get_baseband_version(&f)); VECTOR(golden_get_baseband);
    CHECK(fmt_tx_radio_power(&f, true)); VECTOR(golden_radio_on);
    CHECK(fmt_tx_radio_power(&f, false)); VECTOR(golden_radio_off);
    CHECK(fmt_tx_net_selection_auto(&f)); VECTOR(golden_select_auto);
    CHECK(fmt_tx_oes_confirm(&f)); VECTOR(golden_oes_confirm);
    CHECK(fmt_tx_oes_certificate(&f, 0, 1, (const uint8_t *)"DER01", 5)); VECTOR(golden_oes_certificate);
    CHECK(fmt_tx_oes_certificate(&f, 1, 0, NULL, 0)); VECTOR(golden_oes_missing);
    CHECK(!fmt_tx_oes_certificate(&f, 0, 0, NULL, 1));
    CHECK(!fmt_tx_oes_certificate(&f, 0, 0, (const uint8_t *)"x", 701));
    CHECK(!fmt_tx_oes_certificate(&f, 1, 0, (const uint8_t *)"x", 1));
    CHECK(!fmt_tx_set_preferred_net_type(&f, 255));

    const uint8_t ps[] = {10,0,0,0,13,3,3,1,0,0};
    CHECK(fmt_tx_ps_attach(&f, true, false, 0)); VECTOR(ps);
    VECTOR(golden_ps_attach);
    CHECK(fmt_tx_ps_attach(&f, false, false, 4)); VECTOR(golden_detach_initial_apn);
    const uint8_t get_ps[] = {7,0,0,0,13,3,2};
    CHECK(fmt_tx_get_ps_attach(&f)); VECTOR(get_ps);
    CHECK(fmt_tx_ps_attach(&f, true, true, 4)); VECTOR(ps);
    const uint8_t detach[] = {10,0,0,0,13,3,3,0,1,4};
    CHECK(fmt_tx_ps_attach(&f, false, true, 4)); VECTOR(detach);
    const uint8_t pdp[] = {7,0,0,0,13,4,2};
    CHECK(fmt_tx_get_pdp_context(&f)); VECTOR(pdp);
    const uint8_t definitions[] = {7,0,0,0,13,1,2};
    CHECK(fmt_tx_get_pdp_definitions(&f)); VECTOR(definitions);
    CHECK(fmt_tx_release_pdp_context(&f, 1)); VECTOR(golden_release_pdp);
    CHECK(!fmt_tx_release_pdp_context(&f, 0));
    CHECK(!fmt_tx_release_pdp_context(&f, 16));
    const uint8_t mob[] = {9,0,0,0,13,29,3,1,1};
    CHECK(fmt_tx_mobile_data(&f, true, true)); VECTOR(mob);
    const uint8_t cdma[] = {8,0,0,0,3,2,3,1};
    CHECK(fmt_tx_set_data_call_establish(&f, true)); VECTOR(cdma);
    const uint8_t always[] = {9,0,0,0,13,34,3,1,1};
    CHECK(fmt_tx_set_always_on_pdn(&f, true, 1)); VECTOR(always);
    const uint8_t reg[] = {9,0,0,0,8,5,2,255,3};
    CHECK(fmt_tx_get_data_reg_state(&f)); VECTOR(reg);
    CHECK(fmt_tx_set_service_domain(&f, FMT_TX_SERVICE_DOMAIN_CS_PS)); VECTOR(golden_domain_cs_ps);
    CHECK(f.buf[7] == 1); /* wire 2 is CS ONLY and must never enable data */
    CHECK(fmt_tx_set_service_domain(&f, FMT_TX_SERVICE_DOMAIN_PS_ONLY)); VECTOR(golden_domain_ps_only);
    CHECK(fmt_tx_set_service_domain(&f, FMT_TX_SERVICE_DOMAIN_CS_ONLY)); VECTOR(golden_domain_cs_only);
    CHECK(!fmt_tx_set_service_domain(&f, 3));
    CHECK(fmt_tx_get_service_domain(&f)); VECTOR(golden_get_service_domain);

    /* NET VoLTE state notification / testmode (source: IpcTxSetVolteStateNotification
     * @0x338578, IpcTxGet/SetVolteTestmode @0x338410/@0x3384c0). Byte-exact. */
    CHECK(fmt_tx_set_volte_state_notification(&f, true)); VECTOR(golden_volte_state_ready);
    CHECK(fmt_tx_set_volte_state_notification(&f, false)); VECTOR(golden_volte_state_not_ready);
    CHECK(fmt_tx_get_volte_testmode(&f)); VECTOR(golden_get_volte_testmode);
    CHECK(fmt_tx_set_volte_testmode(&f, 1)); VECTOR(golden_set_volte_testmode);

    char apn[102]; memset(apn, 'a', sizeof apn); apn[101] = 0;
    CHECK(!fmt_tx_set_data_profile(&f, apn, 0, 4));
    CHECK(!fmt_tx_set_lte_attach_profile(&f, apn, 0, 4, 1, 3));
    CHECK(!fmt_tx_set_pdp_context(&f, apn, 0, 4, 1, 1));
    CHECK(!fmt_tx_define_pdp_context(&f, apn, 4, 1));
    CHECK(!fmt_tx_sync_profile_info(&f, apn, 0, 4));
    apn[100] = 0;
    CHECK(fmt_tx_set_data_profile(&f, apn, 0, 4));
    CHECK(f.buf[7+122] == 0);
    CHECK(!fmt_tx_set_data_profile(NULL, "internet", 0, 4));
    CHECK(!fmt_tx_set_data_profile(&f, NULL, 0, 4));
    CHECK(!fmt_tx_set_data_profile(&f, "", 0, 4));
    CHECK(!fmt_tx_set_data_profile(&f, "internet", 4, 4));

    /* Explicit IMS DataProfile (type 2, label "ims", APN ims...gprs) — the
     * modem-managed IMS/ePDN bearer contract recovered from IpcTxSetDataProfile
     * @0x31ff48 + DataCallList::GetCall(2) in ImsPdnTriggered @0x28f0e0. */
    CHECK(fmt_tx_set_data_profile_ex(&f, "ims.mnc008.mcc204.gprs",
                                     FMT_TX_AUTH_NONE, FMT_TX_PROTO_IPV6,
                                     2u, "ims"));
    /* header: len=203, main=13(GPRS), sub=27, type=3; payload[0]=profile 2 */
    CHECK(f.buf[0] == 0xcb && f.buf[4] == 13 && f.buf[5] == 27 && f.buf[6] == 3);
    CHECK(f.buf[7] == 2);                 /* DataProfile type 2 (IMS/ePDN) */
    CHECK(memcmp(f.buf+8, "ims", 3) == 0); /* profile label "ims" */
    CHECK(f.buf[7+21] == 0x06);           /* IPv6 wire byte */
    CHECK(memcmp(f.buf+7+22, "ims.mnc008.mcc204.gprs", 23) == 0); /* APN (23 bytes, no NUL) */
    /* profile_id is a 1-byte wire value (0 is valid); only label/apn bounds fail */
    CHECK(!fmt_tx_set_data_profile_ex(&f, "ims.mnc008.mcc204.gprs", 0, 3, 2, ""));
    CHECK(!fmt_tx_set_data_profile_ex(&f, "ims.mnc008.mcc204.gprs", 0, 3, 2, NULL));
    CHECK(!fmt_tx_set_data_profile_ex(&f, "ims.mnc008.mcc204.gprs", 0, 3, 2, "toolonglabelxyz"));
    CHECK(!fmt_tx_set_pdp_context(&f, "internet", 0, 4, 0, 1));
    CHECK(!fmt_tx_set_pdp_context(&f, "internet", 0, 4, 1, 9));
    const uint8_t raw[] = {10,0,0,0,13,3,3,0xaa,0xbb,0xcc};
    CHECK(fmt_tx_raw(&f, 13, 3, 3, raw+7, 3)); VECTOR(raw);
    CHECK(!fmt_tx_raw(&f, 13, 3, 3, NULL, 3));
    CHECK(!fmt_tx_raw(&f, 13, 3, 3, raw, FMT_TX_MAX_FRAME));
    CHECK(!fmt_tx_raw(NULL, 13, 3, 3, raw, 3));
    /* MISC IMS SDM (Service Domain Manager) settings — recovered from
     * Ipc41PacketBuilder dispatch (SdmImsMode/SmsFmt/SmsOverIP/Domain/Pcscf). */
    const uint8_t sdm_mode[] = {8,0,0,0,10,32,3,1};
    CHECK(fmt_tx_sdm_ims_mode(&f, FMT_TX_SDM_IMS_MODE_ON)); VECTOR(sdm_mode);
    const uint8_t sdm_fmt[] = {8,0,0,0,10,26,3,0};
    CHECK(fmt_tx_sdm_ims_sms_fmt(&f, 0)); VECTOR(sdm_fmt);
    const uint8_t sdm_oip[] = {8,0,0,0,10,27,3,1};
    CHECK(fmt_tx_sdm_ims_sms_over_ip(&f, 1)); VECTOR(sdm_oip);
    const uint8_t sdm_dom[] = {29,0,0,0,10,28,3,'i','m','s','.','m','n','c','0','0','8','.','m','c','c','2','0','4','.','g','p','r','s'};
    CHECK(fmt_tx_sdm_ims_domain(&f, "ims.mnc008.mcc204.gprs")); VECTOR(sdm_dom);
    const uint8_t sdm_pcscf[] = {8,0,0,0,10,34,3,'x'};
    CHECK(fmt_tx_sdm_pcscf(&f, "x")); VECTOR(sdm_pcscf);
    CHECK(!fmt_tx_sdm_ims_domain(&f, NULL));
    CHECK(!fmt_tx_sdm_ims_domain(&f, ""));
    CHECK(!fmt_tx_sdm_pcscf(&f, NULL));
    CHECK(!fmt_tx_sdm_pcscf(&f, ""));

    printf("FMT vendor golden vectors: %s (%d failures)\n", failures ? "FAIL" : "PASS", failures);
    return failures ? 1 : 0;
}
