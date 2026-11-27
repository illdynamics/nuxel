/* SPDX-License-Identifier: GPL-2.0-only
 *
 * ims_sip.c — bounded SIP/IMS wire codec. See ims_sip.h.
 * No network I/O; no registration-state claim. Never logs secret material.
 */
#include "ims_sip.h"
#include "nv_items.h"   /* nv_md5_hex() RFC 1321 MD5 */
#include <string.h>
#include <stdio.h>
#include <ctype.h>
#include <stdarg.h>
#include <stdlib.h>

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
    return ims_sip_register_build_ex(out, cap, impu, impi, pcscf, local_ip,
                                     port, sec_offer, NULL);
}

/* RFC 5626 +sip.instance IMEI URN: "urn:gsma:imei:<8>-<6>-<1>". The AP only
 * obtains a real IMEI when the modem reports it (SV); otherwise a syntactically
 * valid all-zero URN is emitted (an IMS core treats an unprovisioned instance
 * as an anonymous device — it cannot be used to bypass entitlement). */
static size_t sip_instance_urn(const char *imei, char *out, size_t cap)
{
    int k;
    if (imei && (strlen(imei) == 15)) {
        bool digs = true;
        for (int i = 0; i < 15; i++) if (imei[i] < '0' || imei[i] > '9') { digs = false; break; }
        if (digs) {
            k = snprintf(out, cap, "urn:gsma:imei:%.8s-%.6s-%c",
                         imei, imei + 8, imei[14]);
            return (k > 0 && (size_t)k < cap) ? (size_t)k : 0;
        }
    }
    k = snprintf(out, cap, "urn:gsma:imei:00000000-000000-0");
    return (k > 0 && (size_t)k < cap) ? (size_t)k : 0;
}

size_t ims_sip_register_build_ex(char *out, size_t cap, const char *impu,
                                 const char *impi, const char *pcscf,
                                 const char *local_ip, uint16_t port,
                                 const char *sec_offer, const char *imei)
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
    char inst[32];
    if (!sip_instance_urn(imei, inst, sizeof inst)) return 0;
    struct buf r={out,cap,0};
    if (!addf(&r,"REGISTER sip:%s SIP/2.0\r\n", ruri)) return 0;
    if (!addf(&r,"Via: SIP/2.0/UDP [%s]:%u;branch=z9hG4bKnuxel\r\n", local_ip, port)) return 0;
    if (!addf(&r,"Max-Forwards: 70\r\n")) return 0;
    if (!addf(&r,"From: <%s>;tag=nuxel\r\n", impu_uri)) return 0;
    if (!addf(&r,"To: <%s>\r\n", impu_uri)) return 0;
    if (!addf(&r,"Call-ID: nuxel-%x@%s\r\n", (unsigned)(uintptr_t)out, local_ip)) return 0;
    if (!addf(&r,"CSeq: 1 REGISTER\r\n")) return 0;
    /* Contact MUST be a valid SIP URI. The previous form
     * "sip:<user>@[<ipv6>]:<port>" is not a parseable SIP/SIPS URI once the
     * bracketed IPv6 literal is present (RFC 3261 19.1.1 requires the host in
     * a URI, no [] unless inside authority with an explicit scheme; the CP
     * P-CSCF rejects malformed Contact). Use the IMPU domain as the URI host
     * (a stock-observed form) with an explicit UDP transport, plus a
     * syntactically valid +sip.instance URN (RFC 5626 4.1) and the
     * IMS communication service identifier for MMTEL. `transport=udp` names
     * the signaling to which the ipsec-3gpp Security-Client applies.
     * The local IP stays in the Via (the UE's real reachable address). */
    if (!addf(&r,"Contact: <sip:%s@%s;transport=udp>;+sip.instance=\"<urn:uuid:%s>\";"
              "+g.3gpp.icsi-ref=\"urn%%3Aurn-7%%3A3gpp-service.ims.icsi.mmtel\";expires=600000\r\n",
              cuser, ruri, inst)) return 0;
    /* The INVITE/REGISTER is sent directly to the P-CSCF address (outbound
     * proxy) on the transport; no Route header is needed and adding one that
     * points at the same P-CSCF caused the CP/P-CSCF to reject the request.
     * (Live: with a direct R-URI-to-domain REGISTER the P-CSCF responded 480
     *  "user unavailable" for an unknown IMPU instead of 403.) */
    /* Netherlands LTE (KPN) is FDD, not TDD. A wrong access type is rejected. */
    if (!addf(&r,"P-Access-Network-Info: 3GPP-E-UTRAN-FDD;utran-cell-id-3gpp=00000000\r\n")) return 0;
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
        if (!addf(&r,"Security-Client: %s\r\n", sec_offer)) return 0;
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
    if (strcmp(alg,"AKAv1-MD5")!=0 && strcmp(alg,"AKAv2-MD5")!=0) return false;
    /* cnonce: deterministic privacy-safe token (real impl uses RANDOM). */
    snprintf(cnonce,16,"%x",0x6e75786cU); /* "nuxel" */
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
    const char *colon=strchr(a1user,'@');
    /* A1 username is the private identity (IMPI), not the full sip: URI. */
    char username[128]={0};
    if (colon && colon>a1user && (size_t)(colon-a1user)<sizeof username) {
        memcpy(username,a1user,(size_t)(colon-a1user)); username[colon-a1user]=0;
    } else snprintf(username,sizeof username,"%s",a1user);
    const char *pp[]={username,p->realm?p->realm:"",a1};
    if (!md5cathex(pp,3,ha1)) return 0;
    const char *a2u=p->uri?p->uri:""; const char *m=p->method?p->method:"REGISTER";
    const char *pa2[]={m,a2u};
    if (!md5cathex(pa2,2,ha2)) return 0;
    const char *nc="00000001";
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
    struct buf b={out,cap,0};
    if (!addf(&b,"MESSAGE sip:%s SIP/2.0\r\n", to)) return 0;
    if (!addf(&b,"Via: SIP/2.0/UDP nuxel;branch=z9hG4bKmsg%u\r\n", (unsigned)tag)) return 0;
    if (!addf(&b,"Max-Forwards: 70\r\n")) return 0;
    if (!addf(&b,"From: <%s>\r\n", from)) return 0;
    if (!addf(&b,"To: <%s>\r\n", to)) return 0;
    if (!addf(&b,"Call-ID: nuxel-msg-%u\r\n", (unsigned)tag)) return 0;
    if (!addf(&b,"CSeq: 1 MESSAGE\r\n")) return 0;
    if (route_uri && *route_uri) { if (!addf(&b,"Route: <%s;lr>\r\n", route_uri)) return 0; }
    if (!addf(&b,"P-Asserted-Identity: <%s>\r\n", impu)) return 0;
    if (!addf(&b,"Content-Type: application/vnd.3gpp.sms\r\n")) return 0;
    if (!addf(&b,"Content-Length: %u\r\n\r\n", (unsigned)body_len)) return 0;
    if (!addn(&b,body,body_len)) return 0;
    return b.len;
}
