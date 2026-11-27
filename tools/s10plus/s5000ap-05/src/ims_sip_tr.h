/* SPDX-License-Identifier: GPL-2.0-only
 *
 * ims_sip_tr.h — native SIP/IMS network transport + registration state machine.
 *
 * This is the MISSING "connect the codec to a real transport" layer: it owns a
 * UDP socket for the isolated IMS bearer (CID 2), drives the TS 24.229
 * REGISTER -> 401(AKAv1-MD5) -> REGISTER(Authorization) -> 200 lifecycle, and
 * submits SMS-over-IP via TS 24.341 SIP MESSAGE. It REUSES the bounded,
 * emulation-verified codecs in ims_sip.c / ims_sms.c and does NOT duplicate
 * them.
 *
 * The module is pure-C and transport-callback injectable so the full
 * registration/SMS-over-IP lifecycle is host-testable with a synthetic loopback
 * SIP peer (see tests/test_ims_sip_tr.c). In production radiod binds a real
 * UDP4/UDP6 socket on the IMS bearer interface.
 *
 * SAFETY:
 *   - Never performs IPsec key install (that is ims_security.c's job, invoked
 *     by the caller with CK/IK from the legitimate USIM AKA result).
 *   - Never invents a P-CSCF; the caller supplies the discovered address.
 *   - Never logs RAND/AUTN/RES/CK/IK, PII, or message bodies.
 *   - Bounded buffers; every parse validates length before reading.
 */
#ifndef NUXEL_IMS_SIP_TR_H
#define NUXEL_IMS_SIP_TR_H

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>
#include <sys/types.h>

#ifdef __cplusplus
extern "C" {
#endif

#define IMS_SIP_TR_MAX_MSG    2048u
#define IMS_SIP_TR_MAX_REPLY  4096u
#define IMS_SIP_TR_NONCE_MAX  160u
#define IMS_SIP_TR_REALM_MAX  96u
#define IMS_SIP_TR_ID_MAX     160u
#define IMS_SIP_TR_HOST_MAX   64u

/* Registration phase. Only REGISTERED reflects an authoritative 200 OK
 * (2xx) received from the network; it is never inferred from a transport or
 * modem acknowledgment. */
enum ims_sip_tr_phase {
    IMS_SIP_TR_IDLE = 0,
    IMS_SIP_TR_REGISTER_SENT,   /* initial REGISTER out, awaiting 401/2xx */
    IMS_SIP_TR_SECURE_REGISTER_SENT, /* sec-agree REGISTER out, awaiting 401/2xx */
    IMS_SIP_TR_CHALLENGED,      /* 401 AKAv1-MD5 received; awaiting USIM RES */
    IMS_SIP_TR_AUTH_SENT,       /* authenticated REGISTER out, awaiting 2xx */
    IMS_SIP_TR_REGISTERED,      /* 200 OK received (authoritative) */
    IMS_SIP_TR_DEREG_SENT,      /* deregister in flight */
    IMS_SIP_TR_FAILED,
    IMS_SIP_TR_RETRY_WAIT,      /* 480/503 + Retry-After: back off until the
                                 * network-supplied interval elapses, then a
                                 * fresh REGISTER (does NOT fail permanently;
                                 * Retry-After is the registrar's own gate). */
};

/* Transport callbacks (injectable for host tests; real UDP in production). */
struct ims_sip_tr_io {
    /* Send `len` bytes of a datagram to the configured P-CSCF (already encoded
     * as a target by the transport). Returns true on a full send. */
    bool (*send)(const void *msg, size_t len, void *user);
    /* Deliver one received datagram. The module BOUNDS this to MAX_REPLY and
     * parses exactly one SIP response. */
    void (*recv)(const uint8_t *msg, size_t len, void *user);
};

/* Secret-free digest/identity inputs the registration FSM needs. RES/CK/IK
 * are NOT stored here; the caller supplies base64(RES) only when building the
 * Authorization header and passes CK/IK to ims_security_install externally. */
struct ims_sip_tr_cfg {
    const char *impu;        /* sip:public@... */
    const char *impi;        /* private identity username portion */
    const char *pcscf;       /* discovered P-CSCF host (literal IP or FQDN) */
    const char *local_ip;    /* IMS bearer local address (bind/contact) */
    uint16_t    port;        /* local SIP client port */
    uint16_t    pcscf_port;  /* P-CSCF SIP server port (5060) */
    const char *sec_offer;   /* Security-Client ipsec-3gpp offer, or NULL */
    const char *cell_id;     /* REAL serving ECI (hex) for utran-cell-id-3gpp,
                              * or NULL when unavailable (parameter omitted;
                              * never fabricated). */
    const char *home_plmn;   /* serving PLMN, 5 ASCII digits (e.g. "20408")
                              * for the (MCC||MNC) prefix of utran-cell-id-3gpp.
                              * The parameter needs BOTH this and cell_id; if
                              * either is absent it is omitted, never faked. */
    bool        security_first; /* emit Require/Proxy-Require: sec-agree on the
                                 * initial REGISTER (TS 33.203 7.1). Only set
                                 * when sec_offer is a complete ipsec-3gpp offer. */
};

struct ims_sip_tr {
    /* Owned copies of the config strings (deep-copied on open) so the FSM can
     * outlive the caller's stack buffers. */
    char _impu[IMS_SIP_TR_ID_MAX];
    char _impi[IMS_SIP_TR_ID_MAX];
    char _pcscf[IMS_SIP_TR_HOST_MAX];
    char _local_ip[IMS_SIP_TR_HOST_MAX];
    char _sec_offer[320];
    char _cell_id[24];
    char _home_plmn[8];

    struct ims_sip_tr_cfg cfg;
    struct ims_sip_tr_io  io;
    void *user;

    enum ims_sip_tr_phase phase;
    uint8_t attempt;
    uint64_t deadline_ms;
    /* Retry-After (seconds) from a 480/503; used to schedule the next
     * REGISTER instead of a fixed retry. Capped to keep the loop bounded.
     * SECONDS OF THE LAST NETWORK RETRY-AFTER; 0 = none. A per-SIM hold is
     * additionally derived from this so it survives libc/FSM state resets. */
    uint32_t retry_after_s;
    uint8_t  retry_waits;       /* consecutive Retry-After waits (bounded) */

    char realm[IMS_SIP_TR_REALM_MAX];
    char nonce[IMS_SIP_TR_NONCE_MAX];   /* base64(RAND||AUTN) from 401 */
    char qop[16], alg[24], cnonce[24];
    char res_b64[64];                  /* base64(RES) from the USIM AKA; wiped after auth */
    /* Security-Server offer echoed by a 401/407 (RFC 3329); when set the
     * authenticated REGISTER carries Security-Verify and the caller installs
     * the matching IPsec SAs from CK/IK BEFORE that REGISTER is sent. */
    char sec_server[320];
    bool sec_server_valid;
    uint32_t cseq;
    /* Absolute monotonic time (ms) of the NEXT permitted REGISTER attempt.
     * Carried across a transport re-open so the registrar's Retry-After is
     * honored even when the bearer/socket is re-established mid-backoff.
     * 0 = no hold. Never reset to 0 by a re-open. */
    uint64_t next_action_ms;

    /* Outbound message scratch (REGISTER/MESSAGE); never logged in full. */
    unsigned char scratch[IMS_SIP_TR_MAX_MSG];
    unsigned    scratch_len;
};

/* Open/O init a transport FSM. `io.send`/`io.recv` may be NULL for offline
 * build-only use; they are required for a live exchange.
 *
 * `prev` (optional) is the PREVIOUS FSM instance the caller is about to
 * destroy (typically when re-opening the UDP socket). When supplied, the
 * network-imposed backoff deadline (next_action_ms) and the consecutive
 * Retry-After wait counter are CARRIED OVER, so a socket re-open can never be
 * used to bypass a registrar's Retry-After. All identity/digest material
 * except RES (never carried; it is per-challenge) is re-read from `cfg`. */
bool ims_sip_tr_open(struct ims_sip_tr *t, const struct ims_sip_tr_cfg *cfg,
                     const struct ims_sip_tr_io *io, void *user,
                     const struct ims_sip_tr *prev);
void ims_sip_tr_close(struct ims_sip_tr *t);

/* Advance the FSM. `now_ms` monotonic. `ready` = transport up (socket bound,
 * bearer usable) AND P-CSCF present. Returns the current phase. */
enum ims_sip_tr_phase ims_sip_tr_tick(struct ims_sip_tr *t, uint64_t now_ms, bool ready);

/* Build the initial REGISTER into the transport's scratch and send it (if
 * io.send is set). Returns true on send, false on build/bounds error. */
bool ims_sip_tr_start(struct ims_sip_tr *t);

/* Feed a received SIP response (one datagram). Updates phase on:
 *   401/407 -> CHALLENGED (records realm/nonce if AKAv1-MD5/AKAv2-MD5)
 *   200    -> REGISTERED
 *   403/404/500/503 -> FAILED
 * The caller may inspect phase after the call. */
void ims_sip_tr_feed(struct ims_sip_tr *t, const uint8_t *msg, size_t len);

/* Supply the USIM AKA result RES (raw bytes, 4..16). The module base64-encodes
 * it and, on the next tick, sends the authenticated REGISTER. Returns false if
 * not in CHALLENGED or on an invalid length. Secret is zeroized after use. */
bool ims_sip_tr_auth(struct ims_sip_tr *t, const uint8_t *res, size_t res_len);

/* Snapshot the negotiated ipsec-3gpp parameters for installing IPsec SAs from
 * the CK/IK the USIM AKA returned. `out_offer` receives the negotiated
 * Security-Server offer string (the SAs must mirror the server's SPIs/ports),
 * `local_ip`/`remote_ip`/`family` describe the P-CSCF leg. Returns false when
 * no ipsec-3gpp Security-Server was advertised (network secures otherwise). */
bool ims_sip_tr_security_params(const struct ims_sip_tr *t,
                                char *out_offer, size_t offer_cap,
                                char *local_ip, size_t lip_cap,
                                char *remote_ip, size_t rip_cap, int *family);

/* Initiate de-registration (REGISTER with expires=0). */
bool ims_sip_tr_deregister(struct ims_sip_tr *t);

/* Build a SIP MESSAGE (SMS-over-IP) with an RP-DATA body and send it. Returns
 * true on send. `tpdu`/`tpdu_len` is the TS 23.040 TPDU (SMS-DELIVER PDU). */
bool ims_sip_tr_submit_sms(struct ims_sip_tr *t, const char *to,
                           const uint8_t *tpdu, size_t tpdu_len,
                           uint8_t rp_ref);

/* Classification of a SIP response that is NOT a REGISTER transaction reply.
 * Used to advance the SMS-over-IMS submission (TS 24.341): a MESSAGE's
 * SIP transaction result tells only that the request reached the network; a
 * 2xx to a MESSAGE is a provisional "accepted for delivery", never a proven
 * SMS delivery (only a STATUS-REPORT proves recipient delivery). NON-REGISTER
 * responses are ignored by the REGISTER FSM. */
enum ims_sip_tr_msg_ev {
    IMS_SIP_TR_MSG_NONE = 0,   /* not a response / not a MESSAGE reply */
    IMS_SIP_TR_MSG_ACCEPTED,   /* 2xx to the MESSAGE (SIP transaction accepted) */
    IMS_SIP_TR_MSG_REJECTED,   /* non-2xx final (>=300) to the MESSAGE */
    IMS_SIP_TR_MSG_PROVISIONAL /* 1xx to the MESSAGE */
};
/* Parse `msg`; when it is a final/provisional response to a MESSAGE (the CSeq
 * method is MESSAGE) return the classification and set *code. Any response to
 * a different method (e.g. REGISTER) or a non-response returns NONE. */
enum ims_sip_tr_msg_ev ims_sip_tr_classify(const uint8_t *msg, size_t len, int *code);

/* True only in REGISTERED (authoritative 200 OK), never in CHALLENGED/AUTH_SENT. */
bool ims_sip_tr_registered(const struct ims_sip_tr *t);
const char *ims_sip_tr_phase_name(enum ims_sip_tr_phase ph);

#ifdef __cplusplus
}
#endif
#endif /* NUXEL_IMS_SIP_TR_H */
