/*
 * radio_fsm.h — S5000AP truthful radio/UI state machine.
 *
 * SPDX-License-Identifier: GPL-2.0-only
 *
 * This module maps *observed, authenticated* radio inputs into one of the
 * Stage-06 UI states required by directive 06:
 *
 *   NO_MODEM, CP_OFFLINE, SIM_MISSING, PIN_REQUIRED, SEARCHING,
 *   REGISTERED, ATTACHED, DATA_ACTIVE, FAILURE
 *
 * It is PURE and side-effect free: it never opens a device node, never sends
 * an ioctl, never transmits SIPC/RFS traffic, and never fabricates a transition
 * the inputs do not support. It only computes a state label + a machine-readable
 * rationale from a struct of authenticated inputs.
 *
 * Input provenance discipline (mirrors 00_MASTER_SAFETY_AND_TRUTH.md):
 *   - cp_state        : ONLY from kernel phone_state (sysfs "modem_state" or
 *                       IOCTL_MODEM_STATUS). NEVER from daemon liveness.
 *   - sim_detect      : the GPIC "ds_detect" module param is NOT real SIM
 *                       presence (it is a static dual-SIM config flag). Real SIM
 *                       state is STATE_SIM_ATTACH/STATE_SIM_DETACH from
 *                       IOCTL_MODEM_STATUS. This FSM therefore does NOT accept
 *                       ds_detect as a presence signal; it accepts sim_attached.
 *   - sim_attached    : true iff kernel reports STATE_SIM_ATTACH (protocol-backed
 *                       CP->AP SIM attach notification).
 *   - pin_required    : true iff an authenticated RIL/SIM provider reports
 *                       PIN_REQUIRED. (No PIN/PUK value is ever stored here.)
 *   - registered      : true iff an authenticated RIL/operator source reports
 *                       registered (operator + RAT from a real CP response),
 *                       NOT from signal bars.
 *   - data_active     : true iff a real PDP/data bearer + rmnet UP + IP + route
 *                       table are authenticated as cellular.
 *   - failure         : true iff an authenticated upstream error occurred
 *                       (CP crash, link loss, DNS fail, daemon failure).
 *
 * The state machine is monotonic in the sense that a more "capable" state is
 * reachable ONLY when every prerequisite gate below it is also satisfied. It
 * refuses to advance to DATA_ACTIVE without REGISTERED, etc.
 */
#ifndef NUXEL_RADIO_FSM_H
#define NUXEL_RADIO_FSM_H

#include <stdbool.h>
#include <stdint.h>
#include <stddef.h>

#ifdef __cplusplus
extern "C" {
#endif

enum nuxel_radio_ui_state {
    NUXEL_RADIO_STATE_NO_MODEM = 0,
    NUXEL_RADIO_STATE_CP_OFFLINE,
    NUXEL_RADIO_STATE_SIM_MISSING,
    NUXEL_RADIO_STATE_PIN_REQUIRED,
    NUXEL_RADIO_STATE_SEARCHING,
    NUXEL_RADIO_STATE_REGISTERED,
    NUXEL_RADIO_STATE_ATTACHED,
    NUXEL_RADIO_STATE_DATA_ACTIVE,
    NUXEL_RADIO_STATE_FAILURE,
    NUXEL_RADIO_STATE_MAX,
};

struct nuxel_radio_inputs {
    bool device_present;       /* S5000AP modem platform device present */
    uint8_t cp_state;          /* enum modem_state value (kernel) */
    bool sim_attached;         /* STATE_SIM_ATTACH (protocol-backed) */
    bool pin_required;         /* authenticated PIN_REQUIRED (no PIN value) */
    bool registered;           /* operator+RAT from real CP response */
    bool attachment;           /* GPRS/PS attach / registered home/roam */
    bool data_active;          /* PDP + rmnet UP + IP + route (cellular) */
    bool failure;              /* authenticated upstream error */
};

struct nuxel_radio_result {
    enum nuxel_radio_ui_state state;
    /*
     * "reason" is a SHORT, non-secret, machine-readable rationale. It NEVER
     * contains IMSI/ICCID/IMEI/PIN/PUK/MSISDN or other private identity.
     */
    const char *reason;
};

#define NUXEL_RADIO_CP_ONLINE     4u
#define NUXEL_RADIO_CP_SIM_ATTACH 7u
#define NUXEL_RADIO_CP_SIM_DETACH 8u

const char *nuxel_radio_ui_state_name(enum nuxel_radio_ui_state s);

/*
 * Compute the truthful UI state. Pure. Never touches I/O, never fabricates.
 * Returns by value and always populates a valid enum; on invalid input it
 * degrades to the most conservative state the inputs still allow, and records
 * a reason string.
 */
struct nuxel_radio_result nuxel_radio_fsm_eval(const struct nuxel_radio_inputs *in);

#ifdef __cplusplus
}
#endif
#endif /* NUXEL_RADIO_FSM_H */
