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
/* Companion base64 helpers used by challenge/nonce framing. */
size_t ims_base64_encode(const uint8_t *in, size_t in_len, char *out, size_t cap);
bool   ims_base64_decode(const char *in, size_t in_len, uint8_t *out, size_t cap, size_t *out_len);
#endif
