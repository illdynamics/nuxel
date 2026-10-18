/* Offline regression test for the REAL S10+ MT frame parser (nuxel-mt.h) and
 * the REAL gesture FSM (nuxel-button-fsm.h).
 *
 * The bug this locks down: the daemon used to emit TOUCH_DOWN on
 * ABS_MT_TRACKING_ID, before ABS_MT_POSITION_X/Y in the same frame.  The first
 * tap of a session therefore reported (0,0) as its down point:
 *   * a tap looked like a swipe from the left edge -> spurious action=back;
 *   * a swipe up from the bottom never satisfied the bottom-zone test -> no
 *     action=home.
 * These tests drive the shipped header code and would fail on that old order.
 */
#include <stdio.h>
#include <string.h>

#include "../../a33/nuxel-button-fsm.h"
#include "../../a33/nuxel-mt.h"

static int failures;
static int checks;

static void ok(const char *name, int cond, const char *detail) {
  checks++;
  if (cond) {
    printf("  PASS %s\n", name);
  } else {
    failures++;
    printf("  FAIL %s%s%s\n", name, detail && *detail ? " - " : "", detail ? detail : "");
  }
}

static struct input_event ev(unsigned type, unsigned code, int value) {
  struct input_event e;
  memset(&e, 0, sizeof e);
  e.type = type; e.code = code; e.value = value;
  return e;
}

/* Feed raw events through the parser; feed the resulting FSM events and return
 * the actions produced (joined with ',' into out for easy assertions). */
static void drive(nuxel_mt_state *m, nuxel_fsm *f, const nuxel_fsm_cfg *c,
                  const struct input_event *raw, int nraw,
                  char *out, size_t outn) {
  size_t o = 0;
  out[0] = 0;
  for (int i = 0; i < nraw; i++) {
    nuxel_mt_event me;
    if (!nuxel_mt_feed(m, &raw[i], &me)) continue;
    nuxel_fsm_event te;
    memset(&te, 0, sizeof te);
    te.t_ms = (int64_t)i * 10;       /* every raw event is 10 ms apart */
    te.kind = NUXEL_FSM_EV_TOUCH;
    te.x = me.x; te.y = me.y;
    te.axis_max_x = me.axis_max_x; te.axis_max_y = me.axis_max_y;
    switch (me.phase) {
      case NUXEL_MT_PHASE_DOWN:   te.phase = NUXEL_FSM_TOUCH_DOWN; break;
      case NUXEL_MT_PHASE_MOVE:   te.phase = NUXEL_FSM_TOUCH_MOVE; break;
      case NUXEL_MT_PHASE_UP:     te.phase = NUXEL_FSM_TOUCH_UP; break;
      case NUXEL_MT_PHASE_CANCEL: te.phase = NUXEL_FSM_TOUCH_CANCEL; break;
      default: continue;
    }
    const char *a[4];
    int n = nuxel_fsm_feed((nuxel_fsm *)f, c, &te, a, 4);
    for (int k = 0; k < n; k++) {
      if (o && o + 1 < outn) out[o++] = ',';
      size_t l = strlen(a[k]);
      if (o + l + 1 > outn) l = outn - o - 1;
      memcpy(out + o, a[k], l); o += l; out[o] = 0;
    }
  }
}

static void run_case(const char *name,
                     const struct input_event *raw, int nraw,
                     int32_t maxx, int32_t maxy,
                     const char *want) {
  nuxel_mt_state m;
  nuxel_fsm_cfg c;
  nuxel_fsm f;
  nuxel_fsm_cfg_defaults(&c);
  nuxel_fsm_init(&f, &c);
  nuxel_mt_init(&m, maxx, maxy);
  char got[256];
  drive(&m, &f, &c, raw, nraw, got, sizeof got);
  ok(name, !strcmp(got, want), got);
}

/* A complete MT-B frame, in the order the sec_ts driver uses. */
#define F_SLOT0        ev(EV_ABS, ABS_MT_SLOT, 0)
#define F_TRACK(id)    ev(EV_ABS, ABS_MT_TRACKING_ID, (id))
#define F_X(x)         ev(EV_ABS, ABS_MT_POSITION_X, (x))
#define F_Y(y)         ev(EV_ABS, ABS_MT_POSITION_Y, (y))
#define F_SYN          ev(EV_SYN, SYN_REPORT, 0)

int main(void) {
  const int32_t MAXX = 4095, MAXY = 4095;

  /* 1. The parser must not emit DOWN at ABS_MT_TRACKING_ID.  This exact frame
   *    order (id before x/y) is what sec_ts produces. */
  {
    nuxel_mt_state m;
    nuxel_mt_init(&m, MAXX, MAXY);
    struct input_event raw[] = { F_SLOT0, F_TRACK(7), F_X(2000), F_Y(1266), F_SYN };
    int downs = 0, evs = 0;
    for (int i = 0; i < (int)(sizeof raw / sizeof raw[0]); i++) {
      nuxel_mt_event me;
      if (!nuxel_mt_feed(&m, &raw[i], &me)) continue;
      evs++;
      if (me.phase == NUXEL_MT_PHASE_DOWN) {
        downs++;
        ok("DOWN is emitted at SYN_REPORT with the frame's real coordinates",
           me.x == 2000 && me.y == 1266, "wrong down coordinates");
      }
    }
    ok("one DOWN per frame", downs == 1 && evs == 1, "parser emitted the wrong number of events");
  }

  /* 2. A normal tap in the middle must not become edge-back. */
  {
    struct input_event raw[] = {
      F_SLOT0, F_TRACK(1), F_X(2000), F_Y(1266), F_SYN,
      F_TRACK(-1), F_SYN
    };
    run_case("a mid-screen tap is gesture-none (never back)", raw,
             (int)(sizeof raw / sizeof raw[0]), MAXX, MAXY, "gesture-none");
  }

  /* 3. The decisive test: swipe up from the bottom edge must emit home. */
  {
    struct input_event raw[] = {
      F_SLOT0, F_TRACK(2), F_X(2000), F_Y(4050), F_SYN,
      F_Y(3000), F_SYN, F_Y(1500), F_SYN, F_Y(900), F_SYN,
      F_TRACK(-1), F_SYN
    };
    run_case("swipe up from the bottom edge emits home", raw,
             (int)(sizeof raw / sizeof raw[0]), MAXX, MAXY, "home");
  }

  /* 4. Edge-back still works when the down point is genuinely on the edge. */
  {
    struct input_event raw[] = {
      F_SLOT0, F_TRACK(3), F_X(8), F_Y(1500), F_SYN,
      F_X(300), F_SYN, F_X(600), F_SYN,
      F_TRACK(-1), F_SYN
    };
    run_case("a real left-edge swipe still emits back", raw,
             (int)(sizeof raw / sizeof raw[0]), MAXX, MAXY, "back");
  }

  /* 5. Some drivers report X/Y before TRACKING_ID.  The result must be the
   *    same because DOWN is decided when the frame closes. */
  {
    struct input_event raw[] = {
      F_SLOT0, F_X(2000), F_Y(4050), F_TRACK(4), F_SYN,
      F_Y(1200), F_SYN,
      F_TRACK(-1), F_SYN
    };
    run_case("coordinate-before-tracking frame order also emits home", raw,
             (int)(sizeof raw / sizeof raw[0]), MAXX, MAXY, "home");
  }

  /* 6. The down point survives a secondary slot's events (slot 0 stays ours). */
  {
    struct input_event raw[] = {
      F_SLOT0, F_TRACK(5), F_X(2000), F_Y(4050), F_SYN,
      ev(EV_ABS, ABS_MT_SLOT, 1), ev(EV_ABS, ABS_MT_TRACKING_ID, 9),
      ev(EV_ABS, ABS_MT_POSITION_X, 10), ev(EV_ABS, ABS_MT_POSITION_Y, 10), F_SYN,
      F_SLOT0, F_Y(1000), F_SYN,
      F_TRACK(-1), F_SYN
    };
    run_case("a second finger cannot steal the slot-0 bottom swipe", raw,
             (int)(sizeof raw / sizeof raw[0]), MAXX, MAXY, "home");
  }

  /* 7. SYN_DROPPED cancels a half-tracked contact instead of leaving it armed. */
  {
    nuxel_mt_state m;
    nuxel_mt_init(&m, MAXX, MAXY);
    struct input_event raw[] = {
      F_SLOT0, F_TRACK(6), F_X(2000), F_Y(4050), F_SYN,
      ev(EV_SYN, SYN_DROPPED, 0)
    };
    int phases[8], n = 0;
    for (int i = 0; i < (int)(sizeof raw / sizeof raw[0]); i++) {
      nuxel_mt_event me;
      if (nuxel_mt_feed(&m, &raw[i], &me) && n < 8) phases[n++] = me.phase;
    }
    ok("SYN_DROPPED emits a CANCEL after an active contact",
       n == 2 && phases[0] == NUXEL_MT_PHASE_DOWN && phases[1] == NUXEL_MT_PHASE_CANCEL,
       "wrong phase sequence");
  }

  printf("== %d check(s), %d failure(s) ==\n", checks, failures);
  return failures ? 1 : 0;
}
