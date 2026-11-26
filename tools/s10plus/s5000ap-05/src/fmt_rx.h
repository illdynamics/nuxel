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
};
/* IpcRxNetRegState @0x339818: reject cause is payload[10], not [3]. */
bool fmt_rx_registration(const uint8_t *p, size_t n, struct fmt_rx_registration *out);

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
    uint16_t mtu;
};
/* Bounds-checked IpcRxIpConfiguration @0x321620, addresses in network order. */
bool fmt_rx_ip(const uint8_t *p, size_t n, struct fmt_rx_ip *out);

/* ---- IMS (main=22) receive-side decode ---- */

/* IpcRxImsModeChange / registration-state notification. The modem reports the
 * actual IMS registration state; this is authoritative (not a local guess). */
struct fmt_rx_ims_state {
    uint8_t status;       /* 0=none, 1=registered, 2=deregistering, ... */
    uint8_t network_type; /* Android RADIO_TECH (14=LTE) */
    uint8_t rat;
    bool registered;      /* true only when status implies IMS registered */
};
bool fmt_rx_ims_state(const uint8_t *p, size_t n, struct fmt_rx_ims_state *out);

/* SEC_IMS_AUTH (main=5 sub=9) SIM AKA challenge from the modem. The AP must
 * relay this to the UICC/ISIM and return the response via IpcTxImsAuthResp.
 * `data`/`len` are opaque; never log or persist them. */
struct fmt_rx_ims_auth {
    const uint8_t *data;
    size_t len;
};
bool fmt_rx_ims_auth(const uint8_t *p, size_t n, struct fmt_rx_ims_auth *out);
#endif
