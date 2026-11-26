/* SPDX-License-Identifier: GPL-2.0-only
 *
 * ims_pdn.c — native IMS APN PDN establishment (MODEM-MANAGED bearer).
 *
 * This module synchronizes the IMS profile and drives the modem-managed IMS
 * DataCall. ImsPdnTriggered @0x28f0e0 only checks an existing DataCall; it
 * does not prove autonomous activation. A profile acknowledgment is not a
 * bearer or P-CSCF readiness indication. CID 1 is never modified.
 *
 * The prior implementation sent SetDataProfile(ims) and then stopped in
 * VERIFY, waiting for a CID-2 attach that never arrived. The CP rejected a
 * separate DefinePdpContext(profile_id=2) with 0x8001 because payload[1] of
 * DEFINE is AccessNetworkType (EUTRAN=1), NOT a DataProfile id. This module
 * now advances SetDataProfile -> DEFINE(EUTRAN) -> ACTIVATE(CID 2) and only
 * then VERIFYs a real GPRS_IP_CONFIGURATION(cid=2) with a usable P-CSCF.
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

/* AccessNetworkType EUTRAN selector for DefinePdpContext payload[1].
 * Stock IpcTxDefinePdpContext uses the same value for internet and IMS. */
#define IMS_PDN_EUTRAN 1u

bool ims_pdn_open(struct ims_pdn *p, ims_pdn_write_fn write, void *user)
{
    if (!p || !write) return false;
    memset(p, 0, sizeof *p);
    p->write = write;
    p->user = user;
    p->cid = IMS_PDN_CID;
    /* Round 07 fb9da745 live-verified config (the only configuration with
     * physical GPRS_PDP_CONTEXT cid=2 state=1): profile is IPv4v6, DEFINE is
     * lowered to IPv4 wire 0x05 (the CP validator rejects the dual-stack wire
     * 0x04), PDP auth is CHAP (empty creds), APN is the FQDN. The later
     * AUTH_NONE+IPv6 change (da472387) regressed CID-2 to state=3. */
    p->proto = FMT_TX_PROTO_IPV4V6;
    p->auth = FMT_TX_AUTH_CHAP;
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
    static const char *const n[] = {"idle","set-profile","verify","active","failed","define","activate","release"};
    return (ph <= IMS_PDN_RELEASE) ? n[ph] : "unknown";
}

enum ims_pdn_phase ims_pdn_tick(struct ims_pdn *p, uint64_t now_ms, bool online)
{
    if (!p) return IMS_PDN_IDLE;
    if (!online) {
        p->active = false;
        p->attached = p->ip_ready = p->pcscf_ready = false;
        p->phase = IMS_PDN_IDLE;
        p->phase_deadline_ms=0;
        memset(&p->ip,0,sizeof p->ip);
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
    case IMS_PDN_DEFINE:
    case IMS_PDN_ACTIVATE:
    case IMS_PDN_RELEASE: {
        /* An accepted write is never repeated on timeout: activation may
         * already have reached the network. Recovery requires a new epoch. */
        if (p->phase_deadline_ms) {
            if (now_ms>=p->phase_deadline_ms) p->phase=IMS_PDN_FAILED;
            break;
        }
        struct fmt_tx_frame f;
        bool built = false;
        if (p->phase == IMS_PDN_SET_PROFILE) {
            built = fmt_tx_ims_profile(&f, IMS_PDN_APN, p->proto);
        } else if (p->phase == IMS_PDN_DEFINE) {
            /* Round 07 fb9da745: DEFINE lowers IPv4v6 profile to IPv4 wire
             * 0x05 (the CP validator rejects the dual-stack 0x04 with 0x8001).
             * payload[1] selector is 2 (the IMS DataProfile/CID slot). */
            uint8_t define_proto = (p->proto == FMT_TX_PROTO_IPV4V6) ?
                                   FMT_TX_PROTO_IP : p->proto;
            built = fmt_tx_ims_define(&f, IMS_PDN_APN, define_proto);
        } else if (p->phase == IMS_PDN_ACTIVATE) {
            /* main=13 sub=4 ACTIVATE for CID 2, no PDP-layer auth. */
            built = fmt_tx_set_pdp_context(&f, IMS_PDN_APN, p->auth,
                                           p->proto, p->cid,
                                           FMT_TX_PDP_TYPE_FULL);
        } else {
            built = fmt_tx_release_pdp_context(&f, p->cid);
        }
        if (built && p->write(&f, &p->last_write_seq, p->user)) {
            p->pending_sub = f.sub_cmd;
            p->phase_deadline_ms = now_ms + IMS_PDN_STEP_TIMEOUT_MS;
        } else {
            p->phase = IMS_PDN_FAILED;
        }
        break;
    }
    case IMS_PDN_VERIFY:
        /* ACTIVATE was acknowledged (GEN 0x8000) but the modem must independently
         * confirm a CID-2 attach + IP + P-CSCF. If that confirmation never
         * arrives (the CID-2 deactivation/state=3 regression), re-arm the whole
         * SET_PROFILE->DEFINE->ACTIVATE sequence instead of sitting inert.
         * Bounded by the attempt limit so an unprovisioned bearer cannot
         * retry-storm the CP. */
        if (p->phase_deadline_ms == 0) {
            p->phase_deadline_ms = now_ms + IMS_PDN_RETRY_MS;
        } else if (now_ms >= p->phase_deadline_ms) {
            p->phase_deadline_ms = 0;
            if (++p->attempt >= IMS_PDN_ATTEMPT_LIMIT) p->phase = IMS_PDN_FAILED;
            else p->phase = IMS_PDN_SET_PROFILE;
        }
        break;
    case IMS_PDN_ACTIVE:
    case IMS_PDN_FAILED:
        break;
    }
    return p->phase;
}

void ims_pdn_gen_result(struct ims_pdn *p, uint16_t result, uint8_t ack_seq)
{
    if (!p || !p->phase_deadline_ms || ack_seq != p->last_write_seq ||
        (p->phase != IMS_PDN_SET_PROFILE && p->phase != IMS_PDN_DEFINE &&
         p->phase != IMS_PDN_ACTIVATE && p->phase != IMS_PDN_RELEASE)) return;
    p->last_result = result;
    p->phase_deadline_ms = 0;
    if (result != FMT_RX_GEN_OK) { p->phase = IMS_PDN_FAILED; return; }

    switch (p->phase) {
    case IMS_PDN_SET_PROFILE:
        /* SetDataProfile(ims) accepted -> DEFINE (EUTRAN), NOT straight to
         * VERIFY. The modem does not auto-create the ims bearer on this CP;
         * the ims APN string must be defined then activated. */
        p->phase = IMS_PDN_DEFINE;
        break;
    case IMS_PDN_DEFINE:
        /* DEFINE accepted -> ACTIVATE CID 2. */
        p->phase = IMS_PDN_ACTIVATE;
        break;
    case IMS_PDN_ACTIVATE:
        /* ACTIVATE accepted -> VERIFY a real CID-2 attach+IP+P-CSCF. */
        p->phase = IMS_PDN_VERIFY;
        if (p->active) p->phase = IMS_PDN_ACTIVE;
        break;
    case IMS_PDN_RELEASE:
        p->phase = IMS_PDN_IDLE;
        break;
    default:
        break;
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
    if (!attached) { p->ip_ready = p->pcscf_ready = false; memset(&p->ip,0,sizeof p->ip); }
    update_ready(p);
}

void ims_pdn_report_ip(struct ims_pdn *p, const struct fmt_rx_ip *ip)
{
    if (!p || !ip || ip->cid != p->cid) return;
    p->ip=*ip;
    p->ip_ready = ip->ipv4_valid || ip->ipv6_valid;
    p->pcscf_ready = (ip->ipv4_valid && ip->pcscf4_count) ||
                     (ip->ipv6_valid && ip->pcscf6_count);
    update_ready(p);
}
