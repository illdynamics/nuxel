/*
 * fuzz_driver.c — deterministic stdin driver for sipc5_fmt.c.
 * SPDX-License-Identifier: GPL-2.0-only
 *
 * Reads a blob from stdin and stream-parses it under a fixed memory budget,
 * modelling a bounded read() loop over a SIPC FORMAT byte stream (the
 * userspace-visible model). Also, for each prefix, exercises the link-header
 * parser on the same bytes to catch overreads. Emits coverage counters to
 * stdout so the Python fuzzer can detect new coverage; NEVER prints payload
 * bytes (subscriber data could be present).
 *
 * Cap: input capped at NUXEL_FUZZ_MAX_INPUT (1 MiB) via bounded read.
 */
#include "sipc5_fmt.h"
#include "rfs_proto.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

#define CAP (1u << 20)   /* 1 MiB hard input cap */

int main(void)
{
    static u8 buf[CAP];
    size_t n = 0;
    ssize_t r;

    /* bounded read from stdin */
    while (n < CAP) {
        r = read(0, buf + n, CAP - n);
        if (r < 0) return 2;
        if (r == 0) break;
        n += (size_t)r;
    }

    /* 1) stream-parse FMT frames with a 64 KiB payload cap */
    {
        size_t off = 0;
        unsigned long coverage = 0;
        while (off + SIPC_FMT_HDR_SIZE <= n) {
            struct nuxel_sipc_fmt f;
            size_t c = 0;
            int res = sipc5_parse_fmt(buf + off, n - off, 0x10000, &f, &c);
            coverage = coverage * 31u + (unsigned long)((int)res + 10);
            if (res == SIPC_PARSE_TRUNCATED || res == SIPC_PARSE_OVERFLOW) {
                /* corrupt/partial tail: skip exactly one byte and continue,
                 * so hostile length fields cannot pin the loop. */
                off += 1;
                continue;
            }
            if (res != SIPC_PARSE_OK) { off += 1; continue; }
            off += c;
            if (c == 0) off += 1; /* never stall */
        }
        printf("fmt_coverage=%lu\n", coverage);
    }

    /* 2) parse the SIPC5 link header at every aligned offset (overread check) */
    {
        size_t off;
        unsigned long coverage = 0;
        for (off = 0; off < n; off++) {
            struct nuxel_sipc5_link l;
            int res = sipc5_parse_link_header(buf + off, n - off, &l);
            coverage ^= (unsigned long)((int)res + 5) * 0x9e3779b9u;
        }
        printf("link_coverage=%lu\n", coverage);
    }

    /* 3) RFS raw-header parser at every offset (overread/classification check) */
    {
        size_t off;
        unsigned long coverage = 0;
        for (off = 0; off < n; off++) {
            struct rfs_proto_msg m;
            int res = rfs_proto_parse(buf + off, n - off, &m);
            coverage ^= (unsigned long)((int)res + 7) * 0x85ebca6bu;
        }
        printf("rfs_coverage=%lu\n", coverage);
    }

    printf("bytes=%zu\n", n);
    return 0;
}
