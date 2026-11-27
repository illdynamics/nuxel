/* SPDX-License-Identifier: GPL-2.0-only
 *
 * ims_iil_rx.h — native IIL (IpcProtocol41Iil) RECEIVE-path parser and
 * event state machine. Complements ims_iil.{c,h} (TX serializer).
 *
 * The IIL endpoint delivers the stock IMS bearer/registration/auth/SMS
 * events to the AP over /dev/umts_ipc0 (channel 0xEB) using the 7-byte IIL
 * header [u16 total_len][u16 msg_seq][u8 main][u8 sub][u8 type]. It is
 * distinct from the FMT header (which uses u8 msg_seq + u8 ack_seq).
 *
 * Authoritative vendor RX handlers (round17.md; recovered from libsec-ril.so
 * build 60889dd714394ae0db7c2ecc2bf2740f, IpcRxIil dispatch @0x356c18):
 *   sub 1  IpcRxSmsIncomingMsg @0x356d08 — SMS-over-IP RP-DATA
 *   sub 2  IpcRxIilPreference  @0x356628 — IMS preference (SMS-over-IP fmt)
 *   sub 4  IpcRxIilParameters  @0x356800 — vendor STUB (returns 0; ignored)
 *   sub 7  IpcRxIilRegistration @0x356528 — IMS registration state + IMPU
 *   sub 17 IpcRxIilIsimAuth    @0x356808 — AKA challenge (RAND@[1], AUTN@[17])
 *   sub 22 IpcRxIilConnected   @0x356870 — connect notification (event 123)
 *   sub 23 IpcRxIilChangePreferredNetwork
 *   sub 24 IpcRxIilEpdgConfiguration
 *   sub 20 IpcRxIilDeregistration (stub)
 * Subcodes 8,9,10,11,12..16,18,19,21 are UNHANDLED by the CP.
 *
 * This parser is BOUNDED and fail-closed. It NEVER logs subscriber auth
 * material (RAND/AUTN/RES/CK/IK) or PII.
 */
#ifndef NUXEL_IMS_IIL_RX_H
#define NUXEL_IMS_IIL_RX_H
#include <stdint.h>
#include <stddef.h>
#include <stdbool.h>

#define IIL_RX_MAX_FRAME 1024u

/* IIL main_cmd values (mirror ims_iil.h) */
#define IIL_MAIN_IIL    112u
#define IIL_MAIN_SMS_RP   4u
#define IIL_MAIN_GPRS    13u

/* IIL sub_cmd values recovered from the AUTHORITATIVE vendor dispatch:
 * IpcProtocol41Iil::IpcRxIil @0x356c18 jump table @0x14acbd (indexed by
 * sub-1) resolved through _ZTV16IpcProtocol41Iil @0x3a9a60. See round17.md.
 * A previous revision used CONNECTED=10/PARAMETERS=8/ISIM_AUTH=9/
 * REGISTRATION=4/PREFERENCE=11/SMS_INCOMING=21, which are all UNHANDLED by
 * the CP and could never decode a live event. Corrected values: */
#define IIL_SUB_SMS_INCOMING  1u   /* -> IpcRxSmsIncomingMsg */
#define IIL_SUB_PREFERENCE    2u   /* -> IpcRxIilPreference (SMS-over-IP fmt) */
#define IIL_SUB_PARAMETERS    4u   /* -> IpcRxIilParameters (vendor STUB, ignored) */
#define IIL_SUB_IIL           6u   /* -> IpcRxIil */
#define IIL_SUB_REGISTRATION  7u   /* -> IpcRxIilRegistration */
#define IIL_SUB_ISIM_AUTH    17u   /* -> IpcRxIilIsimAuth (RAND/AUTN) */
#define IIL_SUB_DEREGISTRATION 20u /* -> IpcRxIilDeregistration (stub) */
#define IIL_SUB_CONNECTED    22u   /* -> IpcRxIilConnected (event code 123) */
#define IIL_SUB_CHANGE_PREF_NET 23u /* -> IpcRxIilChangePreferredNetwork */
#define IIL_SUB_EPDG_CONFIG  24u   /* -> IpcRxIilEpdgConfiguration */
#define IIL_SUB_SMS          IIL_SUB_SMS_INCOMING /* alias */
/* Legacy 16-bit SIPC main for the SMS/RP family still observed. */
#define IIL_MAIN_SMS_RP_LEGACY 22u

struct iil_rx_event {
    uint16_t msg_seq;
    uint8_t  main_cmd;
    uint8_t  sub_cmd;
    uint8_t  cmd_type;
    const uint8_t *payload;
    size_t   payload_len;
};

/* Parse ONE complete IIL frame from `buf` (which begins with the 7-byte IIL
 * header). Returns consumed bytes on OK, 0 on incomplete (need more bytes),
 * or negative on malformed. `out` is filled only on OK.
 * The IIL header has a 16-bit msg_seq (no ack_seq), unlike FMT. */
int iil_rx_parse(const uint8_t *buf, size_t len, struct iil_rx_event *out,
                 size_t *consumed);

/* --- semantic decoders (bounded, fail-closed) --- */

/* IpcRxIilConnected: IMS bearer connect notification. Carries the IMS CID and
 * whether the PDN attached. `cid` output is the context id (2 for IMS). */
bool iil_rx_connected(const struct iil_rx_event *e, uint8_t *cid, bool *attached);

/* IpcRxIilParameters: carries IMS IP configuration + P-CSCF address list.
 * Fills `family` (AF_INET/AF_INET6), `ip`, `prefix`, and up to `n` P-CSCF
 * addresses with their lengths. Returns false on malformed input. */
bool iil_rx_parameters(const struct iil_rx_event *e, int *family,
                       uint8_t ip[16], uint8_t *prefix,
                       uint8_t pcscf[][16], uint8_t *pcscf_len,
                       unsigned max_pcscf, unsigned *pcscf_count);

/* IpcRxIilIsimAuth: AKA challenge. Extracts RAND(16)+AUTN(16). NEVER logged. */
bool iil_rx_isim_auth(const struct iil_rx_event *e,
                      uint8_t rand[16], uint8_t autn[16]);

/* IpcRxIilRegistration (sub 7): IMS registration status. Returns the
 * ImsRegStatus byte (payload[0]) or -1 if not a Registration event.
 * 1=REGISTERED, 2=REGISTERING, 3=NOT_REGISTERED, (vendor clamps 1..5).
 * Optionally copies the operator/modem-provisioned IMPU (public identity,
 * NOT a secret/PII credential) from payload[10+1..] into `impu` (bounded,
 * printable-only). The IMPU is never logged in full by the caller. */
int iil_rx_registration(const struct iil_rx_event *e, int *status,
                        char *impu, size_t impu_cap);

/* IpcRxIilPreference: SMS-over-IP preference/format from the network. */
bool iil_rx_preference(const struct iil_rx_event *e, uint8_t *sms_over_ip_fmt);

/* IpcRxSmsIncomingMsg: inbound SMS-over-IP RP-DATA notification. Returns a
 * pointer/length to the RP PDU body (application/vnd.3gpp.sms) for ims_rp. */
bool iil_rx_sms_incoming(const struct iil_rx_event *e,
                         const uint8_t **rp, size_t *rp_len);

#endif /* NUXEL_IMS_IIL_RX_H */
