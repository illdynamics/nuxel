/* nuxel-wl-snapshot — one-shot wlr-screencopy capture of the live Nuxel
 * compositor, written as a PPM.  It does NOT open /dev/fb0 and never becomes a
 * framebuffer owner: it is an ordinary Wayland client asking phoc for the same
 * composited frame nuxel-wl-fb presents.  Diagnostic only.
 *
 * build (host):
 *   wayland-scanner client-header wlr-screencopy-unstable-v1.xml gen/...h
 *   wayland-scanner private-code  wlr-screencopy-unstable-v1.xml gen/...c
 *   cc -O2 -o nuxel-wl-snapshot nuxel-wl-snapshot.c gen/...c $(pkg-config --cflags --libs wayland-client)
 */
#define _GNU_SOURCE
#include <errno.h>
#include <fcntl.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/mman.h>
#include <sys/stat.h>
#include <time.h>
#include <unistd.h>
#include <wayland-client.h>
#include "wlr-screencopy-unstable-v1-client-protocol.h"

static struct wl_compositor *compositor;
static struct wl_shm *shm;
static struct zwlr_screencopy_manager_v1 *scm;
static struct wl_output *output;
static int have_buffer, ready, failed;
static int fb_w, fb_h, fb_stride;
static uint32_t fb_format;
static void *fb_data;
static size_t fb_len;
static int out_fd = -1;
static const char *out_path;

static void frame_buffer(void *d, struct zwlr_screencopy_frame_v1 *f,
                         uint32_t fmt, uint32_t w, uint32_t h, uint32_t stride) {
  (void)d; (void)f;
  fb_format = fmt; fb_w = (int)w; fb_h = (int)h; fb_stride = (int)stride;
  fb_len = (size_t)stride * h;
  out_fd = memfd_create("nuxel-snapshot", MFD_CLOEXEC);
  if (out_fd < 0 || ftruncate(out_fd, (off_t)fb_len) < 0) {
    fprintf(stderr, "SNAPSHOT_SHM_FAIL errno=%d\n", errno); failed = 1; return;
  }
  fb_data = mmap(NULL, fb_len, PROT_READ | PROT_WRITE, MAP_SHARED, out_fd, 0);
  if (fb_data == MAP_FAILED) { fb_data = NULL; fprintf(stderr, "SNAPSHOT_MMAP_FAIL errno=%d\n", errno); failed = 1; return; }
  have_buffer = 1;
}
static void frame_flags(void *d, struct zwlr_screencopy_frame_v1 *f, uint32_t flags) { (void)d; (void)f; (void)flags; }
static uint32_t ready_hi, ready_lo, ready_ns;
static void frame_ready_cb(void *d, struct zwlr_screencopy_frame_v1 *f, uint32_t sec_hi, uint32_t sec_lo, uint32_t nsec) {
  (void)d; (void)f; ready_hi = sec_hi; ready_lo = sec_lo; ready_ns = nsec; ready = 1;
}
static void frame_failed_cb(void *d, struct zwlr_screencopy_frame_v1 *f) { (void)d; (void)f; failed = 1; }
static void frame_damage(void *d, struct zwlr_screencopy_frame_v1 *f, uint32_t x, uint32_t y, uint32_t w, uint32_t h) { (void)d;(void)f;(void)x;(void)y;(void)w;(void)h; }
static void frame_linux_dmabuf(void *d, struct zwlr_screencopy_frame_v1 *f, uint32_t fmt, uint32_t w, uint32_t h) { (void)d;(void)f;(void)fmt;(void)w;(void)h; }
static void frame_buffer_done(void *d, struct zwlr_screencopy_frame_v1 *f) { (void)d;(void)f; }
static const struct zwlr_screencopy_frame_v1_listener frame_listener = {
  .buffer = frame_buffer, .flags = frame_flags, .ready = frame_ready_cb,
  .failed = frame_failed_cb, .damage = frame_damage,
  .linux_dmabuf = frame_linux_dmabuf, .buffer_done = frame_buffer_done,
};

static void reg_global(void *d, struct wl_registry *r, uint32_t name,
                       const char *iface, uint32_t ver) {
  (void)d;
  if (!strcmp(iface, wl_shm_interface.name)) shm = wl_registry_bind(r, name, &wl_shm_interface, 1);
  else if (!strcmp(iface, zwlr_screencopy_manager_v1_interface.name))
    scm = wl_registry_bind(r, name, &zwlr_screencopy_manager_v1_interface, ver < 3 ? ver : 3);
  else if (!strcmp(iface, wl_output_interface.name))
    output = wl_registry_bind(r, name, &wl_output_interface, ver < 2 ? ver : 2);
  else if (!strcmp(iface, wl_compositor_interface.name))
    compositor = wl_registry_bind(r, name, &wl_compositor_interface, 1);
}
static void reg_remove(void *d, struct wl_registry *r, uint32_t name) { (void)d;(void)r;(void)name; }
static const struct wl_registry_listener reg_listener = { reg_global, reg_remove };

static int write_ppm(const char *path) {
  if (!fb_data || !fb_w || !fb_h) return -1;
  FILE *f = fopen(path, "wb");
  if (!f) { fprintf(stderr, "SNAPSHOT_OPEN_FAIL path=%s errno=%d\n", path, errno); return -1; }
  fprintf(f, "P6\n%d %d\n255\n", fb_w, fb_h);
  uint64_t hash = 1469598103934665603ULL;
  for (int y = 0; y < fb_h; y++) {
    const uint32_t *row = (const uint32_t *)((const uint8_t *)fb_data + (size_t)y * fb_stride);
    for (int x = 0; x < fb_w; x++) {
      uint32_t p = row[x];
      unsigned char rgb[3] = { (unsigned char)((p >> 16) & 0xff),
                               (unsigned char)((p >> 8) & 0xff),
                               (unsigned char)(p & 0xff) };
      hash ^= p; hash *= 1099511628211ULL;
      fwrite(rgb, 1, 3, f);
    }
  }
  fclose(f);
  fprintf(stderr, "SNAPSHOT_OK path=%s w=%d h=%d stride=%d format=0x%08x fnv64=%016llx frame_ts=%u.%09u\n",
          path, fb_w, fb_h, fb_stride, fb_format, (unsigned long long)hash, ready_lo, ready_ns);
  return 0;
}

int main(int argc, char **argv) {
  out_path = argc > 1 ? argv[1] : "/tmp/nuxel-snapshot.ppm";
  struct wl_display *dpy = wl_display_connect(NULL);
  if (!dpy) { fprintf(stderr, "SNAPSHOT_CONNECT_FAIL errno=%d\n", errno); return 2; }
  struct wl_registry *reg = wl_display_get_registry(dpy);
  wl_registry_add_listener(reg, &reg_listener, NULL);
  for (int i = 0; i < 3; i++) if (wl_display_roundtrip(dpy) < 0) { fprintf(stderr, "SNAPSHOT_ROUNDTRIP_FAIL\n"); return 3; }
  if (!shm || !scm || !output) { fprintf(stderr, "SNAPSHOT_MISSING_GLOBAL shm=%d scm=%d output=%d\n", !!shm, !!scm, !!output); return 4; }
  struct zwlr_screencopy_frame_v1 *frame = zwlr_screencopy_manager_v1_capture_output(scm, 0, output);
  zwlr_screencopy_frame_v1_add_listener(frame, &frame_listener, NULL);
  while (!ready && !failed) {
    if (wl_display_dispatch(dpy) < 0) { fprintf(stderr, "SNAPSHOT_DISPATCH_FAIL errno=%d\n", errno); return 5; }
    if (have_buffer && !ready && !failed) {
      /* use the shm pool path expected by the protocol: wl_shm_pool + wl_buffer */
      struct wl_shm_pool *pool = wl_shm_create_pool(shm, out_fd, (int)fb_len);
      struct wl_buffer *buf = wl_shm_pool_create_buffer(pool, 0, fb_w, fb_h, fb_stride, fb_format);
      zwlr_screencopy_frame_v1_copy(frame, buf);
      wl_buffer_destroy(buf);
      wl_shm_pool_destroy(pool);
      have_buffer = 0;
    }
  }
  if (failed || !ready) { fprintf(stderr, "SNAPSHOT_FRAME_FAILED failed=%d ready=%d\n", failed, ready); return 6; }
  int rc = write_ppm(out_path);
  zwlr_screencopy_frame_v1_destroy(frame);
  if (fb_data) munmap(fb_data, fb_len);
  if (out_fd >= 0) close(out_fd);
  wl_display_disconnect(dpy);
  return rc ? 7 : 0;
}
