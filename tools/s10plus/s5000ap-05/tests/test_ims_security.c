/* SPDX-License-Identifier: GPL-2.0-only */
#include "ims_security.h"
#include <assert.h>
#include <stdio.h>
int main(void)
{
    struct ims_security_offer s;
    assert(ims_security_parse("ipsec-3gpp;alg=hmac-sha-1-96;ealg=aes-cbc;prot=esp;mod=trans;spi-c=4096;spi-s=4097;port-c=5062;port-s=5064",&s));
    assert(s.aes && s.sha1 && s.spi_s==4097);
    assert(!ims_security_parse("ipsec-3gpp;alg=none",&s));
    assert(!ims_security_parse("ipsec-3gpp;alg=hmac-md5-96;ealg=null;prot=esp;mod=trans;spi-c=4294967296;spi-s=4097;port-c=5062;port-s=5064",&s));
    assert(!ims_security_parse("ipsec-3gpp;alg=hmac-md5-96;ealg=null;prot=esp;mod=trans;spi-c=4096;spi-s=4096;port-c=5062;port-s=5064",&s));
    struct ims_security ctx={0};
    const char *client="ipsec-3gpp;alg=hmac-sha-1-96;ealg=aes-cbc;prot=esp;mod=trans;spi-c=4096;spi-s=4097;port-c=5062;port-s=5064";
    const char *server="ipsec-3gpp;alg=hmac-sha-1-96;ealg=aes-cbc;prot=esp;mod=trans;spi-c=8192;spi-s=8193;port-c=6062;port-s=6064";
    assert(ims_security_negotiate(&ctx,client,server));
    assert(ctx.local.spi_c==4096 && ctx.remote.spi_c==8192 && ctx.remote.port_s==6064);
    assert(!ims_security_negotiate(&ctx,client,"ipsec-3gpp;alg=hmac-md5-96;ealg=null;prot=esp;mod=trans;spi-c=8192;spi-s=8193;port-c=6062;port-s=6064"));
    puts("IMS security negotiation bounds: PASS");
}
