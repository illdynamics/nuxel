/* SPDX-License-Identifier: GPL-2.0-only
 *
 * iil_auth.c — IIL IMS AKA relay. See iil_auth.h.
 * Never logs RAND/AUTN/RES/CK/IK. The USIM request goes through SEC 5/9; the
 * RES is returned to the modem via IIL main=112 sub=2 (IpcTxImsAuthResp).
 */
#include "iil_auth.h"
#include "fmt_rx.h"
#include <string.h>

#define IIL_AUTH_TIMEOUT_MS 15000u
#define IIL_AUTH_ATTEMPT_LIMIT 3u

static void wipe(struct iil_auth *a)
{
    volatile unsigned char *v = (volatile unsigned char *)a;
    if (!a) return;
    /* clear secret fields only; keep callbacks/user for reuse */
    memset(a->rand, 0, sizeof a->rand);
    memset(a->autn, 0, sizeof a->autn);
    memset(a->res, 0, sizeof a->res);
    memset(a->ck, 0, sizeof a->ck);
    memset(a->ik, 0, sizeof a->ik);
    a->res_len = 0;
    a->have_challenge = false;
    a->pending = false;
    a->deadline_ms = 0;
    (void)v;
}

bool iil_auth_open(struct iil_auth *a, iil_auth_iil_write_fn iil_write,
                   iil_auth_usim_write_fn usim_write, void *user)
{
    if (!a || !iil_write || !usim_write) return false;
    memset(a, 0, sizeof *a);
    a->iil_write = iil_write;
    a->usim_write = usim_write;
    a->user = user;
    return true;
}

void iil_auth_close(struct iil_auth *a) { if (a) { wipe(a); memset(a,0,sizeof *a); } }

bool iil_auth_challenge(struct iil_auth *a, const uint8_t rand[16],
                        const uint8_t autn[16], uint64_t now_ms)
{
    if (!a || !rand || !autn) return false;
    if (a->pending) return false;        /* one outstanding transaction */
    memcpy(a->rand, rand, 16);
    memcpy(a->autn, autn, 16);
    a->have_challenge = true;
    struct fmt_tx_frame f;
    if (!fmt_tx_usim_auth(&f, rand, autn)) { wipe(a); return false; }
    uint8_t seq = 0;
    if (!a->usim_write(&f, &seq, a->user)) { wipe(a); return false; }
    a->last_usim_seq = seq;
    a->pending = true;
    a->deadline_ms = now_ms + IIL_AUTH_TIMEOUT_MS;
    return true;
}

bool iil_auth_usim_result(struct iil_auth *a, const struct fmt_rx_usim_auth *r,
                          uint64_t now_ms)
{
    (void)now_ms;
    if (!a || !a->pending || !r) return false;
    a->pending = false;
    a->deadline_ms = 0;

    struct iil_frame f;
    if (r->authenticated && r->res && r->res_len >= 4 && r->res_len <= 16) {
        /* Forward RES to the modem via IpcTxImsAuthResp. CK/IK are retained in
         * the struct only for the AP-side IPsec profile (not sent to modem). */
        memcpy(a->res, r->res, r->res_len);
        a->res_len = r->res_len;
        if (r->ck) memcpy(a->ck, r->ck, 16);
        if (r->ik) memcpy(a->ik, r->ik, 16);
        if (!iil_tx_ims_auth_resp(&f, a->res, a->res_len)) { wipe(a); return false; }
    } else if (r->auts && r->auts_len == 14) {
        /* Sync failure: forward the AUTS re-sync token instead of RES. */
        if (!iil_tx_ims_auth_resp(&f, r->auts, r->auts_len)) { wipe(a); return false; }
    } else {
        wipe(a);
        return false;   /* malformed / UICC failure; drop, do not fabricate */
    }

    uint8_t seq = 0;
    if (!a->iil_write(&f, &seq, a->user)) { wipe(a); return false; }
    a->last_iil_seq = seq;
    a->have_challenge = false;
    memset(a->rand, 0, sizeof a->rand);
    memset(a->autn, 0, sizeof a->autn);
    return true;
}

bool iil_auth_tick(struct iil_auth *a, uint64_t now_ms)
{
    if (!a) return false;
    if (a->pending && a->deadline_ms && now_ms >= a->deadline_ms) {
        wipe(a);
        return false;
    }
    return a->pending;
}
