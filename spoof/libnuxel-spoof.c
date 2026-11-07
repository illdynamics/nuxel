/* libnuxel-spoof.c — aarch64 app-scoped LD_PRELOAD spoof library for Nuxel.
 *
 * Interposes only the identity-reading symbols apps actually use.  It is
 * recursion-safe via dlsym(RTLD_NEXT) + a thread-local guard, forwards
 * open()/openat() varargs correctly (mode_t only when O_CREAT is present),
 * and never applies globally: the launcher injects LD_PRELOAD only for
 * explicitly selected app launches.
 *
 * Config: NUXEL_SPOOF_PROFILE (default /run/nuxel/spoof/profile.json).
 *
 * Build (on-device aarch64):
 *   gcc -shared -fPIC -O2 -o libnuxel-spoof.so libnuxel-spoof.c -ldl
 */
#define _GNU_SOURCE
#include <stdarg.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <dlfcn.h>
#include <fcntl.h>
#include <sys/stat.h>
#include <sys/utsname.h>

static __thread int spoof_guard = 0;
static int spoof_ready = 0;
static char spoof_os_release[512] = "/run/nuxel/spoof/os-release";
static char spoof_sysname[256] = "Linux";
static char spoof_nodename[256] = "nuxel-spoof";
static char spoof_release[256] = "6.1.0-nuxel-spoof";
static char spoof_version[256] = "#1 SMP PREEMPT_DYNAMIC";
static char spoof_machine[256] = "aarch64";

static void spoof_load(void) {
    if (spoof_ready) return;
    spoof_ready = 1;
    spoof_guard = 1;  /* the loader must not recurse through interposed fopen */
    const char *profile = getenv("NUXEL_SPOOF_PROFILE");
    if (!profile || !*profile) profile = "/run/nuxel/spoof/profile.json";
    FILE *f = fopen(profile, "r");
    if (!f) { spoof_guard = 0; return; }
    char *buf = malloc(16384);
    if (!buf) { fclose(f); spoof_guard = 0; return; }
    size_t n = fread(buf, 1, 16383, f);
    buf[n] = '\0';
    fclose(f);

    const char *keys[] = { "\"os_release\"", "\"sysname\"", "\"nodename\"",
                           "\"release\"", "\"version\"", "\"machine\"" };
    char *dsts[] = { spoof_os_release, spoof_sysname, spoof_nodename,
                     spoof_release, spoof_version, spoof_machine };
    size_t caps[] = { sizeof(spoof_os_release), sizeof(spoof_sysname),
                      sizeof(spoof_nodename), sizeof(spoof_release),
                      sizeof(spoof_version), sizeof(spoof_machine) };
    for (int i = 0; i < 6; i++) {
        const char *k = strstr(buf, keys[i]);
        if (!k) continue;
        const char *q = strchr(k + 1, '"');
        if (!q) continue;
        q = strchr(q + 1, '"');
        if (!q) continue;
        const char *v1 = q + 1;
        const char *v2 = strchr(v1, '"');
        if (!v2) continue;
        size_t len = (size_t)(v2 - v1);
        if (len >= caps[i]) len = caps[i] - 1;
        memcpy(dsts[i], v1, len);
        dsts[i][len] = '\0';
    }
    free(buf);
    spoof_guard = 0;
}

static const char *redirect_os_release(const char *path) {
    if (spoof_guard || !path) return NULL;
    spoof_load();
    if (spoof_guard) return NULL;
    return strcmp(path, "/etc/os-release") == 0 ? spoof_os_release : NULL;
}

/* ---- uname ----------------------------------------------------------- */
typedef int (*uname_fn)(struct utsname *);
int uname(struct utsname *buf) {
    static uname_fn real_uname = NULL;
    if (!real_uname) real_uname = (uname_fn)dlsym(RTLD_NEXT, "uname");
    if (!real_uname || !buf) return -1;
    int rc = real_uname(buf);
    if (spoof_guard) return rc;
    spoof_load();
    snprintf(buf->sysname, sizeof(buf->sysname), "%s", spoof_sysname);
    snprintf(buf->nodename, sizeof(buf->nodename), "%s", spoof_nodename);
    snprintf(buf->release, sizeof(buf->release), "%s", spoof_release);
    snprintf(buf->version, sizeof(buf->version), "%s", spoof_version);
    snprintf(buf->machine, sizeof(buf->machine), "%s", spoof_machine);
    return rc;
}

/* ---- fopen / fopen64 -------------------------------------------------- */
typedef FILE *(*fopen_fn)(const char *, const char *);
static FILE *spoof_fopen(const char *path, const char *mode) {
    static fopen_fn real_fopen = NULL;
    if (!real_fopen) real_fopen = (fopen_fn)dlsym(RTLD_NEXT, "fopen");
    if (!real_fopen) return NULL;
    const char *redirect = redirect_os_release(path);
    spoof_guard = 1;
    FILE *out = real_fopen(redirect ? redirect : path, mode);
    spoof_guard = 0;
    return out;
}
FILE *fopen(const char *path, const char *mode) { return spoof_fopen(path, mode); }
FILE *fopen64(const char *path, const char *mode) { return spoof_fopen(path, mode); }

/* ---- open / open64 / openat / openat64 (varargs handled correctly) ----- */
typedef int (*open_fn)(const char *, int, ...);
typedef int (*openat_fn)(int, const char *, int, ...);
static int spoof_open(const char *path, int flags, mode_t mode, int has_mode) {
    static open_fn real_open = NULL;
    if (!real_open) real_open = (open_fn)dlsym(RTLD_NEXT, "open");
    if (!real_open) return -1;
    const char *redirect = redirect_os_release(path);
    const char *use_path = redirect ? redirect : path;
    spoof_guard = 1;
    int rc = has_mode ? real_open(use_path, flags, mode) : real_open(use_path, flags);
    spoof_guard = 0;
    return rc;
}
static int spoof_openat(int dirfd, const char *path, int flags, mode_t mode, int has_mode) {
    static openat_fn real_openat = NULL;
    if (!real_openat) real_openat = (openat_fn)dlsym(RTLD_NEXT, "openat");
    if (!real_openat) return -1;
    const char *redirect = redirect_os_release(path);
    const char *use_path = redirect ? redirect : path;
    spoof_guard = 1;
    int rc = has_mode ? real_openat(dirfd, use_path, flags, mode)
                      : real_openat(dirfd, use_path, flags);
    spoof_guard = 0;
    return rc;
}
int open(const char *path, int flags, ...) {
    mode_t mode = 0; int has_mode = (flags & O_CREAT) != 0;
    if (has_mode) { va_list ap; va_start(ap, flags); mode = va_arg(ap, mode_t); va_end(ap); }
    return spoof_open(path, flags, mode, has_mode);
}
int open64(const char *path, int flags, ...) {
    mode_t mode = 0; int has_mode = (flags & O_CREAT) != 0;
    if (has_mode) { va_list ap; va_start(ap, flags); mode = va_arg(ap, mode_t); va_end(ap); }
    return spoof_open(path, flags, mode, has_mode);
}
int openat(int dirfd, const char *path, int flags, ...) {
    mode_t mode = 0; int has_mode = (flags & O_CREAT) != 0;
    if (has_mode) { va_list ap; va_start(ap, flags); mode = va_arg(ap, mode_t); va_end(ap); }
    return spoof_openat(dirfd, path, flags, mode, has_mode);
}
int openat64(int dirfd, const char *path, int flags, ...) {
    mode_t mode = 0; int has_mode = (flags & O_CREAT) != 0;
    if (has_mode) { va_list ap; va_start(ap, flags); mode = va_arg(ap, mode_t); va_end(ap); }
    return spoof_openat(dirfd, path, flags, mode, has_mode);
}
