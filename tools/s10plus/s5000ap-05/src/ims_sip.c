/* SPDX-License-Identifier: GPL-2.0-only
 *
 * ims_sip.c — bounded SIP/IMS wire codec. See ims_sip.h.
 * No network I/O; no registration-state claim. Never logs secret material.
 */
#include "ims_sip.h"
#include "nv_items.h"   /* nv_md5_hex() RFC 1321 MD5 */
#include <string.h>
#include <stdio.h>
#include <unistd.h>
#include <sys/random.h>
#include <ctype.h>
#include <stdarg.h>
#include <stdlib.h>

static void sip_wipe(void *p,size_t n)
{ volatile unsigned char *v=p;while(n--) *v++=0; }

/* ---- base64 (RFC 4648, no padding requirement enforced) ---- */
static const char b64[]="ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/";
static int b64val(char c)
{
    if (c>='A'&&c<='Z') return c-'A';
    if (c>='a'&&c<='z') return c-'a'+26;
    if (c>='0'&&c<='9') return c-'0'+52;
    if (c=='+') return 62;
    if (c=='/') return 63;
    return -1;
}
size_t ims_base64_encode(const uint8_t *in, size_t n, char *out, size_t cap)
{
    if (!in || (n && !out)) return 0;
    size_t o=0;
    for (size_t i=0;i<n;i+=3) {
        uint32_t v=in[i]<<16;
        v |= i+1<n ? in[i+1]<<8 : 0;
        v |= i+2<n ? in[i+2] : 0;
        if (o>=cap) return 0;
        out[o++]=b64[(v>>18)&63];
        if (o>=cap) return 0;
        out[o++]=b64[(v>>12)&63];
        if (o>=cap) return 0;
        out[o++]= i+1<n ? b64[(v>>6)&63] : '=';
        if (o>=cap) return 0;
        out[o++]= i+2<n ? b64[v&63] : '=';
    }
    return o;
}
bool ims_base64_decode(const char *in, size_t n, uint8_t *out, size_t cap, size_t *out_len)
{
    if (!in || !out || !out_len) return false;
    size_t o=0; uint32_t acc=0; int bits=0;
    for (size_t i=0;i<n;i++) {
        char c=in[i];
        if (c=='=' || c=='\r' || c=='\n') break;
        int v=b64val(c); if (v<0) return false;
        acc=(acc<<6)|(uint32_t)v; bits+=6;
        if (bits>=8) { bits-=8; if (o>=cap) return false; out[o++]= (acc>>bits)&0xff; }
    }
    *out_len=o; return true;
}

/* ---- bounded append ---- */
struct buf { char *p; size_t cap, len; };
static bool add(struct buf *b, const char *s)
{ size_t n=strlen(s); if (b->len+n>=b->cap) return false;
  memcpy(b->p+b->len,s,n); b->len+=n; return true; }
static bool addn(struct buf *b, const char *s, size_t n)
{ if (n && b->len+n>=b->cap) return false;
  if (n) { memcpy(b->p+b->len,s,n); b->len+=n; } return true; }
static bool addf(struct buf *b, const char *fmt, ...)
{
    char tmp[512]; va_list ap; va_start(ap,fmt);
    int n=vsnprintf(tmp,sizeof tmp,fmt,ap); va_end(ap);
    if (n<0 || (size_t)n>=sizeof tmp) return false;
    return add(b,tmp);
}

size_t ims_sip_register_build(char *out, size_t cap, const char *impu,
                              const char *impi, const char *pcscf,
                              const char *local_ip, uint16_t port,
                              const char *sec_offer)
{
    return ims_sip_register_build_ex2(out, cap, impu, impi, pcscf, local_ip,
                                      port, sec_offer, NULL, NULL);
}

/* Persistent UUID or actual IMEI only. Never invent an IMEI. */
static size_t sip_instance_urn(const char *instance, char *out, size_t cap)
{
    if (!instance || !*instance) { if(cap) out[0]=0; return 0; }
    if (strlen(instance)==45 && !strncmp(instance,"urn:uuid:",9)) {
        for (size_t i=9;i<45;i++) {
            bool dash=i==17 || i==22 || i==27 || i==32;
            if (dash ? instance[i]!='-' : !isxdigit((unsigned char)instance[i])) return 0;
        }
        int n=snprintf(out,cap,"%s",instance);
        return n>0 && (size_t)n<cap ? (size_t)n : 0;
    }
    if (strlen(instance)!=15) return 0;
    for (unsigned i=0;i<15;i++) if(instance[i]<'0' || instance[i]>'9') return 0;
    int n=snprintf(out,cap,"urn:gsma:imei:%.8s-%.6s-0",instance,instance+8);
    return n>0 && (size_t)n<cap ? (size_t)n : 0;
}

size_t ims_sip_register_build_ex(char *out, size_t cap, const char *impu,
                                 const char *impi, const char *pcscf,
                                 const char *local_ip, uint16_t port,
                                 const char *sec_offer, const char *imei)
{
    return ims_sip_register_build_ex2(out, cap, impu, impi, pcscf, local_ip,
                                      port, sec_offer, imei, NULL);
}

static size_t ims_sip_register_build_core(char *out, size_t cap,
                                          const char *impu, const char *impi,
                                          const char *pcscf, const char *local_ip,
                                          uint16_t port, const char *sec_offer,
                                          const char *imei, const char *cell_id,
                                          const char *home_plmn, int utran_tac,
                                          bool require_sec_agree);

size_t ims_sip_register_build_ex2(char *out, size_t cap, const char *impu,
                                  const char *impi, const char *pcscf,
                                  const char *local_ip, uint16_t port,
                                  const char *sec_offer, const char *imei,
                                  const char *cell_id)
{
    return ims_sip_register_build_core(out, cap, impu, impi, pcscf, local_ip,
                                       port, sec_offer, imei, cell_id, NULL, -1, false);
}
size_t ims_sip_register_build_ex3(char *out, size_t cap, const char *impu,
                                  const char *impi, const char *pcscf,
                                  const char *local_ip, uint16_t port,
                                  const char *sec_offer, const char *imei,
                                  const char *cell_id, const char *home_plmn)
{
    return ims_sip_register_build_core(out, cap, impu, impi, pcscf, local_ip,
                                       port, sec_offer, imei, cell_id, home_plmn,
                                       -1, false);
}
size_t ims_sip_register_build_ex4(char *out, size_t cap, const char *impu,
                                  const char *impi, const char *pcscf,
                                  const char *local_ip, uint16_t port,
                                  const char *sec_offer, const char *imei,
                                  const char *cell_id, const char *home_plmn,
                                  int utran_tac)
{
    return ims_sip_register_build_core(out, cap, impu, impi, pcscf, local_ip,
                                       port, sec_offer, imei, cell_id, home_plmn,
                                       utran_tac, false);
}

/* Security-first initial REGISTER (TS 33.203 7.1 / TS 24.229 5.1.2A). Some
 * P-CSCFs refuse a plaintext initial REGISTER (answering 480) and require the
 * UE to assert sec-agree + a valid Security-Client offer before they issue the
 * 401/407 AKA challenge. This variant adds `Require: sec-agree` and
 * `Proxy-Require: sec-agree` alongside the canonical ipsec-3gpp Security-Client
 * offer. The offer/proxy MUST be self-consistent; callers only use this when a
 * complete ipsec-3gpp offer with real SPI/port values is supplied. */
size_t ims_sip_register_build_secure(char *out, size_t cap, const char *impu,
                                     const char *impi, const char *pcscf,
                                     const char *local_ip, uint16_t port,
                                     const char *sec_offer, const char *imei,
                                     const char *cell_id)
{
    return ims_sip_register_build_core(out, cap, impu, impi, pcscf, local_ip,
                                       port, sec_offer, imei, cell_id, NULL, -1, true);
}
size_t ims_sip_register_build_secure_ex3(char *out, size_t cap,
                                         const char *impu, const char *impi,
                                         const char *pcscf, const char *local_ip,
                                         uint16_t port, const char *sec_offer,
                                         const char *imei, const char *cell_id,
                                         const char *home_plmn)
{
    return ims_sip_register_build_core(out, cap, impu, impi, pcscf, local_ip,
                                       port, sec_offer, imei, cell_id, home_plmn,
                                       -1, true);
}
size_t ims_sip_register_build_secure_ex4(char *out, size_t cap,
                                         const char *impu, const char *impi,
                                         const char *pcscf, const char *local_ip,
                                         uint16_t port, const char *sec_offer,
                                         const char *imei, const char *cell_id,
                                         const char *home_plmn, int utran_tac)
{
    return ims_sip_register_build_core(out, cap, impu, impi, pcscf, local_ip,
                                       port, sec_offer, imei, cell_id, home_plmn,
                                       utran_tac, true);
}

static size_t ims_sip_register_build_core(char *out, size_t cap,
                                          const char *impu, const char *impi,
                                          const char *pcscf, const char *local_ip,
                                          uint16_t port, const char *sec_offer,
                                          const char *imei, const char *cell_id,
                                          const char *home_plmn, int utran_tac,
                                          bool require_sec_agree)
{
    if (!out || !impu || !impi || !pcscf || !local_ip) return 0;
    /* Accept impu with or without the "sip:" scheme; derive (a) the full SIP
     * URI and (b) the registrar domain (the part after '@') for the R-URI.
     * A REGISTER Request-URI is the registrar/home domain, e.g.
     *   REGISTER sip:ims.mnc008.mcc204.3gppnetwork.org
     * NOT "sip:sip:IMSI@domain" (a previously emitted malformed R-URI that the
     * P-CSCF answered with 403). To/From/Contact use the IMPU SIP URI. */
    const char *impu_uri = (strncmp(impu, "sip:", 4) == 0) ? impu : NULL;
    char impu_buf[256];
    if (!impu_uri) {
        int k = snprintf(impu_buf, sizeof impu_buf, "sip:%s", impu);
        if (k < 0 || (size_t)k >= sizeof impu_buf) return 0;
        impu_uri = impu_buf;
    }
    const char *dom = strchr(impu_uri, '@');
    const char *ruri = dom ? dom + 1 : (impu_uri + 4);
    /* Contact userpart: the user part of the IMPI (before '@'), e.g. the
     * IMSI. The Contact host is the UE's local IMS IP/port. */
    const char *impi_n = (strncmp(impi, "sip:", 4) == 0) ? impi + 4 : impi;
    char cuser_buf[128];
    const char *at = strchr(impi_n, '@');
    size_t clen = at ? (size_t)(at - impi_n) : strlen(impi_n);
    if (clen == 0 || clen >= sizeof cuser_buf) return 0;
    memcpy(cuser_buf, impi_n, clen); cuser_buf[clen] = 0;
    const char *cuser = cuser_buf;
    char inst[64]="", instance_param[96]="";
    if (imei && *imei) {
        if (!sip_instance_urn(imei,inst,sizeof inst)) return 0;
        snprintf(instance_param,sizeof instance_param,";+sip.instance=\"<%s>\"",inst);
    }
    struct buf r={out,cap,0};
    if (!addf(&r,"REGISTER sip:%s SIP/2.0\r\n", ruri)) return 0;
    if (!addf(&r,"Via: SIP/2.0/UDP [%s]:%u;branch=z9hG4bKnuxel\r\n", local_ip, port)) return 0;
    if (!addf(&r,"Max-Forwards: 70\r\n")) return 0;
    if (!addf(&r,"From: <%s>;tag=nuxel\r\n", impu_uri)) return 0;
    if (!addf(&r,"To: <%s>\r\n", impu_uri)) return 0;
    if (!addf(&r,"Call-ID: nuxel-%x@%s\r\n", (unsigned)(uintptr_t)out, local_ip)) return 0;
    if (!addf(&r,"CSeq: 1 REGISTER\r\n")) return 0;
    /* Reachable local contact; SMS capability, not unimplemented IMS voice. */
    if (strchr(local_ip, ':')) {
        if (!addf(&r,"Contact: <sip:%s@[%s]:%u;transport=udp>%s;+g.3gpp.smsip;expires=600\r\n",
                  cuser,local_ip,(unsigned)port,instance_param)) return 0;
    } else {
        if (!addf(&r,"Contact: <sip:%s@%s:%u;transport=udp>%s;+g.3gpp.smsip;expires=600\r\n",
                  cuser,local_ip,(unsigned)port,instance_param)) return 0;
    }
    /* The INVITE/REGISTER is sent directly to the P-CSCF address (outbound
     * proxy) on the transport; no Route header is needed and adding one that
     * points at the same P-CSCF caused the CP/P-CSCF to reject the request.
     * (Live: with a direct R-URI-to-domain REGISTER the P-CSCF responded 480
     *  "user unavailable" for an unknown IMPU instead of 403.) */
    /* TS 24.229 7.2A.4.3 item 12: MCC+MNC+TAC(4 hex)+ECI(7 hex).
     * Never mix a SIM home PLMN with serving-cell information. Unknown or
     * incomplete location leaves only the known access type. */
    bool cell_ok = cell_id && strlen(cell_id)==7;
    if (cell_ok) for (const char *q=cell_id;*q;q++)
        if (!isxdigit((unsigned char)*q)) cell_ok=false;
    size_t pn = home_plmn ? strlen(home_plmn) : 0;
    bool plmn_ok = pn==5 || pn==6;
    if (plmn_ok) for (const char *q=home_plmn;*q;q++)
        if (*q<'0' || *q>'9') plmn_ok=false;
    if (cell_ok && plmn_ok && utran_tac>0 && utran_tac<=0xffff && utran_tac!=0xfffe) {
        if (!addf(&r,"P-Access-Network-Info: 3GPP-E-UTRAN-FDD;utran-cell-id-3gpp=%s%04x%s\r\n",
                  home_plmn,(unsigned)utran_tac,cell_id)) return 0;
    } else if (!add(&r,"P-Access-Network-Info: 3GPP-E-UTRAN-FDD\r\n")) return 0;
    /* TS 33.203 7.1 / TS 24.229 5.1.2A: the first REGISTER in an IMS access
     * network carries an ipsec-3gpp Security-Client offer and the
     * Require/Proxy-Require: sec-agree headers so the P-CSCF returns the
     * 401 with Security-Server instead of treating the registration as
     * unauthenticated. */
    /* Round 18 live evidence: the KPN P-CSCF returns 400 Bad Request when the
     * first REGISTER carries "Require: sec-agree" + "Proxy-Require: sec-agree"
     * together with Security-Client (it does not accept IPsec-3gpp negotiation
     * this way). Dropping the two Require headers but keeping Security-Client
     * makes the request parse cleanly (-> 480 Retry-After), so the offer alone
     * is transmitted here and sec-agree is asserted only when continuing after
     * a 401 that advertises Security-Server (handled by the FSM). */
    if (sec_offer && *sec_offer) {
        /* RFC 3329 2.1 / TS 33.203 7.1: the header value MUST begin with the
         * security mechanism name ("ipsec-3gpp"), followed by the parameters.
         * The caller's offer may or may not already carry it; enforce it. */
        if (strncmp(sec_offer, "ipsec-3gpp", 10) == 0)
            { if (!addf(&r,"Security-Client: %s\r\n", sec_offer)) return 0; }
        else
            { if (!addf(&r,"Security-Client: ipsec-3gpp;%s\r\n", sec_offer)) return 0; }
    }
    /* TS 33.203 7.1: when this variant is requested, assert sec-agree so the
     * P-CSCF MUST negotiate integrity/confidentiality (requires the full
     * Security-Client offer to be present). */
    if (require_sec_agree && sec_offer && *sec_offer) {
        if (!addf(&r,"Require: sec-agree\r\n")) return 0;
        if (!addf(&r,"Proxy-Require: sec-agree\r\n")) return 0;
    }
    /* P-Preferred-Identity: control the *public* identity presented, separate
     * from the private IMPI used for digest. This is the UE-selected IMPU. */
    if (!addf(&r,"P-Preferred-Identity: <%s>\r\n", impu_uri)) return 0;
    if (!addf(&r,"Supported: path, outbound, 100rel\r\n")) return 0;
    if (!addf(&r,"Allow: REGISTER, MESSAGE, OPTIONS\r\n")) return 0;
    if (!addf(&r,"Content-Length: 0\r\n\r\n")) return 0;
    return r.len;
}

/* Extract "<key>=<quoted-or-token>", respecting RFC 2617 quoted-string. */
static bool param(const char *hdr, size_t n, const char *key, size_t keylen,
                  char *out, size_t outcap)
{
    const char *p=hdr; size_t remain=n;
    while (remain >= keylen) {
        const char *eq = (const char*)memchr(p, key[0], remain);
        if (!eq) return false;
        size_t skip=(size_t)(eq-p);
        if (skip+keylen>remain) return false;
        if (memcmp(eq,key,keylen)!=0) { p=eq+1; remain-=skip+1; continue; }
        size_t v=keylen; const char *val=eq+v; size_t vn=remain-skip-v;
        bool q = vn>0 && *val=='"';
        size_t j=0; const char *c=val+(q?1:0); size_t cn=vn-(q?1:0);
        while (cn>0 && j+1<outcap) {
            char ch=*c;
            if (q) { if (ch=='"' ) { c++; cn--; break; } }
            else   { if (ch==',' || ch==' ' || ch=='\t') break; }
            out[j++]=ch; c++; cn--;
        }
        out[j]=0;
        return j>0;
    }
    return false;
}
bool ims_sip_challenge_parse(const char *hdr, size_t n, char realm[64], char nonce[128],
                             char qop[16], char alg[24], char cnonce[16])
{
    if (!hdr || !realm || !nonce || !qop || !alg || !cnonce) return false;
    realm[0]=nonce[0]=qop[0]=alg[0]=cnonce[0]=0;
    bool ok = param(hdr,n,"realm=",6,realm,64) &&
              param(hdr,n,"nonce=",6,nonce,128) &&
              param(hdr,n,"algorithm=",10,alg,24);
    (void)param(hdr,n,"qop=",4,qop,16);      /* optional; validated loosely */
    if (!ok) return false;
    if (strcmp(alg,"AKAv1-MD5") || strcmp(qop,"auth")) return false;
    uint8_t random[7];if(getentropy(random,sizeof random)) return false;
    for(unsigned i=0;i<sizeof random;i++) snprintf(cnonce+2*i,3,"%02x",random[i]);
    return true;
}

/* Copy the first Safety-Server "ipsec-3gpp" offer value (the whole header
 * value is one offer list; we take the leading ipsec-3gpp token only). */
bool ims_sip_security_server(const char *hdr, size_t hdr_len,
                             char *out, size_t outcap)
{
    if (!hdr || !out || outcap == 0) return false;
    out[0] = 0;
    size_t i = 0;
    while (i < hdr_len) {
        while (i < hdr_len && (hdr[i] == ' ' || hdr[i] == '\t' || hdr[i] == ',')) i++;
        if (hdr_len - i < 11 || strncmp(hdr + i, "ipsec-3gpp", 10) != 0) {
            /* Not an ipsec-3gpp offer here; skip to the next comma. */
            const char *c = memchr(hdr + i, ',', hdr_len - i);
            if (!c) break;
            i = (size_t)(c - hdr) + 1;
            continue;
        }
        size_t j = i;
        while (j < hdr_len && hdr[j] != ',') j++;
        size_t len = j - i;
        while (len && (hdr[i + len - 1] == ' ' || hdr[i + len - 1] == '\t')) len--;
        if (len >= outcap) len = outcap - 1;
        memcpy(out, hdr + i, len);
        out[len] = 0;
        return len > 0;
    }
    return false;
}

/* RFC 2617 digest = H( H(A1) : nonce : nc : cnonce : qop : H(A2) )
 * IMS AKA: A1 = impi : realm : RESPONSE, where RESPONSE is base64(RES).
 * A2 for REGISTER = method : uri. */
static bool md5cathex(const char **parts, size_t np, char out[33])
{
    size_t total=1; int rc;
    for (size_t i=0;i<np;i++) total+=strlen(parts[i])+(i+1<np?1:0);
    char *sbuf=(char *)malloc(total); if(!sbuf) return false;
    size_t off=0;
    for (size_t i=0;i<np;i++) {
        size_t l=strlen(parts[i]);
        memcpy(sbuf+off,parts[i],l); off+=l;
        if (i+1<np) { sbuf[off++]=':'; }
    }
    sbuf[off]=0;
    rc=nv_md5_hex((const uint8_t*)sbuf,off,out);
    free(sbuf);
    return rc==0;
}
size_t ims_sip_authorization_build(char *out, size_t cap,
                                   const struct ims_sip_digest_params *p, bool is_aka)
{
    if (!out || !p) return 0;
    char ha1[33], ha2[33], resp[33];
    const char *a1 = p->response ? p->response : "";
    const char *a1user = p->impu ? p->impu : "";
    /* IMPI includes its realm; AKA password is binary RES, not base64 text. */
    const char *username=!strncmp(a1user,"sip:",4)?a1user+4:a1user;
    const char *realm=p->realm?p->realm:"";
    if (is_aka) {
        uint8_t res[16], a1buf[512];size_t rn=0;
        if (!ims_base64_decode(a1,strlen(a1),res,sizeof res,&rn) || rn<4 || rn>16) return 0;
        int n=snprintf((char *)a1buf,sizeof a1buf,"%s:%s:",username,realm);
        if (n<0 || (size_t)n+rn>sizeof a1buf) { sip_wipe(res,sizeof res);return 0; }
        memcpy(a1buf+n,res,rn);
        int rc=nv_md5_hex(a1buf,(size_t)n+rn,ha1);
        sip_wipe(a1buf,sizeof a1buf);sip_wipe(res,sizeof res);
        if(rc) return 0;
    } else {
        const char *pp[]={username,realm,a1};
        if (!md5cathex(pp,3,ha1)) return 0;
    }
    const char *a2u=p->uri?p->uri:""; const char *m=p->method?p->method:"REGISTER";
    const char *pa2[]={m,a2u};
    if (!md5cathex(pa2,2,ha2)) return 0;
    char nc[9];snprintf(nc,sizeof nc,"%08x",p->nonce_count?p->nonce_count:1u);
    const char *qop="auth";
    const char *pd[]={ha1,p->nonce?p->nonce:"",nc,p->cnonce?p->cnonce:"",qop,ha2};
    if (!md5cathex(pd,6,resp)) return 0;
    struct buf b={out,cap,0};
    if (!addf(&b,"Authorization: Digest username=\"%s\", realm=\"%s\", nonce=\"%s\", uri=\"%s\", "
              "response=\"%s\", algorithm=%s, cnonce=\"%s\", nc=%s, qop=%s\r\n",
              username, p->realm?p->realm:"", p->nonce?p->nonce:"",
              p->uri?p->uri:"", resp, is_aka?"AKAv1-MD5":"MD5",
              p->cnonce?p->cnonce:"", nc, qop)) return 0;
    return b.len;
}

size_t ims_sip_message_build(char *out, size_t cap, const char *impu, const char *to,
                             const char *from, const char *route_uri, uint16_t tag,
                             const void *body, size_t body_len)
{
    if (!out || !impu || !to || !from || !body) return 0;
    /* Legacy signature: no home domain / local IP available. Delegate to the
     * standards builder with the recipient used verbatim and the IMPU host as
     * the home domain so a bare number still yields a valid R-URI. */
    const char *dom = from ? strchr(from, '@') : NULL;
    char home[128] = {0};
    if (dom) snprintf(home, sizeof home, "%s", dom + 1);
    return ims_sip_message_build_ex(out, cap, impu, home, to, NULL, 0,
                                    route_uri, tag, body, body_len);
}

size_t ims_sip_message_build_ex(char *out, size_t cap,
                                const char *impu, const char *home_domain,
                                const char *to, const char *local_ip,
                                uint16_t local_port, const char *route_uri,
                                uint16_t tag, const void *body, size_t body_len)
{
    if (!out || !impu || !to || !body || body_len == 0) return 0;
    /* Request-URI: a supplied sip:/tel: URI is used verbatim. A bare number is
     * encoded as "sip:<digits>@<home_domain>" (KPN terminates via the IMS
     * domain); a "+" prefix is preserved. */
    char ruri[256];
    if (!strncmp(to, "sip:", 4) || !strncmp(to, "tel:", 4))
        snprintf(ruri, sizeof ruri, "%s", to);
    else {
        const char *host = (home_domain && *home_domain) ? home_domain : "localhost";
        snprintf(ruri, sizeof ruri, "sip:%s@%s", to, host);
    }
    uint8_t random[16];char token[33];
    if(getentropy(random,sizeof random)) return 0;
    for(unsigned i=0;i<sizeof random;i++) snprintf(token+2*i,3,"%02x",random[i]);
    struct buf b={out,cap,0};
    if (!addf(&b,"MESSAGE %s SIP/2.0\r\n", ruri)) return 0;
    if (local_ip && *local_ip) {
        if (strchr(local_ip, ':'))
            { if (!addf(&b,"Via: SIP/2.0/UDP [%s]:%u;branch=z9hG4bK%s\r\n",
                        local_ip, (unsigned)local_port, token)) return 0; }
        else
            { if (!addf(&b,"Via: SIP/2.0/UDP %s:%u;branch=z9hG4bK%s\r\n",
                        local_ip, (unsigned)local_port, token)) return 0; }
    } else {
        if (!addf(&b,"Via: SIP/2.0/UDP ims;branch=z9hG4bK%s\r\n", token)) return 0;
    }
    if (!addf(&b,"Max-Forwards: 70\r\n")) return 0;
    /* From carries an originator tag; To has none (it is the callee). */
    if (!addf(&b,"From: <%s>;tag=nuxel%u\r\n", impu, (unsigned)tag)) return 0;
    if (!addf(&b,"To: <%s>\r\n", ruri)) return 0;
    if (!addf(&b,"Call-ID: nuxel-msg-%s\r\n", token)) return 0;
    if (!addf(&b,"CSeq: 1 MESSAGE\r\n")) return 0;
    /* Route: only a real sip:/tel: URI is used; a bare host is wrapped with an
     * explicit scheme and the loose-route ;lr flag (RFC 3261 8.1.2). */
    if (route_uri && *route_uri) {
        if (*route_uri=='<') {
            if (!addf(&b,"Route: %s\r\n",route_uri)) return 0;
        } else if (!strncmp(route_uri, "sip:", 4) || !strncmp(route_uri, "tel:", 4)) {
            if (strstr(route_uri, ";lr"))
                { if (!addf(&b,"Route: <%s>\r\n", route_uri)) return 0; }
            else
                { if (!addf(&b,"Route: <%s;lr>\r\n", route_uri)) return 0; }
        } else {
            if (!addf(&b,"Route: <sip:%s;lr>\r\n", route_uri)) return 0;
        }
    }
    /* UE-originated identity is P-Preferred-Identity, not P-Asserted. */
    if (!addf(&b,"P-Preferred-Identity: <%s>\r\n", impu)) return 0;
    if (!addf(&b,"Content-Type: application/vnd.3gpp.sms\r\n")) return 0;
    if (!addf(&b,"Content-Length: %u\r\n\r\n", (unsigned)body_len)) return 0;
    if (!addn(&b,body,body_len)) return 0;
    return b.len;
}

/* Find a header value by case-insensitive name in a SIPS response; bounded. */
static const uint8_t *ragain_header(const uint8_t *msg, size_t len, const char *name,
                                    size_t *vlen)
{
    size_t nlen = strlen(name);
    if (len < nlen + 2) return NULL;
    const uint8_t *end = msg + len;
    const uint8_t *le = memchr(msg, '\n', len);
    if (!le) return NULL;
    const uint8_t *p = le + 1;
    while (p + nlen + 1 < end) {
        const uint8_t *e = memchr(p, '\n', (size_t)(end - p));
        if (!e) break;
        size_t llen = (size_t)(e - p);
        if(llen==0 || (llen==1 && *p=='\r')) break;
        if (llen >= nlen + 1 && p[nlen] == ':' &&
            strncasecmp((const char *)p, name, nlen) == 0) {
            const uint8_t *v = p + nlen + 1;
            while (v < e && (*v == ' ' || *v == '\t')) v++;
            size_t vl = (size_t)(e - v);
            if (vl && v[vl - 1] == '\r') vl--;
            if (vlen) *vlen = vl;
            return v;
        }
        p = e + 1;
    }
    return NULL;
}

bool ims_sip_response_parse(const void *msg, size_t len, struct ims_sip_response *out)
{
    if (!msg || !out) return false;
    const uint8_t *b = (const uint8_t *)msg;
    out->code = 0;
    out->cseq_method[0] = 0;
    out->body_len = 0;
    out->have_content_length = false;
    if (len < 12 || memcmp(b, "SIP/2.0 ", 8) != 0) return false;
    if (b[8] < '1' || b[8] > '6' || b[9] < '0' || b[9] > '9' ||
        b[10] < '0' || b[10] > '9') return false;
    out->code = (b[8] - '0') * 100 + (b[9] - '0') * 10 + (b[10] - '0');
    /* CSeq: "<seq> <METHOD>" — take the method token after the first SP. */
    size_t vl = 0;
    const uint8_t *c = ragain_header(b, len, "CSeq", &vl);
    if (c) {
        size_t i = 0;
        while (i < vl && (c[i] == ' ' || c[i] == '\t')) i++;
        while (i < vl && c[i] >= '0' && c[i] <= '9') i++;
        while (i < vl && (c[i] == ' ' || c[i] == '\t')) i++;
        size_t j = 0;
        while (i < vl && j + 1 < sizeof out->cseq_method &&
               ((c[i] >= 'A' && c[i] <= 'Z') || (c[i] >= 'a' && c[i] <= 'z')))
            out->cseq_method[j++] = (char)toupper(c[i++]);
        out->cseq_method[j] = 0;
    }
    const uint8_t *hdr_end = memmem(b, len, "\r\n\r\n", 4);
    const uint8_t *body = hdr_end ? hdr_end + 4 : NULL;
    const uint8_t *cl = ragain_header(b, len, "Content-Length", &vl);
    if (cl) {
        unsigned v = 0;
        for (size_t i = 0; i < vl && cl[i] >= '0' && cl[i] <= '9' && i < 9; i++)
            v = v * 10u + (unsigned)(cl[i] - '0');
        out->body_len = v;
        out->have_content_length = true;
    } else if (body) {
        out->body_len = (unsigned)(len - (size_t)(body - b));
    }
    return true;
}

/* Copies only header values, never scans into a binary RP body. */
bool ims_sip_header(const void *msg,size_t n,const char *name,char *out,size_t cap)
{
    size_t len=0;const uint8_t *v=ragain_header(msg,n,name,&len);
    if (!v || !len || len>=cap) return false;
    for(size_t i=0;i<len;i++) if(v[i]<32 && v[i]!='\t') return false;
    memcpy(out,v,len);out[len]=0;return true;
}
bool ims_sip_same_transaction(const void *request,size_t rn,const void *reply,size_t n)
{
    char a[256],b[256];
    const char *fields[]={"Call-ID","CSeq"};
    for(unsigned i=0;i<2;i++)
        if(!ims_sip_header(request,rn,fields[i],a,sizeof a) ||
           !ims_sip_header(reply,n,fields[i],b,sizeof b) || strcmp(a,b)) return false;
    if(!ims_sip_header(request,rn,"Via",a,sizeof a) ||
       !ims_sip_header(reply,n,"Via",b,sizeof b)) return false;
    char *ap=strstr(a,"branch="),*bp=strstr(b,"branch=");
    if(!ap || !bp) return false;
    size_t an=strcspn(ap,"; ,\t"),bn=strcspn(bp,"; ,\t");
    return an==bn && !memcmp(ap,bp,an);
}
bool ims_sip_sms_parse(const void *msg,size_t n,struct ims_sip_sms_request *r)
{
    if(!msg || !r || n<16 || memcmp(msg,"MESSAGE ",8)) return false;
    memset(r,0,sizeof *r);
    const uint8_t *p=msg,*end=memmem(p,n,"\r\n\r\n",4);
    if(!end) return false;
    char type[80],length[16],seq[80];
    if(!ims_sip_header(msg,n,"Content-Type",type,sizeof type) ||
       strcasecmp(type,"application/vnd.3gpp.sms") ||
       !ims_sip_header(msg,n,"Content-Length",length,sizeof length) ||
       !ims_sip_header(msg,n,"CSeq",seq,sizeof seq) ||
       !ims_sip_header(msg,n,"Via",r->via,sizeof r->via) ||
       !ims_sip_header(msg,n,"From",r->from,sizeof r->from) ||
       !ims_sip_header(msg,n,"To",r->to,sizeof r->to) ||
       !ims_sip_header(msg,n,"Call-ID",r->call_id,sizeof r->call_id)) return false;
    unsigned long len=0;
    for(const char *q=length;*q;q++) {if(*q<'0'||*q>'9') return false;len=len*10+*q-'0';if(len>300)return false;}
    char *se;unsigned long cs=strtoul(seq,&se,10);
    if(se==seq || cs>0x7fffffff || strcmp(se," MESSAGE")) return false;
    r->cseq=(uint32_t)cs;r->body=end+4;r->body_len=n-(size_t)(r->body-p);
    return r->body_len==len && len>=2;
}
size_t ims_sip_sms_response(char *out,size_t cap,const struct ims_sip_sms_request *r,unsigned code)
{
    if(!out || !r || (code!=200 && code!=202 && code!=400 && code!=500)) return 0;
    const char *reason=code==200?"OK":code==202?"Accepted":code==400?"Bad Request":"Server Internal Error";
    struct buf b={out,cap,0};
    if(!addf(&b,"SIP/2.0 %u %s\r\nVia: %s\r\nFrom: %s\r\nTo: %s%s\r\nCall-ID: %s\r\nCSeq: %u MESSAGE\r\nContent-Length: 0\r\n\r\n",
        code,reason,r->via,r->from,r->to,strstr(r->to,";tag=")?"":";tag=nuxel-rp",r->call_id,r->cseq))return 0;
    return b.len;
}
