/*
 * test_qbr_items.c — golden-vector + safety tests for the recovered QBR item
 * dictionary (round 35). SPDX-License-Identifier: GPL-2.0-only
 */
#include "qbr_items.h"
#include <string.h>
#include <stdio.h>

static int g_fail = 0;
#define CHECK(cond, msg) do { \
    if (!(cond)) { g_fail++; fprintf(stderr, "FAIL %s:%d: %s\n", __FILE__, __LINE__, msg); } \
} while (0)

int main(void)
{
    const struct qbr_item *it;

    /* Golden vector: the definitive initial-attach APN key MUST resolve and
     * MUST classify as APN (not config, not protected). */
    it = qbr_item_lookup(QBR_ATTACH_APN_NAME);
    CHECK(it != NULL, "NASU.LTE.ATTACH.APN.INFO must be in dictionary");
    if (it) {
        CHECK(it->klass == QBR_CLASS_APN, "attach APN key class == APN");
        CHECK(strcmp(it->name, "NASU.LTE.ATTACH.APN.INFO") == 0, "name roundtrip");
        /* Round-38: numeric NV item ID recovered from CP flash-item table. */
        CHECK(it->nv_id == QBR_ATTACH_APN_NV_ID, "attach APN numeric NV id == 360");
        CHECK(it->nv_id == 0x168u, "attach APN numeric NV id == 0x168");
        CHECK(qbr_nv_id_known(it), "attach APN numeric NV id is known");
    }

    it = qbr_item_lookup(QBR_ATTACH_APN_DS_NAME);
    CHECK(it != NULL, "DS_NASU.LTE.ATTACH.APN.INFO must be in dictionary");
    if (it) {
        CHECK(it->klass == QBR_CLASS_APN, "DS attach APN key class == APN");
        CHECK(it->nv_id == QBR_ATTACH_APN_NV_ID, "DS attach APN numeric NV id == 360");
    }

    /* Config flag recovered from the flash-item table. */
    it = qbr_item_lookup("!SAEL3.Cfg.INTERNET_ATTACH_ENABLED");
    CHECK(it != NULL, "INTERNET_ATTACH_ENABLED key present");
    if (it) {
        CHECK(it->klass == QBR_CLASS_CONFIG, "flag class == CONFIG");
        CHECK(!qbr_nv_id_known(it), "INTERNET_ATTACH_ENABLED numeric id still unknown");
        CHECK(it->nv_id == QBR_NV_ID_UNKNOWN, "unknown id == QBR_NV_ID_UNKNOWN");
    }

    /* Protected RF/calibration item must be classified protected. */
    it = qbr_item_lookup("CAL.LTE.CAL_ITEM10");
    CHECK(it != NULL, "CAL.LTE.CAL_ITEM10 present (for deny classification)");
    if (it) CHECK(qbr_class_protected(it->klass), "RF/cal item is protected");

    /* Fail-closed: unknown / fabricated names are not addressable. */
    CHECK(qbr_item_lookup("") == NULL, "empty name -> NULL");
    CHECK(qbr_item_lookup(NULL) == NULL, "NULL name -> NULL");
    CHECK(qbr_item_lookup("FAKE.NV.ITEM") == NULL, "unknown item -> NULL");
    CHECK(qbr_item_lookup("NV_ITEM_APN_GUESS") == NULL, "guessed NV id -> NULL");

    /* Protected classification helper is defensive. */
    CHECK(qbr_class_protected(QBR_CLASS_RF_CAL) == true, "RF_CAL protected");
    CHECK(qbr_class_protected(QBR_CLASS_IMEI_ID) == true, "IMEI protected");
    CHECK(qbr_class_protected(QBR_CLASS_UNKNOWN) == true, "UNKNOWN protected (fail-closed)");
    CHECK(qbr_class_protected(QBR_CLASS_APN) == false, "APN not 'protected' class");
    CHECK(qbr_class_protected(QBR_CLASS_CONFIG) == false, "CONFIG not 'protected' class");

    /* Iteration is consistent. */
    {
        size_t n = qbr_item_count();
        size_t i;
        CHECK(n > 0, "dictionary non-empty");
        for (i = 0; i < n; ++i) {
            const struct qbr_item *e = qbr_item_at(i);
            CHECK(e != NULL && e->name != NULL, "valid entry");
        }
        CHECK(qbr_item_at(n) == NULL, "out-of-range -> NULL");
    }

    if (g_fail == 0) { printf("test_qbr_items: all PASS\n"); return 0; }
    fprintf(stderr, "test_qbr_items: %d FAILURES\n", g_fail);
    return 1;
}
