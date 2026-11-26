/* SPDX-License-Identifier: GPL-2.0-only */
#include "iil_auth.h"
#include "fmt_rx.h"
#include <assert.h>
#include <stdio.h>
#include <string.h>

static const struct iil_frame *last_iil;
static const struct fmt_tx_frame *last_usim;

static bool iil_cb(const struct iil_frame *f, uint8_t *seq, void *u) {
    (void)u; last_iil = f; if (seq) *seq = 1; return true;
}
static bool usim_cb(const struct fmt_tx_frame *f, uint8_t *seq, void *u) {
    (void)u; last_usim = f; if (seq) *seq = 1; return true;
}

int main(void)
{
    struct iil_auth a;
    assert(iil_auth_open(&a, iil_cb, usim_cb, NULL));

    uint8_t rnd[16], autn[16];
    for (int i = 0; i < 16; i++) { rnd[i] = i; autn[i] = 0x10 + i; }

    /* challenge -> USIM request (SEC 5/9) */
    assert(iil_auth_challenge(&a, rnd, autn, 1000));
    assert(a.pending && last_usim && last_usim->main_cmd == 5 && last_usim->sub_cmd == 9);

    /* USIM authenticated result -> IIL ImsAuthResp (main=112 sub=2) */
    struct fmt_rx_usim_auth r = {0};
    uint8_t payload[] = {2, 0, 4, 0xAA,0xBB,0xCC,0xDD,
                         16, 0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,
                         16, 0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,
                         8,  0,0,0,0,0,0,0,0};
    assert(fmt_rx_usim_auth(payload, sizeof payload, &r));
    assert(r.authenticated && r.res_len == 4);
    assert(iil_auth_usim_result(&a, &r, 2000));
    assert(last_iil && last_iil->main_cmd == 112 && last_iil->sub_cmd == 2);
    assert(!a.pending);

    puts("IIL AKA relay: PASS");
    iil_auth_close(&a);
    return 0;
}
