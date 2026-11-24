/* SPDX-License-Identifier: GPL-2.0-only */
#include "sms_service.h"
#include <stdio.h>
#include <string.h>
static unsigned failures;
#define CHECK(c) do { if (!(c)) { fprintf(stderr,"FAIL %d: %s\n",__LINE__,#c);failures++; } } while (0)
struct mock { struct fmt_tx_frame last;uint8_t seq;unsigned writes,notifications;struct sms_service *service;bool fail; };
static bool write_frame(const struct fmt_tx_frame *f,uint8_t *seq,void *user)
{
    struct mock *m=user;m->last=*f;*seq=m->seq++;m->writes++;
    if (f->main_cmd==4 && f->sub_cmd==1) {
        struct sms_record record;
        CHECK(sms_store_get(&m->service->store,m->service->job.id,&record));CHECK(!strcmp(record.state,"sending"));
    }
    if (f->main_cmd==4 && f->sub_cmd==6 && f->buf[8]==0 && f->buf[9]==0) {
        uint32_t ids[10];CHECK(sms_store_list(&m->service->store,ids,10)>0);
    }
    return !m->fail;
}
static void changed(uint32_t id,bool incoming,void *user)
{ (void)id;(void)incoming;((struct mock *)user)->notifications++; }
static void receive(struct sms_service *s,uint8_t main,uint8_t sub,uint8_t type,uint8_t ack,const uint8_t *p,size_t n)
{
    struct nuxel_sipc_fmt f={.main_cmd=main,.sub_cmd=sub,.cmd_type=type,.ack_seq=ack,.payload=p,.payload_len=(uint32_t)n};
    sms_service_receive(s,&f);
}
int main(void)
{
    struct sms_service s;struct mock m={.service=&s};
    CHECK(sms_service_open(&s,":memory:",write_frame,changed,&m));
    sms_service_tick(&s,100,true,true,true,true);CHECK(m.last.sub_cmd==7 && s.ready_sent);
    const uint8_t ack[]={4,7,3,0,0x80};receive(&s,128,1,2,s.ready_sequence,ack,sizeof ack);CHECK(s.ready_ack);
    sms_service_tick(&s,1100,true,true,true,true);CHECK(m.last.sub_cmd==10);
    const uint8_t smsc[]={0};receive(&s,4,10,2,0,smsc,1);CHECK(s.smsc_len==1);
    uint32_t id;CHECK(sms_store_queue(&s.store,"+12345678901","hello",&id));
    sms_service_tick(&s,1200,true,true,true,true);CHECK(m.last.sub_cmd==1 && s.active);
    uint8_t submit[]={2,0,0,0,0};submit[3]=s.job.pdu.reference;
    receive(&s,4,1,2,(uint8_t)(s.sequence+1),submit,sizeof submit);CHECK(s.active && s.unmatched==1);
    receive(&s,4,1,2,s.sequence,submit,sizeof submit);CHECK(!s.active);
    struct sms_record record;CHECK(sms_store_get(&s.store,id,&record) && !strcmp(record.state,"submitted"));
    CHECK(sms_store_queue(&s.store,"+12345678901","timeout",&id));
    sms_service_tick(&s,1300,true,true,true,true);CHECK(s.active);
    unsigned writes=m.writes;
    sms_service_tick(&s,121300,true,true,true,true);CHECK(!s.active && s.blocked);
    CHECK(sms_store_get(&s.store,id,&record) && !strcmp(record.state,"unknown"));
    CHECK(sms_store_queue(&s.store,"+12345678901","held",&id));
    sms_service_tick(&s,121400,true,true,true,true);CHECK(m.writes==writes);
    const uint8_t pdu[]={0,0,11,0x91,0x21,0x43,0x65,0x87,0x09,0xf1,0,0,0x62,0x11,0x42,0x12,0x43,0x65,0x40,5,0xe8,0x32,0x9b,0xfd,6};
    uint8_t incoming[6+sizeof pdu]={2,1,0,0,42,sizeof pdu};memcpy(incoming+6,pdu,sizeof pdu);
    receive(&s,4,2,3,0,incoming,sizeof incoming);CHECK(m.last.sub_cmd==6 && m.last.buf[8]==0 && m.last.buf[9]==0);
    unsigned notifications=m.notifications;
    receive(&s,4,2,3,0,incoming,sizeof incoming);CHECK(m.notifications==notifications);
    incoming[6+sizeof pdu-1]=0x07;
    CHECK(sqlite3_exec(s.store.db,"PRAGMA query_only=ON",NULL,NULL,NULL)==SQLITE_OK);
    receive(&s,4,2,3,0,incoming,sizeof incoming);CHECK(m.last.buf[8]==0x16 && m.last.buf[9]==0x80 && s.store_errors==1);
    sms_service_close(&s);
    printf("SMS service durability/correlation: %s (%u failures)\n",failures ? "FAIL" : "PASS",failures);
    return failures ? 1 : 0;
}
