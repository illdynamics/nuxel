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

/* Includes the vendor's fixed 711-byte OES certificate event frame. */
#define FMT_TX_MAX_FRAME 1024u

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

/* DataAuth enum from the vendor function signatures. */
#define FMT_TX_AUTH_NONE 0u
#define FMT_TX_AUTH_PAP  1u
#define FMT_TX_AUTH_CHAP 2u
#define FMT_TX_AUTH_PAP_OR_CHAP 3u

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
/* SEC_SIM_ICC_TYPE (main=5 sub=7) request: USIM/ISIM application presence. */
bool fmt_tx_get_sim_icc_type(struct fmt_tx_frame *f);
/* SEC_SIMAPPS_INFO (main=5 sub=15) request: authoritative SIM application inventory. */
bool fmt_tx_get_sim_apps_info(struct fmt_tx_frame *f);
/* IMSI response is used only for known home-PLMN classification. Never log it. */
bool fmt_tx_get_sim_network(struct fmt_tx_frame *f);
/* CP GET handler 0x4121a43c returns {PS attached, suspend state}. */
bool fmt_tx_get_ps_attach(struct fmt_tx_frame *f);
bool fmt_tx_get_baseband_version(struct fmt_tx_frame *f);
/* RF on/off, not CP boot/reset. IpcTxRadioPower @0x33fa80. */
bool fmt_tx_radio_power(struct fmt_tx_frame *f, bool on);
bool fmt_tx_net_selection_auto(struct fmt_tx_frame *f);
/* OES startup exchange, vendor IpcTxCfrm/EventDrkCpInfo. No EFS writes. */
#define FMT_TX_OES_CERT_CHUNK 700u
bool fmt_tx_oes_confirm(struct fmt_tx_frame *f);
bool fmt_tx_oes_certificate(struct fmt_tx_frame *f, uint8_t result, uint8_t index,
                             const uint8_t *data, size_t len);

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
bool fmt_tx_release_pdp_context(struct fmt_tx_frame *f, uint8_t cid);
/* Read definitions (APN/protocol), distinct from sub=4's active-state list.
 * EFUJ2 CP dispatch +0x18 and GET handler 0x41301c56; no payload. */
bool fmt_tx_get_pdp_definitions(struct fmt_tx_frame *f);

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
                            uint8_t auth_code, uint8_t proto, uint8_t cid,
                            uint8_t pdp_type_wire);

/* GPRS always-on PDN (main=13 GPRS, sub=34 SET_ALWAYS_ON_PDN). */
bool fmt_tx_set_always_on_pdn(struct fmt_tx_frame *f, bool enable, uint8_t profile);

/* Serialize a raw FMT frame given explicit fields (validation helper). */
bool fmt_tx_raw(struct fmt_tx_frame *f, uint8_t main, uint8_t sub,
                uint8_t type, const uint8_t *payload, size_t payload_len);

/* ---- NET service-domain / preferred-network-type commands (AP -> CP) ---- */

/* NET service domain config (source: IpcTxNetSetServiceDomain @0x336dc8).
 * main=8 sub=8(0x08) type=3, 8-byte frame, payload=[domain].
 * Internal values 0=CS_PS, 1=PS_ONLY, 2=CS_ONLY; wire values 1,3,2. */
bool fmt_tx_set_service_domain(struct fmt_tx_frame *f, uint8_t domain);
bool fmt_tx_get_service_domain(struct fmt_tx_frame *f);

/* NET preferred network type / network mode select (source:
 * IpcTxNetSetPreferredNetType @0x335e00). main=8 sub=10(0x0a) type=3,
 * 8-byte frame, payload=[PreferredNetType]. 9 = LTE/WCDMA/GSM auto (Android
 * RIL_PREFERRED_NETWORK_MODE_LTE_WCDMA_GSM), the S10+ default LTE mode. */
bool fmt_tx_set_preferred_net_type(struct fmt_tx_frame *f, uint8_t net_type);
bool fmt_tx_get_preferred_net_type(struct fmt_tx_frame *f);

/* NET VoLTE/IMS state notification (source: IpcTxSetVolteStateNotification
 * @0x338578, libsec-ril 60889dd7). main=8 (NET) sub=52 (0x34 NET_VOLTE_STATE)
 * type=3, 8-byte frame, payload[0] = bool (1 = AP IMS/VoLTE stack ready).
 * Stock Samsung sends this from ModemProxy::SetVolteStateNotification(true)
 * when the AP's IMS stack is armed, BEFORE driving IMS registration. This is
 * the "IMS ready" signal the modem requires before it will emit the
 * authoritative IMS registration notification (main=22 sub=3). */
bool fmt_tx_set_volte_state_notification(struct fmt_tx_frame *f, bool ready);

/* NET HVOLTE test-mode (source: IpcTxGetVolteTestmode @0x338410 /
 * IpcTxSetVolteTestmode @0x3384c0). main=8 (NET) sub=40 (0x28
 * NET_HVOLTE_TESTMODE); type=2 request (get) / type=3 (set, 1-byte payload). */
bool fmt_tx_get_volte_testmode(struct fmt_tx_frame *f);
bool fmt_tx_set_volte_testmode(struct fmt_tx_frame *f, uint8_t mode);

/* NET_VOLTE_STATE / NET_HVOLTE_TESTMODE wire sub-command values. */
#define FMT_TX_NET_SUB_VOLTE_STATE   52u
#define FMT_TX_NET_SUB_HVOLTE_TESTMODE 40u
#define FMT_TX_VOLTE_STATE_READY 1u
#define FMT_TX_VOLTE_STATE_NOT_READY 0u

/* Service-domain and preferred-network-type value constants. */
#define FMT_TX_SERVICE_DOMAIN_CS_PS   0u
#define FMT_TX_SERVICE_DOMAIN_PS_ONLY 1u
#define FMT_TX_SERVICE_DOMAIN_CS_ONLY 2u
#define FMT_TX_PREFERRED_NET_LTE_AUTO 9u  /* LTE/WCDMA/GSM auto */
#define FMT_TX_PREFERRED_NET_LTE_ONLY 11u /* LTE only; wire mask 0x08 */
/* SetPdpContext payload[0] wire-byte selectors (VERIFIED this round from the
 * IpcTxSetPdpContext @0x31f6e0 jump table @0x149806; the value is a jump-table
 * selector, NOT "AccessNetworkType LTE = 3"):
 *   1 = full APN+user path (default internet bearer, flags 0x11 carry APN)
 *   2 = simple 3G/UTRAN
 *   4 = simple LTE/EUTRAN (payload[0]=4, flags=0, no APN)
 *   3 = simple (the PRIOR value; wire byte for 2nd-arg==2, NOT LTE).
 * The correct default for the "internet" APN ACTIVATE is 1 (full path). */ 
#define FMT_TX_PDP_TYPE_FULL 1u
#define FMT_TX_PDP_TYPE_LTE  4u
#define FMT_TX_PDP_TYPE_LEGACY 3u
#define FMT_TX_PDP_TYPE_DEFAULT FMT_TX_PDP_TYPE_FULL

 /* NUXEL_FMT_TX_H */

/* ---- IMS (main=22) command serializers (AP -> CP, modem-resident stack) ---- */

/* ImsRegStatus values the AP reports to the modem for registration drive. */
#define FMT_TX_IMS_REGSTATUS_NONE    0u
#define FMT_TX_IMS_REGSTATUS_REGISTERED 1u
#define FMT_TX_IMS_REGSTATUS_DEREG   2u

/* IpcTxImsReqSetRegState (main=22 sub=8, type=3, 6-byte payload).
 * VERIFIED byte layout (IpcProtocol41::IpcTxImsReqSetRegState @0x34d230 +
 * IpcModem::SetImsRegState @0x2fbe88, libsec-ril 60889dd7):
 *   payload[0] = ImsRegStatus   (arg1; 1=REGISTERED, 2=DEREG, 0=NONE)
 *   payload[1] = request flag   (arg2 int; 1=drive registration)
 *   payload[2] = NetworkType    (arg3; Android RADIO_TECH, LTE=14)
 *   payload[3] = EcmpState      (arg4)
 *   payload[4] = EpdgAvailableState (derived; 6 for LTE)
 *   payload[5] = int            (arg7, reserved)
 * The AP requests registration by asserting ImsRegStatus != NONE; the modem
 * autonomously performs the SIP REGISTER + AKA and reports the final state.
 * RadioTechnology (arg8) is consumed only to derive payload[4]; it is NOT
 * itself a payload byte.
 */
bool fmt_tx_ims_set_reg_state(struct fmt_tx_frame *f, uint8_t reg_status,
                              uint8_t network_type, uint8_t rat);

/* IpcTxImsAuthResp (main=22 sub=6). Forward a SIM AKA response to the modem.
 * `data`/`len` are the opaque AKA response the modem requested; no secret is
 * persisted or logged. */
bool fmt_tx_ims_auth_resp(struct fmt_tx_frame *f, const uint8_t *data, size_t len);

/* IpcTxImsReqDeregistration (main=22 sub=7). */
bool fmt_tx_ims_deregistration(struct fmt_tx_frame *f);
#endif

/* ---- MISC device capability (main=10 sub=45) ---- */

/* VoiceDomainPref wire values (Verizon-style PS/CS preference, recovered from
 * IpcTxSetDeviceCapa @0x331400 + DoCheckDeviceCapa @0x247550). The two args
 * are the home and roaming voice-domain preference. KPN 204-08 is LTE-only
 * with VoLTE/IMS, so PS (IMS) is the truthful capability for this handset. */
#define FMT_TX_VOICE_DOMAIN_CS_PS   0u
#define FMT_TX_VOICE_DOMAIN_PS_ONLY 1u
#define FMT_TX_VOICE_DOMAIN_CS_ONLY 2u

/* IpcTxGetDeviceCapa: main=10 (MISC), sub=45, type=2 (request), no payload.
 * Issued before SetDeviceCapa to trigger the modem capability handshake. */
bool fmt_tx_get_device_capa(struct fmt_tx_frame *f);

/* IpcTxSetDeviceCapa: main=10 (MISC), sub=45, type=3, payload=[pref1, pref2]. */
bool fmt_tx_set_device_capa(struct fmt_tx_frame *f, uint8_t pref1, uint8_t pref2);

/* ---- MISC IMS SDM (Service Domain Manager) settings (main=10) ----
 *
 * Recovered from Ipc41PacketBuilder / IpcTxSetImsSdmSettings (@0x32f0c0)
 * dispatch in libsec-ril 60889dd7. These arm the modem's IMS stack with the
 * supported SMS-over-IP format and IMS domain BEFORE registration is driven.
 * Each is a 1-or-more byte MISC notification; the modem acknowledges via the
 * ordinary GEN (main=128) response. No values are guessed; only documented
 * vendor wire bytes are emitted. */

/* IMS mode (sub=32): 0 = off, 1 = IMS enabled. */
#define FMT_TX_SDM_IMS_MODE_OFF 0u
#define FMT_TX_SDM_IMS_MODE_ON  1u

/* SmsOverIpFormat (sub=26, 1 byte) — the SMS-over-IP format selector.
 * Recovered from ImsPreference::SetPreference @0x2bf410 struct layout: the
 * SmsOverIpFormat field (offset 0xc) is written 2 in the vendor's IMS SMS
 * preference paths. Vendor enum: 0=UNKNOWN, 1=CSFB, 2=3GPP SMS-over-IMS. */
#define FMT_TX_SDM_SMSOVERIP_FORMAT_UNKNOWN 0u
#define FMT_TX_SDM_SMSOVERIP_FORMAT_CSFB    1u
#define FMT_TX_SDM_SMSOVERIP_FORMAT_3GPP    2u
bool fmt_tx_sdm_ims_sms_fmt(struct fmt_tx_frame *f, uint8_t fmt);

/* SMS-over-IP enable (sub=27, 1 byte): 0 = off, 1 = SMS-over-IP enabled. */
#define FMT_TX_SDM_SMSOVERIP_DISABLE 0u
#define FMT_TX_SDM_SMSOVERIP_ENABLE  1u
bool fmt_tx_sdm_ims_sms_over_ip(struct fmt_tx_frame *f, uint8_t enable);

/* IMS domain (sub=28, variable): the SIP/IMS domain FQDN. */
bool fmt_tx_sdm_ims_domain(struct fmt_tx_frame *f, const char *domain);

/* IMS mode (sub=32, 1 byte). */
bool fmt_tx_sdm_ims_mode(struct fmt_tx_frame *f, uint8_t mode);

/* P-CSCF (sub=34, variable): the P-CSCF FQDN/address. */
bool fmt_tx_sdm_pcscf(struct fmt_tx_frame *f, const char *pcscf);

/* GPRS set data profile with EXPLICIT vendor DataProfile type + profile label.
 * The default wrapper always advertises the DEFAULT internet profile
 * (ConvertProfileId(DEFAULT)=1, label "lte_internet"). The modem manages the
 * IMS/ePDN bearer itself when the IMS profile (DataProfile type 2, label
 * "ims", APN "ims...") is synced; the AP never drives a raw second CID.
 * Recovered from IpcTxSetDataProfile @0x31ff48 + DataCallList::GetCall(2)
 * in ImsPdnTriggered @0x28f0e0. */
bool fmt_tx_set_data_profile_ex(struct fmt_tx_frame *f, const char *apn,
                                uint8_t auth_code, uint8_t proto,
                                uint8_t profile_id, const char *label);
