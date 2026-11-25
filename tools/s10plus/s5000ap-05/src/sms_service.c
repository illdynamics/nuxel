/* SPDX-License-Identifier: GPL-2.0-only */
#include "sms_service.h"
#include <string.h>

static void notify(struct sms_service *s,uint32_t id,bool incoming)
{ if (s->notify && id) s->notify(id,incoming,s->user); }

bool sms_service_open(struct sms_service *s,const char *path,sms_write_fn write,sms_notify_fn callback,void *user)
{
    if (!s || !write) return false;
    memset(s,0,sizeof *s);s->write=write;s->notify=callback;s->user=user;
    if (!sms_store_open(&s->store,path)) return false;
    sqlite3_stmt *q=NULL;
    if (sqlite3_prepare_v2(s->store.db,"SELECT 1 FROM parts WHERE state='unknown' LIMIT 1",-1,&q,NULL)!=SQLITE_OK) {
        sms_store_close(&s->store);return false;
    }
    s->blocked=sqlite3_step(q)==SQLITE_ROW;sqlite3_finalize(q);
    return true;
}

static void uncertain(struct sms_service *s)
{
    if (!s->active) return;
    if (!sms_store_fail(&s->store,s->job.id,s->job.part,-2,true)) s->store_errors++;
    s->active=false;s->blocked=true;notify(s,s->job.id,false);
}

void sms_service_close(struct sms_service *s)
{ if(s) { uncertain(s);sms_store_close(&s->store); } }

void sms_service_tick(struct sms_service *s,uint64_t now,bool online,bool sim_ready,bool registered,bool writable)
{
    if (!s || !s->store.db) return;
    if (!online || !sim_ready) {
        uncertain(s);s->ready_sent=false;s->ready_ack=false;s->ready_rejected=false;
        s->smsc_len=0;s->setup_attempts=0;s->next_setup_ms=0;s->online=false;return;
    }
    s->online=true;
    if (s->active && now>=s->deadline_ms) uncertain(s);
    if (!writable) return;
    struct fmt_tx_frame f;uint8_t sequence;
    if (!s->ready_sent && now>=s->next_setup_ms && s->setup_attempts<5) {
        s->setup_attempts++;s->next_setup_ms=now+1000;
        if (fmt_sms_ready(&f) && s->write(&f,&sequence,s->user)) {
            s->ready_sequence=sequence;s->ready_sent=true;s->setup_attempts=0;
        }
        return;
    }
    if (s->ready_sent && !s->smsc_len && now>=s->next_setup_ms && s->setup_attempts<5) {
        s->setup_attempts++;s->next_setup_ms=now+10000;
        if (fmt_sms_get_smsc(&f)) (void)s->write(&f,&sequence,s->user);
        return;
    }
    if (s->active || s->blocked || s->ready_rejected || !s->smsc_len || !registered || !sms_store_next(&s->store,&s->job)) return;
    uint8_t pdu[SMS_MAX_PDU];size_t n=s->smsc_len+s->job.pdu.len;
    if (n>sizeof pdu) {
        (void)sms_store_fail(&s->store,s->job.id,s->job.part,-3,false);notify(s,s->job.id,false);return;
    }
    memcpy(pdu,s->smsc,s->smsc_len);memcpy(pdu+s->smsc_len,s->job.pdu.data,s->job.pdu.len);
    /* DomainSelector::GetDomain=2 (CS); ConvertDomainToIPC(2)=0.
     * No IMS transport is silently substituted. */
    if (!fmt_sms_send(&f,s->job.part<s->job.total,0,pdu,n)) return;
    if (!sms_store_sending(&s->store,s->job.id,s->job.part)) { s->store_errors++;s->blocked=true;return; }
    s->active=true;s->deadline_ms=now+120000;
    if (!s->write(&f,&s->sequence,s->user)) uncertain(s);
    else notify(s,s->job.id,false);
}

void sms_service_receive(struct sms_service *s,const struct nuxel_sipc_fmt *f)
{
    if (!s || !s->store.db || !f) return;
    const uint8_t *p=f->payload;size_t n=f->payload_len;
    if (f->main_cmd==128 && f->cmd_type==2 && n==5 && p[0]==4) {
        unsigned result=p[3]|((unsigned)p[4]<<8);
        if (p[1]==7 && p[2]==3 && s->ready_sent && f->ack_seq==s->ready_sequence) {
            s->ready_ack=result==0x8000;s->ready_rejected=result!=0x8000;
        } else if (p[1]==1 && p[2]==1 && s->active && f->ack_seq==s->sequence && result!=0x8000) {
            if (!sms_store_fail(&s->store,s->job.id,s->job.part,(int)result,false)) { s->store_errors++;s->blocked=true; }
            s->active=false;notify(s,s->job.id,false);
        }
        return;
    }
    if (f->main_cmd!=4) return;
    if (f->sub_cmd==10 && f->cmd_type==2) {
        if (!fmt_sms_smsc(p,n,s->smsc,&s->smsc_len)) s->decode_errors++;
    } else if (f->sub_cmd==1 && (f->cmd_type==2 || f->cmd_type==3)) {
        /* Live EFUJ2 emits the SEND result as a NOTIFICATION (type 3) with
         * ack_seq 0, not the DTK9-derived RESPONSE (type 2). Accept both.
         * A type-2 response correlates on the echoed AP sequence; a type-3
         * notification has no echo, so it is matched to the single segment
         * currently in flight (the service never runs two sends at once). */
        struct fmt_sms_submit_result result;
        if (!fmt_sms_submit_result(p,n,&result)) { s->decode_errors++;return; }
        if (!s->active) { s->unmatched++;return; }
        if (f->cmd_type==2 && f->ack_seq!=s->sequence) { s->unmatched++;return; }
        if (!sms_store_submit(&s->store,s->job.id,s->job.part,result.reference,result.result)) { s->store_errors++;uncertain(s);return; }
        s->active=false;notify(s,s->job.id,false);
    } else if (f->sub_cmd==2 && f->cmd_type==3) {
        struct fmt_sms_incoming incoming;struct sms_decoded decoded;
        if (!fmt_sms_incoming(p,n,&incoming)) { s->decode_errors++;return; }
        uint16_t result=0;uint32_t id=0;bool changed=false;
        if (sms_decode(incoming.pdu,incoming.len,&decoded)!=SMS_CODEC_OK) { s->decode_errors++;result=0x806f; }
        else if (!sms_store_receive(&s->store,incoming.pdu,incoming.len,&decoded,&id,&changed)) { s->store_errors++;result=0x8016; }
        else if (changed) { s->received++;notify(s,id,decoded.kind==SMS_DELIVER); }
        struct fmt_tx_frame reply;uint8_t sequence;
        if (!fmt_sms_ack(&reply,incoming.reference,result) || !s->write(&reply,&sequence,s->user)) s->ack_errors++;
    }
}

bool sms_service_resolve(struct sms_service *s,uint32_t id,const char *outcome)
{
    if (!s || !s->store.db) return false;
    if (!sms_store_resolve(&s->store,id,outcome)) return false;
    /* Re-derive blocked from the store rather than trusting the in-memory
     * flag, so resolving the last unknown message clears the block. */
    sqlite3_stmt *q=NULL;
    if (sqlite3_prepare_v2(s->store.db,
        "SELECT 1 FROM parts WHERE state='unknown' LIMIT 1",-1,&q,NULL)!=SQLITE_OK)
        return false;
    s->blocked = sqlite3_step(q)==SQLITE_ROW;
    sqlite3_finalize(q);
    return true;
}
