/* SPDX-License-Identifier: GPL-2.0-only */
#ifndef NUXEL_CALL_SERVICE_H
#define NUXEL_CALL_SERVICE_H
#include "fmt_call.h"
#include "sipc5_fmt.h"
typedef bool (*call_write_fn)(const struct fmt_tx_frame *,uint8_t *,void *);
typedef void (*call_notify_fn)(uint8_t id,const char *state,bool incoming,void *);
struct call_service {
    struct fmt_call_list list;
    struct fmt_call_status status;
    bool list_valid,status_valid,pending,query_pending,dial_waiting;
    uint8_t sequence,subcommand,query_sequence;
    int result; /* -1 pending, -2 unknown after timeout; 0x8000 accepted */
    uint64_t deadline_ms,next_query_ms,query_deadline_ms;
    unsigned parse_errors,unmatched;
    call_write_fn write;
    call_notify_fn notify;
    void *user;
};
void call_service_init(struct call_service *,call_write_fn,call_notify_fn,void *);
void call_service_tick(struct call_service *,uint64_t now,bool online,bool writable);
void call_service_receive(struct call_service *,const struct nuxel_sipc_fmt *);
bool call_service_dial(struct call_service *,const char *number,uint64_t now);
bool call_service_answer(struct call_service *,uint64_t now);
bool call_service_hangup(struct call_service *,uint64_t now);
#endif
