/* SPDX-License-Identifier: GPL-2.0-only */
#include "ims_sip.h"
#include "ims_sms.h"
#include <assert.h>
#include <stdio.h>
#include <string.h>
int main(void)
{
    char buf[2048];
    size_t n=ims_sip_register_build(buf,sizeof buf,
        "sip:user@ims.mnc008.mcc204.3gppnetwork.org",
        "user@ims.mnc008.mcc204.3gppnetwork.org",
        "2001:db8::1","2001:db8::2",5062,
        "alg=hmac-sha-1-96;ealg=aes-cbc;prot=esp;mod=trans;spi-c=4096;spi-s=4097;port-c=5062;port-s=5064");
    assert(n>0 && n<sizeof buf);
    /* R-URI must be the registrar/home domain, not the full IMPU and never a
     * doubled "sip:sip:" (a malformed R-URI the live P-CSCF answered 403). */
    assert(strstr(buf,"REGISTER sip:ims.mnc008.mcc204.3gppnetwork.org SIP/2.0")==buf);
    assert(strstr(buf,"sip:sip:")==NULL);
    assert(strstr(buf,"From: <sip:user@ims.mnc008.mcc204.3gppnetwork.org>"));
    assert(strstr(buf,"To: <sip:user@ims.mnc008.mcc204.3gppnetwork.org>"));
    /* Reachable IPv6 contact; no invented device identifier on missing input. */
    assert(strstr(buf,"Contact: <sip:user@[2001:db8::2]:5062;transport=udp>"));
    assert(!strstr(buf,"+sip.instance"));
    assert(strstr(buf,"urn:uuid:urn:gsma") == NULL);
    assert(strstr(buf,"+g.3gpp.smsip;expires=600"));
    /* RFC 3329 2.1 / TS 33.203 7.1: the Security-Client value MUST begin with
     * the ipsec-3gpp mechanism token. */
    assert(strstr(buf,"Security-Client: ipsec-3gpp;alg=hmac-sha-1-96"));
    /* Round 18 live: the KPN P-CSCF answers 400 Bad Request when the first
     * REGISTER asserts Require/Proxy-Require: sec-agree. The request must
     * therefore carry only the Security-Client OFFER (no Require headers). */
    assert(strstr(buf,"Require: sec-agree") == NULL);
    assert(strstr(buf,"Proxy-Require: sec-agree") == NULL);
    assert(strstr(buf,"P-Preferred-Identity: <sip:user@ims.mnc008.mcc204.3gppnetwork.org>"));
    assert(strstr(buf,"Route:")==NULL);
    assert(strstr(buf,"P-Access-Network-Info: 3GPP-E-UTRAN-FDD"));
    /* No real cell id -> the utran-cell-id-3gpp parameter MUST be omitted,
     * and the fabricated 00000000 placeholder must NEVER appear. */
    assert(strstr(buf,"utran-cell-id-3gpp") == NULL);
    assert(strstr(buf,"utran-cell-id-3gpp=00000000") == NULL);

    /* Security-first REGISTER (TS 33.203 7.1): REQUIRE sec-agree ONLY when a
     * complete ipsec-3gpp offer is present (some P-CSCFs 480 a plaintext
     * initial REGISTER). The default path above MUST stay Require-free. */
    {
        const char *off =
            "alg=hmac-sha-1-96;ealg=aes-cbc;prot=esp;mod=trans;"
            "spi-c=4096;spi-s=4097;port-c=5062;port-s=5064";
        size_t sn=ims_sip_register_build_secure(buf,sizeof buf,
            "sip:user@ims.mnc008.mcc204.3gppnetwork.org",
            "user@ims.mnc008.mcc204.3gppnetwork.org",
            "2001:db8::1","2001:db8::2",5062,off,NULL,NULL);
        assert(sn>0);
        assert(strstr(buf,"Require: sec-agree"));
        assert(strstr(buf,"Proxy-Require: sec-agree"));
        assert(strstr(buf,"Security-Client: ipsec-3gpp;alg=hmac-sha-1-96"));
        /* No security offer: NEVER assert sec-agree (would be invalid). */
        sn=ims_sip_register_build_secure(buf,sizeof buf,
            "sip:user@ims.mnc008.mcc204.3gppnetwork.org",
            "user@ims.mnc008.mcc204.3gppnetwork.org",
            "2001:db8::1","2001:db8::2",5062,NULL,NULL,NULL);
        assert(sn>0);
        assert(strstr(buf,"Require: sec-agree")==NULL);
        assert(strstr(buf,"Proxy-Require: sec-agree")==NULL);
    }

    /* A real ECI requires ex3 + serving PLMN; the value is the (MCC||MNC)
     * prefix joined with the 28-bit ECI (TS 24.229 7.2A.2), e.g. 20408 + ECI. */
    size_t cn=ims_sip_register_build_ex3(buf,sizeof buf,
        "sip:user@ims.mnc008.mcc204.3gppnetwork.org",
        "user@ims.mnc008.mcc204.3gppnetwork.org",
        "2001:db8::1","2001:db8::2",5062,NULL,NULL,"00a1b2c","20408");
    assert(cn>0 && !strstr(buf,"utran-cell-id-3gpp"));
    /* ex2 (no PLMN) leaves the value omitted even with a valid ECI: the
     * parameter cannot be emitted without the MCC||MNC part. */
    cn=ims_sip_register_build_ex2(buf,sizeof buf,
        "sip:user@ims.mnc008.mcc204.3gppnetwork.org",
        "user@ims.mnc008.mcc204.3gppnetwork.org",
        "2001:db8::1","2001:db8::2",5062,NULL,NULL,"00a1b2c");
    assert(cn>0 && strstr(buf,"utran-cell-id-3gpp") == NULL);
    /* ex3 with a malformed/non-hex ECI -> omitted, never echoed verbatim. */
    cn=ims_sip_register_build_ex3(buf,sizeof buf,
        "sip:user@ims.mnc008.mcc204.3gppnetwork.org",
        "user@ims.mnc008.mcc204.3gppnetwork.org",
        "2001:db8::1","2001:db8::2",5062,NULL,NULL,"zz!!","20408");
    assert(cn>0 && strstr(buf,"utran-cell-id-3gpp") == NULL);
    /* ex3 with a non-digit PLMN -> omitted (never splice a bad prefix). */
    cn=ims_sip_register_build_ex3(buf,sizeof buf,
        "sip:user@ims.mnc008.mcc204.3gppnetwork.org",
        "user@ims.mnc008.mcc204.3gppnetwork.org",
        "2001:db8::1","2001:db8::2",5062,NULL,NULL,"00a1b2c","2040x");
    assert(cn>0 && strstr(buf,"utran-cell-id-3gpp") == NULL);
    /* ex4: genuine TAC emitted with a valid PLMN (utran-tac 4 hex octets). */
    cn=ims_sip_register_build_ex4(buf,sizeof buf,
        "sip:user@ims.mnc008.mcc204.3gppnetwork.org",
        "user@ims.mnc008.mcc204.3gppnetwork.org",
        "2001:db8::1","2001:db8::2",5062,NULL,NULL,NULL,"20408",285);
    assert(cn>0 && !strstr(buf,"utran-tac") && !strstr(buf,"utran-cell-id"));
    /* ex4: ECI + TAC together. */
    cn=ims_sip_register_build_ex4(buf,sizeof buf,
        "sip:user@ims.mnc008.mcc204.3gppnetwork.org",
        "user@ims.mnc008.mcc204.3gppnetwork.org",
        "2001:db8::1","2001:db8::2",5062,NULL,NULL,"00a1b2c","20408",285);
    assert(cn>0 && strstr(buf,"utran-cell-id-3gpp=20408011d00a1b2c"));
    /* ex4: TAC without PLMN -> omitted (never a bare TAC). */
    cn=ims_sip_register_build_ex4(buf,sizeof buf,
        "sip:user@ims.mnc008.mcc204.3gppnetwork.org",
        "user@ims.mnc008.mcc204.3gppnetwork.org",
        "2001:db8::1","2001:db8::2",5062,NULL,NULL,NULL,NULL,285);
    assert(cn>0 && strstr(buf,"utran-tac") == NULL);
    /* ex4: out-of-range TAC (-1 / 70000) -> omitted. */
    cn=ims_sip_register_build_ex4(buf,sizeof buf,
        "sip:user@ims.mnc008.mcc204.3gppnetwork.org",
        "user@ims.mnc008.mcc204.3gppnetwork.org",
        "2001:db8::1","2001:db8::2",5062,NULL,NULL,NULL,"20408",70000);
    assert(cn>0 && strstr(buf,"utran-tac") == NULL);

    /* ex3 with no ECI -> parameter omitted (the fabricated 00000000 is never
     * injected by any code path). */
    cn=ims_sip_register_build_ex3(buf,sizeof buf,
        "sip:user@ims.mnc008.mcc204.3gppnetwork.org",
        "user@ims.mnc008.mcc204.3gppnetwork.org",
        "2001:db8::1","2001:db8::2",5062,NULL,NULL,NULL,"20408");
    assert(cn>0 && strstr(buf,"utran-cell-id-3gpp") == NULL);

    cn=ims_sip_register_build_ex(buf,sizeof buf,"user@example.test","user@example.test",
        "2001:db8::1","2001:db8::2",5062,NULL,
        "urn:uuid:12345678-1234-4321-8765-123456789abc");
    assert(cn && strstr(buf,"+sip.instance=\"<urn:uuid:12345678-1234-4321-8765-123456789abc>\""));

    /* _ex with a real 15-digit IMEI advertises a real device instance URN
     * (RFC 5626 <8>-<6>-<1> grouping); it is a device id, never a secret. */
    size_t en=ims_sip_register_build_ex(buf,sizeof buf,
        "sip:user@ims.mnc008.mcc204.3gppnetwork.org",
        "user@ims.mnc008.mcc204.3gppnetwork.org",
        "2001:db8::1","2001:db8::2",5062,NULL,
        "353234110123456");
    assert(en>0 && en<sizeof buf);
    assert(strstr(buf,"+sip.instance=\"<urn:gsma:imei:35323411-012345-0>\""));
    /* Invalid device identity is rejected. */
    en=ims_sip_register_build_ex(buf,sizeof buf,
        "sip:user@ims.mnc008.mcc204.3gppnetwork.org",
        "user@ims.mnc008.mcc204.3gppnetwork.org",
        "2001:db8::1","2001:db8::2",5062,NULL,"not-an-imei");
    assert(en==0);

    char realm[64],nonce[128],qop[16],alg[24],cnonce[16];
    const char ch[]="WWW-Authenticate: Digest realm=\"ims.mnc008.mcc204.3gppnetwork.org\", nonce=\"AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=\", algorithm=AKAv1-MD5, qop=\"auth\"";
    assert(ims_sip_challenge_parse(ch,sizeof ch-1,realm,nonce,qop,alg,cnonce));
    assert(!strcmp(alg,"AKAv1-MD5"));
    assert(!strcmp(qop,"auth"));
    assert(strlen(nonce)>0 && strlen(realm)>0);
    /* MD5-only must be rejected (IMS requires AKA). */
    const char md5ch[]="WWW-Authenticate: Digest realm=\"x\", nonce=\"y\", algorithm=MD5";
    assert(!ims_sip_challenge_parse(md5ch,sizeof md5ch-1,realm,nonce,qop,alg,cnonce));

    struct ims_sip_digest_params d={0};
    d.impu="user@ims.mnc008.mcc204.3gppnetwork.org";
    d.realm="ims.mnc008.mcc204.3gppnetwork.org";
    d.nonce="AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA="; d.cnonce="6e75786c"; d.method="REGISTER";
    d.uri="sip:ims.mnc008.mcc204.3gppnetwork.org";
    d.response="AQIDBA=="; /* base64 of RES [01 02 03 04] */
    size_t an=ims_sip_authorization_build(buf,sizeof buf,&d,true);
    assert(an>0 && strstr(buf,"Authorization: Digest "));
    assert(strstr(buf,"algorithm=AKAv1-MD5"));
    assert(strstr(buf,"username=\"user@ims.mnc008.mcc204.3gppnetwork.org\""));
    assert(strstr(buf,"response=\"b95aa38050f8ae91b06c884dcf23beef\""));

    /* SMS-over-IP MESSAGE with RP-DATA body. */
    uint8_t sc[]={3,0x91,0x21,0xf3}, tp[]={1,9,0}, rp[300];
    size_t rn=ims_rp_submit(rp,sizeof rp,77,sc,sizeof sc,tp,sizeof tp);
    assert(rn>0);
    size_t mn=ims_sip_message_build(buf,sizeof buf,
        "sip:user@ims.mnc008.mcc204.3gppnetwork.org",
        "sip:+12025550123@ims.mnc008.mcc204.3gppnetwork.org",
        "sip:user@ims.mnc008.mcc204.3gppnetwork.org",
        "2001:db8::1", 1, rp, rn);
    assert(mn>0 && strstr(buf,"Content-Type: application/vnd.3gpp.sms"));
    assert(strstr(buf,"MESSAGE sip:"));

    /* Standards-compliant MESSAGE: real Via (bracketed IPv6 + port), From
     * with tag, To without tag, P-Preferred-Identity (not P-Asserted), and a
     * Route built from a bare P-CSCF host as "sip:<host>;lr". A bare MSISDN
     * becomes a sip:<digits>@<home> R-URI. */
    mn=ims_sip_message_build_ex(buf,sizeof buf,
        "sip:user@ims.mnc008.mcc204.3gppnetwork.org",
        "ims.mnc008.mcc204.3gppnetwork.org",
        "+12025550123","2001:db8::2",5062,"2001:db8::1",7,rp,rn);
    assert(mn>0);
    assert(strstr(buf,"MESSAGE sip:+12025550123@ims.mnc008.mcc204.3gppnetwork.org SIP/2.0")==buf);
    assert(strstr(buf,"Via: SIP/2.0/UDP [2001:db8::2]:5062;branch="));
    assert(strstr(buf,"From: <sip:user@ims.mnc008.mcc204.3gppnetwork.org>;tag=nuxel7"));
    assert(strstr(buf,"To: <sip:+12025550123@ims.mnc008.mcc204.3gppnetwork.org>\r\n"));
    assert(strstr(buf,"Route: <sip:2001:db8::1;lr>"));
    assert(strstr(buf,"P-Preferred-Identity: <sip:user@ims.mnc008.mcc204.3gppnetwork.org>"));
    assert(strstr(buf,"P-Asserted-Identity") == NULL);
    /* A proper sip: route with ;lr is preserved; a sip: route without ;lr gets it. */
    mn=ims_sip_message_build_ex(buf,sizeof buf,
        "sip:user@d","d","sip:+31@d","2001:db8::2",5062,"sip:pcscf.example;lr",9,rp,rn);
    assert(mn>0 && strstr(buf,"Route: <sip:pcscf.example;lr>\r\n"));
    mn=ims_sip_message_build_ex(buf,sizeof buf,
        "sip:user@d","d","sip:+31@d","2001:db8::2",5062,"sip:pcscf.example",9,rp,rn);
    assert(mn>0 && strstr(buf,"Route: <sip:pcscf.example;lr>\r\n"));

    /* base64 round-trip of RAND||AUTN. */
    uint8_t randautn[32]; for (int i=0;i<32;i++) randautn[i]=(uint8_t)(i*7+1);
    char b64out[128]; size_t blen=ims_base64_encode(randautn,32,b64out,sizeof b64out);
    uint8_t dec[32]; size_t dlen=0;
    assert(blen>0 && ims_base64_decode(b64out,blen,dec,sizeof dec,&dlen));
    assert(dlen==32 && !memcmp(dec,randautn,32));

    /* Bounded SIP response parser: code, CSeq method, body length. */
    {
        struct ims_sip_response r;
        const char *ok=
            "SIP/2.0 200 OK\r\n"
            "Via: SIP/2.0/UDP [2001:db8::2]:5062;branch=z9hG4bKmsg7\r\n"
            "CSeq: 1 MESSAGE\r\n"
            "Content-Type: application/vnd.3gpp.sms\r\n"
            "Content-Length: 2\r\n\r\n\x02\x07";
        assert(ims_sip_response_parse(ok, strlen(ok), &r));
        assert(r.code==200 && !strcmp(r.cseq_method,"MESSAGE"));
        assert(r.have_content_length && r.body_len==2);
        const char *reg=
            "SIP/2.0 480 Temporarily Unavailable\r\n"
            "Via: SIP/2.0/UDP [2001:db8::2]:5062;branch=z9hG4bKnuxel\r\n"
            "CSeq: 1 register\r\n"
            "Retry-After: 180\r\n"
            "Content-Length: 0\r\n\r\n";
        assert(ims_sip_response_parse(reg, strlen(reg), &r));
        assert(r.code==480 && !strcmp(r.cseq_method,"REGISTER") && r.body_len==0);
        /* No Content-Length: body length is what follows the header terminator. */
        const char *no_cl="SIP/2.0 503 Service Unavailable\r\nCSeq: 9 MESSAGE\r\n\r\nabc";
        assert(ims_sip_response_parse(no_cl, strlen(no_cl), &r));
        assert(r.code==503 && r.body_len==3 && !r.have_content_length);
        /* Truncated / non-response inputs are rejected. */
        assert(!ims_sip_response_parse("SIP/2.0", 7, &r));
        assert(!ims_sip_response_parse("MESSAGE sip:x SIP/2.0\r\n", 22, &r));
        assert(!ims_sip_response_parse("", 0, &r));
    }

    /* Actual AP-side binary RP MESSAGE parser/response and correlation. */
    {
        const uint8_t rp[]={3,77};char wire[2048],response[2400];
        size_t wn=ims_sip_message_build_ex(wire,sizeof wire,"sip:sc@example.test",NULL,
            "sip:user@example.test","2001:db8::1",5064,"2001:db8::2",17,rp,sizeof rp);
        assert(wn);struct ims_sip_sms_request request;
        assert(ims_sip_sms_parse(wire,wn,&request));
        assert(request.body_len==2 && !memcmp(request.body,rp,2));
        size_t rn=ims_sip_sms_response(response,sizeof response,&request,200);
        assert(rn && ims_sip_same_transaction(wire,wn,response,rn));
        assert(!ims_sip_sms_parse(wire,wn-1,&request));
        assert(!ims_sip_same_transaction(wire,wn,"SIP/2.0 200 OK\r\n\r\n",18));
        const uint8_t sc[]={3,0x91,0x21,0xf3};char uri[32];
        assert(ims_smsc_uri(sc,sizeof sc,uri,sizeof uri) && !strcmp(uri,"tel:+123"));
        const uint8_t bad[]={3,0x91,0xf1,0x32};
        assert(!ims_smsc_uri(bad,sizeof bad,uri,sizeof uri));
    }
    puts("IMS SIP wire codec: PASS");
    return 0;
}
