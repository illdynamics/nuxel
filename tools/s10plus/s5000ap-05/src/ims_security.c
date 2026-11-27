/* SPDX-License-Identifier: GPL-2.0-only */
#include "ims_security.h"
#include <string.h>
#include <stdlib.h>
#include <errno.h>
#include <limits.h>
#include <stdio.h>
static bool number(const char *s,uint32_t *n)
{
    if (!*s) return false;
    uint64_t v=0;
    for (;*s;s++) { if (*s<'0'||*s>'9') return false;v=v*10+(*s-'0');if(v>UINT32_MAX)return false; }
    *n=(uint32_t)v;return true;
}
bool ims_security_parse(const char *value,struct ims_security_offer *out)
{
    if (!value || !out || strlen(value)>=512) return false;
    char buf[512];strcpy(buf,value);char *save=NULL,*t=strtok_r(buf,";",&save);
    if (!t || strcmp(t,"ipsec-3gpp")) return false;
    struct ims_security_offer r={0};unsigned seen=0;
    while ((t=strtok_r(NULL,";",&save))) {
        while (*t==' ' || *t=='\t') t++;
        char *end=t+strlen(t);while(end>t && (end[-1]==' ' || end[-1]=='\t'))*--end=0;
        char *eq=strchr(t,'=');if(!eq)return false;*eq++=0;
        unsigned bit=0;uint32_t n;
        if(!strcmp(t,"alg")) {bit=1;r.sha1=!strcmp(eq,"hmac-sha-1-96");if(!r.sha1 && strcmp(eq,"hmac-md5-96"))return false;}
        else if(!strcmp(t,"ealg")) {bit=2;r.aes=!strcmp(eq,"aes-cbc");if(!r.aes && strcmp(eq,"null"))return false;}
        else if(!strcmp(t,"prot")) {bit=4;if(strcmp(eq,"esp"))return false;}
        else if(!strcmp(t,"mod")) {bit=8;if(strcmp(eq,"trans"))return false;}
        else if(!strcmp(t,"spi-c")) {bit=16;if(!number(eq,&n)||n<256)return false;r.spi_c=n;}
        else if(!strcmp(t,"spi-s")) {bit=32;if(!number(eq,&n)||n<256)return false;r.spi_s=n;}
        else if(!strcmp(t,"port-c")) {bit=64;if(!number(eq,&n)||!n||n>65535)return false;r.port_c=n;}
        else if(!strcmp(t,"port-s")) {bit=128;if(!number(eq,&n)||!n||n>65535)return false;r.port_s=n;}
        else if(strcmp(t,"q")) return false;
        if (seen&bit) return false;
        seen|=bit;
    }
    if ((seen&255)!=255 || r.spi_c==r.spi_s || r.port_c==r.port_s) return false;
    *out=r;return true;
}
bool ims_security_negotiate(struct ims_security *s,const char *client,const char *server)
{
    struct ims_security_offer local,remote;
    if (!s || !ims_security_parse(client,&local) || !ims_security_parse(server,&remote) ||
        local.aes!=remote.aes || local.sha1!=remote.sha1) return false;
    s->local=local;s->remote=remote;return true;
}
#ifdef __linux__
#include <sys/socket.h>
#include <unistd.h>
#include <arpa/inet.h>
#include <linux/netlink.h>
#include <linux/rtnetlink.h>
#include <linux/xfrm.h>
struct request { struct nlmsghdr h; uint8_t data[2048]; };
static bool attr(struct request *r,unsigned type,const void *v,size_t n)
{
    size_t off=NLMSG_ALIGN(r->h.nlmsg_len),len=RTA_LENGTH(n);
    if(off+RTA_ALIGN(len)>sizeof *r)return false;
    struct rtattr *a=(void *)((uint8_t *)r+off);a->rta_type=type;a->rta_len=len;
    memcpy(RTA_DATA(a),v,n);r->h.nlmsg_len=off+RTA_ALIGN(len);return true;
}
static bool exchange(struct request *r)
{
    int fd=socket(AF_NETLINK,SOCK_RAW|SOCK_CLOEXEC,NETLINK_XFRM);if(fd<0)return false;
    struct timeval timeout={.tv_sec=2};setsockopt(fd,SOL_SOCKET,SO_RCVTIMEO,&timeout,sizeof timeout);
    struct sockaddr_nl peer={.nl_family=AF_NETLINK};
    r->h.nlmsg_seq=1;r->h.nlmsg_flags|=NLM_F_REQUEST|NLM_F_ACK;
    bool ok=false;
    if(sendto(fd,r,r->h.nlmsg_len,0,(void *)&peer,sizeof peer)==(ssize_t)r->h.nlmsg_len) {
        uint8_t buf[4096];ssize_t n=recv(fd,buf,sizeof buf,0);
        for(struct nlmsghdr *h=(void *)buf;n>0 && NLMSG_OK(h,n);h=NLMSG_NEXT(h,n))
            if(h->nlmsg_type==NLMSG_ERROR && h->nlmsg_seq==1 && h->nlmsg_len>=NLMSG_LENGTH(sizeof(struct nlmsgerr))) {
                int err=((struct nlmsgerr *)NLMSG_DATA(h))->error;ok=err==0;errno=-err;break;
            }
    }
    close(fd);return ok;
}
struct flow { const uint8_t *src,*dst;uint16_t sport,dport;uint32_t spi;bool in; };
static struct flow flow(const struct ims_security *s,unsigned i)
{
    /* 33.203: client request -> peer server; server response -> peer client.
     * Receive SPIs are allocated by the destination, not the sender. */
    struct flow f={0};f.in=i<2;
    f.src=f.in?s->remote_ip:s->local_ip;f.dst=f.in?s->local_ip:s->remote_ip;
    switch(i) {
    case 0:f.sport=s->remote.port_s;f.dport=s->local.port_c;f.spi=s->local.spi_c;break;
    case 1:f.sport=s->remote.port_c;f.dport=s->local.port_s;f.spi=s->local.spi_s;break;
    case 2:f.sport=s->local.port_c;f.dport=s->remote.port_s;f.spi=s->remote.spi_s;break;
    default:f.sport=s->local.port_s;f.dport=s->remote.port_c;f.spi=s->remote.spi_c;break;
    }return f;
}
static void selector(struct xfrm_selector *sel,const struct ims_security *s,struct flow f)
{
    size_t n=s->family==AF_INET6?16:4;memset(sel,0,sizeof *sel);
    memcpy(&sel->saddr,f.src,n);memcpy(&sel->daddr,f.dst,n);sel->family=s->family;
    sel->prefixlen_s=sel->prefixlen_d=n*8;sel->proto=IPPROTO_UDP;
    sel->sport=htons(f.sport);sel->dport=htons(f.dport);sel->sport_mask=sel->dport_mask=0xffff;
}
static bool sa(struct ims_security *s,unsigned i,const uint8_t *ck,const uint8_t *ik,bool add)
{
    struct request r={0};struct flow f=flow(s,i);size_t n=s->family==AF_INET6?16:4;
    if(!add) {
        struct xfrm_usersa_id *v=(void *)r.data;r.h.nlmsg_type=XFRM_MSG_DELSA;r.h.nlmsg_len=NLMSG_LENGTH(sizeof *v);
        memcpy(&v->daddr,f.dst,n);v->spi=htonl(f.spi);v->family=s->family;v->proto=IPPROTO_ESP;
        return exchange(&r);
    }
    struct xfrm_usersa_info *v=(void *)r.data;r.h.nlmsg_type=XFRM_MSG_NEWSA;r.h.nlmsg_flags=NLM_F_CREATE|NLM_F_EXCL;r.h.nlmsg_len=NLMSG_LENGTH(sizeof *v);
    memcpy(&v->id.daddr,f.dst,n);memcpy(&v->saddr,f.src,n);v->id.spi=htonl(f.spi);v->id.proto=IPPROTO_ESP;
    v->family=s->family;v->mode=XFRM_MODE_TRANSPORT;v->reqid=s->reqid+i;v->replay_window=32;
    selector(&v->sel,s,f);v->lft.soft_byte_limit=v->lft.hard_byte_limit=XFRM_INF;
    v->lft.soft_packet_limit=v->lft.hard_packet_limit=XFRM_INF;v->lft.hard_add_expires_seconds=7200;
    struct { struct xfrm_algo_auth a;uint8_t key[20]; } auth={0};
    strcpy(auth.a.alg_name,s->remote.sha1?"hmac(sha1)":"hmac(md5)");
    auth.a.alg_key_len=s->remote.sha1?160:128;auth.a.alg_trunc_len=96;memcpy(auth.key,ik,16);
    struct { struct xfrm_algo a;uint8_t key[16]; } enc={0};
    strcpy(enc.a.alg_name,s->remote.aes?"cbc(aes)":"ecb(cipher_null)");enc.a.alg_key_len=s->remote.aes?128:0;
    if(s->remote.aes)memcpy(enc.key,ck,16);
    bool ok=attr(&r,XFRMA_ALG_AUTH_TRUNC,&auth,sizeof auth.a+auth.a.alg_key_len/8) &&
        attr(&r,XFRMA_ALG_CRYPT,&enc,sizeof enc.a+enc.a.alg_key_len/8) && exchange(&r);
    explicit_bzero(&auth,sizeof auth);explicit_bzero(&enc,sizeof enc);explicit_bzero(&r,sizeof r);return ok;
}
static bool policy(struct ims_security *s,unsigned i,bool add)
{
    struct request r={0};struct flow f=flow(s,i);
    if(!add) {
        struct xfrm_userpolicy_id *v=(void *)r.data;r.h.nlmsg_type=XFRM_MSG_DELPOLICY;r.h.nlmsg_len=NLMSG_LENGTH(sizeof *v);
        selector(&v->sel,s,f);v->dir=f.in?XFRM_POLICY_IN:XFRM_POLICY_OUT;return exchange(&r);
    }
    struct xfrm_userpolicy_info *v=(void *)r.data;r.h.nlmsg_type=XFRM_MSG_NEWPOLICY;r.h.nlmsg_flags=NLM_F_CREATE|NLM_F_EXCL;r.h.nlmsg_len=NLMSG_LENGTH(sizeof *v);
    selector(&v->sel,s,f);v->dir=f.in?XFRM_POLICY_IN:XFRM_POLICY_OUT;v->action=XFRM_POLICY_ALLOW;v->priority=100;
    v->lft.soft_byte_limit=v->lft.hard_byte_limit=XFRM_INF;v->lft.soft_packet_limit=v->lft.hard_packet_limit=XFRM_INF;
    v->lft.hard_add_expires_seconds=7200;
    struct xfrm_user_tmpl t={0};t.id.proto=IPPROTO_ESP;t.id.spi=htonl(f.spi);t.family=s->family;
    t.reqid=s->reqid+i;t.mode=XFRM_MODE_TRANSPORT;t.aalgos=t.ealgos=t.calgos=~0u;
    memcpy(&t.id.daddr,f.dst,s->family==AF_INET6?16:4);memcpy(&t.saddr,f.src,s->family==AF_INET6?16:4);
    return attr(&r,XFRMA_TMPL,&t,sizeof t) && exchange(&r);
}
void ims_security_clear(struct ims_security *s)
{
    if(!s)return;
    while(s->policies)policy(s,--s->policies,false);
    while(s->states)sa(s,--s->states,NULL,NULL,false);
    s->active=false;
}
bool ims_security_install(struct ims_security *s,const uint8_t ck[16],const uint8_t ik[16])
{
    if(!s || !ck || !ik || s->active || (s->family!=AF_INET && s->family!=AF_INET6))return false;
    for(unsigned i=0;i<4;i++) { if(!sa(s,i,ck,ik,true))goto fail;s->states++; }
    for(unsigned i=0;i<4;i++) { if(!policy(s,i,true))goto fail;s->policies++; }
    s->active=true;return true;
fail:ims_security_clear(s);return false;
}
#else
bool ims_security_install(struct ims_security *s,const uint8_t ck[16],const uint8_t ik[16])
{(void)s;(void)ck;(void)ik;return false;}
void ims_security_clear(struct ims_security *s) {if(s)s->active=false;}
#endif
