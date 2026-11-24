/* SPDX-License-Identifier: GPL-2.0-only */
#include "call_service.h"
#include <stdio.h>
#include <string.h>
static unsigned failures;
#define CHECK(c) do { if(!(c)) { fprintf(stderr,"FAIL %d: %s\n",__LINE__,#c);failures++; } } while(0)
struct mock { unsigned seq,writes,incoming,notifications;char state[24]; };
static bool write_frame(const struct fmt_tx_frame *f,uint8_t *seq,void *user)
{ (void)f;struct mock *m=user;*seq=(uint8_t)m->seq++;m->writes++;return true; }
static void notify(uint8_t id,const char *state,bool incoming,void *user)
{ (void)id;struct mock *m=user;m->notifications++;snprintf(m->state,sizeof m->state,"%s",state);if(incoming)m->incoming++; }
static void rx(struct call_service *s,uint8_t main,uint8_t sub,uint8_t type,uint8_t ack,const uint8_t *p,size_t n)
{ struct nuxel_sipc_fmt f={.main_cmd=main,.sub_cmd=sub,.cmd_type=type,.ack_seq=ack,.payload=p,.payload_len=(uint32_t)n};call_service_receive(s,&f); }
int main(void)
{
    struct call_service s;struct mock m={0};call_service_init(&s,write_frame,notify,&m);
    CHECK(!call_service_dial(&s,"+12345678901",0));
    call_service_tick(&s,1,true,true);CHECK(s.query_pending);
    uint8_t empty[]={0};rx(&s,2,6,2,s.query_sequence,empty,1);CHECK(s.list_valid);
    CHECK(call_service_dial(&s,"+12345678901",100));CHECK(!call_service_dial(&s,"+12345678901",101));
    uint8_t ack[]={2,1,1,0,0x80};rx(&s,128,1,2,(uint8_t)(s.sequence+1),ack,5);CHECK(s.pending);
    rx(&s,128,1,2,s.sequence,ack,5);CHECK(!s.pending && s.result==0x8000 && s.list.count==0);
    call_service_tick(&s,200,true,true);
    uint8_t incoming[]={1,0,1,3,2,5,0,0,0};
    rx(&s,2,6,2,s.query_sequence,incoming,sizeof incoming);CHECK(m.incoming==1 && !strcmp(m.state,"incoming"));
    CHECK(!call_service_dial(&s,"+12345678901",300));CHECK(call_service_answer(&s,300));
    call_service_tick(&s,30300,true,true);CHECK(!s.pending && s.result==-2);
    CHECK(call_service_hangup(&s,30400));
    ack[1]=3;rx(&s,128,1,2,s.sequence,ack,5);
    call_service_tick(&s,30500,true,true);rx(&s,2,6,2,s.query_sequence,empty,1);CHECK(!strcmp(m.state,"ended"));
    call_service_tick(&s,30600,false,false);CHECK(!s.list_valid);
    /* A lost/malformed observation must invalidate an active UI/audio route,
     * without inventing remote termination or repeatedly ringing. */
    call_service_tick(&s,31000,true,true);
    incoming[5]=1;
    rx(&s,2,6,2,s.query_sequence,incoming,sizeof incoming);
    CHECK(s.list_valid && !strcmp(m.state,"active"));
    call_service_tick(&s,32000,true,true);
    call_service_tick(&s,33000,true,true);
    call_service_tick(&s,38000,true,true);
    CHECK(!s.list_valid && !s.list.count && !strcmp(m.state,"unknown"));
    unsigned notices=m.notifications;
    call_service_tick(&s,39000,true,true);
    CHECK(m.notifications==notices);
    call_service_tick(&s,43000,true,true);
    rx(&s,2,6,2,s.query_sequence,incoming,sizeof incoming);
    CHECK(s.list_valid && !strcmp(m.state,"active"));
    call_service_tick(&s,44000,true,true);
    call_service_tick(&s,45000,true,true);
    rx(&s,2,6,2,s.query_sequence,incoming,2);
    CHECK(!s.list_valid && !strcmp(m.state,"unknown"));
    CHECK(!call_service_dial(&s,"+12345678901",104001));
    printf("Call service correlation/lifecycle: %s (%u failures)\n",failures ? "FAIL" : "PASS",failures);return failures ? 1 : 0;
}
