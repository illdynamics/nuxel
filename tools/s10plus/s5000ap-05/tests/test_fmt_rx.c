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
    assert(reg.lac_tac == 0);   /* denied[4]=denied[5]=0 */
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

    /* Synthetic vendor-verified LTE record; both old and NR-capable forms. */
    {
        uint8_t old[35]={0,0,1,0,1,'0','0','1','0','1','#',
                        0x67,0x45,0x23,1,0x2d,1,0,0,0x56,0x34,0x14,5};
        struct fmt_rx_net_cell_info ci;
        assert(fmt_rx_net_cell_info(old,sizeof old,"00101",&ci));
        assert(ci.cell_id_valid && !strcmp(ci.cell_id,"1234567"));
        assert(ci.tac==0x3456 && ci.pci==301 && ci.earfcn==1300);
        assert(fmt_rx_cell_current(&ci,"00101",true,1000,31000));
        assert(!fmt_rx_cell_current(&ci,"00101",true,1000,31001));
        assert(!fmt_rx_cell_current(&ci,"00101",true,1000,999));
        assert(!fmt_rx_cell_current(&ci,"00101",false,1000,1001));
        assert(!fmt_rx_cell_current(&ci,"00102",true,1000,1001));
        uint8_t newer[36]={0,0,1,0,0}; memcpy(newer+5,old+4,31);
        assert(fmt_rx_net_cell_info(newer,sizeof newer,"00101",&ci) && ci.cell_id_valid);
        for(size_t n=0;n<sizeof old;n++) {
            assert(!fmt_rx_net_cell_info(old,n,"00101",&ci));
            assert(!ci.cell_id_valid);
        }
        assert(fmt_rx_net_cell_info(old,sizeof old,"00102",&ci) && !ci.cell_id_valid);
        uint8_t bad[35]; memcpy(bad,old,35);bad[4]=0;
        assert(fmt_rx_net_cell_info(bad,35,NULL,&ci) && !ci.cell_id_valid);
        bad[4]=2; assert(!fmt_rx_net_cell_info(bad,35,NULL,&ci));
        memcpy(bad,old,35);bad[14]=0x81; /* invalid high ECI bits, never mask */
        assert(fmt_rx_net_cell_info(bad,35,NULL,&ci) && !ci.cell_id_valid);
        memcpy(bad,old,35);bad[10]='2';
        assert(fmt_rx_net_cell_info(bad,35,"001012",&ci) && ci.cell_id_valid);
        bad[5]='X';assert(!fmt_rx_net_cell_info(bad,35,NULL,&ci));
        uint8_t multi[66]={0,0,2,0};memcpy(multi+4,old+4,31);memcpy(multi+35,old+4,31);
        assert(!fmt_rx_net_cell_info(multi,66,NULL,&ci) && !ci.cell_id_valid);
        multi[4]=0;assert(fmt_rx_net_cell_info(multi,66,NULL,&ci) && ci.cell_id_valid);
        uint8_t mixed[75]={1,1,1,0};memcpy(mixed+44,old+4,31);
        assert(fmt_rx_net_cell_info(mixed,75,NULL,&ci) && ci.cell_id_valid);
        uint8_t empty[4]={255,0,0,255};
        assert(fmt_rx_net_cell_info(empty,4,NULL,&ci) && !ci.cell_id_valid);
        assert(!fmt_rx_net_cell_info(NULL,4,NULL,&ci));
    }

    /* Live EFUJ2 8/5 PS-home frame (this CP's live bytes): domain=3,
     * state_wire=2 -> state 1 (REGISTERED_HOME), reject 0, LAC/TAC [4..5]=0. */
    {
        const uint8_t ps_home[] = {0x21,0x03,0x02,0x00,0x00,0x00,0x1f,0xf3,
                                   0x76,0x00,0x00,0x6e,0x84,0x01,0x01,0x00,
                                   0x1d,0x01,0x00,0x00};
        struct fmt_rx_registration r2;
        assert(fmt_rx_registration(ps_home, sizeof ps_home, &r2));
        assert(r2.domain == 3 && r2.state == 1 && fmt_rx_registered(r2.state));
        assert(r2.reject_cause == 0 && r2.lac_tac == 0x0000);
    }
    /* Synthetic non-zero LAC/TAC extraction at [4..5]. */
    {
        uint8_t f[20] = {0x21,0x03,0x02,0x00,0x34,0x12, 0};
        struct fmt_rx_registration r2;
        assert(fmt_rx_registration(f, sizeof f, &r2) && r2.lac_tac == 0x1234);
    }

    puts("FMT receive bounds, result correlation, RAT, PDP and IP: PASS");
    return 0;
}
