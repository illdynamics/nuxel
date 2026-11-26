/* SPDX-License-Identifier: GPL-2.0-only
 *
 * iil_pdn.c — IIL IMS APN PDN driver. See iil_pdn.h.
 *
 * Drives the emulation-verified IIL DefinePdpContext -> SetPdpContext
 * (ACTIVATE) sequence for the isolated CID-2 IMS bearer, and only reports
 * active once the modem confirms attach + IP + P-CSCF via the IIL Connected
 * and Parameters events. CID 1 (ordinary internet) is never touched.
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
    static const char *const n[] = {"idle","provision","define","activate","verify","active","failed"};
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
        p->phase = IIL_PDN_PROVISION;
        break;
    case IIL_PDN_PROVISION:
    case IIL_PDN_DEFINE:
    case IIL_PDN_ACTIVATE: {
        if (p->phase_deadline_ms) {
            if (now_ms >= p->phase_deadline_ms) {
                p->phase_deadline_ms = 0;
                if (++p->attempt >= IIL_PDN_ATTEMPT_LIMIT) p->phase = IIL_PDN_FAILED;
                else p->phase = IIL_PDN_PROVISION;  /* re-arm from PROVISION */
            }
            break;
        }
        struct iil_frame f;
        bool built;
        const char *empty[8] = {0,0,0,0,0,0,0,0};
        if (p->phase == IIL_PDN_PROVISION) {
            /* Fire IpcTxImsReqSetImsPdnInfoE911 first: provision the modem's
             * INTERNAL IMS stack. Empty config strings -> keep the modem's
             * NVRAM defaults; we never fabricate P-CSCF/security/identity. */
            built = iil_tx_ims_set_pdn_info(&f, IIL_PDN_E911_PROV_APN, empty, NULL);
        } else if (p->phase == IIL_PDN_DEFINE) {
            built = iil_tx_define_pdp(&f, IIL_PDN_APN, 3 /*IPV6*/, 1 /*EUTRAN AccessNetworkType*/);
        } else {
            built = iil_tx_set_pdp_context(&f, p->cid, IIL_PDN_APN);
        }
        uint8_t seq = 0;
        if (built && p->write(&f, &seq, p->user)) {
            p->last_write_seq = seq;
            p->phase_deadline_ms = now_ms + IIL_PDN_STEP_TIMEOUT_MS;
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
    /* GEN_OK (0x8000 in this CP's encoding) advances the phase; rejection
     * fails the phase. PROVISION/DEFINE/ACTIVATE writes all await a GEN ack. */
    if (p->phase == IIL_PDN_PROVISION) {
        /* The IpcTxImsReqSetImsPdnInfoE911 provisioner is best-effort: it
         * seeds the modem's INTERNAL IMS stack. On this CP the E911 path is
         * rejected (0x8003 UNSUPPORTED) or denied (0x8001), but the direct
         * IIL GPRS Define/Activate for CID-2 is independently acknowledgeable
         * (0x8000). Treat any provisioner result as "skip provisioner" and
         * proceed to DEFINE/ACTIVATE so a rejected provisioning step does not
         * block the only other live path. */
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
