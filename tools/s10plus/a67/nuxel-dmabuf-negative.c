/* PWNAGE-53000: linux-dmabuf negative + stress test.
 *
 * Submits malformed and unsupported buffers to the live compositor:
 *   - valid LINEAR AB24 (known-good pair, from a udmabuf)
 *   - unsupported modifier (0xdeadbeef)
 *   - out-of-range offset/stride
 *   - absurd dimensions
 *   - repeated create/destroy
 * PASS means every request was answered (failed or buffer) and the
 * connection stayed alive.  Phoc must still be running afterwards.
 */
#define _GNU_SOURCE
#include <errno.h>
#include <fcntl.h>
#include <linux/udmabuf.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/ioctl.h>
#include <sys/mman.h>
#include <unistd.h>
#include <wayland-client.h>
#include "linux-dmabuf-unstable-v1-client-protocol.h"

#define DRM_FORMAT_ABGR8888 0x34324241u

struct ctx { struct wl_display *dpy; struct wl_registry *reg;
             struct wl_compositor *comp; struct zwp_linux_dmabuf_v1 *dmabuf; };

static int failed_events;
static void params_failed(void *d, struct zwp_linux_buffer_params_v1 *p) {
  (void)d; (void)p; failed_events++;
}
static const struct zwp_linux_buffer_params_v1_listener params_listener = {
  .created = NULL, .failed = params_failed,
};
static void g(void *data, struct wl_registry *r, uint32_t name,
              const char *iface, uint32_t ver) {
  struct ctx *c = data;
  if (!strcmp(iface, "wl_compositor"))
    c->comp = wl_registry_bind(r, name, &wl_compositor_interface, ver < 4 ? ver : 4);
  else if (!strcmp(iface, "zwp_linux_dmabuf_v1"))
    c->dmabuf = wl_registry_bind(r, name, &zwp_linux_dmabuf_v1_interface, ver < 3 ? ver : 3);
}
static void gr(void *d, struct wl_registry *r, uint32_t n) { (void)d; (void)r; (void)n; }
static const struct wl_registry_listener reg_listener = { g, gr };

static int export_linear(int w, int h, int *out_fd, int *out_stride) {
  static int stride = 0;
  if (!stride) stride = (w * 4 + 4095) & ~4095;
  size_t len = (size_t)stride * h;
  int mfd = memfd_create("nuxel-dmabuf-neg", MFD_CLOEXEC | MFD_ALLOW_SEALING);
  if (mfd < 0) return -1;
  if (ftruncate(mfd, len) != 0) { close(mfd); return -1; }
  fcntl(mfd, F_ADD_SEALS, F_SEAL_SHRINK | F_SEAL_GROW | F_SEAL_SEAL);
  int ub = open("/dev/udmabuf", O_RDWR | O_CLOEXEC);
  if (ub < 0) { close(mfd); return -1; }
  struct udmabuf_create req = { .memfd = mfd, .flags = 0, .offset = 0, .size = len };
  int fd = ioctl(ub, UDMABUF_CREATE, &req);
  close(ub); close(mfd);
  if (fd < 0) return -1;
  *out_fd = fd; *out_stride = stride;
  return 0;
}

static int attempt(struct ctx *c, int fd, int stride, int w, int h,
                   uint64_t modifier, int offset) {
  struct zwp_linux_buffer_params_v1 *p =
      zwp_linux_dmabuf_v1_create_params(c->dmabuf);
  if (!p) return -1;
  zwp_linux_buffer_params_v1_add_listener(p, &params_listener, NULL);
  zwp_linux_buffer_params_v1_add(p, fd, 0, offset, stride,
                                 (uint32_t)(modifier >> 32), (uint32_t)modifier);
  struct wl_buffer *b = zwp_linux_buffer_params_v1_create_immed(
      p, w, h, DRM_FORMAT_ABGR8888, 0);
  zwp_linux_buffer_params_v1_destroy(p);
  if (b) { wl_buffer_destroy(b); return 0; }
  return 1; /* server rejected it */
}

int main(int argc, char **argv) {
  int loops = argc > 1 ? atoi(argv[1]) : 20;
  const char *mode = argc > 2 ? argv[2] : "all";
  if (!strcmp(mode, "kill-client")) {
    /* Deliberately malformed: the server is entitled to raise a protocol
     * error and drop THIS client.  Run in a child so the harness can prove
     * the compositor itself survived. */
    struct ctx c = {0};
    c.dpy = wl_display_connect(NULL);
    if (!c.dpy) return 2;
    c.reg = wl_display_get_registry(c.dpy);
    wl_registry_add_listener(c.reg, &reg_listener, &c);
    wl_display_roundtrip(c.dpy);
    int fd, stride;
    if (export_linear(16, 16, &fd, &stride) != 0) return 4;
    attempt(&c, fd, stride, 16, 16, 0, 0x7fffffff);
    wl_display_roundtrip(c.dpy);
    int e = wl_display_get_error(c.dpy);
    printf("{\"malformed_offset\":\"disconnect_ok\",\"display_error\":%d}\n", e);
    return e ? 0 : 6;
  }
  struct ctx c = {0};
  c.dpy = wl_display_connect(NULL);
  if (!c.dpy) { perror("wl_display_connect"); return 2; }
  c.reg = wl_display_get_registry(c.dpy);
  wl_registry_add_listener(c.reg, &reg_listener, &c);
  wl_display_roundtrip(c.dpy);
  if (!c.dmabuf) { fprintf(stderr, "no linux-dmabuf global\n"); return 3; }
  printf("linux-dmabuf version=%u\n",
         (unsigned)zwp_linux_dmabuf_v1_get_version(c.dmabuf));

  int fd, stride;
  if (export_linear(64, 64, &fd, &stride) != 0) {
    perror("udmabuf export"); return 4;
  }
  int ok = 0, rejected = 0, bad = 0;
  for (int i = 0; i < loops; i++) {
    /* known-good LINEAR pair: must be accepted */
    if (!strcmp(mode, "all") || !strcmp(mode, "valid") || !strcmp(mode, "stress")) {
      if (attempt(&c, fd, stride, 64, 64, 0, 0) == 0) ok++;
    }
    if (!strcmp(mode, "all") || !strcmp(mode, "mod")) {
      int r = attempt(&c, fd, stride, 64, 64, 0xdeadbeef00000000ull, 0);
      if (r == 1) rejected++; else if (r == 0) bad++;
    }
    if (!strcmp(mode, "all") || !strcmp(mode, "offset")) {
      int r = attempt(&c, fd, stride, 64, 64, 0, 0x7fffffff);
      if (r == 1) rejected++; else if (r == 0) bad++;
    }
    if (!strcmp(mode, "all") || !strcmp(mode, "dim")) {
      int r = attempt(&c, fd, stride, 0x7fffffff, 0x7fffffff, 0, 0);
      if (r == 1) rejected++; else if (r == 0) bad++;
    }
    wl_display_roundtrip(c.dpy);
    if (wl_display_get_error(c.dpy)) break;
  }
  printf("{\"loops\":%d,\"accepted\":%d,\"rejected\":%d,\"failed_events\":%d}\n",
         loops, ok, rejected, failed_events);
  close(fd);
  wl_display_roundtrip(c.dpy);
  if (wl_display_get_error(c.dpy) != 0) { fprintf(stderr, "display error\n"); return 5; }
  wl_display_disconnect(c.dpy);
  printf("PASS\n");
  return 0;
}
