/* SPDX-License-Identifier: GPL-2.0-only
 *
 * ims_init.c — native IMS initialization FSM:
 *   device-capability advertisement + IMS SDM configuration.
 *
 * See ims_init.h for the vendor contract. The modem-facing operations are:
 *   1. IpcTxGetDeviceCapa (MISC main=10 sub=45 type=2 request).
 *   2. IpcTxSetDeviceCapa (MISC main=10 sub=45 type=3, payload=[pref1,pref2]).
 *   3. IpcTxSetImsSdmSettings(MODE)     (MISC main=10 sub=32 type=3, [1]).
 *   4. IpcTxSetImsSdmSettings(SMS_FMT)  (MISC main=10 sub=26 type=3, [0]).
 *   5. IpcTxSetImsSdmSettings(SMS_OIP)  (MISC main=10 sub=27 type=3, [1]).
 *   6. IpcTxSetImsSdmSettings(DOMAIN)   (MISC main=10 sub=28 type=3).
 *
 * Each SDM step requires a generic GEN acknowledgment before the FSM may
 * advance. We never mark initialization complete without observing the ack,
 * and we never fabricate IMS registration. */
#include "ims_init.h"
#include "fmt_rx.h"
#include <string.h>

#define IMS_INIT_ATTEMPT_LIMIT 4u
#define IMS_INIT_STEP_TIMEOUT_MS 8000u
#define IMS_INIT_RETRY_MS 4000u

/* KPN 204-08 IMS domain (same FQDN the modem reports as its IMS APN). */
static const char IMS_DOMAIN[] = "ims.mnc008.mcc204.gprs";

bool ims_init_open(struct ims_init *i, ims_init_write_fn write, void *user)
{
    if (!i || !write) return false;
    memset(i, 0, sizeof *i);
    i->write = write;
    i->user = user;
    i->phase = IMS_INIT_IDLE;
    return true;
}

void ims_init_close(struct ims_init *i) { if (i) memset(i, 0, sizeof *i); }

bool ims_init_done(const struct ims_init *i)
{ return i && i->done && i->phase == IMS_INIT_DONE; }

const char *ims_init_phase_name(enum ims_init_phase p)
{
    static const char *const n[] = {
        "idle","send-get","wait-get-ack","send-capa","wait-ack",
        "send-sdm-mode","wait-sdm-mode","send-sdm-fmt","wait-sdm-fmt",
        "send-sdm-oip","wait-sdm-oip","send-sdm-dom","wait-sdm-dom",
        "done","failed"
    };
    return (p <= IMS_INIT_FAILED) ? n[p] : "unknown";
}

/* Build + transmit the frame for the current phase. Returns true when the
 * write was accepted; sets *advance when the phase should move to the next
 * pending-write stage. */
static bool emit_phase(struct ims_init *i, uint64_t now_ms, bool *accepted)
{
    struct fmt_tx_frame f;
    uint8_t seq = 0;
    bool ok = false;
    switch (i->phase) {
    case IMS_INIT_SEND_GET:
        ok = fmt_tx_get_device_capa(&f);
        break;
    case IMS_INIT_SEND_CAPA:
        ok = fmt_tx_set_device_capa(&f, FMT_TX_VOICE_DOMAIN_PS_ONLY,
                                    FMT_TX_VOICE_DOMAIN_PS_ONLY);
        break;
    case IMS_INIT_SEND_SDM_MODE:
        ok = fmt_tx_sdm_ims_mode(&f, FMT_TX_SDM_IMS_MODE_ON);
        break;
    case IMS_INIT_SEND_SDM_FMT:
        ok = fmt_tx_sdm_ims_sms_fmt(&f, 0u /* 3GPP */);
        break;
    case IMS_INIT_SEND_SDM_OIP:
        ok = fmt_tx_sdm_ims_sms_over_ip(&f, 1u /* enabled */);
        break;
    case IMS_INIT_SEND_SDM_DOM:
        ok = fmt_tx_sdm_ims_domain(&f, IMS_DOMAIN);
        break;
    default:
        *accepted = false;
        return false;
    }
    if (ok && i->write(&f, &seq, i->user)) {
        i->last_write_seq = seq;
        i->phase_deadline_ms = now_ms + IMS_INIT_STEP_TIMEOUT_MS;
        *accepted = true;
        return true;
    }
    *accepted = false;
    return false;
}

enum ims_init_phase ims_init_tick(struct ims_init *i, uint64_t now_ms, bool online)
{
    if (!i) return IMS_INIT_IDLE;
    if (!online) {
        i->done = false;
        if (i->phase != IMS_INIT_FAILED) i->phase = IMS_INIT_IDLE;
        return i->phase;
    }
    switch (i->phase) {
    case IMS_INIT_IDLE:
        i->attempt = 0;
        i->next_action_ms = 0;
        i->phase = IMS_INIT_SEND_GET;
        break;

    case IMS_INIT_SEND_GET:
    case IMS_INIT_SEND_CAPA:
    case IMS_INIT_SEND_SDM_MODE:
    case IMS_INIT_SEND_SDM_FMT:
    case IMS_INIT_SEND_SDM_OIP:
    case IMS_INIT_SEND_SDM_DOM:
        if (i->phase_deadline_ms && now_ms < i->phase_deadline_ms) break;
        if (now_ms >= i->next_action_ms && i->attempt < IMS_INIT_ATTEMPT_LIMIT) {
            i->attempt++;
            bool accepted = false;
            if (emit_phase(i, now_ms, &accepted)) {
                /* advance to the matching wait phase */
                switch (i->phase) {
                case IMS_INIT_SEND_GET: i->phase = IMS_INIT_WAIT_GET_ACK; break;
                case IMS_INIT_SEND_CAPA: i->phase = IMS_INIT_WAIT_ACK; break;
                case IMS_INIT_SEND_SDM_MODE: i->phase = IMS_INIT_WAIT_SDM_MODE; break;
                case IMS_INIT_SEND_SDM_FMT: i->phase = IMS_INIT_WAIT_SDM_FMT; break;
                case IMS_INIT_SEND_SDM_OIP: i->phase = IMS_INIT_WAIT_SDM_OIP; break;
                case IMS_INIT_SEND_SDM_DOM: i->phase = IMS_INIT_WAIT_SDM_DOM; break;
                default: break;
                }
            } else {
                i->next_action_ms = now_ms + IMS_INIT_RETRY_MS;
            }
        } else if (i->attempt >= IMS_INIT_ATTEMPT_LIMIT) {
            i->phase = IMS_INIT_FAILED;
        }
        break;

    case IMS_INIT_WAIT_GET_ACK:
    case IMS_INIT_WAIT_ACK:
    case IMS_INIT_WAIT_SDM_MODE:
    case IMS_INIT_WAIT_SDM_FMT:
    case IMS_INIT_WAIT_SDM_OIP:
    case IMS_INIT_WAIT_SDM_DOM:
        if (now_ms >= i->phase_deadline_ms) {
            i->phase_deadline_ms = 0;
            i->next_action_ms = 0;
            /* Bounded retry of the originating send phase. */
            switch (i->phase) {
            case IMS_INIT_WAIT_GET_ACK: i->phase = IMS_INIT_SEND_GET; break;
            case IMS_INIT_WAIT_ACK: i->phase = IMS_INIT_SEND_CAPA; break;
            case IMS_INIT_WAIT_SDM_MODE: i->phase = IMS_INIT_SEND_SDM_MODE; break;
            case IMS_INIT_WAIT_SDM_FMT: i->phase = IMS_INIT_SEND_SDM_FMT; break;
            case IMS_INIT_WAIT_SDM_OIP: i->phase = IMS_INIT_SEND_SDM_OIP; break;
            case IMS_INIT_WAIT_SDM_DOM: i->phase = IMS_INIT_SEND_SDM_DOM; break;
            default: break;
            }
        }
        break;

    case IMS_INIT_DONE:
    case IMS_INIT_FAILED:
        break;
    }
    return i->phase;
}

void ims_init_capa_response(struct ims_init *i, uint8_t ack_seq)
{
    if (!i) return;
    (void)ack_seq;
    if (i->phase == IMS_INIT_WAIT_GET_ACK) {
        /* The modem answered GetDeviceCapa with a direct MISC sub=45 response
         * (2-byte VoiceDomainPref readback). Advance to SetDeviceCapa. */
        i->attempt = 0;
        i->phase_deadline_ms = 0;
        i->next_action_ms = 0;
        i->phase = IMS_INIT_SEND_CAPA;
    }
}

void ims_init_gen_result(struct ims_init *i, uint16_t result, uint8_t ack_seq)
{
    if (!i) return;
    (void)ack_seq;
    /* Only the SetDeviceCapa and SDM writes are acknowledged via GEN. */
    enum ims_init_phase next;
    switch (i->phase) {
    case IMS_INIT_WAIT_ACK:        next = IMS_INIT_SEND_SDM_MODE; break;
    case IMS_INIT_WAIT_SDM_MODE:   next = IMS_INIT_SEND_SDM_FMT; break;
    case IMS_INIT_WAIT_SDM_FMT:    next = IMS_INIT_SEND_SDM_OIP; break;
    case IMS_INIT_WAIT_SDM_OIP:    next = IMS_INIT_SEND_SDM_DOM; break;
    case IMS_INIT_WAIT_SDM_DOM:    next = IMS_INIT_DONE; break;
    default: return;
    }
    if (result == FMT_RX_GEN_OK) {
        i->attempt = 0;
        i->phase_deadline_ms = 0;
        i->next_action_ms = 0;
        if (next == IMS_INIT_DONE) {
            i->done = true;
            i->phase = IMS_INIT_DONE;
        } else {
            i->phase = next;
        }
    } else {
        /* Re-drive the current stage on non-zero GEN (bounded). */
        i->phase_deadline_ms = 0;
        i->next_action_ms = 0;
        switch (i->phase) {
        case IMS_INIT_WAIT_ACK:      i->phase = IMS_INIT_SEND_CAPA; break;
        case IMS_INIT_WAIT_SDM_MODE: i->phase = IMS_INIT_SEND_SDM_MODE; break;
        case IMS_INIT_WAIT_SDM_FMT:  i->phase = IMS_INIT_SEND_SDM_FMT; break;
        case IMS_INIT_WAIT_SDM_OIP:  i->phase = IMS_INIT_SEND_SDM_OIP; break;
        case IMS_INIT_WAIT_SDM_DOM:  i->phase = IMS_INIT_SEND_SDM_DOM; break;
        default: break;
        }
    }
}
