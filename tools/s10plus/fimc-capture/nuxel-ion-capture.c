/*
 * nuxel-ion-capture — Samsung FIMC-IS2 (Exynos9820) capture via ION DMABUF.
 *
 * The FIMC-IS2 driver (CONFIG_DMA_BUF_CONTAINER) manages capture buffers as
 * ION-allocated DMABUF fds.  Standard V4L2_MEMORY_MMAP QBUF fails with
 * "failed to get dmabuf of fd: 0" in is_dbufcon_prepare.  The correct flow is:
 *   1. open /dev/ion, ION_IOC_ALLOC from camera_contig_heap (id 4) / camera_heap (id 5)
 *      -> returns a DMABUF fd directly in ion_allocation_data.fd
 *   2. VIDIOC_QBUF with V4L2_MEMORY_DMABUF and buf->m.planes[p].m.fd = that fd
 *   3. mmap the SAME dmabuf fd in userspace to read the pixels back
 *
 * Heaps observed on this device (kernel 4.14.253):
 *   camera_contig_heap id=4 type=2 (DMA, 14.6 MB)  -> contiguous, use for capture
 *   camera_heap        id=5 type=6 (DMA-BUF)
 *   secure_camera_heap id=3 type=2 (protected)
 *
 * This tool is physical-frame evidence only; it never fabricates pixels.
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

/* --- Samsung 4.14 ION UAPI (Samsung modifications return fd in .fd) --- */
#define ION_IOC_MAGIC 'I'
struct ion_allocation_data {
    uint64_t len;
    uint32_t heap_id_mask;
    uint32_t flags;
    uint32_t fd;
    uint32_t unused;
};
#define ION_FLAG_CACHED 1
/* ION_IOC_ALLOC = _IOWR('I', 0, struct ion_allocation_data{24 bytes})
 * = 0xC0000000 | ('I'<<8 = 0x4900) | (0) | (24<<16 = 0x180000)
 * = 0xC0184900
 */
#define ION_IOC_ALLOC 0xC0184900UL

#define CAMERA_CONTIG_HEAP_ID 4
#define CAMERA_HEAP_ID 5
#define MAX_BUFS 4
#define MAX_PLANES 8

struct opts {
    const char *node;
    const char *raw;
    int heap_id;
    unsigned width, height, buffers, frames, timeout_ms;
    int json;
};

static struct opts O = {
    .node = NULL, .raw = NULL, .heap_id = CAMERA_CONTIG_HEAP_ID,
    .width = 1440, .height = 1080, .buffers = 4, .frames = 1, .timeout_ms = 3000,
};

static const char *stage = "none";
static int last_errno = 0;

static int do_ioctl(int fd, unsigned long req, void *arg, const char *name) {
    stage = name; errno = 0;
    int ret = ioctl(fd, req, arg);
    last_errno = ret < 0 ? errno : 0;
    return ret;
}

int main(int argc, char **argv) {
    int i;
    for (i = 1; i < argc; i++) {
        const char *a = argv[i], *v = (i+1<argc)?argv[i+1]:NULL;
        if (!strcmp(a,"--node")&&v){O.node=v;i++;}
        else if (!strcmp(a,"--raw")&&v){O.raw=v;i++;}
        else if (!strcmp(a,"--heap")&&v){O.heap_id=strtol(v,NULL,0);i++;}
        else if (!strcmp(a,"--width")&&v){O.width=strtoul(v,NULL,0);i++;}
        else if (!strcmp(a,"--height")&&v){O.height=strtoul(v,NULL,0);i++;}
        else if (!strcmp(a,"--buffers")&&v){O.buffers=strtoul(v,NULL,0);i++;}
        else if (!strcmp(a,"--frames")&&v){O.frames=strtoul(v,NULL,0);i++;}
        else if (!strcmp(a,"--timeout")&&v){O.timeout_ms=strtoul(v,NULL,0);i++;}
        else if (!strcmp(a,"--json")){O.json=1;}
        else { fprintf(stderr,"unknown: %s\n",a); return 2; }
    }
    if (!O.node) { fprintf(stderr,"usage: --node /dev/videoN [--heap 4|5]\n"); return 2; }

    /* 1. allocate ION DMABUF */
    int ionfd = open("/dev/ion", O_RDWR);
    if (ionfd < 0) { fprintf(stderr,"[%s] open /dev/ion: %s\n", stage="ion_open", strerror(errno)); return 4; }

    unsigned img_size = O.width * O.height * 2; /* YUYV 2 bytes/px */
    int heap_mask = 1u << O.heap_id;
    int ionfds[MAX_BUFS]; void *ionmaps[MAX_BUFS];
    for (i = 0; i < (int)O.buffers; i++) {
        struct ion_allocation_data ad; memset(&ad, 0, sizeof ad);
        ad.len = img_size; ad.heap_id_mask = heap_mask; ad.flags = ION_FLAG_CACHED;
        stage = "ion_alloc";
        if (do_ioctl(ionfd, ION_IOC_ALLOC, &ad, stage) < 0 || ad.fd < 0) {
            fprintf(stderr,"[ion_alloc] heap %d size %u failed: %s (ret fd=%d)\n",
                    O.heap_id, img_size, strerror(last_errno), ad.fd);
            return 4;
        }
        ionfds[i] = ad.fd;
        ionmaps[i] = mmap(NULL, img_size, PROT_READ|PROT_WRITE, MAP_SHARED, ad.fd, 0);
        if (ionmaps[i] == MAP_FAILED) {
            fprintf(stderr,"[ion_mmap] fd %d: %s\n", ad.fd, strerror(errno));
            return 4;
        }
        fprintf(stderr,"[ion] buf %d: fd=%d heap_id=%d size=%u\n", i, ad.fd, O.heap_id, img_size);
    }

    /* 2. open capture node */
    int fd = open(O.node, O_RDWR | O_NONBLOCK);
    if (fd < 0) { last_errno = errno; stage = "open"; fprintf(stderr,"[open] %s\n", strerror(errno)); return 4; }

    struct v4l2_capability cap; memset(&cap,0,sizeof cap);
    stage = "QUERYCAP";
    if (do_ioctl(fd, VIDIOC_QUERYCAP, &cap, stage) < 0) { fprintf(stderr,"[QUERYCAP] %s\n", strerror(last_errno)); return 4; }
    fprintf(stderr,"[QUERYCAP] card=%.32s caps=0x%08x\n", cap.card, cap.capabilities);

    /* S_INPUT (rear=0) */
    unsigned inp = 0;
    stage = "S_INPUT";
    if (do_ioctl(fd, VIDIOC_S_INPUT, &inp, stage) < 0) { fprintf(stderr,"[S_INPUT] %s\n", strerror(last_errno)); return 4; }

    /* S_FMT MPLANE */
    struct v4l2_format fmt; memset(&fmt,0,sizeof fmt);
    fmt.type = V4L2_BUF_TYPE_VIDEO_CAPTURE_MPLANE;
    fmt.fmt.pix_mp.width = O.width; fmt.fmt.pix_mp.height = O.height;
    fmt.fmt.pix_mp.pixelformat = V4L2_PIX_FMT_YUYV;
    fmt.fmt.pix_mp.field = V4L2_FIELD_NONE;
    fmt.fmt.pix_mp.colorspace = V4L2_COLORSPACE_JPEG;
    fmt.fmt.pix_mp.num_planes = 2; /* image + meta */
    stage = "S_FMT";
    if (do_ioctl(fd, VIDIOC_S_FMT, &fmt, stage) < 0) { fprintf(stderr,"[S_FMT] %s\n", strerror(last_errno)); return 4; }
    fprintf(stderr,"[S_FMT] OK w=%u h=%u planes=%u fourcc=0x%08x\n",
            fmt.fmt.pix_mp.width, fmt.fmt.pix_mp.height, fmt.fmt.pix_mp.num_planes, fmt.fmt.pix_mp.pixelformat);

    /* REQBUFS DMABUF */
    struct v4l2_requestbuffers req; memset(&req,0,sizeof req);
    req.count = O.buffers; req.type = V4L2_BUF_TYPE_VIDEO_CAPTURE_MPLANE; req.memory = V4L2_MEMORY_DMABUF;
    stage = "REQBUFS";
    if (do_ioctl(fd, VIDIOC_REQBUFS, &req, stage) < 0 || req.count == 0) { fprintf(stderr,"[REQBUFS] %s\n", strerror(last_errno)); return 4; }

    /* QUERYBUF + attach dmabuf fd + QBUF */
    struct v4l2_buffer bufs[MAX_BUFS]; struct v4l2_plane pl[MAX_BUFS][MAX_PLANES];
    for (i = 0; i < (int)req.count; i++) {
        memset(&bufs[i], 0, sizeof bufs[i]); memset(&pl[i], 0, sizeof pl[i]);
        bufs[i].index = i; bufs[i].type = V4L2_BUF_TYPE_VIDEO_CAPTURE_MPLANE; bufs[i].memory = V4L2_MEMORY_DMABUF;
        bufs[i].m.planes = pl[i]; bufs[i].length = MAX_PLANES;
        stage = "QUERYBUF";
        if (do_ioctl(fd, VIDIOC_QUERYBUF, &bufs[i], stage) < 0) { fprintf(stderr,"[QUERYBUF %d] %s\n", i, strerror(last_errno)); return 4; }
        unsigned npl = bufs[i].length; if (npl > MAX_PLANES) npl = MAX_PLANES;
        fprintf(stderr,"[QUERYBUF %d] planes=%u\n", i, npl);
        /* Attach our single DMABUF fd to image plane 0; meta plane 1 may need its own fd */
        pl[i][0].m.fd = ionfds[i];
        /* For plane 1 (meta), allocate a small ION buffer too */
        struct ion_allocation_data am; memset(&am,0,sizeof am);
        am.len = 32*1024; am.heap_id_mask = heap_mask; am.flags = 0;
        if (do_ioctl(ionfd, ION_IOC_ALLOC, &am, stage) < 0 || am.fd < 0) { fprintf(stderr,"[ion meta alloc] %s\n", strerror(last_errno)); return 4; }
        pl[i][1].m.fd = am.fd;
        bufs[i].m.planes = pl[i];
        stage = "QBUF";
        if (do_ioctl(fd, VIDIOC_QBUF, &bufs[i], stage) < 0) {
            fprintf(stderr,"[QBUF %d] %s\n", i, strerror(last_errno));
            return 4;
        }
        fprintf(stderr,"[QBUF %d] OK\n", i);
    }

    /* STREAMON */
    enum v4l2_buf_type btype = V4L2_BUF_TYPE_VIDEO_CAPTURE_MPLANE;
    stage = "STREAMON";
    if (do_ioctl(fd, VIDIOC_STREAMON, &btype, stage) < 0) { fprintf(stderr,"[STREAMON] %s\n", strerror(last_errno)); return 4; }

    /* DQBUF */
    unsigned framed = 0, total = 0;
    unsigned long long deadline = 0;
    while (framed < O.frames) {
        if (!deadline) { struct timespec ts; clock_gettime(CLOCK_MONOTONIC,&ts); deadline = ts.tv_sec*1000ULL+ts.tv_nsec/1000000ULL + O.timeout_ms; }
        struct timespec ts; clock_gettime(CLOCK_MONOTONIC,&ts);
        unsigned long long now = ts.tv_sec*1000ULL+ts.tv_nsec/1000000ULL;
        if (now >= deadline) { fprintf(stderr,"[DQBUF] timeout\n"); break; }
        struct pollfd pfd = { .fd = fd, .events = POLLIN };
        int pr = poll(&pfd, 1, 100);
        if (pr < 0 && errno != EINTR) { fprintf(stderr,"[poll] %s\n", strerror(errno)); break; }
        if (!(pr > 0 && (pfd.revents & (POLLIN|POLLRDNORM)))) continue;

        struct v4l2_buffer dq; struct v4l2_plane dpl[MAX_PLANES];
        memset(&dq,0,sizeof dq); memset(dpl,0,sizeof dpl);
        dq.type = V4L2_BUF_TYPE_VIDEO_CAPTURE_MPLANE; dq.memory = V4L2_MEMORY_DMABUF;
        dq.m.planes = dpl; dq.length = MAX_PLANES;
        stage = "DQBUF";
        if (do_ioctl(fd, VIDIOC_DQBUF, &dq, stage) < 0) {
            if (errno == EAGAIN) continue;
            fprintf(stderr,"[DQBUF] %s\n", strerror(last_errno)); break;
        }
        if (dq.index >= req.count) { fprintf(stderr,"[DQBUF] bad index %u\n", dq.index); break; }
        unsigned bytesused = dpl[0].bytesused;
        /* Read pixels from our mapped ION buffer (we mapped ionfds[dq.index]) */
        unsigned char *px = (unsigned char*)ionmaps[dq.index];
        int varied = 0;
        for (unsigned k = 1; k < bytesused && k < img_size; k++)
            if (px[k] != px[0]) { varied = 1; break; }
        if (O.raw && bytesused) {
            FILE *rf = fopen(O.raw, framed==0?"wb":"ab");
            if (rf) { fwrite(px, 1, bytesused, rf); fclose(rf); }
        }
        fprintf(stderr,"DQBUF idx=%u seq=%u bytesused=%u varied=%d flags=0x%x\n",
                dq.index, dq.sequence, bytesused, varied, dq.flags);
        framed++; total += bytesused;
        /* requeue */
        struct v4l2_buffer rb = dq; struct v4l2_plane rpl[MAX_PLANES];
        memcpy(rpl, dpl, sizeof rpl); rb.m.planes = rpl;
        rpl[0].m.fd = ionfds[dq.index]; rpl[1].m.fd = -1; /* keep meta fd? needs re-attach */
        do_ioctl(fd, VIDIOC_QBUF, &rb, "QBUF(requeue)");
    }

    stage = "STREAMOFF";
    do_ioctl(fd, VIDIOC_STREAMOFF, &btype, stage);
    fprintf(stderr, "RESULT frames=%u bytes=%u node=%s\n", framed, total, O.node);
    if (O.json) {
        printf("{\"tool\":\"nuxel-ion-capture\",\"node\":\"%s\",\"frames\":%u,\"bytes\":%u,\"ok\":%s,\"stage\":\"%s\",\"errno\":%d}\n",
               O.node, framed, total, framed>0?"true":"false", stage, last_errno);
    }
    close(fd); close(ionfd);
    return framed > 0 ? 0 : 3;
}
