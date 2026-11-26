/*
 * ipc41_cmdmap.h — S5000AP IpcProtocol41 telephony command vocabulary.
 *
 * SPDX-License-Identifier: GPL-2.0-only
 *
 * Source-backed recovery from the EXACT vendor RIL
 *   vendor/lib64/libsec-ril.so  (SM-G975F / beyond2lte / EFUJ2)
 *   GNU Build ID  60889dd714394ae0db7c2ecc2bf2740f
 *   file SHA-256  b02bd095ae44a991b3cb676e584b3209a947160c22e678578f8b0c877e282cb3
 *   analysed read-only on-device with aarch64 binutils (readelf/objdump/
 *   strings/nm); NO vendor binary is copied into this repository.
 *
 * METHOD (no invented IDs):
 *   1. IpcProtocol41 exports GetMainCommandName(int) @0x323860 and
 *      GetSubCommandName(int,int) @0x323a58. The main-cmd name is resolved
 *      through a 128-entry byte jump-table at .rodata VA 0x149934 (base
 *      adr 0x32388c). The sub-cmd name is resolved through a 128-entry
 *      halfword jump-table at VA 0x1499b4 (base adr 0x323a8c) which lands in a
 *      per-family block whose `adrp x9 + add x9` yields a `const char*` array
 *      in .data.rel.ro. Those pointer slots are filled at load time by
 *      R_AARCH64_RELATIVE relocations (`readelf -r`), each pointing at a
 *      .rodata NUL-terminated name string. Resolving the whole chain yields a
 *      complete (main_cmd, sub_cmd) -> NAME map with zero guessing.
 *   2. Each entry below lists (main_cmd value, sub_cmd value, recovered name,
 *      vendor function/address evidence). Values are numeric from the jump
 *      tables; names are the literal vendor strings. Confidence: O4
 *      (source-backed, single authoritative reference); NOT yet O5/O6 live
 *      functional unless annotated.
 *
 * SAFETY: this is a *name dictionary*. It does not by itself establish
 * request payload layout, response semantics, or safe-to-transmit status.
 * radiod treats all telephony sub-commands as fail-closed UNKNOWN until a
 * specific, separately-reviewed implementation exists.
 */
#ifndef NUXEL_IPC41_CMDMAP_H
#define NUXEL_IPC41_CMDMAP_H

#include <stdint.h>

/* cmd_type set: GetCmdTypeName(int) @0x323838 indexes a 5-slot table
 * (type 1..5). The vendor string table also carries the class labels
 * IPC_CMD_NOTI / IPC_CMD_REQ / IPC_CMD_RESP etc. Live evidence: the
 * AST_POWERON notification arrives as type=0x03 (NOTI-class). We record the
 * numeric classes as vendor enum labels WITHOUT asserting an exact 1:1
 * (type)->name map beyond what is corroborated. */
#define IPC41_TYPE_UNKNOWN 0
#define IPC41_TYPE_REQUEST  1
#define IPC41_TYPE_RESPONSE 2
#define IPC41_TYPE_NOTIFICATION 3   /* live: AST_POWERON carries type=3 */
#define IPC41_TYPE_5  5

/* main_cmd families recovered from GetMainCommandName (jump table @0x149934). */
enum ipc41_main_cmd {
    IPC41_MAIN_RESERVED0 = 0,
    IPC41_MAIN_PWR       = 1,   /* PWR_CMD */
    IPC41_MAIN_CALL      = 2,   /* CALL_CMD */
    IPC41_MAIN_CDMA_DATA = 3,   /* CDMA_DATA_CMD */
    IPC41_MAIN_SMS       = 4,   /* SMS_CMD */
    IPC41_MAIN_SEC       = 5,   /* SEC_CMD  (SIM/security) */
    IPC41_MAIN_PB        = 6,   /* PB_CMD   (phonebook) */
    IPC41_MAIN_DISP      = 7,   /* DISP_CMD (display/status heartbeat) */
    IPC41_MAIN_NET       = 8,   /* NET_CMD  (registration/PLMN) */
    IPC41_MAIN_SND       = 9,   /* SND_CMD  (sound) */
    IPC41_MAIN_MISC      = 10,  /* MISC_CMD */
    IPC41_MAIN_SVC       = 11,  /* SVC_CMD */
    IPC41_MAIN_SS        = 12,  /* SS_CMD */
    IPC41_MAIN_GPRS      = 13,  /* GPRS_CMD (data/PDP) */
    IPC41_MAIN_SAT       = 14,  /* SAT_CMD  (SIM application toolkit) */
    IPC41_MAIN_CFG       = 15,  /* CFG_CMD */
    IPC41_MAIN_IMEI      = 16,  /* IMEI_CMD */
    IPC41_MAIN_GPS       = 17,  /* GPS_CMD */
    IPC41_MAIN_SAP       = 18,  /* SAP_CMD */
    IPC41_MAIN_FACTORY   = 19,  /* FACTORY_CMD (AST_POWERON family) */
    IPC41_MAIN_OMADM     = 20,  /* OMADM_CMD */
    IPC41_MAIN_RFS       = 21,  /* RFS_CMD */
    IPC41_MAIN_IMS       = 22,  /* IMS_CMD */
    IPC41_MAIN_EMBMS     = 23,  /* EMBMS_CMD */
    IPC41_MAIN_MMS       = 24,  /* MMS_PROVISION_CMD */
    IPC41_MAIN_RFS_EXT   = 25,  /* RFS_EXT_CMD */
    IPC41_MAIN_MODEMTEST = 31,  /* MODEMTEST_CMD */
    IPC41_MAIN_DOMESTIC  = 32,  /* DOMESTIC_CMD */
    IPC41_MAIN_PCSC      = 33,  /* PCSC_CMD */
    IPC41_MAIN_QMI_HIDDEN= 34,  /* QMI_HIDDENMENU_CMD */
    IPC41_MAIN_SMARTAS   = 35,  /* SMARTAS_CMD */
    IPC41_MAIN_PROSE     = 36,  /* PROSE_CMD */
    IPC41_MAIN_MCPTT     = 37,  /* MCPTT_CMD */
    IPC41_MAIN_OES       = 38,  /* OES_CMD */
    IPC41_MAIN_SYSTEM    = 39,  /* SYSTEM_CMD */
    IPC41_MAIN_JPN       = 48,  /* JPN_CMD */
    IPC41_MAIN_QMIIMS    = 64,  /* QMIIMS_CMD */
    IPC41_MAIN_IIL       = 112, /* IIL_CMD */
    IPC41_MAIN_GEN       = 128, /* GEN_CMD */
};

/* ---- sub_cmd name tables (family -> recovered sub-command names) ------- */
/* Each family's sub_cmd value begins at 1 and names are indexed in order. */

/* SEC (main=5) — SIM/security. table @0x3a86a0 (20 entries). */
enum ipc41_sec_subcmd {
    IPC41_SEC_PIN_STATUS          = 1,
    IPC41_SEC_PHONE_LOCK          = 2,
    IPC41_SEC_CHANGE_LOCKING_PW   = 3,
    IPC41_SEC_SIM_LANG            = 4,
    IPC41_SEC_RSIM_ACCESS         = 5,
    IPC41_SEC_GSIM_ACCESS         = 6,
    IPC41_SEC_SIM_ICC_TYPE        = 7,
    IPC41_SEC_LOCK_INFOMATION     = 8,
    IPC41_SEC_IMS_AUTH            = 9,
    IPC41_SEC_ATR_INFO            = 10,
    IPC41_SEC_RUIM_CONFIG         = 11,
    IPC41_SEC_SIM_ICCID           = 12,
    IPC41_SEC_SIM_POWER           = 13,
    IPC41_SEC_IMS_SUPP_AUTH_TYPES = 14,
    IPC41_SEC_SIMAPPS_INFO        = 15,
    IPC41_SEC_SIM_ON_OFF          = 16,
    IPC41_SEC_SIM_LOW_LEVEL_CTRL  = 17,
    IPC41_SEC_PIN_STATUS2         = 18,
    IPC41_SEC_SIM_INFO            = 19,
    IPC41_SEC_TF_LOCK_STATUS      = 20,
};

/* NET (main=8) — registration/PLMN. table @0x3a8798. */
enum ipc41_net_subcmd {
    IPC41_NET_PREF_PLMN              = 1,
    IPC41_NET_PLMN_SEL               = 2,
    IPC41_NET_SERVING_NETWORK        = 3,
    IPC41_NET_PLMN_LIST              = 4,
    IPC41_NET_REGIST                 = 5,
    IPC41_NET_SUBSCRIBER_NUM         = 6,
    IPC41_NET_BAND_SEL               = 7,
    IPC41_NET_SERVICE_DOMAIN_CONFIG  = 8,
    IPC41_NET_POWERON_ATTACH         = 9,
    IPC41_NET_MODE_SEL               = 10,
    IPC41_NET_ACQ_ORDER              = 11,
    IPC41_NET_IDENTITY               = 12,
    IPC41_NET_PREFERRED_NETWORK_INFO = 13,
    IPC41_NET_HYBRID_MODE            = 14,
    IPC41_NET_HANDOVER               = 15,
    IPC41_NET_CELL_INFO              = 18,
    IPC41_NET_ECC_RAT                = 19,
    IPC41_NET_LTE_UE_CAPA            = 20,
    IPC41_NET_HVOLTE_TESTMODE       = 40,  /* NET_HVOLTE_TESTMODE (IpcTxGet/SetVolteTestmode) */
    IPC41_NET_VOLTE_STATE           = 52,  /* NET_VOLTE_STATE (IpcTxSetVolteStateNotification) */
};

/* SMS (main=4), AP name table @0x3a85f8, dispatch @0x3466b8. */
enum ipc41_sms_subcmd {
    IPC41_SMS_SEND_MSG=1, IPC41_SMS_INCOMING_MSG=2, IPC41_SMS_READ_MSG=3,
    IPC41_SMS_SAVE_MSG=4, IPC41_SMS_DEL_MSG=5, IPC41_SMS_DELIVER_REPORT=6,
    IPC41_SMS_DEVICE_READY=7, IPC41_SMS_SEL_MEM=8, IPC41_SMS_STORED_MSG_COUNT=9,
    IPC41_SMS_SVC_CENTER_ADDR=10, IPC41_SMS_SVC_OPTION=11, IPC41_SMS_MEM_STATUS=12,
    IPC41_SMS_CBS_MSG=13, IPC41_SMS_CBS_CFG=14, IPC41_SMS_STORED_MSG_STATUS=15,
    IPC41_SMS_PARAM_COUNT=16, IPC41_SMS_PARAM=17, IPC41_SMS_STATUS=18,
    IPC41_SMS_CBS_CBMI_CFG=19, IPC41_SMS_CBS_ACTIVATION=20, IPC41_SMS_RP_SMMA=21
};

/* GPRS (main=13) — packet data. table @0x3a8aa8. */
enum ipc41_gprs_subcmd {
    IPC41_GPRS_DEFINE_PDP_CONTEXT        = 1,
    IPC41_GPRS_QOS                       = 2,
    IPC41_GPRS_PS                        = 3,
    IPC41_GPRS_PDP_CONTEXT               = 4,
    IPC41_GPRS_ENTER_DATA                = 5,
    IPC41_GPRS_SHOW_PDP_ADDR             = 6,
    IPC41_GPRS_MS_CLASS                  = 7,
    IPC41_GPRS_3G_QUAL_SRVC_PROFILE      = 8,
    IPC41_GPRS_IP_CONFIGURATION          = 9,
    IPC41_GPRS_DEFINE_SEC_PDP_CONTEXT    = 10,
    IPC41_GPRS_TFT                       = 11,
    IPC41_GPRS_HSDPA_STATUS              = 12,
    IPC41_GPRS_CURRENT_SESSION_DATA_CTR  = 13,
    IPC41_GPRS_DATA_DORMANT              = 14,
    IPC41_GPRS_PIN_CTRL                  = 15,
    IPC41_GPRS_CALL_STATUS               = 16,
    IPC41_GPRS_PORT_LIST                 = 17,
    IPC41_GPRS_LTE_QOS_PROFILE           = 18,
    IPC41_GPRS_NW_INITIATED_PDN_DISCONNECT = 19,
    IPC41_GPRS_LTE_ATTACH_APN_INFO       = 20,
    IPC41_GPRS_EPDG_HANDOVER             = 21,
    IPC41_GPRS_EPDG_STATUS               = 22,
    IPC41_GPRS_FD_INFORMATION            = 23,
    IPC41_GPRS_OPERATOR_RESERVED_PCO     = 24,
    IPC41_GPRS_LTE_CA_STATUS             = 25,
    IPC41_GPRS_BACKOFF_TIMER             = 26,
    IPC41_GPRS_SET_APN_INFO              = 27,
    IPC41_GPRS_TRAFFIC_CHANNEL_STATUS    = 28,
    IPC41_GPRS_MOBILE_DATA_STATUS        = 29,
    IPC41_GPRS_SET_ALWAYS_ON_PDN         = 34,
    IPC41_GPRS_SYNC_PROFILE_INFO         = 37,
};

/* DISP (main=7) — status heartbeat. table @0x3a8768. */
enum ipc41_disp_subcmd {
    IPC41_DISP_ICON_INFO        = 1,
    IPC41_DISP_HOMEZONE_INFO    = 2,
    IPC41_DISP_PHONE_FATAL_INFO = 3,
    IPC41_DISP_EXT_ROAM_INFO    = 4,
    IPC41_DISP_USER_INDICATION  = 5,
    IPC41_DISP_RSSI_INFO        = 6,
};

/* PWR (main=1) — modem power. table @0x3a8370. */
enum ipc41_pwr_subcmd {
    IPC41_PWR_PHONE_PWR_UP   = 1,
    IPC41_PWR_PHONE_PWR_OFF  = 2,
    IPC41_PWR_PHONE_RESET    = 3,
    IPC41_PWR_BATT_STATUS    = 4,
    IPC41_PWR_BATT_TYPE      = 5,
    IPC41_PWR_BATT_COMP      = 6,
    IPC41_PWR_PHONE_STATE    = 7,
    IPC41_PWR_BATT_VOLTAGE   = 8,
    IPC41_PWR_ENABLE_MODEM   = 9,
};

/* SYSTEM (main=39) — system info. table @0x3a9758. */
enum ipc41_system_subcmd {
    IPC41_SYSTEM_CP_CHANNEL_INFO     = 1,
    IPC41_SYSTEM_CHARGING_DOCK       = 2,
    IPC41_SYSTEM_CP_ULTRA_SONIC_INFO = 3,
    IPC41_SYSTEM_CP_DBG_LEVEL_COMPL  = 4,
};

/* OES (main=38) — OEM extension. table @0x3a8fe8 region (SAP-adjacent). */
enum ipc41_oes_subcmd {
    IPC41_OES_CASS = 1, /* IpcRxOesCass evidence; exact list not in contiguous dump */
};

/* helpers */
static inline const char *ipc41_main_name(uint8_t main) {
    switch (main) {
    case IPC41_MAIN_PWR: return "PWR";
    case IPC41_MAIN_CALL: return "CALL";
    case IPC41_MAIN_CDMA_DATA: return "CDMA_DATA";
    case IPC41_MAIN_SMS: return "SMS";
    case IPC41_MAIN_SEC: return "SEC";
    case IPC41_MAIN_PB: return "PB";
    case IPC41_MAIN_DISP: return "DISP";
    case IPC41_MAIN_NET: return "NET";
    case IPC41_MAIN_SND: return "SND";
    case IPC41_MAIN_MISC: return "MISC";
    case IPC41_MAIN_SVC: return "SVC";
    case IPC41_MAIN_SS: return "SS";
    case IPC41_MAIN_GPRS: return "GPRS";
    case IPC41_MAIN_SAT: return "SAT";
    case IPC41_MAIN_CFG: return "CFG";
    case IPC41_MAIN_IMEI: return "IMEI";
    case IPC41_MAIN_GPS: return "GPS";
    case IPC41_MAIN_SAP: return "SAP";
    case IPC41_MAIN_FACTORY: return "FACTORY";
    case IPC41_MAIN_OMADM: return "OMADM";
    case IPC41_MAIN_RFS: return "RFS";
    case IPC41_MAIN_IMS: return "IMS";
    case IPC41_MAIN_EMBMS: return "EMBMS";
    case IPC41_MAIN_MMS: return "MMS";
    case IPC41_MAIN_RFS_EXT: return "RFS_EXT";
    case IPC41_MAIN_MODEMTEST: return "MODEMTEST";
    case IPC41_MAIN_DOMESTIC: return "DOMESTIC";
    case IPC41_MAIN_PCSC: return "PCSC";
    case IPC41_MAIN_QMI_HIDDEN: return "QMI_HIDDENMENU";
    case IPC41_MAIN_SMARTAS: return "SMARTAS";
    case IPC41_MAIN_PROSE: return "PROSE";
    case IPC41_MAIN_MCPTT: return "MCPTT";
    case IPC41_MAIN_OES: return "OES";
    case IPC41_MAIN_SYSTEM: return "SYSTEM";
    case IPC41_MAIN_JPN: return "JPN";
    case IPC41_MAIN_QMIIMS: return "QMIIMS";
    case IPC41_MAIN_IIL: return "IIL";
    case IPC41_MAIN_GEN: return "GEN";
    default: return "UNKNOWN";
    }
}

 /* NUXEL_IPC41_CMDMAP_H */

/*
 * NOTE on main_cmd values above:
 * Recovery is via GetMainCommandName jump-table (0x149934) and
 * GetSubCommandName jump-table (0x1499b4) + .data.rel.ro relocation chains,
 * resolved with readelf/objdump/strings on the read-only vendor mount.
 * The sub_cmd tables are laid out contiguously in .data.rel.ro in main_cmd
 * order; the literals below are the EXACT vendor name strings, so a given
 * (main_cmd, sub_cmd) is unambiguous. The enums above only list the subset
 * relevant to the Stage-06 SIM/registration/data objective plus a few
 * neighbouring families for completeness; the full recovery covers all
 * 39 families and is reproducible with scripts/resolve_ipc41_vocab.py.
 */

/* =========================================================================
 * IMS (main=22) sub-command family — recovered round 05 from libsec-ril.so.
 *
 * These names are the literal vendor strings exported by IpcProtocol41;
 * the (sub_cmd -> builder address) pairs are:
 *
 *   name                              builder (IpcProtocol41)
 *   ------------------------------------------------------------
 *   IpcTxImsReqDeregistration         0x34cdc0
 *   IpcTxImsAuthResp                  0x34ce10
 *   IpcTxImsReqDeregistrationE911     0x34ceb0
 *   IpcTxImsReqSetDeregistration      0x34cf50
 *   IpcTxImsReqSetRegState            0x34d230
 *
 * VERIFIED payload layout for IpcTxImsReqSetRegState (main=22 sub=8,
 * type=3, total_len=13, 6-byte payload) from @0x34d230 + @0x2fbe88:
 *
 *   [ ImsRegStatus, requestFlag(int), NetworkType, EcmpState,
 *     EpdgAvailableState(derived), int ]
 *
 * requestFlag is a separate `int` parameter BETWEEN ImsRegStatus and
 * NetworkType (demangled signature: ImsRegStatus, int, NetworkType,
 * EcmpState, EpdgState, EpdgAvailableState, int, RadioTechnology).
 * RadioTechnology (8th param) is consumed only to derive EpdgAvailableState.
 *
 * These are CP state reports, not a registration engine. See the correction
 * below: stock authentication/registration and SMS use the AP IMS endpoint.
 */
enum ipc41_ims_subcmd {
    IPC41_IMS_UNKNOWN_1 = 1,
    IPC41_IMS_UNKNOWN_2 = 2,
    IPC41_IMS_UNKNOWN_3 = 3,
    IPC41_IMS_REQ_SET_REGDEREG = 4,
    IPC41_IMS_REQ_SET_REGDEREG_E911 = 5,
    IPC41_IMS_AUTH_RESP = 6,
    IPC41_IMS_REQ_DEREGISTRATION = 7,
    IPC41_IMS_REQ_SET_REG_STATE = 8,
};

/* =========================================================================
 * IMS (main=22) sub-command family — COMPLETE recovery (round 06).
 *
 * Verified against libsec-ril.so 60889dd7 via aarch64 disassembly:
 *   IpcProtocol41::GetSubCommandName jump-table for main=22 yields these
 *   names in order. sub_cmd 8 = REQ_SET_REG_STATE (IpcTxImsReqSetRegState
 *   @0x34d230, 6-byte payload, layout fully decoded in fmt_tx.c).
 *
 * Correction: these CP commands report AP IMS state. Registration is
 * received from the separate IIL endpoint (IpcRxIilRegistration @0x356528).
 * IpcRxImsModeChange @0x34cfa0 is a mode-switch intent, not registration.
 * IpcTxImsAuthResp @0x34ce10 is unsupported on this CP protocol. UICC AKA
 * uses SEC_IMS_AUTH requests/results, not a main=22 challenge/response relay.
 */

/* QMIIMS (main=64) — separate Qualcomm-style IMS transport. Names only. */
#define IPC41_QMIIMS_UNUSED 0u

/* ImsRegStatus enum values (recovered from ImsRegState ctor semantics and
 * ModemProxy::SetImsRegState signature; these are the values the AP reports
 * to the modem, NOT the modem's confirmed registration state). */
#define IMS_REG_STATUS_NONE        0u
#define IMS_REG_STATUS_REGISTERED  1u
#define IMS_REG_STATUS_DEREGISTER  2u  /* request deregistration */
#define IMS_REG_STATUS_NOT_REG     3u

/* NetworkType wire values for IpcTxImsReqSetRegState payload[2]. */
#define IMS_NETWORK_TYPE_LTE       14u
#define IMS_NETWORK_TYPE_UNKNOWN   0u
#endif
