/* SPDX-License-Identifier: GPL-2.0-only
 *
 * iil_auth.h — IIL IMS AKA relay. Bridges the modem's IIL IsimAuth challenge
 * (IpcRxIilIsimAuth) to the USIM (SEC 5/9 ABN) and returns the RES to the
 * modem via IpcTxImsAuthResp (main=112 sub=2). Session secret material
 * (RAND/AUTN/RES/CK/IK) is held in the struct only and never logged.
 */
#ifndef NUXEL_IIL_AUTH_H
#define NUXEL_IIL_AUTH_H
#include <stdint.h>
#include <stdbool.h>
#include "ims_iil.h"
#include "fmt_tx.h"
#include "fmt_rx.h"

typedef bool (*iil_auth_iil_write_fn)(const struct iil_frame *f, uint8_t *seq, void *user);
typedef bool (*iil_auth_usim_write_fn)(const struct fmt_tx_frame *f, uint8_t *seq, void *user);

struct iil_auth {
    iil_auth_iil_write_fn  iil_write;
    iil_auth_usim_write_fn usim_write;
    void *user;
    uint8_t last_iil_seq, last_usim_seq;
    uint8_t rand[16], autn[16];
    uint8_t res[16]; size_t res_len;
    uint8_t ck[16], ik[16];
    bool pending;              /* AKA in flight (challenge received, awaiting RES) */
    bool have_challenge;
    uint64_t deadline_ms;
    unsigned attempt;
};

bool iil_auth_open(struct iil_auth *a, iil_auth_iil_write_fn iil_write,
                   iil_auth_usim_write_fn usim_write, void *user);
void iil_auth_close(struct iil_auth *a);

/* Feed an IIL IsimAuth challenge (RAND+AUTN) and drive the USIM request. */
bool iil_auth_challenge(struct iil_auth *a, const uint8_t rand[16],
                        const uint8_t autn[16], uint64_t now_ms);

/* Feed the solicited USIM AKA result (RES/CK/IK or AUTS) and forward the
 * appropriate IpcTxImsAuthResp to the modem. Returns true if a frame was sent. */
bool iil_auth_usim_result(struct iil_auth *a, const struct fmt_rx_usim_auth *r,
                          uint64_t now_ms);

/* Timeout handling: drop a stale transaction. */
bool iil_auth_tick(struct iil_auth *a, uint64_t now_ms);
#endif /* NUXEL_IIL_AUTH_H */
