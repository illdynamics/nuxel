/* nuxel-text-input-probe — a tiny Wayland client that maps an xdg_toplevel and
 * enables zwp_text_input_v3, so the native OSK (Stevia) shows its keyboard.
 * Diagnostic only: used to prove Stevia binds the input-method path and to
 * observe where its keyboard layer lands relative to the native nav dock. */
#define _GNU_SOURCE
#include <errno.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <wayland-client.h>
#include "text-input-unstable-v3-client-protocol.h"
#include "xdg-shell-client-protocol.h"

static struct wl_compositor *compositor;
static struct xdg_wm_base *wm_base;
static struct zwp_text_input_manager_v3 *tim;
static struct wl_seat *seat;
static struct wl_surface *surface;
static struct xdg_surface *xdg_surface;
static struct xdg_toplevel *toplevel;
static struct zwp_text_input_v3 *ti;
static int configured = 0;
static int seconds = 10;

static void wm_ping(void *d, struct xdg_wm_base *w, uint32_t serial) {
  (void)d; xdg_wm_base_pong(w, serial);
}
static const struct xdg_wm_base_listener wm_listener = { .ping = wm_ping };

static void xdg_configure(void *d, struct xdg_surface *s, uint32_t serial) {
  (void)d; xdg_surface_ack_configure(s, serial);
  configured = 1;
  wl_surface_commit(surface);   /* map (or re-map) so phoc can focus it */
}
static const struct xdg_surface_listener xdg_listener = { .configure = xdg_configure };

static void tl_configure(void *d, struct xdg_toplevel *t, int32_t w, int32_t h, struct wl_array *states) {
  (void)d; (void)t; (void)w; (void)h; (void)states;
}
static void tl_close(void *d, struct xdg_toplevel *t) { (void)d; (void)t; }
static const struct xdg_toplevel_listener tl_listener = { .configure = tl_configure, .close = tl_close };

static void ti_enter(void *d, struct zwp_text_input_v3 *t, struct wl_surface *s) {
  (void)d; (void)t; (void)s; fprintf(stderr, "TEXT_INPUT_ENTER\n");
}
static void ti_leave(void *d, struct zwp_text_input_v3 *t, struct wl_surface *s) {
  (void)d; (void)t; (void)s; fprintf(stderr, "TEXT_INPUT_LEAVE\n");
}
static void ti_preedit(void *d, struct zwp_text_input_v3 *t, const char *text, int32_t a, int32_t b) {
  (void)d; (void)t; (void)text; (void)a; (void)b;
}
static void ti_commit(void *d, struct zwp_text_input_v3 *t, const char *text) {
  (void)d; (void)t; fprintf(stderr, "TEXT_INPUT_COMMIT '%s'\n", text);
}
static void ti_delete(void *d, struct zwp_text_input_v3 *t, uint32_t b, uint32_t l) {
  (void)d; (void)t; (void)b; (void)l;
}
static void ti_done(void *d, struct zwp_text_input_v3 *t, uint32_t serial) {
  (void)d; (void)t; (void)serial;
}
static const struct zwp_text_input_v3_listener ti_listener = {
  .enter = ti_enter, .leave = ti_leave, .commit_string = ti_commit,
  .delete_surrounding_text = ti_delete, .preedit_string = ti_preedit, .done = ti_done,
};

static void reg_global(void *d, struct wl_registry *r, uint32_t name, const char *iface, uint32_t ver) {
  (void)d;
  if (!strcmp(iface, wl_compositor_interface.name))
    compositor = wl_registry_bind(r, name, &wl_compositor_interface, 4);
  else if (!strcmp(iface, xdg_wm_base_interface.name))
    wm_base = wl_registry_bind(r, name, &xdg_wm_base_interface, 1);
  else if (!strcmp(iface, zwp_text_input_manager_v3_interface.name))
    tim = wl_registry_bind(r, name, &zwp_text_input_manager_v3_interface, 1);
  else if (!strcmp(iface, wl_seat_interface.name) && !seat)
    seat = wl_registry_bind(r, name, &wl_seat_interface, 1);
}
static void kb_keymap(void *d, struct wl_keyboard *k, uint32_t f, int fd, uint32_t sz) { (void)d;(void)k;(void)f;(void)fd;(void)sz; }
static void kb_enter(void *d, struct wl_keyboard *k, uint32_t s, struct wl_surface *surf, struct wl_array *keys) {
  (void)d;(void)k;(void)s;(void)surf;(void)keys; fprintf(stderr, "KEYBOARD_ENTER\n");
}
static void kb_leave(void *d, struct wl_keyboard *k, uint32_t s, struct wl_surface *surf) {
  (void)d;(void)k;(void)s;(void)surf; fprintf(stderr, "KEYBOARD_LEAVE\n");
}
static void kb_key(void *d, struct wl_keyboard *k, uint32_t s, uint32_t t, uint32_t key, uint32_t st) { (void)d;(void)k;(void)s;(void)t;(void)key;(void)st; }
static void kb_mod(void *d, struct wl_keyboard *k, uint32_t s, uint32_t md, uint32_t ml, uint32_t mo, uint32_t mg) { (void)d;(void)k;(void)s;(void)md;(void)ml;(void)mo;(void)mg; }
static void kb_repeat(void *d, struct wl_keyboard *k, int32_t r, int32_t del) { (void)d;(void)k;(void)r;(void)del; }
static const struct wl_keyboard_listener kb_listener = { .keymap=kb_keymap,.enter=kb_enter,.leave=kb_leave,.key=kb_key,.modifiers=kb_mod,.repeat_info=kb_repeat };
static struct wl_keyboard *keyboard;

static void seat_caps(void *d, struct wl_seat *s, uint32_t caps) {
  (void)d;(void)s;
  if ((caps & WL_SEAT_CAPABILITY_KEYBOARD) && !keyboard) {
    keyboard = wl_seat_get_keyboard(seat);
    wl_keyboard_add_listener(keyboard, &kb_listener, NULL);
  }
}
static void seat_name2(void *d, struct wl_seat *s, const char *n) { (void)d;(void)s;(void)n; }
static const struct wl_seat_listener seat_listener = { .capabilities = seat_caps, .name = seat_name2 };

static void reg_remove(void *d, struct wl_registry *r, uint32_t name) { (void)d; (void)r; (void)name; }
static const struct wl_registry_listener reg_listener = { reg_global, reg_remove };

int main(int argc, char **argv) {
  if (argc > 1) seconds = atoi(argv[1]);
  struct wl_display *display = wl_display_connect(NULL);
  if (!display) { fprintf(stderr, "DISPLAY_FAIL\n"); return 1; }
  struct wl_registry *reg = wl_display_get_registry(display);
  wl_registry_add_listener(reg, &reg_listener, NULL);
  wl_display_roundtrip(display);
  if (!compositor || !wm_base || !tim || !seat) { fprintf(stderr, "GLOBALS_MISSING\n"); return 2; }
  wl_seat_add_listener(seat, &seat_listener, NULL);
  xdg_wm_base_add_listener(wm_base, &wm_listener, NULL);

  surface = wl_compositor_create_surface(compositor);
  xdg_surface = xdg_wm_base_get_xdg_surface(wm_base, surface);
  xdg_surface_add_listener(xdg_surface, &xdg_listener, NULL);
  toplevel = xdg_surface_get_toplevel(xdg_surface);
  xdg_toplevel_add_listener(toplevel, &tl_listener, NULL);
  xdg_toplevel_set_title(toplevel, "nuxel-text-input-probe");
  xdg_toplevel_set_min_size(toplevel, 200, 100);
  wl_surface_commit(surface);
  wl_display_roundtrip(display);   /* configure -> ack -> map */
  wl_display_roundtrip(display);   /* keyboard focus settles */

  ti = zwp_text_input_manager_v3_get_text_input(tim, seat);
  zwp_text_input_v3_add_listener(ti, &ti_listener, NULL);
  zwp_text_input_v3_enable(ti);
  zwp_text_input_v3_set_cursor_rectangle(ti, 0, 0, 10, 40);
  zwp_text_input_v3_commit(ti);
  wl_display_roundtrip(display);   /* activate -> enter */
  fprintf(stderr, "PROBE_READY seconds=%d configured=%d\n", seconds, configured);

  /* spin until timeout; re-assert text-input every iteration so a focus that
     arrives late still activates */
  for (int i = 0; i < seconds * 10; i++) {
    if (i % 5 == 0) { zwp_text_input_v3_enable(ti); zwp_text_input_v3_commit(ti); }
    wl_display_roundtrip(display);
    usleep(100000);
  }
  fprintf(stderr, "PROBE_DONE\n");
  return 0;
}
