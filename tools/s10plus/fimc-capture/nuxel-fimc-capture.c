/*
 * nuxel-fimc-capture — minimal FIMC-IS (Exynos9820) capture/self-test client.
 *
 * The Samsung "exynos-fimc-is" video nodes implement their own multi-plane
 * capture ioctls (V4L2_CAP_VIDEO_CAPTURE_MPLANE + V4L2_CAP_EXT_PIX_FORMAT) and
 * deliberately do NOT auto-select the multi-plane path for the *non*-MPLANE
 * VIDIOC_S_FMT form.  A generic `v4l2-ctl --stream-mmap` therefore gets ENOTTY
 * (the classic "FIMC-IS is not a camera" mis-diagnosis) even though the node is
 * a real capture client.  This tool drives exactly the ioctls the driver
 * exports in drivers/media/platform/exynos/fimc-is2/fimc-is-video-ispp.c:
 *
 *   QUERYCAP -> S_INPUT -> [TRY_FMT] -> S_FMT(MPLANE) -> REQBUFS
 *   -> QUERYBUF -> QBUF -> STREAMON -> DQBUF -> (STREAMOFF)
 *
 * It never invents frames: a passthrough is proven only by a positive byte
 * count and the kernel's own buffer timestamps/sequence, and every result is
 * printed as JSON for the diagnostic + acceptance log.
 *
 * Usage:
 *   nuxel-fimc-capture --node /dev/video130 [--input 0] [--fourcc YUYV]
 *       [--width 1440] [--height 1080] [--buffers 4] [--frames 1]
 *       [--timeout 2000] [--raw out.bin] [--probe-only] [--json]
 *   nuxel-fimc-capture --sensor-node /dev/video101 --sensor-position 0
 *       --sensor-probe --allow-sensor-init --json
 *
 * Exit: 0 accepted probe or dequeued payload (not physical verification), 3 no frame,
 *       2 usage error, 4 ioctl failure (details in JSON), 5 node missing.
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

struct opts {
	const char *node;
	const char *raw;
	const char *fourcc;
	unsigned input;
	unsigned sensor_input;
	int sensor_position_set;
	unsigned width, height;
	unsigned buffers, frames, timeout_ms;
	int probe_only;
	int sensor_probe;
	int allow_sensor_init;
	int json;
};

static struct opts O = {
	.node = NULL, .raw = NULL, .fourcc = "YUYV",
	.input = 0, .width = 1440, .height = 1080,
	.buffers = 4, .frames = 1, .timeout_ms = 2000,
	.probe_only = 0, .json = 0,
};

static unsigned long long now_ms(void)
{
	struct timespec ts;
	clock_gettime(CLOCK_MONOTONIC, &ts);
	return (unsigned long long)ts.tv_sec * 1000ULL + ts.tv_nsec / 1000000ULL;
}

static uint32_t fourcc_of(const char *s)
{
	if (!s || strlen(s) != 4)
		return 0;
	return v4l2_fourcc(s[0], s[1], s[2], s[3]);
}

static const char *stage = "none";
static int last_errno = 0;
static int do_ioctl(int fd, unsigned long req, void *arg, const char *name)
{
	int ret;
	stage = name;
	errno = 0;
	ret = ioctl(fd, req, arg);
	last_errno = ret < 0 ? errno : 0;
	return ret;
}

/* Current mapper supports one memory plane only. Reject metadata/multiple
 * planes rather than silently reporting a partial frame. */
static int payload_length(const struct v4l2_buffer *dq,
                          const struct v4l2_plane *p, size_t mapped,
                          size_t *length)
{
    if (dq->length != 1 || (dq->flags & V4L2_BUF_FLAG_ERROR) ||
        !p->bytesused || p->bytesused > mapped ||
        p->data_offset >= p->bytesused)
        return -1;
    *length = p->bytesused - p->data_offset;
    return 0;
}

static int varied_payload(const unsigned char *p, size_t n)
{
    size_t i;
    for (i = 1; i < n; i++)
        if (p[i] != p[0]) return 1;
    return 0;
}

static void usage(void)
{
	fputs("usage: nuxel-fimc-capture --node /dev/videoN [--input I] "
	      "[--fourcc YUYV] [--width W] [--height H] [--buffers N] "
	      "[--frames N] [--timeout MS] [--raw FILE] [--probe-only] [--json]\n"
	      "       nuxel-fimc-capture --sensor-node /dev/videoNN --sensor-position 0 "
	      "--sensor-probe --allow-sensor-init [--json]\n", stderr);
}

static int parse(int argc, char **argv)
{
	int i;
	for (i = 1; i < argc; i++) {
		const char *a = argv[i];
		const char *v = (i + 1 < argc) ? argv[i + 1] : NULL;
		if (!strcmp(a, "--node") && v) { O.node = v; i++; }
		else if (!strcmp(a, "--sensor-node") && v) { O.node = v; i++; }
		else if (!strcmp(a, "--sensor-id")) {
            fputs("--sensor-id is invalid for CONFIG_USE_SENSOR_GROUP; use --sensor-position 0 for the bounded rear trial\n", stderr);
            return 2;
        }
        else if (!strcmp(a, "--sensor-position") && v) {
            if (strcmp(v, "0")) {
                fputs("only rear position 0 is supported by this bounded probe\n", stderr);
                return 2;
            }
            O.sensor_input = 0; /* position=rear, scenario=normal, source video=0 */
            O.sensor_position_set = 1;
            i++;
        }
		else if (!strcmp(a, "--raw") && v) { O.raw = v; i++; }
		else if (!strcmp(a, "--fourcc") && v) { O.fourcc = v; i++; }
		else if (!strcmp(a, "--input") && v) { O.input = strtoul(v, NULL, 0); i++; }
		else if (!strcmp(a, "--width") && v) { O.width = strtoul(v, NULL, 0); i++; }
		else if (!strcmp(a, "--height") && v) { O.height = strtoul(v, NULL, 0); i++; }
		else if (!strcmp(a, "--buffers") && v) { O.buffers = strtoul(v, NULL, 0); i++; }
		else if (!strcmp(a, "--frames") && v) { O.frames = strtoul(v, NULL, 0); i++; }
		else if (!strcmp(a, "--timeout") && v) { O.timeout_ms = strtoul(v, NULL, 0); i++; }
		else if (!strcmp(a, "--probe-only")) { O.probe_only = 1; }
		else if (!strcmp(a, "--sensor-probe")) { O.sensor_probe = 1; }
		else if (!strcmp(a, "--allow-sensor-init")) { O.allow_sensor_init = 1; }
		else if (!strcmp(a, "--json")) { O.json = 1; }
		else if (!strcmp(a, "-h") || !strcmp(a, "--help")) { usage(); exit(0); }
		else { fprintf(stderr, "unknown argument: %s\n", a); usage(); return 2; }
	}
	if (!O.node) { usage(); return 2; }
	if (O.sensor_probe && !O.sensor_position_set) {
		fputs("--sensor-probe requires --sensor-position 0 (packed group ABI)\n", stderr);
		return 2;
	}
	if (O.sensor_probe && (O.probe_only || O.raw)) {
		fputs("--sensor-probe cannot be combined with --probe-only or --raw\n", stderr);
		return 2;
	}
	if (O.sensor_probe && !O.allow_sensor_init) {
		fputs("refusing sensor init: S_INPUT reads EEPROM and can toggle sensor retention; pass --allow-sensor-init after owner approval\n", stderr);
		return 2;
	}
	if (!O.timeout_ms || O.timeout_ms > 30000) { fputs("--timeout must be 1..30000 ms\n", stderr); return 2; }
	if (!O.allow_sensor_init) { fputs("S_INPUT requires --allow-sensor-init after owner approval\n", stderr); return 2; }
	if (O.buffers == 0 || O.buffers > 32) { fputs("--buffers must be 1..32\n", stderr); return 2; }
	if (O.frames == 0 || O.frames > 10000) { fputs("--frames must be 1..10000\n", stderr); return 2; }
	return 0;
}

struct buf {
	void *mem;
	size_t len;
};

static void jstr(const char *s)
{
	putchar('"');
	for (; s && *s; s++) {
		if (*s == '"' || *s == '\\') printf("\\%c", *s);
		else if (*s == '\n') fputs("\\n", stdout);
		else if ((unsigned char)*s < 0x20) printf("\\u%04x", *s);
		else putchar(*s);
	}
	putchar('"');
}

static void emit(int ok, const char *verdict, uint64_t frames, uint64_t bytes,
		 struct v4l2_capability *cap, struct v4l2_pix_format_mplane *pix,
		 double fps, const char *detail)
{
	printf("{\"tool\":\"nuxel-fimc-capture\",\"node\":");
	jstr(O.node);
	printf(",\"ok\":%s,\"verdict\":", ok ? "true" : "false");
	jstr(verdict);
	printf(",\"physical_frame_verified\":false,\"stage\":");
	jstr(stage);
	printf(",\"errno\":%d,\"frames\":%llu,\"bytes\":%llu", last_errno,
	       (unsigned long long)frames, (unsigned long long)bytes);
	if (cap) {
		char drv[17], card[33], bus[33];
		memcpy(drv, cap->driver, 16); drv[16] = 0;
		memcpy(card, cap->card, 32); card[32] = 0;
		memcpy(bus, cap->bus_info, 32); bus[32] = 0;
		printf(",\"driver\":"); jstr(drv);
		printf(",\"card\":"); jstr(card);
		printf(",\"bus_info\":"); jstr(bus);
		printf(",\"caps\":\"0x%08x\"", cap->capabilities);
	}
	if (pix) {
		char fcc[5] = { (char)(pix->pixelformat & 0xff), (char)((pix->pixelformat >> 8) & 0xff),
				(char)((pix->pixelformat >> 16) & 0xff), (char)((pix->pixelformat >> 24) & 0xff), 0 };
		printf(",\"fourcc\":"); jstr(fcc);
		printf(",\"width\":%u,\"height\":%u,\"planes\":%u,\"num_planes\":%u,\"flags\":\"0x%x\"",
		       pix->width, pix->height, pix->num_planes, pix->num_planes, pix->flags);
	}
	if (fps > 0.0)
		printf(",\"fps\":%.2f", fps);
	printf(",\"detail\":"); jstr(detail ? detail : "");
	printf("}\n");
}

int main(int argc, char **argv)
{
	int rc, fd, framed = 0, verified = 0, streaming = 0, i, q;
	struct stat st;
	struct v4l2_capability cap;
	struct v4l2_format fmt;
	struct v4l2_requestbuffers req;
	struct v4l2_buffer bufs[32], dq;
	struct v4l2_plane planes[32][VIDEO_MAX_PLANES];
	struct buf map[32];
	uint64_t total = 0, first_ms = 0, last_ms = 0, deadline = 0;
	FILE *raw = NULL;
	double fps = 0.0;

	memset(&cap, 0, sizeof(cap));
	memset(&fmt, 0, sizeof(fmt));
	memset(&req, 0, sizeof(req));
	memset(map, 0, sizeof(map));

	rc = parse(argc, argv);
	if (rc)
		return rc;

	stage = "stat_node";
	if (stat(O.node, &st) != 0 || !S_ISCHR(st.st_mode)) {
		last_errno = errno;
		emit(0, "NO_NODE", 0, 0, NULL, NULL, 0, "node missing or not a character device");
		return 5;
	}

	stage = "open";
	fd = open(O.node, O_RDWR | O_NONBLOCK);
	if (fd < 0) {
		last_errno = errno;
		emit(0, "OPEN_FAILED", 0, 0, NULL, NULL, 0, "open(O_RDWR|O_NONBLOCK) failed");
		return 4;
	}

	stage = "VIDIOC_QUERYCAP";
	if (do_ioctl(fd, VIDIOC_QUERYCAP, &cap, stage) < 0) {
		emit(0, "ENOTTY_ON_QUERYCAP", 0, 0, NULL, NULL, 0, "node does not answer QUERYCAP");
		close(fd);
		return 4;
	}
	/*
	 * FIMC-IS sensor endpoints (SS0..SS5) advertise VIDEO_OUTPUT_MPLANE.
	 * They must receive the Samsung packed position through S_INPUT before the
	 * ISP/output endpoints can be configured.  Samsung's S_INPUT is not a
	 * read-only probe: it can power EEPROM/I2C and toggle sensor retention.
	 * It therefore requires an explicit consent flag and stops immediately
	 * afterwards: no format, buffers, or userspace STREAMON is requested.
	 */
	if (O.sensor_probe) {
		stage = "VIDIOC_S_INPUT(sensor)";
		if (!((cap.capabilities & V4L2_CAP_DEVICE_CAPS ? cap.device_caps : cap.capabilities) & V4L2_CAP_VIDEO_OUTPUT_MPLANE)) {
			emit(0, "NOT_MPLANE_SENSOR", 0, 0, &cap, NULL, 0,
			     "sensor probe requires a V4L2_CAP_VIDEO_OUTPUT_MPLANE endpoint");
			close(fd);
			return 4;
		}
		if (do_ioctl(fd, VIDIOC_S_INPUT, &O.sensor_input, stage) < 0) {
			emit(0, "SENSOR_INPUT_FAILED", 0, 0, &cap, NULL, 0,
			     "kernel rejected the packed rear position or firmware initialization failed");
			close(fd);
			return 4;
		}
		emit(1, "SENSOR_BOUND", 0, 0, &cap, NULL, 0,
		     "S_INPUT accepted; sensor init was owner-authorized; no format, buffers, or userspace STREAMON requested");
		close(fd);
		return 0;
	}
	if (!((cap.capabilities & V4L2_CAP_DEVICE_CAPS ? cap.device_caps : cap.capabilities) & V4L2_CAP_VIDEO_CAPTURE_MPLANE)) {
		emit(0, "NOT_MPLANE_CAPTURE", 0, 0, &cap, NULL, 0, "node is not V4L2_CAP_VIDEO_CAPTURE_MPLANE");
		close(fd);
		return 4;
	}

	stage = "VIDIOC_S_INPUT";
	if (do_ioctl(fd, VIDIOC_S_INPUT, &O.input, stage) < 0) {
		emit(0, "S_INPUT_FAILED", 0, 0, &cap, NULL, 0, "sensor/input selection rejected");
		close(fd);
		return 4;
	}

	stage = "VIDIOC_S_FMT";
	memset(&fmt, 0, sizeof(fmt));
	fmt.type = V4L2_BUF_TYPE_VIDEO_CAPTURE_MPLANE;
	fmt.fmt.pix_mp.width = O.width;
	fmt.fmt.pix_mp.height = O.height;
	fmt.fmt.pix_mp.pixelformat = fourcc_of(O.fourcc);
	fmt.fmt.pix_mp.field = V4L2_FIELD_NONE;
	fmt.fmt.pix_mp.colorspace = V4L2_COLORSPACE_JPEG;
	fmt.fmt.pix_mp.num_planes = 1;
	fmt.fmt.pix_mp.plane_fmt[0].bytesperline = 0;
	fmt.fmt.pix_mp.plane_fmt[0].sizeimage = 0;
	if (do_ioctl(fd, VIDIOC_S_FMT, &fmt, stage) < 0) {
		emit(0, "S_FMT_FAILED", 0, 0, &cap, NULL, 0,
		     "multi-plane S_FMT rejected (check fourcc/size; see driver fimc_is_formats[])");
		close(fd);
		return 4;
	}

	stage = "VIDIOC_G_FMT";
	memset(&fmt, 0, sizeof(fmt));
	fmt.type = V4L2_BUF_TYPE_VIDEO_CAPTURE_MPLANE;
	if (do_ioctl(fd, VIDIOC_G_FMT, &fmt, stage) < 0) {
		emit(0, "G_FMT_FAILED", 0, 0, &cap, NULL, 0,
		     "multi-plane G_FMT rejected after S_FMT");
		close(fd);
		return 4;
	}
	stage = "format";
	if (!fmt.fmt.pix_mp.width || !fmt.fmt.pix_mp.height ||
	    !fmt.fmt.pix_mp.pixelformat || !fmt.fmt.pix_mp.num_planes ||
	    !fmt.fmt.pix_mp.plane_fmt[0].sizeimage ||
	    fmt.fmt.pix_mp.num_planes != 1 ||
	    !fmt.fmt.pix_mp.plane_fmt[0].bytesperline) {
		last_errno = 0;
		emit(0, "FORMAT_UNCOMMITTED", 0, 0, &cap, &fmt.fmt.pix_mp, 0,
		     "S_FMT returned success but G_FMT has no usable format; do not stream");
		close(fd);
		return 4;
	}

	if (O.probe_only) {
		emit(1, "PROBE_OK", 0, 0, &cap, &fmt.fmt.pix_mp, 0,
		     "ioctl path accepted; no frames requested (--probe-only)");
		close(fd);
		return 0;
	}

	stage = "VIDIOC_REQBUFS";
	memset(&req, 0, sizeof(req));
	req.count = O.buffers;
	req.type = V4L2_BUF_TYPE_VIDEO_CAPTURE_MPLANE;
	req.memory = V4L2_MEMORY_MMAP;
	if (do_ioctl(fd, VIDIOC_REQBUFS, (void *)&req, stage) < 0 || req.count == 0) {
		emit(0, "REQBUFS_FAILED", 0, 0, &cap, &fmt.fmt.pix_mp, 0,
		     "buffer allocation rejected (queue/framemgr not ready)");
		close(fd);
		return 4;
	}
	if (req.count > O.buffers)
		req.count = O.buffers;

	for (q = 0; q < (int)req.count; q++) {
		memset(&bufs[q], 0, sizeof(bufs[q]));
		memset(&planes[q], 0, sizeof(planes[q]));
		bufs[q].index = q;
		bufs[q].type = V4L2_BUF_TYPE_VIDEO_CAPTURE_MPLANE;
		bufs[q].memory = V4L2_MEMORY_MMAP;
		bufs[q].m.planes = planes[q];
		bufs[q].length = VIDEO_MAX_PLANES;
		stage = "VIDIOC_QUERYBUF";
		if (do_ioctl(fd, VIDIOC_QUERYBUF, &bufs[q], stage) < 0) {
			emit(0, "QUERYBUF_FAILED", 0, 0, &cap, &fmt.fmt.pix_mp, 0, "buffer query rejected");
			goto fail;
		}
		if (bufs[q].length != 1 ||
		    planes[q][0].length < fmt.fmt.pix_mp.plane_fmt[0].sizeimage) {
			last_errno = 0;
			emit(0, "QUERYBUF_EMPTY", 0, 0, &cap, &fmt.fmt.pix_mp, 0,
			     "driver reported a zero-length plane (no ISP-allocated buffer)");
			goto fail;
		}
		stage = "mmap";
		map[q].len = planes[q][0].length;
		map[q].mem = mmap(NULL, map[q].len, PROT_READ | PROT_WRITE, MAP_SHARED, fd,
				  planes[q][0].m.mem_offset);
		if (map[q].mem == MAP_FAILED) {
			map[q].mem = NULL;
			last_errno = errno;
			emit(0, "MMAP_FAILED", 0, 0, &cap, &fmt.fmt.pix_mp, 0, "mmap of the DMA buffer failed");
			goto fail;
		}
	}

	for (q = 0; q < (int)req.count; q++) {
		stage = "VIDIOC_QBUF";
		if (do_ioctl(fd, VIDIOC_QBUF, &bufs[q], stage) < 0) {
			emit(0, "QBUF_FAILED", 0, 0, &cap, &fmt.fmt.pix_mp, 0, "queueing a capture buffer failed");
			goto fail;
		}
	}

	stage = "VIDIOC_STREAMON";
	{
		enum v4l2_buf_type type = V4L2_BUF_TYPE_VIDEO_CAPTURE_MPLANE;
		if (do_ioctl(fd, VIDIOC_STREAMON, &type, stage) < 0) {
			emit(0, "STREAMON_FAILED", 0, 0, &cap, &fmt.fmt.pix_mp, 0,
			     "stream start rejected (ISP/sensor power or firmware not ready)");
			goto fail;
		}
	}

	streaming = 1;
	if (O.raw) {
		stage = "raw_open";
		raw = fopen(O.raw, "wbx");
		if (!raw) {
			last_errno = errno;
			emit(0, "RAW_OPEN_FAILED", 0, 0, &cap, &fmt.fmt.pix_mp, 0, "output must be a new writable file");
			goto fail;
		}
	}

	while (framed < (int)O.frames) {
		if (!deadline) deadline = now_ms() + O.timeout_ms;

		stage = "poll";
		for (;;) {
			struct pollfd pfd = { .fd = fd, .events = POLLIN };
			unsigned long long t = now_ms();
			int pr;

			if (t >= deadline) {
				last_errno = ETIMEDOUT;
				if (framed == 0) {
					emit(0, "NO_FRAME_TIMEOUT", 0, 0, &cap, &fmt.fmt.pix_mp, 0,
					     "stream started but DQBUF produced no frame before the timeout");
					goto fail;
				}
				goto done;
			}
			pr = poll(&pfd, 1, (int)(deadline - t > 100 ? 100 : deadline - t));
			if (pr < 0 && errno != EINTR) {
				last_errno = errno;
				emit(0, "POLL_FAILED", total ? (uint64_t)framed : 0, total, &cap,
				     &fmt.fmt.pix_mp, 0, "poll() on the capture fd failed");
				goto fail;
			}
			if (pr > 0 && (pfd.revents & (POLLIN | POLLRDNORM)))
				break;
		}

		memset(&dq, 0, sizeof(dq));
		memset(&planes[0], 0, sizeof(planes[0]));
		dq.type = V4L2_BUF_TYPE_VIDEO_CAPTURE_MPLANE;
		dq.memory = V4L2_MEMORY_MMAP;
		dq.m.planes = planes[0];
		dq.length = VIDEO_MAX_PLANES;
		stage = "VIDIOC_DQBUF";
		if (do_ioctl(fd, VIDIOC_DQBUF, &dq, stage) < 0) {
			if (errno == EAGAIN)
				continue;
			emit(0, "DQBUF_FAILED", total ? (uint64_t)framed : 0, total, &cap,
			     &fmt.fmt.pix_mp, 0, "dequeue of a capture buffer failed");
			goto fail;
		}
		if (dq.index >= req.count) {
			last_errno = EINVAL;
			emit(0, "DQBUF_BAD_INDEX", total ? (uint64_t)framed : 0, total, &cap,
			     &fmt.fmt.pix_mp, 0, "driver returned an out-of-range buffer index");
			goto fail;
		}

		{
			unsigned long long ts = now_ms();
            size_t bytelen;
            const unsigned char *payload;
            if (payload_length(&dq, &planes[0][0], map[dq.index].len, &bytelen)) {
                emit(0, "INVALID_PAYLOAD", framed, total, &cap, &fmt.fmt.pix_mp, 0,
                     "empty, errored, or out-of-bounds dequeue");
                goto fail;
            }
            payload = (const unsigned char *)map[dq.index].mem + planes[0][0].data_offset;
            if (!varied_payload(payload, bytelen)) {
                emit(0, "CONSTANT_PAYLOAD", framed, total, &cap, &fmt.fmt.pix_mp, 0,
                     "constant bytes cannot establish a physical frame");
                goto fail;
            }
            fprintf(stderr, "DQBUF index=%u sequence=%u timestamp=%lld.%06ld bytes=%zu offset=%u\n",
                    dq.index, dq.sequence, (long long)dq.timestamp.tv_sec,
                    (long)dq.timestamp.tv_usec, bytelen, planes[0][0].data_offset);

			if (framed == 0)
				first_ms = ts;
			last_ms = ts;
			total += bytelen;
			if (raw && (fwrite(payload, 1, bytelen, raw) != bytelen || fflush(raw))) {
                emit(0, "RAW_WRITE_FAILED", framed, total, &cap, &fmt.fmt.pix_mp, 0,
                     "frame evidence could not be saved completely");
                goto fail;
            }
			framed++;
			verified = 1;
			deadline = 0;
		}

		stage = "VIDIOC_QBUF(requeue)";
		if (do_ioctl(fd, VIDIOC_QBUF, &dq, stage) < 0) {
			emit(0, "REQUEUE_FAILED", (uint64_t)framed, total, &cap, &fmt.fmt.pix_mp, 0,
			     "re-queueing the buffer after DQBUF failed");
			goto fail;
		}
	}

done:
	if (framed > 1 && last_ms > first_ms)
		fps = (framed - 1) * 1000.0 / (double)(last_ms - first_ms);
	stage = "VIDIOC_STREAMOFF";
	streaming = 0; /* one attempt only, including a failed STREAMOFF */
	if (do_ioctl(fd, VIDIOC_STREAMOFF, &(enum v4l2_buf_type){ V4L2_BUF_TYPE_VIDEO_CAPTURE_MPLANE }, stage) < 0) {
        emit(0, "STREAMOFF_FAILED", framed, total, &cap, &fmt.fmt.pix_mp, 0,
             "stop failed; close fd and inspect kernel log before any further trial");
        rc = 4;
        goto out;
    }
	emit(verified, verified ? "FRAMES_CAPTURED" : "NO_FRAME", (uint64_t)framed, total,
	     &cap, &fmt.fmt.pix_mp, fps,
	     verified ? "Dequeued nonconstant payload; physical scene correlation still required" : "no frame");
	rc = verified ? 0 : 3;
	goto out;

fail:
	stage = "cleanup";
	if (streaming)
        do_ioctl(fd, VIDIOC_STREAMOFF, &(enum v4l2_buf_type){ V4L2_BUF_TYPE_VIDEO_CAPTURE_MPLANE }, stage);
	rc = 4;

out:
	for (i = 0; i < (int)req.count; i++)
		if (map[i].mem)
			munmap(map[i].mem, map[i].len);
	if (raw)
		fclose(raw);
	close(fd);
	return rc;
}
