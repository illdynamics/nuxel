/* SPDX-License-Identifier: GPL-2.0-only
 *
 * ims_iil.h — native IIL (IpcProtocol41Iil) wire contract for the S5000AP.
 *
 * The recovered stock IMS registration/SMS-over-IP path is the SEPARATE
 * "IIL" protocol endpoint (IpcProtocol41Iil) multiplexed on /dev/umts_ipc0
 * (SIPC5 FMT channel 0xEB), NOT the plain IpcProtocol41 FMT endpoint. The
 * FMT SDM_IMS_MODE (MISC sub=32) arm is REJECTED (GEN 0x8001) by this CP;
 * the IIL endpoint that stock imsservice drives is the correct bearer/auth/
 * SMS-over-IP surface.
 *
 * All layouts below are recovered from the pinned vendor RIL (libsec-ril.so
 * build 60889dd714394ae0db7c2ecc2bf2740f) disassembly of
 * IpcProtocol41Iil / IpcModem. Values are the exact vendor wire bytes; none
 * are guessed. This header only SERIALIZES frames and never transmits.
 */
#ifndef NUXEL_IMS_IIL_H
#define NUXEL_IMS_IIL_H

#include <stdint.h>
#include <stddef.h>
#include <stdbool.h>

#define IIL_TX_MAX_FRAME 1024u

/* IIL frame header is NOT `struct sipc_fmt_hdr`. Recovered from
 * IpcProtocol41Iil::IpcTxImsAuthResp/IpcTxSetPdpContext:
 *
 *   [u16 total_len][u16 msg_seq][u8 main][u8 sub][u8 type][u8 flag][payload]
 *
 * total_len includes the 8-byte header + payload. There is NO ack_seq field;
 * correlation uses the 16-bit msg_seq. Some builders prepend a payload-length
 * byte (IpcTxImsAuthResp); others place fixed-structure payload at offset 8.
 */
struct iil_frame {
    uint8_t  buf[IIL_TX_MAX_FRAME];
    size_t   len;      /* total bytes = 8 + payload_len (+1 for the extra len byte) */
    uint8_t  main_cmd;
    uint8_t  sub_cmd;
    uint8_t  cmd_type;
    uint8_t  flag;
};

/* Begin an IIL frame (8-byte header). Returns payload pointer starting at
 * buf[8], or NULL on bounds error. type is the IpcProtocol41Iil cmd_type. */
uint8_t *iil_begin(struct iil_frame *f, uint8_t main, uint8_t sub,
                   uint8_t type, uint8_t flag, size_t payload_len);

/* ---- IIL command -> wire (main, sub, type) mapping, recovered from
 * IpcProtocol41Iil::ConvertToIpcCmd @0x355d10 ----
 *
 * The IIL logical "family" name is main=112 ("IIL"), but the actual wire
 * main_cmd values are 4 / 8 / 112 after ConvertToIpcCmd:
 *   IPC_SMS_RP_SMMA     (0x1a0=416) -> msg 5000, main=4,  sub=21, type=2
 *   (subrange 0x1b5a..)            -> msg 5000, main=112, sub in {4,8,9,10,11,21,22}, type=2
 *   IPC_CP_STATE        (0x321=801) -> msg 3000, main=8,  sub=5,  type=2
 * Everything else is delegated to base IpcProtocol41::ConvertToIpcCmd.
 */
#define IIL_MAIN_IIL   112u
#define IIL_MAIN_GPRS   13u   /* IIL PDP-context commands use GPRS main=13 */
#define IIL_MAIN_SMS_RP  4u
#define IIL_MAIN_CP_STATE 8u

/* sub_cmd values recovered from IpcProtocol41Iil::GetSubCommandName @0x357208
 * for main=112 (bitmap selects sub 1..26). The wire sub values below come
 * from ConvertToIpcCmd, not from the bitmap. */
#define IIL_SUB_IMS_AUTH_RESP      2u   /* IpcTxImsAuthResp: main=112 sub=2 type=2 flag=1 */
#define IIL_SUB_GPRS_DEFINE        1u   /* IpcTxDefinePdpContext: main=13 sub=1 type=3 flag=0/1 */
#define IIL_SUB_GPRS_ACTIVATE      4u   /* IpcTxSetPdpContext: main=13 sub=4 type=3 */

/* ---- Serializers (recovered layouts) ---- */

/* IpcProtocol41Iil::IpcTxImsAuthResp(char *data, int len) @0x356218.
 * Frame: main=112, sub=2, type=2, flag=1, payload=[len byte][data len bytes].
 * data = the SIP AKA result (RES/CK/IK); never logged. */
bool iil_tx_ims_auth_resp(struct iil_frame *f, const uint8_t *data, size_t len);

/* IpcProtocol41Iil::IpcTxSendRPSMMA(char *text) @0x3570f8 → main=4 sub=21.
 * Frame: total=263, msg_seq=0, main=4, sub=21(0x15), type=2, then NUL-text. */
bool iil_tx_send_rpsmma(struct iil_frame *f, const char *text);

/* IpcProtocol41Iil::IpcTxDefinePdpContext(const char* apn, char, proto, bool,
 * uint8_t*, uint8_t*) @0x357340 → main=13 sub=1 type=3. 134-byte frame:
 *   [8] = an 8-bit selector, [9] = proto wire byte (0x05 IP / 0x06 IPV6 /
 *   0x04 IPV4V6), [10..110) = APN, sized fields for PDN info. */
bool iil_tx_define_pdp(struct iil_frame *f, const char *apn, uint8_t proto,
                       uint8_t selector, bool with_auth);

/* IpcProtocol41Iil::IpcTxSetPdpContext(uint8_t cid, ...) @0x357488 →
 * main=13 sub=4 type=3. 112-byte ACTIVATE frame; payload[8]=cid. */
bool iil_tx_set_pdp_context(struct iil_frame *f, uint8_t cid, uint8_t pdp_type);

#endif /* NUXEL_IMS_IIL_H */
