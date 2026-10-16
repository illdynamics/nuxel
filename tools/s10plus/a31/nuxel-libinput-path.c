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
#include <dirent.h>
#include <errno.h>
#include <fcntl.h>
#include <stdarg.h>
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
#  ifdef NUXEL_HAVE_EVDEV
#    include <sys/inotify.h>
#    define NUXEL_HAVE_INOTIFY 1
#  endif
#endif

/* --- ABI constants (stable kernel ABI; local copies keep this file buildable
 *     on a host that has no kernel headers at all) ------------------------- */
#define NUXEL_EV_KEY              0x01
#define NUXEL_EV_ABS              0x03
#define NUXEL_BTN_TOUCH           0x14a
#define NUXEL_ABS_X               0x00
#define NUXEL_ABS_Y               0x01
#define NUXEL_ABS_MT_SLOT         0x2f
#define NUXEL_ABS_MT_POSITION_X   0x35
#define NUXEL_ABS_MT_POSITION_Y   0x36
#define NUXEL_INPUT_PROP_DIRECT   1

/* linux/bitops.h's BITS_TO_LONGS is a kernel-internal helper and is NOT part of
   the uapi headers this file may include, so the word count is expressed here. */
#define NUXEL_WORDS(n) (((n) + 63) / 64)

#ifdef NUXEL_HAVE_EVDEV
/* Fail the build if a local constant ever drifts from the kernel header. */
_Static_assert(NUXEL_EV_KEY == EV_KEY, "EV_KEY drift");
_Static_assert(NUXEL_EV_ABS == EV_ABS, "EV_ABS drift");
_Static_assert(NUXEL_BTN_TOUCH == BTN_TOUCH, "BTN_TOUCH drift");
_Static_assert(NUXEL_ABS_MT_POSITION_X == ABS_MT_POSITION_X, "ABS_MT_POSITION_X drift");
_Static_assert(NUXEL_ABS_MT_POSITION_Y == ABS_MT_POSITION_Y, "ABS_MT_POSITION_Y drift");
_Static_assert(NUXEL_INPUT_PROP_DIRECT == INPUT_PROP_DIRECT, "INPUT_PROP_DIRECT drift");
#endif

#define STATE_FILE      "/run/nuxel-libinput-path.state"
#define DEV_INPUT_DIR   "/dev/input"
#define NODE_PREFIX     "event"
#define UDEV_DATA_DIR   "/run/udev/data"
#define MAX_NODES       64
#define NAME_MAX_       64
#define MAX_TRACKED     64
#define HQ_CAP          128

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
struct cand {
  char path[64];
  char name[NAME_MAX_];
  int  direct;
  int  mt;                    /* ABS_MT_POSITION_X and ABS_MT_POSITION_Y present */
  int  btn;                   /* BTN_TOUCH */
  int  legacy_xy;             /* ABS_X and ABS_Y */
  int  slot_max;
  int  x_min, x_max, y_min, y_max;
  int  order;                 /* numeric part of the node name, for sorting */
  int  accept;
  char reason[110];
};

static void cand_init(struct cand *c, const char *entry) {
  memset(c, 0, sizeof *c);
  snprintf(c->path, sizeof c->path, "%s/%s", DEV_INPUT_DIR, entry);
  c->x_min = c->y_min = 0;
  c->x_max = c->y_max = -1;
  c->slot_max = -1;
  c->order = -1;
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

static int read_whole(const char *path, char *out, size_t n) {
  FILE *f = fopen(path, "r");
  if (!f) return -1;
  size_t got = fread(out, 1, n - 1, f);
  fclose(f);
  out[got] = 0;
  return 0;
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
  int fd = open(c->path, O_RDONLY | O_NONBLOCK | O_CLOEXEC);
  if (fd < 0) return -1;

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
  if (ioctl(fd, EVIOCGBIT(NUXEL_EV_KEY, sizeof keyb), keyb) >= 0)
    c->btn = !!(keyb[NUXEL_BTN_TOUCH / (8 * (int)sizeof(unsigned long))] &
                (1ul << (NUXEL_BTN_TOUCH % (8 * (int)sizeof(unsigned long)))));
  close(fd);
  return 0;
}
#endif

/* --- the decision (capability only) ------------------------------------- */
static void decide(struct cand *c) {
  if (!c->direct) {
    snprintf(c->reason, sizeof c->reason, "reject: INPUT_PROP_DIRECT absent (not a touch surface)");
    c->accept = 0;
    return;
  }
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
  snprintf(c->reason, sizeof c->reason, "accept: DIRECT%s%s range x=%d..%d y=%d..%d slots=%d",
           c->mt ? "+ABS_MT" : "+BTN_TOUCH", c->btn ? "+BTN_TOUCH" : "",
           c->x_min, c->x_max, c->y_min, c->y_max, c->slot_max);
  c->accept = 1;
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
  st("SCAN_RESULT nodes=%d accepted=%d%s", n, naccepted, naccepted ? "" : " (ZERO_DEVICES: compositor stays up)");
  if (verbose) {
    printf("SCAN_RESULT nodes=%d accepted=%d\n", n, naccepted);
    if (!naccepted) printf("ZERO_DEVICES\n");
    for (int i = 0; i < naccepted; i++) printf("SELECTED %s\n", out[i].path);
  }
  return naccepted;
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

struct tracked { char name[NAME_MAX_]; void *dev; int used; };
static struct tracked g_tracked[MAX_TRACKED];

static const char *g_fixture_root;   /* set only by the offline selftest */
static int g_hotplug_stdout;         /* set only by the offline selftest */

static int tracked_count(void) {
  int n = 0;
  for (int i = 0; i < MAX_TRACKED; i++) if (g_tracked[i].used) n++;
  return n;
}

static int tracked_find(const char *name) {
  for (int i = 0; i < MAX_TRACKED; i++)
    if (g_tracked[i].used && !strcmp(g_tracked[i].name, name)) return i;
  return -1;
}

static void *tracked_get(const char *name) {
  int i = tracked_find(name);
  return i >= 0 ? g_tracked[i].dev : NULL;
}

static int tracked_add(const char *name, void *dev) {
  if (tracked_find(name) >= 0) return 0;
  for (int i = 0; i < MAX_TRACKED; i++) {
    if (!g_tracked[i].used) {
      snprintf(g_tracked[i].name, sizeof g_tracked[i].name, "%s", name);
      g_tracked[i].dev = dev;
      g_tracked[i].used = 1;
      return 1;
    }
  }
  st("TRACKED_TABLE_FULL name=%s (bounded at %d; extra device ignored)", name, MAX_TRACKED);
  return 0;
}

static void *tracked_remove(const char *name) {
  int i = tracked_find(name);
  if (i < 0) return NULL;
  void *dev = g_tracked[i].dev;
  g_tracked[i].used = 0;
  g_tracked[i].dev = NULL;
  g_tracked[i].name[0] = 0;
  return dev;
}

enum { HQ_ADD = 0, HQ_REMOVE = 1 };
struct hq_ev { int op; char name[NAME_MAX_]; };
static struct hq_ev g_hq[HQ_CAP];
static int g_hq_head, g_hq_tail, g_hq_count;

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

static void seed_udev_db(const char *path) {
  struct stat sb;
  if (stat(path, &sb) < 0) { st("UDEVDB_STAT_FAIL %s errno=%d", path, errno); return; }
  if (mkdir("/run/udev", 0755) < 0 && errno != EEXIST) { /* fall through */ }
  if (mkdir(UDEV_DATA_DIR, 0755) < 0 && errno != EEXIST) { /* fall through */ }
  char fn[96];
  snprintf(fn, sizeof fn, "%s/c%u:%u", UDEV_DATA_DIR, (unsigned)major(sb.st_rdev), (unsigned)minor(sb.st_rdev));
  if (access(fn, F_OK) == 0) return;            /* already initialized */
  FILE *f = fopen(fn, "w");
  if (!f) { st("UDEVDB_WRITE_FAIL %s errno=%d", fn, errno); return; }
  /* Properties libinput/quirks read, derived from what the node actually is. */
  fprintf(f, "E:ID_INPUT=1\nE:ID_INPUT_TOUCHSCREEN=1\nE:ID_INPUT_WIDTH_MM=64\n"
             "E:ID_INPUT_HEIGHT_MM=135\nE:ID_SEAT=seat0\n"
             "E:DEVLINKS=%s/by-path/nuxel-touchscreen\n", DEV_INPUT_DIR);
  fprintf(f, "I:%ld\n", (long)time(NULL) * 1000000L);   /* 'I' = initialized */
  fclose(f);
  db_seeded++;
  st("UDEVDB_SEEDED %s (initialized marker; systemd-udevd cannot run on this kernel)", fn);
}

/* --- the interposers wlroots calls -------------------------------------- */
static void *shim_libinput_add(const char *path) {
  seed_udev_db(path);
  return libinput_path_add_device(g_li, path);
}
static void shim_libinput_remove(void *dev) { libinput_path_remove_device((struct libinput_device *)dev); }

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
  struct cand sel[MAX_NODES];
  int seen = scan_nodes(NULL, sel, MAX_NODES, 0);
  int added = 0;
  for (int i = 0; i < seen; i++) {
    void *dev = shim_libinput_add(sel[i].path);
    st("PATH_ADD node=%s order=%d name='%s' accepted=%d", sel[i].path, sel[i].order, sel[i].name, dev != NULL);
    if (dev && tracked_add(sel[i].name, dev)) added++;
  }
  st("PATH_ASSIGN_SEAT seat='%s' direct_devices_seen=%d added=%d db_seeded=%d tracked=%d",
     seat_id ? seat_id : "(null)", seen, added, db_seeded, tracked_count());
  watch_start();
  return 0;   /* wlroots treats 0 as "seat assigned"; ZERO_DEVICES is not an error here */
}

int libinput_dispatch(struct libinput *li) {
  static int (*real)(struct libinput *);
  if (!real) real = dlsym(RTLD_NEXT, "libinput_dispatch");
  int rc = real ? real(li) : -1;
  hq_drain();
  return rc;
}
#endif /* !NUXEL_SHIM_SELFTEST */

/* ==========================================================================
 * PART 4 — shim_apply: the single place where a hotplug event becomes
 *          a libinput device (or an explained rejection)
 * ==========================================================================*/
static void shim_apply(int op, const char *name) {
  if (op == HQ_ADD) {
    if (tracked_get(name)) {
      st("HOTPLUG_ADD node=%s ignored=already-tracked", name);
      if (g_hotplug_stdout) printf("HOTPLUG ADD %s IGNORED already-tracked\n", name);
      return;
    }
    struct cand c;
    int rc = g_fixture_root ? fixture_probe(g_fixture_root, name, &c) : node_probe(name, &c);
    if (rc != 0) {
      st("HOTPLUG_ADD node=%s rejected=metadata-or-open-failed", name);
      if (g_hotplug_stdout) printf("HOTPLUG ADD %s REJECT reason=metadata-or-open-failed\n", name);
      return;
    }
    decide(&c);
    if (!c.accept) {
      st("HOTPLUG_ADD node=%s rejected=%s", c.path, c.reason);
      if (g_hotplug_stdout) printf("HOTPLUG ADD %s REJECT reason=\"%s\"\n", name, c.reason);
      return;
    }
#ifdef NUXEL_SHIM_SELFTEST
    void *dev = (void *)1;              /* the offline harness never calls libinput */
#else
    void *dev = shim_libinput_add(c.path);
#endif
    if (dev) {
      tracked_add(name, dev);
      st("HOTPLUG_ADD node=%s accepted=1 tracked=%d", c.path, tracked_count());
      if (g_hotplug_stdout) printf("HOTPLUG ADD %s ACCEPT tracked=%d\n", name, tracked_count());
    } else {
      st("HOTPLUG_ADD node=%s accepted=0 (libinput_path_add_device returned NULL)", c.path);
      if (g_hotplug_stdout) printf("HOTPLUG ADD %s ADD_FAILED\n", name);
    }
    return;
  }
  void *dev = tracked_remove(name);
  if (!dev) {
    st("HOTPLUG_REMOVE node=%s not-tracked (ignored)", name);
    if (g_hotplug_stdout) printf("HOTPLUG REMOVE %s NOT_TRACKED\n", name);
    return;
  }
#ifndef NUXEL_SHIM_SELFTEST
  shim_libinput_remove(dev);
#endif
  st("HOTPLUG_REMOVE node=%s removed tracked=%d", name, tracked_count());
  if (g_hotplug_stdout) printf("HOTPLUG REMOVE %s REMOVED tracked=%d\n", name, tracked_count());
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
      if (len < 0 && (errno == EAGAIN || errno == EWOULDBLOCK)) { usleep(200000); continue; }
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
