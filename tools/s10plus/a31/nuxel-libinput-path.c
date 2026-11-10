/* ==========================================================================
 * nuxel-libinput-path — capability-based libinput discovery for the Nuxel
 *                       S10+ (beyond2lte, Exynos 9820) phone stack.
 *
 * FILE IDENTITY (enforced by tools/s10plus/a33/tests/test-libinput-parity.py)
 *   tools/s10plus/a33/nuxel-libinput-path.c   <- authoritative source (A33)
 *   tools/s10plus/a31/nuxel-libinput-path.c   <- the deployed copy, compiled by
 *                                                tools/s10plus/a31/build-a31.sh
 *   The two files are byte-identical on purpose: one implementation, one gate.
 *   Change one without the other and the offline tests fail.
 *
 * WHY THIS EXISTS (measured A31 on the handset, Linux 4.14.253 / systemd 258)
 *   phoc is started with WLR_BACKENDS=headless,libinput and can only create its
 *   libinput backend when a backend session exists; seatd provides that
 *   (LIBSEAT_BACKEND=seatd).  The backend then still saw ZERO devices, because
 *   libinput's udev backend discovers devices through `udev_enumerate`, which is
 *   answered by the udev DAEMON — and systemd-udevd stays MASKED on this image:
 *   it cannot register its worker objects on 4.14
 *       systemd-udevd[...]: Failed to create worker object: Function not implemented
 *   and forks unboundedly (measured A26: 17,723 processes in 50 s, watchdog
 *   reset; re-measured in A31: 281 -> 544 processes within seconds of
 *   `udevadm trigger --subsystem-match=input`).  That is why un-masking udevd is
 *   NOT an option on this kernel and why this shim, not a udev replacement, is
 *   the deployment path.  The durable kernel-side fix (an sd-event child-watch
 *   compat patch, or a kernel with the missing syscalls) is tracked outside this
 *   file and is NOT deployed.
 *
 *   wlroots itself only needs a udev_device for TABLET tools/pads
 *   (backend/libinput/tablet_tool.c, tablet_pad.c); pointer, keyboard, touch and
 *   switch do not.  wlroots also never sets output_name for libinput devices, so
 *   a device without a udev device maps to the default output exactly like a
 *   udev-backed one.
 *
 * WHAT THIS DOES
 *   Interposes the libinput entry points wlroots calls in
 *   backend/libinput/backend.c::backend_start():
 *       libinput_udev_create_context()  -> libinput_path_create_context()
 *       libinput_udev_assign_seat()     -> libinput_path_add_device() for every
 *                                          node that PROVES it is a direct touch
 *                                          surface (INPUT_PROP_DIRECT + ABS_MT)
 *   The device is the real kernel evdev node: libinput parses the real
 *   multitouch protocol, wlroots turns it into wl_touch, the compositor delivers
 *   it to the WebKit view.  Nothing is synthesised and no events are fabricated —
 *   only the *discovery* step changes, from "ask a daemon that cannot run here"
 *   to "open the node whose capabilities prove what it is".
 *
 * A33 HARDENING (mission rule: never assume /dev/input/eventN)
 *   * Enumeration is a real directory scan of /dev/input (entries parsed at
 *     runtime, sorted numerically).  No event node NUMBER is written in this
 *     file.  Gate: tools/s10plus/a33/tests/test-no-eventn-literal.py.
 *   * Acceptance is decided by CAPABILITY ONLY, in this order:
 *       1. EVIOCGPROP        -> INPUT_PROP_DIRECT must be set
 *       2. EVIOCGBIT(EV_ABS) -> ABS_MT_POSITION_X and _Y  (or, as a documented
 *          fallback, EVIOCGBIT(EV_KEY).BTN_TOUCH with legacy ABS_X/ABS_Y)
 *       3. EVIOCGABS         -> the ABS_MT range must not be degenerate
 *     Every candidate — accepted or rejected — is logged with its reason to
 *     /run/nuxel-libinput-path.state.  Evidence, not a claim.
 *   * Device ABSENCE (the charger-mode/LPM boot, where sec_ts never probes and no
 *     DIRECT node exists at all) no longer leaves a dead compositor:
 *     assign_seat logs ZERO_DEVICES, returns 0, and a bounded inotify watcher
 *     adds the panel the moment it appears and removes it when it goes away.
 *   * All libinput calls happen on the thread that calls libinput_dispatch()
 *     (the compositor's main loop).  The watcher thread only queues events under
 *     a mutex; at most 64 paths are tracked and the queue is a bounded ring, so
 *     an unbounded device storm cannot grow memory or block the compositor.
 *   * Seat handling keeps the seatd/libseat path: libseat_open_device() and
 *     libseat_close_device() are interposed for /dev/input paths only, because
 *     this handset has NO VT (/dev/tty0, /sys/class/vtconsole, /proc/consoles
 *     absent), so a VT-bound seat can never activate and libseat's noop backend
 *     refuses device opens.  With LIBSEAT_BACKEND=seatd and a usable seat the
 *     libseat call wins; the fallback exists for the noop-seat case measured on
 *     the handset (phoc runs as root; the evdev nodes are root-only).
 *
 * OFFLINE TESTABILITY (no phone, no devboard, no /dev/input)
 *   The selection + hotplug decisions are pure functions of device metadata, so
 *   the same source file compiles into an offline test binary:
 *       cc -DNUXEL_SHIM_SELFTEST -o selftest nuxel-libinput-path.c
 *       ./selftest --scan  <fixture-root>        # prints SEL/REJECT + SELECTED
 *       ./selftest --hotplug <fixture-root> <ops-file>
 *   Fixture mode reads the same metadata from a synthetic sysfs/uevent tree
 *   (tests/fixtures/).  The evdev ioctl path is compiled out on a host without
 *   <linux/input.h>; the decision logic under test is identical either way.
 * ==========================================================================*/
#define _GNU_SOURCE
#include <ctype.h>
#include <dirent.h>
#include <errno.h>
#include <fcntl.h>
#include <stdarg.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <time.h>
#include <unistd.h>

#if defined(__linux__) && defined(__has_include)
#  if __has_include(<linux/input.h>)
#    define NUXEL_HAVE_EVDEV 1
#  endif
#endif

#ifdef NUXEL_HAVE_EVDEV
#  include <linux/input.h>
#  include <sys/ioctl.h>
#  include <sys/sysmacros.h>
#endif

#ifndef NUXEL_SHIM_SELFTEST
#  include <dlfcn.h>
#  include <pthread.h>
#  include <sys/eventfd.h>
#  ifdef NUXEL_HAVE_EVDEV
#    include <sys/inotify.h>
#    define NUXEL_HAVE_INOTIFY 1
#  endif
#endif

/* --- ABI constants (stable kernel ABI; local copies keep this file buildable
 *     on a host that has no kernel headers at all) ------------------------- */
#define NUXEL_EV_KEY              0x01
#define NUXEL_EV_REL              0x02
#define NUXEL_EV_ABS              0x03
#define NUXEL_REL_X               0x00
#define NUXEL_REL_Y               0x01
#define NUXEL_BTN_LEFT            0x110
#define NUXEL_BTN_RIGHT           0x111
#define NUXEL_BTN_MIDDLE          0x112
#define NUXEL_BTN_TOUCH           0x14a
#define NUXEL_ABS_X               0x00
#define NUXEL_ABS_Y               0x01
#define NUXEL_ABS_MT_SLOT         0x2f
#define NUXEL_ABS_MT_POSITION_X   0x35
#define NUXEL_ABS_MT_POSITION_Y   0x36
#define NUXEL_KEY_ENTER           28
#define NUXEL_KEY_A               30
#define NUXEL_KEY_LEFTSHIFT       42
#define NUXEL_KEY_Z               44
#define NUXEL_KEY_SPACE           57
#define NUXEL_INPUT_PROP_DIRECT   1

/* linux/bitops.h's BITS_TO_LONGS is a kernel-internal helper and is NOT part of
   the uapi headers this file may include, so the word count is expressed here. */
#define NUXEL_WORDS(n) (((n) + 63) / 64)

#ifdef NUXEL_HAVE_EVDEV
/* Fail the build if a local constant ever drifts from the kernel header. */
_Static_assert(NUXEL_EV_KEY == EV_KEY, "EV_KEY drift");
_Static_assert(NUXEL_EV_REL == EV_REL, "EV_REL drift");
_Static_assert(NUXEL_EV_ABS == EV_ABS, "EV_ABS drift");
_Static_assert(NUXEL_REL_X == REL_X, "REL_X drift");
_Static_assert(NUXEL_REL_Y == REL_Y, "REL_Y drift");
_Static_assert(NUXEL_BTN_LEFT == BTN_LEFT, "BTN_LEFT drift");
_Static_assert(NUXEL_BTN_RIGHT == BTN_RIGHT, "BTN_RIGHT drift");
_Static_assert(NUXEL_BTN_MIDDLE == BTN_MIDDLE, "BTN_MIDDLE drift");
_Static_assert(NUXEL_BTN_TOUCH == BTN_TOUCH, "BTN_TOUCH drift");
_Static_assert(NUXEL_ABS_MT_POSITION_X == ABS_MT_POSITION_X, "ABS_MT_POSITION_X drift");
_Static_assert(NUXEL_ABS_MT_POSITION_Y == ABS_MT_POSITION_Y, "ABS_MT_POSITION_Y drift");
_Static_assert(NUXEL_INPUT_PROP_DIRECT == INPUT_PROP_DIRECT, "INPUT_PROP_DIRECT drift");
#endif

#define STATE_FILE      "/run/nuxel-libinput-path.state"
#define INPUT_DOC       "/etc/nuxel/input/input.json"
#define INPUT_STATE     "/run/nuxel-input.state"
#define ORIENT_INPUT_FILE "/run/nuxel-orientation/input.json"
#define TOUCH_CAL_STATE "/run/nuxel-touch-calibration.state"
#define DEV_INPUT_DIR   "/dev/input"
#define NODE_PREFIX     "event"
#define UDEV_DATA_DIR   "/run/udev/data"
#define MAX_NODES       64
#define NAME_MAX_       64
#define MAX_TRACKED     64
#define HQ_CAP          128
#define RETRY_MAX       16
#define RETRY_ATTEMPTS  8

/* ==========================================================================
 * PART 1 — logging, bitmap decode, capability probe, decision, enumeration
 * ==========================================================================*/

static int g_log_stdout;      /* selftest: machine-readable stdout instead of
                                 the on-device state file */

static void st(const char *fmt, ...) {
  va_list ap;
  if (g_log_stdout) {
    fputs("STATE ", stdout);
    va_start(ap, fmt); vfprintf(stdout, fmt, ap); va_end(ap);
    fputc('\n', stdout);
    fflush(stdout);
  } else {
    FILE *f = fopen(STATE_FILE, "a");
    if (f) {
      fprintf(f, "%ld ", (long)time(NULL));
      va_start(ap, fmt); vfprintf(f, fmt, ap); va_end(ap);
      fputc('\n', f);
      fclose(f);
    }
  }
  if (getenv("NUXEL_LIBINPUT_PATH_DEBUG")) {
    fputs("[nuxel-libinput-path] ", stderr);
    va_start(ap, fmt); vfprintf(stderr, fmt, ap); va_end(ap);
    fputc('\n', stderr);
  }
}

/* A candidate node and the decision made about it.  `path` is always composed at
 * runtime from DEV_INPUT_DIR + "/" + the directory entry name. */
/* What a node proved it is.  A node can be more than one of these (a HID
 * keyboard interface with media keys, for example), so these are flags. */
enum cand_kind {
  CAND_TOUCH    = 1,
  CAND_POINTER  = 2,
  CAND_KEYBOARD = 4
};

struct cand {
  char path[64];
  char node[NAME_MAX_];       /* event entry name; the unique device key */
  char name[NAME_MAX_];
  int  direct;
  int  mt;                    /* ABS_MT_POSITION_X and ABS_MT_POSITION_Y present */
  int  btn;                   /* BTN_TOUCH */
  int  legacy_xy;             /* ABS_X and ABS_Y */
  int  rel_x, rel_y;          /* REL_X and REL_Y */
  int  btn_left;              /* BTN_LEFT (a real pointer button) */
  int  btn_mouse;             /* BTN_LEFT/RIGHT/MIDDLE */
  int  key_letters;           /* number of standard letter keys present */
  int  kind;                  /* CAND_* */
  int  slot_max;
  int  x_min, x_max, y_min, y_max;
  unsigned long long ino;     /* devtmpfs inode: distinguishes a re-created node */
  int  order;                 /* numeric part of the node name, for sorting */
  int  accept;
  /* USB grouping for the OSK policy: a mouse's macro-keyboard interfaces
   * must not count as an attached keyboard, while a keyboard's interface 0
   * must.  -1 means "not a USB interface" (Bluetooth, uinput, fixtures). */
  char usb_product[64];
  int  usb_ifnum;
  int  hw_keyboard;
  int  aux_keyboard;
  char reason[160];
};

static void cand_init(struct cand *c, const char *entry) {
  memset(c, 0, sizeof *c);
  snprintf(c->path, sizeof c->path, "%s/%s", DEV_INPUT_DIR, entry);
  snprintf(c->node, sizeof c->node, "%s", entry);
  c->x_min = c->y_min = 0;
  c->x_max = c->y_max = -1;
  c->slot_max = -1;
  c->order = -1;
  c->usb_ifnum = -1;
}

/* Parse the numeric suffix of a node entry name (the prefix followed by a
 * decimal number -> that number).  Returns -1
 * when the entry is not an event node. */
static int node_order(const char *entry) {
  size_t pl = strlen(NODE_PREFIX);
  if (strncmp(entry, NODE_PREFIX, pl) != 0) return -1;
  const char *p = entry + pl;
  if (!*p) return -1;
  char *end = NULL;
  long v = strtol(p, &end, 10);
  if (!end || *end || v < 0 || v > 4096) return -1;
  return (int)v;
}

/* Hex bitmaps as printed by the kernel with the FIRST word holding the HIGHEST
 * bits (the /proc/bus/input/devices convention used by
 * tools/s10plus/a32/tests/input-bitmap-decode.py).  The synthetic fixtures use
 * the same convention; the on-device path never reads sysfs for capabilities. */
static int decode_bitmap(const char *hex, unsigned long *words, int maxw) {
  int n = 0;
  const char *p = hex;
  while (*p && n < maxw) {
    while (*p == ' ' || *p == '\t' || *p == '\n' || *p == '\r' || *p == ',') p++;
    if (!*p) break;
    char *end = NULL;
    unsigned long w = strtoul(p, &end, 16);
    if (end == p) break;
    words[n++] = w;
    p = end;
  }
  return n;
}

#define BITMAP_WORDS 16

static int bitmap_has(const unsigned long *words, int nwords, int bit) {
  if (bit < 0 || nwords <= 0) return 0;
  int word_index = bit / 64;
  int printed = nwords - 1 - word_index;     /* first printed word is highest */
  if (printed < 0 || printed >= nwords) return 0;
  return (int)((words[printed] >> (bit % 64)) & 1ul);
}

static int bitmap_count_range(const unsigned long *words, int nwords, int lo, int hi) {
  int n = 0;
  for (int bit = lo; bit <= hi; bit++) n += bitmap_has(words, nwords, bit);
  return n;
}

/* An `absinfo` fixture line: "<NAME> <min> <max> <fuzz> <flat>". */
static void fixture_abs(const char *root, const char *entry, struct cand *c) {
  char fn[512];
  snprintf(fn, sizeof fn, "%s/sys/class/input/%s/device/absinfo", root, entry);
  FILE *f = fopen(fn, "r");
  if (!f) return;
  char line[256];
  while (fgets(line, sizeof line, f)) {
    char nm[64];
    int mn = 0, mx = 0, fz = 0, fl = 0;
    if (sscanf(line, "%63s %d %d %d %d", nm, &mn, &mx, &fz, &fl) < 3) continue;
    (void)fz; (void)fl;   /* present because absinfo carries them; unused here */
    if (!strcmp(nm, "ABS_MT_POSITION_X") || !strcmp(nm, "ABS_X")) { c->x_min = mn; c->x_max = mx; }
    else if (!strcmp(nm, "ABS_MT_POSITION_Y") || !strcmp(nm, "ABS_Y")) { c->y_min = mn; c->y_max = mx; }
    else if (!strcmp(nm, "ABS_MT_SLOT")) c->slot_max = mx;
  }
  fclose(f);
}

static int read_first_line(const char *path, char *out, size_t n) {
  FILE *f = fopen(path, "r");
  if (!f) return -1;
  if (!fgets(out, (int)n, f)) { fclose(f); return -1; }
  fclose(f);
  size_t l = strlen(out);
  while (l && (out[l - 1] == '\n' || out[l - 1] == '\r')) out[--l] = 0;
  return 0;
}

/* st_mtim is Linux; the offline selftest also builds on macOS where the same
 * fields are named st_mtimespec.  One helper keeps the decision code portable. */
static long long stat_mtime_ns(const struct stat *sb) {
#if defined(__APPLE__)
  return (long long)sb->st_mtimespec.tv_sec * 1000000000LL + sb->st_mtimespec.tv_nsec;
#else
  return (long long)sb->st_mtim.tv_sec * 1000000000LL + sb->st_mtim.tv_nsec;
#endif
}

static int read_whole(const char *path, char *out, size_t n) {
  FILE *f = fopen(path, "r");
  if (!f) return -1;
  size_t got = fread(out, 1, n - 1, f);
  fclose(f);
  out[got] = 0;
  return 0;
}

/* Read the USB product/interface grouping from the input node's sysfs link.
 * The interface component looks like "1-1.4:1.0"; its parent "1-1.4" is the
 * USB product.  This lets the compositor tell a keyboard from a mouse's
 * auxiliary macro-keyboard interfaces without trusting vendor names. */
static void usb_group_from_sysfs(const char *entry, struct cand *c) {
  char link[512];
  snprintf(link, sizeof link, "/sys/class/input/%s/device", entry);
  /* The class symlink is only "../../inputNN"; resolve it to the full USB
   * path so the product/interface components are visible. */
  char *target = realpath(link, NULL);
  if (!target) return;
  char prev[64] = "";
  char *save = NULL;
  for (char *comp = strtok_r(target, "/", &save); comp;
       comp = strtok_r(NULL, "/", &save)) {
    char *colon = strchr(comp, ':');
    char *dot = colon ? strchr(colon + 1, '.') : NULL;
    if (colon && dot && !strchr(colon + 1, ':')) {
      char *end = NULL;
      long ifnum = strtol(dot + 1, &end, 10);
      if (end && *end == 0 && ifnum >= 0 && ifnum < 256) {
        snprintf(c->usb_product, sizeof c->usb_product, "%s", prev);
        c->usb_ifnum = (int)ifnum;
        break;
      }
    }
    snprintf(prev, sizeof prev, "%s", comp);
  }
  free(target);
}

/* --- probe: fixture (synthetic sysfs/uevent tree) ------------------------- */
static int fixture_probe(const char *root, const char *entry, struct cand *c) {
  char fn[512], buf[512];
  cand_init(c, entry);
  c->order = node_order(entry);
  if (c->order < 0) return -1;

  snprintf(fn, sizeof fn, "%s/sys/class/input/%s/device/name", root, entry);
  if (read_first_line(fn, buf, sizeof buf) != 0) return -1;
  /* sysfs device names are quoted when they contain spaces; strip quotes. */
  size_t l = strlen(buf);
  if (l >= 2 && buf[0] == '"' && buf[l - 1] == '"') { memmove(buf, buf + 1, l - 2); buf[l - 2] = 0; }
  snprintf(c->name, sizeof c->name, "%s", buf);

  unsigned long w[BITMAP_WORDS];
  int nw;

  snprintf(fn, sizeof fn, "%s/sys/class/input/%s/device/properties", root, entry);
  nw = (read_whole(fn, buf, sizeof buf) == 0) ? decode_bitmap(buf, w, BITMAP_WORDS) : 0;
  c->direct = bitmap_has(w, nw, NUXEL_INPUT_PROP_DIRECT);

  snprintf(fn, sizeof fn, "%s/sys/class/input/%s/device/capabilities/abs", root, entry);
  nw = (read_whole(fn, buf, sizeof buf) == 0) ? decode_bitmap(buf, w, BITMAP_WORDS) : 0;
  int mt_x = bitmap_has(w, nw, NUXEL_ABS_MT_POSITION_X);
  int mt_y = bitmap_has(w, nw, NUXEL_ABS_MT_POSITION_Y);
  int abs_x = bitmap_has(w, nw, NUXEL_ABS_X);
  int abs_y = bitmap_has(w, nw, NUXEL_ABS_Y);
  c->mt = mt_x && mt_y;
  c->legacy_xy = abs_x && abs_y;

  snprintf(fn, sizeof fn, "%s/sys/class/input/%s/device/capabilities/key", root, entry);
  nw = (read_whole(fn, buf, sizeof buf) == 0) ? decode_bitmap(buf, w, BITMAP_WORDS) : 0;
  c->btn = bitmap_has(w, nw, NUXEL_BTN_TOUCH);
  c->btn_left = bitmap_has(w, nw, NUXEL_BTN_LEFT);
  c->btn_mouse = c->btn_left || bitmap_has(w, nw, NUXEL_BTN_RIGHT) ||
                 bitmap_has(w, nw, NUXEL_BTN_MIDDLE);
  /* A physical keyboard always exposes the standard letter block.  Requiring
   * several letters keeps volume/power/media keys (gpio_keys, Headset) out. */
  c->key_letters = bitmap_count_range(w, nw, 16, 25) +   /* QWERTYUIOP */
                   bitmap_count_range(w, nw, 30, 38) +   /* ASDFGHJKL  */
                   bitmap_count_range(w, nw, 44, 50);    /* ZXCVBNM    */

  snprintf(fn, sizeof fn, "%s/sys/class/input/%s/device/capabilities/rel", root, entry);
  nw = (read_whole(fn, buf, sizeof buf) == 0) ? decode_bitmap(buf, w, BITMAP_WORDS) : 0;
  c->rel_x = bitmap_has(w, nw, NUXEL_REL_X);
  c->rel_y = bitmap_has(w, nw, NUXEL_REL_Y);

  fixture_abs(root, entry, c);
  return 0;
}

/* --- probe: the real evdev node ------------------------------------------ */
#ifndef NUXEL_HAVE_EVDEV
/* Non-Linux host: the ioctl path cannot exist here; fixture mode is mandatory
 * and the offline tests drive the identical decision code. */
static int node_probe(const char *entry, struct cand *c) {
  cand_init(c, entry);
  c->order = node_order(entry);
  return -1;
}
#else
static int node_probe(const char *entry, struct cand *c) {
  cand_init(c, entry);
  c->order = node_order(entry);
  if (c->order < 0) return -1;
  usb_group_from_sysfs(entry, c);
  int fd = open(c->path, O_RDONLY | O_NONBLOCK | O_CLOEXEC);
  if (fd < 0) return -1;
  struct stat stbuf;
  if (stat(c->path, &stbuf) == 0) c->ino = (unsigned long long)stbuf.st_ino;

  char nm[NAME_MAX_] = {0};
  if (ioctl(fd, EVIOCGNAME(sizeof nm - 1), nm) >= 0) snprintf(c->name, sizeof c->name, "%s", nm);

  unsigned long prop[NUXEL_WORDS(INPUT_PROP_MAX)] = {0};
  if (ioctl(fd, EVIOCGPROP(sizeof prop), prop) >= 0)
    c->direct = !!(prop[NUXEL_INPUT_PROP_DIRECT / (8 * (int)sizeof(unsigned long))] &
                   (1ul << (NUXEL_INPUT_PROP_DIRECT % (8 * (int)sizeof(unsigned long)))));

  unsigned long absb[NUXEL_WORDS(ABS_CNT)] = {0};
  int have_abs = (ioctl(fd, EVIOCGBIT(NUXEL_EV_ABS, sizeof absb), absb) >= 0);
  if (have_abs) {
    c->mt = !!(absb[NUXEL_ABS_MT_POSITION_X / (8 * (int)sizeof(unsigned long))] &
               (1ul << (NUXEL_ABS_MT_POSITION_X % (8 * (int)sizeof(unsigned long))))) &&
            !!(absb[NUXEL_ABS_MT_POSITION_Y / (8 * (int)sizeof(unsigned long))] &
               (1ul << (NUXEL_ABS_MT_POSITION_Y % (8 * (int)sizeof(unsigned long)))));
    c->legacy_xy = !!(absb[NUXEL_ABS_X / (8 * (int)sizeof(unsigned long))] &
                      (1ul << (NUXEL_ABS_X % (8 * (int)sizeof(unsigned long))))) &&
                   !!(absb[NUXEL_ABS_Y / (8 * (int)sizeof(unsigned long))] &
                      (1ul << (NUXEL_ABS_Y % (8 * (int)sizeof(unsigned long)))));
    struct input_absinfo ai;
    if (ioctl(fd, EVIOCGABS(NUXEL_ABS_MT_POSITION_X), &ai) >= 0) { c->x_min = ai.minimum; c->x_max = ai.maximum; }
    if (ioctl(fd, EVIOCGABS(NUXEL_ABS_MT_POSITION_Y), &ai) >= 0) { c->y_min = ai.minimum; c->y_max = ai.maximum; }
    if (ioctl(fd, EVIOCGABS(NUXEL_ABS_MT_SLOT), &ai) >= 0) c->slot_max = ai.maximum;
    if (c->x_max < 0 || c->y_max < 0) {   /* legacy single-touch panel */
      if (ioctl(fd, EVIOCGABS(NUXEL_ABS_X), &ai) >= 0) { c->x_min = ai.minimum; c->x_max = ai.maximum; }
      if (ioctl(fd, EVIOCGABS(NUXEL_ABS_Y), &ai) >= 0) { c->y_min = ai.minimum; c->y_max = ai.maximum; }
    }
  }

  unsigned long keyb[NUXEL_WORDS(KEY_CNT)] = {0};
  if (ioctl(fd, EVIOCGBIT(NUXEL_EV_KEY, sizeof keyb), keyb) >= 0) {
    c->btn = !!(keyb[NUXEL_BTN_TOUCH / (8 * (int)sizeof(unsigned long))] &
                (1ul << (NUXEL_BTN_TOUCH % (8 * (int)sizeof(unsigned long)))));
    c->btn_left = !!(keyb[NUXEL_BTN_LEFT / (8 * (int)sizeof(unsigned long))] &
                     (1ul << (NUXEL_BTN_LEFT % (8 * (int)sizeof(unsigned long)))));
    int btn_right = !!(keyb[NUXEL_BTN_RIGHT / (8 * (int)sizeof(unsigned long))] &
                       (1ul << (NUXEL_BTN_RIGHT % (8 * (int)sizeof(unsigned long)))));
    int btn_middle = !!(keyb[NUXEL_BTN_MIDDLE / (8 * (int)sizeof(unsigned long))] &
                        (1ul << (NUXEL_BTN_MIDDLE % (8 * (int)sizeof(unsigned long)))));
    c->btn_mouse = c->btn_left || btn_right || btn_middle;
    /* Kernel bitmaps are laid out in unsigned long words.  Counting the
     * standard letter block (Q..P, A..L, Z..M) is a capability proof that a
     * node is a real keyboard; power/volume/headset nodes have no letters. */
    for (int k = 16; k <= 25; k++) c->key_letters += !!(keyb[k / (8 * (int)sizeof(unsigned long))] &
                                                         (1ul << (k % (8 * (int)sizeof(unsigned long)))));
    for (int k = 30; k <= 38; k++) c->key_letters += !!(keyb[k / (8 * (int)sizeof(unsigned long))] &
                                                         (1ul << (k % (8 * (int)sizeof(unsigned long)))));
    for (int k = 44; k <= 50; k++) c->key_letters += !!(keyb[k / (8 * (int)sizeof(unsigned long))] &
                                                         (1ul << (k % (8 * (int)sizeof(unsigned long)))));
  }

  unsigned long relb[NUXEL_WORDS(REL_CNT)] = {0};
  if (ioctl(fd, EVIOCGBIT(NUXEL_EV_REL, sizeof relb), relb) >= 0) {
    c->rel_x = !!(relb[NUXEL_REL_X / (8 * (int)sizeof(unsigned long))] &
                  (1ul << (NUXEL_REL_X % (8 * (int)sizeof(unsigned long)))));
    c->rel_y = !!(relb[NUXEL_REL_Y / (8 * (int)sizeof(unsigned long))] &
                  (1ul << (NUXEL_REL_Y % (8 * (int)sizeof(unsigned long)))));
  }
  close(fd);
  return 0;
}
#endif

/* --- the decision (capability only) -------------------------------------
 *
 * The panel is still selected by DIRECT + multitouch, exactly as before, and
 * only such a device receives the orientation calibration matrix.  USB HID
 * pointers and keyboards are selected by their own capabilities:
 *
 *   pointer  : REL_X + REL_Y + a real button (BTN_LEFT/RIGHT/MIDDLE), or
 *              ABS_X + ABS_Y + a real button for an absolute touchpad/tablet
 *   keyboard : the standard letter block is present (>= 10 of Q..P/A..L/Z..M)
 *
 * Requiring a button keeps sensor nodes (hrm_sensor, ssp_context), the panel's
 * non-DIRECT sec_touchpad emulation interface, gpio_keys and the headset button
 * out of the pointer path.  Requiring letters keeps power/volume keys out of
 * the keyboard path.  No node number and no device name is used.
 */
static void decide(struct cand *c) {
  c->kind = 0;

  if (c->direct) {
    if (!(c->mt || (c->btn && c->legacy_xy))) {
      snprintf(c->reason, sizeof c->reason,
               "reject: no multitouch axes (ABS_MT_POSITION_X/Y) and no BTN_TOUCH+ABS_X/Y");
      c->accept = 0;
      return;
    }
    if (c->x_max <= c->x_min || c->y_max <= c->y_min) {
      snprintf(c->reason, sizeof c->reason,
               "reject: degenerate axis range x=%d..%d y=%d..%d", c->x_min, c->x_max, c->y_min, c->y_max);
      c->accept = 0;
      return;
    }
    c->kind |= CAND_TOUCH;
  }

  int has_rel_xy = c->rel_x && c->rel_y;
  int has_abs_xy = c->legacy_xy;
  if (((has_rel_xy || has_abs_xy) && c->btn_mouse)) c->kind |= CAND_POINTER;
  if (c->key_letters >= 10) c->kind |= CAND_KEYBOARD;

  if (c->kind & CAND_TOUCH) {
    snprintf(c->reason, sizeof c->reason, "accept: DIRECT%s%s range x=%d..%d y=%d..%d slots=%d",
             c->mt ? "+ABS_MT" : "+BTN_TOUCH", c->btn ? "+BTN_TOUCH" : "",
             c->x_min, c->x_max, c->y_min, c->y_max, c->slot_max);
    c->accept = 1;
    return;
  }
  if (!c->kind) {
    snprintf(c->reason, sizeof c->reason,
             "reject: INPUT_PROP_DIRECT absent (not a touch surface); no pointer/keyboard capability");
    c->accept = 0;
    return;
  }

  const char *axes = has_rel_xy ? "REL_X/Y+BTN" : "ABS_X/Y+BTN";
  if ((c->kind & CAND_POINTER) && (c->kind & CAND_KEYBOARD)) {
    snprintf(c->reason, sizeof c->reason, "accept: pointer(%s)+keyboard(letters=%d)", axes, c->key_letters);
  } else if (c->kind & CAND_POINTER) {
    snprintf(c->reason, sizeof c->reason, "accept: pointer(%s)", axes);
  } else {
    snprintf(c->reason, sizeof c->reason, "accept: keyboard(letters=%d)", c->key_letters);
  }
  c->accept = 1;
}

static const char *kind_name(int kind) {
  if ((kind & CAND_TOUCH) && (kind & CAND_POINTER) && (kind & CAND_KEYBOARD)) return "touch+pointer+keyboard";
  if ((kind & CAND_TOUCH) && (kind & CAND_POINTER)) return "touch+pointer";
  if ((kind & CAND_TOUCH) && (kind & CAND_KEYBOARD)) return "touch+keyboard";
  if ((kind & CAND_POINTER) && (kind & CAND_KEYBOARD)) return "pointer+keyboard";
  if (kind & CAND_TOUCH) return "touch";
  if (kind & CAND_POINTER) return "pointer";
  if (kind & CAND_KEYBOARD) return "keyboard";
  return "none";
}

/* --- enumeration -------------------------------------------------------- */
static int order_cmp(const void *a, const void *b) {
  const char *ea = (const char *)a, *eb = (const char *)b;
  int oa = node_order(ea), ob = node_order(eb);
  if (oa != ob) return oa < ob ? -1 : 1;
  return strcmp(ea, eb);
}

/* List the event node entries of a directory, in NUMERIC order.  Works for the
 * real /dev/input and for a fixture tree, and never contains a node number. */
static int list_event_entries(const char *dir, char entries[][NAME_MAX_], int max) {
  DIR *d = opendir(dir);
  if (!d) return 0;
  int n = 0;
  struct dirent *de;
  while ((de = readdir(d)) && n < max) {
    if (node_order(de->d_name) < 0) continue;
    snprintf(entries[n], NAME_MAX_, "%s", de->d_name);
    n++;
  }
  closedir(d);
  if (n > 1) qsort(entries, (size_t)n, NAME_MAX_, order_cmp);
  return n;
}

/* Scan one root ("/dev/input" style container) and fill the accepted set. */
/* Mark which accepted keyboard nodes represent a real external keyboard.
 * A USB product whose interface 0 is a pointer is a mouse (or a pointer-first
 * combo); its other interfaces are macro/media keyboard endpoints, not an
 * external keyboard for OSK auto-hide.  A product with no pointer interface 0
 * is a keyboard (including a keyboard with a built-in touchpad). */
static void classify_keyboards(struct cand out[], int n) {
  for (int i = 0; i < n; i++) {
    if (!(out[i].kind & CAND_KEYBOARD))
      continue;
    int pointer_primary = 0;
    if (out[i].usb_ifnum >= 0) {
      for (int j = 0; j < n; j++) {
        if (out[j].usb_ifnum == 0 && (out[j].kind & CAND_POINTER) &&
            strcmp(out[i].usb_product, out[j].usb_product) == 0) {
          pointer_primary = 1;
          break;
        }
      }
    }
    if (out[i].usb_ifnum < 0 || !pointer_primary)
      out[i].hw_keyboard = 1;
    else
      out[i].aux_keyboard = 1;
    st("KEYBOARD_CLASS node=%s name='%s' product='%s' if=%d hw=%d aux=%d",
       out[i].node, out[i].name, out[i].usb_product, out[i].usb_ifnum,
       out[i].hw_keyboard, out[i].aux_keyboard);
  }
}

static int scan_nodes(const char *fixture_root, struct cand out[], int maxout, int verbose) {
  char entries[MAX_NODES][NAME_MAX_];
  int n;
  if (fixture_root) {
    char dir[400];
    snprintf(dir, sizeof dir, "%s/sys/class/input", fixture_root);
    n = list_event_entries(dir, entries, MAX_NODES);
  } else {
    n = list_event_entries(DEV_INPUT_DIR, entries, MAX_NODES);
  }
  int naccepted = 0;
  st("SCAN root=%s nodes=%d", fixture_root ? fixture_root : DEV_INPUT_DIR, n);
  if (verbose) printf("SCAN nodes=%d\n", n);
  for (int i = 0; i < n; i++) {
    struct cand c;
    int rc = fixture_root ? fixture_probe(fixture_root, entries[i], &c) : node_probe(entries[i], &c);
    if (rc != 0) {
      st("CANDIDATE node=%s unreadable (fixture metadata absent or node not openable)", entries[i]);
      if (verbose) printf("NODE %s UNREADABLE reason=metadata-or-open-failed\n", entries[i]);
      continue;
    }
    decide(&c);
    st("CANDIDATE node=%s order=%d name='%s' direct=%d mt=%d btn=%d range=%d..%d/%d..%d slots=%d %s",
       c.path, c.order, c.name, c.direct, c.mt, c.btn, c.x_min, c.x_max, c.y_min, c.y_max, c.slot_max, c.reason);
    if (verbose)
      printf("NODE %s order=%d name=\"%s\" direct=%d mt=%d btn=%d range=%d..%d/%d..%d slots=%d %s\n",
             c.path, c.order, c.name, c.direct, c.mt, c.btn, c.x_min, c.x_max, c.y_min, c.y_max,
             c.slot_max, c.reason);
    if (c.accept && naccepted < maxout) out[naccepted++] = c;
  }
  classify_keyboards(out, naccepted);
  st("SCAN_RESULT nodes=%d accepted=%d%s", n, naccepted, naccepted ? "" : " (ZERO_DEVICES: compositor stays up)");
  if (verbose) {
    printf("SCAN_RESULT nodes=%d accepted=%d\n", n, naccepted);
    if (!naccepted) printf("ZERO_DEVICES\n");
    for (int i = 0; i < naccepted; i++) printf("SELECTED %s\n", out[i].path);
  }
  return naccepted;
}

/* ==========================================================================
 * PART 1b — ONE touch calibration owner
 *
 * MEASURED (Phoc 0.54.0 + wlroots 0.19.3): wlroots applies an output transform
 * to absolute POINTER devices, but wlr_touch events remain raw libinput
 * coordinates.  Phoc calls wlr_cursor_absolute_to_layout_coords() directly, so
 * a rotated Phoc desktop has portrait-mapped touch unless the touch device is
 * calibrated.  libinput's calibration matrix is the compositor-owned input
 * transform; this shim is already the single input-discovery owner, so it also
 * consumes /run/nuxel-orientation/input.json and applies that matrix exactly
 * once.  No daemon, second listener, or framebuffer rotation is introduced.
 * ==========================================================================*/
static int matrix_valid(const float m[6]) {
  for (int i = 0; i < 6; i++) {
    if (!(m[i] >= -4.0f && m[i] <= 4.0f)) return 0;  /* rejects NaN/Inf */
  }
  /* The calibration affine transform must be invertible. */
  float det = m[0] * m[4] - m[1] * m[3];
  if (det < 0) det = -det;
  return det > 0.0001f;
}

static void matrix_identity(float m[6]) {
  m[0] = 1.0f; m[1] = 0.0f; m[2] = 0.0f;
  m[3] = 0.0f; m[4] = 1.0f; m[5] = 0.0f;
}

static int matrix_equal(const float a[6], const float b[6]) {
  for (int i = 0; i < 6; i++) {
    float d = a[i] - b[i];
    if (d < 0) d = -d;
    if (d > 0.0001f) return 0;
  }
  return 1;
}

/* Parse the compact JSON document written by nuxel-orientationd.  The file is
 * ours, but parsing is still defensive: a missing/invalid document restores
 * the identity and never leaves a guessed transform active. */
static int parse_input_state(const char *buf, float m[6], int *transform, int *applied) {
  const char *p = strstr(buf, "\"matrix\"");
  if (!p) return 0;
  p = strchr(p, '[');
  if (!p) return 0;
  p++;
  float v[6];
  for (int i = 0; i < 6; i++) {
    char *end = NULL;
    v[i] = strtof(p, &end);
    if (end == p) return 0;
    p = end;
    while (*p == ' ' || *p == '\t' || *p == ',' || *p == '\n' || *p == '\r') p++;
  }
  if (*p != ']' || !matrix_valid(v)) return 0;
  memcpy(m, v, sizeof v);
  p = strstr(buf, "\"transform\"");
  *transform = -1;
  if (p) {
    p = strchr(p, ':');
    if (p) *transform = (int)strtol(p + 1, NULL, 10);
  }
  p = strstr(buf, "\"applied\"");
  *applied = 0;
  if (p) {
    p = strchr(p, ':');
    if (p) {
      p++;
      while (*p == ' ' || *p == '\t') p++;
      *applied = (strncmp(p, "true", 4) == 0);
    }
  }
  return 1;
}

/* ==========================================================================
 * PART 1c — physical pointer settings (one document, one parser)
 *
 * /etc/nuxel/input/input.json is written by the Settings app.  The shim reads
 * it directly and applies the values to every libinput pointer it accepts, so
 * a mouse/touchpad works with the user's settings even if a GSettings change
 * notification never reaches the compositor.  Phoc also consumes the same
 * values through GSettings (nuxel-input-apply), so the compositor's own
 * hotplug path cannot re-apply stale defaults over ours.
 *
 * Keyboard layout/repeat stay in /etc/nuxel/keyboard/keyboard.json: they are
 * compositor (XKB) settings, not libinput device settings.
 * ==========================================================================*/
struct input_cfg {
  int loaded;
  double mouse_speed, touchpad_speed;
  int mouse_profile, touchpad_profile;   /* 0 default, 1 flat, 2 adaptive */
  int mouse_natural, mouse_left, mouse_middle;
  int touchpad_natural, touchpad_tap, touchpad_twofinger, touchpad_dwt, touchpad_left;
};

static struct input_cfg g_input_cfg;
static long long g_input_cfg_mtime_ns = -1;
static long long g_input_cfg_last_poll_ms;

static void input_cfg_defaults(struct input_cfg *c) {
  memset(c, 0, sizeof *c);
  c->mouse_profile = 0;
  c->touchpad_profile = 0;
  c->touchpad_natural = 1;
  c->touchpad_tap = 1;
  c->touchpad_twofinger = 1;
  c->touchpad_dwt = 1;
}

static const char *json_value_ptr(const char *buf, const char *key) {
  char pat[80];
  snprintf(pat, sizeof pat, "\"%s\"", key);
  const char *p = strstr(buf, pat);
  if (!p) return NULL;
  p = strchr(p, ':');
  if (!p) return NULL;
  p++;
  while (*p == ' ' || *p == '\t' || *p == '\n' || *p == '\r') p++;
  return p;
}

static int json_bool_key(const char *buf, const char *key, int *out) {
  const char *p = json_value_ptr(buf, key);
  if (!p) return 0;
  if (!strncmp(p, "true", 4)) { *out = 1; return 1; }
  if (!strncmp(p, "false", 5)) { *out = 0; return 1; }
  return 0;
}

static int json_num_key(const char *buf, const char *key, double lo, double hi, double *out) {
  const char *p = json_value_ptr(buf, key);
  if (!p) return 0;
  char *end = NULL;
  double v = strtod(p, &end);
  if (end == p || v < lo || v > hi) return 0;
  *out = v;
  return 1;
}

static int input_profile(const char *buf, const char *key, int *out) {
  const char *p = json_value_ptr(buf, key);
  if (!p) return 0;
  if (!strncmp(p, "\"default\"", 9)) { *out = 0; return 1; }
  if (!strncmp(p, "\"flat\"", 6)) { *out = 1; return 1; }
  if (!strncmp(p, "\"adaptive\"", 10)) { *out = 2; return 1; }
  return 0;
}

/* Returns 0 whether the document is present or absent: absence means defaults,
 * never a reason to stop the compositor. */
static int input_cfg_load(void) {
  input_cfg_defaults(&g_input_cfg);
  const char *path = getenv("NUXEL_INPUT_DOC");
  if (!path || !*path) path = INPUT_DOC;
  struct stat sb;
  if (stat(path, &sb) != 0) {
    g_input_cfg.loaded = 0;
    g_input_cfg_mtime_ns = -1;
    st("INPUT_CFG_DEFAULTS path=%s (document absent; pointer defaults stay)", path);
    return 0;
  }
  g_input_cfg_mtime_ns = stat_mtime_ns(&sb);
  char buf[8192];
  int fd = open(path, O_RDONLY | O_CLOEXEC);
  if (fd < 0) { st("INPUT_CFG_OPEN_FAIL path=%s errno=%d", path, errno); return 0; }
  ssize_t n = read(fd, buf, sizeof buf - 1);
  close(fd);
  if (n <= 0) { st("INPUT_CFG_READ_FAIL path=%s", path); return 0; }
  buf[n] = 0;

  json_num_key(buf, "mouse.speed", -1.0, 1.0, &g_input_cfg.mouse_speed);
  json_num_key(buf, "touchpad.speed", -1.0, 1.0, &g_input_cfg.touchpad_speed);
  input_profile(buf, "mouse.accel_profile", &g_input_cfg.mouse_profile);
  input_profile(buf, "touchpad.accel_profile", &g_input_cfg.touchpad_profile);
  json_bool_key(buf, "mouse.natural_scroll", &g_input_cfg.mouse_natural);
  json_bool_key(buf, "mouse.left_handed", &g_input_cfg.mouse_left);
  json_bool_key(buf, "mouse.middle_emulation", &g_input_cfg.mouse_middle);
  json_bool_key(buf, "touchpad.natural_scroll", &g_input_cfg.touchpad_natural);
  json_bool_key(buf, "touchpad.tap_to_click", &g_input_cfg.touchpad_tap);
  json_bool_key(buf, "touchpad.two_finger_scroll", &g_input_cfg.touchpad_twofinger);
  json_bool_key(buf, "touchpad.disable_while_typing", &g_input_cfg.touchpad_dwt);
  json_bool_key(buf, "touchpad.left_handed", &g_input_cfg.touchpad_left);
  g_input_cfg.loaded = 1;
  st("INPUT_CFG_LOADED path=%s mouse.speed=%.2f mouse.natural=%d touchpad.speed=%.2f "
     "touchpad.tap=%d touchpad.natural=%d",
     path, g_input_cfg.mouse_speed, g_input_cfg.mouse_natural,
     g_input_cfg.touchpad_speed, g_input_cfg.touchpad_tap, g_input_cfg.touchpad_natural);
  return 1;
}

/* ==========================================================================
 * PART 2 — hotplug queue and the tracked-device table
 *
 * Pure logic on purpose: this is the part the offline tests exercise, and the
 * part that must never crash the compositor when a device comes or goes.
 * ==========================================================================*/
#ifdef NUXEL_SHIM_SELFTEST
#  define HQ_LOCK()   ((void)0)
#  define HQ_UNLOCK() ((void)0)
#else
static pthread_mutex_t g_hq_lock = PTHREAD_MUTEX_INITIALIZER;
#  define HQ_LOCK()   pthread_mutex_lock(&g_hq_lock)
#  define HQ_UNLOCK() pthread_mutex_unlock(&g_hq_lock)
#endif

struct tracked { char key[NAME_MAX_]; char name[NAME_MAX_]; void *dev; int kind; unsigned long long ino; int used; };
static struct tracked g_tracked[MAX_TRACKED];

static const char *g_fixture_root;   /* set only by the offline selftest */
static int g_hotplug_stdout;         /* set only by the offline selftest */

static int tracked_count(void) {
  int n = 0;
  for (int i = 0; i < MAX_TRACKED; i++) if (g_tracked[i].used) n++;
  return n;
}

/* The tracked key is the event node entry (eventN), not the product name:
 * one physical mouse can expose a pointer interface and two keyboard
 * interfaces with the SAME product name.  Keying by name made the second and
 * third interfaces untracked at startup and ignored on a replug. */
static int tracked_find(const char *key) {
  for (int i = 0; i < MAX_TRACKED; i++)
    if (g_tracked[i].used && !strcmp(g_tracked[i].key, key)) return i;
  return -1;
}

static void *tracked_get(const char *key) {
  int i = tracked_find(key);
  return i >= 0 ? g_tracked[i].dev : NULL;
}

static int tracked_add(const char *key, const char *name, void *dev, int kind,
                       unsigned long long ino) {
  if (tracked_find(key) >= 0) return 0;
  for (int i = 0; i < MAX_TRACKED; i++) {
    if (!g_tracked[i].used) {
      snprintf(g_tracked[i].key, sizeof g_tracked[i].key, "%s", key);
      snprintf(g_tracked[i].name, sizeof g_tracked[i].name, "%s", name);
      g_tracked[i].dev = dev;
      g_tracked[i].kind = kind;
      g_tracked[i].ino = ino;
      g_tracked[i].used = 1;
      return 1;
    }
  }
  st("TRACKED_TABLE_FULL key=%s name=%s (bounded at %d; extra device ignored)", key, name, MAX_TRACKED);
  return 0;
}

static void *tracked_remove(const char *key) {
  int i = tracked_find(key);
  if (i < 0) return NULL;
  void *dev = g_tracked[i].dev;
  g_tracked[i].used = 0;
  g_tracked[i].dev = NULL;
  g_tracked[i].kind = 0;
  g_tracked[i].ino = 0;
  g_tracked[i].key[0] = 0;
  g_tracked[i].name[0] = 0;
  return dev;
}

enum { HQ_ADD = 0, HQ_REMOVE = 1 };
struct hq_ev { int op; char name[NAME_MAX_]; };
static struct hq_ev g_hq[HQ_CAP];
static int g_hq_head, g_hq_tail, g_hq_count;

/* The compositor's event loop blocks in epoll; a queue push alone does not
 * wake it.  The Wayland loop owns an eventfd registered by the interposer in
 * PART 3, so one nonblocking write makes the compositor thread run hq_drain()
 * (outside libinput_dispatch, which is the safe context for path_add_device). */
#ifdef NUXEL_SHIM_SELFTEST
static void wake_loop(void) { }
#else
static int g_wake_fd = -1;
static void wake_loop(void) {
  if (g_wake_fd < 0) return;
  uint64_t one = 1;
  ssize_t r = write(g_wake_fd, &one, sizeof one);
  (void)r;
}
#endif

static void hq_push(int op, const char *name) {
  HQ_LOCK();
  if (g_hq_count >= HQ_CAP) {
    HQ_UNLOCK();
    st("HOTPLUG_QUEUE_FULL dropped op=%d name=%s (bounded at %d)", op, name, HQ_CAP);
    return;
  }
  g_hq[g_hq_head].op = op;
  snprintf(g_hq[g_hq_head].name, NAME_MAX_, "%s", name);
  g_hq_head = (g_hq_head + 1) % HQ_CAP;
  g_hq_count++;
  HQ_UNLOCK();
  wake_loop();
}

static int hq_pop(struct hq_ev *out) {
  HQ_LOCK();
  if (g_hq_count == 0) { HQ_UNLOCK(); return 0; }
  *out = g_hq[g_hq_tail];
  g_hq_tail = (g_hq_tail + 1) % HQ_CAP;
  g_hq_count--;
  HQ_UNLOCK();
  return 1;
}

static void shim_apply(int op, const char *name);

/* Drain on the compositor's thread (from libinput_dispatch, or once at the end
 * of a selftest).  Bounded by HQ_CAP, so a device storm cannot block the loop. */
static void hq_drain(void) {
  struct hq_ev ev;
  while (hq_pop(&ev)) shim_apply(ev.op, ev.name);
}

/* A devtmpfs node can become visible a few milliseconds before evdev accepts
 * an open (measured with a uinput keyboard).  A real USB HID interface can hit
 * the same window.  Retry the ADD a bounded number of times from the watcher
 * thread; never sleep on the compositor thread. */
static long long mono_ms_now(void);   /* defined in PART 1b */
struct retry_ent { char name[NAME_MAX_]; int attempts; long long due_ms; int used; };
static struct retry_ent g_retry[RETRY_MAX];

#ifdef NUXEL_SHIM_SELFTEST
static void retry_schedule(const char *name) { (void)name; }
static void retry_tick(void) { }
#else
static pthread_mutex_t g_retry_lock = PTHREAD_MUTEX_INITIALIZER;

static void retry_schedule(const char *name) {
  long long now = mono_ms_now();
  int slot = -1;
  pthread_mutex_lock(&g_retry_lock);
  for (int i = 0; i < RETRY_MAX; i++) {
    if (g_retry[i].used && !strcmp(g_retry[i].name, name)) { slot = i; break; }
    if (slot < 0 && !g_retry[i].used) slot = i;
  }
  if (slot < 0) {
    pthread_mutex_unlock(&g_retry_lock);
    st("HOTPLUG_RETRY_TABLE_FULL node=%s", name);
    return;
  }
  if (!g_retry[slot].used) {
    snprintf(g_retry[slot].name, sizeof g_retry[slot].name, "%s", name);
    g_retry[slot].attempts = 0;
    g_retry[slot].used = 1;
  } else {
    g_retry[slot].attempts++;
    if (g_retry[slot].attempts >= RETRY_ATTEMPTS) {
      g_retry[slot].used = 0;
      pthread_mutex_unlock(&g_retry_lock);
      st("HOTPLUG_RETRY_GIVE_UP node=%s", name);
      return;
    }
  }
  g_retry[slot].due_ms = now + 200LL * (g_retry[slot].attempts + 1);
  int attempt = g_retry[slot].attempts + 1;
  pthread_mutex_unlock(&g_retry_lock);
  st("HOTPLUG_RETRY_SCHEDULED node=%s attempt=%d", name, attempt);
}

static void retry_tick(void) {
  char due[RETRY_MAX][NAME_MAX_];
  int n = 0;
  long long now = mono_ms_now();
  pthread_mutex_lock(&g_retry_lock);
  for (int i = 0; i < RETRY_MAX; i++) {
    if (g_retry[i].used && g_retry[i].due_ms <= now) {
      snprintf(due[n], NAME_MAX_, "%s", g_retry[i].name);
      g_retry[i].used = 0;
      n++;
    }
  }
  pthread_mutex_unlock(&g_retry_lock);
  for (int i = 0; i < n; i++) {
    st("HOTPLUG_RETRY node=%s", due[i]);
    hq_push(HQ_ADD, due[i]);
  }
}
#endif

static void watch_start(void);   /* PART 5; declared here because assign_seat uses it */

/* ==========================================================================
 * PART 3 — interposers (only in the deployed shared object)
 * ==========================================================================*/
#ifndef NUXEL_SHIM_SELFTEST
struct libinput;
struct libinput_device;
struct libinput_interface;
extern struct libinput *libinput_path_create_context(const struct libinput_interface *, void *);
extern struct libinput_device *libinput_path_add_device(struct libinput *, const char *);
extern void libinput_path_remove_device(struct libinput_device *);
extern int libinput_dispatch(struct libinput *);
struct libseat;
extern int libseat_open_device(struct libseat *, const char *, int *);
extern int libseat_close_device(struct libseat *, int);

static struct libinput *g_li;
static int g_aux_fd[MAX_TRACKED];

extern int libinput_device_config_calibration_has_matrix(struct libinput_device *);
extern int libinput_device_config_calibration_get_matrix(struct libinput_device *, float[6]);
extern int libinput_device_config_calibration_set_matrix(struct libinput_device *, const float[6]);

/* Physical pointer settings (libinput 1.30 symbols present in phoc's process). */
extern int libinput_device_config_accel_is_available(struct libinput_device *);
extern int libinput_device_config_accel_set_speed(struct libinput_device *, double);
extern uint32_t libinput_device_config_accel_get_profiles(struct libinput_device *);
extern int libinput_device_config_accel_set_profile(struct libinput_device *, int);
extern int libinput_device_config_scroll_has_natural_scroll(struct libinput_device *);
extern int libinput_device_config_scroll_set_natural_scroll_enabled(struct libinput_device *, int);
extern uint32_t libinput_device_config_scroll_get_methods(struct libinput_device *);
extern int libinput_device_config_scroll_set_method(struct libinput_device *, int);
extern int libinput_device_config_left_handed_is_available(struct libinput_device *);
extern int libinput_device_config_left_handed_set(struct libinput_device *, int);
extern int libinput_device_config_middle_emulation_is_available(struct libinput_device *);
extern int libinput_device_config_middle_emulation_set_enabled(struct libinput_device *, int);
extern int libinput_device_config_tap_get_finger_count(struct libinput_device *);
extern int libinput_device_config_tap_set_enabled(struct libinput_device *, int);
extern int libinput_device_config_tap_set_drag_enabled(struct libinput_device *, int);
extern int libinput_device_config_dwt_is_available(struct libinput_device *);
extern int libinput_device_config_dwt_set_enabled(struct libinput_device *, int);

static float g_touch_matrix[6] = {1.0f, 0.0f, 0.0f, 0.0f, 1.0f, 0.0f};
static float g_touch_applied[6] = {1.0f, 0.0f, 0.0f, 0.0f, 1.0f, 0.0f};
static int g_touch_matrix_valid;
static int g_touch_transform = -1;
static int g_touch_state_applied;
static long long g_touch_state_mtime_ns = -1;
static long long g_touch_last_poll_ms;
static int g_touch_identity_applied;
/* libinput applies a calibration change to the device state used by its next
 * read(2)/dispatch.  A matrix set before the device pair is fully initialised
 * (the path backend initialises it during the first dispatch) is accepted by
 * set_matrix() but is not the effective calibration for that first event.
 * The startup path therefore keeps a one-shot force flag and re-applies after
 * the first real dispatch.  This is why a correctly logged matrix could still
 * behave as identity after boot until the first touch/rotation. */
static int g_touch_force_apply = 1;
static unsigned g_touch_dispatch_count;
static pthread_mutex_t g_cal_lock = PTHREAD_MUTEX_INITIALIZER;
static void calibration_tick_unlocked(void);
static void calibration_tick(void);

static void aux_remember(int fd) {
  for (int i = 0; i < MAX_TRACKED; i++) if (g_aux_fd[i] == 0) { g_aux_fd[i] = fd; return; }
}
static int aux_forget(int fd) {
  for (int i = 0; i < MAX_TRACKED; i++) if (g_aux_fd[i] == fd) { g_aux_fd[i] = 0; return 1; }
  return 0;
}

/* ============================================================================
 * PART 3a — the device OPEN, without a VT-backed seat
 *
 * With LIBSEAT_BACKEND=noop the seat is created and becomes usable (wlroots'
 * "Timeout waiting session to become active" disappears - the handset has NO VT
 * at all: /dev/tty0 absent, /sys/class/vtconsole absent, /proc/consoles empty),
 * but libseat_open_device() on the noop backend refuses every device, so
 * libinput_path_add_device() returned NULL for the panel (measured A31:
 * PATH_ADD node=<panel node> ... accepted=0).
 *
 * This intercepts ONLY libseat_open_device()/libseat_close_device() and ONLY for
 * paths under /dev/input/: when libseat declines, the node is opened directly
 * (phoc runs as root; the kernel's evdev nodes here are root-only, which is the
 * exact case libseat cannot express without a session manager).  With
 * LIBSEAT_BACKEND=seatd and a usable seat the libseat call succeeds and this
 * fallback is never taken - both paths are logged, so which one was used is
 * evidence rather than an assumption.  Every other path goes through libseat
 * untouched, and every fd opened here is tracked so its close is balanced.
 * ==========================================================================*/
int libseat_open_device(struct libseat *seat, const char *path, int *fd) {
  static int (*real)(struct libseat *, const char *, int *);
  if (!real) real = dlsym(RTLD_NEXT, "libseat_open_device");
  int r = real ? real(seat, path, fd) : -1;
  if (r == -1 && path && strncmp(path, DEV_INPUT_DIR "/", strlen(DEV_INPUT_DIR) + 1) == 0) {
    int f = open(path, O_RDWR | O_CLOEXEC | O_NONBLOCK);
    if (f >= 0) {
      *fd = f; aux_remember(f);
      st("DEVICE_OPEN_FALLBACK path=%s fd=%d (libseat declined; direct root open)", path, f);
      return 0;
    }
    st("DEVICE_OPEN_FALLBACK_FAIL path=%s errno=%d", path, errno);
  } else {
    st("DEVICE_OPEN_LIBSEAT path=%s rc=%d fd=%d", path ? path : "?", r, (r == 0 && fd) ? *fd : -1);
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
 * PART 3b — the udev DATABASE entry, without the udev daemon
 *
 * libinput 1.30 has no pure "no udev" mode: libinput_path_add_device()
 * (src/path-seat.c) still resolves the node to a udev device first
 *
 *     dev = udev_device_new_from_devnum(udev, 'c', st.st_rdev);
 *     while (dev && !udev_device_get_is_initialized(dev)) {        // 200 x 10 ms
 *             msleep(10); dev = udev_device_new_from_devnum(...); }
 *     if (count > 200) -> "udev device never initialized" -> NULL
 *
 * and it returned NULL exactly like that (measured A31: ~2 s between PATH_ADD
 * lines, accepted=0).  `is_initialized` is true only when
 * /run/udev/data/<subsystem>:<devnum> exists and carries the 'I' marker that the
 * udev WORKER writes - which cannot happen here because systemd-udevd is masked
 * on this kernel (see the fork-storm rationale in the file header).
 *
 * So the entry is written from the device's OWN capability data (INPUT_PROP_DIRECT,
 * ABS_MT_*, BTN_TOUCH read by us), scoped to the /dev/input nodes we just accepted,
 * and only when it is absent.  This is the smallest possible replacement for a
 * daemon that cannot exist on Linux 4.14 - it does not invent a device, it records
 * the one libinput is about to open.
 * ==========================================================================*/
static int db_seeded;

static void seed_udev_db(const struct cand *c) {
  struct stat sb;
  if (stat(c->path, &sb) < 0) { st("UDEVDB_STAT_FAIL %s errno=%d", c->path, errno); return; }
  if (mkdir("/run/udev", 0755) < 0 && errno != EEXIST) { /* fall through */ }
  if (mkdir(UDEV_DATA_DIR, 0755) < 0 && errno != EEXIST) { /* fall through */ }
  char fn[96];
  snprintf(fn, sizeof fn, "%s/c%u:%u", UDEV_DATA_DIR, (unsigned)major(sb.st_rdev), (unsigned)minor(sb.st_rdev));
  /* Always rewrite: an event node number can be reused by a different device after
   * a hub reset (Razer node -> Keychron node).  Keeping the old file made
   * libinput see stale ID_INPUT_MOUSE/KEYBOARD tags for the new node. */
  FILE *f = fopen(fn, "w");
  if (!f) { st("UDEVDB_WRITE_FAIL %s errno=%d", fn, errno); return; }
  /* Properties libinput/quirks read, derived from what the node actually is.
   * A keyboard must NEVER be tagged ID_INPUT_TOUCHSCREEN; the old unconditional
   * touch tag was harmless only because non-touch nodes were rejected. */
  fprintf(f, "E:ID_INPUT=1\nE:ID_SEAT=seat0\n");
  if (c->kind & CAND_TOUCH) {
    fprintf(f, "E:ID_INPUT_TOUCHSCREEN=1\nE:ID_INPUT_WIDTH_MM=64\n"
               "E:ID_INPUT_HEIGHT_MM=135\n"
               "E:DEVLINKS=%s/by-path/nuxel-touchscreen\n", DEV_INPUT_DIR);
  } else {
    if (c->kind & CAND_POINTER) {
      int touchpad = strstr(c->name, "ouchpad") != NULL || strstr(c->name, "rackpad") != NULL;
      fprintf(f, "E:ID_INPUT_%s=1\nE:ID_INPUT_KEY=1\n",
              touchpad ? "TOUCHPAD" : "MOUSE");
    }
    if (c->kind & CAND_KEYBOARD)
      fprintf(f, "E:ID_INPUT_KEYBOARD=1\nE:ID_INPUT_KEY=1\n");
    if (c->aux_keyboard)
      fprintf(f, "E:NUXEL_INPUT_AUX_KEYBOARD=1\n");
    else if (c->hw_keyboard)
      fprintf(f, "E:NUXEL_INPUT_HW_KEYBOARD=1\n");
  }
  fprintf(f, "I:%ld\n", (long)time(NULL) * 1000000L);   /* 'I' = initialized */
  fclose(f);
  db_seeded++;
  st("UDEVDB_SEEDED %s kind=%d (initialized marker; systemd-udevd cannot run on this kernel)", fn, c->kind);
}

/* --- the interposers wlroots calls -------------------------------------- */
static int is_touch_screen_name(const char *name) {
  if (!name || !*name) return 0;
  if (strstr(name, "proximity") || strstr(name, "proximity_sensor")) return 0;
  return strstr(name, "touch") != NULL || strstr(name, "Touch") != NULL;
}

static void calibrate_device(const char *name, void *dev, int kind, const float m[6], const char *why) {
  /* The orientation matrix belongs to the touch surface only.  A USB mouse or
   * keyboard must never receive it (the old name check was a safety net; the
   * kind is now the authoritative gate). */
  if (!dev || !(kind & CAND_TOUCH) || !is_touch_screen_name(name)) return;
  struct libinput_device *d = (struct libinput_device *)dev;
  if (!libinput_device_config_calibration_has_matrix(d)) {
    st("TOUCH_MATRIX_UNSUPPORTED device='%s' why=%s", name, why);
    return;
  }
  float before[6] = {0};
  libinput_device_config_calibration_get_matrix(d, before);
  int rc = libinput_device_config_calibration_set_matrix(d, m);
  float after[6] = {0};
  libinput_device_config_calibration_get_matrix(d, after);
  int ok = (rc == 0 && matrix_equal(after, m));
  st("TOUCH_MATRIX_APPLY device='%s' why=%s rc=%d ok=%d matrix=%.4f,%.4f,%.4f,%.4f,%.4f,%.4f before=%.4f,%.4f,%.4f,%.4f,%.4f,%.4f",
     name, why, rc, ok, after[0], after[1], after[2], after[3], after[4], after[5],
     before[0], before[1], before[2], before[3], before[4], before[5]);
  FILE *f = fopen(TOUCH_CAL_STATE, "w");
  if (f) {
    fprintf(f, "device=%s\nwhy=%s\napplied=%d\nmatrix=%.4f,%.4f,%.4f,%.4f,%.4f,%.4f\n"
               "transform=%d\nsource=%s\nowner=libnuxel-libinput-path.so\n",
            name, why, ok, after[0], after[1], after[2], after[3], after[4], after[5],
            g_touch_transform, ORIENT_INPUT_FILE);
    fclose(f);
  }
}

static void calibrate_all(const char *why) {
  for (int i = 0; i < MAX_TRACKED; i++) {
    if (g_tracked[i].used)
      calibrate_device(g_tracked[i].name, g_tracked[i].dev, g_tracked[i].kind, g_touch_matrix, why);
  }
  memcpy(g_touch_applied, g_touch_matrix, sizeof g_touch_applied);
}

static long long mono_ms_now(void) {
  struct timespec ts;
  clock_gettime(CLOCK_MONOTONIC, &ts);
  return (long long)ts.tv_sec * 1000 + ts.tv_nsec / 1000000;
}

/* Called on the compositor's thread before libinput_dispatch().  The state file
 * is atomically replaced, so polling its mtime is sufficient; no watcher thread
 * is needed and no input call happens off the compositor thread. */
static void calibration_tick_unlocked(void) {
  long long now = mono_ms_now();
  if (now - g_touch_last_poll_ms < 250) return;
  g_touch_last_poll_ms = now;
  struct stat sb;
  if (stat(ORIENT_INPUT_FILE, &sb) != 0) {
    if (!g_touch_identity_applied) {
      matrix_identity(g_touch_matrix);
      g_touch_matrix_valid = 1;
      g_touch_transform = -1;
      g_touch_state_applied = 0;
      calibrate_all("state-missing-identity");
      g_touch_identity_applied = 1;
    }
    return;
  }
  long long mtime_ns = stat_mtime_ns(&sb);
  if (mtime_ns == g_touch_state_mtime_ns &&
      matrix_equal(g_touch_applied, g_touch_matrix)) return;
  char buf[1024];
  int fd = open(ORIENT_INPUT_FILE, O_RDONLY | O_CLOEXEC);
  if (fd < 0) return;
  ssize_t n = read(fd, buf, sizeof buf - 1);
  close(fd);
  if (n <= 0) return;
  buf[n] = 0;
  float m[6];
  int transform = -1, applied = 0;
  if (!parse_input_state(buf, m, &transform, &applied)) {
    st("TOUCH_MATRIX_PARSE_FAIL file=%s (identity retained)", ORIENT_INPUT_FILE);
    return;
  }
  g_touch_state_mtime_ns = mtime_ns;
  g_touch_matrix_valid = 1;
  g_touch_transform = transform;
  g_touch_state_applied = applied;
  memcpy(g_touch_matrix, m, sizeof g_touch_matrix);
  g_touch_identity_applied = 0;
  if (!matrix_equal(g_touch_applied, g_touch_matrix)) {
    g_touch_force_apply = 1;
    calibrate_all("orientation-state");
  }
}

static void calibration_tick(void) {
  pthread_mutex_lock(&g_cal_lock);
  calibration_tick_unlocked();
  if (g_touch_force_apply && g_touch_matrix_valid) {
    calibrate_all("deferred-after-dispatch");
    g_touch_force_apply = 0;
  }
  pthread_mutex_unlock(&g_cal_lock);
}

/* The compositor's Wayland loop only calls libinput_dispatch() when a libinput
 * fd is readable.  An idle screen therefore has no dispatch call to notice a
 * rotation.  This tiny inotify thread consumes the daemon's atomically replaced
 * input.json and updates the libinput calibration in place.  It makes no
 * orientation decision, never opens the framebuffer, and is not a second
 * authority: it only mirrors the already-verified transform into libinput. */
static void *calibration_watch_thread(void *arg) {
  (void)arg;
  int fd = inotify_init1(IN_NONBLOCK | IN_CLOEXEC);
  if (fd < 0) { st("TOUCH_MATRIX_WATCH_UNAVAILABLE errno=%d", errno); return NULL; }
  int runwd = inotify_add_watch(fd, "/run", IN_CREATE | IN_MOVED_TO | IN_ONLYDIR);
  int dirwd = inotify_add_watch(fd, "/run/nuxel-orientation",
                                IN_CLOSE_WRITE | IN_MOVED_TO | IN_CREATE | IN_MODIFY);
  st("TOUCH_MATRIX_WATCH_READY runwd=%d dirwd=%d", runwd, dirwd);
  char buf[4096] __attribute__((aligned(__alignof__(struct inotify_event))));
  for (;;) {
    ssize_t len = read(fd, buf, sizeof buf);
    if (len <= 0) {
      if (len < 0 && (errno == EAGAIN || errno == EWOULDBLOCK)) { usleep(200000); continue; }
      if (len < 0 && errno == EINTR) continue;
      break;
    }
    int relevant = 0;
    for (char *p = buf; p < buf + len; ) {
      struct inotify_event *ev = (struct inotify_event *)p;
      p += sizeof(struct inotify_event) + ev->len;
      if (ev->wd == runwd && ev->len && !strcmp(ev->name, "nuxel-orientation")) {
        if (dirwd < 0) {
          dirwd = inotify_add_watch(fd, "/run/nuxel-orientation",
                                    IN_CLOSE_WRITE | IN_MOVED_TO | IN_CREATE | IN_MODIFY);
          st("TOUCH_MATRIX_WATCH_DIR_ADDED wd=%d", dirwd);
        }
        relevant = 1;
      } else if (ev->wd == dirwd && ev->len && !strcmp(ev->name, "input.json")) {
        relevant = 1;
      }
    }
    if (relevant) {
      pthread_mutex_lock(&g_cal_lock);
      g_touch_last_poll_ms = 0;
      calibration_tick_unlocked();
      /* The shim's watcher may update libinput immediately, but libinput is
       * owned by the compositor thread.  Force a second application from the
       * next dispatch so the effective calibration cannot remain stale even
       * when set_matrix() ran before the pair was fully initialised. */
      g_touch_force_apply = 1;
      pthread_mutex_unlock(&g_cal_lock);
    }
  }
  close(fd);
  return NULL;
}

static void calibration_watch_start(void) {
  static int started;
  if (started) return;
  started = 1;
  pthread_t th;
  if (pthread_create(&th, NULL, calibration_watch_thread, NULL) == 0) pthread_detach(th);
  else st("TOUCH_MATRIX_WATCH_THREAD_FAIL");
}

/* Wayland event-loop bridge.  libinput_path_add_device() is only safe on the
 * compositor thread outside libinput_dispatch(); this callback is that context.
 * The watcher thread only queues and writes the eventfd. */
struct wl_display;
struct wl_event_loop;
struct wl_event_source;
extern struct wl_event_loop *wl_display_get_event_loop(struct wl_display *);
extern struct wl_event_source *wl_event_loop_add_fd(struct wl_event_loop *, int,
                                                   uint32_t, int (*)(int, uint32_t, void *), void *);
#define NUXEL_WL_EVENT_READABLE 1u

static int wake_event_cb(int fd, uint32_t mask, void *data) {
  (void)mask; (void)data;
  uint64_t v;
  ssize_t r = read(fd, &v, sizeof v);
  (void)r;
  hq_drain();
  return 0;
}

static void wake_register(struct wl_event_loop *loop) {
  if (g_wake_fd >= 0 || !loop) return;
  int fd = eventfd(0, EFD_NONBLOCK | EFD_CLOEXEC);
  if (fd < 0) { st("HOTPLUG_WAKE_UNAVAILABLE eventfd errno=%d", errno); return; }
  struct wl_event_source *src = wl_event_loop_add_fd(loop, fd, NUXEL_WL_EVENT_READABLE,
                                                     wake_event_cb, NULL);
  if (!src) {
    close(fd);
    st("HOTPLUG_WAKE_REGISTER_FAIL loop=%p errno=%d (dispatch-only hotplug remains)", (void *)loop, errno);
    return;
  }
  g_wake_fd = fd;
  st("HOTPLUG_WAKE_READY fd=%d loop=%p", fd, (void *)loop);
}

struct wl_event_loop *wl_display_get_event_loop(struct wl_display *display) {
  static struct wl_event_loop *(*real)(struct wl_display *);
  if (!real) real = dlsym(RTLD_NEXT, "wl_display_get_event_loop");
  struct wl_event_loop *loop = real ? real(display) : NULL;
  wake_register(loop);
  return loop;
}

static void *shim_libinput_add(const struct cand *c) {
  seed_udev_db(c);
  void *dev = libinput_path_add_device(g_li, c->path);
  return dev;
}

/* libinput enum values (stable public ABI). */
#define NUXEL_LI_ACCEL_FLAT      1
#define NUXEL_LI_ACCEL_ADAPTIVE  2
#define NUXEL_LI_SCROLL_TWO_FINGER 1
#define NUXEL_LI_SCROLL_EDGE       2
#define NUXEL_LI_TAP_ENABLED       1

static void apply_pointer_settings(struct libinput_device *d, const char *name, int kind, const char *why) {
  if (!d || !(kind & CAND_POINTER)) return;
  int touchpad = libinput_device_config_tap_get_finger_count(d) > 0;
  double speed = touchpad ? g_input_cfg.touchpad_speed : g_input_cfg.mouse_speed;
  int profile = touchpad ? g_input_cfg.touchpad_profile : g_input_cfg.mouse_profile;
  int natural = touchpad ? g_input_cfg.touchpad_natural : g_input_cfg.mouse_natural;
  int left = touchpad ? g_input_cfg.touchpad_left : g_input_cfg.mouse_left;
  int middle = g_input_cfg.mouse_middle;
  int speed_rc = -1, profile_rc = -1, natural_rc = -1, left_rc = -1, middle_rc = -1;
  int tap_rc = -1, drag_rc = -1, dwt_rc = -1, scroll_rc = -1;

  if (libinput_device_config_accel_is_available(d)) {
    speed_rc = libinput_device_config_accel_set_speed(d, speed);
    if (profile) {
      uint32_t profiles = libinput_device_config_accel_get_profiles(d);
      int want = profile == 1 ? NUXEL_LI_ACCEL_FLAT : NUXEL_LI_ACCEL_ADAPTIVE;
      if (profiles & (uint32_t)want)
        profile_rc = libinput_device_config_accel_set_profile(d, want);
    }
  }
  if (libinput_device_config_scroll_has_natural_scroll(d))
    natural_rc = libinput_device_config_scroll_set_natural_scroll_enabled(d, natural);
  if (libinput_device_config_left_handed_is_available(d))
    left_rc = libinput_device_config_left_handed_set(d, left);
  if (libinput_device_config_middle_emulation_is_available(d))
    middle_rc = libinput_device_config_middle_emulation_set_enabled(d, middle);

  if (touchpad) {
    if (libinput_device_config_tap_get_finger_count(d) > 0) {
      int tap = g_input_cfg.touchpad_tap;
      tap_rc = libinput_device_config_tap_set_enabled(d, tap ? NUXEL_LI_TAP_ENABLED : 0);
      drag_rc = libinput_device_config_tap_set_drag_enabled(d, tap ? NUXEL_LI_TAP_ENABLED : 0);
    }
    if (libinput_device_config_dwt_is_available(d))
      dwt_rc = libinput_device_config_dwt_set_enabled(d, g_input_cfg.touchpad_dwt);
    uint32_t methods = libinput_device_config_scroll_get_methods(d);
    if (g_input_cfg.touchpad_twofinger && (methods & NUXEL_LI_SCROLL_TWO_FINGER))
      scroll_rc = libinput_device_config_scroll_set_method(d, NUXEL_LI_SCROLL_TWO_FINGER);
    else if (!g_input_cfg.touchpad_twofinger && (methods & NUXEL_LI_SCROLL_EDGE))
      scroll_rc = libinput_device_config_scroll_set_method(d, NUXEL_LI_SCROLL_EDGE);
  }

  st("INPUT_APPLY_POINTER name='%s' why=%s touchpad=%d speed=%.2f profile=%d natural=%d "
     "left=%d middle=%d tap=%d dwt=%d scroll=%d rc=%d/%d/%d/%d/%d/%d/%d/%d",
     name, why, touchpad, speed, profile, natural, left, middle,
     g_input_cfg.touchpad_tap, g_input_cfg.touchpad_dwt, g_input_cfg.touchpad_twofinger,
     speed_rc, profile_rc, natural_rc, left_rc, middle_rc, tap_rc, drag_rc, dwt_rc);
  (void)scroll_rc;
}

static void apply_all_pointer_settings(const char *why) {
  for (int i = 0; i < MAX_TRACKED; i++) {
    if (g_tracked[i].used && (g_tracked[i].kind & CAND_POINTER))
      apply_pointer_settings((struct libinput_device *)g_tracked[i].dev,
                             g_tracked[i].name, g_tracked[i].kind, why);
  }
}

static void write_input_state(const char *why) {
  char tmp[64];
  snprintf(tmp, sizeof tmp, "%s.tmp.%d", INPUT_STATE, (int)getpid());
  FILE *f = fopen(tmp, "w");
  if (!f) { st("INPUT_STATE_WRITE_FAIL path=%s errno=%d", tmp, errno); return; }
  int nptr = 0, nkbd = 0, ntouch = 0;
  for (int i = 0; i < MAX_TRACKED; i++) {
    if (!g_tracked[i].used) continue;
    if (g_tracked[i].kind & CAND_POINTER) nptr++;
    if (g_tracked[i].kind & CAND_KEYBOARD) nkbd++;
    if (g_tracked[i].kind & CAND_TOUCH) ntouch++;
  }
  fprintf(f, "schema_version=1\nowner=libnuxel-libinput-path.so\nwhy=%s\n"
             "updated_at=%ld\npointer_devices=%d\nkeyboard_devices=%d\ntouch_devices=%d\n",
          why, (long)time(NULL), nptr, nkbd, ntouch);
  int n = 0;
  for (int i = 0; i < MAX_TRACKED; i++) {
    if (!g_tracked[i].used) continue;
    fprintf(f, "device.%d kind=%s node=%s name='%s'\n", n++,
            kind_name(g_tracked[i].kind), g_tracked[i].key, g_tracked[i].name);
  }
  fprintf(f, "mouse.speed=%.2f\nmouse.accel_profile=%d\nmouse.natural_scroll=%d\n"
             "mouse.left_handed=%d\nmouse.middle_emulation=%d\n"
             "touchpad.speed=%.2f\ntouchpad.accel_profile=%d\ntouchpad.natural_scroll=%d\n"
             "touchpad.tap_to_click=%d\ntouchpad.two_finger_scroll=%d\n"
             "touchpad.disable_while_typing=%d\ntouchpad.left_handed=%d\n"
             "verdict=READY\n",
          g_input_cfg.mouse_speed, g_input_cfg.mouse_profile, g_input_cfg.mouse_natural,
          g_input_cfg.mouse_left, g_input_cfg.mouse_middle, g_input_cfg.touchpad_speed,
          g_input_cfg.touchpad_profile, g_input_cfg.touchpad_natural,
          g_input_cfg.touchpad_tap, g_input_cfg.touchpad_twofinger,
          g_input_cfg.touchpad_dwt, g_input_cfg.touchpad_left);
  fclose(f);
  if (rename(tmp, INPUT_STATE) != 0) {
    st("INPUT_STATE_RENAME_FAIL path=%s errno=%d", INPUT_STATE, errno);
    unlink(tmp);
  }
}

static void input_cfg_tick(void) {
  long long now = mono_ms_now();
  if (now - g_input_cfg_last_poll_ms < 500) return;
  g_input_cfg_last_poll_ms = now;
  const char *path = getenv("NUXEL_INPUT_DOC");
  if (!path || !*path) path = INPUT_DOC;
  struct stat sb;
  if (stat(path, &sb) != 0) {
    if (g_input_cfg_mtime_ns != -1) {
      g_input_cfg_mtime_ns = -1;
      input_cfg_load();
      apply_all_pointer_settings("document-removed");
      write_input_state("document-removed");
    }
    return;
  }
  long long mtime_ns = stat_mtime_ns(&sb);
  if (mtime_ns == g_input_cfg_mtime_ns) return;
  if (input_cfg_load()) {
    apply_all_pointer_settings("config-changed");
    write_input_state("config-changed");
  }
}

struct libinput *libinput_udev_create_context(const struct libinput_interface *iface,
                                              void *user_data, void *udev) {
  (void)udev;
  struct libinput *li = libinput_path_create_context(iface, user_data);
  g_li = li;
  st("PATH_CONTEXT_CREATED ctx=%p udev=%p (the udev daemon is masked on this kernel and is not required)",
     (void *)li, udev);
  if (!li) st("PATH_CONTEXT_FAILED errno=%d", errno);
  return li;
}

int libinput_udev_assign_seat(struct libinput *li, const char *seat_id) {
  g_li = li;
  input_cfg_load();
  struct cand sel[MAX_NODES];
  int seen = scan_nodes(NULL, sel, MAX_NODES, 0);
  int added = 0, np = 0, nk = 0, nt = 0;
  for (int i = 0; i < seen; i++) {
    void *dev = shim_libinput_add(&sel[i]);
    st("PATH_ADD node=%s order=%d name='%s' kind=%s accepted=%d",
       sel[i].path, sel[i].order, sel[i].name, kind_name(sel[i].kind), dev != NULL);
    if (dev && tracked_add(sel[i].node, sel[i].name, dev, sel[i].kind, sel[i].ino)) {
      added++;
      if (sel[i].kind & CAND_POINTER) { np++; apply_pointer_settings((struct libinput_device *)dev, sel[i].name, sel[i].kind, "device-add"); }
      if (sel[i].kind & CAND_KEYBOARD) nk++;
      if (sel[i].kind & CAND_TOUCH) {
        nt++;
        calibrate_device(sel[i].name, dev, sel[i].kind, g_touch_matrix, "device-add");
      }
    }
  }
  st("PATH_ASSIGN_SEAT seat='%s' direct_devices_seen=%d added=%d pointer=%d keyboard=%d touch=%d db_seeded=%d tracked=%d",
     seat_id ? seat_id : "(null)", seen, added, np, nk, nt, db_seeded, tracked_count());
  write_input_state("assign-seat");
  calibration_watch_start();
  watch_start();
  g_touch_force_apply = 1;
  return 0;   /* wlroots treats 0 as "seat assigned"; ZERO_DEVICES is not an error here */
}

int libinput_dispatch(struct libinput *li) {
  static int (*real)(struct libinput *);
  if (!real) real = dlsym(RTLD_NEXT, "libinput_dispatch");
  calibration_tick();
  int rc = real ? real(li) : -1;
  /* libinput's path backend finishes device initialization inside the first
   * dispatch.  Re-assert the matrix afterwards; the pre-dispatch application
   * on the very first call is accepted by set_matrix() but is not effective
   * for the first input frame.  Three passes cover startup and a hotplug. */
  if (g_touch_dispatch_count < 3) {
    g_touch_dispatch_count++;
    pthread_mutex_lock(&g_cal_lock);
    g_touch_force_apply = 1;
    /* calibration_tick() would re-lock the same non-recursive mutex. */
    calibration_tick_unlocked();
    pthread_mutex_unlock(&g_cal_lock);
  }
  hq_drain();
  input_cfg_tick();
  return rc;
}
#endif /* !NUXEL_SHIM_SELFTEST */

/* ==========================================================================
 * PART 4 — shim_apply: the single place where a hotplug event becomes
 *          a libinput device (or an explained rejection)
 * ==========================================================================*/
/* Does the event node exist right now, and what is its devtmpfs inode?
 * During a hub reset the new node can be announced before the old node's
 * delete notification.  Comparing the inode tells the two apart without
 * guessing from timing or from the product name. */
static int node_stat_ino(const char *name, unsigned long long *ino) {
  char path[96];
  snprintf(path, sizeof path, "%s/%s", DEV_INPUT_DIR, name);
  struct stat sb;
  if (stat(path, &sb) != 0) return 0;
  *ino = (unsigned long long)sb.st_ino;
  return 1;
}

static void shim_apply(int op, const char *name) {
  if (op == HQ_ADD) {
    struct cand c;
    int rc;
    if (g_fixture_root) {
      rc = fixture_probe(g_fixture_root, name, &c);
      if (rc == 0) {
        decide(&c);
        c.hw_keyboard = !!(c.kind & CAND_KEYBOARD);
      }
    } else {
      /* Re-scan the accepted set so the new node is classified with its USB
       * siblings (a mouse's macro keyboard vs a real keyboard's interface 0). */
      struct cand all[MAX_NODES];
      int n = scan_nodes(NULL, all, MAX_NODES, 0);
      int found = 0;
      for (int i = 0; i < n; i++) {
        if (strcmp(all[i].node, name) == 0) { c = all[i]; found = 1; break; }
      }
      if (!found) {
        rc = node_probe(name, &c);
        if (rc == 0) decide(&c);
      } else {
        rc = 0;
      }
    }
    if (rc != 0) {
      st("HOTPLUG_ADD node=%s rejected=metadata-or-open-failed", name);
      if (g_hotplug_stdout) printf("HOTPLUG ADD %s REJECT reason=metadata-or-open-failed\n", name);
      retry_schedule(name);
      return;
    }
    if (!c.accept) {
      st("HOTPLUG_ADD node=%s rejected=%s", c.path, c.reason);
      if (g_hotplug_stdout) printf("HOTPLUG ADD %s REJECT reason=\"%s\"\n", name, c.reason);
      return;
    }
    int old = tracked_find(name);
    if (old >= 0) {
      if (g_tracked[old].ino == c.ino) {
        st("HOTPLUG_ADD node=%s ignored=already-tracked ino=%llu", name, c.ino);
        if (g_hotplug_stdout) printf("HOTPLUG ADD %s IGNORED already-tracked\n", name);
        return;
      }
      /* Same event name, new devtmpfs inode: the hub re-created the node.
       * Release the old tracking entry (libinput owns the dead fd) and add
       * the new device.  A late REMOVE for the old inode is ignored below. */
      st("HOTPLUG_REPLACE node=%s old_ino=%llu new_ino=%llu", name, g_tracked[old].ino, c.ino);
      tracked_remove(name);
    }
#ifdef NUXEL_SHIM_SELFTEST
    void *dev = (void *)1;              /* the offline harness never calls libinput */
#else
    void *dev = shim_libinput_add(&c);
#endif
    if (dev) {
      tracked_add(name, c.name, dev, c.kind, c.ino);
#ifndef NUXEL_SHIM_SELFTEST
      if (c.kind & CAND_TOUCH) calibrate_device(name, dev, c.kind, g_touch_matrix, "hotplug-add");
      if (c.kind & CAND_POINTER) apply_pointer_settings((struct libinput_device *)dev, name, c.kind, "hotplug-add");
      write_input_state("hotplug-add");
#endif
      st("HOTPLUG_ADD node=%s kind=%s ino=%llu accepted=1 tracked=%d", c.path, kind_name(c.kind), c.ino, tracked_count());
      if (g_hotplug_stdout) printf("HOTPLUG ADD %s ACCEPT kind=%s tracked=%d\n", name, kind_name(c.kind), tracked_count());
    } else {
      st("HOTPLUG_ADD node=%s accepted=0 (libinput_path_add_device returned NULL)", c.path);
      if (g_hotplug_stdout) printf("HOTPLUG ADD %s ADD_FAILED\n", name);
      retry_schedule(name);
    }
    return;
  }

  /* Removal.  A DELETE for the old inode can arrive after the new node was
   * already added.  Only release our entry when the node is actually gone;
   * if a replacement node is present, schedule its add instead. */
  unsigned long long ino = 0;
  int present = node_stat_ino(name, &ino);
  int ti = tracked_find(name);
  if (present) {
    if (ti >= 0 && g_tracked[ti].ino == ino) {
      st("HOTPLUG_REMOVE node=%s ignored=still-present ino=%llu", name, ino);
      if (g_hotplug_stdout) printf("HOTPLUG REMOVE %s IGNORED still-present\n", name);
      return;
    }
    st("HOTPLUG_REMOVE node=%s stale entry; replacement ino=%llu scheduled", name, ino);
    if (ti >= 0) tracked_remove(name);
    retry_schedule(name);
    if (g_hotplug_stdout) printf("HOTPLUG REMOVE %s REPLACED tracked=%d\n", name, tracked_count());
    return;
  }
  void *dev = tracked_remove(name);
  if (!dev) {
    st("HOTPLUG_REMOVE node=%s not-tracked (ignored)", name);
    if (g_hotplug_stdout) printf("HOTPLUG REMOVE %s NOT_TRACKED\n", name);
    return;
  }
#ifndef NUXEL_SHIM_SELFTEST
  /* Do NOT call libinput_path_remove_device() here.  This runs inside
   * libinput_dispatch() on the compositor thread; libinput 1.30 crashes with
   * SIGSEGV in libinput_path_remove_device when a pointer/keyboard is removed
   * from that context (measured on the handset 2026-11-09).  The path backend
   * owns the fd and observes ENODEV on its own next dispatch.  We release our
   * tracking entry so a replug with the same event name can be added again. */
  write_input_state("hotplug-remove");
#endif
  st("HOTPLUG_REMOVE node=%s marked-removed tracked=%d (libinput owns fd teardown)", name, tracked_count());
  if (g_hotplug_stdout) printf("HOTPLUG REMOVE %s MARKED_REMOVED tracked=%d\n", name, tracked_count());
}

/* ==========================================================================
 * PART 5 — the inotify watcher (deployed build, Linux only)
 *
 * The watcher thread NEVER touches libinput: it only pushes {op,name} into the
 * bounded ring.  The compositor's main loop drains it from libinput_dispatch().
 * If inotify is unavailable the shim degrades to "no hotplug" and says so; it
 * never aborts the compositor.
 * ==========================================================================*/
#ifndef NUXEL_SHIM_SELFTEST
#ifdef NUXEL_HAVE_INOTIFY
static int g_watch_fd = -1;

static void *watch_thread(void *arg) {
  (void)arg;
  char buf[4096] __attribute__((aligned(__alignof__(struct inotify_event))));
  for (;;) {
    ssize_t len = read(g_watch_fd, buf, sizeof buf);
    if (len <= 0) {
      if (len < 0 && (errno == EAGAIN || errno == EWOULDBLOCK)) {
        retry_tick();
        usleep(200000);
        continue;
      }
      if (len < 0 && errno == EINTR) continue;
      break;
    }
    for (char *p = buf; p < buf + len; ) {
      struct inotify_event *ev = (struct inotify_event *)p;
      p += sizeof(struct inotify_event) + ev->len;
      if (!ev->len) continue;
      if (node_order(ev->name) < 0) continue;
      int op = (ev->mask & (IN_CREATE | IN_MOVED_TO | IN_ATTRIB)) ? HQ_ADD : HQ_REMOVE;
      hq_push(op, ev->name);
    }
    retry_tick();
  }
  st("HOTPLUG_WATCH_ENDED");
  return NULL;
}

static void watch_start(void) {
  if (g_watch_fd >= 0) return;
  g_watch_fd = inotify_init1(IN_NONBLOCK | IN_CLOEXEC);
  if (g_watch_fd < 0) { st("HOTPLUG_WATCH_UNAVAILABLE inotify_init1 errno=%d", errno); return; }
  int wd = inotify_add_watch(g_watch_fd, DEV_INPUT_DIR,
                            IN_CREATE | IN_MOVED_TO | IN_DELETE | IN_MOVED_FROM | IN_ATTRIB);
  if (wd < 0) {
    st("HOTPLUG_WATCH_FAIL path=%s errno=%d", DEV_INPUT_DIR, errno);
    close(g_watch_fd); g_watch_fd = -1;
    return;
  }
  pthread_t th;
  if (pthread_create(&th, NULL, watch_thread, NULL) == 0) {
    pthread_detach(th);
    st("HOTPLUG_WATCH_READY path=%s (bounded queue %d)", DEV_INPUT_DIR, HQ_CAP);
  } else {
    st("HOTPLUG_WATCH_THREAD_FAIL (no hotplug; compositor unaffected)");
  }
}
#else
static void watch_start(void) { st("HOTPLUG_WATCH_UNAVAILABLE (this build has no inotify)"); }
#endif
#else
/* The offline harness never has a watcher thread; the hotplug *logic* it feeds
   is exercised through hq_push/hq_drain instead (see PART 6). */
static void watch_start(void) __attribute__((unused));
static void watch_start(void) {}
#endif /* !NUXEL_SHIM_SELFTEST */

/* ==========================================================================
 * PART 6 — offline selftest harness (the same decision code, no phone)
 * ==========================================================================*/
#ifdef NUXEL_SHIM_SELFTEST
static int selftest_scan(const char *root) {
  g_log_stdout = 1;
  g_fixture_root = root;
  struct cand sel[MAX_NODES];
  scan_nodes(root, sel, MAX_NODES, 1);
  /* ZERO_DEVICES is never a failure: the compositor must survive device absence. */
  printf("SELFTEST_RC=0\n");
  return 0;
}

static int selftest_hotplug(const char *root, const char *opsfile) {
  g_log_stdout = 1;
  g_fixture_root = root;
  g_hotplug_stdout = 1;
  FILE *f = fopen(opsfile, "r");
  if (!f) { fprintf(stderr, "selftest: cannot open ops file %s\n", opsfile); return 2; }
  char line[256];
  while (fgets(line, sizeof line, f)) {
    char op[16], name[NAME_MAX_];
    if (line[0] == '#') continue;
    if (sscanf(line, "%15s %63s", op, name) != 2) continue;
    if (!strcmp(op, "add")) hq_push(HQ_ADD, name);
    else if (!strcmp(op, "remove")) hq_push(HQ_REMOVE, name);
    else if (!strcmp(op, "drain")) hq_drain();
  }
  fclose(f);
  hq_drain();
  printf("TRACKED final=%d\n", tracked_count());
  printf("SELFTEST_RC=0\n");
  return 0;
}

int main(int argc, char **argv) {
  if (argc >= 3 && !strcmp(argv[1], "--scan")) return selftest_scan(argv[2]);
  if (argc >= 4 && !strcmp(argv[1], "--hotplug")) return selftest_hotplug(argv[2], argv[3]);
  fprintf(stderr, "usage: %s --scan <fixture-root> | --hotplug <fixture-root> <ops-file>\n", argv[0]);
  return 2;
}
#endif
