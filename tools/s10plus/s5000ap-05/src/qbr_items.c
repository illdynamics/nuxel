/*
 * qbr_items.c — recovered S5000AP QBR item dictionary (read-only reference).
 * SPDX-License-Identifier: GPL-2.0-only
 */
#include "qbr_items.h"

#include <string.h>

/*
 * Recovered item names (STRICT evidence: CP firmware string/symbol tables,
 * round 35). Names only. Numeric IDs/signed encoding are intentionally absent
 * and MUST NOT be fabricated. Protected RF/calibration and identity items are
 * included ONLY so that lookups can classify-and-deny rather than guess.
 */
static const struct qbr_item g_qbr_items[] = {
    /* --- data-session APN / attach profile --- */
    { "NASU.LTE.ATTACH.APN.INFO",        QBR_CLASS_APN },
    { "DS_NASU.LTE.ATTACH.APN.INFO",     QBR_CLASS_APN },
    { "!SAEL3.LTE_VZW_APN_DISABLED_FLAG", QBR_CLASS_APN },
    { "!SAEL3_DS.LTE_VZW_APN_DISABLED_FLAG", QBR_CLASS_APN },
    { "NASU.BLOCK.APN",                  QBR_CLASS_APN },
    { "!SAEL3.Cfg.IMS.APN",              QBR_CLASS_APN },

    /* --- L3 / user-plane configuration flags --- */
    { "!SAEL3.Cfg.INTERNET_ATTACH_ENABLED", QBR_CLASS_CONFIG },
    { "SAECOMM_FLASH_LTE_INTERNET_ATTACH_ENABLED", QBR_CLASS_CONFIG },
    { "SAECOMM_FLASH_LTE_DETACH_RE_ATTACH_REQUIRED_SUPPORT", QBR_CLASS_CONFIG },
    { "SAECOMM_FLASH_LTE_MODE_UPDATE_DEATCH_SUPPORT", QBR_CLASS_CONFIG },
    { "SAECOMM_FLASH_PCO_IPV4_MTU_MAX_SIZE", QBR_CLASS_CONFIG },
    { "SAECOMM_FLASH_LTE_SET_PS_MODE_2", QBR_CLASS_CONFIG },
    { "SAECOMM_FLASH_LTE_CATS_SUPPORT",   QBR_CLASS_CONFIG },
    { "SAECOMM_FLASH_ENS_ENABLED",        QBR_CLASS_CONFIG },
    { "SAECOMM_FLASH_NR_CONFIG_MODE",     QBR_CLASS_CONFIG },
    { "SAECOMM_FLASH_PSM_MODE",           QBR_CLASS_CONFIG },

    /* --- PDNMGR flash items (namespace grouped) --- */
    { "PDNMGR_FLASH_INT_DDS",            QBR_CLASS_CONFIG },
    { "PDNMGR_FLASH_IMS_DDS",            QBR_CLASS_CONFIG },
    { "PDNMGR_FLASH_CLASS1_BACKOFFTIMER_VALUE", QBR_CLASS_CONFIG },
    { "PDNMGR_FLASH_CLASS3_BACKOFFTIMER_VALUE", QBR_CLASS_CONFIG },
    { "PDNMGR_FLASH_LTE_VZW_EXCESSIVE_PDN_MAX_CONN", QBR_CLASS_CONFIG },
    { "PDNMGR_FLASH_LTE_VZW_ERROR_MAX_CONN_T", QBR_CLASS_CONFIG },
    { "PDNMGR_FLASH_LTE_VZW_INTERNET_ATTACH_ENABLED", QBR_CLASS_CONFIG },
    { "PDNMGR_FLASH_VOICE_DOMAIN_PREF",   QBR_CLASS_CONFIG },
    { "PDNMGR_FLASH_DOMESTIC_DATA_STATUS", QBR_CLASS_CONFIG },
    { "PDNMGR_FLASH_ROAMING_DATA_STATUS", QBR_CLASS_CONFIG },
    { "PDNMGR_FLASH_IMS_OVER_WLAN_STATUS", QBR_CLASS_CONFIG },

    /* --- network / PLMN registration state --- */
    { "NASU.LAST.REGISTERED.PLMN",        QBR_CLASS_NETWORK },
    { "DS_NASU.LAST.REGISTERED.PLMN",     QBR_CLASS_NETWORK },
    { "NASU.LAST.INSERTED.IMSI",          QBR_CLASS_NETWORK },
    { "DS_NASU.LAST.INSERTED.IMSI",       QBR_CLASS_NETWORK },
    { "NASU.EF_RAT",                      QBR_CLASS_NETWORK },
    { "NASU.MODEM.STATE",                 QBR_CLASS_NETWORK },

    /* --- protected RF / calibration (deny unconditionally) ---
     * Names recovered from the NV_ITEM0..35 RF/cal region so lookups can
     * classify them correctly; these are NEVER writable NOR guess-patched. */
    { "CAL.LTE.CAL_ITEM10",               QBR_CLASS_RF_CAL },
    { "CAL.LTE.NV_ARRAY_ITEM10",          QBR_CLASS_RF_CAL },
};

const struct qbr_item *qbr_item_lookup(const char *name)
{
    size_t i;
    if (name == NULL || name[0] == '\0') return NULL;
    for (i = 0; i < sizeof(g_qbr_items) / sizeof(g_qbr_items[0]); ++i) {
        if (strcmp(g_qbr_items[i].name, name) == 0)
            return &g_qbr_items[i];
    }
    return NULL; /* fail-closed: unknown item not addressable */
}

size_t qbr_item_count(void)
{
    return sizeof(g_qbr_items) / sizeof(g_qbr_items[0]);
}

const struct qbr_item *qbr_item_at(size_t index)
{
    if (index >= qbr_item_count()) return NULL;
    return &g_qbr_items[index];
}
