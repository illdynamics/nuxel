/* SPDX-License-Identifier: GPL-2.0-only
 *
 * ims_pdn.c — native IMS APN PDN establishment (second data context).
 *
 * Uses the SAME verified SIPC5 builders as the internet data session
 * (fmt_tx_define_pdp_context / fmt_tx_set_pdp_context), but for APN "ims"
 * with a DISTINCT CID. It is fully isolated from the internet bearer:
 * it never detaches, releases, or modifies CID 1.
 *
 * Auth is AUTH_NONE at the PDP layer by design: IMS bearer authentication is
 * performed at SIP REGISTER via SIM AKA (SEC_IMS_AUTH), not at PDP attach.
 * This mirrors 3GPP VoLTE and the documented KPN 204-08 "ims" APN.
 */
#include "ims_pdn.h"
#include "fmt_rx.h"
#include <string.h>

#define IMS_PDN_ATTEMPT_LIMIT 5u
#define IMS_PDN_STEP_TIMEOUT_MS 12000u
#define IMS_PDN_RETRY_MS 8000u

bool ims_pdn_open(struct ims_pdn *p, ims_pdn_write_fn write, void *user)
{
    if (!p || !write) return false;
    memset(p, 0, sizeof *p);
    p->write = write;
    p->user = user;
    p->cid = IMS_PDN_CID;
    p->proto = FMT_TX_PROTO_IPV4V6; /* IMS P-CSCF discovery over IPv4v6 */
    p->auth = FMT_TX_AUTH_NONE;      /* PDP-layer auth NONE (SIP does AKA) */
    p->phase = IMS_PDN_IDLE;
    p->active = false;
    return true;
}

void ims_pdn_close(struct ims_pdn *p) { if (p) memset(p, 0, sizeof *p); }

bool ims_pdn_active(const struct ims_pdn *p)
{ return p && p->active && p->phase == IMS_PDN_ACTIVE; }

const char *ims_pdn_phase_name(enum ims_pdn_phase ph)
{
    static const char *const n[] = {"idle","define","activate","verify","active","failed"};
    return (ph <= IMS_PDN_FAILED) ? n[ph] : "unknown";
}

enum ims_pdn_phase ims_pdn_tick(struct ims_pdn *p, uint64_t now_ms, bool online)
{
    if (!p) return IMS_PDN_IDLE;
    if (!online) {
        p->active = false;
        if (p->phase != IMS_PDN_FAILED) p->phase = IMS_PDN_IDLE;
        return p->phase;
    }
    switch (p->phase) {
    case IMS_PDN_IDLE:
        p->attempt = 0;
        p->next_action_ms = 0;
        p->phase = IMS_PDN_DEFINE;
        break;
    case IMS_PDN_DEFINE:
        /* Wait for an uncorrelated GEN response before retrying; otherwise the
         * same frame is re-emitted every tick and exhausts the attempt budget
         * without observing the modem rejection. */
        if (p->phase_deadline_ms && now_ms < p->phase_deadline_ms) break;
        if (now_ms >= p->next_action_ms && p->attempt < IMS_PDN_ATTEMPT_LIMIT) {
            p->attempt++;
            struct fmt_tx_frame f;
            uint8_t seq = 0;
            /* The CP DEFINE validator accepts only PDP wire types 2,5,6
             * (0x05=IPv4, 0x06=IPv6); the IPv4v6 wire byte 0x04 is rejected
             * with GEN 0x8001 (invalid parameter). Mirror the proven internet
             * path: DEFINE an IPv4 context when the profile is dual-stack. */
            uint8_t define_proto = (p->proto == FMT_TX_PROTO_IPV4V6) ?
                                   FMT_TX_PROTO_IP : p->proto;
            if (fmt_tx_define_pdp_context(&f, IMS_PDN_APN, define_proto, IMS_PDN_CID) &&
                p->write(&f, &seq, p->user)) {
                p->last_write_seq = seq;
                p->phase_deadline_ms = now_ms + IMS_PDN_STEP_TIMEOUT_MS;
            } else p->next_action_ms = now_ms + IMS_PDN_RETRY_MS;
        } else if (p->attempt >= IMS_PDN_ATTEMPT_LIMIT) {
            p->phase = IMS_PDN_FAILED;
        }
        break;
    case IMS_PDN_ACTIVATE:
        if (p->phase_deadline_ms && now_ms < p->phase_deadline_ms) break;
        if (now_ms >= p->next_action_ms && p->attempt < IMS_PDN_ATTEMPT_LIMIT) {
            p->attempt++;
            struct fmt_tx_frame f;
            uint8_t seq = 0;
            if (fmt_tx_set_pdp_context(&f, IMS_PDN_APN, p->auth, p->proto, IMS_PDN_CID,
                                        FMT_TX_PDP_TYPE_FULL) &&
                p->write(&f, &seq, p->user)) {
                p->last_write_seq = seq;
                p->phase_deadline_ms = now_ms + IMS_PDN_STEP_TIMEOUT_MS;
            } else p->next_action_ms = now_ms + IMS_PDN_RETRY_MS;
        } else if (p->attempt >= IMS_PDN_ATTEMPT_LIMIT) {
            p->phase = IMS_PDN_FAILED;
        }
        break;
    case IMS_PDN_VERIFY:
    case IMS_PDN_ACTIVE:
    case IMS_PDN_FAILED:
        break;
    }
    return p->phase;
}

void ims_pdn_gen_result(struct ims_pdn *p, uint16_t result, uint8_t ack_seq)
{
    if (!p) return;
    (void)ack_seq;
    if (result == FMT_RX_GEN_OK) {
        if (p->phase == IMS_PDN_DEFINE) {
            p->attempt = 0;
            p->next_action_ms = 0;
            p->phase_deadline_ms = 0;
            p->phase = IMS_PDN_ACTIVATE;
        } else if (p->phase == IMS_PDN_ACTIVATE) {
            p->attempt = 0;
            p->phase_deadline_ms = 0;
            p->phase = IMS_PDN_VERIFY;
        }
    } else {
        p->phase = IMS_PDN_FAILED;
        p->phase_deadline_ms = 0;
    }
}

void ims_pdn_report_cid(struct ims_pdn *p, uint8_t cid, bool attached)
{
    if (!p || cid != p->cid) return;
    if (attached && p->phase == IMS_PDN_VERIFY) {
        p->active = true;
        p->phase = IMS_PDN_ACTIVE;
    } else if (!attached) {
        p->active = false;
    }
}
