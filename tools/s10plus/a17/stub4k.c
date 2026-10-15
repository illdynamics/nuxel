/* Emulate a Linux 4.14 kernel (no pidfd_open / no pidfd-capable pidfd_spawn)
 * inside the modern podman kernel, so the exact Nuxel/S10+ spawn path can be
 * reproduced and validated offline. */
#define _GNU_SOURCE
#include <errno.h>
#include <sys/types.h>

int pidfd_spawn(int *pidfd, const char *path, const void *fa, const void *attr,
                char *const argv[], char *const envp[]) {
        (void) pidfd; (void) path; (void) fa; (void) attr; (void) argv; (void) envp;
        return ENOSYS;                     /* glibc: "clone pidfd unsupported" */
}

int pidfd_open(pid_t pid, unsigned int flags) {
        (void) pid; (void) flags;
        errno = ENOSYS;                    /* Linux 4.14: no pidfd_open syscall */
        return -1;
}

int pidfd_send_signal(int fd, int sig, void *info, unsigned int flags) {
        (void) fd; (void) sig; (void) info; (void) flags;
        errno = ENOSYS;
        return -1;
}

int pidfd_getfd(int fd, int targetfd, unsigned int flags) {
        (void) fd; (void) targetfd; (void) flags;
        errno = ENOSYS;
        return -1;
}
