/*
 * transport.h — device transport abstraction for S5000AP SIPC5 endpoints.
 *
 * SPDX-License-Identifier: GPL-2.0-only
 *
 * One nuxel_sipc_dev owns exactly ONE /dev/umts_* endpoint. It:
 *   - opens O_RDWR|O_NONBLOCK|O_CLOEXEC,
 *   - takes an exclusive advisory flock (LOCK_EX|LOCK_NB) so two daemons can
 *     never interleave on the same endpoint (kernel also has its own open count,
 *     but flock gives us a clean userspace ownership contract),
 *   - performs bounded reads into a caller buffer,
 *   - distinguishes "no data" (EAGAIN) from a real disconnect/error,
 *   - performs writes only when the caller has been granted write capability
 *     (the CP-online gate is enforced by the kernel via -EPERM).
 *
 * The transport NEVER parses or interprets bytes; framing lives in sipc5_fmt.c.
 * It NEVER logs payload bytes.
 */
#ifndef NUXEL_TRANSPORT_H
#define NUXEL_TRANSPORT_H

#include <stddef.h>
#include <stdint.h>
#include <sys/types.h>

#ifdef __cplusplus
extern "C" {
#endif

#define NUXEL_TR_MAX_FRAME 65536u  /* hard cap on a single read (per DT max dl_buffer_size*count) */

struct nuxel_sipc_dev {
    int    fd;          /* >=0 when open */
    int    locked;      /* flock held */
    char   node[64];
    uint8_t ch_id;
    uint8_t format;     /* 0=FMT 1=RAW 2=RFS */
};

typedef enum nuxel_io_status {
    NUXEL_IO_OK = 0,
    NUXEL_IO_NO_DATA,        /* EAGAIN: nothing queued (not an error) */
    NUXEL_IO_WOULDBLOCK,
    NUXEL_IO_DISCONNECTED,   /* ENODEV/EIO/EPOLLHUP: endpoint gone/reset */
    NUXEL_IO_PERMISSION,     /* EPERM/EBUSY: CP offline / value gated */
    NUXEL_IO_ERROR,
} nuxel_io_status;

/* Open + exclusive-lock a channel. Returns 0 on success, negative errno-style. */
int  nuxel_dev_open(struct nuxel_sipc_dev *d, const char *node,
                    uint8_t ch_id, uint8_t format);

/* Close + release flock (idempotent). */
void nuxel_dev_close(struct nuxel_sipc_dev *d);

/*
 * Read up to `cap` bytes into `buf` (cap clamped to NUXEL_TR_MAX_FRAME).
 * Returns >=0 byte count on success, or a negative nuxel_io_status sentinel
 * via a separate out param. (We use a struct to keep errno out of the ABI.)
 */
enum nuxel_io_status nuxel_dev_read(struct nuxel_sipc_dev *d,
                                    uint8_t *buf, size_t cap,
                                    ssize_t *out_len);

/*
 * Write exactly `len` bytes (single SIPC FORMAT message: 7-byte FMT header +
 * payload). The kernel prepends the SIPC5 link header itself. Returns OK on a
 * full write, or a negative nuxel_io_status. Writes are REFUSED unless
 * the device was opened for write and the caller is allowed by policy.
 */
enum nuxel_io_status nuxel_dev_write(struct nuxel_sipc_dev *d,
                                     const uint8_t *msg, size_t len);

/* Non-blocking poll hint for the event loop: 1 if POLLIN/POLLHUP. */
enum nuxel_io_status nuxel_dev_poll(struct nuxel_sipc_dev *d, int timeout_ms);

const char *nuxel_io_status_name(enum nuxel_io_status s);

#ifdef __cplusplus
}
#endif
#endif /* NUXEL_TRANSPORT_H */
