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

    /* SEC_SIMAPPS_INFO (main=5 sub=15): live EFUJ2 payload from the USIM-only
     * subscription. One application, AID prefix A0000000871002 (USIM), no
     * ISIM. The trailing per-app bytes are ignored. */
    const uint8_t simapps[] = {
        0x01, 0x00, 0x10, 0xa0,0x00,0x00,0x00,0x87,0x10,0x02,0xff,0x31,0xf0,0x01,
        0x89,0x08,0x06,0x00,0x00,0x00, 0x03,0x05,0x05,0x0a,0x0a};
    struct fmt_rx_sim_apps apps;
    assert(fmt_rx_sim_apps(simapps, sizeof simapps, &apps));
    assert(apps.count == 1 && apps.usim == 1 && apps.isim == 0 && apps.csim == 0);
    /* Any truncation that cuts into the AID must fail; the parser ignores
     * trailing per-application bytes, so lengths >= the first AID end parse. */
    for (size_t k = 0; k < 19; k++) assert(!fmt_rx_sim_apps(simapps, k, &apps));
    assert(fmt_rx_sim_apps(simapps, 19, &apps) && apps.usim == 1);
    assert(!fmt_rx_sim_apps(NULL, sizeof simapps, &apps));
    /* Synthetic ISIM-only and USIM+ISIM inventories (no subscriber data). */
    const uint8_t isim_only[] = {
        0x01, 0x00, 0x10, 0xa0,0x00,0x00,0x00,0x87,0x10,0x04,0x00,0x00,0x00,0x00,
        0x00,0x00,0x00,0x00,0x00,0x00};
    assert(fmt_rx_sim_apps(isim_only, sizeof isim_only, &apps));
    assert(apps.count == 1 && apps.isim == 1 && apps.usim == 0);
    /* Build programmatically to keep the two AIDs exactly 16 bytes each. */
    uint8_t both_ok[37]; size_t bo = 0;
    both_ok[bo++] = 0x02;
    both_ok[bo++] = 0x00; both_ok[bo++] = 0x10;
    memcpy(both_ok + bo, (const uint8_t[16]){0xa0,0,0,0,0x87,0x10,0x02,0,0,0,0,0,0,0,0,0}, 16); bo += 16;
    both_ok[bo++] = 0x01; both_ok[bo++] = 0x10;
    memcpy(both_ok + bo, (const uint8_t[16]){0xa0,0,0,0,0x87,0x10,0x04,0,0,0,0,0,0,0,0,0}, 16); bo += 16;
    assert(bo == sizeof both_ok);
    assert(fmt_rx_sim_apps(both_ok, sizeof both_ok, &apps));
    assert(apps.count == 2 && apps.usim == 1 && apps.isim == 1);
    (void)0;
    /* Zero applications and an over-long count are rejected. */
    const uint8_t zero[] = {0x00};
    assert(!fmt_rx_sim_apps(zero, sizeof zero, &apps));
    const uint8_t many[] = {0x11};
    assert(!fmt_rx_sim_apps(many, sizeof many, &apps));

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
    /* Independent synthetic vector from CP 0x41301c56's response writes.
     * sm_GetApn is copied at record+2; compression occupies +123/+124. */
    uint8_t definitions[253] = {2,1,5,'i','n','t','e','r','n','e','t'};
    definitions[124] = 2; definitions[125] = 3;
    definitions[127] = 27; definitions[128] = 6;
    memcpy(definitions+129, "ims", 4);
    struct fmt_rx_pdp_profiles profiles;
    assert(fmt_rx_pdp_profiles(definitions, sizeof definitions, &profiles));
    assert(profiles.count == 2 && profiles.profile[0].cid == 1);
    assert(profiles.profile[0].protocol_wire == 5 && !strcmp(profiles.profile[0].apn,"internet"));
    assert(profiles.profile[0].data_compression == 2 && profiles.profile[0].header_compression == 3);
    assert(profiles.profile[1].cid == 27 && !strcmp(profiles.profile[1].apn,"ims"));
    uint8_t capacity[1387] = {11};
    memcpy(capacity+1,definitions+1,sizeof definitions-1);
    assert(fmt_rx_pdp_profiles(capacity,sizeof capacity,&profiles) && profiles.count == 2);
    capacity[253+50] = 1;
    assert(!fmt_rx_pdp_profiles(capacity,sizeof capacity,&profiles));
    for (size_t n = 0; n < sizeof definitions; n++)
        assert(!fmt_rx_pdp_profiles(definitions,n,&profiles));
    definitions[127] = 1; assert(!fmt_rx_pdp_profiles(definitions,sizeof definitions,&profiles));
    definitions[127] = 28; assert(!fmt_rx_pdp_profiles(definitions,sizeof definitions,&profiles));
    definitions[127] = 27;
    memset(definitions+3,'x',101);
    assert(!fmt_rx_pdp_profiles(definitions,sizeof definitions,&profiles));
    assert(fmt_rx_pdp_profiles(empty,1,&profiles) && !profiles.count);
    assert(!fmt_rx_pdp_profiles(NULL,1,&profiles));
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
    /* P-CSCF offsets recovered from IpcRxIpConfiguration @0x32198c. */
    uint8_t ims_ip[257]={2,0x40}; ims_ip[35]=0x20; ims_ip[36]=1;
    ims_ip[51]=0x20; ims_ip[52]=1; ims_ip[66]=1;
    ims_ip[177]=0x20; ims_ip[178]=1; ims_ip[192]=2;
    assert(fmt_rx_ip(ims_ip,sizeof ims_ip,&v) && v.pcscf6_count==2);
    assert(v.pcscf6[0][15]==1 && v.pcscf6[1][15]==2);
    assert(fmt_rx_ip(ims_ip,192,&v) && v.pcscf6_count==1);
    ims_ip[51]=0xff;
    assert(fmt_rx_ip(ims_ip,sizeof ims_ip,&v) && v.pcscf6_count==1);
    /* Synthetic USIM result. No test material is sent to a physical card. */
    uint8_t aka[50]={2,0,4,1,2,3,4,16}; aka[24]=16; aka[41]=8;
    struct fmt_rx_usim_auth auth;
    assert(fmt_rx_usim_auth(aka,sizeof aka,&auth) && auth.authenticated);
    assert(auth.res==aka+3 && auth.res_len==4 && auth.ck==aka+8 && auth.ik==aka+25);
    for (size_t n=0;n<sizeof aka;n++) assert(!fmt_rx_usim_auth(aka,n,&auth));
    aka[24]=255; assert(!fmt_rx_usim_auth(aka,sizeof aka,&auth)); aka[24]=16;
    aka[0]=0; assert(!fmt_rx_usim_auth(aka,sizeof aka,&auth));
    uint8_t sync[20]={2,4,14};
    assert(fmt_rx_usim_auth(sync,sizeof sync,&auth) && !auth.authenticated && auth.auts_len==14);
    uint8_t reject[]={2,3};
    assert(fmt_rx_usim_auth(reject,sizeof reject,&auth) && !auth.authenticated && !auth.ck);
    /* NET_SERVING_NETWORK (main=8 sub=3): live EFUJ2/KPN frame. Real PLMN is
     * decoded; NO cell id is reported (this CP carries none in IPC41). */
    static const uint8_t serv[] = {
        0x05,0x02,0x21,'2','0','4','0','8',0x23,0x00,0x00,0x00,0x1f,0xf3,
        0x76,0x00,0x6e,0x84,0xff,0x00,0x00,0xff,0x00,0x00,0x1d,0x01
    };
    struct fmt_rx_serving_network sn;
    assert(fmt_rx_serving_network(serv, sizeof serv, &sn));
    assert(sn.plmn_valid && !strcmp(sn.plmn, "20408"));
    assert(!sn.cell_id_valid);
    /* Truncated before the PLMN: still returns true but no plmn/cell id. */
    assert(fmt_rx_serving_network(serv, 7, &sn) && !sn.plmn_valid && !sn.cell_id_valid);
    /* Non-digit PLMN bytes: rejected (no plmn_valid). */
    uint8_t bad[26]; memcpy(bad, serv, sizeof bad); bad[3]='X';
    assert(fmt_rx_serving_network(bad, sizeof bad, &sn) && !sn.plmn_valid);
    /* NULL / zero-length safety. */
    assert(!fmt_rx_serving_network(NULL, 0, &sn));
    assert(fmt_rx_serving_network(serv, 0, &sn) && !sn.plmn_valid);

    /* ---- NET_CELL_INFO_LIST (8/17) decoder: valid / malformed / truncated /
     * unavailable / stale (all synthetic; never real subscriber data). ---- */
    {
        struct fmt_rx_net_cell_info ci;
        /* Helper: build a 1-LTE-record response with a given ECI + gid. */
        for (int variant = 0; variant < 6; variant++) {
            uint8_t buf[40]; size_t n = 12 + 20;
            memset(buf, 0, sizeof buf);
            if (variant != 4) { buf[0] = (uint8_t)(n & 0xff); buf[1] = (uint8_t)(n >> 8); }
            buf[6] = 3;               /* cmd_type = response */
            buf[11] = 1;              /* n_lte = 1 */
            uint8_t *e = buf + 12;
            uint32_t eci = 0x0004bc5a; uint8_t gid = 2;
            if (variant == 0) { /* valid */ }
            else if (variant == 1) { eci = 0; }             /* zero ECI */
            else if (variant == 2) { gid = 3; }             /* wrong class */
            else if (variant == 3) { e[6] = 0xff; e[7] = 0xff; e[8] = 0xff; e[9] = 0x0f; } /* 28-bit max ECI */
            else if (variant == 4) { n = 11; }              /* truncated hdr */
            else if (variant == 5) { buf[11] = 2; }         /* total mismatch */
            e[0] = gid;
            e[1] = 2; e[2] = 0; e[3] = 4;  /* PLMN digits 2,0,4 (MCC 204) */
            if (variant != 3) {
                e[6] = (uint8_t)(eci & 0xff); e[7] = (uint8_t)((eci >> 8) & 0xff);
                e[8] = (uint8_t)((eci >> 16) & 0xff); e[9] = (uint8_t)((eci >> 24) & 0xff);
            }
            e[4] = 0x11; e[5] = 0x22;
            e[10] = 0x2e; e[11] = 0x00;
            memset(&ci, 0xaa, sizeof ci);
            bool r = fmt_rx_net_cell_info(buf, n, NULL, &ci);
            if (variant == 0) {
                assert(r && ci.cell_id_valid && !strcmp(ci.cell_id, "0004bc5a"));
                assert(ci.tac == 0x2211 && ci.pci == 0x002e && ci.lte_count == 1);
            } else if (variant == 3) {
                assert(r && ci.cell_id_valid && !strcmp(ci.cell_id, "0fffffff"));
            } else {
                assert(!ci.cell_id_valid);   /* never fabricate on bad input */
                if (variant == 4) assert(!r);
            }
        }
        /* Empty LTE section: parsed, no cell. */
        uint8_t empty[12] = {12,0,0,0,0,0,3, 0,0,0,0,0};
        memset(&ci, 0xaa, sizeof ci);
        assert(fmt_rx_net_cell_info(empty, sizeof empty, NULL, &ci) && !ci.cell_id_valid);
        /* Multi-LTE: only the gid==2 record is taken. */
        uint8_t multi[12 + 40]; memset(multi, 0, sizeof multi);
        multi[0] = (uint8_t)(sizeof multi); /* total = 52 */
        multi[6] = 3; multi[11] = 2;
        multi[12] = 3; /* first record gid 3 -> skip */
        multi[32] = 2; multi[32+1] = 2; multi[32+2] = 0; multi[32+3] = 4;
        multi[32+6] = 0x78; multi[32+7] = 0x56; /* second: 0x5678 */
        assert(fmt_rx_net_cell_info(multi, sizeof multi, NULL, &ci) && ci.cell_id_valid &&
               !strcmp(ci.cell_id, "00005678"));
        /* Overflow-sized counts are rejected before any multiply. */
        uint8_t huge[12] = {255,255,0,0,0,0,3, 40,40,40,40,16};
        assert(!fmt_rx_net_cell_info(huge, sizeof huge, NULL, &ci));
        /* PLMN sanity: same frame, expect "20408" -> accepted; expect a
         * different MCC -> ECI rejected (stale/foreign cell). */
        uint8_t ok[32]; memset(ok, 0, sizeof ok); ok[0]=32; ok[6]=3; ok[11]=1;
        uint8_t *q = ok+12; q[0]=2; q[1]=2; q[2]=0; q[3]=4;
        q[6]=0x5a; q[7]=0xbc; q[8]=0x04; q[9]=0x00;
        memset(&ci,0xaa,sizeof ci);
        assert(fmt_rx_net_cell_info(ok, sizeof ok, "20408", &ci) &&
               ci.cell_id_valid && ci.plmn_sane && !strcmp(ci.cell_id,"0004bc5a"));
        assert(fmt_rx_net_cell_info(ok, sizeof ok, "20808", &ci) &&
               !ci.cell_id_valid && !ci.plmn_sane);
        /* NULL / short safety. */
        assert(!fmt_rx_net_cell_info(NULL, 0, NULL, &ci));
        assert(!fmt_rx_net_cell_info(empty, 5, NULL, &ci));
    }

    puts("FMT receive bounds, result correlation, RAT, PDP and IP: PASS");
    return 0;
}
