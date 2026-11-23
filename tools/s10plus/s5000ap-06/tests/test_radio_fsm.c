/*
 * test_radio_fsm.c — unit tests for the truthful radio/UI state machine.
 * SPDX-License-Identifier: GPL-2.0-only
 *
 * These are OFFLINE fixtures. They prove the gate ladder is monotonic and that
 * the FSM never advances a gate without the prerequisite authenticated inputs.
 * They are NOT physical radio results.
 */
#include "radio_fsm.h"
#include <stdio.h>
#include <string.h>

static int failures = 0;

#define CHECK(cond, msg) do { \
    if (!(cond)) { ++failures; fprintf(stderr, "FAIL: %s (line %d)\n", (msg), __LINE__); } \
} while (0)

static struct nuxel_radio_inputs base(void)
{
    struct nuxel_radio_inputs in;
    memset(&in, 0, sizeof in);
    in.device_present = true;
    in.cp_state = NUXEL_RADIO_CP_ONLINE;
    in.sim_attached = true;
    in.registered = true;
    in.attachment = true;
    in.data_active = false;
    return in;
}

int main(void)
{
    struct nuxel_radio_inputs in;
    struct nuxel_radio_result r;

    /* 1. NULL input -> failure, never crash. */
    r = nuxel_radio_fsm_eval(NULL);
    CHECK(r.state == NUXEL_RADIO_STATE_FAILURE, "NULL input must be FAILURE");

    /* 2. No device -> no modem. */
    in = base(); in.device_present = false;
    r = nuxel_radio_fsm_eval(&in);
    CHECK(r.state == NUXEL_RADIO_STATE_NO_MODEM, "no device -> NO_MODEM");

    /* 3. CP offline -> CP offline. */
    in = base(); in.cp_state = 0; /* STATE_OFFLINE */
    r = nuxel_radio_fsm_eval(&in);
    CHECK(r.state == NUXEL_RADIO_STATE_CP_OFFLINE, "cp offline -> CP_OFFLINE");

    /* 4. CP online, no SIM attach, no PIN -> SIM missing. */
    in = base(); in.sim_attached = false; in.pin_required = false;
    r = nuxel_radio_fsm_eval(&in);
    CHECK(r.state == NUXEL_RADIO_STATE_SIM_MISSING, "no sim attach -> SIM_MISSING");

    /* 5. CP online, no SIM attach but PIN required -> PIN required (PIN implies presence). */
    in = base(); in.sim_attached = false; in.pin_required = true;
    r = nuxel_radio_fsm_eval(&in);
    CHECK(r.state == NUXEL_RADIO_STATE_PIN_REQUIRED, "pin required -> PIN_REQUIRED");

    /* 6. SIM attached, PIN required -> PIN required. */
    in = base(); in.sim_attached = true; in.pin_required = true;
    r = nuxel_radio_fsm_eval(&in);
    CHECK(r.state == NUXEL_RADIO_STATE_PIN_REQUIRED, "attached+pin -> PIN_REQUIRED");

    /* 7. SIM ready, not registered -> searching. */
    in = base(); in.sim_attached = true; in.pin_required = false; in.registered = false;
    r = nuxel_radio_fsm_eval(&in);
    CHECK(r.state == NUXEL_RADIO_STATE_SEARCHING, "ready not registered -> SEARCHING");

    /* 8. registered, not attached -> registered. */
    in = base(); in.registered = true; in.attachment = false;
    r = nuxel_radio_fsm_eval(&in);
    CHECK(r.state == NUXEL_RADIO_STATE_REGISTERED, "registered not attached -> REGISTERED");

    /* 9. attached, no data -> attached. */
    in = base(); in.attachment = true; in.data_active = false;
    r = nuxel_radio_fsm_eval(&in);
    CHECK(r.state == NUXEL_RADIO_STATE_ATTACHED, "attached no data -> ATTACHED");

    /* 10. data active -> data active. */
    in = base(); in.data_active = true;
    r = nuxel_radio_fsm_eval(&in);
    CHECK(r.state == NUXEL_RADIO_STATE_DATA_ACTIVE, "data active -> DATA_ACTIVE");

    /* 11. failure overrides everything (even data active). */
    in = base(); in.data_active = true; in.failure = true;
    r = nuxel_radio_fsm_eval(&in);
    CHECK(r.state == NUXEL_RADIO_STATE_FAILURE, "failure overrides all");

    /* 12. Monotonic gate: data_active can NEVER be reached without registered. */
    in = base(); in.registered = false; in.data_active = true;
    r = nuxel_radio_fsm_eval(&in);
    CHECK(r.state != NUXEL_RADIO_STATE_DATA_ACTIVE, "data active requires registered");

    /* 13. Monotonic gate: data_active can NEVER be reached without sim_attached. */
    in = base(); in.sim_attached = false; in.data_active = true;
    r = nuxel_radio_fsm_eval(&in);
    CHECK(r.state == NUXEL_RADIO_STATE_SIM_MISSING, "data active requires sim attach");

    /* 14. State name mapping. */
    CHECK(strcmp(nuxel_radio_ui_state_name(NUXEL_RADIO_STATE_NO_MODEM), "no modem") == 0,
          "NO_MODEM name");
    CHECK(strcmp(nuxel_radio_ui_state_name(NUXEL_RADIO_STATE_DATA_ACTIVE), "data active") == 0,
          "DATA_ACTIVE name");

    if (failures == 0) {
        printf("RESULT=PASS: 0 failures\n");
        return 0;
    }
    printf("RESULT=FAIL: %d failures\n", failures);
    return 1;
}
