// Nuxel wayvnc compatibility shim.
//
// 1. Hide ext-image-copy-capture globals. wayvnc 0.9.1 prefers that protocol
//    but phoc advertises no usable buffer format on this image. Without them
//    wayvnc falls back to the proven zwlr-screencopy path.
// 2. Advertise screencopy v2. phoc copy_with_damage returns an unfilled
//    buffer on the headless output; plain copy works.
// 3. Wayvnc 0.9.1 does not handle wl_output transform changes (upstream TODO).
//    Translate a transform change into the dimension-change callback it does
//    handle, so a live VNC client receives RFB DesktopSize on rotation.
#define _GNU_SOURCE
#include <stdlib.h>
#include <string.h>
#include <dlfcn.h>
#include <wayland-client-core.h>
#include <wayland-client-protocol.h>

struct regwrap {
    struct wl_registry_listener listener;
    struct wl_registry_listener orig;
    void *data;
};

struct outwrap {
    struct wl_output_listener listener;
    struct wl_output_listener orig;
    void *data;
    int32_t width, height, refresh;
    int32_t transform, last_transform;
    int have_mode, have_transform;
};

static int hidden(const char *iface)
{
    return iface && (!strcmp(iface, "ext_image_copy_capture_manager_v1") ||
                     !strcmp(iface, "ext_output_image_capture_source_manager_v1"));
}

static void reg_global(void *data, struct wl_registry *registry, uint32_t name,
                       const char *interface, uint32_t version)
{
    struct regwrap *w = data;
    if (hidden(interface))
        return;
    if (interface && !strcmp(interface, "zwlr_screencopy_manager_v1") && version > 2)
        version = 2;
    if (w->orig.global)
        w->orig.global(w->data, registry, name, interface, version);
}

static void reg_remove(void *data, struct wl_registry *registry, uint32_t name)
{
    struct regwrap *w = data;
    if (w->orig.global_remove)
        w->orig.global_remove(w->data, registry, name);
}

static void out_geometry(void *data, struct wl_output *o, int32_t x, int32_t y,
                         int32_t pw, int32_t ph, int32_t sub, const char *make,
                         const char *model, int32_t transform)
{
    struct outwrap *w = data;
    if (w->orig.geometry)
        w->orig.geometry(w->data, o, x, y, pw, ph, sub, make, model, transform);
    w->transform = transform;
    if (!w->have_transform) {
        w->last_transform = transform;
        w->have_transform = 1;
    }
}

static void out_mode(void *data, struct wl_output *o, uint32_t flags,
                     int32_t width, int32_t height, int32_t refresh)
{
    struct outwrap *w = data;
    if (w->orig.mode)
        w->orig.mode(w->data, o, flags, width, height, refresh);
    if (flags & WL_OUTPUT_MODE_CURRENT) {
        w->width = width;
        w->height = height;
        w->refresh = refresh;
        w->have_mode = 1;
    }
}

static void out_done(void *data, struct wl_output *o)
{
    struct outwrap *w = data;
    // Feed a fake size then the real size before the done callback. wayvnc
    // sets is_dimension_changed on the first event and keeps it until done,
    // while the second restores the real mode for the capture restart.
    if (w->have_transform && w->have_mode && w->transform != w->last_transform) {
        if (w->orig.mode) {
            w->orig.mode(w->data, o, WL_OUTPUT_MODE_CURRENT,
                         w->width + 1, w->height, w->refresh);
            w->orig.mode(w->data, o, WL_OUTPUT_MODE_CURRENT,
                         w->width, w->height, w->refresh);
        }
        w->last_transform = w->transform;
    }
    if (w->orig.done)
        w->orig.done(w->data, o);
}

static void out_scale(void *data, struct wl_output *o, int32_t factor)
{
    struct outwrap *w = data;
    if (w->orig.scale)
        w->orig.scale(w->data, o, factor);
}

static void out_name(void *data, struct wl_output *o, const char *name)
{
    struct outwrap *w = data;
    if (w->orig.name)
        w->orig.name(w->data, o, name);
}

static void out_description(void *data, struct wl_output *o, const char *desc)
{
    struct outwrap *w = data;
    if (w->orig.description)
        w->orig.description(w->data, o, desc);
}

int wl_proxy_add_listener(struct wl_proxy *proxy,
                          void (**implementation)(void), void *data)
{
    static int (*real)(struct wl_proxy *, void (**)(void), void *);
    if (!real)
        real = (int (*)(struct wl_proxy *, void (**)(void), void *))
            dlsym(RTLD_NEXT, "wl_proxy_add_listener");
    const char *cls = wl_proxy_get_class(proxy);

    if (cls && !strcmp(cls, "wl_registry")) {
        struct regwrap *w = calloc(1, sizeof(*w));
        if (w) {
            w->orig = *(struct wl_registry_listener *)implementation;
            w->data = data;
            w->listener.global = reg_global;
            w->listener.global_remove = reg_remove;
            return real(proxy, (void (**)(void))&w->listener, w);
        }
    }

    if (cls && !strcmp(cls, "wl_output")) {
        struct outwrap *w = calloc(1, sizeof(*w));
        if (w) {
            w->orig = *(struct wl_output_listener *)implementation;
            w->data = data;
            w->listener.geometry = out_geometry;
            w->listener.mode = out_mode;
            w->listener.done = out_done;
            w->listener.scale = out_scale;
            w->listener.name = out_name;
            w->listener.description = out_description;
            return real(proxy, (void (**)(void))&w->listener, w);
        }
    }

    return real(proxy, implementation, data);
}
