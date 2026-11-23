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
 * TX FRAMING RESOLUTION (the stage-06 "contradiction", now closed):
 * ----------------------------------------------------------------
 *  - Kernel RX already proved the CP emits `sipc_fmt_hdr` (AST_POWERON).
 *  - Kernel TX (modem_io_device.c `misc_write`) treats a userspace write as an
 *    OPAQUE payload: it `copy_from_user`'s the exact bytes then PREPENDS the
 *    SIPC5 link header via `sipc5_build_header` (when iod->link_header). It
 *    does NOT parse main/sub/type or add a checksum. So the userspace TX
 *    format is EXACTLY the same `sipc_fmt_hdr`+payload as RX.
 *  - Vendor disassembly corroborates: IpcTxGetPdpContext() and IpcTxPsAttach()
 *    build `sipc_fmt_hdr`+payload on the stack and write it via the channel
 *    vtable send ([x8,#48]). Confirmed byte layout:
 *        buf[0..1]=len, buf[2]=msg_seq, buf[3]=ack_seq,
 *        buf[4]=main, buf[5]=sub, buf[6]=type, buf[7..]=payload.
 *  - The alternative 14-byte layout with `0x0605` magic + additive checksum
 *    (IpcTxExchange @0x342a80) is a DIFFERENT inner dialogue used by a
 *    separate "exchange" path; it is NOT what the data-path IpcTx* functions
 *    emit and NOT what /dev/umts_ipc0 expects for SIM/PDP traffic. It must not
 *    be conflated with `sipc_fmt_hdr`.
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

/* worst-case FMT frame this module can build (134-byte PDP + hdr + slack) */
#define FMT_TX_MAX_FRAME 256u

/* cmd_type numeric classes (vendor enum; see ipc41_cmdmap.h) */
#define FMT_TX_TYPE_REQUEST       2u
#define FMT_TX_TYPE_NOTIFICATION  3u

/* Samsung DataProtocol (IP family) enum numeric values (recovered) */
enum fmt_tx_data_protocol {
    /* Vendor DataProtocol enum (libsec-ril, VERIFIED @0x31f580):
     * IP=2, IPV6=3, IPV4V6=4. Wire byte = 0x00040605 >> ((proto-2)*8):
     * IP(2)=0x05, IPV6(3)=0x06, IPV4V6(4)=0x04. */
    FMT_TX_PROTO_IP      = 2,
    FMT_TX_PROTO_IPV6    = 3,
    FMT_TX_PROTO_IPV4V6  = 4,
};

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

/* Query SIM ATR info. No payload (len=7). */
bool fmt_tx_get_atr(struct fmt_tx_frame *f);

/* ---- NET / registration commands (AP -> CP requests) ---- */

/* Query serving network / registration. No payload. */
bool fmt_tx_get_serving_network(struct fmt_tx_frame *f);
bool fmt_tx_get_registration(struct fmt_tx_frame *f);

/* ---- GPRS / data-path commands (AP -> CP requests) ---- */

/* GPRS PS attach/detach (main=13 sub=3, 3-byte payload).
 * attach: 1=attach, 0=detach. detach_reason: 0..4 (clamped). */
bool fmt_tx_ps_attach(struct fmt_tx_frame *f, bool attach, bool suspend,
                      uint8_t detach_reason);

/* GPRS get PDP context (query, no payload). */
bool fmt_tx_get_pdp_context(struct fmt_tx_frame *f);

/* GPRS sync profile / mobile-data (sub=29) enable/disable (9-byte frame).
 * NOTE: recovered from IpcTxSetMobileDataSetting disasm (main=13,sub=0x1d). */
bool fmt_tx_mobile_data(struct fmt_tx_frame *f, bool enable, bool extra);

/* GPRS define PDP context (134-byte frame, APN + protocol).
 * apn: NUL-terminated, <=100 chars. proto: IP family (see enum). */
bool fmt_tx_define_pdp_context(struct fmt_tx_frame *f, const char *apn,
                               uint8_t proto, uint8_t profile_id);

/* GPRS data-call establish (main=3 CDMA_DATA, sub=2 CDMA_DATA_CALL_ESTABLISH).
 * Recovered from IpcTxSetDataCallEstablish @0x320a10: 8-byte frame,
 * payload[0]=1 when establish else 2. */
bool fmt_tx_set_data_call_establish(struct fmt_tx_frame *f, bool establish);

/* GPRS always-on PDN (main=13 GPRS, sub=34 SET_ALWAYS_ON_PDN).
 * Recovered from IpcTxSetAlwaysOnPdn @0x321550: 9-byte frame,
 * payload[0]=on/off(1/0), payload[1]=profile code (region-dependent). */
bool fmt_tx_set_always_on_pdn(struct fmt_tx_frame *f, bool enable, uint8_t profile);

/* Serialize a raw FMT frame given explicit fields (validation helper). */
bool fmt_tx_raw(struct fmt_tx_frame *f, uint8_t main, uint8_t sub,
                uint8_t type, const uint8_t *payload, size_t payload_len);

#endif /* NUXEL_FMT_TX_H */
