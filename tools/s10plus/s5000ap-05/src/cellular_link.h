/* SPDX-License-Identifier: GPL-2.0-only */
#ifndef NUXEL_CELLULAR_LINK_H
#define NUXEL_CELLULAR_LINK_H
#include "fmt_rx.h"
#include <sys/types.h>

enum cellular_link_operation { CELL_LINK_NONE, CELL_LINK_APPLY, CELL_LINK_DOWN, CELL_LINK_CHECK };
struct cellular_link {
    pid_t pid;
    uint64_t deadline_ms;
    enum cellular_link_operation operation;
    bool configured, timed_out;
    int result;
};
/* Asynchronous child: modem/RFS reception continues during OS configuration.
 * The helper consumes only validated CP addresses, never shell fragments. */
bool cellular_link_apply(struct cellular_link *link,const struct fmt_rx_ip *ip,uint64_t now);
bool cellular_link_down(struct cellular_link *link,uint64_t now);
bool cellular_link_check(struct cellular_link *link,uint64_t now);
/* true only on completion; result is zero on verified success. */
bool cellular_link_poll(struct cellular_link *link,uint64_t now);
#endif
