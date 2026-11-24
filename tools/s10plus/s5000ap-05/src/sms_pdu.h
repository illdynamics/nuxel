/* SPDX-License-Identifier: GPL-2.0-only */
#ifndef NUXEL_SMS_PDU_H
#define NUXEL_SMS_PDU_H
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

#define SMS_MAX_PARTS 8
#define SMS_MAX_PDU 255
#define SMS_MAX_TEXT 4096
#define SMS_MAX_PEER 64

enum sms_codec_result { SMS_CODEC_OK, SMS_CODEC_INVALID, SMS_CODEC_TOO_LONG, SMS_CODEC_UNSUPPORTED };
struct sms_segment { uint8_t data[SMS_MAX_PDU]; size_t len; uint8_t reference; };
struct sms_encoded { size_t count; bool ucs2; struct sms_segment parts[SMS_MAX_PARTS]; };
/* TPDU only, without the SMSC prefix. UTF-8 input; UCS-2 rejects non-BMP text.
 * All parts request a delivery report. References are supplied by the store. */
enum sms_codec_result sms_encode(const char *to, const char *text, uint8_t first_mr,
                                 uint8_t concat_reference, struct sms_encoded *out);
enum sms_message_kind { SMS_DELIVER, SMS_STATUS_REPORT };
struct sms_decoded {
    enum sms_message_kind kind;
    char peer[SMS_MAX_PEER], text[SMS_MAX_TEXT];
    char timestamp[32], discharge[32];
    uint8_t reference, status, dcs;
    bool multipart;
    uint16_t concat_reference;
    uint8_t part, total;
};
/* Full PDU including the SMSC length byte. Output is unchanged on failure. */
enum sms_codec_result sms_decode(const uint8_t *pdu, size_t len, struct sms_decoded *out);
const char *sms_codec_name(enum sms_codec_result r);
#endif
