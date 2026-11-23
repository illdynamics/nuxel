/*
 * s5000ap-status — READ-ONLY CP status probe for Exynos9820 / S5000AP.
 *
 * Opens /dev/umts_boot0 O_RDONLY, takes a shared non-blocking lock, issues
 * exactly ONE ioctl (IOCTL_MODEM_STATUS == 0x6F27), prints JSON, closes.
 *
 * It performs NO write(), NO O_RDWR/O_WRONLY, NO reset/boot/power/download
 * ioctl, NO mmap, and NO block-device access. It cannot move the modem state.
 *
 * Safety invariants are enforced at compile time via _Static_assert against
 * the verified s5000ap_uapi.h. If the header drifts, this binary fails to
 * build rather than mislabelling the modem state.
 */
#define _GNU_SOURCE
#include <stdio.h>
#include <string.h>
#include <errno.h>
#include <fcntl.h>
#include <unistd.h>
#include <sys/ioctl.h>
#include <sys/file.h>
#include <time.h>

#include "s5000ap_uapi.h"

/* ---- compile-time ABI pins (fail build on drift) ---------------------- */
_Static_assert(IOCTL_MODEM_STATUS == 0x6F27, "IOCTL_MODEM_STATUS must be 0x6F27");
_Static_assert(STATE_OFFLINE == 0 && STATE_ONLINE == 4
               && STATE_CRASH_WATCHDOG == 9, "modem_state order drift");
_Static_assert(STATE_BOOTING == 3, "STATE_BOOTING must be 3");

#define DEFAULT_NODE "/dev/umts_boot0"

static const char *state_name(enum modem_state s)
{
    switch (s) {
    case STATE_OFFLINE: return "OFFLINE";
    case STATE_CRASH_RESET: return "CRASH_RESET";
    case STATE_CRASH_EXIT: return "CRASH_EXIT";
    case STATE_BOOTING: return "BOOTING";
    case STATE_ONLINE: return "ONLINE";
    case STATE_NV_REBUILDING: return "NV_REBUILDING";
    case STATE_LOADER_DONE: return "LOADER_DONE";
    case STATE_SIM_ATTACH: return "SIM_ATTACH";
    case STATE_SIM_DETACH: return "SIM_DETACH";
    case STATE_CRASH_WATCHDOG: return "CRASH_WATCHDOG";
    default: return "UNKNOWN";
    }
}

int main(int argc, char **argv)
{
    const char *node = (argc > 1) ? argv[1] : DEFAULT_NODE;
    int fd, ret;
    char ts[40];
    struct timespec now;
    long state;

    /* READ-ONLY open; the handful of flags below are the only ones used. */
    fd = open(node, O_RDONLY | O_CLOEXEC | O_NOCTTY | O_NONBLOCK);
    if (fd < 0) {
        printf("{\"node\":\"%s\",\"state\":null,\"errno\":%d,\"errno_name\":\"%s\",\"op\":\"open\"}\n",
               node, errno, strerror(errno));
        return 1;
    }

    /* Shared non-blocking lock: never blocks, never changes ownership. */
    if (flock(fd, LOCK_SH | LOCK_NB) != 0) {
        int e = errno;
        printf("{\"node\":\"%s\",\"state\":null,\"errno\":%d,\"errno_name\":\"%s\",\"op\":\"flock\"}\n",
               node, e, strerror(e));
        close(fd);
        return 1;
    }

    /* The single hardware-touching syscall: a read of the phone state. */
    ret = ioctl(fd, IOCTL_MODEM_STATUS);
    if (ret < 0) {
        int e = errno;
        printf("{\"node\":\"%s\",\"state\":null,\"errno\":%d,\"errno_name\":\"%s\",\"op\":\"ioctl\"}\n",
               node, e, strerror(e));
        flock(fd, LOCK_UN);
        close(fd);
        return 1;
    }

    state = (long)ret;

    clock_gettime(CLOCK_REALTIME, &now);
    {
        struct tm tm;
        gmtime_r(&now.tv_sec, &tm);
        strftime(ts, sizeof(ts), "%Y-%m-%dT%H:%M:%SZ", &tm);
    }

    printf("{\"node\":\"%s\",\"state\":\"%s\",\"state_code\":%ld,"
           "\"errno\":0,\"errno_name\":\"0\",\"ts\":\"%s\"}\n",
           node, state_name((enum modem_state)state), state, ts);

    flock(fd, LOCK_UN);
    close(fd);
    return 0;
}
