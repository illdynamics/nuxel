/* Minimal UAPI <linux/compiler.h> for userspace builds on non-Linux hosts.
 * The kernel header only needs __user/__force/__bitwise for userspace. */
#ifndef _UAPI__LINUX_COMPILER_H
#define _UAPI__LINUX_COMPILER_H
#ifndef __user
#define __user
#endif
#ifndef __force
#define __force
#endif
#ifndef __bitwise
#define __bitwise
#endif
#ifndef __packed
#define __packed __attribute__((packed))
#endif
#ifndef __KERNEL__
/* Apple's <sys/ioctl.h> already defines the same _IOC/_IO* macros; the UAPI
 * asm-generic header is included afterwards and would warn. Suppress only the
 * redefinition noise, not the definitions themselves. */
#ifdef __APPLE__
#pragma clang diagnostic ignored "-Wmacro-redefined"
#pragma GCC diagnostic ignored "-Wmacro-redefined"
#endif
#endif
#endif
