/* SPDX-License-Identifier: GPL-2.0-only */
#ifndef NUXEL_FMT_SMS_H
#define NUXEL_FMT_SMS_H
#include "fmt_tx.h"

/* AP serializers 0x344df8, 0x344f48, 0x345340, 0x3455d8. */
bool fmt_sms_send(struct fmt_tx_frame *f, bool more, uint8_t domain_wire,
                  const uint8_t *sca_tpdu, size_t len);
bool fmt_sms_ack(struct fmt_tx_frame *f, uint8_t reference, uint16_t result);
bool fmt_sms_ready(struct fmt_tx_frame *f);
bool fmt_sms_get_smsc(struct fmt_tx_frame *f);

/* Incoming GSM: type, category, reserved[2], reference, PDU length, SCA+TPDU.
 * The reference is for acknowledgement, not the outgoing TP-Message-Reference. */
struct fmt_sms_incoming {
    uint8_t reference, category;
    const uint8_t *pdu;
    size_t len;
};
bool fmt_sms_incoming(const uint8_t *p, size_t n, struct fmt_sms_incoming *out);
struct fmt_sms_submit_result {
    uint16_t result; /* zero = submitted to network, NEVER means delivered */
    uint8_t reference;
    const uint8_t *pdu;
    size_t len;
};
bool fmt_sms_submit_result(const uint8_t *p, size_t n, struct fmt_sms_submit_result *out);
/* SMSC is its length byte followed by TON/NPI and BCD, max 20 digits. */
bool fmt_sms_smsc(const uint8_t *p, size_t n, uint8_t out[12], size_t *len);
#endif
