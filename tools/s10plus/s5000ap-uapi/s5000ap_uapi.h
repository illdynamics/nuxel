/*
 * s5000ap_uapi.h — VERIFIED USERSPACE ABI for Samsung Shannon S5000AP
 * (Exynos9820 downstream kernel, modem_v1 / modem_ctrl_s5000ap.c).
 *
 * This header is a faithful transcription of the UAPI-relevant definitions
 * extracted from the pinned kernel source commit
 *   f7194c1d15eded1c2a1a4dc63825b26103435cc0  (2021-11-13, linux 4.14.253)
 * paths:
 *   drivers/misc/modem_v1/modem_prj.h      (ioctl commands, modem_state,
 *                                           struct modem_firmware,
 *                                           struct modem_sec_req,
 *                                           enum cp_boot_mode)
 *   drivers/misc/modem_v1/include/sipc5.h  (SIPC5 framing)
 *   drivers/misc/modem_v1/modem_v1.h       (SIPC channel IDs)
 *   drivers/misc/modem_v1/modem_io_device.c (ioctl dispatch semantics)
 *   drivers/misc/modem_v1/modem_ctrl_s5000ap.c (boot state machine)
 *   drivers/misc/modem_v1/link_device_shmem.c (xmit_boot / security_req)
 *
 * It is intentionally FREE OF kernel-only types: no <linux/...> headers, no
 * sk_buff, no __iomem. It compiles in both freestanding userspace C and
 * (with __KERNEL__ guards removed) matches the kernel layout byte-for-byte.
 *
 * NOTE ON IOCTL ENCODING: every command below is declared with _IO (which is
 * _IOC(_IOC_NONE,...)); this kernel header declares them as _IO('o',N).
 * The Samsung cbd (cpboot_v3) matches this ONLY when built with
 * -DLEGACY_SIPC_IOCTL (use_legacy_sipc_ioctl=true in the Lineage device tree),
 * which reverts BOOT_ON(0x22)/RESET(0x21)/LOAD_CP_IMAGE(0x40)/REQ_SECURITY(0x53)
 * to the bare _IO form. The non-legacy cbd uses _IOW/_IOR encodings whose
 * numeric value differs (size/direction in bits 29..14). See the BUILD-RECEIPT
 * and BOOT-CONTRACT reports for the numeric derivation.
 */
#ifndef NUXEL_S5000AP_UAPI_H
#define NUXEL_S5000AP_UAPI_H

#include <stdint.h>
#include <stddef.h>
#include <sys/ioctl.h>

#ifdef __cplusplus
extern "C" {
#endif

/* ---- type aliases mirroring kernel u8/u16/u32 ------------------------- */
typedef uint8_t  u8;
typedef uint16_t u16;
typedef uint32_t u32;
typedef uint64_t u64;

/* ---- ioctl command encodings -------------------------------------------------
 * These are the LINUX asm-generic (AArch64) numeric values of _IO('o',N),
 * i.e. 0x6F00 | N. We pin the numeric literals directly so the header is
 * independent of the host libc's ioctl encoding (macOS/BSD uses 0x20000000
 * direction bits and _IO('o',0x27)==0x20006F27, which is NOT the Linux ABI).
 * On a Linux target the companion check asserts _IO('o',N)==these constants.
 */
#define IOCTL_MAGIC 0x6F00

#define IOCTL_MODEM_ON                (IOCTL_MAGIC | 0x19)   /* 0x6F19 */
#define IOCTL_MODEM_OFF               (IOCTL_MAGIC | 0x20)   /* 0x6F20 */
#define IOCTL_MODEM_RESET             (IOCTL_MAGIC | 0x21)   /* 0x6F21 */
#define IOCTL_MODEM_BOOT_ON           (IOCTL_MAGIC | 0x22)   /* 0x6F22 */
#define IOCTL_MODEM_BOOT_OFF          (IOCTL_MAGIC | 0x23)   /* 0x6F23 */
#define IOCTL_MODEM_BOOT_DONE         (IOCTL_MAGIC | 0x24)   /* 0x6F24 */
#define IOCTL_MODEM_PROTOCOL_SUSPEND  (IOCTL_MAGIC | 0x25)   /* 0x6F25 */
#define IOCTL_MODEM_PROTOCOL_RESUME   (IOCTL_MAGIC | 0x26)   /* 0x6F26 */
#define IOCTL_MODEM_STATUS            (IOCTL_MAGIC | 0x27)   /* 0x6F27 */
#define IOCTL_MODEM_DL_START          (IOCTL_MAGIC | 0x28)   /* 0x6F28 */
#define IOCTL_MODEM_FW_UPDATE         (IOCTL_MAGIC | 0x29)   /* 0x6F29 */
#define IOCTL_MODEM_NET_SUSPEND       (IOCTL_MAGIC | 0x30)   /* 0x6F30 */
#define IOCTL_MODEM_NET_RESUME        (IOCTL_MAGIC | 0x31)   /* 0x6F31 */
#define IOCTL_MODEM_DUMP_START        (IOCTL_MAGIC | 0x32)   /* 0x6F32 */
#define IOCTL_MODEM_DUMP_UPDATE       (IOCTL_MAGIC | 0x33)   /* 0x6F33 */
#define IOCTL_MODEM_FORCE_CRASH_EXIT  (IOCTL_MAGIC | 0x34)   /* 0x6F34 */
#define IOCTL_MODEM_CP_UPLOAD         (IOCTL_MAGIC | 0x35)   /* 0x6F35 */
#define IOCTL_LINK_CONNECTED          (IOCTL_MAGIC | 0x33)   /* 0x6F33 (alias) */
#define IOCTL_MODEM_SET_TX_LINK       (IOCTL_MAGIC | 0x37)   /* 0x6F37 */
#define IOCTL_MODEM_XMIT_BOOT         (IOCTL_MAGIC | 0x40)   /* 0x6F40 */
#define IOCTL_MODEM_GET_SHMEM_INFO    (IOCTL_MAGIC | 0x41)   /* 0x6F41 */
#define IOCTL_DPRAM_INIT_STATUS       (IOCTL_MAGIC | 0x43)   /* 0x6F43 */
#define IOCTL_LINK_DEVICE_RESET       (IOCTL_MAGIC | 0x44)   /* 0x6F44 */
#define IOCTL_MODEM_GET_SHMEM_SRINFO  (IOCTL_MAGIC | 0x45)   /* 0x6F45 */
#define IOCTL_MODEM_SET_SHMEM_SRINFO  (IOCTL_MAGIC | 0x46)   /* 0x6F46 */
#define IOCTL_MODEM_GET_CP_BOOTLOG    (IOCTL_MAGIC | 0x47)   /* 0x6F47 */
#define IOCTL_MODEM_CLR_CP_BOOTLOG    (IOCTL_MAGIC | 0x48)   /* 0x6F48 */
#define IOCTL_MIF_LOG_DUMP            (IOCTL_MAGIC | 0x51)   /* 0x6F51 */
#define IOCTL_MIF_DPRAM_DUMP          (IOCTL_MAGIC | 0x52)   /* 0x6F52 */
#define IOCTL_SECURITY_REQ            (IOCTL_MAGIC | 0x53)   /* 0x6F53 */
#define IOCTL_SHMEM_FULL_DUMP         (IOCTL_MAGIC | 0x54)   /* 0x6F54 */
#define IOCTL_MODEM_CRASH_REASON      (IOCTL_MAGIC | 0x55)   /* 0x6F55 */
#define IOCTL_MODEM_AIRPLANE_MODE     (IOCTL_MAGIC | 0x56)   /* 0x6F56 */
#define IOCTL_VSS_FULL_DUMP           (IOCTL_MAGIC | 0x57)   /* 0x6F57 */
#define IOCTL_ACPM_FULL_DUMP          (IOCTL_MAGIC | 0x58)   /* 0x6F58 */
#define IOCTL_CPLOG_FULL_DUMP         (IOCTL_MAGIC | 0x59)   /* 0x6F59 */
#define IOCTL_DATABUF_FULL_DUMP       (IOCTL_MAGIC | 0x5A)   /* 0x6F5A */
#define IOCTL_MODEM_RAMDUMP_START     (IOCTL_MAGIC | 0xCE)   /* 0x6FCE */
#define IOCTL_MODEM_RAMDUMP_STOP      (IOCTL_MAGIC | 0xCF)   /* 0x6FCF */

/* ---- modem_state enum (kernel modem_prj.h order) ---------------------- */
enum modem_state {
    STATE_OFFLINE = 0,
    STATE_CRASH_RESET = 1,      /* silent reset */
    STATE_CRASH_EXIT = 2,       /* cp ramdump */
    STATE_BOOTING = 3,
    STATE_ONLINE = 4,
    STATE_NV_REBUILDING = 5,    /* rebuilding start */
    STATE_LOADER_DONE = 6,
    STATE_SIM_ATTACH = 7,
    STATE_SIM_DETACH = 8,
    STATE_CRASH_WATCHDOG = 9,   /* cp watchdog crash */
};

/* ---- cp_boot_mode (kernel modem_prj.h) ------------------------------- */
enum cp_boot_mode {
    CP_BOOT_MODE_NORMAL = 0,
    CP_BOOT_MODE_DUMP = 1,
    CP_BOOT_RE_INIT = 2,
    CP_BOOT_REQ_CP_RAM_LOGGING = 5,
    CP_BOOT_MODE_MANUAL = 7,
    MAX_CP_BOOT_MODE,
};

/* ---- struct modem_firmware (kernel modem_prj.h, __packed) -------------
 * Layout (verified by _Static_assert in nuxel-s5000ap-uapi-check):
 *   u64 binary;  // user VA of CP image buffer (8 bytes)
 *   u32 size;    // full image size in target window
 *   u32 m_offset;// memory offset into CP window
 *   u32 b_offset;// byte offset into usermem buffer
 *   u32 mode;    // 0=BOOT_MODE, nonzero=DUMP_MODE
 *   u32 len;     // bytes to copy this call
 * Total: 28 bytes on AArch64/ILP32 because __packed removes ALL tail padding:
 *   binary@0 (8), size@8, m_offset@12, b_offset@16, mode@20, len@24 => 28.
 * The binary pointer field is 8 bytes (LP64) / 8 bytes (ILP32 has 8-byte
 * long long too), so this struct is layout-identical on 32/64-bit. See check.
 */
struct modem_firmware {
    unsigned long long binary;
    u32 size;
    u32 m_offset;
    u32 b_offset;
    u32 mode;
    u32 len;
} __attribute__((__packed__));

/* ---- struct modem_sec_req (kernel modem_prj.h, __packed) ------------- */
struct modem_sec_req {
    u32 mode;
    u32 param2;
    u32 param3;
    u32 param4;
} __attribute__((__packed__));

/* ---- struct sec_info (kernel modem_prj.h) ---------------------------- */
struct sec_info {
    enum cp_boot_mode mode;
    u32 size;
};

/* ---- core SIPC5 link-layer header (include/sipc5.h) ------------------ */
#define SIPC5_START_MASK        (0b11111000u)  /* 0xF8 */
#define SIPC5_CONFIG_MASK       (0b00000111u)  /* 0x07 */
#define SIPC5_EXT_FIELD_MASK    (0b00000011u)  /* 0x03 */
#define SIPC5_PADDING_EXIST     (0b00000100u)  /* 0x04 */
#define SIPC5_EXT_FIELD_EXIST   (0b00000010u)  /* 0x02 */
#define SIPC5_CTL_FIELD_EXIST   (0b00000001u)  /* 0x01 */
#define SIPC5_MULTI_FRAME_CFG   (0b00000011u)
#define SIPC5_EXT_LENGTH_CFG    (0b00000010u)

#define SIPC5_MIN_HEADER_SIZE            4
#define SIPC5_HEADER_SIZE_WITH_CTL_FLD   5
#define SIPC5_HEADER_SIZE_WITH_EXT_LEN   6
#define SIPC5_MAX_HEADER_SIZE            SIPC5_HEADER_SIZE_WITH_EXT_LEN

struct multi_frame_control {
    u8 id : 7,   /* frame id (SIPC multi-frame id) */
        more : 1; /* more-frames indicator */
} __attribute__((__packed__));   /* 1 byte, packed bitfields */

struct sipc5_link_header {
    u8  cfg;      /* START_MASK(0xF8 bits) | config/ctrl/ext bits */
    u8  ch;       /* SIPC5 channel id */
    u16 len;      /* little-endian frame length */
    union {
        struct multi_frame_control ctrl;  /* 1 byte (packed) */
        u16 ext_len;                       /* 2 bytes (ext-length path) */
    };
} __attribute__((__packed__));   /* 6 bytes total: 1+1+2+2 */
_Static_assert(sizeof(struct multi_frame_control) == 1, "mfctrl 1 byte");
_Static_assert(sizeof(struct sipc5_link_header) == 6, "sipc5 hdr 6 bytes");

/* ---- SIPC5 channel IDs (modem_v1.h) ---------------------------------- */
enum sipc5_channel_id {
    SIPC_CH_ID_PDP_0 = 10,
    SIPC_CH_ID_PDP_1,
    SIPC_CH_ID_PDP_2,
    SIPC_CH_ID_PDP_3,
    SIPC_CH_ID_PDP_4,
    SIPC_CH_ID_PDP_5,
    SIPC_CH_ID_PDP_6,
    SIPC_CH_ID_PDP_7,
    SIPC_CH_ID_PDP_8,
    SIPC_CH_ID_PDP_9,
    SIPC_CH_ID_PDP_10,
    SIPC_CH_ID_PDP_11,
    SIPC_CH_ID_PDP_12,
    SIPC_CH_ID_PDP_13,
    SIPC_CH_ID_PDP_14,
    SIPC_CH_ID_BT_DUN = 25,
    SIPC_CH_ID_CIQ_DATA,
    SIPC_CH_ID_PDP_17,          /* reserved */
    SIPC_CH_ID_CPLOG1 = 28,
    SIPC_CH_ID_CPLOG2,
    SIPC_CH_ID_LOOPBACK1 = 30,
    SIPC_CH_ID_LOOPBACK2,
    SIPC_CH_ID_CASS = 35,
    SIPC5_CH_ID_BOOT_0 = 215,
    SIPC5_CH_ID_BOOT_1,
    SIPC5_CH_ID_BOOT_2,
    SIPC5_CH_ID_BOOT_3,
    SIPC5_CH_ID_BOOT_4,
    SIPC5_CH_ID_BOOT_5,
    SIPC5_CH_ID_BOOT_6,
    SIPC5_CH_ID_BOOT_7,
    SIPC5_CH_ID_BOOT_8,
    SIPC5_CH_ID_BOOT_9,
    SIPC5_CH_ID_DUMP_0 = 225,
    SIPC5_CH_ID_DUMP_1,
    SIPC5_CH_ID_DUMP_2,
    SIPC5_CH_ID_DUMP_3,
    SIPC5_CH_ID_DUMP_4,
    SIPC5_CH_ID_DUMP_5,
    SIPC5_CH_ID_DUMP_6,
    SIPC5_CH_ID_DUMP_7,
    SIPC5_CH_ID_DUMP_8,
    SIPC5_CH_ID_DUMP_9,
    SIPC5_CH_ID_FMT_0 = 235,
    SIPC5_CH_ID_FMT_1,
    SIPC5_CH_ID_FMT_2,
    SIPC5_CH_ID_FMT_3,
    SIPC5_CH_ID_FMT_4,
    SIPC5_CH_ID_FMT_5,
    SIPC5_CH_ID_FMT_6,
    SIPC5_CH_ID_FMT_7,
    SIPC5_CH_ID_FMT_8,
    SIPC5_CH_ID_FMT_9,
    SIPC5_CH_ID_RFS_0 = 245,
    SIPC5_CH_ID_RFS_1,
    SIPC5_CH_ID_RFS_2,
    SIPC5_CH_ID_RFS_3,
    SIPC5_CH_ID_RFS_4,
    SIPC5_CH_ID_RFS_5,
    SIPC5_CH_ID_RFS_6,
    SIPC5_CH_ID_RFS_7,
    SIPC5_CH_ID_RFS_8,
    SIPC5_CH_ID_RFS_9,
    SIPC5_CH_ID_MAX = 255
};

/* Standard UDL (boot loader download) command constants (sipc5.h) ------ */
#define STD_UDL_STEP_MASK  0x0000000Fu
#define STD_UDL_SEND       0x1
#define STD_UDL_CRC        0xC

struct std_dload_info {
    u32 size;
    u32 mtu;
    u32 num_frames;
} __attribute__((__packed__));

#ifdef __cplusplus
}
#endif

#endif /* NUXEL_S5000AP_UAPI_H */
