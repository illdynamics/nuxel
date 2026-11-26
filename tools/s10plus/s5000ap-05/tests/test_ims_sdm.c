/* SPDX-License-Identifier: GPL-2.0-only
 * ims_sdm readback unit tests. No modem access; captures are synthetic.
 */
#include "ims_sdm.h"
#include <stdio.h>
#include <string.h>

static int failures;
#define CHECK(c) do { if (!(c)) { fprintf(stderr,"FAIL %s:%d: %s\n",__FILE__,__LINE__,#c); failures++; } } while(0)

static const struct fmt_tx_frame *last_frame;
static uint8_t last_seq;

static bool capture_write(const struct fmt_tx_frame *f, uint8_t *seq, void *user)
{
    (void)user;
    last_frame = f;
    *seq = 42;
    last_seq = 42;
    return true;
}

int main(void)
{
    struct ims_sdm s;
    CHECK(ims_sdm_open(&s, capture_write, NULL));

    /* First tick advances IDLE -> GET_MODE; second tick fires the query. */
    enum ims_sdm_phase ph = ims_sdm_tick(&s, 1000, true);
    CHECK(ph == IMS_SDM_GET_MODE);
    ph = ims_sdm_tick(&s, 1000, true);
    CHECK(ph == IMS_SDM_GET_MODE);
    CHECK(last_frame != NULL);
    if (!last_frame) { printf("no frame\n"); return 2; }
    CHECK(last_frame->main_cmd == 10 && last_frame->sub_cmd == 32 && last_frame->cmd_type == 2);
    CHECK(last_frame->len == 7);

    /* feed the response: 1-byte mode=1; advance to GET_PCSCF */
    uint8_t mode = 1;
    CHECK(ims_sdm_receive(&s, 32, 42, &mode, 1));
    CHECK(s.phase == IMS_SDM_GET_PCSCF);
    CHECK(s.mode_valid && s.mode == 1);

    /* tick fires GET_PCSCF (sub=34) */
    ph = ims_sdm_tick(&s, 6000, true);
    CHECK(ph == IMS_SDM_GET_PCSCF);
    CHECK(last_frame->sub_cmd == 34 && last_frame->cmd_type == 2);

    /* feed P-CSCF response */
    const char *pcscf = "pcscf.example.net";
    CHECK(ims_sdm_receive(&s, 34, 42, (const uint8_t*)pcscf, strlen(pcscf)+1));
    CHECK(s.phase == IMS_SDM_GET_DOMAIN);
    CHECK(s.pcscf_valid && !strcmp(s.pcscf, pcscf));

    /* domain */
    ims_sdm_tick(&s, 20000, true);
    CHECK(last_frame->sub_cmd == 28);
    const char *dom = "ims.mnc008.mcc204.gprs";
    CHECK(ims_sdm_receive(&s, 28, 42, (const uint8_t*)dom, strlen(dom)+1));
    CHECK(s.phase == IMS_SDM_GET_SMSOVERIP);
    CHECK(s.domain_valid && !strcmp(s.domain, dom));

    /* smsoverip */
    ims_sdm_tick(&s, 30000, true);
    CHECK(last_frame->sub_cmd == 27);
    uint8_t oip = 1;
    CHECK(ims_sdm_receive(&s, 27, 42, &oip, 1));
    CHECK(s.phase == IMS_SDM_GET_SMSFMT);
    CHECK(s.smsoverip_valid && s.smsoverip == 1);

    /* smsfmt */
    ims_sdm_tick(&s, 40000, true);
    CHECK(last_frame->sub_cmd == 26);
    uint8_t fmt = 2;
    CHECK(ims_sdm_receive(&s, 26, 42, &fmt, 1));
    CHECK(s.phase == IMS_SDM_DONE);
    CHECK(s.smsfmt_valid && s.smsfmt == 2);

    /* wrong ack/sub must not advance */
    CHECK(!ims_sdm_receive(&s, 34, 7, (const uint8_t*)pcscf, strlen(pcscf)+1));

    ims_sdm_close(&s);
    CHECK(s.phase == IMS_SDM_IDLE);
    printf("ims_sdm readback: PASS (%d failures)\n", failures);
    return failures ? 1 : 0;
}
