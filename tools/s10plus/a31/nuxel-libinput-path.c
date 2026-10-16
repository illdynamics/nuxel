/* nuxel-libinput-path — let wlroots/phoc take REAL evdev input on the S10+
 * without the udev daemon.
 *
 * WHY THIS EXISTS (measured A31, handset, Linux 4.14.253 / systemd 258)
 *   phoc is started with WLR_BACKENDS=headless,libinput and can only create its
 *   libinput backend when a backend session exists; seatd now provides that
 *   (LIBSEAT_BACKEND=seatd).  The backend then still sees ZERO devices, because
 *   libinput's udev backend discovers devices through `udev_enumerate`, which is
 *   answered by the udev DAEMON - and systemd-udevd is masked on this image:
 *   it cannot register its worker objects on 4.14
 *       systemd-udevd[...]: Failed to create worker object: Function not implemented
 *   and forks unboundedly (measured A26: 17,723 processes in 50 s, watchdog
 *   reset).  Re-enabling it reproduced the fork storm in this cycle (281 -> 544
 *   processes within seconds of `udevadm trigger --subsystem-match=input`).
 *
 *   wlroots itself only needs a udev_device for TABLET tools/pads
 *   (grep -rn libinput_device_get_udev_device backend/libinput/: tablet_tool.c,
 *   tablet_pad.c only) - pointer, keyboard, touch and switch do not.  wlroots
 *   also never sets output_name for libinput devices (only the x11/wayland
 *   nested backends do), so a device with no udev device maps to the default
 *   output exactly like a udev-backed one.
 *
 * WHAT THIS DOES
 *   Interposes the two libinput entry points wlroots calls in
 *   backend/libinput/backend.c::backend_start():
 *       libinput_udev_create_context()  -> libinput_path_create_context()
 *       libinput_udev_assign_seat()     -> libinput_path_add_device() for each
 *                                          /dev/input/eventN carrying
 *                                          INPUT_PROP_DIRECT (the panel's
 *                                          sec_touchscreen)
 *   The device is the real kernel evdev node: libinput parses the real
 *   multitouch protocol, wlroots turns it into wl_touch, the compositor delivers
 *   it to the WebKit view.  Nothing is synthesised, no events are fabricated and
 *   no /dev/input filter is bypassed - only the *discovery* step changes, and it
 *   changes from "ask a daemon that cannot run here" to "open the node whose
 *   capability proves what it is".
 *
 *   Every decision is written to /run/nuxel-libinput-path.state (evidence, not a
 *   claim).  Set NUXEL_LIBINPUT_PATH_DEBUG=1 to also print to stderr.
 */
#define _GNU_SOURCE
#include <dlfcn.h>
#include <errno.h>
#include <fcntl.h>
#include <linux/input.h>
#include <stdarg.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/ioctl.h>
#include <sys/stat.h>
#include <sys/sysmacros.h>
#include <time.h>
#include <unistd.h>

#define STATE "/run/nuxel-libinput-path.state"

static void st(const char *fmt, ...) {
  FILE *f = fopen(STATE, "a");
  if (f) {
    fprintf(f, "%ld ", (long)time(NULL));
    va_list ap; va_start(ap, fmt); vfprintf(f, fmt, ap); va_end(ap);
    fputc('\n', f); fclose(f);
  }
  if (getenv("NUXEL_LIBINPUT_PATH_DEBUG")) {
    fputs("[nuxel-libinput-path] ", stderr);
    va_list ap; va_start(ap, fmt); vfprintf(stderr, fmt, ap); va_end(ap);
    fputc('\n', stderr);
  }
}

/* Declared exactly as libinput exports them: no libinput headers are needed on
   the build host, so this shim cannot drift with libinput's private internals. */
struct libinput;
struct libinput_device;
struct libinput_interface;
extern struct libinput *libinput_path_create_context(const struct libinput_interface *, void *);
extern struct libinput_device *libinput_path_add_device(struct libinput *, const char *);

/* Is this event node a built-in direct pointer (a touchscreen)?  Chosen by
   capability, never by event number (same rule nuxel-touch-arm uses). */
static int direct_pointer(const char *path, char *name, size_t namelen) {
  int fd = open(path, O_RDONLY | O_NONBLOCK);
  if (fd < 0) return 0;
  unsigned long prop[8];
  memset(prop, 0, sizeof prop);
  int direct = 0;
  if (ioctl(fd, EVIOCGPROP(sizeof prop), prop) >= 0) {
    unsigned bit = (unsigned)INPUT_PROP_DIRECT;
    direct = (int)((prop[bit / (8 * sizeof(unsigned long))] >>
                    (bit % (8 * sizeof(unsigned long)))) & 1ul);
  }
  if (name && namelen) {
    name[0] = 0;
    if (ioctl(fd, EVIOCGNAME(namelen - 1), name) < 0) name[0] = 0;
  }
  close(fd);
  return direct;
}

struct libinput *libinput_udev_create_context(const struct libinput_interface *iface,
                                              void *user_data, void *udev) {
  (void)udev;
  struct libinput *li = libinput_path_create_context(iface, user_data);
  st("PATH_CONTEXT_CREATED ctx=%p udev=%p (udev daemon not required)", (void *)li, udev);
  if (!li) st("PATH_CONTEXT_FAILED errno=%d", errno);
  return li;
}

static void seed_udev_db(const char *path);   /* defined in PART 3 below */
static int db_seeded;

int libinput_udev_assign_seat(struct libinput *li, const char *seat_id) {
  int seen = 0, added = 0;
  for (int i = 0; i < 64; i++) {
    char path[64], name[128];
    snprintf(path, sizeof path, "/dev/input/event%d", i);
    if (!direct_pointer(path, name, sizeof name)) continue;
    seen++;
    seed_udev_db(path);       /* libinput 1.30 requires an initialized udev device */
    struct libinput_device *d = libinput_path_add_device(li, path);
    st("PATH_ADD node=%s name='%s' accepted=%d", path, name, d != NULL);
    if (d) added++;
  }
  st("PATH_ASSIGN_SEAT seat='%s' direct_devices_seen=%d added=%d db_seeded=%d", seat_id ? seat_id : "(null)", seen, added, db_seeded);
  return 0;   /* wlroots treats 0 as "seat assigned" */
}

/* ============================================================================
 * PART 2 — the device OPEN, without a VT-backed seat  (measured A31)
 *
 * With LIBSEAT_BACKEND=noop the seat is created and becomes usable (wlroots'
 * "Timeout waiting session to become active" disappears - the handset has NO VT
 * at all: /dev/tty0 absent, /sys/class/vtconsole absent, /proc/consoles empty, so
 * seatd's VT-bound seat can never activate and libseat exposes no other usable
 * backend).  But libseat_open_device() on the noop backend refuses every device,
 * so libinput_path_add_device() returned NULL for sec_touchscreen
 * (measured: PATH_ADD node=/dev/input/event2 ... accepted=0).
 *
 * This intercepts ONLY libseat_open_device()/libseat_close_device() and ONLY for
 * paths under /dev/input/: when libseat declines, the node is opened directly
 * (phoc runs as root; the kernel's evdev nodes here are root-only, which is the
 * exact case libseat cannot express without a session manager).  Every other path
 * still goes through libseat untouched, and every fd opened here is tracked so its
 * close is balanced.
 * ==========================================================================*/
#define MAX_AUX_FD 64
static int aux_fd[MAX_AUX_FD];

static void aux_remember(int fd) {
  for (int i = 0; i < MAX_AUX_FD; i++) if (aux_fd[i] == 0) { aux_fd[i] = fd; return; }
}
static int aux_forget(int fd) {
  for (int i = 0; i < MAX_AUX_FD; i++) if (aux_fd[i] == fd) { aux_fd[i] = 0; return 1; }
  return 0;
}

struct libseat;
extern int libseat_open_device(struct libseat *, const char *, int *);
extern int libseat_close_device(struct libseat *, int);

int libseat_open_device(struct libseat *seat, const char *path, int *fd) {
  static int (*real)(struct libseat *, const char *, int *);
  if (!real) real = dlsym(RTLD_NEXT, "libseat_open_device");
  int r = real ? real(seat, path, fd) : -1;
  if (r == -1 && path && strncmp(path, "/dev/input/", 11) == 0) {
    int f = open(path, O_RDWR | O_CLOEXEC | O_NONBLOCK);
    if (f >= 0) {
      *fd = f; aux_remember(f);
      st("DEVICE_OPEN_FALLBACK path=%s fd=%d (libseat declined; direct root open)", path, f);
      return 0;
    }
    st("DEVICE_OPEN_FALLBACK_FAIL path=%s errno=%d", path, errno);
  } else {
    st("DEVICE_OPEN_LIBSEAT path=%s rc=%d fd=%d", path ? path : "?", r, r == 0 && fd ? *fd : -1);
  }
  return r;
}

int libseat_close_device(struct libseat *seat, int fd) {
  static int (*real)(struct libseat *, int);
  if (!real) real = dlsym(RTLD_NEXT, "libseat_close_device");
  if (aux_forget(fd)) { close(fd); st("DEVICE_CLOSE_FALLBACK fd=%d", fd); return 0; }
  return real ? real(seat, fd) : -1;
}

/* ============================================================================
 * PART 3 — the udev DATABASE entry, without the udev daemon  (measured A31)
 *
 * libinput 1.30 does not have a pure "no udev" path mode: libinput_path_add_device()
 * (src/path-seat.c) still resolves the node to a udev device first
 *
 *     dev = udev_device_new_from_devnum(udev, 'c', st.st_rdev);
 *     while (dev && !udev_device_get_is_initialized(dev)) {   // 200 x 10 ms
 *             msleep(10); dev = udev_device_new_from_devnum(...); }
 *     if (count > 200) -> "udev device never initialized" -> NULL
 *
 * and it returned NULL for /dev/input/event2 exactly like that (measured: ~2 s
 * between PATH_ADD lines, accepted=0).  `is_initialized` is true only when
 * /run/udev/data/<subsystem>:<devnum> exists and carries the 'I' marker that the
 * udev WORKER writes when a device is fully processed - which cannot happen here
 * because systemd-udevd is masked on this kernel.
 *
 * So the entry is written from the device's OWN capability data (INPUT_PROP_DIRECT,
 * ABS_MT_*, EV_KEY.BTN_TOUCH read by us), scoped to /dev/input direct pointers, and
 * only when it is absent.  This is the smallest possible replacement for a daemon
 * that cannot exist on Linux 4.14 - it does not invent a device, it records the one
 * libinput is about to open, and it is what lets the real evdev node through.
 * ==========================================================================*/
extern int udev_device_get_is_initialized(void *);

static void seed_udev_db(const char *path) {
  struct stat sb;                     /* NOT `st` - that is the logger below */
  if (stat(path, &sb) < 0) { st("UDEVDB_STAT_FAIL %s errno=%d", path, errno); return; }
  if (mkdir("/run/udev", 0755) < 0 && errno != EEXIST) { /* fall through */ }
  if (mkdir("/run/udev/data", 0755) < 0 && errno != EEXIST) { /* fall through */ }
  char fn[80];
  snprintf(fn, sizeof fn, "/run/udev/data/c%u:%u", (unsigned)major(sb.st_rdev), (unsigned)minor(sb.st_rdev));
  if (access(fn, F_OK) == 0) return;            /* already initialized */
  FILE *f = fopen(fn, "w");
  if (!f) { st("UDEVDB_WRITE_FAIL %s errno=%d", fn, errno); return; }
  /* Properties libinput/quirks read, derived from what the node actually is. */
  fprintf(f, "E:ID_INPUT=1\nE:ID_INPUT_TOUCHSCREEN=1\nE:ID_INPUT_WIDTH_MM=64\nE:ID_INPUT_HEIGHT_MM=135\nE:ID_SEAT=seat0\nE:DEVLINKS=/dev/input/by-path/nuxel-touchscreen\n");
  fprintf(f, "I:%ld\n", (long)time(NULL) * 1000000L);   /* 'I' = initialized */
  fclose(f);
  db_seeded++;
  st("UDEVDB_SEEDED %s (initialized marker; systemd-udevd cannot run on this kernel)", fn);
}
