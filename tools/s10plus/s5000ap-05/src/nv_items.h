/*
 * nv_items.h — S5000AP CP-NV (QBR/.nv_core) record decoder + provisioning
 * policy. SPDX-License-Identifier: GPL-2.0-only
 *
 * Historical bounded decoder for a candidate .nv_core envelope, plus checksum
 * primitives. The candidate record interpretation below is NOT a verified EFS
 * APN item schema and MUST NOT authorize provisioning or select a file offset.
 * Actual compiled NV descriptors and their item indices are independently
 * recovered by scripts/recover_cp_apn_metadata.py (DTK9 and EFUJ2).
 *
 * Candidate envelope (little endian): size, name_ptr, type, aux_ptr, data.
 * The parser is retained for offline fixtures only. Its ability to parse bytes
 * does not prove these fields describe a real item in nv_data.bin/.nv_core.
 *
 * nv_md5_hex is plain RFC 1321 MD5. Samsung's nv_data.bin.md5 is instead
 * nv_vendor_md5_hex: MD5(image || "Samsung_Android_RIL"). Neither checksum
 * authenticates an item or proves that an APN-only write is authorized.
 * Protected identity/calibration items must never be rewritten.
 */
#ifndef NUXEL_NV_ITEMS_H
#define NUXEL_NV_ITEMS_H

#include <stdint.h>
#include <stddef.h>
#include <stdbool.h>

#ifdef __cplusplus
extern "C" {
#endif

#define NV_REC_HDR_MIN   16u   /* size+name_ptr+type+aux_ptr */
#define NV_NAME_PTR_MASK 0xF0000000u

/* Data-type codes observed in .nv_core records. */
enum nv_rec_type {
    NV_TYPE_UNKNOWN = 0,
    NV_TYPE_ITEM    = 0x04,   /* scalar NV item */
    NV_TYPE_GUARD   = 0x05,
    NV_TYPE_REF     = 0x07,
    NV_TYPE_ARRAY   = 0x80,   /* 128 = array/blob record */
};

struct nv_record {
    uint32_t size;      /* total record size incl. header */
    uint32_t name_ptr;  /* CP RAM name-string pointer */
    uint32_t type;      /* data-type code */
    uint32_t aux_ptr;   /* secondary pointer (may be 0) */
    uint32_t name_span; /* classification of name_ptr range */
    bool     size_valid;   /* size within [NV_REC_HDR_MIN, cap] */
    bool     name_is_ram;  /* name_ptr looks like CP RAM/BSS/text */
};

/* Parse one .nv_core record envelope from buf[0..len). Pure.
 * Returns bytes consumed (>= NV_REC_HDR_MIN) on success, 0 on a short/invalid
 * header. Never reads past len. */
size_t nv_record_parse(const uint8_t *buf, size_t len, struct nv_record *out);

/* Recovery/classify the name_ptr into a textual span for diagnostics. */
const char *nv_name_ptr_span(uint32_t name_ptr);

/* --- MD5 integrity (the ACTUAL mechanism; no RSA/ECDSA) --- */

/* Returns the 32-char lowercase hex MD5 of buf[0..len) into out[33].
 * Returns 0 on success, -1 on NULL out. */
int nv_md5_hex(const uint8_t *data, size_t len, char out[33]);
/* Samsung sidecar checksum: MD5(image || "Samsung_Android_RIL"). */
int nv_vendor_md5_hex(const uint8_t *data, size_t len, char out[33]);

/* Compare a stored 32-hex MD5 string against the computed MD5 of data.
 * Returns 0 (match), 1 (mismatch), -1 (malformed stored hex). */
int nv_md5_verify(const uint8_t *data, size_t len, const char *stored_hex);

/* --- provisioning policy (fail-closed) --- */

enum nv_provision_decision {
    NV_PROV_ALLOW_BACKUP_READ  = 0,  /* read-only inspection / backup */
    NV_PROV_DENY_UNKNOWN_ID    = -1, /* requires a numeric ID we do not know */
    NV_PROV_DENY_PROTECTED     = -2, /* RF/cal/IMEI/identity */
    NV_PROV_DENY_NO_REFERENCE  = -3, /* no verified known-good reference */
    NV_PROV_DENY_MD5_MISMATCH  = -4, /* stored MD5 does not match (unsafe) */
};

/*
 * Decide whether a provisioning transition may proceed. `item_known` means we
 * hold the cbd/flash-item numeric ID; `item_protected` means RF/cal/IMEI.
 * `md5_ok` is the result of nv_md5_verify on the pre-image. Returns an
 * nv_provision_decision. Read-only backup is always allowed.
 */
enum nv_provision_decision nv_provision_policy(bool write_requested,
                                               bool item_known,
                                               bool item_protected,
                                               bool md5_ok);

/* --- Round-38: recovered initial-attach APN item contract --- */

/* Logical CP index 220; value size 360. The value contains a 324-byte profile,
 * NOT a plaintext APN string at byte zero. See qbr_items.h and the protocol
 * recovery document. A physical file offset is still required separately. */
#define NV_ATTACH_APN_ITEM_ID    220u
#define NV_ATTACH_APN_VALUE_SIZE 360u
#define NV_ATTACH_APN_NAME_MAX   128u

struct nv_apn_record {
    uint8_t  apn[NV_ATTACH_APN_NAME_MAX]; /* NUL-terminated APN name */
    size_t   apn_len;                     /* length excl. NUL */
    bool     valid;                        /* apn is non-empty, length in range */
};

/* Validate an APN string only. This is NOT an encoder for the 360-byte NV
 * value, and its output must never be written at an item's base offset. */
int nv_apn_record_init(struct nv_apn_record *rec, const char *apn, size_t apn_len);

#ifdef __cplusplus
}
#endif
#endif /* NUXEL_NV_ITEMS_H */
