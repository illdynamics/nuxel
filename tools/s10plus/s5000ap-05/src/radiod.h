/*
 * radiod.h — internal interfaces for nuxel-radiod (production S5000AP service).
 * SPDX-License-Identifier: GPL-2.0-only
 */
#ifndef NUXEL_RADIOD_H
#define NUXEL_RADIOD_H

#include <stdint.h>
#include <stddef.h>
#include <stdbool.h>
#include "transport.h"
#include "sipc5_fmt.h"

/* bounded reassembly buffer per endpoint */
#define RADIOD_RX_BUF  (2u * NUXEL_TR_MAX_FRAME)
/* bounded outbound request queue */
#define RADIOD_MAX_PENDING 32u
/* max FMT payload we will accept (sanity bound; kernel dl_buffer is 4 KiB/8 KiB) */
#define RADIOD_MAX_PAYLOAD 65535u
/* ring of recent redacted observations kept for diagnostics */
#define RADIOD_OBS_RING 64u

struct radiod_diag_stats {
    uint64_t rx_frames;          /* successfully parsed complete FMT messages */
    uint64_t rx_bytes;           /* raw bytes read */
    uint64_t tx_frames;          /* FMT messages written (authorized) */
    uint64_t parse_truncated;    /* partial frames seen (reassembled) */
    uint64_t parse_errors;       /* malformed frames dropped */
    uint64_t overflow_drops;     /* buffer overflow / oversized frame drops */
    uint64_t unknown_cmd;        /* frames with main_cmd not in knowledge table */
    uint64_t raw_frames;         /* opaque non-FMT messages (RFS/RAW channels) */
    uint64_t raw_bytes;
    uint64_t rfs_ops;            /* RFS raw requests observed */
    uint64_t rfs_destructive;    /* RFS destructive requests (never executed) */
    uint64_t raw_rx_unclassified;/* opaque blobs that are not RFS-header shaped */
    uint64_t rfs_responses;    /* RFS responses written (policy-gated) */
    uint64_t rfs_resp_errors;  /* RFS response write failures */
    uint64_t disconnects;        /* endpoint disconnect events */
    uint64_t reconnects;         /* successful reopens */
    uint64_t timeouts;           /* request/response timeouts */
    uint64_t permissions;        /* EPERM/EBUSY (CP offline) events */
};

/* one redacted protocol observation (NO payload contents, NO identifiers) */
struct radiod_obs {
    uint64_t ts_ms;
    uint8_t  ch_id;
    uint8_t  main_cmd;
    uint8_t  sub_cmd;
    uint8_t  cmd_type;
    uint8_t  msg_seq;
    uint8_t  ack_seq;
    uint16_t payload_len;
    uint8_t  known;   /* 1 if (main,sub,type) present in the knowledge table */
};

struct radiod_cp_state {
    char     state[24];  /* kernel modem_state mirror: OFFLINE|BOOTING|ONLINE|... */
    int      state_code; /* raw IOCTL value if known, else -1 */
    uint64_t last_change_ms;
};

#endif
