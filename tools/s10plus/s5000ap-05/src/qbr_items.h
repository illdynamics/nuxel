/*
 * qbr_items.h — recovered S5000AP QBR (persistent NV) item dictionary.
 * SPDX-License-Identifier: GPL-2.0-only
 *
 * Round-35 recovery, derived STRICTLY from the matching stock CP firmware
 * (SAMFW G975FXXS9DTK9 CP modem.bin MAIN image, ARM32 Thumb, load 0x40010000).
 * This is a READ-ONLY reference dictionary. It does NOT implement, authorize,
 * or perform any NV/EFS write. Its purpose is to (a) record the vendor ABI
 * item identifiers recovered from the firmware symbol/string tables and (b)
 * give diagnostics a typed, length-checked way to NAME an item without
 * fabricating a numeric NV ID or an undocumented on-disk encoding.
 *
 * TRUTH CONTRACT:
 *  - Item NAMES are recovered from the firmware (evidence-level). Numeric
 *    QBR item IDs and the signed on-disk encoding are NOT recovered here and
 *    MUST NOT be guessed or written blindly.
 *  - Item GROUP codes describe what subsystem owns the item; they are NOT NV
 *    IDs. A "PROTECTED" item is RF/calibration/IMEI-adjacent and is deny-
 *    listed unconditionally.
 *  - No function in this header may be used to justify a write to an unknown
 *    NV identifier.
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

struct qbr_item {
    const char *name;              /* QBR item name (e.g. NASU.LTE.ATTACH.APN.INFO) */
    enum qbr_item_class klass;
};

/* The single definitive recovered key for the LTE initial-attach APN.
 * Recovered: "NASU.LTE.ATTACH.APN.INFO" and its dual-sim variant
 * "DS_NASU.LTE.ATTACH.APN.INFO" (CP file offsets 0x46b640 / 0x46b65c /
 * 0x6c31c4 / 0x6c31e0). This is the persistent storage item that the running
 * modem reads during LTE INITIAL ATTACH to form the default EPS bearer. */
#define QBR_ATTACH_APN_NAME    "NASU.LTE.ATTACH.APN.INFO"
#define QBR_ATTACH_APN_DS_NAME "DS_NASU.LTE.ATTACH.APN.INFO"

/* Look up a recovered item by name. Returns NULL when the name is not part of
 * the recovered dictionary (fail-closed: unknown names are NOT addressable). */
const struct qbr_item *qbr_item_lookup(const char *name);

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
