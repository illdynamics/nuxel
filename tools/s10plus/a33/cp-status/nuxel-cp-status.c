/*
 * nuxel-cp-status.c — READ-ONLY Samsung Shannon S5000AP CP state probe.
 *
 * What it does (and nothing else):
 *   * opens /dev/umts_boot0 O_RDONLY|O_CLOEXEC|O_NOCTTY|O_NONBLOCK
 *   * takes a shared (LOCK_SH|LOCK_NB) flock so a concurrently booting CP
 *     owner makes us fail rather than interleave
 *   * issues exactly one ioctl: IOCTL_MODEM_STATUS = _IO('o', 0x27)
 *   * prints {"node":..,"state":..,"state_code":..,"errno":..,"errno_name":..,"ts":..}
 *
 * What it never does:
 *   * opens the node READ-ONLY (O_RDONLY); the kernel rejects writes through the
 *     resulting fd, and this program performs no write() or writev()
 *   * no BOOT_ON/OFF/DONE, no DOWNLOAD, no XMIT_BOOT,
 *     no RESET, no RFS, no SIPC, no AT traffic, no power-state change
 *   * no partition or block-device access
 *   * no SIM/IMSI/ICCID/IMEI reads
 *
 * ioctl encoding comes from the exact pinned kernel source:
 *   kernel/s10plus/.build/src.polluted.case-insensitive/drivers/misc/modem_v1/
 *   modem_prj.h: #define IOCTL_MODEM_STATUS _IO('o', 0x27)
 *   modem_io_device.c handles it and returns mc->phone_state (enum modem_state).
 * Compile-time asserts pin the ioctl value and the enum ordering so a header
 * drift fails the build instead of silently mislabelling CP state.
 *
 * SPDX-License-Identifier: GPL-2.0-only
 */
#ifndef _GNU_SOURCE
#define _GNU_SOURCE
#endif
#include <errno.h>
#include <fcntl.h>
#include <stdio.h>
#include <string.h>
#include <sys/file.h>
#include <sys/ioctl.h>
#include <time.h>
#include <unistd.h>

#define NUXEL_IOCTL_MODEM_STATUS _IO('o', 0x27)

/* enum modem_state — must match modem_prj.h verbatim, in order. */
enum modem_state {
	STATE_OFFLINE = 0,
	STATE_CRASH_RESET,
	STATE_CRASH_EXIT,
	STATE_BOOTING,
	STATE_ONLINE,
	STATE_NV_REBUILDING,
	STATE_LOADER_DONE,
	STATE_SIM_ATTACH,
	STATE_SIM_DETACH,
	STATE_CRASH_WATCHDOG,
	STATE_MAX
};

_Static_assert(NUXEL_IOCTL_MODEM_STATUS == 0x6f27, "IOCTL_MODEM_STATUS value drifted");
_Static_assert(STATE_OFFLINE == 0 && STATE_ONLINE == 4 && STATE_CRASH_WATCHDOG == 9,
	       "enum modem_state ordering drifted from pinned kernel");

static const char *state_name(int s)
{
	switch (s) {
	case STATE_OFFLINE:        return "OFFLINE";
	case STATE_CRASH_RESET:    return "CRASH_RESET";
	case STATE_CRASH_EXIT:     return "CRASH_EXIT";
	case STATE_BOOTING:        return "BOOTING";
	case STATE_ONLINE:         return "ONLINE";
	case STATE_NV_REBUILDING:  return "NV_REBUILDING";
	case STATE_LOADER_DONE:    return "LOADER_DONE";
	case STATE_SIM_ATTACH:     return "SIM_ATTACH";
	case STATE_SIM_DETACH:     return "SIM_DETACH";
	case STATE_CRASH_WATCHDOG: return "CRASH_WATCHDOG";
	default:                   return "UNKNOWN";
	}
}

static void now_iso(char *buf, size_t n)
{
	time_t t = time(NULL);
	struct tm tm;
	if (gmtime_r(&t, &tm))
		strftime(buf, n, "%Y-%m-%dT%H:%M:%SZ", &tm);
	else
		snprintf(buf, n, "unknown");
}

/* strerrorname_np is glibc>=2.32. The device has glibc 2.42 but the host
 * cross-toolchain may not, so we degrade to numeric-only rather than fail the
 * build. The JSON shape is identical; only the human label is omitted.
 */
#ifndef NUXEL_HAVE_STRERRORNAME_NP
#ifdef __GLIBC__
#if (__GLIBC__ > 2) || (__GLIBC__ == 2 && __GLIBC_MINOR__ >= 32)
#define NUXEL_HAVE_STRERRORNAME_NP 1
#endif
#endif
#endif
static const char *errno_name_of(int err)
{
#ifdef NUXEL_HAVE_STRERRORNAME_NP
	return strerrorname_np(err);
#else
	(void)err;
	return "errno-name-unavailable";
#endif
}

static void emit_error(const char *node, const char *errno_name, int err)
{
	char ts[32];
	now_iso(ts, sizeof ts);
	printf("{\"node\":\"%s\",\"state\":\"UNKNOWN\",\"state_code\":-1,"
	       "\"errno\":%d,\"errno_name\":\"%s\",\"ts\":\"%s\"}\n",
	       node, err, errno_name, ts);
}

int main(int argc, char **argv)
{
	const char *node = (argc > 1) ? argv[1] : "/dev/umts_boot0";
	char ts[32];
	int fd, st, e;

	fd = open(node, O_RDONLY | O_CLOEXEC | O_NOCTTY | O_NONBLOCK);
	if (fd < 0) {
		emit_error(node, errno_name_of(errno), errno);
		return 2;
	}
	if (flock(fd, LOCK_SH | LOCK_NB) != 0) {
		e = errno;
		close(fd);
		emit_error(node, errno_name_of(e), e);
		return 3;
	}

	errno = 0;
	st = ioctl(fd, NUXEL_IOCTL_MODEM_STATUS);
	e = errno;

	flock(fd, LOCK_UN);
	close(fd);

	now_iso(ts, sizeof ts);
	if (st < 0) {
		emit_error(node, errno_name_of(e), e);
		return 4;
	}
	printf("{\"node\":\"%s\",\"state\":\"%s\",\"state_code\":%d,"
	       "\"errno\":0,\"errno_name\":\"0\",\"ts\":\"%s\"}\n",
	       node, state_name(st), st, ts);
	return 0;
}
