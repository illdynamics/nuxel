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

    CHECK(c.phase == DS_SIM_CHECK, "starts by querying SIM state");
    CHECK(strcmp((const char*)c.apn, "internet") == 0, "APN recorded");
    CHECK(c.profile_id == 1, "profile id recorded");
    CHECK(c.attach_flag == 1, "initial profile uses flag 1, never always-on flag 3");

    /* No ack -> stays put (no fabricated advance). */
    enum ds_phase p = ds_step(&c, false, 100);
    CHECK(p == DS_SIM_CHECK, "no ack -> stays SIM_CHECK");

    /* Authenticated ack advances each phase. The previous DEFINE rejection
     * was a protocol value error: CP 0x41219fe4 rejects dual-stack wire 4.
     * It did not establish that the whole DEFINE command is unsupported. */
    p = ds_step(&c, true, 100);  CHECK(p == DS_NET_REGIST_CHECK, "SIM_CHECK -> NET_REGIST_CHECK");
    p = ds_step(&c, true, 100);  CHECK(p == DS_SET_SERVICE_DOMAIN, "NET_REGIST_CHECK -> SET_SERVICE_DOMAIN");
    p = ds_step(&c, true, 100);  CHECK(p == DS_VERIFY_SERVICE_DOMAIN, "SET_SERVICE_DOMAIN needs actual readback");
    p = ds_step(&c, true, 100);  CHECK(p == DS_SET_PREFERRED_NET, "verified CS+PS -> SET_PREFERRED_NET");
    p = ds_step(&c, true, 100);  CHECK(p == DS_VERIFY_NET_MODE, "SET_PREFERRED_NET -> VERIFY_NET_MODE");
    p = ds_step(&c, true, 100);  CHECK(p == DS_ENABLE_MOBILE_DATA, "VERIFY_NET_MODE -> ENABLE_MOBILE_DATA");
    p = ds_step(&c, true, 100);  CHECK(p == DS_SET_DATA_PROFILE, "ENABLE_MOBILE_DATA -> SET_DATA_PROFILE (skip SYNC_PROFILE)");
    p = ds_step(&c, true, 100);  CHECK(p == DS_SET_LTE_ATTACH, "SET_DATA_PROFILE -> SET_LTE_ATTACH");
    /* Round-31 inserted the recovered MBIM MS LTE Attach Config (CID 0x0A)
     * phase between SET_LTE_ATTACH and ALWAYS_ON_PDN. It is gated OFF by
     * default (NUXEL_MBIM_ATTACH env), but the FSM phase exists so the
     * sequence must account for it regardless of the runtime gate. */
    p = ds_step(&c, true, 100);  CHECK(p == DS_MBIM_ATTACH_CONFIG, "SET_LTE_ATTACH -> MBIM_ATTACH_CONFIG");
    p = ds_step(&c, true, 100);  CHECK(p == DS_DEFINE_PDP, "MBIM_ATTACH_CONFIG -> DEFINE_PDP");
    p = ds_step(&c, true, 100);  CHECK(p == DS_ALWAYS_ON_PDN, "DEFINE_PDP -> ALWAYS_ON_PDN");
    p = ds_step(&c, true, 100);  CHECK(p == DS_PS_REGIST_CHECK, "query real registration before PS attach");
    c.net_regist_valid = true; c.last_ps_reg_state = 0;
    p = ds_step(&c, true, 100);  CHECK(p == DS_PS_ATTACH, "unregistered -> PS_ATTACH");
    p = ds_step(&c, true, 100);  CHECK(p == DS_PS_REGIST_VERIFY, "PS_ATTACH needs actual registration");
    p = ds_step(&c, true, 100);  CHECK(p == DS_DATA_CALL, "PS_REGIST_VERIFY -> DATA_CALL");
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
    /* success advances SIM_CHECK -> NET_REGIST_CHECK */
    p = ds_feedback(&c, true, 1000);
    CHECK(p == DS_NET_REGIST_CHECK, "ds_feedback(success) advances (got %d)", (int)p);
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

    /* Initial APN updates must wait for detached state, and an intermediate
     * failure must restore PS before reporting the original rejection. */
    ds_reset(&c, "internet", 1);
    c.reattach_for_apn = true; c.phase = DS_SET_DATA_PROFILE;
    CHECK(ds_step(&c, true, 1000) == DS_IA_STATE_QUERY, "IA update queries packet state first");
    CHECK(ds_step(&c, true, 1000) == DS_IA_STATE_QUERY, "missing state cannot authorize detach");
    c.net_regist_valid = true; c.attached = false;
    CHECK(ds_step(&c, true, 1000) == DS_SET_LTE_ATTACH, "already detached does not send a rejected detach");
    c.phase = DS_IA_STATE_QUERY; c.attached = true;
    CHECK(ds_step(&c, true, 1000) == DS_PS_DETACH, "attached IA update requests detach");
    c.needs_ps_restore = true; /* set only after the transport writes detach */
    CHECK(ds_step(&c, true, 1000) == DS_PS_DETACHED_VERIFY, "detach ACK needs state verification");
    CHECK(ds_step(&c, false, 1100) == DS_PS_DETACHED_VERIFY, "no state proof cannot change profile");
    CHECK(ds_step(&c, true, 1200) == DS_SET_LTE_ATTACH, "detached -> initial profile");
    c.last_gen_result = 4;
    c.gen_result_valid = true;
    CHECK(ds_feedback(&c, false, 1300) == DS_RECOVER_PS_ATTACH, "profile rejection restores PS");
    CHECK(c.failure_phase == DS_SET_LTE_ATTACH && c.failure_result == 4, "preserves original failure");
    CHECK(c.failure_result_valid, "rejected command result is valid");
    CHECK(ds_step(&c, true, 1400) == DS_RECOVER_PS_REGIST && c.needs_ps_restore, "recovery ACK still needs registration");
    CHECK(ds_step(&c, true, 1600) == DS_REJECTED && !c.needs_ps_restore, "registered recovery reports rejection, never ACTIVE");
    ds_reset(&c, "internet", 1);
    c.phase = DS_PS_DETACHED_VERIFY; c.needs_ps_restore = true;
    c.attempt = 3; c.step_deadline_ms = 1000;
    CHECK(ds_step(&c, false, 1100) == DS_RECOVER_PS_ATTACH, "detach timeout restores PS");
    CHECK(ds_feedback(&c, false, 1200) == DS_REJECTED && c.needs_ps_restore, "failed recovery stays explicit");

    /* Live EFUJ2: PS GET remains 00 00 while LTE is registered and CID1
     * is active. A redundant attach is rejected. Registration must decide
     * whether to request attachment; the control flag is not a network enum. */
    ds_reset(&c, "internet", 1); c.phase = DS_PS_REGIST_CHECK;
    c.needs_ps_restore = true;
    c.ps_control_valid = true; c.ps_control_state = 0;
    CHECK(ds_step(&c, true, 100) == DS_PS_REGIST_CHECK, "PS control reply alone proves no registration");
    c.net_regist_valid = true; c.last_ps_reg_state = 1;
    CHECK(ds_step(&c, true, 101) == DS_DATA_CALL, "registered default context avoids redundant PS attach");
    c.phase = DS_PS_REGIST_CHECK; c.last_ps_reg_state = 0; c.ps_control_state = 1;
    CHECK(!c.needs_ps_restore, "actual registration clears pending PS restoration");
    CHECK(ds_step(&c, true, 102) == DS_PS_ATTACH, "control flag 1 cannot fabricate network registration");

    printf("\n%s: %d failures\n", failures ? "RESULT=FAIL" : "RESULT=PASS", failures);
    return failures ? 1 : 0;
}
