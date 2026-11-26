/* SPDX-License-Identifier: GPL-2.0-only
 *
 * ims_init.c — native IMS capability + SMS-over-IP preference initialization.
 *
 * See ims_init.h. The runtime queries/sets device preferences and reports
 * that the native AP VoLTE backend is not ready. Previously rejected SDM
 * SMS probes are retained as serializers but not repeated by this lifecycle.
 */
#include "ims_init.h"
#include "fmt_rx.h"
#include <string.h>

#define IMS_INIT_ATTEMPT_LIMIT 4u
#define IMS_INIT_STEP_TIMEOUT_MS 8000u
#define IMS_INIT_RETRY_MS 4000u

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
{
    /* `done` means the REGISTRATION GATE (SetDeviceCapa ack) is satisfied.
     * The best-effort SMS-over-IP arming never blocks registration, even when
     * it ends in FAILED (sub=26/32 are rejected by the modem with 0x8001). */
    return i && i->done;
}

const char *ims_init_phase_name(enum ims_init_phase p)
{
    static const char *const n[] = {"idle","send-get","wait-get-ack",
                                    "send-capa","wait-ack","send-sms-fmt",
                                    "wait-sms-fmt","send-sms-oip","wait-sms-oip",
                                    "send-volte-state","wait-volte-state",
                                    "done","failed"};
    return (p <= IMS_INIT_FAILED) ? n[p] : "unknown";
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
        if (i->phase_deadline_ms && now_ms < i->phase_deadline_ms) break;
        if (now_ms >= i->next_action_ms && i->attempt < IMS_INIT_ATTEMPT_LIMIT) {
            i->attempt++;
            struct fmt_tx_frame f;
            uint8_t seq = 0;
            if (fmt_tx_get_device_capa(&f) &&
                i->write(&f, &seq, i->user)) {
                i->last_write_seq = seq;
                i->phase_deadline_ms = now_ms + IMS_INIT_STEP_TIMEOUT_MS;
                i->phase = IMS_INIT_WAIT_GET_ACK;
            } else {
                i->next_action_ms = now_ms + IMS_INIT_RETRY_MS;
            }
        } else if (i->attempt >= IMS_INIT_ATTEMPT_LIMIT) {
            i->phase = IMS_INIT_FAILED;
        }
        break;
    case IMS_INIT_WAIT_GET_ACK:
        if (now_ms >= i->phase_deadline_ms) {
            i->phase_deadline_ms = 0;
            i->next_action_ms = 0;
            i->phase = IMS_INIT_SEND_GET;
        }
        break;
    case IMS_INIT_SEND_CAPA:
        if (i->phase_deadline_ms && now_ms < i->phase_deadline_ms) break;
        if (now_ms >= i->next_action_ms && i->attempt < IMS_INIT_ATTEMPT_LIMIT) {
            i->attempt++;
            struct fmt_tx_frame f;
            uint8_t seq = 0;
            /* Truthful KPN 204-08 capability: PS-only (IMS/VoLTE) voice domain. */
            if (fmt_tx_set_device_capa(&f, FMT_TX_VOICE_DOMAIN_PS_ONLY,
                                       FMT_TX_VOICE_DOMAIN_PS_ONLY) &&
                i->write(&f, &seq, i->user)) {
                i->last_write_seq = seq;
                i->phase_deadline_ms = now_ms + IMS_INIT_STEP_TIMEOUT_MS;
                i->phase = IMS_INIT_WAIT_ACK;
            } else {
                i->next_action_ms = now_ms + IMS_INIT_RETRY_MS;
            }
        } else if (i->attempt >= IMS_INIT_ATTEMPT_LIMIT) {
            i->phase = IMS_INIT_FAILED;
        }
        break;
    case IMS_INIT_WAIT_ACK:
        if (now_ms >= i->phase_deadline_ms) {
            i->phase_deadline_ms = 0;
            /* Re-drive capability on timeout (bounded). */
            i->next_action_ms = 0;
            i->phase = IMS_INIT_SEND_CAPA;
        }
        break;
    case IMS_INIT_SEND_SMS_FMT:
        if (i->phase_deadline_ms && now_ms < i->phase_deadline_ms) break;
        if (now_ms >= i->next_action_ms && i->attempt < IMS_INIT_ATTEMPT_LIMIT) {
            i->attempt++;
            struct fmt_tx_frame f;
            uint8_t seq = 0;
            /* Arm SMS-over-IP format: 3GPP SMS-over-IMS (KPN 204-08). */
            if (fmt_tx_sdm_ims_sms_fmt(&f, FMT_TX_SDM_SMSOVERIP_FORMAT_3GPP) &&
                i->write(&f, &seq, i->user)) {
                i->last_write_seq = seq;
                i->phase_deadline_ms = now_ms + IMS_INIT_STEP_TIMEOUT_MS;
                i->phase = IMS_INIT_WAIT_SMS_FMT;
            } else {
                i->next_action_ms = now_ms + IMS_INIT_RETRY_MS;
            }
        } else if (i->attempt >= IMS_INIT_ATTEMPT_LIMIT) {
            i->phase = IMS_INIT_FAILED;
        }
        break;
    case IMS_INIT_WAIT_SMS_FMT:
        if (now_ms >= i->phase_deadline_ms) {
            i->phase_deadline_ms = 0;
            i->next_action_ms = 0;
            i->phase = IMS_INIT_SEND_SMS_FMT;
        }
        break;
    case IMS_INIT_SEND_SMS_OIP:
        if (i->phase_deadline_ms && now_ms < i->phase_deadline_ms) break;
        if (now_ms >= i->next_action_ms && i->attempt < IMS_INIT_ATTEMPT_LIMIT) {
            i->attempt++;
            struct fmt_tx_frame f;
            uint8_t seq = 0;
            /* Enable SMS-over-IP transport. */
            if (fmt_tx_sdm_ims_sms_over_ip(&f, FMT_TX_SDM_SMSOVERIP_ENABLE) &&
                i->write(&f, &seq, i->user)) {
                i->last_write_seq = seq;
                i->phase_deadline_ms = now_ms + IMS_INIT_STEP_TIMEOUT_MS;
                i->phase = IMS_INIT_WAIT_SMS_OIP;
            } else {
                i->next_action_ms = now_ms + IMS_INIT_RETRY_MS;
            }
        } else if (i->attempt >= IMS_INIT_ATTEMPT_LIMIT) {
            i->phase = IMS_INIT_FAILED;
        }
        break;
    case IMS_INIT_WAIT_SMS_OIP:
        if (now_ms >= i->phase_deadline_ms) {
            i->phase_deadline_ms = 0;
            i->next_action_ms = 0;
            i->phase = IMS_INIT_SEND_SMS_OIP;
        }
        break;
    case IMS_INIT_SEND_VOLTE_STATE:
        if (i->phase_deadline_ms && now_ms < i->phase_deadline_ms) break;
        if (now_ms >= i->next_action_ms && i->attempt < IMS_INIT_ATTEMPT_LIMIT) {
            i->attempt++;
            struct fmt_tx_frame f;
            uint8_t seq = 0;
            /* No native SIP backend is connected. Report that truthfully;
             * this state report cannot initiate registration. */
            if (fmt_tx_set_volte_state_notification(&f, false) &&
                i->write(&f, &seq, i->user)) {
                i->last_write_seq = seq;
                i->phase_deadline_ms = now_ms + IMS_INIT_STEP_TIMEOUT_MS;
                i->phase = IMS_INIT_WAIT_VOLTE_STATE;
            } else {
                i->next_action_ms = now_ms + IMS_INIT_RETRY_MS;
            }
        } else if (i->attempt >= IMS_INIT_ATTEMPT_LIMIT) {
            i->phase = IMS_INIT_FAILED;
        }
        break;
    case IMS_INIT_WAIT_VOLTE_STATE:
        if (now_ms >= i->phase_deadline_ms) {
            i->phase_deadline_ms = 0;
            i->next_action_ms = 0;
            i->phase = IMS_INIT_SEND_VOLTE_STATE;
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
    if (!i || ack_seq != i->last_write_seq) return;
    if (i->phase == IMS_INIT_WAIT_GET_ACK) {
        /* The modem answered GetDeviceCapa with a direct MISC sub=45 response
         * (2-byte VoiceDomainPref readback). That is the authoritative query
         * completion; advance to the SetDeviceCapa advertisement stage. */
        i->attempt = 0;
        i->phase_deadline_ms = 0;
        i->next_action_ms = 0;
        i->phase = IMS_INIT_SEND_CAPA;
    }
}

void ims_init_gen_result(struct ims_init *i, uint16_t result, uint8_t ack_seq)
{
    if (!i || ack_seq != i->last_write_seq) return;
    /* GEN responses acknowledge SetDeviceCapa/SmsFmt/SmsOverIP writes. */
    switch (i->phase) {
    case IMS_INIT_WAIT_ACK:
        /* Acknowledged capability configuration, not IMS registration. The
         * old SDM probes were already rejected; do not repeat those probes. */
        if (result == FMT_RX_GEN_OK) {
            i->done = true;
            i->attempt = 0;
            i->phase_deadline_ms = 0;
            i->next_action_ms = 0;
            i->phase = IMS_INIT_SEND_VOLTE_STATE;
        } else {
            i->done = false;
            i->phase_deadline_ms = 0;
            i->next_action_ms = 0;
            i->phase = IMS_INIT_SEND_CAPA;
        }
        break;
    case IMS_INIT_WAIT_SMS_FMT:
        /* Best-effort: any ack result advances to SMS_OIP; done remains set. */
        i->attempt = 0;
        i->phase_deadline_ms = 0;
        i->next_action_ms = 0;
        i->phase = IMS_INIT_SEND_SMS_OIP;
        break;
    case IMS_INIT_WAIT_SMS_OIP:
        /* Best-effort: SMS-over-IP arming done. Advance to the VoLTE
         * state-notification handshake (the last arming step before done). */
        i->attempt = 0;
        i->phase_deadline_ms = 0;
        i->next_action_ms = 0;
        i->phase = IMS_INIT_SEND_VOLTE_STATE;
        break;
    case IMS_INIT_WAIT_VOLTE_STATE:
        /* VoLTE-state notification acknowledged (or rejected) — best-effort.
         * The registration gate (done) is already true; don't clear it. */
        i->attempt = 0;
        i->phase_deadline_ms = 0;
        i->phase = IMS_INIT_DONE;
        break;
    default:
        break;
    }
}
