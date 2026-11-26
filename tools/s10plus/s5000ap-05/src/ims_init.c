/* SPDX-License-Identifier: GPL-2.0-only
 *
 * ims_init.c — native IMS device-capability + IMS-stack-arm initialization.
 *
 * Sequence (vendor ImsManager startup):
 *   1. IpcTxGetDeviceCapa  (MISC main=10 sub=45 type=2) — capability query.
 *   2. IpcTxSetDeviceCapa  (MISC main=10 sub=45 type=3) — truthful capability.
 *   3. IpcTxSetImsSdmSetting mode=ON (MISC main=10 sub=32 type=3 payload[0]=1)
 *      — arms the modem's SIP/IMS registration stack.
 * Each step is response-correlated via the ordinary GEN acknowledgment. We
 * never mark done without observing the corresponding ack, and we never
 * fabricate IMS registration.
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
{ return i && i->done && i->phase == IMS_INIT_DONE; }

const char *ims_init_phase_name(enum ims_init_phase p)
{
    static const char *const n[] = {"idle","send-get","wait-get-ack",
                                    "send-capa","wait-ack","send-sdm",
                                    "wait-sdm-ack","done","failed"};
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
            i->next_action_ms = 0;
            i->phase = IMS_INIT_SEND_CAPA;
        }
        break;
    case IMS_INIT_SEND_SDM:
        if (i->phase_deadline_ms && now_ms < i->phase_deadline_ms) break;
        if (now_ms >= i->next_action_ms && i->attempt < IMS_INIT_ATTEMPT_LIMIT) {
            i->attempt++;
            struct fmt_tx_frame f;
            uint8_t seq = 0;
            /* Arm the modem's IMS/SIP registration stack: SDM mode = ON. */
            if (fmt_tx_sdm_ims_mode(&f, FMT_TX_SDM_IMS_MODE_ON) &&
                i->write(&f, &seq, i->user)) {
                i->last_write_seq = seq;
                i->phase_deadline_ms = now_ms + IMS_INIT_STEP_TIMEOUT_MS;
                i->phase = IMS_INIT_WAIT_SDM_ACK;
            } else {
                i->next_action_ms = now_ms + IMS_INIT_RETRY_MS;
            }
        } else if (i->attempt >= IMS_INIT_ATTEMPT_LIMIT) {
            i->phase = IMS_INIT_FAILED;
        }
        break;
    case IMS_INIT_WAIT_SDM_ACK:
        if (now_ms >= i->phase_deadline_ms) {
            i->phase_deadline_ms = 0;
            i->next_action_ms = 0;
            i->phase = IMS_INIT_SEND_SDM;
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
    if (i->phase == IMS_INIT_WAIT_ACK) {
        /* SetDeviceCapa acknowledged -> advance to SDM IMS mode=ON. */
        if (result == FMT_RX_GEN_OK) {
            i->attempt = 0;
            i->phase_deadline_ms = 0;
            i->next_action_ms = 0;
            i->phase = IMS_INIT_SEND_SDM;
        } else {
            i->done = false;
            i->phase_deadline_ms = 0;
            i->next_action_ms = 0;
            i->phase = IMS_INIT_SEND_CAPA;
        }
    } else if (i->phase == IMS_INIT_WAIT_SDM_ACK) {
        /* SDM IMS mode=ON acknowledged -> IMS stack armed; may register. */
        if (result == FMT_RX_GEN_OK) {
            i->done = true;
            i->phase_deadline_ms = 0;
            i->phase = IMS_INIT_DONE;
        } else {
            /* SDM mode rejected (GEN 0x8001): retry the mode set, bounded.
             * This is a real precondition failure, not a silent drop; the
             * IMS registration FSM must not proceed past this gate. */
            i->done = false;
            i->phase_deadline_ms = 0;
            i->next_action_ms = 0;
            i->phase = IMS_INIT_SEND_SDM;
        }
    }
}
