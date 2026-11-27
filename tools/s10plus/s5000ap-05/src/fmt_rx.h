/* SPDX-License-Identifier: GPL-2.0-only */
#ifndef NUXEL_FMT_RX_H
#define NUXEL_FMT_RX_H
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

#define FMT_RX_GEN_OK 0x8000u
#define FMT_RX_GEN_UNSUPPORTED 0x8003u
struct fmt_rx_gen { uint8_t main, sub, type; uint16_t result; };
bool fmt_rx_gen(const uint8_t *p, size_t n, struct fmt_rx_gen *out);
/* Recognize the two network prefixes relevant to this device investigation.
 * Never copy or return the subscriber part of an IMSI. Empty on unknown. */
bool fmt_rx_sim_network(const uint8_t *p, size_t n, char plmn[6]);
/* ConvertLockType @0x343300 and GenerateSimStatus @0x315be0. */
bool fmt_rx_sim_ready(const uint8_t *p, size_t n);
/* Software version field only; never return equipment/subscriber identifiers. */
bool fmt_rx_baseband(const uint8_t *p, size_t n, char version[33]);

/* IpcRxNetRegState's wire enum is NOT the public RegState enum. */
uint8_t fmt_rx_reg_state(uint8_t wire);
const char *fmt_rx_reg_name(uint8_t state);
bool fmt_rx_registered(uint8_t state);
struct fmt_rx_registration {
    uint8_t rat_wire, domain, state_wire, state, reject_cause;
    uint16_t lac_tac;   /* location area / tracking area code (payload[4..5]) */
};
/* IpcRxNetRegState @0x339818: reject cause is payload[10], not [3]. */
bool fmt_rx_registration(const uint8_t *p, size_t n, struct fmt_rx_registration *out);

/* NET_SERVING_NETWORK (main=8 sub=3), IpcRxNetServingNetwork @0x33a648.
 * Bounded decode of the live EFUJ2/KPN frame. The frame carries a real PLMN
 * (the service area identity) but NO 28-bit E-UTRAN cell id on this CP (the
 * ECI lives behind the OEM-socket GetLteCellInfo @0x309978 opcode 0x1f54,
 * which is NOT an IPC41 FMT command). Therefore `cell_id_valid` is reported
 * FALSE and the caller MUST NOT fabricate a utran-cell-id-3gpp value.
 *   payload[3..7] = ASCII PLMN "MCCMNC" (e.g. "20408")
 * PLMN is validated all-digit before being copied; never returns a
 * subscriber field. */
struct fmt_rx_serving_network {
    char    plmn[6];        /* "20408" or empty when not present/valid */
    bool    plmn_valid;
    bool    cell_id_valid;  /* false on this CP: no ECI in the IPC41 frame */
};
bool fmt_rx_serving_network(const uint8_t *p, size_t n,
                            struct fmt_rx_serving_network *out);

/* Bounded NET_CELL_INFO_LIST payload decoder, vendor build 60889dd7. */
struct fmt_rx_net_cell_info {
    char cell_id[8]; /* seven hex digits: 28-bit ECI */
    char plmn[7];    /* serving record's MCC + two/three-digit MNC */
    bool cell_id_valid, plmn_sane;
    uint16_t tac, pci;
    uint32_t earfcn;
    uint8_t lte_count;
};
bool fmt_rx_net_cell_info(const uint8_t *p, size_t n, const char *plmn_expect,
                          struct fmt_rx_net_cell_info *out);
bool fmt_rx_cell_current(const struct fmt_rx_net_cell_info *c, const char *plmn,
                         bool lte_registered, uint64_t observed, uint64_t now);

/* NET_REGIST's RAT is a Samsung wire enum, not the Android RadioTechnology. */
uint8_t fmt_rx_rat(uint8_t wire);
const char *fmt_rx_rat_name(uint8_t wire);

/* PDP list: count followed by count pairs {CID, state}. */
bool fmt_rx_pdp_state(const uint8_t *p, size_t n, uint8_t cid, uint8_t *state);

#define FMT_RX_PDP_PROFILES 11u
struct fmt_rx_pdp_profile {
    uint8_t cid, protocol_wire, data_compression, header_compression;
    char apn[101];
};
struct fmt_rx_pdp_profiles {
    uint8_t count;
    struct fmt_rx_pdp_profile profile[FMT_RX_PDP_PROFILES];
};
/* EFUJ2 CP GET handler 0x41301c56: count + count * 126 bytes. This
 * reports sm_GetApn's context value; it does not prove NV persistence. */
bool fmt_rx_pdp_profiles(const uint8_t *p, size_t n, struct fmt_rx_pdp_profiles *out);

struct fmt_rx_ip {
    uint8_t cid;
    uint16_t flags;
    bool ipv4_valid, ipv6_valid;
    uint8_t ipv4[4], dns4[2][4], gateway4[4], prefix4;
    uint8_t ipv6[16], dns6[2][16];
    uint8_t pcscf4[8][4], pcscf6[8][16];
    uint8_t pcscf4_count, pcscf6_count;
    uint16_t mtu;
};
/* Bounds-checked IpcRxIpConfiguration @0x321620, addresses in network order. */
bool fmt_rx_ip(const uint8_t *p, size_t n, struct fmt_rx_ip *out);

/* SEC_IMS_AUTH is a solicited UICC result, not an incoming AKA challenge.
 * Views borrow the RX frame only for synchronous consumption. Never log,
 * persist, or echo these buffers; CK/IK are session key material. */
struct fmt_rx_usim_auth {
    uint8_t result;
    bool authenticated;
    const uint8_t *res, *ck, *ik, *auts;
    size_t res_len, auts_len;
};
bool fmt_rx_usim_auth(const uint8_t *p, size_t n, struct fmt_rx_usim_auth *out);

/* SEC_SIMAPPS_INFO (main=5 sub=15) response: numberOfApps(1) followed by
 * numberOfApps entries of {slot(1), aid_len(1), aid[aid_len]}. Each trailing
 * remainder is ignored. Classifies applications by the 7-byte 3GPP AID
 * prefix (TS 31.101 / 31.103): USIM A0000000871002, ISIM A0000000871004,
 * CSIM A0000000871003. Bounded; never copies the full AID or any subscriber
 * field. */
struct fmt_rx_sim_apps {
    uint8_t count;      /* applications parsed (== numberOfApps) */
    uint8_t usim;       /* count of USIM AIDs */
    uint8_t isim;       /* count of ISIM AIDs */
    uint8_t csim;       /* count of CSIM AIDs */
};
bool fmt_rx_sim_apps(const uint8_t *p, size_t n, struct fmt_rx_sim_apps *out);

/* ---- IMS (main=22) receive-side decode ---- */

#endif
