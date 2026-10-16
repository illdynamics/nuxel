/* nuxel-touch-arm — arm the Samsung sec_ts touchscreen on the running S10+.
 *
 * WHY (measured on hardware, cycle A29)
 *   Linux4/android_kernel_samsung_exynos9820 @ f7194c1d,
 *   drivers/input/touchscreen/sec_ts/y771/sec_ts.c:
 *
 *     probe()          : sec_ts_power(ts,true); ts->power_status = POWER_ON;
 *     sec_ts_input_open(): ret = sec_ts_start_device(ts);       // returns 0 always
 *     sec_ts_start_device(): if (power_status == POWER_ON) {
 *                                "%s: already power on"; goto out; }   // ret = -1
 *                            ... sec_ts_wait_for_ready(); sec_ts_reinit();
 *                            SEC_TS_CMD_SENSE_ON; enable_irq();        // SKIPPED
 *     sec_ts_input_close(): sec_ts_stop_device();   // disable_irq + POWER_OFF
 *
 *   So the first open(2) of the panel touchscreen always short-circuits and the
 *   controller's IRQ is never enabled: open(2) still succeeds, no events ever
 *   arrive, and no error is reported anywhere.  This is the real reason A23..A28
 *   never captured a finger (the kernel log on the handset says exactly:
 *       sec_ts 4-0048: sec_ts_start_device: already power on
 *       sec_ts 4-0048: sec_ts_input_open: Failed to start device  ).
 *
 *   The lever that works is the driver's own factory stop command
 *   (module_off_master -> sec_ts_stop_device(): POWER_OFF + disable_irq)
 *   followed by the driver's own display notifier, which re-runs
 *   sec_ts_start_device(): power on + wait_for_ready + reinit + SENSE_ON +
 *   enable_irq().  The notifier is driven by an fb0 blank 1 -> 0 transition,
 *   the same operation the kernel's own panel notifier performs.  A reader fd is
 *   then held open, and every other reader (libinput inside the compositor, the
 *   fallback UI) receives the events too.
 *
 * NO GUESSING: the node is chosen by capability (ABS_MT_POSITION_X/Y +
 * INPUT_PROP_DIRECT), never by event number; the axis ranges are read from the
 * device.  Device state is logged to /run/nuxel-touch-arm.state so the arming is
 * evidence, not a claim.
 */
#define _GNU_SOURCE
#include <dirent.h>
#include <stdarg.h>
#include <errno.h>
#include <fcntl.h>
#include <linux/input.h>
#include <stdio.h>
#include <string.h>
#include <sys/ioctl.h>
#include <sys/select.h>
#include <sys/stat.h>
#include <sys/syscall.h>
#include <time.h>
#include <unistd.h>

#define STATE "/run/nuxel-touch-arm.state"
#define MAXDEV 32
#define EVSZ (ssize_t)sizeof(struct input_event)

struct dev {
  char path[64];
  char name[64];
  int mt, direct, btn, fd;
  int minx, maxx, miny, maxy, slots;
};

static void st(const char *fmt, ...) __attribute__((format(printf, 1, 2)));
static void st(const char *fmt, ...) {
  va_list ap;
  FILE *f = fopen(STATE, "a");   /* append: the touch history is evidence */
  if (!f) return;
  time_t t = time(NULL);
  struct tm tm;
  gmtime_r(&t, &tm);
  fprintf(f, "%04d-%02d-%02dT%02d:%02d:%02dZ ", tm.tm_year + 1900, tm.tm_mon + 1,
          tm.tm_mday, tm.tm_hour, tm.tm_min, tm.tm_sec);
  va_start(ap, fmt);
  vfprintf(f, fmt, ap);
  va_end(ap);
  fputc('\n', f);
  fclose(f);
}

static int ev_read_name(int fd, char *out, size_t n) {
  char buf[256] = {0};
  long r = ioctl(fd, EVIOCGNAME(sizeof buf - 1), buf);
  if (r < 0) return -1;
  snprintf(out, n, "%s", buf);
  return 0;
}

static int bit(const unsigned long *b, int c) {
  return (b[c / (8 * sizeof(long))] >> (c % (8 * sizeof(long)))) & 1UL;
}

static int probe(const char *path, struct dev *d) {
  memset(d, 0, sizeof *d);
  d->fd = -1;
  int fd = open(path, O_RDONLY | O_NONBLOCK);
  if (fd < 0) return -1;
  unsigned long absb[(ABS_MAX + 1) / (8 * sizeof(long)) + 1] = {0};
  unsigned long keyb[(KEY_MAX + 1) / (8 * sizeof(long)) + 1] = {0};
  unsigned long propb[1] = {0};
  if (ev_read_name(fd, d->name, sizeof d->name) < 0) { close(fd); return -1; }
  if (ioctl(fd, EVIOCGBIT(EV_ABS, sizeof absb), absb) < 0) { close(fd); return -1; }
  ioctl(fd, EVIOCGBIT(EV_KEY, sizeof keyb), keyb);
  ioctl(fd, EVIOCGPROP(sizeof propb), propb);
  d->mt = bit(absb, ABS_MT_POSITION_X) && bit(absb, ABS_MT_POSITION_Y);
  d->btn = bit(keyb, BTN_TOUCH);
  d->direct = bit(propb, INPUT_PROP_DIRECT);
  struct input_absinfo ai;
  if (ioctl(fd, EVIOCGABS(ABS_MT_POSITION_X), &ai) == 0) { d->minx = ai.minimum; d->maxx = ai.maximum; }
  if (ioctl(fd, EVIOCGABS(ABS_MT_POSITION_Y), &ai) == 0) { d->miny = ai.minimum; d->maxy = ai.maximum; }
  d->slots = 1;
  if (ioctl(fd, EVIOCGABS(ABS_MT_SLOT), &ai) == 0) d->slots = ai.maximum + 1;
  snprintf(d->path, sizeof d->path, "%s", path);
  d->fd = fd; /* caller decides */
  return 0;
}

/* Arm the controller through the driver's OWN factory commands.
 *
 * MEASURED ON HARDWARE (A29): the open -> close -> open trick does NOT work -
 * sec_ts_input_close() is never reached on this device (400 s of kernel log with
 * zero "sec_ts_stop_device" lines, while "already power on" repeats every ~2 s
 * from the display notifier), so power_status stays POWER_ON and the real start
 * path - the only one that calls enable_irq() - is unreachable that way.
 *
 * The driver does expose the stop/start pair as factory commands
 * (drivers/input/touchscreen/sec_ts/y771/sec_ts_fn.c):
 *      module_off_master -> sec_ts_stop_device()   (disable_irq + POWER_OFF)
 *      module_on_master  -> sec_ts_start_device()  (power on + SENSE_ON + enable_irq)
 * Issuing module_off_master moved the sec_ts IRQ counter for the first time on
 * this handset (61 -> 63): the path works.
 *
 * Sequence used here:  module_off_master -> fb0 blank 1 -> 0 -> hold an fd   [*]
 *
 * [*] MEASURED (A29b, handset): a trailing `module_on_master` written from
 *     userspace is NOT harmless - right after it the controller was left with
 *     "sec_ts_i2c_read: POWER_STATUS : OFF" and the IC stopped sensing (one tap
 *     window produced IRQ 14-14, all_touch_count TTCN:0).  The start that really
 *     start is the driver's own: after a *successful* stop, the notifier's
 *     sec_ts_input_open() runs sec_ts_start_device() -> sec_ts_wait_for_ready ->
 *     sec_ts_reinit -> SENSE_ON -> enable_irq() and ends by printing
 *     "module_on_master: OK" itself (measured 2026-09-15T00:17:24Z, IRQ 16->225
 *     with a real finger: "[P] tID:0.0 z:63 ... loc:E.C", "[R] tID:2 ...").
 *     A client open() alone does NOT trigger it (libinput keeps dev->users > 0).
 *     The tsp command result is read back with a timeout - the cmd engine can
 *     answer EBUSY - and logged, so the arming is evidence, never a claim.
 */
#define TSP_CMD "/sys/class/sec/tsp/cmd"

static int tsp_cmd(const char *cmd) {
  for (int try = 0; try < 8; try++) {
    int fd = open(TSP_CMD, O_WRONLY);
    if (fd < 0) { usleep(200000); continue; }
    char line[64];
    int n = snprintf(line, sizeof line, "%s\n", cmd);
    ssize_t w = write(fd, line, (size_t)n);
    int err = errno;
    close(fd);
    if (w > 0) return 0;
    if (err == EBUSY) { usleep(250000); continue; }   /* cmd engine busy */
    usleep(200000);
  }
  return -1;
}

/* Read /sys/class/sec/tsp/cmd_result without ever blocking: the attribute waits
 * for the command engine, which the ~2 s panel-notifier storm can hold busy. */
static int tsp_result(char *out, size_t n) {
  out[0] = 0;
  int fd = open("/sys/class/sec/tsp/cmd_result", O_RDONLY | O_NONBLOCK);
  if (fd < 0) return -1;
  int rc = -1;
  for (int i = 0; i < 40; i++) {                 /* up to ~2 s */
    ssize_t r = read(fd, out, n - 1);
    if (r > 0) { out[r] = 0; rc = 0; break; }
    if (r < 0 && errno != EAGAIN && errno != EWOULDBLOCK && errno != EINTR) break;
    usleep(50000);
    lseek(fd, 0, SEEK_SET);
  }
  close(fd);
  for (size_t i = 0; out[i]; i++) if (out[i] == '\n') out[i] = 0;
  return rc;
}

static int arm(struct dev *d) {
  char res[64] = "";
  close(d->fd);
  d->fd = -1;
  int off = -1;
  for (int try = 0; try < 6 && off != 0; try++) {
    if (tsp_cmd("module_off_master") == 0) {      /* stop: POWER_OFF + disable_irq */
      usleep(300000);
      tsp_result(res, sizeof res);
      if (strstr(res, "module_off_master:OK")) off = 0;
      else if (res[0]) snprintf(res, sizeof res, "unexpected '%s'", res);
    }
    if (off != 0) usleep(400000);
  }
  /* REAL START.  The only path that reaches SENSE_ON + enable_irq() is
   * sec_ts_start_device(), and on this handset it is reached from the driver's
   * own display notifier (sec_ts_fb_notifier_callback -> sec_ts_input_open), not
   * from a client open(): libinput/the compositor already hold the evdev node,
   * so dev->users never returns to 0 and input_open is not called again
   * (MEASURED 2026-09-15T00:22Z: after a successful module_off_master a plain
   * open() left "POWER_STATUS : OFF" and IRQ frozen at 304).
   * So the driver's notifier is driven directly, exactly as the kernel's own
   * panel notifier does: fb0 blank 1 -> 0 (FB_BLANK_NORMAL -> FB_BLANK_UNBLANK).
   * MEASURED immediately after that transition (00:24:24Z):
   *   sec_ts_power: on: avdd:on, dvdd:on / sec_ts_wait_for_ready
   *   sec_ts_reinit: charger=0x0, touch_functions=0x61, Power mode=0x2
   *   sec_ts_read_event: STATUS 1d 61 2 2 3 0 0 0 / "Normal changed"
   *   sec_ts_get_touch_function: touch_functions:61 ic_status:61
   */
  int fb = open("/sys/class/graphics/fb0/blank", O_WRONLY);
  int blank_rc = -1;
  if (fb >= 0) {
    blank_rc = 0;
    if (write(fb, "1", 1) < 0) blank_rc = -1;
    usleep(400000);
    if (write(fb, "0", 1) < 0) blank_rc = -1;
    close(fb);
  }
  int fd = open(d->path, O_RDONLY | O_NONBLOCK);   /* also keep a reader fd */
  if (fd < 0) { st("ARM_OPEN_FAIL path=%s errno=%d", d->path, errno); return -1; }
  usleep(500000);
  char pw[64] = "";
  FILE *f = fopen("/sys/class/sec/tsp/power", "r");
  if (f) { if (fgets(pw, sizeof pw, f)) { for (size_t i = 0; pw[i]; i++) if (pw[i] == '\n') pw[i] = 0; } fclose(f); }
  st("ARM_DONE off_rc=%d off_result='%s' fb_blank_rc=%d power='%s'", off, res, blank_rc, pw);
  d->fd = fd;            /* held for the lifetime of the unit: the armed state survives */
  return 0;
}

static void tsp_state(char *out, size_t n) {
  out[0] = 0;
  FILE *f = fopen("/sys/class/sec/tsp/status", "r");
  if (!f) { snprintf(out, n, "unavailable"); return; }
  size_t got = fread(out, 1, n - 1, f);
  out[got] = 0;
  for (size_t i = 0; i < got; i++) if (out[i] == '\n') out[i] = 0;
  fclose(f);
}

int main(void) {
  struct dev devs[MAXDEV];
  int ndev = 0;
  DIR *dp = opendir("/dev/input");
  if (!dp) { st("SCAN_FAIL errno=%d", errno); return 1; }
  struct dirent *e;
  while ((e = readdir(dp)) && ndev < MAXDEV) {
    if (strncmp(e->d_name, "event", 5) != 0) continue;
    char p[64];
    snprintf(p, sizeof p, "/dev/input/%s", e->d_name);
    struct dev d;
    if (probe(p, &d) == 0) { close(d.fd); d.fd = -1; devs[ndev++] = d; }
  }
  closedir(dp);

  int pick = -1;
  for (int i = 0; i < ndev && pick < 0; i++)
    if (devs[i].mt && devs[i].direct) pick = i;
  for (int i = 0; i < ndev && pick < 0; i++)
    if (devs[i].mt && strstr(devs[i].name, "touchscreen")) pick = i;
  for (int i = 0; i < ndev && pick < 0; i++)
    if (devs[i].mt) pick = i;
  if (pick < 0) { st("NO_TOUCH_DEVICE devices=%d", ndev); return 2; }
  struct dev *t = &devs[pick];

  char before[256];
  tsp_state(before, sizeof before);
  if (arm(t) < 0) return 3;
  char after[256];
  tsp_state(after, sizeof after);
  st("ARMED_OK path=%s name='%s' mt=%d direct=%d btn=%d slots=%d x=[%d.%d] y=[%d.%d] "
     "tsp_before='%s' tsp_after='%s'",
     t->path, t->name, t->mt, t->direct, t->btn, t->slots, t->minx, t->maxx,
     t->miny, t->maxy, before, after);

  /* Keep the fd open for the lifetime of the unit and log contact evidence. */
  int cur = 0, on[16] = {0};
  long points = 0;
  for (;;) {
    fd_set rf;
    FD_ZERO(&rf);
    FD_SET(t->fd, &rf);
    struct timeval tv = {5, 0};
    int r = select(t->fd + 1, &rf, NULL, NULL, &tv);
    if (r < 0) { if (errno == EINTR) continue; st("SELECT_FAIL errno=%d", errno); return 4; }
    if (r == 0) continue;
    struct input_event ev[64];
    ssize_t n = read(t->fd, ev, sizeof ev);
    if (n <= 0) { if (n < 0 && (errno == EAGAIN || errno == EINTR)) continue;
                  st("READ_FAIL errno=%d", errno); return 5; }
    for (ssize_t i = 0; i < n / EVSZ; i++) {
      if (ev[i].type == EV_ABS && ev[i].code == ABS_MT_SLOT) cur = ev[i].value % 16;
      else if (ev[i].type == EV_ABS && ev[i].code == ABS_MT_TRACKING_ID) {
        if (ev[i].value >= 0) on[cur] = 1; else on[cur] = 0;
      } else if (ev[i].type == EV_SYN && ev[i].code == SYN_REPORT) {
        for (int s = 0; s < 16; s++)
          if (on[s]) { points++; st("TOUCH_POINT slot=%d n=%ld", s, points); break; }
      }
    }
  }
}
