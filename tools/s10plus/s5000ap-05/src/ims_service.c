/* SPDX-License-Identifier: GPL-2.0-only
 *
 * ims_service.c — native IMS registration-driving state machine for the
 * S5000AP (Shannon) modem-over-SIPC5.
 *
 * The modem firmware contains a complete IMS/SIP registration + AKA stack.
 * The AP's role is bounded and well-defined:
 *   1. (data-session) establish the `ims` APN PDN alongside the internet bearer.
 *   2. Drive the modem IMS stack with IpcTxImsReqSetRegState (main=22 sub=8).
 *   3. Relay SIM AKA challenges (SEC_IMS_AUTH) back via IpcTxImsAuthResp.
 *   4. Observe the authoritative state reported by IpcRxImsModeChange.
 *
 * TRUTH CONTRACT: this FSM NEVER fabricates registration. `modem_confirmed_-
 * registered` is set only when the modem reports status==1; it is cleared on
 * deregistration/failure. A local IMS PDN flag is NOT proof of carrier
 * admission. No AKA secret or subscriber identifier is stored or logged.
 */
#include "ims_service.h"
#include <string.h>

#define IMS_ATTEMPT_LIMIT 6u
#define IMS_STEP_TIMEOUT_MS 15000u
#define IMS_RETRY_DELAY_MS 10000u

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

void ims_service_close(struct ims_service *s) { if (s) memset(s, 0, sizeof *s); }

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

const char *ims_phase_name(enum ims_phase p)
{
    static const char *const n[] = {
        "idle","wait-pdn","request-reg","wait-auth","wait-registered",
        "registered","deregistering","failed"
    };
    return (p <= IMS_FAILED) ? n[p] : "unknown";
}

enum ims_phase ims_service_tick(struct ims_service *s, uint64_t now_ms,
                                 bool online, bool ims_pdn)
{
    if (!s) return IMS_IDLE;
    s->ims_pdn_up = ims_pdn;

    if (!online) {
        s->modem_confirmed_registered = false;
        s->auth_pending = false;
        if (s->phase != IMS_FAILED) set_phase(s, IMS_IDLE, "offline");
        return s->phase;
    }

    switch (s->phase) {
    case IMS_IDLE:
        s->attempt = 0;
        s->next_action_ms = 0;
        set_phase(s, IMS_WAIT_PDN, "await-ims-pdn");
        break;
    case IMS_WAIT_PDN:
        if (ims_pdn) set_phase(s, IMS_REQUEST_REG, "ims-pdn-up");
        else if (now_ms >= s->next_action_ms) s->next_action_ms = now_ms + 1000;
        break;
    case IMS_REQUEST_REG:
        if (now_ms >= s->next_action_ms) {
            if (s->attempt >= IMS_ATTEMPT_LIMIT) {
                set_phase(s, IMS_FAILED, "attempt-limit");
                break;
            }
            s->attempt++;
            struct fmt_tx_frame f;
            uint8_t seq = 0;
            if (fmt_tx_ims_set_reg_state(&f, FMT_TX_IMS_REGSTATUS_REGISTERED,
                                         FMT_TX_RAT_LTE, FMT_TX_RAT_LTE) &&
                s->write(&f, &seq, s->user)) {
                s->last_write_seq = seq;
                s->auth_pending = false;
                set_phase(s, IMS_WAIT_REGISTERED, "reg-request-sent");
                s->phase_deadline_ms = now_ms + IMS_STEP_TIMEOUT_MS;
            } else {
                s->next_action_ms = now_ms + IMS_RETRY_DELAY_MS;
            }
        }
        break;
    case IMS_WAIT_AUTH:
        /* Waiting for a secure ISIM response. No polling writes. */
        if (now_ms >= s->phase_deadline_ms) {
            s->auth_pending = false;
            set_phase(s, IMS_REQUEST_REG, "auth-timeout");
            s->next_action_ms = now_ms + IMS_RETRY_DELAY_MS;
        }
        break;
    case IMS_WAIT_REGISTERED:
        if (s->modem_confirmed_registered) set_phase(s, IMS_REGISTERED, "modem-confirmed");
        else if (now_ms >= s->phase_deadline_ms) {
            set_phase(s, IMS_REQUEST_REG, "reg-timeout");
            s->next_action_ms = now_ms + IMS_RETRY_DELAY_MS;
        }
        break;
    case IMS_REGISTERED:
        /* No periodic re-drive; the modem maintains registration. */
        break;
    case IMS_FAILED:
        break;
    default:
        break;
    }
    return s->phase;
}

void ims_service_notify_state(struct ims_service *s, const struct fmt_rx_ims_state *st)
{
    if (!s || !st) return;
    if (st->registered) {
        s->modem_confirmed_registered = true;
        if (s->phase == IMS_WAIT_REGISTERED || s->phase == IMS_WAIT_AUTH)
            set_phase(s, IMS_REGISTERED, "modem-confirmed");
    } else if (s->modem_confirmed_registered) {
        s->modem_confirmed_registered = false;
        set_phase(s, IMS_WAIT_PDN, "modem-deregistered");
        s->next_action_ms = 0;
    }
}

void ims_service_auth_challenge(struct ims_service *s, const struct fmt_rx_ims_auth *a)
{
    if (!s || !a || !a->len) return;
    s->auth_pending = true;
    s->phase_deadline_ms = 0; /* recomputed on tick */
    set_phase(s, IMS_WAIT_AUTH, "sim-aka-challenge");
}

void ims_service_auth_ready(struct ims_service *s)
{
    if (!s || !s->auth_pending || s->phase != IMS_WAIT_AUTH) return;
    s->auth_pending = false;
    set_phase(s, IMS_WAIT_REGISTERED, "auth-response-queued");
    s->phase_deadline_ms = 0;
}

void ims_service_gen_result(struct ims_service *s, uint16_t result, uint8_t ack_seq)
{
    if (!s) return;
    (void)ack_seq;
    /* A generic acknowledgment (0x8000) is NOT registration confirmation. Only
     * the modem's status==1 notification (ims_service_notify_state) marks
     * registration. We do not advance the FSM on a generic ack alone. */
    if (result != FMT_RX_GEN_OK && (s->phase == IMS_REQUEST_REG ||
        s->phase == IMS_WAIT_REGISTERED)) {
        set_phase(s, IMS_REQUEST_REG, "modem-rejected");
    }
}
