/* SPDX-License-Identifier: GPL-2.0-only
 *
 * ims_sip.h — bounded SIP/IMS wire codec for TS 24.229 REGISTER and
 * TS 24.341 SMS-over-IP (SIP MESSAGE). Pure C, no PJSIP runtime dependency:
 * the build/parse primitives are independently testable and are the exact
 * message surface the native registration backend emits/consumes.
 *
 * These functions never perform a network I/O or claim registration success.
 * They only serialize/parse well-formed requests and challenges. RAND/AUTN
 * and RES/CK/IK are session secret material and are never logged.
 */
#ifndef NUXEL_IMS_SIP_H
#define NUXEL_IMS_SIP_H
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

/* RFC 2617 MD5 digest hex output (SIP digest doesn't truncate). */
struct ims_sip_digest_params {
    const char *impu;      /* public identity (sip:...) */
    const char *realm;
    const char *nonce;     /* base64(RAND||AUTN) for AKA, server nonce otherwise */
    const char *cnonce;
    const char *method;    /* "REGISTER" / "MESSAGE" */
    const char *uri;       /* request-URI */
    const char *response;  /* base64(RES) from the SIM AUTHENTICATE result */
};

/* Serialize a privacy-safe REGISTER request. `pcscf` is the P-CSCF address;
 * `impu` the public identity; `impi` the derived private identity (username).
 * `port` is the local SIP port; `sec` is the ipsec-3gpp Security-Client
 * offer string (e.g. "ipsec-3gpp;alg=...;port-c=...;port-s=...") or NULL.
 * Returns bytes written, 0 on bounds error. Never includes RAND/AUTN or RES. */
size_t ims_sip_register_build(char *out, size_t cap,
                              const char *impu, const char *impi,
                              const char *pcscf, const char *local_ip,
                              uint16_t port, const char *sec_offer);
/* Same as ims_sip_register_build but advertises a real device +sip.instance
 * (RFC 5626) from a 15-digit IMEI when supplied/NUL-valid; otherwise a
 * syntactically valid all-zero URN is used. The IMEI is a device identifier,
 * never a secret; it is not logged. */
size_t ims_sip_register_build_ex(char *out, size_t cap,
                                 const char *impu, const char *impi,
                                 const char *pcscf, const char *local_ip,
                                 uint16_t port, const char *sec_offer,
                                 const char *imei);
/* Full variant: `cell_id` is a REAL E-UTRAN cell identity (hex string) for the
 * utran-cell-id-3gpp parameter, or NULL/"" when genuinely unavailable. When
 * NULL the parameter is OMITTED entirely (TS 24.229 7.2A.4 / RFC 3455 4.1):
 * a fabricated all-zero cell id must never be transmitted. */
size_t ims_sip_register_build_ex2(char *out, size_t cap,
                                  const char *impu, const char *impi,
                                  const char *pcscf, const char *local_ip,
                                  uint16_t port, const char *sec_offer,
                                  const char *imei, const char *cell_id);
/* Fullest variant: adds the serving PLMN (5 ASCII digits, e.g. "20408") so
 * utran-cell-id-3gpp can be emitted as (MCC||MNC)||ECI per TS 24.229 7.2A.2.
 * The parameter is emitted ONLY when BOTH home_plmn (5 digits) and a valid hex
 * cell_id are present; otherwise it is omitted (never fabricated/partial). */
size_t ims_sip_register_build_ex3(char *out, size_t cap,
                                  const char *impu, const char *impi,
                                  const char *pcscf, const char *local_ip,
                                  uint16_t port, const char *sec_offer,
                                  const char *imei, const char *cell_id,
                                  const char *home_plmn);
/* Security-first initial REGISTER: adds `Require: sec-agree` +
 * `Proxy-Require: sec-agree` to a REGISTER that already carries a complete
 * ipsec-3gpp Security-Client offer. Used for P-CSCFs that reject a plaintext
 * initial REGISTER (480) before the AKA challenge (TS 33.203 7.1). */
size_t ims_sip_register_build_secure(char *out, size_t cap, const char *impu,
                                     const char *impi, const char *pcscf,
                                     const char *local_ip, uint16_t port,
                                     const char *sec_offer, const char *imei,
                                     const char *cell_id);
size_t ims_sip_register_build_secure_ex3(char *out, size_t cap,
                                         const char *impu, const char *impi,
                                         const char *pcscf, const char *local_ip,
                                         uint16_t port, const char *sec_offer,
                                         const char *imei, const char *cell_id,
                                         const char *home_plmn);
/* Parse a 401/407 WWW-Authenticate challenge. Only AKAv1-MD5/AKAv2-MD5 and
 * qop=auth without integrity are accepted for IMS; MD5-only challenges are
 * rejected (IMS requires AKA). `nonce`/`realm`/`cnonce` are zero-terminated
 * outputs sized per caller. `nonce_raw` returns the decoded RAND||AUTN (32
 * bytes) when base64 is valid. */
bool ims_sip_challenge_parse(const char *hdr, size_t hdr_len,
                             char realm[64], char nonce[128], char qop[16],
                             char alg[24], char cnonce[16]);
/* Build the Authorization header after the SIM returns RES. Returns bytes
 * written (including trailing CRLF) or 0 on bounds error. Takes ownership of
 * none of the buffers. */
/* Optional Security-Server advertisement on a 401/407 (RFC 3329). When present
 * in the challenge and `sec_server` is non-NULL, the first ipsec-3gpp offer
 * is copied (bounded) so the UE can mirror it in a Security-Verify header and
 * install the matching IPsec SAs. Returns false if absent. */
bool ims_sip_security_server(const char *hdr, size_t hdr_len,
                             char *out, size_t outcap);

size_t ims_sip_authorization_build(char *out, size_t cap,
                                   const struct ims_sip_digest_params *p,
                                   bool is_aka);
/* Build a SIP MESSAGE carrying TS 24.011 RP-DATA as the binary body
 * application/vnd.3gpp.sms. `body`/`body_len` are the RP PDU from ims_sms. */
size_t ims_sip_message_build(char *out, size_t cap,
                             const char *impu, const char *to,
                             const char *from, const char *route_uri,
                             uint16_t tag, const void *body, size_t body_len);
/* Standards-compliant SIP MESSAGE builder (RFC 3261 / TS 24.341):
 *   - request-URI: `to` as given when it is a "sip:"/"tel:" URI; otherwise a
 *     raw E.164/MSISDN is encoded as "sip:<digits>@<home_domain>".
 *   - Via: real "SIP/2.0/UDP [<local_ip>]:<local_port>".
 *   - From with a tag + P-Preferred-Identity (UE-originated, NOT P-Asserted).
 *   - To without a tag; Route only when `route_uri` is a proper sip:/tel: URI
 *     with the ;lr flag (a bare host is wrapped as "sip:<host>;lr").
 * `home_domain` is the IMPU's host (used only to form a bare-number R-URI).
 * Returns bytes written, 0 on bounds error. Never logs the body. */
size_t ims_sip_message_build_ex(char *out, size_t cap,
                                const char *impu, const char *home_domain,
                                const char *to, const char *local_ip,
                                uint16_t local_port, const char *route_uri,
                                uint16_t tag, const void *body, size_t body_len);
/* Bounded parse of a SIPS response. Extracts the status class (1..6; 0 if the
 * datagram is not a SIPS response), the numeric status code (0 if absent), the
 * CSeq method token (up to 15 bytes; empty if absent) and the body length
 * (from Content-Length when present, else the bytes after the header
 * terminator). Only the request-correlating fields (code + CSeq method) are
 * surfaced; no identities, tags or bodies are retained. */
struct ims_sip_response {
    int      code;              /* 100..699, or 0 when not a SIPS response */
    char     cseq_method[16];   /* "MESSAGE"/"REGISTER"/..; empty if absent */
    unsigned body_len;
    bool     have_content_length;
};
bool ims_sip_response_parse(const void *msg, size_t len, struct ims_sip_response *out);
/* Companion base64 helpers used by challenge/nonce framing. */
size_t ims_base64_encode(const uint8_t *in, size_t in_len, char *out, size_t cap);
bool   ims_base64_decode(const char *in, size_t in_len, uint8_t *out, size_t cap, size_t *out_len);
#endif
