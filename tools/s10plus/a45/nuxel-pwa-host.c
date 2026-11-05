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
#include <ifaddrs.h>
#include <arpa/inet.h>
#include <net/if.h>
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
#include <pwd.h>
#include <zlib.h>

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

/* PWNAGE-54000: the launcher state is an append-only diagnostics log and is
 * polled by Home every few seconds.  It previously grew without bound (measured
 * 286 KB after one hour), so every status read became a larger file read and
 * the journal/disk got slower over time.  Keep one bounded file; rotate once at
 * 256 KiB.  The recent tail remains available for touch/input evidence. */
#define STATE_MAX_BYTES (256u * 1024u)
static void st(const char *fmt, ...) __attribute__((format(printf, 1, 2)));
static void st(const char *fmt, ...) {
  static int rotated;
  if (!rotated) {
    struct stat sb;
    if (stat(STATE, &sb) == 0 && (unsigned long long)sb.st_size > STATE_MAX_BYTES) {
      char old[64];
      snprintf(old, sizeof old, "%s.1", STATE);
      rename(STATE, old);
    }
    rotated = 1;
  }
  FILE *f = fopen(STATE, "a");
  if (!f) return;
  fprintf(f, "%ld ", (long)time(NULL));
  va_list ap; va_start(ap, fmt); vfprintf(f, fmt, ap); va_end(ap);
  fputc('\n', f); fclose(f);
}

/* ============================================================================
 * PWNAGE-63000 — launcher-minted keyring tokens
 *
 * The WebKit iframe used for a PWA does not send a Referer header (measured on
 * the S10+), so the HTTP bridge cannot tell Vault from an arbitrary same-origin
 * page by Referer alone.  The trusted top-level Home page relays a token request
 * from the exact iframe it created; this root-owned host injects a top-frame-only
 * script that exchanges that request for a Bridge token using a per-device
 * secret in a root-only file.  The secret lives in the user-script closure, is
 * never exposed as a window property, and iframes do not receive this script.
 * ==========================================================================*/
#define KEYRING_SECRET_PATH "/etc/nuxel/keyring-launcher.secret"
static char g_launcher_secret[65];

static int hex64(const char *s) {
  size_t n = strlen(s);
  if (n != 64) return 0;
  for (size_t i = 0; i < n; i++) {
    char c = s[i];
    if (!((c >= '0' && c <= '9') || (c >= 'a' && c <= 'f') || (c >= 'A' && c <= 'F'))) return 0;
  }
  return 1;
}

static void keyring_secret_load(void) {
  char buf[256] = {0};
  FILE *f = fopen(KEYRING_SECRET_PATH, "r");
  if (f) {
    if (fgets(buf, sizeof buf, f)) {
      char *p = buf;
      while (*p == ' ' || *p == '\t' || *p == '\r' || *p == '\n') p++;
      size_t n = strlen(p);
      while (n && (p[n-1] == '\r' || p[n-1] == '\n' || p[n-1] == ' ' || p[n-1] == '\t')) p[--n] = 0;
      if (hex64(p)) snprintf(g_launcher_secret, sizeof g_launcher_secret, "%s", p);
    }
    fclose(f);
  }
  if (g_launcher_secret[0]) {
    st("NUXEL_KEYRING_SECRET loaded=1");
    return;
  }
  unsigned char raw[32];
  int ok = 0;
  int fd = open("/dev/urandom", O_RDONLY | O_CLOEXEC);
  if (fd >= 0) {
    ssize_t got = read(fd, raw, sizeof raw);
    close(fd);
    if (got == (ssize_t)sizeof raw) ok = 1;
  }
  if (!ok) { st("NUXEL_KEYRING_SECRET missing=1 urandom=0"); return; }
  char hex[65];
  for (int i = 0; i < 32; i++) snprintf(hex + i * 2, 3, "%02x", raw[i]);
  hex[64] = 0;
  int out = open(KEYRING_SECRET_PATH, O_WRONLY | O_CREAT | O_TRUNC | O_CLOEXEC, 0600);
  if (out < 0) { st("NUXEL_KEYRING_SECRET write_failed=1"); return; }
  ssize_t wrote = write(out, hex, 64);
  if (wrote == 64) { write(out, "\n", 1); fsync(out); }
  close(out);
  if (wrote != 64) { st("NUXEL_KEYRING_SECRET write_failed=1"); return; }
  snprintf(g_launcher_secret, sizeof g_launcher_secret, "%s", hex);
  st("NUXEL_KEYRING_SECRET generated=1");
}

static void keyring_mint_attach(WebKitUserContentManager *ucm) {
  if (!ucm || !g_launcher_secret[0]) {
    st("NUXEL_KEYRING_MINT disabled=missing-secret");
    return;
  }
  GString *js = g_string_new(
      "(function(){"
      "if(window.top!==window)return;"
      "var S=\"");
  g_string_append(js, g_launcher_secret);
  g_string_append(js,
      "\";"
      "var F=window.fetch.bind(window);"
      "function reply(o){try{window.postMessage(o,window.location.origin);}catch(e){}}"
      "window.addEventListener('message',function(e){"
        "if(e.source!==window||e.origin!==window.location.origin||!e.data||e.data.type!=='nuxel-keyring-mint')return;"
        "var a=String(e.data.app_id||''),n=String(e.data.nonce||'');"
        "if(!/^[A-Za-z0-9._:-]{1,64}$/.test(a)||!/^[A-Za-z0-9._-]{8,96}$/.test(n))return;"
        "F('http://127.0.0.1:8080/api/v1/auth/app-token',{method:'POST',headers:{'Content-Type':'application/json','X-Nuxel-Launcher-Secret':S},body:JSON.stringify({app_id:a,nonce:n})})"
        ".then(function(r){return r.json();})"
        ".then(function(d){reply({type:'nuxel-keyring-token',nonce:n,token:(d&&d.token)||''});})"
        ".catch(function(){reply({type:'nuxel-keyring-token',nonce:n,token:''});});"
      "});"
      "})();");
  WebKitUserScript *ks = webkit_user_script_new(js->str,
      WEBKIT_USER_CONTENT_INJECT_TOP_FRAME,
      WEBKIT_USER_SCRIPT_INJECT_AT_DOCUMENT_START, NULL, NULL);
  webkit_user_content_manager_add_script(ucm, ks);
  webkit_user_script_unref(ks);
  g_string_free(js, TRUE);
  st("NUXEL_KEYRING_MINT enabled=1 top-frame-only=1");
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
    char base[1536], path[1600], type[64] = "unknown", capbuf[32] = "";
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
    char path[1600], value[128] = "";
    snprintf(path, sizeof path, "%s/%s/UDC", ind_root("NUXEL_CONFIGFS_GADGET", "/sys/kernel/config/usb_gadget"), de->d_name);
    if (ind_read_line(path, value, sizeof value) && value[0]) { bound = 1; break; }
  }
  closedir(d);
  return bound;
}

/* A73: independent physical detach signal.  Samsung 4.14 can leave a bound
   gadget + "configured" UDC intact after a physical cable pull, so the
   Type-C class data_role is read and a real detach (no [device] role) vetoes
   a stale positive.  A74: the DWC3 debugfs link_state read was REMOVED — on
   this downstream 4.14 kernel it dereferences the controller registers while
   the FSYS0 power domain can be off right after detach, producing a bus
   SLVERR that escalates to a hard lockup + watchdog reset.  The Type-C
   data_role is sufficient on its own and is a safe PMIC class attribute. */
static int ind_typec_device_role(void) {
  /* -1 = Type-C class absent, 0 = present but no [device] role, 1 = [device]. */
  DIR *d = opendir(ind_root("NUXEL_SYS_TYPEC", "/sys/class/typec"));
  if (!d) return -1;
  int saw_port = 0, device_role = 0;
  struct dirent *de;
  while ((de = readdir(d))) {
    if (!strcmp(de->d_name, ".") || !strcmp(de->d_name, "..")) continue;
    if (strstr(de->d_name, "-partner") || strstr(de->d_name, "-cable")) continue;
    char path[1600], role[128] = "";
    snprintf(path, sizeof path, "%s/%s/data_role",
             ind_root("NUXEL_SYS_TYPEC", "/sys/class/typec"), de->d_name);
    if (ind_read_line(path, role, sizeof role)) {
      saw_port = 1;
      if (strstr(role, "[device]")) { device_role = 1; break; }
    }
  }
  closedir(d);
  if (!saw_port) return -1;
  return device_role ? 1 : 0;
}

/* Speeds a connected gadget controller can report.  The S10+ DWC3 controller
   reports ``UNKNOWN`` after a physical detach while the gadget framework still
   says ``configured`` (measured: /var/lib/nuxel/a74-usb-unplug.log). */
static int ind_speed_connected(const char *speed) {
  return ind_eq_ci(speed, "low-speed") || ind_eq_ci(speed, "full-speed") ||
         ind_eq_ci(speed, "high-speed") || ind_eq_ci(speed, "super-speed") ||
         ind_eq_ci(speed, "super-speed-plus");
}

/* Return 1 when a UDC is configured, and report that controller's
   current_speed (empty when the attribute is absent, which is neutral). */
static int ind_udc_configured(char *speed, size_t speedn) {
  if (speed && speedn) speed[0] = 0;
  DIR *d = opendir(ind_root("NUXEL_SYS_UDC", "/sys/class/udc"));
  if (!d) return 0;
  int connected = 0;
  struct dirent *de;
  while ((de = readdir(d))) {
    if (!strcmp(de->d_name, ".") || !strcmp(de->d_name, "..")) continue;
    char path[1600], state[64] = "";
    snprintf(path, sizeof path, "%s/%s/state", ind_root("NUXEL_SYS_UDC", "/sys/class/udc"), de->d_name);
    if (!ind_read_line(path, state, sizeof state)) continue;
    if (ind_eq_ci(state, "configured")) {
      connected = 1;
      if (speed && speedn) {
        snprintf(path, sizeof path, "%s/%s/current_speed",
                 ind_root("NUXEL_SYS_UDC", "/sys/class/udc"), de->d_name);
        if (!ind_read_line(path, speed, speedn)) speed[0] = 0;
      }
      break;
    }
  }
  closedir(d);
  return connected;
}

/* A bus-powered USB gadget cannot carry a data link without VBUS.  Wireless
   charging is deliberately excluded: it powers the battery but never data.
   -1 = no readable wired supply, 0 = every readable wired supply offline,
    1 = at least one wired supply online. */
static int ind_wired_vbus(void) {
  int seen = 0;
  DIR *d = opendir(ind_root("NUXEL_SYS_POWER_SUPPLY", "/sys/class/power_supply"));
  if (!d) return -1;
  struct dirent *de;
  while ((de = readdir(d))) {
    if (!strcmp(de->d_name, ".") || !strcmp(de->d_name, "..")) continue;
    char base[1536], type[64] = "unknown", path[1600];
    snprintf(base, sizeof base, "%s/%s",
             ind_root("NUXEL_SYS_POWER_SUPPLY", "/sys/class/power_supply"), de->d_name);
    if (!ind_path_exists(base)) continue;
    snprintf(path, sizeof path, "%s/type", base);
    if (!ind_read_line(path, type, sizeof type)) continue;
    int wired = ind_eq_ci(type, "usb") || ind_eq_ci(type, "usb-pd") ||
                ind_eq_ci(type, "usb_typec") || ind_eq_ci(type, "usb_type_c") ||
                ind_eq_ci(type, "usb_c") || ind_eq_ci(type, "mains") ||
                ind_eq_ci(type, "ac") || ind_eq_ci(type, "dc") ||
                ind_eq_ci(type, "charger") || ind_eq_ci(type, "quick_charge") ||
                ind_eq_ci(type, "hv_charger");
    if (!wired) continue;
    snprintf(path, sizeof path, "%s/online", base);
    int online = ind_online(path);
    if (online < 0) continue;
    seen = 1;
    if (online == 1) { closedir(d); return 1; }
  }
  closedir(d);
  return seen ? 0 : -1;
}

static int ind_pc_connected_ex(char *source, size_t sourcen) {
  if (!ind_gadget_bound()) {
    if (source) snprintf(source, sourcen, "%s", "unavailable:gadget-not-bound");
    return 0;
  }
  char speed[64] = "";
  if (!ind_udc_configured(speed, sizeof speed)) {
    if (source) snprintf(source, sourcen, "%s", "unavailable:no-udc-config");
    return 0;
  }
  int typec = ind_typec_device_role();
  if (typec == 0) {
    if (source) snprintf(source, sourcen, "%s",
                         "sysfs:udc:configured-vetoed-by-physical-detach");
    return 0;
  }
  /* A77: data_role and UDC state both stay stale on this board after a real
     cable pull.  A non-connected current_speed is a positive detach signal. */
  if (speed[0] && !ind_speed_connected(speed)) {
    if (source) snprintf(source, sourcen, "%s",
                         "sysfs:udc:configured-vetoed-by-udc-speed");
    return 0;
  }
  /* A77: no wired VBUS means the bus-powered gadget cannot be attached. */
  if (ind_wired_vbus() == 0) {
    if (source) snprintf(source, sourcen, "%s",
                         "sysfs:udc:configured-vetoed-by-no-vbus");
    return 0;
  }
  if (source) snprintf(source, sourcen, "%s", "sysfs:udc:configured");
  return 1;
}
static int ind_pc_connected(void) {
  return ind_pc_connected_ex(NULL, 0);
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
    /* fdpath is up to 511 chars and de->d_name up to 255, so a 512-byte
       linkpath can truncate.  GCC's -Werror=format-truncation caught this on
       Ubuntu; size it for the worst case and check the result. */
    char linkpath[768], target[512];
    int ln = snprintf(linkpath, sizeof linkpath, "%s/%s", fdpath, de->d_name);
    if (ln < 0 || (size_t)ln >= sizeof linkpath) continue;
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

static int ind_console_service_armed(void) {
  /* True when any nuxel-console process is alive (daemon armed), independent
     of whether a host is attached or a session is active.  This is the
     "service armed" layer; the display predicate is ind_live_console(). */
  DIR *d = opendir(ind_root("NUXEL_PROC", "/proc"));
  if (!d) return 0;
  int armed = 0;
  struct dirent *de;
  while ((de = readdir(d))) {
    if (!strcmp(de->d_name, ".") || !strcmp(de->d_name, "..")) continue;
    if (de->d_name[0] < '0' || de->d_name[0] > '9') continue;
    pid_t pid = (pid_t)atoi(de->d_name);
    if (pid > 0 && ind_cmdline_has(pid, "nuxel-console")) { armed = 1; break; }
  }
  closedir(d);
  return armed;
}

/* ---------------------------------------------------------------------------
 * PWNAGE-34000: independent console transports + file-transfer/mode truth.
 * Serial is the existing live-console predicate.  WLAN is a reachable key-only
 * sshd listener on a non-loopback address (with a separate established-session
 * count so a listening-but-idle console is not mislabelled).  USB network is
 * blocked on this kernel and is therefore never presented as active.
 * ------------------------------------------------------------------------- */
static int ind_json_bool_field(const char *path, const char *key, int *out) {
  char buf[2048];
  if (!ind_read_line(path, buf, sizeof buf)) return 0;
  char pat[80];
  snprintf(pat, sizeof pat, "\"%s\":", key);
  char *p = strstr(buf, pat);
  if (!p) return 0;
  p += strlen(pat);
  while (*p == ' ' || *p == '\t') p++;
  if (!strncmp(p, "true", 4)) { *out = 1; return 1; }
  if (!strncmp(p, "false", 5)) { *out = 0; return 1; }
  return 0;
}

static int ind_json_str_field(const char *path, const char *key, char *out, size_t outn) {
  char buf[2048];
  if (!ind_read_line(path, buf, sizeof buf)) return 0;
  char pat[80];
  snprintf(pat, sizeof pat, "\"%s\":", key);
  char *p = strstr(buf, pat);
  if (!p) return 0;
  p += strlen(pat);
  while (*p == ' ' || *p == '\t') p++;
  if (*p != '"') return 0;
  p++;
  size_t i = 0;
  while (*p && *p != '"' && i + 1 < outn) out[i++] = *p++;
  out[i] = 0;
  return 1;
}

/* True interactive WLAN SSH console sessions.
 *
 * A listening sshd, a Wi-Fi address, a port-forward, an SFTP subsystem or a
 * one-shot `ssh host true` are all *not* console sessions.  A session counts
 * only when an ESTABLISHED TCP/22 socket has a local address belonging to a
 * real Wi-Fi interface AND its sshd process has a live descendant owned by the
 * nuxel account running an interactive shell with stdin/stdout/stderr on a
 * /dev/pts pty.  Socket inodes make the attribution exact and let the count
 * drop as soon as the last session closes. */
static int ind_wifi_ipv4(char out[][INET_ADDRSTRLEN], int max) {
  struct ifaddrs *ifa = NULL;
  int n = 0;
  if (getifaddrs(&ifa) != 0) return 0;
  for (struct ifaddrs *a = ifa; a && n < max; a = a->ifa_next) {
    if (!a->ifa_addr || a->ifa_addr->sa_family != AF_INET) continue;
    if (!(a->ifa_flags & IFF_UP) || (a->ifa_flags & IFF_LOOPBACK)) continue;
    const char *name = a->ifa_name ? a->ifa_name : "";
    if (strncmp(name, "usb", 3) && strncmp(name, "ncm", 3) &&
        strncmp(name, "rndis", 5) && strncmp(name, "wlan", 4) &&
        strncmp(name, "wlp", 3) && strncmp(name, "wifi", 4) &&
        strncmp(name, "wl", 2)) continue;
    const struct sockaddr_in *sin = (const struct sockaddr_in *)a->ifa_addr;
    if (inet_ntop(AF_INET, &sin->sin_addr, out[n], INET_ADDRSTRLEN)) n++;
  }
  freeifaddrs(ifa);
  return n;
}

static int ind_pid_comm(pid_t pid, char *out, size_t outn) {
  char path[512];
  snprintf(path, sizeof path, "%s/%d/comm", ind_root("NUXEL_PROC", "/proc"), (int)pid);
  return ind_read_line(path, out, outn);
}

static long ind_pid_ppid(pid_t pid) {
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
    if (field == 4) return strtol(tok, NULL, 10);  /* ppid */
  }
  return -1;
}

static int ind_pid_uid(pid_t pid) {
  char path[512], text[2048];
  snprintf(path, sizeof path, "%s/%d/status", ind_root("NUXEL_PROC", "/proc"), (int)pid);
  FILE *f = fopen(path, "rb");
  if (!f) return -1;
  size_t n = fread(text, 1, sizeof text - 1, f);
  fclose(f);
  text[n] = 0;
  char *p = strstr(text, "\nUid:");
  if (!p) p = strstr(text, "Uid:");
  if (!p) return -1;
  p = strchr(p, '\t');
  if (!p) return -1;
  return (int)strtol(p + 1, NULL, 10);
}

static int ind_pid_has_pts(pid_t pid) {
  char fdpath[512];
  snprintf(fdpath, sizeof fdpath, "%s/%d/fd", ind_root("NUXEL_PROC", "/proc"), (int)pid);
  DIR *d = opendir(fdpath);
  if (!d) return 0;
  int holds = 0;
  struct dirent *de;
  while ((de = readdir(d))) {
    if (de->d_name[0] < '0' || de->d_name[0] > '9') continue;
    char lp[768], target[512];
    snprintf(lp, sizeof lp, "%s/%s", fdpath, de->d_name);
    ssize_t n = readlink(lp, target, sizeof target - 1);
    if (n <= 0) continue;
    target[n] = 0;
    if (!strncmp(target, "/dev/pts/", 9)) { holds = 1; break; }
  }
  closedir(d);
  return holds;
}

static int ind_pid_has_socket_inode(pid_t pid, unsigned long inode) {
  char fdpath[512], want[64];
  snprintf(want, sizeof want, "socket:[%lu]", inode);
  snprintf(fdpath, sizeof fdpath, "%s/%d/fd", ind_root("NUXEL_PROC", "/proc"), (int)pid);
  DIR *d = opendir(fdpath);
  if (!d) return 0;
  int found = 0;
  struct dirent *de;
  while ((de = readdir(d))) {
    if (de->d_name[0] < '0' || de->d_name[0] > '9') continue;
    char lp[768], target[512];
    snprintf(lp, sizeof lp, "%s/%s", fdpath, de->d_name);
    ssize_t n = readlink(lp, target, sizeof target - 1);
    if (n <= 0) continue;
    target[n] = 0;
    if (!strcmp(target, want)) { found = 1; break; }
  }
  closedir(d);
  return found;
}

static int ind_is_descendant(pid_t pid, pid_t ancestor) {
  pid_t cur = pid;
  for (int depth = 0; depth < 12 && cur > 1; depth++) {
    long pp = ind_pid_ppid(cur);
    if (pp <= 0) return 0;
    if ((pid_t)pp == ancestor) return 1;
    cur = (pid_t)pp;
  }
  return 0;
}

static int ind_shell_name(const char *comm) {
  static const char *names[] = { "bash", "sh", "zsh", "fish", "dash", "ash", "ksh", NULL };
  for (int i = 0; names[i]; i++) if (!strcmp(comm, names[i])) return 1;
  return 0;
}

static int ind_interactive_descendant(pid_t owner) {
  DIR *d = opendir(ind_root("NUXEL_PROC", "/proc"));
  if (!d) return 0;
  int found = 0;
  struct dirent *de;
  while ((de = readdir(d))) {
    if (de->d_name[0] < '0' || de->d_name[0] > '9') continue;
    pid_t pid = (pid_t)atoi(de->d_name);
    if (pid <= 0 || pid == owner) continue;
    char comm[64] = "";
    if (!ind_pid_comm(pid, comm, sizeof comm)) continue;
    if (!ind_shell_name(comm)) continue;
    if (ind_pid_uid(pid) != 1000) continue;
    if (!ind_pid_has_pts(pid)) continue;
    if (!ind_is_descendant(pid, owner)) continue;
    found = 1;
    break;
  }
  closedir(d);
  return found;
}

static int ind_wlan_ssh_sessions(void) {
  static time_t cached_at;
  static int cached_count;
  time_t now = time(NULL);
  if (cached_at && now - cached_at < 1) return cached_count;
  cached_at = now;
  cached_count = 0;

  char wifi[8][INET_ADDRSTRLEN];
  int nwifi = ind_wifi_ipv4(wifi, 8);
  if (nwifi <= 0) return 0;

  unsigned long seen[32];
  int nseen = 0;
  const char *files[] = { "/proc/net/tcp", "/proc/net/tcp6" };
  for (int fi = 0; fi < 2; fi++) {
    FILE *f = fopen(files[fi], "r");
    if (!f) continue;
    char line[512];
    int first = 1;
    while (fgets(line, sizeof line, f)) {
      if (first) { first = 0; continue; }
      char local[128], st[16], inodebuf[64];
      if (sscanf(line, "%*s %127s %*s %15s %*s %*s %*s %*s %*s %63s",
                 local, st, inodebuf) != 3) continue;
      if (strcmp(st, "01") != 0) continue;
      char *colon = strchr(local, ':');
      if (!colon) continue;
      if ((int)strtol(colon + 1, NULL, 16) != 22) continue;
      unsigned long inode = strtoul(inodebuf, NULL, 10);
      if (!inode || nseen >= (int)(sizeof seen / sizeof seen[0])) continue;

      int matches = 0;
      if (fi == 0) {
        unsigned a = 0, b = 0, c = 0, d = 0;
        *colon = 0;
        if (sscanf(local, "%2x%2x%2x%2x", &a, &b, &c, &d) == 4) {
          char ip[INET_ADDRSTRLEN];
          snprintf(ip, sizeof ip, "%u.%u.%u.%u", d, c, b, a);
          for (int i = 0; i < nwifi; i++)
            if (!strcmp(ip, wifi[i])) { matches = 1; break; }
        }
      } else {
        /* The S10+ WLAN SSH path is IPv4.  Do not guess an IPv6 interface
           from a global address: that could mislabel USB-network or another
           namespace as WLAN.  IPv6 sessions stay uncounted until an exact
           local-address match is added. */
        matches = 0;
      }
      if (!matches) continue;

      int duplicate = 0;
      for (int i = 0; i < nseen; i++) if (seen[i] == inode) duplicate = 1;
      if (duplicate) continue;

      /* Find the sshd process holding this exact socket inode. */
      DIR *d = opendir(ind_root("NUXEL_PROC", "/proc"));
      if (!d) continue;
      struct dirent *de;
      pid_t owner = 0;
      while ((de = readdir(d))) {
        if (de->d_name[0] < '0' || de->d_name[0] > '9') continue;
        pid_t pid = (pid_t)atoi(de->d_name);
        if (pid <= 0) continue;
        char comm[64] = "";
        if (!ind_pid_comm(pid, comm, sizeof comm)) continue;
        if (!strstr(comm, "sshd")) continue;
        if (ind_pid_has_socket_inode(pid, inode)) { owner = pid; break; }
      }
      closedir(d);
      if (!owner) continue;
      if (!ind_interactive_descendant(owner)) continue;
      seen[nseen++] = inode;
      cached_count++;
    }
    fclose(f);
  }
  return cached_count;
}

/* Kept for the availability side: a listener is reported separately, never as
 * an active console. */
static void ind_ssh_tcp(int *listening, int *established) {
  *listening = 0;
  *established = ind_wlan_ssh_sessions();
  const char *files[] = { "/proc/net/tcp", "/proc/net/tcp6" };
  for (int fi = 0; fi < 2; fi++) {
    FILE *f = fopen(files[fi], "r");
    if (!f) continue;
    char line[512];
    int first = 1;
    while (fgets(line, sizeof line, f)) {
      if (first) { first = 0; continue; }
      char local[128], st[16];
      if (sscanf(line, "%*s %127s %*s %15s", local, st) != 2) continue;
      char *colon = strchr(local, ':');
      if (!colon) continue;
      if ((int)strtol(colon + 1, NULL, 16) != 22) continue;
      if (!strcmp(st, "0A") && strcmp(local, "0100007F:0016")) *listening = 1;
    }
    fclose(f);
  }
}

static void indicators_json(char *out, size_t outn) {
  int external_power = 0, charging = 0;
  ind_power(&external_power, &charging);
  char pcsrc[96] = "";
  int pc = ind_pc_connected_ex(pcsrc, sizeof pcsrc);
  int serial_active = ind_live_console();
  int armed = ind_console_service_armed();
  int wlan = 0, ssh_sessions = 0;
  ind_ssh_tcp(&wlan, &ssh_sessions);
  /* PWNAGE-62000 visual contract: the base live penguin means "the Live
     Console service is running/ready" (or a transport session is active).
     The serial/USB/WLAN type icons mean an actual interactive session only. */
  int live = armed || serial_active || (ssh_sessions > 0);
  int ft_active = 0;
  ind_json_bool_field("/run/nuxel/usb-mode.state", "active", &ft_active);
  /* Bluetooth is proof-only: the authoritative bridge/provider writes this
     document.  A missing or malformed document leaves it UNKNOWN (null), which
     hides the indicator; it is never interpreted as OFF. */
  int bt_powered = 0, bt_discovering = 0, bt_known = 0;
  char bt_state[32] = "unknown";
  char bt_source[96] = "unavailable:no-provider-state";
  const char *btpath = ind_root("NUXEL_BLUETOOTH_INDICATOR",
                                "/run/nuxel/bluetooth-indicator.json");
  if (ind_path_exists(btpath)) {
    if (ind_json_bool_field(btpath, "powered", &bt_powered)) bt_known = 1;
    ind_json_bool_field(btpath, "discovering", &bt_discovering);
    if (ind_json_str_field(btpath, "state", bt_state, sizeof bt_state)) {
      if (strcmp(bt_state, "on") && strcmp(bt_state, "off") &&
          strcmp(bt_state, "discovering") && strcmp(bt_state, "unknown") &&
          strcmp(bt_state, "hardware_blocked") && strcmp(bt_state, "service_unavailable")) {
        strcpy(bt_state, "unknown");
      }
    }
    snprintf(bt_source, sizeof bt_source, "bridge:bluetooth-indicator");
  }
  char mode[32] = "charging";
  if (!ind_json_str_field("/run/nuxel/connection-mode.json", "mode", mode, sizeof mode)) {
    strcpy(mode, "charging");
  }
  int level = -1;
  char levelbuf[32] = "";
  /* Level is informational only; the icon is driven by the booleans. */
  const char *psroot = ind_root("NUXEL_SYS_POWER_SUPPLY", "/sys/class/power_supply");
  DIR *ps = opendir(psroot);
  if (ps) {
    struct dirent *de;
    while ((de = readdir(ps))) {
      if (!strcmp(de->d_name, ".") || !strcmp(de->d_name, "..")) continue;
      char typepath[1600], type[64] = "unknown", cappath[1600];
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
    "\"usb_data\":{\"pc_connected\":%d,\"source\":\"%s\"},"
    "\"live_console\":{\"active\":%d,\"service_armed\":%d,\"transport_connected\":%d,\"session_active\":%d,\"source\":\"proc:nuxel-console:tty\"},"
    "\"console_transports\":{"
      "\"serial\":{\"active\":%d,\"source\":\"%s\"},"
      "\"usb\":{\"active\":0,\"source\":\"blocked-kernel-usb-network\",\"sessions\":0},"
      "\"wlan\":{\"active\":%d,\"source\":\"%s\",\"sessions\":%d}},"
    "\"file_transfer\":{\"active\":%d,\"selected\":\"%s\",\"endpoint_state\":\"%s\",\"source\":\"%s\",\"error\":null},"
    "\"bluetooth\":{\"powered\":%s,\"state\":\"%s\",\"discovering\":%s,\"source\":\"%s\"},"
    "\"connection_mode\":{\"selected\":\"%s\",\"transition_in_progress\":0,\"host_connected\":%d,\"endpoint_state\":\"%s\",\"last_error\":null}}",
    external_power, charging, level, pc, pcsrc, live, armed, pc, serial_active,
    serial_active, (serial_active ? "proc:nuxel-console:tty" : "inactive:no-console-session"),
    (ssh_sessions > 0), (ssh_sessions > 0 ? "wlan:interactive-pty-session" :
                         "inactive:no-interactive-session"), ssh_sessions,
    ft_active, mode, (ft_active ? "active" : "inactive"), (ft_active ? "usb-mode-helper" : "unavailable:not-activated"),
    (bt_known ? (bt_powered ? "true" : "false") : "null"), bt_state,
    (bt_discovering ? "true" : "false"), bt_source,
    mode, pc, (ft_active ? "active" : "inactive"));
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
  /* Drain the whole datagram queue.  A kobject burst used to leave one
   * GLib callback per datagram, each scheduling the same 120 ms refresh. */
  for (;;) {
    char buf[4096];
    gsize got = 0;
    GError *err = NULL;
    GIOStatus rc = g_io_channel_read_chars(ch, buf, sizeof buf - 1, &got, &err);
    if (rc != G_IO_STATUS_NORMAL) {
      if (err) g_error_free(err);
      break;
    }
    buf[got] = 0;
    if (strstr(buf, "power_supply") || strstr(buf, "usb") || strstr(buf, "udc") ||
        strstr(buf, "typec") || strstr(buf, "ttyGS0") || strstr(buf, "dwc3")) {
      if (!ind_uevent_timeout) ind_uevent_timeout = (guint)g_timeout_add(120, ind_push_event, NULL);
    }
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
  int power = 0, charging = 0, pc = 0, live = 0, bt = 0;
  ind_power(&power, &charging);
  pc = ind_pc_connected();
  live = ind_live_console();
  ind_json_bool_field(ind_root("NUXEL_BLUETOOTH_INDICATOR",
                               "/run/nuxel/bluetooth-indicator.json"),
                      "powered", &bt);
  snprintf(out, outn, "p%d c%d pc%d l%d bt%d", power, charging, pc, live, bt);
}

static gboolean ind_signature_tick(gpointer data) {
  (void)data;
  if (!g_main_view) return TRUE;
  /* The kobject uevent socket is the event source.  This signature read is a
   * safety net for state that does not emit uevents (e.g. a console session
   * appearing/disappearing).  G_LIKELY signatures change on power/USB events,
   * which the netlink path already pushes within 120 ms; re-reading every
   * second was measurably pure idle churn.  Keep a 5 s floor so a missed
   * uevent is still caught quickly. */
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
  /* The kobject uevent socket is the primary path.  This signature fallback is
   * only for kernels where a non-root session cannot bind it; 1 s is still
   * event-driven at the UI boundary (it pushes only on a real state change) and
   * removes four wakeups/second while the phone is idle. */
  ind_fallback_timer = (guint)g_timeout_add(5000, ind_signature_tick, NULL);
  st("HOST_INDICATOR_FALLBACK interval=5000ms push-on-change=1");
}

struct cfgfile { const char *name; const char *path; int writable; };
static const struct cfgfile CFG[] = {
  { "statusbar-safezones", "/etc/nuxel/display/statusbar-safezones.json", 1 },
  { "statusbar-icons",     "/etc/nuxel/display/statusbar-icons.json",     1 },
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
  { "keyboard-visible",    "/run/nuxel-keyboard.visible",                  0 },
  { "lock-state",          "/run/nuxel/security/lock-state.json",            0 },
  { "navdock-state",       "/run/nuxel-navdock.state",                     0 },
  { "navdock-json",        "/run/nuxel-navdock.json",                      0 },
  { "statusbar-json",      "/run/nuxel-statusbar.state",                   0 },
  { "shell-chrome",        "/run/nuxel/shell-chrome.json",                 0 },
  { "lock-enforcement",    "/run/nuxel/lock-enforcement.state",            0 },
  { "foreground",          "/run/nuxel/foreground.state",                  0 },
  { "power-action-result", "/run/nuxel/power-action.result",               0 },
  /* Real S10+ battery nodes (the gauge is named `battery`, not BAT*). */
  { "battery-capacity",    "/sys/class/power_supply/battery/capacity",     0 },
  { "battery-status",      "/sys/class/power_supply/battery/status",       0 },
  /* A45 Display & Lockscreen: the Home Settings timeout selector writes this
     document, which nuxel-button-manager (the single idle owner) reads live. */
  { "display-timeout",     "/etc/nuxel/display/screen-timeout.json",      1 },
  /* A68 lockhead indicators: computed in-process from sysfs, not a file read. */
  { "system-indicators",   NULL,                                           0 },
  /* Power surface (Settings > Power and power-menu.html): the menu table and
     the battery-mode profiles are the SAME documents nuxel-button-manager and
     nuxel-power-diag.sh read.  Read-only here; the actions go through the
     manager's reboot gate / host action path. */
  { "power-menu",          "/etc/nuxel/power/power-menu.json",            0 },
  { "power",               "/etc/nuxel/power/power.json",                 0 },
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

/* ---------------------------------------------------------------------------
 * PWNAGE-35000: acknowledge power actions immediately and let systemd run the
 * reboot/poweroff job in the background.  Running `systemctl reboot` synchronously
 * in this GTK process was the black-screen stall: systemd could not stop the
 * session (nuxel-wayland -> this host) while the host was still blocked inside
 * action_perform, so shutdown sat until a timeout.  Forking decouples the two.
 * ------------------------------------------------------------------------- */
/* Detached children (systemctl, foreign-toplevel) have no caller to wait for
 * them.  Registering them with GLib's child watcher reaps the exit status, so a
 * long session cannot accumulate one zombie per Home/power action. */
static void detached_child_exited(GPid pid, gint status, gpointer data) {
  (void)status; (void)data;
  g_spawn_close_pid(pid);
}

/* ---------------------------------------------------------------------------
 * POWER MENU: "Take screenshot".
 *
 * The hardware-button manager dispatches `action screenshot` to
 * /run/nuxel-pwa-host.cmd (chord Power+VolumeDown and the menu entry).  The host
 * used to answer `unknown-action`, so the entry and the chord did nothing.
 *
 * The capture runs nuxel-screenshot (wlr-screencopy; never opens /dev/fb0),
 * converts the PPM to a real PNG with zlib in-process, and stores the file in
 * the session user's Gallery so the Gallery app indexes it.  Nothing is claimed
 * when the capture fails: the caller gets ok:false with the reason.
 * ------------------------------------------------------------------------- */
#define SHOT_BIN "/usr/lib/nuxel/nuxel-screenshot"
#define SHOT_DIR "/home/nuxel/Gallery"

static void png_be32(unsigned char *p, uint32_t v) {
  p[0] = (unsigned char)(v >> 24); p[1] = (unsigned char)(v >> 16);
  p[2] = (unsigned char)(v >> 8);  p[3] = (unsigned char)v;
}

static int png_chunk(FILE *f, const char *type, const unsigned char *data, size_t n) {
  unsigned char hdr[8], crc[4];
  png_be32(hdr, (uint32_t)n);
  memcpy(hdr + 4, type, 4);
  uLong c = crc32(0L, Z_NULL, 0);
  c = crc32(c, (const Bytef *)type, 4);
  if (n) c = crc32(c, (const Bytef *)data, (uInt)n);
  png_be32(crc, (uint32_t)c);
  if (fwrite(hdr, 1, 8, f) != 8) return -1;
  if (n && fwrite(data, 1, n, f) != n) return -1;
  return (fwrite(crc, 1, 4, f) == 4) ? 0 : -1;
}

/* PPM (P6, 8-bit) -> PNG.  Returns 0 on success. */
static int ppm_to_png(const char *ppm_path, const char *png_path, int *out_w, int *out_h) {
  FILE *in = fopen(ppm_path, "rb");
  if (!in) return -1;
  char magic[3] = {0};
  int w = 0, h = 0, maxv = 0;
  if (fscanf(in, "%2s", magic) != 1 || strcmp(magic, "P6") ||
      fscanf(in, "%d %d %d", &w, &h, &maxv) != 3 || w <= 0 || h <= 0 || maxv != 255) {
    fclose(in);
    return -1;
  }
  int c = fgetc(in);              /* exactly one whitespace byte after maxval */
  if (c == EOF) { fclose(in); return -1; }
  size_t rowbytes = (size_t)w * 3;
  unsigned char *row = g_malloc(rowbytes + 1);
  unsigned char *raw = g_malloc((rowbytes + 1) * (size_t)h);
  if (!row || !raw) { g_free(row); g_free(raw); fclose(in); return -1; }
  for (int y = 0; y < h; y++) {
    size_t off = (rowbytes + 1) * (size_t)y;
    raw[off] = 0;                 /* filter type 0 (None) */
    if (fread(row, 1, rowbytes, in) != rowbytes) {
      g_free(row); g_free(raw); fclose(in); return -1;
    }
    memcpy(raw + off + 1, row, rowbytes);
  }
  fclose(in);
  g_free(row);

  uLongf zlen = compressBound((uLong)((rowbytes + 1) * (size_t)h));
  unsigned char *zbuf = g_malloc(zlen);
  if (!zbuf || compress2(zbuf, &zlen, raw, (uLong)((rowbytes + 1) * (size_t)h), 6) != Z_OK) {
    g_free(zbuf); g_free(raw); return -1;
  }
  g_free(raw);

  FILE *out = fopen(png_path, "wb");
  if (!out) { g_free(zbuf); return -1; }
  static const unsigned char sig[8] = {0x89, 'P', 'N', 'G', '\r', '\n', 0x1a, '\n'};
  unsigned char ihdr[13];
  png_be32(ihdr, (uint32_t)w);
  png_be32(ihdr + 4, (uint32_t)h);
  ihdr[8] = 8;   /* bit depth */
  ihdr[9] = 2;   /* colour type: truecolour */
  ihdr[10] = 0; ihdr[11] = 0; ihdr[12] = 0;
  int ok = (fwrite(sig, 1, 8, out) == 8) &&
           png_chunk(out, "IHDR", ihdr, sizeof ihdr) == 0 &&
           png_chunk(out, "IDAT", zbuf, (size_t)zlen) == 0 &&
           png_chunk(out, "IEND", NULL, 0) == 0;
  if (ok) { fflush(out); fsync(fileno(out)); }
  fclose(out);
  g_free(zbuf);
  if (!ok) { unlink(png_path); return -1; }
  *out_w = w; *out_h = h;
  return 0;
}

/* Capture the current composited frame into the Gallery.  Returns 0 on success
 * and fills `out_path`; never invents success. */
static int nuxel_capture_screenshot(char *out_path, size_t outn, int *out_w, int *out_h,
                                    char *err, size_t errn) {
  char tmpl[] = "/run/nuxel-shot-XXXXXX";
  int fd = mkstemp(tmpl);
  if (fd < 0) { snprintf(err, errn, "tempfile-failed"); return -1; }
  close(fd);
  unlink(tmpl);
  char ppm[256];
  snprintf(ppm, sizeof ppm, "%s.ppm", tmpl);
  err[0] = 0;

  pid_t pid = fork();
  if (pid < 0) { snprintf(err, errn, "fork-failed"); unlink(ppm); return -1; }
  if (pid == 0) {
    (void)setsid();
    int devnull = open("/dev/null", O_WRONLY);
    if (devnull >= 0) { dup2(devnull, 2); close(devnull); }
    execl(SHOT_BIN, "nuxel-screenshot", ppm, (char *)NULL);
    _exit(127);
  }
  int status = 0;
  for (int i = 0; i < 100; i++) {          /* bounded: 10 s max */
    pid_t r = waitpid(pid, &status, WNOHANG);
    if (r == pid) break;
    if (r < 0) break;
    usleep(100000);
    if (i == 99) { kill(pid, SIGKILL); waitpid(pid, NULL, 0); }
  }
  if (!WIFEXITED(status) || WEXITSTATUS(status) != 0) {
    snprintf(err, errn, "capture-failed rc=%d", WIFEXITED(status) ? WEXITSTATUS(status) : -1);
    unlink(ppm);
    return -1;
  }

  mkdir(SHOT_DIR, 0750);
  char stamp[32], base[32];
  struct timespec now;
  clock_gettime(CLOCK_REALTIME, &now);
  struct tm tm;
  gmtime_r(&now.tv_sec, &tm);
  strftime(base, sizeof base, "%Y%m%dT%H%M%S", &tm);
  /* Millisecond suffix: two captures in the same second must never share a
     path.  A shared path was one source of zero-byte Gallery entries. */
  snprintf(stamp, sizeof stamp, "%s%03ldZ", base, now.tv_nsec / 1000000L);
  snprintf(out_path, outn, SHOT_DIR "/nuxel-screenshot-%s.png", stamp);

  int w = 0, h = 0;
  if (ppm_to_png(ppm, out_path, &w, &h) != 0) {
    snprintf(err, errn, "convert-failed");
    unlink(ppm);
    return -1;
  }
  unlink(ppm);
  chmod(out_path, 0640);
  struct passwd *pw = getpwnam("nuxel");
  if (pw && geteuid() == 0) { if (chown(out_path, pw->pw_uid, pw->pw_gid) != 0) { /* best effort */ } }
  if (out_w) *out_w = w;
  if (out_h) *out_h = h;
  return 0;
}

/* Visible acknowledgement for actions initiated by the hardware chord (there is
 * no RPC caller to receive the JSON result).  The launcher renders this as a
 * transient, pointer-inert OSD.  Never claim success before the PNG is written. */
/* Hardware-button flashlight requests are routed to the HTTP bridge's single
 * LED owner.  This process never opens an LED node. */
static void run_async_flashlight(const char *verb) {
  gchar *argv[] = { (gchar *)"/usr/bin/nuxel-flashlight-rpc", (gchar *)verb, NULL };
  GError *err = NULL;
  if (!g_spawn_async(NULL, argv, NULL, G_SPAWN_SEARCH_PATH, NULL, NULL, NULL, &err)) {
    st("HOST_FLASHLIGHT_SPAWN_FAILED %s", err ? err->message : "unknown");
    if (err) g_error_free(err);
  }
}

static void host_toast(const char *text) {
  if (!g_main_view) return;
  char *esc = json_escape(text, strlen(text));
  GString *g = g_string_new("");
  g_string_append_printf(g,
    "window.dispatchEvent(new CustomEvent('nuxel:toast',{detail:{text:%s}}));", esc);
  webkit_web_view_evaluate_javascript(g_main_view, g->str, -1, NULL, NULL, NULL, NULL, NULL);
  g_string_free(g, TRUE);
  g_free(esc);
}

/* PWNAGE-62000: never lose a nav command because the dock FIFO was not ready
 * yet.  A short bounded retry covers the normal map race; a persistent request
 * file is consumed by nuxel-navdock on its next 500 ms tick. */
static int nav_command(const char *cmd) {
  for (int i = 0; i < 12; i++) {
    int fd = open("/run/nuxel-navdock.cmd", O_WRONLY | O_NONBLOCK);
    if (fd >= 0) {
      dprintf(fd, "%s\n", cmd);
      close(fd);
      return 0;
    }
    usleep(50000);
  }
  const char *tmp = "/run/nuxel-navdock.request.tmp";
  int fd = open(tmp, O_WRONLY | O_CREAT | O_TRUNC | O_CLOEXEC, 0600);
  if (fd < 0) return -1;
  dprintf(fd, "%s\n", cmd);
  close(fd);
  if (rename(tmp, "/run/nuxel-navdock.request") != 0) return -1;
  st("HOST_NAV_CMD_QUEUED %s", cmd);
  return 0;
}

/* The host cannot write the authoritative lock state itself (security_provider
 * is the single owner).  This fixed helper asks the loopback bridge to persist
 * the lock, so a lock request still takes effect even when the native app hides
 * the Home WebView.  Failures are non-fatal: the Home JS path remains. */
static void request_authoritative_lock(const char *reason) {
  pid_t pid = fork();
  if (pid == 0) {
    setsid();
    execl("/usr/lib/nuxel/nuxel-security-lock-rpc",
          "nuxel-security-lock-rpc", reason ? reason : "host", (char *)NULL);
    _exit(127);
  }
  if (pid > 0) g_child_watch_add(pid, detached_child_exited, NULL);
}


static void reset_web_zoom(WebKitWebView *v);
static int wlfb_command(const char *cmd);
static void publish_keyboard_visibility(int visible);

/* PWNAGE-80000: keyboard dismissal must not minimize the foreground app.  The
 * old `dismiss-keyboard` action ran `nuxel-foreign-toplevel home`, which
 * backgrounded a native app (and raised Home over a PWA) merely because the user
 * pressed Back with the OSK open.  Here we blur the WebKit focus chain first;
 * for native text-input clients the foreign-toplevel helper performs a bounded
 * focus bounce that returns to the same app instead of leaving Home on top. */
static void host_hide_keyboard(void) {
  if (g_main_view) {
    const char *js =
      "(function(){try{"
      "function blurWin(w){try{var a=w.document&&w.document.activeElement;"
      "if(a&&a.tagName==='IFRAME'){try{blurWin(a.contentWindow);}catch(e){}}"
      "if(a&&a.blur)a.blur();"
      "try{w.dispatchEvent(new CustomEvent('nuxel:dismiss-keyboard'));}catch(e){}"
      "}catch(e){}}"
      "blurWin(window);"
      "try{if(document.body&&document.body.focus)document.body.focus();}catch(e){}"
      "}catch(e){}})();";
    webkit_web_view_evaluate_javascript(g_main_view, js, -1, NULL, NULL, NULL, NULL, NULL);
  }
  pid_t pid = fork();
  if (pid == 0) {
    setsid();
    execl("/usr/lib/nuxel/nuxel-foreign-toplevel",
          "nuxel-foreign-toplevel", "hide-keyboard", (char *)NULL);
    _exit(127);
  }
  if (pid > 0) g_child_watch_add(pid, detached_child_exited, NULL);
  publish_keyboard_visibility(0);
  st("HOST_KEYBOARD_DISMISS blur=1 native_focus_bounce=1 home_raise=0");
}

/* A lifecycle transition (app close, launcher reload, lockscreen) must leave a
 * complete valid frame: pin WebKit zoom, clear the focus chain and ask the
 * framebuffer bridge for one full blit instead of waiting for a partial damage
 * region to age out.  This is a one-shot, not a repeating timer. */
static void host_after_app_close(const char *why) {
  reset_web_zoom(g_main_view);
  if (g_main_view) {
    const char *js =
      "(function(){try{"
      "if(window.NuxelZoomPolicy&&window.NuxelZoomPolicy.reset)window.NuxelZoomPolicy.reset(window);"
      "if(window.NuxelImmersive&&window.NuxelImmersive.reset)window.NuxelImmersive.reset();"
      "try{if(document.activeElement&&document.activeElement.blur)document.activeElement.blur();}catch(e){}"
      "try{window.dispatchEvent(new CustomEvent('nuxel:app-closed'));}catch(e){}"
      "try{window.dispatchEvent(new CustomEvent('nuxel:zoom-reset'));}catch(e){}"
      "}catch(e){}})();";
    webkit_web_view_evaluate_javascript(g_main_view, js, -1, NULL, NULL, NULL, NULL, NULL);
  }
  wlfb_command("repaint");
  if (g_main_window) { gtk_widget_queue_draw(g_main_window); }
  st("HOST_AFTER_APP_CLOSE why=%s zoom=1 repaint=1 focus=cleared", why ? why : "unspecified");
}

static void action_perform(const char *action, char *result, size_t rn) {
  if (!strcmp(action, "screen-lock")) {
    /* Lock is the display bridge's verb; hide the native dock first so no
       layer-shell frame can paint over the lockscreen. */
    request_authoritative_lock("host-native-screen-lock");
    nav_command("hide");
    /* The display bridge owns screen-off, not a "lock" verb.  Send the real
       verb and also drive Home's lock presentation: when a native app covers
       the WebView the DOM listener still runs in the hidden view, and the
       compositor-level lock watcher then keeps Home above every app. */
    int fd = open("/run/nuxel-wl-fb.cmd", O_WRONLY | O_NONBLOCK);
    if (fd >= 0) {
      dprintf(fd, "screen-off\n");
      close(fd);
    }
    if (g_main_view) {
      const char *js =
        "window.dispatchEvent(new CustomEvent('nuxel:action',"
        "{detail:{action:'lock'}}));";
      webkit_web_view_evaluate_javascript(g_main_view, js, -1, NULL, NULL,
                                          NULL, NULL, NULL);
    }
    st("HOST_ACTION screen-lock -> host lockscreen + nuxel-wl-fb screen-off");
    snprintf(result, rn, "{\"ok\":true,\"action\":\"screen-lock\"}");
    return;
  }
  if (!strcmp(action, "flashlight")) {
    run_async_flashlight("toggle");
    snprintf(result, rn, "{\"ok\":true,\"action\":\"flashlight\",\"pending\":true}");
    return;
  }
  if (!strcmp(action, "screenshot") || !strcmp(action, "take-screenshot")) {
    char path[512], err[128];
    int w = 0, h = 0;
    if (nuxel_capture_screenshot(path, sizeof path, &w, &h, err, sizeof err) != 0) {
      st("HOST_SCREENSHOT_FAILED %s", err);
      char msg[192];
      snprintf(msg, sizeof msg, "Screenshot failed: %s", err);
      host_toast(msg);
      snprintf(result, rn, "{\"ok\":false,\"error\":\"screenshot-failed\",\"reason\":\"%s\"}", err);
      return;
    }
    st("HOST_SCREENSHOT_SAVED path=%s %dx%d", path, w, h);
    host_toast("Screenshot saved to Gallery");
    snprintf(result, rn, "{\"ok\":true,\"action\":\"screenshot\",\"path\":\"%s\",\"width\":%d,\"height\":%d}", path, w, h);
    return;
  }
  if (!strcmp(action, "suspend") || !strcmp(action, "systemctl-suspend")) {
    int fd = open("/run/nuxel-buttons.cmd", O_WRONLY | O_NONBLOCK);
    if (fd < 0) { snprintf(result, rn, "{\"ok\":false,\"error\":\"button-fifo-absent\"}"); return; }
    dprintf(fd, "action systemctl-suspend\n");
    close(fd);
    st("HOST_ACTION systemctl-suspend -> button manager fifo");
    snprintf(result, rn, "{\"ok\":true,\"action\":\"systemctl-suspend\",\"pending\":true}");
    return;
  }
  if (!strcmp(action, "restart") || !strcmp(action, "poweroff")) {
    /* PWNAGE-80000: the Settings power surface and any host caller go through
     * the SAME gate and the SAME timestamped execution path as the hardware
     * power menu.  A direct systemctl call here bypassed the cooldown/policy
     * checks and made the menu look intermittently gated.  The manager owns
     * the result and logs REBOOT_ALLOWED/REFUSED plus the request timestamps. */
    int fd = open("/run/nuxel-buttons.cmd", O_WRONLY | O_NONBLOCK);
    if (fd < 0) {
      snprintf(result, rn, "{\"ok\":false,\"error\":\"button-fifo-absent\"}");
      return;
    }
    dprintf(fd, "action %s\n", !strcmp(action, "restart") ? "systemctl-reboot" : "systemctl-poweroff");
    close(fd);
    st("HOST_ACTION %s -> button-manager gate (request queued)", action);
    snprintf(result, rn, "{\"ok\":true,\"action\":\"%s\",\"pending\":true,\"backend\":\"button-manager-gate\"}", action);
    return;
  }
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
  /* PWNAGE-80000: a pure keyboard dismissal never raises Home or backgrounds
   * the foreground app.  Home itself still performs the authoritative
   * foreign-toplevel Home transition below. */
  if (!strcmp(action, "dismiss-keyboard") || !strcmp(action, "hide-keyboard")) {
    host_hide_keyboard();
    snprintf(result, rn, "{\"ok\":true,\"action\":\"hide-keyboard\"}");
    return;
  }
  /* Root-console test hooks.  They can only resolve a local app id or a DOM
   * id/selector-shaped token, never arbitrary JavaScript.  They exist so the
   * four-orientation/acceptance matrix can be driven from the SSH console when
   * the physical panel is not in reach, and they use the same launcher/app
   * functions as a real tap. */
  if (!strncmp(action, "launch-app ", 11)) {
    const char *id = action + 11;
    int ok = *id != 0;
    for (const char *p = id; *p; p++) {
      if (!(isalnum((unsigned char)*p) || *p == '.' || *p == '-' || *p == '_')) { ok = 0; break; }
    }
    if (ok && g_main_view) {
      char js[256];
      snprintf(js, sizeof js,
        "try{window.appRegistry&&window.appRegistry.launchApp('%s');}catch(e){}", id);
      webkit_web_view_evaluate_javascript(g_main_view, js, -1, NULL, NULL, NULL, NULL, NULL);
      st("HOST_UI_LAUNCH app_id=%s", id);
      snprintf(result, rn, "{\"ok\":true,\"action\":\"launch-app\",\"app_id\":\"%s\"}", id);
    } else {
      snprintf(result, rn, "{\"ok\":false,\"error\":\"invalid_app_id\"}");
    }
    return;
  }
  if (!strncmp(action, "ui-swipe ", 9)) {
    /* Bounded acceptance hook: dispatch the same pointer sequence a finger
     * produces on one Recents card.  It is not a general evaluator: the id must
     * exist in the launcher document and the direction is one of left/right. */
    char swipe_id[160] = "", dir[16] = "";
    if (sscanf(action + 9, "%159s %15s", swipe_id, dir) == 2) {
      int valid = (*swipe_id != 0) && (!strcmp(dir, "left") || !strcmp(dir, "right"));
      for (const char *p = swipe_id; valid && *p; p++) {
        if (!(isalnum((unsigned char)*p) || *p == '.' || *p == '-' || *p == '_' || *p == ':')) valid = 0;
      }
      if (valid && g_main_view) {
        char js[2600];
        snprintf(js, sizeof js,
          "(function(){try{var id='%s',dir='%s';var e=document.getElementById(id);"
          "if(!e||!e.getBoundingClientRect)return;var r=e.getBoundingClientRect();"
          "var x=r.left+r.width/2,y=r.top+r.height/2,d=(dir==='right'?110:-110);"
          "function pe(t,cx){try{return new PointerEvent(t,{bubbles:true,cancelable:true,composed:true,pointerId:7,pointerType:'touch',isPrimary:true,button:0,buttons:t==='pointerup'?0:1,clientX:cx,clientY:y});}"
          "catch(q){return new MouseEvent(t,{bubbles:true,cancelable:true,clientX:cx,clientY:y,button:0});}}"
          "e.dispatchEvent(pe('pointerdown',x));e.dispatchEvent(pe('pointermove',x+d/2));"
          "e.dispatchEvent(pe('pointermove',x+d));e.dispatchEvent(pe('pointerup',x+d));"
          "try{window.webkit.messageHandlers.nuxelDiag.postMessage('UI_SWIPE id='+id+' dir='+dir);}catch(q){}"
          "}catch(e){try{window.webkit.messageHandlers.nuxelDiag.postMessage('UI_SWIPE_ERROR '+e);}catch(q){}}})();",
          swipe_id, dir);
        webkit_web_view_evaluate_javascript(g_main_view, js, -1, NULL, NULL, NULL, NULL, NULL);
        st("HOST_UI_SWIPE id=%s dir=%s", swipe_id, dir);
        snprintf(result, rn, "{\"ok\":true,\"action\":\"ui-swipe\",\"id\":\"%s\",\"dir\":\"%s\"}", swipe_id, dir);
      } else {
        snprintf(result, rn, "{\"ok\":false,\"error\":\"invalid_swipe_target\"}");
      }
    } else {
      snprintf(result, rn, "{\"ok\":false,\"error\":\"invalid_swipe_args\"}");
    }
    return;
  }
  if (!strncmp(action, "ui-focus ", 9) || !strncmp(action, "ui-click ", 9)) {
    const char *id = action + 9;
    int ok = *id != 0;
    for (const char *p = id; *p; p++) {
      if (!(isalnum((unsigned char)*p) || *p == '.' || *p == '-' || *p == '_' || *p == ':')) { ok = 0; break; }
    }
    if (ok && g_main_view) {
      char js[1024];
      snprintf(js, sizeof js,
        "(function(){try{function w(x){try{var e=x.document.getElementById('%s');"
        "if(e){try{e.focus();}catch(q){}try{e.click();}catch(q){}"
        "try{x.webkit.messageHandlers.nuxelDiag.postMessage('UI_FOCUS id=%s result=ok');}catch(q){}"
        "return true;}var f=x.document.querySelectorAll('iframe');"
        "for(var i=0;i<f.length;i++){if(w(f[i].contentWindow))return true;}"
        "}catch(q){}return false;}return w(window);}catch(e){}})();", id, id);
      webkit_web_view_evaluate_javascript(g_main_view, js, -1, NULL, NULL, NULL, NULL, NULL);
      st("HOST_UI_FOCUS id=%s", id);
      snprintf(result, rn, "{\"ok\":true,\"action\":\"ui-focus\",\"id\":\"%s\"}", id);
    } else {
      snprintf(result, rn, "{\"ok\":false,\"error\":\"invalid_element_id\"}");
    }
    return;
  }
  if (!strcmp(action, "diag-ui")) {
    if (g_main_view) {
      const char *js =
        "try{var l=window.launcher||{};var d=document.getElementById('drawer-list');"
        "window.webkit.messageHandlers.nuxelDiag.postMessage('UI '+JSON.stringify({"
        "drawerOpen:!!l.drawerOpen,drawerHidden:d?d.hidden:null,drawerChildren:d?d.children.length:null,"
        "bodyClass:String(document.body.className),appState:document.body.dataset.appState,"
        "session:(window.nuxel&&window.nuxel.appSession&&window.nuxel.appSession.state)||null,"
        "grid:!!document.getElementById('app-grid'),dock:!!document.getElementById('dock'),"
        "drawerDisplay:d?getComputedStyle(d).display:null,drawerVis:d?getComputedStyle(d).visibility:null,"
        "drawerOpacity:d?getComputedStyle(d).opacity:null,drawerZ:d?getComputedStyle(d).zIndex:null,"
        "drawerRect:d?{x:d.getBoundingClientRect().x,y:d.getBoundingClientRect().y,w:d.getBoundingClientRect().width,h:d.getBoundingClientRect().height}:null,"
        "drawerCols:d?getComputedStyle(d).gridTemplateColumns:null,"
        "drawerScroll:d?{w:d.scrollWidth,h:d.scrollHeight,cw:d.clientWidth,ch:d.clientHeight,left:d.scrollLeft,top:d.scrollTop}:null,"
        "drawerItems:d?(function(){var q=d.querySelectorAll('.app-item');var a=q[0],b=q[q.length-1];var rr=function(e){if(!e)return null;var r=e.getBoundingClientRect();return {x:r.x,y:r.y,w:r.width,h:r.height,right:r.right,bottom:r.bottom};};return {count:q.length,first:rr(a),last:rr(b)};})():null,"
        "drawerVar:d?getComputedStyle(document.documentElement).getPropertyValue('--drawer-columns'):null,"
        "homeVar:getComputedStyle(document.documentElement).getPropertyValue('--home-columns'),"
        "visualViewport:window.visualViewport?{w:window.visualViewport.width,h:window.visualViewport.height,scale:window.visualViewport.scale,offsetX:window.visualViewport.offsetLeft,offsetY:window.visualViewport.offsetTop}:null,"
        "docScroll:{w:document.documentElement.scrollWidth,h:document.documentElement.scrollHeight},"
        "gridDisplay:document.getElementById('app-grid')?getComputedStyle(document.getElementById('app-grid')).display:null,"
        "appListHidden:document.querySelector('.app-list:not(.drawer-list)')?document.querySelector('.app-list:not(.drawer-list)').hidden:null,"
        "lockEl:!!document.getElementById('lockscreen'),lockHidden:document.getElementById('lockscreen')?document.getElementById('lockscreen').hidden:null,"
        "lockDisplay:document.getElementById('lockscreen')?getComputedStyle(document.getElementById('lockscreen')).display:null,"
        "lockClass:document.getElementById('lockscreen')?String(document.getElementById('lockscreen').className):null,"
        "docClass:String(document.documentElement.className),hidden:document.hidden,visibility:document.visibilityState,hasFocus:document.hasFocus(),"
        "appId:(window.nuxel&&window.nuxel.appSession&&window.nuxel.appSession.app&&window.nuxel.appSession.app.id)||null,"
        "cal:(function(){try{var f=Array.from(document.querySelectorAll('iframe')).find(function(x){return /calendar/.test(x.src||'');});if(!f||!f.contentDocument)return null;var d=f.contentDocument;var g=function(id){return d.getElementById(id);};var cs=function(e){return e?getComputedStyle(e):null;};var ed=g('event-editor'),kp=g('time-keypad'),st=g('event-start'),ad=g('event-all-day');var ca=d.defaultView.nuxelCalendar&&d.defaultView.nuxelCalendar.app?d.defaultView.nuxelCalendar.app():null;return {editorHidden:ed?ed.hidden:null,editorClass:ed?ed.className:null,editorDisplay:ed?cs(ed).display:null,keypadHidden:kp?kp.hidden:null,keypadClass:kp?kp.className:null,keypadDisplay:kp?cs(kp).display:null,start:st?st.value:null,startDisabled:st?st.disabled:null,allDay:ad?ad.checked:null,active:(d.activeElement&&d.activeElement.id)||'',app:!!ca,bound:ca?ca.bound:null,events:ca&&ca.events?ca.events.length:null,gridChildren:g('day-grid')?g('day-grid').children.length:null,keypadRect:kp?{x:kp.getBoundingClientRect().x,y:kp.getBoundingClientRect().y,w:kp.getBoundingClientRect().width,h:kp.getBoundingClientRect().height}:null};}catch(e){return 'ERR '+e;}})(),"
        "overlays:{frames:document.querySelectorAll('.pwa-frame').length,iframes:document.querySelectorAll('iframe').length,powerMenus:document.querySelectorAll('#nuxel-power-menu').length,osd:document.querySelectorAll('#nuxel-osd').length,folderSheets:document.querySelectorAll('.folder-sheet').length},"
        "frame:(function(){try{var f=Array.from(document.querySelectorAll('.pwa-frame')).find(function(x){return !x.hidden;});if(!f)return null;var w=f.contentWindow;return {src:String(f.src||''),navDepth:f.__nuxelNavDepth||0,historyLength:w.history?w.history.length:null,hasNavigation:!!w.navigation,navigationCanGoBack:(w.navigation&&typeof w.navigation.canGoBack==='boolean')?w.navigation.canGoBack:null,explicitBack:!!(w.NuxelBack&&w.NuxelBack.canGoBack),canGoBack:!!(w.NuxelBack&&w.NuxelBack.canGoBack&&w.NuxelBack.canGoBack())};}catch(e){return 'ERR '+e;}})(),"
        "innerWidth:window.innerWidth,innerHeight:window.innerHeight,dpr:window.devicePixelRatio}));"
        "}catch(e){try{window.webkit.messageHandlers.nuxelDiag.postMessage('UI_ERROR '+e);}catch(x){}}";
      webkit_web_view_evaluate_javascript(g_main_view, js, -1, NULL, NULL, NULL, NULL, NULL);
    }
    snprintf(result, rn, "{\"ok\":true,\"action\":\"diag-ui\"}");
    return;
  }
  if (!strcmp(action, "reset-zoom")) {
    reset_web_zoom(g_main_view);
    wlfb_command("repaint");
    snprintf(result, rn, "{\"ok\":true,\"action\":\"reset-zoom\",\"zoom\":1.0}");
    return;
  }
  if (!strcmp(action, "force-redraw") || !strcmp(action, "after-app-close")) {
    host_after_app_close(action);
    snprintf(result, rn, "{\"ok\":true,\"action\":\"%s\",\"repaint\":true}", action);
    return;
  }
  if (!strcmp(action, "home")) {
    pid_t pid = fork();
    if (pid == 0) {
      setsid();
      execl("/usr/lib/nuxel/nuxel-foreign-toplevel",
            "nuxel-foreign-toplevel", "home", (char *)NULL);
      _exit(127);
    }
    if (pid > 0) g_child_watch_add(pid, detached_child_exited, NULL);
    if (g_main_window) gtk_window_present(GTK_WINDOW(g_main_window));
    st("HOST_ACTION home -> foreign-toplevel home + raise");
  }
  if (!strcmp(action, "nav-hide") || !strcmp(action, "nav-show")) {
    const char *cmd = !strcmp(action, "nav-show") ? "show" : "hide";
    if (nav_command(cmd) != 0) {
      snprintf(result, rn, "{\"ok\":false,\"error\":\"navdock-command-unavailable\"}");
      return;
    }
    st("HOST_ACTION %s -> navdock (fifo or queued request)", action);
    snprintf(result, rn, "{\"ok\":true,\"action\":\"%s\",\"queued\":false}", action);
    return;
  }
  if (!strcmp(action, "home") || !strcmp(action, "back") || !strcmp(action, "back-long") || !strcmp(action, "forward") ||
      !strcmp(action, "stop") || !strcmp(action, "reload-launcher") ||
      !strcmp(action, "search") || !strcmp(action, "settings") ||
      !strcmp(action, "recents") || !strcmp(action, "all-apps") ||
      !strcmp(action, "notifications-panel") ||
      !strcmp(action, "lock") || !strcmp(action, "unlock")) {
    /* A native terminal window is a separate top-level surface: the launcher's
     * DOM `home` event cannot dismiss it.  Home/back must close it here, or the
     * fullscreen terminal stays in front of Home (the A34 owner-test symptom). */
    if (!strcmp(action, "home")) term_close_window();
    /* Hide the native dock BEFORE any launcher transition that can reveal the
       lockscreen.  Unlock is different: Home maps the dock only after the
       authoritative unlock and Home transition, so the host does not show it. */
    if (!strcmp(action, "lock")) nav_command("hide");
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
                              !strcmp(action, "all-apps") ? "'all-apps'" :
                              !strcmp(action, "notifications-panel") ? "'notifications-panel'" :
                              !strcmp(action, "lock") ? "'lock'" : "'unlock'";
      g_string_append_printf(g,
        "window.dispatchEvent(new CustomEvent('nuxel:action',{detail:{action:%s}}));", js_action);
      webkit_web_view_evaluate_javascript(g_main_view, g->str, -1, NULL, NULL, NULL, NULL, NULL);
      g_string_free(g, TRUE);
    }
    if (!strcmp(action, "unlock")) {
      /* Deliberately do NOT map the dock here.  _unlock() queues nav-show
         after the lockscreen hide and Home transition; that is the only path
         allowed to restore the native dock. */
      st("HOST_ACTION unlock -> launcher page (dock restore deferred to Home)");
    } else {
      st("HOST_ACTION %s -> launcher page", action);
    }
    snprintf(result, rn, "{\"ok\":true,\"action\":\"%s\"}", action);
    return;
  }
  st("HOST_ACTION_REFUSED %s", action);
  snprintf(result, rn, "{\"ok\":false,\"error\":\"unknown-action\"}");
}

static gint64 g_mic_grant_until_us;

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
    /* Successful status reads are not events.  Logging every 2 s made the
     * diagnostics file a write amplifier; failures still log above. */
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
  if (!strcmp(method, "media.mic-authorize")) {
    /* Trusted-origin gate is evaluated by WebKit before this handler is
       reached.  Grant is deliberately short (15 s) and consumed once. */
    g_mic_grant_until_us = g_get_monotonic_time() + 15 * G_TIME_SPAN_SECOND;
    host_reply(v, id, 1, "{\"ok\":true,\"grant\":\"audio-once\",\"ttl_ms\":15000}");
    st("HOST_MEDIA_MIC_AUTHORIZE ttl_ms=15000");
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
  /* Power surface: the console tool is the single implementation.  The host only
   * runs it with a VALIDATED profile name and returns its real output, so the
   * Settings surface can never disagree with `nuxel-power-diag.sh`. */
  if (!strcmp(method, "power.status")) {
    FILE *pf = popen("/usr/local/bin/nuxel-power-diag.sh status --json 2>/dev/null", "r");
    char sbuf[4096];
    size_t sn = 0;
    if (pf) { sn = fread(sbuf, 1, sizeof sbuf - 1, pf); pclose(pf); }
    sbuf[sn] = 0;
    while (sn && (sbuf[sn-1] == '\n' || sbuf[sn-1] == '\r' || sbuf[sn-1] == ' ')) sbuf[--sn] = 0;
    if (!sn || sbuf[0] != '{') {
      host_reply(v, id, 0, "{\"error\":\"power-status-unavailable\"}");
      st("HOST_POWER_STATUS unavailable");
      g_free(js);
      return;
    }
    host_reply(v, id, 1, sbuf);
    st("HOST_POWER_STATUS ok bytes=%zu", sn);
    g_free(js);
    return;
  }
  if (!strcmp(method, "power.apply-profile")) {
    char mode[32] = "";
    json_str(js, "mode", mode, sizeof mode);
    /* Validate against the shipped document: adaptive|balanced|performance only. */
    int okmode = 0;
    FILE *mf = fopen("/etc/nuxel/power/power.json", "rb");
    if (mf) {
      char mbuf[8192];
      size_t mn = fread(mbuf, 1, sizeof mbuf - 1, mf);
      fclose(mf);
      mbuf[mn] = 0;
      char pat[64];
      snprintf(pat, sizeof pat, "\"%s\": {", mode);
      okmode = mode[0] && strstr(mbuf, pat) != NULL;
    }
    if (!okmode) {
      host_reply(v, id, 0, "{\"ok\":false,\"error\":\"unknown-profile\"}");
      st("HOST_POWER_PROFILE_REFUSED mode=%s", mode);
      g_free(js);
      return;
    }
    char cmdline[256];
    snprintf(cmdline, sizeof cmdline,
             "/usr/local/bin/nuxel-power-diag.sh mode %s >/dev/null 2>&1", mode);
    int rc = system(cmdline);
    /* Read the persisted profile back instead of claiming success. */
    char applied[64] = "";
    FILE *af = fopen("/var/lib/nuxel/power/profile.json", "rb");
    if (af) {
      char abuf[1024];
      size_t an = fread(abuf, 1, sizeof abuf - 1, af);
      fclose(af);
      abuf[an] = 0;
      char *pp = strstr(abuf, "\"profile\"");
      if (pp) {
        char *q = strchr(pp, ':');
        if (q) {
          q++;
          while (*q == ' ' || *q == '\t') q++;
          if (*q == '"') {
            q++;
            size_t i = 0;
            while (*q && *q != '"' && i + 1 < sizeof applied) applied[i++] = *q++;
            applied[i] = 0;
          }
        }
      }
    }
    if (rc == 0 && !strcmp(applied, mode)) {
      GString *out = g_string_new("");
      g_string_append_printf(out, "{\"ok\":true,\"mode\":\"%s\",\"persisted\":true}", mode);
      host_reply(v, id, 1, out->str);
      g_string_free(out, TRUE);
      st("HOST_POWER_PROFILE mode=%s persisted=1", mode);
    } else {
      GString *out = g_string_new("");
      g_string_append_printf(out,
        "{\"ok\":false,\"error\":\"profile-not-applied\",\"mode\":\"%s\",\"readback\":\"%s\",\"rc\":%d}",
        mode, applied, rc);
      host_reply(v, id, 0, out->str);
      g_string_free(out, TRUE);
      st("HOST_POWER_PROFILE mode=%s persisted=0 rc=%d readback=%s", mode, rc, applied);
    }
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


/* ---------------------------------------------------------------------------
 * PWNAGE-80000 CENTRAL ZOOM POLICY
 *
 * Default deny in every frame.  This user script is injected into ALL frames
 * (not just the top document) before any app script runs.  It is one layer of
 * defence in depth with the WebKitSettings/WebView pinning and the GTK gesture
 * capture-denial installed in view_new().  It never intercepts one-finger
 * scrolling, dragging, selection or app controls.
 * ------------------------------------------------------------------------- */
static const char *ZOOM_POLICY_JS =
  "(function(){try{"
  "if(window.__nuxelZoomPolicy80000)return;window.__nuxelZoomPolicy80000=1;"
  "var allow=function(){try{return !!(window.NuxelZoomPolicy&&window.NuxelZoomPolicy.allowed&&window.NuxelZoomPolicy.allowed(window.NuxelZoomPolicy.appId));}catch(e){return false;}};"
  "var stop=function(e){try{if(e.cancelable)e.preventDefault();}catch(x){}try{e.stopPropagation();}catch(x){}return false;};"
  "['gesturestart','gesturechange','gestureend'].forEach(function(n){document.addEventListener(n,function(e){if(!allow())stop(e);},{capture:true,passive:false});});"
  "document.addEventListener('wheel',function(e){if((e.ctrlKey||e.metaKey)&&!allow())stop(e);},{capture:true,passive:false});"
  "document.addEventListener('keydown',function(e){if(!(e.ctrlKey||e.metaKey)||allow())return;if(e.key==='+'||e.key==='='||e.key==='-'||e.key==='_'||e.key==='0')stop(e);},{capture:true,passive:false});"
  "var multi=function(e){if(!allow()&&e.touches&&e.touches.length>1)stop(e);};"
  "document.addEventListener('touchstart',multi,{capture:true,passive:false});"
  "document.addEventListener('touchmove',multi,{capture:true,passive:false});"
  "window.addEventListener('nuxel:zoom-reset',function(){try{window.scrollTo(window.scrollX||0,window.scrollY||0);}catch(e){}});"
  "}catch(e){}})();";

/* Focus observation is the only way the native shell can know the virtual
 * keyboard is on-screen without guessing a keyboard rectangle.  It is
 * deliberately limited to a boolean and never records field values. */
static const char *KEYBOARD_FOCUS_JS =
  "(function(){try{"
  "if(window.__nuxelFocusObs80000)return;window.__nuxelFocusObs80000=1;"
  "var post=function(on){try{window.webkit.messageHandlers.nuxelKeyboard.postMessage(on?'1':'0');}catch(e){}};"
  "var editable=function(el){try{return !!(el&&(el.isContentEditable||/^(INPUT|TEXTAREA|SELECT)$/.test(el.tagName||'')));}catch(e){return false;}};"
  "document.addEventListener('focusin',function(e){if(editable(e.target))post(1);},true);"
  "document.addEventListener('focusout',function(){setTimeout(function(){post(editable(document.activeElement)?1:0);},80);},true);"
  "window.addEventListener('nuxel:dismiss-keyboard',function(){try{if(document.activeElement&&document.activeElement.blur)document.activeElement.blur();}catch(e){}post(0);});"
  "}catch(e){}})();";

static void publish_keyboard_visibility(int visible) {
  int fd = open("/run/nuxel-keyboard.visible", O_WRONLY | O_CREAT | O_TRUNC, 0644);
  if (fd >= 0) { dprintf(fd, "%d\n", visible); close(fd); }
  if (g_main_view) {
    char js[192];
    snprintf(js, sizeof js,
      "window.__nuxelHostEvent&&window.__nuxelHostEvent('keyboard-visible',{visible:%d});",
      visible ? 1 : 0);
    webkit_web_view_evaluate_javascript(g_main_view, js, -1, NULL, NULL, NULL, NULL, NULL);
  }
  st("NUXEL_KEYBOARD_VISIBLE %d", visible);
}

static void on_keyboard_message(WebKitUserContentManager *m, WebKitJavascriptResult *r, gpointer d) {
  (void)m; (void)d;
  JSCValue *v = webkit_javascript_result_get_js_value(r);
  char *s = v ? jsc_value_to_string(v) : NULL;
  int visible = s && s[0] == '1';
  publish_keyboard_visibility(visible);
  if (s) g_free(s);
}

/* Pin both WebKit zoom mechanisms.  WebKitGTK 2.54 exposes `magnification`
 * (pinch page scale) and `zoom-level` (page zoom); neither alone is enough. */
static int zoom_guard_active;
static void reset_web_zoom(WebKitWebView *v) {
  if (!v || zoom_guard_active) return;
  zoom_guard_active = 1;
  GObjectClass *c = G_OBJECT_GET_CLASS(v);
  if (g_object_class_find_property(c, "magnification"))
    g_object_set(v, "magnification", 1.0, NULL);
  if (g_object_class_find_property(c, "zoom-level"))
    g_object_set(v, "zoom-level", 1.0, NULL);
  zoom_guard_active = 0;
}
static void on_web_zoom_changed(GObject *o, GParamSpec *pspec, gpointer d) {
  (void)pspec; (void)d;
  if (zoom_guard_active) return;
  gdouble m = 1.0, z = 1.0;
  GObjectClass *c = G_OBJECT_GET_CLASS(o);
  if (g_object_class_find_property(c, "magnification")) g_object_get(o, "magnification", &m, NULL);
  if (g_object_class_find_property(c, "zoom-level")) g_object_get(o, "zoom-level", &z, NULL);
  if (m != 1.0 || z != 1.0) {
    st("NUXEL_ZOOM_RESET magnification=%.4f zoom=%.4f", m, z);
    reset_web_zoom(WEBKIT_WEB_VIEW(o));
  }
}
static void deny_gesture_begin(GtkGesture *g, GdkEventSequence *seq, gpointer d) {
  (void)seq; (void)d;
  gtk_gesture_set_state(g, GTK_EVENT_SEQUENCE_DENIED);
}
static void deny_gesture_scale(GtkGestureZoom *g, gdouble scale, gpointer d) {
  (void)scale; (void)d;
  gtk_gesture_set_state(GTK_GESTURE(g), GTK_EVENT_SEQUENCE_DENIED);
}
static void deny_multipress(GtkGestureMultiPress *g, gint n_press, gdouble x, gdouble y, gpointer d) {
  (void)x; (void)y; (void)d;
  /* Only the second (and later) press is denied.  A single tap must pass
   * through to the page untouched. */
  if (n_press >= 2) gtk_gesture_set_state(GTK_GESTURE(g), GTK_EVENT_SEQUENCE_DENIED);
}
static gboolean on_ctrl_scroll(GtkWidget *w, GdkEventScroll *ev, gpointer d) {
  (void)w; (void)d;
  if (!ev) return FALSE;
  return (ev->state & (GDK_CONTROL_MASK | GDK_MOD1_MASK)) ? TRUE : FALSE;
}
static void install_zoom_guards(WebKitWebView *v) {
  reset_web_zoom(v);
  g_signal_connect(v, "notify::magnification", G_CALLBACK(on_web_zoom_changed), NULL);
  g_signal_connect(v, "notify::zoom-level", G_CALLBACK(on_web_zoom_changed), NULL);

  GtkGesture *pinch = gtk_gesture_zoom_new(GTK_WIDGET(v));
  gtk_event_controller_set_propagation_phase(GTK_EVENT_CONTROLLER(pinch), GTK_PHASE_CAPTURE);
  g_signal_connect(pinch, "begin", G_CALLBACK(deny_gesture_begin), NULL);
  g_signal_connect(pinch, "scale-changed", G_CALLBACK(deny_gesture_scale), NULL);

  GtkGesture *dbl = gtk_gesture_multi_press_new(GTK_WIDGET(v));
  gtk_event_controller_set_propagation_phase(GTK_EVENT_CONTROLLER(dbl), GTK_PHASE_CAPTURE);
  g_signal_connect(dbl, "pressed", G_CALLBACK(deny_multipress), NULL);
  g_signal_connect(v, "scroll-event", G_CALLBACK(on_ctrl_scroll), NULL);
  st("NUXEL_ZOOM_GUARD installed=1 default=deny magnification=1 zoom=1 gestures=denied");
}

static int wlfb_command(const char *cmd) {
  int fd = open("/run/nuxel-wl-fb.cmd", O_WRONLY | O_NONBLOCK);
  if (fd < 0) return -1;
  dprintf(fd, "%s\n", cmd);
  close(fd);
  return 0;
}

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

/* Permission policy: deny by default, allow only from the trusted local
 * origin, and only capabilities with a real backend.  Notifications are used by
 * the launcher.  Audio capture is allowed only for the local Recorder page,
 * whose ALSA/PipeWire route is verified by the Bridge before getUserMedia.  The
 * S10+ camera remains denied because its vendor capture graph is unavailable.
 * Every request and decision is written to the state file. */
/* The recorder app runs inside the launcher iframe, so WebKitWebView's URI is
 * the launcher URL rather than /pwa/nuxel-apps/recorder/.  WebKitGTK 4.1 does
 * not expose the requesting frame origin on WebKitUserMediaPermissionRequest.
 * The recorder therefore asks the host for a one-shot, short-lived microphone
 * authorization immediately before getUserMedia.  Only the trusted local
 * launcher can send nuxelHost messages, and the grant is consumed by one
 * permission request, so an arbitrary remote origin still cannot capture. */

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
    /* PWNAGE-33000: the Recorder is a real getUserMedia capture client.  Allow
       audio only, only from the local recorder page.  Video/camera remains
       denied because the camera backend is explicitly deferred. */
    gboolean audio = webkit_user_media_permission_is_for_audio_device(
        WEBKIT_USER_MEDIA_PERMISSION_REQUEST(r));
    gboolean video = webkit_user_media_permission_is_for_video_device(
        WEBKIT_USER_MEDIA_PERMISSION_REQUEST(r));
    /* WebKit 2.54 can report only the requested device class through this
       permission object.  The recorder page never asks for video, so an audio
       device or an audio-only request from that exact page is allowed. */
    gboolean recorder_page = uri &&
        (g_strstr_len(uri, -1, "/pwa/nuxel-apps/recorder/") != NULL);
    gboolean host_grant = g_mic_grant_until_us > g_get_monotonic_time();
    if (!video && (recorder_page || host_grant)) {
      allow = TRUE;
      if (host_grant) g_mic_grant_until_us = 0;  /* one-shot */
      reason = audio ? (host_grant ? "allowed-microphone-host-grant" :
                                    "allowed-microphone-recorder") :
                       "allowed-microphone-recorder-media-object";
    } else if (video) {
      reason = "denied-camera-backend-deferred";
    } else {
      reason = "denied-microphone-not-recorder";
    }
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
  /* Input diagnostics are an opt-in engineering tool.  They were opt-out and
   * injected five document-level listeners plus per-move elementFromPoint()
   * work into every tap on the shipping phone.  That is observer cost on the
   * exact path we are trying to make immediate, and it never changes UI state. */
  const char *diag_env = getenv("NUXEL_INPUT_DIAG");
  gboolean diag = (diag_env && diag_env[0] == '1');
  st("NUXEL_HOME_MEDIA enable_media=%d audio_sink=%d", media ? 1 : 0, media ? 1 : 0);
  WebKitSettings *s = webkit_settings_new_with_settings(
      "enable-javascript", TRUE,
      "enable-dns-prefetching", FALSE,
      "enable-developer-extras", FALSE,
      "javascript-can-open-windows-automatically", TRUE,
      "enable-media", media,
      "enable-media-stream", TRUE,
      "enable-mediasource", media,
      "enable-back-forward-navigation-gestures", FALSE,
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
    st("NUXEL_INPUT_DIAG enabled=1 (explicit NUXEL_INPUT_DIAG=1; launcher source unmodified)");
  } else {
    st("NUXEL_INPUT_DIAG disabled=1 (set NUXEL_INPUT_DIAG=1 to enable)");
  }
  /* PWNAGE-80000: the centralized zoom policy and keyboard-focus observer are
   * injected into EVERY frame (apps live in same-origin iframes, and popups are
   * separate WebKit views).  They run before app script and cannot be removed by
   * the page.  This is additive to the native GTK gesture denial below. */
  {
    WebKitUserScript *zs = webkit_user_script_new(ZOOM_POLICY_JS,
        WEBKIT_USER_CONTENT_INJECT_ALL_FRAMES,
        WEBKIT_USER_SCRIPT_INJECT_AT_DOCUMENT_START, NULL, NULL);
    webkit_user_content_manager_add_script(ucm, zs);
    webkit_user_script_unref(zs);
    WebKitUserScript *ks = webkit_user_script_new(KEYBOARD_FOCUS_JS,
        WEBKIT_USER_CONTENT_INJECT_ALL_FRAMES,
        WEBKIT_USER_SCRIPT_INJECT_AT_DOCUMENT_START, NULL, NULL);
    webkit_user_content_manager_add_script(ucm, ks);
    webkit_user_script_unref(ks);
    webkit_user_content_manager_register_script_message_handler(ucm, "nuxelKeyboard");
    g_signal_connect(ucm, "script-message-received::nuxelKeyboard",
                     G_CALLBACK(on_keyboard_message), NULL);
    st("NUXEL_ZOOM_POLICY injected=all-frames default=deny");
  }
  keyring_secret_load();
  keyring_mint_attach(ucm);
  WebKitWebView *v = WEBKIT_WEB_VIEW(
      webkit_web_view_new_with_user_content_manager(ucm));
  webkit_web_view_set_settings(v, s);
  install_zoom_guards(v);            /* PWNAGE-80000: deny pinch/double-tap/Ctrl+wheel */
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
    /* The active server layout is /pwa/nuxel-home.  The flat
     * /nuxel-home copy exists only as a legacy fallback, so it must not decide
     * the cache-busting stamp for the page actually loaded. */
    if (stat("/usr/share/nuxel/pwa/nuxel-home/index.html", &sb) != 0)
      (void)stat("/usr/share/nuxel/nuxel-home/index.html", &sb);
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
