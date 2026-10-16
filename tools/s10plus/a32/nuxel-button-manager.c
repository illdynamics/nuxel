/* nuxel-button-manager — the S10+ physical buttons as PHONE buttons (A32)
 *
 * WHY THIS EXISTS (mission 10-13)
 *   On the handset the buttons are one evdev device, "gpio_keys" (measured:
 *   /proc/bus/input/devices -> Handlers=sec_key_notifier event1, KEY bitmap with
 *   VOLUMEDOWN=114, VOLUMEUP=115, POWER=116 and the Samsung assistant key
 *   0x2bf=703).  Nothing in the Fedora userspace owns them: there is no logind
 *   session here, phoc treats them as an ordinary keyboard, and the A27 fb UI
 *   (which used to read them) is masked.  This single manager is therefore the
 *   only handler, which is what "prevent duplicated handling" (mission 10)
 *   requires.
 *
 * BEHAVIOUR (all measured, never assumed):
 *   POWER  short press  -> DISPLAY_OFF / DISPLAY_ON toggle through the running
 *                          display bridge (no second /dev/fb0 owner)
 *   POWER  long  press  -> configurable action (default: "power-menu", which is
 *                          currently logged-and-refused rather than guessed); the
 *                          Samsung hardware combos (Download/Recovery held at
 *                          boot) are untouched because they happen before Linux
 *   VOLUME +/-          -> the REAL ALSA mixer of card0 (beyond-madera), with
 *                          autorepeat and a published OSD state file
 *   ASSISTANT (Bixby)   -> "open-terminal": the Nuxel Terminal PWA in the real
 *                          launcher host (mission 13), remappable in Settings
 *
 * CONFIGURATION  /etc/nuxel/input/buttons.json (also written by the Settings app
 *   through the launcher host and by /usr/bin/nuxelctl on the live console).
 *   Logical actions are separated from physical keycodes:
 *       KEY_SOURCE -> LOGICAL_ACTION -> APPLICATION_OR_SYSTEM_ACTION
 *   so a future phone only needs a new key->source mapping, not new logic.
 *
 * MODES
 *   --probe              print every input device with its real capabilities
 *                        (EVIOCGNAME/EVIOCGBIT/EVIOCGPROP/EVIOCGABS) and exit
 *   --capture [SECONDS]  decode and print KEY/MT events (diagnostics only)
 *   (default)            run the manager
 */
#define _GNU_SOURCE
#include <alsa/asoundlib.h>
#include <ctype.h>
#include <dirent.h>
#include <errno.h>
#include <fcntl.h>
#include <linux/input.h>
#include <poll.h>
#include <signal.h>
#include <stdarg.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/ioctl.h>
#include <sys/stat.h>
#include <sys/time.h>
#include <time.h>
#include <unistd.h>

#define STATE_FILE   "/var/lib/nuxel/buttons"
/* OSD state is published INSIDE the launcher's own docroot: /usr/share/nuxel is
 * served by the launcher's static server (nuxel-session.sh), so the unmodified
 * launcher page can poll it without any new service, socket or API. */
#define OSD_FILE     "/usr/share/nuxel/runtime/osd.json"
#define OSD_DIR      "/usr/share/nuxel/runtime"
#define CONFIG_FILE  "/etc/nuxel/input/buttons.json"
#define CTRL_FIFO    "/run/nuxel-buttons.cmd"
#define WLFB_FIFO    "/run/nuxel-wl-fb.cmd"
#define HOST_FIFO    "/run/nuxel-pwa-host.cmd"

/* Samsung assistant/Bixby key on this keypad.  It is the only key above
 * BTN_MISC in the gpio_keys bitmap (measured: KEY=...8000000000000000 ...);
 * the physical press is confirmed in the acceptance test. */
#define KEY_BIXBY 0x2bf

static int verbose = 1;
static void st(const char *fmt, ...) __attribute__((format(printf, 1, 2)));
static void st(const char *fmt, ...) {
  va_list ap;
  va_start(ap, fmt);
  if (verbose) { vfprintf(stderr, fmt, ap); fputc('\n', stderr); }
  va_end(ap);
}

static void publish(const char *fmt, ...) {
  FILE *f = fopen(STATE_FILE, "w");
  if (!f) return;
  char t[32];
  time_t now = time(NULL);
  struct tm tm;
  gmtime_r(&now, &tm);
  strftime(t, sizeof t, "%Y-%m-%dT%H:%M:%SZ", &tm);
  fprintf(f, "%s ", t);
  va_list ap;
  va_start(ap, fmt);
  vfprintf(f, fmt, ap);
  va_end(ap);
  fputc('\n', f);
  fclose(f);
}

/* ---------------- config ---------------- */
struct cfg {
  char bixby_short[64], bixby_long[64];
  char power_short[64], power_long[64];
  char vol_up[64], vol_down[64];
};
static struct cfg C = { "open-terminal", "disabled", "screen-toggle", "power-menu",
                        "volume-up", "volume-down" };
static time_t cfg_mtime;

static void json_field(const char *js, const char *key, char *out, size_t outn, const char *dflt) {
  snprintf(out, outn, "%s", dflt);
  char pat[96];
  snprintf(pat, sizeof pat, "\"%s\"", key);
  const char *p = strstr(js, pat);
  if (!p) return;
  p += strlen(pat);
  while (*p && (*p == ' ' || *p == ':' || *p == '\t')) p++;
  if (*p != '"') return;
  p++;
  size_t i = 0;
  while (*p && *p != '"' && i + 1 < outn) out[i++] = *p++;
  out[i] = 0;
}

static void cfg_load(int force) {
  struct stat sb;
  if (stat(CONFIG_FILE, &sb) != 0) {
    if (force) st("CONFIG_ABSENT %s (built-in defaults in use)", CONFIG_FILE);
    return;
  }
  if (!force && sb.st_mtime == cfg_mtime) return;
  cfg_mtime = sb.st_mtime;
  FILE *f = fopen(CONFIG_FILE, "rb");
  if (!f) return;
  static char buf[8192];
  size_t n = fread(buf, 1, sizeof buf - 1, f);
  buf[n] = 0;
  fclose(f);
  json_field(buf, "bixby_short", C.bixby_short, sizeof C.bixby_short, "open-terminal");
  json_field(buf, "bixby_long",  C.bixby_long,  sizeof C.bixby_long,  "disabled");
  json_field(buf, "power_short", C.power_short, sizeof C.power_short, "screen-toggle");
  json_field(buf, "power_long",  C.power_long,  sizeof C.power_long,  "power-menu");
  json_field(buf, "volume_up",   C.vol_up,      sizeof C.vol_up,      "volume-up");
  json_field(buf, "volume_down", C.vol_down,    sizeof C.vol_down,    "volume-down");
  st("CONFIG_LOADED mtime=%ld bixby_short=%s power_short=%s power_long=%s",
     (long)sb.st_mtime, C.bixby_short, C.power_short, C.power_long);
}

/* ---------------- actions ---------------- */
static void fifo_send(const char *path, const char *line) {
  int fd = open(path, O_WRONLY | O_NONBLOCK);
  if (fd < 0) { st("ACTION_FAIL path=%s errno=%d", path, errno); return; }
  if (write(fd, line, strlen(line)) < 0) { /* best effort */ }
  close(fd);
}

/* ---- real ALSA volume (card 0 = beyond-madera; measured with the probe) ---- */
static snd_mixer_t *mixer;
static snd_mixer_elem_t *selem;
static long vol_min, vol_max, vol_cur;
static int mixer_ready;

static int mixer_open_dev(void) {
  if (mixer_ready) return 0;
  if (snd_mixer_open(&mixer, 0) < 0) { st("MIXER_OPEN_FAIL"); return -1; }
  if (snd_mixer_attach(mixer, "default") < 0 && snd_mixer_attach(mixer, "hw:0") < 0) {
    st("MIXER_ATTACH_FAIL"); snd_mixer_close(mixer); mixer = NULL; return -1;
  }
  snd_mixer_selem_register(mixer, NULL, NULL);
  if (snd_mixer_load(mixer) < 0) { st("MIXER_LOAD_FAIL"); snd_mixer_close(mixer); mixer = NULL; return -1; }
  /* prefer a playback volume element; log every candidate so the choice is auditable */
  static const char *prefer[] = { "Master", "Speaker", "Headphone", "Digital Volume", "PCM", "Playback", NULL };
  for (int i = 0; prefer[i] && !selem; i++)
    for (snd_mixer_elem_t *e = snd_mixer_first_elem(mixer); e; e = snd_mixer_elem_next(e)) {
      if (!snd_mixer_selem_is_active(e) || !snd_mixer_selem_has_playback_volume(e)) continue;
      if (strcasestr(snd_mixer_selem_get_name(e), prefer[i])) { selem = e; break; }
    }
  if (!selem)
    for (snd_mixer_elem_t *e = snd_mixer_first_elem(mixer); e; e = snd_mixer_elem_next(e))
      if (snd_mixer_selem_is_active(e) && snd_mixer_selem_has_playback_volume(e)) { selem = e; break; }
  if (!selem) { st("MIXER_NO_PLAYBACK_ELEMENT (audio path has no writable playback vol control)"); mixer_ready = 1; return -1; }
  snd_mixer_selem_get_playback_volume_range(selem, &vol_min, &vol_max);
  if (snd_mixer_selem_get_playback_volume(selem, SND_MIXER_SCHN_FRONT_LEFT, &vol_cur) < 0) vol_cur = vol_min;
  mixer_ready = 1;
  st("MIXER_READY element=%s min=%ld max=%ld current=%ld",
     snd_mixer_selem_get_name(selem), vol_min, vol_max, vol_cur);
  return 0;
}

static void osd_publish(const char *kind, const char *text, int value, int level_max) {
  mkdir(OSD_DIR, 0755);
  char tmp[256];
  snprintf(tmp, sizeof tmp, "%s.tmp", OSD_FILE);
  FILE *f = fopen(tmp, "w");
  if (!f) return;
  fprintf(f, "{\"schema_version\":1,\"kind\":\"%s\",\"text\":\"%s\",\"value\":%d,\"max\":%d,\"ts\":%ld}\n",
          kind, text, value, level_max, (long)time(NULL));
  fclose(f);
  rename(tmp, OSD_FILE);
}

static void osd_volume(void) {
  if (mixer_open_dev() < 0 || !selem) {
    osd_publish("volume", "audio path unavailable", 0, 0);
    publish("VOLUME_UNSUPPORTED reason=no-playback-element");
    return;
  }
  long v = vol_cur;
  int pct = (vol_max > vol_min) ? (int)(((v - vol_min) * 100) / (vol_max - vol_min)) : 0;
  char txt[64];
  snprintf(txt, sizeof txt, "%d%%", pct);
  osd_publish("volume", txt, pct, 100);
  publish("VOLUME element=%s value=%ld pct=%d", snd_mixer_selem_get_name(selem), v, pct);
}

static void volume_step(int dir) {
  if (mixer_open_dev() < 0 || !selem) { osd_volume(); return; }
  long step = (vol_max - vol_min) / 20;             /* 5 % of the range */
  if (step < 1) step = 1;
  long v = vol_cur + (dir > 0 ? step : -step);
  if (v > vol_max) v = vol_max;
  if (v < vol_min) v = vol_min;
  if (snd_mixer_selem_set_playback_volume_all(selem, v) < 0) {
    st("VOLUME_SET_FAIL value=%ld", v);
    return;
  }
  vol_cur = v;
  osd_volume();
}

static void volume_mute_toggle(void) {
  if (mixer_open_dev() < 0 || !selem) { osd_volume(); return; }
  int sw = 0;
  if (snd_mixer_selem_has_playback_switch(selem) && snd_mixer_selem_get_playback_switch(selem, SND_MIXER_SCHN_FRONT_LEFT, &sw) == 0) {
    snd_mixer_selem_set_playback_switch_all(selem, sw ? 0 : 1);
    osd_publish("volume", sw ? "muted" : "unmuted", sw ? 0 : 100, 100);
    publish("VOLUME_MUTE=%d", sw ? 1 : 0);
  } else {
    osd_publish("volume", "no mute switch on this control", 0, 0);
    publish("VOLUME_MUTE_UNSUPPORTED");
  }
}

/* ---- application/system action dispatch (KEY_SOURCE -> LOGICAL_ACTION) ---- */
static void perform(const char *action, const char *source) {
  publish("ACTION source=%s action=%s", source, action);
  if (!action[0] || !strcmp(action, "disabled") || !strcmp(action, "none")) {
    st("ACTION %s -> disabled (%s)", action, source);
    return;
  }
  if (!strcmp(action, "screen-toggle") || !strcmp(action, "screen-off") || !strcmp(action, "screen-on")) {
    char l[64];
    snprintf(l, sizeof l, "%s\n", action);
    fifo_send(WLFB_FIFO, l);
    st("ACTION %s -> display bridge", action);
    return;
  }
  if (!strcmp(action, "volume-up"))   { volume_step(+1); st("ACTION volume-up (%s)", source); return; }
  if (!strcmp(action, "volume-down")) { volume_step(-1); st("ACTION volume-down (%s)", source); return; }
  if (!strcmp(action, "volume-mute")) { volume_mute_toggle(); return; }
  if (!strcmp(action, "open-terminal")) { fifo_send(HOST_FIFO, "open-terminal\n"); st("ACTION open-terminal -> launcher host"); return; }
  if (!strcmp(action, "home") || !strcmp(action, "search") || !strcmp(action, "settings")) {
    char l[64];
    snprintf(l, sizeof l, "action %s\n", action);
    fifo_send(HOST_FIFO, l);
    st("ACTION %s -> launcher host", action);
    return;
  }
  if (!strncmp(action, "app:", 4)) {
    const char *id = action + 4;
    for (const char *p = id; *p; p++)
      if (!(isalnum((unsigned char)*p) || *p == '.' || *p == '_' || *p == '-')) {
        st("ACTION app:%s REFUSED (invalid id)", id);
        return;
      }
    char l[128];
    snprintf(l, sizeof l, "launch %s\n", id);
    fifo_send(HOST_FIFO, l);
    st("ACTION app:%s -> launcher host", id);
    return;
  }
  if (!strcmp(action, "power-menu")) {
    /* No power menu exists in the launcher yet.  Refusing loudly is the honest
       behaviour: a long press must never be silently guessed as "shut down". */
    st("ACTION power-menu NOT IMPLEMENTED (long press recorded, no system change)");
    osd_publish("power", "power menu: not available yet", 0, 100);
    return;
  }
  st("ACTION %s UNKNOWN (ignored)", action);
}

/* ---------------- input device discovery ---------------- */
struct keydev {
  int fd;
  char path[64];
  char name[256];
  int has_key;
};

/* Proper capability walk: EVIOCGBIT(EV_KEY) with the kernel's own long size, so
   a key the driver really reports can never be classified as absent (mission
   6.4).  A missing/incorrect ioctl is reported, never silently ignored. */
static int dev_has_key(int fd, unsigned code) {
  unsigned long bits[(KEY_MAX / (8 * sizeof(long))) + 1];
  memset(bits, 0, sizeof bits);
  if (ioctl(fd, EVIOCGBIT(EV_KEY, sizeof bits), bits) < 0) return -1;
  return !!(bits[code / (8 * sizeof(long))] & (1UL << (code % (8 * sizeof(long)))));
}

static void print_dev(int fd, const char *path) {
  char name[256] = "";
  if (ioctl(fd, EVIOCGNAME(sizeof name), name) < 0) snprintf(name, sizeof name, "?");
  struct input_id id;
  memset(&id, 0, sizeof id);
  ioctl(fd, EVIOCGID, &id);
  unsigned long props[(INPUT_PROP_MAX / (8 * sizeof(long))) + 1];
  memset(props, 0, sizeof props);
  int prc = ioctl(fd, EVIOCGPROP(sizeof props), props);
  unsigned long keys[(KEY_MAX / (8 * sizeof(long))) + 1];
  memset(keys, 0, sizeof keys);
  int krc = ioctl(fd, EVIOCGBIT(EV_KEY, sizeof keys), keys);
  unsigned long abs[(ABS_MAX / (8 * sizeof(long))) + 1];
  memset(abs, 0, sizeof abs);
  int arc = ioctl(fd, EVIOCGBIT(EV_ABS, sizeof abs), abs);
  printf("%s name=%s bus=%04x vid=%04x pid=%04x\n", path, name, id.bustype, id.vendor, id.product);
  printf("    EVIOCGPROP rc=%d direct=%d\n", prc,
         (prc >= 0) ? !!(props[INPUT_PROP_DIRECT / (8 * sizeof(long))] & (1UL << (INPUT_PROP_DIRECT % (8 * sizeof(long))))) : -1);
  printf("    EVIOCGBIT(EV_KEY) rc=%d keys:", krc);
  if (krc >= 0)
    for (unsigned c = 0; c <= KEY_MAX; c++)
      if (keys[c / (8 * sizeof(long))] & (1UL << (c % (8 * sizeof(long))))) printf(" %u", c);
  printf("\n");
  printf("    EVIOCGBIT(EV_ABS) rc=%d abs:", arc);
  if (arc >= 0)
    for (unsigned c = 0; c <= ABS_MAX; c++)
      if (abs[c / (8 * sizeof(long))] & (1UL << (c % (8 * sizeof(long))))) printf(" %u", c);
  printf("\n");
  unsigned probe[] = { ABS_X, ABS_Y, ABS_MT_SLOT, ABS_MT_POSITION_X, ABS_MT_POSITION_Y, ABS_MT_TRACKING_ID, ABS_PRESSURE };
  for (unsigned i = 0; i < sizeof probe / sizeof probe[0]; i++) {
    struct input_absinfo ai;
    memset(&ai, 0, sizeof ai);
    if (ioctl(fd, EVIOCGABS(probe[i]), &ai) == 0)
      printf("    ABS%u min=%d max=%d fuzz=%d flat=%d res=%d\n",
             probe[i], ai.minimum, ai.maximum, ai.fuzz, ai.flat, ai.resolution);
  }
  fflush(stdout);
}

static int open_key_device(struct keydev *kd, const char *want) {
  DIR *d = opendir("/dev/input");
  if (!d) return -1;
  struct dirent *de;
  while ((de = readdir(d))) {
    if (strncmp(de->d_name, "event", 5)) continue;
    char path[80];
    snprintf(path, sizeof path, "/dev/input/%s", de->d_name);
    int fd = open(path, O_RDONLY | O_NONBLOCK);
    if (fd < 0) continue;
    char name[256] = "";
    if (ioctl(fd, EVIOCGNAME(sizeof name), name) < 0) { close(fd); continue; }
    int iskey = dev_has_key(fd, KEY_POWER) > 0 || dev_has_key(fd, KEY_VOLUMEUP) > 0 ||
                dev_has_key(fd, KEY_VOLUMEDOWN) > 0;
    if (iskey && (!want || strstr(name, want))) {
      kd->fd = fd;
      snprintf(kd->path, sizeof kd->path, "%s", path);
      snprintf(kd->name, sizeof kd->name, "%s", name);
      kd->has_key = 1;
      closedir(d);
      return 0;
    }
    close(fd);
  }
  closedir(d);
  return -1;
}

/* ---------------- capture / diagnostics ---------------- */
static void capture(double secs) {
  DIR *d = opendir("/dev/input");
  int fds[16]; char paths[16][32]; int n = 0;
  struct pollfd pfd[16];
  if (!d) return;
  struct dirent *de;
  while ((de = readdir(d)) && n < 16) {
    if (strncmp(de->d_name, "event", 5)) continue;
    char p[80];
    snprintf(p, sizeof p, "/dev/input/%s", de->d_name);
    int fd = open(p, O_RDONLY | O_NONBLOCK);
    if (fd < 0) continue;
    fds[n] = fd; snprintf(paths[n], sizeof paths[n], "%s", de->d_name);
    pfd[n].fd = fd; pfd[n].events = POLLIN;
    n++;
  }
  printf("capture: %d devices for %.1fs — touch/press now\n", n, secs);
  fflush(stdout);
  struct timeval t0, now;
  gettimeofday(&t0, NULL);
  for (;;) {
    gettimeofday(&now, NULL);
    if ((now.tv_sec - t0.tv_sec) + (now.tv_usec - t0.tv_usec) / 1e6 > secs) break;
    int r = poll(pfd, (nfds_t)n, 200);
    if (r <= 0) continue;
    for (int i = 0; i < n; i++) {
      if (!(pfd[i].revents & POLLIN)) continue;
      struct input_event ev[64];
      ssize_t got = read(fds[i], ev, sizeof ev);
      int cnt = (int)(got / (ssize_t)sizeof(struct input_event));
      for (int k = 0; k < cnt; k++) {
        struct input_event *e = &ev[k];
        gettimeofday(&now, NULL);
        double t = (now.tv_sec - t0.tv_sec) + (now.tv_usec - t0.tv_usec) / 1e6;
        if (e->type == EV_KEY)
          printf("%s t=%.3f EV_KEY code=%u value=%d%s\n", paths[i], t, e->code, e->value,
                 e->code == KEY_POWER ? " (POWER)" : e->code == KEY_VOLUMEUP ? " (VOLUMEUP)"
                 : e->code == KEY_VOLUMEDOWN ? " (VOLUMEDOWN)" : e->code == KEY_BIXBY ? " (ASSISTANT/BIXBY)" : "");
        else if (e->type == EV_ABS)
          printf("%s t=%.3f EV_ABS code=%u value=%d\n", paths[i], t, e->code, e->value);
        else if (e->type == EV_SYN && e->code == SYN_REPORT)
          printf("%s t=%.3f SYN_REPORT\n", paths[i], t);
      }
      fflush(stdout);
    }
  }
  for (int i = 0; i < n; i++) close(fds[i]);
}

/* ---------------- main loop ---------------- */
static volatile int running = 1;
static void on_term(int sig) { (void)sig; running = 0; }

int main(int argc, char **argv) {
  if (argc > 1 && !strcmp(argv[1], "--probe")) {
    DIR *d = opendir("/dev/input");
    if (!d) { perror("/dev/input"); return 1; }
    struct dirent *de;
    while ((de = readdir(d))) {
      if (strncmp(de->d_name, "event", 5)) continue;
      char p[80];
      snprintf(p, sizeof p, "/dev/input/%s", de->d_name);
      int fd = open(p, O_RDONLY | O_NONBLOCK);
      if (fd < 0) { printf("%s OPEN_FAIL errno=%d\n", p, errno); continue; }
      print_dev(fd, p);
      close(fd);
    }
    closedir(d);
    printf("--- ALSA ---\n");
    mixer_open_dev();
    printf("--- /proc/asound/cards ---\n");
    FILE *f = fopen("/proc/asound/cards", "r");
    if (f) { char line[256]; while (fgets(line, sizeof line, f)) fputs(line, stdout); fclose(f); }
    printf("--- backlight ---\n");
    int fd = open("/sys/class/backlight/panel/brightness", O_RDONLY);
    if (fd >= 0) { char b[32]; ssize_t k = read(fd, b, sizeof b - 1); if (k > 0) { b[k] = 0; printf("brightness=%s", b); } close(fd); }
    fd = open("/sys/class/backlight/panel/max_brightness", O_RDONLY);
    if (fd >= 0) { char b[32]; ssize_t k = read(fd, b, sizeof b - 1); if (k > 0) { b[k] = 0; printf("max_brightness=%s", b); } close(fd); }
    return 0;
  }
  if (argc > 2 && !strcmp(argv[1], "--capture")) { capture(atof(argv[2])); return 0; }
  if (argc > 1) { fprintf(stderr, "usage: %s [--probe|--capture SECS]\n", argv[0]); return 2; }

  signal(SIGTERM, on_term);
  signal(SIGINT, on_term);
  cfg_load(1);

  /* control FIFO for the launcher host / console (same logical actions) */
  unlink(CTRL_FIFO);
  if (mkfifo(CTRL_FIFO, 0600) < 0 && errno != EEXIST) st("CTRL_FIFO_FAIL errno=%d", errno);
  int ctl = open(CTRL_FIFO, O_RDWR | O_NONBLOCK | O_CLOEXEC);

  struct keydev kd = { -1, "", "", 0 };
  if (open_key_device(&kd, getenv("NUXEL_KEY_DEVICE")) < 0) {
    st("KEY_DEVICE_NOT_FOUND (no evdev node exposes POWER/VOLUME keys)");
    publish("KEY_DEVICE_NOT_FOUND");
    return 3;
  }
  st("KEY_DEVICE_OPEN path=%s name=%s", kd.path, kd.name);
  publish("KEY_DEVICE_OPEN path=%s name=%s", kd.path, kd.name);

  unsigned long keys[(KEY_MAX / (8 * sizeof(long))) + 1];
  memset(keys, 0, sizeof keys);
  if (ioctl(kd.fd, EVIOCGBIT(EV_KEY, sizeof keys), keys) >= 0) {
    char list[512];
    size_t o = 0;
    for (unsigned c = 0; c <= KEY_MAX && o < sizeof list - 8; c++)
      if (keys[c / (8 * sizeof(long))] & (1UL << (c % (8 * sizeof(long)))))
        o += (size_t)snprintf(list + o, sizeof list - o, "%u ", c);
    list[o] = 0;
    publish("KEY_CAPABILITIES %s", list);
    st("KEY_CAPABILITIES %s", list);
  } else {
    st("EVIOCGBIT(EV_KEY) FAILED errno=%d — refusing to guess the key set", errno);
    publish("EVIOCGBIT_FAILED errno=%d", errno);
  }

  struct pollfd pf[2] = { { kd.fd, POLLIN, 0 }, { ctl, POLLIN, 0 } };
  int64_t power_down_ms = 0, bixby_down_ms = 0;
  int power_used = 0, bixby_used = 0;
  int64_t vol_repeat_ms = 0;
  int vol_held = 0;
  time_t last_cfg_poll = 0;
  publish("MANAGER_READY device=%s", kd.path);

  while (running) {
    int r = poll(pf, 2, 200);
    time_t now = time(NULL);
    if (now != last_cfg_poll) { last_cfg_poll = now; cfg_load(0); }
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC, &ts);
    int64_t now_ms = (int64_t)ts.tv_sec * 1000 + ts.tv_nsec / 1000000;
    if (r > 0 && (pf[1].revents & POLLIN)) {
      char buf[512];
      ssize_t n = read(ctl, buf, sizeof buf - 1);
      if (n > 0) {
        buf[n] = 0;
        for (char *q = buf; q && *q; ) {
          char *nl = strchr(q, '\n');
          if (nl) *nl = 0;
          if (!strcmp(q, "volume-up")) volume_step(+1);
          else if (!strcmp(q, "volume-down")) volume_step(-1);
          else if (!strcmp(q, "volume-mute")) volume_mute_toggle();
          else if (!strncmp(q, "action ", 7)) perform(q + 7, "control-fifo");
          else if (!strcmp(q, "reload")) cfg_load(1);
          else if (*q) st("CTRL_UNKNOWN '%s'", q);
          q = nl ? nl + 1 : NULL;
        }
      }
    }
    if (r > 0 && (pf[0].revents & POLLIN)) {
      struct input_event ev[64];
      ssize_t got = read(kd.fd, ev, sizeof ev);
      int cnt = (int)(got / (ssize_t)sizeof(struct input_event));
      for (int k = 0; k < cnt; k++) {
        struct input_event *e = &ev[k];
        if (e->type != EV_KEY) continue;
        if (e->code == KEY_POWER) {
          if (e->value == 1) { power_down_ms = now_ms; power_used = 0; }
          else if (e->value == 2) {
            if ((now_ms - power_down_ms) >= 2000 && !power_used) {
              power_used = 1;
              perform(C.power_long, "power(long)");
            }
          } else if (e->value == 0) {
            if (!power_used) {
              int64_t held = now_ms - power_down_ms;
              if (held >= 30 && held < 2000) perform(C.power_short, "power(short)");
              else st("POWER_DEBOUNCED held=%lldms", (long long)held);
            }
            power_used = 0;
          }
        } else if (e->code == KEY_VOLUMEUP || e->code == KEY_VOLUMEDOWN) {
          int dir = (e->code == KEY_VOLUMEUP) ? +1 : -1;
          if (e->value == 1) {
            vol_held = dir;
            vol_repeat_ms = now_ms + 400;      /* debounce, then autorepeat */
            if (dir > 0) perform(C.vol_up, "volume-up"); else perform(C.vol_down, "volume-down");
          } else if (e->value == 2) {
            /* autorepeat is handled on the timer below */
          } else if (e->value == 0) {
            vol_held = 0; st("VOLUME_KEY_RELEASED code=%u", e->code);
          }
        } else if (e->code == (unsigned)KEY_BIXBY) {
          if (e->value == 1) { bixby_down_ms = now_ms; bixby_used = 0; }
          else if (e->value == 2) {
            if ((now_ms - bixby_down_ms) >= 1500 && !bixby_used) {
              bixby_used = 1;
              perform(C.bixby_long, "bixby(long)");
            }
          } else if (e->value == 0) {
            if (!bixby_used) {
              int64_t held = now_ms - bixby_down_ms;
              if (held >= 20 && held < 1500) perform(C.bixby_short, "bixby(short)");
              else st("BIXBY_DEBOUNCED held=%lldms", (long long)held);
            }
            bixby_used = 0;
          }
        } else if (e->value == 1) {
          st("KEY_UNMAPPED code=%u source=keyboard", e->code);
        }
      }
    }
    if (vol_held && now_ms >= vol_repeat_ms) {
      perform(vol_held > 0 ? C.vol_up : C.vol_down, vol_held > 0 ? "volume-up(repeat)" : "volume-down(repeat)");
      vol_repeat_ms = now_ms + 250;
    }
  }
  st("MANAGER_EXIT");
  publish("MANAGER_EXIT");
  if (ctl >= 0) close(ctl);
  close(kd.fd);
  return 0;
}
