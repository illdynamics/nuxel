/*
 * nv_items.h — S5000AP CP-NV (QBR/.nv_core) record decoder + provisioning
 * policy. SPDX-License-Identifier: GPL-2.0-only
 *
 * Round-37 recovery, derived STRICTLY from the physical CP EFS snapshot
 * recovered from the live SM-G975F (/dev/sdd1 cpefs). This module is PURE
 * (no I/O, no write), so it can be host-fuzzed and unit-tested. It decodes
 * the on-disk NV record envelope and computes/verifies the MD5 integrity that
 * the vendor NvCore path actually applies (nv.log shows "MD5 on"/"MD5 off" toggles;
 * there is NO mandatory asymmetric signature — see reports/S5000AP-06-RESULTS).
 *
 * RECOVERED .nv_core record envelope (little-endian, observed at cpefs):
 *
 *   [u32 size][u32 name_ptr][u32 type][u32 aux_ptr][ payload ... ]
 *
 *   size      = total record size in bytes (observed 0x01,0x46,0x47,0x60,
 *               0x7e,0x80). Variable-length; never process OOB.
 *   name_ptr  = CP runtime RAM address of the item-name string (0x4160xxxx
 *               data/BSS or 0x40fcxxxx text). These are the CP's register
 *               table pointers, resolved only at CP boot.
 *   type      = small data-type/class code (observed 0x04..0x12).
 *   aux_ptr   = secondary pointer (0x4177xxxx / 0x40fcxxxx) or 0.
 *   payload   = size-(fixed header) bytes of item value.
 *
 * TRUTH CONTRACT (rounds 25-36):
 *  - Item NAMES are recovered (qbr_items.h). The numeric item-ID used by
 *    pal_Security_NV_ITEM_{Read,Write}("Item %d") is a SEPARATE proprietary
 *    cbd/flash-item key and is NOT recoverable from name ordering/offsets.
 *  - This module does NOT fabricate a numeric item ID. A provisioning attempt
 *    that requires an unknown numeric ID is classified DENY (fail-closed).
 *  - No protected NV (RF/calibration/IMEI) may ever be rewritten.
 *  - MD5 verification here proves self-consistency, NOT authenticity.
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

/* Recovered type of NV item 360 (NASU.LTE.ATTACH.APN.INFO):
 *   type_desc = "u8" (byte string), numeric_id = 0x168 (360).
 * The item VALUE is the APN name as a NUL-terminated byte string
 * (e.g. "internet"). This is the SEMANTIC contract only.
 *
 * The exact on-disk QBR serialization (length prefix / record framing inside
 * nv_data.bin) is intentionally NOT reconstructed here: it is gated by the
 * fail-closed provisioning policy (item_known now true, but the on-disk framing
 * and per-item offset must still be recovered from a known-good reference or
 * the CP QBR item metadata before any write is authorized).
 */
#define NV_ATTACH_APN_ITEM_ID    0x168u  /* 360, recovered round-38 */
#define NV_ATTACH_APN_NAME_MAX   128u

struct nv_apn_record {
    uint8_t  apn[NV_ATTACH_APN_NAME_MAX]; /* NUL-terminated APN name */
    size_t   apn_len;                     /* length excl. NUL */
    bool     valid;                        /* apn is non-empty, length in range */
};

/* Build a validated APN record from a NUL-terminated or length-bounded APN
 * string. Pure; never writes. Returns 0 on success, -1 on NULL/oversize/empty. */
int nv_apn_record_init(struct nv_apn_record *rec, const char *apn, size_t apn_len);

#ifdef __cplusplus
}
#endif
#endif /* NUXEL_NV_ITEMS_H */
