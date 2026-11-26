/* SPDX-License-Identifier: GPL-2.0-only
 *
 * ims_iil.h — native IIL (IpcProtocol41Iil) wire contract for the S5000AP.
 *
 * The recovered stock IMS registration/SMS-over-IP path is the SEPARATE
 * "IIL" endpoint (IpcProtocol41Iil) multiplexed on /dev/umts_ipc0 (SIPC5
 * FMT channel 0xEB), NOT the plain IpcProtocol41 FMT endpoint. The FMT
 * SDM_IMS_MODE (MISC sub=32) arm is REJECTED (GEN 0x8001) by this CP; the
 * IIL endpoint that stock imsservice drives is the correct bearer/auth/
 * SMS-over-IP surface.
 *
 * All layouts below are EMULATION-VERIFIED against the pinned vendor RIL
 * (libsec-ril.so build 60889dd714394ae0db7c2ecc2bf2740f) using the Unicorn
 * machine — see tools/s10plus/s5000ap-05/tests/check_vendor_usim.py for the
 * harness. Values are exact captured wire bytes; none are guessed.
 *
 * IIL frame header (7 bytes, distinct from sipc_fmt_hdr):
 *   [u16 total_len][u16 msg_seq][u8 main][u8 sub][u8 type][payload]
 * (FMT uses [u8 msg_seq][u8 ack_seq]; IIL uses a 16-bit msg_seq, no ack_seq.)
 * Some builders append flag/length bytes as payload (IpcTxImsAuthResp); see
 * each serializer.
 */
#ifndef NUXEL_IMS_IIL_H
#define NUXEL_IMS_IIL_H

#include <stdint.h>
#include <stddef.h>
#include <stdbool.h>

#define IIL_TX_MAX_FRAME 2384u

struct iil_frame {
    uint8_t  buf[IIL_TX_MAX_FRAME];
    size_t   len;      /* total bytes = 7 (header) + payload */
    uint8_t  main_cmd;
    uint8_t  sub_cmd;
    uint8_t  cmd_type;
};

/* Begin a 7-byte IIL frame. Returns payload pointer at buf[7]. */
uint8_t *iil_begin(struct iil_frame *f, uint8_t main, uint8_t sub,
                   uint8_t type, size_t payload_len);

/* Wire main_cmd values verified by emulation:
 *   IpcTxImsAuthResp -> main=112 sub=2 type=2
 *   IpcTxSendRPSMMA   -> main=4   sub=21(type=3 notification)
 * (IpcProtocol41Iil::ConvertToIpcCmd @0x355d10 also maps the IIL subrange to
 *  main=112 and IPC_CP_STATE(801) to main=8 sub=5.) */
#define IIL_MAIN_IIL     112u
#define IIL_MAIN_SMS_RP    4u
#define IIL_SUB_IMS_AUTH_RESP  2u
#define IIL_SUB_RPSMMA        21u
#define IIL_MAIN_GPRS         13u
#define IIL_SUB_GPRS_DEFINE    1u
#define IIL_SUB_GPRS_ACTIVATE  4u

/* IpcTxImsAuthResp(char* data, int len) — main=112 sub=2 type=2.
 * Payload = [flag=1][len byte][data]. Emulation-verified frame:
 *   19 00 00 00 70 02 02 | 01 10 <16 data bytes>. `data` is the SIP AKA
 *   result (RES/CK/IK); never logged. */
bool iil_tx_ims_auth_resp(struct iil_frame *f, const uint8_t *data, size_t len);

/* IpcTxDefinePdpContext(const char* apn, char, proto, bool, uint8_t*, uint8_t*)
 * — main=13(GPRS) sub=1 type=3, 134-byte frame, 8-byte header (flag=1).
 * Payload: [char=0][proto wire byte][APN NUL-padded]. Emulation-verified:
 *   86 00 00 00 0d 01 03 01 | 00 06 "ims.mnc008.mcc204.gprs" ... */
bool iil_tx_define_pdp(struct iil_frame *f, const char *apn, uint8_t proto,
                       uint8_t flag0);

/* IpcTxSetPdpContext(uint8_t cid, ...) — main=13 sub=4 type=3, 112-byte
 * frame, 8-byte header (flag=1). Payload: [cid][0x11][0][0][0][APN ...].
 * Emulation-verified (cid=2): 70 00 00 00 0d 04 03 01 | 02 11 00 00 00
 * "ims.mnc008.mcc204.gprs" ... */
bool iil_tx_set_pdp_context(struct iil_frame *f, uint8_t cid, const char *apn);

/* IpcTxSendRPSMMA(char* text) — main=4 sub=21 type=3 (notification).
 * Payload = NUL-terminated text at offset 7, zero-padded to 263 total.
 * Emulation-verified frame: 07 01 00 00 04 15 03 "hello". */
bool iil_tx_send_rpsmma(struct iil_frame *f, const char *text);

/* IpcTxImsReqSetImsPdnInfoE911 @0x355fe0 (IpcProtocol41Iil) — the modem's
 * INTERNAL IMS-stack provisioning trigger. main=112 sub=10 type=1, total_len
 * 2332. Recovered AArch64 disassembly (exact, NULL-invariant, not guessed):
 *
 *   [0..1]  total_len = 2332 (0x091c)
 *   [2..3]  msg_seq   (assigned by the shared endpoint counter at send)
 *   [4]     main = 112
 *   [5]     sub  = 10
 *   [6]     type = 1
 *   [7..27]   apn (21 bytes, strlcpy dstsize 21, NUL-padded)
 *   [28..283] config[0] (256 bytes)
 *   [284..539] config[1] (256)
 *   [540..795] config[2] (256)
 *   [796..1051] config[3] (256)
 *   [1052..1307] config[4] (256)
 *   [1308..1563] config[5] (256)
 *   [1564..1819] config[6] (256)
 *   [1820..2075] config[7] (256)
 *   [2076..2331] e911_tail (256 bytes)
 *
 * Field strides are 0x100 (256) bytes from config[0] at offset 28; the apn
 * field is the single 21-byte strlcpy the vendor emitted (`mov w2,#0x15`).
 * Config strings are carrier-provisioned; pass NULL/"" for fields the AP
 * does not authoritatively hold so the modem keeps its own NVRAM default.
 * Never fabricated, never a secret channel. */
bool iil_tx_ims_set_pdn_info(struct iil_frame *f, const char *apn,
                             const char *const config[8], const char *e911_tail);

#endif /* NUXEL_IMS_IIL_H */
