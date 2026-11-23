/*
 * rfs_policy.h — strict RFS filesystem-access security policy/validator.
 * SPDX-License-Identifier: GPL-2.0-only
 *
 * The Samsung S5000AP RFS channel (SIPC5_CH_ID_RFS_0=245, IPC_RFS) is a
 * transport for the modem to request filesystem/NV operations from the AP.
 * The KERNEL only carries the bytes; the RFS file operation protocol is
 * defined ENTIRELY by the closed Samsung userspace (rild / libsec-ril).
 *
 * Because the opcode semantics are classed UNKNOWN (see report §RFS), this
 * module does NOT implement any RFS opcode processor. It provides a
 * FAIL-CLOSED path/access validator that must front-end ANY hypothetical or
 * future RFS bridge so that no CP request can reach arbitrary host paths,
 * protected partitions, or secret stores.
 *
 * The default answer to every path is DENY. Only entries in an explicit
 * allowlist that are (a) relative, (b) normalized, (c) within a single
 * bounded root, (d) not symlink/hardlink/block/char devices, and (e) not
 * matching protected prefixes, are permitted — and even then only with
 * read-only default.
 */
#ifndef NUXEL_RFS_POLICY_H
#define NUXEL_RFS_POLICY_H

#include <stdint.h>
#include <stddef.h>
#include <stdbool.h>
#include <sys/types.h>
#include <sys/stat.h>

#ifdef __cplusplus
extern "C" {
#endif

#define RFS_MAX_PATH 512u

/* Result of an RFS path validation. */
typedef enum rfs_verdict {
    RFS_DENY = 0,        /* fail-closed: not on allowlist / unsafe */
    RFS_ALLOW_READ = 1,  /* safe for read-only */
    RFS_ALLOW_WRITE = 2, /* safe for read+write (subject to caller auth) */
} rfs_verdict;

/* A normalized access request. */
struct rfs_access {
    char  path[RFS_MAX_PATH];  /* normalized absolute path inside root */
    int   op;                  /* 0=read, 1=write (informational) */
    bool  is_allowlisted;      /* matched an explicit allowlist entry */
    int   deny_reason;         /* packed reason code (see below) */
    unsigned int mode;         /* st_mode if stat succeeded, else 0 */
};

/* deny reason codes (used for diagnostics/logging, never secrets) */
enum rfs_deny_reason {
    RFS_OK = 0,
    RFS_DENY_NOT_ALLOWLISTED = 1,
    RFS_DENY_EMPTY = 2,
    RFS_DENY_ABSOLUTE = 3,
    RFS_DENY_TRAVERSAL_DOTDOT = 4,
    RFS_DENY_TRAVERSAL_OTHER = 5,
    RFS_DENY_SYMLINK = 6,
    RFS_DENY_HARDLINK = 7,
    RFS_DENY_BLOCK_DEV = 8,
    RFS_DENY_CHAR_DEV = 9,
    RFS_DENY_PROTECTED_PREFIX = 10,
    RFS_DENY_ROOT_ESCAPE = 11,
    RFS_DENY_STAT_FAILED = 12,
    RFS_DENY_OTHER_TYPE = 13,
    RFS_DENY_NAMING = 14,
};

/*
 * Install/clear the canonical root for RFS access. `root` must be an
 * absolute path of an existing REAL directory (no trailing slash stored).
 * Any access is confined strictly inside this root by realpath(3) + prefix
 * membership. Passing NULL clears and re-locks everything (deny-all).
 */
void rfs_policy_set_root(const char *root);

/*
 * Add an explicit allowlist entry, relative to the RFS root.
 * `allow_write` selects read-only vs read+write. Entries are matched after
 * normalization; a directory entry authorizes everything beneath it.
 */
int rfs_policy_allow(const char *relpath, bool allow_write);

/* Reset the allowlist to empty (deny-all). */
void rfs_policy_clear_allowlist(void);

/*
 * Validate a proposed access. `path` is the (typically CP-supplied) path
 * string; `op` is 0=read,1=write; `want_write` is whether the caller is
 * attempting a write (even a read verdict on a write request is downgraded
 * to DENY). The function performs:
 *   - empty/absolute/dot-dot/backslash/symlink/hardlink/device rejection
 *   - realpath(3) canonicalization + strict root-prefix confinement
 *   - protected-prefix rejection (EFS, EFSG, SEC_EFS, NV, calibration,
 *     keys, carrier identifiers, block/char devices, /proc,/sys,/dev)
 *   - allowlist membership
 *   - read-only default (a write verdict requires both an allow_write entry
 *     and want_write, otherwise DENY)
 * Returns rfs_verdict. `out` (if non-NULL) receives detail.
 */
rfs_verdict rfs_policy_validate(const char *path, int op, bool want_write,
                                struct rfs_access *out);

/* Human-readable deny-reason name (for diagnostics). */
const char *rfs_deny_reason_name(int reason);

#ifdef __cplusplus
}
#endif

#endif /* NUXEL_RFS_POLICY_H */
