/* radio_fsm.c — truthful radio/UI state machine. GPL-2.0-only. */
#include "radio_fsm.h"

const char *nuxel_radio_ui_state_name(enum nuxel_radio_ui_state s)
{
    switch (s) {
    case NUXEL_RADIO_STATE_NO_MODEM:     return "no modem";
    case NUXEL_RADIO_STATE_CP_OFFLINE:   return "CP offline";
    case NUXEL_RADIO_STATE_SIM_MISSING:  return "SIM missing";
    case NUXEL_RADIO_STATE_PIN_REQUIRED: return "PIN required";
    case NUXEL_RADIO_STATE_SEARCHING:    return "searching";
    case NUXEL_RADIO_STATE_REGISTERED:   return "registered";
    case NUXEL_RADIO_STATE_ATTACHED:     return "attached";
    case NUXEL_RADIO_STATE_DATA_ACTIVE:  return "data active";
    case NUXEL_RADIO_STATE_FAILURE:      return "failure";
    default:                             return "failure";
    }
}

/*
 * The gate ladder is strictly ordered. A state is reachable only when every
 * lower gate is already satisfied, so the UI can never show "data active" while
 * SIM is missing, etc. This is the truth contract, enforced in code.
 *
 * Order (low -> high):
 *   NO_MODEM < CP_OFFLINE < (SIM_MISSING|PIN_REQUIRED) < SEARCHING
 *            < REGISTERED < ATTACHED < DATA_ACTIVE ; FAILURE orthogonal.
 */
struct nuxel_radio_result nuxel_radio_fsm_eval(const struct nuxel_radio_inputs *in)
{
    struct nuxel_radio_result r = { NUXEL_RADIO_STATE_FAILURE, "invalid-input" };
    if (!in) return r;

    /* FAILURE is orthogonal and highest priority once authenticated. */
    if (in->failure) {
        r.state  = NUXEL_RADIO_STATE_FAILURE;
        r.reason = "authenticated-upstream-error";
        return r;
    }

    if (!in->device_present) {
        r.state  = NUXEL_RADIO_STATE_NO_MODEM;
        r.reason = "no-platform-modem-device";
        return r;
    }

    if (in->cp_state != NUXEL_RADIO_CP_ONLINE) {
        /* Not ONLINE: distinguish SIM_ATTACH (a real, slightly-later signal) is
         * impossible here. Any non-ONLINE CP is "CP offline" unless it is the
         * specific SIM attach/detach transitional value. */
        if (in->cp_state == NUXEL_RADIO_CP_SIM_ATTACH && in->sim_attached) {
            /* SIM attach observed while CP not yet fully online -> searching */
            if (in->registered) {
                r.state  = NUXEL_RADIO_STATE_REGISTERED;
                r.reason = "sim-attached-registered-not-online";
            } else {
                r.state  = NUXEL_RADIO_STATE_SEARCHING;
                r.reason = "sim-attached-searching";
            }
            return r;
        }
        r.state  = NUXEL_RADIO_STATE_CP_OFFLINE;
        r.reason = "cp-not-online";
        return r;
    }

    /* CP ONLINE. Now gate on SIM. */
    if (!in->sim_attached) {
        /*
         * We cannot distinguish "physically absent" from "present but not yet
         * attached" using kernel state alone; both map to the conservative
         * "SIM missing" here UNLESS an authenticated provider indicates
         * PIN_REQUIRED (which itself requires a real SIM present).
         */
        if (in->pin_required) {
            r.state  = NUXEL_RADIO_STATE_PIN_REQUIRED;
            r.reason = "sim-present-pin-required";
        } else {
            r.state  = NUXEL_RADIO_STATE_SIM_MISSING;
            r.reason = "no-authenticated-sim-attach";
        }
        return r;
    }

    /* SIM attached. PIN gate. */
    if (in->pin_required) {
        r.state  = NUXEL_RADIO_STATE_PIN_REQUIRED;
        r.reason = "sim-attached-pin-required";
        return r;
    }

    /* SIM ready. Registration gate. */
    if (!in->registered) {
        r.state  = NUXEL_RADIO_STATE_SEARCHING;
        r.reason = "sim-ready-not-registered";
        return r;
    }

    /* Registered. Data gates. */
    if (!in->attachment) {
        r.state  = NUXEL_RADIO_STATE_REGISTERED;
        r.reason = "registered-not-attached";
        return r;
    }

    if (!in->data_active) {
        r.state  = NUXEL_RADIO_STATE_ATTACHED;
        r.reason = "attached-no-data-bearer";
        return r;
    }

    r.state  = NUXEL_RADIO_STATE_DATA_ACTIVE;
    r.reason = "data-active";
    return r;
}
