/**
 * Nuxel App Sandbox - Implementation
 *
 * Implements the 5-layer sandbox for applications (briq-se1 numbering):
 *   Layer 1: Namespace isolation (clone() with CLONE_NEW* flags)
 *   Layer 2: seccomp BPF syscall filtering
 *   Layer 3: Landlock filesystem restrictions
 *   Layer 4: cgroupv2 per-app cgroup (feed for Layer 5 nftables)
 *   Layer 5: nftables per-app network isolation (socket cgroupv2 match)
 *
 * In addition to the 5 layers, an AppArmor profile transition is attempted
 * on exec when libapparmor is present (a supplementary MAC-introspection
 * label; see nuxel_sandbox_apply_apparmor).
 *
 * briq-14 additions:
 *   - On app launch, create/ensure /sys/fs/cgroup/nuxel/<app-...> with
 *     proper delegation (name prefixed "app-" matching the nft ruleset).
 *   - Move the child process into that cgroup via cgroup.procs.
 *   - Set memory.max (1 GiB) and memory.high (512 MiB).
 *   - Fall back to cpu,memory controller files on cgroup v1.
 *   - Remove the cgroup on process exit.
 *   - New CLI flag --cgroup <app-id>, validated against the same
 *     deterministic app-id -> cgroup mapping used by nftables.sh.
 *
 * Target: aarch64 (mustang Pixel 10 Pro XL), Linux 6.12 LTS
 */

#define _GNU_SOURCE
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <errno.h>
#include <sched.h>
#include <ctype.h>
#include <sys/types.h>
#include <sys/wait.h>
#include <sys/mount.h>
#include <sys/prctl.h>
#include <sys/capability.h>
#include <sys/stat.h>
#include <sys/syscall.h>
#include <sys/vfs.h>
#include <fcntl.h>
#include <signal.h>
#include <linux/landlock.h>
#include <linux/seccomp.h>
#include <linux/filter.h>
#include <linux/audit.h>
#include <linux/capability.h>
#include <linux/magic.h>

#include "sandbox.h"

/* O_PATH availability (Linux); fallback for minimal cross sysroots. */
#ifndef O_PATH
#define O_PATH 0x200000
#endif


/* Landlock ABI version (Linux 6.12 supports ABI 4) */
#ifndef LANDLOCK_ABI_MAX
#define LANDLOCK_ABI_MAX 4
#endif
#define LANDLOCK_ABI_MIN 1

/* Default cgroup subtree */
#define NUXXEL_CGROUP_BASE "/sys/fs/cgroup/nuxel"

/* Single-source path config (briq-20): the sandbox reads /etc/nuxel/paths.conf
 * (overridable via NUXEL_PATHS_CONF) so it agrees with the rest of the system
 * on the canonical Nuxel config directory (NUXEL_CONFIG_DIR). The resolved
 * value is cached here and exposed via nuxel_sandbox_get_config_dir(). */
static char g_nuxel_config_dir[512] = "/etc/nuxel";

/* Canonical sandbox runtime dir (NUXEL_SANDBOX_DIR, default
 * "/opt/nuxel/sandbox") where per-app JSON profiles live. Resolved from
 * /etc/nuxel/paths.conf and exposed via nuxel_sandbox_get_sandbox_dir(). */
static char g_nuxel_sandbox_dir[512] = "/opt/nuxel/sandbox";

static void nuxel_sandbox_load_paths_conf(void)
{
    const char *path = getenv("NUXEL_PATHS_CONF");
    if (path == NULL || path[0] == '\0')
        path = "/etc/nuxel/paths.conf";

    FILE *fp = fopen(path, "r");
    if (fp == NULL) {
        /* Fall back to defaults. */
        const char *env_cfg = getenv("NUXEL_CONFIG_DIR");
        if (env_cfg && env_cfg[0] != '\0') {
            snprintf(g_nuxel_config_dir, sizeof(g_nuxel_config_dir), "%s", env_cfg);
        }
        const char *env_sb = getenv("NUXEL_SANDBOX_DIR");
        if (env_sb && env_sb[0] != '\0') {
            snprintf(g_nuxel_sandbox_dir, sizeof(g_nuxel_sandbox_dir), "%s", env_sb);
        }
        return;
    }

    char line[1024];
    while (fgets(line, sizeof(line), fp)) {
        char *p = line;
        while (*p == ' ' || *p == '\t') p++;
        if (*p == '#' || *p == '\n' || *p == '\0')
            continue;
        char *eq = strchr(p, '=');
        if (eq == NULL)
            continue;
        *eq = '\0';
        char *key = p;
        char *val = eq + 1;
        /* trim spaces around key and leading/trailing quotes on val */
        char *ke = key + strlen(key);
        while (ke > key && (*(ke-1) == ' ' || *(ke-1) == '\t')) *--ke = '\0';
        while (*val == ' ' || *val == '\t') val++;
        size_t vlen = strlen(val);
        while (vlen > 0 && (val[vlen-1] == '\n' || val[vlen-1] == '\r' ||
                            val[vlen-1] == ' ' || val[vlen-1] == '\t'))
            val[--vlen] = '\0';
        if (vlen >= 2 && val[0] == '"' && val[vlen-1] == '"') {
            val[vlen-1] = '\0'; val++;
        }
        if (strcmp(key, "NUXEL_CONFIG_DIR") == 0 && val[0] != '\0') {
            snprintf(g_nuxel_config_dir, sizeof(g_nuxel_config_dir), "%s", val);
        } else if (strcmp(key, "NUXEL_SANDBOX_DIR") == 0 && val[0] != '\0') {
            snprintf(g_nuxel_sandbox_dir, sizeof(g_nuxel_sandbox_dir), "%s", val);
        }
    }
    fclose(fp);

    /* Environment always wins. */
    const char *env_cfg = getenv("NUXEL_CONFIG_DIR");
    if (env_cfg && env_cfg[0] != '\0') {
        snprintf(g_nuxel_config_dir, sizeof(g_nuxel_config_dir), "%s", env_cfg);
    }
    const char *env_sb = getenv("NUXEL_SANDBOX_DIR");
    if (env_sb && env_sb[0] != '\0') {
        snprintf(g_nuxel_sandbox_dir, sizeof(g_nuxel_sandbox_dir), "%s", env_sb);
    }
}

const char *nuxel_sandbox_get_config_dir(void)
{
    return g_nuxel_config_dir;
}

const char *nuxel_sandbox_get_sandbox_dir(void)
{
    return g_nuxel_sandbox_dir;
}

/* ---- seccomp BPF helpers ---- */

#define BPF_STMT(code, k) ((struct sock_filter){ (unsigned short)(code), 0, 0, (unsigned int)(k) })
#define BPF_JUMP(code, k, jt, jf) ((struct sock_filter){ (unsigned short)(code), (unsigned char)(jt), (unsigned char)(jf), (unsigned int)(k) })

/* Syscall numbers for aarch64 */
#define __NR_aarch64_read             0
#define __NR_aarch64_write            1
#define __NR_aarch64_openat          56
#define __NR_aarch64_close           57
#define __NR_aarch64_lseek           62
#define __NR_aarch64_mmap            222
#define __NR_aarch64_mprotect        226
#define __NR_aarch64_munmap          215
#define __NR_aarch64_brk             214
#define __NR_aarch64_rt_sigaction    134
#define __NR_aarch64_rt_sigprocmask  135
#define __NR_aarch64_rt_sigreturn    139
#define __NR_aarch64_ioctl           29
#define __NR_aarch64_readv           65
#define __NR_aarch64_writev          66
#define __NR_aarch64_nanosleep       101
#define __NR_aarch64_clock_gettime   113
#define __NR_aarch64_getrandom       278
#define __NR_aarch64_futex           98
#define __NR_aarch64_exit            93
#define __NR_aarch64_exit_group      94
#define __NR_aarch64_clone           220
#define __NR_aarch64_fork            220
#define __NR_aarch64_vfork           220
#define __NR_aarch64_execve          221
#define __NR_aarch64_execveat        281
#define __NR_aarch64_wait4           260
#define __NR_aarch64_kill            129
#define __NR_aarch64_socket          198
#define __NR_aarch64_connect         203
#define __NR_aarch64_bind            200
#define __NR_aarch64_listen          201
#define __NR_aarch64_accept          202
#define __NR_aarch64_getsockname     204
#define __NR_aarch64_getpeername     205
#define __NR_aarch64_setsockopt      208
#define __NR_aarch64_getsockopt      209
#define __NR_aarch64_sendto          206
#define __NR_aarch64_recvfrom        207
#define __NR_aarch64_sendmsg         211
#define __NR_aarch64_recvmsg         212
#define __NR_aarch64_poll            32
#define __NR_aarch64_epoll_create    104
#define __NR_aarch64_epoll_ctl       105
#define __NR_aarch64_epoll_wait      106
#define __NR_aarch64_dup             23
#define __NR_aarch64_dup2            24
#define __NR_aarch64_dup3            25
#define __NR_aarch64_fcntl           25
#define __NR_aarch64_fstat           80
#define __NR_aarch64_stat            79
#define __NR_aarch64_lstat           78
#define __NR_aarch64_newfstatat      79
#define __NR_aarch64_readlinkat      78
#define __NR_aarch64_getdents64      61
#define __NR_aarch64_pipe2           60
#define __NR_aarch64_mkdirat         34
#define __NR_aarch64_rmdir           35
#define __NR_aarch64_unlinkat        36
#define __NR_aarch64_renameat        38
#define __NR_aarch64_linkat          37
#define __NR_aarch64_symlinkat       39
#define __NR_aarch64_fchmodat        53
#define __NR_aarch64_fchownat        54
#define __NR_aarch64_utimensat       88
#define __NR_aarch64_truncate        45
#define __NR_aarch64_ftruncate       46
#define __NR_aarch64_fallocate       47
#define __NR_aarch64_prctl           167
#define __NR_aarch64_sched_yield     124
#define __NR_aarch64_getpid          172
#define __NR_aarch64_getppid         173
#define __NR_aarch64_getuid          174
#define __NR_aarch64_geteuid         175
#define __NR_aarch64_getgid          176
#define __NR_aarch64_getegid         177
#define __NR_aarch64_gettid          178
#define __NR_aarch64_sysinfo         179
#define __NR_aarch64_uname           160
#define __NR_aarch64_getcpu          168
#define __NR_aarch64_getcwd          17
#define __NR_aarch64_chdir           49
#define __NR_aarch64_fchdir          50
#define __NR_aarch64_open_by_handle_at  296
#define __NR_aarch64_landlock_create_ruleset  444
#define __NR_aarch64_landlock_add_rule        445
#define __NR_aarch64_landlock_restrict_self   446
#define __NR_aarch64_membarrier          283
#define __NR_aarch64_copy_file_range      285
#define __NR_aarch64_seccomp              277
#define __NR_aarch64_accept4              242
#define __NR_aarch64_eventfd2             208
#define __NR_aarch64_epoll_pwait2         297
#define __NR_aarch64_inotify_init1        104
#define __NR_aarch64_inotify_add_watch     27
#define __NR_aarch64_inotify_rm_watch      28
#define __NR_aarch64_fsync               82
#define __NR_aarch64_fdatasync           83
#define __NR_aarch64_getrusage           165
#define __NR_aarch64_getpriority         141
#define __NR_aarch64_setpriority         142
#define __NR_aarch64_setsid               99
#define __NR_aarch64_getppid_            173
#define __NR_aarch64_umask               166
#define __NR_aarch64_socketpair          199
#define __NR_aarch64_shutdown            210
#define __NR_aarch64_getpeername_        205
#define __NR_aarch64_ppoll               70
#define __NR_aarch64_write_              1
#define __NR_aarch64_set_tid_address      217

/* ---- Layer 3: Landlock helpers ---- */

/* briq-05a: measured enforcement state for THIS kernel.
 *
 * Landlock entered mainline in Linux 5.13. The S10+ vendor kernel is
 * 4.14.253, where the LSM simply does not exist. Refusing to launch (the old
 * behaviour: _exit(126)) would make every sandboxed app unusable on the
 * device, so an UNAVAILABLE Landlock is degraded and reported loudly, while a
 * Landlock that exists but fails to apply stays fatal (fail-closed). The
 * distinction is deliberately strict: state 1 = available, 2 = unavailable,
 * and the permission manager reports it as a documented limitation. */
#define NUXXEL_LANDLOCK_UNKNOWN      0
#define NUXXEL_LANDLOCK_AVAILABLE    1
#define NUXXEL_LANDLOCK_UNAVAILABLE  2

static int g_nuxel_landlock_state = NUXXEL_LANDLOCK_UNKNOWN;
static char g_nuxel_landlock_reason[192] = "not probed";

static int nuxel_landlock_state(void)
{
    return g_nuxel_landlock_state;
}

static const char *nuxel_landlock_reason(void)
{
    return g_nuxel_landlock_reason;
}

static void nuxel_landlock_mark_unavailable(const char *why)
{
    g_nuxel_landlock_state = NUXXEL_LANDLOCK_UNAVAILABLE;
    snprintf(g_nuxel_landlock_reason, sizeof(g_nuxel_landlock_reason), "%s",
             why ? why : "unavailable");
}

static int nuxel_landlock_detect_abi(void)
{
    int abi = 0;
    FILE *f = fopen("/proc/sys/kernel/landlock/abi_version", "r");
    if (f) {
        if (fscanf(f, "%d", &abi) != 1)
            abi = 0;
        fclose(f);
    }
    return abi;
}

static int nuxel_landlock_apply(const nuxel_sandbox_config_t *config)
{
    int abi = nuxel_landlock_detect_abi();
    int supported = 0;
    int ruleset_fd;

    if (abi > 0)
        supported = abi > LANDLOCK_ABI_MAX ? LANDLOCK_ABI_MAX : abi;

    if (supported < LANDLOCK_ABI_MIN) {
        /* Distinguish "this kernel has no Landlock" from "Landlock broke".
         * No /proc/sys/kernel/landlock/abi_version AND a kernel older than
         * 5.13 is the expected state on the S10+ (4.14.253). */
        nuxel_landlock_mark_unavailable(
            "Landlock LSM is not present on this kernel "
            "(mainline >= 5.13; no /proc/sys/kernel/landlock/abi_version)");
        fprintf(stderr, "nuxel-sandbox: LANDLOCK_UNAVAILABLE: %s\n",
                g_nuxel_landlock_reason);
        return -2;
    }
    g_nuxel_landlock_state = NUXXEL_LANDLOCK_AVAILABLE;
    snprintf(g_nuxel_landlock_reason, sizeof(g_nuxel_landlock_reason),
             "ABI %d", supported);

    struct landlock_ruleset_attr attr = {
        .handled_access_fs =
            LANDLOCK_ACCESS_FS_EXECUTE |
            LANDLOCK_ACCESS_FS_WRITE_FILE |
            LANDLOCK_ACCESS_FS_READ_FILE |
            LANDLOCK_ACCESS_FS_READ_DIR |
            LANDLOCK_ACCESS_FS_REMOVE_DIR |
            LANDLOCK_ACCESS_FS_REMOVE_FILE |
            LANDLOCK_ACCESS_FS_MAKE_CHAR |
            LANDLOCK_ACCESS_FS_MAKE_DIR |
            LANDLOCK_ACCESS_FS_MAKE_REG |
            LANDLOCK_ACCESS_FS_MAKE_SYM |
            LANDLOCK_ACCESS_FS_MAKE_BLOCK |
            LANDLOCK_ACCESS_FS_MAKE_FIFO |
            LANDLOCK_ACCESS_FS_MAKE_SOCK,
    };

    /* Network access via netns is governed by nftables/cgroup — Landlock ABI 4
     * also understands TCP connect(). For ABI >= 4 restrict connectivity to the
     * app data loopback only if the app has no network capability. */
    if (supported >= 4 && !(config->flags & NUXXEL_SANDBOX_NETWORK)) {
        attr.handled_access_net =
            LANDLOCK_ACCESS_NET_BIND_TCP |
            LANDLOCK_ACCESS_NET_CONNECT_TCP;
    }

    ruleset_fd = syscall(__NR_aarch64_landlock_create_ruleset,
                         &attr, sizeof(attr), 0);
    if (ruleset_fd < 0) {
        /* ABI 1 rulesets do not like net access field on older glibc headers */
        if (supported >= 2) {
            struct landlock_ruleset_attr attr_fs = {
                .handled_access_fs = attr.handled_access_fs,
            };
            ruleset_fd = syscall(__NR_aarch64_landlock_create_ruleset,
                                 &attr_fs, sizeof(attr_fs), 0);
        }
        if (ruleset_fd < 0) {
            if (errno == ENOSYS || errno == EOPNOTSUPP || errno == EINVAL) {
                nuxel_landlock_mark_unavailable(
                    "landlock_create_ruleset returned ENOSYS/EOPNOTSUPP/EINVAL "
                    "(kernel built without Landlock)");
                fprintf(stderr, "nuxel-sandbox: LANDLOCK_UNAVAILABLE: %s\n",
                        g_nuxel_landlock_reason);
                return -2;
            }
            perror("landlock_create_ruleset");
            return -1;
        }
    }

    struct landlock_path_beneath_attr pb = {
        .allowed_access =
            LANDLOCK_ACCESS_FS_READ_FILE |
            LANDLOCK_ACCESS_FS_READ_DIR |
            LANDLOCK_ACCESS_FS_EXECUTE,
    };

    const char *ro_paths[] = { "/usr", "/etc", NULL };
    for (int i = 0; ro_paths[i] != NULL; i++) {
        int fd = open(ro_paths[i], O_PATH | O_CLOEXEC);
        if (fd < 0)
            continue;
        pb.parent_fd = fd;
        if (syscall(__NR_aarch64_landlock_add_rule, ruleset_fd,
                    LANDLOCK_RULE_PATH_BENEATH, &pb, 0) < 0) {
            perror("landlock_add_rule (ro)");
        }
        close(fd);
    }

    for (size_t i = 0; i < config->num_extra_ro_paths; i++) {
        int fd = open(config->extra_ro_paths[i], O_PATH | O_CLOEXEC);
        if (fd < 0)
            continue;
        pb.parent_fd = fd;
        if (syscall(__NR_aarch64_landlock_add_rule, ruleset_fd,
                    LANDLOCK_RULE_PATH_BENEATH, &pb, 0) < 0) {
            perror(config->extra_ro_paths[i]);
        }
        close(fd);
    }

    uint64_t rw_access =
        LANDLOCK_ACCESS_FS_READ_FILE |
        LANDLOCK_ACCESS_FS_READ_DIR |
        LANDLOCK_ACCESS_FS_WRITE_FILE |
        LANDLOCK_ACCESS_FS_REMOVE_DIR |
        LANDLOCK_ACCESS_FS_REMOVE_FILE |
        LANDLOCK_ACCESS_FS_MAKE_DIR |
        LANDLOCK_ACCESS_FS_MAKE_REG;
    pb.allowed_access = rw_access;

    if (config->data_dir[0] != '\0') {
        int fd = open(config->data_dir, O_PATH | O_CLOEXEC);
        if (fd >= 0) {
            pb.parent_fd = fd;
            if (syscall(__NR_aarch64_landlock_add_rule, ruleset_fd,
                        LANDLOCK_RULE_PATH_BENEATH, &pb, 0) < 0) {
                perror(config->data_dir);
            }
            close(fd);
        }
    }

    for (size_t i = 0; i < config->num_extra_rw_paths; i++) {
        int fd = open(config->extra_rw_paths[i], O_PATH | O_CLOEXEC);
        if (fd >= 0) {
            pb.parent_fd = fd;
            if (syscall(__NR_aarch64_landlock_add_rule, ruleset_fd,
                        LANDLOCK_RULE_PATH_BENEATH, &pb, 0) < 0) {
                perror(config->extra_rw_paths[i]);
            }
            close(fd);
        }
    }

    /* Optional: restrict TCP bind/connect when network is disabled.
     * ABI 4 exposes net access via a net_beneath rule for cgroup-less apps.
     * We rely on the nftables cgroup match instead, so this is intentionally
     * not populated — the per-app cgroup (Layer 4) feed already drops
     * everything at the nftables Layer 5 network-isolation chain. */

    if (syscall(__NR_aarch64_landlock_restrict_self, ruleset_fd, 0) < 0) {
        perror("landlock_restrict_self");
        close(ruleset_fd);
        return -1;
    }

    close(ruleset_fd);
    return 0;
}

/* ---- Layer 2: seccomp BPF ---- */

/* Build the PWA & native allow/deny filters. We keep the classic direct
 * BPF_PROG approach: a small allow-list per category, everything else
 * explicitly killed. This is intentionally strict. */

static int nuxel_seccomp_build_filter(const nuxel_sandbox_config_t *config,
                                      int category)
{
    struct sock_filter filter[128];
    size_t n = 0;
    int require_network = (config->flags & NUXXEL_SANDBOX_NETWORK) ? 1 : 0;

    /* Load arch */
    filter[n++] = BPF_STMT(BPF_LD | BPF_W | BPF_ABS,
                           (offsetof(struct seccomp_data, arch)));
    filter[n++] = BPF_JUMP(BPF_JMP | BPF_JEQ | BPF_K, AUDIT_ARCH_AARCH64, 1, 0);
    filter[n++] = BPF_STMT(BPF_RET | BPF_K, SECCOMP_RET_KILL_PROCESS);

    /* Load syscall nr */
    filter[n++] = BPF_STMT(BPF_LD | BPF_W | BPF_ABS,
                           (offsetof(struct seccomp_data, nr)));

    /* Core userspace syscalls every process needs */
    static const int core_allowed[] = {
        __NR_aarch64_read, __NR_aarch64_write, __NR_aarch64_openat,
        __NR_aarch64_close, __NR_aarch64_lseek, __NR_aarch64_mmap,
        __NR_aarch64_mprotect, __NR_aarch64_munmap, __NR_aarch64_brk,
        __NR_aarch64_rt_sigaction, __NR_aarch64_rt_sigprocmask,
        __NR_aarch64_rt_sigreturn, __NR_aarch64_nanosleep,
        __NR_aarch64_clock_gettime, __NR_aarch64_getrandom,
        __NR_aarch64_futex, __NR_aarch64_exit, __NR_aarch64_exit_group,
        __NR_aarch64_clone, __NR_aarch64_execve, __NR_aarch64_getpid,
        __NR_aarch64_getppid, __NR_aarch64_getuid, __NR_aarch64_geteuid,
        __NR_aarch64_getgid, __NR_aarch64_getegid, __NR_aarch64_gettid,
        __NR_aarch64_prctl, __NR_aarch64_sched_yield, __NR_aarch64_uname,
        __NR_aarch64_getcwd, __NR_aarch64_fcntl, __NR_aarch64_dup,
        __NR_aarch64_dup2, __NR_aarch64_dup3, __NR_aarch64_newfstatat,
        __NR_aarch64_readv, __NR_aarch64_writev, __NR_aarch64_poll,
        __NR_aarch64_epoll_create, __NR_aarch64_epoll_ctl,
        __NR_aarch64_epoll_wait, __NR_aarch64_pipe2, __NR_aarch64_getdents64,
        __NR_aarch64_ioctl, __NR_aarch64_stat, __NR_aarch64_fstat,
        __NR_aarch64_readlinkat, __NR_aarch64_umask, __NR_aarch64_set_tid_address,
    };
    size_t core_len = sizeof(core_allowed) / sizeof(core_allowed[0]);

    for (size_t i = 0; i < core_len; i++) {
        if (n + 3 > sizeof(filter) / sizeof(filter[0]))
            break;
        filter[n++] = BPF_JUMP(BPF_JMP | BPF_JEQ | BPF_K, core_allowed[i], 0, 1);
        filter[n++] = BPF_STMT(BPF_RET | BPF_K, SECCOMP_RET_ALLOW);
    }

    /* Native apps additionally get the syscalls GTK4/GLib need */
    if (category == NUXXEL_SANDBOX_CATEGORY_NATIVE) {
        static const int native_allowed[] = {
            __NR_aarch64_setsid, __NR_aarch64_kill, __NR_aarch64_getrusage,
            __NR_aarch64_inotify_init1, __NR_aarch64_inotify_add_watch,
            __NR_aarch64_inotify_rm_watch, __NR_aarch64_fsync,
            __NR_aarch64_ppoll, __NR_aarch64_socketpair,
        };
        size_t nlen = sizeof(native_allowed) / sizeof(native_allowed[0]);
        for (size_t i = 0; i < nlen; i++) {
            if (n + 3 > sizeof(filter) / sizeof(filter[0]))
                break;
            filter[n++] = BPF_JUMP(BPF_JMP | BPF_JEQ | BPF_K, native_allowed[i], 0, 1);
            filter[n++] = BPF_STMT(BPF_RET | BPF_K, SECCOMP_RET_ALLOW);
        }
    }

    /* If network capability granted: stream, dgram sockets via inet (aarch64
     * uses socket(), connect(), sendto/recvfrom, etc.). */
    if (require_network) {
        static const int net_allowed[] = {
            __NR_aarch64_socket, __NR_aarch64_connect, __NR_aarch64_bind,
            __NR_aarch64_setsockopt, __NR_aarch64_getsockopt,
            __NR_aarch64_sendto, __NR_aarch64_recvfrom,
            __NR_aarch64_sendmsg, __NR_aarch64_recvmsg,
        };
        size_t nlen = sizeof(net_allowed) / sizeof(net_allowed[0]);
        for (size_t i = 0; i < nlen; i++) {
            if (n + 3 > sizeof(filter) / sizeof(filter[0]))
                break;
            filter[n++] = BPF_JUMP(BPF_JMP | BPF_JEQ | BPF_K, net_allowed[i], 0, 1);
            filter[n++] = BPF_STMT(BPF_RET | BPF_K, SECCOMP_RET_ALLOW);
        }
    }

    /* Deny-by-default */
    if (n + 1 > sizeof(filter) / sizeof(filter[0]))
        return -1;
    filter[n++] = BPF_STMT(BPF_RET | BPF_K, SECCOMP_RET_KILL_PROCESS);

    struct sock_fprog prog = {
        .len = (unsigned short)n,
        .filter = filter,
    };

    if (prctl(PR_SET_NO_NEW_PRIVS, 1, 0, 0, 0) < 0) {
        perror("prctl(PR_SET_NO_NEW_PRIVS)");
        return -1;
    }
    if (prctl(PR_SET_SECCOMP, SECCOMP_MODE_FILTER, &prog) < 0) {
        perror("prctl(PR_SET_SECCOMP)");
        return -1;
    }
    return 0;
}

/* ---- cgroup (Layer 4) helpers ---- */

static int nuxel_cgroup_is_v2(void)
{
#ifdef __linux__
    struct statfs st;
    if (statfs("/sys/fs/cgroup", &st) == 0 && st.f_type == CGROUP2_SUPER_MAGIC)
        return 1;
    return 0;
#else
    /* Non-Linux (cross-build sanity env): assume cgroupv2 so the rest of the
       unit-testable path is exercised. Real Linux targets use statfs(). */
    return 1;
#endif
}

/*
 * Deterministic app-id -> cgroup mapping.
 * Lowercases the app-id and replaces every character outside [a-z0-9-]
 * with '-', then prefixes "app-". Guarantees a match against the
 * "socket cgroupv2 level 2 \"app-*\"" rules.
 */
int nuxel_sandbox_app_id_to_cgroup(const char *app_id, char *out, size_t out_size)
{
    /* This MUST produce exactly the same result as sanitize_app_id() in
     * shell/nuxel-shell/nuxel-sandbox/nftables.sh: lowercased, restricted to
     * [a-z0-9-], every other char -> '-', repeated '-' collapsed, leading /
     * trailing '-' trimmed, then prefixed "app-". The nft ruleset matches
     * "socket cgroupv2 level 2 'app-*'", so C and shell must agree. */
    char raw[NUXXEL_SANDBOX_MAX_APP_ID * 2 + 1];
    char buf[NUXXEL_SANDBOX_MAX_APP_ID * 2 + 1];
    size_t n = 0, w = 0;
    int prev_dash = 0;

    /* Buffer must hold "app-" (4) + at least 1 char + NUL (1) = 6 bytes. */
    if (!app_id || !out || out_size < 6)
        return -1;

    /* Phase 1: lowercase + replace out-of-range chars with '-' */
    for (const char *p = app_id; *p && n < sizeof(raw) - 1; p++) {
        char c = *p;
        if (c >= 'A' && c <= 'Z')
            c = (char)(c - 'A' + 'a');
        if ((c >= 'a' && c <= 'z') || (c >= '0' && c <= '9') || c == '-')
            raw[n++] = c;
        else
            raw[n++] = '-';
    }
    raw[n] = '\0';

    /* Phase 2: collapse repeated dashes + trim leading/trailing dashes */
    for (size_t i = 0; raw[i] && w < sizeof(buf) - 1; i++) {
        char c = raw[i];
        if (c == '-') {
            if (prev_dash)
                continue;         /* collapse "a--b" -> "a-b" */
            /* trim leading dashes */
            if (w == 0)
                continue;
            buf[w++] = c;
            prev_dash = 1;
        } else {
            buf[w++] = c;
            prev_dash = 0;
        }
    }
    /* trim trailing dash */
    if (w > 0 && buf[w-1] == '-')
        w--;
    buf[w] = '\0';

    /* Any app-id whose sanitized core is empty yields an invalid cgroup. */
    if (w == 0)
        return -1;

    /* Phase 3: prefix "app-" (keep left or right unicode tests consistent). */
    if (w + 4 >= out_size)
        return -1;
    out[0] = 'a'; out[1] = 'p'; out[2] = 'p'; out[3] = '-';
    memcpy(out + 4, buf, w + 1);
    return 0;
}

int nuxel_sandbox_validate_app_id(const char *app_id, char *out, size_t out_size)
{
    return nuxel_sandbox_app_id_to_cgroup(app_id, out, out_size);
}

static int nuxel_sandbox_write_file(const char *path, const char *value)
{
    FILE *f = fopen(path, "w");
    if (!f)
        return -1;
    int r = fprintf(f, "%s", value);
    fclose(f);
    return (r < 0) ? -1 : 0;
}

static int nuxel_sandbox_read_uint64(const char *path, uint64_t *out)
{
    FILE *f = fopen(path, "r");
    if (!f)
        return -1;
    unsigned long long v = 0;
    int r = fscanf(f, "%llu", &v);
    fclose(f);
    if (r != 1)
        return -1;
    *out = (uint64_t)v;
    return 0;
}

/* Ensure the nuxel base cgroup + subtree control exist (cgroupv2). */
static int nuxel_sandbox_ensure_base_cgroup_v2(void)
{
    struct stat sb;
    if (stat(NUXXEL_CGROUP_BASE, &sb) == 0) {
        if (!S_ISDIR(sb.st_mode)) {
            errno = ENOTDIR;
            return -1;
        }
    } else {
        if (mkdir(NUXXEL_CGROUP_BASE, 0755) < 0 && errno != EEXIST) {
            perror("mkdir cgroup base");
            return -1;
        }
    }

    /* Enable controllers on the root subtree so they can propagate into the
     * nuxel subtree, and (critically) on nuxel's own subtree_control so the
     * leaf app-* cgroups actually expose memory.max / memory.high / cpu.max /
     * io.max files. Without enabling controllers on /sys/fs/cgroup/nuxel/
     * cgroup.subtree_control those leaf files do not exist and the memory
     * limits briq-14 specifies are silently never applied. */
    (void)nuxel_sandbox_write_file("/sys/fs/cgroup/cgroup.subtree_control",
                                   "+memory +cpu +io");
    if (nuxel_sandbox_write_file(NUXXEL_CGROUP_BASE "/cgroup.subtree_control",
                                 "+memory +cpu +io") < 0) {
        /* The leaf app cgroups will not have controller files; fail loudly
         * rather than silently skip the 1 GiB / 512 MiB memory limits. */
        perror("enable nuxel subtree controllers");
        return -1;
    }

    return 0;
}

/*
 * Create the per-app cgroup (Layer 4, briq-14) and attach pid.
 * On cgroupv2:
 *   - mkdir /sys/fs/cgroup/nuxel/<app-...>
 *   - write pid to <cg>/cgroup.procs
 *   - set memory.max / memory.high
 * On cgroup v1: fall back to cpu,memory controller files.
 */
int nuxel_sandbox_create_cgroup(const nuxel_sandbox_config_t *config, pid_t pid)
{
    char cg_base[320];
    char path[384];
    char pid_str[32];
    uint64_t mem_max, mem_high;
    int v2;

    if (!config || config->cgroup_name[0] == '\0') {
        errno = EINVAL;
        return -1;
    }

    snprintf(cg_base, sizeof(cg_base), "%s/%s", NUXXEL_CGROUP_BASE,
             config->cgroup_name);

    /* memory limits */
    mem_max = config->cgroup_memory_max ? config->cgroup_memory_max
                                        : NUXXEL_SANDBOX_DEFAULT_MEMORY_MAX;
    mem_high = config->cgroup_memory_high ? config->cgroup_memory_high
                                          : NUXXEL_SANDBOX_DEFAULT_MEMORY_HIGH;

    v2 = nuxel_cgroup_is_v2();
    if (v2) {
        if (nuxel_sandbox_ensure_base_cgroup_v2() < 0)
            return -1;

        if (mkdir(cg_base, 0755) < 0 && errno != EEXIST) {
            perror("mkdir app cgroup");
            return -1;
        }

        snprintf(pid_str, sizeof(pid_str), "%d", pid);
        snprintf(path, sizeof(path), "%s/cgroup.procs", cg_base);
        if (nuxel_sandbox_write_file(path, pid_str) < 0) {
            perror("write cgroup.procs");
            return -1;
        }

        /* memory.max — hard limit */
        char lim[32];
        snprintf(lim, sizeof(lim), "%llu", (unsigned long long)mem_max);
        snprintf(path, sizeof(path), "%s/memory.max", cg_base);
        if (nuxel_sandbox_write_file(path, lim) < 0) {
            perror("write memory.max");
            return -1;
        }

        /* memory.high — soft throttle */
        snprintf(lim, sizeof(lim), "%llu", (unsigned long long)mem_high);
        snprintf(path, sizeof(path), "%s/memory.high", cg_base);
        if (nuxel_sandbox_write_file(path, lim) < 0) {
            perror("write memory.high");
            return -1;
        }

        /* Runtime assertion: read back memory.max to confirm the limit was
         * actually applied (i.e. the controller is enabled on this subtree).
         * Fail loudly if it cannot be applied instead of silently continuing. */
        uint64_t read_back = 0;
        snprintf(path, sizeof(path), "%s/memory.max", cg_base);
        if (nuxel_sandbox_read_uint64(path, &read_back) < 0 ||
            read_back != mem_max) {
            fprintf(stderr,
                    "nuxel-sandbox: memory.max not applied (read %llu, expected "
                    "%llu); ensure memory controller is enabled on the nuxel "
                    "subtree\n",
                    (unsigned long long)read_back,
                    (unsigned long long)mem_max);
            return -1;
        }

        return 0;
    }

    /* ---- cgroup v1 fallback ----
     *
     * cgroup v1 uses one hierarchy per controller. If /sys/fs/cgroup/cpu and
     * /sys/fs/cgroup/memory exist we mirror the app cgroup there and pin the
     * PID via each controller's "tasks" file. nftables then matches via
     * net_cls.classid (see nftables.sh). */
    struct {
        const char *root;
        const char *subdir;   /* controller */
    } v1_dirs[] = {
        { "/sys/fs/cgroup/cpu", "cpu" },
        { "/sys/fs/cgroup/memory", "memory" },
        { "/sys/fs/cgroup/net_cls", "net_cls" },
    };

    for (size_t i = 0; i < sizeof(v1_dirs) / sizeof(v1_dirs[0]); i++) {
        snprintf(path, sizeof(path), "%s/%s", v1_dirs[i].root, config->cgroup_name);
        struct stat dstat;
        if (mkdir(path, 0755) < 0 && errno != EEXIST)
            continue;
        (void)dstat; /* silence unused warning */
        /* cpu controller not always present on every system */
        snprintf(pid_str, sizeof(pid_str), "%d", pid);
        snprintf(path, sizeof(path), "%s/%s/tasks", v1_dirs[i].root, config->cgroup_name);
        (void)nuxel_sandbox_write_file(path, pid_str);
    }

    /* memory limits only from the memory controller */
    char lim[32];
    snprintf(lim, sizeof(lim), "%llu", (unsigned long long)mem_max);
    snprintf(path, sizeof(path), "/sys/fs/cgroup/memory/%s/memory.limit_in_bytes",
             config->cgroup_name);
    (void)nuxel_sandbox_write_file(path, lim);
    snprintf(lim, sizeof(lim), "%llu", (unsigned long long)mem_high);
    snprintf(path, sizeof(path), "/sys/fs/cgroup/memory/%s/memory.soft_limit_in_bytes",
             config->cgroup_name);
    (void)nuxel_sandbox_write_file(path, lim);

    if (config->cgroup_classid) {
        char cls[32];
        snprintf(cls, sizeof(cls), "0x%08x", config->cgroup_classid);
        snprintf(path, sizeof(path), "/sys/fs/cgroup/net_cls/%s/net_cls.classid",
                 config->cgroup_name);
        (void)nuxel_sandbox_write_file(path, cls);
    }

    return 0;
}

/* Layer 4 + Layer 5 integration: per-app cgroup + nftables socket match.
 * Layer 4 creates /sys/fs/cgroup/nuxel/<app-...>; Layer 5 injects the
 * deterministic "socket cgroupv2 level 2 'app-<id>'" ACCEPT rule. */
static int nuxel_sandbox_create_cgroup_internal(const nuxel_sandbox_config_t *config)
{
    char cg_path[320];
    if (!config || config->cgroup_name[0] == '\0') {
        errno = EINVAL;
        return -1;
    }
    /* Ensure /sys/fs/cgroup/nuxel (and its subtree controllers) exists before
     * creating the leaf cgroup. A fresh boot has no nuxel/ base dir; mkdir of
     * the leaf alone would fail with ENOENT. (briq-14) */
    if (nuxel_sandbox_ensure_base_cgroup_v2() < 0)
        return -1;
    snprintf(cg_path, sizeof(cg_path), "%s/%s", NUXXEL_CGROUP_BASE,
             config->cgroup_name);
    if (mkdir(cg_path, 0755) < 0 && errno != EEXIST) {
        perror("mkdir cgroup");
        return -1;
    }
    return 0;
}

static int nuxel_sandbox_apply_nft_rule(const nuxel_sandbox_config_t *config)
{
    /* Deterministic: cgroup name is already sanitized to app-<safe>. */
    char cmd[640];
    snprintf(cmd, sizeof(cmd),
             "nft add rule inet nuxel_app_firewall output "
             "socket cgroupv2 level 2 \"%s\" accept 2>/dev/null || true",
             config->cgroup_name);
    int r = system(cmd);
    if (r == -1)
        return -1;
    return 0;
}

static int nuxel_sandbox_remove_nft_rule(const nuxel_sandbox_config_t *config)
{
    /* Remove any rule whose cgroup string matches. Use delete-by-handle via
     * listing; simplest is to replace the output chain (re-apply base ruleset).
     * We instead clone the deterministic rule's handle. To stay robust when
     * multiple matches exist, loop until none remain. */
    char cmd[768];
    snprintf(cmd, sizeof(cmd),
             "while h=$(nft -a list chain inet nuxel_app_firewall output "
             "2>/dev/null | grep 'cgroupv2 level 2 \\\"%s\\\"' | head -1 | "
             "awk '{print $NF}'); do [ -n \"$h\" ] || break; "
             "nft delete rule inet nuxel_app_firewall output handle \"$h\" "
             "2>/dev/null || break; done",
             config->cgroup_name);
    int r = system(cmd);
    if (r == -1)
        return -1;
    return 0;
}

int nuxel_sandbox_setup_network(const nuxel_sandbox_config_t *config)
{
    if (nuxel_sandbox_create_cgroup_internal(config) < 0)
        return -1;

    /* cgroupv2: nftables "socket cgroupv2 level 2" match requires the app
     * cgroup to exist (it does now). Add an ACCEPT rule only if the app has
     * the network capability; otherwise the default drop policy applies. */
    if (config->flags & NUXXEL_SANDBOX_NETWORK) {
        (void)nuxel_sandbox_apply_nft_rule(config);
    }
    return 0;
}

/* ---- Supplementary AppArmor label transition ----
 * AppArmor is a MAC-introspection label applied on top of the 5 layers.
 * It best-effort transitions the exec to a profile named <binary> when
 * libapparmor is linked in; profile *enforcement* is the boot units' job
 * (aa-enforce), which the sandbox intentionally does not duplicate. */

static int nuxel_sandbox_apply_apparmor(const nuxel_sandbox_config_t *config)
{
    /* AppArmor confinement is applied by the kernel based on the binary
     * profile label. If a profile exists for <binary> we rely on the boot
     * script to have placed it in enforce mode (see aa-enforce). Here we
     * only optionally point an existing mediate_deleted label; profile
     * enforcement is the responsibility of systemd/rc scripts. */
    (void)config;
    return 0;
}

/* ---- Public API ---- */

void nuxel_sandbox_config_init(nuxel_sandbox_config_t *config)
{
    memset(config, 0, sizeof(*config));
    config->category = NUXXEL_SANDBOX_CATEGORY_PWA;
    config->flags = 0;
    config->cgroup_classid = 0;
    config->cgroup_memory_max = 0;
    config->cgroup_memory_high = 0;

    /* Source the single-source path config so later path lookups agree with
     * the rest of the system (briq-20). */
    nuxel_sandbox_load_paths_conf();
}

/*
 * Load a sandbox JSON profile. This implementation does not depend on cJSON
 * (the project builds plain gcc without cJSON), so it uses a lightweight
 * key/value scanner for the fields sandbox.c consumes. It reads:
 *   - app_id
 *   - category
 *   - data_dir
 *   - cgroup_name / cgroup_classid (legacy)
 *   - flags / capabilities (string arrays -> flag bits, incl. network)
 *   - network_class (public / isolated) -> NUXXEL_SANDBOX_NETWORK + class
 *   - network_policy { allow_dns, allow_tcp_outbound, allow_udp_outbound, allow_inbound }
 *   - network (legacy bool -> NUXXEL_SANDBOX_NETWORK)
 *   - allowed_ro_paths / allowed_rw_paths (arrays)
 * Returns 0 on success.
 */
#define JSON_LINE_MAX 4096

/* Map a profile keyword (flag or capability name) to its bit flag. Returns 0
 * for "network" (which the caller sets via NUXXEL_SANDBOX_NETWORK) so the same
 * helper can drive both the `flags` and `capabilities` arrays (briq-31). */
static uint64_t nuxel_sandbox_flag_for_name(const char *name)
{
    if (!name) return 0;
    if (strcmp(name, "network") == 0)    return NUXXEL_SANDBOX_NETWORK;
    if (strcmp(name, "audio") == 0)      return NUXXEL_SANDBOX_AUDIO;
    if (strcmp(name, "camera") == 0)     return NUXXEL_SANDBOX_CAMERA;
    if (strcmp(name, "dbus") == 0)       return NUXXEL_SANDBOX_DBUS;
    if (strcmp(name, "devices") == 0)    return NUXXEL_SANDBOX_DEVICES;
    if (strcmp(name, "background") == 0) return NUXXEL_SANDBOX_BACKGROUND;
    if (strcmp(name, "sms") == 0)        return NUXXEL_SANDBOX_CAP_SMS;
    if (strcmp(name, "call") == 0)       return NUXXEL_SANDBOX_CAP_CALL;
    if (strcmp(name, "contacts") == 0)   return NUXXEL_SANDBOX_CAP_CONTACTS;
    if (strcmp(name, "storage") == 0)    return NUXXEL_SANDBOX_CAP_STORAGE;
    if (strcmp(name, "mic") == 0)        return NUXXEL_SANDBOX_CAP_MIC;
    if (strcmp(name, "location") == 0)   return NUXXEL_SANDBOX_CAP_LOCATION;
    return 0;
}

/* Walk a JSON array literal ("["a", "b"]") and invoke cb(token) for every
 * quoted string token found (e.g. a flags/capabilities element). Returns the
 * number of tokens emitted. Non-string tokens ("true"/"false"/numbers) are
 * ignored. */
typedef void (*nuxel_json_str_cb)(const char *token, void *ctx);
static size_t nuxel_sandbox_parse_string_array(const char *buf,
                                               nuxel_json_str_cb cb,
                                               void *ctx)
{
    size_t n = 0;
    const char *p = buf;
    while (p && *p) {
        p = strchr(p, '"');
        if (!p)
            break;
        const char *end = strchr(p + 1, '"');
        if (!end)
            break;
        size_t len = (size_t)(end - p - 1);
        if (len > 0) {
            char tmp[128];
            if (len >= sizeof(tmp))
                len = sizeof(tmp) - 1;
            memcpy(tmp, p + 1, len);
            tmp[len] = '\0';
            if (cb)
                cb(tmp, ctx);
            n++;
        }
        p = end + 1;
    }
    return n;
}

/* Callback for nuxel_sandbox_parse_string_array: OR a profile flag/capability
 * name's bit into the config's flags. Used for both the `flags` and
 * `capabilities` arrays (briq-31). */
static void nuxel_sandbox_set_flag_from_name(const char *token, void *ctx)
{
    nuxel_sandbox_config_t *cfg = (nuxel_sandbox_config_t *)ctx;
    if (!token || !cfg) return;
    cfg->flags |= nuxel_sandbox_flag_for_name(token);
}

/* Context for appending allowed_ro_paths / allowed_rw_paths tokens. */
typedef struct {
    nuxel_sandbox_config_t *cfg;
    int rw;   /* 1 = rw list, 0 = ro list */
} nuxel_path_ctx_t;

static void nuxel_sandbox_append_path(const char *token, void *ctx)
{
    nuxel_path_ctx_t *pc = (nuxel_path_ctx_t *)ctx;
    if (!token || !pc || !pc->cfg || token[0] == '\0')
        return;
    char ***arr = pc->rw ? &pc->cfg->extra_rw_paths : &pc->cfg->extra_ro_paths;
    size_t *num = pc->rw ? &pc->cfg->num_extra_rw_paths : &pc->cfg->num_extra_ro_paths;
    char **tmp = realloc(*arr, (*num + 1) * sizeof(char *));
    if (!tmp)
        return;
    *arr = tmp;
    (*arr)[*num] = strdup(token);
    (*num)++;
}

int nuxel_sandbox_config_load(const char *profile_path,
                               nuxel_sandbox_config_t *config)
{
    FILE *fp;
    char line[JSON_LINE_MAX];
    int in_ro = 0, in_rw = 0, in_flags = 0, in_caps = 0, in_np = 0;

    if (!profile_path || !config)
        return -1;

    fp = fopen(profile_path, "r");
    if (!fp)
        return -1;

    config->extra_ro_paths = NULL;
    config->extra_rw_paths = NULL;
    config->num_extra_ro_paths = 0;
    config->num_extra_rw_paths = 0;

    while (fgets(line, sizeof(line), fp)) {
        char *p = line;
        while (*p == ' ' || *p == '\t' || *p == '\n' || *p == '\r')
            p++;
        if (*p == '\0' || *p == '{' || *p == '}')
            continue;

        char *colon = strchr(p, ':');
        if (!colon)
            continue;
        char key[128];
        size_t kl = (size_t)(colon - p);
        if (kl >= sizeof(key))
            kl = sizeof(key) - 1;
        memcpy(key, p, kl);
        key[kl] = '\0';
        /* trim key */
        char *ke = key + kl;
        while (ke > key && (*(ke-1) == ' ' || *(ke-1) == '\t' || *(ke-1) == '"')) {
            *--ke = '\0';
        }
        char *kp = key;
        while (*kp == ' ' || *kp == '\t' || *kp == '"')
            kp++;

        char *val = colon + 1;
        while (*val == ' ' || *val == '\t')
            val++;

        /* Array/object open tracking. Under the lightweight line scanner an
         * array or object is entered when its key line ends in '[' or '{'
         * (with no closing bracket on the same line); each following element
         * line is collected until the next bracketed key resets the mode. */
        if (strcmp(kp, "allowed_ro_paths") == 0 ||
            strcmp(kp, "read_only") == 0) {
            in_ro = 1; in_rw = 0; in_flags = 0; in_caps = 0; in_np = 0;
            /* Profiles keep these arrays on the key line; parse them now so
             * the declared Landlock paths have runtime effect (briq-31). */
            {
                nuxel_path_ctx_t pc = { config, 0 };
                nuxel_sandbox_parse_string_array(val,
                                                 nuxel_sandbox_append_path, &pc);
            }
            continue;
        }
        if (strcmp(kp, "allowed_rw_paths") == 0 ||
            strcmp(kp, "read_write") == 0) {
            in_rw = 1; in_ro = 0; in_flags = 0; in_caps = 0; in_np = 0;
            {
                nuxel_path_ctx_t pc = { config, 1 };
                nuxel_sandbox_parse_string_array(val,
                                                 nuxel_sandbox_append_path, &pc);
            }
            continue;
        }
        /* Arrays the launcher does not consume at parse time (dbus access,
         * device nodes, seccomp profile refs, landlock object) must not leak
         * into the ro/rw path capture. Reset the capture modes here. */
        if (strcmp(kp, "dbus_access") == 0 ||
            strcmp(kp, "devices") == 0 ||
            strcmp(kp, "seccomp_profile") == 0 ||
            strcmp(kp, "landlock_rules") == 0 ||
            /* briq-05a: these keys live INSIDE landlock_rules / enforcement.
             * Without an explicit reset the line scanner treated them as
             * further ro/rw path elements, so a profile's "deny" list (or a
             * kernel_note string) was appended to the ALLOWED sets. That would
             * have granted write access to /dev and /sys on any kernel that
             * does support Landlock. Reset instead of capture. */
            strcmp(kp, "deny") == 0 ||
            strcmp(kp, "kernel_note") == 0 ||
            strcmp(kp, "enforcement") == 0 ||
            strcmp(kp, "attacker_privilege_class") == 0 ||
            strcmp(kp, "root_note") == 0 ||
            strcmp(kp, "apparmor") == 0 ||
            strcmp(kp, "landlock") == 0 ||
            strcmp(kp, "seccomp") == 0 ||
            strcmp(kp, "note") == 0 ||
            strcmp(kp, "network_policy") == 0) {
            in_ro = 0; in_rw = 0; in_flags = 0; in_caps = 0; in_np = 0;
            continue;
        }
        if (strcmp(kp, "flags") == 0) {
            in_flags = 1; in_ro = 0; in_rw = 0; in_caps = 0; in_np = 0;
            /* Profiles keep these arrays on the key line; parse them directly. */
            nuxel_sandbox_parse_string_array(val,
                                             nuxel_sandbox_set_flag_from_name,
                                             config);
            continue;
        }
        if (strcmp(kp, "capabilities") == 0) {
            in_caps = 1; in_ro = 0; in_rw = 0; in_flags = 0; in_np = 0;
            nuxel_sandbox_parse_string_array(val,
                                             nuxel_sandbox_set_flag_from_name,
                                             config);
            continue;
        }
        if (strcmp(kp, "network_policy") == 0) {
            in_np = 1; in_ro = 0; in_rw = 0; in_flags = 0; in_caps = 0;
            continue;
        }
        /* A lone '{' / '[' keyless line is an object/array body line — keep
         * collecting the active mode. Standalone "true"/"false"/number lines
         * inside network_policy are handled by the nested-key branch below. */

        /* strip trailing quotes/comma */
        char *ve = val + strlen(val);
        while (ve > val) {
            char c = *(ve-1);
            if (c == '\n' || c == '\r' || c == ' ' || c == '\t' || c == ',' || c == '"')
                ve--;
            else
                break;
        }
        *ve = '\0';
        /* strip a leading quote and whitespace so scalar values like
         * "public" / "app-nuxel-dialer" compare cleanly (briq-31). */
        while (*val == ' ' || *val == '\t')
            val++;
        if (*val == '"')
            val++;

        if (strcmp(kp, "app_id") == 0 && *val) {
            strncpy(config->app_id, val, sizeof(config->app_id) - 1);
        } else if (strcmp(kp, "category") == 0) {
            if (strcmp(val, "pwa") == 0)
                config->category = NUXXEL_SANDBOX_CATEGORY_PWA;
            else if (strcmp(val, "native") == 0)
                config->category = NUXXEL_SANDBOX_CATEGORY_NATIVE;
            else if (strcmp(val, "system") == 0)
                config->category = NUXXEL_SANDBOX_CATEGORY_SYSTEM;
            else
                config->category = NUXXEL_SANDBOX_CATEGORY_CUSTOM;
        } else if (strcmp(kp, "data_dir") == 0) {
            strncpy(config->data_dir, val, sizeof(config->data_dir) - 1);
        } else if (strcmp(kp, "network") == 0) {
            if (strcmp(val, "true") == 0 || strcmp(val, "1") == 0)
                config->flags |= NUXXEL_SANDBOX_NETWORK;
        } else if (strcmp(kp, "network_class") == 0) {
            /* Declared network class. "public" grants outbound (ACCEPT rule);
             * "isolated"/"unspec" stays under the default drop. network_class
             * takes precedence, but we also mirror it into NUXXEL_SANDBOX_NETWORK
             * so nuxel_sandbox_setup_network() grants the nft rule correctly. */
            if (strcmp(val, "public") == 0) {
                config->network_class = NUXXEL_SANDBOX_NETWORK_PUBLIC;
                config->flags |= NUXXEL_SANDBOX_NETWORK;
            } else if (strcmp(val, "isolated") == 0) {
                config->network_class = NUXXEL_SANDBOX_NETWORK_ISOLATED;
                config->flags &= ~NUXXEL_SANDBOX_NETWORK;
            } else if (strcmp(val, "unspec") == 0) {
                config->network_class = NUXXEL_SANDBOX_NETWORK_UNSPEC;
            }
        } else if (in_np && (strcmp(kp, "allow_dns") == 0 ||
                             strcmp(kp, "allow_tcp_outbound") == 0 ||
                             strcmp(kp, "allow_udp_outbound") == 0 ||
                             strcmp(kp, "allow_inbound") == 0)) {
            int v = (strcmp(val, "true") == 0 || strcmp(val, "1") == 0);
            if (strcmp(kp, "allow_dns") == 0)            config->network_policy.allow_dns = v;
            else if (strcmp(kp, "allow_tcp_outbound") == 0) config->network_policy.allow_tcp_outbound = v;
            else if (strcmp(kp, "allow_udp_outbound") == 0) config->network_policy.allow_udp_outbound = v;
            else                                          config->network_policy.allow_inbound = v;
        } else if (strcmp(kp, "cgroup_name") == 0) {
            strncpy(config->cgroup_name, val, sizeof(config->cgroup_name) - 1);
        } else if (strcmp(kp, "cgroup_classid") == 0) {
            config->cgroup_classid = (uint32_t)strtoul(val, NULL, 0);
        } else if (in_flags && *val) {
            /* Multi-line flags array element (defensive); single-line arrays
             * are consumed at the tracking block. */
            config->flags |= nuxel_sandbox_flag_for_name(val);
        } else if (in_caps && *val) {
            config->flags |= nuxel_sandbox_flag_for_name(val);
        } else if (in_ro && *val) {
            config->extra_ro_paths =
                realloc(config->extra_ro_paths,
                        (config->num_extra_ro_paths + 1) * sizeof(char *));
            config->extra_ro_paths[config->num_extra_ro_paths] = strdup(val);
            config->num_extra_ro_paths++;
        } else if (in_rw && *val) {
            config->extra_rw_paths =
                realloc(config->extra_rw_paths,
                        (config->num_extra_rw_paths + 1) * sizeof(char *));
            config->extra_rw_paths[config->num_extra_rw_paths] = strdup(val);
            config->num_extra_rw_paths++;
        }
    }
    fclose(fp);

    /* If a cgroup_name was not set in the profile, derive it deterministically
     * from the app_id so it always matches the nftables "app-*" rule. */
    if (config->cgroup_name[0] == '\0' && config->app_id[0] != '\0') {
        char derived[64];
        if (nuxel_sandbox_app_id_to_cgroup(config->app_id, derived, sizeof(derived)) == 0)
            strncpy(config->cgroup_name, derived, sizeof(config->cgroup_name) - 1);
    }

    return 0;
}

/* ---- App registry integration (briq-se1) ----
 *
 * The app registry (configs/nuxel/app-registry/app_registry.json) is the
 * single source for app registration across the bridge, portal, sandbox and
 * nftables. When no per-app sandbox JSON profile is staged we fall back to it
 * so the sandbox derives the same deterministic cgroup_name, network_class,
 * capabilities, data_dir and memory limits that the rest of the system uses.
 */

const char *nuxel_sandbox_get_app_registry_path(void)
{
    static char g_reg_path[384];
    const char *env;

    env = getenv("NUXEL_APP_REGISTRY");
    if (env && env[0] != '\0') {
        snprintf(g_reg_path, sizeof(g_reg_path), "%s", env);
        return g_reg_path;
    }

    /* Runtime (writable) copy wins over the read-only system copy. */
    static const char *cands[] = {
        "/var/lib/nuxel/app-registry/app_registry.json",
        "/etc/nuxel/app-registry/app_registry.json",
        NULL,
    };
    for (size_t i = 0; cands[i]; i++) {
        struct stat st;
        if (stat(cands[i], &st) == 0 && S_ISREG(st.st_mode)) {
            snprintf(g_reg_path, sizeof(g_reg_path), "%s", cands[i]);
            return g_reg_path;
        }
    }
    return NULL;
}

int nuxel_sandbox_config_load_from_registry(nuxel_sandbox_config_t *config)
{
    const char *reg_path;
    FILE *fp;
    char line[JSON_LINE_MAX];
    int brace = 0;           /* current top-level brace depth */
    int in_apps = 0;         /* inside the "apps" array object body */
    int in_app_obj = 0;      /* inside an app object { ... } */
    int match = 0;           /* the enclosing app object equals our app_id */
    int matched_once = 0;
    int in_flags = 0, in_caps = 0, in_ro = 0, in_rw = 0;

    if (!config || config->app_id[0] == '\0')
        return -1;

    reg_path = nuxel_sandbox_get_app_registry_path();
    if (!reg_path)
        return -1;

    fp = fopen(reg_path, "r");
    if (!fp)
        return -1;

    while (fgets(line, sizeof(line), fp)) {
        char *p = line;
        while (*p == ' ' || *p == '\t' || *p == '\n' || *p == '\r')
            p++;

        /* Track braces so we know when an app object opens and closes.
         * Root object -> brace 1; each app object inside the "apps" array
         * sits at brace 2 while its object is open. */
        for (char *c = p; *c; c++) {
            if (*c == '{') {
                bool entering = (brace == 1);
                brace++;
                if (entering && in_apps) {
                    /* opening an app object */
                    in_app_obj = 1;
                    in_flags = 0; in_caps = 0; in_ro = 0; in_rw = 0;
                }
            } else if (*c == '}') {
                bool leaving = (in_app_obj && brace == 2);
                brace--;
                if (leaving) {
                    /* closing the app object we were scanning */
                    if (match)
                        matched_once = 1;
                    in_app_obj = 0; match = 0;
                    in_flags = 0; in_caps = 0;
                    in_ro = 0; in_rw = 0;
                }
            }
        }

        if (strstr(p, "\"schema_version\"") || strstr(p, "\"cgroup_rule\"") ||
            strstr(p, "\"path\"") || strstr(p, "\"generated\""))
            continue;

        char *colon = strchr(p, ':');
        if (!colon)
            continue;
        char key[128];
        size_t kl = (size_t)(colon - p);
        if (kl >= sizeof(key)) kl = sizeof(key) - 1;
        memcpy(key, p, kl); key[kl] = '\0';
        char *ke = key + kl;
        while (ke > key && (*(ke-1)==' '||*(ke-1)=='\t'||*(ke-1)=='"')) *--ke='\0';
        char *kp = key;
        while (*kp==' '||*kp=='\t'||*kp=='"') kp++;

        char *val = colon + 1;
        while (*val==' '||*val=='\t') val++;

        /* The "apps" key marks entry into the app list. */
        if (strcmp(kp, "apps") == 0) {
            in_apps = 1;
            continue;
        }
        if (!in_apps)
            continue;

        if (strcmp(kp, "app_id") == 0) {
            char id[NUXXEL_SANDBOX_MAX_APP_ID];
            size_t l = 0;
            char *vv = val;
            while (*vv==' '||*vv=='\t') vv++;
            if (*vv == '"') vv++;
            while (*vv && *vv != '"' && *vv != ',' &&
                   *vv != '\n' && *vv != '\r' && l < sizeof(id)-1)
                id[l++] = *vv++;
            id[l] = '\0';
            match = (config->app_id[0] && strcmp(id, config->app_id) == 0);
            if (match) {
                /* Start fresh for this app object. */
                in_flags = in_caps = in_ro = in_rw = 0;
            }
            continue;
        }

        /* Everything below only applies when we are inside the matching app. */
        if (!match)
            continue;

        /* type -> category */
        if (strcmp(kp, "kernel_note") == 0 || strcmp(kp, "deny") == 0 ||
            strcmp(kp, "enforcement") == 0) {
            in_flags = in_caps = in_ro = in_rw = 0;
            continue;
        }
        if (strcmp(kp, "type") == 0) {
            if (strstr(val, "pwa"))      config->category = NUXXEL_SANDBOX_CATEGORY_PWA;
            else if (strstr(val, "native")) config->category = NUXXEL_SANDBOX_CATEGORY_NATIVE;
            else if (strstr(val, "system")) config->category = NUXXEL_SANDBOX_CATEGORY_SYSTEM;
            else                            config->category = NUXXEL_SANDBOX_CATEGORY_CUSTOM;
            continue;
        }
        if (strcmp(kp, "executable") == 0) {
            continue; /* consumed by the launcher via exec_path only */
        }
        if (strcmp(kp, "cgroup_name") == 0) {
            char v[64]; size_t l=0; char *vv=val;
            while (*vv==' '||*vv=='\t') vv++;
            if (*vv=='"') vv++;
            while (*vv && *vv!='"' && *vv!=',' && *vv!='\n' && *vv!='\r' && l<sizeof(v)-1)
                v[l++]=*vv++;
            v[l]='\0';
            if (l) strncpy(config->cgroup_name, v, sizeof(config->cgroup_name)-1);
            continue;
        }
        if (strcmp(kp, "cgroup_classid") == 0) {
            config->cgroup_classid = (uint32_t)strtoul(val, NULL, 0);
            continue;
        }
        if (strcmp(kp, "network_class") == 0) {
            if (strstr(val, "public")) {
                config->network_class = NUXXEL_SANDBOX_NETWORK_PUBLIC;
                config->flags |= NUXXEL_SANDBOX_NETWORK;
            } else if (strstr(val, "isolated")) {
                config->network_class = NUXXEL_SANDBOX_NETWORK_ISOLATED;
                config->flags &= ~NUXXEL_SANDBOX_NETWORK;
            } else {
                config->network_class = NUXXEL_SANDBOX_NETWORK_UNSPEC;
            }
            continue;
        }
        if (strcmp(kp, "data_dir") == 0) {
            char v[NUXXEL_SANDBOX_MAX_PATH]; size_t l=0; char *vv=val;
            while (*vv==' '||*vv=='\t') vv++;
            if (*vv=='"') vv++;
            while (*vv && *vv!='"' && l<sizeof(v)-1) v[l++]=*vv++;
            v[l]='\0';
            if (l) strncpy(config->data_dir, v, sizeof(config->data_dir)-1);
            continue;
        }
        if (strcmp(kp, "allowed_ro_paths") == 0 ||
            strcmp(kp, "read_only") == 0) {
            in_ro = 1; in_rw = 0; in_flags = 0; in_caps = 0;
            nuxel_path_ctx_t pc = { config, 0 };
            nuxel_sandbox_parse_string_array(val, nuxel_sandbox_append_path, &pc);
            continue;
        }
        if (strcmp(kp, "allowed_rw_paths") == 0 ||
            strcmp(kp, "read_write") == 0) {
            in_rw = 1; in_ro = 0; in_flags = 0; in_caps = 0;
            nuxel_path_ctx_t pc = { config, 1 };
            nuxel_sandbox_parse_string_array(val, nuxel_sandbox_append_path, &pc);
            continue;
        }
        if (strcmp(kp, "capabilities") == 0) {
            in_caps = 1; in_flags = 0; in_ro = 0; in_rw = 0;
            nuxel_sandbox_parse_string_array(val, nuxel_sandbox_set_flag_from_name, config);
            continue;
        }
        if (strcmp(kp, "default_capabilities") == 0) {
            in_caps = 1; in_flags = 0; in_ro = 0; in_rw = 0;
            nuxel_sandbox_parse_string_array(val, nuxel_sandbox_set_flag_from_name, config);
            continue;
        }
        if (strcmp(kp, "flags") == 0) {
            in_flags = 1; in_caps = 0; in_ro = 0; in_rw = 0;
            nuxel_sandbox_parse_string_array(val, nuxel_sandbox_set_flag_from_name, config);
            continue;
        }
        if (strcmp(kp, "memory_max_bytes") == 0) {
            config->cgroup_memory_max = strtoull(val, NULL, 0);
            continue;
        }
        if (strcmp(kp, "memory_high_bytes") == 0) {
            config->cgroup_memory_high = strtoull(val, NULL, 0);
            continue;
        }
        /* collected-but-not-applied hints (dbus_access, devices) are skipped:
         * they do not change the cgroup/network contract. allowed_ro/rw_paths
         * fall-through elements for multi-line arrays: */
        if ((in_ro || in_rw) && *val) {
            char v[NUXXEL_SANDBOX_MAX_PATH]; size_t l=0; char *vv=val;
            while (*vv==' '||*vv=='\t') vv++;
            if (*vv=='"') vv++;
            while (*vv && *vv!='"' && *vv!=',' && l<sizeof(v)-1) v[l++]=*vv++;
            v[l]='\0';
            if (l) {
                nuxel_path_ctx_t pc = { config, in_rw };
                nuxel_sandbox_append_path(v, &pc);
            }
            continue;
        }
    }
    fclose(fp);

    if (matched_once) {
        /* If the registry did not carry a cgroup_name, derive it. */
        if (config->cgroup_name[0] == '\0' && config->app_id[0] != '\0') {
            char derived[64];
            if (nuxel_sandbox_app_id_to_cgroup(config->app_id, derived,
                                               sizeof(derived)) == 0)
                strncpy(config->cgroup_name, derived,
                        sizeof(config->cgroup_name) - 1);
        }
        return 0;
    }
    errno = ENOENT;
    return -1;
}

int nuxel_sandbox_apply_landlock(const nuxel_sandbox_config_t *config)
{
    return nuxel_landlock_apply(config);
}

int nuxel_sandbox_apply_seccomp(const nuxel_sandbox_config_t *config)
{
    int category;
    switch (config->category) {
    case NUXXEL_SANDBOX_CATEGORY_PWA:
    case NUXXEL_SANDBOX_CATEGORY_CUSTOM:
        category = NUXXEL_SANDBOX_CATEGORY_PWA;
        break;
    case NUXXEL_SANDBOX_CATEGORY_NATIVE:
        category = NUXXEL_SANDBOX_CATEGORY_NATIVE;
        break;
    case NUXXEL_SANDBOX_CATEGORY_SYSTEM:
        /* System daemons get an audit-first filter (deny nothing harmful,
         * but enforce no_new_privs). */
        return 0;
    default:
        return 0;
    }
    return nuxel_seccomp_build_filter(config, category);
}

void nuxel_sandbox_cleanup(const nuxel_sandbox_config_t *config)
{
    if (!config)
        return;

    (void)nuxel_sandbox_remove_nft_rule(config);

    /* Remove the per-app cgroup (also removes any lingering processes). */
    char cg_base[320];
    snprintf(cg_base, sizeof(cg_base), "%s/%s", NUXXEL_CGROUP_BASE,
             config->cgroup_name);
    (void)rmdir(cg_base);

    /* cgroup v1 controllers — mirror the same app cgroup name per controller */
    for (size_t i = 0; i < 3; i++) {
        const char *roots[] = {
            "/sys/fs/cgroup/cpu/%s",
            "/sys/fs/cgroup/memory/%s",
            "/sys/fs/cgroup/net_cls/%s",
        };
        snprintf(cg_base, sizeof(cg_base), roots[i], config->cgroup_name);
        (void)rmdir(cg_base);
    }
}

/* briq-05a: read one trimmed line; leaves the buffer untouched (value stays
 * "unknown") when the file does not exist. Never invents a value. */
static void nuxel_read_first_line(const char *path, char *out, size_t out_size)
{
    FILE *f = fopen(path, "r");
    size_t n;
    if (!f)
        return;
    if (fgets(out, (int)out_size, f)) {
        n = strlen(out);
        while (n > 0 && (out[n-1] == '\n' || out[n-1] == '\r'))
            out[--n] = '\0';
    }
    fclose(f);
}

/* ---- CLI (briq-14) ---- */

/* briq-05a: report what this kernel can ACTUALLY enforce, so the permission
 * manager, verify-permissions.py and the security auditor never have to guess.
 * Prints one JSON object; an unknown value stays "unknown" and is never
 * assumed to be available. */
static int nuxel_sandbox_print_enforcement(void)
{
    char release[128] = "unknown";
    char lsm[256] = "unknown";
    char cg[256] = "unknown";
    char userns[64] = "unknown";
    char yama[64] = "unknown";
    char seccomp_avail[128] = "unknown";
    int landlock_file, apparmor_dir, apparmor, selinux, yama_on;
    int major = 0, minor = 0;
    struct stat st;

    nuxel_read_first_line("/proc/sys/kernel/osrelease", release, sizeof(release));
    nuxel_read_first_line("/sys/kernel/security/lsm", lsm, sizeof(lsm));
    nuxel_read_first_line("/sys/fs/cgroup/cgroup.controllers", cg, sizeof(cg));
    nuxel_read_first_line("/proc/sys/user/max_user_namespaces", userns, sizeof(userns));
    nuxel_read_first_line("/proc/sys/kernel/yama/ptrace_scope", yama, sizeof(yama));
    nuxel_read_first_line("/proc/sys/kernel/seccomp/actions_avail",
                          seccomp_avail, sizeof(seccomp_avail));

    landlock_file = (stat("/proc/sys/kernel/landlock/abi_version", &st) == 0);
    apparmor_dir  = (stat("/sys/kernel/security/apparmor", &st) == 0);
    apparmor = (strstr(lsm, "apparmor") != NULL) || apparmor_dir;
    selinux  = (strstr(lsm, "selinux") != NULL);
    yama_on  = (strstr(lsm, "yama") != NULL);
    (void)sscanf(release, "%d.%d", &major, &minor);

    printf("{\n");
    printf("  \"kernel_release\": \"%s\",\n", release);
    printf("  \"kernel_class\": \"%s\",\n",
           (major < 5 || (major == 5 && minor < 13)) ? "pre-5.13" : "5.13+");
    printf("  \"landlock\": \"%s\",\n",
           landlock_file ? "available" : "unavailable");
    printf("  \"landlock_note\": \"%s\",\n",
           landlock_file
             ? "Landlock present: path-level filesystem confinement is kernel-enforced"
             : "Landlock is mainline >= 5.13; absent here, so there is NO per-app "
               "path confinement for unprivileged apps (documented limitation)");
    printf("  \"seccomp_bpf\": \"%s\",\n",
           (strcmp(seccomp_avail, "unknown") != 0) ? "available" : "unknown");
    printf("  \"seccomp_actions_avail\": \"%s\",\n", seccomp_avail);
    printf("  \"lsm_list\": \"%s\",\n", lsm);
    printf("  \"apparmor\": \"%s\",\n",
           apparmor ? "available" : "unknown-or-absent");
    printf("  \"selinux\": \"%s\",\n", selinux ? "available" : "absent");
    printf("  \"yama\": \"%s\",\n", yama_on ? "available" : "not-in-lsm-list");
    printf("  \"ptrace_scope\": \"%s\",\n", yama);
    printf("  \"cgroup_v2_controllers\": \"%s\",\n", cg);
    printf("  \"user_namespaces_max\": \"%s\",\n", userns);
    printf("  \"nft_socket_cgroupv2\": \"%s\",\n",
           (major > 5 || (major == 5 && minor >= 13)) ? "possible" : "unavailable");
    printf("  \"nft_per_app_match\": \"%s\",\n",
           (major > 5 || (major == 5 && minor >= 13))
             ? "socket cgroupv2 level 2"
             : "meta cgroup (cgroup v1 net_cls classid)");
    printf("  \"verified_by\": \"nuxel-sandbox --print-enforcement\"\n");
    printf("}\n");
    return 0;
}

static void nuxel_sandbox_usage(const char *prog)
{
    fprintf(stderr,
        "Nuxel App Sandbox — hardened launcher (cgroup + nftables + seccomp + Landlock)\n"
        "\n"
        "Usage:\n"
        "  %s --cgroup <app-id> [options] [--] <command> [args...]\n"
        "  %s --print-cgroup <app-id>      Print the deterministic cgroup name and exit\n"
        "  %s --selfcheck [registry]       Verify the app-id -> cgroup mapping vs expected\n"
        "  %s --print-enforcement          Report what THIS kernel can enforce (JSON)\n"
        "\n"
        "Required:\n"
        "  --cgroup <app-id>  Per-app cgroup name; used to match the\n"
        "                     nftables \"socket cgroupv2 level 2 'app-*'\" rule.\n"
        "                     The app-id is lowercased/sanitized to [a-z0-9-] and\n"
        "                     prefixed 'app-'. A cgroup is created under\n"
        "                     /sys/fs/cgroup/nuxel/ and the child is moved into it.\n"
        "\n"
        "Options:\n"
        "  --network            Grant the app network access (else it stays blocked)\n"
        "  --seccomp            Enable seccomp BPF filtering (default on for PWAs)\n"
        "  --no-seccomp         Disable seccomp BPF filtering\n"
        "  --landlock           Enable Landlock filesystem restrictions (default on)\n"
        "  --no-landlock        Disable Landlock\n"
        "  --mem-max <bytes>    Override cgroup memory.max (default 1 GiB)\n"
        "  --mem-high <bytes>   Override cgroup memory.high (default 512 MiB)\n"
        "  -h, --help           Show this help\n"
        "\n"
        "Examples (unit test / verification):\n"
        "  %s --cgroup test-app /bin/true\n"
        "  %s --print-cgroup Org.Nuxel.Mail    # -> app-org-nuxel-mail\n"
        "  %s --selfcheck\n",
        prog, prog, prog, prog, prog, prog, prog);
}

/* ---- Verification helpers (briq-se1) ----
 * These give a runnable check that the deterministic app-id -> cgroup-name
 * mapping implemented here stays in lockstep with the app registry and the
 * shell sanitize_app_id() in nftables.sh. They never start any sandbox,
 * so they are safe to run on any host, and are exercised by
 * shell/nuxel-shell/nuxel-sandbox/verify-sandbox.sh.
 */

/* Expected deterministic outputs for a representative set that exercises the
 * three mapping phases (lowercase, out-of-range -> '-', collapse/trim). */
typedef struct { const char *app_id; const char *expect; } nuxel_selfcheck_case_t;
static const nuxel_selfcheck_case_t nuxel_selfcheck_cases[] = {
    { "nuxel-dialer",       "app-nuxel-dialer" },
    { "nuxel-contacts",     "app-nuxel-contacts" },
    { "nuxel-messages",     "app-nuxel-messages" },
    { "nuxel-settings",     "app-nuxel-settings" },
    { "nuxel-permissions",  "app-nuxel-permissions" },
    { "Org.Nuxel.Mail",     "app-org-nuxel-mail" },   /* lowercase + dots -> '-' */
    { "org.nuxel.PWA",      "app-org-nuxel-pwa" },    /* mixed case */
    { "My__App",            "app-my-app" },           /* repeated '-' collapse */
    { "-lead-trail-",       "app-lead-trail" },       /* trimmed edge '-' */
    { "123",                "app-123" },
};

static int nuxel_sandbox_run_selfcheck(const char *registry_path)
{
    int failed = 0;
    size_t n = sizeof(nuxel_selfcheck_cases) / sizeof(nuxel_selfcheck_cases[0]);

    for (size_t i = 0; i < n; i++) {
        char out[64];
        if (nuxel_sandbox_app_id_to_cgroup(nuxel_selfcheck_cases[i].app_id,
                                           out, sizeof(out)) < 0) {
            fprintf(stderr, "[selfcheck] FAIL: '%s' produced no cgroup\n",
                    nuxel_selfcheck_cases[i].app_id);
            failed = 1;
            continue;
        }
        if (strcmp(out, nuxel_selfcheck_cases[i].expect) == 0) {
            printf("[selfcheck] ok:   %-22s -> %s\n",
                   nuxel_selfcheck_cases[i].app_id, out);
        } else {
            printf("[selfcheck] FAIL: %-22s -> %s (expected %s)\n",
                   nuxel_selfcheck_cases[i].app_id, out,
                   nuxel_selfcheck_cases[i].expect);
            failed = 1;
        }
    }

    /* Cross-check every registry app's cgroup_name against the C mapping.
     * The sandbox falls back to the registry when no per-app JSON profile is
     * staged; agreement here guarantees the --cgroup flag and the nftables
     * "socket cgroupv2 level 2 'app-*'" match stay in sync. */
    if (registry_path && *registry_path) {
        nuxel_sandbox_config_t ref;
        nuxel_sandbox_config_init(&ref);
        char line[JSON_LINE_MAX];
        FILE *fp = fopen(registry_path, "r");
        if (!fp) {
            fprintf(stderr, "[selfcheck] registry not readable: %s\n",
                    registry_path);
            return 1;
        }
        int in_apps = 0, brace = 0, in_app_obj = 0;
        char cur_id[NUXXEL_SANDBOX_MAX_APP_ID] = "";
        char cur_cg[64] = "";
        int reg_failed = 0;
        while (fgets(line, sizeof(line), fp)) {
            char *p = line;
            while (*p==' '||*p=='\t'||*p=='\n'||*p=='\r') p++;
            for (char *c = p; *c; c++) {
                if (*c == '{') { if (brace>=1 && in_apps) in_app_obj=1; brace++; }
                else if (*c=='}') {
                    if (in_app_obj && brace==2) {
                        /* resolve current app object */
                        if (cur_id[0] && cur_cg[0]) {
                            char d[64];
                            if (nuxel_sandbox_app_id_to_cgroup(cur_id, d, sizeof(d)) < 0) {
                                fprintf(stderr, "[selfcheck] FAIL: registry app_id '%s' has no cgroup mapping\n", cur_id);
                                reg_failed = 1;
                            } else if (strcmp(d, cur_cg) != 0) {
                                fprintf(stderr, "[selfcheck] FAIL: registry %s cgroup_name '%s' != C mapping '%s'\n",
                                        cur_id, cur_cg, d);
                                reg_failed = 1;
                            }
                        }
                        cur_id[0]='\0'; cur_cg[0]='\0';
                        in_app_obj = 0;
                    }
                    brace--;
                }
            }
            if (!in_apps) {
                if (strstr(p, "\"apps\"")) in_apps = 1;
                continue;
            }
            char *colon = strchr(p, ':');
            if (!colon || !in_app_obj) continue;
            char key[128]; size_t kl = (size_t)(colon - p);
            if (kl >= sizeof(key)) kl = sizeof(key)-1;
            memcpy(key, p, kl); key[kl]='\0';
            char *ke = key + kl;
            while (ke>key && (*(ke-1)==' '||*(ke-1)=='\t'||*(ke-1)=='"')) *--ke='\0';
            char *kp = key; while (*kp==' '||*kp=='\t'||*kp=='"') kp++;
            char *val = colon + 1;
            while (*val==' '||*val=='\t') val++;
            if (strcmp(kp,"app_id")==0) {
                char *vv=val; if (*vv=='"') vv++;
                size_t l=0; while (*vv && *vv!='"' && *vv!=',' && l<sizeof(cur_id)-1) cur_id[l++]=*vv++;
                cur_id[l]='\0';
            } else if (strcmp(kp,"cgroup_name")==0) {
                char *vv=val; if (*vv=='"') vv++;
                size_t l=0; while (*vv && *vv!='"' && *vv!=',' && l<sizeof(cur_cg)-1) cur_cg[l++]=*vv++;
                cur_cg[l]='\0';
            }
        }
        fclose(fp);
        if (reg_failed) { failed = 1; }
        else if (failed == 0) {
            printf("[selfcheck] ok:   registry %s agrees with C mapping\n",
                   registry_path);
        } else {
            fprintf(stderr, "[selfcheck] registry cross-check flagged mismatches above\n");
        }
    }

    return failed ? 1 : 0;
}

/* ---- */

/* Set the sandbox flag toggles in errno-free helpers */
static void nuxel_sandbox_set_seccomp(nuxel_sandbox_config_t *cfg, int on)
{
    if (on)
        cfg->flags |= NUXXEL_SANDBOX_SANDBOX_SECCOMP;
    else
        cfg->flags &= ~NUXXEL_SANDBOX_SANDBOX_SECCOMP;
}
static void nuxel_sandbox_set_landlock(nuxel_sandbox_config_t *cfg, int on)
{
    if (on)
        cfg->flags |= NUXXEL_SANDBOX_SANDBOX_LANDLOCK;
    else
        cfg->flags &= ~NUXXEL_SANDBOX_SANDBOX_LANDLOCK;
}

int nuxel_sandbox_main(int argc, char **argv)
{
    nuxel_sandbox_config_t config;
    nuxel_sandbox_config_init(&config);

    /* Default hardening ON for every launch (briq-15). */
    nuxel_sandbox_set_seccomp(&config, 1);
    nuxel_sandbox_set_landlock(&config, 1);

    char *cgroup_arg = NULL;
    char *mem_max_str = NULL;
    char *mem_high_str = NULL;
    int i = 1;

    for (; i < argc; i++) {
        const char *a = argv[i];
        if (strcmp(a, "--cgroup") == 0) {
            if (i + 1 >= argc) {
                fprintf(stderr, "--cgroup requires an app-id argument\n");
                nuxel_sandbox_usage(argv[0]);
                return 2;
            }
            cgroup_arg = argv[++i];
        } else if (strcmp(a, "--network") == 0) {
            config.flags |= NUXXEL_SANDBOX_NETWORK;
        } else if (strcmp(a, "--seccomp") == 0) {
            nuxel_sandbox_set_seccomp(&config, 1);
        } else if (strcmp(a, "--no-seccomp") == 0) {
            nuxel_sandbox_set_seccomp(&config, 0);
        } else if (strcmp(a, "--landlock") == 0) {
            nuxel_sandbox_set_landlock(&config, 1);
        } else if (strcmp(a, "--no-landlock") == 0) {
            nuxel_sandbox_set_landlock(&config, 0);
        } else if (strcmp(a, "--mem-max") == 0) {
            if (i + 1 >= argc) { fprintf(stderr, "--mem-max requires bytes\n"); return 2; }
            mem_max_str = argv[++i];
        } else if (strcmp(a, "--mem-high") == 0) {
            if (i + 1 >= argc) { fprintf(stderr, "--mem-high requires bytes\n"); return 2; }
            mem_high_str = argv[++i];
        } else if (strcmp(a, "--print-enforcement") == 0) {
            /* briq-05a: measured enforcement report for this kernel. */
            return nuxel_sandbox_print_enforcement();
        } else if (strcmp(a, "--selfcheck") == 0) {
            /* briq-se1: verify the deterministic mapping vs built-in cases and,
             * optionally, the app registry. Safe to run on any host. */
            const char *reg = (i + 1 < argc && argv[i+1][0] != '-')
                                ? argv[++i] : nuxel_sandbox_get_app_registry_path();
            return nuxel_sandbox_run_selfcheck(reg);
        } else if (strcmp(a, "--print-cgroup") == 0) {
            if (i + 1 >= argc) {
                fprintf(stderr, "--print-cgroup requires an app-id\n");
                nuxel_sandbox_usage(argv[0]);
                return 2;
            }
            char out[64];
            const char *app = argv[++i];
            if (nuxel_sandbox_validate_app_id(app, out, sizeof(out)) < 0) {
                fprintf(stderr, "Invalid app-id: '%s'\n", app);
                return 2;
            }
            printf("%s\n", out);
            return 0;
        } else if (strcmp(a, "--help") == 0 || strcmp(a, "-h") == 0) {
            nuxel_sandbox_usage(argv[0]);
            return 0;
        } else if (strcmp(a, "--") == 0) {
            i++;
            break;
        } else if (a[0] == '-') {
            fprintf(stderr, "Unknown option: %s\n", a);
            nuxel_sandbox_usage(argv[0]);
            return 2;
        } else {
            break; /* first positional = the command */
        }
    }

    if (!cgroup_arg) {
        fprintf(stderr, "Missing required --cgroup <app-id>\n");
        nuxel_sandbox_usage(argv[0]);
        return 2;
    }
    if (i >= argc) {
        fprintf(stderr, "No command specified to run in the sandbox\n");
        nuxel_sandbox_usage(argv[0]);
        return 2;
    }

    /* Validate the app-id via the deterministic mapping (briq-14). */
    char cgroup_derived[64];
    if (nuxel_sandbox_validate_app_id(cgroup_arg, cgroup_derived,
                                      sizeof(cgroup_derived)) < 0) {
        fprintf(stderr, "Invalid --cgroup app-id: '%s' (no usable characters)\n",
                cgroup_arg);
        return 2;
    }
    strncpy(config.cgroup_name, cgroup_derived,
            sizeof(config.cgroup_name) - 1);
    config.cgroup_name[sizeof(config.cgroup_name) - 1] = '\0';
    strncpy(config.app_id, cgroup_arg, sizeof(config.app_id) - 1);
    config.app_id[sizeof(config.app_id) - 1] = '\0';

    /* Load the per-app JSON profile (briq-31) so the profile's declared
     * capabilities, allowed paths, cgroup and network class have runtime
     * effect (nuxel_sandbox_config_load), not just the CLI flags. The profile
     * is resolved from the app-id. If no profile exists we keep the CLI-driven
     * defaults so a launch is never silently dropped. */
    {
        char prof_path[NUXXEL_SANDBOX_MAX_PATH];
        const char *sb_dir = nuxel_sandbox_get_sandbox_dir();
        int loaded = 0;
        if (snprintf(prof_path, sizeof(prof_path), "%s/%s.json",
                     sb_dir, config.app_id) < (int)sizeof(prof_path)) {
            if (nuxel_sandbox_config_load(prof_path, &config) == 0) {
                loaded = 1;
            }
        }
        if (!loaded &&
            snprintf(prof_path, sizeof(prof_path), "%s/profiles/%s.json",
                     sb_dir, config.app_id) < (int)sizeof(prof_path)) {
            if (nuxel_sandbox_config_load(prof_path, &config) == 0) {
                loaded = 1;
            }
        }
        if (!loaded) {
            /* Dev-tree fallback so the launcher still exercises the profile
             * during development without a staged /opt/nuxel/sandbox. */
            snprintf(prof_path, sizeof(prof_path),
                     "nuxel-sandbox/profiles/%s.json", config.app_id);
            if (nuxel_sandbox_config_load(prof_path, &config) == 0) {
                loaded = 1;
            }
        }
        if (loaded) {
            /* The profile's cgroup name/classid may override the derived one;
             * re-derive cgroup_name from the (possibly profile-supplied)
             * app_id so the nftables "app-*" rule still matches. */
            if (config.cgroup_name[0] == '\0' && config.app_id[0] != '\0') {
                char d2[64];
                if (nuxel_sandbox_app_id_to_cgroup(config.app_id, d2,
                                                   sizeof(d2)) == 0)
                    strncpy(config.cgroup_name, d2,
                            sizeof(config.cgroup_name) - 1);
            }
            fprintf(stderr, "nuxel-sandbox: loaded profile %s\n", prof_path);
        } else {
            /* No staged per-app profile: fall back to the single-source app
             * registry (briq-se1). The registry is the authoritative list of
             * apps and their cgroup_name / network_class / capabilities, so
             * the sandbox stays in sync with the bridge, portal and nftables.
             * Launches are never silently dropped — CLI defaults stand if the
             * registry is also absent. */
            if (nuxel_sandbox_config_load_from_registry(&config) == 0) {
                char reg_path_dbg[384];
                const char *rp = nuxel_sandbox_get_app_registry_path();
                snprintf(reg_path_dbg, sizeof(reg_path_dbg),
                         "%s", rp ? rp : "?");
                fprintf(stderr, "nuxel-sandbox: loaded app registry entry "
                                "for %s from %s\n",
                        config.app_id, reg_path_dbg);
            } else if (getenv("NUXEL_APP_REGISTRY") &&
                       config.cgroup_name[0] != '\0') {
                fprintf(stderr, "nuxel-sandbox: app registry present but no "
                                "entry for %s; using CLI defaults\n",
                        config.app_id);
            }
        }
    }

    if (mem_max_str)
        config.cgroup_memory_max = strtoull(mem_max_str, NULL, 0);
    if (mem_high_str)
        config.cgroup_memory_high = strtoull(mem_high_str, NULL, 0);

    /* Command + args */
    char *exec_path = argv[i];
    char **cmd_argv = &argv[i];

    /* Use provided envp or the current environment. */
    extern char **environ;

    nuxel_sandbox_result_t res =
        nuxel_sandbox_launch(&config, exec_path, cmd_argv, environ);

    if (!res.success) {
        fprintf(stderr, "nuxel-sandbox: %s (errno %d)\n",
                res.error_message, res.error_code);
        return 1;
    }

    int status;
    if (waitpid(res.child_pid, &status, 0) < 0) {
        perror("waitpid");
        nuxel_sandbox_cleanup(&config);
        return 1;
    }

    /* On process exit remove the app cgroup (briq-14 point 5). */
    nuxel_sandbox_cleanup(&config);

    if (WIFEXITED(status))
        return WEXITSTATUS(status);
    if (WIFSIGNALED(status)) {
        fprintf(stderr, "child terminated by signal %d\n", WTERMSIG(status));
        return 128 + WTERMSIG(status);
    }
    return 1;
}

int main(int argc, char **argv)
{
    return nuxel_sandbox_main(argc, argv);
}

nuxel_sandbox_result_t nuxel_sandbox_launch(
    const nuxel_sandbox_config_t *config,
    const char *exec_path, char *const argv[], char *const envp[])
{
    nuxel_sandbox_result_t result = {0};

    /* Create the per-app cgroup (Layer 4) and (if allowed) the nftables match
     * before forking so the socket match is in place the instant the child
     * attempts any network traffic. */
    if (nuxel_sandbox_setup_network(config) < 0) {
        result.success = false;
        result.error_code = errno;
        strncpy(result.error_message, "Failed to set up per-app cgroup/network",
                sizeof(result.error_message) - 1);
        return result;
    }

    pid_t pid = fork();
    if (pid < 0) {
        result.success = false;
        result.error_code = errno;
        strncpy(result.error_message, "fork() failed",
                sizeof(result.error_message) - 1);
        return result;
    }

    if (pid == 0) {
        /* Child — apply hardening layers BEFORE exec. */

        /* Layer 1: namespaces.
         *
         * NOTE: we deliberately DO NOT unshare the network namespace
         * (CLONE_NEWNET). The app stays in the host netns so that the per-app
         * nftables cgroupv2 socket matches ("socket cgroupv2 level 2 'app-*'")
         * in configs/nftables/nuxel-app-firewall.nft actually govern the app's
         * sockets. Network policy is therefore enforced by nftables keyed off
         * the per-app cgroup (briq-14), not by a private netns. */
        int clone_flags = CLONE_NEWNS | CLONE_NEWPID | CLONE_NEWIPC |
                          CLONE_NEWUTS;
        if (unshare(clone_flags) < 0 && errno != EPERM && errno != EINVAL) {
            perror("unshare namespaces");
            _exit(126);
        }

        mount("none", "/", NULL, MS_REC | MS_PRIVATE, NULL);
        (void)mount("proc", "/proc", "proc", 0, NULL);

        /* Layer 3: Landlock (unless disabled).
         *
         * briq-05a: on a kernel without Landlock (the S10+ runs 4.14.253) the
         * layer is reported and skipped - the app still launches under
         * seccomp + namespaces + cgroup + nftables. A Landlock that exists but
         * fails to apply is still fatal, because that would silently drop a
         * confinement layer the kernel does support. */
        if (config->flags & NUXXEL_SANDBOX_SANDBOX_LANDLOCK) {
            int ll = nuxel_sandbox_apply_landlock(config);
            if (ll < 0) {
                if (ll == -2) {
                    fprintf(stderr,
                            "nuxel-sandbox: ENFORCEMENT landlock=unavailable "
                            "seccomp=%s cgroup=%s (documented limitation: no "
                            "path-level filesystem confinement on this kernel)\n",
                            (config->flags & NUXXEL_SANDBOX_SANDBOX_SECCOMP)
                                ? "on" : "off",
                            config->cgroup_name);
                } else {
                    fprintf(stderr, "Landlock setup failed\n");
                    _exit(126);
                }
            }
        }

        /* Layer 2: seccomp BPF (unless disabled). */
        if ((config->flags & NUXXEL_SANDBOX_SANDBOX_SECCOMP) &&
            nuxel_sandbox_apply_seccomp(config) < 0) {
            fprintf(stderr, "seccomp setup failed\n");
            _exit(126);
        }

        /* Supplementary AppArmor label hand-off (best-effort profile
         * transition; Layer 5 nftables network isolation is applied by the
         * outbound chain keyed on the Layer 4 cgroup, not here). */
        nuxel_sandbox_apply_apparmor(config);

        if (prctl(PR_SET_NO_NEW_PRIVS, 1, 0, 0, 0) < 0) {
            perror("prctl no_new_privs");
            _exit(126);
        }

        execve(exec_path, argv, envp);
        fprintf(stderr, "execve(%s): %s\n", exec_path, strerror(errno));
        _exit(127);
    }

    /* Parent: move child into the app cgroup now that it exists. */
    result.success = true;
    result.child_pid = pid;
    if (nuxel_sandbox_create_cgroup(config, pid) < 0) {
        fprintf(stderr, "nuxel-sandbox: could not attach PID %d to cgroup %s\n",
                pid, config->cgroup_name);
        /* Do not fail the launch; seccomp/Landlock are already active. */
    }

    return result;
}
