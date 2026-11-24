/*
 * data_session.c — S5000AP Stage-06 native data-session state machine.
 * SPDX-License-Identifier: GPL-2.0-only
 */
#include "data_session.h"
#include "fmt_rx.h"
#include <string.h>

#define DS_STEP_TIMEOUT_MS 5000u

const char *ds_phase_name(enum ds_phase p)
{
    switch (p) {
    case DS_IDLE:               return "IDLE";
    case DS_SIM_CHECK:          return "SIM_CHECK";
    case DS_NET_REGIST_CHECK:   return "NET_REGIST_CHECK";
    case DS_SET_SERVICE_DOMAIN: return "SET_SERVICE_DOMAIN";
    case DS_VERIFY_SERVICE_DOMAIN: return "VERIFY_SERVICE_DOMAIN";
    case DS_SET_PREFERRED_NET:  return "SET_PREFERRED_NET";
    case DS_VERIFY_NET_MODE:    return "VERIFY_NET_MODE";
    case DS_ENABLE_MOBILE_DATA: return "ENABLE_MOBILE_DATA";
    case DS_SYNC_PROFILE:       return "SYNC_PROFILE";
    case DS_SET_DATA_PROFILE:   return "SET_DATA_PROFILE";
    case DS_IA_STATE_QUERY:     return "IA_STATE_QUERY";
    case DS_PS_DETACH:          return "PS_DETACH";
    case DS_PS_DETACHED_VERIFY: return "PS_DETACHED_VERIFY";
    case DS_SET_LTE_ATTACH:     return "SET_LTE_ATTACH";
    case DS_MBIM_ATTACH_CONFIG: return "MBIM_ATTACH_CONFIG";
    case DS_DEFINE_PDP:         return "DEFINE_PDP";
    case DS_ALWAYS_ON_PDN:      return "ALWAYS_ON_PDN";
    case DS_PS_REGIST_CHECK:    return "PS_REGIST_CHECK";
    case DS_PS_ATTACH:          return "PS_ATTACH";
    case DS_PS_REGIST_VERIFY:   return "PS_REGIST_VERIFY";
    case DS_DATA_CALL:          return "DATA_CALL";
    case DS_GET_PDP_LIST:       return "GET_PDP_LIST";
    case DS_WAIT_IP:            return "WAIT_IP";
    case DS_RECOVER_PS_ATTACH:  return "RECOVER_PS_ATTACH";
    case DS_RECOVER_PS_REGIST:  return "RECOVER_PS_REGIST";
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
    c->phase = DS_SIM_CHECK;
    c->phase_entered_ms = 0;
    c->profile_id = profile_id;
    c->protocol = 2;   /* IPv4; the CP rejects dual-stack in the initial profile */
    c->preferred_net = 9;
    c->attach_cid = DS_ATTACH_CID; /* default RIL slot 0 */
    c->attach_flag = 1; /* CP PMPM_CreateProfile for profile zero; 3 adds profile 12 */
    c->auth_code = 0;   /* DataAuth NONE */
    c->pdp_type_wire = 1; /* activate */
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

void ds_expect(struct data_session_ctx *c, uint8_t main, uint8_t sub, uint8_t type)
{
    c->expected_main = main; c->expected_sub = sub; c->expected_type = type;
    c->expected_valid = true; c->gen_result_valid = false;
}

enum ds_gen_status ds_gen_response(struct data_session_ctx *c, const uint8_t *p,
                                   size_t n)
{
    struct fmt_rx_gen r;
    if (!c || !c->expected_valid || !fmt_rx_gen(p, n, &r) ||
        r.main != c->expected_main || r.sub != c->expected_sub ||
        r.type != c->expected_type) return DS_GEN_IGNORE;
    c->last_gen_result = r.result; c->gen_result_valid = true;
    if (r.result == FMT_RX_GEN_OK) return DS_GEN_ACCEPTED;
    /* CP handler 0x4121c0f2 returns 0x8003 before doing anything when its
     * optional mobile-data feature is disabled. This is NOT already-on. */
    if (c->phase == DS_ENABLE_MOBILE_DATA && r.main == 13 && r.sub == 29 &&
        r.type == 3 && r.result == FMT_RX_GEN_UNSUPPORTED) {
        c->mobile_data_unsupported = true;
        c->mobile_data_on = false;
        return DS_GEN_OPTIONAL_UNSUPPORTED;
    }
    return DS_GEN_REJECTED;
}

bool ds_terminal(const struct data_session_ctx *c)
{
    if (!c) return true;
    return c->phase == DS_ACTIVE || c->phase == DS_REJECTED || c->phase == DS_FAILED;
}

static enum ds_phase fail(struct data_session_ctx *c, enum ds_phase result)
{
    if (c->failure_phase == DS_IDLE) {
        c->failure_phase = c->phase;
        c->failure_result = c->last_gen_result;
        c->failure_result_valid = c->gen_result_valid;
    }
    if (c->needs_ps_restore && c->phase != DS_RECOVER_PS_ATTACH &&
        c->phase != DS_RECOVER_PS_REGIST) {
        c->phase = DS_RECOVER_PS_ATTACH;
        c->attempt = 0;
        c->step_deadline_ms = 0;
        c->expected_valid = false;
    } else c->phase = result;
    return c->phase;
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
            return fail(c, DS_FAILED);
        }
        c->attempt++;
        c->step_deadline_ms = now_ms + DS_STEP_TIMEOUT_MS;
        return c->phase;
    }

    if (!ack) return c->phase;   /* still waiting for the modem */

    /* ack received: advance to the next verified phase */
    c->step_deadline_ms = now_ms + DS_STEP_TIMEOUT_MS;
    c->expected_valid = false;
    c->attempt = 0;
    switch (c->phase) {
    case DS_SIM_CHECK:          c->phase = DS_NET_REGIST_CHECK;   break;
    case DS_NET_REGIST_CHECK:   c->phase = DS_SET_SERVICE_DOMAIN; break;
    case DS_SET_SERVICE_DOMAIN: c->phase = DS_VERIFY_SERVICE_DOMAIN; break;
    case DS_VERIFY_SERVICE_DOMAIN: c->phase = DS_SET_PREFERRED_NET; break;
    case DS_SET_PREFERRED_NET:  c->phase = DS_VERIFY_NET_MODE; break;
    case DS_VERIFY_NET_MODE:    c->phase = DS_ENABLE_MOBILE_DATA; break;
    case DS_ENABLE_MOBILE_DATA: c->phase = DS_SET_DATA_PROFILE;   break;  /* SYNC_PROFILE(sub=37) live-rejected (GEN=1); skip */
    case DS_SYNC_PROFILE:       c->phase = DS_SET_DATA_PROFILE;   break;
    case DS_SET_DATA_PROFILE:   c->phase = c->reattach_for_apn ? DS_IA_STATE_QUERY : DS_SET_LTE_ATTACH; break;
    case DS_IA_STATE_QUERY:
        if (c->net_regist_valid) c->phase = c->attached ? DS_PS_DETACH : DS_SET_LTE_ATTACH;
        break;
    case DS_PS_DETACH:          c->phase = DS_PS_DETACHED_VERIFY; break;
    case DS_PS_DETACHED_VERIFY: c->phase = DS_SET_LTE_ATTACH; break;
    case DS_SET_LTE_ATTACH:     c->phase = DS_MBIM_ATTACH_CONFIG; break;  /* then MBIM attach-config, then define+activate */
    case DS_MBIM_ATTACH_CONFIG: c->phase = DS_DEFINE_PDP;          break;
    case DS_DEFINE_PDP:         c->phase = DS_ALWAYS_ON_PDN;      break;
    case DS_ALWAYS_ON_PDN:      c->phase = DS_PS_REGIST_CHECK; break;
    case DS_PS_REGIST_CHECK:
        if (c->net_regist_valid) {
            if (fmt_rx_registered(c->last_ps_reg_state)) c->needs_ps_restore = false;
            c->phase = fmt_rx_registered(c->last_ps_reg_state) ? DS_DATA_CALL : DS_PS_ATTACH;
        }
        break;
    case DS_PS_ATTACH:          c->phase = DS_PS_REGIST_VERIFY; break;
    case DS_PS_REGIST_VERIFY:   c->needs_ps_restore = false; c->phase = DS_DATA_CALL; break;
    case DS_RECOVER_PS_ATTACH:  c->phase = DS_RECOVER_PS_REGIST; break;
    case DS_RECOVER_PS_REGIST:  c->needs_ps_restore = false; c->phase = DS_REJECTED; break;
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
            return fail(c, DS_FAILED);
        } else {
            c->attempt++;
            return fail(c, DS_REJECTED);
        }
        return c->phase;
    }

    /* Success: advance exactly like ds_step(ack=true). */
    return ds_step(c, true, now_ms);
}
