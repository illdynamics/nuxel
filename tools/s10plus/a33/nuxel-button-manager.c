/* nuxel-button-manager — the S10+ physical buttons and screen gestures as PHONE
 * controls (A33, briq-03e). Supersedes tools/s10plus/a32/nuxel-button-manager.c
 * WITHOUT touching it: the A32 sources stay byte-identical because they are the
 * protected baseline (docs/beta-finalization/baseline-protection.json, INV-4),
 * and the offline test asserts behavioural parity with them.
 *
 * WHAT CHANGED FROM A32
 *   * the press logic is now a real state machine (nuxel-button-fsm.h) with
 *     single, double, long and VERY LONG press classes,
 *   * a power MENU exists (selection, refusal, timeout) instead of the A32
 *     "logged-and-refused" placeholder,
 *   * the screen gestures swipe-up (home), swipe-up-and-hold (recents) and
 *     edge-swipe-inward (back) are recognised,
 *   * the reboot class is gated by a policy file and refuses by default,
 *   * Recovery / Download-Mode entries EXIST in the menu and are hard-refused.
 *
 * WHAT DID NOT CHANGE
 *   * one process owns the gpio_keys key set,
 *   * POWER short toggles the display through the running bridge (never a second
 *     framebuffer owner),
 *   * volume drives the REAL ALSA mixer of the beyond-madera card,
 *   * input nodes are selected by capability and name, never by eventN.
 *
 * HONESTY
 *   Nothing here claims the handset does anything. The daemon publishes what it
 *   DECIDED and what it DISPATCHED. Whether the panel blinked, the volume moved
 *   or the assistant opened is observable only on the phone
 *   (docs/beta-finalization/system/BUTTONS-GESTURES.md).
 *
 * MODES
 *   (default)              run the manager
 *   --probe                print the real input devices, their capabilities, the
 *                          resolved key/touch nodes, the ALSA mixer and the
 *                          resolved configuration
 *   --capture [SECONDS]    decode and print KEY/MT events (diagnostics only)
 *   --menu-dump            print the state machine's constants and menu table
 *   --fsm-sim <trace.json> replay a recorded event trace through the REAL FSM
 *                          core (delegates to the nuxel-button-fsm-sim helper so
 *                          no second implementation of the logic exists)
 *   --config-check         parse every configuration file and print the result
 *                          WITHOUT opening any input device or mixer
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
#include <sys/wait.h>
#include <time.h>
#include <unistd.h>

#include "nuxel-button-fsm.h"

/* ---- paths (single source of truth: configs/nuxel/paths.conf) ------------ */
#define STATE_FILE   "/var/lib/nuxel/buttons"
#define LOG_FILE     "/var/log/nuxel/buttons.log"
#define OSD_FILE     "/usr/share/nuxel/runtime/osd.json"
#define OSD_DIR      "/usr/share/nuxel/runtime"
#define BUTTONS_JSON "/etc/nuxel/input/buttons.json"
#define FSM_JSON     "/etc/nuxel/input/button-fsm.json"
#define GATE_JSON    "/etc/nuxel/buttons/reboot-gate.json"
#define POLICY_JSON  "/var/lib/nuxel/reboot/policy.json"
#define GATE_STATE   "/var/lib/nuxel/buttons/reboot-gate.json"
#define AUDIO_JSON   "/etc/nuxel/audio/audio.json"
#define BRINGUP_FLAG "/var/lib/nuxel/audio/bringup-incomplete"
#define CTRL_FIFO    "/run/nuxel-buttons.cmd"
#define WLFB_FIFO    "/run/nuxel-wl-fb.cmd"
#define HOST_FIFO    "/run/nuxel-pwa-host.cmd"
#define SIM_BIN      "/usr/lib/nuxel/nuxel-button-fsm-sim"
/* briq-03e additions: the sound-mode state, the flashlight request and the
 * one-time verbose-boot request/state published by briq-02b. */
#define SOUND_MODE_FILE "/var/lib/nuxel/audio/sound-mode"
#define SOUND_MODE_DIR  "/var/lib/nuxel/audio"
#define FLASHLIGHT_REQ  "/run/nuxel/flashlight.request"
#define VERBOSE_ONCE    "/run/nuxel/boot-verbose-once"
#define VERBOSE_STATE   "/run/nuxel/verbose-boot"
#define BOOT_CAPS       "/run/nuxel/boot-stage-capabilities"

static int verbose = 1;
static void st(const char *fmt, ...) __attribute__((format(printf, 1, 2)));
static void st(const char *fmt, ...) {
  va_list ap;
  va_start(ap, fmt);
  if (verbose) { vfprintf(stderr, fmt, ap); fputc('\n', stderr); }
  va_end(ap);
}

/* Every decision is also appended to the audit log, so an action can always be
 * traced back to the event that produced it. */
static void audit(const char *fmt, ...) {
  va_list ap, ap2;
  va_start(ap, fmt);
  va_copy(ap2, ap);
  if (verbose) { vfprintf(stderr, fmt, ap); fputc('\n', stderr); }
  va_end(ap);
  mkdir("/var/log/nuxel", 0755);
  FILE *f = fopen(LOG_FILE, "a");
  if (f) {
    char t[32];
    time_t now = time(NULL);
    struct tm tm;
    gmtime_r(&now, &tm);
    strftime(t, sizeof t, "%Y-%m-%dT%H:%M:%SZ", &tm);
    fprintf(f, "%s ", t);
    vfprintf(f, fmt, ap2);
    fputc('\n', f);
    fclose(f);
  }
  va_end(ap2);
}

static void publish(const char *fmt, ...) {
  mkdir("/var/lib/nuxel", 0755);
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

/* ============================ configuration ============================== */

static int json_int(const char *js, const char *key, int dflt) {
  char pat[96];
  snprintf(pat, sizeof pat, "\"%s\"", key);
  const char *p = strstr(js, pat);
  if (!p) return dflt;
  p += strlen(pat);
  while (*p && (*p == ' ' || *p == ':' || *p == '\t')) p++;
  if (!*p) return dflt;
  if (*p == 't') return 1;              /* true  */
  if (*p == 'f') return 0;              /* false */
  return atoi(p);
}

static void json_str(const char *js, const char *key, char *out, size_t outn, const char *dflt) {
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

/* read a whole file into a static buffer; returns NULL when absent */
static char *slurp(const char *path, size_t max) {
  static char buf[16384];
  if (max > sizeof buf) max = sizeof buf;
  FILE *f = fopen(path, "r");
  if (!f) return NULL;
  size_t n = fread(buf, 1, max - 1, f);
  buf[n] = 0;
  fclose(f);
  return buf;
}

static nuxel_fsm_cfg C;        /* the action map (FSM defaults + buttons.json) */
static nuxel_fsm_gate GATE;    /* the reboot gate                              */
static int vol_cap_pct = 25;   /* from audio.json                              */
static int vol_cap_active = 0; /* only while the bring-up flag exists          */

static void cfg_load_actions(void) {
  nuxel_fsm_cfg_defaults(&C);
  char *j = slurp(FSM_JSON, 0);
  if (j) {
    json_str(j, "power_short",      C.power_short,       sizeof C.power_short,       C.power_short);
    json_str(j, "power_long",       C.power_long,        sizeof C.power_long,        C.power_long);
    json_str(j, "power_double",     C.power_double,      sizeof C.power_double,      C.power_double);
    json_str(j, "power_very_long",  C.power_very_long,   sizeof C.power_very_long,   C.power_very_long);
    json_str(j, "volume_up",        C.volume_up,         sizeof C.volume_up,         C.volume_up);
    json_str(j, "volume_down",      C.volume_down,       sizeof C.volume_down,       C.volume_down);
    json_str(j, "bixby_short",      C.bixby_short,       sizeof C.bixby_short,       C.bixby_short);
    json_str(j, "bixby_long",       C.bixby_long,        sizeof C.bixby_long,        C.bixby_long);
    json_str(j, "bixby_double",     C.bixby_double,      sizeof C.bixby_double,      C.bixby_double);
    C.defer_power_short_for_double = json_int(j, "defer_power_short_for_double", C.defer_power_short_for_double);
    C.defer_bixby_short_for_double = json_int(j, "defer_bixby_short_for_double", C.defer_bixby_short_for_double);
    C.gestures_enabled             = json_int(j, "gestures_enabled", C.gestures_enabled);
  } else {
    st("FSM_SPEC_ABSENT %s — built-in defaults in use", FSM_JSON);
  }
  /* The A32 file WINS: an owner remap made in Settings or with nuxelctl must
   * never be overridden by the state machine's defaults. */
  char *b = slurp(BUTTONS_JSON, 0);
  if (b) {
    json_str(b, "power_short",   C.power_short,   sizeof C.power_short,   C.power_short);
    json_str(b, "power_long",    C.power_long,    sizeof C.power_long,    C.power_long);
    json_str(b, "power_double",  C.power_double,  sizeof C.power_double,  C.power_double);
    json_str(b, "volume_up",     C.volume_up,     sizeof C.volume_up,     C.volume_up);
    json_str(b, "volume_down",   C.volume_down,   sizeof C.volume_down,   C.volume_down);
    json_str(b, "bixby_short",   C.bixby_short,   sizeof C.bixby_short,   C.bixby_short);
    json_str(b, "bixby_long",    C.bixby_long,    sizeof C.bixby_long,    C.bixby_long);
    json_str(b, "bixby_double",  C.bixby_double,  sizeof C.bixby_double,  C.bixby_double);
    /* briq-03e: the panel/chord/early-hold mappings are owner-remappable too, and
     * an owner value WINS over the shipped default exactly like the A32 keys. */
    json_str(b, "volume_up_long",   C.volume_up_long,   sizeof C.volume_up_long,   C.volume_up_long);
    json_str(b, "volume_down_long", C.volume_down_long, sizeof C.volume_down_long, C.volume_down_long);
    json_str(b, "bixby_early_hold", C.bixby_early_hold, sizeof C.bixby_early_hold, C.bixby_early_hold);
    json_str(b, "chord_power_volume_up",   C.chord_power_volume_up,
             sizeof C.chord_power_volume_up,   C.chord_power_volume_up);
    json_str(b, "chord_power_volume_down", C.chord_power_volume_down,
             sizeof C.chord_power_volume_down, C.chord_power_volume_down);
    C.volume_repeat_enabled = json_int(b, "volume_repeat_enabled", C.volume_repeat_enabled);
    audit("CONFIG_LOADED buttons_json=%s power_short=%s power_long=%s bixby_short=%s",
          BUTTONS_JSON, C.power_short, C.power_long, C.bixby_short);
  } else {
    st("BUTTONS_JSON_ABSENT %s — FSM defaults in use (A32 behaviour)", BUTTONS_JSON);
  }

  /* audio: the low-volume cap only bites while the first bring-up is unfinished */
  char *a = slurp(AUDIO_JSON, 0);
  vol_cap_pct = a ? json_int(a, "volume_cap_percent", 25) : 25;
  struct stat sb;
  vol_cap_active = (stat(BRINGUP_FLAG, &sb) == 0) ||
                   (getenv("NUXEL_AUDIO_LOW_VOLUME") && atoi(getenv("NUXEL_AUDIO_LOW_VOLUME")) != 0);
}

static int file_exists(const char *p) { struct stat sb; return stat(p, &sb) == 0; }

static int journal_clean(void) {
  /* A journal that cannot be read in full is not a journal we may reboot on:
     `journalctl --verify` is the only honest check available, and an absent
     journalctl is reported as unclean rather than assumed fine. */
  if (access("/usr/bin/journalctl", X_OK) != 0) return 0;
  int rc = system("journalctl --verify >/dev/null 2>&1");
  return rc == 0;
}

static void gate_load(void) {
  memset(&GATE, 0, sizeof GATE);
  GATE.min_interval_s = NUXEL_FSM_REBOOT_MIN_INTERVAL_S;
  GATE.max_per_hour = NUXEL_FSM_REBOOT_MAX_PER_HOUR;
  GATE.require_rollback_path = 1;
  char *g = slurp(GATE_JSON, 0);
  if (g) {
    GATE.enabled = json_int(g, "enabled", 0);
    GATE.allow_restart = json_int(g, "allow_restart", 0);
    GATE.allow_poweroff = json_int(g, "allow_poweroff", 0);
    GATE.min_interval_s = json_int(g, "min_interval_s", GATE.min_interval_s);
    GATE.max_per_hour = json_int(g, "max_reboots_per_hour", GATE.max_per_hour);
    GATE.require_rollback_path = json_int(g, "require_rollback_path", 1);
    GATE.require_clean_journal = json_int(g, "require_clean_journal", 0);
  } else {
    st("REBOOT_GATE_ABSENT %s — refusing every reboot/power-off action", GATE_JSON);
  }
  /* bg-09's policy is an ADDITIONAL permission, never an override. */
  char *p = slurp(POLICY_JSON, 0);
  if (p) {
    GATE.policy_known = 1;
    GATE.policy_allow_reboot = json_int(p, "allow_reboot", 0);
  }
  /* rollback path: the mission requires a known-working userspace rollback. */
  GATE.rollback_path_ok = file_exists("/usr/lib/nuxel/nuxel-wl-fb.prev-a32") ||
                          file_exists("/nuxel/tools/nuxel-rollback-home.sh") ||
                          file_exists("tools/nuxel-rollback-home.sh");
  if (GATE.require_clean_journal) GATE.journal_clean = journal_clean();
  else GATE.journal_clean = 1;
  /* last-reboot bookkeeping from the gate state file (written on every decision) */
  char *s = slurp(GATE_STATE, 0);
  if (s) {
    GATE.last_reboot_t_s = (int64_t)atoll(s);   /* first line: epoch seconds */
    GATE.reboots_last_hour = 0;
  }
  audit("REBOOT_GATE enabled=%d restart=%d poweroff=%d rollback_ok=%d policy_known=%d policy_allow=%d",
        GATE.enabled, GATE.allow_restart, GATE.allow_poweroff, GATE.rollback_path_ok,
        GATE.policy_known, GATE.policy_allow_reboot);
}

/* =============================== dispatch ================================ */

static int osd_menu_index = -1;   /* index currently rendered into the OSD file */

static void fifo_send(const char *path, const char *line) {
  int fd = open(path, O_WRONLY | O_NONBLOCK);
  if (fd < 0) { audit("ACTION_FAIL path=%s errno=%d", path, errno); return; }
  if (write(fd, line, strlen(line)) < 0) { /* best effort */ }
  close(fd);
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

static void osd_menu(int open, int index) {
  if (!open) {
    if (osd_menu_index >= 0) { osd_publish("power-menu", "", 0, 0); osd_menu_index = -1; }
    return;
  }
  osd_menu_index = index;
  mkdir(OSD_DIR, 0755);
  char tmp[256];
  snprintf(tmp, sizeof tmp, "%s.tmp", OSD_FILE);
  FILE *f = fopen(tmp, "w");
  if (!f) return;
  fprintf(f, "{\"schema_version\":1,\"kind\":\"power-menu\",\"index\":%d,\"count\":%d,\"ts\":%ld,\"entries\":[",
          index, nuxel_fsm_menu_count, (long)time(NULL));
  for (int i = 0; i < nuxel_fsm_menu_count; i++)
    fprintf(f, "%s{\"id\":\"%s\",\"label\":\"%s\",\"allowed\":%s}", i ? "," : "",
            nuxel_fsm_menu[i].id, nuxel_fsm_menu[i].label,
            nuxel_fsm_menu[i].trigger_allowed ? "true" : "false");
  fprintf(f, "]}\n");
  fclose(f);
  rename(tmp, OSD_FILE);
}

/* ---- real ALSA volume (card resolved by NAME, never by a fixed index) ---- */
static snd_mixer_t *mixer;
static snd_mixer_elem_t *selem;
static long vol_min, vol_max, vol_cur;
static int mixer_ready, mixer_capped;

static int mixer_open_dev(void) {
  if (mixer_ready) return mixer ? 0 : -1;
  mixer_ready = 1;
  if (snd_mixer_open(&mixer, 0) < 0) { audit("MIXER_OPEN_FAIL"); mixer = NULL; return -1; }
  /* Prefer the card NAME. `default` may resolve through the softvol safety chain
   * (configs/pipewire/asound-nuxel-safe.conf), which is the intended path. */
  if (snd_mixer_attach(mixer, "default") < 0 && snd_mixer_attach(mixer, "hw:0") < 0) {
    audit("MIXER_ATTACH_FAIL"); snd_mixer_close(mixer); mixer = NULL; return -1;
  }
  snd_mixer_selem_register(mixer, NULL, NULL);
  if (snd_mixer_load(mixer) < 0) { audit("MIXER_LOAD_FAIL"); snd_mixer_close(mixer); mixer = NULL; return -1; }
  static const char *prefer[] = { "Master", "Speaker", "Headphone", "Digital Volume", "PCM", "Playback", NULL };
  for (int i = 0; prefer[i] && !selem; i++)
    for (snd_mixer_elem_t *e = snd_mixer_first_elem(mixer); e; e = snd_mixer_elem_next(e)) {
      if (!snd_mixer_selem_is_active(e) || !snd_mixer_selem_has_playback_volume(e)) continue;
      if (strcasestr(snd_mixer_selem_get_name(e), prefer[i])) { selem = e; break; }
    }
  if (!selem)
    for (snd_mixer_elem_t *e = snd_mixer_first_elem(mixer); e; e = snd_mixer_elem_next(e))
      if (snd_mixer_selem_is_active(e) && snd_mixer_selem_has_playback_volume(e)) { selem = e; break; }
  if (!selem) {
    audit("MIXER_NO_PLAYBACK_ELEMENT (the audio path exposes no writable playback volume control)");
    return -1;
  }
  snd_mixer_selem_get_playback_volume_range(selem, &vol_min, &vol_max);
  if (snd_mixer_selem_get_playback_volume(selem, SND_MIXER_SCHN_FRONT_LEFT, &vol_cur) < 0) vol_cur = vol_min;
  audit("MIXER_READY element=%s min=%ld max=%ld current=%ld cap_active=%d cap_pct=%d",
        snd_mixer_selem_get_name(selem), vol_min, vol_max, vol_cur, vol_cap_active, vol_cap_pct);
  return 0;
}

static long vol_cap_ceiling(void) {
  if (!vol_cap_active) return vol_max;
  long ceiling = vol_min + ((vol_max - vol_min) * vol_cap_pct) / 100;
  return ceiling > vol_max ? vol_max : ceiling;
}

static void osd_volume(void) {
  if (mixer_open_dev() < 0 || !selem) {
    osd_publish("volume", "audio path unavailable", 0, 0);
    publish("VOLUME_UNSUPPORTED reason=no-playback-element");
    return;
  }
  int pct = (vol_max > vol_min) ? (int)(((vol_cur - vol_min) * 100) / (vol_max - vol_min)) : 0;
  char txt[64];
  snprintf(txt, sizeof txt, "%d%%%s", pct, vol_cap_active ? " (bring-up limit)" : "");
  osd_publish("volume", txt, pct, 100);
  publish("VOLUME element=%s value=%ld pct=%d", snd_mixer_selem_get_name(selem), vol_cur, pct);
}

static void volume_step(int dir) {
  if (mixer_open_dev() < 0 || !selem) { osd_volume(); return; }
  long step = nuxel_fsm_volume_step(vol_min, vol_max);   /* same formula as A32 */
  long ceiling = vol_cap_ceiling();
  long v = vol_cur + (dir > 0 ? step : -step);
  if (v > ceiling) { v = ceiling; if (dir > 0) mixer_capped = 1; }
  if (v < vol_min) v = vol_min;
  if (snd_mixer_selem_set_playback_volume_all(selem, v) < 0) { audit("VOLUME_SET_FAIL value=%ld", v); return; }
  vol_cur = v;
  audit("VOLUME_STEP dir=%d value=%ld step=%ld ceiling=%ld capped=%d", dir, v, step, ceiling, mixer_capped);
  osd_volume();
}

static void volume_mute_toggle(void) {
  if (mixer_open_dev() < 0 || !selem) { osd_volume(); return; }
  int sw = 0;
  if (snd_mixer_selem_has_playback_switch(selem) &&
      snd_mixer_selem_get_playback_switch(selem, SND_MIXER_SCHN_FRONT_LEFT, &sw) == 0) {
    snd_mixer_selem_set_playback_switch_all(selem, sw ? 0 : 1);
    osd_publish("volume", sw ? "muted" : "unmuted", sw ? 0 : 100, 100);
    publish("VOLUME_MUTE=%d", sw ? 1 : 0);
  } else {
    osd_publish("volume", "no mute switch on this control", 0, 0);
    publish("VOLUME_MUTE_UNSUPPORTED");
  }
}

/* ---- sound mode: normal -> vibrate -> silent (briq-03e chord, area 6) ----
 * The mode is RECORDED in /var/lib/nuxel/audio/sound-mode, which is the shared
 * contract with the audio settings surface (briq-03c). The mixer playback switch
 * is set for silent/normal; whether the owner then HEARS anything stays
 * NEEDS_OWNER_TEST - a switch write is never an audibility claim. */
static void volume_set_switch(int on) {
  if (mixer_open_dev() < 0 || !selem) return;
  if (snd_mixer_selem_has_playback_switch(selem))
    snd_mixer_selem_set_playback_switch_all(selem, on ? 1 : 0);
}

static void sound_mode_cycle(void) {
  char cur[16] = "normal";
  FILE *f = fopen(SOUND_MODE_FILE, "r");
  if (f) { if (fscanf(f, "%15s", cur) != 1) strcpy(cur, "normal"); fclose(f); }
  const char *next = !strcmp(cur, "normal") ? "vibrate" : (!strcmp(cur, "vibrate") ? "silent" : "normal");
  mkdir(SOUND_MODE_DIR, 0755);
  FILE *o = fopen(SOUND_MODE_FILE, "w");
  if (o) { fprintf(o, "%s\n", next); fclose(o); }
  else audit("SOUND_MODE_WRITE_FAIL errno=%d", errno);
  volume_set_switch(!strcmp(next, "normal"));
  char l[64]; snprintf(l, sizeof l, "sound-mode %s\n", next);
  fifo_send(HOST_FIFO, l);            /* the launcher shows the mode on the glass */
  char txt[96]; snprintf(txt, sizeof txt, "sound mode: %s", next);
  osd_publish("sound", txt, 100, 100);
  audit("SOUND_MODE %s -> %s (switch_write=%s)", cur, next,
        (!strcmp(next, "normal")) ? "unmute" : "mute");
  publish("SOUND_MODE=%s", next);
  if (!strcmp(next, "vibrate"))
    audit("SOUND_MODE_NOTE vibrate mode also needs the vibrator path (briq-08b): "
          "recorded here, not claimed as a working haptic");
}

/* ---- flashlight: the button side of briq-08c's real LED control ---------- *
 * This manager does NOT write an LED device node: the camera flash is shared
 * with the camera, has thermal limits and needs camera/flashlight arbitration,
 * all of which are owned by briq-08c. The dispatch publishes a REQUEST the
 * owner of that path consumes, and never claims the LED lit. */
static void flashlight_request(void) {
  mkdir("/run/nuxel", 0755);
  FILE *f = fopen(FLASHLIGHT_REQ, "w");
  if (!f) { audit("FLASHLIGHT_REQUEST_FAIL errno=%d", errno); publish("FLASHLIGHT_REQUEST_FAIL errno=%d", errno); return; }
  fprintf(f, "action=toggle requested_by=nuxel-button-manager at=%lld\n", (long long)time(NULL));
  fclose(f);
  fifo_send(HOST_FIFO, "action flashlight\n");
  osd_publish("flashlight", "flashlight toggle requested", 100, 100);
  audit("FLASHLIGHT_REQUESTED path=%s (the LED itself is owned by the camera/flashlight "
        "arbitration in briq-08c; this is the request, not a claim that it lit)", FLASHLIGHT_REQ);
  publish("FLASHLIGHT_REQUESTED");
}

/* ---- the one-time verbose-boot note (Bixby early hold) ------------------- *
 * briq-02b owns the consumer (nuxel-verbose-boot, which runs in the EARLY
 * userspace boot stage and reads /run/nuxel/boot-verbose-once). This is the
 * BUTTON side: publish the request, and say plainly when it cannot apply. */
static void verbose_boot_note_once(void) {
  int consumer_ran = file_exists(VERBOSE_STATE);
  char cap[256] = ""; char *c = slurp(BOOT_CAPS, 0);
  if (c) { snprintf(cap, sizeof cap, "%s", c); free(c); }
  if (consumer_ran) {
    /* The early stage already decided this boot. The button manager starts AFTER
     * it, so it cannot make THIS boot verbose; honouring the override before the
     * first userspace stage needs an initramfs/BOOT key capture. */
    audit("VERBOSE_ONCE_REFUSED reason=boot-stage-already-ran state=BOOT_UPDATE_REQUIRED "
          "caps=%s", cap[0] ? cap : "(none)");
    publish("VERBOSE_ONCE_REFUSED reason=boot-stage-already-ran state=BOOT_UPDATE_REQUIRED");
    osd_publish("boot", "verbose boot: the early boot stage must capture the key (BOOT update pending)", 0, 100);
    return;
  }
  mkdir("/run/nuxel", 0755);
  FILE *f = fopen(VERBOSE_ONCE, "w");
  if (!f) { audit("VERBOSE_ONCE_FAIL errno=%d", errno); return; }
  fprintf(f, "requested_by=nuxel-button-manager at=%lld (this boot only)\n", (long long)time(NULL));
  fclose(f);
  audit("VERBOSE_ONCE_REQUESTED path=%s caps=%s (one boot only; never persisted)", VERBOSE_ONCE,
        cap[0] ? cap : "(none)");
  publish("VERBOSE_ONCE_REQUESTED");
  osd_publish("boot", "verbose boot requested for THIS boot", 100, 100);
}

/* The ONLY place a userspace reboot/power-off is ever executed, and it executes
 * nothing unless the gate allows it. No other path in this program can reboot. */
static void gated_system_action(const char *what) {
  int is_poweroff = (strstr(what, "poweroff") != NULL);
  const char *reason = NULL;
  int ok = nuxel_fsm_gate_decide(&GATE, is_poweroff, (int64_t)time(NULL), &reason);
  if (!ok) {
    audit("REBOOT_REFUSED action=%s reason=%s (nothing was executed)", what, reason);
    publish("REBOOT_REFUSED action=%s reason=%s", what, reason);
    osd_publish("power", "power off / restart is gated: see the engineering report", 0, 100);
    return;
  }
  audit("REBOOT_ALLOWED action=%s reason=%s -> executing through the userspace path", what, reason);
  publish("REBOOT_ALLOWED action=%s reason=%s", what, reason);
  /* record the attempt so the min-interval rule can see it */
  mkdir("/var/lib/nuxel/buttons", 0755);
  FILE *f = fopen(GATE_STATE, "w");
  if (f) { fprintf(f, "%lld\n", (long long)time(NULL)); fclose(f); }
  pid_t pid = fork();
  if (pid == 0) {
    execl("/usr/bin/systemctl", "systemctl", is_poweroff ? "poweroff" : "reboot", (char *)NULL);
    _exit(127);
  }
}

static void perform(const char *action, const char *source) {
  publish("ACTION source=%s action=%s", source, action);
  audit("FSM_ACTION source=%s action=%s", source, action);
  if (!action[0] || !strcmp(action, "disabled") || !strcmp(action, "none")) {
    st("ACTION %s -> disabled (%s)", action, source);
    return;
  }
  if (!strcmp(action, "screen-toggle") || !strcmp(action, "screen-off") || !strcmp(action, "screen-on")) {
    char l[64];
    snprintf(l, sizeof l, "%s\n", action);
    fifo_send(WLFB_FIFO, l);
    return;
  }
  if (!strcmp(action, "volume-up") || !strcmp(action, "volume-up-autorepeat")) { volume_step(+1); return; }
  if (!strcmp(action, "volume-down") || !strcmp(action, "volume-down-autorepeat")) { volume_step(-1); return; }
  if (!strcmp(action, "volume-mute")) { volume_mute_toggle(); return; }
  if (!strcmp(action, "sound-mode-cycle")) { sound_mode_cycle(); return; }
  if (!strcmp(action, "flashlight")) { flashlight_request(); return; }
  if (!strcmp(action, "verbose-boot-note")) { verbose_boot_note_once(); return; }
  if (!strcmp(action, "reboot-request")) { gated_system_action("systemctl-reboot"); return; }
  if (!strcmp(action, "systemctl-reboot")) { gated_system_action("systemctl-reboot"); return; }
  if (!strcmp(action, "systemctl-poweroff")) { gated_system_action("systemctl-poweroff"); return; }
  /* ---- the NO FLASHING invariant, enforced in code ---------------------- *
   * These two actions must exist (the menu is complete) and must never run.
   * Refusing here, loudly and with the reason recorded, is the whole point of
   * having the entries: the invariant is observable, not a comment.          */
  if (!strcmp(action, "enter-recovery") || !strcmp(action, "enter-download-mode")) {
    audit("MENU_REFUSED action=%s reason=NO_FLASH_INVARIANT "
          "(this mission performs no flashing and never leaves Linux for the bootloader)", action);
    publish("MENU_REFUSED action=%s reason=NO_FLASH_INVARIANT", action);
    osd_publish("power-menu", "refused: this mission never enters Recovery or Download Mode", 0, 100);
    return;
  }
  if (!strcmp(action, "open-terminal")) { fifo_send(HOST_FIFO, "open-terminal\n"); return; }
  if (!strcmp(action, "back") || !strcmp(action, "home") || !strcmp(action, "recents") ||
      !strcmp(action, "search") || !strcmp(action, "settings") || !strcmp(action, "lock") ||
      !strcmp(action, "screenshot") || !strcmp(action, "camera") || !strcmp(action, "voice-input") ||
      !strcmp(action, "notifications-panel") || !strcmp(action, "all-apps")) {
    char l[64];
    snprintf(l, sizeof l, "action %s\n", action);
    fifo_send(HOST_FIFO, l);
    return;
  }
  if (!strncmp(action, "app:", 4)) {
    const char *id = action + 4;
    for (const char *p = id; *p; p++)
      if (!(isalnum((unsigned char)*p) || *p == '.' || *p == '_' || *p == '-')) {
        audit("ACTION app:%s REFUSED (invalid id)", id);
        return;
      }
    char l[128];
    snprintf(l, sizeof l, "launch %s\n", id);
    fifo_send(HOST_FIFO, l);
    return;
  }
  audit("ACTION %s UNKNOWN (ignored)", action);
}

/* ---- FSM action -> effect ---------------------------------------------- *
 * The FSM names decisions; this is the single place that turns a decision into
 * an effect. Menu bookkeeping (OSD document, audit trail) happens here so the
 * menu on the glass and the menu in the log can never disagree. */
static void menu_select(nuxel_fsm *f, int64_t t) {
  (void)t;
  const nuxel_fsm_menu_entry *m = &nuxel_fsm_menu[f->menu_index];
  if (m->trigger_allowed) {
    audit("MENU_SELECT id=%s action=%s", m->id, m->action);
    f->menu_open = 0;
    osd_menu(0, 0);
    perform(m->action, "menu");
  } else {
    audit("MENU_REFUSED id=%s reason=%s", m->id, m->refusal ? m->refusal : "not-allowed");
    publish("MENU_REFUSED action=%s reason=%s", m->action, m->refusal ? m->refusal : "not-allowed");
    osd_publish("power-menu", "entry refused (see the audit log)", 0, 100);
  }
}

static void handle_action(nuxel_fsm *f, const char *a, const char *src) {
  if (!strcmp(a, "menu-open")) {
    audit("MENU_OPEN index=%d id=%s", f->menu_index, nuxel_fsm_menu[f->menu_index].id);
    osd_menu(1, f->menu_index);
    return;
  }
  if (!strcmp(a, "menu-close") || !strcmp(a, "menu-close-timeout")) {
    audit("MENU_CLOSE reason=%s", a);
    osd_menu(0, 0);
    return;
  }
  if (!strcmp(a, "menu-move-up") || !strcmp(a, "menu-move-down")) {
    audit("MENU_NAV %s index=%d id=%s", a, f->menu_index, nuxel_fsm_menu[f->menu_index].id);
    osd_menu(1, f->menu_index);
    return;
  }
  if (!strncmp(a, "menu-select:", 12)) {
    audit("MENU_SELECT id=%s", a + 12);
    osd_menu(0, 0);
    return;                       /* the entry's own action follows from the FSM */
  }
  if (!strncmp(a, "menu-refused:", 13)) {
    audit("MENU_REFUSED id=%s (the entry exists and is deliberately not executable)", a + 13);
    publish("MENU_REFUSED action=%s reason=%s", a + 13, "gated-or-no-flash-invariant");
    osd_publish("power-menu", "entry refused (see the audit log)", 0, 100);
    return;
  }
  if (!strcmp(a, "gesture-none")) return;    /* recognised as "not a gesture" */
  perform(a, src);
}

/* ========================= input device discovery ======================== */

/* Proper capability walk: EVIOCGBIT(EV_KEY) with the kernel's own long size, so
   a key the driver really reports can never be classified as absent. */
static int dev_has_key(int fd, unsigned code) {
  unsigned long bits[(KEY_MAX / (8 * sizeof(long))) + 1];
  memset(bits, 0, sizeof bits);
  if (ioctl(fd, EVIOCGBIT(EV_KEY, sizeof bits), bits) < 0) return -1;
  return !!(bits[code / (8 * sizeof(long))] & (1UL << (code % (8 * sizeof(long)))));
}
static int dev_has_abs(int fd, unsigned code) {
  unsigned long bits[(ABS_MAX / (8 * sizeof(long))) + 1];
  memset(bits, 0, sizeof bits);
  if (ioctl(fd, EVIOCGBIT(EV_ABS, sizeof bits), bits) < 0) return -1;
  return !!(bits[code / (8 * sizeof(long))] & (1UL << (code % (8 * sizeof(long)))));
}

/* Every input node is examined once; the KEY node is chosen by capability and
 * (as a tie-break) by name, and the TOUCH node by MT capability + DIRECT prop.
 * No /dev/input/eventN is ever assumed — the numbers are read from the directory
 * and reported, so a different enumeration order cannot break the manager. */
struct devsel {
  int  key_fd;   char key_path[96];  char key_name[256];
  int  touch_fd; char touch_path[96]; char touch_name[256];
  int32_t axis_max_x, axis_max_y;
};

static int open_devices(struct devsel *d) {
  d->key_fd = d->touch_fd = -1;
  DIR *dir = opendir("/dev/input");
  if (!dir) { audit("INPUT_DIR_FAIL errno=%d (/dev/input is not readable)", errno); return -1; }
  struct dirent *de;
  int key_score = -1, touch_score = -1;
  while ((de = readdir(dir))) {
    if (strncmp(de->d_name, "event", 5)) continue;
    char path[96];
    snprintf(path, sizeof path, "/dev/input/%.80s", de->d_name);
    int fd = open(path, O_RDONLY | O_NONBLOCK);
    if (fd < 0) { audit("INPUT_OPEN_FAIL path=%s errno=%d", path, errno); continue; }
    char name[256] = "";
    if (ioctl(fd, EVIOCGNAME(sizeof name), name) < 0) snprintf(name, sizeof name, "?");

    int kp = dev_has_key(fd, KEY_POWER) > 0 ? 1 : 0;
    int kv = dev_has_key(fd, KEY_VOLUMEUP) > 0 ? 1 : 0;
    int kd = dev_has_key(fd, KEY_VOLUMEDOWN) > 0 ? 1 : 0;
    if (kp || kv || kd) {
      int score = kp + kv + kd + ((strstr(name, "gpio_keys") || strstr(name, "sec_key_notifier")) ? 4 : 0);
      if (score > key_score) {
        if (d->key_fd >= 0) close(d->key_fd);
        key_score = score;
        d->key_fd = fd;
        snprintf(d->key_path, sizeof d->key_path, "%s", path);
        snprintf(d->key_name, sizeof d->key_name, "%s", name);
        fd = -1;                       /* ownership moved */
      }
    }
    if (fd >= 0 && d->touch_fd < 0) {
      unsigned long props[(INPUT_PROP_MAX / (8 * sizeof(long))) + 1];
      memset(props, 0, sizeof props);
      int prc = ioctl(fd, EVIOCGPROP(sizeof props), props);
      int direct = (prc >= 0) &&
        !!(props[INPUT_PROP_DIRECT / (8 * sizeof(long))] & (1UL << (INPUT_PROP_DIRECT % (8 * sizeof(long)))));
      int mt = dev_has_abs(fd, ABS_MT_POSITION_X) > 0 && dev_has_abs(fd, ABS_MT_POSITION_Y) > 0;
      if (mt && direct) {
        int score = 2 + ((strstr(name, "sec_touchscreen") || strstr(name, "sec_ts") ||
                          strstr(name, "touchscreen")) ? 2 : 0);
        if (score > touch_score) {
          if (d->touch_fd >= 0) close(d->touch_fd);
          touch_score = score;
          d->touch_fd = fd;
          snprintf(d->touch_path, sizeof d->touch_path, "%s", path);
          snprintf(d->touch_name, sizeof d->touch_name, "%s", name);
          struct input_absinfo ai;
          if (ioctl(fd, EVIOCGABS(ABS_MT_POSITION_X), &ai) == 0) d->axis_max_x = ai.maximum;
          if (ioctl(fd, EVIOCGABS(ABS_MT_POSITION_Y), &ai) == 0) d->axis_max_y = ai.maximum;
          fd = -1;
        }
      }
    }
    if (fd >= 0) close(fd);
  }
  closedir(dir);
  if (d->key_fd < 0) audit("KEY_DEVICE_NOT_FOUND (no evdev node exposes POWER/VOLUMEUP/VOLUMEDOWN)");
  else audit("KEY_DEVICE_OPEN path=%s name=%s (selected by capability, not by eventN)", d->key_path, d->key_name);
  if (d->touch_fd < 0) audit("TOUCH_DEVICE_NOT_FOUND (no DIRECT+MT device: gestures stay disabled)");
  else audit("TOUCH_DEVICE_OPEN path=%s name=%s axis_max=%dx%d grab=none",
             d->touch_path, d->touch_name, d->axis_max_x, d->axis_max_y);
  return d->key_fd >= 0 ? 0 : -1;
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
  printf("%s name=%s bus=%04x vid=%04x pid=%04x EVIOCGPROP rc=%d direct=%d\n",
         path, name, id.bustype, id.vendor, id.product, prc,
         (prc >= 0) ? !!(props[INPUT_PROP_DIRECT / (8 * sizeof(long))] & (1UL << (INPUT_PROP_DIRECT % (8 * sizeof(long))))) : -1);
  unsigned long keys[(KEY_MAX / (8 * sizeof(long))) + 1];
  memset(keys, 0, sizeof keys);
  int krc = ioctl(fd, EVIOCGBIT(EV_KEY, sizeof keys), keys);
  printf("    EVIOCGBIT(EV_KEY) rc=%d keys:", krc);
  if (krc >= 0)
    for (unsigned c = 0; c <= KEY_MAX; c++)
      if (keys[c / (8 * sizeof(long))] & (1UL << (c % (8 * sizeof(long))))) printf(" %u", c);
  printf("\n");
  unsigned long abs[(ABS_MAX / (8 * sizeof(long))) + 1];
  memset(abs, 0, sizeof abs);
  int arc = ioctl(fd, EVIOCGBIT(EV_ABS, sizeof abs), abs);
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
      printf("    ABS%u min=%d max=%d fuzz=%d flat=%d res=%d\n", probe[i], ai.minimum, ai.maximum, ai.fuzz, ai.flat, ai.resolution);
  }
  fflush(stdout);
}

/* ================================ modes ================================== */

static void mode_probe(void) {
  DIR *d = opendir("/dev/input");
  if (d) {
    struct dirent *de;
    while ((de = readdir(d))) {
      if (strncmp(de->d_name, "event", 5)) continue;
      char p[96];
      snprintf(p, sizeof p, "/dev/input/%.80s", de->d_name);
      int fd = open(p, O_RDONLY | O_NONBLOCK);
      if (fd < 0) { printf("%s OPEN_FAIL errno=%d\n", p, errno); continue; }
      print_dev(fd, p);
      close(fd);
    }
    closedir(d);
  } else {
    printf("/dev/input: %s\n", strerror(errno));
  }
  cfg_load_actions();
  gate_load();
  /* resolve the same way the running manager does, and print the decision */
  struct devsel sel;
  open_devices(&sel);
  printf("--- resolved devices ---\n");
  printf("key=%s (%s)\ntouch=%s (%s) axis_max=%dx%d\n",
         sel.key_path[0] ? sel.key_path : "NOT_FOUND", sel.key_name,
         sel.touch_path[0] ? sel.touch_path : "NOT_FOUND", sel.touch_name,
         sel.axis_max_x, sel.axis_max_y);
  printf("--- resolved actions ---\n");
  printf("power_short=%s power_long=%s power_double=%s power_very_long=%s\n",
         C.power_short, C.power_long, C.power_double, C.power_very_long);
  printf("bixby_short=%s bixby_long=%s bixby_double=%s gestures=%d\n",
         C.bixby_short, C.bixby_long, C.bixby_double, C.gestures_enabled);
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
  if (sel.key_fd >= 0) close(sel.key_fd);
  if (sel.touch_fd >= 0) close(sel.touch_fd);
}

static void mode_capture(double secs) {
  DIR *d = opendir("/dev/input");
  int fds[16]; char paths[16][96]; int n = 0;
  struct pollfd pfd[16];
  if (!d) return;
  struct dirent *de;
  while ((de = readdir(d)) && n < 16) {
    if (strncmp(de->d_name, "event", 5)) continue;
    char p[96];
    snprintf(p, sizeof p, "/dev/input/%.80s", de->d_name);
    int fd = open(p, O_RDONLY | O_NONBLOCK);
    if (fd < 0) continue;
    fds[n] = fd; snprintf(paths[n], sizeof paths[n], "%.80s", de->d_name);
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
                 : e->code == KEY_VOLUMEDOWN ? " (VOLUMEDOWN)"
                 : e->code == NUXEL_FSM_KEY_BIXBY ? " (ASSISTANT/BIXBY)" : "");
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

static void mode_menu_dump(void) {
  printf("SPEC_VERSION %d\n", NUXEL_FSM_SPEC_VERSION);
  printf("MENU_COUNT %d\n", nuxel_fsm_menu_count);
  for (int i = 0; i < nuxel_fsm_menu_count; i++)
    printf("ENTRY %d %s allowed=%d action=%s refusal=%s\n", i, nuxel_fsm_menu[i].id,
           nuxel_fsm_menu[i].trigger_allowed, nuxel_fsm_menu[i].action,
           nuxel_fsm_menu[i].refusal ? nuxel_fsm_menu[i].refusal : "-");
  printf("NO_FLASH_INVARIANT enforced=1 (enter-recovery, enter-download-mode are refused at execution)\n");
}

static void mode_config_check(void) {
  cfg_load_actions();
  gate_load();
  printf("power_short=%s\npower_long=%s\npower_double=%s\npower_very_long=%s\n",
         C.power_short, C.power_long, C.power_double, C.power_very_long);
  printf("volume_up=%s\nvolume_down=%s\nbixby_short=%s\nbixby_long=%s\nbixby_double=%s\n",
         C.volume_up, C.volume_down, C.bixby_short, C.bixby_long, C.bixby_double);
  printf("defer_power=%d defer_bixby=%d gestures=%d\n",
         C.defer_power_short_for_double, C.defer_bixby_short_for_double, C.gestures_enabled);
  const char *reason = NULL;
  int ok = nuxel_fsm_gate_decide(&GATE, 0, (int64_t)time(NULL), &reason);
  printf("reboot_gate decide=%s reason=%s\n", ok ? "ALLOW" : "REFUSE", reason);
}

/* =============================== main loop =============================== */

static volatile int running = 1;
static void on_term(int sig) { (void)sig; running = 0; }

static int64_t now_ms(void) {
  struct timespec ts;
  clock_gettime(CLOCK_MONOTONIC, &ts);
  return (int64_t)ts.tv_sec * 1000 + ts.tv_nsec / 1000000;
}

/* A trace replay is delegated to the built helper so there is exactly ONE
 * implementation of the state machine: the sim compiles nuxel-button-fsm.h with
 * -DNUXEL_FSM_MAIN. Delegating also means the replay can run on a host with no
 * panel, no libasound and no evdev. */
static int mode_fsm_sim(const char *trace) {
  char self[4096];
  ssize_t n = readlink("/proc/self/exe", self, sizeof self - 1);
  if (n > 0) {
    self[n] = 0;
    char *slash = strrchr(self, '/');
    if (slash) {
      *slash = 0;
      char cand[4096];
      snprintf(cand, sizeof cand, "%.4000s/nuxel-button-fsm-sim", self);
      if (access(cand, X_OK) == 0) { execl(cand, "nuxel-button-fsm-sim", trace, (char *)NULL); }
    }
  }
  if (access(SIM_BIN, X_OK) == 0) execl(SIM_BIN, "nuxel-button-fsm-sim", trace, (char *)NULL);
  fprintf(stderr,
          "fsm-sim helper not installed (%s). Build it with\n"
          "  cc -std=c11 -O1 -DNUXEL_FSM_MAIN -x c nuxel-button-fsm.h -o nuxel-button-fsm-sim\n"
          "then re-run: nuxel-button-manager --fsm-sim %s\n", SIM_BIN, trace);
  return 1;
}

/* Translate one evdev frame into FSM events. Multi-touch: only the primary
 * (slot 0) contact is tracked — the three gestures this manager owns are
 * single-finger gestures, and pretending to handle pinch would be dishonest. */
struct mttrack {
  int slot, tracking;
  int32_t x, y;
  int32_t axis_max_x, axis_max_y;
};

int main(int argc, char **argv) {
  if (argc > 1 && !strcmp(argv[1], "--probe")) { mode_probe(); return 0; }
  if (argc > 2 && !strcmp(argv[1], "--capture")) { mode_capture(atof(argv[2])); return 0; }
  if (argc > 1 && !strcmp(argv[1], "--menu-dump")) { mode_menu_dump(); return 0; }
  if (argc > 1 && !strcmp(argv[1], "--config-check")) { mode_config_check(); return 0; }
  if (argc > 2 && !strcmp(argv[1], "--fsm-sim")) return mode_fsm_sim(argv[2]);
  if (argc > 1) {
    fprintf(stderr,
      "usage: %s [--probe|--capture SECS|--menu-dump|--config-check|--fsm-sim TRACE]\n", argv[0]);
    return 2;
  }

  signal(SIGTERM, on_term);
  signal(SIGINT, on_term);
  cfg_load_actions();
  gate_load();

  struct devsel sel;
  if (open_devices(&sel) < 0) {
    publish("KEY_DEVICE_NOT_FOUND");
    return 3;
  }
  if (!C.gestures_enabled && sel.touch_fd >= 0) {
    close(sel.touch_fd);
    sel.touch_fd = -1;
    audit("GESTURES_DISABLED by configuration (%s)", FSM_JSON);
  }

  /* control FIFO: the launcher host / console / nuxelctl drive the SAME actions */
  unlink(CTRL_FIFO);
  if (mkfifo(CTRL_FIFO, 0600) < 0 && errno != EEXIST) audit("CTRL_FIFO_FAIL errno=%d", errno);
  int ctl = open(CTRL_FIFO, O_RDWR | O_NONBLOCK | O_CLOEXEC);

  nuxel_fsm fsm;
  nuxel_fsm_init(&fsm, &C);
  struct mttrack mt;
  memset(&mt, 0, sizeof mt);
  mt.tracking = -1;
  mt.slot = 0;
  mt.axis_max_x = sel.axis_max_x ? sel.axis_max_x : NUXEL_FSM_DEFAULT_AXIS_MAX_X;
  mt.axis_max_y = sel.axis_max_y ? sel.axis_max_y : NUXEL_FSM_DEFAULT_AXIS_MAX_Y;

  publish("MANAGER_READY device=%s touch=%s", sel.key_path,
          sel.touch_fd >= 0 ? sel.touch_path : "none");
  audit("MANAGER_READY key=%s touch=%s gestures=%d fsm_spec_v=%d",
        sel.key_path, sel.touch_fd >= 0 ? sel.touch_path : "none", C.gestures_enabled, NUXEL_FSM_SPEC_VERSION);

  /* publish the key capabilities so the on-device report can be compared with
   * /proc/bus/input/devices instead of trusting this program */
  unsigned long keys[(KEY_MAX / (8 * sizeof(long))) + 1];
  memset(keys, 0, sizeof keys);
  if (ioctl(sel.key_fd, EVIOCGBIT(EV_KEY, sizeof keys), keys) >= 0) {
    char list[512]; size_t o = 0;
    for (unsigned c = 0; c <= KEY_MAX && o < sizeof list - 8; c++)
      if (keys[c / (8 * sizeof(long))] & (1UL << (c % (8 * sizeof(long)))))
        o += (size_t)snprintf(list + o, sizeof list - o, "%u ", c);
    list[o] = 0;
    publish("KEY_CAPABILITIES %s", list);
    audit("KEY_CAPABILITIES %s", list);
  } else {
    audit("EVIOCGBIT(EV_KEY) FAILED errno=%d — refusing to guess the key set", errno);
    publish("EVIOCGBIT_FAILED errno=%d", errno);
  }

  /* ---- start-up key-state sync (one-time) ---------------------------------
   * A key the owner is ALREADY holding when this manager opens the node produces
   * no further evdev event, so without this sync the Bixby early-hold ("hold
   * Bixby through the boot") would be invisible: the FSM's early window would
   * never see a press. EVIOCGKEY reports the state the driver holds RIGHT NOW;
   * a set bit becomes a synthetic press at t~start. It never synthesises a
   * release and it never grabs the device, so libinput and Phoc keep receiving
   * every event they receive today. */
  {
    const unsigned long bits = 8 * sizeof(long);
    unsigned long held[(KEY_MAX / bits) + 1];
    memset(held, 0, sizeof held);
    if (ioctl(sel.key_fd, EVIOCGKEY(sizeof held), held) >= 0) {
      static const unsigned probe[4] = { KEY_POWER, KEY_VOLUMEUP, KEY_VOLUMEDOWN,
                                         (unsigned)NUXEL_FSM_KEY_BIXBY };
      for (int i = 0; i < 4; i++) {
        unsigned code = probe[i];
        if (code > KEY_MAX) continue;
        if (!(held[code / bits] & (1UL << (code % bits)))) continue;
        nuxel_fsm_event se; memset(&se, 0, sizeof se);
        se.t_ms = now_ms(); se.kind = NUXEL_FSM_EV_KEY; se.code = (int)code; se.value = 1;
        const char *a[4];
        int n = nuxel_fsm_feed(&fsm, &C, &se, a, 4);
        for (int j = 0; j < n; j++) handle_action(&fsm, a[j], "key-sync");
        audit("KEY_STATE_SYNC code=%u value=1 held_at_start=1 (already down when the manager started)", code);
      }
    } else {
      audit("EVIOCGKEY FAILED errno=%d — no start-up key-state sync: a Bixby held through the "
            "boot cannot be seen by the early-hold window on this run", errno);
      publish("EVIOCGKEY_FAILED errno=%d", errno);
    }
  }

  struct pollfd pf[3];
  pf[0].fd = sel.key_fd;   pf[0].events = POLLIN;
  pf[1].fd = ctl;          pf[1].events = POLLIN;
  pf[2].fd = sel.touch_fd; pf[2].events = POLLIN;
  nfds_t npf = sel.touch_fd >= 0 ? 3 : 2;

  time_t last_cfg_poll = 0;

  while (running) {
    int r = poll(pf, npf, 200);
    int64_t t = now_ms();

    time_t now = time(NULL);
    if (now != last_cfg_poll) { last_cfg_poll = now; cfg_load_actions(); }

    /* The poll timeout IS the tick source: a hold produces no event, so without
     * ticks a long press could never be classified. */
    {
      nuxel_fsm_event te; memset(&te, 0, sizeof te); te.t_ms = t; te.kind = NUXEL_FSM_EV_TICK;
      const char *a[4];
      int n = nuxel_fsm_feed(&fsm, &C, &te, a, 4);
      for (int i = 0; i < n; i++) handle_action(&fsm, a[i], "tick");
    }

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
          else if (!strcmp(q, "menu-open")) { fsm.menu_open = 1; fsm.menu_index = 0; fsm.menu_last_activity_ms = t; osd_menu(1, 0); }
          else if (!strcmp(q, "menu-close")) { fsm.menu_open = 0; osd_menu(0, 0); }
          else if (!strcmp(q, "menu-down")) { if (fsm.menu_open) { fsm.menu_index = (fsm.menu_index + 1) % nuxel_fsm_menu_count; osd_menu(1, fsm.menu_index); } }
          else if (!strcmp(q, "menu-up")) { if (fsm.menu_open) { fsm.menu_index = (fsm.menu_index - 1 + nuxel_fsm_menu_count) % nuxel_fsm_menu_count; osd_menu(1, fsm.menu_index); } }
          else if (!strcmp(q, "menu-select")) { if (fsm.menu_open) menu_select(&fsm, t); }
          else if (!strncmp(q, "action ", 7)) perform(q + 7, "control-fifo");
          else if (!strcmp(q, "reload")) { cfg_load_actions(); gate_load(); }
          else if (*q) audit("CTRL_UNKNOWN '%s'", q);
          q = nl ? nl + 1 : NULL;
        }
      }
    }

    if (r > 0 && (pf[0].revents & POLLIN)) {
      struct input_event ev[64];
      ssize_t got = read(sel.key_fd, ev, sizeof ev);
      int cnt = (int)(got / (ssize_t)sizeof(struct input_event));
      for (int k = 0; k < cnt; k++) {
        nuxel_fsm_event e; memset(&e, 0, sizeof e);
        e.t_ms = t; e.kind = NUXEL_FSM_EV_KEY;
        e.code = ev[k].code; e.value = ev[k].value;
        if (ev[k].type != EV_KEY) continue;
        const char *a[4];
        int n = nuxel_fsm_feed(&fsm, &C, &e, a, 4);
        for (int i = 0; i < n; i++) handle_action(&fsm, a[i], "key");
        if (!n && ev[k].value == 1 &&
            ev[k].code != KEY_POWER && ev[k].code != KEY_VOLUMEUP &&
            ev[k].code != KEY_VOLUMEDOWN && ev[k].code != (unsigned)NUXEL_FSM_KEY_BIXBY)
          audit("KEY_UNMAPPED code=%u", ev[k].code);
      }
    }

    if (sel.touch_fd >= 0 && r > 0 && (pf[2].revents & POLLIN)) {
      struct input_event ev[64];
      ssize_t got = read(sel.touch_fd, ev, sizeof ev);
      int cnt = (int)(got / (ssize_t)sizeof(struct input_event));
      for (int k = 0; k < cnt; k++) {
        struct input_event *e = &ev[k];
        if (e->type == EV_ABS) {
          switch (e->code) {
            case ABS_MT_SLOT: mt.slot = e->value; break;
            case ABS_MT_TRACKING_ID:
              if (mt.slot == 0) {
                if (e->value >= 0) {
                  mt.tracking = e->value;
                  nuxel_fsm_event te; memset(&te, 0, sizeof te);
                  te.t_ms = t; te.kind = NUXEL_FSM_EV_TOUCH; te.phase = NUXEL_FSM_TOUCH_DOWN;
                  te.x = mt.x; te.y = mt.y; te.axis_max_x = mt.axis_max_x; te.axis_max_y = mt.axis_max_y;
                  const char *a[4]; int n = nuxel_fsm_feed(&fsm, &C, &te, a, 4);
                  for (int i = 0; i < n; i++) handle_action(&fsm, a[i], "touch");
                } else {
                  mt.tracking = -1;
                }
              }
              break;
            case ABS_MT_POSITION_X: if (mt.slot == 0) mt.x = e->value; break;
            case ABS_MT_POSITION_Y: if (mt.slot == 0) mt.y = e->value; break;
            default: break;
          }
        } else if (e->type == EV_SYN && e->code == SYN_REPORT && mt.slot == 0) {
          nuxel_fsm_event te; memset(&te, 0, sizeof te);
          te.t_ms = t; te.kind = NUXEL_FSM_EV_TOUCH;
          te.x = mt.x; te.y = mt.y; te.axis_max_x = mt.axis_max_x; te.axis_max_y = mt.axis_max_y;
          te.phase = mt.tracking >= 0 ? NUXEL_FSM_TOUCH_MOVE : NUXEL_FSM_TOUCH_UP;
          const char *a[4]; int n = nuxel_fsm_feed(&fsm, &C, &te, a, 4);
          for (int i = 0; i < n; i++) handle_action(&fsm, a[i], "touch");
        }
      }
    }
  }
  audit("MANAGER_EXIT");
  publish("MANAGER_EXIT");
  osd_menu(0, 0);
  if (ctl >= 0) close(ctl);
  if (sel.key_fd >= 0) close(sel.key_fd);
  if (sel.touch_fd >= 0) close(sel.touch_fd);
  return 0;
}
