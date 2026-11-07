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
/* PWNAGE-80000: the native OSD used to be pass-through-only, so the power menu
 * it painted above every app could not be tapped.  These fields describe the
 * exact card geometry from the last frame; the input region and the touch
 * mapping use the same numbers, so a visible row and a tappable row cannot
 * disagree. */
static int menu_present = 0;
static int menu_rows = 0;
static int menu_index = 0;
static int menu_cols = 1;
static int menu_rows_per_col = 0;
static double menu_x = 0, menu_y = 0, menu_cw = 0, menu_ch = 0;
static double menu_row_h = 46.0, menu_col_w = 0;
static struct wl_seat *seat = NULL;
static struct wl_touch *touch = NULL;
static struct wl_pointer *pointer = NULL;
static int touch_active = 0;
static double touch_x = 0, touch_y = 0;
#define BUTTON_FIFO "/run/nuxel-buttons.cmd"
#define HAPTIC_FIFO "/run/nuxel-haptics/haptics.cmd"

static void button_line(const char *line) {
  int fd = open(BUTTON_FIFO, O_WRONLY | O_NONBLOCK);
  if (fd < 0) return;
  dprintf(fd, "%s\n", line);
  close(fd);
}
static void haptic_line(const char *line) {
  int fd = open(HAPTIC_FIFO, O_WRONLY | O_NONBLOCK);
  if (fd < 0) return;
  dprintf(fd, "%s\n", line);
  close(fd);
}
static void osd_input_region(int interactive) {
  if (!surface || !compositor) return;
  struct wl_region *r = wl_compositor_create_region(compositor);
  if (!r) return;
  if (interactive) {
    /* Full-screen modal: a tap outside the card closes the menu, while every
     * app touch underneath is blocked until the menu is dismissed. */
    wl_region_add(r, 0, 0, width, height);
  }
  wl_surface_set_input_region(surface, r);
  wl_region_destroy(r);
  wl_surface_commit(surface);
}

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
    /* The landscape layer-shell height can be as little as 600 logical px
     * after the status/nav exclusive zones.  Sixteen rows at a 34 px minimum
     * then overflow the card.  Use two columns in that case so every visible
     * row is also inside the hit-test card.  Portrait keeps one column. */
    int cols = (n > 10 && height < 900) ? 2 : 1;
    int rows_per_col = (n + cols - 1) / cols;
    double cardw = fmin(width - 36.0, cols == 2 ? 620.0 : 320.0);
    double cardh = fmin(height - 40.0, 84.0 + rows_per_col * 46.0);
    double ideal_row = (cardh - 84.0) / (rows_per_col > 0 ? rows_per_col : 1);
    menu_row_h = ideal_row > 46.0 ? 46.0 : ideal_row;
    if (menu_row_h < 32.0) menu_row_h = 32.0;
    menu_cols = cols;
    menu_rows_per_col = rows_per_col;
    menu_col_w = cardw / cols;
    double x = (width - cardw) / 2.0, y = (height - cardh) / 2.0;
    menu_present = 1; menu_rows = n; menu_index = (int)idx;
    menu_x = x; menu_y = y; menu_cw = cardw; menu_ch = cardh;
    cairo_set_source_rgba(cr, 0.047, 0.086, 0.149, 0.98);
    cairo_rectangle(cr, x, y, cardw, cardh);
    cairo_fill(cr);
    cairo_set_source_rgba(cr, 0.376, 0.647, 0.98, 0.55);
    cairo_set_line_width(cr, 1.0);
    cairo_rectangle(cr, x + .5, y + .5, cardw - 1, cardh - 1);
    cairo_stroke(cr);
    draw_text(cr, "POWER", x + 16, y + 14, cardw - 32, "Nuxel Sans Bold 11", .63, .82, 1.0, 0);
    for (int i = 0; i < n; i++) {
      int c = cols == 2 ? i / rows_per_col : 0;
      int r = cols == 2 ? i % rows_per_col : i;
      double cx = x + c * menu_col_w;
      double ry = y + 46 + r * menu_row_h;
      if (i == (int)idx) {
        cairo_set_source_rgba(cr, 0.114, 0.306, 0.847, 1.0);
        cairo_rectangle(cr, cx + 10, ry, menu_col_w - 20, menu_row_h - 6);
        cairo_fill(cr);
      }
      draw_text(cr, labs[i], cx + 22, ry + (menu_row_h - 18) / 2, menu_col_w - 44,
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

  if (!(power && n > 0)) { menu_present = 0; menu_rows = 0; }
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


/* ---- touch (PWNAGE-80000) ------------------------------------------------ */
static int menu_row_at(double x, double y) {
  if (!menu_present) return -1;
  if (x < menu_x || x > menu_x + menu_cw || y < menu_y || y > menu_y + menu_ch)
    return -2;                       /* outside the card: dismiss */
  int c = menu_cols == 2 ? (int)((x - menu_x) / menu_col_w) : 0;
  if (c < 0) c = 0;
  if (c >= menu_cols) c = menu_cols - 1;
  double top = menu_y + 46.0;
  if (y < top) return -1;            /* title area: no action */
  int r = (int)((y - top) / menu_row_h);
  if (r < 0 || r >= menu_rows_per_col) return -1;
  int i = c * menu_rows_per_col + r;
  return i < menu_rows ? i : -1;
}
static void menu_activate(double x, double y) {
  int row = menu_row_at(x, y);
  if (row >= 0) {
    char line[64];
    snprintf(line, sizeof line, "menu-select %d", row);
    button_line(line);
    haptic_line("navigation");
    menu_present = 0;
    osd_input_region(0);
    fprintf(stderr, "OSD_MENU_TAP row=%d x=%.1f y=%.1f\n", row, x, y);
  } else if (row == -2) {
    button_line("menu-close");
    haptic_line("navigation");
    menu_present = 0;
    osd_input_region(0);
    fprintf(stderr, "OSD_MENU_DISMISS outside x=%.1f y=%.1f\n", x, y);
  }
}

/* Pointer input is deliberately supported as well as touch: the layer-shell
 * menu must be usable by a mouse/trackpad on the desktop and by the test
 * harness.  The visible row and the hit-tested row are the same rectangle. */
static void pointer_enter_cb(void *d, struct wl_pointer *p, uint32_t serial,
                             struct wl_surface *surf, wl_fixed_t x, wl_fixed_t y) {
  (void)d; (void)p; (void)serial; (void)surf;
  touch_x = wl_fixed_to_double(x); touch_y = wl_fixed_to_double(y);
}
static void pointer_leave_cb(void *d, struct wl_pointer *p, uint32_t serial,
                             struct wl_surface *surf) {
  (void)d; (void)p; (void)serial; (void)surf;
}
static void pointer_motion_cb(void *d, struct wl_pointer *p, uint32_t time,
                              wl_fixed_t x, wl_fixed_t y) {
  (void)d; (void)p; (void)time;
  touch_x = wl_fixed_to_double(x); touch_y = wl_fixed_to_double(y);
}
static void pointer_button_cb(void *d, struct wl_pointer *p, uint32_t serial,
                              uint32_t time, uint32_t button, uint32_t state) {
  (void)d; (void)p; (void)serial; (void)time;
  if (button != 0x110 || state != WL_POINTER_BUTTON_STATE_RELEASED || !menu_present) return;
  menu_activate(touch_x, touch_y);
}
static void pointer_axis_cb(void *d, struct wl_pointer *p, uint32_t time,
                            uint32_t axis, wl_fixed_t value) {
  (void)d; (void)p; (void)time; (void)axis; (void)value;
}
static void pointer_frame_cb(void *d, struct wl_pointer *p) { (void)d; (void)p; }
static void pointer_axis_source_cb(void *d, struct wl_pointer *p, uint32_t source) {
  (void)d; (void)p; (void)source;
}
static void pointer_axis_stop_cb(void *d, struct wl_pointer *p, uint32_t time, uint32_t axis) {
  (void)d; (void)p; (void)time; (void)axis;
}
static void pointer_axis_discrete_cb(void *d, struct wl_pointer *p, uint32_t axis, int32_t discrete) {
  (void)d; (void)p; (void)axis; (void)discrete;
}
static const struct wl_pointer_listener pointer_listener = {
  .enter = pointer_enter_cb, .leave = pointer_leave_cb, .motion = pointer_motion_cb,
  .button = pointer_button_cb, .axis = pointer_axis_cb, .frame = pointer_frame_cb,
  .axis_source = pointer_axis_source_cb, .axis_stop = pointer_axis_stop_cb,
  .axis_discrete = pointer_axis_discrete_cb,
};

static void touch_down_cb(void *d, struct wl_touch *t, uint32_t serial,
                          uint32_t time, struct wl_surface *surf, int32_t id,
                          wl_fixed_t x, wl_fixed_t y) {
  (void)d; (void)t; (void)serial; (void)time; (void)surf; (void)id;
  if (!menu_present) return;
  touch_active = 1;
  touch_x = wl_fixed_to_double(x);
  touch_y = wl_fixed_to_double(y);
}
static void touch_up_cb(void *d, struct wl_touch *t, uint32_t serial,
                        uint32_t time, int32_t id) {
  (void)d; (void)t; (void)serial; (void)time; (void)id;
  if (!touch_active) return;
  touch_active = 0;
  menu_activate(touch_x, touch_y);
}
static void touch_motion_cb(void *d, struct wl_touch *t, uint32_t time, int32_t id,
                            wl_fixed_t x, wl_fixed_t y) {
  (void)d; (void)t; (void)time; (void)id;
  touch_x = wl_fixed_to_double(x); touch_y = wl_fixed_to_double(y);
}
static void touch_frame_cb(void *d, struct wl_touch *t) { (void)d; (void)t; }
static void touch_cancel_cb(void *d, struct wl_touch *t) { (void)d; (void)t; touch_active = 0; }
static const struct wl_touch_listener touch_listener = {
  .down = touch_down_cb, .up = touch_up_cb, .motion = touch_motion_cb,
  .frame = touch_frame_cb, .cancel = touch_cancel_cb,
};
static void seat_caps_cb(void *d, struct wl_seat *s, uint32_t caps) {
  (void)d; (void)s;
  if ((caps & WL_SEAT_CAPABILITY_TOUCH) && !touch) {
    touch = wl_seat_get_touch(seat);
    wl_touch_add_listener(touch, &touch_listener, NULL);
  } else if (!(caps & WL_SEAT_CAPABILITY_TOUCH) && touch) {
    wl_touch_destroy(touch); touch = NULL;
  }
  if ((caps & WL_SEAT_CAPABILITY_POINTER) && !pointer) {
    pointer = wl_seat_get_pointer(seat);
    wl_pointer_add_listener(pointer, &pointer_listener, NULL);
  } else if (!(caps & WL_SEAT_CAPABILITY_POINTER) && pointer) {
    wl_pointer_destroy(pointer); pointer = NULL;
  }
}
static void seat_name_cb(void *d, struct wl_seat *s, const char *name) {
  (void)d; (void)s; (void)name;
}
static const struct wl_seat_listener seat_listener = {
  .capabilities = seat_caps_cb, .name = seat_name_cb,
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
  else if (!strcmp(iface, wl_seat_interface.name) && !seat)
    seat = wl_registry_bind(r, name, &wl_seat_interface, 5);
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
  if (seat) wl_seat_add_listener(seat, &seat_listener, NULL);
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
  osd_input_region(0);
  zwlr_layer_surface_v1_add_listener(layer_surface, &layer_listener, NULL);
  wl_surface_commit(surface);
  wl_display_roundtrip(display);

  char json[32768];
  int last_visible = 0;
  int last_interactive = -1;
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
        if (menu_present != last_interactive) {
          osd_input_region(menu_present);
          last_interactive = menu_present;
          fprintf(stderr, "OSD_INPUT interactive=%d rows=%d row_h=%.1f cols=%d rows_per_col=%d\n", menu_present, menu_rows, menu_row_h, menu_cols, menu_rows_per_col);
        }
        last_visible = visible;
      } else if (visible && !strcmp(kind, "power-menu") && n > 0) {
        /* Keep the selected row current while hardware volume keys move it. */
        static double last_idx = -1;
        if (idx != last_idx) { last_idx = idx; draw_osd(json);
          if (menu_present != last_interactive) { osd_input_region(menu_present); last_interactive = menu_present; } }
      }
    } else if (pf.revents & POLLIN) {
      if (wl_display_read_events(display) < 0) return 0;
      if (wl_display_dispatch_pending(display) < 0) return 0;
    } else {
      wl_display_cancel_read(display);
    }
  }
}
