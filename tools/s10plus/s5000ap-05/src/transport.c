/* transport.c — SIPC5 device transport. GPL-2.0-only. */
#define _GNU_SOURCE
#include "transport.h"

#include <errno.h>
#include <fcntl.h>
#include <poll.h>
#include <string.h>
#include <sys/file.h>
#include <sys/stat.h>
#include <unistd.h>

static void copy_node(char *dst, size_t cap, const char *src)
{
    size_t n = 0;
    if (!dst || cap == 0) return;
    if (src) { while (src[n] && n + 1 < cap) { dst[n] = src[n]; n++; } }
    dst[n] = '\0';
}

int nuxel_dev_open(struct nuxel_sipc_dev *d, const char *node,
                   uint8_t ch_id, uint8_t format)
{
    if (!d || !node) return -EINVAL;
    memset(d, 0, sizeof(*d));
    d->fd = -1;
    copy_node(d->node, sizeof(d->node), node);
    d->ch_id = ch_id;
    d->format = format;

    int fd = open(node, O_RDWR | O_NONBLOCK | O_CLOEXEC | O_NOCTTY);
    if (fd < 0) {
        /* Important: the umts misc nodes may not allow O_RDWR when the CP is
         * offline. Retry O_RDONLY so a status-only daemon still starts; write
         * capability is gated separately. */
        fd = open(node, O_RDONLY | O_NONBLOCK | O_CLOEXEC | O_NOCTTY);
        if (fd < 0) return -errno;
    }
    /* Exclusive ownership: refuse to share an endpoint. If another owner holds
     * the lock we return -EWOULDBLOCK. */
    if (flock(fd, LOCK_EX | LOCK_NB) != 0) {
        int e = errno;
        close(fd);
        return -e;
    }
    d->fd = fd;
    d->locked = 1;
    return 0;
}

void nuxel_dev_close(struct nuxel_sipc_dev *d)
{
    if (!d) return;
    if (d->fd >= 0) {
        if (d->locked) (void)flock(d->fd, LOCK_UN);
        close(d->fd);
    }
    d->fd = -1;
    d->locked = 0;
}

enum nuxel_io_status nuxel_dev_read(struct nuxel_sipc_dev *d,
                                    uint8_t *buf, size_t cap,
                                    ssize_t *out_len)
{
    if (out_len) *out_len = 0;
    if (!d || d->fd < 0) return NUXEL_IO_DISCONNECTED;
    if (!buf || cap == 0) return NUXEL_IO_ERROR;
    if (cap > NUXEL_TR_MAX_FRAME) cap = NUXEL_TR_MAX_FRAME;
    for (;;) {
        ssize_t r = read(d->fd, buf, cap);
        if (r > 0) { if (out_len) *out_len = r; return NUXEL_IO_OK; }
        if (r == 0) return NUXEL_IO_NO_DATA;   /* misc_read: no skb -> 0 */
        if (errno == EAGAIN || errno == EWOULDBLOCK) return NUXEL_IO_NO_DATA;
        if (errno == EINTR) continue;
        if (errno == ENODEV || errno == EIO) return NUXEL_IO_DISCONNECTED;
        if (errno == EPERM || errno == EBUSY) return NUXEL_IO_PERMISSION;
        return NUXEL_IO_ERROR;
    }
}

enum nuxel_io_status nuxel_dev_write(struct nuxel_sipc_dev *d,
                                     const uint8_t *msg, size_t len)
{
    if (!d || d->fd < 0) return NUXEL_IO_DISCONNECTED;
    if (!msg || len == 0 || len > NUXEL_TR_MAX_FRAME) return NUXEL_IO_ERROR;
    for (;;) {
        ssize_t w = write(d->fd, msg, len);
        if (w == (ssize_t)len) return NUXEL_IO_OK;
        if (w < 0) {
            if (errno == EINTR) continue;
            if (errno == EAGAIN || errno == EWOULDBLOCK) return NUXEL_IO_WOULDBLOCK;
            if (errno == ENODEV || errno == EIO) return NUXEL_IO_DISCONNECTED;
            if (errno == EPERM || errno == EBUSY) return NUXEL_IO_PERMISSION;
            return NUXEL_IO_ERROR;
        }
        /* partial write: kernel misc_write is all-or-nothing per msg; treat as error */
        return NUXEL_IO_ERROR;
    }
}

enum nuxel_io_status nuxel_dev_poll(struct nuxel_sipc_dev *d, int timeout_ms)
{
    if (!d || d->fd < 0) return NUXEL_IO_DISCONNECTED;
    struct pollfd pfd = { .fd = d->fd, .events = POLLIN, .revents = 0 };
    int pr = poll(&pfd, 1, timeout_ms);
    if (pr < 0) return (errno == EINTR) ? NUXEL_IO_WOULDBLOCK : NUXEL_IO_ERROR;
    if (pr == 0) return NUXEL_IO_NO_DATA;
    if (pfd.revents & (POLLHUP | POLLERR | POLLNVAL)) return NUXEL_IO_DISCONNECTED;
    if (pfd.revents & POLLIN) return NUXEL_IO_OK;
    return NUXEL_IO_NO_DATA;
}

const char *nuxel_io_status_name(enum nuxel_io_status s)
{
    switch (s) {
    case NUXEL_IO_OK:           return "OK";
    case NUXEL_IO_NO_DATA:      return "NO_DATA";
    case NUXEL_IO_WOULDBLOCK:   return "WOULDBLOCK";
    case NUXEL_IO_DISCONNECTED: return "DISCONNECTED";
    case NUXEL_IO_PERMISSION:   return "PERMISSION";
    default:                    return "ERROR";
    }
}
