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
 *
 * REVISION A30-single-fb-owner (2026-10-16): handoff with the initramfs
 * boot-animation player before the bridge touches the panel.
 *
 * REVISION A31 (2026-10-16, beta finalizer) - four measured corrections to A30:
 *   1. NO scanout write before the stop is CONFIRMED.  A30 staged a launcher
 *      frame while the animation was still painting (`frame_blit_once()` right
 *      before ANIMATION_STOP_REQUESTED); that is itself a concurrent write.
 *   2. Stop timeout is no longer "recover anyway".  If the painter is still alive
 *      after the bounded wait the bridge sends SIGTERM then SIGKILL *only* after
 *      re-verifying executable identity, re-checks, and if the painter STILL
 *      lives it does NOT touch the panel - it writes a diagnostic and exits
 *      non-zero so the animation/fallback keeps sole ownership (mission 10.3).
 *   3. No periodic FBIOPUT_VSCREENINFO/FBIOPAN_DISPLAY every reporting interval.
 *      The bridge writes the visible buffer directly (yoffset 0, no double
 *      buffer), so the steady state needs no display reset at all; the DECON is
 *      re-asserted only when a real failure is measured (mission 10.4).
 *   4. Paced presentation (NUXEL_TARGET_FPS, default 30) with measured frame
 *      timing instead of an unbounded screencopy loop (mission 10.5).
 *
 * REVISION A32 (2026-10-16, beta hardware finalizer) - three measured fixes:
 *   5. COLOUR (mission 8.2).  A29..A31 passed the compositor's shm pixels
 *      straight into scanout.  The compositor hands this bridge XRGB8888
 *      (memory B,G,R,X, i.e. R@16 B@0) while the DECON on this panel maps
 *      R@0 G@8 B@16 (ABGR_8888) - the order the boot-animation player itself
 *      overrides to (it logs NUXEL_ANIM_FB_RED_OFF=16 then
 *      NUXEL_ANIM_HW_ORDER_NAME=abgr8888 R@0 G@8 B@16).  Copying XRGB8888
 *      words unchanged therefore swapped red and blue on the glass.  The
 *      conversion is now explicit, logged (source format + target order), and
 *      the hardware order still wins over fb_var's declared order (which the
 *      driver never programs - same evidence as nuxel-anim-player.c).
 *   6. BOOT ANIMATION LENGTH (mission 15).  The hand-off used to fire as soon
 *      as the launcher committed its page, i.e. 2-3 s into the boot animation:
 *      the animation's remaining part was replaced by the launcher's static
 *      wallpaper.  The bridge now waits until the player has completed at least
 *      NUXEL_ANIM_MIN_LOOPS (default 1) full cycles - read from the player's own
 *      NUXEL_ANIM_LOOP kmsg markers - before requesting the stop.
 *   7. SCREEN ON/OFF (mission 11).  A control FIFO /run/nuxel-wl-fb.cmd lets the
 *      Nuxel hardware-button manager turn the panel off and back on WITHOUT a
 *      second framebuffer owner: the bridge stays the single /dev/fb0 owner, it
 *      simply stops presenting and drives the sysfs backlight to the panel's
 *      own minimum.  State is published in /var/lib/nuxel/display.
 */
#define _GNU_SOURCE
#include <errno.h>
#include <fcntl.h>
#include <linux/fb.h>
#include <signal.h>
#include <stdarg.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/ioctl.h>
#include <sys/mman.h>
#include <sys/stat.h>
#include <sys/stat.h>
#include <sys/time.h>
#include <time.h>
#include <unistd.h>
#include <wayland-client.h>
#include "wlr-screencopy-unstable-v1-client-protocol.h"

#define STATE "/run/nuxel-wl-fb.state"
#define MAX_OUT 4
#define CTRL_FIFO  "/run/nuxel-wl-fb.cmd"
#define DISP_STATE "/var/lib/nuxel/display"
#define BACKLIGHT  "/sys/class/backlight/panel/brightness"
#define BL_MAX     "/sys/class/backlight/panel/max_brightness"

/* ---- A32 colour: the DECON order this panel actually uses -------------------
   Measured on the handset (A23, re-confirmed A32 from the live player log):
     fb_var  declares  R@16 G@8 B@0  (XRGB8888)
     DECON   maps      R@0  G@8 B@16 (ABGR_8888)  <- the glass follows THIS one
   The player overrides fb_var for exactly this reason; this bridge must do the
   same, because it copies a foreign buffer (the compositor's XRGB8888 shm
   surface) into the same scanout memory. */
static unsigned hw_r_off = 0, hw_g_off = 8, hw_b_off = 16;
static int hw_order_override = 1;      /* --fbvar-order restores the old code path */
static uint32_t *cv_lo, *cv_hi;        /* 2 x 64K LUT for the R<->B swap fast path */
static uint32_t src_fmt;               /* WL_SHM_FORMAT_* actually offered */
static int color_warned;

static void color_build(uint32_t format) {
  src_fmt = format;
  free(cv_lo); free(cv_hi); cv_lo = cv_hi = NULL;
  if (format != WL_SHM_FORMAT_XRGB8888 && format != WL_SHM_FORMAT_ARGB8888) return;
  if (hw_r_off != 0 || hw_g_off != 8 || hw_b_off != 16) return;   /* generic path */
  cv_lo = malloc(sizeof(uint32_t) * 65536);
  cv_hi = malloc(sizeof(uint32_t) * 65536);
  if (!cv_lo || !cv_hi) { free(cv_lo); free(cv_hi); cv_lo = cv_hi = NULL; return; }
  /* Source XRGB8888 word 0x00RRGGBB -> destination ABGR_8888 word 0xAABBGGRR.
     low half  x = 0xGGBB -> G stays at bits 8..15, B moves to bits 16..23,
                alpha is set to 0xff (the DECON does not blend, so every pixel the
                launcher draws is opaque - a transparent shm pixel must never
                expose the previous frame);
     high half x = 0x00RR   -> R moves down to bits 0..7.                      */
  for (uint32_t x = 0; x < 65536; x++) {
    cv_lo[x] = ((x & 0xffu) << 16) | (x & 0xff00u) | 0xff000000u;
    cv_hi[x] = (x & 0xffu);
  }
}

static inline uint32_t color_convert(uint32_t v) {
  if (cv_lo && cv_hi) return cv_lo[v & 0xffffu] | cv_hi[v >> 16];
  /* generic (also used when the declared order is trusted) */
  uint32_t r = (v >> 16) & 0xffu, g = (v >> 8) & 0xffu, b = v & 0xffu;
  return (r << hw_r_off) | (g << hw_g_off) | (b << hw_b_off) | 0xff000000u;
}


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
  /* A32 colour truth, logged the same way the animation player logs it. */
  const char *fbo = getenv("NUXEL_WLFB_FBVAR_ORDER");
  if (fbo && fbo[0] == '1') hw_order_override = 0;
  if (hw_order_override) {
    hw_r_off = 0; hw_g_off = 8; hw_b_off = 16;
    st("COLOR_ORDER declared=R@%u G@%u B@%u A@%u  applied=R@%u G@%u B@%u A@24 name=%s override=1(decon_abgr8888)",
       fb.var.red.offset, fb.var.green.offset, fb.var.blue.offset, fb.var.transp.offset,
       hw_r_off, hw_g_off, hw_b_off, "abgr8888");
  } else {
    hw_r_off = fb.var.red.offset; hw_g_off = fb.var.green.offset; hw_b_off = fb.var.blue.offset;
    st("COLOR_ORDER declared=R@%u G@%u B@%u A@%u  applied=same name=fbvar override=0",
       fb.var.red.offset, fb.var.green.offset, fb.var.blue.offset, fb.var.transp.offset);
  }
  return 0;
}

/* copy one composited frame into the panel, nearest-neighbour by integer scale
   when the compositor output is smaller than the panel (720x1520 -> 1440x3040) */
static uint16_t *xmap;      /* dest x -> source x (A31: one integer divide per
                               frame instead of one per destination pixel) */
static int xmap_w, xmap_sx;

static void blit(const uint8_t *src, int sw, int sh, int stride, uint32_t format) {
  if (fb.bpp != 32 || !fb.map) return;
  if (format != src_fmt) color_build(format);
  int sx = (int)fb.w / sw, sy = (int)fb.h / sh;
  if (sx < 1) sx = 1;
  if (sy < 1) sy = 1;
  if (!xmap || xmap_w != (int)fb.w || xmap_sx != sx) {
    free(xmap);
    xmap = malloc(sizeof(uint16_t) * (fb.w ? fb.w : 1));
    if (!xmap) return;
    for (uint32_t x = 0; x < fb.w; x++) {
      int tx = (int)(x / (uint32_t)sx); if (tx >= sw) tx = sw - 1;
      xmap[x] = (uint16_t)tx;
    }
    xmap_w = (int)fb.w; xmap_sx = sx;
  }
  /* XRGB/ARGB 8888 arrive as 0xXXRRGGBB and must be re-ordered; XBGR/ABGR 8888 are
     already 0xAABBGGRR, which is this panel's order, so they only need the alpha
     forced opaque.  Anything else is logged and passed through rather than
     silently mis-converted. */
  int convert = (format == WL_SHM_FORMAT_XRGB8888 || format == WL_SHM_FORMAT_ARGB8888);
  int known   = convert || format == WL_SHM_FORMAT_XBGR8888 || format == WL_SHM_FORMAT_ABGR8888;
  if (!known && !color_warned) {
    color_warned = 1;
    st("COLOR_UNKNOWN_SRC_FORMAT=0x%08x passthrough", format);
  }
  for (uint32_t y = 0; y < fb.h; y++) {
    int ty = (int)(y / (uint32_t)sy); if (ty >= sh) ty = sh - 1;
    const uint32_t *s = (const uint32_t *)(src + (size_t)ty * stride);
    uint32_t *d = (uint32_t *)(fb.map + (size_t)y * fb.line);
    if (convert) {
      for (uint32_t x = 0; x < fb.w; x++) d[x] = color_convert(s[xmap[x]]);
    } else {
      for (uint32_t x = 0; x < fb.w; x++) d[x] = s[xmap[x]] | 0xff000000u;
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

/* ============================================================================
 * A30 — SINGLE-FRAMEBUFFER-OWNER HANDOFF
 *
 * MEASURED DEFECT (live handset, 2026-10-16):
 *   Two processes were writing the SAME /dev/fb0 scanout memory at the same
 *   time for the whole session:
 *     pid 3523 /opt/nuxel/nuxel-anim-player   <- initramfs MP4 player, looping
 *                                                 forever (5280 frames, 27 loops)
 *     pid 5436 /usr/lib/nuxel/nuxel-wl-fb     <- this bridge (5645 frames)
 *   Nothing in the A29 launcher path ever created /var/lib/nuxel/anim-stop; the
 *   ONLY writer of that file was nuxel-ui.c, i.e. the A27 framebuffer fallback
 *   that the port replaced.  Result on the glass: the animation and the launcher
 *   alternated frame by frame (the "old TL light" flicker) and the launcher was
 *   never cleanly visible.
 *
 * THE FIX (mission 10.2/10.3): this bridge now performs an explicit, verified
 * ownership handoff before it touches the panel:
 *
 *   LAUNCHER_STARTING -> LAUNCHER_READY (page committed, /run/nuxel-launcher-ready)
 *     -> ANIMATION_STOP_REQUESTED  (write /var/lib/nuxel/anim-stop + fb-hold-stop)
 *     -> ANIMATION_STOP_CONFIRMED  (/proc/<pid> identity-checked, process gone)
 *     -> LAUNCHER_DISPLAY_OWNER    (DECON re-asserted, full frame blitted)
 *
 *   * It never blits before the handoff, so during the animation it is not a
 *     second writer at all.
 *   * The stop is requested by FILE, never by a stale pid file kill: the pid from
 *     fb-anim.pid is only ever signalled/awaited after /proc/<pid>/comm proves it
 *     is still the animation player (mission 10.2: verify process identity).
 *   * A process that closes /dev/fb0 runs decon_release and powers the AMOLED
 *     down (measured A21/A24) - so immediately after the player has gone, the
 *     DECON is re-asserted with FBIOPUT_VSCREENINFO and the full frame is
 *     written, which also replaces every stale animation pixel.
 *   * If the launcher never becomes ready the bridge exits WITHOUT ever touching
 *     the panel, leaving the animation/fallback as the sole owner.
 * ==========================================================================*/
#define LAUNCHER_READY "/run/nuxel-launcher-ready"
#define HOME_STATE     "/run/nuxel-home.state"
#define ANIM_STOP      "/var/lib/nuxel/anim-stop"
#define ANIM_PID       "/var/lib/nuxel/fb-anim.pid"
#define ANIM_STATE     "/var/lib/nuxel/animation"
#define HOLD_STOP      "/var/lib/nuxel/fb-hold-stop"
#define HOLD_PID       "/var/lib/nuxel/fb-hold.pid"
#define STAGE_OWNER    "/var/lib/nuxel/fb-owner"
#define ANIM_STOP_CONFIRMED_FILE "/run/nuxel-anim-stop.confirmed"

static void wr_state(const char *path, const char *data) {
  int fd = open(path, O_WRONLY | O_CREAT | O_TRUNC, 0644);
  if (fd < 0) return;
  if (write(fd, data, strlen(data)) < 0) { /* best effort */ }
  close(fd);
}

static int file_has(const char *path, const char *needle, char *out, size_t outn) {
  char buf[1024];
  int fd = open(path, O_RDONLY);
  if (fd < 0) return 0;
  ssize_t n = read(fd, buf, sizeof buf - 1);
  close(fd);
  if (n <= 0) return 0;
  buf[n] = 0;
  if (out && outn) { size_t k = (size_t)n < outn - 1 ? (size_t)n : outn - 1; memcpy(out, buf, k); out[k] = 0; }
  return needle ? (strstr(buf, needle) != NULL) : 1;
}

static long read_pid_file(const char *path) {
  char b[32];
  if (!file_has(path, NULL, b, sizeof b)) return -1;
  long v = strtol(b, NULL, 10);
  return v > 1 ? v : -1;
}

/* Identity before trust (mission 10.3): a pid is only ever treated as "the
   animation painter" when BOTH /proc/<pid>/comm and /proc/<pid>/exe still name
   it, so a recycled pid (or a stale pid file) can never be signalled. */
static int proc_exe_contains(long pid, const char *needle) {
  char p[64], buf[256];
  snprintf(p, sizeof p, "/proc/%ld/exe", pid);
  ssize_t n = readlink(p, buf, sizeof buf - 1);
  if (n <= 0) return 0;
  buf[n] = 0;
  return strstr(buf, needle) != NULL;
}

static int proc_comm_starts(long pid, const char *prefix) {
  char p[64], buf[64];
  snprintf(p, sizeof p, "/proc/%ld/comm", pid);
  if (!file_has(p, NULL, buf, sizeof buf)) return 0;
  for (int i = 0; buf[i]; i++) if (buf[i] == '\n') { buf[i] = 0; break; }
  return strncmp(buf, prefix, strlen(prefix)) == 0;
}

/* Still painting the panel?  nuxel-anim-player = the initramfs MP4 player,
   nuxel-fb-phone = the initramfs first-light/hold painter. */
static int painter_alive(void) {
  long p = read_pid_file(ANIM_PID);
  if (p > 0 && proc_comm_starts(p, "nuxel-anim") && proc_exe_contains(p, "nuxel-anim-player"))
    return (int)p;
  p = read_pid_file(HOLD_PID);
  if (p > 0 && proc_comm_starts(p, "nuxel-fb-phone") && proc_exe_contains(p, "nuxel-fb-phone"))
    return (int)p;
  return 0;
}

static void panel_assert(const char *why);

/* ---- A32: how far has the boot animation got? -------------------------------
   The initramfs player prints NUXEL_ANIM_LOOP=<n> at every loop start and
   NUXEL_ANIM_HEARTBEAT_LOOPS=<n> while painting (measured on the handset:
   "NUXEL_ANIM_LOOP=3", "NUXEL_ANIM_HEARTBEAT_LOOPS=3").  Reading /dev/kmsg keeps
   its own position per fd and does not consume records for other readers, so the
   bridge can read the ring from its start and learn the real progress of the
   animation instead of guessing from a timer. */
static int kmsg_max_loops(void) {
  int fd = open("/dev/kmsg", O_RDONLY | O_NONBLOCK | O_CLOEXEC);
  if (fd < 0) return -1;
  char buf[65536];
  int maxl = -1;
  for (int i = 0; i < 8192; i++) {
    ssize_t n = read(fd, buf, sizeof buf - 1);
    if (n <= 0) break;
    buf[n] = 0;
    for (char *q = buf; q && *q; ) {
      char *nl = strchr(q, '\n');
      if (nl) *nl = 0;
      const char *keys[2] = { "NUXEL_ANIM_LOOP=", "NUXEL_ANIM_HEARTBEAT_LOOPS=" };
      for (int k = 0; k < 2; k++) {
        char *m = strstr(q, keys[k]);
        if (m) {
          int v = atoi(m + strlen(keys[k]));
          if (v > maxl) maxl = v;
        }
      }
      q = nl ? nl + 1 : NULL;
    }
  }
  close(fd);
  return maxl;
}

/* ---- A32: panel on/off without a second framebuffer owner ------------------
   Mission 11: a short POWER press must blank the panel and a second press must
   bring it back, with Fedora, the console and the launcher state preserved.
   This process stays the one and only /dev/fb0 owner: screen-off stops frame
   presentation and drives the panel's sysfs backlight to 0 (the DECON/DSIM path
   keeps its configuration, so no decon_release is triggered and no re-init is
   needed on wake). */
static int ctrl_fd = -1;
static int display_on = 1;
static int saved_brightness = -1;
static int max_brightness = -1;

static int read_int_file(const char *path) {
  char b[32];
  if (!file_has(path, NULL, b, sizeof b)) return -1;
  return atoi(b);
}

static void backlight_write(int v) {
  int fd = open(BACKLIGHT, O_WRONLY);
  if (fd < 0) { st("BACKLIGHT_WRITE_FAIL path=%s", BACKLIGHT); return; }
  char b[16];
  int n = snprintf(b, sizeof b, "%d\n", v);
  if (write(fd, b, (size_t)n) < 0) { /* best effort */ }
  close(fd);
}

static void display_publish(void) {
  char b[192];
  snprintf(b, sizeof b,
           "DISPLAY_%s\nbrightness=%d\nsaved_brightness=%d\nmax_brightness=%d\nowner=nuxel-wl-fb\n",
           display_on ? "ON" : "OFF", read_int_file(BACKLIGHT), saved_brightness, max_brightness);
  wr_state(DISP_STATE, b);
}

static void display_set(int on, const char *why) {
  if (on && !display_on) {
    int b = saved_brightness;
    if (b < 0) b = max_brightness > 0 ? max_brightness / 2 : 255;
    backlight_write(b);
    panel_assert("screen-on");
    display_on = 1;
    st("DISPLAY_ON why=%s brightness=%d", why, b);
  } else if (!on && display_on) {
    int cur = read_int_file(BACKLIGHT);
    if (cur > 0) saved_brightness = cur;
    backlight_write(0);
    display_on = 0;
    st("DISPLAY_OFF why=%s saved_brightness=%d", why, saved_brightness);
  }
  display_publish();
}

static void ctrl_pump(void) {
  char buf[1024];
  if (ctrl_fd < 0) return;
  for (int i = 0; i < 32; i++) {
    ssize_t n = read(ctrl_fd, buf, sizeof buf - 1);
    if (n <= 0) break;
    buf[n] = 0;
    for (char *q = buf; q && *q; ) {
      char *nl = strchr(q, '\n');
      if (nl) *nl = 0;
      if (!strncmp(q, "screen-off", 10))       display_set(0, "control-fifo");
      else if (!strncmp(q, "screen-on", 9))    display_set(1, "control-fifo");
      else if (!strncmp(q, "screen-toggle", 13)) display_set(!display_on, "control-fifo");
      else if (!strncmp(q, "status", 6))       display_publish();
      q = nl ? nl + 1 : NULL;
    }
  }
}

static void ctrl_open(void) {
  unlink(CTRL_FIFO);
  if (mkfifo(CTRL_FIFO, 0600) < 0 && errno != EEXIST) { st("CTRL_FIFO_FAIL errno=%d", errno); return; }
  ctrl_fd = open(CTRL_FIFO, O_RDWR | O_NONBLOCK | O_CLOEXEC);
  if (ctrl_fd < 0) { st("CTRL_FIFO_OPEN_FAIL errno=%d", errno); return; }
  st("CTRL_FIFO_READY %s", CTRL_FIFO);
}

static void panel_assert(const char *why) {
  long r1 = ioctl(fb.fd, FBIOBLANK, FB_BLANK_UNBLANK);
  fb.var.activate = FB_ACTIVATE_NOW;
  fb.var.xoffset = 0; fb.var.yoffset = 0;
  long r2 = ioctl(fb.fd, FBIOPUT_VSCREENINFO, &fb.var);
  long r3 = ioctl(fb.fd, FBIOPAN_DISPLAY, &fb.var);
  st("DECON_ASSERT why=%s unblank=%ld vinfo=%ld pan=%ld", why, r1, r2, r3);
}

/* Wait (bounded) for the launcher's own readiness marker.  /run/nuxel-launcher-ready
   is written by nuxel-pwa-host only after WebKit COMMITTED the real page, so this
   is a graphical-readiness test, not a "the process exists" test (mission 10.3). */
static int wait_launcher_ready(int secs) {
  const char *env = getenv("NUXEL_HANDOFF_WAIT");
  if (env) { int v = atoi(env); if (v > 0) secs = v; }
  for (int i = 0; i <= secs * 4; i++) {
    if (file_has(LAUNCHER_READY, NULL, NULL, 0)) return 1;
    if (file_has(HOME_STATE, "NUXEL_HOME_READY", NULL, 0)) return 1;
    if ((i % 20) == 0) st("HANDOFF_WAIT_LAUNCHER t=%ds", i / 4);
    usleep(250000);
  }
  return 0;
}

static void frame_blit_once(void) {
  blit(frame_buf.data, frame_buf.w, frame_buf.h, frame_buf.stride, frame_buf.format);
}

/* Offline, deterministic colour test (mission 17).  Runs on any host, touches no
   framebuffer: it builds the same lookup tables blit() uses and checks the four
   primaries numerically, so the conversion is verified instead of eyeballed. */
static int colour_selftest(void) {
  struct { uint32_t src; uint32_t want; const char *name; } t[] = {
    { 0x00ff0000u, 0xff0000ffu, "red"   },
    { 0x0000ff00u, 0xff00ff00u, "green" },
    { 0x000000ffu, 0xffff0000u, "blue"  },
    { 0x00ffffffu, 0xffffffffu, "white" },
    { 0x00000000u, 0xff000000u, "black" },
  };
  int fail = 0;
  color_build(WL_SHM_FORMAT_XRGB8888);
  if (!cv_lo || !cv_hi) { printf("FAIL colour LUT not built\n"); return 1; }
  for (unsigned i = 0; i < sizeof t / sizeof t[0]; i++) {
    uint32_t got = color_convert(t[i].src);
    int ok = (got == t[i].want);
    printf("%s %-5s src=0x%08x got=0x%08x want=0x%08x\n",
           ok ? "PASS" : "FAIL", t[i].name, t[i].src, got, t[i].want);
    if (!ok) fail++;
  }
  for (unsigned i = 0; i < 4; i++) {
    uint32_t src = (0xffu << (8 * i)) ^ 0x00000000u;
    uint32_t got = color_convert(src);
    if (((got >> 24) & 0xffu) != 0xffu) { printf("FAIL alpha not opaque: 0x%08x\n", got); fail++; }
  }
  printf("%s alpha forced opaque on every channel pattern\n", fail ? "FAIL" : "PASS");
  return fail ? 1 : 0;
}

int main(int argc, char **argv) {
  if (argc > 1 && !strcmp(argv[1], "--colour-selftest")) return colour_selftest();
  const char *outname = argc > 1 ? argv[1] : getenv("NUXEL_WL_OUTPUT");
  (void)outname;
  struct wl_display *dpy = wl_display_connect(NULL);
  if (!dpy) { st("WL_CONNECT_FAIL errno=%d display=%s", errno, getenv("WAYLAND_DISPLAY") ?: "(unset)"); return 1; }
  struct wl_registry *reg = wl_display_get_registry(dpy);
  wl_registry_add_listener(reg, &reg_listener, NULL);
  for (int i = 0; i < 3; i++) wl_display_roundtrip(dpy);
  if (!compositor || !shm || !scm) { st("WL_MISSING_GLOBAL"); return 2; }
  if (nouts == 0) { st("WL_NO_OUTPUT"); return 3; }
  struct out *o = &outs[0];
  if (fb_open() < 0) return 4;

  /* --- 1. the launcher must be graphically ready before we claim the panel --- */
  st("LAUNCHER_STARTING panel=%ux%u waiting for %s", fb.w, fb.h, LAUNCHER_READY);
  if (!wait_launcher_ready(120)) {
    /* No launcher: the initramfs animation (or nuxel-fallback) keeps the panel.
       Never become a second writer.  Exit 0 => systemd does not restart us and
       the fallback's ExecCondition can take over. */
    st("HANDOFF_NO_LAUNCHER panel untouched, animation stays sole owner");
    close(fb.fd);
    return 0;
  }
  st("LAUNCHER_READY page_committed");
  wr_state(STAGE_OWNER, "BOOT_WAIT_LAUNCHER\nLAUNCHER_READY\n");

  /* --- 2. take ONE composited frame and hold it ---------------------------- */
  int frames = 0, failures = 0;
  time_t t0 = time(NULL), last = t0;
  int got = 0;
  for (int tries = 0; tries < 2000 && !got; tries++) {
    if (o->w <= 0) { wl_display_roundtrip(dpy); if (wl_display_dispatch(dpy) < 0) { st("WL_DISPATCH_FAIL"); return 5; } usleep(20000); continue; }
    struct zwlr_screencopy_frame_v1 *frame = zwlr_screencopy_manager_v1_capture_output(scm, 0, o->wl);
    frame_ready = frame_failed = have_pending = 0;
    zwlr_screencopy_frame_v1_add_listener(frame, &frame_listener, NULL);
    while (!frame_ready && !frame_failed) {
      if (wl_display_dispatch(dpy) < 0) { st("WL_DISPATCH_FAIL errno=%d", errno); return 5; }
      if (have_pending && !frame_ready && !frame_failed) {
        zwlr_screencopy_frame_v1_copy(frame, pending_buf);
        have_pending = 0;
      }
    }
    if (frame_failed) failures++;
    else got = 1;
    zwlr_screencopy_frame_v1_destroy(frame);
    if (got) break;
    if (frame_buf.wl) { wl_buffer_destroy(frame_buf.wl); munmap(frame_buf.data, frame_buf.len); frame_buf.wl = NULL; }
    usleep(50000);
  }
  if (!got) { st("HANDOFF_NO_FRAME failures=%d panel untouched", failures); close(fb.fd); return 6; }

  /* --- 3. ANIMATION_STOP_REQUESTED (NO scanout write yet) ---------------- */
  /* A31 fix 1: while the animation player may still be painting, this process
     must not write scanout memory at all - not even "staging" a frame.  Only
     files are written here.  The panel is claimed in step 4, after proof. */
  /* --- 2b. A32: let the ORIGINAL boot animation finish what it is showing ----
     The launcher's page commits ~2-3 s after the player's first frame, and until
     A31 the hand-off happened right then: the animation's remaining part was
     replaced by the launcher's static wallpaper (mission 15 / the operator's
     report).  Wait for NUXEL_ANIM_MIN_LOOPS complete animation cycles first. */
  long pid = painter_alive();
  {
    const char *env = getenv("NUXEL_ANIM_MIN_LOOPS");
    int min_loops = env ? atoi(env) : 1;
    if (min_loops > 0 && pid > 0) {
      int wait_s = 24;
      const char *wenv = getenv("NUXEL_ANIM_MIN_WAIT");
      if (wenv) { int v = atoi(wenv); if (v > 0) wait_s = v; }
      int seen = kmsg_max_loops();
      for (int i = 0; i <= wait_s * 10; i++) {
        seen = kmsg_max_loops();
        if (seen >= min_loops) break;
        if (!painter_alive()) break;                 /* player gone on its own */
        if ((i % 10) == 0) st("ANIM_MIN_CYCLE_WAIT loops=%d target=%d t=%ds", seen, min_loops, i / 10);
        usleep(100000);
      }
      st("ANIM_MIN_CYCLE_RESULT loops=%d target=%d painter=%d", seen, min_loops, painter_alive());
      wr_state("/var/lib/nuxel/anim-min-cycle.completed",
               seen >= min_loops ? "ANIM_MIN_CYCLE_COMPLETED\n" : "ANIM_MIN_CYCLE_NOT_SEEN\n");
    }
  }
  wr_state(HOLD_STOP, "ANIMATION_STOP_REQUESTED\n");
  wr_state(STAGE_OWNER, "BOOT_WAIT_LAUNCHER\nLAUNCHER_READY\nANIMATION_STOP_REQUESTED\n");
  st("ANIMATION_STOP_REQUESTED painter_pid=%ld", pid);

  /* --- 3b. ANIMATION_STOP_CONFIRMED - proof of termination, not intent ---- */
  int confirmed = 0;
  if (pid <= 0) {
    confirmed = 1;                                  /* no painter was running */
  } else {
    for (int i = 0; i < 500; i++) {                 /* <= 10 s */
      if (!painter_alive()) { confirmed = 1; break; }
      usleep(20000);
    }
  }
  /* A30 continued ("recovering anyway") when the stop was not confirmed, which
     races a live painter.  A31 does a bounded, identity-verified stop instead:
     SIGTERM, then SIGKILL - the pid comes from painter_alive(), which has already
     proved /proc/<pid>/comm AND /proc/<pid>/exe are the animation player. */
  if (!confirmed) {
    st("HANDOFF_STOP_TIMEOUT pid=%ld -> SIGTERM (identity verified)", pid);
    kill((pid_t)pid, SIGTERM);
    for (int i = 0; i < 150 && painter_alive(); i++) usleep(20000);   /* <= 3 s */
    if (painter_alive()) {
      st("HANDOFF_STOP_SIGKILL pid=%ld", pid);
      kill((pid_t)pid, SIGKILL);
      for (int i = 0; i < 150 && painter_alive(); i++) usleep(20000);
    }
    if (!painter_alive()) { confirmed = 1; st("HANDOFF_STOP_FORCED pid=%ld gone", pid); }
  }
  if (!confirmed) {
    /* Refuse to race the still-running animation: the panel is left untouched so
       the painter (or nuxel-fallback) keeps sole ownership and the USB console
       stays usable.  A diagnostic is recorded and the unit fails visibly. */
    st("HANDOFF_REFUSED pid=%ld still painting; panel UNTOUCHED (no second writer)", pid);
    wr_state(STAGE_OWNER, "BOOT_WAIT_LAUNCHER\nLAUNCHER_READY\nANIMATION_STOP_REQUESTED\nANIMATION_STOP_UNCONFIRMED\n");
    close(fb.fd);
    return 7;
  }
  st("ANIMATION_STOP_CONFIRMED pid=%ld", pid);
  wr_state(ANIM_STOP_CONFIRMED_FILE, "ANIMATION_STOP_CONFIRMED\n");
  wr_state(STAGE_OWNER, "BOOT_WAIT_LAUNCHER\nLAUNCHER_READY\nANIMATION_STOP_REQUESTED\nANIMATION_STOP_CONFIRMED\n");

  /* --- 4. LAUNCHER_DISPLAY_OWNER - the FIRST scanout write ---------------- */
  /* The player's close(/dev/fb0) ran decon_release and powered the AMOLED down
     (measured A21/A24), so the DECON is re-asserted and the full frame is
     written, replacing every stale animation pixel.  This is now the first time
     this process touches scanout memory. */
  panel_assert("post-stop");
  frame_blit_once();
  wr_state(ANIM_STATE, "ANIM_STAGE=ANIMATION_STOPPED\nANIM_OWNER=nuxel-wl-fb\n");
  wr_state(STAGE_OWNER, "BOOT_WAIT_LAUNCHER\nLAUNCHER_READY\nANIMATION_STOP_REQUESTED\nANIMATION_STOP_CONFIRMED\nLAUNCHER_DISPLAY_OWNER\n");
  ctrl_open();
  max_brightness = read_int_file(BL_MAX);
  saved_brightness = read_int_file(BACKLIGHT);
  display_on = 1;
  display_publish();
  st("BACKLIGHT_READY node=%s current=%d max=%d", BACKLIGHT, saved_brightness, max_brightness);
  st("LAUNCHER_DISPLAY_OWNER stopped=%d out=%dx%d src=%dx%d scale=%d panel=%ux%u",
     confirmed, o->w, o->h, frame_buf.w, frame_buf.h, o->scale, fb.w, fb.h);

  /* --- 5. normal ownership loop - paced, no periodic display reset (A31) --- */
  frames = 1;
  int fps = 0;
  int fps_target = 30;
  const char *fpsenv = getenv("NUXEL_TARGET_FPS");
  if (fpsenv) { int v = atoi(fpsenv); if (v >= 1 && v <= 120) fps_target = v; }
  long frame_ns = 1000000000L / fps_target;
  int consec_fail = 0;
  unsigned long long blit_ns_sum = 0;
  time_t now = time(NULL);
  last = now;
  st("OWNERSHIP_LOOP fps_target=%d single_owner=1", fps_target);
  for (;;) {
    struct timespec t_start;
    clock_gettime(CLOCK_MONOTONIC, &t_start);
    ctrl_pump();                      /* A32: screen on/off + status requests */
    struct zwlr_screencopy_frame_v1 *frame = zwlr_screencopy_manager_v1_capture_output(scm, 0, o->wl);
    frame_ready = frame_failed = have_pending = 0;
    zwlr_screencopy_frame_v1_add_listener(frame, &frame_listener, NULL);
    while (!frame_ready && !frame_failed) {
      if (wl_display_dispatch(dpy) < 0) { st("WL_DISPATCH_FAIL errno=%d", errno); return 5; }
      if (have_pending && !frame_ready && !frame_failed) {
        zwlr_screencopy_frame_v1_copy(frame, pending_buf);
        have_pending = 0;
      }
    }
    if (frame_failed) { failures++; consec_fail++; }
    else if (!display_on) {
      /* panel is off: keep consuming compositor frames so the client stays live,
         but present nothing (mission 11: stop visible frame presentation) */
      frames++; consec_fail = 0;
    }
    else {
      frame_blit_once(); frames++; consec_fail = 0;
      struct timespec t_end;
      clock_gettime(CLOCK_MONOTONIC, &t_end);
      blit_ns_sum += (unsigned long long)(t_end.tv_sec - t_start.tv_sec) * 1000000000ull
                   + (unsigned long long)(t_end.tv_nsec - t_start.tv_nsec);
    }
    zwlr_screencopy_frame_v1_destroy(frame);
    if (frame_buf.wl) { wl_buffer_destroy(frame_buf.wl); munmap(frame_buf.data, frame_buf.len); frame_buf.wl = NULL; }

    /* Panel re-assertion ONLY on measured failure evidence (A31 fix 3): a
       sustained run of failed captures.  The steady state performs no
       FBIOPUT_VSCREENINFO and no FBIOPAN_DISPLAY at all - the visible buffer is
       written directly (yoffset 0, no double buffering), so re-initialising the
       display every reporting interval bought nothing and disturbed the panel. */
    if (consec_fail >= 10) { panel_assert("capture-failures"); consec_fail = 0; }

    now = time(NULL);
    if (now != last) {
      int avg_ms = frames ? (int)(blit_ns_sum / (unsigned long long)frames / 1000000ull) : 0;
      st("FRAMES_OK total=%d fps_1s=%d failures=%d blit_avg_ms=%d out=%dx%d src=%dx%d scale=%d panel=%ux%u owner=nuxel-wl-fb display=%s src_format=0x%08x colour=R@%u,G@%u,B@%u_abgr8888_override=%d",
         frames, fps, failures, avg_ms, o->w, o->h, o->w, o->h, o->scale, fb.w, fb.h,
         display_on ? "on" : "off", src_fmt, hw_r_off, hw_g_off, hw_b_off, hw_order_override);
      fps = 0;
      last = now;
      int intruder = painter_alive();
      if (intruder) {   /* a painter came back behind us: re-arm the stop */
        wr_state(ANIM_STOP, "ANIMATION_STOP_REQUESTED\n");
        wr_state(HOLD_STOP, "ANIMATION_STOP_REQUESTED\n");
        st("ANIMATION_RESURRECTED pid=%d stop re-armed", intruder);
      }
    }
    fps++;

    /* pace presentation to the target rate (mission 10.5: bounded, paced output
       instead of a tight screencopy loop burning CPU for no visible gain) */
    struct timespec t_now;
    clock_gettime(CLOCK_MONOTONIC, &t_now);
    long used_ns = (t_now.tv_sec - t_start.tv_sec) * 1000000000L + (t_now.tv_nsec - t_start.tv_nsec);
    long rest_ns = frame_ns - used_ns;
    if (rest_ns > 0) {
      struct timespec ts;
      ts.tv_sec = rest_ns / 1000000000L;
      ts.tv_nsec = rest_ns % 1000000000L;
      nanosleep(&ts, NULL);
    }
  }
}
