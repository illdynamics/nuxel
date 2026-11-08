/* nuxel-statusbar — persistent top bar for fullscreen native applications.
 *
 * The Home PWA draws its own DOM status bar.  Native Wayland clients
 * (Firefox, VLC, Signal, Stremio) are fullscreen and cover that DOM surface.
 * This layer-shell OVERLAY surface keeps the same Nuxel top strip visible:
 * clock on the left, Wi-Fi/battery on the right.  Over a native app it
 * collapses to a bounded top-edge gesture strip, expands on a downward swipe,
 * and collapses again on the next upward swipe so taps reach the app.
 *
 * Scope is deliberately tiny: it reads /sys and /proc, renders with cairo/Pango
 * into a wl_shm buffer, and never touches /dev/fb0, storage or the USB gadget.
 */
#define _GNU_SOURCE
#include <cairo/cairo.h>
#include <pango/pangocairo.h>
#include <errno.h>
#include <math.h>
#include <stdarg.h>
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
/* PWNAGE-94000: this layer-shell client is the compositor-boundary
 * PRESENTATION ADAPTER for the canonical Nuxel top bar.  It never invents a
 * second bar: its data comes from /run/nuxel/statusbar-model.json, published by
 * the Home DOM status bar, and it renders the same four levels:
 *   0 strip (hidden), 1 standard bar, 2 expanded QS summary, 3 extended.
 * The surface never sets an exclusive zone, so a fullscreen app is never
 * resized while the panel is temporarily visible. */
#define BAR_STRIP_HEIGHT 12
#define BAR_STRIP_INPUT_PORTRAIT 40
#define BAR_STRIP_INPUT_LANDSCAPE 56
#define BAR_REVEAL_DISTANCE 16
#define BAR_AUTOHIDE_MS 4500
#define PANEL_EXPANDED_PORTRAIT 220
#define PANEL_EXPANDED_LANDSCAPE 180
#define PANEL_EXTENDED_PORTRAIT 470
#define PANEL_EXTENDED_LANDSCAPE 300
#define MODEL_FILE "/run/nuxel/statusbar-model.json"
#define CMD_FIFO "/run/nuxel-statusbar.cmd"
#define STATE_FILE "/run/nuxel-statusbar.state"
#define LOG_FILE "/run/nuxel-statusbar.log"
#define FG_STATE "/run/nuxel/foreground.state"
#define PRELOAD_OVERLAY "/run/nuxel/preload-cinema.overlay"
#define LOCK_STATE "/run/nuxel/security/lock-state.json"
#define LOCATION_POLICY "/var/lib/nuxel/permissions/location-policy.json"
#define FT_BIN "/usr/lib/nuxel/nuxel-foreign-toplevel"
#define HOST_FIFO "/run/nuxel-pwa-host.cmd"

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
static int32_t width = 360, height = BAR_HEIGHT, scale = 2;
static int configured = 0;
static int bar_level = 0;        /* 0 strip, 1 standard, 2 expanded, 3 extended */
static int strip_mode = 1;       /* derived: bar_level == 0 */
static int64_t reveal_deadline = 0;
static int touch_down = 0;
static int32_t down_y = 0, last_y = 0;
static int cmd_fd = -1;
static int32_t out_w = 720, out_h = 1520;

static void audit(const char *fmt, ...) {
  FILE *f = fopen(LOG_FILE, "a");
  if (!f) return;
  va_list ap; va_start(ap, fmt);
  time_t t = time(NULL); struct tm tm; localtime_r(&t, &tm);
  char ts[32]; strftime(ts, sizeof ts, "%Y-%m-%dT%H:%M:%S", &tm);
  fprintf(f, "%s ", ts); vfprintf(f, fmt, ap); fputc('\n', f);
  va_end(ap); fclose(f);
}

static int session_locked(void);
static int64_t now_ms(void);
static void bar_strip(void);
static void bar_set_level(int level);
static void bar_create(void);
static void bar_hide(void);

static int is_landscape(void) {
  /* Logical viewport width (layer configure), not physical panel pixels. */
  return width >= 500 || out_w > out_h;
}

static int strip_input_height(void) {
  return is_landscape() ? BAR_STRIP_INPUT_LANDSCAPE : BAR_STRIP_INPUT_PORTRAIT;
}

static int bar_height_for_level(int level) {
  if (level <= 0) return strip_input_height();
  if (level == 1) return BAR_HEIGHT;
  if (level == 2) return BAR_HEIGHT + (is_landscape() ? PANEL_EXPANDED_LANDSCAPE : PANEL_EXPANDED_PORTRAIT);
  return BAR_HEIGHT + (is_landscape() ? PANEL_EXTENDED_LANDSCAPE : PANEL_EXTENDED_PORTRAIT);
}

/* Read one scalar/string field from the canonical model.  The document is a
 * tiny, fixed-shape JSON written by the launcher; this parser deliberately
 * never allocates or walks arbitrary nesting. */
static int model_get(const char *key, char *out, size_t n) {
  if (!key || !out || n < 2) return 0;
  out[0] = 0;
  FILE *f = fopen(MODEL_FILE, "r");
  if (!f) return 0;
  char b[2048];
  size_t got = fread(b, 1, sizeof b - 1, f);
  fclose(f);
  b[got] = 0;
  char pat[96];
  snprintf(pat, sizeof pat, "\"%s\"", key);
  char *p = strstr(b, pat);
  if (!p) return 0;
  p = strchr(p + strlen(pat), ':');
  if (!p) return 0;
  p++;
  while (*p == ' ' || *p == '\t' || *p == '\n' || *p == '\r') p++;
  size_t i = 0;
  if (*p == '"') {
    p++;
    while (*p && *p != '"' && i + 1 < n) {
      if (*p == '\\' && p[1]) p++;
      out[i++] = *p++;
    }
  } else {
    while (*p && *p != ',' && *p != '}' && *p != '\n' && i + 1 < n) out[i++] = *p++;
    while (i && (out[i-1] == ' ' || out[i-1] == '\t')) i--;
  }
  out[i] = 0;
  return i > 0;
}

static void publish_state(int visible, const char *reason, const char *fg,
                          int locked, const char *error) {
  char tmp[128];
  snprintf(tmp, sizeof tmp, STATE_FILE ".%d", (int)getpid());
  FILE *f = fopen(tmp, "w");
  if (!f) return;
  fprintf(f,
    "{\"schema_version\":1,\"ready\":true,\"visible\":%s,"
    "\"reason\":\"%s\",\"foreground_app_id\":\"%s\","
    "\"locked\":%s,\"width\":%d,\"height\":%d,\"scale\":%d,"
    "\"strip\":%s,\"revealed\":%s,\"level\":%d,"
    "\"error\":\"%s\",\"owner\":\"nuxel-statusbar\"}\n",
    visible ? "true" : "false", reason ? reason : "",
    fg ? fg : "", locked ? "true" : "false", width, height, scale,
    strip_mode ? "true" : "false", bar_level > 0 ? "true" : "false", bar_level,
    error ? error : "");
  fclose(f);
  rename(tmp, STATE_FILE);
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

/* PWNAGE-45000 follow-up: the native overlay top bar must never cover the
 * lockscreen.  /run/nuxel/security/lock-state.json is the authoritative
 * session lock flag written by the root bridge.  Missing/unreadable state is
 * treated as LOCKED (fail closed), matching security_provider.py. */
static int session_locked(void) {
  FILE *f = fopen(LOCK_STATE, "r");
  if (!f) return 1;
  char b[4096];
  size_t n = fread(b, 1, sizeof b - 1, f);
  fclose(f);
  b[n] = 0;
  char *p = strstr(b, "\"locked\"");
  if (!p) return 1;
  p += 8;
  while (*p == ' ' || *p == '\t' || *p == '\n' || *p == '\r') p++;
  if (*p != ':') return 1;
  p++;
  while (*p == ' ' || *p == '\t' || *p == '\n' || *p == '\r') p++;
  return strncmp(p, "true", 4) == 0;
}

/* PWNAGE-49000: one top bar, never two.  The Home WebView draws the proper
 * full status bar; this native overlay exists only to keep chrome over a
 * separate GTK/Flatpak toplevel.  Ask the compositor which toplevel is
 * activated and show the overlay only when it is a non-Home app.  The helper
 * is the same trusted foreign-toplevel tool used by Back/Home; it is a short
 * bounded child, not a poller inside the render path. */
static int foreground_from_watcher(char *app_id, size_t app_n) {
  struct stat st;
  if (stat(FG_STATE, &st) != 0) return -1;
  /* The lock watcher rewrites this at least every 2 s while running.  A stale
     file must not pin chrome over Home. */
  if (time(NULL) - st.st_mtime > 3) return -1;
  char b[512];
  if (!read_text(FG_STATE, b, sizeof b)) return -1;
  if (!strstr(b, "locked=0")) return -1;
  if (!strstr(b, "native=1")) return -1;
  const char *p = strstr(b, "app_id=");
  if (!p) return -1;
  p += 7;
  size_t i = 0;
  while (*p && *p != '\n' && *p != ' ' && i + 1 < app_n) app_id[i++] = *p++;
  app_id[i] = 0;
  return *app_id ? 1 : -1;
}

static int native_foreground(char *app_id, size_t app_n) {
  if (app_id && app_n) app_id[0] = 0;
  int cached = foreground_from_watcher(app_id, app_n);
  if (cached >= 0) return cached;
  /* Fallback for a missing/restarting watcher: one bounded helper invocation.
     The caller applies a 2 s cache, so this is never a per-frame cost. */
  FILE *p = popen(FT_BIN " list 2>/dev/null", "r");
  if (!p) return 0;
  char line[512];
  int found = 0;
  while (fgets(line, sizeof line, p)) {
    if (strncmp(line, "WIN ", 4) != 0) continue;
    if (!strstr(line, " act=1 ")) continue;
    if (strstr(line, "app_id=nuxel-pwa-host")) continue;
    if (strstr(line, "title=Nuxel")) continue;
    if (app_id && app_n) {
      const char *a = strstr(line, "app_id=");
      if (a) {
        a += 7;
        size_t i = 0;
        while (*a && *a != ' ' && *a != '\n' && i + 1 < app_n) app_id[i++] = *a++;
        app_id[i] = 0;
      }
    }
    found = 1;
    break;
  }
  pclose(p);
  return found;
}

static int preloading_active(void) {
  char b[512];
  if (!read_text(PRELOAD_OVERLAY, b, sizeof b)) return 0;
  return strstr(b, "\"state\": \"starting\"") ||
         strstr(b, "\"state\":\"starting\"") ||
         strstr(b, "\"state\": \"covered\"") ||
         strstr(b, "\"state\":\"covered\"");
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


/* PWNAGE-42000: real, high-contrast top-bar glyphs.  The old overlay rendered
 * only text; on a dark strip the Wi-Fi/location state could read as a dim grey
 * smear.  These are explicit Cairo shapes, not theme-dependent text. */
static int location_enabled(void) {
  FILE *f = fopen(LOCATION_POLICY, "r");
  if (!f) return 0;
  char b[4096];
  size_t n = fread(b, 1, sizeof b - 1, f);
  fclose(f);
  b[n] = 0;
  char *p = strstr(b, "\"enabled\"");
  if (!p) return 0;
  p += 9;
  while (*p == ' ' || *p == '\t' || *p == '\n' || *p == '\r') p++;
  if (*p != ':') return 0;
  p++;
  while (*p == ' ' || *p == '\t' || *p == '\n' || *p == '\r') p++;
  return strncmp(p, "true", 4) == 0;
}

static void draw_wifi(cairo_t *cr, double cx, double cy, int up) {
  cairo_set_line_width(cr, 2.0);
  cairo_set_line_cap(cr, CAIRO_LINE_CAP_ROUND);
  if (up) cairo_set_source_rgba(cr, 0.49, 0.89, 0.60, 1.0);
  else    cairo_set_source_rgba(cr, 0.78, 0.85, 0.94, 0.90);
  cairo_arc(cr, cx, cy + 4.0, 7.6, M_PI * 1.16, M_PI * 1.84);
  cairo_stroke(cr);
  cairo_set_line_width(cr, 1.9);
  cairo_arc(cr, cx, cy + 4.0, 4.3, M_PI * 1.16, M_PI * 1.84);
  cairo_stroke(cr);
  cairo_arc(cr, cx, cy + 3.2, 1.7, 0, 2 * M_PI);
  cairo_fill(cr);
}

static void draw_location(cairo_t *cr, double cx, double cy) {
  cairo_set_source_rgba(cr, 0.41, 0.72, 1.0, 1.0);
  cairo_set_line_width(cr, 1.5);
  cairo_arc(cr, cx, cy, 7.2, 0, 2 * M_PI);
  cairo_stroke(cr);
  cairo_arc(cr, cx, cy, 4.0, 0, 2 * M_PI);
  cairo_fill(cr);
}

static void draw_bolt(cairo_t *cr, double x, double y, double w, double h) {
  cairo_move_to(cr, x + w * 0.62, y);
  cairo_line_to(cr, x + w * 0.20, y + h * 0.56);
  cairo_line_to(cr, x + w * 0.46, y + h * 0.56);
  cairo_line_to(cr, x + w * 0.36, y + h);
  cairo_line_to(cr, x + w * 0.82, y + h * 0.42);
  cairo_line_to(cr, x + w * 0.54, y + h * 0.42);
  cairo_line_to(cr, x + w * 0.72, y);
  cairo_close_path(cr);
  cairo_fill(cr);
}

static void draw_battery(cairo_t *cr, double x, double cy, int level, int chg) {
  const double w = 27.0, h = 13.0;
  double top = cy - h / 2.0;
  cairo_set_source_rgba(cr, 0.96, 0.98, 1.0, 1.0);
  cairo_set_line_width(cr, 1.6);
  cairo_rectangle(cr, x, top, w, h);
  cairo_stroke(cr);
  cairo_rectangle(cr, x + w + 1.0, top + 4.0, 2.8, 5.0);
  cairo_fill(cr);
  double pct = (level < 0 ? 0 : (level > 100 ? 100 : level)) / 100.0;
  if (pct > 0) {
    cairo_set_source_rgba(cr, 0.45, 0.88, 0.60, 1.0);
    cairo_rectangle(cr, x + 2.0, top + 2.0, (w - 4.0) * pct, h - 4.0);
    cairo_fill(cr);
  }
  if (chg) {
    /* Three yellow zaps, matching the Home DOM battery indicator. */
    cairo_set_source_rgba(cr, 1.0, 0.84, 0.18, 1.0);
    draw_bolt(cr, x + 1.8, top + 1.2, 7.0, h - 2.4);
    draw_bolt(cr, x + 9.9, top + 1.2, 7.0, h - 2.4);
    draw_bolt(cr, x + 18.0, top + 1.2, 7.0, h - 2.4);
  }
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

  if (bar_level == 0) {
    /* Hidden state: transparent edge band with a small grabber.  No top bar
     * pixels and no permanently visible input surface. */
    cairo_set_operator(cr, CAIRO_OPERATOR_CLEAR);
    cairo_paint(cr);
    cairo_set_operator(cr, CAIRO_OPERATOR_OVER);
    double gw = is_landscape() ? 64.0 : 46.0, gh = 3.0;
    cairo_set_source_rgba(cr, 1.0, 1.0, 1.0, 0.38);
    cairo_rectangle(cr, (width - gw) / 2.0, 3.0, gw, gh);
    cairo_fill(cr);
  } else {
    /* PWNAGE-96000: exact Home DOM design token
     * (status-bar.css: rgba(26, 26, 46, 0.95)), not the older #0b121f. */
    cairo_set_source_rgba(cr, 26.0 / 255.0, 26.0 / 255.0, 46.0 / 255.0, 0.95);
    cairo_paint(cr);

    char timebuf[32];
    if (!model_get("time", timebuf, sizeof timebuf)) {
      time_t t = time(NULL); struct tm tm; localtime_r(&t, &tm);
      strftime(timebuf, sizeof timebuf, "%H:%M", &tm);
    }
    int lvl = battery_level();
    int chg = battery_charging();
    int loc_on = location_enabled();
    int wifi_on = wifi_up();
    char mval[64];
    if (model_get("battery", mval, sizeof mval)) lvl = atoi(mval);
    if (model_get("charging", mval, sizeof mval)) chg = !strcmp(mval, "true");
    if (model_get("wifi_on", mval, sizeof mval)) wifi_on = !strcmp(mval, "true");
    if (model_get("location", mval, sizeof mval)) loc_on = !strcmp(mval, "true");
    char pctbuf[16];
    snprintf(pctbuf, sizeof pctbuf, "%d%%", lvl >= 0 ? lvl : 0);

    PangoLayout *layout = pango_cairo_create_layout(cr);
    PangoFontDescription *desc = pango_font_description_from_string("Nuxel Sans 13");
    pango_font_description_set_weight(desc, PANGO_WEIGHT_SEMIBOLD);
    pango_layout_set_font_description(layout, desc);
    cairo_set_source_rgb(cr, 1.0, 1.0, 1.0);

    pango_layout_set_text(layout, timebuf, -1);
    int tw = 0, th = 0; pango_layout_get_pixel_size(layout, &tw, &th);
    cairo_move_to(cr, 16, (BAR_HEIGHT - th) / 2.0 - 1);
    pango_cairo_show_layout(cr, layout);

    PangoFontDescription *pct_desc = pango_font_description_from_string("Nuxel Sans 12");
    pango_layout_set_font_description(layout, pct_desc);
    pango_layout_set_text(layout, pctbuf, -1);
    pango_layout_get_pixel_size(layout, &tw, &th);
    double pct_x = width - tw - 16.0;
    cairo_move_to(cr, pct_x, (BAR_HEIGHT - th) / 2.0 - 1);
    pango_cairo_show_layout(cr, layout);
    pango_font_description_free(pct_desc);
    pango_font_description_free(desc);
    double battery_x = pct_x - 34.0;
    draw_battery(cr, battery_x, BAR_HEIGHT / 2.0, lvl, chg);
    double wifi_x = battery_x - 22.0;
    draw_wifi(cr, wifi_x, BAR_HEIGHT / 2.0, wifi_on);
    double loc_x = wifi_x - 20.0;
    if (loc_on) draw_location(cr, loc_x, BAR_HEIGHT / 2.0);

    /* Match status-bar.css border-bottom: 1px rgba(255,255,255,0.03). */
    cairo_set_source_rgba(cr, 1.0, 1.0, 1.0, 0.03);
    cairo_rectangle(cr, 0, BAR_HEIGHT - 1.0, width, 1.0);
    cairo_fill(cr);

    /* The little grabber is the only decorative element; it makes the
     * upward-dismiss gesture discoverable without stealing app pixels. */
    cairo_set_source_rgba(cr, 1.0, 1.0, 1.0, 0.30);
    cairo_rectangle(cr, (width - 40.0) / 2.0, BAR_HEIGHT - 3.0, 40.0, 2.0);
    cairo_fill(cr);

    if (bar_level >= 2) {
      char wifi[48] = "unknown", bt[48] = "unknown", sound[32] = "unknown";
      char mobile[48] = "unknown", notif[32] = "0", usb[48] = "";
      char loc[32] = "off";
      model_get("wifi", wifi, sizeof wifi);
      model_get("bluetooth", bt, sizeof bt);
      model_get("sound", sound, sizeof sound);
      model_get("mobile", mobile, sizeof mobile);
      model_get("notifications", notif, sizeof notif);
      model_get("usb", usb, sizeof usb);
      model_get("location", loc, sizeof loc);
      if (!strcmp(bt, "true")) snprintf(bt, sizeof bt, "on");
      else if (!strcmp(bt, "false")) snprintf(bt, sizeof bt, "off");

      PangoFontDescription *small = pango_font_description_from_string("Nuxel Sans 12");
      PangoFontDescription *head = pango_font_description_from_string("Nuxel Sans Bold 10");
      double y = BAR_HEIGHT + 9.0;

      pango_layout_set_font_description(layout, head);
      cairo_set_source_rgba(cr, 0.49, 0.72, 0.98, 1.0);
      pango_layout_set_text(layout, bar_level >= 3 ? "EXTENDED QUICK SETTINGS" : "QUICK SETTINGS", -1);
      pango_layout_get_pixel_size(layout, &tw, &th);
      cairo_move_to(cr, 14, y);
      pango_cairo_show_layout(cr, layout);
      y += th + 7.0;

      pango_layout_set_font_description(layout, small);
      cairo_set_source_rgb(cr, 1.0, 1.0, 1.0);
      const char *rows[8];
      int nrows = 0;
      char rowbuf[8][160];
      snprintf(rowbuf[nrows], sizeof rowbuf[nrows], "Wi-Fi: %s", wifi);
      rows[nrows] = rowbuf[nrows]; nrows++;
      snprintf(rowbuf[nrows], sizeof rowbuf[nrows], "Battery: %d%%%s",
               lvl >= 0 ? lvl : 0, chg ? " (charging)" : "");
      rows[nrows] = rowbuf[nrows]; nrows++;
      snprintf(rowbuf[nrows], sizeof rowbuf[nrows], "Bluetooth: %s", bt);
      rows[nrows] = rowbuf[nrows]; nrows++;
      snprintf(rowbuf[nrows], sizeof rowbuf[nrows], "Sound: %s", sound);
      rows[nrows] = rowbuf[nrows]; nrows++;
      snprintf(rowbuf[nrows], sizeof rowbuf[nrows], "Unread notifications: %s", notif);
      rows[nrows] = rowbuf[nrows]; nrows++;
      if (bar_level >= 3) {
        snprintf(rowbuf[nrows], sizeof rowbuf[nrows], "Mobile: %s", mobile);
        rows[nrows] = rowbuf[nrows]; nrows++;
        snprintf(rowbuf[nrows], sizeof rowbuf[nrows], "Location: %s", loc);
        rows[nrows] = rowbuf[nrows]; nrows++;
        snprintf(rowbuf[nrows], sizeof rowbuf[nrows], "USB: %s", usb[0] ? usb : "inactive");
        rows[nrows] = rowbuf[nrows]; nrows++;
      }
      for (int i = 0; i < nrows; i++) {
        if (y > height - 16) break;
        pango_layout_set_text(layout, rows[i], -1);
        pango_layout_get_pixel_size(layout, &tw, &th);
        cairo_move_to(cr, 16, y);
        pango_cairo_show_layout(cr, layout);
        y += th + 9.0;
      }
      if (bar_level >= 3) {
        pango_layout_set_font_description(layout, head);
        cairo_set_source_rgba(cr, 0.72, 0.82, 0.95, 0.9);
        pango_layout_set_text(layout, "Swipe up once to close the entire panel", -1);
        pango_layout_get_pixel_size(layout, &tw, &th);
        double yy = height - th - 12.0;
        if (yy > y) { cairo_move_to(cr, 16, yy); pango_cairo_show_layout(cr, layout); }
      }
      pango_font_description_free(head);
      pango_font_description_free(small);
    }

    g_object_unref(layout);
  }

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
  wl_buffer_destroy(buf);
  close(fd);
}

static const struct zwlr_layer_surface_v1_listener layer_listener;

static void bar_hide(void) {
  if (!layer_surface) return;
  zwlr_layer_surface_v1_destroy(layer_surface);
  layer_surface = NULL;
  if (surface) {
    wl_surface_attach(surface, NULL, 0, 0);
    wl_surface_commit(surface);
    wl_surface_destroy(surface);
    surface = NULL;
  }
  configured = 0;
  bar_level = 0;
  strip_mode = 1;
  reveal_deadline = 0;
  audit("STATUSBAR_HIDDEN reason=lock_or_home");
  publish_state(0, "lock_home_or_preload", "", session_locked(), NULL);
}

static void bar_create(void) {
  if (layer_surface || !compositor || !layer_shell || !output) return;
  if (!surface) surface = wl_compositor_create_surface(compositor);
  if (!surface) return;
  int32_t h = bar_height_for_level(bar_level);
  layer_surface = zwlr_layer_shell_v1_get_layer_surface(
      layer_shell, surface, output, ZWLR_LAYER_SHELL_V1_LAYER_OVERLAY, "nuxel-statusbar");
  zwlr_layer_surface_v1_set_anchor(layer_surface,
      ZWLR_LAYER_SURFACE_V1_ANCHOR_TOP | ZWLR_LAYER_SURFACE_V1_ANCHOR_LEFT |
      ZWLR_LAYER_SURFACE_V1_ANCHOR_RIGHT);
  zwlr_layer_surface_v1_set_size(layer_surface, 0, (uint32_t)h);
  /* PWNAGE-94000: never reserve layout space.  The app stays exactly as it
   * was; the panel is a temporary overlay and the Home CSS owns the only
   * desktop inset calculation.  This removes the double-inset geometry class. */
  zwlr_layer_surface_v1_set_exclusive_zone(layer_surface, 0);
  zwlr_layer_surface_v1_set_keyboard_interactivity(layer_surface,
      ZWLR_LAYER_SURFACE_V1_KEYBOARD_INTERACTIVITY_NONE);
  height = h;
  zwlr_layer_surface_v1_add_listener(layer_surface, &layer_listener, NULL);
  wl_surface_commit(surface);
  configured = 0;
}

static void bar_show(void) {
  /* Default native-foreground state is the hidden strip.  The panel is only
   * mapped after a real downward gesture. */
  if (bar_level <= 0) { bar_strip(); return; }
  bar_create();
  audit("STATUSBAR_SHOWN level=%d", bar_level);
  publish_state(1, "native_foreground", "", 0, NULL);
}

static void bar_strip(void) {
  if (layer_surface) bar_hide();
  bar_level = 0;
  strip_mode = 1;
  reveal_deadline = 0;
  bar_create();
  audit("STATUSBAR_STRIP native_foreground");
  publish_state(0, "native_strip", "", 0, NULL);
}

static void bar_set_level(int level) {
  if (level < 0) level = 0;
  if (level > 3) level = 3;
  if (level == bar_level && layer_surface) {
    reveal_deadline = level == 1 ? now_ms() + BAR_AUTOHIDE_MS : 0;
    render();
    publish_state(1, "native_level", "", 0, NULL);
    return;
  }
  if (layer_surface) bar_hide();
  bar_level = level;
  strip_mode = level == 0 ? 1 : 0;
  reveal_deadline = level == 1 ? now_ms() + BAR_AUTOHIDE_MS : 0;
  bar_create();
  audit("STATUSBAR_LEVEL %d landscape=%d height=%d", bar_level, is_landscape(), height);
  publish_state(level > 0, level ? "native_level" : "native_strip", "", 0, NULL);
}

/* PWNAGE-90000: the compact bar's SECOND downward pull must open the real
 * expanded Quick Settings through the launcher's authoritative controller.
 * The statusbar never invents its own shade state. */
static void send_host_action(const char *action) {
  int fd = open(HOST_FIFO, O_WRONLY | O_NONBLOCK);
  if (fd < 0) { audit("STATUSBAR_HOST_FIFO_OPEN_FAIL action=%s errno=%d", action, errno); return; }
  dprintf(fd, "action %s\n", action);
  close(fd);
  audit("STATUSBAR_HOST_ACTION %s", action);
}


static int64_t now_ms(void) {
  struct timespec ts;
  clock_gettime(CLOCK_MONOTONIC, &ts);
  return (int64_t)ts.tv_sec * 1000 + ts.tv_nsec / 1000000;
}

static void layer_configure(void *d, struct zwlr_layer_surface_v1 *ls,
                            uint32_t serial, uint32_t w, uint32_t h) {
  (void)d;
  if ((int32_t)w > 0) width = (int32_t)w;
  height = bar_height_for_level(bar_level);
  zwlr_layer_surface_v1_ack_configure(ls, serial);
  configured = 1;
  render();
}
static void layer_closed(void *d, struct zwlr_layer_surface_v1 *ls) {
  (void)d;
  if (ls == layer_surface) {
    layer_surface = NULL;
    configured = 0;
    if (surface) { wl_surface_destroy(surface); surface = NULL; }
  }
  audit("LAYER_CLOSED");
  publish_state(0, "layer-closed", "", session_locked(), "layer-closed");
}
static const struct zwlr_layer_surface_v1_listener layer_listener = {
  .configure = layer_configure, .closed = layer_closed,
};

/* ---- top gesture strip touch -------------------------------------------- */
static void touch_down_cb(void *d, struct wl_touch *t, uint32_t serial,
                          uint32_t time, struct wl_surface *surf, int32_t id,
                          wl_fixed_t x, wl_fixed_t y) {
  (void)d; (void)t; (void)serial; (void)time; (void)surf; (void)id; (void)x;
  if (!layer_surface) return;
  touch_down = 1;
  down_y = last_y = wl_fixed_to_int(y);
}
static void touch_motion_cb(void *d, struct wl_touch *t, uint32_t time, int32_t id,
                            wl_fixed_t x, wl_fixed_t y) {
  (void)d; (void)t; (void)time; (void)id; (void)x;
  last_y = wl_fixed_to_int(y);
  if (!touch_down) return;
  /* Deliberate landscape threshold: a 16 px motion is enough in either
   * orientation, but a panel only advances ONE level per physical swipe. */
  if ((last_y - down_y) >= BAR_REVEAL_DISTANCE) {
    touch_down = 0;
    if (bar_level < 3) bar_set_level(bar_level + 1);
  } else if ((down_y - last_y) >= BAR_REVEAL_DISTANCE) {
    /* Strict requirement: one upward swipe closes EVERY level atomically. */
    touch_down = 0;
    send_host_action("quick-settings-close");
    bar_strip();
  }
}
static void touch_up_cb(void *d, struct wl_touch *t, uint32_t serial,
                        uint32_t time, int32_t id) {
  (void)d; (void)t; (void)serial; (void)time; (void)id;
  touch_down = 0;
}
static void touch_cancel_cb(void *d, struct wl_touch *t) {
  (void)d; (void)t; touch_down = 0;
}
static void touch_frame_cb(void *d, struct wl_touch *t) { (void)d; (void)t; }
static const struct wl_touch_listener touch_listener = {
  .down = touch_down_cb, .up = touch_up_cb, .motion = touch_motion_cb,
  .frame = touch_frame_cb, .cancel = touch_cancel_cb,
};
static void seat_caps(void *d, struct wl_seat *s, uint32_t caps) {
  (void)d;
  if ((caps & WL_SEAT_CAPABILITY_TOUCH) && !touch) {
    touch = wl_seat_get_touch(seat);
    wl_touch_add_listener(touch, &touch_listener, NULL);
  }
}
static void seat_name(void *d, struct wl_seat *s, const char *name) {
  (void)d; (void)s; (void)name;
}
static const struct wl_seat_listener seat_listener = {
  .capabilities = seat_caps, .name = seat_name,
};

static void output_mode(void *d, struct wl_output *o, uint32_t flags,
                        int32_t w, int32_t h, int32_t refresh) {
  (void)d; (void)o; (void)flags; (void)refresh;
  if (w > 0 && h > 0) { out_w = w; out_h = h; }
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
  else if (!strcmp(iface, wl_seat_interface.name) && !seat)
    seat = wl_registry_bind(r, name, &wl_seat_interface, 5);
}
static void reg_remove(void *d, struct wl_registry *r, uint32_t name) { (void)d;(void)r;(void)name; }
static const struct wl_registry_listener reg_listener = { reg_global, reg_remove };

static void process_cmd(const char *q) {
  if (!q || !*q) return;
  if (!strncmp(q, "level ", 6)) {
    int n = atoi(q + 6);
    audit("STATUSBAR_CMD level=%d", n);
    bar_set_level(n);
    return;
  }
  if (!strcmp(q, "strip") || !strcmp(q, "hide")) { bar_set_level(0); return; }
  if (!strcmp(q, "standard")) { bar_set_level(1); return; }
  if (!strcmp(q, "expanded")) { bar_set_level(2); return; }
  if (!strcmp(q, "extended")) { bar_set_level(3); return; }
  if (!strcmp(q, "status")) { publish_state(bar_level > 0, "status", "", 0, NULL); return; }
}

int main(void) {
  unlink(LOG_FILE);
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
  if (seat) wl_seat_add_listener(seat, &seat_listener, NULL);
  wl_display_roundtrip(display);

  /* Bounded operator/test control channel.  It only changes the panel LEVEL;
   * it cannot inject input into any application and it is not a second UI
   * state owner (the canonical model remains /run/nuxel/statusbar-model.json). */
  unlink(CMD_FIFO);
  if (mkfifo(CMD_FIFO, 0600) == 0) {
    /* PWNAGE-94000: open the control FIFO read/write.  A read-only FIFO with
     * no writer is permanently readable with POLLHUP, which turned the main
     * loop into a 100%-CPU busy spin after the last test writer exited. */
    cmd_fd = open(CMD_FIFO, O_RDWR | O_NONBLOCK | O_CLOEXEC);
  }
  audit("STATUSBAR_CMD_FIFO %s", cmd_fd >= 0 ? "ready" : "absent");

  /* The overlay owns presentation only while ALL of these are true:
     - the session is unlocked (never over the lockscreen; the DOM bar owns
       that surface), and
     - a non-Home Wayland toplevel is activated (never double the Home bar). */
  int locked = session_locked();
  char fg[256] = "";
  int shown = 0;
  if (!locked && !preloading_active() && native_foreground(fg, sizeof fg)) {
    bar_strip();
    shown = 1;
    wl_display_roundtrip(display);
    audit("STATUSBAR_READY width=%d height=%d scale=%d", width, height, scale);
  } else {
    audit("STATUSBAR_START_HIDDEN locked=%d preload=%d", locked, preloading_active());
    publish_state(0, locked ? "locked" : preloading_active() ? "preload" : "home",
                  fg, locked, NULL);
  }
  time_t last = 0;
  for (;;) {
    while (wl_display_prepare_read(display) != 0) {
      if (wl_display_dispatch_pending(display) < 0) return 0;
    }
    wl_display_flush(display);
    struct pollfd pf[2] = {
      { .fd = wl_display_get_fd(display), .events = POLLIN, .revents = 0 },
      { .fd = cmd_fd, .events = POLLIN, .revents = 0 },
    };
    int maxfd = (cmd_fd >= 0) ? 2 : 1;
    int pr = poll(pf, (nfds_t)maxfd, 250);
    if (pr < 0) { wl_display_cancel_read(display); if (errno == EINTR) continue; return 0; }
    if (pr == 0) {
      wl_display_cancel_read(display);
      int now_locked = session_locked();
      int want = 0;
      char fg[256] = "";
      if (shown && !layer_surface) shown = 0;   /* recreate after LAYER_CLOSED */
      if (!now_locked && !preloading_active()) {
        /* The persistent watcher is the normal source; the bounded popen
           fallback is rate-limited to once every 2 s. */
        static time_t fg_checked = 0;
        static int fg_cached = 0;
        static char fg_id[256] = "";
        time_t now = time(NULL);
        if (now - fg_checked >= 2) {
          fg_cached = native_foreground(fg_id, sizeof fg_id);
          fg_checked = now;
        }
        want = fg_cached;
        snprintf(fg, sizeof fg, "%s", fg_id);
      }
      if (now_locked != locked || want != shown) {
        locked = now_locked;
        shown = want;
        if (shown) bar_show(); else bar_hide();
        audit("STATUSBAR_TRANSITION locked=%d shown=%d fg=%s", locked, shown, fg);
        publish_state(shown, shown ? "native_foreground" :
                      locked ? "locked" : preloading_active() ? "preload" : "home",
                      fg, locked, NULL);
      }
      if (shown && bar_level == 1 && reveal_deadline && now_ms() >= reveal_deadline) {
        bar_strip();
        audit("STATUSBAR_GESTURE_AUTOHIDE");
      }
      time_t now = time(NULL);
      if (shown && now - last >= 10) { last = now; if (bar_level > 0) render(); }
      continue;
    }
    if (pf[0].revents & POLLIN) {
      if (wl_display_read_events(display) < 0) return 0;
      if (wl_display_dispatch_pending(display) < 0) return 0;
    } else {
      wl_display_cancel_read(display);
    }
    if (cmd_fd >= 0 && (pf[1].revents & (POLLIN | POLLHUP | POLLERR))) {
      char buf[512];
      ssize_t n = read(cmd_fd, buf, sizeof buf - 1);
      if (n > 0) {
        buf[n] = 0;
        for (char *q = buf; q && *q; ) {
          char *nl = strchr(q, '\n');
          if (nl) *nl = 0;
          process_cmd(q);
          q = nl ? nl + 1 : NULL;
        }
      }
    }
  }
}
