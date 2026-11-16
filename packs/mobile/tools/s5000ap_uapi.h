#ifndef NUXEL_S5000AP_UAPI_H
#define NUXEL_S5000AP_UAPI_H

/*
 * Deliberately tiny, read-only subset of the Samsung modem_v1 userspace ABI.
 * This header exposes ONLY MODEM_STATUS.  It intentionally does not define
 * power/reset/download/firmware-update/dump/RFS write ioctls.
 *
 * Target audited in the supplied Nuxel tree: Samsung SM-G975F / beyond2lte,
 * Exynos 9820, vendor Linux 4.14.253.
 */
#include <sys/ioctl.h>

#define NUXEL_IOCTL_MODEM_STATUS _IO('o', 0x27)

enum nuxel_s5000ap_phone_state {
    NUXEL_STATE_OFFLINE = 0,
    NUXEL_STATE_CRASH_RESET,
    NUXEL_STATE_CRASH_EXIT,
    NUXEL_STATE_BOOTING,
    NUXEL_STATE_ONLINE,
    NUXEL_STATE_NV_REBUILDING,
    NUXEL_STATE_LOADER_DONE,
    NUXEL_STATE_SIM_ATTACH,
    NUXEL_STATE_SIM_DETACH,
    NUXEL_STATE_CRASH_WATCHDOG
};

#endif
