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
    puts("IMS security negotiation bounds: PASS");
}
