/*
 * data_session.h — S5000AP Stage-06 native data-session state machine.
 * SPDX-License-Identifier: GPL-2.0-only
 *
 * Drives the verified FMT data-path commands (mobile-data, set-data-profile,
 * set-lte-attach-profile, define PDP context, always-on PDN, PS attach,
 * data-call establish) in a bounded, step-wise, response-correlated sequence.
 * This module is PURE re: I/O — it only advances the FSM state; the caller
 * (radiod) performs the actual bounded device writes via fmt_tx + the
 * transport, and feeds back modem responses.
 *
 * TRUTH CONTRACT:
 *  - A step does NOT "succeed" merely because a frame was written. It advances
 *    ONLY when the corresponding modem response is authenticated.
 *  - Retries are bounded. On a modem rejection the FSM stops and reports the
 *    exact failure; it never brute-forces commands/APNs/flags.
 *  - No PIN/PUK/IMSI/ICCID/IMEI/MSISDN is ever stored or logged.
 */
#ifndef NUXEL_DATA_SESSION_H
#define NUXEL_DATA_SESSION_H

#include <stdint.h>
#include <stdbool.h>

enum ds_phase {
    DS_IDLE = 0,
    DS_SIM_CHECK,          /* confirm SIM READY */
    DS_ENABLE_MOBILE_DATA, /* GPRS mobile data ON */
    DS_SET_DATA_PROFILE,   /* set APN/auth/protocol data profile */
    DS_SET_LTE_ATTACH,     /* set LTE attach profile (required for LTE PS) */
    DS_DEFINE_PDP,         /* define PDP context w/ APN */
    DS_ALWAYS_ON_PDN,      /* always-on PDN profile */
    DS_PS_ATTACH,          /* GPRS PS attach */
    DS_DATA_CALL,          /* establish data call */
    DS_WAIT_IP,            /* wait for rmnet + IP config */
    DS_ACTIVE,             /* data active */
    DS_REJECTED,           /* modem rejected (terminal for this attempt) */
    DS_FAILED,             /* timeout/generic failure */
};

struct data_session_ctx {
    enum ds_phase  phase;
    uint8_t        attempt;      /* bounded attempt counter */
    uint8_t        apn[128];     /* configured APN (owner-approved) */
    uint8_t        apn_len;
    uint8_t        profile_id;
    bool           mobile_data_on;
    bool           attached;
    bool           call_established;
    bool           ip_configured;
    uint64_t       step_deadline_ms;
};

/* Advance the FSM given: current phase, whether the last modem response
 * acknowledged the step, and a monotonic timestamp. Returns the phase to
 * surface. Pure: does not write anything. */
enum ds_phase ds_step(struct data_session_ctx *c, bool ack, uint64_t now_ms);

/* Reset for a new bounded attempt. */
void ds_reset(struct data_session_ctx *c, const char *apn, uint8_t profile_id);

/* Human-readable phase name (diagnostics, no secrets). */
const char *ds_phase_name(enum ds_phase p);

/* True if the FSM has reached a terminal phase (ACTIVE/REJECTED/FAILED). */
bool ds_terminal(const struct data_session_ctx *c);

#endif /* NUXEL_DATA_SESSION_H */
