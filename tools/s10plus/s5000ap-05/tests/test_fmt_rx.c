/* SPDX-License-Identifier: GPL-2.0-only */
#include "fmt_rx.h"
#include "data_session.h"
#include <assert.h>
#include <stdio.h>
#include <string.h>
#include "vendor_rx_vectors.h"

int main(void)
{
    for (unsigned wire = 0; wire < 256; wire++)
        assert(fmt_rx_reg_state((uint8_t)wire) == golden_registration_states[wire]);
    /* Regression: the actual live wire state 1 is NOT home registration. */
    assert(!fmt_rx_registered(fmt_rx_reg_state(1)));
    assert(fmt_rx_registered(fmt_rx_reg_state(2)));
    assert(fmt_rx_registered(fmt_rx_reg_state(6)));
    assert(!fmt_rx_registered(fmt_rx_reg_state(5)));
    /* Actual rejected CS shape; location identifiers replaced with zero.
     * The reject field follows the cell ID at payload byte 10. */
    uint8_t denied[20] = {3,2,4,0,0,0,0,0,0,0,11};
    struct fmt_rx_registration reg;
    assert(fmt_rx_registration(denied, sizeof denied, &reg));
    assert(reg.domain == 2 && reg.state == 3 && reg.reject_cause == 11);
    assert(!fmt_rx_registered(reg.state));
    for (size_t n = 0; n < sizeof denied; n++) assert(!fmt_rx_registration(denied, n, &reg));
    denied[1] = 0; assert(!fmt_rx_registration(denied, sizeof denied, &reg));
    denied[1] = 3; denied[2] = 2; denied[10] = 0;
    assert(fmt_rx_registration(denied, sizeof denied, &reg) && fmt_rx_registered(reg.state));
    uint8_t version[33] = {1, 'G','9','7','5','F','X','X','S','9','D','T','K','9'};
    char baseband[33];
    assert(fmt_rx_baseband(version, sizeof version, baseband) && !strcmp(baseband, "G975FXXS9DTK9"));
    assert(!fmt_rx_baseband(version, 32, baseband) && !baseband[0]);
    version[4] = '"';
    assert(!fmt_rx_baseband(version, sizeof version, baseband) && !baseband[0]);
    const uint8_t unlocked[] = {0,0}, ready[] = {0x82,0};
    const uint8_t no_sim[] = {0x80,0}, pin[] = {3,1};
    assert(fmt_rx_sim_ready(unlocked, 2) && fmt_rx_sim_ready(ready, 2));
    assert(!fmt_rx_sim_ready(no_sim, 2) && !fmt_rx_sim_ready(pin, 2));
    assert(!fmt_rx_sim_ready(NULL, 2) && !fmt_rx_sim_ready(ready, 1));
    /* Synthetic identifiers only; the parser returns a public network prefix. */
    const uint8_t kpn[] = {15,'2','0','4','0','8','0','0','0','0','0','0','0','0','0','0'};
    char plmn[6];
    assert(fmt_rx_sim_network(kpn, sizeof kpn, plmn) && !strcmp(plmn, "20408"));
    for (size_t n = 0; n < sizeof kpn; n++) {
        assert(!fmt_rx_sim_network(kpn, n, plmn) && plmn[0] == 0);
    }
    uint8_t other[sizeof kpn]; memcpy(other, kpn, sizeof kpn); other[3] = '5';
    assert(!fmt_rx_sim_network(other, sizeof other, plmn) && plmn[0] == 0);
    other[3] = '4'; other[7] = 'x';
    assert(!fmt_rx_sim_network(other, sizeof other, plmn) && plmn[0] == 0);
    const uint8_t success[] = {13,27,3,0,0x80};
    struct fmt_rx_gen r;
    assert(fmt_rx_gen(success, 5, &r) && r.result == 0x8000);
    for (size_t n = 0; n < 5; n++) assert(!fmt_rx_gen(success, n, &r));
    assert(!fmt_rx_gen(NULL, 5, &r));

    struct data_session_ctx c;
    ds_reset(&c, "internet", 1); c.phase = DS_SET_DATA_PROFILE;
    assert(ds_gen_response(&c, success, 5) == DS_GEN_IGNORE);
    ds_expect(&c, 13, 27, 3);
    assert(ds_gen_response(&c, success, 5) == DS_GEN_ACCEPTED);
    const uint8_t old_ack[] = {13,20,3,0,0x80};
    const uint8_t wrong_main[] = {8,27,3,0,0x80};
    const uint8_t wrong_type[] = {13,27,2,0,0x80};
    assert(ds_gen_response(&c, old_ack, 5) == DS_GEN_IGNORE);
    assert(ds_gen_response(&c, wrong_main, 5) == DS_GEN_IGNORE);
    assert(ds_gen_response(&c, wrong_type, 5) == DS_GEN_IGNORE);
    const uint8_t wrong_high[] = {13,27,3,0,0x81};
    assert(ds_gen_response(&c, wrong_high, 5) == DS_GEN_REJECTED);
    assert(c.last_gen_result == 0x8100);
    const uint8_t rejected[] = {13,27,3,1,0x80};
    assert(ds_gen_response(&c, rejected, 5) == DS_GEN_REJECTED);
    ds_step(&c, true, 10);
    assert(ds_gen_response(&c, success, 5) == DS_GEN_IGNORE);
    c.phase = DS_ENABLE_MOBILE_DATA; ds_expect(&c, 13,29,3);
    const uint8_t absent[] = {13,29,3,3,0x80};
    assert(ds_gen_response(&c, absent, 5) == DS_GEN_OPTIONAL_UNSUPPORTED);
    assert(c.mobile_data_unsupported && !c.mobile_data_on);
    c.phase = DS_SET_DATA_PROFILE;
    assert(ds_gen_response(&c, absent, 5) == DS_GEN_REJECTED);

    uint8_t state;
    const uint8_t disconnected[] = {1,1,0};
    assert(fmt_rx_pdp_state(disconnected, 3, 1, &state) && state == 0);
    const uint8_t contexts[] = {3,1,0,5,1,7,11};
    assert(fmt_rx_pdp_state(contexts, 7, 5, &state) && state == 1);
    assert(fmt_rx_pdp_state(contexts, 7, 7, &state) && state == 11);
    assert(fmt_rx_pdp_state(contexts, 7, 4, &state) && state == 0);
    assert(!fmt_rx_pdp_state(contexts, 6, 5, &state));
    const uint8_t empty[] = {0};
    assert(fmt_rx_pdp_state(empty, 1, 1, &state) && state == 0);
    assert(fmt_rx_rat(1) == 16 && !strcmp(fmt_rx_rat_name(1), "GSM"));
    assert(fmt_rx_rat(33) == 14 && !strcmp(fmt_rx_rat_name(33), "LTE"));
    assert(fmt_rx_rat(255) == 0);

    /* Independent IpcRxIpConfiguration offsets; documentation-only IPs. */
    uint8_t ip[156] = {1,0x19,0x20,192,0,2,7,192,0,2,53,198,51,100,53,
                      192,0,2,1,255,255,255,0};
    ip[152] = 0xdc; ip[153] = 5;
    struct fmt_rx_ip v;
    assert(fmt_rx_ip(ip, sizeof ip, &v));
    assert(v.cid == 1 && v.ipv4_valid && !v.ipv6_valid);
    assert(v.ipv4[3] == 7 && v.dns4[0][3] == 53 && v.dns4[1][0] == 198);
    assert(v.gateway4[3] == 1 && v.prefix4 == 24 && v.mtu == 1500);
    for (size_t n = 0; n < sizeof ip; n++) assert(!fmt_rx_ip(ip, n, &v));
    ip[20] = 0x7f; assert(!fmt_rx_ip(ip, sizeof ip, &v)); ip[20] = 255;
    memset(ip+3,0,4); assert(!fmt_rx_ip(ip, sizeof ip, &v));
    ip[1] = 0x40; ip[2] = 0; ip[35]=0x20; ip[36]=1; ip[37]=0x0d; ip[38]=0xb8;
    assert(fmt_rx_ip(ip, sizeof ip, &v) && v.ipv6_valid && !v.ipv4_valid);
    assert(!fmt_rx_ip(ip, 130, &v));
    puts("FMT receive bounds, result correlation, RAT, PDP and IP: PASS");
    return 0;
}
