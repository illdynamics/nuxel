/* SPDX-License-Identifier: GPL-2.0-only */
#include "ims_service.h"
#include <stdio.h>
#include <assert.h>
#include <string.h>
static unsigned writes;
static bool write_capture(const struct fmt_tx_frame *f, uint8_t *seq, void *u)
{
    (void)u; writes++; *seq=(uint8_t)writes;
    assert(f->main_cmd==5 && f->sub_cmd==9 && f->buf[7]==2);
    return true;
}
static unsigned callbacks;
static bool authenticated, failed;
static void auth_done(const struct fmt_rx_usim_auth *r, void *user)
{
    (void)user; callbacks++; failed=!r;
    authenticated=r && r->authenticated;
    if (authenticated) assert(r->res_len==4 && r->ck && r->ik);
}
static void test_identity(void)
{
    struct ims_identity id;
    const uint8_t imsi[]="234150999999999"; /* TS 23.003 example, not a subscriber */
    assert(ims_identity_from_usim(&id,imsi,15,2));
    assert(!strcmp(id.impi,"234150999999999@ims.mnc015.mcc234.3gppnetwork.org"));
    assert(!strcmp(id.impu,"sip:234150999999999@ims.mnc015.mcc234.3gppnetwork.org"));
    assert(ims_identity_from_usim(&id,imsi,15,3));
    assert(!strcmp(id.domain,"ims.mnc150.mcc234.3gppnetwork.org"));
    assert(!ims_identity_from_usim(&id,imsi,15,0) && !id.ready && !id.impi[0]);
    assert(!ims_identity_from_usim(&id,(const uint8_t *)"23415x",6,2));
    assert(!ims_identity_from_usim(&id,imsi,16,2));
    assert(!ims_identity_from_usim(&id,NULL,15,2));
    assert(!ims_identity_from_usim(&id,imsi,5,2));
    ims_identity_clear(&id);
    for (size_t i=0;i<sizeof id;i++) assert(!((uint8_t *)&id)[i]);
}
static void test_auth(void)
{
    struct ims_service s;
    uint8_t rand[16]={0}, autn[16]={0}; /* synthetic, never sent to a SIM */
    assert(ims_service_open(&s,write_capture,NULL,NULL));
    assert(!ims_service_auth_request(&s,rand,autn,0,auth_done,NULL));
    ims_service_tick(&s,0,true,false);
    assert(ims_service_auth_request(&s,rand,autn,1,auth_done,NULL));
    assert(!ims_service_auth_request(&s,rand,autn,2,auth_done,NULL));
    uint8_t response[50]={2,0,4,1,2,3,4,16};
    response[24]=16; response[41]=8;
    struct nuxel_sipc_fmt f={.main_cmd=5,.sub_cmd=9,.cmd_type=2,
        .ack_seq=(uint8_t)(s.last_write_seq+1),.payload=response,.payload_len=sizeof response};
    ims_service_receive(&s,&f); assert(s.auth_pending && !callbacks);
    f.ack_seq=s.last_write_seq; f.cmd_type=3;
    ims_service_receive(&s,&f); assert(s.auth_pending && !callbacks);
    f.cmd_type=2;
    ims_service_receive(&s,&f); assert(!s.auth_pending && callbacks==1 && authenticated);
    assert(!ims_service_registered(&s));
    ims_service_receive(&s,&f); assert(callbacks==1); /* stale result */
    assert(ims_service_auth_request(&s,rand,autn,2,auth_done,NULL));
    unsigned sent=writes;
    ims_service_tick(&s,15001,true,false); assert(s.auth_pending);
    ims_service_tick(&s,15002,true,false); assert(!s.auth_pending && callbacks==2 && failed);
    ims_service_tick(&s,30000,true,false); assert(writes==sent); /* no blind retry */
    assert(ims_service_auth_request(&s,rand,autn,30001,auth_done,NULL));
    const uint8_t example[]="234150999999999";
    assert(ims_identity_from_usim(&s.identity,example,15,2));
    ims_service_tick(&s,30002,false,false);
    assert(!s.auth_pending && failed && !s.identity.ready && !s.identity.impi[0]);
    ims_service_close(&s);
}
int main(void)
{
    struct ims_service s;
    assert(ims_service_open(&s, write_capture, NULL, NULL));
    assert(ims_service_tick(&s, 0, true, false) == IMS_WAIT_BACKEND);
    /* Neither profile sync nor attachment starts REGISTER by reporting an
     * invented registered status. No time-based retry can release SMS. */
    for (unsigned t=1; t<100000; t+=1000) {
        assert(ims_service_tick(&s, t, true, true) == IMS_WAIT_BACKEND);
        assert(!ims_service_registered(&s) && writes==0);
    }
    assert(ims_service_tick(&s, 100001, false, false)==IMS_IDLE);
    assert(!ims_service_registered(&s) && writes==0);
    ims_service_close(&s);
    test_identity(); test_auth();
    puts("test_ims_service OK");
    return 0;
}
