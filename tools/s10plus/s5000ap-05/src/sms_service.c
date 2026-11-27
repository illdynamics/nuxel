/* SPDX-License-Identifier: GPL-2.0-only */
#include "sms_service.h"
#include <string.h>

static void notify(struct sms_service *s,uint32_t id,bool incoming)
{ if (s->notify && id) s->notify(id,incoming,s->user); }

/* Emit redacted submission-result metadata. Never includes recipient,
 * message body, or PDU bytes. */
static void result_diag(struct sms_service *s,const struct nuxel_sipc_fmt *f,
                        const struct fmt_sms_submit_result *r,bool correlated,
                        const char *state)
{
    struct sms_record record;
    if (!state && s->active && sms_store_get(&s->store,s->job.id,&record)) state=record.state;
    if (!state) state="no-active-message";
    const char *reason=correlated ? "ack-sequence" : f->cmd_type==3 ? "unsequenced-modem-reference" : "no-matching-sequence";
    struct sms_submit_result_diag d = {
        .message_id = s->active ? s->job.id : 0,
        .cmd_type    = f->cmd_type,
        .payload_len = f->payload_len,
        .ack_seq     = f->ack_seq,
        .result_code = r ? r->result : 0,
        .modem_ref   = r ? r->reference : 0,
        .correlated  = correlated,
        .state       = state,
        .reason      = reason,
    };
    if (!sms_store_result(&s->store,d.message_id,d.cmd_type,d.payload_len,d.ack_seq,
                          d.result_code,d.modem_ref,correlated,state,reason)) {
        s->store_errors++;s->blocked=true;
    }
    if (s->result_diag) s->result_diag(&d,s->user);
}

bool sms_service_open(struct sms_service *s,const char *path,sms_write_fn write,sms_notify_fn callback,void *user)
{
    if (!s || !write) return false;
    memset(s,0,sizeof *s);s->write=write;s->notify=callback;s->user=user;
    if (!sms_store_open(&s->store,path)) return false;
    s->blocked=sms_store_blocked(&s->store);
    return true;
}

void sms_service_set_result_diag(struct sms_service *s,sms_result_fn fn)
{ if (s) s->result_diag=fn; }

void sms_service_set_ims_submit(struct sms_service *s,sms_ims_submit_fn fn)
{ if (s) s->ims_submit=fn; }

static void uncertain(struct sms_service *s)
{
    if (!s->active) return;
    if (!sms_store_fail(&s->store,s->job.id,s->job.part,-2,true)) s->store_errors++;
    s->active=false;s->blocked=true;notify(s,s->job.id,false);
}

void sms_service_close(struct sms_service *s)
{ if(s) { uncertain(s);sms_store_close(&s->store); } }

void sms_service_tick(struct sms_service *s,uint64_t now,bool online,bool sim_ready,bool cs_registered,bool ims_registered,bool writable)
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
    s->ims_registered = ims_registered;
    /* Transport selection, transport-independent and truthful:
     *   - CS domain (wire 0 == ConvertDomainToIPC(GetDomain=2)) is the legacy
     *     path; it requires the CP's CS registration AND the FMT writer.
     *   - SMS-over-IMS (TS 24.341) requires an authoritative IMS registration
     *     (SIP 200 OK) and the ims_submit hook. The FMT writer is NOT an IMS
     *     transport, so the CS path is never used to fake IMS.
     * A job is only dequeued once a real transport is ready; otherwise it
     * stays durably queued (never a doomed submission). */
    bool cs_ready = cs_registered && s->ready_ack && !s->ready_rejected &&
                    s->smsc_len && s->write;
    bool ims_ready = ims_registered && s->ims_submit;
    uint8_t domain_wire = 0u;
    if (cs_ready) {
        s->selected_domain = domain_wire;
    } else if (!ims_ready) {
        return;
    } else {
        s->selected_domain = 0xffu;   /* IMS (no CP FMT domain byte) */
    }

    if (s->active || s->blocked || !sms_store_next(&s->store,&s->job)) return;

    if (cs_ready) {
        struct fmt_tx_frame f;uint8_t sequence;
        uint8_t pdu[SMS_MAX_PDU];size_t n=s->smsc_len+s->job.pdu.len;
        if (n>sizeof pdu) {
            (void)sms_store_fail(&s->store,s->job.id,s->job.part,-3,false);notify(s,s->job.id,false);return;
        }
        memcpy(pdu,s->smsc,s->smsc_len);memcpy(pdu+s->smsc_len,s->job.pdu.data,s->job.pdu.len);
        if (!fmt_sms_send(&f,s->job.part<s->job.total,domain_wire,pdu,n)) return;
        if (!sms_store_sending(&s->store,s->job.id,s->job.part)) { s->store_errors++;s->blocked=true;return; }
        s->active=true;s->deadline_ms=now+120000;
        if (!s->write(&f,&sequence,s->user)) uncertain(s);
        else { s->sequence=sequence; notify(s,s->job.id,false); }
        return;
    }

    /* IMS path: hand the pure TP-MTI TPDU (already stored WITHOUT an SMSC
     * prefix) to the SIP MESSAGE builder, which wraps it in RP-DATA addressed
     * to the originating UE. The TPDU is what the SMSC encodes/decodes. */
    {
        uint32_t peer_off = s->job.id ? 0u : 0u; (void)peer_off;
        char peer[SMS_MAX_PEER];
        if (!sms_store_peer(&s->store, s->job.id, peer, sizeof peer)) return;
        if (!sms_store_sending(&s->store,s->job.id,s->job.part)) { s->store_errors++;s->blocked=true;return; }
        s->active=true; s->deadline_ms=now+120000;
        if (!s->ims_submit(peer, s->job.pdu.data, s->job.pdu.len,
                           s->job.pdu.reference, s->user)) {
            /* Could not push the MESSAGE: revert to queued (no network send
             * happened) so a later tick can retry after backoff. */
            (void)sms_store_requeue(&s->store,s->job.id,s->job.part);
            s->active=false;
            return;
        }
        notify(s,s->job.id,false);
    }
}

void sms_service_receive(struct sms_service *s,const struct nuxel_sipc_fmt *f)
{
    if (!s || !s->store.db || !f) return;
    const uint8_t *p=f->payload;size_t n=f->payload_len;
    if (n && !p) { s->decode_errors++;return; }
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
        /* Vendor 0x3463c0: GSM, LE result, reference, bounded optional PDU.
         * EFUJ2 also emits this payload as type 3 with ack 0. Type 2 keeps
         * explicit sequence correlation. Physical Round02 returned MR157 for
         * requested TP-MR1: this field is NOT an echo. No validated token
         * exists for type3/ack0. Even an equal MR can be coincidental or stale.
         * Retain the result, leave the message pending, then timeout unknown. */
        struct fmt_sms_submit_result result;
        if (!fmt_sms_submit_result(p,n,&result)) { s->decode_errors++;return; }
        if (!s->active) { s->unmatched++;result_diag(s,f,&result,false,NULL);return; }
        bool match = f->cmd_type==2 && f->ack_seq==s->sequence;
        if (!match) { s->unmatched++;result_diag(s,f,&result,false,NULL);return; }
        if (!sms_store_submit(&s->store,s->job.id,s->job.part,result.reference,result.result)) { s->store_errors++;uncertain(s);result_diag(s,f,&result,false,"storage-error");return; }
        struct sms_record record;
        const char *state=sms_store_get(&s->store,s->job.id,&record) ? record.state : "storage-error";
        result_diag(s,f,&result,true,state);
        s->active=false;notify(s,s->job.id,false);
    } else if (f->sub_cmd==2 && f->cmd_type==3) {
        struct fmt_sms_incoming incoming;struct sms_decoded decoded;
        if (!fmt_sms_incoming(p,n,&incoming)) { s->decode_errors++;return; }
        uint16_t result=0;uint32_t id=0;bool changed=false;
        if (sms_decode(incoming.pdu,incoming.len,&decoded)!=SMS_CODEC_OK) { s->decode_errors++;result=0x806f; }
        else if (!sms_store_receive(&s->store,incoming.pdu,incoming.len,&decoded,&id,&changed)) { s->store_errors++;result=0x8016; }
        else if (changed) { s->received++;s->blocked=sms_store_blocked(&s->store);notify(s,id,decoded.kind==SMS_DELIVER); }
        struct fmt_tx_frame reply;uint8_t sequence;
        if (!fmt_sms_ack(&reply,incoming.reference,result) || !s->write(&reply,&sequence,s->user)) s->ack_errors++;
    }
}

bool sms_service_resolve(struct sms_service *s,uint32_t id,const char *outcome)
{
    if (!s || !s->store.db) return false;
    if (!sms_store_resolve(&s->store,id,outcome)) return false;
    s->blocked=sms_store_blocked(&s->store);
    notify(s,id,false);
    return true;
}
