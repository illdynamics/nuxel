/*
 * qbr_items.h — recovered S5000AP QBR (persistent NV) item dictionary.
 * SPDX-License-Identifier: GPL-2.0-only
 *
 * Round-35 recovery (item names) + Round-38 recovery (numeric NV item IDs).
 * Derived STRICTLY from the matching stock CP firmware
 * (SAMFW G975FXXS9DTK9 CP modem.bin MAIN image, ARM32 Thumb, load 0x40010000,
 * MAIN file offset 0x2260, size 0x260c170).
 *
 * This is a READ-ONLY reference dictionary. It does NOT implement, authorize,
 * or perform any NV/EFS write. Its purpose is to (a) record the vendor ABI
 * item identifiers (name + numeric ID) recovered from the firmware and (b) give
 * diagnostics a typed, length-checked way to NAME an item without fabricating
 * a numeric NV ID or an undocumented on-disk encoding.
 *
 * Corrected Round-43 contract: the table at MAIN VA 0x4014d0a4 has TWENTY
 * bytes per descriptor: name pointer, element size, element count, flags,
 * type-name pointer (five LE u32s). The previous 16-byte interpretation was
 * wrong: 360 is the record SIZE, not its ID. The hash-table initializer at
 * 0x40c92bf2 records the descriptor index; lookup at 0x40c92bb2 returns it.
 * Read at 0x40c92e76 and GetSize at 0x40c92ee2 index the table with index*20.
 * NASU.LTE.ATTACH.APN.INFO: descriptor 0x4014e1d4, index 220, 1*360 bytes.
 * DS_NASU.LTE.ATTACH.APN.INFO: 0x4014e224, index 224, 1*360 bytes.
 * These are logical CP indices, never physical offsets in nv_data.bin.
 *  - A "PROTECTED" item is RF/calibration/IMEI-adjacent and is deny-listed
 *    unconditionally. Its numeric ID is recorded ONLY for deny classification.
 *  - No function here may be used to justify a write to an unknown NV ID.
 */
#ifndef NUXEL_QBR_ITEMS_H
#define NUXEL_QBR_ITEMS_H

#include <stdint.h>
#include <stddef.h>
#include <stdbool.h>

#ifdef __cplusplus
extern "C" {
#endif

#define QBR_NAME_MAX 96u

/* Ownership/safety class of a recovered persistent item. */
enum qbr_item_class {
    QBR_CLASS_UNKNOWN    = 0,
    QBR_CLASS_APN        = 1,  /* data-session APN profile item */
    QBR_CLASS_CONFIG     = 2,  /* L3/user-plane configuration flag */
    QBR_CLASS_RF_CAL     = 3,  /* RF / calibration — PROTECTED, deny */
    QBR_CLASS_IMEI_ID    = 4,  /* identity — PROTECTED, deny */
    QBR_CLASS_NETWORK     = 5,  /* PLMN/registration state */
};

/* Sentinel: "no numeric NV item ID recovered / not addressable". */
#define QBR_NV_ID_UNKNOWN 0u

struct qbr_item {
    const char *name;              /* QBR item name (e.g. NASU.LTE.ATTACH.APN.INFO) */
    enum qbr_item_class klass;
    uint32_t nv_id;                /* numeric NV item id (QBR_NV_ID_UNKNOWN if not recovered) */
};

/* The single definitive recovered key for the LTE initial-attach APN.
 * Recovered: "NASU.LTE.ATTACH.APN.INFO" and its dual-sim variant
 * "DS_NASU.LTE.ATTACH.APN.INFO" (CP file offsets 0x46b640 / 0x46b643). */
#define QBR_ATTACH_APN_NAME    "NASU.LTE.ATTACH.APN.INFO"
#define QBR_ATTACH_APN_DS_NAME "DS_NASU.LTE.ATTACH.APN.INFO"

/* Logical indices in the exact DTK9 CP descriptor table. */
#define QBR_ATTACH_APN_NV_ID 220u
#define QBR_ATTACH_APN_DS_NV_ID 224u
#define QBR_ATTACH_APN_VALUE_SIZE 360u

/* Look up a recovered item by name. Returns NULL when the name is not part of
 * the recovered dictionary (fail-closed: unknown names are NOT addressable). */
const struct qbr_item *qbr_item_lookup(const char *name);

/* Whether an item's numeric NV ID has actually been recovered (not 0/unknown). */
static inline bool qbr_nv_id_known(const struct qbr_item *it) {
    return it != NULL && it->nv_id != QBR_NV_ID_UNKNOWN;
}

/* Whether an item class is protected (must never be written or guess-patched). */
static inline bool qbr_class_protected(enum qbr_item_class k) {
    return k == QBR_CLASS_RF_CAL || k == QBR_CLASS_IMEI_ID || k == QBR_CLASS_UNKNOWN;
}

/* Number of entries in the recovered dictionary (diagnostics/iteration). */
size_t qbr_item_count(void);
const struct qbr_item *qbr_item_at(size_t index);

#ifdef __cplusplus
}
#endif
#endif /* NUXEL_QBR_ITEMS_H */
