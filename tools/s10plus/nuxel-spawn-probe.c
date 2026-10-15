/* Nuxel S10+ process-spawn probe.
 *
 * Measures, at the libc boundary the Fedora 43 userspace actually uses, why
 * systemd 258.11's posix_spawn_wrapper() returns ENOSYS on this 4.14.253 kernel.
 *
 * Expected (Linux < 5.4, glibc >= 2.39):
 *   waitid(P_PIDFD, ...)        -> EINVAL
 *   posix_spawn()               -> 0        (works: clone3() with a clone() fallback)
 *   pidfd_spawn()               -> ENOSYS   (glibc's __clone_pidfd_supported() probe fails)
 * and therefore every systemd service spawn logs
 *   "Failed to spawn executor: Function not implemented".
 *
 * Results go to stdout AND to /dev/kmsg (this device's /dev/console is ENODEV).
 * Build: aarch64, glibc 2.42 (Fedora 43), same version as the device rootfs.
 */
#define _GNU_SOURCE
#include <errno.h>
#include <fcntl.h>
#include <spawn.h>
#include <stdarg.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/syscall.h>
#include <sys/utsname.h>
#include <sys/wait.h>
#include <unistd.h>
#include <gnu/libc-version.h>

#ifndef P_PIDFD
#define P_PIDFD 3
#endif

extern char **environ;

static int kfd = -1;

static void emit(const char *fmt, ...) {
        char buf[512];
        va_list ap;
        int n;

        va_start(ap, fmt);
        n = vsnprintf(buf, sizeof buf, fmt, ap);
        va_end(ap);
        if (n < 0)
                return;
        if ((size_t) n >= sizeof buf)
                n = (int) sizeof buf - 1;

        fwrite(buf, 1, (size_t) n, stdout);
        fflush(stdout);
        if (kfd >= 0) {
                char line[520];
                int m = snprintf(line, sizeof line, "%.*s", n, buf);
                if (m > 0)
                        (void) !write(kfd, line, (size_t) m);
        }
}

static const char *errname(int e) {
        switch (e) {
        case 0:     return "OK";
        case ENOSYS:return "ENOSYS (Function not implemented)";
        case EINVAL:return "EINVAL (Invalid argument)";
        case EBADF: return "EBADF";
        case ECHILD:return "ECHILD";
        case EOPNOTSUPP: return "EOPNOTSUPP";
        default:    return strerror(e);
        }
}

int main(void) {
        struct utsname u;
        char *argv[] = { (char *) "sh", (char *) "-c", (char *) "exit 7", NULL };
        pid_t pid = -1;
        int pidfd = -1, r;
        long sr;

        kfd = open("/dev/kmsg", O_WRONLY | O_CLOEXEC);

        emit("NUXEL-SPAWN-PROBE begin\n");
        if (uname(&u) == 0)
                emit("NUXEL-SPAWN-PROBE kernel=%s glibc=%s\n", u.release, gnu_get_libc_version());
        emit("NUXEL-SPAWN-PROBE pid=%d ppid=%d\n", (int) getpid(), (int) getppid());

        /* 1. the exact probe glibc uses to gate pidfd_spawn() */
        errno = 0;
        sr = syscall(SYS_waitid, P_PIDFD, (long) 0x7fffffc0L, NULL, WEXITED | WNOHANG);
        emit("NUXEL-SPAWN-PROBE waitid(P_PIDFD,0x7fffffc0,NULL,WEXITED|WNOHANG) ret=%ld errno=%d %s%s\n",
             sr, errno, errname(errno),
             errno == EBADF ? " [glibc would ALLOW pidfd_spawn]" : " [glibc DENIES pidfd_spawn -> it returns ENOSYS]");

        /* 2. plain posix_spawn(): the path systemd must fall back to */
        errno = 0;
        r = posix_spawn(&pid, "/bin/sh", NULL, NULL, argv, environ);
        if (r == 0) {
                int st = 0;
                waitpid(pid, &st, 0);
                emit("NUXEL-SPAWN-PROBE posix_spawn(/bin/sh,\"exit 7\") rc=0 child_status=%d %s\n",
                     WIFEXITED(st) ? WEXITSTATUS(st) : -1,
                     (WIFEXITED(st) && WEXITSTATUS(st) == 7) ? "[ok: process really ran]" : "[unexpected]");
        } else
                emit("NUXEL-SPAWN-PROBE posix_spawn(/bin/sh,\"exit 7\") rc=%d %s\n", r, errname(r));

        /* 3. pidfd_spawn(): what systemd 258.11 actually calls */
        errno = 0;
        r = pidfd_spawn(&pidfd, "/bin/sh", NULL, NULL, argv, environ);
        emit("NUXEL-SPAWN-PROBE pidfd_spawn(/bin/sh,\"exit 7\") rc=%d %s pidfd=%d%s\n",
             r, errname(r), pidfd,
             r == ENOSYS ? "  <== THIS IS THE systemd \"Failed to spawn executor\" ERROR" : "");
        if (r == 0 && pidfd >= 0)
                close(pidfd);

        /* 4. fork() + execve(): the mechanism nothing in a working boot can avoid */
        pid = fork();
        if (pid == 0) {
                char *a[] = { (char *) "sh", (char *) "-c", (char *) "exit 5", NULL };
                execve("/bin/sh", a, environ);
                _exit(127);
        }
        if (pid > 0) {
                int st = 0;
                waitpid(pid, &st, 0);
                emit("NUXEL-SPAWN-PROBE fork+execve(/bin/sh,\"exit 5\") child_status=%d %s\n",
                     WIFEXITED(st) ? WEXITSTATUS(st) : -1,
                     (WIFEXITED(st) && WEXITSTATUS(st) == 5) ? "[ok]" : "[unexpected]");
        } else
                emit("NUXEL-SPAWN-PROBE fork failed errno=%d %s\n", errno, errname(errno));

        /* 5. the cgroup v2 facts systemd 258 asserts */
        r = open("/sys/fs/cgroup/cgroup.controllers", O_RDONLY | O_CLOEXEC);
        emit("NUXEL-SPAWN-PROBE cgroup2_unified=%s\n", r >= 0 ? "present" : "absent");
        if (r >= 0) close(r);

        emit("NUXEL-SPAWN-PROBE end\n");
        emit("NUXEL_MARKER SPAWN_PROBE_DONE\n");
        return 0;
}
