/* SPDX-License-Identifier: GPL-2.0-only */
#include "ims_sms.h"
#include <assert.h>
#include <stdio.h>
int main(void)
{
    uint8_t out[300],sc[]={3,0x91,0x21,0xf3},tp[]={1,9,0};
    size_t n=ims_rp_submit(out,sizeof out,77,sc,sizeof sc,tp,sizeof tp);
    struct ims_rp r;
    assert(n && ims_rp_decode(out,n,&r) && r.type==0 && r.reference==77);
    assert(r.destination_len==3 && r.origin_len==0 && r.tpdu_len==3);
    for (size_t k=0;k<n;k++) assert(!ims_rp_decode(out,k,&r));
    assert(!ims_rp_decode(out,n+1,&r));
    assert(!ims_rp_submit(out,2,0,sc,sizeof sc,tp,sizeof tp));
    n=ims_rp_reply(out,77,0);assert(n==2 && ims_rp_decode(out,n,&r) && r.type==2);
    n=ims_rp_reply(out,77,111);assert(n==4 && ims_rp_decode(out,n,&r) && r.cause==111);
    uint8_t ack[]={3,77,0x41,1,1};assert(ims_rp_decode(ack,sizeof ack,&r));
    ack[2]=0;assert(!ims_rp_decode(ack,sizeof ack,&r));
    puts("IMS RP bounds/encapsulation: PASS");
}
