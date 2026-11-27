/* SPDX-License-Identifier: GPL-2.0-only */
#include "fmt_rx.h"
#include <string.h>

bool fmt_rx_baseband(const uint8_t *p, size_t n, char version[33])
{
    if (!version) return false;
    memset(version, 0, 33);
    if (!p || n < 33 || !(p[0] & 1)) return false;
    size_t len = 0;
    while (len < 32 && p[1+len]) {
        uint8_t c = p[1+len];
        if (!((c >= 'A' && c <= 'Z') || (c >= 'a' && c <= 'z') ||
              (c >= '0' && c <= '9') || c == '.' || c == '_' || c == '-')) return false;
        len++;
    }
    if (!len) return false;
    memcpy(version, p+1, len);
    return true;
}

uint8_t fmt_rx_reg_state(uint8_t wire)
{
    /* Vendor @0x3399cc / table 0x14a212. EPDG and vendor domestic-roaming
     * overrides are absent: preserve roaming instead of promoting it to home. */
    static const uint8_t reg[] = {4, 0, 1, 2, 3, 4, 5, 4, 0, 3, 4};
    return wire < sizeof reg ? reg[wire] : 4;
}

bool fmt_rx_registered(uint8_t state)
{
    return state == 1 || state == 5;
}

bool fmt_rx_registration(const uint8_t *p, size_t n, struct fmt_rx_registration *out)
{
    if (!p || !out || n < 20 || p[1] < 1 || p[1] > 3) return false;
    /* Location area code / tracking area code. The WCDMA and LTE variants of
     * this frame carry it as a u16 at payload[4..5] (libsec-ril EFUJ2
     * IpcRxNetRegState @0x339818). This is a SILENT location indicator: the
     * caller MUST only use it as the P-Access-Network-Info TAC when an LTE
     * PS home registration is affirmatively present (see radiod), never as
     * a cell identity. */
    struct fmt_rx_registration r = {
        .rat_wire = p[0], .domain = p[1], .state_wire = p[2],
        .state = fmt_rx_reg_state(p[2]), .reject_cause = p[10],
        .lac_tac = (uint16_t)(p[4] | (p[5] << 8))
    };
    *out = r;
    return true;
}

const char *fmt_rx_reg_name(uint8_t state)
{
    static const char *const names[] = {
        "NOT_REGISTERED", "REGISTERED_HOME", "SEARCHING", "DENIED", "UNKNOWN", "REGISTERED_ROAMING"
    };
    return state < sizeof names / sizeof names[0] ? names[state] : "UNKNOWN";
}

bool fmt_rx_sim_ready(const uint8_t *p, size_t n)
{
    return p && n == 2 && (p[0] == 0 || p[0] == 0x82) && p[1] == 0;
}

bool fmt_rx_sim_network(const uint8_t *p, size_t n, char plmn[6])
{
    if (!plmn) return false;
    memset(plmn, 0, 6);
    if (!p || n < 1 || p[0] < 5 || p[0] > 15 || n != (size_t)p[0]+1) return false;
    for (size_t i = 1; i < n; i++) if (p[i] < '0' || p[i] > '9') return false;
    if (!memcmp(p+1, "20408", 5)) memcpy(plmn, "20408", 6);
    else if (!memcmp(p+1, "20416", 5)) memcpy(plmn, "20416", 6);
    else return false;
    return true;
}

bool fmt_rx_gen(const uint8_t *p, size_t n, struct fmt_rx_gen *out)
{
    if (!p || !out || n != 5) return false;
    out->main = p[0]; out->sub = p[1]; out->type = p[2];
    out->result = (uint16_t)p[3] | ((uint16_t)p[4] << 8);
    return true;
}

uint8_t fmt_rx_rat(uint8_t wire)
{
    /* DTK9 jump table at 0x14a22d, converter 0x33a028. Entry 33 returns
     * the preloaded 14 directly; it does not execute the preceding MOV 0. */
    static const uint8_t rat[49] = {
        [1]=16, [2]=1, [3]=2, [4]=3, [5]=3,
        [17]=4, [18]=5, [19]=6, [20]=7, [21]=7,
        [22]=8, [23]=8, [24]=8, [25]=13,
        [33]=14, [34]=17, [36]=20, [48]=18
    };
    return wire < sizeof rat ? rat[wire] : 0;
}

const char *fmt_rx_rat_name(uint8_t wire)
{
    switch (fmt_rx_rat(wire)) {
    case 1: return "GPRS"; case 2: return "EDGE"; case 3: return "UMTS";
    case 7: return "1xRTT"; case 8: return "HSDPA"; case 13: return "eHRPD";
    case 14: return "LTE"; case 16: return "GSM"; case 17: return "TD-SCDMA";
    case 18: return "IWLAN"; case 20: return "NR"; default: return "UNKNOWN";
    }
}

bool fmt_rx_pdp_state(const uint8_t *p, size_t n, uint8_t cid, uint8_t *state)
{
    if (!p || !state || n < 1 || n != 1u + 2u * p[0]) return false;
    *state = 0;
    for (size_t i = 0; i < p[0]; i++) {
        if (p[1+2*i] == cid) { *state = p[2+2*i]; return true; }
    }
    return true; /* valid list, requested CID absent => disconnected */
}

static bool nonzero(const uint8_t *p, size_t n)
{
    for (size_t i = 0; i < n; i++) if (p[i]) return true;
    return false;
}

bool fmt_rx_pdp_profiles(const uint8_t *p, size_t n, struct fmt_rx_pdp_profiles *out)
{
    if (!p || !out || n < 1 || p[0] > FMT_RX_PDP_PROFILES ||
        n != 1u + 126u * p[0]) return false;
    struct fmt_rx_pdp_profiles v = {0};
    uint32_t seen = 0;
    for (unsigned i = 0; i < p[0]; i++) {
        const uint8_t *q = p + 1 + 126u * i;
        /* The CP counts valid contexts before filtering the RIL instance,
         * then allocates/zeroes the whole reply. Unfilled slots stay zero
         * (0x41301c62 versus 0x41301d18). They are not a CID0 profile. */
        if (!nonzero(q,126)) continue;
        if (!q[0] || q[0] > 27 || (seen & (1u << q[0]))) return false;
        seen |= 1u << q[0];
        const uint8_t *end = memchr(q + 2, 0, 101);
        if (!end) return false;
        size_t len = (size_t)(end - (q + 2));
        for (size_t k = 0; k < len; k++)
            if (q[2+k] < 0x20 || q[2+k] > 0x7e) return false;
        v.profile[v.count].cid = q[0];
        v.profile[v.count].protocol_wire = q[1];
        memcpy(v.profile[v.count].apn, q + 2, len);
        v.profile[v.count].data_compression = q[123];
        v.profile[v.count].header_compression = q[124];
        v.count++;
    }
    *out = v;
    return true;
}

bool fmt_rx_ip(const uint8_t *p, size_t n, struct fmt_rx_ip *out)
{
    if (!p || !out || n < 3 || p[0] == 0 || p[0] > 15) return false;
    struct fmt_rx_ip v = {0};
    v.cid = p[0]; v.flags = (uint16_t)p[1] | ((uint16_t)p[2] << 8);
    if (v.flags & 1u) {
        if (n < 15) return false;
        memcpy(v.ipv4, p+3, 4); memcpy(v.dns4, p+7, 8);
        v.ipv4_valid = nonzero(v.ipv4, 4) && v.ipv4[0] < 224 && v.ipv4[0] != 127;
        if (v.flags & (1u<<3)) {
            if (n < 19) return false;
            memcpy(v.gateway4, p+15, 4);
        }
        /* A raw-IP cellular link can use a host address with an on-link
         * default. Do not invent the vendor's fallback gateway (.1). */
        v.prefix4 = 32;
        if (v.flags & (1u<<4)) {
            if (n < 23) return false;
            bool zero_seen = false; v.prefix4 = 0;
            for (unsigned b = 0; b < 32; b++) {
                bool bit = (p[19+b/8] & (0x80u >> (b%8))) != 0;
                if (bit && zero_seen) return false;
                if (bit) v.prefix4++; else zero_seen = true;
            }
        }
    }
    if (v.flags & (1u<<6)) {
        if (n < 131) return false;
        memcpy(v.ipv6, p+35, 16); memcpy(v.dns6, p+99, 32);
        v.ipv6_valid = nonzero(v.ipv6, 16) && v.ipv6[0] != 0xff;
    }
    if (v.flags & (1u<<13)) {
        if (n < 156) return false;
        uint32_t mtu = (uint32_t)p[152] | ((uint32_t)p[153]<<8) |
                       ((uint32_t)p[154]<<16) | ((uint32_t)p[155]<<24);
        if (mtu > 65535) return false;
        v.mtu = (uint16_t)mtu;
    }
    /* IpcRxIpConfiguration @0x32198c: three base P-CSCF addresses,
     * followed by five more in the extended frame. Never read a short field. */
    for (unsigned i=0; i<8; i++) {
        size_t o4 = i<3 ? 23u+4u*i : 157u+4u*(i-3);
        size_t o6 = i<3 ? 51u+16u*i : 177u+16u*(i-3);
        if (n >= o4+4 && nonzero(p+o4,4) && p[o4] < 224) {
            memcpy(v.pcscf4[v.pcscf4_count++],p+o4,4);
        }
        if (n >= o6+16 && nonzero(p+o6,16) && p[o6] != 0xff) {
            memcpy(v.pcscf6[v.pcscf6_count++],p+o6,16);
        }
    }
    if (!v.ipv4_valid && !v.ipv6_valid) return false;
    *out = v;
    return true;
}

bool fmt_rx_usim_auth(const uint8_t *p, size_t n, struct fmt_rx_usim_auth *out)
{
    if (!out) return false;
    memset(out,0,sizeof *out);
    if (!p || n<2 || p[0]!=2) return false;
    struct fmt_rx_usim_auth v={.result=p[1]};
    /* IpcRxSecImsAuth @0x343ec0 accepts result 0,4,5 as data-bearing;
     * result 3 is a UICC failure, other values are errors. */
    if (v.result!=0 && v.result!=4 && v.result!=5) {
        if (n!=2) return false;
        *out=v; return true;
    }
    const uint8_t *part[4]; size_t len[4], off=2;
    for (unsigned i=0;i<4;i++) {
        if (off>=n) return false;
        len[i]=p[off++];
        if (len[i]>n-off) return false;
        part[i]=p+off; off+=len[i];
    }
    if (off!=n) return false;
    if (v.result==0) {
        if (len[0]<4 || len[0]>16 || len[1]!=16 || len[2]!=16 || len[3]!=8)
            return false;
        v.authenticated=true; v.res=part[0]; v.res_len=len[0];
        v.ck=part[1]; v.ik=part[2];
    } else {
        if (len[0]!=14 || len[1] || len[2] || len[3]) return false;
        v.auts=part[0]; v.auts_len=len[0];
    }
    *out=v; return true;
}

/* SEC_SIMAPPS_INFO decode. Live EFUJ2 payload (redacted of subscriber data,
 * only the application inventory is used):
 *   numberOfApps, then per app {slot, aid_len, aid[aid_len]}, trailing bytes.
 * The 7-byte 3GPP AID prefixes identify the application type. We never copy
 * the full AID out; only counts are reported. */
static const uint8_t k_aid_usim[7] = {0xA0,0x00,0x00,0x00,0x87,0x10,0x02};
static const uint8_t k_aid_csim[7] = {0xA0,0x00,0x00,0x00,0x87,0x10,0x03};
static const uint8_t k_aid_isim[7] = {0xA0,0x00,0x00,0x00,0x87,0x10,0x04};

bool fmt_rx_sim_apps(const uint8_t *p, size_t n, struct fmt_rx_sim_apps *out)
{
    if (!p || !out || n < 1) return false;
    uint8_t count = p[0];
    if (count == 0 || count > 16) return false;
    struct fmt_rx_sim_apps v = {0};
    size_t off = 1;
    for (uint8_t i = 0; i < count; i++) {
        if (off + 2 > n) return false;
        uint8_t alen = p[off + 1];
        if (alen < 7 || off + 2 + (size_t)alen > n) return false;
        const uint8_t *aid = p + off + 2;
        if (!memcmp(aid, k_aid_usim, 7)) v.usim++;
        else if (!memcmp(aid, k_aid_csim, 7)) v.csim++;
        else if (!memcmp(aid, k_aid_isim, 7)) v.isim++;
        off += 2 + (size_t)alen;
    }
    v.count = count;
    *out = v;
    return true;
}

/* NET_SERVING_NETWORK (main=8 sub=3). Bounded, evidence-based decode of the
 * live EFUJ2/KPN frame:
 *   05 02 21 "20408" ...        (RAT, state, 0x21, ASCII PLMN MCC+MNC)
 * This CP answers the IPC41 GetServingNetwork with an Operator record only;
 * it contains NO 28-bit E-UTRAN cell id (the real ECI is only reachable via
 * the OEM-socket GetLteCellInfo opcode 0x1f54, not IPC41 FMT). We therefore
 * never emit a cell id from here. The PLMN is copied only after an all-digit
 * check; on any malformation the function returns false and copies nothing. */
bool fmt_rx_serving_network(const uint8_t *p, size_t n,
                            struct fmt_rx_serving_network *out)
{
    if (!p || !out) return false;
    struct fmt_rx_serving_network v = {0};
    /* Need at least the ASCII PLMN at [3..7]. */
    if (n >= 8) {
        const uint8_t *q = p + 3;
        bool digs = (q[0] >= '0' && q[0] <= '9') && (q[1] >= '0' && q[1] <= '9') &&
                    (q[2] >= '0' && q[2] <= '9') && (q[3] >= '0' && q[3] <= '9') &&
                    (q[4] >= '0' && q[4] <= '9');
        if (digs) {
            memcpy(v.plmn, q, 5);
            v.plmn[5] = 0;
            v.plmn_valid = true;
        }
    }
    /* No cell id is carried by this IPC41 frame on this CP. */
    v.cell_id_valid = false;
    *out = v;
    return true;
}

/* NET_CELL_INFO_LIST (main=8 sub=17), decoded from libsec-ril EFUJ2
 * IpcProtocol41::IpcRxNetCellInfoList @0x33c3b0 (request builder
 * IpcProtocol41::IpcTxNetCellInfoList @0x3378d0 emits header
 * `07 00 00 00 08 11 02` == main=8 sub=17 type=2 REQUEST, no payload).
 *
 * Payload (length byte [0..1]=total LE; [6]=cmd_type(3); [7..11]=per-RAT
 * counts in the fixed order GSM-general, GSM, WCDMA-UMTS, UMTS, LTE; data
 * starts at +12). Each LTE record is EXACTLY 20 bytes:
 *   [0]     gid        (2 = ECI; the 28-bit E-UTRAN cell identity)
 *   [1..3]  PLMN triplet
 *   [4..5]  TAC (LE)
 *   [6..9]  ECI (LE, 28 bits significant)                 <-- wanted
 *   [10..11] PCI (LE)
 *   [12..14] EARFCN (3 bytes)
 *   [15]    bandwidth
 *   [0x10..] RSRP/RSRQ/RSSNR/CQI/TA
 * Non-LTE records must be skipped to reach the LTE block:
 *   GSM-general 20, GSM 20, WCDMA-UMTS 32, UMTS 31, LTE 20 bytes each.
 *
 * This decoder is strictly bounded and never fabricates: it validates the
 * declared total against the sum implied by the counts, rejects any count
 * that would overflow the payload, and returns the ECI ONLY when the first
 * LTE record with gid==2 has a non-zero ECI. On truncation, malformation or
 * gid!=2 it reports cell_id_valid=false. It is read-only by nature. */
bool fmt_rx_net_cell_info(const uint8_t *p, size_t n,
                          const char *plmn_expect,
                          struct fmt_rx_net_cell_info *out)
{
    if (!out) return false;
    memset(out, 0, sizeof *out);
    if (!p || n < 12) return false;
    unsigned total = (unsigned)p[0] | ((unsigned)p[1] << 8);
    uint8_t n_gsmg = p[7], n_gsm = p[8], n_wcu = p[9], n_umts = p[10], n_lte = p[11];
    /* Declared total must reference the actual buffer (allow trailing bytes
     * but not fewer than declared). */
    if (total < 12 || total > n) return false;
    if (p[6] != 3) return false;          /* cmd_type must be a response */
    /* Overflow-guard: refuse absurd counts before multiplying. */
    if (n_gsmg > 32 || n_gsm > 32 || n_wcu > 32 || n_umts > 32 || n_lte > 16)
        return false;
    size_t need = 12u;
    need += (size_t)n_gsmg * 20u;
    need += (size_t)n_gsm  * 20u;
    need += (size_t)n_wcu  * 32u;
    need += (size_t)n_umts * 31u;
    need += (size_t)n_lte  * 20u;
    /* total_length must exactly equal the computed record size. */
    if (need != total) return false;
    size_t off = 12u;
    off += (size_t)n_gsmg * 20u;
    off += (size_t)n_gsm  * 20u;
    off += (size_t)n_wcu  * 32u;
    off += (size_t)n_umts * 31u;
    out->lte_count = n_lte;
    for (unsigned i = 0; i < n_lte; i++) {
        const uint8_t *e = p + off + (size_t)i * 20u;
        if (off + (size_t)(i + 1) * 20u > total) break;
        uint8_t gid = e[0];
        uint32_t eci = (uint32_t)e[6] | ((uint32_t)e[7] << 8) |
                       ((uint32_t)e[8] << 16) | ((uint32_t)e[9] << 24);
        eci &= 0x0FFFFFFFu;   /* ECI is 28 bits */
        uint16_t tac = (uint16_t)e[4] | ((uint16_t)e[5] << 8);
        uint16_t pci = (uint16_t)e[10] | ((uint16_t)e[11] << 8);
        if (gid == 2 && eci != 0) {
            /* Fill tac/pci/plmn first so the PLMN sanity check can gate it. */
            out->tac = tac;
            out->pci = pci;
            /* PLMN: NetworkManager::SetOperatorNametoCellInfo formats the
             * operator as "%s%s" (alpha=record[+10..12], numeric=
             * record[+20..22]); each is a byte array where byte k is
             * MCC/MNC digit k of "MCC||MNC". Network 8/3 already gives the
             * authoritative serving PLMN (P-Access-Network-Info prefix), so we
             * register a SANITY check here only: accept the cell's PLMN iff its
             * five digits equal the serving PLMN the daemon passed in
             * `plmn_expect`. This rejects stale/foreign cells without ever
             * fabricating a value (the daemon still uses 8/3 for the prefix). */
            out->plmn_bcd[0] = e[1]; out->plmn_bcd[1] = e[2]; out->plmn_bcd[2] = e[3];
            bool sane = true;
            for (int k = 0; k < 3; k++)
                if (out->plmn_bcd[k] > 9) { sane = false; break; }
            if (sane && plmn_expect && strlen(plmn_expect) >= 5) {
                /* cell digits d0 d1 d2 = MCC(3); for a 3-digit MNC the vendor
                 * uses e[3] as the 3rd MNC digit; otherwise e[3]==0xFF. We only
                 * assert the MCC matches and (when present) the digits line up
                 * with the expected 5-digit PLMN prefix. */
                const char *x = plmn_expect;
                bool eq = (out->plmn_bcd[0] == (uint8_t)(x[0]-'0') &&
                           out->plmn_bcd[1] == (uint8_t)(x[1]-'0') &&
                           out->plmn_bcd[2] == (uint8_t)(x[2]-'0'));
                out->plmn_sane = eq;
            } else {
                out->plmn_sane = sane;   /* no expectation: just digit check */
            }
            if (!out->plmn_sane) return true;   /* stale/foreign cell: reject ECI */
            /* 8 lowercase hex digits, no libc printf dependency. */
            static const char hx[] = "0123456789abcdef";
            for (int b = 7; b >= 0; b--) out->cell_id[7 - b] = hx[(eci >> (b * 4)) & 0xf];
            out->cell_id[8] = 0;
            out->cell_id_valid = true;
            return true;
        }
    }
    return true;   /* parsed; no ECI-class serving cell present */
}
