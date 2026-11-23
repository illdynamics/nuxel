/*
 * rfs_policy.c — FAIL-CLOSED RFS path/access validator.
 * SPDX-License-Identifier: GPL-2.0-only
 *
 * See rfs_policy.h for the threat model. This implementation is deliberately
 * conservative and has no "default allow" anywhere.
 */
#include "rfs_policy.h"

#include <string.h>
#include <stdlib.h>
#include <stdio.h>
#include <unistd.h>
#include <limits.h>
#include <errno.h>

/* protected path prefixes — ANY match => immediate DENY. */
static const char *const PROTECTED_PREFIXES[] = {
    "/efs", "/efsg", "/sec_efs",       /* IMEI/NV/calibration stores */
    "/nv", "/nv_data", "/nvdata",
    "/calibration", "/calib",
    "/keys", "/keymaster", "/keystore",
    "/misc/wifi", /* not strictly modem, but never CP-writable */
    "/proc", "/sys", "/dev",            /* never expose kernel/device surfaces */
    "/data/vendor/radio",               /* carrier/subscriber identifiers */
    "/persist", "/pstore",
};

#define NPROT (sizeof(PROTECTED_PREFIXES) / sizeof(PROTECTED_PREFIXES[0]))

/* allowlist entry */
struct allow_entry {
    char path[RFS_MAX_PATH];
    bool allow_write;
};

static struct allow_entry g_allow[64];
static size_t g_nallow = 0;
static char g_root[PATH_MAX];   /* canonical root, empty => locked */
static int g_root_len = 0;

void rfs_policy_set_root(const char *root)
{
    char tmp[PATH_MAX];
    if (!root) { g_root[0] = '\0'; g_root_len = 0; return; }
    if (realpath(root, tmp) == NULL) { g_root[0] = '\0'; g_root_len = 0; return; }
    size_t n = strlen(tmp);
    if (n >= sizeof(g_root)) n = sizeof(g_root) - 1;
    memcpy(g_root, tmp, n); g_root[n] = '\0';
    g_root_len = (int)n;
}

void rfs_policy_clear_allowlist(void) { g_nallow = 0; }

int rfs_policy_allow(const char *relpath, bool allow_write)
{
    if (g_nallow >= 64) return -1;
    if (!relpath || relpath[0] == '\0') return -2;
    if (relpath[0] == '/') return -3;                 /* must be relative */
    if (strstr(relpath, "..")) return -4;             /* no traversal */
    if (strlen(relpath) >= RFS_MAX_PATH) return -5;
    strncpy(g_allow[g_nallow].path, relpath, RFS_MAX_PATH - 1);
    g_allow[g_nallow].path[RFS_MAX_PATH - 1] = '\0';
    g_allow[g_nallow].allow_write = allow_write;
    g_nallow++;
    return 0;
}

static bool has_dotdot(const char *s)
{
    return strstr(s, "..") != NULL;
}

static const char *const PROTECTED_COMPONENTS[] = {
    "efs", "efsg", "sec_efs", "nv", "nv_data", "nvdata",
    "calibration", "calib", "keys", "keymaster", "keystore",
    "radio", "persist", "pstore", "proc", "sys", "dev", "sbin", "boot",
};
#define NCOMP (sizeof(PROTECTED_COMPONENTS)/sizeof(PROTECTED_COMPONENTS[0]))

static bool component_is_protected(const char *comp)
{
    size_t i;
    for (i=0;i<NCOMP;i++)
        if (strcmp(comp, PROTECTED_COMPONENTS[i])==0) return true;
    return false;
}

static bool prefix_is_protected(const char *path)
{
    /* absolute-prefix form (path starts with /efs, /proc, ...) */
    size_t i;
    for (i = 0; i < NPROT; i++) {
        size_t n = strlen(PROTECTED_PREFIXES[i]);
        if (strncmp(path, PROTECTED_PREFIXES[i], n) == 0 &&
            (path[n] == '\0' || path[n] == '/'))
            return true;
    }
    /* component form: catch <anything>/efs/..., <anything>/proc/... etc. */
    {
        char buf[PATH_MAX];
        char *save = NULL, *tok;
        size_t plen = strlen(path);
        if (plen >= sizeof(buf)) return true;
        memcpy(buf, path, plen + 1);
        for (tok = strtok_r(buf, "/", &save); tok; tok = strtok_r(NULL, "/", &save)) {
            if (component_is_protected(tok)) return true;
        }
    }
    return false;
}

static bool allowlist_match(const char *rel)  /* rel = normalized path sans leading / */
{
    size_t i;
    for (i = 0; i < g_nallow; i++) {
        const char *e = g_allow[i].path;
        size_t elen = strlen(e);
        if (strncmp(rel, e, elen) == 0 &&
            (rel[elen] == '\0' || rel[elen] == '/' || e[elen-1] == '/')) {
            /* also require a DIRECT child match to prevent prefix abuse:
               rel == e  OR  rel starts with e + "/" */
            if (rel[elen] == '\0' || rel[elen] == '/')
                return true;
        }
    }
    return false;
}

static bool allowlist_writable(const char *rel)
{
    size_t i;
    for (i = 0; i < g_nallow; i++) {
        const char *e = g_allow[i].path;
        size_t elen = strlen(e);
        if (g_allow[i].allow_write &&
            strncmp(rel, e, elen) == 0 &&
            (rel[elen] == '\0' || rel[elen] == '/')) {
            return true;
        }
    }
    return false;
}

rfs_verdict rfs_policy_validate(const char *path, int op, bool want_write,
                                struct rfs_access *out)
{
    struct rfs_access a;
    char resolved[PATH_MAX];
    struct stat st;
    char rel[PATH_MAX];
    size_t rn;

    (void)op;
    memset(&a, 0, sizeof(a));
    if (out) memset(out, 0, sizeof(*out));

    /* 1. basic rejections */
    if (!path || path[0] == '\0') { a.deny_reason = RFS_DENY_EMPTY; goto deny; }
    if (strlen(path) >= RFS_MAX_PATH) { a.deny_reason = RFS_DENY_NAMING; goto deny; }
    if (path[0] == '/') { a.deny_reason = RFS_DENY_ABSOLUTE; goto deny; }
    if (has_dotdot(path)) { a.deny_reason = RFS_DENY_TRAVERSAL_DOTDOT; goto deny; }
    if (strchr(path, '\\')) { a.deny_reason = RFS_DENY_TRAVERSAL_OTHER; goto deny; }

    /* 2. root must be installed */
    if (g_root_len == 0) { a.deny_reason = RFS_DENY_ROOT_ESCAPE; goto deny; }

    /* 3. canonicalize via realpath of root + "/" + path */
    rn = (size_t)g_root_len;
    if (rn + 1 + strlen(path) + 1 > sizeof(rel)) {
        a.deny_reason = RFS_DENY_ROOT_ESCAPE; goto deny;
    }
    snprintf(rel, sizeof(rel), "%s/%s", g_root, path);
    if (realpath(rel, resolved) == NULL) {
        a.deny_reason = RFS_DENY_STAT_FAILED; goto deny;
    }

    /* 4. confine strictly inside root: resolved must equal root or root + "/..." */
    if (strncmp(resolved, g_root, (size_t)g_root_len) != 0) {
        a.deny_reason = RFS_DENY_ROOT_ESCAPE; goto deny;
    }
    if (resolved[g_root_len] != '\0' && resolved[g_root_len] != '/') {
        a.deny_reason = RFS_DENY_ROOT_ESCAPE; goto deny;
    }

    /* 5. protected prefixes */
    if (prefix_is_protected(resolved)) { a.deny_reason = RFS_DENY_PROTECTED_PREFIX; goto deny; }

    /* 6. stat for type checks (no follow once canonicalized) */
    if (lstat(resolved, &st) != 0) { a.deny_reason = RFS_DENY_STAT_FAILED; goto deny; }
    a.mode = (unsigned int)st.st_mode;

    if (S_ISLNK(st.st_mode)) { a.deny_reason = RFS_DENY_SYMLINK; goto deny; }
    if (st.st_nlink > 1 && S_ISREG(st.st_mode)) { a.deny_reason = RFS_DENY_HARDLINK; goto deny; }
    if (S_ISBLK(st.st_mode)) { a.deny_reason = RFS_DENY_BLOCK_DEV; goto deny; }
    if (S_ISCHR(st.st_mode)) { a.deny_reason = RFS_DENY_CHAR_DEV; goto deny; }
    if (!S_ISREG(st.st_mode) && !S_ISDIR(st.st_mode)) {
        a.deny_reason = RFS_DENY_OTHER_TYPE; goto deny;
    }

    /* 7. allowlist membership (relative to root) */
    {
        const char *relp = resolved + (size_t)g_root_len;
        if (*relp == '/') relp++;
        if (!allowlist_match(relp)) { a.deny_reason = RFS_DENY_NOT_ALLOWLISTED; goto deny; }
        a.is_allowlisted = true;
        /* write requires an allow_write entry AND a write request */
        if (want_write) {
            if (!allowlist_writable(relp)) { a.deny_reason = RFS_DENY_NOT_ALLOWLISTED; goto deny; }
            a.op = 1;
        } else {
            a.op = 0;
        }
    }

    strncpy(a.path, resolved, RFS_MAX_PATH - 1);
    a.path[RFS_MAX_PATH - 1] = '\0';
    a.deny_reason = RFS_OK;
    if (out) *out = a;
    return (want_write) ? RFS_ALLOW_WRITE : RFS_ALLOW_READ;

deny:
    /* never copy the input path into logs; only reason + mode */
    if (out) *out = a;
    return RFS_DENY;
}

const char *rfs_deny_reason_name(int reason)
{
    switch (reason) {
    case RFS_OK: return "OK";
    case RFS_DENY_NOT_ALLOWLISTED: return "NOT_ALLOWLISTED";
    case RFS_DENY_EMPTY: return "EMPTY";
    case RFS_DENY_ABSOLUTE: return "ABSOLUTE_PATH";
    case RFS_DENY_TRAVERSAL_DOTDOT: return "DOTDOT";
    case RFS_DENY_TRAVERSAL_OTHER: return "TRAVERSAL";
    case RFS_DENY_SYMLINK: return "SYMLINK";
    case RFS_DENY_HARDLINK: return "HARDLINK";
    case RFS_DENY_BLOCK_DEV: return "BLOCK_DEV";
    case RFS_DENY_CHAR_DEV: return "CHAR_DEV";
    case RFS_DENY_PROTECTED_PREFIX: return "PROTECTED_PREFIX";
    case RFS_DENY_ROOT_ESCAPE: return "ROOT_ESCAPE";
    case RFS_DENY_STAT_FAILED: return "STAT_FAILED";
    case RFS_DENY_OTHER_TYPE: return "OTHER_TYPE";
    case RFS_DENY_NAMING: return "BAD_NAME";
    default: return "UNKNOWN";
    }
}
