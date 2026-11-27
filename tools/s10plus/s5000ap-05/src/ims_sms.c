/* SPDX-License-Identifier: GPL-2.0-only */
#include "ims_sms.h"
#include <string.h>
static bool field(const uint8_t **p,size_t *n,const uint8_t **v,size_t *len,size_t max)
{
    if (!*n) return false;
    *len=*(*p)++; --*n;
    if (*len>*n || *len>max) return false;
    *v=*p; *p+=*len; *n-=*len; return true;
}
bool ims_rp_decode(const uint8_t *p,size_t n,struct ims_rp *out)
{
    if (!p || !out || n<2 || (p[0]&0xf8)) return false;
    struct ims_rp r={.type=p[0],.reference=p[1]}; p+=2;n-=2;
    if (r.type==0 || r.type==1) {
        if (!field(&p,&n,&r.origin,&r.origin_len,12) ||
            !field(&p,&n,&r.destination,&r.destination_len,12) ||
            !field(&p,&n,&r.tpdu,&r.tpdu_len,255) || !r.tpdu_len) return false;
    } else if (r.type==2 || r.type==3 || r.type==4 || r.type==5) {
        if (r.type==4 || r.type==5) {
            const uint8_t *cause;size_t len;
            if (!field(&p,&n,&cause,&len,2) || !len) return false;
            r.cause=cause[0]&127;
        }
        if (n) {
            if (*p++!=0x41) return false;
            --n;
            if (!field(&p,&n,&r.tpdu,&r.tpdu_len,255) || !r.tpdu_len) return false;
        }
    } else return false;
    if (n) return false;
    *out=r;return true;
}
size_t ims_rp_submit(uint8_t *out,size_t cap,uint8_t ref,const uint8_t *smsc,
                     size_t slen,const uint8_t *tpdu,size_t tlen)
{
    if (!out || !smsc || slen<2 || slen>13 || smsc[0]!=slen-1 ||
        !tpdu || !tlen || tlen>255 || cap<4+slen+tlen) return 0;
    out[0]=0;out[1]=ref;out[2]=0; /* RP-DATA MS->network, empty OA */
    memcpy(out+3,smsc,slen);out[3+slen]=(uint8_t)tlen;
    memcpy(out+4+slen,tpdu,tlen);return 4+slen+tlen;
}
size_t ims_rp_reply(uint8_t out[5],uint8_t ref,uint8_t cause)
{
    out[0]=cause?4:2;out[1]=ref;
    if (!cause) return 2;
    out[2]=1;out[3]=cause;return 4;
}

bool ims_smsc_uri(const uint8_t *p,size_t n,char *out,size_t cap)
{
    if(!p || !out || n<3 || n>12 || p[0]!=n-1 || p[1]!=0x91 || cap<5) return false;
    memcpy(out,"tel:+",5);size_t k=5;
    for(size_t i=2;i<n;i++) for(unsigned half=0;half<2;half++) {
        unsigned d=(p[i]>>(4*half))&15;
        if(d==15 && i==n-1 && half==1) continue;
        if(d>9 || k+1>=cap || k>=20) return false;
        out[k++]=(char)('0'+d);
    }
    if(k==5 || k>=cap)return false;
    out[k]=0;return true;
}
