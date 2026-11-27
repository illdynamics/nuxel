/* SPDX-License-Identifier: GPL-2.0-only
 * Linux-only physical kernel test. Run as root; all XFRM changes are confined
 * to a new network namespace. Synthetic documentation addresses and keys. */
#define _GNU_SOURCE
#include "ims_security.h"
#include <assert.h>
#include <arpa/inet.h>
#include <sched.h>
#include <stdio.h>
#include <string.h>
int main(void)
{
    if(unshare(CLONE_NEWNET)) {perror("isolated network namespace");return 77;}
    struct ims_security s={.family=AF_INET6,.reqid=0x525000};
    const char *local="ipsec-3gpp;alg=hmac-sha-1-96;ealg=aes-cbc;prot=esp;mod=trans;spi-c=4096;spi-s=4097;port-c=5062;port-s=5064";
    const char *remote="ipsec-3gpp;alg=hmac-sha-1-96;ealg=aes-cbc;prot=esp;mod=trans;spi-c=8192;spi-s=8193;port-c=6062;port-s=6064";
    assert(ims_security_negotiate(&s,local,remote));
    assert(inet_pton(AF_INET6,"2001:db8::1",s.local_ip)==1);
    assert(inet_pton(AF_INET6,"2001:db8::2",s.remote_ip)==1);
    uint8_t ck[16]={1},ik[16]={2};
    assert(ims_security_install(&s,ck,ik));
    assert(s.active && s.states==4 && s.policies==4);
    assert(!ims_security_install(&s,ck,ik));
    struct ims_security duplicate=s;duplicate.active=false;duplicate.states=duplicate.policies=0;
    assert(!ims_security_install(&duplicate,ck,ik));
    assert(!duplicate.active && !duplicate.states && !duplicate.policies);
    ims_security_clear(&s);assert(!s.active && !s.states && !s.policies);
    assert(ims_security_install(&s,ck,ik));ims_security_clear(&s);
    memset(ck,0,sizeof ck);memset(ik,0,sizeof ik);
    puts("isolated kernel: four negotiated SAs/policies, duplicate failure, cleanup/reinstall PASS");
    return 0;
}
