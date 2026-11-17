/* Socket-only diagnostic for a PRIVATE network namespace. No bind/connect,
 * device access, sysfs or Binder. Used to explain lhd's AF_INET EACCES. */
#define _DEFAULT_SOURCE
#include <errno.h>
#include <grp.h>
#include <string.h>
#include <stdio.h>
#include <sys/socket.h>
#include <unistd.h>
int main(int argc, char **argv)
{
    /* Optional credential drop in the initial user namespace. bwrap remains
     * responsible for private mount/network/PID namespaces. */
    if (argc == 2) {
        gid_t gid;
        if (!strcmp(argv[1], "3003")) gid = 3003;
        else if (!strcmp(argv[1], "65534")) gid = 65534;
        else return 64;
        if (setgroups(0, NULL) || setgid(gid) || setuid(65534)) {
            perror("credential drop");
            return 1;
        }
    } else if (argc != 1) return 64;
    int fd = socket(AF_INET, SOCK_STREAM, 0);
    int error = fd < 0 ? errno : 0;
    printf("uid=%lu gid=%lu AF_INET_errno=%d hardware_verified=false\n",
           (unsigned long)getuid(), (unsigned long)getgid(), error);
    if (fd >= 0) close(fd);
    return error == EACCES ? 13 : error ? 1 : 0;
}
