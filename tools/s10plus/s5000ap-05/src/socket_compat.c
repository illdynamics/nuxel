/* SPDX-License-Identifier: GPL-2.0-only
 * Linux 4.14 compatibility for systemd-resolved's SO_BINDTOIFINDEX.
 * Preserve interface binding with the older SO_BINDTODEVICE API. Never
 * ignore a socket error or turn a failed binding into an unbound socket.
 * This library is loaded only by systemd-resolved, not system-wide.
 */
#define _GNU_SOURCE
#include <errno.h>
#include <net/if.h>
#include <string.h>
#include <sys/socket.h>
#include <sys/syscall.h>
#include <unistd.h>
#ifndef SO_BINDTOIFINDEX
#define SO_BINDTOIFINDEX 62
#endif
int setsockopt(int fd, int level, int option, const void *value, socklen_t length)
{
    int result = (int)syscall(SYS_setsockopt, fd, level, option, value, length);
    if (result == 0 || errno != ENOPROTOOPT || level != SOL_SOCKET ||
        option != SO_BINDTOIFINDEX || !value || length != sizeof(int))
        return result;
    int index;
    memcpy(&index, value, sizeof index);
    char name[IF_NAMESIZE] = {0};
    if (index < 0) { errno = ENODEV; return -1; }
    if (index && !if_indextoname((unsigned)index, name)) return -1;
    return (int)syscall(SYS_setsockopt, fd, SOL_SOCKET, SO_BINDTODEVICE,
                        name, strlen(name) + 1);
}
