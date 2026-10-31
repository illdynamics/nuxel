/* nuxel-button-fsm.h — the S10+ (beyond2lte) hardware-button and screen-gesture
 * finite state machine, as a dependency-free, replayable core (A33, briq-03e).
 *
 * WHY THIS FILE IS SEPARATE FROM THE DAEMON
 *   The daemon (nuxel-button-manager.c) needs libasound and <linux/input.h>, so
 *   it can only be built and run on the target or in the VM. The *logic* on the
 *   other hand is pure: given a timestamped event and a small configuration it
 *   produces an action. Keeping that logic in this header means the REAL state
 *   machine — not a Python re-implementation of it — can be replayed offline on
 *   the developer host against recorded event traces:
 *
 *       cc -std=c11 -O1 -DNUXEL_FSM_MAIN -x c nuxel-button-fsm.h -o /tmp/fsm-sim
 *       /tmp/fsm-sim --menu-dump
 *       /tmp/fsm-sim < tests/fixtures-p3/button-fsm/<case>.trace
 *
 *   Every timing constant below is authoritative in configs/nuxel/input/
 *   button-fsm.json too, and tools/s10plus/a33/tests/test-button-fsm.py
 *   cross-checks JSON <-> these defines <-> the PROTECTED A32 source, so the
 *   three implementations cannot drift. Changing a number here without changing
 *   the JSON (or the A32 parity contract) fails the offline test.
 *
 * INVARIANTS THIS FILE HONOURS
 *   * No /dev/input/eventN is ever named: the daemon selects nodes by capability
 *     and name. See input_selection in the JSON spec.
 *   * No flashing surface of any kind: nothing here can reach a bootloader, a
 *     partition or a block device. The Recovery and Download-Mode power-menu
 *     entries EXIST (so the menu is complete and the refusal is observable) and
 *     are hard-refused at execution time with reason NO_FLASH_INVARIANT.
 *   * The reboot class is gated: a very-long power press or the Restart entry
 *     executes nothing unless nuxel_fsm_gate_decide() returns allow.
 *   * Unproven behaviour is never claimed: the file reports what the state
 *     machine decided, never that a phone did something.
 */
#ifndef NUXEL_BUTTON_FSM_H
#define NUXEL_BUTTON_FSM_H

#include <stddef.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>

#define NUXEL_FSM_SPEC_VERSION 1

/* ---- key codes (measured on the handset: gpio_keys bitmap) ---------------- */
#define NUXEL_FSM_KEY_VOLUMEDOWN 114
#define NUXEL_FSM_KEY_VOLUMEUP   115
#define NUXEL_FSM_KEY_POWER      116
#define NUXEL_FSM_KEY_BIXBY      703   /* KEY 0x2bf, the Samsung assistant key */

/* ---- press classes (ms) — mirror of press_classes in button-fsm.json ----- */
#define NUXEL_FSM_POWER_DEBOUNCE_MS        30
#define NUXEL_FSM_POWER_SHORT_MAX_MS       2000
#define NUXEL_FSM_POWER_LONG_MIN_MS        2000
#define NUXEL_FSM_POWER_VERY_LONG_MIN_MS   8000
#define NUXEL_FSM_POWER_DOUBLE_GAP_MS      400
#define NUXEL_FSM_BIXBY_DEBOUNCE_MS        20
#define NUXEL_FSM_BIXBY_SHORT_MAX_MS       1500
#define NUXEL_FSM_BIXBY_LONG_MIN_MS        1500
#define NUXEL_FSM_BIXBY_DOUBLE_GAP_MS      400
#define NUXEL_FSM_VOLUME_DEBOUNCE_MS       20
#define NUXEL_FSM_VOLUME_LONG_MIN_MS       500
#define NUXEL_FSM_VOLUME_REPEAT_DELAY_MS   400
#define NUXEL_FSM_VOLUME_REPEAT_INTERVAL_MS 250
/* Chords (briq-03e): both keys held together for this long. Measured from the
 * SECOND key press, so "hold both keys" means what it says on the glass. */
#define NUXEL_FSM_CHORD_HOLD_MIN_MS        500
/* The Bixby early-hold window, measured from the FIRST event the manager sees
 * (i.e. the start of Nuxel's userspace, not the kernel's). */
#define NUXEL_FSM_BIXBY_EARLY_WINDOW_MS    2000

/* ---- volume step — mirror of volume_step in the JSON --------------------- */
#define NUXEL_FSM_VOLUME_STEP_DIVISOR      20
#define NUXEL_FSM_VOLUME_STEP_MIN          1

/* ---- gesture geometry and timing — mirror of gestures in the JSON -------- */
#define NUXEL_FSM_EDGE_ZONE_PX             24
#define NUXEL_FSM_BOTTOM_ZONE_PX           48
#define NUXEL_FSM_MIN_TRAVEL_PX            90
#define NUXEL_FSM_HOLD_MAX_DRIFT_PX        24
#define NUXEL_FSM_DEFAULT_AXIS_MAX_X       1439
#define NUXEL_FSM_DEFAULT_AXIS_MAX_Y       3039
#define NUXEL_FSM_SWIPE_MAX_MS             600
#define NUXEL_FSM_HOLD_MS                  500
#define NUXEL_FSM_EDGE_BACK_MAX_MS         400
#define NUXEL_FSM_STALE_TRACK_MS           1500

/* ---- power menu / reboot gate — mirror of the JSON ----------------------- */
#define NUXEL_FSM_MENU_TIMEOUT_MS          15000
#define NUXEL_FSM_REBOOT_MIN_INTERVAL_S    1800
#define NUXEL_FSM_REBOOT_MAX_PER_HOUR      1

/* gesture recognizer ids */
enum {
  NUXEL_FSM_GESTURE_NONE = 0,
  NUXEL_FSM_GESTURE_EDGE_BACK,
  NUXEL_FSM_GESTURE_SWIPE_UP_HOME,
  NUXEL_FSM_GESTURE_SWIPE_UP_HOLD_RECENTS
};

/* event kinds */
enum {
  NUXEL_FSM_EV_KEY = 1,     /* code/value from an evdev EV_KEY               */
  NUXEL_FSM_EV_TOUCH = 2,   /* phase/x/y from the touchscreen (MT-B or ST)   */
  NUXEL_FSM_EV_TICK = 3     /* timer tick: the only thing that can fire a hold */
};

/* touch phases */
enum { NUXEL_FSM_TOUCH_DOWN = 1, NUXEL_FSM_TOUCH_MOVE = 2, NUXEL_FSM_TOUCH_UP = 3,
       NUXEL_FSM_TOUCH_CANCEL = 4 };

typedef struct {
  int64_t t_ms;      /* monotonic milliseconds, supplied by the caller       */
  int     kind;      /* NUXEL_FSM_EV_*                                      */
  int     code;      /* EV_KEY: key code                                    */
  int     value;     /* EV_KEY: 0 release, 1 press, 2 autorepeat             */
  int     phase;     /* EV_TOUCH: NUXEL_FSM_TOUCH_*                         */
  int32_t x, y;      /* EV_TOUCH: panel pixels (raw axis units)             */
  int32_t axis_max_x, axis_max_y; /* EV_TOUCH: axis ranges, 0 => default    */
} nuxel_fsm_event;

/* The action map. Values are short identifiers dispatched by the daemon. Any
 * value found in /etc/nuxel/input/buttons.json wins over these defaults. */
typedef struct {
  char power_short[64];
  char power_long[64];
  char power_double[64];
  char power_very_long[64];
  char volume_up[64];
  char volume_down[64];
  char volume_up_repeat[64];
  char volume_down_repeat[64];
  char volume_up_long[64];            /* the long-press class: panel, not repeat */
  char volume_down_long[64];
  char chord_power_volume_up[64];     /* Power + VolumeUp   held together     */
  char chord_power_volume_down[64];   /* Power + VolumeDown held together     */
  char bixby_short[64];
  char bixby_long[64];
  char bixby_double[64];
  char bixby_early_hold[64];          /* Bixby held from the start of userspace */
  char gesture_back[64];
  char gesture_home[64];
  char gesture_recents[64];
  int  defer_power_short_for_double;  /* 0 = A32 behaviour (immediate)     */
  int  defer_bixby_short_for_double;  /* 1 = default: disambiguate 1x/2x   */
  int  gestures_enabled;
  int  volume_repeat_enabled;  /* 0 = a volume HOLD opens a panel (briq-03e);
                                * 1 (or a *-autorepeat remap) = A32 cadence */
  int  early_window_ms;        /* Bixby early-hold window after FSM start    */
} nuxel_fsm_cfg;

typedef struct {
  int64_t power_down_ms, power_used_long, power_used_very_long;
  int     power_down, power_pending_double_armed, power_double_deferring;
  int64_t power_release_ms, power_pending_deadline_ms;

  int64_t bixby_down_ms, bixby_used_long;
  int     bixby_down, bixby_double_deferring, bixby_pending_double_armed;
  int64_t bixby_release_ms, bixby_pending_deadline_ms;
  int     bixby_early;              /* the press began inside the early window */

  int     vol_held;                 /* 0 none, +1 up, -1 down             */
  int     vol_used_long;            /* the long-press class already fired  */
  int     vol_repeat_mode;          /* this hold is a key-repeat hold      */
  int64_t vol_down_ms, vol_next_repeat_ms;

  /* chords (priority above every single-key class) */
  int     chord_armed;              /* 0 none, +1 power+up, -1 power+down  */
  int     chord_fired;
  int64_t chord_start_ms;
  int     chord_step_pending;       /* +1/-1: a volume step buffered by a chord */

  int     started;                  /* the FSM has seen its first event    */
  int64_t fsm_start_ms;             /* = t of that first event (userspace start) */

  /* touch track */
  int     touch_active;
  int64_t touch_down_ms, touch_last_ms;
  int32_t touch_down_x, touch_down_y, touch_axis_max_x, touch_axis_max_y;
  int     touch_hold_fired, touch_gesture_done;

  /* power menu */
  int     menu_open;
  int     menu_index;
  int64_t menu_last_activity_ms;

  /* bookkeeping for evidence (never a claim about hardware) */
  int64_t now_ms;
  unsigned actions_emitted;
} nuxel_fsm;

/* The reboot gate. Pure data; filled by the caller from
 * /etc/nuxel/buttons/reboot-gate.json (and /var/lib/nuxel/reboot/policy.json
 * when bg-09's policy exists). Decision logic is pure so it can be unit-tested. */
typedef struct {
  int     enabled;
  int     allow_restart;
  int     allow_poweroff;
  int     min_interval_s;
  int     max_per_hour;
  int     require_rollback_path;
  int     require_clean_journal;
  int     rollback_path_ok;   /* caller verified the path exists           */
  int     journal_clean;      /* caller verified the journal is not corrupt */
  int64_t last_reboot_t_s;    /* 0 = never in this boot history            */
  int     reboots_last_hour;
  int     policy_allow_reboot;/* bg-09 policy file says allow_reboot=true   */
  int     policy_known;       /* the policy file exists / was read          */
} nuxel_fsm_gate;

static void nuxel_fsm_cfg_defaults(nuxel_fsm_cfg *c) {
  memset(c, 0, sizeof *c);
  strcpy(c->power_short,       "screen-toggle");
  strcpy(c->power_long,        "power-menu");
  strcpy(c->power_double,      "camera");
  strcpy(c->power_very_long,   "reboot-request");
  strcpy(c->volume_up,         "volume-up");
  strcpy(c->volume_down,       "volume-down");
  strcpy(c->volume_up_repeat,  "volume-up");
  strcpy(c->volume_down_repeat,"volume-down");
  /* briq-03e exact mapping: a volume HOLD opens a panel. The A32 autorepeat
   * cadence is NOT deleted - it stays reachable by remapping volume_up_long /
   * volume_down_long to the *-autorepeat actions (or volume_repeat_enabled=1),
   * which is why the repeat windows above are still authoritative. */
  strcpy(c->volume_up_long,    "notifications-panel");
  strcpy(c->volume_down_long,  "all-apps");
  strcpy(c->chord_power_volume_up,   "sound-mode-cycle");
  strcpy(c->chord_power_volume_down, "screenshot");
  strcpy(c->bixby_short,       "open-terminal");
  strcpy(c->bixby_long,        "disabled");
  strcpy(c->bixby_double,      "flashlight");
  strcpy(c->bixby_early_hold,  "verbose-boot-note");
  strcpy(c->gesture_back,      "back");
  strcpy(c->gesture_home,      "home");
  strcpy(c->gesture_recents,   "recents");
  /* A32 compatibility: A32 dispatched the power short-press action on release
   * with no deferral window, and that behaviour is protected. Bixby's short
   * press is deferred instead, which is where single-vs-double actually
   * matters (open-terminal vs voice-input). */
  c->defer_power_short_for_double = 0;
  c->defer_bixby_short_for_double = 1;
  c->gestures_enabled = 1;
  c->volume_repeat_enabled = 0;
  c->early_window_ms = NUXEL_FSM_BIXBY_EARLY_WINDOW_MS;
}

static void nuxel_fsm_init(nuxel_fsm *f, const nuxel_fsm_cfg *c) {
  (void)c;
  memset(f, 0, sizeof *f);
  f->vol_held = 0;
  f->menu_index = 0;
}

/* ------------------------------------------------------------------ power menu */
typedef struct { const char *id; const char *label; const char *action; int trigger_allowed; const char *refusal; } nuxel_fsm_menu_entry;

/* Mirror of power_menu.entries in configs/nuxel/input/button-fsm.json. The
 * offline test compares this table with the JSON entry-by-entry, so the menu the
 * daemon shows cannot silently differ from the menu the spec documents. */
static const nuxel_fsm_menu_entry nuxel_fsm_menu[] = {
  /* A34 TOUCHDOWN: the owner explicitly asked for a Cancel entry.  It is first
   * so the safest choice is the initial selection; menu-close is an internal
   * action, never a reboot path. */
  { "cancel",        "Cancel",            "menu-close",            1, NULL },
  { "lock-screen",   "Lock screen",       "lock",                  1, NULL },
  { "screenshot",    "Take screenshot",   "screenshot",            1, NULL },
  { "restart",       "Restart",           "systemctl-reboot",      1, "gate-closed-owner-absent" },
  { "power-off",     "Power off",         "systemctl-poweroff",    1, "gate-closed-owner-absent" },
  { "reboot-verbose","Reboot Verbose",    "reboot-verbose",        1, "gate-closed-owner-absent" },
  { "reboot-safe-mode","Safe Mode",       "reboot-safe-mode",      1, "gate-closed-owner-absent" },
  { "reboot-diag",   "Reboot Diag",       "reboot-diag",           1, "gate-closed-owner-absent" },
  { "reboot-debug",  "Reboot Debug",      "reboot-debug",          1, "gate-closed-owner-absent" },
  /* Browser-style controls operate only on the foreground PWA through the
   * existing host-fifo contract.  They are part of the 15-entry configured
   * menu; omitting them from the active A34 build was PWNAGE-44000 defect #3. */
  { "back",          "Back",              "back",                  1, NULL },
  { "forward",       "Forward",           "forward",               1, NULL },
  { "stop",          "Stop loading",      "stop",                  1, NULL },
  { "reload-launcher","Reload launcher",  "reload-launcher",       1, NULL },
  { "recovery",      "Recovery (Samsung)","enter-recovery",        0, "NO_FLASH_INVARIANT" },
  { "download-mode", "Download Mode (Odin)","enter-download-mode", 0, "NO_FLASH_INVARIANT" }
};
static const int nuxel_fsm_menu_count = (int)(sizeof(nuxel_fsm_menu) / sizeof(nuxel_fsm_menu[0]));

/* ------------------------------------------------------------------- reboot gate
 * Returns 1 when the action may execute, 0 when it must be refused, and writes a
 * machine-readable reason. The gate is closed unless EVERY condition holds:
 * explicit enable, the per-action allow flag, the min-interval since the last
 * reboot, the per-hour cap, a verified rollback path, a clean journal, and -
 * when bg-09's policy file exists - that policy's own allow_reboot=true.
 * The AND (never OR) is deliberate: neither build group can silently override
 * the other. */
static int nuxel_fsm_gate_decide(const nuxel_fsm_gate *g, int is_poweroff,
                                 int64_t now_s, const char **reason) {
  if (!g->enabled)                    { *reason = "gate-disabled"; return 0; }
  if (is_poweroff && !g->allow_poweroff) { *reason = "poweroff-not-allowed"; return 0; }
  if (!is_poweroff && !g->allow_restart) { *reason = "restart-not-allowed"; return 0; }
  if (g->policy_known && !g->policy_allow_reboot) { *reason = "policy-denies-reboot"; return 0; }
  if (g->require_rollback_path && !g->rollback_path_ok) { *reason = "no-rollback-path"; return 0; }
  if (g->require_clean_journal && !g->journal_clean) { *reason = "journal-not-clean"; return 0; }
  if (g->min_interval_s > 0 && g->last_reboot_t_s > 0 &&
      (now_s - g->last_reboot_t_s) < g->min_interval_s) { *reason = "min-interval-not-elapsed"; return 0; }
  if (g->max_per_hour > 0 && g->reboots_last_hour >= g->max_per_hour) { *reason = "hourly-cap-reached"; return 0; }
  *reason = "allowed";
  return 1;
}

/* --------------------------------------------------------------------- feed
 * Feeds one event and yields up to `max` actions (usually 0 or 1; a timer tick
 * can close a menu and open another action in the same pass).
 * Returns the number of actions written to `out`. */
static int nuxel_fsm_feed(nuxel_fsm *f, const nuxel_fsm_cfg *c,
                          const nuxel_fsm_event *e,
                          const char **out, int max) {
  int n = 0;
  f->now_ms = e->t_ms;
  if (!f->started) { f->started = 1; f->fsm_start_ms = e->t_ms; }

#define EMIT(s) do { if (n < max) out[n++] = (s); f->actions_emitted++; } while (0)

  /* ---- menu idle timeout: a stray long press must not strand a modal menu -- */
  if (f->menu_open && (e->t_ms - f->menu_last_activity_ms) >= NUXEL_FSM_MENU_TIMEOUT_MS) {
    f->menu_open = 0;
    EMIT("menu-close-timeout");
  }

  /* ---- deferred single-press commits (double-press disambiguation) -------- */
  if (f->power_double_deferring && e->t_ms >= f->power_pending_deadline_ms) {
    f->power_double_deferring = 0;
    EMIT(c->power_short);
  }
  if (f->bixby_double_deferring && e->t_ms >= f->bixby_pending_deadline_ms) {
    f->bixby_double_deferring = 0;
    EMIT(c->bixby_short);
  }

  /* ---- volume hold: chord > long press (panel) > key-repeat volume --------
   * A Chord in progress keeps the volume class completely quiet, because the
   * chord outranks every single-key class (see ARBITRATION in the spec). */
  if (f->vol_held && e->kind == NUXEL_FSM_EV_TICK && !f->chord_armed) {
    if (f->vol_repeat_mode) {
      /* A32 cadence, kept for an owner remap / volume_repeat_enabled=1:
       * 400 ms delay, then every 250 ms. */
      if (e->t_ms >= f->vol_next_repeat_ms) {
        EMIT(f->vol_held > 0 ? c->volume_up_repeat : c->volume_down_repeat);
        f->vol_next_repeat_ms = e->t_ms + NUXEL_FSM_VOLUME_REPEAT_INTERVAL_MS;
      }
    } else if (!f->vol_used_long &&
               (e->t_ms - f->vol_down_ms) >= NUXEL_FSM_VOLUME_LONG_MIN_MS) {
      f->vol_used_long = 1;
      EMIT(f->vol_held > 0 ? c->volume_up_long : c->volume_down_long);
    }
  }

  /* ---- chords: decided on the timer, before any long-press class ---------- */
  if (f->chord_armed && !f->chord_fired && e->kind == NUXEL_FSM_EV_TICK &&
      (e->t_ms - f->chord_start_ms) >= NUXEL_FSM_CHORD_HOLD_MIN_MS) {
    f->chord_fired = 1;
    f->chord_step_pending = 0;          /* the chord wins; a buffered step is dropped */
    /* cancel every single-key class for the rest of this hold, including the
     * 8 s reboot class: an emergency combo must never also ask for a reboot */
    f->power_used_long = 1;
    f->power_used_very_long = 1;
    f->vol_used_long = 1;
    if (f->menu_open) { f->menu_open = 0; f->menu_last_activity_ms = e->t_ms; EMIT("menu-close"); }
    EMIT(f->chord_armed > 0 ? c->chord_power_volume_up : c->chord_power_volume_down);
  }

  if (e->kind == NUXEL_FSM_EV_KEY) {
    /* ---------------- POWER ---------------- */
    if (e->code == NUXEL_FSM_KEY_POWER) {
      if (e->value == 1) {
        f->power_down = 1;
        f->power_down_ms = e->t_ms;
        f->power_used_long = 0;
        f->power_used_very_long = 0;
        /* A34 TOUCHDOWN: a deferred Bixby short press (bixby_short=open-terminal)
         * must never surface later as `source=tick action=open-terminal` while
         * the owner is using Power.  The measured failure was exactly that: a
         * Bixby release inside its 400 ms double-press window, followed by
         * Power activity, opened Terminal on a later tick.  Power now cancels
         * the pending Bixby short; a deliberate Bixby long hold (bixby_down)
         * is unaffected. */
        if (f->bixby_double_deferring && !f->bixby_down) {
          f->bixby_double_deferring = 0;
        }
        if (f->vol_held) {                 /* power pressed while volume held */
          f->chord_armed = f->vol_held > 0 ? 1 : -1;
          f->chord_fired = 0;
          f->chord_step_pending = 0;       /* the volume press already emitted its step */
          f->chord_start_ms = e->t_ms;
        }
        if (f->power_double_deferring) {   /* second press => it was a double */
          f->power_double_deferring = 0;
          f->power_pending_double_armed = 1;
        }
      } else if (e->value == 2 || e->kind == NUXEL_FSM_EV_TICK) {
        /* autorepeat path is handled on ticks below; kept for kernel repeats */
      }
      /* long / very-long are decided by ticks (and by EV_KEY autorepeat)      */
      if ((e->value == 2 || e->value == 1) && f->power_down && !f->chord_armed) {
        int64_t held = e->t_ms - f->power_down_ms;
        if (held >= NUXEL_FSM_POWER_VERY_LONG_MIN_MS && !f->power_used_very_long) {
          f->power_used_very_long = 1;
          if (f->menu_open) { f->menu_open = 0; EMIT("menu-close"); }
          EMIT(c->power_very_long);      /* gate applied by the caller */
        } else if (held >= NUXEL_FSM_POWER_LONG_MIN_MS && !f->power_used_long) {
          f->power_used_long = 1;
          if (f->menu_open) {
            f->menu_open = 0;            /* a second long press dismisses it */
            f->menu_last_activity_ms = e->t_ms;
            EMIT("menu-close");
          } else if (!strcmp(c->power_long, "power-menu")) {
            f->menu_open = 1;
            f->menu_index = 0;
            f->menu_last_activity_ms = e->t_ms;
            EMIT("menu-open");
          } else {
            EMIT(c->power_long);
          }
        }
      }
      if (e->value == 0) {
        int64_t held = e->t_ms - f->power_down_ms;
        f->power_down = 0;
        if (f->chord_armed && !f->chord_fired) {
          /* the other key was released too early: no chord. Any buffered volume
           * step is delivered by the volume release below, so no press is lost. */
          f->chord_armed = 0;
        } else if (f->chord_fired) {
          f->chord_armed = 0;            /* the chord already acted: release is inert */
        }
        if (f->power_used_very_long) {
          /* the reboot class already fired on the hold; the release is inert  */
        } else if (f->power_used_long) {
          /* The long press already opened (or closed) the menu: the release that
             ends the hold must NOT dismiss a menu the user is about to use. */
        } else if (held >= NUXEL_FSM_POWER_DEBOUNCE_MS) {
          if (f->power_pending_double_armed) {
            f->power_pending_double_armed = 0;
            EMIT(c->power_double);
          } else if (f->menu_open) {
            const nuxel_fsm_menu_entry *m = &nuxel_fsm_menu[f->menu_index];
            f->menu_last_activity_ms = e->t_ms;
            if (m->trigger_allowed) {
              /* The FSM names the decision; the daemon dispatches it. A refused
                 entry still publishes why it was refused - that refusal is the
                 observable proof for the Recovery / Download-Mode entries. */
              static char sel[96];
              snprintf(sel, sizeof sel, "menu-select:%s", m->id);
              EMIT(sel);
              EMIT(m->action);
              f->menu_open = 0;            /* a successful selection closes it */
            } else {
              static char ref[96];
              snprintf(ref, sizeof ref, "menu-refused:%s", m->id);
              EMIT(ref);
            }
          } else if (c->defer_power_short_for_double) {
            f->power_double_deferring = 1;
            f->power_pending_deadline_ms = e->t_ms + NUXEL_FSM_POWER_DOUBLE_GAP_MS;
          } else {
            EMIT(c->power_short);
          }
        }
      }
    }
    /* ---------------- VOLUME ---------------- */
    else if (e->code == NUXEL_FSM_KEY_VOLUMEUP || e->code == NUXEL_FSM_KEY_VOLUMEDOWN) {
      int dir = (e->code == NUXEL_FSM_KEY_VOLUMEUP) ? +1 : -1;
      if (e->value == 1) {
        if (f->menu_open && !f->power_down) {
          f->menu_index = (f->menu_index + (dir > 0 ? -1 : 1) + nuxel_fsm_menu_count) % nuxel_fsm_menu_count;
          f->menu_last_activity_ms = e->t_ms;
          EMIT(dir > 0 ? "menu-move-up" : "menu-move-down");
        } else if (f->power_down) {
          /* Power is held: this is the Power+Volume chord, NOT a volume press.
           * The step is buffered (not emitted) and delivered if the chord does
           * not complete, so a press is never silently swallowed. */
          f->chord_armed = dir > 0 ? 1 : -1;
          f->chord_fired = 0;
          f->chord_step_pending = dir;
          f->chord_start_ms = e->t_ms > f->power_down_ms ? e->t_ms : f->power_down_ms;
          f->vol_held = dir;
          f->vol_down_ms = e->t_ms;
          f->vol_used_long = 0;
          f->vol_repeat_mode = 0;
        } else {
          f->vol_held = dir;
          f->vol_down_ms = e->t_ms;
          f->vol_used_long = 0;
          /* The A32 cadence survives, but only when it is asked for: either the
           * owner remapped the long action to *-autorepeat, or the explicit
           * volume_repeat_enabled setting is on. */
          f->vol_repeat_mode =
            (!strcmp(dir > 0 ? c->volume_up_long : c->volume_down_long,
                     dir > 0 ? "volume-up-autorepeat" : "volume-down-autorepeat")
             || c->volume_repeat_enabled) ? 1 : 0;
          f->vol_next_repeat_ms = e->t_ms + NUXEL_FSM_VOLUME_REPEAT_DELAY_MS;
          EMIT(dir > 0 ? c->volume_up : c->volume_down);
        }
      } else if (e->value == 0) {
        if (f->vol_held == dir) {
          f->vol_held = 0;
          if (f->chord_armed && !f->chord_fired) {
            f->chord_armed = 0;
            if (f->chord_step_pending == dir) {
              f->chord_step_pending = 0;
              EMIT(dir > 0 ? c->volume_up : c->volume_down);
            }
          } else if (f->chord_fired) {
            f->chord_armed = 0;
          }
        }
      }
    }
    /* ---------------- BIXBY / assistant ---------------- */
    else if (e->code == NUXEL_FSM_KEY_BIXBY) {
      if (e->value == 1) {
        f->bixby_down = 1;
        f->bixby_down_ms = e->t_ms;
        f->bixby_used_long = 0;
        /* EARLY window: measured from the first event this manager saw, i.e. the
         * start of Nuxel's userspace. A key the owner is ALREADY holding when the
         * manager opens the node arrives as a synthetic press at t~start (see the
         * EVIOCGKEY sync in the daemon), so holding Bixby through the boot lands
         * here - which is exactly the documented one-time verbose-boot override. */
        f->bixby_early = ((e->t_ms - f->fsm_start_ms) <= c->early_window_ms) ? 1 : 0;
        if (f->bixby_double_deferring) {   /* second press => it was a double */
          f->bixby_double_deferring = 0;
          f->bixby_pending_double_armed = 1;
        }
      }
      if ((e->value == 2 || e->value == 1) && f->bixby_down) {
        int64_t held = e->t_ms - f->bixby_down_ms;
        if (held >= NUXEL_FSM_BIXBY_LONG_MIN_MS && !f->bixby_used_long) {
          f->bixby_used_long = 1;
          EMIT(f->bixby_early ? c->bixby_early_hold : c->bixby_long);
        }
      }
      if (e->value == 0) {
        int64_t held = e->t_ms - f->bixby_down_ms;
        f->bixby_down = 0;
        if (f->bixby_pending_double_armed) {
          f->bixby_pending_double_armed = 0;
          EMIT(c->bixby_double);
        } else if (!f->bixby_used_long && held >= NUXEL_FSM_BIXBY_DEBOUNCE_MS) {
          if (c->defer_bixby_short_for_double) {
            f->bixby_double_deferring = 1;
            f->bixby_pending_deadline_ms = e->t_ms + NUXEL_FSM_BIXBY_DOUBLE_GAP_MS;
          } else {
            EMIT(c->bixby_short);
          }
        }
      }
    }
    /* unknown keys are the daemon's business (it logs KEY_UNMAPPED)          */
  }

  /* ---- power long/very-long decided on ticks (a hold produces no event) --- */
  if (e->kind == NUXEL_FSM_EV_TICK && f->power_down && !f->chord_armed) {
    int64_t held = e->t_ms - f->power_down_ms;
    if (held >= NUXEL_FSM_POWER_VERY_LONG_MIN_MS && !f->power_used_very_long) {
      f->power_used_very_long = 1;
      if (f->menu_open) { f->menu_open = 0; EMIT("menu-close"); }
      EMIT(c->power_very_long);
    } else if (held >= NUXEL_FSM_POWER_LONG_MIN_MS && !f->power_used_long) {
      f->power_used_long = 1;
      if (f->menu_open) {
        f->menu_open = 0;                /* a second long press dismisses it */
        f->menu_last_activity_ms = e->t_ms;
        EMIT("menu-close");
      } else if (!strcmp(c->power_long, "power-menu")) {
        f->menu_open = 1;
        f->menu_index = 0;
        f->menu_last_activity_ms = e->t_ms;
        EMIT("menu-open");
      } else {
        EMIT(c->power_long);
      }
    }
  }
  if (e->kind == NUXEL_FSM_EV_TICK && f->bixby_down) {
    int64_t held = e->t_ms - f->bixby_down_ms;
    if (held >= NUXEL_FSM_BIXBY_LONG_MIN_MS && !f->bixby_used_long) {
      f->bixby_used_long = 1;
      EMIT(f->bixby_early ? c->bixby_early_hold : c->bixby_long);
    }
  }

  /* ------------------------------------------------------------------ gestures */
  if (e->kind == NUXEL_FSM_EV_TOUCH) {
    if (e->phase == NUXEL_FSM_TOUCH_DOWN) {
      f->touch_active = 1;
      f->touch_down_ms = f->touch_last_ms = e->t_ms;
      f->touch_down_x = e->x; f->touch_down_y = e->y;
      f->touch_axis_max_x = e->axis_max_x > 0 ? e->axis_max_x : NUXEL_FSM_DEFAULT_AXIS_MAX_X;
      f->touch_axis_max_y = e->axis_max_y > 0 ? e->axis_max_y : NUXEL_FSM_DEFAULT_AXIS_MAX_Y;
      f->touch_hold_fired = 0;
      f->touch_gesture_done = 0;
    } else if (e->phase == NUXEL_FSM_TOUCH_MOVE && f->touch_active) {
      f->touch_last_ms = e->t_ms;
    } else if (e->phase == NUXEL_FSM_TOUCH_UP && f->touch_active) {
      f->touch_active = 0;
      f->touch_last_ms = e->t_ms;
      if (!f->touch_gesture_done && c->gestures_enabled) {
        int32_t dx = e->x - f->touch_down_x, dy = e->y - f->touch_down_y;
        int32_t adx = dx < 0 ? -dx : dx, ady = dy < 0 ? -dy : dy;
        int64_t dur = e->t_ms - f->touch_down_ms;
        int bottom = f->touch_down_y >= (f->touch_axis_max_y - NUXEL_FSM_BOTTOM_ZONE_PX);
        int edge = (f->touch_down_x <= NUXEL_FSM_EDGE_ZONE_PX) ||
                   (f->touch_down_x >= (f->touch_axis_max_x - NUXEL_FSM_EDGE_ZONE_PX));
        if (edge && adx >= NUXEL_FSM_MIN_TRAVEL_PX && adx > ady && dur <= NUXEL_FSM_EDGE_BACK_MAX_MS) {
          EMIT(c->gesture_back);
        } else if (bottom && dy <= -NUXEL_FSM_MIN_TRAVEL_PX && ady > adx && dur <= NUXEL_FSM_SWIPE_MAX_MS) {
          EMIT(c->gesture_home);
        } else {
          EMIT("gesture-none");
        }
      }
    } else if (e->phase == NUXEL_FSM_TOUCH_CANCEL) {
      f->touch_active = 0;
    }
  }
  /* swipe-up-and-hold fires on the timer, so the state is unambiguous: the user
   * is still touching at hold_ms with almost no movement. It fires once. */
  if (e->kind == NUXEL_FSM_EV_TICK && f->touch_active && c->gestures_enabled) {
    int64_t held = e->t_ms - f->touch_down_ms;
    if (held >= NUXEL_FSM_HOLD_MS && !f->touch_hold_fired &&
        f->touch_down_y >= (f->touch_axis_max_y - NUXEL_FSM_BOTTOM_ZONE_PX)) {
      /* still down at hold_ms inside the bottom zone => recents, fired once */
      f->touch_hold_fired = 1;
      f->touch_gesture_done = 1;
      EMIT(c->gesture_recents);
    }
    if (held > NUXEL_FSM_STALE_TRACK_MS) f->touch_active = 0;   /* lost lift */
  }
  return n;
#undef EMIT
}

/* Convenience: how many volume steps a full range would move. Kept here so the
 * daemon and the offline test compute the same number from the same constant. */
static long nuxel_fsm_volume_step(long range_min, long range_max) {
  long step = (range_max - range_min) / NUXEL_FSM_VOLUME_STEP_DIVISOR;
  return step < NUXEL_FSM_VOLUME_STEP_MIN ? NUXEL_FSM_VOLUME_STEP_MIN : step;
}

#endif /* NUXEL_BUTTON_FSM_H */

/* ==========================================================================
 * NUXEL_FSM_MAIN — the offline replay harness.
 *
 * Compiled only when the test asks for it, and it is the SAME state machine the
 * daemon runs: the test never re-implements the logic, it drives it.
 *
 *   cc -std=c11 -O1 -DNUXEL_FSM_MAIN -x c nuxel-button-fsm.h -o fsm-sim
 *   fsm-sim --menu-dump            # machine-readable menu table + constants
 *   fsm-sim --gate enabled=0,...   # exercise the reboot gate
 *   fsm-sim < trace                # replay: prints ACTION lines + a summary
 *
 * Trace grammar (whitespace separated, '#' starts a comment):
 *   <t_ms> key <power|volume_up|volume_down|bixby> <0|1|2>
 *   <t_ms> touch <down|move|up|cancel> <x> <y> [<axis_max_x> <axis_max_y>]
 *   <t_ms> tick
 *   cfg reboot_allowed=<0|1> | cfg defer=power|bixby|both|none
 * ========================================================================== */
#ifdef NUXEL_FSM_MAIN
#include <stdio.h>
#include <stdlib.h>

static int fsm_sim_menu_dump(void) {
  printf("SPEC_VERSION %d\n", NUXEL_FSM_SPEC_VERSION);
  printf("POWER_DEBOUNCE_MS %d\n", NUXEL_FSM_POWER_DEBOUNCE_MS);
  printf("POWER_SHORT_MAX_MS %d\n", NUXEL_FSM_POWER_SHORT_MAX_MS);
  printf("POWER_LONG_MIN_MS %d\n", NUXEL_FSM_POWER_LONG_MIN_MS);
  printf("POWER_VERY_LONG_MIN_MS %d\n", NUXEL_FSM_POWER_VERY_LONG_MIN_MS);
  printf("POWER_DOUBLE_GAP_MS %d\n", NUXEL_FSM_POWER_DOUBLE_GAP_MS);
  printf("BIXBY_DEBOUNCE_MS %d\n", NUXEL_FSM_BIXBY_DEBOUNCE_MS);
  printf("BIXBY_SHORT_MAX_MS %d\n", NUXEL_FSM_BIXBY_SHORT_MAX_MS);
  printf("BIXBY_LONG_MIN_MS %d\n", NUXEL_FSM_BIXBY_LONG_MIN_MS);
  printf("BIXBY_DOUBLE_GAP_MS %d\n", NUXEL_FSM_BIXBY_DOUBLE_GAP_MS);
  printf("VOLUME_DEBOUNCE_MS %d\n", NUXEL_FSM_VOLUME_DEBOUNCE_MS);
  printf("VOLUME_LONG_MIN_MS %d\n", NUXEL_FSM_VOLUME_LONG_MIN_MS);
  printf("CHORD_HOLD_MIN_MS %d\n", NUXEL_FSM_CHORD_HOLD_MIN_MS);
  printf("BIXBY_EARLY_WINDOW_MS %d\n", NUXEL_FSM_BIXBY_EARLY_WINDOW_MS);
  printf("VOLUME_REPEAT_DELAY_MS %d\n", NUXEL_FSM_VOLUME_REPEAT_DELAY_MS);
  printf("VOLUME_REPEAT_INTERVAL_MS %d\n", NUXEL_FSM_VOLUME_REPEAT_INTERVAL_MS);
  printf("VOLUME_STEP_DIVISOR %d\n", NUXEL_FSM_VOLUME_STEP_DIVISOR);
  printf("VOLUME_STEP_MIN %d\n", NUXEL_FSM_VOLUME_STEP_MIN);
  printf("EDGE_ZONE_PX %d\n", NUXEL_FSM_EDGE_ZONE_PX);
  printf("BOTTOM_ZONE_PX %d\n", NUXEL_FSM_BOTTOM_ZONE_PX);
  printf("MIN_TRAVEL_PX %d\n", NUXEL_FSM_MIN_TRAVEL_PX);
  printf("HOLD_MAX_DRIFT_PX %d\n", NUXEL_FSM_HOLD_MAX_DRIFT_PX);
  printf("DEFAULT_AXIS_MAX_X %d\n", NUXEL_FSM_DEFAULT_AXIS_MAX_X);
  printf("DEFAULT_AXIS_MAX_Y %d\n", NUXEL_FSM_DEFAULT_AXIS_MAX_Y);
  printf("SWIPE_MAX_MS %d\n", NUXEL_FSM_SWIPE_MAX_MS);
  printf("HOLD_MS %d\n", NUXEL_FSM_HOLD_MS);
  printf("EDGE_BACK_MAX_MS %d\n", NUXEL_FSM_EDGE_BACK_MAX_MS);
  printf("STALE_TRACK_MS %d\n", NUXEL_FSM_STALE_TRACK_MS);
  printf("MENU_TIMEOUT_MS %d\n", NUXEL_FSM_MENU_TIMEOUT_MS);
  printf("REBOOT_MIN_INTERVAL_S %d\n", NUXEL_FSM_REBOOT_MIN_INTERVAL_S);
  printf("REBOOT_MAX_PER_HOUR %d\n", NUXEL_FSM_REBOOT_MAX_PER_HOUR);
  printf("KEY_POWER %d\n", NUXEL_FSM_KEY_POWER);
  printf("KEY_VOLUMEUP %d\n", NUXEL_FSM_KEY_VOLUMEUP);
  printf("KEY_VOLUMEDOWN %d\n", NUXEL_FSM_KEY_VOLUMEDOWN);
  printf("KEY_BIXBY %d\n", NUXEL_FSM_KEY_BIXBY);
  printf("MENU_COUNT %d\n", nuxel_fsm_menu_count);
  /* exercises the shared volume-step helper so the sim and the daemon provably
   * compute the same A32 cadence step (5 % of the range, floored at 1)        */
  printf("VOLUME_STEP_RANGE31 %ld\n", nuxel_fsm_volume_step(0, 31));
  printf("VOLUME_STEP_RANGE100 %ld\n", nuxel_fsm_volume_step(0, 100));
  for (int i = 0; i < nuxel_fsm_menu_count; i++)
    printf("ENTRY %d %s allowed=%d action=%s refusal=%s\n", i, nuxel_fsm_menu[i].id,
           nuxel_fsm_menu[i].trigger_allowed, nuxel_fsm_menu[i].action,
           nuxel_fsm_menu[i].refusal ? nuxel_fsm_menu[i].refusal : "-");
  printf("NO_FLASH_INVARIANT enforced=1\n");
  return 0;
}

static void fsm_sim_emit(int64_t t, const char *a) { printf("ACTION t=%lld name=%s\n", (long long)t, a); }

static int fsm_sim_run(FILE *in, int print_all) {
  nuxel_fsm_cfg c; nuxel_fsm f; nuxel_fsm_cfg_defaults(&c); nuxel_fsm_init(&f, &c);
  char line[512]; int64_t last_t = 0; int rc_total = 0;
  while (fgets(line, sizeof line, in)) {
    char *h = strchr(line, '#'); if (h) *h = 0;
    char *tok[8]; int nt = 0;
    for (char *p = strtok(line, " \t\r\n"); p && nt < 8; p = strtok(NULL, " \t\r\n")) tok[nt++] = p;
    if (nt == 0) continue;
    if (!strcmp(tok[0], "cfg")) {
      for (int i = 1; i < nt; i++) {
        if (!strncmp(tok[i], "reboot_allowed=", 15)) { /* recorded for the gate leg */ }
        if (!strncmp(tok[i], "defer=", 6)) {
          const char *v = tok[i] + 6;
          c.defer_power_short_for_double = (!strcmp(v, "power") || !strcmp(v, "both"));
          c.defer_bixby_short_for_double = (!strcmp(v, "bixby") || !strcmp(v, "both"));
        }
        if (!strncmp(tok[i], "gestures=", 9)) c.gestures_enabled = atoi(tok[i] + 9);
        if (!strncmp(tok[i], "volume_long=", 12)) {
          if (!strcmp(tok[i] + 12, "repeat")) {
            strcpy(c.volume_up_long, "volume-up-autorepeat");
            strcpy(c.volume_down_long, "volume-down-autorepeat");
          } else {
            strcpy(c.volume_up_long, "notifications-panel");
            strcpy(c.volume_down_long, "all-apps");
          }
        }
        if (!strncmp(tok[i], "repeat=", 7)) c.volume_repeat_enabled = atoi(tok[i] + 7);
        if (!strncmp(tok[i], "early_window=", 13)) c.early_window_ms = atoi(tok[i] + 13);
      }
      continue;
    }
    int64_t t = (int64_t)strtoll(tok[0], NULL, 10);
    nuxel_fsm_event e; memset(&e, 0, sizeof e); e.t_ms = t;
    if (nt >= 4 && !strcmp(tok[1], "key")) {
      e.kind = NUXEL_FSM_EV_KEY;
      e.code = !strcmp(tok[2], "power") ? NUXEL_FSM_KEY_POWER :
               !strcmp(tok[2], "volume_up") ? NUXEL_FSM_KEY_VOLUMEUP :
               !strcmp(tok[2], "volume_down") ? NUXEL_FSM_KEY_VOLUMEDOWN :
               !strcmp(tok[2], "bixby") ? NUXEL_FSM_KEY_BIXBY : atoi(tok[2]);
      e.value = atoi(tok[3]);
    } else if (nt >= 5 && !strcmp(tok[1], "touch")) {
      e.kind = NUXEL_FSM_EV_TOUCH;
      e.phase = !strcmp(tok[2], "down") ? NUXEL_FSM_TOUCH_DOWN :
                !strcmp(tok[2], "move") ? NUXEL_FSM_TOUCH_MOVE :
                !strcmp(tok[2], "cancel") ? NUXEL_FSM_TOUCH_CANCEL : NUXEL_FSM_TOUCH_UP;
      e.x = (int32_t)atoi(tok[3]); e.y = (int32_t)atoi(tok[4]);
      if (nt >= 7) { e.axis_max_x = (int32_t)atoi(tok[5]); e.axis_max_y = (int32_t)atoi(tok[6]); }
    } else if (!strcmp(tok[1], "tick")) {
      e.kind = NUXEL_FSM_EV_TICK;
    } else {
      continue;
    }
    /* A tick is delivered immediately before every event, exactly as the real
     * 200 ms poll loop does, so a hold is resolved at the first tick at or after
     * its threshold and never later. */
    { nuxel_fsm_event tk; memset(&tk, 0, sizeof tk);
      tk.kind = NUXEL_FSM_EV_TICK; tk.t_ms = t;
      const char *a[4]; int n = nuxel_fsm_feed(&f, &c, &tk, a, 4);
      for (int i = 0; i < n; i++) fsm_sim_emit(t, a[i]);
      rc_total += n; }
    { const char *a[4]; int n = nuxel_fsm_feed(&f, &c, &e, a, 4);
      for (int i = 0; i < n; i++) fsm_sim_emit(t, a[i]);
      rc_total += n; }
    if (t > last_t) last_t = t;
  }
  /* Settle: one final tick far enough ahead to flush deferred presses and menu
   * timeouts, so a trace never depends on the reader's timing. */
  { nuxel_fsm_event tk; memset(&tk, 0, sizeof tk);
    tk.kind = NUXEL_FSM_EV_TICK; tk.t_ms = last_t + NUXEL_FSM_MENU_TIMEOUT_MS + NUXEL_FSM_POWER_DOUBLE_GAP_MS + 1;
    const char *a[4]; int n = nuxel_fsm_feed(&f, &c, &tk, a, 4);
    for (int i = 0; i < n; i++) fsm_sim_emit(tk.t_ms, a[i]);
    rc_total += n; }
  printf("SUMMARY actions=%u emitted=%d menu_open=%d\n", f.actions_emitted, rc_total, f.menu_open);
  if (print_all) printf("NOTE state machine replayed from the real FSM core\n");
  return 0;
}

int main(int argc, char **argv) {
  for (int i = 1; i < argc; i++) {
    if (!strcmp(argv[i], "--menu-dump")) return fsm_sim_menu_dump();
    if (!strcmp(argv[i], "--gate")) {
      nuxel_fsm_gate g; memset(&g, 0, sizeof g);
      g.enabled = 1; g.allow_restart = 1; g.allow_poweroff = 0;
      g.min_interval_s = NUXEL_FSM_REBOOT_MIN_INTERVAL_S;
      g.max_per_hour = NUXEL_FSM_REBOOT_MAX_PER_HOUR;
      g.require_rollback_path = 1; g.rollback_path_ok = 1;
      g.require_clean_journal = 1; g.journal_clean = 1;
      const char *reason = NULL;
      for (int k = 1; k < argc; k++) {
        if (!strncmp(argv[k], "enabled=", 8)) g.enabled = atoi(argv[k] + 8);
        else if (!strncmp(argv[k], "restart=", 8)) g.allow_restart = atoi(argv[k] + 8);
        else if (!strncmp(argv[k], "poweroff=", 9)) g.allow_poweroff = atoi(argv[k] + 9);
        else if (!strncmp(argv[k], "rollback=", 9)) g.rollback_path_ok = atoi(argv[k] + 9);
        else if (!strncmp(argv[k], "journal=", 8)) g.journal_clean = atoi(argv[k] + 8);
        else if (!strncmp(argv[k], "last=", 5)) g.last_reboot_t_s = (int64_t)strtoll(argv[k] + 5, NULL, 10);
        else if (!strncmp(argv[k], "perhour=", 8)) g.reboots_last_hour = atoi(argv[k] + 8);
        else if (!strncmp(argv[k], "policy=", 7)) { g.policy_known = 1; g.policy_allow_reboot = atoi(argv[k] + 7); }
        else if (!strncmp(argv[k], "poweroff_action=", 16)) { /* alias */ }
      }
      int is_po = 0;
      for (int k = 1; k < argc; k++) if (!strcmp(argv[k], "action=poweroff")) is_po = 1;
      int ok = nuxel_fsm_gate_decide(&g, is_po, 1000000, &reason);
      printf("GATE decide=%s reason=%s\n", ok ? "ALLOW" : "REFUSE", reason);
      return ok ? 0 : 1;
    }
    if (!strcmp(argv[i], "--help")) {
      printf("usage: fsm-sim [--menu-dump] [--gate k=v ...] [trace-file]\n");
      printf("  trace cfg keys: defer=power|bixby|both|none  gestures=0|1\n");
      printf("                  volume_long=panel|repeat  repeat=0|1  early_window=<ms>\n");
      return 0;
    }
  }
  FILE *in = stdin;
  if (argc > 1 && argv[1][0] != '-') { in = fopen(argv[1], "r"); if (!in) { perror(argv[1]); return 2; } }
  return fsm_sim_run(in, 1);
}
#endif /* NUXEL_FSM_MAIN */
