/* nuxel-foreign-toplevel — trusted shell-side window controller for Nuxel.
 *
 * Uses zwlr_foreign_toplevel_manager_v1 (exposed by phoc/wlroots, verified in
 * the phoc binary) to enumerate toplevel windows and to route the Penguin Home
 * action at the COMPOSITOR level: minimize/raise windows without killing them.
 *
 * libwayland-client is dlopen()'d at runtime so this file needs no wayland
 * headers to cross-compile from the Mac. The protocol is marshalled with
 * wl_proxy_marshal_flags using hand-declared wl_message/wl_interface tables
 * whose layout matches wayland-client-core.h exactly.
 *
 * Modes:
 *   list      print every toplevel (title, app_id, states)
 *   home      minimize every non-Home toplevel, unset_minimized(raise) Home
 *
 * Never kills a client, never touches the framebuffer.
 */
#define _GNU_SOURCE
#include <dlfcn.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

struct wl_array { size_t size; size_t alloc; void *data; };
struct wl_interface {
    const char *name; int version;
    int method_count; const void *methods;
    int event_count; const void *events;
};
struct wl_message {
    const char *name; const char *signature;
    const struct wl_interface **types;
};

static void *WL;
static void *(*_connect)(const char *);
static void (*_disconnect)(void *);
static int (*_roundtrip)(void *);
static void *(*_marshal)(void *, uint32_t, const void *, uint32_t, uint32_t, ...);
static int (*_add_listener)(void *, void (**)(void), void *);
static void (*_destroy)(void *);

static int load_wayland(void) {
    WL = dlopen("libwayland-client.so.0", RTLD_NOW | RTLD_GLOBAL);
    if (!WL) { fprintf(stderr, "DLOPEN_FAIL %s\n", dlerror()); return -1; }
    _connect   = (void *(*)(const char *)) dlsym(WL, "wl_display_connect");
    _disconnect= (void (*)(void *)) dlsym(WL, "wl_display_disconnect");
    _roundtrip = (int (*)(void *)) dlsym(WL, "wl_display_roundtrip");
    _marshal   = (void *(*)(void *,uint32_t,const void *,uint32_t,uint32_t,...)) dlsym(WL, "wl_proxy_marshal_flags");
    _add_listener = (int (*)(void *,void (**)(void),void *)) dlsym(WL, "wl_proxy_add_listener");
    _destroy   = (void (*)(void *)) dlsym(WL, "wl_proxy_destroy");
    if (!_connect || !_disconnect || !_roundtrip || !_marshal || !_add_listener || !_destroy) {
        fprintf(stderr, "DLSYM_FAIL %s\n", dlerror()); return -1;
    }
    return 0;
}

/* ---- interface tables (types arrays name new_id targets) ----------------- */
static struct wl_interface wl_registry_interface;
static struct wl_interface fto_manager_interface;
static struct wl_interface fto_handle_interface;

static const struct wl_interface *wl_display_sync_types[] = { NULL };       /* wl_callback */
static const struct wl_interface *wl_display_get_registry_types[] = { &wl_registry_interface };
static struct wl_message wl_display_messages[] = {
    { "sync", "n", wl_display_sync_types },
    { "get_registry", "n", wl_display_get_registry_types },
};
static struct wl_message wl_display_events[] = {
    { "error", "ous", NULL }, { "delete_id", "u", NULL },
};
static struct wl_interface wl_display_interface = {
    "wl_display", 1, 2, wl_display_messages, 2, wl_display_events,
};

static const struct wl_interface *wl_registry_bind_types[] = { NULL, NULL, NULL, &fto_manager_interface };
static struct wl_message wl_registry_messages[] = {
    { "bind", "usun", wl_registry_bind_types },
};
static struct wl_message wl_registry_events[] = {
    { "global", "usu", NULL }, { "global_remove", "u", NULL },
};
static struct wl_interface wl_registry_interface = {
    "wl_registry", 1, 1, wl_registry_messages, 2, wl_registry_events,
};

static struct wl_message fto_manager_messages[] = { { "stop", "", NULL } };
static const struct wl_interface *fto_manager_toplevel_types[] = { &fto_handle_interface };
static struct wl_message fto_manager_events[] = {
    { "toplevel", "n", fto_manager_toplevel_types },
    { "finished", "", NULL },
};
static struct wl_interface fto_manager_interface = {
    "zwlr_foreign_toplevel_manager_v1", 3, 1, fto_manager_messages, 2, fto_manager_events,
};

static struct wl_message fto_handle_messages[] = {
    { "set_maximized", "", NULL },
    { "unset_maximized", "", NULL },
    { "set_minimized", "", NULL },
    { "unset_minimized", "", NULL },
    { "activate", "o", NULL },
    { "close", "", NULL },
    { "set_rectangle", "oiiii", NULL },
    { "destroy", "", NULL },
    { "set_fullscreen", "?o", NULL },
    { "unset_fullscreen", "", NULL },
};
static struct wl_message fto_handle_events[] = {
    { "title", "s", NULL },
    { "app_id", "s", NULL },
    { "output_enter", "o", NULL },
    { "output_leave", "o", NULL },
    { "state", "a", NULL },
    { "done", "", NULL },
    { "closed", "", NULL },
    { "parent", "?o", NULL },
};
static struct wl_interface fto_handle_interface = {
    "zwlr_foreign_toplevel_handle_v1", 3, 10, fto_handle_messages, 8, fto_handle_events,
};

/* ---- window tracking ------------------------------------------------------ */
struct window {
    void *handle; char title[256]; char app_id[256];
    int maximized, minimized, activated, fullscreen;
    struct window *next;
};
static struct window *windows;
static void *g_display, *g_registry, *g_manager;
static int have_manager;

static struct window *find_win(void *h) {
    for (struct window *w = windows; w; w = w->next) if (w->handle == h) return w;
    return NULL;
}
static void on_title(void *d, void *h, const char *t) { (void)d; struct window *w=find_win(h); if(w) snprintf(w->title,sizeof w->title,"%s",t?t:""); }
static void on_appid(void *d, void *h, const char *t) { (void)d; struct window *w=find_win(h); if(w) snprintf(w->app_id,sizeof w->app_id,"%s",t?t:""); }
static void on_out_e(void *d, void *h, void *o) { (void)d;(void)h;(void)o; }
static void on_out_l(void *d, void *h, void *o) { (void)d;(void)h;(void)o; }
static void on_state(void *d, void *h, struct wl_array *a) {
    (void)d; struct window *w = find_win(h); if(!w) return;
    w->maximized=w->minimized=w->activated=w->fullscreen=0;
    uint32_t *p = (uint32_t*)a->data; size_t n = a->size/4;
    for (size_t i=0;i<n;i++){ switch(p[i]){ case 1: w->maximized=1; break; case 2: w->minimized=1; break; case 3: w->activated=1; break; case 4: w->fullscreen=1; break; } }
}
static void on_done(void *d, void *h) { (void)d;(void)h; }
static void on_closed(void *d, void *h) {
    (void)d; struct window **pp=&windows;
    while(*pp){ if((*pp)->handle==h){ struct window *t=*pp; *pp=t->next; free(t); break; } pp=&(*pp)->next; }
}
static void on_parent(void *d, void *h, void *p) { (void)d;(void)h;(void)p; }
static void (*handle_listener[])(void) = {
    (void(*)(void))on_title,(void(*)(void))on_appid,(void(*)(void))on_out_e,(void(*)(void))on_out_l,
    (void(*)(void))on_state,(void(*)(void))on_done,(void(*)(void))on_closed,(void(*)(void))on_parent,
    NULL,
};
static void on_toplevel(void *d, void *m, void *h) {
    (void)d;(void)m; struct window *w=calloc(1,sizeof *w); w->handle=h; w->next=windows; windows=w;
    _add_listener(h, handle_listener, NULL);
}
static void on_finished(void *d, void *m) { (void)d;(void)m; }
static void (*manager_listener[])(void) = { (void(*)(void))on_toplevel, (void(*)(void))on_finished, NULL };

static void on_global(void *d, void *r, uint32_t name, const char *iface, uint32_t ver) {
    (void)d;(void)r;
    fprintf(stderr, "GLOBAL name=%u iface=%s ver=%u\n", name, iface, ver);
    if (!strcmp(iface, "zwlr_foreign_toplevel_manager_v1")) {
        have_manager = 1;
        /* bind: registry opcode 0 ("usun"); new_id target set via types[3] */
        g_manager = _marshal(g_registry, 0, &fto_manager_interface, ver < 3 ? ver : 3, 0,
                             name, "zwlr_foreign_toplevel_manager_v1", ver, NULL);
        if (g_manager) _add_listener(g_manager, manager_listener, NULL);
    }
}
static void on_global_remove(void *d, void *r, uint32_t n) { (void)d;(void)r;(void)n; }
static void on_display_error(void *d, void *display, void *object, uint32_t code, const char *msg) {
    (void)d;(void)display; fprintf(stderr, "DISPLAY_ERROR object=%p code=%u msg=%s\n", object, code, msg?msg:"?");
}
static void on_delete_id(void *d, void *display, uint32_t id) { (void)d;(void)display;(void)id; }
static void (*display_listener[])(void) = { (void(*)(void))on_display_error, (void(*)(void))on_delete_id, NULL };
static void (*registry_listener[])(void) = { (void(*)(void))on_global, (void(*)(void))on_global_remove, NULL };

int main(int argc, char **argv) {
    const char *mode = (argc > 1) ? argv[1] : "list";
    if (load_wayland()) return 2;
    g_display = _connect(NULL);
    if (!g_display) { fprintf(stderr, "CONNECT_FAIL\n"); return 3; }
    /* display opcode 1 = get_registry */
    _add_listener(g_display, display_listener, NULL);
    g_registry = _marshal(g_display, 1, &wl_registry_interface, 1, 0, NULL);
    if (!g_registry) { fprintf(stderr, "REG_FAIL\n"); return 4; }
    _add_listener(g_registry, registry_listener, NULL);
    _roundtrip(g_display); _roundtrip(g_display);
    if (!have_manager || !g_manager) { fprintf(stderr, "NO_FOREIGN_TOPLEVEL_MANAGER\n"); return 5; }
    _roundtrip(g_display); _roundtrip(g_display);

    int n=0; for (struct window *w=windows;w;w=w->next) n++;
    printf("WINDOWS=%d\n", n);
    for (struct window *w=windows;w;w=w->next)
        printf("WIN title=%s app_id=%s max=%d min=%d act=%d fs=%d\n",
               w->title, w->app_id, w->maximized, w->minimized, w->activated, w->fullscreen);

    if (!strcmp(mode, "home")) {
        int minimized=0, raised=0;
        for (struct window *w=windows;w;w=w->next) {
            int is_home = !strcmp(w->app_id, "nuxel-pwa-host") || !strcmp(w->title, "Nuxel");
            if (is_home) {
                _marshal(w->handle, 3, &fto_handle_interface, 3, 0);  /* unset_minimized */
                raised++;
            } else {
                _marshal(w->handle, 2, &fto_handle_interface, 3, 0);  /* set_minimized */
                minimized++;
            }
        }
        _roundtrip(g_display);
        printf("HOME_ACTION minimized=%d raised=%d\n", minimized, raised);
    }
    /* PWNAGE-43000: bring a launched native app to the glass.  The Home
       surface is a FULLSCREEN toplevel, so a normal app window would otherwise
       map underneath it even after activation.  Minimize Home, then
       unminimize/activate/fullscreen the requested app (or every non-Home
       window when no app id is supplied). */
    if (!strcmp(mode, "focus") || !strcmp(mode, "fullscreen")) {
        const char *want = (argc > 2) ? argv[2] : NULL;
        int focused=0, minimized=0;
        for (struct window *w=windows;w;w=w->next) {
            int is_home = !strcmp(w->app_id, "nuxel-pwa-host") || !strcmp(w->title, "Nuxel");
            if (is_home) {
                /* A fullscreen Home is the reason set_minimized looked
                   ineffective.  Leave fullscreen first, then minimize. */
                _marshal(w->handle, 9, &fto_handle_interface, 3, 0);  /* unset_fullscreen */
                _marshal(w->handle, 2, &fto_handle_interface, 3, 0);  /* set_minimized */
                minimized++;
                continue;
            }
            if (want && *want && strcmp(w->app_id, want) && strcmp(w->title, want)) continue;
            _marshal(w->handle, 3, &fto_handle_interface, 3, 0);  /* unset_minimized */
            _marshal(w->handle, 0, &fto_handle_interface, 3, 0);  /* set_maximized */
            focused++;
        }
        _roundtrip(g_display);
        printf("FOCUS_ACTION focused=%d home_minimized=%d want=%s\n",
               focused, minimized, want ? want : "*");
    }
    _disconnect(g_display);
    return 0;
}
