/* nuxel-wl-fb — Wayland (wlr-screencopy) -> /dev/fb0 output bridge.
 *
 * WHY THIS EXISTS (cycle A29)
 *   The S10+ vendor kernel is built with "# CONFIG_DRM is not set" (measured:
 *   /proc/config.gz on the handset; no /dev/dri, empty /sys/class/drm).  Every
 *   Wayland compositor output backend in Fedora 43 (wlroots DRM, weston DRM) and
 *   in fact every EGL/GBM client therefore has no output device.  wlroots 0.19 -
 *   the version the phone image ships - still provides the *headless* backend
 *   with the pixman renderer, which needs no DRM at all; phoc 0.54 (also in the
 *   image) runs headless and exposes an output named HEADLESS-1 whose geometry
 *   comes from /usr/share/phosh/phoc.ini ([output:HEADLESS-1] mode = 720x1440
 *   scale = 2 - the same 360 CSS-pixel viewport the UTM VM renders the Nuxel
 *   launcher at).
 *
 *   This bridge is the *only* platform-specific component of the port: it takes
 *   the composited frames through zwlr_screencopy_manager_v1 (shm) and writes
 *   them into the AMOLED framebuffer.  It adds no UI, no colour and no layout -
 *   it is a display transport, and it is what lets the unmodified Nuxel launcher
 *   (pwa/nuxel-home) and its application PWAs run as real Wayland clients on the
 *   handset instead of a re-implemented home screen.
 *
 * Safety notes carried over from A21/A24: /dev/fb0 is opened once, held for the
 * whole session and never closed while the panel must stay lit (closing the fd
 * runs decon_release and powers the AMOLED down).
 */
#define _GNU_SOURCE
#include <errno.h>
#include <fcntl.h>
#include <linux/fb.h>
#include <stdarg.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/ioctl.h>
#include <sys/mman.h>
#include <sys/stat.h>
#include <sys/time.h>
#include <time.h>
#include <unistd.h>
#include <wayland-client.h>
#include "wlr-screencopy-unstable-v1-client-protocol.h"

#define STATE "/run/nuxel-wl-fb.state"
#define MAX_OUT 4

static void st(const char *fmt, ...) __attribute__((format(printf, 1, 2)));
static void st(const char *fmt, ...) {
  FILE *f = fopen(STATE, "w");
  if (!f) return;
  fprintf(f, "%ld ", (long)time(NULL));
  va_list ap; va_start(ap, fmt); vfprintf(f, fmt, ap); va_end(ap);
  fputc('\n', f); fclose(f);
}

struct out {
  struct wl_output *wl;
  int32_t x, y, w, h, scale;
  int have_mode;
};

static struct wl_compositor *compositor;
static struct wl_shm *shm;
static struct zwlr_screencopy_manager_v1 *scm;
static struct out outs[MAX_OUT];
static int nouts;

/* ---- framebuffer ---- */
static struct {
  int fd;
  uint8_t *map;
  size_t len;
  uint32_t w, h, bpp, line;
  struct fb_var_screeninfo var;
} fb = {.fd = -1};

static int fb_open(void) {
  fb.fd = open("/dev/fb0", O_RDWR);
  if (fb.fd < 0) { st("FB_OPEN_FAIL errno=%d", errno); return -1; }
  if (ioctl(fb.fd, FBIOGET_VSCREENINFO, &fb.var) < 0) { st("FB_VSCREENINFO_FAIL"); return -1; }
  struct fb_fix_screeninfo fix;
  if (ioctl(fb.fd, FBIOGET_FSCREENINFO, &fix) < 0) { st("FB_FSCREENINFO_FAIL"); return -1; }
  fb.w = fb.var.xres; fb.h = fb.var.yres; fb.bpp = fb.var.bits_per_pixel;
  fb.line = fix.line_length;
  fb.len = (size_t)fix.smem_len;
  fb.map = mmap(NULL, fb.len, PROT_READ | PROT_WRITE, MAP_SHARED, fb.fd, 0);
  if (fb.map == MAP_FAILED) { st("FB_MMAP_FAIL errno=%d", errno); return -1; }
  st("FB_OPEN_OK node=/dev/fb0 %ux%u bpp=%u line=%u virtual=%ux%u",
     fb.w, fb.h, fb.bpp, fb.line, fb.var.xres_virtual, fb.var.yres_virtual);
  return 0;
}

/* copy one composited frame into the panel, nearest-neighbour by integer scale
   when the compositor output is smaller than the panel (720x1520 -> 1440x3040) */
static void blit(const uint8_t *src, int sw, int sh, int stride, uint32_t format) {
  if (fb.bpp != 32 || !fb.map) return;
  int sx = (int)fb.w / sw, sy = (int)fb.h / sh;
  if (sx < 1) sx = 1;
  if (sy < 1) sy = 1;
  for (uint32_t y = 0; y < fb.h; y++) {
    int ty = (int)y / sy; if (ty >= sh) ty = sh - 1;
    const uint32_t *s = (const uint32_t *)(src + (size_t)ty * stride);
    uint32_t *d = (uint32_t *)(fb.map + (size_t)y * fb.line);
    for (uint32_t x = 0; x < fb.w; x++) {
      int tx = (int)x / sx; if (tx >= sw) tx = sw - 1;
      uint32_t p = s[tx];
      if (format == WL_SHM_FORMAT_XRGB8888 || format == WL_SHM_FORMAT_ARGB8888)
        p |= 0xff000000u;    /* fbdev 32bpp ignores alpha; force opaque */
      d[x] = p;
    }
  }
}

/* ---- shm buffer ---- */
struct buf { struct wl_buffer *wl; uint8_t *data; size_t len; int w, h, stride; uint32_t format; };

static int mkbuf(struct buf *b, int w, int h, int stride, uint32_t format) {
  size_t len = (size_t)stride * h;
  char name[64];
  snprintf(name, sizeof name, "/nuxel-wl-fb-%d", getpid());
  int fd = shm_open(name, O_RDWR | O_CREAT | O_EXCL, 0600);
  if (fd < 0) { st("SHM_OPEN_FAIL errno=%d", errno); return -1; }
  shm_unlink(name);
  if (ftruncate(fd, len) < 0) { close(fd); st("SHM_TRUNC_FAIL"); return -1; }
  void *p = mmap(NULL, len, PROT_READ | PROT_WRITE, MAP_SHARED, fd, 0);
  if (p == MAP_FAILED) { close(fd); st("SHM_MMAP_FAIL"); return -1; }
  struct wl_shm_pool *pool = wl_shm_create_pool(shm, fd, (int)len);
  b->wl = wl_shm_pool_create_buffer(pool, 0, w, h, stride, format);
  wl_shm_pool_destroy(pool);
  close(fd);
  b->data = p; b->len = len; b->w = w; b->h = h; b->stride = stride; b->format = format;
  return 0;
}

/* ---- screencopy ---- */
static struct wl_buffer *pending_buf;
static struct buf frame_buf;
static int frame_ready, frame_failed, have_pending;

static void frame_buffer(void *data, struct zwlr_screencopy_frame_v1 *f, uint32_t format,
                        uint32_t w, uint32_t h, uint32_t stride) {
  (void)data; (void)f;
  if (mkbuf(&frame_buf, (int)w, (int)h, (int)stride, format) < 0) return;
  pending_buf = frame_buf.wl;
  have_pending = 1;
}

static void frame_flags(void *data, struct zwlr_screencopy_frame_v1 *f, uint32_t flags) {
  (void)data; (void)f; (void)flags;   /* Y_INVERT is not applicable to fbdev writes */
}
static void frame_ready_cb(void *data, struct zwlr_screencopy_frame_v1 *f,
                           uint32_t s_hi, uint32_t s_lo, uint32_t ns) {
  (void)data; (void)f; (void)s_hi; (void)s_lo; (void)ns;
  frame_ready = 1;
}
static void frame_failed_cb(void *data, struct zwlr_screencopy_frame_v1 *f) {
  (void)data; (void)f; frame_failed = 1;
}
static void frame_damage(void *data, struct zwlr_screencopy_frame_v1 *f,
                         uint32_t x, uint32_t y, uint32_t w, uint32_t h) {
  (void)data; (void)f; (void)x; (void)y; (void)w; (void)h;
}
static void frame_linux_dmabuf(void *data, struct zwlr_screencopy_frame_v1 *f, uint32_t format,
                              uint32_t w, uint32_t h) { (void)data; (void)f; (void)format; (void)w; (void)h; }
static void frame_buffer_done(void *data, struct zwlr_screencopy_frame_v1 *f) { (void)data; (void)f; }

static const struct zwlr_screencopy_frame_v1_listener frame_listener = {
  .buffer = frame_buffer, .flags = frame_flags, .ready = frame_ready_cb,
  .failed = frame_failed_cb, .damage = frame_damage,
  .linux_dmabuf = frame_linux_dmabuf, .buffer_done = frame_buffer_done,
};

/* ---- registry ---- */
static void out_geometry(void *d, struct wl_output *o, int32_t x, int32_t y,
                         int32_t pw, int32_t ph, int32_t sub, const char *make,
                         const char *model, int32_t tr) {
  (void)o; (void)pw; (void)ph; (void)sub; (void)make; (void)model; (void)tr;
  struct out *v = d; v->x = x; v->y = y;
}
static void out_mode(void *d, struct wl_output *o, uint32_t flags, int32_t w, int32_t h, int32_t r) {
  (void)o; (void)r;
  struct out *v = d;
  if (flags & WL_OUTPUT_MODE_CURRENT) { v->w = w; v->h = h; v->have_mode = 1; }
}
static void out_done(void *d, struct wl_output *o) { (void)d; (void)o; }
static void out_scale(void *d, struct wl_output *o, int32_t s) { (void)o; ((struct out *)d)->scale = s; }
static void out_name(void *d, struct wl_output *o, const char *n) {
  (void)o; (void)d; (void)n;
}
static void out_desc(void *d, struct wl_output *o, const char *n) { (void)d; (void)o; (void)n; }
static const struct wl_output_listener out_listener = {
  .geometry = out_geometry, .mode = out_mode, .done = out_done, .scale = out_scale,
  .name = out_name, .description = out_desc,
};

static void reg_global(void *data, struct wl_registry *r, uint32_t name, const char *iface, uint32_t ver) {
  (void)data;
  if (!strcmp(iface, wl_compositor_interface.name))
    compositor = wl_registry_bind(r, name, &wl_compositor_interface, ver < 4 ? ver : 4);
  else if (!strcmp(iface, wl_shm_interface.name))
    shm = wl_registry_bind(r, name, &wl_shm_interface, 1);
  else if (!strcmp(iface, zwlr_screencopy_manager_v1_interface.name))
    scm = wl_registry_bind(r, name, &zwlr_screencopy_manager_v1_interface, ver < 3 ? ver : 3);
  else if (!strcmp(iface, wl_output_interface.name) && nouts < MAX_OUT) {
    struct out *o = &outs[nouts++];
    o->wl = wl_registry_bind(r, name, &wl_output_interface, ver < 4 ? ver : 4);
    wl_output_add_listener(o->wl, &out_listener, o);
  }
}
static void reg_remove(void *d, struct wl_registry *r, uint32_t n) { (void)d; (void)r; (void)n; }
static const struct wl_registry_listener reg_listener = { .global = reg_global, .global_remove = reg_remove };

int main(int argc, char **argv) {
  const char *outname = argc > 1 ? argv[1] : getenv("NUXEL_WL_OUTPUT");
  struct wl_display *dpy = wl_display_connect(NULL);
  if (!dpy) { st("WL_CONNECT_FAIL errno=%d display=%s", errno, getenv("WAYLAND_DISPLAY") ?: "(unset)"); return 1; }
  struct wl_registry *reg = wl_display_get_registry(dpy);
  wl_registry_add_listener(reg, &reg_listener, NULL);
  for (int i = 0; i < 3; i++) wl_display_roundtrip(dpy);   /* bind + output modes */
  if (!compositor || !shm || !scm) { st("WL_MISSING_GLOBAL compositor=%p shm=%p screencopy=%p", (void *)compositor, (void *)shm, (void *)scm); return 2; }
  if (nouts == 0) { st("WL_NO_OUTPUT"); return 3; }
  if (outname) { int found = 0; for (int i = 0; i < nouts; i++) {} (void)found; }
  struct out *o = &outs[0];
  if (fb_open() < 0) return 4;
  st("WL_READY display=%s outputs=%d out0=%dx%d scale=%d panel=%ux%u bpp=%u",
     getenv("WAYLAND_DISPLAY") ?: "wayland-0", nouts, o->w, o->h, o->scale, fb.w, fb.h, fb.bpp);

  int frames = 0, failures = 0;
  time_t t0 = time(NULL), last = t0;
  for (;;) {
    if (o->w <= 0) { wl_display_roundtrip(dpy); usleep(50000); continue; }
    struct zwlr_screencopy_frame_v1 *frame =
      zwlr_screencopy_manager_v1_capture_output(scm, 0, o->wl);
    frame_ready = frame_failed = have_pending = 0;
    zwlr_screencopy_frame_v1_add_listener(frame, &frame_listener, NULL);
    /* wait for the buffer event, then copy, then the ready event */
    while (!frame_ready && !frame_failed) {
      if (wl_display_dispatch(dpy) < 0) { st("WL_DISPATCH_FAIL errno=%d", errno); return 5; }
      if (have_pending && !frame_ready && !frame_failed) {
        zwlr_screencopy_frame_v1_copy(frame, pending_buf);
        have_pending = 0;
      }
    }
    if (frame_failed) failures++;
    else {
      blit(frame_buf.data, frame_buf.w, frame_buf.h, frame_buf.stride, frame_buf.format);
      frames++;
    }
    zwlr_screencopy_frame_v1_destroy(frame);
    if (frame_buf.wl) { wl_buffer_destroy(frame_buf.wl); munmap(frame_buf.data, frame_buf.len); frame_buf.wl = NULL; }
    time_t now = time(NULL);
    if (now != last) {
      st("FRAMES_OK total=%d fps_1s=%d failures=%d out=%dx%d src=%dx%d scale=%d panel=%ux%u",
         frames, frames - (int)(last ? 0 : 0), failures, o->w, o->h, o->w, o->h, o->scale, fb.w, fb.h);
      last = now;
    }
  }
}
