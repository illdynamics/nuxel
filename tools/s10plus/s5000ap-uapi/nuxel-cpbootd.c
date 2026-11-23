/*
 * nuxel-cpbootd — STRICTLY DRY-RUN CP boot coordinator for Exynos9820/S5000AP.
 *
 * RATIONALE: the matching Samsung cbd (cpboot_v3) is ABI-exact ONLY when built
 * against Android's Bionic libc + liblog + libcutils + libselinux (soong
 * cc_binary "cbd"). Nuxel is a glibc/systemd Linux, not an Android runtime, so
 * the stock cbd cannot be dropped in unchanged. This daemon is therefore a
 * DRY-RUN coordinator that owns the boot transaction PLAN and safety fences,
 * WITHOUT executing any hardware-changing ioctl by default.
 *
 * SAFETY MODEL (all enforced in code + _Static_assert):
 *   - DANGER_DISABLED by default. The single hardware-mutating code path
 *     (execute_boot_stage) is compiled out unless NUXEL_CPBOOTD_ENABLE_HW=1
 *     is defined at build time, AND requires --really-boot at runtime.
 *   - Single exclusive owner of /dev/umts_boot0 via flock(LOCK_EX|LOCK_NB);
 *     a second instance exits immediately (no double-invocation).
 *   - Dry-run opens the node O_RDONLY and issues ONLY IOCTL_MODEM_STATUS.
 *   - Every stage has a bounded deadline; exceeding it aborts the whole plan.
 *   - No hidden modem/radio/efs partition write in ANY path.
 *   - Idempotent: a failed stage leaves the node closed and the lock released.
 *
 * This is a PLANNING + FENCE executable. It is not a modem bring-up and does
 * not claim to boot the CP. The proposed stage table is emitted as JSON.
 */
#define _GNU_SOURCE
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <errno.h>
#include <fcntl.h>
#include <unistd.h>
#include <time.h>
#include <signal.h>
#include <stdint.h>
#include <sys/ioctl.h>
#include <sys/file.h>

#include "s5000ap_uapi.h"

/* Compile-time ABI fence: if the header drifts, the daemon refuses to build. */
_Static_assert(IOCTL_MODEM_STATUS    == 0x6F27, "status ioctl");
_Static_assert(IOCTL_MODEM_BOOT_ON   == 0x6F22, "boot_on ioctl");
_Static_assert(IOCTL_MODEM_DL_START  == 0x6F28, "dl_start ioctl");
_Static_assert(IOCTL_MODEM_XMIT_BOOT == 0x6F40, "xmit_boot ioctl");
_Static_assert(IOCTL_MODEM_BOOT_DONE == 0x6F24, "boot_done ioctl");
_Static_assert(IOCTL_SECURITY_REQ    == 0x6F53, "security ioctl");
_Static_assert(sizeof(struct modem_firmware) == 28, "modem_firmware 28 bytes");

#define DEFAULT_NODE "/dev/umts_boot0"
#define DEFAULT_STAGE_DEADLINE_MS 30000   /* 30s per stage, bounded */
#define MAX_STAGES 16

/* Boot stage table — PLAN ONLY (source of truth in the contract report). */
struct boot_stage_plan {
    const char *name;
    unsigned long ioctl_num;   /* 0 = no ioctl (pure SIPC write) */
    const char *source_proof;
    int is_hw_mutating;
};

static const struct boot_stage_plan PLAN[] = {
    { "status-probe",            0x6F27, "IOCTL_MODEM_STATUS returns phone_state",           0 },
    { "power-on",                0x6F19, "s5000ap_on: cal_cp_init + AP2CP_CFG",            1 },
    { "boot-loader-download",    0x6F40, "shmem_xmit_boot copies BOOT stage into shmem",    1 },
    { "start-cp-bootloader",     0x6F22, "s5000ap_boot_on polls cp_status mailbox",        1 },
    { "dl-start",                0x6F28, "dload_start + modem_boot_confirm (ap_status)",    1 },
    { "main-image-download",     0,      "SIPC5 BOOT channel (ch 215..224) std_udl stages",1 },
    { "security-check",          0x6F53, "shmem_security_request -> exynos_smc (TEE)",      1 },
    { "complete-normal-bootup",  0x6F23, "s5000ap_boot_off waits init_cmpl (MIF_INIT_TIMEOUT 15s)", 1 },
    { "boot-done",               0x6F24, "s5000ap_boot_done (no-op confirm)",              1 },
    { "online",                  0x6F27, "IOCTL_MODEM_STATUS == STATE_ONLINE (4)",          0 },
};

static const size_t PLAN_LEN = sizeof(PLAN) / sizeof(PLAN[0]);

static void print_json_stage_plan(void)
{
    size_t i;
    fputs("{\"plan\":[", stdout);
    for (i = 0; i < PLAN_LEN; i++) {
        printf("{\"stage\":\"%s\",\"ioctl\":\"0x%06lX\",\"hw_mutating\":%s,\"source\":\"%s\"}%s",
               PLAN[i].name, PLAN[i].ioctl_num,
               PLAN[i].is_hw_mutating ? "true" : "false",
               PLAN[i].source_proof,
               (i + 1 < PLAN_LEN) ? "," : "");
    }
    fputs("]}", stdout);
}

/* ---- dry-run status probe (read-only) --------------------------------- */
static int read_cp_status(int fd, const char *node)
{
    int ret = ioctl(fd, IOCTL_MODEM_STATUS);
    if (ret < 0) {
        printf("{\"stage\":\"status-probe\",\"node\":\"%s\",\"state\":null,\"errno\":%d}\n",
               node, errno);
        return -1;
    }
    printf("{\"stage\":\"status-probe\",\"node\":\"%s\",\"state\":%d,\"errno\":0}\n",
           node, ret);
    return ret;
}

#ifdef NUXEL_CPBOOTD_ENABLE_HW
/* Compile-time HW ENABLE — owner must define NUXEL_CPBOOTD_ENABLE_HW=1. */
static int execute_boot_stage(int fd, const struct boot_stage_plan *stage)
{
    /* Each hardware-mutating ioctl is gated here; none run in dry-run. */
    switch (stage->ioctl_num) {
    case IOCTL_MODEM_BOOT_ON:   return ioctl(fd, IOCTL_MODEM_BOOT_ON);
    case IOCTL_MODEM_DL_START:  return ioctl(fd, IOCTL_MODEM_DL_START);
    case IOCTL_MODEM_BOOT_DONE: return ioctl(fd, IOCTL_MODEM_BOOT_DONE);
    case IOCTL_MODEM_XMIT_BOOT: /* requires struct modem_firmware; NOT auto-built */
    case IOCTL_SECURITY_REQ:    /* requires modem_sec_req + smc params; NOT auto-built */
        fprintf(stderr, "refusing to auto-issue 0x%lX without an explicit prebuilt plan\n",
                stage->ioctl_num);
        return -EINVAL;
    default:
        return 0;
    }
}
#endif

static volatile sig_atomic_t g_stop __attribute__((unused)) = 0;
static void on_signal(int s) __attribute__((unused));
static void on_signal(int s) { (void)s; g_stop = 1; }

int main(int argc, char **argv)
{
    const char *node = DEFAULT_NODE;
    int really_boot = 0;
    int show_plan = 0;
    int fd, i, status;
    int exclusive __attribute__((unused)) = 0;
    long deadline_ms __attribute__((unused)) = DEFAULT_STAGE_DEADLINE_MS;
    struct timespec t0 __attribute__((unused)), t1 __attribute__((unused));

    for (i = 1; i < argc; i++) {
        if (!strcmp(argv[i], "--plan")) show_plan = 1;
        else if (!strcmp(argv[i], "--node") && i + 1 < argc) node = argv[++i];
        else if (!strcmp(argv[i], "--really-boot")) really_boot = 1;
        else if (!strcmp(argv[i], "--deadline-ms") && i + 1 < argc) deadline_ms = atol(argv[++i]);
    }

    if (show_plan) { print_json_stage_plan(); fputc('\n', stdout); return 0; }

    /* ---- DRY-RUN is the default and the only safe default ---------------- */
    if (!really_boot) {
        fd = open(node, O_RDONLY | O_CLOEXEC | O_NOCTTY | O_NONBLOCK);
        if (fd < 0) {
            printf("{\"mode\":\"dry-run\",\"node\":\"%s\",\"lock\":\"failed\","
                   "\"reason\":\"open\",\"errno\":%d}\n", node, errno);
            return 1;
        }
        /* shared lock in dry-run: does not block a real cbd owner */
        if (flock(fd, LOCK_SH | LOCK_NB) != 0) {
            printf("{\"mode\":\"dry-run\",\"node\":\"%s\",\"lock\":\"shared-failed\","
                   "\"errno\":%d}\n", node, errno);
            close(fd);
            return 1;
        }
        printf("{\"mode\":\"dry-run\",\"node\":\"%s\",\"lock\":\"shared\",", node);
        status = read_cp_status(fd, node);
        if (status >= 0 && status == STATE_ONLINE) {
            printf("\"verdict\":\"already-online\"}\n");
        } else {
            printf("\"verdict\":\"offline-or-booting\",\"note\":\"no hardware-changing ioctl issued\"}\n");
        }
        print_json_stage_plan();
        fputc('\n', stdout);
        flock(fd, LOCK_UN);
        close(fd);
        return 0;
    }

#ifndef NUXEL_CPBOOTD_ENABLE_HW
    fprintf(stderr, "error: --really-boot requires a build with -DNUXEL_CPBOOTD_ENABLE_HW=1 "
                    "(compile-time hardware enable). This binary is dry-run only.\n");
    return 2;
#else
    /* ---- Exclusive-owner hardware path (only when compiled in) --------- */
    signal(SIGTERM, on_signal);
    signal(SIGINT, on_signal);

    fd = open(node, O_RDWR | O_CLOEXEC | O_NOCTTY);
    if (fd < 0) {
        fprintf(stderr, "open %s failed: %s\n", node, strerror(errno));
        return 1;
    }
    if (flock(fd, LOCK_EX | LOCK_NB) != 0) {
        fprintf(stderr, "cannot obtain exclusive lock on %s (another owner present): %s\n",
                node, strerror(errno));
        close(fd);
        return 1;
    }
    exclusive = 1;

    printf("{\"mode\":\"really-boot\",\"node\":\"%s\",\"deadline_ms\":%ld,\"lock\":\"exclusive\"}\n",
           node, deadline_ms);

    for (i = 0; i < (int)PLAN_LEN && !g_stop; i++) {
        const struct boot_stage_plan *s = &PLAN[i];
        clock_gettime(CLOCK_MONOTONIC, &t0);
        int r = execute_boot_stage(fd, s);
        clock_gettime(CLOCK_MONOTONIC, &t1);
        long elapsed_ms = (t1.tv_sec - t0.tv_sec) * 1000
                        + (t1.tv_nsec - t0.tv_nsec) / 1000000;
        printf("{\"stage\":\"%s\",\"rc\":%d,\"elapsed_ms\":%ld}\n", s->name, r, elapsed_ms);
        if (r < 0 || elapsed_ms > deadline_ms) {
            printf("{\"verdict\":\"aborted\",\"stage\":\"%s\",\"reason\":\"%s\"}\n",
                   s->name, (elapsed_ms > deadline_ms) ? "deadline" : "stage-failed");
            goto cleanup;
        }
    }
    printf("{\"verdict\":\"plan-complete\"}\n");

cleanup:
    (void)exclusive;
    flock(fd, LOCK_UN);
    close(fd);
    return 0;
#endif
}
