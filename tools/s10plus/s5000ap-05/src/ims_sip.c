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
    return ims_sip_register_build_ex2(out, cap, impu, impi, pcscf, local_ip,
                                      port, sec_offer, NULL, NULL);
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
    return ims_sip_register_build_ex2(out, cap, impu, impi, pcscf, local_ip,
                                      port, sec_offer, imei, NULL);
}

static size_t ims_sip_register_build_core(char *out, size_t cap,
                                          const char *impu, const char *impi,
                                          const char *pcscf, const char *local_ip,
                                          uint16_t port, const char *sec_offer,
                                          const char *imei, const char *cell_id,
                                          const char *home_plmn,
                                          bool require_sec_agree);

size_t ims_sip_register_build_ex2(char *out, size_t cap, const char *impu,
                                  const char *impi, const char *pcscf,
                                  const char *local_ip, uint16_t port,
                                  const char *sec_offer, const char *imei,
                                  const char *cell_id)
{
    return ims_sip_register_build_core(out, cap, impu, impi, pcscf, local_ip,
                                       port, sec_offer, imei, cell_id, NULL, false);
}
size_t ims_sip_register_build_ex3(char *out, size_t cap, const char *impu,
                                  const char *impi, const char *pcscf,
                                  const char *local_ip, uint16_t port,
                                  const char *sec_offer, const char *imei,
                                  const char *cell_id, const char *home_plmn)
{
    return ims_sip_register_build_core(out, cap, impu, impi, pcscf, local_ip,
                                       port, sec_offer, imei, cell_id, home_plmn,
                                       false);
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
                                       port, sec_offer, imei, cell_id, NULL, true);
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
                                       true);
}

static size_t ims_sip_register_build_core(char *out, size_t cap,
                                          const char *impu, const char *impi,
                                          const char *pcscf, const char *local_ip,
                                          uint16_t port, const char *sec_offer,
                                          const char *imei, const char *cell_id,
                                          const char *home_plmn,
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
    /* RFC 3261 19.1.1 permits a bracketed IPv6 host in a SIP URI authority
     * ("sip:user@[2001:db8::1]:5062"). The Contact MUST be the UE's own
     * reachable address (TS 24.229 5.1.1.2 / registrar reachability), so use
     * the real local IMS IP + port. The previous IMPU-domain host made the
     * Contact unreachable, which a reachability-checking registrar rejects. */
    if (strchr(local_ip, ':')) {
        if (!addf(&r,"Contact: <sip:%s@[%s]:%u;transport=udp>;+sip.instance=\"<%s>\";"
                  "+g.3gpp.icsi-ref=\"urn%%3Aurn-7%%3A3gpp-service.ims.icsi.mmtel\";expires=600000\r\n",
                  cuser, local_ip, (unsigned)port, inst)) return 0;
    } else {
        if (!addf(&r,"Contact: <sip:%s@%s:%u;transport=udp>;+sip.instance=\"<%s>\";"
                  "+g.3gpp.icsi-ref=\"urn%%3Aurn-7%%3A3gpp-service.ims.icsi.mmtel\";expires=600000\r\n",
                  cuser, local_ip, (unsigned)port, inst)) return 0;
    }
    /* The INVITE/REGISTER is sent directly to the P-CSCF address (outbound
     * proxy) on the transport; no Route header is needed and adding one that
     * points at the same P-CSCF caused the CP/P-CSCF to reject the request.
     * (Live: with a direct R-URI-to-domain REGISTER the P-CSCF responded 480
     *  "user unavailable" for an unknown IMPU instead of 403.) */
    /* Netherlands LTE (KPN) is FDD, not TDD. The utran-cell-id-3gpp parameter
     * is emitted ONLY when a REAL serving-cell identity is available. It is
     * OMITTED (not fabricated) otherwise: TS 24.229 7.2A.4 / RFC 3455 4.1
     * allow the parameter to be absent, and a bogus all-zero ECI is a
     * interoperability hazard. This CP's IPC41 serving-network frame carries
     * no ECI (the real one is behind the OEM-socket GetLteCellInfo), so in
     * production this is normally omitted. */
    bool cell_ok = cell_id && *cell_id;
    if (cell_ok) {
        for (const char *q = cell_id; *q; q++)
            if (!((*q >= '0' && *q <= '9') || (*q >= 'a' && *q <= 'f') ||
                  (*q >= 'A' && *q <= 'F'))) { cell_ok = false; break; }
        if (cell_ok && strlen(cell_id) > 16) cell_ok = false;
    }
    /* TS 24.229 7.2A.2 / RFC 3455 4.1: utran-cell-id-3gpp =
     *   (MCC||MNC) joined with the 28-bit ECI in 7 hex octets.
     * The ECI is always present in this value (the parameter is "cell-id"),
     * so we require BOTH a real PLMN (home_plmn, from NET 8/3) AND a real,
     * non-zero ECI (from NET 8/17) before emitting it. If EITHER is missing,
     * the cell-id parameter is OMITTED entirely (3GPP-E-UTRAN-FDD alone), which
     * TS 24.229 permits; we never emit a fabricated 00000000 ECI and never
     * splice a partial value. */
    bool plmn_ok = home_plmn && strlen(home_plmn) >= 5;
    if (plmn_ok) {
        for (const char *q = home_plmn; q < home_plmn + 5; q++)
            if (*q < '0' || *q > '9') { plmn_ok = false; break; }
    }
    if (cell_ok && plmn_ok) {
        if (!addf(&r,"P-Access-Network-Info: 3GPP-E-UTRAN-FDD;utran-cell-id-3gpp=%.5s%s\r\n",
                  home_plmn, cell_id)) return 0;
    } else {
        if (!addf(&r,"P-Access-Network-Info: 3GPP-E-UTRAN-FDD\r\n")) return 0;
    }
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
    struct buf b={out,cap,0};
    if (!addf(&b,"MESSAGE %s SIP/2.0\r\n", ruri)) return 0;
    if (local_ip && *local_ip) {
        if (strchr(local_ip, ':'))
            { if (!addf(&b,"Via: SIP/2.0/UDP [%s]:%u;branch=z9hG4bKmsg%u\r\n",
                        local_ip, (unsigned)local_port, (unsigned)tag)) return 0; }
        else
            { if (!addf(&b,"Via: SIP/2.0/UDP %s:%u;branch=z9hG4bKmsg%u\r\n",
                        local_ip, (unsigned)local_port, (unsigned)tag)) return 0; }
    } else {
        if (!addf(&b,"Via: SIP/2.0/UDP ims;branch=z9hG4bKmsg%u\r\n", (unsigned)tag)) return 0;
    }
    if (!addf(&b,"Max-Forwards: 70\r\n")) return 0;
    /* From carries an originator tag; To has none (it is the callee). */
    if (!addf(&b,"From: <%s>;tag=nuxel%u\r\n", impu, (unsigned)tag)) return 0;
    if (!addf(&b,"To: <%s>\r\n", ruri)) return 0;
    if (!addf(&b,"Call-ID: nuxel-msg-%u\r\n", (unsigned)tag)) return 0;
    if (!addf(&b,"CSeq: 1 MESSAGE\r\n")) return 0;
    /* Route: only a real sip:/tel: URI is used; a bare host is wrapped with an
     * explicit scheme and the loose-route ;lr flag (RFC 3261 8.1.2). */
    if (route_uri && *route_uri) {
        if (!strncmp(route_uri, "sip:", 4) || !strncmp(route_uri, "tel:", 4)) {
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
