#ifndef NUXXEL_SANDBOX_H
#define NUXXEL_SANDBOX_H

/**
 * Nuxel App Sandbox - C library for creating hardened app sandboxes.
 *
 * Combines bubblewrap (namespace isolation) + seccomp BPF (syscall filter)
 * + Landlock (filesystem restrictions) into a unified API.
 *
 * Each app gets a 5-layer sandbox:
 *   1. Namespace isolation (bubblewrap/clone)
 *   2. Syscall filtering (seccomp BPF)
 *   3. Filesystem restriction (Landlock)
 *   4. Mandatory access control (AppArmor via kernel label)
 *   5. Network isolation (nftables cgroupv2 socket matching)
 *
 * Layer 5 relies on per-app cgroups created under /sys/fs/cgroup/nuxel/
 * with names prefixed "app-" so that the nftables ruleset in
 * configs/nftables/nuxel-app-firewall.nft can match them with
 * "socket cgroupv2 level 2 \"app-*\"". See briq-14.
 *
 * Target: aarch64 (mustang Pixel 10 Pro XL), Linux 6.12 LTS
 */

#include <stdint.h>
#include <stdbool.h>
#include <sys/types.h>

#ifdef __cplusplus
extern "C" {
#endif

/* Maximum app ID length */
#define NUXXEL_SANDBOX_MAX_APP_ID 128

/* Maximum profile path length */
#define NUXXEL_SANDBOX_MAX_PATH 4096

/* Sandbox flags */
#define NUXXEL_SANDBOX_NETWORK      (1 << 0)  /* Allow network access */
#define NUXXEL_SANDBOX_DBUS         (1 << 1)  /* Allow D-Bus access */
#define NUXXEL_SANDBOX_DEVICES      (1 << 2)  /* Allow device node access */
#define NUXXEL_SANDBOX_AUDIO        (1 << 3)  /* Allow PipeWire audio */
#define NUXXEL_SANDBOX_CAMERA       (1 << 4)  /* Allow camera access */
#define NUXXEL_SANDBOX_BACKGROUND   (1 << 5)  /* Allow background execution */

/* Per-app capability bits (briq-31). These mirror the capabilities declared in
 * each profile's `capabilities` array (network, sms, call, contacts, storage,
 * camera, mic, location) and give the sandbox runtime effect. Networking is
 * derived from NUXXEL_SANDBOX_NETWORK above. */
#define NUXXEL_SANDBOX_CAP_SMS       (1 << 16)  /* Send/receive SMS */
#define NUXXEL_SANDBOX_CAP_CALL      (1 << 17)  /* Place/receive calls */
#define NUXXEL_SANDBOX_CAP_CONTACTS  (1 << 18)  /* Access contacts */
#define NUXXEL_SANDBOX_CAP_STORAGE   (1 << 19)  /* App-scoped storage */
#define NUXXEL_SANDBOX_CAP_MIC       (1 << 20)  /* Microphone access */
#define NUXXEL_SANDBOX_CAP_LOCATION  (1 << 21)  /* Location access */

/* Network classes declared per profile. These map to whether the sandbox
 * grants the app network access (an nftables "socket cgroupv2" ACCEPT rule)
 * or leaves it isolated under the ruleset default drop policy. */
typedef enum {
    NUXXEL_SANDBOX_NETWORK_UNSPEC  = 0,   /* not declared; fall back to flags */
    NUXXEL_SANDBOX_NETWORK_ISOLATED,      /* no ACCEPT rule — default drop */
    NUXXEL_SANDBOX_NETWORK_PUBLIC,        /* ACCEPT rule — outbound allowed */
} nuxel_sandbox_network_class_t;

/* Per-app network policy (briq-31). Mirrors the profile's network_policy
 * object; 0 means "not declared". */
typedef struct {
    int allow_dns;          /* allow UDP/TCP :53 even when isolated */
    int allow_tcp_outbound; /* grant outbound TCP */
    int allow_udp_outbound; /* grant outbound UDP */
    int allow_inbound;      /* allow inbound connections */
} nuxel_sandbox_network_policy_t;

/* Sandbox hardening toggles (default ON for PWA launch) */
#define NUXXEL_SANDBOX_SANDBOX_SECCOMP  (1 << 8)  /* Enable seccomp BPF filter */
#define NUXXEL_SANDBOX_SANDBOX_LANDLOCK (1 << 9)  /* Enable Landlock restrictions */

/* Default cgroup memory limits (bytes) — memory.max / memory.high */
#define NUXXEL_SANDBOX_DEFAULT_MEMORY_MAX  (1024UL * 1024UL * 1024UL)      /* 1 GiB */
#define NUXXEL_SANDBOX_DEFAULT_MEMORY_HIGH (512UL  * 1024UL * 1024UL)      /* 512 MiB */

/* App categories for seccomp profiles */
typedef enum {
    NUXXEL_SANDBOX_CATEGORY_PWA,       /* Most restrictive - web apps */
    NUXXEL_SANDBOX_CATEGORY_NATIVE,    /* Standard native app */
    NUXXEL_SANDBOX_CATEGORY_SYSTEM,    /* System daemon - broad access */
    NUXXEL_SANDBOX_CATEGORY_CUSTOM,    /* Custom profile from JSON */
} nuxel_sandbox_category_t;

/* Sandbox configuration */
typedef struct {
    char app_id[NUXXEL_SANDBOX_MAX_APP_ID];      /* Application identifier */
    char data_dir[NUXXEL_SANDBOX_MAX_PATH];       /* App data directory */
    char profile_path[NUXXEL_SANDBOX_MAX_PATH];   /* Custom profile path */
    uint64_t flags;                                /* Sandbox flags */
    nuxel_sandbox_category_t category;             /* App category */
    nuxel_sandbox_network_class_t network_class;   /* Declared network class */

    /* Per-app network policy (briq-31) read from the profile. */
    nuxel_sandbox_network_policy_t network_policy;

    /* Per-app network cgroup (cgroupv2) */
    char cgroup_name[64];     /* sanitized: "app-" + lowercased alnum+'-' app_id */
    uint32_t cgroup_classid;  /* legacy net_cls classid for cgroup v1 fallback */

    /* cgroup memory limits (bytes). 0 = use defaults. */
    uint64_t cgroup_memory_max;
    uint64_t cgroup_memory_high;

    /* Additional Landlock allowed paths */
    char **extra_ro_paths;
    size_t num_extra_ro_paths;
    char **extra_rw_paths;
    size_t num_extra_rw_paths;

    /* Additional seccomp allowed syscalls */
    int *extra_syscalls;
    size_t num_extra_syscalls;
} nuxel_sandbox_config_t;

/* Sandbox execution result */
typedef struct {
    bool success;
    int error_code;
    char error_message[256];
    pid_t child_pid;
} nuxel_sandbox_result_t;

/**
 * Initialize a sandbox config with defaults.
 * Sets up the most restrictive configuration.
 */
void nuxel_sandbox_config_init(nuxel_sandbox_config_t *config);

/**
 * Deterministically map an app-id to the nftables cgroup path name.
 *
 * The app-id is lowercased and every character outside [a-z0-9-] is
 * replaced with '-', then prefixed with "app-". This guarantees the
 * cgroup name always matches the "socket cgroupv2 level 2 \"app-*\""
 * rule set in configs/nftables/nuxel-app-firewall.nft.
 *
 * Returns 0 on success, -1 if the resulting name would be empty.
 */
int nuxel_sandbox_app_id_to_cgroup(const char *app_id, char *out, size_t out_size);

/**
 * Validate a --cgroup <app-id> argument.
 * Applies the same sanitisation as nuxel_sandbox_app_id_to_cgroup.
 * Returns 0 if valid (writes sanitized name to out), -1 otherwise.
 */
int nuxel_sandbox_validate_app_id(const char *app_id, char *out, size_t out_size);

/**
 * Load sandbox config from a JSON profile.
 * Profiles are stored in sandbox/profiles/<app-id>.json
 */
int nuxel_sandbox_config_load(const char *profile_path,
                               nuxel_sandbox_config_t *config);

/**
 * Resolve the canonical app-registry path (briq-se1). Returns the NUXEL_APP_REGISTRY
 * environment variable if set; otherwise the runtime copy
 * /var/lib/nuxel/app-registry/app_registry.json if it exists; otherwise the
 * read-only system copy /etc/nuxel/app-registry/app_registry.json. Returns NULL
 * if neither exists. The returned pointer is only valid until the next call.
 */
const char *nuxel_sandbox_get_app_registry_path(void);

/**
 * Load sandbox config from the single-source app registry
 * (configs/nuxel/app-registry/app_registry.json on the build tree; resolved to
 * an absolute on-device path by nuxel_sandbox_get_app_registry_path). Looks up
 * the app object whose "app_id" equals config->app_id and fills cgroup_name,
 * network_class, capabilities, data_dir, dbus/devices hints and memory limits,
 * so the sandbox stays in sync with the bridge/portal/nftables on cgroup and
 * network-class for the sandbox, keeping it in sync with the
 * bridge/portal/nftables on cgroup and network-class. Returns 0 on success,
 * -1 if the registry or the app entry is unavailable.
 *
 * This is the profile FALLBACK when no per-app sandbox JSON profile is staged:
 * a staged profile (nuxel_sandbox_config_load) always takes precedence.
 */
int nuxel_sandbox_config_load_from_registry(nuxel_sandbox_config_t *config);

/**
 * Return the canonical sandbox runtime dir (NUXEL_SANDBOX_DIR,
 * default "/opt/nuxel/sandbox") resolved from /etc/nuxel/paths.conf.
 * Sandbox profiles are loaded from <sandbox-dir>/<app-id>.json.
 */
const char *nuxel_sandbox_get_sandbox_dir(void);

/**
 * Apply Landlock restrictions to the current process.
 * Must be called after fork() but before exec().
 */
int nuxel_sandbox_apply_landlock(const nuxel_sandbox_config_t *config);

/**
 * Apply seccomp BPF filter to the current process.
 * Must be called after fork() but before exec().
 */
int nuxel_sandbox_apply_seccomp(const nuxel_sandbox_config_t *config);

/**
 * Set up nftables rules for per-app network isolation.
 * Creates the per-app cgroup and, if network is allowed, the matching
 * nftables "socket cgroupv2" ACCEPT rule (deterministic app-id mapping).
 */
int nuxel_sandbox_setup_network(const nuxel_sandbox_config_t *config);

/**
 * Create the per-app cgroup (with delegation, memory limits) and attach
 * the given PID to it. Sets memory.max / memory.high on cgroupv2 and
 * falls back to cpu,memory controller files on cgroupv1.
 */
int nuxel_sandbox_create_cgroup(const nuxel_sandbox_config_t *config,
                                 pid_t pid);

/**
 * Remove the per-app nftables rule and cgroup.
 */
void nuxel_sandbox_cleanup(const nuxel_sandbox_config_t *config);

/**
 * Launch an app within the complete sandbox.
 * Forks, sets up namespaces, applies seccomp + Landlock (Layer 4 cgroup
 * attach), then exec()s the target binary.
 */
nuxel_sandbox_result_t nuxel_sandbox_launch(
    const nuxel_sandbox_config_t *config,
    const char *exec_path,
    char *const argv[],
    char *const envp[]);

/* ---- CLI (briq-14) ---- */

/**
 * Run the nuxel-sandbox command-line launcher.
 *
 * Usage:
 *   nuxel-sandbox --cgroup <app-id> [--network] [--no-seccomp] \
 *                 [--no-landlock] [--] <command> [args...]
 *
 * The required --cgroup flag names the per-app cgroup; the remaining
 * arguments are exec'd inside the hardened sandbox. See briq-14.
 */
int nuxel_sandbox_main(int argc, char **argv);

#ifdef __cplusplus
}
#endif

#endif /* NUXXEL_SANDBOX_H */
