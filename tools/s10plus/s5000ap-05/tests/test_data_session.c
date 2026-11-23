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

    CHECK(c.phase == DS_SIM_CHECK, "starts at SIM_CHECK");
    CHECK(strcmp((const char*)c.apn, "internet") == 0, "APN recorded");
    CHECK(c.profile_id == 1, "profile id recorded");

    /* No ack -> stays put (no fabricated advance). */
    enum ds_phase p = ds_step(&c, false, 100);
    CHECK(p == DS_SIM_CHECK, "no ack -> stays SIM_CHECK");

    /* Authenticated ack advances each phase in order. */
    p = ds_step(&c, true, 100);  CHECK(p == DS_ENABLE_MOBILE_DATA, "SIM_CHECK -> ENABLE_MOBILE_DATA");
    p = ds_step(&c, true, 100);  CHECK(p == DS_DEFINE_PDP, "-> DEFINE_PDP");
    p = ds_step(&c, true, 100);  CHECK(p == DS_PS_ATTACH, "-> PS_ATTACH");
    p = ds_step(&c, true, 100);  CHECK(p == DS_DATA_CALL, "-> DATA_CALL");
    p = ds_step(&c, true, 100);  CHECK(p == DS_WAIT_IP, "-> WAIT_IP");
    p = ds_step(&c, true, 100);  CHECK(p == DS_ACTIVE, "-> ACTIVE");

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

    printf("\n%s: %d failures\n", failures ? "RESULT=FAIL" : "RESULT=PASS", failures);
    return failures ? 1 : 0;
}
