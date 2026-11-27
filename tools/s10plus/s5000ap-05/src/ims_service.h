/* SPDX-License-Identifier: GPL-2.0-only */
#ifndef NUXEL_IMS_SERVICE_H
#define NUXEL_IMS_SERVICE_H
#include <stdint.h>
#include <stdbool.h>
#include "fmt_tx.h"
#include "fmt_rx.h"
#include "sipc5_fmt.h"

/* Post-frame callback (same contract as sms_write). Returns true if the frame
 * was accepted into the bounded TX path; the caller feeds back responses. */
typedef bool (*ims_write_fn)(const struct fmt_tx_frame *f, uint8_t *seq, void *user);
/* Redacted IMS-state diagnostic callback; never carries secrets. */
typedef void (*ims_state_fn)(const char *state, const char *reason, void *user);

/* NULL result means timeout, offline, or rejected/malformed response.
 * A result is valid only during the callback; it never confirms SIP registration. */
typedef void (*ims_auth_fn)(const struct fmt_rx_usim_auth *result, void *user);
struct ims_identity {
    bool ready;
    char domain[64], impi[96], impu[100];
    /* MSISDN-derived public identity, when EF_MSISDN was read successfully.
     * Empty until proven by an actual EF_MSISDN read; NEVER fabricated. */
    bool msisdn_impu_valid;
    char msisdn_impu[100];
};
/* TS 23.003 13.2/13.3/13.4B. MNC length must come from subscription data,
 * never guessed from IMSI length. Output is cleared on invalid input. */
bool ims_identity_from_usim(struct ims_identity *out, const uint8_t *imsi,
                            size_t len, unsigned mnc_digits);
/* Replace the public identity with the MSISDN-based IMPU
 * (sip:+<msisdn>@<domain>) when `digits` is a verified E.164 MSISDN read from
 * the subscriber's own EF_MSISDN. The private identity (IMPI) is unchanged —
 * IMS AKA digest uses the IMSI-derived private identity, never the MSISDN. */
bool ims_identity_prefer_msisdn(struct ims_identity *out, const char *digits);
/* Adopt an operator/modem-provisioned IMPU (full public SIP/tel identity) as
 * reported by the modem's IIL registration event. Accepted only when printable
 * and bounded; the IMSI-derived IMPI (private identity) is unchanged. */
bool ims_identity_prefer_impu(struct ims_identity *out, const char *impu);
void ims_identity_clear(struct ims_identity *out);

enum ims_phase {
    IMS_IDLE = 0,
    IMS_WAIT_PDN,        /* waiting for the ims APN PDN to be established */
    IMS_REQUEST_REG,     /* reserved for a future native SIP backend */
    IMS_WAIT_AUTH,       /* reserved; UICC requests use auth_pending */
    IMS_WAIT_REGISTERED, /* awaiting confirmed IMS registration */
    IMS_REGISTERED,      /* authenticated SIP registration, currently unavailable */
    IMS_DEREGISTERING,   /* requesting deregistration */
    IMS_FAILED,          /* terminal failure */
    IMS_WAIT_BACKEND,    /* native SIP registration backend is not connected */
};

struct ims_service {
    ims_write_fn write;
    ims_state_fn state_cb;
    void *user;
    enum ims_phase phase;
    uint8_t attempt;
    bool ims_pdn_up;      /* provided by the data-session/caller */
    bool modem_confirmed_registered;
    bool auth_pending;
    uint64_t next_action_ms;
    uint64_t phase_deadline_ms;
    uint8_t last_write_seq;
    const char *last_reason;
    struct ims_identity identity;
    bool online;
    uint64_t auth_deadline_ms;
    ims_auth_fn auth_done;
    void *auth_user;
};

bool ims_service_open(struct ims_service *s, ims_write_fn write, ims_state_fn cb, void *user);
void ims_service_close(struct ims_service *s);
/* Advance the IMS registration FSM. `now` is a monotonic ms clock.
 * `online` = CP online + SIM ready + writable transport. `ims_pdn` = the
 * ims APN PDN has confirmed attachment, IP and P-CSCF.
 * Returns the current phase. */
enum ims_phase ims_service_tick(struct ims_service *s, uint64_t now_ms,
                                 bool online, bool ims_pdn);
/* Broker a real SIP challenge through the supported USIM interface. One
 * outstanding transaction, exact response correlation, no automatic retry. */
bool ims_service_auth_request(struct ims_service *s, const uint8_t rand[16],
                               const uint8_t autn[16], uint64_t now_ms,
                               ims_auth_fn done, void *user);
void ims_service_receive(struct ims_service *s, const struct nuxel_sipc_fmt *f);
bool ims_service_registered(const struct ims_service *s);
/* Record an AUTHORITATIVE native SIP 200 OK from the connected SIP backend.
 * This is the only valid path to `modem_confirmed_registered`; it is never
 * inferred from an AP-to-modem registration-status relay or a generic
 * acknowledgment. Call when ims_sip_tr_registered() transitions true. */
void ims_service_native_registered(struct ims_service *s, bool registered);
const char *ims_phase_name(enum ims_phase p);

#endif /* NUXEL_IMS_SERVICE_H */
