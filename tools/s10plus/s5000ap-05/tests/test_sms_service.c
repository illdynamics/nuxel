/* SPDX-License-Identifier: GPL-2.0-only */
#include "sms_service.h"
#include <stdio.h>
#include <string.h>
static unsigned failures;
#define CHECK(c) do { if (!(c)) { fprintf(stderr,"FAIL %d: %s\n",__LINE__,#c);failures++; } } while (0)
struct mock { struct fmt_tx_frame last;uint8_t seq;unsigned writes,notifications;struct sms_service *service;bool fail;
              struct sms_submit_result_diag diag;char state[32];unsigned diags;
              unsigned ims_calls;bool ims_ok;char ims_peer[64];uint8_t ims_tpdu[256];size_t ims_tpdu_len;uint8_t ims_mr; };
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
static void diag(const struct sms_submit_result_diag *d,void *user)
{ struct mock *m=user;m->diag=*d;snprintf(m->state,sizeof m->state,"%s",d->state ? d->state : "");m->diag.state=m->state;m->diags++; }
static bool ims_submit(const char *peer,const uint8_t *tpdu,size_t tpdu_len,uint8_t mr,void *user)
{
    struct mock *m=user;m->ims_calls++;
    snprintf(m->ims_peer,sizeof m->ims_peer,"%s",peer);
    if (tpdu_len>sizeof m->ims_tpdu) return false;
    memcpy(m->ims_tpdu,tpdu,tpdu_len);m->ims_tpdu_len=tpdu_len;m->ims_mr=mr;
    return m->ims_ok;
}
static void receive(struct sms_service *s,uint8_t main,uint8_t sub,uint8_t type,uint8_t ack,const uint8_t *p,size_t n)
{
    struct nuxel_sipc_fmt f={.main_cmd=main,.sub_cmd=sub,.cmd_type=type,.ack_seq=ack,.payload=p,.payload_len=(uint32_t)n};
    sms_service_receive(s,&f);
}
int main(void)
{
    struct sms_service s;struct mock m={.service=&s};
    CHECK(sms_service_open(&s,":memory:",write_frame,changed,&m));
    sms_service_set_result_diag(&s,diag);
    sms_service_tick(&s,100,true,true,true,false,true);CHECK(m.last.sub_cmd==7 && s.ready_sent);
    const uint8_t ack[]={4,7,3,0,0x80};receive(&s,128,1,2,s.ready_sequence,ack,sizeof ack);CHECK(s.ready_ack);
    sms_service_tick(&s,1100,true,true,true,false,true);CHECK(m.last.sub_cmd==10);
    const uint8_t smsc[]={0};receive(&s,4,10,2,0,smsc,1);CHECK(s.smsc_len==1);
    uint32_t id;CHECK(sms_store_queue(&s.store,"+12345678901","hello",&id));
    /* An IMS registration flag cannot reroute the CP writer to the AP IMS
     * transport. In particular it must not send payload domain 8. */
    unsigned before_ims=m.writes;
    sms_service_tick(&s,1150,true,true,false,true,true);
    CHECK(m.writes==before_ims && !s.active);
    struct sms_record held;
    CHECK(sms_store_get(&s.store,id,&held) && !strcmp(held.state,"queued"));
    sms_service_tick(&s,1200,true,true,true,false,true);CHECK(m.last.sub_cmd==1 && s.active);
    uint8_t submit[]={2,0,0,0,0};submit[3]=s.job.pdu.reference;
    /* Wrong ack_seq is unmatched (still active, no submit). */
    receive(&s,4,1,2,(uint8_t)(s.sequence+1),submit,sizeof submit);CHECK(s.active && s.unmatched==1);
    /* Correct ack_seq + correct reference correlates and marks submitted. */
    receive(&s,4,1,2,s.sequence,submit,sizeof submit);CHECK(!s.active);
    CHECK(m.diags && m.diag.correlated && m.diag.cmd_type==2 && m.diag.result_code==0
          && m.diag.modem_ref==s.job.pdu.reference && m.diag.state && !strcmp(m.diag.state,"submitted"));
    struct sms_record record;CHECK(sms_store_get(&s.store,id,&record) && !strcmp(record.state,"submitted"));

    /* Type-3 is decoded/retained, but even equal MR is NOT a correlation token. */
    CHECK(sms_store_queue(&s.store,"+12345678901","notify",&id));
    sms_service_tick(&s,1210,true,true,true,false,true);CHECK(s.active);
    unsigned d0=m.diags;
    uint8_t notify_submit[]={2,0,0,0,0};notify_submit[3]=s.job.pdu.reference;
    receive(&s,4,1,3,0,notify_submit,sizeof notify_submit);CHECK(s.active);
    CHECK(sms_store_get(&s.store,id,&record) && !strcmp(record.state,"sending"));
    CHECK(m.diags==d0+1 && !m.diag.correlated && m.diag.cmd_type==3 && m.diag.ack_seq==0);
    receive(&s,4,1,2,s.sequence,notify_submit,sizeof notify_submit);CHECK(!s.active);
    CHECK(sms_store_get(&s.store,id,&record) && !strcmp(record.state,"submitted"));

    /* Unsuccessful type-2 result (raw 0x8016) marks the segment failed. */
    CHECK(sms_store_queue(&s.store,"+12345678901","reject",&id));
    sms_service_tick(&s,1220,true,true,true,false,true);CHECK(s.active);
    uint8_t reject[]={2,0x16,0x80,0,0};reject[3]=s.job.pdu.reference;
    receive(&s,4,1,2,s.sequence,reject,sizeof reject);CHECK(!s.active);
    CHECK(sms_store_get(&s.store,id,&record) && !strcmp(record.state,"failed"));
    CHECK(m.diag.correlated && m.diag.cmd_type==2 && m.diag.result_code==0x8016 && m.diag.state && !strcmp(m.diag.state,"failed"));

    /* Malformed notification (bad structure) increments decode errors, never submits. */
    CHECK(sms_store_queue(&s.store,"+12345678901","malformed",&id));
    sms_service_tick(&s,1230,true,true,true,false,true);CHECK(s.active);
    unsigned de=s.decode_errors;
    uint8_t malformed[]={9,0,0,0,0};receive(&s,4,1,3,0,malformed,sizeof malformed);
    CHECK(s.active && s.decode_errors==de+1);

    /* Stale type-3 notification for the in-flight segment but wrong reference
     * is rejected without consuming the active segment. */
    uint8_t wrong_ref3[]={2,0,0,0,0};wrong_ref3[3]=(uint8_t)(s.job.pdu.reference+1);
    unsigned un=s.unmatched;
    receive(&s,4,1,3,0,wrong_ref3,sizeof wrong_ref3);CHECK(s.active && s.unmatched==un+1);
    receive(&s,4,1,3,9,submit,sizeof submit);CHECK(s.active);
    receive(&s,4,9,3,0,submit,sizeof submit);CHECK(s.active);
    receive(&s,4,1,3,0,submit,4);CHECK(s.active);
    uint8_t bad_len[]={2,0,0,0,1};receive(&s,4,1,3,0,bad_len,sizeof bad_len);CHECK(s.active);
    /* A delayed previously accepted notification cannot resolve this job. */
    receive(&s,4,1,3,0,notify_submit,sizeof notify_submit);CHECK(s.active);
    /* A decoded unsuccessful NOTIFICATION is retained without false attribution. */
    uint8_t good3[]={2,0x16,0x80,0,0};good3[3]=s.job.pdu.reference;
    receive(&s,4,1,3,0,good3,sizeof good3);CHECK(s.active);
    CHECK(m.diag.result_code==0x8016 && !m.diag.correlated);
    receive(&s,4,1,2,s.sequence,good3,sizeof good3);CHECK(!s.active);
    CHECK(sms_store_get(&s.store,id,&record) && !strcmp(record.state,"failed"));
    unsigned duplicates=s.unmatched;
    receive(&s,4,1,3,0,good3,sizeof good3);CHECK(s.unmatched==duplicates+1 && !m.diag.correlated);

    CHECK(sms_store_queue(&s.store,"+12345678901","timeout",&id));
    sms_service_tick(&s,1300,true,true,true,false,true);CHECK(s.active);
    /* Actual EFUJ2 Round02 shape: result2, returned MR157, no result PDU.
     * Incoming code is not a standardized carrier cause and does not echo MR. */
    uint8_t efuj2[]={2,2,0,157,0};
    receive(&s,4,1,3,0,efuj2,sizeof efuj2);
    CHECK(s.active && !m.diag.correlated && m.diag.result_code==2 && m.diag.modem_ref==157);
    sqlite3_stmt *receipt=NULL;
    CHECK(sqlite3_prepare_v2(s.store.db,"SELECT result,mr,correlated,state FROM submission_results ORDER BY id DESC LIMIT 1",-1,&receipt,NULL)==SQLITE_OK);
    CHECK(sqlite3_step(receipt)==SQLITE_ROW && sqlite3_column_int(receipt,0)==2 &&
          sqlite3_column_int(receipt,1)==157 && !sqlite3_column_int(receipt,2) &&
          !strcmp((const char *)sqlite3_column_text(receipt,3),"sending"));
    sqlite3_finalize(receipt);
    unsigned writes=m.writes;
    sms_service_tick(&s,121300,true,true,true,false,true);CHECK(!s.active && s.blocked);
    CHECK(sms_store_get(&s.store,id,&record) && !strcmp(record.state,"unknown"));
    CHECK(sms_store_queue(&s.store,"+12345678901","held",&id));
    sms_service_tick(&s,121400,true,true,true,false,true);CHECK(m.writes==writes);
    /* Resolving the unknown timeout message clears the block and lets the
     * next queued message transmit; it does not resend the resolved one. */
    CHECK(sms_service_resolve(&s,s.job.id,"superseded"));CHECK(!s.blocked);
    struct sms_record resolved;CHECK(sms_store_get(&s.store,s.job.id,&resolved) && !strcmp(resolved.state,"unknown"));
    sms_service_tick(&s,121500,true,true,true,false,true);CHECK(m.writes==writes+1);
    const uint8_t pdu[]={0,0,11,0x91,0x21,0x43,0x65,0x87,0x09,0xf1,0,0,0x62,0x11,0x42,0x12,0x43,0x65,0x40,5,0xe8,0x32,0x9b,0xfd,6};
    uint8_t incoming[6+sizeof pdu]={2,1,0,0,42,sizeof pdu};memcpy(incoming+6,pdu,sizeof pdu);
    receive(&s,4,2,3,0,incoming,sizeof incoming);CHECK(m.last.sub_cmd==6 && m.last.buf[8]==0 && m.last.buf[9]==0);
    unsigned notifications=m.notifications;
    receive(&s,4,2,3,0,incoming,sizeof incoming);CHECK(m.notifications==notifications);
    incoming[6+sizeof pdu-1]=0x07;
    CHECK(sqlite3_exec(s.store.db,"PRAGMA query_only=ON",NULL,NULL,NULL)==SQLITE_OK);
    receive(&s,4,2,3,0,incoming,sizeof incoming);CHECK(m.last.buf[8]==0x16 && m.last.buf[9]==0x80 && s.store_errors==1);
    /* ---- SMS-over-IMS dispatch (transport-independent hook) ----
     * With CS unavailable but IMS registered AND an ims_submit hook set, the
     * service must hand the PURE TPDU (no SMSC prefix) to the hook, never the
     * CP FMT writer, and only dequeue when a transport is genuinely ready. */
    {
        struct sms_service is; struct mock im={.service=&is};
        CHECK(sms_service_open(&is,":memory:",write_frame,changed,&im));
        sms_service_set_ims_submit(&is,ims_submit);
        /* CP readiness handshake still runs so the store is armed. */
        sms_service_tick(&is,100,true,true,false,false,true);
        const uint8_t ackc[]={4,7,3,0,0x80};receive(&is,128,1,2,is.ready_sequence,ackc,sizeof ackc);
        const uint8_t smscc[]={0};receive(&is,4,10,2,0,smscc,1);
        uint32_t iid;CHECK(sms_store_queue(&is.store,"+12345678901","ims hello",&iid));
        /* Not registered: held, no IMS call. */
        sms_service_tick(&is,200,true,true,false,false,true);
        CHECK(im.ims_calls==0 && !is.active);
        /* Registered + hook present, hook OK: dispatched, message -> sending. */
        im.ims_ok=true;
        unsigned iw_before=im.writes;
        sms_service_tick(&is,300,true,true,false,true,true);
        CHECK(im.ims_calls==1 && is.active);
        CHECK(im.ims_tpdu_len>0 && im.ims_tpdu_len==is.job.pdu.len);
        CHECK(im.ims_tpdu[0]==is.job.pdu.data[0]); /* pure TPDU, no SMSC */
        CHECK(!strcmp(im.ims_peer,"+12345678901"));
        struct sms_record ir;CHECK(sms_store_get(&is.store,iid,&ir) && !strcmp(ir.state,"sending"));
        CHECK(im.writes==iw_before); /* never went through the CP FMT writer */
        /* A refused MESSAGE (send failed) requeues the part, no fake success. */
        uint8_t ref=is.job.pdu.reference;
        sms_service_close(&is);
        struct sms_service is2; struct mock im2={.service=&is2};
        CHECK(sms_service_open(&is2,":memory:",write_frame,changed,&im2));
        sms_service_set_ims_submit(&is2,ims_submit);
        sms_service_tick(&is2,100,true,true,false,false,true);
        receive(&is2,128,1,2,is2.ready_sequence,ackc,sizeof ackc);
        receive(&is2,4,10,2,0,smscc,1);
        (void)ref;
        uint32_t iid2;CHECK(sms_store_queue(&is2.store,"+12345678901","ims refuse",&iid2));
        im2.ims_ok=false; /* transport refuses */
        sms_service_tick(&is2,200,true,true,false,true,true);
        CHECK(im2.ims_calls==1 && !is2.active);
        struct sms_record ir2;
        uint32_t ids[8];size_t nids=sms_store_list(&is2.store,ids,8);
        CHECK(nids>=1 && sms_store_get(&is2.store,iid2,&ir2) && !strcmp(ir2.state,"queued"));
        sms_service_close(&is2);
    }

    sms_service_close(&s);
    printf("SMS service durability/correlation: %s (%u failures)\n",failures ? "FAIL" : "PASS",failures);
    return failures ? 1 : 0;
}
