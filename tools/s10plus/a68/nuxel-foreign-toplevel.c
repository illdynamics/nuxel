/* nuxel-foreign-toplevel — trusted shell-side window controller for Nuxel (A68).

 * Uses zwlr_foreign_toplevel_manager_v1 (phoc/wlroots) to enumerate toplevels
 * and route compositor-level navigation with the verbs phoc 0.54 actually
 * wires: request_activate, request_maximize, request_fullscreen, request_close.
 * phoc 0.54 does NOT wire request_minimize, so `set_minimized` is a silent
 * no-op on this device (measured A66: a "minimized" native window stays
 * mapped, min=0).  Home must therefore take native apps OUT of fullscreen /
 * maximize and then activate the Home toplevel, instead of pretending
 * set_minimized backgrounds them.

 * Modes:
 *   list                  print toplevels (title, app_id, max/min/act/fs)
 *   home                  background every non-Home toplevel (unset fs/max) and
 *                         raise/activate Home
 *   activate [substr]     activate the first non-Home toplevel whose app_id
 *                         contains substr (no substr: first non-Home)
 *   close-foreground      close the activated non-Home toplevel (long Back)
 *
 * Never kills a client except through the compositor's own `close` verb.
 */
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <wayland-client.h>
#include "wlr-foreign-toplevel-unstable-v1-client-protocol.h"

struct toplevel {
    struct zwlr_foreign_toplevel_handle_v1 *handle;
    char title[256];
    char app_id[256];
    uint32_t maximized, minimized, activated, fullscreen;
    struct toplevel *next;
};

static struct toplevel *tops;
static struct wl_seat *seat;

static struct toplevel *find_top(struct zwlr_foreign_toplevel_handle_v1 *h) {
    for (struct toplevel *t = tops; t; t = t->next)
        if (t->handle == h) return t;
    return NULL;
}

static void on_title(void *d, struct zwlr_foreign_toplevel_handle_v1 *h, const char *title) {
    (void)d; struct toplevel *t = find_top(h); if (t) snprintf(t->title, sizeof t->title, "%s", title ? title : "");
}
static void on_app_id(void *d, struct zwlr_foreign_toplevel_handle_v1 *h, const char *app_id) {
    (void)d; struct toplevel *t = find_top(h); if (t) snprintf(t->app_id, sizeof t->app_id, "%s", app_id ? app_id : "");
}
static void on_output_enter(void *d, struct zwlr_foreign_toplevel_handle_v1 *h, struct wl_output *o) {
    (void)d;(void)h;(void)o;
}
static void on_output_leave(void *d, struct zwlr_foreign_toplevel_handle_v1 *h, struct wl_output *o) {
    (void)d;(void)h;(void)o;
}
static void on_state(void *d, struct zwlr_foreign_toplevel_handle_v1 *h, struct wl_array *a) {
    (void)d; struct toplevel *t = find_top(h); if (!t) return;
    t->maximized = t->minimized = t->activated = t->fullscreen = 0;
    uint32_t *p = a->data; size_t n = a->size / sizeof(uint32_t);
    for (size_t i = 0; i < n; i++) {
        switch (p[i]) {
        case ZWLR_FOREIGN_TOPLEVEL_HANDLE_V1_STATE_MAXIMIZED: t->maximized = 1; break;
        case ZWLR_FOREIGN_TOPLEVEL_HANDLE_V1_STATE_MINIMIZED: t->minimized = 1; break;
        case ZWLR_FOREIGN_TOPLEVEL_HANDLE_V1_STATE_ACTIVATED: t->activated = 1; break;
        case ZWLR_FOREIGN_TOPLEVEL_HANDLE_V1_STATE_FULLSCREEN: t->fullscreen = 1; break;
        default: break;
        }
    }
}
static void on_done(void *d, struct zwlr_foreign_toplevel_handle_v1 *h) { (void)d;(void)h; }
static void on_closed(void *d, struct zwlr_foreign_toplevel_handle_v1 *h) {
    (void)d; struct toplevel **pp = &tops;
    while (*pp) {
        if ((*pp)->handle == h) { struct toplevel *t = *pp; *pp = t->next; free(t); return; }
        pp = &(*pp)->next;
    }
}
static void on_parent(void *d, struct zwlr_foreign_toplevel_handle_v1 *h, struct zwlr_foreign_toplevel_handle_v1 *p) {
    (void)d;(void)h;(void)p;
}
static const struct zwlr_foreign_toplevel_handle_v1_listener handle_listener = {
    .title = on_title, .app_id = on_app_id,
    .output_enter = on_output_enter, .output_leave = on_output_leave,
    .state = on_state, .done = on_done, .closed = on_closed, .parent = on_parent,
};

static void on_manager_toplevel(void *d, struct zwlr_foreign_toplevel_manager_v1 *m,
                                struct zwlr_foreign_toplevel_handle_v1 *h) {
    (void)d;(void)m;
    struct toplevel *t = calloc(1, sizeof *t);
    t->handle = h; t->next = tops; tops = t;
    zwlr_foreign_toplevel_handle_v1_add_listener(h, &handle_listener, NULL);
}
static void on_manager_finished(void *d, struct zwlr_foreign_toplevel_manager_v1 *m) { (void)d;(void)m; }
static const struct zwlr_foreign_toplevel_manager_v1_listener manager_listener = {
    .toplevel = on_manager_toplevel, .finished = on_manager_finished,
};

static void reg_global(void *d, struct wl_registry *reg, uint32_t name, const char *iface, uint32_t ver) {
    (void)d;
    if (!strcmp(iface, zwlr_foreign_toplevel_manager_v1_interface.name)) {
        struct zwlr_foreign_toplevel_manager_v1 *m =
            wl_registry_bind(reg, name, &zwlr_foreign_toplevel_manager_v1_interface, ver < 3 ? ver : 3);
        zwlr_foreign_toplevel_manager_v1_add_listener(m, &manager_listener, NULL);
    } else if (!strcmp(iface, wl_seat_interface.name) && !seat) {
        seat = wl_registry_bind(reg, name, &wl_seat_interface, 5);
    }
}
static void reg_remove(void *d, struct wl_registry *reg, uint32_t name) { (void)d;(void)reg;(void)name; }
static const struct wl_registry_listener registry_listener = { .global = reg_global, .global_remove = reg_remove };

static int is_home(struct toplevel *t) {
    return !strcmp(t->app_id, "nuxel-pwa-host");
}

static void list(void) {
    int n = 0; for (struct toplevel *t = tops; t; t = t->next) n++;
    printf("WINDOWS=%d\n", n);
    for (struct toplevel *t = tops; t; t = t->next)
        printf("WIN title=%s app_id=%s max=%u min=%u act=%u fs=%u\n",
               t->title, t->app_id, t->maximized, t->minimized, t->activated, t->fullscreen);
}

static void background_all_but_home(void) {
    for (struct toplevel *t = tops; t; t = t->next) {
        if (is_home(t)) continue;
        /* phoc 0.54 does not wire request_minimize: instead of a no-op
           set_minimized, take the window out of fullscreen/maximize so it can
           sit behind Home in the normal stacking layer. */
        if (t->fullscreen) zwlr_foreign_toplevel_handle_v1_unset_fullscreen(t->handle);
        if (t->maximized) zwlr_foreign_toplevel_handle_v1_unset_maximized(t->handle);
    }
}

int main(int argc, char **argv) {
    const char *mode = argc > 1 ? argv[1] : "list";
    const char *arg = argc > 2 ? argv[2] : NULL;
    struct wl_display *dpy = wl_display_connect(NULL);
    if (!dpy) { fprintf(stderr, "CONNECT_FAIL\n"); return 2; }
    struct wl_registry *reg = wl_display_get_registry(dpy);
    wl_registry_add_listener(reg, &registry_listener, NULL);
    wl_display_roundtrip(dpy);
    wl_display_roundtrip(dpy);   /* toplevel handles + state delivered */

    if (!strcmp(mode, "list")) {
        list();
        wl_display_disconnect(dpy);
        return 0;
    }
    if (!strcmp(mode, "home")) {
        background_all_but_home();
        int raised = 0;
        for (struct toplevel *t = tops; t; t = t->next) {
            if (is_home(t)) {
                zwlr_foreign_toplevel_handle_v1_activate(t->handle, seat);
                raised++;
            }
        }
        wl_display_flush(dpy);
        wl_display_roundtrip(dpy);
        wl_display_roundtrip(dpy);   /* collect post-action states */
        list();
        printf("HOME_ACTION raised=%d\n", raised);
        wl_display_disconnect(dpy);
        return 0;
    }
    if (!strcmp(mode, "activate")) {
        int activated = 0;
        for (struct toplevel *t = tops; t; t = t->next) {
            if (is_home(t)) continue;
            if (arg && !strstr(t->app_id, arg)) continue;
            zwlr_foreign_toplevel_handle_v1_activate(t->handle, seat);
            activated++;
            if (arg) break;
            break;
        }
        wl_display_flush(dpy);
        wl_display_roundtrip(dpy);
        wl_display_roundtrip(dpy);
        list();
        printf("ACTIVATE_ACTION activated=%d\n", activated);
        wl_display_disconnect(dpy);
        return 0;
    }
    if (!strcmp(mode, "close-foreground")) {
        int closed = 0;
        for (struct toplevel *t = tops; t; t = t->next) {
            if (!is_home(t) && t->activated) {
                zwlr_foreign_toplevel_handle_v1_close(t->handle);
                closed++;
            }
        }
        wl_display_flush(dpy);
        wl_display_roundtrip(dpy);
        printf("CLOSE_FOREGROUND closed=%d\n", closed);
        wl_display_disconnect(dpy);
        return 0;
    }
    fprintf(stderr, "UNKNOWN_MODE %s\n", mode);
    wl_display_disconnect(dpy);
    return 6;
}
