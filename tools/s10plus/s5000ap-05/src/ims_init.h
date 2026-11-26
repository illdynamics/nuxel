/* SPDX-License-Identifier: GPL-2.0-only */
#ifndef NUXEL_IMS_INIT_H
#define NUXEL_IMS_INIT_H
#include <stdint.h>
#include <stdbool.h>
#include "fmt_tx.h"

/* Modem capability configuration. Completion means configuration was
 * acknowledged, never SIP registration or IMS transport readiness. The
 * current runtime reports AP VoLTE not-ready until a native backend exists.
 * Previously rejected SDM SMS probes are not repeated on service restart. */
typedef bool (*ims_init_write_fn)(const struct fmt_tx_frame *f, uint8_t *seq, void *user);

enum ims_init_phase {
    IMS_INIT_IDLE = 0,
    IMS_INIT_SEND_GET,      /* query device capability (MISC sub=45 type=2) */
    IMS_INIT_WAIT_GET_ACK,  /* awaiting GEN ack for the capability query */
    IMS_INIT_SEND_CAPA,     /* advertise device capability (MISC sub=45 type=3) */
    IMS_INIT_WAIT_ACK,      /* awaiting GEN ack for the capability set */
    IMS_INIT_SEND_SDM_MODE, /* arm modem IMS stack (MISC sub=32 SDM_IMS_MODE ON) */
    IMS_INIT_WAIT_SDM_MODE, /* awaiting GEN ack for SDM_IMS_MODE */
    IMS_INIT_SEND_SMS_FMT,  /* arm SMS-over-IP format (MISC sub=26 type=3) */
    IMS_INIT_WAIT_SMS_FMT,  /* awaiting GEN ack for SMS_FMT */
    IMS_INIT_SEND_SMS_OIP,  /* enable SMS-over-IP (MISC sub=27 type=3) */
    IMS_INIT_WAIT_SMS_OIP,  /* awaiting GEN ack for SMS_OVER_IP */
    IMS_INIT_SEND_VOLTE_STATE,  /* notify AP IMS stack ready (NET sub=52) */
    IMS_INIT_WAIT_VOLTE_STATE,  /* awaiting GEN ack for VOLTE_STATE */
    IMS_INIT_DONE,          /* capability + SMS-over-IP + VoLTE ready */
    IMS_INIT_FAILED,
};

struct ims_init {
    ims_init_write_fn write;
    void *user;
    enum ims_init_phase phase;
    uint8_t attempt;
    uint8_t last_write_seq;
    uint64_t next_action_ms;
    uint64_t phase_deadline_ms;
    bool done;
};

bool ims_init_open(struct ims_init *i, ims_init_write_fn write, void *user);
void ims_init_close(struct ims_init *i);
/* Advance the capability-init FSM. `now_ms` monotonic; `online` = CP online +
 * SIM ready + writable. Returns current phase. */
enum ims_init_phase ims_init_tick(struct ims_init *i, uint64_t now_ms, bool online);
/* Correlate a GEN response to the last capability write (SetDeviceCapa). */
void ims_init_gen_result(struct ims_init *i, uint16_t result, uint8_t ack_seq);
/* Report the modem's direct GetDeviceCapa response (main=10 sub=45 type=2). */
void ims_init_capa_response(struct ims_init *i, uint8_t ack_seq);
bool ims_init_done(const struct ims_init *i);
const char *ims_init_phase_name(enum ims_init_phase p);

#endif /* NUXEL_IMS_INIT_H */
