/*
 * data_session.c — S5000AP Stage-06 native data-session state machine.
 * SPDX-License-Identifier: GPL-2.0-only
 */
#include "data_session.h"
#include <string.h>

#define DS_STEP_TIMEOUT_MS 5000u

const char *ds_phase_name(enum ds_phase p)
{
    switch (p) {
    case DS_IDLE:               return "IDLE";
    case DS_SIM_CHECK:          return "SIM_CHECK";
    case DS_NET_REGIST_CHECK:   return "NET_REGIST_CHECK";
    case DS_SET_SERVICE_DOMAIN: return "SET_SERVICE_DOMAIN";
    case DS_SET_PREFERRED_NET:  return "SET_PREFERRED_NET";
    case DS_ENABLE_MOBILE_DATA: return "ENABLE_MOBILE_DATA";
    case DS_SYNC_PROFILE:       return "SYNC_PROFILE";
    case DS_SET_DATA_PROFILE:   return "SET_DATA_PROFILE";
    case DS_SET_LTE_ATTACH:     return "SET_LTE_ATTACH";
    case DS_DEFINE_PDP:         return "DEFINE_PDP";
    case DS_ALWAYS_ON_PDN:      return "ALWAYS_ON_PDN";
    case DS_PS_ATTACH:          return "PS_ATTACH";
    case DS_PS_REGIST_VERIFY:   return "PS_REGIST_VERIFY";
    case DS_DATA_CALL:          return "DATA_CALL";
    case DS_GET_PDP_LIST:       return "GET_PDP_LIST";
    case DS_WAIT_IP:            return "WAIT_IP";
    case DS_ACTIVE:             return "ACTIVE";
    case DS_REJECTED:           return "REJECTED";
    case DS_FAILED:             return "FAILED";
    default:                    return "UNKNOWN";
    }
}

void ds_reset(struct data_session_ctx *c, const char *apn, uint8_t profile_id)
{
    if (!c) return;
    memset(c, 0, sizeof *c);
    c->phase = DS_NET_REGIST_CHECK;   /* SIM already READY (CP-notified); read PS/data registration first */
    c->phase_entered_ms = 0;
    c->profile_id = profile_id;
    c->gen_result_valid = false;
    c->gprs_call_state_valid = false;
    c->gprs_pdp_state_valid = false;
    if (apn) {
        size_t n = strlen(apn);
        if (n > sizeof c->apn - 1) n = sizeof c->apn - 1;
        memcpy(c->apn, apn, n);
        c->apn_len = (uint8_t)n;
        c->apn[n] = 0;
    }
}

bool ds_terminal(const struct data_session_ctx *c)
{
    if (!c) return true;
    return c->phase == DS_ACTIVE || c->phase == DS_REJECTED || c->phase == DS_FAILED;
}

/*
 * Advance the FSM. `ack` is true only when the corresponding modem response
 * for the *current* phase has been authenticated (not merely "frame written").
 * `now_ms` is monotonic. This is a bounded state machine: each phase waits for
 * an authenticated ack and times out with a bounded retry budget.
 */
enum ds_phase ds_step(struct data_session_ctx *c, bool ack, uint64_t now_ms)
{
    if (!c) return DS_FAILED;
    if (c->phase == DS_IDLE) return DS_IDLE;

    /* Timeout guard: do not loop forever. */
    if (c->step_deadline_ms && now_ms >= c->step_deadline_ms && !ack) {
        if (c->attempt >= 3) {     /* bounded: 3 attempts total */
            c->phase = DS_FAILED;
            return c->phase;
        }
        c->attempt++;
        c->step_deadline_ms = now_ms + DS_STEP_TIMEOUT_MS;
        return c->phase;
    }

    if (!ack) return c->phase;   /* still waiting for the modem */

    /* ack received: advance to the next verified phase */
    c->step_deadline_ms = now_ms + DS_STEP_TIMEOUT_MS;
    switch (c->phase) {
    case DS_SIM_CHECK:          c->phase = DS_NET_REGIST_CHECK;   break;
    case DS_NET_REGIST_CHECK:   c->phase = DS_SET_SERVICE_DOMAIN; break;
    case DS_SET_SERVICE_DOMAIN: c->phase = DS_SET_PREFERRED_NET;  break;
    case DS_SET_PREFERRED_NET:  c->phase = DS_ENABLE_MOBILE_DATA; break;
    case DS_ENABLE_MOBILE_DATA: c->phase = DS_SET_DATA_PROFILE;   break;  /* skip SyncProfile (rejected result=1) */
    case DS_SYNC_PROFILE:       c->phase = DS_SET_DATA_PROFILE;   break;
    case DS_SET_DATA_PROFILE:   c->phase = DS_SET_LTE_ATTACH;     break;
    case DS_SET_LTE_ATTACH:     c->phase = DS_ALWAYS_ON_PDN;      break;  /* DefinePdp(sub=1) is legacy 3G; LTE uses SetPdpContext(sub=4) define+activate in one */
    case DS_DEFINE_PDP:         c->phase = DS_ALWAYS_ON_PDN;      break;
    case DS_ALWAYS_ON_PDN:      c->phase = DS_PS_ATTACH;          break;
    case DS_PS_ATTACH:          c->phase = DS_PS_REGIST_VERIFY;   break;
    case DS_PS_REGIST_VERIFY:   c->phase = DS_DATA_CALL;          break;
    case DS_DATA_CALL:          c->phase = DS_GET_PDP_LIST;       break;
    case DS_GET_PDP_LIST:       c->phase = DS_WAIT_IP;            break;
    case DS_WAIT_IP:            c->phase = DS_ACTIVE;             break;
    case DS_ACTIVE: case DS_REJECTED: case DS_FAILED:
        break;   /* terminal */
    default:
        break;
    }
    return c->phase;
}


/*
 * Strict response-feedback driver.
 *
 * Unlike ds_step(ack=true), this function consumes the DECODED result of a real
 * modem response for the current phase. A non-zero GEN result, an "not
 * connected" GPRS_CALL_STATUS, or an empty PDP-context list means the step
 * FAILED and the FSM must NOT advance. On failure we move to DS_REJECTED (a
 * terminal, observable state) with a bounded attempt budget so we never loop
 * and never silently claim a bearer that does not exist.
 */
enum ds_phase ds_feedback(struct data_session_ctx *c, bool success, uint64_t now_ms)
{
    if (!c) return DS_FAILED;
    if (c->phase == DS_IDLE || c->phase == DS_ACTIVE ||
        c->phase == DS_REJECTED || c->phase == DS_FAILED)
        return c->phase;

    if (!success) {
        /* Rejection: stop on this attempt, honouring the truth contract. */
        if (c->attempt >= 3u) {
            c->phase = DS_FAILED;
        } else {
            c->attempt++;
            c->phase = DS_REJECTED;
        }
        return c->phase;
    }

    /* Success: advance exactly like ds_step(ack=true). */
    return ds_step(c, true, now_ms);
}
