/* nuxel-statusbar — persistent top bar for fullscreen native applications.
 *
 * The Home PWA draws its own DOM status bar.  Native Wayland clients
 * (Firefox, VLC, Signal, Stremio) are fullscreen and cover that DOM surface.
 * This layer-shell OVERLAY surface keeps the same Nuxel top strip visible:
 * clock on the left, Wi-Fi/battery on the right.  It uses an empty input
 * region, so taps pass through to the client underneath (the Home DOM status
 * bar remains the Quick Settings gesture owner while Home is visible).
 *
 * Scope is deliberately tiny: it reads /sys and /proc, renders with cairo/Pango
 * into a wl_shm buffer, and never touches /dev/fb0, storage or the USB gadget.
 */
#define _GNU_SOURCE
#include <cairo/cairo.h>
#include <pango/pangocairo.h>
#include <errno.h>
#include <fcntl.h>
#include <poll.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/mman.h>
#include <sys/stat.h>
#include <time.h>
#include <unistd.h>
#include <wayland-client.h>
#include "wlr-layer-shell-unstable-v1-client-protocol.h"

#define BAR_HEIGHT 36
#define STATE_FILE "/run/nuxel-statusbar.state"

static struct wl_display *display;
static struct wl_registry *registry;
static struct wl_compositor *compositor;
static struct wl_shm *shm;
static struct zwlr_layer_shell_v1 *layer_shell;
static struct wl_output *output;
static struct wl_surface *surface;
static struct zwlr_layer_surface_v1 *layer_surface;
static int32_t width = 360, height = BAR_HEIGHT, scale = 2;
static int configured = 0;

static void audit(const char *fmt, ...) {
  FILE *f = fopen(STATE_FILE, "a");
  if (!f) return;
  va_list ap; va_start(ap, fmt);
  time_t t = time(NULL); struct tm tm; localtime_r(&t, &tm);
  char ts[32]; strftime(ts, sizeof ts, "%Y-%m-%dT%H:%M:%S", &tm);
  fprintf(f, "%s ", ts); vfprintf(f, fmt, ap); fputc('\n', f);
  va_end(ap); fclose(f);
}

static int read_text(const char *path, char *out, size_t n) {
  FILE *f = fopen(path, "r");
  if (!f) return 0;
  if (!fgets(out, (int)n, f)) { fclose(f); return 0; }
  fclose(f);
  size_t l = strlen(out);
  while (l && (out[l-1] == '\n' || out[l-1] == '\r')) out[--l] = 0;
  return l > 0;
}

static int wifi_up(void) {
  char b[64];
  if (read_text("/sys/class/net/wlan0/operstate", b, sizeof b))
    return !strcmp(b, "up");
  return 0;
}

static int battery_level(void) {
  char b[64];
  if (read_text("/sys/class/power_supply/battery/capacity", b, sizeof b))
    return atoi(b);
  return -1;
}

static int battery_charging(void) {
  char b[64];
  return read_text("/sys/class/power_supply/battery/status", b, sizeof b) &&
         (!strcasecmp(b, "Charging") || !strcasecmp(b, "Full"));
}

static int create_shm(size_t size) {
  int fd = memfd_create("nuxel-statusbar", MFD_CLOEXEC);
  if (fd < 0) return -1;
  if (ftruncate(fd, (off_t)size) < 0) { close(fd); return -1; }
  return fd;
}

static void render(void) {
  if (!configured || !surface || !shm) return;
  int bw = width * scale, bh = height * scale;
  size_t stride = (size_t)bw * 4, size = stride * (size_t)bh;
  int fd = create_shm(size);
  if (fd < 0) return;
  unsigned char *px = mmap(NULL, size, PROT_READ | PROT_WRITE, MAP_SHARED, fd, 0);
  if (px == MAP_FAILED) { close(fd); return; }
  cairo_surface_t *cs = cairo_image_surface_create_for_data(px, CAIRO_FORMAT_ARGB32, bw, bh, (int)stride);
  cairo_t *cr = cairo_create(cs);
  cairo_scale(cr, scale, scale);

  /* Opaque Nuxel strip (matches the launcher's status-bar colour family). */
  cairo_set_source_rgba(cr, 0.043, 0.071, 0.122, 0.96);
  cairo_paint(cr);

  char timebuf[16]; time_t t = time(NULL); struct tm tm; localtime_r(&t, &tm);
  strftime(timebuf, sizeof timebuf, "%H:%M", &tm);
  char right[96]; int lvl = battery_level();
  int chg = battery_charging();
  snprintf(right, sizeof right, "%s%s %d%%", wifi_up() ? "Wi-Fi  " : "", chg ? "⚡" : "", lvl >= 0 ? lvl : 0);

  PangoLayout *layout = pango_cairo_create_layout(cr);
  PangoFontDescription *desc = pango_font_description_from_string("Nuxel Sans 13");
  pango_layout_set_font_description(layout, desc);
  cairo_set_source_rgb(cr, 0.92, 0.96, 1.0);

  pango_layout_set_text(layout, timebuf, -1);
  int tw = 0, th = 0; pango_layout_get_pixel_size(layout, &tw, &th);
  cairo_move_to(cr, 14, (height - th) / 2.0 - 1);
  pango_cairo_show_layout(cr, layout);

  pango_layout_set_text(layout, right, -1);
  pango_layout_get_pixel_size(layout, &tw, &th);
  cairo_move_to(cr, width - tw - 14, (height - th) / 2.0 - 1);
  pango_cairo_show_layout(cr, layout);

  pango_font_description_free(desc);
  g_object_unref(layout);
  cairo_destroy(cr);
  cairo_surface_flush(cs);

  struct wl_shm_pool *pool = wl_shm_create_pool(shm, fd, size);
  struct wl_buffer *buf = wl_shm_pool_create_buffer(pool, 0, bw, bh, (int)stride,
                                                   WL_SHM_FORMAT_ARGB8888);
  wl_shm_pool_destroy(pool);
  wl_surface_set_buffer_scale(surface, scale);
  wl_surface_attach(surface, buf, 0, 0);
  wl_surface_damage(surface, 0, 0, bw, bh);
  wl_surface_commit(surface);
  cairo_surface_destroy(cs);
  munmap(px, size);
  wl_buffer_destroy(buf);   /* compositor has copied the SHM contents */
  close(fd);
}

static void layer_configure(void *d, struct zwlr_layer_surface_v1 *ls,
                            uint32_t serial, uint32_t w, uint32_t h) {
  (void)d;
  if ((int32_t)w > 0) width = (int32_t)w;
  height = BAR_HEIGHT;
  zwlr_layer_surface_v1_ack_configure(ls, serial);
  configured = 1;
  render();
}
static void layer_closed(void *d, struct zwlr_layer_surface_v1 *ls) {
  (void)d; (void)ls; audit("LAYER_CLOSED");
}
static const struct zwlr_layer_surface_v1_listener layer_listener = {
  .configure = layer_configure, .closed = layer_closed,
};

static void output_mode(void *d, struct wl_output *o, uint32_t flags,
                        int32_t w, int32_t h, int32_t refresh) {
  (void)d; (void)o; (void)flags; (void)refresh; (void)w; (void)h;
}
static void output_scale(void *d, struct wl_output *o, int32_t s) {
  (void)d; (void)o; if (s > 0) scale = s;
}
static void output_geometry(void *d, struct wl_output *o, int32_t x, int32_t y,
                            int32_t pw, int32_t ph, int32_t sub, const char *make,
                            const char *model, int32_t transform) {
  (void)d;(void)o;(void)x;(void)y;(void)pw;(void)ph;(void)sub;(void)make;(void)model;(void)transform;
}
static void output_done(void *d, struct wl_output *o) { (void)d;(void)o; }
static const struct wl_output_listener output_listener = {
  .geometry = output_geometry, .mode = output_mode, .done = output_done,
  .scale = output_scale,
};

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
}
static void reg_remove(void *d, struct wl_registry *r, uint32_t name) { (void)d;(void)r;(void)name; }
static const struct wl_registry_listener reg_listener = { reg_global, reg_remove };

int main(void) {
  unlink(STATE_FILE);
  display = wl_display_connect(NULL);
  if (!display) { audit("DISPLAY_CONNECT_FAIL"); return 1; }
  registry = wl_display_get_registry(display);
  wl_registry_add_listener(registry, &reg_listener, NULL);
  wl_display_roundtrip(display);
  if (!compositor || !shm || !layer_shell || !output) {
    audit("GLOBALS_MISSING compositor=%d shm=%d layer=%d output=%d",
          !!compositor, !!shm, !!layer_shell, !!output);
    return 2;
  }
  wl_output_add_listener(output, &output_listener, NULL);
  wl_display_roundtrip(display);

  surface = wl_compositor_create_surface(compositor);
  layer_surface = zwlr_layer_shell_v1_get_layer_surface(
      layer_shell, surface, output, ZWLR_LAYER_SHELL_V1_LAYER_OVERLAY, "nuxel-statusbar");
  zwlr_layer_surface_v1_set_anchor(layer_surface,
      ZWLR_LAYER_SURFACE_V1_ANCHOR_TOP | ZWLR_LAYER_SURFACE_V1_ANCHOR_LEFT |
      ZWLR_LAYER_SURFACE_V1_ANCHOR_RIGHT);
  zwlr_layer_surface_v1_set_size(layer_surface, 0, BAR_HEIGHT);
  zwlr_layer_surface_v1_set_exclusive_zone(layer_surface, BAR_HEIGHT);
  zwlr_layer_surface_v1_set_keyboard_interactivity(layer_surface,
      ZWLR_LAYER_SURFACE_V1_KEYBOARD_INTERACTIVITY_NONE);
  /* Empty input region: taps pass through to Home's own status bar (Quick
     Settings gesture) while Home is visible, and to the app otherwise. */
  struct wl_region *empty = wl_compositor_create_region(compositor);
  wl_surface_set_input_region(surface, empty);
  wl_region_destroy(empty);
  zwlr_layer_surface_v1_add_listener(layer_surface, &layer_listener, NULL);
  wl_surface_commit(surface);
  wl_display_roundtrip(display);

  audit("STATUSBAR_READY width=%d height=%d scale=%d", width, height, scale);
  time_t last = 0;
  for (;;) {
    while (wl_display_prepare_read(display) != 0) {
      if (wl_display_dispatch_pending(display) < 0) return 0;
    }
    wl_display_flush(display);
    struct pollfd pf = { .fd = wl_display_get_fd(display), .events = POLLIN };
    int pr = poll(&pf, 1, 5000);
    if (pr < 0) { wl_display_cancel_read(display); if (errno == EINTR) continue; return 0; }
    if (pr == 0) {
      wl_display_cancel_read(display);
      time_t now = time(NULL);
      if (now - last >= 10) { last = now; render(); }
      continue;
    }
    if (pf.revents & POLLIN) {
      if (wl_display_read_events(display) < 0) return 0;
      if (wl_display_dispatch_pending(display) < 0) return 0;
    } else {
      wl_display_cancel_read(display);
    }
  }
}
