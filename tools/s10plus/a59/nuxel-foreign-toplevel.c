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
 *   list               print every toplevel (title, app_id, states)
 *   home               minimize every non-Home toplevel, raise Home
 *   activate <app_id>  unminimize/maximize/activate one app and minimize Home
 *   close <app_id>     ask one non-Home toplevel to close (exact identity)
 *   close-foreground   ask the activated non-Home toplevel to close
 *
 * `close-foreground` uses the compositor's close request (opcode 5); the
 * Bridge follows it with a bounded stop of that app's transient systemd units.
 * It never kills Home, the launcher host or a daemon, and never writes /dev/fb0.
 */
#define _GNU_SOURCE
#include <dlfcn.h>
#include <errno.h>
#include <fcntl.h>
#include <poll.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <time.h>
#include <unistd.h>

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
static int (*_flush)(void *);
static int (*_get_fd)(void *);
static int (*_dispatch)(void *);
static uint32_t (*_get_version)(void *);
static const struct wl_interface *(*_get_iface)(void *);

static int load_wayland(void) {
    WL = dlopen("libwayland-client.so.0", RTLD_NOW | RTLD_GLOBAL);
    if (!WL) { fprintf(stderr, "DLOPEN_FAIL %s\n", dlerror()); return -1; }
    _connect   = (void *(*)(const char *)) dlsym(WL, "wl_display_connect");
    _disconnect= (void (*)(void *)) dlsym(WL, "wl_display_disconnect");
    _roundtrip = (int (*)(void *)) dlsym(WL, "wl_display_roundtrip");
    _marshal   = (void *(*)(void *,uint32_t,const void *,uint32_t,uint32_t,...)) dlsym(WL, "wl_proxy_marshal_flags");
    _add_listener = (int (*)(void *,void (**)(void),void *)) dlsym(WL, "wl_proxy_add_listener");
    _destroy   = (void (*)(void *)) dlsym(WL, "wl_proxy_destroy");
    _flush     = (int (*)(void *)) dlsym(WL, "wl_display_flush");
    _get_fd    = (int (*)(void *)) dlsym(WL, "wl_display_get_fd");
    _dispatch  = (int (*)(void *)) dlsym(WL, "wl_display_dispatch");
    _get_version = (uint32_t (*)(void *)) dlsym(WL, "wl_proxy_get_version");
    _get_iface = (const struct wl_interface *(*)(void *)) dlsym(WL, "wl_proxy_get_interface");
    if (!_connect || !_disconnect || !_roundtrip || !_marshal || !_add_listener || !_destroy ||
        !_flush || !_get_fd || !_dispatch || !_get_version) {
        fprintf(stderr, "DLSYM_FAIL %s\n", dlerror()); return -1;
    }
    return 0;
}

/* ---- interface tables (types arrays name new_id targets) ----------------- */
static struct wl_interface wl_registry_interface;
static struct wl_interface wl_seat_interface;
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

/* wl_registry.bind's new_id interface is supplied to wl_proxy_marshal_flags
 * as its interface argument (as generated code does), not by this table. */
static const struct wl_interface *wl_registry_bind_types[] = { NULL, NULL, NULL, NULL };
static struct wl_message wl_registry_messages[] = {
    { "bind", "usun", wl_registry_bind_types },
};
static struct wl_message wl_registry_events[] = {
    { "global", "usu", NULL }, { "global_remove", "u", NULL },
};
static struct wl_interface wl_registry_interface = {
    "wl_registry", 1, 1, wl_registry_messages, 2, wl_registry_events,
};
/* Minimal but protocol-complete wl_seat table.  foreign-toplevel activate()
 * names the seat whose focus should move.  The seat still emits capabilities
 * and name events; an interface with event_count=0 made libwayland abort
 * dispatch ("interface 'wl_seat' has no event 1"), which silently hid EVERY
 * toplevel from the chrome/lock watcher. */
static struct wl_message wl_seat_events[] = {
    { "capabilities", "u", NULL },
    { "name", "s", NULL },
};
static struct wl_interface wl_seat_interface = {
    "wl_seat", 7, 0, NULL, 2, wl_seat_events,
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
static void *g_display, *g_registry, *g_manager, *g_seat;
static int have_manager;
/* PWNAGE-90000: lock enforcement is edge-triggered.  A level-triggered
   re-enforce every second raised Home over the playing preload surface, which
   made phoc consider that surface invisible and stop its frame callbacks. */
static int g_state_dirty;

/* Seat events are informational; consuming them keeps the default queue
 * healthy while activate() still receives the seat object. */
static void on_seat_capabilities(void *d, void *s, uint32_t caps) {
    (void)d; (void)s; (void)caps;
}
static void on_seat_name(void *d, void *s, const char *name) {
    (void)d; (void)s; (void)name;
}
static void (*seat_listener[])(void) = {
    (void(*)(void))on_seat_capabilities,
    (void(*)(void))on_seat_name,
    NULL,
};

static struct window *find_win(void *h) {
    for (struct window *w = windows; w; w = w->next) if (w->handle == h) return w;
    return NULL;
}
static void on_title(void *d, void *h, const char *t) { (void)d; struct window *w=find_win(h); if(w) snprintf(w->title,sizeof w->title,"%s",t?t:""); }
static void on_appid(void *d, void *h, const char *t) { (void)d; struct window *w=find_win(h); if(w) snprintf(w->app_id,sizeof w->app_id,"%s",t?t:""); }
static void on_out_e(void *d, void *h, void *o) { (void)d;(void)h;(void)o; }
static void on_out_l(void *d, void *h, void *o) { (void)d;(void)h;(void)o; }
static int is_preload_window(const struct window *w) {
    if (!w) return 0;
    return !strcmp(w->app_id, "mpv") ||
           strstr(w->title, "nuxel-preloading") != NULL ||
           strstr(w->title, "preload") != NULL;
}
static void on_state(void *d, void *h, struct wl_array *a) {
    (void)d; struct window *w = find_win(h); if(!w) return;
    int was_max = w->maximized, was_fs = w->fullscreen, was_act = w->activated;
    w->maximized=w->minimized=w->activated=w->fullscreen=0;
    uint32_t *p = (uint32_t*)a->data; size_t n = a->size/4;
    /* zwlr_foreign_toplevel_handle_v1.state: 0=maximized, 1=minimized,
       2=activated, 3=fullscreen.  An off-by-one here made windowed
       GTK/Flatpak apps invisible to the top bar and focus watcher. */
    for (size_t i=0;i<n;i++){ switch(p[i]){ case 0: w->maximized=1; break; case 1: w->minimized=1; break; case 2: w->activated=1; break; case 3: w->fullscreen=1; break; } }
    /* Only a change that could cover the lockscreen needs re-enforcement.
       The preload player is a trusted Nuxel overlay and is exempt. */
    if (!is_preload_window(w) && strcmp(w->app_id, "nuxel-pwa-host") &&
        ((w->maximized && !was_max) || (w->fullscreen && !was_fs) ||
         (w->activated && !was_act))) {
        g_state_dirty = 1;
    }
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
    if (!strcmp(iface, "wl_seat") && !g_seat) {
        g_seat = _marshal(g_registry, 0, &wl_seat_interface, ver < 7 ? ver : 7, 0,
                          name, "wl_seat", ver < 7 ? ver : 7, NULL);
        if (g_seat) _add_listener(g_seat, seat_listener, NULL);
    } else if (!strcmp(iface, "zwlr_foreign_toplevel_manager_v1")) {
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


/* ---------------------------------------------------------------------------
 * PWNAGE-62000: compositor-level lock enforcement.
 *
 * The authoritative lock flag is written only by the root bridge
 * (security_provider.py).  Missing, unreadable or malformed state fails closed.
 * While locked, a persistent foreign-toplevel subscription re-checks every
 * 250 ms and on every state event: every non-Home toplevel is taken out of
 * fullscreen/maximised and asked to minimise, then the Home toplevel is
 * unminimised, un-fullscreened, maximised and activated.  A late app activation
 * therefore cannot cover the Home lockscreen; the app process is never killed.
 * ------------------------------------------------------------------------- */
#define LOCK_STATE "/run/nuxel/security/lock-state.json"
#define LOCK_RECEIPT "/run/nuxel/lock-enforcement.state"
#define FOREGROUND_STATE "/run/nuxel/foreground.state"

static int read_lock_state(void) {
    FILE *f = fopen(LOCK_STATE, "r");
    if (!f) return -1;                 /* unknown -> fail closed */
    char b[4096];
    size_t n = fread(b, 1, sizeof b - 1, f);
    fclose(f);
    b[n] = 0;
    char *p = strstr(b, "\"locked\"");
    if (!p) return -1;
    p = strchr(p, ':');
    if (!p) return -1;
    p++;
    while (*p == ' ' || *p == '\t' || *p == '\n' || *p == '\r') p++;
    if (!strncmp(p, "false", 5)) return 0;
    if (!strncmp(p, "true", 4)) return 1;
    return -1;
}

static uint32_t handle_version(void *h) {
    return _get_version ? _get_version(h) : 3;
}

static int is_home(const struct window *w) {
    return !strcmp(w->app_id, "nuxel-pwa-host") || !strcmp(w->title, "Nuxel");
}

static void json_id(char *dst, size_t n, const char *src) {
    size_t i = 0;
    if (n == 0) return;
    for (; src && *src && i + 1 < n; src++) {
        char c = *src;
        if (c == '"' || c == '\\' || c == '\n' || c == '\r' || c == '\t') c = '_';
        dst[i++] = c;
    }
    dst[i] = 0;
}

static void write_receipt(int locked, int home_raised, int hidden,
                          const char *active, const char *error) {
    char tmp[256];
    snprintf(tmp, sizeof tmp, LOCK_RECEIPT ".%d", (int)getpid());
    FILE *f = fopen(tmp, "w");
    if (!f) return;
    char act[256] = "", err[256] = "";
    json_id(act, sizeof act, active ? active : "");
    json_id(err, sizeof err, error ? error : "");
    time_t now = time(NULL);
    fprintf(f,
        "{\"schema_version\":1,\"updated_at\":%lld,\"locked\":%s,"
        "\"home_raised\":%s,\"hidden_non_home\":%d,\"active_app\":\"%s\","
        "\"error\":\"%s\",\"owner\":\"nuxel-foreign-toplevel\"}\n",
        (long long)now, locked ? "true" : "false",
        home_raised ? "true" : "false", hidden, act, err);
    fclose(f);
    rename(tmp, LOCK_RECEIPT);
}

static void write_foreground(int locked, const char *active) {
    char tmp[256];
    snprintf(tmp, sizeof tmp, FOREGROUND_STATE ".%d", (int)getpid());
    FILE *f = fopen(tmp, "w");
    if (!f) return;
    char act[256] = "";
    json_id(act, sizeof act, active ? active : "");
    fprintf(f, "locked=%d native=%d app_id=%s\n",
            locked ? 1 : 0, (active && *active) ? 1 : 0, act);
    fclose(f);
    rename(tmp, FOREGROUND_STATE);
}

/* True while the trusted preload cinema owns the glass.  /run is per-boot, so
   a document left by an older boot cannot qualify. */
static int preload_active(void) {
    FILE *f = fopen("/run/nuxel/preload-cinema.overlay", "r");
    if (!f) return 0;
    char b[1024];
    size_t n = fread(b, 1, sizeof b - 1, f);
    fclose(f); b[n] = 0;
    return strstr(b, "\"state\": \"covered\"") != NULL ||
           strstr(b, "\"state\":\"covered\"") != NULL ||
           strstr(b, "\"state\": \"starting\"") != NULL ||
           strstr(b, "\"state\":\"starting\"") != NULL;
}

static void enforce_locked(int locked) {
    int hidden = 0, raised = 0;
    const char *active = "";
    /* The preload video is a trusted, audio-free Nuxel surface above the real
       lockscreen.  Re-raising Home over it stops its frame callbacks.  The
       security state stays locked; only the compositor restack is skipped. */
    if (preload_active()) {
        write_receipt(locked, 0, 0, "", "preload-overlay-active");
        write_foreground(locked, NULL);
        return;
    }
    for (struct window *w = windows; w; w = w->next) {
        if (is_home(w)) continue;
        if (w->activated) active = w->app_id;
        /* phoc 0.54 does not implement request_minimize, but unsetting
           fullscreen/maximise is honoured and is enough to move the app out
           of the top stacking layer.  Only issue a request when the state
           actually calls for it; repeating identical requests every second
           caused GTK/Electron redraw and reinitialisation. */
        if (w->fullscreen) _marshal(w->handle, 9, NULL, handle_version(w->handle), 0);
        if (w->maximized) _marshal(w->handle, 1, NULL, handle_version(w->handle), 0);
        if (!w->minimized) _marshal(w->handle, 2, NULL, handle_version(w->handle), 0);
        hidden++;
    }
    for (struct window *w = windows; w; w = w->next) {
        if (!is_home(w)) continue;
        if (w->minimized) _marshal(w->handle, 3, NULL, handle_version(w->handle), 0);
        if (w->fullscreen) _marshal(w->handle, 9, NULL, handle_version(w->handle), 0);
        if (!w->maximized) _marshal(w->handle, 0, NULL, handle_version(w->handle), 0);
        if (!w->activated && g_seat) _marshal(w->handle, 4, NULL, handle_version(w->handle), 0, g_seat);
        raised = 1;
    }
    if (g_display) _flush(g_display);   /* bounded: never block on a roundtrip */
    write_receipt(locked, raised, hidden, active, NULL);
    write_foreground(locked, active);
}

static int watch_lock(void *dpy) {
    int last_locked = -2;
    time_t last_receipt = 0;
    time_t last_enforce = 0;
    for (;;) {
        int locked = read_lock_state();
        time_t now = time(NULL);
        int nonhome_active = 0;
        for (struct window *w = windows; w; w = w->next)
            if (!is_home(w) && w->activated && !is_preload_window(w)) { nonhome_active = 1; break; }
        /* Fail closed: unknown is treated exactly like locked.  Enforcement is
           edge-triggered (lock transition, a late non-Home activation, or a
           meaningful state change).  A level-triggered 1 s re-enforce raised
           Home over the preload video and froze its frame callbacks. */
        if (locked != 0 && (locked != last_locked || nonhome_active || g_state_dirty)) {
            if (locked != last_locked || g_state_dirty || now - last_enforce >= 1) {
                enforce_locked(1);
                last_enforce = now;
                g_state_dirty = 0;
            }
        } else if (locked != 0) {
            write_foreground(1, NULL);
        } else {
            int native = 0;
            const char *active = "";
            for (struct window *w = windows; w; w = w->next) {
                if (is_home(w)) continue;
                if (w->activated) { native = 1; active = w->app_id; break; }
            }
            if (locked != last_locked || now - last_receipt >= 2) {
                write_receipt(0, 0, 0, active, NULL);
                last_receipt = now;
            }
            write_foreground(0, native ? active : NULL);
        }
        if (locked != last_locked) {
            fprintf(stderr, "LOCK_WATCH locked=%d\n", locked);
            last_locked = locked;
        }
        _flush(dpy);
        struct pollfd pfd = { .fd = _get_fd(dpy), .events = POLLIN, .revents = 0 };
        int pr = poll(&pfd, 1, 250);
        if (pr < 0) {
            if (errno == EINTR) continue;
            fprintf(stderr, "LOCK_WATCH poll errno=%d\n", errno);
            return 1;
        }
        if (pr > 0 && (pfd.revents & POLLIN)) {
            if (_dispatch(dpy) < 0) {
                fprintf(stderr, "LOCK_WATCH dispatch failed\n");
                return 1;
            }
        }
    }
}

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
                _marshal(w->handle, 3, NULL, handle_version(w->handle), 0);  /* unset_minimized */
                _marshal(w->handle, 0, NULL, handle_version(w->handle), 0);  /* set_maximized */
                if (g_seat) _marshal(w->handle, 4, NULL, handle_version(w->handle), 0, g_seat); /* activate */
                raised++;
            } else {
                _marshal(w->handle, 2, NULL, handle_version(w->handle), 0);  /* set_minimized */
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
    if (!strcmp(mode, "focus") || !strcmp(mode, "fullscreen") || !strcmp(mode, "activate")) {
        const char *want = (argc > 2) ? argv[2] : NULL;
        int focused=0, minimized=0;
        for (struct window *w=windows;w;w=w->next) {
            int is_home = !strcmp(w->app_id, "nuxel-pwa-host") || !strcmp(w->title, "Nuxel");
            if (is_home) {
                /* A fullscreen Home is the reason set_minimized looked
                   ineffective.  Leave fullscreen first, then minimize. */
                _marshal(w->handle, 9, NULL, handle_version(w->handle), 0);  /* unset_fullscreen */
                _marshal(w->handle, 2, NULL, handle_version(w->handle), 0);  /* set_minimized */
                minimized++;
                continue;
            }
            if (want && *want && strcmp(w->app_id, want) && strcmp(w->title, want)) continue;
            _marshal(w->handle, 3, NULL, handle_version(w->handle), 0);  /* unset_minimized */
            _marshal(w->handle, 0, NULL, handle_version(w->handle), 0);  /* set_maximized */
            /* The protocol requires a wl_seat for activate(); without this
               call wlroots may update the requested size but keep keyboard
               focus and stacking on the shell surface. */
            if (g_seat) _marshal(w->handle, 4, NULL, handle_version(w->handle), 0, g_seat);
            focused++;
        }
        _roundtrip(g_display);
        printf("FOCUS_ACTION focused=%d home_minimized=%d want=%s\n",
               focused, minimized, want ? want : "*");
    }
    if (!strcmp(mode, "close")) {
        const char *want = (argc > 2) ? argv[2] : NULL;
        int closed = 0;
        if (want && *want) {
            for (struct window *w = windows; w; w = w->next) {
                int is_home = !strcmp(w->app_id, "nuxel-pwa-host") ||
                              !strcmp(w->title, "Nuxel");
                if (is_home) continue;
                if (strcmp(w->app_id, want) && strcmp(w->title, want)) continue;
                _marshal(w->handle, 5, NULL, handle_version(w->handle), 0);  /* close */
                printf("CLOSE_ACTION app_id=%s title=%s closed=1\n", w->app_id, w->title);
                closed++;
            }
            _roundtrip(g_display);
        }
        printf("CLOSE_TARGET closed=%d want=%s\n", closed, want ? want : "*");
    }
    /* Long Back: close ONLY the activated non-Home toplevel.  Home, the
       pwa-host and every daemon are excluded by identity, not by index. */
    if (!strcmp(mode, "lock") || !strcmp(mode, "enforce-lock")) {
        enforce_locked(1);
        printf("LOCK_ACTION locked=1\n");
    }
    if (!strcmp(mode, "watch-lock")) {
        return watch_lock(g_display);
    }
    if (!strcmp(mode, "hide-keyboard")) {
        /* PWNAGE-80000: dismiss the compositor IME without leaving the app
         * backgrounded.  A short focus bounce to Home forces text-input leave
         * (Stevia hides), then the same toplevel is re-activated. */
        struct window *prev = NULL;
        for (struct window *w = windows; w; w = w->next) {
            int is_home = !strcmp(w->app_id, "nuxel-pwa-host") || !strcmp(w->title, "Nuxel");
            if (!is_home && w->activated) { prev = w; break; }
        }
        if (!prev) {
            printf("HIDE_KEYBOARD no-foreground\n");
        } else {
            for (struct window *w = windows; w; w = w->next) {
                int is_home = !strcmp(w->app_id, "nuxel-pwa-host") || !strcmp(w->title, "Nuxel");
                if (is_home) { _marshal(w->handle, 4, NULL, handle_version(w->handle), 0, g_seat); break; }
            }
            _roundtrip(g_display);
            usleep(180000);
            _marshal(prev->handle, 4, NULL, handle_version(prev->handle), 0, g_seat);
            _roundtrip(g_display);
            printf("HIDE_KEYBOARD app_id=%s restored=1\n", prev->app_id);
        }
    }
    if (!strcmp(mode, "close-foreground")) {
        int closed = 0, skipped_home = 0;
        for (struct window *w = windows; w; w = w->next) {
            int is_home = !strcmp(w->app_id, "nuxel-pwa-host") ||
                          !strcmp(w->title, "Nuxel");
            if (is_home) { skipped_home++; continue; }
            if (!w->activated) continue;
            _marshal(w->handle, 5, NULL, handle_version(w->handle), 0);  /* close */
            printf("CLOSE_ACTION app_id=%s title=%s closed=1\n", w->app_id, w->title);
            closed++;
        }
        _roundtrip(g_display);
        printf("CLOSE_FOREGROUND closed=%d home_skipped=%d\n", closed, skipped_home);
    }
    _disconnect(g_display);
    return 0;
}
