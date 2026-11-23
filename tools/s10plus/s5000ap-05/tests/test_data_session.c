/*
 * test_data_session.c — unit tests for the Stage-06 data-session FSM.
 * SPDX-License-Identifier: GPL-2.0-only
 */
#include "data_session.h"
#include <stdio.h>
#include <string.h>

static int failures = 0;
#define CHECK(c, ...) do { if (!(c)) { failures++; printf("FAIL %s:%d: ", __FILE__, __LINE__); printf(__VA_ARGS__); printf("\n"); } \
    else { printf("ok   %s:%d: ", __FILE__, __LINE__); printf(__VA_ARGS__); printf("\n"); } } while (0)

int main(void)
{
    struct data_session_ctx c;
    ds_reset(&c, "internet", 1);

    CHECK(c.phase == DS_NET_REGIST_CHECK, "starts at NET_REGIST_CHECK (SIM already READY)");
    CHECK(strcmp((const char*)c.apn, "internet") == 0, "APN recorded");
    CHECK(c.profile_id == 1, "profile id recorded");

    /* No ack -> stays put (no fabricated advance). */
    enum ds_phase p = ds_step(&c, false, 100);
    CHECK(p == DS_NET_REGIST_CHECK, "no ack -> stays NET_REGIST_CHECK");

    /* Authenticated ack advances each phase in order
     * (NET_REGIST_CHECK -> ENABLE_MOBILE_DATA -> SYNC_PROFILE -> ... -> ACTIVE). */
    p = ds_step(&c, true, 100);  CHECK(p == DS_ENABLE_MOBILE_DATA, "NET_REGIST_CHECK -> ENABLE_MOBILE_DATA");
    p = ds_step(&c, true, 100);  CHECK(p == DS_SYNC_PROFILE, "ENABLE_MOBILE_DATA -> SYNC_PROFILE");
    p = ds_step(&c, true, 100);  CHECK(p == DS_SET_DATA_PROFILE, "SYNC_PROFILE -> SET_DATA_PROFILE");
    p = ds_step(&c, true, 100);  CHECK(p == DS_SET_LTE_ATTACH, "SET_DATA_PROFILE -> SET_LTE_ATTACH");
    p = ds_step(&c, true, 100);  CHECK(p == DS_DEFINE_PDP, "SET_LTE_ATTACH -> DEFINE_PDP");
    p = ds_step(&c, true, 100);  CHECK(p == DS_ALWAYS_ON_PDN, "DEFINE_PDP -> ALWAYS_ON_PDN");
    p = ds_step(&c, true, 100);  CHECK(p == DS_PS_ATTACH, "ALWAYS_ON_PDN -> PS_ATTACH");
    p = ds_step(&c, true, 100);  CHECK(p == DS_DATA_CALL, "PS_ATTACH -> DATA_CALL");
    p = ds_step(&c, true, 100);  CHECK(p == DS_GET_PDP_LIST, "DATA_CALL -> GET_PDP_LIST");
    p = ds_step(&c, true, 100);  CHECK(p == DS_WAIT_IP, "GET_PDP_LIST -> WAIT_IP");
    p = ds_step(&c, true, 100);  CHECK(p == DS_ACTIVE, "WAIT_IP -> ACTIVE");

    CHECK(ds_terminal(&c), "ACTIVE is terminal");

    /* Rejection paths are terminal (a modem REJECT, not a timeout, must stop). */
    ds_reset(&c, "internet", 1);
    c.phase = DS_REJECTED;
    CHECK(ds_terminal(&c), "REJECTED is terminal");

    /* Timeout with bounded retry: never loops forever.
     * Each timeout re-arms the deadline; after `attempt` reaches 3 -> FAILED. */
    ds_reset(&c, "internet", 1);
    uint64_t now = 1000;
    c.step_deadline_ms = now + 5000;   /* first deadline */
    p = DS_SIM_CHECK;
    int steps = 0;
    while (p != DS_FAILED && steps < 100) {
        now += 6000;                    /* jump past each deadline */
        p = ds_step(&c, false, now);
        steps++;
    }
    CHECK(p == DS_FAILED, "bounded retries -> FAILED (got %d)", (int)p);
    CHECK(c.attempt <= 3, "attempt count bounded (got %u)", c.attempt);

    /* --- ds_feedback: strict success/rejection behaviour --- */
    ds_reset(&c, "internet", 1);
    /* success advances NET_REGIST_CHECK -> ENABLE_MOBILE_DATA */
    p = ds_feedback(&c, true, 1000);
    CHECK(p == DS_ENABLE_MOBILE_DATA, "ds_feedback(success) advances (got %d)", (int)p);
    /* rejection -> REJECTED (terminal for this attempt, bounded) */
    p = ds_feedback(&c, false, 1000);
    CHECK(p == DS_REJECTED, "ds_feedback(fail) -> REJECTED (got %d)", (int)p);
    CHECK(ds_terminal(&c), "REJECTED is terminal after feedback failure");

    /* after 3 rejections -> FAILED (bounded, no infinite loop) */
    ds_reset(&c, "internet", 1);
    c.attempt = 3;
    p = ds_feedback(&c, false, 1000);
    CHECK(p == DS_FAILED, "ds_feedback(fail) at attempt==3 -> FAILED (got %d)", (int)p);

    /* --- ds_gprs_call_connected helper --- */
    CHECK(ds_gprs_call_connected(1), "call state 1 is connected");
    CHECK(ds_gprs_call_connected(10), "call state 10 is connected");
    CHECK(ds_gprs_call_connected(11), "call state 11 is connected");
    CHECK(!ds_gprs_call_connected(3), "call state 3 (live-observed) is NOT connected");
    CHECK(!ds_gprs_call_connected(0), "call state 0 is NOT connected");

    printf("\n%s: %d failures\n", failures ? "RESULT=FAIL" : "RESULT=PASS", failures);
    return failures ? 1 : 0;
}
