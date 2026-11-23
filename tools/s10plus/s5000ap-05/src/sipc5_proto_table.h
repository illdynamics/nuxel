/*
 * sipc5_proto_table.h — S5000AP SIPC5/SBD channel + message knowledge table.
 *
 * SPDX-License-Identifier: GPL-2.0-only
 *
 * This table records EVERY protocol fact the Nuxel radiod relies on, together
 * with its EVIDENCE SOURCE, CONFIDENCE and LIVE-VALIDATION STATUS. It exists so
 * that the daemon never silently "knows" something it cannot justify.
 *
 * Provenance (all lawfully accessible, pinned):
 *   KDT  = device-tree  arch/arm64/boot/dts/samsung/exynos9820-d2x_eur_open_16.dts
 *          (mif iodevs block) — the AUTHORITATIVE channel id/format/app map for
 *          the installed kernel. These are hard numbers, not guesses.
 *   KSH  = drivers/misc/modem_v1/include/sipc5.h           (link framing)
 *   KPRJ = drivers/misc/modem_v1/modem_prj.h               (sipc_fmt_hdr, enums)
 *   KMV1 = drivers/misc/modem_v1/modem_v1.h                (sipc_ch_id, attrs)
 *   KIO  = drivers/misc/modem_v1/modem_io_device.c         (read/write model)
 *   KSHM = drivers/misc/modem_v1/link_device_shmem.c       (rild_ready/INIT_END)
 *   KTIO = drivers/misc/modem_v1/link_device_memory.h      (SBD CMD_* commands)
 *   LIVE = observed on this handset (redacted) this stage
 *
 * CLASSES:
 *   KNOWN_LIVE          proven by live device evidence (exact, corroborated)
 *   KNOWN_SOURCE        proven from pinned open source (ABI-certain)
 *   DOCUMENTED_ONLY     documented but not exercised on this hardware
 *   UNKNOWN             semantics not lawfully reconstructable yet
 *
 * The FMT *telephony message vocabulary* (meaning of main_cmd/sub_cmd/cmd_type
 * as SIM/registration/bearer requests) is defined ONLY in the closed Samsung
 * libsec-ril.so and is therefore UNKNOWN here. We do NOT fabricate it and we do
 * NOT transmit speculative commands.
 */
#ifndef NUXEL_SIPC5_PROTO_TABLE_H
#define NUXEL_SIPC5_PROTO_TABLE_H

#include <stdint.h>

enum nuxel_proto_class {
    NUXEL_CLASS_UNKNOWN = 0,
    NUXEL_CLASS_DOCUMENTED_ONLY,
    NUXEL_CLASS_KNOWN_SOURCE,
    NUXEL_CLASS_KNOWN_LIVE,
};

/* ---- channel (io_device) table — source = KDT -------------------------- */
struct nuxel_channel_desc {
    const char *node;     /* /dev/... */
    uint8_t     ch_id;    /* SIPC5 channel id (8-bit) */
    uint8_t     format;   /* 0=FMT 1=RAW 2=RFS (KMV1 enum legacy_ipc_map) */
    uint32_t    attrs;    /* iod,attrs from DT (bitmask of iodev_attr_bit) */
    const char *app;      /* iod,app label from DT (informational only) */
    enum nuxel_proto_class cls;
    const char *evidence;
};

static const struct nuxel_channel_desc nuxel_channels[] = {
    { "/dev/umts_ipc0",   0xEB, 0, 0x2082, "RIL",          NUXEL_CLASS_KNOWN_SOURCE, "KDT io_device_1" },
    { "/dev/umts_ipc1",   0xEC, 0, 0x0082, "RIL",          NUXEL_CLASS_KNOWN_SOURCE, "KDT io_device_2" },
    { "/dev/umts_rfs0",   0xF5, 2, 0x2082, "RFS",          NUXEL_CLASS_KNOWN_SOURCE, "KDT io_device_3" },
    { "/dev/umts_csd",    0x01, 1, 0x0082, "CSVT",         NUXEL_CLASS_KNOWN_SOURCE, "KDT io_device_4" },
    { "/dev/umts_router", 0x19, 1, 0x0082, "Data Router",  NUXEL_CLASS_KNOWN_SOURCE, "KDT io_device_5" },
    { "/dev/umts_dm0",    0x1C, 1, 0x0082, "DIAG",         NUXEL_CLASS_KNOWN_SOURCE, "KDT io_device_6" },
    { "/dev/umts_cass",   0x23, 1, 0x2082, "CASS",         NUXEL_CLASS_KNOWN_SOURCE, "KDT io_device_0" },
};
#define NUXEL_NUM_CHANNELS (sizeof(nuxel_channels)/sizeof(nuxel_channels[0]))

/* iodev_attr_bit names used in attrs (KMV1) */
#define NUXEL_ATTR_SIPC5        (1u << 1)
#define NUXEL_ATTR_LEGACY_RFS   (1u << 5)
#define NUXEL_ATTR_SBD_IPC      (1u << 7)
#define NUXEL_ATTR_NO_LINK_HDR  (1u << 8)
#define NUXEL_ATTR_DIT          (1u << 13)

/* ---- SIPC5 link control SBD commands (source = KTIO) ------------------ */
struct nuxel_sbd_cmd_desc {
    const char *name;
    uint16_t    value;
    enum nuxel_proto_class cls;
};
static const struct nuxel_sbd_cmd_desc nuxel_sbd_cmds[] = {
    { "CMD_INIT_START",       0x0001, NUXEL_CLASS_KNOWN_SOURCE },
    { "CMD_INIT_END",         0x0002, NUXEL_CLASS_KNOWN_SOURCE },
    { "CMD_REQ_ACTIVE",       0x0003, NUXEL_CLASS_KNOWN_SOURCE },
    { "CMD_RES_ACTIVE",       0x0004, NUXEL_CLASS_KNOWN_SOURCE },
    { "CMD_REQ_TIME_SYNC",    0x0005, NUXEL_CLASS_KNOWN_SOURCE },
    { "CMD_KERNEL_PANIC",     0x0006, NUXEL_CLASS_KNOWN_SOURCE },
    { "CMD_CRASH_RESET",      0x0007, NUXEL_CLASS_KNOWN_SOURCE },
    { "CMD_PHONE_START",      0x0008, NUXEL_CLASS_KNOWN_LIVE },
    { "CMD_CRASH_EXIT",       0x0009, NUXEL_CLASS_KNOWN_SOURCE },
    { "CMD_CP_DEEP_SLEEP",    0x000A, NUXEL_CLASS_KNOWN_SOURCE },
    { "CMD_NV_REBUILDING",    0x000B, NUXEL_CLASS_KNOWN_SOURCE },
    { "CMD_EMER_DOWN",        0x000C, NUXEL_CLASS_KNOWN_SOURCE },
    { "CMD_PIF_INIT_DONE",    0x000D, NUXEL_CLASS_KNOWN_SOURCE },
    { "CMD_SILENT_NV_REBUILD",0x000E, NUXEL_CLASS_KNOWN_SOURCE },
    { "CMD_NORMAL_POWER_OFF", 0x000F, NUXEL_CLASS_KNOWN_SOURCE },
};
#define NUXEL_NUM_SBD_CMDS (sizeof(nuxel_sbd_cmds)/sizeof(nuxel_sbd_cmds[0]))

/* ---- FMT message vocabulary -------------------------------------------- */
/*
 * The ONLY FMT-class message we have observed live is a CP debug/log line:
 *   main_cmd=0x13 sub_cmd=0x05 cmd_type=0x03 payload started with 0f 00 0d 0a
 * ("\n" text). It is corroborated as a non-telephony log/notification by the
 * printable ASCII payload. We record it as OBSERVED but its *semantic family*
 * is UNKNOWN (we do not know if 0x13 is "log" universally).
 *
 * The telephony main_cmd/sub_cmd space (SIM, registration, bearer, call, SMS,
 * RFS opcodes) is closed-source and classed UNKNOWN. NO id below is invented.
 */
struct nuxel_fmt_observation {
    uint8_t main_cmd;
    uint8_t sub_cmd;
    uint8_t cmd_type;
    uint8_t ch_id;
    enum nuxel_proto_class cls;
    const char *evidence;
    const char *live_note;
};
static const struct nuxel_fmt_observation nuxel_fmt_observations[] = {
    /* LIVE (userspace read of /dev/umts_ipc0 during approved CP boot):
     * len=25 payload = "\x0f\x00\r\nAST_POWERON\r\n\x00" — a CP boot-stage
     * readiness TEXT notification. Family is a boot/status notify, NOT telephony.
     * We record the exact (main,sub,type) but do NOT assert universal meaning. */
    { 0x13, 0x05, 0x03, 0xEB, NUXEL_CLASS_UNKNOWN,
      "LIVE userspace read ch235 (redacted)",
      "payload '\r\nAST_POWERON\r\n'; CP boot-stage text notify; not telephony" },
};

/*
 * RFS (ch 245) — OBSERVED raw request format (NOT sipc_fmt_hdr):
 *   [u32 len LE][u8 op_class][u8 flags][u16 path_len][u16 reserved][path+\0]
 * Observed op_class=0x0b, path="DELETE_ALL_VIS" (DESTRUCTIVE NV/EFS delete-all).
 * The full op_class->operation map is CLOSED/UNKNOWN. Destructive operations
 * are FAIL-CLOSED by policy: radiod never executes them. No response fabricated.
 */
struct nuxel_rfs_observation {
    uint8_t op_class;
    const char *op_text;   /* exact ASCII path/opcode observed (not a secret) */
    enum nuxel_proto_class cls;
    const char *live_note;
};
static const struct nuxel_rfs_observation nuxel_rfs_observations[] = {
    { 0x0b, "DELETE_ALL_VIS", NUXEL_CLASS_UNKNOWN,
      "LIVE: destructive NV/EFS delete-all request; FAIL-CLOSED, never executed" },
};
#define NUXEL_NUM_RFS_OBS (sizeof(nuxel_rfs_observations)/sizeof(nuxel_rfs_observations[0]))

#define NUXEL_NUM_FMT_OBS (sizeof(nuxel_fmt_observations)/sizeof(nuxel_fmt_observations[0]))

/* Lookup helpers (return NULL when not present — callers must treat as UNKNOWN). */
static inline const struct nuxel_channel_desc *nuxel_channel_by_node(const char *node)
{
    unsigned i;
    if (!node) return 0;
    for (i = 0; i < NUXEL_NUM_CHANNELS; i++)
        if (nuxel_channels[i].node && !__builtin_strcmp(node, nuxel_channels[i].node))
            return &nuxel_channels[i];
    return 0;
}
static inline const char *nuxel_sbd_cmd_name(uint16_t v)
{
    unsigned i;
    for (i = 0; i < NUXEL_NUM_SBD_CMDS; i++)
        if (nuxel_sbd_cmds[i].value == v) return nuxel_sbd_cmds[i].name;
    return "UNKNOWN";
}
static inline const char *nuxel_class_name(enum nuxel_proto_class c)
{
    switch (c) {
    case NUXEL_CLASS_KNOWN_LIVE:     return "KNOWN_LIVE";
    case NUXEL_CLASS_KNOWN_SOURCE:   return "KNOWN_SOURCE";
    case NUXEL_CLASS_DOCUMENTED_ONLY:return "DOCUMENTED_ONLY";
    default:                         return "UNKNOWN";
    }
}

/*
 * ----------------------------------------------------------------------
 * STAGE-06 RECOVERY (source-backed, this round) - see test_ipc41_recovery.c
 * ----------------------------------------------------------------------
 * Recovered from vendor/lib64/libsec-ril.so (SM-G975F vendor, GNU Build ID
 * 60889dd714394ae0db7c2ecc2bf2740f) via on-device readelf/objdump/strings/nm
 * on the read-only sda26 mount. Provenance is EXACT (same binary the previous
 * rounds fingerprinted); these are O3_STATIC_CANDIDATE facts, NOT live-
 * corroborated (O4/O5) semantics. We record them to bound the closed
 * vocabulary and to validate the FMT transport framing; we do NOT use them
 * to transmit any speculative command.
 *
 *   DIALECT: the class "IpcProtocol41" is exported (IpcRx- / IpcTx- syms).
 *   FMT HDR: IpcTxExchange at 0x342a80 stores (main,sub,type,seq,ack)
 *            into consecutive bytes after a u16 len - matching the pinned
 *            struct sipc_fmt_hdr (u16 len,msg_seq,ack_seq,main_cmd,sub_cmd,
 *            cmd_type). Therefore the existing 7-byte parser is ABI-correct.
 *   cmd_type: enum carries IPC_CMD_NOTI; live AST_POWERON carries type=0x03
 *            (main=0x13 sub=0x05), i.e. 0x03 is a notification class.
 *   main_cmd FAMILIES: 35 distinct names recovered from
 *            "*_SUB_CMD_UNDEFINED" fmt strings; numeric ids stay UNKNOWN.
 */
#define NUXEL_IPC41_DIALECT   "IpcProtocol41"
/* Number of distinct main_cmd family NAMES recovered (strings). */
#define NUXEL_NUM_MAINCMD_FAMILY_NAMES 34

#endif /* NUXEL_SIPC5_PROTO_TABLE_H */
