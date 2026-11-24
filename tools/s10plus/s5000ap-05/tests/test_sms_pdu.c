/* SPDX-License-Identifier: GPL-2.0-only */
#include "sms_pdu.h"
#include <stdio.h>
#include <string.h>
static unsigned failures;
#define CHECK(c) do { if (!(c)) { fprintf(stderr,"FAIL %d: %s\n",__LINE__,#c);failures++; } } while (0)
static size_t hex(const char *s,uint8_t *b)
{
    size_t n=0;unsigned v;
    while (*s && sscanf(s,"%2x",&v)==1) { b[n++]=(uint8_t)v;s+=2; }
    return n;
}
/* A separate envelope converter lets the independent DELIVER decoder check
 * long text packing. Fixed golden PDUs below check interoperability. */
static size_t as_deliver(const struct sms_segment *s,uint8_t *b)
{
    size_t a=2+(s->data[2]+1u)/2;
    b[0]=0;b[1]=s->data[0]&0x40;
    memcpy(b+2,s->data+2,a+2);
    const uint8_t date[]={0x62,0x11,0x42,0x12,0x43,0x65,0x40};
    memcpy(b+4+a,date,7);
    memcpy(b+11+a,s->data+4+a,s->len-4-a);
    return s->len+7;
}
int main(void)
{
    struct sms_encoded e;uint8_t b[SMS_MAX_PDU],gold[SMS_MAX_PDU];
    size_t n=hex("212a0b912143658709f1000005e8329bfd06",gold);
    CHECK(sms_encode("+12345678901","hello",0x2a,1,&e)==SMS_CODEC_OK);
    CHECK(e.count==1 && !e.ucs2 && e.parts[0].len==n && !memcmp(e.parts[0].data,gold,n));
    n=hex("21000b912143658709f10008046f225b57",gold);
    CHECK(sms_encode("+12345678901","漢字",0,1,&e)==SMS_CODEC_OK);
    CHECK(e.count==1 && e.ucs2 && e.parts[0].len==n && !memcmp(e.parts[0].data,gold,n));
    struct sms_decoded d;
    n=hex("00000b912143658709f100006211421243654005e8329bfd06",b);
    CHECK(sms_decode(b,n,&d)==SMS_CODEC_OK);
    CHECK(d.kind==SMS_DELIVER && !strcmp(d.peer,"+12345678901") && !strcmp(d.text,"hello"));
    CHECK(!strcmp(d.timestamp,"2026-11-24T21:34:56+01:00"));
    for (size_t i=0;i<n;i++) {
        memset(&d,0xa5,sizeof d);struct sms_decoded before=d;
        CHECK(sms_decode(b,i,&d)!=SMS_CODEC_OK);CHECK(!memcmp(&d,&before,sizeof d));
    }
    n=hex("00022a0b912143658709f1621142124365406211421243754000",b);
    CHECK(sms_decode(b,n,&d)==SMS_CODEC_OK && d.kind==SMS_STATUS_REPORT && d.reference==0x2a && d.status==0);
    b[n++]=4;CHECK(sms_decode(b,n,&d)==SMS_CODEC_INVALID); /* TP-UDL absent */
    n=hex("00000b912143658709f1000862114212436540046f225b57",b);
    CHECK(sms_decode(b,n,&d)==SMS_CODEC_OK && !strcmp(d.text,"漢字"));
    char longtext[1300],combined[SMS_MAX_TEXT];memset(longtext,'A',sizeof longtext);longtext[160]=0;
    CHECK(sms_encode("+12345678901",longtext,254,0x42,&e)==SMS_CODEC_OK && e.count==1);
    longtext[160]='A';longtext[161]=0;
    CHECK(sms_encode("+12345678901",longtext,254,0x42,&e)==SMS_CODEC_OK && e.count==2);
    combined[0]=0;
    for (size_t i=0;i<e.count;i++) {
        n=as_deliver(&e.parts[i],b);CHECK(sms_decode(b,n,&d)==SMS_CODEC_OK);
        CHECK(d.multipart && d.concat_reference==0x42 && d.total==2 && d.part==i+1);
        strcat(combined,d.text);
    }
    CHECK(!strcmp(combined,longtext));
    memset(longtext,'A',152);strcpy(longtext+152,"^{}[]~|\\€");
    CHECK(sms_encode("+12345678901",longtext,255,0x43,&e)==SMS_CODEC_OK && e.count==2);
    CHECK(e.parts[0].reference==255 && e.parts[1].reference==0);
    combined[0]=0;
    for (size_t i=0;i<e.count;i++) { n=as_deliver(&e.parts[i],b);CHECK(sms_decode(b,n,&d)==SMS_CODEC_OK);strcat(combined,d.text); }
    CHECK(!strcmp(combined,longtext));
    longtext[0]=0;for (unsigned i=0;i<71;i++) strcat(longtext,"漢");
    CHECK(sms_encode("+12345678901",longtext,1,0x44,&e)==SMS_CODEC_OK && e.count==2 && e.ucs2);
    combined[0]=0;
    for (size_t i=0;i<e.count;i++) { n=as_deliver(&e.parts[i],b);CHECK(sms_decode(b,n,&d)==SMS_CODEC_OK);strcat(combined,d.text); }
    CHECK(!strcmp(combined,longtext));
    memset(longtext,'A',sizeof longtext-1);longtext[sizeof longtext-1]=0;
    CHECK(sms_encode("+1",longtext,0,0,&e)==SMS_CODEC_TOO_LONG);
    CHECK(sms_encode("+1","😀",0,0,&e)==SMS_CODEC_UNSUPPORTED);
    CHECK(sms_encode("+1","\xc0\xaf",0,0,&e)==SMS_CODEC_INVALID);
    CHECK(sms_encode("+1","\xed\xa0\x80",0,0,&e)==SMS_CODEC_INVALID);
    CHECK(sms_encode("+1","",0,0,&e)==SMS_CODEC_INVALID);
    CHECK(sms_encode("+1;2","x",0,0,&e)==SMS_CODEC_INVALID);
    CHECK(sms_encode("+123456789012345678901","x",0,0,&e)==SMS_CODEC_INVALID);
    /* Deterministic parser stress, including truncated and arbitrary UDH. */
    uint32_t random=0x43;
    for (unsigned i=0;i<10000;i++) {
        size_t count=i%sizeof b;
        for (size_t j=0;j<count;j++) { random=random*1664525u+1013904223u;b[j]=(uint8_t)(random>>24); }
        (void)sms_decode(b,count,&d);
    }
    printf("SMS codec: %s (%u failures)\n",failures ? "FAIL" : "PASS",failures);
    return failures ? 1 : 0;
}
