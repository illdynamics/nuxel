/* SPDX-License-Identifier: GPL-2.0-only
 *
 * ims_sdm.c — readback of the modem's carrier-provisioned IMS SDM settings.
 * See ims_sdm.h. No values are fabricated; every field is populated only from
 * a direct type=2 RESPONSE the modem itself sends for the matching (main=10,
 * sub). Secret/PII is never stored or logged.
 */
#include "ims_sdm.h"
#include <string.h>

#define IMS_SDM_STEP_TIMEOUT_MS 4000u

bool ims_sdm_open(struct ims_sdm *s, ims_sdm_write_fn write, void *user)
{
    if (!s || !write) return false;
    memset(s, 0, sizeof *s);
    s->write = write;
    s->user = user;
    s->phase = IMS_SDM_IDLE;
    return true;
}

/* The modem may answer an SDM GET via the ordinary GEN channel (main=128)
 * with result 0x8000=OK, 0x8001=REJECT, or 0x8003=UNSUPPORTED instead of a
 * direct (main=10) value. On rejection, advance past the query WITHOUT
 * retrying so a dead readback surface never produces a retry storm. */
bool ims_sdm_gen_result(struct ims_sdm *s, uint16_t result, uint8_t ack_seq)
{
    if (!s || !s->next_action_ms) return false;
    if (ack_seq != s->last_write_seq) return false;
    if (result == 0x8000u) return false;   /* OK: still await the direct value */
    /* Reject/unsupported: mark the pending field absent and advance. */
    enum ims_sdm_phase next;
    switch (s->phase) {
    case IMS_SDM_GET_MODE:      next = IMS_SDM_GET_PCSCF; break;
    case IMS_SDM_GET_PCSCF:     next = IMS_SDM_GET_DOMAIN; break;
    case IMS_SDM_GET_DOMAIN:    next = IMS_SDM_GET_SMSOVERIP; break;
    case IMS_SDM_GET_SMSOVERIP: next = IMS_SDM_GET_SMSFMT; break;
    case IMS_SDM_GET_SMSFMT:    next = IMS_SDM_DONE; break;
    default: return false;
    }
    s->phase = next;
    s->next_action_ms = 0;
    s->online_done_seen = (next == IMS_SDM_DONE);
    return true;
}

void ims_sdm_close(struct ims_sdm *s) { if (s) memset(s, 0, sizeof *s); }

const char *ims_sdm_phase_name(enum ims_sdm_phase ph)
{
    static const char *const n[] = {"idle","get-mode","get-pcscf","get-domain",
                                    "get-smsoverip","get-smsfmt","done"};
    return (ph <= IMS_SDM_DONE) ? n[ph] : "unknown";
}

static bool fire(struct ims_sdm *s, uint8_t sub, uint64_t now_ms)
{
    struct fmt_tx_frame f;
    uint8_t seq = 0;
    bool built = false;
    switch (sub) {
    case 32u: built = fmt_tx_sdm_ims_mode_get(&f); break;
    case 34u: built = fmt_tx_sdm_pcscf_get(&f); break;
    case 28u: built = fmt_tx_sdm_ims_domain_get(&f); break;
    case 27u: built = fmt_tx_sdm_ims_sms_over_ip_get(&f); break;
    case 26u: built = fmt_tx_sdm_ims_sms_fmt_get(&f); break;
    default: return false;
    }
    if (!built || !s->write(&f, &seq, s->user)) return false;
    s->pending_sub = sub;
    s->last_write_seq = seq;
    s->next_action_ms = now_ms + IMS_SDM_STEP_TIMEOUT_MS;
    return true;
}

enum ims_sdm_phase ims_sdm_tick(struct ims_sdm *s, uint64_t now_ms, bool online)
{
    if (!s) return IMS_SDM_IDLE;
    if (!online) {
        if (s->phase != IMS_SDM_IDLE) s->phase = IMS_SDM_IDLE;
        s->next_action_ms = 0;
        s->online_done_seen = false;
        return s->phase;
    }
    switch (s->phase) {
    case IMS_SDM_IDLE:
        s->phase = IMS_SDM_GET_MODE;
        s->next_action_ms = 0;
        break;
    case IMS_SDM_GET_MODE:
    case IMS_SDM_GET_PCSCF:
    case IMS_SDM_GET_DOMAIN:
    case IMS_SDM_GET_SMSOVERIP:
    case IMS_SDM_GET_SMSFMT: {
        if (s->next_action_ms && now_ms < s->next_action_ms) break;
        uint8_t sub;
        switch (s->phase) {
        case IMS_SDM_GET_MODE:      sub = 32u; break;
        case IMS_SDM_GET_PCSCF:     sub = 34u; break;
        case IMS_SDM_GET_DOMAIN:    sub = 28u; break;
        case IMS_SDM_GET_SMSOVERIP: sub = 27u; break;
        default:                    sub = 26u; break;
        }
        if (fire(s, sub, now_ms)) break;
        /* Write failed; skip to DONE without retry storm. */
        s->phase = IMS_SDM_DONE;
        break;
    }
    case IMS_SDM_DONE:
        break;
    }
    return s->phase;
}

/* Capture a direct modem RESPONSE. `sub` is the SDM sub (26/27/28/32/34);
 * the modem sends type=2 with ack_seq == our query seq. Only the authoritative
 * modem-provided value is stored; malformed input is dropped. */
bool ims_sdm_receive(struct ims_sdm *s, uint8_t sub, uint8_t ack_seq,
                     const uint8_t *payload, size_t payload_len)
{
    if (!s) return false;
    if (ack_seq != s->last_write_seq || sub != s->pending_sub) return false;
    /* Advance to the next stage regardless of the specific value, so a single
     * empty/missing field cannot wedge the readback. */
    enum ims_sdm_phase next = s->phase;
    switch (s->phase) {
    case IMS_SDM_GET_MODE:      next = IMS_SDM_GET_PCSCF; break;
    case IMS_SDM_GET_PCSCF:     next = IMS_SDM_GET_DOMAIN; break;
    case IMS_SDM_GET_DOMAIN:    next = IMS_SDM_GET_SMSOVERIP; break;
    case IMS_SDM_GET_SMSOVERIP: next = IMS_SDM_GET_SMSFMT; break;
    case IMS_SDM_GET_SMSFMT:    next = IMS_SDM_DONE; break;
    default: return false;
    }
    s->phase = next;
    s->next_action_ms = 0;
    s->online_done_seen = (next == IMS_SDM_DONE);

    switch (sub) {
    case 32u: /* IMS mode: 1-byte payload */
        if (payload_len >= 1) { s->mode = payload[0]; s->mode_valid = true; }
        break;
    case 34u: /* P-CSCF: NUL-terminated string (<=255) */
        if (payload_len >= 1 && payload_len <= 255) {
            size_t n = payload_len;
            if (n > 255) n = 255;
            memcpy(s->pcscf, payload, n);
            s->pcscf[n < 255 ? n : 254] = 0;
            s->pcscf[255] = 0;
            size_t l = strnlen(s->pcscf, 255);
            s->pcscf_valid = (l > 0);
        }
        break;
    case 28u: /* IMS domain: NUL-terminated string */
        if (payload_len >= 1 && payload_len <= 255) {
            size_t n = payload_len < 255 ? payload_len : 254;
            memcpy(s->domain, payload, n);
            s->domain[n] = 0;
            s->domain_valid = (strnlen(s->domain, 254) > 0);
        }
        break;
    case 27u: /* SMS-over-IP: 1-byte */
        if (payload_len >= 1) { s->smsoverip = payload[0]; s->smsoverip_valid = true; }
        break;
    case 26u: /* SMS format: 1-byte */
        if (payload_len >= 1) { s->smsfmt = payload[0]; s->smsfmt_valid = true; }
        break;
    default:
        break;
    }
    return true;
}
