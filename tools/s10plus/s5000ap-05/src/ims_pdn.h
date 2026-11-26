/* SPDX-License-Identifier: GPL-2.0-only */
#ifndef NUXEL_IMS_PDN_H
#define NUXEL_IMS_PDN_H
#include <stdint.h>
#include <stdbool.h>
#include "fmt_tx.h"
#include "fmt_rx.h"

/* IMS profile synchronization and independently observed bearer readiness.
 * A profile ACK alone cannot establish the bearer. CID 1 remains isolated. */
typedef bool (*ims_pdn_write_fn)(const struct fmt_tx_frame *f, uint8_t *seq, void *user);

/* Distinct IMS APN data context identity. CID 1 is the ordinary internet
 * bearer, CID 2 is the isolated IMS APN PDN (KPN 204-08 "ims"). */
#define IMS_PDN_CID 2u
#define IMS_PDN_APN "ims.mnc008.mcc204.gprs" /* KPN 204-08 FQDN IMS APN (live-verified in Round 07 fb9da745: pdp_definitions apns='internet.mnc008.mcc204.gprs,ims.mnc008.mcc204.gprs'; CID2 state=1) */

enum ims_pdn_phase {
    IMS_PDN_IDLE = 0,
    IMS_PDN_SET_PROFILE,  /* GPRS SET_DATA_PROFILE (IMS DataProfile type 2, APN ims) */
    IMS_PDN_VERIFY,       /* confirm the modem managed the IMS bearer itself */
    IMS_PDN_ACTIVE,       /* IMS PDN established (modem-confirmed) */
    IMS_PDN_FAILED,
    IMS_PDN_DEFINE,
    IMS_PDN_ACTIVATE,
    IMS_PDN_RELEASE,
};

struct ims_pdn {
    ims_pdn_write_fn write;
    void *user;
    enum ims_pdn_phase phase;
    uint8_t attempt;
    uint8_t cid;         /* distinct from internet CID 1 */
    uint8_t proto;       /* IP family (IPv6 for IMS P-CSCF discovery) */
    uint8_t auth;        /* AUTH_NONE at PDP layer */
    uint8_t profile_id;  /* vendor IMS DataProfile wire id (2 = IMS/ePDN) */
    uint8_t last_write_seq, pending_sub;
    uint16_t last_result;
    struct fmt_rx_ip ip;
    uint64_t next_action_ms;
    uint64_t phase_deadline_ms;
    bool active, attached, ip_ready, pcscf_ready;
};

bool ims_pdn_open(struct ims_pdn *p, ims_pdn_write_fn write, void *user);
void ims_pdn_close(struct ims_pdn *p);
/* Advance the IMS PDN FSM. Returns the current phase. `online` = CP online +
 * writable + SIM ready. Caller feeds back correlated GEN results. */
enum ims_pdn_phase ims_pdn_tick(struct ims_pdn *p, uint64_t now_ms, bool online);
/* Feed a GEN response correlated to the last write. */
void ims_pdn_gen_result(struct ims_pdn *p, uint16_t result, uint8_t ack_seq);
/* Feed a PDP context LIST state; the caller reports whether CID is attached. */
void ims_pdn_report_cid(struct ims_pdn *p, uint8_t cid, bool attached);
void ims_pdn_report_ip(struct ims_pdn *p, const struct fmt_rx_ip *ip);
bool ims_pdn_active(const struct ims_pdn *p);
const char *ims_pdn_phase_name(enum ims_pdn_phase ph);
#endif
