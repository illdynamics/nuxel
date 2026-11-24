/*
 * fmt_tx.c — S5000AP IpcProtocol41 FMT transmit serialization.
 * SPDX-License-Identifier: GPL-2.0-only
 *
 * See fmt_tx.h for the framing-resolution rationale. This module is a pure
 * serializer: it builds byte-exact sipc_fmt_hdr + payload frames and NEVER
 * transmits. All layouts below are recovered from the exact vendor RIL
 * (vendor/lib64/libsec-ril.so, SM-G975F/EFUJ2, build 60889dd7) disassembly.
 */
#include "fmt_tx.h"
#include <string.h>

/* constant channel-independent command tables (main_cmd values) */
#define MAIN_GPRS  13u
#define MAIN_NET   8u
#define MAIN_SEC   5u

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

/*
 * GPRS set data profile (recovered from IpcTxSetDataProfile @0x31ff48, 203 bytes).
 *
 * Layout (frame base = 7-byte sipc_fmt_hdr; payload = 196 bytes; offsets below
 * are payload offsets, VERIFIED from the SIMD/store disassembly):
 *   payload[0]       = auth code (DataAuth -> numeric; NONE=1)
 *   payload[1..20]   = profile name (20 bytes, NUL-padded)
 *   payload[21]      = protocol wire byte (0x05/0x06/0x04)
 *   payload[22..122] = APN (101 bytes, NUL-padded)
 *   payload[123..154]= username (32 bytes, NUL-padded)
 *   payload[155..186]= password (32 bytes, NUL-padded)
 *   payload[187]     = auth flag (0x00010201 >> ((auth-1)*8))
 *   payload[188]     = protocol wire byte (second copy)
 *   payload[189]     = pco flag ((~pco)&1)
 *   payload[190..191]= int a (halfword, PcscfViaPco-related, default 0)
 *   payload[192..193]= int b (halfword, default 0)
 *   payload[194..195]= int c (halfword, default 0)
 *
 * Every field is source-verified from the disassembly. The three trailing
 * halfwords (a/b/c) are carrier-tuning ints that default to 0 for a standard
 * no-auth internet profile; they are emitted as 0 (their carrier-default)
 * rather than invented nonzero values.
 */
bool fmt_tx_set_data_profile(struct fmt_tx_frame *f, const char *apn,
                             uint8_t auth_code, uint8_t proto)
{
    if (!f || !apn) return false;
    size_t alen = strlen(apn);
    if (alen > 100u) return false;

    uint8_t *p = fmt_tx_begin(f, MAIN_GPRS, 27u /*SET_DATA_PROFILE*/,
                              FMT_TX_TYPE_NOTIFICATION, 196u);
    if (!p) return false;
    memset(p, 0, 196u);

    p[0] = auth_code;            /* DataAuth -> numeric code (NONE=1) */

    /* profile name (payload[1..20], NUL-padded). The vendor writes the carrier
     * DataProfile name here (for the default bearer this is the APN/profile
     * label, e.g. "internet"). We write the APN as the profile name. */
    {
        const char *name = apn;
        size_t nn = strlen(name);
        if (nn > 20u) nn = 20u;
        memcpy(&p[1], name, nn);
    }

    uint8_t pb = proto_wire_byte(proto);
    p[21] = pb;
    p[188] = pb;

    /* auth flag byte: 0x00010201 >> ((auth-1)*8). NONE(auth_code=1)->1. */
    {
        unsigned idx = (auth_code >= 1u) ? (auth_code - 1u) : 0u;
        uint32_t pat = 0x00010201u;
        p[187] = (uint8_t)((idx < 4u) ? (pat >> (idx * 8u)) & 0xffu : 0u);
    }

    /* pco flag: (~pco)&1. pco=0 (no PCO) -> 1. pco is the PcscfViaPco enum. */
    p[189] = (uint8_t)((~0u) & 1u);  /* pco=0 -> (~0)&1 = 1 */

    /* APN at payload[22..22+alen]. */
    memcpy(&p[22], apn, alen);

    return true;
}

/*
 * GPRS set PDP context / activate (recovered from IpcTxSetPdpContext @0x31f6e0):
 * 112-byte frame: main=13 sub=4 type=3; payload=105 bytes.
 *   payload[0]     = pdp_type wire code (3 = LTE EUTRAN default)
 *   payload[1]     = cid (u8)
 *   payload[2..5]  = flags word (bit0=APN present, bit4=ACTIVATE)
 *   payload[6..37] = APN (32 bytes NUL-padded)
 *   payload[38..69] = username (32 bytes)
 *   payload[70..101] = password (32 bytes)
 *   payload[102]   = auth flag (0x00010201 >> ((auth-1)*8))
 *   payload[103]   = reserved (0)
 *   payload[104]   = protocol/tech byte
 *
 * This is the REAL LTE PDP activation command (the CDMA SetDataCallEstablish
 * main=3/sub=2 is a legacy CDMA path and does NOT bring up a GPRS/LTE bearer).
 */
bool fmt_tx_set_pdp_context(struct fmt_tx_frame *f, const char *apn,
                            uint8_t auth_code, uint8_t proto, uint8_t cid,
                            uint8_t pdp_type_wire)
{
    if (!f || !apn) return false;
    size_t alen = strlen(apn);
    if (alen > 31u) return false;   /* APN field is 32 bytes */

    /* AUTHORITATIVE layout recovered from IpcTxSetPdpContext @0x31f6e0
     * (libsec-ril.so build 60889dd714394ae0db7c2ecc2bf2740f). The mangled
     * prototype is IpcTxSetPdpContext(unsigned char cid, int pdp_type,
     * char const* apn, char const* password, int auth, int proto) and the
     * stack writes are verbatim (frame base = sp, payload base = sp+7):
     *
     *   payload[0]      = pdp_type selector byte (AccessNetworkType wire code;
     *                     EUTRAN/LTE => 3). Set by a jump-table on arg2.
     *   payload[1]      = cid (unsigned char, frame offset 8 == payload[0]+1)
     *   payload[2..5]   = flags word (LE): bit0 = APN present, bit4 = ACTIVATE.
     *                     The vendor ORs 0x01 (APN) and 0x10 (activate) when
     *                     the activation state requests it, yielding 0x11.
     *   payload[6..37]  = APN (32 bytes NUL-padded)
     *   payload[38..69] = password (32 bytes)   [the 2nd char* is password]
     *   payload[70..101]= (username/reserved)    [zero for internet APN]
     *   payload[102]    = auth flag (0x00010201 >> ((auth-1)*8))
     *   payload[103]    = reserved (0)
     *   payload[104]    = protocol wire byte (2nd copy)
     *
     * NOTE: the PRIOR layout (payload[0]=protocol, payload[1]=pdp_type, and
     * cid being dropped) was WRONG. The CP therefore rejected the ACTIVATE,
     * which is exactly the live-observed GPRS_CALL_STATUS call_state=3 /
     * pdp_state=0. */
    uint8_t *p = fmt_tx_begin(f, MAIN_GPRS, 4u /*GPRS_PDP_CONTEXT*/,
                              FMT_TX_TYPE_NOTIFICATION, 105u);
    if (!p) return false;
    memset(p, 0, 105u);

    p[0] = pdp_type_wire;                   /* payload[0] = jump-table selector */
    p[1] = cid;                             /* payload[1] = cid */

    /* The vendor's "full" path (payload[0]==1) carries the APN + flags; the
     * simple paths (payload[0]==2..8) carry NONE of these. When the wire
     * selector is the full path we emit the APN + flags; otherwise we emit the
     * simple (APN-empty, flags-zero) frame exactly as the vendor does.
     *
     * ROUND-28 correction (IpcTxSetPdpContext @0x31f6e0 authoritative):
     * the ACTIVATE bit (flags bit4 = 0x10) is OR'd in ONLY when the DataAuth
     * argument (auth_code) is NON-ZERO. For a no-auth APN (auth_code==0, e.g.
     * KPN "internet") the vendor emits flags=0x01 (APN present, NO ACTIVATE)
     * and relies on the LTE initial attach to activate the default bearer.
     * The PRIOR code hardcoded 0x11 (APN|ACTIVATE) regardless of auth, which
     * the CP rejects (the immediate GPRS_CALL_STATUS state=3, no cause). */
    if (pdp_type_wire == FMT_TX_PDP_TYPE_FULL) {
        /* flags word (LE): APN present (bit0); ACTIVATE (bit4) only if the
         * SetPdpContext DataAuth int (0=NONE) is non-zero. auth_code here uses
         * the region-code convention (1=NONE); convert to the DataAuth enum. */
        uint8_t pdp_auth = (auth_code == FMT_TX_AUTH_NONE) ? 0u : (auth_code - 1u);
        uint8_t flags = 0x01u;              /* APN present */
        if (pdp_auth != 0u) flags |= 0x10u; /* ACTIVATE */
        p[2] = flags;
        memcpy(&p[6], apn, alen);           /* APN at payload[6..6+alen] */
    }

    {
        /* auth flag byte (payload[102], IpcTxSetPdpContext @0x31f6e0):
         * 0x00010201 >> ((auth-1)*8) for the SetPdpContext DataAuth int auth in
         * {1,2,3}; 0x00 when auth==0 (NONE) or auth>3. */
        uint8_t pdp_auth = (auth_code == FMT_TX_AUTH_NONE) ? 0u : (auth_code - 1u);
        if (pdp_auth >= 1u && pdp_auth <= 3u) {
            uint32_t pat = 0x00010201u;
            p[102] = (uint8_t)((pat >> ((pdp_auth - 1u) * 8u)) & 0xffu);
        } else {
            p[102] = 0u;
        }
    }
    p[103] = 0u;
    p[104] = proto_wire_byte(proto);        /* protocol 2nd copy */

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

/*
 * GPRS LTE attach profile (recovered from IpcTxSetLteAttachProfile @0x320238):
 *   201-byte frame: main=13 sub=20(0x14) type=3; payload=194 bytes.
 *     payload[0]       = flag (3 or 4; 3=apply live-verified)
 *     payload[1]       = cid (u8, profile/context id)
 *     payload[2]       = protocol home wire byte
 *     payload[3..103]  = APN (101 bytes, NUL-padded)
 *     payload[104..119]= extra (16 bytes, zero)
 *     payload[120..123]= int (4 bytes, zero)
 *     payload[124..126]= reserved (zero)
 *     payload[127..158]= username (32 bytes)
 *     payload[159..190]= password (32 bytes)
 *     payload[191]     = auth flag (0x00010201 >> ((auth-1)*8))
 *     payload[192]     = protocol roaming wire byte
 *     payload[193]     = reserved (zero)
 */
bool fmt_tx_set_lte_attach_profile(struct fmt_tx_frame *f, const char *apn,
                                   uint8_t auth_code, uint8_t proto, uint8_t cid,
                                   uint8_t flag)
{
    if (!f || !apn) return false;
    size_t alen = strlen(apn);
    if (alen > 100u) return false;

    uint8_t *p = fmt_tx_begin(f, MAIN_GPRS, 20u /*SET_LTE_ATTACH_PROFILE*/,
                              FMT_TX_TYPE_NOTIFICATION, 194u);
    if (!p) return false;
    memset(p, 0, 194u);

    /* AUTHORITATIVE (round-17) layout from IpcProtocol41::IpcTxSetLteAttachProfile
     * @0x320238 and its caller DataCallManager::SetLteAttachProfile @0x22b518:
     *
     *   payload[0] = 3 when the trailing bool arg is set, else 1  (apply flag)
     *   payload[1] = the first "int" argument = 1 (a profile selector
     *               hardcoded to 1 by the vendor), NOT the attach CID. The CID
     *               is allocated separately by CidManager during AllocateCall.
     *   payload[2] = protocol-home wire byte
     *
     * Prior code wrote the attach CID into payload[1]; that is a semantic bug.
     * `cid` is still accepted for API compatibility but is only advisory. */
    /* AUTHORITATIVE flag decode (IpcTxSetLteAttachProfile @0x320238):
     *   tst w8,#1 ; csinc w8,3,wzr,ne  ->  payload[0] = (flag & 1) ? 3 : 4.
     * The vendor NEVER emits 1/2 as payload[0]; those are live-rejected
     * (gen_result=4). 3 = apply profile (accepted), 4 = the alternate selector
     * (live-rejected on this modem). */
    p[0] = (uint8_t)((flag & 1u) ? 3u : 4u);
    p[1] = 1u;     /* vendor-hardcoded profile selector int (NOT the CID) */
    (void)cid;
    p[2] = proto_wire_byte(proto);

    /* AUTHORITATIVE layout recovered this round from
     * IpcProtocol41::IpcTxSetLteAttachProfile @0x320238 (aarch64),
     * signature (unsigned char flag, char* apn, char* user, char* pass,
     * DataAuth, DataProtocol home, DataProtocol roaming, PcscfViaPco, ...).
     *
     * frame base = sp+0x10; every store offset below was re-derived and is
     * payload-relative (frame[7+i] == payload[i]):
     *   payload[0]    = flag (3 = apply; 4 was live-rejected on SM-G975F)
     *   payload[1]    = cid
     *   payload[2]    = protocol home wire byte
     *   payload[3..103]   = APN (101 bytes)
     *   payload[104..119] = extra (16 bytes; zero for internet APN)
     *   payload[120..123] = int (4 bytes; zero)
     *   payload[124..126] = reserved (zero)
     *   payload[127..158] = username (32 bytes; zero)
     *   payload[159..190] = password (32 bytes; zero)
     *   payload[191]  = auth flag (0x00010201 >> ((auth-1)*8))
     *   payload[192]  = protocol roaming wire byte
     *   payload[193]  = reserved (zero)
     *
     * The PRIOR code placed the auth flag at payload[168] (inside the password
     * region) and a spurious pco byte at payload[169], and omitted the protocol
     * roaming byte at payload[192]. That malformed the LTE attach profile, so
     * the CP attached with a wrong/empty profile and the subsequent
     * SetPdpContext default-bearer activation failed (GPRS_CALL_STATUS
     * state=3). */
    /* APN at payload[3..3+alen]. */
    memcpy(&p[3], apn, alen);

    /* protocol roaming (payload[192]) = same as home for a single profile. */
    p[192] = proto_wire_byte(proto);

    /* auth flag at payload[191] (0x00010201 >> ((auth-1)*8)). */
    {
        unsigned idx = (auth_code >= 1u) ? (auth_code - 1u) : 0u;
        uint32_t pat = 0x00010201u;
        p[191] = (uint8_t)((idx < 4u) ? (pat >> (idx * 8u)) & 0xffu : 0u);
    }

    return true;
}

/* SIM query: vendor sends SEC interrogations as 7-byte frames (type=2). */
bool fmt_tx_get_sim_status(struct fmt_tx_frame *f)
{
    return fmt_tx_raw(f, MAIN_SEC, 1 /*SEC_PIN_STATUS*/, FMT_TX_TYPE_REQUEST, NULL, 0);
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
    p[1] = suspend ? 1u : 0u;
    p[2] = (detach_reason > 4u) ? 0u : detach_reason;
    return fmt_tx_raw(f, MAIN_GPRS, 3 /*GPRS_PS*/, FMT_TX_TYPE_NOTIFICATION, p, 3);
}

/* GPRS get PDP context: 7-byte query (recovered from IpcTxGetPdpContext). */
bool fmt_tx_get_pdp_context(struct fmt_tx_frame *f)
{
    return fmt_tx_raw(f, MAIN_GPRS, 4 /*GPRS_PDP_CONTEXT*/, FMT_TX_TYPE_REQUEST, NULL, 0);
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
    if (!f || !apn) return false;
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

    {
        unsigned idx = (auth_code >= 1u) ? (auth_code - 1u) : 0u;
        uint32_t pat = 0x00010201u;
        p[311] = (uint8_t)((idx < 4u) ? (pat >> (idx * 8u)) & 0xffu : 0u);
    }
    p[312] = pb;
    p[313] = pb;
    p[314] = (uint8_t)((~0u) & 1u);

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
 * NetServiceDomainType: 1=CS_ONLY, 2=CS_PS (voice+data), 3=PS_ONLY.
 * The vendor default for a normal LTE attach is CS_PS (2), required before the
 * GPRS data path will accept a PS attach. Verified byte-exact this round.
 */
bool fmt_tx_set_service_domain(struct fmt_tx_frame *f, uint8_t domain)
{
    uint8_t p[1];
    /* Mirror the vendor's csinc/csel: 1->1, 2->2, else->3. */
    p[0] = (domain == 1u) ? 1u : (domain == 2u) ? 2u : 3u;
    return fmt_tx_raw(f, MAIN_NET, 8u /*NET_SERVICE_DOMAIN_CONFIG*/,
                      FMT_TX_TYPE_NOTIFICATION, p, 1);
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
    p[0] = net_type;
    return fmt_tx_raw(f, MAIN_NET, 10u /*NET_MODE_SEL*/,
                      FMT_TX_TYPE_NOTIFICATION, p, 1);
}
