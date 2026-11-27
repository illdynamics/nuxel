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
        s->smsc_len=0;s->setup_attempts=0;s->next_setup_ms=0;s->online=false;
        s->ims_await_ack=false;s->ims_deadline_ms=0;return;
    }
    s->online=true;
    if (s->active && now>=s->deadline_ms) { uncertain(s);s->ims_await_ack=false;s->ims_deadline_ms=0; }
    /* An SMS-over-IMS MESSAGE whose SIP transaction result never arrived by
     * the send deadline is uncertain: fail it closed (never resend blindly). */
    if (s->active && s->ims_await_ack && s->ims_deadline_ms && now>=s->ims_deadline_ms) {
        (void)sms_store_fail(&s->store,s->job.id,s->job.part,-2,true);
        s->ims_await_ack=false;s->ims_deadline_ms=0;s->active=false;s->blocked=true;
        notify(s,s->job.id,false);
    }
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
    /* CS submit readiness = CS domain registered AND the CP DeviceReady
     * handshake accepted. The SMSC address is NOT a CS precondition: the CMS
     * submit with a zero-length SMSC lets the CP's own SMSC complete the
     * RP-Destination-Address (always true on LTE). Requiring a separately
     * echoed SMSC here previously made cs_ready always false, so no transport
     * could ever be selected even once CS registered. */
    bool cs_ready = cs_registered && s->ready_ack && !s->ready_rejected && s->write;
    /* SMS-over-IMS requires an AUTHORITATIVE native SIP 200 OK to our REGISTER,
     * not merely a modem IIL claim (the modem relays its registration state).
     * This makes a real AP-side IMS registration a hard prerequisite for the
     * IMS transport, so a good SMS-over-IP MESSAGE is never sent while the
     * REGISTER is still the P-CSCF's 480. */
    bool ims_ready = ims_registered && s->ims_submit && s->ims_registered_native;
    uint8_t domain_wire = 0u;
    if (cs_ready) {
        s->selected_domain = domain_wire;
    } else if (!ims_ready) {
        return;
    } else {
        s->selected_domain = 0xffu;   /* IMS (no CP FMT domain byte) */
    }

    if (s->submit_held || s->active || s->blocked || !sms_store_next(&s->store,&s->job)) return;

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
        char peer[SMS_MAX_PEER];
        if (!sms_store_peer(&s->store, s->job.id, peer, sizeof peer)) return;
        if (!sms_store_sending(&s->store,s->job.id,s->job.part)) { s->store_errors++;s->blocked=true;return; }
        s->active=true; s->deadline_ms=now+120000;
        s->ims_await_ack=true; s->ims_deadline_ms=now+45000;
        if (!s->ims_submit(peer, s->job.pdu.data, s->job.pdu.len,
                           s->job.pdu.reference, s->user)) {
            s->ims_await_ack=false; s->ims_deadline_ms=0;
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
    /* EFUJ2 IpcRxDeviceReady @3463b0 emits registrant 57 without reading
     * payload bytes. It is an event, not a zero-success result field. */
    if (f->main_cmd==4 && f->sub_cmd==7 && f->cmd_type==3 && n<=1 && s->ready_sent) {
        s->ready_ack=true;s->ready_rejected=false;
        return;
    }
    if (f->main_cmd==128 && f->cmd_type==2 && n==5 && p[0]==4) {
        unsigned result=p[3]|((unsigned)p[4]<<8);
        if (p[1]==1 && p[2]==1 && s->active && !s->ims_await_ack && f->ack_seq==s->sequence && result!=0x8000) {
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
        if (!s->active || s->ims_await_ack) { s->unmatched++;result_diag(s,f,&result,false,NULL);return; }
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

bool sms_service_ims_pending(const struct sms_service *s)
{ return s && s->active && s->ims_await_ack; }
bool sms_service_deliver_ims(struct sms_service *s, const uint8_t *pdu,
                             size_t len)
{
    if (!s || !s->store.db || !pdu || len == 0) return false;
    struct sms_decoded decoded;
    if (sms_decode(pdu, len, &decoded) != SMS_CODEC_OK) { s->decode_errors++; return false; }
    uint32_t id = 0; bool changed = false;
    if (!sms_store_receive(&s->store, pdu, len, &decoded, &id, &changed)) {
        s->store_errors++;
        return false;
    }
    if (changed) { s->received++; s->blocked = sms_store_blocked(&s->store); notify(s, id, decoded.kind == SMS_DELIVER); }
    return true;
}

/* Consume the SIP MESSAGE transaction result for the in-flight SMS-over-IMS
 * submission. This is deliberately separate from the CP FMT result
 * correlation: a SIP 2xx proves the MESSAGE reached the network (accepted for
 * delivery), NOT that the recipient received an SMS and NOT that an RP-ACK was
 * returned. Only matching RP-ACK marks submitted; STATUS-REPORT describes
 * delivery. Only the numeric SIP code is passed in; no SIP text. */
bool sms_service_ims_result(struct sms_service *s, bool accepted, int sip_code)
{
    if (!s || !s->store.db) return false;
    /* Gate on the IMS transaction state alone: `active` is a shared flag that
     * an unrelated CP-path result may have already cleared. */
    if (!s->ims_await_ack) return false;
    if (accepted) return true; /* SIP acceptance is not an RP submission result. */
    /* Non-2xx final: the network refused the MESSAGE. Fail the part with the
     * SIP status as the error and do not auto-retransmit (a client error will
     * recur; a transient 5xx is left to the operator/durable queue policy). */
    int err = (sip_code > 0 && sip_code < 0x8000) ? sip_code : -4;
    if (!sms_store_fail(&s->store, s->job.id, s->job.part, err, false)) {
        s->store_errors++; s->blocked = true;
    } else {
        s->blocked = sms_store_blocked(&s->store);
    }
    s->ims_await_ack=false; s->ims_deadline_ms=0; s->active=false;
    notify(s, s->job.id, false);
    return true;
}

bool sms_service_ims_rp_result(struct sms_service *s,uint8_t reference,uint8_t cause)
{
    if (!s || !s->store.db || !s->active || !s->ims_await_ack ||
        reference!=s->job.pdu.reference) return false;
    if (!sms_store_submit(&s->store,s->job.id,s->job.part,reference,cause)) {
        s->store_errors++;uncertain(s);return false;
    }
    s->ims_await_ack=false;s->ims_deadline_ms=0;s->active=false;
    s->blocked=sms_store_blocked(&s->store);notify(s,s->job.id,false);return true;
}
