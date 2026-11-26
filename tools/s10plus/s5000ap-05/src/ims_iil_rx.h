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
 * Recovered vendor RX handlers (see sms15.md for provenance; emulation/
 * disassembly verified):
 *   IpcRxIilRegistration @0x356528 (main=112)  — IMS registration state
 *   IpcRxIilIsimAuth     @0x356808 (main=112)  — AKA challenge (RAND/AUTN)
 *   IpcRxIilConnected    @0x356870 (main=112)  — IMS bearer connected + IP
 *   IpcRxIilParameters   @0x356800 (main=112)  — P-CSCF / IMS config
 *   IpcRxIilPreference   @0x356628 (main=112)  — IMS preference (SMS-over-IP fmt)
 *   IpcRxSms             @0x357018 / IpcRxSmsIncomingMsg @0x356d08 — SMS-in
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

/* IIL sub_cmd values recovered for the RX surface */
#define IIL_SUB_REGISTRATION  4u
#define IIL_SUB_PARAMETERS    8u
#define IIL_SUB_ISIM_AUTH     9u
#define IIL_SUB_CONNECTED    10u
#define IIL_SUB_PREFERENCE   11u
#define IIL_SUB_SMS_INCOMING 21u
#define IIL_SUB_SMS          22u

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

/* IpcRxIilRegistration: IMS registration state. `registered` = 1 when the
 * network confirms registration (200 OK relayed by modem), 0 otherwise. */
bool iil_rx_registration(const struct iil_rx_event *e, bool *registered);

/* IpcRxIilPreference: SMS-over-IP preference/format from the network. */
bool iil_rx_preference(const struct iil_rx_event *e, uint8_t *sms_over_ip_fmt);

/* IpcRxSmsIncomingMsg: inbound SMS-over-IP RP-DATA notification. Returns a
 * pointer/length to the RP PDU body (application/vnd.3gpp.sms) for ims_rp. */
bool iil_rx_sms_incoming(const struct iil_rx_event *e,
                         const uint8_t **rp, size_t *rp_len);

#endif /* NUXEL_IMS_IIL_RX_H */
