/* nuxel-wl-fb-ext - Nuxel external display bridge (Wayland -> /dev/fb1).
 *
 * The S10+ external-video path is not DRM.  The Samsung vendor stack exposes the
 * DP output as the decon_t framebuffer /dev/fb1.  This bridge is the only
 * writer of that framebuffer.  It captures a compositor output through
 * zwlr_screencopy_manager_v1, fits it into the current /dev/fb1 mode preserving
 * aspect ratio (letterbox/pillarbox), optionally rotates it, converts the
 * compositor's XRGB8888/ARGB8888 words to the DECON's ABGR order, and writes
 * the frame directly into the mapping.
 *
 * It never opens /dev/fb0 and never replaces the compositor.
 */
#define _GNU_SOURCE
#include <errno.h>
#include <fcntl.h>
#include <getopt.h>
#include <linux/fb.h>
#include <linux/v4l2-dv-timings.h>
#include <linux/videodev2.h>
#include <math.h>
#include <poll.h>
#include <signal.h>
#include <stdarg.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/file.h>
#include <sys/ioctl.h>
#include <sys/mman.h>
#include <sys/stat.h>
#include <sys/syscall.h>
#include <time.h>
#include <unistd.h>
#include <wayland-client.h>

#include "wlr-screencopy-unstable-v1-client-protocol.h"

#define MAX_OUTPUTS 8
#define STATE_PATH "/run/nuxel-display/ext.state"
#define LOCK_PATH "/run/nuxel-fb1-owner.lock"

/* ---- Samsung decon_t / ION vendor interface -----------------------------
 * The S10+ external output is decon_t /dev/fb1 (not DRM).  Writing pixels
 * into the fb1 mapping does not start scan-out: decon2 must first be
 * unblanked (which reaches displayport_enable) and then programmed with the
 * vendor S3CFB_WIN_CONFIG ioctl using a dma-buf.  The fb1 dma-buf itself is
 * not exportable to userspace, so we allocate an ION system-heap buffer and
 * hand its fd to the decon.  This is the same interface Samsung's display
 * HAL uses; no undocumented register writes are involved.
 *
 * The layouts below mirror drivers/video/fbdev/exynos/dpu20/decon.h for
 * this exact Exynos 9820 build (CONFIG_EXYNOS_MCD_HDR=y, 64-bit dma_addr_t).
 */
#define DEXT_MAX_DECON_WIN 6
#define DEXT_MAX_PLANE_CNT 3
#define DEXT_WIN_IDX       4   /* decon_t DT default_win */
#define DEXT_IDMA_G1       1   /* DPU_DMA2CH(IDMA_G1) == 2 == decon_t default_ch */
/* Caller-side DECON pixel-format IDs (the kernel's enum values).
 *
 * decon_set_win_config() runs dpu_translate_fmt_to_dpp() before programming
 * the DPP:
 *
 *   caller BGRA_8888 (3) -> IDMA ARGB_8888 (0)  word 0xAARRGGBB, bytes B,G,R,A
 *   caller RGBA_8888 (2) -> IDMA ABGR_8888 (1)  word 0xAABBGGRR, bytes R,G,B,A
 *
 * The normal bridge packing is 0xAARRGGBB (R@16 G@8 B@0 A@24), so it must
 * pass caller BGRA_8888.  Passing ARGB_8888 here translated to IDMA BGRA
 * (word B,G,R,A), which reads the opaque 0xff alpha byte as the blue channel
 * and produces the measured all-blue overlay.  The diagnostic --color-order
 * abgr packing is 0xAABBGGRR (R@0 G@8 B@16 A@24) and must pass caller RGBA. */
#define DEXT_FMT_BGRA8888  3   /* caller BGRA -> IDMA ARGB (R@16 G@8 B@0 A@24) */
#define DEXT_FMT_RGBA8888  2   /* caller RGBA -> IDMA ABGR (R@0  G@8 B@16 A@24) */

struct dext_win_rect { int x, y; uint32_t w, h; };
struct dext_dpp_params {
    uint64_t addr[DEXT_MAX_PLANE_CNT];
    uint32_t rot, eq_mode, comp_src, hdr_std, min_luminance, max_luminance;
};
struct dext_frame { int x, y; uint32_t w, h, f_w, f_h; };
struct dext_win_config {
    uint32_t state;
    union {
        uint32_t color;
        struct {
            int fd_idma[3];
            int acq_fence, rel_fence, plane_alpha;
            uint32_t blending, idma_type, format;
            struct dext_dpp_params dpp_parm;
            struct dext_win_rect block_area, transparent_area, opaque_area;
            struct dext_frame src;
        };
    };
    struct dext_frame dst;
    uint8_t protection, compression;
    uint32_t wcg_mode;
};
struct dext_win_config_extra { int remained_frames; uint32_t reserved[7]; };
struct dext_win_config_data {
    int retire_fence, fd_odma;
    struct dext_win_config config[DEXT_MAX_DECON_WIN + 1];
    struct dext_win_config_extra extra;
};
#define DEXT_S3CFB_WIN_CONFIG _IOW('F', 209, struct dext_win_config_data)

struct dext_ion_alloc {
    uint64_t len;
    uint32_t heap_id_mask;
    uint32_t flags;
    uint32_t fd;
    uint32_t unused;
};
#define DEXT_ION_IOC_ALLOC _IOWR('I', 0, struct dext_ion_alloc)
#define DEXT_ION_HEAP_SYSTEM (1u << 0)

/* ---- Samsung displayport preset ioctl --------------------------------
 * decon_t exposes EXYNOS_SET_DISPLAYPORT_CONFIG on /dev/fb1.  It reaches
 * displayport_s_dv_timings(), which sets displayport->cur_video and refreshes
 * decon->lcd_info.  The vendor driver otherwise leaves cur_video at the
 * unplug default (V640X480P60), which is why the external output stayed at
 * 640x480 even though the TV EDID advertises 1920x1080p60.
 *
 * The layout mirrors struct exynos_displayport_data in
 * drivers/video/fbdev/exynos/dpu20/displayport.h.  The ioctl command number
 * encodes sizeof(struct), so the fields must match the kernel UAPI exactly.
 */
struct dext_dp_data {
    int state; /* EXYNOS_DISPLAYPORT_STATE_PRESET */
    struct v4l2_dv_timings timings;
    struct v4l2_enum_dv_timings etimings;
    uint32_t audio_info;
    int hdr_support;
};
#define DEXT_GET_DP_CONFIG _IOW(70, 300, struct dext_dp_data) /* 'F' */
#define DEXT_SET_DP_CONFIG _IOW(70, 301, struct dext_dp_data)
#define DEXT_DP_STATE_PRESET 0

struct dext_preset {
    const char *name;
    uint32_t w, h;
    struct v4l2_dv_timings timings;
};


struct output {
    struct wl_output *wl;
    char name[128];
    char description[256];
    int32_t x, y, phys_w, phys_h;
    int32_t width, height, refresh;
    int have_name, have_mode;
};

static struct wl_display *display;
static struct wl_registry *registry;
static struct wl_compositor *compositor;
static struct wl_shm *shm;
static struct zwlr_screencopy_manager_v1 *scm;
static struct output outputs[MAX_OUTPUTS];
static int noutputs;
static char wanted_output[128];
static const char *mode_name = "mirror";
static const char *fb_path = "/dev/fb1";
static int target_fps = 20;
static int rotation = 0;
static int rotation_set = 0;
static const char *fit_mode_name = "fit";
static int link_watch = 1;
/* The external decon_t OUTFIFO is programmed with DECON_RGB pixel order
 * (decon_reg_configure_lcd: only DSI-without-DSC selects DECON_BGR).  The
 * normal path packs the bridge word as 0xAARRGGBB (memory bytes B,G,R,A) and
 * asks decon_set_win_config() for caller-side BGRA_8888; the kernel translates
 * that to IDMA ARGB_8888, whose 0xAARRGGBB layout is exactly this packing.
 * --color-order abgr keeps the pre-swapped 0xAABBGGRR diagnostic packing
 * (memory R,G,B,A) and therefore asks for caller-side RGBA_8888, which the
 * kernel translates to IDMA ABGR_8888. */
static int color_order_argb = 1;
static int auto_orientation = 0;
static const char *orientation_path = "/run/nuxel-wl-fb-orientation";
static const char *test_pattern = NULL;      /* bars | grey | NULL */
static const char *dump_source_path = NULL;  /* raw screencopy PPM */
static const char *dump_output_path = NULL;  /* converted scanout half PPM */
static int orientation_transform = -1;
static int link_fail_count = 0;
static int orientation_effective = -1;
static int color_selftest = 0;
static int out_width = 0, out_height = 0;
static int running = 1;
static int capture_once = 0;
static volatile sig_atomic_t got_signal = 0;

struct fbdev {
    int fd;          /* /dev/fb1: used for FBIOBLANK and the decon ioctl */
    int ion_fd;      /* dma-buf handed to decon2 for scan-out */
    int half;        /* double-buffer half currently being written */
    uint8_t *map;    /* mmap of the ION dma-buf */
    size_t len;
    uint32_t w, h, bpp, line;
    uint32_t r_off, g_off, b_off, a_off;
    uint32_t decon_format;
    uint32_t black;
    struct fb_var_screeninfo var;
    struct fb_fix_screeninfo fix;
};

static struct fbdev fb = {.fd = -1, .ion_fd = -1, .half = 0};
static size_t dbg_nz = 0;   /* sampled non-black pixels in the last written half */

struct shmbuf {
    struct wl_buffer *buffer;
    void *data;
    size_t size;
    int fd;
    int32_t w, h, stride;
    uint32_t format;
};

struct frame_state {
    struct shmbuf *buf;
    int ready;
    int failed;
    int y_invert;
};

static void logmsg(const char *fmt, ...) {
    va_list ap;
    time_t t = time(NULL);
    struct tm tm;
    localtime_r(&t, &tm);
    fprintf(stderr, "%04d-%02d-%02dT%02d:%02d:%02d nuxel-wl-fb-ext: ",
            tm.tm_year + 1900, tm.tm_mon + 1, tm.tm_mday,
            tm.tm_hour, tm.tm_min, tm.tm_sec);
    va_start(ap, fmt);
    vfprintf(stderr, fmt, ap);
    va_end(ap);
    fputc('\n', stderr);
    fflush(stderr);
}

static void write_state(const char *fmt, ...) {
    char buf[1024];
    va_list ap;
    va_start(ap, fmt);
    vsnprintf(buf, sizeof(buf), fmt, ap);
    va_end(ap);
    int fd = open(STATE_PATH, O_WRONLY | O_CREAT | O_TRUNC, 0644);
    if (fd < 0) return;
    dprintf(fd, "%s\n", buf);
    fsync(fd);
    close(fd);
}

static void on_signal(int sig) {
    (void)sig;
    got_signal = 1;
    running = 0;
}

/* ---- output enumeration ------------------------------------------------ */
static void out_geometry(void *data, struct wl_output *wl, int32_t x, int32_t y,
                         int32_t pw, int32_t ph, int32_t subpixel,
                         const char *make, const char *model, int32_t transform) {
    (void)wl; (void)subpixel; (void)make; (void)model; (void)transform;
    struct output *o = data;
    o->x = x; o->y = y; o->phys_w = pw; o->phys_h = ph;
}

static void out_mode(void *data, struct wl_output *wl, uint32_t flags,
                     int32_t width, int32_t height, int32_t refresh) {
    (void)wl;
    struct output *o = data;
    if (flags & WL_OUTPUT_MODE_CURRENT) {
        o->width = width; o->height = height; o->refresh = refresh;
        o->have_mode = 1;
    }
}

static void out_done(void *data, struct wl_output *wl) { (void)data; (void)wl; }
static void out_scale(void *data, struct wl_output *wl, int32_t scale) {
    (void)data; (void)wl; (void)scale;
}
static void out_name(void *data, struct wl_output *wl, const char *name) {
    (void)wl;
    struct output *o = data;
    snprintf(o->name, sizeof(o->name), "%s", name ? name : "");
    o->have_name = 1;
}
static void out_description(void *data, struct wl_output *wl, const char *desc) {
    (void)wl;
    struct output *o = data;
    snprintf(o->description, sizeof(o->description), "%s", desc ? desc : "");
}

static const struct wl_output_listener output_listener = {
    .geometry = out_geometry,
    .mode = out_mode,
    .done = out_done,
    .scale = out_scale,
    .name = out_name,
    .description = out_description,
};

static void registry_global(void *data, struct wl_registry *reg, uint32_t name,
                            const char *iface, uint32_t version) {
    (void)data;
    if (strcmp(iface, wl_compositor_interface.name) == 0) {
        compositor = wl_registry_bind(reg, name, &wl_compositor_interface,
                                      version < 4 ? version : 4);
    } else if (strcmp(iface, wl_shm_interface.name) == 0) {
        shm = wl_registry_bind(reg, name, &wl_shm_interface, 1);
    } else if (strcmp(iface, zwlr_screencopy_manager_v1_interface.name) == 0) {
        scm = wl_registry_bind(reg, name, &zwlr_screencopy_manager_v1_interface,
                               version < 3 ? version : 3);
    } else if (strcmp(iface, wl_output_interface.name) == 0 &&
               noutputs < MAX_OUTPUTS) {
        struct output *o = &outputs[noutputs++];
        memset(o, 0, sizeof(*o));
        o->wl = wl_registry_bind(reg, name, &wl_output_interface,
                                 version < 4 ? version : 4);
        wl_output_add_listener(o->wl, &output_listener, o);
    }
}

static void registry_remove(void *data, struct wl_registry *reg, uint32_t name) {
    (void)data; (void)reg; (void)name;
}

static const struct wl_registry_listener registry_listener = {
    .global = registry_global,
    .global_remove = registry_remove,
};

static struct output *pick_output(void) {
    if (wanted_output[0]) {
        for (int i = 0; i < noutputs; i++)
            if (strcmp(outputs[i].name, wanted_output) == 0) return &outputs[i];
        return NULL;
    }
    if (strcmp(mode_name, "desktop") == 0) {
        /* Prefer the second output; the phone is the first. */
        for (int i = 1; i < noutputs; i++)
            if (outputs[i].have_mode) return &outputs[i];
        return NULL;
    }
    for (int i = 0; i < noutputs; i++)
        if (outputs[i].have_mode) return &outputs[i];
    return NULL;
}

static int dext_read_int(const char *path, int *out) {
    FILE *f = fopen(path, "r");
    if (!f) return -1;
    int v = -1;
    int ok = fscanf(f, "%d", &v) == 1;
    fclose(f);
    if (!ok) return -1;
    *out = v;
    return 0;
}

/* Cheap, side-effect-free DP link check.  Reading these attributes does not
 * issue PD/OPCODE traffic or parse a test EDID.  The bridge checks this before
 * every submit and exits immediately when the cable is pulled, so decon2 is
 * never knowingly programmed against a dead link. */
static int dext_link_ok(void) {
    int secdp = -1;
    if (dext_read_int("/sys/class/switch/secdp/state", &secdp) < 0 || secdp != 1)
        return 0;
    FILE *f = fopen("/sys/class/extcon/extcon0/state", "r");
    if (!f) return 0;
    char buf[256] = {0};
    size_t n = fread(buf, 1, sizeof(buf) - 1, f);
    fclose(f);
    buf[n] = 0;
    return strstr(buf, "DP=1") != NULL || strstr(buf, "DP=true") != NULL;
}

static int dext_set_preset(int fd, const struct dext_preset *p, int verbose) {
    struct dext_dp_data d;
    memset(&d, 0, sizeof(d));
    d.state = DEXT_DP_STATE_PRESET;
    d.timings = p->timings;
    if (ioctl(fd, DEXT_SET_DP_CONFIG, &d) < 0) {
        if (verbose) logmsg("DP preset %s failed: %s", p->name, strerror(errno));
        return -1;
    }
    /* Verify through the driver's own getter, not just the ioctl return. */
    memset(&d, 0, sizeof(d));
    d.state = DEXT_DP_STATE_PRESET;
    if (ioctl(fd, DEXT_GET_DP_CONFIG, &d) < 0 ||
        d.timings.bt.width != p->w || d.timings.bt.height != p->h) {
        if (verbose) logmsg("DP preset %s did not stick (got %ux%u)", p->name,
                            d.timings.bt.width, d.timings.bt.height);
        return -1;
    }
    return 0;
}

static int dext_select_preset(int fd, uint32_t want_w, uint32_t want_h,
                              uint32_t *got_w, uint32_t *got_h) {
    static const struct dext_preset presets[] = {
        {"1920x1080p60", 1920, 1080, V4L2_DV_BT_CEA_1920X1080P60},
        {"1280x720p60",  1280,  720, V4L2_DV_BT_CEA_1280X720P60},
        {"640x480p60",    640,  480, V4L2_DV_BT_DMT_640X480P60},
    };
    size_t n = sizeof(presets) / sizeof(presets[0]);
    if (want_w && want_h) {
        for (size_t i = 0; i < n; i++) {
            if (presets[i].w == want_w && presets[i].h == want_h) {
                if (dext_set_preset(fd, &presets[i], 1) == 0) {
                    *got_w = presets[i].w; *got_h = presets[i].h;
                    return 0;
                }
                return -1;
            }
        }
        logmsg("unsupported requested resolution %ux%u", want_w, want_h);
        return -1;
    }
    for (size_t i = 0; i < n; i++) {
        if (dext_set_preset(fd, &presets[i], 1) == 0) {
            *got_w = presets[i].w; *got_h = presets[i].h;
            return 0;
        }
    }
    return -1;
}

static void fb_powerdown(void) {
    if (fb.fd >= 0) {
        if (ioctl(fb.fd, FBIOBLANK, FB_BLANK_POWERDOWN) < 0)
            logmsg("FBIOBLANK(POWERDOWN) failed: %s", strerror(errno));
        else
            logmsg("fb1 powered down (DP stream disabled)");
    }
}

static void fb_release(void) {
    if (fb.map) { munmap(fb.map, fb.len); fb.map = NULL; }
    if (fb.ion_fd >= 0) { close(fb.ion_fd); fb.ion_fd = -1; }
    if (fb.fd >= 0) { close(fb.fd); fb.fd = -1; }
    fb.len = 0;
}

static int fb_alloc_ion(void) {
    int ifd = open("/dev/ion", O_RDWR | O_CLOEXEC);
    if (ifd < 0) {
        logmsg("open /dev/ion failed: %s", strerror(errno));
        return -1;
    }
    struct dext_ion_alloc a;
    memset(&a, 0, sizeof(a));
    a.len = fb.len;
    a.heap_id_mask = DEXT_ION_HEAP_SYSTEM;
    a.flags = 0;
    if (ioctl(ifd, DEXT_ION_IOC_ALLOC, &a) < 0) {
        logmsg("ION_IOC_ALLOC(%zu) failed: %s", fb.len, strerror(errno));
        close(ifd);
        return -1;
    }
    close(ifd);
    fb.ion_fd = (int)a.fd;
    fb.map = mmap(NULL, fb.len, PROT_READ | PROT_WRITE, MAP_SHARED, fb.ion_fd, 0);
    if (fb.map == MAP_FAILED) {
        logmsg("mmap ion failed: %s", strerror(errno));
        fb.map = NULL;
        close(fb.ion_fd); fb.ion_fd = -1;
        return -1;
    }
    memset(fb.map, 0, fb.len);
    logmsg("ion dma-buf fd=%d len=%zu", fb.ion_fd, fb.len);
    return 0;
}

/* Program decon2 window 4 with our dma-buf.  yoff selects the visible half
 * of the 2x-height buffer (double buffering). */
static int dp_win_submit(uint32_t yoff) {
    if (fb.fd < 0 || fb.ion_fd < 0) return -1;
    struct dext_win_config_data wd;

    memset(&wd, 0, sizeof(wd));
    wd.retire_fence = -1;
    wd.fd_odma = -1;
    for (int i = 0; i <= DEXT_MAX_DECON_WIN; i++) {
        wd.config[i].state = 0; /* DISABLED */
        wd.config[i].fd_idma[0] = wd.config[i].fd_idma[1] = wd.config[i].fd_idma[2] = -1;
        wd.config[i].acq_fence = -1;
        wd.config[i].rel_fence = -1;
    }
    struct dext_win_config *c = &wd.config[DEXT_WIN_IDX];
    c->state = 2; /* DECON_WIN_STATE_BUFFER */
    c->fd_idma[0] = fb.ion_fd;
    c->fd_idma[1] = -1;
    c->fd_idma[2] = -1;
    c->acq_fence = -1;
    c->rel_fence = -1;
    c->plane_alpha = 255;
    c->blending = 0;        /* DECON_BLENDING_NONE */
    c->idma_type = DEXT_IDMA_G1;
    c->format = fb.decon_format;
    c->dpp_parm.rot = 0;    /* DPP_ROT_NORMAL: rotation is done in software */
    c->dpp_parm.eq_mode = 0;
    c->dpp_parm.comp_src = 0;
    c->dpp_parm.hdr_std = 0;
    c->src.x = 0;
    c->src.y = (int)yoff;
    c->src.w = fb.w;
    c->src.h = fb.h;
    c->src.f_w = fb.w;
    c->src.f_h = fb.h * 2;
    c->dst.x = 0;
    c->dst.y = 0;
    c->dst.w = fb.w;
    c->dst.h = fb.h;
    c->dst.f_w = fb.w;
    c->dst.f_h = fb.h;
    c->protection = 0;
    c->compression = 0;
    c->wcg_mode = 0;

    int r = ioctl(fb.fd, DEXT_S3CFB_WIN_CONFIG, &wd);
    if (r == 0) {
        /* The vendor driver installs a release-fence fd for every active
         * window and returns it in config[i].rel_fence.  The fd belongs to
         * this process and must be closed after each submit, otherwise the
         * bridge leaks one fd per frame until get_unused_fd_flags() fails
         * (the "decon_create_release_fences: failed to get unused fd" storm). */
        for (int i = 0; i <= DEXT_MAX_DECON_WIN; i++)
            if (wd.config[i].rel_fence >= 0)
                close(wd.config[i].rel_fence);
        if (wd.retire_fence >= 0)
            close(wd.retire_fence);
    }
    return r;
}

/* ---- framebuffer ------------------------------------------------------- */
static int fb_open(void) {
    fb.fd = open(fb_path, O_RDWR | O_CLOEXEC);
    if (fb.fd < 0) {
        logmsg("open %s failed: %s", fb_path, strerror(errno));
        return -1;
    }
    if (ioctl(fb.fd, FBIOGET_VSCREENINFO, &fb.var) < 0 ||
        ioctl(fb.fd, FBIOGET_FSCREENINFO, &fb.fix) < 0) {
        logmsg("fb ioctl failed: %s", strerror(errno));
        close(fb.fd); fb.fd = -1; return -1;
    }

    /* The fb1 var is frozen at the probe-time 640x480 default.  The real
     * scan-out size is selected through the DP preset ioctl and our own
     * ION buffer, so do not derive geometry from fb1.var. */
    if (out_width && out_height) {
        uint32_t gw = 0, gh = 0;
        if (dext_select_preset(fb.fd, (uint32_t)out_width, (uint32_t)out_height,
                               &gw, &gh) < 0) {
            logmsg("requested DP mode %dx%d unavailable", out_width, out_height);
            close(fb.fd); fb.fd = -1; return -1;
        }
        fb.w = gw; fb.h = gh;
    } else {
        uint32_t gw = 0, gh = 0;
        if (dext_select_preset(fb.fd, 0, 0, &gw, &gh) < 0) {
            logmsg("no usable DP video preset");
            close(fb.fd); fb.fd = -1; return -1;
        }
        fb.w = gw; fb.h = gh;
    }
    fb.bpp = 32;
    fb.line = fb.w * 4;
    fb.len = (size_t)fb.line * fb.h * 2;   /* double buffered */
    /* Decon input packing.  See the comment above color_order_argb.
     *  - Normal 0xAARRGGBB packing (R@16 G@8 B@0 A@24): caller BGRA_8888,
     *    translated by the kernel to IDMA ARGB_8888.
     *  - Diagnostic 0xAABBGGRR packing (R@0 G@8 B@16 A@24): caller RGBA_8888,
     *    translated by the kernel to IDMA ABGR_8888.
     * fb_var on this vendor kernel declares R@16/B@0 but the DECON does not
     * program that order; it is only trusted behind an explicit diagnostic
     * env override. */
    if (color_order_argb) {
        fb.r_off = 16; fb.g_off = 8; fb.b_off = 0;
        fb.decon_format = DEXT_FMT_BGRA8888;
    } else {
        fb.r_off = 0; fb.g_off = 8; fb.b_off = 16;
        fb.decon_format = DEXT_FMT_RGBA8888;
    }
    fb.a_off = 24;
    const char *trust = getenv("NUXEL_EXT_FBVAR_ORDER");
    if (trust && strcmp(trust, "1") == 0) {
        fb.r_off = fb.var.red.offset;
        fb.g_off = fb.var.green.offset;
        fb.b_off = fb.var.blue.offset;
        fb.a_off = fb.var.transp.offset;
        fb.decon_format = DEXT_FMT_BGRA8888;
    }
    fb.black = 0xff000000u;
    logmsg("external mode %ux%u fb=%s line=%u len=%zu double-buffered "
           "decon_fmt=%s->IDMA_%s(R@%u G@%u B@%u A@%u)",
           fb.w, fb.h, fb_path, fb.line, fb.len,
           color_order_argb ? "BGRA8888" : "RGBA8888",
           color_order_argb ? "ARGB8888" : "ABGR8888",
           fb.r_off, fb.g_off, fb.b_off, fb.a_off);

    if (fb_alloc_ion() < 0) {
        fb_release();
        return -1;
    }

    /* Ensure any previous scan-out (and DP stream) is stopped before the
     * timing generator is re-enabled with the newly selected preset. */
    ioctl(fb.fd, FBIOBLANK, FB_BLANK_POWERDOWN);

    /* Unblank decon2.  This reaches decon_enable -> displayport_enable(),
     * which starts the DP video stream at fb.w x fb.h. */
    if (ioctl(fb.fd, FBIOBLANK, FB_BLANK_UNBLANK) < 0) {
        logmsg("FBIOBLANK(FB_BLANK_UNBLANK) failed: %s", strerror(errno));
        fb_powerdown();
        fb_release();
        return -1;
    }
    logmsg("fb %s unblanked at %ux%u", fb_path, fb.w, fb.h);

    if (dp_win_submit(0) < 0)
        logmsg("decon2 win config failed: %s", strerror(errno));
    else
        logmsg("decon2 window %d -> dma-buf fd=%d (%ux%u double-buffered)",
               DEXT_WIN_IDX, fb.ion_fd, fb.w, fb.h);
    fb.half = 1;
    return 0;
}

static int fb_refresh(void) {
    if (fb.fd < 0) return fb_open();
    /* fb1.var stays at the probe-time default; only the fd health matters.
     * Re-reading var here would falsely force a reopen on every frame. */
    struct fb_fix_screeninfo f;
    if (ioctl(fb.fd, FBIOGET_FSCREENINFO, &f) < 0)
        return -1;
    return 0;
}

static void fb_clear(void) {
    if (!fb.map || !fb.len) return;
    uint32_t *p = (uint32_t *)fb.map;
    size_t words = fb.len / 4;
    for (size_t i = 0; i < words; i++) p[i] = fb.black;
}

/* ---- colour LUT -------------------------------------------------------- */
static uint32_t *lut_lo, *lut_hi;
static uint32_t lut_format;
static uint32_t lut_r, lut_g, lut_b, lut_a;

static void build_lut(uint32_t format) {
    free(lut_lo); free(lut_hi);
    lut_lo = malloc(sizeof(uint32_t) * 65536);
    lut_hi = malloc(sizeof(uint32_t) * 65536);
    if (!lut_lo || !lut_hi) { free(lut_lo); free(lut_hi); lut_lo = lut_hi = NULL; return; }
    lut_format = format;
    lut_r = fb.r_off; lut_g = fb.g_off; lut_b = fb.b_off;
    lut_a = 0xff000000u;
    for (uint32_t x = 0; x < 65536; x++) {
        uint32_t b = x & 0xffu, g = (x >> 8) & 0xffu;
        lut_lo[x] = (b << lut_b) | (g << lut_g) | lut_a;
        /* convert_word indexes this with the whole high 16 bits of the
         * source word.  For ARGB8888 that is 0xAARR, so the table must be
         * filled for every 16-bit index with the low byte (RR), not with
         * (x >> 16) (which used to make every entry zero and drop red). */
        lut_hi[x] = ((x & 0xffu) << lut_r);
    }
}

static inline uint32_t convert_word(uint32_t v, uint32_t format) {
    if (format == WL_SHM_FORMAT_XRGB8888 || format == WL_SHM_FORMAT_ARGB8888) {
        if (!lut_lo || lut_format != format) build_lut(format);
        if (lut_lo) return lut_lo[v & 0xffffu] | lut_hi[v >> 16];
        uint32_t r = (v >> 16) & 0xffu, g = (v >> 8) & 0xffu, b = v & 0xffu;
        return (r << lut_r) | (g << lut_g) | (b << lut_b) | lut_a;
    }
    if (format == WL_SHM_FORMAT_XBGR8888 || format == WL_SHM_FORMAT_ABGR8888) {
        uint32_t b = (v >> 16) & 0xffu, g = (v >> 8) & 0xffu, r = v & 0xffu;
        return (r << fb.r_off) | (g << fb.g_off) | (b << fb.b_off) | 0xff000000u;
    }
    /* Unknown 32-bit format: pass through with opaque alpha. */
    return v | 0xff000000u;
}


/* ---- orientation authority ---------------------------------------------
 * nuxel-orientationd publishes the verified compositor transform in a tiny
 * key=value file.  The external TV must undo that transform in software:
 * the raw screencopy buffer is in the physical 720x1520 output mode, while
 * the logical scene is e.g. 1520x720 in landscape.  We never rotate the HDMI
 * timing; only the copied pixels.  The sign is validated against grim (which
 * applies the same wl_output transform) and stored in the report evidence.
 */
static int read_orientation_file(int *transform, int *effective) {
    FILE *f = fopen(orientation_path, "r");
    if (!f) return -1;
    char line[256];
    int t = -1, e = -1;
    while (fgets(line, sizeof(line), f)) {
        int v;
        if (sscanf(line, "transform=%d", &v) == 1) t = v;
        else if (sscanf(line, "effective_orientation=%d", &v) == 1) e = v;
    }
    fclose(f);
    if (t != 0 && t != 90 && t != 180 && t != 270) {
        /* Fall back to the documented Nuxel orientation->transform map. */
        switch (e) {
        case 0: t = 0; break;
        case 90: t = 270; break;
        case 180: t = 180; break;
        case 270: t = 90; break;
        default: return -1;
        }
    }
    *transform = t;
    *effective = e;
    return 0;
}

static int orientation_to_rotation(int transform) {
    /* The bridge's rotation parameter uses the same clockwise convention as
     * wl_output's transform.  Measured against grim on this device:
     * raw 720x1520 rotated clockwise 270 == the compositor's 1520x720
     * landscape screenshot exactly (MSE 0).  Therefore the external presenter
     * applies the reported transform value, not its inverse.  Rotating the
     * inverse produced a sideways picture with rotation=90 at transform=270. */
    return transform;
}

static void update_orientation(void) {
    static double last_check = 0.0;
    if (!auto_orientation) return;
    struct timespec now;
    clock_gettime(CLOCK_MONOTONIC, &now);
    double t = (double)now.tv_sec + (double)now.tv_nsec / 1e9;
    if (t - last_check < 0.20) return;
    last_check = t;
    int transform = -1, effective = -1;
    if (read_orientation_file(&transform, &effective) < 0) {
        /* Keep the last verified rotation; never invent an orientation. */
        return;
    }
    int next = orientation_to_rotation(transform);
    if (transform != orientation_transform || effective != orientation_effective) {
        int old = rotation;
        orientation_transform = transform;
        orientation_effective = effective;
        rotation = next;
        logmsg("orientation effective=%d transform=%d external_rotation=%d%s",
               effective, transform, rotation,
               old != rotation ? " (updated)" : "");
        /* Publish the transition immediately; the normal frame receipt is
         * throttled to 1 Hz, which was too slow for rotation monitoring. */
        write_state("state RUNNING mode=%s output=%s fb=%s dst=%ux%u fps=%d "
                    "rot=%d fit=%s color=%s orient_eff=%d orient_tf=%d",
                    mode_name, wanted_output[0] ? wanted_output : "auto",
                    fb_path, fb.w, fb.h, target_fps, rotation, fit_mode_name,
                    color_order_argb ? "argb" : "abgr", effective, transform);
    }
}

/* ---- deterministic colour diagnostics ---------------------------------- */
static inline uint32_t pack_rgb(uint32_t r, uint32_t g, uint32_t b) {
    return (r << fb.r_off) | (g << fb.g_off) | (b << fb.b_off) | 0xff000000u;
}

static inline void unpack_rgb(uint32_t v, uint32_t *r, uint32_t *g, uint32_t *b) {
    *r = (v >> fb.r_off) & 0xffu;
    *g = (v >> fb.g_off) & 0xffu;
    *b = (v >> fb.b_off) & 0xffu;
}

static uint32_t source_word(uint32_t format, uint32_t r, uint32_t g, uint32_t b) {
    if (format == WL_SHM_FORMAT_XBGR8888 || format == WL_SHM_FORMAT_ABGR8888)
        return (b << 16) | (g << 8) | r;
    return (r << 16) | (g << 8) | b; /* XRGB8888 / ARGB8888 */
}

static int dump_source_ppm(const char *path, const void *data, int w, int h,
                           uint32_t stride, uint32_t format) {
    FILE *f = fopen(path, "wb");
    if (!f) { logmsg("dump-source open %s failed: %s", path, strerror(errno)); return -1; }
    fprintf(f, "P6\n%d %d\n255\n", w, h);
    const uint8_t *base = data;
    for (int y = 0; y < h; y++) {
        const uint32_t *row = (const uint32_t *)(base + (size_t)y * stride);
        for (int x = 0; x < w; x++) {
            uint32_t v = row[x], r, g, b;
            if (format == WL_SHM_FORMAT_XBGR8888 || format == WL_SHM_FORMAT_ABGR8888) {
                b = (v >> 16) & 0xffu; g = (v >> 8) & 0xffu; r = v & 0xffu;
            } else {
                r = (v >> 16) & 0xffu; g = (v >> 8) & 0xffu; b = v & 0xffu;
            }
            uint8_t rgb[3] = { (uint8_t)r, (uint8_t)g, (uint8_t)b };
            fwrite(rgb, 1, 3, f);
        }
    }
    fclose(f);
    logmsg("dumped raw source %s (%dx%d stride=%u format=0x%x)", path, w, h, stride, format);
    return 0;
}

static int dump_output_ppm(const char *path, const uint32_t *pix, int w, int h,
                           int stride_words) {
    FILE *f = fopen(path, "wb");
    if (!f) { logmsg("dump-output open %s failed: %s", path, strerror(errno)); return -1; }
    fprintf(f, "P6\n%d %d\n255\n", w, h);
    for (int y = 0; y < h; y++) {
        const uint32_t *row = pix + (size_t)y * stride_words;
        for (int x = 0; x < w; x++) {
            uint32_t r, g, b;
            unpack_rgb(row[x], &r, &g, &b);
            uint8_t rgb[3] = { (uint8_t)r, (uint8_t)g, (uint8_t)b };
            fwrite(rgb, 1, 3, f);
        }
    }
    fclose(f);
    logmsg("dumped converted scanout %s (%dx%d)", path, w, h);
    return 0;
}

static int test_pattern_selftest(void) {
    static const struct { const char *name; uint32_t r, g, b; } colours[] = {
        {"black", 0,0,0}, {"white",255,255,255}, {"red",255,0,0},
        {"green",0,255,0}, {"blue",0,0,255}, {"cyan",0,255,255},
        {"magenta",255,0,255}, {"yellow",255,255,0}, {"midgrey",128,128,128},
        {"darkgrey",32,32,32}, {"lightgrey",224,224,224},
    };
    static const uint32_t formats[] = {WL_SHM_FORMAT_XRGB8888,
        WL_SHM_FORMAT_ARGB8888, WL_SHM_FORMAT_XBGR8888, WL_SHM_FORMAT_ABGR8888};
    int failures = 0;
    int orders[2] = {1, 0};
    for (int oi = 0; oi < 2; oi++) {
        color_order_argb = orders[oi];
        fb.r_off = color_order_argb ? 16u : 0u;
        fb.g_off = 8u;
        fb.b_off = color_order_argb ? 0u : 16u;
        fb.a_off = 24u;
        /* The caller-side format must match the word the bridge packs:
         * 0xAARRGGBB -> BGRA_8888 -> IDMA ARGB_8888
         * 0xAABBGGRR -> RGBA_8888 -> IDMA ABGR_8888. */
        fb.decon_format = color_order_argb ? DEXT_FMT_BGRA8888 : DEXT_FMT_RGBA8888;
        fb.black = 0xff000000u;
        build_lut(WL_SHM_FORMAT_XRGB8888);
        for (size_t fi = 0; fi < sizeof(formats)/sizeof(formats[0]); fi++) {
            for (size_t ci = 0; ci < sizeof(colours)/sizeof(colours[0]); ci++) {
                uint32_t src = source_word(formats[fi], colours[ci].r,
                                           colours[ci].g, colours[ci].b);
                uint32_t out = convert_word(src, formats[fi]);
                uint32_t r, g, b;
                unpack_rgb(out, &r, &g, &b);
                int ok = (r == colours[ci].r && g == colours[ci].g && b == colours[ci].b);
                printf("%s order=%s fmt=0x%x colour=%-9s src=0x%08x out=0x%08x decoded=%u,%u,%u\n",
                       ok ? "PASS" : "FAIL", color_order_argb ? "argb" : "abgr",
                       formats[fi], colours[ci].name, src, out, r, g, b);
                if (!ok) failures++;
            }
        }
    }
    printf("colour selftest: %s (%d failures)\n", failures ? "FAIL" : "PASS", failures);
    return failures ? 1 : 0;
}

/* Fill one double-buffer half with a deterministic TV test pattern. */
static void write_test_pattern(uint32_t *dst, int w, int h, int line_words) {
    static const uint32_t bars[8][3] = {
        {255,255,255}, {255,255,0}, {0,255,255}, {0,255,0},
        {255,0,255}, {255,0,0}, {0,0,255}, {0,0,0},
    };
    int bars_h = (strcmp(test_pattern, "grey") == 0) ? 0 : (h * 3) / 4;
    for (int y = 0; y < h; y++) {
        uint32_t *row = dst + (size_t)y * line_words;
        for (int x = 0; x < w; x++) {
            uint32_t r, g, b;
            if (y < bars_h) {
                int idx = (x * 8) / w;
                if (idx > 7) idx = 7;
                r = bars[idx][0]; g = bars[idx][1]; b = bars[idx][2];
            } else {
                int idx = (x * 16) / w;
                if (idx > 15) idx = 15;
                uint32_t v = (uint32_t)(idx * 255 / 15);
                r = g = b = v;
            }
            row[x] = pack_rgb(r, g, b);
        }
    }
}

/* ---- source -> destination index map ----------------------------------- */
static int32_t *src_index;
static size_t src_index_count;
static int map_sw, map_sh, map_dw, map_dh, map_rot;
static uint32_t map_stride;

static void build_map(int sw, int sh, uint32_t sstride) {
    int rw = (rotation == 90 || rotation == 270) ? sh : sw;
    int rh = (rotation == 90 || rotation == 270) ? sw : sh;
    int dw = (int)fb.w, dh = (int)fb.h;
    if (dw <= 0 || dh <= 0 || sw <= 0 || sh <= 0) return;
    if ((int)fb.bpp != 32) {
        logmsg("unsupported framebuffer bpp=%u", fb.bpp);
        return;
    }
    int fill = (fit_mode_name && strcmp(fit_mode_name, "fill") == 0);
    double scale = fill ? fmax((double)dw / (double)rw, (double)dh / (double)rh)
                        : fmin((double)dw / (double)rw, (double)dh / (double)rh);
    if (scale <= 0.0) return;
    int content_w = (int)lround((double)rw * scale);
    int content_h = (int)lround((double)rh * scale);
    if (content_w > dw) content_w = dw;
    if (content_h > dh) content_h = dh;
    int off_x = (dw - content_w) / 2;
    int off_y = (dh - content_h) / 2;

    if (src_index_count < (size_t)dw * (size_t)dh) {
        free(src_index);
        src_index = malloc(sizeof(int32_t) * (size_t)dw * (size_t)dh);
        src_index_count = (size_t)dw * (size_t)dh;
        if (!src_index) { src_index_count = 0; return; }
    }
    int src_stride_words = (int)(sstride / 4);
    for (int dy = 0; dy < dh; dy++) {
        for (int dx = 0; dx < dw; dx++) {
            int32_t idx = -1;
            if (dx >= off_x && dx < off_x + content_w &&
                dy >= off_y && dy < off_y + content_h) {
                int rx = (int)((double)(dx - off_x) / scale);
                int ry = (int)((double)(dy - off_y) / scale);
                if (rx >= rw) rx = rw - 1;
                if (ry >= rh) ry = rh - 1;
                int sx = 0, sy = 0;
                switch (rotation) {
                case 90:  sx = ry;          sy = sh - 1 - rx; break;
                case 180: sx = sw - 1 - rx; sy = sh - 1 - ry; break;
                case 270: sx = sw - 1 - ry; sy = rx;          break;
                default:  sx = rx;          sy = ry;          break;
                }
                if (sx >= 0 && sx < sw && sy >= 0 && sy < sh)
                    idx = sy * src_stride_words + sx;
            }
            src_index[(size_t)dy * dw + dx] = idx;
        }
    }
    map_sw = sw; map_sh = sh; map_dw = dw; map_dh = dh;
    map_rot = rotation; map_stride = sstride;
    logmsg("map src=%dx%d dst=%dx%d scale=%.3f content=%dx%d offset=%d,%d rot=%d fit=%s",
           sw, sh, dw, dh, scale, content_w, content_h, off_x, off_y, rotation, fit_mode_name);
}

static void blit(const void *data, int sw, int sh, uint32_t sstride, uint32_t format) {
    if (fb_refresh() < 0 || !fb.map) return;
    if (!src_index || map_sw != sw || map_sh != sh || map_dw != (int)fb.w ||
        map_dh != (int)fb.h || map_rot != rotation || map_stride != sstride)
        build_map(sw, sh, sstride);
    if (!src_index) return;
    const uint32_t *src = data;
    int dw = (int)fb.w;
    int line_words = (int)(fb.line / 4);
    size_t half_words = (size_t)line_words * fb.h;
    uint32_t *dst = (uint32_t *)fb.map + (size_t)fb.half * half_words;
    for (int dy = 0; dy < (int)fb.h; dy++) {
        uint32_t *row = dst + (size_t)dy * line_words;
        const int32_t *m = src_index + (size_t)dy * dw;
        for (int dx = 0; dx < dw; dx++) {
            int32_t idx = m[dx];
            row[dx] = (idx < 0) ? fb.black : convert_word(src[idx], format);
        }
    }
    if (dump_source_path) {
        dump_source_ppm(dump_source_path, data, sw, sh, sstride, format);
        dump_source_path = NULL;
    }
    if (dump_output_path) {
        dump_output_ppm(dump_output_path, dst, dw, (int)fb.h, line_words);
        dump_output_path = NULL;
    }
    /* Sample the half we just wrote.  This is the exact dma-buf region the
     * decon will scan, so a non-zero count proves it is not black. */
    size_t nz = 0;
    for (size_t i = 0; i < half_words; i += 97)
        if (dst[i] & 0x00ffffffu) nz++;
    dbg_nz = nz;

    /* Never submit against a link that has already gone away.  This is the
     * userspace half of disconnect safety; the vendor driver still has a
     * fatal BUG() on a shadow-update timeout, so the kernel patch in this
     * mission removes that BUG as well.
     *
     * A deliberate FBIOBLANK powerdown/unblank during bridge startup can
     * briefly clear secdp/extcon even though the cable is still attached.
     * Require several consecutive failures (250 ms at 20 fps) before calling
     * the link dead; a real unplug is still detected well within half a
     * second, while the self-induced transient is ignored. */
    if (link_watch && !dext_link_ok()) {
        if (++link_fail_count < 5) {
            return;
        }
        running = 0;
        write_state("state STOPPED reason=DP_LINK_LOST frames=%d", 0);
        logmsg("DP link lost after %d consecutive checks; stopping before "
               "submitting another frame", link_fail_count);
        return;
    } else {
        link_fail_count = 0;
    }
    /* Hand the freshly written half to decon2, then write into the other. */
    if (dp_win_submit((uint32_t)fb.half * fb.h) < 0)
        logmsg("decon2 win config failed: %s", strerror(errno));
    fb.half ^= 1;
}

/* ---- screencopy -------------------------------------------------------- */
static int make_shm(struct shmbuf *b, int w, int h, uint32_t stride, uint32_t format) {
    memset(b, 0, sizeof(*b));
    b->size = (size_t)stride * (size_t)h;
    b->fd = (int)syscall(SYS_memfd_create, "nuxel-wl-fb-ext", MFD_CLOEXEC);
    if (b->fd < 0) {
        logmsg("memfd_create failed: %s", strerror(errno));
        return -1;
    }
    if (ftruncate(b->fd, (off_t)b->size) < 0) {
        logmsg("ftruncate failed: %s", strerror(errno));
        close(b->fd); b->fd = -1; return -1;
    }
    b->data = mmap(NULL, b->size, PROT_READ | PROT_WRITE, MAP_SHARED, b->fd, 0);
    if (b->data == MAP_FAILED) {
        logmsg("shm mmap failed: %s", strerror(errno));
        b->data = NULL; close(b->fd); b->fd = -1; return -1;
    }
    struct wl_shm_pool *pool = wl_shm_create_pool(shm, b->fd, (int32_t)b->size);
    if (!pool) { munmap(b->data, b->size); close(b->fd); b->fd = -1; return -1; }
    b->buffer = wl_shm_pool_create_buffer(pool, 0, w, h, (int32_t)stride, format);
    wl_shm_pool_destroy(pool);
    if (!b->buffer) { munmap(b->data, b->size); close(b->fd); b->fd = -1; return -1; }
    b->w = w; b->h = h; b->stride = (int32_t)stride; b->format = format;
    return 0;
}

static void free_shm(struct shmbuf *b) {
    if (!b) return;
    if (b->buffer) wl_buffer_destroy(b->buffer);
    if (b->data && b->data != MAP_FAILED) munmap(b->data, b->size);
    if (b->fd >= 0) close(b->fd);
    memset(b, 0, sizeof(*b));
    b->fd = -1;
}

static void frame_buffer(void *data, struct zwlr_screencopy_frame_v1 *frame,
                         uint32_t format, uint32_t w, uint32_t h, uint32_t stride) {
    (void)frame;
    struct frame_state *fs = data;
    if (fs->buf) return;
    struct shmbuf *b = calloc(1, sizeof(*b));
    if (!b) { fs->failed = 1; return; }
    b->fd = -1;
    if (make_shm(b, (int)w, (int)h, stride, format) < 0) {
        free(b); fs->failed = 1; return;
    }
    fs->buf = b;
    /* The buffer event only announces the layout; the copy request is what
       actually asks the compositor to fill our wl_buffer. */
    zwlr_screencopy_frame_v1_copy(frame, b->buffer);
}

static void frame_flags(void *data, struct zwlr_screencopy_frame_v1 *frame,
                        uint32_t flags) {
    (void)frame;
    struct frame_state *fs = data;
    fs->y_invert = (flags & ZWLR_SCREENCOPY_FRAME_V1_FLAGS_Y_INVERT) != 0;
}
static void frame_ready(void *data, struct zwlr_screencopy_frame_v1 *frame,
                        uint32_t tv_sec_hi, uint32_t tv_sec_lo, uint32_t tv_nsec) {
    (void)frame; (void)tv_sec_hi; (void)tv_sec_lo; (void)tv_nsec;
    ((struct frame_state *)data)->ready = 1;
}
static void frame_failed(void *data, struct zwlr_screencopy_frame_v1 *frame) {
    (void)frame;
    ((struct frame_state *)data)->failed = 1;
}
static void frame_damage(void *data, struct zwlr_screencopy_frame_v1 *frame,
                         uint32_t x, uint32_t y, uint32_t w, uint32_t h) {
    (void)data; (void)frame; (void)x; (void)y; (void)w; (void)h;
}
static void frame_linux_dmabuf(void *data, struct zwlr_screencopy_frame_v1 *frame,
                               uint32_t format, uint32_t w, uint32_t h) {
    (void)data; (void)frame; (void)format; (void)w; (void)h;
}
static void frame_buffer_done(void *data, struct zwlr_screencopy_frame_v1 *frame) {
    (void)data; (void)frame;
}

static const struct zwlr_screencopy_frame_v1_listener frame_listener = {
    .buffer = frame_buffer,
    .flags = frame_flags,
    .ready = frame_ready,
    .failed = frame_failed,
    .damage = frame_damage,
    .linux_dmabuf = frame_linux_dmabuf,
    .buffer_done = frame_buffer_done,
};

/* ---- main -------------------------------------------------------------- */
static void usage(const char *argv0) {
    fprintf(stderr,
        "usage: %s [--mode mirror-portrait|mirror-landscape|fullscreen|desktop]\n"
        "          [--output NAME] [--fb /dev/fb1] [--resolution WxH]\n"
        "          [--fit fit|fill] [--fps N] [--rotate 0|90|180|270]\n"
        "          [--auto-orientation] [--orientation-file PATH]\n"
        "          [--color-order argb|abgr] [--test-pattern bars|grey]\n"
        "          [--dump-source PATH] [--dump-output PATH]\n"
        "          [--selftest-colour] [--no-link-watch] [--list-outputs] [--once]\n",
        argv0);
}

int main(int argc, char **argv) {
    enum {
        OPT_COLOR_ORDER = 1000,
        OPT_AUTO_ORIENTATION,
        OPT_ORIENTATION_FILE,
        OPT_TEST_PATTERN,
        OPT_DUMP_SOURCE,
        OPT_DUMP_OUTPUT,
        OPT_SELFTEST_COLOUR,
    };
    static const struct option opts[] = {
        {"mode", required_argument, 0, 'm'},
        {"output", required_argument, 0, 'o'},
        {"fb", required_argument, 0, 'f'},
        {"resolution", required_argument, 0, 's'},
        {"fit", required_argument, 0, 'F'},
        {"fps", required_argument, 0, 'p'},
        {"rotate", required_argument, 0, 'r'},
        {"color-order", required_argument, 0, OPT_COLOR_ORDER},
        {"auto-orientation", no_argument, 0, OPT_AUTO_ORIENTATION},
        {"orientation-file", required_argument, 0, OPT_ORIENTATION_FILE},
        {"test-pattern", required_argument, 0, OPT_TEST_PATTERN},
        {"dump-source", required_argument, 0, OPT_DUMP_SOURCE},
        {"dump-output", required_argument, 0, OPT_DUMP_OUTPUT},
        {"selftest-colour", no_argument, 0, OPT_SELFTEST_COLOUR},
        {"no-link-watch", no_argument, 0, 'W'},
        {"list-outputs", no_argument, 0, 'l'},
        {"once", no_argument, 0, '1'},
        {"help", no_argument, 0, 'h'},
        {0, 0, 0, 0}
    };
    int c;
    while ((c = getopt_long(argc, argv, "m:o:f:s:F:p:r:Wl1h", opts, NULL)) != -1) {
        switch (c) {
        case 'm': mode_name = optarg; break;
        case 'o': snprintf(wanted_output, sizeof(wanted_output), "%s", optarg); break;
        case 'f': fb_path = optarg; break;
        case 's': {
            unsigned int w = 0, h = 0;
            if (sscanf(optarg, "%ux%u", &w, &h) == 2) { out_width = (int)w; out_height = (int)h; }
            else { logmsg("invalid --resolution %s", optarg); return 2; }
            break;
        }
        case 'F': fit_mode_name = optarg; break;
        case 'p': target_fps = atoi(optarg); break;
        case 'r': rotation = atoi(optarg); rotation_set = 1; break;
        case OPT_COLOR_ORDER:
            if (strcmp(optarg, "argb") == 0) color_order_argb = 1;
            else if (strcmp(optarg, "abgr") == 0) color_order_argb = 0;
            else { logmsg("invalid --color-order %s (argb|abgr)", optarg); return 2; }
            break;
        case OPT_AUTO_ORIENTATION: auto_orientation = 1; break;
        case OPT_ORIENTATION_FILE: orientation_path = optarg; break;
        case OPT_TEST_PATTERN:
            if (strcmp(optarg, "bars") != 0 && strcmp(optarg, "grey") != 0) {
                logmsg("invalid --test-pattern %s (bars|grey)", optarg); return 2;
            }
            test_pattern = optarg;
            break;
        case OPT_DUMP_SOURCE: dump_source_path = optarg; break;
        case OPT_DUMP_OUTPUT: dump_output_path = optarg; break;
        case OPT_SELFTEST_COLOUR: color_selftest = 1; break;
        case 'W': link_watch = 0; break;
        case 'l': capture_once = 2; break;
        case '1': capture_once = 1; break;
        case 'h': usage(argv[0]); return 0;
        default: usage(argv[0]); return 2;
        }
    }
    if (target_fps < 1) target_fps = 1;
    if (target_fps > 120) target_fps = 120;
    if (rotation != 0 && rotation != 90 && rotation != 180 && rotation != 270) {
        logmsg("invalid rotation %d", rotation);
        return 2;
    }
    if (strcmp(fit_mode_name, "fit") != 0 && strcmp(fit_mode_name, "fill") != 0) {
        logmsg("invalid --fit %s (fit|fill)", fit_mode_name);
        return 2;
    }
    if (color_selftest) {
        int rc = test_pattern_selftest();
        return rc;
    }
    /* Mode defaults.  Explicit --rotate wins; --auto-orientation overrides
     * both and re-reads the authoritative orientation every frame. */
    if (!rotation_set && !auto_orientation) {
        if (strcmp(mode_name, "mirror-landscape") == 0 ||
            strcmp(mode_name, "landscape") == 0 ||
            strcmp(mode_name, "fullscreen") == 0)
            rotation = 90;
        else
            rotation = 0;
    }
    if (strcmp(mode_name, "fullscreen") == 0)
        fit_mode_name = "fill";
    if (strcmp(mode_name, "landscape") == 0)
        mode_name = "mirror-landscape";
    if (strcmp(mode_name, "mirror") == 0)
        mode_name = "mirror-portrait";

    signal(SIGTERM, on_signal);
    signal(SIGINT, on_signal);
    write_state("state STARTING mode=%s output=%s fb=%s fps=%d rot=%d fit=%s resolution=%s",
                mode_name, wanted_output[0] ? wanted_output : "auto", fb_path,
                target_fps, rotation, fit_mode_name,
                (out_width && out_height) ? "requested" : "auto");

    int lockfd = open(LOCK_PATH, O_CREAT | O_RDWR | O_CLOEXEC, 0600);
    if (lockfd < 0 || flock(lockfd, LOCK_EX | LOCK_NB) < 0) {
        write_state("state FAILED reason=FB1_OWNER_BUSY");
        logmsg("another /dev/fb1 writer holds %s", LOCK_PATH);
        return 3;
    }

    display = wl_display_connect(NULL);
    if (!display) {
        write_state("state FAILED reason=WAYLAND_CONNECT_FAILED");
        logmsg("wayland connect failed (XDG_RUNTIME_DIR=%s WAYLAND_DISPLAY=%s)",
               getenv("XDG_RUNTIME_DIR") ?: "?", getenv("WAYLAND_DISPLAY") ?: "?");
        return 4;
    }
    registry = wl_display_get_registry(display);
    wl_registry_add_listener(registry, &registry_listener, NULL);
    wl_display_roundtrip(display);
    wl_display_roundtrip(display);
    if (!compositor || !shm || !scm) {
        write_state("state FAILED reason=WL_GLOBALS_MISSING compositor=%d shm=%d screencopy=%d",
                    !!compositor, !!shm, !!scm);
        logmsg("missing Wayland globals");
        return 5;
    }
    if (capture_once == 2) {
        for (int i = 0; i < noutputs; i++)
            printf("%s\t%d\t%d\t%d\t%d\t%d\n", outputs[i].name,
                   outputs[i].width, outputs[i].height, outputs[i].refresh,
                   outputs[i].x, outputs[i].y);
        return 0;
    }
    struct output *out = pick_output();
    if (!out) {
        write_state("state FAILED reason=OUTPUT_NOT_FOUND wanted=%s available=%d",
                    wanted_output[0] ? wanted_output : "(auto)", noutputs);
        logmsg("requested output not found (wanted=%s, %d outputs)",
               wanted_output[0] ? wanted_output : "auto", noutputs);
        for (int i = 0; i < noutputs; i++)
            logmsg("  output[%d]=%s %dx%d", i, outputs[i].name,
                   outputs[i].width, outputs[i].height);
        return 6;
    }
    logmsg("capturing output %s %dx%d mode=%s", out->name, out->width, out->height, mode_name);

    if (fb_open() < 0) {
        write_state("state FAILED reason=FB_OPEN_FAILED fb=%s", fb_path);
        return 7;
    }

    write_state("state STARTING mode=%s output=%s fb=%s color=%s auto_orientation=%d",
                mode_name, out->name, fb_path,
                color_order_argb ? "argb" : "abgr", auto_orientation);
    struct timespec next;
    clock_gettime(CLOCK_MONOTONIC, &next);
    long period_ns = 1000000000L / target_fps;
    int frame_no = 0;
    int consecutive_failures = 0;

    while (running) {
        update_orientation();
        if (test_pattern) {
            if (link_watch && !dext_link_ok()) {
                write_state("state STOPPED reason=DP_LINK_LOST frames=%d", frame_no);
                logmsg("DP link lost during test pattern");
                break;
            }
            int line_words = (int)(fb.line / 4);
            size_t half_words = (size_t)line_words * fb.h;
            uint32_t *dst = (uint32_t *)fb.map + (size_t)fb.half * half_words;
            write_test_pattern(dst, (int)fb.w, (int)fb.h, line_words);
            size_t nz = 0;
            for (size_t i = 0; i < half_words; i += 97)
                if (dst[i] & 0x00ffffffu) nz++;
            if (dp_win_submit((uint32_t)fb.half * fb.h) < 0)
                logmsg("decon2 test-pattern submit failed: %s", strerror(errno));
            fb.half ^= 1;
            frame_no++;
            if (frame_no == 1 || (frame_no % target_fps) == 0) {
                write_state("state RUNNING mode=test-%s output=%s fb=%s "
                            "dst=%ux%u fps=%d frames=%d nz=%zu color=%s",
                            test_pattern, out->name, fb_path, fb.w, fb.h,
                            target_fps, frame_no, nz,
                            color_order_argb ? "argb" : "abgr");
                logmsg("test-pattern %s frame %d dst=%ux%u nz=%zu",
                       test_pattern, frame_no, fb.w, fb.h, nz);
            }
            if (capture_once == 1) break;
            clock_gettime(CLOCK_MONOTONIC, &next);
            next.tv_nsec += period_ns;
            while (next.tv_nsec >= 1000000000L) { next.tv_nsec -= 1000000000L; next.tv_sec++; }
            struct timespec now;
            clock_gettime(CLOCK_MONOTONIC, &now);
            long sleep_ns = (next.tv_sec - now.tv_sec) * 1000000000L + (next.tv_nsec - now.tv_nsec);
            if (sleep_ns > 0) {
                struct timespec ts = {sleep_ns / 1000000000L, sleep_ns % 1000000000L};
                nanosleep(&ts, NULL);
            } else {
                clock_gettime(CLOCK_MONOTONIC, &next);
            }
            continue;
        }
        struct frame_state fs;
        memset(&fs, 0, sizeof(fs));
        fs.buf = NULL;
        struct zwlr_screencopy_frame_v1 *frame =
            zwlr_screencopy_manager_v1_capture_output(scm, 1, out->wl);
        if (!frame) {
            write_state("state FAILED reason=CAPTURE_REQUEST_FAILED");
            logmsg("capture_output failed");
            break;
        }
        zwlr_screencopy_frame_v1_add_listener(frame, &frame_listener, &fs);
        int wait_ms = 1500;
        while (running && !fs.ready && !fs.failed) {
            wl_display_dispatch_pending(display);
            if (wl_display_flush(display) < 0) break;
            struct pollfd pfd = {.fd = wl_display_get_fd(display), .events = POLLIN};
            int pr = poll(&pfd, 1, wait_ms);
            if (pr < 0 && errno != EINTR) break;
            if (pr == 0) { fs.failed = 1; break; }
            if (pr > 0 && wl_display_dispatch(display) < 0) { fs.failed = 1; break; }
        }
        if (fs.ready && fs.buf) {
            blit(fs.buf->data, fs.buf->w, fs.buf->h, (uint32_t)fs.buf->stride,
                 fs.buf->format);
            frame_no++;
            consecutive_failures = 0;
            if (frame_no == 1 || (frame_no % target_fps) == 0) {
                        write_state("state RUNNING mode=%s output=%s fb=%s src=%dx%d dst=%ux%u fps=%d rot=%d fit=%s frames=%d nz=%zu color=%s orient_eff=%d orient_tf=%d",
                            mode_name, out->name, fb_path, fs.buf->w, fs.buf->h,
                            fb.w, fb.h, target_fps, rotation, fit_mode_name, frame_no, dbg_nz,
                            color_order_argb ? "argb" : "abgr",
                            orientation_effective, orientation_transform);
                logmsg("frame %d src=%dx%d dst=%ux%u nz=%zu", frame_no, fs.buf->w,
                       fs.buf->h, fb.w, fb.h, dbg_nz);
            }
        } else {
            consecutive_failures++;
            logmsg("capture failed (%d consecutive)", consecutive_failures);
            if (consecutive_failures >= 10) {
                write_state("state FAILED reason=CAPTURE_FAILED consecutive=%d", consecutive_failures);
                zwlr_screencopy_frame_v1_destroy(frame);
                free_shm(fs.buf); free(fs.buf);
                break;
            }
        }
        zwlr_screencopy_frame_v1_destroy(frame);
        free_shm(fs.buf);
        free(fs.buf);
        if (capture_once == 1) break;

        clock_gettime(CLOCK_MONOTONIC, &next);
        next.tv_nsec += period_ns;
        while (next.tv_nsec >= 1000000000L) { next.tv_nsec -= 1000000000L; next.tv_sec++; }
        struct timespec now;
        clock_gettime(CLOCK_MONOTONIC, &now);
        long sleep_ns = (next.tv_sec - now.tv_sec) * 1000000000L + (next.tv_nsec - now.tv_nsec);
        if (sleep_ns > 0) {
            struct timespec ts = {sleep_ns / 1000000000L, sleep_ns % 1000000000L};
            nanosleep(&ts, NULL);
        } else {
            clock_gettime(CLOCK_MONOTONIC, &next);
        }
    }

    fb_clear();
    if (capture_once != 1)
        fb_powerdown();
    if (capture_once == 1)
        write_state("state STOPPED reason=once frames=%d", frame_no);
    else
        write_state("state STOPPED reason=%s frames=%d",
                    got_signal ? "signal" : "error", frame_no);
    logmsg("stopped frames=%d", frame_no);
    fb_release();
    zwlr_screencopy_manager_v1_destroy(scm);
    for (int i = 0; i < noutputs; i++)
        if (outputs[i].wl) wl_output_destroy(outputs[i].wl);
    wl_shm_destroy(shm);
    wl_compositor_destroy(compositor);
    wl_registry_destroy(registry);
    wl_display_disconnect(display);
    flock(lockfd, LOCK_UN);
    close(lockfd);
    return 0;
}
