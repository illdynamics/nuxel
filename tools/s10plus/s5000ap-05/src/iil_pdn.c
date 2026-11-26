/* SPDX-License-Identifier: GPL-2.0-only
 *
 * iil_pdn.c — IIL IMS APN PDN driver. See iil_pdn.h.
 *
 * Drives the IMS DataProfile sync (FMT main=13 sub=27 SET_DATA_PROFILE with
 * wire type 2, label "ims") followed by the emulation-verified IIL
 * DefinePdpContext -> SetPdpContext (ACTIVATE) sequence for the isolated
 * CID-2 IMS bearer, and only reports active once the modem confirms attach +
 * IP + P-CSCF via the IIL Connected and Parameters events. CID 1 (ordinary
 * internet) is never touched.
 */
#include "iil_pdn.h"
#include <string.h>

#define IIL_PDN_ATTEMPT_LIMIT 5u
#define IIL_PDN_STEP_TIMEOUT_MS 12000u
#define IIL_PDN_RETRY_MS 8000u

bool iil_pdn_open(struct iil_pdn *p, iil_pdn_write_fn write, void *user)
{
    if (!p || !write) return false;
    memset(p, 0, sizeof *p);
    p->write = write;
    p->user = user;
    p->cid = IIL_PDN_CID;
    p->phase = IIL_PDN_IDLE;
    return true;
}

void iil_pdn_set_fmt_write(struct iil_pdn *p, iil_pdn_fmt_write_fn fmt_write,
                           void *fmt_user)
{
    if (!p) return;
    p->fmt_write = fmt_write;
    p->fmt_user = fmt_user;
}

void iil_pdn_close(struct iil_pdn *p) { if (p) memset(p, 0, sizeof *p); }

bool iil_pdn_active(const struct iil_pdn *p)
{
    /* Readiness is the attached+IP+P-CSCF triple; phase tracks it for the
     * caller, but the readiness itself must not be gated on the phase so the
     * VERIFY->ACTIVE transition can complete in a single step. */
    return p && p->attached && p->ip_ready && p->pcscf_ready;
}

const char *iil_pdn_phase_name(enum iil_pdn_phase ph)
{
    static const char *const n[] = {"idle","set-profile","provision","define","activate","verify","active","failed"};
    return (ph <= IIL_PDN_FAILED) ? n[ph] : "unknown";
}

enum iil_pdn_phase iil_pdn_tick(struct iil_pdn *p, uint64_t now_ms, bool online)
{
    if (!p) return IIL_PDN_IDLE;
    if (!online) {
        p->attached = p->ip_ready = p->pcscf_ready = false;
        p->pcscf_count = 0;
        p->phase = IIL_PDN_IDLE;
        p->phase_deadline_ms = 0;
        return p->phase;
    }
    switch (p->phase) {
    case IIL_PDN_IDLE:
        p->attempt = 0;
        p->phase_deadline_ms = 0;
        p->phase = IIL_PDN_SET_PROFILE;
        break;
    case IIL_PDN_SET_PROFILE:
    case IIL_PDN_PROVISION:
    case IIL_PDN_DEFINE:
    case IIL_PDN_ACTIVATE: {
        if (p->phase_deadline_ms) {
            if (now_ms >= p->phase_deadline_ms) {
                p->phase_deadline_ms = 0;
                if (++p->attempt >= IIL_PDN_ATTEMPT_LIMIT) p->phase = IIL_PDN_FAILED;
                else p->phase = IIL_PDN_SET_PROFILE;  /* re-arm from SET_PROFILE */
            }
            break;
        }
        uint8_t seq = 0;
        bool sent = false;
        uint8_t write_kind = 0;   /* 0=IIL write, 1=FMT write */

        if (p->phase == IIL_PDN_SET_PROFILE) {
            /* Sync the modem's IMS DataProfile (wire type 2, label "ims",
             * APN ims.mnc008.mcc204.gprs) via the FMT GPRS SET_DATA_PROFILE
             * path (main=13 sub=27). This is the missing provisioning step:
             * it seeds the modem's IMS APN profile before the IIL Define/
             * Activate. When no FMT writer is configured (offline), skip. */
            if (p->fmt_write) {
                struct fmt_tx_frame f;
                if (fmt_tx_ims_profile(&f, IIL_PDN_APN, FMT_TX_PROTO_IPV6)) {
                    sent = p->fmt_write(&f, &seq, p->fmt_user);
                    write_kind = 1;
                }
            } else {
                /* No FMT writer: proceed to IIL PROVISION (host-test path). */
                p->phase = IIL_PDN_PROVISION;
                p->attempt = 0;
                break;
            }
        } else {
            struct iil_frame f;
            bool built;
            const char *empty[8] = {0,0,0,0,0,0,0,0};
            if (p->phase == IIL_PDN_PROVISION) {
                built = iil_tx_ims_set_pdn_info(&f, IIL_PDN_E911_PROV_APN, empty, NULL);
            } else if (p->phase == IIL_PDN_DEFINE) {
                built = iil_tx_define_pdp(&f, IIL_PDN_APN, 3 /*IPV6*/, 1 /*EUTRAN AccessNetworkType*/);
            } else {
                built = iil_tx_set_pdp_context(&f, p->cid, IIL_PDN_APN);
            }
            if (built && p->write(&f, &seq, p->user)) {
                sent = true;
                write_kind = 0;
            }
        }

        if (sent) {
            p->last_write_seq = seq;
            p->last_write_kind = write_kind;
            p->phase_deadline_ms = now_ms + IIL_PDN_STEP_TIMEOUT_MS;
        } else if (p->phase == IIL_PDN_SET_PROFILE) {
            /* Failed to build/send the IMS DataProfile sync: fail (do not
             * silently skip to IIL, which would never bring CID-2 up). */
            p->phase = IIL_PDN_FAILED;
        } else {
            p->phase = IIL_PDN_FAILED;
        }
        break;
    }
    case IIL_PDN_VERIFY:
    case IIL_PDN_ACTIVE:
    case IIL_PDN_FAILED:
        break;
    }
    return p->phase;
}

void iil_pdn_gen_result(struct iil_pdn *p, uint16_t result, uint8_t ack_seq)
{
    if (!p || ack_seq != p->last_write_seq || !p->phase_deadline_ms) return;
    p->last_result = result;
    p->phase_deadline_ms = 0;

    if (p->phase == IIL_PDN_SET_PROFILE) {
        /* IMS DataProfile sync result. GEN_OK (0x8000) advances to the IIL
         * PROVISION/E911 step; a rejection is treated as non-fatal here so the
         * direct IIL Define/Activate path is still attempted (the E911
         * provisioner is independently best-effort). */
        p->phase = IIL_PDN_PROVISION; p->attempt = 0;
    } else if (p->phase == IIL_PDN_PROVISION) {
        /* The IpcTxImsReqSetImsPdnInfoE911 provisioner is best-effort: this CP
         * rejects it (0x8003) but the IIL Define/Activate for CID-2 is
         * independently acknowledgeable. Treat any provisioner result as
         * "skip provisioner" and proceed to DEFINE. */
        p->phase = IIL_PDN_DEFINE; p->attempt = 0;
    } else if (p->phase == IIL_PDN_DEFINE) {
        if (result == 0x8000u) { p->phase = IIL_PDN_ACTIVATE; p->attempt = 0; }
        else { p->phase = IIL_PDN_FAILED; }
    } else if (p->phase == IIL_PDN_ACTIVATE) {
        if (result == 0x8000u) { p->phase = IIL_PDN_VERIFY; p->attempt = 0; }
        else { p->phase = IIL_PDN_FAILED; }
    }
}

void iil_pdn_on_connected(struct iil_pdn *p, const struct iil_rx_event *e)
{
    uint8_t cid = 0; bool attached = false;
    if (!p || !iil_rx_connected(e, &cid, &attached)) return;
    if (cid != p->cid) return;
    p->attached = attached;
    if (!attached) { p->ip_ready = p->pcscf_ready = false; p->pcscf_count = 0; }
    if (p->phase == IIL_PDN_VERIFY || p->phase == IIL_PDN_ACTIVE)
        p->phase = iil_pdn_active(p) ? IIL_PDN_ACTIVE : IIL_PDN_VERIFY;
}

void iil_pdn_on_parameters(struct iil_pdn *p, const struct iil_rx_event *e)
{
    if (!p) return;
    int family = 0; uint8_t ip[16]; uint8_t prefix = 0;
    unsigned n = 0;
    if (!iil_rx_parameters(e, &family, ip, &prefix,
                           p->pcscf, p->pcscf_len, 4, &n)) return;
    p->family = family;
    memcpy(p->ip, ip, 16);
    p->prefix = prefix;
    p->pcscf_count = n;
    p->ip_ready = true;
    p->pcscf_ready = (n > 0);
    if (p->phase == IIL_PDN_VERIFY || p->phase == IIL_PDN_ACTIVE)
        p->phase = iil_pdn_active(p) ? IIL_PDN_ACTIVE : IIL_PDN_VERIFY;
}
