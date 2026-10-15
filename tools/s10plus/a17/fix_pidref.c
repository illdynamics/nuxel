/* Candidate fix under test: pidref_set_pid() must degrade to a pid-only PidRef
 * when the kernel has no pidfd_open(), instead of returning -ENOSYS. */
#define _GNU_SOURCE
#include <errno.h>
#include <stdint.h>
#include <sys/types.h>

typedef struct PidRef { pid_t pid; int fd; uint64_t fd_id; } PidRef;

int pidfd_open(pid_t pid, unsigned int flags);

int pidref_set_pid(PidRef *p, pid_t pid) {
        uint64_t pidfdid = 0;
        int fd;

        if (pid < 0) return -ESRCH;
        fd = pidfd_open(pid, 0);
        if (fd < 0) {
                /* NUXEL: no pidfd support in this kernel -> pid-only PidRef */
                if (errno != ENOSYS && errno != EOPNOTSUPP && errno != ENOTTY)
                        return -errno;
                fd = -EBADF;
        }
        *p = (PidRef) { .pid = pid, .fd = fd, .fd_id = pidfdid };
        return 0;
}
