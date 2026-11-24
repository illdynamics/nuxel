/* SPDX-License-Identifier: GPL-2.0-only
 * 3GPP TS 23.038 alphabet / TS 23.040 TPDU. No modem or filesystem access.
 */
#include "sms_pdu.h"
#include <stdio.h>
#include <string.h>

static const uint16_t alphabet[128] = {
    '@',0x00a3,'$',0x00a5,0x00e8,0x00e9,0x00f9,0x00ec,0x00f2,0x00c7,'\n',0x00d8,0x00f8,'\r',0x00c5,0x00e5,
    0x0394,'_',0x03a6,0x0393,0x039b,0x03a9,0x03a0,0x03a8,0x03a3,0x0398,0x039e,0xffff,0x00c6,0x00e6,0x00df,0x00c9,
    ' ','!','"','#',0x00a4,'%','&','\'','(',')','*','+',',','-','.','/',
    '0','1','2','3','4','5','6','7','8','9',':',';','<','=','>','?',
    0x00a1,'A','B','C','D','E','F','G','H','I','J','K','L','M','N','O',
    'P','Q','R','S','T','U','V','W','X','Y','Z',0x00c4,0x00d6,0x00d1,0x00dc,0x00a7,
    0x00bf,'a','b','c','d','e','f','g','h','i','j','k','l','m','n','o',
    'p','q','r','s','t','u','v','w','x','y','z',0x00e4,0x00f6,0x00f1,0x00fc,0x00e0
};
static const struct { uint16_t unicode; uint8_t code; } extension[] = {
    {0x000c,0x0a},{'^',0x14},{'{',0x28},{'}',0x29},{'\\',0x2f},
    {'[',0x3c},{'~',0x3d},{']',0x3e},{'|',0x40},{0x20ac,0x65}
};

const char *sms_codec_name(enum sms_codec_result r)
{
    switch (r) {
    case SMS_CODEC_OK:return "ok"; case SMS_CODEC_INVALID:return "invalid-pdu-or-utf8";
    case SMS_CODEC_TOO_LONG:return "message-too-long";
    case SMS_CODEC_UNSUPPORTED:return "unsupported-alphabet-or-pdu";
    default:return "unknown";
    }
}

static bool next_utf8(const uint8_t **p, const uint8_t *end, uint32_t *out)
{
    if (*p >= end) return false;
    uint8_t c = *(*p)++;
    uint32_t value; unsigned n; uint32_t minimum;
    if (c < 0x80) { *out = c; return c != 0; }
    if (c >= 0xc2 && c <= 0xdf) { n=1; value=c&31; minimum=0x80; }
    else if (c >= 0xe0 && c <= 0xef) { n=2; value=c&15; minimum=0x800; }
    else if (c >= 0xf0 && c <= 0xf4) { n=3; value=c&7; minimum=0x10000; }
    else return false;
    if ((size_t)(end-*p) < n) return false;
    for (unsigned i=0;i<n;i++) {
        c=*(*p)++; if ((c&0xc0)!=0x80) return false;
        value=(value<<6)|(c&63);
    }
    if (value < minimum || value > 0x10ffff || (value>=0xd800 && value<=0xdfff)) return false;
    *out=value; return true;
}

static bool emit_utf8(char *out, size_t cap, size_t *used, uint16_t c)
{
    if (!c || c==0xffff || (c>=0xd800 && c<=0xdfff)) return false;
    size_t n=c<0x80 ? 1 : c<0x800 ? 2 : 3;
    if (*used+n >= cap) return false;
    if (n==1) out[(*used)++]=(char)c;
    else if (n==2) { out[(*used)++]=(char)(0xc0|(c>>6));out[(*used)++]=(char)(0x80|(c&63)); }
    else {
        out[(*used)++]=(char)(0xe0|(c>>12));out[(*used)++]=(char)(0x80|((c>>6)&63));out[(*used)++]=(char)(0x80|(c&63));
    }
    out[*used]=0; return true;
}

static unsigned gsm_code(uint32_t c, uint8_t code[2])
{
    for (unsigned i=0;i<128;i++) if (i!=27 && alphabet[i]==c) { code[0]=(uint8_t)i;return 1; }
    for (size_t i=0;i<sizeof extension/sizeof extension[0];i++) if (extension[i].unicode==c) {
        code[0]=27;code[1]=extension[i].code;return 2;
    }
    return 0;
}

static void set_septet(uint8_t *data, size_t bit, uint8_t code)
{
    for (unsigned i=0;i<7;i++) if (code&(1u<<i)) data[(bit+i)/8]|=(uint8_t)(1u<<((bit+i)%8));
}

static uint8_t get_septet(const uint8_t *data, size_t bit)
{
    uint8_t value=0;
    for (unsigned i=0;i<7;i++) if (data[(bit+i)/8]&(1u<<((bit+i)%8))) value|=(uint8_t)(1u<<i);
    return value;
}

static bool gsm_decode(const uint8_t *p, size_t bit, size_t count, char *text, size_t cap)
{
    size_t used=0; bool escaped=false; text[0]=0;
    for (size_t i=0;i<count;i++,bit+=7) {
        uint8_t v=get_septet(p,bit); uint16_t c=0xffff;
        if (escaped) {
            for (size_t j=0;j<sizeof extension/sizeof extension[0];j++)
                if (extension[j].code==v) c=extension[j].unicode;
            escaped=false;
        } else if (v==27) { escaped=true;continue; }
        else c=alphabet[v];
        if (!emit_utf8(text,cap,&used,c)) return false;
    }
    return !escaped;
}

enum sms_codec_result sms_encode(const char *to, const char *text, uint8_t mr,
                                 uint8_t concat_ref, struct sms_encoded *out)
{
    if (!to || !text || !out) return SMS_CODEC_INVALID;
    bool international=to[0]=='+'; const char *digits=to+(international ? 1 : 0);
    size_t nd=strnlen(digits,21), bytes=strnlen(text,SMS_MAX_TEXT);
    if (!nd || nd>20 || strspn(digits,"0123456789")!=nd || !bytes) return SMS_CODEC_INVALID;
    if (bytes==SMS_MAX_TEXT) return SMS_CODEC_TOO_LONG;
    uint32_t cp[SMS_MAX_TEXT]; size_t nc=0,septets=0; bool gsm=true;
    const uint8_t *pos=(const uint8_t *)text,*end=pos+bytes;
    while (pos<end) {
        uint32_t c; uint8_t code[2];
        if (!next_utf8(&pos,end,&c)) return SMS_CODEC_INVALID;
        if (c>0xffff) return SMS_CODEC_UNSUPPORTED; /* UCS-2, not UTF-16 */
        unsigned n=gsm_code(c,code); if (!n) gsm=false; septets+=n;
        cp[nc++]=c;
    }
    size_t units=gsm ? septets : nc;
    bool multipart=units>(gsm ? 160u : 70u);
    size_t capacity= multipart ? (gsm ? 153u : 67u) : (gsm ? 160u : 70u);
    struct sms_encoded result={0};result.ucs2=!gsm;
    size_t first=0;
    while (first<nc) {
        if (result.count==SMS_MAX_PARTS) return SMS_CODEC_TOO_LONG;
        size_t last=first,amount=0;
        while (last<nc) {
            uint8_t code[2];size_t cost=gsm ? gsm_code(cp[last],code) : 1;
            if (amount+cost>capacity) break;
            amount+=cost;last++;
        }
        struct sms_segment *s=&result.parts[result.count];s->reference=(uint8_t)(mr+result.count);
        uint8_t *p=s->data;
        *p++=(uint8_t)(0x21|(multipart ? 0x40 : 0));*p++=s->reference;
        *p++=(uint8_t)nd;*p++=international ? 0x91 : 0x81;
        for (size_t i=0;i<nd;i+=2) *p++=(uint8_t)((digits[i]-'0')|((i+1<nd ? digits[i+1]-'0' : 15)<<4));
        *p++=0;*p++=gsm ? 0 : 8;
        size_t header=multipart ? 6 : 0,header_septets=(header*8+6)/7;
        *p++=(uint8_t)(gsm ? amount+header_septets : amount*2+header);
        uint8_t *ud=p;
        if (multipart) { ud[0]=5;ud[1]=0;ud[2]=3;ud[3]=concat_ref;ud[4]=0;ud[5]=(uint8_t)(result.count+1); }
        size_t bit=header_septets*7,off=header;
        for (size_t i=first;i<last;i++) {
            if (gsm) {
                uint8_t code[2];unsigned n=gsm_code(cp[i],code);
                for (unsigned j=0;j<n;j++,bit+=7) set_septet(ud,bit,code[j]);
            } else { ud[off++]=(uint8_t)(cp[i]>>8);ud[off++]=(uint8_t)cp[i]; }
        }
        s->len=(size_t)(p-s->data)+(gsm ? (bit+7)/8 : off);
        result.count++;first=last;
    }
    if (multipart) for (size_t i=0;i<result.count;i++) {
        size_t ud_offset=7+(nd+1)/2;
        result.parts[i].data[ud_offset+4]=(uint8_t)result.count;
    }
    *out=result;return SMS_CODEC_OK;
}

struct reader { const uint8_t *p,*end; };
static bool take(struct reader *r,size_t n,const uint8_t **p)
{
    if ((size_t)(r->end-r->p)<n) return false;
    *p=r->p;r->p+=n;return true;
}

static bool address(struct reader *r,char text[SMS_MAX_PEER])
{
    const uint8_t *h,*p;if (!take(r,2,&h) || !h[0] || h[0]>20 || !(h[1]&0x80)) return false;
    size_t n=(h[0]+1u)/2u;if (!take(r,n,&p)) return false;
    if ((h[1]&0x70)==0x50) return gsm_decode(p,0,h[0]*4/7,text,SMS_MAX_PEER);
    size_t used=0;if ((h[1]&0x70)==0x10) text[used++]='+';
    for (unsigned i=0;i<h[0];i++) {
        uint8_t digit=(p[i/2]>>(i%2 ? 4 : 0))&15;
        if (digit>9) return false;
        text[used++]=(char)('0'+digit);
    }
    if ((h[0]&1) && (p[n-1]>>4)!=15) return false;
    text[used]=0;return true;
}

static bool timestamp(struct reader *r,char text[32])
{
    const uint8_t *p;if (!take(r,7,&p)) return false;
    unsigned v[7];
    for (unsigned i=0;i<7;i++) {
        uint8_t b=p[i];if (i==6) b&=(uint8_t)~8;
        if ((b&15)>9 || (b>>4)>9) return false;
        v[i]=(b&15)*10u+(b>>4);
    }
    if (!v[1] || v[1]>12 || !v[2] || v[2]>31 || v[3]>23 || v[4]>59 || v[5]>59 || v[6]>56) return false;
    snprintf(text,32,"%04u-%02u-%02uT%02u:%02u:%02u%c%02u:%02u",
             v[0]+(v[0]>=90 ? 1900 : 2000),v[1],v[2],v[3],v[4],v[5],
             p[6]&8 ? '-' : '+',v[6]/4,(v[6]%4)*15);
    return true;
}

static enum sms_codec_result user_data(struct reader *r,uint8_t first,uint8_t dcs,struct sms_decoded *v)
{
    const uint8_t *p;
    if (!take(r,1,&p)) return SMS_CODEC_INVALID;
    unsigned udl=p[0],coding;
    if ((dcs&0xc0)==0 || (dcs&0xc0)==0x40) {
        if (dcs&0x20) return SMS_CODEC_UNSUPPORTED;
        coding=(dcs>>2)&3;
    } else if ((dcs&0xf0)==0xc0 || (dcs&0xf0)==0xd0) coding=0;
    else if ((dcs&0xf0)==0xe0) coding=2;
    else if ((dcs&0xf0)==0xf0) coding=dcs&4 ? 1 : 0;
    else return SMS_CODEC_UNSUPPORTED;
    if (coding!=0 && coding!=2) return SMS_CODEC_UNSUPPORTED;
    size_t bytes=coding==0 ? (udl*7u+7)/8 : udl;
    if (bytes>140 || !take(r,bytes,&p) || r->p!=r->end) return SMS_CODEC_INVALID;
    size_t header=0;
    if (first&0x40) {
        if (!bytes) return SMS_CODEC_INVALID;
        header=1u+p[0];if (header>bytes) return SMS_CODEC_INVALID;
        for (size_t i=1;i<header;) {
            if (header-i<2) return SMS_CODEC_INVALID;
            uint8_t ie=p[i++],len=p[i++];if (len>header-i) return SMS_CODEC_INVALID;
            if (ie==0 || ie==8) {
                if (v->multipart || len!=(ie==0 ? 3 : 4)) return SMS_CODEC_INVALID;
                v->multipart=true;
                v->concat_reference=ie==0 ? p[i] : (uint16_t)((p[i]<<8)|p[i+1]);
                v->total=p[i+len-2];v->part=p[i+len-1];
                if (!v->total || v->total>SMS_MAX_PARTS || !v->part || v->part>v->total) return SMS_CODEC_UNSUPPORTED;
            } else if ((ie==0x24 || ie==0x25) && (len!=1 || p[i]!=0)) return SMS_CODEC_UNSUPPORTED;
            i+=len;
        }
    }
    if (!coding) {
        size_t hs=(header*8+6)/7;if (hs>udl) return SMS_CODEC_INVALID;
        return gsm_decode(p,hs*7,udl-hs,v->text,sizeof v->text) ? SMS_CODEC_OK : SMS_CODEC_INVALID;
    }
    if ((bytes-header)&1) return SMS_CODEC_INVALID;
    size_t used=0;
    for (size_t i=header;i<bytes;i+=2)
        if (!emit_utf8(v->text,sizeof v->text,&used,(uint16_t)((p[i]<<8)|p[i+1]))) return SMS_CODEC_UNSUPPORTED;
    return SMS_CODEC_OK;
}

enum sms_codec_result sms_decode(const uint8_t *pdu,size_t len,struct sms_decoded *out)
{
    if (!pdu || !out || !len || len>SMS_MAX_PDU || pdu[0]>11 || len<=1u+pdu[0]) return SMS_CODEC_INVALID;
    if (pdu[0]) {
        if (pdu[0]<2 || !(pdu[1]&0x80) || (pdu[1]&0x70)==0x50) return SMS_CODEC_INVALID;
        for (size_t i=2;i<=pdu[0];i++)
            if ((pdu[i]&15)>9 || ((pdu[i]>>4)>9 && !(i==pdu[0] && (pdu[i]>>4)==15))) return SMS_CODEC_INVALID;
    }
    struct reader r={pdu+1+pdu[0],pdu+len};const uint8_t *p;
    struct sms_decoded v={0};
    if (!take(&r,1,&p)) return SMS_CODEC_INVALID;
    uint8_t first=*p;
    if ((first&3)==2) {
        v.kind=SMS_STATUS_REPORT;
        if (!take(&r,1,&p)) return SMS_CODEC_INVALID;
        v.reference=*p;
        if (!address(&r,v.peer) || !timestamp(&r,v.timestamp) || !timestamp(&r,v.discharge) || !take(&r,1,&p)) return SMS_CODEC_INVALID;
        v.status=*p;
        if (r.p<r.end) {
            if (!take(&r,1,&p)) return SMS_CODEC_INVALID;
            unsigned pi=*p;
            /* Reserved/extended parameter descriptions need their own schema. */
            if (pi&0xf8) return SMS_CODEC_UNSUPPORTED;
            if ((pi&1) && !take(&r,1,&p)) return SMS_CODEC_INVALID;
            if (pi&2) { if (!take(&r,1,&p)) return SMS_CODEC_INVALID;v.dcs=*p; }
            if (pi&4) {
                enum sms_codec_result result=user_data(&r,first,v.dcs,&v);
                if (result!=SMS_CODEC_OK) return result;
            } else if (r.p!=r.end) return SMS_CODEC_INVALID;
        }
    } else if ((first&3)==0) {
        v.kind=SMS_DELIVER;
        if (!address(&r,v.peer) || !take(&r,2,&p)) return SMS_CODEC_INVALID;
        v.dcs=p[1];
        if (!timestamp(&r,v.timestamp)) return SMS_CODEC_INVALID;
        enum sms_codec_result result=user_data(&r,first,v.dcs,&v);
        if (result!=SMS_CODEC_OK) return result;
    } else return SMS_CODEC_UNSUPPORTED;
    *out=v;return SMS_CODEC_OK;
}
