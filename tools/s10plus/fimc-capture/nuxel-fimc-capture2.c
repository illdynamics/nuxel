/*
 * nuxel-fimc-capture2 — Samsung FIMC-IS2 (Exynos9820) MPLANE capture probe.
 *
 * Difference vs nuxel-fimc-capture.c: the FIMC-IS2 driver's
 * vidioc_g_fmt_vid_cap_mplane() is a STUB (returns 0 without filling the
 * struct), so G_FMT must not be treated as authoritative.  Instead we use
 * TRY_FMT to negotiate, S_FMT to commit, and then trust the plane layout the
 * driver's fimc_is_formats[] table defines: YUYV == 1 image plane + 1 meta
 * plane (SIZE_OF_META_PLANE == 32 KiB).  This tool:
 *   - does QUERYCAP, S_INPUT, TRY_FMT, S_FMT (not G_FMT-gated),
 *   - REQBUFS/QUERYBUF/QBUF/STREAMON/DQBUF with the META plane accounted,
 *   - treats every payload byte count + variation as evidence only.
 * It never fabricates frames.
 */
#define _GNU_SOURCE
#include <errno.h>
#include <fcntl.h>
#include <poll.h>
#include <stdio.h>
#include <stdint.h>
#include <stdlib.h>
#include <string.h>
#include <sys/ioctl.h>
#include <sys/mman.h>
#include <sys/stat.h>
#include <sys/time.h>
#include <time.h>
#include <unistd.h>
#include <linux/videodev2.h>

#define MAX_BUFS 32
#define MAX_PLANES 8
#define META_PLANE_SIZE (32*1024)

struct opts {
    const char *node;
    const char *raw;
    const char *fourcc;
    unsigned input;
    unsigned width, height;
    unsigned buffers, frames, timeout_ms;
    int json;
    int try_only;
    int allow_sensor;
};

static struct opts O = {
    .node = NULL, .raw = NULL, .fourcc = "YUYV",
    .input = 0, .width = 1440, .height = 1080,
    .buffers = 4, .frames = 1, .timeout_ms = 3000,
};

static const char *stage = "none";
static int last_errno = 0;

static uint32_t fourcc_of(const char *s) {
    if (!s || strlen(s) != 4) return 0;
    return v4l2_fourcc(s[0], s[1], s[2], s[3]);
}

static int do_ioctl(int fd, unsigned long req, void *arg, const char *name) {
    int ret;
    stage = name;
    errno = 0;
    ret = ioctl(fd, req, arg);
    last_errno = ret < 0 ? errno : 0;
    return ret;
}

static void jstr(const char *s) {
    putchar('"');
    for (; s && *s; s++) {
        if (*s == '"' || *s == '\\') printf("\\%c", *s);
        else if (*s == '\n') fputs("\\n", stdout);
        else if ((unsigned char)*s < 0x20) printf("\\u%04x", *s);
        else putchar(*s);
    }
    putchar('"');
}

static unsigned long long now_ms(void){ struct timespec ts; clock_gettime(CLOCK_MONOTONIC,&ts); return ts.tv_sec*1000ULL+ts.tv_nsec/1000000ULL; }

static void emit(int ok, const char *verdict, unsigned frames, unsigned long long bytes,
                 struct v4l2_capability *cap, struct v4l2_pix_format_mplane *pix,
                 const char *detail) {
    printf("{\"tool\":\"nuxel-fimc-capture2\",\"node\":");
    jstr(O.node);
    printf(",\"ok\":%s,\"verdict\":", ok ? "true" : "false");
    jstr(verdict);
    printf(",\"physical_frame_verified\":false,\"stage\":");
    jstr(stage);
    printf(",\"errno\":%d,\"frames\":%u,\"bytes\":%llu", last_errno, frames, bytes);
    if (cap) {
        char drv[17] = {0}, card[33] = {0}, bus[33] = {0};
        memcpy(drv, cap->driver, 16); memcpy(card, cap->card, 32); memcpy(bus, cap->bus_info, 32);
        printf(",\"driver\":"); jstr(drv);
        printf(",\"card\":"); jstr(card);
        printf(",\"bus_info\":"); jstr(bus);
        printf(",\"caps\":\"0x%08x\"", cap->capabilities);
    }
    if (pix) {
        char fcc[5] = {0};
        fcc[0] = pix->pixelformat & 0xff; fcc[1] = (pix->pixelformat>>8)&0xff;
        fcc[2] = (pix->pixelformat>>16)&0xff; fcc[3] = (pix->pixelformat>>24)&0xff;
        printf(",\"fourcc\":"); jstr(fcc);
        printf(",\"width\":%u,\"height\":%u,\"num_planes\":%u,\"sizeimage0\":%u,\"sizeimage1\":%u",
               pix->width, pix->height, pix->num_planes,
               pix->plane_fmt[0].sizeimage,
               pix->num_planes > 1 ? pix->plane_fmt[1].sizeimage : 0);
    }
    printf(",\"detail\":"); jstr(detail ? detail : "");
    printf("}\n");
}

int main(int argc, char **argv) {
    int i;
    for (i = 1; i < argc; i++) {
        const char *a = argv[i];
        const char *v = (i+1 < argc) ? argv[i+1] : NULL;
        if (!strcmp(a, "--node") && v) { O.node = v; i++; }
        else if (!strcmp(a, "--raw") && v) { O.raw = v; i++; }
        else if (!strcmp(a, "--fourcc") && v) { O.fourcc = v; i++; }
        else if (!strcmp(a, "--input") && v) { O.input = strtoul(v, NULL, 0); i++; }
        else if (!strcmp(a, "--width") && v) { O.width = strtoul(v, NULL, 0); i++; }
        else if (!strcmp(a, "--height") && v) { O.height = strtoul(v, NULL, 0); i++; }
        else if (!strcmp(a, "--buffers") && v) { O.buffers = strtoul(v, NULL, 0); i++; }
        else if (!strcmp(a, "--frames") && v) { O.frames = strtoul(v, NULL, 0); i++; }
        else if (!strcmp(a, "--timeout") && v) { O.timeout_ms = strtoul(v, NULL, 0); i++; }
        else if (!strcmp(a, "--json")) { O.json = 1; }
        else if (!strcmp(a, "--try-only")) { O.try_only = 1; }
        else if (!strcmp(a, "--allow-sensor")) { O.allow_sensor = 1; }
        else { fprintf(stderr, "unknown: %s\n", a); return 2; }
    }
    if (!O.node) { fprintf(stderr, "usage: --node /dev/videoN ...\n"); return 2; }

    int fd = open(O.node, O_RDWR | O_NONBLOCK);
    if (fd < 0) { last_errno = errno; stage = "open"; emit(0, "OPEN_FAILED", 0, 0, NULL, NULL, strerror(errno)); return 4; }

    struct v4l2_capability cap; memset(&cap, 0, sizeof cap);
    stage = "QUERYCAP";
    if (do_ioctl(fd, VIDIOC_QUERYCAP, &cap, stage) < 0) {
        emit(0, "QUERYCAP_FAILED", 0, 0, NULL, NULL, "QUERYCAP rejected"); close(fd); return 4;
    }
    uint32_t dcaps = (cap.capabilities & V4L2_CAP_DEVICE_CAPS) ? cap.device_caps : cap.capabilities;

    /* S_INPUT (required before S_FMT on FIMC-IS). */
    stage = "S_INPUT";
    unsigned inp = O.input;
    if (!O.allow_sensor) {
        /* still try; sensor select may be governed by a separate node */
    }
    if (do_ioctl(fd, VIDIOC_S_INPUT, &inp, stage) < 0) {
        emit(0, "S_INPUT_FAILED", 0, 0, &cap, NULL, "S_INPUT rejected; try --allow-sensor and check sensor node first"); close(fd); return 4;
    }

    struct v4l2_format fmt; memset(&fmt, 0, sizeof fmt);
    fmt.type = V4L2_BUF_TYPE_VIDEO_CAPTURE_MPLANE;
    fmt.fmt.pix_mp.width = O.width;
    fmt.fmt.pix_mp.height = O.height;
    fmt.fmt.pix_mp.pixelformat = fourcc_of(O.fourcc);
    fmt.fmt.pix_mp.field = V4L2_FIELD_NONE;
    fmt.fmt.pix_mp.colorspace = V4L2_COLORSPACE_JPEG;
    fmt.fmt.pix_mp.num_planes = 1;

    stage = "TRY_FMT";
    if (do_ioctl(fd, VIDIOC_TRY_FMT, &fmt, stage) < 0) {
        emit(0, "TRY_FMT_FAILED", 0, 0, &cap, NULL, "TRY_FMT rejected (fourcc/size unsupported?)"); close(fd); return 4;
    }
    /* TRY_FMT may not fill on FIMC-IS either; fall back to known table. */
    unsigned num_planes = fmt.fmt.pix_mp.num_planes;
    if (num_planes == 0 || num_planes > MAX_PLANES) num_planes = 2; /* image + meta */

    if (O.try_only) {
        emit(1, "TRY_FMT_OK", 0, 0, &cap, &fmt.fmt.pix_mp, "TRY_FMT accepted");
        close(fd); return 0;
    }

    /* S_FMT commit */
    fmt.fmt.pix_mp.num_planes = num_planes;
    stage = "S_FMT";
    if (do_ioctl(fd, VIDIOC_S_FMT, &fmt, stage) < 0) {
        emit(0, "S_FMT_FAILED", 0, 0, &cap, &fmt.fmt.pix_mp, "S_FMT rejected"); close(fd); return 4;
    }
    /* Use committed values; driver keeps format internally. */
    unsigned width = fmt.fmt.pix_mp.width;
    unsigned height = fmt.fmt.pix_mp.height;
    if (!width || !height) { width = O.width; height = O.height; }

    /* Compute plane sizes (image plane + meta plane). */
    /* YUYV: 2 bytes/pixel; meta 32KB */
    unsigned size_img = width * height * 2;
    unsigned size_meta = META_PLANE_SIZE;
    if (fmt.fmt.pix_mp.plane_fmt[0].sizeimage) size_img = fmt.fmt.pix_mp.plane_fmt[0].sizeimage;

    struct v4l2_requestbuffers req; memset(&req, 0, sizeof req);
    req.count = O.buffers;
    req.type = V4L2_BUF_TYPE_VIDEO_CAPTURE_MPLANE;
    req.memory = V4L2_MEMORY_MMAP;
    stage = "REQBUFS";
    if (do_ioctl(fd, VIDIOC_REQBUFS, &req, stage) < 0 || req.count == 0) {
        emit(0, "REQBUFS_FAILED", 0, 0, &cap, &fmt.fmt.pix_mp, "REQBUFS rejected"); close(fd); return 4;
    }

    struct v4l2_buffer bufs[MAX_BUFS];
    struct v4l2_plane planes[MAX_BUFS][MAX_PLANES];
    void *maps[MAX_BUFS][MAX_PLANES] = {{0}};
    size_t maplens[MAX_BUFS][MAX_PLANES] = {{0}};

    int q;
    for (q = 0; q < (int)req.count; q++) {
        memset(&bufs[q], 0, sizeof bufs[q]);
        memset(&planes[q], 0, sizeof planes[q]);
        bufs[q].index = q;
        bufs[q].type = V4L2_BUF_TYPE_VIDEO_CAPTURE_MPLANE;
        bufs[q].memory = V4L2_MEMORY_MMAP;
        bufs[q].m.planes = planes[q];
        bufs[q].length = MAX_PLANES;
        stage = "QUERYBUF";
        if (do_ioctl(fd, VIDIOC_QUERYBUF, &bufs[q], stage) < 0) {
            emit(0, "QUERYBUF_FAILED", 0, 0, &cap, &fmt.fmt.pix_mp, "QUERYBUF rejected"); goto fail;
        }
        /* Map each plane the driver reports. */
        unsigned npl = bufs[q].length;
        if (npl > MAX_PLANES) npl = MAX_PLANES;
        for (unsigned p = 0; p < npl; p++) {
            unsigned len = planes[q][p].length;
            /* If driver under-reports meta plane length, use expected. */
            if (p == 1 && (len < size_meta)) len = size_meta;
            if (len == 0) continue;
            void *m = mmap(NULL, len, PROT_READ|PROT_WRITE, MAP_SHARED, fd, planes[q][p].m.mem_offset);
            if (m == MAP_FAILED) {
                last_errno = errno;
                emit(0, "MMAP_FAILED", 0, 0, &cap, &fmt.fmt.pix_mp, "mmap failed"); goto fail;
            }
            maps[q][p] = m; maplens[q][p] = len;
        }
    }

    for (q = 0; q < (int)req.count; q++) {
        stage = "QBUF";
        if (do_ioctl(fd, VIDIOC_QBUF, &bufs[q], stage) < 0) {
            emit(0, "QBUF_FAILED", 0, 0, &cap, &fmt.fmt.pix_mp, "QBUF rejected"); goto fail;
        }
    }

    enum v4l2_buf_type btype = V4L2_BUF_TYPE_VIDEO_CAPTURE_MPLANE;
    stage = "STREAMON";
    if (do_ioctl(fd, VIDIOC_STREAMON, &btype, stage) < 0) {
        emit(0, "STREAMON_FAILED", 0, 0, &cap, &fmt.fmt.pix_mp, "STREAMON rejected"); goto fail;
    }

    unsigned framed = 0, total = 0;
    unsigned long long deadline = 0;
    unsigned long long t0 = 0, tN = 0;

    while (framed < O.frames) {
        if (!deadline) deadline = now_ms() + O.timeout_ms;
        struct pollfd pfd = { .fd = fd, .events = POLLIN };
        unsigned long long t = now_ms();
        if (t >= deadline) {
            last_errno = ETIMEDOUT;
            if (!framed) { emit(0, "NO_FRAME_TIMEOUT", 0, total, &cap, &fmt.fmt.pix_mp, "STREAMON ok but no DQBUF before timeout"); goto fail; }
            goto done;
        }
        int pr = poll(&pfd, 1, (int)(deadline - t > 100 ? 100 : deadline - t));
        if (pr < 0 && errno != EINTR) { last_errno = errno; emit(0,"POLL_FAILED",framed,total,&cap,&fmt.fmt.pix_mp,"poll failed"); goto fail; }
        if (!(pr > 0 && (pfd.revents & (POLLIN|POLLRDNORM)))) continue;

        struct v4l2_buffer dq; struct v4l2_plane dp[MAX_PLANES];
        memset(&dq, 0, sizeof dq); memset(dp, 0, sizeof dp);
        dq.type = V4L2_BUF_TYPE_VIDEO_CAPTURE_MPLANE;
        dq.memory = V4L2_MEMORY_MMAP;
        dq.m.planes = dp; dq.length = MAX_PLANES;
        stage = "DQBUF";
        if (do_ioctl(fd, VIDIOC_DQBUF, &dq, stage) < 0) {
            if (errno == EAGAIN) { /* requeue needs re-qbuf */
                continue;
            }
            emit(0, "DQBUF_FAILED", framed, total, &cap, &fmt.fmt.pix_mp, "DQBUF rejected"); goto fail;
        }
        if (dq.index >= req.count) { last_errno = EINVAL; emit(0,"DQBUF_BAD_INDEX",framed,total,&cap,&fmt.fmt.pix_mp,"bad index"); goto fail; }
        unsigned bytesused = dp[0].bytesused;
        unsigned offset0 = dp[0].data_offset;
        if (dq.flags & V4L2_BUF_FLAG_ERROR) {
            /* some FIMC-IS frames carry ERROR flag but still deliver; record honestly */
        }
        const unsigned char *payload = (const unsigned char*)maps[dq.index][0] + offset0;
        /* variation check on image plane */
        int varied = 0;
        for (unsigned k = 1; k < bytesused && k < (unsigned)maplens[dq.index][0]; k++)
            if (payload[k] != payload[0]) { varied = 1; break; }
        unsigned long long tsnow = now_ms();
        if (!framed) t0 = tsnow; tN = tsnow;
        if (O.raw && bytesused) {
            FILE *rf = fopen(O.raw, framed == 0 ? "wb" : "ab");
            if (rf) { fwrite(payload, 1, bytesused, rf); fclose(rf); }
        }
        fprintf(stderr, "DQBUF idx=%u seq=%u bytesused=%u varied=%d flags=0x%x ts=%lld.%06ld\n",
                dq.index, dq.sequence, bytesused, varied, dq.flags,
                (long long)dq.timestamp.tv_sec, (long)dq.timestamp.tv_usec);
        framed++; total += bytesused;
        if (O.raw == NULL) deadline = 0; /* next frame */
        /* requeue */
        stage = "QBUF(requeue)";
        if (do_ioctl(fd, VIDIOC_QBUF, &dq, stage) < 0) { emit(0,"REQUEUE_FAILED",framed,total,&cap,&fmt.fmt.pix_mp,"requeue failed"); goto fail; }
    }

done:
    stage = "STREAMOFF";
    do_ioctl(fd, VIDIOC_STREAMOFF, &btype, stage);
    emit(framed > 0, framed > 0 ? "FRAMES_CAPTURED" : "NO_FRAME", framed, total, &cap, &fmt.fmt.pix_mp,
         framed > 0 ? "dequeued payload(s); scene correlation still required" : "no frame dequeued");
    close(fd);
    return framed > 0 ? 0 : 3;

fail:
    do_ioctl(fd, VIDIOC_STREAMOFF, &btype, "cleanup-STREAMOFF");
    for (q = 0; q < (int)req.count; q++)
        for (unsigned p = 0; p < MAX_PLANES; p++)
            if (maps[q][p]) munmap(maps[q][p], maplens[q][p]);
    close(fd);
    return 4;
}
