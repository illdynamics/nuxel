/* SPDX-License-Identifier: BSD-2-Clause */
/*
 * Nuxel kernel host-tool <byteswap.h> shim for macOS (Darwin).
 *
 * Linux kernel host tools (notably scripts/mod/modpost.h -> modpost) pull in
 * glibc's <byteswap.h> for bswap_16/32/64.  Apple ships no <byteswap.h>; this
 * thin shim provides exactly the bswap_* family via libkern/OSByteOrder.h and
 * is injected only into the *host* tool compile (HOSTCFLAGS), never into the
 * arm64 cross (target) build.  On Linux the real <byteswap.h> is used.
 */
#ifndef _NUXEL_HOST_BYTESWAP_H_
#define _NUXEL_HOST_BYTESWAP_H_

#include <stdint.h>

#if defined(__APPLE__)
#  include <libkern/OSByteOrder.h>
#  define bswap_16(x) ((uint16_t)OSSwapConstInt16((uint16_t)(x)))
#  define bswap_32(x) ((uint32_t)OSSwapConstInt32((uint32_t)(x)))
#  define bswap_64(x) ((uint64_t)OSSwapConstInt64((uint64_t)(x)))
#else
/* Portable pure-C fallback (endianness-independent byte swap). */
#  define bswap_16(x)                                          \
	((uint16_t)((((uint16_t)(x) & 0x00ffU) << 8) |         \
		    (((uint16_t)(x) & 0xff00U) >> 8)))
#  define bswap_32(x)                                           \
	((uint32_t)((((uint32_t)(x) & 0x000000ffUL) << 24) |    \
		    (((uint32_t)(x) & 0x0000ff00UL) << 8)  |    \
		    (((uint32_t)(x) & 0x00ff0000UL) >> 8)  |    \
		    (((uint32_t)(x) & 0xff000000UL) >> 24)))
#  define bswap_64(x)                                           \
	((uint64_t)((((uint64_t)(x) & 0x00000000000000ffULL) << 56) | \
		    (((uint64_t)(x) & 0x000000000000ff00ULL) << 40) | \
		    (((uint64_t)(x) & 0x0000000000ff0000ULL) << 24) | \
		    (((uint64_t)(x) & 0x00000000ff000000ULL) << 8)  | \
		    (((uint64_t)(x) & 0x000000ff00000000ULL) >> 8)  | \
		    (((uint64_t)(x) & 0x0000ff0000000000ULL) >> 24) | \
		    (((uint64_t)(x) & 0x00ff000000000000ULL) >> 40) | \
		    (((uint64_t)(x) & 0xff00000000000000ULL) >> 56)))
#endif

#endif /* _NUXEL_HOST_BYTESWAP_H_ */
