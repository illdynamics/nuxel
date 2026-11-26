/* SPDX-License-Identifier: GPL-2.0-only
 *
 * ims_sdm.h — native readback of the modem's carrier-provisioned IMS SDM
 * (Service Domain Manager) settings.
 *
 * The recovered IpcTxGetImsSdmSettings / Ipc41PacketBuilder GET builders
 * (BuildIpcModemSdmImsModeGet @0x353790, ...PcscfGet @0x353568, ...) issue
 * a 7-byte FMT REQUEST (type=2) at (main=10, sub). The modem answers with a
 * direct type=2 RESPONSE whose payload is the current value. This module
 * queries those values WITHOUT fabricating them and exposes only the
 * bounded, redacted result. P-CSCF/domain are carrier-provisioned; they are
 * never invented here.
 */
#ifndef NUXEL_IMS_SDM_H
#define NUXEL_IMS_SDM_H

#include <stdint.h>
#include <stddef.h>
#include <stdbool.h>
#include "fmt_tx.h"

typedef bool (*ims_sdm_write_fn)(const struct fmt_tx_frame *f, uint8_t *seq, void *user);

enum ims_sdm_phase {
    IMS_SDM_IDLE = 0,
    IMS_SDM_GET_MODE,
    IMS_SDM_GET_PCSCF,
    IMS_SDM_GET_DOMAIN,
    IMS_SDM_GET_SMSOVERIP,
    IMS_SDM_GET_SMSFMT,
    IMS_SDM_DONE,
};

struct ims_sdm {
    ims_sdm_write_fn write;
    void *user;
    enum ims_sdm_phase phase;
    uint8_t pending_sub;
    uint8_t last_write_seq;
    uint64_t next_action_ms;
    bool online_done_seen;

    /* Captured modem-provisioned values (redacted on output). */
    bool mode_valid; uint8_t mode;             /* FMT_TX_SDM_IMS_MODE_* */
    bool pcscf_valid; char pcscf[256];         /* P-CSCF FQDN/address */
    bool domain_valid; char domain[256];       /* SIP/IMS domain */
    bool smsoverip_valid; uint8_t smsoverip;   /* SMS-over-IP enable */
    bool smsfmt_valid; uint8_t smsfmt;         /* SMS-over-IP format */
};

bool ims_sdm_open(struct ims_sdm *s, ims_sdm_write_fn write, void *user);
void ims_sdm_close(struct ims_sdm *s);
/* Advance the readback. Fires the next GET query when due. Returns phase. */
enum ims_sdm_phase ims_sdm_tick(struct ims_sdm *s, uint64_t now_ms, bool online);
/* Feed a direct type=2 RESPONSE (main=10) to capture the modem's value. */
bool ims_sdm_receive(struct ims_sdm *s, uint8_t sub, uint8_t ack_seq,
                     const uint8_t *payload, size_t payload_len);
const char *ims_sdm_phase_name(enum ims_sdm_phase ph);

#endif /* NUXEL_IMS_SDM_H */
