/* SPDX-License-Identifier: GPL-2.0-only */
#ifndef NUXEL_SMS_SERVICE_H
#define NUXEL_SMS_SERVICE_H
#include "fmt_sms.h"
#include "sms_store.h"
#include "sipc5_fmt.h"
typedef bool (*sms_write_fn)(const struct fmt_tx_frame *,uint8_t *sequence,void *);
typedef void (*sms_notify_fn)(uint32_t id,bool incoming,void *);
struct sms_service {
    struct sms_store store;
    sms_write_fn write;
    sms_notify_fn notify;
    void *user;
    uint8_t smsc[12],sequence,ready_sequence;
    size_t smsc_len;
    bool ready_sent,ready_ack,ready_rejected,active,blocked,online;
    unsigned setup_attempts;
    uint64_t next_setup_ms,deadline_ms;
    struct sms_job job;
    unsigned received,decode_errors,store_errors,ack_errors,unmatched;
};
bool sms_service_open(struct sms_service *s,const char *path,sms_write_fn write,sms_notify_fn notify,void *user);
void sms_service_close(struct sms_service *s);
void sms_service_tick(struct sms_service *s,uint64_t now,bool online,bool sim_ready,bool registered,bool writable);
void sms_service_receive(struct sms_service *s,const struct nuxel_sipc_fmt *frame);
#endif
