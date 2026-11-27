/* SPDX-License-Identifier: GPL-2.0-only
 *
 * ims_service.c — native IMS registration-driving state machine for the
 * S5000AP (Shannon) modem-over-SIPC5.
 *
 * EFUJ2 libsec-ril 60889dd7 receives IMS registration over IIL from the
 * AP IMS service. SetImsRegState reports that state to the CP; it does not
 * start SIP REGISTER. CP main=22/sub=16 is a mode-switch request, not
 * registration evidence. Until a native SIP backend supplies authenticated
 * registration and an IMS SMS transport, this service must hold SMS closed.
 */
#include "ims_service.h"
#include "ims_msisdn.h"
#include <string.h>
#include <stdio.h>

static void erase(void *p, size_t n)
{
    volatile unsigned char *v=p;
    while (n--) *v++=0;
}
void ims_identity_clear(struct ims_identity *out)
{ if (out) erase(out,sizeof *out); }

bool ims_identity_from_usim(struct ims_identity *out, const uint8_t *imsi,
                            size_t len, unsigned mnc_digits)
{
    if (!out) return false;
    ims_identity_clear(out);
    if (!imsi || len<6 || len>15 || (mnc_digits!=2 && mnc_digits!=3) ||
        len<=3+mnc_digits) return false;
    for (size_t i=0;i<len;i++) if (imsi[i]<'0' || imsi[i]>'9') return false;
    char mnc[4]={0};
    if (mnc_digits==2) { mnc[0]='0'; memcpy(mnc+1,imsi+3,2); }
    else memcpy(mnc,imsi+3,3);
    snprintf(out->domain,sizeof out->domain,"ims.mnc%s.mcc%.3s.3gppnetwork.org",mnc,(const char *)imsi);
    snprintf(out->impi,sizeof out->impi,"%.*s@%s",(int)len,(const char *)imsi,out->domain);
    snprintf(out->impu,sizeof out->impu,"sip:%s",out->impi);
    out->ready=true;
    return true;
}

bool ims_identity_prefer_msisdn(struct ims_identity *out, const char *digits)
{
    if (!out || !out->ready) return false;
    if (!digits || !digits[0]) return false;
    if (!ims_msisdn_impu(digits, out->domain, out->msisdn_impu,
                         sizeof out->msisdn_impu)) return false;
    out->msisdn_impu_valid = true;
    /* Prefer the MSISDN-derived IMPU for presentation; the private identity
     * (IMPI) stays the IMSI-derived value that IMS AKA uses as the digest
     * username. Never copy the MSISDN into the IMSI-derived impu field. */
    return true;
}

/* Adopt an operator/modem-provisioned public identity (IMPU) directly, as
 * reported by the modem's IIL registration event. `impu` is already a full
 * SIP URI ("sip:...@...") or bare userpart? The modem emits the IMPU exactly
 * as the operator configured it (typically a full sip:/tel: URI). We only
 * accept a non-empty, printable, bounded value and store it as the preferred
 * MSISDN-independent operator IMPU; the private identity (IMPI) is unchanged.
 * This is a PUBLIC identity, not a secret/PII credential, but it is still
 * never logged in full by the caller. */
bool ims_identity_prefer_impu(struct ims_identity *out, const char *impu)
{
    if (!out || !out->ready || !impu || !impu[0]) return false;
    size_t n = strlen(impu);
    if (n == 0 || n >= sizeof out->msisdn_impu) return false;
    for (size_t i = 0; i < n; i++) {
        unsigned char c = (unsigned char)impu[i];
        if (c < 0x20 || c > 0x7e) return false;   /* printable-only */
    }
    memcpy(out->msisdn_impu, impu, n + 1);
    out->msisdn_impu_valid = true;
    return true;
}

static void auth_complete(struct ims_service *s, const struct fmt_rx_usim_auth *r)
{
    ims_auth_fn done=s->auth_done; void *user=s->auth_user;
    s->auth_pending=false; s->auth_deadline_ms=0;
    s->auth_done=NULL; s->auth_user=NULL;
    if (done) done(r,user);
}

bool ims_service_open(struct ims_service *s, ims_write_fn write, ims_state_fn cb, void *user)
{
    if (!s || !write) return false;
    memset(s, 0, sizeof *s);
    s->write = write;
    s->state_cb = cb;
    s->user = user;
    s->phase = IMS_IDLE;
    return true;
}

void ims_service_close(struct ims_service *s)
{ if (s) { s->online=false; auth_complete(s,NULL); erase(s,sizeof *s); } }

static void set_phase(struct ims_service *s, enum ims_phase p, const char *reason)
{
    if (s->phase == p) return;
    s->phase = p;
    s->last_reason = reason;
    s->phase_deadline_ms = 0; /* recomputed per phase */
    if (s->state_cb) s->state_cb(ims_phase_name(p), reason ? reason : "", s->user);
}

bool ims_service_registered(const struct ims_service *s)
{
    return s && s->phase == IMS_REGISTERED && s->modem_confirmed_registered;
}

void ims_service_native_registered(struct ims_service *s, bool registered)
{
    if (!s) return;
    s->modem_confirmed_registered = registered;
    if (registered) {
        if (s->phase != IMS_REGISTERED)
            set_phase(s, IMS_REGISTERED, "native-sip-200-ok");
    } else {
        /* A loss of registration (deregister/timeout) returns to WAIT_BACKEND
         * so SMS transport is held closed until the next authoritative 200. */
        if (s->phase == IMS_REGISTERED)
            set_phase(s, IMS_WAIT_BACKEND, "native-sip-deregistered");
    }
}

const char *ims_phase_name(enum ims_phase p)
{
    static const char *const n[] = {
        "idle","wait-pdn","request-reg","wait-auth","wait-registered",
        "registered","deregistering","failed","wait-backend"
    };
    return (p <= IMS_WAIT_BACKEND) ? n[p] : "unknown";
}

enum ims_phase ims_service_tick(struct ims_service *s, uint64_t now_ms,
                                 bool online, bool ims_pdn)
{
    if (!s) return IMS_IDLE;
    s->ims_pdn_up = ims_pdn;
    s->online=online;

    if (!online) {
        s->modem_confirmed_registered = false;
        auth_complete(s,NULL);
        ims_identity_clear(&s->identity);
        if (s->phase != IMS_FAILED) set_phase(s, IMS_IDLE, "offline");
        return s->phase;
    }

    /* No CP command starts SIP registration on the recovered stock path. */
    if (s->auth_pending && now_ms>=s->auth_deadline_ms) auth_complete(s,NULL);
    set_phase(s, IMS_WAIT_BACKEND, "sip-registration-backend-missing");
    return s->phase;
}

bool ims_service_auth_request(struct ims_service *s, const uint8_t rand[16],
                               const uint8_t autn[16], uint64_t now_ms,
                               ims_auth_fn done, void *user)
{
    if (!s || !s->online || s->auth_pending || !done) return false;
    struct fmt_tx_frame f;
    if (!fmt_tx_usim_auth(&f,rand,autn)) return false;
    uint8_t seq=0;
    bool sent=s->write(&f,&seq,s->user);
    erase(&f,sizeof f);
    if (!sent) return false;
    s->last_write_seq=seq; s->auth_pending=true;
    s->auth_deadline_ms=now_ms+15000; s->auth_done=done; s->auth_user=user;
    return true;
}

void ims_service_receive(struct ims_service *s, const struct nuxel_sipc_fmt *f)
{
    if (!s || !f || !s->auth_pending || f->cmd_type!=2 ||
        f->ack_seq!=s->last_write_seq) return;
    if (f->main_cmd==5 && f->sub_cmd==9) {
        struct fmt_rx_usim_auth r;
        if (!fmt_rx_usim_auth(f->payload,f->payload_len,&r)) auth_complete(s,NULL);
        else auth_complete(s,&r);
    } else if (f->main_cmd==128 && f->sub_cmd==1) {
        struct fmt_rx_gen gen;
        if (fmt_rx_gen(f->payload,f->payload_len,&gen) && gen.main==5 &&
            gen.sub==9 && gen.type==2 && gen.result!=FMT_RX_GEN_OK)
            auth_complete(s,NULL);
    }
}
