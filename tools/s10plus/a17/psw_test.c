/* Calls libsystemd-shared's real posix_spawn_wrapper() the way PID1 does. */
#define _GNU_SOURCE
#include <errno.h>
#include <signal.h>
#include <spawn.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/wait.h>
#include <unistd.h>

typedef struct PidRef { pid_t pid; int fd; uint64_t fd_id; } PidRef;

extern int posix_spawn_wrapper(const char *path, char *const *argv, char *const *envp,
                               const char *cgroup, PidRef *ret_pidref);
extern char **environ;

int main(int argc, char **argv) {
        const char *cgroup = argc > 1 && strcmp(argv[1], "-") ? argv[1] : NULL;
        char *av[] = { (char *)"sh", (char *)"-c", (char *)"echo CHILD-RAN >> /b/nx17/childran.txt; sleep 0.3; exit 0", NULL };
        PidRef p = { .pid = 0, .fd = -EBADF, .fd_id = 0 };

        int r = posix_spawn_wrapper("/bin/sh", av, environ, cgroup, &p);
        printf("RESULT posix_spawn_wrapper rc=%d (%s) pid=%d fd=%d fd_id=%llu\n",
               r, r ? strerror(r < 0 ? -r : r) : "ok", p.pid, p.fd,
               (unsigned long long) p.fd_id);
        if (r == 0 && p.pid > 0) {
                int st = 0;
                waitpid(p.pid, &st, 0);
                printf("RESULT child exited status=%d\n", WIFEXITED(st) ? WEXITSTATUS(st) : -1);
        }
        /* mirror executor.c's decision */
        printf("RESULT pid1_would_log=%s\n", r < 0 ? "FAILED-TO-SPAWN-EXECUTOR" : "spawn-ok");
        return 0;
}
