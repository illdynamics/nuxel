/*
 * mbim_tx.h — S5000AP MBIM<->SIPC transport + MBIM message builders.
 *
 * SPDX-License-Identifier: GPL-2.0-only
 *
 * Recovered this round (round-31) from the EXACT vendor RIL
 *   .vendor-ro/libsec-ril.so  (BuildID 60889dd714394ae0db7c2ecc2bf2740f)
 * via aarch64-linux-gnu-objdump on the local copy (same hash the previous
 * rounds fingerprinted). The MBIM host is compiled INTO libsec-ril.so
 * (MbimManager / MbimAdaptor / MbimRespBuilder / RawIpc); there is no
 * separate "/vendor/bin/libsecmbim" binary (correcting the round-28/30
 * "missing proprietary binary" conclusion).
 *
 * KEY RECOVERED FACTS (see reports/S5000AP-06-ROUND31-MBIM-SIPC-RECOVERED.md):
 *
 *  1. MBIM messages are carried over the EXISTING RIL SIPC FMT channel as a
 *     RAW-IPC forward:
 *       MbimManager::DoOemRawIpc -> ModemProxy::SendRawIpc (vtable #2368)
 *         -> IpcModem::SendRawIpc @0x307f38
 *         -> IpcProtocol41::IpcTxRawIpc @0x3180f0
 *     IpcTxRawIpc validates/emits a SIPC FORMAT frame with:
 *         main_cmd = 0x16 (22)   RAW-IPC / MBIM forward
 *         sub_cmd  = 0x0c (12)
 *         cmd_type = 0x05 (5)    RAW-IPC class
 *         [+7]     = forward flag / sub-func id byte
 *         [+8 .. ] = the raw MBIM message payload
 *     Response path: MbimManager::OnMbimRawIpcReceived (via
 *     ModemProxy::RegisterForRawIpc), payload at RawIpc+0xc.
 *
 *  2. The RawIpc object stores the MBIM payload at offset 0xc (12); its length
 *     at +8204/+8208. The FMT header bytes precede the payload.
 *
 *  3. MBIM "MS LTE Attach Config" (Microsoft/USB-IF CID 0x0000000A) is built
 *     by MbimAdaptor::MakeSetMsLteAttachConfig @0x1c3018 as a 984-byte
 *     MbimMsLteAttachConfigData holding 3 * 324-byte MbimMsLteAttachContextData
 *     (constructor @0x2c0e90), then serialized by MbimRespBuilder::
 *     FillMbimMsLteAttachConfig @0x2d6158 -> FillMbimMsLteAttachContext
 *     @0x2d5e18 into the standard MBIM info buffer.
 *
 *  4. MbimMsLteAttachContextData field layout (324 = 0x144 bytes):
 *         +0x00  u32 contextId / element index
 *         +0x04  u32 ipType (MbimContextIpType: 3=IPv4, 6=IPv6, 5=IPv4v6)
 *         +0x08  u32 auth (MbimAuthProtocol: 0=none, 1=PAP, 2=CHAP)
 *         +0x14  char[]  APN        (per context; 0x65 = 101 bytes)
 *         +0x79  char[]  username
 *         +0xdd  char[]  password
 *
 *  5. The serialized MBIM context (MbimMsLteAttachContext) is:
 *         +0x00 u32 context index
 *         +0x04 u32 ipType
 *         +0x08 u32 authProtocol
 *         +0x0c u32 offset to APN (UTF-16LE)
 *         +0x10 u32 APN length (UTF-16LE bytes)
 *         +0x14 u32 offset to username (UTF-16LE)
 *         +0x18 u32 username length (UTF-16LE bytes)
 *         +0x1c u32 offset to password (UTF-16LE)
 *         +0x20 u32 password length (UTF-16LE bytes)
 *         +0x24 u32 compression / spare word
 *         +0x28 u32 spare word
 *         +0x2c ... UTF-16LE strings (APN, username, password), each 4-byte
 *                  aligned per the recovered FillMbimMsLteAttachContext code.
 *
 *  SAFETY: builders only SERIALIZE into a caller buffer; they never open a
 *  device or transmit. A separate, explicitly-authorized caller decides
 *  whether and when to write, and every write is bounded + policy-gated (the
 *  existing transport.c / radiod.c --write-enable path).
 */
#ifndef NUXEL_MBIM_TX_H
#define NUXEL_MBIM_TX_H

#include <stdint.h>
#include <stddef.h>
#include <stdbool.h>

/* MBIM transfer types (USB MBIM specification). */
#define MBIM_MSG_TYPE_OPEN           0x00000001u
#define MBIM_MSG_TYPE_CLOSE          0x00000002u
#define MBIM_MSG_TYPE_COMMAND        0x00000003u
#define MBIM_MSG_TYPE_HOST_ERROR     0x00000004u
#define MBIM_MSG_TYPE_INDICATE_STATUS 0x00000007u

/* Standard MBIM CIDs (USB-IF MBIM v1.0). */
#define MBIM_CID_DEVICE_CAPS            0x00000001u
#define MBIM_CID_SUBSCRIBER_READY_STATUS 0x00000002u
#define MBIM_CID_RADIO_STATE            0x00000003u

/* Microsoft MBIM extension CIDs. */
#define MBIM_CID_MS_LTE_ATTACH_CONFIG  0x0000000Au
#define MBIM_CID_MS_LTE_ATTACH_STATUS  0x0000000Bu

/* MbimContextIpType (USB MBIM spec). */
#define MBIM_CONTEXT_IP_TYPE_DEFAULT 0u
#define MBIM_CONTEXT_IP_TYPE_IPV4    3u
#define MBIM_CONTEXT_IP_TYPE_IPV6    6u
#define MBIM_CONTEXT_IP_TYPE_IPV4V6  5u

/* MbimAuthProtocol (USB MBIM spec). */
#define MBIM_AUTH_PROTOCOL_NONE  0u
#define MBIM_AUTH_PROTOCOL_PAP   1u
#define MBIM_AUTH_PROTOCOL_CHAP  2u
#define MBIM_AUTH_PROTOCOL_MSCHAPV2 3u

/*
 * SIPC FORMAT raw-IPC (MBIM forward) frame header bytes, recovered from
 * IpcProtocol41::IpcTxRawIpc @0x3180f0. These are the FMT main/sub/type
 * (see sipc5_fmt.h struct sipc_fmt_hdr) for the MBIM-over-SIPC channel.
 */
#define MBIM_RAW_IPC_MAIN_CMD  0x16u /* 22 */
#define MBIM_RAW_IPC_SUB_CMD   0x0cu /* 12 */
#define MBIM_RAW_IPC_CMD_TYPE  0x05u /* 5  */
#define MBIM_RAW_IPC_FWD_FLAG  0x01u /* forward-flag byte at FMT hdr[+7] */

/* Bound the largest MBIM frame this module emits (3 contexts + 12-byte MBIM
 * header + 7-byte FMT header + slack). */
#define MBIM_TX_MAX_FRAME 1024u

/* A single initial-attach context (internet APN + optional user/pass). */
struct mbim_attach_context {
    const char *apn;      /* UTF-8; required, non-empty */
    const char *username; /* may be NULL/empty */
    const char *password; /* may be NULL/empty */
    uint32_t    ip_type;  /* MBIM_CONTEXT_IP_TYPE_* */
    uint32_t    auth;     /* MBIM_AUTH_PROTOCOL_* */
};

/*
 * Build the raw MBIM "MS LTE Attach Config" (CID 0x0A) command payload into
 * `out` (capacity `cap`). Returns total MBIM bytes written, or 0 on overflow
 * / invalid input. The output begins with the 12-byte MBIM message header
 * [u32 type=COMMAND][u32 length][u32 transaction_id] followed by the MBIM
 * command header [u32 CID][u32 command_type=SET] and the information buffer.
 * `contexts`/`ncontexts` (1..3) describe the attach contexts (index 0 is the
 * default internet bearer context).
 */
size_t mbim_tx_build_lte_attach_config(uint8_t *out, size_t cap,
                                       const struct mbim_attach_context *contexts,
                                       size_t ncontexts, uint32_t transaction_id);

/*
 * Wrap a raw MBIM payload (`mbim`, `mbim_len`) in the SIPC FORMAT raw-IPC
 * frame that IpcTxRawIpc emits. Output: 7-byte sipc_fmt_hdr with
 * main=0x16/sub=0x0c/type=0x05, a 1-byte forward flag, then the MBIM payload.
 * Returns total frame bytes (FMT header + flag + payload), or 0 on overflow.
 * seq/ack are the sipc_fmt_hdr sequence fields (caller-managed).
 */
size_t mbim_tx_build_raw_ipc_frame(uint8_t *out, size_t cap,
                                   const uint8_t *mbim, size_t mbim_len,
                                   uint8_t seq, uint8_t ack);

/*
 * Convert a UTF-8 string to UTF-16LE into `out` (capacity `cap16` in bytes).
 * Returns bytes written (always even), or 0 on overflow. No NUL terminator is
 * emitted (MBIM offset/size pairs are explicit).
 */
size_t mbim_tx_utf8_to_utf16le(uint8_t *out16, size_t cap16,
                               const char *s, size_t max_bytes);

#endif /* NUXEL_MBIM_TX_H */

/* ------------------------------------------------------------------------- */
/* MBIM session control-plane primitives (USB-IF MBIM v1.0 spec, §10.5).      */
/* These are the control messages the native host must issue BEFORE a CID      */
/* command (such as MS LTE Attach Config) to establish the MBIM session that   */
/* the S5000AP CP expects. Recovered cross-check: the vendor MbimManager does   */
/* not build these itself (it only forwards pre-formed MBIM payloads via       */
/* SendRawIpc/DoOemRawIpc); the session handshake is performed by the MBIM      */
/* host (libsecmbim) ahead of the first proprietary CID.                      */
/* ------------------------------------------------------------------------- */

/* Standard MBIM OPEN information element: max_control_transfer (u32) the host
 * will accept. The vendor uses 4096; the spec minimum is 512. */
#define MBIM_MAX_CONTROL_TRANSFER 4096u

/* Build an MBIM OPEN message (16 bytes total):
 *   [u32 type=OPEN][u32 length=16][u32 transaction_id][u32 max_control_transfer]
 * Returns 16 on success, 0 on overflow. */
size_t mbim_tx_build_open(uint8_t *out, size_t cap, uint32_t transaction_id,
                          uint32_t max_control_transfer);

/* Build an MBIM CLOSE message (12 bytes total):
 *   [u32 type=CLOSE][u32 length=12][u32 transaction_id]
 * Returns 12 on success, 0 on overflow. */
size_t mbim_tx_build_close(uint8_t *out, size_t cap, uint32_t transaction_id);

/* Build an MBIM "MS Device Caps" query (QUERY, no info buffer; Microsoft CID
 * 0x00000001). The standard MBIM init sequence queries device caps + version
 * before issuing commands. */
size_t mbim_tx_build_caps_query(uint8_t *out, size_t cap, uint32_t transaction_id);

/* Build an MBIM "MS Subscriber Ready State" style status query — the generic
 * QUERY command header for an extension CID (used for the vendor attach-status
 * read-back path: CID 0x0B = MBIM_CID_MS_LTE_ATTACH_STATUS). */
size_t mbim_tx_build_query(uint8_t *out, size_t cap, uint32_t transaction_id,
                           uint32_t cid);
