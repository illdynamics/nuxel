/* SPDX-License-Identifier: GPL-2.0-only */
#ifndef NUXEL_IMS_INIT_H
#define NUXEL_IMS_INIT_H
#include <stdint.h>
#include <stdbool.h>
#include "fmt_tx.h"

/* Native IMS device-capability initialization.
 *
 * Stock Samsung initializes the modem IMS stack by advertising truthful
 * device voice-domain capability via ModemProxy::GetDeviceCapa/SetDeviceCapa
 * (IpcTxGetDeviceCapa main=10 MISC sub=45 type=2 request, then IpcTxSetDeviceCapa
 * main=10 MISC sub=45 type=3 2-byte payload) BEFORE driving registration.
 * Without this the modem's IMS stack is not armed and SetImsRegState never
 * produces an authoritative registration notification (observed: GEN 0x8000
 * ack only, then registration timeout).
 *
 * This module is a bounded, response-correlated FSM that performs ONLY that
 * legitimate capability advertisement. It never fabricates capability or
 * registration; it observes a real modem acknowledgment and reports readiness
 * to the IMS registration FSM. */
typedef bool (*ims_init_write_fn)(const struct fmt_tx_frame *f, uint8_t *seq, void *user);

enum ims_init_phase {
    IMS_INIT_IDLE = 0,
    IMS_INIT_SEND_GET,      /* query device capability (MISC sub=45 type=2) */
    IMS_INIT_WAIT_GET_ACK,  /* awaiting GEN ack for the capability query */
    IMS_INIT_SEND_CAPA,     /* advertise device capability (MISC sub=45 type=3) */
    IMS_INIT_WAIT_ACK,      /* awaiting GEN acknowledgment for the capability set */
    IMS_INIT_DONE,          /* capability acknowledged; IMS may register */
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
