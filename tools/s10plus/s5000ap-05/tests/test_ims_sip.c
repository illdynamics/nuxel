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
        "ipsec-3gpp;alg=hmac-sha-1-96;ealg=aes-cbc;prot=esp;mod=trans;spi-c=4096;spi-s=4097;port-c=5062;port-s=5064");
    assert(n>0 && n<sizeof buf);
    assert(strstr(buf,"REGISTER sip:")==buf);
    assert(strstr(buf,"Security-Client: ipsec-3gpp"));
    assert(strstr(buf,"Route: <sip:2001:db8::1;lr>"));
    assert(strstr(buf,"P-Access-Network-Info: 3GPP-E-UTRAN-TDD"));

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
