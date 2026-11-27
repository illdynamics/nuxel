/* SPDX-License-Identifier: GPL-2.0-only */
#include "ims_sip_tr.h"
#include <assert.h>
#include <stdio.h>
#include <string.h>

/* Synthetic loopback peer: captures the last datagram sent and feeds a canned
 * reply. */
static unsigned char captured[IMS_SIP_TR_MAX_MSG];
static size_t captured_len;
static bool send_called;

static bool fake_send(const void *msg, size_t len, void *user)
{
    (void)user;
    if (len > sizeof captured) return false;
    memcpy(captured, msg, len);
    captured_len = len;
    send_called = true;
    return true;
}

static void reset_capture(void) { captured_len = 0; send_called = false; memset(captured, 0, sizeof captured); }

int main(void)
{
    struct ims_sip_tr_cfg cfg = {
        .impu = "sip:user@ims.mnc008.mcc204.3gppnetwork.org",
        .impi = "user@ims.mnc008.mcc204.3gppnetwork.org",
        .pcscf = "2001:db8::1",
        .local_ip = "2001:db8::2",
        .port = 5062,
        .pcscf_port = 5060,
        .sec_offer = "ipsec-3gpp;alg=hmac-sha-1-96;ealg=aes-cbc;prot=esp;mod=trans;spi-c=4096;spi-s=4097;port-c=5062;port-s=5064",
    };
    struct ims_sip_tr_io io = { .send = fake_send, .recv = NULL };
    struct ims_sip_tr t;
    assert(ims_sip_tr_open(&t, &cfg, &io, NULL, NULL));
    assert(t.phase == IMS_SIP_TR_IDLE);
    assert(!ims_sip_tr_registered(&t));

    /* 1. start -> initial REGISTER (no Authorization). */
    reset_capture();
    assert(ims_sip_tr_start(&t));
    assert(t.phase == IMS_SIP_TR_REGISTER_SENT);
    assert(send_called && captured_len > 0);
    assert(memmem(captured, captured_len, "REGISTER ", 9) == captured);
    assert(memmem(captured, captured_len, "Authorization:", 14) == NULL);

    /* 2. feed 401 AKAv1-MD5 -> CHALLENGED, realm/nonce recorded. */
    static const char ch401[] =
        "SIP/2.0 401 Unauthorized\r\n"
        "WWW-Authenticate: Digest realm=\"ims.mnc008.mcc204.3gppnetwork.org\", "
        "nonce=\"AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=\", "
        "algorithm=AKAv1-MD5, qop=\"auth\"\r\n"
        "Content-Length: 0\r\n\r\n";
    ims_sip_tr_feed(&t, (const uint8_t *)ch401, sizeof ch401 - 1);
    assert(t.phase == IMS_SIP_TR_CHALLENGED);
    assert(strlen(t.realm) > 0 && strlen(t.nonce) > 0);

    /* 3. supply RES -> base64 stored; on tick -> authenticated REGISTER. */
    unsigned char res[4] = {1,2,3,4};
    assert(ims_sip_tr_auth(&t, res, sizeof res));
    assert(t.res_b64[0] != 0);
    reset_capture();
    assert(ims_sip_tr_tick(&t, 1000, true) == IMS_SIP_TR_AUTH_SENT);
    assert(send_called);
    assert(memmem(captured, captured_len, "Authorization: Digest ", 22) != NULL);
    assert(memmem(captured, captured_len, "algorithm=AKAv1-MD5", 18) != NULL);

    /* 4. feed 200 OK -> REGISTERED. */
    static const char ok200[] =
        "SIP/2.0 200 OK\r\n"
        "Contact: <sip:user@[2001:db8::2]:5062>;expires=600000\r\n"
        "Content-Length: 0\r\n\r\n";
    ims_sip_tr_feed(&t, (const uint8_t *)ok200, sizeof ok200 - 1);
    assert(t.phase == IMS_SIP_TR_REGISTERED);
    assert(ims_sip_tr_registered(&t));

    /* 5. submit an SMS-over-IP MESSAGE (RP-DATA body). */
    unsigned char tpdu[] = {0x01, 0x09, 0x00}; /* SMS-SUBMIT-ish minimal TPDU */
    reset_capture();
    assert(ims_sip_tr_submit_sms(&t, "sip:+31649353067@ims.mnc008.mcc204.3gppnetwork.org", tpdu, sizeof tpdu, 77));
    assert(send_called);
    assert(memmem(captured, captured_len, "MESSAGE sip:", 11) != NULL);
    assert(memmem(captured, captured_len, "Content-Type: application/vnd.3gpp.sms", 38) != NULL);

    /* 6. deregister. */
    reset_capture();
    assert(ims_sip_tr_deregister(&t));
    assert(t.phase == IMS_SIP_TR_DEREG_SENT);

    /* 7. 480 + Retry-After enters Retry-Wait, then a fresh REGISTER is sent
     * only after the network interval elapses (not an instant fail/retry). */
    {
        struct ims_sip_tr t2;
        struct ims_sip_tr_cfg cfg = {
            .impu="sip:u@ims.mnc008.mcc204.3gppnetwork.org",
            .impi="u@ims.mnc008.mcc204.3gppnetwork.org",
            .pcscf="2001:db8::1", .local_ip="2001:db8::2",
            .port=5062, .pcscf_port=5060, .sec_offer=NULL };
        const struct ims_sip_tr_io io = { .send=fake_send, .recv=NULL };
        assert(ims_sip_tr_open(&t2, &cfg, &io, NULL, NULL));
        assert(ims_sip_tr_start(&t2));
        static const char e480[] =
            "SIP/2.0 480 Temporarily Unavailable\r\n"
            "Via: SIP/2.0/UDP [2001:db8::2]:5062;branch=z9hG4bKx\r\n"
            "Retry-After: 5\r\nContent-Length: 0\r\n\r\n";
        ims_sip_tr_feed(&t2, (const uint8_t *)e480, sizeof e480 - 1);
        assert(t2.phase == IMS_SIP_TR_RETRY_WAIT);
        assert(t2.retry_after_s == 5);
        reset_capture();
        /* Before the interval: no send, still waiting. */
        assert(ims_sip_tr_tick(&t2, 1000, true) == IMS_SIP_TR_RETRY_WAIT);
        assert(!send_called);
        /* After the interval: a fresh unauthenticated REGISTER is sent. */
        assert(ims_sip_tr_tick(&t2, 1000 + 5001, true) == IMS_SIP_TR_REGISTER_SENT);
        assert(send_called);
        { char cb[sizeof captured + 1]; memcpy(cb, captured, captured_len); cb[captured_len] = 0;
          assert(strstr(cb, "REGISTER sip:") != NULL); }
        ims_sip_tr_close(&t2);
    }


    /* 8. Re-opening the transport (socket/bearer change) must NOT bypass a
     * registrar Retry-After: the absolute hold is carried into the new FSM. */
    {
        struct ims_sip_tr a, b;
        struct ims_sip_tr_cfg cfg = {
            .impu="sip:u@ims.mnc008.mcc204.3gppnetwork.org",
            .impi="u@ims.mnc008.mcc204.3gppnetwork.org",
            .pcscf="2001:db8::1", .local_ip="2001:db8::2",
            .port=5062, .pcscf_port=5060, .sec_offer=NULL };
        const struct ims_sip_tr_io io = { .send=fake_send, .recv=NULL };
        assert(ims_sip_tr_open(&a, &cfg, &io, NULL, NULL));
        assert(ims_sip_tr_start(&a));
        static const char e480[] =
            "SIP/2.0 480 Temporarily Unavailable\r\n"
            "Via: SIP/2.0/UDP [2001:db8::2]:5062;branch=z9hG4bKx\r\n"
            "Retry-After: 30\r\nContent-Length: 0\r\n\r\n";
        ims_sip_tr_feed(&a, (const uint8_t *)e480, sizeof e480 - 1);
        assert(a.phase == IMS_SIP_TR_RETRY_WAIT);
        assert(ims_sip_tr_tick(&a, 1000, true) == IMS_SIP_TR_RETRY_WAIT);
        assert(a.next_action_ms == 1000 + 30000);
        /* Re-open into a fresh FSM, carrying the hold. */
        assert(ims_sip_tr_open(&b, &cfg, &io, NULL, &a));
        assert(b.next_action_ms == 1000 + 30000);
        assert(b.phase == IMS_SIP_TR_RETRY_WAIT);
        /* Before the hold elapses: start refuses; tick sends nothing. */
        reset_capture();
        assert(!ims_sip_tr_start(&b));
        assert(ims_sip_tr_tick(&b, 1000 + 29000, true) == IMS_SIP_TR_RETRY_WAIT);
        assert(!send_called);
        /* After it elapses: a fresh REGISTER is permitted again. */
        assert(ims_sip_tr_tick(&b, 1000 + 30001, true) == IMS_SIP_TR_REGISTER_SENT);
        assert(send_called);
        ims_sip_tr_close(&b);
        ims_sip_tr_close(&a);
    }

    /* 9. RFC 3329: a 401 carrying Security-Server must be captured and the
     * authenticated REGISTER must echo it in Security-Verify so the P-CSCF
     * can confirm the negotiated IPsec SAs. */
    {
        struct ims_sip_tr a;
        struct ims_sip_tr_cfg cfg = {
            .impu="sip:u@ims.mnc008.mcc204.3gppnetwork.org",
            .impi="u@ims.mnc008.mcc204.3gppnetwork.org",
            .pcscf="2001:db8::1", .local_ip="2001:db8::2",
            .port=5062, .pcscf_port=5060,
            .sec_offer="ipsec-3gpp;alg=hmac-sha-1-96;ealg=aes-cbc;prot=esp;mod=trans;spi-c=4096;spi-s=4097;port-c=5062;port-s=5064" };
        const struct ims_sip_tr_io io = { .send=fake_send, .recv=NULL };
        assert(ims_sip_tr_open(&a, &cfg, &io, NULL, NULL));
        assert(ims_sip_tr_start(&a));
        static const char c401[] =
            "SIP/2.0 401 Unauthorized\r\n"
            "WWW-Authenticate: Digest realm=\"ims.mnc008.mcc204.3gppnetwork.org\", "
            "nonce=\"AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=\", "
            "algorithm=AKAv1-MD5, qop=\"auth\"\r\n"
            "Security-Server: ipsec-3gpp;alg=hmac-sha-1-96;ealg=aes-cbc;prot=esp;"
            "mod=trans;spi-c=5000;spi-s=5001;port-c=5064;port-s=5062\r\n"
            "Content-Length: 0\r\n\r\n";
        ims_sip_tr_feed(&a, (const uint8_t *)c401, sizeof c401 - 1);
        assert(a.phase == IMS_SIP_TR_CHALLENGED);
        char off[320], lip[64], rip[64]; int fam=0;
        assert(ims_sip_tr_security_params(&a, off, sizeof off, lip, sizeof lip,
                                          rip, sizeof rip, &fam));
        assert(strstr(off, "spi-c=5000") && strstr(off, "ipsec-3gpp"));
        assert(fam == 10 /*AF_INET6*/);
        unsigned char res[8] = {9,8,7,6,5,4,3,2};
        assert(ims_sip_tr_auth(&a, res, sizeof res));
        reset_capture();
        assert(ims_sip_tr_tick(&a, 1000, true) == IMS_SIP_TR_AUTH_SENT);
        assert(send_called);
        assert(memmem(captured, captured_len, "Security-Verify: ipsec-3gpp",
                      strlen("Security-Verify: ipsec-3gpp")) != NULL);
        assert(memmem(captured, captured_len, "spi-c=5000", 10) != NULL);
        ims_sip_tr_close(&a);
    }

    /* ---- SMS-over-IMS response classification (TS 24.341) ----
     * Only a response whose CSeq method is MESSAGE is an SMS transaction
     * result; a REGISTER reply (incl. REGISTER 480) is NEVER an SMS result. */
    {
        int code=0;
        const char *msg200="SIP/2.0 200 OK\r\nCSeq: 1 MESSAGE\r\nContent-Length: 0\r\n\r\n";
        assert(ims_sip_tr_classify((const uint8_t *)msg200, strlen(msg200), &code)
               == IMS_SIP_TR_MSG_ACCEPTED && code==200);
        const char *msg503="SIP/2.0 503 Service Unavailable\r\nCSeq: 1 MESSAGE\r\n\r\n";
        assert(ims_sip_tr_classify((const uint8_t *)msg503, strlen(msg503), &code)
               == IMS_SIP_TR_MSG_REJECTED && code==503);
        const char *msg100="SIP/2.0 100 Trying\r\nCSeq: 1 MESSAGE\r\n\r\n";
        assert(ims_sip_tr_classify((const uint8_t *)msg100, strlen(msg100), &code)
               == IMS_SIP_TR_MSG_PROVISIONAL && code==100);
        const char *reg480="SIP/2.0 480 Temporarily Unavailable\r\nCSeq: 1 REGISTER\r\n\r\n";
        assert(ims_sip_tr_classify((const uint8_t *)reg480, strlen(reg480), &code)
               == IMS_SIP_TR_MSG_NONE);
        const char *noreq="MESSAGE sip:x@y SIP/2.0\r\nCSeq: 1 MESSAGE\r\n\r\n";
        assert(ims_sip_tr_classify((const uint8_t *)noreq, strlen(noreq), &code)
               == IMS_SIP_TR_MSG_NONE);
    }

    /* Security-first profile: the FIRST REGISTER asserts sec-agree and the FSM
     * uses SECURE_REGISTER_SENT; a 401 with a complete ipsec-3gpp
     * Security-Server still transitions to CHALLENGED (AKA path intact). */
    {
        struct ims_sip_tr_cfg sc = {
            .impu = "sip:user@ims.mnc008.mcc204.3gppnetwork.org",
            .impi = "user@ims.mnc008.mcc204.3gppnetwork.org",
            .pcscf = "2001:db8::1",
            .local_ip = "2001:db8::2",
            .port = 5062, .pcscf_port = 5060,
            .sec_offer = "alg=hmac-sha-1-96;ealg=aes-cbc;prot=esp;mod=trans;"
                         "spi-c=4096;spi-s=4097;port-c=5062;port-s=5064",
            .security_first = true,
        };
        struct ims_sip_tr u;
        assert(ims_sip_tr_open(&u, &sc, &io, NULL, NULL));
        reset_capture();
        assert(ims_sip_tr_start(&u));
        assert(u.phase == IMS_SIP_TR_SECURE_REGISTER_SENT);
        assert(strstr((const char *)captured, "Require: sec-agree") != NULL);
        assert(strstr((const char *)captured, "Proxy-Require: sec-agree") != NULL);
        assert(strstr((const char *)captured, "Security-Client: ipsec-3gpp") != NULL);
        static const char sc401[] =
            "SIP/2.0 401 Unauthorized\r\n"
            "WWW-Authenticate: Digest realm=\"ims.mnc008.mcc204.3gppnetwork.org\", "
            "nonce=\"AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=\", "
            "algorithm=AKAv1-MD5, qop=\"auth\"\r\n"
            "Security-Server: ipsec-3gpp;alg=hmac-sha-1-96;ealg=aes-cbc;prot=esp;"
            "mod=trans;spi-c=4097;spi-s=4096;port-c=5064;port-s=5062\r\n"
            "Content-Length: 0\r\n\r\n";
        ims_sip_tr_feed(&u, (const uint8_t *)sc401, sizeof sc401 - 1);
        assert(u.phase == IMS_SIP_TR_CHALLENGED);
        ims_sip_tr_close(&u);
    }

    ims_sip_tr_close(&t);
    puts("IMS SIP transport FSM: PASS");
    return 0;
}
