/* SPDX-License-Identifier: GPL-2.0-only */
#ifndef NUXEL_IMS_SERVICE_H
#define NUXEL_IMS_SERVICE_H
#include <stdint.h>
#include <stdbool.h>
#include "fmt_tx.h"
#include "fmt_rx.h"

/* Post-frame callback (same contract as sms_write). Returns true if the frame
 * was accepted into the bounded TX path; the caller feeds back responses. */
typedef bool (*ims_write_fn)(const struct fmt_tx_frame *f, uint8_t *seq, void *user);
/* Redacted IMS-state diagnostic callback; never carries secrets. */
typedef void (*ims_state_fn)(const char *state, const char *reason, void *user);

enum ims_phase {
    IMS_IDLE = 0,
    IMS_WAIT_PDN,        /* waiting for the ims APN PDN to be established */
    IMS_REQUEST_REG,     /* issuing IpcTxImsReqSetRegState(REGISTERED) */
    IMS_WAIT_AUTH,       /* modem requested SIM AKA; awaiting auth response */
    IMS_WAIT_REGISTERED, /* awaiting confirmed IMS registration */
    IMS_REGISTERED,      /* modem confirmed IMS registration */
    IMS_DEREGISTERING,   /* requesting deregistration */
    IMS_FAILED,          /* bounded retry exhausted / terminal failure */
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
};

bool ims_service_open(struct ims_service *s, ims_write_fn write, ims_state_fn cb, void *user);
void ims_service_close(struct ims_service *s);
/* Advance the IMS registration FSM. `now` is a monotonic ms clock.
 * `online` = CP online + SIM ready + writable transport. `ims_pdn` = the
 * ims APN PDN is actually established (carrier/gate, not a local guess).
 * Returns the current phase. */
enum ims_phase ims_service_tick(struct ims_service *s, uint64_t now_ms,
                                 bool online, bool ims_pdn);
/* Feed an authoritative modem IMS notification (IpcRxImsModeChange or
 * registration response). */
void ims_service_notify_state(struct ims_service *s, const struct fmt_rx_ims_state *st);
/* Feed a SIM AKA challenge (SEC_IMS_AUTH). The service will issue a matching
 * IpcTxImsAuthResp only after a secure ISIM response is supplied. */
void ims_service_auth_challenge(struct ims_service *s, const struct fmt_rx_ims_auth *a);
/* Report that a secure ISIM AKA response is available for submission. */
void ims_service_auth_ready(struct ims_service *s);
/* Report a modem GEN response correlation for the last written IMS frame. */
void ims_service_gen_result(struct ims_service *s, uint16_t result, uint8_t ack_seq);
bool ims_service_registered(const struct ims_service *s);
const char *ims_phase_name(enum ims_phase p);

#endif /* NUXEL_IMS_SERVICE_H */
