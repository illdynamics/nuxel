/* SPDX-License-Identifier: BSD-2-Clause */
/*
 * Nuxel kernel host-tool <endian.h> shim for macOS (Darwin).
 *
 * The Linux kernel builds several *host* tools (arch/arm64/tools/gen-hyprel,
 * scripts/recordmcount, scripts/sorttable, ...) that include the POSIX/glibc
 * <endian.h>.  macOS ships no <endian.h> and glibc's byte-swap helpers are
 * absent.  This header provides the small, self-contained subset those host
 * tools need, backed by macOS's libkern/OSByteOrder.h primitives, so the
 * kernel build is no longer blocked on what is purely a host-library gap.
 *
 * It is only injected into the *host* tool compile (HOSTCFLAGS), never for
 * target/arm64 cross-compilation.  On Linux hosts the real <endian.h> is used
 * instead; this shim is arm64/clean be/le portable and harmless everywhere.
 *
 * Host architecture endianness: use __BYTE_ORDER__ (GCC/Clang builtin define).
 * The shim is used only on macOS, which is always little-endian in practice,
 * but the fallback below keeps it correct even on a big-endian host.
 */
#ifndef _NUXEL_HOST_ENDIAN_H_
#define _NUXEL_HOST_ENDIAN_H_

/* Prefer the compact glibc/musl-compatible names used by the kernel scripts. */
#if defined(__APPLE__)
#  include <libkern/OSByteOrder.h>
#  define __BYTE_ORDER    __DARWIN_BYTE_ORDER
#  define __LITTLE_ENDIAN __DARWIN_LITTLE_ENDIAN
#  define __BIG_ENDIAN    __DARWIN_BIG_ENDIAN
#  define BYTE_ORDER      __BYTE_ORDER
#  define LITTLE_ENDIAN   __LITTLE_ENDIAN
#  define BIG_ENDIAN      __BIG_ENDIAN

#  define htobe16(x) OSSwapHostToBigInt16(x)
#  define htole16(x) OSSwapHostToLittleInt16(x)
#  define be16toh(x) OSSwapBigToHostInt16(x)
#  define le16toh(x) OSSwapLittleToHostInt16(x)

#  define htobe32(x) OSSwapHostToBigInt32(x)
#  define htole32(x) OSSwapHostToLittleInt32(x)
#  define be32toh(x) OSSwapBigToHostInt32(x)
#  define le32toh(x) OSSwapLittleToHostInt32(x)

#  define htobe64(x) OSSwapHostToBigInt64(x)
#  define htole64(x) OSSwapHostToLittleInt64(x)
#  define be64toh(x) OSSwapBigToHostInt64(x)
#  define le64toh(x) OSSwapLittleToHostInt64(x)
#else
/* Robust fallback (non-Apple): pure-C swap based on __BYTE_ORDER__. */
#  include <stdint.h>
#  ifndef __BYTE_ORDER
#    error "endian.h shim: host __BYTE_ORDER__/endianness must be defined"
#  endif
#  define _nuxel_swap16(x) \
	((uint16_t)((((uint16_t)(x) & 0x00ffU) << 8) | \
		    (((uint16_t)(x) & 0xff00U) >> 8)))
#  define _nuxel_swap32(x) \
	((uint32_t)((((uint32_t)(x) & 0x000000ffUL) << 24) | \
		    (((uint32_t)(x) & 0x0000ff00UL) << 8)  | \
		    (((uint32_t)(x) & 0x00ff0000UL) >> 8)  | \
		    (((uint32_t)(x) & 0xff000000UL) >> 24)))
#  define _nuxel_swap64(x) \
	((uint64_t)((((uint64_t)(x) & 0x00000000000000ffULL) << 56) | \
		    (((uint64_t)(x) & 0x000000000000ff00ULL) << 40) | \
		    (((uint64_t)(x) & 0x0000000000ff0000ULL) << 24) | \
		    (((uint64_t)(x) & 0x00000000ff000000ULL) << 8)  | \
		    (((uint64_t)(x) & 0x000000ff00000000ULL) >> 8)  | \
		    (((uint64_t)(x) & 0x0000ff0000000000ULL) >> 24) | \
		    (((uint64_t)(x) & 0x00ff000000000000ULL) >> 40) | \
		    (((uint64_t)(x) & 0xff00000000000000ULL) >> 56)))
#  if __BYTE_ORDER__ == __ORDER_LITTLE_ENDIAN__
#    define htobe16(x) _nuxel_swap16(x)
#    define htole16(x) ((uint16_t)(x))
#    define be16toh(x) _nuxel_swap16(x)
#    define le16toh(x) ((uint16_t)(x))
#    define htobe32(x) _nuxel_swap32(x)
#    define htole32(x) ((uint32_t)(x))
#    define be32toh(x) _nuxel_swap32(x)
#    define le32toh(x) ((uint32_t)(x))
#    define htobe64(x) _nuxel_swap64(x)
#    define htole64(x) ((uint64_t)(x))
#    define be64toh(x) _nuxel_swap64(x)
#    define le64toh(x) ((uint64_t)(x))
#  else
#    define htobe16(x) ((uint16_t)(x))
#    define htole16(x) _nuxel_swap16(x)
#    define be16toh(x) ((uint16_t)(x))
#    define le16toh(x) _nuxel_swap16(x)
#    define htobe32(x) ((uint32_t)(x))
#    define htole32(x) _nuxel_swap32(x)
#    define be32toh(x) ((uint32_t)(x))
#    define le32toh(x) _nuxel_swap32(x)
#    define htobe64(x) ((uint64_t)(x))
#    define htole64(x) _nuxel_swap64(x)
#    define be64toh(x) ((uint64_t)(x))
#    define le64toh(x) _nuxel_swap64(x)
#  endif
#  undef _nuxel_swap16
#  undef _nuxel_swap32
#  undef _nuxel_swap64
#endif

#endif /* _NUXEL_HOST_ENDIAN_H_ */
