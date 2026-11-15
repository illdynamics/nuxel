/* Minimal UAPI <linux/types.h> for userspace builds on non-Linux hosts. */
#ifndef _UAPI_LINUX_TYPES_H
#define _UAPI_LINUX_TYPES_H
#include <stdint.h>
#include <stddef.h>
typedef uint8_t __u8; typedef uint16_t __u16; typedef uint32_t __u32;
typedef uint64_t __u64; typedef int8_t __s8; typedef int16_t __s16;
typedef int32_t __s32; typedef int64_t __s64;
typedef uint16_t __le16; typedef uint32_t __le32; typedef uint64_t __le64;
typedef uint16_t __be16; typedef uint32_t __be32; typedef uint64_t __be64;
typedef uint16_t __sum16; typedef uint32_t __wsum; typedef uint64_t __poll_t;
typedef unsigned long __kernel_ulong_t;
typedef int __kernel_pid_t;
typedef unsigned int __kernel_uid32_t;
typedef unsigned int __kernel_gid32_t;
typedef long long __kernel_loff_t;
typedef unsigned int __kernel_size_t;
typedef int __kernel_ssize_t;
typedef long long __kernel_time_t;
typedef long long __kernel_suseconds_t;
typedef unsigned int __kernel_clock_t;
typedef int __kernel_daddr_t;
typedef unsigned int __kernel_old_dev_t;
typedef unsigned int __kernel_mode_t;
typedef int __kernel_key_t;
typedef int __kernel_mqd_t;
#ifndef __bitwise
#define __bitwise
#endif
#endif
