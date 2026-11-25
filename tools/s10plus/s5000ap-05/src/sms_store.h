/* SPDX-License-Identifier: GPL-2.0-only */
#ifndef NUXEL_SMS_STORE_H
#define NUXEL_SMS_STORE_H
#include "sms_pdu.h"
#include <sqlite3.h>
struct sms_store { sqlite3 *db; };
struct sms_job {
    uint32_t id;
    unsigned part,total;
    struct sms_segment pdu;
};
struct sms_record {
    uint32_t id;
    char direction[8],state[24],peer[SMS_MAX_PEER],text[SMS_MAX_TEXT],timestamp[32];
    unsigned parts;
    int error;
};
bool sms_store_open(struct sms_store *s,const char *path);
void sms_store_close(struct sms_store *s);
bool sms_store_queue(struct sms_store *s,const char *to,const char *text,uint32_t *id);
bool sms_store_next(struct sms_store *s,struct sms_job *job); /* false when empty */
bool sms_store_sending(struct sms_store *s,uint32_t id,unsigned part);
bool sms_store_submit(struct sms_store *s,uint32_t id,unsigned part,uint8_t mr,uint16_t result);
bool sms_store_fail(struct sms_store *s,uint32_t id,unsigned part,int error,bool uncertain);
/* Durable commit before the caller acknowledges to CP. Duplicate deliveries
 * are acknowledged but do not create a second message. */
bool sms_store_receive(struct sms_store *s,const uint8_t *pdu,size_t len,
                       const struct sms_decoded *v,uint32_t *id,bool *changed);
bool sms_store_get(struct sms_store *s,uint32_t id,struct sms_record *out);
size_t sms_store_list(struct sms_store *s,uint32_t *ids,size_t cap);
/* Truthful aggregate: true only when at least one outbound message has reached
 * the delivered state through a matching TP-ST=0 status report. It is derived
 * from per-message evidence, never latched after a single success. */
bool sms_store_any_delivered(struct sms_store *s);
#endif
/* Safe user-facing reconciliation for an unresolved (unknown) outbound
 * submission. outcome must be "failed" (definitively not delivered) or
 * "delivered" (owner confirmed receipt). This only changes the specific
 * message's parts; it never queues a resend and never posts a delivery report. */
bool sms_store_resolve(struct sms_store *s,uint32_t id,const char *outcome);
