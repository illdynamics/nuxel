/* nuxel-scroll-workload — deterministic pointer/wheel workload for A/B runs.
 *
 * Uses zwlr_virtual_pointer_manager_v1 (real compositor input, no touch device
 * writes).  It moves the pointer over the launcher content and emits wheel
 * events for a bounded duration, alternating direction.  It never clicks a
 * destructive control and never sends keys.
 *
 * Build on the phone:
 *   wayland-scanner client-header wlr-virtual-pointer-unstable-v1.xml vptr.h
 *   wayland-scanner private-code  wlr-virtual-pointer-unstable-v1.xml vptr.c
 *   cc -O2 -o nuxel-scroll-workload nuxel-scroll-workload.c vptr.c \
 *      $(pkg-config --cflags --libs wayland-client)
 *
 * Usage: nuxel-scroll-workload [seconds] [x] [y]
 */
#define _GNU_SOURCE
#include <wayland-client.h>
#include <linux/input-event-codes.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <unistd.h>
#include "wlr-virtual-pointer-unstable-v1-client-protocol.h"

static struct zwlr_virtual_pointer_manager_v1 *mgr;

static void global(void *d, struct wl_registry *r, uint32_t name,
                   const char *iface, uint32_t ver) {
  (void)d;
  if (!strcmp(iface, zwlr_virtual_pointer_manager_v1_interface.name))
    mgr = wl_registry_bind(r, name, &zwlr_virtual_pointer_manager_v1_interface,
                           ver < 2 ? ver : 2);
}
static void global_remove(void *d, struct wl_registry *r, uint32_t n) {
  (void)d; (void)r; (void)n;
}
static const struct wl_registry_listener listener = {global, global_remove};

static uint32_t now_ms(void) {
  struct timespec ts;
  clock_gettime(CLOCK_MONOTONIC, &ts);
  return (uint32_t)(ts.tv_sec * 1000 + ts.tv_nsec / 1000000);
}

int main(int argc, char **argv) {
  int seconds = argc > 1 ? atoi(argv[1]) : 20;
  int x = argc > 2 ? atoi(argv[2]) : 360;
  int y = argc > 3 ? atoi(argv[3]) : 620;
  if (seconds < 1) seconds = 1;
  struct wl_display *dpy = wl_display_connect(NULL);
  if (!dpy) { fprintf(stderr, "no wayland display\n"); return 2; }
  struct wl_registry *reg = wl_display_get_registry(dpy);
  wl_registry_add_listener(reg, &listener, NULL);
  wl_display_roundtrip(dpy);
  if (!mgr) { fprintf(stderr, "no virtual pointer manager\n"); return 3; }
  struct zwlr_virtual_pointer_v1 *p = zwlr_virtual_pointer_manager_v1_create_virtual_pointer(mgr, NULL);
  if (!p) { fprintf(stderr, "create pointer failed\n"); return 4; }
  /* Absolute motion needs the version-2 request; fall back to relative. */
  if (zwlr_virtual_pointer_v1_get_version(p) >= 2)
    zwlr_virtual_pointer_v1_motion_absolute(p, now_ms(), x, y, 720, 1520);
  else
    zwlr_virtual_pointer_v1_motion(p, now_ms(), wl_fixed_from_int(x), wl_fixed_from_int(y));
  wl_display_flush(dpy);
  usleep(200000);
  int events = 0;
  time_t end = time(NULL) + seconds;
  int dir = 1;
  while (time(NULL) < end) {
    /* Two wheel notches 20 times/s is a realistic finger-scroll cadence. */
    for (int i = 0; i < 2; i++) {
      zwlr_virtual_pointer_v1_axis(p, now_ms(), WL_POINTER_AXIS_VERTICAL_SCROLL,
                                   wl_fixed_from_int(dir * 15));
      events++;
    }
    if ((events / 40) % 2 == 1) dir = -1; else dir = 1;
    wl_display_flush(dpy);
    usleep(50000);
  }
  zwlr_virtual_pointer_v1_destroy(p);
  wl_display_roundtrip(dpy);
  wl_display_disconnect(dpy);
  printf("SCROLL_WORKLOAD seconds=%d events=%d x=%d y=%d\n", seconds, events, x, y);
  return 0;
}
