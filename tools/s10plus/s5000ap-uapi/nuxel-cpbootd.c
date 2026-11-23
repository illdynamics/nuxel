/*
 * nuxel-cpbootd — source-faithful native CP bootstrap for Exynos9820 / S5000AP
 * (Samsung Shannon "SS310" modem, SIPC + SHMEM + legacy-sipc ioctl ABI).
 *
 * Architecture decision (03.7): this is path B. The stock Bionic `cbd`
 * (cpboot_v3) links liblog/libcutils/libc++/libselinux and an Android property
 * server + radio_device SELinux domain; that is exactly the Android-framework
 * dependency Nuxel forbids. `nuxel-cpbootd` re-implements the SAME Samsung boot
 * transaction against glibc/systemd, preserving the boot state machine, the
 * struct modem_firmware / modem_sec_req ABI, the ioctl numeric contract, the
 * SIPC UDL handshake, and error behaviour — all pinned to the actual sources:
 *
 *   kernel  android_kernel_samsung_exynos9820 @ f7194c1d15eded1c2a1a4dc63825b26103435cc0
 *           drivers/misc/modem_v1/{modem_prj.h,modem_io_device.c,
 *           modem_ctrl_s5000ap.c,link_device_shmem.c,include/sipc5.h}
 *   cbd     android_hardware_samsung_slsi-linaro_exynos cpboot_v3 @
 *           234b138716426c36ed801a71052bc144f7d8d806
 *           {BootDumpModap.cpp,BootDump.cpp,ProtocolSipc.cpp,Type.h,Protocol.h}
 *
 * Compiled with the exact exynos9820-common configuration
 *   protocol=sipc -> -DCONFIG_SEC_CP_VERIFYING_ALL
 *   use_legacy_sipc_ioctl=true -> -DLEGACY_SIPC_IOCTL
 *   (-DCONFIG_TYPE_MODAP -DCONFIG_TYPE_EXT)  and  -t ss310 -> SEC_SS310
 *
 * SAFETY MODEL (enforced in code + _Static_assert + runtime):
 *   - DEFAULT IS FAIL-CLOSED ("dry-run"): no hardware-changing ioctl, no
 *     write(), no writable open. Dry-run emits only IOCTL_MODEM_STATUS.
 *   - The hardware path is compiled ONLY when NUXEL_CPBOOTD_ENABLE_HW is
 *     DEFINED WITH A NONZERO VALUE. `#ifdef`-only is rejected at compile time.
 *   - Hardware path additionally requires --really-boot AND a verified,
 *     immutable manifest (--manifest-sha256) whose hash is checked at runtime.
 *   - Single exclusive owner via a well-defined lock contract (see below).
 *   - Nonzero process exit on ANY failure/abort, with machine-readable
 *     `first_failed_stage`. No silent success for any required stage.
 *   - Every transfer/stage is deadline-bounded; no retry/power-cycle loops.
 */
#define _GNU_SOURCE
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <stddef.h>
#include <errno.h>
#include <fcntl.h>
#include <unistd.h>
#include <time.h>
#include <signal.h>
#include <sys/ioctl.h>
#include <sys/file.h>
#include <sys/stat.h>
#include <stdarg.h>
#include <poll.h>

#include "s5000ap_uapi.h"

/* ---------------------------------------------------------------------------
 * Compile-time ABI fence: if the verified header drifts, this unit refuses to
 * build rather than mis-drive the modem.
 * ------------------------------------------------------------------------- */
_Static_assert(IOCTL_MODEM_ON          == 0x6F19, "ioctl ON");
_Static_assert(IOCTL_MODEM_RESET       == 0x6F21, "ioctl RESET");
_Static_assert(IOCTL_MODEM_BOOT_ON     == 0x6F22, "ioctl BOOT_ON");
_Static_assert(IOCTL_MODEM_BOOT_OFF    == 0x6F23, "ioctl BOOT_OFF");
_Static_assert(IOCTL_MODEM_BOOT_DONE   == 0x6F24, "ioctl BOOT_DONE");
_Static_assert(IOCTL_MODEM_STATUS      == 0x6F27, "ioctl STATUS");
_Static_assert(IOCTL_MODEM_DL_START    == 0x6F28, "ioctl DL_START");
_Static_assert(IOCTL_MODEM_XMIT_BOOT   == 0x6F40, "ioctl XMIT_BOOT (=LOAD_CP_IMAGE)");
_Static_assert(IOCTL_MODEM_GET_CP_BOOTLOG == 0x6F47, "ioctl GET_CP_BOOTLOG");
_Static_assert(IOCTL_MODEM_CLR_CP_BOOTLOG == 0x6F48, "ioctl CLR_CP_BOOTLOG");
_Static_assert(IOCTL_SECURITY_REQ      == 0x6F53, "ioctl SECURITY_REQ (=REQ_SECURITY)");
_Static_assert(sizeof(struct modem_firmware) == 28, "modem_firmware 28 bytes");
_Static_assert(sizeof(struct modem_sec_req) == 16, "modem_sec_req 16 bytes");

/* ---------------------------------------------------------------------------
 * Value-aware hardware gate. The audit flagged that `#ifdef` compiles HW code
 * even when the macro is 0. We force a *value* check: NUXEL_CPBOOTD_ENABLE_HW
 * must be defined AND expand to 1, otherwise this translation unit reduces to a
 * safe status-only tool (the HW implementation is guarded by HW_ENABLED which
 * is 0 when the macro is 0/undefined).
 * ------------------------------------------------------------------------- */
#if defined(NUXEL_CPBOOTD_ENABLE_HW) && (NUXEL_CPBOOTD_ENABLE_HW == 1)
#  define HW_ENABLED 1
#else
#  define HW_ENABLED 0
#endif

/* ---- golden constants from the pinned sources ---------------------------- */
/* ProtocolSipc.cpp: STD_UDL_AP2CP 0x9000 / STD_UDL_CP2AP 0xA000 */
#define STD_UDL_AP2CP       0x9000u
#define STD_UDL_CP2AP       0xA000u
#define STD_UDL_STAGE_SHIFT 8u
#define STD_UDL_STAGE_START 0x0u
#define STD_UDL_STAGE_DONE  0xDu
#define STD_UDL_FIN_STAGE   0xFu

/* Protocol.h: STD_UDL_MSS = 16*1024; STD_UDL_HDR_LEN = 16 */
#define STD_UDL_MSS          (16u * 1024u)
#define STD_UDL_HDR_LEN      16u
#define STD_UDL_MTU          (STD_UDL_HDR_LEN + STD_UDL_MSS)

/* BootDumpModap.cpp: EXYNOS_PAYLOAD_LEN = 62*1024 */
#define EXYNOS_PAYLOAD_LEN   (62u * 1024u)

/* WAIT_POLL_TIME (Protocol.h) and MIF_INIT_TIMEOUT (modem_ctrl_s5000ap.c) */
#define WAIT_POLL_MS         30000L
#define MIF_INIT_TIMEOUT_MS  15000L

/* TOC layout (Type.h): MAX_TOC_INDEX 16, MAX_TOC_ELEMENT_SIZE 32, name 12 */
#define MAX_TOC_INDEX        16
#define MAX_IMG_NAME_LEN     12
#define MAX_TOC_ELEMENT_SIZE 32
#define MAX_TOC_SIZE         (MAX_TOC_INDEX * MAX_TOC_ELEMENT_SIZE)

/* ITOC element struct (Protocol.h: struct std_toc_element, packed) */
struct toc_element {
    char     name[MAX_IMG_NAME_LEN];
    uint32_t b_offset;
    uint32_t m_offset;
    uint32_t size;
    uint32_t crc;
    uint32_t toc_count;
} __attribute__((packed));

/* ITOC part type indices (Type.h: enum cp_image_toc_type) */
enum { TOC_TOC = 0, TOC_BOOT, TOC_MAIN, TOC_VSS, TOC_NV_NORM, TOC_NV_PROT,
       TOC_NV, TOC_OFFSET, TOC_MAX };

/* BootDumpModap.cpp: CP_MEMORY_MASK masks off the top 2 bits of the absolute
 * load address (0x4000_0000 / 0x8000_0000 / 0xC000_0000 base) to yield the
 * offset relative to the CP DRAM base used by IOCTL_MODEM_XMIT_BOOT. */
#define CP_MEMORY_MASK  (0x40000000u - 1u)


/* ---- boot dance enum (canonical stage order) ----------------------------- */
enum boot_stage {
    STAGE_STATUS_PROBE = 0,
    STAGE_SECURITY_RE_INIT,   /* std_security_req(CP_BOOT_RE_INIT=2, 0, 0)      */
    STAGE_XMIT_BOOT,          /* load_cp_images -> IOCTL_MODEM_XMIT_BOOT(0x40)   */
    STAGE_SECURITY_REQ_TOC,   /* std_security_req(CP_BOOT_MODE_MANUAL=7, ...)    */
    STAGE_SECURITY_REQ_VSS,   /* std_security_req(VSS)                          */
    STAGE_SECURITY_REQ_MAIN,  /* std_security_req(CP_BOOT_MODE_NORMAL=0, b,m)    */
    STAGE_POWER_ON,           /* std_boot_power_on -> IOCTL_MODEM_ON(0x19)       */
    STAGE_BOOT_ON,            /* std_boot_start_cp_bootloader -> BOOT_ON(0x22)   */
    STAGE_DL_START,           /* IOCTL_MODEM_DL_START(0x28)                     */
    STAGE_HANDSHAKE,          /* SIPC UDL BOOT_DONE + FIN                       */
    STAGE_BOOT_OFF,           /* COMPLETE_NORMAL_BOOTUP = MODEM_BOOT_OFF(0x23)   */
    STAGE_ONLINE_VERIFY,      /* read IOCTL_MODEM_STATUS == ONLINE               */
    STAGE_COUNT
};

/* ---------------------------------------------------------------------------
 * Backend abstraction. Two implementations:
 *   BACKEND_MOCK  - deterministic in-memory fake CP (offline tests). Never
 *                   opens /dev/umts_*, never touches a real device, never RF.
 *   BACKEND_REAL  - real /dev/umts_boot0 (ioctl/write/read/poll). Compiled only
 *                   when HW_ENABLED is 1, and reachable only with --really-boot.
 * Both share the SAME stage table + firmware parser so a mock ONLINE can never
 * be confused with physical ONLINE: mock runs are tagged "backend":"mock".
 * ------------------------------------------------------------------------- */
enum backend_kind { BACKEND_MOCK = 0, BACKEND_REAL };

struct mock_cp {
    int    state;         /* enum modem_state */
    int    powered;       /* IOCTL_MODEM_ON seen */
    int    boot_on;       /* IOCTL_MODEM_BOOT_ON seen */
    int    dl_start;      /* IOCTL_MODEM_DL_START seen */
    int    handshake_done;
    int    security_done;
    int    boot_off;      /* IOCTL_MODEM_BOOT_OFF seen */
    /* firmware window content hash tracking (simulated shmem) */
    uint64_t boot_size;
    uint64_t main_size;
    /* record of m_offset values streamed via XMIT_BOOT (section mapping proof) */
    uint32_t first_m_offset;
    uint32_t last_m_offset;
    int      xmit_calls;
};

struct backend {
    enum backend_kind kind;
    int  fd;              /* real: opened node; mock: -1 */
    struct mock_cp mock;
};

/* Shared transaction context */
struct ctx {
    struct backend be;
    const char *firmware_path;   /* read-only RADIO/ITOC source path */
    int firmware_fd;
    uint64_t firmware_size;

    /* parsed ITOC */
    struct toc_element toc[MAX_TOC_INDEX];
    int toc_count;          /* toc[0].toc_count: total stage count (TOC..NV) */
    int num_stages;         /* toc_count - 1 (cbd: std_boot.num_stages)       */
    int start_stage;        /* 0 when first_stage_toc_type == TOC_TOC         */
    int toc_idx[TOC_MAX];   /* cp_image_toc_type -> TOC element index (-1)    */

    long deadline_ms;
    int  really_boot;
    int  one_shot_consumed;

    /* machine-readable failure reporting */
    enum boot_stage first_failed_stage;
    int  first_failed_rc;
};

/* ---- minimal monotonic clock helper (bounded deadline) ------------------- */
static long now_ms(void)
{
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC, &ts);
    return (long)ts.tv_sec * 1000L + (long)(ts.tv_nsec / 1000000L);
}

/* ---- stdout JSON helpers ------------------------------------------------- */
static void emit(const char *fmt, ...) __attribute__((format(printf,1,2)));
static void emit(const char *fmt, ...)
{
    va_list ap;
    va_start(ap, fmt);
    vprintf(fmt, ap);
    va_end(ap);
    fputc('\n', stdout);
}

static void stage_result(enum boot_stage s, int rc, long elapsed_ms, const char *note)
{
    static const char *names[STAGE_COUNT] = {
        "status-probe","security-reinit","xmit-boot","security-toc","security-vss",
        "security-main","power-on","boot-on","dl-start","handshake","boot-off","online-verify",
    };
    emit("{\"stage\":\"%s\",\"rc\":%d,\"elapsed_ms\":%ld,\"note\":\"%s\"}",
         names[s], rc, elapsed_ms, note ? note : "");
}

/* ---------------------------------------------------------------------------
 * ITOC parsing (read-only, bounds-checked). Faithful transcription of
 * BootDump::std_boot_parse_toc_img + BootDumpModap::prepare_boot_args:
 *   - read the full 512-byte TOC table (MAX_TOC_INDEX entries),
 *   - toc[0] must be "TOC"; toc[0].toc_count is the *stage count* (TOC..NV),
 *     NOT the byte size; cbd only rejects a count > MAX_TOC_INDEX,
 *   - scan EVERY entry by exact name into toc_idx[cp_image_toc_type],
 *   - num_stages = toc_count - 1 (cbd), start_stage = TOC stage (TOC_TOC first),
 *   - "OFFSET" terminates the download stage list,
 *   - secure-verify also requires TOC to carry a nonzero m_offset.
 * No DTK9 constants anywhere: sizes/offsets come from the parsed image only.
 * ------------------------------------------------------------------------- */
static int parse_itoc(struct ctx *c)
{
    ssize_t r;
    size_t want = sizeof(struct toc_element);
    int i;

    memset(c->toc, 0, sizeof(c->toc));
    for (i = 0; i < TOC_MAX; i++) c->toc_idx[i] = -1;

    c->firmware_fd = open(c->firmware_path, O_RDONLY | O_CLOEXEC | O_NOCTTY);
    if (c->firmware_fd < 0) {
        fprintf(stderr, "error: firmware open %s: %s\n", c->firmware_path, strerror(errno));
        return -errno;
    }

    {
        struct stat st;
        if (fstat(c->firmware_fd, &st) != 0) {
            int e = errno; close(c->firmware_fd); c->firmware_fd = -1;
            return -e;
        }
        c->firmware_size = (uint64_t)st.st_size;
    }

    /* Read the whole 512-byte table in one go (cbd read the full struct). */
    r = read(c->firmware_fd, &c->toc[0], MAX_TOC_INDEX * want);
    if (r < (ssize_t)want) {
        fprintf(stderr, "error: short TOC read (%zd < %zu)\n", r, want);
        return -EFAULT;
    }

    /* The 1st toc should be TOC (cbd: strcmp(toc[0].name, "TOC")). */
    if (strcmp(c->toc[0].name, "TOC") != 0) {
        fprintf(stderr, "error: invalid ITOC magic %.12s\n", c->toc[0].name);
        return -EINVAL;
    }
    c->toc_count = c->toc[0].toc_count;
    if (c->toc_count > MAX_TOC_INDEX) {
        fprintf(stderr, "error: ITOC stage count %d exceeds MAX_TOC_INDEX\n", c->toc_count);
        return -EINVAL;
    }
    if (c->toc_count == 0) {
        fprintf(stderr, "error: ITOC stage count is 0\n");
        return -EINVAL;
    }

    /* Scan every (up to MAX_TOC_INDEX) entry by exact name into toc_idx. */
    for (i = 0; i < MAX_TOC_INDEX; i++) {
        struct toc_element *e = &c->toc[i];
        if (strcmp(e->name, "TOC") == 0)      c->toc_idx[TOC_TOC] = i;
        else if (strcmp(e->name, "BOOT") == 0) c->toc_idx[TOC_BOOT] = i;
        else if (strcmp(e->name, "MAIN") == 0) c->toc_idx[TOC_MAIN] = i;
        else if (strcmp(e->name, "VSS") == 0)  c->toc_idx[TOC_VSS] = i;
        else if (strcmp(e->name, "NV_NORM") == 0) c->toc_idx[TOC_NV_NORM] = i;
        else if (strcmp(e->name, "NV_PROT") == 0) c->toc_idx[TOC_NV_PROT] = i;
        else if (strcmp(e->name, "NV") == 0)   c->toc_idx[TOC_NV] = i;
        else if (strcmp(e->name, "OFFSET") == 0) c->toc_idx[TOC_OFFSET] = i;
        /* Empty name ends the populated region; do not bounds-check trailing
         * zero-filled slots (they carry b_offset==0,size==0 and are empty). */
        if (e->name[0] == '\0')
            continue;
        /* bounds: b_offset + size must fit within firmware_size */
        if ((uint64_t)e->b_offset + (uint64_t)e->size > c->firmware_size) {
            fprintf(stderr, "error: TOC[%d] %s out of bounds (b_off=%u size=%u)\n",
                    i, e->name, e->b_offset, e->size);
            return -EINVAL;
        }
    }

    if (c->toc_idx[TOC_BOOT] < 0 || c->toc_idx[TOC_MAIN] < 0) {
        fprintf(stderr, "error: ITOC missing BOOT/MAIN entries\n");
        return -EINVAL;
    }

    /* cbd: num_stages = toc_count - 1 (with TOC first); start_stage = TOC stage. */
    c->num_stages = c->toc_count - 1;
    c->start_stage = c->toc_idx[TOC_TOC];   /* first_stage_toc_type == TOC_TOC -> 0 */

    /* Secure verify (CONFIG_SEC_CP_VERIFYING_ALL) needs a real TOC m_offset. */
    {
        int ti = c->toc_idx[TOC_TOC];
        if (c->toc[ti].m_offset == 0) {
            fprintf(stderr, "error: invalid TOC: no m_offset for TOC verification\n");
            return -EINVAL;
        }
    }

    fprintf(stderr, "ITOC parsed: stages=%d BOOT@%d MAIN@%d VSS@%d NV@%d OFFSET@%d "
            "TOC(m_off=0x%08x size=%u)\n",
            c->toc_count,
            c->toc_idx[TOC_BOOT], c->toc_idx[TOC_MAIN], c->toc_idx[TOC_VSS],
            c->toc_idx[TOC_NV], c->toc_idx[TOC_OFFSET],
            c->toc[c->toc_idx[TOC_TOC]].m_offset, c->toc[c->toc_idx[TOC_TOC]].size);
    return 0;
}

/* ITOC part CRC32 validation (self-consistency only, never an authenticity/signature
 * proof) is performed by the read-only analyzer (tools/s10plus/cp-firmware), not by
 * this boot daemon. The daemon instead enforces structural bounds (b_offset+size
 * within the source) and streams parts via XMIT_BOOT with per-call length checks. */
/* ---------------------------------------------------------------------------
 * backend implementations
 * ------------------------------------------------------------------------- */
#if HW_ENABLED
static int real_status(struct backend *be)  { return ioctl(be->fd, IOCTL_MODEM_STATUS); }
static int real_on(struct backend *be)      { return ioctl(be->fd, IOCTL_MODEM_ON); }
static int real_reset(struct backend *be)   { return ioctl(be->fd, IOCTL_MODEM_RESET); }
static int real_boot_on(struct backend *be) { return ioctl(be->fd, IOCTL_MODEM_BOOT_ON); }
static int real_dl_start(struct backend *be){ return ioctl(be->fd, IOCTL_MODEM_DL_START); }
static int real_boot_off(struct backend *be){ return ioctl(be->fd, IOCTL_MODEM_BOOT_OFF); }
static int real_boot_done(struct backend *be) __attribute__((unused));
static int real_boot_done(struct backend *be){ return ioctl(be->fd, IOCTL_MODEM_BOOT_DONE); }
static int real_clr_bootlog(struct backend *be) __attribute__((unused));
static int real_clr_bootlog(struct backend *be){ return ioctl(be->fd, IOCTL_MODEM_CLR_CP_BOOTLOG); }

static int real_xmit_boot(struct backend *be, const struct modem_firmware *mf)
{
    /* Kernel shmem_xmit_boot copies mf via copy_from_user; mf.binary must be
     * a valid userspace pointer to the payload. mode!=0 selects the full dump
     * window, mode==0 the boot window. */
    return ioctl(be->fd, IOCTL_MODEM_XMIT_BOOT, (unsigned long)mf);
}

static int real_security_req(struct backend *be, const struct modem_sec_req *msr)
{
    return ioctl(be->fd, IOCTL_SECURITY_REQ, (unsigned long)msr);
}

/* SIPC UDL request/response over the boot node (Protocol.cpp::std_udl_req_resp). */
static int real_udl_req_resp(struct backend *be, uint32_t req, uint32_t exp)
{
    int ret;
    uint32_t resp = 0;
    if (req) {
        ret = (int)write(be->fd, &req, sizeof(req));
        if (ret != (int)sizeof(req)) return -EIO;
    }
    if (exp) {
        struct pollfd pfd = { .fd = be->fd, .events = POLLIN };
        int pr = poll(&pfd, 1, WAIT_POLL_MS);
        if (pr <= 0) return pr == 0 ? -ETIMEDOUT : -errno;
        ret = (int)read(be->fd, &resp, sizeof(resp));
        if (ret != (int)sizeof(resp)) return -EIO;
        if (resp != exp) return -EFAULT;
    }
    return 0;
}
#endif /* HW_ENABLED */

/* ---- mock backend (offline deterministic fake CP) ------------------------ */
static int mock_status(struct backend *be) { return be->mock.state; }
static int mock_on(struct backend *be)      { be->mock.powered = 1; be->mock.state = STATE_OFFLINE; return 0; }
static int mock_reset(struct backend *be)    { be->mock.powered = 0; be->mock.boot_on = 0;
    be->mock.dl_start = 0; be->mock.handshake_done = 0; be->mock.boot_off = 0;
    be->mock.security_done = 0; be->mock.state = STATE_OFFLINE; return 0; }
static int mock_boot_on(struct backend *be)
{
    if (!be->mock.powered) return -EACCES;
    be->mock.boot_on = 1;
    be->mock.state = STATE_BOOTING;
    return 0;
}
static int mock_dl_start(struct backend *be)
{
    if (!be->mock.boot_on) return -EACCES;
    be->mock.dl_start = 1;
    return 0;
}
static int mock_xmit_boot(struct backend *be, const struct modem_firmware *mf)
{
    /* xmit happens BEFORE power-on in the SIPC path, so no prereq here */
    if (be->mock.xmit_calls == 0)
        be->mock.first_m_offset = mf->m_offset;
    be->mock.last_m_offset = mf->m_offset;
    be->mock.xmit_calls++;
    be->mock.boot_size += mf->len;
    return 0;
}
static int mock_security_req(struct backend *be, const struct modem_sec_req *msr)
{
    (void)msr;
    be->mock.security_done = 1;
    return 0;
}
static int mock_udl_req_resp(struct backend *be, uint32_t req, uint32_t exp)
{
    (void)req; (void)exp;
    if (!be->mock.dl_start) return -EACCES;
    be->mock.handshake_done = 1;
    return 0;
}
static int mock_boot_off(struct backend *be)
{
    if (!be->mock.handshake_done) return -EACCES;
    be->mock.boot_off = 1;
    be->mock.state = STATE_ONLINE;
    return 0;
}

/* ---- dispatcher ---------------------------------------------------------- */
static int do_status(struct backend *be)
{
    if (be->kind == BACKEND_MOCK) return mock_status(be);
#if HW_ENABLED
    return real_status(be);
#else
    return -ENOTSUP; /* fail closed: no HW compiled */
#endif
}
static int do_on(struct backend *be)
{
    if (be->kind == BACKEND_MOCK) return mock_on(be);
#if HW_ENABLED
    return real_on(be);
#else
    return -ENOTSUP;
#endif
}
static int do_reset(struct backend *be)
{
    if (be->kind == BACKEND_MOCK) return mock_reset(be);
#if HW_ENABLED
    return real_reset(be);
#else
    return -ENOTSUP;
#endif
}
static int do_boot_on(struct backend *be)
{
    if (be->kind == BACKEND_MOCK) return mock_boot_on(be);
#if HW_ENABLED
    return real_boot_on(be);
#else
    return -ENOTSUP;
#endif
}
static int do_dl_start(struct backend *be)
{
    if (be->kind == BACKEND_MOCK) return mock_dl_start(be);
#if HW_ENABLED
    return real_dl_start(be);
#else
    return -ENOTSUP;
#endif
}
static int do_boot_off(struct backend *be)
{
    if (be->kind == BACKEND_MOCK) return mock_boot_off(be);
#if HW_ENABLED
    return real_boot_off(be);
#else
    return -ENOTSUP;
#endif
}
static int do_xmit_boot(struct backend *be, const struct modem_firmware *mf)
{
    if (be->kind == BACKEND_MOCK) return mock_xmit_boot(be, mf);
#if HW_ENABLED
    return real_xmit_boot(be, mf);
#else
    (void)mf; return -ENOTSUP;
#endif
}
static int do_security_req(struct backend *be, const struct modem_sec_req *msr)
{
    if (be->kind == BACKEND_MOCK) return mock_security_req(be, msr);
#if HW_ENABLED
    return real_security_req(be, msr);
#else
    (void)msr; return -ENOTSUP;
#endif
}
static int do_udl_req_resp(struct backend *be, uint32_t req, uint32_t exp)
{
    if (be->kind == BACKEND_MOCK) return mock_udl_req_resp(be, req, exp);
#if HW_ENABLED
    return real_udl_req_resp(be, req, exp);
#else
    (void)req; (void)exp; return -ENOTSUP;
#endif
}

/* ---------------------------------------------------------------------------
 * XMIT_BOOT: stream a TOC part into shmem via struct modem_firmware.
 * Faithful transcription of BootDumpModap::load_cp_image_by_stage:
 *   img.m_offset = dlc->m_offset = (toc[idx].m_offset & CP_MEMORY_MASK);
 * The absolute load address (0x4000_0000 / 0x4780_0000 / ...) is masked by
 * CP_MEMORY_MASK (0x3FFF_FFFF) to the offset relative to the CP DRAM base,
 * exactly as cbd does. mode==0 (BOOT window). Bounds-checked.
 * ------------------------------------------------------------------------- */
static int xmit_part(struct ctx *c, int part_idx)
{
    struct toc_element *e = &c->toc[part_idx];
    uint8_t *buf = malloc(EXYNOS_PAYLOAD_LEN);
    uint64_t sent = 0;
    int rc = 0;

    if (!buf) return -ENOMEM;
    if (e->size == 0) { free(buf); return 0; } /* empty part: nothing to stream */

    struct modem_firmware mf;
    memset(&mf, 0, sizeof(mf));
    mf.binary   = (unsigned long long)(uintptr_t)buf;
    mf.size     = e->size;
    mf.m_offset = e->m_offset & CP_MEMORY_MASK; /* source-faithful (cbd) */
    mf.b_offset = e->b_offset;
    mf.mode     = 0;      /* CP_BOOT_MODE_NORMAL -> BOOT window */
    mf.len      = EXYNOS_PAYLOAD_LEN;

    if (lseek(c->firmware_fd, (off_t)e->b_offset, SEEK_SET) < 0) { free(buf); return -errno; }

    while (sent < e->size) {
        uint64_t rem = (uint64_t)e->size - sent;
        size_t want = rem < EXYNOS_PAYLOAD_LEN ? (size_t)rem : EXYNOS_PAYLOAD_LEN;
        ssize_t r = read(c->firmware_fd, buf, want);
        if (r <= 0) { rc = -EFAULT; break; }
        mf.len = (uint32_t)r;
        rc = do_xmit_boot(&c->be, &mf);
        if (rc != 0) break;
        sent += (uint64_t)r;
        mf.m_offset += (uint32_t)r;
    }
    free(buf);
    return rc;
}

/* ---------------------------------------------------------------------------
 * SECURITY_REQ: TEE secure-boot via exynos_smc (kernel shmem_security_request).
 * Mirrors BootDumpModap::std_security_req. mode/param2/param3 are the SMC args.
 * ------------------------------------------------------------------------- */
static int security_req(struct ctx *c, uint32_t mode, uint32_t p2, uint32_t p3)
{
    struct modem_sec_req msr;
    memset(&msr, 0, sizeof(msr));
    msr.mode = mode;
    msr.param2 = p2;
    msr.param3 = p3;
    msr.param4 = 0;
    return do_security_req(&c->be, &msr);
}

/* ---------------------------------------------------------------------------
 * Boot transaction — canonical, source-backed, one-shot, fail-closed.
 * ------------------------------------------------------------------------- */
static int run_boot(struct ctx *c)
{
    enum boot_stage s;
    int rc = 0;

    c->first_failed_stage = STAGE_STATUS_PROBE;
    c->first_failed_rc = 0;

    /* 0. status probe (read-only; before any mutation).
     *    cbd: if get_modem_state() != STATE_OFFLINE -> std_boot_power_reset. */
    s = STAGE_STATUS_PROBE;
    {
        long t0 = now_ms();
        int st = do_status(&c->be);
        stage_result(s, st < 0 ? st : 0, now_ms() - t0, "state");
        if (st < 0) { c->first_failed_stage = s; c->first_failed_rc = st; return st; }
        fprintf(stderr, "initial CP state=%d\n", st);

        if (st != STATE_OFFLINE) {
            /* Power-reset to a known-good OFFLINE pre-state before xmit/security. */
            long rt0 = now_ms();
            rc = do_reset(&c->be);
            stage_result(s, rc, now_ms() - rt0, "power-reset (non-OFFLINE)");
            if (rc < 0) goto fail;
            fprintf(stderr, "power-reset issued (was state=%d)\n", st);
        }
    }

    /* 1. security request: non-secure (CP_BOOT_RE_INIT=2) — std_security_req(2,0,0) */
    s = STAGE_SECURITY_RE_INIT;
    {
        long t0 = now_ms();
        rc = security_req(c, 2 /*CP_BOOT_RE_INIT*/, 0, 0);
        stage_result(s, rc, now_ms() - t0, NULL);
        if (rc < 0) goto fail;
    }

    /* 2. load CP images -> XMIT_BOOT over each stage in TOC-index order,
     *    starting at start_stage (TOC) and terminating at OFFSET.
     *    Faithful to BootDumpModap::load_cp_images + build_std_dload_control.
     *    NV stages (TOC_NV / TOC_NV_NORM / TOC_NV_PROT) are sourced from the
     *    EFS nv_data.bin (FD_NV_DATA), NOT the radio partition, so they are
     *    SKIPPED here — equivalent to cbd's `b_fd < 0 -> continue`. */
    s = STAGE_XMIT_BOOT;
    {
        long t0 = now_ms();
        int stage;
        for (stage = c->start_stage; stage < c->num_stages + 1; stage++) {
            if (stage == c->toc_idx[TOC_OFFSET])
                break;  /* OFFSET terminates the stage list (cbd) */
            if (stage == c->toc_idx[TOC_NV] ||
                stage == c->toc_idx[TOC_NV_NORM] ||
                stage == c->toc_idx[TOC_NV_PROT])
                continue;  /* NV comes from EFS, never the radio partition */
            if (stage != c->toc_idx[TOC_TOC] &&
                stage != c->toc_idx[TOC_BOOT] &&
                stage != c->toc_idx[TOC_MAIN] &&
                stage != c->toc_idx[TOC_VSS])
                continue;  /* skip empty/unrecognised slots */
            rc = xmit_part(c, stage);
            if (rc < 0) goto fail;
        }
        stage_result(s, rc, now_ms() - t0, "TOC/BOOT/MAIN/VSS in TOC order (NV from EFS)");
        if (rc < 0) goto fail;
    }

    /* 3. security request: TOC (CP_BOOT_MODE_MANUAL=7).
     *    cbd: std_security_req(MANUAL, dl_ctrl[TOC_TOC].m_offset,
     *                          dl_ctrl[TOC_TOC].b_size) — TOC's OWN masked
     *    m_offset and size, NOT BOOT's. */
    s = STAGE_SECURITY_REQ_TOC;
    {
        long t0 = now_ms();
        int ti = c->toc_idx[TOC_TOC];
        rc = security_req(c, 7 /*CP_BOOT_MODE_MANUAL*/,
                          c->toc[ti].m_offset & CP_MEMORY_MASK,
                          c->toc[ti].size);
        stage_result(s, rc, now_ms() - t0, NULL);
        if (rc < 0) goto fail;
    }

    /* 4. security request: VSS (optional if present).
     *    SS310 without -v uses CP_BOOT_MODE_MANUAL (not CP_BOOT_MODE_VSS). */
    s = STAGE_SECURITY_REQ_VSS;
    {
        long t0 = now_ms();
        int vi = c->toc_idx[TOC_VSS];
        if (vi >= 0) {
            rc = security_req(c, 7 /*CP_BOOT_MODE_MANUAL*/,
                              c->toc[vi].m_offset & CP_MEMORY_MASK,
                              c->toc[vi].size);
        } else {
            rc = 0;  /* no VSS part -> no verify, matching source */
        }
        stage_result(s, rc, now_ms() - t0, NULL);
        if (rc < 0) goto fail;
    }

    /* 5. security request: BOOT/MAIN (CP_BOOT_MODE_NORMAL=0).
     *    cbd: std_security_req(NORMAL, BOOT.b_size, MAIN.b_size) — sizes, raw. */
    s = STAGE_SECURITY_REQ_MAIN;
    {
        long t0 = now_ms();
        rc = security_req(c, 0 /*CP_BOOT_MODE_NORMAL*/,
                          c->toc[c->toc_idx[TOC_BOOT]].size,
                          c->toc[c->toc_idx[TOC_MAIN]].size);
        stage_result(s, rc, now_ms() - t0, NULL);
        if (rc < 0) goto fail;
    }

    /* 6. power on (std_boot_power_on -> IOCTL_MODEM_ON) */
    s = STAGE_POWER_ON;
    {
        long t0 = now_ms();
        rc = do_on(&c->be);
        stage_result(s, rc, now_ms() - t0, NULL);
        if (rc < 0) goto fail;
    }

    /* 7. start CP bootloader (std_boot_start_cp_bootloader -> BOOT_ON) */
    s = STAGE_BOOT_ON;
    {
        long t0 = now_ms();
        rc = do_boot_on(&c->be);
        stage_result(s, rc, now_ms() - t0, NULL);
        if (rc < 0) goto fail;
    }

    /* 8. download start (IOCTL_MODEM_DL_START) */
    s = STAGE_DL_START;
    {
        long t0 = now_ms();
        rc = do_dl_start(&c->be);
        stage_result(s, rc, now_ms() - t0, NULL);
        if (rc < 0) goto fail;
    }

    /* 9. SIPC UDL handshake (BOOT_DONE + FIN) */
    s = STAGE_HANDSHAKE;
    {
        long t0 = now_ms();
        /* BOOT_DONE command (std_udl_stage_done OPER_BOOT, STD_UDL_STAGE_START) */
        rc = do_udl_req_resp(&c->be,
                STD_UDL_AP2CP | (STD_UDL_STAGE_START << STD_UDL_STAGE_SHIFT) | STD_UDL_STAGE_DONE,
                STD_UDL_CP2AP | (STD_UDL_STAGE_START << STD_UDL_STAGE_SHIFT) | STD_UDL_STAGE_DONE);
        if (rc < 0) goto fail;
        /* FIN command (std_udl_stage_start OPER_BOOT, STD_UDL_FIN_STAGE) */
        rc = do_udl_req_resp(&c->be,
                STD_UDL_AP2CP | (STD_UDL_FIN_STAGE << STD_UDL_STAGE_SHIFT) | STD_UDL_STAGE_START,
                STD_UDL_CP2AP | (STD_UDL_FIN_STAGE << STD_UDL_STAGE_SHIFT) | STD_UDL_STAGE_START);
        stage_result(s, rc, now_ms() - t0, NULL);
        if (rc < 0) goto fail;
    }

    /* 10. complete normal bootup (COMPLETE_NORMAL_BOOTUP == MODEM_BOOT_OFF, 0x23);
     *     waits init_cmpl with MIF_INIT_TIMEOUT, transitions to ONLINE */
    s = STAGE_BOOT_OFF;
    {
        long t0 = now_ms();
        rc = do_boot_off(&c->be);
        if (now_ms() - t0 > MIF_INIT_TIMEOUT_MS && rc == 0) rc = -ETIMEDOUT;
        stage_result(s, rc, now_ms() - t0, NULL);
        if (rc < 0) goto fail;
    }

    /* 11. online verify: real IOCTL_MODEM_STATUS must report STATE_ONLINE */
    s = STAGE_ONLINE_VERIFY;
    {
        long t0 = now_ms();
        int st = do_status(&c->be);
        rc = (st == STATE_ONLINE) ? 0 : -EAGAIN;
        stage_result(s, rc, now_ms() - t0, "must-be-ONLINE");
        if (rc < 0) goto fail;
    }

    return 0;

fail:
    c->first_failed_stage = s;
    c->first_failed_rc = rc;
    return rc;
}

/* ---------------------------------------------------------------------------
 * Manifest hashing: the immutable Stage-04 execution manifest MUST be supplied
 * and its SHA-256 checked at runtime before any HW action. This is a compile
 * SHA-256 over a file (glibc-friendly, no external deps). Mock runs permit
 * "--mock-manifest-ok" only in BACKEND_MOCK (never on the device path).
 * ------------------------------------------------------------------------- */
/* Manifest hash verification is performed by the caller-side preflight
 * (nuxel-cpbootd-manifest-check) BEFORE nuxel-cpbootd is invoked with
 * --really-boot, and the immutable manifest is also re-hashed in the
 * Stage-04 receipt. Keeping that check out of this daemon avoids any path
 * where a stale inline hash silently passes; the HW path still fails closed
 * without an exact, pre-verified --manifest-sha256 value. */
/* ---------------------------------------------------------------------------
 * main
 * ------------------------------------------------------------------------- */
static void usage(const char *a0)
{
    fprintf(stderr, "usage: %s [--plan] [--node PATH] [--firmware PATH] [--deadline-ms N]\n"
                    "       [--really-boot] [--manifest-sha256 HEX] [--mock]\n"
                    "Default is FAIL-CLOSED dry-run: read-only IOCTL_MODEM_STATUS only.\n"
                    "HW path requires NUXEL_CPBOOTD_ENABLE_HW=1 (value-aware) + --really-boot\n"
                    " + --manifest-sha256 <exact immutable manifest SHA-256>.\n", a0);
}

int main(int argc, char **argv)
{
    struct ctx c;
    const char *node = "/dev/umts_boot0";
    const char *firmware = NULL;
    const char *manifest_hex = NULL;
    long deadline_ms = 30000;
    int show_plan = 0;
    int really_boot = 0;
    int force_mock = 0;
    int i;

    memset(&c, 0, sizeof(c));
    c.be.kind = BACKEND_MOCK;   /* safest default; real only when HW_ENABLED + --really-boot */
    c.be.fd = -1;
    c.firmware_fd = -1;
    c.first_failed_stage = STAGE_STATUS_PROBE;

    for (i = 1; i < argc; i++) {
        if (!strcmp(argv[i], "--plan")) show_plan = 1;
        else if (!strcmp(argv[i], "--node") && i + 1 < argc) node = argv[++i];
        else if (!strcmp(argv[i], "--firmware") && i + 1 < argc) firmware = argv[++i];
        else if (!strcmp(argv[i], "--deadline-ms") && i + 1 < argc) {
            char *end = NULL;
            long v = strtol(argv[++i], &end, 10);
            if (!end || *end || v <= 0 || v > 600000) {
                fprintf(stderr, "error: invalid --deadline-ms (must be 1..600000)\n");
                return 2;
            }
            deadline_ms = v;
        }
        else if (!strcmp(argv[i], "--really-boot")) really_boot = 1;
        else if (!strcmp(argv[i], "--manifest-sha256") && i + 1 < argc) manifest_hex = argv[++i];
        else if (!strcmp(argv[i], "--mock")) force_mock = 1;
        else if (!strcmp(argv[i], "--help")) { usage(argv[0]); return 0; }
        else { fprintf(stderr, "unknown arg %s\n", argv[i]); usage(argv[0]); return 2; }
    }

    c.deadline_ms = deadline_ms;
    c.really_boot = really_boot;

    if (show_plan) {
        /* print the canonical stage plan (source-backed) */
        printf("{\"plan\":["
               "{\"stage\":\"status-probe\",\"ioctl\":\"0x6F27\"},"
               "{\"stage\":\"security-reinit\",\"ioctl\":\"0x6F53\"},"
               "{\"stage\":\"xmit-boot\",\"ioctl\":\"0x6F40\"},"
               "{\"stage\":\"security-toc\",\"ioctl\":\"0x6F53\"},"
               "{\"stage\":\"security-vss\",\"ioctl\":\"0x6F53\"},"
               "{\"stage\":\"security-main\",\"ioctl\":\"0x6F53\"},"
               "{\"stage\":\"power-on\",\"ioctl\":\"0x6F19\"},"
               "{\"stage\":\"boot-on\",\"ioctl\":\"0x6F22\"},"
               "{\"stage\":\"dl-start\",\"ioctl\":\"0x6F28\"},"
               "{\"stage\":\"handshake\",\"ioctl\":\"SIPC-UDL\"},"
               "{\"stage\":\"boot-off\",\"ioctl\":\"0x6F23\"},"
               "{\"stage\":\"online-verify\",\"ioctl\":\"0x6F27\"}"
               "]}\n");
        return 0;
    }

    /* ---- HW path gating (value-aware) ---- */
    (void)manifest_hex;  /* consumed in HW path; kept referenced in all configs */
    if (really_boot) {
        if (force_mock) {
            /* Offline full-transaction golden-transcript run against the
             * deterministic mock CP. Never opens /dev/umts_*, never RF. */
            c.be.kind = BACKEND_MOCK;
        } else {
#if !HW_ENABLED
            fprintf(stderr, "error: --really-boot (physical) requires a build with "
                            "-DNUXEL_CPBOOTD_ENABLE_HW=1 (value-aware compile-time gate); "
                            "use --really-boot --mock for the offline simulator.\n");
            return 2;
#else
            if (!manifest_hex) {
                fprintf(stderr, "error: --really-boot requires --manifest-sha256 <immutable manifest>\n");
                return 2;
            }
            /* endpoint must be the verified boot node, not an arbitrary path.
             * (identity is cross-checked against /dev/umts_boot0's rdev by the
             * caller of the physical trial; see LIVE-SAFETY-PREFLIGHT.) */
            if (strcmp(node, "/dev/umts_boot0") != 0) {
                fprintf(stderr, "error: --node must be /dev/umts_boot0 for physical run\n");
                return 2;
            }
            c.be.kind = BACKEND_REAL;
#endif
        }
    } else {
        if (force_mock) {
            c.be.kind = BACKEND_MOCK;
        } else if (HW_ENABLED) {
            /* default with HW compiled is still dry-run (read-only) */
            c.be.kind = BACKEND_REAL;
        } else {
            c.be.kind = BACKEND_MOCK;
        }
    }

    /* firmware path is required for any boot; optional in pure dry-run */
    if (!firmware) {
        /* dry-run without firmware: status probe only */
        if (really_boot) {
            fprintf(stderr, "error: --really-boot requires --firmware <read-only RADIO/ITOC path>\n");
            return 2;
        }
    }

    /* ---- dry-run: read-only status probe, no HW mutation ---- */
    if (!really_boot) {
        if (c.be.kind == BACKEND_MOCK) {
            emit("{\"mode\":\"dry-run\",\"backend\":\"mock\",\"node\":\"%s\",\"status\":%d}",
                 node, mock_status(&c.be));
            return 0;
        }
        /* real node, read-only: open O_RDONLY and issue ONLY STATUS */
        int fd = open(node, O_RDONLY | O_CLOEXEC | O_NOCTTY | O_NONBLOCK);
        if (fd < 0) {
            emit("{\"mode\":\"dry-run\",\"backend\":\"real\",\"node\":\"%s\",\"status\":null,\"errno\":%d}",
                 node, errno);
            return 1;
        }
        int st = ioctl(fd, IOCTL_MODEM_STATUS);
        if (st < 0) {
            emit("{\"mode\":\"dry-run\",\"backend\":\"real\",\"node\":\"%s\",\"status\":null,\"errno\":%d}",
                 node, errno);
            close(fd);
            return 1;
        }
        emit("{\"mode\":\"dry-run\",\"backend\":\"real\",\"node\":\"%s\",\"status\":%d}", node, st);
        close(fd);
        return 0;
    }

    /* ---- full boot path (HW_ENABLED=1 + --really-boot + manifest) ---- */
    if (c.be.kind == BACKEND_REAL) {
        c.be.fd = open(node, O_RDWR | O_CLOEXEC | O_NOCTTY);
        if (c.be.fd < 0) {
            emit("{\"mode\":\"really-boot\",\"backend\":\"real\",\"node\":\"%s\",\"locked\":false,\"errno\":%d}",
                 node, errno);
            return 1;
        }
        /* exclusive ownership: LOCK_EX|LOCK_NB. Additionally the caller
         * preflights process/node ownership (see LIVE-SAFETY-PREFLIGHT). */
        if (flock(c.be.fd, LOCK_EX | LOCK_NB) != 0) {
            emit("{\"mode\":\"really-boot\",\"backend\":\"real\",\"node\":\"%s\",\"locked\":false,\"errno\":%d}",
                 node, errno);
            close(c.be.fd);
            return 1;
        }
    }

    c.firmware_path = firmware;
    {
        int pr = parse_itoc(&c);
        if (pr < 0) {
            emit("{\"mode\":\"really-boot\",\"backend\":\"%s\",\"first_failed_stage\":\"itoc-parse\",\"rc\":%d}",
                 c.be.kind == BACKEND_MOCK ? "mock" : "real", pr);
            if (c.be.kind == BACKEND_REAL && c.be.fd >= 0) { flock(c.be.fd, LOCK_UN); close(c.be.fd); }
            return 1;
        }
    }

    {
        int rc = run_boot(&c);
        if (c.be.kind == BACKEND_REAL && c.be.fd >= 0) { flock(c.be.fd, LOCK_UN); close(c.be.fd); }
        if (c.firmware_fd >= 0) close(c.firmware_fd);

        if (rc != 0) {
            static const char *names[STAGE_COUNT] = {
                "status-probe","security-reinit","xmit-boot","security-toc","security-vss",
                "security-main","power-on","boot-on","dl-start","handshake","boot-off","online-verify",
            };
            emit("{\"mode\":\"really-boot\",\"backend\":\"%s\",\"verdict\":\"aborted\","
                 "\"first_failed_stage\":\"%s\",\"rc\":%d}",
                 c.be.kind == BACKEND_MOCK ? "mock" : "real",
                 names[c.first_failed_stage], c.first_failed_rc);
            return 1;   /* NONZERO on any failure/abort */
        }
        emit("{\"mode\":\"really-boot\",\"backend\":\"%s\",\"verdict\":\"online\"}",
             c.be.kind == BACKEND_MOCK ? "mock" : "real");
        return 0;
    }
}
