/* SPDX-License-Identifier: GPL-2.0-only */
#ifndef NUXEL_FMT_CALL_H
#define NUXEL_FMT_CALL_H
#include "fmt_tx.h"
#define FMT_CALL_MAX 7
#define FMT_CALL_NUMBER 83
struct fmt_call { uint16_t type;uint8_t id,direction,state,multiparty;char number[FMT_CALL_NUMBER]; };
struct fmt_call_list { size_t count;struct fmt_call calls[FMT_CALL_MAX]; };
struct fmt_call_status { uint16_t type;uint8_t id,state,cause_class,cause; };
/* Normal CS voice only, no emergency or supplementary-service encoding. */
bool fmt_call_dial(struct fmt_tx_frame *f,const char *number);
bool fmt_call_answer(struct fmt_tx_frame *f);
bool fmt_call_release(struct fmt_tx_frame *f);
bool fmt_call_get_list(struct fmt_tx_frame *f);
bool fmt_call_voice_registration(struct fmt_tx_frame *f);
bool fmt_call_list(const uint8_t *p,size_t n,struct fmt_call_list *out);
bool fmt_call_status(const uint8_t *p,size_t n,struct fmt_call_status *out);
const char *fmt_call_state_name(uint8_t state);
#endif
