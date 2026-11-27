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
    struct fmt_rx_registration r = {
        .rat_wire = p[0], .domain = p[1], .state_wire = p[2],
        .state = fmt_rx_reg_state(p[2]), .reject_cause = p[10]
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
