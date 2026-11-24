/* SPDX-License-Identifier: GPL-2.0-only */
#include "call_service.h"
#include <string.h>
void call_service_init(struct call_service *s,call_write_fn write,call_notify_fn notify,void *user)
{ memset(s,0,sizeof *s);s->write=write;s->notify=notify;s->user=user;s->result=-1; }
static void notification(struct call_service *s,uint8_t id,const char *state,bool incoming)
{ if(s->notify)s->notify(id,state,incoming,s->user); }
static void invalidate_list(struct call_service *s)
{
    /* Loss of observation is not a remotely confirmed hang-up. Publish it
     * once so consumers cannot retain an active call/audio route forever. */
    if(s->list_valid)
        for(size_t i=0;i<s->list.count;i++)
            notification(s,s->list.calls[i].id,"unknown",false);
    s->list_valid=false;
    s->list.count=0;
}
static bool command(struct call_service *s,struct fmt_tx_frame *f,uint64_t now)
{
    if(s->pending || !s->write)return false;
    s->subcommand=f->sub_cmd;s->result=-1;
    if(!s->write(f,&s->sequence,s->user)) { s->result=-2;return false; }
    s->pending=true;s->deadline_ms=now+30000;s->next_query_ms=now+1000;return true;
}
bool call_service_dial(struct call_service *s,const char *number,uint64_t now)
{
    if(!s || !s->list_valid || s->list.count || s->result==-2 || s->dial_waiting)return false;
    struct fmt_tx_frame f;
    bool sent=fmt_call_dial(&f,number) && command(s,&f,now);
    if(sent)s->dial_waiting=true;
    return sent;
}
bool call_service_answer(struct call_service *s,uint64_t now)
{
    if(!s || !s->list_valid)return false;
    bool incoming=false;
    for(size_t i=0;i<s->list.count;i++)if(s->list.calls[i].state==5 || s->list.calls[i].state==6)incoming=true;
    struct fmt_tx_frame f;
    return incoming && fmt_call_answer(&f) && command(s,&f,now);
}
bool call_service_hangup(struct call_service *s,uint64_t now)
{
    if(!s)return false;
    s->pending=false;s->dial_waiting=false; /* Explicit cancellation may supersede setup. */
    struct fmt_tx_frame f;
    return fmt_call_release(&f) && command(s,&f,now);
}
void call_service_tick(struct call_service *s,uint64_t now,bool online,bool writable)
{
    if(!s)return;
    if(!online) {
        if(s->pending)s->result=-2;
        s->pending=false;s->query_pending=false;s->status_valid=false;s->dial_waiting=false;
        invalidate_list(s);s->next_query_ms=0;return;
    }
    if(s->pending && now>=s->deadline_ms) { s->pending=false;s->result=-2;s->next_query_ms=0; }
    if(s->dial_waiting && now>=s->deadline_ms) { s->dial_waiting=false;s->result=-2;s->next_query_ms=0; }
    if(s->query_pending && now>=s->query_deadline_ms) {
        s->query_pending=false;invalidate_list(s);s->next_query_ms=now+5000;
    }
    if(s->list.count && s->next_query_ms>now+1000)
        s->next_query_ms=now+1000;
    if(writable && !s->query_pending && now>=s->next_query_ms) {
        struct fmt_tx_frame f;
        if(fmt_call_get_list(&f) && s->write(&f,&s->query_sequence,s->user)) {
            s->query_pending=true;s->query_deadline_ms=now+5000;
        }
        s->next_query_ms=now+(s->list.count || s->pending || s->dial_waiting ? 1000 : 60000);
    }
}
void call_service_receive(struct call_service *s,const struct nuxel_sipc_fmt *f)
{
    if(!s || !f)return;
    const uint8_t *p=f->payload;size_t n=f->payload_len;
    if(f->main_cmd==128 && f->cmd_type==2 && n==5 && p[0]==2 && p[2]==1) {
        if(!s->pending || p[1]!=s->subcommand || f->ack_seq!=s->sequence) { s->unmatched++;return; }
        s->result=p[3]|((unsigned)p[4]<<8);s->pending=false;s->next_query_ms=0;
        if(s->result!=0x8000)s->dial_waiting=false;
        return;
    }
    if(f->main_cmd!=2)return;
    if(f->cmd_type==3) {
        if(f->sub_cmd==5) {
            s->status_valid=fmt_call_status(p,n,&s->status);if(!s->status_valid)s->parse_errors++;
        }
        if(f->sub_cmd==2 || f->sub_cmd==5 || f->sub_cmd==6 || f->sub_cmd==9)s->next_query_ms=0;
        return;
    }
    if(f->sub_cmd!=6 || f->cmd_type!=2)return;
    if(!s->query_pending || f->ack_seq!=s->query_sequence) { s->unmatched++;return; }
    s->query_pending=false;
    struct fmt_call_list list;
    if(!fmt_call_list(p,n,&list)) {
        s->parse_errors++;invalidate_list(s);return;
    }
    for(size_t i=0;i<list.count;i++) {
        const struct fmt_call *c=&list.calls[i];bool different=true;
        for(size_t j=0;j<s->list.count && s->list_valid;j++)
            if(s->list.calls[j].id==c->id && s->list.calls[j].state==c->state)different=false;
        if(different)notification(s,c->id,fmt_call_state_name(c->state),c->state==5 || c->state==6);
    }
    for(size_t i=0;i<s->list.count && s->list_valid;i++) {
        bool present=false;for(size_t j=0;j<list.count;j++)if(s->list.calls[i].id==list.calls[j].id)present=true;
        if(!present)notification(s,s->list.calls[i].id,"ended",false);
    }
    s->list=list;s->list_valid=true;
    if(list.count)s->dial_waiting=false;
}
