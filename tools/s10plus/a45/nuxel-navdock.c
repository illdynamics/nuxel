/* nuxel-navdock — the persistent Back / Penguin Home / Recents system-navigation
 * dock as a NATIVE layer-shell surface (zwlr_layer_shell_v1, OVERLAY layer, bottom
 * anchored, exclusive zone).  It renders the same three owner-supplied button
 * PNGs the DOM dock used (pre-baked to ARGB8888 in navdock-art.h) and forwards a
 * tap to the launcher host exactly like the hardware-button manager does:
 *
 *     /run/nuxel-pwa-host.cmd  <-  "action back|home|recents\n"
 *
 * WHY A NATIVE DOCK EXISTS (A45):
 *   The working on-screen keyboard is the native Phosh OSK provider, Stevia
 *   (/usr/bin/phosh-osk-stevia), which binds zwp_input_method_manager_v2 and
 *   paints a compositor KEYBOARD-LAYER surface.  That layer covers every client
 *   surface, so a DOM navigation strip inside the WebKit launcher disappears
 *   under Stevia.  This dock lives at the OVERLAY layer with an exclusive zone:
 *   it stays above the keyboard and reserves the bottom strip, so the keyboard
 *   occupies the space immediately above the three buttons instead of covering
 *   them.
 *
 * SAFETY: a Wayland client only.  It never opens /dev/fb0, never writes a block
 * device, never touches the kernel/bootloader and never flashes anything.
 */
#define _GNU_SOURCE
#include <errno.h>
#include <fcntl.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdarg.h>
#include <sys/mman.h>
#include <sys/stat.h>
#include <poll.h>
#include <time.h>
#include <unistd.h>
#include <wayland-client.h>
#include "wlr-layer-shell-unstable-v1-client-protocol.h"
#include "navdock-art.h"

#define NAV_HEIGHT 62           /* logical px = 62 CSS px */
#define HOST_FIFO  "/run/nuxel-pwa-host.cmd"
#define HAP_FIFO   "/run/nuxel-haptics/haptics.cmd"
#define CMD_FIFO   "/run/nuxel-navdock.cmd"
#define REQ_FILE   "/run/nuxel-navdock.request"
#define STATE_JSON "/run/nuxel-navdock.json"
#define LOCK_STATE "/run/nuxel/security/lock-state.json"
#define LAUNCHER_READY "/run/nuxel-launcher-ready"

static struct wl_display *display;
static struct wl_registry *registry;
static struct wl_compositor *compositor;
static struct wl_shm *shm;
static struct zwlr_layer_shell_v1 *layer_shell;
static struct wl_output *output;
static struct wl_seat *seat;
static struct wl_touch *touch;

static struct wl_surface *surface;
static struct zwlr_layer_surface_v1 *layer_surface;
static struct wl_buffer *buffer;
static int cmd_fd = -1;
static int dock_visible = 0;   /* fail closed until lock state is ready */
static int touch_down = 0;
static int long_fired = 0;              /* one action per gesture */
static const struct zwlr_layer_surface_v1_listener layer_listener;
static int32_t scale = 2;
static int32_t out_w = 720, out_h = 1520;
static int32_t width = 720, height = NAV_HEIGHT;

static int lock_state_read(void);
static int home_ready(void);
static void audit(const char *fmt, ...) {
  char b[512];
  va_list ap;
  va_start(ap, fmt);
  vsnprintf(b, sizeof b, fmt, ap);
  va_end(ap);
  int fd = open("/run/nuxel-navdock.state", O_WRONLY | O_APPEND | O_CREAT, 0644);
  if (fd < 0) return;
  time_t t = time(NULL);
  dprintf(fd, "%lld %s\n", (long long)t, b);
  close(fd);
}

static void publish_state(const char *reason) {
  int st = lock_state_read();
  char tmp[128];
  snprintf(tmp, sizeof tmp, STATE_JSON ".%d", (int)getpid());
  FILE *f = fopen(tmp, "w");
  if (!f) return;
  fprintf(f,
    "{\"schema_version\":1,\"visible\":%s,\"mapped\":%s,"
    "\"lock\":\"%s\",\"home_ready\":%s,\"fifo_ready\":%s,"
    "\"width\":%d,\"height\":%d,\"scale\":%d,\"reason\":\"%s\"}\n",
    dock_visible ? "true" : "false", (dock_visible && surface) ? "true" : "false",
    st == 2 ? "unlocked" : st == 1 ? "locked" : "unknown",
    home_ready() ? "true" : "false", cmd_fd >= 0 ? "true" : "false",
    width, height, scale, reason ? reason : "");
  fclose(f);
  rename(tmp, STATE_JSON);
}

/* ---- authoritative lock state ------------------------------------------- */
/* Return 2 = unlocked, 1 = locked, 0 = unknown/unreadable.  The contract is
 * fail-closed: a missing/partially-written document or a missing lock-state
 * owner never lets the native dock map over the lockscreen. */
static int lock_state_read(void) {
  char buf[512];
  int fd = open(LOCK_STATE, O_RDONLY | O_CLOEXEC);
  if (fd < 0) return 0;
  ssize_t n = read(fd, buf, sizeof buf - 1);
  close(fd);
  if (n <= 0) return 0;
  buf[n] = 0;
  char *p = strstr(buf, "\"locked\"");
  if (!p) return 0;
  p = strchr(p, ':');
  if (!p) return 0;
  p++;
  while (*p == ' ' || *p == '\t') p++;
  if (!strncmp(p, "false", 5)) return 2;
  if (!strncmp(p, "true", 4)) return 1;
  return 0;
}

static void dock_show(void);
static void dock_hide(void);

static int home_ready(void) {
  return access(LAUNCHER_READY, F_OK) == 0;
}

static void dock_resolve_startup(void) {
  int st = lock_state_read();
  if (st == 2 && home_ready()) {
    dock_show();
    audit("NAV_DOCK_START visible=1 lock=unlocked home=ready");
  } else {
    dock_hide();
    audit("NAV_DOCK_START visible=0 lock=%s home=%s",
          st == 2 ? "unlocked" : st == 1 ? "locked" : "unknown",
          home_ready() ? "ready" : "not-ready");
  }
}

/* ---- shared-memory buffer (single wl_shm pool per frame) ---------------- */
static int create_shm(size_t size) {
  int fd = memfd_create("nuxel-navdock", MFD_CLOEXEC);
  if (fd < 0) { audit("SHM_MEMFD_FAIL errno=%d", errno); return -1; }
  if (ftruncate(fd, (off_t)size) < 0) { close(fd); return -1; }
  return fd;
}

/* Copy one button's ARGB8888 art into the buffer with nearest-neighbour
 * integer scaling so the pixel-art stays crisp at buffer_scale 2. */
static void blit(unsigned int *dst, int dst_stride, int dst_w, int dst_h,
                 const unsigned int *art, int art_w, int art_h,
                 int dst_x, int dst_y, int out_scale) {
  int dy, dx;
  for (dy = 0; dy < dst_h; dy++) {
    int ay = dy / out_scale;
    if (ay < 0 || ay >= art_h) continue;
    unsigned int *row = dst + (size_t)(dst_y + dy) * dst_stride;
    for (dx = 0; dx < dst_w; dx++) {
      int ax = dx / out_scale;
      if (ax < 0 || ax >= art_w) continue;
      unsigned int c = art[(size_t)ay * art_w + ax];
      if ((c >> 24) == 0) continue;   /* keep transparent pixels clear */
      row[dst_x + dx] = c;
    }
  }
  (void)dst_stride;
}

static void render_frame(void) {
  int bw = width * scale, bh = height * scale;
  size_t stride = (size_t)bw;
  size_t size = stride * bh * 4;
  if (bw <= 0 || bh <= 0) return;

  int fd = create_shm(size);
  if (fd < 0) return;
  unsigned int *px = mmap(NULL, size, PROT_READ | PROT_WRITE, MAP_SHARED, fd, 0);
  if (px == MAP_FAILED) { close(fd); audit("SHM_MMAP_FAIL errno=%d", errno); return; }
  memset(px, 0, size);   /* fully transparent background */

  int cell = bw / 3;
  int art_px = NAV_ART_SIZE * scale;   /* art square size in buffer px */

  blit(px, stride, art_px, art_px, art_left, NAV_ART_SIZE, NAV_ART_SIZE,
       cell * 0 + (cell - art_px) / 2, (bh - art_px) / 2, scale);
  blit(px, stride, art_px, art_px, art_middle, NAV_ART_SIZE, NAV_ART_SIZE,
       cell * 1 + (cell - art_px) / 2, (bh - art_px) / 2, scale);
  blit(px, stride, art_px, art_px, art_right, NAV_ART_SIZE, NAV_ART_SIZE,
       cell * 2 + (cell - art_px) / 2, (bh - art_px) / 2, scale);

  struct wl_shm_pool *pool = wl_shm_create_pool(shm, fd, size);
  struct wl_buffer *buf = wl_shm_pool_create_buffer(pool, 0, bw, bh, stride * 4,
                                                   WL_SHM_FORMAT_ARGB8888);
  wl_shm_pool_destroy(pool);
  munmap(px, size);
  close(fd);

  if (buffer) wl_buffer_destroy(buffer);
  buffer = buf;
  wl_surface_set_buffer_scale(surface, scale);
  wl_surface_attach(surface, buffer, 0, 0);
  wl_surface_damage(surface, 0, 0, bw, bh);
  wl_surface_commit(surface);
}

/* ---- native dock lifecycle ------------------------------------------------ */
static void dock_create(void) {
  if (!dock_visible || surface || !compositor || !shm || !layer_shell || !output) return;
  surface = wl_compositor_create_surface(compositor);
  if (!surface) { audit("DOCK_SURFACE_FAIL"); return; }
  layer_surface = zwlr_layer_shell_v1_get_layer_surface(
      layer_shell, surface, output, ZWLR_LAYER_SHELL_V1_LAYER_OVERLAY, "nuxel-navdock");
  zwlr_layer_surface_v1_set_anchor(layer_surface,
      ZWLR_LAYER_SURFACE_V1_ANCHOR_BOTTOM | ZWLR_LAYER_SURFACE_V1_ANCHOR_LEFT |
      ZWLR_LAYER_SURFACE_V1_ANCHOR_RIGHT);
  zwlr_layer_surface_v1_set_size(layer_surface, 0, NAV_HEIGHT);
  zwlr_layer_surface_v1_set_exclusive_zone(layer_surface, NAV_HEIGHT);
  zwlr_layer_surface_v1_set_keyboard_interactivity(layer_surface,
      ZWLR_LAYER_SURFACE_V1_KEYBOARD_INTERACTIVITY_NONE);
  zwlr_layer_surface_v1_add_listener(layer_surface, &layer_listener, NULL);
  wl_surface_commit(surface);
  publish_state("show");
}

static void dock_destroy(void) {
  touch_down = 0;
  if (buffer) { wl_buffer_destroy(buffer); buffer = NULL; }
  if (layer_surface) { zwlr_layer_surface_v1_destroy(layer_surface); layer_surface = NULL; }
  if (surface) { wl_surface_destroy(surface); surface = NULL; }
  publish_state("hide");
}

static void dock_show(void) {
  int st = lock_state_read();
  if (st != 2) {
    // Fail closed: an explicit show during lock/unknown is refused.
    dock_hide();
    audit("NAV_DOCK_SHOW_REFUSED lock=%s", st == 1 ? "locked" : "unknown");
    return;
  }
  if (dock_visible && surface) { publish_state("show-idempotent"); return; }
  dock_visible = 1;
  dock_create();
  audit("NAV_DOCK_SHOW lock=unlocked");
  publish_state("show");
}

static void dock_hide(void) {
  if (!dock_visible && !surface) return;
  dock_visible = 0;
  dock_destroy();
  audit("NAV_DOCK_HIDE");
  publish_state("hide");
}

static void process_command(const char *q);

static void cmd_pump(void) {
  char buf[512];
  if (cmd_fd < 0) return;
  for (int i = 0; i < 16; i++) {
    ssize_t n = read(cmd_fd, buf, sizeof buf - 1);
    if (n <= 0) break;
    buf[n] = 0;
    for (char *q = buf; q && *q; ) {
      char *nl = strchr(q, '\n');
      if (nl) *nl = 0;
      process_command(q);
      q = nl ? nl + 1 : NULL;
    }
  }
}

static void process_command(const char *q) {
  if (!q || !*q) return;
  if (!strcmp(q, "hide")) dock_hide();
  else if (!strcmp(q, "show")) dock_show();
  else if (!strcmp(q, "status")) {
    audit("NAV_DOCK_STATUS visible=%d surface=%d locked=%d",
          dock_visible, surface != NULL, lock_state_read());
    publish_state("status");
  }
}

/* A nav-show written before the FIFO existed must not be lost.  The host
 * atomically drops the desired command here when open("/run/nuxel-navdock.cmd")
 * fails; this is checked at startup and on every bounded tick. */
static void cmd_read_pending(void) {
  int fd = open(REQ_FILE, O_RDONLY | O_CLOEXEC);
  if (fd < 0) return;
  char buf[128];
  ssize_t n = read(fd, buf, sizeof buf - 1);
  close(fd);
  unlink(REQ_FILE);
  if (n <= 0) return;
  buf[n] = 0;
  char *nl = strchr(buf, '\n');
  if (nl) *nl = 0;
  audit("NAV_DOCK_PENDING_CMD %s", buf);
  process_command(buf);
}

/* Authoritative-state reconciliation.  Runs on a bounded 500 ms timer so a
 * lost/stale FIFO command can never leave the dock visible over the lockscreen
 * or hide it forever after unlock. */
static void dock_tick(void) {
  static int last_st = -2, last_home = -1;
  int st = lock_state_read();
  int home = home_ready();
  if (st != last_st || home != last_home) {
    publish_state("tick");
    last_st = st;
    last_home = home;
  }
  if (st != 2) {
    if (dock_visible || surface) {
      dock_hide();
      audit("NAV_DOCK_LOCK_HIDE lock=%s", st == 1 ? "locked" : "unknown");
    }
  } else if (!dock_visible && home_ready()) {
    dock_show();
    audit("NAV_DOCK_LOCK_RESTORE lock=unlocked home=ready");
  }
  cmd_read_pending();
}

static void cmd_open(void) {
  unlink(CMD_FIFO);
  if (mkfifo(CMD_FIFO, 0600) < 0 && errno != EEXIST) { audit("CMD_FIFO_FAIL errno=%d", errno); return; }
  cmd_fd = open(CMD_FIFO, O_RDWR | O_NONBLOCK | O_CLOEXEC);
  if (cmd_fd < 0) { audit("CMD_FIFO_OPEN_FAIL errno=%d", errno); return; }
  audit("CMD_FIFO_READY %s", CMD_FIFO);
}

/* ---- actions ------------------------------------------------------------- */
static void send_haptic(const char *name) {
  int hf = open(HAP_FIFO, O_WRONLY | O_NONBLOCK);
  if (hf < 0) return;
  dprintf(hf, "%s\n", name);
  close(hf);
}

/* Exactly one haptic per logical action.  A long Back gets the distinct
 * `long` pattern; the ordinary navigation tick is never also sent. */
static void forward(const char *action) {
  if (!dock_visible || !layer_surface) return;
  send_haptic(!strcmp(action, "back-long") ? "long" : "navigation");

  int fd = open(HOST_FIFO, O_WRONLY | O_NONBLOCK);
  if (fd < 0) { audit("HOST_FIFO_OPEN_FAIL errno=%d action=%s", errno, action); return; }
  dprintf(fd, "action %s\n", action);
  close(fd);
  audit("NAV_DOCK action=%s haptic=%s width=%d height=%d scale=%d", action,
        !strcmp(action, "back-long") ? "long" : "navigation", width, height, scale);
}

static int64_t now_ms(void) {
  struct timespec ts;
  clock_gettime(CLOCK_MONOTONIC, &ts);
  return (int64_t)ts.tv_sec * 1000 + ts.tv_nsec / 1000000;
}

static int cell_at(int32_t x) {
  if (width <= 0) return -1;
  int cell = x * 3 / width;
  if (cell < 0) cell = 0;
  if (cell > 2) cell = 2;
  return cell;
}

static void tap_at(int32_t x, int32_t y, int64_t held_ms) {
  if (width <= 0 || !dock_visible) return;
  (void)y; (void)held_ms;
  const char *actions[3] = { "back", "home", "recents" };
  forward(actions[cell_at(x)]);
}

/* ---- touch (single-finger) ---------------------------------------------- */
static int32_t down_x = 0, down_y = 0, last_x = 0, last_y = 0;
static int64_t down_ms = 0;

#define LONG_HOLD_MS 700
#define TAP_SLOP_PX  24

static void touch_down_cb(void *d, struct wl_touch *t, uint32_t serial,
                          uint32_t time, struct wl_surface *surf, int32_t id,
                          wl_fixed_t x, wl_fixed_t y) {
  (void)d; (void)t; (void)serial; (void)time; (void)surf; (void)id;
  if (!dock_visible) return;
  if (!touch_down) {
    touch_down = 1;
    long_fired = 0;
    down_ms = now_ms();
    down_x = last_x = wl_fixed_to_int(x);
    down_y = last_y = wl_fixed_to_int(y);
  }
}
static void touch_up_cb(void *d, struct wl_touch *t, uint32_t serial,
                        uint32_t time, int32_t id) {
  (void)d; (void)t; (void)serial; (void)time; (void)id;
  if (!touch_down) return;
  touch_down = 0;
  if (long_fired) { long_fired = 0; return; }   /* never double-fire */
  int dx = last_x - down_x, dy = last_y - down_y;
  /* A tap is a mostly-stationary contact: treat drags as non-actions. */
  if (dx < TAP_SLOP_PX && dx > -TAP_SLOP_PX &&
      dy < TAP_SLOP_PX && dy > -TAP_SLOP_PX)
    tap_at(down_x, down_y, now_ms() - down_ms);
}
static void touch_motion_cb(void *d, struct wl_touch *t, uint32_t time, int32_t id,
                            wl_fixed_t x, wl_fixed_t y) {
  (void)d; (void)t; (void)time; (void)id;
  last_x = wl_fixed_to_int(x);
  last_y = wl_fixed_to_int(y);
}
static void touch_frame_cb(void *d, struct wl_touch *t) { (void)d; (void)t; }
static void touch_cancel_cb(void *d, struct wl_touch *t) {
  (void)d; (void)t; touch_down = 0; long_fired = 0;
}
static const struct wl_touch_listener touch_listener = {
  .down = touch_down_cb, .up = touch_up_cb, .motion = touch_motion_cb,
  .frame = touch_frame_cb, .cancel = touch_cancel_cb,
};

/* Timer-driven threshold: the long pulse and the close request fire while the
 * finger is still down, not on release.  Movement beyond the tap slop or a
 * pointer cancel disarms it, so a scroll across the dock never closes an app. */
static void maybe_long_press(void) {
  if (!touch_down || long_fired || !dock_visible) return;
  if (cell_at(down_x) != 0) return;
  int dx = last_x - down_x, dy = last_y - down_y;
  if (dx >= TAP_SLOP_PX || dx <= -TAP_SLOP_PX ||
      dy >= TAP_SLOP_PX || dy <= -TAP_SLOP_PX) return;
  if (now_ms() - down_ms < LONG_HOLD_MS) return;
  long_fired = 1;
  forward("back-long");
}

static int long_press_timeout_ms(void) {
  if (!touch_down || long_fired || !dock_visible || cell_at(down_x) != 0) return -1;
  int dx = last_x - down_x, dy = last_y - down_y;
  if (dx >= TAP_SLOP_PX || dx <= -TAP_SLOP_PX ||
      dy >= TAP_SLOP_PX || dy <= -TAP_SLOP_PX) return -1;
  int64_t elapsed = now_ms() - down_ms;
  if (elapsed >= LONG_HOLD_MS) return 0;
  return (int)(LONG_HOLD_MS - elapsed);
}

/* ---- seat ----------------------------------------------------------------- */
static void seat_caps(void *d, struct wl_seat *s, uint32_t caps) {
  (void)d; (void)s;
  if ((caps & WL_SEAT_CAPABILITY_TOUCH) && !touch) {
    touch = wl_seat_get_touch(seat);
    wl_touch_add_listener(touch, &touch_listener, NULL);
  }
}
static void seat_name(void *d, struct wl_seat *s, const char *name) { (void)d; (void)s; (void)name; }
static const struct wl_seat_listener seat_listener = { .capabilities = seat_caps, .name = seat_name };

/* ---- layer surface -------------------------------------------------------- */
static void layer_configure(void *d, struct zwlr_layer_surface_v1 *ls,
                            uint32_t serial, uint32_t w, uint32_t h) {
  (void)d; (void)ls;
  if ((int32_t)w > 0) width = (int32_t)w;
  if ((int32_t)h > 0) height = (int32_t)h;
  zwlr_layer_surface_v1_ack_configure(layer_surface, serial);
  render_frame();
  publish_state("configured");
}
static void layer_closed(void *d, struct zwlr_layer_surface_v1 *ls) {
  (void)d; (void)ls; audit("LAYER_CLOSED");
}
static const struct zwlr_layer_surface_v1_listener layer_listener = {
  .configure = layer_configure, .closed = layer_closed,
};

/* ---- output ---------------------------------------------------------------- */
static void output_geometry(void *d, struct wl_output *o, int32_t x, int32_t y,
                            int32_t pw, int32_t ph, int32_t sub, const char *make,
                            const char *model, int32_t transform) {
  (void)d; (void)o; (void)x; (void)y; (void)pw; (void)ph; (void)sub;
  (void)make; (void)model; (void)transform;
}
static void output_mode(void *d, struct wl_output *o, uint32_t flags,
                        int32_t w, int32_t h, int32_t refresh) {
  (void)d; (void)o; (void)flags; (void)refresh;
  if (flags & WL_OUTPUT_MODE_CURRENT) { out_w = w; out_h = h; }
}
static void output_done(void *d, struct wl_output *o) { (void)d; (void)o; }
static void output_scale(void *d, struct wl_output *o, int32_t s) {
  (void)d; (void)o; if (s > 0) scale = s;
}
static const struct wl_output_listener output_listener = {
  .geometry = output_geometry, .mode = output_mode, .done = output_done,
  .scale = output_scale,
};

/* ---- registry -------------------------------------------------------------- */
static void reg_global(void *d, struct wl_registry *r, uint32_t name,
                       const char *iface, uint32_t ver) {
  (void)d;
  if (!strcmp(iface, wl_compositor_interface.name))
    compositor = wl_registry_bind(r, name, &wl_compositor_interface, 4);
  else if (!strcmp(iface, wl_shm_interface.name))
    shm = wl_registry_bind(r, name, &wl_shm_interface, 1);
  else if (!strcmp(iface, zwlr_layer_shell_v1_interface.name))
    layer_shell = wl_registry_bind(r, name, &zwlr_layer_shell_v1_interface, ver < 3 ? ver : 3);
  else if (!strcmp(iface, wl_output_interface.name) && !output)
    output = wl_registry_bind(r, name, &wl_output_interface, 3);
  else if (!strcmp(iface, wl_seat_interface.name) && !seat)
    seat = wl_registry_bind(r, name, &wl_seat_interface, 5);
}
static void reg_remove(void *d, struct wl_registry *r, uint32_t name) { (void)d; (void)r; (void)name; }
static const struct wl_registry_listener reg_listener = { reg_global, reg_remove };

int main(void) {
  unlink("/run/nuxel-navdock.state");
  display = wl_display_connect(NULL);
  if (!display) { audit("DISPLAY_CONNECT_FAIL"); return 1; }

  registry = wl_display_get_registry(display);
  wl_registry_add_listener(registry, &reg_listener, NULL);
  wl_display_roundtrip(display);

  if (!compositor || !shm || !layer_shell || !output) {
    audit("GLOBALS_MISSING compositor=%d shm=%d layer_shell=%d output=%d",
          compositor != NULL, shm != NULL, layer_shell != NULL, output != NULL);
    return 2;
  }
  wl_output_add_listener(output, &output_listener, NULL);
  if (seat) wl_seat_add_listener(seat, &seat_listener, NULL);
  wl_display_roundtrip(display);   /* collect output mode/scale */

  cmd_open();
  cmd_read_pending();
  dock_resolve_startup();
  wl_display_roundtrip(display);   /* receive configure -> render + map */

  audit("NAV_DOCK_READY width=%d height=%d scale=%d out=%dx%d",
        width, height, scale, out_w, out_h);
  publish_state("ready");

  for (;;) {
    while (wl_display_prepare_read(display) != 0) {
      if (wl_display_dispatch_pending(display) < 0) { audit("NAV_DOCK_EXIT dispatch"); return 0; }
    }
    wl_display_flush(display);
    struct pollfd pf[2] = {
      { .fd = wl_display_get_fd(display), .events = POLLIN, .revents = 0 },
      { .fd = cmd_fd, .events = POLLIN, .revents = 0 }
    };
    int nfds = cmd_fd >= 0 ? 2 : 1;
    int timeout = long_press_timeout_ms();
    if (timeout < 0 || timeout > 500) timeout = 500;
    int pr = poll(pf, (nfds_t)nfds, timeout);
    if (pr < 0) {
      wl_display_cancel_read(display);
      if (errno == EINTR) continue;
      audit("NAV_DOCK_EXIT poll errno=%d", errno);
      return 0;
    }
    if (pr == 0) {
      wl_display_cancel_read(display);
      maybe_long_press();
      dock_tick();
      continue;
    }
    if (pf[0].revents & POLLIN) {
      if (wl_display_read_events(display) < 0) { audit("NAV_DOCK_EXIT read"); return 0; }
      if (wl_display_dispatch_pending(display) < 0) { audit("NAV_DOCK_EXIT dispatch"); return 0; }
    } else {
      wl_display_cancel_read(display);
    }
    if (cmd_fd >= 0 && (pf[1].revents & (POLLIN | POLLHUP))) cmd_pump();
    maybe_long_press();
    dock_tick();
  }
  audit("NAV_DOCK_EXIT");
  return 0;
}
