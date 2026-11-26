/* SPDX-License-Identifier: GPL-2.0-only */
#ifndef NUXEL_IMS_SMS_H
#define NUXEL_IMS_SMS_H
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>
/* TS 24.011 RP PDUs carried as binary application/vnd.3gpp.sms (24.341).
 * Address inputs use the SMSC length+TOA+BCD representation already stored
 * by the native service. No SIP response is an RP submission result. */
struct ims_rp {
    uint8_t type, reference, cause;
    const uint8_t *origin, *destination, *tpdu;
    size_t origin_len, destination_len, tpdu_len;
};
bool ims_rp_decode(const uint8_t *p,size_t n,struct ims_rp *out);
size_t ims_rp_submit(uint8_t *out,size_t cap,uint8_t ref,const uint8_t *smsc,
                     size_t smsc_len,const uint8_t *tpdu,size_t tpdu_len);
size_t ims_rp_reply(uint8_t out[5],uint8_t ref,uint8_t cause);
#endif
