/* SPDX-License-Identifier: GPL-2.0-only
 *
 * iil_pdn.h — IIL IMS APN PDN driver. Establishes the isolated CID-2 IMS
 * bearer using the recovered IIL (IpcProtocol41Iil) wire contract, NOT the
 * FMT GPRS path that was proven to stall at WAIT_IP/Verify on this CP.
 *
 * The serializers (iil_tx_define_pdp / iil_tx_set_pdp_context) are the
 * emulation-verified byte-exact builders the stock imsservice uses. This
 * module drives SET_DATA_PROFILE(IMS type 2) -> DEFINE -> ACTIVATE ->
 * (observe Connected/Parameters RX) and only reports active once the modem
 * confirms the CID-2 attach + IP + P-CSCF, mirroring IpcRxIilConnected /
 * IpcRxIilParameters.
 *
 * SET_DATA_PROFILE (main=13 sub=27) is a GPRS command multiplexed on the
 * ordinary FMT endpoint and is NOT part of the IIL serializer set; it must be
 * emitted through the caller-supplied FMT write callback so the modem's IMS
 * DataProfile (wire type 2, label "ims") is synced before the IIL Define/
 * Activate sequence. A profile acknowledgement is never treated as bearer
 * readiness; only the Connected + Parameters events are.
 */
#ifndef NUXEL_IIL_PDN_H
#define NUXEL_IIL_PDN_H
#include <stdint.h>
#include <stdbool.h>
#include "ims_iil.h"
#include "ims_iil_rx.h"
#include "fmt_tx.h"

typedef bool (*iil_pdn_write_fn)(const struct iil_frame *f, uint8_t *seq, void *user);
/* Optional FMT write callback for the GPRS SET_DATA_PROFILE(IMS) sync frame.
 * NULL is allowed for offline/build-only use; a live run requires it so the
 * modem learns the IMS DataProfile before IIL Define/Activate. */
typedef bool (*iil_pdn_fmt_write_fn)(const struct fmt_tx_frame *f, uint8_t *seq, void *user);

#define IIL_PDN_CID 2u
#define IIL_PDN_APN "ims.mnc008.mcc204.gprs"
/* The recovered IpcTxImsReqSetImsPdnInfoE911 apn field is a 21-byte strlcpy
 * (dlen 21, so 20 chars + NUL). The IMS bearer APN above is 22 chars and does
 * NOT fit; the modem internal-IMS provisioning contract is the 3GPP well-known
 * IMS APN "ims", not the operator DN. This value is standard (TS 23.003 9.2). */
#define IIL_PDN_E911_PROV_APN "ims"

enum iil_pdn_phase {
    IIL_PDN_IDLE = 0,
    IIL_PDN_SET_PROFILE, /* FMT SET_DATA_PROFILE(IMS type 2) sync of the modem DataProfile */
    IIL_PDN_PROVISION,   /* fire IpcTxImsReqSetImsPdnInfoE911 (main=112 sub=10) */
    IIL_PDN_DEFINE,
    IIL_PDN_ACTIVATE,
    IIL_PDN_VERIFY,
    IIL_PDN_ACTIVE,
    IIL_PDN_FAILED,
};

struct iil_pdn {
    iil_pdn_write_fn write;
    iil_pdn_fmt_write_fn fmt_write;
    void *user;
    void *fmt_user;
    enum iil_pdn_phase phase;
    uint8_t attempt;
    uint8_t cid;
    uint8_t last_write_seq;      /* msg_seq assigned on the last write (IIL or FMT) */
    uint8_t last_write_kind;     /* 0=IIL, 1=FMT; used for correlated GEN ack routing */
    uint16_t last_result;        /* GEN result correlated to the last write */
    uint64_t phase_deadline_ms;
    bool attached, ip_ready, pcscf_ready;
    int family;
    uint8_t ip[16];
    uint8_t prefix;
    uint8_t pcscf[4][16];
    uint8_t pcscf_len[4];
    unsigned pcscf_count;
};

bool iil_pdn_open(struct iil_pdn *p, iil_pdn_write_fn write, void *user);
/* Set the optional FMT write callback + user for the IMS DataProfile sync. */
void iil_pdn_set_fmt_write(struct iil_pdn *p, iil_pdn_fmt_write_fn fmt_write,
                           void *fmt_user);
void iil_pdn_close(struct iil_pdn *p);
enum iil_pdn_phase iil_pdn_tick(struct iil_pdn *p, uint64_t now_ms, bool online);
/* Feed a GEN result correlated to the last write (ack_seq matches). Works for
 * both the FMT SET_DATA_PROFILE and the IIL Define/Activate acks. */
void iil_pdn_gen_result(struct iil_pdn *p, uint16_t result, uint8_t ack_seq);
/* Feed the IIL Connected and Parameters events (from the RX path). */
void iil_pdn_on_connected(struct iil_pdn *p, const struct iil_rx_event *e);
void iil_pdn_on_parameters(struct iil_pdn *p, const struct iil_rx_event *e);
bool iil_pdn_active(const struct iil_pdn *p);
const char *iil_pdn_phase_name(enum iil_pdn_phase ph);
#endif /* NUXEL_IIL_PDN_H */
