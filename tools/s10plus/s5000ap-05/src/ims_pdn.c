/* SPDX-License-Identifier: GPL-2.0-only
 *
 * ims_pdn.c — native IMS APN PDN establishment (MODEM-MANAGED bearer).
 *
 * This module synchronizes the IMS profile. ImsPdnTriggered @0x28f0e0
 * only checks an existing DataCall; it does not prove autonomous activation.
 * A profile acknowledgment is not a bearer or P-CSCF readiness indication.
 * CID 1 is never modified by this module.
 */
#include "ims_pdn.h"
#include "fmt_rx.h"
#include <string.h>

#define IMS_PDN_ATTEMPT_LIMIT 5u
#define IMS_PDN_STEP_TIMEOUT_MS 12000u
#define IMS_PDN_RETRY_MS 8000u

/* Vendor IMS/ePDN DataProfile wire id (DataCallList::GetCall(2) in
 * ImsPdnTriggered @0x28f0e0). This is the modem-managed IMS bearer profile,
 * NOT the DEFAULT internet profile (id 1). */
#define IMS_PDN_PROFILE_ID 2u

bool ims_pdn_open(struct ims_pdn *p, ims_pdn_write_fn write, void *user)
{
    if (!p || !write) return false;
    memset(p, 0, sizeof *p);
    p->write = write;
    p->user = user;
    p->cid = IMS_PDN_CID;
    p->proto = FMT_TX_PROTO_IPV6;   /* VoLTE/IMS P-CSCF discovery over IPv6 (KPN 204-08) */
    p->auth = FMT_TX_AUTH_NONE;      /* 3GPP IMS APN: no PDP-layer auth; SIP/REGISTER AKA */
    p->profile_id = IMS_PDN_PROFILE_ID;
    p->phase = IMS_PDN_IDLE;
    p->active = false;
    return true;
}

void ims_pdn_close(struct ims_pdn *p) { if (p) memset(p, 0, sizeof *p); }

bool ims_pdn_active(const struct ims_pdn *p)
{
    return p && p->active && p->attached && p->ip_ready && p->pcscf_ready &&
           p->phase == IMS_PDN_ACTIVE;
}

const char *ims_pdn_phase_name(enum ims_pdn_phase ph)
{
    static const char *const n[] = {"idle","set-profile","verify","active","failed"};
    return (ph <= IMS_PDN_FAILED) ? n[ph] : "unknown";
}

enum ims_pdn_phase ims_pdn_tick(struct ims_pdn *p, uint64_t now_ms, bool online)
{
    if (!p) return IMS_PDN_IDLE;
    if (!online) {
        p->active = false;
        p->attached = p->ip_ready = p->pcscf_ready = false;
        if (p->phase != IMS_PDN_FAILED) p->phase = IMS_PDN_IDLE;
        return p->phase;
    }
    switch (p->phase) {
    case IMS_PDN_IDLE:
        p->attempt = 0;
        p->next_action_ms = 0;
        p->phase_deadline_ms = 0;
        p->phase = IMS_PDN_SET_PROFILE;
        break;
    case IMS_PDN_SET_PROFILE:
        /* Wait for an uncorrelated GEN response before retrying. */
        if (p->phase_deadline_ms && now_ms < p->phase_deadline_ms) break;
        if (now_ms >= p->next_action_ms && p->attempt < IMS_PDN_ATTEMPT_LIMIT) {
            p->attempt++;
            struct fmt_tx_frame f;
            uint8_t seq = 0;
            if (fmt_tx_set_data_profile_ex(&f, IMS_PDN_APN, p->auth, p->proto,
                                           p->profile_id, "ims") &&
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
    if (!p || p->phase != IMS_PDN_SET_PROFILE ||
        !p->phase_deadline_ms || ack_seq != p->last_write_seq) return;
    if (result == FMT_RX_GEN_OK) {
        if (p->phase == IMS_PDN_SET_PROFILE) {
            p->attempt = 0;
            p->next_action_ms = 0;
            p->phase_deadline_ms = 0;
            /* Profile accepted; await actual attachment/IP/P-CSCF. */
            p->active = false;
            p->phase = IMS_PDN_VERIFY;
        }
    } else {
        p->phase = IMS_PDN_FAILED;
        p->phase_deadline_ms = 0;
    }
}

static void update_ready(struct ims_pdn *p)
{
    p->active = p->attached && p->ip_ready && p->pcscf_ready;
    if (p->phase == IMS_PDN_VERIFY || p->phase == IMS_PDN_ACTIVE)
        p->phase = p->active ? IMS_PDN_ACTIVE : IMS_PDN_VERIFY;
}

void ims_pdn_report_cid(struct ims_pdn *p, uint8_t cid, bool attached)
{
    if (!p || cid != p->cid) return;
    p->attached = attached;
    if (!attached) p->ip_ready = p->pcscf_ready = false;
    update_ready(p);
}

void ims_pdn_report_ip(struct ims_pdn *p, const struct fmt_rx_ip *ip)
{
    if (!p || !ip || ip->cid != p->cid) return;
    p->ip_ready = ip->ipv4_valid || ip->ipv6_valid;
    p->pcscf_ready = (ip->ipv4_valid && ip->pcscf4_count) ||
                     (ip->ipv6_valid && ip->pcscf6_count);
    update_ready(p);
}
