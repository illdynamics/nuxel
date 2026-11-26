/* SPDX-License-Identifier: GPL-2.0-only
 *
 * ims_pdn.c — native IMS APN PDN establishment (MODEM-MANAGED bearer).
 *
 * Stock Samsung does NOT drive a raw second GPRS CID for IMS. The AP merely
 * syncs the IMS DataProfile (type 2, label "ims", APN "ims..."), then the
 * modem autonomously activates the IMS/ePDN bearer and performs P-CSCF
 * discovery. This module performs ONLY that supported profile sync; it is
 * fully isolated from the internet bearer (never detaches/releases CID 1).
 *
 * Evidence: LteEpdgDataCallManager::ImsPdnTriggered @0x28f0e0 calls
 * DataCallList::GetCall(2) (IMS/ePDN DataProfile) and waits for the
 * modem-managed data call; the AP does not send DEFINE/SET_PDP_CONTEXT for a
 * second CID. Auth is AUTH_NONE at the PDP layer because IMS bearer auth is
 * SIP/REGISTER via SIM AKA, not at PDP attach.
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
{ return p && p->active && p->phase == IMS_PDN_ACTIVE; }

const char *ims_pdn_phase_name(enum ims_pdn_phase ph)
{
    static const char *const n[] = {"idle","set-profile","sync-profile","verify","active","failed"};
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
    case IMS_PDN_SYNC_PROFILE:
        if (p->phase_deadline_ms && now_ms < p->phase_deadline_ms) break;
        if (now_ms >= p->next_action_ms && p->attempt < IMS_PDN_ATTEMPT_LIMIT) {
            p->attempt++;
            struct fmt_tx_frame f;
            uint8_t seq = 0;
            if (fmt_tx_sync_profile_info(&f, IMS_PDN_APN, p->auth, p->proto) &&
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
        if (p->phase == IMS_PDN_SET_PROFILE) {
            p->attempt = 0;
            p->next_action_ms = 0;
            p->phase_deadline_ms = 0;
            p->phase = IMS_PDN_SYNC_PROFILE;
        } else if (p->phase == IMS_PDN_SYNC_PROFILE) {
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
    /* A modem-managed IMS/ePDN bearer becomes visible as the modem reports the
     * distinct IMS CID attached (GPRS_CALL_STATUS or GPRS_PDP_CONTEXT). Only a
     * real modem notification moves VERIFY -> ACTIVE; never a local guess. */
    if (attached && p->phase == IMS_PDN_VERIFY) {
        p->active = true;
        p->phase = IMS_PDN_ACTIVE;
    } else if (!attached) {
        p->active = false;
    }
}
