/* SPDX-License-Identifier: GPL-2.0-only */
#include "fmt_call.h"
#include <string.h>

bool fmt_call_dial(struct fmt_tx_frame *f,const char *number)
{
    if (!number) return false;
    size_t n=strnlen(number,FMT_CALL_NUMBER);
    bool international=number[0]=='+';const char *digits=number+(international ? 1 : 0);
    if (!n || n>=FMT_CALL_NUMBER || !*digits || strspn(digits,"0123456789")!=strlen(digits)) return false;
    uint8_t *p=fmt_tx_begin(f,2,1,1,92);if(!p)return false;
    memset(p,0,92);
    p[0]=0;p[1]=1; /* normal voice: u16 LE 0x0100, ConvertCallTypeToIpc(1) */
    p[2]=0; /* default CLIR */
    p[3]=(uint8_t)n;p[4]=international ? 0x11 : 0x21;
    memcpy(p+5,number,n); /* 82 bytes plus reserved padding; final flags zero */
    return true;
}
bool fmt_call_answer(struct fmt_tx_frame *f) { return fmt_tx_raw(f,2,4,1,NULL,0); }
bool fmt_call_release(struct fmt_tx_frame *f) { return fmt_tx_raw(f,2,3,1,NULL,0); }
bool fmt_call_get_list(struct fmt_tx_frame *f) { return fmt_tx_raw(f,2,6,2,NULL,0); }
bool fmt_call_voice_registration(struct fmt_tx_frame *f)
{ const uint8_t p[]={255,2};return fmt_tx_raw(f,8,5,2,p,sizeof p); }

const char *fmt_call_state_name(uint8_t state)
{
    switch(state) {
    case 1:return "active";case 2:return "held";case 3:return "dialing";
    case 4:return "alerting";case 5:return "incoming";case 6:return "waiting";
    default:return "unknown";
    }
}
bool fmt_call_list(const uint8_t *p,size_t n,struct fmt_call_list *out)
{
    if (!p || !out || !n || p[0]>FMT_CALL_MAX) return false;
    struct fmt_call_list v={.count=p[0]};size_t pos=1;
    for(size_t i=0;i<v.count;i++) {
        if(n-pos<8)return false;
        const uint8_t *q=p+pos;size_t digits=q[6];struct fmt_call *c=&v.calls[i];
        if(digits>=FMT_CALL_NUMBER || digits>n-pos-8 || q[3]<1 || q[3]>2 || q[4]<1 || q[4]>6 || q[5]>1)return false;
        c->type=(uint16_t)(q[0]|((unsigned)q[1]<<8));
        /* Normal CS voice layout. IMS/regional optional tails require a
         * separate verified schema and are not guessed from packet length. */
        if(c->type!=0x100)return false;
        c->id=q[2];c->direction=q[3];c->state=q[4];c->multiparty=q[5];
        for(size_t j=0;j<digits;j++)if((q[8+j]<'0' || q[8+j]>'9') && !(j==0 && q[8+j]=='+'))return false;
        if(digits && (q[7]&0x70)==0x10 && q[8]!='+') {
            if(digits+1>=sizeof c->number)return false;
            c->number[0]='+';memcpy(c->number+1,q+8,digits);
        } else memcpy(c->number,q+8,digits);
        for(size_t j=0;j<i;j++)if(v.calls[j].id==c->id)return false;
        pos+=8+digits;
    }
    if(pos!=n)return false;
    *out=v;return true;
}
bool fmt_call_status(const uint8_t *p,size_t n,struct fmt_call_status *out)
{
    if(!p || !out || n!=6)return false;
    *out=(struct fmt_call_status){.type=(uint16_t)(p[0]|((unsigned)p[1]<<8)),
        .id=p[2],.state=p[3],.cause_class=p[4],.cause=p[5]};return true;
}
