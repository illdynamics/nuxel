/*
 * nuxel-mfc-decode — experimental Exynos 9820 vendor-ABI MFC decode helper
 *
 * PWNAGE-61000.  This is NOT a generic V4L2 M2M client.  The pinned Samsung
 * driver (drivers/media/platform/exynos/mfc) does not implement
 * VIDIOC_DECODER_CMD, V4L2_EVENT_SOURCE_CHANGE, MMAP or the stateless Request
 * API.  Its capture queue imports DMA-BUF fds; its output queue accepts
 * USERPTR/DMA-BUF.  This helper follows that vendor ABI:
 *
 *   1. S_FMT OUTPUT (H.264)              -> opens the MFC instance
 *   2. REQBUFS/QBUF/STREAMON OUTPUT      -> feed the elementary stream
 *   3. G_FMT CAPTURE                     -> wait for SEQ_DONE / get real size
 *   4. S_FMT/REQBUFS/QBUF/STREAMON CAPTURE (DMABUF via /dev/udmabuf)
 *   5. poll/DQBUF CAPTURE                -> decoded NV12M planes
 *   6. STREAMOFF/close                   -> clean teardown
 *
 * Safety:
 *   - resolves the node by exact sysfs identity, never by /dev/videoN guess;
 *   - refuses to run without --allow-hardware-open and an owner-approved
 *     safety receipt that names this exact node and firmware hash;
 *   - opens exactly one node, once;
 *   - the kernel patch (0008-mfc-firmware-fail-closed.patch) is what makes a
 *     missing firmware fail promptly.  A userspace alarm cannot rescue a task
 *     stuck in uninterruptible D state.
 *
 * Build (native aarch64 or cross):
 *   aarch64-linux-gnu-gcc -O2 -Wall -Wextra -o nuxel-mfc-decode \
 *       nuxel-mfc-decode.c
 *
 * Status: IMPLEMENTED, NOT_TESTED_ON_DEVICE.  Do not claim MFC proof from a
 * successful compile.
 */
#define _GNU_SOURCE
#include <errno.h>
#include <fcntl.h>
#include <getopt.h>
#include <limits.h>
#include <linux/videodev2.h>
#include <poll.h>
#include <signal.h>
#include <stdarg.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/ioctl.h>
#include <sys/mman.h>
#include <sys/stat.h>
#include <sys/types.h>
#include <unistd.h>

#define VERSION "1.0.0"
#define EXPECTED_DRIVER "s5p-mfc"
#define EXPECTED_COMPATIBLE "samsung,exynos-mfc"
#define EXPECTED_IP_VER "0x1300"
#define EXPECTED_PLATFORM "188d0000.mfc"
#define DECODER_SYSFS_NAME "s5p-mfc-dec0"
#define FIRMWARE_NAME "mfc_fw.bin"
#define FIRMWARE_SHA256 "f3802d34524f5919c16505c03b4cbfe184963f98787feed6232b643bda68b55f"
#define KERNEL_PATCH "0008-mfc-firmware-fail-closed.patch"

#define NUXEL_SYS_MEMFD_CREATE 279 /* aarch64 */
#ifndef PATH_MAX
#define PATH_MAX 4096
#endif
#define PATHBUF (PATH_MAX + 64)
#define SRC_BUF_COUNT 4
#define SRC_BUF_SIZE (2u * 1024u * 1024u)
#define CAP_BUF_COUNT_MIN 8
#define POLL_TIMEOUT_MS 10000
#define OPEN_ALARM_SECONDS 30

#ifndef V4L2_CID_MPEG_MFC_BASE
#define V4L2_CID_MPEG_MFC_BASE (V4L2_CTRL_CLASS_MPEG | 0x2000)
#endif
#ifndef V4L2_CID_MPEG_MFC51_BASE
#define V4L2_CID_MPEG_MFC51_BASE (V4L2_CTRL_CLASS_MPEG | 0x1100)
#endif
#ifndef V4L2_CID_MPEG_MFC51_VIDEO_DECODER_H264_DISPLAY_DELAY
#define V4L2_CID_MPEG_MFC51_VIDEO_DECODER_H264_DISPLAY_DELAY (V4L2_CID_MPEG_MFC51_BASE + 0)
#endif
#ifndef V4L2_CID_MPEG_VIDEO_DECODER_IMMEDIATE_DISPLAY
#define V4L2_CID_MPEG_VIDEO_DECODER_IMMEDIATE_DISPLAY (V4L2_CID_MPEG_MFC_BASE + 47)
#endif
#ifndef V4L2_CID_MPEG_VIDEO_DECODER_WAIT_DECODING_START
#define V4L2_CID_MPEG_VIDEO_DECODER_WAIT_DECODING_START (V4L2_CID_MPEG_MFC_BASE + 49)
#endif
#ifndef V4L2_CID_MPEG_MFC_SET_DYNAMIC_DPB_MODE
#define V4L2_CID_MPEG_MFC_SET_DYNAMIC_DPB_MODE (V4L2_CID_MPEG_MFC_BASE + 95)
#endif

/* Local copy of the pinned kernel's UAPI (include/uapi/linux/udmabuf.h). */
struct udmabuf_create_local {
    uint32_t memfd;
    uint32_t flags;
    uint64_t offset;
    uint64_t size;
};
#define NUXEL_UDMABUF_CREATE _IOW('u', 0x42, struct udmabuf_create_local)

struct options {
    const char *device;
    const char *input;
    const char *output;
    const char *receipt;
    unsigned width;
    unsigned height;
    unsigned max_frames;
    int allow_hardware_open;
    int query_only;
    int timeout_seconds;
};

struct cap_buffer {
    int memfd[2];
    int dmabuf_fd[2];
    void *map[2];
    size_t sizes[2];
    unsigned planes;
};

static volatile sig_atomic_t g_alarm;
static void alarm_handler(int sig) { (void)sig; g_alarm = 1; }

static void die(const char *what) {
    fprintf(stderr, "nuxel-mfc-decode: %s: %s\n", what, strerror(errno));
    exit(1);
}

static void fail(const char *fmt, ...) __attribute__((format(printf, 1, 2)));
static void fail(const char *fmt, ...) {
    va_list ap;
    va_start(ap, fmt);
    fprintf(stderr, "nuxel-mfc-decode: ");
    vfprintf(stderr, fmt, ap);
    fprintf(stderr, "\n");
    va_end(ap);
    exit(1);
}

static void info(const char *fmt, ...) __attribute__((format(printf, 1, 2)));
static void info(const char *fmt, ...) {
    va_list ap;
    va_start(ap, fmt);
    fprintf(stderr, "nuxel-mfc-decode: ");
    vfprintf(stderr, fmt, ap);
    fprintf(stderr, "\n");
    va_end(ap);
}

static int read_text(const char *path, char *buf, size_t n) {
    int fd = open(path, O_RDONLY | O_CLOEXEC);
    if (fd < 0) return -1;
    ssize_t r = read(fd, buf, n - 1);
    close(fd);
    if (r < 0) return -1;
    while (r > 0 && (buf[r - 1] == '\n' || buf[r - 1] == '\0' || buf[r - 1] == ' '))
        r--;
    buf[r] = '\0';
    return 0;
}

static uint32_t read_dt_u32(const char *path) {
    unsigned char b[4];
    int fd = open(path, O_RDONLY | O_CLOEXEC);
    if (fd < 0) return 0xffffffffu;
    if (read(fd, b, sizeof(b)) != (ssize_t)sizeof(b)) { close(fd); return 0xffffffffu; }
    close(fd);
    /* Device-tree cells are big-endian in the DTB. */
    return ((uint32_t)b[0] << 24) | ((uint32_t)b[1] << 16) |
           ((uint32_t)b[2] << 8) | (uint32_t)b[3];
}

static int read_file(const char *path, unsigned char **out, size_t *out_size) {
    int fd = open(path, O_RDONLY | O_CLOEXEC);
    if (fd < 0) return -1;
    struct stat st;
    if (fstat(fd, &st) < 0 || st.st_size <= 0) { close(fd); errno = EINVAL; return -1; }
    if ((uint64_t)st.st_size > 64u * 1024u * 1024u) { close(fd); errno = EFBIG; return -1; }
    unsigned char *p = malloc((size_t)st.st_size);
    if (!p) { close(fd); errno = ENOMEM; return -1; }
    size_t off = 0;
    while (off < (size_t)st.st_size) {
        ssize_t r = read(fd, p + off, (size_t)st.st_size - off);
        if (r < 0) { if (errno == EINTR) continue; free(p); close(fd); return -1; }
        if (r == 0) break;
        off += (size_t)r;
    }
    close(fd);
    *out = p;
    *out_size = off;
    return 0;
}

static int file_contains(const char *path, const char *needle) {
    unsigned char *data = NULL;
    size_t size = 0;
    if (read_file(path, &data, &size) < 0) return -1;
    int found = 0;
    if (strlen(needle) <= size) {
        for (size_t i = 0; i + strlen(needle) <= size; i++) {
            if (memcmp(data + i, needle, strlen(needle)) == 0) { found = 1; break; }
        }
    }
    free(data);
    return found;
}

static int verify_receipt(const char *path, const char *device) {
    /* Defense in depth; the Python diag performs strict JSON validation. */
    if (!path || access(path, R_OK) < 0) {
        fail("safety receipt missing/unreadable: %s", path ? path : "<none>");
        return -1;
    }
    if (file_contains(path, "\"owner_approved\": true") != 1 &&
        file_contains(path, "\"owner_approved\":true") != 1)
        fail("receipt lacks owner_approved:true");
    if (file_contains(path, "\"kernel_patch_applied\": true") != 1 &&
        file_contains(path, "\"kernel_patch_applied\":true") != 1)
        fail("receipt lacks kernel_patch_applied:true");
    if (file_contains(path, "\"missing_firmware_test\"") != 1) fail("receipt lacks missing_firmware_test");
    if (file_contains(path, "\"firmware_sha256\": \"" FIRMWARE_SHA256 "\"") != 1 &&
        file_contains(path, "\"firmware_sha256\":\"" FIRMWARE_SHA256 "\"") != 1)
        fail("receipt firmware_sha256 does not match the verified blob");
    if (file_contains(path, "\"kernel_patch\": \"" KERNEL_PATCH "\"") != 1 &&
        file_contains(path, "\"kernel_patch\":\"" KERNEL_PATCH "\"") != 1)
        fail("receipt kernel_patch does not match " KERNEL_PATCH);
    if (file_contains(path, device) != 1)
        fail("receipt does not name the exact decoder node %s", device);
    return 0;
}

static int resolve_identity(const char *device, char *sysfs_name, size_t n,
                            char *driver, size_t dn, char *compatible, size_t cn,
                            char *ipver, size_t in) {
    const char *base = strrchr(device, '/');
    base = base ? base + 1 : device;
    char cls[PATH_MAX], namep[PATHBUF], devp[PATHBUF], drvp[PATHBUF];
    snprintf(cls, sizeof(cls), "/sys/class/video4linux/%s", base);
    snprintf(namep, sizeof(namep), "%s/name", cls);
    snprintf(devp, sizeof(devp), "%s/device", cls);
    if (read_text(namep, sysfs_name, n) < 0) return -1;
    char devreal[PATHBUF];
    if (!realpath(devp, devreal)) return -1;
    const char *plat = strrchr(devreal, '/');
    plat = plat ? plat + 1 : devreal;
    snprintf(drvp, sizeof(drvp), "%s/driver", devreal);
    char drvreal[PATHBUF];
    if (!realpath(drvp, drvreal)) return -1;
    const char *drv = strrchr(drvreal, '/');
    drv = drv ? drv + 1 : drvreal;
    if (strlen(drv) >= dn) return -1;
    memcpy(driver, drv, strlen(drv) + 1);
    char of[PATHBUF];
    snprintf(of, sizeof(of), "%s/of_node", devreal);
    char comp[PATHBUF];
    snprintf(comp, sizeof(comp), "%s/compatible", of);
    if (read_text(comp, compatible, cn) < 0) compatible[0] = '\0';
    char ip[PATHBUF];
    snprintf(ip, sizeof(ip), "%s/ip_ver", of);
    uint32_t v = read_dt_u32(ip);
    if (v == 0xffffffffu) snprintf(ipver, in, "?");
    else snprintf(ipver, in, "0x%04x", v);
    if (strcmp(plat, EXPECTED_PLATFORM) != 0) return -1;
    if (strcmp(sysfs_name, DECODER_SYSFS_NAME) != 0) return -1;
    if (strcmp(driver, EXPECTED_DRIVER) != 0) return -1;
    if (strcmp(compatible, EXPECTED_COMPATIBLE) != 0) return -1;
    if (strcmp(ipver, EXPECTED_IP_VER) != 0) return -1;
    return 0;
}

static int create_udmabuf(size_t size, int *memfd_out, int *dmabuf_out, void **map_out) {
    size_t page = (size_t)sysconf(_SC_PAGESIZE);
    size_t aligned = (size + page - 1) & ~(page - 1);
    int memfd = (int)syscall(NUXEL_SYS_MEMFD_CREATE, "nuxel-mfc-cap", 0x0001u /* MFD_CLOEXEC */);
    if (memfd < 0) return -1;
    if (ftruncate(memfd, (off_t)aligned) < 0) { close(memfd); return -1; }
    int udev = open("/dev/udmabuf", O_RDWR | O_CLOEXEC);
    if (udev < 0) { close(memfd); return -1; }
    struct udmabuf_create_local req = {
        .memfd = (uint32_t)memfd,
        .flags = 0,
        .offset = 0,
        .size = aligned,
    };
    int dmabuf = ioctl(udev, NUXEL_UDMABUF_CREATE, &req);
    int saved = errno;
    close(udev);
    if (dmabuf < 0) { close(memfd); errno = saved; return -1; }
    void *map = mmap(NULL, aligned, PROT_READ | PROT_WRITE, MAP_SHARED, memfd, 0);
    if (map == MAP_FAILED) { close(dmabuf); close(memfd); return -1; }
    *memfd_out = memfd;
    *dmabuf_out = dmabuf;
    *map_out = map;
    return 0;
}

static uint32_t fnv1a(const void *data, size_t n) {
    const unsigned char *p = data;
    uint32_t h = 2166136261u;
    for (size_t i = 0; i < n; i++) { h ^= p[i]; h *= 16777619u; }
    return h;
}

static int xioctl(int fd, unsigned long req, void *arg, const char *what) {
    int r;
    do { r = ioctl(fd, req, arg); } while (r < 0 && errno == EINTR);
    if (r < 0) info("%s failed: %s", what, strerror(errno));
    return r;
}

static void set_ctrl_best_effort(int fd, uint32_t id, int32_t value) {
    struct v4l2_control c = { .id = id, .value = value };
    if (xioctl(fd, VIDIOC_S_CTRL, &c, "VIDIOC_S_CTRL") < 0)
        info("optional control 0x%08x=%d not accepted (continuing)", id, value);
}

static void set_fmt_out(int fd, unsigned w, unsigned h) {
    struct v4l2_format f;
    memset(&f, 0, sizeof(f));
    f.type = V4L2_BUF_TYPE_VIDEO_OUTPUT_MPLANE;
    f.fmt.pix_mp.width = w;
    f.fmt.pix_mp.height = h;
    f.fmt.pix_mp.pixelformat = V4L2_PIX_FMT_H264;
    f.fmt.pix_mp.field = V4L2_FIELD_NONE;
    f.fmt.pix_mp.num_planes = 1;
    f.fmt.pix_mp.plane_fmt[0].sizeimage = SRC_BUF_SIZE;
    if (xioctl(fd, VIDIOC_S_FMT, &f, "VIDIOC_S_FMT(OUTPUT/H264)") < 0)
        fail("S_FMT OUTPUT failed (the vendor driver opens the MFC instance here)");
    info("OUTPUT format: %ux%u fourcc=%c%c%c%c sizeimage=%u",
         f.fmt.pix_mp.width, f.fmt.pix_mp.height,
         (f.fmt.pix_mp.pixelformat >> 0) & 0xff, (f.fmt.pix_mp.pixelformat >> 8) & 0xff,
         (f.fmt.pix_mp.pixelformat >> 16) & 0xff, (f.fmt.pix_mp.pixelformat >> 24) & 0xff,
         f.fmt.pix_mp.plane_fmt[0].sizeimage);
}

static void set_fmt_cap(int fd, unsigned w, unsigned h, uint32_t fourcc, unsigned planes) {
    struct v4l2_format f;
    memset(&f, 0, sizeof(f));
    f.type = V4L2_BUF_TYPE_VIDEO_CAPTURE_MPLANE;
    f.fmt.pix_mp.width = w;
    f.fmt.pix_mp.height = h;
    f.fmt.pix_mp.pixelformat = fourcc;
    f.fmt.pix_mp.field = V4L2_FIELD_NONE;
    f.fmt.pix_mp.num_planes = planes ? planes : 2;
    f.fmt.pix_mp.plane_fmt[0].sizeimage = w * h;
    if (f.fmt.pix_mp.num_planes > 1)
        f.fmt.pix_mp.plane_fmt[1].sizeimage = w * h / 2;
    if (xioctl(fd, VIDIOC_S_FMT, &f, "VIDIOC_S_FMT(CAPTURE)") < 0)
        fail("S_FMT CAPTURE failed");
}

static int get_fmt_cap(int fd, struct v4l2_format *f) {
    memset(f, 0, sizeof(*f));
    f->type = V4L2_BUF_TYPE_VIDEO_CAPTURE_MPLANE;
    return xioctl(fd, VIDIOC_G_FMT, f, "VIDIOC_G_FMT(CAPTURE)");
}

static int reqbufs(int fd, enum v4l2_buf_type type, enum v4l2_memory mem, unsigned count) {
    struct v4l2_requestbuffers rb;
    memset(&rb, 0, sizeof(rb));
    rb.count = count;
    rb.type = type;
    rb.memory = mem;
    int r = xioctl(fd, VIDIOC_REQBUFS, &rb, "VIDIOC_REQBUFS");
    return r < 0 ? -1 : (int)rb.count;
}

static int qbuf_userptr(int fd, unsigned index, unsigned plane_count, void *ptr, size_t size, size_t bytesused) {
    struct v4l2_buffer b;
    struct v4l2_plane planes[4];
    memset(&b, 0, sizeof(b));
    memset(planes, 0, sizeof(planes));
    b.type = V4L2_BUF_TYPE_VIDEO_OUTPUT_MPLANE;
    b.memory = V4L2_MEMORY_USERPTR;
    b.index = index;
    b.length = plane_count;
    b.m.planes = planes;
    planes[0].m.userptr = (unsigned long)ptr;
    planes[0].length = (uint32_t)size;
    planes[0].bytesused = (uint32_t)bytesused;
    return xioctl(fd, VIDIOC_QBUF, &b, "VIDIOC_QBUF(OUTPUT)");
}

static int qbuf_dmabuf(int fd, unsigned index, unsigned plane_count, const int *fds, const size_t *sizes) {
    struct v4l2_buffer b;
    struct v4l2_plane planes[4];
    memset(&b, 0, sizeof(b));
    memset(planes, 0, sizeof(planes));
    b.type = V4L2_BUF_TYPE_VIDEO_CAPTURE_MPLANE;
    b.memory = V4L2_MEMORY_DMABUF;
    b.index = index;
    b.length = plane_count;
    b.m.planes = planes;
    for (unsigned i = 0; i < plane_count; i++) {
        planes[i].m.fd = fds[i];
        planes[i].length = (uint32_t)sizes[i];
        planes[i].bytesused = (uint32_t)sizes[i];
    }
    return xioctl(fd, VIDIOC_QBUF, &b, "VIDIOC_QBUF(CAPTURE)");
}

static int dqbuf(int fd, enum v4l2_buf_type type, enum v4l2_memory mem,
                 unsigned *index, unsigned *bytesused, unsigned *nplanes,
                 int *plane_fds, size_t *plane_sizes) {
    struct v4l2_buffer b;
    struct v4l2_plane planes[4];
    memset(&b, 0, sizeof(b));
    memset(planes, 0, sizeof(planes));
    b.type = type;
    b.memory = mem;
    b.length = 4;
    b.m.planes = planes;
    if (xioctl(fd, VIDIOC_DQBUF, &b, "VIDIOC_DQBUF") < 0) return -1;
    *index = b.index;
    *nplanes = b.length;
    if (bytesused && b.length > 0) *bytesused = planes[0].bytesused;
    for (unsigned i = 0; i < b.length && i < 4; i++) {
        if (plane_fds) plane_fds[i] = planes[i].m.fd;
        if (plane_sizes) plane_sizes[i] = planes[i].length;
    }
    return 0;
}

static int stream(int fd, unsigned long req, enum v4l2_buf_type type, const char *what) {
    return xioctl(fd, req, &type, what);
}

static int wait_readable(int fd, int timeout_ms) {
    struct pollfd p = { .fd = fd, .events = POLLIN | POLLERR | POLLHUP };
    int r;
    do { r = poll(&p, 1, timeout_ms); } while (r < 0 && errno == EINTR);
    return r;
}

struct src_buffer {
    void *ptr;
    int in_use;
};

static int feed_source(int fd, struct src_buffer *srcs, unsigned nsrc,
                       const unsigned char *data, size_t size, size_t *offset) {
    if (*offset >= size) return 0;
    for (unsigned i = 0; i < nsrc; i++) {
        if (srcs[i].in_use) continue;
        size_t chunk = size - *offset;
        if (chunk > SRC_BUF_SIZE) chunk = SRC_BUF_SIZE;
        memcpy(srcs[i].ptr, data + *offset, chunk);
        if (qbuf_userptr(fd, i, 1, srcs[i].ptr, SRC_BUF_SIZE, chunk) < 0)
            return -1;
        srcs[i].in_use = 1;
        *offset += chunk;
        return 1;
    }
    return -1; /* no free source buffer */
}

static int reclaim_source(int fd, struct src_buffer *srcs, unsigned nsrc) {
    unsigned index = 0, bytesused = 0, nplanes = 0;
    if (dqbuf(fd, V4L2_BUF_TYPE_VIDEO_OUTPUT_MPLANE, V4L2_MEMORY_USERPTR,
              &index, &bytesused, &nplanes, NULL, NULL) < 0)
        return 0;
    if (index < nsrc) srcs[index].in_use = 0;
    return 1;
}

static void print_caps(int fd) {
    struct v4l2_capability cap;
    memset(&cap, 0, sizeof(cap));
    if (xioctl(fd, VIDIOC_QUERYCAP, &cap, "VIDIOC_QUERYCAP") < 0)
        fail("QUERYCAP failed");
    info("driver=%s card=%s caps=0x%08x device_caps=0x%08x",
         cap.driver, cap.card, cap.capabilities, cap.device_caps);
    if (!(cap.device_caps & V4L2_CAP_VIDEO_OUTPUT_MPLANE) ||
        !(cap.device_caps & V4L2_CAP_VIDEO_CAPTURE_MPLANE) ||
        !(cap.device_caps & V4L2_CAP_STREAMING))
        fail("node does not advertise the expected OUTPUT/CAPTURE mplane + streaming caps");
    for (uint32_t type = V4L2_BUF_TYPE_VIDEO_OUTPUT_MPLANE;
         type <= V4L2_BUF_TYPE_VIDEO_CAPTURE_MPLANE; type++) {
        info("formats for type %u:", type);
        for (uint32_t index = 0; index < 64; index++) {
            struct v4l2_fmtdesc d;
            memset(&d, 0, sizeof(d));
            d.index = index;
            d.type = type;
            if (xioctl(fd, VIDIOC_ENUM_FMT, &d, "VIDIOC_ENUM_FMT") < 0) break;
            info("  [%u] %c%c%c%c  %s", index,
                 (d.pixelformat >> 0) & 0xff, (d.pixelformat >> 8) & 0xff,
                 (d.pixelformat >> 16) & 0xff, (d.pixelformat >> 24) & 0xff,
                 d.description);
        }
    }
}

static int run_decode(int fd, const struct options *o, const unsigned char *data, size_t size) {
    int ret = 1;
    FILE *out = NULL;
    struct src_buffer srcs[SRC_BUF_COUNT];
    struct cap_buffer caps[32];
    unsigned cap_count = 0;
    unsigned frames = 0;
    uint32_t checksum = 2166136261u;
    size_t offset = 0;
    int streaming_out = 0, streaming_cap = 0;
    unsigned final_w = 0, final_h = 0;

    memset(srcs, 0, sizeof(srcs));
    memset(caps, 0, sizeof(caps));
    for (unsigned i = 0; i < 32; i++) {
        caps[i].memfd[0] = caps[i].memfd[1] = -1;
        caps[i].dmabuf_fd[0] = caps[i].dmabuf_fd[1] = -1;
    }

    if (o->output) {
        out = fopen(o->output, "wb");
        if (!out) die("open output");
    }

    /* Vendor controls: best effort, never fatal except the device identity. */
    set_ctrl_best_effort(fd, V4L2_CID_MPEG_MFC51_VIDEO_DECODER_H264_DISPLAY_DELAY, 0);
    set_ctrl_best_effort(fd, V4L2_CID_MPEG_VIDEO_DECODER_IMMEDIATE_DISPLAY, 1);
    set_ctrl_best_effort(fd, V4L2_CID_MPEG_VIDEO_DECODER_WAIT_DECODING_START, 1);
    set_ctrl_best_effort(fd, V4L2_CID_MPEG_MFC_SET_DYNAMIC_DPB_MODE, 1);

    /* S_FMT OUTPUT opens the instance in this vendor driver. */
    set_fmt_out(fd, o->width, o->height);
    /* Seed CAPTURE format before header parsing. */
    set_fmt_cap(fd, o->width, o->height, V4L2_PIX_FMT_NV12M, 2);

    if (reqbufs(fd, V4L2_BUF_TYPE_VIDEO_OUTPUT_MPLANE, V4L2_MEMORY_USERPTR, SRC_BUF_COUNT) < 0)
        fail("REQBUFS OUTPUT failed");
    for (unsigned i = 0; i < SRC_BUF_COUNT; i++) {
        if (posix_memalign(&srcs[i].ptr, 4096, SRC_BUF_SIZE) != 0)
            fail("posix_memalign source buffer");
        memset(srcs[i].ptr, 0, SRC_BUF_SIZE);
    }

    /* Fill the source queue and start the OUTPUT queue. */
    for (unsigned i = 0; i < SRC_BUF_COUNT; i++) {
        int r = feed_source(fd, srcs, SRC_BUF_COUNT, data, size, &offset);
        if (r <= 0) break;
    }
    if (stream(fd, VIDIOC_STREAMON, V4L2_BUF_TYPE_VIDEO_OUTPUT_MPLANE, "STREAMON OUTPUT") < 0)
        fail("STREAMON OUTPUT failed");
    streaming_out = 1;

    /* Wait for header parsing: G_FMT CAPTURE blocks on SEQ_DONE. */
    struct v4l2_format cf;
    int have_cap_fmt = 0;
    for (unsigned attempt = 0; attempt < 20; attempt++) {
        int wr = wait_readable(fd, 2000);
        if (wr > 0) {
            while (reclaim_source(fd, srcs, SRC_BUF_COUNT)) { }
            while (feed_source(fd, srcs, SRC_BUF_COUNT, data, size, &offset) > 0) { }
        }
        if (get_fmt_cap(fd, &cf) == 0 && cf.fmt.pix_mp.width > 0 && cf.fmt.pix_mp.height > 0 &&
            cf.fmt.pix_mp.plane_fmt[0].sizeimage > 0) {
            have_cap_fmt = 1;
            break;
        }
        usleep(100000);
    }
    if (!have_cap_fmt)
        fail("G_FMT CAPTURE did not resolve (header/SEQ_DONE not completed; check the stream and dmesg)");

    final_w = cf.fmt.pix_mp.width;
    final_h = cf.fmt.pix_mp.height;
    uint32_t fourcc = cf.fmt.pix_mp.pixelformat ? cf.fmt.pix_mp.pixelformat : V4L2_PIX_FMT_NV12M;
    unsigned planes = cf.fmt.pix_mp.num_planes ? cf.fmt.pix_mp.num_planes : 2;
    if (planes > 2) fail("capture format has %u planes; this helper supports NV12M/NV12N (<=2)", planes);
    size_t plane_sizes[2] = {
        cf.fmt.pix_mp.plane_fmt[0].sizeimage,
        planes > 1 ? cf.fmt.pix_mp.plane_fmt[1].sizeimage : 0,
    };
    if (plane_sizes[0] == 0) fail("capture plane 0 size is zero");
    info("decoded format: %ux%u fourcc=%c%c%c%c planes=%u sizes=%zu/%zu",
         final_w, final_h,
         (fourcc >> 0) & 0xff, (fourcc >> 8) & 0xff,
         (fourcc >> 16) & 0xff, (fourcc >> 24) & 0xff,
         planes, plane_sizes[0], plane_sizes[1]);

    /* Re-apply the actual capture format, then request DMABUF buffers. */
    set_fmt_cap(fd, final_w, final_h, fourcc, planes);

    struct v4l2_control minc = { .id = V4L2_CID_MIN_BUFFERS_FOR_CAPTURE, .value = 0 };
    int min_buffers = CAP_BUF_COUNT_MIN;
    if (xioctl(fd, VIDIOC_G_CTRL, &minc, "VIDIOC_G_CTRL(MIN_BUFFERS)") == 0 &&
        minc.value > 0 && minc.value < 32)
        min_buffers = minc.value;
    cap_count = (unsigned)min_buffers;
    if (cap_count < CAP_BUF_COUNT_MIN) cap_count = CAP_BUF_COUNT_MIN;
    if (cap_count > 32) cap_count = 32;

    int got = reqbufs(fd, V4L2_BUF_TYPE_VIDEO_CAPTURE_MPLANE, V4L2_MEMORY_DMABUF, cap_count);
    if (got < 0) fail("REQBUFS CAPTURE failed (driver requires DMA-BUF and dpb_count >= %d)", min_buffers);
    cap_count = (unsigned)got;

    for (unsigned i = 0; i < cap_count; i++) {
        caps[i].planes = planes;
        for (unsigned p = 0; p < planes; p++) {
            caps[i].sizes[p] = plane_sizes[p];
            if (create_udmabuf(plane_sizes[p], &caps[i].memfd[p], &caps[i].dmabuf_fd[p], &caps[i].map[p]) < 0)
                fail("udmabuf allocation failed for capture plane %u (is /dev/udmabuf available?)", p);
        }
        if (qbuf_dmabuf(fd, i, planes, caps[i].dmabuf_fd, caps[i].sizes) < 0)
            fail("QBUF CAPTURE failed for buffer %u", i);
    }
    if (stream(fd, VIDIOC_STREAMON, V4L2_BUF_TYPE_VIDEO_CAPTURE_MPLANE, "STREAMON CAPTURE") < 0)
        fail("STREAMON CAPTURE failed");
    streaming_cap = 1;
    info("streaming: capture buffers=%u planes=%u", cap_count, planes);

    unsigned max_frames = o->max_frames ? o->max_frames : UINT_MAX;
    unsigned idle = 0;
    while (frames < max_frames && idle < 20) {
        int progress = 0;
        while (feed_source(fd, srcs, SRC_BUF_COUNT, data, size, &offset) > 0) { }
        int wr = wait_readable(fd, 2000);
        while (reclaim_source(fd, srcs, SRC_BUF_COUNT)) progress = 1;

        for (;;) {
            unsigned index = 0, bytesused = 0, nplanes = 0;
            if (dqbuf(fd, V4L2_BUF_TYPE_VIDEO_CAPTURE_MPLANE, V4L2_MEMORY_DMABUF,
                      &index, &bytesused, &nplanes, NULL, NULL) < 0)
                break;
            if (index >= cap_count) continue;
            for (unsigned p = 0; p < caps[index].planes; p++) {
                uint32_t h = fnv1a(caps[index].map[p], caps[index].sizes[p]);
                checksum = (checksum ^ h) * 16777619u;
                if (out)
                    fwrite(caps[index].map[p], 1, caps[index].sizes[p], out);
            }
            frames++;
            progress = 1;
            if (qbuf_dmabuf(fd, index, caps[index].planes,
                            caps[index].dmabuf_fd, caps[index].sizes) < 0)
                fail("re-QBUF CAPTURE failed for buffer %u", index);
            if (frames >= max_frames) break;
        }
        if (progress) idle = 0;
        else idle++;
        if (offset >= size && idle > 5) break;
        if (wr < 0 && errno != EINTR) break;
    }

    info("RESULT decoded_frames=%u checksum=0x%08x width=%u height=%u planes=%u",
         frames, checksum, final_w, final_h, planes);
    if (frames == 0) {
        info("no decoded frames: check the input stream, firmware ABI and dmesg");
        ret = 1;
    } else {
        ret = 0;
    }

    if (streaming_cap)
        stream(fd, VIDIOC_STREAMOFF, V4L2_BUF_TYPE_VIDEO_CAPTURE_MPLANE, "STREAMOFF CAPTURE");
    if (streaming_out)
        stream(fd, VIDIOC_STREAMOFF, V4L2_BUF_TYPE_VIDEO_OUTPUT_MPLANE, "STREAMOFF OUTPUT");
    for (unsigned i = 0; i < cap_count; i++) {
        for (unsigned p = 0; p < caps[i].planes; p++) {
            if (caps[i].map[p] && caps[i].map[p] != MAP_FAILED) {
                size_t page = (size_t)sysconf(_SC_PAGESIZE);
                size_t aligned = (caps[i].sizes[p] + page - 1) & ~(page - 1);
                munmap(caps[i].map[p], aligned);
            }
            if (caps[i].dmabuf_fd[p] >= 0) close(caps[i].dmabuf_fd[p]);
            if (caps[i].memfd[p] >= 0) close(caps[i].memfd[p]);
        }
    }
    for (unsigned i = 0; i < SRC_BUF_COUNT; i++) free(srcs[i].ptr);
    if (out) fclose(out);
    return ret;
}

static void usage(FILE *f) {
    fprintf(f,
        "usage: nuxel-mfc-decode --device /dev/videoN --allow-hardware-open \\\n"
        "                        --receipt FILE (--query-only | --input FILE --width W --height H)\n"
        "\n"
        "Experimental Exynos 9820 vendor-ABI MFC decode helper (PWNAGE-61000).\n"
        "This is NOT a generic V4L2 M2M client.  It requires --allow-hardware-open\n"
        "and an owner-approved safety receipt that names this exact node.\n"
        "\n"
        "  -d, --device PATH      exact decoder node (must be s5p-mfc-dec0)\n"
        "  -i, --input FILE       H.264 Annex-B elementary stream\n"
        "  -o, --output FILE      raw decoded NV12M planes (frame-major)\n"
        "  -W, --width N          coded width (SPS/presentation may override)\n"
        "  -H, --height N         coded height\n"
        "  -n, --max-frames N     stop after N decoded frames (default: until EOF/idle)\n"
        "  -t, --timeout SEC      userspace alarm (default 120; cannot rescue D state)\n"
        "  -R, --receipt FILE     safety receipt (default /etc/nuxel/mfc/safety-receipt.json)\n"
        "  -Q, --query-only       QUERYCAP + ENUM_FMT only, then close\n"
        "  -A, --allow-hardware-open  explicit opt-in (never implied)\n"
        "  -V, --version\n"
        "  -h, --help\n");
}

int main(int argc, char **argv) {
    struct options o;
    memset(&o, 0, sizeof(o));
    o.timeout_seconds = 120;

    static const struct option longopts[] = {
        { "device", required_argument, NULL, 'd' },
        { "input", required_argument, NULL, 'i' },
        { "output", required_argument, NULL, 'o' },
        { "width", required_argument, NULL, 'W' },
        { "height", required_argument, NULL, 'H' },
        { "max-frames", required_argument, NULL, 'n' },
        { "timeout", required_argument, NULL, 't' },
        { "receipt", required_argument, NULL, 'R' },
        { "query-only", no_argument, NULL, 'Q' },
        { "allow-hardware-open", no_argument, NULL, 'A' },
        { "version", no_argument, NULL, 'V' },
        { "help", no_argument, NULL, 'h' },
        { NULL, 0, NULL, 0 },
    };

    int c;
    while ((c = getopt_long(argc, argv, "d:i:o:W:H:n:t:R:QAVh", longopts, NULL)) != -1) {
        switch (c) {
        case 'd': o.device = optarg; break;
        case 'i': o.input = optarg; break;
        case 'o': o.output = optarg; break;
        case 'W': o.width = (unsigned)strtoul(optarg, NULL, 0); break;
        case 'H': o.height = (unsigned)strtoul(optarg, NULL, 0); break;
        case 'n': o.max_frames = (unsigned)strtoul(optarg, NULL, 0); break;
        case 't': o.timeout_seconds = atoi(optarg); break;
        case 'R': o.receipt = optarg; break;
        case 'Q': o.query_only = 1; break;
        case 'A': o.allow_hardware_open = 1; break;
        case 'V': printf("nuxel-mfc-decode %s\n", VERSION); return 0;
        case 'h': usage(stdout); return 0;
        default: usage(stderr); return 2;
        }
    }

    if (!o.allow_hardware_open) {
        fprintf(stderr, "nuxel-mfc-decode: REFUSED — --allow-hardware-open is required\n");
        return 2;
    }
    if (!o.device) {
        fprintf(stderr, "nuxel-mfc-decode: REFUSED — --device /dev/videoN is required\n");
        return 2;
    }
    if (!o.receipt) o.receipt = "/etc/nuxel/mfc/safety-receipt.json";

    char sysfs_name[64], driver[64], compatible[128], ipver[16];
    if (resolve_identity(o.device, sysfs_name, sizeof(sysfs_name),
                         driver, sizeof(driver), compatible, sizeof(compatible),
                         ipver, sizeof(ipver)) < 0) {
        fail("node %s is not the exact allowed MFC decoder "
             "(%s/%s/%s on %s ip_ver %s)", o.device,
             DECODER_SYSFS_NAME, EXPECTED_DRIVER, EXPECTED_COMPATIBLE,
             EXPECTED_PLATFORM, EXPECTED_IP_VER);
    }
    info("identity: %s name=%s driver=%s compatible=%s ip_ver=%s",
         o.device, sysfs_name, driver, compatible, ipver);
    verify_receipt(o.receipt, o.device);

    if (o.timeout_seconds <= 0) o.timeout_seconds = 120;
    signal(SIGALRM, alarm_handler);
    alarm((unsigned)o.timeout_seconds);
    int fd = open(o.device, O_RDWR | O_NONBLOCK | O_CLOEXEC);
    if (fd < 0) {
        alarm(0);
        die("open MFC decoder");
    }
    alarm(0);
    if (g_alarm) fail("open did not complete within the userspace alarm window");

    print_caps(fd);

    if (o.query_only) {
        close(fd);
        printf("QUERY_ONLY PASS node=%s firmware_sha256=%s\n", o.device, FIRMWARE_SHA256);
        return 0;
    }

    if (!o.input || !o.width || !o.height) {
        close(fd);
        fail("--input, --width and --height are required for decode");
    }

    unsigned char *data = NULL;
    size_t size = 0;
    if (read_file(o.input, &data, &size) < 0) {
        close(fd);
        die("read input");
    }
    info("input: %s size=%zu bytes", o.input, size);

    int rc = run_decode(fd, &o, data, size);
    free(data);
    close(fd);
    return rc;
}
