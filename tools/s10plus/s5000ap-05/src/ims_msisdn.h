/* SPDX-License-Identifier: GPL-2.0-only
 *
 * ims_msisdn.h — bounded, standards-based decoder for USIM EF_MSISDN (6F40)
 * and MSISDN-derived IMS identity construction.
 *
 * TS 31.102 4.4.2.3 defines the EF_ADN/EF_MSISDN telephone-number encoding:
 *   [len-of-BCD-number][TON_and_NPI][BCD digits...]
 * EF_MSISDN carries the subscription-associated MSISDN (no alpha-identifier,
 * no capability/extension bytes). This decoder only extracts the dialled
 * digits (E.164 international form via TON=0x91) and NEVER emits or logs the
 * raw MSISDN. The caller must treat the returned string as subscriber PII.
 *
 * These functions are pure (no I/O) and host-testable. They never fabricate a
 * number when the EF is absent/malformed and never impersonate any subscriber.
 */
#ifndef NUXEL_IMS_MSISDN_H
#define NUXEL_IMS_MSISDN_H
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

#define IMS_MSISDN_MAX_DIGITS 15u           /* E.164 max, exclusive of '+' */
#define IMS_MSISDN_MAX_BCDBYTES 8u          /* ceil(15/2)+1 */

/* Decode an EF_MSISDN linear-fixed record into a NUL-terminated E.164 string
 * WITHOUT the leading '+' (e.g. "316xxxxxxxx"). Only the international form
 * (TON 0x91 = international, ISDN numbering) is accepted and the '+' is
 * implied; other TON/NPI forms are rejected as not applicable to this
 * USIM-based IMS identity path. Returns false (and empty out) on any
 * bounds/parity/format error. `out` capacity must be >= max_digits+1. */
bool ims_msisdn_decode(const uint8_t *ef, size_t ef_len,
                       char *out, size_t cap);
/* Build the MSISDN-based IMS public/private identity pair for a USIM-only
 * IMS registration (TS 23.003 13.3 / TS 24.229 5.1.1.1A fallback).
 * The phone number is expected WITHOUT '+'; the SIP IMPU becomes
 * sip:+<digits>@domain and the IMPI stays the IMSI-derived private identity
 * (the MSISDN is a public identity, never the digest username). */
bool ims_msisdn_impu(const char *digits, const char *domain,
                     char *out, size_t cap);
#endif

/* Parse a protected subscriber-config line of the form "MSISDN=<digits>"
 * (trailing newline already stripped by the caller). Validates the value as
 * E.164 digits only and copies it out without the '+' (same contract as
 * ims_msisdn_decode output). Pure, host-testable, never logs. Returns false
 * on any malformed short/long/non-digit value and leaves out empty. */
bool ims_msisdn_parse_conf(const char *line, char *out, size_t cap);
