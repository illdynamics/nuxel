/*
 * fmt_tx.c — S5000AP IpcProtocol41 FMT transmit serialization.
 * SPDX-License-Identifier: GPL-2.0-only
 *
 * See fmt_tx.h for the framing-resolution rationale. This module is a pure
 * serializer: it builds byte-exact sipc_fmt_hdr + payload frames and NEVER
 * transmits. All layouts below are recovered from the exact vendor RIL
 * (vendor/lib64/libsec-ril.so, build 60889dd7) disassembly.
 */
#include "fmt_tx.h"
#include <string.h>

/* constant channel-independent command tables (main_cmd values) */
#define MAIN_GPRS  13u
#define MAIN_NET   8u
#define MAIN_SEC   5u

bool fmt_tx_get_baseband_version(struct fmt_tx_frame *f)
{
    const uint8_t flags = 0xff;
    return fmt_tx_raw(f, 10, 1, 2, &flags, 1);
}

bool fmt_tx_radio_power(struct fmt_tx_frame *f, bool on)
{
    /* Vendor enum ON=2, OFF=1; normal (non-carrier-override) state payload. */
    const uint8_t p[] = {on ? 2 : 1, on ? 2 : 0};
    return fmt_tx_raw(f, 1, 7, 1, p, sizeof p);
}

bool fmt_tx_net_selection_auto(struct fmt_tx_frame *f)
{
    const uint8_t p[] = {2, 0, 0, 0, 0, 0, 0, 0xff};
    return fmt_tx_raw(f, 8, 2, 3, p, sizeof p);
}

bool fmt_tx_oes_confirm(struct fmt_tx_frame *f)
{
    return fmt_tx_begin(f, 38, 1, 4, 0) != NULL;
}

bool fmt_tx_oes_certificate(struct fmt_tx_frame *f, uint8_t result, uint8_t index,
                             const uint8_t *data, size_t len)
{
    if (len > FMT_TX_OES_CERT_CHUNK || (len && !data) || result > 1 ||
        (result && (len || index))) return false;
    uint8_t *p = fmt_tx_begin(f, 38, 1, 5, FMT_TX_OES_CERT_CHUNK + 4);
    if (!p) return false;
    memset(p, 0, FMT_TX_OES_CERT_CHUNK + 4);
    p[0] = (uint8_t)(len + 2); p[1] = (uint8_t)((len + 2) >> 8);
    p[2] = result; p[3] = index;
    if (len) memcpy(p+4, data, len);
    return true;
}

uint8_t *fmt_tx_begin(struct fmt_tx_frame *f, uint8_t main, uint8_t sub,
                      uint8_t type, size_t payload_len)
{
    if (!f || payload_len > FMT_TX_MAX_FRAME - 7u) return NULL;
    f->main_cmd = main;
    f->sub_cmd  = sub;
    f->cmd_type = type;
    f->len      = 7u + payload_len;

    uint16_t total = (uint16_t)f->len;
    f->buf[0] = (uint8_t)(total & 0xff);
    f->buf[1] = (uint8_t)(total >> 8);
    f->buf[2] = 0;   /* msg_seq */
    f->buf[3] = 0;   /* ack_seq */
    f->buf[4] = main;
    f->buf[5] = sub;
    f->buf[6] = type;
    return &f->buf[7];
}

bool fmt_tx_raw(struct fmt_tx_frame *f, uint8_t main, uint8_t sub,
                uint8_t type, const uint8_t *payload, size_t payload_len)
{
    uint8_t *p = fmt_tx_begin(f, main, sub, type, payload_len);
    if (!p) return false;
    if (payload_len > 0) {
        if (!payload) return false;
        memcpy(p, payload, payload_len);
    }
    return true;
}

/*
 * GPRS/data-call establish (recovered from IpcTxSetDataCallEstablish @0x320a10):
 *   8-byte frame: len=8, msg_seq=0, ack_seq=0, main=3, sub=2, type=3,
 *   payload[0]=1 when establish else 2.
 */
bool fmt_tx_set_data_call_establish(struct fmt_tx_frame *f, bool establish)
{
    uint8_t p[1];
    p[0] = establish ? 1u : 2u;
    return fmt_tx_raw(f, 3u /*CDMA_DATA*/, 2u /*CDMA_DATA_CALL_ESTABLISH*/,
                      FMT_TX_TYPE_NOTIFICATION, p, 1);
}

/*
 * DataProtocol -> wire byte helper (VERIFIED @0x31f5dc / 0x31ff48).
 * wire = (0x00040605 >> ((proto-2)*8)) & 0xff, with csel fallback to 0x02
 * when (proto-2) >= 3 (unsigned). DataProtocol enum: IP=2, IPV6=3, IPV4V6=4.
 */
static uint8_t proto_wire_byte(uint8_t proto)
{
    switch (proto) {
    case FMT_TX_PROTO_IP:     return 0x05;
    case FMT_TX_PROTO_IPV6:   return 0x06;
    case FMT_TX_PROTO_IPV4V6: return 0x04;
    default:                  return 0x05;  /* unknown -> IP (vendor default) */
    }
}

/* GPRS SET_APN_INFO, IpcTxSetDataProfile @0x31ff48.
 * CP sipcProcGprsSetApnInfoSet @0x4121b7a8 confirms that byte 189 is
 * APN DISABLED, not a PCO flag. The first byte is the profile ID, not auth.
 * See docs/S5000AP-IPC41-DATA.md and the vendor-emulated golden vectors.
 * This convenience API configures the default internet profile (wire ID 1).
 */
bool fmt_tx_set_data_profile_ex(struct fmt_tx_frame *f, const char *apn,
                                  uint8_t auth_code, uint8_t proto,
                                  uint8_t profile_id, const char *label)
{
    if (!f || !apn || !label || auth_code > FMT_TX_AUTH_PAP_OR_CHAP) return false;
    size_t alen = strlen(apn);
    size_t llen = strlen(label);
    if (alen == 0 || alen > 100u || llen == 0 || llen > 12u) return false;
    uint8_t *p = fmt_tx_begin(f, MAIN_GPRS, 27u, FMT_TX_TYPE_NOTIFICATION, 196u);
    if (!p) return false;
    memset(p, 0, 196u);
    p[0] = profile_id;                   /* explicit vendor DataProfile wire id */
    memcpy(p + 1, label, llen);          /* fixed 12-byte profile label, zero padded */
    p[21] = proto_wire_byte(proto);
    memcpy(p + 22, apn, alen);
    /* DataAuth NONE=0, PAP=1, CHAP=2, PAP_OR_CHAP=3 -> 0,1,2,1. */
    static const uint8_t auth_wire[] = {0, 1, 2, 1};
    p[187] = auth_wire[auth_code];
    p[188] = 0;                        /* no P-CSCF requested */
    p[189] = 0;                        /* enabled: (~true) & 1 */
    return true;
}

bool fmt_tx_set_data_profile(struct fmt_tx_frame *f, const char *apn,
                             uint8_t auth_code, uint8_t proto)
{
    /* Default internet profile: ConvertProfileId(DEFAULT)==1, label
     * "lte_internet" (verified golden vector). */
    return fmt_tx_set_data_profile_ex(f, apn, auth_code, proto, 1u,
                                      "lte_internet");
}

/* IpcTxSetPdpContext @0x31f6e0 takes username/password, NOT an APN.
 * DefinePdpContext or the attach profile supplies the APN separately.
 * Wire state 1 activates the CID. The flags describe credential presence;
 * bit 4 means authentication supplied and is not an activation bit.
 * This compatibility wrapper supports the no-credentials internet context.
 */
bool fmt_tx_set_pdp_context(struct fmt_tx_frame *f, const char *apn,
                            uint8_t auth_code, uint8_t proto, uint8_t cid,
                            uint8_t pdp_type_wire)
{
    if (!f || !apn || !apn[0] || strlen(apn) > 100u ||
        auth_code > FMT_TX_AUTH_PAP_OR_CHAP || cid == 0 || cid > 15u ||
        pdp_type_wire < 1u || pdp_type_wire > 8u) return false;
    (void)proto; /* IP family belongs to the profile, not this command. */
    uint8_t *p = fmt_tx_begin(f, MAIN_GPRS, 4u, FMT_TX_TYPE_NOTIFICATION, 105u);
    if (!p) return false;
    memset(p, 0, 105u);
    p[0] = pdp_type_wire;
    p[1] = cid;
    if (pdp_type_wire == 1u && auth_code != FMT_TX_AUTH_NONE) {
        static const uint8_t auth_wire[] = {0, 1, 2, 1};
        p[2] = 0x10u;
        p[102] = auth_wire[auth_code];
    }
    return true;
}

/*
 * GPRS always-on PDN (recovered from IpcTxSetAlwaysOnPdn @0x321550):
 *   header main=13 sub=34(0x22) type=3; payload[0]=on/off(1/0),
 *   payload[1]=profile code.
 */
bool fmt_tx_set_always_on_pdn(struct fmt_tx_frame *f, bool enable, uint8_t profile)
{
    uint8_t p[2];
    p[0] = enable ? 1u : 0u;
    p[1] = profile;
    return fmt_tx_raw(f, MAIN_GPRS, 34u /*SET_ALWAYS_ON_PDN*/, FMT_TX_TYPE_NOTIFICATION, p, 2);
}

/* IpcTxSetLteAttachProfile @0x320238. The trailing vendor boolean
 * selects 3 when true and 1 when false (CSINC with WZR increments 0 to 1).
 * Accept the actual wire selector, not a bitmask. CID is transmitted intact.
 */
bool fmt_tx_set_lte_attach_profile(struct fmt_tx_frame *f, const char *apn,
                                   uint8_t auth_code, uint8_t proto, uint8_t cid,
                                   uint8_t flag)
{
    if (!f || !apn || auth_code > FMT_TX_AUTH_PAP_OR_CHAP ||
        (flag != 1u && flag != 3u) || cid == 0 || cid > 15u) return false;
    size_t alen = strlen(apn);
    if (alen == 0 || alen > 100u) return false;
    uint8_t *p = fmt_tx_begin(f, MAIN_GPRS, 20u, FMT_TX_TYPE_NOTIFICATION, 194u);
    if (!p) return false;
    memset(p, 0, 194u);
    p[0] = flag;
    p[1] = cid;
    p[2] = proto_wire_byte(proto);
    memcpy(p + 3, apn, alen);
    static const uint8_t auth_wire[] = {0, 1, 2, 1};
    p[191] = auth_wire[auth_code];
    p[192] = proto_wire_byte(proto);
    return true;
}

/* SIM query: vendor sends SEC interrogations as 7-byte frames (type=2). */
bool fmt_tx_get_sim_status(struct fmt_tx_frame *f)
{
    return fmt_tx_raw(f, MAIN_SEC, 1 /*SEC_PIN_STATUS*/, FMT_TX_TYPE_REQUEST, NULL, 0);
}

bool fmt_tx_usim_auth(struct fmt_tx_frame *f, const uint8_t rand[16],
                      const uint8_t autn[16])
{
    if (!f || !rand || !autn) return false;
    uint8_t *p = fmt_tx_begin(f, MAIN_SEC, 9, FMT_TX_TYPE_REQUEST, 35);
    if (!p) return false;
    p[0]=2; p[1]=16;
    memcpy(p+2,rand,16); p[18]=16; memcpy(p+19,autn,16);
    return true;
}

bool fmt_tx_get_sim_icc_type(struct fmt_tx_frame *f)
{
    /* SEC_SIM_ICC_TYPE (main=5 sub=7) request, 7-byte frame. Tells whether the
     * UICC exposes SIM applications. ISIM absence does not preclude IMS: see
     * TS 24.229 5.1.1.1A/C.2 and TS 33.203 8.0 (USIM fallback). */
    return fmt_tx_raw(f, MAIN_SEC, 7 /*SEC_SIM_ICC_TYPE*/, FMT_TX_TYPE_REQUEST, NULL, 0);
}

bool fmt_tx_get_sim_apps_info(struct fmt_tx_frame *f)
{
    /* SEC_SIMAPPS_INFO (main=5 sub=15) request, 7-byte frame. Authoritative
     * SIM application inventory (USIM/ISIM/CSIM). Recovered from the EFUJ2
     * IpcTxGetSimAppsInfo @0x341000 wire = [07 00 00 00 05 0f 02]. This is the
     * vendor GetSimAppsInfo path (ModemProxy/SimManager), not the single-byte
     * ICC-type heuristic. */
    return fmt_tx_raw(f, MAIN_SEC, 15 /*SEC_SIMAPPS_INFO*/, FMT_TX_TYPE_REQUEST, NULL, 0);
}

bool fmt_tx_get_ps_attach(struct fmt_tx_frame *f)
{
    return fmt_tx_raw(f, 13, 3, 2, NULL, 0);
}

bool fmt_tx_get_sim_network(struct fmt_tx_frame *f)
{
    /* IpcTxGetImsi @0x32b6d0. Response length byte then ASCII digits. */
    return fmt_tx_raw(f, 10u, 2u, FMT_TX_TYPE_REQUEST, NULL, 0);
}

bool fmt_tx_get_atr(struct fmt_tx_frame *f)
{
    return fmt_tx_raw(f, MAIN_SEC, 10 /*SEC_ATR_INFO*/, FMT_TX_TYPE_REQUEST, NULL, 0);
}

bool fmt_tx_get_serving_network(struct fmt_tx_frame *f)
{
    return fmt_tx_raw(f, MAIN_NET, 3 /*NET_SERVING_NETWORK*/, FMT_TX_TYPE_REQUEST, NULL, 0);
}

bool fmt_tx_get_registration(struct fmt_tx_frame *f)
{
    return fmt_tx_raw(f, MAIN_NET, 5 /*NET_REGIST*/, FMT_TX_TYPE_REQUEST, NULL, 0);
}

/*
 * PS/data registration state query (IpcTxNetGetDataRegState @0x335b00).
 *
 * Recovered byte-exact from the vendor RIL: the function builds a 9-byte frame
 * with header main=8 (NET), sub=5 (NET_REGIST), type=2 (REQUEST) and a 2-byte
 * payload [0xFF, 0x03]. The 0x03 trailing byte is the data-registration
 * selection; 0xFF is the vendor's fixed marker. This is the query the RIL
 * issues via ModemProxy::GetDataRegState -> IpcModem::GetDataRegState
 * (transaction 801) to learn the PS/data registration state of the CP.
 */
bool fmt_tx_get_data_reg_state(struct fmt_tx_frame *f)
{
    static const uint8_t payload[2] = { 0xFF, 0x03 };
    return fmt_tx_raw(f, MAIN_NET, 5 /*NET_REGIST*/, FMT_TX_TYPE_REQUEST, payload, 2);
}

/*
 * GPRS PS attach (recovered from IpcTxPsAttach disasm @0x31fa98):
 *   header main=13 sub=3 type=3; payload[0]=attach, payload[1]=suspend,
 *   payload[2]=detach_reason (clamped 0..4).
 */
bool fmt_tx_ps_attach(struct fmt_tx_frame *f, bool attach, bool suspend,
                      uint8_t detach_reason)
{
    uint8_t p[3];
    p[0] = attach ? 1u : 0u;
    p[1] = !attach && suspend ? 1u : 0u;
    p[2] = !attach && detach_reason <= 4u ? detach_reason : 0u;
    return fmt_tx_raw(f, MAIN_GPRS, 3 /*GPRS_PS*/, FMT_TX_TYPE_NOTIFICATION, p, 3);
}

/* GPRS get PDP context: 7-byte query (recovered from IpcTxGetPdpContext). */
bool fmt_tx_get_pdp_context(struct fmt_tx_frame *f)
{
    return fmt_tx_raw(f, MAIN_GPRS, 4 /*GPRS_PDP_CONTEXT*/, FMT_TX_TYPE_REQUEST, NULL, 0);
}

/* IpcTxSetPdpContext(CID, 0, empty credentials): isolated vendor vector.
 * Release only this context; do not detach packet service or power off RF. */
bool fmt_tx_release_pdp_context(struct fmt_tx_frame *f, uint8_t cid)
{
    if (!f || cid < 1 || cid > 15) return false;
    uint8_t *p = fmt_tx_begin(f, MAIN_GPRS, 4u, FMT_TX_TYPE_NOTIFICATION, 105u);
    if (!p) return false;
    memset(p, 0, 105u); p[1] = cid;
    return true;
}

bool fmt_tx_get_pdp_definitions(struct fmt_tx_frame *f)
{
    return fmt_tx_raw(f, MAIN_GPRS, 1, FMT_TX_TYPE_REQUEST, NULL, 0);
}

/*
 * GPRS sync full data profile (recovered from IpcTxSyncProfileInfo @0x31fb48):
 * 326-byte frame: main=13 sub=37(0x25) type=3; payload=319 bytes.
 * This is the REAL full-profile sync (incl. RAT) the Android RIL issues to
 * prepare the CP for a data session. The 9-byte SetMobileDataSetting (sub=29)
 * is a simpler toggle and is NOT sufficient for LTE attach.
 *
 *   payload[0]       = 1 (enable)
 *   payload[1..2]    = region code (1 = default/non-NTC)
 *   payload[3]       = rat code (RadioTechnologyType; LTE = 14, VERIFIED)
 *   payload[4..104]  = APN (101 bytes NUL-padded)
 *   payload[105..108]= reserved (0)
 *   payload[109]     = protocol byte (home)
 *   payload[110]     = protocol byte (roaming)
 *   payload[111..142]= username (32 bytes)
 *   payload[143..174]= password (32 bytes)
 *   payload[175..310]= reserved (0)
 *   payload[311]     = auth flag (0x00010201 >> ((auth-1)*8))
 *   payload[312]     = protocol byte (2nd copy)
 *   payload[313]     = protocol byte (3rd copy)
 *   payload[314]     = pco flag ((~pco)&1)
 *   payload[315..318]= reserved (0)
 */
bool fmt_tx_sync_profile_info(struct fmt_tx_frame *f, const char *apn,
                              uint8_t auth_code, uint8_t proto)
{
    if (!f || !apn || auth_code > FMT_TX_AUTH_PAP_OR_CHAP) return false;
    size_t alen = strlen(apn);
    if (alen > 100u) return false;

    uint8_t *p = fmt_tx_begin(f, MAIN_GPRS, 37u /*SYNC_PROFILE_INFO*/,
                              FMT_TX_TYPE_NOTIFICATION, 319u);
    if (!p) return false;
    memset(p, 0, 319u);

    p[0] = 1u;
    p[1] = 1u;   /* region code low byte (non-NTC default) */
    p[2] = 0u;   /* region code high byte */
    p[3] = FMT_TX_RAT_LTE;   /* RadioTechnologyType LTE = 14 (VERIFIED enum) */

    memcpy(&p[4], apn, alen);

    uint8_t pb = proto_wire_byte(proto);
    p[109] = pb;
    p[110] = pb;

    static const uint8_t auth_wire[] = {0, 1, 2, 1};
    p[311] = auth_wire[auth_code];
    p[312] = 0; /* P-CSCF home */
    p[313] = 0; /* P-CSCF roaming */
    p[314] = 0; /* enabled */

    return true;
}

/*
 * GPRS mobile-data on/off (recovered from IpcTxSetMobileDataSetting @0x3214c8):
 *   main=13 sub=0x1d(29 SYNC_PROFILE_INFO) type=3;
 *   payload[0]=enable, payload[1]=extra.
 */
bool fmt_tx_mobile_data(struct fmt_tx_frame *f, bool enable, bool extra)
{
    uint8_t p[2];
    p[0] = enable ? 1u : 0u;
    p[1] = extra ? 1u : 0u;
    return fmt_tx_raw(f, MAIN_GPRS, 29 /*GPRS_SYNC_PROFILE_INFO*/,
                      FMT_TX_TYPE_NOTIFICATION, p, 2);
}

/*
 * GPRS define PDP context (recovered from IpcTxDefinePdpContext @0x31f580).
 * 134-byte frame: 7-byte header + 127-byte payload.
 *   payload[0]   = 0x01 (fixed profile flag)
 *   payload[1]   = profile id (u8)
 *   payload[2]   = protocol byte (see below)
 *   payload[3..103] = APN (101 bytes, NUL padded)
 *   payload[104..126] = reserved (23 bytes, zero)
 */
bool fmt_tx_define_pdp_context(struct fmt_tx_frame *f, const char *apn,
                               uint8_t proto, uint8_t profile_id)
{
    if (!f || !apn) return false;
    size_t alen = strlen(apn);
    if (alen > 100u) return false;   /* vendor strlen<=0x65 gate */

    uint8_t *p = fmt_tx_begin(f, MAIN_GPRS, 1 /*GPRS_DEFINE_PDP_CONTEXT*/,
                              FMT_TX_TYPE_NOTIFICATION, 127u);
    if (!p) return false;
    memset(p, 0, 127u);

    p[0] = 0x01;             /* fixed profile flag */
    p[1] = profile_id;       /* profile id */
    p[2] = proto_wire_byte(proto);
    /* APN into payload[3 .. 3+alen] (full-frame offset 10). */
    memcpy(&p[3], apn, alen);

    return true;
}

/*
 * NET service domain config (IpcTxNetSetServiceDomain @0x336dc8).
 * 8-byte frame: main=8 sub=8(0x08) type=3, payload=[domain].
 * Internal NetServiceDomainType: 0=CS_PS, 1=PS_ONLY, 2=CS_ONLY.
 * Vendor @0x336e30 maps these to wire 1,3,2 respectively. Sending wire 2
 * disables packet service; the previous implementation mislabeled it CS_PS.
 */
bool fmt_tx_set_service_domain(struct fmt_tx_frame *f, uint8_t domain)
{
    uint8_t p[1];
    if (domain > FMT_TX_SERVICE_DOMAIN_CS_ONLY) return false;
    p[0] = domain == FMT_TX_SERVICE_DOMAIN_PS_ONLY ? 3u :
           domain == FMT_TX_SERVICE_DOMAIN_CS_ONLY ? 2u : 1u;
    return fmt_tx_raw(f, MAIN_NET, 8u /*NET_SERVICE_DOMAIN_CONFIG*/,
                      FMT_TX_TYPE_NOTIFICATION, p, 1);
}

bool fmt_tx_get_service_domain(struct fmt_tx_frame *f)
{
    return fmt_tx_raw(f, MAIN_NET, 8u, FMT_TX_TYPE_REQUEST, NULL, 0);
}

/*
 * NET preferred network type / network mode select
 * (IpcTxNetSetPreferredNetType @0x335e00).
 * 8-byte frame: main=8 sub=10(0x0a) type=3, payload=[PreferredNetType].
 * 9 = LTE/WCDMA/GSM auto (Android PreferredNetworkType), the S10+ LTE default.
 */
bool fmt_tx_set_preferred_net_type(struct fmt_tx_frame *f, uint8_t net_type)
{
    uint8_t p[1];
    /* ConvertPreferredNetTypeToIpcWithBitmask @0x335c60:
     * PreferredNetType 9 (LTE/GSM/WCDMA) -> mask 0x0b, not 0x09. */
    if (net_type == FMT_TX_PREFERRED_NET_LTE_AUTO) p[0] = 0x0bu;
    else if (net_type == FMT_TX_PREFERRED_NET_LTE_ONLY) p[0] = 0x08u;
    else return false;
    return fmt_tx_raw(f, MAIN_NET, 10u /*NET_MODE_SEL*/,
                      FMT_TX_TYPE_NOTIFICATION, p, 1);
}

bool fmt_tx_get_preferred_net_type(struct fmt_tx_frame *f)
{
    /* IpcTxNetGetPreferredNetType @0x335ed8, complete vendor frame 7 bytes. */
    return fmt_tx_raw(f, MAIN_NET, 10u, FMT_TX_TYPE_REQUEST, NULL, 0);
}

/* NET_VOLTE_STATE (sub=52) — IpcTxSetVolteStateNotification @0x338578.
 * 8-byte frame: total=8, msg_seq=0, ack_seq=0, main=8(NET), sub=0x34(52),
 * type=3, payload[0] = bool (1 = AP IMS/VoLTE stack ready).
 * This does not start SIP registration. Byte-exact vendor frame. */
bool fmt_tx_set_volte_state_notification(struct fmt_tx_frame *f, bool ready)
{
    uint8_t p[1];
    p[0] = ready ? FMT_TX_VOLTE_STATE_READY : FMT_TX_VOLTE_STATE_NOT_READY;
    return fmt_tx_raw(f, MAIN_NET, FMT_TX_NET_SUB_VOLTE_STATE,
                      FMT_TX_TYPE_NOTIFICATION, p, 1);
}

/* NET_HVOLTE_TESTMODE (sub=40) — IpcTxGetVolteTestmode @0x338410 (type=2,
 * 7-byte frame) / IpcTxSetVolteTestmode @0x3384c0 (type=3, 8-byte frame). */
bool fmt_tx_get_volte_testmode(struct fmt_tx_frame *f)
{
    return fmt_tx_raw(f, MAIN_NET, FMT_TX_NET_SUB_HVOLTE_TESTMODE,
                      FMT_TX_TYPE_REQUEST, NULL, 0);
}

bool fmt_tx_set_volte_testmode(struct fmt_tx_frame *f, uint8_t mode)
{
    return fmt_tx_raw(f, MAIN_NET, FMT_TX_NET_SUB_HVOLTE_TESTMODE,
                      FMT_TX_TYPE_NOTIFICATION, &mode, 1);
}

/*
 * IMS (main=22) serialization — AP registration-state reporting.
 *
 * IpcTxImsReqSetRegState (IpcProtocol41::IpcTxImsReqSetRegState @0x34d230):
 * 8-byte header + 6-byte payload (total_len=13). Recovered wire layout:
 *   hdr: total_len=13, msg_seq=0, ack_seq=0, main=0x16(22), sub=0x08, type=3
 *   payload[0] = ImsRegStatus   (arg1)
 *   payload[1] = request flag   (arg2, int)
 *   payload[2] = NetworkType    (arg3)
 *   payload[3] = EcmpState      (arg4)
 *   payload[4] = EpdgAvailState (derived from RadioTechnology via jump tbl)
 *   payload[5] = RadioTechnology(arg7)
 */
bool fmt_tx_ims_set_reg_state(struct fmt_tx_frame *f, uint8_t reg_status,
                              uint8_t network_type, uint8_t rat)
{
    if (!f || reg_status > FMT_TX_IMS_REGSTATUS_DEREG) return false;
    uint8_t p[6] = {0};
    /* Corrected against IpcProtocol41::IpcTxImsReqSetRegState @0x34d230
     * (aarch64 disassembly, libsec-ril 60889dd7) and its unique caller
     * IpcModem::SetImsRegState @0x2fbe88. The demangled signature is
     *   SetImsRegState(ImsRegStatus, int, NetworkType, EcmpState,
     *                  EpdgState, EpdgAvailableState, int, RadioTechnology)
     * and both disassemblies write the SAME 6-byte on-wire layout:
     *   payload[0] = ImsRegStatus   (w1)
     *   payload[1] = service flags  (w2, int)
     *   payload[2] = NetworkType    (w3; Android RADIO_TECH, LTE=14)
     *   payload[3] = EcmpState      (w4)
     *   payload[4] = EpdgState/    EpdgAvailableState (derived; 6 for LTE)
     *   payload[5] = int            (w7, second int)
     * RadioTechnology (w8/stack) is consumed ONLY to derive payload[4] via a
     * jump table (LTE/14 -> 6); it is NOT itself a payload byte. The prior
     * implementation dropped payload[1] and shifted NetworkType/EcmpState,
     * which left the service flags byte carrying the RAT value (14) instead of
     * 1 -- a structurally valid but semantically wrong frame the modem ignored. */
    p[0] = reg_status;                 /* ImsRegStatus (1=REGISTERED,2=DEREG) */
    p[1] = (reg_status == FMT_TX_IMS_REGSTATUS_DEREG) ? 0u : 1u; /* service flags */
    p[2] = network_type;               /* NetworkType (LTE=14) */
    p[3] = 0u;                         /* EcmpState */
    p[4] = 6u;                         /* Epdg/available-state (LTE -> 6) */
    p[5] = 0u;                         /* second int (reserved) */
    (void)rat;
    return fmt_tx_raw(f, 22u /*IMS*/, 8u /*REQ_SET_REG_STATE*/,
                      FMT_TX_TYPE_NOTIFICATION, p, sizeof p);
}

bool fmt_tx_ims_deregistration(struct fmt_tx_frame *f)
{
    return fmt_tx_raw(f, 22u /*IMS*/, 7u /*REQ_DEREGISTRATION*/,
                      FMT_TX_TYPE_NOTIFICATION, NULL, 0);
}

/* ---- MISC device capability (AP -> CP) ---- */

/* IpcProtocol41::IpcTxGetDeviceCapa @0x331350 (libsec-ril 60889dd7):
 *   FMT main=10 (MISC), sub=45 (0x2d), type=2 (REQUEST), no payload.
 *   Same (main,sub) as SetDeviceCapa but the REQUEST type; the vendor issues
 *   this first (DoCheckDeviceCapa -> GetDeviceCapa) to trigger the modem's
 *   device-capability handshake. The modem replies with IpcRxMiscDeviceCapaResp
 *   (main=10 sub=82). Verified by isolated emulation: frame 07 00 00 00 0a 2d 02.
 */
bool fmt_tx_get_device_capa(struct fmt_tx_frame *f)
{
    return fmt_tx_raw(f, 10u /*MISC*/, 45u /*GET/SET_DEVICE_CAPA*/,
                      FMT_TX_TYPE_REQUEST, NULL, 0);
}

/* IpcProtocol41::IpcTxSetDeviceCapa @0x331400 (libsec-ril 60889dd7):
 *   FMT main=10 (MISC), sub=45 (0x2d), type=3 (notification), 2-byte payload
 *   [ voice_domain_pref_1, voice_domain_pref_2 ].
 * The vendor calls this from MiscManager::DoOemSetDeviceCapa and the startup
 * DoCheckDeviceCapa. Acknowledgment confirms preference configuration only. */
bool fmt_tx_set_device_capa(struct fmt_tx_frame *f, uint8_t pref1, uint8_t pref2)
{
    uint8_t p[2];
    p[0] = pref1;
    p[1] = pref2;
    /* Truthful capabilities only; caller supplies documented domain values. */
    return fmt_tx_raw(f, 10u /*MISC*/, 45u /*SET_DEVICE_CAPA*/, 3u /*notification*/,
                      p, sizeof p);
}

/* ---- MISC IMS SDM (Service Domain Manager) settings ----
 *
 * Wire contract recovered from Ipc41PacketBuilder (libsec-ril 60889dd7):
 *   main=10 (MISC), type=3 (notification).
 *   sub=26 SdmImsSmsFmtSet   payload[0] = SmsOverIpFormat byte
 *   sub=27 SdmImsSmsOverIPSet payload[0] = enable byte
 *   sub=28 SdmImsDomainSet     payload = domain string (bounded)
 *   sub=32 SdmImsModeSet       payload[0] = mode byte
 *   sub=34 SdmPcscfSet         payload = P-CSCF string (bounded)
 * Every builder observed writes 8-byte frames for the 1-byte payloads and
 * bounded variable payloads otherwise. */

bool fmt_tx_sdm_ims_sms_fmt(struct fmt_tx_frame *f, uint8_t fmt)
{
    return fmt_tx_raw(f, 10u /*MISC*/, 26u /*SDM_IMS_SMS_FMT*/, 3u,
                      &fmt, 1u);
}

bool fmt_tx_sdm_ims_sms_over_ip(struct fmt_tx_frame *f, uint8_t enable)
{
    return fmt_tx_raw(f, 10u /*MISC*/, 27u /*SDM_IMS_SMS_OVER_IP*/, 3u,
                      &enable, 1u);
}

bool fmt_tx_sdm_ims_domain(struct fmt_tx_frame *f, const char *domain)
{
    if (!f || !domain) return false;
    size_t n = strlen(domain);
    if (n == 0 || n > 255u) return false;
    return fmt_tx_raw(f, 10u /*MISC*/, 28u /*SDM_IMS_DOMAIN*/, 3u,
                      (const uint8_t *)domain, n);
}

bool fmt_tx_sdm_ims_mode(struct fmt_tx_frame *f, uint8_t mode)
{
    return fmt_tx_raw(f, 10u /*MISC*/, 32u /*SDM_IMS_MODE*/, 3u,
                      &mode, 1u);
}

bool fmt_tx_sdm_pcscf(struct fmt_tx_frame *f, const char *pcscf)
{
    if (!f || !pcscf) return false;
    size_t n = strlen(pcscf);
    if (n == 0 || n > 255u) return false;
    return fmt_tx_raw(f, 10u /*MISC*/, 34u /*SDM_PCSCF*/, 3u,
                      (const uint8_t *)pcscf, n);
}

/* Matched RIL 60889dd7: DefinePdpContext @31f66c and SetDataProfile
 * @3201e8 map PcscfViaPco=true to 2(IP), 3(IPV6), 1(IPV4V6).
 * Keep ordinary internet builders unchanged. */
bool fmt_tx_ims_profile(struct fmt_tx_frame *f, const char *apn, uint8_t proto)
{
    if (!fmt_tx_set_data_profile_ex(f,apn,FMT_TX_AUTH_NONE,proto,2,"ims")) return false;
    f->buf[7+188] = proto==FMT_TX_PROTO_IP ? 2 : proto==FMT_TX_PROTO_IPV6 ? 3 : 1;
    return true;
}
bool fmt_tx_ims_define(struct fmt_tx_frame *f, const char *apn, uint8_t proto)
{
    /* payload[1] selector restored to the Round 07 fb9da745 value (=2, the
     * live-verified IMS DataProfile/CID slot that produced GPRS_PDP_CONTEXT
     * cid=2 state=1). The interim 09980a02 change to 1u (mislabeled
     * "EUTRAN") plus the IIL/bare-APN regressions drove CID-2 back to
     * state=3 (deactivated). */
    if (!fmt_tx_define_pdp_context(f, apn, proto, 2u)) return false;
    f->buf[7+126] = proto==FMT_TX_PROTO_IP ? 2 : proto==FMT_TX_PROTO_IPV6 ? 3 : 1;
    return true;
}

/* IpcTxSetSipParam @0x3207e0: normal IMS SIP config (main=3 CDMA_DATA sub=19).
 * See fmt_tx.h for the recovered 369-byte layout. */
bool fmt_tx_set_sip_param(struct fmt_tx_frame *f, const char *proxy,
                          const char *user, const char *pass,
                          uint8_t auth, uint8_t proto)
{
    if (!f) return false;
    if (!proxy || !proxy[0]) return false;   /* proxy (P-CSCF) is mandatory */
    if (strlen(proxy) > 102) return false;
    if (user  && strlen(user)  > 127) return false;
    if (pass  && strlen(pass)  > 127) return false;
    uint8_t *p = fmt_tx_begin(f, 3u /*CDMA_DATA*/, 19u /*SET_SIP_PARAM*/,
                              3u /*notification*/, 362u);
    if (!p) return false;
    memset(p, 0, 362);

    uint32_t flags = 0;
    if (proxy && proxy[0]) { flags |= 1u; strncpy((char*)&p[4], proxy, 102); p[4+102-1]=0; }
    if (user  && user[0])  { flags |= 2u; strncpy((char*)&p[106], user, 127); p[106+127-1]=0; }
    if (pass  && pass[0])  { flags |= 4u; strncpy((char*)&p[233], pass, 127); p[233+127-1]=0; }

    p[0] = (uint8_t)(flags & 0xff);
    p[1] = (uint8_t)((flags >> 8) & 0xff);
    p[2] = (uint8_t)((flags >> 16) & 0xff);
    p[3] = (uint8_t)((flags >> 24) & 0xff);

    /* auth at offset 367 (frame byte), proto at 368. Payload offsets:
     * p[360] = auth, p[361] = proto. */
    p[360] = auth;
    p[361] = proto;
    return true;
}

/* ---- MISC IMS SDM readback (GET) serializers ----
 * The modem ANSWERS IpcTxGetImsSdmSettings(SdmImsParm) with a direct type=2
 * (RESPONSE) frame at the same (main=10, sub) as the corresponding SET. The
 * recovered Ipc41PacketBuilder GET builders (VERIFIED disassembly, e.g.
 * BuildIpcModemSdmImsModeGet @0x353790, BuildIpcModemSdmPcscfGet @0x353568)
 * emit a 7-byte FMT REQUEST frame:
 *   [u16 total_len=7][u8 msg_seq][u8 ack_seq][u8 main=10][u8 sub][u8 type=2]
 * with NO payload. This is the authoritative readback of the modem's own
 * carrier-provisioned IMS SDM values (P-CSCF, domain, mode, SMS-over-IP),
 * which the AP must NOT fabricate. */

bool fmt_tx_sdm_ims_sms_fmt_get(struct fmt_tx_frame *f)
{
    return fmt_tx_raw(f, 10u /*MISC*/, 26u /*SDM_IMS_SMS_FMT*/,
                      FMT_TX_TYPE_REQUEST, NULL, 0);
}

bool fmt_tx_sdm_ims_sms_over_ip_get(struct fmt_tx_frame *f)
{
    return fmt_tx_raw(f, 10u /*MISC*/, 27u /*SDM_IMS_SMS_OVER_IP*/,
                      FMT_TX_TYPE_REQUEST, NULL, 0);
}

bool fmt_tx_sdm_ims_domain_get(struct fmt_tx_frame *f)
{
    return fmt_tx_raw(f, 10u /*MISC*/, 28u /*SDM_IMS_DOMAIN*/,
                      FMT_TX_TYPE_REQUEST, NULL, 0);
}

bool fmt_tx_sdm_ims_mode_get(struct fmt_tx_frame *f)
{
    return fmt_tx_raw(f, 10u /*MISC*/, 32u /*SDM_IMS_MODE*/,
                      FMT_TX_TYPE_REQUEST, NULL, 0);
}

bool fmt_tx_sdm_pcscf_get(struct fmt_tx_frame *f)
{
    return fmt_tx_raw(f, 10u /*MISC*/, 34u /*SDM_PCSCF*/,
                      FMT_TX_TYPE_REQUEST, NULL, 0);
}
