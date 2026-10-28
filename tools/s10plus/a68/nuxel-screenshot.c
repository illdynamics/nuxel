/* nuxel-screenshot — one-shot wlr-screencopy capture -> PPM, for physical
 * visual evidence over the USB live console.  Never opens /dev/fb0. */
#define _GNU_SOURCE
#include <errno.h>
#include <fcntl.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/mman.h>
#include <unistd.h>
#include <wayland-client.h>
#include "wlr-screencopy-unstable-v1-client-protocol.h"

static struct wl_compositor *compositor;
static struct wl_shm *shm;
static struct zwlr_screencopy_manager_v1 *scm;
static struct wl_output *output;

static uint32_t fmt;
static int32_t fw, fh, fstride;
static int have_buffer;

static void frame_buffer(void *d, struct zwlr_screencopy_frame_v1 *f, uint32_t format,
                         uint32_t w, uint32_t h, uint32_t stride) {
    (void)d; (void)f;
    fmt = format; fw = (int32_t)w; fh = (int32_t)h; fstride = (int32_t)stride;
    have_buffer = 1;
}
static void frame_flags(void *d, struct zwlr_screencopy_frame_v1 *f, uint32_t flags) {
    (void)d; (void)f; (void)flags;
}
static void frame_ready_cb(void *d, struct zwlr_screencopy_frame_v1 *f,
                           uint32_t s_hi, uint32_t s_lo, uint32_t ns) {
    (void)d; (void)f; (void)s_hi; (void)s_lo; (void)ns;
    *(int *)d = 1;
}
static void frame_failed_cb(void *d, struct zwlr_screencopy_frame_v1 *f) {
    (void)d; (void)f; *(int *)d = -1;
}
static void frame_damage(void *d, struct zwlr_screencopy_frame_v1 *f,
                         uint32_t x, uint32_t y, uint32_t w, uint32_t h) {
    (void)d; (void)f; (void)x; (void)y; (void)w; (void)h;
}
static void frame_linux_dmabuf(void *d, struct zwlr_screencopy_frame_v1 *f, uint32_t format, uint32_t w, uint32_t h) {
    (void)d; (void)f; (void)format; (void)w; (void)h;
}
static void frame_buffer_done(void *d, struct zwlr_screencopy_frame_v1 *f) { (void)d; (void)f; }
static const struct zwlr_screencopy_frame_v1_listener frame_listener = {
    .buffer = frame_buffer, .flags = frame_flags, .ready = frame_ready_cb,
    .failed = frame_failed_cb, .damage = frame_damage,
    .linux_dmabuf = frame_linux_dmabuf, .buffer_done = frame_buffer_done,
};

static int create_shm_buffer(int w, int h, int stride, uint32_t format,
                             struct wl_buffer **out, void **map, size_t *mapn) {
    (void)format;
    int size = stride * h;
    if (size <= 0) return -1;
    int fd = memfd_create("nuxel-shot", MFD_CLOEXEC);
    if (fd < 0) fd = open("/tmp", O_TMPFILE | O_RDWR | O_CLOEXEC, 0600);
    if (fd < 0) return -1;
    if (ftruncate(fd, (off_t)size) < 0) { close(fd); return -1; }
    void *m = mmap(NULL, (size_t)size, PROT_READ | PROT_WRITE, MAP_SHARED, fd, 0);
    if (m == MAP_FAILED) { close(fd); return -1; }
    struct wl_shm_pool *pool = wl_shm_create_pool(shm, fd, size);
    struct wl_buffer *b = wl_shm_pool_create_buffer(pool, 0, w, h, stride, WL_SHM_FORMAT_XRGB8888);
    wl_shm_pool_destroy(pool);
    close(fd);
    if (!b) { munmap(m, (size_t)size); return -1; }
    *out = b; *map = m; *mapn = (size_t)size;
    return 0;
}

static void reg_global(void *d, struct wl_registry *r, uint32_t name, const char *iface, uint32_t ver) {
    (void)d;
    if (!strcmp(iface, wl_compositor_interface.name))
        compositor = wl_registry_bind(r, name, &wl_compositor_interface, 4);
    else if (!strcmp(iface, wl_shm_interface.name))
        shm = wl_registry_bind(r, name, &wl_shm_interface, 1);
    else if (!strcmp(iface, zwlr_screencopy_manager_v1_interface.name))
        scm = wl_registry_bind(r, name, &zwlr_screencopy_manager_v1_interface, ver < 3 ? ver : 3);
    else if (!strcmp(iface, wl_output_interface.name) && !output)
        output = wl_registry_bind(r, name, &wl_output_interface, 3);
}
static void reg_remove(void *d, struct wl_registry *r, uint32_t name) { (void)d; (void)r; (void)name; }
static const struct wl_registry_listener reg_listener = { reg_global, reg_remove };

int main(int argc, char **argv) {
    const char *path = argc > 1 ? argv[1] : "/var/tmp/nuxel-shot.ppm";
    struct wl_display *dpy = wl_display_connect(NULL);
    if (!dpy) { fprintf(stderr, "CONNECT_FAIL\n"); return 2; }
    struct wl_registry *reg = wl_display_get_registry(dpy);
    wl_registry_add_listener(reg, &reg_listener, NULL);
    wl_display_roundtrip(dpy);
    if (!scm || !output || !shm) { fprintf(stderr, "GLOBALS_MISSING scm=%d out=%d shm=%d\n", scm != NULL, output != NULL, shm != NULL); return 3; }

    struct zwlr_screencopy_frame_v1 *frame =
        zwlr_screencopy_manager_v1_capture_output(scm, 0, output);
    if (!frame) { fprintf(stderr, "CAPTURE_NULL\n"); return 4; }
    int state = 0;
    zwlr_screencopy_frame_v1_add_listener(frame, &frame_listener, &state);

    int waited = 0;
    while (!have_buffer && waited < 100) {
        if (wl_display_dispatch(dpy) < 0) { fprintf(stderr, "DISPATCH_FAIL\n"); return 5; }
        waited++;
    }
    if (!have_buffer) { fprintf(stderr, "NO_BUFFER_EVENT fmt=%u w=%d h=%d stride=%d\n", fmt, fw, fh, fstride); return 6; }

    struct wl_buffer *buf = NULL; void *map = NULL; size_t mapn = 0;
    if (create_shm_buffer(fw, fh, fstride, fmt, &buf, &map, &mapn) < 0) {
        fprintf(stderr, "SHM_FAIL\n"); return 7;
    }
    zwlr_screencopy_frame_v1_copy(frame, buf);
    int waited2 = 0;
    while (state == 0 && waited2 < 200) {
        if (wl_display_dispatch(dpy) < 0) { fprintf(stderr, "DISPATCH_FAIL2\n"); return 8; }
        waited2++;
    }
    if (state < 0) { fprintf(stderr, "FRAME_FAILED\n"); return 9; }
    if (state == 0) { fprintf(stderr, "FRAME_TIMEOUT\n"); return 10; }

    FILE *f = fopen(path, "wb");
    if (!f) { fprintf(stderr, "OPEN_FAIL %s\n", path); return 11; }
    const uint8_t *px = (const uint8_t *)map;
    fprintf(f, "P6\n%d %d\n255\n", fw, fh);
    for (int32_t y = 0; y < fh; y++) {
        const uint32_t *row = (const uint32_t *)(px + (size_t)y * fstride);
        for (int32_t x = 0; x < fw; x++) {
            uint32_t v = row[x];
            unsigned char rgb[3];
            rgb[0] = (unsigned char)((v >> 16) & 0xff); /* R */
            rgb[1] = (unsigned char)((v >> 8) & 0xff);  /* G */
            rgb[2] = (unsigned char)(v & 0xff);         /* B */
            fwrite(rgb, 1, 3, f);
        }
    }
    fclose(f);
    wl_buffer_destroy(buf);
    munmap(map, mapn);
    zwlr_screencopy_frame_v1_destroy(frame);
    wl_display_disconnect(dpy);
    printf("SHOT_OK %s %dx%d stride=%d fmt=0x%08x\n", path, fw, fh, fstride, fmt);
    return 0;
}
