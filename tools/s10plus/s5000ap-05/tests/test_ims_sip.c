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
    /* Contact MUST be a parseable SIP URI with an explicit transport, a
     * syntactically valid +sip.instance URN (RFC 5626) and the MMTEL ICSI
     * (TS 24.229 7.2A). It must NOT be the malformed bracketed-IPv6 form. */
    assert(strstr(buf,"Contact: <sip:user@ims.mnc008.mcc204.3gppnetwork.org;transport=udp>"));
    assert(strstr(buf,"Contact: <sip:user@[2001:db8::2]") == NULL);
    assert(strstr(buf,"+sip.instance=\"<urn:gsma:imei:"));
    assert(strstr(buf,"urn%3Aurn-7%3A3gpp-service.ims.icsi.mmtel"));
    assert(strstr(buf,"Security-Client: alg=")); /* RFC 3329 key=value token list */
    assert(strstr(buf,"Security-Client: alg=hmac-sha-1-96"));
    /* Round 18 live: the KPN P-CSCF answers 400 Bad Request when the first
     * REGISTER asserts Require/Proxy-Require: sec-agree. The request must
     * therefore carry only the Security-Client OFFER (no Require headers). */
    assert(strstr(buf,"Require: sec-agree") == NULL);
    assert(strstr(buf,"Proxy-Require: sec-agree") == NULL);
    assert(strstr(buf,"P-Preferred-Identity: <sip:user@ims.mnc008.mcc204.3gppnetwork.org>"));
    assert(strstr(buf,"Route:")==NULL);
    assert(strstr(buf,"P-Access-Network-Info: 3GPP-E-UTRAN-FDD"));

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
    d.nonce=nonce; d.cnonce="6e75786c"; d.method="REGISTER";
    d.uri="sip:ims.mnc008.mcc204.3gppnetwork.org";
    d.response="AQIDBA=="; /* base64 of RES [01 02 03 04] */
    size_t an=ims_sip_authorization_build(buf,sizeof buf,&d,true);
    assert(an>0 && strstr(buf,"Authorization: Digest "));
    assert(strstr(buf,"algorithm=AKAv1-MD5"));

    /* SMS-over-IP MESSAGE with RP-DATA body. */
    uint8_t sc[]={3,0x91,0x21,0xf3}, tp[]={1,9,0}, rp[300];
    size_t rn=ims_rp_submit(rp,sizeof rp,77,sc,sizeof sc,tp,sizeof tp);
    assert(rn>0);
    size_t mn=ims_sip_message_build(buf,sizeof buf,
        "sip:user@ims.mnc008.mcc204.3gppnetwork.org",
        "sip:+31649353067@ims.mnc008.mcc204.3gppnetwork.org",
        "sip:user@ims.mnc008.mcc204.3gppnetwork.org",
        "2001:db8::1", 1, rp, rn);
    assert(mn>0 && strstr(buf,"Content-Type: application/vnd.3gpp.sms"));
    assert(strstr(buf,"MESSAGE sip:"));

    /* base64 round-trip of RAND||AUTN. */
    uint8_t randautn[32]; for (int i=0;i<32;i++) randautn[i]=(uint8_t)(i*7+1);
    char b64out[128]; size_t blen=ims_base64_encode(randautn,32,b64out,sizeof b64out);
    uint8_t dec[32]; size_t dlen=0;
    assert(blen>0 && ims_base64_decode(b64out,blen,dec,sizeof dec,&dlen));
    assert(dlen==32 && !memcmp(dec,randautn,32));

    puts("IMS SIP wire codec: PASS");
    return 0;
}
