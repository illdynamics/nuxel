/* SPDX-License-Identifier: GPL-2.0-only */
#include "fmt_sms.h"
#include <stdio.h>
#include <string.h>
#include "vendor_sms_vectors.h"
static unsigned failures;
#define CHECK(c) do { if (!(c)) { fprintf(stderr,"FAIL %d: %s\n",__LINE__,#c);failures++; } } while (0)
#define VECTOR(v) CHECK(f.len==sizeof(v) && !memcmp(f.buf,v,sizeof(v)))
int main(void)
{
    struct fmt_tx_frame f;
    const uint8_t *pdu=golden_sms_send_domain_2+11;
    size_t len=sizeof golden_sms_send_domain_2-11;
    CHECK(fmt_sms_send(&f,false,2,pdu,len));VECTOR(golden_sms_send_domain_0);
    CHECK(fmt_sms_send(&f,false,3,pdu,len));VECTOR(golden_sms_send_domain_1);
    CHECK(fmt_sms_send(&f,false,0,pdu,len));VECTOR(golden_sms_send_domain_2);
    CHECK(fmt_sms_send(&f,false,1,pdu,len));VECTOR(golden_sms_send_domain_3);
    CHECK(fmt_sms_send(&f,true,0,pdu,len));VECTOR(golden_sms_send_more);
    CHECK(fmt_sms_ack(&f,0x42,0));VECTOR(golden_sms_ack_ok);
    CHECK(fmt_sms_ack(&f,0x42,0x8016));VECTOR(golden_sms_ack_memory_full);
    CHECK(fmt_sms_get_smsc(&f));VECTOR(golden_sms_get_smsc);
    CHECK(fmt_sms_ready(&f));VECTOR(golden_sms_device_ready);
    CHECK(!fmt_sms_send(&f,false,0,pdu,256));CHECK(!fmt_sms_send(&f,false,4,pdu,len));
    CHECK(!fmt_sms_send(&f,false,8,pdu,len)); /* ModemType is not Domain */
    CHECK(!fmt_sms_send(&f,false,0,NULL,len));CHECK(!fmt_sms_send(NULL,false,0,pdu,len));
    CHECK(!fmt_sms_send(&f,false,0,pdu,0));CHECK(!fmt_sms_ack(&f,1,1));
    uint8_t incoming[]={2,1,0,0,0x42,3,0,1,2};
    struct fmt_sms_incoming rx;
    CHECK(fmt_sms_incoming(incoming,sizeof incoming,&rx));CHECK(rx.reference==0x42 && rx.len==3 && rx.pdu==incoming+6);
    for (size_t i=0;i<sizeof incoming;i++) CHECK(!fmt_sms_incoming(incoming,i,&rx));
    incoming[0]=1;CHECK(!fmt_sms_incoming(incoming,sizeof incoming,&rx));
    uint8_t response[]={2,0x16,0x80,0x42,0};
    struct fmt_sms_submit_result result;
    CHECK(fmt_sms_submit_result(response,sizeof response,&result));CHECK(result.result==0x8016 && result.reference==0x42);
    for (size_t i=0;i<sizeof response;i++) CHECK(!fmt_sms_submit_result(response,i,&result));
    response[4]=1;CHECK(!fmt_sms_submit_result(response,sizeof response,&result));
    uint8_t sca[]={7,0x91,0x21,0x43,0x65,0x87,0x09,0xf1},out[12];size_t n=0;
    CHECK(fmt_sms_smsc(sca,sizeof sca,out,&n));CHECK(n==sizeof sca && !memcmp(sca,out,n));
    uint8_t padded[12];memset(padded,0xff,sizeof padded);memcpy(padded,sca,sizeof sca);
    CHECK(fmt_sms_smsc(padded,sizeof padded,out,&n) && n==sizeof sca && !memcmp(sca,out,n));
    padded[0]=12;CHECK(!fmt_sms_smsc(padded,sizeof padded,out,&n));
    for (size_t i=0;i<sizeof sca;i++) CHECK(!fmt_sms_smsc(sca,i,out,&n));
    sca[3]=0xf1;CHECK(!fmt_sms_smsc(sca,sizeof sca,out,&n));
    sca[0]=0;CHECK(fmt_sms_smsc(sca,1,out,&n) && n==1);
    printf("SMS vendor golden vectors: %s (%u failures)\n",failures ? "FAIL" : "PASS",failures);
    return failures ? 1 : 0;
}
