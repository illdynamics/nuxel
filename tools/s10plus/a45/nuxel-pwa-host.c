/* nuxel-pwa-host — the display host for the EXISTING Nuxel launcher.
 *
 * This is NOT a launcher.  It renders the launcher that already exists and
 * already runs in the UTM VM - /usr/share/nuxel/nuxel-home, served on
 * 127.0.0.1:8000 by the same static server the VM uses (services/nuxel-web
 * .service) - in the same engine family the VM renders it with (WebKitGTK).
 * All UI, styling, icons, ordering and app-launching behaviour stay in
 * pwa/nuxel-home (index.html, css/*, js/apps.js registry, js/launcher.js,
 * js/app.js).  js/app.js itself opens a tapped application as a fullscreen
 * iframe of that registry entry, so one view is enough and the app registry is
 * never duplicated here.
 *
 * Differences from the VM, and nothing else:
 *   * Wayland-only: the view is a Wayland client of the stock phoc compositor
 *     running with the headless backend (no /dev/dri on this handset); the
 *     composited frames reach the AMOLED through nuxel-wl-fb.
 *   * Software rendering: WEBKIT_DISABLE_COMPOSITING_MODE=1 is exported by the
 *     session wrapper because there is no EGL/GBM device on this kernel.
 *   * The URL is read from the environment so the same binary can host any
 *     registry entry (NUXEL_HOME_URL).
 *
 * Evidence: NUXEL_HOME_READY / NUXEL_HOME_LOAD_FAIL and the iframe/app
 * navigations are written to /run/nuxel-home.state, and the readiness file
 * /run/nuxel-launcher-ready is what the fallback unit waits for.
 */
#include <gtk/gtk.h>
#include <webkit2/webkit2.h>
#include <ctype.h>
#include <errno.h>
#include <dirent.h>
#include <fcntl.h>
#include <signal.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/ioctl.h>
#include <sys/socket.h>
#ifdef __linux__
#include <linux/netlink.h>
#endif
#include <sys/stat.h>
#include <sys/types.h>
#include <sys/wait.h>
#include <termios.h>
#include <time.h>
#include <unistd.h>
#include <pty.h>

/* REVISION A31 (2026-10-16, beta finalizer) - three corrections:
 *   1. BOOT ANIMATION OWNERSHIP (mission 9).  On the S10+ the OS has already
 *      played the authoritative boot animation from the initramfs before this
 *      view exists, and the launcher's own <div id="boot-splash"> fullscreen
 *      <video> is therefore a SECOND, redundant animation that can flash over
 *      the launcher and intercept input.  This host now tells the launcher that
 *      the OS owns the animation (?boot=os); pwa/nuxel-home/js/app.js removes
 *      the splash element for that launch mode.  NUXEL_PWA_SPLASH=1 restores the
 *      PWA's own splash (the VM/desktop behaviour) - nothing global was deleted.
 *   2. PERMISSIONS (mission 16).  A29 granted EVERY permission request from ANY
 *      page.  A31 denies by default and grants only what this device and this
 *      trusted local origin actually have; every decision is logged.
 *   3. WEB PROCESS SUPERVISION (mission 15).  A dead WebKitWebProcess is now
 *      detected (web-process-terminated) and reloaded, bounded, instead of
 *      leaving a blank view forever.
 *
 * REVISION A33 (2026-10-16, beta finalizer, briq-02a/02b) - the launcher's Settings
 * surface must be able to persist the two boot documents this cycle owns, and the
 * verbose-boot log overlay must be able to read the boot evidence:
 *   7. four new allow-list entries, no new verbs:
 *        verbose-boot       (WRITABLE) /etc/nuxel/boot/verbose-boot.json
 *        animation-handoff  (read)     /etc/nuxel/boot/animation-handoff.json
 *        verbose-boot-state (read)     /run/nuxel/verbose-boot
 *        fb-owner           (read)     /var/lib/nuxel/fb-owner
 *        anim-handoff       (read)     /run/nuxel-anim-handoff
 *        boot-stage-log     (read)     /var/log/nuxel/boot-stage.log
 *      The write path is unchanged (same-directory atomic rename), and the page
 *      still cannot name an arbitrary path: the name is resolved through this
 *      table only.
 *
 * REVISION A32 (2026-10-16, beta hardware finalizer) - the phone needs a real
 * backend for the launcher's Settings app, the hardware buttons and the Terminal
 * application (missions 9, 11, 12, 13 and 14).  Three additions, all of them
 * bounded and allow-listed - none of them is a new UI:
 *   4. nuxelHost: a script-message API for the *unmodified* launcher pages.
 *      config.get / config.set read and write ONLY the Nuxel settings files
 *      (/etc/nuxel/...), never arbitrary paths; system.action maps a small
 *      logical action set (screen-off/on/toggle, home, search, settings,
 *      open-terminal) onto the existing Nuxel services; term.* drives the
 *      terminal PTY.  Every call is logged with its verdict.
 *   5. A control FIFO /run/nuxel-pwa-host.cmd so the hardware-button manager can
 *      ask for the same logical actions without going through the web page.
 *   6. The Nuxel Terminal: a REAL PTY (forkpty) hosting /bin/sh, rendered by
 *      pwa/nuxel-apps/terminal.  One instance only - a second request focuses the
 *      existing window instead of spawning another shell (mission 13).
 */
#define STATE  "/run/nuxel-home.state"
#define READY  "/run/nuxel-launcher-ready"
#define DEFAULT_URL "http://127.0.0.1:8000/pwa/nuxel-home/index.html"

static void st(const char *fmt, ...) __attribute__((format(printf, 1, 2)));
static void st(const char *fmt, ...) {
  FILE *f = fopen(STATE, "a");
  if (!f) return;
  fprintf(f, "%ld ", (long)time(NULL));
  va_list ap; va_start(ap, fmt); vfprintf(f, fmt, ap); va_end(ap);
  fputc('\n', f); fclose(f);
}


/* ============================================================================
 * A32 — nuxelHost: the launcher's real backend on the phone
 *
 * The UTM build gets this from nuxel-http-bridge/nuxel-bridge (D-Bus + HTTP).
 * The handset has neither, so the same *logical* operations are served by the
 * process that hosts the launcher itself, over WebKit's script-message channel.
 * The launcher pages are not modified to use it: pwa/nuxel-home/js/host-bridge.js
 * exposes it as window.NuxelHost and relays iframe requests (same-origin
 * postMessage) so the Settings and Terminal PWAs use exactly the same API.
 *
 * Security: there is no shell, no path from the page, and no unvalidated verb.
 *   config.get/set   -> whitelisted files under /etc/nuxel/ (atomic replace)
 *   status.read      -> whitelisted read-only state files
 *   system.action    -> screen-off|screen-on|screen-toggle|home|search|settings|
 *                       open-terminal|volume-up|volume-down|volume-mute|
 *                       haptics-tap|haptics-navigation|haptics-switch|haptics-long
 *   term.input       -> bytes for the existing PTY
 *   term.close       -> end the terminal session
 * Anything else is refused and logged.
 * ==========================================================================*/

static WebKitWebView *view_new(void);
static void term_open_window(void);
static void uevent_open(void);
static void indicators_json(char *out, size_t outn);
static GtkWidget *g_main_window;
static WebKitWebView *g_main_view;

/* ============================================================================
 * Lockhead indicators — real sysfs/proc state, no invented values.
 *
 * charging: any external power_supply node with online=1.
 * charging animation: battery status is exactly "Charging".
 * USB data: a configfs gadget is bound AND the UDC is exactly configured.
 *           The power_supply online flag is deliberately not consulted.
 * live console: a running nuxel-console process holds an fd to the console tty
 *           (or a validated session lease from the initramfs launcher) AND the
 *           USB data link is currently configured.  A bind-mounted gadget, an
 *           existing /dev/ttyGS0 node, a lease that outlives the cable, or root
 *           access alone are each insufficient.
 * ==========================================================================*/
static int ind_read_line(const char *path, char *out, size_t outn) {
  if (!path || !out || outn < 2) return 0;
  FILE *f = fopen(path, "rb");
  if (!f) return 0;
  out[0] = 0;
  if (fgets(out, (int)outn, f)) {
    size_t n = strlen(out);
    while (n && (out[n-1] == '\n' || out[n-1] == '\r')) out[--n] = 0;
  }
  fclose(f);
  return out[0] != 0;
}

static int ind_path_exists(const char *p) {
  struct stat sb;
  return p && stat(p, &sb) == 0;
}

/* Roots are env-overridable so the offline C harness can exercise the exact
   same reader against a synthetic tree (the live host uses the defaults). */
static const char *ind_root(const char *env, const char *fallback) {
  const char *v = getenv(env);
  return (v && *v) ? v : fallback;
}

static int ind_eq_ci(const char *a, const char *b) {
  while (*a && *b) {
    if (tolower((unsigned char)*a) != tolower((unsigned char)*b)) return 0;
    a++; b++;
  }
  return *a == *b;
}

static int ind_online(const char *path) {
  char b[32];
  if (!ind_read_line(path, b, sizeof b)) return -1;
  return (b[0] == '1') ? 1 : (b[0] == '0' ? 0 : -1);
}

static void ind_power(int *external_power, int *charging) {
  int seen_battery = 0;
  char status[64] = "unknown";
  *external_power = 0;
  *charging = 0;
  DIR *d = opendir(ind_root("NUXEL_SYS_POWER_SUPPLY", "/sys/class/power_supply"));
  if (!d) return;
  struct dirent *de;
  while ((de = readdir(d))) {
    if (!strcmp(de->d_name, ".") || !strcmp(de->d_name, "..")) continue;
    char base[360], path[420], type[64] = "unknown", capbuf[32] = "";
    snprintf(base, sizeof base, "%s/%s", ind_root("NUXEL_SYS_POWER_SUPPLY", "/sys/class/power_supply"), de->d_name);
    if (!ind_path_exists(base)) continue;
    snprintf(path, sizeof path, "%s/type", base);
    ind_read_line(path, type, sizeof type);
    snprintf(path, sizeof path, "%s/capacity", base);
    ind_read_line(path, capbuf, sizeof capbuf);
    int capacity = capbuf[0] ? atoi(capbuf) : -1;
    if (ind_eq_ci(type, "Battery") || (ind_eq_ci(type, "unknown") && capacity >= 0)) {
      if (!seen_battery) {
        seen_battery = 1;
        snprintf(path, sizeof path, "%s/status", base);
        ind_read_line(path, status, sizeof status);
      }
      continue;
    }
    /* OTG/host mode is not charging. */
    if (ind_eq_ci(type, "otg") || ind_eq_ci(type, "usb_host")) continue;
    snprintf(path, sizeof path, "%s/online", base);
    if (ind_online(path) == 1) *external_power = 1;
  }
  closedir(d);
  *charging = seen_battery && ind_eq_ci(status, "Charging");
}

static int ind_gadget_bound(void) {
  DIR *d = opendir(ind_root("NUXEL_CONFIGFS_GADGET", "/sys/kernel/config/usb_gadget"));
  if (!d) return 0;
  int bound = 0;
  struct dirent *de;
  while ((de = readdir(d))) {
    if (!strcmp(de->d_name, ".") || !strcmp(de->d_name, "..")) continue;
    char path[420], value[128] = "";
    snprintf(path, sizeof path, "%s/%s/UDC", ind_root("NUXEL_CONFIGFS_GADGET", "/sys/kernel/config/usb_gadget"), de->d_name);
    if (ind_read_line(path, value, sizeof value) && value[0]) { bound = 1; break; }
  }
  closedir(d);
  return bound;
}

static int ind_pc_connected(void) {
  if (!ind_gadget_bound()) return 0;
  DIR *d = opendir(ind_root("NUXEL_SYS_UDC", "/sys/class/udc"));
  if (!d) return 0;
  int connected = 0;
  struct dirent *de;
  while ((de = readdir(d))) {
    if (!strcmp(de->d_name, ".") || !strcmp(de->d_name, "..")) continue;
    char path[420], state[64] = "";
    snprintf(path, sizeof path, "%s/%s/state", ind_root("NUXEL_SYS_UDC", "/sys/class/udc"), de->d_name);
    if (!ind_read_line(path, state, sizeof state)) continue;
    if (ind_eq_ci(state, "configured")) { connected = 1; break; }
  }
  closedir(d);
  /* `addressed` is only a pre-configuration handshake.  The vendor
     android_usb state is deliberately not a fallback because it may remain
     CONFIGURED after detach.  No fresh UDC proof means PC off. */
  return connected;
}

static int ind_cmdline_has(pid_t pid, const char *needle) {
  char path[512], buf[4096];
  snprintf(path, sizeof path, "%s/%d/cmdline", ind_root("NUXEL_PROC", "/proc"), (int)pid);
  FILE *f = fopen(path, "rb");
  if (!f) return 0;
  size_t n = fread(buf, 1, sizeof buf - 1, f);
  fclose(f);
  buf[n] = 0;
  return n && strstr(buf, needle) != NULL;
}

static int ind_pid_holds_tty(pid_t pid, const char *ttybase) {
  char fdpath[512];
  snprintf(fdpath, sizeof fdpath, "%s/%d/fd", ind_root("NUXEL_PROC", "/proc"), (int)pid);
  DIR *d = opendir(fdpath);
  if (!d) return 0;
  int held = 0;
  struct dirent *de;
  while ((de = readdir(d))) {
    if (!strcmp(de->d_name, ".") || !strcmp(de->d_name, "..")) continue;
    char linkpath[512], target[512];
    snprintf(linkpath, sizeof linkpath, "%s/%s", fdpath, de->d_name);
    ssize_t n = readlink(linkpath, target, sizeof target - 1);
    if (n <= 0) continue;
    target[n] = 0;
    const char *base = strrchr(target, '/');
    if ((base && !strcmp(base + 1, ttybase)) || !strcmp(target, ttybase)) { held = 1; break; }
  }
  closedir(d);
  return held;
}

/* Read one "key=value" field from nuxel-console's atomic session lease.  The
   lease is a multi-line file (pid, tty, state, start_ticks), so the single-line
   reader above is not enough: reading only line 1 would silently ignore the
   generation/state that makes the lease trustworthy. */
static int ind_lease_field(const char *key, char *out, size_t outn) {
  char path[420], text[512];
  size_t n = 0;
  out[0] = 0;
  snprintf(path, sizeof path, "%s/nuxel/live-console-session",
           ind_root("NUXEL_RUN", "/run"));
  FILE *f = fopen(path, "rb");
  if (!f) return 0;
  n = fread(text, 1, sizeof text - 1, f);
  fclose(f);
  text[n] = 0;
  size_t klen = strlen(key);
  for (char *p = text; *p; ) {
    while (*p == ' ' || *p == '\t' || *p == '\n' || *p == '\r') p++;
    if (!*p) break;
    char *end = p;
    while (*end && *end != ' ' && *end != '\t' && *end != '\n' && *end != '\r') end++;
    char saved = *end;
    *end = 0;
    if (!strncmp(p, key, klen) && p[klen] == '=') {
      snprintf(out, outn, "%s", p + klen + 1);
      *end = saved;
      return out[0] != 0;
    }
    *end = saved;
    p = end;
  }
  return 0;
}

/* /proc/<pid>/stat field 22, parsed without trusting comm spacing.  The lease
   carries this value so a recycled PID cannot reactivate an old session. */
static long ind_proc_start_ticks(pid_t pid) {
  char path[512], text[1024];
  snprintf(path, sizeof path, "%s/%d/stat", ind_root("NUXEL_PROC", "/proc"), (int)pid);
  FILE *f = fopen(path, "rb");
  if (!f) return -1;
  size_t n = fread(text, 1, sizeof text - 1, f);
  fclose(f);
  text[n] = 0;
  char *end = strrchr(text, ')');
  if (!end) return -1;
  char *save = NULL;
  int field = 3;
  for (char *tok = strtok_r(end + 1, " \t\n\r", &save); tok;
       tok = strtok_r(NULL, " \t\n\r", &save), field++) {
    if (field == 22) return strtol(tok, NULL, 10);
  }
  return -1;
}

static int ind_pid_alive(pid_t pid) {
  char path[512];
  snprintf(path, sizeof path, "%s/%d", ind_root("NUXEL_PROC", "/proc"), (int)pid);
  return ind_path_exists(path);
}

static int ind_lease_valid(pid_t *lease_out) {
  char buf[128];
  long pid = 0, start = 0;
  if (lease_out) *lease_out = 0;
  if (!ind_lease_field("pid", buf, sizeof buf)) return 0;
  pid = strtol(buf, NULL, 10);
  if (pid <= 0 || pid > 0x7fffffffL) return 0;
  if (ind_lease_field("state", buf, sizeof buf) &&
      !ind_eq_ci(buf, "serving") && !ind_eq_ci(buf, "active")) return 0;
  if (!ind_pid_alive((pid_t)pid)) return 0;
  if (!ind_cmdline_has((pid_t)pid, "nuxel-console")) return 0;
  if (ind_lease_field("start_ticks", buf, sizeof buf)) {
    start = strtol(buf, NULL, 10);
    if (start > 0 && ind_proc_start_ticks((pid_t)pid) != start) return 0;
  }
  if (lease_out) *lease_out = (pid_t)pid;
  return 1;
}

static int ind_live_console(void) {
  const char *ttybase = "ttyGS0";
  char ttypath[420];
  snprintf(ttypath, sizeof ttypath, "%s/ttyGS0", ind_root("NUXEL_SYS_TTY", "/sys/class/tty"));
  /* A live USB console cannot outlive the USB data link (A71).  Checking this
     first is what clears the icon promptly after a cable pull even while the
     daemon and its tty fd survive. */
  if (!ind_pc_connected()) return 0;
  if (!ind_path_exists(ttypath)) return 0;

  DIR *d = opendir(ind_root("NUXEL_PROC", "/proc"));
  if (d) {
    struct dirent *de;
    while ((de = readdir(d))) {
      if (de->d_name[0] < '0' || de->d_name[0] > '9') continue;
      pid_t pid = (pid_t)atoi(de->d_name);
      if (pid <= 0 || !ind_cmdline_has(pid, "nuxel-console")) continue;
      if (ind_pid_holds_tty(pid, ttybase)) { closedir(d); return 1; }
    }
    closedir(d);
  }
  /* A lease is not self-authenticating: it must name a live nuxel-console
     process, carry a serving/active state, and match the process generation. */
  return ind_lease_valid(NULL);
}

static void indicators_json(char *out, size_t outn) {
  int external_power = 0, charging = 0;
  ind_power(&external_power, &charging);
  int pc = ind_pc_connected();
  int live = ind_live_console();
  int level = -1;
  char levelbuf[32] = "";
  /* Level is informational only; the icon is driven by the two booleans. */
  const char *psroot = ind_root("NUXEL_SYS_POWER_SUPPLY", "/sys/class/power_supply");
  DIR *ps = opendir(psroot);
  if (ps) {
    struct dirent *de;
    while ((de = readdir(ps))) {
      if (!strcmp(de->d_name, ".") || !strcmp(de->d_name, "..")) continue;
      char typepath[420], type[64] = "unknown", cappath[420];
      snprintf(typepath, sizeof typepath, "%s/%s/type", psroot, de->d_name);
      ind_read_line(typepath, type, sizeof type);
      if (!ind_eq_ci(type, "Battery")) continue;
      snprintf(cappath, sizeof cappath, "%s/%s/capacity", psroot, de->d_name);
      if (ind_read_line(cappath, levelbuf, sizeof levelbuf)) level = atoi(levelbuf);
      break;
    }
    closedir(ps);
  }
  snprintf(out, outn,
    "{\"charging\":{\"external_power\":%d,\"charging\":%d,\"battery_level\":%d,\"source\":\"sysfs\"},"
    "\"usb_data\":{\"pc_connected\":%d,\"source\":\"sysfs:udc\"},"
    "\"live_console\":{\"active\":%d,\"source\":\"proc:nuxel-console:tty\"}}",
    external_power, charging, level, pc, live);
}

/* Event-driven refresh: the kernel's kobject uevent stream tells us the exact
   moment a power supply, UDC, Type-C port or tty changes.  Pushing one small JS
   event is cheaper than polling /proc and /sys, and makes plug/unplug visible
   while the lockscreen is on screen.  A failed socket is non-fatal: the UI's
   bounded safety read remains the fallback. */
static guint ind_uevent_timeout;
static guint ind_uevent_source;

static gboolean ind_push_event(gpointer data) {
  (void)data;
  ind_uevent_timeout = 0;
  if (!g_main_view) return FALSE;
  webkit_web_view_evaluate_javascript(g_main_view,
      "window.__nuxelHostEvent && window.__nuxelHostEvent('system-indicators', {});",
      -1, NULL, NULL, NULL, NULL, NULL);
  return FALSE;
}

static gboolean ind_uevent_in(GIOChannel *ch, GIOCondition cond, gpointer data) {
  (void)data;
  if (cond & (G_IO_HUP | G_IO_ERR)) return TRUE;
  char buf[4096];
  gsize got = 0;
  GError *err = NULL;
  if (g_io_channel_read_chars(ch, buf, sizeof buf - 1, &got, &err) != G_IO_STATUS_NORMAL) {
    if (err) g_error_free(err);
    return TRUE;
  }
  buf[got] = 0;
  if (strstr(buf, "power_supply") || strstr(buf, "usb") || strstr(buf, "udc") ||
      strstr(buf, "typec") || strstr(buf, "ttyGS0") || strstr(buf, "dwc3")) {
    if (!ind_uevent_timeout) ind_uevent_timeout = (guint)g_timeout_add(120, ind_push_event, NULL);
  }
  return TRUE;
}

/* Fallback for kernels where a non-root session cannot bind the kobject
   uevent socket (NETLINK_KOBJECT_UEVENT normally requires CAP_NET_ADMIN).  This
   is signature-based: it re-reads the cheap sysfs/proc state once a second while
   the lockscreen is visible, but pushes JS ONLY when something changed.  It is
   therefore still event-driven at the UI boundary and costs no wakeups on an
   unchanged system.  The JS layer's 15 s safety read covers bridge/host outages. */
static char ind_last_signature[256];
static guint ind_fallback_timer;

static void ind_signature(char *out, size_t outn) {
  int power = 0, charging = 0, pc = 0, live = 0;
  ind_power(&power, &charging);
  pc = ind_pc_connected();
  live = ind_live_console();
  snprintf(out, outn, "p%d c%d pc%d l%d", power, charging, pc, live);
}

static gboolean ind_signature_tick(gpointer data) {
  (void)data;
  if (!g_main_view) return TRUE;
  char now[256];
  ind_signature(now, sizeof now);
  if (strcmp(now, ind_last_signature) != 0) {
    snprintf(ind_last_signature, sizeof ind_last_signature, "%s", now);
    webkit_web_view_evaluate_javascript(g_main_view,
        "window.__nuxelHostEvent && window.__nuxelHostEvent('system-indicators', {});",
        -1, NULL, NULL, NULL, NULL, NULL);
  }
  return TRUE;
}

static void uevent_open(void) {
#ifdef __linux__
  int fd = socket(AF_NETLINK, SOCK_DGRAM | SOCK_CLOEXEC | SOCK_NONBLOCK,
                  NETLINK_KOBJECT_UEVENT);
  if (fd < 0) { st("HOST_UEVENT_OPEN_FAIL errno=%d (safety read remains)", errno); return; }
  struct sockaddr_nl addr;
  memset(&addr, 0, sizeof addr);
  addr.nl_family = AF_NETLINK;
  addr.nl_groups = 1;                 /* kernel broadcast group */
  if (bind(fd, (struct sockaddr *)&addr, sizeof addr) != 0) {
    st("HOST_UEVENT_BIND_FAIL errno=%d (safety read remains)", errno);
    close(fd);
    return;
  }
  GIOChannel *ch = g_io_channel_unix_new(fd);
  g_io_channel_set_encoding(ch, NULL, NULL);
  ind_uevent_source = g_io_add_watch(ch, G_IO_IN | G_IO_HUP | G_IO_ERR, ind_uevent_in, NULL);
  st("HOST_UEVENT_READY events=power_supply,usb,udc,typec,tty");
#else
  st("HOST_UEVENT_SKIPPED platform=non-linux");
#endif
}

static void indicator_fallback_start(void) {
  ind_signature(ind_last_signature, sizeof ind_last_signature);
  ind_fallback_timer = (guint)g_timeout_add(250, ind_signature_tick, NULL);
  st("HOST_INDICATOR_FALLBACK interval=250ms push-on-change=1");
}

struct cfgfile { const char *name; const char *path; int writable; };
static const struct cfgfile CFG[] = {
  { "statusbar-safezones", "/etc/nuxel/display/statusbar-safezones.json", 1 },
  { "buttons",             "/etc/nuxel/input/buttons.json",               1 },
  { "display",             "/etc/nuxel/display/display.json",             1 },
  /* A33 boot surface: the ONE writable boot document (verbose boot, briq-02b)
     plus the read-only handoff evidence the boot-log overlay renders. */
  { "verbose-boot",        "/etc/nuxel/boot/verbose-boot.json",           1 },
  { "animation-handoff",   "/etc/nuxel/boot/animation-handoff.json",      0 },
  { "verbose-boot-state",  "/run/nuxel/verbose-boot",                     0 },
  { "fb-owner",            "/var/lib/nuxel/fb-owner",                     0 },
  { "anim-handoff",        "/run/nuxel-anim-handoff",                     0 },
  { "boot-stage-log",      "/var/log/nuxel/boot-stage.log",               0 },
  { "wlfb-state",          "/run/nuxel-wl-fb.state",                      0 },
  { "launcher-state",      "/run/nuxel-home.state",                        0 },
  { "anim-state",          "/var/lib/nuxel/animation",                     0 },
  { "display-state",       "/var/lib/nuxel/display",                       0 },
  { "touch-arm-state",     "/run/nuxel-touch-arm.state",                   0 },
  /* REVISION A33c (bg-06-core-phone-apps, briq-06d): the Nuxel Settings app's
     Input group switches the on-screen keyboard through the document
     /etc/nuxel/keyboard/keyboard.json, and it must be able to SHOW what the
     applier actually managed to apply. /run/nuxel-keyboard.state is written by
     tools/s10plus/a33/nuxel-keyboard-apply.sh (the single consumer of that
     document) and is read-only here - no new verb, no new write path, no change
     to the terminal, the buttons or the boot surface. */
  { "keyboard-state",      "/run/nuxel-keyboard.state",                    0 },
  { "lock-state",          "/run/nuxel-lock.state",                        0 },
  { "navdock-state",       "/run/nuxel-navdock.state",                     0 },
  /* Real S10+ battery nodes (the gauge is named `battery`, not BAT*). */
  { "battery-capacity",    "/sys/class/power_supply/battery/capacity",     0 },
  { "battery-status",      "/sys/class/power_supply/battery/status",       0 },
  /* A45 Display & Lockscreen: the Home Settings timeout selector writes this
     document, which nuxel-button-manager (the single idle owner) reads live. */
  { "display-timeout",     "/etc/nuxel/display/screen-timeout.json",      1 },
  /* A68 lockhead indicators: computed in-process from sysfs, not a file read. */
  { "system-indicators",   NULL,                                           0 },
  { NULL, NULL, 0 }
};

static const char *cfg_lookup(const char *name, int *writable) {
  if (!strcmp(name, "system-indicators")) {
    if (writable) *writable = 0;
    return "computed:system-indicators";
  }
  for (int i = 0; CFG[i].name; i++)
    if (!strcmp(CFG[i].name, name)) { if (writable) *writable = CFG[i].writable; return CFG[i].path; }
  return NULL;
}

/* --- terminal ------------------------------------------------------------- */
static pid_t term_pid = -1;
static int term_fd = -1;
static GtkWidget *term_window;
static WebKitWebView *term_view;
static GIOChannel *term_chan;
static guint term_watch;
static int term_bytes;

/* Retire every PTY event source before another window can create a session.
 * Otherwise an old HUP callback reads the NEW global pid/fd and kills it. */
static void term_request_close(void) {
  if (term_watch) { g_source_remove(term_watch); term_watch = 0; }
  if (term_chan) { g_io_channel_unref(term_chan); term_chan = NULL; }
  if (term_fd >= 0) { close(term_fd); term_fd = -1; }
  if (term_pid > 0) { kill(term_pid, SIGHUP); term_pid = -1; }
}

static void term_child_exited(GPid pid, gint status, gpointer data) {
  (void)status; (void)data;
  /* GLib has reaped this child; never alter a subsequently opened session. */
  if (term_pid == pid) term_pid = -1;
  g_spawn_close_pid(pid);
}

static void term_push(const char *jsfun, const char *payload) {
  if (!term_view) return;
  GString *g = g_string_new("");
  g_string_append_printf(g, "window.nuxelTerm && window.nuxelTerm.%s(%s);", jsfun, payload);
  webkit_web_view_evaluate_javascript(term_view, g->str, -1, NULL, NULL, NULL, NULL, NULL);
  g_string_free(g, TRUE);
}

static char *json_escape(const char *s, size_t n) {
  GString *g = g_string_new("\"");
  for (size_t i = 0; i < n; i++) {
    unsigned char c = (unsigned char)s[i];
    switch (c) {
      case '"':  g_string_append(g, "\\\""); break;
      case '\\': g_string_append(g, "\\\\"); break;
      case '\n': g_string_append(g, "\\n");  break;
      case '\r': g_string_append(g, "\\r");  break;
      case '\t': g_string_append(g, "\\t");  break;
      default:
        if (c < 0x20) g_string_append_printf(g, "\\u%04x", c);
        else g_string_append_c(g, (char)c);
    }
  }
  g_string_append_c(g, '"');
  return g_string_free(g, FALSE);
}

static gboolean term_in(GIOChannel *ch, GIOCondition cond, gpointer d) {
  (void)ch; (void)d;
  char buf[4096];
  if (cond & (G_IO_HUP | G_IO_ERR)) {
    term_push("exit", "0");
    term_watch = 0; /* returning FALSE removes the currently dispatched watch */
    term_request_close();
    st("TERMINAL_EXIT bytes=%d", term_bytes);
    return FALSE;
  }
  ssize_t n = read(term_fd, buf, sizeof buf);
  if (n <= 0) return TRUE;
  term_bytes += (int)n;
  char *esc = json_escape(buf, (size_t)n);
  term_push("output", esc);
  g_free(esc);
  return TRUE;
}

static void term_spawn(void) {
  int master = -1;
  pid_t pid = forkpty(&master, NULL, NULL, NULL);
  if (pid < 0) { st("TERMINAL_FORKPTY_FAIL errno=%d", errno); return; }
  if (pid == 0) {
    setenv("TERM", "xterm-256color", 1);
    setenv("HOME", "/root", 1);
    setenv("PATH", "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin", 1);
    setenv("PS1", "\\[\\e[1;34m\\]nuxel\\[\\e[0m\\]:\\w# ", 1);
    execl("/bin/sh", "sh", "-i", (char *)NULL);
    _exit(127);
  }
  term_pid = pid;
  g_child_watch_add(pid, term_child_exited, NULL);
  term_fd = master;
  term_bytes = 0;
  fcntl(term_fd, F_SETFL, O_NONBLOCK);
  term_chan = g_io_channel_unix_new(term_fd);
  g_io_channel_set_encoding(term_chan, NULL, NULL);
  term_watch = g_io_add_watch(term_chan, G_IO_IN | G_IO_HUP | G_IO_ERR, term_in, NULL);
  st("TERMINAL_STARTED pid=%d fd=%d", (int)pid, term_fd);
}

/* Close the native terminal SURFACE, not just its PTY.
 *
 * Measured A34 owner test: tapping the terminal's Close button produced a
 * `click` on #close, but the window stayed on the glass because term.close
 * only killed the shell.  The fullscreen terminal then covered Home for the
 * rest of the session, so every later touch ("Settings", the status-bar pull,
 * the power menu) looked like it did nothing.  A close is only complete when
 * the window is gone. */
static void term_close_window(void) {
  term_request_close();
  if (term_window) {
    GtkWidget *w = term_window;
    term_window = NULL;          /* one-instance guard stops re-entrancy */
    term_view = NULL;
    gtk_widget_destroy(w);
  }
}

/* --- host API ------------------------------------------------------------- */

static void host_reply(WebKitWebView *v, const char *id, int ok, const char *payload_json) {
  if (!v) return;
  GString *g = g_string_new("");
  g_string_append_printf(g, "window.__nuxelHostReply && window.__nuxelHostReply(%s,%d,%s);",
                         id && *id ? id : "null", ok, payload_json ? payload_json : "null");
  webkit_web_view_evaluate_javascript(v, g->str, -1, NULL, NULL, NULL, NULL, NULL);
  g_string_free(g, TRUE);
}

/* minimal, deliberately strict JSON reader: only ever used to fetch a top-level
   string/number/bool value out of a request the page sent */
static int json_str(const char *js, const char *key, char *out, size_t outn) {
  char pat[64];
  snprintf(pat, sizeof pat, "\"%s\"", key);
  const char *p = strstr(js, pat);
  if (!p) return 0;
  p += strlen(pat);
  while (*p == ' ' || *p == ':' || *p == '\t') p++;
  if (*p != '"') return 0;
  p++;
  size_t i = 0;
  while (*p && *p != '"' && i + 1 < outn) {
    if (*p == '\\' && p[1]) {
      p++;
      switch (*p) { case 'n': out[i++] = '\n'; break; case 't': out[i++] = '\t'; break;
                    default: out[i++] = *p; }
    } else out[i++] = *p;
    p++;
  }
  out[i] = 0;
  return 1;
}

static void action_perform(const char *action, char *result, size_t rn) {
  if (!strcmp(action, "screen-off") || !strcmp(action, "screen-on") || !strcmp(action, "screen-toggle")) {
    int fd = open("/run/nuxel-wl-fb.cmd", O_WRONLY | O_NONBLOCK);
    if (fd < 0) { snprintf(result, rn, "{\"ok\":false,\"error\":\"bridge-fifo-absent\"}"); return; }
    dprintf(fd, "%s\n", action);
    close(fd);
    st("HOST_ACTION %s -> nuxel-wl-fb control fifo", action);
    snprintf(result, rn, "{\"ok\":true,\"action\":\"%s\"}", action);
    return;
  }
  if (!strcmp(action, "volume-up") || !strcmp(action, "volume-down") || !strcmp(action, "volume-mute")) {
    int fd = open("/run/nuxel-buttons.cmd", O_WRONLY | O_NONBLOCK);
    if (fd < 0) { snprintf(result, rn, "{\"ok\":false,\"error\":\"button-fifo-absent\"}"); return; }
    if (!strcmp(action, "volume-up"))   dprintf(fd, "volume-up\n");
    if (!strcmp(action, "volume-down")) dprintf(fd, "volume-down\n");
    if (!strcmp(action, "volume-mute")) dprintf(fd, "volume-mute\n");
    close(fd);
    st("HOST_ACTION %s -> button manager fifo", action);
    snprintf(result, rn, "{\"ok\":true,\"action\":\"%s\"}", action);
    return;
  }
  /* On-screen navigation asks for feedback at pointer-down, before the page
   * changes state.  Keep the accepted vocabulary deliberately closed: a web
   * page can request only a named short pattern, never a raw actuator value. */
  if (!strcmp(action, "haptics-tap") || !strcmp(action, "haptics-navigation") ||
      !strcmp(action, "haptics-switch") || !strcmp(action, "haptics-long")) {
    const char *pattern = !strcmp(action, "haptics-navigation") ? "navigation" :
                          (!strcmp(action, "haptics-long") ? "long" :
                           (!strcmp(action, "haptics-switch") ? "switch" : "tap"));
    int fd = open("/run/nuxel-haptics/haptics.cmd", O_WRONLY | O_NONBLOCK);
    if (fd < 0) { snprintf(result, rn, "{\"ok\":false,\"error\":\"haptics-fifo-absent\"}"); return; }
    dprintf(fd, "%s\n", pattern);
    close(fd);
    st("HOST_ACTION %s -> haptics fifo", action);
    snprintf(result, rn, "{\"ok\":true,\"action\":\"%s\"}", action);
    return;
  }
  /* A34 TOUCHDOWN: the on-screen power menu uses the SAME control FIFO as the
   * hardware keys, so tapping Cancel/Restart and pressing them are one path.
   * Only the menu's own verbs are accepted (no arbitrary FIFO injection). */
  if (!strncmp(action, "menu-", 5)) {
    int valid = !strcmp(action, "menu-up") || !strcmp(action, "menu-down") ||
                !strcmp(action, "menu-close") || !strcmp(action, "menu-open") ||
                !strcmp(action, "menu-select");
    if (!valid && !strncmp(action, "menu-select ", 12)) {
      const char *p = action + 12;
      valid = *p != 0;
      for (; *p; p++) if (*p < '0' || *p > '9') { valid = 0; break; }
    }
    if (valid) {
      int fd = open("/run/nuxel-buttons.cmd", O_WRONLY | O_NONBLOCK);
      if (fd < 0) { snprintf(result, rn, "{\"ok\":false,\"error\":\"button-fifo-absent\"}"); return; }
      dprintf(fd, "%s\n", action);
      close(fd);
      st("HOST_ACTION %s -> button manager fifo", action);
      snprintf(result, rn, "{\"ok\":true,\"action\":\"%s\"}", action);
      return;
    }
    snprintf(result, rn, "{\"ok\":false,\"error\":\"bad-menu-action\"}");
    return;
  }
  if (!strcmp(action, "close-terminal")) {
    term_close_window();
    snprintf(result, rn, "{\"ok\":true,\"action\":\"close-terminal\"}");
    return;
  }
  if (!strcmp(action, "open-terminal")) {
    term_open_window();
    snprintf(result, rn, "{\"ok\":true,\"action\":\"open-terminal\"}");
    return;
  }
  if (!strcmp(action, "nav-hide") || !strcmp(action, "nav-show")) {
    int nf = open("/run/nuxel-navdock.cmd", O_WRONLY | O_NONBLOCK);
    if (nf < 0) { snprintf(result, rn, "{\"ok\":false,\"error\":\"navdock-fifo-absent\"}"); return; }
    dprintf(nf, "%s\n", !strcmp(action, "nav-show") ? "show" : "hide");
    close(nf);
    st("HOST_ACTION %s -> navdock fifo", action);
    snprintf(result, rn, "{\"ok\":true,\"action\":\"%s\"}", action);
    return;
  }
  if (!strcmp(action, "home") || !strcmp(action, "back") || !strcmp(action, "back-long") || !strcmp(action, "forward") ||
      !strcmp(action, "stop") || !strcmp(action, "reload-launcher") ||
      !strcmp(action, "search") || !strcmp(action, "settings") ||
      !strcmp(action, "recents") || !strcmp(action, "lock") || !strcmp(action, "unlock")) {
    /* A native terminal window is a separate top-level surface: the launcher's
     * DOM `home` event cannot dismiss it.  Home/back must close it here, or the
     * fullscreen terminal stays in front of Home (the A34 owner-test symptom). */
    if (!strcmp(action, "home")) term_close_window();
    if (g_main_view) {
      GString *g = g_string_new("");
      const char *js_action = !strcmp(action, "home") ? "'home'" :
                              !strcmp(action, "back") ? "'back'" :
                              !strcmp(action, "back-long") ? "'back-long'" :
                              !strcmp(action, "forward") ? "'forward'" :
                              !strcmp(action, "stop") ? "'stop'" :
                              !strcmp(action, "reload-launcher") ? "'reload-launcher'" :
                              !strcmp(action, "search") ? "'search'" :
                              !strcmp(action, "settings") ? "'settings'" :
                              !strcmp(action, "recents") ? "'recents'" :
                              !strcmp(action, "lock") ? "'lock'" : "'unlock'";
      g_string_append_printf(g,
        "window.dispatchEvent(new CustomEvent('nuxel:action',{detail:{action:%s}}));", js_action);
      webkit_web_view_evaluate_javascript(g_main_view, g->str, -1, NULL, NULL, NULL, NULL, NULL);
      g_string_free(g, TRUE);
    }
    /* The native nav dock is an overlay layer-shell surface that would otherwise
       paint over the lockscreen; hide it while locked and restore it on unlock. */
    if (!strcmp(action, "lock")) {
      int nf = open("/run/nuxel-navdock.cmd", O_WRONLY | O_NONBLOCK);
      if (nf >= 0) { dprintf(nf, "hide\n"); close(nf); }
    } else if (!strcmp(action, "unlock")) {
      int nf = open("/run/nuxel-navdock.cmd", O_WRONLY | O_NONBLOCK);
      if (nf >= 0) { dprintf(nf, "show\n"); close(nf); }
    }
    st("HOST_ACTION %s -> launcher page", action);
    snprintf(result, rn, "{\"ok\":true,\"action\":\"%s\"}", action);
    return;
  }
  st("HOST_ACTION_REFUSED %s", action);
  snprintf(result, rn, "{\"ok\":false,\"error\":\"unknown-action\"}");
}

static void on_host_message(WebKitUserContentManager *m, WebKitJavascriptResult *r, gpointer d) {
  (void)m;
  WebKitWebView *v = WEBKIT_WEB_VIEW(d);
  JSCValue *jv = webkit_javascript_result_get_js_value(r);
  char *js = jv ? jsc_value_to_string(jv) : NULL;
  if (!js) return;
  char id[64] = "", method[64] = "", name[128] = "", action[64] = "", text[16384] = "";
  json_str(js, "id", id, sizeof id);
  json_str(js, "method", method, sizeof method);
  json_str(js, "name", name, sizeof name);
  json_str(js, "action", action, sizeof action);

  if (!strcmp(method, "config.get") || !strcmp(method, "status.read")) {
    int wr = 0;
    const char *path = cfg_lookup(name, &wr);
    if (!path) { host_reply(v, id, 0, "{\"error\":\"unknown-config\"}"); st("HOST_CONFIG_REFUSED name=%s", name); g_free(js); return; }
    /* A68: the lockhead indicators are a live sysfs computation, not a file. */
    if (!strcmp(name, "system-indicators")) {
      char ind[1024];
      indicators_json(ind, sizeof ind);
      char *esc = json_escape(ind, strlen(ind));
      GString *io = g_string_new("{\"ok\":true,\"text\":");
      g_string_append(io, esc);
      g_string_append_printf(io, ",\"name\":\"%s\"}", name);
      host_reply(v, id, 1, io->str);
      g_string_free(io, TRUE);
      g_free(esc);
      st("HOST_STATUS_INDICATORS ok");
      g_free(js);
      return;
    }
    FILE *f = fopen(path, "rb");
    if (!f) { host_reply(v, id, 0, "{\"error\":\"unreadable\"}"); g_free(js); return; }
    size_t cap = 1 << 16, n = 0;
    char *buf = g_malloc(cap);
    n = fread(buf, 1, cap - 1, f);
    buf[n] = 0;
    fclose(f);
    char *esc = json_escape(buf, n);
    GString *out = g_string_new("{\"ok\":true,\"text\":");
    g_string_append(out, esc);
    g_string_append_printf(out, ",\"name\":\"%s\"}", name);
    host_reply(v, id, 1, out->str);
    g_string_free(out, TRUE);
    g_free(esc); g_free(buf);
    st("HOST_CONFIG_GET name=%s bytes=%zu", name, n);
    g_free(js);
    return;
  }
  if (!strcmp(method, "config.set")) {
    int wr = 0;
    const char *path = cfg_lookup(name, &wr);
    if (!path || !wr) { host_reply(v, id, 0, "{\"error\":\"read-only-or-unknown\"}"); st("HOST_CONFIG_SET_REFUSED name=%s", name); g_free(js); return; }
    /* the payload must be a JSON object; the native side validates the shape, the
       Nuxel Settings app owns the schema */
    const char *txt = strstr(js, "\"text\"");
    if (!txt || !json_str(js, "text", text, sizeof text)) {
      host_reply(v, id, 0, "{\"error\":\"missing-text\"}"); g_free(js); return;
    }
    const char *p = text;
    while (*p == ' ' || *p == '\n') p++;
    if (*p != '{') { host_reply(v, id, 0, "{\"error\":\"not-an-object\"}"); g_free(js); return; }
    char tmp[512];
    snprintf(tmp, sizeof tmp, "%s.new", path);
    FILE *f = fopen(tmp, "wb");
    if (!f) { host_reply(v, id, 0, "{\"error\":\"write-failed\"}"); g_free(js); return; }
    fwrite(text, 1, strlen(text), f);
    fputc('\n', f);
    fclose(f);
    if (rename(tmp, path) != 0) { host_reply(v, id, 0, "{\"error\":\"rename-failed\"}"); g_free(js); return; }
    host_reply(v, id, 1, "{\"ok\":true}");
    st("HOST_CONFIG_SET name=%s bytes=%zu", name, strlen(text));
    g_free(js);
    return;
  }
  if (!strcmp(method, "system.action")) {
    char result[256];
    /* Home destroys the sending terminal WebView. Reply before that happens. */
    if ((!strcmp(action, "home") || !strcmp(action, "close-terminal")) && v == term_view) {
      host_reply(v, id, 1, "{\"ok\":true}");
      action_perform(action, result, sizeof result);
      g_free(js);
      return;
    }
    action_perform(action, result, sizeof result);
    host_reply(v, id, result[0] ? 1 : 0, result);
    g_free(js);
    return;
  }
  if (!strcmp(method, "term.input")) {
    if (term_fd >= 0 && json_str(js, "data", text, sizeof text)) {
      if (write(term_fd, text, strlen(text)) < 0) { /* best effort */ }
      host_reply(v, id, 1, "{\"ok\":true}");
    } else host_reply(v, id, 0, "{\"error\":\"no-terminal\"}");
    g_free(js);
    return;
  }
  if (!strcmp(method, "term.open")) { term_open_window(); host_reply(v, id, 1, "{\"ok\":true}"); g_free(js); return; }
  if (!strcmp(method, "term.close")) { host_reply(v, id, 1, "{\"ok\":true}"); term_close_window(); g_free(js); return; }
  st("HOST_METHOD_REFUSED %s", method);
  host_reply(v, id, 0, "{\"error\":\"unknown-method\"}");
  g_free(js);
}

static void host_api_attach(WebKitUserContentManager *ucm, WebKitWebView *v) {
  webkit_user_content_manager_register_script_message_handler(ucm, "nuxelHost");
  g_signal_connect(ucm, "script-message-received::nuxelHost", G_CALLBACK(on_host_message), v);
}

/* --- terminal window ------------------------------------------------------ */

static void term_win_destroyed(GtkWidget *w, gpointer d) {
  (void)w; (void)d;
  term_request_close();
  if (term_chan) { g_io_channel_unref(term_chan); term_chan = NULL; }
  term_window = NULL; term_view = NULL;
  st("TERMINAL_WINDOW_CLOSED");
}

static void term_open_window(void) {
  if (term_window) {              /* one instance only (mission 13) */
    gtk_window_present(GTK_WINDOW(term_window));
    st("TERMINAL_FOCUS_EXISTING pid=%d", (int)term_pid);
    return;
  }
  const char *url = getenv("NUXEL_TERMINAL_URL");
  if (!url || !*url) url = "http://127.0.0.1:8000/pwa/nuxel-apps/terminal/index.html";
  term_window = gtk_window_new(GTK_WINDOW_TOPLEVEL);
  gtk_window_set_title(GTK_WINDOW(term_window), "Nuxel Terminal");
  gtk_window_set_decorated(GTK_WINDOW(term_window), FALSE);
  gtk_widget_set_size_request(term_window, 360, 760);
  term_view = view_new();
  gtk_container_add(GTK_CONTAINER(term_window), GTK_WIDGET(term_view));
  g_signal_connect(term_window, "destroy", G_CALLBACK(term_win_destroyed), NULL);
  gtk_widget_show_all(term_window);
  gtk_window_fullscreen(GTK_WINDOW(term_window));
  webkit_web_view_load_uri(term_view, url);
  if (term_pid <= 0) term_spawn();
  st("TERMINAL_WINDOW_OPEN url=%s pid=%d", url, (int)term_pid);
}

/* Resolve a registry id in the running launcher page.  The id is validated
   (registry-id charset only) so a control-FIFO writer can never inject script. */
static void launcher_launch(const char *app_id) {
  if (!g_main_view || !app_id || !*app_id) return;
  for (const char *p = app_id; *p; p++)
    if (!(isalnum((unsigned char)*p) || *p == '.' || *p == '_' || *p == '-')) {
      st("LAUNCH_REFUSED id=%s (invalid charset)", app_id);
      return;
    }
  GString *g = g_string_new("");
  g_string_append_printf(g, "window.appRegistry && window.appRegistry.launchApp(%s);", 
                         g_strdup_printf("'%s'", app_id));
  webkit_web_view_evaluate_javascript(g_main_view, g->str, -1, NULL, NULL, NULL, NULL, NULL);
  g_string_free(g, TRUE);
  st("LAUNCH app_id=%s via launcher registry", app_id);
}

/* A32 — stale-frontend invalidation, on the device that must never show one.
 *
 * Measured this cycle on the handset: after replacing index.html/js/*.js the
 * launcher still rendered the OLD code.  The reason was not the deployment (the
 * files on disk had the new hashes) but the page's own persisted state: the
 * launcher's service worker kept serving ./js/*.js from its cache namespace, and
 * the asset requests never reached the local static server at all (verified in
 * /run/nuxel-web.log: only index.html and sw.js were requested).
 *
 * The VM/desktop path wants that offline cache; the phone does not need it,
 * because the launcher's server is 127.0.0.1 and always up.  So the phone host
 * clears the launcher's website data (service-worker registrations + memory and
 * disk HTTP caches) once at startup, and derives a version stamp from the served
 * index.html so the first navigation can never be a cached document either.
 * NUXEL_KEEP_CACHE=1 opts out (used when measuring cache behaviour itself).
 */
static int rm_rf(const char *path) {
  struct stat sb;
  if (lstat(path, &sb) != 0) return 0;
  if (S_ISDIR(sb.st_mode)) {
    DIR *d = opendir(path);
    if (d) {
      struct dirent *de;
      while ((de = readdir(d))) {
        if (!strcmp(de->d_name, ".") || !strcmp(de->d_name, "..")) continue;
        char child[768];
        snprintf(child, sizeof child, "%s/%s", path, de->d_name);
        rm_rf(child);
      }
      closedir(d);
    }
  }
  return (remove(path) == 0) ? 1 : 0;
}

static void purge_path(const char *path, const char *why) {
  int existed = (access(path, F_OK) == 0);
  if (!existed) { st("CACHE_PURGE absent %s", path); return; }
  rm_rf(path);
  st("CACHE_PURGE removed %s (%s) still_present=%d", path, why, access(path, F_OK) == 0);
}

static void purge_launcher_cache(void) {
  const char *keep = getenv("NUXEL_KEEP_CACHE");
  if (keep && keep[0] == '1') { st("CACHE_PURGE skipped (NUXEL_KEEP_CACHE=1)"); return; }
  /* webkitgtk names its per-application data after the GApplication id, which for
     this host is "nuxel-pwa-host" (measured on the handset):
        <datadir>/nuxel-pwa-host/serviceworkers     -> stale service-worker scripts
        <cachedir>/nuxel-pwa-host/CacheStorage      -> the SW cache namespaces
        <cachedir>/nuxel-pwa-host/WebKitCache       -> the HTTP cache
     Only those three subtrees are removed: localStorage (the launcher's own
     settings fallback when no host is present) is deliberately left alone. */
  const char *home = getenv("HOME") ? getenv("HOME") : "/root";
  char base[512], p1[640], p2[640], p3[640];
  snprintf(base, sizeof base, "%s/.local/share/nuxel-pwa-host", home);
  snprintf(p1, sizeof p1, "%s/serviceworkers", base);
  snprintf(p2, sizeof p2, "%s/.cache/nuxel-pwa-host/CacheStorage", home);
  snprintf(p3, sizeof p3, "%s/.cache/nuxel-pwa-host/WebKitCache", home);
  purge_path(p1, "stale service worker scripts");
  purge_path(p2, "stale service worker cache namespaces");
  purge_path(p3, "stale HTTP cache");
}

/* --- control FIFO: the hardware-button manager's entry point -------------- */
static GIOChannel *ctl_chan;

static gboolean ctl_in(GIOChannel *ch, GIOCondition cond, gpointer d) {
  (void)d;
  if (cond & (G_IO_HUP | G_IO_ERR)) return TRUE;
  char buf[1024];
  gsize got = 0;
  GError *err = NULL;
  if (g_io_channel_read_chars(ch, buf, sizeof buf - 1, &got, &err) != G_IO_STATUS_NORMAL) {
    if (err) g_error_free(err);
    return TRUE;
  }
  buf[got] = 0;
  for (char *q = buf; q && *q; ) {
    char *nl = strchr(q, '\n');
    if (nl) *nl = 0;
    if (!strncmp(q, "open-terminal", 13)) term_open_window();
    else if (!strncmp(q, "close-terminal", 14)) term_close_window();
    else if (!strncmp(q, "home", 4)) {
      action_perform("home", buf, sizeof buf);
    } else if (!strncmp(q, "action ", 7)) {
      char r[256];
      action_perform(q + 7, r, sizeof r);
    } else if (!strncmp(q, "launch ", 7)) {
      /* logical action "app:<registry-id>" from the hardware-button manager or
         the console: resolved through the LAUNCHER's own registry, so the
         authoritative app list stays the single source of truth (mission 13). */
      launcher_launch(q + 7);
    }
    q = nl ? nl + 1 : NULL;
  }
  return TRUE;
}

static void ctl_open(void) {
  const char *path = "/run/nuxel-pwa-host.cmd";
  unlink(path);
  if (mkfifo(path, 0600) < 0 && errno != EEXIST) { st("HOST_CTRL_FIFO_FAIL errno=%d", errno); return; }
  int fd = open(path, O_RDWR | O_NONBLOCK);
  if (fd < 0) { st("HOST_CTRL_FIFO_OPEN_FAIL errno=%d", errno); return; }
  ctl_chan = g_io_channel_unix_new(fd);
  g_io_channel_set_encoding(ctl_chan, NULL, NULL);
  g_io_add_watch(ctl_chan, G_IO_IN, ctl_in, NULL);
  st("HOST_CTRL_FIFO_READY %s", path);
}

static int os_owns_boot_animation(void);
static void host_api_attach(WebKitUserContentManager *ucm, WebKitWebView *v);

/* ============================================================================
 * TOUCH / INPUT DIAGNOSTIC INJECTION (A31, mission 11.5 + 12)
 *
 * The launcher source is NOT modified: this is a WebKit USER SCRIPT injected by
 * the host that reports, for one physical finger, exactly which browser events
 * the real Nuxel Home document received and which element they hit - and whether
 * the launcher's own app activation ran (`app:launch`, dispatched by
 * js/apps.js launchApp()).  Each report is forwarded to the native side through
 * a script-message handler and appended to /run/nuxel-home.state, so a single
 * physical tap can be correlated:
 *
 *   sec_ts IRQ  ->  /dev/input/event2 event  ->  nuxel-touch-arm TOUCH_POINT
 *     ->  libinput (shim log)  ->  phoc (owns event2)  ->  WebKit  ->  this log
 *
 * Disable with NUXEL_INPUT_DIAG=0.  It is a diagnostic, never a synthetic input
 * source: it only observes events that arrived from the real device.
 * ==========================================================================*/
static const char *DIAG_JS =
  "(function(){ try {"
  " if (window.__nuxelDiag) return; window.__nuxelDiag = 1;"
  " var post = function(kind, e) { try {"
  "   var t = (e.touches && e.touches[0]) || (e.changedTouches && e.changedTouches[0]) || null;"
  "   var x = (typeof e.clientX === 'number') ? e.clientX : (t ? t.clientX : -1);"
  "   var y = (typeof e.clientY === 'number') ? e.clientY : (t ? t.clientY : -1);"
  "   var el = e.target || {};"
  "   var id = el.id || '';"
  "   if (!id && el.closest) { var c = el.closest('[data-app-id],[data-app],.app-icon,.dock-item,.app-tile'); if (c) id = c.getAttribute('data-app-id') || c.getAttribute('data-app') || c.className; }"
  "   window.webkit.messageHandlers.nuxelDiag.postMessage("
  "     'EVT ' + kind + ' x=' + Math.round(x) + ' y=' + Math.round(y) +"
  "     ' tag=' + (el.tagName || '?') + ' id=' + id +"
  "     ' w=' + window.innerWidth + ' h=' + window.innerHeight +"
  "     ' dpr=' + (window.devicePixelRatio || 1) + ' splash=' + (document.getElementById('boot-splash') ? 'present' : 'absent'));"
  " } catch (err) {} };"
  " ['touchstart','touchmove','touchend','pointerdown','pointerup','click'].forEach(function(k){"
  "   document.addEventListener(k, function(e){ post(k, e); }, {passive:true, capture:true}); });"
  " document.addEventListener('app:launch', function(e){ try {"
  "   var a = (e.detail && e.detail.app) || {};"
  "   window.webkit.messageHandlers.nuxelDiag.postMessage('EVT app:launch id=' + (a.id || '?') + ' name=' + (a.name || '?'));"
  " } catch (err) {} }, true);"
  " post('diag-ready', {target:{tagName:'-'}, clientX:-1, clientY:-1});"
  /* A32: a JavaScript error in the launcher must be visible from the live console
     instead of being guessed at from the glass. */
  " var wrap = function(level){ var orig = console[level]; if (!orig) return;"
  "   console[level] = function(){ try { var a = Array.prototype.slice.call(arguments).join(' ');"
  "     window.webkit.messageHandlers.nuxelDiag.postMessage('JS-' + level + ' ' + a); } catch(e){}"
  "     return orig.apply(console, arguments); }; };"
  " ['error','warn'].forEach(wrap);"
  " window.addEventListener('error', function(e){ try {"
  "   window.webkit.messageHandlers.nuxelDiag.postMessage('JS-error ' + (e.message||'?') + ' @' + (e.filename||'?') + ':' + (e.lineno||0));"
  " } catch(x){} });"
  " var probe = function(){ try {"
  "   var cs = getComputedStyle(document.body).backgroundImage || '';"
  "   var m = cs.match(/url\\(['\"]?([^'\")]+)['\"]?\\)/);"
  "   var url = m ? m[1] : '(none)';"
  "   if (url.charAt(0) === '/') url = location.origin + url;"
  "   var img = new Image();"
  "   img.onload = function(){ post('wallpaper url=' + url + ' decoded=1 natural=' + img.naturalWidth + 'x' + img.naturalHeight, {target:{tagName:'BODY'}, clientX:-1, clientY:-1}); };"
  "   img.onerror = function(){ post('wallpaper url=' + url + ' decoded=0', {target:{tagName:'BODY'}, clientX:-1, clientY:-1}); };"
  "   img.src = url;"
  " } catch (e) {} };"
  " if (document.readyState === 'complete') probe(); else window.addEventListener('load', probe);"
  " var splash = function(tag){ try {"
  "   var el = document.getElementById('boot-splash');"
  "   var pe = el ? getComputedStyle(el).pointerEvents : 'n/a';"
  "   var dz = el ? getComputedStyle(el).zIndex : 'n/a';"
  "   post('splash-' + tag + ' ' + (el ? 'present' : 'absent') + ' pointer-events=' + pe + ' z-index=' + dz,"
  "        {target:{tagName:'BODY'}, clientX:-1, clientY:-1});"
  " } catch (e) {} };"
  " setTimeout(function(){ splash('t1s'); }, 1000);"
  " setTimeout(function(){ splash('t4s'); }, 4000);"
  " setTimeout(function(){ splash('t9s'); }, 9000);"
  "} catch (e) {} })();";

/* The launcher's own js/app.js removes #boot-splash for ?boot=os, but only after
 * an `await` in its async init - measured live: at the document's `load` event the
 * element was STILL present (diag report `splash=present`).  Until it is gone it is
 * an opaque, z-index:99999, pointer-events:auto layer over the app grid, i.e. it
 * can both hide the launcher and swallow the first touches.  The host therefore
 * enforces the ownership policy itself, two ways, only in phone launch mode:
 *   * a user STYLE SHEET - declarative, applied before first paint, so the overlay
 *     is never visible and never hit-testable;
 *   * a user SCRIPT at document start with a MutationObserver that removes the
 *     element the moment it is parsed.
 * Both are no-ops for any other launch mode (the UTM/desktop behaviour is intact). */
static const char *POLICY_CSS =
  "#boot-splash{display:none !important;visibility:hidden !important;"
  "pointer-events:none !important}";

static const char *POLICY_JS =
  "(function(){ try {"
  " if (window.__nuxelBootOwner) return;"
  " if (new URLSearchParams(window.location.search).get('boot') !== 'os') return;"
  " window.__nuxelBootOwner = 1;"
  " var kill = function(){ try { var el = document.getElementById('boot-splash');"
  "   if (el) { if (el.parentNode) el.parentNode.removeChild(el); else el.style.display='none'; } } catch(e){} };"
  " kill();"
  " var mo = new MutationObserver(function(){ kill(); });"
  " try { mo.observe(document.documentElement, {childList:true, subtree:true}); } catch(e){}"
  " window.addEventListener('DOMContentLoaded', function(){ kill(); setTimeout(kill, 250); }, {once:true});"
  " setTimeout(function(){ kill(); try { mo.disconnect(); } catch(e){} }, 15000);"
  "} catch (e) {} })();";

static void on_diag_message(WebKitUserContentManager *m, WebKitJavascriptResult *r, gpointer d) {
  (void)m; (void)d;
  JSCValue *v = webkit_javascript_result_get_js_value(r);
  char *s = v ? jsc_value_to_string(v) : NULL;
  if (s) { st("NUXEL_INPUT %s", s); g_free(s); }
}

static gboolean on_load_failed(WebKitWebView *v, WebKitLoadEvent ev, gchar *uri, GError *err, gpointer d) {
  (void)v; (void)ev; (void)d;
  st("NUXEL_HOME_LOAD_FAIL uri=%s err=%s", uri, err && err->message ? err->message : "?");
  return FALSE;
}

static void on_load_changed(WebKitWebView *v, WebKitLoadEvent ev, gpointer d) {
  (void)d;
  if (ev == WEBKIT_LOAD_FINISHED) {
    const gchar *uri = webkit_web_view_get_uri(v);
    st("NUXEL_HOME_READY uri=%s", uri ? uri : "?");
    FILE *f = fopen(READY, "w");
    if (f) { fprintf(f, "%s\n", uri ? uri : ""); fclose(f); }
  } else if (ev == WEBKIT_LOAD_COMMITTED) {
    st("NUXEL_HOME_COMMITTED uri=%s", webkit_web_view_get_uri(v) ?: "?");
  }
}

static void on_notify_uri(WebKitWebView *v, GParamSpec *p, gpointer d) {
  (void)p; (void)d;
  st("NUXEL_HOME_NAV uri=%s", webkit_web_view_get_uri(v) ?: "?");
}

/* Web-process supervision (A31, mission 15): WebKit can lose its renderer for
 * reasons outside this view's control (the A29b media-sink crash was one).  A
 * view that is never reloaded stays blank forever - this reloads it, bounded, and
 * records the exact reason code from WebKit instead of guessing. */
static int webproc_reloads;
static gboolean on_web_process_terminated(WebKitWebView *v, WebKitWebProcessTerminationReason reason, gpointer d) {
  (void)d;
  st("NUXEL_HOME_WEBPROC_TERMINATED reason=%d reload=%d", (int)reason, webproc_reloads);
  if (webproc_reloads < 5) { webproc_reloads++; webkit_web_view_reload(v); }
  else st("NUXEL_HOME_WEBPROC_GIVEUP reloads=%d", webproc_reloads);
  return FALSE;
}

/* A registry entry that opens a popup gets a real top-level Wayland window (the
 * compositor maps it fullscreen, exactly like any other client). */
static WebKitWebView *on_create(WebKitWebView *v, WebKitNavigationAction *a, gpointer d) {
  (void)v; (void)d;
  WebKitURIRequest *req = webkit_navigation_action_get_request(a);
  const gchar *uri = req ? webkit_uri_request_get_uri(req) : "?";
  st("NUXEL_APP_WINDOW uri=%s", uri ?: "?");
  return view_new();
}

/* A31 permission policy: deny by default, allow only from the trusted local
   origin, and only the capability the launcher legitimately uses (notifications -
 * js/app.js requests notifications:receive).  Camera/microphone are denied
 * because there is no working media path on this kernel, so the launcher reports
 * them truthfully as unavailable rather than holding a permission it cannot use.
 * Every request and decision is written to the state file. */
static void on_permission(WebKitWebView *v, WebKitPermissionRequest *r, gpointer d) {
  (void)d;
  const char *trusted = getenv("NUXEL_TRUSTED_ORIGIN");
  if (!trusted || !*trusted) trusted = "http://127.0.0.1:8000";
  const gchar *uri = webkit_web_view_get_uri(v);
  gboolean from_trusted = uri && g_str_has_prefix(uri, trusted);
  gboolean allow = FALSE;
  const char *reason = "denied-default";
  if (!from_trusted) {
    reason = "denied-untrusted-origin";
  } else if (WEBKIT_IS_NOTIFICATION_PERMISSION_REQUEST(r)) {
    allow = TRUE; reason = "allowed-notifications";
  } else if (WEBKIT_IS_USER_MEDIA_PERMISSION_REQUEST(r)) {
    reason = "denied-no-camera-or-microphone";
  } else {
    reason = "denied-not-required-by-launcher";
  }
  if (allow) webkit_permission_request_allow(r); else webkit_permission_request_deny(r);
  st("NUXEL_PERMISSION type=%s uri=%s trusted=%d allow=%d reason=%s",
     G_OBJECT_TYPE_NAME(r), uri ? uri : "?", from_trusted ? 1 : 0, allow ? 1 : 0, reason);
}

/* MEASURED (A29b, handset, 2026-09-15T00:07:45Z): webkit2gtk4.1-2.52.5 builds a
 * GStreamer playbin for the launcher's <video id="boot-splash-video"> splash.
 * The handset image carries gstreamer1 + gstreamer1-plugins-base but NOT
 * gstreamer1-plugins-good, so `autoaudiosink` (libgstautodetect.so) is missing.
 * The handset log then reads:
 *     phoc: GStreamer element autoaudiosink not found. Please install it
 *     WebKitWebProcess: invalid (NULL) pointer instance
 *     WebKitWebProcess: g_signal_connect_data: assertion 'G_TYPE_CHECK_INSTANCE (instance)' failed
 *     systemd-coredump: Process 6550 (WebKitWebProces) terminated abnormally
 * and the *web process* is gone: the view stays blank and is never reloaded.
 * The UTM VM renders the same page because its image has 239 gst plugins
 * (libgstautodetect.so present) - this is a host-image gap, not a launcher defect.
 *
 * So media is enabled only where the audio sink really exists, and the decision is
 * written to the state file instead of being claimed.  The launcher degrades by
 * design when media is unavailable: js/app.js hides #boot-splash on the video
 * element's 'error' event and after a 12 s safety timeout, and the phone has
 * already played the original boot animation from the initramfs before this view
 * exists (index.html + js/app.js are not modified by this port).
 */
static gboolean audio_sink_available(void) {
  static const char *p[] = {
      "/usr/lib64/gstreamer-1.0/libgstautodetect.so",
      "/usr/lib/gstreamer-1.0/libgstautodetect.so", NULL};
  for (int i = 0; p[i]; i++)
    if (g_file_test(p[i], G_FILE_TEST_EXISTS)) return TRUE;
  return FALSE;
}

static WebKitWebView *view_new(void) {
  gboolean media = audio_sink_available();
  const char *diag_env = getenv("NUXEL_INPUT_DIAG");
  gboolean diag = !(diag_env && diag_env[0] == '0');
  st("NUXEL_HOME_MEDIA enable_media=%d audio_sink=%d", media ? 1 : 0, media ? 1 : 0);
  WebKitSettings *s = webkit_settings_new_with_settings(
      "enable-javascript", TRUE,
      "enable-dns-prefetching", FALSE,
      "enable-developer-extras", FALSE,
      "javascript-can-open-windows-automatically", TRUE,
      "enable-media", media,
      "enable-mediasource", media,
      "user-agent", "Mozilla/5.0 (Linux; aarch64) Nuxel/1.0 (S10+, like Gecko) WebKitGTK",
      NULL);
  WebKitUserContentManager *ucm = webkit_user_content_manager_new();
  if (os_owns_boot_animation()) {   /* forward decl used here; defined below main's help */
    WebKitUserStyleSheet *ss = webkit_user_style_sheet_new(POLICY_CSS,
        WEBKIT_USER_CONTENT_INJECT_TOP_FRAME, WEBKIT_USER_STYLE_LEVEL_USER, NULL, NULL);
    webkit_user_content_manager_add_style_sheet(ucm, ss);
    webkit_user_style_sheet_unref(ss);
    WebKitUserScript *ps = webkit_user_script_new(POLICY_JS,
        WEBKIT_USER_CONTENT_INJECT_TOP_FRAME,
        WEBKIT_USER_SCRIPT_INJECT_AT_DOCUMENT_START, NULL, NULL);
    webkit_user_content_manager_add_script(ucm, ps);
    webkit_user_script_unref(ps);
    st("NUXEL_BOOT_POLICY host-enforced=1 css=1 dom_removal=1 (phone launch mode)");
  }
  if (diag) {
    webkit_user_content_manager_register_script_message_handler(ucm, "nuxelDiag");
    g_signal_connect(ucm, "script-message-received::nuxelDiag", G_CALLBACK(on_diag_message), NULL);
    WebKitUserScript *us = webkit_user_script_new(DIAG_JS,
        WEBKIT_USER_CONTENT_INJECT_TOP_FRAME,
        WEBKIT_USER_SCRIPT_INJECT_AT_DOCUMENT_START, NULL, NULL);
    webkit_user_content_manager_add_script(ucm, us);
    webkit_user_script_unref(us);
    st("NUXEL_INPUT_DIAG enabled=1 (user-script observer; launcher source unmodified)");
  }
  WebKitWebView *v = WEBKIT_WEB_VIEW(
      webkit_web_view_new_with_user_content_manager(ucm));
  webkit_web_view_set_settings(v, s);
  host_api_attach(ucm, v);          /* A32: settings / actions / terminal API */
  g_object_unref(ucm);
  g_object_unref(s);
  g_signal_connect(v, "load-changed", G_CALLBACK(on_load_changed), NULL);
  g_signal_connect(v, "load-failed", G_CALLBACK(on_load_failed), NULL);
  g_signal_connect(v, "create", G_CALLBACK(on_create), NULL);
  g_signal_connect(v, "permission-request", G_CALLBACK(on_permission), NULL);
  g_signal_connect(v, "web-process-terminated", G_CALLBACK(on_web_process_terminated), NULL);
  g_signal_connect(v, "notify::uri", G_CALLBACK(on_notify_uri), NULL);
  return v;
}

/* Is the OS the boot-animation owner for this launch?  On the phone: yes (the
 * initramfs player already ran).  NUXEL_PWA_SPLASH=1 opts back into the PWA's
 * own splash, which is what the UTM/desktop path wants. */
static int os_owns_boot_animation(void) {
  const char *e = getenv("NUXEL_PWA_SPLASH");
  return !(e && e[0] == '1');
}

int main(int argc, char **argv) {
  /* Invalidate persisted launcher state BEFORE WebKit is initialised: nothing may
     open those paths while they are being removed (measured A32 crash when the
     WebKit data-manager API was used instead during startup). */
  purge_launcher_cache();
  gtk_init(&argc, &argv);
  const char *url = getenv("NUXEL_HOME_URL");
  if (!url || !*url) url = DEFAULT_URL;
  char urlbuf[1024];
  if (os_owns_boot_animation()) {
    /* the stamp is the served index.html's own size+mtime: change the file and the
       launcher URL changes with it (mission 7.2, versioned asset deployment) */
    struct stat sb;
    unsigned long stamp = 0;
    if (stat("/usr/share/nuxel/nuxel-home/index.html", &sb) == 0)
      stamp = (unsigned long)sb.st_mtime + (unsigned long)sb.st_size;
    snprintf(urlbuf, sizeof urlbuf, "%s%sboot=os&v=%lu", url, strchr(url, '?') ? "&" : "?", stamp);
    url = urlbuf;
  }

  GtkWidget *win = gtk_window_new(GTK_WINDOW_TOPLEVEL);
  gtk_window_set_title(GTK_WINDOW(win), "Nuxel");
  gtk_window_set_decorated(GTK_WINDOW(win), FALSE);
  gtk_window_set_resizable(GTK_WINDOW(win), TRUE);
  gtk_widget_set_size_request(win, 360, 760);
  GtkWidget *v = GTK_WIDGET(view_new());
  gtk_container_add(GTK_CONTAINER(win), v);
  g_signal_connect(win, "destroy", G_CALLBACK(gtk_main_quit), NULL);
  g_main_window = win;
  g_main_view = WEBKIT_WEB_VIEW(v);
  ctl_open();
  uevent_open();
  indicator_fallback_start();
  gtk_widget_show_all(win);
  gtk_window_fullscreen(GTK_WINDOW(win));

  st("NUXEL_HOME_BOOT_OWNER os_animation=%d splash_removed_by_launcher=%d",
     os_owns_boot_animation(), os_owns_boot_animation());
  st("NUXEL_HOME_OPEN url=%s engine=WebKitGTK/%d.%d", url,
     webkit_get_major_version(), webkit_get_minor_version());
  webkit_web_view_load_uri(WEBKIT_WEB_VIEW(v), url);
  gtk_main();
  st("NUXEL_HOME_EXIT");
  return 0;
}
