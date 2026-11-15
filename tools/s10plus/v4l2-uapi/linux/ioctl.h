/* Userspace <linux/ioctl.h>: on a Linux host use the system kernel header; on
 * other hosts (macOS build of the tool) use the UAPI asm-generic ioctl macros,
 * which are identical to the Linux values. */
#ifndef _UAPI_LINUX_IOCTL_H
#define _UAPI_LINUX_IOCTL_H
#if defined(__linux__)
#include_next <linux/ioctl.h>
#else
#include <asm/ioctl.h>
#endif
#endif
