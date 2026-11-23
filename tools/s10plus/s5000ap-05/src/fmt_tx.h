/*
 * fmt_tx.h — S5000AP IpcProtocol41 FMT **transmit** serialization.
 *
 * SPDX-License-Identifier: GPL-2.0-only
 *
 * This module builds AP->CP FMT messages using the SAME on-wire framing the
 * CP expects for RX: the 7-byte `struct sipc_fmt_hdr`
 *
 *     [u16 total_len LE][u8 msg_seq][u8 ack_seq][u8 main][u8 sub][u8 type]
 *     [payload...]
 *
 * total_len == 7 + payload_len.
 *
 * SAFETY: these builders only SERIALIZE bytes into a caller buffer. They never
 * open a device or transmit. A separate, explicitly-authorized caller decides
 * whether and when to write a frame, and every write is bounded + policy-gated.
 *
 * Only commands whose payload layout is recovered from the exact vendor RIL
 * (IpcTx* disassembly) are exposed. Unknown/guessed fields are NOT emitted.
 */
#ifndef NUXEL_FMT_TX_H
#define NUXEL_FMT_TX_H

#include <stdint.h>
#include <stddef.h>
#include <stdbool.h>

/* worst-case FMT frame this module can build (326-byte SyncProfileInfo + slack) */
#define FMT_TX_MAX_FRAME 512u

/* cmd_type numeric classes (vendor enum; see ipc41_cmdmap.h) */
#define FMT_TX_TYPE_REQUEST       2u
#define FMT_TX_TYPE_NOTIFICATION  3u

/* Samsung DataProtocol (IP family) enum numeric values (recovered) */
enum fmt_tx_data_protocol {
    /* Vendor DataProtocol enum (libsec-ril, VERIFIED @0x31f580/@0x31ff48):
     * IP=2, IPV6=3, IPV4V6=4. Wire byte = 0x00040605 >> ((proto-2)*8):
     * IP(2)=0x05, IPV6(3)=0x06, IPV4V6(4)=0x04. */
    FMT_TX_PROTO_IP      = 2,
    FMT_TX_PROTO_IPV6    = 3,
    FMT_TX_PROTO_IPV4V6  = 4,
};

/* DataAuth numeric codes (VERIFIED from helper @31fe28):
 * NONE -> 1 (returns 1 for the "no auth" enum). This is the ONLY value we
 * currently authorize for transmission (owner-approved internet APN). */
#define FMT_TX_AUTH_NONE 1u

/*
 * RadioTechnologyType numeric values (VERIFIED: NetworkManager::GetGeneration
 * @0x1f7ce8 indexes an 18-entry table = Android RADIO_TECH enum 1..17).
 * LTE = 14. This is the ONLY RAT we authorize for the LTE internet attach.
 */
#define FMT_TX_RAT_LTE 14u

/* A serialized frame (header + payload). */
struct fmt_tx_frame {
    uint8_t  buf[FMT_TX_MAX_FRAME];
    size_t   len;            /* total bytes = 7 + payload_len */
    uint8_t  main_cmd;
    uint8_t  sub_cmd;
    uint8_t  cmd_type;
};

/* Write the 7-byte sipc_fmt_hdr into buf and return payload pointer.
 * payload_len must be validated by the caller; returns NULL on overflow. */
uint8_t *fmt_tx_begin(struct fmt_tx_frame *f, uint8_t main, uint8_t sub,
                      uint8_t type, size_t payload_len);

/* ---- SIM / security commands (AP -> CP requests) ---- */

/* Query SIM application status. No payload (len=7). */
bool fmt_tx_get_sim_status(struct fmt_tx_frame *f);

/* Query SIM ATR info. No payload (len=7). */
bool fmt_tx_get_atr(struct fmt_tx_frame *f);

/* ---- NET / registration commands (AP -> CP requests) ---- */

/* Query serving network / registration. No payload. */
bool fmt_tx_get_serving_network(struct fmt_tx_frame *f);
bool fmt_tx_get_registration(struct fmt_tx_frame *f);

/* Query PS/data registration state (source: IpcTxNetGetDataRegState @0x335b00).
 * 9-byte NET(NET_REGIST sub=5) request with a 2-byte payload. This is the
 * vendor's data-registration query and is distinct from the 7-byte voice
 * NET_REGIST query above. */
bool fmt_tx_get_data_reg_state(struct fmt_tx_frame *f);

/* ---- GPRS / data-path commands (AP -> CP requests) ---- */

/* GPRS PS attach/detach (main=13 sub=3, 3-byte payload).
 * attach: 1=attach, 0=detach. detach_reason: 0..4 (clamped). */
bool fmt_tx_ps_attach(struct fmt_tx_frame *f, bool attach, bool suspend,
                      uint8_t detach_reason);

/* GPRS get PDP context (query, no payload). */
bool fmt_tx_get_pdp_context(struct fmt_tx_frame *f);

/* GPRS sync FULL data profile (sub=37, 326-byte frame). This is the real
 * full-profile sync incl. RAT (IpcTxSyncProfileInfo @0x31fb48). */
bool fmt_tx_sync_profile_info(struct fmt_tx_frame *f, const char *apn,
                              uint8_t auth_code, uint8_t proto);

/* GPRS sync profile / mobile-data (sub=29) enable/disable (9-byte frame). */
bool fmt_tx_mobile_data(struct fmt_tx_frame *f, bool enable, bool extra);

/* GPRS define PDP context (134-byte frame, APN + protocol). */
bool fmt_tx_define_pdp_context(struct fmt_tx_frame *f, const char *apn,
                               uint8_t proto, uint8_t profile_id);

/* GPRS data-call establish (main=3 CDMA_DATA, sub=2 CDMA_DATA_CALL_ESTABLISH). */
bool fmt_tx_set_data_call_establish(struct fmt_tx_frame *f, bool establish);

/* GPRS set data profile / sync profile (main=13 GPRS, sub=27 SET_DATA_PROFILE).
 * 203-byte frame; COMPLETE layout recovered — see fmt_tx.c. */
bool fmt_tx_set_data_profile(struct fmt_tx_frame *f, const char *apn,
                             uint8_t auth_code, uint8_t proto);

/* GPRS LTE attach profile (main=13 GPRS, sub=20 SET_LTE_ATTACH_PROFILE).
 * 201-byte frame; COMPLETE layout recovered from IpcTxSetLteAttachProfile
 * @0x320238 — see fmt_tx.c. This prepares the CP for LTE PS attach.
 * `flag` is payload[0] (3 = set data profile; 1 = set initial-attach APN). */
bool fmt_tx_set_lte_attach_profile(struct fmt_tx_frame *f, const char *apn,
                                   uint8_t auth_code, uint8_t proto, uint8_t cid,
                                   uint8_t flag);

/* GPRS set PDP context / ACTIVATE (main=13 GPRS, sub=4). The REAL LTE PDP
 * activation command (112-byte frame) recovered from IpcTxSetPdpContext
 * @0x31f6e0 — see fmt_tx.c. */
bool fmt_tx_set_pdp_context(struct fmt_tx_frame *f, const char *apn,
                            uint8_t auth_code, uint8_t proto, uint8_t cid);

/* GPRS always-on PDN (main=13 GPRS, sub=34 SET_ALWAYS_ON_PDN). */
bool fmt_tx_set_always_on_pdn(struct fmt_tx_frame *f, bool enable, uint8_t profile);

/* Serialize a raw FMT frame given explicit fields (validation helper). */
bool fmt_tx_raw(struct fmt_tx_frame *f, uint8_t main, uint8_t sub,
                uint8_t type, const uint8_t *payload, size_t payload_len);

#endif /* NUXEL_FMT_TX_H */

/* ---- NET service-domain / preferred-network-type commands (AP -> CP) ---- */

/* NET service domain config (source: IpcTxNetSetServiceDomain @0x336dc8).
 * main=8 sub=8(0x08) type=3, 8-byte frame, payload=[domain].
 * NetServiceDomainType: 1=CS_ONLY, 2=CS_PS (voice+data), 3=PS_ONLY. The vendor
 * default for a normal LTE attach is CS_PS (2), which is REQUIRED before the
 * GPRS/data path will accept a PS attach. */
bool fmt_tx_set_service_domain(struct fmt_tx_frame *f, uint8_t domain);

/* NET preferred network type / network mode select (source:
 * IpcTxNetSetPreferredNetType @0x335e00). main=8 sub=10(0x0a) type=3,
 * 8-byte frame, payload=[PreferredNetType]. 9 = LTE/WCDMA/GSM auto (Android
 * RIL_PREFERRED_NETWORK_MODE_LTE_WCDMA_GSM), the S10+ default LTE mode. */
bool fmt_tx_set_preferred_net_type(struct fmt_tx_frame *f, uint8_t net_type);

/* Service-domain and preferred-network-type value constants. */
#define FMT_TX_SERVICE_DOMAIN_CS_PS  2u  /* voice + data both enabled */
#define FMT_TX_PREFERRED_NET_LTE_AUTO 9u  /* LTE/WCDMA/GSM auto */
#define FMT_TX_PDP_TYPE_LTE 3u            /* AccessNetworkType EUTRAN (LTE) */
