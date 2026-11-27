/* SPDX-License-Identifier: GPL-2.0-only
 * ims_sip_tr.c — native SIP/IMS transport + registration state machine.
 * See ims_sip_tr.h. Pure C, bounded, secret-safe.
 */
#define _GNU_SOURCE
#include "ims_sip_tr.h"

#include "ims_sip.h"
#include "ims_sms.h"

#include <string.h>
#include <stdio.h>

#define SREG_TIMEOUT_MS   12000u
#define SREG_REFRESH_MS   3600000u   /* > 600s Registration expiry: refresh well inside */
#define SREG_ATTEMPT_LIMIT 4u
#define SREG_RETRY_MS      8000u

/* ---- helper: explicit wipe of secret material ---- */
static void wipe(void *p, size_t n)
{
    if (!p) return;
    volatile unsigned char *v = (volatile unsigned char *)p;
    while (n--) *v++ = 0;
}

bool ims_sip_tr_open(struct ims_sip_tr *t, const struct ims_sip_tr_cfg *cfg,
                     const struct ims_sip_tr_io *io, void *user,
                     const struct ims_sip_tr *prev)
{
    if (!t || !cfg || !cfg->impu || !cfg->impi || !cfg->pcscf || !cfg->local_ip)
        return false;
    if (cfg->port == 0 || cfg->pcscf_port == 0) return false;
    if (strlen(cfg->impu) >= IMS_SIP_TR_ID_MAX ||
        strlen(cfg->impi) >= IMS_SIP_TR_ID_MAX ||
        strlen(cfg->pcscf) >= IMS_SIP_TR_HOST_MAX ||
        strlen(cfg->local_ip) >= IMS_SIP_TR_HOST_MAX) return false;
    if (cfg->sec_offer && strlen(cfg->sec_offer) >= sizeof t->_sec_offer) return false;
    if (cfg->home_plmn && strlen(cfg->home_plmn) >= sizeof t->_home_plmn) return false;
    if (cfg->cell_id && strlen(cfg->cell_id) >= sizeof t->_cell_id) return false;
    memset(t, 0, sizeof *t);
    snprintf(t->_impu, sizeof t->_impu, "%s", cfg->impu);
    snprintf(t->_impi, sizeof t->_impi, "%s", cfg->impi);
    snprintf(t->_pcscf, sizeof t->_pcscf, "%s", cfg->pcscf);
    snprintf(t->_local_ip, sizeof t->_local_ip, "%s", cfg->local_ip);
    if (cfg->sec_offer) snprintf(t->_sec_offer, sizeof t->_sec_offer, "%s", cfg->sec_offer);
    if (cfg->cell_id && *cfg->cell_id) snprintf(t->_cell_id, sizeof t->_cell_id, "%s", cfg->cell_id);
    if (cfg->home_plmn && *cfg->home_plmn) snprintf(t->_home_plmn, sizeof t->_home_plmn, "%s", cfg->home_plmn);
    t->cfg = *cfg;
    t->cfg.impu = t->_impu;
    t->cfg.impi = t->_impi;
    t->cfg.pcscf = t->_pcscf;
    t->cfg.local_ip = t->_local_ip;
    t->cfg.sec_offer = cfg->sec_offer ? t->_sec_offer : NULL;
    t->cfg.cell_id = (cfg->cell_id && *cfg->cell_id) ? t->_cell_id : NULL;
    t->cfg.home_plmn = (cfg->home_plmn && *cfg->home_plmn) ? t->_home_plmn : NULL;
    t->cfg.utran_tac = cfg->utran_tac;
    if (io) t->io = *io;
    t->user = user;
    t->phase = IMS_SIP_TR_IDLE;
    t->cseq = 1;
    /* Carry over a network-imposed hold so re-opening the bearer/socket does
     * NOT bypass a registrar Retry-After (the hold is absolute monotonic ms,
     * so it remains valid across the re-open). RES/digest material is never
     * carried: a new challenge is re-issued by the network. */
    if (prev) {
        t->next_action_ms = prev->next_action_ms;
        t->retry_waits = prev->retry_waits;
        t->retry_after_s = prev->retry_after_s;
        if (t->next_action_ms) t->phase = IMS_SIP_TR_RETRY_WAIT;
    }
    return true;
}

void ims_sip_tr_close(struct ims_sip_tr *t)
{
    if (!t) return;
    wipe(t->nonce, sizeof t->nonce);
    wipe(t->res_b64, sizeof t->res_b64);
    wipe(t->qop, sizeof t->qop);
    wipe(t->cnonce, sizeof t->cnonce);
    wipe(t->sec_server, sizeof t->sec_server);
    t->sec_server_valid = false;
    wipe(t->scratch, sizeof t->scratch);
    wipe(t->_impu, sizeof t->_impu);
    wipe(t->_impi, sizeof t->_impi);
    wipe(t->_pcscf, sizeof t->_pcscf);
    wipe(t->_local_ip, sizeof t->_local_ip);
    wipe(t->_sec_offer, sizeof t->_sec_offer);
    wipe(t->_cell_id, sizeof t->_cell_id);
    wipe(t->_home_plmn, sizeof t->_home_plmn);
    t->scratch_len = 0;
    t->phase = IMS_SIP_TR_IDLE;
}

const char *ims_sip_tr_phase_name(enum ims_sip_tr_phase ph)
{
    static const char *const n[] = {
        "idle","register-sent","secure-register-sent","challenged","auth-sent",
        "registered","dereg-sent","failed","retry-wait"
    };
    return (ph <= IMS_SIP_TR_RETRY_WAIT) ? n[ph] : "unknown";
}

bool ims_sip_tr_registered(const struct ims_sip_tr *t)
{
    return t && t->phase == IMS_SIP_TR_REGISTERED;
}

static bool send_scratch(struct ims_sip_tr *t)
{
    if (!t->io.send || !t->scratch_len) return false;
    return t->io.send(t->scratch, t->scratch_len, t->user);
}

/* Build and send an (un)authenticated REGISTER. When `auth` is true, add the
 * Authorization header using the base64(RES) already stored. */
static bool send_register(struct ims_sip_tr *t, bool auth)
{
    char out[IMS_SIP_TR_MAX_MSG];
    /* Route the REGISTER at the P-CSCF but use the IMPU domain as the SIP URI
     * target. The codec builds "REGISTER sip:<impu>"; we then compute the
     * Authorization from the same fields. */
    /* First (unauthenticated) REGISTER: when the caller has enabled
     * security-first, assert sec-agree + Security-Client so a P-CSCF that
     * requires IPsec from the first packet issues the 401 challenge. The
     * retransmit of the SAME registration (SECURE_REGISTER_SENT) keeps the
     * identical security surface. */
    bool secure_first = t->cfg.security_first &&
                        t->cfg.sec_offer && *t->cfg.sec_offer;
    size_t n = secure_first
        ? ims_sip_register_build_secure_ex4(out, sizeof out,
              t->cfg.impu, t->cfg.impi, t->cfg.pcscf, t->cfg.local_ip,
              t->cfg.port, t->cfg.sec_offer, NULL, t->cfg.cell_id,
              t->cfg.home_plmn, t->cfg.utran_tac)
        : ims_sip_register_build_ex4(out, sizeof out,
              t->cfg.impu, t->cfg.impi, t->cfg.pcscf, t->cfg.local_ip,
              t->cfg.port, t->cfg.sec_offer, NULL, t->cfg.cell_id,
              t->cfg.home_plmn, t->cfg.utran_tac);
    if (n == 0) return false;
    /* Insert Authorization before the trailing CRLF CRLF for authenticated
     * retry. The codec emits Content-Length: 0\r\n\r\n at the end; find it. */
    if (auth) {
        const char *end = "\r\n\r\n";
        size_t mlen = n;
        char *p = (char *)memmem(out, mlen, end, 4);
        if (!p) return false;
        size_t head = (size_t)(p - out);   /* points at first CR of the terminator */
        struct ims_sip_digest_params d = {0};
        d.impu = t->cfg.impi;              /* username is the private identity */
        d.realm = t->realm;
        d.nonce = t->nonce;
        d.cnonce = t->cnonce;
        d.method = "REGISTER";
        d.uri = t->cfg.impu;
        d.response = t->res_b64;
        char authhdr[IMS_SIP_TR_MAX_MSG];
        size_t alen = ims_sip_authorization_build(authhdr, sizeof authhdr, &d, true);
        if (alen == 0) return false;
        /* RFC 3329 2.3: when the P-CSCF advertised ipsec-3gpp in Security-Server
         * and we installed the matching SAs, the authenticated REGISTER must
         * carry Security-Verify echoing the negotiated offer. */
        if (t->sec_server_valid && t->sec_server[0]) {
            int w = snprintf(authhdr + alen, sizeof authhdr - alen,
                             "Security-Verify: %s\r\n", t->sec_server);
            if (w > 0 && alen + (size_t)w < sizeof authhdr) alen += (size_t)w;
        }
        /* authhdr already ends with \r\n; rebuild message = head + auth + tail. */
        if (head + alen + (mlen - head) > sizeof t->scratch) return false;
        memcpy(t->scratch, out, head);
        memcpy(t->scratch + head, authhdr, alen);
        memcpy(t->scratch + head + alen, out + head, mlen - head);
        t->scratch_len = (unsigned)(head + alen + (mlen - head));
        wipe(authhdr, sizeof authhdr);
    } else {
        if (n > sizeof t->scratch) return false;
        memcpy(t->scratch, out, n);
        t->scratch_len = (unsigned)n;
    }
    wipe(out, sizeof out);
    return send_scratch(t);
}

bool ims_sip_tr_start(struct ims_sip_tr *t)
{
    if (!t || t->phase != IMS_SIP_TR_IDLE) return false;
    /* A carried-over hold must still be respected: never send early. */
    if (t->next_action_ms) return false;
    if (!send_register(t, false)) return false;
    t->phase = (t->cfg.security_first && t->cfg.sec_offer && *t->cfg.sec_offer)
                   ? IMS_SIP_TR_SECURE_REGISTER_SENT : IMS_SIP_TR_REGISTER_SENT;
    t->attempt = 0;
    t->deadline_ms = 0; /* set by the caller's tick on transition; fill here too */
    return true;
}

/* ---- response line + header parsing (bounded) ---- */
static int sip_status(const uint8_t *msg, size_t len)
{
    /* "SIP/2.0 <code> <reason>\r\n" */
    if (!msg || len < 12) return 0;
    if (memcmp(msg, "SIP/2.0 ", 8) != 0) return 0;
    const uint8_t *p = msg + 8;
    if (p[0] < '1' || p[0] > '6' ||
        p[1] < '0' || p[1] > '9' || p[2] < '0' || p[2] > '9') return 0;
    int code = (p[0]-'0')*100 + (p[1]-'0')*10 + (p[2]-'0');
    return code;
}

/* Find a header by name (case-sensitive per codec convention), return a
 * pointer to the value (after ": ") and set *vlen. Bounded, returns NULL if
 * absent. */
static const uint8_t *header(const uint8_t *msg, size_t len, const char *name,
                             size_t *vlen)
{
    size_t nlen = strlen(name);
    if (len < nlen + 2) return NULL;
    const uint8_t *p = msg;
    const uint8_t *end = msg + len;
    /* Skip the response line (first CRLF). */
    const uint8_t *line_end = memchr(p, '\n', (size_t)(end-p));
    if (!line_end) return NULL;
    p = line_end + 1;
    while (p + nlen + 1 < end) {
        const uint8_t *le = memchr(p, '\n', (size_t)(end-p));
        if (!le) break;
        /* line = p .. le (exclusive of CR). */
        size_t llen = (size_t)(le - p);
        if (llen >= nlen + 1 && p[nlen] == ':' &&
            memcmp(p, name, nlen) == 0) {
            const uint8_t *v = p + nlen + 1;
            while (v < le && (*v == ' ' || *v == '\t')) v++;
            size_t vl = (size_t)(le - v);
            /* strip trailing CR */
            if (vl && v[vl-1] == '\r') vl--;
            if (vl && v[vl-1] == ' ') vl--;
            if (vlen) *vlen = vl;
            return v;
        }
        p = le + 1;
    }
    return NULL;
}

static bool nonce_and_realm(struct ims_sip_tr *t, const uint8_t *msg, size_t len)
{
    size_t vlen = 0;
    const uint8_t *v = header(msg, len, "WWW-Authenticate", &vlen);
    if (!v) v = header(msg, len, "Proxy-Authenticate", &vlen);
    if (!v) return false;
    char hdr[512];
    if (vlen >= sizeof hdr) return false;
    memcpy(hdr, v, vlen);
    hdr[vlen] = 0;
    char realm[IMS_SIP_TR_REALM_MAX], nonce[IMS_SIP_TR_NONCE_MAX];
    char qop[16], alg[24], cnonce[24];
    if (!ims_sip_challenge_parse(hdr, vlen, realm, nonce, qop, alg, cnonce))
        return false;
    /* Only AKAv1-MD5 / AKAv2-MD5 are accepted (IMS AKA). MD5 rejected by the
     * codec already. */
    if (strcmp(alg, "AKAv1-MD5") != 0 && strcmp(alg, "AKAv2-MD5") != 0)
        return false;
    memcpy(t->realm, realm, sizeof t->realm);
    memcpy(t->nonce, nonce, sizeof t->nonce);
    memcpy(t->qop, qop, sizeof t->qop);
    memcpy(t->alg, alg, sizeof t->alg);
    memcpy(t->cnonce, cnonce, sizeof t->cnonce);
    /* RFC 3329: capture the P-CSCF's Security-Server ipsec-3gpp offer so the
     * authenticated REGISTER can mirror it (Security-Verify) and the caller
     * can install the matching SAs. Absent Security-Server is not fatal: the
     * network may secure the access leg differently (e.g. TLS). */
    size_t svlen = 0;
    const uint8_t *sv = header(msg, len, "Security-Server", &svlen);
    t->sec_server_valid = false;
    t->sec_server[0] = 0;
    if (sv && svlen) {
        char svh[480];
        if (svlen < sizeof svh) {
            memcpy(svh, sv, svlen);
            if (ims_sip_security_server(svh, svlen, t->sec_server,
                                        sizeof t->sec_server) &&
                t->sec_server[0])
                t->sec_server_valid = true;
        }
    }
    /* The nonce for AKA is base64(RAND||AUTN). Decode to hand RAND/AUTN to the
     * legitimate USIM AKA path (iil_auth.c). We do NOT store the raw here. */
    return true;
}

/* Parse Retry-After (delta-seconds, RFC 3261 20.38). Bounded 0..86400;
 * returns 0 if absent/unparseable so the caller falls back to its default. */
static uint32_t retry_after_seconds(const uint8_t *msg, size_t len)
{
    size_t vlen = 0;
    const uint8_t *v = header(msg, len, "Retry-After", &vlen);
    if (!v || vlen == 0) return 0;
    uint32_t secs = 0;
    for (size_t i = 0; i < vlen && i < 10; i++) {
        if (v[i] < '0' || v[i] > '9') break;
        secs = secs * 10u + (uint32_t)(v[i] - '0');
    }
    if (secs > 86400u) secs = 86400u;
    return secs;
}

void ims_sip_tr_feed(struct ims_sip_tr *t, const uint8_t *msg, size_t len)
{
    if (!t || !msg || len == 0 || len > IMS_SIP_TR_MAX_REPLY) return;
    int code = sip_status(msg, len);
    if (code == 0) return;
    switch (t->phase) {
    case IMS_SIP_TR_REGISTER_SENT:
    case IMS_SIP_TR_SECURE_REGISTER_SENT:
    case IMS_SIP_TR_AUTH_SENT:
        if (code == 401 || code == 407) {
            if (nonce_and_realm(t, msg, len)) {
                t->phase = IMS_SIP_TR_CHALLENGED;
                t->deadline_ms = 0;
                /* The caller must now obtain RES via the legitimate USIM AKA
                 * (this module never performs SIM access). */
            } else {
                t->phase = IMS_SIP_TR_FAILED;
            }
        } else if (code >= 200 && code < 300) {
            t->phase = IMS_SIP_TR_REGISTERED;
            t->retry_waits = 0;
            t->next_action_ms = 0;
        } else if (code == 480 || code == 503) {
            /* "Temporarily Unavailable" from the registrar (typically with
             * Retry-After). This is a service-unavailability response, NOT a
             * definitive subscription/permanent failure: honor the interval
             * and try a fresh REGISTER afterwards (bounded). */
            t->retry_after_s = retry_after_seconds(msg, len);
            if (t->retry_after_s == 0) t->retry_after_s = 180u;
            t->deadline_ms = 0;   /* tick schedules from now */
            t->next_action_ms = 0; /* tick fills the ABSOLUTE hold */
            t->phase = IMS_SIP_TR_RETRY_WAIT;
        } else if (code == 403 || code == 404 || code == 500) {
            t->phase = IMS_SIP_TR_FAILED;
        }
        break;
    case IMS_SIP_TR_DEREG_SENT:
        if (code >= 200 && code < 300) t->phase = IMS_SIP_TR_IDLE;
        break;
    default:
        break;
    }
}

bool ims_sip_tr_auth(struct ims_sip_tr *t, const uint8_t *res, size_t res_len)
{
    if (!t || t->phase != IMS_SIP_TR_CHALLENGED) return false;
    if (!res || res_len < 4 || res_len > 16) return false;
    size_t blen = ims_base64_encode(res, res_len, t->res_b64, sizeof t->res_b64);
    if (blen == 0) return false;
    t->res_b64[blen] = 0;
    /* The authenticated REGISTER is sent on the next tick (so the caller can
     * also install IPsec from CK/IK first). */
    return true;
}

bool ims_sip_tr_security_params(const struct ims_sip_tr *t,
                                char *out_offer, size_t offer_cap,
                                char *local_ip, size_t lip_cap,
                                char *remote_ip, size_t rip_cap, int *family)
{
    if (!t || !t->sec_server_valid || !t->sec_server[0]) return false;
    if (out_offer && offer_cap) {
        size_t n = strlen(t->sec_server);
        if (n >= offer_cap) n = offer_cap - 1;
        memcpy(out_offer, t->sec_server, n);
        out_offer[n] = 0;
    }
    if (local_ip && lip_cap) {
        size_t n = strlen(t->cfg.local_ip);
        if (n >= lip_cap) n = lip_cap - 1;
        memcpy(local_ip, t->cfg.local_ip, n); local_ip[n] = 0;
    }
    if (remote_ip && rip_cap) {
        size_t n = strlen(t->cfg.pcscf);
        if (n >= rip_cap) n = rip_cap - 1;
        memcpy(remote_ip, t->cfg.pcscf, n); remote_ip[n] = 0;
    }
    if (family) *family = strchr(t->cfg.pcscf, ':') ? 10 /*AF_INET6*/ : 2 /*AF_INET*/;
    return true;
}

bool ims_sip_tr_deregister(struct ims_sip_tr *t)
{
    if (!t || t->phase != IMS_SIP_TR_REGISTERED) return false;
    /* Build a REGISTER with expires=0. The codec always emits expires=600000;
     * a deregister is handled by sending an unauthenticated REGISTER with
     * expires=0. For correctness we reuse start() but override Contact expiry
     * is out of scope for the codec; instead mark phase and let the caller
     * rebuild. Simplest legitimate path: send the authenticated-by-now empty
     * REGISTER. We send a plain (no Contact) REGISTER. */
    char out[IMS_SIP_TR_MAX_MSG];
    size_t n = ims_sip_register_build(out, sizeof out,
        t->cfg.impu, t->cfg.impi, t->cfg.pcscf, t->cfg.local_ip,
        t->cfg.port, NULL);
    if (n == 0) return false;
    if (n > sizeof t->scratch) return false;
    memcpy(t->scratch, out, n);
    t->scratch_len = (unsigned)n;
    wipe(out, sizeof out);
    if (!send_scratch(t)) return false;
    t->phase = IMS_SIP_TR_DEREG_SENT;
    return true;
}

bool ims_sip_tr_submit_sms(struct ims_sip_tr *t, const char *to,
                           const uint8_t *tpdu, size_t tpdu_len,
                           uint8_t rp_ref)
{
    if (!t || !to || !tpdu || tpdu_len == 0) return false;
    /* Build the RP-DATA body (application/vnd.3gpp.sms). SMSC is not used on
     * the IMS path: a zero-length SMSC address is encoded as 0x00. */
    /* Empty-but-valid SMSC address (Length=1, TOA only, no digits). The IMS
     * path does not require a real SMSC; the RP-Destination-Address is opaque.
     * The codec requires slen>=2 (length byte + at least a TOA byte). */
    uint8_t smsc[2] = {1, 0x91};
    uint8_t rp[300];
    size_t rn = ims_rp_submit(rp, sizeof rp, rp_ref, smsc, sizeof smsc,
                              tpdu, tpdu_len);
    if (rn == 0) return false;
    /* Home domain = the IMPU host (registration registrar/domain). */
    const char *at = strchr(t->cfg.impu, '@');
    char home[IMS_SIP_TR_HOST_MAX + 64] = {0};
    if (at) snprintf(home, sizeof home, "%s", at + 1);
    char out[IMS_SIP_TR_MAX_MSG];
    size_t n = ims_sip_message_build_ex(out, sizeof out,
        t->cfg.impu, home, to, t->cfg.local_ip, t->cfg.port,
        /* The P-CSCF is always the outbound proxy for IMS SMS; without a
         * proper scheme it becomes "sip:<pcscf>;lr" (correct for an IP). */
        t->cfg.pcscf,
        (uint16_t)(++t->cseq & 0xffff), rp, rn);
    wipe(rp, sizeof rp);
    if (n == 0) return false;
    if (n > sizeof t->scratch) return false;
    memcpy(t->scratch, out, n);
    t->scratch_len = (unsigned)n;
    wipe(out, sizeof out);
    return send_scratch(t);
}

enum ims_sip_tr_phase ims_sip_tr_tick(struct ims_sip_tr *t, uint64_t now_ms, bool ready)
{
    if (!t) return IMS_SIP_TR_IDLE;
    if (!ready) {
        /* Network/bearer loss: fall back to idle and re-arm on next ready. */
        t->phase = IMS_SIP_TR_IDLE;
        t->deadline_ms = 0;
        return t->phase;
    }
    /* A carried-over network hold gates any outbound REGISTER while we are in
     * a pre-send state (e.g. after a re-open). RETRY_WAIT is handled by its own
     * deadline below, which also carries the retry counter. */
    if (t->next_action_ms && t->phase != IMS_SIP_TR_RETRY_WAIT) {
        if (now_ms < t->next_action_ms) return t->phase;
        t->next_action_ms = 0;   /* hold elapsed: a fresh REGISTER is permitted */
    }
    switch (t->phase) {
    case IMS_SIP_TR_IDLE:
        /* A registered state falls back to idle only when explicitly
         * deregistered or on loss; otherwise start registration. */
        break;
    case IMS_SIP_TR_CHALLENGED:
        /* Once RES has been stored and the caller installed IPsec, send the
         * authenticated REGISTER. We gate on a non-empty res_b64. */
        if (t->res_b64[0]) {
            if (send_register(t, true)) {
                t->phase = IMS_SIP_TR_AUTH_SENT;
                t->deadline_ms = now_ms + SREG_TIMEOUT_MS;
            }
        }
        break;
    case IMS_SIP_TR_REGISTER_SENT:
    case IMS_SIP_TR_SECURE_REGISTER_SENT:
    case IMS_SIP_TR_AUTH_SENT:
        if (!t->deadline_ms) t->deadline_ms = now_ms + SREG_TIMEOUT_MS;
        if (t->deadline_ms && now_ms >= t->deadline_ms) {
            /* No response within the window: retry (bounded) or fail. */
            if (++t->attempt >= SREG_ATTEMPT_LIMIT) {
                t->phase = IMS_SIP_TR_FAILED;
            } else {
                t->phase = (t->cfg.security_first && t->cfg.sec_offer && *t->cfg.sec_offer)
                               ? IMS_SIP_TR_SECURE_REGISTER_SENT : IMS_SIP_TR_REGISTER_SENT;
                t->deadline_ms = now_ms + SREG_RETRY_MS;
                if (!send_register(t, false)) t->phase = IMS_SIP_TR_FAILED;
            }
        }
        break;
    case IMS_SIP_TR_RETRY_WAIT:
        if (!t->deadline_ms) {
            /* A re-open carries the absolute hold in place of the relative
             * deadline; adopt it so the remaining wait is not extended. */
            uint64_t base = t->next_action_ms ? t->next_action_ms
                                              : now_ms + (uint64_t)t->retry_after_s * 1000u;
            t->deadline_ms = base;
            t->next_action_ms = base;
        }
        if (now_ms >= t->deadline_ms) {
            if (t->retry_waits >= 8u) { t->phase = IMS_SIP_TR_FAILED; break; }
            t->retry_waits++;
            t->attempt = 0;
            t->deadline_ms = 0;
            /* Hold already cleared by the top-of-tick hold check; send. */
            t->next_action_ms = 0;
            if (!send_register(t, false)) { t->phase = IMS_SIP_TR_FAILED; break; }
            t->phase = (t->cfg.security_first && t->cfg.sec_offer && *t->cfg.sec_offer)
                           ? IMS_SIP_TR_SECURE_REGISTER_SENT : IMS_SIP_TR_REGISTER_SENT;
        }
        break;
    case IMS_SIP_TR_REGISTERED:
        /* Long-lived: refresh by deregister+register when the deadline passes.
         * The 600s expiry from the Contact header requires a refresh; we
         * trigger it via a fresh REGISTER. */
        if (t->deadline_ms && now_ms >= t->deadline_ms) {
            if (!send_register(t, false)) { t->phase = IMS_SIP_TR_FAILED; }
            else { t->phase = IMS_SIP_TR_REGISTER_SENT; }
        }
        break;
    default:
        break;
    }
    return t->phase;
}

enum ims_sip_tr_msg_ev ims_sip_tr_classify(const uint8_t *msg, size_t len, int *code)
{
    struct ims_sip_response r;
    if (!ims_sip_response_parse(msg, len, &r)) return IMS_SIP_TR_MSG_NONE;
    if (code) *code = r.code;
    /* Only a response whose CSeq method is MESSAGE belongs to a submission
     * transaction. REGISTER replies are handled by the registration FSM and
     * must never be mistaken for an SMS result. */
    if (strcmp(r.cseq_method, "MESSAGE") != 0) return IMS_SIP_TR_MSG_NONE;
    if (r.code >= 100 && r.code < 200) return IMS_SIP_TR_MSG_PROVISIONAL;
    if (r.code >= 200 && r.code < 300) return IMS_SIP_TR_MSG_ACCEPTED;
    if (r.code >= 300) return IMS_SIP_TR_MSG_REJECTED;
    return IMS_SIP_TR_MSG_NONE;
}
