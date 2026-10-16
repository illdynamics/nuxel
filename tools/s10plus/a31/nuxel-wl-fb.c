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
static uint16_t *xmap;      /* dest x -> source x (A31: one integer divide per
                               frame instead of one per destination pixel) */
static int xmap_w, xmap_sx;

static void blit(const uint8_t *src, int sw, int sh, int stride, uint32_t format) {
  if (fb.bpp != 32 || !fb.map) return;
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
  int opaque = (format == WL_SHM_FORMAT_XRGB8888 || format == WL_SHM_FORMAT_ARGB8888);
  for (uint32_t y = 0; y < fb.h; y++) {
    int ty = (int)(y / (uint32_t)sy); if (ty >= sh) ty = sh - 1;
    const uint32_t *s = (const uint32_t *)(src + (size_t)ty * stride);
    uint32_t *d = (uint32_t *)(fb.map + (size_t)y * fb.line);
    if (opaque) { for (uint32_t x = 0; x < fb.w; x++) d[x] = s[xmap[x]] | 0xff000000u; }
    else        { for (uint32_t x = 0; x < fb.w; x++) d[x] = s[xmap[x]]; }
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

int main(int argc, char **argv) {
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
  long pid = painter_alive();
  wr_state(ANIM_STOP, "ANIMATION_STOP_REQUESTED\n");
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
      st("FRAMES_OK total=%d fps_1s=%d failures=%d blit_avg_ms=%d out=%dx%d src=%dx%d scale=%d panel=%ux%u owner=nuxel-wl-fb",
         frames, fps, failures, avg_ms, o->w, o->h, o->w, o->h, o->scale, fb.w, fb.h);
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
