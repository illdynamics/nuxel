/* SPDX-License-Identifier: GPL-2.0-only */
#ifndef NUXEL_MOBILE_DATA_H
#define NUXEL_MOBILE_DATA_H
#include "fmt_tx.h"
#include "sipc5_fmt.h"
#include <stdbool.h>
#include <stdint.h>
enum mobile_stop_phase { MOBILE_STOP_IDLE, MOBILE_STOP_SETTING, MOBILE_STOP_ALWAYS,
    MOBILE_STOP_RELEASE, MOBILE_STOP_VERIFY, MOBILE_STOP_DONE, MOBILE_STOP_FAILED };
struct mobile_stop { enum mobile_stop_phase phase; bool pending; uint8_t sequence,subcommand;
    uint64_t deadline; int result; };
/* Missing file preserves the supplied installation default. Invalid files fail closed. */
int mobile_preference_load(const char *path,bool *enabled);
int mobile_preference_save(const char *path,bool enabled);
void mobile_stop_begin(struct mobile_stop *s);
bool mobile_stop_frame(struct mobile_stop *s,struct fmt_tx_frame *frame);
void mobile_stop_sent(struct mobile_stop *s,uint8_t sequence,uint64_t now);
void mobile_stop_receive(struct mobile_stop *s,const struct nuxel_sipc_fmt *frame);
void mobile_stop_tick(struct mobile_stop *s,uint64_t now);
bool mobile_stop_busy(const struct mobile_stop *s);
#endif
