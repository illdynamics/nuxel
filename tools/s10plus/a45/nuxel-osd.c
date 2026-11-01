/* nuxel-osd — native overlay for volume and the power menu.
 *
 * The Home PWA's OSD is a DOM element inside nuxel-pwa-host.  A native
 * fullscreen client (Firefox/VLC/...) covers that WebView, so the DOM OSD can
 * be alive and audible yet invisible.  This tiny layer-shell client reads the
 * SAME publisher file (/usr/share/nuxel/runtime/osd.json) and draws above any
 * client.  It owns no state and never invents an action: hardware keys still
 * drive nuxel-button-manager, which writes the file.
 *
 * Input is deliberately pass-through (empty input region).  Menu selection is
 * by the hardware volume/power keys, exactly as before.
 */
#define _GNU_SOURCE
#include <cairo/cairo.h>
#include <pango/pangocairo.h>
#include <errno.h>
#include <fcntl.h>
#include <math.h>
#include <poll.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/mman.h>
#include <time.h>
#include <unistd.h>
#include <wayland-client.h>
#include "wlr-layer-shell-unstable-v1-client-protocol.h"

#define OSD_FILE "/usr/share/nuxel/runtime/osd.json"
#define MAX_ENTRIES 24

static struct wl_display *display;
static struct wl_registry *registry;
static struct wl_compositor *compositor;
static struct wl_shm *shm;
static struct zwlr_layer_shell_v1 *layer_shell;
static struct wl_output *output;
static struct wl_surface *surface;
static struct zwlr_layer_surface_v1 *layer_surface;
static int32_t width = 360, height = 760, scale = 2;
static int configured = 0;
static char last_draw[32768];
static double shown_at = 0;

static int read_file(const char *path, char *out, size_t n) {
  FILE *f = fopen(path, "r");
  if (!f) { if (n) out[0] = 0; return 0; }
  size_t got = fread(out, 1, n - 1, f);
  fclose(f);
  out[got] = 0;
  return (int)got;
}

static int jstr(const char *b, const char *key, char *out, size_t n) {
  char pat[80]; snprintf(pat, sizeof pat, "\"%s\"", key);
  const char *p = strstr(b, pat);
  if (!p) return 0;
  p = strchr(p + strlen(pat), ':');
  if (!p) return 0;
  p++;
  while (*p == ' ' || *p == '\t' || *p == '\n' || *p == '\r') p++;
  if (*p != '"') return 0;
  p++;
  size_t i = 0;
  while (*p && *p != '"' && i + 1 < n) {
    if (*p == '\\' && p[1]) p++;
    out[i++] = *p++;
  }
  out[i] = 0;
  return 1;
}

static int jnum(const char *b, const char *key, double *out) {
  char pat[80]; snprintf(pat, sizeof pat, "\"%s\"", key);
  const char *p = strstr(b, pat);
  if (!p) return 0;
  p = strchr(p + strlen(pat), ':');
  if (!p) return 0;
  char *end = NULL;
  double v = strtod(p + 1, &end);
  if (end == p + 1) return 0;
  *out = v;
  return 1;
}

static int labels(const char *b, char out[MAX_ENTRIES][96]) {
  const char *p = strstr(b, "\"entries\"");
  int n = 0;
  if (!p) return 0;
  p = strchr(p, '[');
  if (!p) return 0;
  while ((p = strstr(p, "\"label\"")) && n < MAX_ENTRIES) {
    const char *q = strchr(p, ':');
    if (!q) break;
    q++;
    while (*q == ' ' || *q == '\t' || *q == '\n' || *q == '\r') q++;
    if (*q != '"') { p = q; continue; }
    q++;
    int i = 0;
    while (*q && *q != '"' && i < 95) {
      if (*q == '\\' && q[1]) q++;
      out[n][i++] = *q++;
    }
    out[n][i] = 0;
    n++;
    p = q;
  }
  return n;
}

static void draw_text(cairo_t *cr, const char *text, double x, double y,
                      double w, const char *font, double r, double g, double b,
                      int align) {
  PangoLayout *l = pango_cairo_create_layout(cr);
  PangoFontDescription *d = pango_font_description_from_string(font);
  pango_layout_set_font_description(l, d);
  pango_layout_set_width(l, (int)(w * PANGO_SCALE));
  pango_layout_set_wrap(l, PANGO_WRAP_WORD_CHAR);
  if (align == 1) pango_layout_set_alignment(l, PANGO_ALIGN_CENTER);
  pango_layout_set_text(l, text ? text : "", -1);
  int tw = 0, th = 0; pango_layout_get_pixel_size(l, &tw, &th);
  cairo_set_source_rgba(cr, r, g, b, 1.0);
  cairo_move_to(cr, x, y);
  pango_cairo_show_layout(cr, l);
  pango_font_description_free(d);
  g_object_unref(l);
}

static void draw_osd(const char *json) {
  if (!configured || !surface || !shm) return;
  int bw = width * scale, bh = height * scale;
  size_t stride = (size_t)bw * 4, size = stride * (size_t)bh;
  int fd = memfd_create("nuxel-osd", MFD_CLOEXEC);
  if (fd < 0) return;
  if (ftruncate(fd, (off_t)size) < 0) { close(fd); return; }
  unsigned char *px = mmap(NULL, size, PROT_READ | PROT_WRITE, MAP_SHARED, fd, 0);
  if (px == MAP_FAILED) { close(fd); return; }
  cairo_surface_t *cs = cairo_image_surface_create_for_data(px, CAIRO_FORMAT_ARGB32, bw, bh, (int)stride);
  cairo_t *cr = cairo_create(cs);
  cairo_scale(cr, scale, scale);
  cairo_set_operator(cr, CAIRO_OPERATOR_SOURCE);
  cairo_set_source_rgba(cr, 0, 0, 0, 0);
  cairo_paint(cr);
  cairo_set_operator(cr, CAIRO_OPERATOR_OVER);

  char kind[64] = "", text[512] = "";
  double ts = 0, value = 0, maxv = 0, idx = 0;
  jstr(json, "kind", kind, sizeof kind);
  jstr(json, "text", text, sizeof text);
  jnum(json, "ts", &ts); jnum(json, "value", &value);
  jnum(json, "max", &maxv); jnum(json, "index", &idx);

  int power = !strcmp(kind, "power-menu");
  char labs[MAX_ENTRIES][96];
  int n = power ? labels(json, labs) : 0;
  double age = time(NULL) - ts;

  if (power && n > 0) {
    cairo_set_source_rgba(cr, 0.008, 0.024, 0.055, 0.68);
    cairo_paint(cr);
    double cardw = fmin(width - 36.0, 320.0);
    double cardh = fmin(height - 80.0, 56.0 + n * 46.0);
    double x = (width - cardw) / 2.0, y = (height - cardh) / 2.0;
    cairo_set_source_rgba(cr, 0.047, 0.086, 0.149, 0.98);
    cairo_rectangle(cr, x, y, cardw, cardh);
    cairo_fill(cr);
    cairo_set_source_rgba(cr, 0.376, 0.647, 0.98, 0.55);
    cairo_set_line_width(cr, 1.0);
    cairo_rectangle(cr, x + .5, y + .5, cardw - 1, cardh - 1);
    cairo_stroke(cr);
    draw_text(cr, "POWER", x + 16, y + 14, cardw - 32, "Nuxel Sans Bold 11", .63, .82, 1.0, 0);
    for (int i = 0; i < n; i++) {
      double ry = y + 46 + i * 46;
      if (i == (int)idx) {
        cairo_set_source_rgba(cr, 0.114, 0.306, 0.847, 1.0);
        cairo_rectangle(cr, x + 10, ry, cardw - 20, 40);
        cairo_fill(cr);
      }
      draw_text(cr, labs[i], x + 22, ry + 10, cardw - 44,
                "Nuxel Sans 14", .92, .96, 1.0, 0);
    }
    draw_text(cr, "Volume Up/Down to move  ·  Power to choose", x + 16,
              y + cardh - 28, cardw - 32, "Nuxel Sans 10", .58, .66, .78, 1);
  } else if (!strcmp(kind, "power-menu") && age < 7.0) {
    /* Refusal / informational line from the power-menu publisher. */
    double cardw = fmin(width - 36.0, 320.0), cardh = 64;
    double x = (width - cardw) / 2.0, y = 58;
    cairo_set_source_rgba(cr, 0.047, 0.086, 0.149, 0.96);
    cairo_rectangle(cr, x, y, cardw, cardh);
    cairo_fill(cr);
    draw_text(cr, text, x + 14, y + 12, cardw - 28, "Nuxel Sans 13", .92, .96, 1.0, 1);
  } else if ((!strcmp(kind, "volume") || !strcmp(kind, "sound") || !strcmp(kind, "flashlight") ||
              !strcmp(kind, "power") || !strcmp(kind, "toast") || !strcmp(kind, "brightness")) &&
             age < 3.2 && *text) {
    double cardw = fmin(width - 40.0, 240.0), cardh = maxv > 0 ? 92 : 70;
    double x = (width - cardw) / 2.0, y = 54;
    cairo_set_source_rgba(cr, 0.039, 0.086, 0.157, 0.96);
    cairo_rectangle(cr, x, y, cardw, cardh);
    cairo_fill(cr);
    draw_text(cr, kind, x + 14, y + 10, cardw - 28, "Nuxel Sans Bold 10", .62, .82, 1.0, 1);
    draw_text(cr, text, x + 14, y + 28, cardw - 28, "Nuxel Sans Bold 20", .92, .96, 1.0, 1);
    if (maxv > 0) {
      double pct = value / maxv; if (pct < 0) pct = 0; if (pct > 1) pct = 1;
      cairo_set_source_rgba(cr, 1, 1, 1, .16);
      cairo_rectangle(cr, x + 16, y + cardh - 22, cardw - 32, 5);
      cairo_fill(cr);
      cairo_set_source_rgba(cr, 0.23, 0.51, 0.96, 1);
      cairo_rectangle(cr, x + 16, y + cardh - 22, (cardw - 32) * pct, 5);
      cairo_fill(cr);
    }
  }

  cairo_destroy(cr);
  cairo_surface_flush(cs);
  struct wl_shm_pool *pool = wl_shm_create_pool(shm, fd, size);
  struct wl_buffer *buf = wl_shm_pool_create_buffer(pool, 0, bw, bh, (int)stride, WL_SHM_FORMAT_ARGB8888);
  wl_shm_pool_destroy(pool);
  wl_surface_set_buffer_scale(surface, scale);
  wl_surface_attach(surface, buf, 0, 0);
  wl_surface_damage(surface, 0, 0, bw, bh);
  wl_surface_commit(surface);
  cairo_surface_destroy(cs);
  munmap(px, size);
  wl_buffer_destroy(buf);
  close(fd);
}

static const struct zwlr_layer_surface_v1_listener layer_listener;
static void layer_configure(void *d, struct zwlr_layer_surface_v1 *ls,
                            uint32_t serial, uint32_t w, uint32_t h) {
  (void)d;
  if ((int32_t)w > 0) width = (int32_t)w;
  if ((int32_t)h > 0) height = (int32_t)h;
  zwlr_layer_surface_v1_ack_configure(ls, serial);
  configured = 1;
  last_draw[0] = 0;
}
static void layer_closed(void *d, struct zwlr_layer_surface_v1 *ls) {
  (void)d; (void)ls; layer_surface = NULL; configured = 0;
}
static const struct zwlr_layer_surface_v1_listener layer_listener = {
  .configure = layer_configure, .closed = layer_closed,
};

static void output_mode(void *d, struct wl_output *o, uint32_t flags, int32_t w, int32_t h, int32_t refresh) {
  (void)d; (void)o; if (flags & WL_OUTPUT_MODE_CURRENT) { if (w > 0) width = w; if (h > 0) height = h; }
  (void)refresh;
}
static void output_scale(void *d, struct wl_output *o, int32_t s) { (void)d; (void)o; if (s > 0) scale = s; }
static void output_geometry(void *d, struct wl_output *o, int32_t x, int32_t y, int32_t pw, int32_t ph,
                            int32_t sub, const char *make, const char *model, int32_t transform) {
  (void)d;(void)o;(void)x;(void)y;(void)pw;(void)ph;(void)sub;(void)make;(void)model;(void)transform;
}
static void output_done(void *d, struct wl_output *o) { (void)d;(void)o; }
static const struct wl_output_listener output_listener = {
  .geometry = output_geometry, .mode = output_mode, .done = output_done, .scale = output_scale,
};

static void reg_global(void *d, struct wl_registry *r, uint32_t name, const char *iface, uint32_t ver) {
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
  display = wl_display_connect(NULL);
  if (!display) return 1;
  registry = wl_display_get_registry(display);
  wl_registry_add_listener(registry, &reg_listener, NULL);
  wl_display_roundtrip(display);
  if (!compositor || !shm || !layer_shell || !output) return 2;
  wl_output_add_listener(output, &output_listener, NULL);
  wl_display_roundtrip(display);

  surface = wl_compositor_create_surface(compositor);
  layer_surface = zwlr_layer_shell_v1_get_layer_surface(
      layer_shell, surface, output, ZWLR_LAYER_SHELL_V1_LAYER_OVERLAY, "nuxel-osd");
  zwlr_layer_surface_v1_set_anchor(layer_surface,
      ZWLR_LAYER_SURFACE_V1_ANCHOR_TOP | ZWLR_LAYER_SURFACE_V1_ANCHOR_BOTTOM |
      ZWLR_LAYER_SURFACE_V1_ANCHOR_LEFT | ZWLR_LAYER_SURFACE_V1_ANCHOR_RIGHT);
  zwlr_layer_surface_v1_set_size(layer_surface, 0, 0);
  zwlr_layer_surface_v1_set_exclusive_zone(layer_surface, 0);
  zwlr_layer_surface_v1_set_keyboard_interactivity(layer_surface,
      ZWLR_LAYER_SURFACE_V1_KEYBOARD_INTERACTIVITY_NONE);
  struct wl_region *empty = wl_compositor_create_region(compositor);
  wl_surface_set_input_region(surface, empty);
  wl_region_destroy(empty);
  zwlr_layer_surface_v1_add_listener(layer_surface, &layer_listener, NULL);
  wl_surface_commit(surface);
  wl_display_roundtrip(display);

  char json[32768];
  int last_visible = 0;
  double last_change = 0;
  for (;;) {
    while (wl_display_prepare_read(display) != 0) {
      if (wl_display_dispatch_pending(display) < 0) return 0;
    }
    wl_display_flush(display);
    struct pollfd pf = { .fd = wl_display_get_fd(display), .events = POLLIN };
    int pr = poll(&pf, 1, 150);
    if (pr < 0) { wl_display_cancel_read(display); if (errno == EINTR) continue; return 0; }
    if (pr == 0) {
      wl_display_cancel_read(display);
      read_file(OSD_FILE, json, sizeof json);
      char kind[64] = ""; double ts = 0, idx = 0;
      jstr(json, "kind", kind, sizeof kind);
      jnum(json, "ts", &ts); jnum(json, "index", &idx);
      char labs[MAX_ENTRIES][96];
      int n = !strcmp(kind, "power-menu") ? labels(json, labs) : 0;
      double age = time(NULL) - ts;
      int visible;
      if (!strcmp(kind, "power-menu")) visible = n > 0 || age < 7.0;
      else visible = strstr(json, "\"text\"") != NULL && age < 3.2;
      double now = (double)time(NULL);
      int changed = strcmp(json, last_draw) != 0;
      if (changed) {
        strncpy(last_draw, json, sizeof last_draw - 1);
        last_draw[sizeof last_draw - 1] = 0;
        shown_at = now;
        last_change = now;
      }
      /* Redraw on a state change, on the first visible frame, and exactly once
         when a toast expires (the transparent frame clears the old pixels). */
      if (changed || (visible && now - last_change > .0 &&
                      (!last_visible || !strcmp(kind, "power-menu"))) ||
          (!visible && last_visible)) {
        draw_osd(json);
        last_visible = visible;
      } else if (visible && !strcmp(kind, "power-menu") && n > 0) {
        /* Keep the selected row current while hardware volume keys move it. */
        static double last_idx = -1;
        if (idx != last_idx) { last_idx = idx; draw_osd(json); }
      }
    } else if (pf.revents & POLLIN) {
      if (wl_display_read_events(display) < 0) return 0;
      if (wl_display_dispatch_pending(display) < 0) return 0;
    } else {
      wl_display_cancel_read(display);
    }
  }
}
