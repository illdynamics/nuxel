/* SPDX-License-Identifier: GPL-2.0-only */
#define _POSIX_C_SOURCE 200809L
#include "cellular_link.h"
#include <arpa/inet.h>
#include <errno.h>
#include <signal.h>
#include <stdio.h>
#include <string.h>
#include <sys/wait.h>
#include <unistd.h>

#define HELPER "/usr/libexec/nuxel/nuxel-cellular-link"

static bool start(struct cellular_link *link,char *const argv[],enum cellular_link_operation op,uint64_t now)
{
    if (link->pid) return false;
    pid_t pid=fork();
    if (pid<0) { link->result=errno; return false; }
    if (!pid) {
        sigset_t mask;
        sigemptyset(&mask);
        (void)sigprocmask(SIG_SETMASK,&mask,NULL);
        (void)setpgid(0,0);
        execv(HELPER,argv);
        _exit(127);
    }
    (void)setpgid(pid,pid);
    link->pid=pid;link->operation=op;link->deadline_ms=now+30000;
    link->timed_out=false;link->result=0;
    return true;
}

bool cellular_link_apply(struct cellular_link *link,const struct fmt_rx_ip *ip,uint64_t now)
{
    if (!link || !ip || ip->cid!=1 || (!ip->ipv4_valid && !ip->ipv6_valid) ||
        ip->mtu<1280 || ip->mtu>1500) return false;
    char v4[INET_ADDRSTRLEN]="-",v6[INET6_ADDRSTRLEN]="-";
    char dns4[2][INET_ADDRSTRLEN]={{'-',0},{'-',0}};
    char dns6[2][INET6_ADDRSTRLEN]={{'-',0},{'-',0}};
    char prefix[4],mtu[6];
    if (ip->ipv4_valid) {
        if (!inet_ntop(AF_INET,ip->ipv4,v4,sizeof v4)) return false;
        for (unsigned i=0;i<2;i++)
            if (!inet_ntop(AF_INET,ip->dns4[i],dns4[i],sizeof dns4[i])) return false;
    }
    if (ip->ipv6_valid) {
        if (!inet_ntop(AF_INET6,ip->ipv6,v6,sizeof v6)) return false;
        for (unsigned i=0;i<2;i++)
            if (!inet_ntop(AF_INET6,ip->dns6[i],dns6[i],sizeof dns6[i])) return false;
    }
    snprintf(prefix,sizeof prefix,"%u",ip->prefix4);
    snprintf(mtu,sizeof mtu,"%u",ip->mtu);
    char *args[]={HELPER,"apply","rmnet0","1",v4,prefix,v6,dns4[0],dns4[1],dns6[0],dns6[1],mtu,NULL};
    return start(link,args,CELL_LINK_APPLY,now);
}

bool cellular_link_down(struct cellular_link *link,uint64_t now)
{
    char *args[]={HELPER,"down",NULL};
    return link && start(link,args,CELL_LINK_DOWN,now);
}

bool cellular_link_check(struct cellular_link *link,uint64_t now)
{
    char *args[]={HELPER,"check",NULL};
    return link && start(link,args,CELL_LINK_CHECK,now);
}

bool cellular_link_poll(struct cellular_link *link,uint64_t now)
{
    if (!link || !link->pid) return false;
    if (now>=link->deadline_ms && !link->timed_out) {
        (void)kill(-link->pid,SIGKILL);
        link->timed_out=true;
    }
    int status=0;
    pid_t r=waitpid(link->pid,&status,WNOHANG);
    if (!r || (r<0 && errno==EINTR)) return false;
    link->result=link->timed_out ? ETIMEDOUT : r<0 ? errno :
                 WIFEXITED(status) ? WEXITSTATUS(status) : EINTR;
    link->configured=!link->result && link->operation!=CELL_LINK_DOWN;
    link->pid=0;
    return true;
}
